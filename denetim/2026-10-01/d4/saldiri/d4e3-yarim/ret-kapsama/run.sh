#!/bin/bash
# usage: run.sh <copy:new|base> <groups> <tag>
W=/tmp/claude-0/-home-user-asd/e165cf01-9b9f-5e2f-87e7-b8341da4ce60/scratchpad/d4/saldiri/d4e3/ret-kapsama
C=$W/$1
cd $C
PYTHONUTF8=1 PYTHONPATH=$C/src:$C MATHVERIFY_LEAN_REPL=/nonexistent timeout 3000 /home/user/asd/.venv/bin/python $W/sonda_rk.py $W/out_$1_$3.json $2 > $W/log_$1_$3.txt 2>&1
