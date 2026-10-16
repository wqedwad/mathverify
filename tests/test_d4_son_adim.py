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
    assert swapped is not None and swapped[0] == [sp.Eq(x**2 - 5*x + 6, 0)]
    # the boundary meets the other premises nowhere: no swap
    assert _boundary_premises(sp.Eq(x, -2), [sp.Gt(x, 0), sp.Eq(x**2, 4)], [sp.Gt(x, 0), sp.Eq(x**2, 4)], ctx) is None


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
    (_mc(_ir("evaluate", {"expr": "asin(1/2)"}), DEG), _sol("pi/6", option="B")),
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


@pytest.mark.parametrize("q,s", [
    (_mc(QI, OI), _sol("x ∈ (2, 3)", "interval", option="B")), (_mc(QI, OI), _sol(A23, "interval", option="B")),
    (_mc(QI, OI), _sol(None, "interval", option="B")), (_mc(QE, OE), _sol("x ∈ {2, 3}", "set", option="B")),
    (_mc(QE, OE), _sol("{2, 3}", "set", option="B")),
    (_mc(QE, {"A": "{1, 2}", "B": "2, 3", "C": "{3, 4}", "D": "{-2, -3}", "E": "∅"}), _sol("{2, 3}", "set", option="B")),
    (_mc(QI, dict(OI, B="$x \\in (2, 3)$")), _sol(A23, "interval", option="B")),
    (_mc(LIN, CM), _sol("6", option="C")), (_mc(LIN, CM), _sol(None, option="C")),
    (_mc(LIN, dict(CM, C="6 TL")), _sol("6", option="C")),
    (_mc(_ir("evaluate", {"expr": "asin(1/2)"}), {"A": "π/6 rad", "B": "π/4", "C": "π/3", "D": "π/2", "E": "π"}),
     _sol("pi/6", option="A")),
])
def test_g1rk1_a_notation_the_claim_reads_is_read_as_an_option(q, s):
    assert verify(q, s).verdict == "CORRECT"


@pytest.mark.parametrize("q,s", [
    (_mc(QI, OI), _sol(A23, "interval", option="A")), (_mc(QI, OI), _sol(None, "interval", option="A")),
    (_mc(QI, OI), _sol(None, "interval", option="D")), (_mc(QE, OE), _sol("{2, 3}", "set", option="A")),
    (_mc(LIN, CM), _sol("6", option="D")), (_mc(LIN, CM), _sol(None, option="D")),
])
def test_g1rk1_a_wrong_letter_in_that_notation_is_refuted(q, s):
    assert verify(q, s).verdict == "INCORRECT"


@pytest.mark.parametrize("opt,given,payload", [("log_2 5", "2**x = 5", "log(5)/log(2)"), ("ln 2", "exp(x) = 2", "log(2)"),
                                               ("log₂5", "2**x = 5", "log(5)/log(2)")])
def test_g1rk1_an_option_no_reader_takes_still_blocks(opt, given, payload):
    """The claim's reader does not take these either (measured): the decision keeps the block."""
    q = _mc(_ir("evaluate", {"expr": "x"}, [given]), {"A": "0", "B": opt, "C": "100", "D": "-100", "E": "1000"})
    assert verify(q, _sol(payload, option="B")).verdict == "UNKNOWN"
    assert verify(_ir("evaluate", {"expr": "x"}, [given]), _sol(opt)).verdict == "UNKNOWN"


def test_g1rk1_wordproblem_reads_the_options_as_the_claim():
    """wordproblem checks the options against the givens: '6 cm' read with no value left no option satisfiable, and the
    right letter was blocked as an inconsistent IR."""
    r = verify(_mc(LIN, CM), _sol("6", option="C"))
    wp = next(la for la in r.layers if la.layer == "certify.wordproblem")
    assert wp.verdict == "pass" and "ir_inconsistent" not in wp.flags


# ---------------------------------------------------------------- G1RK-8: 0**0 in a count

def test_g1rk8_a_count_wrong_under_both_readings_is_never_correct():
    ci = _ir("count_integers", {"var": "x"}, ["x**x*(2 + sin(x)) > 0", "x >= -3", "x <= 3"], [XI], "count")
    for c in ("3", "6"):
        assert verify(ci, _sol(c, "count")).verdict != "CORRECT"
    for c in ("4", "5"):                                 # 0**0 undefined, 0**0 = 1: control
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
