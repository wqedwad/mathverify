"""Deterministic step refuter.

For every step of kind `eq` or `compute` with a parseable claim:
  * `compute`: claim `lhs = rhs` where lhs contains an unevaluated operation (Derivative,
    Integral, Limit, Sum) or is plain arithmetic -> evaluate lhs with the CAS and compare
    with rhs (domain-aware). A definite difference => REFUTED.
  * `eq`: claim is a relation that should follow from the premises. Premises are the
    IR givens plus ALL earlier parseable step claims (not only the cited ones, so that
    under-citation is never penalised), the variables' domain constraints and the task's own
    interval (when the premises have an instance inside it). We look for a point that satisfies every premise,
    lies in the problem domain, and violates the claim. Found => REFUTED with that point.
    A claim that restates one of the problem's own objects (the curve of a tangent line) is
    neither checked nor a premise (`_task_objects`).
Outcomes per step: verified | refuted | unknown | skipped. The layer result is `fail`
(hard) only when at least one step is refuted; otherwise `unknown` (never `pass`).
"""
from __future__ import annotations

import re
import time
from contextvars import ContextVar
from typing import Any

import sympy as sp
from sympy import S, Eq, Or, And

from ..certify.base import Ctx, Timer, result, unknown
from ..certify.domain import relation_holds_at, in_domain
from ..equiv import answers_equivalent
from ..equiv.random_point import sample_points
from ..normalize.parse import ParseError, parse_relation, UndeclaredSymbolError, _refuse_reversed_ranges
from ..sandbox import run as sb_run

LAYER = "steps.refute"

_IN_SET = re.compile(r"^\s*([A-Za-z_]\w*)\s+in\s+(\{.*\})\s*$")

# Seconds one step may spend re-checking itself on the premises (solving them, sampling their region,
# searching a counterexample there). A step over a cubic premise with three real roots spent 120-390 s
# sampling a set of radicals in-process (fourth audit, D4-ADIM-F). Checked between the expensive calls;
# past it the step is unknown (`step_time_budget_exceeded`).
_STEP_BUDGET = 60.0
_deadline: ContextVar[float | None] = ContextVar("mathverify_step_deadline", default=None)


class _OutOfTime(BaseException):
    """The step's time budget ran out. A BaseException, so that no `except Exception` on the way, which
    keeps the identity check's refutation when a re-check fails, turns it into a refutation."""


def _tick() -> None:
    d = _deadline.get()
    if d is not None and time.monotonic() > d:
        raise _OutOfTime()


# A solution's steps together get this many seconds; past it the remaining steps are unknown without a check
# (`solution_time_budget_exceeded`). A comparison of two sides runs in the sandbox for at most
# _COMPARE_TIMEOUT seconds (and never past the step's budget): its numerics (adaptive evalf of
# 1 + 2*exp(-exp(exp(x))) against (1 + exp(-exp(exp(x))))**2) held the GIL for 400 s and more in one call,
# which no check between calls can stop (d4g review S8, S11, S12).
_SOLUTION_BUDGET = 300.0
_COMPARE_TIMEOUT = 40.0


def _sandboxed_equivalent(a, b, shape, domain, seed):
    """`answers_equivalent` in the sandbox's worker. Its own CAS calls run inline there (the worker is a
    daemon and starts no worker of its own); the caller's timeout bounds them all."""
    import os
    os.environ["MATHVERIFY_SANDBOX"] = "inline"
    return answers_equivalent(a, b, shape=shape, domain=domain, seed=seed)


def _equivalent(a, b, ctx: Ctx, shape: str, domain=None) -> tuple[bool | None, dict]:
    _tick()
    d = _deadline.get()
    timeout = _COMPARE_TIMEOUT if d is None else max(1.0, min(_COMPARE_TIMEOUT, d - time.monotonic()))
    r = sb_run("mathverify.steps.deterministic:_sandboxed_equivalent", a, b, shape, domain, ctx.seed,
               timeout=timeout)
    if not r.ok:
        return None, {"error": f"comparison_not_finished: {str(r.error)[:160]}"}
    return r.value


# Heads under which an expression is analytic on the complex plane minus a discrete set: entire functions,
# meromorphic ones, sums, products, integer powers, powers of a positive constant. The class is closed
# under composition, and minus a discrete set the plane stays connected, so two such expressions that
# agree on a set with an accumulation point agree wherever both are defined (identity theorem); a nonzero
# difference vanishes only on a discrete set, which random points miss. Agreement of anything else at
# sample points proves nothing: asin(sin(x)) = x on 0 < x < 1.58, log(x**2) = 2*log(x) on x > -1/1000
# (fourth audit, D4-ADIM-A). A whitelist, not the comparison's list of non-smooth functions.
_ENTIRE = (sp.exp, sp.sin, sp.cos, sp.sinh, sp.cosh)
_MEROMORPHIC = (sp.tan, sp.cot, sp.sec, sp.csc, sp.tanh, sp.coth, sp.sech, sp.csch)


def _analytic_off_discrete(e) -> bool:
    if isinstance(e, (sp.Symbol, sp.Number, sp.NumberSymbol)) or e is S.ImaginaryUnit:
        return e.is_finite is not False
    if isinstance(e, (sp.Add, sp.Mul)):
        return all(_analytic_off_discrete(a) for a in e.args)
    if isinstance(e, sp.Pow):
        b, x = e.args
        if isinstance(x, sp.Integer):
            return _analytic_off_discrete(b)
        if b.is_number and not b.free_symbols and b.is_positive is True and b.is_finite is True:
            return _analytic_off_discrete(x)
        return False
    if isinstance(e, _ENTIRE + _MEROMORPHIC) and len(e.args) == 1:
        return _analytic_off_discrete(e.args[0])
    return False


def _has_interior(dom) -> bool:
    """Does the set hold an interval of positive length (so random points of it accumulate)? A set of
    integers or a finite set does not: binomial(n, 200) vanishes at every integer 0..199, and agreement
    with 0 at sample integers proved nothing (D4-ADIM-A)."""
    try:
        if dom.is_subset(S.Integers) is not False:
            return False
        m = dom.measure
        return bool(m.is_positive) or m == sp.oo
    except Exception:  # noqa: BLE001 - a set whose measure is not known: no interior proved
        return False


def _agreement_proves(a, b, dom: dict, cev: dict, ctx=None) -> bool:
    """Is the comparison's True (`answers_equivalent`) a proof? A symbolic proof, or the comparison's own
    proof for a non-smooth expression (cells between breakpoints, a period checked), is. Agreement at random
    points is only for two expressions analytic off a discrete set (`_analytic_off_discrete`) compared on
    sets with interior, or analytic near the one interval they are compared on (`_analytic_on_interval`);
    otherwise it decides nothing."""
    if cev.get("method") != "random_point":
        return True
    proof = (cev.get("random_point") or {}).get("nonsmooth_proof")
    if isinstance(proof, str) and (proof.startswith("cells_proved") or proof.startswith("period_")):
        return True
    # a symbol compared on one value (a cell of the premises' region, n = 3) is evaluated there, not sampled
    one = {q: next(iter(d)) for q, d in dom.items() if isinstance(d, sp.FiniteSet) and len(d) == 1}
    a, b = sp.sympify(a).xreplace(one), sp.sympify(b).xreplace(one)
    dom = {q: d for q, d in dom.items() if q not in one}
    if not dom:
        # every symbol has one value: the comparison decided the constants exactly (random_point counts no
        # numeric agreement as equality since part d4c; 1 + log(1 + exp(-exp(30))) = 1 is not, review S1)
        return True
    if not (_analytic_off_discrete(a) and _analytic_off_discrete(b)):
        return _analytic_on_interval(a, b, dom, ctx)
    return all(_has_interior(d) for d in dom.values())


def _proved_empty(rel, v, iv, ctx) -> bool:
    if ctx is None:
        return False
    _tick()
    r = sb_run("mathverify.sandbox.ops:solveset_in", rel, v, iv, timeout=ctx.timeout)
    try:
        return r.ok and isinstance(r.value, sp.Set) and r.value.is_empty is True
    except Exception:  # noqa: BLE001
        return False


def _analytic_on_interval(a, b, dom: dict, ctx) -> bool:
    """Are both sides analytic on a complex neighbourhood of the one real interval they are compared on? A
    branch function is, where its argument stays off its cut: log(u) and a fractional power of u where u > 0
    on the interval, asin/acos(u) where |u| < 1, atan(u) everywhere, with u a rational function of the
    variable whose denominator does not vanish there (each proved by solving the negation on the interval).
    Agreement at random points of a connected interval then proves the identity there (identity theorem):
    log(x - 1) + log(x - 3) = log((x - 1)*(x - 3)) for x > 3, while log(x**2) = 2*log(x) on x > -1/1000 is
    not proved (the argument of log(x) is not positive there)."""
    if len(dom) != 1:
        return False
    (v, iv), = dom.items()
    if not isinstance(iv, sp.Interval) and iv != S.Reals or not _has_interior(iv):
        return False

    def arg_ok(u) -> bool:
        if not u.free_symbols <= {v}:
            return False
        num, den = sp.fraction(sp.together(u))
        if not (num.is_polynomial(v) and den.is_polynomial(v)):
            return False
        return den.free_symbols == set() or _proved_empty(Eq(den, 0), v, iv, ctx)

    def ok(e) -> bool:
        if isinstance(e, (sp.Symbol, sp.Number, sp.NumberSymbol)):
            return e.is_finite is not False
        if isinstance(e, (sp.Add, sp.Mul)):
            return all(ok(t) for t in e.args)
        if isinstance(e, sp.Pow):
            base_, ex = e.args
            if isinstance(ex, sp.Integer) or (base_.is_number and base_.is_positive is True and not base_.free_symbols):
                return ok(base_) and ok(ex)
            if isinstance(ex, sp.Rational):
                return arg_ok(base_) and _proved_empty(sp.Le(base_, 0), v, iv, ctx)
            return False
        if isinstance(e, _ENTIRE + _MEROMORPHIC) and len(e.args) == 1:
            return ok(e.args[0])
        if isinstance(e, sp.log) and len(e.args) == 1:
            return arg_ok(e.args[0]) and _proved_empty(sp.Le(e.args[0], 0), v, iv, ctx)
        if isinstance(e, (sp.asin, sp.acos)):
            return arg_ok(e.args[0]) and _proved_empty(sp.Ge(sp.Abs(e.args[0]), 1), v, iv, ctx)
        if isinstance(e, sp.atan):
            return arg_ok(e.args[0])
        return False

    return ok(a) and ok(b)


def _parse_claim(claim: str, ns: dict[str, Any]):
    from ..normalize.parse import _strip_invisible, strip_presentation
    # invisible characters and display wrappers (\boxed{}, $…$) are removed before the `x in {…}`
    # form is recognised: otherwise the form fell through to the general parser, whose guard
    # refuses Python's `in`, and 7 correct solutions became UNKNOWN (adversarial run, 25 Sep 2026)
    m = _IN_SET.match(strip_presentation(_strip_invisible(claim)))
    if m:
        from ..normalize.parse import parse_set_str
        var = ns.get(m.group(1))
        if var is None:
            raise UndeclaredSymbolError(f"unknown symbol {m.group(1)}")
        s_ = parse_set_str(m.group(2), ns)
        return Or(*[Eq(var, e) for e in s_.args]) if len(s_.args) > 1 else Eq(var, list(s_.args)[0])
    return parse_relation(claim, ns)


def _is_relation(e) -> bool:
    return isinstance(e, (sp.core.relational.Relational, And, Or)) or e in (sp.true, sp.false)


def _holds(rel, point: dict) -> bool | None:
    """Tri-state truth of `rel` at `point` ({Symbol: value})."""
    if rel is sp.true:
        return True
    if rel is sp.false:
        return False
    if isinstance(rel, And):
        rs = [_holds(a, point) for a in rel.args]
        if any(r is False for r in rs):
            return False
        return True if all(r is True for r in rs) else None
    if isinstance(rel, Or):
        rs = [_holds(a, point) for a in rel.args]
        if any(r is True for r in rs):
            return True
        return False if all(r is False for r in rs) else None
    if isinstance(rel, (Eq, sp.Ne)) and (isinstance(rel.lhs, sp.MatrixBase) or isinstance(rel.rhs, sp.MatrixBase)):
        # matrix sides: compared entrywise, as `compute` claims are. A wrong `eq` step
        # "M*M**-1 = Matrix([[1, 0], [0, 2]])" stayed "unknown" and was never refuted (audit of
        # 25 Sep 2026, linalg).
        try:
            lhs = rel.lhs.subs(point, simultaneous=True)
            rhs = rel.rhs.subs(point, simultaneous=True)
        except Exception:  # noqa: BLE001
            return None
        if getattr(lhs, "free_symbols", None) or getattr(rhs, "free_symbols", None):
            return None
        ok, _ = answers_equivalent(lhs, rhs, shape="scalar")
        if ok is None:
            return None
        return ok if isinstance(rel, Eq) else (not ok)
    if isinstance(rel, sp.core.relational.Relational):
        # substitute the two sides separately: `Eq(a, b).subs(...)` with Float points
        # auto-evaluates to False on last-bit rounding differences (measured: the identity
        # x^2-5x-14 = (x-7)(x+2) was 'refuted'). Compare tolerantly instead.
        try:
            lhs = rel.lhs.subs(point, simultaneous=True)
            rhs = rel.rhs.subs(point, simultaneous=True)
        except Exception:
            return None
        if lhs.free_symbols or rhs.free_symbols:
            return None
        d = sp.Symbol("_d")
        if lhs.is_Number and rhs.is_Number:
            return relation_holds_at(type(rel)(lhs, rhs, evaluate=False), d, 0)
        # evaluated in the sandbox, bounded in time (d4g review S12: one evaluation of a side with
        # exp(-exp(exp(x))) held the GIL for minutes)
        r = sb_run("mathverify.steps.deterministic:_inline_call", "mathverify.certify.domain:relation_holds_at",
                   type(rel)(lhs, rhs, evaluate=False), d, 0, timeout=_bounded(10.0))
        return r.value if r.ok else None
    try:
        sub = rel.subs(point, simultaneous=True)
    except Exception:
        return None
    if sub is sp.true:
        return True
    if sub is sp.false:
        return False
    return None


def _at_convention(point: dict, ctx: Ctx) -> bool:
    """Is a coordinate of the point outside its symbol's domain only because a value of the problem is a
    convention there (`Ctx.convention_region`)?"""
    for s_, v in point.items():
        if not isinstance(s_, sp.Symbol) or v.free_symbols or ctx.ns.get(s_.name) != s_:
            continue
        if in_domain(ctx.domain_for(s_), v) is False and in_domain(ctx.convention_region(s_), v) is not False:
            return True
    return False


def _in_domains(ctx: Ctx, point: dict) -> bool:
    for s_, v in point.items():
        if v.free_symbols:
            continue
        if in_domain(ctx.domain_for(s_), v) is False:
            return False
    for c in ctx.var_constraints():
        if _holds(c, point) is False:
            return False
    return True


def _step_namespace(ns: dict[str, Any]) -> dict[str, Any]:
    """Namespace for `compute` claims: the calculus operators stay UNEVALUATED so the certificates
    below see them. SymPy stores `Limit(e, x, a)` with dir='+' and `limit(...)` / `diff(...)` /
    `at(diff(...))` evaluate at parse time, so "Limit(|x|/x, x, 0) = 1" was checked from the right
    only and "at(diff(Abs(x), x), x, 0) = 0" became 0 = 0 (audit of 25 Sep 2026). A limit written
    without a direction is two-sided (SOLVER_FORMAT, E6)."""
    out = dict(ns)

    def _limit(e, v, p, d=None):
        if d is None:
            p_ = sp.sympify(p)
            d = "-" if p_ == sp.oo else "+" if p_ == -sp.oo else "+-"
        return sp.Limit(e, v, p, d)

    def _at(e, v, val):
        e = sp.sympify(e)
        return sp.Subs(e, v, val) if e.has(sp.Derivative) else e.subs(v, val)

    def _integral(*a):
        return sp.Integral(*a)

    _integral.binds_range = True          # its variable is a dummy (normalize.parse._binds_range)
    _limit.binds_point = _at.binds_point = True   # likewise (normalize.parse._binds_point)
    out["Limit"] = out["limit"] = _limit
    out["Integral"] = out["integrate"] = _integral
    out["Derivative"] = out["diff"] = lambda *a: sp.Derivative(*a)
    out["at"] = _at
    out["Subs"] = sp.Subs
    return out


def _derivative_points(expr) -> list:
    """Subs(Derivative(f, (x, n)), x, a) atoms: a derivative evaluated at a point."""
    return [s_ for s_ in expr.atoms(sp.Subs)
            if isinstance(s_.expr, sp.Derivative) and len(s_.variables) == 1
            and s_.expr.variables and set(s_.expr.variables) == set(s_.variables)]


def _compare_domains(free, ctx: Ctx, doms: dict | None) -> dict:
    """The set each free symbol of a `compute` claim is compared on: `doms`' when it gives one (the region
    the premises leave, `_on_premises`), else the symbol's domain."""
    return {s_: (doms or {}).get(s_, ctx.domain_for(s_) if s_.name in ctx.ns else S.Reals) for s_ in free}


def _verified_where_conventions(claim, ctx: Ctx, status: str, ev: dict) -> tuple[str, dict]:
    """A `compute` claim verified as an identity on its symbols' domains, which leave out the points where
    the value of a problem expression is a convention (`Ctx.convention_region`): an instance of the problem
    may lie there. Under the given x**(1/3) = x the real root makes x = -1 an instance, and "Abs(x) = x",
    verified on [0, oo), was a verified step (fourth audit, D4-ADIM-K). Checked again with those points;
    verified only when it holds there too (a non-integer Sum/Product bound of the problem is such a point,
    `Ctx.integer_bound_region`). Where a bound of the claim's own Sum/Product may be no integer no reading is the
    curriculum's: not verified (Σ_{k=n}^{n+2} k = 3n + 3 with n real holds in SymPy's stepping alone, review of
    d4f, YO-3)."""
    from ..certify.domain import definedness_conditions, is_integer_bound
    try:
        own = [c for c in definedness_conditions(claim, None) if is_integer_bound(c) and c.free_symbols]
    except Exception:  # noqa: BLE001 - no conditions read: as before
        own = []
    if own:
        return "unknown", {**ev, "reason": "not_verified_where_a_bound_is_not_an_integer"}
    doms: dict = {}
    for s_ in getattr(claim, "free_symbols", set()):
        if ctx.ns.get(s_.name) != s_:
            continue
        reg = ctx.convention_region(s_)
        try:
            empty = reg.is_empty
        except Exception:  # noqa: BLE001
            empty = None
        if empty is not True:
            doms[s_] = sp.Union(ctx.domain_for(s_), reg)
    if not doms:
        return status, ev
    s2, ev2 = _check_compute(claim, ctx, doms=doms)
    if s2 == "verified":
        return status, ev
    return "unknown", {**ev, "reason": "not_verified_where_a_value_is_a_convention", "recheck": ev2}


def _jump_undecided(*rels) -> bool:
    """Does one of `rels` hold a jump (ceiling, floor, sign, frac, Mod, Heaviside, a Piecewise of constant
    conditions) of a number no certified sign settles (equiv.numeric.undecided_jumps)? doit, simplify and the
    solvers read it off rounding noise: with Z = gd(1) - gd(1) exactly 0, the step "Piecewise((1, Z**2 > 0),
    (0, Z**2 <= 0)) = 1" was verified, and "x = ceiling(Z**2)" refuted under x = 0, the right answer then
    INCORRECT (round 9 of part d4b, YO-4). Such a step decides nothing."""
    from ..equiv.numeric import undecided_jumps
    return undecided_jumps(*[r for r in rels if isinstance(r, sp.Basic)])


def _check_compute(claim, ctx: Ctx, doms: dict | None = None) -> tuple[str, dict]:
    ev: dict[str, Any] = {}
    if _jump_undecided(claim):
        return "unknown", {"reason": "jump_of_an_unproved_number"}
    if not isinstance(claim, Eq):
        if isinstance(claim, (sp.core.relational.Relational, And, Or, sp.logic.boolalg.BooleanAtom)) \
                and not getattr(claim, "free_symbols", None):
            # a closed inequality is checkable like a closed equation: "sin(pi/6) < 0" was skipped
            # and the solution stayed CORRECT (audit of 29 Sep 2026)
            status = _closed_claim(claim, ctx)
            if status != "unknown":
                return status, {"reason": "closed_relation"}
        return "skipped", {"reason": "compute_claim_not_equation"}
    lhs, rhs = claim.lhs, claim.rhs
    if rhs.has(sp.Integral, sp.Limit, sp.Subs) and not lhs.has(sp.Integral, sp.Limit, sp.Subs):
        lhs, rhs = rhs, lhs                    # "1 = Limit(...)" is the same claim
    indefinite = [i for i in (lhs.atoms(sp.Integral) | rhs.atoms(sp.Integral))
                  if any(len(a) == 1 for a in i.limits)]
    if indefinite:
        from ..certify.calculus import antiderivative_certificate
        integ = indefinite[0]
        var = integ.limits[0][0]
        if lhs == integ and not rhs.has(sp.Integral, sp.Limit, sp.Derivative, sp.Subs):
            # indefinite integral: derivative certificate on rhs
            F = rhs.subs(sp.Symbol("C"), 0)
            # on the region the premises leave (`_on_premises`): an antiderivative of |x| on the task's
            # [0, 2] is x**2/2 (fourth audit, D4-ADIM-E)
            dom = (doms or {}).get(var, ctx.domain_for(var) if var.name in ctx.ns else S.Reals)
            ok, cev = antiderivative_certificate(F, integ.function, var, timeout=ctx.timeout, discourse=dom)
            ev["antiderivative"] = cev
            return ("verified" if ok is True else "refuted" if ok is False else "unknown"), ev
        # inside a larger expression ("2*Integral(x, x) = x**3"): both sides are families that
        # differ by a constant, so their derivatives must agree. It was skipped before (measured).
        if len(indefinite) != len(lhs.atoms(sp.Integral) | rhs.atoms(sp.Integral)) \
                or any(i.limits[0][0] != var or len(i.limits) != 1 for i in indefinite) \
                or claim.has(sp.Limit, sp.Subs, sp.Sum):
            return "unknown", {"reason": "indefinite_integral_mixed_with_other_operations"}
        r = sb_run("mathverify.steps.deterministic:_diff_doit", lhs - rhs, var, timeout=ctx.timeout)
        if not r.ok:
            return "unknown", {"reason": f"diff_failed: {r.error}"}
        d = r.value
        ev["derivative_of_difference"] = str(d)
        if d == 0:
            return "verified", ev
        dom = _compare_domains(d.free_symbols, ctx, doms)
        ok, cev = _equivalent(d, S.Zero, ctx, "expression" if d.free_symbols else "scalar",
                              dom or None)
        ev["compare"] = cev
        return ("refuted" if ok is False else "unknown"), ev
    subst: dict[Any, Any] = {}
    lims = lhs.atoms(sp.Limit) | rhs.atoms(sp.Limit)
    ders = _derivative_points(lhs) + _derivative_points(rhs)
    if lims or ders:
        # E6 leaks into the step layer otherwise: Limit.doit() is SymPy's one-sided default,
        # so "Limit(|x|/x, x, 0) = 1" would be *verified*. Classify two-sidedly instead; the same
        # for a derivative at a point (sign(0) = 0 is not a derivative). Every such atom is
        # replaced by its certified value, wherever it sits in the claim.
        from ..certify.limits import classify_limit
        from ..certify.calculus import derivative_at_point
        if any(L.free_symbols for L in lims):
            # a limit with a parameter has no value (DECISIONS §80): with n an integer SymPy gives 0
            # for the limit of a*n*sin(pi/n) at oo (a*pi), so "... = 0" was verified and "... = pi*a"
            # refuted (part iv, 1 Oct 2026). Pinned by a given, the parse made it closed.
            return "unknown", {"reason": "parametric_form",
                               "forms": [str(L) for L in lims if L.free_symbols][:3]}
        for L in lims:
            e_, v_, p_, d_ = L.args
            side = None if str(d_) in ("+-", "real") else str(d_)
            cls = classify_limit(e_, v_, p_, side, timeout=ctx.timeout)
            ev.setdefault("limit_classification", []).append({k: str(v) for k, v in cls.items()})
            if cls["kind"] == "UNKNOWN":
                return "unknown", ev
            if cls["kind"] == "DNE":
                return "refuted", {**ev, "reason": "limit_does_not_exist"}
            subst[L] = cls["value"]
        for D in ders:
            der = D.expr
            v_ = der.variables[0]
            f_ = der.expr
            dap = derivative_at_point(f_, v_, len(der.variables), D.point[0], timeout=ctx.timeout)
            ev.setdefault("derivative_at_point", []).append({k: str(v) for k, v in dap.items()})
            if dap["status"] in ("corner", "discontinuous", "cusp"):
                return "refuted", {**ev, "reason": "derivative_does_not_exist"}
            if dap["status"] != "value":
                return "unknown", ev
            subst[D] = dap["value"]
        lhs, rhs = lhs.xreplace(subst), rhs.xreplace(subst)
        if lhs.has(sp.Integral, sp.Derivative, sp.Limit, sp.Subs, sp.Sum):
            return "unknown", {**ev, "reason": "operation_left_after_substitution"}
        if lhs.has(sp.oo, -sp.oo) or rhs.has(sp.oo, -sp.oo):
            if lhs == rhs:
                return "verified", ev
            if (lhs in (sp.oo, -sp.oo) or rhs in (sp.oo, -sp.oo)) and lhs.is_number and rhs.is_number \
                    and not lhs.has(sp.zoo, sp.nan) and not rhs.has(sp.zoo, sp.nan):
                return "refuted", ev
            return "unknown", ev
    from ..equiv.forms import UnverifiedForm, checked_forms
    try:
        lhs, rhs = checked_forms(lhs, ctx.timeout), checked_forms(rhs, ctx.timeout)
    except UnverifiedForm as e:
        # SymPy's value of a closed integral/sum/product that numbers do not confirm decides
        # nothing: "Integral(Abs(cos(x)), (x, -1, 1)) = 0" was verified (audit of 29 Sep 2026);
        # the integrator's own value can still refute it
        if _integrals_refute(claim, ctx):
            return "refuted", {**ev, "reason": "integrals_numeric_value_differs"}
        return "unknown", {**ev, "reason": f"unverified_form: {str(e)[:200]}"}
    from ..equiv.forms import has_parametric_form
    if has_parametric_form(lhs) or has_parametric_form(rhs):
        # an integral with a parameter has no value (DECISIONS §80): SymPy's doit of it was the value
        # ("Integral(x, (x, 0, a)) = a**2/2" verified). Compared as expressions, only an identity
        # that needs no value, or a counterexample at a value of the parameter (the closed integral
        # there, confirmed by numbers), decides; a pin of the parameter re-checks it there.
        free = lhs.free_symbols | rhs.free_symbols
        dom = _compare_domains(free, ctx, doms)
        ok, cev = _equivalent(rhs, lhs, ctx, "expression", dom)
        ev["compare"] = cev
        if ok is True and not _agreement_proves(rhs, lhs, dom, cev, ctx):
            return "unknown", {**ev, "reason": "sample_agreement_is_no_proof_here"}
        if ok is True:
            return _forward_ranges_only(claim, ctx, doms, ev)
        if ok is False:
            return "refuted", ev
        return "unknown", {**ev, "reason": "parametric_form"}
    r = sb_run("mathverify.steps.deterministic:_doit", lhs, timeout=ctx.timeout)
    if not r.ok:
        return "unknown", {"reason": f"doit_failed: {r.error}"}
    val = r.value
    ev["lhs_evaluated"] = str(val)
    if val.has(sp.Integral, sp.Derivative, sp.Limit, sp.Sum):
        return "unknown", {"reason": "cas_could_not_evaluate", **ev}
    if rhs.has(sp.Integral, sp.Derivative, sp.Limit, sp.Sum, sp.Subs):
        r2 = sb_run("mathverify.steps.deterministic:_doit", rhs, timeout=ctx.timeout)
        if not r2.ok or r2.value.has(sp.Integral, sp.Derivative, sp.Limit, sp.Sum):
            return "unknown", {"reason": "cas_could_not_evaluate_rhs", **ev}
        rhs = r2.value
    free = val.free_symbols | rhs.free_symbols
    if free:
        dom = _compare_domains(free, ctx, doms)
        ok, cev = _equivalent(rhs, val, ctx, "expression", dom)
        if ok is True and not _agreement_proves(rhs, val, dom, cev, ctx):
            ev["compare"] = cev
            return "unknown", {**ev, "reason": "sample_agreement_is_no_proof_here"}
    else:
        ok, cev = _equivalent(rhs, val, ctx, "scalar")
    ev["compare"] = cev
    if ok is True:
        return _forward_ranges_only(claim, ctx, doms, ev)
    return ("refuted" if ok is False else "unknown"), ev


def _binders_keep_clear_of(claim, syms) -> bool:
    """Does `claim` bind variables only in Sums, Products and definite Integrals, none of whose
    bound variables is one of `syms`? Then replacing `syms` by values (xreplace) reaches their
    limits and bodies and never a bound variable. A Limit is left out: SymPy's `Limit.subs` also
    replaces the variable it binds; so are a Derivative, a Subs, a Lambda, an indefinite Integral
    (its variable is free) and any other binder."""
    if claim.has(sp.Limit, sp.Derivative, sp.Order):      # they bind without listing bound_symbols
        return False
    for node in sp.preorder_traversal(claim):
        if isinstance(node, (sp.Sum, sp.Product, sp.Integral)):
            if any(len(lim) != 3 or lim[0] in syms for lim in node.limits):
                return False
        elif getattr(node, "bound_symbols", None):        # Subs, Lambda, any other binder
            return False
    return True


def _pins(claim, premises: list) -> dict | None:
    """The one value each free symbol of `claim` is pinned to by the premises (`a = 1`, `b = -5`),
    or None: a symbol no premise pins, or pins to two values not proved equal, or a claim with an
    operation whose bound variable a substitution could reach. A `compute` claim with the
    problem's parameters ("f(2) = 2" for f = x³ + ax² + bx) was checked as an identity in them
    and refuted at a = b = 0, which violates the givens (V15 S1, DECISIONS §72). A Sum, Product or
    definite Integral whose bound variables are not pinned symbols is no such operation: with n = 3
    given, "Sum(k, (k, 1, n)) = 6" was refuted at an n != 3 (part 8, 30 Sep 2026)."""
    from ..certify.base import closed_binding
    from ..equiv.numeric import exact_equal
    syms = getattr(claim, "free_symbols", None)
    if not isinstance(claim, Eq) or not syms or not _binders_keep_clear_of(claim, syms):
        return None
    vals: dict[Any, list] = {}
    for p in premises:
        b = closed_binding(p)
        if b is not None and b[0] in syms:
            vals.setdefault(b[0], []).append(b[1])
    if set(vals) != syms:
        return None
    if any(exact_equal(v, vs[0]) is not True for vs in vals.values() for v in vs[1:]):
        return None
    return {s_: vs[0] for s_, vs in vals.items()}


# The values a finite premise set may hold for each of them to be checked one by one, and the symbols
# the premises may link a claim's symbols to.
_MAX_INSTANCES = 20
_MAX_LINKED = 4


def _premise_parts(premises: list) -> list:
    """The premises with free symbols, an And split into its parts (a chain 0 < n < 5)."""
    out: list = []
    for p in premises:
        for q in (p.args if isinstance(p, And) else (p,)):
            if getattr(q, "free_symbols", None):
                out.append(q)
    return out


def _linked(premises: list, syms) -> tuple[list, set]:
    """The premises that share a symbol with `syms`, directly or through another such premise, and the
    symbols they name together with `syms`."""
    want, out, left = set(syms), [], list(premises)
    grew = True
    while grew:
        grew = False
        for p in list(left):
            if p.free_symbols & want:
                out.append(p)
                want |= p.free_symbols
                left.remove(p)
                grew = True
    return out, want


def _holds_exactly(p, point: dict, ctx: Ctx) -> bool | None:
    """Truth of a premise at a point: a relation exactly (`_decide`), a membership by `decide_membership`
    (a Sum/Product range's condition stays undecided where the range runs backwards)."""
    from ..certify.domain import decide_membership
    if p is sp.true or p is sp.false:
        return bool(p)
    if isinstance(p, sp.Contains):
        try:
            return decide_membership(p.args[0].xreplace(point), p.args[1])
        except Exception:  # noqa: BLE001
            return None
    if isinstance(p, (And, Or)):
        vals = [_holds_exactly(a, point, ctx) for a in p.args]
        if isinstance(p, And):
            return False if False in vals else True if all(v_ is True for v_ in vals) else None
        return True if True in vals else False if all(v_ is False for v_ in vals) else None
    return _decide(p, point, ctx)


def _solved_both_readings(p, v, ctx: Ctx) -> sp.Set | None:
    """The solution set over ℝ of the relation `p` on `v`, under both readings of an odd root written as a
    power (SymPy solves on the principal branch, the curriculum reads the real root: x**(1/3) = x is
    {0, 1} and {-1, 0, 1}), their union; None when one is not solved exactly. The principal branch alone
    left out -1, and "Abs(x) = x" was verified under x**(1/3) = x (fourth audit, D4-ADIM-K); a point there
    is a convention (`Ctx.convention_region`) and decides nothing."""
    from ..equiv.numeric import real_odd_roots
    out = None
    for q in dict.fromkeys([p, real_odd_roots(p)]):
        # the written power read on the principal branch (a negative radicand: not real); the guarded
        # solveset alone leaves no set where the reading is a convention
        r = sb_run("mathverify.sandbox.ops:solveset_principal", q, v, S.Reals, timeout=ctx.timeout)
        if not r.ok or not isinstance(r.value, sp.Set) or r.value.has(sp.ConditionSet):
            return None
        out = r.value if out is None else sp.Union(out, r.value)
    return out


def _confined_values(v, rels: list, ctx: Ctx) -> list | None:
    """The values of `v` its domain (with the points where a range of the problem runs backwards) and the
    relations `rels` on `v` alone leave, when they are finitely many exact real numbers; None otherwise.
    A relation solveset cannot solve exactly is left out (the set stays a superset; each point is checked
    against every premise afterwards)."""
    region = sp.Union(ctx.domain_for(v), ctx.reversed_region(v))
    narrowed = False
    for p in rels:
        sol = _solved_both_readings(p, v, ctx)
        if sol is None:
            continue
        region = sp.Intersection(region, sol)
        narrowed = True
    if not narrowed:
        return None
    if region is S.EmptySet:
        return []
    if isinstance(region, sp.Range) and region.is_finite_set is True and region.size <= _MAX_INSTANCES:
        region = sp.FiniteSet(*region)       # integers between two bounds: 1 <= n <= 5
    if not isinstance(region, sp.FiniteSet) or len(region) > _MAX_INSTANCES:
        return None
    vals = list(region)
    if any(not isinstance(c, sp.Expr) or c.free_symbols or c.is_real is not True for c in vals):
        return None
    return vals


def _finite_instances(syms, premises: list, ctx: Ctx) -> tuple[list[dict], list[dict]] | None:
    """The points the premises allow for `syms` when they confine `syms`, and every symbol a premise links
    them to, to finitely many exact values: (the points where every premise holds and every symbol is in
    its domain, the points where that is undecided). A point where a Sum/Product range of the problem runs
    backwards is undecided (`Ctx.reversed_region`, DECISIONS §80). The symbols are confined one at a time
    (n**2 = 4, then y = x + 1 at each x), or all at once by a polynomial system (`_system_points`). None when
    a symbol is not confined to a finite set computed exactly, or the points are too many."""
    linked, names = _linked(_premise_parts(premises), syms)
    if not linked or len(names) > _MAX_LINKED or any(ctx.ns.get(q.name) != q for q in names):
        return None
    rels = [p for p in linked if isinstance(p, sp.core.relational.Relational)]
    order = sorted(names, key=lambda q: q.name)
    points: list[dict] = []

    def expand(pt: dict) -> bool:
        _tick()
        rest = [q for q in order if q not in pt]
        if not rest:
            points.append(pt)
            return len(points) <= _MAX_INSTANCES
        for v in rest:
            own = []
            for p in rels:
                q_ = p.xreplace(pt) if pt else p
                if isinstance(q_, sp.core.relational.Relational) and q_.free_symbols == {v}:
                    own.append(q_)
            vals = _confined_values(v, own, ctx) if own else None
            if vals is not None:
                return all(expand({**pt, v: c}) for c in vals)
        return False

    if not expand({}):
        # no symbol confined alone (x + y = 5, x - y = 1): the polynomial system, when it determines all
        points[:] = _system_points(rels, order, ctx) or []
        if not points:
            return None
    certain: list[dict] = []
    undecided: list[dict] = []
    for pt in points:
        state: bool | None = True
        for q, c in pt.items():
            inside = in_domain(ctx.domain_for(q), c)
            if inside is True:
                continue
            if inside is False and in_domain(ctx.reversed_region(q), c) is False:
                state = False
                break
            state = None                     # a reversed range there, or a membership undecided
        if state is not False:
            for p in linked:
                h = _holds_exactly(p, pt, ctx)
                if h is False:
                    state = False
                    break
                if h is None:
                    state = None
        if state is True:
            certain.append(pt)
        elif state is None:
            undecided.append(pt)
    return certain, undecided


def _proved_points(eqs: list, order: list, ctx: Ctx) -> list[dict] | None:
    """The real solutions of polynomial equations in the symbols `order`, when their list is PROVED
    complete (`certify.algebra._polynomial_system_worker`: a linear system, or a zero-dimensional ideal
    with as many proved distinct solutions as its radical's quotient dimension); None otherwise.
    `solve`'s list is no proof (round 5 of part d4b, 2 Oct 2026)."""
    r = sb_run("mathverify.certify.algebra:_polynomial_system_worker", eqs, order, timeout=ctx.timeout)
    if not r.ok or not isinstance(r.value, tuple) or r.value[0] is None:
        return None
    pts = r.value[0]
    if any(not isinstance(v, sp.Expr) or v.free_symbols for s_ in pts for v in s_.values()):
        return None
    return [dict(s_) for s_ in pts]


def _system_points(rels: list, order: list, ctx: Ctx) -> list[dict] | None:
    """The real solutions of the premises' equations when they are polynomial and determine every symbol
    in `order` (finitely many points, each exact) and their list is proved complete (`_proved_points`);
    None otherwise. `_check_eq_in` relies on that completeness (route 1, `exhaustive`)."""
    eqs = [p for p in rels if isinstance(p, Eq)]
    if not eqs or not all(_is_polynomial(p, order) for p in eqs):
        return None
    pts = _proved_points(eqs, order, ctx)
    if pts is None:
        return None
    out: list[dict] = []
    for s_ in pts:
        if not isinstance(s_, dict) or set(s_) != set(order):
            return None
        if any(not isinstance(v, sp.Expr) or v.free_symbols for v in s_.values()):
            return None
        if any(v.is_real is False for v in s_.values()):
            continue                         # a complex solution is no instance
        if any(v.is_real is not True for v in s_.values()):
            return None
        out.append(dict(s_))
    return out if 0 < len(out) <= _MAX_INSTANCES else None


def _counterexample_point(ev: dict, syms) -> dict | None:
    """The point at which the comparison of a `compute` claim found its sides to differ, read back from
    the evidence (`equiv.random_point`), or None."""
    from ..normalize.parse import parse_expr_str
    cx = ((ev.get("compare") or {}).get("random_point") or {}).get("counterexample")
    if cx is None:
        # an antiderivative certificate compares F' with the integrand on its own domain: its point
        # (D4-ADIM-E: Integral(Abs(x), x) = x**2/2 refuted at x < 0 on the task's [0, 2])
        cx = (((ev.get("antiderivative") or {}).get("random_point") or {}).get("counterexample")
              if isinstance(ev.get("antiderivative"), dict) else None)
    pt = cx.get("point") if isinstance(cx, dict) else None
    if not isinstance(pt, dict) or not pt:
        return None
    by_name = {q.name: q for q in syms}
    out: dict = {}
    for k, s_ in pt.items():
        q = by_name.get(k)
        if q is None:
            return None
        try:
            out[q] = parse_expr_str(str(s_))
        except Exception:  # noqa: BLE001
            return None
    return out


def _range_spans(claim) -> list:
    """The convention conditions of the claim that name a symbol (`certify.domain.is_convention`): the
    range of its own Sums and Products, `Contains(hi - lo + 1, FORWARD_SPANS)`, which holds where the range
    runs forward or is empty and is undecided where it runs backwards (hi < lo - 1); and the base of an
    odd root written as a power, of b**0, the arguments of C(n, r) and the divisor of Mod
    (`certify.domain.Convention`, part d4a), undecided where the value is a convention."""
    if not isinstance(claim, sp.Basic) or not claim.has(sp.Sum, sp.Product, sp.Pow, sp.binomial, sp.Mod):
        return []
    from ..certify.domain import definedness_conditions, is_value_convention
    try:
        conds = definedness_conditions(claim, None)
    except Exception:  # noqa: BLE001 - no conditions read: the claim is refuted as before
        return []
    # a closed one is left standing only where it is undecided (Mod(7, -5) = 2): no point decides it.
    # Where the other reading is "undefined" (0**0, C(2, 5)) a refutation stands (is_value_convention)
    return [c for c in conds if is_value_convention(c)]


def _runs_backwards_at(spans: list, point: dict) -> bool:
    """Is one of the ranges `spans` (`_range_spans`) not proved to run forward at `point` (symbols matched
    by name; a symbol the point does not fix leaves it undecided)? There the claim's value is a convention,
    SymPy's Karr sum (Σ_{k=3}^{1} k = -2) or the empty sum (0), not the curriculum's: the point is no
    counterexample and verifies nothing (DECISIONS §80). The parser refuses such a range written with
    numbers; with a symbol, the eq step `Sum(k, (k, 3, n)) = 0` under the given n = 1 was refuted with
    Karr's -2 and a solution with the right answer was INCORRECT (part 11, 1 Oct 2026)."""
    from ..certify.domain import decide_membership
    by_name = {str(k): v for k, v in point.items()}
    for c in spans:
        sub = {q: by_name[q.name] for q in c.free_symbols if q.name in by_name}
        try:
            held = decide_membership(c.args[0].xreplace(sub), c.args[1])
        except Exception:  # noqa: BLE001
            held = None
        if held is not True:
            return True
    return False


def _refutation_point(ev: dict, syms) -> dict | None:
    """The point a refutation was found at, read back from its evidence: the counterexample of the
    premises' route, the values the premises pin the symbols to, or the comparison's random point."""
    from ..normalize.parse import parse_expr_str
    for key in ("counterexample", "pinned_by_premises"):
        pt = ev.get(key)
        if isinstance(pt, dict) and pt:
            try:
                return {str(k): parse_expr_str(str(v)) for k, v in pt.items()}
            except Exception:  # noqa: BLE001
                return None
    return _counterexample_point(ev, syms)


def _symbolic_range_nodes(claim) -> list | None:
    """The Sums and Products of `claim` whose range names a free symbol of the claim (no bound variable of
    an enclosing binder), or None when one of them has several limits or a range that also names a bound
    variable (its empty reading is not built here)."""
    free = getattr(claim, "free_symbols", set())
    out = []
    for node in sp.preorder_traversal(claim):
        if not isinstance(node, (sp.Sum, sp.Product)):
            continue
        if any(len(lim) == 3 and (lim[2] - lim[1]).free_symbols for lim in node.limits):
            if len(node.limits) != 1 or not (node.limits[0][2] - node.limits[0][1]).free_symbols <= free:
                return None
            out.append(node)
    return out


def _named(point: dict, ctx: Ctx) -> dict | None:
    """A point read back from evidence (keys are names or symbols) with the problem's symbols as keys."""
    out = {}
    for k, v in point.items():
        q = ctx.ns.get(str(k))
        if not isinstance(q, sp.Symbol):
            return None
        out[q] = v
    return out


def _span_state(ranges: list, point: dict) -> str | None:
    """'forward' when every range (`Contains(hi - lo + 1, FORWARD_SPANS)`) runs forward or is empty at the
    point, 'backward' when one runs backwards there (hi < lo - 1), None when that is not decided."""
    from ..certify.domain import decide_membership
    state = "forward"
    for c in ranges:
        span = c.args[0].xreplace(point)
        if span.free_symbols:
            state = None
            continue
        if span.is_integer is True and span.is_negative is True:
            return "backward"
        try:
            held = decide_membership(span, c.args[1])
        except Exception:  # noqa: BLE001
            held = None
        if held is not True:
            state = None
    return state


def _empty_reading(claim, nodes: list, point: dict | None = None):
    """`claim` with every Sum/Product of `nodes` that runs backwards at `point` (each of them, without a
    point) read as the empty sum (0) or product (1), the reading other than Karr's (DECISIONS §80); None
    when the direction of one is not decided at the point."""
    rep = {}
    for node in nodes:
        _, lo, hi = node.limits[0]
        if point is not None:
            span = (hi - lo + 1).xreplace(point)
            if span.free_symbols or span.is_integer is not True:
                return None
            if span.is_negative is not True:
                continue
        rep[node] = S.Zero if isinstance(node, sp.Sum) else S.One
    return claim.xreplace(rep)


_KARR_ONLY = "verified_only_with_karr_where_a_range_runs_backwards"


def _forward_ranges_only(claim, ctx: Ctx, doms: dict | None, ev: dict) -> tuple[str, dict]:
    """A `compute` claim found equal on the compared sets, checked where one of its own Sum/Product ranges
    runs backwards there: SymPy's value at such a point is Karr's convention, and with the empty sum
    (§80's other reading) "Sum(k, (k, 1, n)) = n*(n + 1)/2" is false at n = -2 (0 != 1). Verified only when
    no compared point runs a range backwards, or the claim with those ranges read as empty (0, or 1 for a
    Product) is verified on those points too; otherwise unknown (`_KARR_ONLY`, fourth audit, D4-ADIM-H).
    The backward points are solved for a range on one symbol; with ranges on several symbols, or ranges
    whose backward sets differ, the claim is unknown."""
    from ..certify.domain import is_range_span
    ranges = [c for c in _range_spans(claim) if is_range_span(c) and c.free_symbols]
    if not ranges:
        return "verified", ev
    syms = set().union(*(c.free_symbols for c in ranges))
    nodes = _symbolic_range_nodes(claim)
    if len(syms) != 1 or nodes is None or any(ctx.ns.get(q.name) != q for q in syms):
        return "unknown", {**ev, "reason": _KARR_ONLY}
    (v,) = syms
    region = (doms or {}).get(v, ctx.domain_for(v))
    backs = []
    for c in ranges:
        _tick()
        r = sb_run("mathverify.sandbox.ops:solveset_in", sp.Lt(c.args[0], 0), v, region, timeout=ctx.timeout)
        if not r.ok or not isinstance(r.value, sp.Set) or r.value.has(sp.ConditionSet):
            return "unknown", {**ev, "reason": _KARR_ONLY}
        backs.append(r.value)
    try:
        empty = sp.Union(*backs).is_empty
    except Exception:  # noqa: BLE001
        empty = None
    if empty is True:
        return "verified", ev
    if len(set(backs)) != 1:
        return "unknown", {**ev, "reason": _KARR_ONLY}
    s2, ev2 = _check_compute(_empty_reading(claim, nodes), ctx, doms={**(doms or {}), v: backs[0]})
    if s2 == "verified":
        return "verified", {**ev, "empty_reading_where_a_range_runs_backwards": "verified"}
    return "unknown", {**ev, "reason": _KARR_ONLY, "empty_reading": {"status": s2, "reason": ev2.get("reason")}}


def _substituted(claim, point: dict):
    """The relation with `point` substituted, each side separately (Eq would evaluate itself)."""
    if isinstance(claim, sp.core.relational.Relational):
        return type(claim)(claim.lhs.xreplace(point), claim.rhs.xreplace(point), evaluate=False)
    return claim.xreplace(point)


_RANGE_PROBES = list(range(-8, 13)) + [20, 50]


def _binds_none_of(claim, syms) -> bool:
    """Does no operation of `claim` bind one of `syms` (a Sum/Product/Integral variable, a Limit's or a
    Derivative's variable, any other binder's)? Then `xreplace` of `syms` reaches only their free
    occurrences."""
    for node in sp.preorder_traversal(claim):
        if isinstance(node, (sp.Sum, sp.Product, sp.Integral)):
            bound = {lim[0] for lim in node.limits}
        elif isinstance(node, sp.Limit):
            bound = {node.args[1]}
        elif isinstance(node, sp.Derivative):
            bound = set(node.variables)
        else:
            bound = set(getattr(node, "bound_symbols", ()) or ())
        if bound & set(syms):
            return False
    return True


def _reading_free(nodes: list, point: dict, ctx: Ctx) -> bool:
    """Is the value of every Sum/Product of `nodes` that runs backwards at `point` the same under both
    readings, Karr's (SymPy's) and the empty sum (0) or product (1)? Then the claim's value there is no
    convention (Sum(0, (k, 1, n)) at n = -3); otherwise it is one, and the point decides nothing (part 11:
    floor(Σ_{k=3}^{1} k) is -2 or 0)."""
    if nodes is None:
        return False
    for node in nodes:
        _, lo, hi = node.limits[0]
        span = (hi - lo + 1).xreplace(point)
        if span.free_symbols or span.is_integer is not True:
            return False
        if span.is_negative is not True:
            continue
        empty = S.Zero if isinstance(node, sp.Sum) else S.One
        r = sb_run("mathverify.steps.deterministic:_doit", node.xreplace(point), timeout=ctx.timeout)
        if not r.ok or not isinstance(r.value, sp.Expr) or r.value.has(sp.Sum, sp.Product):
            return False
        d = sb_run("mathverify.sandbox.ops:simplify_diff", r.value, empty, timeout=ctx.timeout)
        if not d.ok or d.value != 0:
            return False
    return True


def _claim_reading_free(claim, nodes, point: dict, ctx: Ctx) -> bool:
    """Is each side of `claim` worth the same at `point` under both readings of its ranges that run
    backwards there, though a range's own value is not (55 + Sum(1, (k, 1, m)) - Sum(1, (j, 1, m)) is 55
    at m = -3 with Karr's -3 - (-3) and with the empty 0 - 0, d4g review B2)? `_reading_free` per side."""
    if nodes is None or not isinstance(claim, sp.core.relational.Relational):
        return False
    rep = {}
    for node in nodes:
        _, lo, hi = node.limits[0]
        span = (hi - lo + 1).xreplace(point)
        if span.free_symbols or span.is_integer is not True:
            return False
        if span.is_negative is True:
            rep[node] = S.Zero if isinstance(node, sp.Sum) else S.One
    for side in (claim.lhs, claim.rhs):
        r1 = sb_run("mathverify.steps.deterministic:_doit", side.xreplace(point), timeout=ctx.timeout)
        r2 = sb_run("mathverify.steps.deterministic:_doit", side.xreplace(rep).xreplace(point), timeout=ctx.timeout)
        if not (r1.ok and r2.ok) or any(not isinstance(r.value, sp.Basic) or r.value.has(sp.Sum, sp.Product)
                                         for r in (r1, r2)):
            return False
        d = sb_run("mathverify.sandbox.ops:simplify_diff", r1.value, r2.value, timeout=ctx.timeout)
        if not d.ok or d.value != 0:
            return False
    return True


def _neutralized(claim):
    """`claim` with every Sum/Product whose summand is identically 0 (a factor identically 1), inner ones
    first, replaced by that value: it is 0 (1) under every reading of its range, Karr's and the empty one,
    nested or not (Sum(Sum(0, (j, 1, k)), (k, 1, m)), Product(Product(1, ...), ...), d4g review B1, B5,
    B14-B16)."""
    if not isinstance(claim, sp.Basic) or not claim.has(sp.Sum, sp.Product):
        return claim
    rep: dict = {}
    for node in sp.postorder_traversal(claim):
        if isinstance(node, (sp.Sum, sp.Product)):
            neutral = S.Zero if isinstance(node, sp.Sum) else S.One
            body = node.function.xreplace(rep)
            try:
                if sp.expand(body - neutral) == 0:
                    rep[node] = neutral
            except Exception:  # noqa: BLE001
                continue
    return claim.xreplace(rep) if rep else claim


def _refuted_in_both_readings(claim, ranges: list, nodes, ctx: Ctx, premises: list, recheck) -> bool:
    """Is `claim` refuted, re-checked (`recheck`, the step's own check) at values of its ranges' symbols the
    premises allow, at a point where its value is no convention: where every range runs forward (both
    readings agree there), or where the ranges running backwards have the same value under both readings
    (`_reading_free`)? Values of at most two such symbols are probed; a premise that links them to another
    symbol leaves the question open (False)."""
    from itertools import product
    rsyms = set().union(*(c.free_symbols for c in ranges))
    if nodes is None or len(rsyms) > 2 or any(ctx.ns.get(q.name) != q for q in rsyms) \
            or not _binds_none_of(claim, rsyms):
        return False
    on = [p for p in _premise_parts(premises) if p.free_symbols & rsyms]
    if any(not p.free_symbols <= rsyms for p in on):
        return False
    order = sorted(rsyms, key=lambda q: q.name)
    fwd: list[dict] = []
    bwd: list[dict] = []
    for combo in product(_RANGE_PROBES, repeat=len(order)):
        pt = {q: sp.Integer(c) for q, c in zip(order, combo)}
        if any(in_domain(ctx.domain_for(q), v) is not True for q, v in pt.items()):
            continue
        if any(_holds_exactly(p, pt, ctx) is not True for p in on):
            continue
        st = _span_state(ranges, pt)
        if st == "forward" and len(fwd) < 3:
            fwd.append(pt)
        elif st == "backward" and len(bwd) < 3:
            bwd.append(pt)
    for pt in fwd:
        _tick()
        if recheck(_substituted(claim, pt)) == "refuted":
            return True
    for pt in bwd:
        _tick()
        if (_reading_free(nodes, pt, ctx) or _claim_reading_free(claim, nodes, pt, ctx)) and recheck(_substituted(claim, pt)) == "refuted":
            return True
    return False


def _refuted_where_backwards(claim, ev: dict, ctx: Ctx | None = None, premises: list = (),
                             recheck=None) -> bool:
    """Does the refutation of `claim` rest on a convention of one of its own operations (DECISIONS §80), so
    that it is withdrawn? Every route's point is checked here: the premises' solution set, a value pinned
    by a given (`floor` evaluated the pinned Sum, so the parser's range check missed it), a random point of
    the identity check.

    * A value convention other than a range (odd root, Mod divisor, part d4a): withdrawn when the point is
      not read back or does not decide it.
    * A Sum/Product range: the refutation stands where every range runs forward at the point. Where one
      runs backwards it stands only when the value there is the same under both readings, Karr's and the
      empty sum (`_reading_free`). Where the point is not read back or does not fix the range's symbols (a
      closed comparison after SymPy folded Sum(0, (k, 1, n - 5)) away, an antiderivative certificate, a
      random point of x alone), the claim is re-checked at values of those symbols
      (`_refuted_in_both_readings`): withdrawn unless refuted at such a point. Withdrawn before for any
      such point, a wrong step padded with a sum that is 0 under every reading was hidden (fourth audit,
      D4-ADIM-B)."""
    spans = _range_spans(claim)
    if not spans:
        return False
    from ..certify.domain import is_range_span
    pt = _refutation_point(ev, getattr(claim, "free_symbols", set()))
    others = [c for c in spans if not is_range_span(c)]
    ranges = [c for c in spans if is_range_span(c)]
    if others and (pt is None or _runs_backwards_at(others, pt)):
        return True
    if not ranges:
        return False
    if ctx is None or recheck is None:
        return pt is None or _runs_backwards_at(ranges, pt)
    # a Sum/Product that is 0 (1) under every reading takes no part (nested ones too, d4g review)
    claim = _neutralized(claim)
    ranges = [c for c in _range_spans(claim) if is_range_span(c)]
    if not ranges:
        return False
    point = _named(pt, ctx) if pt is not None else None
    state = _span_state(ranges, point) if point is not None else None
    nodes = _symbolic_range_nodes(claim)
    if state == "forward":
        return False
    if state == "backward":
        return not (_reading_free(nodes, point, ctx) or _claim_reading_free(claim, nodes, point, ctx))
    return not _refuted_in_both_readings(claim, ranges, nodes, ctx, list(premises), recheck)


def _undefined_at(conds, point: dict, ctx: Ctx) -> bool:
    """Is one of the claim's written conditions (`_written_relations`) false at the point (symbols matched
    by name)? There the claim, read as written, has no value (principle 12): the point neither refutes nor
    verifies it. A condition the point does not decide does not count."""
    by_name = {str(k): v for k, v in point.items()}
    for c in conds:
        sub = {q: by_name[q.name] for q in c.free_symbols if q.name in by_name}
        if len(sub) != len(c.free_symbols):
            continue
        if _decide(c, sub, ctx) is False:
            return True
    return False


def _check_at(claim, text: str, point: dict, ctx: Ctx, conds=()) -> tuple[str, dict]:
    """The `compute` claim checked at a point: the sides substituted separately (Eq would evaluate itself
    on substitution), a Sum/Product range there through the parser's range checks (reversed, or not an
    integer apart: the claim is not read there). A range that runs backwards at the point decides nothing,
    also when the substitution evaluated it away (`floor` of a pinned Sum: `_runs_backwards_at`). Nor does
    a point where the claim, read as written, is undefined (`conds`): sqrt(x**3) = x*sqrt(x) at x = -2,
    where neither side is real, was refuted (fourth audit, D4-ADIM-J)."""
    _tick()
    if _undefined_at(conds, point, ctx):
        return "unknown", {"reason": "claim_undefined_at_the_point"}
    pinned = Eq(claim.lhs.xreplace(point), claim.rhs.xreplace(point), evaluate=False)
    try:
        _refuse_reversed_ranges(pinned, text)
    except ParseError as e:
        return "unknown", {"reason": f"pinned_claim_not_read: {str(e)[:160]}"}
    if _runs_backwards_at(_range_spans(claim), point):
        return "unknown", {"reason": "a_range_of_the_claim_runs_backwards_at_the_point"}
    return _check_compute(pinned, ctx)


def _antiderivative_on_region(claim, ctx: Ctx, doms: dict) -> tuple[str, dict]:
    """An antiderivative claim `Integral(f, x) = F` checked on the region `doms` as F' = f: the certificate
    compares on its own domain, and its counterexample outside the region (x < 0 for the task's [0, 1])
    was no instance; a point of the region where F' != f is one (uni-010: the wrong antiderivative
    2*sqrt(x)*log(x) - 2*sqrt(x) of log(x)/sqrt(x) stays refuted under the task's interval)."""
    if not isinstance(claim, Eq):
        return "unknown", {}
    lhs, rhs = claim.lhs, claim.rhs
    if isinstance(rhs, sp.Integral) and not isinstance(lhs, sp.Integral):
        lhs, rhs = rhs, lhs
    if not isinstance(lhs, sp.Integral) or len(lhs.limits) != 1 or len(lhs.limits[0]) != 1 \
            or rhs.has(sp.Integral, sp.Limit, sp.Derivative, sp.Subs, sp.Sum, sp.Product):
        return "unknown", {}
    var = lhs.limits[0][0]
    r = sb_run("mathverify.steps.deterministic:_diff_doit", rhs.subs(sp.Symbol("C"), 0), var, timeout=ctx.timeout)
    if not r.ok:
        return "unknown", {}
    return _check_compute(Eq(r.value, lhs.function, evaluate=False), ctx, doms=doms)


def _closed_form_set(d) -> bool:
    """Is `d` a set the comparison can sample without deciding memberships in SymPy: an interval or a union
    of them, the integers or naturals, a Range, a finite set of real numbers, such a set minus finitely many
    points?"""
    if d in (S.Reals, S.Integers, S.Naturals, S.Naturals0) or isinstance(d, (sp.Interval, sp.Range)):
        return True
    if isinstance(d, sp.FiniteSet):
        return all(isinstance(c, sp.Expr) and not c.free_symbols and c.is_real is True for c in d)
    if isinstance(d, sp.Union):
        return all(_closed_form_set(a) for a in d.args)
    if isinstance(d, sp.Complement):
        return _closed_form_set(d.args[0]) and isinstance(d.args[1], sp.FiniteSet)
    return False


def _on_premises(claim, text: str, premises: list, ctx: Ctx, status: str, ev: dict,
                 conds=()) -> tuple[str, dict]:
    """A `compute` claim refuted as an identity (or a parametric form without a value), re-checked where
    the premises (the givens, the variables' constraints, the `eq` steps proved in the same branch) put
    its symbols. The identity's counterexample is no instance of the problem when the premises exclude
    it (principle 5): with n an integer, n**2 = 4 and n > 0, the right step "n**3 = 8" was refuted at
    n = 48, and with the given x > 0 "Abs(x) = x" at x = -0.00919 (part 10, 1 Oct 2026; `_pins` read only
    `s = c`).

    * The premises confine the symbols to finitely many exact values (`_finite_instances`): the claim is
      checked at each. Refuted at one where every premise holds: refuted there. Verified at every point
      not excluded: verified. Otherwise unknown; a point where a range of the problem runs backwards, or
      a premise is undecided, decides nothing (DECISIONS §80). No point at all (premises that contradict
      each other, a = 3 and a = 2): the identity check stands, as before.
    * Otherwise (a Limit or a Derivative in the claim, a premise linking a symbol that is not confined,
      too many values) a refutation stands when its point satisfies every premise on the claim's symbols
      alone. When it does not, the claim is compared again on the region those premises leave each
      symbol (solved exactly; a symbol confined to a few values at each value alone, `_region_cells`),
      and the new counterexample must satisfy them; while a point where a range of the problem runs
      backwards may be in the region, nothing is verified. Without such a counterexample one is searched
      where the premises hold (`_counterexample_on_premises`: on their equations' solutions, y = 2x + 1,
      or by sampling, x > y). A premise that also names a symbol outside the claim is not read here
      (x > 0 from x > y and y > 0 is not derived): that refutation stands.
    * `conds`, the claim's own written conditions (`_written_relations`), sort out its counterexamples too:
      a point where the claim has no value is none (D4-ADIM-J). They narrow the region a counterexample is
      searched in, never the region a refuted identity is verified on (verified only where the claim is
      defined, it is unknown).
    * The point of an antiderivative certificate is read back too (`_counterexample_point`, D4-ADIM-E); a
      refutation that names no point still stands.
    * A claim verified only with Karr's value of a range that may run backwards (`_KARR_ONLY`) is checked
      again on the region: the premises may leave no such point (n > 0)."""
    syms = getattr(claim, "free_symbols", None)
    if not isinstance(claim, Eq) or not syms or any(ctx.ns.get(q.name) != q for q in syms):
        return status, ev
    if _binders_keep_clear_of(claim, syms):
        _tick()
        inst = _finite_instances(syms, premises, ctx)
        if inst is not None:
            if inst[0] or inst[1]:
                return _check_instances(claim, text, syms, inst, ctx, ev, conds)
            return status, {**ev, "no_premise_instance": True}   # no instance at all: nothing to check it at
    if status != "refuted" and ev.get("reason") != _KARR_ONLY:
        return status, ev
    direct = [p for p in _premise_parts(premises) if p.free_symbols <= syms]
    own = [c for c in conds if c.free_symbols <= syms and c not in direct]
    if not direct and not own:
        return status, ev
    pt = _counterexample_point(ev, syms) if status == "refuted" else None
    if status == "refuted" and pt is None:
        return status, ev                    # no point read back: the refutation stands, as before
    if pt is not None and set(pt) == syms and all(_holds_exactly(p, pt, ctx) is True for p in direct) \
            and not _undefined_at(own, pt, ctx):
        return status, {**ev, "counterexample_satisfies_premises": True}
    # the region the premises leave each symbol alone (solved exactly), and within it the part where the
    # claim is defined as written
    region: dict = {}
    narrowed = False
    back: list = []
    for q in syms:
        dom, rev = ctx.domain_for(q), ctx.reversed_region(q)
        for part in (direct, own):
            before = dom
            for p in part:
                if p.free_symbols != {q} or not isinstance(p, sp.core.relational.Relational):
                    continue
                _tick()
                sol = _solved_both_readings(p, q, ctx)
                if sol is not None:
                    dom, rev = sp.Intersection(dom, sol), sp.Intersection(rev, sol)
            if part is own and dom != before:
                narrowed = True
        if dom != ctx.domain_for(q):
            region[q] = dom
        back.append(rev)
    if any(d is S.EmptySet for d in region.values()):
        return status, {**ev, "no_premise_instance": True}   # no instance: nothing to check it at

    def instance(p_):
        """Is the counterexample `p_` an instance? A symbol it does not fix was compared away (SymPy folded
        Sum(0, (k, 1, n - 5)), an antiderivative's derivative lost the constant): the refutation holds for
        each of its values, so a premise on such a symbol alone does not exclude it (D4-ADIM-B, -E); one
        that links it to a fixed symbol is not decided."""
        fixed = set(p_)
        for p in direct:
            if p.free_symbols <= fixed:
                if _holds_exactly(p, p_, ctx) is not True:
                    return False
            elif p.free_symbols & fixed:
                return False
        return not _undefined_at(own, p_, ctx)

    if pt is not None and set(pt) != syms and instance(pt):
        return status, {**ev, "counterexample_satisfies_premises": True}
    base = {"identity_refuted": ev, "premise_region": {str(k): str(v) for k, v in region.items()}}
    pending = None
    for doms in (_region_cells(region) if region else []):
        _tick()
        if not all(_closed_form_set(d) for d in doms.values()):
            # a set SymPy left unevaluated (the real roots of a cubic as an Intersection of radicals):
            # sampling it decides each membership in SymPy and took minutes (D4-ADIM-F)
            if pending is None:
                pending = ("unknown", {"reason": "premise_region_not_in_closed_form"})
            continue
        s2, ev2 = _check_compute(claim, ctx, doms=doms)
        if s2 == "refuted":
            pt2 = _counterexample_point(ev2, syms)
            if pt2 is not None and instance(pt2):
                return "refuted", {**ev2, **base, "counterexample": {str(k): str(v) for k, v in pt2.items()}}
            s3, ev3 = _antiderivative_on_region(claim, ctx, doms)
            pt3 = _counterexample_point(ev3, syms) if s3 == "refuted" else None
            if pt3 is not None and instance(pt3):
                return "refuted", {**ev3, **base, "counterexample": {str(k): str(v) for k, v in pt3.items()}}
            s2 = "unknown"
            ev2 = {**ev2, "reason": "counterexample_not_proved_an_instance"}
        if s2 != "verified" and pending is None:
            pending = (s2, ev2)
    if region and pending is None:
        try:
            reversed_left = any(b.is_empty is not True for b in back)
        except Exception:  # noqa: BLE001
            reversed_left = True
        if reversed_left:
            # a point where a range of the problem runs backwards may be an instance: no verification
            return "unknown", {**base, "reason": "reversed_range_points_undecided"}
        if narrowed and status == "refuted":
            # verified only where the claim is defined as written, a part of what the premises allow:
            # outside it the claim has no value, which verifies nothing either
            return "unknown", {**base, "reason": "verified_only_where_the_claim_is_defined"}
        return "verified", base
    # no counterexample the premises allow yet: one is searched where they put the symbols
    if _binders_keep_clear_of(claim, syms):
        found = _counterexample_on_premises(claim, text, direct, syms, ctx, region, own)
        if found is not None:
            return "refuted", {**found[1], **base, "counterexample": {str(k): str(v) for k, v in found[0].items()}}
    if pending is None:
        return "unknown", {**base, "reason": "identity_counterexample_not_an_instance"}
    return "unknown", {**pending[1], **base, "reason": pending[1].get("reason") or "undecided_on_the_premise_region"}


_MAX_TRIES = 6                       # premise-satisfying points the claim is checked at in the search


def _counterexample_on_premises(claim, text: str, direct: list, syms, ctx: Ctx, region: dict, own=()):
    """(a point every premise in `direct` holds at, where the claim is refuted, the evidence), or None:
    searched on the solutions of the premises' equations (a parametric solution sampled: y = 2x + 1) or,
    without equations, among sample points of the region (x > y). At most _MAX_TRIES points are checked.
    A point where the claim is undefined as written (`own`) is none (`_check_at`); a region not in closed
    form (`_closed_form_set`) is not sampled."""
    order = sorted(syms, key=lambda q: q.name)
    doms = {q: region.get(q, ctx.domain_for(q)) for q in order}
    eqs = [p for p in direct if isinstance(p, Eq)]
    cands: list[dict] = []
    if eqs:
        _tick()
        r = sb_run("mathverify.sandbox.ops:solve_system", eqs, order, True, timeout=ctx.timeout)
        for s_ in (r.value if r.ok and isinstance(r.value, list) else []):
            if not isinstance(s_, dict):
                continue
            rem = set(order) - set(s_)
            for v in s_.values():
                rem |= getattr(v, "free_symbols", set())
            if rem - set(order):
                continue
            rdoms = {q: doms[q] for q in sorted(rem, key=lambda q: q.name)}
            if rem and not all(_closed_form_set(d) for d in rdoms.values()):
                continue
            for pt in (sample_points(rdoms, 12, ctx.seed) + _small_integer_grid(rdoms)[:12] if rem else [{}]):
                full = {k: v.xreplace(pt) for k, v in s_.items()}
                full.update(pt)
                cands.append(full)
    elif all(_closed_form_set(d) for d in doms.values()):
        cands = sample_points(doms, 30, ctx.seed) + _small_integer_grid(doms)[:30]
    tried = 0
    for pt in cands:
        _tick()
        if set(pt) != set(order) or any(getattr(v, "free_symbols", True) for v in pt.values()):
            continue
        if not _in_domains(ctx, pt) or any(_holds(p, pt) is not True for p in direct):
            continue
        if any(_holds_exactly(p, pt, ctx) is not True for p in direct):
            continue
        tried += 1
        s_, e_ = _check_at(claim, text, pt, ctx, own)
        if s_ == "refuted":
            return pt, e_
        if tried >= _MAX_TRIES:
            break
    return None


def _region_cells(region: dict) -> list[dict]:
    """The premise region split so that a symbol confined to a few values is compared at each value alone
    (a random choice from a finite set may miss one); `region` itself when the cells would be too many."""
    from itertools import product
    choices = []
    for q, d in region.items():
        if isinstance(d, sp.Range) and d.is_finite_set is True and d.size <= _MAX_INSTANCES:
            d = sp.FiniteSet(*d)
        if isinstance(d, sp.FiniteSet) and len(d) <= _MAX_INSTANCES:
            choices.append([(q, sp.FiniteSet(c)) for c in d])
        else:
            choices.append([(q, d)])
    n = 1
    for c in choices:
        n *= len(c)
    if n > _MAX_INSTANCES:
        return [region]
    return [dict(cell) for cell in product(*choices)]


def _check_instances(claim, text: str, syms, inst, ctx: Ctx, ev: dict, conds=()) -> tuple[str, dict]:
    certain, undecided = inst
    base = {"identity_refuted": ev, "instances_by_premises": {
        "certain": [{str(k): str(v) for k, v in pt.items() if k in syms} for pt in certain],
        "undecided": [{str(k): str(v) for k, v in pt.items() if k in syms} for pt in undecided]}}
    seen: dict = {}

    def at(pt):
        key = tuple(sorted(((str(k), sp.srepr(v)) for k, v in pt.items() if k in syms)))
        if key not in seen:
            seen[key] = _check_at(claim, text, {k: v for k, v in pt.items() if k in syms}, ctx, conds)
        return seen[key]

    for pt in certain:
        s_, e_ = at(pt)
        if s_ == "refuted":
            return "refuted", {**e_, **base, "counterexample": {str(k): str(v) for k, v in pt.items() if k in syms}}
    pending = None
    for pt in certain + undecided:
        s_, e_ = at(pt)
        if s_ != "verified":
            pending = {"at": {str(k): str(v) for k, v in pt.items() if k in syms}, "status": s_,
                       "reason": e_.get("reason")}
            break
    if pending is None:
        return "verified", base
    return "unknown", {**base, "reason": "not_decided_at_every_instance", "undecided_at": pending}


def _diff_doit(e, var):
    from ..certify.calculus import classical
    return sp.simplify(classical(sp.diff(e, var).doit()))


def _doit(e):
    return sp.simplify(e.doit())


def _small_integer_grid(doms: dict) -> list[dict]:
    """Deterministic small values for integer-domain symbols (TYT solutions are small):
    guarantees that a diophantine premise like 3x+5y=41 gets hit by an integer point."""
    int_syms = [q for q, d in doms.items() if d.is_subset(S.Integers)]
    if not int_syms or len(int_syms) > 2:
        return []
    vals = list(range(-12, 41))
    pts: list[dict] = []
    if len(int_syms) == 1:
        q = int_syms[0]
        for v in vals:
            if doms[q].contains(v) == True:  # noqa: E712
                pts.append({q: sp.Integer(v)})
    else:
        a, b = int_syms
        for va in range(-6, 21):
            for vb in range(-6, 21):
                if doms[a].contains(va) == True and doms[b].contains(vb) == True:  # noqa: E712
                    pts.append({a: sp.Integer(va), b: sp.Integer(vb)})
    # non-integer symbols in the same domain map get a fixed sample so the point is complete
    for q, d in doms.items():
        if q in int_syms:
            continue
        for pt in pts:
            pt[q] = sp.Rational(1, 2) if d.contains(sp.Rational(1, 2)) == True else sp.Integer(2)  # noqa: E712
    return pts


def _negation(claim):
    if isinstance(claim, Eq):
        return sp.Ne(claim.lhs, claim.rhs)
    if isinstance(claim, sp.core.relational.Relational):
        return claim.negated
    return None


def _claim_parts(claim) -> list | None:
    """The relations an And/Or claim is made of (a chain `0 <= p <= 1`, a choice `x in {1, 2}`),
    None when a part is not a plain relation."""
    parts = list(claim.args)
    return parts if all(isinstance(a, sp.core.relational.Relational) for a in parts) else None


def _fail_set(claim, v, region, ctx: Ctx):
    """The part of `region` where the claim is false, or None when it cannot be computed exactly."""
    neg = _negation(claim)
    if neg is not None:
        rb = sb_run("mathverify.sandbox.ops:solveset_in", neg, v, region, timeout=ctx.timeout)
        return rb.value if rb.ok and not rb.value.has(sp.ConditionSet) else None
    parts = _claim_parts(claim) if isinstance(claim, (And, Or)) else None
    if parts is None:
        return None
    sets = []
    for a in parts:
        r = sb_run("mathverify.sandbox.ops:solveset_in", a, v, S.Reals, timeout=ctx.timeout)
        if not r.ok or r.value.has(sp.ConditionSet):
            return None
        sets.append(r.value)
    rb = sb_run("mathverify.steps.deterministic:_outside", region, sets, isinstance(claim, And), timeout=ctx.timeout)
    return rb.value if rb.ok and not rb.value.has(sp.ConditionSet) else None


def _outside(region, sets, conjunction: bool):
    from ..equiv.sets import unify_endpoints
    region, *sets = unify_endpoints([region, *sets])      # raises when two endpoints are undecided
    inside =sp.Intersection(*sets) if conjunction else sp.Union(*sets)
    return sp.Complement(region, inside)


def _set_counterexample(claim, premises: list, v, ctx: Ctx) -> tuple[dict | None, bool, bool]:
    """(a point of the premises' solution set, within the domain, where the claim is false; whether
    the claim is PROVED on that set; whether that set is PROVED empty). Proved means the premises'
    set is exactly computed, not empty, and the part of it where the claim fails is exactly empty.
    An And/Or claim was never tried here: "x in {pi/6, 5*pi/6}" under cos 2x = 1/2 on [0, 2*pi) was
    not refuted, and `solve`'s two principal roots made it "verified" (ayt-trig-010, 28 Sep 2026)."""
    from ..certify.calculus import _points_of
    if any(not isinstance(p, sp.core.relational.Relational) for p in premises):
        return None, False, False
    region = ctx.domain_for(v) if v.name in ctx.ns else S.Reals
    # the points where a value of the problem is a convention: an instance there (x = -1 of
    # x**(1/3) = x under the real root) is neither in nor out, so nothing is proved while one may exist
    conv = ctx.convention_region(v) if v.name in ctx.ns else S.EmptySet
    from ..equiv.numeric import real_odd_roots
    from ..sandbox.exactsets import at_risk
    periodic = []
    for p in premises:
        if at_risk(p, v) and real_odd_roots(p) == p:
            periodic.append(p)
            continue
        sol = _solved_both_readings(p, v, ctx)
        if sol is None:
            return None, False, False
        region = sp.Intersection(region, sol)
        conv = sp.Intersection(conv, sol)
    if periodic:
        # a premise with a trigonometric function is solved on what the others leave (Ctx.cut_by): on ℝ
        # SymPy reads it on one period (sandbox.exactsets), and the written cos(x) != 0 of tan x = sqrt(3)
        # on [0, pi) then left no exact set at all
        region = ctx.cut_by(v, region, periodic)
        if region is None:
            return None, False, False
        if conv is not S.EmptySet:
            conv = sp.Intersection(conv, *[sp.ConditionSet(v, p, S.Reals) for p in periodic])
    fail = _fail_set(claim, v, region, ctx)
    if fail is None:
        return None, False, False
    if fail is S.EmptySet:
        try:
            clear = conv.is_empty is True
        except Exception:  # noqa: BLE001
            clear = False
        if not clear:
            return None, False, False
        e = sb_run("mathverify.steps.deterministic:_emptiness", region, timeout=ctx.timeout)
        return None, bool(e.ok and e.value is False), bool(e.ok and e.value is True)
    spans = _range_spans(claim)
    for pt in _points_of(fail):
        point = {v: pt}
        if not _in_domains(ctx, point):
            continue
        if _runs_backwards_at(spans, point):
            continue                         # the claim's value there is a convention (part 11)
        if all(_decide(p, point, ctx) is True for p in premises) and _decide(claim, point, ctx) is False:
            return point, False, False
    return None, False, False


def _emptiness(s) -> bool | None:
    """SymPy's decision on whether the set is empty; None when undecided. Only False proves a claim
    on the set: a vacuous proof is no proof."""
    return s.is_empty


def _decide(rel, point: dict, ctx: Ctx) -> bool | None:
    """Truth of a relation at a point, exact at exact zeros: the difference of the sides is
    simplified first, and a numeric sign is only trusted when it is far from zero. `_holds`
    compares tolerantly, which misreads x^2 - 2x - 1 >= 0 at x = 1 - sqrt(2) (measured; on 28 Sep 2026
    `_holds` read it right, and agreed with this function on every boundary point tried)."""
    if isinstance(rel, (And, Or)):
        vals = [_decide(a, point, ctx) for a in rel.args]
        if isinstance(rel, And):
            return False if False in vals else True if all(v_ is True for v_ in vals) else None
        return True if True in vals else False if all(v_ is False for v_ in vals) else None
    if not isinstance(rel, sp.core.relational.Relational):
        return None
    try:
        a, b = rel.lhs.subs(point, simultaneous=True), rel.rhs.subs(point, simultaneous=True)
    except Exception:  # noqa: BLE001
        return None
    if a.free_symbols or b.free_symbols:
        return None
    from ..equiv.forms import UnverifiedForm, checked_forms
    try:
        a, b = checked_forms(a, ctx.timeout), checked_forms(b, ctx.timeout)
    except UnverifiedForm:
        return None                       # SymPy's closed form unconfirmed: simplify would trust it
    r = sb_run("mathverify.sandbox.ops:simplify_diff", a, b, timeout=ctx.timeout)
    if not r.ok:
        return None
    d = r.value
    if d == 0:
        sign = 0
    elif isinstance(d, sp.Rational):
        # an exact difference has an exact sign, however small: with SymPy's confirmed 0 for
        # ∫_0^{2π} sin x dx, the step "∫_0^{2π} sin x dx = 10^-40" went undecided below (30 Sep 2026)
        sign = 1 if d > 0 else -1
    else:
        # evaluated in the sandbox, bounded in time: one in-process evaluation held the GIL for minutes
        # (d4g review S8-S12)
        r = sb_run("mathverify.steps.deterministic:_numeric_sign", d, a, b, timeout=_bounded(ctx.timeout))
        if not r.ok or r.value is None or r.value == "small":
            return None
        if r.value == "complex":
            return None if isinstance(rel, (Eq, sp.Ne)) else False
        sign = r.value
    if isinstance(rel, Eq):
        return sign == 0
    if isinstance(rel, sp.Ne):
        return sign != 0
    if isinstance(rel, sp.StrictLessThan):
        return sign < 0
    if isinstance(rel, sp.LessThan):
        return sign <= 0
    if isinstance(rel, sp.StrictGreaterThan):
        return sign > 0
    if isinstance(rel, sp.GreaterThan):
        return sign >= 0
    return None


def _numeric_sign(d, a, b):
    """The sign of the difference `d` of `a` and `b` at 60 digits, trusted only far from zero: 1 or -1,
    "small" (within 1e-40 of the larger side), "complex", or None (not evaluated). Run in the sandbox."""
    from ..equiv.numeric import to_mp
    import mpmath as mp
    try:
        dv = to_mp(d, 60)
        av, bv = to_mp(a, 60), to_mp(b, 60)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(dv, mp.mpc) or isinstance(av, mp.mpc) or isinstance(bv, mp.mpc):
        return "complex"
    scale = max(abs(av), abs(bv), mp.mpf(1))
    if abs(dv) <= mp.mpf(10) ** -40 * scale:
        return "small"
    return 1 if dv > 0 else -1


def _inline_call(fn_path: str, *args):
    """`fn_path(*args)` in the sandbox's worker, its own CAS calls inline there (see _sandboxed_equivalent)."""
    import os
    from ..sandbox.pool import _resolve
    os.environ["MATHVERIFY_SANDBOX"] = "inline"
    return _resolve(fn_path)(*args)


def _bounded(t: float) -> float:
    """A sandbox timeout of at most `t` seconds that does not run past the step's budget."""
    d = _deadline.get()
    return t if d is None else max(1.0, min(t, d - time.monotonic()))


def _is_assignment(claim) -> bool:
    """An equation, or a finite choice of equations (`x in {1, 2}`): the shape of "let n = 20"."""
    return isinstance(claim, Eq) or (isinstance(claim, Or) and all(isinstance(a, Eq) for a in claim.args))


def _outside_domain(claim, ctx: Ctx) -> bool:
    """True when the assignment has one variable and no value of its domain satisfies it (proved):
    "n = 0" for a positive integer n, "n = 2" where the declared constraints leave only n = 1. Such a
    step defines nothing, every instance of the problem contradicts it; made definitional with
    "n = 20", it was no longer refuted and a solution with it and the right answer became CORRECT
    (probe of 28 Sep 2026; refuted before). Anything undecided is False: the step stays a definition."""
    if len(claim.free_symbols) != 1:
        return False
    (v,) = claim.free_symbols
    if ctx.ns.get(v.name) != v:
        return False
    # a point where a value of the problem is a convention (x = 0 next to x**0) is not outside it
    dom = sp.Union(ctx.domain_for(v), ctx.convention_region(v))
    for part in (claim.args if isinstance(claim, Or) else (claim,)):
        r = sb_run("mathverify.sandbox.ops:solveset_in", part, v, dom, timeout=ctx.timeout)
        if not r.ok or r.value.has(sp.ConditionSet):
            return False
        e = sb_run("mathverify.steps.deterministic:_emptiness", r.value, timeout=ctx.timeout)
        if not (e.ok and e.value is True):
            return False
    return True


def _nowhere_true(claim, ctx: Ctx) -> dict | None:
    """A point of the (single) variable's domain where the claim is false, checked exactly."""
    (v,) = claim.free_symbols
    dom = ctx.domain_for(v)
    for c in (0, 1, -1, 2, sp.Rational(1, 2), 10):
        try:
            if dom.contains(c) is not sp.true:
                continue
        except Exception:  # noqa: BLE001
            continue
        if _holds(claim, {v: sp.Integer(c) if isinstance(c, int) else c}) is False:
            return {str(v): str(c)}
    return None


def _point_symbol(claim, ctx: Ctx):
    """The symbol a claim gives a constant value ("x = 0", "y = -1", "x in {1, 2}"), else None."""
    sym = None
    for a in (claim.args if isinstance(claim, Or) else (claim,)):
        if not isinstance(a, Eq):
            return None
        side = next((s_ for s_, o in ((a.lhs, a.rhs), (a.rhs, a.lhs))
                     if isinstance(s_, sp.Symbol) and not o.free_symbols), None)
        if side is None or ctx.ns.get(side.name) != side or (sym is not None and side != sym):
            return None
        sym = side
    return sym


def _has_continuum(s) -> bool:
    """True when the set holds an interval of positive length. A discrete infinite set (the roots
    k*pi + pi/3 of tan x = sqrt(3), the natural numbers) does not: a value picked from it is a root,
    to be checked, not a free choice."""
    if s == S.Reals:
        return True
    if isinstance(s, sp.Interval):
        return bool((s.measure > 0) == True)  # noqa: E712 (sympy tri-state)
    if isinstance(s, sp.Union):
        return any(_has_continuum(a) for a in s.args)
    if isinstance(s, sp.Complement):
        return _has_continuum(s.args[0]) and s.args[1].is_finite_set is True
    return False


def _continuum(s, ctx: Ctx) -> bool:
    r = sb_run("mathverify.steps.deterministic:_has_continuum", s, timeout=ctx.timeout)
    return bool(r.ok and r.value is True)


def _free_choice(claim, v, premises: list, ctx: Ctx) -> dict | None:
    """A witness when the premises leave `v` free over a continuum and the claim's value of `v` is
    one of those they allow; None otherwise. "x = 0" after the line y = 2x − 1 is then a CHOICE (the
    point where the line meets the y-axis), not a consequence: it was refuted and a right solution
    was INCORRECT (V13, 28 Sep 2026). A value the premises exclude is still refuted, and so is one
    picked from a finite or discrete set (a root of x² = 4, of tan x = sqrt(3))."""
    if any(not isinstance(p, sp.core.relational.Relational) for p in premises):
        return None
    syms = set().union({v}, *(p.free_symbols for p in premises))
    if any(ctx.ns.get(q.name) != q for q in syms):
        return None
    eqs = [p for p in premises if isinstance(p, Eq)]
    if syms == {v} or not eqs:
        region = ctx.domain_for(v)
        for p in premises:
            if p.free_symbols == {v}:
                r = sb_run("mathverify.sandbox.ops:solveset_in", p, v, S.Reals, timeout=ctx.timeout)
                if not r.ok or r.value.has(sp.ConditionSet):
                    return None
                region = sp.Intersection(region, r.value)
        if not _continuum(region, ctx):
            return None
    else:
        r = sb_run("mathverify.sandbox.ops:solve_system", eqs, sorted(syms, key=lambda s_: s_.name), True,
                   timeout=ctx.timeout)
        sols = [s_ for s_ in r.value if isinstance(s_, dict)] if r.ok and isinstance(r.value, list) else []
        if not sols:
            return None
        params = set()
        for s_ in sols:
            params |= s_[v].free_symbols if v in s_ else {v}
        if not any(_continuum(ctx.domain_for(q), ctx) for q in params):
            return None
    for part in (claim.args if isinstance(claim, Or) else (claim,)):
        c = part.rhs if part.lhs == v else part.lhs
        rest = sorted(syms - {v}, key=lambda s_: s_.name)
        cands: list[dict] = [{}]
        if rest:
            sub = [p.subs(v, c) for p in eqs]
            sub = [p for p in sub if p is not sp.true]
            cands = []
            if sub and all(isinstance(p, Eq) for p in sub):
                r = sb_run("mathverify.sandbox.ops:solve_system", sub, rest, True, timeout=ctx.timeout)
                for s_ in (r.value if r.ok and isinstance(r.value, list) else []):
                    if isinstance(s_, dict):
                        free = {q: sp.Integer(0) for q in rest if q not in s_}
                        free.update({q: sp.Integer(0) for e in s_.values() for q in e.free_symbols})
                        cands.append({q: s_.get(q, q).subs(free) for q in rest})
            if not sub:
                cands = sample_points({q: ctx.domain_for(q) for q in rest}, 24, ctx.seed)
        for pt in cands:
            point = {v: c, **pt}
            if _in_domains(ctx, point) and all(_decide(p, point, ctx) is True for p in premises):
                return point
    return None


def _check_eq(claim, premises: list, ctx: Ctx, restrictions: list = (), window: list = ()) -> tuple[str, dict]:
    """`premises`: the givens, earlier claims and case assumptions. `restrictions`: the variables'
    domain constraints (`var_constraints`). `window`: the task's own interval for its variable
    (`_task_window`). All three bound the counterexample search; they differ in what they BIND.

    The window only counts when the premises have an instance inside it. When they have none, every
    claim held vacuously: "x = 3" from 3x² − 3 = 0 (roots ±1) on the interval [2, 4] was no longer
    refuted, and a solution with that wrong step and the right maximum became CORRECT (probe of
    28 Sep 2026; refuted before the window existed). The step is then checked without the window."""
    status, ev = _check_eq_in(claim, premises, ctx, restrictions, window)
    if ev.pop("_window_without_instance", False):
        status, ev = _check_eq_in(claim, premises, ctx, restrictions, ())
        ev["window_dropped"] = "no_premise_instance_inside_the_task_interval"
    return status, ev


def _closed_claim(claim, ctx: Ctx) -> str:
    """A claim with no free symbol is true or false whatever the premises: decided exactly on its own
    (`_decide`); a numeric evaluation that tells the sides apart refutes it too. Sent through the
    premises' set route, a closed relation SymPy could not decide came back "proved": the LaTeX step
    "\\gcd(84, 120) = 7" and "gcd(pi, 2) != 1" were verified (audit of 29 Sep 2026)."""
    h = True if claim is sp.true else False if claim is sp.false else _decide(claim, {}, ctx)
    if h is None:
        if not isinstance(claim, sp.Basic) or not claim.has(sp.Integral, sp.Sum, sp.Product, sp.Limit, sp.Derivative):
            h = False if _holds(claim, {}) is False else None
        elif _integrals_refute(claim, ctx) or _limits_refute(claim, ctx):
            h = False
    return "verified" if h is True else "refuted" if h is False else "unknown"


def _limits_refute(claim, ctx: Ctx) -> bool:
    """A closed equation with a limit that does not exist is false, as `_check_compute` rules for a
    compute step: the eq step "\\lim_{x \\to 2} |x - 2|/(x - 2) = 1" (two-sided: the one-sided limits
    are 1 and -1) was left unknown and its solution certified CORRECT (third audit of 30 Sep 2026, N3).
    A limit that exists but is infinite against a finite side, or finite against an infinite one, is
    false too; `_decide` cannot tell (its difference oo - 5 is no number it compares). Each limit is
    classified by `classify_limit` (two-sided unless a side is written, both sides corroborated
    numerically); an undecided classification refutes nothing (principle 5)."""
    if not isinstance(claim, Eq):
        return False
    from ..certify.limits import classify_limit
    lims = [L for L in claim.atoms(sp.Limit) if not L.free_symbols]
    for L in lims:
        e_, v_, p_, d_ = L.args
        side = None if str(d_) in ("+-", "real") else str(d_)
        cls = classify_limit(e_, v_, p_, side, timeout=ctx.timeout)
        if cls.get("kind") == "DNE":
            return True
        if L in (claim.lhs, claim.rhs) and cls.get("kind") in ("VAR", "INF") and cls.get("value") is not None:
            other = claim.rhs if L == claim.lhs else claim.lhs
            if not other.is_number or other.has(sp.Integral, sp.Sum, sp.Product, sp.Limit, sp.Derivative,
                                                 sp.zoo, sp.nan):
                continue
            val = cls["value"]
            if val in (sp.oo, -sp.oo) and other in (sp.oo, -sp.oo):
                if val != other:
                    return True
            elif (val in (sp.oo, -sp.oo)) != (other in (sp.oo, -sp.oo)) and \
                    (val in (sp.oo, -sp.oo) or val.is_finite) and (other in (sp.oo, -sp.oo) or other.is_finite):
                return True
    return False


def _integrals_refute(claim, ctx: Ctx) -> bool:
    """A closed equation whose only forms are integrals over finite ranges is refuted when, with each
    integral replaced by a RIGOROUS enclosure (`certify.calculus.rigorous_integral`, interval
    arithmetic), the interval value of lhs - rhs excludes 0: "Integral(Abs(cos(x)), (x, -1, 1)) = 0"
    stays refuted where SymPy's closed form is wrong. A quadrature's error estimate is no enclosure:
    tanh-sinh and Gauss-Legendre missed a narrow sech² peak together and refuted a true value (review
    of d4c, 2 Oct 2026), and SymPy's evalf of the Dirichlet integral, '-0.e+0', refuted
    "∫_0^oo sin x/x dx = π/2" (S3); an infinite range refutes nothing. The tolerant `_holds` is not used
    over forms: its value of a sum (Euler-Maclaurin) is wrong for oscillating terms (Σ cos(πk/4)/k² came
    out 0.565345, it is 11π²/192 = 0.565446) and refuted true identities; nor over a sum or product at
    all (audit of 29 Sep 2026)."""
    if not isinstance(claim, Eq) or claim.has(sp.Sum, sp.Product, sp.Limit, sp.Derivative):
        return False
    import mpmath as mp
    from ..certify.calculus import integral_excludes, rigorous_integral
    from ..certify.enclosure import Unsupported, iv_eval
    forms = list(claim.atoms(sp.Integral))
    if not forms or len(forms) > 3:
        return False
    for n in forms:
        if n.free_symbols or len(n.limits) != 1 or len(n.limits[0]) != 3:
            return False
    if len(forms) == 1 and forms[0] in (claim.lhs, claim.rhs):
        # one integral equated with a number: refine the enclosure against that number
        n = forms[0]
        other = claim.rhs if n == claim.lhs else claim.lhs
        var, a, b = n.limits[0]
        return integral_excludes(n.function, var, a, b, other, timeout=ctx.timeout)[0]
    env = {}
    for n in forms:
        var, a, b = n.limits[0]
        enc = rigorous_integral(n.function, var, a, b, timeout=ctx.timeout)
        if enc is None or not (mp.isfinite(enc[0]) and mp.isfinite(enc[1])):
            return False
        env[n] = mp.iv.mpf([enc[0], enc[1]])
    reps = {n: sp.Dummy(f"I{k}") for k, n in enumerate(forms)}
    try:
        mp.iv.dps = 30
        d = iv_eval((claim.lhs - claim.rhs).xreplace(reps), {reps[n]: env[n] for n in forms})
        lo, hi = d._mpi_
        lo, hi = mp.make_mpf(lo), mp.make_mpf(hi)
    except (Unsupported, ArithmeticError, ValueError, TypeError):
        return False
    return bool(not (mp.isnan(lo) or mp.isnan(hi)) and (lo > 0 or hi < 0))


def _check_eq_in(claim, premises: list, ctx: Ctx, restrictions: list, window: list) -> tuple[str, dict]:
    if _jump_undecided(claim, *premises):
        return "unknown", {"reason": "jump_of_an_unproved_number"}
    if not getattr(claim, "free_symbols", None):
        return _closed_claim(claim, ctx), {"n_premises": len(premises), "route": "closed_claim"}
    syms = set(claim.free_symbols)
    prem_syms: set = set()
    for p in premises:
        syms |= p.free_symbols
        prem_syms |= p.free_symbols
    # A domain restriction only narrows a symbol, it never determines one: an assignment whose
    # symbols nothing but their domains constrain is a definition. "n = 20" (the 20th term) was
    # refuted with the point {k: 109, n: 50}, which satisfies only k > 0 and n > 0 and is no
    # instance of the problem (K4, 28 Sep 2026: 11 correct ayt-diz solutions). An inequality still
    # counts them: "x >= 3" against the written condition x - 2 >= 0 is a refutable consequence. So
    # does an assignment no value of the domain satisfies (`_outside_domain`).
    binds = not _is_assignment(claim) or (not claim.free_symbols <= prem_syms and _outside_domain(claim, ctx))
    for p in restrictions:
        syms |= p.free_symbols
        if binds:
            prem_syms |= p.free_symbols
    # The window binds nothing, so the definitional test below is the same with or without it and
    # it can only shrink the set a counterexample is drawn from. It joins only when its variable
    # is already in play.
    window = [w for w in window if w.free_symbols <= syms]
    base = list(premises) + list(restrictions)
    premises = base + window
    ev: dict[str, Any] = {"n_premises": len(premises)}
    # A claim that introduces symbols the premises do not constrain is *definitional*
    # ("the tangent line is y = 2x - 1", "let x = 4") and cannot be refuted as a
    # consequence. The only refutable shape without premise support is an identity
    # candidate: both sides depend on exactly the same symbols (sin(3x) = 3 sin x).
    new_syms = set(claim.free_symbols) - prem_syms
    if new_syms:
        identity_shaped = (isinstance(claim, Eq) and claim.lhs.free_symbols == claim.rhs.free_symbols
                           and bool(claim.lhs.free_symbols))
        if not identity_shaped:
            # a "definition" no value of its variable's domain satisfies defines nothing: x**2 + 1 = 0
            # about the integration variable of an integral over x (third audit of 30 Sep 2026, once
            # the integrand's conditions no longer reached the problem's variables). Every point is a
            # counterexample; one is checked and reported.
            w = _nowhere_true(claim, ctx) if _outside_domain(claim, ctx) else None
            if w is not None:
                ev["counterexample"] = w
                ev["reason"] = "no_value_of_the_domain_satisfies_the_claim"
                return "refuted", ev
            ev["reason"] = "definitional_claim_introduces_unconstrained_symbols"
            return "skipped", ev
    syms = sorted(syms, key=lambda s_: s_.name)
    if not syms:
        h = _holds(claim, {})
        return ("verified" if h is True else "refuted" if h is False else "unknown"), ev
    # route 0 (one unknown): the premises' solution SET, and the part of it where the claim fails.
    # Random samples miss thin sets: "x < 1.4" under x^2 < 2, "x != 3" under (x-3)/(x+2) <= 0 and
    # "-2 < x" under x^2 - 5x - 14 <= 0 all went unrefuted (audit of 25 Sep 2026). A witness is
    # still checked pointwise against every premise, so a wrong solveset cannot refute a step.
    if len(syms) == 1:
        w, proved, empty = _set_counterexample(claim, premises, syms[0], ctx)
        if w is not None:
            ev["counterexample"] = {str(k): str(v) for k, v in w.items()}
            ev["route"] = "premise_set"
            return "refuted", ev
        if proved:
            ev["route"] = "premise_set"
            return "verified", ev
        if empty and window:
            return "unknown", {**ev, "_window_without_instance": True}
    eqs = [p for p in premises if isinstance(p, Eq)]
    others = [p for p in base if not isinstance(p, Eq)]
    bounds = [p for p in window if not isinstance(p, Eq)]
    points: list[dict] = []
    # Only a finite solution set of polynomial equations is known to be complete; anything sampled
    # (a parametric solution, rejection sampling, `solve`'s principal roots of a transcendental
    # equation) can miss the one point where the claim fails. "verified" was said for all of them:
    # x >= 6 under x + y = 10, x >= y (x = y = 5), and the wrong "x in {pi/6, 5*pi/6}" of ayt-trig-010.
    # Nothing but the L6 cross-check reads "verified", and it overrules the critic on it.
    exhaustive = False
    # route 1: solve the equational premises
    if eqs:
        r = sb_run("mathverify.sandbox.ops:solve_system", eqs, syms, True, timeout=ctx.timeout)
        if r.ok and isinstance(r.value, list):
            sols = [s_ for s_ in r.value if isinstance(s_, dict)]
            ev["solutions"] = len(sols)
            if not sols:
                return "unknown", {"reason": "premises_inconsistent_or_unsolved", **ev}
            # complete only when proved so (`_proved_points`): `solve`'s list of a polynomial system is no
            # proof (round 5 of part d4b, 2 Oct 2026)
            proved = _proved_points(eqs, syms, ctx) if all(_is_polynomial(p, syms) for p in eqs) else None
            exhaustive = bool(proved)              # no real solution: nothing is proved by it
            if exhaustive:
                sols = proved
            for s_ in sols:
                # parametric solution: sample the remaining free symbols
                rem = set()
                for v in s_.values():
                    rem |= v.free_symbols
                rem |= set(syms) - set(s_.keys())
                if rem:
                    exhaustive = False
                    doms = {q: ctx.domain_for(q) for q in rem}
                    for pt in sample_points(doms, 24, ctx.seed) + _small_integer_grid(doms):
                        full = {k: sp.simplify(v.subs(pt)) for k, v in s_.items()}
                        full.update(pt)
                        points.append(full)
                else:
                    points.append(dict(s_))
        elif r.timed_out:
            ev["flags"] = ["cas_timeout"]
    # route 2: rejection sampling over the domain when nothing solvable
    if not points:
        doms = {q: ctx.domain_for(q) for q in syms}
        # the window's variable is drawn from inside the window: drawn from its whole domain, the
        # samples could all miss a narrow window that the premises do meet
        wdoms = _window_domains(doms, window, ctx)
        for pt in sample_points(wdoms, 60, ctx.seed) + _small_integer_grid(wdoms):
            if all(_holds(p, pt) is True for p in premises):
                points.append(pt)
        ev["rejection_sampled"] = len(points)
        if window and not points and any(all(_holds(p, pt) is True for p in base)
                                         for pt in sample_points(doms, 60, ctx.seed) + _small_integer_grid(doms)):
            return "unknown", {**ev, "_window_without_instance": True}
        if len(points) < 3 and premises:
            return "unknown", {"reason": "no_premise_satisfying_points", **ev}
    checked = inside = outside = backwards = at_convention = 0
    spans = _range_spans(claim)
    for pt in points:
        if not _in_domains(ctx, pt):
            # a solution where a value of the problem is a convention (n = -2 of n**2 = 4 next to
            # C(n, 2)) is neither an instance nor excluded: nothing is verified while one exists
            at_convention += _at_convention(pt, ctx)
            continue
        if any(_holds(p, pt) is False for p in others):
            continue
        if any(_holds(p, pt) is False for p in bounds):
            outside += 1
            continue
        inside += 1
        if _runs_backwards_at(spans, pt):
            # a range of the claim runs backwards here: its value is a convention, neither a
            # counterexample nor a check (part 11); another point may still refute it
            backwards += 1
            ev["reversed_range_points"] = backwards
            continue
        h = _holds(claim, pt)
        if h is False:
            # confirm robustly: every premise must hold definitively at this point
            if all(_holds(p, pt) is True for p in premises):
                ev["counterexample"] = {str(k): str(v) for k, v in pt.items()}
                return "refuted", ev
        if h is True:
            checked += 1
    if outside and not inside:
        return "unknown", {**ev, "_window_without_instance": True}
    ev["points_checked"] = checked
    if checked and checked == len([p for p in points if _in_domains(ctx, p)]):
        if exhaustive and not at_convention:
            return "verified", ev
        if at_convention:
            ev["convention_points"] = at_convention
        ev["reason"] = "no_counterexample_at_sampled_points"
    return "unknown", ev


def _window_domains(doms: dict, window: list, ctx: Ctx) -> dict:
    """`doms` with the window's variable restricted to the window; `doms` itself when the window
    cannot be read as a set."""
    out = dict(doms)
    for w in window:
        if len(w.free_symbols) != 1 or next(iter(w.free_symbols)) not in out:
            return dict(doms)
        (v,) = w.free_symbols
        r = sb_run("mathverify.sandbox.ops:solveset_in", w, v, S.Reals, timeout=ctx.timeout)
        if not r.ok or r.value.has(sp.ConditionSet):
            return dict(doms)
        out[v] = sp.Intersection(out[v], r.value)
    return out


def _is_polynomial(rel, syms) -> bool:
    try:
        return bool((rel.lhs - rel.rhs).is_polynomial(*syms))
    except Exception:  # noqa: BLE001 - a matrix, or anything else that is not an expression
        return False


# the task kinds whose own relation may stand in `params` instead of givens[0] (docs/SOLVER_FORMAT.md; trig_solve's
# certificate reads `equation` or givens[0] the same way, `certify.trig.verify`)
_TASK_RELATION_PARAMS = {"solve_equation": "equation", "solve_inequality": "inequality", "trig_solve": "equation"}


def _task_relations(ir, ctx: Ctx) -> list:
    """The task's own relation when it is written in `params` (solve_equation's and trig_solve's `equation`,
    solve_inequality's `inequality`): a premise as it is when written as givens[0], the other form SOLVER_FORMAT
    gives. Left out, a step derived from it had no premise and was refuted at a random point: x + 2 = x**2 for
    x**2 - x - 2 = 0, and the right solution {-1, 2} was INCORRECT (fourth audit PRE-RK-4); for 2 sin x = 1 in
    trig_solve's params every step was skipped, the wrong sin x = 1/3 too, which givens[0] refutes (round 2 of
    d4h, the same mechanism). Unreadable: no premise (as before)."""
    key = _TASK_RELATION_PARAMS.get(ir.task.kind)
    src = (ir.task.params or {}).get(key) if key else None
    if not isinstance(src, str) or not src.strip():
        return []
    try:
        rel = ctx.rel(src)
    except Exception:  # noqa: BLE001 - LeakageError cannot come from a parse; unread: no premise
        return []
    return [rel] if _is_relation(rel) and rel not in (sp.true, sp.false) else []


def _task_window(ir, ctx: Ctx) -> list:
    """The task's own interval for its variable (`params.interval` of `trig_solve` and `extremum`)
    as relations. It was not a premise: "x = pi/3" from tan x = sqrt(3) on [0, pi) was refuted with
    x = 4*pi/3 (K4, 28 Sep 2026: ayt-trig-004/-013/-017), and a solver's `assert` steps stating the
    interval never join the pool. An And is split so the premise-set route stays open."""
    from ..normalize.parse import parse_set_str
    p = ir.task.params or {}
    iv = p.get("interval")
    v = ctx.ns.get(p.get("var", "x"))
    if not isinstance(iv, str) or not iv.strip() or not isinstance(v, sp.Symbol):
        return _integration_window(ir, ctx)
    try:
        rel = parse_set_str(iv, ctx.ns).as_relational(v)
    except Exception:  # noqa: BLE001 - an interval we cannot read restricts nothing
        return []
    parts = list(rel.args) if isinstance(rel, And) else [rel]
    if any(r in (sp.true, sp.false) or not _is_relation(r) for r in parts):
        return []
    return parts


def _integration_window(ir, ctx: Ctx) -> list:
    """The interval of the problem's own integral for its variable: [a, b] of a definite_integral
    task, or of the one closed integral over a declared variable in an evaluate-like task when that
    variable occurs nowhere else. A solver's step about x there means x in [a, b]: sqrt(x**2) = x
    in the integral over [0, 2] was refuted with x = -1 (known limit K of the V14 audit), and
    log(x**2) = 2*log(x) on [1, e] too, once the integrand's conditions no longer reached the
    problem's variables (third audit of 30 Sep 2026). Like the task interval, it binds nothing."""
    from ..normalize.parse import parse_as_written
    p = ir.task.params or {}
    try:
        if ir.task.kind == "definite_integral":
            v = ctx.ns.get(p.get("var", "x"))
            a, b = ctx.expr(str(p["a"])), ctx.expr(str(p["b"]))
        else:
            src = next((p[k] for k in ("expr", "f") if isinstance(p.get(k), str)), None)
            w = parse_as_written(src, ctx.ns) if src else None
            if w is None or len(w) != 1:
                return []
            ints = [n for n in sp.preorder_traversal(w[0]) if isinstance(n, sp.Integral)]
            if len(ints) != 1 or len(ints[0].limits) != 1 or len(ints[0].limits[0]) != 3:
                return []
            v, a, b = ints[0].limits[0]
            outside = w[0].xreplace({ints[0]: sp.Dummy()})
            if ctx.ns.get(getattr(v, "name", "")) != v or v in outside.free_symbols:
                return []
        if not (isinstance(v, sp.Symbol) and a.is_real and b.is_real and a.is_number and b.is_number):
            return []
        lo, hi = (a, b) if bool(a <= b) else (b, a)
    except Exception:  # noqa: BLE001 - a window we cannot read restricts nothing
        return []
    return [sp.Ge(v, lo, evaluate=False), sp.Le(v, hi, evaluate=False)]


def _task_objects(ir, ctx: Ctx) -> list:
    """Equations of the problem's own objects that are NOT the answer, written in the answer's
    coordinates: the curve of a tangent line, the given line of a parallel/perpendicular line, the
    circle of a tangent to a circle. A solver that writes the curve as `y = x**2` and the tangent as
    `y = 2*x - 1` names two objects with one `y`; the tangent was refuted against the curve with
    (x, x**2) (K4, 28 Sep 2026: ayt-tur-003/-010/-013)."""
    p = ir.task.params or {}
    kind = ir.task.kind
    try:
        if kind == "tangent_line" and isinstance(p.get("f"), str):
            x, y = ctx.ns.get(p.get("var", "x")), ctx.ns.get(p.get("dep", "y"))
            if isinstance(x, sp.Symbol) and isinstance(y, sp.Symbol):
                return [Eq(y, ctx.expr(p["f"]))]
        if kind == "equation_of":
            obj = p.get("object")
            if obj in ("line_point_parallel", "line_point_perpendicular") and isinstance(p.get("line"), str):
                return [ctx.rel(p["line"])]
            x, y = ctx.ns.get("x"), ctx.ns.get("y")
            if obj == "tangent_to_circle_at_point" and isinstance(x, sp.Symbol) and isinstance(y, sp.Symbol):
                (cx, cy), (px, py) = ([ctx.expr(str(c)) for c in p[k]] for k in ("center", "point"))
                return [Eq((x - cx) ** 2 + (y - cy) ** 2, (px - cx) ** 2 + (py - cy) ** 2)]
    except Exception:  # noqa: BLE001 - parameters we cannot read name no object
        return []
    return []


def _ratio(a, b):
    return sp.simplify(sp.cancel(a / b))


def _states_task_object(claim, objects: list, ctx: Ctx) -> bool:
    """True when the claim is the equation of one of `objects` up to a nonzero constant factor.
    Anything less certain is False, and the claim is checked as before."""
    if not isinstance(claim, Eq):
        return False
    a = claim.lhs - claim.rhs
    for obj in objects:
        if not isinstance(obj, Eq) or obj.free_symbols != claim.free_symbols or not claim.free_symbols:
            continue
        b = obj.lhs - obj.rhs
        if a == 0 or b == 0:
            continue
        r = sb_run("mathverify.steps.deterministic:_ratio", a, b, timeout=ctx.timeout)
        if r.ok and isinstance(r.value, sp.Expr) and not r.value.free_symbols and r.value.is_finite \
                and r.value.is_zero is False:
            return True
    return False


def _with_undeclared(text: str, ns: dict[str, Any], names) -> dict[str, Any]:
    """`ns` with the claim's undeclared names: a symbol, or a function where the text calls it (the sequence a of
    a recurrence: read as a symbol, a(3) = 3 + 1/factorial(-1) was no reading at all and its 1/zoo was verified,
    review of d4f, YO-6)."""
    import re
    out = dict(ns)
    for n in names:
        if n not in ns:
            called = re.search(rf"(?<![\w.]){re.escape(n)}\s*\(", text)
            out[n] = sp.Function(n) if called else sp.Symbol(n)
    return out


def _undefined_as_written(text: str, ns: dict[str, Any], unread: bool = False) -> bool:
    """Is the claim, read AS WRITTEN, undefined whatever its free symbols are (a closed condition
    that fails, e.g. a term of a finite sum at one of its indices)? The value parse folds j/j to 1,
    and the compute step `Sum(j/j, (j, -1, 1)) = 3` was verified (V14 tests, 30 Sep 2026). Undeclared
    names are read as `_with_bound_dummies` reads them. A text the as-written reading does not take is `unread`:
    a step the value reading verified is not proved defined then (review of d4f, YO-1)."""
    from ..certify.domain import closed_condition_undecided, definedness_conditions
    from ..normalize.parse import _check_safe, _strip_invisible, parse_set_as_written, preclean
    try:
        names = _check_safe(preclean(_strip_invisible(text)), ns)
    except Exception:  # noqa: BLE001 - LaTeX, or not well-formed: the parse decides
        names = []
    if names:
        ns = _with_undeclared(text, ns, names)
    try:
        # a membership (x in {0, 4}) or a compound step (x = 1 or x = 2) part by part
        w = parse_set_as_written(text, ns)
        if w is None:
            return unread
        conds = definedness_conditions(w, None)
        # a binder whose body is not proved to exist (DEFINEDNESS_UNDECIDED) is not verified either
        return any(c is sp.false for c in conds) or closed_condition_undecided(conds)
    except Exception:  # noqa: BLE001 - no reading as written: as above
        return unread


def _written_relations(text: str, ns: dict[str, Any]) -> list:
    """The conditions on the claim's free symbols under which it, read AS WRITTEN, has a value: relations
    (x != 0 for x/x, x >= 0 for sqrt(x)), not the range or convention memberships. A point where one is
    false is no instance of the claim (principle 12): it neither refutes nor verifies it."""
    from ..certify.domain import definedness_conditions
    from ..normalize.parse import _check_safe, _strip_invisible, parse_as_written, preclean
    try:
        names = _check_safe(preclean(_strip_invisible(text)), ns)
    except Exception:  # noqa: BLE001 - LaTeX, or not well-formed: the parse decides
        names = []
    if names:
        ns = _with_undeclared(text, ns, names)
    try:
        w = parse_as_written(text, ns)
        conds = definedness_conditions(w, None) if w is not None else []
    except Exception:  # noqa: BLE001 - no reading as written: nothing is added
        return []
    return [c for c in conds if isinstance(c, (sp.core.relational.Relational, And, Or))
            and getattr(c, "free_symbols", None)]


def _convention_as_written(text: str, ns: dict[str, Any]) -> bool:
    """Does the claim, read AS WRITTEN, hold a closed operation whose value is a convention with another
    value (`certify.domain.is_value_convention`: Mod(7, -5), (-8)**(1/3)) left standing? The value parse
    computed it SymPy's way before any check saw it. 0**0 and C(2, 5) are 1 and 0 or undefined: a claim
    refuted with SymPy's value is not true under the other reading either. A text the as-written reading does
    not take counts too: its value is not proved the curriculum's (review of d4f, YO-1). Σ_{k=c}^{c+2} k with
    c = 1/2 written in nested roots has a closed bound not proved an integer (`certify.domain.INTEGER_BOUND`), and
    the step "= 3" was refuted with SymPy's 9/2."""
    from ..certify.domain import definedness_conditions, is_value_convention
    from ..normalize.parse import _check_safe, _strip_invisible, parse_set_as_written, preclean
    try:
        names = _check_safe(preclean(_strip_invisible(text)), ns)
    except Exception:  # noqa: BLE001 - LaTeX, or not well-formed: the parse decides
        names = []
    if names:
        ns = _with_undeclared(text, ns, names)
    try:
        w = parse_set_as_written(text, ns)
        if w is None:
            return True
        return any(is_value_convention(c) and not c.free_symbols for c in definedness_conditions(w, None))
    except Exception:  # noqa: BLE001 - no reading as written: as above
        return True


_MAX_DEFINED_POINTS = 200            # points of the premises' sets a claim's definedness is checked at one by one


def _finite_values(s) -> list | None:
    """The elements of `s` when it is a finite set (a Range included) of at most _MAX_DEFINED_POINTS exact
    real numbers; None otherwise."""
    if isinstance(s, sp.Range) and s.is_finite_set is True and s.size <= _MAX_DEFINED_POINTS:
        s = sp.FiniteSet(*s)
    if not isinstance(s, sp.FiniteSet) or len(s) > _MAX_DEFINED_POINTS:
        return None
    vals = list(s)
    if any(not isinstance(c, sp.Expr) or c.free_symbols or c.is_real is not True for c in vals):
        return None
    return vals


def _held_at(c, point: dict, ctx: Ctx) -> bool | None:
    from ..certify.domain import decide_membership
    if c is sp.true or c is sp.false:
        return bool(c)
    if isinstance(c, sp.Contains):
        try:
            return decide_membership(c.args[0].xreplace(point), c.args[1])
        except Exception:  # noqa: BLE001
            return None
    return _decide(c, point, ctx)


def _holds_on(c, v, region, ctx: Ctx) -> bool:
    """Is the condition `c` on the one symbol `v` proved to hold on all of `region` (its negation solved
    there is empty)? A range's condition is read as `span >= 0`; a value convention is left to its own
    rules (`_range_spans`); a membership holds when the region lies in the set."""
    from ..certify.domain import is_convention, FORWARD_SPANS
    if isinstance(c, sp.Contains):
        if c.args[1] == FORWARD_SPANS:
            c = sp.Ge(c.args[0], 0)
        elif is_convention(c):
            return True
        else:
            try:
                return c.args[0] == v and region.is_subset(c.args[1]) is True
            except Exception:  # noqa: BLE001
                return False
    if not isinstance(c, sp.core.relational.Relational):
        return False
    _tick()
    r = sb_run("mathverify.sandbox.ops:solveset_in", c.negated, v, region, timeout=ctx.timeout)
    if not r.ok or not isinstance(r.value, sp.Set) or r.value.has(sp.ConditionSet):
        return False
    try:
        return r.value.is_empty is True
    except Exception:  # noqa: BLE001
        return False


def _split_nonnegative_sums(premises: list, ctx: Ctx) -> list:
    """The premises with an equation `a1 + a2 + ... = 0` whose terms are each nonnegative for real symbols
    (x**2 + y**2 = 0, Abs(x) + (y - 1)**2 = 0) read as `a1 = 0, a2 = 0, ...`: its real solutions. SymPy
    solves it over the complex numbers (x = ±I*y), and "x/x = 1" was verified under x**2 + y**2 = 0, whose
    one real point has x = 0 (d4g review Q4-Q10)."""
    out: list = []
    for p in _premise_parts(premises):
        if isinstance(p, Eq):
            d = p.lhs - p.rhs
            syms_ = d.free_symbols
            try:
                real = all(ctx.domain_for(q).is_subset(S.Reals) is True for q in syms_ if ctx.ns.get(q.name) == q) \
                    and all(ctx.ns.get(q.name) == q for q in syms_)
            except Exception:  # noqa: BLE001
                real = False
            if real and isinstance(d, sp.Add) and len(d.args) > 1:
                reps = {q: sp.Dummy(q.name, real=True) for q in syms_}
                if all(a.xreplace(reps).is_nonnegative is True for a in d.args):
                    out.extend(Eq(a, 0) for a in d.args)
                    continue
        out.append(p)
    return out


def _proved_on_system(c, multi: list, sets: dict, ctx: Ctx) -> bool:
    """Is the condition `c` proved where the premises `multi` (each on several symbols) hold: on its one
    symbol's set alone, or at each explicit real solution of their equations (y = x**2: y >= 0 becomes
    x**2 >= 0, proved on x's set)? A non-real solution (x = I*y) leaves a condition
    the reals do not prove (its negation solved over the reals is not empty): not proved."""
    cs = c.free_symbols
    if len(cs) == 1:
        (u,) = cs
        if _holds_on(c, u, sets.get(u, ctx.domain_for(u)), ctx):
            return True
    eqs = [p for p in multi if isinstance(p, Eq) and p.free_symbols & cs]
    if not eqs:
        return False
    # solved for the condition's own symbols, in terms of the others
    order = sorted(set().union(*(p.free_symbols for p in eqs)) & cs, key=lambda q: q.name)
    _tick()
    # only a solution PROVED complete proves anything at its points (`solve`'s list is no proof: round 5
    # of part d4b, 2 Oct 2026): each symbol defined explicitly by an equation (y = x**2), or the points of
    # a system in these symbols alone whose completeness is proved (`_proved_points`)
    defs: dict = {}
    for p in eqs:
        for a, b in ((p.lhs, p.rhs), (p.rhs, p.lhs)):
            if a in order and a not in defs and not (b.free_symbols & set(order)):
                defs[a] = b
                break
    if set(defs) == set(order):
        sols = [defs]
    elif set().union(*(p.free_symbols for p in eqs)) <= set(order):
        sols = _proved_points(eqs, order, ctx)
        if not sols:
            return False
    else:
        return False
    for sol in sols:
        if not isinstance(sol, dict) or any(not isinstance(v, sp.Expr) for v in sol.values()):
            return False
        try:
            c2 = c.xreplace(sol)
        except Exception:  # noqa: BLE001 - an order relation between non-real values
            return False
        rem = c2.free_symbols if isinstance(c2, sp.Basic) else set()
        if not rem:
            if _held_at(c2, {}, ctx) is not True:
                return False
            continue
        if len(rem) != 1:
            return False
        (u,) = rem
        if not _holds_on(c2, u, sets.get(u, ctx.domain_for(u)), ctx):
            return False
    return True


def _undefined_at_premises(text: str, ns: dict[str, Any], premises: list, ctx: Ctx) -> bool:
    """Is the claim, read AS WRITTEN, not proved defined at a point the premises allow? `_undefined_as_written`
    looks at closed conditions only, and the value parse folds the rest away: the eq step "x/x = 1" was
    verified under x = 0, "sqrt(x - 3)**2 = x - 3" under x = 2, "x + gcd(x, 2) - gcd(2, x) = pi + E" under
    x = pi + E and "sqrt(x)**2 = x" under x**2 = 4 (V16, 30 Sep 2026).

    Each condition (`certify.domain.definedness_conditions`) is read on the set the premises leave its
    symbols: the solution of the premises on that symbol alone (a pinned value x = 0 among them),
    each symbol on its own (x**2 = 4 and y**2 = 1), and the points of a system the premises solve together
    (`_finite_instances`). On a finite set (a Range of integers too, up to _MAX_DEFINED_POINTS points) it
    must hold at every point; on a larger one, for a condition left on one symbol, it is proved by solving
    its negation there. Not proved: True. Before, only one symbol, or every symbol pinned, and at most 12
    points were read: "x/x = 1" for an integer -1 <= x <= 10, "sqrt(x)**2 + sqrt(y)**2 = x + y" under
    x**2 = 4, y**2 = 1 and "x/x + sqrt(y) - sqrt(y) = 1" under x = 0 with y free were verified (fourth
    audit, D4-ADIM-D, TAN-11). A symbol no premise narrows is not read: the claim is an identity where it
    is defined."""
    from itertools import product
    from ..certify.domain import definedness_conditions
    from ..normalize.parse import _check_safe, _strip_invisible, parse_as_written, preclean
    try:
        names = _check_safe(preclean(_strip_invisible(text)), ns)
    except Exception:  # noqa: BLE001 - LaTeX, or not well-formed: the parse decides
        names = []
    if names:
        ns = _with_undeclared(text, ns, names)
    try:
        w = parse_as_written(text, ns)
        conds = [c for c in definedness_conditions(w, None) if getattr(c, "free_symbols", None)] if w is not None else []
    except Exception:  # noqa: BLE001 - no reading as written: nothing is added
        return False
    if not conds:
        return False
    premises = _split_nonnegative_sums(premises, ctx)
    syms = set().union(*(c.free_symbols for c in conds))
    sets: dict = {}
    for v in syms:
        if ctx.ns.get(v.name) != v:
            continue
        own = [p for p in _premise_parts(premises)
               if isinstance(p, sp.core.relational.Relational) and p.free_symbols == {v}]
        if not own:
            continue
        region = ctx.domain_for(v)
        for p in own:
            _tick()
            r = sb_run("mathverify.sandbox.ops:solveset_in", p, v, S.Reals, timeout=ctx.timeout)
            if not r.ok or not isinstance(r.value, sp.Set) or r.value.has(sp.ConditionSet):
                region = None                # a premise not solved: the symbol is read as not narrowed
                break
            region = sp.Intersection(region, r.value)
        try:
            whole = region is not None and ctx.domain_for(v).is_subset(region) is True
        except Exception:  # noqa: BLE001
            whole = False
        if region is not None and not whole:
            # a premise that leaves the whole domain (x*log(x) = log(x)/(1/x), an identity) narrows nothing
            sets[v] = region
    # a system the premises solve together (x + y = 5, x - y = 1): its points
    linked = {v for v in syms if ctx.ns.get(v.name) == v and v not in sets}
    if linked:
        _tick()
        inst = _finite_instances(linked, premises, ctx)
        for pt in ((inst[0] + inst[1]) if inst is not None else []):
            for c in conds:
                if c.free_symbols <= set(pt) and _held_at(c, pt, ctx) is not True:
                    return True
        if inst is None:
            # symbols a premise on several symbols links (y = x**2, x**2 + y**2 = 1) whose real solution set
            # was not read: a condition on them must be proved on that set (`_proved_on_system`)
            multi = [p for p in _premise_parts(premises)
                     if isinstance(p, sp.core.relational.Relational) and len(p.free_symbols) > 1]
            unresolved = {v for v in linked if any(v in p.free_symbols for p in multi)}
            for c in conds:
                if c.free_symbols & unresolved and not _proved_on_system(c, multi, sets, ctx):
                    return True
    for c in conds:
        narrowed = sorted((v for v in c.free_symbols if v in sets), key=lambda q: q.name)
        if not narrowed:
            continue
        values = {v: _finite_values(sets[v]) for v in narrowed}
        fin = [v for v in narrowed if values[v] is not None]
        count = 1
        for v in fin:
            count *= len(values[v])
        if count > _MAX_DEFINED_POINTS:
            fin = []
        for combo in product(*(values[v] for v in fin)):
            _tick()
            assign = dict(zip(fin, combo))
            c2 = c.xreplace(assign) if assign else c
            rem = c2.free_symbols if isinstance(c2, sp.Basic) else set()
            if not rem:
                if _held_at(c2, {}, ctx) is not True:
                    return True
                continue
            if rem - set(narrowed):
                continue                     # a symbol no premise narrows is left: not read
            if len(rem) != 1:
                return True                  # several symbols on infinite sets: not proved
            (u,) = rem
            if not _holds_on(c2, u, sets[u], ctx):
                return True
    return False


def _with_bound_dummies(text: str, ns: dict[str, Any]):
    """`text` read with its undeclared names as symbols, when every one of them is a BOUND variable
    (the index of a Sum or Product, the variable of an Integral or a Limit) and none is left free.
    `Sum(k, (k, 1, 4)) = 11` was skipped as naming an undeclared `k`, so the wrong step was never
    checked, while `1 + 2 + 3 + 4 = 11` was refuted (audit of 25 Sep 2026). A free undeclared name
    is still the solver's own symbol and the step is skipped (principle 5)."""
    from ..normalize.parse import _check_safe, _strip_invisible, preclean
    try:
        names = _check_safe(preclean(_strip_invisible(text)), ns)
    except Exception:  # noqa: BLE001 - not well-formed: reported by the caller
        return None
    if not names or any(n in ns for n in names):
        return None
    try:
        rel = _parse_claim(text, dict(ns, **{n: sp.Symbol(n) for n in names}))
    except Exception:  # noqa: BLE001
        return None
    free = {getattr(f, "name", None) for f in getattr(rel, "free_symbols", set())}
    return None if free & set(names) else rel


def _with_sequence_terms(ir, ctx: Ctx, text: str, ns: dict[str, Any]):
    """`text` with every call of the task's sequence at an integer index replaced by the exact
    term, or None when that does not make it a checkable relation (a symbolic index, a term the
    recurrence does not determine, another undeclared name)."""
    from sympy.core.function import AppliedUndef
    from ..certify.series import sequence_term_values
    p = ir.task.params or {}
    if ir.task.kind not in ("recurrence_term", "closed_form") or not isinstance(p.get("recurrence"), str):
        return None
    fname = p.get("name", "a")
    if not isinstance(fname, str) or fname in ns:
        return None
    try:
        rel = _parse_claim(text, dict(ns, **{fname: sp.Function(fname)}))
    except Exception:  # noqa: BLE001 - another undeclared name, or not well-formed
        return None
    calls = [c for c in rel.atoms(AppliedUndef) if c.func.__name__ == fname]
    if not calls or any(len(c.args) != 1 or not isinstance(c.args[0], sp.Integer) for c in calls):
        return None
    _, terms = sequence_term_values(ir, ctx, {int(c.args[0]) for c in calls})
    if any(int(c.args[0]) not in terms for c in calls):
        return None
    out = rel.xreplace({c: terms[int(c.args[0])] for c in calls})
    return None if out.atoms(AppliedUndef) else out


def _compute_status(claim, text: str, pool: list, ctx: Ctx, conds=()) -> tuple[str, dict]:
    """A `compute` claim checked as an identity (`_check_compute`), then where the premises `pool` put its
    symbols when the identity failed: its counterexample is no instance of the problem when the premises
    pin every symbol of the claim (principle 5), or exclude it (`_on_premises`). An integral with a
    parameter has no value until the premises pin it (DECISIONS §80); a claim verified only with Karr's
    value of its own range may be verified where the premises leave no backward point. `conds`: the claim's
    written conditions (D4-ADIM-J; a pinned point where one fails is sorted out by `check_steps`)."""
    status, ev = _check_compute(claim, ctx)
    if status == "verified":
        status, ev = _verified_where_conventions(claim, ctx, status, ev)
    if status == "refuted" or (status == "unknown" and ev.get("reason") in ("parametric_form", _KARR_ONLY)):
        pins = _pins(claim, pool)
        if not pins:
            # the premises confine the symbols to finitely many values, or narrow them; a failure there
            # leaves the identity check as it was
            try:
                status, ev = _on_premises(claim, text, pool, ctx, status, ev, conds)
            except Exception as e:  # noqa: BLE001
                ev = {**ev, "premise_recheck_failed": f"{type(e).__name__}: {str(e)[:120]}"}
        if pins:
            # the sides separately: Eq would evaluate itself on substitution
            pinned = Eq(claim.lhs.xreplace(pins), claim.rhs.xreplace(pins), evaluate=False)
            try:
                # a pinned limit of a Sum or Product must pass the parser's range checks (reversed, or not
                # an integer apart), or the claim is not read there
                _refuse_reversed_ranges(pinned, text)
            except ParseError as e:
                status, pev = "unknown", {"reason": f"pinned_claim_not_read: {str(e)[:160]}"}
            else:
                status, pev = _check_compute(pinned, ctx)
            ev = {**pev, "pinned_by_premises": {str(k): str(v) for k, v in pins.items()}, "identity_refuted": ev}
    return status, ev


def _counterexample_where_undefined(claim, ev: dict, conds, ctx: Ctx) -> bool:
    """Is the point a refutation was found at (`_refutation_point`) one where the claim, read as written,
    has no value (`_undefined_at`)? Then it is no counterexample (principle 12, D4-ADIM-J)."""
    if not conds:
        return False
    pt = _refutation_point(ev, getattr(claim, "free_symbols", set()))
    return pt is not None and _undefined_at(conds, pt, ctx)


def check_steps(ir, solution, ctx: Ctx):
    with Timer() as t:
        per_step: list[dict[str, Any]] = []
        parsed: dict[str, Any] = {}
        parsed_cases: dict[str, frozenset] = {}
        givens, restrictions = [], []
        try:
            givens, restrictions = ctx.givens(), ctx.var_constraints()
        except Exception:
            pass
        givens = givens + [r for r in _task_relations(ir, ctx) if r not in givens]
        window = _task_window(ir, ctx)
        objects = _task_objects(ir, ctx)
        first_bad = None
        started = time.monotonic()
        n_ref = n_ver = n_unk = n_skip = n_malformed = 0
        case_claims: dict[str, Any] = {}          # id -> relation assumed in a case branch
        choices: dict[Any, Any] = {}              # symbol -> the solver's latest choice of its value
        verified: set[str] = set()                # ids of the `eq` claims the premises proved
        from_map: dict[str, list[str]] = {s.id: list(s.from_ids) for s in solution.steps}

        def case_closure(sid: str) -> list:
            """Case assumptions reachable through the `from` links of step `sid`."""
            seen, stack, out = set(), list(from_map.get(sid, [])), []
            while stack:
                k = stack.pop()
                if k in seen:
                    continue
                seen.add(k)
                if k in case_claims:
                    out.append(case_claims[k])
                stack.extend(from_map.get(k, []))
            return out

        for idx, st in enumerate(solution.steps, start=1):
            entry: dict[str, Any] = {"id": st.id, "kind": st.kind, "index": idx}
            if st.kind == "case" and st.claim.strip():
                try:
                    c = _parse_claim(st.claim, ctx.ns)
                    if _is_relation(c):
                        case_claims[st.id] = c
                except Exception:  # noqa: BLE001
                    pass
            if st.kind not in ("eq", "compute") or not st.claim.strip():
                entry["status"] = "skipped"
                entry["reason"] = "kind_not_checkable" if st.kind not in ("eq", "compute") else "no_claim"
                n_skip += 1
                per_step.append(entry)
                continue
            step_ns = _step_namespace(ctx.ns) if st.kind == "compute" else ctx.ns
            try:
                claim = _parse_claim(st.claim, step_ns)
            except UndeclaredSymbolError as e:
                # A term of the task's own sequence at an integer index (`a(3) = 6`) is not the
                # solver's symbol: it is read with the term's exact value (audit of 25 Sep 2026).
                claim, read_with = _with_sequence_terms(ir, ctx, st.claim, step_ns), "sequence_terms"
                if claim is None:
                    claim, read_with = _with_bound_dummies(st.claim, step_ns), "bound_variables"
                if claim is None:
                    # The solver named something of its own (`u = sqrt(x+4)`). Well-formed
                    # mathematics we simply cannot check: skipped, no penalty (§3 rule 3).
                    entry["status"] = "skipped"
                    entry["reason"] = f"undeclared_symbol: {str(e)[:120]}"
                    n_skip += 1
                    per_step.append(entry)
                    continue
                entry["read_with"] = read_with
            except Exception as e:  # noqa: BLE001
                # Not well-formed at all. This is NOT "an unproven step", it is a solution that
                # does not meet the structured contract, and silently skipping it let an
                # attacker cancel a refutation by corrupting the claim: measured, appending `}`
                # to a refuted step turned INCORRECT into CORRECT. Abstain instead of accepting.
                entry["status"] = "skipped"
                entry["reason"] = f"malformed_claim: {type(e).__name__}: {str(e)[:120]}"
                n_malformed += 1
                n_skip += 1
                per_step.append(entry)
                continue
            if not _is_relation(claim):
                # SOLVER_FORMAT: every `eq`/`compute` claim IS a relation. Something that
                # parses into an expression is as much a contract violation as something that
                # does not parse, and skipping it silently is the same hole: measured, a
                # refuted step wrapped in \boxed{} came back as a non-relation and its
                # refutation disappeared.
                entry["status"] = "skipped"
                entry["reason"] = "claim_is_not_a_relation"
                n_malformed += 1
                n_skip += 1
                per_step.append(entry)
                continue
            my_cases = case_closure(st.id)
            my_case_ids = frozenset(k for k in case_claims if case_claims[k] in my_cases)
            if st.kind == "eq" and objects and _states_task_object(claim, objects, ctx):
                # the problem's own curve (or given line, circle), not a constraint on the
                # answer's coordinates: not checked, and it never becomes a premise
                entry["status"] = "skipped"
                entry["reason"] = "states_a_task_object"
                n_skip += 1
                per_step.append(entry)
                continue
            left = _SOLUTION_BUDGET - (time.monotonic() - started)
            if left <= 0:
                # the solution's budget is spent: this step is not checked (and joins no premise pool)
                entry["status"] = "unknown"
                entry["reason"] = "solution_time_budget_exceeded"
                n_unk += 1
                per_step.append(entry)
                continue
            chosen = False
            conds: list = []
            token = _deadline.set(time.monotonic() + min(_STEP_BUDGET, left))
            try:
                try:
                    conds = _written_relations(st.claim, step_ns)
                    if st.kind == "compute":
                        # the premises: the givens, the variables' constraints, the `eq` claims proved in
                        # this branch and the task's own interval (it binds nothing but bounds the region:
                        # outside it a point is no instance, D4-ADIM-E)
                        # a Sum/Product worth 0 (1) under every reading is that value (Product(1, (j, 1, m))
                        # kept the comparison from evaluating a wrong identity, d4g review B4)
                        claim = _neutralized(claim)
                        # and the case assumptions the step depends on (a case bounds the region like the
                        # interval: under case x < 0 "Abs(x) = -x" was refuted at x > 0, d4g review Z1-Z4)
                        pool = (list(givens) + list(restrictions) + list(window)
                                + [parsed[k] for k in verified
                                   if k in parsed and parsed_cases.get(k, frozenset()) <= my_case_ids]
                                + list(my_cases))
                        status, ev = _compute_status(claim, st.claim, pool, ctx, conds)
                        if status == "refuted" and window and ev.get("no_premise_instance"):
                            # the task's interval leaves the premises no instance (a case x < 0 on [0, 2]):
                            # like the eq steps' window, it is dropped and the step checked without it
                            pool = [p for p in pool if p not in window]
                            status, ev = _compute_status(claim, st.claim, pool, ctx, conds)
                            ev = {**ev, "window_dropped": "no_premise_instance_inside_the_task_interval"}
                        range_premises = pool

                        def recheck(c, pool=pool, conds=conds, text=st.claim):
                            return _compute_status(c, text, pool, ctx, conds)[0]
                    else:
                        # premises: givens + unconditional earlier claims + claims from the same
                        # case branch(es) + the case assumptions themselves
                        premises = list(givens) + [parsed[k] for k in parsed
                                                   if k != st.id and parsed_cases.get(k, frozenset()) <= my_case_ids]
                        premises += my_cases
                        # a point assignment ("x = 0") is checked with the solver's latest choices of the
                        # OTHER symbols: "y = -1" after the choice "x = 0" is a fact about that point
                        point = _point_symbol(claim, ctx)
                        extra = [c for s_, c in choices.items() if s_ != point] if point is not None else []
                        status, ev = _check_eq(claim, premises + extra, ctx, restrictions, window)
                        range_premises = premises + extra + list(restrictions)

                        def recheck(c, prem=premises + extra):
                            return _check_eq(c, prem, ctx, restrictions, window)[0]
                        if point is not None and status == "refuted":
                            w = _free_choice(claim, point, premises + extra + list(restrictions), ctx)
                            if w is not None:
                                status, chosen = "skipped", True
                                ev = {"reason": "choice_of_a_free_symbol", "witness": {str(k): str(v) for k, v in w.items()}}
                        elif point is not None and extra and status != "skipped":
                            # decided only thanks to a choice: a fact about the chosen point, not a
                            # premise for the general relations that follow
                            chosen = _check_eq(claim, premises, ctx, restrictions, window)[0] == "refuted"
                except Exception as e:  # noqa: BLE001
                    status, ev = "unknown", {"reason": f"checker_exception: {type(e).__name__}: {str(e)[:120]}"}
                    range_premises, recheck = [], None
                if status == "refuted" and _convention_as_written(st.claim, step_ns):
                    # a closed value of the claim is a convention (Mod(7, -5): -3 floored, 2 Euclidean);
                    # SymPy's reading refutes nothing (part d4a, DECISIONS §80)
                    status, ev = "unknown", {"reason": "claim_value_is_a_convention", "withdrawn": ev}
                if status == "refuted" and _refuted_where_backwards(claim, ev, ctx, range_premises, recheck):
                    # the refutation rests on the reading of a range of the claim that runs backwards:
                    # Karr's value or the empty sum, a convention (part 11, D4-ADIM-B, DECISIONS §80)
                    status, ev = "unknown", {"reason": "counterexample_where_a_range_of_the_claim_runs_backwards",
                                             "withdrawn": ev}
                if status == "refuted" and _counterexample_where_undefined(claim, ev, conds, ctx):
                    # the claim, read as written, has no value at the counterexample (principle 12): sqrt(x**3)
                    # = x*sqrt(x) at x = -2, where neither side is real (D4-ADIM-J)
                    status, ev = "unknown", {"reason": "counterexample_where_the_claim_is_undefined", "withdrawn": ev}
                why = None
                if status != "refuted":
                    if _undefined_as_written(st.claim, step_ns, unread=status == "verified"):
                        why = "claim_undefined_as_written"
                    else:
                        try:
                            undefined = _undefined_at_premises(st.claim, step_ns, list(givens) + [
                                parsed[k] for k in parsed if parsed_cases.get(k, frozenset()) <= my_case_ids]
                                + my_cases, ctx)
                        except Exception:  # noqa: BLE001 - not proved defined
                            undefined = True
                        if undefined:
                            why = "claim_undefined_at_the_premises_point"
            except _OutOfTime:
                status, ev, why, chosen = "unknown", {"reason": "step_time_budget_exceeded"}, None, False
            finally:
                _deadline.reset(token)
            if why is not None:
                # the value SymPy checked is not the value of what was written: neither verified
                # nor a premise (principle 12). A refutation stands: the checkers refute only a
                # value they computed, and an undefined claim is no true step either.
                entry["status"] = "unknown"
                entry["reason"] = why
                n_unk += 1
                per_step.append(entry)
                continue
            entry["status"] = status
            entry["evidence"] = ev
            per_step.append(entry)
            if chosen:
                # neither refuted nor a premise of the pool; it stands for its symbol until the next choice
                n_skip += status == "skipped"
                n_ver += status == "verified"
                n_unk += status == "unknown"
                if isinstance(claim, Eq):
                    choices[point] = claim
                continue
            if status == "refuted":
                n_ref += 1
                if first_bad is None:
                    first_bad = idx
                # do not add a refuted claim to the premise pool
                continue
            if status == "verified":
                n_ver += 1
                if st.kind == "eq":
                    verified.add(st.id)
            elif status == "unknown":
                n_unk += 1
            elif status == "skipped":
                n_skip += 1
            # only `eq` claims join the premise pool: compute claims (Derivative/Integral
            # equations) are statements about operations, not constraints on the unknowns
            if st.kind == "eq" and isinstance(claim, (sp.core.relational.Relational, And, Or)):
                parsed[st.id] = claim
                parsed_cases[st.id] = my_case_ids
        ev_all = {"steps": per_step, "n_refuted": n_ref, "n_verified": n_ver, "n_unknown": n_unk,
                  "n_skipped": n_skip, "n_malformed": n_malformed, "n_total": len(solution.steps)}
    if n_ref:
        return result(LAYER, "fail", 0.97, True, ev_all, t.ms, primary=False, first_bad_step=first_bad,
                      flags=["step_refuted"])
    if n_malformed:
        return unknown(LAYER, "malformed_step_claim", t.ms, ev_all, flags=["malformed_step_claim"])
    return unknown(LAYER, "no_step_refuted", t.ms, ev_all)
