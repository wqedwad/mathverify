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
#   MATHVERIFY_ARTIFACT_DIR   directory filled by scripts/fetch_artifacts.sh; a missing REPL
#                             checkout, or one at another revision, is taken from its
#                             lean-sources archive instead of cloned or fetched
#   MATHVERIFY_LEAN_OFFLINE=1 strict offline mode (scripts/cloud/setup_env.sh always sets it): a
#                             git clone or fetch is refused, so without the archive the script
#                             stops before it writes anything
# A checkout already at REPL_REV is built in place. A new one (from the archive) is built in a
# staging directory next to the final location and swapped in; the previous checkout is deleted
# only after the REPL smoke test passed, and put back otherwise.
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

# Run a command with every proxy variable pointing at a closed local port and git limited to the
# file transport, so a toolchain download or a git fetch fails instead of silently fetching (the
# toolchain is installed by setup_lean.sh and the REPL has no dependencies).
offline() {
  local p=http://127.0.0.1:9
  env HTTPS_PROXY=$p https_proxy=$p HTTP_PROXY=$p http_proxy=$p ALL_PROXY=$p all_proxy=$p \
    NO_PROXY= no_proxy= GIT_ALLOW_PROTOCOL=file "$@"
}

# Strict offline mode: a clone or fetch was about to run. Never call it inside $(...).
refuse_online() {
  die "offline mode (MATHVERIFY_LEAN_OFFLINE=1): $*; refusing the online fallback. Fetch the artifacts first (scripts/fetch_artifacts.sh) or run without MATHVERIFY_LEAN_OFFLINE=1"
}

# git for this script's own checks (the checkout may belong to another user when root re-runs).
gitq() { git -c safe.directory='*' "$@"; }

TMPS=()
cleanup() { [ "${#TMPS[@]}" -eq 0 ] || rm -rf "${TMPS[@]}"; }
trap cleanup EXIT

export ELAN_HOME
ELAN_HOME="$(expand_home "${ELAN_HOME:-$HOME/.elan}")"
export PATH="$ELAN_HOME/bin:$PATH"
PROJ="$(expand_home "${MATHVERIFY_LEAN_PROJECT:-$HOME/mathverify-lean}")"
ART=""
[ -z "${MATHVERIFY_ARTIFACT_DIR:-}" ] || ART="$(expand_home "$MATHVERIFY_ARTIFACT_DIR")"
OFFLINE="${MATHVERIFY_LEAN_OFFLINE:-0}"
case "$OFFLINE" in 0|1) ;; *) die "MATHVERIFY_LEAN_OFFLINE must be 0 or 1 (got $OFFLINE)" ;; esac
# Same archive as in setup_lean.sh; its repl/ is a shallow checkout at REPL_REV, origin REPL_URL.
SOURCES_ARCHIVE="lean-sources-${MATHLIB_REV:0:7}.tar.gz"

# As in setup_lean.sh: succeed when the artifact directory holds file $1 and it matches its
# SHA256SUMS.full entry (hard failure on a mismatch or a missing entry). Never call it in $(...).
have_artifact() {
  local name="$1" line
  [ -n "$ART" ] && [ -f "$ART/$name" ] || return 1
  [ -f "$ART/SHA256SUMS.full" ] || die "$ART has $name but no SHA256SUMS.full"
  line="$(awk -v n="$name" '{f = $2; sub(/^\*/, "", f); if (f == n) print}' "$ART/SHA256SUMS.full")"
  [ -n "$line" ] || die "$name is not listed in $ART/SHA256SUMS.full"
  (cd "$ART" && printf '%s\n' "$line" | sha256sum -c --strict --quiet -) \
    || die "SHA256 mismatch for $ART/$name"
}
REPL_BIN="$(expand_home "${MATHVERIFY_LEAN_REPL:-$HOME/repl/.lake/build/bin/repl}")"
case "$REPL_BIN" in
  */.lake/build/bin/repl) REPL_DIR="${REPL_BIN%/.lake/build/bin/repl}" ;;
  *) die "MATHVERIFY_LEAN_REPL must end in /.lake/build/bin/repl (got $REPL_BIN)" ;;
esac

LOG "setup_lean_repl: $(uname -srm), $(nproc) CPU(s), user $(id -un 2>/dev/null || id -u)"
LOG "ELAN_HOME=$ELAN_HOME PROJECT=$PROJ REPL=$REPL_DIR ARTIFACTS=${ART:-(none)} OFFLINE=$OFFLINE"
command -v elan >/dev/null 2>&1 || die "elan not found in $ELAN_HOME/bin; run scripts/setup_lean.sh first"
[ -f "$PROJ/lean-toolchain" ] || die "$PROJ has no lean-toolchain; run scripts/setup_lean.sh first"
[ "$(cat "$PROJ/lean-toolchain")" = "$LEAN_TOOLCHAIN" ] \
  || die "project toolchain $(cat "$PROJ/lean-toolchain") != pinned $LEAN_TOOLCHAIN"
[ "$OFFLINE" = 0 ] || [ -n "$ART" ] || refuse_online "MATHVERIFY_ARTIFACT_DIR is not set"

# A checkout at the pinned revision with the pinned origin (its lean-toolchain may differ: it is
# rewritten below).
repl_at_rev() {
  [ -d "$1/.git" ] \
    && [ "$(gitq -C "$1" rev-parse -q --verify HEAD 2>/dev/null)" = "$REPL_REV" ] \
    && [ "$(gitq -C "$1" remote get-url origin 2>/dev/null)" = "$REPL_URL" ]
}

REPL_PARENT="$(dirname "$REPL_DIR")"
REPL_BASE="$(basename "$REPL_DIR")"
# Leftovers of runs that died (their pid is gone): a staging checkout is removed; a checkout moved
# aside by an interrupted swap is put back when $REPL_DIR is missing, else removed.
for d in "$REPL_PARENT/.$REPL_BASE".stage.* "$REPL_PARENT/.$REPL_BASE".old.*; do
  [ -d "$d" ] || continue
  pid="${d##*.}"
  case "$pid" in ''|*[!0-9]*) continue ;; esac
  ! kill -0 "$pid" 2>/dev/null || continue
  case "$d" in
    *.old.*)
      if [ ! -e "$REPL_DIR" ]; then
        LOG "restoring $REPL_DIR from $d (an interrupted swap)"
        mv -T "$d" "$REPL_DIR"
        continue
      fi ;;
  esac
  LOG "removing $d (left by a run that died)"
  rm -rf "$d"
done

step "REPL checkout $REPL_URL @ $REPL_REV"
BUILD="$REPL_DIR"   # where the REPL is built: $REPL_DIR itself, or a staging checkout
STAGE=""
if repl_at_rev "$REPL_DIR"; then
  LOG "$REPL_DIR is at $REPL_REV; building in place"
elif have_artifact "$SOURCES_ARCHIVE"; then
  LOG "source: artifact $ART/$SOURCES_ARCHIVE"
  # Anything but a git checkout or an empty directory (a mount point, say) is left to the user.
  if [ -e "$REPL_DIR" ] && [ ! -d "$REPL_DIR/.git" ] \
     && ! { [ -d "$REPL_DIR" ] && [ -z "$(ls -A "$REPL_DIR")" ]; }; then
    die "$REPL_DIR exists without a .git directory; move it away first"
  fi
  mkdir -p "$REPL_PARENT"
  # Extract next to the final location (one filesystem), check, build there, then swap it in.
  STAGE="$REPL_PARENT/.$REPL_BASE.stage.$$"
  rm -rf "$STAGE"
  TMPS+=("$STAGE")
  mkdir "$STAGE"
  tar -xzf "$ART/$SOURCES_ARCHIVE" -C "$STAGE" --no-same-owner repl
  [ "$(gitq -C "$STAGE/repl" rev-parse -q --verify HEAD)" = "$REPL_REV" ] \
    || die "$SOURCES_ARCHIVE: repl/ is not at $REPL_REV"
  [ "$(gitq -C "$STAGE/repl" remote get-url origin)" = "$REPL_URL" ] \
    || die "$SOURCES_ARCHIVE: repl/ origin is not $REPL_URL"
  gitq -C "$STAGE/repl" update-index -q --refresh >/dev/null 2>&1 || true
  gitq -C "$STAGE/repl" diff-index --quiet HEAD -- || die "$SOURCES_ARCHIVE: repl/ worktree differs from $REPL_REV"
  BUILD="$STAGE/repl"
  if [ -d "$REPL_DIR/.git" ]; then
    LOG "$REPL_DIR is at $(gitq -C "$REPL_DIR" rev-parse -q --verify HEAD 2>/dev/null || echo none); it is replaced once the new checkout is built"
  fi
elif [ "$OFFLINE" = 1 ]; then
  refuse_online "${ART:-MATHVERIFY_ARTIFACT_DIR}/$SOURCES_ARCHIVE is missing and $REPL_DIR is not at $REPL_REV"
else
  if [ ! -d "$REPL_DIR/.git" ]; then
    mkdir -p "$REPL_PARENT"
    [ ! -d "$REPL_DIR" ] || rmdir "$REPL_DIR" 2>/dev/null \
      || die "$REPL_DIR exists without a .git directory; move it away first"
    LOG "source: online (git clone $REPL_URL)"
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
fi
cd "$BUILD"
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
[ -x "$BUILD/.lake/build/bin/repl" ] || die "REPL binary missing: $BUILD/.lake/build/bin/repl"
LOG "repl binary: $BUILD/.lake/build/bin/repl ($(wc -c < "$BUILD/.lake/build/bin/repl") bytes)"
step_done

# As in setup_lean.sh: a root install must stay readable for a session running as another user.
step "permissions"
n="$(find "$BUILD" ! -perm -o+r | wc -l)"
chmod -R a+rX "$BUILD"
LOG "$BUILD: $n entries were not world-readable; now $(find "$BUILD" ! -perm -o+r | wc -l)"
step_done

OLD=""
if [ -n "$STAGE" ]; then
  step "swap the new checkout into $REPL_DIR"
  if [ -d "$REPL_DIR/.git" ]; then
    OLD="$REPL_PARENT/.$REPL_BASE.old.$$"
    rm -rf "$OLD"
    mv -T "$REPL_DIR" "$OLD"
  elif [ -d "$REPL_DIR" ]; then
    rmdir "$REPL_DIR"
  fi
  if ! mv -T "$BUILD" "$REPL_DIR"; then
    [ -z "$OLD" ] || mv -T "$OLD" "$REPL_DIR" \
      || die "cannot rename $BUILD to $REPL_DIR, nor put the previous checkout back from $OLD"
    die "cannot rename $BUILD to $REPL_DIR; the previous checkout (if any) was put back"
  fi
  step_done
fi
# On a failed smoke test: the new checkout is discarded and the previous one put back (if that
# fails, it stays in .<name>.old.<pid>, which the next run restores or removes).
restore_old() {
  if [ -n "$OLD" ] && [ -d "$OLD" ]; then
    if mv -T "$REPL_DIR" "$STAGE/failed" && mv -T "$OLD" "$REPL_DIR"; then
      LOG "the previous checkout was put back in $REPL_DIR"
    else
      LOG "ERROR: could not put the previous checkout back; it is in $OLD"
    fi
  fi
}

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
[ "$rc" -eq 0 ] || { restore_old; die "REPL exited with code $rc"; }
case "$out" in *'"severity": "error"'*) restore_old; die "REPL reported an error" ;; esac
case "$out" in *'"env": 0'*) ;; *) restore_old; die "REPL did not return env 0 for the Mathlib command" ;; esac
case "$out" in *'"env": 1'*) ;; *) restore_old; die "REPL did not return env 1 for the follow-up command" ;; esac
LOG "REPL SMOKE OK"
[ -z "$OLD" ] || rm -rf "$OLD"
step_done
LOG "REPL DONE in $(( $(date +%s) - T0 ))s"
