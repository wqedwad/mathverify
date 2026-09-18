#!/usr/bin/env bash
# F5 infrastructure: Lean 4 toolchain + a Mathlib-dependent project with a prebuilt cache.
# Runs inside WSL Ubuntu. Idempotent: safe to re-run.
set -euo pipefail
LOG() { echo "[$(date +%H:%M:%S)] $*"; }

export PATH="$HOME/.elan/bin:$PATH"
if ! command -v elan >/dev/null 2>&1; then
  LOG "installing elan"
  curl -fsSL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -o /tmp/elan-init.sh
  bash /tmp/elan-init.sh -y --default-toolchain none
  export PATH="$HOME/.elan/bin:$PATH"
fi
LOG "elan: $(elan --version)"

PROJ="$HOME/mathverify-lean"
if [ ! -d "$PROJ" ]; then
  LOG "creating project $PROJ"
  cd "$HOME"
  # pin the toolchain Mathlib's master needs; lake will adjust from the manifest
  elan toolchain install stable
  elan default stable
  lake +stable new mathverify-lean math
fi
cd "$PROJ"
LOG "lean: $(lake env lean --version 2>/dev/null || echo '(not yet)')"
LOG "updating mathlib dependency"
lake update -R 2>&1 | tail -5
LOG "toolchain now: $(cat lean-toolchain)"
elan toolchain install "$(cat lean-toolchain)" 2>&1 | tail -2
LOG "fetching prebuilt mathlib cache (this is the slow part)"
lake exe cache get 2>&1 | tail -5
LOG "building"
lake build 2>&1 | tail -5
LOG "smoke test"
cat > Smoke.lean <<'LEAN'
import Mathlib
theorem smoke (x : ℝ) (h : x = 2) : x + 2 = 4 := by subst h; norm_num
LEAN
lake env lean Smoke.lean && LOG "SMOKE OK"
LOG "DONE"
