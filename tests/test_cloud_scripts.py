"""Cloud session scripts: static contracts and hook/installer behaviour (offline, fast).

Static checks run everywhere: the SessionStart hook entry in .claude/settings.json, requirements.lock
against pyproject.toml and this interpreter, the lean/ pins, and `bash -n` on every script.

Behaviour checks run the real scripts, never against the real install:
- Windows: only through Git Bash (C:\\Program Files\\Git\\bin\\bash.exe). `bash` from a Windows PATH
  can be the WSL launcher, which is exactly the failure .claude/settings.json's "shell": "bash" avoids.
- POSIX: the hook's Lean state machine on stub install prefixes (MATHVERIFY_HOOK_PREFIXES keeps a
  real /opt install out), its choice of interpreter on a PATH whose only pythons are stubs,
  fetch_artifacts.sh on a tiny generated artifact set, and setup_env.sh's uv
  prewarm with a stub uv and interpreter. The same prewarm with the real uv and CPython 3.14.6 is
  opt-in (MATHVERIFY_CLOUD_INTEGRATION=1, network), since it downloads the locked packages.
- POSIX: setup_env.sh, setup_lean.sh and setup_lean_repl.sh themselves, on pins that point at tiny
  local git repositories, an artifact set built from them and a stub elan/Lean/Lake (LeanBed): the
  offline install, a failed fetch over an installed prefix, a staged update and its rollback, and
  the free-disk checks (a stub df, so no test depends on the host's free disk).
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import importlib.metadata as md
import json
import os
import re
import shutil
import signal
import subprocess
import tarfile
import textwrap
import threading
import time
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / ".claude" / "settings.json"
HOOK = ROOT / "scripts" / "cloud" / "session_start.sh"
SETUP_ENV = ROOT / "scripts" / "cloud" / "setup_env.sh"
FETCH = ROOT / "scripts" / "fetch_artifacts.sh"
HOOK_COMMAND = 'bash "$CLAUDE_PROJECT_DIR"/scripts/cloud/session_start.sh'
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def _real_bash() -> str | None:
    if os.name == "nt":
        return str(GIT_BASH) if GIT_BASH.is_file() else None
    return shutil.which("bash")


BASH = _real_bash()
needs_bash = pytest.mark.skipif(
    BASH is None, reason="no real bash (Windows: Git Bash; the WSL bash launcher is never used)")
posix_only = pytest.mark.skipif(os.name == "nt", reason="runs the cloud scripts natively (POSIX)")


# ---- static contracts -----------------------------------------------------------------------

def test_settings_run_the_session_hook_in_bash():
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entries = data["hooks"]["SessionStart"]
    assert len(entries) == 1
    assert entries[0]["matcher"] == "startup|resume"
    # "shell": "bash" pins the interpreter: under a PowerShell default `bash` is the WSL launcher,
    # which cannot see $CLAUDE_PROJECT_DIR (exit 127 after ~4.6 s, measured 2026-09-24).
    assert entries[0]["hooks"] == [{"type": "command", "shell": "bash",
                                    "command": HOOK_COMMAND, "timeout": 600}]
    assert HOOK.is_file()


def _lock() -> dict[str, Requirement]:
    reqs: dict[str, Requirement] = {}
    for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        r = Requirement(line)
        name = canonicalize_name(r.name)
        assert name not in reqs, f"{name} locked twice"
        reqs[name] = r
    return reqs


def _pinned(r: Requirement) -> str:
    specs = list(r.specifier)
    assert len(specs) == 1 and specs[0].operator == "==", f"lock entry not an exact pin: {r}"
    return specs[0].version


def test_requirements_lock_agrees_with_pyproject():
    lock = _lock()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    declared = list(project["dependencies"])
    for extra in project.get("optional-dependencies", {}).values():
        declared += extra
    exact = 0
    for spec in declared:
        req = Requirement(spec)
        name = canonicalize_name(req.name)
        assert name in lock, f"{req.name} is declared in pyproject.toml but not locked"
        locked = _pinned(lock[name])
        assert req.specifier.contains(locked, prereleases=True), f"{req} vs lock {locked}"
        for s in req.specifier:
            if s.operator == "==":
                exact += 1
                assert s.version == locked, f"{req.name}: pyproject {s.version}, lock {locked}"
    assert exact >= 7  # sympy, mpmath, z3-solver, math-verify, latex2sympy2-extended, anthropic, dotenv
    colorama = lock["colorama"]
    assert colorama.marker is not None
    assert colorama.marker.evaluate({"sys_platform": "win32"})
    assert not colorama.marker.evaluate({"sys_platform": "linux"})


def test_this_interpreter_runs_the_locked_versions():
    # The lock is `uv pip freeze` of the reference Windows .venv, and the cloud .venv is installed
    # from it: in either place every applicable pin must be what is actually imported.
    wrong = []
    for name, r in _lock().items():
        if r.marker is not None and not r.marker.evaluate():
            continue
        try:
            have = md.version(name)
        except md.PackageNotFoundError:
            have = None
        if have != _pinned(r):
            wrong.append(f"{name}: locked {_pinned(r)}, installed {have}")
    assert not wrong, wrong


def _pins() -> dict[str, str]:
    pins = {}
    for line in (ROOT / "lean" / "PINS").read_text(encoding="utf-8").splitlines():
        m = re.fullmatch(r'([A-Z_]+)="([^"]*)"', line.strip())
        if m:
            pins[m[1]] = m[2]
    return pins


def test_lean_pins_agree_with_the_project_files():
    pins = _pins()
    assert pins["LEAN_TOOLCHAIN"] == (ROOT / "lean" / "lean-toolchain").read_text(encoding="utf-8").strip()
    manifest = json.loads((ROOT / "lean" / "lake-manifest.json").read_text(encoding="utf-8"))
    (mathlib,) = [p for p in manifest["packages"] if p["name"] == "mathlib"]
    assert mathlib["rev"] == pins["MATHLIB_REV"]
    lakefile = tomllib.loads((ROOT / "lean" / "lakefile.toml").read_text(encoding="utf-8"))
    (require,) = [r for r in lakefile["require"] if r["name"] == "mathlib"]
    assert require["rev"] == mathlib["inputRev"]  # else `lake` rewrites the manifest
    for key in ("MATHLIB_REV", "REPL_REV"):
        assert re.fullmatch(r"[0-9a-f]{40}", pins[key]), key


def _function(script: Path, name: str) -> str:
    m = re.search(rf"^{name}\(\) \{{.*?^\}}", script.read_text(encoding="utf-8"), re.S | re.M)
    assert m, f"{name}() not found in {script.name}"
    return m[0]


def test_both_scripts_fingerprint_lean_the_same_way():
    # session_start.sh compares lean.done (written by setup_env.sh) with its own fingerprint.
    assert _function(HOOK, "lean_fingerprint") == _function(SETUP_ENV, "lean_fingerprint")


def test_the_artifact_ref_is_chosen_only_by_fetch_artifacts():
    for script in (HOOK, SETUP_ENV):
        assert "refs/arac/" not in script.read_text(encoding="utf-8"), script.name


@needs_bash
@pytest.mark.parametrize("script", sorted(p.relative_to(ROOT).as_posix()
                                          for p in (ROOT / "scripts").rglob("*.sh")))
def test_shell_scripts_parse(script):
    r = subprocess.run([BASH, "-n", (ROOT / script).as_posix()], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    assert (r.returncode, r.stderr) == (0, "")


# ---- the hook outside a cloud session: silent no-op ------------------------------------------

@needs_bash
@pytest.mark.parametrize("remote", [None, "false"])
def test_hook_is_a_silent_noop_outside_the_cloud(remote):
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_REMOTE", None)
    if remote is not None:
        env["CLAUDE_CODE_REMOTE"] = remote
    env["CLAUDE_PROJECT_DIR"] = str(ROOT)  # the backslash form Claude Code passes on Windows
    if os.name == "nt":
        assert "\\" in env["CLAUDE_PROJECT_DIR"]
    # How Claude Code runs a command hook with "shell": "bash": <bash> -c <command>.
    r = subprocess.run([BASH, "-c", HOOK_COMMAND], env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")


# ---- POSIX helpers ----------------------------------------------------------------------------

def _write_exec(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8", newline="\n")
    path.chmod(0o755)
    return path


def _wait_for(path: Path, timeout: float = 15.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if path.is_file() and path.stat().st_size > 0:
            return True
        time.sleep(0.05)
    return False


def _tree(root: Path) -> dict[str, tuple]:
    """Every path under root with its type, size and mtime: a write anywhere changes it."""
    out = {}
    for p in sorted(root.rglob("*")):
        st = p.lstat()
        out[p.relative_to(root).as_posix()] = (p.is_dir(), st.st_size, st.st_mtime_ns)
    return out


# ---- fetch_artifacts.sh on a generated artifact set --------------------------------------------

@pytest.fixture
def artifacts(tmp_path):
    src = tmp_path / "src"
    (src / "parts").mkdir(parents=True)
    files = {"alpha.bin": bytes(range(256)) * 40 + b"tail", "beta.txt": b"beta\n"}
    sums = []
    for name, data in files.items():
        sums.append(f"{hashlib.sha256(data).hexdigest()}  {name}\n")
        chunks = [data[i:i + 4000] for i in range(0, len(data), 4000)]
        for i, chunk in enumerate(chunks):
            (src / "parts" / f"{name}.part-{i:03d}").write_bytes(chunk)
    # not an "<name>.part-<digits>" member: must be ignored
    (src / "parts" / "alpha.bin.part-old").write_bytes(b"junk")
    (src / "SHA256SUMS.full").write_text("".join(sums), encoding="utf-8", newline="\n")
    return src, files


def _fetch(src: Path, dest: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(tmp_path / "home"),
           "MATHVERIFY_ARTIFACT_SRC": str(src), "LC_ALL": "C"}
    return subprocess.run([BASH, str(FETCH), str(dest)], env=env, capture_output=True, text=True,
                          timeout=120, cwd=tmp_path)


@posix_only
@needs_bash
def test_fetch_artifacts_assembles_verified_parts(artifacts, tmp_path):
    src, files = artifacts
    dest = tmp_path / "dest"
    r = _fetch(src, dest, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    for name, data in files.items():
        assert (dest / name).read_bytes() == data
    assert (dest / "SHA256SUMS.full").read_bytes() == (src / "SHA256SUMS.full").read_bytes()
    assert (dest / ".source").read_text().startswith("src sha256(SHA256SUMS.full)=")
    assert sorted(os.listdir(dest)) == sorted([*files, "SHA256SUMS.full", ".source"])
    again = _fetch(src, dest, tmp_path)
    assert again.returncode == 0 and "nothing to do" in again.stdout


@posix_only
@needs_bash
@pytest.mark.parametrize("damage", ["flipped-byte", "missing-middle-part", "file-without-parts"])
def test_fetch_artifacts_rejects_damaged_parts_and_leaves_dest_empty(artifacts, tmp_path, damage):
    src, _ = artifacts
    parts = src / "parts"
    if damage == "flipped-byte":
        p = parts / "alpha.bin.part-001"
        data = bytearray(p.read_bytes())
        data[17] ^= 0x01
        p.write_bytes(bytes(data))
    elif damage == "missing-middle-part":
        (parts / "alpha.bin.part-001").unlink()
    else:
        (parts / "beta.txt.part-000").unlink()
    dest = tmp_path / "dest"
    r = _fetch(src, dest, tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    assert os.listdir(dest) == []


# ---- session_start.sh: the Lean state machine on stub prefixes ---------------------------------

def _stub_python(version: str = "3.14.6") -> str:
    """A stand-in interpreter: version queries, `-m venv DIR` (copies itself and names itself in
    DIR/pyvenv.cfg, as the real venv does), anything else succeeds."""
    return f"""
    #!/bin/sh
    case "$1" in
      -c) case "$2" in
            *platform*) echo {version} ;;
            *sys.version*) echo "{version} (stub)" ;;
          esac ;;
      -m) if [ "$2" = venv ]; then
            mkdir -p "$3/bin" && cp "$0" "$3/bin/python" && echo "executable = $0" > "$3/pyvenv.cfg"
          fi ;;
    esac
    exit 0
"""


STUB_PYTHON = _stub_python()
# A stand-in uv for the hook: `python find` answers STUB_UV_FIND (else "not found"), `venv -q
# --python PY DIR` makes a venv like the stub interpreter's, `pip install` succeeds. Each call is
# recorded as "cwd TAB VIRTUAL_ENV TAB argv".
STUB_UV = r"""
    #!/bin/sh
    printf '%s\t%s\t%s\n' "$PWD" "${VIRTUAL_ENV:-}" "$*" >> "@CALLS@"
    case "$1 $2" in
      "python find") [ -n "${STUB_UV_FIND:-}" ] || exit 2; echo "$STUB_UV_FIND" ;;
      "venv -q") mkdir -p "$5/bin" && cp "$4" "$5/bin/python" && echo "executable = $4" > "$5/pyvenv.cfg" ;;
      "pip install") ;;
      *) echo "stub uv: unexpected $*" >&2; exit 2 ;;
    esac
"""


class HookBed:
    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.repo = tmp_path / "repo"
        self.home = tmp_path / "home"
        self.env_file = tmp_path / "claude_env"
        self.marker = tmp_path / "installer_started"
        (self.repo / "scripts" / "cloud").mkdir(parents=True)
        self.home.mkdir()
        shutil.copy2(HOOK, self.repo / "scripts" / "cloud" / "session_start.sh")
        shutil.copytree(ROOT / "lean", self.repo / "lean", ignore=shutil.ignore_patterns(".lake"))
        for f in ("pyproject.toml", "requirements.lock"):
            shutil.copy2(ROOT / f, self.repo / f)
        # The installer the hook starts in the background: it only records how it was called.
        _write_exec(self.repo / "scripts" / "cloud" / "setup_env.sh", f"""
            #!/usr/bin/env bash
            echo "$* OPT=$MATHVERIFY_OPT" >> "{self.marker}"
        """)
        self.fingerprint = self._fingerprint()

    def _fingerprint(self) -> str:
        # The hook's own lean_fingerprint(), evaluated on this bed's lean/.
        script = f'REPO="{self.repo}"\n{_function(HOOK, "lean_fingerprint")}\nlean_fingerprint\n'
        r = subprocess.run([BASH, "-c", script], capture_output=True, text=True, timeout=60)
        fp = r.stdout.strip()
        assert re.fullmatch(r"[0-9a-f]{64}", fp), r
        return fp

    def prefix(self, name: str = "opt", *, repl: bool = False, done: str | None = None,
               status: str | None = None, lock_file: bool = False, python: bool = True) -> Path:
        p = self.tmp / name
        if python:
            _write_exec(p / "python3.14" / "bin" / "python3.14", STUB_PYTHON)
        logs = p / "mathverify-logs"
        logs.mkdir(parents=True, exist_ok=True)
        if repl:
            _write_exec(p / "repl" / ".lake" / "build" / "bin" / "repl", "#!/bin/sh\nexit 1\n")
            (p / "mathverify-lean" / ".lake").mkdir(parents=True, exist_ok=True)
            (p / "elan" / "bin").mkdir(parents=True, exist_ok=True)
        if done is not None:
            (logs / "lean.done").write_text(done + "\n", encoding="utf-8")
        if status is not None:
            (logs / "setup_env.status").write_text(status + "\n", encoding="utf-8")
        if lock_file:
            (logs / "setup_env.lock").touch()
        return p

    def run(self, *prefixes: Path, **extra: str) -> str:
        env = {"PATH": "/usr/bin:/bin", "HOME": str(self.home), "TMPDIR": str(self.tmp),
               "CLAUDE_CODE_REMOTE": "true", "CLAUDE_PROJECT_DIR": str(self.repo),
               "CLAUDE_ENV_FILE": str(self.env_file), "MATHVERIFY_OPT": str(prefixes[0]),
               "MATHVERIFY_HOOK_PREFIXES": ":".join(map(str, prefixes)), **extra}
        r = subprocess.run([BASH, str(self.repo / "scripts" / "cloud" / "session_start.sh")],
                           env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           timeout=120, cwd=self.tmp)
        assert r.returncode == 0 and r.stderr == "", r
        self.session_log = (prefixes[0] / "mathverify-logs" / "session_start.log").read_text()
        return r.stdout

    def line(self, out: str, start: str) -> str:
        (line,) = [ln for ln in out.splitlines() if ln.startswith(start)]
        return line

    def lean_line(self, out: str) -> str:
        return self.line(out, "- Lean: ")

    def started(self) -> bool:
        return "started setup_env.sh --lean-only" in self.session_log

    def interpreters(self, versions: dict[str, str]) -> Path:
        """A PATH directory with stub interpreters (name -> version) and the stub uv."""
        b = self.tmp / "pybin"
        for name, version in versions.items():
            _write_exec(b / name, _stub_python(version))
        _write_exec(b / "uv", STUB_UV.replace("@CALLS@", str(self.uv_calls)))
        return b

    @property
    def uv_calls(self) -> Path:
        return self.tmp / "uv_calls"

    def rerun_command(self) -> str:
        """The command the status block gives for running the hook again in the same session."""
        return (f'CLAUDE_CODE_REMOTE=true CLAUDE_ENV_FILE="{self.env_file}" '
                f'bash "{self.repo}/scripts/cloud/session_start.sh"')

    def venv_python(self) -> str:
        """The interpreter the hook built ./.venv with (pyvenv.cfg as the stubs write it)."""
        return (self.repo / ".venv" / "pyvenv.cfg").read_text().removeprefix("executable = ").strip()


FAILED_REPL = ("FAILED mode=all failed=[setup_lean_repl] stages=[fetch_artifacts(6s) "
               "setup_lean(126s) setup_lean_repl(9s)] python=3.14.6 lean=missing total=150s")
RERUN_HINT = "kanca bu oturumda kendiliğinden yeniden çalışmaz"


@pytest.fixture
def bed(tmp_path):
    if BASH is None:
        pytest.skip("no bash")
    return HookBed(tmp_path)


@posix_only
def test_hook_ready_needs_lean_done_with_the_current_fingerprint(bed):
    opt = bed.prefix(repl=True, done=bed.fingerprint,
                     status="OK mode=all failed=[] python=3.14.6 lean=ready total=150s")
    out = bed.run(opt)
    assert bed.lean_line(out) == f"- Lean: HAZIR ({opt}/repl/.lake/build/bin/repl)"
    assert bed.line(out, "- Python: ") == f"- Python: 3.14.6 ({opt}/python3.14/bin/python3.14)"
    assert "BAŞARISIZ" not in out and RERUN_HINT not in out
    assert not bed.started()
    env = bed.env_file.read_text()
    assert f'export MATHVERIFY_LEAN_REPL="{opt}/repl/.lake/build/bin/repl"' in env
    assert os.readlink(bed.home / "repl") == str(opt / "repl")
    # a second session adds nothing to the env file and starts nothing
    bed.run(opt)
    assert bed.env_file.read_text() == env and not bed.started()


@posix_only
def test_hook_retries_a_failed_install_and_prints_the_failure(bed):
    # What a failed run leaves: the REPL binary is built before its smoke test, so it exists, but
    # lean.done does not; the lock file is there and nobody holds it.
    opt = bed.prefix(repl=True, status=FAILED_REPL, lock_file=True)
    out = bed.run(opt)
    assert "HAZIR" not in out
    assert bed.lean_line(out).startswith("- Lean: KURULUYOR (arka planda başlatıldı")
    assert f"Önceki kurulum BAŞARISIZ ({opt}/mathverify-logs/setup_env.status): {FAILED_REPL}" in out
    assert bed.started()
    assert _wait_for(bed.marker)
    assert bed.marker.read_text() == f"--lean-only OPT={opt}\n"
    assert not os.path.lexists(bed.home / "repl")  # not linked while unverified


@posix_only
def test_hook_starts_an_install_when_nothing_is_there(bed):
    opt = bed.prefix()
    out = bed.run(opt)
    assert bed.lean_line(out).startswith("- Lean: KURULUYOR (arka planda başlatıldı")
    assert "BAŞARISIZ" not in out
    assert _wait_for(bed.marker) and bed.marker.read_text() == f"--lean-only OPT={opt}\n"
    # Nothing runs the hook again when that install finishes: the status block says how.
    hint = bed.line(out, "  Kurulum bitince ")
    assert hint == (f'  Kurulum bitince ({opt}/mathverify-logs/setup_env.status "OK" ile başlar) '
                    f"{RERUN_HINT}; ~/.elan, ~/mathverify-lean, ~/repl bağlantıları için: "
                    f"{bed.rerun_command()}")


@posix_only
@pytest.mark.parametrize("holder", ["flock", "pid-file"])
def test_hook_does_not_start_a_second_install(bed, holder):
    opt = bed.prefix(repl=True, status=FAILED_REPL)
    logs = opt / "mathverify-logs"
    if holder == "flock":
        if shutil.which("flock") is None:
            pytest.skip("no flock(1)")
        proc = subprocess.Popen(["flock", str(logs / "setup_env.lock"), "sleep", "60"],
                                start_new_session=True)
        end = time.monotonic() + 10
        while subprocess.run(["flock", "-n", "-E", "75", str(logs / "setup_env.lock"), "true"]
                             ).returncode != 75:
            assert time.monotonic() < end, "the lock was never taken"
            time.sleep(0.05)
    else:
        proc = subprocess.Popen(["sleep", "60"], start_new_session=True)
        (logs / "setup_env.pid").write_text(f"{proc.pid}\n")
    try:
        out = bed.run(opt)
    finally:
        os.killpg(proc.pid, signal.SIGTERM)  # flock's child holds the lock too
        proc.wait(timeout=10)
    assert bed.lean_line(out).startswith("- Lean: KURULUYOR (başka bir setup_env.sh çalışıyor")
    assert "Önceki kurulum BAŞARISIZ" in out
    assert not bed.started()
    time.sleep(0.5)
    assert not bed.marker.exists()


@posix_only
def test_hook_updates_an_install_made_from_other_pins(bed):
    opt = bed.prefix(repl=True, done="0" * 64)
    out = bed.run(opt)
    assert bed.lean_line(out).startswith("- Lean: HAZIR ama lean/ sabitleri kurulumdan farklı")
    assert bed.started()
    assert _wait_for(bed.marker) and bed.marker.read_text() == f"--lean-only OPT={opt}\n"
    assert os.readlink(bed.home / "repl") == str(opt / "repl")  # still usable meanwhile


@posix_only
def test_hook_prefers_the_prefix_built_from_the_current_pins(bed):
    old = bed.prefix("old", repl=True, done="0" * 64)
    new = bed.prefix("new", repl=True, done=bed.fingerprint)
    out = bed.run(old, new)
    assert bed.lean_line(out) == f"- Lean: HAZIR ({new}/repl/.lake/build/bin/repl)"
    assert not bed.started()


@posix_only
def test_hook_reports_a_failed_setup_even_when_lean_is_ready(bed):
    status = "FAILED mode=all failed=[uv_prewarm] stages=[uv_prewarm(3s)] python=3.14.6 lean=ready total=9s"
    opt = bed.prefix(repl=True, done=bed.fingerprint, status=status)
    out = bed.run(opt)
    assert bed.lean_line(out).startswith("- Lean: HAZIR (")
    assert f"Önceki kurulum BAŞARISIZ ({opt}/mathverify-logs/setup_env.status): {status}" in out


@posix_only
def test_hook_skip_lean_never_starts_an_install(bed):
    opt = bed.prefix(repl=True, status=FAILED_REPL, lock_file=True)
    out = bed.run(opt, MATHVERIFY_SKIP_LEAN="1")
    assert bed.lean_line(out).startswith("- Lean: YOK (MATHVERIFY_SKIP_LEAN=1")
    assert "Önceki kurulum BAŞARISIZ" in out
    assert not bed.started()


PER_USER_COMMAND = 'MATHVERIFY_OPT="$HOME/.mathverify-opt" bash scripts/cloud/setup_env.sh --lean-only'


def _read_only_prefix(bed: HookBed, name: str = "opt") -> Path:
    """A finished install from other pins in a prefix this (non-root) user cannot write, with the
    world-writable log directory setup_env.sh leaves behind: a root-made /opt seen by the session."""
    if os.geteuid() == 0:
        pytest.skip("root writes read-only directories")
    opt = bed.prefix(name, repl=True, done="0" * 64)
    (opt / "mathverify-logs").chmod(0o777)
    opt.chmod(0o555)
    return opt


@posix_only
def test_hook_stale_read_only_prefix_prints_the_per_user_command(bed):
    opt = _read_only_prefix(bed)
    try:
        out = bed.run(opt)
    finally:
        opt.chmod(0o755)
    assert bed.lean_line(out).startswith(
        f"- Lean: ESKİ: lean/ sabitleri kurulumdan farklı ve {opt} bu kullanıcıya")
    # `setup_env.sh --lean-only` alone would install into the read-only prefix and fail; the
    # per-user form works, and its disk cost is stated (a second full install is never automatic).
    (hint,) = [ln for ln in out.splitlines() if PER_USER_COMMAND in ln]
    assert hint.startswith("  Güncel sabitlerle kullanıcı kurulumu (yaklaşık 12 GB disk ister;")
    assert "$HOME altında boş: " in hint
    assert not bed.started()
    time.sleep(0.5)
    assert not bed.marker.exists()
    # the stale install stays in use meanwhile
    assert f'export MATHVERIFY_LEAN_REPL="{opt}/repl/.lake/build/bin/repl"' in bed.env_file.read_text()
    assert os.readlink(bed.home / "repl") == str(opt / "repl")


@posix_only
def test_hook_stale_read_only_prefix_reports_a_running_user_install(bed):
    opt = _read_only_prefix(bed)
    user = bed.prefix("user-opt")
    proc = subprocess.Popen(["sleep", "60"], start_new_session=True)
    (user / "mathverify-logs" / "setup_env.pid").write_text(f"{proc.pid}\n")
    try:
        out = bed.run(opt, user)
    finally:
        opt.chmod(0o755)
        proc.kill()
        proc.wait(timeout=10)
    assert bed.lean_line(out) == (
        f"- Lean: HAZIR ama lean/ sabitleri kurulumdan farklı; güncel sabitlerle yeni kurulum {user} "
        f"içinde sürüyor (günlük: {user}/mathverify-logs/setup_env.log). Bitene dek Lean sonuçları "
        f"eski sabitlerle ({opt}).")
    assert PER_USER_COMMAND not in out
    assert not bed.started()


@posix_only
def test_hook_follows_a_per_user_install_of_the_current_pins(bed):
    # Session 1: only the stale read-only install exists; the hook links ~/.elan etc. to it.
    opt = _read_only_prefix(bed)
    user = bed.prefix("user-opt")
    foreign = bed.tmp / "someone-elses-elan"
    try:
        bed.run(opt, user)
        assert os.readlink(bed.home / "repl") == str(opt / "repl")
        (bed.home / "mathverify-lean").unlink()
        (bed.home / "mathverify-lean").symlink_to(foreign)  # not a link this hook made
        # Session 2 (resumed): the per-user install of the current pins has finished meanwhile.
        user = bed.prefix("user-opt", repl=True, done=bed.fingerprint)
        out = bed.run(opt, user)
        assert bed.lean_line(out) == f"- Lean: HAZIR ({user}/repl/.lake/build/bin/repl)"
        assert os.readlink(bed.home / "repl") == str(user / "repl")
        assert os.readlink(bed.home / ".elan") == str(user / "elan")
        assert os.readlink(bed.home / "mathverify-lean") == str(foreign)
        # Session 3: the per-user install was deleted (to free disk, say): back to the stale one.
        shutil.rmtree(user)
        out = bed.run(opt, user)
    finally:
        opt.chmod(0o755)
    assert bed.lean_line(out).startswith("- Lean: ESKİ: ")
    assert os.readlink(bed.home / "repl") == str(opt / "repl")  # not left dangling
    assert os.readlink(bed.home / "mathverify-lean") == str(foreign)
    # the last exported block (the one that wins when the file is sourced) is the current install
    exports = [ln for ln in bed.env_file.read_text().splitlines() if ln.startswith("export MATHVERIFY_LEAN_REPL=")]
    assert exports == [f'export MATHVERIFY_LEAN_REPL="{p}/repl/.lake/build/bin/repl"' for p in (opt, user, opt)]


@posix_only
def test_hook_writable_stale_prefix_is_updated_but_skip_lean_prints_the_command(bed):
    opt = bed.prefix(repl=True, done="0" * 64)
    out = bed.run(opt, MATHVERIFY_SKIP_LEAN="1")
    assert bed.lean_line(out).startswith("- Lean: ESKİ: lean/ sabitleri kurulumdan farklı; MATHVERIFY_SKIP_LEAN=1")
    assert f'  Elle güncelleme: MATHVERIFY_OPT="{opt}" bash scripts/cloud/setup_env.sh --lean-only' in out
    assert not bed.started()


@posix_only
def test_hook_restores_missing_reports_and_never_overwrites(bed):
    # The committed snapshot fills in git-ignored reports/*.json (calibration.json included, which
    # fuse/rules.py reads under MATHVERIFY_CALIBRATION=on), as on the local machine. A file that
    # is already there is never replaced, and only *.json are copied.
    reports = bed.repo / "reports"
    arsiv = reports / "arsiv" / "2026-09-24"
    arsiv.mkdir(parents=True)
    snapshot = {"calibration.json": '{"from": "archive"}\n', "eval_results.json": '{"n": 1}\n',
                "lean_results.json": '{"n": 2}\n'}
    for name, text in snapshot.items():
        (arsiv / name).write_text(text, encoding="utf-8")
    (arsiv / "notes.md").write_text("not a report\n", encoding="utf-8")
    (reports / "calibration.json").write_text('{"from": "this machine"}\n', encoding="utf-8")
    opt = bed.prefix()
    out = bed.run(opt, MATHVERIFY_SKIP_LEAN="1")
    assert "- Raporlar: reports/arsiv/2026-09-24/ içinden 2 eksik JSON kopyalandı" in out
    assert (reports / "calibration.json").read_text(encoding="utf-8") == '{"from": "this machine"}\n'
    for name in ("eval_results.json", "lean_results.json"):
        assert (reports / name).read_bytes() == (arsiv / name).read_bytes()
        assert (reports / name).stat().st_mtime_ns == (arsiv / name).stat().st_mtime_ns  # cp -p
    assert not (reports / "notes.md").exists()
    before = _tree(reports)
    again = bed.run(opt, MATHVERIFY_SKIP_LEAN="1")
    assert "Raporlar" not in again
    assert _tree(reports) == before


# ---- session_start.sh: which interpreter builds the .venv --------------------------------------

@pytest.fixture(scope="session")
def sysbin(tmp_path_factory) -> str:
    """/usr/bin and /bin as symlinks, minus every python* and uv*: the hook's interpreter search
    then sees only the stubs a test puts in front of it (WSL Ubuntu has /usr/bin/python3.14, the
    cloud /usr/bin/python3.12 and python3.13)."""
    d = tmp_path_factory.mktemp("sysbin")
    for src in ("/usr/bin", "/bin"):
        if not os.path.isdir(src):
            continue
        for name in os.listdir(src):
            if name.startswith(("python", "uv")) or os.path.lexists(d / name):
                continue
            (d / name).symlink_to(os.path.join(src, name))
    return str(d)


FALLBACK_NOTE = ("Windows'takiyle (3.14.7) aynı değil. Tam takım yedek yorumlayıcılardan yalnız "
                 "3.12.11'de ölçüldü ve Windows ile aynı sonucu verdi (DECISIONS §42)")


@posix_only
@pytest.mark.parametrize("have, chosen", [
    ({"python3.14": "3.14.2", "python3.13": "3.13.5", "python3": "3.11.15"}, "python3.14"),
    ({"uv-managed": "3.14.3", "python3.13": "3.13.5"}, "uv python find 3.14"),
    # the cloud as measured: python3 is 3.11.15, python3.13 and python3.12 exist. The full suite
    # was measured only on 3.12.11 among the fallbacks, so python3.12 wins over python3.13.
    ({"python3.13": "3.13.5", "python3.12": "3.12.3", "python3": "3.11.15"}, "python3.12"),
    ({"python3.12": "3.12.3", "python3": "3.11.15"}, "python3.12"),
    ({"python3.13": "3.13.5", "python3": "3.11.15"}, "python3.13"),
    ({"python3": "3.12.11"}, "python3"),
])
def test_hook_fallback_interpreter_order(bed, sysbin, have, chosen):
    opt = bed.prefix(python=False)  # no setup script ran: the pinned 3.14.6 is not there yet
    pybin = bed.interpreters({k: v for k, v in have.items() if k != "uv-managed"})
    extra = {}
    exe, version = pybin / chosen, have.get(chosen)
    if "uv-managed" in have:  # a python3.14 only uv knows of (a uv-managed install, say)
        exe = _write_exec(bed.tmp / "uv-python" / "bin" / "python3.14", _stub_python(have["uv-managed"]))
        version = have["uv-managed"]
        extra["STUB_UV_FIND"] = str(exe)
    out = bed.run(opt, PATH=f"{pybin}:{sysbin}", VIRTUAL_ENV=str(bed.repo / ".venv"),
                  MATHVERIFY_SKIP_LEAN="1", **extra)
    assert bed.line(out, "- Python: ") == (
        f"- Python: {version} ({exe}) — YEDEK ({chosen}): kurulum betiğinin CPython 3.14.6'sı "
        f"({opt}/python3.14) yok ya da çalışmıyor; bu yorumlayıcı {FALLBACK_NOTE}")
    assert bed.line(out, "- .venv: ").startswith("- .venv: KURULDU (")
    assert bed.venv_python() == str(exe)
    calls = [ln.split("\t") for ln in bed.uv_calls.read_text().splitlines()]
    assert [c[2] for c in calls][-3:] == [
        f"venv -q --python {exe} {bed.repo}/.venv",
        f"pip install --python {bed.repo}/.venv/bin/python --offline -r {bed.repo}/requirements.lock",
        f"pip install --python {bed.repo}/.venv/bin/python --offline --no-deps -e {bed.repo}"]
    # uv is asked for a 3.14 from / and without VIRTUAL_ENV, so it cannot answer with ./.venv
    finds = [c for c in calls if c[2].startswith("python find")]
    if chosen == "python3.14":
        assert finds == []
    else:
        assert finds == [["/", "", "python find 3.14"]]


@posix_only
def test_hook_never_builds_the_venv_with_a_python_older_than_3_12(bed, sysbin):
    opt = bed.prefix(python=False)
    pybin = bed.interpreters({"python3": "3.11.15"})
    keep = bed.repo / ".venv" / "keep"
    keep.parent.mkdir()
    keep.write_text("an earlier .venv\n")
    out = bed.run(opt, PATH=f"{pybin}:{sysbin}", MATHVERIFY_SKIP_LEAN="1")
    assert bed.line(out, "- Python: ") == (
        f"- Python: yok — HATA: Python >= 3.12 bulunamadı (sırayla: {opt}/python3.14, python3.14, "
        f"uv python find 3.14, python3.12, python3.13, python3); 3.12'den eski ya da çalışmayan: "
        f"python3 = {pybin}/python3 (3.11.15)")
    assert bed.line(out, "- .venv: ").startswith(
        "- .venv: HATA: Python >= 3.12 yok; .venv kurulmadı (var olan .venv'e dokunulmadı)")
    assert sorted(os.listdir(bed.repo / ".venv")) == ["keep"]
    assert [ln.split("\t")[2] for ln in bed.uv_calls.read_text().splitlines()] == ["python find 3.14"]


@posix_only
def test_hook_never_picks_an_interpreter_inside_the_venv(bed, sysbin):
    # A PATH with ./.venv activated names .venv/bin/python3.14; build_venv deletes .venv first.
    opt = bed.prefix(python=False)
    venv_bin = bed.repo / ".venv" / "bin"
    _write_exec(venv_bin / "python3.14", STUB_PYTHON)
    pybin = bed.interpreters({"python3.12": "3.12.3"})
    out = bed.run(opt, PATH=f"{venv_bin}:{pybin}:{sysbin}", MATHVERIFY_SKIP_LEAN="1")
    assert bed.line(out, "- Python: ").startswith(f"- Python: 3.12.3 ({pybin}/python3.12) — YEDEK (python3.12): ")
    assert bed.venv_python() == str(pybin / "python3.12")


@posix_only
def test_hook_rebuilds_a_fallback_venv_once_the_pinned_python_exists(bed, sysbin):
    # Measured in the cloud (2026-09-24, no setup script): the first session start has no
    # /opt/python3.14; the hook's own background install brings it, and only a re-run of the
    # hook in that session rebuilds the .venv with it.
    opt = bed.prefix(python=False)
    pybin = bed.interpreters({"python3.13": "3.13.5", "python3": "3.11.15"})
    path = f"{pybin}:{sysbin}"
    out = bed.run(opt, PATH=path)
    assert bed.line(out, "- Python: ").startswith(f"- Python: 3.13.5 ({pybin}/python3.13) — YEDEK (python3.13): ")
    assert bed.lean_line(out).startswith("- Lean: KURULUYOR (arka planda başlatıldı")
    assert bed.line(out, "  Kurulum bitince ").endswith(
        f"{RERUN_HINT}; .venv'i CPython 3.14.6 ile yeniden kurmak ve ~/.elan, ~/mathverify-lean, "
        f"~/repl bağlantıları için: {bed.rerun_command()}")
    assert bed.venv_python() == str(pybin / "python3.13")
    assert _wait_for(bed.marker)
    # The install has put the pinned interpreter in place; the printed command is run as a later
    # Bash command of the session would run it (the hook's CLAUDE_* variables are not set there).
    _write_exec(opt / "python3.14" / "bin" / "python3.14", STUB_PYTHON)
    env = {"PATH": path, "HOME": str(bed.home), "TMPDIR": str(bed.tmp), "MATHVERIFY_OPT": str(opt),
           "MATHVERIFY_HOOK_PREFIXES": str(opt)}
    r = subprocess.run([BASH, "-c", bed.rerun_command()], env=env, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=120, cwd=bed.tmp)
    assert r.returncode == 0 and r.stderr == "", r
    assert bed.line(r.stdout, "- Python: ") == f"- Python: 3.14.6 ({opt}/python3.14/bin/python3.14)"
    assert bed.line(r.stdout, "- .venv: ").startswith("- .venv: KURULDU (")
    assert bed.venv_python() == str(opt / "python3.14" / "bin" / "python3.14")
    # the next session finds the stamp current
    out = bed.run(opt, PATH=path, MATHVERIFY_SKIP_LEAN="1")
    assert bed.line(out, "- .venv: ").startswith("- .venv: HAZIR (değişiklik yok)")
    assert bed.venv_python() == str(opt / "python3.14" / "bin" / "python3.14")


# ---- setup_env.sh: the uv prewarm writes nothing under the repository --------------------------

def _prewarm_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "scripts" / "cloud").mkdir(parents=True)
    shutil.copy2(SETUP_ENV, repo / "scripts" / "cloud" / "setup_env.sh")
    for f in ("pyproject.toml", "requirements.lock"):
        shutil.copy2(ROOT / f, repo / f)
    shutil.copytree(ROOT / "src", repo / "src",
                    ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    return repo


def _run_setup_env(repo: Path, opt: Path, tmp_path: Path, path: str, *args: str):
    env = {"PATH": path, "HOME": str(tmp_path / "home"), "TMPDIR": str(tmp_path),
           "MATHVERIFY_OPT": str(opt), "CLAUDE_PROJECT_DIR": str(repo),
           "MATHVERIFY_PROFILE_D": str(tmp_path / "profile.d")}
    (tmp_path / "home").mkdir(exist_ok=True)
    return subprocess.run([BASH, str(repo / "scripts" / "cloud" / "setup_env.sh"), *args],
                          env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          timeout=1800, cwd=tmp_path)


@posix_only
@needs_bash
def test_setup_env_prewarm_writes_nothing_under_the_repo(tmp_path):
    repo = _prewarm_repo(tmp_path)
    opt = tmp_path / "opt"
    _write_exec(opt / "python3.14" / "bin" / "python3.14", STUB_PYTHON)
    calls = tmp_path / "uv_calls"
    pycalls = tmp_path / "python_calls"
    # A stand-in uv: records cwd and argv, and writes into an editable install's source tree what
    # a real setuptools build writes there (src/<name>.egg-info), so a build in the checkout shows.
    _write_exec(tmp_path / "bin" / "uv", f"""
        #!/usr/bin/env bash
        printf '%s\\t%s\\n' "$PWD" "$*" >> "{calls}"
        case "$1" in
          --version) echo "uv 0.0.0 (stub)" ;;
          venv)
            for d; do :; done
            mkdir -p "$d/bin"
            printf '#!/bin/sh\\necho "PYTHONDONTWRITEBYTECODE=$PYTHONDONTWRITEBYTECODE $*" >> "{pycalls}"\\n' > "$d/bin/python"
            chmod +x "$d/bin/python" ;;
          pip)
            prev=
            for a; do
              if [ "$prev" = -e ]; then mkdir -p "$a/src/mathverify.egg-info" && echo stub > "$a/src/mathverify.egg-info/PKG-INFO"; fi
              prev="$a"
            done ;;
        esac
        exit 0
    """)
    before = _tree(repo)
    r = _run_setup_env(repo, opt, tmp_path, f"{tmp_path / 'bin'}:/usr/bin:/bin", "--python-only")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _tree(repo) == before
    status = (opt / "mathverify-logs" / "setup_env.status").read_text()
    assert status.startswith("OK mode=python failed=[] stages=[uv_prewarm("), status
    assert (opt / "mathverify-logs" / "uv-prewarm.done").is_file()
    lines = [ln.split("\t") for ln in calls.read_text().splitlines()]
    (editable,) = [argv.split() for _, argv in lines if " -e " in f" {argv} "]
    target = Path(editable[editable.index("-e") + 1])
    assert repo not in target.parents and target != repo
    assert not target.exists()  # the throwaway copy is removed with the prewarm venv
    for cwd, _ in lines:
        assert repo not in Path(cwd).parents and Path(cwd) != repo
    imports = [ln for ln in pycalls.read_text().splitlines() if "import mathverify" in ln]
    assert imports and all(ln.startswith("PYTHONDONTWRITEBYTECODE=1 ") for ln in imports)
    assert not list(opt.glob(".uv-prewarm.*"))


def _integration_python() -> Path | None:
    home = os.environ.get("MATHVERIFY_TEST_PYTHON314", "/opt/python3.14")
    exe = Path(home) / "bin" / "python3.14"
    return Path(home) if exe.is_file() else None


@posix_only
@needs_bash
@pytest.mark.skipif(os.environ.get("MATHVERIFY_CLOUD_INTEGRATION") != "1",
                    reason="opt-in: downloads the locked packages (MATHVERIFY_CLOUD_INTEGRATION=1)")
def test_setup_env_real_prewarm_then_offline_session_install(tmp_path):
    py_home = _integration_python()
    uv = shutil.which("uv")
    if py_home is None or uv is None:
        pytest.skip("needs CPython 3.14.6 (MATHVERIFY_TEST_PYTHON314 or /opt/python3.14) and uv on PATH")
    repo = _prewarm_repo(tmp_path)
    opt = tmp_path / "opt"
    opt.mkdir()
    shutil.copytree(py_home, opt / "python3.14", symlinks=True)
    before = _tree(repo)
    path = f"{Path(uv).parent}:/usr/bin:/bin"
    r = _run_setup_env(repo, opt, tmp_path, path, "--python-only")
    assert r.returncode == 0, r.stdout + r.stderr
    status = (opt / "mathverify-logs" / "setup_env.status").read_text()
    assert status.startswith("OK mode=python failed=[]"), status + r.stdout
    assert _tree(repo) == before
    # The session user's install, as session_start.sh runs it: offline, from the prewarmed cache.
    env = {**os.environ, "UV_CACHE_DIR": str(opt / "uv-cache"), "UV_PYTHON_DOWNLOADS": "never"}
    venv = tmp_path / "session-venv"
    for cmd in ([uv, "venv", "-q", "--python", str(opt / "python3.14" / "bin" / "python3.14"), str(venv)],
                [uv, "pip", "install", "--python", str(venv / "bin" / "python"), "--offline",
                 "-r", str(repo / "requirements.lock")],
                [uv, "pip", "install", "--python", str(venv / "bin" / "python"), "--offline",
                 "--no-deps", "-e", str(repo)],
                [str(venv / "bin" / "python"), "-c", "import mathverify; print(mathverify.__file__)"]):
        c = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600, cwd=tmp_path)
        assert c.returncode == 0, (cmd, c.stdout, c.stderr)
    assert c.stdout.strip() == str(repo / "src" / "mathverify" / "__init__.py")


# ---- setup_env.sh, setup_lean.sh, setup_lean_repl.sh on a stub Lean install ---------------------

TOOLCHAIN = "leanprover/lean4:v4.34.0"
TC_DIR_NAME = "leanprover--lean4---v4.34.0"
FAKE_REPL_URL = "https://example.invalid/repl"
SHIFTED_TOOLCHAIN = "leanprover/lean4:v4.99.0"  # what the pinned REPL revision names

STUB_ELAN = """
    #!/bin/sh
    [ "$1" = --version ] && { echo "elan 4.2.4 (stub)"; exit 0; }
    echo "stub elan: unexpected $*" >&2
    exit 3
"""
STUB_LEAN = """
    #!/bin/sh
    case "$1" in
      --print-prefix) echo "$ELAN_HOME/toolchains/@TC@" ;;
      --version) echo "Lean (version 4.34.0, stub)" ;;
      *) echo "stub lean: unexpected $*" >&2; exit 3 ;;
    esac
"""
# Records "cwd TAB argv TAB HTTPS_PROXY TAB GIT_ALLOW_PROTOCOL TAB MATHLIB_CACHE_DIR" and does
# what the scripts expect of the real Lake. STUB_LEAN_SMOKE=fail / STUB_REPL_SMOKE=fail make the
# `import Mathlib` smoke test and the REPL smoke test fail; STUB_LEAN_SMOKE_FAIL_IN=DIR makes the
# `import Mathlib` smoke test fail only when it runs in DIR (a project that breaks when renamed).
STUB_LAKE = r"""
    #!/usr/bin/env bash
    printf '%s\t%s\t%s\t%s\t%s\n' "$PWD" "$*" "${HTTPS_PROXY:-}" "${GIT_ALLOW_PROTOCOL:-}" \
      "${MATHLIB_CACHE_DIR:-}" >> "@CALLS@"
    lib=.lake/packages/mathlib/.lake/build/lib/lean
    case "$1 ${2:-}" in
      "--version ") echo "Lake version 5.0.0 (stub)" ;;
      "exe cache")
        [ "${3:-}" = unpack ] || { echo "stub lake: unexpected $*" >&2; exit 2; }
        (cd .lake/packages/mathlib && find Mathlib -name '*.lean') | while read -r m; do
          mkdir -p "$lib/$(dirname "$m")" && echo olean > "$lib/${m%.lean}.olean"
        done ;;
      "build Mathlib") echo olean > "$lib/Mathlib.olean" ;;
      "build ")
        mkdir -p .lake/build/bin && printf '#!/bin/sh\nexit 0\n' > .lake/build/bin/repl
        chmod +x .lake/build/bin/repl ;;
      "env lean")
        [ "${STUB_LEAN_SMOKE:-ok}" = ok ] || { echo "error: stub smoke failure"; exit 1; }
        [ "$PWD" != "${STUB_LEAN_SMOKE_FAIL_IN:-}" ] || { echo "error: stub smoke failure in $PWD"; exit 1; }
        echo "'smoke' depends on axioms: [propext, Classical.choice, Quot.sound]" ;;
      "env "*/repl)
        cat > /dev/null
        [ "${STUB_REPL_SMOKE:-ok}" = ok ] || { echo '{"severity": "error"}'; exit 0; }
        printf '{"env": 0}\n\n{"env": 1}\n' ;;
      *) echo "stub lake: unexpected $*" >&2; exit 2 ;;
    esac
"""

# df records the directory it was asked about and answers from STUB_DF_MAP, a file of
# "PREFIX TAB FILESYSTEM TAB AVAIL_KB" lines (the first PREFIX that is the directory or one of its
# parents wins; FILESYSTEM "-" makes df fail), else for a virtual-disk-like /dev/sdd with
# STUB_DF_AVAIL_KB free (default 100 GB, so no test depends on the host's free disk). Measured in
# WSL 2 (2026-09-24): `df -Pk` names the distribution's disk /dev/sdd and a Windows drive "C:\".
STUB_DF = r"""
    #!/bin/sh
    for d; do :; done
    echo "$d" >> "@CALLS@"
    fs=/dev/sdd
    avail=${STUB_DF_AVAIL_KB:-104857600}
    if [ -n "${STUB_DF_MAP:-}" ]; then
      tab=$(printf '\t')
      while IFS="$tab" read -r prefix f a; do
        case "$d" in "$prefix"|"$prefix"/*) fs=$f; avail=$a; break ;; esac
      done < "$STUB_DF_MAP"
    fi
    [ "$fs" != - ] || { echo "df: $d: No such file or directory" >&2; exit 1; }
    echo "Filesystem 1024-blocks Used Available Capacity Mounted on"
    printf '%s 209715200 0 %s 0%% /\n' "$fs" "$avail"
"""
# STUB_DU_KB replaces the size `du -sk` reports for a directory (the old project before a staged
# rebuild). A symbolic link is left to the real du, which (without -L) measures the link: 0 KiB.
STUB_DU = r"""
    #!/bin/sh
    if [ "$1" = -sk ] && [ -n "${STUB_DU_KB:-}" ] && [ ! -L "$2" ]; then
      printf '%s\t%s\n' "$STUB_DU_KB" "$2"; exit 0
    fi
    for d in /usr/bin /bin; do [ -x "$d/du" ] && exec "$d/du" "$@"; done
    exit 127
"""
# `uname -r` answers STUB_UNAME_R (default: no WSL kernel), anything else the real uname: with
# MATHVERIFY_WSL_MARKER_DIR pointing at a directory without WSLInterop, no test sees the host's
# WSL (measured 2026-09-24 in WSL Ubuntu: WSLInterop present, uname -r
# 6.18.33.2-microsoft-standard-WSL2).
STUB_UNAME = r"""
    #!/bin/sh
    if [ "$1" = -r ]; then echo "${STUB_UNAME_R:-6.1.0-stub}"; exit 0; fi
    for d in /usr/bin /bin; do [ -x "$d/uname" ] && exec "$d/uname" "$@"; done
    exit 127
"""
GB = 1048576  # KiB

_GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "stub", "GIT_AUTHOR_EMAIL": "stub@example.invalid",
            "GIT_COMMITTER_NAME": "stub", "GIT_COMMITTER_EMAIL": "stub@example.invalid"}


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
                       env={**os.environ, **_GIT_ENV}, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r
    return r.stdout.strip()


def _git_checkout(path: Path, files: dict[str, str], url: str) -> str:
    """A one-commit repository with origin = url, as the sources artifact holds one; its HEAD."""
    for name, text in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text, encoding="utf-8", newline="\n")
    _git(path, "init", "-q")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "pinned")
    _git(path, "remote", "add", "origin", url)
    return _git(path, "rev-parse", "HEAD")


def _dot_entries(d: Path) -> list[str]:
    """Hidden entries: staging, swap and temporary .ltar directories the scripts leave on failure."""
    return sorted(p.name for p in d.iterdir() if p.name.startswith("."))


class LeanBed:
    """A checkout whose lean/ pins name tiny local git repositories (two Lake packages, the REPL),
    the artifact set built from them (parts/ + SHA256SUMS.full for fetch_artifacts.sh, and the
    assembled files for direct runs), and an install prefix with a stub CPython and a stub
    elan/Lean/Lake. Every run's PATH starts with a lake and a curl that only record."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.repo = tmp / "repo"
        self.opt = tmp / "opt"
        self.home = tmp / "home"
        self.bin = tmp / "bin"
        self.calls = tmp / "lake_calls"
        self.src = tmp / "art-src"
        self.art = tmp / "art"
        self.home.mkdir()
        for rel in ("scripts/cloud/setup_env.sh", "scripts/fetch_artifacts.sh",
                    "scripts/setup_lean.sh", "scripts/setup_lean_repl.sh"):
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, self.repo / rel)
        for f in ("pyproject.toml", "requirements.lock"):
            shutil.copy2(ROOT / f, self.repo / f)

        srcs = tmp / "sources"
        self.urls = {"mathlib": "https://example.invalid/mathlib4",
                     "batteries": "https://example.invalid/batteries"}
        self.revs = {
            "mathlib": _git_checkout(srcs / "packages" / "mathlib", {
                "lakefile.lean": "-- stub\n", "Mathlib.lean": "import Mathlib.A\n",
                "Mathlib/A.lean": "-- a\n", "Mathlib/B/C.lean": "-- c\n"}, self.urls["mathlib"]),
            "batteries": _git_checkout(srcs / "packages" / "batteries",
                                       {"Batteries.lean": "-- b\n"}, self.urls["batteries"]),
        }
        self.repl_rev = _git_checkout(srcs / "repl", {"lean-toolchain": SHIFTED_TOOLCHAIN + "\n",
                                                      "REPL.lean": "-- repl\n"}, FAKE_REPL_URL)
        self.rev7 = self.revs["mathlib"][:7]

        lean = self.repo / "lean"
        (lean / "MathverifyLean").mkdir(parents=True)
        pins = (f'LEAN_TOOLCHAIN="{TOOLCHAIN}"\nMATHLIB_REV="{self.revs["mathlib"]}"\n'
                f'REPL_URL="{FAKE_REPL_URL}"\nREPL_REV="{self.repl_rev}"\nELAN_VERSION="4.2.4"\n')
        packages = [{"url": self.urls[n], "type": "git", "subDir": None, "scope": "stub",
                     "rev": self.revs[n], "name": n, "manifestFile": "lake-manifest.json",
                     "inputRev": "main", "inherited": n != "mathlib", "configFile": "lakefile.lean"}
                    for n in ("mathlib", "batteries")]
        manifest = {"version": "1.2.0", "packagesDir": ".lake/packages", "packages": packages,
                    "name": "mathverify-lean", "lakeDir": ".lake"}
        for name, text in {"PINS": pins, "lean-toolchain": TOOLCHAIN + "\n",
                           "lake-manifest.json": json.dumps(manifest, indent=1) + "\n",
                           "lakefile.toml": 'name = "mathverify-lean"\n',
                           "MathverifyLean.lean": "import MathverifyLean.Basic\n",
                           "MathverifyLean/Basic.lean": "import Mathlib\n"}.items():
            (lean / name).write_text(text, encoding="utf-8", newline="\n")

        self.art.mkdir()
        with tarfile.open(self.art / f"lean-sources-{self.rev7}.tar.gz", "w:gz") as t:
            t.add(srcs / "packages", arcname="packages")
            t.add(srcs / "repl", arcname="repl")
        ltar = tmp / "ltar" / "mathlib"
        ltar.mkdir(parents=True)
        for n in ("aaaa", "bbbb"):
            (ltar / f"{n}.ltar").write_bytes(n.encode() * 1000)
        with tarfile.open(self.art / f"mathlib-cache-{self.rev7}.tar", "w") as t:
            t.add(ltar, arcname="mathlib")
        (self.src / "parts").mkdir(parents=True)
        sums = []
        for f in sorted(self.art.iterdir()):
            sums.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n")
            shutil.copy2(f, self.src / "parts" / f"{f.name}.part-000")
        for d in (self.src, self.art):
            (d / "SHA256SUMS.full").write_text("".join(sums), encoding="utf-8", newline="\n")

        _write_exec(self.opt / "python3.14" / "bin" / "python3.14", STUB_PYTHON)
        elan = self.opt / "elan"
        lake = STUB_LAKE.replace("@CALLS@", str(self.calls))
        _write_exec(elan / "bin" / "elan", STUB_ELAN)
        _write_exec(elan / "bin" / "lean", STUB_LEAN.replace("@TC@", TC_DIR_NAME))
        _write_exec(elan / "bin" / "lake", lake)
        _write_exec(elan / "toolchains" / TC_DIR_NAME / "bin" / "lean", "#!/bin/sh\nexit 0\n")
        _write_exec(self.bin / "lake", lake)
        _write_exec(self.bin / "curl", f'#!/bin/sh\necho "curl $*" >> "{self.calls}"\nexit 7\n')
        _write_exec(self.bin / "df", STUB_DF.replace("@CALLS@", str(self.df_calls)))
        _write_exec(self.bin / "du", STUB_DU)
        _write_exec(self.bin / "uname", STUB_UNAME)
        self.markers = tmp / "binfmt_misc"  # WSL's interop marker goes here (none by default)
        self.markers.mkdir()

    @property
    def df_calls(self) -> Path:
        return self.tmp / "df_calls"

    def env(self, **extra: str | None) -> dict[str, str]:
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home), "TMPDIR": str(self.tmp),
               "LC_ALL": "C", "GIT_CONFIG_GLOBAL": os.devnull,
               "GIT_CONFIG_SYSTEM": str(self.tmp / "gitconfig-system"),
               "MATHVERIFY_OPT": str(self.opt), "CLAUDE_PROJECT_DIR": str(self.repo),
               "MATHVERIFY_PROFILE_D": str(self.tmp / "profile.d"),
               "MATHVERIFY_ARTIFACT_SRC": str(self.src),
               "MATHVERIFY_WSL_MARKER_DIR": str(self.markers), **extra}
        return {k: v for k, v in env.items() if v is not None}

    def _run(self, script: Path, args: tuple[str, ...], env: dict[str, str]):
        t = time.monotonic()
        r = subprocess.run([BASH, str(script), *args], env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=600, cwd=self.tmp)
        return r, time.monotonic() - t

    def setup_env(self, *args: str, **extra: str | None):
        return self._run(self.repo / "scripts" / "cloud" / "setup_env.sh", args, self.env(**extra))

    def script(self, name: str, **extra: str | None):
        """scripts/<name> run directly, offline mode, on the prefix and the assembled artifacts."""
        env = self.env(**{"ELAN_HOME": str(self.opt / "elan"),
                          "MATHVERIFY_LEAN_PROJECT": str(self.opt / "mathverify-lean"),
                          "MATHVERIFY_LEAN_REPL": str(self.opt / "repl" / ".lake" / "build" / "bin" / "repl"),
                          "MATHVERIFY_ARTIFACT_DIR": str(self.art), "MATHVERIFY_LEAN_OFFLINE": "1", **extra})
        return self._run(self.repo / "scripts" / name, (), env)

    def status(self) -> str:
        return (self.opt / "mathverify-logs" / "setup_env.status").read_text().strip()

    def lake_calls(self) -> list[list[str]]:
        if not self.calls.exists():
            return []
        return [ln.split("\t") for ln in self.calls.read_text().splitlines()]

    def fingerprint(self) -> str:
        script = f'REPO="{self.repo}"\n{_function(SETUP_ENV, "lean_fingerprint")}\nlean_fingerprint\n'
        r = subprocess.run([BASH, "-c", script], capture_output=True, text=True, timeout=60)
        return r.stdout.strip()

    def change_pins(self) -> Path:
        basic = self.repo / "lean" / "MathverifyLean" / "Basic.lean"
        basic.write_text(basic.read_text() + "-- the pins moved on\n", encoding="utf-8", newline="\n")
        return basic


@pytest.fixture
def lean_bed(tmp_path):
    if BASH is None or shutil.which("git") is None:
        pytest.skip("needs bash and git")
    return LeanBed(tmp_path)


@pytest.fixture
def installed(lean_bed):
    """lean_bed after a successful `setup_env.sh --lean-only` (the call log is then cleared)."""
    r, _ = lean_bed.setup_env("--lean-only")
    assert lean_bed.status().startswith("OK mode=lean failed=[]"), r.stdout + r.stderr
    lean_bed.calls.unlink()
    return lean_bed


PROJECT_FILES = ("lakefile.toml", "lean-toolchain", "lake-manifest.json", "MathverifyLean.lean",
                 "MathverifyLean/Basic.lean")


@posix_only
def test_setup_env_installs_lean_offline_from_the_artifacts(lean_bed):
    bed = lean_bed
    r, _ = bed.setup_env("--lean-only")
    status = bed.status()
    assert re.fullmatch(r"OK mode=lean failed=\[\] stages=\[fetch_artifacts\(\d+s\) setup_lean\(\d+s\) "
                        r"setup_lean_repl\(\d+s\)\] python=3\.14\.6 lean=ready total=\d+s", status), \
        status + r.stdout
    proj = bed.opt / "mathverify-lean"
    for f in PROJECT_FILES:
        assert (proj / f).read_bytes() == (bed.repo / "lean" / f).read_bytes()
    assert (bed.opt / "mathverify-logs" / "lean.done").read_text().strip() == bed.fingerprint()
    calls = bed.lake_calls()
    assert calls and all(len(c) == 5 for c in calls), calls  # curl never ran
    # every lake run had the network cut off; the .ltar were only unpacked, from $OPT/.mathlib-ltar
    assert all(c[2] == "http://127.0.0.1:9" and c[3] == "file" for c in calls), calls
    argv = [c[1] for c in calls]
    assert argv.count("exe cache unpack") == 1 and not any("get" in a for a in argv), argv
    (unpack,) = [c for c in calls if c[1] == "exe cache unpack"]
    assert unpack[4] == str(bed.opt / ".mathlib-ltar")
    # the .ltar (only the input of `cache unpack`) and the reassembled artifacts are gone
    assert sorted(p.name for p in bed.opt.iterdir()) == [
        "elan", "mathverify-lean", "mathverify-logs", "python3.14", "repl"]
    assert not (bed.home / ".cache").exists()
    assert not list((proj / ".lake").glob(".mathverify-setup.*"))
    log = (bed.opt / "mathverify-logs" / "setup_env.log").read_text()
    assert f"removing {bed.opt}/.mathlib-ltar (2 .ltar, " in log
    assert "lean.done written" in log


@posix_only
def test_setup_env_failed_fetch_leaves_an_installed_prefix_alone(installed):
    # Round-2 finding: after a failed fetch the Lean stage still ran, rewrote project files in the
    # live install and hung >24 min in `lake exe cache get`. Now: skipped, nothing touched, seconds.
    bed = installed
    bed.change_pins()
    before = {d: _tree(bed.opt / d) for d in ("elan", "mathverify-lean", "repl", "python3.14")}
    done = (bed.opt / "mathverify-logs" / "lean.done").read_text()
    r, secs = bed.setup_env("--lean-only", MATHVERIFY_ARTIFACT_SRC=str(bed.tmp / "unreachable"))
    assert r.returncode == 0
    status = bed.status()
    assert re.fullmatch(r"FAILED mode=lean failed=\[fetch_artifacts setup_lean setup_lean_repl\] "
                        r"stages=\[fetch_artifacts\(\d+s\) setup_lean\(skipped\) setup_lean_repl\(skipped\)\] "
                        r"reason=fetch python=3\.14\.6 lean=stale total=\d+s", status), status + r.stdout
    assert {d: _tree(bed.opt / d) for d in before} == before
    assert (bed.opt / "mathverify-logs" / "lean.done").read_text() == done
    assert not bed.calls.exists()  # neither lake nor curl ran
    slog = (bed.opt / "mathverify-logs" / "setup_lean.log").read_text()
    assert "skipped: no verified artifacts (reason=fetch)" in slog
    assert _dot_entries(bed.opt) == []
    assert secs < 30, secs


@posix_only
def test_setup_env_unverified_artifacts_skip_the_stages(lean_bed):
    bed = lean_bed
    # a fetch that reports success but leaves a damaged artifact set behind
    _write_exec(bed.repo / "scripts" / "fetch_artifacts.sh", """
        #!/usr/bin/env bash
        mkdir -p "$1" && echo damaged > "$1/lean-sources.tar.gz"
        echo "$(printf 'intact' | sha256sum | cut -d' ' -f1)  lean-sources.tar.gz" > "$1/SHA256SUMS.full"
    """)
    (bed.opt / "python3.14").rename(bed.tmp / "no-python")  # the Python stage is gated too
    r, _ = bed.setup_env("--lean-only")
    status = bed.status()
    assert re.fullmatch(r"FAILED mode=lean failed=\[python setup_lean setup_lean_repl\] "
                        r"stages=\[fetch_artifacts\(\d+s\) python\(skipped\) setup_lean\(skipped\) "
                        r"setup_lean_repl\(skipped\)\] reason=artifacts python=missing lean=missing "
                        r"total=\d+s", status), status + r.stdout
    assert not (bed.opt / "mathverify-lean").exists() and not (bed.opt / "python3.14").exists()
    assert not bed.calls.exists()
    assert (bed.opt / "arac").is_dir()  # kept for a retry (fetch_artifacts.sh replaces it)


@posix_only
def test_setup_env_offline_mode_refuses_what_a_verified_set_lacks(lean_bed):
    # The set verifies (every listed file matches) but has no .ltar cache: setup_lean.sh must
    # refuse `lake exe cache get` instead of falling back to cache.mathlib.org.
    bed = lean_bed
    name = f"mathlib-cache-{bed.rev7}.tar"
    (bed.src / "parts" / f"{name}.part-000").unlink()
    sums = bed.src / "SHA256SUMS.full"
    sums.write_text("".join(ln + "\n" for ln in sums.read_text().splitlines() if not ln.endswith(name)))
    r, secs = bed.setup_env("--lean-only")
    assert bed.status().startswith("FAILED mode=lean failed=[setup_lean] "), bed.status() + r.stdout
    slog = (bed.opt / "mathverify-logs" / "setup_lean.log").read_text()
    assert f"offline mode (MATHVERIFY_LEAN_OFFLINE=1): {bed.opt}/arac/{name} (Mathlib .ltar cache) is missing" in slog
    assert not bed.calls.exists() and not (bed.opt / "mathverify-lean").exists()
    assert secs < 30, secs


@posix_only
@pytest.mark.parametrize("failure", ["smoke", "smoke-after-swap"])
def test_setup_env_update_is_staged_and_a_failed_one_keeps_the_old_project(installed, failure):
    bed = installed
    proj = bed.opt / "mathverify-lean"
    basic = bed.change_pins()
    before = _tree(proj)
    done = (bed.opt / "mathverify-logs" / "lean.done").read_text()
    # "smoke-after-swap": the staged project passes its smoke test and fails the same test once it
    # is renamed to its final place.
    fail = ({"STUB_LEAN_SMOKE": "fail"} if failure == "smoke"
            else {"STUB_LEAN_SMOKE_FAIL_IN": str(proj)})
    r, _ = bed.setup_env("--lean-only", **fail)
    assert bed.status().startswith("FAILED mode=lean failed=[setup_lean] "), bed.status() + r.stdout
    # The new project was built next to the live one and discarded; the live one is as it was.
    assert _tree(proj) == before
    assert (bed.opt / "mathverify-logs" / "lean.done").read_text() == done
    calls = bed.lake_calls()
    cwds = [Path(c[0]) for c in calls]
    log = (bed.opt / "mathverify-logs" / "setup_lean.log").read_text()
    assert f"{proj} differs from the pins: building the new project in" in log
    if failure == "smoke":
        assert cwds and all(c.name.startswith(".mathverify-lean.stage.") for c in cwds), cwds
    else:
        # smoke passed in the staging directory, swapped in, the same smoke failed there, swapped back
        smokes = [c for c in calls if c[1].startswith("env lean ")]
        assert [Path(c[0]).name.startswith(".mathverify-lean.stage.") for c in smokes] == [True, False]
        assert smokes[1][1] == smokes[0][1] and Path(smokes[1][0]) == proj and calls[-1] == smokes[1]
        assert all(c.name.startswith(".mathverify-lean.stage.") for c in cwds[:-1])
        assert f"smoke test failed in {proj} after the swap; the previous project was put back" in log
    assert _dot_entries(bed.opt) == []
    # The same update without the failure swaps the new project in, then deletes the old one.
    bed.calls.unlink()
    r, _ = bed.setup_env("--lean-only")
    assert bed.status().startswith("OK mode=lean failed=[]"), bed.status() + r.stdout
    assert (proj / "MathverifyLean" / "Basic.lean").read_bytes() == basic.read_bytes()
    assert (bed.opt / "mathverify-logs" / "lean.done").read_text().strip() == bed.fingerprint()
    smokes = [c for c in bed.lake_calls() if c[1].startswith("env lean ")]
    assert [Path(c[0]) == proj for c in smokes] == [False, True], smokes  # staged, then in place
    in_proj = [c[1] for c in bed.lake_calls() if Path(c[0]) == proj]
    assert in_proj[0].startswith("env lean "), in_proj  # the smoke test first (then the REPL smoke)
    log = (bed.opt / "mathverify-logs" / "setup_lean.log").read_text()
    assert f"SMOKE OK in {proj}" in log
    assert _dot_entries(bed.opt) == [] and not list((proj / ".lake").glob(".mathverify-setup.*"))


@posix_only
@pytest.mark.parametrize("case", ["fresh", "fresh-without-toolchain", "staged", "staged-large-old",
                                  "in-place"])
def test_setup_lean_checks_the_disk_before_writing(lean_bed, case):
    bed = lean_bed
    extra: dict[str, str] = {}
    if case.startswith("staged") or case == "in-place":
        r, _ = bed.setup_env("--lean-only")
        assert bed.status().startswith("OK mode=lean failed=[]"), r.stdout
        bed.calls.unlink()
        if case != "in-place":
            bed.change_pins()
    staged = f"{bed.opt}/mathverify-lean differs from the pins and is left untouched"
    # (GB this run must write next to the project, GB free given to it, what the refusal names)
    if case == "fresh":
        # a measured new build (7.2 GB project + 0.45 GB .ltar)
        size, avail, left = 7.7, 8.5, "nothing was installed"
    elif case == "fresh-without-toolchain":
        # plus the toolchain (3.0 GB measured), not installed yet and on the same filesystem;
        # checked before elan is even downloaded (online mode here: curl would run next)
        extra = {"ELAN_HOME": str(bed.tmp / "no-elan"), "MATHVERIFY_LEAN_OFFLINE": "0"}
        size, avail, left = 10.7, 11.5, "nothing was installed"
    elif case == "staged":
        # the old project is small: a new build's measured size counts
        size, avail, left = 7.7, 8.5, staged
    elif case == "staged-large-old":
        extra = {"STUB_DU_KB": str(20 * GB)}
        size, avail, left = 20.0, 20.5, staged
    else:
        # the pinned project is there: only what a new build would add to it counts
        extra = {"STUB_DU_KB": str(int(7.5 * GB))}
        size, avail, left = 0.2, 1.1, "nothing was installed"
    need = size + 1.0  # the margin
    before = _tree(bed.opt)
    r, secs = bed.script("setup_lean.sh", STUB_DF_AVAIL_KB=str(int(avail * GB)), **extra)
    assert r.returncode == 1, r.stdout + r.stderr
    assert (f"ERROR: not enough disk on {bed.opt}: ~{need:.1f} GB needed ({size:.1f} GB + 1.0 GB margin), "
            f"{avail:.1f} GB free; {left}") in r.stderr, r.stderr
    assert _tree(bed.opt) == before
    assert not bed.calls.exists() and not (bed.tmp / "no-elan").exists()
    assert bed.df_calls.read_text().splitlines()[-1] == str(bed.opt)
    assert secs < 30, secs
    # 0.2 GB more than needed is enough
    r, _ = bed.script("setup_lean.sh", STUB_DF_AVAIL_KB=str(int((need + 0.2) * GB)), **extra)
    if case == "fresh-without-toolchain":
        # past the check, the online elan download is the next step (the stub curl exits 7)
        assert r.returncode == 7 and "not enough disk" not in r.stderr, r.stdout + r.stderr
        assert bed.calls.read_text().startswith("curl ")
    else:
        assert r.returncode == 0, r.stdout + r.stderr
        assert "SMOKE OK" in r.stdout and _dot_entries(bed.opt) == []


@posix_only
@pytest.mark.parametrize("case", ["in-place", "staged"])
def test_setup_lean_sizes_stages_and_swaps_a_linked_project_at_its_target(installed, case):
    # session_start.sh links ~/mathverify-lean to <prefix>/mathverify-lean. Round-4 finding:
    # `du -sk` of the link measured 0 KiB; the staging directory would sit next to the link and
    # the swap would replace the link with a new directory, leaving the install it points to old.
    bed = installed
    proj = bed.opt / "mathverify-lean"
    link = bed.home / "mathverify-lean"
    link.symlink_to(proj)
    if case == "in-place":
        # 7.5 GB already there: 0.2 GB left to add (the link measured 0 KiB: 7.7 GB)
        extra = {"STUB_DU_KB": str(int(7.5 * GB))}
        size, avail = 0.2, 1.1
    else:
        basic = bed.change_pins()
        # the old project holds 20 GB, so the staged copy may need as much (the link: 7.7 GB)
        extra = {"STUB_DU_KB": str(20 * GB)}
        size, avail = 20.0, 20.5
    extra["MATHVERIFY_LEAN_PROJECT"] = str(link)
    need = size + 1.0
    before = _tree(bed.opt)
    r, _ = bed.script("setup_lean.sh", STUB_DF_AVAIL_KB=str(int(avail * GB)), **extra)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"PROJECT={proj} (given as {link})" in r.stdout
    assert (f"ERROR: not enough disk on {bed.opt}: ~{need:.1f} GB needed ({size:.1f} GB + 1.0 GB "
            f"margin), {avail:.1f} GB free; ") in r.stderr, r.stderr
    assert _tree(bed.opt) == before and not bed.calls.exists()
    r, _ = bed.script("setup_lean.sh", STUB_DF_AVAIL_KB=str(int((need + 0.2) * GB)), **extra)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"disk: {need + 0.2:.1f} GB free on {bed.opt}, {need:.1f} GB needed" in r.stdout
    assert bed.df_calls.read_text().splitlines()[-1] == str(bed.opt)
    assert "SMOKE OK" in r.stdout
    # the link is still the link, and the install it points to is the one that was completed
    assert os.readlink(link) == str(proj)
    assert _dot_entries(bed.home) == [] and _dot_entries(bed.opt) == []
    if case == "in-place":
        assert f"{proj} already has the pinned project files" in r.stdout
    else:
        assert f"building the new project in {bed.opt}/.mathverify-lean.stage." in r.stdout
        assert (proj / "MathverifyLean" / "Basic.lean").read_bytes() == basic.read_bytes()
        assert f"SMOKE OK in {proj}" in r.stdout


# ---- setup_lean.sh inside WSL: the Windows drive under the distribution's virtual disk ----------

# `reg.exe query HKCU\Software\Microsoft\Windows\CurrentVersion\Lxss /s` in the shape measured in
# WSL Ubuntu on 2026-09-24 (CRLF line ends, four-space separators), with two distributions: Debian
# on E:, and Ubuntu on D: with its BasePath before its name and in the \\?\ form.
REG_LXSS = "\r\n".join([
    "",
    r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Lxss",
    "    DefaultDistribution    REG_SZ    {1111}",
    "    DefaultVersion    REG_DWORD    0x2",
    "",
    r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Lxss\{1111}",
    "    State    REG_DWORD    0x1",
    "    DistributionName    REG_SZ    Debian",
    r"    BasePath    REG_SZ    E:\WSL\Debian",
    "",
    r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Lxss\{2222}",
    r"    BasePath    REG_SZ    \\?\D:\WSL images\Ubuntu",
    "    DistributionName    REG_SZ    Ubuntu",
    "    VhdFileName    REG_SZ    ext4.vhdx",
    "",
])
REG_QUERY = r"reg.exe query HKCU\Software\Microsoft\Windows\CurrentVersion\Lxss /s"
# Stand-ins for WSL interop, each recording its argv: reg.exe prints $STUB_REG_OUT, cmd.exe echoes
# $STUB_LOCALAPPDATA (CRLF, as the real one), wslpath -u 'X:\' answers <tmp>/mnt/x/.
STUB_REG = r"""
    #!/bin/sh
    printf '%s\n' "reg.exe $*" >> "@CALLS@"
    [ -n "${STUB_REG_OUT:-}" ] || exit 1
    cat "$STUB_REG_OUT"
"""
STUB_CMD = r"""
    #!/bin/sh
    printf '%s\n' "cmd.exe $*" >> "@CALLS@"
    [ -n "${STUB_LOCALAPPDATA:-}" ] || exit 1
    printf '%s\r\n' "$STUB_LOCALAPPDATA"
"""
STUB_WSLPATH = r"""
    #!/bin/sh
    printf '%s\n' "wslpath $*" >> "@CALLS@"
    [ "$1" = -u ] || exit 1
    echo "@MNT@/$(printf '%s' "$2" | cut -c1 | tr 'A-Z' 'a-z')/"
"""


class WinTools:
    """reg.exe, cmd.exe and wslpath stubs in their own PATH directory, and a df map file."""

    def __init__(self, bed: LeanBed):
        self.bed = bed
        self.bin = bed.tmp / "winbin"
        self.calls_file = bed.tmp / "win_calls"
        self.mnt = bed.tmp / "mnt"
        self.reg_out = bed.tmp / "reg_out"
        self.reg_out.write_bytes(REG_LXSS.encode())
        for name, text in (("reg.exe", STUB_REG), ("cmd.exe", STUB_CMD), ("wslpath", STUB_WSLPATH)):
            _write_exec(self.bin / name, text.replace("@CALLS@", str(self.calls_file))
                        .replace("@MNT@", str(self.mnt)))

    def path(self) -> str:
        return f"{self.bin}:{self.bed.bin}:/usr/bin:/bin"

    def calls(self) -> list[str]:
        return self.calls_file.read_text().splitlines() if self.calls_file.exists() else []

    def df_map(self, rows: list[tuple[str, str, float]]) -> str:
        """STUB_DF_MAP for (directory, filesystem, GB free) rows."""
        f = self.bed.tmp / "df_map"
        f.write_text("".join(f"{d.rstrip('/')}\t{fs}\t{int(gb * GB)}\n" for d, fs, gb in rows))
        return str(f)


@posix_only
@pytest.mark.parametrize("found", ["registry", "localappdata", "fallback", "override"])
def test_setup_lean_under_wsl_checks_the_windows_drive(lean_bed, found):
    # Round-4 finding: inside WSL df sees the ext4 virtual disk (941 GB free) while the Windows
    # drive holding its ext4.vhdx had 6.2 GB (measured 2026-09-24); that drive filled up.
    bed = lean_bed
    win = WinTools(bed)
    extra = {"PATH": win.path(), "WSL_DISTRO_NAME": "Ubuntu", "STUB_REG_OUT": str(win.reg_out)}
    if found == "registry":
        (bed.markers / "WSLInterop").touch()
        # wslpath's answer "<mnt>/d/" (with the slash, as the real one) is used without it
        drive, drive_dir = "D:", f"{win.mnt}/d"
        how = r"registry: BasePath of distribution Ubuntu = \\?\D:\WSL images\Ubuntu"
        calls = [REG_QUERY, "wslpath -u D:\\"]
    elif found == "localappdata":
        # only the kernel says WSL; the registry has no distribution of this name
        extra.update(STUB_UNAME_R="5.15.167.4-microsoft-standard-WSL2", WSL_DISTRO_NAME="Ubuntu-24.04",
                     STUB_LOCALAPPDATA=r"E:\Users\u\AppData\Local")
        drive, drive_dir = "E:", f"{win.mnt}/e"
        how = (r"no registry BasePath for distribution Ubuntu-24.04; %LOCALAPPDATA% = "
               r"E:\Users\u\AppData\Local (a distribution's default location)")
        calls = [REG_QUERY, "cmd.exe /d /c echo %LOCALAPPDATA%", "wslpath -u E:\\"]
    elif found == "fallback":
        # no interop (none of reg.exe, cmd.exe, wslpath on PATH); newer WSL's marker name
        (bed.markers / "WSLInterop-late").touch()
        extra["PATH"] = f"{bed.bin}:/usr/bin:/bin"
        drive, drive_dir = "C:", "/mnt/c"
        how = "fallback: neither the registry nor %LOCALAPPDATA% named a drive"
        calls = []
    else:
        (bed.markers / "WSLInterop").touch()
        drive, drive_dir = "", str(bed.tmp / "windrive")
        extra["MATHVERIFY_WSL_DRIVE_DIR"] = drive_dir
        how = "MATHVERIFY_WSL_DRIVE_DIR"
        calls = []
    place = (f"the Windows drive {drive + ' ' if drive else ''}({drive_dir}), which holds this WSL "
             f"distribution's virtual disk")
    before = _tree(bed.opt)
    r, secs = bed.script("setup_lean.sh", STUB_DF_MAP=win.df_map([(drive_dir, f"{drive or 'X:'}\\", 6.2)]),
                         **extra)
    assert r.returncode == 1, r.stdout + r.stderr
    # the virtual disk has room (100 GB); the drive under it has not
    assert f"disk: 100.0 GB free on {bed.opt}, 8.7 GB needed" in r.stdout, r.stdout
    assert f"WSL: {place} ({how})" in r.stdout, r.stdout
    assert (f"ERROR: not enough disk on {place}: ~8.7 GB needed (7.7 GB + 1.0 GB margin), "
            f"6.2 GB free; nothing was installed") in r.stderr, r.stderr
    assert _tree(bed.opt) == before and not bed.calls.exists()
    assert bed.df_calls.read_text().splitlines()[-1] == drive_dir
    assert win.calls() == calls
    assert secs < 30, secs
    r, _ = bed.script("setup_lean.sh", STUB_DF_MAP=win.df_map([(drive_dir, f"{drive or 'X:'}\\", 8.9)]),
                      **extra)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"disk: 8.9 GB free on {place}, 8.7 GB needed" in r.stdout
    assert "SMOKE OK" in r.stdout and _dot_entries(bed.opt) == []


@posix_only
@pytest.mark.parametrize("layout", ["all-on-the-virtual-disk", "project-on-that-drive",
                                    "project-on-another-drive"])
def test_setup_lean_under_wsl_counts_what_lands_on_the_windows_drive(lean_bed, layout):
    bed = lean_bed
    win = WinTools(bed)
    (bed.markers / "WSLInterop").touch()
    drive_dir = str(win.mnt / "c")
    rows = [(drive_dir, "C:\\", 6.2)]
    extra = {"MATHVERIFY_WSL_DRIVE_DIR": drive_dir}
    place = f"the Windows drive ({drive_dir}), which holds this WSL distribution's virtual disk"
    if layout == "all-on-the-virtual-disk":
        # the toolchain is not installed either: both go into the disk image, summed
        extra.update(ELAN_HOME=str(bed.tmp / "no-elan"), MATHVERIFY_LEAN_OFFLINE="0")
        size = 10.7
    elif layout == "project-on-that-drive":
        # the project directory is on the drive itself (df names it "C:\" like the drive)
        rows.insert(0, (str(bed.opt), "C:\\", 100.0))
        size = 7.7
    else:
        # on another Windows drive: what is written there does not grow the disk image
        rows.insert(0, (str(bed.opt), "F:\\", 100.0))
        size = 0.0
    r, _ = bed.script("setup_lean.sh", STUB_DF_MAP=win.df_map(rows), **extra)
    if size == 0.0:
        assert r.returncode == 0, r.stdout + r.stderr
        assert f"WSL: nothing this run writes lands on a virtual disk or on {drive_dir}" in r.stdout
        assert drive_dir in bed.df_calls.read_text().splitlines()  # its filesystem was compared
        assert "SMOKE OK" in r.stdout
        return
    assert r.returncode == 1, r.stdout + r.stderr
    assert (f"ERROR: not enough disk on {place}: ~{size + 1:.1f} GB needed ({size:.1f} GB + 1.0 GB "
            f"margin), 6.2 GB free; nothing was installed") in r.stderr, r.stderr
    assert not bed.calls.exists() and not (bed.tmp / "no-elan").exists()


@posix_only
@pytest.mark.parametrize("drive", ["unmounted", "unreadable"])
def test_setup_lean_under_wsl_refuses_a_windows_drive_it_cannot_read(lean_bed, drive):
    # No interop, so the fallback /mnt/c. Unmounted, /mnt/c is a plain directory of the virtual disk
    # (df names /dev/sdd there, with its ~1 TB free: the number the check exists to look past);
    # unreadable, df fails. Either way the run stops before writing, even with 900 GB "free".
    bed = lean_bed
    win = WinTools(bed)
    (bed.markers / "WSLInterop").touch()
    fs = "/dev/sdd" if drive == "unmounted" else "-"
    before = _tree(bed.opt)
    r, secs = bed.script("setup_lean.sh", PATH=f"{bed.bin}:/usr/bin:/bin", WSL_DISTRO_NAME="Ubuntu",
                         STUB_DF_MAP=win.df_map([("/mnt/c", fs, 900.0)]))
    assert r.returncode == 1, r.stdout + r.stderr
    place = "the Windows drive C: (/mnt/c), which holds this WSL distribution's virtual disk"
    why = (": df names /dev/sdd for /mnt/c, a disk inside WSL, not a Windows drive (is the drive "
           "mounted?)" if drive == "unmounted" else " (df -Pk /mnt/c)")
    assert (f"ERROR: cannot read the free disk space of {place}{why}; set MATHVERIFY_WSL_DRIVE_DIR to "
            f"a directory on the Windows drive that holds the virtual disk (ext4.vhdx); nothing was "
            f"installed") in r.stderr, r.stderr
    assert "not enough disk" not in r.stderr
    assert _tree(bed.opt) == before and not bed.calls.exists()
    assert bed.df_calls.read_text().splitlines()[-1] == "/mnt/c"
    assert secs < 30, secs


@posix_only
def test_setup_lean_outside_wsl_never_asks_windows(lean_bed):
    # Interop stand-ins on PATH and WSL_DISTRO_NAME set, but neither WSL marker (no WSLInterop,
    # a kernel without "microsoft"): the Windows drive is never looked up or checked.
    bed = lean_bed
    win = WinTools(bed)
    r, _ = bed.script("setup_lean.sh", PATH=win.path(), WSL_DISTRO_NAME="Ubuntu",
                      STUB_REG_OUT=str(win.reg_out), STUB_LOCALAPPDATA=r"C:\Users\u\AppData\Local",
                      STUB_DF_MAP=win.df_map([(f"{win.mnt}/d", "D:\\", 0.1), (f"{win.mnt}/c", "C:\\", 0.1)]))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WSL: " not in r.stdout and "SMOKE OK" in r.stdout
    assert win.calls() == []
    assert bed.df_calls.read_text().splitlines() == [str(bed.opt)]


@posix_only
@pytest.mark.parametrize("missing", ["artifact-dir", "mathlib-cache", "elan"])
def test_setup_lean_offline_refuses_before_writing(installed, missing):
    bed = installed
    bed.change_pins()  # the project would be rebuilt: nothing may be written before the refusal
    before = _tree(bed.opt)
    extra: dict[str, str | None] = {}
    if missing == "artifact-dir":
        extra["MATHVERIFY_ARTIFACT_DIR"] = None
        expect = "MATHVERIFY_ARTIFACT_DIR is not set"
    elif missing == "mathlib-cache":
        partial = bed.tmp / "art-partial"
        shutil.copytree(bed.art, partial)
        (partial / f"mathlib-cache-{bed.rev7}.tar").unlink()
        extra["MATHVERIFY_ARTIFACT_DIR"] = str(partial)
        expect = f"{partial}/mathlib-cache-{bed.rev7}.tar (Mathlib .ltar cache) is missing"
    else:
        extra["ELAN_HOME"] = str(bed.tmp / "no-elan")  # neither elan nor the toolchain installed
        expect = "(elan 4.2.4) is missing"
    r, secs = bed.script("setup_lean.sh", **extra)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "ERROR: offline mode (MATHVERIFY_LEAN_OFFLINE=1): " in r.stderr
    assert expect in r.stderr and "refusing the online fallback" in r.stderr, r.stderr
    assert _tree(bed.opt) == before
    assert not bed.calls.exists() and not (bed.tmp / "no-elan").exists()
    assert secs < 30, secs


@posix_only
def test_setup_lean_alone_uses_a_temporary_ltar_cache(lean_bed):
    bed = lean_bed
    r, _ = bed.script("setup_lean.sh")  # no MATHLIB_CACHE_DIR: a private one, removed on exit
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fresh install in" in r.stdout and "SMOKE OK" in r.stdout
    (unpack,) = [c for c in bed.lake_calls() if c[1] == "exe cache unpack"]
    assert re.fullmatch(rf"{re.escape(str(bed.opt))}/\.mathverify-lean\.ltar\.\d+", unpack[4]), unpack
    assert not Path(unpack[4]).exists()
    assert not (bed.home / ".cache").exists()
    assert _dot_entries(bed.opt) == []


@posix_only
def test_setup_lean_repl_offline_refuses_a_clone(installed):
    bed = installed
    shutil.rmtree(bed.opt / "repl")
    r, secs = bed.script("setup_lean_repl.sh", MATHVERIFY_ARTIFACT_DIR=str(bed.tmp / "no-artifacts"))
    assert r.returncode == 1
    assert "ERROR: offline mode (MATHVERIFY_LEAN_OFFLINE=1): " in r.stderr
    assert f"lean-sources-{bed.rev7}.tar.gz is missing" in r.stderr, r.stderr
    assert not (bed.opt / "repl").exists() and not bed.calls.exists()
    assert secs < 30, secs


@posix_only
def test_setup_lean_repl_swaps_a_new_checkout_in_only_after_its_smoke_test(installed):
    bed = installed
    repl = bed.opt / "repl"
    # the installed checkout is at another revision (made from older pins, say)
    (repl / "Extra.lean").write_text("-- another revision\n", encoding="utf-8")
    _git(repl, "add", "Extra.lean")
    _git(repl, "commit", "-q", "-m", "another revision")
    other = _git(repl, "rev-parse", "HEAD")
    before = _tree(repl)
    r, _ = bed.script("setup_lean_repl.sh", STUB_REPL_SMOKE="fail")
    assert r.returncode == 1 and "REPL reported an error" in r.stderr, r.stdout + r.stderr
    assert "the previous checkout was put back" in r.stdout
    assert _git(repl, "rev-parse", "HEAD") == other and _tree(repl) == before
    assert _dot_entries(bed.opt) == []
    r, _ = bed.script("setup_lean_repl.sh")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _git(repl, "rev-parse", "HEAD") == bed.repl_rev
    assert (repl / "lean-toolchain").read_text().strip() == TOOLCHAIN
    assert (repl / ".lake" / "build" / "bin" / "repl").is_file()
    assert _dot_entries(bed.opt) == []


@posix_only
@pytest.mark.parametrize("case", ["other-revision", "dangling"])
def test_setup_lean_repl_updates_a_linked_checkout_at_its_target(installed, case):
    # session_start.sh links ~/repl to <prefix>/repl. Round-6 finding: setup_lean_repl.sh never
    # resolved that link, so it staged the new checkout next to the link and swapped the link
    # itself: the link became a new directory and the checkout it pointed to stayed old.
    bed = installed
    repl = bed.opt / "repl"
    target = Path(os.path.realpath(repl))  # what `readlink -m` logs, were the bed under a link
    link = bed.home / "repl"
    link.symlink_to(repl)
    extra = {"MATHVERIFY_LEAN_REPL": str(link / ".lake" / "build" / "bin" / "repl")}
    if case == "other-revision":
        (repl / "Extra.lean").write_text("-- another revision\n", encoding="utf-8")
        _git(repl, "add", "Extra.lean")
        _git(repl, "commit", "-q", "-m", "another revision")
        other = _git(repl, "rev-parse", "HEAD")
        before = _tree(repl)
        # a failed smoke test puts the previous checkout back at the target, the link untouched
        r, _ = bed.script("setup_lean_repl.sh", STUB_REPL_SMOKE="fail", **extra)
        assert r.returncode == 1 and "REPL reported an error" in r.stderr, r.stdout + r.stderr
        assert f"the previous checkout was put back in {target}" in r.stdout, r.stdout
        assert link.is_symlink() and os.readlink(link) == str(repl)
        assert _git(repl, "rev-parse", "HEAD") == other and _tree(repl) == before
        assert _dot_entries(bed.home) == [] and _dot_entries(bed.opt) == []
        bed.calls.unlink()
    else:
        shutil.rmtree(repl)  # the link dangles: the checkout is created at its target
    r, _ = bed.script("setup_lean_repl.sh", **extra)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"REPL={target} (given as {link})" in r.stdout, r.stdout
    assert f"swap the new checkout into {target}" in r.stdout and "REPL SMOKE OK" in r.stdout
    # built in a staging checkout next to the target, not next to the link ...
    (build,) = [c for c in bed.lake_calls() if c[1] == "build"]
    assert re.fullmatch(rf"{re.escape(str(target.parent))}/\.repl\.stage\.\d+/repl", build[0]), build
    # ... and smoke-tested through the link, the path the verifier launches
    (smoke,) = [c for c in bed.lake_calls() if c[1].startswith("env ")]
    assert smoke[1] == f"env {link}/.lake/build/bin/repl", smoke
    assert link.is_symlink() and os.readlink(link) == str(repl)
    assert _git(repl, "rev-parse", "HEAD") == bed.repl_rev
    assert (repl / "lean-toolchain").read_text().strip() == TOOLCHAIN
    assert (repl / ".lake" / "build" / "bin" / "repl").is_file()
    assert _dot_entries(bed.home) == [] and _dot_entries(bed.opt) == []


# ---- fetch_artifacts.sh over git smart HTTP: the MATHVERIFY_GITHUB_TOKEN retry ------------------
# The claude.ai setup script runs before Claude Code connects to the session's GitHub proxy; the
# private repository answered it 401 ("could not read Username"; 24 Sep 2026). These tests serve
# the artifact ref with `git http-backend` behind the same 401 and check that the token is sent
# only after the plain fetch failed, only to its own URL prefix, and is never printed, written or
# put on a command line.

TOKEN = "github_pat_TEST_0123456789_abcdefghij_TOKEN"
OWNER = "sahip"


class _GitServer(http.server.ThreadingHTTPServer):
    """git smart HTTP on 127.0.0.1. With `auth` set, a request without exactly that Authorization
    header gets 401. `seen` records every request's Authorization and marker headers."""
    daemon_threads = True

    def __init__(self, root: Path, auth: str | None):
        super().__init__(("127.0.0.1", 0), _GitHandler)
        self.root, self.auth, self.seen = root, auth, []


class _GitHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _body(self) -> bytes:
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            out = b""
            while (size := int(self.rfile.readline().split(b";")[0], 16)) > 0:
                out += self.rfile.read(size)
                self.rfile.readline()
            self.rfile.readline()
            return out
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def _serve(self):
        body = self._body() if self.command == "POST" else b""
        self.server.seen.append({"path": self.path,
                                 "auth": self.headers.get_all("Authorization") or [],
                                 "marker": self.headers.get_all("X-Mathverify-Test") or []})
        if self.server.auth is not None and self.headers.get("Authorization") != self.server.auth:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="test"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        path, _, query = self.path.partition("?")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.server.root),
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_PROJECT_ROOT": str(self.server.root),
               "GIT_HTTP_EXPORT_ALL": "1", "PATH_INFO": path, "QUERY_STRING": query,
               "REQUEST_METHOD": self.command, "REMOTE_ADDR": "127.0.0.1",
               "CONTENT_TYPE": self.headers.get("Content-Type", ""),
               "CONTENT_LENGTH": str(len(body)),
               "HTTP_CONTENT_ENCODING": self.headers.get("Content-Encoding", ""),
               "GIT_PROTOCOL": self.headers.get("Git-Protocol", "")}
        out = subprocess.run(["git", "http-backend"], input=body, env=env, capture_output=True,
                             timeout=60).stdout
        sep = b"\r\n\r\n" if b"\r\n\r\n" in out else b"\n\n"
        head, _, payload = out.partition(sep)
        status, headers = 200, []
        for line in head.decode("latin-1").splitlines():
            name, _, value = line.partition(":")
            if name.lower() == "status":
                status = int(value.split()[0])
            elif name and name.lower() != "content-length":
                headers.append((name, value.strip()))
        self.send_response(status)
        for name, value in headers:
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = _serve


def _basic(user: str, secret: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{secret}".encode()).decode()


class TokenBed:
    """The artifact set of the `artifacts` fixture on ref refs/arac/test of a bare repository
    served over HTTP, a checkout whose origin points at it, and a `git` wrapper on PATH that
    records every git command line."""

    REF = "refs/arac/test"

    def __init__(self, tmp_path: Path, src: Path):
        self.tmp = tmp_path
        srv = tmp_path / "srv"
        bare = srv / OWNER / "asd"
        bare.mkdir(parents=True)
        _git(bare, "init", "-q", "--bare")
        work = tmp_path / "artifact-tree"
        shutil.copytree(src, work)
        _git(work, "init", "-q")
        _git(work, "add", "-A")
        _git(work, "commit", "-q", "-m", "artifacts")
        _git(work, "push", "-q", str(bare), f"HEAD:{self.REF}")
        self.srv = srv
        self.checkout = tmp_path / "checkout"
        (self.checkout / "scripts").mkdir(parents=True)
        shutil.copy2(FETCH, self.checkout / "scripts" / "fetch_artifacts.sh")
        _git(self.checkout, "init", "-q")
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.argv_log = tmp_path / "git-argv.log"
        self.bin = tmp_path / "bin"
        _write_exec(self.bin / "git", f"""
            #!/bin/bash
            printf '%s\\n' "$*" >> '{self.argv_log}'
            exec '{shutil.which("git")}' "$@"
            """)

    def run(self, auth: str | None, token: str | None, token_url: str | None = "server",
            extra_env: dict[str, str] | None = None, origin_userinfo: str = ""):
        server = _GitServer(self.srv, auth)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}/"
            if "origin" in _git(self.checkout, "remote").split():
                _git(self.checkout, "remote", "remove", "origin")
            origin = f"{base}{OWNER}/asd"
            if origin_userinfo:
                origin = origin.replace("http://", f"http://{origin_userinfo}@", 1)
            _git(self.checkout, "remote", "add", "origin", origin)
            env = {"PATH": f"{self.bin}:{os.environ.get('PATH', '/usr/bin:/bin')}",
                   "HOME": str(self.home), "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
                   "MATHVERIFY_ARTIFACT_REF": self.REF, **(extra_env or {})}
            if token is not None:
                env["MATHVERIFY_GITHUB_TOKEN"] = token
            if token_url == "server":
                env["MATHVERIFY_GITHUB_TOKEN_URL"] = base
            elif token_url is not None:
                env["MATHVERIFY_GITHUB_TOKEN_URL"] = token_url
            dest = self.tmp / "dest"
            r = subprocess.run([BASH, str(self.checkout / "scripts" / "fetch_artifacts.sh"),
                                str(dest)], env=env, capture_output=True, text=True, timeout=120,
                               cwd=self.tmp)
            return r, dest, list(server.seen), base
        finally:
            server.shutdown()
            server.server_close()

    def leaks(self, *secrets: str) -> list[str]:
        """Files under the test directory that contain any of the secrets (the server records
        headers in memory only)."""
        found = []
        for p in self.tmp.rglob("*"):
            if p.is_file() and not p.is_symlink():
                data = p.read_bytes()
                found += [f"{p}: {s[:12]}..." for s in secrets if s.encode() in data]
        return found


@pytest.fixture
def token_bed(artifacts, tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not found")
    return TokenBed(tmp_path, artifacts[0]), artifacts[1]


@posix_only
@needs_bash
def test_fetch_artifacts_retries_a_401_with_the_github_token(token_bed):
    bed, files = token_bed
    expected = _basic(OWNER, TOKEN)
    # a GIT_CONFIG_* entry the session already carries must survive the appended header
    marker = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.extraHeader",
              "GIT_CONFIG_VALUE_0": "X-Mathverify-Test: kept"}
    r, dest, seen, _ = bed.run(auth=expected, token=TOKEN, extra_env=marker)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    for name, data in files.items():
        assert (dest / name).read_bytes() == data
    assert (dest / ".source").read_text().splitlines()[0] == f"ref {TokenBed.REF}"
    # first the plain fetch, refused; then the token, on every request of the retry
    assert seen[0]["auth"] == [], seen
    authed = [s for s in seen if s["auth"]]
    assert authed and all(s["auth"] == [expected] for s in authed), seen
    assert all(s["marker"] == ["kept"] for s in seen), seen
    assert "retrying the fetch with MATHVERIFY_GITHUB_TOKEN (value not printed)" in r.stdout, out
    assert "the token fetch succeeded" in r.stdout, out
    b64 = expected.split()[1]
    assert TOKEN not in out and b64 not in out
    argv = bed.argv_log.read_text()
    assert "fetch" in argv and TOKEN not in argv and b64 not in argv
    assert bed.leaks(TOKEN, b64) == []


@posix_only
@needs_bash
def test_fetch_artifacts_without_a_token_fails_like_the_setup_script(token_bed):
    bed, _ = token_bed
    r, dest, seen, _ = bed.run(auth=_basic(OWNER, TOKEN), token=None)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "MATHVERIFY_GITHUB_TOKEN is not set: no token retry" in r.stdout, out
    assert "could not read Username" in r.stderr, out
    assert seen and all(s["auth"] == [] for s in seen), seen
    assert sorted(os.listdir(dest)) == []


@posix_only
@needs_bash
def test_fetch_artifacts_never_sends_the_token_outside_its_url_prefix(token_bed):
    bed, _ = token_bed
    # default prefix https://github.com/: the local server is not under it
    r, dest, seen, base = bed.run(auth=_basic(OWNER, TOKEN), token=TOKEN, token_url=None)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert f"MATHVERIFY_GITHUB_TOKEN is set but {base}{OWNER}/asd is not under " \
           "https://github.com/: token not sent" in r.stdout, out
    assert seen and all(s["auth"] == [] for s in seen), seen
    assert TOKEN not in out and bed.leaks(TOKEN) == []


@posix_only
@needs_bash
def test_fetch_artifacts_does_not_send_the_token_when_the_plain_fetch_works(token_bed):
    # inside a session the GitHub proxy authenticates: the token must never be sent there
    bed, files = token_bed
    r, dest, seen, _ = bed.run(auth=None, token=TOKEN)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    for name, data in files.items():
        assert (dest / name).read_bytes() == data
    assert seen and all(s["auth"] == [] for s in seen), seen
    assert "MATHVERIFY_GITHUB_TOKEN" not in r.stdout, out


@posix_only
@needs_bash
def test_fetch_artifacts_token_tolerates_pasted_whitespace(token_bed):
    bed, files = token_bed
    r, dest, seen, _ = bed.run(auth=_basic(OWNER, TOKEN), token=f"  {TOKEN}\r\n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert [s for s in seen if s["auth"] == [_basic(OWNER, TOKEN)]], seen
    for name, data in files.items():
        assert (dest / name).read_bytes() == data


@posix_only
@needs_bash
def test_fetch_artifacts_never_logs_credentials_embedded_in_the_url(token_bed):
    bed, _ = token_bed
    # the origin URL carries its own user:password; it is not under the default token prefix
    r, _, seen, base = bed.run(auth=_basic(OWNER, TOKEN), token=TOKEN, token_url=None,
                               origin_userinfo="kisi:gizli-parola")
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "is not under https://github.com/: token not sent" in r.stdout, out
    assert "gizli-parola" not in r.stdout, out
    assert all(s["auth"] != [_basic(OWNER, TOKEN)] for s in seen), seen


@posix_only
@needs_bash
def test_fetch_artifacts_wrong_token_fails_fast_without_printing_it(token_bed):
    bed, _ = token_bed
    wrong = TOKEN.replace("TEST", "WRONG")
    r, dest, seen, _ = bed.run(auth=_basic(OWNER, TOKEN), token=wrong)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert [s for s in seen if s["auth"]] and all(
        s["auth"] in ([], [_basic(OWNER, wrong)]) for s in seen), seen
    assert wrong not in out and bed.leaks(wrong, _basic(OWNER, wrong).split()[1]) == []
    assert sorted(os.listdir(dest)) == []
