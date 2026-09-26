from h import *
def LA(op, **p):
    d = {"op": op}; d.update(p)
    return ir("linalg", d, answer_shape="expression")
if __name__ == "__main__":
    M = "Matrix([[2,1],[1,2]])"   # eigen 1 (v=(1,-1)), 3 (v=(1,1))
    run("eigvals_set", LA("eigenvalues", matrix=M), sol("{1, 3}", "set"), "CORRECT")
    run("eigvals_tuple", LA("eigenvalues", matrix=M), sol("(1, 3)"), "CORRECT")
    run("eigvals_wrong", LA("eigenvalues", matrix=M), sol("{1, 2}", "set"), "INCORRECT")
    # repeated eigenvalue: 2I has single eigenvalue 2
    run("eig_rep_scalar", LA("eigenvalues", matrix="Matrix([[2,0],[0,2]])"), sol("2"), "CORRECT", show=True)
    run("eig_rep_set", LA("eigenvalues", matrix="Matrix([[2,0],[0,2]])"), sol("{2}", "set"), "CORRECT")
    run("eig_jordan_scalar", LA("eigenvalues", matrix="Matrix([[3,1],[0,3]])"), sol("3"), "CORRECT", show=True)
    # eigenvector
    run("evec_ok", LA("eigenvector", matrix=M, eigenvalue=3), sol("(1, 1)"), "CORRECT")
    run("evec_scaled", LA("eigenvector", matrix=M, eigenvalue=3), sol("(-5, -5)"), "CORRECT")
    run("evec_matrix", LA("eigenvector", matrix=M, eigenvalue=3), sol("Matrix([2, 2])"), "CORRECT")
    run("evec_zero", LA("eigenvector", matrix=M, eigenvalue=3), sol("(0, 0)"), "INCORRECT")
    run("evec_wrong", LA("eigenvector", matrix=M, eigenvalue=3), sol("(1, -1)"), "INCORRECT")
    run("evec_other_lambda", LA("eigenvector", matrix=M, eigenvalue=5), sol("(1, 1)"), "INCORRECT")
    run("evec_tiny", LA("eigenvector", matrix=M, eigenvalue=3), sol("(10**(-50), 10**(-50))"), "CORRECT")
    run("evec_near_zero_wrong", LA("eigenvector", matrix=M, eigenvalue=3), sol("(1, 1 + 10**(-40))"), "INCORRECT")
    # inverse
    run("inv_ok", LA("inverse", matrix="Matrix([[1,2],[3,4]])"), sol("Matrix([[-2, 1], [3/2, -1/2]])"), "CORRECT")
    run("inv_wrong", LA("inverse", matrix="Matrix([[1,2],[3,4]])"), sol("Matrix([[-2, 1], [3/2, 1/2]])"), "INCORRECT")
    run("inv_decimals", LA("inverse", matrix="Matrix([[1,2],[3,4]])"), sol("Matrix([[-2, 1], [1.5, -0.5]])"), "CORRECT")
    run("inv_singular_dne", LA("inverse", matrix="Matrix([[1,2],[2,4]])"), sol("DNE", "dne"), None, show=True)
    run("inv_singular_zero", LA("inverse", matrix="Matrix([[1,2],[2,4]])"), sol("Matrix([[0,0],[0,0]])"), "INCORRECT")
    # solve_system
    run("sys_ok", LA("solve_system", A="Matrix([[1,1],[1,-1]])", b="Matrix([3,1])"), sol("(2, 1)"), "CORRECT")
    run("sys_wrong", LA("solve_system", A="Matrix([[1,1],[1,-1]])", b="Matrix([3,1])"), sol("(1, 2)"), "INCORRECT")
    run("sys_singular_particular", LA("solve_system", A="Matrix([[1,1],[2,2]])", b="Matrix([2,4])"), sol("(1, 1)"), "UNKNOWN")
    run("sys_nonsquare", LA("solve_system", A="Matrix([[1,1],[1,-1],[2,0]])", b="Matrix([3,1,4])"), sol("(2, 1)"), None, show=True)
    run("sys_nonsquare_inconsistent", LA("solve_system", A="Matrix([[1,1],[1,-1],[2,0]])", b="Matrix([3,1,5])"), sol("(2, 1)"), "INCORRECT", show=True)
    # matrix_expr: product giving a column vector; claim as tuple
    run("mexpr_col_tuple", LA("matrix_expr", expr="Matrix([[1,2],[3,4]])*Matrix([1,1])"), sol("(3, 7)"), "CORRECT", show=True)
    run("mexpr_col_matrix", LA("matrix_expr", expr="Matrix([[1,2],[3,4]])*Matrix([1,1])"), sol("Matrix([3, 7])"), "CORRECT")
    run("mexpr_scalar", LA("matrix_expr", expr="Matrix([[1,2]])*Matrix([3,4])"), sol("11"), "CORRECT", show=True)
    run("mexpr_T", LA("matrix_expr", expr="Matrix([[1,2],[3,4]]).T"), sol("Matrix([[1,3],[2,4]])"), "CORRECT", show=True)
    run("mexpr_pow", LA("matrix_expr", expr="Matrix([[1,1],[0,1]])**5"), sol("Matrix([[1,5],[0,1]])"), "CORRECT")
    run("mexpr_inv", LA("matrix_expr", expr="Matrix([[1,2],[3,4]])**-1"), sol("Matrix([[-2, 1], [3/2, -1/2]])"), "CORRECT")
