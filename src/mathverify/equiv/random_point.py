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
import time
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
        if dom.is_finite_set:
            return sp.Integer(rng.choice(list(dom)))
        # an unbounded Range has no list (`Range(2, oo)`: ValueError, audit of 29 Sep 2026), and
        # SymPy's own indexing of it raises IndexError: the k-th element is computed
        k, step = rng.randint(0, 120), abs(dom.step)
        if dom.inf.is_finite:
            return sp.Integer(dom.inf + k * step)
        if dom.sup.is_finite:
            return sp.Integer(dom.sup - k * step)
        return None
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


def sample_points(domains: dict, n: int, seed: int, special: bool = False) -> list[dict]:
    """`n` random points of the domains. With special=True, deterministic probe points are
    appended: for each symbol in turn, small integers, half-integers and far points of its
    domain (the others held at the first random point). Random 6-decimal samples essentially
    never land on an integer or a boundary, which is where a wrong strict/non-strict step
    (`-2 < x` for x² − 5x − 14 ≤ 0) differs from the truth (audit of 25 Sep 2026, D2)."""
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
    if special and pts:
        base = pts[0]
        for sym, dom in domains.items():
            for v in _special_values(dom):
                pt = dict(base)
                pt[sym] = v
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


# Functions whose value can change abruptly (or stop being analytic) at isolated points. For an
# analytic expression, agreement on a sample with accumulation points pins the function down on
# the connected piece of its domain; for these it does not. Measured (audit of 25 Sep 2026): the
# samples lie in |x| ≤ 1000 with 6-decimal rationals and integers in [−60, 60], so
# floor(x) + floor(−x) = −1 (false at every integer), sign(x)² = 1 (false at 0),
# |x − 2025| + |x + 2025| = 4050 and Max(x, 1001) = 1001 (false far out) were certified CORRECT,
# and so were the antiderivative x²/2 + Max(x − 5000, 0) of x and the derivative
# 2x + Max(x − 1500, 0) of x² (calculus audit, C07).
_NONSMOOTH = (sp.Abs, sp.sign, sp.Max, sp.Min, sp.floor, sp.ceiling, sp.frac, sp.Mod,
              sp.Piecewise, sp.Heaviside, sp.re, sp.im, sp.arg, sp.conjugate)
_BREAKPOINT_LIMIT = 40
_CELL_LIMIT = 24
_PERIOD_LIMIT = 5000


def _nonsmooth(e) -> list:
    # gcd/lcm (normalize.parse) only have integer values: agreement at sampled points proves nothing
    # (gcd(n, 1000003) and 1 agree almost everywhere)
    return [n for n in sp.preorder_traversal(e)
            if isinstance(n, _NONSMOOTH) or type(n).__name__ in ("gcd", "lcm")]


def _in(dom, v) -> bool:
    try:
        return dom.contains(v) == True  # noqa: E712  (sympy tri-state)
    except Exception:  # noqa: BLE001
        return False


def _special_values(dom, far: bool = False) -> list:
    """Deterministic probe values: small integers and half-integers and, with far=True, far points
    (10³ … 10⁶ and their negatives, also with a rational offset), filtered by the domain."""
    vals = [sp.Integer(k) for k in range(-12, 13)]
    vals += [sp.Rational(k, 2) for k in (-5, -3, -1, 1, 3, 5)]
    if far:
        for v in (10 ** 3, 3 * 10 ** 3, 7 * 10 ** 3, 10 ** 4, 10 ** 5, 10 ** 6):
            v = sp.Integer(v)
            vals += [v, -v, v + sp.Rational(1, 3), -v - sp.Rational(1, 3)]
    return [v for v in vals if _in(dom, v)]


def _far_safe(e) -> bool:
    """Can `e` be substituted EXACTLY at |x| ~ 10⁶? Not with the variable in an exponent
    (2**x would become a 300 000-digit integer) or inside factorial/binomial/gamma."""
    if not getattr(e, "free_symbols", None):
        return True
    for p in e.atoms(sp.Pow):
        if p.exp.free_symbols:
            return False
    if e.has(sp.exp) and any(f.args[0].free_symbols for f in e.atoms(sp.exp)):
        return False
    bad = (sp.factorial, sp.binomial, sp.gamma, sp.RisingFactorial, sp.FallingFactorial, sp.factorial2)
    return not any(f.args and f.args[0].free_symbols for f in e.atoms(*bad))


def _breakpoints(exprs, sym, dom, timeout: float = 5.0) -> list | None:
    """Points where a non-smooth function in `exprs` can switch branch (exact, finite), or None
    when that set cannot be computed (floor/ceiling/Mod on an unbounded domain, a solver failure)."""
    from ..sandbox import run as sb_run
    eqs = []
    for e in exprs:
        for n in _nonsmooth(e):
            if isinstance(n, (sp.Abs, sp.sign, sp.Heaviside)):
                eqs.append(n.args[0])
            elif isinstance(n, (sp.Max, sp.Min)):
                args = list(n.args)
                eqs += [args[i] - args[j] for i in range(len(args)) for j in range(i + 1, len(args))]
            elif isinstance(n, sp.Piecewise):
                for _, cond in n.args:
                    for r in sp.preorder_traversal(cond):
                        if isinstance(r, sp.core.relational.Relational):
                            eqs.append(r.lhs - r.rhs)
            else:
                return None
    pts: list = []
    for g in eqs:
        if sym not in getattr(g, "free_symbols", set()):
            continue
        r = sb_run("mathverify.sandbox.ops:solveset_in", sp.Eq(g, 0), sym, sp.S.Reals, timeout=timeout)
        if not r.ok or not isinstance(r.value, sp.FiniteSet):
            return None
        for v in r.value.args:
            if not getattr(v, "is_number", False) or v.is_real is False:
                continue
            if not any(v == u for u in pts):
                pts.append(v)
        if len(pts) > _BREAKPOINT_LIMIT:
            return None
    return pts


_FORMS = (sp.Sum, sp.Product, sp.Integral, sp.Limit)
_MAX_TERMS = 2000
_FORM_CHECKS = 2          # points per comparison that may take `forms.checked_forms` (see _exact_counterexample)
_FORM_TIMEOUT = 4.0
_EVAL_TERMS = 200_000        # terms of finite sums/products lambdify may run through at one point
_EVAL_BUDGET = 20.0          # seconds of point evaluations per comparison (in this process)


def _terms_at(e, syms, pt) -> int:
    """How many terms the finite Sums/Products of `e` run through at `pt` (nested ones multiply;
    a range that is not a pair of integers there counts as one term)."""
    total = 1
    for n in sp.preorder_traversal(e):
        if isinstance(n, (sp.Sum, sp.Product)):
            for lim in n.limits:
                if len(lim) != 3:
                    continue
                try:
                    lo, hi = (sp.sympify(x_).subs({s_: pt[s_] for s_ in syms}, simultaneous=True) for x_ in lim[1:])
                except Exception:  # noqa: BLE001
                    continue
                if getattr(lo, "is_Integer", False) and getattr(hi, "is_Integer", False) and hi >= lo:
                    total *= int(hi - lo + 1)
    return total


def _written_out(e):
    """`e` with every finite Sum/Product at a point written out term by term (an exact value, not
    SymPy's closed form), or None when an unevaluated form is left. Taken by strict evalf instead,
    Σ_{k=1}^{2n} sin²(πk/2) at 48 sample points held one check for 180-330 s in the verifier's own
    process (second audit of 29 Sep 2026)."""
    for _ in range(8):
        inner = [n for n in sp.preorder_traversal(e) if isinstance(n, (sp.Sum, sp.Product))
                 and not any(isinstance(m, _FORMS) for a in n.args for m in sp.preorder_traversal(a))]
        if not inner:
            break
        reps = {}
        for n in inner:
            if len(n.limits) != 1:
                return None
            k, lo, hi = n.limits[0]
            if not (getattr(lo, "is_Integer", False) and getattr(hi, "is_Integer", False)) or hi - lo + 1 > _MAX_TERMS:
                return None
            terms = [n.function.subs(k, i) for i in range(int(lo), int(hi) + 1)]
            reps[n] = (sp.Add if isinstance(n, sp.Sum) else sp.Mul)(*terms) if terms else \
                (sp.S.Zero if isinstance(n, sp.Sum) else sp.S.One)
        e = e.xreplace(reps)
    return None if e.has(*_FORMS) else e


def _exact_counterexample(a, b, syms, pt, budget: list | None = None) -> dict[str, Any] | None | bool:
    """Is `pt` an EXACT counterexample? dict when it is, False when the two sides are equal
    there (or both undefined), None when undecided.

    `budget` (a one-element list, decremented): how many more points may take a closed form that
    cannot be written out (an integral, a finite sum of more than `_MAX_TERMS` terms) through
    `forms.checked_forms`, SymPy's value confirmed by numbers. Without it such a point was never
    decided, and a wrong claim for Integral(t² - 2t, (t, 0, x)) or Σ_{k=1}^{1000n} k stayed UNKNOWN
    (third audit of 30 Sep 2026, N6). A difference found that way must also stand clear of the
    numbers' tolerance."""
    from .numeric import certified_sign, exact_equal, real_odd_roots, to_mp, NONREAL
    via_forms = False
    try:
        da = real_odd_roots(a.subs(pt, simultaneous=True))
        db = real_odd_roots(b.subs(pt, simultaneous=True))
        if da.has(*_FORMS) or db.has(*_FORMS):
            wa, wb = _written_out(da), _written_out(db)
            if wa is None or wb is None:
                if not budget or budget[0] <= 0:
                    return None
                budget[0] -= 1
                from .forms import UnverifiedForm, checked_forms
                try:
                    wa, wb = checked_forms(da, _FORM_TIMEOUT), checked_forms(db, _FORM_TIMEOUT)
                except UnverifiedForm:
                    return None
                if wa.has(*_FORMS) or wb.has(*_FORMS):
                    return None
                via_forms = True
            da, db = wa, wb
    except Exception:  # noqa: BLE001
        return None
    und_a = da.has(sp.zoo, sp.nan) or da.has(sp.oo, -sp.oo)
    und_b = db.has(sp.zoo, sp.nan) or db.has(sp.oo, -sp.oo)
    point = {s_.name: str(pt[s_]) for s_ in syms}
    if und_a and und_b:
        return False
    if und_a != und_b:
        return {"point": point, "lhs": str(da), "rhs": str(db), "exact": "defined_on_one_side_only"}
    ra, rb = certified_sign(da), certified_sign(db)
    if ra is None or rb is None:
        return None
    if (ra == NONREAL) != (rb == NONREAL):
        return {"point": point, "lhs": str(da), "rhs": str(db), "exact": "real_on_one_side_only"}
    eq = exact_equal(da, db)
    if eq is None:
        return None
    if eq:
        return False
    if via_forms:
        # SymPy's value was confirmed only to the numbers' tolerance (1e-15 or finer): a difference
        # inside 1e-12 of the larger side (or of 1) is not one the numbers can vouch for
        try:
            va, vb = to_mp(da, 30), to_mp(db, 30)
        except Exception:  # noqa: BLE001
            return None
        with mp.workdps(30):
            if abs(va - vb) <= mp.mpf("1e-12") * max(abs(va), abs(vb), 1):
                return None
        return {"point": point, "lhs": str(da), "rhs": str(db), "exact": "values_differ", "via": "checked_forms"}
    return {"point": point, "lhs": str(da), "rhs": str(db), "exact": "values_differ"}


def _smooth_on_cell(e, sym, q):
    """`e` with every non-smooth function replaced by the analytic branch it takes at q (q is
    interior to a cell with no breakpoint, so that branch is the one on the whole cell)."""
    from .numeric import certified_sign, NONREAL

    def pick(n):
        if isinstance(n, sp.Abs):
            s = certified_sign(n.args[0].subs(sym, q))
            return None if s in (None, 0, NONREAL) else (n.args[0] if s > 0 else -n.args[0])
        if isinstance(n, sp.sign):
            s = certified_sign(n.args[0].subs(sym, q))
            return None if s in (None, 0, NONREAL) else sp.Integer(s)
        if isinstance(n, sp.Heaviside):
            s = certified_sign(n.args[0].subs(sym, q))
            return None if s in (None, 0, NONREAL) else sp.Integer(1 if s > 0 else 0)
        if isinstance(n, (sp.Max, sp.Min)):
            best = n.args[0]
            for c in n.args[1:]:
                s = certified_sign((c - best).subs(sym, q))
                if s in (None, NONREAL):
                    return None
                if (s > 0) == isinstance(n, sp.Max) and s != 0:
                    best = c
            return best
        if isinstance(n, sp.Piecewise):
            from ..certify.domain import relation_holds_at
            for val, cond in n.args:
                if cond is sp.true:
                    return val
                h = relation_holds_at(cond, sym, q)
                if h is None:
                    return None
                if h:
                    return val
            return None
        return None

    out = e
    for _ in range(8):                          # innermost first, until no non-smooth node is left
        nodes = _nonsmooth(out)
        if not nodes:
            return out
        inner = [n for n in nodes if not any(isinstance(m, _NONSMOOTH) for m in n.args
                                             for m in sp.preorder_traversal(m))]
        reps = {}
        for n in inner:
            r = pick(n)
            if r is None:
                return None
            reps[n] = r
        out = out.xreplace(reps)
    return None


def _cell_proof(a, b, sym, dom, ev) -> bool | None:
    """Univariate identity with Abs/sign/Max/Min/Piecewise: on each open cell between exact
    breakpoints every non-smooth function is one analytic branch, so the identity is proved
    there symbolically; at each breakpoint it is checked exactly."""
    from .symbolic import sym_equal
    bps = _breakpoints([a, b], sym, dom)
    if bps is None:
        ev["nonsmooth_proof"] = "breakpoints_not_computable"
        return None
    try:
        bps = sorted(bps, key=lambda v: float(sp.N(v, 30)))
    except Exception:  # noqa: BLE001
        return None
    if len(bps) + 1 > _CELL_LIMIT:
        ev["nonsmooth_proof"] = "too_many_cells"
        return None
    for bp in bps:
        if not _in(dom, bp):
            continue
        c = _exact_counterexample(a, b, [sym], {sym: bp})
        if c is None:
            ev["nonsmooth_proof"] = f"undecided_at_breakpoint_{bp}"
            return None
        if c is not False:
            ev["counterexample"] = c
            return False
    edges = [-sp.oo] + bps + [sp.oo]
    for lo, hi in zip(edges[:-1], edges[1:]):
        if lo == -sp.oo and hi == sp.oo:
            q = sp.Rational(1, 3)
        elif lo == -sp.oo:
            q = sp.floor(sp.N(hi, 30)) - sp.Rational(2, 3)
        elif hi == sp.oo:
            q = sp.ceiling(sp.N(lo, 30)) + sp.Rational(2, 3)
        else:
            q = sp.nsimplify(sp.N((lo + hi) / 2, 30), rational=True)
            if not (lo < q < hi):
                return None
        cell = sp.Intersection(sp.Interval.open(lo, hi), dom)
        if cell is sp.S.EmptySet:
            continue
        if not _in(dom, q):
            # the domain meets this cell but not at q: prove on the cell only if q's branch is
            # still the right one there -> not attempted, abstain
            ev["nonsmooth_proof"] = f"cell_probe_outside_domain_{lo}_{hi}"
            return None
        sa, sb_ = _smooth_on_cell(a, sym, q), _smooth_on_cell(b, sym, q)
        if sa is None or sb_ is None:
            ev["nonsmooth_proof"] = f"branch_undecided_on_({lo}, {hi})"
            return None
        # prove on the cell itself: x = lo + t, x = hi − t or x = lo + (hi − lo)·t/(1 + t), t > 0,
        # so the CAS knows the sign facts that hold there (log(x²) = 2·log(−x) needs x < 0)
        t = sp.Dummy("t", positive=True)
        if lo == -sp.oo:
            xt = hi - t
        elif hi == sp.oo:
            xt = lo + t
        else:
            xt = lo + (hi - lo) * t / (1 + t)
        ok, _ = sym_equal(sa.subs(sym, xt), sb_.subs(sym, xt))
        if ok is not True:
            ok, _ = sym_equal(sa, sb_)
        if ok is not True:
            ev["nonsmooth_proof"] = f"no_symbolic_proof_on_({lo}, {hi})"
            return None
    ev["nonsmooth_proof"] = f"cells_proved({len(bps) + 1})"
    return True


def _periodic_proof(a, b, n, ev) -> bool | None:
    """Integer variable: floor(P/m), ceiling(P/m) and Mod(P, m) with P an integer polynomial are
    rewritten through Mod(P, m), which has period m in n. If the part of a − b outside those Mod
    terms cancels, a − b is periodic with period lcm(m) and one period decides it exactly."""
    from .numeric import exact_equal
    d = sp.sympify(a - b)

    def as_mod(x):
        if isinstance(x, (sp.floor, sp.ceiling)):
            num, den = sp.fraction(sp.together(x.args[0]))
            if not (den.is_Integer and den > 0):
                return None
            if isinstance(x, sp.ceiling):
                num = -num
            try:
                P = sp.Poly(num, n)
            except sp.PolynomialError:
                return None
            if not all(c.is_Integer for c in P.coeffs()):
                return None
            fl = (num - sp.Mod(num, den)) / den
            return -fl if isinstance(x, sp.ceiling) else fl
        return x

    moduli: list = []
    for _ in range(4):
        reps = {}
        for x in _nonsmooth(d):
            if isinstance(x, (sp.floor, sp.ceiling)):
                r = as_mod(x)
                if r is None:
                    return None
                reps[x] = r
        if not reps:
            break
        d = d.xreplace(reps)
    for x in _nonsmooth(d):
        if not isinstance(x, sp.Mod):
            return None
        P, m = x.args
        if not (m.is_Integer and m > 0):
            return None
        try:
            poly = sp.Poly(P, n)
        except sp.PolynomialError:
            return None
        if not all(c.is_Integer for c in poly.coeffs()):
            return None
        moduli.append(int(m))
    if not moduli:
        return None
    L = int(sp.ilcm(*moduli)) if len(moduli) > 1 else moduli[0]
    if L > _PERIOD_LIMIT:
        return None
    mods = {x: sp.Dummy("m") for x in _nonsmooth(d)}
    outside = sp.expand(d.xreplace(mods))
    if n in outside.free_symbols:
        ev["nonsmooth_proof"] = "not_periodic"
        return None
    for k in range(L):
        eq = exact_equal(a.subs(n, k), b.subs(n, k))
        if eq is not True:
            if eq is False:
                ev["counterexample"] = {"point": {n.name: str(k)}, "exact": "values_differ"}
            return eq if eq is False else None
    ev["nonsmooth_proof"] = f"period_{L}_checked"
    return True


def random_point_equal(a, b, var, domain, seed: int = 0, n: int = 30, dps: int = 30,
                       require_real: bool = True) -> tuple[bool | None, dict[str, Any]]:
    """Compare a and b on random points of `domain`.

    var: a Symbol or an iterable of Symbols. domain: a sympy Set (applied to every var)
    or a dict {Symbol: Set}. domain=None raises ValueError (E4).

    Agreement on points is evidence only for analytic expressions. With a non-smooth function
    (Abs, sign, Max, Min, floor, ceiling, Mod, Piecewise, …) the answer is True only with a proof
    (_cell_proof for one real variable, _periodic_proof for one integer variable); otherwise
    None. Deterministic probe points (integers, half-integers, far points, breakpoints) are
    checked in addition to the random ones, and a counterexample found there is confirmed
    exactly before it counts.
    """
    if domain is None:
        raise ValueError("random_point_equal requires an explicit domain from the IR (E4)")
    from .numeric import real_odd_roots
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
    nonsmooth = bool(_nonsmooth(a) or _nonsmooth(b))
    pts = sample_points(domains, n, seed)
    if len(pts) < max(3, n // 3):
        ev["error"] = "could not sample enough points from domain"
        return None, ev
    ae, be = real_odd_roots(a), real_odd_roots(b)
    try:
        fa = sp.lambdify(syms, ae, "mpmath")
        fb = sp.lambdify(syms, be, "mpmath")
    except Exception as e:
        ev["error"] = f"lambdify: {e}"
        return None, ev
    tol = mp.mpf(10) ** (-(dps - 10))

    spent = [0.0]

    def disagree(pt) -> tuple[str, dict] | None:
        if _terms_at(a, syms, pt) > _EVAL_TERMS or _terms_at(b, syms, pt) > _EVAL_TERMS:
            # lambdify runs a finite sum term by term in this process: Σ_{k=0}^{100000} x^k/k! held
            # the verifier for minutes (fourth audit of 1 Oct 2026, S4). Not evaluated, not counted.
            return "both_undefined", {}
        t0 = time.monotonic()
        try:
            va, vb = _eval(fa, syms, pt, dps), _eval(fb, syms, pt, dps)
        finally:
            spent[0] += time.monotonic() - t0
        if va is None and vb is None:
            return "both_undefined", {}
        point = {s_.name: str(pt[s_]) for s_ in syms}
        if (va is None) != (vb is None):
            return "defined_on_one_side_only", {"point": point, "lhs": str(va), "rhs": str(vb)}
        if require_real and (isinstance(va, mp.mpc) != isinstance(vb, mp.mpc)):
            return "real_on_one_side_only", {"point": point, "lhs": str(va), "rhs": str(vb)}
        with mp.workdps(dps):
            scale = max(abs(va), abs(vb))
            diff = abs(va - vb)
            if scale != 0 and diff / scale > tol:
                return "values_differ", {"point": point, "lhs": mp.nstr(va, 15), "rhs": mp.nstr(vb, 15)}
        return None

    unconfirmed = 0
    budget = [_FORM_CHECKS]
    for pt in pts:
        if spent[0] > _EVAL_BUDGET:
            ev["evaluation_time_budget"] = True    # the points left are not evaluated
            break
        d = disagree(pt)
        if d is not None and d[0] == "both_undefined":
            continue                      # both undefined here: uninformative
        if d is not None:
            # a numeric disagreement is a counterexample only when the exact values confirm it
            # (principle 5): "undefined" may only mean that mpmath cannot evaluate an operation
            # (gcd(n, n + 1) = 1 was refuted at n = 109), and "values differ" may be cancellation:
            # arccot(x) = atan(1/x) for x > 0 was refuted with a residue of 2e-31 (audit of
            # 29 Sep 2026)
            c = _exact_counterexample(a, b, syms, pt, budget)
            if isinstance(c, dict):
                ev["evaluated"] += 1
                ev["counterexample"] = c
                ev["reason"] = f"exact_{c['exact']}"
                return False, ev
            unconfirmed += c is None
            if c is False:
                ev["evaluated"] += 1
                ev["agreed"] += 1
            continue
        ev["evaluated"] += 1
        ev["agreed"] += 1
    if unconfirmed:
        ev["unconfirmed_points"] = unconfirmed
    if ev["evaluated"] < max(3, n // 3):
        ev["error"] = "too few evaluable points"
        return None, ev
    # deterministic probes: integers, half-integers, far points, breakpoints (one variable
    # probed at a time, the others held at the first random sample); confirmed exactly
    probes: list[dict] = []
    base = pts[0]
    far = _far_safe(a) and _far_safe(b)
    for s_ in syms:
        vals = _special_values(domains[s_], far=far)
        if nonsmooth and len(syms) == 1:
            bps = _breakpoints([a, b], s_, domains[s_]) or []
            for bp in bps:
                for off in (0, sp.Rational(1, 1000), -sp.Rational(1, 1000)):
                    v = bp + off
                    if _in(domains[s_], v):
                        vals.append(v)
        for v in vals:
            pt = dict(base)
            pt[s_] = v
            probes.append(pt)
    ev["probes"] = len(probes)
    for pt in probes:
        if spent[0] > _EVAL_BUDGET:
            ev["evaluation_time_budget"] = True
            ev["reason"] = "probes_not_evaluated_in_time"
            return None, ev
        d = disagree(pt)
        if d is None or d[0] == "both_undefined":
            continue
        c = _exact_counterexample(a, b, syms, pt)
        if isinstance(c, dict):
            ev["counterexample"] = c
            ev["reason"] = f"probe_{c['exact']}"
            return False, ev
    if nonsmooth:
        proof = None
        if len(syms) == 1:
            s_ = syms[0]
            dom = domains[s_]
            if dom.is_subset(sp.S.Integers):
                proof = _periodic_proof(a, b, s_, ev)
                if proof is None:
                    proof = _cell_proof(a, b, s_, sp.S.Reals, ev)
            else:
                proof = _cell_proof(a, b, s_, dom, ev)
        if proof is False:
            ev["reason"] = "nonsmooth_counterexample"
            return False, ev
        if proof is not True:
            ev["reason"] = "nonsmooth_without_proof"
            ev.setdefault("nonsmooth_proof", "multivariate" if len(syms) > 1 else "none")
            return None, ev
        return True, ev
    # Agreement within tolerance is not yet equality. Evaluating each side and subtracting can
    # only see differences above the working precision; the DIFFERENCE itself, evaluated by
    # SymPy's adaptive evalf, is computed to relative precision and reveals any difference at
    # all. Measured: 1/(x−1) and 1/(x−1) + e^(−1000) agreed at every point (the gap is
    # 1e-435) and were declared equal. A true identity evaluates to 0, or to a zero with no
    # significant bits ("0.e-167", _prec ≈ 1); a real difference carries ~100 bits.
    witness, unsure = _definite_nonzero_difference(ae - be, syms, pts[:8], a, b, budget)
    if witness is not None:
        ev["counterexample"] = witness
        ev["reason"] = "difference_below_working_precision_but_nonzero"
        return False, ev
    if unsure:
        ev["unconfirmed_difference_points"] = unsure
        ev["reason"] = "difference_below_working_precision_not_confirmed"
        return None, ev
    if unconfirmed:
        ev["reason"] = "disagreement_not_confirmed_exactly"
        return None, ev
    return True, ev


def _definite_nonzero_difference(d, syms, pts, a, b, budget: list | None = None) -> tuple[dict[str, Any] | None, int]:
    """(witness, number of unconfirmed points): a point where a and b differ, decided by their EXACT
    values there (`_exact_counterexample`). No evalf of the difference decides anything. Strict evalf
    gave 1.6e-35 for Σ_{k=1}^{436} cos(kπ/2), which is 0, and all six full-period trig sums of the third
    audit were refuted (30 Sep 2026, N4). A zero with no significant bits ('0.e-168') is no proof of
    equality: evalf follows a cancellation only so far, and 1 - tanh(100x) at x = 15 (2e-1303) and
    Σ_{k=0}^{5000} a^k - 1/(1 - a) came out that way, so tanh(100x) -> 1 and the infinite series' value
    were certified (fourth audit of 1 Oct 2026, S5); evalf even returns an exact 0 for log(1 + 15/10^600),
    which rounds to log(1). And evalf of a sum it cannot write out held the verifier for minutes in its
    own process (S4); the exact check takes such a sum only through `forms.checked_forms`, in the
    sandbox. A point the exact values call equal is no witness; one they cannot decide is counted, and
    the caller abstains (principle 5)."""
    try:
        d = sp.sympify(d)
    except (sp.SympifyError, TypeError):
        return None, 0
    unsure = 0
    for pt in pts:
        try:
            dp = d.subs({s_: pt[s_] for s_ in syms}, simultaneous=True)
            if dp.has(*_FORMS):
                w = _written_out(dp)
                dp = dp if w is None else w
        except Exception:  # noqa: BLE001
            unsure += 1
            continue
        if dp == 0:
            continue                          # exactly 0 at this point
        c = _exact_counterexample(a, b, syms, pt, budget)
        if isinstance(c, dict):
            return {"point": {s_.name: str(pt[s_]) for s_ in syms}, "exact": c["exact"]}, unsure
        unsure += c is None
    return None, unsure
