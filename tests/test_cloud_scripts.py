"""Cloud session scripts: static contracts and hook/installer behaviour (offline, fast).

Static checks run everywhere: the SessionStart hook entry in .claude/settings.json, requirements.lock
against pyproject.toml and this interpreter, the lean/ pins, and `bash -n` on every script.

Behaviour checks run the real scripts, never against the real install:
- Windows: only through Git Bash (C:\\Program Files\\Git\\bin\\bash.exe). `bash` from a Windows PATH
  can be the WSL launcher, which is exactly the failure .claude/settings.json's "shell": "bash" avoids.
- POSIX: the hook's Lean state machine on stub install prefixes (MATHVERIFY_HOOK_PREFIXES keeps a
  real /opt install out), fetch_artifacts.sh on a tiny generated artifact set, and setup_env.sh's uv
  prewarm with a stub uv and interpreter. The same prewarm with the real uv and CPython 3.14.6 is
  opt-in (MATHVERIFY_CLOUD_INTEGRATION=1, network), since it downloads the locked packages.
- POSIX: setup_env.sh, setup_lean.sh and setup_lean_repl.sh themselves, on pins that point at tiny
  local git repositories, an artifact set built from them and a stub elan/Lean/Lake (LeanBed): the
  offline install, a failed fetch over an installed prefix, a staged update and its rollback.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import os
import re
import shutil
import signal
import subprocess
import tarfile
import textwrap
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

# A stand-in interpreter: version queries, `-m venv DIR` (copies itself), anything else succeeds.
STUB_PYTHON = """
    #!/bin/sh
    case "$1" in
      -c) case "$2" in
            *platform*) echo 3.14.6 ;;
            *sys.version*) echo "3.14.6 (stub)" ;;
          esac ;;
      -m) if [ "$2" = venv ]; then mkdir -p "$3/bin" && cp "$0" "$3/bin/python"; fi ;;
    esac
    exit 0
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
               status: str | None = None, lock_file: bool = False) -> Path:
        p = self.tmp / name
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

    def lean_line(self, out: str) -> str:
        (line,) = [ln for ln in out.splitlines() if ln.startswith("- Lean: ")]
        return line

    def started(self) -> bool:
        return "started setup_env.sh --lean-only" in self.session_log


FAILED_REPL = ("FAILED mode=all failed=[setup_lean_repl] stages=[fetch_artifacts(6s) "
               "setup_lean(126s) setup_lean_repl(9s)] python=3.14.6 lean=missing total=150s")


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
    assert "BAŞARISIZ" not in out
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
# `import Mathlib` smoke test and the REPL smoke test fail, STUB_ENV_TRUE=fail `lake env true`.
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
        echo "'smoke' depends on axioms: [propext, Classical.choice, Quot.sound]" ;;
      "env true") [ "${STUB_ENV_TRUE:-ok}" = ok ] || { echo "error: stub lake env failure"; exit 1; } ;;
      "env "*/repl)
        cat > /dev/null
        [ "${STUB_REPL_SMOKE:-ok}" = ok ] || { echo '{"severity": "error"}'; exit 0; }
        printf '{"env": 0}\n\n{"env": 1}\n' ;;
      *) echo "stub lake: unexpected $*" >&2; exit 2 ;;
    esac
"""

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

    def env(self, **extra: str | None) -> dict[str, str]:
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home), "TMPDIR": str(self.tmp),
               "LC_ALL": "C", "GIT_CONFIG_GLOBAL": os.devnull,
               "GIT_CONFIG_SYSTEM": str(self.tmp / "gitconfig-system"),
               "MATHVERIFY_OPT": str(self.opt), "CLAUDE_PROJECT_DIR": str(self.repo),
               "MATHVERIFY_PROFILE_D": str(self.tmp / "profile.d"),
               "MATHVERIFY_ARTIFACT_SRC": str(self.src), **extra}
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
@pytest.mark.parametrize("failure", ["smoke", "lake-env-after-swap"])
def test_setup_env_update_is_staged_and_a_failed_one_keeps_the_old_project(installed, failure):
    bed = installed
    proj = bed.opt / "mathverify-lean"
    basic = bed.change_pins()
    before = _tree(proj)
    done = (bed.opt / "mathverify-logs" / "lean.done").read_text()
    fail = {"STUB_LEAN_SMOKE": "fail"} if failure == "smoke" else {"STUB_ENV_TRUE": "fail"}
    r, _ = bed.setup_env("--lean-only", **fail)
    assert bed.status().startswith("FAILED mode=lean failed=[setup_lean] "), bed.status() + r.stdout
    # The new project was built next to the live one and discarded; the live one is as it was.
    assert _tree(proj) == before
    assert (bed.opt / "mathverify-logs" / "lean.done").read_text() == done
    cwds = [Path(c[0]) for c in bed.lake_calls()]
    log = (bed.opt / "mathverify-logs" / "setup_lean.log").read_text()
    assert f"{proj} differs from the pins: building the new project in" in log
    if failure == "smoke":
        assert cwds and all(c.name.startswith(".mathverify-lean.stage.") for c in cwds), cwds
    else:
        # swapped in, Lake failed there, swapped back
        assert cwds[-1] == proj and all(c.name.startswith(".mathverify-lean.stage.") for c in cwds[:-1])
        assert "the previous project was put back" in log
    assert _dot_entries(bed.opt) == []
    # The same update without the failure swaps the new project in, then deletes the old one.
    bed.calls.unlink()
    r, _ = bed.setup_env("--lean-only")
    assert bed.status().startswith("OK mode=lean failed=[]"), bed.status() + r.stdout
    assert (proj / "MathverifyLean" / "Basic.lean").read_bytes() == basic.read_bytes()
    assert (bed.opt / "mathverify-logs" / "lean.done").read_text().strip() == bed.fingerprint()
    in_proj = [c[1] for c in bed.lake_calls() if Path(c[0]) == proj]
    assert in_proj[0] == "env true", in_proj  # Lake opens the swapped-in project (then the REPL smoke)
    assert _dot_entries(bed.opt) == [] and not list((proj / ".lake").glob(".mathverify-setup.*"))


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
