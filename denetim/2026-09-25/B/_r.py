"""Minimal repro helper: prints verdict and the ground-truth expectation for each case."""
import json
import sys

import os; sys.path.insert(0, os.environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))


def IR(kind, params, vars_=("x",), **kw):
    d = {"task": {"kind": kind, "params": params}, "vars": [{"name": v} for v in vars_],
         "givens": [], "answer_shape": kw.pop("answer_shape", "scalar")}
    d.update(kw)
    return d


def SOL(kind, payload, steps=None):
    return {"claimed_answer": {"kind": kind, "payload": payload}, "steps": steps or []}


def check(label, ir, sol, expected_not):
    """expected_not: the verdict that would be WRONG given the ground truth."""
    from mathverify.verifier import verify
    r = verify(ir, sol)
    bug = r.verdict == expected_not
    print(f"{'BUG' if bug else 'ok '} {label}: verdict={r.verdict} conf={r.confidence}")
    print("    problem_ir =", json.dumps(ir))
    print("    solution   =", json.dumps(sol))
    return bug
