
# ------- usage:  j-interactive.py  [rep]
# rep - j server will return result as an object, e.g. list, otherwise it'll return a string representation

import time
import random
import os
import time
import sys
import string
import traceback
import re
import types
import urllib
import cStringIO
import threading
import glob
import cPickle
import thread
import uuid
import hashlib

from hsdl.common import general
from hsdl.franca import franca, franca_comm
from hsdl.vim import shared
from hsdl.vim import vim_emulator_vim

from hsdl.eclipse import eclipse


import jcommon
import pseudofile

import vim_commands

False=0
True=1

HOME = os.getenv("HOME")

def unprotect(lines):
    pat = re.compile(r'^(?P<spaces>\s*)`')

    def sub(matchobj):
        spaces = matchobj.group('spaces')
        return spaces


    lines = map(lambda line: pat.sub(sub, line), lines)
    return lines



def get_meta_info(vim, start_row):
    if start_row < 1:
        return {}

    dict = {}

    start_line_num = int(vim.eval('line(".")'))-1       # line numbering starts at 1, but indexing starts at 0

    buff = vim.current.buffer

    i = start_row
    while i>0:
        line = string.strip(buff[i])
        if line[:2] == '::':
            p = string.find(line, '=')
            key = string.strip(line[:p])[2:]
            value = map(lambda x: string.strip(x),  string.split(string.strip(line[p+1:]), ' `` ')  )
            dict[key] = value
        else:
            break

        i -= 1

    return dict


# arg_pat = re.compile('([a-zA-Z0-9_]+__ARG)|(\*[^* )]+\*)')   # works for x__ARG  and (*whatever* ...)
arg_pat = re.compile('([a-zA-Z0-9_]+__ARG)')   # works for x__ARG  and (*whatever* ...)

# There are special identifiers that we use that j cannot understand or use directly, such as x__ARG, which we use only for
#   autocompletion and which has not run-time meaning.
# ALSO: remove lines that contain 'NB. ---'
def j_rewrite_lines(lines):
    final = map(lambda line:  arg_pat.sub('  ', line), lines)
    final = filter(lambda line: string.find(line, 'NB. ---')<0 and string.find(line, 'NB.---')<0, final)
    final = map(lambda line: jcommon.directive_pat.sub('', line), final)
    return final

# remove all "<<...>>"
def remove_directives(lines):
    return map(lambda line: jcommon.directive_pat.sub('', line), lines)



def handle_future(vim, code, lang, line_num):
    label = 'vim-' + str(uuid.uuid1())

    bash_tempfname = '/tmp/' + label + '.sh'

    shell_cmd = ''

    if lang == 'bash':
        script_tempfname = '/tmp/' + label + '.run'
        cmd = 'bash'

    elif lang in ['py', 'python']:
        script_tempfname = '/tmp/' + label + '.run'
        shell_cmd = 'export MALLOC_CHECK_=0'
        cmd = 'python'

    elif lang == 'clj':
        script_tempfname = '/tmp/' + label + '.run'
        cmd = 'clojure-script'

    elif lang == 'lfe':
        script_tempfname = '/tmp/' + label + '.run'
        cmd = 'lfe-run'

    elif lang == 'erl':
        script_tempfname = '/tmp/' + label + '.run'
        code = """
            main(Args) ->
            \n
        """ + code
        cmd = 'escript'

    elif lang in ['ecl', 'lisp']:
        script_tempfname = '/tmp/' + label + '.run'
        code = """
            (load "/tech/hsdl/lib/lisp/hsdl/prelude.lisp")

            (with-output-to-string (*standard-output*)
                (require :trivial-backtrace)
                (require :pcond)
                (require :uuid)
                (require :xref)
                (load "/tech/hsdl/play/lisp/prolog.lisp")
                (load "/tech/hsdl/play/lisp/logic.lisp")
                (load "/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp"))

            (setf *mind-buffer-name* "%s")

            (print (try-backtrace (eval (progn %s)))  )
            (finish-output)

        """ % (vim.current.buffer.name, code)
        cmd = 'ecl-py-run'

    elif lang == 'abcl':
        script_tempfname = '/tmp/' + label + '.run'
        #code = """
        #    %s
        #    (exit)
        #""" % code
        code = """
            (load "/tech/hsdl/lib/lisp/hsdl/prelude.lisp")

            (with-output-to-string (*standard-output*)
                (require :trivial-backtrace)
                (require :pcond)
                (require :uuid)
                (require :xref)
                (load "/tech/hsdl/play/lisp/prolog.lisp")
                (load "/tech/hsdl/play/lisp/logic.lisp")
                (load "/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp"))

            (setf *mind-buffer-name* "%s")

            (print (try-backtrace (eval (progn %s)))  )
            (finish-output)
            (exit)

        """ % (vim.current.buffer.name, code)
        cmd = 'abcl --load '


    elif lang == 'sbcl':
        script_tempfname = '/tmp/' + label + '.run'
        code = """
            (load "/tech/hsdl/lib/lisp/hsdl/prelude.lisp")

            (with-output-to-string (*standard-output*)
                (require :trivial-backtrace)
                (require :pcond)
                (require :uuid)
                (require :xref)
                (load "/tech/hsdl/play/lisp/prolog.lisp")
                (load "/tech/hsdl/play/lisp/logic.lisp")
                (load "/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp"))

            (setf *mind-buffer-name* "%s")

            (print (try-backtrace (eval (progn %s)))  )
            (finish-output)
        """ % (vim.current.buffer.name, code)
        cmd = 'sbcl --script '

    elif lang == 'chicken':
        script_tempfname = '/tmp/' + label + '.run'
        cmd = 'csi -script '

    elif lang == 'sisc':
        script_tempfname = '/tmp/' + label + '.run'
        code = """
            (case-sensitive #t)
            (hsdl-load "hsdl/prelude.scm")
            (hsdl-load "hsdl/python.scm")
            (hsdl-load "hsdl/objs.scm")
            (hsdl-load "/tech/frontier/notes/mind/prelude.scm")

            \n
        """ + code
        #cmd = 'sisc -x '
        cmd = 'jythonsisc'

    elif lang == 'mzscheme':
        script_tempfname = '/tmp/' + label + '.run'
        cmd = 'mzscheme --script '

    else:
        script_tempfname = '/tmp/' + label + '.run'
        cmd = 'myjconsole'

    base_fname = os.path.join(HOME, 'done/%s' % label)

    fout = open(base_fname + '.job', 'wb')
    fout.write('')
    fout.close()

    buffname = vim.current.buffer.name
    fout = open(base_fname + '.info', 'wb')
    fout.write(buffname + '#' + str(line_num) + ' ' + str(time.time()) + '\n')
    fout.close()

    #NB: because we pipe output to tee, you may have to deal with how stdout is flushing
    fout = open(bash_tempfname, 'wb')
    SCRIPT = """source %s/.bashrc
                %s
                python -c 'import time; print time.time()' >> %s.time
                %s  %s | tee  %s.job
                python -c 'import time; print time.time()' >> %s.time
                mv %s.job  %s.done
                # ---- remove self ----
                #rm %s
            """ % (HOME, shell_cmd, base_fname, cmd, script_tempfname, base_fname, base_fname, base_fname, base_fname, script_tempfname)
    fout.write(SCRIPT)
    fout.close()

    fout = open(script_tempfname, 'wb')

    s = jcommon.clean_future_refs(code)

    if cmd == 'myjconsole':
        s = j_rewrite_lines([s])[0]
        s3 = string.join(jcommon.ignore_special_lines(string.split(s,'\n')), '\n')
        fout.write("FUN=: 3 : 0\n")
        fout.write(s3 + '\n')
        fout.write(")\n\n")
        fout.write("""  (FUN :: (pr @: ('NB. !!!!!!!!!!! error running script !!!!!!!!!'"_))) 0 \n""")
        fout.write("\nexit''\n")
    elif cmd == 'python':
        fout.write('if 1:\n')       # likely, the code will be indented, so introduce it with this fully dedented true expression
        fout.write(s + '\n')
    else:
        fout.write(s + '\n')

    fout.close()

    os.system(""" screen -x -r main -p ALWAYS -X screen -t %s bash %s """ % (label, bash_tempfname))

    return label,  time.time()

def clear_future_files(label):
    base_fname = os.path.join(HOME, 'done/%s' % label)
    if os.path.exists(base_fname + '.done'):
        os.unlink(base_fname + '.done')

    if os.path.exists(base_fname + '.time'):
        os.unlink(base_fname + '.time')

    if os.path.exists(base_fname + '.info'):
        os.unlink(base_fname + '.info')

    if 1:
        script_fname = os.path.join('/tmp', label + '.sh')      ###!
        if os.path.exists(script_fname):
            os.unlink(script_fname)



# look for <<NAME:...>> or <<REPEAT:__:...>>
def extract_name(lines):
    pat = re.compile(r'<<NAME:(?P<name>[^>]+)>>')
    pat2 = re.compile(r'<<REPEAT(_DOWN)?:[^:]+:(?P<name>[^>]+)>>')

    s = string.join(lines, '')
    r = pat.search(s)
    if r:
        return r.group('name')
    else:
        r = pat2.search(s)
        if r:
            return r.group('name')
        else:
            return ''


def dump_to_output(dump_fname, code_name, lines):
    MARK = ' ::: ' + code_name + ' ::: ========================================================='
    dump_fname.write(MARK + '\n' + string.join(lines, '\n') + '\n')

def update_output(vim, output_info, start_row, end_row, old_lines, new_lines, new_window=0, orig_cursor=(), orig_mode='n', refresh=0, output_indent=None):        # *************
    orig_name = vim.current.buffer.name
    buffer = vim.current.buffer

    # ---------------------------------
    original_output = get_output_text(vim, output_info)
    original_lines = string.split(string.strip(jcommon.rewrite_data(original_output)), '\n')
    original_lines = [string.strip(line) for line in original_lines]
    if not output_indent is None:
        original_lines= jcommon.indent_lines(original_lines, output_indent+1)
    # ---------------------------------


    if output_info:
        output_line_start, output_col, output_line_end, output_col_end = output_info

        if new_window:
            #final_lines = old_lines + jcommon.tag_data_lines(new_lines)
            final_lines = jcommon.tag_data_lines(new_lines)
            final_lines = jcommon.fix_unbalanced_parens(final_lines)

            #tempfname = general.mklocaltemp() + '.mind'
            tempfname = general.local_hsdl_mktemp('INF__') + '.mind'
            vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa
            new_buffer = vim.current.buffer

            new_buffer[:] = final_lines + ['']

            if 0:
                z = string.join(final_lines, '\n')
                vim.buffer_replace_string(output_line_start-1, output_col, output_line_end-1, output_col_end, z)

            vim.current.window.cursor = (1, 0)  # move to top
            vim.command("set nomodified")

            # -- go back to original
            vim.go_to_opened_buffer(orig_name)
        else:

            if orig_mode == 'i':
                #final_lines = jcommon.tag_data_lines(original_lines + [''] + new_lines)    # append
                final_lines = jcommon.tag_data_lines(new_lines + [''] + original_lines)     # prepend
            else:
                final_lines = jcommon.tag_data_lines(new_lines)

            final_lines = map(lambda line: (' '*(output_col)) + line, final_lines)
            final_lines = jcommon.fix_unbalanced_parens(final_lines)

            #r = string.split(string.strip(original_output) + '\n' + last, '\n')          # prepend the original output to new output

            z = '(__OUT__ """\n' + string.join(final_lines, '\n') + '""")'
            this_current_cursor = vim.current.window.cursor
            vim.buffer_replace_string(output_line_start-1, output_col, output_line_end-1, output_col_end, z)
            vim.current.window.cursor = this_current_cursor
    else:
        final_lines = jcommon.tag_data_lines(new_lines)

        if new_window:
            tempfname = general.local_hsdl_mktemp('INF__') + '.mind'
            vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa
            new_buffer = vim.current.buffer
            new_buffer[:] = final_lines + ['']
            vim.current.window.cursor = (1, 0)  # move to top
            vim.command("set nomodified")
            toggle_buffer(vim)
        else:
            final_lines = jcommon.fix_unbalanced_parens(final_lines)
            jcommon.replace_vim_lines(buffer, start_row, end_row, final_lines + [''])

    if orig_cursor:
        # it's possible that you're placed on a line that no longer exists, such as after a deletion
        try:
            vim.current.window.cursor = orig_cursor
        except:
            pass


    if refresh:
        pass #vim.command("redraw")



def erl_lfe(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, ext=None, output_info=(), orig_cursor=(), orig_mode='n', outputter_fun=None):
    reload(jcommon)

    s = string.join(jcommon.ignore_special_lines(j_rewrite_lines(lines)), '\n')       # remove instances of x__ARG

    buffer = vim.current.buffer

    if string.find(s, '%::ERL::%')>=0 or ext == 'erl':
        set_exec_lang_ext('erl')
        remote_args = ['servers.eval:eval_erl', s]
    else:
        set_exec_lang_ext('lfe')
        remote_args = ['servers.eval:eval_lfe', s, 0, "the_lfe_service"]

    try:
        status, s = jcommon.send_action_franca_nonblocking('erl', remote_args, port=16020, machine='worlddb')
    except:
        vim.current.window.cursor = orig_cursor
        buff = cStringIO.StringIO()
        traceback.print_exc(file=buff)
        print buff.getvalue()
        print "Socket call terminated"
        return


    if status == "error":
        r = string.split("+++++++++++ EXCEPTION +++++++++\n" + s, '\n') + ['']
    else:
        r = string.split(s, '\n') + ['']

    new_lines = jcommon.indent_lines(r, curr_indent+1)

    if dump_fname:
        name = extract_name(lines)
        dump_to_output(dump_fname, name, new_lines)

    if outputter_fun:
        outputter_fun(new_lines)
    else:
        update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************



def pyeval(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname='', output_info=(), orig_cursor=(), orig_mode='n', outputter_fun=None):
    reload(jcommon)

    G = shared.GLOBALS
    if not G:
        G = globals()

    r = None
    import ast
    import _ast
    if isinstance(ast.parse(s).body[-1], _ast.Expr):    # all we care about is whether the last object is an expr
        r = eval(s, G, G)
    else:
        exec s in G, G

    if r is None:
        return
    else:
        import ppprint
        r = ppprint.pformat(r)

        new_lines = r.split('\n')

        if outputter_fun:
            outputter_fun(new_lines)
        else:
            if dump_fname:
                name = extract_name(lines)
                dump_to_output(dump_fname, name, new_lines)

            update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************


def get_output_text(vim, output_info):
    if output_info:
        row_start, col_start, row_end, col_end = output_info
        lines = vim.current.buffer[row_start-1:row_end]
        s = string.join(lines, '\n')
        pat = re.compile(r'\(\s*__OUT__\s+"""(?P<inside>.+?)"""\s*\)', re.DOTALL)
        r = pat.search(s)
        if r:
            return r.group('inside')

    return ''

def wait_for_lfe_result(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, ext=None, output_info=(), orig_cursor=(), orig_mode='n', original_output=''):

    last = ""

    if 0:
        original_output = get_output_text(vim, output_info)
        original_lines = string.split(string.strip(jcommon.rewrite_data(original_output)), '\n')
        original_lines = [string.strip(line) for line in original_lines]
        original_output = string.join(original_lines, '\n')

    while 1:
        try:
            last  = franca_comm.send_action_franca('erl', ['servers.eval:lfe_get'], port=15020, machine='worlddb', timeout_on=1)
        except:
            buff = cStringIO.StringIO()
            traceback.print_exc(file=buff)
            last = ('=' * 80) + '\n' + buff.getvalue() + '\n' + ('=' * 80) + '\n'
            break


        jcommon.debug_log(repr(last))

        if shared.LFE_WAIT_STOP:
            last = '<<<<<<<<<<< STOPPED >>>>>>>>>>>'
            break

        if last:
            break

        time.sleep(2)

    if not last:
        #vim.command("set noreadonly")
        return

    jcommon.debug_log('DONE')

    #r = string.split(string.strip(original_output) + '\n' + last, '\n')          # prepend the original output to new output
    r = string.split(last, '\n')          # prepend the original output to new output


    new_lines = jcommon.indent_lines(r, curr_indent+1)

    if dump_fname:
        name = extract_name(lines)
        dump_to_output(dump_fname, name, new_lines)

    #vim.command("set noreadonly")
    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************
    if orig_mode == 'i':
        old_row, old_col = orig_cursor
        vim.current.window.cursor = (old_row+1, old_col)
        num_spaces = jcommon.get_num_leading_spaces(s)
        vim.insert_lines(['', ' '*num_spaces])
        vim.current.window.cursor = (old_row+2, num_spaces)
        vim.enter_insert_mode()
    else:
        vim.current.window.cursor = orig_cursor

def lfe_wait_stop(vim):
    shared.LFE_WAIT_STOP = 1



def async_erl_lfe(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, ext=None, output_info=(), orig_cursor=(), orig_mode='n'):
    from hsdl.franca import franca, franca_comm


    s = string.join(jcommon.ignore_special_lines(j_rewrite_lines(lines)), '\n')       # remove instances of x__ARG

    buffer = vim.current.buffer
    if string.find(s, '%::ERL::%')>=0 or ext == 'erl':
        set_exec_lang_ext('erl')
        r = franca_comm.send_action_franca('erl', ['servers.eval:eval', s], port=15020, machine='worlddb')
        #print "^"*40, r
        r = [repr(r)]
    else:
        # the returned string may contain new lines, because it is pretty printing
        set_exec_lang_ext('lfe')
        shared.LFE_WAIT_STOP = 0
        franca_comm.send_action_franca('erl', ['servers.eval:lfe_cmd', s], port=15020, machine='worlddb', timeout_on=1)
        #thread.start_new_thread(wait_for_lfe_result,  (vim, s, lines, start_row, end_row, curr_indent, new_window, dump_fname, ext, output_info, orig_cursor, orig_mode))
        wait_for_lfe_result(vim, s, lines, start_row, end_row, curr_indent, new_window, dump_fname, ext, output_info, orig_cursor, orig_mode)
        return

    new_lines = jcommon.indent_lines(r, curr_indent+1)

    if dump_fname:
        name = extract_name(lines)
        dump_to_output(dump_fname, name, new_lines)

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************



def scala(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    set_exec_lang_ext('scala')

    r = string.split(jcommon.scala_eval(vim, s), '\n')
    new_lines = jcommon.indent_lines(r, curr_indent+1)

    if dump_fname:
        name = extract_name(lines)
        dump_to_output(dump_fname, name, new_lines)

    new_lines = jcommon.tag_data_lines(new_lines)

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode)        # *************

    return

    if new_window:
        tempfname = general.mklocaltemp() + '.mind'
        vim.open_new_tab(tempfname)
        buffer = vim.current.buffer
        buffer[:] = final_lines

        vim.current.window.cursor = (1, 0)  # move to top
        vim.command("set nomodified")
    else:
        jcommon.replace_vim_lines(buffer, start_row, end_row, final_lines)


def display_sisc_parsing(s):
    from hsdl.schemepy.skime.compiler.parser import Parser
    p = Parser(s); z = p.parse()
    from hsdl.schemepy.skime.types.symbol import Symbol

    if isinstance(z.car, Symbol) and z.car.name == 'quasiquote':
        z = z.rest.car

    if isinstance(z.car, Symbol):
        if z.car.name == '::sisc::':
            print "::SISC::"
        elif z.car.name == '::j::':
            print z.rest.start, z.rest.end
            print s[z.rest.start:z.rest.end]
            print "::J::"

    return # ============

    reg = p.registry
    keys = reg.keys()
    keys.sort()

    for a,b in keys:
        if reg[(a,b)]:
            sub = s[a:b]
            if sub:
                print "|" + s[a:b] + "|              ", reg[(a,b)]


# ---- may not be usable under jython ---
if sys.subversion[0] == 'CPython':
    from hsdl.schemepy.skime.types.pair import Pair
    from hsdl.schemepy.skime.types.symbol import Symbol



def check_let(obj):
    if isinstance(obj, Pair):
        if isinstance(obj.car, Symbol):
            if obj.car.name == 'let-compl':
                return 1
    return 0


def get_lets(obj):
    names = []
    z = obj.rest.car
    while z:
        if isinstance(z, Pair):
            names.append((z.car.car.name, z.car.rest.car))
        z = z.rest
    names.reverse()
    return names


def sisc_find_lets(obj, closest, sofar):
    if obj == closest:
        return sofar

    elif isinstance(obj, Pair):
        is_let = check_let(obj)
        sublets = []
        more = []
        if is_let:
            sublets = get_lets(obj)
            return sisc_find_lets(obj.rest.rest, closest, sublets + sofar)
        else:
            a1 = sisc_find_lets(obj.car, closest, sofar)
            if a1:
                return a1

            z = obj.rest
            while z:
                a1 = sisc_find_lets(z, closest, sofar)
                if a1:
                    return a1
                z = z.rest

            return []

    elif isinstance(obj, Symbol):
        return []
    else:
        return []



# returns (nearest-symbol,  list-of-lets)
def get_sisc_context(vim, code, start_row, end_row, curr_indent):
    pos = int(vim.eval('line2byte(line("."))+col(".")')) - 1 - 1
    pos1 = int(vim.eval('line2byte(' + str(start_row) + ')')) - 1
    pos2 = int(vim.eval('line2byte(' + str(end_row+1) + ')')) - 1 - 1

    rel_pos = pos - pos1
    print "||" + code[rel_pos:rel_pos+10] + "||"
    from hsdl.schemepy.skime.compiler.parser import Parser
    p = Parser(code); z = p.parse()

    closest = 0
    closest_start = 0
    for start, end in p.registry.keys():
        v = string.strip(code[start:end])
        if end > closest and end < rel_pos:
            closest = end
            closest_start= start

    if closest==0 and closest_start == 0:
        return ('', [])

    c = p.registry[(closest_start, closest)]
    if hasattr(c, 'car'):
        c = c.car

    from hsdl.schemepy.skime.types.symbol import Symbol
    nearest = ''
    if isinstance(c, Symbol):
        nearest = c.name

    print "<<<" + code[rel_pos:rel_pos+20] + ">>  ", closest, "    CLOSEST: ||" + code[closest_start:closest_start+10] + "||"

    print type(z.rest)
    zz = sisc_find_lets(z, c, [])
    print "LLLLLL:", zz
    return (nearest, zz)



def bash(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n', outputter_fun = None):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s2 = jcommon.rewrite_triple_quotes(s)

    s = s2

    import uuid
    label = 'vim-' + str(uuid.uuid1())
    bash_tempfname = '/tmp/' + label + '.sh'

    label = 'vim-' + str(uuid.uuid1())
    bash_tempfname_major = '/tmp/' + label + '.sh'

    label = 'vim-' + str(uuid.uuid1())
    bash_tempfname_output = '/tmp/' + label + '.sh'

    fout = open(bash_tempfname_major, 'wb')
    fout.write("bash %s >& %s" % (bash_tempfname, bash_tempfname_output))
    fout.close()

    fout = open(bash_tempfname, 'wb')
    fout.write(s)
    fout.close()

    os.system("bash %s" % bash_tempfname_major)

    if 1:
        fin = open(bash_tempfname_output, 'rb')
        s = fin.read()
        fin.close()

        os.unlink(bash_tempfname)
        os.unlink(bash_tempfname_major)
        os.unlink(bash_tempfname_output)

        new_lines = string.split(s, '\n')

        if outputter_fun:
            outputter_fun(new_lines)
        else:
            update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode)        # *************

def python(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s2 = jcommon.rewrite_triple_quotes(s)

    s = s2

    import uuid
    label = 'vim-' + str(uuid.uuid1())
    bash_tempfname = '/tmp/' + label + '.sh'

    label = 'vim-' + str(uuid.uuid1())
    bash_tempfname_major = '/tmp/' + label + '.sh'

    label = 'vim-' + str(uuid.uuid1())
    bash_tempfname_output = '/tmp/' + label + '.sh'

    fout = open(bash_tempfname_major, 'wb')
    fout.write("python %s >& %s" % (bash_tempfname, bash_tempfname_output))
    fout.close()

    # -------------
    prefix = ''
    if shared.VIM_OUTPUT_PATH:
        prefix = 'VIM_OUTPUT_PATH = "%s"\n' % shared.VIM_OUTPUT_PATH
        prefix += """def vim_output(s):\n  fout = open(VIM_OUTPUT_PATH, 'wb')\n  fout.write(s)\n  fout.close()\n"""
    else:
        prefix += """def vim_output(s):\n  pass\n"""

    s = prefix + '\nif 1:\n' + s        # "if 1:" allows out script to be indented

    fout = open(bash_tempfname, 'wb')
    #fout.write('if 1:\n')           # this allows our script to be indented
    fout.write(s)
    fout.close()

    os.system("bash %s" % bash_tempfname_major)     #!!! execution here

    fin = open(bash_tempfname_output, 'rb')
    s = fin.read()
    fin.close()

    os.unlink(bash_tempfname)
    os.unlink(bash_tempfname_major)
    os.unlink(bash_tempfname_output)

    new_lines = string.split(s, '\n')

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode)        # *************



def chicken(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s2 = jcommon.rewrite_triple_quotes(s)

    s = s2

    import uuid
    label = 'vim-' + str(uuid.uuid1())
    bash_tempfname = '/tmp/' + label + '.sh'

    label = 'vim-' + str(uuid.uuid1())
    bash_tempfname_major = '/tmp/' + label + '.sh'

    label = 'vim-' + str(uuid.uuid1())
    bash_tempfname_output = '/tmp/' + label + '.sh'

    fout = open(bash_tempfname_major, 'wb')
    fout.write("csi -script %s >& %s" % (bash_tempfname, bash_tempfname_output))
    fout.close()

    fout = open(bash_tempfname, 'wb')
    fout.write("""(let* ((result (begin %s))
                         (sout (open-output-string)))
                        (pretty-print result sout)
                        (flush-output sout)
                        (display (get-output-string sout)))""" % s)
    fout.close()

    os.system("bash %s" % bash_tempfname_major)

    if 1:
        fin = open(bash_tempfname_output, 'rb')
        s = fin.read()
        fin.close()

        os.unlink(bash_tempfname)
        os.unlink(bash_tempfname_major)
        os.unlink(bash_tempfname_output)

        new_lines = string.split(s, '\n')

        update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor)        # *************


def sisc(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), catch_exception=1, orig_mode='n'):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s2 = jcommon.rewrite_triple_quotes(s)

    s = s2

    set_exec_lang_ext('scm')

    #display_sisc_parsing(s)

    #start_row, end_row, s = vim.get_selection()
    #nearest, lets = get_sisc_context(vim, s, start_row, end_row, curr_indent)


    if 0:
        print "="*70
        print s
        print "="*70

    if string.find(s, '(:=use ')>=0 or string.find(s, '(:=within ')>=0 or string.find(s, '(:=load ')>=0:
        r = jcommon.sisc_rewrite_exec(vim, s, catch_exception=catch_exception)
    else:
        r = jcommon.send_to_sisc(vim, s)        # regular execution

    if r == None:       # very likely signifies exception
        return

    r = string.split(r, '\n')

    new_lines = jcommon.indent_lines(r, curr_indent+1)

    jcommon.sisc_clean_temp(vim)        # possibly, temp variables were created above; remove them

    if dump_fname:
        name = extract_name(lines)
        dump_to_output(dump_fname, name, new_lines)

    new_lines = jcommon.tag_data_lines(new_lines)  + ['']

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode)        # *************



def rkt(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), catch_exception=1, orig_mode='n'):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s2 = jcommon.rewrite_triple_quotes(s)

    s = s2

    set_exec_lang_ext('rkt')

    if 0:
        print "="*70
        print s
        print "="*70

    from hsdl.vim import racket_helper
    r = repr(racket_helper.racket_eval(s))

    if r == None:       # very likely signifies exception
        return

    r = string.split(r, '\n')

    new_lines = jcommon.indent_lines(r, curr_indent+1)

    if dump_fname:
        name = extract_name(lines)
        dump_to_output(dump_fname, name, new_lines)

    new_lines = jcommon.tag_data_lines(new_lines)  + ['']

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode)        # *************




def find_all_data_refs(sexp, dict):
    if type(sexp.obj) == list:
        for each in sexp:
            if type(each.obj) == list:
                if each[0] == ('-->',):
                    key = each[1].obj[0]
                    dict[key] = (each.start, each.end, each.line_num, each.line_col)
            find_all_data_refs(each, dict)
    else:
        pass

def range_interpolate(s, interp_list):
    final = []
    last = 0
    for (start, end, _line_num, _line_col), sub in interp_list:
        final.append(s[last:start])
        final.append(sub)
        last = end
    final.append(s[last:])
    return string.join(final, '')


def sisc_show_data(vim, catch_exception=1):
    from hsdl.vim import jcommon
    reload(jcommon)

    vim.sign_clear()

    path = vim.current.buffer.name

    orig_cursor = vim.current.window.cursor

    ancs = vim.find_ancestors()

    block = None

    if 1:
        cursor_row, _ = vim.current.window.cursor
        _, main_block, col, main_start_row, col1, end_row, col2 = ancs[0]
        sexp, main_block2 = full_parse_sexp(main_block, col)

        for subsexp in sexp[1:]:
            #print subsexp.line_num
            this_start_row = main_start_row              # start with parent's start_row
            this_start_row += subsexp.line_num
            this_block = subsexp.obj

            if type(this_block) == types.StringType:
                this_end_row = this_start_row + len(string.split(this_block, '\n')) - 1
                if cursor_row >= this_start_row  and cursor_row <= this_end_row:
                    start_row = this_start_row
                    end_row = this_end_row
                    block = this_block
                    block = main_block[subsexp.start : subsexp.end]

    #TODO a hack!
    p = string.find(block, '"""')
    if p>=0:
        block = block[:p]

    if 0:
        print "H"*80
        print block
        print "H"*80

    starting_line = orig_cursor[0]

    if not block:
        return

    orig_s = block

    full_sexp, _ = full_parse_sexp(orig_s, 0)
    refs_dict = {}
    if full_sexp:
        find_all_data_refs(full_sexp, refs_dict)


    orig_start = full_sexp.start

    new_s = jcommon.sisc_rewrite_show_data(vim, orig_s, catch_exception=catch_exception)

    if new_s == None: return    # very likely signifies exception

    sexp, _ = full_parse_sexp(new_s, 0)

    if not sexp: return

    d = {}
    for pair in sexp:
        key = pair[0].obj[0]
        val_str = new_s[pair[1].start:pair[1].end]
        d[key] = val_str

    signs_lines = []

    interp_list = []
    for key, tup in refs_dict.items():
        if d.has_key(key):
            value = d[key]
            _, _, the_line_num, the_line_col = tup
            the_line_num += (starting_line + 2)     #TODO hack (2)
            real_line_col = the_line_col + len(key) + 3
            value2 = jcommon.string_shift_col(value, real_line_col)
            interp_list.append((tup, "(--> %s %s)" % (key, value2)))
            signs_lines.append(the_line_num)

    interp_list.sort()

    s2 = range_interpolate(orig_s, interp_list)

    all_lines = string.split(orig_s, '\n')
    num_lines = len(all_lines)

    start_line = starting_line + full_sexp.line_num
    start_col = full_sexp.line_col
    end_line = starting_line + num_lines
    end_col = len(all_lines[-1])-1


    if 0:
        print "V"*80
        print start_line, start_col, end_line, end_col
        print "V"*80

    s2 = s2[orig_start:]

    vim.buffer_replace_string(start_line+1, start_col+1, end_line, end_col, s2) #line1, col1, line2, col2, new_str)

    jcommon.sisc_clean_temp(vim)        # possibly, temp variables were created above; remove them

    for the_line_num in signs_lines:
        vim.add_sign(the_line_num, path, open_if_not_opened=False, symbol='data')

    vim.current.window.cursor = orig_cursor

def mzscheme(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    reload(jcommon)
    from hsdl.vim import mzscheme_common
    reload(mzscheme_common)

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s2 = jcommon.rewrite_triple_quotes(s)

    s = s2

    r = mzscheme_common.send_to_mzscheme_eval(vim, s)

    if r == None:       # very likely signifies exception
        return

    r = string.split(r, '\n')

    new_lines = jcommon.indent_lines(r, curr_indent+1)

    new_lines = jcommon.tag_data_lines(new_lines)  + ['']

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************



def slime_lisp(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    reload(jcommon)
    from hsdl.vim import mzscheme_common
    reload(mzscheme_common)

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s2 = jcommon.rewrite_triple_quotes(s)

    s = s2

    r = jcommon.lisp_eval(vim, s)
    r = string.split(r, '\n')

    if 1:

        #new_lines = jcommon.indent_lines(r, curr_indent+1)
        new_lines = jcommon.tag_data_lines(r)
        jcommon.lisp_display_info(vim, new_lines, orig_cursor)

        return

        path = vim.current.buffer.name
        tempfname = general.local_hsdl_mktemp('INF__') + '.mind'

        vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa

        buffer = vim.current.buffer
        size = len(buffer[:])

        buffer[size-1:size] = new_lines + ['']
        vim.command("set nomodified")
        vim.command("normal G")
        vim.command(":vertical resize 50")

        vim.go_to_opened_buffer(path)
        vim.current.window.cursor = orig_cursor

        #update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode)        # *************

    else:
        r = string.split(msg, '\n')

        new_lines = jcommon.indent_lines(r, curr_indent+1)

        new_lines = jcommon.tag_data_lines(new_lines)  + ['']

        update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************


def lisp(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    reload(jcommon)
    from hsdl.vim import mzscheme_common
    reload(mzscheme_common)

    buffer = vim.current.buffer

    shared.THREAD.join()
    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')
    s = jcommon.rewrite_triple_quotes(s)
    r = jcommon.lisp_eval(vim, s)
    new_lines = string.split(r, '\n')

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************


def handle_factor(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    set_exec_lang_ext('factor')

    r = jcommon.factor_eval(vim, s)

    if r == None:       # very likely signifies exception
        return

    r = string.lstrip(r)
    r_lines = string.split(r, '\n')
    r_lines = filter(lambda line: string.find(line, '( scratchpad )')<0, r_lines)
    r_lines = filter(lambda line: string.find(line, '--- Data stack:')<0, r_lines)

    new_lines = jcommon.tag_data_lines( jcommon.indent_lines(r_lines, curr_indent+1) ) + ['']

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************

    return

    if new_window:
        tempfname = general.mklocaltemp() + '.mind'
        vim.open_new_tab(tempfname)
        buffer = vim.current.buffer
        buffer[:] = final_lines

        vim.current.window.cursor = (1, 0)  # move to top
        vim.command("set nomodified")
    else:
        jcommon.replace_vim_lines(buffer, start_row, end_row, final_lines)



def handle_clojure(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s = jcommon.rewrite_triple_quotes(s)

    set_exec_lang_ext('clj')

    r = jcommon.clojure_eval(vim, s)

    if r == None:       # very likely signifies exception
        return

    new_lines = jcommon.tag_data_lines( jcommon.indent_lines(string.split(r, '\n'), curr_indent+1) ) + ['']

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************

    return

    if new_window:
        tempfname = general.mklocaltemp() + '.mind'
        vim.open_new_tab(tempfname)
        buffer = vim.current.buffer
        buffer[:] = final_lines

        vim.current.window.cursor = (1, 0)  # move to top
        vim.command("set nomodified")
    else:
        jcommon.replace_vim_lines(buffer, start_row, end_row, final_lines)



def handle_haskell(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s = jcommon.rewrite_triple_quotes(s)

    set_exec_lang_ext('hs')

    r = jcommon.haskell_external_eval(vim, s)

    if r == None:       # very likely signifies exception
        return

    new_lines = jcommon.tag_data_lines( jcommon.indent_lines(string.split(r, '\n'), curr_indent+1) ) + ['']

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************


def handle_scala(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.franca import franca, franca_comm

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(remove_directives(jcommon.ignore_special_lines(string.split(s, '\n'))), '\n')

    s = jcommon.rewrite_triple_quotes(s)

    set_exec_lang_ext('hs')

    r = jcommon.scala_external_eval(vim, s)

    if r == None:       # very likely signifies exception
        return

    new_lines = jcommon.tag_data_lines( jcommon.indent_lines(string.split(r, '\n'), curr_indent+1) ) + ['']

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************



def clp(vim, s, lines, start_row, end_row, curr_indent, new_window=False, dump_fname=None, output_info=(), orig_cursor=(), orig_mode='n'):
    from hsdl.franca import franca, franca_comm

    print "="*80
    print s
    print "="*80
    print lines
    print "="*80

    return

    buffer = vim.current.buffer

    lines = jcommon.ignore_special_lines(lines)

    s = string.join(jcommon.ignore_special_lines(string.split(s, '\n')), '\n')

    set_exec_lang_ext('ecl')
    r = string.split(jcommon.send_to_clp(vim, s), '\n')
    new_lines = jcommon.indent_lines(r, curr_indent+1)

    if dump_fname:
        name = extract_name(lines)
        dump_to_output(dump_fname, name, new_lines)

    new_lines = jcommon.tag_data_lines(new_lines)

    new_lines += ['']

    update_output(vim, output_info, start_row, end_row, lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=curr_indent)        # *************

    return #==============

    if new_window:
        tempfname = general.mklocaltemp() + '.mind'
        vim.open_new_tab(tempfname)
        buffer = vim.current.buffer
        buffer[:] = final_lines

        vim.current.window.cursor = (1, 0)  # move to top
        vim.command("set nomodified")
    else:
        jcommon.replace_vim_lines(buffer, start_row, end_row, final_lines)



def set_exec_lang_ext(ext):
    if ext:
        shared.LANG_EXT = ext


def get_exec_lang_ext():
    return shared.LANG_EXT

def check_lang(s, marker, curr_ext, ext):
    p = string.find(s, marker)
    if p>=0:
        return 1
    else:
        return 0
        #return curr_ext == ext

def vimcallj_repeat_down(vim, visualize=False, force_new_window=False, repeat_down=0, repeat_set='', dump_fname=None, ext=None):
    if not ext:
        ext = vim.get_current_language(ext)

    buffer = vim.current.buffer
    start_line_num = int(vim.eval('line(".")'))
    line_num = start_line_num - 1

    if line_num < 1:        # if you start on the first line, the first block is skipped by the while loop below,
                            # so let's force it to be done
        vimcallj(vim, visualize=visualize, force_new_window=force_new_window, repeat_down=1, repeat_set=repeat_set, dump_fname=dump_fname, ext=ext)
        line_num = 1

    vim.current.window.cursor = (line_num, 0)  # position cursor right before the line

    # keep off iteration
    while 1:
        buffer = vim.current.buffer
        line_num = int(vim.eval('line(".")'))

        size = len(vim.current.buffer)
        i = line_num
        found = 0

        while (i+1) < size:
            buffer = vim.current.buffer
            size = len(vim.current.buffer)

            line = buffer[i]
            if string.find(line, '<<REPEAT')>=0:      # it could be REPEAT or REPEAT_DOWN
                found = 1
                vim.current.window.cursor = (i+1, 0)  # move to top
                if string.strip(line)[0] == '`':
                    vimsendjdata(vim, silent=1)
                else:
                    vimcallj(vim, visualize=visualize, force_new_window=force_new_window, repeat_down=1, repeat_set=repeat_set, dump_fname=dump_fname, ext=ext)
                    if force_new_window:
                        break

            i += 1

        if not found: break

    if not force_new_window:
        vim.current.window.cursor = (start_line_num, 0)  # move to top

    if 0:   # ---- bad attempt to clear undo stack ---------; DOES NOT WORK!!!
            # clear undo history
            vim.command(":set undolevels=-1")
            vim.command(":silent! keepjumps 0,")
            vim.command(":let &undolevels = 1000")


def get_repeat_set(s):
    pat = re.compile(r'<<REPEAT(_DOWN)?:(?P<name>[^>:]+)')
    r = pat.search(s)
    if r:
        return r.group('name')
    else:
        return ''

# remember: make sure your code calls the j verb 'VISUALIZE', which assigns your data to VISUALIZE_VALUE, which
# is then used by the wxpython code

def visualize_data_using_wx(vim, code):
    data = jcommon.callj_value(vim, code)

    #jcommon.execDosScript("c:/apps/python24/python24.exe  h:/hsdl/lib/python/hsdl/vim/grid.py", start_path="h:/hsdl/lib/python/hsdl/vim/", title='mrxvt_bat')
    is_win32 = vim.eval('has("win32")') == '1'
    if is_win32:
        jcommon.launchProcess("grid", "c:/apps/python24/python24.exe", ["h:/hsdl/lib/python/hsdl/vim/grid.py"], start_path="h:/hsdl/lib/python/hsdl/vim/", sep_console=False, is_win32=is_win32)
    else:
        label = 'temp-' + str(uuid.uuid1())
        tempfname = '/tmp/' + label + '.pickle'
        fout = open(tempfname, 'wb')
        fout.write(cPickle.dumps(data))
        fout.close()

        jcommon.launchProcess("grid", "python", ["/tech/hsdl/lib/python/hsdl/vim/grid.py", tempfname], start_path="/tech/hsdl/lib/python/hsdl/vim/", sep_console=False, is_win32=is_win32)


def full_parse_sexp(block, col):
    reload(jcommon)

    s = (' '*col) + block   # let's preserve the indentation

    #lines = jcommon.ignore_special_lines( string.split(s, '\n') )
    lines = string.split(s, '\n')
    orig_num_lines = len(lines)
    lines = jcommon.clean_repeat_lines(lines)
    s = string.join(lines, '\n')
    s = jcommon.clean_future_refs(s)

    s2, shift_dict = jcommon.rewrite_triple_quotes_shifting(s)

    shift_list = shift_dict.items()
    shift_list.sort()

    from hsdl.schemepy import skime

    parser = skime.compiler.parser.Parser(s2)
    a = parser.parse() #skime.compiler.parser.parse(s)

    line_ranges = jcommon.line_ranges_dict(s)                       # our view is still based on the old string; and because the shifting has already set the positions
                                                                    # from the persepctive of the old string; thus, we can calculate line nums and cols now
    sexp = lisp_to_python_main(parser, s, s2, a, shift_list, line_ranges)

    return sexp, s2


def find_out_sexp(vim, ancs):
    # -- go up ancestors to find one; may fail
    for _, main_block, col, main_start_row, col1, end_row, col2 in ancs:
        sexp, main_block2 = full_parse_sexp(main_block, col)

        for subsexp in sexp[1:]:
            this_start_row = main_start_row              # start with parent's start_row
            this_start_row += subsexp.line_num
            this_block = subsexp.obj
            if type(this_block) == types.ListType and this_block[0] == ('__OUT__',):
                output_line_start = main_start_row + subsexp.line_num        # start with parent's start_row
                output_col = subsexp.line_col
                num_lines = len( string.split( main_block2[subsexp.start : subsexp.end], '\n') )
                output_line_end = output_line_start + num_lines - 1
                return output_line_start, output_col, output_line_end

    return -1, -1, -1

def set_stage_search_page(vim, stage_level):
    path = [each for each in xrange(stage_level)]
    path.reverse()

    cmd = "(%s;'z';'base') 18!:2 <'stage%d'" % (string.join(["'stage%d'" % each for each in path], ';'),     stage_level)
    jcommon.callj(vim, cmd)

# returns int
def get_cocurrent_stage_level(code):
    # pat = re.compile(r"cocurrent\s*'(?P<cocurrent>[^']+)'")
    pat = re.compile(r"NB\.\s*stage\s*=\s*(?P<cocurrent>[0-9]+)")
    all = pat.findall(code)
    all.sort()
    if all:
        stage = all[-1]
        try:
            return int(stage)
        except:
            return None
    else:
        return None

# returns official name of the new stage
def prepare_next_j_stage(vim, code=''):
    curr = get_cocurrent_stage_level(code)
    if curr is None:
        # advance the global count
        curr = shared.J_STAGE
        shared.J_STAGE += 1
        next = shared.J_STAGE
    else:
        next = curr + 1
        if next > shared.J_STAGE:
            shared.J_STAGE = next

    set_stage_search_page(vim, next)
    return next

LANGS_EMBEDDABLE = [] # 'lfe', 'sisc', 'chicken', 'mzscheme', 'mz', 'clj']


def modify_code_for_selection(sell, ext):
    if ext == 'lfe':
        return '(begin '  + sell + ')'
    else:
        return sell

def execute_code_jtext(vim,
                       visualize=False,
                       force_new_window=False,
                       repeat_down=0,
                       repeat_set='',
                       dump_fname=None,
                       ext=None,
                       catch_exception=1,
                       lang='',
                       orig_mode='n',
                       use_selection=0,
                       execution_type=''):


        ancs = vim.find_ancestors()

        poss_ext, _, _, _, _ = jcommon.find_first_lang_spec(ancs)
        if poss_ext:
            ext = poss_ext

        r = find_out_region(vim, dir=1)
        if r != (-1, -1):
            ll, cc = vim.current.window.cursor
            orig_cursor = ll, cc

            output_line_start, output_col = r
            pos = vim.getOffsetAtLine(output_line_start) + output_col

            s = vim.getText()
            parens_r = jcommon.find_surrounding_matched_exp(s, pos, '()')
            if parens_r:
                pos_start, pos_end = parens_r
                region_parens = s[pos_start:pos_end]

                output_line_end = vim.getLineNum(pos_end-1)

                output_col_end = pos_end - vim.getOffsetAtLine(output_line_end)

                output_info = (output_line_start, output_col, output_line_end, output_col_end)

                block, start_row, end_row = vim.get_block(check_indent=False, use_line=1)
                lines = block.split('\n')

                line = vim.current.line
                curr_indent  = jcommon.get_indentation(line)

                if shared.ALWAYS_CHECK_PS:
                    from hsdl.vim import vim_commands_lfe
                    reload(vim_commands_lfe)
                    vim_commands_lfe.lfe_start()

                if ext=='bash':
                    return bash(vim, block, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)
                elif ext=='j':
                    immed_lines, func_dict = jcommon.separate_code_lines(None, lines)   # None means that we don't care about indentation
                    code_name = ''
                    if immed_lines:
                        code_name = extract_name(immed_lines)
                        new_window =   string.find(string.join(immed_lines,'\n'), '<<EXT>>')>=0 or force_new_window == True
                        immed_lines = j_rewrite_lines(immed_lines)
                        if visualize:
                            immed_lines = map(lambda x: string.strip(x),  immed_lines)
                            immed_lines = filter(lambda x: len(x) > 0, immed_lines)
                            immed_lines[-1] = 'VISUALIZE ' + immed_lines[-1]
                            full = string.join(immed_lines, '\n')
                            visualize_data_using_wx(vim, full)

                        else:
                            return vimcallj_basic(vim, immed_lines, start_row, end_row, full_text = block, new_window=new_window,
                                                  dump_fname=dump_fname, code_name=code_name, ext=ext, output_info=output_info, orig_cursor=orig_cursor, lang=lang, orig_mode=orig_mode)
                elif ext=='rkt':
                    return rkt(vim, block, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, catch_exception=catch_exception, orig_mode=orig_mode)

                elif ext in ['lfe', 'erl']:
                    if shared.ALWAYS_CHECK_PS:
                        from hsdl.vim import vim_commands_lfe
                        reload(vim_commands_lfe)
                        vim_commands_lfe.lfe_start()
                    return erl_lfe(vim, block, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, ext=ext, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

        # if we get here, that means somehow it didn't work out
        from hsdl.embedit.components import embcomp_code
        from hsdl.embedit.embcomp_editors import EmbComp_Editor_output
        ed = vim.ed

        if isinstance(ed, embcomp_code.EmbComp_Editor_code):

            if execution_type == 'after':
                    block, start_row, end_row = vim.get_block(check_indent=False, use_line=1)
                    lines = block.split('\n')

                    def outputter_fun(lines):
                        line = vim.current.buffer[end_row]
                        the_pos = vim.getOffsetAtLine(end_row+1)+ len(line)
                        new_s = '\n' + string.join(lines, '\n') + '\n\n'

                        from hsdl.embedit import style
                        reload(style)
                        ed.insertString(new_s,  the_pos, style.executeOutputTextAttrSet)

                        ed.setCaretPosition(the_pos + len(new_s))

                    ed_lang = ed.__class__.__name__.replace('EmbComp_Editor_', '')
                    line = vim.current.line
                    curr_indent  = jcommon.get_indentation(line)

                    if ed_lang == 'pyeval':
                        ed.addToInputHistory(block)
                        print "*"*100
                        print block
                        print "*"*100
                        return pyeval(vim, block, lines, -1, -1, curr_indent, new_window=0, dump_fname='',
                                      output_info=(), orig_cursor=(), orig_mode=orig_mode,
                                      outputter_fun = outputter_fun)

                    elif ed_lang == 'j':
                        ed.addToInputHistory(block)
                        immed_lines, func_dict = jcommon.separate_code_lines(None, lines)   # None means that we don't care about indentation
                        if immed_lines:
                            immed_lines = j_rewrite_lines(immed_lines)
                            if visualize:
                                immed_lines = map(lambda x: string.strip(x),  immed_lines)
                                immed_lines = filter(lambda x: len(x) > 0, immed_lines)
                                immed_lines[-1] = 'VISUALIZE ' + immed_lines[-1]
                                full = string.join(immed_lines, '\n')
                                visualize_data_using_wx(vim, full)
                            else:
                                return vimcallj_basic(vim, immed_lines, -1, -1, full_text = block, new_window=0,
                                                      dump_fname='', code_name='', ext='j', output_info=(), orig_cursor=(), lang='j', orig_mode='n',
                                                      outputter_fun = outputter_fun)


            else:
                    parEd = ed.getParentEditor()
                    my_pos = ed.getMyPosInParent()
                    size = parEd.getTextSize()
                    comps_after_me =  parEd.getComponentsWithinPosRange(my_pos+1, size)

                    output_comps_after_me = filter(lambda(_ed_pos, the_ed): isinstance(the_ed, EmbComp_Editor_output),  comps_after_me)

                    if not output_comps_after_me:
                        from hsdl.embedit import class_registry
                        klass = class_registry.get_class_by_short_name('EmbComp_Editor_output')
                        if klass:
                            new_ed = class_registry.instantiate_class(klass)
                            from hsdl.vim import vim_emulator_jtext
                            temp_vim = vim_emulator_jtext.VimEmulatorJText(parEd, parEd.getDocument(), '/tmp')   # created just to use .getLineNum()
                            line_num = temp_vim.getLineNum(my_pos)

                            if line_num != -1:
                                end_pos = parEd.getEndOffsetAtLine(line_num)
                                parEd.insertString('\n', end_pos)
                                parEd.setCaretPosition(end_pos)
                                parEd.insertComponentKeepVisible(new_ed, grab_focus=0)

                                output_comps_after_me = [(my_pos+2, new_ed)]   # this is fake, but causes the logic below to work

                                if 0:       # TODO: why does calling getComponentsWIthinPosRange() file to see the newly added component; somehow, its position is marked as 0
                                    old_size = size
                                    size = parEd.getTextSize()
                                    new_my_pos = ed.getMyPosInParent()
                                    output_comps_after_me =  parEd.getComponentsWithinPosRange(my_pos+1, size)
                                    print ":::::::", my_pos, new_my_pos, old_size, size
                                    print ">>>>>>>>>", output_comps_after_me


                    if output_comps_after_me:
                        # find first _output
                        ed_found = None
                        for ed_pos, the_ed in output_comps_after_me:
                            if isinstance(the_ed, EmbComp_Editor_output):
                                ed_found = the_ed
                                break


                        if ed_found:
                                block, start_row, end_row = vim.get_block(check_indent=False, use_line=1)
                                lines = block.split('\n')

                                line = vim.current.line
                                curr_indent  = jcommon.get_indentation(line)

                                if shared.ALWAYS_CHECK_PS:
                                    from hsdl.vim import vim_commands_lfe
                                    reload(vim_commands_lfe)
                                    vim_commands_lfe.lfe_start()

                                ed_lang = ed.__class__.__name__.replace('EmbComp_Editor_', '')

                                def outputter_fun(lines):
                                    hor_bar, ver_bar = ed.findScrollBars()
                                    if hor_bar and ver_bar:
                                        hor_val = hor_bar.getValue()
                                        ver_val = ver_bar.getValue()

                                    s = string.join(lines, '\n')
                                    ed_found.setText(s)

                                    if hor_bar and ver_bar:
                                        from hsdl.embedit import embcomp_editors
                                        thread.start_new_thread(embcomp_editors.adjustScrollBars, (ed, hor_bar, ver_bar, hor_val, ver_val))


                                if ed_lang == 'bash':
                                    return bash(vim, block, lines, -1, -1, curr_indent, new_window=0, dump_fname='', output_info=(), orig_cursor=(), orig_mode='n',
                                                outputter_fun = outputter_fun)

                                elif ed_lang == 'j':
                                    immed_lines, func_dict = jcommon.separate_code_lines(None, lines)   # None means that we don't care about indentation
                                    if immed_lines:
                                        immed_lines = j_rewrite_lines(immed_lines)
                                        if visualize:
                                            immed_lines = map(lambda x: string.strip(x),  immed_lines)
                                            immed_lines = filter(lambda x: len(x) > 0, immed_lines)
                                            immed_lines[-1] = 'VISUALIZE ' + immed_lines[-1]
                                            full = string.join(immed_lines, '\n')
                                            visualize_data_using_wx(vim, full)
                                        else:
                                            return vimcallj_basic(vim, immed_lines, -1, -1, full_text = block, new_window=0,
                                                                  dump_fname='', code_name='', ext='j', output_info=(), orig_cursor=(), lang='j', orig_mode='n',
                                                                  outputter_fun = outputter_fun)

                                elif ed_lang == 'rkt':
                                    return rkt(vim, block, lines, -1, -1, curr_indent, new_window=0, dump_fname='',
                                               output_info=(), orig_cursor=(), catch_exception=catch_exception, orig_mode=orig_mode,
                                               outputter_fun = outputter_fun)

                                elif ed_lang in ['lfe', 'erl']:
                                    return erl_lfe(vim, block, lines, -1, -1, curr_indent, new_window=0, dump_fname='', ext=ext,
                                                   output_info=(), orig_cursor=(), orig_mode=orig_mode,
                                                   outputter_fun = outputter_fun)

                                elif ed_lang == 'pyeval':
                                    return pyeval(vim, block, lines, -1, -1, curr_indent, new_window=0, dump_fname='',
                                                  output_info=(), orig_cursor=(), orig_mode=orig_mode,
                                                  outputter_fun = outputter_fun)




def vimcallj(vim, visualize=False,
                  force_new_window=False,
                  repeat_down=0,
                  repeat_set='',
                  dump_fname=None,
                  ext=None,
                  catch_exception=1,
                  lang='',
                  orig_mode='n',
                  use_selection=0,
                  execution_type=''):

    reload(jcommon)

    from hsdl.vim import vim_emulator_jtext

    if use_selection:
        _, _, _, _, sell = vim.get_selection()

    if not ext:
        ext = vim.get_current_language(ext)

    line_num = int(vim.eval('line(".")'))

    # ==================================================================================
    #           simplified for jtext
    # ==================================================================================

    if isinstance(vim, vim_emulator_jtext.VimEmulatorJText):
        return execute_code_jtext(vim, visualize=visualize,
                                       force_new_window=force_new_window,
                                       repeat_down=repeat_down,
                                       repeat_set=repeat_set,
                                       dump_fname=dump_fname,
                                       ext=ext,
                                       catch_exception=catch_exception,
                                       lang=lang,
                                       orig_mode=orig_mode,
                                       use_selection=use_selection,
                                       execution_type=execution_type)


    # ==================================================================================
    # ==================================================================================


    line = vim.current.line
    bname = vim.current.buffer.name
    if bname:
        _, b_ext = os.path.splitext(bname)
    else:
        b_ext = ''

    if vim.eval("has('readonly')") == '1':
        force_new_window = True



    # -- if we are doing it by block, we at to FIRST position the cursor above the '(::', so that it can extract
    # -- necessary structures, like (__OUT__ ); later, we move the cursor back
    #by_block = string.find(line, '(=== ')<0
    by_block = 1

    if b_ext in ['.lisp']:
        old_line, old_col = vim.current.window.cursor
        block, start_row, end_row = vim.get_block(check_indent=False)
    elif by_block:
        old_line, old_col = vim.current.window.cursor
        find_typing_region(vim, -1)

    curr_indent  = jcommon.get_indentation(line)

    repeatable = 0
    if string.find(line, '<<REPEAT')>=0:
        repeatable = 1
        if not force_new_window:
            vim.clear_children()


    #orig_cursor = vim.current.window.cursor

    ancs = vim.find_ancestors()

    poss_ext, _, _, _, _ = jcommon.find_first_lang_spec(ancs)
    if poss_ext:
        ext = poss_ext

    if b_ext[1:] == ext:    # ignore the beginning dot
        force_new_window = 1

    output_line_start = -1
    output_line_end = -1
    output_col = -1

    _, block, col, start_row, col1, end_row, col2 = ancs[0]     # default

    if b_ext in ['.lisp']:
        pass
    elif ext in LANGS_EMBEDDABLE:
        _, block, col, start_row, col1, end_row, col2 = ancs[0]
        sexp, _ = full_parse_sexp(block, col)

        start_row = start_row + sexp.line_num
        end_row = start_row + len(string.split(block, '\n')) - 1
        start_row -= 1
    else:
        block = None

        cursor_row, _ = vim.current.window.cursor
        _, main_block, col, main_start_row, col1, end_row, col2 = ancs[0]
        sexp, main_block2 = full_parse_sexp(main_block, col)

        for subsexp in sexp[1:]:
            #print subsexp.line_num
            this_start_row = main_start_row              # start with parent's start_row
            this_start_row += subsexp.line_num
            this_block = subsexp.obj

            if type(this_block) == types.StringType:
                this_end_row = this_start_row + len(string.split(this_block, '\n')) - 1
                if cursor_row >= this_start_row  and cursor_row <= this_end_row:
                    start_row = this_start_row
                    end_row = this_end_row
                    block = this_block

            else:
                if type(this_block) == types.ListType and this_block[0] == ('__OUT__',):
                    output_line_start = main_start_row + subsexp.line_num        # start with parent's start_row
                    output_col = subsexp.line_col
                    num_lines = len( string.split( main_block2[subsexp.start : subsexp.end], '\n') )
                    output_line_end = output_line_start + num_lines - 1


        if output_line_start == -1:
            if len(ancs)>1:
                output_line_start, output_col, output_line_end = find_out_sexp(vim, ancs[1:])

    if b_ext in ['.lisp']:
        pass
    elif by_block:
        orig_cursor = old_line, old_col
        vim.current.window.cursor = orig_cursor
        block, _, _ = vim.get_block(check_indent=False)


    if block is None:
        return

    output_info = ()

    if output_line_start != -1:
        vim.current.window.cursor = (output_line_start, output_col)
        vim.command("normal %")
        output_line_end, output_col_end = vim.current.window.cursor
        vim.command("normal %")
        output_info = (output_line_start, output_col, output_line_end, output_col_end)



    if len(ancs) == 1:
        pass

    s = block

    if use_selection:
        s = modify_code_for_selection(sell, ext)

    lines = string.split(s, '\n')

    if 0:
        print ext, "+"*70
        for line in lines:
            print line
        print "+"*70
        print start_row, end_row
        print "+"*70



    #jcommon.debug_log('================\n' + repr([s, lines]) + '\n=====================')

    if ext in ['erl', 'lfe']:
        if shared.ALWAYS_CHECK_PS:
            from hsdl.vim import vim_commands_lfe
            reload(vim_commands_lfe)
            vim_commands_lfe.lfe_start()
        return erl_lfe(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, ext=ext, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext=='clp':
        return clp(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    #elif ext=='scala':
    #    return scala(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext=='chicken':
        return chicken(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext=='sisc':
        return sisc(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, catch_exception=catch_exception, orig_mode=orig_mode)

    elif ext=='rkt':
        return rkt(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, catch_exception=catch_exception, orig_mode=orig_mode)

    elif ext=='mzscheme':
        return mzscheme(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext in ['lisp', 'ecl']:
        return lisp(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext=='python':
        return python(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext=='bash':
        return bash(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext=='factor':
        return handle_factor(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext=='clj':
        return handle_clojure(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext=='hs':
        return handle_haskell(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    elif ext=='scala':
        return handle_scala(vim, s, lines, start_row, end_row, curr_indent, new_window=force_new_window, dump_fname=dump_fname, output_info=output_info, orig_cursor=orig_cursor, orig_mode=orig_mode)

    # --- at this point, we're dealing with j
    set_exec_lang_ext('ijs')

    immed_lines, func_dict = jcommon.separate_code_lines(None, lines)   # None means that we don't care about indentation

    code_name = ''


    if immed_lines:
        code_name = extract_name(immed_lines)

        new_window =   string.find(string.join(immed_lines,'\n'), '<<EXT>>')>=0 or force_new_window == True

        immed_lines = j_rewrite_lines(immed_lines)
        if visualize:
            immed_lines = map(lambda x: string.strip(x),  immed_lines)
            immed_lines = filter(lambda x: len(x) > 0, immed_lines)
            immed_lines[-1] = 'VISUALIZE ' + immed_lines[-1]

            full = string.join(immed_lines, '\n')
            visualize_data_using_wx(vim, full)

        else:
            vim.current.window.cursor = orig_cursor
            if repeatable:
                vimcallj_basic(vim, immed_lines, start_row, end_row, full_text = s, new_window=new_window,
                               repeatable=1, dump_fname=dump_fname, code_name=code_name, ext=ext, output_info=output_info, lang=lang, orig_mode=orig_mode)
            else:
                vimcallj_basic(vim, immed_lines, start_row, end_row, full_text = s, new_window=new_window,
                               dump_fname=dump_fname, code_name=code_name, ext=ext, output_info=output_info, lang=lang, orig_mode=orig_mode)

    if orig_cursor:
        if orig_mode == 'i':
            #vim.enter_insert_mode()
            try:
                the_line, the_col = orig_cursor
                vim.current.window.cursor = (the_line, the_col+1)

                old_row, old_col = orig_cursor
                vim.current.window.cursor = (old_row+1, old_col)
                num_spaces = jcommon.get_num_leading_spaces(s)

                stage_level = prepare_next_j_stage(vim, string.join(lines, '\n'))
                vim.insert_lines(['', (' '*num_spaces) + "cocurrent 'stage', STR stage [ link_stages stage [ stage=: %d  NB.stage=%d %s" % (stage_level, stage_level, '='*100), ' '*num_spaces + ' '])

                vim.current.window.cursor = (old_row+3, num_spaces)
                vim.center_current_line()
                vim.enter_insert_mode()
            except:
                buff = cStringIO.StringIO()
                traceback.print_exc(file=buff)
                print "*"*80
                print buff.getvalue()
                print "*"*80
        else:
            vim.current.window.cursor = orig_cursor
    else:
        if repeatable and not force_new_window:
            print "BBBB", line_num
            vim.current.window.cursor = (line_num, 0)


# inserts code that saves an expression value to a file (yet still returns the value); this is added to the last line of code
def add_j_instrumentation(s):
    final = []
    lines = string.split(s, '\n')
    i = len(lines) - 1
    first = 1
    while i>=0:
        line = lines[i]
        if string.strip(line):
            if first:
                final.append("( ] [ (writeall&'/tmp/TEMP_j_instrumentation' @: enc) )  " + line)
            else:
                final.append(line)
            first = 0
        else:
            final.append(line)

        i -= 1

    final.reverse()
    return string.join(final, '\n')



def vimcallj_basic(vim, lines,
                        start_row,
                        end_row,
                        full_text = '',
                        new_window=False,
                        repeatable=0,
                        dump_fname=None,
                        code_name='',
                        ext=None,
                        output_info=(),
                        lang='',
                        orig_mode='n',
                        orig_cursor=(),
                        outputter_fun=None):
    from hsdl.j import vim_utils

    if not lines: return

    if not ext:
        ext = vim.get_current_language(ext)

    full = string.join(lines, '\n')

    last_line = lines[-1]

    silent_pat = re.compile('^\s*SILENT\s+')
    be_silent = 0
    if silent_pat.match(last_line):
        be_silent = 1

    indent = jcommon.get_indentation(last_line)

    if lang:
        full = add_j_instrumentation(full)


    VARS_TO_BE_SET = []     # list of (varname, buff_obj)


    # NOTE: this is a different "shared" module than the one imported above

    #from hsdl.j import shared as shared_j
    #shared_j.VIM = vim

    # -------------- extra vim variables --------------------------------------------------------
    jcommon.prepare_j_for_vim(vim)

    if 0:
        if string.find(full, 'vimotext')>=0:
            companion_lines = vim_utils.get_companion_buffer_lines(vim)
            if companion_lines:
                companion_text = string.join(companion_lines, jcommon.LINE_DELIMITER)
                jcommon.sendjdata(vim, companion_text, tempvar='vimotext')

        if string.find(full, 'vimopath')>=0:
            other_path = vim_utils.get_companion_buffer_path(vim)
            if not other_path is None:
                jcommon.sendjdata(vim, other_path, tempvar='vimopath')

    # -----

    assigned_buffer_vars = {}   # path_spec -> hash ; keep track of variables used to hold buffer strings or lists

    # path_spec can be one path, '' to signify the other buffer in the window (like a split or vsplit), or wildcarded
    vim_buff_pat = re.compile(r"([^a-zA-Z0-9_]|^)vimbuffer\s*'(?P<path_spec>[^']*)'", re.DOTALL)

    def sub_buffer_refs(matchobj):
        path_spec = string.strip(matchobj.group('path_spec'))
        o = hashlib.sha1()
        o.update(path_spec)
        hx = o.hexdigest()
        varname = 'VIMTEXT' + hx
        if not path_spec in assigned_buffer_vars:
            assigned_buffer_vars[path_spec] = varname
        return varname


    r = vim_buff_pat.search(full)
    if r:
        path_spec = r.group('path_spec')
        full = vim_buff_pat.sub(sub_buffer_refs, full)

        for path_spec, varname in assigned_buffer_vars.items():
            buff_obj = vim_utils.get_buffers_by_spec(vim, path_spec, as_string=1)
            if not buff_obj:
                print "No buffer matches spec:", path_spec
                raise "No buffer matches spec:", path_spec

            if len(buff_obj)==1 and string.find(path_spec, '*')<0:    # user's intention was to select one (if it exists), not a list of them
                buff_obj = buff_obj[0][1]      # convert from list of one to scalar, and just the buffer

            VARS_TO_BE_SET.append((varname, buff_obj))

        # if we get here, that means there were no exceptions. start setting variables
        for varname, buff_obj in VARS_TO_BE_SET:
            jcommon.sendjdata(vim, buff_obj, tempvar=varname)

    # -------------------------------------------------------------------------------------------

    try:
            replacing = string.find(full, 'NB.!!')>=0 or string.find(full, 'NB. !!')>=0
            if replacing:
                if not new_window:
                    vim.clear_children(extra=1)        # clear the next line, which is blank

                result = jcommon.callj_value(vim, full)
                if type(result) == types.ListType:
                    final = []
                    for each in result:
                        if type(each) == types.StringType(each):
                            final.append(each)
                        else:
                            final.append(str(each))
                    result = string.join(final, '\n')
                else:
                    result = str(result)
            else:
                result = jcommon.callj(vim, full)
    finally:
        # unset variables
        for varname, _ in VARS_TO_BE_SET:
            print "Unsetting:", varname
            jcommon.callj(vim, "erase '%s'" % varname)


    if result == []:        # this is how j returns an empty string
        result = ''

    result = string.replace(result, '\r\n', '\n')

    buffer = vim.current.buffer

    if string.find(result, '\n')>=0:
        parts = string.split(result, '\n')
        thelist = parts
    else:
        thelist = [result]

    thelist = jcommon.tag_data_lines(thelist)

    if not replacing:
        thelist += ['']

    if new_window:
        # only need 1 indentation, in case the output is formatted text (Control-D only acts on indented text)
        thelist = jcommon.indent_lines(thelist, 1)
    else:
        thelist = jcommon.indent_lines(thelist, indent+1)
        #thelist.append('        ')
        thelist.append(jcommon.BASE_INDENT_SPACES * indent)


    if outputter_fun:
        outputter_fun(thelist)
        return

    if repeatable:                   # this removes extra lines at the bottom so that the result does not push lines below it down
        thelist = thelist[:-2]

    if dump_fname:
        dump_to_output(dump_fname, code_name, thelist)

    if not result: return           # Why bail out here instead of earlier? I wanted to give dump_to_output() a chance to run
                                    # This is important when vim is automated. Some commands produce no result, but the
                                    # empty result needs to be dumped anyway.

    if new_window:
        old_lines = string.split(full_text, '\n')
        new_lines = thelist
        update_output(vim, output_info, start_row, end_row, old_lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=indent)        # *************
    else:
        old_lines = string.split(full_text, '\n')
        new_lines = thelist
        update_output(vim, output_info, start_row, end_row, old_lines, new_lines, new_window=new_window, orig_cursor=orig_cursor, orig_mode=orig_mode, output_indent=indent)        # *************


def insert_text(vim, start, end, s):
    buffer = vim.current.buffer

    if string.find(s, '\n')>=0:
        buffer[start:end] = string.split(s, '\n')
    else:
        buffer[start:end] = [s]



# if reference, returns (whole_url, protocol, path)
# otherwise, ()
def get_references(vim):
    line = vim.current.line
    return jcommon.extract_references(line)


# order of preference: .gpg .gz
def check_other_extensions(path):
    if os.path.exists(path + '.gpg'):
        return path + '.gpg'
    elif os.path.exists(path + '.gz'):
        return path + '.gz'
    else:
        return path

# escape ampersands
def win32_clean_url(url):
    url = string.replace(url, '&', '^&')
    return url


def open_j_file(vim, r, start_path):
    path = r.group('path')
    _, base_fname = os.path.split(path)
    _, ext = os.path.splitext(base_fname)
    if ext == '':
        path = path + '.ijs'
    full_path = os.path.join(start_path,  path)
    if os.path.exists(full_path):
        r = vim.go_to_opened_buffer(full_path)      # if there is one opened
        if not r:
            vim.command(":silent tabnew " + full_path)
            vim.command(":silent set nofoldenable")
        return 1
    return 0


def check_j_references(vim, line):
    pat = re.compile(r"(^|[^a-zA-Z_])ws\s*'(?P<path>[^']+)'")                           # ws '----'
    r = pat.search(line)
    if r:
        if open_j_file(vim, r, general.interpolate_filename('${llib}/j/hsdl/ws')):
            return 1

    pat = re.compile(r"(^|[^a-zA-Z_])hsdl\s*'(?P<path>[^']+)'")                         # hsdl '----'
    r = pat.search(line)
    if r:
        if open_j_file(vim, r, general.interpolate_filename('${llib}/j/hsdl')):
            return 1

    pat = re.compile(r"(^|[^a-zA-Z_])load\s*'(?P<path>[^']+)'")                         # load '----'
    r = pat.search(line)
    if r:
        if open_j_file(vim, r, '/home/shared/apps/j602/system/main'):
            return 1

    pat = re.compile(r"(^|[^a-zA-Z_])require\s*'(?P<path>[^']+)'")                      # require '----'
    r = pat.search(line)
    if r:
        if open_j_file(vim, r, '/home/shared/apps/j602/system/main'):
            return 1



from hsdl.vim import mzscheme_common


def sisc_open(vim):
    from hsdl.vim import jcommon
    reload(jcommon)

    z = jcommon.get_sexp_special_marker(vim, '(:=load', dir=-1)
    if not z is None:
        sexp, _ = full_parse_sexp(z, 0)
        if sexp and sexp[0] == (':=load',):
            path = sexp[1].obj
            if path[:2] == '~/':
                path = os.path.join(general.interpolate_filename("${HOME}"), path)
            else:
                #path = os.path.join(general.interpolate_filename("${HSDL_LIB_HOME}/sisc/hsdl/"), path)
                path = os.path.join(general.interpolate_filename("${mind}/"), path)
            jcommon.jump_to_file_and_line_num(vim, path, 1)



def go_to_python(vim, mod_dotted, fun_name):
    from hsdl.common import mod_dynamic
    mod_slashed = mod_dotted.replace('.', '/')
    try:
        mod = mod_dynamic.import_path(mod_slashed)
        mod_path = mod.__file__
        mod_base, mod_ext = os.path.splitext(mod_path)
        if mod_ext == '.pyc':
            mod_path = mod_base + '.py'

        pat = re.compile('^\s*def\s+(?P<name>[^ (]+)')
        fin = open(mod_path, 'rb')
        i = 0
        found_line = -1
        while 1:
            i += 1
            line = fin.readline()
            if not line: break
            r = pat.match(line)
            if r and r.group('name') == fun_name:
                found_line = i
                break
        fin.close()

        if found_line != -1:
            jcommon.jump_to_file_and_line_num(vim, mod_path, found_line)
    except:
        pass

def lfe_open(vim):
    from hsdl.vim import jcommon
    reload(jcommon)

    z = jcommon.get_sexp_special_marker(vim, '(: pynerl ', dir=-1)
    if not z is None:
        sexp, _ = full_parse_sexp(z, 0)
        if sexp and sexp[0] == (':',):
            if sexp[2] == ('call',):
                if sexp[3][0] == ('quote',):
                    mod_dotted = sexp[3][1].obj
                    if sexp[4][0] == ('quote',):
                        fun_name = sexp[4][1].obj
                        go_to_python(vim, mod_dotted, fun_name)

def python_open(vim):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.vim import vim_commands
    reload(vim_commands)
    from hsdl.vim import vim_commands_python
    reload(vim_commands_python)

    line = vim.current.line

    # -----------------
    pat = re.compile(r"""ecl\.((apply_ecl)|(eval_ecl))\(['"](?P<name>[^'"]+)['"]""")
    r = pat.search(line)
    if r:
        name = r.group('name')
        fnames = ['/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp']
        fnames += glob.glob('/tech/hsdl/lib/ecl/hsdl/*.lisp')
        fnames += glob.glob('/tech/hsdl/lib/lisp/hsdl/*.lisp')

        for fname in fnames:
            line_num = vim_commands.ecl_find_definition_helper(fname, name)
            if not line_num is None:
                vim.command(":tabnew " + fname)
                vim.command(":set nofoldenable")
                vim.command("normal %dG" % line_num)

    # ----------------
    pat = re.compile(r"""franca_comm.send_action_franca\(\s*'(?P<lang>[^']+)'\s*,\s*\['(?P<name>[^']+)'""")
    r = pat.search(line)
    if r:
        lang = r.group('lang')
        if lang in ['py', 'python', 'jy', 'python']:
            func_name = r.group('name')
            fnames = glob.glob(general.interpolate_filename("${serv}/py/*.py"))
            for fname in fnames:
                line_num = vim_commands_python.python_find_definition_helper(fname, func_name)
                if not line_num is None:
                    if os.path.exists(fname):
                        r2 = vim.go_to_opened_buffer(fname)      # if there is one opened
                        if not r2:
                            vim.command(":tabnew " + fname)
                            vim.command(":set nofoldenable")
                            vim.current.window.cursor = (line_num, 0)

        elif lang in ['erl', 'erlang']:
            #  franca_comm.send_action_franca('erl', ['servers.eval:lfe_cmd', s], port=15020, machine='worlddb', timeout_on=1)
            func_spec = r.group('name')
            fname, func_name = string.split(func_spec, ':')
            func_name = string.strip(func_name)
            fname = string.strip(fname)
            base_fname = string.replace(fname, '.', '/')
            full_path = general.interpolate_filename("${serv}/erl/") + base_fname
            if os.path.exists(full_path + '.erl'):
                from hsdl.eclipse import ViPluginCommandsC
                reload(ViPluginCommandsC)
                all = ViPluginCommandsC.helper_find_erl_definition_file(full_path + '.erl', func_name)
                for fname, line_num, name, kind, extra  in all:
                    if name == func_name:
                        full_path = full_path + '.erl'
                        if os.path.exists(full_path):
                            r2 = vim.go_to_opened_buffer(full_path)      # if there is one opened
                            if not r2:
                                vim.command(":tabnew " + full_path)
                                vim.command(":set nofoldenable")
                                vim.current.window.cursor = (line_num, 0)

        elif lang in ['lfe']:
            func_spec = r.group('name')
            fname, func_name = string.split(func_spec, ':')
            func_name = string.strip(func_name)
            fname = string.strip(fname)
            base_fname = string.replace(fname, '.', '/')
            full_path = general.interpolate_filename("${serv}/erl/") + base_fname
            if os.path.exists(full_path + '.lfe'):
                from hsdl.eclipse import ViPluginCommandsC
                reload(ViPluginCommandsC)
                all = ViPluginCommandsC.helper_find_lfe_definition_file(full_path + '.lfe', func_name)
                for   fname, line_num, name, arity, kind, extra, comment   in all:
                    if name == func_name:
                        full_path = full_path + '.lfe'
                        if os.path.exists(full_path):
                            r2 = vim.go_to_opened_buffer(full_path)      # if there is one opened
                            if not r2:
                                vim.command(":tabnew " + full_path)
                                vim.command(":set nofoldenable")
                                vim.current.window.cursor = (line_num, 0)


def lisp_open(vim):
    from hsdl.vim import jcommon
    reload(jcommon)
    from hsdl.vim import vim_commands
    reload(vim_commands)

    buffname = vim.current.buffer.name

    line = vim.current.line
    pat = re.compile(r"""\(mind-load\s+['"](?P<name>[^'"]+)['"]\s*\)""")
    r = pat.search(line)
    if r:
        if buffname:
            support_name = r.group('name')
            full_path = jcommon.get_support_source(buffname, support_name)

            if os.path.exists(full_path):
                r2 = vim.go_to_opened_buffer(full_path)      # if there is one opened
                if not r2:
                    vim.command(":tabnew " + full_path)
                    vim.command(":set nofoldenable")

    else:
        line = vim.current.line
        col = int(vim.eval('col(".")'))-1
        word = jcommon.find_word(line, col)
        word = string.replace(word, '(', '')
        word = string.replace(word, ')', '')
        word = string.strip(word)
        if not word:
            return

        dirname, _ = os.path.split(buffname)

        fnames = []
        fnames += glob.glob(dirname + '/*.lisp')
        fnames += glob.glob(dirname + '/*.mind')
        fnames += ['/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp']
        fnames += glob.glob('/tech/hsdl/lib/ecl/hsdl/*.lisp')
        fnames += glob.glob('/tech/hsdl/lib/lisp/hsdl/*.lisp')

        for fname in fnames:
            line_num = vim_commands.ecl_find_definition_helper(fname, word)
            if not line_num is None:
                #raise Exception(repr((fname, word, line_num)))

                if os.path.exists(fname):
                    r2 = vim.go_to_opened_buffer(fname)      # if there is one opened
                    if not r2:
                        vim.command(":tabnew " + fname)
                        vim.command(":set nofoldenable")
                    vim.command("normal %dG" % line_num)
                    break

def generic_open_paste(vim, do_load = 0):

    def action_fun(path, do_load = do_load):
        if do_load:
            s = ':load ' + path
        else:
            fin = open(path, 'rb')
            s = fin.read()
            fin.close()
            reload(jcommon)


        jcommon.paste_to_screen_terminal('no-project/' + path, s)

    generic_open(vim, action_fun = action_fun)


def register_open_handler(fun):
    if not fun in shared.open_handlers:
        shared.open_handlers.append(fun)

def clear_open_handlers():
    shared.open_handlers = []

def check_open_handlers(vim, line):
    for handler in shared.open_handlers:
        t = handler(vim, line)
        if t:
            path, goto_line = t
            path = jcommon.clean_path_for_vim(path)

            jcommon.jump_to_file_and_line_num(vim, path, goto_line)

            return 1

    return 0



def generic_open(vim, action_fun = None):
    name = vim.current.buffer.name
    if name:
        dirname = os.path.split(name)[0]
    else:
        dirname = '/tmp'


    if dirname == '/tmp':
        dirname = general.dgetenv("mind", "/tmp")

    line = string.strip(vim.current.line)

    # any registered open handler has priority
    opened = check_open_handlers(vim, line)
    if opened:
        return

    refs = get_references(vim)
    if refs:
        if line and line[0] == '`' and len(refs)>1:     # this line is multi-columned, likely we can just the last reference
            ref = refs[-1]
        else:
            ref = refs[-1]       # we only act on the last reference

        url, protocol, path = ref
        is_win32 = vim.eval('has("win32")') == '1'

        if protocol == 'file':
            goto_line = None
            goto_mark = ""

            replace_curr_buff = string.find(path, '<replace>')>=0
            if replace_curr_buff:
                path = string.replace(path, '<replace>', '')        # remove the marker so that we can extract possible line number

            p = string.find(path, '#')
            if string.find(path, '##')>=0:
                try:
                    goto_mark = string.strip(path[p+2:])
                except: pass
                path = path[:p]

            elif string.find(path, '#')>=0:
                try:
                    goto_line = int(string.strip(path[p+1:]))
                except: pass
                path = path[:p]


            path = jcommon.adapt_path(path, is_win32=is_win32)

            path = os.path.join(dirname, path)      # allow relative path

            base, ext = os.path.splitext(path)
            if (ext in ['.xls', '.doc', '.pdf', '.odt', '.mp3', '.wmv', '.mov', '.gif', '.jpg', '.png', '.csv', '.rtf', '.html', '.htm']) and is_win32:
                if is_win32:
                    jcommon.execDosScript("start %s" % path, start_path="h:/frontier/notes", title='mrxvt_bat')
                else:
                    pass    # launch app in linux based on extension
            elif ext in ['.pdf']:
                print path
                jcommon.launchProcess("evince", "evince", [path], start_path="/tech/hsdl/lib/python/hsdl/vim/", sep_console=False, is_win32=is_win32)
            else:
                path = check_other_extensions(path)

                if action_fun:
                    action_fun(path)
                else:
                    path = jcommon.clean_path_for_vim(path)

                    jcommon.jump_to_file_and_line_num(vim, path, goto_line)

                    if goto_mark:
                        line_num, col_num = vim.find_mark_in_buffer(goto_mark)
                        if line_num >= 0:
                            vim.current.window.cursor = (line_num+1, col_num)
                        else:
                            print "Unable to find mark:", goto_mark


        elif (protocol in ['http', 'https', 'ftp']):
            url = win32_clean_url(url)
            if is_win32:
                jcommon.execDosScript("start %s" % url, start_path="h:/frontier/notes", title='mrxvt_bat')
            else:
                jcommon.launchProcess("firefox", "firefox", [url], start_path="/tech/hsdl/lib/python/hsdl/vim/", sep_console=False, is_win32=is_win32)


        else:
            vim.command(":silent tabnew " + url)
            vim.command(":silent set nofoldenable")
    else:
        if shared.SEXP_PATTERN_ON and name and string.find(name, '__patterns')>=0:
            the_line, _ = vim.current.window.cursor
            for i in xrange(len(shared.SEXP_PATTERNS)):
                each = shared.SEXP_PATTERNS[i]
                choose_line_start, choose_line_end, the_path, start_row, start_col, end_row, end_col, to_insert, orig_cleaned = each
                if the_line >= choose_line_start  and the_line <= choose_line_end:
                    shared.SEXP_PATTERN_INDEX = i
                    insert_pattern_match(vim)
                    shared.SEXP_PATTERN_MODIFIED = 1

        else:
                path = vim.current.buffer.name
                if not path:
                    return

                path = os.path.join(dirname, path)      # allow relative path
                base, ext = os.path.splitext(path)

                if ext in ['.mind']:
                        reload(jcommon)
                        ancs = vim.find_ancestors()
                        lang, start, end, _, _  = jcommon.find_first_lang_spec(ancs)

                        if lang == 'j':
                            r = check_j_references(vim, line)
                            if not r:
                                import vim_commands
                                reload(vim_commands)
                                import vim_commands_python
                                reload(vim_commands_python)
                                try:
                                    vim_commands.hier_goto_helper(vim, suppress_message=True)
                                except Exception:
                                    vim_commands_python.python_goto_helper(vim)

                        elif lang == 'sisc':
                            return sisc_open(vim)
                        elif lang in ['lisp', 'ecl', 'sbcl', 'abcl']:
                            return lisp_open(vim)
                        elif lang in ['py']:
                            return python_open(vim)
                        else:
                            from hsdl.eclipse import langs
                            reload(langs)
                            d = langs.__dict__
                            if d.has_key(lang + '__jumpto'):
                                fun = d[lang + '__jumpto']
                                line = vim.current.line
                                col = int(vim.eval('col(".")'))-1
                                word = jcommon.find_word(line, col)
                                word = string.replace(word, '(', '')
                                word = string.replace(word, ')', '')
                                return fun(vim, line, col, word)

                elif ext == '.lfe':
                    return lfe_open(vim)

                elif ext == '.py':
                    return python_open(vim)



def generic_exec(vim, new_window=0):
    name = vim.current.buffer.name
    if name:
        dirname = os.path.split(name)[0]
    else:
        dirname = '/tmp'


    if dirname == '/tmp':
        dirname = general.dgetenv("mind", "/tmp")

    line = string.strip(vim.current.line)

    pat = re.compile(r'\(==(?P<lang>[^=]+)==\s*\(===\s*"""(?P<code>.+?)"""\s*\)\s*\)')

    r = pat.search(line)
    if r:
        lang = r.group('lang')
        code = r.group('code')

        exec_code = ''

        if lang == 'bash':
            exec_code = code

        if new_window:
            jcommon.proc(code, detach=1)
        else:
            output_info = 1, 1, 1, 1
            curr_line = int(vim.eval('line(".")'))-1
            orig_cursor = vim.current.window.cursor
            bash(vim, code, [code], curr_line, curr_line, 0, new_window=1, dump_fname=None, output_info=output_info, orig_cursor=orig_cursor, orig_mode='n')


def generic_open_location(vim, new_window=0):
    name = vim.current.buffer.name
    if name:
        dirname = os.path.split(name)[0]
    else:
        dirname = '/tmp'


    if dirname == '/tmp':
        dirname = general.dgetenv("mind", "/tmp")

    line = string.strip(vim.current.line)

    pat = re.compile(r'\(==(?P<lang>[^=]+)==\s*\(===\s*"""(?P<code>.+?)"""\s*\)\s*\)')

    r = pat.search(line)
    if r:
        lang = r.group('lang')
        code = r.group('code')

        cd_pat = re.compile(r'cd\s+(?P<dir>[^ ;|>]+)')

        r2 = cd_pat.search(code)
        if r2:
            directory = r2.group('dir')

            exec_code = ''

            if lang == 'bash':
                exec_code = ''
                label = 'temp-' + str(uuid.uuid1())
                tempfname = '/tmp/' + label + '.sh'
                script_code = "cd %s; rm %s" % (directory, tempfname)   # goes to that dir then deletes the script
                fout = open(tempfname, 'wb')
                fout.write(script_code)
                fout.close()
                jcommon.proc("file-as-stdin bash " + tempfname, prompt=0, floater=0)    # uses "expect"



def display_storage_message(s):
    print "Stored in MAIN_S / MAIN: >> (%d lines): %s" % (len(string.split(s,'\n')), repr(s)[:40])


# splits set of lines into (j_code_lines, data_lines)
def partition_lines(lines):
    code_lines = []
    regular_lines = []

    for line in lines:
        if string.find(line, 'NB.--')>=0 or string.find(line, 'NB. --')>=0 or \
           string.find(line, 'NB.!!')>=0 or string.find(line, 'NB. !!')>=0:
            code_lines.append(line)
        else:
            regular_lines.append(line)

    return code_lines, regular_lines


def vimsendjdata(vim, silent=0):
    refs = get_references(vim)

    line = vim.current.line
    line2 = string.lstrip(vim.current.line)

    if refs and line2 and line2[0] != '`':
        ref = refs[0]       # we only care about the first one
        url, protocol, path = ref
        if protocol == 'file':
            is_win32 = vim.eval('has("win32")') == '1'
            path = jcommon.adapt_path(path, is_win32=is_win32)
            fin = open(path, 'rb')
            s = fin.read()
            fin.close()

            jcommon.sendjdata(vim, s)
            if not silent:
                display_storage_message(s)

    else:
        r = vim.current.range
        start = r.start
        end = r.end

        if start == end:
            # you want to
            #s, start_row, end_row = jcommon.get_all_same_indent(vim)
            s, start_row, end_row = vim.get_block(check_indent=True)
        else:
            # unprotect
            start_row, end_row, _, _, s = vim.get_selection()


        lines = string.split(s, '\n')

        # --- if meta info available, such as 'colexpr=', we will use it
        meta = get_meta_info(vim, start_row-1)

        j_code_lines, lines = partition_lines(lines)
        lines = unprotect(lines)
        s = string.join(lines, '\n')

        s = jcommon.rewrite_data(s)

        jcommon.sendjdata(vim, s)

        if not silent:
            display_storage_message(s)

        if 0: #meta:    # this means meta that's specified from the start of line, e.g. '::source='
            jcommon.callj(vim, """   MAIN=:  strip&.>    (' `` '&strsplit) gridstr strip MAIN_S  """)
        else:
            #jcommon.callj(vim, """   MAIN=:  3 }. strip&.>    (' `` '&strsplit) gridstr strip MAIN_S  """)       # this is data where the first 3 rows contain meta data for columns; drop for now
            if lines:
                did_main = 0

                if (string.find(lines[0], '::colexpr=')>=0) or (string.find(lines[0], '::colname=')>=0):      # if top has NB., treat header as list of conversion functions for the data
                    appended_exprs = {}  # index -> [lines]
                    colname = []

                    colexpr_pat = re.compile(r'``\s*::colexpr=')
                    colname_pat = re.compile(r'``\s*::colname=')

                    max = len(lines)
                    i = 0
                    while i<max:
                        the_line = lines[i]
                        header_line = jcommon.rewrite_data(lines[i])
                        r = colexpr_pat.search(header_line)
                        if r:
                            did_main = 1
                            header_line = colexpr_pat.sub('', header_line)
                            exprs = map(lambda x: string.strip(x),  string.split(string.strip(header_line), '``')  )
                            for j in xrange(len(exprs)):
                                if not appended_exprs.has_key(j):
                                    appended_exprs[j] = []
                                appended_exprs[j].append(exprs[j])

                        r = colname_pat.search(header_line)
                        if r:
                            did_main = 1
                            header_line = colname_pat.sub('', header_line)
                            colname = map(lambda x: string.strip(x),  string.split(string.strip(header_line), '``')  )


                        if string.find(the_line, '::colexpr=')<0 and string.find(the_line, '::colname=')<0:
                            break

                        i += 1

                    colexpr = []
                    keys = appended_exprs.keys()
                    keys.sort()
                    for key in keys:
                        colexpr.append(string.join(appended_exprs[key], '\n'))

                    meta['colexpr'] = colexpr
                    if colname:
                        meta['colname'] = colname

                    jcommon.callj(vim, """   MAIN=:  %d }. strip&.>    (' `` '&strsplit) gridstr strip MAIN_S  """ % i)       # this is data where the first 3 rows contain meta data for columns; drop for now

                if not did_main:    #  no colexpr
                    jcommon.callj(vim, """   MAIN=:  strip&.>    (' `` '&strsplit) gridstr strip MAIN_S  """)       # this is data where the first 3 rows contain meta data for columns; drop for now


        # apply colexpr code to data in each column
        if meta.has_key('colexpr'):
            colexpr = meta['colexpr']
            if colname:
                jcommon.sendjdata(vim, colname, tempvar='COLNAME')
            else:
                jcommon.sendjdata(vim, 0, tempvar='COLNAME')

            jcommon.sendjdata(vim, colexpr, tempvar='COLEXPR')

            CODE = """
                if. 0 < # COLEXPR do.
                    acc=. ''
                    for_x. i. # COLEXPR do.
                        fun=. 3 : (> x { COLEXPR )
                        col=. x {"1  MAIN
                        colresult=. fun&.> col
                        acc=. acc , <colresult
                    end.
                    if. 0 -: COLNAME do.
                        MAIN=: |: > acc
                    else.
                        MAIN=: COLNAME , (|: > acc)
                    end.
                end.
                'ok'
            """

            jcommon.callj(vim, CODE)

        #print "Stored in TEMP: >>" + repr(s[:50])

        if j_code_lines:
            if 1:
                code = string.join(j_code_lines, '\n')
                vimcallj_basic(vim, [code], start_row, end_row)
            else:     # ---- exec each line separately
                last_result = ''
                # for now, use only the first line
                for line in j_code_lines[:-1]:      # do not do the last one
                    last_result = jcommon.callj(vim, line)
                vimcallj_basic(vim, [j_code_lines[-1]], start_row, end_row)

def clean_folding(vim):
    buff = vim.current.buffer
    start_line = vim.eval('line(".")')

    start_line_num = int(vim.eval('line(".")'))-1       # line numbering starts at 1, but indexing starts at 0

    start_indent = jcommon.get_foldlevel(vim)
    if start_indent == 0: return

    # keep going back to last line having the same indentation
    i = start_line_num
    last_line_num = i
    while i>0:
        line = buff[i]
        indent = jcommon.get_indentation(line)
        if indent == start_indent:
            last_line_num = i
        elif indent < start_indent:
            break
        i-=1

    vim.command("normal " + str(last_line_num+1) + "G")

    last_line = start_line

    while 1:
        vim.command("normal zj")        # go to next
        the_line = vim.eval('line(".")')
        if the_line == last_line: break     # we've reached the end
        last_line = the_line

        indent = jcommon.get_foldlevel(vim)
        if indent <= start_indent:
            break
        vim.command("normal zc")

    vim.command("normal " + start_line + "G")




# we may want to indent, but indenting can delete tabs
# call this function to prefix '`' before each line in the selection
def protect_text(vim, start, end, lines):
    lines = map(lambda x: '`' + x, lines)
    vim.current.buffer[start-1:end] = lines

# remove the first '`'
def unprotect_text(vim, start, end, lines):
    lines = unprotect(lines)
    vim.current.buffer[start-1:end] = lines


protection_pat = re.compile(r'^(?P<spaces>\s*`)')

def starts_with_protection(s):
    return not protection_pat.match(s) is None

def handle_embedded_data(vim):
    r = vim.current.range
    start = r.start
    end = r.end

    if start == end:
        pass
    else:
        start, end, _, _, s = vim.get_selection()
        lines = vim.current.buffer[start-1:end]
        if lines:
            #if string.find(lines[0], '`')>=0:
            st = starts_with_protection(lines[0])
            print "STARTS:", st
            if starts_with_protection(lines[0]):
                unprotect_text(vim, start, end, lines)
            else:
                protect_text(vim, start, end, lines)


def zzz_helper_format_display(lines):
    if lines:
        temp = string.strip(lines[0])
        if not temp[0] == '`': return

        indent = jcommon.get_indentation(lines[0])
        all = []
        for line in lines:
            parts = string.split(string.strip(line)[1:], '``')
            parts = map(lambda part: string.strip(part), parts)
            all.append(parts)


        max_cols = max(map(lambda line: len(line), all))

        max_widths = {}

        for col in xrange(max_cols):
            max_widths[col] = 0

            for parts in all:
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
        for parts in all:
            sofar = []
            for col in xrange(len(parts)):
                if max_widths.has_key(col):     # this will only fail if it's among the trailing columns
                    pad = max_widths[col]
                    if 1: #col == 0:
                        sofar.append((parts[col] + (' '*pad))[:pad])        # left-justified
                    else:
                        sofar.append(('%0' + str(pad) + 's') % parts[col])  # right-justified

            final.append(string.join(sofar, ' `` '))

        final = map(lambda line: ('    '*indent) + '`' + line, final)

        final = jcommon.tag_data_lines(final)

        return final, all
    else:
        return [], []

# check only first line
def is_key_value_block(lines):
  if lines:
    first = lines[0]
    if first.find('|') <0 and first.find("=")>0:
      return True
  return False


def expand_key_value_block(lines, fun_analyze=None, fun_column_line=None, fun_each_line=None):
  if not lines:
    return []

  ind = jcommon.get_indentation(lines[0])

  full = []
  for line in lines:
    line = line.strip()
    if not line: continue

    d = {}
    last_key = ''
    line += ' @@@'    # an ending sentinel: will end up being ignored
    parts = line.split("=")
    for part in parts:
      sub = part.split()
      next_key = sub[-1]
      last_val = " ".join(sub[:-1])
      if last_key:
        d[last_key] = last_val
      last_key = next_key
    full.append(d)

    common_d = {}
    for d in full:
      common_d.update(d)


  if fun_analyze:
    preferred_order = fun_analyze(full, common_d)
  else:
    preferred_order = []

  final = []

  line = []

  # use alphabetical order
  if not preferred_order:
    preferred_order = sorted( common_d.keys() )

  for col in preferred_order:
    if col in common_d:
      line.append(col)


  if fun_column_line:
    fun_column_line(common_d, full, line)


  final.append(line)

  for d in full:
    line = []
    for col in preferred_order:
      if col in common_d:
        if col in d:
          line.append(d[col])
        else:
          line.append('')

    if fun_each_line:
      fun_each_line(common_d, full, line)

    final.append(line)

  indent = jcommon.BASE_INDENT_SPACES * ind
  fixed = []
  fixed.append( indent + "`==== " + " | ".join(final[0]) )
  for each in final[1:]:
    fixed.append( indent +  "`" + " | ".join(each) )

  return fixed



def format_display(vim):
    curr_line_num = int(vim.eval('line(".")'))

    s, start_row, end_row = jcommon.get_all_same_indent(vim, base_indent_size=1)
    buff = vim.current.buffer

    # minor character rewrites
    s = jcommon.rewrite_data(s)

    lines = s.split("\n")
    if is_key_value_block(lines):
      from hsdl.vim import vim_commands_kh

      def get_preferred_order(data_list, common_d):
        if 'codes' in common_d and ('purchaser' in common_d or 'supplier' in common_d):
          preferred_order = """date purchaser supplier desc codes nontaxable person_value person_vat consumer_value
                               consumer_vat vat_in_num quantity waived_original waived_value
                               waived_vat import_value import_vat local_value local_vat""".split()
          return preferred_order
        else:
          return []

      def hook_for_column_line(common_d, data_list, line):
        if 'codes' in common_d and ('purchaser' in common_d or 'supplier' in common_d):
          if not 'date' in common_d:
            line.insert(0, 'date')

      def hook_for_each_line(common_d, data_list, line):
        if 'codes' in common_d and ('purchaser' in common_d or 'supplier' in common_d):
          if not 'date' in common_d:
            line.insert(0, '?')

      lines = expand_key_value_block(lines,
                                     fun_analyze=get_preferred_order,
                                     fun_column_line=hook_for_column_line,
                                     fun_each_line=hook_for_each_line)

      end_row -= 1  # because we add another line (column header), subtract 1 to fit them in

    final, raw_lines = jcommon.format_display_parse(lines)

    # has there been a change?
    if lines != final:
        jcommon.replace_vim_lines(buff, start_row, end_row, final)

        vim.command("normal " + str(curr_line_num) + "G")

def visualize_formatted_data(vim):
    curr_line_num = int(vim.eval('line(".")'))

    s, start_row, end_row = jcommon.get_all_same_indent(vim, base_indent_size=1)
    buff = vim.current.buffer

    s = jcommon.rewrite_data(s)

    lines = string.split(s, '\n')
    final, raw_lines = jcommon.format_display_parse(lines)
    if raw_lines:
        is_win32 = vim.eval('has("win32")') == '1'
        if is_win32:
            jcommon.launchProcess("grid", "c:/apps/python24/python24.exe", ["h:/hsdl/lib/python/hsdl/vim/grid.py"], start_path="h:/hsdl/lib/python/hsdl/vim/", sep_console=False, is_win32=is_win32)
        else:
            label = 'temp-' + str(uuid.uuid1())
            tempfname = '/tmp/' + label + '.pickle'
            fout = open(tempfname, 'wb')
            fout.write(cPickle.dumps(raw_lines))
            fout.close()

            jcommon.launchProcess("grid", "python", ["/tech/hsdl/lib/python/hsdl/vim/grid.py", tempfname], start_path="/tech/hsdl/lib/python/hsdl/vim/", sep_console=False, is_win32=is_win32)


def show_line(vim):
    start, end, _, _, s = vim.get_selection()
    print ">>>" + s + ">>>"

def get_shell_results(cmd):
    proc = os.popen(cmd)
    s = proc.read()
    proc.close()
    return  s.split("\n")[:-1]    # drop the last


def find_interesting_files(include_notes=True):
    fnames_mind = []
    fnames_notes = []
    fnames_notes_mind = []
    fnames_personal = []
    if include_notes:
        fnames_mind = glob.glob(general.interpolate_filename("${mind}/*.mind"))
        fnames_notes = glob.glob(general.interpolate_filename("${notes}/*.txt*"))
        fnames_notes_mind = glob.glob(general.interpolate_filename("${notes}/*.mind*"))
        fnames_personal = glob.glob(general.interpolate_filename("${notes}/cabinet/personal/*.gpg"))

    fnames_j = glob.glob(general.interpolate_filename("${lj}/hsdl/*.ijs"))
    fnames_jscripts = glob.glob(general.interpolate_filename("${lj}/hsdl/jscripts/*.ijs"))
    fnames_snippets = glob.glob(general.interpolate_filename("/home/hsdl/.vim/snippets/*.snippets"))
    fnames_pycommon = glob.glob(general.interpolate_filename("${lpy}/hsdl/common/*.py"))
    fnames_pyvim = glob.glob(general.interpolate_filename("${pyvim}/*.py"))
    fnames_pyeclipse = glob.glob(general.interpolate_filename("${pyeclipse}/*.py"))
    fnames_notes_embedit = glob.glob(general.interpolate_filename("${notes}/embedit/*.emb"))

    fnames_main =  get_shell_results('find /big/data_root/ -name "main_*.ijs"')
    fnames_ws = get_shell_results('find /tech/hsdl/lib/j/hsdl/ws/ -name "ws_*.ijs"')

    return  (fnames_mind + fnames_notes + fnames_notes_mind + fnames_personal + fnames_notes_embedit +
             fnames_j + fnames_jscripts + fnames_ws +  fnames_main  +
             fnames_snippets + fnames_pycommon + fnames_pyvim + fnames_pyeclipse)


def h_command(vim):
    tup1, tup2 = (vim.current.buffer.mark('<'), vim.current.buffer.mark('>'))
    if not tup1 or not tup2:        # if not already set, then set it; if it has been set (likely by the completion code), we don't want to overwrite it -- it was trying to preserve the info
        shared.INITIAL_SELECTION = (vim.current.buffer.mark('<'), vim.current.buffer.mark('>'))
    name = vim.eval("a:MainArg")
    args = map(lambda i: vim.eval("a:" + str(i)), xrange(1, int(vim.eval("a:0"))+1))
    r = h_command_base(vim, name, args)
    vim.command("delmarks <")
    vim.command("delmarks >")
    return r


# really, based on h_command
def hs_command(vim):
    name = 'search'
    arg0 = vim.eval("a:MainArg")
    args = [arg0] + map(lambda i: vim.eval("a:" + str(i)), xrange(1, int(vim.eval("a:0"))+1))
    return h_command_base(vim, name, args)          # we use h_command_base undercover


def send_h_command(vim, cmd_line):
    from hsdl.vim import jinteractive
    reload(jinteractive)

    args = string.split(cmd_line)
    name = args[0]
    args = args[1:]

    return h_command_base(vim, name, args)



def test_vrapper(vim):
        import net
        import org

        if 0:
            ed = net.sourceforge.vrapper.vim.DataDeposit.hidden
            print "+"*70
            print dir(ed.__class__)
            print ed.getTitleToolTip()
            #styled = ed.getViewer().getTextWidget()
            #print "333333", styled.getSelectionCount()
            print "+"*70

        win = net.sourceforge.vrapper.vim.DataDeposit.hidden

        print "000000000000000000000>>>>>>>>>>>", win.getPages()[0].getEditorReferences()[2].getEditor(0)
        print "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ:::", win.getPages()[0]

        inp = win.getPages()[0].getEditorReferences()[1].getEditorInput()
        win.getPages()[0].openEditor(inp, '')
        return

        win.getPages()[0].closeAllEditors(0)
        return

        thePage = win.getPages()[0].getEditorReferences()[2].getEditor(0)
        print "PPPPPPPPPPP:", thePage
        win.openPage(thePage)
        return

        path = win.getPages()[0].getActiveEditor().getTitleToolTip()
        print ">>>>>>>>>>>", path
        viewer = win.getPages()[0].getActiveEditor()

        active = win.getPages()[0].getActiveEditor()
        print "AAAAAAAAAA:", active, active.__class__.__name__
        if active.__class__.__name__ == 'PyEdit':
            # if isinstance(active, org.python.pydev.editor.PyEdit):  # this test does not work
            text = active.getEditorSourceViewer().getTextWidget()
        else:
            text = active.getViewer().getTextWidget()



        print ">>>>>>>>>>>", text.getSelectionCount()


        from hsdl.vim import vim_emulator_eclipse
        reload(vim_emulator_eclipse)
        vim = vim_emulator_eclipse.VimEmulatorEclipse(text, path)
        print vim.current.buffer.line
        print vim.current.buffer.lines
        print vim.current.buffer.name
        buffer = vim.current.buffer
        print "X"*70
        print buffer[:]
        print "X"*70

        buffer[2:-2] = "who\ndo\nyou\nthink\nyou\nare?"

        print "LINE_NUM:", vim.getLineNum()
        print "COL_NUM:", vim.getColNum()

        #vim.current.window.cursor = (5, 3)

        print vim.current.window.cursor

        print "@@@@@@@@@@@@@ LINE:", vim.eval("line('.')")
        print "@@@@@@@@@@@@@ COL:", vim.eval("col('.')")
        print "@@@@@@@@@@@@@ LINE2BYTE:", vim.eval("line2byte(2)")
        print "@@@@@@@@@@@@@ LINE($):", vim.eval("line('$')")
        print "@@@@@@@@@@@@@ COL($):", vim.eval("col('$')")



        page = win.getPages()[0]
        print "WWWWWWWWWINNNN:", win
        print "PPPPPPPPPPAGE:", page.openEditor


        if 0:
            from org.eclipse.jface.dialogs import InputDialog
            shell = viewer.getSite().getWorkbenchWindow().getShell()
            print "SSS:", shell
            shell = text.getShell()
            #shell = win.getShell()
            d = InputDialog(shell, "Title", "Please help me", "Default", None)
            d.open()
            return

        if 0:
            from org.eclipse.ui.part  import FileEditorInput
            #from org.eclipse.core.internal.resources import File
            from org.eclipse.core.resources import IFile
            f = IFile.create(None, 0, None)

            EFS = org.eclipse.core.filesystem.EFS
            fs = EFS.getFileSystem("file:///tmp/")

            return

            import java
            input = FileEditorInput(java.io.File("/tmp/doit.py"))

            #input = org.eclipse.ui.internal.part.services.NullEditorInput()
            theId = 'whatever123'
            page.openEditor(input, theId)


def h_command_from_vrapper(wb_win, doc, editor, command, line):

    try:
        import net
        import org

        #test_vrapper(vim)

        from hsdl.vim import vim_emulator_eclipse
        reload(vim_emulator_eclipse)
        ed, text = eclipse.vrapper_get_widget_info(wb_win)
        path = eclipse.vrapper_get_editor_path(ed)
        vim = vim_emulator_eclipse.VimEmulatorEclipse(text, path)

        parts = string.split(command)
        if not parts:
            return

        parts = parts[1:]   # drop the 'H'

        if not parts:
            return

        name = parts[0]
        args = parts[1:]
        return h_command_base(vim, name, args)

    except:
        buff = cStringIO.StringIO()
        traceback.print_exc(file=buff)
        print "*"*80
        print buff.getvalue()
        print "*"*80


# script is one line containing commands separated by "//"
#  e.g. :H lang j :spaced :vsplit // :H temp
def h_command_base_scripting_wrapper(vim, script):
    commands = script.split("//")
    for command in commands:
        parts = command.split()
        if len(parts)>1 and parts[0] in (':H', 'H'):
            cmd = parts[1]
            args = parts[2:]
            h_command_base(vim, cmd, args)
        elif len(parts)>1 and parts[0] in (':F', 'F'):
            cmd = parts[1]
            f_command_base(vim, cmd)


def h_command_base(vim, name, args):
    reload(jcommon)

    path = ''
    line = ''
    word = ''
    curr_line_num = 0
    curr_col = 0

    if vim and not type(vim) == types.FunctionType:
        curr_line_num = int(vim.eval('line(".")'))
        curr_col = int(vim.eval('col(".")'))-1
        line = vim.current.line
        word = jcommon.find_word(line, curr_col)
        path = vim.current.buffer.name

    if 0:
        from hsdl.cl import genlisp
        genlisp.start_lisp()
        genlisp.vim_prepare()

    lang = ''
    #lang = jcommon.get_lang(vim)


    exts = ['']
    if lang:
        exts.append('_' + lang)

    modules_vim = [os.path.splitext(os.path.split(each)[1])[0] for each in glob.glob("/tech/hsdl/lib/python/hsdl/vim/vim_command*.py")]
    modules_eclipse = [os.path.splitext(os.path.split(each)[1])[0] for each in glob.glob("/tech/hsdl/lib/python/hsdl/eclipse/eclipse_command*.py")]

    modules = modules_vim + modules_eclipse

    for module in modules:

        for ext in exts:

            #mod_name = 'vim_commands' + ext
            mod_name = module + ext

            try:
                if mod_name.startswith('vim_'):
                    main_m = __import__('hsdl.vim.' + mod_name)
                else:
                    main_m = __import__('hsdl.eclipse.' + mod_name)
            except:
                continue


            if mod_name.startswith('vim_'):
                mod = main_m.vim.__dict__[mod_name]
            else:
                mod = main_m.eclipse.__dict__[mod_name]

            reload(mod)


            if 1: #try:
                reload(mod)

                if name and name[0] == '(':
                    name = string.replace(name, '(', 'paren ')
                    parts = string.split(name)
                    if len(parts)>1:
                        args = parts[1:] + args
                    name = parts[0]

                if mod.__dict__.has_key(name):
                    meth = mod.__dict__[name]
                    if (meth.func_code.co_argcount == 12):
                        all_args = [
                                    None,                           # wb
                                    None,                           # win
                                    None,                           # doc
                                    None,                           # editor
                                    0,                              # offset
                                    curr_line_num,                  # line
                                    curr_col,                       # col
                                    word,                           # word
                                    path,                           # path
                                    args,
                                    vim,                            # vim
                                    0                               # decide_how_to_show
                                    ]
                        return apply(meth, all_args)
                    else:
                        if type(vim) == types.FunctionType:
                            the_fun = vim
                            vim = the_fun()
                        else:
                            vim = vim_emulator_vim.VimEmulatorVim(vim)
                            vim = jcommon.VimWrapper(vim)
                        return apply(meth, [vim] + args)

            else: #except Exception, e:
                if not vim:
                    raise e
                else:
                    buff = cStringIO.StringIO()
                    traceback.print_exc(file=buff)
                    parts = string.split(buff.getvalue(), '\n')
                    parts = jcommon.annotate_python_traceback(parts)
                    reload(jcommon)
                    vim.open_new_tab(general.mklocaltemp() + '.mind')

                    new_buffer = vim.current.buffer
                    new_buffer[:] = parts
                    vim.command("set nomodified")


def f_command_from_vrapper(wb_win, doc, editor, command, line):
    try:
        import net
        import org

        parts = string.split(command)

        if not parts:
            return

        parts = parts[1:]   # drop the 'F'

        if not parts:
            return

        name = parts[0]
        d = eclipse.vrapper_get_tabs_map(wb_win)
        for id, (title, editor, inp) in d.items():
            if string.find(title, name)>=0:
                page = wb_win.getActivePage()
                page.openEditor(inp, '')        # the id is not specified, thus ''
                break

    except:
        buff = cStringIO.StringIO()
        traceback.print_exc(file=buff)
        print "*"*80
        print buff.getvalue()
        print "*"*80


def f_command(vim, memorize_files_only=0):
    name = vim.eval("a:MainArg")
    reload(jcommon)
    found = vim.find_buffer_name_containing(name)

    if not found:
        all = find_interesting_files()
        matches = filter(lambda path: string.find(os.path.split(path)[1], name)>=0,   all)
        if memorize_files_only:
            matches = filter(lambda path: string.find(os.path.split(path)[1], '_mem.')>=0,   matches)

        tosort = map(lambda path:  (os.path.split(path),  path),   matches)
        tosort.sort()

        if tosort:
            _, the_path = tosort[0]

            vim.open_new_tab(the_path)
            vim.current.window.cursor = (1, 0)


def f_command_completion(vim, memorize_files_only=0):
    arglead = vim.eval("a:ArgLead")
    cmdline = vim.eval("a:CmdLine")
    parts = string.split(cmdline)

    r = []

    reload(jcommon)
    dict = vim.get_opened_buffer_map()

    r = []
    for _, paths in dict.items():
        for path in paths:
            _, base = os.path.split(path)
            if string.find(base, arglead) == 0:
                r.append(base)

    all = find_interesting_files()
    for path in all:
        the_base = os.path.split(path)[1]
        if string.find(the_base, arglead) == 0:
            r.append(the_base)

    r.sort()

    if memorize_files_only:
        r = filter(lambda path: path.find('_mem.')>=0, r)

    vim.command(":let g:returning=" + repr(r))

def find_local_files():
    return general.tree_walk(os.getcwd(), reject_exts=['.class', '.pyc', '.gif', '.jpg', '.png', '.pdf', '.so', '.o', '.zip', '.tar', '.gz', '.egg'], reject_names=['__pycache__'])

def ff_command(vim, memorize_files_only=0):
    name = vim.eval("a:MainArg")
    reload(jcommon)
    found = vim.find_buffer_name_containing(name)

    if not found:
        all = find_interesting_files(include_notes=False)
        all += find_local_files()

        matches = filter(lambda path: string.find(os.path.split(path)[1], name)>=0,   all)
        if memorize_files_only:
            matches = filter(lambda path: string.find(os.path.split(path)[1], '_mem.')>=0,   matches)

        tosort = map(lambda path:  (os.path.split(path),  path),   matches)
        tosort.sort()

        if tosort:
            _, the_path = tosort[0]

            vim.open_new_tab(the_path)
            vim.current.window.cursor = (1, 0)

def ff_command_completion(vim, memorize_files_only=0):
    arglead = vim.eval("a:ArgLead")
    cmdline = vim.eval("a:CmdLine")
    parts = string.split(cmdline)

    r = []

    reload(jcommon)
    dict = vim.get_opened_buffer_map()

    r = []
    for _, paths in dict.items():
        for path in paths:
            _, base = os.path.split(path)
            if string.find(base, arglead) == 0:
                r.append(base)

    all = find_interesting_files(include_notes=False)
    all += find_local_files()

    for path in all:
        the_base = os.path.split(path)[1]
        if string.find(the_base, arglead) == 0:
            r.append(the_base)

    r.sort()

    if memorize_files_only:
        r = filter(lambda path: path.find('_mem.')>=0, r)

    vim.command(":let g:returning=" + repr(r))

class EditorEmulatingEclipse:
    def __init__(self, vim):
        self.vim = vim

    def getLineNum(self):
        return int(self.vim.eval('line(".")'))

def c_command(vim):
    name = vim.eval("a:MainArg")
    args = map(lambda i: vim.eval("a:" + str(i)), xrange(1, int(vim.eval("a:0"))+1))
    return c_command_base(vim, name, args)

def c_command_from_vrapper(wb_win, doc, editor, command, line):

    try:
        import net
        import org

        #test_vrapper(vim)

        from hsdl.vim import vim_emulator_eclipse
        reload(vim_emulator_eclipse)
        ed, text = eclipse.vrapper_get_widget_info(wb_win)
        path = eclipse.vrapper_get_editor_path(ed)
        vim = vim_emulator_eclipse.VimEmulatorEclipse(text, path)

        parts = string.split(command)
        if not parts:
            return

        parts = parts[1:]   # drop the 'C'

        if not parts:
            return

        name = parts[0]
        args = parts[1:]
        return c_command_base(vim, name, args)

    except:
        buff = cStringIO.StringIO()
        traceback.print_exc(file=buff)
        print "*"*80
        print buff.getvalue()
        print "*"*80



def c_command_base(vim, name, args):
    try:
        from hsdl.eclipse import ViPluginCommandsC
        reload(ViPluginCommandsC)
        meth = ViPluginCommandsC.__dict__[name]

        #print "METH:", meth

        doc = None
        editor = EditorEmulatingEclipse(vim)
        cmd = name
        line = vim.current.line
        col = int(vim.eval('col(".")'))-1
        word = jcommon.find_word(line, col)
        path = vim.current.buffer.name

        reload(jcommon)
        if jcommon.is_vim_emulator(vim):
            path = jcommon.determineEclipseProject(path)


        #r = apply(meth, (doc, editor, cmd, line, col, word, path, vim))

        _, fun_default_args, _ = general.get_func_params_info(meth)
        if 'args' in fun_default_args:
            r = apply(meth, (doc, editor, cmd, line, col, word, path), {'vim': vim, 'decide_how_to_show':1, 'args':args})
        else:
            r = apply(meth, (doc, editor, cmd, line, col, word, path), {'vim': vim, 'decide_how_to_show':1})

        if r and type(r) == type(''):
            curr_indent  = jcommon.get_indentation(line)
            lines = string.split(r, '\n')
            lines = jcommon.indent_lines(lines, curr_indent)
            vim.insert_lines(lines)

    except Exception, e:
        if vim is None:
            raise e
        else:
            buff = cStringIO.StringIO()
            traceback.print_exc(file=buff)
            parts = string.split(buff.getvalue(), '\n')
            parts = jcommon.annotate_python_traceback(parts)
            vim.open_new_tab(general.mklocaltemp() + '.mind')

            new_buffer = vim.current.buffer
            new_buffer[:] = parts
            vim.command("set nomodified")


def c_command_completion(vim):
    arglead = vim.eval("a:ArgLead")
    cmdline = vim.eval("a:CmdLine")
    all = c_command_completion_base(vim, arglead, cmdline)
    return all

def c_command_completion_vrapper(wb_win, command):
    if not string.strip(command):
        return []

    parts = string.split(command)

    if command[-1] == ' ':
        arglead = ''
    else:
        arglead = parts[-1]

    try:
        from hsdl.vim import vim_emulator_eclipse
        reload(vim_emulator_eclipse)
        ed, text = eclipse.vrapper_get_widget_info(wb_win)
        path = eclipse.vrapper_get_editor_path(ed)
        vim = vim_emulator_eclipse.VimEmulatorEclipse(text, path)

        r = c_command_completion_base(vim, arglead, command)
        if r:
            print "="*30
            for each in r:
                print each,
            print
            print "="*30
        return r
    except:
        buff = cStringIO.StringIO()
        traceback.print_exc(file=buff)
        err = buff.getvalue()
        print "*" * 80
        print err
        print "*" * 80

        return []


def c_command_completion_base(vim, arglead, cmdline, the_files=[]):

    parts = string.split(cmdline)

    main = ''

    if arglead:
        # incomplete
        if len(parts) > 1: # only 'C' is showing
            if parts[1] != arglead:
                parts = parts[:-1]
                main = parts[1]
    else:
        if len(parts)>1:
            main = parts[1]

    from hsdl.eclipse import ViPluginCommandsC
    reload(ViPluginCommandsC)
    dict = ViPluginCommandsC.__dict__
    if main:
        if dict.has_key(main + '_completer'):
            completer_meth = dict[main + '_completer']

            _, fun_default_args, _ = general.get_func_params_info(completer_meth)
            if 'the_files' in fun_default_args:
                r = completer_meth(vim, arglead, parts[1:], the_files=the_files)
            else:
                r = completer_meth(vim, arglead, parts[1:])      # the first argument, 'C', is dropped
        else:
            r = []
    else:
        # C commands: finding functions that are tabbable is not as restrictive as the H commands
        r = filter(lambda name: type(dict[name]) == types.FunctionType and string.find(name, '_completer')<0 and string.find(name, '_helper')<0, dict.keys())

    r = filter(lambda name: string.find(name, arglead)==0, r)
    r = filter(lambda name: (not name.startswith('helper_')) and (not name.startswith('goto_func')) and (not name.startswith('OLD_')), r)

    r.sort()

    reload(jcommon)
    if jcommon.is_vim_emulator(vim):
        return r
    else:
        vim.command(":let g:returning=" + repr(r))


def c_command_emulate(vim, cmd, doc=None, editor=None, line='', col=-1, word='', path='', decide_how_to_show=1):
    from hsdl.eclipse import ViPluginCommandsC
    reload(ViPluginCommandsC)

    meth = ViPluginCommandsC.__dict__[cmd]

    doc = None
    if vim and not editor:
        editor = EditorEmulatingEclipse(vim)
    if vim and not line:
        line = vim.current.line
    if vim and col == -1:
        col = int(vim.eval('col(".")'))-1
    if not word:
        word = jcommon.find_word(line, col)
    if vim and not path:
        path = vim.current.buffer.name

    #r = apply(meth, (doc, editor, cmd, line, col, word, path, vim))
    r = apply(meth, (doc, editor, cmd, line, col, word, path), {'vim':vim, 'decide_how_to_show':decide_how_to_show})

    if r and type(r) == type(''):
        curr_indent  = jcommon.get_indentation(line)
        lines = string.split(r, '\n')
        lines = jcommon.indent_lines(lines, curr_indent)
        vim.insert_lines(lines)

# this is really a special shortcut that uses h_command_completion by secretly converting 'Hs __' to 'H search __'
def hs_command_completion(vim):
    arglead = vim.eval("a:ArgLead")
    cmdline = vim.eval("a:CmdLine")
    if cmdline[:3] == 'Hs ':
        cmdline = 'H search ' + cmdline[3:]
    all = h_command_completion_base(vim, arglead, cmdline)
    return all

def h_command_completion(vim):
    # preserve it before it gets replaced with text search of structure (e.g. get_lang())
    shared.INITIAL_SELECTION = (vim.current.buffer.mark('<'), vim.current.buffer.mark('>'))
    arglead = vim.eval("a:ArgLead")
    cmdline = vim.eval("a:CmdLine")
    all = h_command_completion_base(vim, arglead, cmdline)
    return all



def h_command_completion_vrapper(wb_win, command):
    if not string.strip(command):
        return []

    parts = string.split(command)

    if command[-1] == ' ':
        arglead = ''
    else:
        arglead = parts[-1]

    try:
        from hsdl.vim import vim_emulator_eclipse
        reload(vim_emulator_eclipse)
        ed, text = eclipse.vrapper_get_widget_info(wb_win)
        path = eclipse.vrapper_get_editor_path(ed)
        vim = vim_emulator_eclipse.VimEmulatorEclipse(text, path)

        r = h_command_completion_base(vim, arglead, command)
        if r:
            print "="*30
            for each in r:
                print each,
            print
            print "="*30
        return r
    except:
        buff = cStringIO.StringIO()
        traceback.print_exc(file=buff)
        err = buff.getvalue()
        print "*" * 80
        print err
        print "*" * 80

        return []


def h_command_completion_base(vim, arglead, cmdline, from_command_line=0):
    if from_command_line:
        lang = ''
    else:
        lang = jcommon.get_lang(vim)

    parts = string.split(cmdline)

    main = ''

    if arglead:
        # incomplete
        if len(parts) > 1: # only 'H' is showing
            if parts[1] != arglead:
                parts = parts[:-1]
                main = parts[1]
    else:
        if len(parts)>1:
            main = parts[1]

    force_sort = 1

    all_r = []

    exts = ['']
    if lang:
        exts.append('_' + lang)

    modules_vim = [os.path.splitext(os.path.split(each)[1])[0] for each in glob.glob("/tech/hsdl/lib/python/hsdl/vim/vim_command*.py")]
    modules_eclipse = [os.path.splitext(os.path.split(each)[1])[0] for each in glob.glob("/tech/hsdl/lib/python/hsdl/eclipse/eclipse_command*.py")]

    modules = modules_vim + modules_eclipse

    for module in modules:
        for ext in exts:
            r = []              # to be filled

            #mod_name = 'vim_commands' + ext
            mod_name = module + ext


            try:
                if mod_name.startswith('vim_'):
                    main_m = __import__('hsdl.vim.' + mod_name)
                else:
                    main_m = __import__('hsdl.eclipse.' + mod_name)
            except:
                continue


            if mod_name.startswith('vim_'):
                mod = main_m.vim.__dict__[mod_name]
            else:
                mod = main_m.eclipse.__dict__[mod_name]


            reload(mod)
            dict = mod.__dict__
            keys = dict.keys()
            keys.sort()
            if main:
                if dict.has_key(main + '_completer'):
                    completer_meth = dict[main + '_completer']
                    r = completer_meth(vim, arglead, parts[1:])      # the first argument, 'H', is dropped
                    if type(r) == type(()):                          # 1-tuple (containing a list) is the signal that list should NOT be sorted
                        r = r[0]
                        force_sort = 0

                elif dict.has_key(main) and dict[main].func_defaults:       # completer code is specified as j code in default argument
                    jcode = dict[main].func_defaults[0]
                    r = jcommon.callj_value(vim, jcode)
                else:
                    #r = h_command_completion_base_lisp(vim, main, arglead, parts[1:])       # NEW
                    r = []
            else:
                r = filter(lambda name: jcommon.is_function_visible(name,dict), dict.keys())
                r_lisp = lisp_find_all_definitions()
                #jcommon.debug_log("!!!!!!!!LANG EXT=" + repr(r_lisp))
                just_lisp = filter(lambda x: not x.endswith('-completer'), r_lisp)
                r += just_lisp

            if r:
                all_r += r


    all_r = filter(lambda name: string.find(name, arglead)==0, all_r)

    all_r = general.uniq_list(all_r)

    if force_sort:
        all_r.sort()

    reload(jcommon)
    if jcommon.is_vim_emulator(vim):
        return all_r
    else:
        vim.command(":let g:returning=" + repr(all_r)) #['sar','sop','son','suon']")


def h_command_completion_base_lisp(vim, name, arglead, args):
    from hsdl.cl import genlisp
    from hsdl.cl import shared
    shared.vim = vim

    try:
        full_name = "vim/" + name + '-completer'
        r = genlisp.eval_ecl("(fboundp '%s)" % full_name)
        if r == jcommon.ECL_T:
            r2 = genlisp.apply_ecl(full_name, [vim, arglead, args])
            #r2 = genlisp.apply_ecl(full_name, ['', arglead, args])
            return r2
        else:
            return []
    except Exception, e:
        if vim is None:
            raise e
        else:
            buff = cStringIO.StringIO()
            traceback.print_exc(file=buff)
            parts = string.split(buff.getvalue(), '\n')
            parts = jcommon.annotate_python_traceback(parts)
            reload(jcommon)
            vim.open_new_tab(general.mklocaltemp() + '.mind')

            new_buffer = vim.current.buffer
            new_buffer[:] = parts
            vim.command("set nomodified")
            return []


def lisp_find_all_definitions():
    return []       # !!! LISP TO BE DONE

    from hsdl.cl import genlisp

    all = []

    r = genlisp.eval_ecl('(apropos-list "")')
    for each in r:
        if each == jcommon.ECL_NIL: continue        # nil shows up
        if type(each) == types.TupleType:
            name = string.lower(each[0])
            if name.startswith("vim/"):
                all.append(name[4:])

    return all

# ---------- N commands (for snippets) ---------------

def snip_command(vim):
    reload(jcommon)

    buffer = vim.current.buffer
    cmd = vim.eval("a:MainArg")
    line = vim.current.line
    curr_line_num = int(vim.eval('line(".")'))
    curr_col = int(vim.eval('col(".")'))-1

    new_line = line[:curr_col] + cmd + line[curr_col:]
    buffer[curr_line_num-1 : curr_line_num] = [new_line]

    vim.current.window.cursor = (curr_line_num, curr_col + len(cmd))
    jcommon.trigger_snippet(vim)


def snip_command_completion(vim):
    arglead = vim.eval("a:ArgLead")
    cmdline = vim.eval("a:CmdLine")
    parts = string.split(cmdline)
    buffname = vim.current.buffer.name
    print buffname
    if not buffname: return

    main = ''

    if arglead:
        # incomplete
        if len(parts) > 1: # only 'C' is showing
            if parts[1] != arglead:
                parts = parts[:-1]
                main = parts[1]
    else:
        if len(parts)>1:
            main = parts[1]

    reload(jcommon)
    r = jcommon.snippets_list(vim)

    r = filter(lambda name: string.find(name, arglead)==0, r)
    vim.command(":let g:returning=" + repr(r))


def tooltip(vim):
    return jcommon.tooltip(vim)

# NOT USED
def hier_goto(vim):
    import vim_commands
    reload(vim_commands)
    vim_commands.hier_goto_helper(vim)


def visualize(vim):
    vimcallj(vim, visualize=True)

def testme(vim):
    vim.open_new_tab('')
    buffer = vim.current.buffer
    buffer[:] = ['sarino', 'is', 'a', 'nice', 'guy']


# 1 = forward; -1 = backward
def find_arg(vim, dir=1, recurse=1, use_col=None):
    line = vim.current.line
    (line_num, col_start) = vim.current.window.cursor
    if not use_col is None:
        col_start = use_col

    last_i = -1
    i = 0
    last_arg = ''
    while 1:
        r = arg_pat.search(line, i)
        if r:
            start = r.start()
            if dir == 1:
                if start > col_start:
                    last_i = start
                    last_arg = r.group()
                    break
            else:
                if start >= col_start:
                    break

            last_i = start
            last_arg = r.group()

            i = r.end()
        else:
            break

    if last_i >= 0 and last_i != col_start:

        old_last_i = last_i

        if 1:
            # ----- position it now
            p2 = last_i + len(last_arg)

            pat = re.compile(r"""('|"|\S)""")

            r = pat.search(line, p2)
            if r:
                start = r.start()
                diff = line[p2:start-1]
                if r.group() in ['"', "'"]:
                    last_i = start + 1
                else:
                    last_i = start

        if dir == -1 and last_i == col_start and last_i > 0 and recurse:
            find_arg(vim, dir=dir, recurse=0, use_col = old_last_i - 1)
        else:
            vim.current.window.cursor = (line_num, last_i)


def scan_future_waiting(vim):
    buffer = vim.current.buffer

    found_lines = []
    for i in xrange(len(buffer)):
        line = buffer[i]
        if string.find(line, '<<FUTURE/WAITING')>=0:
            found_lines.append(i+1)

    return found_lines

# return 1 if an update was done; otherwise 0
def update_future_waiting(vim, found_lines):
    for line_num in found_lines:
        vim.current.window.cursor = (line_num, 0)
        line = vim.current.line
        curr_indent  = jcommon.get_indentation(line)

        s, start_row, end_row = vim.get_block(check_indent=False)
        lines = string.split(s, '\n')

        if string.find(s, '<<FUTURE')>=0:
            if string.find(s, '<<FUTURE/WAITING')>=0:
                r = handle_future_waiting(vim, curr_indent, s, lines, start_row, end_row)
                if r:
                    vim.command("redraw")
                    return 1

    return 0

def check_futures_helper(vim):
    found_lines = []
    r = 1

    while 1:
        if shared.FUTURES_CHECKING_STOP:
            break

        if r:
            found_lines = scan_future_waiting(vim)

        if not found_lines: break

        r = update_future_waiting(vim, found_lines)
        time.sleep(5)

class MyThread(threading.Thread):
    def __init__(self, vim):
        threading.Thread.__init__(self)
        self.vim = vim

    def run(self):
        check_futures_helper(self.vim)

class FunThread(threading.Thread):
    def __init__(self, fun):
        threading.Thread.__init__(self)
        self.fun = fun

    def run(self):
        self.fun()


def check_futures_joined_thread(vim):
    th = MyThread(vim)
    th.start()
    th.join()

def check_futures_threaded(vim):
    buffname = vim.current.buffer.name
    if not buffname:
        print "Can only execute in a named buffer"
        return

    vim.command("set readonly")
    is_win32 = vim.eval('has("win32")') == '1'
    if 1: #is_win32:
        vim.command("syntax off")

    (line_num, _) = vim.current.window.cursor
    vim.add_sign(line_num, buffname, symbol='thread')
    vim.command("redraw")

    check_futures_joined_thread(vim)

    vim.command("set noreadonly")
    if 1: #is_win32:
        vim.command("syntax on")

    vim.sign_clear()

def check_futures(vim):
    import thread
    thread.start_new_thread(check_futures_threaded, (vim,))

def check_futures(vim):
    while 1:
        found_lines = scan_future_waiting(vim)

        if found_lines:
            update_future_waiting(vim, found_lines)
        else:
            break

        time.sleep(1)


# returns the first such line number; if not found, returns 0
def find_auto_repeat_set(fname, repeat_set):
    pat = re.compile(r'<<REPEAT(_DOWN)?:' + repeat_set + '(:[^>]+)?>>')

    fin = open(fname, 'rb')
    i = 1
    while 1:
        line = fin.readline()
        if not line: break
        if pat.search(line): #string.find(line, to_find)>=0 or string.find(line, to_find2)>=0:
            fin.close()     # we're done; don't forget to close file
            return i
        i += 1

    fin.close()
    return 0



ansi_pat = re.compile(chr(27) + r"\[[0-9]+[a-zA-Z]")

def remove_ansi_coloring(s):
    return pat.sub('',s)


def parse_command_line(args, defaults):
    d = {}
    for arg in args:
        p = string.find(arg, '=')
        if p>=0:
            key = arg[:p]
            value = arg[p+1:]
        else:
            key = arg

            if arg[0] == '-':
                value = 'true'
            else:
                value = ''

        if key[:2] == '--':
            key = key[2:]
        elif key[0] == '-':
            key = key[1:]

        d[key] = value

    for key, value in defaults.items():
        if not d.has_key(key):
            d[key] = value

    return d

# NOTES: these things cause automation to fail (or run incorrectly)
#   folding
#   using feedkeys(); seems to be a timing issue; call the python function directly instead

def check_for_automation(vim):
    if os.environ.has_key('VIM_COMMAND_THEN_EXIT'):
        vim.command(os.environ['VIM_COMMAND_THEN_EXIT'])
        vim.command(":silent q!")
    elif os.environ.has_key('VIM_COMMAND'):
        h_command_base_scripting_wrapper(vim, os.environ['VIM_COMMAND'])
    elif os.environ.has_key('VIM_AUTO_ARGS'):
        #shared.EXCEPTION_EXIT = 1

        args = cPickle.loads(urllib.unquote_plus(os.environ['VIM_AUTO_ARGS']))
        defaults = {'sarino' : 'SUON',
                    'fred' : 'FREDDO'}
        d = parse_command_line(args, defaults)
        if d.has_key('path'):
            path = d['path']
            vim.command("silent! e %s" % path)

        if d.has_key('action'):
            from hsdl.cl import genlisp
            genlisp.start_lisp()
            genlisp.prepare()
            genlisp.vim_prepare()
            genlisp.eval_ecl('(load "/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp")')

            from hsdl.vim import jinteractive
            reload(jinteractive)

            md = jinteractive.__dict__
            if md.has_key(d['action']):
                meth = md[d['action']]
                meth(vim, d)

def auto_checkit(vim, args_dict):
    from hsdl.vim import jinteractive
    vim.current.window.cursor = 55, 1
    jinteractive.vimcallj(vim)

    vim.current.window.cursor = 271, 9
    jinteractive.vimcallj(vim)

    vim.current.window.cursor = 428, 12
    jinteractive.vimcallj(vim)

    vim.current.window.cursor = 479, 8
    jinteractive.vimcallj(vim)

    for i in xrange(1123):
        vim.command("normal -)")
        jinteractive.vimcallj(vim)

    vim.command("w! /tmp/eraseme.mind")
    vim.command("qa!")

    return

# return -1 if nothing found
def auto_find(vim, pattern, start=0):
    lines = vim.current.buffer[:]
    for i in xrange(start, len(lines)):
        line = lines[i]
        if string.find(line, pattern)>=0:
            return i
    return -1

def auto_tags(vim, args_dict):
    curr_line = 0
    while 1:
        line_num = auto_find(vim, '(<<automate>>', start=curr_line)
        if line_num>=0:
            vim.current.window.cursor = line_num+1, 0
            ancs = vim.find_ancestors()

            if ancs:
                lang, block, col, row1, row2 = jcommon.find_first_lang_spec(ancs)
                if lang:
                    sexp, _ = full_parse_sexp(block, 0)
                    if sexp:
                        found = None
                        for child in sexp:
                            if type(child.obj) == list:
                                if child[0] == ('===', ):
                                    found = child
                        if found:
                            new_line = row1 + found.line_num
                            vim.current.window.cursor = new_line, found.line_col + 1  # put us past the open paren
                            vimcallj(vim)
                            curr_line = new_line
                            continue

            curr_line = line_num + 1
        else:
            break


def auto_tags(vim, args_dict):
    curr_line = 0
    while 1:
        line_num = auto_find(vim, '(<<automate>>', start=curr_line)
        if line_num>=0:
            vim.current.window.cursor = line_num+1, 0
            ancs = vim.find_ancestors()

            if ancs:
                lang, block, col, row1, row2 = jcommon.find_first_lang_spec(ancs)
                if lang:
                    sexp, _ = full_parse_sexp(block, 0)
                    if sexp:
                        found = []
                        for child in sexp:
                            if type(child.obj) == list:
                                if child[0] == ('<<automate>>', ):
                                    found.append(child)

                        if found:
                            for automate in found:
                                for child in automate:
                                    if type(child.obj) == list:
                                        if child[0] == ('===', ):
                                            print row1 + child.line_num
                                            new_line = row1 + child.line_num
                                            vim.current.window.cursor = new_line, child.line_col + 1  # put us past the open paren
                                            vimcallj(vim)
                                            curr_line = new_line
                            continue

            curr_line = line_num + 1
        else:
            break

# NOTES: only a future within an 'id' field gets executed
def auto_futures(vim, args_dict):
    curr_line = 0

    while 1:
        line_num = auto_find(vim, '(<<future>>', start=curr_line)

        if line_num < 0:
            break

        else:
            vim.current.window.cursor = line_num+1, 0
            line = vim.current.line
            p = string.find(line, '(<<future>>')
            if p >= 0:

                # see if 'id' already exists; it should not
                vim.current.window.cursor = line_num+1, p       # move to paren so that we can get the entire sexp
                s = jcommon.get_matched_region(vim)
                if s:
                    sexp, _ = full_parse_sexp(s, 0)
                    future_info, code_sexp, start, end = get_future_data_from_sexp(sexp)
                    if future_info.has_key(('id',)):
                        break

                vim.current.window.cursor = line_num+1, p + 2   # move to within <<future>> tag
                process_future(vim, action='launch')

                vim.current.window.cursor = line_num+1, p       # move to paren so that we can get the entire sexp
                s = jcommon.get_matched_region(vim)
                if s:
                    sexp, _ = full_parse_sexp(s, 0)
                    future_info, code_sexp, start, end = get_future_data_from_sexp(sexp)
                    if future_info.has_key(('id',)):
                        label = future_info[('id',)][0]
                        print "Future:", label

                        # --- keep checking
                        vim.current.window.cursor = line_num+1, p + 2   # move to within <<future>> tag
                        while 1:
                            process_future(vim, action='query')         # if done, id will be added, so that output will display on the next call
                            time.sleep(1)
                            f_done,  f_ref,  f_time_start,  f_time_done, f_output = get_future_info(label)
                            if f_done or not future_info_existence(label):
                                process_future(vim, action='query')     # do it again to display output
                                break

            curr_line = line_num + 1


    #tempfname = general.local_hsdl_mktemp('OUT__') + '.mind'
    tempfname = 'OUT-' + str(uuid.uuid1()) + '.mind'
    vim.command("w! " + tempfname)
    vim.command("qa!")

def check_for_repgen(vim):
    name = vim.current.buffer.name
    if name:
        dirname, basename = os.path.split(name)
        if basename[:2] == 'H.' or (basename[:3] in ['RD.', 'RB.']):
            vim.command(":set syn=rgen")


def temp(vim):  # same as vim_commands:temp()
    vim.open_new_tab(general.mklocaltemp() + '.mind')


def mark_buffer_switch(vim):
    if shared.MARK_BUFFER_SWITCH:
        try:
            name = vim.current.buffer.name
            if name  and  name != shared.CURR_BUFFER_PATH:
                shared.LAST_BUFFER_PATH = shared.CURR_BUFFER_PATH
                shared.CURR_BUFFER_PATH = name

        except:
            pass    # we don't want a problem here; just ignore

# must be called explicitly
def mark_buffer_switch_of_three(vim):
  name = vim.current.buffer.name

  last_three = shared.LAST_THREE_PATHS
  if name in last_three:
    # shift right 1
    p = last_three.index(name)
    shared.LAST_THREE_PATHS = last_three[p+1:] + last_three[:p] + [last_three[p]]
  else:
    # shift right 1 but add new file as the last in the list
    shared.LAST_THREE_PATHS = [last_three[2], last_three[0], name]


def toggle_buffer(vim, switch_tab=0):
    reload(jcommon)
    if switch_tab:
        #print shared.LAST_BUFFER_PATH
        if shared.LAST_BUFFER_PATH:
            _, base = os.path.split(shared.LAST_BUFFER_PATH)
            vim.command(":F " + base)
    elif shared.LAST_BUFFER_PATH:
        vim.go_to_opened_buffer(shared.LAST_BUFFER_PATH)

def toggle_buffer_of_three(vim):
  last_three = shared.LAST_THREE_PATHS
  if last_three[1]:
    # shift right 1
    shared.LAST_THREE_PATHS = [last_three[2], last_three[0], last_three[1]]
    print shared.LAST_THREE_PATHS

    shared.MARK_BUFFER_SWITCH = 0
    vim.go_to_opened_buffer(last_three[1])
    shared.MARK_BUFFER_SWITCH = 1

def toggle_status(vim):
    print shared.LAST_BUFFER_PATH + "  /  " +  shared.CURR_BUFFER_PATH + "\n=========="


def make_j_string(s):
    return "'" + string.replace(s, "'", "''") + "'"

def start_at_quote(s):
    p = string.find(s, "'")
    if p>=0:
        return s[p:]
    else:
        return s


# There is always this bit of code to guide us:
#   'some_volname' getinfo__varname
# If found and the varname is not already defined, load the volume using the varname
def first_load_volume(vim, jcode):
    varname = ''
    volname = ''

    pat = re.compile(r"'(?P<volname>[^']+)' getinfo__(?P<varname>[a-z]+)")
    r = pat.search(jcode)
    if r:
        volname = r.group('volname')
        varname = r.group('varname')
        if not jcommon.jexists(varname):
            code = varname + "=: volload'%s'" % volname
            jcommon.callj(vim, code)



def get_j_code(vim):
    path = vim.current.buffer.name

    line = vim.current.line
    col = int(vim.eval('col(".")'))-1

    code = make_j_string(start_at_quote(line[col:]))
    first_load_volume(vim, code)
    rest = 'LF  combine <"1   repr   /:~  ( ti0 ;  ( ((> @: , @: tolines) @: ti1 @: ti1) ) )"_1     regscripts  ".    rewrite_wip_code  ' + code

    from hsdl.vim import jcommon
    reload(jcommon)

    lines = jcommon.callj_value(vim, rest)

    if not lines:
        lines = ''

    tempfname = general.local_hsdl_mktemp('INF__') + '.mind'

    vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa

    buffer = vim.current.buffer
    buffer[:] = string.split(lines, '\n')
    vim.command("set nomodified")

    vim.go_to_opened_buffer(path)



def get_j_info(vim):
    path = vim.current.buffer.name

    line = vim.current.line
    col = int(vim.eval('col(".")'))-1

    first_load_volume(vim, start_at_quote(line[col:]))
    rest = 'LF  combine <"1   repr   ,.  ".  rewrite_wip_code  ' + make_j_string(start_at_quote(line[col:]))

    from hsdl.vim import jcommon
    reload(jcommon)

    lines = jcommon.callj_value(vim, rest)


    tempfname = general.local_hsdl_mktemp('INF__') + '.mind'

    vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa

    buffer = vim.current.buffer
    buffer[:] = string.split(lines, '\n')
    vim.command("set nomodified")

    vim.go_to_opened_buffer(path)


def get_j_map(vim):
    path = vim.current.buffer.name

    line = vim.current.line
    col = int(vim.eval('col(".")'))-1

    first_load_volume(vim, start_at_quote(line[col:]))
    rest = 'LF  combine <"1   repr   > 0 {   ".   rewrite_wip_code  ' + make_j_string(start_at_quote(line[col:]))

    from hsdl.vim import jcommon
    reload(jcommon)

    lines = jcommon.callj_value(vim, rest)


    tempfname = general.local_hsdl_mktemp('INF__') + '.mind'

    vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa

    buffer = vim.current.buffer
    buffer[:] = string.split(lines, '\n')
    vim.command("set nomodified")

    vim.go_to_opened_buffer(path)



def get_j_data(vim):
    path = vim.current.buffer.name

    line = vim.current.line
    col = int(vim.eval('col(".")'))-1

    first_load_volume(vim, start_at_quote(line[col:]))
    rest = 'LF  combine <"1   repr   > 1 {   ".   rewrite_wip_code  ' + make_j_string(start_at_quote(line[col:]))

    from hsdl.vim import jcommon
    reload(jcommon)

    lines = jcommon.callj_value(vim, rest)


    tempfname = general.local_hsdl_mktemp('INF__') + '.mind'

    vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa

    buffer = vim.current.buffer
    buffer[:] = string.split(lines, '\n')
    vim.command("set nomodified")

    vim.go_to_opened_buffer(path)


def get_j_raw_data(vim):
    path = vim.current.buffer.name

    line = vim.current.line
    col = int(vim.eval('col(".")'))-1

    first_load_volume(vim, start_at_quote(line[col:]))
    rest = 'LF  combine <"1   repr   > 1 {   ".   rewrite_wip_code  ' + make_j_string(start_at_quote(line[col:]))

    from hsdl.vim import jcommon
    reload(jcommon)

    lines = jcommon.callj_value(vim, rest)


    tempfname = general.local_hsdl_mktemp('INF__') + '.mind'

    vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa

    buffer = vim.current.buffer
    buffer[:] = string.split(lines, '\n')
    vim.command("set nomodified")

    vim.go_to_opened_buffer(path)


def get_j_data_visualize(vim, special=1):
    path = vim.current.buffer.name

    line = vim.current.line
    col = int(vim.eval('col(".")'))-1

    if special:
        first_load_volume(vim, start_at_quote(line[col:]))
        rest = 'VISUALIZE  > 1 {   ".   rewrite_wip_code  ' + make_j_string(start_at_quote(line[col:]))
    else:
        first_load_volume(vim, line[col:])
        rest = 'VISUALIZE  ".   rewrite_wip_code  ' + make_j_string(line[col:])

    print rest

    from hsdl.vim import jcommon
    reload(jcommon)

    visualize_data_using_wx(vim, rest)


def get_j_goto_file(vim, go_to_script=0):
    path = vim.current.buffer.name

    line = vim.current.line
    col = int(vim.eval('col(".")'))-1

    first_load_volume(vim, start_at_quote(line[col:]))

    if go_to_script:
        rest = """  'script' getmap   > 0 {  ".   rewrite_wip_code  """ + make_j_string(start_at_quote(line[col:]))
    else:
        rest = """  'fname' getmap   > 0 {  ".   rewrite_wip_code  """ + make_j_string(start_at_quote(line[col:]))


    from hsdl.vim import jcommon
    reload(jcommon)

    result = jcommon.callj_value(vim, rest)

    if result:
            parts = map(lambda part: string.strip(part),  string.split(result))

            if parts:

                first_one = 1

                # keep in mind that the first file is special; we start a new tab with it
                # other filenames in the list will be contained in a split window
                for fname in parts:
                        pat = re.compile(r'(?P<path>[^#`]+)(``(?P<subpath>[^#]+))?(#(?P<line_num>[0-9]+))?')

                        r = pat.search(fname)
                        if r.group('line_num'):
                            line_num = int(r.group('line_num'))
                        else:
                            line_num = 1

                        main_path = r.group('path')
                        search_for = main_path

                        subpath = r.group('subpath')

                        dirname, base_name = os.path.split(main_path)
                        _, ext = os.path.splitext(base_name)

                        prefix = ''
                        suffix = ''
                        if subpath:
                            prefix = 'zipfile:'
                            suffix = '::' + subpath
                            search_for = subpath

                        full_path = prefix + main_path + suffix

                        if first_one:
                            r = vim.check_already_exists(search_for)
                            if r:
                                tab_num, paths, found_fname = r
                                vim.go_to_window_in_tab(tab_num, paths, found_fname)
                                vim.current.window.cursor = (line_num, 0)

                                break       # just open the existing tab; no need to continue by adding additional split screens

                            else:
                                vim.open_new_tab(full_path)
                                vim.current.window.cursor = (line_num, 0)
                        else:
                            if subpath:
                                _, base_subpath = os.path.split(subpath)
                                _, ext = os.path.splitext(base_subpath)
                                ext = string.upper(ext)
                                if not ext in ['.xml', '.csv', '.txt', '.ijs', '.html', '.js', '.json']:
                                    continue

                            vim.open_new_split(full_path, vertical=0)
                            vim.current.window.cursor = (line_num, 0)

                        first_one = 0



def show_actions(vim):
    r = jcommon.find_lisp_actions(vim)
    if r:
        final = []
        for item in r:
            final.append(item + '   :::      ')

        tempfname = general.local_hsdl_mktemp('INF__') + '.mind'

        vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa

        buffer = vim.current.buffer
        buffer[:] = final
        vim.command("set nomodified")


def scala_type_at(vim):
    pos = int(vim.eval('line2byte(line("."))+col(".")')) - 1 - 1
    print "POS:", pos
    fname = vim.current.buffer.name
    r = jcommon.scala_type_at(vim, fname, pos)
    print r


def scala_complete(vim):
    pos = int(vim.eval('line2byte(line("."))+col(".")')) - 1 - 1
    fname = vim.current.buffer.name

    buffer = vim.current.buffer
    z = vim.current.buffer[:]
    s = string.join(z, '\n')

    tempfname = general.mklocaltemp() + '.scala'
    fout = open(tempfname, 'wb')
    fout.write(s)
    fout.close()

    r = jcommon.scala_complete(vim, tempfname, pos)
    #os.unlink(tempfname)

    print "="*50
    print tempfname, pos, "|||" + s[pos-10:pos+10] + "|||"  + s[pos-2:pos+3] + "|||",  r
    print "="*50



def table_to_vim(vim):
    s = vim.eval("@*")
    jcommon.sendjdata(vim, s, do_unprotect=False, tempvar='TEMPTEMP')
    lines = jcommon.callj_value(vim, 'todelimited fromexcel2 TEMPTEMP')
    jcommon.sendjdata(vim, '', do_unprotect=False, tempvar='TEMPTEMP')

    if lines:
        lines = map(lambda line: '    ' + line,  lines)
        vim.insert_lines(lines)


def process_block(vim):
    start, end, start_col, end_col, s = vim.get_selection()
    if s:
        lines = string.split(s, '\n')
        lines = map(lambda line: line[start_col:end_col+1], lines)

        print ">>>>>>>", start, end, start_col, end_col
        for line in lines:
            print ":::::::::::", line




def match_yank_send(vim):
    buffname = vim.current.buffer.name
    if buffname:
        parent, fname = os.path.split(buffname)
        basename, ext = os.path.splitext(fname)
        ext = ext[1:]   # drop the leading DOT
    else:
        return


    if ext in ['lfe', 'clj']:
        vim.command("normal v")
        vim.command("normal f")
        vim.command("normal %")
        vim.command('normal "ty')
        buff = vim.eval("@t")
        buff = string.rstrip(buff)
        vim.command('normal ``')        # send cursor back to where you started
    else:
        buff, _, _ = vim.get_block(direction=0, check_indent=False)

    reload(jcommon)
    tup = jcommon.findMrxvtFifo(ext)

    if tup:
        user, pid, fname = tup
        if os.path.exists(fname):
            fout = open(fname, 'ab')

            lines = string.split(buff, '\n')
            for line in lines:
                fout.write('Str ' + line + '\\n\n')
                fout.flush()
            fout.close()



def yank_send(vim):
    buffname = vim.current.buffer.name
    if buffname:
        parent, fname = os.path.split(buffname)
        basename, ext = os.path.splitext(fname)
        ext = ext[1:]   # drop the leading DOT
    else:
        return


    if ext in ['lfe', 'clj', 'scm', 'lisp']:
        vim.command("normal [(")
        vim.command("normal v")
        vim.command("normal f")
        vim.command("normal %")
        vim.command('normal "ty')
        buff = vim.eval("@t")
        buff = string.rstrip(buff)
        vim.command('normal ``')    # send cursor back to where you started
    else:
        buff, _, _ = vim.get_block(direction=0, check_indent=False)


    print "="*70
    print buff
    print "="*70




def view_future(label):
    if jcommon.is_future_running_helper(label):
        os.system("mrxvt -t mrxvt_floater -e screen -r main -x -p " + label + " &")


def check_futures_delegate(vim):
    shared.FUTURES_CHECKING_STOP = 1
    check_futures(vim)


def flatten_lisp_list(obj):
    final = []
    curr = obj
    while curr:
        final.append(curr.first)
        curr = curr.rest
    return final




def calc_shift(pos, shift_list):
    count = 0
    for shift_pos, shift_count in shift_list:
        if pos > shift_pos:         # note we don't do >=, because = will mean that a string will shift itself
            count += shift_count

    return count



def include_shift(obj, orig, shift_list, line_ranges):
    shift_start = calc_shift(obj.start, shift_list)
    if shift_start>0:
        obj.shift_start(shift_start)

    shift_end = calc_shift(obj.end, shift_list)
    if shift_end>0:
        obj.shift_end(shift_end)

    obj.calc_line_col(line_ranges)      # note: we call this AFTER the adjustment is done

    if type(obj.obj) in [types.StringType, types.UnicodeType]:
        poss_triple_quotes = orig[obj.start-2:obj.start+1]
        if poss_triple_quotes == '"""':
            obj.orig_str = '"""'        # this is just to signify that triple quotes are used

    if type(obj.obj) == types.ListType:
        for subobj in obj.obj:
            include_shift(subobj, orig, shift_list, line_ranges)


def hooray_helper(obj, final):
    real = obj.obj
    if type(real) == types.StringType:
        final.append(('(attach-pos-info  %d %d  "' % (obj.start, obj.end)) + string.replace(real, '"', '\\"') + '")')
    elif type(real) == types.TupleType:
        final.append(("(attach-pos-info %d %d  '%s)" % (obj.start, obj.end, real[0])))
    elif type(real) == types.ListType:
        final.append("(attach-pos-info %s %s (list " % (obj.start, obj.end))
        for subobj in real:
            hooray_helper(subobj, final)
        final.append(")) ")
    else:
        final.append(("(attach-pos-info %d %d  %s)" % (obj.start, obj.end, str(real))))


def hooray(obj):
    final = []
    hooray_helper(obj, final)
    return string.join(final, '')


def lisp_to_python(parser, orig, obj, start, end, real_pair):
    if isinstance(obj, Pair):
        curr = obj
        final = []
        is_first = 1
        while curr:
            if is_first:
                final.append(lisp_to_python(parser, orig, curr.first, curr.start, curr.end, real_pair))
            else:
                final.append(lisp_to_python(parser, orig, curr.first, curr.start, curr.end, curr))

            is_first = 0
            curr = curr.rest

        items = parser.registry.items()
        items.sort()
        for (true_start, true_end), the_obj in items:
            if the_obj == real_pair:  # that's me!
                return jcommon.SexprWrapper(final, true_start, true_end)

        return jcommon.SexprWrapper(final, start, end)

    elif isinstance(obj, Symbol):
        return jcommon.SexprWrapper((obj.name, ), start, end)
    elif type(obj) in [types.IntType, types.LongType, types.FloatType]:
        st = orig[start:end]
        new_obj = jcommon.SexprWrapper(obj, start, end)
        new_obj.orig_str = st
        return new_obj
    elif type(obj) in [types.StringType, types.UnicodeType]:
        poss_quotes = orig[start-3:start+3]
        st = orig[start:end]
        new_obj = jcommon.SexprWrapper(obj, start, end)
        if st[:3] == '"""':
            new_obj.orig_str = st                               #TODO is it a good idea to use .orig_str?
        return new_obj
    else:   # quantity
        return jcommon.SexprWrapper(obj, start, end)


# this only works for an sexp
def lisp_to_python_main(parser, orig, orig2, obj, shift_list, line_ranges):
    r = lisp_to_python(parser, orig2, obj, obj.start, obj.end, obj)
    include_shift(r, orig, shift_list, line_ranges)
    return r

def struct_to_wrapper(obj):
    if type(obj) == types.ListType:
        final = map(struct_to_wrapper, obj)
        return jcommon.SexprWrapper(final, -1, -1)
    elif type(obj) == types.TupleType:
        return jcommon.SexprWrapper(obj, -1, -1)
    else:
        return jcommon.SexprWrapper(obj, -1, -1)


def process_sexp_info(vim):
    ancs = vim.find_ancestors()
    lang, _, _, _, _  = jcommon.find_first_lang_spec(ancs)
    print lang

def get_more_info(vim):
    reload(jcommon)
    _, col = vim.current.window.cursor
    line = vim.current.line
    word = jcommon.find_word(line, col)
    word = string.replace(word, ')', '')
    word = string.replace(word, '(', '')
    word = string.replace(word, '#', '')
    word = string.replace(word, "'", '')
    r = jcommon.describe_symbol(vim, word)
    if not r is None:
        jcommon.lisp_display_info(vim, string.split(r,'\n'))

    return
    if not r is None:
        path = vim.current.buffer.name
        tempfname = general.local_hsdl_mktemp('LISP__') + '.mind'
        vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='LISP__')     # if another already exists within the sa
        buffer = vim.current.buffer
        buffer[:] = string.split(r, '\n')
        vim.command("set nomodified")

        vim.go_to_opened_buffer(path)  # go back


def describe_function(vim):
    reload(jcommon)
    _, col = vim.current.window.cursor
    line = vim.current.line
    word = jcommon.find_word(line, col)
    word = string.replace(word, ')', '')
    word = string.replace(word, '(', '')
    s = jcommon.describe_function(vim, word)
    if s:
        jcommon.lisp_display_info(vim, string.split(s,'\n'))
        return

        path = vim.current.buffer.name
        tempfname = general.local_hsdl_mktemp('BIN__') + '.mind'
        vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='BIN__')     # if another already exists within the sa
        buffer = vim.current.buffer
        buffer[:] = string.split(s, '\n')
        vim.command("set nomodified")

        vim.go_to_opened_buffer(path)  # go back

def disassemble_symbol(vim):
    reload(jcommon)
    _, col = vim.current.window.cursor
    line = vim.current.line
    word = jcommon.find_word(line, col)
    word = string.replace(word, ')', '')
    word = string.replace(word, '(', '')
    r = jcommon.disassemble_symbol(vim, word)
    if not r is None:
        jcommon.lisp_display_info(vim, string.split(r,'\n'))
        return
        path = vim.current.buffer.name
        tempfname = general.local_hsdl_mktemp('BIN__') + '.mind'
        vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='BIN__')     # if another already exists within the sa
        buffer = vim.current.buffer
        buffer[:] = string.split(r, '\n')
        vim.command("set nomodified")

        vim.go_to_opened_buffer(path)  # go back


def apropos_list_for_emacs(vim):
    reload(jcommon)

    _, col = vim.current.window.cursor
    line = vim.current.line
    word = jcommon.find_word(line, col)
    word = string.replace(word, ')', '')
    word = string.replace(word, '(', '')
    lines = jcommon.apropos_list_for_emacs(vim, word)
    if lines:
        jcommon.lisp_display_info(vim, lines)
        return
        path = vim.current.buffer.name
        tempfname = general.local_hsdl_mktemp('BIN__') + '.mind'
        vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='BIN__')     # if another already exists within the sa
        buffer = vim.current.buffer
        buffer[:] = lines
        vim.command("set nomodified")

        vim.go_to_opened_buffer(path)  # go back

def lisp_hyperspec(vim, go_to_first=0):
    reload(jcommon)
    _, col = vim.current.window.cursor
    line = vim.current.line
    word = jcommon.find_word(line, col)
    word = string.replace(word, ')', '')
    word = string.replace(word, '(', '')

    hyperspec_path = general.interpolate_filename('${HSDL_SOFT_HOME}/data/hyperspec/HyperSpec/')
    db_path = general.interpolate_filename('${pyvim}/tools/hyperspec.db')

    if not shared.HYPERSPEC_DB and os.path.exists(db_path):
        import bsddb
        db = bsddb.btopen(db_path, 'r')
        shared.HYPERSPEC_DB = db
    else:
        db = shared.HYPERSPEC_DB

    if db.has_key(word):
        all = cPickle.loads(db[word])

        final = []
        final.append(word)
        for desc, html_page in all:
            final.append('    %s        file://%s' % (desc, os.path.join(hyperspec_path, html_page)))

        if go_to_first:
            desc, html_page = all[0]
            url = os.path.join(hyperspec_path, html_page)
            #os.system('firefox %s' % page_path)
            tempfname = general.local_hsdl_mktemp() + '.sh'     #TODO better way of starting processing in the background and piping standard error to /dev/null, so that X warning does not show
            fout = open(tempfname, 'wb')
            fout.write('cd %s; firefox %s >& /dev/null; rm %s\n' % ("/tech/hsdl/lib/python/hsdl/vim/", url, tempfname))
            fout.close()
            jcommon.launchProcess("bash", "bash", [tempfname], start_path="/tech/hsdl/lib/python/hsdl/vim/", sep_console=False, is_win32=0)
        else:
            jcommon.lisp_display_info(vim, final)

            return

            path = vim.current.buffer.name
            tempfname = general.local_hsdl_mktemp('BIN__') + '.mind'
            vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='BIN__')     # if another already exists within the sa
            buffer = vim.current.buffer
            buffer[:] = final
            vim.command("set nomodified")

            vim.go_to_opened_buffer(path)  # go back


def lisp_compile_file(vim, load=0):
    reload(jcommon)

    path = vim.current.buffer.name
    if not path:
        return

    reload(jcommon)

    _, col = vim.current.window.cursor
    line = vim.current.line
    word = jcommon.find_word(line, col)
    word = string.replace(word, ')', '')
    word = string.replace(word, '(', '')
    if jcommon.vim_modified(vim):
        vim.command(":w")

    messages = jcommon.lisp_compile_file(vim, path, load=load)
    vim.sign_clear()

    if messages:
        all_code = {}   # path -> line_ranges
        lines = []

        for d in messages:
            if d.has_key(':message'):
                lines.append('>> ' + d[':message'])
                if d.has_key(':severity'):
                    lines.append('KIND: ' + d[':severity'][0])
                if d.has_key(':location'):
                    val = d[':location']
                    if val[0] == (':location',):
                        if val[1][0] == (':file',) and val[2][0] == (':position',):
                            fname = val[1][1].obj
                            pos = val[2][1].obj

                            if not all_code.has_key(fname):
                                fin = open(fname, 'rb')
                                code = fin.read()
                                fin.close()
                                line_ranges = jcommon.line_ranges_dict(code)
                                all_code[fname] = line_ranges

                            line_ranges = all_code[fname]
                            line_num, col_num = jcommon.which_line_col(line_ranges, pos)
                            line_num += 1

                            lines.append(">> POS: %s --- (%d) %d, %d" % (fname, pos, line_num, col_num))
                            vim.add_sign(line_num, fname, open_if_not_opened=False, symbol='pietwarning')

        if lines:
            jcommon.lisp_display_info(vim, lines)


def future_info_existence(label):
    base_fname = os.path.join(HOME, 'done/%s' % label)
    return os.path.exists(base_fname+'.info')

def get_future_info(label):
    f_done = 0
    f_ref = ''
    f_time_start = 0.0
    f_time_done = -1
    f_output = ''

    base_fname = os.path.join(HOME, 'done/%s' % label)
    if os.path.exists(base_fname+'.info'):
        fin = open(base_fname + '.info','rb')
        s = fin.read()
        fin.close()
        parts = string.split(s)
        f_ref = parts[0]

    if os.path.exists(base_fname+'.done'):
        f_done = 1
        fin = open(base_fname + '.done','rb')
        f_output = fin.read()
        fin.close()


    if os.path.exists(base_fname+'.time'):
        fin = open(base_fname + '.time','rb')
        s = string.strip(fin.read())
        fin.close()
        if s:
            parts = string.split(s)
            f_time_start = float(parts[0])
            if len(parts)>1:    # this second field shows only if done
                f_time_done = float(parts[1])

    return f_done,  f_ref,  f_time_start,  f_time_done, f_output


# returns future_info, code, start, end
def get_future_data_from_sexp(sexp):
    start = -1
    end = -1
    code_sexp = None
    future_info = {}

    for subexp in sexp:
        if type(subexp.obj) == types.ListType   and   subexp[0] == ('===', ):
            code_sexp = subexp

    if len(sexp)>2:
        start = sexp[1].start
        end = sexp[1].end

        try:
            info = eval(str(sexp[1]))
        except:
            info = []

        if not info:
            info = []

        for tup in info:
            try:
                key, value = tup
                if value is None:
                    value = []

                if key == ('id',):
                    future_info[key] = value
                elif key == ('started',):
                    future_info[key] = value
                elif key == ('jack',):
                    future_info[key] = value
                elif key == ('elapsed',):
                    future_info[key] = value
                elif key == ('history-elapsed', ):
                    future_info[key] = value
            except:
                pass

    return future_info, code_sexp, start, end



def process_future(vim, action='launch'):
    orig_cursor = vim.current.window.cursor

    ancs = vim.find_ancestors()
    lang, _, _, _, _  = jcommon.find_first_lang_spec(ancs)

    if not lang: return

    for anc in ancs:
        sym, block, col, start_row, start_col, end_row, end_col = anc
        if sym == '<<future>>':
            sexp, _s2 = full_parse_sexp(block, 0)

            code_sexp = None
            future_info, code_sexp, start, end = get_future_data_from_sexp(sexp)
            if start == -1 or end == -1:
                continue

            if not future_info.has_key(('history-elapsed',)):
                future_info[('history-elapsed',)] = []


            if future_info.has_key(('id',)):
                label = future_info[('id',)][0]

                if action == 'view':
                    view_future(label)
                    return

                elif action == 'query':
                    f_done, f_ref, f_time_start, f_time_done, f_output = get_future_info(label)
                    if f_done:
                        elapsed = f_time_done - f_time_start

                        output_line_start, output_col, output_line_end = find_out_sexp(vim, ancs[1:])   # dump to __OUT__
                        if output_line_start != -1:
                            vim.current.window.cursor = (output_line_start, output_col)
                            vim.command("normal %")
                            output_line_end, output_col_end = vim.current.window.cursor
                            vim.command("normal %")
                            output_info = (output_line_start, output_col, output_line_end, output_col_end)
                            lines = string.split(jcommon.string_shift_col(f_output, 4, all=1), '\n')    # 4 shifts it a little
                            update_output(vim, output_info, start_row, end_row, '', lines, new_window=0, orig_cursor=orig_cursor, output_indent=4)

                            #future_info[('elapsed',)] = elapsed        #TODO uncomment
                            del future_info[('id',)]    # remove from consideration
                            if future_info.has_key(('history-elapsed',)):
                                hist = future_info[('history-elapsed',)]
                                #hist.append(elapsed)               # TODO uncomment
                            if future_info.has_key(('started',)):
                                del future_info[('started',)]    # remove from consideration

                            clear_future_files(label)
                        else:
                            return
                    else:
                        return


            else:
                if code_sexp and action == 'launch':
                    code = code_sexp[1].obj  # [0] is ('===', )
                    real_line = start_row + code_sexp.line_num + 1
                    label, f_time_start = handle_future(vim, code, lang, real_line)
                    # launch
                    #future_info[('started',)] = time.ctime(f_time_start)   #TODO uncomment
                    future_info[('id',)] = (label,)
                    print "future launched"
                else:
                    return

            its = map(list, future_info.items())    # converts each tup to list
            its.sort()

            zz = string.join(jcommon.pretty_print(struct_to_wrapper(its), 0).buffer, '')

            from hsdl.vim import racket_helper
            zz2 = racket_helper.pprint(zz)

            if sexp.line_num == sexp[1].line_num:
                indent = start_col + sexp.line_col + sexp[1].line_col
            else:
                indent = sexp[1].line_col

            zz2 = jcommon.string_shift_col(zz2, indent)

            block2 = block[:start] + zz2 + block[end:]

            vim.buffer_replace_string(start_row-1, start_col, end_row-1, end_col, block2)

            vim.current.window.cursor = orig_cursor

            return


TYPING_REGION_STR = '(=== '

def clear_out_region(vim):
    orig_cursor = vim.current.window.cursor
    line = vim.current.line
    if string.find(line, TYPING_REGION_STR)<0:          # we're not already on such a line
        find_typing_region(vim, dir=-1)

    ancs = vim.find_ancestors()

    for anc in ancs:
        sym, block, col, start_row, start_col, end_row, end_col = anc
        output_line_start, output_col, output_line_end = find_out_sexp(vim, ancs[1:])   # dump to __OUT__
        if output_line_start != -1:
            vim.current.window.cursor = (output_line_start, output_col)
            vim.command("normal %")
            output_line_end, output_col_end = vim.current.window.cursor
            vim.command("normal %")
            output_info = (output_line_start, output_col, output_line_end, output_col_end)
            update_output(vim, output_info, start_row, end_row, '', ['\n' + (' '*(col+9))  ], new_window=0, orig_cursor=orig_cursor)
            return

    # it's possible you're placed on a line that no longer exists, e.g. after deletion
    try:
        vim.current.window.cursor = orig_cursor
    except:
        pass

def check_sexp(vim):
    reload(jcommon)

    buffer = vim.current.buffer
    lines = buffer[:]
    s = string.join(lines, '\n')
    s2 =  jcommon.rewrite_triple_quotes(s)
    try:
        from hsdl.schemepy import skime
        parser = skime.compiler.parser.Parser("(" + s2 + ")" )
        a = parser.parse()
        print "PASSED"
    except:
        jcommon.dump_exception_new_tab(vim)

def summarize_sexp(vim):
    reload(jcommon)

    buffer = vim.current.buffer
    lines = buffer[:]
    s = string.join(lines, '\n')
    s2 =  jcommon.rewrite_triple_quotes(s)

    try:
        from hsdl.schemepy import skime
        parser = skime.compiler.parser.Parser("(" + s2 + ")" )
        a = parser.parse()
        line_ranges = jcommon.line_ranges_dict(s2)
        sexp = lisp_to_python_main(parser, s, s2, a, [], line_ranges)

        cwd = os.getcwd()
        fullpath = os.path.join(cwd, buffer.name)

        result_lines = []
        for each in sexp:
            if type(each.obj) == types.ListType:
                obj = each.obj
                if type(obj[0].obj) == types.TupleType:
                    name = obj[0].obj[0]
                    result_lines.append(name + '           file://%s#%d' % (fullpath, obj[0].line_num+1))
                    rest = obj[1:]
                    if rest:
                        info = rest[0].obj
                        if type(info) == types.StringType and info[:2] == '@+':
                            result_lines.append('     ' + rest[0].obj)


        if 1:
            if result_lines:
                vim.open_new_tab(general.mklocaltemp() + '.mind')
                new_buffer = vim.current.buffer
                new_buffer[:] = result_lines
                vim.command("set nomodified")

    except:
        jcommon.dump_exception_new_tab(vim)



def exec_command_is_local(fun_name):
    if fun_name.startswith("local/"):
        fun_name = fun_name[6:]

    from hsdl.vim import exec_commands
    reload(exec_commands)
    d = exec_commands.__dict__
    return d.has_key('cmd_' + fun_name)


def call_exec_command(vim, fun_name, sexp):
    fun_name = string.replace(fun_name, '<<', '')
    fun_name = string.replace(fun_name, '>>', '')
    fun_name = 'cmd_' + string.replace(fun_name, '-', '_')

    from hsdl.vim import exec_commands
    reload(exec_commands)
    d = exec_commands.__dict__

    print "<<<<<<<<", fun_name, sexp

    if d.has_key(fun_name):
        fun = d[fun_name]
        apply(fun, [vim, sexp])



def process_sexp(vim):
    import hsdl

    from hsdl.vim import jinteractive
    reload(jinteractive)

    reload(jcommon)

    ancs = vim.find_ancestors()
    print "ancs:", map(lambda tup: tup[0], ancs)
    lang, block, col, _, _  = jcommon.find_first_lang_spec(ancs)
    print "lang:", lang
    cmd, block, col, _, _  = jcommon.find_first_cmd_spec(ancs)
    print "cmd:", cmd

    if not cmd:
        return

    print "COL:", col
    s = (' '*col) + block   # let's preserve the indentation

    lines = jcommon.ignore_special_lines( string.split(s, '\n') )
    orig_num_lines = len(lines)
    lines = jcommon.clean_repeat_lines(lines)
    s = string.join(lines, '\n')
    s = jcommon.clean_future_refs(s)

    s2, shift_dict = jcommon.rewrite_triple_quotes_shifting(s)
    shift_list = shift_dict.items()
    shift_list.sort()

    from hsdl.schemepy import skime

    parser = skime.compiler.parser.Parser(s2)
    a = parser.parse() #skime.compiler.parser.parse(s)

    if 1:
        line_ranges = jcommon.line_ranges_dict(s)                       # our view is still based on the old string; and because the shifting has already set the positions
                                                                        # from the persepctive of the old string; thus, we can calculate line nums and cols now
        sexp = lisp_to_python_main(parser, s, s2, a, shift_list, line_ranges)

        if exec_command_is_local(cmd):
            args = sexp.obj[1:]
            call_exec_command(vim, cmd, sexp)
        else:
            print "VVVVVVVVV:", sexp[0].obj[0], cmd

            sss = cPickle.dumps(sexp)

            open('/tmp/sss.pickle','wb').write(sss)

            reload(jcommon)
            r_pickled = jcommon.sisc_vim_sexp(vim, sss)

            open('/tmp/sss2.pickle','wb').write(r_pickled)

            original_start = sexp.start
            sexp2 = cPickle.loads(r_pickled)


            if type(sexp2.obj) == types.ListType:
                if sexp2.obj[0] == ('command-attached',):
                    action = sexp2.obj[1]
                    fun_name = action[0].obj[0]
                    args = action[1:]

                    call_exec_command(vim, fun_name, sexp2)

                else:
                    b = jcommon.pretty_print(sexp2, first_start=original_start)
                    rr = string.join(b.buffer, '')
                    new_lines = string.split(rr, '\n')
                    line_num = int(vim.eval('line(".")'))
                    vim.insert_lines(new_lines, line_num=line_num)

                    return

                    resp = sexp2.obj
                    fun_name = resp[0].obj[0]
                    call_exec_command(vim, fun_name, sexp2)

                print "="*60
                print sexp2
                print "="*60

    return

    # -----------------------------

    if isinstance(a, Pair):
        if isinstance(a.first, Symbol) and a.first.name == '==vim==':
            rest = a.rest
            if isinstance(rest, Pair) and isinstance(rest.first, Pair):
                if isinstance(rest.first.first, Symbol):
                    name = rest.first.first.name
                    if name[:2] == '<<' and name[-2:] == '>>':
                        fun_name = name[2:-2]
                        lst = rest.first.rest

                        line_ranges = jcommon.line_ranges_dict(s)                       # our view is still based on the old string; and because the shifting has already set the positions
                                                                                        # from the persepctive of the old string; thus, we can calculate line nums and cols now
                        sexp = lisp_to_python_main(parser, s, s2, lst, shift_list, line_ranges)
                        from hsdl.vim import exec_commands
                        reload(exec_commands)
                        d = exec_commands.__dict__
                        if d.has_key(fun_name):
                            fun = d[fun_name]
                            fun(vim, sexp, s, start_row, end_row)

def process_sexp_parent(vim):
    anc = vim.find_ancestors()
    print anc


def get_line_num(pos, line_lens):
    sum = 0
    r = 0
    for the_len in line_lens:
        sum += the_len + 1
        if sum > pos:
            return r
        r += 1
    return -1

def transpose_sexp_generic(vim, dir=1, expect='(', not_expect=')', cmd='['):
    line = vim.current.line
    if line:
        col = int(vim.eval('col(".")'))-1
        c = line[col]
        if c in '()':
            if not c == expect:
                vim.command("normal %")
        else:
            vim.command("normal " + cmd + expect)

        first1 = int(vim.eval('line2byte(line("."))+col(".")')) - 1 - dir
        vim.command("normal %")
        first2 = int(vim.eval('line2byte(line("."))+col(".")')) - 1 - dir

        the_row, the_col = vim.current.window.cursor

        if first1 != first2:
            #print "AAAAAAAAAA:", first1, first2

            if first1 > first2:
                temp = first1
                first1 = first2
                first2 = temp

            s = string.join(vim.current.buffer[:], '\n')
            line_lens = map(len, string.split(s, '\n'))

            the_max = len(s)

            found = 0

            if dir == 1:
                i = first2 + 1  # jump back or ahead one
            else:
                i = first1 - 3  # jump back or ahead one

            while 1:
                c = s[i]

                if c == not_expect:
                    return  # nothing more
                elif c == expect:
                    found = 1
                    break
                if c == '\n':
                    the_row += dir
                    if dir == 1:
                        the_col = 0
                    else:
                        the_col = line_lens[the_row-1]
                else:
                    the_col += dir

                i += dir
                if i < 0 or i > the_max:
                    break

            if the_row < 1:
                return

            if found:

                #print the_row, the_col
                if dir == -1:
                    the_col -= 1

                #print ":LOC:", the_row, the_col
                vim.current.window.cursor = the_row, the_col
                second1 = int(vim.eval('line2byte(line("."))+col(".")')) - 1 - 1
                vim.command("normal %")
                second2 = int(vim.eval('line2byte(line("."))+col(".")')) - 1 - 1

                #print "BBBBBBBBB:", second1, second2

                if second1 > second2:
                    temp = second1
                    second1 = second2
                    second2 = temp

                if second1 != second2:
                    #print "||" + s[second1:second2+1] + "||"

                    all_min = min(first1, second1)
                    all_max = max(first2, second2)

                    line1 = get_line_num(all_min, line_lens)
                    line2 = get_line_num(all_max, line_lens)

                    #print "COMPARE:", first1, first2, second1, second2
                    if dir == 1:
                        old_first = s[first1:first2+1]
                        old_second = s[second1:second2+1]
                        s2 = s[:first1] + old_second + s[first2+1:second1] + old_first + s[second2+1:]
                    elif dir == -1:
                        old_first = s[first1-2:first2-1]
                        old_second = s[second1:second2+1]
                        s2 = s[:second1] + old_first + s[second2+1:first1-2] + old_second + s[first2-1:]

                    parts = string.split(s2, '\n')
                    vim.current.buffer[line1:line2]  = parts[line1:line2]
                    #vim.current.buffer[:] = string.split(s2, '\n')

                    print "LINES::::", line1, line2

def transpose_sexp_after(vim):
    return transpose_sexp_generic(vim, dir=1, expect='(', not_expect=')', cmd='[')

def transpose_sexp_before(vim):
    return transpose_sexp_generic(vim, dir=-1, expect=')', not_expect='(', cmd=']')


def sexp_comment(vim, dir=1, expect='(', not_expect=')', cmd='['):
    line = vim.current.line
    if line:
        col = int(vim.eval('col(".")'))-1
        c = line[col]
        if c in '()':
            if not c == expect:
                vim.command("normal %")
        else:
            vim.command("normal " + cmd + expect)

        line_num = int(vim.eval('line(".")'))-1       # line numbering starts at 1, but indexing starts at 0
        the_line_num, the_col = vim.current.window.cursor
        vim.current.buffer[line_num:line_num] = [' ' * the_col + '; ']
        vim.current.window.cursor = (the_line_num, the_col+2)
        vim.enter_insert_mode()


def sexp_wrap(vim):
    line = vim.current.line
    if line:
        col = int(vim.eval('col(".")'))-1
        c = line[col]
        if c == '(':
            vim.command("normal %")
        elif c == ')':
            pass
        else:
            vim.command("normal [(")
            vim.command("normal %")

        vim.command("normal i)" + chr(27))
        vim.command("normal %")
        vim.command("normal i( " + chr(27))
        vim.enter_insert_mode()


def sexp_extract_completion(vim, row_num, col_num, sexp_info, to_insert='___MATCH___'):
    symbol, buff, col, row1, col1, row2, col2 = sexp_info
    lines = string.split(buff, '\n')
    pos = 0
    for i in xrange(row_num - row1):
        pos += len(lines[i]) + 1
    if row_num - row1 == 0:
        pos += (col_num - col)
    else:
        pos += col_num


    p = string.find(buff, ')', pos)
    if 0: #p>=0:
        r1 = buff[:pos] + ' ' + to_insert + ' )' + buff[p:]
        r2 = buff[:pos] + ' ' + to_insert + ' ... )' + buff[p:]
        return r1, r2
    else:
        r = buff[:pos] + ' ' + to_insert + ' ' + buff[pos:]
        return r, r



def mzscheme_match(vim, code):
    reload(mzscheme_common)
    code = jcommon.rewrite_triple_quotes(code)

    r = mzscheme_common.send_to_mzscheme_matches(vim, "(quasiquote %s)" % code)
    if r == '()':
        return []
    else:
        sexp, _ = full_parse_sexp(r, 0)
        if sexp.obj == [ None ]:        #TODO don't know why None shows up
            return []
        else:
            return sexp.obj

def pre_mzscheme(code):
    code = jcommon.rewrite_triple_quotes(code)
    return "(quasiquote %s)" % code


class SexpThread(threading.Thread):
    def __init__(self, fun):
        threading.Thread.__init__(self)
        self.fun = fun
        self.result = []

    def run(self):
        self.result = self.fun()


def mzscheme_matches(vim, codelist, concise=0):
    reload(mzscheme_common)
    reload(jcommon)

    def fun1():
        return mzscheme_common.send_to_mzscheme_matches(vim, codelist, concise=concise)

    def fun2():
        return string.split(jcommon.sisc_vim_sexp_match(vim, codelist, concise=concise), "`````")

    th1 = SexpThread(fun1)
    th2 = SexpThread(fun2)

    th1.start()
    th2.start()

    th1.join()
    th2.join()

    final1 = []
    for r in th1.result:
        if r == '()':
            final1.append([])
        else:
            sexp, _ = full_parse_sexp(r, 0)
            if sexp.obj == [ None ]:        #TODO don't know why None shows up
                final1.append([])
            else:
                final1.append(sexp.obj)


    final2 = []
    for r in th2.result:
        if r == '()':
            final2.append([])
        else:
            sexp, _ = full_parse_sexp(r, 0)
            if sexp.obj == [ None ]:        #TODO don't know why None shows up
                final2.append([])
            else:
                final2.append(sexp.obj)

    both_final = [final1[0] + final2[0],
                  final1[1] + final2[1]]

                  #final1[2] + final2[2]]

    return both_final



def mzscheme_matches_regular(vim, code, concise=0):
    reload(mzscheme_common)
    reload(jcommon)

    def fun1():
        return mzscheme_common.send_to_mzscheme_matches_regular(vim, code, concise=concise)

    def fun2():
        return string.split(jcommon.sisc_vim_sexp_match_regular(vim, code, concise=concise), "`````")

    th1 = SexpThread(fun1)
    th2 = SexpThread(fun2)

    th1.start()
    th2.start()

    th1.join()
    th2.join()

    print "REGULAR"*10
    print code
    print th1.result
    final1 = []
    for r in th1.result:
        if r == '()':
            continue
        else:
            sexp, _ = full_parse_sexp(r, 0)
            if sexp.obj == [ None ]:        #TODO don't know why None shows up
                continue
            else:
                final1.append(sexp)


    final2 = []
    print th2.result
    for r in th2.result:
        if r == '()':
            continue
        else:
            sexp, _ = full_parse_sexp(r, 0)
            if sexp.obj == [ None ]:        #TODO don't know why None shows up
                continue
            else:
                final2.append(sexp)

    both_final = final1 + final2


    return both_final


def mzscheme_matches_multiple(vim, code, concise=0):
    reload(mzscheme_common)
    reload(jcommon)

    def fun1():
        return mzscheme_common.send_to_mzscheme_matches_multiple(vim, code, concise=concise)

    def fun2():
        return string.split(jcommon.sisc_vim_sexp_match_multiple(vim, code, concise=concise), "`````")

    th1 = SexpThread(fun1)
    th2 = SexpThread(fun2)

    th1.start()
    th2.start()

    th1.join()
    th2.join()

    final1 = []
    print "MULTIPLE"*10
    for r in th1.result:
        if r == '()':
            continue
        else:
            sexp, _ = full_parse_sexp(r, 0)
            if sexp.obj == [ None ]:        #TODO don't know why None shows up
                continue
            else:
                final1.append(sexp)


    final2 = []
    for r in th2.result:
        if r == '()':
            continue
        else:
            sexp, _ = full_parse_sexp(r, 0)
            if sexp.obj == [ None ]:        #TODO don't know why None shows up
                continue
            else:
                print "---------", sexp
                final2.append(sexp)

    both_final = final1 + final2
    return both_final


def sexp_completion(vim, concise=0):
    reload(mzscheme_common)

    cwd = os.getcwd()
    full_path = os.path.join(cwd, vim.current.buffer.name)

    row_num, col_num = vim.current.window.cursor
    ancs = vim.find_ancestors()
    vim.current.window.cursor = row_num, col_num

    all = []

    if ancs:
        ancs.reverse()                  # start with the largest pattern, working down to smallest
        for entry in ancs:
            s1, s2 = sexp_extract_completion(vim, row_num, col_num, entry)
            _, _, _, start_row, start_col, end_row, end_col = entry
            sexp, _ = full_parse_sexp(s1, 0)

            # --- nothing elided
            z = string.join(jcommon.pretty_print(sexp, 0).buffer, '')
            z0 = string.replace(z, '___MATCH___', ',___MATCH___')
            result = mzscheme_matches_regular(vim, pre_mzscheme(z0), concise=concise)
            all += map(lambda each: ('single', each, (s1, (start_row, start_col, end_row, end_col))),  result)

            # --- truncated after the ___MATCH___ symbol, allowing for wildcards afterwards
            z2 = string.replace(z, '___MATCH___', ',___MATCH___ ...')
            result = mzscheme_matches_multiple(vim, pre_mzscheme(z2), concise=concise)
            all += map(lambda each: ('multiple', each, (s1, (start_row, start_col, end_row, end_col))),  result)


    if not all:
        return


    touniq = []

    #for kind, each, (orig, orig_info) in all:
    for entry in all:
        print ">>>>>>>>>>>>>>>>>>>", entry
        kind, each, (orig, orig_info) = entry
        s = string.join(jcommon.pretty_print(each, 0).buffer, '')
        s = string.strip(s)
        if kind == 'multiple':
            s = string.replace(s, '*-*', '')
            s = string.strip(s)[1:-1]               # remove surrounding ()
            s = ' *-* ' + s

        orig_cleaned = s
        #orig_cleaned = string.strip(string.replace(orig_cleaned, '*-*', ''))

        s = string.replace(orig, '___MATCH___', s)
        #s = string.replace(s, '\n', ' ')        #TODO bad simplification!
        touniq.append((kind, s, orig_cleaned, orig_info))

    uniq = general.uniq_list(touniq)

    tosort = []
    for kind, each, orig_cleaned, orig_info in uniq:
        tosort.append((len(each), kind, each, orig_cleaned, orig_info))

    tosort.sort()
    #tosort.reverse()

    shared.SEXP_PATTERN_ON = 1
    shared.SEXP_PATTERN_MODIFIED = 0
    shared.SEXP_PATTERN_PATH = full_path
    shared.SEXP_PATTERN_INDEX = 0
    shared.SEXP_PREVIOUS_SHOW_START = -1
    shared.SEXP_PREVIOUS_SHOW_END = -1

    patterns = []

    i = 1
    final_lines = []
    already_done = {}   # s -> 1
    for size, kind, each, orig_cleaned, orig_info in tosort:
        start_row, start_col, end_row, end_col = orig_info
        choose_line_start = i
        to_display = string.replace(each, '*-*','')
        to_display = mzscheme_common.send_to_mzscheme_pretty_print(vim, to_display)

        # we use the displayed value to determine uniqueness
        if not already_done.has_key(to_display):
            i += len(string.split(to_display, '\n'))
            choose_line_end = i
            final_lines.append(to_display + '\n') # + '           pattern://%s::%d::%d::%d::%d' % (full_path, start_row, start_col, end_row, end_col))
            patterns.append((choose_line_start, choose_line_end-1, full_path, start_row, start_col, end_row, end_col, each, orig_cleaned))
            already_done[to_display] = 1

            i += 1  # empty line separating the matches

    vim.command(":nmap <C-P> :py from hsdl.vim import jinteractive; jinteractive.sexp_popup_previous_helper(vim)<cr>")
    vim.command(":nmap <C-N> :py from hsdl.vim import jinteractive; jinteractive.sexp_popup_next_helper(vim)<cr>")
    vim.command(":nmap <esc> :py from hsdl.vim import jinteractive; jinteractive.sexp_popup_quit(vim)<cr>")

    s = string.join(final_lines, '\n')
    final_lines = string.split(s, '\n')
    vim.open_new_split('/tmp/buffer__patterns.mind', vertical=1, unique=1)

    shared.SEXP_PATTERNS = patterns

    new_buffer = vim.current.buffer
    new_buffer[:] = final_lines
    vim.command("set nomodified")
    #vim.command("setlocal scrolloff=999")

    insert_pattern_match(vim)


def insert_pattern_match(vim):
    opts_pat = re.compile(r'^\s*\*-\*\s+\(\*options\*', re.DOTALL)

    if not shared.SEXP_PATTERN_ON: return

    if not shared.SEXP_PATTERNS: return

    i = shared.SEXP_PATTERN_INDEX

    if 1:
            choose_line_start, choose_line_end, the_path, start_row, start_col, end_row, end_col, to_insert, orig_cleaned = shared.SEXP_PATTERNS[i]


            pat_r = opts_pat.match(orig_cleaned)
            if pat_r: #orig_cleaned[:14] == '*-* (*options*':
                    r = vim.go_to_opened_buffer(the_path)      # if there is one opened
                    curr_line, curr_col = vim.current.window.cursor
                    #print "RRRRRRRRR:", curr_line, curr_col #real_col, start_col, marker_pos, curr_col

                    if shared.SEXP_PATTERN_MODIFIED:
                        vim.command("normal u")

                    reload(mzscheme_common)
                    to_insert2 = mzscheme_common.send_to_mzscheme_pretty_print(vim, orig_cleaned)

                    as_lines = string.split(to_insert2, '\n')
                    as_lines = [as_lines[0]] + map(lambda line: (' '*start_col) + line, as_lines[1:])
                    to_insert3 = string.join(as_lines, '\n')
                    marker_pos = string.find(to_insert3, '*-*')

                    lines_to_check = string.split(to_insert3[:marker_pos], '\n')
                    #print lines_to_check
                    real_row = start_row + len(lines_to_check) - 1      # excludes the first line
                    if len(lines_to_check) >1 :
                        real_col = len(lines_to_check[-1])
                    else:
                        #real_col = marker_pos #TODO  is not correct
                        real_row = curr_line
                        real_col = curr_col #start_col + marker_pos #TODO  is not correct

                    to_insert3 = string.replace(to_insert3, '*-*', '')

                    #to_insert3 = mzscheme_common.send_to_mzscheme_pretty_print(vim, to_insert3)        # this ruins positioning later

                    print ":::::", real_row, real_col

                    vim.current.window.cursor = real_row, real_col #start_row, start_col
                    vim.command("normal J")

                    # -------------
                    from hsdl.schemepy import skime
                    toparse = string.replace(orig_cleaned, '*-*', '')
                    parser = skime.compiler.parser.Parser(toparse)
                    a = parser.parse()
                    sexp = lisp_to_python_main(parser, toparse, toparse, a, [], {})
                    all = []
                    for each in sexp.obj[1:]:               # remember: we're manually going through SexpWrapper objects
                        obj = each.obj
                        if type(obj) == types.StringType:
                            all.append(obj)
                        elif type(obj) == types.TupleType:
                            all.append(obj[0])
                    shared.SEXP_POPUP_LIST = all
                    sexp_popup(vim)

                    shared.SEXP_PATTERN_MODIFIED = 1
            else:
                r = vim.go_to_opened_buffer(the_path)      # if there is one opened
                if r:
                    if shared.SEXP_PATTERN_MODIFIED:
                        vim.command("normal u")

                    reload(mzscheme_common)
                    to_insert2 = mzscheme_common.send_to_mzscheme_pretty_print(vim, to_insert)

                    as_lines = string.split(to_insert2, '\n')
                    as_lines = [as_lines[0]] + map(lambda line: (' '*start_col) + line, as_lines[1:])
                    to_insert3 = string.join(as_lines, '\n')
                    marker_pos = string.find(to_insert3, '*-*')

                    lines_to_check = string.split(to_insert3[:marker_pos], '\n')
                    #print lines_to_check
                    real_row = start_row + len(lines_to_check) - 1      # excludes the first line
                    if len(lines_to_check) >1 :
                        real_col = len(lines_to_check[-1])
                    else:
                        real_col = start_col + marker_pos #TODO  is not correct
                    to_insert3 = string.replace(to_insert3, '*-*', '')

                    #to_insert3 = mzscheme_common.send_to_mzscheme_pretty_print(vim, to_insert3)        # this ruins positioning later

                    vim.buffer_replace_string(start_row-1, start_col, end_row-1, end_col, to_insert3)
                    vim.current.window.cursor = real_row, real_col #start_row, start_col
                    #print "::::::REAL:", real_row, real_col, len(lines_to_check), start_col
                    #vim.command("normal d$")
                    vim.command("normal J")

                    shared.SEXP_PATTERN_MODIFIED = 1

                    if 1:
                        current_path = vim.current.buffer.name
                        vim.open_new_split('/tmp/buffer__patterns.mind', vertical=1, unique=1)
                        selection_window_show_current(vim, choose_line_start, choose_line_end)
                        vim.go_to_opened_buffer(current_path)

                    #vim.command("normal v%")


def insert_pattern_match_previous(vim):
    if not shared.SEXP_PATTERN_ON: return
    i = shared.SEXP_PATTERN_INDEX
    i -= 1
    if i < 0:
        i = len(shared.SEXP_PATTERNS)-1
    shared.SEXP_PATTERN_INDEX = i

    insert_pattern_match(vim)

def insert_pattern_match_next(vim):
    if not shared.SEXP_PATTERN_ON: return
    i = shared.SEXP_PATTERN_INDEX
    size = len(shared.SEXP_PATTERNS)
    i += 1
    if i >= size :
        i = 0
    shared.SEXP_PATTERN_INDEX = i

    insert_pattern_match(vim)


def au_CursorMoved(vim):
    tab = shared.RACKET_TABLE
    if not tab: return

    block = shared.RACKET_BLOCK
    pad = shared.RACKET_PAD

    line, col = vim.current.window.cursor

    cur_pos = int(vim.eval('line2byte(line("."))+col(".")')) - pad

    for start_pos, end_pos, the_line, the_col, the_type in tab:
        #if the_line == line and the_col == col:
        if (cur_pos >= start_pos) and (cur_pos < end_pos):
            data = block[start_pos:end_pos]
            print ":::", cur_pos, pad, start_pos, end_pos, the_type, repr(data[:40])
            break

    return
    if shared.SEXP_PATTERN_ON:
        c_command_emulate(vim, 'close_errors')
        print "????"

def exit_mode(vim):
    from hsdl.vim import jcommon
    reload(jcommon)
    vim.sign_clear()
    shared.RACKET_TABLE = []

def au_InsertEnter(vim):
    if shared.SEXP_PATTERN_ON:
        sexp_popup_quit(vim)
        #c_command_emulate(vim, 'close_errors')



def sexp_popup(vim):
    shared.SEXP_PUM_ON = 1

    vim.enter_insert_mode()
    vim.command(":imap <CR> <esc>:silent! py from hsdl.vim import jinteractive; jinteractive.sexp_popup_post(vim)<cr>")
    #vim.command(":inoremap <Down> <C-R>:silent! py from hsdl.vim import jinteractive; jinteractive.sexp_popup_previous(vim)<cr>")
    #vim.command(":inoremap <Up> <C-R>:silent! py from hsdl.vim import jinteractive; jinteractive.sexp_popup_next(vim)<cr>")
    #vim.command(':inoremap <expr> <C-E>=pumvisible() ? "<C-N>" : "<Down>"<CR>')
                #py from hsdl.vim import jinteractive; jinteractive.sexp_popup_next_helper(vim)<cr>")
    #vim.command(':inoremap <expr> <C-Y>=pumvisible() ? "<C-P>" : "<Up>"<CR>')
    #vim.command(":inoremap <expr> <C-Y>=py from hsdl.vim import jinteractive; jinteractive.sexp_popup_previous_helper(vim)<cr>")
    #vim.command(':inoremap <Down> <C-R>=pumvisible() ? "\<lt>C-N>" : "\<lt>Down>"<CR>')
    #vim.command(':inoremap <expr> <C-E>  :py asdasd()')
    #vim.command(':inoremap <expr> <C-Y>  :py asdasd()')
    vim.command(':call feedkeys("\\<C-X>\\<C-U>")')

def sexp_popup_next_helper(vim):
    if shared.SEXP_PATTERN_ON:
        return insert_pattern_match_next(vim)

def sexp_popup_previous_helper(vim):
    if shared.SEXP_PATTERN_ON:
        return insert_pattern_match_previous(vim)

def sexp_popup_post(vim):
    if 1: #if vim.eval("pumvisible()") == "1":
        vim.command(":iunmap <CR>")
        #vim.command(":iunmap <C-N>")
        #vim.command(":iunmap <C-P>")


def sexp_popup_quit(vim):
    vim.command(":nunmap <esc>")
    vim.command(":nunmap <C-N>")
    vim.command(":nunmap <C-P>")


def selection_window_show_current(vim, start_line, end_line):
    if shared.SEXP_PREVIOUS_SHOW_START != -1:
        first = shared.SEXP_PREVIOUS_SHOW_START
        last = shared.SEXP_PREVIOUS_SHOW_END

        lines = vim.current.buffer[first-1:last]
        lines = map(lambda line: line[4:], lines)   # delete the first 4 chars
        vim.current.buffer[first-1:last] = lines
        vim.command("set nomodified")

    if start_line != -1:
        vim.command("normal " + str(start_line) + "G")
        lines = vim.current.buffer[start_line-1:end_line]
        lines = map(lambda line: "!!! " + line, lines)
        vim.current.buffer[start_line-1:end_line] = lines
        vim.command("set nomodified")

        shared.SEXP_PREVIOUS_SHOW_START = start_line
        shared.SEXP_PREVIOUS_SHOW_END = end_line


def find_typing_region(vim, dir=1, move_cursor=1):
    buff = vim.current.buffer
    line = vim.current.line
    p = string.find(line, TYPING_REGION_STR)
    if p >= 0:
        col = int(vim.eval('col(".")'))-1
        if (dir == 1 and p>col) or (dir == -1 and p<(col-1)):   # (col-1) so that we can jump outside of the current region
            i = int(vim.eval('line(".")'))-1
            if move_cursor:
                vim.current.window.cursor = i+1, p+1        # p+1 so that we are not on the '('
                return i+1, p+1
            else:
                return i+1, p                               # when cursor is not moved, pos should be on the '('

            return

    max = len(buff)-1
    i = int(vim.eval('line(".")'))-1
    found = 0
    p = -1

    while 1:
        i += dir
        if i<0 or i>=max:
            break

        line = buff[i]
        p = string.find(line, TYPING_REGION_STR)
        if p >= 0:
            found = 1
            break

    if found:
        if move_cursor:
            vim.current.window.cursor = i+1, p+1        # p+1 so that we are not on the '('
            return i+1, p+1
        else:
            return i+1, p                               # when cursor is not moved, pos should be on the '('
    else:
        return ()


def find_lang_region(vim, dir=1):
    pat = re.compile(r'\(==[a-zA-Z0-9_-]+==')
    buff = vim.current.buffer
    max = len(buff)-1
    i = int(vim.eval('line(".")'))-1
    found = 0
    p = -1

    while 1:
        i += dir
        if i<0 or i>=max:
            break
        line = buff[i]
        r = pat.search(line)
        if r:
            p = r.start()
            if p >= 0:
                found = 1
                break

    if found:
        vim.current.window.cursor = i+1, p+1

def find_out_region(vim, dir=1):
    pat = re.compile(r'\(__OUT__')
    buff = vim.current.buffer
    max = len(buff)-1
    i = int(vim.eval('line(".")'))-1
    found = 0
    p = -1

    while 1:
        i += dir
        if i<0 or i>=max:
            break
        line = buff[i]
        r = pat.search(line)
        if r:
            p = r.start()
            if p >= 0:
                found = 1
                break

    if found:
        return i+1, p
    else:
        return -1, -1


def find_section_marker(vim, dir=1):
    pat = re.compile(r'@@(@?) ')
    buff = vim.current.buffer
    line = vim.current.line
    r = pat.search(line)
    if r:
        p = r.start()
        col = int(vim.eval('col(".")'))-1
        print p, col
        if (dir == 1 and p>col) or (dir == -1 and p<(col-1)):   # (col-1) so that we can jump outside of the current region
            i = int(vim.eval('line(".")'))-1
            vim.current.window.cursor = i+1, p+1        # p+1 so that we are not on the '('
            return


    max = len(buff)-1
    i = int(vim.eval('line(".")'))-1
    found = 0
    p = -1

    while 1:
        i += dir
        if i<0 or i>=max:
            break
        line = buff[i]
        r = pat.search(line)
        if r:
            p = r.start()
            if p >= 0:
                found = 1
                break

    if found:
        vim.current.window.cursor = i+1, p+1


ACTION_MARKER_STR = '(_action_ '

# returns the cur that begins the sexp
def find_action_marker(vim, dir=1, move_cursor=1):
    buff = vim.current.buffer
    line = vim.current.line
    p = string.find(line, ACTION_MARKER_STR)
    if p >= 0:
        col = int(vim.eval('col(".")'))-1
        if (dir == 1 and p>col) or (dir == -1 and p<(col-1)):   # (col-1) so that we can jump outside of the current region
            i = int(vim.eval('line(".")'))-1
            vim.current.window.cursor = i+1, p                  # unlike other finds, we want to be on the '('
            return i+1, p

    max = len(buff)-1
    i = int(vim.eval('line(".")'))-1
    found = 0
    p = -1

    while 1:
        i += dir
        if i<0 or i>=max:
            break

        line = buff[i]
        p = string.find(line, ACTION_MARKER_STR)
        if p >= 0:
            found = 1
            break

    if found:
        if move_cursor:
            vim.current.window.cursor = i+1, p          # unlike other finds, we want to be on the '('
        return i+1, p
    else:
        return ()



# returns: the code, the cur that begins the sexp, and the ending cur
def find_action_marker_complete(vim, dir=1, move_cursor=1):
    orig_cur = vim.current.window.cursor

    start_cur = find_action_marker(vim, dir=dir, move_cursor=move_cursor)
    vim.current.window.cursor = start_cur

    code, end_cur = jcommon.get_matched_region_with_pos(vim)

    vim.current.window.cursor = orig_cur

    return code, start_cur, end_cur



BASIC_SEXPR_MARKER_STR = '('

def find_basic_sexpr_marker(vim, dir=1, move_cursor=1):
    buff = vim.current.buffer
    line = vim.current.line
    _, curr_col = vim.current.window.cursor
    line = line[:curr_col]
    print "::::::::" + line + ":::::::"
    p = string.rfind(line, BASIC_SEXPR_MARKER_STR)
    if p >= 0:
        col = int(vim.eval('col(".")'))-1
        if (dir == 1 and p>col) or (dir == -1 and p<col):   # (col-1) so that we can jump outside of the current region
            i = int(vim.eval('line(".")'))
            vim.current.window.cursor = i, p                  # unlike other finds, we want to be on the '('
            return i, p

    max = len(buff)-1
    i = int(vim.eval('line(".")'))-1
    found = 0
    p = -1

    while 1:
        i += dir
        if i<0 or i>=max:
            break

        line = buff[i]
        p = string.find(line, BASIC_SEXPR_MARKER_STR)
        if p >= 0:
            found = 1
            break

    if found:
        if move_cursor:
            vim.current.window.cursor = i+1, p          # unlike other finds, we want to be on the '('
        return i+1, p
    else:
        return ()

# trimmed means that the end pieces are ignored
def highlight_triple_quoted_region(vim, trimmed=0):
    buff = vim.current.buffer
    the_max = len(buff)-1
    start = int(vim.eval('line(".")'))-1
    found = 0

    i = start

    # --- go forward
    while i>-1:
        i -= 1
        line = buff[i]
        p = string.find(line, '"""')
        if p>=0:
            if trimmed:
                start_line = i+1
                start_col = 0
            else:
                start_line = i
                start_col = p+3
            found = 1
            break

    if found:
        found = 0

        i = start
        # --- go forward
        while i<the_max:
            i += 1
            line = buff[i]
            p = string.find(line, '"""')
            if p>=0:
                if trimmed:
                    end_line = i-1
                    end_col = len(buff[i-1])-1
                else:
                    end_line = i
                    end_col = p
                found = 1
                break


        if found:
            vim.current.window.cursor = start_line+1, start_col
            vim.command("normal v")
            vim.current.window.cursor = end_line+1, max(0, end_col-1)   # CAREFUL: seg fault if col is -1


def new_typing_region(vim, dir=1):
    buff = vim.current.buffer
    ancs = vim.find_ancestors()
    if ancs:
        found = 0

        for sym, buff, col, row1, col1, row2, col2 in ancs:
            if sym == '===':
                found = 1
                vim.current.buffer[row2:row2] = [' '*col + '(=== """  ',
                                                 ' '*col + '    """)']
                vim.current.window.cursor = row2+1, col + 8

        if not found:
            _, _, col, _, _, _, _ = ancs[0]

            line = int(vim.eval('line(".")'))-1
            col += 2    # we base our indentation off the first ancestor's indentation
            vim.current.buffer[line:line] = [' '*col + '(=== """  ',
                                             ' '*col + '    """)']
            vim.current.window.cursor = line+1, col + 8

        vim.enter_insert_mode()


snip_var_pat = re.compile(r'\${(?P<id>[a-zA-Z0-9_/]+)(:(?P<default>[^}]+))?}')

# returns the value; returns None on failure
def snippets_get_closest_name(bindings, id, default=()):
    name = jcommon.snippet_canonical_name(id)
    if bindings.has_key(name):
        return name
    else:
        for (the_sorter, the_name), value in bindings.items():
            if the_name == id:
                return (the_sorter, the_name)

    return default


def snippets_update_template(vim, curr_name, full=0, as_string=0, text_editor_fun=None):
    buffer = vim.current.buffer
    orig_line = shared.snip_start_line

    template = shared.snip_template
    bindings = shared.snip_bindings

    to_return = (-1, -1)

    if as_string:
        full = 1

    full_final = []

    many_line_amends = []    # list of (line_num, col, val)

    for i in xrange(len(template)):
        line = template[i]
        old_line = line

        line_amends = []

        cum_diff = 0

        while 1:

            r = snip_var_pat.search(line)
            if r:
                id = r.group('id')
                the_name = snippets_get_closest_name(bindings, id)
                default = r.group('default')
                start = r.start()
                end = r.end()
                width = end - start
                if bindings.has_key(the_name):
                    val = bindings[the_name]
                else:
                    val = ''

                diff = len(val) - width
                line_amends.append((start, diff, cum_diff, val))
                cum_diff += diff

                line = line[:start] + val + line[end:]
                if not default is None:
                    if the_name == curr_name:
                        to_return = (i, start)

            else:
                break

        if line_amends:
            many_line_amends.append((i, line_amends, line))

        if full:
            full_final.append(line)
        else:
            if line != old_line:
                real_line = orig_line + i
                #vim.command("call setline(%d,'%s')" % (real_line, line))
                if text_editor_fun:
                    pass    # do it when all data are collected (below)
                else:
                    buffer[real_line-1:real_line] = [line]

    if text_editor_fun:
        text_editor_fun(many_line_amends)

    if as_string:
        return to_return,  full_final

    elif full:
        buffer[orig_line-1:orig_line] = full_final
        vim.command("set nomodified")

    return to_return


def snippets_cursor_moved(vim):
    if shared.snip_on and not shared.snip_start_col is None:

        from hsdl.vim import vim_emulator_jtext
        is_jtext = isinstance(vim, vim_emulator_jtext.VimEmulatorJText)

        line = vim.current.line
        curr_name = shared.snip_curr_name

        curr_line, curr_col = vim.current.window.cursor
        new_frag = line[shared.snip_start_col:curr_col]

        if shared.snip_do_update    and    curr_name in shared.snip_bindings:
            old_frag = shared.snip_bindings[curr_name]
            shared.snip_bindings[curr_name] = new_frag

            start_line = shared.snip_start_line

            if is_jtext:
                doc = vim.doc
                from hsdl.embedit import style
                buffer = vim.current.buffer

                def text_editor_fun(many_amends):
                    for rel_line, amends, new_line in many_amends:
                        line_pos = vim.getOffsetAtLine(rel_line + start_line)

                        if 0:
                            for col_num, diff, cum_diff, new_text in amends:
                                if new_text == new_frag:    # ignore hilighting other variables
                                    pos = line_pos + col_num
                                    doc.setCharacterAttributes(pos, len(old_frag), style.blackAttrSet, False)

                        buffer[rel_line + start_line-1] = new_line

                        for col_num, diff, cum_diff, new_text in amends:
                            if new_text == new_frag:    # ignore hilighting other variables
                                pos = line_pos + col_num
                                doc.setCharacterAttributes(pos, len(new_text), style.snippetTextAttrSet, False)
                            else:
                                pos = line_pos + col_num
                                doc.setCharacterAttributes(pos, len(new_text), style.blueAttrSet, False)

                snippets_update_template(vim, curr_name, text_editor_fun=text_editor_fun)

            else:
                snippets_update_template(vim, curr_name, text_editor_fun=None)

            vim.current.window.cursor = curr_line, curr_col
        else:
            pass

        shared.snip_prefix = None   # invalidate the prefix

        reload(jcommon)
        jcommon.update_interactive_completer(vim, new_frag)


def snippets_jump(vim, dir=1):
    curr_name = shared.snip_curr_name
    bindings = shared.snip_bindings

    curr_name = jcommon.snippet_next_name(vim, dir=dir)
    if curr_name == ():         # there are no variables
        vim.enter_insert_mode()
        return

    shared.snip_curr_name = curr_name
    start_line = shared.snip_start_line


    from hsdl.vim import vim_emulator_jtext
    is_jtext = isinstance(vim, vim_emulator_jtext.VimEmulatorJText)

    next_line, next_col = snippets_update_template(vim, curr_name)

    if is_jtext:        # clear out styles in the mean time
        doc = vim.doc
        from hsdl.embedit import style
        size = vim.ed.getTextSize()
        doc.setCharacterAttributes(0, size, style.regularTextAttrSet, False)

    if next_line != -1:
        next_line += start_line
        vim.current.window.cursor = next_line, next_col
        vim.command("normal v")
        vim.current.window.cursor = next_line, next_col + len(bindings[curr_name])
        vim.command(':call feedkeys("\\<C-G>")')
        shared.snip_start_col = next_col
    else:
        print "Unable to find:", curr_name

    shared.snip_curr_width = len(bindings[curr_name])



def snippets_exit(vim):
    if shared.snip_on:
        shared.snip_on = 0
        old_line, old_cur = vim.current.window.cursor

        if shared.snip_do_update:
            all = vim.current.buffer[:]
            #jcommon.end_undo_block(vim)
            if shared.snip_path:
                r = vim.go_to_opened_buffer(shared.snip_path)
                if r:
                    buffer = vim.current.buffer
                    all = jcommon.dedent_lines_common(all)
                    buffer[shared.snip_orig_line-1:shared.snip_orig_line] = all
                    #snippets_update_template(vim, 0, full=1)        # 0 doesn't matter; we don't use it

                    c_command_emulate(vim, 'close_errors')

                    reload(jcommon)
                    r = vim.find_buffer_name_containing('COMPLETER')
                    if r:
                        vim.command(":silent q! ")

                    try:
                        vim.current.window.cursor = old_line + shared.snip_orig_line -1,  old_cur+1
                    except:
                        pass    # may go out of buffer  # TODO

                    buffer = vim.current.buffer
            else:
                c_command_emulate(vim, 'close_errors')
                vim.command(":silent q! ")
                print "Cannot find a named buffer to save to"
        else:
            reload(jcommon)
            r = vim.find_buffer_name_containing('COMPLETER')
            if r:
                vim.command(":silent q! ")



def show_action_menu(vim):
    reload(jcommon)

    all = jcommon.find_lisp_actions(vim)
    all.sort()

    if 0:
        shared.SEXP_POPUP_LIST = all
        sexp_popup(vim)
    else:
        path = vim.current.buffer.name
        tempfname = general.local_hsdl_mktemp('INF__') + '.mind'
        vim.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__', size=50)     # if another already exists within the sa
        buffer = vim.current.buffer
        buffer[:] = all
        vim.command("set nomodified")

        vim.go_to_opened_buffer(path)  # go back


def interactive_completion(vim):
    reload(jcommon)
    jcommon.start_interactive_completion(vim)

def interactive_completion_select_up(vim):
    if shared.INTERACT_ENABLE_SELECT:
        line = vim.current.line
        curr_line, curr_col = vim.current.window.cursor
        frag = line[shared.snip_start_col:curr_col+1]
        if shared.snip_prefix is None:
            shared.snip_prefix = frag
        vim.command(':call feedkeys("l")')
        vim.enter_insert_mode()
        jcommon.update_interactive_completer(vim, frag, choice_dir=-1, use_choice=1)

def interactive_completion_select_down(vim):
    if shared.INTERACT_ENABLE_SELECT:
        line = vim.current.line
        curr_line, curr_col = vim.current.window.cursor
        frag = line[shared.snip_start_col:curr_col+1]
        if shared.snip_prefix is None:
            shared.snip_prefix = frag
        vim.command(':call feedkeys("l")')
        vim.enter_insert_mode()
        jcommon.update_interactive_completer(vim, frag, choice_dir=1, use_choice=1)



def auto_run_action(vim, debug=0):
    reload(jcommon)

    reload(vim_commands)
    jcommon.prepare_debug(vim, debug)
    eligible_actions = vim_commands.action_completer(vim, "", ["action"])
    send_h_command(vim, "action *")
    jcommon.prepare_debug(vim, 0)

    return

    orig_cur = vim.current.window.cursor
    find_action_marker(vim, dir=-1)
    new_cur = vim.current.window.cursor
    if new_cur != orig_cur:
        code = jcommon.get_matched_region(vim)
        vim.current.window.cursor = orig_cur
        if code:
            sexp, _ = full_parse_sexp(code, 0)
            if len(sexp) == 3:
                action = sexp[1].obj[0]
                if action in eligible_actions:
                    send_h_command(vim, "action " + action)
                else:
                    print "action '%s' does not apply; use H action <tab> to find eligible actions" % action


def fast_execute(vim, lang=''):
    reload(jcommon)
    orig_cur = vim.current.window.cursor

    try:
        find_typing_region(vim, dir=-1, move_cursor=1)
        vimcallj(vim, catch_exception=0, lang=lang)
        vim.current.window.cursor = orig_cur
    except:
        vim.current.window.cursor = orig_cur
        jcommon.dump_exception_new_tab(vim)


def fast_show_data(vim):
    reload(jcommon)
    orig_cur = vim.current.window.cursor

    try:
        find_typing_region(vim, dir=-1, move_cursor=1)
        sisc_show_data(vim)
        vim.current.window.cursor = orig_cur
    except:
        vim.current.window.cursor = orig_cur
        jcommon.dump_exception_new_tab(vim)



def keep_parsing(sexp_str):
    from hsdl.cl import genlisp
    new_sexp_str = sexp_str[1:-1]   # remove the surrounding parens
    final = []
    r = genlisp.apply_ecl("keep-parsing", [new_sexp_str])
    last = 0
    for end, code in r:
        #final.append( ((last, end), code.strip()) )
        final.append( ((last, end), new_sexp_str[last:end]) )
        last = end

    if 0:
        print r
        print "@@@@@@@@@@@@", final
        for (start, end), code in final:
            print "------" + code + "------"
    return final

def move_out_of_double_quote(line, pos):
    beginning = line[:pos]
    num_dquotes = string.count(beginning, '"')
    if num_dquotes % 2 == 0:
        return pos
    else:
        return string.rfind(beginning, '"')



def quicktest(vim):
    reload(jcommon)
    line = vim.current.line
    col = int(vim.eval('col(".")'))-1
    word = jcommon.find_word(line, col)
    word = [c for c in word if c in string.letters + string.digits + '_-@']
    word = string.join(word, '')


    found = []

    pat1 = re.compile(r'{{\s*' + word)
    paths = glob.glob(general.interpolate_filename('${fm}/comps/*.erl'))
    for path in paths:
        i = 0
        fin = open(path, 'rb')
        while 1:
            line = fin.readline()
            if not line: break
            i += 1
            r = pat1.search(line)
            if r:
                found.append((path, i, string.strip(line)))
        fin.close()

    pat2 = re.compile(r'`#\(\s*#\(\s*' + word)
    pat3 = re.compile(r'\(\s*\(\s*tuple\s+' + word)
    paths = glob.glob(general.interpolate_filename('${fm}/comps/*.lfe'))
    for path in paths:
        i = 0
        fin = open(path, 'rb')
        while 1:
            line = fin.readline()
            if not line: break
            i += 1
            r = pat2.search(line)
            if not r:
                r = pat3.search(line)

            if r:
                found.append((path, i, string.strip(line)))
        fin.close()


    result_lines = []
    for path, i, line in found:
        _, base = os.path.split(path)
        result_lines.append(base)
        result_lines.append('    ' + line + '      file://' + path + '#' + str(i))
        result_lines.append('')

    vim.open_new_tab(general.mklocaltemp() + '.mind')
    new_buffer = vim.current.buffer
    new_buffer[:] = result_lines
    vim.command("set nomodified")


# ================================================
# ----- called when vim first loads --------------
# ================================================
def mind_opened(vim):
    from hsdl.vim import jcommon
    reload(jcommon)

    jcommon.parse_header_commands(vim)
    return

    print "This happens many times"
    print "OPENED", random.random()
    curr_path = vim.current.buffer.name
    if not curr_path:
        return

    first_line = vim.current.buffer[0]
    one_opened = 0

    if first_line and first_line[:3] == '+++' and first_line[-3:] == '+++':
        core = first_line[3:-3]
        files = string.split(core)
        cwd = os.getcwd()
        for fname in files:
            full = os.path.join(cwd, fname)
            if os.path.exists(full):
                if not vim.check_already_exists(full):
                    vim.open_new_tab(full)
                    one_opened = 1
    if one_opened:
        # bring back original
        #vim.go_to_opened_buffer(curr_path)
        pass


def mind_closed(vim):
    curr_path = vim.current.buffer.name
    if not curr_path:
        return

    from hsdl.vim import shared
    main_link = jcommon.is_part_of_linkage(curr_path)
    if main_link:
        jcommon.remove_from_linkage(curr_path)
        print "This file is part of linkage", main_link

    if curr_path in shared.LINKAGE:
        del shared.LINKAGE[curr_path]

def initialize_environment(vim):
    return
    G = globals()

    def output(s):
        if shared.VIM_OUTPUT_PATH:
            path = shared.VIM_OUTPUT_PATH
            print "PRINTING TO:", path
            fout = open(path, 'wb')
            fout.write(s)
            fout.close()

    G['output'] = output

    if shared.VIM_OUTPUT_PATH:
        j_code = """
        VIM_OUTPUT_PATH=: '%s'
        vim_output=: writeall&'%s'

        """ % (shared.VIM_OUTPUT_PATH, shared.VIM_OUTPUT_PATH)
    else:
        j_code = """
        VIM_OUTPUT_PATH=: ''
        vim_output=: ]
        """

    jcommon.callj(vim, j_code)


def initialize_open_handlers(vim):
    import vim_commands_typescript
    shared.open_handlers.append(vim_commands_typescript.open_handler)

def initialize(vim):
    initialize_open_handlers(vim)

    if 0:
        # racket startup CANNOT occur within a thread
        from hsdl.racket import racket
        racket.start()

    if 0:
        from hsdl.cl import genlisp
        genlisp.start_lisp()
        genlisp.prepare()
        genlisp.vim_prepare()
        genlisp.eval_ecl('(load "/tech/hsdl/lib/lisp/hsdl/sexp-processing.lisp")')


    vim.command("delmarks <")
    vim.command("delmarks >")

    path = vim.current.buffer.name
    if path:
        _, ext = os.path.splitext(path)
        if ext in ['.mind']:
            def fun():
                pass
                #from hsdl.racket import racket
                #racket.start()
                #time.sleep(10)
                #print "DONE SLEEPING"
                #shared.THREAD.join()

            from hsdl.vim import shared
            if not shared.THREAD:
                shared.THREAD = FunThread(fun)
            shared.THREAD.start()

    return

    from hsdl.cl import genlisp, shared
    genlisp.start_lisp()
    genlisp.prepare()
    genlisp.vim_prepare()


def initialize_after_first_load(vim):
    # call this only once
    if not shared.INITALIZE_AFTER_FIRST_LOAD_DONE:
        shared.INITALIZE_AFTER_FIRST_LOAD_DONE = 1

        if os.environ.has_key('VIM_START_POS'):
            pos_str = os.environ['VIM_START_POS']
            if pos_str:
                try:
                    pos = eval(pos_str)
                    vim.current.window.cursor = pos
                    jcommon.vim_command(vim, 'set nofoldenable')
                except:
                    pass

        if os.environ.has_key('VIM_OUTPUT_PATH'):
            shared.VIM_OUTPUT_PATH = os.environ['VIM_OUTPUT_PATH']

        if os.environ.has_key('EXTERNAL_EDITOR_OUTPUT_PATH'):
            vim.set_register('@', '')
            shared.EXTERNAL_EDITOR_OUTPUT_PATH = os.environ['EXTERNAL_EDITOR_OUTPUT_PATH']

        initialize_environment(vim)

def redraw_screen(vim):
    vim.command("redraw!")

def enter_h(vim):
    #vim.insert_lines([chr(171)])
    vim.command(':call feedkeys(":H ")')


def command_on_other_buffer(vim, cmd=''):
    if cmd:
        curr_path = vim.current.buffer.name
        from hsdl.vim import jcommon
        reload(jcommon)
        r = vim.find_buffer_name_containing('__', curr_tab_only=1)
        if r:
            vim.command(cmd)
            vim.go_to_opened_buffer(curr_path)


def execute_support_code_sections(vim, path, s, results, env):
    orig_cursor = vim.current.window.cursor
    pat = re.compile(r'\(==(?P<language>[a-zA-Z0-9_-]+)==\s+"<:::\s*(?P<identifier>[^": ]+)\s*:::>"\s+\(\s*===\s+"""(?P<code>.+?)"""\s*\)\s*\)', re.DOTALL)
    i = 0
    while 1:
        r = pat.search(s, i)
        if r:
            i = r.end()

            language = string.strip(r.group('language'))
            ident = r.group('identifier')
            code = r.group('code')
            body_lines = [line for line in string.split(code, '\n') if string.strip(line)]

            res = []

            if language  == 'python':
                fun = general.create_function(['vim'], body_lines, env)
                if fun:
                    res = fun(vim)

            elif language == 'j':
                from hsdl.j import jlib
                jlib.jset("VIMPATH", path)
                res = jlib.jeval(code)

            elif language == 'rkt':
                from hsdl.vim import racket_helper
                res = racket_helper.racket_eval(code)

            elif language in ['erl', 'lfe']:

                if language == 'erl':
                    remote_args = ['servers.eval:eval_erl', code, 0, "the_lfe_service"]
                else:
                    remote_args = ['servers.eval:eval_lfe', code, 0, "the_lfe_service"]

                    if shared.ALWAYS_CHECK_PS:
                        from hsdl.vim import vim_commands_lfe
                        reload(vim_commands_lfe)
                        vim_commands_lfe.lfe_start()

                try:
                    status, s = jcommon.send_action_franca_nonblocking('erl', remote_args, port=16020, machine='worlddb')
                except:
                    vim.current.window.cursor = orig_cursor
                    print "Socket call terminated"
                    return

                if status == "error":
                    res = string.split("+++++++++++ EXCEPTION +++++++++\n" + s, '\n') + ['']
                else:
                    res = string.split(s, '\n') + ['']

            if res and type(res) in [types.ListType, types.TupleType]:
                results[ident] = [str(line) for line in res]
        else:
            break

# switches to the buffer named by the path, then executes code
def execute_support_buffer(vim, path, results, env):
    r = vim.go_to_opened_buffer(path)
    if r:
        s = string.join(vim.current.buffer[:], jcommon.LINE_DELIMITER)
        try:
            execute_support_code_sections(vim, path, s, results, env)
        except:
            buff = cStringIO.StringIO()
            traceback.print_exc(file=buff)
            print "*"*80
            print " Error in file:", path
            print "*"*80
            print buff.getvalue()
            print "*"*80

def execute_support(vim, paths, original_path):
    env = general.create_basic_env("time random os time sys string traceback re types urllib cStringIO threading glob cPickle thread uuid".split())

    results = {}
    for path in paths:
        execute_support_buffer(vim, path, results, env)

    return results

def autoload_open_files(vim, paths):
    opened_paths = {}

    m = vim.get_opened_buffer_map()
    for _, curr_paths in m.items():
        for curr_path  in curr_paths:
            opened_paths[curr_path] = 1

    for path in paths:
        if not path in opened_paths:
            vim.command(":silent tabnew " + path)


def autoload_files(vim, original_path, paths):
    shared.MARK_BUFFER_SWITCH = 0

    autoload_open_files(vim, paths)

    results = execute_support(vim, paths, original_path)
    vim.go_to_opened_buffer(original_path)
    s = string.join(vim.current.buffer[:], jcommon.LINE_DELIMITER)

    idents = results.keys()
    idents.sort()
    for ident in idents:
        pat = '<::: %s :::>' % ident
        lines = results[ident]
        s = jcommon.interpolate_string_indented(s, pat, lines)
    vim.current.buffer[:] = string.split(s, jcommon.LINE_DELIMITER)
    vim.command(":set nomodified")
    shared.MARK_BUFFER_SWITCH = 1


# .mind file has been started; see if we need to autoload other files
def check_autoload(vim, force=0, immediate=0):
    # Not sure if we want autoloads, which may make changes to the primary file when
    # code blocks get executed.
    if 0:
        reload(jcommon)
        vim = jcommon.build_vim(vim)

        s = vim.getText() #"\n".join(vim.current.buffer[:])
        if s.find('VIMAUTOLOAD::')>=0:
            do_autoload(vim)

    return

    path = vim.current.buffer.name

    if force or shared.AUTOLOAD_ON: #   and   not path in shared.AUTOLOAD_DONE):
        subs = glob.glob(path + '._.*')
        if subs:
            pass #print "*** AUTOLOAD ***"

def do_autoload(vim):
    path = vim.current.buffer.name
    subs = jcommon.get_autoload_support_files(path)
    #do_rackload(vim)
    autoload_files(vim, path, subs)


def find_autoload_code(vim, ident):
    pat = re.compile(r'"<:::\s*(?P<ident>[a-zA-Z0-9_]+)\s*:::>"')

    path = vim.current.buffer.name
    paths = jcommon.get_autoload_support_files(path)
    autoload_open_files(vim, paths)  # make sure all supporting files are in place

    shared.MARK_BUFFER_SWITCH = 0

    for path in paths:
        r = vim.go_to_opened_buffer(path)
        stop = 0
        if r:
            line_num = 1
            lines = vim.current.buffer[:]
            for line in lines:
                r2 = pat.search(line)
                if r2:
                    if r2.group('ident') == ident:
                        vim.current.window.cursor = (line_num, r2.start()+1)  # move to it
                        stop = 1
                        break
                line_num += 1

        if stop:
            break

    shared.MARK_BUFFER_SWITCH = 1

# ============================================

def get_rackload_files(vim):
    original_path = vim.current.buffer.name
    paths = jcommon.get_autoload_support_files(original_path)

    shared.MARK_BUFFER_SWITCH = 0

    autoload_open_files(vim, paths)     # opens the files

    results = execute_support(vim, paths, original_path)

    all_code = []

    for path in paths:
        r = vim.go_to_opened_buffer(path)
        if r:
            this_path = vim.current.buffer.name

            s = string.join(vim.current.buffer[:], jcommon.LINE_DELIMITER)

            pat = re.compile(r'\(==(?P<language>[a-zA-Z0-9_-]+)==\s+\(\s*===\s+"""(?P<code>.+?)"""\s*\)\s*\)', re.DOTALL)
            i = 0
            while 1:
                r = pat.search(s, i)
                if r:
                    i = r.end()

                    language = string.strip(r.group('language'))
                    code = r.group('code')


                    if language == 'rkt':
                        before = s[:r.start()]
                        line_num = before.count(jcommon.LINE_DELIMITER) + 1
                        all_code.append((';; from file://%s#%d' % (this_path, line_num)) + jcommon.LINE_DELIMITER + code)
                else:
                    break


    vim.go_to_opened_buffer(original_path)
    shared.MARK_BUFFER_SWITCH = 1

    return all_code


def do_rackload(vim):
    all_code = get_rackload_files(vim)

    s = string.join(all_code, '\n') + '\n'
    fname_out = os.path.join('/tmp', 'vim-' + str(uuid.uuid1()) + '.rkt')
    fout = open(fname_out, 'wb')
    fout.write(s)
    fout.close()

    from hsdl.vim import racket_helper
    racket_helper.racket_load(fname_out)



def on_vim_leave(vim):
        try:
            path = shared.EXTERNAL_EDITOR_OUTPUT_PATH
            if not path:
                return

            all_text = ''

            s = vim.get_register('@')       # read from default clipboard
            if s:
                all_text = s
            else:
                line = vim.current.line
                if not line.strip():        # if you are on empty line, forget it
                    return

                block, _line_start, _line_end = vim.get_block(check_indent=0)
                all_text = block

            fout = open(path, 'wb')
            fout.write(all_text + '\n')
            fout.close()
        except:
            pass


def show_error_on_this_line(vim):
  path = vim.current.buffer.name
  d = shared.GENERIC_ERRORS
  if not d: return
  line_num = int(vim.eval('line(".")'))
  tup = (path, line_num)
  if d.has_key(tup):
    print "\n".join(d[tup])


