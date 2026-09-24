"""Lean REPL launcher across platforms (offline, fast; no Lean toolchain needed).

Windows reaches Lean through `wsl ... bash -lc`; Linux/macOS (the cloud container) run the same
shell line in a local bash. Three failure modes this file pins:
- a missing launcher (no wsl.exe / no bash) used to surface as FileNotFoundError, which callers
  that handle LeanUnavailable (formal.prove) did not catch;
- on POSIX `lake env <repl>` runs the REPL as a child of lake, so killing only the launcher pid
  orphaned the REPL (~6.7 GB RSS with Mathlib loaded) on every timeout/respawn;
- on POSIX a missing REPL binary still started `lake env`, which clones the project's missing
  dependencies before it fails on the binary.
"""
import os
import signal
import subprocess
import sys
import time

import pytest

from mathverify.formal import lean_client as lc

_LINE = ('cd ~/mathverify-lean && export PATH="${ELAN_HOME:-$HOME/.elan}/bin:$PATH" '
         '&& exec lake env ~/repl/.lake/build/bin/repl')


def test_repl_command_native_runs_the_line_in_a_local_bash():
    cmd = lc.repl_command("~/mathverify-lean", "~/repl/.lake/build/bin/repl", "Ubuntu", native=True)
    assert cmd == ["bash", "-lc", _LINE]


def test_repl_command_on_windows_goes_through_wsl():
    cmd = lc.repl_command("~/mathverify-lean", "~/repl/.lake/build/bin/repl", "Ubuntu", native=False)
    assert cmd == ["wsl", "-d", "Ubuntu", "--", "bash", "-lc", _LINE]


def test_repl_command_defaults_to_the_host_platform():
    args = ("/opt/mathverify-lean", "/opt/repl/.lake/build/bin/repl", "Ubuntu")
    assert lc.repl_command(*args) == lc.repl_command(*args, native=os.name != "nt")
    assert lc.repl_command(*args)[0] == ("wsl" if os.name == "nt" else "bash")


def test_a_missing_launcher_is_lean_unavailable_not_a_crash(monkeypatch, tmp_path):
    seen: dict = {}

    def no_such_program(cmd, **kw):
        seen.update(cmd=cmd, kw=kw)
        raise FileNotFoundError(2, "No such file or directory", cmd[0])

    repl = tmp_path / "repl"
    repl.write_bytes(b"")                  # the binary exists; only the launcher is missing
    monkeypatch.setattr(lc.subprocess, "Popen", no_such_program)
    client = lc.LeanClient(project=str(tmp_path), repl=str(repl), distro="D")
    with pytest.raises(lc.LeanUnavailable, match="cannot launch the Lean REPL"):
        client.run("example : True := trivial", timeout=5)
    assert client._proc is None
    assert seen["cmd"] == lc.repl_command(str(tmp_path), str(repl), "D")
    # POSIX launches in a new session so _kill can reach the REPL child; Windows is unchanged
    assert seen["kw"].get("start_new_session", False) is (os.name != "nt")


# ---------------------------------------------------------------- missing REPL binary
# `lake env <repl>` materialises the project's missing dependencies BEFORE it discovers that
# <repl> does not exist (measured on a toy project with a git dependency: the dependency was
# cloned into .lake/packages and a lake-manifest.json written, then exit 255). On a
# half-installed cloud project that is a Mathlib clone per call, so on POSIX a missing binary
# must stop the launch before any process starts.
class _Launched(Exception):
    pass


def _record_popen(monkeypatch) -> list:
    calls: list = []

    def fake(cmd, **kw):
        calls.append(cmd)
        raise _Launched(cmd)

    monkeypatch.setattr(lc.subprocess, "Popen", fake)
    return calls


def test_a_missing_repl_binary_never_starts_lake_on_posix(monkeypatch, tmp_path):
    monkeypatch.setattr(lc, "_POSIX", True)
    calls = _record_popen(monkeypatch)
    missing = tmp_path / "repl" / ".lake" / "build" / "bin" / "repl"
    client = lc.LeanClient(project=str(tmp_path), repl=str(missing), distro="D")
    with pytest.raises(lc.LeanUnavailable, match="REPL binary missing") as ei:
        client.run("example : True := trivial", timeout=5)
    assert str(missing) in str(ei.value)
    assert calls == [], "a process was launched for a REPL binary that does not exist"
    assert client._proc is None


def test_an_existing_repl_binary_is_launched_on_posix(monkeypatch, tmp_path):
    monkeypatch.setattr(lc, "_POSIX", True)
    calls = _record_popen(monkeypatch)
    repl = tmp_path / "repl"
    repl.write_bytes(b"")
    with pytest.raises(_Launched):
        lc.LeanClient(project=str(tmp_path), repl=str(repl), distro="D").run("x", timeout=5)
    assert len(calls) == 1


def test_windows_does_not_check_the_wsl_side_path(monkeypatch, tmp_path):
    """On Windows the REPL path is a path inside WSL: it cannot be checked from here, so the
    launch goes ahead exactly as before and WSL reports the failure."""
    monkeypatch.setattr(lc, "_POSIX", False)
    calls = _record_popen(monkeypatch)
    missing = str(tmp_path / "no-such-repl")
    with pytest.raises(_Launched):
        lc.LeanClient(project=str(tmp_path), repl=missing, distro="D").run("x", timeout=5)
    assert calls == [lc.repl_command(str(tmp_path), missing, "D", native=False)]


def test_native_repl_path_resolves_like_the_shell_line(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))          # what expanduser reads on Windows
    monkeypatch.setenv("MV_TEST_OPT", str(tmp_path / "opt"))
    proj = str(tmp_path / "proj")
    # `~` and `$VAR` are expanded by bash, so they are expanded here too
    got = lc.native_repl_path(proj, "~/repl/.lake/build/bin/repl")
    assert os.path.normpath(got) == os.path.normpath(str(home / "repl/.lake/build/bin/repl"))
    got = lc.native_repl_path(proj, "$MV_TEST_OPT/repl/.lake/build/bin/repl")
    assert os.path.normpath(got) == os.path.normpath(str(tmp_path / "opt/repl/.lake/build/bin/repl"))
    # the line `cd`s into the project first, so a relative path is taken from there
    got = lc.native_repl_path(proj, "sub/repl")
    assert os.path.normpath(got) == os.path.normpath(os.path.join(proj, "sub/repl"))
    # a bare name is a PATH lookup in the login shell and an unknown variable is the shell's
    # business: neither can be decided here, so neither is refused
    assert lc.native_repl_path(proj, "repl") is None
    monkeypatch.delenv("MV_TEST_UNSET_VAR", raising=False)
    assert lc.native_repl_path(proj, "$MV_TEST_UNSET_VAR/repl") is None


def test_a_bare_repl_name_is_left_to_the_shell(monkeypatch, tmp_path):
    monkeypatch.setattr(lc, "_POSIX", True)
    calls = _record_popen(monkeypatch)
    with pytest.raises(_Launched):
        lc.LeanClient(project=str(tmp_path), repl="repl", distro="D").run("x", timeout=5)
    assert len(calls) == 1


@pytest.mark.skipif(os.name == "nt", reason="process groups are POSIX-only; Windows kills wsl.exe")
def test_kill_takes_down_the_whole_process_group():
    # The same shape as `lake env repl`: the Popen pid (leader) has a long-lived child.
    proc = subprocess.Popen(["bash", "-c", "sleep 300 & echo $!; sleep 301"],
                            stdout=subprocess.PIPE, text=True, start_new_session=True)
    child = int(proc.stdout.readline())               # the child exists before we kill
    pgid = proc.pid
    assert os.getpgid(child) == pgid
    client = lc.LeanClient()
    client._proc = proc
    try:
        client._kill()
        assert client._proc is None
        deadline = time.monotonic() + 5.0
        while _live_members(pgid) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not _live_members(pgid), f"orphans left in group {pgid}: {_live_members(pgid)}"
    finally:
        try:
            os.killpg(pgid, signal.SIGKILL)           # never leak sleeps if the assertion fails
        except ProcessLookupError:
            pass
        proc.stdout.close()


def _live_members(pgid: int) -> list[int]:
    """Non-zombie processes still in process group `pgid`. A killed orphan is reparented and
    may stay a zombie when PID 1 does not reap (bare containers), so zombies count as gone."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return []
    if not sys.platform.startswith("linux"):
        return [pgid]                                 # no /proc: any member counts as alive
    live = []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat", encoding="utf-8", errors="replace") as fh:
                stat = fh.read()
        except OSError:
            continue
        # fields after the parenthesised comm: state ppid pgrp ...
        state, _ppid, pgrp = stat.rsplit(")", 1)[1].split()[:3]
        if int(pgrp) == pgid and state != "Z":
            live.append(int(d))
    return live
