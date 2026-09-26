from h import *
def G(points, constraints, target):
    return ir("synthetic_geometry", {"points": points, "constraints": constraints, "target": target})
if __name__ == "__main__":
    g = G(["A","B","C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90"], "dist(A,C)")
    run("rt_ok", g, sol("10"), "CORRECT")
    run("rt_wrong", g, sol("11"), "INCORRECT")
    run("rt_tiny_off", g, sol("10 + 10**(-19)"), "INCORRECT", show=True)
    run("rt_tiny_off2", g, sol("10000000000000000001/1000000000000000000"), "INCORRECT")
    run("rt_float", g, sol("10.0"), "CORRECT")
    # scale heuristic: legs 1 and 1, angle unknown -> underdetermined
    g2 = G(["A","B","C"], ["dist(A,C) = 1", "dist(B,C) = 1"], "angle(A,C,B)")
    run("iso_underdet_60", g2, sol("60"), "UNKNOWN", show=True)
    g3 = G(["A","B","C"], ["dist(A,C) = 2", "dist(B,C) = 2"], "angle(A,C,B)")
    run("iso_underdet_2", g3, sol("2*asin(1/4)*180/pi"), "UNKNOWN", show=True)
    # determined equilateral with side 2 -> expect CORRECT (coverage)
    g4 = G(["A","B","C"], ["dist(A,B) = 2", "dist(A,C) = 2", "dist(B,C) = 2"], "area(A,B,C)")
    run("equi2_area", g4, sol("sqrt(3)"), "CORRECT", show=True)
    g5 = G(["A","B","C"], ["dist(A,B) = 1", "dist(A,C) = 2", "perpendicular(A,B,A,C)"], "dist(B,C)")
    run("rt12_hyp", g5, sol("sqrt(5)"), "CORRECT", show=True)
