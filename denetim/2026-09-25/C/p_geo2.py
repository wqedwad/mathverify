from h import *
import sympy as sp
def G(points, constraints, target):
    return ir("synthetic_geometry", {"points": points, "constraints": constraints, "target": target})
if __name__ == "__main__":
    for s in [1, 10, 100, 1000]:
        g = G(["A","B","C"], [f"dist(A,B) = {10*s}", f"dist(B,C) = {6*s}", "angle(B,A,C) = 30"], "dist(A,C)")
        v1 = sp.nsimplify(s*(5*sp.sqrt(3) + sp.sqrt(11)))
        v2 = sp.nsimplify(s*(5*sp.sqrt(3) - sp.sqrt(11)))
        run(f"ssa_s{s}_big", g, sol(str(v1)), "UNKNOWN", show=True)
        run(f"ssa_s{s}_small", g, sol(str(v2)), "UNKNOWN")
