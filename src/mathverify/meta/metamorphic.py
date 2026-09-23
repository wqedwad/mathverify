"""Metamorphic method test (L5).

A solution whose *method* is wrong can still land on the right answer (D cell). Under a
change of the problem's data the same method should fail, while a right method keeps
working. We therefore (1) build perturbed instances of the problem with a KNOWN answer
(new values for the unknowns, givens re-derived from them — fully deterministic, checked
for uniqueness with SymPy), (2) ask the solver family to solve each instance *following the
given solution's method*, and (3) compare with the known answer deterministically.

Scope in F3: `evaluate` tasks with equational givens (word problems, systems). The signal is
soft: `l5_method_failed` lowers confidence; it never produces a verdict by itself.
"""
from __future__ import annotations

import json
import random
from typing import Any

import sympy as sp

from ..certify.base import Timer, result, unknown
from ..equiv import answers_equivalent
from ..intake.structured import load_problem_ir
from ..normalize.parse import build_namespace, parse_relation, parse_expr_str, parse_answer

__all__ = ["perturb_ir", "metamorphic_check", "l5_layer"]

LAYER = "meta.metamorphic"


def _sample_value(domain: str, rng: random.Random):
    if domain in ("positive_integer", "natural"):
        return sp.Integer(rng.randint(2, 40))
    if domain == "nonneg_integer":
        return sp.Integer(rng.randint(0, 40))
    if domain == "integer":
        return sp.Integer(rng.randint(-20, 40))
    if domain == "positive_real":
        return sp.Integer(rng.randint(2, 30)) if rng.random() < 0.7 else sp.Rational(rng.randint(3, 60), 2)
    if domain == "nonneg_real":
        return sp.Integer(rng.randint(0, 30))
    return sp.Integer(rng.randint(-15, 30)) if rng.random() < 0.7 else sp.Rational(rng.randint(-40, 60), 4)


def _holds(rel, point: dict) -> bool | None:
    try:
        sub = rel.subs(point, simultaneous=True)
    except Exception:
        return None
    if sub is sp.true:
        return True
    if sub is sp.false:
        return False
    try:
        return bool(sp.simplify(sub))
    except Exception:
        return None


def perturb_ir(ir: dict[str, Any], seed: int = 0, k: int = 3, tries: int = 40) -> list[dict[str, Any]]:
    """Return up to k perturbed instances [{"ir", "expected", "values", "changed"}] or [] if not applicable."""
    try:
        obj = load_problem_ir(ir)
    except Exception:
        return []
    if obj.task.kind != "evaluate" or not obj.givens or not obj.vars:
        return []
    if any(f.params for f in obj.functions):
        return []
    ns = build_namespace(obj)
    syms = {v.name: ns[v.name] for v in obj.vars}
    try:
        rels = [parse_relation(g, ns) for g in obj.givens]
        target = parse_expr_str(obj.task.params.get("expr") or obj.unknown_of_interest, ns)
        cons = [parse_relation(c, ns) for v in obj.vars for c in v.constraints]
    except Exception:
        return []
    eqs = [r for r in rels if isinstance(r, sp.Equality)]
    ineqs = [r for r in rels if not isinstance(r, sp.Equality)]
    if not eqs:
        return []
    # only equations with one numeric side can be re-derived
    for e in eqs:
        if not (e.rhs.is_number or e.lhs.is_number):
            return []
    rng = random.Random(seed)
    variants: list[dict[str, Any]] = []
    for _ in range(tries):
        if len(variants) >= k:
            break
        point = {syms[v.name]: _sample_value(v.domain, rng) for v in obj.vars}
        if any(_holds(c, point) is not True for c in cons):
            continue
        if any(_holds(iq, point) is not True for iq in ineqs):
            continue
        new_givens: list[str] = []
        changed = []
        for r in rels:
            if isinstance(r, sp.Equality):
                side, num = (r.lhs, r.rhs) if r.rhs.is_number else (r.rhs, r.lhs)
                if not side.free_symbols:
                    new_givens.append(f"{sp.sstr(side)} = {sp.sstr(num)}")
                    continue
                val = sp.simplify(side.subs(point))
                new_givens.append(f"{sp.sstr(side)} = {sp.sstr(val)}")
                changed.append((sp.sstr(num), sp.sstr(val)))
            else:
                new_givens.append(sp.sstr(r))
        if not changed or all(a == b for a, b in changed):
            continue
        # uniqueness of the perturbed instance
        try:
            new_eqs = [parse_relation(g, ns) for g in new_givens if "=" in g and not any(op in g for op in ("<", ">", "!="))]
            sols = sp.solve(new_eqs, list(syms.values()), dict=True)
        except Exception:
            continue
        good = []
        for s_ in sols:
            if any(v.free_symbols for v in s_.values()):
                good = None
                break
            full = dict(point)
            full.update(s_)
            if all(_holds(c, s_) is not False for c in cons) and all(_holds(iq, s_) is not False for iq in ineqs):
                good.append(s_)
        if good is None or len(good) != 1:
            continue
        expected = sp.simplify(target.subs(point))
        ir2 = json.loads(json.dumps(ir))
        ir2["givens"] = new_givens
        ir2["options"] = None
        variants.append({"ir": ir2, "expected": sp.sstr(expected), "values": {s.name: sp.sstr(v) for s, v in point.items()},
                         "changed": changed})
    return variants


def _method_text(solution: dict[str, Any]) -> str:
    lines = []
    for st in solution.get("steps", []):
        claim = st.get("claim") or ""
        txt = st.get("text") or ""
        lines.append(f"{st.get('id')}: [{st.get('kind')}] {claim} {('— ' + txt) if txt else ''}".strip())
    return "\n".join(lines) if lines else "(no steps given; the final answer was " + str(solution["claimed_answer"].get("payload")) + ")"


def metamorphic_check(question_tr: str, ir: dict[str, Any], solution: dict[str, Any], solver_family: str | None,
                      *, k: int = 3, seed: int = 0, effort: str = "high") -> dict[str, Any]:
    from ..resolve.cross_family import solve_with_family
    out: dict[str, Any] = {"applicable": False, "variants": [], "n": 0, "failed": 0, "passed": 0,
                           "undecided": 0, "calls": 0, "cost_usd": 0.0}
    variants = perturb_ir(ir, seed=seed, k=k)
    if not variants:
        out["reason"] = "not_applicable"
        return out
    out["applicable"] = True
    family = solver_family or "anthropic"
    method = _method_text(solution)
    try:
        ns = build_namespace(load_problem_ir(ir))
    except Exception:
        out["reason"] = "ir_namespace_error"
        return out
    for var in variants:
        givens_txt = "; ".join(var["ir"]["givens"])
        q = (f"{question_tr.strip()}\n\n## Modified instance\nSolve the SAME problem with these data instead "
             f"(all other conditions unchanged, no options — give the value): {givens_txt}")
        hint = ("Reproduce exactly the method of this earlier solution of the original instance, step by step, "
                "with the new numbers (do not switch to a different method):\n" + method)
        r = solve_with_family(q, None, var["ir"], family, effort=effort, method_hint=hint, verify_against_ir=False,
                              tag="metamorphic")
        out["calls"] += r.get("calls", 0)
        out["cost_usd"] += r.get("cost_usd", 0.0)
        rec: dict[str, Any] = {"changed": var["changed"], "expected": var["expected"], "got": None, "ok": None}
        sol = r.get("solution")
        if sol:
            ca = sol["claimed_answer"]
            rec["got"] = ca.get("payload")
            try:
                got = parse_answer(ca["kind"], ca["payload"], ns)
                exp = parse_expr_str(var["expected"], ns)
                ok, _ = answers_equivalent(got, exp, shape="scalar")
                rec["ok"] = ok
            except Exception as e:  # noqa: BLE001
                rec["error"] = str(e)[:100]
        else:
            rec["error"] = "; ".join(r.get("errors") or ["no solution"])
        out["variants"].append(rec)
        if rec["ok"] is True:
            out["passed"] += 1
        elif rec["ok"] is False:
            out["failed"] += 1
        else:
            out["undecided"] += 1
    out["n"] = len(variants)
    return out


def l5_layer(meta: dict[str, Any]):
    with Timer() as t:
        ev = {k: v for k, v in meta.items() if k != "variants"}
        ev["variants"] = meta.get("variants")
    if not meta.get("applicable"):
        return unknown(LAYER, meta.get("reason", "not_applicable"), t.ms, ev)
    if meta["failed"] >= 2 or (meta["n"] == 1 and meta["failed"] == 1):
        return result(LAYER, "unknown", 0.0, False, dict(ev, reason="method_fails_on_perturbed_instances"), t.ms,
                      flags=["l5_method_failed"])
    if meta["passed"] >= 2 and meta["failed"] == 0:
        return result(LAYER, "unknown", 0.0, False, dict(ev, reason="method_holds_on_perturbed_instances"), t.ms,
                      flags=["l5_method_ok"])
    return unknown(LAYER, "inconclusive", t.ms, ev, flags=["l5_inconclusive"])
