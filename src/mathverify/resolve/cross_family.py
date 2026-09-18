"""Cross-family solving and the L4 signal.

solve_with_family(question, options, ir, family)  — the app's own solver (path a) or the L4
re-solver: the model solves from the NATURAL-LANGUAGE question (not from the IR, so it is an
independent path), using the IR's symbol names so its steps are machine-checkable; the
result is verified deterministically against the IR.

l4_layer(...) — compares the claimed answer with the re-solver's answer:
  l4_agree                 same answer                      -> no change (never CORRECT by itself)
  l4_disagree_certified    different answer AND the re-solver's answer was certified CORRECT
                           against the IR -> two certified answers for one IR -> IR does not
                           pin the problem -> blocks CORRECT (UNKNOWN)
  l4_disagree_uncertified  different answer, re-solver not certified -> small penalty
  l4_undecided             answers could not be compared
"""
from __future__ import annotations

import json
import time
from typing import Any

import sympy as sp

from ..certify.base import Timer, result, unknown, make_ctx
from ..equiv import answers_equivalent
from ..intake.structured import load_problem_ir, load_solution, SchemaError
from ..llm import get_client, other_family, LLMError
from ..llm.schemas import SOLUTION_SCHEMA, solution_from_llm
from ..normalize.parse import build_namespace, parse_answer, parse_relation
from ..extract.prompts import SOLVER_SYSTEM

__all__ = ["solve_with_family", "cross_family_resolve", "l4_layer"]

LAYER = "resolve.cross_family"


def _solver_user_prompt(question_tr: str, options: dict[str, str] | None, ir: dict[str, Any] | None,
                        method_hint: str | None = None) -> str:
    q = question_tr.strip()
    if options:
        q += "\n" + "  ".join(f"{k}) {v}" for k, v in options.items())
    parts = [f"## Question (Turkish)\n{q}"]
    if ir:
        names = [v["name"] for v in ir.get("vars") or []]
        funcs = [f"{f['name']}({', '.join(f.get('args') or ['x'])})" for f in ir.get("functions") or []]
        hints = []
        if names:
            hints.append("unknown symbols to use: " + ", ".join(names))
        if funcs:
            hints.append("function symbols available: " + ", ".join(funcs))
        pts = (ir.get("task", {}).get("params") or {}).get("points")
        if pts:
            hints.append("point names: " + ", ".join(pts))
        shape = ir.get("answer_shape")
        if shape:
            hints.append(f"answer shape expected: {shape}")
        if hints:
            parts.append("## Notation\n" + "\n".join(hints))
    if method_hint:
        parts.append("## Method to follow\n" + method_hint)
    parts.append("## Structured solution (JSON)")
    return "\n\n".join(parts)


def _sanitize(sol: dict[str, Any], ns) -> list[str]:
    notes = []
    for st in sol.get("steps", []):
        if st.get("kind") in ("eq", "compute") and st.get("claim"):
            try:
                parse_relation(st["claim"], ns)
            except Exception as e:  # noqa: BLE001
                notes.append(f"{st['id']}: {str(e)[:60]}")
                st["text"] = (st.get("text") or "") + f" [claim: {st['claim']}]"
                st["claim"] = ""
                st["kind"] = "note"
    return notes


def solve_with_family(question_tr: str, options: dict[str, str] | None, ir: dict[str, Any] | None, family: str, *,
                      effort: str = "xhigh", method_hint: str | None = None, verify_against_ir: bool = True,
                      tag: str = "solve") -> dict[str, Any]:
    """Ask `family` to solve; optionally verify its solution deterministically against `ir`."""
    t0 = time.perf_counter()
    out: dict[str, Any] = {"family": family, "model": None, "solution": None, "verdict": None, "confidence": None,
                           "calls": 0, "cost_usd": 0.0, "errors": [], "downgraded_steps": []}
    client = get_client(family)
    try:
        r = client.complete(SOLVER_SYSTEM, _solver_user_prompt(question_tr, options, ir, method_hint),
                            schema=SOLUTION_SCHEMA, effort=effort, max_tokens=16000, tag=tag)
    except LLMError as e:
        out["errors"].append(f"llm: {str(e)[:160]}")
        return out
    out["calls"] = 1
    out["cost_usd"] = r.cost_usd
    out["model"] = r.model
    out["stop_reason"] = r.stop_reason
    if r.parsed is None:
        out["errors"].append("no_json")
        return out
    try:
        sol = solution_from_llm(r.parsed)
        load_solution(sol)
    except (SchemaError, KeyError, ValueError, TypeError) as e:
        out["errors"].append(f"schema: {str(e)[:120]}")
        return out
    out["solution"] = sol
    if ir is not None and verify_against_ir:
        try:
            ns = build_namespace(load_problem_ir(ir))
            out["downgraded_steps"] = _sanitize(sol, ns)
            from ..verifier import verify
            v = verify(ir, sol)
            out["verdict"], out["confidence"], out["flags"] = v.verdict, v.confidence, v.flags
            out["trace"] = v.decision_trace
            out["first_bad_step"] = v.first_bad_step
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"verify: {type(e).__name__}: {str(e)[:120]}")
    out["latency_ms"] = (time.perf_counter() - t0) * 1000
    return out


def cross_family_resolve(question_tr: str, options: dict[str, str] | None, ir: dict[str, Any],
                         solver_family: str | None, *, effort: str = "xhigh") -> dict[str, Any]:
    family = other_family(solver_family) if solver_family else "anthropic"
    return solve_with_family(question_tr, options, ir, family, effort=effort, tag="resolve")


def l4_layer(ir: dict[str, Any], original_solution: dict[str, Any], resolve: dict[str, Any],
             original_verdict: str | None = None):
    """Turn a cross_family_resolve result into a soft LayerResult.

    `original_verdict` is the deterministic verdict on the claimed solution (before L4): when
    the claim was already REFUTED, a disagreeing certified re-solve simply confirms the
    refutation (`l4_confirms_refutation`); only a CORRECT/UNKNOWN claim facing a different
    *certified* answer is the 'two certified answers for one IR' anomaly."""
    with Timer() as t:
        ev: dict[str, Any] = {"family": resolve.get("family"), "model": resolve.get("model"),
                              "resolver_verdict": resolve.get("verdict"), "resolver_confidence": resolve.get("confidence"),
                              "errors": resolve.get("errors")}
        sol = resolve.get("solution")
        if not sol:
            return unknown(LAYER, "resolver_unavailable", t.ms, ev, flags=["l4_undecided"])
        ev["resolver_answer"] = sol["claimed_answer"]
        ev["claimed_answer"] = original_solution["claimed_answer"]
        try:
            ir_obj = load_problem_ir(ir)
            ns = build_namespace(ir_obj)
            a_ = original_solution["claimed_answer"]
            b_ = sol["claimed_answer"]
            if a_["kind"] == "dne" or b_["kind"] == "dne":
                agree = (a_["kind"] == b_["kind"])
            elif a_.get("option") and b_.get("option") and ir_obj.options:
                agree = a_["option"] == b_["option"]
            else:
                a = parse_answer(a_["kind"], a_["payload"], ns)
                b = parse_answer(b_["kind"], b_["payload"], ns)
                shape = "set" if isinstance(a, sp.Set) or isinstance(b, sp.Set) else \
                    ("count" if a_["kind"] == "count" else ("equation" if a_["kind"] == "equation" else "scalar"))
                var = ns.get((ir_obj.task.params or {}).get("var", "x"))
                agree, cev = answers_equivalent(a, b, shape=shape, var=var if isinstance(var, sp.Symbol) else None)
                ev["compare"] = cev
        except Exception as e:  # noqa: BLE001
            ev["compare_error"] = f"{type(e).__name__}: {str(e)[:120]}"
            agree = None
        ev["agree"] = agree
    if agree is True:
        return result(LAYER, "unknown", 0.0, False, dict(ev, reason="l4_agree"), t.ms, flags=["l4_agree"])
    if agree is False:
        if original_verdict == "INCORRECT":
            return result(LAYER, "unknown", 0.0, False, dict(ev, reason="resolver_disagrees_with_refuted_claim"), t.ms,
                          flags=["l4_confirms_refutation"])
        if resolve.get("verdict") == "CORRECT":
            return result(LAYER, "unknown", 0.0, False, dict(ev, reason="two_certified_answers_for_one_ir"), t.ms,
                          flags=["l4_disagree_certified"])
        return result(LAYER, "unknown", 0.0, False, dict(ev, reason="resolver_disagrees_uncertified"), t.ms,
                      flags=["l4_disagree_uncertified"])
    return unknown(LAYER, "answers_not_comparable", t.ms, ev, flags=["l4_undecided"])
