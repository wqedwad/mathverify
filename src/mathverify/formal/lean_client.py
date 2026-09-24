"""Persistent Lean 4 + Mathlib REPL (handoff §10 / [2]).

The REPL process runs with Mathlib imported once (~13 s): on Windows inside WSL, on
Linux/macOS (e.g. a cloud container) in a local bash. Every later check is a JSON round-trip
on the cached environment, so a proof attempt costs ~0.1-3 s instead of a fresh
`import Mathlib`. Protocol (leanprover-community/repl): one JSON object per request followed
by a blank line; the reply is one JSON object.

Hard rules: every call has a wall-clock timeout, a timed-out or crashed REPL is killed and
respawned, and nothing here ever decides a verdict — it reports what Lean said.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["LeanClient", "LeanResult", "LeanUnavailable", "get_lean", "lean_available",
           "repl_command"]

DEFAULT_PROJECT = os.environ.get("MATHVERIFY_LEAN_PROJECT", "~/mathverify-lean")
DEFAULT_REPL = os.environ.get("MATHVERIFY_LEAN_REPL", "~/repl/.lake/build/bin/repl")
DEFAULT_DISTRO = os.environ.get("MATHVERIFY_WSL_DISTRO", "Ubuntu")

_POSIX = os.name != "nt"


class LeanUnavailable(RuntimeError):
    pass


def repl_command(project: str, repl: str, distro: str, native: bool | None = None) -> list[str]:
    """The argv that starts the REPL. Windows reaches the toolchain through WSL; on
    Linux/macOS the same shell line runs in a local bash (`native` defaults to "not Windows").

    `ELAN_HOME` is honoured when the login shell has it (cloud layout: /opt/elan) and falls
    back to `$HOME/.elan`; the WSL login shell does not set it, so Windows runs the exact
    toolchain it always did."""
    if native is None:
        native = _POSIX
    line = (f'cd {project} && export PATH="${{ELAN_HOME:-$HOME/.elan}}/bin:$PATH" '
            f'&& exec lake env {repl}')
    if native:
        return ["bash", "-lc", line]
    return ["wsl", "-d", distro, "--", "bash", "-lc", line]


@dataclass
class LeanResult:
    ok: bool                                  # compiled with no error-severity message
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)
    sorries: list[dict[str, Any]] = field(default_factory=list)
    env: int | None = None
    ms: float = 0.0
    timed_out: bool = False
    raw: dict[str, Any] | None = None

    @property
    def clean(self) -> bool:
        """Compiled, no errors, no `sorry` placeholders."""
        return self.ok and not self.sorries


class LeanClient:
    """One REPL subprocess with Mathlib preloaded. Not thread-safe: use one per thread."""

    def __init__(self, project: str = DEFAULT_PROJECT, repl: str = DEFAULT_REPL,
                 distro: str = DEFAULT_DISTRO, boot_timeout: float = 300.0):
        self.project, self.repl, self.distro = project, repl, distro
        self.boot_timeout = boot_timeout
        self._proc: subprocess.Popen | None = None
        self._base_env: int | None = None
        self._lock = threading.Lock()
        self.restarts = 0

    # ---------------------------------------------------------------- process
    def _spawn(self) -> None:
        # `lake env <cmd>` is the only reliable way to hand Mathlib's LEAN_PATH to the REPL:
        # a `LEAN_PATH=... exec repl` prefix assignment is NOT exported (exec is a special
        # builtin), which silently gives an import-less environment where even `+` fails to
        # parse. Measured: import Mathlib then returns in 3 s instead of ~13 s — that speed
        # is itself the symptom.
        cmd = repl_command(self.project, self.repl, self.distro)
        env = dict(os.environ, MSYS_NO_PATHCONV="1")
        # POSIX: `lake env` runs the REPL as its CHILD, so killing the Popen pid alone would
        # orphan the REPL (~1 GB) on every timeout. A new session makes the launcher a process
        # group leader, and _kill takes down the whole group. On Windows killing wsl.exe
        # already tears down the Linux side, so nothing changes there.
        extra: dict[str, Any] = {"start_new_session": True} if _POSIX else {}
        try:
            self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                          errors="replace", bufsize=1, env=env, **extra)
        except OSError as e:           # no wsl.exe / no bash: the toolchain is absent, not a crash
            self._proc = None
            raise LeanUnavailable(f"cannot launch the Lean REPL ({cmd[0]}): {e}") from e
        r = self._send_raw({"cmd": "import Mathlib", "env": None}, timeout=self.boot_timeout)
        if r.raw is None or "env" not in (r.raw or {}):
            self._kill()
            raise LeanUnavailable(f"REPL did not start: {r.errors[:2]}")
        self._base_env = r.raw["env"]
        # prove the environment really has Mathlib: an import-less env parses none of this
        probe = self._send_raw({"cmd": "example : (2 : ℝ) + 2 = 4 := by norm_num",
                                "env": self._base_env}, timeout=60.0)
        if not probe.clean:
            self._kill()
            raise LeanUnavailable(f"Mathlib environment not usable: {probe.errors[:2]}")

    def _kill(self) -> None:
        if self._proc is not None:
            if _POSIX:
                # the launcher leads its own process group (start_new_session): kill the REPL
                # child too, not just the launcher
                try:
                    os.killpg(self._proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            try:
                self._proc.kill()
                self._proc.wait(timeout=10)
            except Exception:
                pass
        self._proc, self._base_env = None, None

    def close(self) -> None:
        self._kill()

    def _alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ---------------------------------------------------------------- protocol
    def _send_raw(self, payload: dict[str, Any], timeout: float) -> LeanResult:
        assert self._proc is not None and self._proc.stdin and self._proc.stdout
        t0 = time.perf_counter()
        line = json.dumps(payload, ensure_ascii=False)
        try:
            self._proc.stdin.write(line + "\n\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            self._kill()
            return LeanResult(ok=False, errors=[f"write failed: {e}"], ms=0.0)
        out: list[str] = []
        done = threading.Event()

        def _read():
            try:
                for ln in self._proc.stdout:            # type: ignore[union-attr]
                    if ln.strip() == "" and out:
                        break
                    out.append(ln)
                    try:
                        json.loads("".join(out))
                        break
                    except json.JSONDecodeError:
                        continue
            except Exception:
                pass
            finally:
                done.set()

        th = threading.Thread(target=_read, daemon=True)
        th.start()
        if not done.wait(timeout):
            self.restarts += 1
            self._kill()
            return LeanResult(ok=False, errors=[f"lean timeout after {timeout:.0f}s"],
                              ms=(time.perf_counter() - t0) * 1000, timed_out=True)
        txt = "".join(out).strip()
        ms = (time.perf_counter() - t0) * 1000
        if not txt:
            self._kill()
            return LeanResult(ok=False, errors=["empty reply (REPL died)"], ms=ms)
        try:
            data = json.loads(txt)
        except json.JSONDecodeError as e:
            return LeanResult(ok=False, errors=[f"bad JSON from REPL: {e}: {txt[:200]}"], ms=ms)
        msgs = data.get("messages") or []
        errs = [m.get("data", "") for m in msgs if m.get("severity") == "error"]
        warns = [m.get("data", "") for m in msgs if m.get("severity") == "warning"]
        infos = [m.get("data", "") for m in msgs if m.get("severity") == "info"]
        return LeanResult(ok=not errs and "message" not in data, errors=errs, warnings=warns, infos=infos,
                          sorries=data.get("sorries") or [], env=data.get("env"), ms=ms, raw=data)

    # ---------------------------------------------------------------- public
    def run(self, code: str, timeout: float = 120.0, env: int | None = -1) -> LeanResult:
        """Elaborate `code` on top of the Mathlib environment. env=-1 means the base env."""
        with self._lock:
            if not self._alive():
                self._spawn()
            use_env = self._base_env if env == -1 else env
            r = self._send_raw({"cmd": code, "env": use_env}, timeout=timeout)
            if r.timed_out or (not r.ok and any("REPL died" in e or "write failed" in e for e in r.errors)):
                try:
                    self._spawn()                      # bring it back for the next caller
                except LeanUnavailable:
                    pass
            return r


_LOCAL = threading.local()


def get_lean() -> LeanClient:
    c = getattr(_LOCAL, "lean", None)
    if c is None:
        c = LeanClient()
        _LOCAL.lean = c
    return c


def lean_available(timeout: float = 300.0) -> bool:
    try:
        r = get_lean().run("example : (2 : ℕ) + 2 = 4 := by norm_num", timeout=timeout)
        return r.clean
    except Exception:
        return False
