#!/bin/bash
# Kullanım: araclar/olc.sh <src dizini> <çıktı dizini>
# Denetçilerin bütün tekrar-üretim ve sonda betiklerini <src>'ye karşı koşturur (Lean'siz).
# Sayım: .venv/bin/python araclar/say.py <çıktı dizini>
SRC=$(cd "$1" && pwd); OUT=$2; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
D=$(cd "$(dirname "$0")/.." && pwd)
ROOT=$(cd "$D/../.." && pwd)
PY=${PY:-$ROOT/.venv/bin/python}
export MV_SRC=$SRC MATHVERIFY_LEAN_REPL=/nonexistent PYTHONUTF8=1
run() { # <grup> <dizin> <dosya>
  (cd "$2" && timeout 300 "$PY" "$3" 2>&1 | grep -v "Timeout is disabled"; echo "EXIT ${PIPESTATUS[0]}") > "$OUT/$1__$3.txt"
}
for f in $(cd "$D/A/repro" && ls r*.py); do run A-repro "$D/A/repro" "$f"; done
for f in $(cd "$D/A" && ls p*.py); do run A-sonda "$D/A" "$f"; done
for f in $(cd "$D/B" && ls [CHM]*.py); do run B "$D/B" "$f"; done
for f in $(cd "$D/C" && ls p_*.py repro_*.py); do run C "$D/C" "$f"; done
run D "$D/D" repro_D.py
(cd "$D/E" && IDS=ALL timeout 1800 "$PY" calistir_E.py 2>&1 | grep -v "Timeout is disabled") > "$OUT/E__hepsi.txt"
echo done > "$OUT/DONE"
