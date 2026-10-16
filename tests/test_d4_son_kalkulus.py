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
    # control (a regression of c92f19d, the branch's first commit): |sin x| has a corner at each k*pi (sin(x) in ORIGIN): at pi/2 the condition, put in by at() unevaluated, is read
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
    # arg(-1 + I*x) jumps at 0 (read as atan2: discontinuous; left as arg, undecided): f' = -1 nowhere
    from mathverify.normalize.parse import _differentiability
    x = sp.Symbol("x", real=True)
    assert _differentiability(sp.arg(-1 + sp.I * x), x) == [sp.Ne(x, 0)]
    q = _se("diff(f(x), x) = -1", "arg(-1 + I*x)")
    assert _v(q, _sol("EmptySet", "set")) == "CORRECT"
    assert _v(q, _sol("{0}", "set")) == "INCORRECT"


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


# The additions of the evening (kararlar "EK (16 Ekim akşam)"): G2RK-13/14/15, SON-G3-RK-1/2/4/9 -----------------------
XP = {"name": "x", "domain": "real", "constraints": ["x > 0"]}
NP2 = {"name": "n", "domain": "positive_integer", "constraints": ["n >= 2"]}
NP3 = {"name": "n", "domain": "positive_integer", "constraints": ["n >= 3"]}


def _anti(f, vars_=None):
    return _ir("antiderivative", {"integrand": f, "var": "x"}, (), vars_, "expression")


def _ext(f, which, interval):
    return _ir("extremum", {"f": f, "var": "x", "which": which, "interval": interval})


def _derk(f, order, vars_):
    return _ir("derivative", {"f": f, "var": "x", "order": order}, (), vars_, "expression")


@pytest.mark.parametrize("f,claim", [
    ("cbrt(x)", "1/(3*cbrt(x)**2)"), ("cbrt(x)", "1/(3*cbrt(x**2))"), ("cbrt(x)", "cbrt(x)/(3*x)"),
    ("cbrt(2*x + 1)", "2/(3*cbrt((2*x + 1)**2))"), ("cbrt(x)**4", "4*cbrt(x)/3"), ("root(x, 3)", "1/(3*root(x, 3)**2)"),
])
def test_a_real_root_has_no_derivative_at_its_zero_and_its_textbook_derivative_elsewhere(f, claim):
    # G2RK-13: sign(u)*|u|**(1/3) at a simple zero of u is an infinite slope, read exactly (`_real_root_rule`)
    assert _v(_der(f), _sol(claim, "expression")) == "CORRECT"


def test_a_wrong_real_root_derivative_stays_wrong():
    # control
    assert _v(_der("cbrt(x)"), _sol("1/(3*cbrt(x))", "expression")) == "INCORRECT"
    assert _v(_der("cbrt(x)"), _sol("cbrt(x)**2/3", "expression")) == "INCORRECT"


def test_the_real_root_rules_slope_is_read_where_sympys_formula_has_none():
    # x*∛x has f'(0) = 0 (g(0) = 0): read by the rule, where SymPy's formula holds a DiracDelta; the limits decided nothing
    assert _v(_der("x*cbrt(x)"), _sol("4*cbrt(x)/3", "expression")) == "CORRECT"
    assert _v(_der("x**2*cbrt(x)"), _sol("7*x*cbrt(x)/3", "expression")) == "CORRECT"
    # a claim with another value at 0 alone: wrong there
    assert _v(_der("x*cbrt(x)"), _sol("4*cbrt(x)/3 + 1 - Abs(sign(x))", "expression")) == "INCORRECT"


def test_the_real_root_rule():
    from mathverify.certify.calculus import _real_root_rule, abs_form, switch_arguments
    x = sp.Symbol("x", real=True)
    third = sp.Rational(1, 3)

    def rule(f, p):
        sw = switch_arguments(f, x)
        u = next(s_ for s_ in sw if s_.subs(x, p) == 0)
        return _real_root_rule(abs_form(f), x, sp.sympify(p), u, sw, [])
    assert rule(sp.sign(x) * sp.Abs(x) ** third, 0) == "corner"                  # ∛x: an infinite slope
    assert rule(1 + sp.sign(x - 1) * sp.Abs(x - 1) ** third, 1) == "corner"
    assert rule(sp.sign(x) ** 2 * sp.Abs(x) ** (2 * third), 0) == "corner"        # ∛(x²): a cusp
    assert rule(x**2 * sp.sign(x) * sp.Abs(x) ** third, 0) == "value"             # g(0) = 0
    assert rule(sp.sign(x) * sp.Abs(x) ** (4 * third), 0) == "value"              # r > 1
    assert rule(sp.sign(x) ** 2 * sp.Abs(x), 0) == "corner"                       # |x|


@pytest.mark.parametrize("f,claim", [("cbrt(x)", "1/(3*x**(2/3))"), ("cbrt(x)", "x**(-2/3)/3"),
                                     ("cbrt(x**2)", "2/(3*x**(1/3))"), ("x*cbrt(x)", "4*x**(1/3)/3")])
def test_a_claims_odd_root_convention_is_read_on_the_declared_region(f, claim):
    # G2RK-14: x > 0 declared, x**(2/3) has its one value there
    assert _v(_der(f, vars_=[XP]), _sol(claim, "expression")) == "CORRECT"


def test_a_claims_odd_root_convention_off_the_declared_region():
    # controls: a wrong claim stays wrong; on all of ℝ the claim's principal value is a convention for x < 0
    assert _v(_der("cbrt(x)", vars_=[XP]), _sol("1/(3*x**(1/3))", "expression")) == "INCORRECT"
    assert _v(_der("cbrt(x)"), _sol("1/(3*x**(2/3))", "expression")) == "UNKNOWN"


@pytest.mark.parametrize("f,which,interval,claim,verdict", [
    ("x**(1/3)*(1 - x)", "max", "[0, 1]", "3/(4*4**(1/3))", "CORRECT"), ("x**(2/3)", "max", "[1, 8]", "4", "CORRECT"),
    ("x**(1/3) - x/3", "max", "[0, 8]", "2/3", "CORRECT"), ("x**(1/3) - x/3", "min", "[0, 8]", "-2/3", "CORRECT"),
    ("x**(2/3)*(5 - x)", "max", "[0, 5]", "3*cbrt(4)", "CORRECT"), ("x**(1/3)*(1 - x)", "max", "[0, 1]", "1/2", "INCORRECT"),
    ("x**pi", "max", "[1, 2]", "2**pi", "CORRECT"), ("x**pi", "min", "[1, 2]", "1", "CORRECT"),
    ("x**sqrt(2)", "max", "[1, 2]", "2**sqrt(2)", "CORRECT"), ("x**pi", "max", "[1, 2]", "4", "INCORRECT"),
    ("x**x", "max", "[1, 2]", "4", "CORRECT"),
])
def test_the_extremum_of_a_fractional_or_irrational_power(f, which, interval, claim, verdict):
    # G2RK-15: an odd root's base not negative on the interval; f strictly monotone, proved by intervals
    assert _v(_ext(f, which, interval), _sol(claim)) == verdict


def test_strict_monotonicity_by_intervals():
    from mathverify.certify.extremum import _strictly_monotone
    x = sp.Symbol("x", real=True)
    assert _strictly_monotone(x**sp.pi, x, 1, 2) == 1
    assert _strictly_monotone(-x**3 - x, x, -1, 1) == -1
    assert _strictly_monotone(x**sp.pi, x, 0, 1) is None          # not analytic at 0
    assert _strictly_monotone(sp.sin(x), x, 0, sp.pi) is None      # f' changes sign


@pytest.mark.parametrize("q,claim,verdict", [
    (_der("x**pi"), "pi*x**(pi - 1)", "CORRECT"), (_der("x**pi"), "x**(pi - 1)", "INCORRECT"),
    (_der("x**sqrt(2)"), "sqrt(2)*x**(sqrt(2) - 1)", "CORRECT"), (_der("(2*x + 1)**pi"), "2*pi*(2*x + 1)**(pi - 1)", "CORRECT"),
    (_anti("x**pi"), "x**(pi + 1)/(pi + 1)", "CORRECT"), (_anti("x**sqrt(2)"), "x**(sqrt(2) + 1)/(sqrt(2) + 1)", "CORRECT"),
])
def test_an_irrational_power_on_an_unconstrained_variable(q, claim, verdict):
    # SON-G3-RK-1: the convention point 0 of x**pi is an end of its domain, never read by a derivative function
    assert _v(q, _sol(claim, "expression")) == verdict


def test_a_convention_on_more_than_the_ends_of_the_domain_still_stops_the_gate():
    # controls (the decision reads finitely many ends only): x**x fails on all of x <= 0, (x**2)**pi at the interior 0
    assert _v(_der("x**x"), _sol("x**x*(log(x) + 1)", "expression")) == "UNKNOWN"
    assert _v(_der("(x**2)**pi"), _sol("2*pi*x*(x**2)**(pi - 1)", "expression")) == "UNKNOWN"


@pytest.mark.parametrize("f,order,vars_,claim,verdict", [
    ("x**n", 2, [X, NP2], "n*(n - 1)*x**(n - 2)", "CORRECT"),
    ("x**n", 3, [X, NP3], "n*(n - 1)*(n - 2)*x**(n - 3)", "CORRECT"),
    ("(x + 1)**n", 2, [X, NP2], "n*(n - 1)*(x + 1)**(n - 2)", "CORRECT"),
    ("x**n", 2, [X, NP2], "n**2*x**(n - 2)", "INCORRECT"),
    # control: with n = 1 allowed the claim is 0*x**(-1), undefined at 0 where f'' = 0 exists
    ("x**n", 2, [X, NP], "n*(n - 1)*x**(n - 2)", "UNKNOWN"),
])
def test_an_integer_exponent_bounded_below_by_a_constraint(f, order, vars_, claim, verdict):
    # SON-G3-RK-2: n >= 2 read on the claim's exponent (n = 2 + k, k >= 0)
    assert _v(_derk(f, order, vars_), _sol(claim, "expression")) == verdict


@pytest.mark.parametrize("q,claim,verdict", [
    (_der("log(sin(x))", "pi/4"), "1", "CORRECT"), (_der("sqrt(sin(x))", "pi/6"), "sqrt(6)/4", "CORRECT"),
    (_der("sqrt(cos(x))", "0"), "0", "CORRECT"), (_der("log(cos(x))", "pi/3"), "-sqrt(3)", "CORRECT"),
    (_der("log(tan(x))", "pi/4"), "2", "CORRECT"), (_der("log(sin(x))", "pi/4"), "0", "INCORRECT"),
    (_ir("limit", {"expr": "log(cos(x))/x**2", "var": "x", "to": "0"}), "-1/2", "CORRECT"),
    (_ir("limit", {"expr": "log(cos(x))/x**2", "var": "x", "to": "0"}), "1/2", "INCORRECT"),
    (_ir("limit", {"expr": "log(1 + sin(x))/x", "var": "x", "to": "0"}), "1", "CORRECT"),
])
def test_a_trigonometric_condition_holding_strictly_at_the_point(q, claim, verdict):
    # SON-G3-RK-9: sin(x) > 0 at pi/4, continuous: it holds on a neighbourhood (`calculus.strict_at`)
    assert _v(q, _sol(claim)) == verdict


def test_a_trigonometric_condition_failing_at_the_point_is_still_undecided():
    # control: x*log(sin(x)) at 0+ (sin(0) = 0): no strict reading at the point
    q = _ir("limit", {"expr": "x*log(sin(x))", "var": "x", "to": "0", "side": "+"})
    assert _v(q, _sol("0")) == "UNKNOWN"


@pytest.mark.parametrize("kind,text,claim,verdict", [
    ("domain_of", "1/(x - 2)", "R - {2}", "CORRECT"), ("domain_of", "1/(x - 2)", r"\mathbb{R} - \{2\}", "CORRECT"),
    ("domain_of", "1/(x - 2)", r"\mathbb{R} \setminus \{2\}", "CORRECT"), ("domain_of", "1/(x - 2)", "ℝ∖{2}", "CORRECT"),
    ("domain_of", "1/(x - 2)", r"(-\infty, 2) \cup (2, \infty)", "CORRECT"),
    ("domain_of", "log(x**2 - 1)", r"(-\infty, -1) \cup (1, \infty)", "CORRECT"),
    ("domain_of", "1/(x - 2)", "R - {3}", "INCORRECT"),
    ("solve_inequality", "x**2 - 5*x + 6 > 0", r"(-\infty, 2) \cup (3, \infty)", "CORRECT"),
    ("solve_inequality", "x**2 - 5*x + 6 > 0", "R - [2, 3]", "CORRECT"),
    ("solve_inequality", "x**2 - 5*x + 6 > 0", r"(-\infty, 2) \cup (4, \infty)", "INCORRECT"),
])
def test_textbook_set_notation(kind, text, claim, verdict):
    # SON-G3-RK-4: ℝ minus a set and LaTeX's \cup
    params = {"expr": text, "var": "x"} if kind == "domain_of" else {"inequality": text, "var": "x"}
    q = _ir(kind, params, (), None, "set" if kind == "domain_of" else "interval")
    assert _v(q, _sol(claim, "set" if kind == "domain_of" else "interval")) == verdict


def test_set_difference_reading():
    from mathverify.normalize.parse import parse_set_str
    two = sp.Union(sp.Interval.open(-sp.oo, 2), sp.Interval.open(2, sp.oo))
    for s in ("R - {2}", r"\mathbb{R} - \{2\}", r"\mathbb{R} \setminus \{2\}", "ℝ∖{2}", "Reals - {2}"):
        assert parse_set_str(s) == two
    assert parse_set_str("R - [2, 3]") == sp.Union(sp.Interval.open(-sp.oo, 2), sp.Interval.open(3, sp.oo))
    assert parse_set_str("R") == sp.S.Reals                                     # control
