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
