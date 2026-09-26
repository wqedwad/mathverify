from h import *
def LA(op, **p):
    d = {"op": op}; d.update(p)
    return ir("linalg", d, answer_shape="expression")
if __name__ == "__main__":
    run("inv_claim_is_computation", LA("inverse", matrix="Matrix([[1,2],[3,4]])"), sol("Matrix([[1,2],[3,4]])**-1"), "UNKNOWN", show=True)
    run("mexpr_restated", LA("matrix_expr", expr="Matrix([[1,1],[0,1]])**5"), sol("Matrix([[1,1],[0,1]])**5"), "UNKNOWN", show=True)
    run("sys_claim_computation", LA("solve_system", A="Matrix([[1,1],[1,-1]])", b="Matrix([3,1])"), sol("Matrix([[1,1],[1,-1]])**-1*Matrix([3,1])"), "UNKNOWN", show=True)
    run("mexpr_T_restated", LA("matrix_expr", expr="Transpose(Matrix([[1,2],[3,4]]))"), sol("Transpose(Matrix([[1,2],[3,4]]))"), "UNKNOWN", show=True)
    run("evec_claim_nullspace", LA("eigenvector", matrix="Matrix([[2,1],[1,2]])", eigenvalue=3), sol("(Matrix([[2,1],[1,2]]) - 3*eye(2))**0*Matrix([1,1])"), None, show=True)
