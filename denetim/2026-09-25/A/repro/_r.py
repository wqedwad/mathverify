import sys, json
import os; sys.path.insert(0, os.environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[4] / "src")))
from mathverify.verifier import verify

def show(label, ir, sol, expect_correct):
    r = verify(json.loads(json.dumps(ir)), json.loads(json.dumps(sol)))
    bad = (r.verdict == "CORRECT" and not expect_correct) or (r.verdict == "INCORRECT" and expect_correct)
    tag = "BUG" if bad else ("cov" if r.verdict == "UNKNOWN" and expect_correct else "ok ")
    print(f"[{tag}] {label}: verdict={r.verdict} conf={r.confidence} (answer is {'right' if expect_correct else 'WRONG'})")
    print("      IR  =", json.dumps(ir, ensure_ascii=False))
    print("      SOL =", json.dumps(sol, ensure_ascii=False))
    return r
