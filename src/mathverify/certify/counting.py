"""Exact counting (E10): real roots, integers in a set, small brute force.

Every count is decided exactly (audit of 25 Sep 2026). Measured before on master, each of these
was certified CORRECT for a WRONG count:
  * count_roots read the auto-simplified expression and ignored where the problem's expression is
    undefined: x³/x "has 1 root" (x = 0 is not in its domain); the zero polynomial "had 0 roots";
  * count_solutions evaluated the givens with float `lambdify(..., "math")`: 1/x + 1/y = 1/6 on
    1..50 lost 2 of its 9 solutions, x/10 + y/10 = 3/10 lost all 4;
  * count_integers treated `is_integer is None` as "not an integer" and compared an open endpoint
    with an integer structurally: x·log 2 = log 8 "had no integer solution", and |x| < log 8/log 2
    "had 7".
"""
from __future__ import annotations

import itertools
from fractions import Fraction
from typing import Any

import sympy as sp
from sympy import S, Interval, FiniteSet, oo, And

from ..equiv import exact_integer
from ..equiv.numeric import (certified_sign, certified_floor, certified_integer, real_odd_roots,
                             NONREAL)
from ..equiv.sets import normalize_set
from ..sandbox import run as sb_run
from ..sandbox.exactsets import at_risk
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.counting"

# brute-force limits: exact Fraction arithmetic is cheap, a SymPy evaluation per point is not
_FRACTION_LIMIT = 400_000
_SYMPY_LIMIT = 20_000


def count_real_roots(expr, var, lo=-oo, hi=oo, distinct: bool = True) -> int:
    expr = sp.sympify(expr)
    try:
        p = sp.Poly(expr, var)
    except sp.PolynomialError as e:
        raise ValueError(f"not a polynomial in {var}: {e}") from e
    if not p.domain.is_Exact:
        # A root count of a polynomial with Float coefficients is not well defined near a
        # multiple root, and snapping the coefficients to "nice" numbers is a rounding (§3
        # rule 15). Measured: the old nsimplify branch counted 1 root for
        # x² − 0.6666666666666666x + 0.1111111111111111, whose discriminant is −4.2e-17 (no real
        # root as written). The parser turns every decimal into an exact rational, so the
        # verifier never gets here; any other caller gets a refusal, not a guess.
        raise ValueError(f"polynomial has inexact coefficients (domain {p.domain})")
    if p.free_symbols_in_domain:
        raise ValueError("polynomial has symbolic coefficients")
    if p.is_zero:
        # every real number is a root; Poly(0).count_roots() returns 0 (audit of 25 Sep 2026)
        raise ValueError("identically zero: infinitely many roots")
    if distinct:
        return int(p.count_roots(lo, hi))
    rr = p.real_roots()
    return sum(1 for r in rr if (lo == -oo or r >= lo) and (hi == oo or r <= hi))


def _poly_real_roots(num, var):
    """Sandbox worker: exact real roots of a polynomial, with multiplicity (rationals/CRootOf)."""
    return list(sp.Poly(num, var).real_roots())


# ---------------------------------------------------------------------------------------------
# count_roots
# ---------------------------------------------------------------------------------------------
def _count_roots(expr, var, lo, hi, distinct: bool, ctx: Ctx, ev: dict) -> tuple[int | None, str | None]:
    """Roots of the problem's expression AS WRITTEN: the zeros of the numerator of the
    (auto-simplified) rational form, minus every point where the denominator vanishes or a
    definedness condition — of the parsed expression or of the written one — fails."""
    from .domain import definedness_conditions, relation_holds_at, in_domain
    unbound = ctx.unapplied_conditions(var)
    if unbound:
        return None, f"condition_not_applied: {[str(u) for u in unbound][:3]}"
    # the variable's domain (its declared domain and constraints, the domain of discourse, the given
    # side conditions): the roots were counted on all of ℝ, so x² − 4 under x > 0 had 2 (part vi)
    dom = ctx.domain_for(var)
    conds_w, nowhere = ctx.written_conditions()
    if var in nowhere:
        ev["reason_detail"] = "expression_defined_nowhere"
        return 0, None
    expr = real_odd_roots(expr)
    try:
        num, den = sp.fraction(sp.together(expr))
        num = sp.expand(num)
    except Exception as e:  # noqa: BLE001
        return None, f"not_rational_in_var: {e}"
    if (num.free_symbols | den.free_symbols) - {var}:
        return None, "symbolic_coefficients"
    try:
        pn = sp.Poly(num, var)
        pd = sp.Poly(den, var)
    except sp.PolynomialError:
        return None, "not_a_rational_function_of_var"
    if not (pn.domain.is_Exact and pd.domain.is_Exact):
        return None, "inexact_coefficients"
    if pn.is_zero:
        # identically zero wherever defined: infinitely many roots unless the domain is finite
        ev["identically_zero"] = True
        return None, "identically_zero_expression_infinitely_many_roots"
    r = sb_run("mathverify.certify.counting:_poly_real_roots", num, var, timeout=ctx.timeout)
    if not r.ok:
        return None, f"root_isolation_failed: {r.error}"
    roots = list(r.value)
    conds = list(definedness_conditions(expr, var))
    conds += [c for c in conds_w if c.free_symbols <= {var} and c not in conds]
    kept: list = []
    rejected: list = []
    for rt in roots:
        if lo != -oo:
            s = certified_sign(rt - lo)
            if s is None or s == NONREAL:
                return None, f"interval_membership_undecided: {rt}"
            if s < 0:
                continue
        if hi != oo:
            s = certified_sign(hi - rt)
            if s is None or s == NONREAL:
                return None, f"interval_membership_undecided: {rt}"
            if s < 0:
                continue
        m = in_domain(dom, rt)
        if m is None:
            return None, f"domain_membership_undecided: {rt}"
        if m is False:
            rejected.append((str(rt), "outside_the_domain"))
            continue
        dv = certified_sign(den.subs(var, rt))
        if dv is None:
            return None, f"denominator_undecided: {rt}"
        if dv == 0:
            rejected.append((str(rt), "denominator_zero"))
            continue
        bad = None
        for c in conds:
            h = relation_holds_at(c, var, rt)
            if h is None:
                return None, f"definedness_undecided at {rt}: {c}"
            if h is False:
                bad = str(c)
                break
        if bad:
            rejected.append((str(rt), f"undefined: {bad}"))
            continue
        kept.append(rt)
    ev["roots_kept"] = [str(k) for k in kept]
    ev["roots_rejected"] = rejected
    if distinct:
        uniq: list = []
        for k in kept:
            if not any(k == u for u in uniq):
                uniq.append(k)
        return len(uniq), None
    return len(kept), None


# ---------------------------------------------------------------------------------------------
# count_integers
# ---------------------------------------------------------------------------------------------
def _count_in_interval(iv: Interval) -> int | None:
    lo, hi = iv.inf, iv.sup
    if lo == -oo or hi == oo:
        return None
    fl = certified_floor(lo)
    fh = certified_floor(hi)
    if fl is None or fh is None:
        return None
    lo_int = certified_sign(lo - fl) == 0
    hi_int = certified_sign(hi - fh) == 0
    a = fl if (lo_int and not iv.left_open) else fl + 1
    b = fh - 1 if (hi_int and iv.right_open) else fh
    return max(0, int(b - a + 1))


def _integer_points(pts) -> int | None:
    n = 0
    for p in pts:
        is_int, _ = certified_integer(p)
        if is_int is None:
            return None
        n += 1 if is_int else 0
    return n


def count_integers_in(sset: sp.Set) -> int | None:
    """Number of integers in a set, decided exactly; None when infinite or undecidable."""
    sset = sp.sympify(sset)
    if sset is S.EmptySet:
        return 0
    if isinstance(sset, sp.Range):
        try:
            return len(sset)
        except (TypeError, ValueError):
            return None
    if isinstance(sset, sp.Intersection):
        ints = [a for a in sset.args if a in (S.Integers, S.Naturals, S.Naturals0)]
        rest = [a for a in sset.args if a not in (S.Integers, S.Naturals, S.Naturals0)]
        if not ints or len(rest) != 1:
            return None
        base = rest[0]
        if S.Naturals in ints:
            base = sp.Intersection(base, Interval(1, oo))
        elif S.Naturals0 in ints:
            base = sp.Intersection(base, Interval(0, oo))
        if isinstance(base, sp.Intersection):
            return None
        return count_integers_in(base)
    if isinstance(sset, sp.Complement):
        a, b = sset.args
        if not isinstance(b, FiniteSet):
            return None
        total = count_integers_in(a)
        if total is None:
            return None
        from .domain import in_domain
        for p in b.args:
            is_int, _ = certified_integer(p)
            if is_int is None:
                return None
            if is_int:
                m = in_domain(a, p)
                if m is None:
                    return None
                total -= 1 if m else 0
        return total
    norm = normalize_set(sset)
    if norm is None:
        return None
    ivs, pts = norm
    total = 0
    for iv in ivs:
        n = _count_in_interval(iv)
        if n is None:
            return None
        total += n
    n = _integer_points(pts)
    if n is None:
        return None
    return total + n


def _interval_int_bounds(iv: Interval) -> tuple[int | None, int | None, bool]:
    """(first integer, last integer, ok) of an interval, certified; None for an unbounded side."""
    a = b = None
    if iv.inf != -oo:
        fl = certified_floor(iv.inf)
        if fl is None:
            return None, None, False
        on = certified_sign(iv.inf - fl) == 0
        a = int(fl) if (on and not iv.left_open) else int(fl) + 1
    if iv.sup != oo:
        fh = certified_floor(iv.sup)
        if fh is None:
            return None, None, False
        on = certified_sign(iv.sup - fh) == 0
        b = int(fh) - 1 if (on and iv.right_open) else int(fh)
    return a, b, True


def _dom_int_bounds(dom) -> tuple[int | None, int | None]:
    lo = hi = None
    try:
        if dom.inf != -oo and dom.inf.is_number:
            f = certified_floor(dom.inf)
            lo = int(f) if f is not None else None
        if dom.sup != oo and dom.sup.is_number:
            f = certified_floor(dom.sup)
            hi = int(f) + 1 if f is not None else None
    except Exception:  # noqa: BLE001
        return None, None
    return lo, hi


def _count_integers(ctx: Ctx, var, ev: dict) -> tuple[int | None, str | None]:
    """Integers k that satisfy every given and lie in the variable's domain. The CAS solution
    sets only propose WHERE to look; membership of each candidate is decided exactly, and each
    candidate is also checked against the relations themselves (a disagreement abstains).
    SymPy's own Interval ∩ Integers is not used: it compares irrational endpoints numerically and
    raised on |x| < log 8/log 2."""
    from .domain import in_domain, relation_holds_at
    # a symbol a given fixes is read as its value: solveset read the binding b = 0 on x as the empty
    # set, and every count with a binding was 0 (part vi, 30 Sep 2026)
    rels, unbound = ctx.on_var(ctx.givens(), var)
    unbound = ctx.unapplied_conditions(var) + unbound
    if unbound:
        return None, f"condition_not_applied: {[str(u) for u in unbound][:3]}"
    if not rels:
        return None, "no_givens"
    try:
        dom = ctx.domain_for(var)
    except Exception as e:  # noqa: BLE001
        return None, f"domain_failed: {type(e).__name__}"
    rels_r = [real_odd_roots(r) for r in rels]
    pieces: list = []
    # one relation at a time: solveset does not accept a conjunction
    for rel in rels_r:
        r = sb_run("mathverify.sandbox.ops:solveset_in", rel, var, S.Reals, timeout=ctx.timeout)
        # a trigonometric relation on ℝ stays a ConditionSet (sandbox.exactsets: SymPy's set was one
        # period, and 3 was certified for the integers of [0, 10] with sin x > 0, fourth audit G2):
        # it bounds no candidate, and each candidate's membership is decided at the point
        if not r.ok or (isinstance(r.value, sp.ConditionSet) and not at_risk(rel, var)):
            return None, "solveset_failed"
        pieces.append(r.value)
    ev["solution_sets"] = [str(p_) for p_ in pieces]
    # candidate range: the tightest integer bounds any single solution set gives on each side
    lows, highs = [], []
    dlo, dhi = _dom_int_bounds(dom)
    if dlo is not None:
        lows.append(dlo)
    if dhi is not None:
        highs.append(dhi)
    for p_ in pieces:
        n = normalize_set(p_)
        if n is None:
            continue
        ivs, pts = n
        plo: list = []
        phi: list = []
        good = True
        for iv in ivs:
            a_, b_, ok = _interval_int_bounds(iv)
            if not ok:
                good = False
                break
            plo.append(a_)
            phi.append(b_)
        for q in pts:
            f = certified_floor(q)
            if f is None:
                good = False
                break
            plo.append(int(f))
            phi.append(int(f) + 1)
        if not good:
            continue
        if not plo:                       # empty set: no integer at all
            lows.append(1)
            highs.append(0)
            continue
        if all(v is not None for v in plo):
            lows.append(min(plo))
        if all(v is not None for v in phi):
            highs.append(max(phi))
    if not lows or not highs:
        return None, "infinite_or_unsupported_set"
    lo_c, hi_c = max(lows), min(highs)
    if hi_c - lo_c + 1 > _SYMPY_LIMIT:
        return None, "candidate_range_too_large"
    cands = [sp.Integer(k) for k in range(lo_c, hi_c + 1)]
    seen: set = set()
    count = 0
    for k in cands:
        if k in seen:
            continue
        seen.add(k)
        indom = in_domain(dom, k)
        if indom is None:
            return None, f"domain_membership_undecided_at_{k}"
        if not indom:
            continue
        member = [in_domain(p_, k) for p_ in pieces]
        holds = [relation_holds_at(r, var, k) for r in rels_r]
        if any(m is None for m in member) or any(h is None for h in holds):
            return None, f"undecided_at_{k}"
        if all(member) != all(holds):
            return None, f"cas_unreliable: solution set and relation disagree at {k}"
        count += 1 if all(holds) else 0
    ev["candidates"] = len(seen)
    return count, None


# ---------------------------------------------------------------------------------------------
# count_solutions
# ---------------------------------------------------------------------------------------------
_FRACTION_FUNCS = (sp.Abs, sp.floor, sp.ceiling, sp.Mod, sp.Min, sp.Max, sp.Piecewise)


def _fraction_safe(e) -> bool:
    """Can `e` be evaluated EXACTLY with Python Fractions (rational arithmetic only)?"""
    if e.has(sp.Float) or e.atoms(sp.NumberSymbol) or e.has(sp.I):
        return False
    for p in e.atoms(sp.Pow):
        if not p.exp.is_Integer:
            return False
    for f in e.atoms(sp.Function):
        if not isinstance(f, _FRACTION_FUNCS):
            return False
    return True


def _fraction_predicate(rels, syms):
    from sympy.printing.pycode import PythonCodePrinter

    class _FracPrinter(PythonCodePrinter):
        def _print_Rational(self, e):
            return f"Fraction({e.p}, {e.q})"

        def _print_Half(self, e):
            return "Fraction(1, 2)"

    return sp.lambdify(syms, And(*rels) if len(rels) > 1 else rels[0],
                       modules=[{"Fraction": Fraction}, "math"], printer=_FracPrinter)


def _holds_exact(rel, point: dict) -> bool | None:
    from .domain import relation_holds_at
    if rel is sp.true:
        return True
    if rel is sp.false:
        return False
    if isinstance(rel, (sp.And, sp.Or)):
        parts = [_holds_exact(a, point) for a in rel.args]
        if isinstance(rel, sp.And):
            if any(p is False for p in parts):
                return False
            return True if all(p is True for p in parts) else None
        if any(p is True for p in parts):
            return True
        return False if all(p is False for p in parts) else None
    if not isinstance(rel, sp.core.relational.Relational):
        return None
    lhs = rel.lhs.subs(point, simultaneous=True)
    rhs = rel.rhs.subs(point, simultaneous=True)
    if lhs.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or rhs.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        return False                                   # undefined at this point: not a solution
    return relation_holds_at(type(rel)(lhs, rhs, evaluate=False), sp.Dummy("_d"), 0)


def _brute_force_count(givens, syms, bounds: dict[str, tuple[int, int]],
                       limit: int = _FRACTION_LIMIT, domains: dict | None = None) -> tuple[int | None, str]:
    """`domains`: a set of values per symbol (the domain of discourse), decided exactly per value."""
    from .domain import in_domain
    ranges = []
    size = 1
    for s_ in syms:
        lo, hi = bounds[s_.name]
        vals = range(int(lo), int(hi) + 1)
        d = (domains or {}).get(s_)
        if d is not None:
            if len(vals) > limit:
                return None, "search_space_too_large"
            member = [(k, in_domain(d, sp.Integer(k))) for k in vals]
            if any(m is None for _, m in member):
                return None, f"domain_membership_undecided_for_{s_.name}"
            vals = [k for k, m in member if m]
        ranges.append(vals)
        size *= len(ranges[-1])
    if not givens:
        return size, "no_constraints"
    rels = [real_odd_roots(g) for g in givens]
    if all(_fraction_safe(r) for r in rels):
        if size > limit:
            return None, "search_space_too_large"
        f = _fraction_predicate(rels, syms)
        cnt = 0
        for tup in itertools.product(*ranges):
            try:
                if f(*[Fraction(v) for v in tup]):
                    cnt += 1
            except (ZeroDivisionError, ValueError):
                continue                                  # undefined here: not a solution
        return cnt, "exact_fraction"
    if size > _SYMPY_LIMIT:
        return None, "search_space_too_large_for_exact_evaluation"
    cnt = 0
    for tup in itertools.product(*ranges):
        pt = {s_: sp.Integer(v) for s_, v in zip(syms, tup)}
        ok = True
        for r in rels:
            h = _holds_exact(r, pt)
            if h is None:
                return None, f"undecided_at_{tup}"
            if h is False:
                ok = False
                break
        cnt += 1 if ok else 0
    return cnt, "exact_sympy"


def _why_flags(why: str | None) -> list[str]:
    return ["condition_not_applied"] if (why or "").startswith("condition_not_applied") else []


def verify(ir, solution, ctx: Ctx):
    kind = ir.task.kind
    if kind not in ("count_roots", "count_integers", "count_solutions"):
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        ca = solution.claimed_answer
        try:
            raw = ca.payload if ca.kind == "count" else ctx.claimed(solution)
        except Exception as e:
            return unknown(LAYER, f"claimed_not_parsed: {e}", flags=["parse_error"])
        # A count is an integer. `int()` truncated a claimed 7/2 to 3 and certified it (measured
        # by harness/soundness_fuzz.py); a non-integer claim is simply a wrong count.
        claimed = exact_integer(raw)
        if claimed is None:
            return result(LAYER, "fail", 0.99, True, {"claimed": str(raw),
                          "reason": "claimed_count_is_not_an_integer"}, t.ms, primary=True)
        ev: dict[str, Any] = {"claimed": claimed}
        if kind == "count_roots":
            var = ctx.sym(p.get("var", "x"))
            expr, err = parse_or_unknown(LAYER, ctx.expr, p["expr"])
            if err:
                return err
            lo = ctx.expr(str(p["lo"])) if "lo" in p else -oo
            hi = ctx.expr(str(p["hi"])) if "hi" in p else oo
            truth, why = _count_roots(expr, var, lo, hi, p.get("distinct", True), ctx, ev)
            if truth is None:
                return unknown(LAYER, why or "count_failed", 0, ev, flags=_why_flags(why))
            ev["method"] = "exact_real_roots_with_written_definedness"
        elif kind == "count_integers":
            var = ctx.sym(p.get("var", "x"))
            truth, why = _count_integers(ctx, var, ev)
            if truth is None:
                return unknown(LAYER, why or "count_failed", 0, ev, flags=_why_flags(why))
            ev["method"] = "interval_integer_count"
        else:  # count_solutions: exact brute force over integer boxes
            syms = ctx.syms()
            bounds = {}
            for v in ir.vars:
                b = p.get("bounds", {}).get(v.name)
                if b is None:
                    return unknown(LAYER, f"no_bounds_for_{v.name}", 0, ev)
                lo_b, hi_b = exact_integer(ctx.expr(str(b[0]))), exact_integer(ctx.expr(str(b[1])))
                if lo_b is None or hi_b is None:
                    return unknown(LAYER, f"non_integer_bounds_for_{v.name}", 0, ev)
                bounds[v.name] = (lo_b, hi_b)
            rels = ctx.var_constraints() + ctx.givens()
            nowhere = ctx.written_conditions()[1] & set(syms)
            if nowhere:
                # an expression of the problem defined nowhere as written in a variable (sqrt(-x) with
                # x a positive integer folds away as sqrt(-x) - sqrt(-x)): no tuple counts. The closed
                # condition never reached var_constraints, and 3 was certified (fourth audit TAN-08)
                rels = rels + [sp.false]
            # the domain of discourse restricts each variable it mentions; it was not read here, so
            # x + y = 4 on x > 2 counted all 5 pairs of 0..4 (part vi, 30 Sep 2026)
            doms = {s_: d for s_ in syms if (d := ctx.discourse(s_)) != S.Reals}
            truth, how = _brute_force_count(rels, syms, bounds, domains=doms)
            if truth is None:
                flags = [] if how.startswith("domain_membership") else ["brute_force_limit"]
                return unknown(LAYER, how, 0, ev, flags=flags)
            ev["method"] = f"brute_force:{how}"
            ev["bounds"] = bounds
        ev["truth"] = truth
        ok = (truth == claimed)
    conf = 0.99
    return result(LAYER, "pass" if ok else "fail", conf, True, ev, t.ms, primary=True)
