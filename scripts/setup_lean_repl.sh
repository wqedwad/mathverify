#!/usr/bin/env bash
# Stage 2: build the pinned Lean REPL against the Mathlib project so proof checking is a fast
# JSON round-trip instead of a fresh `import Mathlib` per call. Run scripts/setup_lean.sh first.
# Works on native Linux (cloud) and inside WSL, as root or as a user. Idempotent.
#
# Environment:
#   ELAN_HOME                 elan home (default $HOME/.elan)
#   MATHVERIFY_LEAN_PROJECT   Mathlib project directory (default $HOME/mathverify-lean)
#   MATHVERIFY_LEAN_REPL      REPL binary (default $HOME/repl/.lake/build/bin/repl); the REPL
#                             checkout is the part before /.lake/build/bin/repl
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lean/PINS
. "$ROOT/lean/PINS"

T0=$(date +%s)
LOG() { echo "[$(date +%H:%M:%S) +$(( $(date +%s) - T0 ))s] $*"; }
die() { LOG "ERROR: $*" >&2; exit 1; }
STEP_NAME=""
STEP_T0=$T0
step() { STEP_NAME="$1"; STEP_T0=$(date +%s); LOG "== $1"; }
step_done() { LOG "== $STEP_NAME: done in $(( $(date +%s) - STEP_T0 ))s"; }

expand_home() {
  case "$1" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s\n' "$HOME/${1#\~/}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

# Run a command with every proxy variable pointing at a closed local port, so a toolchain
# download attempt fails instead of silently fetching (the toolchain is installed by setup_lean.sh
# and the REPL has no dependencies).
offline() {
  local p=http://127.0.0.1:9
  env HTTPS_PROXY=$p https_proxy=$p HTTP_PROXY=$p http_proxy=$p ALL_PROXY=$p all_proxy=$p \
    NO_PROXY= no_proxy= "$@"
}

export ELAN_HOME
ELAN_HOME="$(expand_home "${ELAN_HOME:-$HOME/.elan}")"
export PATH="$ELAN_HOME/bin:$PATH"
PROJ="$(expand_home "${MATHVERIFY_LEAN_PROJECT:-$HOME/mathverify-lean}")"
REPL_BIN="$(expand_home "${MATHVERIFY_LEAN_REPL:-$HOME/repl/.lake/build/bin/repl}")"
case "$REPL_BIN" in
  */.lake/build/bin/repl) REPL_DIR="${REPL_BIN%/.lake/build/bin/repl}" ;;
  *) die "MATHVERIFY_LEAN_REPL must end in /.lake/build/bin/repl (got $REPL_BIN)" ;;
esac

LOG "setup_lean_repl: $(uname -srm), $(nproc) CPU(s), user $(id -un 2>/dev/null || id -u)"
LOG "ELAN_HOME=$ELAN_HOME PROJECT=$PROJ REPL=$REPL_DIR"
command -v elan >/dev/null 2>&1 || die "elan not found in $ELAN_HOME/bin; run scripts/setup_lean.sh first"
[ -f "$PROJ/lean-toolchain" ] || die "$PROJ has no lean-toolchain; run scripts/setup_lean.sh first"
[ "$(cat "$PROJ/lean-toolchain")" = "$LEAN_TOOLCHAIN" ] \
  || die "project toolchain $(cat "$PROJ/lean-toolchain") != pinned $LEAN_TOOLCHAIN"

step "REPL checkout $REPL_URL @ $REPL_REV"
if [ ! -d "$REPL_DIR/.git" ]; then
  mkdir -p "$(dirname "$REPL_DIR")"
  git clone -q "$REPL_URL" "$REPL_DIR"
fi
cd "$REPL_DIR"
if ! git cat-file -e "$REPL_REV^{commit}" 2>/dev/null; then
  LOG "fetching $REPL_URL"
  git fetch -q "$REPL_URL" "$REPL_REV" || git fetch -q "$REPL_URL"
fi
if [ "$(git rev-parse HEAD)" != "$REPL_REV" ]; then
  LOG "checking out $REPL_REV (discarding local changes to tracked files)"
  git checkout -q -f --detach "$REPL_REV"
fi
[ "$(git rev-parse HEAD)" = "$REPL_REV" ] || die "REPL HEAD is not $REPL_REV"
# The pinned REPL revision names a newer toolchain; build it with the project's toolchain.
if [ "$(cat lean-toolchain)" != "$LEAN_TOOLCHAIN" ]; then
  printf '%s\n' "$LEAN_TOOLCHAIN" > lean-toolchain
  LOG "lean-toolchain set to $LEAN_TOOLCHAIN"
fi
step_done

step "lake build (REPL)"
set +e
offline lake build 2>&1 | tr '\r' '\n' | grep --line-buffered -v -E '^[[:space:]]*$' | tail -n 5
rc=${PIPESTATUS[0]}
set -e
[ "$rc" -eq 0 ] || die "lake build of the REPL failed (exit $rc)"
[ -x "$REPL_BIN" ] || die "REPL binary missing: $REPL_BIN"
LOG "repl binary: $REPL_BIN ($(wc -c < "$REPL_BIN") bytes)"
step_done

# As in setup_lean.sh: a root install must stay readable for a session running as another user.
step "permissions"
n="$(find "$REPL_DIR" ! -perm -o+r | wc -l)"
chmod -R a+rX "$REPL_DIR"
LOG "$REPL_DIR: $n entries were not world-readable; now $(find "$REPL_DIR" ! -perm -o+r | wc -l)"
step_done

# Smoke: the same launch the verifier uses (lean_client: cd project && lake env repl), one command
# importing Mathlib and one reusing its environment. Hard failure unless both succeed cleanly.
step "REPL smoke test through lake env"
cd "$PROJ"
set +e
out="$(printf '%s\n\n%s\n\n' \
  '{"cmd": "import Mathlib\ntheorem t (x : ℝ) (h : x = 2) : x + 2 = 4 := by subst h; norm_num"}' \
  '{"cmd": "example : (2 : ℝ) + 2 = 4 := by norm_num", "env": 0}' \
  | offline timeout 900 lake env "$REPL_BIN" 2>&1)"
rc=$?
set -e
printf '%s\n' "${out:0:3000}"
[ "$rc" -eq 0 ] || die "REPL exited with code $rc"
case "$out" in *'"severity": "error"'*) die "REPL reported an error" ;; esac
case "$out" in *'"env": 0'*) ;; *) die "REPL did not return env 0 for the Mathlib command" ;; esac
case "$out" in *'"env": 1'*) ;; *) die "REPL did not return env 1 for the follow-up command" ;; esac
LOG "REPL SMOKE OK"
step_done
LOG "REPL DONE in $(( $(date +%s) - T0 ))s"
