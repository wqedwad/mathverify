"""Audit of 25 Sep 2026 (geometry / combinatorics / series / linear algebra certificates).

Every test here is a measured reproduction: before the fix the verdict was the opposite of the
mathematical truth (false CORRECT or false INCORRECT), or the layer crashed. The ground truth is
stated next to each case and was computed independently (exact iteration, brute force, a point on
one curve and not on the other)."""
import sympy as sp

from mathverify.verifier import verify


def _ir(kind, params, **kw):
    d = {"task": {"kind": kind, "params": params}, "vars": kw.pop("vars", []), "givens": [],
         "answer_shape": kw.pop("answer_shape", "scalar")}
    d.update(kw)
    return d


def _v(ir, payload, kind="value", steps=None, option=None):
    ca = {"kind": kind}
    if payload is not None:
        ca["payload"] = payload
    if option is not None:
        ca["option"] = option
    return verify(ir, {"claimed_answer": ca, "steps": steps or []}).verdict


# ------------------------------------------------------------------------------------------------
# equation_of: point sets of the plane, not solveset in x (C1, C2, H4)
# ------------------------------------------------------------------------------------------------
def _eq(params):
    return _ir("equation_of", params, answer_shape="equation")


def test_horizontal_line_rejects_other_curves_in_y():
    # truth y = 2; `y**3 = 27` is the line y = 3 — (0, 2) is on the truth and not on the claim
    ir = _eq({"object": "line_points", "p1": [0, 2], "p2": [5, 2]})
    assert _v(ir, "y**3 = 27", "equation") == "INCORRECT"
    assert _v(ir, "y**2 = 4", "equation") == "INCORRECT"            # also the line y = -2
    assert _v(ir, "y = 2", "equation") == "CORRECT"
    assert _v(ir, "(y - 2)**3 = 0", "equation") == "CORRECT"       # same zero set
    tan = _eq({"object": "tangent_to_circle_at_point", "center": [0, 0], "point": [0, 5]})
    assert _v(tan, "y**2 = 25", "equation") == "INCORRECT"         # both tangents y = ±5
    assert _v(tan, "y = 5", "equation") == "CORRECT"
    s0 = _eq({"object": "line_point_slope", "p": [3, 4], "slope": 0})
    assert _v(s0, "y**2 = 25", "equation") == "INCORRECT"
    par = _eq({"object": "line_point_parallel", "p": [1, -1], "line": "y = 3"})
    assert _v(par, "(y - 3)**2 = 0", "equation") == "INCORRECT"


def test_extra_factor_without_x_is_not_dropped():
    ir = _eq({"object": "line_points", "p1": [0, 1], "p2": [1, 3]})          # y = 2x + 1
    assert _v(ir, "y*(2*x - y + 1) = 0", "equation") == "INCORRECT"         # plus the x-axis
    assert _v(ir, "(2*x - y + 1)*(y - 5) = 0", "equation") == "INCORRECT"
    assert _v(ir, "(2*x - y + 1)*floor(y) = 0", "equation") != "CORRECT"     # a whole strip
    assert _v(ir, "(2*x - y + 1)*sin(y) = 0", "equation") != "CORRECT"
    assert _v(ir, "log(y) = log(2*x + 1)", "equation") == "INCORRECT"       # a half line
    assert _v(ir, "4*x - 2*y + 2 = 0", "equation") == "CORRECT"
    assert _v(ir, "x = (y - 1)/2", "equation") == "CORRECT"
    pb = _eq({"object": "perpendicular_bisector", "p1": [0, 0], "p2": [4, 0]})   # x = 2
    assert _v(pb, "(x - 2)*(y - 1) = 0", "equation") == "INCORRECT"


def test_claim_undefined_on_the_line_as_written():
    ir = _eq({"object": "line_points", "p1": [0, 1], "p2": [1, 3]})
    # (0, 1) is on the line, and the written claim is undefined there
    assert _v(ir, "(y - 1)/x = 2", "equation") == "INCORRECT"
    assert _v(ir, "(2*x - y + 1)/(x - 3) = 0", "equation") == "INCORRECT"   # misses (3, 7)
    assert _v(ir, "x/x*(y - 2*x - 1) = 0", "equation") == "INCORRECT"       # misses (0, 1)


def test_circle_extra_terms_are_not_ignored():
    ir = _eq({"object": "circle_center_radius", "center": [1, 2], "radius": 3})
    base = "x**2 + y**2 - 2*x - 4*y - 4"
    # (4, 2) is on the circle; the claims are 64, 16, 8, sin(4)**3, 512 there
    for extra in ("x**3", "y**4", "Abs(x*y)", "sin(x)**3", "x**3*y**3"):
        assert _v(ir, f"{base} + {extra} = 0", "equation") == "INCORRECT", extra
    assert _v(ir, f"{base} = 0", "equation") == "CORRECT"
    assert _v(ir, "2*x**2 + 2*y**2 - 4*x - 8*y - 8 = 0", "equation") == "CORRECT"
    assert _v(ir, "(x - 1)**2 + (y - 2)**2 = 9", "equation") == "CORRECT"
    assert _v(ir, "(x - 1)**2 + 2*(y - 2)**2 = 9", "equation") == "INCORRECT"
    dia = _eq({"object": "circle_diameter", "p1": [0, 0], "p2": [4, 0]})
    assert _v(dia, "x**2 - 4*x + y**2 + x**4 = 0", "equation") == "INCORRECT"
    assert _v(dia, "x**2 - 4*x + y**2 = 0", "equation") == "CORRECT"
    r5 = _eq({"object": "circle_center_radius", "center": [0, 0], "radius": "sqrt(5)"})
    assert _v(r5, "x**2 + y**2 = 5", "equation") == "CORRECT"
    assert _v(r5, "x**2 + y**2 = 6", "equation") == "INCORRECT"


def test_vertical_line_with_infinite_slope_and_bad_radius():
    ir = _eq({"object": "line_point_slope", "p": [3, 4], "slope": "oo"})
    assert _v(ir, "x = 3", "equation") == "CORRECT"
    assert _v(ir, "y = 4", "equation") == "INCORRECT"
    neg = _eq({"object": "circle_center_radius", "center": [0, 0], "radius": -2})
    assert _v(neg, "x**2 + y**2 = 4", "equation") == "UNKNOWN"
    # a value where an equation is asked for: no crash, no verdict
    c = _eq({"object": "circle_center_radius", "center": [0, 0], "radius": 1})
    assert _v(c, "1") == "UNKNOWN"
