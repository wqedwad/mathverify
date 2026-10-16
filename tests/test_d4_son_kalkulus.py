"""The last attack (A+ son saldırı, 16 Oct 2026), lens 3 (calculus, definedness): SON-G3-YO-1..5 (the main session's
decisions, "MERCEK 3"). Each assertion failed on 0e93ed5 unless it is marked as a control.

YO-1 (realistic): at(diff(·)) and the pinned diff(·) read a Piecewise's switch point and atan2/arg's branch cut as points
of the derivative: f'(0) = 1 for the piecewise |x|, a jump's f'(1) = 2, atan2(x, -1)'(0) = -1 were certified. They are
classified now as certify.calculus classifies a kink (u continuous, the one-sided derivatives equal, exactly); a C1
junction keeps its value. Siblings: x*|x| at 0 was read as a point with no derivative ((x|x|)' = 0 had the empty set
certified); SymPy's one-sided limit of a Piecewise at its switch point reads the wrong branch, so the derivative task, its
tangent and its function left the corner of a piecewise undecided.
YO-2 (artificial): a tangent claim is read as written. YO-3, YO-4 (artificial): the rules of A-YO-5 and A-YO-3 hold on
the value (an infinite limit as an argument) and on the operation (a pole inside any wrapper over ℂ).
YO-5 (record): (x**n)' = n*x**(n - 1), n a positive integer, stays CORRECT.
"""
import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
A_ = {"name": "a", "domain": "real"}
B_ = {"name": "b", "domain": "real"}
NP = {"name": "n", "domain": "positive_integer"}
NN = {"name": "n", "domain": "nonneg_integer"}

PW_ABS = "Piecewise((-x, x < 0), (x, x >= 0))"
JUMP = "Piecewise((x**2, x < 1), (2*x, x >= 1))"
CORNER = "Piecewise((x**2, x < 1), (3*x - 2, x >= 1))"
CUBE = "Piecewise((x**3, x < 1), (3*x - 2, x >= 1))"
C1 = "Piecewise((x**2 + 1, x < 1), (2*x, x >= 1))"
C1B = "Piecewise((x**2, x < 1), (2*x - 1, x >= 1))"
C2 = "Piecewise((x**3, x < 0), (x**3 + x**4, x >= 0))"
ROOF = "Piecewise((x + 2, x < 0), (2 - x, x >= 0))"
DNE = {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}


def _ir(kind, params, givens=(), vars_=None, shape="scalar", **extra):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    d.update({k: v for k, v in extra.items() if v is not None})
    return d


def _sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": "compute", "claim": c, "from": [], "text": ""}
                                            for i, c in enumerate(steps)]}


def _v(q, s):
    return verify(q, s).verdict


def _fn(body):
    return [{"name": "f", "expr": body, "args": ["x"], "params": []}] if body else None


def _ev(expr, f=None, givens=(), vars_=None, options=None, dod=None):
    return _ir("evaluate", {"expr": expr}, givens, vars_, functions=_fn(f), options=options, domain_of_discourse=dod)


def _at(f, p="1", order=1):
    return _ev(f"at(diff(f(x), x{', ' + str(order) if order > 1 else ''}), x, {p})", f)


def _der(f, at=None, vars_=None):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    return _ir("derivative", p, (), vars_, "scalar" if at is not None else "expression")


def _tan(f, at):
    return _ir("tangent_line", {"f": f, "var": "x", "at": at, "dep": "y"}, (), [X, Y], "equation")


def _se(eq, f=None):
    return _ir("solve_equation", {"var": "x", "equation": eq}, (), None, "set", functions=_fn(f))


# YO-1: the switch points of at(diff) -----------------------------------------------------------------------------
@pytest.mark.parametrize("q,claim", [
    (_at(PW_ABS, "0"), "1"), (_at(JUMP), "2"), (_at(CORNER), "3"), (_at(CORNER), "2"), (_at(CUBE, "1", 2), "0"),
    (_ev("diff(f(x), x)", JUMP, ("x = 1",)), "2"), (_ev("diff(f(x), x)", PW_ABS, ("x = 0",)), "1"),
    (_ev("at(diff(atan2(x, -1), x), x, 0)"), "-1"), (_ev("at(diff(arg(-1 + I*x), x), x, 0)"), "-1"),
    (_at(ROOF, "0"), "-1"),
])
def test_a_switch_point_with_no_derivative_has_no_value(q, claim):
    assert _v(q, _sol(claim)) == "UNKNOWN"


def test_an_option_at_a_switch_point_is_not_certified():
    opts = {"A": "-1", "B": "0", "C": "1", "D": "2", "E": "Yoktur"}
    assert _v(_ev("at(diff(f(x), x), x, 0)", PW_ABS, options=opts), _sol("1", option="C")) != "CORRECT"
    opts = {"A": "1", "B": "2", "C": "3", "D": "4", "E": "Yoktur"}
    assert _v(_ev("at(diff(f(x), x), x, 1)", JUMP, options=opts), _sol("2", option="B")) != "CORRECT"


def test_the_branch_cut_leaves_the_solution_set():
    # f'(x) = -1/(1 + x**2) = -1 only at 0, where atan2(x, -1) jumps: no solution (the right empty set was refuted)
    q = _se("diff(f(x), x) = -1", "atan2(x, -1)")
    assert _v(q, _sol("{0}", "set")) == "INCORRECT"
    assert _v(q, _sol("EmptySet", "set")) == "CORRECT"


@pytest.mark.parametrize("q", [_se("diff(x*Abs(x), x) = 0"), _se("diff(f(x), x) = 0", "x*Abs(x)")])
def test_a_point_with_a_derivative_stays_in_the_solution_set(q):
    # (x|x|)' = 2|x| = 0 at 0, where x|x| has the derivative 0: |x|'s corner rule dropped the point (sibling)
    assert _v(q, _sol("{0}", "set")) == "CORRECT"
    assert _v(q, _sol("EmptySet", "set")) == "INCORRECT"


def test_the_derivative_task_reads_a_piecewise_corner():
    # SymPy's one-sided limit of Piecewise((-1, x < 0), (1, True)) from the left of 0 is 1: undecided before
    assert _v(_der(PW_ABS, "0"), _sol("1")) == "INCORRECT"
    assert _v(_der(PW_ABS, "0"), DNE) == "CORRECT"
    assert _v(_der(ROOF, "0"), DNE) == "CORRECT"
    assert _v(_der(ROOF, "0"), _sol("-1")) == "INCORRECT"
    assert _v(_der(JUMP, "1"), DNE) == "CORRECT"
    assert _v(_der(JUMP, "1"), _sol("2")) == "INCORRECT"
    assert _v(_tan(ROOF, "0"), DNE) == "CORRECT"
    assert _v(_tan(ROOF, "0"), _sol("y = x + 2", "equation")) == "INCORRECT"
    assert _v(_der(PW_ABS), _sol("Piecewise((-1, x < 0), (1, x > 0))", "expression")) == "CORRECT"


def test_a_step_at_a_piecewise_corner_is_refuted():
    r = verify(_ev("x", ROOF, ("x = 1",)), _sol("1", steps=["at(diff(f(x), x), x, 0) = -1"]))
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    assert layer.evidence["steps"][-1]["status"] == "refuted"


def test_a_c1_junction_keeps_its_derivative():
    # control: a C1 junction (continuous, equal one-sided derivatives) has its value
    assert _v(_at(C1), _sol("2")) == "CORRECT"
    assert _v(_at(C1B), _sol("2")) == "CORRECT"
    assert _v(_at(C1B), _sol("3")) == "INCORRECT"
    assert _v(_at(C2, "0", 2), _sol("0")) == "CORRECT"
    assert _v(_ev("diff(f(x), x)", C1, ("x = 1",)), _sol("2")) == "CORRECT"
    assert _v(_der(C1, "1"), _sol("2")) == "CORRECT"
    assert _v(_tan(C1, "1"), _sol("y = 2*x", "equation")) == "CORRECT"
    opts = {"A": "1", "B": "2", "C": "3", "D": "4", "E": "Yoktur"}
    assert _v(_ev("at(diff(f(x), x), x, 1)", C1, options=opts), _sol("2", option="B")) == "CORRECT"


def test_off_the_switch_point_the_derivative_is_read_as_before():
    # controls
    assert _v(_at(ROOF, "-1"), _sol("1")) == "CORRECT"
    assert _v(_at(ROOF, "3"), _sol("-1")) == "CORRECT"
    assert _v(_at(ROOF, "3"), _sol("1")) == "INCORRECT"
    assert _v(_at(JUMP, "2"), _sol("2")) == "CORRECT"
    assert _v(_at(PW_ABS, "-3"), _sol("-1")) == "CORRECT"
    assert _v(_ev("at(diff(atan2(x, -1), x), x, 1)"), _sol("-1/2")) == "CORRECT"
    assert _v(_ev("at(diff(atan2(x, 1), x), x, 0)"), _sol("1")) == "CORRECT"
    assert _v(_ev("at(diff(atan2(x**2, -1), x), x, 0)"), _sol("0")) == "CORRECT"
    assert _v(_ev("at(diff(Abs(x - 1), x), x, 3)"), _sol("1")) == "CORRECT"
    giv = ("a*1**2 + b = 4*1 - 1", "at(diff(a*x**2 + b, x), x, 1) = at(diff(4*x - 1, x), x, 1)")
    assert _v(_ev("a + b", vars_=[A_, B_, X], givens=giv), _sol("3")) == "CORRECT"
    assert _v(_ev("a + b", vars_=[A_, B_, X], givens=giv), _sol("4")) == "INCORRECT"


def test_a_family_of_zeros_is_undecided_at_its_members_alone():
    # |sin x| has a corner at each k*pi (sin(x) in ORIGIN): at pi/2 the condition, put in by at() unevaluated, is read
    # with its element evaluated (sin(pi/2) = 1); left standing, the derivative was undecided there too
    assert _v(_ev("at(diff(Abs(sin(x)), x), x, pi/2)"), _sol("0")) == "CORRECT"
    assert _v(_ev("at(diff(Abs(sin(x)), x), x, pi/2)"), _sol("1")) == "INCORRECT"
    assert _v(_ev("at(diff(Abs(sin(x)), x), x, pi)"), _sol("-1")) == "UNKNOWN"


def test_the_written_derivative_is_read_the_same_every_time():
    # SymPy's cache kept a power read as written (x**(2/1**1)); its minimal polynomial raised PolynomialError inside
    # the sign guard and the as-written parse failed now and then: f'(3) = 6 of |x**2 - 4| was undecided
    q = _ev("at(diff(Abs(x**2 - 4), x), x, 3)")
    assert [_v(q, _sol("6")) for _ in range(3)] == ["CORRECT"] * 3
    assert _v(q, _sol("5")) == "INCORRECT"


def test_arg_is_read_as_atan2_at_its_zero():
    # arg(1 + I*x) has no cut at 0 (re > 0): its derivative 1 there; SymPy takes no limit of arg (undecided before
    # the rewrite, which only the classification uses)
    assert _v(_ev("at(diff(arg(1 + I*x), x), x, 0)"), _sol("1")) == "CORRECT"


def test_the_differentiability_conditions():
    from mathverify.certify.domain import DEFINEDNESS_UNDECIDED, ORIGIN
    from mathverify.normalize.parse import _differentiability
    x = sp.Symbol("x", real=True)
    assert _differentiability(sp.Piecewise((x**2, x < 1), (2*x, True)), x) == [sp.Ne(x, 1)]
    assert _differentiability(sp.Piecewise((x**2, x < 1), (2*x - 1, True)), x) == []
    assert _differentiability(x * sp.Abs(x), x) == []
    assert _differentiability(sp.atan2(x, -1), x) == [sp.Ne(x, 0)]
    assert _differentiability(sp.Abs(x - 2), x) == [sp.Ne(x, 2)]
    assert _differentiability(sp.Max(x, x**2), x) == [sp.Ne(x, 0), sp.Ne(x, 1)]
    # a family of zeros: undecided at each, never "no value"
    assert _differentiability(sp.Piecewise((x, sp.sin(x) > 0), (0, True)), x) == [sp.Contains(sp.sin(x), ORIGIN)]
    # beside a switch with no argument to read (floor), a Piecewise is undecided
    assert DEFINEDNESS_UNDECIDED in _differentiability(sp.floor(x) * sp.Piecewise((x, x < 0), (1, True)), x)


def test_an_undecided_zero_is_undecided_there_alone(monkeypatch):
    # a zero whose classification decides nothing: no value there is not proved, and it is no point without one
    from mathverify.certify import calculus as C
    from mathverify.certify.domain import ORIGIN
    from mathverify.normalize import parse as P
    monkeypatch.setattr(C, "_classify_kink", lambda *a, **k: None)
    P._SWITCH_CACHE.clear()
    x = sp.Symbol("x", real=True)
    try:
        conds = P._differentiability(x * sp.Abs(x), x)
        assert conds == [sp.Contains(x, ORIGIN)]
        assert _v(_se("diff(x*Abs(x), x) = 0"), _sol("EmptySet", "set")) != "CORRECT"
        assert _v(_se("diff(x*Abs(x), x) = 0"), _sol("{0}", "set")) != "INCORRECT"
    finally:
        P._SWITCH_CACHE.clear()


def test_a_closed_or_condition_is_read():
    from mathverify.certify.domain import DEFINEDNESS_UNDECIDED, closed_condition_undecided
    with sp.evaluate(False):
        at_zero = sp.Or(sp.Ne(0, 0), DEFINEDNESS_UNDECIDED)
        at_one = sp.Or(sp.Ne(1, 0), DEFINEDNESS_UNDECIDED)
        both = sp.And(sp.Ne(1, 0), sp.Ne(2, 0))
    assert closed_condition_undecided([at_zero]) is True
    assert closed_condition_undecided([at_one]) is False
    assert closed_condition_undecided([both]) is False


def test_the_piecewise_rule():
    from mathverify.certify.calculus import _piecewise_rule
    x = sp.Symbol("x", real=True)
    assert _piecewise_rule(sp.Piecewise((-x, x < 0), (x, True)), x, sp.Integer(0)) == "corner"
    assert _piecewise_rule(sp.Piecewise((x**2, x < 1), (2*x, True)), x, sp.Integer(1)) == "corner"
    assert _piecewise_rule(sp.Piecewise((x**2, x < 1), (2*x - 1, True)), x, sp.Integer(1)) == "value"
    assert _piecewise_rule(sp.Piecewise((x**2, x < -1), (x, x < 1), (x**2, True)), x, sp.Integer(1)) == "corner"
    assert _piecewise_rule(sp.Piecewise((x**2, x < -1), (x, x < 1), (x**2, True)), x, sp.Integer(-1)) == "corner"
    assert _piecewise_rule(sp.Piecewise((0, x < 0), (x**2, True)), x, sp.Integer(0)) == "value"
    # a branch with no derivative at the point: not this rule's (|x|'s SymPy derivative sign(0) = 0 would make the
    # corner of Piecewise((0, x < 0), (|x|, True)) a C1 junction)
    assert _piecewise_rule(sp.Piecewise((0, x < 0), (sp.sqrt(x), True)), x, sp.Integer(0)) is None
    assert _piecewise_rule(sp.Piecewise((0, x < 0), (sp.Abs(x), True)), x, sp.Integer(0)) is None
    # no branch at the point: no value there, f's own condition
    assert _piecewise_rule(sp.Piecewise((x, x < 0), (x + 1, x > 0)), x, sp.Integer(0)) is None


# YO-2: the tangent claim as written ------------------------------------------------------------------------------
@pytest.mark.parametrize("f,at,line", [
    ("x**2", "1", "y = 2*x - 1 + 0*log(x - 1)"), ("x**2", "1", "y = 2*x - 1 + 0*log(-x)"),
    ("x**2", "1", "y = 2*x - 1 + 0*sqrt(x - 5)"), ("sin(x)", "0", "y = x + 0*cot(x)"),
    ("exp(x)", "0", "y = x + 1 + 0*log(x)"), ("log(x)", "1", "y = (x**2 - x)/x"),
    ("x**3", "0", "y = 0*x + 0*sqrt(-x)"), ("sin(x)", "0", "y = x*sin(x)/sin(x)"),
    ("x**2", "1", "y = 2*x - 1 + 0*sqrt(y - 5)"), ("x**2", "1", "2*x - 1 + 0*sqrt(x - 5)"),
    ("x**2", "1", "y = 2*x - 1 + 0*sqrt(-1 - x**2)"),
])
def test_a_tangent_undefined_at_a_point_of_the_line_is_wrong(f, at, line):
    assert _v(_tan(f, at), _sol(line, "equation")) == "INCORRECT"


def test_a_tangent_condition_not_proved_on_the_line_is_not_certified():
    assert _v(_tan("x**2", "1"), _sol("y = 2*x - 1 + 0*log(sin(x))", "equation")) == "UNKNOWN"


@pytest.mark.parametrize("line", ["y = 2*x - 1", "2*x - y = 1", "y - 1 = 2*(x - 1)", "2*x - 1",
                                  "y = 2*x - 1 + 0*sqrt(x**2 + 1)", "y = 2*x - 1 + 0*log(x**2 + 1)"])
def test_a_tangent_defined_on_the_whole_line_is_certified(line):
    # control
    assert _v(_tan("x**2", "1"), _sol(line, "equation")) == "CORRECT"


# YO-3: a closed infinite argument written as a limit --------------------------------------------------------------
@pytest.mark.parametrize("expr,claim", [
    (r"\arctan\left(\lim_{x \to 0} \frac{1}{x^2}\right)", "pi/2"), (r"0 \cdot \sin\left(\lim_{x \to \infty} x\right)", "0"),
    (r"\frac{1}{\lim_{x \to 0} \frac{1}{x^2}}", "0"), (r"e^{-\lim_{x \to \infty} x}", "0"),
    (r"\arctan\left(\lim_{n \to \infty} 2^n\right)", "pi/2"), (r"\tanh\left(\lim_{x \to \infty} x\right)", "1"),
])
def test_an_infinite_limit_is_no_argument(expr, claim):
    assert _v(_ev(expr, vars_=[]), _sol(claim)) == "UNKNOWN"


def test_a_limit_with_no_value_is_no_number():
    from mathverify.certify.domain import _form_value_no_number
    x = sp.Symbol("x", real=True)
    assert _form_value_no_number(sp.Limit(sp.sin(x), x, sp.oo))           # SymPy's AccumBounds(-1, 1)
    assert _form_value_no_number(sp.Limit(1 / x**2, x, 0))
    assert not _form_value_no_number(sp.Limit(sp.sin(x) / x, x, 0))
    assert not _form_value_no_number(sp.Integer(2))


def test_a_step_with_an_infinite_limit_argument_is_not_verified():
    q = _ir("limit", {"expr": "exp(-1/x**2)", "var": "x", "to": "0"})
    r = verify(q, _sol("0", steps=[r"e^{-\lim_{x \to 0} \frac{1}{x^2}} = 0"]))
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    assert layer.evidence["steps"][-1]["status"] != "verified"


@pytest.mark.parametrize("expr,claim,verdict", [
    (r"\arctan\left(\lim_{x \to 0} (x + 1)\right)", "pi/4", "CORRECT"), (r"e^{\lim_{x \to 0} \frac{\sin x}{x}}", "E", "CORRECT"),
    (r"\frac{1}{\lim_{x \to 1} x}", "1", "CORRECT"), (r"\frac{1}{\lim_{x \to 1} x}", "2", "INCORRECT"),
    ("exp(-Sum(1/2**k, (k, 1, oo)))", "exp(-1)", "CORRECT"),
])
def test_a_finite_limit_argument_is_read_as_before(expr, claim, verdict):
    # control
    assert _v(_ev(expr, vars_=[{"name": "k", "domain": "integer"}]), _sol(claim)) == verdict


def test_an_infinite_limit_itself_is_a_value():
    # control
    assert _v(_ir("limit", {"expr": "1/x**2", "var": "x", "to": "0"}), _sol("oo")) == "CORRECT"


# YO-4: a pole over ℂ inside any operation -------------------------------------------------------------------------
@pytest.mark.parametrize("expr,claim", [
    ("Abs(1/0)", "oo"), ("acot(Abs(1/0))", "0"), ("exp(-Abs(1/(1 + I**2)))", "0"), ("acot(Abs(tan(pi/2)))", "0"),
    ("acot(Abs(log(0)))", "0"), ("acot(Abs(cot(0)))", "0"), (r"\cot^{-1}\left|\frac{1}{0}\right|", "0"),
])
def test_a_complex_pole_has_no_value_in_a_wrapper(expr, claim):
    assert _v(_ev(expr, vars_=[], dod="complex"), _sol(claim)) == "UNKNOWN"


@pytest.mark.parametrize("expr,claim", [
    ("sqrt(-4)", "2*I"), ("log(-1)", "I*pi"), ("Abs(1/(1 + I))", "sqrt(2)/2"), ("1/(2 + I**2)", "1"), ("tan(pi/4)", "1"),
])
def test_the_complex_reading_keeps_its_values(expr, claim):
    # control
    assert _v(_ev(expr, vars_=[], dod="complex"), _sol(claim)) == "CORRECT"


def test_complex_pole():
    from mathverify.certify.domain import complex_pole
    with sp.evaluate(False):                    # as written
        poles = [sp.Abs(sp.Pow(sp.Integer(0), -1)), sp.acot(sp.Abs(sp.tan(sp.pi / 2))),
                 sp.exp(-sp.Abs(sp.Pow(1 + sp.I**2, -1))), sp.log(sp.Integer(0)), sp.cot(sp.Integer(0))]
        values = [sp.Abs(sp.Pow(1 + sp.I, -1)), sp.log(sp.Integer(-1)), sp.sqrt(sp.Integer(-4)), sp.tan(sp.pi / 4)]
    assert all(complex_pole(e) for e in poles)
    assert not any(complex_pole(e) for e in values)


# YO-5 (record, controls) -------------------------------------------------------------------------------------------
def test_the_power_rule_with_an_integer_exponent_stays_correct():
    assert _v(_der("x**n", vars_=[X, NP]), _sol("n*x**(n - 1)", "expression")) == "CORRECT"
    assert _v(_der("x**(n + 1)", vars_=[X, NN]), _sol("(n + 1)*x**n", "expression")) == "CORRECT"
    assert _v(_der("x**n", vars_=[X, NP]), _sol("x**(n - 1)", "expression")) == "INCORRECT"
