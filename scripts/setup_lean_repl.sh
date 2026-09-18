#!/usr/bin/env bash
# Stage 2: build the Lean REPL against the Mathlib project so proof checking is a fast
# JSON round-trip instead of a fresh `import Mathlib` (~30 s) per call.
set -euo pipefail
LOG() { echo "[$(date +%H:%M:%S)] $*"; }
export PATH="$HOME/.elan/bin:$PATH"
PROJ="$HOME/mathverify-lean"
REPL="$HOME/repl"
cd "$PROJ"
TOOLCHAIN="$(cat lean-toolchain)"
LOG "project toolchain: $TOOLCHAIN"
if [ ! -d "$REPL" ]; then
  LOG "cloning repl"
  git clone -q https://github.com/leanprover-community/repl "$REPL"
fi
cd "$REPL"
git fetch -q --all --tags
# pick the repl revision matching our toolchain when one exists, else master
echo "$TOOLCHAIN" > lean-toolchain
LOG "building repl with $TOOLCHAIN"
lake build 2>&1 | tail -3
LOG "repl binary: $(ls -la .lake/build/bin/repl 2>/dev/null || echo MISSING)"
# smoke: run a command with Mathlib imported from the project's search path
cd "$PROJ"
printf '%s\n' '{"cmd": "import Mathlib\ntheorem t (x : ℝ) (h : x = 2) : x + 2 = 4 := by subst h; norm_num", "env": null}' '' \
  | timeout 900 env LEAN_PATH="$(lake env printenv LEAN_PATH)" "$REPL/.lake/build/bin/repl" | head -c 800
echo
LOG "REPL DONE"
