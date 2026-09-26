# synthetic_geometry compares with num_equal(..., rel_tol=1e-18): a declared tolerance switches the
# precision ladder to NON-strict, so a claim within 1e-18 relative (or with an imaginary part < 1e-24)
# passes at the first rung. This is exactly the e^(pi*sqrt(163)) case num_equal's docstring says was fixed.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

def V(params, payload):
    pir = {"task": {"kind": "synthetic_geometry", "params": params}, "vars": [], "givens": [], "answer_shape": "scalar"}
    r = verify(pir, {"claimed_answer": {"kind": "value", "payload": payload}, "steps": []})
    return f"{r.verdict} {r.confidence:.2f}"

if __name__ == "__main__":
    rt = {"points": ["A", "B", "C"], "constraints": ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90"], "target": "dist(A,C)"}
    N = 262537412640768744
    seg = {"points": ["A", "B"], "constraints": [f"dist(A,B) = {N}"], "target": "dist(A,B)"}
    for params, claim, truth in [(rt, "10 + 10**(-19)", 10), (rt, "10000000000000000001/1000000000000000000", 10),
                                 (rt, "10 + 10**(-25)*I", 10), (seg, "exp(pi*sqrt(163))", N)]:
        diff = sp.N(sp.sympify(claim) - truth, 40)
        print(f"claim {claim:45s} truth {truth}  exact difference = {diff}  -> {V(params, claim)}")
