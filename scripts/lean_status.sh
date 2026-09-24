#!/usr/bin/env bash
# Honours ELAN_HOME and MATHVERIFY_LEAN_PROJECT (defaults $HOME/.elan, $HOME/mathverify-lean).
ELAN_HOME="${ELAN_HOME:-$HOME/.elan}"
ELAN_HOME="${ELAN_HOME/#\~/$HOME}"
export ELAN_HOME
export PATH="$ELAN_HOME/bin:$PATH"
echo "elan: $(command -v elan || echo MISSING)"
P="${MATHVERIFY_LEAN_PROJECT:-$HOME/mathverify-lean}"
P="${P/#\~/$HOME}"
echo "project: $P exists=$([ -d "$P" ] && echo yes || echo no)"
[ -d "$P" ] || exit 0
cd "$P"
echo "toolchain: $(cat lean-toolchain 2>/dev/null)"
echo "packages: $(ls .lake/packages 2>/dev/null | tr '\n' ' ')"
echo "mathlib build size: $(du -sh .lake/packages/mathlib/.lake/build 2>/dev/null | cut -f1)"
echo "olean count: $(find .lake/packages/mathlib/.lake/build -name '*.olean' 2>/dev/null | wc -l)"
ls Smoke.lean >/dev/null 2>&1 && echo "smoke file: yes"
echo "--- timing an import Mathlib check ---"
cat > /tmp/smoke2.lean <<'LEAN'
import Mathlib
theorem smoke2 (x : ℝ) (h : x = 2) : x + 2 = 4 := by subst h; norm_num
LEAN
time lake env lean /tmp/smoke2.lean && echo "LEAN CHECK OK"
