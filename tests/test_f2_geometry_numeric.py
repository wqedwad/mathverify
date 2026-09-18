"""F2 — synthetic geometry by numeric realisation: determined targets are certified,
underdetermined targets are UNKNOWN (never guessed), degenerate configurations are rejected."""
import pytest
import sympy as sp

from mathverify.certify.geometry_numeric import certify_geometry, GeoProblem
from mathverify.verifier import verify


def _ir(points, constraints, target):
    return {"task": {"kind": "synthetic_geometry",
                     "params": {"points": points, "constraints": constraints, "target": target}}, "vars": []}


def _sol(v):
    return {"claimed_answer": {"kind": "value", "payload": v}}


def test_right_triangle_hypotenuse():
    ir = _ir(["A", "B", "C"], ["dist(A,B) = 3", "dist(B,C) = 4", "angle(A,B,C) = 90"], "dist(A,C)")
    assert verify(ir, _sol("5")).verdict == "CORRECT"
    assert verify(ir, _sol("7")).verdict == "INCORRECT"
    assert verify(ir, _sol("sqrt(25)")).verdict == "CORRECT"


def test_scale_free_angle_problem():
    ir = _ir(["A", "B", "C"], ["angle(B,A,C) = 50", "angle(A,B,C) = 60"], "angle(A,C,B)")
    assert verify(ir, _sol("70")).verdict == "CORRECT"
    assert verify(ir, _sol("60")).verdict == "INCORRECT"


def test_length_target_in_scale_free_problem_is_unknown():
    ir = _ir(["A", "B", "C"], ["angle(B,A,C) = 50", "angle(A,B,C) = 60"], "dist(A,C)")
    r = verify(ir, _sol("5"))
    assert r.verdict == "UNKNOWN"


def test_underdetermined_is_unknown_with_flag():
    ir = _ir(["A", "B", "C"], ["dist(A,B) = 3"], "dist(A,C)")
    r = verify(ir, _sol("5"))
    assert r.verdict == "UNKNOWN" and "ir_incomplete" in r.flags


def test_midpoint_median_and_area():
    ir = _ir(["A", "B", "C", "M"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90", "midpoint(M, A, C)"],
             "dist(B,M)")
    assert verify(ir, _sol("5")).verdict == "CORRECT"          # median to the hypotenuse
    ir = _ir(["A", "B", "C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90"], "area(A,B,C)")
    assert verify(ir, _sol("24")).verdict == "CORRECT"
    assert verify(ir, _sol("48")).verdict == "INCORRECT"


def test_isosceles_base_angles():
    ir = _ir(["A", "B", "C"], ["dist(A,B)**2 = dist(A,C)**2", "angle(B,A,C) = 40"], "angle(A,B,C)")
    assert verify(ir, _sol("70")).verdict == "CORRECT"


def test_parallel_and_perpendicular_constraints():
    # rectangle: AB = 12, BC = 5, right angles -> diagonal 13
    ir = _ir(["A", "B", "C", "D"], ["dist(A,B) = 12", "dist(B,C) = 5", "perpendicular(A,B,B,C)",
                                    "parallel(A,B,D,C)", "parallel(B,C,A,D)"], "dist(A,C)")
    assert verify(ir, _sol("13")).verdict == "CORRECT"


def test_realisations_are_deterministic_under_seed():
    ok1, ev1 = certify_geometry(["A", "B", "C"], ["dist(A,B) = 3", "dist(B,C) = 4", "angle(A,B,C) = 90"],
                                "dist(A,C)", sp.Integer(5), seed=3)
    ok2, ev2 = certify_geometry(["A", "B", "C"], ["dist(A,B) = 3", "dist(B,C) = 4", "angle(A,B,C) = 90"],
                                "dist(A,C)", sp.Integer(5), seed=3)
    assert ok1 is True and ev1["value"] == ev2["value"]


def test_inequality_constraint_rejected():
    ok, ev = certify_geometry(["A", "B", "C"], ["dist(A,B) > 3"], "dist(A,C)", sp.Integer(5))
    assert ok is None and "parse_error" in ev["error"]


def test_geo_problem_counts_degrees_of_freedom():
    gp = GeoProblem(["A", "B", "C"], ["dist(A,B) = 3", "dist(B,C) = 4", "angle(A,B,C) = 90"], "dist(A,C)")
    assert gp.n_free == 0 and gp.scale_fixed is True
