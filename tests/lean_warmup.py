"""Start Lean once per test session, before the first test that uses it, outside every test's
timeout.

The first `import Mathlib` after a container restart (or from a restored snapshot) reads Mathlib
from a cold disk: ~340-400 s measured on 26 Sep 2026. A test that uses Lean waits for it inside its
own 300 s pytest-timeout (pyproject.toml), which fired first: plain `pytest` failed
test_f5_lean.py::test_lean_proves_true_and_refuses_false and skipped 92 Lean tests, while a second
run on the warm disk was clean. `check.py --full` already warms Lean up before its gates; this does
the same for every pytest run that selects a Lean test, with the budget of that warm-up (900 s).

The warm-up owns its client and closes it: what it warms is the disk cache, and the tests keep the
client `get_lean()` gives them, with its usual 300 s boot budget. A test uses Lean when it calls a
module's `_lean()` helper or requests the `lean` fixture, the only two ways the suite reaches a
live Lean (tests/test_lean_warmup.py keeps it that way). A failed warm-up is reported and changes
nothing else: the Lean tests then decide for themselves, as before.

Loaded by tests/conftest.py.
"""
from __future__ import annotations

import time

import pytest

BOOT_TIMEOUT = 900.0            # the warm-up of check.py --full
LEAN_HELPERS = frozenset({"_lean"})
LEAN_FIXTURES = frozenset({"lean"})
PROBE = "example : (2 : Nat) + 2 = 4 := by norm_num"


def needs_lean(item) -> bool:
    fn = getattr(item, "function", None)
    code = getattr(fn, "__code__", None)
    if code is not None and LEAN_HELPERS & set(code.co_names):
        return True
    return bool(LEAN_FIXTURES & set(getattr(item, "fixturenames", ())))


def warm_up() -> tuple[bool, float, str]:
    """(Lean answered the probe, seconds, why not)."""
    from mathverify.formal.lean_client import LeanClient
    t0 = time.monotonic()
    client = None
    try:
        client = LeanClient(boot_timeout=BOOT_TIMEOUT)
        r = client.run(PROBE, timeout=120)
        return r.clean, time.monotonic() - t0, "" if r.clean else "; ".join(r.errors[:2])
    except Exception as e:  # noqa: BLE001  (an absent toolchain is an outcome, not a crash)
        return False, time.monotonic() - t0, f"{type(e).__name__}: {e}"
    finally:
        if client is not None:
            client.close()


@pytest.hookimpl(tryfirst=True)
def pytest_runtestloop(session):
    if session.config.option.collectonly or not any(map(needs_lean, session.items)):
        return None
    ok, secs, why = warm_up()
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        line = f"Lean ısınması: {secs:.0f} s, " + ("hazır" if ok else f"hazır değil ({why[:200]})")
        reporter.write_line(line)
    return None                 # the default loop runs the tests
