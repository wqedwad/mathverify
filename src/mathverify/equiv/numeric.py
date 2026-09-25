"""Numeric equivalence with RELATIVE tolerance and a precision ladder (E3, E9).

Never a fixed 1e-12 absolute threshold (handoff §11/3). Precision is increased when
the comparison is inconclusive; a difference that is stable across precisions is a
genuine difference.
"""
from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp

__all__ = ["num_equal", "to_mp", "certified_sign", "exact_equal", "exact_zero_test", "has_float",
           "real_odd_roots", "NONREAL", "certified_integer"]

DPS_LADDER = (30, 50, 80)

# ---------------------------------------------------------------------------
# certified signs and exact equality (audit of 25 Sep 2026)
# ---------------------------------------------------------------------------
# A relation between two EXACT numbers is a fact about exact numbers, and a tolerance cannot
# decide it. Measured before these helpers existed: at x = 1 + √2 the exactly-zero quantity
# x² − 2x − 1 evaluated to −3.5e-192 at 40 digits, so `x² − 2x − 1 ≥ 0` came out False and
# `< 0` True; the correct answer (1 − √2, 1 + √2) to x² − 2x − 1 < 0 was refuted and the empty
# set was certified as the solution of √(x² − 2x − 1) = 0. And the last rung of the precision
# ladder (80 digits) accepted a relative gap below 1e-70 as equality, so √(10¹⁰⁰ + 1) = 10⁵⁰,
# tanh(100) = 1 and a 75-digit decimal for π were certified CORRECT.
#
# A sign is certified by SymPy's adaptive evalf in `strict` mode (it raises instead of returning a
# value it cannot distinguish from zero), and a ZERO only by an exact method: a CAS rewrite to 0,
# or the minimal polynomial (for an algebraic number it is `t` exactly when the number is 0).
# Anything else is undecided — the caller abstains.
NONREAL = "nonreal"
_SIGN_DPS = 30


def has_float(*es) -> bool:
    for e in es:
        if isinstance(e, float):
            return True
        try:
            if sp.sympify(e).has(sp.Float):
                return True
        except (sp.SympifyError, TypeError):
            return True
    return False


def exact_zero_test(d) -> bool | None:
    """Sandbox worker: True when `d` is PROVABLY 0, False when provably nonzero, None undecided.
    Only exact methods: CAS rewrites that reach 0, and the minimal polynomial."""
    d = sp.sympify(d)
    if d == 0:
        return True
    for fn in (sp.expand, lambda e: sp.cancel(sp.together(e)), sp.radsimp, sp.simplify,
               lambda e: sp.expand_log(e, force=False), sp.logcombine, sp.trigsimp,
               lambda e: sp.simplify(e.rewrite(sp.exp)), sp.expand_complex):
        try:
            r = fn(d)
        except Exception:  # noqa: BLE001
            continue
        if r == 0 or (getattr(r, "is_number", False) and r.is_zero is True):
            return True
    try:
        t = sp.Dummy("t")
        m = sp.minimal_polynomial(d, t)
        return bool(sp.expand(m - t) == 0)
    except Exception:  # noqa: BLE001 - NotAlgebraic, …
        return None


def _evalf_strict(e):
    """(real part, imaginary part) of a constant with every nonzero part certified, or None."""
    from sympy.core.evalf import PrecisionExhausted
    try:
        v = e.evalf(_SIGN_DPS, strict=True)
    except PrecisionExhausted:
        return None
    except Exception:  # noqa: BLE001
        return None
    if not getattr(v, "is_number", False) or v.has(sp.nan, sp.zoo):
        return None
    try:
        re_, im_ = v.as_real_imag()
    except Exception:  # noqa: BLE001
        return None
    if not (re_.is_number and im_.is_number):
        return None
    return re_, im_


def certified_sign(e, timeout: float = 5.0):
    """Sign of a constant: -1, 0 or 1 when certified, NONREAL when it is certainly not real,
    None when it cannot be decided. Never a sign read off rounding noise."""
    try:
        e = sp.sympify(e)
    except (sp.SympifyError, TypeError):
        return None
    if getattr(e, "free_symbols", None):
        return None
    if e.has(sp.nan, sp.zoo):
        return None
    if e is sp.oo:
        return 1
    if e is sp.S.NegativeInfinity:
        return -1
    if e.has(sp.oo, sp.S.NegativeInfinity):
        return None
    if isinstance(e, sp.Rational):
        return int(sp.sign(e))
    e = real_odd_roots(e)
    parts = _evalf_strict(e)
    if parts is not None:
        re_, im_ = parts
        if im_ != 0:
            return NONREAL
        if re_ != 0:
            return 1 if re_ > 0 else -1
        if e.is_zero is True:
            return 0
    from ..sandbox import run as sb_run
    r = sb_run("mathverify.equiv.numeric:exact_zero_test", e, timeout=timeout)
    if r.ok and r.value is True:
        return 0
    return None


def exact_equal(a, b, timeout: float = 5.0) -> bool | None:
    """Exact equality of two constants: True only when a − b is PROVED to be 0, False when a
    certified evaluation separates them, None otherwise."""
    try:
        a, b = sp.sympify(a), sp.sympify(b)
    except (sp.SympifyError, TypeError):
        return None
    if a == b:
        return True
    try:
        d = a - b
    except Exception:  # noqa: BLE001
        return None
    s = certified_sign(d, timeout=timeout)
    if s is None:
        return None
    return s == 0


def certified_integer(c, timeout: float = 5.0):
    """(True, k) when the constant c is PROVED to equal the integer k, (False, None) when it is
    certainly not an integer, (None, None) when undecided. `is_integer` of an expression such as
    log(8)/log(2) is None, and treating None as "not an integer" dropped the only solution of
    x·log 2 = log 8 from an integer count (audit of 25 Sep 2026)."""
    try:
        c = sp.sympify(c)
    except (sp.SympifyError, TypeError):
        return None, None
    if isinstance(c, sp.Integer):
        return True, c
    if isinstance(c, sp.Rational):
        return False, None
    if getattr(c, "free_symbols", None) or c.has(sp.oo, sp.S.NegativeInfinity, sp.zoo, sp.nan):
        return None, None
    if c.is_integer is False:
        return False, None
    parts = _evalf_strict(real_odd_roots(c))
    if parts is None:
        return None, None
    re_, im_ = parts
    if im_ != 0:
        return False, None
    k = sp.Integer(int(sp.floor(re_ + sp.Rational(1, 2))))    # nearest integer to the value
    s = certified_sign(c - k, timeout=timeout)
    if s == 0:
        return True, k
    if s in (-1, 1):
        # c != k and |c - k| < 1 (certified): no other integer is that close
        far = certified_sign(sp.Abs(c - k) - 1, timeout=timeout)
        return (False, None) if far == -1 else (None, None)
    return None, None


def real_odd_roots(e):
    """Odd roots read as REAL roots, the curriculum's convention: ∛(−8) = −2, x^(2/3) = ∛(x²).

    SymPy's x**(1/3) is the principal complex root, so ∛(−8) evaluated to 1 + 1.73i. The domain
    rules (`definedness_conditions`) and the z3 translation already treat an odd root as defined
    for negative bases; evaluating it on the principal branch contradicted them: the right answer
    ∛(−8) = −2 was refuted and x^(1/3) + 2 = 0 was certified to have no solution (audit of
    25 Sep 2026). A negative base becomes (−1)^p·|b|^(p/q); a base of unknown sign becomes
    sign(b)^p·|b|^(p/q)."""
    try:
        e = sp.sympify(e)
    except (sp.SympifyError, TypeError):
        return e
    if not getattr(e, "has", None) or not e.has(sp.Pow):
        return e

    def rewrite(p):
        b, ex = p.base, p.exp
        if not (isinstance(ex, sp.Rational) and not ex.is_Integer and ex.q % 2 == 1):
            return p
        if b.is_nonnegative:
            return p
        if b.is_negative:
            return sp.Pow(-b, ex) if ex.p % 2 == 0 else -sp.Pow(-b, ex)
        if b.is_extended_real is False:
            return p
        # even p: the real root of b^p is |b|^(p/q) (both vanish at b = 0); odd p: sign(b)·|b|^(p/q)
        return sp.Pow(sp.Abs(b), ex) if ex.p % 2 == 0 else sp.sign(b) * sp.Pow(sp.Abs(b), ex)

    return e.replace(lambda n: isinstance(n, sp.Pow), rewrite)


def to_mp(expr, dps: int):
    """Evaluate a constant sympy expression to mpf/mpc at `dps` digits. Raises on failure."""
    with mp.workdps(dps):
        if isinstance(expr, (int, float)):
            return mp.mpmathify(expr)
        expr = real_odd_roots(sp.sympify(expr))
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
    # Two EXACT constants and no declared tolerance: equality is a fact about exact numbers and
    # is decided exactly (see certified_sign). Agreement at every rung was still accepted as
    # equality, and the 80-digit rung passes any relative gap below 1e-70: √(10¹⁰⁰ + 1) = 10⁵⁰,
    # tanh(100) = 1, atan(10⁸⁰) = π/2 and a 75-digit decimal for π were certified CORRECT
    # (audit of 25 Sep 2026). When neither a proof of zero nor a certified difference exists,
    # the answer is None — the caller abstains.
    if strict and not has_float(a, b):
        try:
            sa, sb = sp.sympify(a), sp.sympify(b)
            exact_ok = not (sa.free_symbols or sb.free_symbols) and not any(
                x_.has(sp.oo, sp.S.NegativeInfinity, sp.zoo, sp.nan) for x_ in (sa, sb))
        except (sp.SympifyError, TypeError, AttributeError):
            exact_ok = False
        if exact_ok:
            r = exact_equal(sa, sb)
            ev["decided_by"] = "exact" if r is not None else "exact_undecided"
            return r, ev
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
