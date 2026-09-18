"""JSON schemas for structured LLM outputs and converters to the internal dict formats.

Constraints measured on the Anthropic structured-output compiler: no `minimum`/`maximum`
on integers, and at most 16 union-typed (nullable) properties per schema. The IR schema
therefore uses **zero nullables**: task params are an array of {key, value, list} triples,
optional strings are "" and optional arrays are []. Meta's Model API accepts the same schema.

  IR_SCHEMA        extractor output  -> `ir_from_llm()`  -> ProblemIR dict; `ir_to_llm()` renders exemplars
  SOLUTION_SCHEMA  solver / restructurer output -> `solution_from_llm()` -> Solution dict
  JUDGE_SCHEMA     round-trip judge output {score, faithful, discrepancies, notes}
"""
from __future__ import annotations

import json
from typing import Any

from ..ir import ANSWER_SHAPES, VAR_DOMAINS
from ..router import ROUTES
from ..solution import ANSWER_KINDS, STEP_KINDS


def _s(desc: str = "") -> dict:
    return {"type": "string", "description": desc} if desc else {"type": "string"}


def _arr(items: dict, desc: str = "") -> dict:
    d = {"type": "array", "items": items}
    if desc:
        d["description"] = desc
    return d


def _obj(props: dict[str, dict], desc: str = "") -> dict:
    d = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
    if desc:
        d["description"] = desc
    return d


TASK_KINDS = sorted(ROUTES) + ["proof", "unsupported"]

# params that carry a LIST of strings in the `list` slot; everything else is a scalar `value`
LIST_PARAMS = {"p1", "p2", "p", "center", "point", "points", "constraints", "initial", "bounds"}
JSON_PARAMS = {"space"}          # value is a JSON document
INT_PARAMS = {"order", "index"}
BOOL_PARAMS = {"distinct"}

PARAM_DOC = (
    "expr, var, equation, inequality, to, side, integrand, a, b, f, at, order, interval, which, object, "
    "p1, p2, p, center, point (lists [x, y]), radius, line, slope, lo, hi, distinct, points (list), "
    "constraints (list), target, space (JSON string), predicate, event, recurrence, initial (list of "
    "'index=value'), index, name, term, op, matrix, eigenvalue, A, dep, x, y, bounds (list of 'var=lo..hi'), rel_tol"
)

IR_SCHEMA = _obj({
    "task": _obj({
        "kind": {"type": "string", "enum": TASK_KINDS},
        "params": _arr(_obj({"key": _s("parameter name"), "value": _s("scalar value, '' if the parameter is list-valued"),
                             "list": _arr(_s(), "list value, [] if scalar")}),
                       "task parameters as key/value/list triples"),
    }),
    "vars": _arr(_obj({"name": _s(), "domain": {"type": "string", "enum": sorted(VAR_DOMAINS)},
                       "constraints": _arr(_s())})),
    "givens": _arr(_s(), "relations in canonical syntax that the problem states"),
    "functions": _arr(_obj({"name": _s(), "expr": _s(), "args": _arr(_s()), "params": _arr(_s()),
                            "domain": _s("'' if unrestricted")})),
    "unknown_of_interest": _s("'' if not applicable"),
    "answer_shape": {"type": "string", "enum": sorted(ANSWER_SHAPES)},
    "options": _arr(_obj({"letter": _s(), "value": _s("canonical expression of the option text")}),
                    "[] for open-ended questions"),
    "units": _s("'' if none"),
    "sanity": _arr(_s(), "relations on `ans` every valid answer must satisfy"),
    "domain_of_discourse": _s("restriction stated by the PROBLEM on the main variable, '' if none"),
    "topic": _s(), "level": {"type": "string", "enum": ["TYT", "AYT", "UNI"]},
    "question_en": _s("faithful English restatement of the question"),
    "assumptions": _arr(_s(), "anything you had to assume or could not encode"),
    "confidence": {"type": "integer", "description": "0-10 self-assessed confidence"},
})

SOLUTION_SCHEMA = _obj({
    "claimed_answer": _obj({"kind": {"type": "string", "enum": sorted(ANSWER_KINDS)},
                            "payload": _s("canonical expression / set / interval; '' for dne"),
                            "option": _s("option letter for multiple choice, '' otherwise")}),
    "steps": _arr(_obj({"id": _s(), "kind": {"type": "string", "enum": sorted(STEP_KINDS)},
                        "claim": _s("machine-readable relation in canonical syntax; '' for prose"),
                        "from": _arr(_s()), "text": _s()})),
    "final_answer_text": _s("one line, human readable"),
})

JUDGE_SCHEMA = _obj({
    "score": {"type": "integer", "description": "0-10 fidelity score (validated client-side)"},
    "faithful": {"type": "boolean"},
    "discrepancies": _arr(_s()),
    "notes": _s(),
})


# ---------------------------------------------------------------------------- converters
def _num_or_str(e):
    s = str(e).strip()
    try:
        return int(s)
    except ValueError:
        return s


def ir_from_llm(d: dict[str, Any]) -> dict[str, Any]:
    """Structured extractor output -> ProblemIR dict."""
    params: dict[str, Any] = {}
    for kv in d.get("task", {}).get("params") or []:
        k = (kv.get("key") or "").strip()
        if not k:
            continue
        val, lst = kv.get("value", ""), kv.get("list") or []
        if k in LIST_PARAMS:
            if k == "initial":
                params[k] = {}
                for e in lst:
                    idx, _, v = str(e).partition("=")
                    params[k][idx.strip()] = v.strip()
            elif k == "bounds":
                params[k] = {}
                for e in lst:
                    var, _, rng = str(e).partition("=")
                    lo, _, hi = rng.partition("..")
                    params[k][var.strip()] = [lo.strip(), hi.strip()]
            else:
                params[k] = [str(x) for x in lst]
        elif k in JSON_PARAMS:
            try:
                sp_ = json.loads(val) if isinstance(val, str) else val
            except json.JSONDecodeError:
                sp_ = {"_raw": val}
            if isinstance(sp_, dict):
                if "elements" in sp_ and sp_["elements"] is not None:
                    sp_["elements"] = [_num_or_str(e) for e in sp_["elements"]]
                if "sets" in sp_ and sp_["sets"] is not None:
                    sp_["sets"] = [[_num_or_str(e) for e in s] for s in sp_["sets"]]
                params[k] = {kk: vv for kk, vv in sp_.items() if vv is not None}
            else:
                params[k] = sp_
        elif k in INT_PARAMS:
            try:
                params[k] = int(str(val).strip())
            except ValueError:
                params[k] = val
        elif k in BOOL_PARAMS:
            params[k] = str(val).strip().lower() in ("true", "1", "yes", "evet")
        else:
            if val != "":
                params[k] = val
            elif lst:
                params[k] = [str(x) for x in lst]
    options = {o["letter"].strip().upper(): o["value"] for o in (d.get("options") or []) if o.get("letter")}
    ir = {
        "task": {"kind": d["task"]["kind"], "params": params},
        "vars": [{"name": v["name"], "domain": v.get("domain", "real"), "constraints": list(v.get("constraints") or [])}
                 for v in d.get("vars") or []],
        "givens": list(d.get("givens") or []),
        "functions": [{"name": f["name"], "expr": f["expr"], "args": list(f.get("args") or ["x"]),
                       "params": list(f.get("params") or []),
                       **({"domain": f["domain"]} if f.get("domain") else {})} for f in d.get("functions") or []],
        "unknown_of_interest": d.get("unknown_of_interest") or None,
        "answer_shape": d.get("answer_shape", "scalar"),
        "options": options or None,
        "units": d.get("units") or None,
        "sanity": list(d.get("sanity") or []),
        "domain_of_discourse": d.get("domain_of_discourse") or None,
        "topic": d.get("topic") or None,
        "level": d.get("level") or None,
        "question_en": d.get("question_en") or None,
    }
    return ir


def ir_to_llm(ir: dict[str, Any], question_en: str = "", topic: str = "", level: str = "TYT") -> dict[str, Any]:
    """Inverse of ir_from_llm: render a hand-written IR in the extractor's output format (for exemplars)."""
    params = []
    for k, v in (ir.get("task", {}).get("params") or {}).items():
        if k == "initial" and isinstance(v, dict):
            params.append({"key": k, "value": "", "list": [f"{i}={val}" for i, val in v.items()]})
        elif k == "bounds" and isinstance(v, dict):
            params.append({"key": k, "value": "", "list": [f"{var}={lo}..{hi}" for var, (lo, hi) in v.items()]})
        elif k in JSON_PARAMS:
            params.append({"key": k, "value": json.dumps(v, ensure_ascii=False), "list": []})
        elif isinstance(v, (list, tuple)):
            params.append({"key": k, "value": "", "list": [str(x) for x in v]})
        else:
            params.append({"key": k, "value": str(v), "list": []})
    return {
        "task": {"kind": ir["task"]["kind"], "params": params},
        "vars": [{"name": v["name"], "domain": v.get("domain", "real"), "constraints": list(v.get("constraints") or [])}
                 for v in ir.get("vars") or []],
        "givens": list(ir.get("givens") or []),
        "functions": [{"name": f["name"], "expr": f["expr"], "args": list(f.get("args") or ["x"]),
                       "params": list(f.get("params") or []), "domain": f.get("domain") or ""} for f in ir.get("functions") or []],
        "unknown_of_interest": ir.get("unknown_of_interest") or "",
        "answer_shape": ir.get("answer_shape", "scalar"),
        "options": [{"letter": k, "value": str(v)} for k, v in (ir.get("options") or {}).items()],
        "units": ir.get("units") or "",
        "sanity": list(ir.get("sanity") or []),
        "domain_of_discourse": ir.get("domain_of_discourse") or "",
        "topic": topic or ir.get("topic") or "",
        "level": level or ir.get("level") or "TYT",
        "question_en": question_en,
        "assumptions": [],
        "confidence": 10,
    }


def solution_from_llm(d: dict[str, Any]) -> dict[str, Any]:
    ca = d["claimed_answer"]
    steps = []
    for i, s in enumerate(d.get("steps") or []):
        steps.append({"id": s.get("id") or f"s{i+1}", "kind": s.get("kind", "note"), "claim": s.get("claim") or "",
                      "from": list(s.get("from") or []), "text": s.get("text") or ""})
    payload = ca.get("payload")
    option = (ca.get("option") or "").strip() or None
    return {"claimed_answer": {"kind": ca["kind"], "payload": (payload if payload not in ("", None) else None),
                               "option": option},
            "steps": steps, "raw_text": d.get("final_answer_text") or "", "source": "structured"}
