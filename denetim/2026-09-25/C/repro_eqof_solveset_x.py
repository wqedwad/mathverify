# equation_of (lines): a nonlinear claim is compared by solveset in x only, with y a free parameter.
#  (a) truth is a horizontal line (x absent): solveset(.., x) = EmptySet for BOTH sides -> any
#      nonlinear claim in y alone is "equal" (y**3 = 27, i.e. the line y = 3, accepted for y = 2);
#  (b) a factor that does not contain x is dropped: (2x - y + 1)*y = 0 (line U x-axis) accepted.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import sympy as sp
from mathverify.verifier import verify

x, y = sp.symbols("x y", real=True)

def same_zero_set_witness(truth, claim, pts):
    """independent ground truth: a point on exactly one of the two curves"""
    for px, py in pts:
        a = sp.simplify((truth.lhs - truth.rhs).subs({x: px, y: py})) == 0
        b = sp.simplify((claim.lhs - claim.rhs).subs({x: px, y: py})) == 0
        if a != b:
            return (px, py, a, b)
    return None

if __name__ == "__main__":
    cases = [
        ({"object": "line_points", "p1": [0, 2], "p2": [5, 2]}, "y**3 = 27", sp.Eq(y, 2)),
        ({"object": "line_point_slope", "p": [3, 4], "slope": 0}, "y**2 = 25", sp.Eq(y, 4)),
        ({"object": "tangent_to_circle_at_point", "center": [0, 0], "point": [0, 5]}, "y**2 = 25", sp.Eq(y, 5)),
        ({"object": "line_point_parallel", "p": [1, -1], "line": "y = 3"}, "(y - 3)**2 = 0", sp.Eq(y, -1)),
        ({"object": "perpendicular_bisector", "p1": [0, 0], "p2": [0, 4]}, "y**2 = 1", sp.Eq(y, 2)),
        ({"object": "line_points", "p1": [0, 1], "p2": [1, 3]}, "y*(2*x - y + 1) = 0", sp.Eq(y, 2*x + 1)),
        ({"object": "line_points", "p1": [0, 1], "p2": [1, 3]}, "(2*x - y + 1)*sin(y) = 0", sp.Eq(y, 2*x + 1)),
        ({"object": "line_points", "p1": [0, 1], "p2": [1, 3]}, "(2*x - y + 1)*floor(y) = 0", sp.Eq(y, 2*x + 1)),
        ({"object": "perpendicular_bisector", "p1": [0, 0], "p2": [4, 0]}, "(x - 2)*(y - 1) = 0", sp.Eq(x, 2)),
    ]
    pts = [(0, 0), (0, 2), (0, 3), (5, 0), (0, sp.pi), (0, sp.Rational(1, 2)), (7, 1), (2, 5), (0, 4), (0, 5), (0, -1), (0, -5)]
    for params, claim, truth in cases:
        pir = {"task": {"kind": "equation_of", "params": params}, "vars": [], "givens": [], "answer_shape": "equation"}
        r = verify(pir, {"claimed_answer": {"kind": "equation", "payload": claim}, "steps": []})
        lhs, rhs = claim.split("=")
        c = sp.Eq(sp.sympify(lhs, locals={"x": x, "y": y}), sp.sympify(rhs, locals={"x": x, "y": y}))
        print(f"{params['object']:28s} truth {str(truth):14s} claim {claim:28s} -> {r.verdict} {r.confidence:.2f}"
              f"  witness(point, on_truth, on_claim)={same_zero_set_witness(truth, c, pts)}")
