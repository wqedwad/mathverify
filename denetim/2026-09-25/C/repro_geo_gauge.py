# synthetic_geometry: _scale_is_fixed() ignores length constraints whose constants are in {±1, ±2, 1/2}
# (or sqrt(2)), and area constraints entirely; the gauge then silently adds dist(P1,P2) = 1. An
# UNDER-determined problem becomes "determined" and the gauge's value is certified.
# _scale_invariant() also calls dist*dist/dist "scale invariant" although it scales linearly.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

def V(params, payload):
    pir = {"task": {"kind": "synthetic_geometry", "params": params}, "vars": [], "givens": [], "answer_shape": "scalar"}
    r = verify(pir, {"claimed_answer": {"kind": "value", "payload": payload}, "steps": []})
    return f"{r.verdict} {r.confidence:.2f}"

def apex_deg(leg, base):          # isosceles apex angle, law of cosines (independent ground truth)
    return sp.N(sp.deg(sp.acos((2*leg**2 - base**2) / (2*leg**2))), 12)

if __name__ == "__main__":
    P = ["A", "B", "C"]
    # CA = CB = 1, nothing else: the apex angle is NOT determined
    g1 = {"points": P, "constraints": ["dist(A,C) = 1", "dist(B,C) = 1"], "target": "angle(A,C,B)"}
    print("CA=CB=1: apex for AB=1:", apex_deg(1, 1), " for AB=1.5:", apex_deg(1, sp.Rational(3, 2)), " -> claim 60:", V(g1, "60"))
    g2 = {"points": P, "constraints": ["dist(A,C) = sqrt(2)", "dist(B,C) = sqrt(2)"], "target": "angle(A,C,B)"}
    print("CA=CB=sqrt2: apex for AB=1:", apex_deg(sp.sqrt(2), 1), " for AB=2:", apex_deg(sp.sqrt(2), 2), " -> claim 360*asin(sqrt(2)/4)/pi:", V(g2, "360*asin(sqrt(2)/4)/pi"))
    # isosceles with area 12: base 1 -> apex 2*atan(1/48); base 6 (height 4) -> apex 2*atan(3/4)
    g3 = {"points": P, "constraints": ["area(A,B,C) = 12", "dist(A,C)**2 = dist(B,C)**2"], "target": "angle(A,C,B)"}
    print("isosceles area 12: apex(base 1) =", sp.N(sp.deg(2*sp.atan(sp.Rational(1, 48))), 12), " apex(base 6) =", sp.N(sp.deg(2*sp.atan(sp.Rational(3, 4))), 12),
          " -> claim 360*atan(1/48)/pi:", V(g3, "360*atan(1/48)/pi"))
    # scale-free equilateral triangle, target dist(A,B)*dist(A,C)/dist(B,C) = side length s (arbitrary)
    g4 = {"points": P, "constraints": ["dist(A,C)**2 = dist(A,B)**2", "dist(B,C)**2 = dist(A,B)**2"], "target": "dist(A,B)*dist(A,C)/dist(B,C)"}
    print("equilateral of any side s: target = s*s/s = s -> claim 1:", V(g4, "1"))
