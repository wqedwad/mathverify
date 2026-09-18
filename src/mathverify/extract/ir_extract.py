"""NL -> IR extraction with deterministic validation, two-family round-trip audit and a
bounded repair loop (handoff §5, [17] roundtrip verification and repair).

extract_ir(question, options) ->
  1. extractor (anthropic family) produces an IR in the strict output format
  2. deterministic validation: schema, every expression parses in the IR namespace,
     options parse in the declared answer shape, task-kind normalisation
  3. round-trip: the IR is rendered back to natural language and audited by BOTH families;
     both must give >= 9/10 (handoff §5) — otherwise the findings are fed back to the
     extractor (at most `max_repairs` rounds)
  4. result: accepted IR or None with the full audit trail; nothing here ever guesses.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from ..intake.structured import load_problem_ir, SchemaError
from ..ir import LeakageError
from ..llm import get_client, LLMError
from ..llm.schemas import IR_SCHEMA, ir_from_llm
from ..normalize.parse import build_namespace, parse_relation, parse_expr_str, parse_answer
from .prompts import exemplar_block, extraction_user_prompt, extraction_system_blocks
from .roundtrip import judge_roundtrip

__all__ = ["extract_ir", "validate_ir", "normalize_task", "ExtractResult"]

ROUNDTRIP_THRESHOLD = 9


@dataclass
class ExtractResult:
    ir: dict[str, Any] | None
    accepted: bool
    rounds: list[dict[str, Any]] = field(default_factory=list)
    cost_usd: float = 0.0
    calls: int = 0
    latency_ms: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ir": self.ir, "accepted": self.accepted, "rounds": self.rounds, "cost_usd": round(self.cost_usd, 4),
                "calls": self.calls, "latency_ms": round(self.latency_ms), "reason": self.reason}


# ---------------------------------------------------------------------------- validation
_EXPR_PARAMS = ("expr", "equation", "inequality", "integrand", "f", "term", "matrix", "A", "b", "a", "to", "at",
                "radius", "slope", "line", "lo", "hi", "eigenvalue", "target")


def normalize_task(ir: dict[str, Any]) -> dict[str, Any]:
    """Deterministic task-kind normalisation for common extractor choices."""
    ir = json.loads(json.dumps(ir))
    task = ir["task"]
    kind, p = task["kind"], task.get("params", {})
    givens = ir.get("givens") or []
    # alias keys some extractors invent for the unknown of a system
    for alias in ("solve_for", "unknown", "target_var"):
        if alias in p and "var" not in p and isinstance(p[alias], str):
            p["var"] = p.pop(alias)
    for alias in ("system", "equations"):
        if alias in p and isinstance(p[alias], list):
            for eq in p.pop(alias):
                if eq not in givens:
                    givens.append(eq)
            ir["givens"] = givens
    if kind == "solve_equation" and len(givens) > 1 and ir.get("answer_shape", "scalar") in ("scalar",):
        task["kind"] = "evaluate"
        p.pop("equation", None)
        p["expr"] = p.get("var") or (ir.get("unknown_of_interest") or "")
        ir["unknown_of_interest"] = p["expr"]
    if kind == "evaluate" and not p.get("expr") and ir.get("unknown_of_interest"):
        p["expr"] = ir["unknown_of_interest"]
    if kind == "trig_solve" and p.get("equation") and not givens:
        ir["givens"] = [p["equation"]]
    if kind == "solve_inequality" and p.get("inequality") and not givens:
        ir["givens"] = [p["inequality"]]
    return ir


def validate_ir(ir: dict[str, Any]) -> list[str]:
    """Return a list of deterministic problems ([] = valid)."""
    errors: list[str] = []
    try:
        obj = load_problem_ir(ir, strict_kind=True)
    except (SchemaError, LeakageError, ValueError, TypeError) as e:
        return [f"schema: {e}"]
    try:
        ns = build_namespace(obj)
    except Exception as e:  # noqa: BLE001
        return [f"namespace: {type(e).__name__}: {e}"]
    for g in obj.givens:
        try:
            parse_relation(g, ns)
        except Exception as e:  # noqa: BLE001
            errors.append(f"given {g!r} does not parse: {str(e)[:120]}")
    for v in obj.vars:
        for c in v.constraints:
            try:
                parse_relation(c, ns)
            except Exception as e:  # noqa: BLE001
                errors.append(f"constraint {c!r} does not parse: {str(e)[:120]}")
    p = obj.task.params
    for key in _EXPR_PARAMS:
        if key in p and isinstance(p[key], str) and p[key] and obj.task.kind != "synthetic_geometry":
            try:
                parse_relation(p[key], ns) if key in ("equation", "inequality", "line") else parse_expr_str(p[key], ns)
            except Exception as e:  # noqa: BLE001
                errors.append(f"param {key}={p[key]!r} does not parse: {str(e)[:120]}")
    if obj.task.kind == "synthetic_geometry":
        for req in ("points", "constraints", "target"):
            if req not in p:
                errors.append(f"synthetic_geometry needs param {req}")
    if obj.task.kind in ("probability", "count_structures") and not isinstance(p.get("space"), dict):
        errors.append("probability/count_structures need a JSON `space` object")
    if obj.task.kind == "evaluate" and not (p.get("expr") or obj.unknown_of_interest):
        errors.append("evaluate needs params.expr")
    if obj.task.kind == "limit" and not (p.get("expr") and p.get("to")):
        errors.append("limit needs params.expr and params.to")
    if obj.options:
        shape = obj.answer_shape
        kind = "count" if shape == "count" else ("set" if shape in ("set", "interval") else
                                                  "equation" if shape == "equation" else "value")
        for letter, val in obj.options.items():
            if shape == "dne_or_scalar" and any(w in str(val).lower() for w in ("yok", "dne", "tanımsız")):
                continue
            try:
                if kind == "count":
                    int(parse_expr_str(str(val), ns))
                else:
                    parse_answer(kind, str(val), ns)
            except Exception as e:  # noqa: BLE001
                errors.append(f"option {letter}={val!r} does not parse as {shape}: {str(e)[:100]}")
    return errors


# ---------------------------------------------------------------------------- extraction
def extract_ir(question_tr: str, options: dict[str, str] | None = None, level_hint: str | None = None, *,
               client=None, exemplar_ids: list[str] | None = None, exclude_ids: list[str] | None = None,
               max_repairs: int = 2, effort: str = "max", judge_families: tuple[str, ...] = ("anthropic", "meta"),
               roundtrip: bool = True) -> ExtractResult:
    t0 = time.perf_counter()
    client = client or get_client("anthropic")
    ids = list(exemplar_ids) if exemplar_ids else None
    if exclude_ids:
        from .prompts import EXEMPLAR_IDS
        ids = [i for i in (ids or EXEMPLAR_IDS) if i not in set(exclude_ids)]
    exemplars = exemplar_block(ids)
    system = extraction_system_blocks(exemplars)      # cacheable stable prefix
    res = ExtractResult(ir=None, accepted=False)
    feedback: str | None = None
    prev_ir: dict | None = None
    for rnd in range(max_repairs + 1):
        user = extraction_user_prompt(question_tr, options, level_hint, "", feedback, prev_ir)
        round_rec: dict[str, Any] = {"round": rnd}
        try:
            r = client.complete(system, user, schema=IR_SCHEMA, effort=effort, max_tokens=20000,
                                tag="ir_extract")
        except LLMError as e:
            round_rec["error"] = f"llm: {e}"
            res.rounds.append(round_rec)
            res.reason = f"llm_error: {str(e)[:120]}"
            break
        res.calls += 1
        res.cost_usd += r.cost_usd
        round_rec.update({"stop": r.stop_reason, "cached": r.cached, "cost_usd": round(r.cost_usd, 4)})
        if r.stop_reason == "refusal" or r.parsed is None:
            round_rec["error"] = "no_json" if r.stop_reason != "refusal" else "refusal"
            res.rounds.append(round_rec)
            feedback = "The previous reply was not valid JSON matching the schema."
            continue
        try:
            ir = normalize_task(ir_from_llm(r.parsed))
        except Exception as e:  # noqa: BLE001
            round_rec["error"] = f"convert: {type(e).__name__}: {e}"
            res.rounds.append(round_rec)
            feedback = f"The previous IR could not be converted: {e}"
            continue
        round_rec["assumptions"] = r.parsed.get("assumptions")
        round_rec["confidence"] = r.parsed.get("confidence")
        errors = validate_ir(ir)
        round_rec["validation_errors"] = errors
        if errors:
            res.rounds.append(round_rec)
            feedback = "Deterministic validation failed: " + "; ".join(errors)
            prev_ir = ir
            continue
        if not roundtrip:
            res.rounds.append(round_rec)
            res.ir, res.accepted, res.reason = ir, True, "validated_no_roundtrip"
            break
        audit = judge_roundtrip(question_tr, options, ir, families=judge_families)
        res.calls += audit["calls"]
        res.cost_usd += audit["cost_usd"]
        round_rec["roundtrip"] = {k: v for k, v in audit.items() if k != "calls"}
        res.rounds.append(round_rec)
        if audit["passed"]:
            res.ir, res.accepted, res.reason = ir, True, "roundtrip_passed"
            break
        disc = []
        for fam, j in audit["judges"].items():
            if j.get("score") is not None and j["score"] < ROUNDTRIP_THRESHOLD:
                disc += [f"[{fam}] {d}" for d in j.get("discrepancies", [])] or [f"[{fam}] score {j['score']}"]
        feedback = "Round-trip audit found: " + "; ".join(disc)
        prev_ir = ir
        res.ir = ir                   # keep the last candidate for diagnostics; not accepted
    if not res.accepted and not res.reason:
        res.reason = "roundtrip_failed" if res.rounds and "roundtrip" in res.rounds[-1] else \
            ("validation_failed" if res.rounds and res.rounds[-1].get("validation_errors") else "extraction_failed")
    res.latency_ms = (time.perf_counter() - t0) * 1000
    return res
