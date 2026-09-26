# recurrence_term: sp.solve(rel, a(n)) and sol[0] is taken silently. For a(n)**2 = 4*a(n-1) the first
# root is the NEGATIVE branch; the verifier certifies the complex value -4*I and rejects the real,
# positive sequence value 4. Ambiguity is not flagged.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

if __name__ == "__main__":
    pir = {"task": {"kind": "recurrence_term", "params": {"recurrence": "a(n)**2 = 4*a(n-1)", "initial": {"1": "4"}, "index": 3, "var": "n"}},
           "vars": [{"name": "n", "domain": "positive_integer"}], "givens": [], "answer_shape": "scalar"}
    # independent ground truth: real sequences satisfying the recurrence
    reals = set()
    for a2 in (2*sp.sqrt(4), -2*sp.sqrt(4)):
        for s in (1, -1):
            a3 = s*2*sp.sqrt(a2)
            if a3.is_real:
                reals.add(a3)
    print("real values of a(3):", reals, " (positive sequence: 4)")
    for claim in ["4", "-4*I"]:
        r = verify(pir, {"claimed_answer": {"kind": "value", "payload": claim}, "steps": []})
        print(f"claim {claim:6s} -> {r.verdict} {r.confidence:.2f}")
