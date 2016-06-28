import string
import sys
import os
import re
import types

from hsdl.vim import jcommon

class VimEmulator:
    def getPath(self): pass

    def setLine(self, text, line_num = None): #DONE
        if line_num is None:
            line_num = self.getLineNum()

        self.setLines(line_num, line_num, text)

    def begin_undo_block(self):
        pass

    def getLines(self): pass
    def setAllLines(self, lines): pass
    def replace(self, offset, total_size, newStr, style = None): pass
    def setLines(self, startLineNum, endLineNum, linesOrString, style = None):  pass
    def setSelectionLines(self, startLineNum, endLineNum):  pass
    def setSelection(self, posStart, posEnd):   pass
    def getLength(self):    pass
    def getLineLength(self, line_num):  pass
    def selectAll(self):    pass
    def getText(self, start=None, end=None): pass
    def setPosition(self, pos): pass
    def insert(self, s, style=None): pass
    def insertAt(self, newStr, off, style=None): pass
    def getSelectionText(self): pass
    def setText(self, s): pass
    def clear(self): pass
    def append(self, s, style=None): pass
    def getPosition(self): pass
    def getColNum(self): pass
    def getLineNum(self, pos = None):   pass

    def setLineNum(self, line_num): 
        offset = self.getOffsetAtLine(line_num)
        self.setPosition(offset)

    def setColNum(self, colNum):
        line_num = self.getLineNum()
        line_pos = self.getOffsetAtLine(line_num)
        self.setPosition(line_pos + colNum)

    def getOffsetAtLine(self, line_num): pass
    def getLineInfo(self, line_num): pass    # TODO: _jtext version conflicts with definition in embcomp_editors
    def getPositionInfo(self): pass
    def getLineCount(self): pass
    def getLineCountBetween(self, start, end): pass
    def open_new_tab(self, fname, set_folding=1): pass
    def get_buffer_list(self): pass
    def get_opened_buffer_list(self): pass
    def create_new_split(self, fname, vertical=0, force_bottom=0): pass
    def open_new_split(self, fname, vertical=0, force_bottom=0, unique=0, unique_prefix='', size=None): pass
    def get_opened_buffer_map(self): pass
    def go_to_window_in_tab(self, tab_num, full_list, fname): pass
    def go_to_opened_buffer(self, fname='', pos=None): pass
    def find_buffer_name_containing(self, match, curr_tab_only=0): pass

    def dump_to_new_vsplit(self, lines, return_to_original=1):
        print string.join(lines, '\n')

    def dump_to_new_split(self, lines, return_to_original=1): 
        print string.join(lines, '\n')

    def dump_to_new_tab(self, lines, return_to_original=1, tempfname=''): pass


    def tabGetCurrentPage(self): pass
    def tabGetCount(self): pass
    def tabCloseAllOthers(self): pass
    def tabNext(self): pass
    def tabClose(self): pass
    def find_mark_in_buffer(self, goto_mark): pass
    def list_marks_in_file(self, path): pass
    def check_already_exists(self, fname): pass
    def get_register(self, name): pass
    def set_register(self, name, s): pass
    def is_vim_emulator(self): pass
    def sign_show(self): pass
    def sign_clear(self): pass
    def sign_next(self): pass
    def next_sign_id(self): pass
    def add_sign(self, line, fname, open_if_not_opened=False, symbol='piet'): pass
    def sign_prev(self): pass
    def check_exit_condition(self): pass
    def displayRacketPositionInfo(self): pass
    def getRacketTypeInfo(self, pos): pass
    def getRacketArrowInfo(self, pos): pass
    def getRacketJumpInfo(self, pos): pass
    def displayGenericErrorMessage(self): pass
    def set_mode(self, mode): pass
    def get_text_range_data(self, start_pos, end_pos, start_col, orig_str): pass

    def buffer_replace_string(self, line1, col1, line2, col2, new_str):
        vim = self.vim

        start = vim.current.buffer[line1][:col1]
        end = vim.current.buffer[line2][col2+1:]
        mid = string.split(new_str, '\n')
        num_lines = len(mid)
        if num_lines > 1:
            vim.current.buffer[line1:line2+1] = [start + mid[0]] + mid[1:-1] + [mid[-1] + end]
        elif num_lines == 1:
            vim.current.buffer[line1:line2+1] = [start + mid[0] + end]

    def get_block_lisp(self): pass
    def get_selection(self): pass
    def get_curr(self): pass
    def get_current_language(self, ext=None): pass
    def clear_children(self, extra=0): pass
    def get_all_children(self): pass
    def insert_lines(self, lines, match_indent=None, line_num=None): pass
    def center_current_line(self): pass
    def enter_insert_mode(self): pass
    def enter_insert_mode_at_end(self): pass
    def enter_insert_mode_after(self): pass
    def sendKeys(self, s): pass


    def find_ancestors_helper(self, lines, pos, row, col):
        pat = re.compile(r'(?P<symbol>[^() \r\n]+)')

        s = string.join(lines, jcommon.LINE_DELIMITER)
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

        sys.stdout.flush()
        return acc

    # returns list of (spec, block)
    def find_ancestors(self):
        pat = re.compile(r'(?P<symbol>[^() \r\n]+)')

        window = self.current.window
        row, col = window.cursor
        line_start = self.getOffsetAtLine(row)      # NOTE: this is 1-indexed #DONE   
        #line_start = int(vim.eval('line2byte(%d)' % row))
        pos = line_start + col - 1
        acc = self.find_ancestors_helper(self.current.buffer[:], pos, row, col)
        return acc


    def get_line_col(self, pos):
        line = self.getLineNum(pos)
        col = pos - int(self.eval("line2byte(%i)"%line)) + 1
        return line, col



    def get_block(self, direction=0, check_indent=True, use_line='', is_sexp=0):
        line = self.current.line
        start_line_num = int(self.eval('line(".")'))-1       # line numbering starts at 1, but indexing starts at 0

        buff = self.current.buffer
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

    # ===========================

    def enter_insert_mode(self):
        pass

    def enter_insert_mode_after(self):
        pass

