"""Word-problem / multiple-choice uniqueness certificate with z3 (E7).

certificate = sat(givens ∧ target = claim) ∧ unsat(givens ∧ target ≠ claim)
With options: exactly one option sat -> certified without trusting the solver's
reasoning; >= 2 sat -> IR incomplete; 0 sat -> IR wrong / inconsistent question.
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import S, Eq, Ne, FiniteSet

from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown, closed_binding
from .domain import definedness_conditions

LAYER = "certify.wordproblem"


def _check(constraints, syms_info, extra, timeout_ms):
    r = sb_run("mathverify.sandbox.ops:z3_check", list(constraints), dict(syms_info), list(extra),
               timeout_ms, timeout=timeout_ms / 1000 + 3)
    if not r.ok:
        return ("error", r.error)
    return r.value


def uniqueness_certificate(givens, target, syms_info: dict[str, str], claimed_value,
                           options: dict[str, Any] | None = None, timeout_ms: int = 4000) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "unknown", "claim_sat": None, "other_unsat": None,
                           "sat_options": [], "option_status": {}, "unsupported": None}
    givens = list(givens)
    # claim
    if claimed_value is not None:
        st, m = _check(givens, syms_info, [Eq(target, claimed_value)], timeout_ms)
        if st == "unsupported":
            out["unsupported"] = m
            return out
        if st == "error":
            out["error"] = m
            return out
        out["claim_sat"] = (st == "sat")
        out["claim_model"] = m if st == "sat" else None
        if st == "unknown":
            out["claim_sat"] = None
        st2, _ = _check(givens, syms_info, [Ne(target, claimed_value)], timeout_ms)
        out["other_unsat"] = (st2 == "unsat") if st2 in ("sat", "unsat") else None
        if st2 == "unsupported":
            out["unsupported"] = _
            return out
    # options
    if options:
        for letter, val in options.items():
            if val is None:
                out["option_status"][letter] = "unparsed"
                continue
            st, m = _check(givens, syms_info, [Eq(target, val)], timeout_ms)
            out["option_status"][letter] = st
            if st == "sat":
                out["sat_options"].append(letter)
            if st == "unsupported":
                out["unsupported"] = m
                return out
        n = len(out["sat_options"])
        if any(v == "unknown" for v in out["option_status"].values()):
            out["status"] = "unknown"
            return out
        if n == 0:
            out["status"] = "ir_inconsistent"
            return out
        if n >= 2:
            out["status"] = "ir_incomplete"
            return out
        # Exactly one satisfiable option is NOT a proof that the givens determine the value: the
        # true value may simply be missing from the options. Measured (audit of 25 Sep 2026):
        # 3a + 5b = 41 over positive integers allows a + b ∈ {9, 11, 13}; with options
        # {9, 10, 12} only 9 was satisfiable and "a + b = 9" was certified CORRECT. The claim is
        # certified only when every other value is also excluded (other_unsat).
        if out["claim_sat"] is True and out["other_unsat"] is True:
            out["status"] = "certified"
        elif out["claim_sat"] is True and out["other_unsat"] is False:
            out["status"] = "not_unique"
        elif out["claim_sat"] is False:
            out["status"] = "refuted"
        return out
    if out["claim_sat"] is True and out["other_unsat"] is True:
        out["status"] = "certified"
    elif out["claim_sat"] is False:
        out["status"] = "refuted"
    elif out["claim_sat"] is True and out["other_unsat"] is False:
        out["status"] = "not_unique"
    return out


class _DomainUntranslatable(ValueError):
    pass


def _set_as_relation(dom, v):
    """A domain set as a z3-translatable relation in v (finite bounds only)."""
    if dom == S.Reals:
        return sp.true
    if dom is S.EmptySet:
        return sp.false
    if isinstance(dom, sp.Interval):
        parts = []
        if dom.inf != -sp.oo:
            parts.append(sp.Gt(v, dom.inf, evaluate=False) if dom.left_open else sp.Ge(v, dom.inf, evaluate=False))
        if dom.sup != sp.oo:
            parts.append(sp.Lt(v, dom.sup, evaluate=False) if dom.right_open else sp.Le(v, dom.sup, evaluate=False))
        return sp.And(*parts) if parts else sp.true
    if isinstance(dom, sp.FiniteSet):
        return sp.Or(*[sp.Eq(v, p, evaluate=False) for p in dom.args])
    if isinstance(dom, sp.Union):
        return sp.Or(*[_set_as_relation(a, v) for a in dom.args])
    if isinstance(dom, sp.Intersection):
        return sp.And(*[_set_as_relation(a, v) for a in dom.args if a not in (S.Integers,)])
    if isinstance(dom, sp.Complement) and isinstance(dom.args[1], sp.FiniteSet):
        return sp.And(_set_as_relation(dom.args[0], v),
                      *[sp.Ne(v, p, evaluate=False) for p in dom.args[1].args])
    if dom in (S.Integers,):
        return sp.true
    raise _DomainUntranslatable(str(dom))


def _discourse_constraints(ctx: Ctx) -> list:
    """The problem's domain of discourse (`domain_of_discourse`) for each variable it mentions.
    It used to be ignored here: z3 then found the root x = 0 of x³ = x "missing" from the claim
    {1} on x > 0 and refuted the right answer (audit of 25 Sep 2026)."""
    from ..normalize.parse import parse_domain
    dod = ctx.ir.domain_of_discourse
    if not dod:
        return []
    out = []
    for v in ctx.syms():
        if not ctx._dod_mentions(v):
            continue
        dom = parse_domain(dod, v, ctx.ns)
        rel = _set_as_relation(dom, v)
        if rel is not sp.true:
            out.append(rel)
    return out


class _GivenSystem(ValueError):
    pass


def _equation_givens(ctx: Ctx, rel, var, seeds: set, others: list) -> tuple[list, set]:
    """The givens that constrain the equation, and every symbol the equation is tied to: a given
    or a constraint (`others`: the variables' constraints, the domain of discourse) joins when it
    shares a symbol with the equation, the claim (`seeds`) or one that joined (`a = 4` next to
    x² = a; `x > 5` next to 2x = 4; `b = 0` next to the constraint x > b). Only the
    single-variable inequalities in `var` were used before, so z3 read every other symbol of the
    equation as free: the model {x: 0, a: 0} made the right {-2, 2} of x² = a with a = 4 "miss a
    root", and x² + a² = 0 with a = 4 had {0} certified (third audit of 30 Sep 2026, N7). A second
    equation in `var` makes a system, which this certificate does not solve (`_GivenSystem`)."""
    rest = [(g, True) for g in ctx.givens() if g != rel] + [(c, False) for c in others]
    syms = set(rel.free_symbols) | {var} | set(seeds)
    used: list = []
    grew = True
    while grew:
        grew = False
        for item in list(rest):
            fs = getattr(item[0], "free_symbols", set())
            if fs & syms:
                rest.remove(item)
                if item[1]:
                    used.append(item[0])
                syms |= fs
                grew = True
    for g in used:
        if isinstance(g, Eq) and var in g.free_symbols:
            raise _GivenSystem(str(g))
    return used, syms


def _constraints(ctx: Ctx, extra_rels=None) -> list:
    rels = ctx.givens() + ctx.var_constraints() + _discourse_constraints(ctx) + list(extra_rels or [])
    # definedness of every expression appearing in the givens (sqrt radicand >= 0, denominators != 0)
    out = list(rels)
    for r in rels:
        for v in ctx.syms():
            for c in definedness_conditions(r, v):
                if c not in out:
                    out.append(c)
    return out


def verify(ir, solution, ctx: Ctx):
    kind = ir.task.kind
    if kind not in ("evaluate", "solve_equation"):
        return unknown(LAYER, "not_applicable")
    if not ir.givens and not ir.task.params.get("equation"):
        return unknown(LAYER, "no_givens")
    with Timer() as t:
        p = ir.task.params
        syms_info = ctx.syms_info()
        ev: dict[str, Any] = {}
        if kind == "evaluate":
            expr_src = p.get("expr") or ir.unknown_of_interest
            if not expr_src:
                return unknown(LAYER, "no_target_expression")
            target, err = parse_or_unknown(LAYER, ctx.expr, expr_src)
            if err:
                return err
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            if isinstance(claimed, sp.Set) or (hasattr(claimed, "free_symbols") and claimed.free_symbols):
                return unknown(LAYER, "claimed_not_scalar")
            options = None
            if ir.options:
                options = {}
                for letter in ir.options:
                    try:
                        options[letter] = ctx.option_value(letter)
                    except Exception:
                        options[letter] = None
            try:
                cons = _constraints(ctx)
            except _DomainUntranslatable as e:
                return unknown(LAYER, f"domain_of_discourse_not_translatable: {e}")
            # the target must be defined at the solution (1/√a with a = 0 has no value)
            for v in ctx.syms():
                for c in definedness_conditions(target, v):
                    if c not in cons:
                        cons.append(c)
            cert = uniqueness_certificate(cons, target, syms_info, claimed, options)
            ev.update({"target": str(target), "claimed": str(claimed), "constraints": [str(c) for c in cons], "z3": cert})
        else:  # solve_equation: each claimed root sat; all-other unsat (completeness by z3)
            var = ctx.sym(p.get("var", "x"))
            eq_src = p.get("equation") or ir.givens[0]
            rel, err = parse_or_unknown(LAYER, ctx.rel, eq_src)
            if err:
                return err
            from .algebra import _claimed_as_set
            claimed, err = parse_or_unknown(LAYER, _claimed_as_set, ctx, solution)
            if err:
                return err
            if not isinstance(claimed, FiniteSet):
                return unknown(LAYER, "claimed_set_not_finite")
            if var.name not in syms_info:
                syms_info[var.name] = "real"
            try:
                # the givens restrict the solutions (x > 5 next to 2x = 4) and fix the parameters
                # (a = 4 next to x² = a)
                others = ctx.var_constraints() + _discourse_constraints(ctx)
                extra, tied = _equation_givens(ctx, rel, var, claimed.free_symbols, others)
                cons = [rel] + extra + others
            except _DomainUntranslatable as e:
                return unknown(LAYER, f"domain_of_discourse_not_translatable: {e}")
            except _GivenSystem as e:
                return unknown(LAYER, f"given_equation_in_the_variable: {e}")
            for c in definedness_conditions(rel, var):
                cons.append(c)
            params = [g for g in extra if var not in g.free_symbols]
            if params:
                # contradictory givens (a = 4 and a = 9) leave no instance of the problem: a root
                # z3 then finds "unsatisfiable" is no evidence against the claim
                st, m = _check(params + others, syms_info, [], 4000)
                if st == "unsupported":
                    return unknown(LAYER, f"z3_unsupported: {m}", flags=["z3_unsupported"])
                if st != "sat":
                    return unknown(LAYER, f"givens_without_an_instance: {st}")
            # A claimed root is checked for SOME value of the parameters (sat), the other roots for
            # every value (unsat). The claim is the answer only where the givens pin each parameter
            # to one value: with `a` free, {0} for x² + a² = 0 and {-√a, √a, 2} for x² = a were
            # certified, true only at a = 0 and a = 4; so was {-2, 2} for x² = 4 under x > b.
            pinned = {b[0] for b in map(closed_binding, extra + others) if b is not None}
            free_params = sorted(s_.name for s_ in tied - pinned - {var})
            # exclude non-rational claimed roots (z3 works over exact rationals/algebraics)
            roots = list(claimed.args)
            cert: dict[str, Any] = {"roots": {}, "status": "unknown"}
            all_sat = True
            for r_ in roots:
                st, m = _check(cons, syms_info, [Eq(var, r_)], 4000)
                cert["roots"][str(r_)] = st
                if st == "unsupported":
                    return unknown(LAYER, f"z3_unsupported: {m}", 0, {"z3": cert}, flags=["z3_unsupported"])
                if st != "sat":
                    all_sat = False if st == "unsat" else all_sat
                    if st == "unsat":
                        cert["status"] = "refuted"
                        cert["bad_root"] = str(r_)
                        break
            if cert["status"] != "refuted":
                st, m = _check(cons, syms_info, [Ne(var, r_) for r_ in roots], 4000)
                cert["others"] = st
                cert["other_model"] = m
                if st == "unsat" and all_sat:
                    cert["status"] = "certified" if not free_params else "parameters_not_pinned"
                    if free_params:
                        cert["free_parameters"] = free_params
                elif st == "sat":
                    cert["status"] = "missing_root"
                    cert["status_detail"] = m
            ev.update({"equation": str(rel), "claimed": str(claimed), "z3": cert})
    st = ev["z3"].get("status")
    if ev["z3"].get("unsupported"):
        return unknown(LAYER, f"z3_unsupported: {ev['z3']['unsupported']}", t.ms, ev, flags=["z3_unsupported"])
    if st == "certified":
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if st in ("refuted", "missing_root"):
        ev["reason"] = st
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    if st == "ir_incomplete":
        return unknown(LAYER, "ir_incomplete_multiple_options_sat", t.ms, ev, flags=["ir_incomplete"])
    if st == "ir_inconsistent":
        return unknown(LAYER, "ir_inconsistent_no_option_sat", t.ms, ev, flags=["ir_inconsistent"])
    if st == "not_unique":
        return unknown(LAYER, "target_not_unique", t.ms, ev, flags=["ir_incomplete"])
    if st == "parameters_not_pinned":
        return unknown(LAYER, "parameters_not_pinned_by_the_givens", t.ms, ev)
    return unknown(LAYER, "z3_undecided", t.ms, ev)
