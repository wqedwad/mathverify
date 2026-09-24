#!/usr/bin/env bash
# F5 infrastructure: the pinned Lean 4 toolchain, the Mathlib project and its prebuilt cache.
# Everything is pinned by lean/PINS and the project files in lean/, which are copied into the
# project directory (never `lake new` / `lake update`). Works on native Linux (cloud) and inside
# WSL, as root or as a user. Idempotent: safe to re-run.
#
# Environment:
#   ELAN_HOME                 elan home (default $HOME/.elan)
#   MATHVERIFY_LEAN_PROJECT   project directory (default $HOME/mathverify-lean)
#   MATHVERIFY_ARTIFACT_DIR   directory filled by scripts/fetch_artifacts.sh; each component found
#                             there (elan, Lean toolchain, the Lake package sources, Mathlib .ltar
#                             cache) is installed offline, anything missing is fetched online.
#                             With the package sources and the .ltar cache both present, every
#                             lake command runs with the network cut off (no git clone at all)
#   MATHVERIFY_LEAN_OFFLINE=1 strict offline mode (scripts/cloud/setup_env.sh always sets it):
#                             every online fallback is refused (elan or toolchain download,
#                             `lake exe cache get`, a Lake clone, apt-get), so a missing artifact
#                             stops the script before it writes anything, within seconds
#   MATHLIB_CACHE_DIR, XDG_CACHE_HOME
#                             Mathlib .ltar cache location, resolved exactly as Mathlib's
#                             Cache/IO.lean does (default $HOME/.cache/mathlib). When the .ltar
#                             come from the artifacts and MATHLIB_CACHE_DIR is unset, they are
#                             extracted into a temporary cache directory next to the project,
#                             removed on exit (the oleans are unpacked by then; ~450 MB saved)
#   MATHVERIFY_OPT            cloud install prefix (default /opt); only used to find
#                             $MATHVERIFY_OPT/python3.14 as a zstd decompressor
#
# Every artifact this run needs is verified (SHA256SUMS.full) before anything is written, and the
# free disk is checked before the toolchain and the project are (choose_workdir). An existing
# project directory is then completed in place only when it already holds the pinned project
# files and package revisions (the remaining work only adds oleans); otherwise the new project is
# built in a staging directory next to it and replaces it only after its smoke test passed, both
# there and again after the rename, so a failed run never leaves a working install half rewritten.
# Sourcing this file only defines the helpers; running it performs the setup.
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

export ELAN_HOME
ELAN_HOME="$(expand_home "${ELAN_HOME:-$HOME/.elan}")"
PROJ="$(expand_home "${MATHVERIFY_LEAN_PROJECT:-$HOME/mathverify-lean}")"
ART=""
[ -z "${MATHVERIFY_ARTIFACT_DIR:-}" ] || ART="$(expand_home "$MATHVERIFY_ARTIFACT_DIR")"
OPT="${MATHVERIFY_OPT:-/opt}"
OFFLINE="${MATHVERIFY_LEAN_OFFLINE:-0}"
case "$OFFLINE" in 0|1) ;; *) die "MATHVERIFY_LEAN_OFFLINE must be 0 or 1 (got $OFFLINE)" ;; esac
export PATH="$ELAN_HOME/bin:$PATH"
# The directory this run builds the project in: $PROJ, or a staging directory (choose_workdir).
WORK="$PROJ"

ARCH="$(uname -m)"
LEAN_VERSION="${LEAN_TOOLCHAIN##*:v}"
# elan's directory name for a toolchain: "leanprover/lean4:v4.34.0" -> "leanprover--lean4---v4.34.0"
TC_NAME="${LEAN_TOOLCHAIN//:/---}"
TC_NAME="${TC_NAME//\//--}"
TC_DIR="$ELAN_HOME/toolchains/$TC_NAME"
ELAN_ARCHIVE="elan-$ARCH-unknown-linux-gnu.tar.gz"
LEAN_ARCHIVE="lean-$LEAN_VERSION-linux.tar.zst"
[ "$ARCH" = x86_64 ] || LEAN_ARCHIVE="lean-$LEAN_VERSION-linux_$ARCH.tar.zst"
LEAN_TOPDIR="${LEAN_ARCHIVE%.tar.zst}"
MATHLIB_ARCHIVE="mathlib-cache-${MATHLIB_REV:0:7}.tar"
# Shallow git checkouts of the lake-manifest.json packages (packages/<name>/) and of the REPL
# (repl/, used by setup_lean_repl.sh), each at its pinned revision with origin = the pinned URL.
SOURCES_ARCHIVE="lean-sources-${MATHLIB_REV:0:7}.tar.gz"
# Standalone CPython shipped with the artifacts; only a fallback zstd decompressor here.
PY_ARCHIVE="cpython-3.14.6-$ARCH-unknown-linux-gnu-install_only_stripped.tar.gz"
PROJECT_FILES=(lakefile.toml lean-toolchain lake-manifest.json MathverifyLean.lean MathverifyLean/Basic.lean)

TMPS=()
cleanup() { [ "${#TMPS[@]}" -eq 0 ] || rm -rf "${TMPS[@]}"; }
trap cleanup EXIT
# mktmp VAR [PARENT]: create a temporary directory (removed on exit) and store its path in VAR.
mktmp() {
  local _d
  _d="$(mktemp -d "${2:-${TMPDIR:-/tmp}}/.mathverify-setup.XXXXXX")"
  TMPS+=("$_d")
  printf -v "$1" '%s' "$_d"
}

# Run a command with every proxy variable pointing at a closed local port and git limited to the
# file transport: any download attempt (elan, curl, a git clone or fetch by lake) fails at once.
# Used to prove that an artifact install needs no network.
offline() {
  local p=http://127.0.0.1:9
  env HTTPS_PROXY=$p https_proxy=$p HTTP_PROXY=$p http_proxy=$p ALL_PROXY=$p all_proxy=$p \
    NO_PROXY= no_proxy= GIT_ALLOW_PROTOCOL=file "$@"
}

# Strict offline mode: an online fallback was about to run. Never call it inside $(...).
refuse_online() {
  die "offline mode (MATHVERIFY_LEAN_OFFLINE=1): $*; refusing the online fallback. Fetch the artifacts first (scripts/fetch_artifacts.sh) or run without MATHVERIFY_LEAN_OFFLINE=1"
}

# git for this script's own checks: it reads package checkouts that may belong to another user
# (a root re-run over a user install), where plain git refuses with "dubious ownership".
gitq() { git -c safe.directory='*' "$@"; }

# The packages pinned in lake-manifest.json ($1), one "name url rev" line each. Only git
# packages without a subDir are supported (all nine are); anything else is a hard failure.
manifest_packages() {
  local n_type n_git out
  n_type="$(grep -c '"type":' "$1" || true)"
  n_git="$(grep -c '"type": "git"' "$1" || true)"
  [ "$n_type" = "$n_git" ] || die "$1: only git packages are supported ($n_git of $n_type)"
  if grep '"subDir":' "$1" | grep -qv '"subDir": null'; then
    die "$1: packages with a subDir are not supported"
  fi
  out="$(awk -F'"' '/"url":/ {url = $4} /"rev":/ {rev = $4}
    /"name":/ && rev != "" {print $4, url, rev; rev = ""; url = ""}' "$1")"
  [ "$(printf '%s\n' "$out" | grep -c .)" = "$n_type" ] || die "$1: could not read $n_type packages"
  printf '%s\n' "$out"
}

# Hard failure unless the git checkout $1 has HEAD = $3, origin = $2 and a worktree equal to HEAD
# (the index is refreshed first, so extracted files are compared by content).
verify_checkout() {
  local d="$1" url="$2" rev="$3" head origin
  head="$(gitq -C "$d" rev-parse -q --verify HEAD)" || die "$d: no HEAD"
  [ "$head" = "$rev" ] || die "$d: HEAD $head, pinned $rev"
  origin="$(gitq -C "$d" remote get-url origin)" || die "$d: no origin remote"
  [ "$origin" = "$url" ] || die "$d: origin $origin, pinned $url"
  gitq -C "$d" update-index -q --refresh >/dev/null 2>&1 || true
  gitq -C "$d" diff-index --quiet HEAD -- || die "$d: worktree differs from $rev"
}

# Succeed when MATHVERIFY_ARTIFACT_DIR holds file $1, after checking it against the directory's
# SHA256SUMS.full (hard failure on a mismatch or a missing entry); each file is hashed once per
# run. Never call it inside $(...): die must end the script, not a subshell.
declare -gA VERIFIED=()
have_artifact() {
  local name="$1" line
  [ -n "$ART" ] && [ -f "$ART/$name" ] || return 1
  [ -z "${VERIFIED[$name]:-}" ] || return 0
  [ -f "$ART/SHA256SUMS.full" ] || die "$ART has $name but no SHA256SUMS.full"
  line="$(awk -v n="$name" '{f = $2; sub(/^\*/, "", f); if (f == n) print}' "$ART/SHA256SUMS.full")"
  [ -n "$line" ] || die "$name is not listed in $ART/SHA256SUMS.full"
  (cd "$ART" && printf '%s\n' "$line" | sha256sum -c --strict --quiet -) \
    || die "SHA256 mismatch for $ART/$name"
  VERIFIED[$name]=1
}

# want NAME WHAT: verify artifact NAME now if present. A missing one means an online fallback
# later, which offline mode refuses here, before anything is written.
want() {
  if have_artifact "$1"; then
    LOG "verified $1 ($2)"
  elif [ "$OFFLINE" = 1 ]; then
    refuse_online "${ART:-MATHVERIFY_ARTIFACT_DIR}/$1 ($2) is missing"
  else
    LOG "$1 is not among the artifacts: $2 will be fetched online"
  fi
}

# Pick a zstd decompressor once (global UNZSTD): the zstd CLI, else a python3 >= 3.14 with
# compression.zstd (PATH, then $MATHVERIFY_OPT/python3.14, then the CPython artifact unpacked to a
# temporary directory), else `apt-get install zstd` when running as root.
UNZSTD=""
choose_unzstd() {
  [ -z "$UNZSTD" ] || return 0
  local c d
  if command -v zstd >/dev/null 2>&1; then
    UNZSTD=zstd
  else
    for c in python3 python3.14 "$OPT/python3.14/bin/python3" "$OPT/python3.14/bin/python3.14"; do
      if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import compression.zstd' >/dev/null 2>&1; then
        UNZSTD="$(command -v "$c")"
        break
      fi
    done
    if [ -z "$UNZSTD" ] && have_artifact "$PY_ARCHIVE"; then
      mktmp d
      tar -xzf "$ART/$PY_ARCHIVE" -C "$d"
      if "$d/python/bin/python3" -c 'import compression.zstd' >/dev/null 2>&1; then
        UNZSTD="$d/python/bin/python3"
      fi
    fi
    if [ -z "$UNZSTD" ]; then
      if [ "$OFFLINE" = 1 ]; then
        refuse_online "no zstd decompressor (zstd CLI, python3 >= 3.14 with compression.zstd, or $PY_ARCHIVE among the artifacts) and apt-get needs the network"
      elif [ "$(id -u)" = 0 ] && command -v apt-get >/dev/null 2>&1; then
        LOG "no zstd decompressor found; installing zstd with apt-get"
        export DEBIAN_FRONTEND=noninteractive
        apt-get install -y -q zstd || { apt-get update -q && apt-get install -y -q zstd; } \
          || die "apt-get install zstd failed"
        UNZSTD=zstd
      else
        die "cannot decompress .zst: need the zstd CLI or python3 >= 3.14 with compression.zstd (as root, zstd is installed with apt-get)"
      fi
    fi
  fi
  LOG "zstd decompressor: $UNZSTD"
}

# Decompress a .zst file to stdout. Call choose_unzstd first (this runs inside a pipeline).
unzstd_cat() {
  [ -n "$UNZSTD" ] || die "choose_unzstd was not called"
  if [ "$UNZSTD" = zstd ]; then
    zstd -dc -- "$1"
  else
    "$UNZSTD" -c 'import shutil, sys
from compression import zstd
with zstd.open(sys.argv[1], "rb") as f:
    shutil.copyfileobj(f, sys.stdout.buffer, 1 << 20)' "$1"
  fi
}

# Mathlib's CACHEDIR (Cache/IO.lean): MATHLIB_CACHE_DIR, else $XDG_CACHE_HOME/mathlib, else
# $HOME/.cache/mathlib. A relative value is relative to the project directory, where
# `lake exe cache` runs.
mathlib_cache_dir() {
  local d
  if [ -n "${MATHLIB_CACHE_DIR+x}" ]; then
    [ -n "$MATHLIB_CACHE_DIR" ] || die "MATHLIB_CACHE_DIR is set but empty"
    d="$MATHLIB_CACHE_DIR"
  elif [ -n "${XDG_CACHE_HOME+x}" ]; then
    [ -n "$XDG_CACHE_HOME" ] || die "XDG_CACHE_HOME is set but empty"
    d="$XDG_CACHE_HOME/mathlib"
  else
    d="$HOME/.cache/mathlib"
  fi
  case "$d" in /*) ;; *) d="$WORK/$d" ;; esac
  printf '%s\n' "$d"
}

count_ltar() { find "$1" -maxdepth 1 -name '*.ltar' 2>/dev/null | wc -l; }

install_elan() {
  step "elan $ELAN_VERSION -> $ELAN_HOME"
  if [ -x "$ELAN_HOME/bin/elan" ]; then
    local have
    have="$("$ELAN_HOME/bin/elan" --version | awk '{print $2}')"
    LOG "elan $have already installed"
    [ "$have" = "$ELAN_VERSION" ] || LOG "WARNING: pinned elan is $ELAN_VERSION, keeping installed $have"
  else
    local d a run=()
    mktmp d
    if have_artifact "$ELAN_ARCHIVE"; then
      a="$ART/$ELAN_ARCHIVE"
      LOG "source: artifact $a"
      run=(offline)
    else
      [ "$OFFLINE" = 0 ] || refuse_online "elan is not installed and $ELAN_ARCHIVE is missing"
      LOG "source: online (github.com/leanprover/elan release v$ELAN_VERSION)"
      a="$d/$ELAN_ARCHIVE"
      curl -fsSL --retry 3 -o "$a" \
        "https://github.com/leanprover/elan/releases/download/v$ELAN_VERSION/$ELAN_ARCHIVE"
    fi
    tar -xzf "$a" -C "$d"
    "${run[@]}" env ELAN_INIT_SKIP_SUDO_CHECK=yes ELAN_INIT_SKIP_PATH_CHECK=yes \
      "$d/elan-init" -y --no-modify-path --default-toolchain none
  fi
  LOG "$(elan --version)"
  step_done
}

install_toolchain() {
  step "Lean toolchain $LEAN_TOOLCHAIN -> $TC_DIR"
  local d
  if [ -x "$TC_DIR/bin/lean" ]; then
    LOG "already installed"
  elif have_artifact "$LEAN_ARCHIVE"; then
    LOG "source: artifact $ART/$LEAN_ARCHIVE"
    choose_unzstd
    mkdir -p "$ELAN_HOME/toolchains"
    # Extract next to the final location, then rename: an interrupted run leaves no half toolchain.
    mktmp d "$ELAN_HOME/toolchains"
    unzstd_cat "$ART/$LEAN_ARCHIVE" | tar -xf - -C "$d"
    [ -x "$d/$LEAN_TOPDIR/bin/lean" ] || die "$LEAN_ARCHIVE has no $LEAN_TOPDIR/bin/lean"
    mv "$d/$LEAN_TOPDIR" "$TC_DIR"
  else
    [ "$OFFLINE" = 0 ] || refuse_online "the toolchain is not installed and $LEAN_ARCHIVE is missing"
    LOG "source: online (elan toolchain install)"
    elan toolchain install "$LEAN_TOOLCHAIN"
  fi
  [ -x "$TC_DIR/bin/lean" ] || die "toolchain not found at $TC_DIR"
  LOG "toolchains: $(ls "$ELAN_HOME/toolchains" | tr '\n' ' ')"
  step_done
}

install_project_files() {
  step "project files -> $WORK"
  mkdir -p "$WORK/MathverifyLean"
  local f changed=0
  for f in "${PROJECT_FILES[@]}"; do
    if ! cmp -s "$ROOT/lean/$f" "$WORK/$f"; then
      cp "$ROOT/lean/$f" "$WORK/$f"
      LOG "wrote $f"
      changed=$((changed + 1))
    fi
  done
  LOG "$changed file(s) changed"
  # elan must resolve the project's lean-toolchain to the pinned directory. After an artifact
  # install this runs with the network cut off, so a download attempt fails here.
  local run=() prefix
  [ -z "$ART" ] || run=(offline)
  cd "$WORK"
  prefix="$("${run[@]}" lean --print-prefix)" || die "elan could not resolve $LEAN_TOOLCHAIN without a download"
  [ "$(cd "$prefix" && pwd -P)" = "$(cd "$TC_DIR" && pwd -P)" ] || die "project resolves to $prefix, expected $TC_DIR"
  LOG "resolved offline=$([ -n "$ART" ] && echo yes || echo no): $prefix"
  LOG "$("${run[@]}" lean --version)"
  LOG "$("${run[@]}" lake --version)"
  step_done
}

# Lake clones every package of lake-manifest.json that is missing from .lake/packages (from
# github.com; mathlib4 alone brings ~500 MB of history). A checkout whose HEAD already is the
# manifest revision is used as it is, with no git network access (Lake's
# PackageEntry.materialize), so the sources artifact provides one shallow checkout per package,
# origin set to the manifest URL. Checkouts already at their revision are kept; any other content
# of a package directory is replaced. SOURCES=1: every package came from, or already matched, it.
SOURCES=0
install_sources() {
  step "Lake package sources -> $WORK/.lake/packages"
  if ! have_artifact "$SOURCES_ARCHIVE"; then
    [ "$OFFLINE" = 0 ] || refuse_online "$SOURCES_ARCHIVE is missing (Lake would clone the packages)"
    LOG "source: online (lake clones the packages from their manifest URLs)"
    step_done
    return 0
  fi
  LOG "source: artifact $ART/$SOURCES_ARCHIVE"
  local d name url rev pkg kept=0 added=0
  mkdir -p "$WORK/.lake/packages"
  # Extract next to the final location (one filesystem), then rename each package into place.
  mktmp d "$WORK/.lake"
  tar -xzf "$ART/$SOURCES_ARCHIVE" -C "$d" --no-same-owner packages
  while read -r name url rev; do
    pkg="$WORK/.lake/packages/$name"
    if [ -d "$pkg/.git" ] && [ "$(gitq -C "$pkg" rev-parse -q --verify HEAD 2>/dev/null)" = "$rev" ]; then
      kept=$((kept + 1))
      continue
    fi
    [ -d "$d/packages/$name/.git" ] || die "$SOURCES_ARCHIVE has no packages/$name"
    verify_checkout "$d/packages/$name" "$url" "$rev"
    if [ -e "$pkg" ]; then
      LOG "$name: replacing $pkg (HEAD $(gitq -C "$pkg" rev-parse -q --verify HEAD 2>/dev/null || echo none))"
      rm -rf "$pkg"
    fi
    mv "$d/packages/$name" "$pkg"
    added=$((added + 1))
  done <<< "$PKGS"
  # Now, not on exit: a staged project is renamed before then and would carry it along.
  rm -rf "$d"
  SOURCES=1
  LOG "$added package(s) installed from the artifact, $kept already at their revision"
  step_done
}

# With the .ltar archive from the artifacts the cache is complete for MATHLIB_REV (only what the
# server lacks too is missing), so `cache unpack` is used: it never contacts the cache server.
# Without it, `cache get` downloads from the Mathlib cache server.
CACHE_CMD=get
install_mathlib_ltar() {
  step "Mathlib .ltar cache -> $CACHE_DIR"
  local top
  mkdir -p "$CACHE_DIR"
  if have_artifact "$MATHLIB_ARCHIVE"; then
    LOG "source: artifact $ART/$MATHLIB_ARCHIVE ($(count_ltar "$CACHE_DIR") .ltar present before)"
    top="$(tar -tf "$ART/$MATHLIB_ARCHIVE" | cut -d/ -f1 | sort -u)"
    [ "$top" = mathlib ] || die "$MATHLIB_ARCHIVE: expected one top directory mathlib/, got: $top"
    tar -xf "$ART/$MATHLIB_ARCHIVE" -C "$CACHE_DIR" --strip-components=1 --skip-old-files
    CACHE_CMD=unpack
  else
    [ "$OFFLINE" = 0 ] || refuse_online "$MATHLIB_ARCHIVE is missing (lake exe cache get would download it)"
    LOG "source: online (lake exe cache get downloads from the Mathlib cache server)"
  fi
  LOG "$(count_ltar "$CACHE_DIR") .ltar in $CACHE_DIR"
  step_done
}

# With the package sources and the .ltar cache both from the artifacts (always so in offline
# mode), every lake command below runs offline: a clone or a download attempt fails loudly
# instead of silently using the network.
LAKE_RUN=()
cache_fetch() {
  local before after rc d
  if [ "$OFFLINE" = 1 ] && { [ "$SOURCES" != 1 ] || [ "$CACHE_CMD" != unpack ]; }; then
    refuse_online "lake exe cache $CACHE_CMD without the artifact sources and .ltar"
  fi
  if [ "$SOURCES" = 1 ] && [ "$CACHE_CMD" = unpack ]; then
    LAKE_RUN=(offline)
    step "lake exe cache unpack (offline: packages and .ltar from the artifacts; unpacks .ltar into oleans)"
  else
    step "lake exe cache $CACHE_CMD (clones missing packages, fetches missing .ltar, unpacks .ltar into oleans)"
  fi
  mktmp d
  before="$(count_ltar "$CACHE_DIR")"
  cd "$WORK"
  set +e
  "${LAKE_RUN[@]}" lake exe cache "$CACHE_CMD" 2>&1 | tr '\r' '\n' \
    | grep --line-buffered -v -E '^[[:space:]]*$' | tee "$d/cache.log"
  rc=${PIPESTATUS[0]}
  set -e
  after="$(count_ltar "$CACHE_DIR")"
  LOG "cache $CACHE_CMD exit code $rc; .ltar downloaded: $((after - before)); lake clones: $(grep -c ': cloning ' "$d/cache.log" || true)"
  if [ "$SOURCES" = 1 ] && grep -q ': cloning ' "$d/cache.log"; then
    die "lake cloned a package although $SOURCES_ARCHIVE provided all of them"
  fi
  # A failed download is not fatal by itself: the olean check and the smoke test below decide.
  [ "$rc" -eq 0 ] || LOG "WARNING: lake exe cache $CACHE_CMD failed (exit $rc); checking the build state"
  step_done
}

check_pins() {
  step "pinned revisions"
  cd "$WORK"
  cmp -s "$ROOT/lean/lake-manifest.json" lake-manifest.json \
    || die "lake-manifest.json differs from the pinned lean/lake-manifest.json (changed by lake?)"
  local pkgs name url rev head origin n=0 shallow=0
  pkgs="$(manifest_packages lake-manifest.json)"
  while read -r name url rev; do
    [ -d ".lake/packages/$name/.git" ] || die "package $name is missing"
    head="$(gitq -C ".lake/packages/$name" rev-parse HEAD 2>/dev/null)" || die "package $name has no HEAD"
    [ "$head" = "$rev" ] || die "package $name is at $head, manifest pins $rev"
    # Lake deletes and clones again a package whose origin differs from the manifest URL.
    origin="$(gitq -C ".lake/packages/$name" remote get-url origin 2>/dev/null)" || die "package $name has no origin"
    [ "$origin" = "$url" ] || die "package $name has origin $origin, manifest URL $url"
    [ "$(gitq -C ".lake/packages/$name" rev-parse --is-shallow-repository)" = false ] || shallow=$((shallow + 1))
    n=$((n + 1))
  done <<< "$pkgs"
  [ "$n" -gt 0 ] || die "no packages read from lake-manifest.json"
  head="$(gitq -C .lake/packages/mathlib rev-parse HEAD)"
  [ "$head" = "$MATHLIB_REV" ] || die "mathlib HEAD $head != MATHLIB_REV $MATHLIB_REV"
  LOG "$n package(s) at their manifest revisions with origin = manifest URL ($shallow shallow); mathlib HEAD = MATHLIB_REV = $MATHLIB_REV"
  step_done
}

# Mathlib modules (paths without .lean) under Mathlib/ that have no olean, one per line.
MATHLIB_LIB=.lake/packages/mathlib/.lake/build/lib/lean
missing_oleans() {
  local m
  while read -r m; do
    [ -f "$MATHLIB_LIB/${m%.lean}.olean" ] || printf '%s\n' "${m%.lean}"
  done < <(cd .lake/packages/mathlib && find Mathlib -name '*.lean' | sort)
}

# The prebuilt cache for MATHLIB_REV lacks two modules, the root Mathlib and
# Mathlib/Probability/Kernel/Invariance (measured 2026-09-24: `cache get` tried 2 downloads from
# cache.mathlib.org and found none). `lake build Mathlib` compiles just those two on top of the
# cached oleans (12 s on 4 CPUs). A large gap would mean a multi-hour full build: fail fast.
MAX_MISSING_OLEANS=20
build_root_if_missing() {
  step "Mathlib oleans"
  cd "$WORK"
  local rc missing=()
  mapfile -t missing < <(missing_oleans)
  LOG "$(find "$MATHLIB_LIB/Mathlib" -name '*.olean' | wc -l) module oleans under Mathlib/, ${#missing[@]} missing; root Mathlib.olean $([ -f "$MATHLIB_LIB/Mathlib.olean" ] && echo present || echo missing)"
  [ "${#missing[@]}" -eq 0 ] || printf '  missing: %s\n' "${missing[@]:0:$MAX_MISSING_OLEANS}"
  if [ "${#missing[@]}" -gt "$MAX_MISSING_OLEANS" ]; then
    die "${#missing[@]} Mathlib modules have no olean after cache $CACHE_CMD (limit $MAX_MISSING_OLEANS); refusing a full Mathlib build"
  fi
  if [ "${#missing[@]}" -gt 0 ] || [ ! -f "$MATHLIB_LIB/Mathlib.olean" ]; then
    LOG "building the missing modules (lake build Mathlib)"
    set +e
    "${LAKE_RUN[@]}" lake build Mathlib 2>&1 | tr '\r' '\n' | grep --line-buffered -v -E '^[[:space:]]*$' | tail -n 8
    rc=${PIPESTATUS[0]}
    set -e
    [ "$rc" -eq 0 ] || die "lake build Mathlib failed (exit $rc)"
    [ -f "$MATHLIB_LIB/Mathlib.olean" ] || die "lake build Mathlib did not produce Mathlib.olean"
    mapfile -t missing < <(missing_oleans)
    # Modules outside Mathlib.lean's import closure are not built by `lake build Mathlib`.
    [ "${#missing[@]}" -eq 0 ] || LOG "WARNING: still without olean (not imported by Mathlib.lean?): ${missing[*]:0:10}"
  fi
  step_done
}

# lake/leantar write cached oleans with mode 0600. When root installs for a session that runs as
# another user, those files would be unreadable, so everything under the project and the elan
# home is made world-readable (directories world-searchable).
make_world_readable() {
  step "permissions"
  local d n
  for d in "$WORK" "$ELAN_HOME"; do
    n="$(find "$d" ! -perm -o+r | wc -l)"
    chmod -R a+rX "$d"
    LOG "$d: $n entries were not world-readable; now $(find "$d" ! -perm -o+r | wc -l)"
  done
  step_done
}

# Lake runs git in every package checkout on each start (`lake env` included) and treats a git
# failure as a changed URL: it deletes the package and clones it again (measured: without git on
# PATH, `lake env` deleted .lake/packages/mathlib). A session user who does not own a root-made
# install hits git's "dubious ownership" refusal, so root registers the exact checkout paths as
# safe directories in the system git config (Ubuntu 24.04's git 2.43 has no path wildcard).
trust_package_repos() {
  step "git safe.directory for the package checkouts (root install)"
  local d n=0 have
  have="$(git config --system --get-all safe.directory 2>/dev/null || true)"
  for d in "$PROJ"/.lake/packages/*/; do
    [ -d "$d/.git" ] || continue
    d="$(cd "$d" && pwd -P)"
    if ! printf '%s\n' "$have" | grep -Fqx -- "$d"; then
      git config --system --add safe.directory "$d"
      n=$((n + 1))
    fi
  done
  LOG "$n path(s) added; system git config now lists $(git config --system --get-all safe.directory | wc -l) safe.directory entries"
  step_done
}

SMOKE_FILE=""
SMOKE_WHY=""
# smoke_passes DIR: run the smoke file with Lake in project directory DIR and print its output.
# On failure it returns 1 with the reason in SMOKE_WHY (the caller decides what to undo).
smoke_passes() {
  local out
  out="$(cd "$1" && "${LAKE_RUN[@]}" lake env lean "$SMOKE_FILE" 2>&1)" \
    || { printf '%s\n' "$out"; SMOKE_WHY="smoke test failed in $1"; return 1; }
  printf '%s\n' "$out"
  case "$out" in *sorryAx*) SMOKE_WHY="smoke proof depends on sorryAx"; return 1 ;; esac
  case "$out" in *"depends on axioms"*) ;; *) SMOKE_WHY="smoke test printed no axiom list"; return 1 ;; esac
}

smoke_test() {
  step "smoke test: import Mathlib + norm_num"
  local d
  mktmp d
  cat > "$d/Smoke.lean" <<'LEAN'
import Mathlib
theorem smoke (x : ℝ) (h : x = 2) : x + 2 = 4 := by subst h; norm_num
#print axioms smoke
LEAN
  SMOKE_FILE="$d/Smoke.lean"
  smoke_passes "$WORK" || die "$SMOKE_WHY"
  LOG "SMOKE OK"
  step_done
}

# Every artifact this run will use is verified before anything is written. In offline mode a
# missing one stops the run here; otherwise it is fetched online later.
preflight() {
  step "artifacts (verified before anything is written)"
  [ "$OFFLINE" = 0 ] || [ -n "$ART" ] || refuse_online "MATHVERIFY_ARTIFACT_DIR is not set"
  if [ -x "$ELAN_HOME/bin/elan" ]; then
    LOG "elan already installed; $ELAN_ARCHIVE not needed"
  else
    want "$ELAN_ARCHIVE" "elan $ELAN_VERSION"
  fi
  if [ -x "$TC_DIR/bin/lean" ]; then
    LOG "toolchain already installed; $LEAN_ARCHIVE not needed"
  else
    want "$LEAN_ARCHIVE" "Lean toolchain $LEAN_TOOLCHAIN"
    # The decompressor may itself come from an artifact (or apt-get, refused offline).
    if have_artifact "$LEAN_ARCHIVE"; then choose_unzstd; fi
  fi
  want "$SOURCES_ARCHIVE" "Lake package sources"
  want "$MATHLIB_ARCHIVE" "Mathlib .ltar cache"
  step_done
}

# Staging and swap directories live next to $PROJ (one filesystem, so a rename moves them):
# .<name>.stage.<pid> while a run builds, .<name>.old.<pid> during a swap.
PROJ_PARENT="$(dirname "$PROJ")"
PROJ_BASE="$(basename "$PROJ")"

# Leftovers of runs that died (their pid is gone): a staging or temporary .ltar directory is
# removed; an old project moved aside by an interrupted swap is put back when $PROJ is missing,
# else removed.
clean_leftovers() {
  local d pid
  local stale=("$PROJ_PARENT/.$PROJ_BASE".stage.* "$PROJ_PARENT/.$PROJ_BASE".ltar.*
               "$PROJ_PARENT/.$PROJ_BASE".old.*)
  for d in "${stale[@]}"; do
    [ -d "$d" ] || continue
    pid="${d##*.}"
    case "$pid" in ''|*[!0-9]*) continue ;; esac
    ! kill -0 "$pid" 2>/dev/null || continue
    case "$d" in
      *.old.*)
        if [ ! -e "$PROJ" ]; then
          LOG "restoring $PROJ from $d (an interrupted swap)"
          mv -T "$d" "$PROJ"
          continue
        fi ;;
    esac
    LOG "removing $d (left by a run that died)"
    rm -rf "$d"
  done
}

# True when directory $1 already holds the pinned project files and every manifest package at its
# revision with origin = manifest URL: what is left to do there only adds files.
project_matches_pins() {
  local d="$1" f name url rev
  for f in "${PROJECT_FILES[@]}"; do cmp -s "$ROOT/lean/$f" "$d/$f" || return 1; done
  while read -r name url rev; do
    [ -d "$d/.lake/packages/$name/.git" ] || return 1
    [ "$(gitq -C "$d/.lake/packages/$name" rev-parse -q --verify HEAD 2>/dev/null)" = "$rev" ] || return 1
    [ "$(gitq -C "$d/.lake/packages/$name" remote get-url origin 2>/dev/null)" = "$url" ] || return 1
  done <<< "$PKGS"
}

# Disk sizes in KiB, measured 2026-09-24 (du -sh) in the WSL end-to-end run and in the cloud: a
# finished project is 7.2 GB and the Mathlib .ltar cache it is unpacked from 448 MB, ~7.7 GB
# together (the .ltar land next to the project too: setup_env.sh uses $OPT/.mathlib-ltar, a run
# alone .<name>.ltar.<pid>); the toolchain under $ELAN_HOME is 3.0 GB (cloud). A margin of 1 GB
# comes on top of each check. Inside WSL, df sees the ext4 virtual disk (~1 TB), not the Windows
# drive that holds its .vhdx: these checks cannot notice that drive filling up.
NEW_PROJECT_KB=$(( 77 * 1048576 / 10 ))
TOOLCHAIN_KB=$(( 3 * 1048576 ))
MARGIN_KB=1048576
kb_gb() { awk -v k="$1" 'BEGIN {printf "%.1f", k / 1048576}'; }
# The nearest existing directory at or above $1 (a fresh $PROJ_PARENT or $ELAN_HOME may not exist
# yet; the install creates it).
existing_dir() {
  local d="$1"
  while [ ! -e "$d" ] && [ "$d" != / ] && [ "$d" != . ]; do d="$(dirname "$d")"; done
  printf '%s\n' "$d"
}
# need_space KB DIR WHAT: die unless KB plus the margin is free on DIR's filesystem (WHAT says
# what was left alone).
need_space() {
  local need=$(( $1 + MARGIN_KB )) d avail
  d="$(existing_dir "$2")"
  avail="$(df -Pk "$d" 2>/dev/null | awk 'NR == 2 {print $4}')" || true
  case "$avail" in ''|*[!0-9]*) die "cannot read the free disk space of $d (df -Pk); $3" ;; esac
  LOG "disk: $(kb_gb "$avail") GB free on $d, $(kb_gb "$need") GB needed ($(kb_gb "$1") GB + $(kb_gb "$MARGIN_KB") GB margin)"
  [ "$avail" -ge "$need" ] \
    || die "not enough disk on $d: ~$(kb_gb "$need") GB needed ($(kb_gb "$1") GB + $(kb_gb "$MARGIN_KB") GB margin), $(kb_gb "$avail") GB free; $3"
}
# check_disk PROJECT_KB WHAT: the project (PROJECT_KB next to $PROJ) and, when it is not installed
# yet, the toolchain; summed when both are on one filesystem.
check_disk() {
  local proj_kb="$1" tc_kb=0
  [ -x "$TC_DIR/bin/lean" ] || tc_kb="$TOOLCHAIN_KB"
  if [ "$tc_kb" -gt 0 ] && [ "$(stat -c %d "$(existing_dir "$ELAN_HOME")")" != "$(stat -c %d "$(existing_dir "$PROJ_PARENT")")" ]; then
    need_space "$tc_kb" "$ELAN_HOME" "$2"
    tc_kb=0
  fi
  [ $(( proj_kb + tc_kb )) -eq 0 ] || need_space $(( proj_kb + tc_kb )) "$PROJ_PARENT" "$2"
}

# Choose WORK: $PROJ for a fresh install (or an empty directory) and for a project that already
# matches the pins; otherwise a staging directory, swapped in by swap_in after the smoke test.
# It runs before the toolchain is installed, so the disk check precedes every large write.
choose_workdir() {
  step "project directory"
  clean_leftovers
  local used=0
  if [ ! -e "$PROJ" ] || { [ -d "$PROJ" ] && [ -z "$(ls -A "$PROJ")" ]; }; then
    check_disk "$NEW_PROJECT_KB" "nothing was installed"
    WORK="$PROJ"
    LOG "fresh install in $PROJ"
    step_done
    return 0
  fi
  [ -d "$PROJ" ] || die "$PROJ exists and is not a directory"
  used="$(du -sk "$PROJ" 2>/dev/null | cut -f1)" || true
  case "$used" in ''|*[!0-9]*) used=0 ;; esac
  if project_matches_pins "$PROJ"; then
    # What is left to add: an interrupted run may have unpacked no oleans yet.
    check_disk $(( used < NEW_PROJECT_KB ? NEW_PROJECT_KB - used : 0 )) "nothing was installed"
    WORK="$PROJ"
    LOG "$PROJ already has the pinned project files and package revisions; completing it in place"
  else
    # The new project sits next to the old one until the swap: the larger of a measured new build
    # and the old project's own size (it may hold more build output than a fresh one).
    [ "$used" -ge "$NEW_PROJECT_KB" ] || used="$NEW_PROJECT_KB"
    check_disk "$used" "$PROJ differs from the pins and is left untouched"
    WORK="$PROJ_PARENT/.$PROJ_BASE.stage.$$"
    rm -rf "$WORK"
    TMPS+=("$WORK")
    mkdir "$WORK" || die "cannot create $WORK (is $PROJ_PARENT writable?); $PROJ is left untouched"
    LOG "$PROJ differs from the pins: building the new project in $WORK; it replaces $PROJ only after its smoke test"
  fi
  step_done
}

# The Mathlib .ltar cache. With the archive from the artifacts and no MATHLIB_CACHE_DIR chosen by
# the caller, a private directory next to the project, removed on exit: the .ltar are only the
# input of `cache unpack` (setup_env.sh passes its own directory and removes it itself).
setup_cache_dir() {
  if [ -z "${MATHLIB_CACHE_DIR+x}" ] && have_artifact "$MATHLIB_ARCHIVE"; then
    export MATHLIB_CACHE_DIR="$PROJ_PARENT/.$PROJ_BASE.ltar.$$"
    TMPS+=("$MATHLIB_CACHE_DIR")
    rm -rf "$MATHLIB_CACHE_DIR"
    LOG "temporary MATHLIB_CACHE_DIR=$MATHLIB_CACHE_DIR (removed on exit)"
  fi
  CACHE_DIR="$(mathlib_cache_dir)"
}

# Put a staged project in place: move $PROJ aside, rename the staging directory to $PROJ, run the
# `import Mathlib` smoke test again there (the one before the rename ran under the staging path),
# and only then delete the old one (put back on any failure; if even that fails, the old one stays
# in .<name>.old.<pid>, which the next run restores or removes).
swap_in() {
  [ "$WORK" != "$PROJ" ] || return 0
  step "swap the staged project into $PROJ"
  local old="$PROJ_PARENT/.$PROJ_BASE.old.$$"
  rm -rf "$old"
  mv -T "$PROJ" "$old" || die "cannot move $PROJ aside; it is left untouched"
  if ! mv -T "$WORK" "$PROJ"; then
    mv -T "$old" "$PROJ" || die "cannot rename $WORK to $PROJ, nor put the previous project back from $old"
    die "cannot rename $WORK to $PROJ; the previous project was put back"
  fi
  LOG "smoke test again in $PROJ, before the previous project is deleted"
  if ! smoke_passes "$PROJ"; then
    { mv -T "$PROJ" "$WORK" && mv -T "$old" "$PROJ"; } \
      || die "$SMOKE_WHY after the swap, and putting the previous project back failed: it is in $old"
    die "$SMOKE_WHY after the swap; the previous project was put back"
  fi
  LOG "SMOKE OK in $PROJ"
  WORK="$PROJ"
  rm -rf "$old"
  step_done
}

main() {
  LOG "setup_lean: $(uname -srm), $(nproc) CPU(s), user $(id -un 2>/dev/null || id -u), HOME=$HOME"
  LOG "ELAN_HOME=$ELAN_HOME PROJECT=$PROJ ARTIFACTS=${ART:-(none)} OFFLINE=$OFFLINE"
  local t tools=(git tar sha256sum)
  [ "$OFFLINE" = 1 ] || tools+=(curl)
  for t in "${tools[@]}"; do
    command -v "$t" >/dev/null 2>&1 || die "$t not found"
  done
  PKGS="$(manifest_packages "$ROOT/lean/lake-manifest.json")"
  preflight
  choose_workdir
  install_elan
  install_toolchain
  setup_cache_dir
  install_project_files
  install_sources
  install_mathlib_ltar
  cache_fetch
  check_pins
  build_root_if_missing
  make_world_readable
  smoke_test
  swap_in
  if [ "$(id -u)" = 0 ]; then
    trust_package_repos
  else
    LOG "not root: the install belongs to $(id -un 2>/dev/null || id -u); no system git safe.directory entries"
  fi
  LOG "disk: $(du -sh "$ELAN_HOME" | cut -f1) $ELAN_HOME; $(du -sh "$PROJ" | cut -f1) $PROJ; $(du -sh "$CACHE_DIR" | cut -f1) $CACHE_DIR ($(count_ltar "$CACHE_DIR") .ltar$(case " ${TMPS[*]} " in *" $CACHE_DIR "*) echo ', temporary: removed on exit' ;; esac))"
  LOG "DONE in $(( $(date +%s) - T0 ))s (lake ran offline: $([ "${#LAKE_RUN[@]}" -gt 0 ] && echo yes || echo no))"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
