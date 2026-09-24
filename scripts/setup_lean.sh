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
#   MATHLIB_CACHE_DIR, XDG_CACHE_HOME
#                             Mathlib .ltar cache location, resolved exactly as Mathlib's
#                             Cache/IO.lean does (default $HOME/.cache/mathlib)
#   MATHVERIFY_OPT            cloud install prefix (default /opt); only used to find
#                             $MATHVERIFY_OPT/python3.14 as a zstd decompressor
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
export PATH="$ELAN_HOME/bin:$PATH"

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
# SHA256SUMS.full (hard failure on a mismatch or a missing entry). Never call it inside $(...):
# die must end the script, not a subshell.
have_artifact() {
  local name="$1" line
  [ -n "$ART" ] && [ -f "$ART/$name" ] || return 1
  [ -f "$ART/SHA256SUMS.full" ] || die "$ART has $name but no SHA256SUMS.full"
  line="$(awk -v n="$name" '{f = $2; sub(/^\*/, "", f); if (f == n) print}' "$ART/SHA256SUMS.full")"
  [ -n "$line" ] || die "$name is not listed in $ART/SHA256SUMS.full"
  (cd "$ART" && printf '%s\n' "$line" | sha256sum -c --strict --quiet -) \
    || die "SHA256 mismatch for $ART/$name"
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
      if [ "$(id -u)" = 0 ] && command -v apt-get >/dev/null 2>&1; then
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
  case "$d" in /*) ;; *) d="$PROJ/$d" ;; esac
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
    LOG "source: online (elan toolchain install)"
    elan toolchain install "$LEAN_TOOLCHAIN"
  fi
  [ -x "$TC_DIR/bin/lean" ] || die "toolchain not found at $TC_DIR"
  LOG "toolchains: $(ls "$ELAN_HOME/toolchains" | tr '\n' ' ')"
  step_done
}

install_project_files() {
  step "project files -> $PROJ"
  mkdir -p "$PROJ/MathverifyLean"
  local f changed=0
  for f in "${PROJECT_FILES[@]}"; do
    if ! cmp -s "$ROOT/lean/$f" "$PROJ/$f"; then
      cp "$ROOT/lean/$f" "$PROJ/$f"
      LOG "wrote $f"
      changed=$((changed + 1))
    fi
  done
  LOG "$changed file(s) changed"
  # elan must resolve the project's lean-toolchain to the pinned directory. After an artifact
  # install this runs with the network cut off, so a download attempt fails here.
  local run=() prefix
  [ -z "$ART" ] || run=(offline)
  cd "$PROJ"
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
  step "Lake package sources -> $PROJ/.lake/packages"
  if ! have_artifact "$SOURCES_ARCHIVE"; then
    LOG "source: online (lake clones the packages from their manifest URLs)"
    step_done
    return 0
  fi
  LOG "source: artifact $ART/$SOURCES_ARCHIVE"
  local d pkgs name url rev pkg kept=0 added=0
  pkgs="$(manifest_packages "$ROOT/lean/lake-manifest.json")"
  mkdir -p "$PROJ/.lake/packages"
  # Extract next to the final location (one filesystem), then rename each package into place.
  mktmp d "$PROJ/.lake"
  tar -xzf "$ART/$SOURCES_ARCHIVE" -C "$d" --no-same-owner packages
  while read -r name url rev; do
    pkg="$PROJ/.lake/packages/$name"
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
  done <<< "$pkgs"
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
    LOG "source: online (lake exe cache get downloads from the Mathlib cache server)"
  fi
  LOG "$(count_ltar "$CACHE_DIR") .ltar in $CACHE_DIR"
  step_done
}

# With the package sources and the .ltar cache both from the artifacts, every lake command below
# runs offline: a clone or a download attempt fails loudly instead of silently using the network.
LAKE_RUN=()
cache_fetch() {
  local before after rc d
  if [ "$SOURCES" = 1 ] && [ "$CACHE_CMD" = unpack ]; then
    LAKE_RUN=(offline)
    step "lake exe cache unpack (offline: packages and .ltar from the artifacts; unpacks .ltar into oleans)"
  else
    step "lake exe cache $CACHE_CMD (clones missing packages, fetches missing .ltar, unpacks .ltar into oleans)"
  fi
  mktmp d
  before="$(count_ltar "$CACHE_DIR")"
  cd "$PROJ"
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
  cd "$PROJ"
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
  cd "$PROJ"
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
  for d in "$PROJ" "$ELAN_HOME"; do
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

smoke_test() {
  step "smoke test: import Mathlib + norm_num"
  cd "$PROJ"
  local d out
  mktmp d
  cat > "$d/Smoke.lean" <<'LEAN'
import Mathlib
theorem smoke (x : ℝ) (h : x = 2) : x + 2 = 4 := by subst h; norm_num
#print axioms smoke
LEAN
  out="$("${LAKE_RUN[@]}" lake env lean "$d/Smoke.lean" 2>&1)" || { printf '%s\n' "$out"; die "smoke test failed"; }
  printf '%s\n' "$out"
  case "$out" in *sorryAx*) die "smoke proof depends on sorryAx" ;; esac
  case "$out" in *"depends on axioms"*) ;; *) die "smoke test printed no axiom list" ;; esac
  LOG "SMOKE OK"
  step_done
}

main() {
  LOG "setup_lean: $(uname -srm), $(nproc) CPU(s), user $(id -un 2>/dev/null || id -u), HOME=$HOME"
  LOG "ELAN_HOME=$ELAN_HOME PROJECT=$PROJ ARTIFACTS=${ART:-(none)}"
  local t
  for t in curl git tar sha256sum; do
    command -v "$t" >/dev/null 2>&1 || die "$t not found"
  done
  CACHE_DIR="$(mathlib_cache_dir)"
  install_elan
  install_toolchain
  install_project_files
  install_sources
  install_mathlib_ltar
  cache_fetch
  check_pins
  build_root_if_missing
  make_world_readable
  if [ "$(id -u)" = 0 ]; then
    trust_package_repos
  else
    LOG "not root: the install belongs to $(id -un 2>/dev/null || id -u); no system git safe.directory entries"
  fi
  smoke_test
  LOG "disk: $(du -sh "$ELAN_HOME" | cut -f1) $ELAN_HOME; $(du -sh "$PROJ" | cut -f1) $PROJ; $(du -sh "$CACHE_DIR" | cut -f1) $CACHE_DIR"
  LOG "DONE in $(( $(date +%s) - T0 ))s (lake ran offline: $([ "${#LAKE_RUN[@]}" -gt 0 ] && echo yes || echo no))"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
