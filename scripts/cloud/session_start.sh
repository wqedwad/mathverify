#!/usr/bin/env bash
# SessionStart hook (.claude/settings.json, matcher startup|resume). Outside a Claude Code cloud
# session (CLAUDE_CODE_REMOTE != true) it exits at once without output, on Windows too.
#
# In a cloud session it (1) picks a Python >= 3.12 (pyproject.toml): the CPython 3.14.6 that
# scripts/cloud/setup_env.sh installs as ${MATHVERIFY_OPT:-/opt}/python3.14, else python3.14 on
# PATH (or found by uv), python3.13, python3.12, and python3 only when it is >= 3.12; a fallback
# is named in the status block; (2) creates or
# refreshes ./.venv from requirements.lock plus `--no-deps -e .`, skipped while the stamp
# (sha256 of requirements.lock + pyproject.toml, interpreter path and version) is unchanged, so a
# .venv built by a fallback is rebuilt by the first run that finds the pinned 3.14.6;
# (3) copies missing reports/*.json from reports/arsiv/2026-09-24/ (never overwrites);
# (4) exports the Lean install through $CLAUDE_ENV_FILE and links it under $HOME, or starts
# `setup_env.sh --lean-only` in the background when it is missing; (5) prints a short Turkish
# status block, which Claude Code adds to the session context. It always exits 0.
# Lean counts as installed only when mathverify-logs/lean.done exists: setup_env.sh writes it
# after the REPL smoke test passed. A REPL binary without it is what a failed run leaves (the REPL
# is built before its smoke test), so that case is retried in the background, never reported ready.
# An install made from other lean/ pins stays in use and is updated in the background when this
# user can write its prefix; otherwise (a root-made /opt, a non-root session) the hook prints the
# per-user command instead and never starts a second full install itself (~12 GB; the cloud disk
# is 30 GB).
# A FAILED setup_env.status in any prefix is always printed.
# MATHVERIFY_SKIP_LEAN=1 reports an existing Lean install but never starts one.
# MATHVERIFY_HOOK_PREFIXES (colon-separated) replaces the install prefix list below; the tests
# use it so that a real /opt install cannot leak into them.
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

trap 'exit 0' EXIT
T0=$(date +%s)
HOME="${HOME:-/root}"

REPO="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$REPO" ] || [ ! -f "$REPO/pyproject.toml" ]; then
  REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
fi
cd "$REPO" 2>/dev/null || { echo "mathverify: depo bulunamadı ($REPO); kurulum atlandı."; exit 0; }

# Install prefixes, in order: MATHVERIFY_OPT, the setup script's /opt, and the per-user prefix
# used when /opt is not writable for this session's user.
if [ -n "${MATHVERIFY_HOOK_PREFIXES:-}" ]; then
  IFS=: read -r -a CANDIDATES <<<"$MATHVERIFY_HOOK_PREFIXES"
else
  CANDIDATES=("${MATHVERIFY_OPT:-}" /opt "$HOME/.mathverify-opt")
fi
PREFIXES=()
for p in "${CANDIDATES[@]}"; do
  [ -n "$p" ] || continue
  case " ${PREFIXES[*]} " in *" $p "*) ;; *) PREFIXES+=("$p") ;; esac
done

writable_logdir() {  # print $1/mathverify-logs when it can be created and written
  mkdir -p "$1/mathverify-logs" 2>/dev/null && [ -w "$1/mathverify-logs" ] \
    && printf '%s\n' "$1/mathverify-logs"
}
LOGDIR=""
for p in "${PREFIXES[@]}"; do
  LOGDIR="$(writable_logdir "$p")" && break
done
[ -n "$LOGDIR" ] || { LOGDIR="${TMPDIR:-/tmp}/mathverify-logs"; mkdir -p "$LOGDIR" 2>/dev/null; }
SLOG="$LOGDIR/session_start.log"
log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$SLOG" 2>/dev/null; }
log "==== session_start user=$(id -un 2>/dev/null || id -u) HOME=$HOME repo=$REPO"

# ---- Python -----------------------------------------------------------------------------------
# mathverify needs Python >= 3.12. Measured in the cloud (2026-09-24): python3 is 3.11.15 there
# (/usr/local/bin/python3) while /usr/bin/python3.13 and /usr/bin/python3.12 exist, and before
# setup_env.sh has run there is no python3.14 at all; the hook used python3 and the .venv install
# failed. Order: the pinned 3.14.6 under a prefix, python3.14 on PATH, a python3.14 uv knows,
# python3.13, python3.12, python3 when it is >= 3.12. Nothing older ever builds the .venv.
export UV_PYTHON_DOWNLOADS=never       # releases.astral.sh is not reachable from the cloud
VENV="$REPO/.venv"
py_version() { "$1" -c 'import platform; print(platform.python_version())' 2>/dev/null; }
# py_usable EXE: print EXE's version when it runs, is >= 3.12 and is not inside ./.venv (which
# build_venv deletes first; a PATH with the .venv activated names its interpreters).
py_usable() {
  local v maj min
  [ -n "$1" ] && [ -x "$1" ] || return 1
  case "$1" in "$VENV"/*) return 1 ;; esac
  v="$(py_version "$1")"
  IFS=. read -r maj min _ <<<"$v"
  case "$maj.$min" in .*|*.|*[!0-9.]*) return 1 ;; esac
  { [ "$maj" -gt 3 ] || { [ "$maj" -eq 3 ] && [ "$min" -ge 12 ]; }; } || return 1
  printf '%s\n' "$v"
}
PY=""; PYVER=""; PYNOTE=""; PYPREFIX=""; PYHOW=""; PYREJECTED=""
for p in "${PREFIXES[@]}"; do
  if PYVER="$(py_usable "$p/python3.14/bin/python3.14")"; then
    PY="$p/python3.14/bin/python3.14"; PYPREFIX="$p"; break
  fi
done
UV="$(command -v uv 2>/dev/null)"
if [ -z "$UV" ]; then
  for c in "${PREFIXES[@]/%//uv-tool/bin/uv}" "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /root/.local/bin/uv; do
    [ -x "$c" ] && { UV="$c"; break; }
  done
fi
if [ -z "$PY" ]; then
  for how in python3.14 "uv python find 3.14" python3.13 python3.12 python3; do
    case "$how" in
      uv*)
        [ -n "$UV" ] || continue
        # From / and without VIRTUAL_ENV: uv would otherwise report the repository's own .venv.
        exe="$(cd / && env -u VIRTUAL_ENV "$UV" python find 3.14 2>/dev/null)" ;;
      *) exe="$(command -v "$how" 2>/dev/null)" ;;
    esac
    [ -n "$exe" ] || continue
    if PYVER="$(py_usable "$exe")"; then PY="$exe"; PYHOW="$how"; break; fi
    PYREJECTED="${PYREJECTED:+$PYREJECTED, }$how = $exe ($(py_version "$exe" || echo 'çalışmadı'))"
  done
  if [ -n "$PY" ]; then
    PYNOTE="YEDEK ($PYHOW): kurulum betiğinin CPython 3.14.6'sı (${PREFIXES[0]:-/opt}/python3.14) yok ya da çalışmıyor; bu yorumlayıcı Windows'takiyle (3.14.7) aynı değil. Tam takım yedek yorumlayıcılardan yalnız 3.12.11'de ölçüldü ve Windows ile aynı sonucu verdi (DECISIONS §42)"
  else
    PYNOTE="HATA: Python >= 3.12 bulunamadı (sırayla: ${PREFIXES[0]:-/opt}/python3.14, python3.14, uv python find 3.14, python3.13, python3.12, python3)"
    [ -z "$PYREJECTED" ] || PYNOTE="$PYNOTE; 3.12'den eski ya da çalışmayan: $PYREJECTED"
  fi
fi
log "python: ${PY:-none} (${PYVER:-?}) via ${PYHOW:-${PYPREFIX:+prefix $PYPREFIX}} uv: ${UV:-none}${PYREJECTED:+ rejected: $PYREJECTED}"

# ---- .venv ----------------------------------------------------------------------------------
STAMPF="$VENV/.mathverify-stamp"
VLOG="$LOGDIR/venv.log"
if [ -z "${UV_CACHE_DIR:-}" ]; then
  for p in "$PYPREFIX" "${PREFIXES[@]}"; do
    if [ -n "$p" ] && [ -d "$p/uv-cache" ] && [ -w "$p/uv-cache" ]; then
      export UV_CACHE_DIR="$p/uv-cache"; break
    fi
  done
fi
stamp() {
  { sha256sum "$REPO/requirements.lock" "$REPO/pyproject.toml" | awk '{print $1}'
    echo "$PY"; "$PY" -c 'import sys; print(sys.version)'; } 2>/dev/null | sha256sum | awk '{print $1}'
}
uv_install() {  # uv pip install ARGS..., offline first (prewarmed cache), then online
  "$UV" pip install --python "$VENV/bin/python" --offline "$@" \
    || "$UV" pip install --python "$VENV/bin/python" "$@"
}
build_venv() {
  case "$VENV" in */.venv) ;; *) return 1 ;; esac
  rm -rf "$VENV"
  export UV_COMPILE_BYTECODE=1
  if [ -n "$UV" ]; then
    "$UV" venv -q --python "$PY" "$VENV" \
      && uv_install -r "$REPO/requirements.lock" \
      && uv_install --no-deps -e "$REPO" || return 1
  else
    "$PY" -m venv "$VENV" \
      && "$VENV/bin/python" -m pip install -q -r "$REPO/requirements.lock" \
      && "$VENV/bin/python" -m pip install -q --no-deps -e "$REPO" || return 1
  fi
  "$VENV/bin/python" -c 'import mathverify, sympy, z3, math_verify, anthropic, pytest' || return 1
}
VSTATE=""
if [ -z "$PY" ] || [ -z "$PYVER" ]; then
  VSTATE="HATA: Python >= 3.12 yok; .venv kurulmadı (var olan .venv'e dokunulmadı)"
else
  ST="$(stamp)"
  if [ -x "$VENV/bin/python" ] && [ "$(cat "$STAMPF" 2>/dev/null)" = "$ST" ]; then
    VSTATE="HAZIR (değişiklik yok)"
  else
    t=$(date +%s)
    { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] building $VENV with $PY (uv: ${UV:-none}, UV_CACHE_DIR=${UV_CACHE_DIR:-default})"
      build_venv; } >"$VLOG" 2>&1
    if [ $? -eq 0 ]; then
      echo "$ST" >"$STAMPF"
      VSTATE="KURULDU ($(( $(date +%s) - t )) s)"
    else
      VSTATE="HATA ($(( $(date +%s) - t )) s; günlük: $VLOG)"
    fi
  fi
fi
log "venv: $VSTATE"

# ---- reports: the committed snapshot fills in the git-ignored reports/*.json -----------------
NREP=0
for f in "$REPO"/reports/arsiv/2026-09-24/*.json; do
  [ -f "$f" ] || continue
  t="$REPO/reports/$(basename "$f")"
  if [ ! -e "$t" ] && cp -p "$f" "$t" 2>/dev/null; then NREP=$((NREP + 1)); fi
done

# ---- Lean -------------------------------------------------------------------------------------
setup_running() {  # $1 = prefix; true while a setup_env.sh run holds its lock
  local lock="$1/mathverify-logs/setup_env.lock" pidf="$1/mathverify-logs/setup_env.pid" rc
  if [ -f "$lock" ] && command -v flock >/dev/null 2>&1; then
    flock -n -E 75 "$lock" true 2>/dev/null; rc=$?
    [ "$rc" -eq 75 ] && return 0
    [ "$rc" -eq 0 ] && return 1
  fi
  [ -f "$pidf" ] && kill -0 "$(cat "$pidf" 2>/dev/null)" 2>/dev/null
}
# Must match lean_fingerprint in setup_env.sh: the pinned lean/ files an install was made from.
lean_fingerprint() {
  (cd "$REPO" && find lean -type f ! -name README.md | LC_ALL=C sort | xargs sha256sum 2>/dev/null) \
    | sha256sum | awk '{print $1}'
}
start_install() {  # $1 = prefix; detached from this hook (own session, no inherited stdio)
  local detach=(nohup)
  [ -f "$REPO/scripts/cloud/setup_env.sh" ] || return 1
  command -v setsid >/dev/null 2>&1 && detach=(setsid nohup)
  MATHVERIFY_OPT="$1" "${detach[@]}" bash "$REPO/scripts/cloud/setup_env.sh" --lean-only \
    </dev/null >>"$1/mathverify-logs/setup_env.nohup.log" 2>&1 &
  log "started setup_env.sh --lean-only in the background (pid $!, prefix $1)"
}
can_install() { writable_logdir "$1" >/dev/null && [ -w "$1" ]; }
installed() {  # $1 = prefix; a finished install: REPL, project and lean.done (smoke test passed)
  [ -x "$1/repl/.lake/build/bin/repl" ] && [ -d "$1/mathverify-lean" ] \
    && [ -f "$1/mathverify-logs/lean.done" ]
}
# A second, per-user install needs this much disk (measured peak of setup_env.sh --lean-only
# into a fresh prefix, artifacts included); the cloud disk is 30 GB, so it is never started
# automatically next to an existing install.
USER_INSTALL_GB=12
free_gb() { df -Pk "$1" 2>/dev/null | awk 'NR == 2 {printf "%.1f", $4 / 1048576}'; }
LP=""; LSTATE=""; ULP=""; STALE_WHY=""
FP="$(lean_fingerprint)"
# An install made from the current lean/ pins wins, whichever prefix holds it.
for p in "${PREFIXES[@]}"; do
  if installed "$p" && [ "$(cat "$p/mathverify-logs/lean.done" 2>/dev/null)" = "$FP" ]; then
    LP="$p"; LSTATE=ready; break
  fi
done
if [ -z "$LP" ]; then
  for p in "${PREFIXES[@]}"; do
    installed "$p" || continue
    # The snapshot predates a change of lean/ (pins): keep using it, update it in the background.
    LP="$p"; ULP="$p"
    if setup_running "$LP"; then LSTATE=updating
    elif [ "${MATHVERIFY_SKIP_LEAN:-}" = 1 ]; then LSTATE=stale; STALE_WHY=skip
    elif can_install "$LP"; then
      if start_install "$LP"; then LSTATE=updating; else LSTATE=stale; STALE_WHY=nostart; fi
    else
      # Not writable for this user (a root-made /opt, say): only a separate install can bring the
      # current pins. One the user already started in another prefix counts as the update.
      LSTATE=stale; STALE_WHY=readonly
      for q in "${PREFIXES[@]}"; do
        if [ "$q" != "$LP" ] && setup_running "$q"; then LSTATE=updating; ULP="$q"; break; fi
      done
    fi
    break
  done
fi
# No finished install. A REPL binary without lean.done (a failed or interrupted run) falls through
# to here: it is reported as installing while a setup_env.sh run holds the lock, else retried.
if [ -z "$LP" ]; then
  for p in "${PREFIXES[@]}"; do
    if setup_running "$p"; then LP="$p"; LSTATE=installing; break; fi
  done
fi
if [ -z "$LP" ] && [ "${MATHVERIFY_SKIP_LEAN:-}" = 1 ]; then
  LSTATE=skipped
elif [ -z "$LP" ]; then
  # Install where this user can write: MATHVERIFY_OPT or /opt, else the per-user prefix.
  for p in "${PREFIXES[@]}"; do
    if can_install "$p"; then LP="$p"; break; fi
  done
  if [ -n "$LP" ] && start_install "$LP"; then
    LSTATE=started
  else
    LP=""; LSTATE=missing
  fi
fi
log "lean: ${LSTATE} ${LP}"

if [ -n "$LP" ]; then
  # Later Bash commands of this session see these (the values are fixed, so they are exported
  # while the install is still running too; lean_client treats a missing REPL as unavailable).
  # The last block wins when the file is sourced: a resumed session whose install moved to another
  # prefix (a per-user install of the current pins, say) gets a new block.
  if [ -n "${CLAUDE_ENV_FILE:-}" ] \
     && [ "$(grep -s '^export MATHVERIFY_LEAN_REPL=' "$CLAUDE_ENV_FILE" | tail -n 1)" \
          != "export MATHVERIFY_LEAN_REPL=\"$LP/repl/.lake/build/bin/repl\"" ]; then
    {
      echo "export MATHVERIFY_OPT=\"$LP\""
      echo "export ELAN_HOME=\"$LP/elan\""
      echo "export MATHVERIFY_LEAN_PROJECT=\"$LP/mathverify-lean\""
      echo "export MATHVERIFY_LEAN_REPL=\"$LP/repl/.lake/build/bin/repl\""
      echo "export PATH=\"$LP/elan/bin:\$PATH\""
    } >>"$CLAUDE_ENV_FILE" 2>/dev/null
  fi
  # The default locations (~/.elan, ~/mathverify-lean, ~/repl) for tools that ignore the env. A
  # link to the same part of another prefix (made earlier by this hook) follows an install from
  # the current pins, or any install once its target is gone; anything else is left alone.
  if [ "$LSTATE" = ready ] || [ "$LSTATE" = updating ] || [ "$LSTATE" = stale ]; then
    for pair in .elan:elan mathverify-lean:mathverify-lean repl:repl; do
      l="$HOME/${pair%%:*}"
      want="$LP/${pair#*:}"
      if [ -L "$l" ]; then
        cur="$(readlink "$l")"
        { [ "$cur" != "$want" ] && { [ "$LSTATE" = ready ] || [ ! -e "$cur" ]; }; } || continue
        for p in "${PREFIXES[@]}"; do
          if [ "$cur" = "$p/${pair#*:}" ]; then ln -sfn "$want" "$l" 2>/dev/null; break; fi
        done
      elif [ ! -e "$l" ]; then
        ln -s "$want" "$l" 2>/dev/null
      fi
    done
  fi
fi

# ---- status block (stdout goes into Claude's context) -----------------------------------------
case "$LSTATE" in
  ready) LTXT="HAZIR ($LP/repl/.lake/build/bin/repl)" ;;
  installing) LTXT="KURULUYOR (başka bir setup_env.sh çalışıyor; günlük: $LP/mathverify-logs/setup_env.log)" ;;
  started) LTXT="KURULUYOR (arka planda başlatıldı; günlük: $LP/mathverify-logs/setup_env.log). Bitene dek Lean testleri atlanır." ;;
  updating)
    if [ "$ULP" = "$LP" ]; then
      LTXT="HAZIR ama lean/ sabitleri kurulumdan farklı; arka planda güncelleniyor (günlük: $ULP/mathverify-logs/setup_env.log). Güncelleme bitene dek Lean sonuçları eski sabitlerle."
    else
      LTXT="HAZIR ama lean/ sabitleri kurulumdan farklı; güncel sabitlerle yeni kurulum $ULP içinde sürüyor (günlük: $ULP/mathverify-logs/setup_env.log). Bitene dek Lean sonuçları eski sabitlerle ($LP)."
    fi ;;
  stale)
    case "$STALE_WHY" in
      skip) LTXT="ESKİ: lean/ sabitleri kurulumdan farklı; MATHVERIFY_SKIP_LEAN=1 olduğu için güncelleme başlatılmadı ($LP). Lean sonuçları eski sabitlerle." ;;
      readonly) LTXT="ESKİ: lean/ sabitleri kurulumdan farklı ve $LP bu kullanıcıya ($(id -un 2>/dev/null || id -u)) yazılabilir değil; Lean sonuçları eski sabitlerle. Disk sınırlı olduğu için ikinci bir tam kurulum kendiliğinden başlatılmadı." ;;
      *) LTXT="ESKİ: lean/ sabitleri kurulumdan farklı ve güncelleme başlatılamadı ($LP; scripts/cloud/setup_env.sh bulunamadı)" ;;
    esac ;;
  skipped) LTXT="YOK (MATHVERIFY_SKIP_LEAN=1: arka plan kurulumu başlatılmadı)" ;;
  *) LTXT="YOK (kurulum başlatılamadı: yazılabilir önek yok)" ;;
esac
echo "[mathverify bulut oturumu — session_start.sh, $(( $(date +%s) - T0 )) s]"
if [ -n "$PY" ]; then
  echo "- Python: $PYVER ($PY)${PYNOTE:+ — $PYNOTE}"
else
  echo "- Python: yok — $PYNOTE"
fi
echo "- .venv: $VSTATE; komutlar .venv/bin/python ile (PYTHONUTF8=1) çalışır, Windows'taki .venv/Scripts/python.exe yerine"
echo "- Lean: $LTXT"
if [ "$LSTATE" = stale ]; then
  # The command that brings the current pins. Where this user cannot write, only a per-user
  # prefix works (setup_env.sh --lean-only alone would try the read-only one and fail).
  if [ "$STALE_WHY" = readonly ]; then
    FREE="$(free_gb "$HOME")"
    LOW="$(awk -v f="${FREE:-0}" -v n="$USER_INSTALL_GB" 'BEGIN {if (f < n) print " — YETERSİZ"}')"
    echo "  Güncel sabitlerle kullanıcı kurulumu (yaklaşık $USER_INSTALL_GB GB disk ister; \$HOME altında boş: ${FREE:-?} GB$LOW): MATHVERIFY_OPT=\"\$HOME/.mathverify-opt\" bash scripts/cloud/setup_env.sh --lean-only"
  else
    echo "  Elle güncelleme: MATHVERIFY_OPT=\"$LP\" bash scripts/cloud/setup_env.sh --lean-only"
  fi
fi
if [ "$LSTATE" = started ] || [ "$LSTATE" = installing ]; then
  # Nothing runs this hook again when the background install finishes: a .venv built by a
  # fallback interpreter (or not built) and the ~/.elan, ~/mathverify-lean, ~/repl links wait for
  # a re-run in this session, which rebuilds the .venv with the pinned 3.14.6 (the stamp holds the
  # interpreter path). The exported variables are already in $CLAUDE_ENV_FILE.
  if [ -z "$PY" ]; then WHAT=".venv'i CPython 3.14.6 ile kurmak ve ~/.elan, ~/mathverify-lean, ~/repl bağlantıları"
  elif [ -z "$PYPREFIX" ]; then WHAT=".venv'i CPython 3.14.6 ile yeniden kurmak ve ~/.elan, ~/mathverify-lean, ~/repl bağlantıları"
  else WHAT="~/.elan, ~/mathverify-lean, ~/repl bağlantıları"
  fi
  echo "  Kurulum bitince ($LP/mathverify-logs/setup_env.status \"OK\" ile başlar) kanca bu oturumda kendiliğinden yeniden çalışmaz; $WHAT için: CLAUDE_CODE_REMOTE=true${CLAUDE_ENV_FILE:+ CLAUDE_ENV_FILE=\"$CLAUDE_ENV_FILE\"} bash \"$REPO/scripts/cloud/session_start.sh\""
fi
# Every prefix, whatever the Lean state: the line names the failed stages (Python ones included),
# and a retry started above rewrites the file only when it finishes.
for p in "${PREFIXES[@]}"; do
  if grep -qs '^FAILED' "$p/mathverify-logs/setup_env.status"; then
    echo "  Önceki kurulum BAŞARISIZ ($p/mathverify-logs/setup_env.status): $(head -c 400 "$p/mathverify-logs/setup_env.status")"
  fi
done
[ "$NREP" -eq 0 ] || echo "- Raporlar: reports/arsiv/2026-09-24/ içinden $NREP eksik JSON kopyalandı"
echo "- Günlükler: $SLOG, $VLOG, $LOGDIR/setup_env.log"
echo "- Önce HANDOFF.md, sonra docs/BULUT.md okunur."
log "done in $(( $(date +%s) - T0 ))s"
exit 0
