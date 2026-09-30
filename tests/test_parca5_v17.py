"""V17 (30 Sep 2026, DECISIONS §74; `franklin`'s completeness audit): two false accepts and a test gap.

(1) The family parameter of a trig general solution took the IR's declaration of k/n/m: with k a
    positive integer, {Abs(k)*pi} was read as {k*pi} and then spread over every integer, so the
    nonnegative multiples of pi alone were certified as the solutions of sin x = 0.
(2) A derivative (or an indefinite integral) in a variable declared an integer: SymPy applies the
    declaration to the function first (sin(pi*n) = 0), so with n a positive integer diff(sin(pi*n), n)
    was 0 and 0 was certified at n = 2 (the derivative is pi*cos(pi*n), pi there), pi refuted, and the
    step "diff(sin(pi*n), n) = 0" verified. Such an operation is no longer read (UNKNOWN); at()/Subs and
    ranged binders give the variable a real (or assumption-free) dummy and stay readable. The LaTeX
    reading follows the same rule by name.
(3) `equiv.sets.unify_endpoints` refuses an endpoint pair it cannot decide; no test held it (the U04
    mutant, which equates such a pair, survived the whole suite).
(4) Two more guards of the §73 port no test held (the mutations P04 and L03 of
    denetim/2026-09-30/parca5/mutasyon.py survived): a point binder's argument passed by keyword, and
    the undirected limit at the closed end of a positive variable.
Measured on the code before the change (b788caa): 92 of these 160 tests fail; the other 68 are
controls (right families, derivatives at a point, a real variable) and the pins of U04, P04 and L03,
which hold there and fail on their mutants.
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.normalize.parse import ParseError, _SAFE_NAMES, parse_as_written, parse_expr_str
from mathverify.verifier import verify


def _ir(kind, params, vars_=(), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [dict(s, text="") for s in steps]}


def _step(i, kind, claim):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": []}


def _step_statuses(r):
    return [s["status"] for layer in r.layers if layer.layer == "steps.refute"
            for s in layer.evidence.get("steps", [])]


# ---------------------------------------------------------------------------- (1) trig family parameter
X = {"name": "x", "domain": "real"}


def _trig(eq, par=None, dom=None, interval=None):
    p = {"equation": eq, "var": "x"}
    if interval:
        p["interval"] = interval
    return _ir("trig_solve", p, [X] + ([{"name": par, "domain": dom}] if dom else []), shape="set")


NONNEG_INT = ("positive_integer", "natural", "nonneg_integer")
# (equation, parameter, claim, claim kind): each family gives the nonnegative multiples only
HALF_FAMILIES = [
    ("sin(x) = 0", "k", "{Abs(k)*pi}", "set"),
    ("sin(x) = 0", "k", "{sqrt(k**2)*pi}", "set"),
    ("sin(x) = 0", "k", "Abs(k)*pi", "value"),
    ("cos(x) = 1", "k", "{2*pi*Abs(k)}", "set"),
    ("cos(x) = 1", "n", "{2*pi*sqrt(n**2)}", "set"),
    ("cos(x) = 1", "n", "{2*pi*Max(n, 0)}", "set"),
    ("cos(x) = 1", "m", "{2*pi*Abs(m)}", "set"),
    ("sin(x) = 1/2", "k", "{pi/6 + 2*Abs(k)*pi, 5*pi/6 + 2*Abs(k)*pi}", "set"),
]


@pytest.mark.parametrize("dom", NONNEG_INT)
@pytest.mark.parametrize("eq,par,claim,kind", HALF_FAMILIES)
def test_a_family_of_nonnegative_multiples_is_not_the_general_solution(dom, eq, par, claim, kind):
    assert verify(_trig(eq, par, dom), _sol(claim, kind)).verdict != "CORRECT"


@pytest.mark.parametrize("dom", NONNEG_INT + ("integer", "real", None))
@pytest.mark.parametrize("eq,par,claim,verdict", [
    ("sin(x) = 0", "k", "{k*pi}", "CORRECT"),
    ("cos(x) = 1", "k", "{2*k*pi}", "CORRECT"),
    ("cos(x) = 1", "n", "{2*n*pi}", "CORRECT"),
    ("sin(x) = 1/2", "k", "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", "CORRECT"),
    ("sin(x) = 0", "k", "{2*k*pi}", "INCORRECT"),
])
def test_the_family_parameter_is_an_integer_whatever_the_ir_declares(dom, eq, par, claim, verdict):
    assert verify(_trig(eq, par, dom), _sol(claim, "set")).verdict == verdict


@pytest.mark.parametrize("dom", ("integer", "real", None))
def test_an_absolute_family_stays_unread_where_it_was(dom):
    assert verify(_trig("sin(x) = 0", "k", dom), _sol("{Abs(k)*pi}", "set")).verdict == "UNKNOWN"


def test_m_is_a_family_parameter_only_when_declared():
    assert verify(_trig("cos(x) = 1", "m", "positive_integer"), _sol("{2*m*pi}", "set")).verdict == "CORRECT"
    assert verify(_trig("cos(x) = 1"), _sol("{2*m*pi}", "set")).verdict == "UNKNOWN"   # undeclared, as before


def test_a_window_reads_the_claim_as_before():
    ir = _trig("sin(x) = 0", "k", "positive_integer", "[0, 2*pi)")
    assert verify(ir, _sol("{0, pi}", "set")).verdict == "CORRECT"
    assert verify(ir, _sol("{pi}", "set")).verdict == "INCORRECT"
    # on a window there is no family: k is the problem's symbol, with its declaration (k > 0)
    assert verify(ir, _sol("{0, Abs(k)*pi/k}", "set")).verdict == "CORRECT"


# ---------------------------------------------------------------------------- (2) calculus in an integer
N = sp.Symbol("n", integer=True, positive=True)
XR = sp.Symbol("x", real=True)


def _ns(n=N):
    return dict(_SAFE_NAMES, n=n, x=XR)


def _step_ns(n=N):
    from mathverify.steps.deterministic import _step_namespace
    return _step_namespace(_ns(n))


INTEGER_CALCULUS = [
    "diff(sin(pi*n), n)", "Derivative(sin(pi*n), n)", "diff(cos(pi*n), n)", "diff(sin(pi*n), (n, 2))",
    "diff(sin(pi*n))",                     # no variable: SymPy takes the body's only symbol
    "diff(sin(pi*n), n + 0)", "diff(sin(pi*n), 1*n)",
    "diff(exp(2*x), x, n)",                # a second variable, not an order
    "x*diff(sin(pi*n), n)", "1 + Derivative(cos(pi*n), [n, 1])",
    "Limit(diff(sin(pi*n), n), n, oo)",    # a limit at oo keeps the integer: a sequence
    "Integral(sin(pi*n), n)", "integrate(sin(pi*n), n)", "Integral(sin(pi*n), (n,))", "integrate(sin(pi*n))",
]


@pytest.mark.parametrize("n", [N, sp.Symbol("n", integer=True), sp.Symbol("n", integer=True, nonnegative=True)])
@pytest.mark.parametrize("text", INTEGER_CALCULUS)
def test_calculus_in_a_variable_declared_an_integer_is_not_read(text, n):
    with pytest.raises(ParseError):
        parse_expr_str(text, _ns(n))
    with pytest.raises(ParseError):
        parse_expr_str(text, _step_ns(n))
    if not text.startswith("Limit("):
        # the as-written reading judges no operation inside a binder (the normal reading does, with
        # the binder's variable), see test_the_as_written_reading_keeps_the_conditions_of_a_bound_derivative
        assert parse_as_written(text, _ns(n)) is None


@pytest.mark.parametrize("text,value", [
    ("at(diff(sin(pi*n), n), n, 1)", -sp.pi),          # at() binds a real dummy
    ("at(diff(cos(pi*n), n), n, 1/2)", -sp.pi),
    ("Sum(diff(sin(pi*n), n), (n, 1, 3))", -sp.pi),     # a ranged index is assumption-free while read
    ("Integral(sin(pi*n), (n, 0, 1))", 2 / sp.pi),      # definite: the range binds n
    ("at(integrate(sin(pi*n), n), n, 1)", 1 / sp.pi),
])
def test_a_bound_variable_is_differentiated_as_a_real_one(text, value):
    e = parse_expr_str(text, _ns())
    assert sp.simplify(e.doit() - value) == 0


def test_other_derivatives_near_an_integer_stay_readable():
    ns = _ns()
    assert sp.simplify(parse_expr_str("diff(x**n, x)", ns) - N * XR**(N - 1)) == 0       # in x, an integer power
    assert isinstance(parse_expr_str("diff(exp(2*x), (x, n))", ns), sp.Derivative)       # an order n, not a variable
    assert parse_expr_str("diff(x*sin(pi*n), x)", ns) == 0                             # sin(pi*n) = 0 is true here
    nr = sp.Symbol("n", real=True)
    assert parse_expr_str("diff(sin(pi*n), n)", _ns(nr)) == sp.pi * sp.cos(sp.pi * nr)


@pytest.mark.parametrize("text", [
    r"\frac{d}{dn} \sin(\pi n)",                          # was right (Subs in latex2sympy's own n)
    r"\lim_{n \to \infty} \frac{d}{dn} \sin(\pi n)",      # was 0: the limit's integer n reached it
    r"\sum_{n=1}^{3} \frac{d}{dn} \sin(\pi n)",           # was 0 (it is -pi): the sum's integer index
    r"\int \sin(\pi n) \, dn",
    r"\frac{d^2}{dn^2} \left(n \sin(\pi n)\right)",       # d**2*n*sin(pi*n)/dn**2 folded to 0 (2*pi there)
])
def test_latex_calculus_in_a_variable_declared_an_integer_is_not_read(text):
    with pytest.raises(ParseError):
        parse_expr_str(text, _ns())
    with pytest.raises(ParseError):
        parse_expr_str(text, _step_ns())


def test_latex_calculus_near_an_integer_stays_readable():
    ns = _ns()
    assert sp.simplify(parse_expr_str(r"\int_0^1 \sin(\pi n) \, dn", ns).doit() - 2 / sp.pi) == 0
    assert sp.simplify(parse_expr_str(r"\frac{d}{dx} x^{n}", ns).doit() - N * XR**(N - 1)) == 0
    assert parse_expr_str(r"\frac{d}{dx} \left(x \sin(\pi n)\right)", ns).doit() == 0
    nr = sp.Symbol("n", real=True)
    e = parse_expr_str(r"\frac{d}{dn} \sin(\pi n)", _ns(nr))
    assert sp.simplify(e.doit() - sp.pi * sp.cos(sp.pi * nr)) == 0


def test_the_as_written_reading_keeps_the_conditions_of_a_bound_derivative():
    from mathverify.certify.domain import definedness_conditions
    w = parse_as_written("at(diff(sqrt(n), n), n, 0)", _ns())
    assert w is not None and sp.false in definedness_conditions(w, None)
    assert parse_as_written("at(diff(Abs(n - 1), n), n, 1)", _ns()) is not None
    assert parse_as_written("Limit(diff(sin(pi*n), n), n, oo)", _ns()) is not None   # the normal reading refuses
    # a definite integral binds a range, in both readings
    assert parse_as_written("Integral(sin(pi*n), (n, 0, 1))", _ns()) is not None
    assert parse_as_written("integrate(1/n, (n, 1, 2))", _ns()) is not None


NP = [{"name": "n", "domain": "positive_integer"}]
XNP = [X] + NP


def _ev(expr, vars_=NP, givens=("n = 2",)):
    return _ir("evaluate", {"expr": expr}, vars_, givens)


@pytest.mark.parametrize("ir,claim,kind", [
    (_ev("diff(sin(pi*n), n)"), "0", "value"),
    (_ev("diff(sin(pi*n), n)"), "pi", "value"),
    (_ev("Derivative(sin(pi*n), n)"), "0", "value"),
    (_ev("Derivative(sin(pi*n), n)"), "pi", "value"),
    (_ev("diff(cos(pi*n), n)"), "I*pi", "value"),
    (_ev("diff(cos(pi*n), n)"), "0", "value"),
    (_ev("diff(sin(pi*n), n)", [{"name": "n", "domain": "integer"}]), "0", "value"),
    (_ev("Limit(diff(sin(pi*n), n), n, oo)", NP, ()), "0", "value"),
    (_ir("limit", {"expr": "diff(sin(pi*n), n)", "var": "n", "to": "oo"}, NP), "0", "value"),
    (_ir("derivative", {"f": "x*diff(sin(pi*n), n)", "var": "x"}, XNP, (), "expression"), "0", "expression"),
    (_ir("derivative", {"f": "x*diff(sin(pi*n), n)", "var": "x"}, XNP, (), "expression"), "pi*(-1)**n",
     "expression"),
    (_ir("limit", {"expr": "x*diff(sin(pi*n), n)", "var": "x", "to": "1"}, XNP), "0", "value"),
    (_ev(r"\frac{d}{dn} \sin(\pi n)"), "pi", "value"),
    (_ev(r"\lim_{n \to \infty} \frac{d}{dn} \sin(\pi n)", NP, ()), "0", "value"),
    (_ev(r"\sum_{n=1}^{3} \frac{d}{dn} \sin(\pi n)", NP, ()), "0", "value"),
    (_ev(r"\frac{d^2}{dn^2} \left(n \sin(\pi n)\right)"), "0", "value"),
])
def test_a_task_that_differentiates_in_an_integer_is_not_decided(ir, claim, kind):
    assert verify(ir, _sol(claim, kind)).verdict == "UNKNOWN"


@pytest.mark.parametrize("kind,claim", [
    ("compute", "diff(sin(pi*n), n) = 0"), ("eq", "Derivative(sin(pi*n), n) = 0"),
    ("compute", "Integral(sin(pi*n), n) = 7"), ("compute", "integrate(sin(pi*n), n) = 0"),
    ("compute", "diff(sin(pi*n), n) = 5"),
])
def test_a_step_that_differentiates_in_an_integer_is_not_verified(kind, claim):
    r = verify(_ev("n**2"), _sol("4", steps=[_step(1, kind, claim)]))
    assert _step_statuses(r) and _step_statuses(r)[0] != "verified"
    assert r.verdict != "CORRECT"


@pytest.mark.parametrize("ir,claim,verdict", [
    (_ev("at(diff(sin(pi*n), n), n, 1)", NP, ()), "-pi", "CORRECT"),
    (_ev("at(diff(sin(pi*n), n), n, 1)", NP, ()), "0", "INCORRECT"),
    (_ev("diff(sin(pi*n), n)", [{"name": "n", "domain": "real"}]), "pi", "CORRECT"),
    (_ev("diff(sin(pi*n), n)", [{"name": "n", "domain": "real"}]), "0", "INCORRECT"),
    (_ev("diff(sin(pi*n), n)", [{"name": "n"}]), "pi", "CORRECT"),
    (_ev(r"\frac{d}{dn} \sin(\pi n)", [{"name": "n", "domain": "real"}]), "pi", "CORRECT"),
    (_ev(r"\frac{d}{dn} \sin(\pi n)", [{"name": "n", "domain": "real"}]), "0", "INCORRECT"),
    (_ir("derivative", {"f": "sin(pi*n)", "var": "n", "at": "2"}, NP), "pi", "UNKNOWN"),   # task level, §73 (e)
])
def test_derivatives_at_a_point_and_in_a_real_variable_are_decided_as_before(ir, claim, verdict):
    assert verify(ir, _sol(claim)).verdict == verdict


@pytest.mark.parametrize("claim,status,verdict", [
    ("at(diff(sin(pi*n), n), n, 1) = -pi", "verified", "CORRECT"),
    ("at(diff(sin(pi*n), n), n, 1) = 0", "refuted", "INCORRECT"),
])
def test_a_step_with_a_derivative_at_a_point_is_checked_as_before(claim, status, verdict):
    r = verify(_ev("n**2"), _sol("4", steps=[_step(1, "compute", claim)]))
    assert _step_statuses(r) == [status] and r.verdict == verdict


# ---------------------------------------------------------------------------- (3) undecided endpoints
# sqrt(9 + exp(-10000)) - 3 is about 1.7e-4344: no exact check decides it against 3, and 20 digits
# call the two equal. Equating them would read (-oo, 3) U (R', oo) as the set without 3, although it
# also leaves out (3, R'].
R_NEAR = "sqrt(9 + exp(-10000))"


def test_unify_endpoints_refuses_an_undecided_pair():
    from mathverify.equiv.sets import EndpointsIncomparable, unify_endpoints
    r = parse_expr_str(R_NEAR)
    with pytest.raises(EndpointsIncomparable):
        unify_endpoints([sp.Interval.open(-sp.oo, 3), sp.Interval.open(r, sp.oo)])


@pytest.mark.parametrize("claim,verdict", [
    (f"(-oo, 3) U ({R_NEAR}, oo)", "UNKNOWN"),
    (f"Union(Interval.open(-oo, 3), Interval.open({R_NEAR}, oo))", "UNKNOWN"),
    ("(-oo, 3) U (3, oo)", "CORRECT"),
])
def test_a_set_with_an_undecided_endpoint_pair_is_not_read(claim, verdict):
    ir = _ir("domain_of", {"expr": "1/(x - 3)", "var": "x"}, [{"name": "x"}], shape="set")
    assert verify(ir, _sol(claim, "set")).verdict == verdict


def test_a_step_with_an_undecided_endpoint_pair_is_not_verified():
    ir = _ir("solve_inequality", {"var": "x"}, [{"name": "x"}], ["x > 0"], "interval")
    r = verify(ir, _sol("(0, oo)", "interval", [_step(1, "eq", f"Or(x < 3, x > {R_NEAR})")]))
    assert _step_statuses(r) and _step_statuses(r)[0] != "verified"


# ---------------------------------------------------------------------------- (4) §73 code the mutations hold
@pytest.mark.parametrize("text", ["at(sqrt(x**2), v=x, val=-1)", "at(sqrt(x**2), x, val=-1)",
                                  "Limit(sqrt(x**2)/x, v=x, p=-oo)", "Limit(sqrt(x**2)/x, x, p=-oo)"])
def test_a_point_binder_argument_passed_by_keyword_is_refused(text):
    # A keyword named like a problem variable passes the text check; the renaming sees positional
    # arguments only, so the body kept the declared x > 0: sqrt(x**2) at -1 was -1 and the limit at -oo
    # Limit(1, x, -oo). The mutation that drops the keyword refusal (P04) survived every V14 test.
    ns = dict(_SAFE_NAMES, x=sp.Symbol("x", positive=True), v=sp.Symbol("v"), val=sp.Symbol("val"),
              p=sp.Symbol("p"))
    with pytest.raises(ParseError):
        parse_expr_str(text, ns)


XPR = [{"name": "x", "domain": "positive_real"}]


@pytest.mark.parametrize("claim,verdict", [("0", "CORRECT"), ("-1", "INCORRECT")])
def test_an_undirected_limit_at_the_closed_end_is_read_from_inside(claim, verdict):
    # x > 0: at 0 the limit is the right-hand one (`_domain_end_limits`); two-sided, floor has none. The
    # mutation that keeps it two-sided (L03) survived every V14 test (x*log(x) has 0 from both sides).
    assert verify(_ev("Limit(floor(x), x, 0)", XPR, ()), _sol(claim)).verdict == verdict


def test_an_undirected_limit_step_at_the_closed_end_is_read_from_inside():
    r = verify(_ev("x", XPR, ("x = 2",)), _sol("2", steps=[_step(1, "compute", "Limit(floor(x), x, 0) = 0")]))
    assert _step_statuses(r) == ["verified"] and r.verdict == "CORRECT"
