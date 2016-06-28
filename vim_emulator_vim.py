import string
import sys
import os
import re
import types
import random

from hsdl.common import general

from hsdl.vim import shared

from hsdl.vim import vim_emulator
from hsdl.vim import jcommon

LINE_DELIMITER = '\n'

BASE_INDENT_SPACES = '    '
BASE_INDENT_SIZE = len(BASE_INDENT_SPACES)

spaces_pat = re.compile(r'^(?P<spaces>\s*)')

MODE_SEXP = 1
MODE_PROLOG = 2

mode_color = {
    MODE_SEXP : 'green',
    MODE_PROLOG : 'blue'
}

multi_spaces = re.compile(r'\s+')

struct_pat = re.compile(r'struct:tc-results?\s*')

def set_exec_lang_ext(ext):
    if ext:
        shared.LANG_EXT = ext

def get_exec_lang_ext():
    return shared.LANG_EXT

class VimEmulatorVim(vim_emulator.VimEmulator):
    def __init__(self, vim):
        self.vim = vim
        self.ALL_SIGNS = []
        self.SIGN_CURRENT = 0
        self.SIGN_DICT = {}

    def __repr__(self):
        return '<VimEmulatorVim>'

    def __str__(self):
        return self.__repr__()

    def __getattr__(self, attr):
        if hasattr(self.vim, attr):
            return getattr(self.vim, attr)
        else:
            return self.__dict__[attr]

    def getPath(self):
        return self.vim.current.buffer.name

    def getLine(self, line_num = None): #DONE
        if line_num is None:
            return self.vim.current.line
        else:
            # this often happens when you start with an empty file
            if line_num == -1:
              return ''
            else:
              return self.vim.current.buffer[line_num-1]

    def setLine(self, text, line_num = None): #DONE
        if line_num is None:
            line_num = self.getLineNum()

        self.setLines(line_num, line_num, text)

    def getLines(self): #DONE
        return self.getText().split("\n")

    def setAllLines(self, lines):   #DONE
        self.vim.current.buffer[:] = lines

    def replace(self, offset, total_size, newStr, style = None): #DONE
        s = self.getText()
        s2 = s[:offset] + newStr + s[offset + total_size:]
        self.setText(s2)

    # 0-indexed line nums
    def setLines(self, startLineNum, endLineNum, linesOrString, style = None):  #DONE
        if endLineNum >= startLineNum:
            startOff = self.getOffsetAtLine(startLineNum)
            endOff = self.getOffsetAtLine(endLineNum) + len(self.getLine(endLineNum))
            if type(linesOrString) == types.ListType:
                self.replace(startOff, endOff - startOff, string.join(linesOrString, '\n'), style=style)
            else:
                self.replace(startOff, endOff - startOff, linesOrString, style=style)

    # 0-indexed line nums; inclusive
    # TODO: ending position of by a couple of chars
    def setSelectionLines(self, startLineNum, endLineNum):  #TODO, but awaiting other methods to work correctly
        if endLineNum >= startLineNum:
            startOff = self.getOffsetAtLine(startLineNum)
            endOff = self.getOffsetAtLine(endLineNum) + len(self.getLine(endLineNum))
            self.setSelection(startOff, endOff)

    def setSelection(self, posStart, posEnd):   #TODO
        pass

    def getLength(self):    #DONE
        return int(self.vim.eval('line2byte(line("$")+1)')) -1   # see: http://vimdoc.sourceforge.net/htmldoc/eval.html

    def getLineLength(self, line_num):  #DONE
        return len(self.getLine(line_num))

    def selectAll(self):    #TODO
        pass

    def getText(self, start=None, end=None):  #DONE
        if start is None:
            start = 0
        if end is None:
            end = self.getLength()

        s = string.join(self.vim.current.buffer[:], LINE_DELIMITER)
        return s[start:end]

    def setPosition(self, pos): #DONE
        self.vim.command(":go " + str(pos + 1))     # :go is 1-indexed

    def insert(self, s, style=None):    #DONE
        off = self.getPosition()
        self.insertAt(s, off, style=style)

    def insertAt(self, newStr, off, style=None):    #DONE
        s = string.join(self.vim.current.buffer[:], LINE_DELIMITER)
        s2 = s[:off] + newStr + s[off:]
        self.setText(s2)

    def getSelectionText(self): #TODO
        return ''

    def setText(self, s):   #DONE
        lines = s.split(LINE_DELIMITER)
        self.setAllLines(lines)

    def clear(self):    #DONE
        self.vim.current.buffer[:] = []

    def append(self, s, style=None):    #DONE
        off = self.getLength()
        self.insertAt(s, off, style=style)

    # position of caret, 0-indexed
    def getPosition(self):  #DONE
        return int(self.vim.eval('line2byte(line("."))+col(".")')) - 1 - 1

    # 0-indexed     # TODO is this true? seems to be 1-indexed
    def getLineNum(self, pos = None):   #DONE
        if pos is None:
            pos = self.getPosition()

        return int(self.vim.eval("byte2line(%s)" % (pos+1)))

    # 0-indexed
    def getColNum(self):    #DONE
        return int(self.vim.eval("col('.')")) - 1

    # 0-indexed
    def setColNum(self, colNum):
        line_num = self.getLineNum()
        self.vim.current.window.cursor = (line_num, colNum)

    def getOffsetAtLine(self, line_num):    # NOTE: this is 1-indexed #DONE
        return int( self.vim.eval("line2byte(%s)" % line_num) ) - 1

    # returns (startOffset, endOffset, length)
    def getLineInfo(self, line_num):    #DONE
        line_length = len(self.vim.current.buffer[line_num-1])
        offset = self.getOffsetAtLine(line_num)
        return offset, offset + line_length, line_length

    # returns pos, line_num, line_offset, col_num
    def getPositionInfo(self):  #DONE
        line_num = self.getLineNum()
        return (self.getPosition(),
                line_num,
                self.getOffsetAtLine(line_num),
                self.getColNum())

    def getLineCount(self): #DONE
        return len(self.vim.current.buffer)

    def getLineCountBetween(self, start, end):  #TODO
        return -1

    # ---------------- here is where we start adding on additional methods -------

    def open_new_tab(self, fname, set_folding=1, return_to_original=0):
        vim = self.vim

        curr_path = vim.current.buffer.name
        vim.command(":silent tabnew " + fname)
        if not set_folding: #not ext in ['.mind']:
            vim.command(":silent set nofoldenable")

        if return_to_original:
            self.go_to_opened_buffer(curr_path)

    # ==================================================================================================
    # ==================================================================================================
    #   candidates for inclusion in VimEmulator interface
    # ==================================================================================================
    # ==================================================================================================

    # all buffers, including those not visible
    def get_buffer_list(self):
        vim = self.vim

        vim.command("let g:zzz=''")
        names = []
        i = 1
        while 1:
            vim.command("let g:zzz=bufname(%d)" % i)
            name = vim.eval("g:zzz")
            if name is None: break
            names.append(name)
            i += 1
        return names


    def get_opened_buffer_list(self):
        vim = self.vim

        starting_name = vim.current.buffer.name

        full = self.get_buffer_list()

        last = ''
        all = []
        for i in xrange(1, len(full)+1):
            vim.command(":silent! %dtabnext" % i)
            name = vim.current.buffer.name
            if name == last: break
            all.append(name)
            last = name


        # go back to original
        if starting_name in all:
            num = all.index(starting_name)
            vim.command(":silent! %dtabnext" % num)

        return all


    def create_new_split(self, fname, vertical=0, force_bottom=0, new=False):
        vim = self.vim

        if vertical:
          if new:
            vim.command(":silent! vnew" + fname)
          else:
            vim.command(":silent! rightbelow vsplit " + fname)
        else:
            if force_bottom:
              if new:
                vim.command(":silent! rightbelow new " + fname)
              else:
                vim.command(":silent! rightbelow split " + fname)
            else:
              if new:
                vim.command(":silent! topleft new  " + fname)
              else:
                vim.command(":silent! topleft split " + fname)


    # decide before splitting
    def open_new_split(self, fname, vertical=0, force_bottom=0, unique=0, unique_prefix='', new=False, size=None):
        if self.is_vim_emulator():
            return

        dict = self.get_opened_buffer_map()
        curr_num = self.tabGetCurrentPage()

        if unique:
            if dict.has_key(curr_num):
                found = 0
                found_fname = ''

                for path in dict[curr_num]:
                    _, base_fname = os.path.split(path)
                    if (path == fname) or  (unique_prefix and string.find(base_fname, unique_prefix) == 0):
                        found = 1
                        found_fname = path

                if found:
                    self.go_to_window_in_tab(curr_num, dict[curr_num], found_fname)
                    return

        # -- if we got here, that means we have to split
        self.create_new_split(fname, vertical=vertical, force_bottom=force_bottom, new=new)
        if not size is None:
            self.vim.command(":vertical resize %d" % size)

        self.vim.command(":silent set nofoldenable")


    # returns dict: tab_num -> [fname1, ...]
    #   tab_num starts at 1; fname does not contain the path
    #   the list is of windows within a tab, in the event that there's a split
    #       if horizontal split, it seems to correspond to order from top to bottom
    def get_opened_buffer_map(self):
        vim = self.vim

        vim.command(":redir @h")            # redirect to register H
        vim.command(":silent! tabs")        # dump the list
        vim.command(":redir END")

        cwd = general.get_canonical_name(os.getcwd())

        buff = vim.eval("@h")
        if not buff:
            buff = ""

        lines = string.split(buff, '\n')

        dict = {}

        curr_tab_num = 0

        for line in lines:
            line = string.strip(line)
            if not line: continue

            parts = string.split(line)

            if parts[:2] == ['Tab', 'page']:
                curr_tab_num = int(parts[2])
                dict[curr_tab_num] = []
            else:
                fname = parts[-1]                                       # the first symbols could be ">" or "+", but the filename is always last
                fname = general.get_canonical_name(fname)
                fname = os.path.join(cwd, fname)

                if curr_tab_num>0 and dict.has_key(curr_tab_num):
                    dict[curr_tab_num].append(fname)

        return dict

    # this code works; setting "swtichbuf=useopen" is crucial
    def go_to_window_in_tab(self, tab_num, full_list, fname):
        vim = self.vim

        if self.is_vim_emulator():
            return

        vim.command(":silent! %dtabnext" % tab_num)

        if len(full_list)>1:
            vim.command(":set switchbuf=useopen")
            vim.command(":silent! sb " + fname)
            vim.command(":set switchbuf=")              # restore

        return True


    def go_to_opened_buffer(self, fname='', pos=None):
        dict = self.get_opened_buffer_map()

        found_tab_num = 0

        if fname:
            windows_list = []
            for tab_num, paths in dict.items():
                for path in paths:
                    path = general.get_real_path(path)
                    if fname == path:
                        found_tab_num = tab_num
                        windows_list = paths
                        break

        elif not pos is None:
            if pos == -1:
                found_tab_num = len(dict)
                windows_list = dict[len(dict)]
            else:
                found_tab_num = pos + 1
                windows_list = dict[pos+1]

        if found_tab_num>0:
            return self.go_to_window_in_tab(found_tab_num, windows_list, fname)
        return False


    # goes to the buffer containing the substring
    # if multiple choices, goes to the first one when sorted in a case-insensitive way
    # curr_tab_only: find only the one within this tab
    def find_buffer_name_containing(self, match, curr_tab_only=0):
        match_upper = string.upper(match)

        tab_num = self.tabGetCurrentPage()

        dict = self.get_opened_buffer_map()
        matches = []
        for the_tab_num, paths in dict.items():

            if curr_tab_only and the_tab_num != tab_num:
                continue

            for path in paths:
                fname_upper = string.upper(os.path.split(path)[1])
                if string.find(fname_upper, match_upper)>=0:                #!!! matching might not be enough; ambiguous
                    matches.append(path)

        if len(matches) == 1:
            self.go_to_opened_buffer(matches[0])
            return 1

        elif len(matches)>1:
            tosort = map(lambda path: (string.upper(os.path.split(path)[1]), path),  matches)
            tosort.sort()
            self.go_to_opened_buffer(tosort[0][1])  # choose the first
            return 1


    def dump_to_new_vsplit(self, lines, return_to_original=1):
        vim = self.vim

        curr_path = vim.current.buffer.name

        tempfname = general.local_hsdl_mktemp('INF__') + '.mind'
        self.open_new_split(tempfname, vertical=1, unique=1, unique_prefix='INF__')     # if another already exists within the sa
        new_buffer = vim.current.buffer
        new_buffer[:] = lines
        vim.command("set nomodified")
        vim.command(":set nofoldenable")

        if return_to_original:
            self.go_to_opened_buffer(curr_path)


    def dump_to_new_split(self, lines, return_to_original=1):
        vim = self.vim

        curr_path = vim.current.buffer.name

        tempfname = general.local_hsdl_mktemp('INF__') + '.mind'
        self.open_new_split(tempfname, vertical=0, unique=1, unique_prefix='INF__')     # if another already exists within the sa
        new_buffer = vim.current.buffer
        new_buffer[:] = lines
        vim.command("set nomodified")
        vim.command(":set nofoldenable")

        if return_to_original:
            self.go_to_opened_buffer(curr_path)

    def dump_to_new_tab(self, lines, return_to_original=1, tempfname=''):
        vim = self.vim

        curr_path = vim.current.buffer.name

        if not tempfname:
            tempfname = general.local_hsdl_mktemp('INF__') + '.mind'

        self.open_new_tab(tempfname)
        new_buffer = vim.current.buffer
        new_buffer[:] = lines
        vim.command("set nomodified")
        vim.command(":set nofoldenable")

        if return_to_original:
            self.go_to_opened_buffer(curr_path)

    def tabGetCurrentPage(self):  # 1-indexed
        return int(self.vim.eval("tabpagenr()"))

    def tabGetCount(self):
        return int(self.vim.eval("tabpagenr('$')"))

    def tabCloseAllOthers(self):
        self.vim.command(":silent tabonly!")

    def tabNext(self):
        self.vim.command(":silent tabnext")

    def tabClose(self):
        self.vim.command(":silent q!")

    # returns line_num, col_num  0-indexed
    def find_mark_in_buffer(self, goto_mark):
        goto_mark = string.strip(goto_mark)
        pat = re.compile(r'<::\s*' + goto_mark +  '\s*::>', re.IGNORECASE)

        curr_line = 0
        for line in self.vim.current.buffer[:]:
            r = pat.search(line)
            if r:
                return curr_line, r.start()
            curr_line += 1
        return -1, -1


    # returns list of (mark-label, line_num, col_num)

    def list_marks_in_file(self, path):
        if not os.path.exists(path):
            return []

        all = []

        pat = re.compile(r'<::\s*(?P<label>[^:]+)\s*::>')

        fin = open(path, 'rb')

        curr_line = 0
        while 1:
            line = fin.readline()
            if not line: break

            r = pat.search(line)
            if r:
                label = string.strip(r.group('label'))
                all.append((label, curr_line, r.start()))
            curr_line += 1

        fin.close()

        return all


    def check_already_exists(self, fname):
        reload(jcommon)
        dict = self.get_opened_buffer_map()

        for tab_num, paths  in dict.items():
                for path in paths:
                    if jcommon.path_matches(path, fname):
                        return tab_num, paths, path

        return None

    def get_register(self, name):
        buff = self.vim.eval("@" + name)
        if not buff:
            buff = ""
        return buff

    def set_register(self, name, s):
        s = string.replace(s, '\\', '\\\\')
        s = string.replace(s, '"', '\\"')
        self.vim.command('let @' + name + '="%s"' % s)

    def is_vim_emulator(self):
        return 0

    def sign_show(self):
        vim = self.vim

        curr_fname = vim.current.buffer.name
        _id, dest_fname = self.ALL_SIGNS[self.SIGN_CURRENT-1]

        if curr_fname != dest_fname:
            r = vim.go_to_opened_buffer(dest_fname)
            if not r:
                self.open_new_tab(dest_fname)

        vim.command(":sign jump %d file=%s" % (self.SIGN_CURRENT, dest_fname))


    def sign_clear(self):
        self.ALL_SIGNS = []
        self.SIGN_CURRENT = 0
        self.SIGN_DICT = {}
        TOOLTIP_DICT = {}
        self.vim.command(":sign unplace *")

    def sign_next(self):
        count = len(self.ALL_SIGNS)
        if not self.ALL_SIGNS: return

        if count>0 and self.SIGN_CURRENT < count:
            self.SIGN_CURRENT += 1
        else:
            self.SIGN_CURRENT = 1

        self.sign_show()


    def next_sign_id(self):
        return len(self.ALL_SIGNS) + 1


    def add_sign(self, line, fname, open_if_not_opened=False, symbol='piet'):
        id = self.next_sign_id()
        self.ALL_SIGNS.append((id, fname))

        try:
            self.vim.command(":sign place %d line=%d name=%s file=%s" % (id, line, symbol, fname))
        except:
            self.check_exit_condition()
            if open_if_not_opened:
                self.open_new_tab(fname)
                self.vim.command(":sign place %d line=%d name=%s file=%s" % (id, line, symbol, fname))     # try again

    def sign_prev(self):
        if not self.ALL_SIGNS: return

        count = len(self.ALL_SIGNS)
        if count>0 and self.SIGN_CURRENT > 1:
            self.SIGN_CURRENT -= 1
        else:
            self.SIGN_CURRENT = count

        self.sign_show()

    def check_exit_condition(self):
        if shared.EXCEPTION_EXIT:
            buff = cStringIO.StringIO()
            traceback.print_exc(file=buff)
            msg = buff.getvalue()
            fout = open('__vim_error.mind','wb')
            fout.write(msg + '\n')
            fout.close()

            self.vim.command("echo 'Error. See __vim_error.mind in the current directory'")
            self.vim.command("qa!")


    def displayRacketPositionInfo(self):
        pos = int(self.vim.eval('line2byte(line("."))+col(".")')) - 1
        type_info = self.getRacketTypeInfo(pos)
        arrow_info = self.getRacketArrowInfo(pos)
        jump_info = self.getRacketJumpInfo(pos)

        if type_info or arrow_info or jump_info:
            if not type_info:
                type_info = '-'

            if jump_info:
                text = type_info + ' : ' + arrow_info + ' -> ' + jump_info
            else:
                text = type_info + ' : ' + arrow_info
            print text
        else:
            print ''    # clear out previous message (if any)



    def getRacketTypeInfo(self, pos):
        from hsdl.vim import racket_helper
        reload(racket_helper)
        path = self.vim.current.buffer.name

        def when_not_found():
            from hsdl.vim import vim_commands_racket
            reload(vim_commands_racket)
            vim_commands_racket.racktypes(self, ())

        d = racket_helper.get_data(path, 'types', when_not_found, {}, optional=1)

        found = []
        for (start_pos, end_pos), (item, message) in d.items():
            if pos>=start_pos and pos<=end_pos:
                # we will sort on size, because the narrowest range takes priority (i.e. it is most specific)
                found.append((end_pos-start_pos, start_pos, end_pos, item, message))

        if found:
            found.sort()
            _, _, _, item, message = found[0]
            s = "%s %s" % (item, message)
            s = string.replace(s, '\n', ' ')
            s = multi_spaces.sub(' ', s)
            s = struct_pat.sub('', s)
            s = s[:150]
            return s
        else:
            return ''

    def getRacketArrowInfo(self, pos):
        from hsdl.vim import racket_helper
        reload(racket_helper)
        path = self.vim.current.buffer.name

        def when_not_found():
            from hsdl.vim import vim_commands_racket
            reload(vim_commands_racket)
            vim_commands_racket.rackanalyze(self, ())

        arrow_entries = racket_helper.get_data(path, 'arrows', when_not_found, [])

        if arrow_entries:
            for target, target_start, target_end, target_line, target_col, src, src_start, src_end, src_line, src_col, actual, level  in  arrow_entries:
                if pos>=target_start and pos<=target_end:
                    return str(target) + " | " + str(src)
        return ''

    def getRacketJumpInfo(self, pos):
        from hsdl.vim import racket_helper
        reload(racket_helper)
        path = self.vim.current.buffer.name

        def when_not_found():
            from hsdl.vim import vim_commands_racket
            reload(vim_commands_racket)
            vim_commands_racket.rackanalyze(self, ())

        jump_entries = racket_helper.get_data(path, 'jumps', when_not_found, [])

        if jump_entries:
            for src_start, src_end, the_id, the_path in jump_entries:
                if pos>=src_start and pos<=src_end:
                    return the_id + " (" + the_path + ")"
        return ''

    def jumpToFirstErrorInFile(self):
        path = self.vim.current.buffer.name
        d = shared.GENERIC_ERRORS
        keys = d.keys()
        tosort = [(line_num, the_path) for (the_path, line_num) in d.keys()]
        tosort.sort()
        for line_num, the_path in tosort:
            if path == the_path:
                self.setLineNum(line_num)
                self.displayGenericErrorMessage()
                return

    def displayGenericErrorMessage(self, full=False):
        from hsdl.vim import racket_helper
        reload(racket_helper)
        path = self.vim.current.buffer.name

        if racket_helper.has_data(path, 'types') or racket_helper.has_data(path, 'arrows') or racket_helper.has_data(path, 'jumps'):
            self.displayRacketPositionInfo()
        else:
            d = shared.GENERIC_ERRORS
            if not d: return

            line_num = int(self.vim.eval('line(".")'))
            tup = (path, line_num)
            if d.has_key(tup):
                if full:
                  s = string.join(d[tup], '\n')
                  print s
                else:
                  s = string.join(d[tup], ' -- ')
                  print s
            else:
                print ""

    def set_mode(self, mode):
        if mode in mode_color:
            path = self.vim.current.buffer.name
            if path:
                color = mode_color[mode]
                shared.CURR_MODE = mode
                self.sign_clear()
                self.vim.command('highlight SignColumn ctermbg=' + color)
                self.add_sign(1, path, open_if_not_opened=False, symbol='mode')


    def get_text_range_data(self, start_pos, end_pos, start_col, orig_str):
        vim = self.vim

        line1 = int(vim.eval("byte2line(%d)" % start_pos))
        line2 = int(vim.eval("byte2line(%d)" % end_pos))
        parts = string.split(orig_str, '\n')
        if len(parts) == 1:
            end_col = start_col + len(parts[0])
        else:
            end_col = len(parts[-1])

        return line1, start_col, line2, end_col

    def get_block_lisp(self):
        vim = self.vim

        line_num = int(vim.eval('line(".")'))
        line = vim.current.line
        p = string.rfind(line, ')')
        if p>=0:
            coords_orig = vim.current.window.cursor
            vim.current.window.cursor = (line_num, p)
            vim.command("normal v")
            vim.command("normal %")
            line_num2 = int(vim.eval('line(".")'))
            start_indent = jcommon.get_indentation(vim.current.line)
            vim.command('normal "ty')
            buff = vim.eval("@t")
            vim.current.window.cursor = coords_orig
            lines = string.split(buff, '\n')
            lines = lines[:-1] + [line]
            first_line = (BASE_INDENT_SPACES*start_indent) + lines[0]
            lines[0] = first_line
            buff = string.join(lines, '\n')
            return buff, line_num2, line_num
        else:
            return None, -1, -1

    def get_block(self, direction=0, check_indent=True, use_line='', is_sexp=0):
        vim = self.vim

        line = vim.current.line
        if use_line:
            if string.find(use_line, ';::SISC::')>=0 or string.find(use_line, ';::CLJ::')>=0 or \
               string.find(use_line, ';::LFE::')>=0 or string.find(use_line, ';::SCM::')>=0:
                s, start_row, end_row = self.get_block_lisp()
                return s, start_row-1, end_row
        elif is_sexp:
            s, start_row, end_row = self.get_block_lisp()
            return s, start_row-1, end_row



        start_line_num = int(vim.eval('line(".")'))-1       # line numbering starts at 1, but indexing starts at 0

        buff = vim.current.buffer
        max = len(buff)

        start_indent = jcommon.get_indentation(buff[start_line_num])
        if check_indent:
            if start_indent == 0: return '', -1, -1

        # go backward
        i = start_line_num - 1
        while i>=0:
            line = buff[i]
            if not string.strip(line): break
            if check_indent:
                indent = jcommon.get_indentation(line)
                if indent < start_indent:
                    break
            i -= 1

        real_start = i+1

        if direction == -1:     # only going backward
            max = start_line_num


        all = []
        for i in xrange(real_start, max):
            line = buff[i]
            if not string.strip(line): break
            if check_indent:
                indent = jcommon.get_indentation(line)
                if indent < start_indent:
                    break

            all.append(line)

        return string.join(all, '\n'), real_start, i


    def find_ancestors_helper(self, lines, pos, row, col):
        vim = self.vim

        pat = re.compile(r'(?P<symbol>[^() \r\n]+)')

        s = string.join(lines, LINE_DELIMITER)
        size = len(s)

        acc = []

        # -- go backward
        i = pos
        if i<size:

            found = 0
            while i>=0:
                if s[i] == '(':
                    end_pos, block = jcommon.find_matching_symbol(s, i, size, '(', ')')
                    if not block is None:
                        r = pat.search(block)
                        if r:
                            sym = r.group('symbol')
                            line1, col1 = self.get_line_col(i)
                            line2, col2 = self.get_line_col(end_pos)
                            acc.append((sym, block, col1, line1, col1, line2, col2))

                            if sym[:2] == '==' and sym[-2:] == '==' and sym != '===' and sym != '==':   # stop when you reach the language spec
                                break
                i -= 1

        return acc

    # returns list of (spec, block)
    def find_ancestors(self):
        vim = self.vim

        pat = re.compile(r'(?P<symbol>[^() \r\n]+)')

        window = vim.current.window
        row, col = window.cursor
        line_start = int(vim.eval('line2byte(%d)' % row))
        pos = line_start + col - 1
        acc = self.find_ancestors_helper(vim.current.buffer[:], pos, row, col)
        return acc


    def get_line_col(self, pos):
        vim = self.vim
        line = int(vim.eval("byte2line(%i)"%(pos+1)))
        col = pos - int(vim.eval("line2byte(%i)"%line)) + 1
        return line, col


    # returns start_row, end_row, start_col, end_col
    def get_selection(self):
        vim = self.vim

        buff = vim.current.buffer

        tup = buff.mark('<')
        if tup:
            start, col_start  = tup
        else:
            return -1, -1, -1, -1, ''


        tup = buff.mark('>')
        if tup:
            end, col_end = tup
        else:
            return -1, -1, -1, -1, ''

        if start and end:
            final = []
            for i in xrange(start-1, end):
                line = vim.current.buffer[i]
                final.append(line)
            return start, end, col_start, col_end, string.join(final, '\n')


        else:
            return start_row, end_row, ''

    # returns (last_row, str)
    def get_curr(self):
        vim = self.vim

        r = vim.current.range
        start = r.start
        end = r.end
        if start == end:
            return end+1, vim.current.line
        else:
            s = string.join(vim.current.buffer[start:end], '\n')
            return end, s


    def get_current_language(self, ext=None):
        vim = self.vim

        buffname = vim.current.buffer.name
        if buffname:
            parent, fname = os.path.split(buffname)
            basename, ext = os.path.splitext(fname)
            if not ext in ['.mind']:
                return ext[1:]

        if ext:
            return ext

        try:
            s = vim.eval("g:lang_ext")
        except:
            s = ''      # Remember: default language is J

        last = get_exec_lang_ext()

        if not s and last:
            s = last

        if s:
            return s

    def clear_children(self, extra=0):
        # 'extra' parameter is needed in the case of j result block leaving a dangling, empty indented line in preparation
        # for the next command; extra=1 will delete that line
        _, start_row, end_row = self.get_all_children(vim)
        vim.current.buffer[start_row:end_row + extra] = []

    def get_all_children(self):
        vim = self.vim

        start_line_num = int(vim.eval('line(".")'))-1       # line numbering starts at 1, but indexing starts at 0

        buff = vim.current.buffer
        max = len(buff)

        start_indent = jcommon.get_indentation(buff[start_line_num])

        all = []
        i = start_line_num+1    # have i be set in case the loop below does NO iterations
        for i in xrange(start_line_num+1, max):
            line = buff[i]
            indent = jcommon.get_indentation(line)
            if indent <= start_indent:
                break

            all.append(line)

        return string.join(all, '\n'), start_line_num+1, i


    def insert_lines(self, lines, match_indent=None, line_num=None):     # if you want to match indent, set the arg to the number
        vim = self.vim

        lines = map(lambda line: line.encode('utf-8'), lines)
        if line_num is None:
            line_num = int(vim.eval('line(".")')) - 1
        buff = vim.current.buffer
        if not match_indent is None:
            lines = map(lambda line:  (BASE_INDENT_SPACES * match_indent) + line,   lines)
        buff[line_num:line_num] = lines

    def center_current_line(self):
        self.vim.command("normal zz")

    def enter_insert_mode(self):
        self.vim.command(':call feedkeys("i")')

    def enter_insert_mode_at_end(self):
        self.vim.command(':call feedkeys("A")')

    def enter_insert_mode_after(self):
        self.vim.command(':call feedkeys("a")')

    def sendKeys(self, s):
        self.vim.command(':call feedkeys("%s")' %s)

