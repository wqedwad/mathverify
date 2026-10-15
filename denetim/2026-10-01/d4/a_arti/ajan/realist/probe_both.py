"""Run probe_tb (textbook labels) and probe_units (corpus keys) in one process: args 'tb:<label>' or '<corpus>/<id>'."""
import runpy
import sys

if __name__ == '__main__':
    args = sys.argv[1:]
    tb = [a[3:] for a in args if a.startswith('tb:')]
    un = [a for a in args if not a.startswith('tb:')]
    here = '/tmp/claude-0/-home-user-asd/f97a07bd-dea8-5bbe-88dc-ada419b43e01/scratchpad/wf/realist/'
    if tb:
        sys.argv = [here + 'probe_tb.py'] + tb
        runpy.run_path(here + 'probe_tb.py', run_name='__main__')
    if un:
        sys.argv = [here + 'probe_units.py'] + un
        runpy.run_path(here + 'probe_units.py', run_name='__main__')
