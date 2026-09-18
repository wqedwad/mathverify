"""Path (b) with an LLM (D1): free-text solution -> structured Solution using the IR's symbols.

Fidelity guards (handoff D1: "sessiz anlam kaybı burada olur"):
  * the restructurer must transcribe, never repair (prompt), and the result is validated
    deterministically (schema + every claim parses in the IR namespace, else the step is
    downgraded to a note so nothing is silently dropped);
  * the LLM's claimed answer is cross-checked against the deterministic final-answer
    extractor; a disagreement is flagged (`restructure_answer_mismatch`) and blocks CORRECT.
"""
from __future__ import annotations

import json
import time
from typing import Any

from ..equiv import answers_equivalent
from ..intake.restructure import extract_final_answer
from ..intake.structured import load_problem_ir, load_solution, SchemaError
from ..llm import get_client, LLMError
from ..llm.schemas import SOLUTION_SCHEMA, solution_from_llm
from ..normalize.parse import build_namespace, parse_answer, parse_relation, ParseError
from .prompts import RESTRUCTURE_SYSTEM
from .roundtrip import render_ir

__all__ = ["restructure_solution"]


def _sanitize_steps(sol: dict[str, Any], ns) -> tuple[dict[str, Any], list[str]]:
    """Downgrade unparseable eq/compute claims to notes (never drop them); report what changed."""
    notes = []
    for st in sol.get("steps", []):
        if st.get("kind") in ("eq", "compute") and st.get("claim"):
            try:
                parse_relation(st["claim"], ns)
            except Exception as e:  # noqa: BLE001
                notes.append(f"{st['id']}: claim {st['claim']!r} unparseable -> note ({str(e)[:60]})")
                st["text"] = (st.get("text") or "") + f" [claim: {st['claim']}]"
                st["claim"] = ""
                st["kind"] = "note"
    return sol, notes


def restructure_solution(ir: dict[str, Any], solution_text: str, *, family: str = "anthropic", client=None,
                         effort: str = "high", max_repairs: int = 1) -> dict[str, Any]:
    t0 = time.perf_counter()
    out: dict[str, Any] = {"solution": None, "calls": 0, "cost_usd": 0.0, "errors": [], "flags": [],
                           "deterministic_answer": None, "answers_agree": None, "downgraded_steps": []}
    client = client or get_client(family)
    try:
        ir_obj = load_problem_ir(ir)
        ns = build_namespace(ir_obj)
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"ir: {e}")
        return out
    det = extract_final_answer(solution_text, answer_shape=ir_obj.answer_shape)
    out["deterministic_answer"] = det.__dict__ if det else None
    user = (f"## Problem IR (rendered)\n{render_ir(ir)}\n\n## Problem IR (JSON)\n{json.dumps(ir, ensure_ascii=False)}\n\n"
            f"## Solution text to transcribe\n{solution_text.strip()}\n\n## Structured solution (JSON)")
    feedback = None
    for rnd in range(max_repairs + 1):
        u = user if not feedback else user + f"\n\nThe previous transcription had problems: {feedback}. Fix them without changing the mathematics."
        try:
            r = client.complete(RESTRUCTURE_SYSTEM, u, schema=SOLUTION_SCHEMA, effort=effort, max_tokens=12000,
                                tag="restructure")
        except LLMError as e:
            out["errors"].append(f"llm: {str(e)[:160]}")
            break
        out["calls"] += 1
        out["cost_usd"] += r.cost_usd
        if r.parsed is None:
            feedback = "reply was not valid JSON"
            out["errors"].append("no_json")
            continue
        try:
            sol = solution_from_llm(r.parsed)
            sol["source"] = "restructured"
            load_solution(sol)
        except (SchemaError, KeyError, ValueError, TypeError) as e:
            feedback = f"schema: {e}"
            out["errors"].append(f"schema: {str(e)[:120]}")
            continue
        ca = sol["claimed_answer"]
        try:
            if ca["kind"] not in ("dne", "none"):
                parse_answer(ca["kind"], ca["payload"], ns)
        except Exception as e:  # noqa: BLE001
            feedback = f"claimed_answer payload {ca['payload']!r} does not parse: {str(e)[:100]}"
            out["errors"].append(feedback)
            continue
        sol, downgraded = _sanitize_steps(sol, ns)
        out["downgraded_steps"] = downgraded
        out["solution"] = sol
        break
    # cross-check with the deterministic extractor
    if out["solution"] and det is not None:
        ca = out["solution"]["claimed_answer"]
        try:
            if det.kind == "dne" or ca["kind"] == "dne":
                agree = (det.kind == ca["kind"])
            elif det.option and ca.get("option"):
                agree = det.option == ca["option"]
            elif det.payload is not None and ca["payload"] is not None:
                a = parse_answer(det.kind, det.payload, ns)
                b = parse_answer(ca["kind"], ca["payload"], ns)
                import sympy as sp
                shape = "set" if isinstance(a, sp.Set) or isinstance(b, sp.Set) else ("count" if ca["kind"] == "count" else "scalar")
                agree, _ = answers_equivalent(a, b, shape=shape)
            else:
                agree = None
        except Exception:  # noqa: BLE001
            agree = None
        out["answers_agree"] = agree
        if agree is False:
            out["flags"].append("restructure_answer_mismatch")
    out["latency_ms"] = (time.perf_counter() - t0) * 1000
    return out
