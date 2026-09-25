"""Deterministic step refuter.

For every step of kind `eq` or `compute` with a parseable claim:
  * `compute`: claim `lhs = rhs` where lhs contains an unevaluated operation (Derivative,
    Integral, Limit, Sum) or is plain arithmetic -> evaluate lhs with the CAS and compare
    with rhs (domain-aware). A definite difference => REFUTED.
  * `eq`: claim is a relation that should follow from the premises. Premises are the
    IR givens plus ALL earlier parseable step claims (not only the cited ones, so that
    under-citation is never penalised). We look for a point that satisfies every premise,
    lies in the problem domain, and violates the claim. Found => REFUTED with that point.
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
    m = _IN_SET.match(claim)
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


def _set_counterexample(claim, premises: list, v, ctx: Ctx) -> dict | None:
    """A point of the premises' solution set (within the domain) where the claim is false."""
    from ..certify.calculus import _points_of
    neg = _negation(claim)
    if neg is None or any(not isinstance(p, sp.core.relational.Relational) for p in premises):
        return None
    region = ctx.domain_for(v) if v.name in ctx.ns else S.Reals
    for p in premises:
        r = sb_run("mathverify.sandbox.ops:solveset_in", p, v, S.Reals, timeout=ctx.timeout)
        if not r.ok or r.value.has(sp.ConditionSet):
            return None
        region = sp.Intersection(region, r.value)
    rb = sb_run("mathverify.sandbox.ops:solveset_in", neg, v, region, timeout=ctx.timeout)
    if not rb.ok or rb.value is S.EmptySet or rb.value.has(sp.ConditionSet):
        return None
    for pt in _points_of(rb.value):
        point = {v: pt}
        if not _in_domains(ctx, point):
            continue
        if all(_decide(p, point, ctx) is True for p in premises) and _decide(claim, point, ctx) is False:
            return point
    return None


def _decide(rel, point: dict, ctx: Ctx) -> bool | None:
    """Truth of a relation at a point, exact at exact zeros: the difference of the sides is
    simplified first, and a numeric sign is only trusted when it is far from zero. `_holds`
    compares tolerantly, which misreads x^2 - 2x - 1 >= 0 at x = 1 - sqrt(2) (measured)."""
    from ..equiv.numeric import to_mp
    import mpmath as mp
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


def _check_eq(claim, premises: list, ctx: Ctx) -> tuple[str, dict]:
    ev: dict[str, Any] = {"n_premises": len(premises)}
    syms = set(claim.free_symbols)
    prem_syms: set = set()
    for p in premises:
        syms |= p.free_symbols
        prem_syms |= p.free_symbols
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
        w = _set_counterexample(claim, premises, syms[0], ctx)
        if w is not None:
            ev["counterexample"] = {str(k): str(v) for k, v in w.items()}
            ev["route"] = "premise_set"
            return "refuted", ev
    eqs = [p for p in premises if isinstance(p, Eq)]
    others = [p for p in premises if not isinstance(p, Eq)]
    points: list[dict] = []
    # route 1: solve the equational premises
    if eqs:
        r = sb_run("mathverify.sandbox.ops:solve_system", eqs, syms, True, timeout=ctx.timeout)
        if r.ok and isinstance(r.value, list):
            sols = [s_ for s_ in r.value if isinstance(s_, dict)]
            ev["solutions"] = len(sols)
            if not sols:
                return "unknown", {"reason": "premises_inconsistent_or_unsolved", **ev}
            for s_ in sols:
                # parametric solution: sample the remaining free symbols
                rem = set()
                for v in s_.values():
                    rem |= v.free_symbols
                rem |= set(syms) - set(s_.keys())
                if rem:
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
        for pt in sample_points(doms, 60, ctx.seed) + _small_integer_grid(doms):
            if all(_holds(p, pt) is True for p in premises):
                points.append(pt)
        ev["rejection_sampled"] = len(points)
        if len(points) < 3 and premises:
            return "unknown", {"reason": "no_premise_satisfying_points", **ev}
    checked = 0
    for pt in points:
        if not _in_domains(ctx, pt):
            continue
        if any(_holds(p, pt) is False for p in others):
            continue
        h = _holds(claim, pt)
        if h is False:
            # confirm robustly: every premise must hold definitively at this point
            if all(_holds(p, pt) is True for p in premises):
                ev["counterexample"] = {str(k): str(v) for k, v in pt.items()}
                return "refuted", ev
        if h is True:
            checked += 1
    ev["points_checked"] = checked
    if checked and checked == len([p for p in points if _in_domains(ctx, p)]):
        return "verified", ev
    return "unknown", ev


def check_steps(ir, solution, ctx: Ctx):
    with Timer() as t:
        per_step: list[dict[str, Any]] = []
        parsed: dict[str, Any] = {}
        parsed_cases: dict[str, frozenset] = {}
        givens = []
        try:
            givens = ctx.givens() + ctx.var_constraints()
        except Exception:
            pass
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
            try:
                claim = _parse_claim(st.claim, _step_namespace(ctx.ns) if st.kind == "compute" else ctx.ns)
            except UndeclaredSymbolError as e:
                # The solver named something of its own (`u = sqrt(x+4)`). Well-formed
                # mathematics we simply cannot check: skipped, no penalty (§3 rule 3).
                entry["status"] = "skipped"
                entry["reason"] = f"undeclared_symbol: {str(e)[:120]}"
                n_skip += 1
                per_step.append(entry)
                continue
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
            try:
                if st.kind == "compute":
                    status, ev = _check_compute(claim, ctx)
                else:
                    # premises: givens + unconditional earlier claims + claims from the same
                    # case branch(es) + the case assumptions themselves
                    premises = list(givens) + [parsed[k] for k in parsed
                                               if k != st.id and parsed_cases.get(k, frozenset()) <= my_case_ids]
                    premises += my_cases
                    status, ev = _check_eq(claim, premises, ctx)
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
