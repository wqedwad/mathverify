from h import *
def st(i, kind, claim):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": [], "text": ""}
if __name__ == "__main__":
    # combinatorics: correct final 10, wrong compute step
    C = ir("count_structures", {"space": {"structure": "combination", "n": 5, "k": 2}, "predicate": ""}, answer_shape="count")
    for i, (k, c) in enumerate([("compute", "binomial(5,2) = 11"), ("compute", "5*4/2 = 11"), ("eq", "binomial(5,2) = 11"),
                                 ("compute", "P(5,2) = 21"), ("compute", "factorial(5)/(factorial(2)*factorial(3)) = 12"),
                                 ("compute", "Sum(k, (k, 1, 4)) = 11")]):
        run(f"dc_comb_{i}", C, sol("10", "count", [st(1, k, c)]), "INCORRECT", show=True)
    # probability
    P = ir("probability", {"space": {"structure": "sequence", "elements": ["T","Y"], "k": 3}, "event": "t.count('T') >= 2"})
    run("dc_prob", P, sol("1/2", steps=[st(1, "compute", "3/8 + 1/8 = 5/8"), st(2, "compute", "4/8 = 1/2")]), "INCORRECT", show=True)
    # geometry
    G = ir("synthetic_geometry", {"points": ["A","B","C"], "constraints": ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90"], "target": "dist(A,C)"})
    run("dc_geo_num", G, sol("10", steps=[st(1, "compute", "6**2 + 8**2 = 110"), st(2, "compute", "sqrt(100) = 10")]), "INCORRECT", show=True)
    run("dc_geo_pts", G, sol("10", steps=[st(1, "eq", "dist(A,C)**2 = 36 + 64 + 1")]), None, show=True)
    # series
    S = ir("series_sum", {"term": "1/k**2", "var": "k", "lo": 1, "hi": "oo"}, vars=[{"name": "k", "domain": "positive_integer"}])
    run("dc_ser_sum", S, sol("pi**2/6", steps=[st(1, "compute", "Sum(1/k**2, (k, 1, oo)) = pi**2/7"), st(2, "compute", "pi**2/7 = pi**2/6")]), "INCORRECT", show=True)
    run("dc_ser_sum2", S, sol("pi**2/6", steps=[st(1, "compute", "Sum(1/k**2, (k, 1, 2)) = 3/2")]), "INCORRECT", show=True)
    R = ir("recurrence_term", {"recurrence": "a(n) = a(n-1) + 2*a(n-2)", "initial": {"1": "1", "2": "3"}, "index": 6, "var": "n"}, vars=[{"name": "n", "domain": "positive_integer"}])
    run("dc_rec_seqnotation", R, sol("43", steps=[st(1, "eq", "a(3) = 6"), st(2, "compute", "21 + 2*11 = 43")]), "INCORRECT", show=True)
    run("dc_rec_arith", R, sol("43", steps=[st(1, "compute", "3 + 2*1 = 6"), st(2, "compute", "21 + 2*11 = 43")]), "INCORRECT", show=True)
    # linalg
    L = ir("linalg", {"op": "inverse", "matrix": "Matrix([[1,2],[3,4]])"}, answer_shape="expression")
    run("dc_la_det", L, sol("Matrix([[-2, 1], [3/2, -1/2]])", steps=[st(1, "compute", "det(Matrix([[1,2],[3,4]])) = -3"), st(2, "compute", "Matrix([[4, -2], [-3, 1]])/(-2) = Matrix([[-2, 1], [3/2, -1/2]])")]), "INCORRECT", show=True)
    run("dc_la_matmul", L, sol("Matrix([[-2, 1], [3/2, -1/2]])", steps=[st(1, "compute", "Matrix([[1,2],[3,4]])*Matrix([[-2, 1], [3/2, -1/2]]) = Matrix([[1,0],[0,2]])")]), "INCORRECT", show=True)
    run("dc_la_matmul_eq", L, sol("Matrix([[-2, 1], [3/2, -1/2]])", steps=[st(1, "eq", "Matrix([[1,2],[3,4]])*Matrix([[-2, 1], [3/2, -1/2]]) = Matrix([[1,0],[0,2]])")]), "INCORRECT", show=True)
    E = ir("equation_of", {"object": "line_points", "p1": [0, 1], "p2": [1, 3]}, answer_shape="equation")
    run("dc_eqof_slope", E, sol("y = 2*x + 1", "equation", [st(1, "compute", "(3 - 1)/(1 - 0) = 3"), st(2, "compute", "1 - 2*0 = 1")]), "INCORRECT", show=True)
    run("dc_eqof_eqstep", E, sol("y = 2*x + 1", "equation", [st(1, "eq", "y = 3*x + 1")]), "INCORRECT", show=True)
