# synthetic_geometry: preclean turns "40°" into 40*pi/180 (radians) while angle() is measured in DEGREES.
# A constraint written with the degree sign builds the wrong figure; a claim written with it is compared in radians.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

def V(params, payload, options=None, option=None):
    pir = {"task": {"kind": "synthetic_geometry", "params": params}, "vars": [], "givens": [], "answer_shape": "scalar"}
    if options: pir["options"] = options
    ca = {"kind": "value"}
    if payload is not None: ca["payload"] = payload
    if option: ca["option"] = option
    r = verify(pir, {"claimed_answer": ca, "steps": []})
    return f"{r.verdict} {r.confidence:.2f}"

if __name__ == "__main__":
    # (1) tyt-geo-002 written as in the booklet: |AB| = |AC|, angle A = 40 deg -> angle B = 70 deg
    iso = {"points": ["A", "B", "C"], "constraints": ["dist(A,B)**2 = dist(A,C)**2", "angle(B,A,C) = 40°"], "target": "angle(A,B,C)"}
    print("ground truth angle B = (180-40)/2 =", sp.Rational(180 - 40, 2))
    print("claim 70              ->", V(iso, "70"))
    print("claim 90 - pi/9 (wrong: 'angle A = 2*pi/9 degrees') ->", V(iso, "90 - pi/9"), "  numeric:", sp.N(90 - sp.pi/9))
    opts = {"A": "40°", "B": "50°", "C": "60°", "D": "70°", "E": "80°"}
    iso_plain = dict(iso, constraints=["dist(A,B)**2 = dist(A,C)**2", "angle(B,A,C) = 40"])
    print("plain constraint, options with deg sign, letter D only ->", V(iso_plain, None, opts, "D"))
    # (2) right triangle legs 6, 8, right angle written 90° -> hypotenuse 10
    rt = {"points": ["A", "B", "C"], "constraints": ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90°"], "target": "dist(A,C)"}
    print("ground truth AC =", sp.sqrt(6**2 + 8**2))
    print("claim 10 ->", V(rt, "10"))
    print("claim sqrt(100 - 96*cos(pi**2/360)) (wrong, =%s) ->" % sp.N(sp.sqrt(100 - 96*sp.cos(sp.pi**2/360)), 8), V(rt, "sqrt(100 - 96*cos(pi**2/360))"))
