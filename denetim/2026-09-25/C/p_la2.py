from h import *
def LA(op, **p):
    d = {"op": op}; d.update(p)
    return ir("linalg", d, answer_shape="expression")
if __name__ == "__main__":
    # eigenvector (1,2) of [[1,1],[4,1]] for lambda = 3: M(1,2) = (3,6)
    M = "Matrix([[1,1],[4,1]])"
    run("evec_exact_norm", LA("eigenvector", matrix=M, eigenvalue=3), sol("(1/sqrt(5), 2/sqrt(5))"), "CORRECT")
    run("evec_dec15", LA("eigenvector", matrix=M, eigenvalue=3), sol("(0.447213595499958, 0.894427190999916)"), None, show=True)
    # same decimal precision accepted elsewhere? matrix_expr with sqrt entries
    run("mexpr_dec15", LA("matrix_expr", expr="Matrix([1, 2])/sqrt(5)"), sol("Matrix([0.447213595499958, 0.894427190999916])"), None, show=True)
    # solve_system with 1/3 solution: 3x = 1, y = 2
    S = LA("solve_system", A="Matrix([[3,0],[0,1]])", b="Matrix([1,2])")
    run("sys_dec15", S, sol("(0.333333333333333, 2)"), None, show=True)
    run("sys_dec_exact_binary", S, sol("(0.3333333333333333333333333333333, 2)"), None, show=True)
    run("sys_exact", S, sol("(1/3, 2)"), "CORRECT")
    # inverse with 1/3 entries as decimals
    run("inv_dec15", LA("inverse", matrix="Matrix([[3,0],[0,1]])"), sol("Matrix([[0.333333333333333, 0],[0, 1]])"), None, show=True)
    # eigenvalues decimals
    run("eigvals_dec", LA("eigenvalues", matrix="Matrix([[2,1],[1,1]])"), sol("{0.381966011250105, 2.61803398874989}", "set"), None, show=True)
