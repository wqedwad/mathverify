# linalg: a claim that IS the computation (the question restated) is evaluated by the parser and
# certified. `**` on a Matrix is not in COMPUTING_OPERATORS and linalg has no restatement check
# (evaluate has _same_structure). Principle 2: the verifier must not compute the answer itself.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
from mathverify.verifier import verify
def V(params, payload):
    pir = {"task": {"kind": "linalg", "params": params}, "vars": [], "givens": [], "answer_shape": "expression"}
    r = verify(pir, {"claimed_answer": {"kind": "value", "payload": payload}, "steps": []})
    return f"{r.verdict} {r.confidence:.2f} flags={r.flags}"
if __name__ == "__main__":
    print("inverse of [[1,2],[3,4]], claim 'Matrix([[1,2],[3,4]])**-1' ->", V({"op": "inverse", "matrix": "Matrix([[1,2],[3,4]])"}, "Matrix([[1,2],[3,4]])**-1"))
    print("matrix_expr M**5, claim = the expression itself ->", V({"op": "matrix_expr", "expr": "Matrix([[1,1],[0,1]])**5"}, "Matrix([[1,1],[0,1]])**5"))
    print("solve_system, claim 'A**-1*b' ->", V({"op": "solve_system", "A": "Matrix([[1,1],[1,-1]])", "b": "Matrix([3,1])"}, "Matrix([[1,1],[1,-1]])**-1*Matrix([3,1])"))
