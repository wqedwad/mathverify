# closed_form: rel.replace(f, Lambda(n, closed)) auto-evaluates Eq(...) to BooleanTrue when the claim
# satisfies the recurrence identically after SymPy's automatic expansion (every arithmetic sequence),
# then `.lhs` raises AttributeError -> layer_exception -> UNKNOWN for the CORRECT closed form.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

if __name__ == "__main__":
    pir = {"task": {"kind": "closed_form", "params": {"recurrence": "a(n) = a(n-1) + 3", "initial": {"1": "2"}, "var": "n"}},
           "vars": [{"name": "n", "domain": "positive_integer"}], "givens": [], "answer_shape": "expression"}
    for claim in ["3*n - 1", "3*(n-1) + 2"]:
        r = verify(pir, {"claimed_answer": {"kind": "expression", "payload": claim}, "steps": []})
        n = sp.Symbol("n")
        c = sp.sympify(claim, locals={"n": n})
        ok = c.subs(n, 1) == 2 and sp.simplify(c - (c.subs(n, n - 1) + 3)) == 0
        print(f"claim {claim:12s} -> {r.verdict} flags={r.flags}  | ground truth: a(1)=2 and a(n)-a(n-1)=3 identically: {ok}")
        for l in r.layers:
            if l.layer == "certify.series":
                print("    ", l.evidence.get("reason"))
