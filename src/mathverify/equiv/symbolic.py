"""Symbolic equivalence (positive evidence only).

Returns True when a CAS canonicaliser proves a - b == 0, otherwise None. It NEVER
returns False: symbolic failure to simplify is not evidence of inequality
(Richardson [24]). Negative evidence comes from `numeric` / `random_point`.
Every CAS call runs in the sandbox with a hard timeout (§11/4).
"""
from __future__ import annotations

from typing import Any

import sympy as sp

from ..sandbox import run as sb_run

__all__ = ["sym_equal"]


def sym_equal(a, b, timeout: float = 5.0) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"method": None}
    a, b = sp.sympify(a), sp.sympify(b)
    if a == b:
        ev["method"] = "structural"
        return True, ev
    try:
        d = a - b
    except Exception:
        return None, ev
    if d == 0:
        ev["method"] = "structural_diff"
        return True, ev
    r = sb_run("mathverify.sandbox.ops:zero_test_battery", d, timeout=timeout)
    ev["battery"] = {"ok": r.ok, "ms": round(r.ms, 1), "flags": r.flags}
    if r.ok and r.value is True:
        ev["method"] = "zero_test_battery"
        return True, ev
    r2 = sb_run("mathverify.sandbox.ops:equals", a, b, timeout=timeout)
    ev["equals"] = {"ok": r2.ok, "value": r2.value if r2.ok else r2.error, "ms": round(r2.ms, 1)}
    if r2.ok and r2.value is True:
        ev["method"] = "sympy_equals"
        return True, ev
    ev["flags"] = list(set(r.flags + r2.flags))
    return None, ev
