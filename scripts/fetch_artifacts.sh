#!/usr/bin/env bash
# Fetch the offline tool artifacts used by cloud sessions (Lean toolchain, elan, the Mathlib .ltar
# cache, the Lake package and REPL sources, a standalone CPython), reassemble the split parts and
# verify every file against SHA256SUMS.full. The cloud GitHub proxy blocks release assets of
# repositories that are not attached to the session, so these files live in this repository under
# a non-branch git ref.
#
# Usage: scripts/fetch_artifacts.sh [DEST]
#   DEST   defaults to ${MATHVERIFY_ARTIFACT_DIR:-$HOME/.cache/mathverify/arac}
# Source (first match wins):
#   MATHVERIFY_ARTIFACT_SRC   local directory holding parts/ and SHA256SUMS.full (offline use)
#   otherwise ${MATHVERIFY_ARTIFACT_REF:-refs/arac/bulut-v2} from
#   ${MATHVERIFY_ARTIFACT_URL:-<origin remote of this repository>}, fetched
#     1. shallow into a fresh temporary repository that carries this checkout's repo-local
#        http.*, credential.* and url.* settings; if that fails and MATHVERIFY_GITHUB_TOKEN is set,
#        the same fetch again with that token (below); if that fails too,
#     2. with the same token, file by file from ${MATHVERIFY_GITHUB_RAW_URL-https://raw.githubusercontent.com/}
#        <owner>/<repo>/$REF/: SHA256SUMS.full, SHA256SUMS.parts and every part it lists, each
#        part checked against it (the raw host sits behind the session's security proxy, not its
#        GitHub proxy; measured 25 Sep 2026 in a session: without the header 404, with a bogus
#        token 404, with the real token 200, i.e. the header reaches GitHub unchanged, while the
#        GitHub proxy answers api.github.com with its own credential whatever header is sent);
#        if that fails too,
#     3. by `git fetch` run inside this checkout (its remotes, full config and credentials), with
#        the received objects written to the temporary object store instead of the checkout's,
#        which serves only as an alternate: no ref, FETCH_HEAD or object is added to the checkout.
#   MATHVERIFY_ARTIFACT_VIA=raw skips the git steps and uses only step 2 (to measure it).
# MATHVERIFY_GITHUB_TOKEN: a GitHub token that can read this repository (fine-grained, Contents:
#   read-only), for the claude.ai setup script. It runs before Claude Code connects to the
#   session's GitHub proxy, so the private repository answered 401 there (measured 24 Sep 2026)
#   while the same fetch works inside the session. The token is sent only after the plain fetch
#   failed (inside a session the proxy authenticates and the token is never sent), only to URLs
#   under ${MATHVERIFY_GITHUB_TOKEN_URL:-https://github.com/}, as HTTP basic auth (user: the
#   repository owner) in an extra header passed through GIT_CONFIG_* in the environment of that
#   one git command: never on a command line, in a log or on disk. Step 2 sends it only for a
#   remote under that prefix, as "Authorization: token ..." read by curl from a config on stdin
#   (never an argv), with no redirect followed, so it never goes to a third host.
#   The claude.ai environment's variables do NOT reach the setup script (measured 25 Sep 2026:
#   the session had the variable, the setup-script run logged it unset), so it is pasted into the
#   setup script's own text, which hands it to scripts/cloud/setup_env.sh (docs/BULUT.md).
# Idempotent: when DEST already verifies against its SHA256SUMS.full and was produced from the
# same source (same ref name, or a byte-identical SHA256SUMS.full for a local source), nothing is
# fetched. A ref is never rewritten in place; new content gets a new ref name (bulut-v3, ...).
set -euo pipefail
export LC_ALL=C

T0=$(date +%s)
LOG() { echo "[$(date +%H:%M:%S) +$(( $(date +%s) - T0 ))s] fetch_artifacts: $*"; }
die() { LOG "ERROR: $*" >&2; exit 1; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-${MATHVERIFY_ARTIFACT_DIR:-$HOME/.cache/mathverify/arac}}"
REF="${MATHVERIFY_ARTIFACT_REF:-refs/arac/bulut-v2}"
SRC="${MATHVERIFY_ARTIFACT_SRC:-}"
VIA="${MATHVERIFY_ARTIFACT_VIA:-auto}"
case "$VIA" in auto|raw) ;; *) die "MATHVERIFY_ARTIFACT_VIA must be auto or raw, not $VIA" ;; esac
# The token stays in this shell (whitespace a paste may leave around it would only turn it into a
# 401): git, curl and every other child of this script get no copy of it in their environment.
TOKEN="${MATHVERIFY_GITHUB_TOKEN:-}"
TOKEN="${TOKEN//[[:space:]]/}"
unset MATHVERIFY_GITHUB_TOKEN

command -v sha256sum >/dev/null 2>&1 || die "sha256sum not found"

# Source identity recorded in DEST/.source; the idempotence check compares against it.
if [ -n "$SRC" ]; then
  [ -f "$SRC/SHA256SUMS.full" ] || die "MATHVERIFY_ARTIFACT_SRC=$SRC has no SHA256SUMS.full"
  [ -d "$SRC/parts" ] || die "MATHVERIFY_ARTIFACT_SRC=$SRC has no parts/ directory"
  SOURCE_ID="src sha256(SHA256SUMS.full)=$(sha256sum < "$SRC/SHA256SUMS.full" | cut -d' ' -f1)"
else
  command -v git >/dev/null 2>&1 || die "git not found"
  SOURCE_ID="ref $REF"
fi

dest_verifies() {
  [ -f "$DEST/SHA256SUMS.full" ] && [ -f "$DEST/.source" ] || return 1
  [ "$(head -n 1 "$DEST/.source")" = "$SOURCE_ID" ] || return 1
  (cd "$DEST" && sha256sum -c --strict --quiet SHA256SUMS.full >/dev/null 2>&1)
}

mkdir -p "$DEST"
DEST="$(cd "$DEST" && pwd)"
LOG "destination $DEST, source: $SOURCE_ID"
if dest_verifies; then
  LOG "already present and verified; nothing to do (total $(( $(date +%s) - T0 ))s)"
  exit 0
fi

# Work inside DEST so the final moves stay on one filesystem. mktemp -d makes it private (0700):
# the temporary repository may hold copied credential settings.
WORK="$(mktemp -d "$DEST/.fetch.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/out"

# git on this checkout. safe.directory (these commands only): the setup script may run as root on
# a checkout owned by another user, where git refuses to read the repository otherwise.
rgit() { git -c safe.directory='*' -C "$ROOT" "$@"; }

# Copy this checkout's repo-local http.*, credential.* and url.* settings (including files that
# its .git/config includes) into the git directory $1: a proxy, an extra header or a URL rewrite
# configured for this clone only. Global and system settings apply to $1 anyway. Values are never
# printed: they may hold tokens.
copy_git_config() {
  local rec key val n=0
  while IFS= read -r -d '' rec; do
    key="${rec%%$'\n'*}"
    if [ "$key" = "$rec" ]; then val=true; else val="${rec#*$'\n'}"; fi
    git --git-dir="$1" config --add "$key" "$val"
    n=$((n + 1))
  done < <(rgit config --local --includes --null --get-regexp '^(http|credential|url)\.' 2>/dev/null || true)
  LOG "copied $n repo-local http/credential/url setting(s) from $ROOT"
}

TOKEN_URL="${MATHVERIFY_GITHUB_TOKEN_URL:-https://github.com/}"

# 0 when MATHVERIFY_GITHUB_TOKEN may be sent to $URL; logs why not otherwise (never the value).
token_applies() {
  if [ -z "$TOKEN" ]; then
    LOG "MATHVERIFY_GITHUB_TOKEN is not set: no token retry (claude.ai environment variables do not reach the setup script; put it in the setup script's text, docs/BULUT.md)"
    return 1
  fi
  case "$URL" in
    "$TOKEN_URL"*) return 0 ;;
  esac
  # user:password@ is cut from the logged URL: a clone URL may carry credentials of its own
  LOG "MATHVERIFY_GITHUB_TOKEN is set but $(printf '%s' "$URL" | sed -E 's#//[^/@]*@#//#') is not under $TOKEN_URL: token not sent"
  return 1
}

# Run "$@" with the token as HTTP basic auth for URLs under $TOKEN_URL. A subshell, so the header
# exists only in the environment of this one command; printf and export are builtins, so the
# token never appears in an argv. Entries already in GIT_CONFIG_* (a cloud session sets some)
# are kept: the header is appended after them.
with_token() (
  owner="${URL#"$TOKEN_URL"}"
  owner="${owner%%/*}"
  [ -n "$owner" ] || owner=x-access-token
  auth="$(printf '%s:%s' "$owner" "$TOKEN" | base64 | tr -d '\n')"
  n="${GIT_CONFIG_COUNT:-0}"
  export "GIT_CONFIG_KEY_$n=http.$TOKEN_URL.extraHeader"
  export "GIT_CONFIG_VALUE_$n=Authorization: Basic $auth"
  export GIT_CONFIG_COUNT=$((n + 1))
  "$@"
)

RAW_URL="${MATHVERIFY_GITHUB_RAW_URL-https://raw.githubusercontent.com/}"
RAWDIR=""

# <owner>/<repo> of $URL under $TOKEN_URL (a trailing .git or / is dropped); 1 when it is not one.
repo_path() {
  local p="${URL#"$TOKEN_URL"}"
  p="${p%/}"; p="${p%.git}"
  case "$p" in ''|/*|*/|*/*/*|*[!A-Za-z0-9._/-]*) return 1 ;; */*) printf '%s\n' "$p" ;; *) return 1 ;; esac
}

# 0 when the raw download may be tried. Silent when there is no token or the remote is not under
# $TOKEN_URL: token_applies has logged that already.
raw_applies() {
  [ -n "$TOKEN" ] || return 1
  case "$URL" in "$TOKEN_URL"*) ;; *) return 1 ;; esac
  [ -n "$RAW_URL" ] || { LOG "MATHVERIFY_GITHUB_RAW_URL is empty: no raw download"; return 1; }
  command -v curl >/dev/null 2>&1 || { LOG "curl not found: no raw download"; return 1; }
  repo_path >/dev/null || { LOG "the remote is not <owner>/<repo> under $TOKEN_URL: no raw download"; return 1; }
  # the value goes into a curl config line: only the characters GitHub tokens are made of
  case "$TOKEN" in
    *[!A-Za-z0-9_]*) LOG "MATHVERIFY_GITHUB_TOKEN has characters no GitHub token has: no raw download"; return 1 ;;
  esac
}

# raw_get PATH OUT: $RAW_URL<owner>/<repo>/$REF/PATH into OUT, the token in a header that curl
# reads from a config on stdin (printf is a builtin: the value is in no argv). Redirects are not
# followed, so the header never goes to another host.
raw_get() {
  local code
  code="$(printf 'header = "Authorization: token %s"\n' "$TOKEN" \
          | curl -sS -K - --connect-timeout 20 --max-time 900 --retry 3 --retry-delay 2 \
              -o "$2" -w '%{http_code}' "$RAW_URL$(repo_path)/$REF/$1")" || true
  [ "$code" = 200 ] && return 0
  LOG "raw download of $1 failed (HTTP ${code:-none})"
  return 1
}

# Download the ref's checksum lists and every part listed in SHA256SUMS.parts into $RAWDIR, each
# part checked against it. On failure nothing is left behind and RAWDIR is empty again.
raw_fetch() {
  local sum name n=0 t
  t=$(date +%s)
  RAWDIR="$WORK/raw"
  mkdir -p "$RAWDIR/parts"
  if raw_get SHA256SUMS.full "$RAWDIR/SHA256SUMS.full" \
     && raw_get SHA256SUMS.parts "$RAWDIR/SHA256SUMS.parts"; then
    while read -r sum name; do
      [ -n "${name:-}" ] || continue
      name="${name#\*}"
      case "$name" in
        */*|.*|*[!A-Za-z0-9._-]*) LOG "unexpected part name in SHA256SUMS.parts: $name"; n=-1; break ;;
      esac
      raw_get "parts/$name" "$RAWDIR/parts/$name" || { n=-1; break; }
      n=$((n + 1))
    done < "$RAWDIR/SHA256SUMS.parts"
    if [ "$n" -gt 0 ] && (cd "$RAWDIR/parts" && sha256sum -c --strict --quiet ../SHA256SUMS.parts); then
      LOG "downloaded $n part(s) in $(( $(date +%s) - t ))s ($(du -sh "$RAWDIR" | cut -f1)), each matching SHA256SUMS.parts"
      return 0
    fi
    [ "$n" != 0 ] || LOG "SHA256SUMS.parts lists no parts"
    [ "$n" -le 0 ] || LOG "the downloaded parts do not match SHA256SUMS.parts"
  fi
  rm -rf "$RAWDIR"
  RAWDIR=""
  return 1
}

if [ -n "$SRC" ]; then
  cp "$SRC/SHA256SUMS.full" "$WORK/out/SHA256SUMS.full"
  list_parts() { (cd "$SRC/parts" && ls -1 -- "$1".part-* 2>/dev/null | sort); }
  cat_part() { cat "$SRC/parts/$1"; }
  COMMIT=""
else
  URL="${MATHVERIFY_ARTIFACT_URL:-}"
  REMOTE="$URL"
  if [ -z "$URL" ]; then
    URL="$(rgit remote get-url origin)" || die "no MATHVERIFY_ARTIFACT_URL and no origin remote in $ROOT"
    REMOTE=origin
  fi
  G="$WORK/git"
  git init -q --bare "$G"
  # Keep the received pack as it is: below fetch.unpackLimit (default 100 objects; the ref has
  # fewer) git would inflate every part into a loose object and compress it again.
  FETCH=(-c fetch.unpackLimit=1 -c transfer.unpackLimit=1 -c gc.auto=0 -c maintenance.auto=false fetch -q --no-tags)
  t=$(date +%s)
  COMMIT=""
  if rgit rev-parse --git-dir >/dev/null 2>&1; then copy_git_config "$G"; fi
  [ "$VIA" = auto ] && LOG "git fetch --depth 1 $REF into a fresh repository"
  if [ "$VIA" = auto ] \
      && GIT_TERMINAL_PROMPT=0 git --git-dir="$G" "${FETCH[@]}" --depth 1 "$URL" "$REF"; then
    COMMIT="$(git --git-dir="$G" rev-parse FETCH_HEAD)"
  elif [ "$VIA" = auto ] && token_applies \
      && LOG "retrying the fetch with MATHVERIFY_GITHUB_TOKEN (value not printed)" \
      && GIT_TERMINAL_PROMPT=0 with_token git --git-dir="$G" "${FETCH[@]}" --depth 1 "$URL" "$REF"; then
    COMMIT="$(git --git-dir="$G" rev-parse FETCH_HEAD)"
    LOG "the token fetch succeeded"
  elif { [ "$VIA" = auto ] || token_applies; } && raw_applies \
      && LOG "downloading $REF file by file from $RAW_URL with MATHVERIFY_GITHUB_TOKEN (value not printed)" \
      && raw_fetch; then
    LOG "the raw download succeeded"
  elif [ "$VIA" = raw ]; then
    die "the raw download of $REF was not possible or failed (see above)"
  else
    LOG "fresh-repository fetch failed; fetching $REF from $REMOTE inside $ROOT"
    rgit rev-parse --git-dir >/dev/null 2>&1 || die "git fetch of $REF failed and $ROOT is not a git checkout"
    COMMIT="$(rgit ls-remote "$REMOTE" "$REF" | awk -v r="$REF" '$2 == r {print $1}')" \
      || die "git ls-remote $REMOTE $REF failed"
    [ -n "$COMMIT" ] || die "$REF not found on $REMOTE (is the ref pushed and readable with these credentials?)"
    # Objects go to $G; the checkout's own store is only read (alternate, for negotiation).
    # --refmap= and --no-write-fetch-head: no ref or FETCH_HEAD of the checkout is touched.
    GOBJ="$(git --git-dir="$G" rev-parse --path-format=absolute --git-path objects)"
    rgit rev-parse --path-format=absolute --git-path objects > "$GOBJ/info/alternates"
    GIT_OBJECT_DIRECTORY="$GOBJ" rgit "${FETCH[@]}" --refmap= --no-write-fetch-head "$REMOTE" "$REF" \
      || die "git fetch of $REF failed both ways (is the ref pushed and readable with these credentials?)"
    git --git-dir="$G" cat-file -e "$COMMIT^{commit}" || die "fetched objects lack commit $COMMIT"
  fi
  if [ -n "$RAWDIR" ]; then
    cp "$RAWDIR/SHA256SUMS.full" "$WORK/out/SHA256SUMS.full"
    list_parts() { (cd "$RAWDIR/parts" && ls -1 -- "$1".part-* 2>/dev/null | sort); }
    cat_part() { cat "$RAWDIR/parts/$1"; }
  else
    LOG "fetched commit $COMMIT in $(( $(date +%s) - t ))s ($(du -sh "$G" | cut -f1) of git objects)"
    git --git-dir="$G" show "$COMMIT:SHA256SUMS.full" > "$WORK/out/SHA256SUMS.full"
    list_parts() { git --git-dir="$G" ls-tree --name-only "$COMMIT" parts/ | sed 's|^parts/||' | grep -F -- "$1.part-" | sort; }
    cat_part() { git --git-dir="$G" cat-file blob "$COMMIT:parts/$1"; }
  fi
fi

t=$(date +%s)
NAMES=()
while read -r _sum name; do
  [ -n "${name:-}" ] || continue
  NAMES+=("${name#\*}")
done < "$WORK/out/SHA256SUMS.full"
[ "${#NAMES[@]}" -gt 0 ] || die "SHA256SUMS.full lists no files"
for name in "${NAMES[@]}"; do
  case "$name" in */*|.*) die "unexpected file name in SHA256SUMS.full: $name" ;; esac
  parts="$(list_parts "$name" || true)"
  [ -n "$parts" ] || die "no parts for $name"
  n=0
  : > "$WORK/out/$name"
  while read -r p; do
    # Only exact "<name>.part-<digits>" members belong to this file.
    case "${p#"$name".part-}" in ''|*[!0-9]*) continue ;; esac
    cat_part "$p" >> "$WORK/out/$name"
    n=$((n + 1))
  done <<< "$parts"
  [ "$n" -gt 0 ] || die "no parts named $name.part-NNN"
  LOG "reassembled $name from $n part(s), $(wc -c < "$WORK/out/$name") bytes"
done
LOG "reassembly took $(( $(date +%s) - t ))s"
[ -z "${G:-}" ] || rm -rf "$G"
[ -z "$RAWDIR" ] || rm -rf "$RAWDIR"

t=$(date +%s)
(cd "$WORK/out" && sha256sum -c --strict SHA256SUMS.full) \
  || die "SHA256 verification failed; DEST left unchanged"
LOG "sha256 verification took $(( $(date +%s) - t ))s"

# Publish: data files first, then the checksum list and the source marker (written last, so an
# interrupted run never looks complete).
rm -f "$DEST/.source"
for name in "${NAMES[@]}"; do
  mv -f "$WORK/out/$name" "$DEST/$name"
done
mv -f "$WORK/out/SHA256SUMS.full" "$DEST/SHA256SUMS.full"
{ echo "$SOURCE_ID"; [ -z "$COMMIT" ] || echo "commit $COMMIT"; } > "$DEST/.source"
LOG "done: ${#NAMES[@]} file(s), $(du -sh "$DEST" | cut -f1) in $DEST (total $(( $(date +%s) - T0 ))s)"
