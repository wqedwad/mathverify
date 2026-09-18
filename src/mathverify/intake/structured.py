"""Path (a): structured solver output -> Solution / ProblemIR with schema validation."""
from __future__ import annotations

import json
from typing import Any

from ..ir import ProblemIR, LeakageError, ANSWER_SHAPES, VAR_DOMAINS
from ..router import ROUTES, DEFERRED_KINDS
from ..solution import Solution, ANSWER_KINDS, STEP_KINDS


class SchemaError(ValueError):
    pass


def _as_dict(obj: Any) -> dict:
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError as e:
            raise SchemaError(f"invalid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise SchemaError("expected a JSON object")
    return obj


def load_solution(obj: Any) -> Solution:
    d = _as_dict(obj)
    if "claimed_answer" not in d:
        raise SchemaError("missing 'claimed_answer'")
    ca = d["claimed_answer"]
    if isinstance(ca, dict):
        if ca.get("kind") not in ANSWER_KINDS:
            raise SchemaError(f"claimed_answer.kind must be one of {sorted(ANSWER_KINDS)}")
    for i, s in enumerate(d.get("steps", [])):
        if not isinstance(s, dict):
            raise SchemaError(f"step {i} must be an object")
        if s.get("kind", "eq") not in STEP_KINDS:
            raise SchemaError(f"step {i}: kind must be one of {sorted(STEP_KINDS)}")
        if "claim" not in s:
            raise SchemaError(f"step {i}: missing 'claim' (use \"\" for prose-only steps)")
    try:
        return Solution.from_dict(d)
    except LeakageError:
        raise
    except (TypeError, ValueError) as e:
        raise SchemaError(str(e)) from e


def load_problem_ir(obj: Any, strict_kind: bool = False) -> ProblemIR:
    d = _as_dict(obj)
    if "task" not in d:
        raise SchemaError("missing 'task'")
    task = d["task"] if isinstance(d["task"], dict) else {"kind": d["task"]}
    kind = task.get("kind")
    if strict_kind and kind not in ROUTES and kind not in DEFERRED_KINDS:
        raise SchemaError(f"unknown task.kind {kind!r}")
    if d.get("answer_shape", "scalar") not in ANSWER_SHAPES:
        raise SchemaError(f"answer_shape must be one of {sorted(ANSWER_SHAPES)}")
    for v in d.get("vars", []):
        if isinstance(v, dict) and v.get("domain", "real") not in VAR_DOMAINS:
            raise SchemaError(f"var {v.get('name')}: domain must be one of {sorted(VAR_DOMAINS)}")
    try:
        return ProblemIR.from_dict(d)
    except LeakageError:
        raise
    except (TypeError, ValueError) as e:
        raise SchemaError(str(e)) from e
