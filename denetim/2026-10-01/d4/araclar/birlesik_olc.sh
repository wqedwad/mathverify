#!/bin/bash
# birlesik_olc.sh <commit> [sondalar...] : combined measurement of a commit in a git-archive copy (Lean-less)
set -u
C=$1; shift
SONDALAR=${*:-d4a d4b d4c d4d d4g}
SP=/tmp/claude-0/-home-user-asd/e165cf01-9b9f-5e2f-87e7-b8341da4ce60/scratchpad
K=$SP/birlesik_$C; O=$SP/olc_$C
rm -rf $K; mkdir -p $K $O; : > $O/durum.txt
git -C /home/user/asd archive $C | tar -x -C $K
cd $K
export PYTHONUTF8=1 PYTHONPATH=$K/src:$K MATHVERIFY_LEAN_REPL=/nonexistent
P=/home/user/asd/.venv/bin/python
( for s in $SONDALAR; do [ -f denetim/2026-10-01/$s/sonda.py ] || continue; timeout 1800 $P denetim/2026-10-01/$s/sonda.py $O/sonda_$s.json > $O/sonda_$s.log 2>&1; echo "sonda $s exit $?" >> $O/durum.txt; done ) &
timeout 2400 $P -m pytest -q -p no:cacheprovider tests/test_d4_*.py tests/test_parca*.py > $O/pytest.log 2>&1; echo "pytest exit $?" >> $O/durum.txt
run() { timeout 900 $P denetim/2026-10-01/fark_parca.py $O/f$1.json $2 $3 > $O/f$1.log 2>&1; echo "f$1 exit $?" >> $O/durum.txt; }
run 1 0 112 & a=$!; run 2 112 224 & b=$!; wait $a $b
run 3 224 336 & a=$!; run 4 336 448 & b=$!; wait $a $b
run 5 448 558
$P denetim/2026-10-01/fark_parca.py merge $O/sonra.json $O/f1.json $O/f2.json $O/f3.json $O/f4.json $O/f5.json >> $O/durum.txt 2>&1
$P /home/user/asd/denetim/2026-09-29/v14/fark.py compare $SP/fark_taban/taban.json $O/sonra.json > $O/fark.txt 2>&1
wait; echo ALLDONE >> $O/durum.txt
