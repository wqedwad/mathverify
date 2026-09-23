"""Domain-aware random point equivalence test (E4).

The sampling domain is an explicit sympy Set that MUST come from the problem IR.
Passing None raises: deriving the domain from the expressions is exactly the trap
that made sqrt(x^2) == x look true on positive samples.

Semantics: a point where the two sides differ (or exactly one side is undefined /
non-real) is a counterexample => False. All sampled points agree => True (for
polynomial identities this is Schwartz–Zippel-strong; otherwise it is strong
evidence and the caller lowers confidence). Too few evaluable points => None.
"""
from __future__ import annotations

import random
from typing import Any

import mpmath as mp
import sympy as sp
from sympy import S, Interval, FiniteSet, Union, Intersection, Complement, ConditionSet, oo

__all__ = ["random_point_equal", "sample_points"]


def _sample_interval(iv: Interval, rng: random.Random, integer: bool = False):
    lo, hi = iv.inf, iv.sup
    lo_f = -1e3 if lo == -oo else float(lo)
    hi_f = 1e3 if hi == oo else float(hi)
    if lo == -oo and hi == oo:
        # mixture of scales, both signs
        scale = rng.choice([1.0, 10.0, 1000.0, 0.01])
        v = rng.uniform(-scale, scale)
    else:
        if lo == -oo:
            lo_f = hi_f - rng.choice([1.0, 10.0, 1000.0])
        if hi == oo:
            hi_f = lo_f + rng.choice([1.0, 10.0, 1000.0])
        v = rng.uniform(lo_f, hi_f)
    if integer:
        v = int(round(v))
        if lo != -oo and (v < lo or (iv.left_open and v == lo)):
            v = int(sp.ceiling(lo)) + (1 if iv.left_open and sp.ceiling(lo) == lo else 0)
        if hi != oo and (v > hi or (iv.right_open and v == hi)):
            v = int(sp.floor(hi)) - (1 if iv.right_open and sp.floor(hi) == hi else 0)
        return sp.Integer(v)
    # keep strictly inside open ends
    if iv.left_open and lo != -oo and v <= lo_f:
        v = lo_f + (hi_f - lo_f) * 1e-3
    if iv.right_open and hi != oo and v >= hi_f:
        v = hi_f - (hi_f - lo_f) * 1e-3
    # exact rational sample (6 decimals): substitution into polynomial/rational expressions
    # is then exact and an identity never fails on Float rounding (measured on
    # x^2-5x-14 = (x-7)(x+2), which a Float sample 'refuted')
    q = sp.Rational(f"{v:.6f}")
    if iv.contains(q) != True:  # noqa: E712  (rounding pushed it onto an open endpoint)
        q = sp.Rational(f"{(lo_f + hi_f) / 2:.6f}") if (lo != -oo and hi != oo) else q + sp.Rational(1, 1000)
    return q


def _sample_one(dom, rng: random.Random, depth: int = 0):
    if depth > 6:
        return None
    if dom == S.Reals or dom == S.Complexes:
        return _sample_interval(Interval(-oo, oo), rng)
    if dom == S.Integers:
        return sp.Integer(rng.randint(-60, 60))
    if dom == S.Naturals:
        return sp.Integer(rng.randint(1, 120))
    if dom == S.Naturals0:
        return sp.Integer(rng.randint(0, 120))
    if isinstance(dom, Interval):
        return _sample_interval(dom, rng)
    if isinstance(dom, FiniteSet):
        return rng.choice(list(dom.args))
    if isinstance(dom, Union):
        return _sample_one(rng.choice(list(dom.args)), rng, depth + 1)
    if isinstance(dom, sp.Range):
        return sp.Integer(rng.choice(list(dom)))
    if isinstance(dom, (Intersection, Complement, ConditionSet)):
        # rejection sampling from a base set
        base = None
        if isinstance(dom, Intersection):
            for a in dom.args:
                if a in (S.Integers, S.Naturals, S.Naturals0):
                    base = a
                    break
            if base is None:
                base = dom.args[0]
        elif isinstance(dom, Complement):
            base = dom.args[0]
        else:
            base = dom.base_set
        for _ in range(50):
            p = _sample_one(base, rng, depth + 1)
            if p is None:
                return None
            try:
                if dom.contains(p) == True:  # noqa: E712  (sympy tri-state)
                    return p
            except Exception:
                continue
        return None
    # unknown set: try membership rejection on reals
    for _ in range(50):
        p = _sample_interval(Interval(-oo, oo), rng)
        try:
            if dom.contains(p) == True:  # noqa: E712
                return p
        except Exception:
            return None
    return None


def sample_points(domains: dict, n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    pts = []
    for _ in range(n):
        pt = {}
        ok = True
        for sym, dom in domains.items():
            v = _sample_one(dom, rng)
            if v is None:
                ok = False
                break
            pt[sym] = v
        if ok:
            pts.append(pt)
    return pts


def _eval(f, syms, pt, dps):
    with mp.workdps(dps):
        vals = []
        for s_ in syms:
            v = pt[s_]
            vals.append(mp.mpf(str(sp.N(v, dps + 5))))
        try:
            r = f(*vals)
        except (ZeroDivisionError, ValueError, TypeError, OverflowError, mp.libmp.NoConvergence):
            return None
        except Exception:
            return None
        if isinstance(r, (int, float)):
            r = mp.mpf(r)
        if isinstance(r, complex):
            r = mp.mpc(r)
        if not isinstance(r, (mp.mpf, mp.mpc)):
            try:
                r = mp.mpmathify(r)
            except Exception:
                return None
        if isinstance(r, mp.mpc):
            if abs(r.imag) <= mp.mpf(10) ** (-(dps - 8)) * max(1, abs(r.real)):
                return r.real
            return r
        if mp.isnan(r) or mp.isinf(r):
            return None
        return r


def random_point_equal(a, b, var, domain, seed: int = 0, n: int = 30, dps: int = 30,
                       require_real: bool = True) -> tuple[bool | None, dict[str, Any]]:
    """Compare a and b on random points of `domain`.

    var: a Symbol or an iterable of Symbols. domain: a sympy Set (applied to every var)
    or a dict {Symbol: Set}. domain=None raises ValueError (E4).
    """
    if domain is None:
        raise ValueError("random_point_equal requires an explicit domain from the IR (E4)")
    syms = [var] if isinstance(var, sp.Symbol) else list(var)
    if isinstance(domain, dict):
        domains = {s_: domain[s_] for s_ in syms}
    else:
        domains = {s_: domain for s_ in syms}
    a, b = sp.sympify(a), sp.sympify(b)
    extra = (a.free_symbols | b.free_symbols) - set(syms)
    ev: dict[str, Any] = {"seed": seed, "n": n, "dps": dps, "domain": {str(k): str(v) for k, v in domains.items()},
                          "counterexample": None, "evaluated": 0, "agreed": 0}
    if extra:
        ev["error"] = f"unbound symbols {extra}; declare their domains"
        return None, ev
    pts = sample_points(domains, n, seed)
    if len(pts) < max(3, n // 3):
        ev["error"] = "could not sample enough points from domain"
        return None, ev
    try:
        fa = sp.lambdify(syms, a, "mpmath")
        fb = sp.lambdify(syms, b, "mpmath")
    except Exception as e:
        ev["error"] = f"lambdify: {e}"
        return None, ev
    tol = mp.mpf(10) ** (-(dps - 10))
    for pt in pts:
        va, vb = _eval(fa, syms, pt, dps), _eval(fb, syms, pt, dps)
        if va is None and vb is None:
            continue                      # both undefined here: uninformative
        ev["evaluated"] += 1
        point = {s_.name: str(pt[s_]) for s_ in syms}
        if (va is None) != (vb is None):
            ev["counterexample"] = {"point": point, "lhs": str(va), "rhs": str(vb)}
            ev["reason"] = "defined_on_one_side_only"
            return False, ev
        if require_real and (isinstance(va, mp.mpc) != isinstance(vb, mp.mpc)):
            ev["counterexample"] = {"point": point, "lhs": str(va), "rhs": str(vb)}
            ev["reason"] = "real_on_one_side_only"
            return False, ev
        with mp.workdps(dps):
            scale = max(abs(va), abs(vb))
            diff = abs(va - vb)
            if scale != 0 and diff / scale > tol:
                ev["counterexample"] = {"point": point, "lhs": mp.nstr(va, 15), "rhs": mp.nstr(vb, 15)}
                ev["reason"] = "values_differ"
                return False, ev
        ev["agreed"] += 1
    if ev["evaluated"] < max(3, n // 3):
        ev["error"] = "too few evaluable points"
        return None, ev
    # Agreement within tolerance is not yet equality. Evaluating each side and subtracting can
    # only see differences above the working precision; the DIFFERENCE itself, evaluated by
    # SymPy's adaptive evalf, is computed to relative precision and reveals any difference at
    # all. Measured: 1/(x−1) and 1/(x−1) + e^(−1000) agreed at every point (the gap is
    # 1e-435) and were declared equal. A true identity evaluates to 0, or to a zero with no
    # significant bits ("0.e-167", _prec ≈ 1); a real difference carries ~100 bits.
    witness = _definite_nonzero_difference(a - b, syms, pts[:8])
    if witness is not None:
        ev["counterexample"] = witness
        ev["reason"] = "difference_below_working_precision_but_nonzero"
        return False, ev
    return True, ev


def _definite_nonzero_difference(d, syms, pts) -> dict[str, Any] | None:
    try:
        d = sp.sympify(d)
    except (sp.SympifyError, TypeError):
        return None
    for pt in pts:
        try:
            v = sp.N(d.subs({s_: pt[s_] for s_ in syms}, simultaneous=True), 30)
        except Exception:  # noqa: BLE001
            continue
        if v == 0 or not getattr(v, "is_number", False):
            continue
        prec = getattr(v, "_prec", None)
        if prec is None:
            re_, im_ = v.as_real_imag()
            prec = min(getattr(re_, "_prec", 0) or 0, getattr(im_, "_prec", 0) or 0) \
                if re_ != 0 and im_ != 0 else getattr(re_ if re_ != 0 else im_, "_prec", 0)
        if prec and prec >= 50:
            return {"point": {s_.name: str(pt[s_]) for s_ in syms}, "difference": str(v)}
    return None
