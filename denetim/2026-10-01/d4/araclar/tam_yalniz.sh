#!/bin/bash
# tam_yalniz.sh <commit>: full Lean-less pytest in an archive copy (no .git: 4 rule tests fail by design)
C=$1; SP=/tmp/claude-0/-home-user-asd/e165cf01-9b9f-5e2f-87e7-b8341da4ce60/scratchpad
K=$SP/tam_$C; O=$SP/olc_$C; rm -rf $K; mkdir -p $K $O
git -C /home/user/asd archive $C | tar -x -C $K; cd $K
export PYTHONUTF8=1 PYTHONPATH=$K/src:$K MATHVERIFY_LEAN_REPL=/nonexistent
timeout 5400 /home/user/asd/.venv/bin/python -m pytest -p no:cacheprovider tests -q -rf > $O/tam.log 2>&1; echo "tam exit $?" >> $O/durum.txt
cd /; rm -rf $K; echo TAMDONE >> $O/durum.txt
