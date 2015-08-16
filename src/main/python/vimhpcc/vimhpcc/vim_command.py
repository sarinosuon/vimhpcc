import os
import sys
import string
import re
import urllib
import subprocess

import json

DEFAULT_ECLWATCH_HOST="192.168.1.35"
DEFAULT_ECLWATCH_PORT=8010
DEFAULT_ECLWATCH_CLUSTER="thor"

def execute_as_proc(bash_script):
    fname = tempfile.mktemp(".ecl")
    fout = open(fname,'wb')
    fout.write(bash_script)
    fout.close()

    stdin, stdout, stderr  = os.popen3("bash " + fname)
    stdin.close()

    s1 = stdout.read()
    stdout.close()

    s2 = stderr.read()
    stderr.close()

    os.unlink(fname)

    return s1, s2


def get_all_workunits():
    s = urllib.urlopen('http://' + ECLWATCH_HOST + ':' + str(ECLWATCH_PORT) + '/WsWorkunits/WUQuery.json?Wuid=&Owner=&Jobname=&Cluster=&State=&ECL=&LogicalFile=&LogicalFileSearchType=&StartDate=&FromTime=&EndDate=&ToTime=&LastNDays=&PageStartFrom=0&Count=50&rawxml_=true').read()
    o = json.read(s)
    response = o['WUQueryResponse']
    if 'Workunits' in response:
        return [each['Wuid'] for each in response['Workunits']['ECLWorkunit']]
    else:
        return []

def get_cluster_info(vim):
    s = vim.getText()
    pat = re.compile(r'//\s*%ECL_TARGET\s*:\s*(?P<specs>.+)')
    r = pat.search(s)
    if r:
        parts = r.group('specs').strip().split()
        if len(parts) == 3:
            return parts[0], int(parts[1]), parts[2]

    return DEFAULT_ECLWATCH_HOST, DEFAULT_ECLWATCH_PORT, DEFAULT_ECLWATCH_CLUSTER


def run_ecl(vim = None, host='192.168.1.13', port=8010, cluster='thor', popup=True):
    path = vim.current.buffer.name
    stmt = "time scala vimhpcc.HPCC %s  %s %s '%s'"  % (host, port, cluster, path)
    stdout, stderr = execute_as_proc(stmt)
    lines = stderr.split("\n")
    stderr = "\n".join(lines[:-5])
    timing = "\n".join(lines[-5:]).replace("\t", " ")
    if stderr:
        print "="*100
        print "   ERROR:"
        print stderr
        print "="*100
    else:
        print stdout
        print "-"*50

    print timing


