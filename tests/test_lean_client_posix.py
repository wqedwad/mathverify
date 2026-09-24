"""Lean REPL launcher across platforms (offline, fast; no Lean toolchain needed).

Windows reaches Lean through `wsl ... bash -lc`; Linux/macOS (the cloud container) run the same
shell line in a local bash. Two failure modes this file pins:
- a missing launcher (no wsl.exe / no bash) used to surface as FileNotFoundError, which callers
  that handle LeanUnavailable (formal.prove) did not catch;
- on POSIX `lake env <repl>` runs the REPL as a child of lake, so killing only the launcher pid
  orphaned the REPL (~1 GB) on every timeout/respawn.
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


def test_a_missing_launcher_is_lean_unavailable_not_a_crash(monkeypatch):
    seen: dict = {}

    def no_such_program(cmd, **kw):
        seen.update(cmd=cmd, kw=kw)
        raise FileNotFoundError(2, "No such file or directory", cmd[0])

    monkeypatch.setattr(lc.subprocess, "Popen", no_such_program)
    client = lc.LeanClient(project="/p", repl="/r", distro="D")
    with pytest.raises(lc.LeanUnavailable, match="cannot launch the Lean REPL"):
        client.run("example : True := trivial", timeout=5)
    assert client._proc is None
    assert seen["cmd"] == lc.repl_command("/p", "/r", "D")
    # POSIX launches in a new session so _kill can reach the REPL child; Windows is unchanged
    assert seen["kw"].get("start_new_session", False) is (os.name != "nt")


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
