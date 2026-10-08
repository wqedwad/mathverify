#!/bin/bash
# tam_takim.sh <commit> : after birlesik_olc ALLDONE, run full Lean-less pytest in the same copy
C=$1; SP=/tmp/claude-0/-home-user-asd/e165cf01-9b9f-5e2f-87e7-b8341da4ce60/scratchpad
K=$SP/birlesik_$C; O=$SP/olc_$C
until grep -q ALLDONE $O/durum.txt 2>/dev/null; do sleep 20; done
cd $K
export PYTHONUTF8=1 PYTHONPATH=$K/src:$K MATHVERIFY_LEAN_REPL=/nonexistent
timeout 5400 /home/user/asd/.venv/bin/python -m pytest -q -p no:cacheprovider tests -rf > $O/tam.log 2>&1; echo "tam exit $?" >> $O/durum.txt
echo TAMDONE >> $O/durum.txt
