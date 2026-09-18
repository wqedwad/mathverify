"""Sandbox contract (handoff §11/4, §12): hard timeout, recovery, determinism, memory cap."""
import os
import time

import pytest
import sympy as sp

from mathverify.sandbox import Sandbox, SandboxTimeout, SandboxError


@pytest.fixture(scope="module")
def sb():
    s = Sandbox(mem_mb=512, mode="process")
    yield s
    s.close()


def test_basic_call_and_pickling_of_sympy_objects(sb):
    x = sp.Symbol("x", real=True)
    r = sb.call("mathverify.sandbox.ops:simplify_diff", (x + 1) ** 2, x ** 2 + 2 * x + 1)
    assert r == 0
    assert sb.mem_mode != "unknown"


def test_hard_timeout_kills_runaway_and_recovers(sb):
    t0 = time.perf_counter()
    with pytest.raises(SandboxTimeout):
        sb.call("mathverify.sandbox.ops:spin", 30, timeout=1.0)
    assert time.perf_counter() - t0 < 6.0
    assert sb.timeouts >= 1
    # the pool must come back
    assert sb.call("mathverify.sandbox.ops:spin", 0.01) == "done"


def test_run_never_raises(sb):
    r = sb.run("mathverify.sandbox.ops:spin", 30, timeout=0.5)
    assert r.ok is False and r.timed_out is True and "cas_timeout" in r.flags
    r = sb.run("mathverify.sandbox.ops:simplify_diff", 1, 1)
    assert r.ok and r.value == 0 and r.ms >= 0


def test_worker_exception_is_reported_not_fatal(sb):
    with pytest.raises(SandboxError):
        sb.call("mathverify.sandbox.ops:poly_count_roots", sp.sin(sp.Symbol("x")), sp.Symbol("x"))
    assert sb.call("mathverify.sandbox.ops:simplify_diff", 2, 2) == 0


def test_seed_is_applied_in_worker(sb):
    a = sb.call("mathverify.sandbox.ops:echo_seed", seed=123)
    b = sb.call("mathverify.sandbox.ops:echo_seed", seed=123)
    c = sb.call("mathverify.sandbox.ops:echo_seed", seed=124)
    assert a == b and a != c


def test_memory_cap_is_enforced_best_effort(sb):
    if sb.mem_mode in ("none",) or sb.mem_mode.startswith("unavailable"):
        pytest.skip(f"no memory cap available on this platform: {sb.mem_mode}")
    with pytest.raises((SandboxError, SandboxTimeout)):
        sb.call("mathverify.sandbox.ops:hog", 1500, timeout=20)
    assert sb.call("mathverify.sandbox.ops:simplify_diff", 3, 3) == 0


def test_inline_mode_for_debugging_only():
    s = Sandbox(mode="inline")
    assert s.call("mathverify.sandbox.ops:simplify_diff", 1, 1) == 0
    assert s.mem_mode == "inline"


def test_worker_hash_seed_pinned(sb):
    assert os.environ.get("PYTHONHASHSEED") == "0"
