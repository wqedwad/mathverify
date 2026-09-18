"""Critic, meta-verifier and the L6 soft layer."""
from __future__ import annotations

import json
import time
from typing import Any

import sympy as sp

from ..certify.base import Timer, result, unknown, make_ctx
from ..certify.domain import relation_holds_at
from ..intake.structured import load_problem_ir, load_solution
from ..llm import get_client, other_family, LLMError
from ..llm.schemas import _obj, _s, _arr
from ..normalize.parse import build_namespace, parse_relation
from ..extract.prompts import CRITIC_SYSTEM, META_SYSTEM
from ..extract.roundtrip import render_ir

__all__ = ["critique_solution", "meta_verify", "l6_critic_layer", "CRITIC_SCHEMA", "META_SCHEMA"]

LAYER = "critic.steps"

CRITIC_SCHEMA = _obj({
    "assessment": {"type": "string", "enum": ["all_steps_valid", "error_found", "cannot_judge"]},
    "first_bad_step": _s("step id of the first invalid step, '' if none"),
    "error_kind": _s(), "explanation": _s(),
    "counter_check": _s("one TRUE canonical relation exposing the error, '' if none"),
    "answer_correct_regardless": {"type": "boolean"},
    "confidence": {"type": "integer", "description": "0-10"},
})

META_SCHEMA = _obj({
    "error_is_real": {"type": "boolean"},
    "confidence": {"type": "integer", "description": "0-10"},
    "explanation": _s(),
    "corrected_step": _s("'' or the relation the step should have stated"),
})


def _steps_text(solution: dict[str, Any]) -> str:
    lines = []
    for st in solution.get("steps", []):
        frm = ",".join(st.get("from") or []) or "-"
        lines.append(f"{st['id']} [{st.get('kind')}] (from: {frm}) {st.get('claim') or ''}"
                     + (f"  — {st['text']}" if st.get("text") else ""))
    ca = solution["claimed_answer"]
    lines.append(f"FINAL: kind={ca['kind']} payload={ca.get('payload')} option={ca.get('option')}")
    return "\n".join(lines)


def _problem_text(question_tr: str, options: dict[str, str] | None, ir: dict[str, Any]) -> str:
    q = question_tr.strip()
    if options:
        q += "\n" + "  ".join(f"{k}) {v}" for k, v in options.items())
    return f"## Question (Turkish)\n{q}\n\n## Formal problem (IR, rendered)\n{render_ir(ir)}"


def critique_solution(question_tr: str, options: dict[str, str] | None, ir: dict[str, Any],
                      solution: dict[str, Any], solver_family: str | None, *, effort: str = "xhigh") -> dict[str, Any]:
    family = other_family(solver_family) if solver_family else "anthropic"
    out: dict[str, Any] = {"family": family, "model": None, "calls": 0, "cost_usd": 0.0, "report": None, "errors": []}
    user = (_problem_text(question_tr, options, ir) + "\n\n## Solution steps\n" + _steps_text(solution)
            + "\n\nReview the steps. Reply in JSON.")
    try:
        r = get_client(family).complete(CRITIC_SYSTEM, user, schema=CRITIC_SCHEMA, effort=effort, max_tokens=8000,
                                        tag="critic")
    except LLMError as e:
        out["errors"].append(f"llm: {str(e)[:160]}")
        return out
    out["calls"], out["cost_usd"], out["model"] = 1, r.cost_usd, r.model
    if not isinstance(r.parsed, dict):
        out["errors"].append("no_json")
        return out
    out["report"] = r.parsed
    return out


def meta_verify(question_tr: str, options: dict[str, str] | None, ir: dict[str, Any], solution: dict[str, Any],
                report: dict[str, Any], critic_family: str, *, effort: str = "xhigh") -> dict[str, Any]:
    family = other_family(critic_family)
    out: dict[str, Any] = {"family": family, "model": None, "calls": 0, "cost_usd": 0.0, "verdict": None, "errors": []}
    user = (_problem_text(question_tr, options, ir) + "\n\n## Solution steps\n" + _steps_text(solution)
            + "\n\n## Reviewer's error report\n" + json.dumps(report, ensure_ascii=False)
            + "\n\nIs the reported error real? Reply in JSON.")
    try:
        r = get_client(family).complete(META_SYSTEM, user, schema=META_SCHEMA, effort=effort, max_tokens=6000,
                                        tag="meta_verify")
    except LLMError as e:
        out["errors"].append(f"llm: {str(e)[:160]}")
        return out
    out["calls"], out["cost_usd"], out["model"] = 1, r.cost_usd, r.model
    if isinstance(r.parsed, dict):
        out["verdict"] = r.parsed
    else:
        out["errors"].append("no_json")
    return out


def _deterministic_cross_check(ir: dict[str, Any], solution: dict[str, Any], report: dict[str, Any],
                               step_layer_evidence: dict[str, Any] | None) -> dict[str, Any]:
    """(1) Was the flagged step already deterministically VERIFIED? (2) Does the counter-check hold?"""
    out: dict[str, Any] = {"flagged_step_status": None, "counter_check": None, "counter_check_holds": None}
    sid = (report.get("first_bad_step") or "").strip()
    if step_layer_evidence:
        for st in step_layer_evidence.get("steps", []):
            if st.get("id") == sid:
                out["flagged_step_status"] = st.get("status")
    cc = (report.get("counter_check") or "").strip()
    if cc:
        out["counter_check"] = cc
        try:
            ns = build_namespace(load_problem_ir(ir))
            rel = parse_relation(cc, ns)
            if rel is sp.true:
                out["counter_check_holds"] = True
            elif rel is sp.false:
                out["counter_check_holds"] = False
            elif isinstance(rel, sp.core.relational.Relational) and not rel.free_symbols:
                out["counter_check_holds"] = relation_holds_at(rel, sp.Symbol("_d"), 0)
            else:
                out["counter_check_holds"] = None          # has free symbols: not decidable as a fact
        except Exception as e:  # noqa: BLE001
            out["counter_check_error"] = f"{type(e).__name__}: {str(e)[:100]}"
    return out


def l6_critic_layer(question_tr: str, options: dict[str, str] | None, ir: dict[str, Any], solution: dict[str, Any],
                    solver_family: str | None, step_layer_evidence: dict[str, Any] | None = None,
                    original_verdict: str | None = None, *, effort: str = "xhigh"):
    """Run critic -> deterministic cross-check -> meta-verification and return a soft LayerResult
    plus the raw records (for cost accounting)."""
    with Timer() as t:
        crit = critique_solution(question_tr, options, ir, solution, solver_family, effort=effort)
        ev: dict[str, Any] = {"critic": {k: v for k, v in crit.items() if k != "report"}, "report": crit.get("report")}
        cost, calls = crit["cost_usd"], crit["calls"]
        rep = crit.get("report")
        if not rep:
            lr = unknown(LAYER, "critic_unavailable", t.ms, ev, flags=["critic_unavailable"])
            return lr, {"cost_usd": cost, "calls": calls, "critic": crit, "meta": None}
        if rep.get("assessment") != "error_found" or not (rep.get("first_bad_step") or "").strip():
            lr = result(LAYER, "unknown", 0.0, False, dict(ev, reason="critic_found_no_error"), t.ms,
                        flags=["critic_clean" if rep.get("assessment") == "all_steps_valid" else "critic_cannot_judge"])
            return lr, {"cost_usd": cost, "calls": calls, "critic": crit, "meta": None}
        sid = rep["first_bad_step"].strip()
        idx = next((i + 1 for i, st in enumerate(solution.get("steps", [])) if st["id"] == sid), None)
        ev["flagged_index"] = idx
        xc = _deterministic_cross_check(ir, solution, rep, step_layer_evidence)
        ev["cross_check"] = xc
        if xc["flagged_step_status"] == "verified":
            lr = result(LAYER, "unknown", 0.0, False, dict(ev, reason="critic_contradicts_deterministic_verification"),
                        t.ms, flags=["critic_overruled_by_certificate"])
            return lr, {"cost_usd": cost, "calls": calls, "critic": crit, "meta": None}
        if xc["counter_check_holds"] is False:
            lr = result(LAYER, "unknown", 0.0, False, dict(ev, reason="critic_counter_check_is_false"), t.ms,
                        flags=["critic_overruled_by_certificate"])
            return lr, {"cost_usd": cost, "calls": calls, "critic": crit, "meta": None}
        meta = meta_verify(question_tr, options, ir, solution, rep, crit["family"], effort=effort)
        cost += meta["cost_usd"]
        calls += meta["calls"]
        ev["meta"] = {k: v for k, v in meta.items()}
        mv = meta.get("verdict") or {}
        confirmed = bool(mv.get("error_is_real")) and int(mv.get("confidence") or 0) >= 6
        if original_verdict == "INCORRECT":
            flag = "critic_agrees_with_refutation"
        elif confirmed:
            flag = "critic_error_confirmed"
        else:
            flag = "critic_error_unconfirmed"
        lr = result(LAYER, "unknown", 0.0, False, dict(ev, reason=flag), t.ms, primary=False,
                    first_bad_step=idx if confirmed else None, flags=[flag])
    return lr, {"cost_usd": cost, "calls": calls, "critic": crit, "meta": meta}
