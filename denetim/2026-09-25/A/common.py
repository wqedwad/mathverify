import sys, json, time, traceback
import os; sys.path.insert(0, os.environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
from mathverify.verifier import verify

RESULTS = []

def ir(kind, params=None, vars_=None, givens=None, dod=None, shape=None, options=None, functions=None, uoi=None, sanity=None):
    d = {"task": {"kind": kind, "params": params or {}},
         "vars": vars_ if vars_ is not None else [{"name": "x"}],
         "givens": givens or []}
    if dod is not None: d["domain_of_discourse"] = dod
    if shape: d["answer_shape"] = shape
    if options: d["options"] = options
    if functions: d["functions"] = functions
    if uoi: d["unknown_of_interest"] = uoi
    if sanity: d["sanity"] = sanity
    return d

def sol(kind, payload, steps=None, option=None):
    ca = {"kind": kind, "payload": payload}
    if option: ca["option"] = option
    return {"claimed_answer": ca, "steps": steps or []}

def run(name, problem, solution, truth_correct, note=""):
    """truth_correct: True if claimed answer (and steps) are right, False if wrong."""
    t0 = time.time()
    try:
        r = verify(json.loads(json.dumps(problem)), json.loads(json.dumps(solution)))
        v, c, fl = r.verdict, r.confidence, r.flags
        tr = r.decision_trace
    except Exception as e:
        v, c, fl, tr = "EXC", 0, [], traceback.format_exc()
    dt = time.time() - t0
    bad = "."
    if v == "EXC":
        bad = "!!CRASH"
    elif truth_correct is False and v == "CORRECT":
        bad = "!!!FALSE_CORRECT"
    elif truth_correct is True and v == "INCORRECT":
        bad = "!!FALSE_INCORRECT"
    elif truth_correct is True and v == "UNKNOWN":
        bad = "(unknown-cov)"
    if dt > 60:
        bad += " !!SLOW"
    print(f"{bad:18s} {name:40s} truth={'OK ' if truth_correct else 'BAD'} -> {v:9s} conf={c} t={dt:.1f}s flags={fl} {note}")
    if bad.startswith("!!"):
        print("    |TRACE:", tr.replace("\n", "\n    |")[:3000])
    RESULTS.append((name, truth_correct, v, bad))
    sys.stdout.flush()
    return v

def summary():
    n = len(RESULTS)
    bad = [r for r in RESULTS if r[3].startswith("!!")]
    print(f"== {n} cases, {len(bad)} flagged: {[b[0] for b in bad]}")
