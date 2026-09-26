from h import *
def G(points, constraints, target):
    return ir("synthetic_geometry", {"points": points, "constraints": constraints, "target": target})
if __name__ == "__main__":
    g = G(["A","B","C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90°"], "dist(A,C)")
    run("deg_constraint_10", g, sol("10"), "CORRECT", show=True)
    # 30-60-90 triangle: angle at A target
    g2 = G(["A","B","C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90"], "angle(B,C,A)")
    import math
    print("true angle BCA (deg) =", math.degrees(math.atan(6/8)))
    g3 = G(["A","B","C"], ["dist(A,B) = 1", "dist(A,C) = 2", "angle(B,A,C) = 60"], "angle(A,B,C)")
    run("deg_target_plain", g3, sol("90"), "CORRECT", show=True)
    run("deg_target_degsym", g3, sol("90°"), "CORRECT", show=True)
    run("deg_target_rad", g3, sol("pi/2"), "INCORRECT", show=True)
