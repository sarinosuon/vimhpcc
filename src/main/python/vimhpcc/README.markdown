simple tool for testing ECL code on HPCC cluster

Include this in your .vimrc file (set your own keystroke):
:py from hpcc_vim import vim_command
:map \E :vim_command.run_ecl(vim, host='192.168.1.13', port=8010, cluster='thor', popup=True)<CR>

CHANGELOG:

* 0.1.0 -- 2015-08-30 -- initial import into github
