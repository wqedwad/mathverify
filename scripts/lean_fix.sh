#!/usr/bin/env bash
# Complete a Mathlib install whose prebuilt cache lacks the root Mathlib.olean.
# scripts/setup_lean.sh now does this itself; kept for repairing older installs.
# Honours ELAN_HOME and MATHVERIFY_LEAN_PROJECT (defaults $HOME/.elan, $HOME/mathverify-lean).
ELAN_HOME="${ELAN_HOME:-$HOME/.elan}"
ELAN_HOME="${ELAN_HOME/#\~/$HOME}"
export ELAN_HOME
export PATH="$ELAN_HOME/bin:$PATH"
PROJ="${MATHVERIFY_LEAN_PROJECT:-$HOME/mathverify-lean}"
PROJ="${PROJ/#\~/$HOME}"
cd "$PROJ" || exit 1
free -g | head -2
B=.lake/packages/mathlib/.lake/build/lib/lean
for m in Mathlib Mathlib/Tactic Mathlib/Analysis/SpecialFunctions/Pow/Real Mathlib/Data/Real/Basic; do
  [ -f "$B/$m.olean" ] && echo "have: $m" || echo "MISSING: $m"
done
echo "--- retry cache get (root modules) ---"
lake exe cache get Mathlib 2>&1 | tr '\r' '\n' | grep -vE "^Download|^Decompress" | tail -3
[ -f "$B/Mathlib.olean" ] && { echo "Mathlib.olean now present"; exit 0; }
echo "--- building Mathlib root (loads all oleans) ---"
time lake build Mathlib 2>&1 | tail -5
[ -f "$B/Mathlib.olean" ] && echo "BUILT" || echo "STILL MISSING"
