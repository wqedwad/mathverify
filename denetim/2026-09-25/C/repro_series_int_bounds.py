# series_sum (finite): bounds go through int(), which truncates: lo = 1/2 becomes 0 (principle 3: no int()).
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify
if __name__ == "__main__":
    k = sp.Symbol("k")
    print("SymPy Sum(k,(k,1/2,3)).doit() =", sp.Sum(k, (k, sp.Rational(1, 2), 3)).doit(), "| int(1/2) =", int(sp.Rational(1, 2)))
    pir = {"task": {"kind": "series_sum", "params": {"term": "k", "var": "k", "lo": "1/2", "hi": 3}},
           "vars": [{"name": "k", "domain": "positive_integer"}], "givens": [], "answer_shape": "scalar"}
    for c in ("6", "9/2"):
        r = verify(pir, {"claimed_answer": {"kind": "value", "payload": c}, "steps": []})
        print("claim", c, "->", r.verdict, r.confidence)
