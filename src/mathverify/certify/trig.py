"""Trigonometric equations (E1): never compare infinite solution sets directly.

Both the true solution set and the candidate are periodic; we pick a common window
W = lcm(period of the equation, steps of the candidate progressions), enumerate both
sets on [0, W) as FINITE sets and compare those.

Audit of 25 Sep 2026 (each item was measured as a false verdict before the change):
  * the true set is filtered by the definedness of the equation AS WRITTEN and of its real
    branches: sin(x)^2/sin(x) = 0 got {k*pi} (every root is 0/0), sqrt(sin x) = sqrt(cos x) got
    {pi/4 + k*pi} (at 5pi/4 both sides are imaginary);
  * SymPy's solveset is not the only witness: it loses x = pi of sqrt(3) sin x - cos x = 1, so a
    numeric root search on the window must find nothing it missed.
"""
from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp
from sympy import S, Interval, FiniteSet, Union, ImageSet, Lambda, oo

from ..equiv.numeric import num_equal, to_mp
from ..equiv.sets import set_equal
from ..sandbox import run as sb_run
from ..sandbox.exactsets import set_periods
from .base import Ctx, Timer, result, unknown, parse_or_unknown, condition_not_applied
from .domain import definedness_conditions, in_domain, relation_holds_at, written_definedness

LAYER = "certify.trig"


def detect_period(expr, var, timeout: float = 8.0):
    r = sb_run("mathverify.certify.trig:_periodicity", expr, var, timeout=timeout)
    if r.ok and r.value is not None:
        return r.value
    return None


def _periodicity(expr, var):
    from sympy.calculus.util import periodicity
    return periodicity(expr, var)


def _progressions(cand) -> list[tuple[Any, Any]] | None:
    """Decompose a candidate set into arithmetic progressions [(c, a)] meaning {c + a*n}."""
    if isinstance(cand, ImageSet):
        lam = cand.lamda
        if len(lam.variables) != 1 or cand.base_set != S.Integers:
            return None
        n = lam.variables[0]
        e = sp.expand(lam.expr)
        a = e.coeff(n, 1)
        c = e.subs(n, 0)
        if sp.expand(e - (a * n + c)) != 0:
            return None
        return [(c, a)]
    if isinstance(cand, Union):
        out = []
        for part in cand.args:
            p = _progressions(part)
            if p is None:
                return None
            out += p
        return out
    if isinstance(cand, FiniteSet):
        return [(e, 0) for e in cand.args]
    return None


def _rational_multiple(a, P):
    # exact: an irrational ratio must not be rounded into a rational one (nsimplify would)
    q = sp.simplify(a / P)
    return q if isinstance(q, sp.Rational) else None


def _enumerate_on_window(progs, W) -> FiniteSet | None:
    elems = []
    for c, a in progs:
        if a == 0:
            elems.append(c)
            continue
        # n range such that 0 <= c + a n < W
        lo = sp.ceiling(-c / a) if a > 0 else sp.ceiling((W - c) / a)
        hi = sp.floor((W - c) / a) if a > 0 else sp.floor(-c / a)
        try:
            lo_i, hi_i = int(lo), int(hi)
        except TypeError:
            return None
        if hi_i - lo_i > 10000:
            return None
        for k in range(lo_i, hi_i + 1):
            v = sp.simplify(c + a * k)
            if v == W or (v.is_number and (v < 0 or v >= W)):
                continue
            elems.append(v)               # exact; nsimplify would snap it
    return FiniteSet(*elems)


def _true_solutions(rel, var, window, conds, timeout, region=S.Reals) -> tuple[Any, dict[str, Any]]:
    """The equation's solution set on a bounded window, as a FiniteSet, or None.

    The set is the guarded solveset's (sandbox.exactsets): exact only for the classes whose zeros are
    known in closed form, a ConditionSet otherwise (SymPy's own set loses x = pi of sqrt(3) sin x -
    cos x = 1, and a numeric root search misses the multiple root of its cube: no proof either).
    It is filtered: every condition of the equation's definedness (as written and as parsed) must hold
    and both sides must be real there; each element must satisfy the equation. A root outside
    `region` (what the problem says of the variable besides the equation, `_region`) is dropped; one
    whose membership is undecided makes the set unknown."""
    ev: dict[str, Any] = {}
    r = sb_run("mathverify.sandbox.ops:solveset_in", rel, var, window, timeout=timeout)
    if not r.ok or not (r.value is S.EmptySet or isinstance(r.value, FiniteSet)):
        ev["error"] = f"solveset on window failed: {r.error or type(r.value).__name__}"
        return None, ev
    raw = list(r.value)
    ev["solveset_window"] = [str(e) for e in raw]
    kept = []
    for e in raw:
        drop = False
        for c in conds:
            h = relation_holds_at(c, var, e)
            if h is None:
                ev["error"] = f"definedness undecided at {e}: {c}"
                return None, ev
            if h is False:
                drop = True
                break
        if not drop:
            m = in_domain(region, e)
            if m is None:
                ev["error"] = f"membership in the variable's region undecided at {e}"
                return None, ev
            drop = m is False
        if not drop:
            try:
                l_, r_ = to_mp(rel.lhs.subs(var, e), 40), to_mp(rel.rhs.subs(var, e), 40)
            except Exception:  # noqa: BLE001
                ev["error"] = f"sides not evaluable at {e}"
                return None, ev
            if isinstance(l_, mp.mpc) or isinstance(r_, mp.mpc):
                drop = True                         # both sides imaginary is not a real solution
            else:
                same, _ = num_equal(rel.lhs.subs(var, e), rel.rhs.subs(var, e))
                if same is not True:
                    ev["error"] = f"solveset element {e} does not satisfy the equation"
                    return None, ev
        if drop:
            ev.setdefault("dropped", []).append(str(e))
        else:
            kept.append(e)
    return FiniteSet(*kept), ev


def _combined_period(P, conds, var, timeout, periods=()):
    """A common period of the equation, of its definedness conditions and of `periods` (those of the
    variable's region, `sandbox.exactsets.set_periods`), or None."""
    L = sp.Integer(1)
    for Pc in [detect_period(c.lhs - c.rhs, var, timeout) for c in conds] + list(periods):
        if Pc is None:
            return None
        q = _rational_multiple(Pc, P)
        if q is None:
            return None
        L = sp.Rational(sp.ilcm(L.p, abs(q.p)), sp.igcd(L.q, q.q))
    return L * P


def periodic_solution_set_equal(rel, var, candidate, window=None, timeout: float = 8.0, conds=(),
                                region=S.Reals, region_periods=()) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"candidate": str(candidate)}
    expr = rel.lhs - rel.rhs if isinstance(rel, sp.Equality) else rel
    if not isinstance(rel, sp.Equality):
        rel = sp.Eq(expr, 0)
    conds = [c for c in conds if getattr(c, "free_symbols", set()) == {var}]
    if window is not None:
        if not isinstance(window, Interval) or not (window.inf.is_finite and window.sup.is_finite):
            ev["error"] = "window_not_a_bounded_interval"
            return None, ev
        truth, tev = _true_solutions(rel, var, window, conds, timeout, region)
        ev.update(tev)
        if truth is None:
            return None, ev
        ev["true_window"] = [str(e) for e in truth]
        if not isinstance(candidate, FiniteSet) and candidate is not S.EmptySet:
            progs = _progressions(candidate)
            if progs is None:
                return None, ev
            candidate = _enumerate_window_of_interval(progs, window)
            if candidate is None:
                return None, ev
        ev["candidate_window"] = [str(e) for e in candidate]
        ok, sev = set_equal(candidate, truth)
        ev["compare"] = sev
        return ok, ev

    P = detect_period(expr, var, timeout)
    ev["period"] = P
    if P is None:
        # not periodic: compare solution sets on the reals if finite
        r = sb_run("mathverify.sandbox.ops:solveset_in", rel, var, S.Reals, timeout=timeout)
        if r.ok and isinstance(r.value, FiniteSet) and isinstance(candidate, FiniteSet) and not conds \
                and region == S.Reals:
            ok, sev = set_equal(candidate, r.value)
            ev["compare"] = sev
            return ok, ev
        return None, ev
    # the conditions may repeat with a longer period than the parsed equation
    Pw = _combined_period(P, conds, var, timeout, region_periods)
    if Pw is None:
        ev["error"] = "definedness_conditions_not_periodic"
        return None, ev
    if candidate is S.EmptySet:
        progs = []
    else:
        progs = _progressions(candidate)
        if progs is None:
            ev["error"] = "candidate_not_decomposable"
            return None, ev
    # common window
    L = sp.Integer(1)
    for c, a in progs:
        if a == 0:
            ev["error"] = "finite_candidate_for_periodic_equation"
            return False, ev
        q = _rational_multiple(a, Pw)
        if q is None:
            ev["error"] = f"step {a} is not a rational multiple of period {Pw}"
            return None, ev
        # lcm of rationals: lcm(num)/gcd(den)
        L = sp.Rational(sp.ilcm(L.p, abs(q.p)), sp.igcd(L.q, q.q))
    W = sp.simplify(L * Pw)
    ev["window"] = str(W)
    truth, tev = _true_solutions(rel, var, Interval.Ropen(0, W), conds, timeout, region)
    ev.update(tev)
    if truth is None:
        return None, ev
    cand_w = _enumerate_on_window(progs, W) if progs else S.EmptySet
    if cand_w is None:
        ev["error"] = "enumeration_failed"
        return None, ev
    ev["true_window"] = [e for e in truth]
    ev["candidate_window"] = [e for e in cand_w]
    ok, sev = set_equal(cand_w, truth)
    ev["compare"] = sev
    return ok, ev


def _enumerate_window_of_interval(progs, window: Interval):
    lo, hi = window.inf, window.sup
    if lo == -oo or hi == oo:
        return None
    elems = []
    for c, a in progs:
        if a == 0:
            if window.contains(c) == True:  # noqa: E712
                elems.append(c)
            continue
        klo = sp.ceiling((lo - c) / a) if a > 0 else sp.ceiling((hi - c) / a)
        khi = sp.floor((hi - c) / a) if a > 0 else sp.floor((lo - c) / a)
        for k in range(int(klo), int(khi) + 1):
            v = sp.simplify(c + a * k)         # exact; nsimplify would snap it
            if window.contains(v) == True:  # noqa: E712
                elems.append(v)
    return FiniteSet(*elems)


# the names a claimed general solution writes its family parameter with
_FAMILY_NAMES = ("n", "k", "m")


def general_solution_from_claim(claimed, ns) -> Any:
    """Turn a claimed set whose elements contain the integer symbol n/k into ImageSets."""
    if not isinstance(claimed, FiniteSet):
        return claimed
    parts = []
    for e in claimed.args:
        ints = [s_ for s_ in e.free_symbols if s_.name in _FAMILY_NAMES]
        if ints:
            n = ints[0]
            nn = sp.Symbol("n", integer=True)
            parts.append(ImageSet(Lambda(nn, e.subs(n, nn)), S.Integers))
        else:
            parts.append(FiniteSet(e))
    return Union(*parts) if len(parts) > 1 else parts[0]


def _region(ctx: Ctx, var, eq_src: str) -> tuple[sp.Set | None, list]:
    """What the problem says of the variable besides the equation, as a set: its declared domain,
    constraints, the domain of discourse and the written definedness of the problem (`domain_for`),
    cut by every other given on it (another equation, an inequality). The certificate read only the
    interval: all four roots of cos 2x = 1/2 on [0, 2*pi) were certified with the given x > pi, {n*pi}
    for sin x = 0 with x positive or 0 < x < 4, and {0, pi} for sin x + log(-1 - x**2) - log(-1 - x**2)
    = 0, which is defined nowhere (fourth audit G3, TAN-08). None, with the conditions, when one names
    a symbol no given fixes or cannot be solved."""
    unbound = list(ctx.unapplied_conditions(var))
    dom = ctx.domain_for(var)
    if var in written_definedness(eq_src, ctx.ns)[1]:
        dom = S.EmptySet                       # the equation as written is defined nowhere
    rels: list = []
    for g in ctx.ir.givens:
        if g == eq_src:
            continue
        try:
            rel = ctx.rel(g)
        except Exception:  # noqa: BLE001 - a given the certificate cannot read is not applied
            return None, unbound + [g]
        for r in (rel.args if isinstance(rel, sp.And) else (rel,)):
            if not isinstance(r, sp.core.relational.Relational):
                return None, unbound + [g]
            if var in r.free_symbols:
                rels.append(r)
    kept, unb = ctx.on_var(rels, var)
    if unbound or unb:
        return None, unbound + unb
    region = ctx.cut_by(var, dom, kept)
    if region is None:
        return None, kept
    return region, []


def verify(ir, solution, ctx: Ctx):
    """Task `trig_solve`: params {"equation"?: str, "var": str, "interval"?: str}."""
    if ir.task.kind != "trig_solve":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        var = ctx.sym(p.get("var", "x"))
        eq_src = p.get("equation") or (ir.givens[0] if ir.givens else None)
        if eq_src is None:
            return unknown(LAYER, "no_equation")
        rel, err = parse_or_unknown(LAYER, ctx.rel, eq_src)
        if err:
            return err
        from ..normalize.parse import parse_answer, parse_set_str
        ca = solution.claimed_answer
        try:
            ns2 = ctx.claim_ns(solution)
            for nm in ("n", "k"):
                ns2.setdefault(nm, sp.Symbol(nm, integer=True))
            # The family parameter of a general solution runs over ALL the integers
            # (`general_solution_from_claim`), so the claim is read with it as an integer and nothing
            # more, whatever the IR declares under that name. With k declared a positive integer,
            # {Abs(k)*pi} and {sqrt(k**2)*pi} were read as {k*pi} and then spread over every integer:
            # the nonnegative multiples of pi alone were certified as the solutions of sin x = 0, and
            # {2*pi*Max(n, 0)} as those of cos x = 1 (V17, DECISIONS §74). An undeclared m stays
            # undeclared, and a claim on a window (no family) is read as before.
            family = {nm: sp.Symbol(nm, integer=True) for nm in _FAMILY_NAMES
                      if nm != var.name and (nm in ("n", "k") or isinstance(ns2.get(nm), sp.Symbol))}
            ns_claim = dict(ns2, **family) if not p.get("interval") else ns2
            if ca.kind in ("set", "interval"):
                claimed = parse_answer(ca.kind, ca.payload, ns_claim)
            else:
                claimed = FiniteSet(parse_answer("value", ca.payload, ns_claim))
        except Exception as e:
            return unknown(LAYER, f"parse_error: {e}", flags=["parse_error"])
        window = None
        if p.get("interval"):
            window = parse_set_str(p["interval"], ns2)
        # definedness of the equation as WRITTEN (sin(x)^2/sin(x) parses to sin(x)) and of its
        # parsed real branches (sqrt, log, tan poles)
        conds = [c for c in written_definedness(eq_src, ctx.ns)[0] if c.free_symbols == {var}]
        conds += [c for c in definedness_conditions(rel, var)
                  if getattr(c, "free_symbols", set()) == {var} and c not in conds]
        claimed_g = general_solution_from_claim(claimed, ns2) if window is None else claimed
        region, unapplied = _region(ctx, var, eq_src)
        if region is None:
            return condition_not_applied(LAYER, unapplied, t.ms)
        periods: list = []
        if window is None and region != S.Reals:
            periods = set_periods(region)
            if periods is None:
                # a region with no period (x > 0, 0 < x < 4, x an integer): a general solution is no
                # answer there; a finite claim is compared on the region's bounded hull
                try:
                    lo, hi = region.inf, region.sup
                    bounded = lo.is_finite and hi.is_finite and lo.is_number and hi.is_number
                except Exception:  # noqa: BLE001
                    bounded = False
                if not bounded or not (claimed_g is S.EmptySet or isinstance(claimed_g, FiniteSet)):
                    return condition_not_applied(LAYER, [region], t.ms)
                window = Interval(lo, hi)
                periods = []
        ok, ev = periodic_solution_set_equal(rel, var, claimed_g, window=window, timeout=ctx.timeout,
                                             conds=conds, region=region, region_periods=periods)
        ev["conditions"] = [str(c) for c in conds]
        ev["region"] = str(region)
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("error", "undecided"), t.ms, ev)
