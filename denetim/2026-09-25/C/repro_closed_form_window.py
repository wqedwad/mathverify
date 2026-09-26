# closed_form: when the symbolic recurrence check fails, the claim is accepted if the recurrence holds on
# n = lo..lo+19 only, and each term is compared with num_equal(val, 0, abs_tol=1e-25).
# Wrong closed forms that agree on the window, or differ by < 1e-25, are certified CORRECT.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

def V(rec, initial, claim):
    pir = {"task": {"kind": "closed_form", "params": {"recurrence": rec, "initial": initial, "var": "n"}},
           "vars": [{"name": "n", "domain": "positive_integer"}], "givens": [], "answer_shape": "expression"}
    r = verify(pir, {"claimed_answer": {"kind": "expression", "payload": claim}, "steps": []})
    return f"{r.verdict} {r.confidence:.2f}"

def first_bad(truth_terms, claim, N=40):
    n = sp.Symbol("n", integer=True, positive=True)
    c = sp.sympify(claim, locals={"n": n})
    for k in range(1, N + 1):
        if sp.simplify(c.subs(n, k) - truth_terms[k]) != 0:
            return k, sp.N(c.subs(n, k) - truth_terms[k], 5)
    return None

if __name__ == "__main__":
    # independent truth by iterating the recurrence exactly
    ar = {1: sp.Integer(2)}
    for k in range(2, 41): ar[k] = ar[k - 1] + 3          # a(n) = a(n-1) + 3, a(1) = 2  -> 3n - 1
    ge = {1: sp.Integer(3)}
    for k in range(2, 41): ge[k] = 2 * ge[k - 1]          # a(n) = 2 a(n-1), a(1) = 3  -> 3*2^(n-1)
    for rec, init, truth, claim in [
        ("a(n) = a(n-1) + 3", {"1": "2"}, ar, "3*n - 1 + 3*floor(n/22)"),
        ("a(n) = 2*a(n-1)", {"1": "3"}, ge, "3*2**(n-1) + floor(n/23)"),
        ("a(n) = 2*a(n-1)", {"1": "3"}, ge, "3*2**(n-1) + (n-1)*exp(-100*n)"),
    ]:
        print(f"{rec:22s} claim {claim:32s} -> {V(rec, init, claim)}   first index where claim != a(n): {first_bad(truth, claim)}")
