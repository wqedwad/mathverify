"""Word-problem / multiple-choice uniqueness certificate with z3 (E7).

certificate = sat(givens ∧ target = claim) ∧ unsat(givens ∧ target ≠ claim)
With options: exactly one option sat -> certified without trusting the solver's
reasoning; >= 2 sat -> IR incomplete; 0 sat -> IR wrong / inconsistent question.
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import Eq, Ne, FiniteSet

from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown
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
        if out["claim_sat"] is True:
            out["status"] = "certified"
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


def _constraints(ctx: Ctx, extra_rels=None) -> list:
    rels = ctx.givens() + ctx.var_constraints() + list(extra_rels or [])
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
            cons = _constraints(ctx)
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
            cons = [rel] + ctx.var_constraints()
            for c in definedness_conditions(rel, var):
                cons.append(c)
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
                    cert["status"] = "certified"
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
    return unknown(LAYER, "z3_undecided", t.ms, ev)
