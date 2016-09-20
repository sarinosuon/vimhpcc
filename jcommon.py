# -*- coding: utf-8 -*-
import random
import os
import time
import sys
import string
import traceback
import re
import types
import cStringIO
import telnetlib
import glob
import cPickle
import copy

from hsdl.franca import franca
from hsdl.franca import franca_comm
from hsdl.franca import franca_comm_nonblocking

from hsdl.common import general

from hsdl.vim import shared

LINE_DELIMITER = '\n'

MODE_SEXP = 1
MODE_PROLOG = 2

mode_color = {
    MODE_SEXP : 'green',
    MODE_PROLOG : 'blue'
}

BASE_INDENT_SPACES = '    '
BASE_INDENT_SIZE = len(BASE_INDENT_SPACES)

spaces_pat = re.compile(r'^(?P<spaces>\s*)')

False=0
True=1

SUPPORTED_LANGS = "j clj lfe mzscheme sisc chicken bash python scala factor clp abcl ecl sbcl lisp hs rkt".split()
SUPPORTED_LANGS_EXTS = "j clj lfe scm sh py clp lisp lsp hs rkt oz m js sql pl fs cs c c++ cc cpp erl lfe".split()



ALREADY_INIT = False

SIGN_CURRENT = 0
SIGN_DICT = {}      # perhaps used by tooltip; we want to keep track of line and col:  line -> (col, text)
TOOLTIP_DICT = {}   # this has priority over SIGN_DICT

ALL_SIGNS = []      # (id, number)

ECL_T = ('T',)
ECL_NIL = []


SOCKET_KILL_FILE = "/tmp/___SOCKET_KILL___"

# ----- these imports will fail under linux -----
try:
    import win32process
except:
    pass

directive_pat = re.compile(r'<<[a-zA-Z0-9-_:/]+>>')

# =============================================================================
def execDosScript(script_code, start_path=None, title='mrxvt_bat'):
    app = r'C:\cygwin\usr\local\bin\mrxvt.exe'
    exec_str_list = [app, '-ht', '-sr', '-sl', '5000', '-bg', 'DarkSlateBlue', '-fg', 'white', '-title', title, '-e']

    script_fname = general.clean_path(general.hsdl_mktemp() + '.bat')
    script_fname_win32 = string.replace(script_fname, '/', '\\')
    fout = open(script_fname,'wb')
    fout.write(script_code + "\nerase " + script_fname_win32 + "\n")    # execute code and delete self
    fout.close()

    # Tell DOS to execute it as a script; "/C" means run the specified command then close console;
    # "/K" if you want to keep console open
    exec_str_list += ["cmd", "/C", '"%s"' % script_fname]

    exec_str = string.strip( string.join(exec_str_list,' ') )
    if not string.strip(start_path):
        start_path = None

    si = win32process.STARTUPINFO()
    if title:
        si.lpTitle = title
    win32process.CreateProcess(None, exec_str, None, None, 1, 0, os.environ, start_path, si)


def launchProcess(entry_name, app, args, start_path, sep_console=0, is_win32=False):
    cleaned = string.strip(app)
    if not cleaned:
        print "Path to application not given or blank"
        return

    if is_win32:
        exec_str_list = [app]
        for arg in args:
            exec_str_list.append('"%s"' % arg)
        exec_str = string.strip( string.join(exec_str_list,' ') )
        if not string.strip(start_path):
            start_path = None

        si = win32process.STARTUPINFO()
        si.lpTitle = entry_name

        if sep_console:
            handles = win32process.CreateProcess(None, exec_str, None, None, 1, win32process.CREATE_NEW_CONSOLE,os.environ, start_path, si)
        else:
            handles = win32process.CreateProcess(None, exec_str, None, None, 1, 0 ,os.environ, start_path, si)

        return handles
    else:
        stmt = 'cd %s; %s %s &' % (start_path, app, string.join(args,' '))
        fin = os.popen(stmt)
        fin.close()


# =============================================================================


quote_pat = re.compile(r'(\\?")')

# returns result, and number of substitutions
def escape_quote(s):
    counter = {'count':0}

    def sub(matchobj, counter=counter):
        it = matchobj.group()
        if it[0] == '\\':   # leave it alone, already escaping
            return it
        else:
            counter['count'] += 1
            return '\\"'

    return quote_pat.sub(sub, s),  counter['count']

# returns new_s
def rewrite_triple_quotes(s):
    pat = re.compile(r'"""(?P<string>.*?)"""', re.DOTALL)

    def sub(matchobj):
        s = matchobj.group('string')
        #s = string.replace(s, '"','\\"')
        s, _count = escape_quote(s)
        return '  "' + s + '"  ' #return id + padding       #TODO pad string to preserve spacing

    s = pat.sub(sub, s)
    return s

def rewrite_triple_quotes_shifting(s):
    pat = re.compile(r'"""(?P<string>.*?)"""', re.DOTALL)
    quote_pat = re.compile(r'"')

    # return (new_s, num_replaces)
    def count_replace(s):
        #s2, count = quote_pat.subn('\\"', s)
        #s2, count = quote_pat.subn(r'\"', s)                #TODO this is not enough; we may need to do escape_quote() on it, for smarter quoting, such as when there's already escaping going on
        s2, count = escape_quote(s)
        return s2, count

    d = {}  # start_pos -> count_replaces
    acc = [0]

    def sub(matchobj, d=d, count_replace=count_replace, acc=acc):
        s = matchobj.group('string')
        s, count = count_replace(s)
        acc[0] = acc[0] + count
        d[matchobj.start() + acc[0] ] = count
        return '  "' + s + '"  ' #return id + padding       #TODO pad string to preserve spacing

    s = pat.sub(sub, s)
    return s, d



def get_code_type(s):
    if string.find(s, '%::ERL::')>=0:
        return 'erl'
    elif string.find(s, '#::BASH::')>=0:
        return 'bash'
    elif string.find(s, ';::LFE::')>=0:
        return 'lfe'
    elif string.find(s, ';::CHICKEN::')>=0:     # clojure
        return 'chicken'
    elif string.find(s, ';::MZSCHEME::')>=0:     # clojure
        return 'mzscheme'
    elif string.find(s, ';::SISC::')>=0:
        return 'scm'
    elif string.find(s, '%::CLP::%')>=0:
        return 'ecl'
    elif string.find(s, '//::SCALA::')>=0:
        return 'scala'
    elif string.find(s, ';::CLJ::')>=0:     # clojure
        return 'clj'
    elif string.find(s, '#::PYTHON::')>=0:     # clojure
        return 'py'
    elif string.find(s, '! ::FACTOR::')>=0:
        return 'factor'
    elif string.find(s, 'NB. ::J::')>=0:
        return 'ijs'
    else:
        return ''


pytb_pat = re.compile(r'File "(?P<fname>[^"]+)", line (?P<line>[0-9]+), in')

def annotate_python_traceback(lines):
    final = []
    for line in lines:
        r = pytb_pat.search(line)
        if r:
            fname = r.group('fname')
            line_num = r.group('line')
            line = line + '        file://' + fname + '#' + line_num
        final.append(line)
    return final

sisctb_pat = re.compile(r'file:(?P<fname>[^:]+):(?P<line>[0-9]+):(?P<col>[0-9]+)')
def annotate_sisc_traceback(lines):
    final = []
    for line in lines:
        if string.find(line, 'SchemeException: sisc.interpreter.SchemeException:')>=0:
            r = sisctb_pat.search(line)
            if r:
                fname = r.group('fname')
                line_num = r.group('line')
                col_num = r.group('col')
                line = line + '        file://' + fname + '#' + line_num
                final.append(line)
                continue

        final.append(line)
    return final


scalatb_pat = re.compile('^(?P<path>[^:]+):(?P<line>[0-9]+):(?P<kind>[^:]+):(?P<message>.+)')

def annotate_scala_traceback(lines):
    final = []
    for line in lines:
        r = scalatb_pat.search(line)
        if r:
            path = r.group('path')
            line_num = r.group('line')
            line = line + '        file://' + path + '#' + line_num
        final.append(line)
    return final


def get_num_leading_spaces(line):
    r = spaces_pat.match(line)
    if r:
        spaces = r.group('spaces')
        return len(spaces)
    else:
        return 0

def get_indentation(line, base_indent_size = BASE_INDENT_SIZE):
    return get_num_leading_spaces(line) / base_indent_size


# direction:
#   -1     = only go backward (including current)
#   other  = forward and backward
# returns (s, start_row, end_row)

def get_all_same_indent(vim, direction=0, base_indent_size = BASE_INDENT_SIZE ):
    start_line_num = int(vim.eval('line(".")'))-1       # line numbering starts at 1, but indexing starts at 0

    buff = vim.current.buffer
    max = len(buff)

    start_indent = get_indentation(buff[start_line_num], base_indent_size = base_indent_size)
    if start_indent == 0: return '', -1, -1

    # go backward
    i = start_line_num - 1
    while i>=0:
        line = buff[i]
        indent = get_indentation(line, base_indent_size = base_indent_size)
        if indent != start_indent:
            break
        i -= 1

    real_start = i+1

    if direction == -1:     # only going backward
        max = start_line_num


    all = []
    for i in xrange(real_start, max):
        line = buff[i]
        indent = get_indentation(line, base_indent_size = base_indent_size)
        if indent != start_indent:
            break

        all.append(line)

    return string.join(all, '\n'), real_start, i


# direction:
#   -1     = only go backward (including current)
#   other  = forward and backward
# returns (s, start_row, end_row)

def get_all_same_indent_looser(vim, direction=0):
    start_line_num = int(vim.eval('line(".")'))-1       # line numbering starts at 1, but indexing starts at 0

    buff = vim.current.buffer
    max = len(buff)

    start_indent = get_indentation(buff[start_line_num])
    if start_indent == 0: return '', -1, -1

    # go backward
    i = start_line_num - 1
    while i>=0:
        line = buff[i]
        indent = get_indentation(line)
        if indent < start_indent:
            break
        i -= 1

    real_start = i+1

    if direction == -1:     # only going backward
        max = start_line_num


    all = []
    for i in xrange(real_start, max):
        line = buff[i]
        indent = get_indentation(line)
        if indent < start_indent:
            break

        all.append(line)

    return string.join(all, '\n'), real_start, i


def clean_j_value(r):
    if r == '':
        return []

    if r and type(r[0]) == types.ListType and len(r) == 1:
        return r[0]
    else:
        return r


def dump_exception_new_tab(vim):
    vim.check_exit_condition()

    buff = cStringIO.StringIO()
    traceback.print_exc(file=buff)
    parts = string.split(buff.getvalue(), '\n')
    parts = annotate_python_traceback(parts)
    parts = annotate_sisc_traceback(parts)

    vim.open_new_tab(general.mklocaltemp() + '.mind')

    new_buffer = vim.current.buffer
    new_buffer[:] = parts
    vim.command("set nomodified")


# sends code to j; result (which is a string) is ready for printing
def callj(vim, s):
    from hsdl.vim import vim_emulator_jtext
    is_jtext = isinstance(vim, vim_emulator_jtext.VimEmulatorJText)

    s = string.strip(s)
    try:
        if is_jtext:
            from hsdl.java import javajlib
            z = javajlib.jeval(s, as_string=1)
        else:
            from hsdl.j import jlib
            z = jlib.jeval(s, as_string=1)
        #z = franca_comm.send_action_franca('j', ['eval_all_string',s], port=15015, machine='worlddb')
        return z
    except franca_comm.FrancaException, e:
        vim.check_exit_condition()
        if vim is None:
            raise e
        else:
            buff = cStringIO.StringIO()
            traceback.print_exc(file=buff)
            parts = string.split(buff.getvalue(), '\n')
            parts = annotate_python_traceback(parts)

            vim.open_new_tab(general.mklocaltemp() + '.mind')

            new_buffer = vim.current.buffer
            new_buffer[:] = parts
            vim.command("set nomodified")



# sends code to j; result is data structure
def callj_value(vim, s):
    s = string.strip(s)
    #z = franca_comm.send_action_franca('j', ['eval',s], port=15015, machine='worlddb')
    jlib = get_jlib(vim)
    z = jlib.jeval(s)
    return clean_j_value(z)

def jexists(varname):
    from hsdl.vim import vim_emulator_jtext
    is_jtext = isinstance(vim, vim_emulator_jtext.VimEmulatorJText)

    try:
        if is_jtext:
            from hsdl.java import javajlib
            _ = javajlib.jeval(s)
        else:
            from hsdl.j import jlib
            _ = jlib.jeval(varname, silent=1)
        return 1
    except:
        return 0

# sends code to j; result is data structure
def callj_value_binary(vim, s):
    s = string.strip(s)
    z = franca_comm.send_action_franca('j', ['eval_binary',s], port=15015, machine='worlddb')
    return z #clean_j_value(z)

# sends string to j; default global variable name is 'MAIN_S'
def sendjdata(vim, value, do_unprotect=False, tempvar='MAIN_S'):
    jlib = get_jlib(vim)
    z = jlib.jset(tempvar, value)
    return z


# sends string to scala
def scala_eval(vim, s):
    z = franca_comm.send_action_franca('scala', ['scala-eval', s], port=15003, machine='worlddb')
    return z

# note: it's actually handled by the jython service
def send_to_sisc(vim, s):
    try:
        z = franca_comm.send_action_franca('jython', ['sisc', s], port=15003, machine='worlddb')
        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
def get_sisc_env(vim):
    try:
        z = franca_comm.send_action_franca('jython', ['sisc-env'], port=15003, machine='worlddb')
        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
# dict: key -> string_value
def set_sisc_env(vim, dict):
    try:
        z = franca_comm.send_action_franca('jython', ['sisc-set-env', dict.items()], port=15003, machine='worlddb')
        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
def sisc_clean_temp(vim):
    try:
        z = franca_comm.send_action_franca('jython', ['sisc-clean-temp'], port=15003, machine='worlddb')
        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
# NOTE::: Do not attempt to call open_new_tab() when in the middle of completion, such as what we would like
#   to do here with there's an exception. This causes vim to SEGV.

# note: it's actually handled by the jython service
def sisc_rewrite_exec(vim, s, catch_exception=1):
    if catch_exception:
        try:
            z = franca_comm.send_action_franca('jython', ['sisc-rewrite-exec', s], port=15003, machine='worlddb')
            return z
        except:
            dump_exception_new_tab(vim)
    else:
        z = franca_comm.send_action_franca('jython', ['sisc-rewrite-exec', s], port=15003, machine='worlddb')
        return z


# note: it's actually handled by the jython service
def sisc_rewrite_show_data(vim, s, catch_exception=1):
    if catch_exception:
        try:
            z = franca_comm.send_action_franca('jython', ['sisc-rewrite-show-data', s], port=15003, machine='worlddb')
            return z
        except:
            dump_exception_new_tab(vim)
    else:
        z = franca_comm.send_action_franca('jython', ['sisc-rewrite-show-data', s], port=15003, machine='worlddb')
        return z

# note: it's actually handled by the jython service
def lisp_rewrite_action(vim, s):
    from hsdl.cl import genlisp
    genlisp.start_lisp()
    genlisp.vim_prepare("/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp")
    r = genlisp.apply_ecl("get-code-actions", ['(===' + s + ')' ])
    r = map(lambda tup: string.lower(tup[0]), r)
    r.sort()
    return r



# note: it's actually handled by the jython service
# NOTE: vim_command.action_helper() would like to take care of the exception handling itself
def lisp_execute_action(vim, s, catch_exception=1):
    from hsdl.cl import genlisp
    genlisp.start_lisp()
    genlisp.vim_prepare("/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp")

    #s = string.replace(s, '(@@@@@ ', '( ')
    #s = string.replace(s, " put-after-here ", ' 3333  @@@@@ ')

    r = genlisp.apply_ecl("sarino-for-action", ["(=== " + s + ")"])

    print "==========================================================================================="
    print r[0]
    print "==========================================================================================="
    if 0:
        if shared.DEBUG_ON:
            r = genlisp.apply_ecl("vim-exec-action-debug", [s])
        else:
            r = genlisp.apply_ecl("vim-exec-action", [s])

    return r[0]



# note: it's actually handled by the jython service
def sisc_vim_sexp(vim, s_pickled):
    try:
        z = franca_comm.send_action_franca('jython', ['sisc-vim-sexp', s_pickled], port=15003, machine='worlddb')
        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
def sisc_vim_sexp_match(vim, s_list, concise=0):
    try:
        z = franca_comm.send_action_franca('jython', ['sisc-vim-sexp-match', concise, s_list], port=15003, machine='worlddb')

        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
def sisc_vim_sexp_match_regular(vim, code, concise=0):
    try:
        z = franca_comm.send_action_franca('jython', ['sisc-vim-sexp-match-regular', concise, code], port=15003, machine='worlddb')

        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
def sisc_vim_sexp_match_multiple(vim, code, concise=0):
    try:
        z = franca_comm.send_action_franca('jython', ['sisc-vim-sexp-match-multiple', concise, code], port=15003, machine='worlddb')

        return z
    except:
        dump_exception_new_tab(vim)


# note: it's actually handled by the jython service
def lfe_execute_action(vim, s):
    try:
        z = franca_comm.send_action_franca('jython', ['lfe-execute-action', s], port=15003, machine='worlddb')
        return z
    except:
        dump_exception_new_tab(vim)


# note: it's actually handled by the jython service
def scala_type_at(vim, fname, pos):
    try:
        z = franca_comm.send_action_franca('jython', ['scala-typeAt', fname, pos], port=15003, machine='worlddb')
        return z
    except:
        dump_exception_new_tab(vim)


# note: it's actually handled by the jython service
def scala_complete(vim, fname, pos):
    try:
        z = franca_comm.send_action_franca('jython', ['scala-complete', fname, pos], port=15003, machine='worlddb')
        z.sort()
        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
def scala_complete_import(vim, path_list):
    try:
        z = franca_comm.send_action_franca('jython', ['scala-complete-import', path_list], port=15003, machine='worlddb')
        z.sort()
        return z
    except:
        dump_exception_new_tab(vim)


# note: it's actually handled by the jython service
def java_complete_import(vim, path_list):
    try:
        z = franca_comm.send_action_franca('jython', ['java-complete-import', path_list], port=15003, machine='worlddb')
        z.sort()
        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
def scala_compiler_set_files(vim, path_list):
    try:
        franca_comm.send_action_franca('jython', ['scala-compiler-set-files', path_list], port=15003, machine='worlddb')
    except:
        dump_exception_new_tab(vim)

# -- subclassing so that we can override the __del__ method, to close the connection on cleanup
class MyTelnet(telnetlib.Telnet):
    def __init__(self, host, port=9999):
        telnetlib.Telnet.__init__(self, host, port)

    def __del__(self):
        try:
            print self.close()  # This always generates this error: Exception exceptions.TypeError: "'NoneType' object is not callable" in <bound method MyTelnet.__del__ of <hsdl.vim.jcommon.MyTelnet instance at 0x1ce0b48>> ignored
        except:
            pass

# note: it's actually handled by the jython service
def scala_compiler_update(vim):
    try:
        z = franca_comm.send_action_franca('jython', ['scala-compiler-update'], port=15003, machine='worlddb')
        z.sort()
        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
def lfe_get_completers(vim, s):
    try:
        z = franca_comm.send_action_franca('jython', ['lfe-get-completers', s], port=15003, machine='worlddb')
        return z
    except:
        dump_exception_new_tab(vim)

# note: it's actually handled by the jython service
# NOTE::: Do not attempt to call open_new_tab() when in the middle of completion, such as what we would like
#   to do here with there's an exception. This causes vim to SEGV.
def lfe_rewrite_complete(vim, s, prefix):
    z = franca_comm.send_action_franca('jython', ['lfe-rewrite-complete', s, prefix], port=15003, machine='worlddb')
    return z

def old_lisp_complete(vim, prefix):
    #if not shared.SLIME_MAN:
    from hsdl.vim import slime_client


    shared.SLIME_MAN = slime_client.SlimeManager('localhost', 4005)

    try:
        r = shared.SLIME_MAN.simple_completions(prefix)
        shared.SLIME_MAN.close()
        return r

    except:
        shared.SLIME_MAN.close()
        dump_exception_new_tab(vim)


def lisp_complete(vim):
    fin = open("/tech/hsdl/play/cl/LISP_NAMES.txt", 'rb')
    names = string.split(fin.read())
    fin.close()
    return names


def slime_lisp_eval(vim, code):
    #if not shared.SLIME_MAN:
    from hsdl.vim import slime_client
    reload(slime_client)

    shared.SLIME_MAN = slime_client.SlimeManager('localhost', 4005)

    try:
        r = shared.SLIME_MAN.interactive_eval(code)
        shared.SLIME_MAN.close()
        return r
    except:
        shared.SLIME_MAN.close()
        dump_exception_new_tab(vim)

def lisp_eval(vim, code):
    #if not shared.SLIME_MAN:
    from hsdl.cl import genlisp
    genlisp.start_lisp()
    genlisp.vim_prepare("/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp")
    s = genlisp.apply_ecl("eval-simple", [code])
    return s

def describe_symbol(vim, sym):
    #if not shared.SLIME_MAN:
    from hsdl.vim import slime_client
    reload(slime_client)

    shared.SLIME_MAN = slime_client.SlimeManager('localhost', 4005)

    try:
        r = shared.SLIME_MAN.describe_symbol(sym)
        shared.SLIME_MAN.close()
        return r
    except:
        shared.SLIME_MAN.close()
        dump_exception_new_tab(vim)

def describe_function(vim, name):
    #if not shared.SLIME_MAN:
    from hsdl.vim import slime_client
    reload(slime_client)

    shared.SLIME_MAN = slime_client.SlimeManager('localhost', 4005)

    try:
        r = shared.SLIME_MAN.describe_function(name)
        shared.SLIME_MAN.close()
        return r
    except:
        shared.SLIME_MAN.close()
        dump_exception_new_tab(vim)

def disassemble_symbol(vim, sym):
    #if not shared.SLIME_MAN:
    from hsdl.vim import slime_client
    reload(slime_client)

    shared.SLIME_MAN = slime_client.SlimeManager('localhost', 4005)

    try:
        r = shared.SLIME_MAN.disassemble_symbol(sym)
        shared.SLIME_MAN.close()
        return r
    except:
        shared.SLIME_MAN.close()
        dump_exception_new_tab(vim)

def apropos_list_for_emacs(vim, word):
    #if not shared.SLIME_MAN:
    from hsdl.vim import slime_client
    reload(slime_client)

    shared.SLIME_MAN = slime_client.SlimeManager('localhost', 4005)

    try:
        r = shared.SLIME_MAN.apropos_list_for_emacs(word)
        shared.SLIME_MAN.close()
        return r
    except:
        shared.SLIME_MAN.close()
        dump_exception_new_tab(vim)


def lisp_display_info(vim, lines, orig_cursor=()):
    # some individual lines may contain '\n'; vim will complain, so let's clean them up
    lines = string.split(string.join(general.flatten(map(lambda each: string.split(each, '\n'), lines)), '\n'), '\n')

    path = vim.current.buffer.name
    tempfname = general.local_hsdl_mktemp('LISP__') + '.mind'

    vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='LISP__')     # if another already exists within the sa

    buffer = vim.current.buffer
    size = len(buffer[:])

    buffer[size:size+1] = lines + ['-'*80]
    vim.command("set nomodified")
    vim.command("normal G")
    vim.command(":vertical resize 50")

    vim.go_to_opened_buffer(path)

    if orig_cursor:
        vim.current.window.cursor = orig_cursor

def lisp_compile_file(vim, path, load=0):
    #if not shared.SLIME_MAN:
    from hsdl.vim import slime_client
    reload(slime_client)

    shared.SLIME_MAN = slime_client.SlimeManager('localhost', 4005)

    try:
        r = shared.SLIME_MAN.compile_file_for_emacs(path, load=load)
        shared.SLIME_MAN.close()
        return r
    except:
        shared.SLIME_MAN.close()
        dump_exception_new_tab(vim)


# note: it's actually handled by the jython service
def get_clojure_env(vim, prefix):
    try:
        z = franca_comm.send_action_franca('jython', ['clojure-env', prefix], port=15003, machine='worlddb')
        return z
    except:
        dump_exception_new_tab(vim)

def init_factor():
    if shared.FACTOR_TELNET:
        return shared.FACTOR_TELNET
    else:
        #tn = telnetlib.Telnet("localhost", 9999)
        tn = MyTelnet("localhost", 9999)
        tn.read_until("( scratchpad )")

        shared.FACTOR_TELNET = tn

        return tn

def close_factor():
    if shared.FACTOR_TELNET:
        tn = shared.FACTOR_TELNET
        tn.close()

# note: it's actually handled by the jython service
def factor_eval(vim, s):
    try:
        tn = init_factor()
        tn.write(s + "\n")
        r = tn.read_until("( scratchpad )")
        return r
    except:
        dump_exception_new_tab(vim)

def clojure_eval(vim, s):
    try:
        r = franca_comm.send_action_franca('jython', ['clojure-eval', s], port=15003, machine='worlddb')
        return r
    except:
        dump_exception_new_tab(vim)


def extract_form_head(s):
    s = string.replace(s,'(', ' ')
    s = string.replace(s,')', ' ')

    pat = re.compile(r'[^ ()]+')

    r = pat.search(s)
    if r:
        return r.group()
    else:
        return ''


def read_prelude_actions():
    fname = "/tech/frontier/notes/mind/prelude-actions.scm"
    final = []

    if os.path.exists(fname):
        fin = open(fname, 'rb')
        s = fin.read()
        fin.close()

        pat = re.compile(r'^\s*\(\s*define\s+(?P<name>__[a-zA-Z0-9-]+__)')

        lines = string.split(s, '\n')

        for line in lines:
            r = pat.match(line)
            if r:
                final.append(r.group('name'))
    return final




# note that args represent the args from the command-line, not the varargs when this function is called
def find_lisp_actions(vim, _head_arg=''):
    from hsdl.vim import vim_commands
    reload(vim_commands)

    orig_cur = vim.current.window.cursor

    def action_fun(action_name, arg_as_str):
        return '( ' + action_name + ' @@@@@  ' + arg_as_str + ' ) '

    r = vim_commands.action_base_helper(vim, action_fun)
    if not r: return

    new_s, action_name, action_code, action_start_line, action_start_col, action_end_line, action_end_col = r

    r = lisp_rewrite_action(vim, new_s)
    if r is None:   # likely an error
        r = []
    else:
        r.sort()

    vim.current.window.cursor = orig_cur

    r = r + read_prelude_actions()
    return r




# finds the non-list expression at pos
def extract_scheme_expr(s, pos):
    from hsdl.schemepy.skime.compiler.parser import Parser
    from hsdl.schemepy.skime.errors import ParseError
    from hsdl.schemepy.skime.types.pair import Pair
    lines = string.split(s, '\n')
    lines = ignore_special_lines(lines)
    s = string.join(lines, '\n')
    p = Parser(s)
    p.parse()

    smallest_range_size = sys.maxint
    smallest_begin = -1
    smallest_end = -1
    smallest_obj = None
    for (begin, end), obj in p.registry.items():
        if pos>=begin and pos<=end:
            size = end-begin+1
            if size < smallest_range_size:
                smallest_range_size = size
                smallest_begin = begin
                smallest_end = end
                smallest_obj = obj

    if (not smallest_obj is None):
        obj = smallest_obj
        if isinstance(obj, Pair):
            if s[pos] == '(':
                return obj, smallest_begin, smallest_end
            else:
                return obj.car, smallest_begin, smallest_end
            pass
        else:
            return obj, smallest_begin, smallest_end

    return None, -1, -1


def send_to_clp(vim, s):
    z = franca_comm.send_action_franca('python', ['process_eclipse_clp', s], port=15003, machine='localhost')
    return z

marker_pat = re.compile(r"^\s*((@\+)|(@@)|(<<)).*")

DATA_TAG = chr(30)
USE_DATA_TAGS = 0

def ignore_special_lines(lines):
    if USE_DATA_TAGS:
        final = []
        for line in lines:
            r = marker_pat.match(line)
            if string.find(line, DATA_TAG)<0 and (r is None):
                final.append(line)
        return final
    else:
        return lines    # no need to ignore because we don't tag them anymore

def tag_data_lines(lines):
    if USE_DATA_TAGS:
        final = []
        for line in lines:
            if string.strip(line):
                final.append(line + "  " + DATA_TAG + DATA_TAG)
            else:
                final.append(line)
        return final
    else:
        return lines    # don't tag anymore


def quote_j(line):
    indent = get_indentation(line)
    line = string.strip(line)
    line = "'" + string.replace(line, "'", "''") + "'"
    return indent_lines([line], indent)[0]


def unquote_j(line):
    indent = get_indentation(line)
    orig_line = line
    line = string.strip(line)
    if not line:
        return orig_line

    if line[0]=="'":
        line = line[1:]
    if line[-1] == "'":
        line = line[:-1]
    line = string.replace(line, "''", "'")
    return indent_lines([line], indent)[0]


def indent_lines(all, indent, preserve_blank_lines=0):
    final = []
    for each in all:
        if string.strip(each) or preserve_blank_lines:
            #final.append('    ' + each)
            final.append((BASE_INDENT_SPACES*indent) + each)
        else:
            final.append('')
    return final

# keeps the first line unindented; does not use space multiple
def indent_lines_low_level(all, indent, preserve_blank_lines=0):
    if not all:
        return []

    final = []
    for each in all:
        if string.strip(each) or preserve_blank_lines:
            final.append((' '*indent) + each)
        else:
            final.append('')
    return final


leading_spaces_pat = re.compile(r'^(\s*)')
def dedent_lines(all, dedent=1):
    num_spaces = BASE_INDENT_SIZE*dedent
    final = []
    for each in all:
        r = leading_spaces_pat.match(each)
        if r:
            if len(r.group()) >= num_spaces:            # can dedent the required number of spaces
                final.append(each[num_spaces:])
            else:
                final.append(each[len(r.group()):])     # dedent only what's available
        else:
            final.append(each)                          # no leading spaces at all; just add line
    return final


# dedent lines all the way
def dedent_lines_common(all):
    min_indent = sys.maxint
    for line in all:
        if not string.strip(line): continue
        r = leading_spaces_pat.match(line)
        indent = len(r.group())
        if indent < min_indent:
            min_indent = indent

    if min_indent>0:
        all = map(lambda line: line[min_indent:], all)

    return all

ref_pat = re.compile(r"""(?P<protocol>[a-z]+)://(?P<path>[^ '"()]+)""")
def extract_references(line):
    all = []

    p = 0
    while 1:
        r = ref_pat.search(line, p)
        if r:
            protocol = r.group('protocol')
            path = r.group('path')
            all.append( (r.group(), protocol, path) )

            p = r.end()
        else:
            break

    return all


quickie_pat = re.compile(r'(\(\+(?P<choice1>[^)]+)\))|((^|\s)\+(?P<choice2>[^ ]+))')
def extract_quickies(line):
    all = []

    p = 0
    while 1:
        r = quickie_pat.search(line, p)
        if r:
            choice1 = r.group('choice1')
            choice2 = r.group('choice2')
            if choice1:
                all.append(choice1)
            if choice2:
                all.append(choice2)
            p = r.end()
        else:
            break

    return all


# when a linux path is opened in win32, and vice versa
def adapt_path(path, is_win32=False):
    path = general.interpolate_filename(path)
    cleaned = string.replace(path, '\\', '/')
    prefix = string.replace(os.getenv("MAIN_ROOT"), '\\', '/')

    if string.find(cleaned, prefix)==0:
        return path
    else:
        if is_win32:
            if path[:6] == '/tech/':
                return os.path.join('h:', path[5:])
            else:
                return path
        else:
            if len(path)>1 and path[1] == ':':
                return os.path.join('/tech', path[3:])      # drop 'h:/'
            else:
                return path

def get_foldlevel(vim):
    line = vim.current.line
    if string.strip(line):
        r = spaces_pat.search(line)
        if r:
            spaces = r.group('spaces')
            return len(spaces) / 4

    return 0

# special function is case we have to deal with zip files
def path_matches(path, to_find):
    # path can be of the form /path/a/b/c/::/subpath/a/b/c.txt
    parts = string.split(path, '::')
    if len(parts) == 2:
        return parts[-1] == to_find
    else:
        return path == to_find


def is_vim_emulator(vim):
    from hsdl.vim import vim_emulator
    return (vim is None) or isinstance(vim, vim_emulator.VimEmulator)

def is_vim_emulator_jtext(vim):
    from hsdl.vim import vim_emulator_jtext
    return isinstance(vim, vim_emulator_jtext.VimEmulatorJText)

# ----------------------------------------------------
def show_interactive_completer(vim):
    curr_path = vim.current.buffer.name
    vim.open_new_split('/tmp/completer', vertical=1, unique=1, unique_prefix='COMPL__')     # if another already exists within the sa
    vim.go_to_opened_buffer(curr_path)

def update_interactive_completer(vim, frag, choice_dir=0, use_choice=0):
    display_fun = shared.INTERACT_DISPLAY_FUN
    lisp_display_fun = shared.INTERACT_LISP_DISPLAY_FUN

    if display_fun or lisp_display_fun:
        if not shared.snip_prefix is None:
            frag = shared.snip_prefix

        if lisp_display_fun:
            from hsdl.cl import genlisp
            #genlisp.vim_ecl_lazy_load()     #!!!
            genlisp.start_lisp()     #!!!
            entries = genlisp.apply_ecl(lisp_display_fun, [frag, ''])
        else:
            entries  = display_fun(frag, {})

        choice_str = ''
        choice = shared.INTERACT_CHOICE
        choice += choice_dir

        if choice==-1:
            choice = -1
            choice_str = frag
        elif choice<-1:
            choice = len(entries)-1
            choice_str = frag
        elif choice >= len(entries):
            choice = -1
            choice_str = frag
        else:
            if entries:
                choice_str = entries[choice]
            else:
                choice_str = ''

        if choice>-1:
            if shared.INTERACT_CHOOSE_FUN:
                shared.INTERACT_CHOOSE_FUN(entries)
            else:
                if entries:
                    entries[choice] = entries[choice] + '  <<'

        shared.INTERACT_CHOICE = choice

        z = string.join(entries, '\n')
        z = string.replace(z, 'siquasiquote', repr(random.random()))    #!!!
        entries = string.split(z, '\n')


        if use_choice and choice_str:
            buffer = vim.current.buffer
            line = vim.current.line
            curr_line, curr_col = vim.current.window.cursor
            before = shared.snip_orig_line_str[:shared.snip_start_col]
            after = shared.snip_orig_line_str[shared.snip_start_col:]
            #new_line = before + choice_str + " " + str(curr_col) + " : " + str(len(choice_str)) + " " + after
            new_line = before + choice_str + after
            buffer[curr_line-1] = new_line
            vim.current.window.cursor = curr_line, shared.snip_start_col + len(choice_str) - 1

        curr_path = vim.current.buffer.name
        the_buff = vim.go_to_opened_buffer('/tmp/completer')
        if the_buff:
            lines = entries
            vim.current.buffer[:] = [''] + lines        # there's always a blank first line
            vim.go_to_opened_buffer(curr_path)


def start_interactive_completion(vim, display_fun=None, choose_fun=None, lisp_display_fun=None, lisp_choose_fun=None, enable_select=1):
    from hsdl.vim import shared
    shared.snip_curr_name = (1, 'whatever')

    orig_cur = vim.current.window.cursor
    orig_line, orig_col = orig_cur

    shared.INTERACT_CHOICE = -1

    shared.INTERACT_DISPLAY_FUN = display_fun
    shared.INTERACT_CHOOSE_FUN = choose_fun

    shared.INTERACT_LISP_DISPLAY_FUN = lisp_display_fun
    shared.INTERACT_LISP_CHOOSE_FUN = lisp_choose_fun

    shared.INTERACT_ENABLE_SELECT = enable_select

    shared.snip_start_col = orig_col
    shared.snip_start_line = orig_line
    shared.snip_orig_line = orig_line
    shared.snip_template = []
    shared.snip_bindings = {}
    shared.snip_orig_line_str = vim.current.line
    shared.snip_prefix = None

    shared.snip_on = 1
    shared.snip_do_update = 0

    vim.command("call SetCheckCursorMoved()")
    vim.enter_insert_mode()

    show_interactive_completer(vim)
    update_interactive_completer(vim, '')       # when starting out, the selection is ''

    vim.command("imap <tab> <esc>:py from hsdl.vim import jinteractive; jinteractive.snippets_jump(vim, dir=1)<cr>")
    vim.command("imap <s-tab> <esc>:py from hsdl.vim import jinteractive; jinteractive.snippets_jump(vim, dir=-1)<cr>")
    vim.command("smap <tab> <esc>:py from hsdl.vim import jinteractive; jinteractive.snippets_jump(vim, dir=1)<cr>")
    vim.command("smap <s-tab> <esc>:py from hsdl.vim import jinteractive; jinteractive.snippets_jump(vim, dir=-1)<cr>")
    vim.command("smap <C-D>  <ESC>:call UnsetCheckCursorMoved()<CR>")
    vim.command("imap <C-D>  <ESC>:call UnsetCheckCursorMoved()<CR>")

    # NOTE: because we use <ESC> to execute command, it will kick us out of insert mode;
    # so, you'll need to move caret to the right and re-enter insert mode to continue
    vim.command("map <C-N>  <ESC>:py from hsdl.vim import jinteractive; jinteractive.interactive_completion_select_down(vim)<CR>")
    vim.command("imap <C-N>  <ESC>:py from hsdl.vim import jinteractive; jinteractive.interactive_completion_select_down(vim)<CR>")
    vim.command("map <C-P>  <ESC>:py from hsdl.vim import jinteractive; jinteractive.interactive_completion_select_up(vim)<CR>")
    vim.command("imap <C-P>  <ESC>:py from hsdl.vim import jinteractive; jinteractive.interactive_completion_select_up(vim)<CR>")



# ----------------------------------------------------



# similar to indentation, but using exact col number; returns string
# all includes the first line; by default, the first line is left unindented
def string_shift_col(s, col_size, all=0):
    lines = string.split(s, '\n')
    if lines:
        if all:
            lines = map(lambda line: (' '*col_size) + line,  lines)
        else:
            lines = [lines[0]] + map(lambda line: (' '*col_size) + line,  lines[1:])

    return string.join(lines, '\n')



# returns start_row, end_row, start_col, end_col
def get_initial_selection(vim):
    buff = vim.current.buffer

    tup1, tup2 = shared.INITIAL_SELECTION
    if not tup1 or not tup2:
        line_num, col_num = vim.current.window.cursor
        return line_num, line_num, vim.current.line

    if tup1[0] == -1 or tup2[0] == -1:
        return -1, -1, -1, -1, ''

    start, col_start  = tup1
    end, col_end = tup2

    if start and end:
        final = []
        for i in xrange(start-1, end):
            line = vim.current.buffer[i]
            final.append(line)
        return start, end, string.join(final, '\n')
    else:
        return start_row, end_row, ''

full_pat = re.compile('\S?(?P<whatever>[^\s]+)\S?')
leading_non_completion_pat = re.compile(r'^\W*')
trailing_non_completion_pat = re.compile(r'[^a-zA-Z0-9_.:-]*$')


# finds word at this col; if not found, return ''
def find_word(line, col, for_completion=0):
    the_word = ''
    i = 0
    while 1:
        r = full_pat.search(line, i)
        if r:
            start = r.start()
            end = r.end()
            if col>=start and col<=end:
                the_word = r.group()
                break
            i = end
        else:
            break

    if for_completion:
        # remove leading non-alphanumeric characters
        return trailing_non_completion_pat.sub('', leading_non_completion_pat.sub('', the_word))
    else:
        return the_word

# finds word at or before this col; if not found, return ''
def find_word_before(line, col):
    if line[col] == ' ':
        i = col
        while i>=0 and line[i] == ' ':
            i -= 1
        col = i

    the_word = ''
    i = 0
    while 1:
        r = full_pat.search(line, i)
        if r:
            start = r.start()
            end = r.end()
            if col>=start and col<=end:
                the_word = r.group()
                break
            i = end
        else:
            break

    return the_word

def find_next_word(s, start):
    pat = re.compile(r'[a-zA-Z0-9_]')

    size = len(s)
    i = start
    while i < size:
        r = pat.search(s[i])
        if not r:
            break
        i += 1

    return s[start:i]



# NOTE: tooltip is only triggered when the mouse hovers over a word
def tooltip(vim):
    global SIGN_DICT, TOOLTIP_DICT

    bufnr = int(vim.eval("v:beval_bufnr"))
    winnr = int(vim.eval("v:beval_winnr"))
    lnum = int(vim.eval("v:beval_lnum"))
    col = int(vim.eval("v:beval_col")) - 1
    text = vim.eval("v:beval_text")

    line = vim.current.buffer[lnum-1]
    the_word = find_word(line, col)

    message = ''
    if SIGN_DICT.has_key(lnum-1):
        _, message = SIGN_DICT[lnum-1]

    if TOOLTIP_DICT.has_key(lnum-1):
        this_word = string.lower(the_word)
        if this_word and this_word[0] == '+':
            this_word = this_word[1:]
        if TOOLTIP_DICT[lnum-1].has_key(this_word):
            message = TOOLTIP_DICT[lnum-1][this_word]

    if the_word and message:
        #_, message = SIGN_DICT[lnum-1]

        all = []
        all.append('='*50)
        all.append(message)
        all.append('='*50)
        all.append('')
        all.append("INFO:")
        all.append("  bufnr=" + str(bufnr))
        all.append("  winnr=" + str(winnr))
        all.append("  lnum=" + str(lnum))
        all.append("  col=" + str(col))
        all.append("  text=" + text)
        all.append("  the_word=" + the_word)
        all.append("My tooltip: " + str(random.random()))

        text = string.join(all, '\n')

        vim.command(":let g:balloon_returning='" + string.replace(text, "'", "\\'") + "'")
    else:
        vim.command(":let g:balloon_returning=''")


def add_line_tooltip(vim, line, col, message):
    SIGN_DICT[line] = (col, message)


def add_word_tooltip(vim, line, word, message):
    if not TOOLTIP_DICT.has_key(line):
        TOOLTIP_DICT[line] = {}
    dict = TOOLTIP_DICT[line]

    dict[word] = message



# if main_indent is None, that means we ignore indentation
def separate_code_lines(main_indent, lines):
    immed = []

    pat = re.compile(r'NB.\s+\[\[(?P<name>[a-z_A-Z0-9-]+)\]\]')

    dict = {}       # func_name -> lines

    last_func_name = ''
    for line in lines:
        indent = get_indentation(line)
        if (main_indent is None) or (indent == main_indent):
            r = pat.search(line)
            if r:
                func_name = r.group('name')
                if not dict.has_key(func_name):
                    dict[func_name] = []

                rest = pat.sub('', line)
                rest2 = string.strip(rest)
                if rest2:
                    dict[func_name].append(rest)

                last_func_name = func_name
            else:
                immed.append(line)

        elif indent > main_indent:       # subsidiary code
            if last_func_name:
                dict[last_func_name].append(line)

        elif indent < main_indent:
            last_func_name = ''

    dict2 = {}
    for func_name, func_lines in dict.items():
        dict2[func_name] = string.join(func_lines, '\n')

    return immed, dict2


# replace a part of a list of strings starting at line and col
def lines_replace_string(lines, line1, col1, line2, col2, new_str):
    start = lines[line1][:col1]
    end = lines[line2][col2+1:]
    mid = string.split(new_str, '\n')
    num_lines = len(mid)
    if num_lines > 1:
        lines[line1:line2+1] = [start + mid[0]] + mid[1:-1] + [mid[-1] + end]
    elif num_lines == 1:
        lines[line1:line2+1] = [start + mid[0] + end]


# content can be string or list of strings
# returns temp file name
def dump_new_tab(vim, content, modified=False, set_folding=1):
    if shared.FROM_COMMAND_LINE:
        for line in content:
            print line
    else:
        fname = general.mklocaltemp() + '.mind'
        vim.open_new_tab(fname, set_folding=set_folding)

        new_buffer = vim.current.buffer
        if type(content) == types.ListType:
            new_buffer[:] = content
        else:
            lines = string.split(content, '\n')
            new_buffer[:] = lines

        if not modified:
            vim.command("set nomodified")

        return fname

def vim_command(vim, cmd):
    # if called from command line, vim doesn't really apply, so do nothing
    if shared.FROM_COMMAND_LINE:
        pass
    else:
        return vim.command(cmd)

hier_pat = re.compile(r'{:(?P<query>[^:]+):}')
python_ref_pat = re.compile(r'(?P<ref>[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+)\(')


def replace_vim_lines(buff, start_row, end_row, final):
    if len(final) + start_row == end_row:
        buff[start_row:end_row] = final
    else:
        buff[start_row:end_row+1] = final



# background_only means don't execute the script through a terminal
def proc(s, prompt=1, floater=1, detach=0, title='mrxvt_floater', background_only=0):
    from hsdl.common import general


    # -- this is the temp script name
    tempfname = general.local_hsdl_mktemp()

    if prompt:
        footer = "\n echo '----------- DONE ------------'\nread\nrm %s\n" % tempfname
    else:
        footer = "\nrm %s\n" % tempfname

    fout = open(tempfname, 'wb')

    fout.write(s + footer)
    fout.close()

    the_fun = os.popen
    if detach:
        the_fun = os.popen2

    if background_only:
        proc = the_fun("bash " + tempfname)
    elif floater:
        proc = the_fun('mrxvt -maximized -t "%s" -e bash %s' % (title, tempfname))
    else:
        proc = the_fun('mrxvt -maximized -t "%s" -e bash %s' % (title, tempfname))

    if not detach:
        proc.close()


def proc2(s, prompt=1, floater=1, detach=0, title='', geometry='', background_only=0, redirect_output=0):
    from hsdl.common import general


    # -- this is the temp script name
    tempfname = general.local_hsdl_mktemp()

    if prompt:
        footer = "\n echo '----------- DONE ------------'\nread\nrm %s\n" % tempfname
    else:
        footer = "\nrm %s\n" % tempfname

    fout = open(tempfname, 'wb')

    fout.write(s + footer)
    fout.close()

    the_fun = os.popen
    if detach:
        the_fun = os.popen2

    if not title:
        if floater:
            title = 'mrxvt_floater'
        else:
            title = 'mrxvt_window'

    output_tempfname = ''

    # we only do output redirection if prompt is off
    if redirect_output and not prompt:
        top_tempfname = general.local_hsdl_mktemp()
        output_tempfname = general.local_hsdl_mktemp()
        fout = open(top_tempfname, 'wb')
        fout.write("bash %s | tee > %s\n" % (tempfname, output_tempfname))
        fout.close()

        tempfname = top_tempfname


    if background_only:
        proc = the_fun("bash " + tempfname)
    else:
        if geometry:
            proc = the_fun('gnome-terminal  --geometry=%s -t "%s" -e "bash %s"' % (geometry, title, tempfname))
        else:
            proc = the_fun('gnome-terminal  -t "%s" -e "bash %s"' % (title, tempfname))

    if not detach:
        proc.close()

        if redirect_output and not prompt:
            if output_tempfname:
                fin = open(output_tempfname, 'rb')
                s = fin.read()
                fin.close()

                print s

def open_bash_terminal(s, pwd='$HOME', title='', floater=1, geometry=''):
    from hsdl.common import general

    # -- this is the temp script name
    tempfname = general.local_hsdl_mktemp()

    s = "source ~/.bashrc; cd " + pwd + "\n" + s

    fout = open(tempfname, 'wb')
    fout.write(s)
    fout.close()

    the_fun = os.popen

    if floater:
        title = 'mrxvt_floater'
    else:
        title = 'mrxvt_window'

    if geometry:
        proc = the_fun('gnome-terminal  --geometry=%s -t "%s" -e "bash --init-file %s"' % (geometry, title, tempfname))
    else:
        proc = the_fun('gnome-terminal  -t "%s" -e "bash --init-file %s"' % (title, tempfname))


def gpg_encrypt(vim, s, recipient):
    temp_fname_in = general.mklocaltemp()
    fout = open(temp_fname_in, 'wb')
    fout.write(s)
    fout.close()

    temp_fname_out = general.mklocaltemp()
    if os.path.exists(temp_fname_out):
        os.unlink(temp_fname_out)

    stmt = "gpg --encrypt --recipient %s --output=%s %s" % (recipient, temp_fname_out, temp_fname_in)

    from hsdl.eclipse import common
    common.proc(vim, stmt, prompt=0, decide_how_to_show=1)

    os.unlink(temp_fname_in)

    if os.path.exists(temp_fname_out):  # succeeded
        fin = open(temp_fname_out, 'rb')
        s = fin.read()
        fin.close()

        os.unlink(temp_fname_out)

        return s

    else:
        return None


def gpg_decrypt(vim, s):
    temp_fname_in = general.mklocaltemp()
    fout = open(temp_fname_in, 'wb')
    fout.write(s)
    fout.close()

    temp_fname_out = general.mklocaltemp()
    if os.path.exists(temp_fname_out):
        os.unlink(temp_fname_out)

    stmt = "gpg --decrypt  --output=%s %s" % (temp_fname_out, temp_fname_in)

    from hsdl.eclipse import common
    common.proc(vim, stmt, prompt=0, decide_how_to_show=1)

    os.unlink(temp_fname_in)

    if os.path.exists(temp_fname_out):  # succeeded
        fin = open(temp_fname_out, 'rb')
        s = fin.read()
        fin.close()

        os.unlink(temp_fname_out)

        return s

    else:
        return None


def postProcSnippet(s):                 #FEATURE# allows python to post process snippets, such as executing python code within backticks
    pat = re.compile(r'`(?P<code>[^`]*?)`', re.DOTALL)
    assign_pat = re.compile(r'^(?P<id>[a-zA-Z0-9_-]+)\s*=(?P<rest>.*)', re.DOTALL)

    from hsdl.vim import snippet
    dict = snippet.__dict__

    def sub(matchobj, dict=dict, assign_pat=assign_pat):
        code = string.strip(matchobj.group('code'))
        if code:
            r = assign_pat.match(code)
            if r:
                id = r.group('id')
                rest_code = string.strip(r.group('rest') )
                return str(eval(rest_code, dict))
            else:
                return str(eval(code, dict))
        else:
            return code

    return pat.sub(sub, s)

multi_spaces = re.compile(r'\s+')

struct_pat = re.compile(r'struct:tc-results?\s*')


def set_completion_message(vim, s):
    TRANSLATEQUOTES = string.maketrans("\'\"", "\"\'")
    s = s.translate(TRANSLATEQUOTES)
    vim.command('let g:completion_message="%s"' % string.replace(s, '"', '\\"'))


proj_path_candidates = ['/home/hsdl/wk-erlide/', '/home/hsdl/wk-scala-2.10/', '/home/hsdl/git-wk/projects']

def determineEclipseProject(path):
    for candidate in proj_path_candidates:
        full = os.path.join(candidate, path)
        if os.path.exists(full):
            return full
    return path

def get_vim_path(vim):
    path = vim.current.buffer.name
    if is_vim_emulator(vim):
        path = determineEclipseProject(path)
    return path

def findLatestMrxvtProcesses():
    files = glob.glob('/tmp/.mrxvt-*')
    return files

def mapMrxvtProcesses():
    files = findLatestMrxvtProcesses()
    d = {}

    ps_dict = {}    # name -> (user, pid, fname)
    ps_pat = re.compile(r'^(?P<user>[^ ]+)\s+(?P<pid>[0-9]+)\s+.*?special_mrxvt_id:(?P<name>[^ ]+)')

    lines = string.split(os.popen('ps -ef').read(), '\n')
    for line in lines:
        r = ps_pat.search(line)
        if r:
            user = r.group('user')
            pid = r.group('pid')
            name = r.group('name')
            fname = '/tmp/.mrxvt-' + pid
            if os.path.exists(fname):
                ps_dict[name] = (user, pid, fname)

    return ps_dict

def findMrxvtFifo(name):
    d = mapMrxvtProcesses()
    if d.has_key(name):
        return d[name]
    else:
        return ()


def launchMrxvt(name, commands):
    os.system("mrxvt -sr -sl 5000 -bg black -fg white -useFifo -t special_mrxvt_id:%s &" % name)
    time.sleep(2)
    tup = findMrxvtFifo(name)
    if tup:
        name, pid, fname = tup
        fout = open(fname, 'wb')
        for cmd in commands:
            fout.write('Str ' + cmd + '\\n\n')
        fout.close()


future_pat = re.compile(r'<<FUTURE([^>]*)>>.*')

# for each future line, it deletes from the future reference to the end of line
def clean_future_refs(s):
    lines = string.split(s, '\n')
    lines = map(lambda line: future_pat.sub('', line),  lines)
    return string.join(lines, '\n')

def clean_repeat_lines(lines):
    pat = re.compile(r'<<NAME:(?P<name>[^>]+)>>')
    pat2 = re.compile(r'<<REPEAT(_DOWN)?:[^:]+:(?P<name>[^>]+)>>')
    lines = map(lambda line: pat.sub('', line),   lines)
    lines = map(lambda line: pat2.sub('', line),   lines)
    return lines


# still running
def is_future_running_helper(label):
    parent = general.interpolate_filename("${HOME}/done/")
    info_path = os.path.join(parent, label + '.info')
    done_path = os.path.join(parent, label + '.done')
    return os.path.exists(info_path) and (not os.path.exists(done_path))

# finished running but not completed
def is_future_waiting_helper(label):
    parent = general.interpolate_filename("${HOME}/done/")
    info_path = os.path.join(parent, label + '.info')
    done_path = os.path.join(parent, label + '.done')
    return os.path.exists(info_path) and os.path.exists(done_path)


def delete_future_files():
    os.system("rm /tmp/vim-*.sh")
    os.system("rm /tmp/vim-*.run")
    os.system("rm ${HOME}/done/*")


def line_ranges_dict(code):
    line_lengths = map(len, string.split(code, '\n'))

    d = {}      # (start, end) -> line_num
    curr = 0
    last_pos = 0
    for size in line_lengths:
        upto = last_pos + size + 1  # add 1 because the newline is itself a character
        d[(last_pos, upto)] = curr
        curr += 1
        last_pos = upto
    return d


def which_line_col(line_ranges, pos):
    for start, end in line_ranges.keys():
        if pos>=start and pos<end:
            line = line_ranges[(start, end)]
            col = pos - start
            return line, col
    return -1, -1

class SexprWrapper:
    def __init__(self, obj, start, end, line_num=-1, col=-1):
        self.obj = obj
        self.start = start
        self.end = end
        self.line_num = line_num
        self.line_col = col
        self.orig_str = None    # this only has a valid value when we're dealing with a Quantity

    def __eq__(self, other):
        return self.obj == other

    def __getattr__(self, key):
        #if key == 'start':
        #    return self.tup[1].start
        #elif key == 'end':
        #    return self.tup[1].end
        if self.__dict__.has_key(key):
            return self.__dict__[key]
        else:
            raise AttributeError("Could not find: " + key)

    def __getitem__(self, index):
        if type(self.obj) == types.ListType:
            return self.obj[index]
        else:
            raise AttributeError("Not a list")


    def __len__(self):
        if type(self.obj) == types.ListType:
            return len(self.obj)
        else:
            raise AttributeError("Not a list")

    def __repr__(self):
        return repr(self.obj)

    def shift_start(self, x):
        self.start -= x

    def shift_end(self, x):
        self.end -= x

    def calc_line_col(self, line_ranges):
        line, col = which_line_col(line_ranges, self.start)
        self.line_num = line
        self.line_col = col


# dump SexprWrapper object
def dump_meta(obj):
    print "++++++++++++++++++++++", obj
    print "start:", obj.start
    print "end:", obj.end
    print "line_num:", obj.line_num
    print "line_col:", obj.line_col



class OutputBuffer:
    def __init__(self, first_start=None):
        self.buffer = []
        self.line_num = 0
        self.col = 0
        self.list_started = 0
        self.first_start = first_start
        self.the_first = 1
        self.num_seq_vagrant = 0
        self.last_start = -1

    def insert(self, _obj):
        obj = _obj.obj

        start = _obj.start
        end = _obj.end
        line_col = _obj.line_col
        line_num = _obj.line_num

        if self.the_first and (not self.first_start is None):
            line_col = self.first_start

        self.the_first = 0

        # this is such a hack; for a string using triple quotes, move back 2 spaces to allow space for the first 2 quotes
        if type(obj) in [types.StringType, types.UnicodeType]:
            if not _obj.orig_str is None:
                line_col -= 2

        if line_num > self.line_num:
            diff = (line_num - self.line_num)
            self.buffer.append('\n'*diff)
            self.line_num = line_num
            self.col = 0
        elif line_num == -1:
            self.buffer.append(' ')
            self.col += 1
            if 0:
                self.buffer.append('\n')
                self.line_num += 1
                self.col = 0
        elif line_num < self.line_num:          #TODO is this right?
            self.buffer.append('\n')
            self.col = 0


        if self.col != -1:

            if self.num_seq_vagrant > 2:           # should we check for only the last one or look at a run of -1's
                col_diff = line_col
                self.col = 0
                self.line_num += 1             #TODO think about uncommenting this one; it's tricky
            else:
                col_diff = (line_col - self.col)

            if col_diff > 0:
                self.buffer.append(' '*col_diff)
                self.col += col_diff
            elif col_diff < 0:
                self.buffer.append(' ')         # where the columns are not in a progression; this prevents objects from being jammed together
                self.col += 1

        if start == -1:
            self.num_seq_vagrant += 1
        else:
            self.num_seq_vagrant = 0

        self.last_start = self.col


        if self.list_started:
            self.buffer.append('(')
            # NOTE: notice that here we don't advance the column by 1 even though we add '('.
            self.list_started = 0


        if type(obj) in [types.StringType, types.UnicodeType]:
            QUOTES = '"'
            if not _obj.orig_str is None:
                QUOTES = '"""'

            if string.find(obj, '\n')>=0:
                lines = string.split(obj, '\n')
                self.buffer.append(QUOTES + lines[0] + '\n')
                for line in lines[1:-1]:
                    self.buffer.append(line + '\n')
                self.buffer.append(lines[-1] + QUOTES)
                self.col = len(lines[-1])
                self.line_num += (len(lines) - 1)
            else:
                self.buffer.append(QUOTES + obj + QUOTES)
                self.col += len(obj)+2

        elif type(obj) in [types.IntType, types.LongType, types.FloatType]:
            if _obj.orig_str is None:
                if start == -1:
                    if type(obj) in [types.IntType, types.LongType]:
                        s = str(obj)
                    else:
                        s = '%5.2f' % obj
                else:
                    width = end-start
                    if type(obj) in [types.IntType, types.LongType]:
                        s = ('%d' % obj)[:width]
                    else:
                        s = ('%f' % obj)[:width]
            else:
                s = _obj.orig_str

            self.buffer.append(s)
            self.col += len(s)

        elif type(obj) == types.TupleType:
            s = obj[0]
            self.buffer.append(obj[0])
            self.col += len(s)

    def insert_string(self, s):
        self.buffer.append(s)
        self.col += len(s)

    def mark_list_started(self, obj):
        # Was there already a pending start of list? Let's take care of that one before jumping into another (embedded) list.
        if self.list_started:
            self.buffer.append('(')
            # NOTE: notice that here we don't advance the column by 1 even though we add '('.

        #print "+++++++++++++++++", type(obj), len(obj), obj
        self.list_started = 1

    def mark_list_closed(self):
        self.buffer.append(')')
        self.col += 1
        self.list_started = 0



# converts sexp-wrapped structure (originally generated by schemepy.skime) to sisc structure
def pretty_print_helper(_obj, buffer):
    obj = _obj.obj

    if type(obj) == types.ListType:
        if obj and obj[0].obj == ('*-*',):  #TODO magic, to preserve our original cursor position
            buffer.insert_string('*-*')
            obj = obj[1]
            if not type(obj.obj) == types.ListType:
            #print "!!!!!!!!", type(obj.obj)
            #if type(obj.obj) == types.StringType:
                buffer.insert(obj)
                return
                print ">>>>>>", obj.obj

        if 1: #type(obj) == types.ListType:
            #print ":::::::", obj, type(obj), obj.__class__
            if obj == []:
                buffer.insert_string('()')
            else:
                buffer.mark_list_started(obj)
                for each in obj:
                    pretty_print_helper(each, buffer)
                buffer.mark_list_closed()
    else:
        buffer.insert(_obj)


def pretty_print(obj, first_start=None):
    buffer = OutputBuffer(first_start)
    pretty_print_helper(obj, buffer)
    return buffer

def lisp_pretty_print(s):
    from hsdl.cl import genlisp
    genlisp.start_lisp()
    return string.strip(genlisp.apply_ecl("prettify", [s]))


# if we find the symbol '___MATCH___' in an sexp, we ignore everything after it; used for pattern matching
def truncate_sexp_matching(_obj):
    obj = _obj.obj

    if type(obj) == types.ListType:
        all = []
        found = 0
        for each in obj:
            if each == ('___MATCH___',):
                all.append(each)
                found = 1
                break
            else:
                truncate_sexp_matching(each)
                all.append(each)

        if found:
            _obj.obj = all


def find_matching_symbol(s, pos, size, start_symbol, end_symbol):
    opening_count = 0

    i = pos
    while i < size:
        c = s[i]
        if c == start_symbol:
            opening_count += 1
        elif c == end_symbol:
            opening_count -= 1
            if opening_count == 0:
                return i, s[pos:i+1]

        i += 1

    return -1, None


def go_up_level(vim, level):
    orig = vim.current.window.cursor
    for i in xrange(level):
        vim.command("normal [(")
    last = vim.current.window.cursor

    vim.current.window.cursor = orig
    vim.current.window.cursor = last




# assuming that the cursor is on a paren, get text of the entire region that matches it
def get_matched_region(vim):
    try:
        coor_start = vim.current.window.cursor
        vim.command("normal v")
        vim.command("normal %")
        vim.command('normal "ty')
        buff = vim.eval("@t")
        vim.current.window.cursor = coor_start
        return buff
    except:
        return ''

# assuming that the cursor is on a paren, get text of the entire region that matches it, and the (line, col) coordinates
def get_matched_region_with_pos(vim):
    try:
        coor_start = vim.current.window.cursor
        vim.command("normal v")
        vim.command("normal %")
        final_coor = vim.current.window.cursor
        vim.command('normal "ty')
        buff = vim.eval("@t")
        vim.current.window.cursor = coor_start
        return buff, final_coor
    except:
        return ('', (-1, -1))


# returns (code, start_cur, end_cur)
def find_containing_sexpr(vim, curr_char=None):
    orig_cur = vim.current.window.cursor
    if (curr_char is None) or (not curr_char == '('):
        vim.command("normal [(")
    start_cur = vim.current.window.cursor
    s, end_cur = get_matched_region_with_pos(vim)
    vim.current.window.cursor = orig_cur
    return s, start_cur, end_cur




# do regex substitution using character c, but use as many c's so that final string is
# the same length as original
def regex_sub_preserve_width(s, pat, c):
    def sub(matchobj):
        size = len(matchobj.group())
        return c*size

    return pat.sub(sub, s)

# assuming that the ancestors are listed from closest to most distant, returns the first
# (symbol, block, col) that looks like ==x==; if not found, returns ('', '', -1, -1, -1)
def find_first_lang_spec(ancs):
    pat = re.compile('^==(?P<lang>[^= ()\r\n]+)==$')
    for spec, block, col, row1, col1, row2, col2 in ancs:
        r = pat.match(spec)
        if r:
            return r.group('lang'), block, col, row1, row2
    return ('', '', -1, -1, -1)

def get_lang(vim):
    ancs = vim.find_ancestors()
    lang, _, _, _, _  = find_first_lang_spec(ancs)
    return lang

def get_lang_and_block(vim):
    ancs = vim.find_ancestors()
    lang, block, _, _, _  = find_first_lang_spec(ancs)
    return lang, block

# returns code, pos of entire (===lang===), code startreturns None if lang or block is not found
def find_lang_code(vim, lang):
    ancs = vim.find_ancestors()
    this_lang, block, col, row1, row2  = find_first_lang_spec(ancs)
    start_pos = int(vim.eval('line2byte(%d)+col(%d)' % (row1, col)))
    if this_lang == lang:
        pat = re.compile(r'"""(?P<code>.*?)"""', re.DOTALL)
        r = pat.search(block)
        if r:
            code = r.group('code')
            before = block[:r.start()]
            rel_line  = before.count('\n')
            return code, col, start_pos, r.start(), rel_line

    return ()

# assuming that the ancestors are listed from closest to most distant, returns the first
# (symbol, block, col) that looks like <<x>>; if not found, returns ('', '', -1, -1, -1)
def find_first_cmd_spec(ancs):
    pat = re.compile('^<<(?P<cmd>[^= ()\n\r]+)>>$')
    for spec, block, col, row1, col1, row2, col2 in ancs:
        r = pat.match(spec)
        if r:
            return r.group('cmd'), block, col, row1, row2
    return ('', '', -1, -1, -1)


def find_first_head_equal(ancs, head):
    for spec, block, col, row1, col1, row2, col2 in ancs:
        if spec == head:
            return spec, block, col, row1, row2
    return ('', '', -1, -1, -1)

def jump_to_file_and_line_num(vim, path, line_num):
    r = vim.go_to_opened_buffer(path)      # if there is one opened
    if not r:
        vim.command(":silent tabnew " + path)
        base, ext = os.path.splitext(path)
        if not ext in ['.mind']:
            vim.command(":silent set nofoldenable")

    if not line_num is None:
        vim.current.window.cursor = (line_num, 0)

def trigger_snippet(vim):
    vim.command(':call feedkeys("i")')
    vim.command(':let g:specialIgnore=1')
    vim.command(':call TriggerSnippet()')


def snippets_all(vim, default_ext=''):
    buffname = vim.current.buffer.name
    if buffname:
        parent, fname = os.path.split(buffname)
        basename, ext = os.path.splitext(fname)
        ext = ext[1:]       # drop the '.'
    else:
        ext = 'mind'

    if default_ext:
        ext = default_ext

    d = {}
    snippets_fname = general.interpolate_filename("${HSDL_LIB_HOME}" + "/snippets/" + ext + ".snippets")

    last_name = ''
    acc = []
    comments_acc = []

    if os.path.exists(snippets_fname):
        fin = open(snippets_fname,'rb')
        while 1:
            line = fin.readline()
            if not line: break

            if line[0] == '#':
                comments_acc.append(line)
                continue

            if line[:8] == 'snippet ':
                parts = string.split(line)
                if len(parts)>1:
                    the_name = parts[1]

                    if last_name and acc:
                        d[last_name] = (acc, comments_acc)

                    last_name = the_name
                    acc = []
                    comments_acc = []
                    continue

            acc.append(line)

        fin.close()

    if last_name and acc:
        d[last_name] = (acc, comments_acc)

    return d



def find_snippet(vim, target_name):
    buffname = vim.current.buffer.name
    if buffname:
        parent, fname = os.path.split(buffname)
        basename, ext = os.path.splitext(fname)
        ext = ext[1:]       # drop the '.'
    else:
        ext = 'mind'

    d = {}
    snippets_fname = general.interpolate_filename("${HSDL_LIB_HOME}" + "/snippets/" + ext + ".snippets")

    last_name = ''
    acc = []
    comments_acc = []

    if os.path.exists(snippets_fname):
        fin = open(snippets_fname,'rb')
        line_num = 0
        while 1:
            line_num += 1
            line = fin.readline()
            if not line: break

            if line[0] == '#':
                comments_acc.append(line)
                continue

            if line[:8] == 'snippet ':
                parts = string.split(line)
                if len(parts)>1:
                    the_name = parts[1]

                    if the_name == target_name:
                        fin.close()
                        return acc, comments_acc, snippets_fname, line_num

        fin.close()

    return ()

def get_snippets_languages():
    all = glob.glob(general.interpolate_filename("${llib}/snippets/*.snippets"))
    all.sort()
    return [':' + os.path.splitext(os.path.split(each)[1])[0] for each in all]

def snippets_list(vim, default_ext='mind', before=()):
    d = snippets_all(vim, default_ext=default_ext)
    k = d.keys()
    k.sort()
    if len(before) == 1:
        k += get_snippets_languages()
    return k


def get_curr_undo_num(vim):
    vim.command(":redir @t")            # redirect to register H
    vim.command(":silent! undolist")    # dump the list
    vim.command(":redir END")
    buff = vim.eval("@t")
    lines = string.split(buff, '\n')
    if len(lines)>2:
        parts = string.split(lines[-1])
        return int(string.strip(parts[0]))
    else:
        return 0


def vim_modified(vim):
    vim.command(":redir @t")            # redirect to register H
    vim.command(":set mod?")    # dump the list
    vim.command(":redir END")
    buff = vim.eval("@t")
    return string.find(buff, 'nomodified')<0


def begin_undo_block(vim):
    n = get_curr_undo_num(vim)
    shared.undo_start_num = n

def end_undo_block(vim, last=0):
    curr = get_curr_undo_num(vim)
    diff = curr - shared.undo_start_num - last
    vim.command(":earlier %d" % diff)


def snippet_canonical_name(s):
    pat = re.compile('(?P<id>[a-zA-Z0-9_]+)(/(?P<num>[0-9]+))$')
    r = pat.match(s)
    if r:
        id = r.group('id')
        num = r.group('num')
        if num is None:
            return (sys.maxint, id)
        else:
            return (int(num), id)
    else:
        return (sys.maxint, s)

def snippet_next_name(vim, dir=1):
    ordered = shared.snip_bindings.keys()
    if ordered:
        ordered.sort()
        curr = shared.snip_curr_name
        if curr == ():
            return ordered[0]
        else:
            if curr in ordered:
                i = ordered.index(curr) + dir   # get next; 1 goes forward, -1 goes back
                if i<len(ordered):
                    return ordered[i]
                elif i < 0:
                    return ordered[-1]          # wrap to end
                else:
                    return ordered[0]           # wrap to beginninng
    else:
        return ()


def clear_global_state(vim):
    name = vim.current.buffer.name
    if name and string.find(name, 'SNIP__')>=0:
        shared.snip_on = 0
        shared.snip_bindings = {}
        shared.snip_template = []


# given a string (containing newlines), get column within the line
def col_in_line(s, pos):
    lines = string.split(s, '\n')
    d = {}
    d[0] = 1

    p = 0
    for line in lines:
        p += len(line) + 1
        d[p-1] = 1

    places = d.keys()
    places.sort()
    places = places[:-1]    # last entry is always unnecessary
    last = -1

    for each in places:
        if each > pos:
            break
        else:
            last = each

    if last == -1:
        return -1
    else:
        return pos - last - 1

def lisp_alist_to_dict(sexp):
    d = {}
    last_key = ''
    for each in sexp:
        if last_key:
            d[last_key] = each.obj
            last_key = ''
        else:
            last_key = each.obj[0]

    if last_key:
        d[last_key] = each.obj

    return d


def get_current_sexp(vim):
    from hsdl.vim import jinteractive
    reload(jinteractive)

    orig_cur = vim.current.window.cursor

    ancs = vim.find_ancestors()
    if not ancs: return
    _, block, _, _, _, _, _  = ancs[0]
    sexp, _ = jinteractive.full_parse_sexp(block, 0)
    vim.current.window.cursor = orig_cur
    return sexp


def get_sexp_special_marker(vim, prefix, dir=1, current_line_only=0):
    orig_cur = vim.current.window.cursor

    buff = vim.current.buffer
    line = vim.current.line
    p = string.find(line, prefix)
    if p >= 0:
        col = int(vim.eval('col(".")'))-1
        if (dir == 1 and p>col) or (dir == -1 and p<(col-1)):   # (col-1) so that we can jump outside of the current region
            i = int(vim.eval('line(".")'))-1
            vim.current.window.cursor = i+1, p                  # unlike other finds, we want to be on the '('
            s = get_matched_region(vim)
            vim.current.window.cursor = orig_cur
            return s

    if current_line_only:
        return None

    max = len(buff)-1
    i = int(vim.eval('line(".")'))-1
    found = 0
    p = -1

    while 1:
        i += dir
        if i<0 or i>=max:
            break

        line = buff[i]
        p = string.find(line, prefix)
        if p >= 0:
            found = 1
            break

    if found:
            vim.current.window.cursor = i+1, p          # unlike other finds, we want to be on the '('
            s = get_matched_region(vim)
            vim.current.window.cursor = orig_cur
            return s

    return None

def get_support_source(buffname, support_name):
    dirname, fname = os.path.split(buffname)
    basename, _ = os.path.splitext(fname)
    return os.path.join(dirname, basename +  '__' + support_name)

def fix_unbalanced_parens(final_lines):
    stack_size = 0
    s = string.join(final_lines, '\n')
    final = []

    for c in s:
        if c in '()':
            if c == '(':
                stack_size += 1
            elif c == ')':
                if stack_size == 0:
                    c = chr(30) + '()'
                else:
                    stack_size -= 1
        final.append(c)

    for i in xrange(stack_size):
        final.append(chr(30) + ')')
    return string.split(string.join(final, ''), '\n')

def is_insert_mode(vim):
    return vim.eval("mode()") == 'i'

def is_normal_mode(vim):
    return vim.eval("mode()") == 'n'

def get_mode(vim):
    return vim.eval("mode()")

def debug_log(s):
    fout = open('/tmp/VIM_DEBUG_LOG', 'ab')
    fout.write(s + '\n')
    fout.close()

def prepare_debug(vim, debug=0):
    shared.DEBUG_ON = debug

def check_debug(vim):
    if shared.DEBUG_MESSAGE:
        dump_new_tab(vim, shared.DEBUG_MESSAGE)

def get_mode(vim):
    return shared.CURR_MODE

def racket_start():
    if not shared.RACKET_STARTED:
        from hsdl.racket import racket
        racket.start()      # can be called repeatedly

# returns new string (based on orig), where the insertions are based on insert_specs
# insert_specs is list of (pos, string); pos is always the original position, despite its absolute position
# possibly changing as insertions progress

def insert_relative(orig, insert_specs):
    specs = copy.copy(insert_specs)
    specs.sort()
    delta = 0
    for orig_pos, s in specs:
        orig_pos += delta
        orig = orig[:orig_pos] + s + orig[orig_pos:]
        delta += len(s)

    return orig


# s must not contain '\n'; if pos is not given, it will use the current
def insert_into_curr_line(vim, to_insert, pos=None):
    line = vim.current.line
    line_num = int(vim.eval('line(".")'))-1
    if pos is None:
        col = int(vim.eval('col(".")'))-1
    else:
        col = pos

    if to_insert and string.find(to_insert, LINE_DELIMITER)<0:
        line2 = line[:col] + to_insert + line[col:]

        vim.current.buffer[line_num] = line2


def execute_header_commands_lisp(vim, spec):
    pass

def execute_header_commands(vim, spec):
    spec = string.strip(spec)
    if not spec:
        return

    if spec[0] == '(':     # lisp command
        execute_header_commands_lisp(vim, spec)
    else:                   # just a list of files
        curr_path = vim.current.buffer.name
        if not curr_path in shared.LINKAGE:
            the_list = []
            shared.LINKAGE[curr_path] = the_list

            one_opened = 0
            files = string.split(spec)
            cwd = os.getcwd()
            for fname in files:
                full = os.path.join(cwd, fname)
                the_list.append(full)
                if os.path.exists(full):
                    if not vim.check_already_exists(full):
                        vim.open_new_tab(full)
                        vim.command(":silent set nofoldenable")
                        one_opened = 1
                else:
                    print "Unable to open required file:", full

            if one_opened:
                # bring back original
                vim.go_to_opened_buffer(curr_path)


def parse_header_commands(vim):
    curr_path = vim.current.buffer.name
    if not curr_path:
        return

    first_line = string.strip(vim.current.buffer[0])

    pat = re.compile(r'\+\+\+\s*(?P<spec>.+?)\s*\+\+\+', re.DOTALL)

    r = pat.search(first_line)      # see if first already contains entire spec
    if r:
        spec = r.group('spec')
    else:                           # otherwise, check entire buffer
        s = string.join(vim.current.buffer[:], '\n')
        r2 = pat.search(s)
        if r2:
            spec = r2.group('spec')
        else:
            return


    execute_header_commands(vim, spec)

def is_part_of_linkage(curr_path):
    for main, deps in shared.LINKAGE.items():
        if curr_path in deps:
            return main
    return None

def remove_from_linkage(curr_path):
    for main, deps in shared.LINKAGE.items():
        if curr_path in deps:
            print "REMOVED"
            deps.remove(curr_path)
            print shared.LINKAGE

# using get_lang() or anything that involves invisibly moving the caret around
# messes up how vim remembers your previous position; one consequence is that
# after calling get_lang(), moving the cursor up and down a line causes it
# to be placed in the wrong column
def workaround_cursor_positions_lost(vim):
    #cur = vim.current.window.cursor
    #vim.current.window.cursor = cur
    vim.command(':call feedkeys("````")')


# -------- this is called only once -----------
def init():
    global ALREADY_INIT

    if not ALREADY_INIT:
        #callj("vim=: '' conew 'vim' [ hsdl'wip/vim'")
        ALREADY_INIT = 1

def sarino_current_line(vim):
    return int(vim.eval('line(".")'))-1


LAST_CHECK = time.time()

def check_kill_file():
    global LAST_CHECK

    curr = time.time()
    if curr - LAST_CHECK > 0.5:
        LAST_CHECK = curr
        if os.path.exists(SOCKET_KILL_FILE):
            fin = open(SOCKET_KILL_FILE,'rb')
            s = fin.read()
            fin.close()
            if string.strip(s) == 'kill':
                return 1
    return 0


def send_action_franca_nonblocking(service_name, args, port=15001, machine='localhost'):
    if os.path.exists(SOCKET_KILL_FILE):
        os.unlink(SOCKET_KILL_FILE)

    return franca_comm_nonblocking.send_action_franca(service_name, args, port=port, machine=machine, stop_check_fun=check_kill_file)

is_number_pat = re.compile(r'^[0-9,.]+$')
def is_number(s):
  return is_number_pat.search(s) is not None

# can use either "``" or "∥" as separators

def format_display_parse(lines):
    if lines:
        temp = string.strip(lines[0])
        if not temp[0] == '`': return

        indent = get_indentation(lines[0], 1)
        all = []    # list of (kind, parts)
        for line in lines:
            kind = 1
            parts = string.split(string.strip(line)[1:], '|')
            if len(parts) == 1:
                kind = 2
                parts = string.split(string.strip(line)[1:], '∥')
                if len(parts) == 1:
                    kind = 3
                    parts = string.split(string.strip(line)[1:], '``')
            parts = map(lambda part: string.strip(part), parts)
            all.append((kind, parts))


        max_cols = max(map(lambda info: len(info[1]), all))

        max_widths = {}

        for col in xrange(max_cols):
            max_widths[col] = 0

            for _kind, parts in all:
                if len(parts) == 1 and parts[0].startswith('--'):
                    continue
                if col >= len(parts): continue
                if len(parts[col]) > max_widths[col]:
                    max_widths[col] = len(parts[col])

        # some times, the last columns may be empty, so let's remove them if their max_col is 0
        # go backwards
        col_keys = max_widths.keys()
        col_keys.sort()
        col_keys.reverse()
        for col in col_keys:
            if max_widths[col] > 0: break
            del max_widths[col]                 # removed


        final = []
        for kind, parts in all:
            if len(parts) == 1 and parts[0].startswith('--'):
                sofar = parts
            else:
                sofar = []
                for col in xrange(len(parts)):
                    if max_widths.has_key(col):     # this will only fail if it's among the trailing columns
                        pad = max_widths[col]
                        if is_number(parts[col]):
                            sofar.append(('%0' + str(pad) + 's') % parts[col])  # right-justified
                        else:
                            sofar.append((parts[col] + (' '*pad))[:pad])        # left-justified
            if kind == 1:
                final.append(string.join(sofar, ' | '))
            elif kind == 2:
                final.append(string.join(sofar, ' ∥ '))
            else:
                final.append(string.join(sofar, ' `` '))

        final = map(lambda line: (' '*indent) + '`' + line, final)

        final = tag_data_lines(final)

        cleaned_all = [tup[1] for tup in all]
        return final, cleaned_all
    else:
        return [], []

def rewrite_data(s):
    if USE_DATA_TAGS:
        return string.replace(s, DATA_TAG, '')
    else:
        return s


def j_map_to_dict(data):
    d = {}
    for key, value in data:
        d[key] = value
    return d

# preserve indentation; remove all empty lines
def rewrite_code_for_interactive(s):
    all = []
    for line in string.split(s, '\n'):
        if string.strip(line):
            all.append(line)
    return string.join(all, '\n')


def haskell_external_eval(vim, s):
    if shared.HASKELL_EXTERNAL_FNAME_STDIN:
        fname_out = shared.HASKELL_EXTERNAL_FNAME_STDIN
        fname_in = shared.HASKELL_EXTERNAL_FNAME_STDOUT
        fname_finished_writing = shared.HASKELL_EXTERNAL_FNAME_FINISHED_WRITING

        fout = open(fname_out, 'wb')
        fout.write(s)
        fout.close()

        start_time = time.time()
        result = None
        while 1:
            time.sleep(0.05)
            if time.time() - start_time > 10.0:
                break
            if os.path.exists(fname_finished_writing):
                fin = open(fname_in, 'rb')
                s = fin.read()
                fin.close()
                s = string.replace(s, '\r', '')
                result = string.rstrip(s)

                os.unlink(fname_in)
                os.unlink(fname_finished_writing)

                break

        return result


def scala_external_eval(vim, s):
    if shared.SCALA_EXTERNAL_FNAME_STDIN:
        fname_out = shared.SCALA_EXTERNAL_FNAME_STDIN
        fname_in = shared.SCALA_EXTERNAL_FNAME_STDOUT
        fname_finished_writing = shared.SCALA_EXTERNAL_FNAME_FINISHED_WRITING

        fout = open(fname_out, 'wb')
        fout.write(s)
        fout.close()

        start_time = time.time()
        result = None
        while 1:
            time.sleep(0.05)
            if time.time() - start_time > 10.0:
                break
            if os.path.exists(fname_finished_writing):
                fin = open(fname_in, 'rb')
                s = fin.read()
                fin.close()
                s = string.replace(s, '\r', '')
                result = string.rstrip(s)

                os.unlink(fname_in)
                os.unlink(fname_finished_writing)

                break

        return result

def handle_balloon(vim):
    line = int(vim.eval("v:beval_lnum"))
    col = int(vim.eval("v:beval_col"))
    #text = "!!" + find_word(line, col) + "!!"
    #text = "%s - %d,%d" % (vim.eval("v:beval_text"), line, col)
    #vim.command(":let g:balloon_returning='" + text + "'")
    #return

    #pos = int(vim.eval('line2byte(line("."))+col(".")')) - 1
    pos = int(vim.eval('line2byte(%d)' % line)) + col

    type_info = vim.getRacketTypeInfo(pos)
    arrow_info = vim.getRacketArrowInfo(pos)

    text = type_info + ' : ' + arrow_info
    text = string.replace(text, "'", "''")
    vim.command(":let g:balloon_returning='" + text + "'")



ECLIPSE_COMMANDS_PARAMS = ('wb', 'win', 'doc', 'editor', 'offset', 'line', 'col', 'word', 'path', 'args', 'vim')

def is_function_visible(name, dict):
    fun = dict[name]
    if type(fun) == types.FunctionType:
        args = fun.func_code.co_varnames
        crit1 = string.find(name, '_completer')<0 and string.find(name, '_helper')<0
        crit2 = args[:1] == ('args',) or args[:2] == ('vim', 'args') or args[:2] == ('vim', 'arg') or args[:len(ECLIPSE_COMMANDS_PARAMS)] == ECLIPSE_COMMANDS_PARAMS
        return crit1 and crit2
    else:
        return 0

def get_line_comment_symbol(ext):
    ext = string.lower(ext)
    if ext in ['py', 'jy']:
        return '#'
    elif ext == 'j':
        return 'NB. '
    elif ext == 'java':
        return '//'
    elif ext == 'scala':
        return '//'
    elif ext in ['scm', 'rkt', 'lsp', 'lisp']:
        return ';'
    elif ext == 'oz':
        return '%'
    elif ext == 'hs':
        return '--'
    elif ext == 'm':
        return '%'
    elif ext == 'sh':
        return '#'
    elif ext == 'js':
        return '//'
    elif ext == 'sql':
        return '--'
    elif ext == 'pl':
        return '#'
    elif ext == 'fs':
        return '//'
    elif ext == 'cs':
        return '//'
    elif ext in ['c', 'c++', 'cc', 'cpp']:
        return '//'
    elif ext == 'erl':
        return '%'
    elif ext == 'lfe':
        return ';'
    else:
        return ''

    pass


def interpolate_string_indented(s, pat, replace_lines):
    all = []

    lines = string.split(s, LINE_DELIMITER)
    for line in lines:
        p = string.find(line, pat)
        if p>=0:
            if replace_lines:
                line = string.replace(line, pat, replace_lines[0])
                all.append(line)
                for each in replace_lines[1:]:
                    all.append((' ' * p) + each)    # indented
        else:
            all.append(line)

    return string.join(all, LINE_DELIMITER)


def get_autoload_support_files(path):
    subs = glob.glob(path + '._.*')
    subs.sort()
    return subs

def find_match_at_col(line, pat, col):
    i = 0
    while 1:
        r = pat.search(line, i)
        if r:
            start = r.start()
            end = r.end()
            print start, end
            if col >= start and col <= end:
                return start, end, r

            i = r.end()
        else:
            break

    return ()

# returns "<code>" from within '(=== """ <code>  """)'; otherwise, returns None
def extract_code(s):
    pat = re.compile(r'\(===\s+"""(?P<code>.+?)"""\s*\)', re.DOTALL)
    r = pat.search(s)
    if r:
        return r.group('code')
    else:
        return None


# vim has problems with paths containing '%', for example
def clean_path_for_vim(path):
    return string.replace(path, '%', '\\%')



def prepare_j_for_vim(vim):
    from hsdl.j import shared
    from hsdl.j import vim_utils

    shared.VIM = vim                    # this is critical; j needs this value bound

    name = vim.current.buffer.name

    from hsdl.vim import vim_emulator_jtext
    is_jtext = isinstance(vim, vim_emulator_jtext.VimEmulatorJText)


    if is_jtext:
        from hsdl.java import javajlib
    else:
        from hsdl.j import jlib
        try:
            companion_text = string.join(vim_utils.get_companion_buffer_lines(None),  LINE_DELIMITER)
            companion_path = vim_utils.get_companion_buffer_path(None)
            if not companion_path:
                companion_path = ''


            jlib.jset('vimotext', companion_text)
            jlib.jset('vimopath', companion_path)
            jlib.jset('vimpath', name)
            jlib.jset('vimbuffernames', [buffer.name for buffer in vim.buffers])
            #jlib.jset('VIMBUFFERS', [[buffer.name, string.join(buffer[:], LINE_DELIMITER)] for buffer in vim.buffers])

        except:
            buff = cStringIO.StringIO()
            traceback.print_exc(file=buff)
            msg = buff.getvalue()
            print msg

def backup_and_delete_file(path):       #!!! TODO
    os.unlink(path)


def clean_up_scala_for_interp(s):
    s = s.encode('utf8')
    last_object = ''

    def_pat = re.compile(r'def\s+(?P<funName>[^ ]+)\s+')
    skip_on_interp_pat = re.compile(r'//\s*SKIP_ON_INTERP')
    call_on_interp_pat = re.compile(r'//\s*CALL_ON_INTERP')

    run_lines = []

    lines = string.split(s, '\n')

    all = []
    for line in lines:
        if line.startswith('package '):
            continue
        if skip_on_interp_pat.search(line):
            continue

        if line.startswith('object '):
            last_object = string.split(line)[1]

        if call_on_interp_pat.search(line):
            r = def_pat.search(line)
            if r and last_object:
                run_lines.append("%s.%s" % (last_object, r.group('funName')))

        all.append(line)

    if run_lines:
        return string.join(all, '\n') + '\n' +   'def redo = { ' + string.join(run_lines, '\n') + '} \n redo\n'
    else:
        return string.join(all, '\n') + '\n'

def paste_to_screen_terminal(path, selectedText, load_as_file=0):
    if selectedText:
        selectedText = clean_up_scala_for_interp(selectedText)

        parts = string.split(path, '/')
        _proj_name = parts[0]   # currently not used

        if load_as_file:

            selection_temp_fname = general.getuuidtemp('CODE-' + '%012d' % int(time.time())) + ".scala.paste"
            fout = open(selection_temp_fname, 'wb')
            fout.write(selectedText + '\n')
            fout.close()

            script_code = r"""
                RESULT=`term-find-windows "screen-paste" | head -1`   # select the first found
                echo $RESULT
                if [ ! "$RESULT" = "" ]
                then
                    # --- use existing one
                    THE_WINDOW=`echo $RESULT | cut -d' ' -f2`
                    THE_INDEX=`echo $RESULT | cut -d' ' -f3`
                    tmux send-keys -t "$THE_WINDOW:$THE_INDEX"  -l ':load %s'
                    tmux send-keys -t "$THE_WINDOW:$THE_INDEX"  C-m
                fi
            """ % selection_temp_fname

        else:
            escapedText = selectedText.replace("'", r"'\''")
            script_code = r"""
                RESULT=`term-find-windows "screen-paste" | head -1`   # select the first found
                echo $RESULT
                if [ ! "$RESULT" = "" ]
                then
                    # --- use existing one
                    THE_WINDOW=`echo $RESULT | cut -d' ' -f2`
                    THE_INDEX=`echo $RESULT | cut -d' ' -f3`
                    tmux send-keys -t "$THE_WINDOW:$THE_INDEX"  -l '%s'
                    tmux send-keys -t "$THE_WINDOW:$THE_INDEX"  C-m
                fi
            """ % escapedText


        proc(script_code, prompt=0, floater=0)

# list of (num, path)
def list_by_prefix(prefix):
    all = glob.glob(prefix + "*")
    tosort = []
    for path in all:
        rest = path[len(prefix):]
        if rest == '':
            tosort.append((0, path))
        else:
            tosort.append((int(rest), path))
    tosort.sort()
    return tosort


def get_next_file_by_prefix(prefix):
    all = list_by_prefix(prefix)

    if all:
        print all
        return prefix + str(all[-1][0] + 1)
    else:
        return prefix + "1"

# may decide to not use proc if the goal is to send something out to repl (and we are executing within the repl)
def proc_wrapper(s, prompt=1, floater=1, detach=0, title='mrxvt_floater', background_only=0, vim=None):
    if vim and is_vim_scala_repl(vim):
        import jline
        repl = jline.console.RendezvousDeposit.repl
        if repl:
            repl.paste(s)
    else:
        return proc(s, prompt=prompt, floater=floater, detach=detach, title=title, background_only=background_only)

def paste_to_window(window_name, selectedText, load_as_file=1, display_in_window_name_also='', vim=None):
    if selectedText:
        selectedText = clean_up_scala_for_interp(selectedText)

        if load_as_file:

            #selection_temp_fname = general.getuuidtemp('CODE-' + '%012d' % int(time.time())) + ".scala.paste"
            selection_temp_fname = get_next_file_by_prefix("/tmp/SCA")
            fout = open(selection_temp_fname, 'wb')
            fout.write(selectedText + '\n')
            fout.close()

            if display_in_window_name_also:
                script_code = """
                    win-search-sendstring "%s" '\ncat %s\n'  'false'
                """ % (display_in_window_name_also, selection_temp_fname)

                proc(script_code, prompt=0, floater=0)

            script_code = r"""
                win-search-sendstring "%s" '\n:paste %s\n'  'false'
            """ % (window_name, selection_temp_fname)

            if vim and is_vim_scala_repl(vim):
                import jline
                repl = jline.console.RendezvousDeposit.repl
                if repl:
                    repl.paste(selectedText + "\n")
            else:
                proc_wrapper(script_code, prompt=0, floater=0, vim=vim)

        else:
            escapedText = selectedText.replace("'", r"'\''")
            script_code = r"""
                win-search-sendstring "%s" '%s'  'false'
            """ % (window_name, escapedText)

            proc(script_code, prompt=0, floater=0)



# returns the  lines_of_text; returns [] if error
def generate_paste_listing():
    fnames = glob.glob("/tmp/CODE-*.paste")
    fnames.sort()
    fnames.reverse()    # reverse chronological list

    all = []

    if fnames:
        tempfname = general.local_hsdl_mktemp() + '.mind'

        for fname in fnames:
            all.append(fname + '   file://' + fname)
            fin = open(fname, 'rb')
            while 1:
                line = fin.readline()
                if not line: break
                all.append('    ' + line)
            fin.close()
            all.append('')
            all.append('')

    return all


# returns 1 if one meets all substring conditions
def check_ps_listing(substring_conditions):
    for line in string.split(os.popen('ps -ef').read(), '\n'):
        failed = 0
        for substr in substring_conditions:
            if line.find(substr)<0:
                failed = 1
                break

        if not failed:
            return 1
    return 0


class VimWrapper:
    def __init__(self, vim):
        self.vim_core = vim

    def __getattr__(self, key):
        if self.__dict__.has_key(key):
            return self.__dict__[key]
        elif self.vim_core.__dict__.has_key(key):
            return self.vim_core.__dict__[key]
        elif hasattr(self.vim_core, key):
            return getattr(self.vim_core, key)

    def __nonzero__(self):
        return 1

    def suzy(self): pass


# converts the built-in vim object into a VimEmulator
def build_vim(raw_vim):
    from hsdl.vim import vim_emulator_vim

    vim = vim_emulator_vim.VimEmulatorVim(raw_vim)
    vim = VimWrapper(vim)
    return vim

class MethodCallerWrapper:
    def __init__(self, proxy):
        self.proxy = proxy

    def __getattr__(self, key):
        if self.__dict__.has_key(key):
            return self.__dict__[key]
        else:
            print "CALLABLE:", key
            try:
                return self.proxy.getCallable(key)
            except:
                return None

# make this vim instance accessible thru java; under C vim, it will wrap around VimWrapper above; under embedit or eclipse, it is left alone
def prep_jvim(vim):
    #if isinstance(vim, VimWrapper):

    if vim.__class__.__name__ == 'VimWrapper':
        from hsdl.java import javalib

        javalib.prep()

        class AbstractEditor:

            def __init__(self, vim):
                self.vim = vim

            def getLine(self, lineNum):
                return self.vim.getLine(lineNum)

            def clear(self):
                self.vim.clear()

            def setText(self, s):
                self.vim.setText(s.encode('utf8'))

            def setLines(self, startLine, endLine, lines):
                print startLine, endLine, lines, lines.__class__, lines[0], lines[1], list(lines)
                lines = [line.encode('utf8') for line in lines]
                self.vim.setLines(startLine, endLine, lines)


        vim = AbstractEditor(vim)        # wrap
        vim = MethodCallerWrapper(javalib.JProxy("com.hsdl.embedit.emulation.AbstractEditor", inst=vim))  # wrap (proxy)

        jvm = javalib

    else:
        # NOTE: vim is left alone

        # -- prepare namespace
        class k:
            pass

        import com
        import java
        import net
        import org
        import javax

        jvm = k()
        jvm.com = com
        jvm.java = java
        jvm.javax = javax
        jvm.net = net
        jvm.org = org

    return vim, jvm



# find the expression that is surrounded by the two matching chars 'char_matches'
# char_matches can be '()' '{}' '<>' '[]'
# returns (start_pos, end_pos); otherwise ()

def find_surrounding_matched_exp(s, pos, char_matches):
    size = len(s)

    if len(char_matches) != 2:
        return ()

    start_char, end_char = char_matches

    p = pos

    # go back, ignoring matched pairs along the way
    nesting_level = 1
    first = 1   # we don't want to count the closing char that we happen to start on
    while p>-1:
        if s[p] == end_char and not first:
            nesting_level += 1
        elif s[p] == start_char:
            nesting_level -= 1
            if nesting_level == 0:
                break
        first = 0
        p -= 1

    if p == -1:
        return ()

    start_pos = p

    p = start_pos + 1

    # go forward and find the match, ignoring matching pairs along the way
    nest_level = 1

    while p<size:
        if s[p] == start_char:
            nest_level += 1
        elif s[p] == end_char:
            nest_level -= 1
            if nest_level == 0:
                break

        p += 1

    if p<size:
        end_pos = p
        return start_pos, end_pos+1
    else:
        return ()

# gets either the python/c or jython/java version of j wrapping based upon the type of vim emulation
# if it's not supplied, it uses sys.platform
def get_jlib(vim=None):
    from hsdl.vim import vim_emulator_jtext
    is_jtext = isinstance(vim, vim_emulator_jtext.VimEmulatorJText)

    try:
        if is_jtext or ((vim is None) and (sys.platform.find('java')==0)):
            from hsdl.java import javajlib
            return javajlib
        else:
            from hsdl.j import jlib
            return jlib
    except:
        pass

    return None


def is_temp_file(path):
    return os.path.split(path)[0] in ['/tmp', '/temp']

def get_files_matching(vim, regex, ignore_temp=1):
    regex = regex.replace('.', '<DOT>')
    regex = regex.replace('*', '.*')
    regex = regex.replace('<DOT>', r'\.')
    pat = re.compile(regex)
    paths = [buffer.name for buffer in vim.buffers]
    if ignore_temp:
        paths = filter(lambda path: not is_temp_file(path), paths)
    return filter(lambda path: pat.search(os.path.split(path)[1]) != None, paths)

# for the path, gets the content as a string, and applies fun to the string
# returns (path, fun_result)
def extract_file_info(path, fun):
    fin = open(path, 'rb')
    s = fin.read()
    fin.close()
    return (path, fun(s))


def get_fun_kw_args(fun):
    kw_args = {}

    default_values = fun.func_defaults

    if default_values:
        params = fun.func_code.co_varnames[:fun.func_code.co_argcount]
        unbound_vars = params[:-len(default_values)]
        default_vars = params[-len(default_values):]


        for i in xrange(len(default_values)):
            name = default_vars[i]
            value = default_values[i]
            kw_args[name] = value

    return kw_args


def is_vim_eclipse(vim):
    return vim and vim.__class__.__name__ in ['VimEmulatorEclipse']

def is_vim_scala_repl(vim):
    return vim and vim.__class__.__name__ in ['VimEmulatorScalaRepl']

# returns {} if does not exist
def load_scala_repl_config():
    config_path = general.interpolate_filename('${HOME}/.scala-repl-config')
    settings = {}   # name -> value
    if os.path.exists(config_path):
        fin = open(config_path, 'rb')
        s = fin.read().strip()
        fin.close()
        lines = s.split("\n")
        for line in lines:
            p = line.find("=")
            if p>=0:
                key = line[:p].strip()
                value = line[p+1:].strip()
                settings[key] = value
    return settings

def save_scala_repl_config(settings):
    config_path = general.interpolate_filename('${HOME}/.scala-repl-config')
    keys = sorted(settings.keys())

    fout = open(config_path, 'wb')
    for key in keys:
        fout.write("%s = %s" % (key.strip(), settings[key].strip()) + "\n")
    fout.close()



def get_scala_repl_config_value(key, default=None):
    settings = load_scala_repl_config()
    if key in settings:
        return settings[key]
    else:
        if default is None:
            print "Eclipse 'current_file' was not set. Set it using :H repl_file_set or updating ~/.scala-repl-config manually"
            return None
        else:
            return default


def execute_actions(vim, actions_order, actions_dir):
    path = vim.current.buffer.name
    dirname, fname = os.path.split(path)
    base, ext = os.path.splitext(fname)
    ext = ext[1:]

    shared.action_data_in = []    # each action function returns data that may be passed to the next action

    for action in actions_order:
        code, mod = actions_dir[action]
        reload(mod)
        env = {'vim' : vim,
               '_THE_MODULE_' : mod,
               'PATH' : path,
               'DIRNAME' : dirname,
               'FNAME' : fname,
               'BASE' : base,
               'EXT' : ext
              }
        the_code = '_THE_MODULE_.' + code
        try:
            r = eval(the_code, env)

            if type(r) == list:
              shared.action_data_in = r
            else:
              shared.action_data_in = []

        except Exception, e:
            print "="*100
            print "Error executing action:", action, "  -->", code
            print "="*100
            buff = cStringIO.StringIO()
            traceback.print_exc(file=buff)
            msg = buff.getvalue()
            print msg


def parse_actions(specs):
    p = specs.find('#')
    if p >= 0:
        specs = specs[:p]

    pat = re.compile(r'(?P<ignore>-)?(?P<name>[a-zA-Z0-9_]+)(?P<args>\s*\([^)]+\))?')

    found = pat.findall(specs)

    actions = []

    for ignore, name, args in found:
        if ignore != '-':
            args = args.strip()
            if args:
                args = '(vim = vim, ' + args[1:-1] + ')'
            else:
                args = '(vim = vim)'

            code = name + args

            actions.append((code, name))

    return actions


# returns list of (mod_name, mod)
def find_all_mods(vim):
    modules_vim = [os.path.splitext(os.path.split(each)[1])[0] for each in glob.glob("/tech/hsdl/lib/python/hsdl/vim/vim_command*.py")]
    all_mods = []

    for mod_name in modules_vim:
        try:
            if mod_name.startswith('vim_'):
                main_m = __import__('hsdl.vim.' + mod_name)
            else:
                main_m = __import__('hsdl.eclipse.' + mod_name)


            if mod_name.startswith('vim_'):
                mod = main_m.vim.__dict__[mod_name]
            else:
                mod = main_m.eclipse.__dict__[mod_name]


            reload(mod)

            all_mods.append((mod_name, mod))


        except:
            print "="*100
            print "Error finding mod:", mod
            print "="*100
            buff = cStringIO.StringIO()
            traceback.print_exc(file=buff)
            msg = buff.getvalue()
            print msg

    return all_mods


def check_run_actions(vim, force=0):
    if shared.IGNORE_ACTION:
      shared.IGNORE_ACTION = False  # reset it; it is meant to be ignored just once
      return

    if not is_vim_eclipse(vim):
      vim = build_vim(vim)

    all_specs = []

    s = vim.getText()
    marker = '::' + 'VIMACTIONS' + '::'
    neg_marker = '::' + '-VIMACTIONS' + '::'
    force_marker = '::' + '!VIMACTIONS' + '::'

    if  s.find(marker) >= 0 or s.find(force_marker) >= 0:
        lines = s.split("\n")
        for line in lines:
            p = line.find(neg_marker)
            if p >= 0:
                continue

            p = line.find(force_marker)
            if p >=0:
              if force:
                all_specs.append( line[p + len(force_marker):].strip() )
              else:
                continue

            p = line.find(marker)
            if p >=0:
              all_specs.append( line[p + len(marker):].strip() )

    specs = " ".join(all_specs)
    actions = parse_actions(specs)

    mods = find_all_mods(vim)

    good_found = {}     # action_name -> (code, mod)    # ensures that we only run a command once, though it be repeated
    good_found_order = []   # track the original ordering

    check_dups = {} # name -> module_name

    for action, action_name in actions:

        found = False

        for mod_name, mod in mods:

            if hasattr(mod, action_name):
                fun = getattr(mod, action_name)
                params, params_with_defaults, defaults_dict = general.get_func_params_info(fun)

                if 'vim' in params_with_defaults:
                    if action_name in check_dups and check_dups[action_name] != mod_name:
                        raise Exception("Duplicate entries for %s in these modules: %s  and %s" % (action_name, mod_name, check_dups[action_name]))
                    else:
                        check_dups[action_name] = mod_name

                        if not action_name in good_found:
                            good_found_order.append(action_name)
                        good_found[action_name] = (action, mod)

                        found = 1
                        break

        if not found:
            # if we get here, we know the method was not found
            raise Exception("Unable to find vim action: %s. [But it's possible your code inadvertently contains '#' followed by 'VIMACTIONS' and is triggering this error.] " % (action_name,))

    execute_actions(vim, good_found_order, good_found)

def get_all_actions(vim):
    for mod_name, mod in find_all_mods(vim):
        path = mod.__file__
        if path.endswith('.pyc'):
          path = path[:-4] + '.py'
        for name in mod.__dict__.keys():
            if name.startswith('action_'):
              fun = getattr(mod, name)
              line_num = -1
              try:
                line_num = fun.func_code.co_firstlineno
              except:
                pass
              params, params_with_defaults, defaults_dict = general.get_func_params_info(fun)
              if 'vim' in params_with_defaults:
                  yield name, fun, mod, path, line_num


def register_open_handlers():
    from hsdl.vim import jinteractive
    reload(jinteractive)

    # returns (path, go_to_line)
    def handler(vim, line):
        line_num, col = vim.current.window.cursor
        line = vim.current.line
        action_name = find_word(line, col)
        p = action_name.find('(')
        if p >=0:
            action_name = action_name[:p].strip()
        if action_name.startswith('-'):
            action_name = action_name[1:].strip()

        mods = find_all_mods(vim)

        for mod_name, mod in mods:

            if hasattr(mod, action_name):
                fun = getattr(mod, action_name)
                params, params_with_defaults, defaults_dict = general.get_func_params_info(fun)

                if 'vim' in params_with_defaults:
                    line_num = fun.func_code.co_firstlineno
                    path = mod.__file__
                    dirname, fname = os.path.split(path)
                    if fname.endswith('.pyc'):
                        base, _ = os.path.splitext(fname)
                        path = os.path.join(dirname, base + ".py")
                    return path, line_num

        return ()

    jinteractive.register_open_handler(handler)


def system_read2_delete(code):
    out_fname = general.getuuidtemp(prefix='racket')
    fout = open(out_fname, 'wb')
    fout.write(code)
    fout.close()

    stdout, stderr = general.system_read2("bash " + out_fname)

    if os.path.exists(out_fname):
        os.unlink(out_fname)

    return stdout, stderr

def run_action(vim, force=0, *args):
  #H_COMMAND# run_action - looks for VIMACTIONS comment and runs it
  jcommon.check_run_actions(vim, force=force)
  
  
# returns (list_of_params, list_of_params_with_defaults, dict_of_defaults)
def get_func_params_info(fun):
    all_vars = fun.func_code.co_varnames
    all_params = all_vars[:fun.func_code.co_argcount]

    defaults = fun.func_defaults
    if defaults:
        default_args = all_params[-len(defaults):]

        # match defaults args with their default values
        d = {}
        for i in xrange(len(default_args)):
            d[default_args[i]] = defaults[i]

        return all_params, default_args, d
    else:
        return all_params, [], {}

