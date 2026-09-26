# Degree sign in synthetic_geometry: preclean turns "90°" into pi/2, but angle() is measured in degrees.
from h import *
import sympy as sp
def G(points, constraints, target):
    return ir("synthetic_geometry", {"points": points, "constraints": constraints, "target": target})
if __name__ == "__main__":
    # Right triangle, legs 6 and 8, right angle written with the degree sign -> hypotenuse is 10
    g = G(["A","B","C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90°"], "dist(A,C)")
    # ground truth: law of cosines with a 90 degree angle
    truth = sp.sqrt(6**2 + 8**2 - 2*6*8*sp.cos(sp.pi/2))
    print("ground truth AC =", truth)
    wrong = "sqrt(100 - 96*cos(pi**2/360))"   # AC if the angle were pi/2 DEGREES (= 1.5708 deg)
    print("wrong value =", sp.N(sp.sympify(wrong), 20))
    run("deg_constraint_true10", g, sol("10"), "CORRECT", show=True)
    run("deg_constraint_wrong", g, sol(wrong), "INCORRECT", show=True)
    # angle target with the degree sign in the claim
    g3 = G(["A","B","C"], ["dist(A,B) = 1", "dist(A,C) = 2", "angle(B,A,C) = 60"], "angle(A,B,C)")
    # ground truth: 1-2-sqrt3 triangle, angle at B is 90 degrees
    print("ground truth angle ABC =", sp.deg(sp.acos(sp.Rational(1,1)*(1 + 3 - 4)/(2*1*sp.sqrt(3)))))
    run("deg_claim_90deg", g3, sol("90°"), "CORRECT", show=True)
