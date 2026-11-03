"""Values whose reading is a convention: an odd root written as a power, b**(p/q) with q odd.

At a negative base the power is the real root (∛(-8) = -2, the curriculum's reading of a written root) or
SymPy's principal complex value (2·e^{iπ/3} = 1 + √3 i). The comparison engine read it both ways: the
exact symbolic path on the principal branch, the numeric one through `numeric.real_odd_roots`, so
(-8)**(1/3) was certified equal to -2 and to 1 + √3 i (fourth audit of 1 Oct 2026, CAP-C1). A comparison
that meets such a power is made under both readings and decided only when they agree (DECISIONS §80).
Written roots (`cbrt`, `root`, ∛) parse to sign(b)·|b|**(1/q) (normalize.parse._real_root): their base is
never negative and they carry no convention.
"""
from __future__ import annotations

from typing import Any

import sympy as sp

__all__ = ["odd_root_powers", "closed_readings", "open_odd_root_bases"]


def odd_root_powers(e) -> list:
    """The powers b**(p/q) of `e` with q odd and p/q not an integer whose base is not proved >= 0."""
    if not isinstance(e, sp.Basic) or not e.has(sp.Pow):
        return []
    out = []
    for n in sp.preorder_traversal(e):
        if isinstance(n, sp.Pow):
            ex = n.exp
            # a base that is not real has the principal value only (`numeric.real_odd_roots` leaves it):
            # the roots of x**3 - 3x + 1 in Cardano's form are no convention
            if isinstance(ex, sp.Rational) and not ex.is_Integer and ex.q % 2 == 1 \
                    and n.base.is_extended_nonnegative is not True and n.base.is_extended_real is not False:
                out.append(n)
    return out


def _principal(e):
    """`e` with each odd root of a negative number written as its principal value, |b|**r·e^{iπr}, a
    form `numeric.real_odd_roots` leaves alone; None when the sign of such a base is not decided."""
    reps = {}
    for p in odd_root_powers(e):
        b, r = p.base, p.exp
        if not b.is_number:
            return None
        if b.is_negative is not True:
            return None
        reps[p] = sp.Pow(-b, r) * sp.exp(sp.I * sp.pi * r)
    return e.xreplace(reps) if reps else e


def closed_readings(*items) -> tuple[list, list] | None | bool:
    """For operands with an odd root of a negative NUMBER: (the operands under the real reading, under the
    principal reading); None when there is none (nothing to read twice); False when such a base's sign
    is not decided (the comparison is then undecided)."""
    from .numeric import real_odd_roots
    if not any(p.base.is_number for it in items for p in odd_root_powers(it)):
        return None
    real, principal = [], []
    for it in items:
        pr = _principal(it) if any(p.base.is_number for p in odd_root_powers(it)) else it
        if pr is None:
            return False
        real.append(real_odd_roots(it))
        principal.append(pr)
    return real, principal


def open_odd_root_bases(items, domain: dict[Any, sp.Set] | None) -> list:
    """The bases with free symbols of odd roots in `items` that may be negative on `domain` (a dict symbol
    -> set): there the value is a convention. A base proved >= 0 on the domain (one symbol, solved
    exactly) is left out."""
    out = []
    for it in items:
        for p in odd_root_powers(it):
            b = p.base
            if not b.free_symbols:
                continue
            fs = b.free_symbols
            if domain is not None and len(fs) == 1:
                (v,) = tuple(fs)
                dom = domain.get(v) if isinstance(domain, dict) else None
                if dom is not None:
                    try:
                        from ..sandbox.exactsets import exact_solveset
                        # guarded: sin(x) < 0 read on one period of ℝ is empty on [7, 12] (it is not)
                        neg = exact_solveset(sp.Lt(b, 0), v, dom)
                        if neg.is_empty is True:
                            continue
                    except Exception:  # noqa: BLE001
                        pass
            out.append(b)
    return out
