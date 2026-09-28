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
from typing import Any

import sympy as sp
from sympy import S, Eq, Or, And

from ..certify.base import Ctx, Timer, result, unknown
from ..certify.domain import relation_holds_at, in_domain
from ..equiv import answers_equivalent
from ..equiv.random_point import sample_points
from ..normalize.parse import parse_relation, UndeclaredSymbolError
from ..sandbox import run as sb_run

LAYER = "steps.refute"

_IN_SET = re.compile(r"^\s*([A-Za-z_]\w*)\s+in\s+(\{.*\})\s*$")


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
        return relation_holds_at(type(rel)(lhs, rhs, evaluate=False), d, 0)
    try:
        sub = rel.subs(point, simultaneous=True)
    except Exception:
        return None
    if sub is sp.true:
        return True
    if sub is sp.false:
        return False
    return None


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

    out["Limit"] = out["limit"] = _limit
    out["Integral"] = out["integrate"] = lambda *a: sp.Integral(*a)
    out["Derivative"] = out["diff"] = lambda *a: sp.Derivative(*a)
    out["at"] = _at
    out["Subs"] = sp.Subs
    return out


def _derivative_points(expr) -> list:
    """Subs(Derivative(f, (x, n)), x, a) atoms: a derivative evaluated at a point."""
    return [s_ for s_ in expr.atoms(sp.Subs)
            if isinstance(s_.expr, sp.Derivative) and len(s_.variables) == 1
            and s_.expr.variables and set(s_.expr.variables) == set(s_.variables)]


def _check_compute(claim, ctx: Ctx) -> tuple[str, dict]:
    ev: dict[str, Any] = {}
    if not isinstance(claim, Eq):
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
            dom = ctx.domain_for(var) if var.name in ctx.ns else S.Reals
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
        dom = {s_: ctx.domain_for(s_) if s_.name in ctx.ns else S.Reals for s_ in d.free_symbols}
        ok, cev = answers_equivalent(d, S.Zero, shape="expression" if d.free_symbols else "scalar",
                                     domain=dom or None, seed=ctx.seed)
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
        dom = {s_: ctx.domain_for(s_) if s_.name in ctx.ns else S.Reals for s_ in free}
        ok, cev = answers_equivalent(rhs, val, shape="expression", domain=dom, seed=ctx.seed)
    else:
        ok, cev = answers_equivalent(rhs, val, shape="scalar")
    ev["compare"] = cev
    return ("verified" if ok is True else "refuted" if ok is False else "unknown"), ev


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
    inside = sp.Intersection(*sets) if conjunction else sp.Union(*sets)
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
    for p in premises:
        r = sb_run("mathverify.sandbox.ops:solveset_in", p, v, S.Reals, timeout=ctx.timeout)
        if not r.ok or r.value.has(sp.ConditionSet):
            return None, False, False
        region = sp.Intersection(region, r.value)
    fail = _fail_set(claim, v, region, ctx)
    if fail is None:
        return None, False, False
    if fail is S.EmptySet:
        e = sb_run("mathverify.steps.deterministic:_emptiness", region, timeout=ctx.timeout)
        return None, bool(e.ok and e.value is False), bool(e.ok and e.value is True)
    for pt in _points_of(fail):
        point = {v: pt}
        if not _in_domains(ctx, point):
            continue
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
    from ..equiv.numeric import to_mp
    import mpmath as mp
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
    r = sb_run("mathverify.sandbox.ops:simplify_diff", a, b, timeout=ctx.timeout)
    if not r.ok:
        return None
    d = r.value
    if d == 0:
        sign = 0
    else:
        try:
            dv = to_mp(d, 60)
            av, bv = to_mp(a, 60), to_mp(b, 60)
        except Exception:  # noqa: BLE001
            return None
        if isinstance(dv, mp.mpc) or isinstance(av, mp.mpc) or isinstance(bv, mp.mpc):
            return None if isinstance(rel, (Eq, sp.Ne)) else False
        scale = max(abs(av), abs(bv), mp.mpf(1))
        if abs(dv) <= mp.mpf(10) ** -40 * scale:
            return None
        sign = 1 if dv > 0 else -1
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
    dom = ctx.domain_for(v)
    for part in (claim.args if isinstance(claim, Or) else (claim,)):
        r = sb_run("mathverify.sandbox.ops:solveset_in", part, v, dom, timeout=ctx.timeout)
        if not r.ok or r.value.has(sp.ConditionSet):
            return False
        e = sb_run("mathverify.steps.deterministic:_emptiness", r.value, timeout=ctx.timeout)
        if not (e.ok and e.value is True):
            return False
    return True


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


def _check_eq_in(claim, premises: list, ctx: Ctx, restrictions: list, window: list) -> tuple[str, dict]:
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
            exhaustive = all(_is_polynomial(p, syms) for p in eqs)
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
    checked = inside = outside = 0
    for pt in points:
        if not _in_domains(ctx, pt):
            continue
        if any(_holds(p, pt) is False for p in others):
            continue
        if any(_holds(p, pt) is False for p in bounds):
            outside += 1
            continue
        inside += 1
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
        if exhaustive:
            return "verified", ev
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
        return []
    try:
        rel = parse_set_str(iv, ctx.ns).as_relational(v)
    except Exception:  # noqa: BLE001 - an interval we cannot read restricts nothing
        return []
    parts = list(rel.args) if isinstance(rel, And) else [rel]
    if any(r in (sp.true, sp.false) or not _is_relation(r) for r in parts):
        return []
    return parts


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
        window = _task_window(ir, ctx)
        objects = _task_objects(ir, ctx)
        first_bad = None
        n_ref = n_ver = n_unk = n_skip = n_malformed = 0
        case_claims: dict[str, Any] = {}          # id -> relation assumed in a case branch
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
            try:
                if st.kind == "compute":
                    status, ev = _check_compute(claim, ctx)
                else:
                    # premises: givens + unconditional earlier claims + claims from the same
                    # case branch(es) + the case assumptions themselves
                    premises = list(givens) + [parsed[k] for k in parsed
                                               if k != st.id and parsed_cases.get(k, frozenset()) <= my_case_ids]
                    premises += my_cases
                    status, ev = _check_eq(claim, premises, ctx, restrictions, window)
            except Exception as e:  # noqa: BLE001
                status, ev = "unknown", {"reason": f"checker_exception: {type(e).__name__}: {str(e)[:120]}"}
            entry["status"] = status
            entry["evidence"] = ev
            per_step.append(entry)
            if status == "refuted":
                n_ref += 1
                if first_bad is None:
                    first_bad = idx
                # do not add a refuted claim to the premise pool
                continue
            if status == "verified":
                n_ver += 1
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
