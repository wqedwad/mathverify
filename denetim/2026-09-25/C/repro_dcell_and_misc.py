# D-cell: wrong eq-kind steps that are never refuted while the final answer is right.
#  (a) matrix-valued `eq` steps: _check_eq -> _holds -> relation_holds_at cannot decide Eq(Matrix, Matrix)
#      -> "unknown" (the same claim with kind `compute` IS refuted);
#  (b) steps written with the problem's own sequence name a(3) are skipped as undeclared_symbol
#      (`a` lives in task.params, not in ir.functions/vars).
# Also: equation_of with slope "oo" (vertical line) refutes the right answer x = 3.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

def st(kind, claim):
    return {"id": "s1", "kind": kind, "claim": claim, "from": [], "text": ""}

if __name__ == "__main__":
    inv = {"task": {"kind": "linalg", "params": {"op": "inverse", "matrix": "Matrix([[1,2],[3,4]])"}}, "vars": [], "givens": [], "answer_shape": "expression"}
    good = "Matrix([[-2, 1], [3/2, -1/2]])"
    claim = "Matrix([[1,2],[3,4]])*Matrix([[-2, 1], [3/2, -1/2]]) = Matrix([[1,0],[0,2]])"
    print("ground truth M*M^-1 =", sp.Matrix([[1, 2], [3, 4]]) * sp.Matrix([[-2, 1], [sp.Rational(3, 2), -sp.Rational(1, 2)]]))
    for kind in ("eq", "compute"):
        r = verify(inv, {"claimed_answer": {"kind": "expression", "payload": good}, "steps": [st(kind, claim)]})
        print(f"inverse, step kind={kind:7s} '{claim}' -> {r.verdict} {r.confidence:.2f} flags={r.flags}")
    ev = {"task": {"kind": "linalg", "params": {"op": "eigenvector", "matrix": "Matrix([[2,1],[1,2]])", "eigenvalue": 3}}, "vars": [], "givens": [], "answer_shape": "expression"}
    r = verify(ev, {"claimed_answer": {"kind": "value", "payload": "(1, 1)"}, "steps": [st("eq", "Matrix([[2,1],[1,2]])*Matrix([1,1]) = Matrix([3,4])")]})
    print("eigenvector, eq step M*(1,1) = (3,4) [truth (3,3)] ->", r.verdict, r.confidence, r.flags)
    rec = {"task": {"kind": "recurrence_term", "params": {"recurrence": "a(n) = a(n-1) + 2*a(n-2)", "initial": {"1": "1", "2": "3"}, "index": 6, "var": "n"}},
           "vars": [{"name": "n", "domain": "positive_integer"}], "givens": [], "answer_shape": "scalar"}
    r = verify(rec, {"claimed_answer": {"kind": "value", "payload": "43"}, "steps": [st("eq", "a(3) = 6")]})
    print("recurrence a(6)=43, eq step 'a(3) = 6' [truth a(3) = 3 + 2*1 = 5] ->", r.verdict, r.confidence, r.flags)
    v = {"task": {"kind": "equation_of", "params": {"object": "line_point_slope", "p": [3, 4], "slope": "oo"}}, "vars": [], "givens": [], "answer_shape": "equation"}
    r = verify(v, {"claimed_answer": {"kind": "equation", "payload": "x = 3"}, "steps": []})
    print("equation_of vertical line through (3,4) (slope oo), claim x = 3 ->", r.verdict, r.confidence)
