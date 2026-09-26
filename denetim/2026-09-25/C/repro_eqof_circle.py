# equation_of (circles): centre/radius are read from coeff(x,2), coeff(y,2), coeff(x,1), coeff(y,1) and
# the constant; any extra term x**3, y**4, Abs(x*y), sin(x)**3, x**3*y**3 is silently ignored.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

if __name__ == "__main__":
    x, y = sp.symbols("x y", real=True)
    truth = (x - 1)**2 + (y - 2)**2 - 9           # centre (1,2), r = 3
    base = "x**2 + y**2 - 2*x - 4*y - 4"
    pir = {"task": {"kind": "equation_of", "params": {"object": "circle_center_radius", "center": [1, 2], "radius": 3}},
           "vars": [], "givens": [], "answer_shape": "equation"}
    for extra in ["x**3", "y**4", "Abs(x*y)", "sin(x)**3", "x**3*y**3"]:
        claim = f"{base} + {extra} = 0"
        r = verify(pir, {"claimed_answer": {"kind": "equation", "payload": claim}, "steps": []})
        # independent ground truth: (4, 2) lies on the circle; evaluate the claimed polynomial there
        c = sp.sympify(f"{base} + {extra}", locals={"x": x, "y": y})
        print(f"claim {claim:45s} -> {r.verdict} {r.confidence:.2f} | truth(4,2)={truth.subs({x:4, y:2})} claim(4,2)={sp.nsimplify(c.subs({x:4, y:2}))}")
    # circle_diameter as well
    pir2 = {"task": {"kind": "equation_of", "params": {"object": "circle_diameter", "p1": [0, 0], "p2": [4, 0]}},
            "vars": [], "givens": [], "answer_shape": "equation"}
    r = verify(pir2, {"claimed_answer": {"kind": "equation", "payload": "x**2 - 4*x + y**2 + x**4 = 0"}, "steps": []})
    print("diameter claim x**2 - 4*x + y**2 + x**4 = 0 ->", r.verdict, "| (4,0) on circle, claim(4,0) =", 16 - 16 + 0 + 256)
