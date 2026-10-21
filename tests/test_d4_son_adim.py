"""The final attack after the fourth audit (A+, merged 7892190), lens 1/4 "steps, multiple choice" (16 Oct 2026; the
findings in the attack's `tum_bulgular.json`, the decisions of the main session): each assertion failed on 0e93ed5
unless it is marked as a control. Probe: `denetim/2026-10-01/son/adim/sonda.py`.

* G1RK-2 (realistic, unjust rejection): the task's inequality became a premise of the steps (round 2 of d4h), and the
  boundary equation of the sign-table method (x**2 - 5x + 6 = 0, (x - 2)(x - 3) = 0, x = 2 or x = 3 for
  x**2 - 5x + 6 < 0) was refuted at every point of (2, 3): the right (2, 3) INCORRECT. A claim that holds nowhere
  inside an inequality premise is checked on its boundary equation instead: refuted there, refuted (x = 5); otherwise
  unknown, never verified.
* G1RK-3 (realistic, unjust rejection): '%' and '°' are unit marks. On one side only, and nothing in the question
  fixing the unit, the readings %20 = 1/5 and 20, 30° = pi/6 and 30 decide only where they agree: both different
  INCORRECT, one equal UNKNOWN, never CORRECT this way. synthetic_geometry's angle() keeps its degrees, trig_solve its
  radians. LaTeX's 30^\\circ is a degree too (it was the number 30, and \\sin(30^\\circ) was sin(30)).
* G1RK-1 (realistic, coverage): an option is read by the claim's own reader (namespace, answer shape, notation,
  cleaning); one still not read blocks CORRECT; wordproblem's check of the options reads them the same way.
* G1RK-8 (test expectation): a count wrong under both readings of 0**0 is never CORRECT (tests/test_d4_d4b_tur10.py).
* G1RK-5 (coverage, before A+; a cheap exact path): f(f(1)) of a piecewise f was undecided as written (SymPy's
  Piecewise raised on the inner Piecewise put into a condition); the inner one is taken to its branch where certified
  signs decide its conditions.
"""
import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
XI = {"name": "x", "domain": "integer"}
P12 = [{"name": "p1", "domain": "real"}, {"name": "p2", "domain": "real"}]


def _ir(kind, params, givens=(), vars_=None, shape="scalar", options=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    if options is not None:
        d["options"] = options
    return d


def _sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                                            for i, (k, c) in enumerate(steps)]}


def _statuses(r):
    layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
    return [s.get("status") for s in layer.evidence.get("steps", [])] if layer is not None else []


def _ineq(e, form="params"):
    if form == "params":
        return _ir("solve_inequality", {"inequality": e, "var": "x"}, shape="set")
    return _ir("solve_inequality", {"var": "x"}, [e], shape="set")


A23 = "Interval.open(2, 3)"
CRIT = [("eq", "x**2 - 5*x + 6 = 0"), ("eq", "(x - 2)*(x - 3) = 0"), ("eq", "Or(Eq(x, 2), Eq(x, 3))")]


# ---------------------------------------------------------------- G1RK-2: the boundary equation of an inequality

@pytest.mark.parametrize("form", ["params", "givens"])
@pytest.mark.parametrize("steps", [CRIT, CRIT[:1], CRIT[2:]])
def test_g1rk2_the_boundary_equation_of_the_sign_table_is_not_refuted(form, steps):
    r = verify(_ineq("x**2 - 5*x + 6 < 0", form), _sol(A23, "interval", steps))
    assert r.verdict == "CORRECT"
    assert all(s in ("unknown", "skipped") for s in _statuses(r))         # never verified this way


@pytest.mark.parametrize("form", ["params", "givens"])
@pytest.mark.parametrize("steps", [[("eq", "x = 5")], CRIT[:1] + [("eq", "x = 5")],
                                   CRIT[:2] + [("eq", "Or(Eq(x, 2), Eq(x, 5))")], CRIT[:1] + [("eq", "(x - 1)*(x - 6) = 0")],
                                   [("eq", "x < 2")], [("eq", "x**2 - 5*x + 6 > 0")],
                                   [("eq", "(x - 2)*(x - 3) < 0"), ("eq", "Or(Eq(x, 2), Eq(x, 5))")]])
def test_g1rk2_a_wrong_critical_point_is_still_refuted(form, steps):
    r = verify(_ineq("x**2 - 5*x + 6 < 0", form), _sol(A23, "interval", steps))
    assert r.verdict == "INCORRECT" and _statuses(r)[-1] == "refuted"


def test_g1rk2_a_restated_inequality_before_the_critical_points():
    r = verify(_ineq("x**2 - 5*x + 6 < 0"), _sol(A23, "interval", [("eq", "(x - 2)*(x - 3) < 0")] + CRIT[:1] + CRIT[2:]))
    assert r.verdict == "CORRECT" and _statuses(r) == ["verified", "unknown", "unknown"]


@pytest.mark.parametrize("e,answer,steps", [
    ("x**2 - 5*x + 6 <= 0", "Interval(2, 3)", CRIT[:1]),                                   # non-strict: its boundary too
    ("x**2 >= 9", "Union(Interval(-oo, -3), Interval(3, oo))", [("eq", "x**2 = 9")]),
    ("x**2 - 4 >= 0", "Union(Interval(-oo, -2), Interval(2, oo))", [("eq", "Or(Eq(x, -2), Eq(x, 2))")]),
    ("Abs(x - 3) < 2", "Interval.open(1, 5)", [("eq", "Abs(x - 3) = 2"), ("eq", "Or(Eq(x, 1), Eq(x, 5))")]),
])
def test_g1rk2_other_boundaries(e, answer, steps):
    r = verify(_ineq(e), _sol(answer, "interval", steps))
    assert r.verdict == "CORRECT" and _statuses(r)[-1] in ("unknown", "skipped")


@pytest.mark.parametrize("e,answer,steps", [
    ("x**2 - 5*x + 6 <= 0", "Interval(2, 3)", CRIT[:1] + [("eq", "Or(Eq(x, 2), Eq(x, 4))")]),
    ("Abs(x - 3) < 2", "Interval.open(1, 5)", [("eq", "Abs(x - 3) = 2"), ("eq", "Or(Eq(x, 1), Eq(x, 6))")]),
])
def test_g1rk2_a_wrong_point_of_another_boundary_is_refuted(e, answer, steps):
    r = verify(_ineq(e), _sol(answer, "interval", steps))
    assert r.verdict == "INCORRECT" and _statuses(r)[-1] == "refuted"


def test_g1rk2_controls_the_chains_of_d4h_round_2_stay_verified():
    r = verify(_ineq("log(x - 1) < 1"), _sol("Interval.open(1, 1 + E)", "interval",
                                             [("eq", "x - 1 > 0"), ("eq", "x - 1 < E"), ("eq", "x < 1 + E")]))
    assert r.verdict == "CORRECT" and _statuses(r) == ["verified"] * 3
    r = verify(_ineq("Abs(x - 3) < 2"), _sol("Interval.open(1, 5)", "interval", [
        ("eq", "-2 < x - 3"), ("eq", "x - 3 < 2"), ("eq", "x > 1"), ("eq", "x < 5")]))
    assert r.verdict == "CORRECT" and _statuses(r) == ["verified"] * 4


def test_g1rk2_an_inequality_given_next_to_an_equation_is_no_boundary():
    """x = -2 holds nowhere inside x > 0, but the boundary x = 0 meets x**2 = 4 nowhere either: the claim is no boundary
    of the premises, and stays refuted (control: it was refuted before)."""
    q = _ir("evaluate", {"expr": "x"}, ["x > 0", "x**2 = 4"])
    assert _statuses(verify(q, _sol("2", steps=[("eq", "x = -2")]))) == ["refuted"]
    assert _statuses(verify(q, _sol("2", steps=[("eq", "x = 2")]))) == ["verified"]


def test_g1rk2_the_mechanism():
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.steps.deterministic import _boundary_premises, _nowhere_inside
    ctx = make_ctx(ProblemIR.from_dict(_ineq("x**2 - 5*x + 6 < 0")))
    x = ctx.ns["x"]
    p = sp.Lt(x**2 - 5*x + 6, 0)
    assert _nowhere_inside(sp.Eq(x**2 - 5*x + 6, 0), p, ctx) is True
    assert _nowhere_inside(sp.Eq(x, 5), p, ctx) is True
    assert _nowhere_inside(sp.Eq(x, sp.Rational(5, 2)), p, ctx) is False             # inside: a consequence's matter
    assert _nowhere_inside(sp.Eq(x**2 - 5*x + 6, 0), sp.Le(x**2 - 5*x + 6, 0), ctx) is True   # off the boundary
    swapped = _boundary_premises(sp.Eq(x, 5), [p], [p], ctx)
    assert swapped is not None and [a[0] for a in swapped[0]] == [[sp.Eq(x**2 - 5*x + 6, 0)]]
    # the boundary meets the other premises nowhere: no swap
    assert _boundary_premises(sp.Eq(x, -2), [sp.Gt(x, 0), sp.Eq(x**2, 4)], [sp.Gt(x, 0), sp.Eq(x**2, 4)], ctx) is None
    # an inequality claim is no critical point step (SA-YO-3)
    assert _boundary_premises(sp.Ge(x**2 - 5*x + 6, 0), [p], [p], ctx) is None
    # a premise naming the variable and another symbol: no boundary in a system (SA-YO-4)
    a = sp.Symbol("a", real=True)
    assert _boundary_premises(sp.Eq(x, 5), [p, sp.Eq(x**2 - a*x - 6, 0)], [p], ctx) is None
    # an inequality with no point inside: nothing holds "nowhere inside" it (SA-RK-1)
    assert _nowhere_inside(sp.Eq(x, 3), sp.Lt(x**2 - 6*x + 9, 0), ctx) is False


def test_g1rk2_the_critical_equations():
    from mathverify.steps.deterministic import _critical_equations
    x = sp.Symbol("x", real=True)
    assert _critical_equations(sp.Ge((x - 1)/(x + 2), 0), x) == [(sp.Eq(x - 1, 0, evaluate=False), False),
                                                               (sp.Eq(x + 2, 0, evaluate=False), True)]
    eqs = _critical_equations(sp.Gt(x**2 + 1, 0, evaluate=False), x)    # kept as written: no False to fold
    assert len(eqs) == 1 and not isinstance(eqs[0][0], sp.logic.boolalg.BooleanAtom)
    assert _critical_equations(sp.Gt(1/(x - 2), 0), x) == [(sp.Eq(x - 2, 0, evaluate=False), True)]


# ---------------------------------------------------------------- audit of the branch: SA-YO-2/3/4, SA-RK-1/2/7

GE = "Union(Interval(-oo, 2), Interval(3, oo))"
RGE = "Union(Interval.open(-oo, -2), Interval(1, oo))"


@pytest.mark.parametrize("e,answer,steps", [
    # SA-YO-2/SA-RK-2: a claim read on the boundary joins no premise pool; the wrong step after it is refuted
    ("x**2 - 5*x + 6 >= 0", GE, [("eq", "x**2 - 5*x + 6 = 0"), ("eq", "Or(Eq(x, 2), Eq(x, 3))"),
                                 ("eq", "And(x >= 2, x <= 3)")]),
    ("x**2 - 4*x - 5 < 0", "Interval.open(-1, 5)", [("eq", "Or(Eq(x, -1), Eq(x, 5))"), ("eq", "x > 0")]),
    ("x**2 - 4*x - 5 < 0", "Interval.open(-1, 5)", [("eq", "x**2 - 4*x - 5 = 0"), ("eq", "And(x > -1, x < 4)")]),
    ("(x - 1)/(x + 2) < 0", "Interval.open(-2, 1)", [("eq", "x - 1 = 0"), ("eq", "x < 0")]),
    ("x**2 - 5*x + 6 < 0", A23, CRIT + [("eq", "x < 5/2")]),
    ("x**2 - 5*x + 6 < 0", A23, CRIT[:1] + [("eq", "Or(x < 3/2, x > 5/2)")]),
    ("(x - 1)/(x + 2) >= 0", RGE, [("eq", "Or(Eq(x, 1), Eq(x, -2))"), ("eq", "x >= 2")]),
    # SA-YO-3: the closed complement is the wrong region, as the open one is
    ("x**2 - 5*x + 6 < 0", A23, [("eq", "Or(x <= 2, x >= 3)")]),
    ("x**2 - 5*x + 6 < 0", A23, [("eq", "x**2 - 5*x + 6 >= 0")]),
    ("x**2 - 5*x + 6 < 0", A23, [("eq", "(x - 2)*(x - 3) >= 0")]),
    ("x**2 - 5*x + 6 >= 0", GE, [("eq", "And(x >= 2, x <= 3)")]),
    # a wrong list of roots is no choice: one of its values lies outside the solution (yanlis-onay c1 s4)
    ("x**2 - 4*x - 5 < 0", "Interval.open(-1, 5)", [("eq", "x**2 - 4*x - 5 = 0"), ("eq", "Or(Eq(x, 1), Eq(x, -5))")]),
    ("x**2 - 4*x - 5 < 0", "Interval.open(-1, 5)", [("eq", "Or(Eq(x, 1), Eq(x, -5))")]),
    # SA-RK-7: a wrong point is no root of the denominator either
    ("(x - 1)/(x + 2) >= 0", RGE, [("eq", "x = -1")]),
    ("(x + 3)/(x - 1) <= 0", "Interval.Ropen(-3, 1)", [("eq", "x = 3")]),
])
def test_sa_a_wrong_step_near_a_boundary_is_refuted(e, answer, steps):
    r = verify(_ineq(e), _sol(answer, "interval", steps))
    assert r.verdict == "INCORRECT" and _statuses(r)[-1] == "refuted"


def test_sa_yo2_a_step_after_the_boundary_is_never_verified_by_it():
    """x ∈ {2, 5/2, 3} after the root equation of x**2 - 5x + 6 <= 0: each value lies in [2, 3], a choice (skipped, as
    the step alone was before the branch), never verified on the pool the root equation left."""
    r = verify(_ineq("x**2 - 5*x + 6 <= 0"), _sol("Interval(2, 3)", "interval",
                                                 CRIT[:1] + [("eq", "Or(Eq(x, 2), Eq(x, 3), Eq(x, 5/2))")]))
    assert _statuses(r) == ["unknown", "skipped"]


def test_sa_rk2_a_right_step_after_the_boundary_stays_verified():
    r = verify(_ineq("x**2 - 5*x + 6 < 0"), _sol(A23, "interval", CRIT[:1] + [("eq", "And(x > 2, x < 3)")]))
    assert r.verdict == "CORRECT" and _statuses(r) == ["unknown", "verified"]


@pytest.mark.parametrize("givens,steps", [
    (["a > 0", "x**2 - a*x - 6 = 0", "x = 3"], [("eq", "9 + 3*a - 6 = 0")]),
    (["a > 0", "x**2 - a*x - 6 = 0", "x = 3"], [("eq", "a = -1")]),
    (["x > 0", "y > 0", "x + y = 5", "x*y = 6", "x > y"], [("eq", "y = -2")]),
    (["x > 0", "y > 0", "x + y = 5", "x*y = 6", "x > y"], [("eq", "x = -3")]),
])
def test_sa_yo4_no_boundary_in_a_system(givens, steps):
    syms = sorted({c for g in givens for c in "axy" if c in g})
    q = _ir("evaluate", {"expr": "a" if "a" in syms else "x - y"}, givens, [{"name": c, "domain": "real"} for c in syms])
    r = verify(q, _sol("1", steps=steps))
    assert r.verdict == "INCORRECT" and _statuses(r) == ["refuted"]


@pytest.mark.parametrize("q,answer,kind,steps", [
    (_ineq("x**2 - 6*x + 9 < 0"), "EmptySet", "set", [("eq", "(x - 3)**2 < 0")]),
    (_ineq("-x**2 + 4*x - 4 > 0"), "EmptySet", "set", [("eq", "-(x - 2)**2 > 0")]),
    (_ineq("x**2 + 1 < 0"), "EmptySet", "set", [("eq", "x**2 < -1")]),
    (_ineq("Abs(x - 1) < 0"), "EmptySet", "set", [("eq", "Abs(x - 1) < 0")]),
    (_ir("count_integers", {"var": "x"}, ["x**2 - 5*x + 6 < 0"], [XI], "count"), "0", "count", [("eq", "And(x > 2, x < 3)")]),
    (_ir("count_integers", {"var": "x"}, ["x**2 - 5*x + 6 < 0"], [XI], "count"), "0", "count",
     [("eq", "(x - 2)*(x - 3) < 0")]),
])
def test_sa_rk1_an_inequality_with_no_point_inside_has_no_boundary(q, answer, kind, steps):
    r = verify(q, _sol(answer, kind, steps))
    assert r.verdict == "CORRECT" and _statuses(r) == ["unknown"]


@pytest.mark.parametrize("e,answer,steps", [
    ("(x - 1)/(x + 2) >= 0", RGE, [("eq", "x + 2 = 0")]),
    ("(x - 1)/(x + 2) >= 0", RGE, [("eq", "x = 1"), ("eq", "x = -2")]),
    ("(x - 1)/(x + 2) >= 0", RGE, [("eq", "Or(Eq(x, 1), Eq(x, -2))")]),
    ("(x + 3)/(x - 1) <= 0", "Interval.Ropen(-3, 1)", [("eq", "x + 3 = 0"), ("eq", "x - 1 = 0")]),
])
def test_sa_rk7_the_root_of_a_denominator_is_a_critical_point(e, answer, steps):
    r = verify(_ineq(e), _sol(answer, "interval", steps))
    assert r.verdict == "CORRECT" and _statuses(r)[-1] == "unknown"


def test_sa_rk7_a_root_of_the_denominator_outside_a_given_is_no_boundary():
    q = _ir("solve_inequality", {"inequality": "(x - 1)/(x + 2) >= 0", "var": "x"}, ["x > 0"], shape="set")
    r = verify(q, _sol("Interval(1, oo)", "interval", [("eq", "x = -2")]))
    assert r.verdict == "INCORRECT" and _statuses(r) == ["refuted"]


# ---------------------------------------------------------------- G1RK-3: '%' and '°' are unit marks

PCT = {"A": "%10", "B": "%20", "C": "%25", "D": "%30", "E": "%40"}
DEG = {"A": "20°", "B": "30°", "C": "40°", "D": "50°", "E": "60°"}
INC = _ir("evaluate", {"expr": "(p2 - p1)/p1*100"}, ["p1 = 50", "p2 = 60"], P12)
TRI = _ir("evaluate", {"expr": "x"}, ["x + 2*x + 3*x = 180"])
HEX = _ir("evaluate", {"expr": "(n - 2)*180/n"}, ["n = 6"], [{"name": "n", "domain": "positive_integer"}])
OH = {"A": "108°", "B": "120°", "C": "135°", "D": "144°", "E": "150°"}


def _mc(q, opts):
    return dict(q, options=opts)


@pytest.mark.parametrize("q,s", [
    (_mc(INC, PCT), _sol("20", option="B")), (_mc(INC, PCT), _sol("%20", option="B")), (_mc(INC, PCT), _sol(None, option="B")),
    (INC, _sol("%20")), (INC, _sol("20%")), (INC, _sol("20\\%")),
    (_mc(TRI, DEG), _sol("30", option="B")), (_mc(TRI, DEG), _sol("30°", option="B")), (_mc(TRI, DEG), _sol(None, option="B")),
    (TRI, _sol("30°")), (TRI, _sol("30 derece")), (TRI, _sol("30^\\circ")),
    (_mc(HEX, OH), _sol("120", option="B")), (_mc(HEX, OH), _sol(None, option="B")),
])
def test_g1rk3_a_right_answer_with_a_unit_mark_is_not_refuted(q, s):
    r = verify(q, s)
    assert r.verdict == "UNKNOWN" and "unit_convention" in {f for la in r.layers for f in la.flags}


@pytest.mark.parametrize("q,s", [
    (_mc(INC, PCT), _sol("25", option="C")), (_mc(INC, PCT), _sol("20", option="C")), (_mc(INC, PCT), _sol(None, option="C")),
    (INC, _sol("%25")), (_mc(TRI, DEG), _sol("40", option="C")), (_mc(TRI, DEG), _sol("30", option="C")),
    (_mc(TRI, DEG), _sol(None, option="C")), (TRI, _sol("40°")), (TRI, _sol("40^{\\circ}")), (_mc(HEX, OH), _sol(None, option="A")),
])
def test_g1rk3_a_wrong_answer_with_a_unit_mark_is_refuted(q, s):
    assert verify(q, s).verdict == "INCORRECT"


@pytest.mark.parametrize("q,s", [
    # the IR in the unit's own reading (a fraction, radians): one reading equal, never CORRECT this way
    (_mc(_ir("evaluate", {"expr": "(p2 - p1)/p1"}, ["p1 = 50", "p2 = 60"], P12), PCT), _sol(None, option="B")),
    (_mc(_ir("evaluate", {"expr": "x"}, ["x + 2*x + 3*x = pi"]), DEG), _sol("pi/6", option="B")),
])
def test_g1rk3_one_reading_is_never_correct(q, s):
    assert verify(q, s).verdict == "UNKNOWN"


def test_g1rk3_controls_the_unit_fixed_by_the_question():
    assert verify(INC, _sol("20")).verdict == "CORRECT"                                  # no mark: as before
    assert verify(TRI, _sol("30")).verdict == "CORRECT"
    assert verify(_ir("evaluate", {"expr": "%20*50"}), _sol("10")).verdict == "CORRECT"   # the IR's own mark
    assert verify(_ir("evaluate", {"expr": "sin(30°)"}), _sol("1/2")).verdict == "CORRECT"
    geo = _ir("synthetic_geometry", {"points": ["A", "B", "C"], "constraints": ["dist(A,B)**2 = dist(A,C)**2",
                                                                                "angle(B,A,C) = 40"],
                                     "target": "angle(A,B,C)"}, vars_=[])
    for payload in ("70", "70°", "70^\\circ", "70 derece"):
        assert verify(geo, _sol(payload)).verdict == "CORRECT"
    assert verify(_mc(geo, {"A": "40°", "B": "50°", "C": "60°", "D": "70°", "E": "80°"}), _sol("70", option="D")).verdict \
        == "CORRECT"
    assert verify(_mc(geo, {"A": "40°", "B": "50°", "C": "60°", "D": "70°", "E": "80°"}), _sol("70", option="C")).verdict \
        == "INCORRECT"


@pytest.mark.parametrize("q,steps", [
    (TRI, [("eq", "6*x = 180"), ("eq", "x = 30°")]), (TRI, [("compute", "180/6 = 30°")]),
    (INC, [("compute", "(60 - 50)/50*100 = %20")]),
])
def test_g1rk3_a_step_with_a_unit_mark_is_read_both_ways(q, steps):
    r = verify(q, _sol("30" if q is TRI else "20", steps=steps))
    assert r.verdict == "CORRECT" and _statuses(r)[-1] == "unknown"


@pytest.mark.parametrize("q,steps", [
    (TRI, [("eq", "6*x = 180"), ("eq", "x = 40°")]), (INC, [("compute", "(60 - 50)/50*100 = %25")]),
])
def test_g1rk3_a_wrong_step_with_a_unit_mark_is_refuted(q, steps):
    r = verify(q, _sol("30" if q is TRI else "20", steps=steps))
    assert r.verdict == "INCORRECT" and _statuses(r)[-1] == "refuted"


def test_g1rk3_a_trig_identity_in_degrees_holds_both_ways():
    r = verify(_ir("evaluate", {"expr": "sin(5*pi/12)"}),
               _sol("(sqrt(6) + sqrt(2))/4", steps=[("compute", "sin(75°) = sin(45°)*cos(30°) + cos(45°)*sin(30°)")]))
    assert r.verdict == "CORRECT" and _statuses(r) == ["verified"]


@pytest.mark.parametrize("interval,payload,verdict", [
    ("[0, 2*pi]", "{30°, 150°}", "CORRECT"), ("[0°, 360°]", "{30°, 150°}", "CORRECT"),
    ("[0, 2*pi]", "\\{30^\\circ, 150^\\circ\\}", "CORRECT"), ("[0, 2*pi]", "{30°, 120°}", "INCORRECT"),
])
def test_g1rk3_trig_solve_keeps_its_radians(interval, payload, verdict):
    q = _ir("trig_solve", {"var": "x", "interval": interval}, ["sin(x) = 1/2"], shape="set")
    assert verify(q, _sol(payload, "set")).verdict == verdict


def test_g1rk3_a_count_of_degrees_in_trig_solve_is_read_both_ways():
    q = _ir("trig_solve", {"var": "x", "interval": "[0, 360]"}, ["sin(pi*x/180) = 1/2"], shape="set")
    assert verify(q, _sol("{30°, 150°}", "set")).verdict == "UNKNOWN"


def test_g1rk3_latex_degree_is_a_degree():
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import build_namespace, parse_answer, parse_expr_str
    ns = build_namespace(ProblemIR.from_dict(_ir("evaluate", {"expr": "x"})))
    assert sp.simplify(parse_answer("value", "30^\\circ", ns) - sp.pi / 6) == 0
    assert sp.simplify(parse_answer("value", "30^{\\circ}", ns) - sp.pi / 6) == 0
    assert sp.simplify(parse_expr_str("\\sin(30^\\circ)", ns) - sp.Rational(1, 2)) == 0
    r = verify(_ir("evaluate", {"expr": "sin(30°)"}), _sol("1/2", steps=[("compute", "\\sin(30^\\circ) = \\frac{1}{2}")]))
    assert _statuses(r) == ["verified"] and r.verdict == "CORRECT"
    r = verify(_ir("evaluate", {"expr": "sin(75°)"}), _sol("\\sin(45^\\circ)\\cos(30^\\circ) + \\cos(45^\\circ)\\sin(30^\\circ)"))
    assert r.verdict == "CORRECT"


def test_g1rk3_the_marks():
    from mathverify.normalize.parse import unit_marks, without_unit_marks
    assert unit_marks("%20") == unit_marks("20%") == unit_marks("20\\%") == {"%"}
    assert unit_marks("30°") == unit_marks("30 derece") == unit_marks("30^\\circ") == unit_marks("(1/2)°") == {"°"}
    assert unit_marks("30") == unit_marks("x**2") == unit_marks(None) == set()
    assert without_unit_marks("%20", {"%"}) == "20" and without_unit_marks("20\\%", {"%"}) == "20"
    assert without_unit_marks("{30°, 150°}", {"°"}) == "{30, 150}"
    assert without_unit_marks("30^{\\circ}", {"°"}) == "30" and without_unit_marks("(1/2)°", {"°"}) == "(1/2)"
    from mathverify.fuse import rules
    assert "unit_convention" in rules._BLOCK_POSITIVE_FLAGS


# ---------------------------------------------------------------- G1RK-1: the option read as the claim is

QI = _ir("solve_inequality", {"inequality": "x**2 - 5*x + 6 < 0", "var": "x"}, shape="set")
QE = _ir("solve_equation", {"equation": "x**2 - 5*x + 6 = 0", "var": "x"}, shape="set")
OI = {"A": "x ∈ (1, 2)", "B": "x ∈ (2, 3)", "C": "x ∈ (3, 4)", "D": "x ∈ [2, 3]", "E": "x ∈ ℝ"}
OE = {"A": "x ∈ {1, 2}", "B": "x ∈ {2, 3}", "C": "x ∈ {3, 4}", "D": "x ∈ {-2, -3}", "E": "x ∈ ∅"}
LIN = _ir("evaluate", {"expr": "x"}, ["x + y = 10", "x - y = 2"], [X, {"name": "y", "domain": "real"}])
CM = {"A": "4 cm", "B": "5 cm", "C": "6 cm", "D": "7 cm", "E": "8 cm"}
LINU = dict(LIN, units="cm")                     # the IR declares the unit of its value (SA-YO-1, SA-RK-3)


@pytest.mark.parametrize("q,s", [
    (_mc(QI, OI), _sol("x ∈ (2, 3)", "interval", option="B")), (_mc(QI, OI), _sol(A23, "interval", option="B")),
    (_mc(QI, OI), _sol(None, "interval", option="B")), (_mc(QE, OE), _sol("x ∈ {2, 3}", "set", option="B")),
    (_mc(QE, OE), _sol("{2, 3}", "set", option="B")),
    (_mc(QE, {"A": "{1, 2}", "B": "2, 3", "C": "{3, 4}", "D": "{-2, -3}", "E": "∅"}), _sol("{2, 3}", "set", option="B")),
    (_mc(QI, dict(OI, B="$x \\in (2, 3)$")), _sol(A23, "interval", option="B")),
    (_mc(LINU, CM), _sol("6", option="C")), (_mc(LINU, CM), _sol(None, option="C")),
    (_mc(LIN, dict(CM, C="6 tane")), _sol("6", option="C")),
])
def test_g1rk1_a_notation_the_claim_reads_is_read_as_an_option(q, s):
    assert verify(q, s).verdict == "CORRECT"


@pytest.mark.parametrize("q,s", [
    (_mc(QI, OI), _sol(A23, "interval", option="A")), (_mc(QI, OI), _sol(None, "interval", option="A")),
    (_mc(QI, OI), _sol(None, "interval", option="D")), (_mc(QE, OE), _sol("{2, 3}", "set", option="A")),
    (_mc(LINU, CM), _sol("6", option="D")), (_mc(LINU, CM), _sol(None, option="D")),
])
def test_g1rk1_a_wrong_letter_in_that_notation_is_refuted(q, s):
    assert verify(q, s).verdict == "INCORRECT"


LOG = {"A": "log_5 2", "B": "log_2 5", "C": "log₂ 3", "D": "ln 5", "E": "5/2"}
LN = {"A": "ln 3", "B": "ln 2", "C": "ln 4", "D": "2", "E": "1/2"}


@pytest.mark.parametrize("opts,given,payload", [
    ({"A": "0", "B": "log_2 5", "C": "1"}, "2**x = 5", "log(5)/log(2)"), ({"A": "0", "B": "log₂5", "C": "1"}, "2**x = 5", None),
    ({"A": "0", "B": "log₂ 5", "C": "1"}, "2**x = 5", "log(5)/log(2)"), ({"A": "0", "B": "log_2(5)", "C": "1"}, "2**x = 5", None),
    ({"A": "0", "B": "log_{2} 5", "C": "1"}, "2**x = 5", "log(5)/log(2)"), ({"A": "0", "B": "log2(5)", "C": "1"}, "2**x = 5", None),
    ({"A": "0", "B": "ln 2", "C": "1"}, "exp(x) = 2", "log(2)"), ({"A": "0", "B": "ln5/ln2", "C": "1"}, "2**x = 5", "log(5)/log(2)"),
    ({"A": "0", "B": "log₂32", "C": "1"}, "x = 5", "5"),
])
def test_g1rk1_logarithm_notations_are_read(opts, given, payload):
    """log_b, a subscript base and ln written with a number (the verifier's corrected expectation of G1RK-1): read by the
    one reader of claims and options."""
    q = _mc(_ir("evaluate", {"expr": "x"}, [given]), opts)
    assert verify(q, _sol(payload, option="B")).verdict == "CORRECT"


@pytest.mark.parametrize("opts,given,letter", [(LOG, "2**x = 5", "A"), (LOG, "2**x = 5", "C"), (LN, "exp(x) = 2", "A"),
                                               (LN, "exp(x) = 2", "C")])
def test_g1rk1_a_wrong_letter_in_a_logarithm_notation_is_refuted(opts, given, letter):
    """The base reading: these options unread, the wrong letter beside a right value was CORRECT (log_5 2, ln 3)."""
    q = _mc(_ir("evaluate", {"expr": "x"}, [given]), opts)
    payload = "log(5)/log(2)" if given == "2**x = 5" else "log(2)"
    assert verify(q, _sol(payload, option=letter)).verdict == "INCORRECT"
    assert verify(q, _sol(None, option=letter)).verdict == "INCORRECT"


def test_g1rk1_a_closed_interval_letter_for_an_open_answer_is_refuted():
    q = _mc(QI, {"A": "[2, 3]", "B": "x ∈ (2, 3)", "C": "(1, 2)", "D": "(3, 4)", "E": "ℝ"})
    assert verify(q, _sol(A23, "interval", option="A")).verdict == "INCORRECT"
    assert verify(q, _sol(None, "interval", option="A")).verdict == "INCORRECT"
    assert verify(q, _sol(A23, "interval", option="B")).verdict == "CORRECT"


@pytest.mark.parametrize("text", ["ln 2x", "ln 2/3", "log_2 8^2", "log 9", "2 log 3", "ln 2*3"])
def test_g1rk1_an_ambiguous_logarithm_is_not_read(text):
    """A bare number followed by what could extend it, and log without a base (ln or log10?), are read by nobody."""
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import ParseError, build_namespace, parse_answer
    ns = build_namespace(ProblemIR.from_dict(_ir("evaluate", {"expr": "x"})))
    with pytest.raises(ParseError):
        parse_answer("value", text, ns)


def test_g1rk1_the_option_as_read_is_read_as_written():
    """The claim's reader cleans '0**0 tane' to 0**0, whose value 1 is a convention: the text so read is checked as
    written like the claim's own (`_options_as_read`), and the letter is not CORRECT for 1 (control on the base: the
    option was not read at all)."""
    q = _mc(_ir("evaluate", {"expr": "x"}, ["x = 1"]), {"A": "0**0 tane", "B": "2", "C": "3"})
    assert verify(q, _sol("1", option="A")).verdict == "UNKNOWN"


def test_g1rk1_an_option_no_reader_takes_still_blocks():
    q = _mc(QE, {"A": "{1, 2}", "B": "2 ve 3", "C": "{3, 4}", "D": "{-2, -3}", "E": "∅"})
    assert verify(q, _sol("{2, 3}", "set", option="B")).verdict == "UNKNOWN"
    q = _mc(_ir("evaluate", {"expr": "x"}, ["10**x = 9"]), {"A": "0", "B": "log 9", "C": "1"})
    assert verify(q, _sol("log(9)/log(10)", option="B")).verdict == "UNKNOWN"


def test_g1rk1_wordproblem_reads_the_options_as_the_claim():
    """wordproblem checks the options against the givens: '6 cm' read with no value left no option satisfiable, and the
    right letter was blocked as an inconsistent IR."""
    r = verify(_mc(LINU, CM), _sol("6", option="C"))
    wp = next(la for la in r.layers if la.layer == "certify.wordproblem")
    assert wp.verdict == "pass" and "ir_inconsistent" not in wp.flags


# ---------------------------------------------------------------- G1RK-8: 0**0 in a count

def _ci(g, lo, hi):
    return _ir("count_integers", {"var": "x"}, [g, f"x >= {lo}", f"x <= {hi}"], [XI], "count")


def test_g1rk8_a_count_wrong_under_both_readings_of_zero_to_the_zero_is_refuted():
    """x**x (2 + sin x) > 0 on -3..3: -2, 1, 2, 3 and 0 when 0**0 = 1, so 4 or 5. The count never applied the real_power
    convention (the verifier's measure): every claim was UNKNOWN; each integer is now decided at the point."""
    ci = _ci("x**x*(2 + sin(x)) > 0", -3, 3)
    for c in ("2", "3", "6", "7"):
        assert verify(ci, _sol(c, "count")).verdict == "INCORRECT"
    for c in ("4", "5"):
        assert verify(ci, _sol(c, "count")).verdict == "UNKNOWN"


@pytest.mark.parametrize("g,lo,hi,right,wrong", [("x**x*(2 + sin(x)) > 0", 1, 3, "3", "2"),
                                                  ("x**x*(2 + sin(x)) > 0", -3, -1, "1", "0"),
                                                  ("(x - 1)**x > 0", 0, 3, "3", "4"), ("x**x > 1", -3, 3, "2", "3"),
                                                  ("x**x*(2 + sin(x)) > 0", -100, 100, None, "100")])
def test_g1rk8_a_count_with_no_zero_to_the_zero_is_decided(g, lo, hi, right, wrong):
    ci = _ci(g, lo, hi)
    if right is not None:
        assert verify(ci, _sol(right, "count")).verdict == "CORRECT"
    assert verify(ci, _sol(wrong, "count")).verdict == "INCORRECT"


def test_g1rk8_controls_a_power_undecided_at_a_point_decides_nothing():
    ci = _ci("x**(x/2) > 0", -3, 3)                      # (-3)**(-3/2): the real root, the principal value or none
    for c in ("2", "3", "4"):
        assert verify(ci, _sol(c, "count")).verdict == "UNKNOWN"


# ---------------------------------------------------------------- G1RK-5: the composition of a piecewise function

def _fq(f, e):
    return dict(_ir("evaluate", {"expr": e}), functions=[{"name": "f", "expr": f, "args": ["x"], "params": []}])


@pytest.mark.parametrize("f,e,right,wrong", [
    ("Piecewise((x + 1, x < 2), (x - 1, x >= 2))", "f(f(1))", "1", "3"),
    ("Piecewise((x**2, x < 0), (x + 3, x >= 0))", "f(f(-1))", "4", "1"),
    ("Piecewise((3*x + 1, x <= 2), (x**2 - 1, x > 2))", "f(f(1))", "15", "13"),
    ("Piecewise((x**2, x < 0), (x + 3, x >= 0))", "f(f(2))", "8", "9"),
    ("Piecewise((x + 1, x < sqrt(2)), (x - 1, x >= sqrt(2)))", "f(f(sqrt(2)))", "sqrt(2)", "sqrt(2) - 1"),
])
def test_g1rk5_the_composition_of_a_piecewise_function_at_a_point(f, e, right, wrong):
    assert verify(_fq(f, e), _sol(right)).verdict == "CORRECT"
    assert verify(_fq(f, e), _sol(wrong)).verdict == "INCORRECT"


@pytest.mark.parametrize("f,e", [("Piecewise((1/(x - 2), x < 3), (x - 2, x >= 3))", "f(f(4))"),
                                 ("Piecewise((x/x, x < 1), (2, x >= 1))", "f(f(0))")])
def test_g1rk5_controls_an_undefined_composition_stays_undefined(f, e):
    r = verify(_fq(f, e), _sol("0"))
    assert r.verdict == "UNKNOWN" and "problem_undefined_as_written" in {fl for la in r.layers for fl in la.flags}


# ---------------------------------------------------------------- G2YO-5, G2YO-7: options with a declared tolerance

def _tol(options, kind="evaluate"):
    if kind == "evaluate":
        return _ir("evaluate", {"expr": "sqrt(50)", "rel_tol": "0.01"}, options=options)
    return _ir("definite_integral", {"integrand": "exp(x**2)", "var": "x", "a": "0", "b": "1", "rel_tol": "0.01"},
               options=options)


O50 = {"A": "7.01", "B": "7.07", "C": "7.1", "D": "7.2", "E": "7.5"}            # A, B, C within 1% of √50
O50U = {"A": "6.5", "B": "7.07", "C": "7.5", "D": "8", "E": "9"}               # B alone
OEX = {"A": "1.25", "B": "1.46", "C": "1.47", "D": "1.72", "E": "2"}           # B, C within 1% of 1.46265...
OEXU = {"A": "1.25", "B": "1.46", "C": "1.6", "D": "1.72", "E": "2"}


@pytest.mark.parametrize("q,s", [
    (_tol(O50), _sol("7.01", option="A")), (_tol(O50), _sol("7.07", option="B")), (_tol(O50), _sol("7.1", option="C")),
    (_tol(O50), _sol(None, option="A")), (_tol(OEX, "integral"), _sol("1.47", option="C")),
    (_tol(OEX, "integral"), _sol(None, option="C")),
    (_ir("definite_integral", {"integrand": "x**2", "var": "x", "a": "0", "b": "1", "rel_tol": "0.05"},
         options={"A": "1/3", "B": "0.34", "C": "1/2", "D": "1", "E": "2/3"}), _sol("0.34", option="B")),
])
def test_g2yo5_several_options_in_the_window_name_none(q, s):
    r = verify(q, s)
    assert r.verdict == "UNKNOWN" and "options_within_declared_tolerance" in {f for la in r.layers for f in la.flags}


@pytest.mark.parametrize("q,s,verdict", [
    (_tol(O50U), _sol("7.0711", option="B"), "CORRECT"), (_tol(O50U), _sol("7.07", option="B"), "CORRECT"),
    (_tol(O50U), _sol(None, option="B"), "CORRECT"), (_tol(OEXU, "integral"), _sol("1.4627", option="B"), "CORRECT"),
    (_tol(OEXU, "integral"), _sol(None, option="B"), "CORRECT"),
    (_tol(O50U), _sol("7.0711", option="C"), "INCORRECT"), (_tol(O50U), _sol(None, option="C"), "INCORRECT"),
    (_tol(OEXU, "integral"), _sol("1.4627", option="C"), "INCORRECT"),
    (_tol(O50), _sol("7.0711", option="B"), "UNKNOWN"),                      # G2YO-7 with several in the window
])
def test_g2yo7_the_claim_and_the_option_compared_within_the_declared_tolerance(q, s, verdict):
    assert verify(q, s).verdict == verdict


# ---------------------------------------------------------------- audit of the branch: SA-RK-4, SA-RK-5, SA-RK-6

TRIU, INCU = dict(TRI, units="derece"), dict(INC, units="%")


@pytest.mark.parametrize("q,s", [
    (TRIU, _sol("30°")), (TRIU, _sol("30^\\circ")), (TRIU, _sol("30 derece")), (dict(TRI, units="°"), _sol("30°")),
    (_mc(TRIU, DEG), _sol(None, option="B")), (_mc(TRIU, DEG), _sol("30", option="B")), (_mc(TRIU, DEG), _sol("30°", option="B")),
    (INCU, _sol("%20")), (_mc(INCU, PCT), _sol(None, option="B")), (_mc(dict(INC, units="yüzde"), PCT), _sol("20", option="B")),
    (TRIU, _sol("30", steps=[("eq", "6*x = 180"), ("eq", "x = 30°")])),
])
def test_sa_rk4_a_unit_the_ir_declares_is_read_as_the_plain_number(q, s):
    r = verify(q, s)
    assert r.verdict == "CORRECT", r.verdict
    assert all(st != "refuted" for st in _statuses(r))


@pytest.mark.parametrize("q,s", [
    (TRIU, _sol("40°")), (_mc(TRIU, DEG), _sol(None, option="C")), (_mc(TRIU, DEG), _sol("30", option="C")),
    (INCU, _sol("%25")), (_mc(INCU, PCT), _sol(None, option="C")),
    (TRIU, _sol("30", steps=[("eq", "6*x = 180"), ("eq", "x = 40°")])),
])
def test_sa_rk4_a_wrong_answer_in_the_declared_unit_is_refuted(q, s):
    assert verify(q, s).verdict == "INCORRECT"


def test_sa_rk4_the_ir_own_mark_and_a_radian_measure_keep_the_unit():
    # the IR writes '°' itself: its value is pi/6, and the claim's 30° is that too, whatever units says
    q = _ir("evaluate", {"expr": "x"}, ["x = 30°"])
    assert verify(dict(q, units="derece"), _sol("30°")).verdict == "CORRECT"
    # a radian measure: 30° is pi/6 whatever units says (SA-RK-5)
    acute = _ir("evaluate", {"expr": "x"}, ["sin(x) = 1/2", "0 < x", "x < pi/2"])
    assert verify(dict(acute, units="derece"), _sol("30°")).verdict == "CORRECT"


@pytest.mark.parametrize("q,s,verdict", [
    (_ir("evaluate", {"expr": "x"}, ["sin(x) = 1/2", "0 < x", "x < pi/2"]), _sol("30°"), "CORRECT"),
    (_ir("evaluate", {"expr": "x"}, ["sin(x) = 1/2", "0 < x", "x < pi/2"]), _sol("pi/6"), "CORRECT"),
    (_ir("evaluate", {"expr": "x"}, ["sin(x) = 1/2", "0 < x", "x < pi/2"]), _sol("30"), "INCORRECT"),
    (_ir("evaluate", {"expr": "x"}, ["sin(x) = 1/2", "0 < x", "x < pi/2"]), _sol("60°"), "INCORRECT"),
    (_mc(_ir("evaluate", {"expr": "asin(1/2)"}), DEG), _sol("pi/6", option="B"), "CORRECT"),
    (_mc(_ir("evaluate", {"expr": "asin(1/2)"}), DEG), _sol(None, option="C"), "INCORRECT"),
    (_ir("solve_equation", {"equation": "cos(x) = 0", "var": "x"}, vars_=[dict(X, constraints=["0 < x", "x < pi"])],
         shape="set"), _sol("{90°}", "set"), "CORRECT"),
])
def test_sa_rk5_a_degree_of_a_radian_measure_is_its_unit(q, s, verdict):
    assert verify(q, s).verdict == verdict


def test_sa_rk5_the_mechanism():
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR

    def rad(q):
        return make_ctx(ProblemIR.from_dict(q)).angles_in_radians()
    assert rad(_ir("evaluate", {"expr": "x"}, ["sin(x) = 1/2", "0 < x", "x < pi/2"]))
    assert rad(_ir("evaluate", {"expr": "asin(1/2)"})) and rad(_ir("evaluate", {"expr": "acos(1/3)"}))
    assert not rad(_ir("evaluate", {"expr": "asin(1/2)*180/pi"}))                # a count of degrees
    assert not rad(_ir("evaluate", {"expr": "x"}, ["sin(pi*x/180) = 1/2", "0 < x", "x < 90"]))
    assert not rad(_ir("evaluate", {"expr": "x"}, ["x + 2*x + 3*x = 180"]))     # no trigonometric relation
    assert not rad(_ir("evaluate", {"expr": "2*x"}, ["sin(x) = 1/2", "0 < x", "x < pi/2"]))   # not the variable


@pytest.mark.parametrize("q,s,verdict", [
    (_tol(dict(O50U, E="Hiçbiri")), _sol("7.07", option="B"), "CORRECT"),
    (_tol(dict(O50U, E="Belirlenemez")), _sol(None, option="B"), "CORRECT"),
    (_tol(dict(O50U, E="Yukarıdakilerin hiçbiri.")), _sol("7.07", option="B"), "CORRECT"),
    (_tol(dict(O50U, E="Hiçbiri")), _sol("6.5", option="A"), "INCORRECT"),
    (_tol(dict(O50U, E="Hiçbiri")), _sol(None, option="E"), "UNKNOWN"),          # chosen: no value, not read
    (_tol(dict(O50U, E="7 ile 8 arasında")), _sol("7.07", option="B"), "UNKNOWN"),   # a true statement: undecided
    (_tol(dict(O50U, E="5√2")), _sol("7.07", option="B"), "UNKNOWN"),                # √50 itself, in the window
    (_tol(dict(OEXU, E="Hiçbiri"), "integral"), _sol("1.4627", option="B"), "CORRECT"),
])
def test_sa_rk6_an_option_naming_no_value_is_outside_the_window(q, s, verdict):
    assert verify(q, s).verdict == verdict


def test_sa_rk6_the_window_is_read_once():
    from mathverify.certify.base import TOLERANCE_WINDOW
    import mathverify.verifier as V
    calls = []
    orig = V._certify

    def counting(ir, sol, ctx, modules, *a, **k):
        calls.append(sol.claimed_answer.payload)
        return orig(ir, sol, ctx, modules, *a, **k)
    V._certify = counting
    try:
        r = verify(_tol(O50U), _sol("7.07", option="B"))
    finally:
        V._certify = orig
    assert r.verdict == "CORRECT"
    assert len(calls) == 2              # the claim, and the chosen option read as the claim; the others in the window
    assert TOLERANCE_WINDOW


# ---------------------------------------------------------------- audit of the branch: SA-YO-1, SA-RK-3, SA-RK-8

TYT = _ir("evaluate", {"expr": "3*(x + 2)/2 + 1 - (3*x/2 + 1)"})                                      # +3
CNT9 = _ir("count_integers", {"var": "x"}, ["x**2 < 9"], [XI], "count")                                 # 5
SQ36 = _ir("evaluate", {"expr": "sqrt(36)"})                                                            # 6


@pytest.mark.parametrize("q,s", [
    (_mc(TYT, {"A": "3 artar", "B": "3 azalır", "C": "6 artar", "D": "6 azalır", "E": "Değişmez"}), _sol("3", option="B")),
    (_mc(TYT, {"A": "3 artar", "B": "3 azalır", "C": "6 artar", "D": "6 azalır", "E": "Değişmez"}), _sol(None, option="B")),
    (_mc(CNT9, {"A": "3", "B": "4", "C": "7", "D": "9", "E": "5 ten büyük"}), _sol("5", "count", option="E")),
    (_mc(CNT9, {"A": "3", "B": "4", "C": "7", "D": "9", "E": "5 ve üzeri"}), _sol(None, "count", option="E")),
    (_mc(SQ36, {"A": "2", "B": "4", "C": "8", "D": "10", "E": "6 dan büyük"}), _sol("6", option="E")),
    (_mc(SQ36, {"A": "6 m", "B": "6 cm", "C": "12 cm", "D": "3 cm", "E": "60 cm"}), _sol("6", option="A")),
    (_mc(SQ36, {"A": "6 m", "B": "6 cm", "C": "12 cm", "D": "3 cm", "E": "60 cm"}), _sol(None, option="A")),
    (_mc(QI, {"A": "(2, 3) aralığının dışı", "B": "(2, 3)", "C": "[2, 3]"}), _sol(A23, "interval", option="A")),
    (_mc(QI, {"A": "(2, 3) aralığının dışı", "B": "(2, 3)", "C": "[2, 3]"}), _sol(None, "interval", option="A")),
])
def test_sa_yo1_a_word_that_may_carry_meaning_leaves_the_option_unread(q, s):
    """'3 azalır' (the value increases by 3), '5 ten büyük', '6 m' for 6 cm, '(2, 3) aralığının dışı' were read as their
    bare number or set and the wrong letter was CORRECT."""
    assert verify(q, s).verdict != "CORRECT"


@pytest.mark.parametrize("opts,payload,letter", [
    ({"A": "20 dk", "B": "1/2 saat", "C": "45 dk"}, "30", "B"), ({"A": "20 dk", "B": "1/2 saat", "C": "45 dk"}, None, "B"),
    ({"A": "500 g", "B": "1 kg", "C": "2 kg"}, None, "B"),
])
def test_sa_rk3_an_option_in_another_unit_is_not_refuted(opts, payload, letter):
    q = _mc(_ir("evaluate", {"expr": "t"}, ["t = 1000*(1/2)" if "kg" in opts["B"] else "t = 60/2"],
                [{"name": "t", "domain": "real"}]), opts)
    assert verify(q, _sol(payload, option=letter)).verdict != "INCORRECT"


def test_sa_rk3_a_unit_the_ir_declares_is_read():
    q = _mc(dict(_ir("evaluate", {"expr": "t"}, ["t = 60/2"], [{"name": "t", "domain": "real"}]), units="dk"),
            {"A": "20 dk", "B": "30 dk", "C": "45 dk"})
    assert verify(q, _sol("30", option="B")).verdict == "CORRECT"
    assert verify(q, _sol(None, option="C")).verdict == "INCORRECT"


def test_sa_yo1_options_not_read_say_nothing_about_the_ir():
    """'6 cm' with no declared unit is not read; wordproblem found no option READ satisfiable and called the IR
    inconsistent, which blocked the right value given without a letter (UNKNOWN, ir_inconsistent)."""
    q = _mc(_ir("evaluate", {"expr": "a"}, ["a = 3*2"], [{"name": "a", "domain": "real"}]),
            {"A": "4 cm", "B": "6 cm", "C": "8 cm"})
    r = verify(q, _sol("6"))
    assert r.verdict == "CORRECT" and "ir_inconsistent" not in r.flags
    assert verify(q, _sol("4")).verdict == "INCORRECT"
    assert verify(q, _sol(None, option="B")).verdict == "UNKNOWN"             # the letter: still not read
    # every option read and none satisfiable: the true value is missing from them (as before)
    r = verify(_mc(_ir("evaluate", {"expr": "a"}, ["a = 3*2"], [{"name": "a", "domain": "real"}]),
                   {"A": "4", "B": "5", "C": "8"}), _sol("6"))
    assert r.verdict == "UNKNOWN" and "ir_inconsistent" in r.flags


@pytest.mark.parametrize("opt", ["{x}", "x"])
def test_sa_rk8_an_option_naming_the_unknown_is_no_value(opt):
    q = _mc(QE, {"A": "{1, 2}", "B": opt})
    assert verify(q, _sol(None, "set", option="B")).verdict == "UNKNOWN"
    assert verify(q, _sol("{2, 3}", "set", option="B")).verdict == "UNKNOWN"
