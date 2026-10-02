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
from ..normalize.parse import ParseError, parse_relation, UndeclaredSymbolError, _refuse_reversed_ranges
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


def _check_compute(claim, ctx: Ctx, doms: dict | None = None) -> tuple[str, dict]:
    ev: dict[str, Any] = {}
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
        dom = _compare_domains(d.free_symbols, ctx, doms)
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
        ok, cev = answers_equivalent(rhs, lhs, shape="expression", domain=dom, seed=ctx.seed)
        ev["compare"] = cev
        if ok is True:
            return "verified", ev
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
        ok, cev = answers_equivalent(rhs, val, shape="expression", domain=dom, seed=ctx.seed)
    else:
        ok, cev = answers_equivalent(rhs, val, shape="scalar")
    ev["compare"] = cev
    return ("verified" if ok is True else "refuted" if ok is False else "unknown"), ev


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


def _confined_values(v, rels: list, ctx: Ctx) -> list | None:
    """The values of `v` its domain (with the points where a range of the problem runs backwards) and the
    relations `rels` on `v` alone leave, when they are finitely many exact real numbers; None otherwise.
    A relation solveset cannot solve exactly is left out (the set stays a superset; each point is checked
    against every premise afterwards)."""
    region = sp.Union(ctx.domain_for(v), ctx.reversed_region(v))
    narrowed = False
    for p in rels:
        r = sb_run("mathverify.sandbox.ops:solveset_in", p, v, S.Reals, timeout=ctx.timeout)
        if not r.ok or not isinstance(r.value, sp.Set) or r.value.has(sp.ConditionSet):
            continue
        region = sp.Intersection(region, r.value)
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


def _system_points(rels: list, order: list, ctx: Ctx) -> list[dict] | None:
    """The real solutions of the premises' equations when they are polynomial and determine every symbol
    in `order` (finitely many points, each exact); None otherwise. The solution set of such a system is
    complete (as `_check_eq_in` relies on: route 1, `exhaustive`)."""
    eqs = [p for p in rels if isinstance(p, Eq)]
    if not eqs or not all(_is_polynomial(p, order) for p in eqs):
        return None
    r = sb_run("mathverify.sandbox.ops:solve_system", eqs, order, True, timeout=ctx.timeout)
    if not r.ok or not isinstance(r.value, list):
        return None
    out: list[dict] = []
    for s_ in r.value:
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
    """The range conditions of the claim's own Sums and Products that name a symbol: `Contains(hi - lo + 1,
    FORWARD_SPANS)` (`certify.domain.is_range_span`), which holds where the range runs forward or is empty
    and is undecided where it runs backwards (hi < lo - 1)."""
    if not isinstance(claim, sp.Basic) or not claim.has(sp.Sum, sp.Product):
        return []
    from ..certify.domain import definedness_conditions, is_range_span
    try:
        conds = definedness_conditions(claim, None)
    except Exception:  # noqa: BLE001 - no conditions read: the claim is refuted as before
        return []
    return [c for c in conds if is_range_span(c) and c.free_symbols]


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


def _refuted_where_backwards(claim, ev: dict) -> bool:
    """Was the refutation of `claim` found where one of its own ranges runs backwards, or at a point not
    read back while it has such a range? Every route's point is checked here: the premises' solution set,
    a value pinned by a given (`floor` evaluated the pinned Sum, so the parser's range check missed it),
    a random point of the identity check."""
    spans = _range_spans(claim)
    if not spans:
        return False
    pt = _refutation_point(ev, getattr(claim, "free_symbols", set()))
    return pt is None or _runs_backwards_at(spans, pt)


def _check_at(claim, text: str, point: dict, ctx: Ctx) -> tuple[str, dict]:
    """The `compute` claim checked at a point: the sides substituted separately (Eq would evaluate itself
    on substitution), a Sum/Product range there through the parser's range checks (reversed, or not an
    integer apart: the claim is not read there). A range that runs backwards at the point decides nothing,
    also when the substitution evaluated it away (`floor` of a pinned Sum: `_runs_backwards_at`)."""
    pinned = Eq(claim.lhs.xreplace(point), claim.rhs.xreplace(point), evaluate=False)
    try:
        _refuse_reversed_ranges(pinned, text)
    except ParseError as e:
        return "unknown", {"reason": f"pinned_claim_not_read: {str(e)[:160]}"}
    if _runs_backwards_at(_range_spans(claim), point):
        return "unknown", {"reason": "a_range_of_the_claim_runs_backwards_at_the_point"}
    return _check_compute(pinned, ctx)


def _on_premises(claim, text: str, premises: list, ctx: Ctx, status: str, ev: dict) -> tuple[str, dict]:
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
      (x > 0 from x > y and y > 0 is not derived): that refutation stands."""
    syms = getattr(claim, "free_symbols", None)
    if not isinstance(claim, Eq) or not syms or any(ctx.ns.get(q.name) != q for q in syms):
        return status, ev
    if _binders_keep_clear_of(claim, syms):
        inst = _finite_instances(syms, premises, ctx)
        if inst is not None:
            if inst[0] or inst[1]:
                return _check_instances(claim, text, syms, inst, ctx, ev)
            return status, ev                # no instance at all: nothing to check it at
    if status != "refuted":
        return status, ev
    direct = [p for p in _premise_parts(premises) if p.free_symbols <= syms]
    if not direct:
        return status, ev
    pt = _counterexample_point(ev, syms)
    if pt is None:
        return status, ev
    if all(_holds_exactly(p, pt, ctx) is True for p in direct):
        return status, {**ev, "counterexample_satisfies_premises": True}
    region: dict = {}
    back: list = []
    for q in syms:
        dom, rev = ctx.domain_for(q), ctx.reversed_region(q)
        for p in direct:
            if p.free_symbols == {q} and isinstance(p, sp.core.relational.Relational):
                r = sb_run("mathverify.sandbox.ops:solveset_in", p, q, S.Reals, timeout=ctx.timeout)
                if r.ok and isinstance(r.value, sp.Set) and not r.value.has(sp.ConditionSet):
                    dom, rev = sp.Intersection(dom, r.value), sp.Intersection(rev, r.value)
        if dom != ctx.domain_for(q):
            region[q] = dom
        back.append(rev)
    if any(d is S.EmptySet for d in region.values()):
        return status, ev                    # no instance at all: nothing to check it at
    base = {"identity_refuted": ev, "premise_region": {str(k): str(v) for k, v in region.items()}}
    pending = None
    for doms in (_region_cells(region) if region else []):
        s2, ev2 = _check_compute(claim, ctx, doms=doms)
        if s2 == "refuted":
            pt2 = _counterexample_point(ev2, syms)
            if pt2 is not None and all(_holds_exactly(p, pt2, ctx) is True for p in direct):
                return "refuted", {**ev2, **base, "counterexample": {str(k): str(v) for k, v in pt2.items()}}
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
        return "verified", base
    # no counterexample the premises allow yet: one is searched where they put the symbols
    if _binders_keep_clear_of(claim, syms):
        found = _counterexample_on_premises(claim, text, direct, syms, ctx, region)
        if found is not None:
            return "refuted", {**found[1], **base, "counterexample": {str(k): str(v) for k, v in found[0].items()}}
    if pending is None:
        return "unknown", {**base, "reason": "identity_counterexample_not_an_instance"}
    return "unknown", {**pending[1], **base, "reason": pending[1].get("reason") or "undecided_on_the_premise_region"}


_MAX_TRIES = 6                       # premise-satisfying points the claim is checked at in the search


def _counterexample_on_premises(claim, text: str, direct: list, syms, ctx: Ctx, region: dict):
    """(a point every premise in `direct` holds at, where the claim is refuted, the evidence), or None:
    searched on the solutions of the premises' equations (a parametric solution sampled: y = 2x + 1) or,
    without equations, among sample points of the region (x > y). At most _MAX_TRIES points are checked."""
    order = sorted(syms, key=lambda q: q.name)
    doms = {q: region.get(q, ctx.domain_for(q)) for q in order}
    eqs = [p for p in direct if isinstance(p, Eq)]
    cands: list[dict] = []
    if eqs:
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
            for pt in (sample_points(rdoms, 12, ctx.seed) + _small_integer_grid(rdoms)[:12] if rem else [{}]):
                full = {k: v.xreplace(pt) for k, v in s_.items()}
                full.update(pt)
                cands.append(full)
    else:
        cands = sample_points(doms, 30, ctx.seed) + _small_integer_grid(doms)[:30]
    tried = 0
    for pt in cands:
        if set(pt) != set(order) or any(getattr(v, "free_symbols", True) for v in pt.values()):
            continue
        if not _in_domains(ctx, pt) or any(_holds(p, pt) is not True for p in direct):
            continue
        if any(_holds_exactly(p, pt, ctx) is not True for p in direct):
            continue
        tried += 1
        s_, e_ = _check_at(claim, text, pt, ctx)
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


def _check_instances(claim, text: str, syms, inst, ctx: Ctx, ev: dict) -> tuple[str, dict]:
    certain, undecided = inst
    base = {"identity_refuted": ev, "instances_by_premises": {
        "certain": [{str(k): str(v) for k, v in pt.items() if k in syms} for pt in certain],
        "undecided": [{str(k): str(v) for k, v in pt.items() if k in syms} for pt in undecided]}}
    seen: dict = {}

    def at(pt):
        key = tuple(sorted(((str(k), sp.srepr(v)) for k, v in pt.items() if k in syms)))
        if key not in seen:
            seen[key] = _check_at(claim, text, {k: v for k, v in pt.items() if k in syms}, ctx)
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
    """A closed equation whose only forms are integrals is refuted when, over every corner of each
    integral's enclosure (`certify.calculus.integral_enclosure`: tanh-sinh and Gauss-Legendre at 30
    and 50 digits agreeing, 10^3 times their error estimate), the sides keep the same strict order:
    "Integral(Abs(cos(x)), (x, -1, 1)) = 0" stays refuted where SymPy's closed form is wrong. A value
    without such an enclosure refutes nothing: SymPy's evalf of the Dirichlet integral, '-0.e+0' with
    no significant bit, was read as a 40-digit 0 and refuted "∫_0^oo sin x/x dx = π/2" (fourth audit of
    1 Oct 2026, S3). The tolerant `_holds` is not used over forms: its value of a sum (Euler-Maclaurin)
    is wrong for oscillating terms (Σ cos(πk/4)/k² came out 0.565345, it is 11π²/192 = 0.565446) and
    refuted true identities; nor over a sum or product at all (audit of 29 Sep 2026)."""
    if not isinstance(claim, Eq) or claim.has(sp.Sum, sp.Product, sp.Limit, sp.Derivative):
        return False
    import itertools
    import mpmath as mp
    from ..certify.calculus import integral_enclosure
    from ..equiv.numeric import to_mp
    forms = list(claim.atoms(sp.Integral))
    if not forms or len(forms) > 3:
        return False
    boxes = []
    for n in forms:
        if n.free_symbols or len(n.limits) != 1 or len(n.limits[0]) != 3:
            return False
        var, a, b = n.limits[0]
        enc = integral_enclosure(n.function, var, a, b, timeout=ctx.timeout)
        if enc is None:
            return False
        boxes.append(enc[:2])
    d = claim.lhs - claim.rhs
    signs = set()
    with mp.workdps(70):
        for corner in itertools.product((-1, 0, 1), repeat=len(forms)):
            reps = {n: sp.Float(mp.nstr(v + c * w, 65), 65) for n, (v, w), c in zip(forms, boxes, corner)}
            try:
                dv = to_mp(d.xreplace(reps), 60)
            except Exception:  # noqa: BLE001
                return False
            if isinstance(dv, mp.mpc) or not mp.isfinite(dv) or dv == 0:
                return False
            signs.add(dv > 0)
    return len(signs) == 1


def _check_eq_in(claim, premises: list, ctx: Ctx, restrictions: list, window: list) -> tuple[str, dict]:
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
    checked = inside = outside = backwards = 0
    spans = _range_spans(claim)
    for pt in points:
        if not _in_domains(ctx, pt):
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


def _undefined_as_written(text: str, ns: dict[str, Any]) -> bool:
    """Is the claim, read AS WRITTEN, undefined whatever its free symbols are (a closed condition
    that fails, e.g. a term of a finite sum at one of its indices)? The value parse folds j/j to 1,
    and the compute step `Sum(j/j, (j, -1, 1)) = 3` was verified (V14 tests, 30 Sep 2026). Undeclared
    names are read as `_with_bound_dummies` reads them; a text that cannot be read that way adds
    nothing."""
    from ..certify.domain import closed_condition_undecided, definedness_conditions
    from ..normalize.parse import _check_safe, _strip_invisible, parse_as_written, preclean
    try:
        names = _check_safe(preclean(_strip_invisible(text)), ns)
    except Exception:  # noqa: BLE001 - LaTeX, or not well-formed: the parse decides
        names = []
    if names:
        ns = dict(ns, **{n: sp.Symbol(n) for n in names if n not in ns})
    try:
        w = parse_as_written(text, ns)
        if w is None:
            return False
        conds = definedness_conditions(w, None)
        # a binder whose body is not proved to exist (DEFINEDNESS_UNDECIDED) is not verified either
        return any(c is sp.false for c in conds) or closed_condition_undecided(conds)
    except Exception:  # noqa: BLE001 - no reading as written: nothing is added
        return False


def _undefined_at_premises(text: str, ns: dict[str, Any], premises: list, ctx: Ctx) -> bool:
    """Is the claim, read AS WRITTEN, not proved defined at a point the premises allow, when they
    allow finitely many (a premise pins a symbol, `x = 0`, or the premises on one symbol have a finite
    solution set, x**2 = 4)? `_undefined_as_written` looks at closed conditions only, and the value
    parse folds the rest away: the eq step "x/x = 1" was verified under x = 0, "sqrt(x - 3)**2 = x - 3"
    under x = 2, "x + gcd(x, 2) - gcd(2, x) = pi + E" under x = pi + E and "sqrt(x)**2 = x" under
    x**2 = 4 (V16, 30 Sep 2026)."""
    from ..certify.base import closed_binding
    from ..certify.domain import decide_membership, definedness_conditions
    from ..normalize.parse import _check_safe, _strip_invisible, parse_as_written, preclean
    try:
        names = _check_safe(preclean(_strip_invisible(text)), ns)
    except Exception:  # noqa: BLE001 - LaTeX, or not well-formed: the parse decides
        names = []
    if names:
        ns = dict(ns, **{n: sp.Symbol(n) for n in names if n not in ns})
    try:
        w = parse_as_written(text, ns)
        conds = [c for c in definedness_conditions(w, None) if getattr(c, "free_symbols", None)] if w is not None else []
    except Exception:  # noqa: BLE001 - no reading as written: nothing is added
        return False
    if not conds:
        return False
    syms = set().union(*(c.free_symbols for c in conds))
    pins: dict = {}
    for p in premises:
        b = closed_binding(p)
        if b is not None and b[0] in syms:
            pins.setdefault(b[0], b[1])
    points: list[dict] = []
    if set(pins) == syms:
        points = [pins]
    elif len(syms) == 1:
        (v,) = syms
        own = [p for p in premises if isinstance(p, sp.core.relational.Relational) and p.free_symbols == {v}]
        if not own or ctx.ns.get(v.name) != v:
            return False
        region = ctx.domain_for(v)
        for p in own:
            r = sb_run("mathverify.sandbox.ops:solveset_in", p, v, S.Reals, timeout=ctx.timeout)
            if not r.ok or r.value.has(sp.ConditionSet):
                return False
            region = sp.Intersection(region, r.value)
        if not isinstance(region, sp.FiniteSet) or len(region) > 12:
            return False
        points = [{v: q} for q in region]
    for point in points:
        for c in conds:
            if isinstance(c, sp.Contains):
                try:
                    held = decide_membership(c.args[0].xreplace(point), c.args[1])
                except Exception:  # noqa: BLE001
                    held = None
            else:
                held = _decide(c, point, ctx)
            if held is not True:
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
            chosen = False
            try:
                if st.kind == "compute":
                    status, ev = _check_compute(claim, ctx)
                    if status == "refuted" or (status == "unknown" and ev.get("reason") == "parametric_form"):
                        # the identity failed; its counterexample is no instance of the problem when
                        # the premises pin every symbol of the claim (principle 5). An integral with a
                        # parameter has no value until the premises pin it (DECISIONS §80).
                        # (laid out as before part 10: part 3's mutations name these lines)
                        pool = (list(givens) + list(restrictions)
                                     + [parsed[k] for k in verified
                                        if k in parsed and parsed_cases.get(k, frozenset()) <= my_case_ids])
                        pins = _pins(claim, pool)
                        if not pins:
                            # the premises confine the symbols to finitely many values, or narrow them;
                            # a failure there leaves the identity check as it was
                            try:
                                status, ev = _on_premises(claim, st.claim, pool, ctx, status, ev)
                            except Exception as e:  # noqa: BLE001
                                ev = {**ev, "premise_recheck_failed": f"{type(e).__name__}: {str(e)[:120]}"}
                        if pins:
                            # the sides separately: Eq would evaluate itself on substitution
                            pinned = Eq(claim.lhs.xreplace(pins), claim.rhs.xreplace(pins), evaluate=False)
                            try:
                                # a pinned limit of a Sum or Product must pass the parser's range checks
                                # (reversed, or not an integer apart), or the claim is not read there
                                _refuse_reversed_ranges(pinned, st.claim)
                            except ParseError as e:
                                status, pev = "unknown", {"reason": f"pinned_claim_not_read: {str(e)[:160]}"}
                            else:
                                status, pev = _check_compute(pinned, ctx)
                            ev = {**pev, "pinned_by_premises": {str(k): str(v) for k, v in pins.items()},
                                  "identity_refuted": ev}
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
            if status == "refuted" and _refuted_where_backwards(claim, ev):
                # the counterexample sits where a range of the claim runs backwards: the value SymPy
                # refuted there is Karr's convention, not the curriculum's (part 11, DECISIONS §80)
                status, ev = "unknown", {"reason": "counterexample_where_a_range_of_the_claim_runs_backwards",
                                         "withdrawn": ev}
            why = None
            if status != "refuted":
                if _undefined_as_written(st.claim, step_ns):
                    why = "claim_undefined_as_written"
                elif _undefined_at_premises(st.claim, step_ns, list(givens) + [
                        parsed[k] for k in parsed if parsed_cases.get(k, frozenset()) <= my_case_ids] + my_cases, ctx):
                    why = "claim_undefined_at_the_premises_point"
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
