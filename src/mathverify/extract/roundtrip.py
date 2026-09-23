"""IR round-trip audit (handoff §5): render the IR back to plain language deterministically
and have BOTH model families compare it with the original question. Both must score >= 9.
Measured in [5]: consensus-positive formalisations are 96% human-faithful."""
from __future__ import annotations

import json
from typing import Any

from ..llm import get_client, LLMError
from ..llm.schemas import JUDGE_SCHEMA
from .prompts import JUDGE_SYSTEM

__all__ = ["render_ir", "judge_roundtrip"]

_DOMAIN_WORDS = {"real": "real number", "positive_real": "positive real number", "nonneg_real": "non-negative real number",
                 "integer": "integer", "positive_integer": "positive integer", "nonneg_integer": "non-negative integer",
                 "natural": "natural number (>= 1)", "rational": "rational number", "complex": "complex number"}


def _task_sentence(kind: str, p: dict[str, Any], ir: dict[str, Any]) -> str:
    g0 = (ir.get("givens") or [""])[0]
    if kind == "evaluate":
        return f"Find the value of: {p.get('expr') or ir.get('unknown_of_interest')}"
    if kind == "solve_equation":
        return f"Find all {p.get('var', 'x')} satisfying the equation {p.get('equation') or g0} (solution set asked)"
    if kind == "solve_inequality":
        return f"Find all {p.get('var', 'x')} satisfying the inequality {p.get('inequality') or ' and '.join(ir.get('givens') or [])}"
    if kind == "count_integers":
        return f"Count the integers {p.get('var', 'x')} satisfying: {' and '.join(ir.get('givens') or [])}"
    if kind == "count_roots":
        return f"Count the {'distinct ' if p.get('distinct', True) else ''}real roots of {p.get('expr')} in {p.get('var', 'x')}"
    if kind == "domain_of":
        return f"Find the (real) domain of {p.get('expr')} as a function of {p.get('var', 'x')}"
    if kind == "simplify_expression":
        return (f"Rewrite {p.get('expr')} in its simplest equivalent form (same value wherever "
                f"both sides are defined)")
    if kind == "count_solutions":
        b = p.get("bounds") or {}
        rng = "; ".join(f"{v} in [{lohi[0]}, {lohi[1]}]" for v, lohi in b.items())
        return (f"Count the integer tuples satisfying: {' and '.join(ir.get('givens') or [])}"
                + (f", searching {rng}" if rng else ""))
    if kind == "limit":
        side = {"+": " from the right", "-": " from the left"}.get(p.get("side") or "", " (two-sided)")
        return f"Find the limit of {p.get('expr')} as {p.get('var', 'x')} -> {p.get('to')}{side}"
    if kind == "derivative":
        base = f"the derivative{' of order ' + str(p['order']) if p.get('order') else ''} of {p.get('f')} with respect to {p.get('var', 'x')}"
        return f"Find {base} at {p.get('var', 'x')} = {p['at']}" if p.get("at") else f"Find {base}"
    if kind == "antiderivative":
        return f"Find an antiderivative of {p.get('integrand')} with respect to {p.get('var', 'x')}"
    if kind == "definite_integral":
        return f"Compute the definite integral of {p.get('integrand')} d{p.get('var', 'x')} from {p.get('a')} to {p.get('b')}"
    if kind == "tangent_line":
        return f"Find the tangent line to {p.get('dep', 'y')} = {p.get('f')} at {p.get('var', 'x')} = {p.get('at')}"
    if kind == "extremum":
        which = p.get("which", "max")
        w = {"max": "the maximum value", "min": "the minimum value", "argmax": "the point where the maximum is attained",
             "argmin": "the point where the minimum is attained", "local_max": "the local maximum value",
             "local_min": "the local minimum value", "local_argmax": "the point of the local maximum",
             "local_argmin": "the point of the local minimum"}.get(which, which)
        return f"Find {w} of {p.get('f')} on the interval {p.get('interval', 'all reals')}"
    if kind == "trig_solve":
        iv = f" in the interval {p['interval']}" if p.get("interval") else " (general solution, k integer)"
        return f"Solve {p.get('equation') or g0} for {p.get('var', 'x')}{iv}"
    if kind == "equation_of":
        d = {k: v for k, v in p.items() if k not in ("object", "x", "y")}
        return f"Find the equation of the {p.get('object')} determined by {json.dumps(d, ensure_ascii=False)}"
    if kind == "synthetic_geometry":
        return (f"Points {', '.join(p.get('points') or [])} in the plane with constraints: "
                f"{'; '.join(p.get('constraints') or [])}. Find {p.get('target')}")
    if kind == "probability":
        return f"Sample space {json.dumps(p.get('space'), ensure_ascii=False)} (uniform); probability of the event: {p.get('event')}"
    if kind == "count_structures":
        pr = f" satisfying {p['predicate']}" if p.get("predicate") else ""
        return f"Count the elements of {json.dumps(p.get('space'), ensure_ascii=False)}{pr}"
    if kind == "recurrence_term":
        return f"Sequence {p.get('recurrence')} with initial terms {p.get('initial')}; find the term with index {p.get('index')}"
    if kind == "closed_form":
        return f"Sequence {p.get('recurrence')} with initial terms {p.get('initial')}; find the general term in {p.get('var', 'n')}"
    if kind == "series_sum":
        return f"Sum of {p.get('term')} for {p.get('var', 'k')} from {p.get('lo')} to {p.get('hi')}"
    if kind == "linalg":
        d = {k: v for k, v in p.items() if k != "op"}
        return f"Linear algebra, operation {p.get('op')}: {json.dumps(d, ensure_ascii=False)}"
    return f"Task kind {kind}: {json.dumps(p, ensure_ascii=False)}"


def render_ir(ir: dict[str, Any]) -> str:
    """Deterministic plain-language rendering of an IR (English, for the judges)."""
    lines = []
    vs = ir.get("vars") or []
    if vs:
        lines.append("Unknowns: " + "; ".join(
            f"{v['name']} is a {_DOMAIN_WORDS.get(v.get('domain', 'real'), v.get('domain'))}"
            + (f" with {', '.join(v['constraints'])}" if v.get("constraints") else "") for v in vs))
    fs = ir.get("functions") or []
    if fs:
        lines.append("Functions: " + "; ".join(
            f"{f['name']}({', '.join(f.get('args') or ['x'])}) = {f['expr']}"
            + (f" (parameters {', '.join(f['params'])})" if f.get("params") else "")
            + (f", domain {f['domain']}" if f.get("domain") else "") for f in fs))
    gs = ir.get("givens") or []
    if gs:
        lines.append("Given (all hold): " + "; ".join(gs))
    if ir.get("domain_of_discourse"):
        lines.append(f"Domain restriction stated by the problem: {ir['domain_of_discourse']}")
    lines.append("Task: " + _task_sentence(ir["task"]["kind"], ir["task"].get("params") or {}, ir))
    lines.append(f"Expected answer shape: {ir.get('answer_shape', 'scalar')}"
                 + (f", units: {ir['units']}" if ir.get("units") else ""))
    if ir.get("options"):
        lines.append("Options: " + "  ".join(f"{k}) {v}" for k, v in ir["options"].items()))
    if ir.get("sanity"):
        lines.append("Sanity conditions on the answer: " + "; ".join(ir["sanity"]))
    return "\n".join(lines)


def judge_roundtrip(question_tr: str, options: dict[str, str] | None, ir: dict[str, Any],
                    families: tuple[str, ...] = ("anthropic", "meta"), threshold: int = 9,
                    effort: str = "high") -> dict[str, Any]:
    q = question_tr.strip()
    if options:
        q += "\n" + "  ".join(f"{k}) {v}" for k, v in options.items())
    rendered = render_ir(ir)
    user = (f"## Original question (Turkish)\n{q}\n\n## Formalisation (rendered)\n{rendered}\n\n"
            f"## Formalisation (raw IR JSON)\n{json.dumps(ir, ensure_ascii=False)}\n\n"
            "Audit the formalisation. Reply in JSON.")
    out: dict[str, Any] = {"rendered": rendered, "judges": {}, "calls": 0, "cost_usd": 0.0, "passed": False}
    scores = []
    for fam in families:
        try:
            r = get_client(fam).complete(JUDGE_SYSTEM, user, schema=JUDGE_SCHEMA, effort=effort, max_tokens=4000,
                                         tag="roundtrip_judge")
            out["calls"] += 1
            out["cost_usd"] += r.cost_usd
            j = r.parsed if isinstance(r.parsed, dict) else None
            if j is None:
                out["judges"][fam] = {"score": None, "error": f"no_json (stop={r.stop_reason})"}
                continue
            score = j.get("score")
            try:
                score = max(0, min(10, int(score)))
            except (TypeError, ValueError):
                score = None
            out["judges"][fam] = {"score": score, "faithful": bool(j.get("faithful")),
                                  "discrepancies": list(j.get("discrepancies") or []), "notes": j.get("notes", ""),
                                  "model": r.model, "cached": r.cached}
            scores.append(score)
        except LLMError as e:
            out["judges"][fam] = {"score": None, "error": str(e)[:200]}
    out["passed"] = bool(scores) and len(scores) == len(families) and all(s is not None and s >= threshold for s in scores)
    return out
