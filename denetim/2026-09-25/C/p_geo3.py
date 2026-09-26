from h import *
def G(points, constraints, target):
    return ir("synthetic_geometry", {"points": points, "constraints": constraints, "target": target})
if __name__ == "__main__":
    g = G(["A","B","C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90"], "dist(A,C)")
    run("rt_imag_tiny", g, sol("10 + 10**(-25)*I"), "INCORRECT", show=True)
    run("rt_exp163", G(["A","B"], ["dist(A,B) = 262537412640768744"], "dist(A,B)"), sol("exp(pi*sqrt(163))"), "INCORRECT", show=True)
    # area constraint does not "fix the scale" per heuristic
    g2 = G(["A","B","C"], ["area(A,B,C) = 12", "dist(A,C)**2 = dist(B,C)**2"], "angle(A,C,B)")
    run("area_iso_underdet", g2, sol("360*atan(1/48)/pi"), "UNKNOWN", show=True)
    g3 = G(["A","B","C"], ["dist(A,C) = sqrt(2)", "dist(B,C) = sqrt(2)"], "angle(A,C,B)")
    run("sqrt2_iso_underdet", g3, sol("360*asin(sqrt(2)/4)/pi"), "UNKNOWN", show=True)
    # determined: right isosceles with area 8 -> hypotenuse 8 (coverage)
    g4 = G(["A","B","C"], ["perpendicular(C,A,C,B)", "dist(C,A)**2 = dist(C,B)**2", "area(A,B,C) = 8"], "dist(A,B)")
    run("area_det_len", g4, sol("8"), "CORRECT", show=True)
    # determined ratio target with scale-free equilateral (should be fine)
    g5 = G(["A","B","C"], ["dist(A,C)**2 = dist(A,B)**2", "dist(B,C)**2 = dist(A,B)**2"], "dist(A,B)*dist(A,C)/dist(B,C)")
    run("equi_scalefree_lenlike", g5, sol("1"), "UNKNOWN", show=True)
