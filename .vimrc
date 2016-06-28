"NOTES:
"   1) for unknown reasons, 'set paste' can cause tabbing not to work for snipMate

":let loaded_matchparen = 1  "fool it into NOT turning on matching

set t_Co=256

set nocp " :-)
" turn these ON:
"set digraph ek hidden ruler sc vb wmnu
" turn these OFF:
set noeb noet nosol
" non-toggles:
"set bs=2 fo=cqrt ls=2 ww=<,>,h,l   "shm=at
set comments=b:#,:%,fb:-,n:>,n:)
set viminfo=%,'50,\"100,:100,n~/.viminfo

" --- Vundle -------------------------------------------

set nocompatible
filetype off
set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()
Plugin 'gmarik/Vundle.vim'

" The following are examples of different formats supported.
" Keep Plugin commands between vundle#begin/end.
" plugin on GitHub repo
Plugin 'tpope/vim-fugitive'
" plugin from http://vim-scripts.org/vim/scripts.html
Plugin 'L9'
" Git plugin not hosted on GitHub
Plugin 'git://git.wincent.com/command-t.git'
" git repos on your local machine (i.e. when working on your own plugin)
" The sparkup vim script is in a subdirectory of this repo called vim.
" Pass the path to set the runtimepath properly.
Plugin 'rstacruz/sparkup', {'rtp': 'vim/'}
" Avoid a name conflict with L9
"Plugin 'user/L9', {'name': 'newL9'}

Plugin 'bling/vim-airline'
Plugin 'mbbill/undotree'
Plugin 'scrooloose/nerdtree'
Plugin 'kien/ctrlp.vim'
Plugin 'mileszs/ack.vim'
Plugin 'godlygeek/tabular'
Plugin 'sjl/gundo.vim'
Plugin 'tpope/vim-abolish'
Plugin 'tommcdo/vim-exchange'
Plugin 'guns/vim-sexp'
Plugin 'tpope/vim-sexp-mappings-for-regular-people'
Plugin 'tpope/vim-surround'
Plugin 'tpope/vim-repeat'
Plugin 'luochen1990/rainbow'
Plugin 'tpope/vim-unimpaired'
Plugin 'davidhalter/jedi-vim'

Plugin 'derekwyatt/vim-scala'
Plugin 'ensime/ensime-vim'

" All of your Plugins must be added before the following line
call vundle#end()            " required
filetype plugin indent on    " required

let g:rainbow_active = 1

" -------------------------------------------------------

" settings which are the default
" (at least with "nocompatible" anyway):
" set smd sw=8 ts=8
" mappings:
map K     <NUL>
"map <C-Z> :shell
"map ,F :view    $VIMRUNTIME/filetype.vim
"map ,SO :source $VIMRUNTIME/syntax/
"map ,V  :view   $VIMRUNTIME/syntax/
" autocommands:
au FileType mail set tw=70
" some colors:  "white on black"
"hi normal   ctermfg=white  ctermbg=black guifg=white  guibg=black
"hi nontext  ctermfg=blue   ctermbg=black guifg=blue   guibg=black
" syntax coloring!! :-)
syn on
set nowrap
"set shortmess=""

" do not allow vim to change the terminal title
set notitle

set hlsearch
set incsearch
set ignorecase
set smartcase

set expandtab
set ts=2
set noerrorbells visualbell t_vb=
set novisualbell

set undolevels=1000
set tabpagemax=100
set laststatus=2

set nobomb    "unicode characters not added at the beginning of file
"map <F12> :nohlsearch<CR>


let g:lang_ext=''

colorscheme pablo
set guifont=Monospace\ 10    "enter :set gfn? in vim if you need to change it in the future
set ruler

set nobackup
"set autowriteall
set nowritebackup
set noswapfile
set wm=0            " no word wrapping
set textwidth=0     " no breaking
set sw=4            " identation size

if !($OSNAME == "linux")       " on linux, we just assume python is compiled in
    set cursorline
endif

filetype plugin on


if version >= 703
    " ==================== persistent undo ================
    set undodir=~/.vim/undodir
    set undofile
    set undolevels=10000 "maximum number of changes that can be undone
    set undoreload=10000 "maximum number lines to save for undo on a buffer
endif
"ab pystart py import string, re, sys, os, random, types; from vim import *
"ab py1 py current.line = string.upper(current.line)

filetype plugin on
au BufEnter *.hs compiler ghc

"file associations for syntax coloring
au BufRead,BufNewFile *.off set filetype=xml
au BufRead,BufNewFile *.yaws set filetype=erlang
au BufRead,BufNewFile *.lzx set filetype=xml
au BufRead,BufNewFile *.lfe set filetype=lfe
au BufRead,BufNewFile *.rkt set filetype=rkt
au BufRead,BufNewFile *.ecl set filetype=ecl
au BufRead,BufNewFile *.pg set filetype=pg_sql
au BufRead,BufNewFile *.pg set foldmethod=marker
au BufRead,BufNewFile *.dats set filetype=ats
au BufRead,BufNewFile *.sats set filetype=ats
au BufRead,BufNewFile *.json set filetype=javascript
"au BufRead,BufNewFile *.py set filetype=python

au BufRead,BufNewFile *.sbt set filetype=scala
au BufRead,BufNewFile *.scala set filetype=scala
au FileType scala setl sw=2 sts=2 et
au FileType python setl sw=2 sts=2 et
au BufRead,BufNewFile *.sc    set filetype=scala

au BufRead,BufNewFile *.rgen set filetype=rgen

au BufRead,BufNewFile *.ijs setlocal ts=2
au BufRead,BufNewFile *.ijs setlocal sw=2

" ***********************************
au BufEnter *.mind :py reload(jinteractive); jinteractive.check_autoload(vim)

:py if not '/home/hsdl/apps/python-2.7.3/lib/python2.7/site-packages/' in sys.path: sys.path.append('/home/hsdl/apps/python-2.7.3/lib/python2.7/site-packages/')

function PyScalaUpdate()
    :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.scala(jcommon.build_vim(vim), 'update')
endfunction

function PyMercuryUpdate()
    :py from hsdl.vim import vim_commands_mercury; reload(vim_commands_mercury); reload(jcommon); vim_commands_mercury.mercury(jcommon.build_vim(vim))
endfunction

function PyPGFunctionsUpdate()
    :py from hsdl.vim import vim_commands_pg; reload(vim_commands_pg); reload(jcommon); vim_commands_pg.pg(jcommon.build_vim(vim), 'load')
endfunction

function PyECLFunctionsUpdate()
    ":py from hsdl.vim import vim_commands_ecl; reload(vim_commands_ecl); reload(jcommon); vim_commands_ecl.ecl(jcommon.build_vim(vim), 'run')
endfunction

function PyErlangUpdate()
    :py from hsdl.vim import vim_commands_erl; reload(vim_commands_erl); reload(jcommon); vim_commands_erl.erl(jcommon.build_vim(vim), 'full-suite')
endfunction

function PyPythonUpdate()
    :py from hsdl.vim import vim_commands_python; reload(vim_commands_python); reload(jcommon); vim_commands_python.file_saved(jcommon.build_vim(vim), 'full-suite')
endfunction


function PyTypescriptUpdate()
    :py from hsdl.vim import vim_commands_typescript; reload(vim_commands_typescript); reload(jcommon); vim_commands_typescript.typescript_check_errors(jcommon.build_vim(vim), use_margins=1)
endfunction

function PyATSUpdate()
    :py from hsdl.vim import vim_commands_ats; reload(vim_commands_ats); reload(jcommon); vim_commands_ats.ats(jcommon.build_vim(vim))
endfunction


function PyRacketUpdate()
    :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.racket(jcommon.build_vim(vim))
endfunction


"au BufWritePost *.scala :call PyScalaUpdate()


function PyGenericDisplayMessage()
    :py from hsdl.vim import jcommon; reload(jcommon); jcommon.build_vim(vim).displayGenericErrorMessage()
endfunction

function PyGenericDisplayMessageFull()
    :py from hsdl.vim import jcommon; reload(jcommon); jcommon.build_vim(vim).displayGenericErrorMessage(full=True)
endfunction


au CursorMoved  *.ts        :call PyGenericDisplayMessage()
au CursorMoved  *.scala     :call PyGenericDisplayMessage()
au CursorMoved  *.m         :call PyGenericDisplayMessage()
au CursorMoved  *.erl       :call PyGenericDisplayMessage()
au CursorMoved  *.rkt       :call PyGenericDisplayMessage()
au CursorMoved  *.py        :call PyGenericDisplayMessage()
au CursorMoved  *.txt       :call PyGenericDisplayMessage()
au CursorMoved  *.dats      :call PyGenericDisplayMessage()
au CursorMoved  *.sats      :call PyGenericDisplayMessage()
au CursorMoved  *.pg        :call PyGenericDisplayMessage()
au CursorMoved  *.ecl       :call PyGenericDisplayMessage()
au CursorMoved  *.csv       :call PyGenericDisplayMessage()
au CursorMoved  *.ut        :call PyGenericDisplayMessage()

au BufWritePost *.ts        :call PyTypescriptUpdate()
au BufWritePost *.m         :call PyMercuryUpdate()
"au BufWritePost *.pg        :call PyPGFunctionsUpdate()
au BufWritePost *.ecl       :call PyECLFunctionsUpdate()
au BufWritePost *.erl       :call PyErlangUpdate()
"au BufWritePost *.py        :call PyPythonUpdate()
au BufWritePost *.dats      :call PyATSUpdate()
au BufWritePost *.sats      :call PyATSUpdate()
"au BufWritePost *.rkt       :call PyRacketUpdate()

au BufWritePost *.*         :py reload(jcommon); from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.run_action(jcommon.build_vim(vim))

"au CursorMoved  *.mind   :py reload(jinteractive); jinteractive.au_CursorMoved(vim)
"au InsertEnter  *.mind   :py reload(jinteractive); jinteractive.au_InsertEnter(vim)

au CursorMoved  *.mind   :py jinteractive.au_CursorMoved(jcommon.build_vim(vim))

au InsertEnter *.mind       :py jinteractive.exit_mode(jcommon.build_vim(vim))

au BufWritePost *.* :H startup_action_execute_on_write

" --- OmniCppComplete ---
" -- required --
set nocp " non vi compatible mode
filetype plugin on " enable plugins

" -- optional --
" auto close options when exiting insert mode
autocmd InsertLeave * if pumvisible() == 0|pclose|endif
set completeopt=menu,menuone

" -- configs --
let OmniCpp_MayCompleteDot = 1 " autocomplete with .
let OmniCpp_MayCompleteArrow = 1 " autocomplete with ->
let OmniCpp_MayCompleteScope = 1 " autocomplete with ::
let OmniCpp_SelectFirstItem = 2 " select first item (but don't insert)
let OmniCpp_NamespaceSearch = 2 " search namespaces in this and included files
let OmniCpp_ShowPrototypeInAbbr = 1 " show function prototype (i.e. parameters) in popup window

" -- ctags --
" map <ctrl>+F12 to generate ctags for current folder:
map <C-F12> :!ctags -R --c++-kinds=+p --fields=+iaS --extra=+q .<CR><CR>
" add current directory's generated tags file to available tags
"set tags+=./tags

set tags+=~/tags/stl3.3.tags


function CustomFoldText()
    let l:line = getline(v:foldstart)
    return l:line
endfunction

au BufRead,BufNewFile *.mind set filetype=mind
"au BufRead,BufReadPost *.mind :py reload(jinteractive); jinteractive.mind_opened(vim)
"au BufRead,BufUnload *.mind :py reload(jinteractive); jinteractive.mind_closed(vim)

:if $VIM_AUTO_ARGS == ""
    au BufRead,BufNewFile *.mind set foldmethod=indent
:endif

"au BufRead,BufNewFile *.mind set foldmethod=manual
au BufRead,BufNewFile *.mind set foldtext=CustomFoldText()
au BufRead,BufNewFile *.mind set ignorecase
au BufRead,BufNewFile *.mind set list!
au BufRead,BufNewFile *.mind set listchars=trail:.
au BufRead,BufNewFile *.clj set filetype=clojure
"au BufRead,BufNewFile *.mind set spell
"autocmd BufWinLeave * silent mkview
"au! BufReadPost,BufWritePost * silent loadview
"autocmd BufWinEnter * silent loadview
"
au BufRead,BufNewFile *.go set filetype=go
autocmd BufNewFile,BufRead *.ts setlocal filetype=typescript

autocmd BufWritePost * if expand("%") != "" | mkview | endif

" ---- when in automation, we don't bother loading previously saved views
"  (sometimes this fails)
:if $VIM_AUTO_ARGS == ""
:autocmd BufWinEnter * if expand("%") != "" | loadview | endif
:endif


" Sane tab navigation
:nmap <A-PageUp>   :tabprevious<cr>
:nmap <A-PageDown> :tabnext<cr>
:map  <A-PageUp>   :tabprevious<cr>
:map  <A-PageDown> :tabnext<cr>
:imap <A-PageUp>   <ESC>:tabprevious<cr>i
:imap <A-PageDown> <ESC>:tabnext<cr>i
":nmap <C-n>        :tabnew<cr>
":imap <C-n>        <ESC>:tabnew<cr>


"function! Mosh_FocusLost_SaveFiles()
"    :exe ":au FocusLost" expand("%") ":wa"
"endfunction

":call Mosh_FocusLost_SaveFiles()


":au FocusLost * :wa


filetype on
augroup vimrc_filetype
    autocmd!
    autocmd FileType     c         call s:MyCSettings()
    autocmd FileType     vim       call s:MyVimSettings()
    autocmd FileType     python    call s:MyPythonSettings()
augroup end

" Clear all comment markers (one rule for all languages)
map _ :s/^\/\/\\|^--\\|^> \\|^[#"%!;]//<CR>:nohlsearch<CR>

function! s:MyCSettings()
    " Insert comments markers
    map - :s/^/\/\//<CR>:nohlsearch<CR>
endfunction

function! s:MyVimSettings()
    " Insert comments markers
    map - :s/^/\"/<CR>:nohlsearch<CR>
endfunction

function! s:MyPythonSettings()
    " Insert comments markers
    map - :s/^/#/<CR>:nohlsearch<CR>
endfunction

function! s:MyOcamlSettings()
    " Insert comments markers
endfunction

" =====================================================================================
" =====================================================================================
if has("if_pyth") || has("gui_running") || ($OSNAME == "linux")       " on linux, we just assume python is compiled in
    :python import vim
    :python from hsdl.vim import jinteractive
    :python from hsdl.vim import jcommon
    :python from hsdl.vim import s_dispatch
    :python from hsdl.vim import main
    :py vim.command(":sign define pietwarning text=>> texthl=mindArg")
    :py vim.command(":sign define pieterror text==> texthl=mindComment")
    :py vim.command(":sign define piet text=>> texthl=mindComment")
    :py vim.command(":sign define data text=-- texthl=mindComment")
    :py vim.command(":sign define mode text=|| texthl=mindArg")
    ":py vim.command(":sign define thread text=** texthl=mindKeywords")
    ":py vim.command(":sign define piet text=>> texthl=scalaString")
    :py vim.command(":sign define thread text=** texthl=scalaString")
endif

" --- idle-time background execution
set updatetime=0     "3 seconds idle (otherwise an event is triggered)
let g:do_auto=0
let g:do_idle=0

function! ToggleAutoIdle()
   if g:do_auto
        let g:do_auto=0
        echo "AUTO OFF"
   else
        let g:do_auto=1
        echo "AUTO ON"
   end

endfunction


"map <F11> :let g:do_auto=1<CR>
"map <F11> :call ToggleAutoIdle()<CR>
" =====================================================================================
" =====================================================================================


":source ~/.vim/plugin/Shell.vim
":source ~/.vim/plugin/JShell.vim

" --- functions for moving the current tab to the left or right

function TabLeft()
   let tab_number = tabpagenr() - 1
   if tab_number == 0
      execute "tabm" tabpagenr('$') - 1
   else
      execute "tabm" tab_number - 1
   endif
endfunction

function TabRight()
   let tab_number = tabpagenr() - 1
   let last_tab_number = tabpagenr('$') - 1
   if tab_number == last_tab_number
      execute "tabm" 0
   else
      execute "tabm" tab_number + 1
   endif
endfunction





function Send_to_Screen(text)
  if !exists("g:screen_sessionname") || !exists("g:screen_windowname")
    call Screen_Vars()
  end

  echo system("screen -S " . g:screen_sessionname . " -p " . g:screen_windowname . " -X stuff '" . substitute(a:text, "'", "'\\\\''", 'g') . "'")
endfunction

function Screen_Session_Names(A,L,P)
  return system("screen -ls | awk '/Attached/ {print $1}'")
endfunction

function Screen_Vars()
  if !exists("g:screen_sessionname") || !exists("g:screen_windowname")
    let g:screen_sessionname = ""
    let g:screen_windowname = "0"
  end

  let g:screen_sessionname = input("session name: ", "", "custom,Screen_Session_Names")
  let g:screen_windowname = input("window name: ", g:screen_windowname)
endfunction

function FailedTesting()
    execute "normal qz"
    execute "normal zj"
    execute "normal zc"
    execute "normal q"
endfunction

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

vmap <C-c><C-c> "ry :call Send_to_Screen(@r)<CR>
nmap <C-c><C-c> vip<C-c><C-c>

nmap <C-c>v :call Screen_Vars()<CR>

set wildmode=list:longest
"set foldmethod=indent

map <F2> <Esc>:1,$!xmllint --format -<CR>



"set tags=/tech/hsdl/projects/www/lift/cuhsdl-lift/.scala_tags


"if has("autocmd")
"    autocmd FileType python set complete+=k/root/.vim/plugin/pydiction isk+=.,(
"    autocmd FileType python setlocal omnifunc=pysmell#Complete
"endif " has("autocmd")



highlight Folded ctermfg=DarkGray ctermbg=NONE guifg=DarkGray guibg=NONE

au BufRead,BufNewFile *.mind set filetype=mind
au BufRead,BufNewFile *.ut set filetype=ut

:if $VIM_AUTO_ARGS == ""
    au BufRead,BufNewFile *.mind set foldmethod=indent
:endif

"au BufRead,BufNewFile *.mind set foldmethod=manual

map <C-J> :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim))<CR>
map <C-K> :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), use_selection=1)<CR>
imap <C-J> <ESC>:py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), orig_mode='i')<CR>
"nmap <CR> :py reload(jinteractive); jinteractive.vimcallj(vim)<CR>

map <C-U> :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), force_new_window=True)<CR>
map <C-N> :py reload(jinteractive); reload(jcommon); jinteractive.vimsendjdata(jcommon.build_vim(vim))<CR>
"map <C-K> :py reload(jinteractive); jinteractive.clear_children(vim)<CR>
"map <C-V> :py reload(jinteractive); jinteractive.visualize(vim)<CR>
"map <C-O> :py reload(jinteractive); jinteractive.generic_open(vim)<CR>
"map <C-I> :py reload(jinteractive); jinteractive.clean_folding(vim)<CR>
"map <C-I> :py reload(jinteractive); jinteractive.clean_folding(vim)<CR>
map <C-I> :py reload(jinteractive); reload(jcommon); jinteractive.toggle_status(jcommon.build_vim(vim))<CR>
map <C-A> :py reload(jinteractive); reload(jcommon); jinteractive.handle_embedded_data(jcommon.build_vim(vim))<CR>


"map <C-D> :py reload(jinteractive); reload(jcommon); jinteractive.format_display(jcommon.build_vim(vim))<CR>
map ,d :py reload(jinteractive); reload(jcommon); jinteractive.format_display(jcommon.build_vim(vim))<CR>
map ,a :py vim.command(":w"); reload(jcommon); from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.run_action(jcommon.build_vim(vim), force=1)<CR>

map ,E :py reload(jinteractive); reload(jcommon); jinteractive.show_error_on_this_line(jcommon.build_vim(vim))<CR>

"map <C-O> :py reload(jinteractive); jinteractive.generic_open(vim)<CR>

map <C-H> :py reload(jinteractive); reload(jcommon); jinteractive.find_arg(jcommon.build_vim(vim), -1)<CR>
map <C-L> :py reload(jinteractive); reload(jcommon); jinteractive.find_arg(jcommon.build_vim(vim), 1)<CR>

"map <C-I> :py jinteractive.clean_unfolding(vim)<CR>

  "special: grabs url cursor an puts into Win32 clipboard
"map <C-P> <Esc>T vE"*y
"map <C-Q> :call Testing()<CR>      "FAILED

hi! TabLineSel term=bold,reverse,bold ctermfg=Yellow ctermbg=NONE guifg=Yellow guibg=NONE gui=bold


function ProtectText()
    :py jinteractive.protect_text(jcommon.build_vim(vim))
endfunction

function UnProtectText()
    :py jinteractive.unprotect_text(jcommon.build_vim(vim))
endfunction

" =============== the special tabbable C command =============

function C(MainArg, ...)
    " the py function will handle looking at the arguments
    :py reload(jcommon)
    :py jinteractive.c_command(jcommon.build_vim(vim))
endfunction

let g:returning=[]

function! Complete_C(ArgLead, CmdLine, CursorPos)
  let g:returning=[]
  :py reload(jcommon)
  :py jinteractive.c_command_completion(jcommon.build_vim(vim))
  return g:returning
endfunction

:command! -nargs=* -range=% -complete=customlist,Complete_C  C  :call C(<f-args>)


" =============== the special tabbable H command =============

function H(MainArg, ...)
    " the py function will handle looking at the arguments
    :py reload(jcommon)
    :py jinteractive.h_command(jcommon.build_vim(vim))
endfunction

let g:returning=[]

function! Complete_H(ArgLead, CmdLine, CursorPos)
  let g:returning=[]
  :py reload(jcommon)
  :py jinteractive.h_command_completion(jcommon.build_vim(vim))
  return g:returning
endfunction

:command! -nargs=* -range=% -complete=customlist,Complete_H  H  :call H(<f-args>)

" =============== the special tabbable Hs command =============

function Hs(MainArg, ...)
    " the py function will handle looking at the arguments
    :py reload(jcommon)
    :py jinteractive.hs_command(jcommon.build_vim(vim))
endfunction

let g:returning=[]

function! Complete_Hs(ArgLead, CmdLine, CursorPos)
  let g:returning=[]
  :py reload(jcommon)
  :py jinteractive.hs_command_completion(jcommon.build_vim(vim))
  return g:returning
endfunction

:command! -nargs=* -range=% -complete=customlist,Complete_Hs  Hs  :call Hs(<f-args>)


" =============== the special tabbable F command =============

function F(MainArg, ...)
    " the py function will handle looking at the arguments
    :py reload(jcommon)
    :py jinteractive.f_command(jcommon.build_vim(vim))
endfunction

function FF(MainArg, ...)
    " the py function will handle looking at the arguments
    :py reload(jcommon)
    :py jinteractive.ff_command(jcommon.build_vim(vim))
endfunction


let g:returning=[]

function! Complete_F(ArgLead, CmdLine, CursorPos)
  let g:returning=[]
  :py reload(jcommon)
  :py jinteractive.f_command_completion(jcommon.build_vim(vim))
  return g:returning
endfunction

:command! -nargs=* -range=% -complete=customlist,Complete_F  F  :call F(<f-args>)

function! Complete_FF(ArgLead, CmdLine, CursorPos)
  let g:returning=[]
  :py reload(jcommon)
  :py jinteractive.ff_command_completion(jcommon.build_vim(vim))
  return g:returning
endfunction

:command! -nargs=* -range=% -complete=customlist,Complete_FF  FF  :call FF(<f-args>)

" =============== the special tabbable F command =============

function FM(MainArg, ...)
    " the py function will handle looking at the arguments
    :py reload(jcommon)
    :py jinteractive.f_command(jcommon.build_vim(vim), memorize_files_only=1)
endfunction

let g:returning=[]

function! Complete_FM(ArgLead, CmdLine, CursorPos)
  let g:returning=[]
  :py reload(jcommon)
  :py jinteractive.f_command_completion(jcommon.build_vim(vim), memorize_files_only=1)
  return g:returning
endfunction

:command! -nargs=* -range=% -complete=customlist,Complete_FM  FM  :call FM(<f-args>)




" =============== the special tabbable S command =============

function S(MainArg, ...)
    " the py function will handle looking at the arguments
    :py reload(jcommon)
    :py s_dispatch.s_dispatch(jcommon.build_vim(vim))
endfunction

let g:returning=[]

function! Complete_S(ArgLead, CmdLine, CursorPos)
  let g:returning=[]
  :py reload(jcommon)
  :py s_dispatch.s_dispatch_completion(jcommon.build_vim(vim))
  return g:returning
endfunction

:command! -nargs=* -range=% -complete=customlist,Complete_S  S  :call S(<f-args>)

":setlocal omnifunc=pysmell#Complete

":py import os; os.environ["GOODVIM"] = "true"

let g:completion_exception = ''
let g:completion_message   = ''


:py import os; os.environ["INSIDE_VIM"] = "true"

fun! SmartComplete(findstart, base)
  if a:findstart
    let line = getline('.')
    let start = col('.') - 1

    "while start>0 && line[start-1] =~ '\a'
    "while start>0 && line[start-1] =~ '\a'
    if line =~ "_full__ARG"
        while start>0 && line[start-1] =~ "[^'\"]"    "allow * for wildcarding
            let start -= 1
        endwhile
    else
        while start>0 && line[start-1] =~ '[a-zA-Z_0-9*!./^#?`:]' "allow * for wildcarding
            let start -= 1
        endwhile
    endif
    return start
  else
      let g:completion_exception = ''
      let g:returning=[]
      let g:line_around = getline('.')
      let g:complete_findstart = a:findstart
      let g:complete_base = a:base
      :python from hsdl.vim import autocomplete
      :python from hsdl.vim import jcommon
      :python reload(autocomplete); reload(jcommon)
      :py autocomplete.complete(jcommon.build_vim(vim))

      return g:returning
  endif
endfun
:set completefunc=SmartComplete


fun! KeywordComplete(findstart, base)
  if a:findstart
    let line = getline('.')
    let start = col('.') - 1

    "while start>0 && line[start-1] =~ '\a'
    while start>0 && line[start-1] =~ '[a-zA-Z_0-9*!#.:-]' "allow * for wildcarding
        let start -= 1
    endwhile
    return start
  else
      let g:returning=[]
      let g:complete_findstart = a:findstart
      let g:complete_base = a:base
      :python from hsdl.vim import autocomplete
      :python from hsdl.vim import jcommon
      :python reload(autocomplete); reload(jcommon)
      :py autocomplete.keyword_complete(jcommon.build_vim(vim))

      return g:returning
  endif
endfun


au BufRead,BufNewFile *.mind set omnifunc=KeywordComplete
au BufRead,BufNewFile *.scala set omnifunc=KeywordComplete
au BufRead,BufNewFile *.m set omnifunc=KeywordComplete
au BufRead,BufNewFile *.clj set omnifunc=KeywordComplete
au BufRead,BufNewFile *.rkt set omnifunc=KeywordComplete
"au BufRead,BufNewFile *.py set omnifunc=KeywordComplete
au BufRead,BufNewFile *.lfe set omnifunc=KeywordComplete
au BufRead,BufNewFile *.erl set omnifunc=KeywordComplete
au BufRead,BufNewFile *.ts set omnifunc=KeywordComplete

set backspace=indent,eol,start

" ---- color for auto complete menu
highlight PMenu      cterm=bold ctermbg=DarkBlue ctermfg=White guibg=DarkBlue guifg=White
highlight PMenuSel   cterm=bold ctermbg=Green ctermfg=White guibg=DarkGreen guifg=White


set completeopt=longest,menuone,preview
inoremap <expr> <CR> pumvisible() ? "\<C-y>" : "\<C-g>u\<CR>"
inoremap <expr> <C-n> pumvisible() ? '<C-n>' : '<C-n><C-r>=pumvisible() ? "\<lt>Down>" : ""<CR>'

inoremap <expr> <M-,> pumvisible() ? '<C-n>' : '<C-x><C-o><C-n><C-p><C-r>=pumvisible() ? "\<lt>Down>" : ""<CR>'


" -------------- for j ---------------
" my filetype file
if exists("did_load_filetypes")
  "finish
endif
augroup filetypedetect
  au! BufRead,BufNewFile *.ijs,*.ijt,*.ijp,*.ijx        setfiletype j
augroup END

set encoding=utf-8
set termencoding=utf-8


set <a-j>=^[j

set tabline=tabline-layout

function ShortTabLine()
    let ret = ''
    for i in range(tabpagenr('$'))
        if i + 1 == tabpagenr()
            let ret .= '%#errorMsg#'
        else
            let ret .= '%#TabLine#'
        endif

        let buflist = tabpagebuflist(i+1)
        let winnr = tabpagewinnr(i+1)
        let buffername = bufname(buflist[winnr-1])
        let filename = fnamemodify(buffername, ':t')
        if filename == ''
            let filename = 'noname'
        endif
        if strlen(filename) >= 16
            "let ret  .= '[' . filename[0:13] . '>]'
            let ret  .= ' ' . filename[0:13] . '>'
        else
            "let ret .= '[' . filename . ']'
            let ret .= ' ' . filename
        endif
    endfor

    return ret
endfunction

set tabline=%!ShortTabLine()

set statusline=%<[%02n]\ %F%(\ %m%h%w%y%r%)\ %a%=\ %8l,%c%V/%L\ (%P)\ [%08O:%02B]


set showtabline=2           "show the table line even if only one file is open


" --------- running compilations
function LangAction(langCommand)
    :py reload(jinteractive); reload(jcommon); jinteractive.c_command_emulate(jcommon.build_vim(vim), vim.eval("a:langCommand"))
endfunction

:map _cc :call LangAction('compile')<CR>
:map _cr :call LangAction('run')<CR>
:map _ci :call LangAction('interp')<CR>
:map _cd :call LangAction('debug')<CR>
:map _cb :call LangAction('build')<CR>

:map _ca :py reload(jinteractive); reload(jcommon); jinteractive.show_actions(jcommon.build_vim(vim))<cr>

:map _cs :py reload(jinteractive); reload(jcommon); jinteractive.scheme_indent(jcommon.build_vim(vim))<CR>

:map _0 :call LangAction('close_errors')<cr>

:map _u :py reload(jinteractive); reload(jcommon); jinteractive.command_on_other_buffer(jcommon.build_vim(vim), cmd='undo')<cr>
:map _<C-R> :py reload(jinteractive); reload(jcommon); jinteractive.command_on_other_buffer(jcommon.build_vim(vim), cmd='redo')<cr>
:map _r :py reload(jinteractive); reload(jcommon); jinteractive.command_on_other_buffer(jcommon.build_vim(vim), cmd='redo')<cr>
:map _. :py from hsdl.vim import jcommon; reload(jcommon); jcommon.build_vim(vim).jumpToFirstErrorInFile()<cr>

:map _t :py reload(jinteractive); reload(jcommon); jinteractive.toggle_buffer(jcommon.build_vim(vim))<cr>
:map _^ :py reload(jinteractive); reload(jcommon); jinteractive.toggle_buffer(jcommon.build_vim(vim))<cr>
:map _T :py reload(jinteractive); reload(jcommon); jinteractive.toggle_buffer(jcommon.build_vim(vim), switch_tab=1)<cr>
:map <C-^> :py reload(jinteractive); reload(jcommon); jinteractive.toggle_buffer(jcommon.build_vim(vim), switch_tab=0)<cr>

" NOTE: C-@ is usable; can use it to toggle between 3 files
map <C-@> :py reload(jinteractive); reload(jcommon); jinteractive.toggle_buffer_of_three(jcommon.build_vim(vim))<cr>
map ,,@ :py reload(jinteractive); reload(jcommon); jinteractive.mark_buffer_switch_of_three(jcommon.build_vim(vim))<cr>

" -------- going to definitions
function LangGoto(langTag)
    :py reload(jinteractive); reload(jcommon); jinteractive.c_command_emulate(jcommon.build_vim(vim), vim.eval("a:langTag"))
endfunction

:map _gj :call LangGoto('goto_func_j')<cr>
:map _gg :call LangGoto('goto_func')<cr>
:map _gp :call LangGoto('goto_func_py')<cr>
:map _ge :call LangGoto('goto_func_erl')<cr>
:map _gs :call LangGoto('goto_func_scala')<cr>
:map _gz :call LangGoto('goto_func_scheme')<cr>

:map g0 :py from hsdl.vim import jcommon; reload(jinteractive); reload(jcommon); jcommon.build_vim(vim).go_to_opened_buffer(pos=0)<cr>
:map g^ :py from hsdl.vim import jcommon; reload(jinteractive); reload(jcommon); jcommon.build_vim(vim).go_to_opened_buffer(pos=0)<cr>
:map g$ :py from hsdl.vim import jcommon; reload(jinteractive); reload(jcommon); jcommon.build_vim(vim).go_to_opened_buffer(pos=-1)<cr>

" ========================================================================================================================
" ===================================== J SHORTCUTS ======================================================================
" ========================================================================================================================

:map -j0 :H lang j :spaced<cr>
:map -j1 :H snip prep<CR>
:map -j2 :H snip lookup<cr>

:map -Jr :H jread<cr>
:map \r :H jread<CR>
:map <F9> :H jread<CR>

:map -Jw :H jwrite<cr>
:map \w :H jwrite<cr>
"F10 does not work under gnome-terminal
":map <F10> :H jwrite<CR>

:map -Jh :H jhistory<cr>
:map \h :H jhistory<cr>
:map <F11> :H jhistory<CR>

:map -Jx :H jdump<cr>
:map \x :H jdump<cr>
:map <F12> :H jdump<CR>

:map -JX :H jdumpall<cr>
:map \X :H jdumpall<cr>

:map -Je :H jerase<cr>
:map \e :H jerase<cr>

:map -Jf :H jdef<cr>
:map \f :H jdef<cr>


" ========================================================================================================================
" ===================================== J ================================================================================
" ========================================================================================================================


:map -jb :py reload(jinteractive); reload(jcommon); jinteractive.c_command_emulate(jcommon.build_vim(vim), 'build_wip')<cr>
:map -jB :py reload(jinteractive); reload(jcommon); jinteractive.c_command_emulate(jcommon.build_vim(vim), 'build_wip_force')<cr>
:map -jc :py reload(jinteractive); reload(jcommon); jinteractive.get_j_code(jcommon.build_vim(vim))<cr>
:map -jd :py reload(jinteractive); reload(jcommon); jinteractive.get_j_data(jcommon.build_vim(vim))<cr>
:map -jD :py reload(jinteractive); reload(jcommon); jinteractive.get_j_data_visualize(jcommon.build_vim(vim), special=1)<cr>
:map -jj :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), force_new_window=1)<cr>
:map -jv :py reload(jinteractive); reload(jcommon); jinteractive.get_j_data_visualize(jcommon.build_vim(vim), special=0)<cr>
:map -jV :py reload(jinteractive); reload(jcommon); jinteractive.visualize_formatted_data(jcommon.build_vim(vim))<cr>
:map -ji :py reload(jinteractive); reload(jcommon); jinteractive.get_j_info(jcommon.build_vim(vim))<cr>
:map -jm :py reload(jinteractive); reload(jcommon); jinteractive.get_j_map(jcommon.build_vim(vim))<cr>
:map -jg :py reload(jinteractive); reload(jcommon); jinteractive.get_j_goto_file(jcommon.build_vim(vim))<cr>
:map -js :py reload(jinteractive); reload(jcommon); jinteractive.get_j_goto_file(jcommon.build_vim(vim), go_to_script=1)<cr>
:map -jH :py from hsdl.vim import vim_commands_j; reload(vim_commands_j); reload(jcommon); vim_commands_j.helpj(jcommon.build_vim(vim), ())<CR>

"----- NOTE: you can use '\' as a leader, but note that \a is already taken
":imap \? :py from hsdl.vim import autocomplete; reload(autocomplete); reload(jcommon); vim.command("let g:complete_findstart=''"); vim.command("let g:complete_base=''"); autocomplete.complete(jcommon.build_vim(vim))<CR><CR>
:imap <C-\> <esc>:py from hsdl.vim import autocomplete; reload(autocomplete); autocomplete.shortcut_quick_search(vim)<CR>

:map \b :py reload(jinteractive); reload(jcommon); jinteractive.c_command_emulate(jcommon.build_vim(vim), 'build_wip')<cr>
:map \B :py reload(jinteractive); reload(jcommon); jinteractive.c_command_emulate(jcommon.build_vim(vim), 'build_wip_force')<cr>
:map \c :py reload(jinteractive); reload(jcommon); jinteractive.get_j_code(jcommon.build_vim(vim))<cr>
:map \d :py reload(jinteractive); reload(jcommon); jinteractive.get_j_data(jcommon.build_vim(vim))<cr>
:map \D :py reload(jinteractive); reload(jcommon); jinteractive.get_j_data_visualize(jcommon.build_vim(vim), special=1)<cr>
:map \j :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), force_new_window=1)<cr>
:map \v :py reload(jinteractive); reload(jcommon); jinteractive.get_j_data_visualize(jcommon.build_vim(vim), special=0)<cr>
:map \V :py reload(jinteractive); reload(jcommon); jinteractive.visualize_formatted_data(jcommon.build_vim(vim))<cr>
:map \i :py reload(jinteractive); reload(jcommon); jinteractive.get_j_info(jcommon.build_vim(vim))<cr>
:map \m :py reload(jinteractive); reload(jcommon); jinteractive.get_j_map(jcommon.build_vim(vim))<cr>
:map \g :py reload(jinteractive); reload(jcommon); jinteractive.get_j_goto_file(jcommon.build_vim(vim))<cr>
:map \s :py reload(jinteractive); reload(jcommon); jinteractive.get_j_goto_file(jcommon.build_vim(vim), go_to_script=1)<cr>
":map \h :py from hsdl.vim import vim_commands_j; reload(vim_commands_j); reload(jcommon); vim_commands_j.helpj(jcommon.build_vim(vim), ())<CR>

" ========================================================================================================================
" ========================================================================================================================

:map -zz :py from hsdl.vim import racket_test; reload(racket_test); reload(jcommon); racket_test.script(jcommon.build_vim(vim))<CR>


function InsertCodeSection(langTag)
    :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.insert_code_section(jcommon.build_vim(vim), vim.eval("a:langTag"))
endfunction

:map -zj :call InsertCodeSection('j')<CR>
:map -zb :call InsertCodeSection('bash-short')<CR>
:map -zB :call InsertCodeSection('bash')<CR>
:map -zr :call InsertCodeSection('rkt')<CR>
:map -zl :call InsertCodeSection('lfe')<CR>
:map -zp :call InsertCodeSection('python')<CR>

":map <F5> :py from hsdl.vim import vim_commands_j; reload(vim_commands_j); vim_commands_j.helpj(vim, ())<CR>
":map <F6> :py from hsdl.vim import vim_commands_python; reload(vim_commands_python); vim_commands_python.helppy(vim, ())<CR>


" ========================================================================================================================
" ===================================== FUTURES ==========================================================================
" ========================================================================================================================

:map -fl :py reload(jinteractive); reload(jcommon); jinteractive.process_future(jcommon.build_vim(vim), action='launch')<cr>
:map -f? :py reload(jinteractive); reload(jcommon); jinteractive.process_future(jcommon.build_vim(vim), action='query')<cr>
:map -fv :py reload(jinteractive); reload(jcommon); jinteractive.process_future(jcommon.build_vim(vim), action='view')<cr>

" -- shorter shortcuts for futures
:map -1 :py reload(jinteractive); reload(jcommon); jinteractive.process_future(jcommon.build_vim(vim), action='launch')<cr>
:map -2 :py reload(jinteractive); reload(jcommon); jinteractive.process_future(jcommon.build_vim(vim), action='query')<cr>
:map -3 :py reload(jinteractive); reload(jcommon); jinteractive.process_future(jcommon.build_vim(vim), action='view')<cr>

":map _fv :py reload(jinteractive); jinteractive.view_future(vim)<cr>
":map _fc :py reload(jinteractive); jinteractive.check_futures_delegate(vim)<cr>

" ========================================================================================================================


"-- convert table from clipboard
:map _jt :py reload(jinteractive); reload(jcommon); jinteractive.table_to_vim(jcommon.build_vim(vim))<cr>

" -------- special shortcuts for handling table representations
:map _dj  :py reload(jinteractive); reload(jcommon); jinteractive.vimsendjdata(jcommon.build_vim(vim))<CR>
:map _ds  :py reload(jinteractive); reload(jcommon); jinteractive.vimsend_sisc_data(jcommon.build_vim(vim))<CR>
:map _df  :py reload(jinteractive); reload(jcommon); jinteractive.format_display(jcommon.build_vim(vim))<CR>


" -------- special shortcuts for handling types
:map _sc  :py reload(jinteractive); reload(jcommon); jinteractive.scala_complete(jcommon.build_vim(vim))<CR>
:map _st  :py reload(jinteractive); reload(jcommon); jinteractive.scala_type_at(jcommon.build_vim(vim))<CR>


" ********************** executing in different languages *********************
:map !j  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='ijs')<CR>
:map !uj  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='ijs', force_new_window=True)<CR>

:map !e  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='erl')<CR>
:map !ue  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='erl', force_new_window=True)<CR>

:map !s  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='scala')<CR>
:map !us  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='scala', force_new_window=True)<CR>

:map !l  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='lfe')<CR>
:map !ul  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='lfe', force_new_window=True)<CR>

:map !l  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='lfe')<CR>
:map !ul  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='lfe', force_new_window=True)<CR>

:map !z  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='scm')<CR>
:map !uz  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim), ext='scm', force_new_window=True)<CR>

:map <F1> :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.execute_code(jcommon.build_vim(vim), ())<CR>
:map -rx :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.execute_code(jcommon.build_vim(vim), ())<CR>

:map <F2>  :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.execute_completion(jcommon.build_vim(vim), ())<CR>
:map -rc :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.execute_completion(jcommon.build_vim(vim), ())<CR>

:map <F3>  :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.check_jump_to_definition(jcommon.build_vim(vim), ())<CR>
:map -rj :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.check_jump_to_definition(jcommon.build_vim(vim), ())<CR>

:map <F4>  :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.rackanalyze(jcommon.build_vim(vim), ()); reload(jinteractive); jinteractive.redraw_screen(jcommon.build_vim(vim))<CR>
:map -ra :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.rackanalyze(jcommon.build_vim(vim), ()); reload(jinteractive); jinteractive.redraw_screen(jcommon.build_vim(vim))<CR>

":map <F5>  :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.racktypes(jcommon.build_vim(vim), ()); reload(jinteractive); jinteractive.redraw_screen(jcommon.build_vim(vim))<CR>
:map -rt :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.racktypes(jcommon.build_vim(vim), ()); reload(jinteractive); jinteractive.redraw_screen(jcommon.build_vim(vim))<CR>

:map <F6>  :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.execute_pattern_match(jcommon.build_vim(vim), ())<CR>
:map -rp :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.execute_pattern_match(jcommon.build_vim(vim), ())<CR>

":map <F7> :py reload(jinteractive); reload(jcommon); jinteractive.do_autoload(jcommon.build_vim(vim))<CR>
:map \a :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.autoload(jcommon.build_vim(vim))<CR>
:map \A :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.autoload(jcommon.build_vim(vim), 'close_all')<CR>
":map -rA :py reload(jinteractive); reload(jcommon); jinteractive.do_autoload(jcommon.build_vim(vim))<CR>

:map -rl :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.as_lfe(jcommon.build_vim(vim), ())<CR>

":map <F4>  :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); vim_commands_racket.check_type(vim, ())<CR>

:map -u  :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.test(jcommon.build_vim(vim), ())<CR>
"imap <C-Space> <esc>:silent! py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.test(jcommon.build_vim(vim), ())<CR>
imap <C-Space> <esc>:py from hsdl.vim import zcomplete; reload(zcomplete); zcomplete.begin_zcomplete(jcommon.build_vim(vim), adjust=1)<CR>
:map ,+ :py from hsdl.vim import zcomplete; reload(zcomplete); zcomplete.begin_zcomplete(jcommon.build_vim(vim), adjust=1)<CR>
:map ?<Space> :py from hsdl.vim import zcomplete; reload(zcomplete); zcomplete.begin_zcomplete(jcommon.build_vim(vim), diagnostic=1)<CR>
:map ?? :py from hsdl.vim import vim_commands_typescript; reload(vim_commands_typescript); vim_commands_typescript.typescript_get_type(jcommon.build_vim(vim))<CR>
:map ?g :py from hsdl.vim import vim_commands_typescript; reload(vim_commands_typescript); vim_commands_typescript.typescript_goto_definition(jcommon.build_vim(vim))<CR>
:map ?! :py from hsdl.vim import vim_commands_typescript; reload(vim_commands_typescript); vim_commands_typescript.typescript_check_errors(jcommon.build_vim(vim))<CR>
imap <C-@> <C-Space>

":map <F10>  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.kill_socket_call(vim, ())<CR>
":map <F11>  :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); vim_commands_racket.rackhelp(vim, ())<CR>
:map <F8> :py reload(jinteractive); reload(jcommon); jinteractive.redraw_screen(jcommon.build_vim(vim))<CR>

"map <F9> :py reload(jinteractive); jinteractive.sign_next(vim)<CR>

"map <F8> :py from hsdl.vim import vim_common; reload(vim_common); vim_common.clear_undo(vim)<CR>

"map <F12> :py reload(jinteractive); jinteractive.lfe_wait_stop(vim)<CR>

"map <F10> :py reload(jinteractive); jinteractive.sign_prev(vim)<CR>
" map <F12> :py reload(jinteractive); jinteractive.hier_goto(vim)<CR>

"map <F5> :py reload(jinteractive); jinteractive.temp(vim)<CR>

" the following is complex, but every keystroke is needed to make it work
imap <F11> <space><space><ESC>h:py reload(jinteractive); reload(jcommon); jinteractive.trigger_snippet(jcommon.build_vim(vim))<CR>
"map <F12> :py reload(jinteractive); jinteractive.hier_goto(vim)<CR>


":map --  :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); vim_commands_racket.check_source(vim, ())<CR>

function MarkPriority(priority)
    :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon);
    :py vim_commands.priority(jcommon.build_vim(vim), 'mark', str(vim.eval("a:priority")))
endfunction

:map -=1  :call MarkPriority(1)<CR>
:map -=2  :call MarkPriority(2)<CR>
:map -=3  :call MarkPriority(3)<CR>
:map -=4  :call MarkPriority(4)<CR>
:map -=5  :call MarkPriority(5)<CR>
:map -=6  :call MarkPriority(6)<CR>
:map -=7  :call MarkPriority(7)<CR>
:map -=8  :call MarkPriority(8)<CR>
:map -=9  :call MarkPriority(9)<CR>
:map -=0  :call MarkPriority(10)<CR>


" ********* more shortcuts =============
:map =b  :C build<CR>
:map =c  :C compile<CR>
:map =d  :C debug<CR>
:map =i  :C interp<CR>
:map =r  :C run<CR>


" --- the following wouldn't be available to work anyway

":map -P  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.prolog(vim, ())<CR>
:map -R  :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.racket_run(jcommon.build_vim(vim), ())<CR>
:map -S  :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.sexp(jcommon.build_vim(vim), ())<CR>

" ------------------- generic handling of s-expressions (clj, chicken, sisc, mzscheme, lfe) -----------------------
:map -#  :py reload(jinteractive); reload(jcommon); jinteractive.process_sexp(jcommon.build_vim(vim))<CR>
:map -?  :py reload(jinteractive); reload(jcommon); jinteractive.get_more_info(jcommon.build_vim(vim))<CR>
:map -f  :py reload(jinteractive); reload(jcommon); jinteractive.describe_function(jcommon.build_vim(vim))<CR>
:map -h  :py reload(jinteractive); reload(jcommon); jinteractive.lisp_hyperspec(jcommon.build_vim(vim))<CR>
:map -H  :py reload(jinteractive); reload(jcommon); jinteractive.lisp_hyperspec(jcommon.build_vim(vim), go_to_first=1)<CR>
:map -!  :py reload(jinteractive); reload(jcommon); jinteractive.disassemble_symbol(jcommon.build_vim(vim))<CR>
":map -s  :py reload(jinteractive); jinteractive.apropos_list_for_emacs(vim)<CR>
:map -l  :py reload(jinteractive); reload(jcommon); jinteractive.lisp_compile_file(jcommon.build_vim(vim), load=1)<CR>
:map -m  :py reload(jinteractive); reload(jcommon); jinteractive.show_action_menu(jcommon.build_vim(vim))<CR>
":map -a  :py reload(jinteractive); jinteractive.auto_run_action(vim)<CR>
:map -D  :py reload(jinteractive); reload(jcommon); jinteractive.fast_show_data(jcommon.build_vim(vim))<CR>
:map -:  :py reload(jinteractive); reload(jcommon); jinteractive.zzzz(jcommon.build_vim(vim))<CR>

:map -+  :py reload(jinteractive); reload(jcommon); jinteractive.process_sexp_parent(jcommon.build_vim(vim))<CR>

":map -o  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.edit(vim)<CR>
map -o :py reload(jinteractive); reload(jcommon); jinteractive.generic_open(jcommon.build_vim(vim))<CR>
map -p :py reload(jinteractive); reload(jcommon); jinteractive.generic_open_paste(jcommon.build_vim(vim), do_load=0)<CR>
map -P :py reload(jinteractive); reload(jcommon); jinteractive.generic_open_paste(jcommon.build_vim(vim), do_load=1)<CR>
map -x :py reload(jinteractive); reload(jcommon); jinteractive.generic_exec(jcommon.build_vim(vim), new_window=0)<CR>
map -X :py reload(jinteractive); reload(jcommon); jinteractive.generic_exec(jcommon.build_vim(vim), new_window=1)<CR>
map -O :py reload(jinteractive); reload(jcommon); jinteractive.generic_open_location(jcommon.build_vim(vim), new_window=1)<CR>
":map -p  :py reload(jinteractive); jinteractive.sexp_popup(vim)<CR>

:map -<C-N>  :py reload(jinteractive); reload(jcommon); jinteractive.insert_pattern_match_next(jcommon.build_vim(vim))<CR>
:map -<C-P>  :py reload(jinteractive); reload(jcommon); jinteractive.insert_pattern_match_previous(jcommon.build_vim(vim))<CR>

:map -tk  :py reload(jinteractive); reload(jcommon); jinteractive.transpose_sexp_before(jcommon.build_vim(vim))<CR>
:map -tj  :py reload(jinteractive); reload(jcommon); jinteractive.transpose_sexp_after(jcommon.build_vim(vim))<CR>
:map -_  :py reload(jinteractive); reload(jcommon); jinteractive.vimcallj(jcommon.build_vim(vim))<CR>
:map -*  :py reload(jinteractive); reload(jcommon); jinteractive.sexp_completion(jcommon.build_vim(vim))<CR>
:map -&  :py reload(jinteractive); reload(jcommon); jinteractive.sexp_completion(jcommon.build_vim(vim), concise=1)<CR>

:map _-  :py reload(jinteractive); reload(jcommon); jinteractive.yank_send(jcommon.build_vim(vim))<CR>
:map __  :py reload(jinteractive); reload(jcommon); jinteractive.match_yank_send(jcommon.build_vim(vim))<CR>

":map -j  :py reload(jinteractive); jinteractive.vimcallj(vim, by_block=1)<CR>
"
":map -j  :py reload(jinteractive); jinteractive.fast_execute(vim)<CR>
:map -L  :py reload(jinteractive); reload(jcommon); jinteractive.fast_execute(jcommon.build_vim(vim), lang='sisc')<CR>

":map -(  :py reload(jinteractive); reload(jcommon); jinteractive.find_typing_region(jcommon.build_vim(vim), -1)<CR>
":map -)  :py reload(jinteractive); reload(jcommon); jinteractive.find_typing_region(jcommon.build_vim(vim), 1)<CR>

:map -(  :silent! py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); vim_commands_racket.scheme_indent(jcommon.build_vim(vim))<CR>
:map -)  :silent! py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); vim_commands_racket.scheme_indent(jcommon.build_vim(vim))<CR>

:map -[  :py reload(jinteractive); reload(jcommon); jinteractive.find_out_region(jcommon.build_vim(vim), -1)<CR>
:map -]  :py reload(jinteractive); reload(jcommon); jinteractive.find_out_region(jcommon.build_vim(vim), 1)<CR>

:map -"  :py reload(jinteractive); reload(jcommon); jinteractive.highlight_triple_quoted_region(jcommon.build_vim(vim))<CR>
:map -'  :py reload(jinteractive); reload(jcommon); jinteractive.highlight_triple_quoted_region(jcommon.build_vim(vim), trimmed=1)<CR>

:map -do  :py reload(jinteractive); reload(jcommon); jinteractive.clear_out_region(jcommon.build_vim(vim))<CR>

":map -{  :py reload(jinteractive); jinteractive.find_lang_region(vim, -1)<CR>
":map -}  :py reload(jinteractive); jinteractive.find_lang_region(vim, 1)<CR>
:map -<  :py reload(jinteractive); reload(jcommon); jinteractive.find_section_marker(jcommon.build_vim(vim), -1)<CR>
:map ->  :py reload(jinteractive); reload(jcommon); jinteractive.find_section_marker(jcommon.build_vim(vim), 1)<CR>
:map ->  :py reload(jinteractive); reload(jcommon); jinteractive.find_section_marker(jcommon.build_vim(vim), 1)<CR>

" --- moving the current tab around: left or right
:map -{  :call TabLeft()<CR>
:map -}  :call TabRight()<CR>

:map -9  :py reload(jinteractive); reload(jcommon); jinteractive.find_action_marker(jcommon.build_vim(vim)), -1)<CR>
:map -0  :py reload(jinteractive); reload(jcommon); jinteractive.find_action_marker(jcommon.build_vim(vim), 1)<CR>

":map -A  :py reload(jinteractive); jinteractive.new_typing_region(vim)<CR>

:map -T  :py reload(jinteractive); reload(jcommon); jinteractive.testing(jcommon.build_vim(vim))<CR>
:map -~  :py reload(jinteractive); reload(jcommon); jinteractive.quicktest(jcommon.build_vim(vim))<CR>


:map -c  :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.lisp(jcommon.build_vim(vim), 'complete')<CR>
:map -C  :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.lisp(jcommon.build_vim(vim), 'completers')<CR>
:map -e  :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.lisp(jcommon.build_vim(vim), 'eval')<CR>
":map -E  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.lisp(vim, 'eval2')<CR>
"
"
" ----------- have another look at these shortcuts using ? as the leader
":map ??  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.lisp(vim, 'simplify-clean')<CR>
":map ?s  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.lisp(vim, 'simplify')<CR>
":map ?u  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.lisp(vim, 'used')<CR>
":map -a  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.lisp(vim, 'action')<CR>
":map ?a  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.lisp(vim, 'actions')<CR>
":map ?c  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.lisp(vim, 'completers')<CR>
":map -A  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.lisp(vim, 'actions')<CR>
":map ?C  :py reload(jinteractive); jinteractive.interactive_completion(vim)<CR>
" -------------------------------------------------------------------------

":map -P  :py from hsdl.vim import vim_commands; reload(vim_commands); vim_commands.lisp(vim, 'prettify')<CR>
:map -Q  :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.lisp(jcommon.build_vim(vim), 'action-complete')<CR>
:map -@  :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.lisp(jcommon.build_vim(vim), 'pattern')<CR>
:map ,P  :silent! py from hsdl.vim import vim_commands_pg; reload(vim_commands_pg); reload(jcommon); vim_commands_pg.pg(jcommon.build_vim(vim), 'send')<CR>
:map ,p  :silent! py from hsdl.vim import vim_commands_pg; reload(vim_commands_pg); reload(jcommon); vim_commands_pg.pg(jcommon.build_vim(vim), 'send_and_stay')<CR>
:map ,L  :silent! H pg list<CR>

:map ,ka :silent! py from hsdl.vim import vim_commands_pg; reload(vim_commands_pg); reload(jcommon); vim_commands_pg.coa(jcommon.build_vim(vim), 'code')<CR>
:map ,kA :silent! py from hsdl.vim import vim_commands_pg; reload(vim_commands_pg); reload(jcommon); vim_commands_pg.coa(jcommon.build_vim(vim), 'name')<CR>


:map '  :py reload(jinteractive); reload(jcommon); jinteractive.enter_h(jcommon.build_vim(vim))<CR>

" ---- these two not not very flexible; using code from limp -----
"  wrap sexpr in a list
":map -i :call Cursor_push()<CR>[(%a)<ESC>h%i(<ESC>:call Cursor_pop()<CR>
"  unwrap one layer of list
":map -x :call Cursor_push()<CR>[(:call Cursor_push()<CR>%x:call Cursor_pop()<CR>x:call Cursor_pop()<CR>
"  comment
:map -; :py reload(jinteractive); reload(jcommon); jinteractive.sexp_comment(jcommon.build_vim(vim))<CR>
:map -i :py reload(jinteractive); reload(jcommon); jinteractive.sexp_wrap(jcommon.build_vim(vim))<CR>


" -------------------- shortcuts similar to eclipse ----------------------
:map \R :py from hsdl.vim import vim_commands_quick_search; reload(vim_commands_quick_search); reload(jcommon); vim_commands_quick_search.quick_search_files(jcommon.build_vim(vim))<CR>

:map <Space> <PageDown>

" --- symbolic shortcuts
" lambda
:imap `~l  λ
:imap `~L  Λ
" action
:imap `~a  Ⴋ
" completion
:imap `~c  Ⴔ

:imap ``l  λ

:hi TabLineSel guifg=green guibg=green gui=NONE ctermfg=green ctermbg=green cterm=NONE
:hi TabLineFill guifg=green guibg=NONE gui=NONE ctermfg=green ctermbg=None cterm=underline
:hi TabLine guifg=green guibg=NONE gui=NONE ctermfg=green ctermbg=None cterm=underline


"allow toggling when switching between different buffers"
au BufEnter * :py reload(jinteractive); jinteractive.mark_buffer_switch(jcommon.build_vim(vim))
:autocmd FocusLost * wall

let vimclojure#NailgunClient = "/tmp/vimclojure-2.1.2/ng"
let clj_want_gorilla = 1


function! PostProcSnippet(snippet)
python << EOF
if 1:
    import vim
    import string
    from hsdl.vim import jcommon

    s = jcommon.postProcSnippet(vim.eval("a:snippet"))
    s = string.replace(s, "'", "''")
    vim.command("let g:ppSnippet='" + s + "' ")
EOF
endfunction


"let g:EclimQuickfixErrorsOnly="1"

" highlights in red if line is > 80 chars
let mercury_no_highlight_overlong = 1       " this comes from ~/.vim/syntax/mercury.vim

au BufRead,BufNewFile *.clj set autoindent
au BufRead,BufNewFile *.clj set lisp
au BufRead,BufNewFile *.scm set autoindent
au BufRead,BufNewFile *.scm set lisp
au BufRead,BufNewFile *.lisp set autoindent
au BufRead,BufNewFile *.lisp set lisp
au BufRead,BufNewFile *.lfe set autoindent
au BufRead,BufNewFile *.lfe set lisp
au BufRead,BufNewFile *.rkt set autoindent
au BufRead,BufNewFile *.rkt set lisp
au BufRead,BufNewFile *.rkt set filetype=lisp

:py reload(jinteractive); reload(jcommon); jinteractive.check_for_repgen(jcommon.build_vim(vim))

:py reload(jinteractive); reload(jcommon); jinteractive.check_for_automation(jcommon.build_vim(vim))

" -------- highlight current line ----------
":hi CursorLine   cterm=NONE ctermbg=darkgreen ctermfg=white guibg=darkgreen guifg=black
":hi CursorColumn cterm=NONE ctermbg=darkgreen ctermfg=white guibg=darkgreen guifg=black
""""":hi CursorLine   cterm=NONE ctermbg=blue ctermfg=yellow guibg=blue guifg=yellow
":hi CursorColumn cterm=NONE ctermbg=red ctermfg=red guibg=red guifg=red
":nnoremap <Leader>c :set cursorline! cursorcolumn!<CR>
":set cursorline



"inoremap <expr> <Esc>      pumvisible() ? "\<C-e>" : "\<Esc>"
"inoremap <expr> <CR>       pumvisible() ? "\<C-y>" : "\<CR>"
"inoremap <expr> <Down>     pumvisible() ? "\<C-n>" : "\<Down>"
"inoremap <expr> <Up>       pumvisible() ? "\<C-p>" : "\<Up>"
"inoremap <expr> <PageDown> pumvisible() ? "\<PageDown>\<C-p>\<C-n>" : "\<PageDown>"
"inoremap <expr> <PageUp>   pumvisible() ? "\<PageUp>\<C-p>\<C-n>" : "\<PageUp>"
":set scrolloff=999
"


function! CheckCursorMoved()
python << EOF
if 1:
    jinteractive.snippets_cursor_moved(jcommon.build_vim(vim))
EOF
endfunction


function! CheckCursorMovedForQuickSearch()
python << EOF
if 1:
    from hsdl.vim import qs_utils
    reload(qs_utils)
    qs_utils.quick_search_cursor_moved(jcommon.build_vim(vim))
EOF
endfunction


function! UnsetCheckCursorMovedForQuickSearch()
    au! CursorMovedI
    iunmap <tab>
    iunmap <s-tab>
    sunmap <tab>
    sunmap <s-tab>

    unmap <C-P>
    unmap <C-N>
    iunmap <C-P>
    iunmap <C-N>

    unmap <+>
    iunmap <+>
    unmap <ENTER>
    iunmap <ENTER>

    sunmap <C-D>
    nunmap <C-D>
    iunmap <C-D>

    "au! InsertEnter
    :py from hsdl.vim import qs_utils
    :py reload(qs_utils)
    :py qs_utils.quick_search_exit(jcommon.build_vim(vim))
endfunction


function! UnsetCheckCursorMoved()
    au! CursorMovedI
    sunmap <tab>
    iunmap <tab>
    sunmap <enter>
    iunmap <enter>
    sunmap <s-tab>
    iunmap <s-tab>

    "au! InsertEnter
    :py reload(jinteractive)
    :py jinteractive.snippets_exit(jcommon.build_vim(vim))
endfunction


function! SetCheckCursorMoved()
    au CursorMovedI * call CheckCursorMoved()
endfunction


function! SetCheckCursorMovedForQuickSearch()
    au CursorMovedI * call CheckCursorMovedForQuickSearch()
endfunction

:autocmd BufWinLeave * :py from hsdl.vim import jcommon; reload(jcommon); jcommon.clear_global_state(jcommon.build_vim(vim))

if has("multi_byte")
  if &termencoding == ""
    let &termencoding = &encoding
  endif
  set encoding=utf-8
  setglobal fileencoding=utf-8 bomb
  set fileencodings=ucs-bom,utf-8,latin1
endif

" -------------------------
:py reload(jinteractive); jinteractive.initialize(jcommon.build_vim(vim))
au BufRead,BufNewFile *.mind :py jinteractive.initialize_after_first_load(jcommon.build_vim(vim))
au BufRead,BufNewFile *.log,*.LOG :py jinteractive.initialize_after_first_load(jcommon.build_vim(vim))

"set sessionoptions=buffers,curdir,folds,help,resize,winpos,winsize,tabpages,localoptions
set sessionoptions=curdir,folds,help,resize,winpos,winsize,tabpages

"set balloonexpr=Balloon()
"set balloondelay=400
"set ballooneval

"function! Balloon()
"python << EOF
"if 1:
"    import random
"    return str(random.random())
"EOF
"endfunction

function! Balloon()
  let g:balloon_returning=""
  :py from hsdl.vim import jcommon; jcommon.handle_balloon(jcommon.build_vim(vim))
  return g:balloon_returning
endfunction


"===== to allow autoreload of ~/vimrc upon modification
"----- but issues when redefining functions
"if has("autocmd")
"    autocmd bufwritepos .vimrc source $MYVIMRC
"endif


let g:autoclose_on = 1

au VimLeave *.scala :py reload(jinteractive); reload(jcommon); jinteractive.on_vim_leave(jcommon.build_vim(vim))
au VimLeave *.log,*.LOG :py reload(jinteractive); reload(jcommon); jinteractive.on_vim_leave(jcommon.build_vim(vim))

:py from hsdl.vim import vim_commands_pg; reload(vim_commands_pg); vim_commands_pg.register_open_handler()
:py reload(jcommon); jcommon.register_open_handlers()


" Start NERDTree
"autocmd VimEnter * NERDTree
" Go to previous (last accessed) window.
autocmd VimEnter * wincmd p
set formatprg=par\ -w100
"set number

" ----- cause .vimrc to be reload if you changed and save the .vimrc file
"if has("autocmd")
"    autocmd BufWritePost .vimrc source $MYVIMRC
"endif

command! -nargs=0 -bar Qargs execute 'args' QuickfixFilenames()
function! QuickfixFilenames()
  " Building a hash ensures we get each buffer only once
  let buffer_numbers = {}
  for quickfix_item in getqflist()
    let buffer_numbers[quickfix_item['bufnr']] = bufname(quickfix_item['bufnr'])
  endfor
  return join(map(values(buffer_numbers), 'fnameescape(v:val)'))
endfunction

highlight LineNr ctermfg=white ctermbg=blue
highlight LineNr guifg=white guibg=blue

" --- show coloring if line exceeds 90 chars
if 0
    highlight ColorColumn ctermbg=magenta
    call matchadd('ColorColumn', '\%101v', 100)
endif

" --- remove trailing whitespace on save
"autocmd BufWritePre * :%s/\s\+$//e

function! StripTrailingWhitespace()
  normal mZ
  let l:chars = col("$")
  %s/\s\+$//e
  if (line("'Z") != line(".")) || (l:chars != col("$"))
  endif
  normal `Z
endfunction

autocmd BufWritePre * :call StripTrailingWhitespace()


map ,0 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 0)<CR>
map ,1 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 1)<CR>
map ,2 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 2)<CR>
map ,3 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 3)<CR>
map ,4 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 4)<CR>
map ,5 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 5)<CR>
map ,6 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 6)<CR>
map ,7 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 7)<CR>
map ,8 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 8)<CR>
map ,9 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 9)<CR>
map ,- :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 10)<CR>
map ,= :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.quick_jump_to_tab(jcommon.build_vim(vim), 11)<CR>

map ,,0 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 0)<CR>
map ,,1 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 1)<CR>
map ,,2 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 2)<CR>
map ,,3 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 3)<CR>
map ,,4 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 4)<CR>
map ,,5 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 5)<CR>
map ,,6 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 6)<CR>
map ,,7 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 7)<CR>
map ,,8 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 8)<CR>
map ,,9 :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 9)<CR>
map ,,- :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 10)<CR>
map ,,= :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_quick_jump_by_num(jcommon.build_vim(vim), 11)<CR>

map ,,? :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.list_quick_jumps(jcommon.build_vim(vim))<CR>

" --- execute test
map ,x :py from hsdl.vim import vim_commands_testing; reload(vim_commands_testing); reload(jcommon); vim_commands_testing.testing(jcommon.build_vim(vim))<CR>

map ,X :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.run_last_command_saved(jcommon.build_vim(vim))<CR>
map ,,X :py from hsdl.vim import vim_commands; reload(vim_commands); reload(jcommon); vim_commands.set_last_command_for_quick_run(jcommon.build_vim(vim))<CR>
map ,w :py reload(jcommon); from hsdl.vim import shared; shared.IGNORE_ACTION=True<CR>:w<CR>

function! DeleteHiddenBuffers()
    redir => buffersoutput
    buffers
    redir END
    let buflist = split(buffersoutput,"\n")
    for item in filter(buflist,"v:val[5] == ' '")
            exec 'bdelete ' . item[:2]
    endfor
endfunction

" --- clean buffers
map ,B :call DeleteHiddenBuffers()<cr>


:py import sys; sys.path.insert(0, "/home/hsdl/src/python/prompt_toolkit-0.42")
:py import sys; sys.path.insert(0, "/home/hsdl/src/python/prompt_toolkit-0.37-old/")
:py import sys; sys.path.insert(0, "/home/hsdl/src/python/pgcli-0.17.0")
:py import sys; sys.path.append('/home/hsdl/apps/python-2.7.3/lib/python2.7/site-packages/codegen-1.0-py2.7.egg')
:py import sys; sys.path.append('/home/hsdl/apps/python-2.7.3/lib/python2.7/site-packages/XlsxWriter-0.7.7-py2.7.egg')

:py import sys; sys.path.append('/home/hsdl/apps/python-2.7.3/lib/python2.7/site-packages/v8-0.1.5-py2.7-linux-x86_64.egg')

:xmap ,s :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.send_racket_command(jcommon.build_vim(vim), ())<CR>
:map ,S :py from hsdl.vim import vim_commands_racket; reload(vim_commands_racket); reload(jcommon); vim_commands_racket.send_racket_command_full(jcommon.build_vim(vim), ())<CR>

hi MatchParen cterm=none ctermbg=Black ctermfg=white
"hi MatchParen cterm=none ctermbg=DarkBlue ctermfg=white

set guicursor+=i:blinkwait0

set splitright
map ,? :call PyGenericDisplayMessageFull()<CR>

set shortmess+=I

"make J (join lines) keep cursor position *AND* do not include a space between them
nnoremap J mzgJ`z


" remember last position
if has("autocmd")
      au BufReadPost * if line("'\"") > 1 && line("'\"") <= line("$") | exe "normal! g'\"" | endif
  endif





autocmd BufWritePost *.scala :EnTypeCheck
nnoremap <localleader>t :EnTypeCheck<CR>

