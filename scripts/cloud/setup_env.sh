#!/usr/bin/env bash
# mathverify cloud environment setup script (Claude Code cloud, Ubuntu 24.04 x86_64).
#
# The claude.ai environment dialog runs its "Setup script" as root BEFORE Claude Code launches;
# a non-zero exit blocks the session, and the resulting filesystem is snapshotted and reused by
# later sessions (~7 days). This script therefore ALWAYS exits 0 and logs failures loudly; the
# SessionStart hook (scripts/cloud/session_start.sh) retries the Lean part in the background.
#
# Installs under ${MATHVERIFY_OPT:-/opt}:
#   python3.14/        CPython 3.14.6 from the pinned artifact (uv cannot download Python there)
#   uv-cache/          uv cache prewarmed with requirements.lock, so each session's .venv
#                      install is fast and offline (built from a throwaway copy of pyproject.toml
#                      + src/: nothing is written under the repository checkout)
#   elan/ mathverify-lean/ repl/
#                      Lean toolchain, pinned Mathlib project and REPL
#                      (scripts/setup_lean.sh, scripts/setup_lean_repl.sh)
#   mathverify-logs/   setup_env.log (timestamped), one log per stage, setup_env.status
# and, as root, /etc/profile.d/mathverify.sh (ELAN_HOME, MATHVERIFY_LEAN_PROJECT,
# MATHVERIFY_LEAN_REPL, MATHVERIFY_OPT, PATH).
#
# Everything is installed from the artifacts (scripts/fetch_artifacts.sh); only the uv prewarm
# uses the network (PyPI). The Python and Lean stages run only when the fetch succeeded and the
# artifact directory verifies against its SHA256SUMS.full; otherwise they are skipped
# (setup_env.status: FAILED ... reason=fetch|artifacts) and an existing install is not touched.
# The Lean scripts run in strict offline mode (MATHVERIFY_LEAN_OFFLINE=1): they refuse every
# online fallback (toolchain download, `lake exe cache get`, clones) instead of trying it. The
# Mathlib .ltar go to $OPT/.mathlib-ltar, removed after the Lean stages (the oleans are unpacked
# by then), and pip keeps no cache, so the snapshot holds no leftover download cache.
#
# Usage: setup_env.sh [--lean-only | --python-only]
# Environment: MATHVERIFY_OPT, MATHVERIFY_ARTIFACT_SRC / _URL / _REF (see fetch_artifacts.sh),
#   MATHVERIFY_GITHUB_TOKEN (see fetch_artifacts.sh),
#   MATHVERIFY_REPO_URL (clone fallback, default https://github.com/wqedwad/asd),
#   MATHVERIFY_REPO_REF (branch for the clone fallback, default: the remote's default branch),
#   MATHVERIFY_PROFILE_D (where mathverify.sh is written as root, default /etc/profile.d).
#   The claude.ai environment's variables do NOT reach the setup script (measured 25 Sep 2026);
#   for the setup-script run these are exported in the setup script's own text, as below. The
#   clone fallback has no credentials there, so it only works when the repository is readable
#   without them; both measured runs found the checkout at /home/user/asd instead.
#
# Paste-ready bootstrap for the dialog's "Setup script" field, when pasting this whole file is
# inconvenient. It runs the repository's own copy of this script and never fails the session.
# The claude.ai environment's variables do not reach it (measured 25 Sep 2026), so the artifact
# token (fine-grained, wqedwad/asd only, Contents: read-only) is pasted between the quotes of
# T=''. It is not exported: only setup_env.sh gets it, and passes it to the artifact fetch alone.
# Left empty, a value the platform might pass one day is used; without one the fetch is not
# retried with a token and the SessionStart hook installs instead. The first line keeps a traced
# shell (-x/-v) from printing the token. timeout(1) caps the run at 250 s (+10 s to KILL): past ~5
# min the platform fails new sessions (web-quickstart, "New sessions hang or time out during
# setup"); a stopped run is FAILED reason=terminated and the SessionStart hook installs the rest.
# Measured full runs: 192 s and 234 s.
#
#   #!/bin/bash
#   { set +vx; } 2>/dev/null
#   unset T
#   T=''
#   S=
#   for d in "${CLAUDE_PROJECT_DIR:-}" /home/*/* /root/* /workspace /workspace/* /tmp/*; do
#     if [ -f "$d/scripts/cloud/setup_env.sh" ] && grep -qs 'wqedwad/asd' "$d/.git/config"; then
#       S="$d/scripts/cloud/setup_env.sh"; break
#     fi
#   done
#   if [ -z "$S" ]; then
#     rm -rf /tmp/mv-boot
#     GIT_TERMINAL_PROMPT=0 timeout 30 git clone -q --depth 1 ${MATHVERIFY_REPO_REF:+--branch "$MATHVERIFY_REPO_REF"} \
#       https://github.com/wqedwad/asd /tmp/mv-boot && S=/tmp/mv-boot/scripts/cloud/setup_env.sh
#   fi
#   if [ -n "$S" ]; then
#     MATHVERIFY_GITHUB_TOKEN="${T:-${MATHVERIFY_GITHUB_TOKEN:-}}" timeout -k 10 250 bash "$S" || true
#   else
#     echo "mathverify: setup_env.sh not found"
#   fi
#   unset T
#   rm -rf /tmp/mv-boot
#   exit 0

set -o pipefail
umask 022
trap 'exit 0' EXIT          # never block the session, whatever happens below

MODE=all
for arg in "$@"; do
  case "$arg" in
    --lean-only) MODE=lean ;;
    --python-only) MODE=python ;;
    -h|--help) sed -n '2,25p' "${BASH_SOURCE[0]:-$0}" 2>/dev/null; exit 0 ;;
    *) echo "setup_env: ignoring unknown option $arg" ;;
  esac
done

# The artifact token is for fetch_artifacts.sh only: it stays in a shell variable, out of the
# environment of everything else this script runs (uv, pip and the packages' code, Lean, Lake).
# (unset first: a FETCH_TOKEN the caller exported would keep its export attribute.) The value
# still sits in this process's own initial environment (/proc/<pid>/environ), which a process
# running as root can read: this guards against accidental exposure, not against such a reader.
unset FETCH_TOKEN
FETCH_TOKEN="${MATHVERIFY_GITHUB_TOKEN:-}"
unset MATHVERIFY_GITHUB_TOKEN

: "${HOME:=/root}"
export HOME
OPT="${MATHVERIFY_OPT:-/opt}"
REPO_URL="${MATHVERIFY_REPO_URL:-https://github.com/wqedwad/asd}"
PY_VERSION=3.14.6
T0=$(date +%s)

LOGDIR="$OPT/mathverify-logs"
if ! mkdir -p "$LOGDIR" 2>/dev/null || [ ! -w "$LOGDIR" ]; then
  echo "setup_env: !!! $LOGDIR is not writable (run as root or set MATHVERIFY_OPT); logging to /tmp"
  LOGDIR="${TMPDIR:-/tmp}/mathverify-logs"
  mkdir -p "$LOGDIR" 2>/dev/null
fi
LOG="$LOGDIR/setup_env.log"
STATUS_FILE="$LOGDIR/setup_env.status"

log() {
  local line
  line="[$(date -u +%Y-%m-%dT%H:%M:%SZ) +$(( $(date +%s) - T0 ))s] $*"
  printf '%s\n' "$line"
  printf '%s\n' "$line" >>"$LOG" 2>/dev/null
}
loud() { log "!!!!! $*"; }

# One run at a time. The lock is held until this process exits (fd 9); session_start.sh probes
# it with `flock -n` to tell "installing" from "missing".
LOCK="$LOGDIR/setup_env.lock"
if command -v flock >/dev/null 2>&1; then
  exec 9>>"$LOCK"
  chmod a+rw "$LOCK" 2>/dev/null
  if ! flock -n 9; then
    log "another setup_env.sh run holds $LOCK; nothing to do"
    exit 0
  fi
fi
echo "$$" >"$LOGDIR/setup_env.pid" 2>/dev/null
chmod a+rw "$LOGDIR/setup_env.pid" 2>/dev/null
trap 'rm -f "$LOGDIR/setup_env.pid"; exit 0' EXIT
# The claude.ai platform fails new sessions when the setup script passes ~5 min (web-quickstart,
# "New sessions hang or time out during setup"), so the bootstrap stops this run with SIGTERM at
# its time cap (timeout(1) signals the whole process group: every stage dies with it). Record why;
# the SessionStart hook sees FAILED, finds the lock free and installs what is missing. setup_lean.sh
# cleans up what an interrupted run leaves behind.
on_term() {
  trap - TERM INT
  local stages=""
  [ -f "${STAGES_FILE:-}" ] \
    && stages="$(awk '{printf "%s(%s) ", $1, ($3 ~ /^[0-9]+$/ ? $3 "s" : $3)}' "$STAGES_FILE")"
  loud "stopped by a signal after $(( $(date +%s) - T0 ))s (the setup script's time cap, or a shutdown); the SessionStart hook installs what is missing"
  echo "FAILED mode=$MODE stages=[${stages% }] reason=terminated total=$(( $(date +%s) - T0 ))s" >"$STATUS_FILE"
  chmod a+rw "$STATUS_FILE" 2>/dev/null
  rm -f "${STAGES_FILE:-}"
  exit 0
}
trap on_term TERM INT

log "==== setup_env.sh mode=$MODE user=$(id -un 2>/dev/null || id -u) HOME=$HOME OPT=$OPT"
log "host: $(uname -srm), $(nproc 2>/dev/null) CPU(s), $(awk '/MemTotal/ {printf "%.1f GB", $2/1048576}' /proc/meminfo 2>/dev/null) RAM, $(df -h "$OPT" 2>/dev/null | awk 'NR==2 {print $4}') free on $OPT"
[ -w "$OPT" ] || loud "$OPT is not writable by $(id -un 2>/dev/null); installs below will fail"
# Which of these variables this run sees, by name only (never a value). The claude.ai
# environment's variables did not reach the setup script (measured 25 Sep 2026: the session had
# MATHVERIFY_GITHUB_TOKEN, the setup script did not); whether a proxy exists before Claude Code
# starts, and CLAUDE_PROJECT_DIR there, were never measured. MATHVERIFY_SETUP_CANARY is a
# harmless variable the user may add to the environment to see whether any variable gets here.
env_names() {
  local v val have=() lack=()
  for v in MATHVERIFY_GITHUB_TOKEN MATHVERIFY_SETUP_CANARY MATHVERIFY_REPO_REF \
           MATHVERIFY_ARTIFACT_REF CLAUDE_PROJECT_DIR CLAUDE_CODE_REMOTE HTTPS_PROXY https_proxy \
           HTTP_PROXY http_proxy NO_PROXY no_proxy GIT_CONFIG_COUNT; do
    if [ "$v" = MATHVERIFY_GITHUB_TOKEN ]; then val="$FETCH_TOKEN"; else val="${!v:-}"; fi
    if [ -n "$val" ]; then have+=("$v"); else lack+=("$v"); fi
  done
  log "environment (names only): set=[${have[*]}] unset=[${lack[*]}]"
}
env_names

# ---------------------------------------------------------------------------------------------
# Locate the repository: $CLAUDE_PROJECT_DIR, this script's own checkout, a search of likely
# roots for a checkout whose remote is wqedwad/asd, else a shallow clone.
is_repo() {
  [ -n "$1" ] && [ -f "$1/pyproject.toml" ] && [ -f "$1/requirements.lock" ] \
    && grep -qs '^name = "mathverify"' "$1/pyproject.toml"
}
origin_matches() {
  grep -qs 'wqedwad/asd' "$1/.git/config" \
    || git -c safe.directory='*' -C "$1" config --get-regexp '^remote\..*\.url$' 2>/dev/null \
      | grep -q 'wqedwad/asd'
}
CLONED=""
find_repo() {
  local d self g root depth
  if is_repo "${CLAUDE_PROJECT_DIR:-}"; then
    printf '%s\n' "$CLAUDE_PROJECT_DIR"; return 0
  fi
  self="${BASH_SOURCE[0]:-}"
  if [ -n "$self" ] && [ -f "$self" ]; then
    d="$(cd "$(dirname "$self")/../.." 2>/dev/null && pwd)"
    if is_repo "$d"; then printf '%s\n' "$d"; return 0; fi
  fi
  for root in /home /root /workspace /workspaces /tmp /; do
    [ -d "$root" ] || continue
    depth=3; [ "$root" = / ] && depth=4
    while IFS= read -r g; do
      d="${g%/.git}"
      if is_repo "$d" && origin_matches "$d"; then printf '%s\n' "$d"; return 0; fi
    done < <(find "$root" -maxdepth "$depth" \( -path /proc -o -path /sys -o -path /dev \
               -o -path /usr -o -path /snap -o -path /var/lib -o -path "$OPT" \) -prune \
               -o -name .git -print 2>/dev/null)
  done
  return 1
}

REPO="$(find_repo)"
if [ -z "$REPO" ]; then
  d="$OPT/mathverify-src.$$"
  log "no checkout found; cloning $REPO_URL ${MATHVERIFY_REPO_REF:+(branch $MATHVERIFY_REPO_REF) }into $d"
  rm -rf "$d"
  if GIT_TERMINAL_PROMPT=0 git clone -q --depth 1 ${MATHVERIFY_REPO_REF:+--branch "$MATHVERIFY_REPO_REF"} \
       "$REPO_URL" "$d" >>"$LOG" 2>&1 && is_repo "$d"; then
    REPO="$d"; CLONED="$d"
  else
    rm -rf "$d"
  fi
fi
if [ -z "$REPO" ]; then
  loud "FAILED: mathverify repository not found and the clone failed; nothing installed"
  echo "FAILED mode=$MODE reason=no-repo total=$(( $(date +%s) - T0 ))s" >"$STATUS_FILE"
  exit 0
fi
log "repository: $REPO ($(git -c safe.directory='*' -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo 'no git'))"
[ -x "$(command -v git)" ] || loud "git not found"

# ---------------------------------------------------------------------------------------------
ART="${MATHVERIFY_ARTIFACT_DIR:-$OPT/arac}"
PY="$OPT/python3.14/bin/python3.14"
UV_CACHE="$OPT/uv-cache"
ELAN="$OPT/elan"
PROJ="$OPT/mathverify-lean"
REPL_BIN="$OPT/repl/.lake/build/bin/repl"
LEAN_MARK="$LOGDIR/lean.done"
PREWARM_MARK="$LOGDIR/uv-prewarm.done"
LTAR_DIR="$OPT/.mathlib-ltar"

sha_of() { sha256sum "$@" 2>/dev/null | awk '{print $1}' | sha256sum | awk '{print $1}'; }
# The Lean install is defined by the pinned files in lean/ (README.md excluded).
lean_fingerprint() {
  (cd "$REPO" && find lean -type f ! -name README.md | LC_ALL=C sort | xargs sha256sum 2>/dev/null) \
    | sha256sum | awk '{print $1}'
}
python_ok() {
  [ -x "$PY" ] && "$PY" -c "import sys; raise SystemExit(sys.version.split()[0] != '$PY_VERSION')" 2>/dev/null
}
prewarm_fingerprint() {
  { sha_of "$REPO/requirements.lock" "$REPO/pyproject.toml"; "$PY" -c 'import sys; print(sys.version)'; } \
    2>/dev/null | sha256sum | awk '{print $1}'
}
lean_ok() {
  [ -x "$REPL_BIN" ] && [ -d "$PROJ" ] && [ -f "$LEAN_MARK" ] \
    && [ "$(cat "$LEAN_MARK" 2>/dev/null)" = "$(lean_fingerprint)" ]
}
# ready | stale (a finished install made from other lean/ pins) | missing
lean_state() {
  if lean_ok; then echo ready
  elif [ -x "$REPL_BIN" ] && [ -d "$PROJ" ] && [ -f "$LEAN_MARK" ]; then echo stale
  else echo missing
  fi
}
# The fetched artifact directory is complete: every file of its SHA256SUMS.full is present and
# matches (fetch_artifacts.sh checked it too; this guards the stages against anything else).
art_verifies() {
  [ -f "$ART/SHA256SUMS.full" ] && [ -s "$ART/SHA256SUMS.full" ] \
    && (cd "$ART" && sha256sum -c --strict --quiet SHA256SUMS.full)
}

STAGES_FILE="$LOGDIR/stages.$$"
: >"$STAGES_FILE"
# run_stage NAME CMD...: run CMD with its output in $LOGDIR/NAME.log; record the result.
run_stage() {
  local name="$1" slog="$LOGDIR/$1.log" t rc
  shift
  t=$(date +%s)
  log "stage $name: start (log $slog)"
  { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; "$@"; } >"$slog" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    log "stage $name: OK in $(( $(date +%s) - t ))s"
  else
    loud "stage $name: FAILED (exit $rc) after $(( $(date +%s) - t ))s; last lines of $slog:"
    tail -n 25 "$slog" 2>/dev/null | sed 's/^/    | /' | tee -a "$LOG"
  fi
  echo "$name $rc $(( $(date +%s) - t ))" >>"$STAGES_FILE"
  return "$rc"
}
# skip_stage NAME WHY: record NAME as failed without running it (its log says why).
skip_stage() {
  loud "stage $1: SKIPPED, $2"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] skipped: $2" >"$LOGDIR/$1.log"
  echo "$1 1 skipped" >>"$STAGES_FILE"
}

find_uv() {
  local c
  for c in "$(command -v uv 2>/dev/null)" "$OPT/uv-tool/bin/uv" /root/.local/bin/uv \
           /root/.cargo/bin/uv /usr/local/bin/uv /home/*/.local/bin/uv /home/*/.cargo/bin/uv; do
    if [ -n "$c" ] && [ -x "$c" ]; then printf '%s\n' "$c"; return 0; fi
  done
  # Last resort: uv from PyPI (allowed by the cloud network policy) with the artifact Python.
  if [ -x "$PY" ] && "$PY" -m venv "$OPT/uv-tool" >&2 \
     && "$OPT/uv-tool/bin/python" -m pip install -q --no-cache-dir uv >&2; then
    printf '%s\n' "$OPT/uv-tool/bin/uv"; return 0
  fi
  return 1
}

stage_fetch() {
  [ -f "$REPO/scripts/fetch_artifacts.sh" ] || { echo "missing $REPO/scripts/fetch_artifacts.sh"; return 1; }
  MATHVERIFY_GITHUB_TOKEN="$FETCH_TOKEN" bash "$REPO/scripts/fetch_artifacts.sh" "$ART"
}

stage_python() {
  local tgz tmp
  tgz="$(ls "$ART"/cpython-"$PY_VERSION"-x86_64-unknown-linux-gnu-install_only*.tar.gz 2>/dev/null | head -n 1)"
  [ -n "$tgz" ] || { echo "no cpython-$PY_VERSION artifact in $ART"; return 1; }
  tmp="$(mktemp -d "$OPT/.python3.14.XXXXXX")" || return 1
  if ! tar -xzf "$tgz" -C "$tmp"; then rm -rf "$tmp"; return 1; fi
  if ! "$tmp/python/bin/python3.14" -c "import sys; assert sys.version.split()[0] == '$PY_VERSION', sys.version"; then
    rm -rf "$tmp"; return 1
  fi
  # python-build-standalone is relocatable: install by renaming, so a half copy never appears.
  rm -rf "$OPT/python3.14" && mv "$tmp/python" "$OPT/python3.14" && rm -rf "$tmp" || return 1
  "$PY" -c 'import sys, ssl, sqlite3, compression.zstd; print(sys.version); print(ssl.OPENSSL_VERSION)'
}

stage_prewarm() {
  local uvb v rc
  uvb="$(find_uv)" || { echo "uv not found and could not be installed"; return 1; }
  echo "uv: $uvb ($("$uvb" --version))"
  v="$(mktemp -d "$OPT/.uv-prewarm.XXXXXX")" || return 1
  # Nothing may be written under $REPO: this runs as root, and a root-owned
  # src/mathverify.egg-info (or __pycache__) there makes the session user's own
  # `uv pip install -e .` fail with EACCES. The editable build therefore runs on a throwaway copy
  # of pyproject.toml + src/ (it still caches the build backend the session's install needs),
  # uv runs from inside the copy, and the import check writes no bytecode.
  mkdir -p "$v/pkg" && cp "$REPO/pyproject.toml" "$v/pkg/" && cp -R "$REPO/src" "$v/pkg/" \
    || { rm -rf "$v"; return 1; }
  find "$v/pkg/src" \( -name __pycache__ -o -name '*.egg-info' \) -prune -exec rm -rf {} + 2>/dev/null
  export UV_CACHE_DIR="$UV_CACHE" UV_PYTHON_DOWNLOADS=never
  (
    cd "$v" || exit 1
    "$uvb" venv -q --python "$PY" "$v/venv" \
      && "$uvb" pip install --python "$v/venv/bin/python" -r "$REPO/requirements.lock" \
      && "$uvb" pip install --python "$v/venv/bin/python" --no-deps -e "$v/pkg" \
      && PYTHONDONTWRITEBYTECODE=1 "$v/venv/bin/python" -c \
        'import mathverify, sympy, z3, math_verify, anthropic, pytest; print("imports OK:", mathverify.__file__)'
  )
  rc=$?
  rm -rf "$v"
  [ "$rc" -eq 0 ] && prewarm_fingerprint >"$PREWARM_MARK"
  return "$rc"
}

# Strict offline mode: a missing artifact stops the Lean scripts at once instead of sending them
# to the network (a `lake exe cache get` against cache.mathlib.org hung for >24 min, holding the
# setup lock). The .ltar cache goes to $LTAR_DIR, removed after the Lean stages.
stage_lean_env() {
  env ELAN_HOME="$ELAN" MATHVERIFY_LEAN_PROJECT="$PROJ" MATHVERIFY_LEAN_REPL="$REPL_BIN" \
      MATHVERIFY_ARTIFACT_DIR="$ART" MATHVERIFY_OPT="$OPT" MATHVERIFY_LEAN_OFFLINE=1 \
      MATHLIB_CACHE_DIR="$LTAR_DIR" "$@"
}
stage_lean() { stage_lean_env bash "$REPO/scripts/setup_lean.sh"; }
stage_lean_repl() { stage_lean_env bash "$REPO/scripts/setup_lean_repl.sh"; }

# ---------------------------------------------------------------------------------------------
NEED_PY=0; NEED_PREWARM=0; NEED_LEAN=0
if [ "$MODE" != lean ]; then
  python_ok || NEED_PY=1
  if [ "$NEED_PY" = 1 ] || [ ! -d "$UV_CACHE" ] \
     || [ "$(cat "$PREWARM_MARK" 2>/dev/null)" != "$(prewarm_fingerprint)" ]; then
    NEED_PREWARM=1
  fi
fi
if [ "$MODE" != python ]; then
  lean_ok || NEED_LEAN=1
  # setup_lean.sh uses $OPT/python3.14 as its zstd decompressor when the zstd CLI is missing.
  python_ok || NEED_PY=1
fi
log "plan: python=$NEED_PY uv-prewarm=$NEED_PREWARM lean=$NEED_LEAN (1 = to do)"

# The Python and Lean stages install only from a fetched, verified artifact directory. Without
# one they are skipped: an existing install stays exactly as it is, and nothing falls back to the
# network (REASON goes into setup_env.status).
FETCHED=""; ART_OK=""; REASON=""
if [ "$NEED_PY" = 1 ] || [ "$NEED_LEAN" = 1 ]; then
  if run_stage fetch_artifacts stage_fetch; then
    FETCHED=1
    t=$(date +%s)
    if art_verifies >/dev/null 2>&1; then
      ART_OK=1
      log "artifacts in $ART verified against SHA256SUMS.full in $(( $(date +%s) - t ))s"
    else
      REASON=artifacts
      loud "$ART does not verify against its SHA256SUMS.full"
    fi
  else
    REASON=fetch
  fi
fi
if [ "$NEED_PY" = 1 ]; then
  if [ -n "$ART_OK" ]; then
    run_stage python stage_python
  else
    skip_stage python "no verified artifacts (reason=$REASON)"
  fi
fi

pids=()
if [ "$NEED_PREWARM" = 1 ]; then
  if python_ok; then
    run_stage uv_prewarm stage_prewarm &
    pids+=("$!")
  else
    skip_stage uv_prewarm "Python $PY_VERSION is not installed"
  fi
fi
if [ "$NEED_LEAN" = 1 ]; then
  if [ -n "$ART_OK" ]; then
    (
      run_stage setup_lean stage_lean && run_stage setup_lean_repl stage_lean_repl \
        && lean_fingerprint >"$LEAN_MARK"
    ) &
    pids+=("$!")
  else
    skip_stage setup_lean "no verified artifacts (reason=$REASON); the Lean install in $OPT is left as it is"
    skip_stage setup_lean_repl "no verified artifacts (reason=$REASON)"
  fi
fi
for p in "${pids[@]}"; do wait "$p"; done
if [ -d "$LTAR_DIR" ]; then
  log "removing $LTAR_DIR ($(find "$LTAR_DIR" -name '*.ltar' | wc -l) .ltar, $(du -sh "$LTAR_DIR" | cut -f1)): only the input of \`lake exe cache unpack\`; lean.done $([ -f "$LEAN_MARK" ] && echo written || echo 'not written')"
  rm -rf "$LTAR_DIR"
fi

# Make everything usable by a non-root session user (the session user is not known here).
for d in "$OPT/python3.14" "$UV_CACHE" "$OPT/uv-tool" "$ELAN" "$PROJ" "$OPT/repl" "$LOGDIR"; do
  [ -e "$d" ] || continue
  if [ "$d" = "$LOGDIR" ] || [ "$(id -u)" = 0 ]; then
    chmod -R a+rwX "$d" 2>/dev/null || loud "chmod -R a+rwX $d failed"
  fi
done

PROFILE_D="${MATHVERIFY_PROFILE_D:-/etc/profile.d}"
if [ "$(id -u)" = 0 ] && lean_ok && mkdir -p "$PROFILE_D"; then
  cat >"$PROFILE_D/mathverify.sh" <<EOF
# Written by mathverify scripts/cloud/setup_env.sh; the Lean layer's cloud install.
export MATHVERIFY_OPT="$OPT"
export ELAN_HOME="$ELAN"
export MATHVERIFY_LEAN_PROJECT="$PROJ"
export MATHVERIFY_LEAN_REPL="$REPL_BIN"
case ":\$PATH:" in *":$ELAN/bin:"*) ;; *) export PATH="$ELAN/bin:\$PATH" ;; esac
EOF
  chmod 644 "$PROFILE_D/mathverify.sh"
  log "wrote $PROFILE_D/mathverify.sh"
fi

FAILED="$(awk '$2 != 0 {printf "%s ", $1}' "$STAGES_FILE")"
DONE_STAGES="$(awk '{printf "%s(%s) ", $1, ($3 ~ /^[0-9]+$/ ? $3 "s" : $3)}' "$STAGES_FILE")"
rm -f "$STAGES_FILE"
if [ -z "$FAILED" ]; then
  if [ -n "$FETCHED" ] && [ "$ART" = "$OPT/arac" ]; then
    rm -rf "$ART" && log "removed reassembled artifacts $ART"
  fi
  STATUS=OK
else
  STATUS=FAILED
  [ -z "$FETCHED" ] || log "keeping $ART for a retry"
fi
[ -z "$CLONED" ] || rm -rf "$CLONED"
TOTAL=$(( $(date +%s) - T0 ))
python_ok && PYS="$PY_VERSION" || PYS=missing
LEANS="$(lean_state)"
LINE="$STATUS mode=$MODE failed=[${FAILED% }] stages=[${DONE_STAGES% }]${REASON:+ reason=$REASON} python=$PYS lean=$LEANS total=${TOTAL}s"
echo "$LINE" >"$STATUS_FILE"
chmod a+rw "$STATUS_FILE" 2>/dev/null
if [ "$STATUS" = OK ]; then log "FINAL: $LINE"; else loud "FINAL: $LINE (see $LOGDIR)"; fi
exit 0
