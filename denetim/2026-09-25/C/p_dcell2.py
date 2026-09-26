from h import *
def st(i, kind, claim):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": [], "text": ""}
def steps_detail(r):
    for l in r.layers:
        if l.layer == "steps.refute":
            for e in l.evidence.get("steps", []):
                print("      step", e.get("id"), e.get("kind"), e.get("status"), e.get("reason"), str(e.get("evidence"))[:300])
if __name__ == "__main__":
    C = ir("count_structures", {"space": {"structure": "combination", "n": 5, "k": 2}, "predicate": ""}, answer_shape="count")
    steps_detail(run("dc_comb_5", C, sol("10", "count", [st(1, "compute", "Sum(k, (k, 1, 4)) = 11")]), "INCORRECT"))
    R = ir("recurrence_term", {"recurrence": "a(n) = a(n-1) + 2*a(n-2)", "initial": {"1": "1", "2": "3"}, "index": 6, "var": "n"}, vars=[{"name": "n", "domain": "positive_integer"}])
    steps_detail(run("dc_rec_seqnotation", R, sol("43", steps=[st(1, "eq", "a(3) = 6")]), "INCORRECT"))
    L = ir("linalg", {"op": "inverse", "matrix": "Matrix([[1,2],[3,4]])"}, answer_shape="expression")
    steps_detail(run("dc_la_matmul_eq", L, sol("Matrix([[-2, 1], [3/2, -1/2]])", steps=[st(1, "eq", "Matrix([[1,2],[3,4]])*Matrix([[-2, 1], [3/2, -1/2]]) = Matrix([[1,0],[0,2]])")]), "INCORRECT"))
    steps_detail(run("dc_la_det_eq", L, sol("Matrix([[-2, 1], [3/2, -1/2]])", steps=[st(1, "eq", "det(Matrix([[1,2],[3,4]])) = -3")]), "INCORRECT"))
    steps_detail(run("dc_la_inv_eq", L, sol("Matrix([[-2, 1], [3/2, -1/2]])", steps=[st(1, "eq", "Matrix([[1,2],[3,4]])**-1 = Matrix([[-2, 1], [3/2, 1/2]])")]), "INCORRECT"))
    steps_detail(run("dc_la_inv_compute", L, sol("Matrix([[-2, 1], [3/2, -1/2]])", steps=[st(1, "compute", "Matrix([[1,2],[3,4]])**-1 = Matrix([[-2, 1], [3/2, 1/2]])")]), "INCORRECT"))
    E = ir("equation_of", {"object": "line_points", "p1": [0, 1], "p2": [1, 3]}, answer_shape="equation")
    steps_detail(run("dc_eqof_eqstep", E, sol("y = 2*x + 1", "equation", [st(1, "eq", "y = 3*x + 1")]), "INCORRECT"))
    # eigen with vector eq-step
    EV = ir("linalg", {"op": "eigenvector", "matrix": "Matrix([[2,1],[1,2]])", "eigenvalue": 3}, answer_shape="expression")
    steps_detail(run("dc_evec_eq", EV, sol("(1, 1)", steps=[st(1, "eq", "Matrix([[2,1],[1,2]])*Matrix([1,1]) = Matrix([3,4])")]), "INCORRECT"))
    # probability: eq step with fractions and a wrong but eq-kind claim
    P = ir("probability", {"space": {"structure": "sequence", "elements": ["T","Y"], "k": 3}, "event": "t.count('T') >= 2"})
    steps_detail(run("dc_prob_eq", P, sol("1/2", steps=[st(1, "eq", "3/8 + 1/8 = 5/8")]), "INCORRECT"))
    # series finite sum with bound var declared
    S = ir("series_sum", {"term": "k", "var": "k", "lo": 1, "hi": 4}, vars=[{"name": "k", "domain": "positive_integer"}])
    steps_detail(run("dc_ser_eq", S, sol("10", steps=[st(1, "eq", "Sum(k, (k, 1, 4)) = 11")]), "INCORRECT"))
