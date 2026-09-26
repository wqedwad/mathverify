from h import *
import math, itertools
from fractions import Fraction
def G(points, constraints, target):
    return ir("synthetic_geometry", {"points": points, "constraints": constraints, "target": target})
def LA(op, **p):
    d = {"op": op}; d.update(p)
    return ir("linalg", d, answer_shape="expression")
def S(term, lo, hi):
    return ir("series_sum", {"term": term, "var": "k", "lo": lo, "hi": hi}, vars=[{"name": "k", "domain": "positive_integer"}])
if __name__ == "__main__":
    # geometry
    run("g_trap_area", G(["A","B","C","D"], ["dist(A,B) = 10", "parallel(A,B,D,C)", "dist(D,C) = 4", "dist(A,D) = 5", "dist(B,C) = 5"], "area(A,B,C,D)"), sol("28"), None, show=True)
    run("g_perim", G(["A","B","C"], ["dist(A,B) = 3", "dist(B,C) = 4", "angle(A,B,C) = 90"], "perimeter(A,B,C)"), sol("12"), "CORRECT")
    run("g_perim_wrong", G(["A","B","C"], ["dist(A,B) = 3", "dist(B,C) = 4", "angle(A,B,C) = 90"], "perimeter(A,B,C)"), sol("13"), "INCORRECT")
    run("g_ratio", G(["A","B","C","M"], ["dist(A,B) = 6", "dist(A,C) = 8", "angle(B,A,C) = 90", "midpoint(M,B,C)"], "dist(A,M)"), sol("5"), "CORRECT")
    run("g_median_wrong", G(["A","B","C","M"], ["dist(A,B) = 6", "dist(A,C) = 8", "angle(B,A,C) = 90", "midpoint(M,B,C)"], "dist(A,M)"), sol("4.99999999999"), "INCORRECT")
    run("g_equi_angle", G(["A","B","C"], ["dist(A,B) = 3", "dist(B,C) = 3", "dist(A,C) = 3"], "angle(A,B,C)"), sol("60"), None, show=True)
    # combinatorics
    run("c_digits", ir("count_structures", {"space": {"structure": "permutation", "elements": [0,1,2,3,4], "k": 3}, "predicate": "t[0] != 0"}, answer_shape="count"), sol("48", "count"), "CORRECT")
    run("c_digits_wrong", ir("count_structures", {"space": {"structure": "permutation", "elements": [0,1,2,3,4], "k": 3}, "predicate": "t[0] != 0"}, answer_shape="count"), sol("60", "count"), "INCORRECT")
    run("p_dice7", ir("probability", {"space": {"structure": "product", "sets": [[1,2,3,4,5,6],[1,2,3,4,5,6]]}, "event": "sum(t) == 7"}), sol("1/6"), "CORRECT")
    run("p_dice7_dec", ir("probability", {"space": {"structure": "product", "sets": [[1,2,3,4,5,6],[1,2,3,4,5,6]]}, "event": "sum(t) == 7"}), sol("0.1666666666666667"), None, show=True)
    run("p_big_mc_correct", ir("probability", {"space": {"structure": "sequence", "n": 10, "k": 7}, "event": "t[0] == 1"}), sol("1/10"), "UNKNOWN")
    run("p_big_mc_wrong", ir("probability", {"space": {"structure": "sequence", "n": 10, "k": 7}, "event": "t[0] == 1"}), sol("1/5"), "INCORRECT")
    run("c_committee", ir("count_structures", {"space": {"structure": "combination", "elements": ["a1","a2","a3","b1","b2"], "k": 3}, "predicate": "sum(1 for x in t if x[0]=='a') == 2"}, answer_shape="count"), sol("6", "count"), "CORRECT")
    # series
    run("s_geo_half", S("1/2**k", 0, "oo"), sol("2"), "CORRECT")
    run("s_geo_half1", S("1/2**k", 1, "oo"), sol("1"), "CORRECT")
    run("s_big_finite", S("k", 1, 10000), sol("50005000"), "CORRECT")
    run("s_big_finite_wrong", S("k", 1, 10000), sol("50005001"), "INCORRECT")
    run("s_exp", ir("series_sum", {"term": "1/factorial(k)", "var": "k", "lo": 0, "hi": "oo"}, vars=[{"name": "k", "domain": "nonneg_integer"}]), sol("E"), "CORRECT")
    run("s_pi4", ir("series_sum", {"term": "(-1)**k/(2*k+1)", "var": "k", "lo": 0, "hi": "oo"}, vars=[{"name": "k", "domain": "nonneg_integer"}]), sol("pi/4"), "CORRECT")
    run("r_ndep", ir("recurrence_term", {"recurrence": "a(n) = a(n-1) + 2*n - 1", "initial": {"1": "1"}, "index": 12, "var": "n"}, vars=[{"name": "n", "domain": "positive_integer"}]), sol("144"), "CORRECT")
    run("cf_sq", ir("closed_form", {"recurrence": "a(n) = a(n-1) + 2*n - 1", "initial": {"1": "1"}, "var": "n"}, vars=[{"name": "n", "domain": "positive_integer"}], answer_shape="expression"), sol("n**2", "expression"), "CORRECT", show=True)
    run("cf_sq_wrong", ir("closed_form", {"recurrence": "a(n) = a(n-1) + 2*n - 1", "initial": {"1": "1"}, "var": "n"}, vars=[{"name": "n", "domain": "positive_integer"}], answer_shape="expression"), sol("n**2 + n - 1", "expression"), "INCORRECT")
    # linalg
    run("la_inv3", LA("inverse", matrix="Matrix([[2,0,0],[0,3,0],[0,0,4]])"), sol("Matrix([[1/2,0,0],[0,1/3,0],[0,0,1/4]])"), "CORRECT")
    run("la_eig3", LA("eigenvalues", matrix="Matrix([[2,1,0],[1,2,0],[0,0,5]])"), sol("{1, 3, 5}", "set"), "CORRECT")
    run("la_eig_irr", LA("eigenvalues", matrix="Matrix([[1,1],[1,0]])"), sol("{(1+sqrt(5))/2, (1-sqrt(5))/2}", "set"), "CORRECT")
    run("la_evec_cplx", LA("eigenvector", matrix="Matrix([[0,-1],[1,0]])", eigenvalue="I"), sol("(1, -I)"), "CORRECT")
    run("la_evec_cplx_wrong", LA("eigenvector", matrix="Matrix([[0,-1],[1,0]])", eigenvalue="I"), sol("(1, I)"), "INCORRECT")
    run("la_sys3", LA("solve_system", A="Matrix([[1,1,1],[0,1,1],[0,0,1]])", b="Matrix([6,5,3])"), sol("(1, 2, 3)"), "CORRECT")
    run("la_evec_param", LA("eigenvector", matrix="Matrix([[2,1],[1,2]])", eigenvalue=3), sol("(1, 1)"), "CORRECT")
    # equation_of
    run("e_perp", ir("equation_of", {"object": "line_point_perpendicular", "p": [1, 2], "line": "y = 2*x + 5"}, answer_shape="equation"), sol("x + 2*y = 5", "equation"), "CORRECT")
    run("e_perp_wrong", ir("equation_of", {"object": "line_point_perpendicular", "p": [1, 2], "line": "y = 2*x + 5"}, answer_shape="equation"), sol("x + 2*y = 4", "equation"), "INCORRECT")
    run("e_par", ir("equation_of", {"object": "line_point_parallel", "p": [1, 2], "line": "y = 2*x + 5"}, answer_shape="equation"), sol("y = 2*x", "equation"), "CORRECT")
    run("e_tan", ir("equation_of", {"object": "tangent_to_circle_at_point", "center": [0, 0], "point": [3, 4]}, answer_shape="equation"), sol("3*x + 4*y = 25", "equation"), "CORRECT")
    run("e_ccp", ir("equation_of", {"object": "circle_center_point", "center": [1, 1], "point": [4, 5]}, answer_shape="equation"), sol("(x-1)**2 + (y-1)**2 = 25", "equation"), "CORRECT")
