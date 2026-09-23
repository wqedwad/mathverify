"""Numeric equivalence with RELATIVE tolerance and a precision ladder (E3, E9).

Never a fixed 1e-12 absolute threshold (handoff §11/3). Precision is increased when
the comparison is inconclusive; a difference that is stable across precisions is a
genuine difference.
"""
from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp

__all__ = ["num_equal", "to_mp"]

DPS_LADDER = (30, 50, 80)


def to_mp(expr, dps: int):
    """Evaluate a constant sympy expression to mpf/mpc at `dps` digits. Raises on failure."""
    with mp.workdps(dps):
        if isinstance(expr, (int, float)):
            return mp.mpmathify(expr)
        expr = sp.sympify(expr)
        if expr.free_symbols:
            raise ValueError(f"expression has free symbols: {expr.free_symbols}")
        if expr.has(sp.Integral, sp.Derivative, sp.Limit, sp.Sum, sp.Product):
            expr = expr.doit()
        if expr is sp.nan or expr is sp.zoo:
            raise ValueError("nan/zoo")
        if expr in (sp.oo, -sp.oo):
            return mp.inf if expr is sp.oo else -mp.inf
        # arbitrary-precision evalf first (lambdify would go through double-precision
        # Python complex for constants such as I**I — measured: only 15 digits)
        n = sp.N(expr, dps + 5)
        if n.has(sp.zoo, sp.nan):
            raise ValueError("nan/zoo")
        if n in (sp.oo, -sp.oo):
            return mp.inf if n is sp.oo else -mp.inf
        re_, im_ = n.as_real_imag()
        re_n, im_n = sp.N(re_, dps + 5), sp.N(im_, dps + 5)
        if not (re_n.is_number and im_n.is_number) or re_n.free_symbols or im_n.free_symbols:
            raise ValueError(f"could not evaluate {expr} numerically")
        try:
            v = mp.mpc(mp.mpf(str(re_n)), mp.mpf(str(im_n)))
        except Exception as e:  # pragma: no cover
            raise ValueError(f"mpmath conversion failed for {n}: {e}") from e
        if abs(v.imag) <= mp.mpf(10) ** (-(dps - 6)) * max(1, abs(v.real)):
            v = v.real
        return v


def _rel_diff(a, b):
    diff = abs(a - b)
    scale = max(abs(a), abs(b))
    if scale == 0:
        return mp.mpf(0)
    return diff / scale


def num_equal(a, b, rel_tol: float | None = None, abs_tol: float | None = None,
              dps_ladder=DPS_LADDER) -> tuple[bool | None, dict[str, Any]]:
    """Return (True|False|None, evidence).

    rel_tol: caller-declared tolerance (e.g. a problem that asks for 2 decimals). When
    None, the effective tolerance is 10^-(dps-10) at each rung of the ladder, i.e. the
    comparison is 'exact up to working precision'.
    """
    ev: dict[str, Any] = {"ladder": [], "rel_tol": rel_tol, "abs_tol": abs_tol}
    # Exact numbers are compared exactly. Measured: 10^30 + 1 and 10^30 were declared equal,
    # because their relative difference (1e-30) sits below the first rung's tolerance.
    try:
        sa, sb = sp.sympify(a), sp.sympify(b)
        if isinstance(sa, sp.Rational) and isinstance(sb, sp.Rational):
            ev["decided_by"] = "exact_rational"
            return bool(sa == sb), ev
    except (sp.SympifyError, TypeError):
        pass
    prev_rel = None
    # Without a declared tolerance, EQUALITY must survive every rung: a true identity's
    # computed difference is rounding noise that shrinks as precision grows, a genuine small
    # difference does not. Stopping at the first rung that looked equal is how
    # e^(π√163) (= 262537412640768743.99999999999925…) was certified equal to the integer
    # 262537412640768744: relative gap 3e-30, under the 30-digit tolerance of 1e-20.
    strict = rel_tol is None and abs_tol is None
    passed_rungs = 0
    # inputs that are already finite-precision Floats cannot be compared tighter than
    # their own precision (a 15-digit Float vs pi: at most ~1e-15 agreement is possible)
    float_digits = [int(f._prec * 0.30103) for e in (a, b) if hasattr(e, "atoms")
                    for f in sp.sympify(e).atoms(sp.Float)]
    if float_digits:
        lim = mp.mpf(10) ** (-(min(float_digits) - 3))
        rel_tol = max(float(lim), rel_tol or 0.0)
        ev["float_precision_floor"] = mp.nstr(lim, 3)
    for dps in dps_ladder:
        try:
            va, vb = to_mp(a, dps), to_mp(b, dps)
        except Exception as e:
            ev["error"] = f"{type(e).__name__}: {e}"
            return None, ev
        with mp.workdps(dps):
            if (va in (mp.inf, -mp.inf)) or (vb in (mp.inf, -mp.inf)):
                same = (va == vb)
                ev["ladder"].append({"dps": dps, "a": str(va), "b": str(vb)})
                return bool(same), ev
            rel = _rel_diff(va, vb)
            absd = abs(va - vb)
            eff = mp.mpf(10) ** (-(dps - 10))
            if rel_tol is not None:
                eff = max(eff, mp.mpf(rel_tol))
            ev["ladder"].append({"dps": dps, "a": mp.nstr(va, 20), "b": mp.nstr(vb, 20),
                                 "rel_diff": mp.nstr(rel, 5), "eff_tol": mp.nstr(eff, 5)})
            if abs_tol is not None and absd <= mp.mpf(abs_tol):
                ev["decided_by"] = "abs_tol"
                return True, ev
            if rel <= eff:
                if not strict:
                    ev["decided_by"] = f"rel<=tol@dps{dps}"
                    return True, ev
                passed_rungs += 1
                if passed_rungs == len(dps_ladder):
                    ev["decided_by"] = f"rel<=tol at every rung (dps {dps_ladder})"
                    return True, ev
                prev_rel = rel
                continue
            if passed_rungs:
                # equal at a lower precision, different at this one: a genuine tiny difference
                ev["decided_by"] = f"difference_emerged@dps{dps}"
                return False, ev
            if rel > mp.mpf("1e-6"):
                ev["decided_by"] = f"clearly_different@dps{dps}"
                return False, ev
            # inconclusive: is the difference stable across precisions?
            if prev_rel is not None and mp.nstr(prev_rel, 3) == mp.nstr(rel, 3):
                ev["decided_by"] = "stable_difference"
                return False, ev
            prev_rel = rel
    ev["decided_by"] = "ladder_exhausted"
    return None, ev
