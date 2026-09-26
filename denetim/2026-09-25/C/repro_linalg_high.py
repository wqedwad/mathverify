# linalg false INCORRECTs:
#  (a) eigenvalues: a scalar claim is compared as a 1-element multiset, so "2" for 2*I (eigenvalue set {2})
#      is refuted with multiplicity_count_differs;
#  (b) matrix_expr: a vector claim written as a tuple becomes a 1xn ROW, the truth M*v is a column -> shape_mismatch.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

def V(params, payload, kind="value"):
    pir = {"task": {"kind": "linalg", "params": params}, "vars": [], "givens": [], "answer_shape": "expression"}
    r = verify(pir, {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []})
    return f"{r.verdict} {r.confidence:.2f}"

if __name__ == "__main__":
    for M in ("Matrix([[2,0],[0,2]])", "Matrix([[3,1],[0,3]])"):
        ev = sp.Matrix(sp.sympify(M)).eigenvals()
        lam = list(ev)[0]
        print(f"{M}: eigenvalues (SymPy) {ev}; claim '{lam}' ->", V({"op": "eigenvalues", "matrix": M}, str(lam)),
              "| claim '{%s}' (set) ->" % lam, V({"op": "eigenvalues", "matrix": M}, "{%s}" % lam, "set"))
    expr = "Matrix([[1,2],[3,4]])*Matrix([1,1])"
    print("M*v =", list(sp.sympify(expr)), "; claim '(3, 7)' ->", V({"op": "matrix_expr", "expr": expr}, "(3, 7)"),
          "| claim 'Matrix([3, 7])' ->", V({"op": "matrix_expr", "expr": expr}, "Matrix([3, 7])"),
          "| same tuple accepted by solve_system/eigenvector: solve_system ->",
          V({"op": "solve_system", "A": "Matrix([[1,0],[0,1]])", "b": "Matrix([3,7])"}, "(3, 7)"))
