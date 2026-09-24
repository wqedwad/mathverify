#!/usr/bin/env bash
# Fetch the offline tool artifacts used by cloud sessions (Lean toolchain, elan, the Mathlib .ltar
# cache and a standalone CPython), reassemble the split parts and verify every file against
# SHA256SUMS.full. The cloud GitHub proxy blocks release assets of repositories that are not
# attached to the session, so these files live in this repository under a non-branch git ref.
#
# Usage: scripts/fetch_artifacts.sh [DEST]
#   DEST   defaults to ${MATHVERIFY_ARTIFACT_DIR:-$HOME/.cache/mathverify/arac}
# Source (first match wins):
#   MATHVERIFY_ARTIFACT_SRC   local directory holding parts/ and SHA256SUMS.full (offline use)
#   otherwise a shallow fetch of ${MATHVERIFY_ARTIFACT_REF:-refs/arac/bulut-v1} from
#   ${MATHVERIFY_ARTIFACT_URL:-<origin remote of this repository>}
# Idempotent: when DEST already verifies against its SHA256SUMS.full and was produced from the
# same source (same ref name, or a byte-identical SHA256SUMS.full for a local source), nothing is
# fetched. A ref is never rewritten in place; new content gets a new ref name (bulut-v2, ...).
set -euo pipefail
export LC_ALL=C

T0=$(date +%s)
LOG() { echo "[$(date +%H:%M:%S) +$(( $(date +%s) - T0 ))s] fetch_artifacts: $*"; }
die() { LOG "ERROR: $*" >&2; exit 1; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-${MATHVERIFY_ARTIFACT_DIR:-$HOME/.cache/mathverify/arac}}"
REF="${MATHVERIFY_ARTIFACT_REF:-refs/arac/bulut-v1}"
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

# Work inside DEST so the final moves stay on one filesystem.
WORK="$(mktemp -d "$DEST/.fetch.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/out"

if [ -n "$SRC" ]; then
  cp "$SRC/SHA256SUMS.full" "$WORK/out/SHA256SUMS.full"
  list_parts() { (cd "$SRC/parts" && ls -1 -- "$1".part-* 2>/dev/null | sort); }
  cat_part() { cat "$SRC/parts/$1"; }
  COMMIT=""
else
  URL="${MATHVERIFY_ARTIFACT_URL:-}"
  if [ -z "$URL" ]; then
    # safe.directory (this one command only): the setup script may run as root on a checkout
    # owned by another user, where git refuses to read the repository otherwise.
    URL="$(git -c safe.directory='*' -C "$ROOT" remote get-url origin)" \
      || die "no MATHVERIFY_ARTIFACT_URL and no origin remote in $ROOT"
  fi
  G="$WORK/git"
  git init -q "$G"
  t=$(date +%s)
  LOG "git fetch --depth 1 $REF"
  git -C "$G" fetch -q --depth 1 --no-tags "$URL" "$REF" \
    || die "git fetch of $REF failed (is the ref pushed and readable with these credentials?)"
  COMMIT="$(git -C "$G" rev-parse FETCH_HEAD)"
  LOG "fetched commit $COMMIT in $(( $(date +%s) - t ))s ($(du -sh "$G" | cut -f1) of git objects)"
  git -C "$G" show "$COMMIT:SHA256SUMS.full" > "$WORK/out/SHA256SUMS.full"
  list_parts() { git -C "$G" ls-tree --name-only "$COMMIT" parts/ | sed 's|^parts/||' | grep -F -- "$1.part-" | sort; }
  cat_part() { git -C "$G" cat-file blob "$COMMIT:parts/$1"; }
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
