function H(MainArg, ...)
    " the py function will handle looking at the arguments
    :py reload(jcommon)
    :py jinteractive.h_command(jcommon.build_vim(vim))
endfunction


function! Complete_H(ArgLead, CmdLine, CursorPos)
  let g:returning=[]
  :py reload(jcommon)
  :py jinteractive.h_command_completion(jcommon.build_vim(vim))
  return g:returning
endfunction

:command! -nargs=* -range=% -complete=customlist,Complete_H  H  :call H(<f-args>)


======
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


