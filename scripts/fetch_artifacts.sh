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
#     2. by `git fetch` run inside this checkout (its remotes, full config and credentials), with
#        the received objects written to the temporary object store instead of the checkout's,
#        which serves only as an alternate: no ref, FETCH_HEAD or object is added to the checkout.
# MATHVERIFY_GITHUB_TOKEN: a GitHub token that can read this repository (fine-grained, Contents:
#   read-only), for the claude.ai setup script. It runs before Claude Code connects to the
#   session's GitHub proxy, so the private repository answered 401 there (measured 24 Sep 2026)
#   while the same fetch works inside the session. The token is sent only after the plain fetch
#   failed (inside a session the proxy authenticates and the token is never sent), only to URLs
#   under ${MATHVERIFY_GITHUB_TOKEN_URL:-https://github.com/}, as HTTP basic auth (user: the
#   repository owner) in an extra header passed through GIT_CONFIG_* in the environment of that
#   one git command: never on a command line, in a log or on disk.
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
  if [ -z "${MATHVERIFY_GITHUB_TOKEN:-}" ]; then
    LOG "MATHVERIFY_GITHUB_TOKEN is not set: no token retry"
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
  # whitespace a paste may leave around the value would only turn the token into a 401
  token="${MATHVERIFY_GITHUB_TOKEN//[[:space:]]/}"
  auth="$(printf '%s:%s' "$owner" "$token" | base64 | tr -d '\n')"
  n="${GIT_CONFIG_COUNT:-0}"
  export "GIT_CONFIG_KEY_$n=http.$TOKEN_URL.extraHeader"
  export "GIT_CONFIG_VALUE_$n=Authorization: Basic $auth"
  export GIT_CONFIG_COUNT=$((n + 1))
  "$@"
)

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
  LOG "git fetch --depth 1 $REF into a fresh repository"
  if GIT_TERMINAL_PROMPT=0 git --git-dir="$G" "${FETCH[@]}" --depth 1 "$URL" "$REF"; then
    COMMIT="$(git --git-dir="$G" rev-parse FETCH_HEAD)"
  elif token_applies && LOG "retrying the fetch with MATHVERIFY_GITHUB_TOKEN (value not printed)" \
      && GIT_TERMINAL_PROMPT=0 with_token git --git-dir="$G" "${FETCH[@]}" --depth 1 "$URL" "$REF"; then
    COMMIT="$(git --git-dir="$G" rev-parse FETCH_HEAD)"
    LOG "the token fetch succeeded"
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
  LOG "fetched commit $COMMIT in $(( $(date +%s) - t ))s ($(du -sh "$G" | cut -f1) of git objects)"
  git --git-dir="$G" show "$COMMIT:SHA256SUMS.full" > "$WORK/out/SHA256SUMS.full"
  list_parts() { git --git-dir="$G" ls-tree --name-only "$COMMIT" parts/ | sed 's|^parts/||' | grep -F -- "$1.part-" | sort; }
  cat_part() { git --git-dir="$G" cat-file blob "$COMMIT:parts/$1"; }
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
