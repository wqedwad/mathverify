#!/bin/bash
# usage: kos.sh <probe.py> <tree: yeni|taban> <out-tag>
W=/tmp/claude-0/-home-user-asd/e165cf01-9b9f-5e2f-87e7-b8341da4ce60/scratchpad/d4/saldiri/d4e3/yanlis-onay
cd $W/$2 && PYTHONUTF8=1 PYTHONPATH=$W/$2/src:$W/$2:$W/p MATHVERIFY_LEAN_REPL=/nonexistent timeout ${TO:-590} /home/user/asd/.venv/bin/python $W/p/$1 $W/p/$3_$2.json > $W/p/$3_$2.out 2>&1
echo "exit $?"
