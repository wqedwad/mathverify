"""Process-isolated CAS/z3 execution with hard timeouts (handoff §7, §11/4, §12).

Every symbolic computation that can hang (simplify/solve/integrate/limit — Richardson
[24], SymPy issues [25]) runs in a persistent worker process. On timeout the worker is
killed and respawned, so one runaway call cannot poison the next one.

Design:
  * one persistent worker (imports sympy/mpmath/z3 once) -> low per-call overhead
  * functions are referenced by dotted path "module:qualname" (spawn-safe on Windows)
  * seed is passed explicitly and applied in the worker (determinism, §11/13)
  * best-effort memory cap: RLIMIT_AS on POSIX, Job Object on Windows
  * MATHVERIFY_SANDBOX=inline runs in-process (debugging only; never in production)

This is process isolation, NOT a security sandbox. Model-generated *code* must run in
gVisor/nsjail/Firecracker (§11/7). Phase 1 never executes model-generated code: it
parses expressions with a whitelist and evaluates them with sympy.
"""
from __future__ import annotations

import atexit
import importlib
import multiprocessing as mp
import os
import random
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Sandbox", "SandboxTimeout", "SandboxError", "CasResult", "get_sandbox", "run"]


class SandboxTimeout(TimeoutError):
    pass


class SandboxError(RuntimeError):
    pass


@dataclass
class CasResult:
    ok: bool
    value: Any = None
    error: str | None = None
    timed_out: bool = False
    ms: float = 0.0
    fn: str = ""
    flags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# worker side
# ---------------------------------------------------------------------------
def _resolve(path: str):
    mod, _, name = path.partition(":")
    obj: Any = importlib.import_module(mod)
    for part in name.split("."):
        obj = getattr(obj, part)
    return obj


def _apply_mem_limit(mem_mb: int) -> str:
    if mem_mb <= 0:
        return "none"
    try:
        if os.name == "posix":
            import resource
            lim = mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
            return "rlimit_as"
        if os.name == "nt":
            return _win_job_limit(mem_mb)
    except Exception as e:  # pragma: no cover - platform dependent
        return f"unavailable:{type(e).__name__}"
    return "none"


def _win_job_limit(mem_mb: int) -> str:  # pragma: no cover - exercised only on Windows
    import ctypes
    from ctypes import wintypes as wt

    k32 = ctypes.windll.kernel32

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in
                    ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                     "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wt.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wt.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wt.DWORD),
                    ("SchedulingClass", wt.DWORD)]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
    JobObjectExtendedLimitInformation = 9
    job = k32.CreateJobObjectW(None, None)
    if not job:
        return "unavailable:CreateJobObject"
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY
    info.ProcessMemoryLimit = mem_mb * 1024 * 1024
    ok = k32.SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                     ctypes.byref(info), ctypes.sizeof(info))
    if not ok:
        return "unavailable:SetInformationJobObject"
    if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
        return "unavailable:AssignProcessToJobObject"
    return "job_object"


def _rss_bytes() -> int | None:
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes as wt

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            k32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                return int(pmc.PagefileUsage)
            return None
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(r) * (1024 if sys.platform != "darwin" else 1)
    except Exception:
        return None


def _start_mem_watchdog(mem_mb: int) -> bool:
    """Best-effort memory cap that works even when Job Objects/rlimits are unavailable:
    a daemon thread polls the process memory and hard-exits the worker above the cap."""
    import threading
    if mem_mb <= 0 or _rss_bytes() is None:
        return False
    cap = mem_mb * 1024 * 1024

    def _watch():
        while True:
            time.sleep(0.1)
            b = _rss_bytes()
            if b is not None and b > cap:
                os._exit(137)

    threading.Thread(target=_watch, daemon=True, name="mem-watchdog").start()
    return True


def _worker_main(conn, mem_mb: int) -> None:
    mem_mode = _apply_mem_limit(mem_mb)
    if mem_mode.startswith("unavailable") or mem_mode == "none":
        if _start_mem_watchdog(mem_mb):
            mem_mode = f"watchdog({mem_mode})"
    import sympy, mpmath, z3  # noqa: F401  (warm import)
    conn.send(("ready", mem_mode))
    while True:
        try:
            msg = conn.recv()
        except (EOFError, OSError):
            break
        if msg is None:
            break
        fn_path, args, kwargs, seed = msg
        t0 = time.perf_counter()
        try:
            random.seed(seed)
            fn = _resolve(fn_path)
            res = fn(*args, **kwargs)
            try:
                conn.send(("ok", res, (time.perf_counter() - t0) * 1000))
            except Exception as e:  # unpicklable result
                conn.send(("err", "PickleError", f"{type(e).__name__}: {e}", "",
                           (time.perf_counter() - t0) * 1000))
        except BaseException as e:  # noqa: BLE001 - we must report everything
            conn.send(("err", type(e).__name__, str(e), traceback.format_exc(),
                       (time.perf_counter() - t0) * 1000))
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                break


# ---------------------------------------------------------------------------
# parent side
# ---------------------------------------------------------------------------
class Sandbox:
    def __init__(self, mem_mb: int = 2048, mode: str | None = None):
        self.mem_mb = mem_mb
        self.mode = mode or os.environ.get("MATHVERIFY_SANDBOX", "process")
        self._proc: mp.Process | None = None
        self._conn = None
        self.mem_mode = "inline" if self.mode == "inline" else "unknown"
        self.restarts = 0
        self.calls = 0
        self.timeouts = 0

    # lifecycle ---------------------------------------------------------
    def _start(self) -> None:
        # determinism (§11/13): SymPy set/dict ordering can depend on the hash seed
        # (measured: `is_subset` on ImageSet unions flips between None and True across
        # seeds). Every CAS computation runs in the worker, so pin the seed there.
        os.environ.setdefault("PYTHONHASHSEED", "0")
        ctx = mp.get_context("spawn")
        parent, child = ctx.Pipe(duplex=True)
        proc = ctx.Process(target=_worker_main, args=(child, self.mem_mb), daemon=True)
        proc.start()
        child.close()
        if parent.poll(60):
            status, mem_mode = parent.recv()
            self.mem_mode = mem_mode
        else:  # pragma: no cover
            proc.kill()
            raise SandboxError("worker did not become ready")
        self._proc, self._conn = proc, parent

    def _alive(self) -> bool:
        return self._proc is not None and self._proc.is_alive() and self._conn is not None

    def _kill(self) -> None:
        if self._proc is not None:
            try:
                self._proc.kill()
                self._proc.join(5)
            except Exception:  # pragma: no cover
                pass
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:  # pragma: no cover
                pass
        self._proc, self._conn = None, None

    def close(self) -> None:
        if self._alive():
            try:
                self._conn.send(None)
                self._proc.join(2)
            except Exception:  # pragma: no cover
                pass
        self._kill()

    # execution -----------------------------------------------------------
    def call(self, fn_path: str, *args, timeout: float = 5.0, seed: int = 0, **kwargs) -> Any:
        """Run `fn_path(*args, **kwargs)` in the worker. Raises SandboxTimeout / SandboxError."""
        self.calls += 1
        if self.mode == "inline":
            random.seed(seed)
            return _resolve(fn_path)(*args, **kwargs)
        if not self._alive():
            self._start()
        try:
            self._conn.send((fn_path, args, kwargs, seed))
        except Exception as e:
            self._kill()
            raise SandboxError(f"cannot send to worker: {e}") from e
        if not self._conn.poll(timeout):
            self.timeouts += 1
            self.restarts += 1
            self._kill()
            raise SandboxTimeout(f"{fn_path} exceeded {timeout:.1f}s")
        try:
            msg = self._conn.recv()
        except (EOFError, OSError) as e:  # worker died (e.g. memory cap)
            self.restarts += 1
            self._kill()
            raise SandboxError(f"worker died during {fn_path}: {e}") from e
        if msg[0] == "ok":
            return msg[1]
        _, ename, emsg, tb, _ms = msg
        raise SandboxError(f"{ename}: {emsg}")

    def run(self, fn_path: str, *args, timeout: float = 5.0, seed: int = 0, **kwargs) -> CasResult:
        """Like `call` but never raises; returns a CasResult for evidence logging."""
        t0 = time.perf_counter()
        try:
            v = self.call(fn_path, *args, timeout=timeout, seed=seed, **kwargs)
            return CasResult(True, v, None, False, (time.perf_counter() - t0) * 1000, fn_path)
        except SandboxTimeout as e:
            return CasResult(False, None, str(e), True, (time.perf_counter() - t0) * 1000,
                             fn_path, ["cas_timeout"])
        except SandboxError as e:
            return CasResult(False, None, str(e), False, (time.perf_counter() - t0) * 1000,
                             fn_path, ["cas_error"])


_DEFAULT: Sandbox | None = None


def get_sandbox() -> Sandbox:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Sandbox()
        atexit.register(_DEFAULT.close)
    return _DEFAULT


def run(fn_path: str, *args, timeout: float = 5.0, seed: int = 0, **kwargs) -> CasResult:
    return get_sandbox().run(fn_path, *args, timeout=timeout, seed=seed, **kwargs)
