"""V16's definedness and step items (30 Sep 2026, part v-b B; DECISIONS §73 "Açık kalanlar", HANDOFF V16).

(1) A binder's variable kept the IR's declaration in the first condition loop (`domain._outer_nodes`):
    with x declared positive, sqrt(-x) in ∫_{-1}^{0} sqrt(-x) dx gave the closed condition `false`,
    the expression was read as defined nowhere, the empty solution set certified and the right answer
    {-log 6} of exp(-y) = 6 + 0·∫… refuted. The body is now read on assumption-free dummies; its
    conditions on the bound variable are decided over the binder's range (`_binder_conditions`).
(2) The derivative (no point), the antiderivative and the definite integral read only the OPEN
    written conditions of their function: x + Σ_{k=-1}^{1} k/k (defined nowhere) had the derivative 1
    certified. And a parametric integral's improper point was "the value's business" though its
    derivative is taken by the fundamental theorem without any value: diff(∫_1^x dt/t, x) = -1 had
    {-1} certified (N1's side finding). Such a function makes the problem undefined as written, and
    an improper point the bounds may reach leaves the integral undecided.
(3) A constant whose rationality no check decides (pi + E): the value x + gcd(x, 2) - gcd(2, x) there
    and the root pi + E were certified (`in_domain` None read as inside).
(4) A step undefined as written at the point the premises allow was verified (x/x = 1 under x = 0),
    an extra term undefined in another variable was ignored in a simplification's claim (x + log(y) -
    log(y) for x; gcd, n!, sqrt and log alike), and an expression defined nowhere was simplified.
Measured on the code before the change (20d4edf): 52 of these 75 tests fail; the other 23 are controls
(defined functions, decided memberships, steps defined at the premises' point, simplifications on the
expression's own domain) and pins that hold there too (a sum undefined on its own range).
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.verifier import verify


def _ir(kind, params, vars_=(), givens=(), shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def _sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [dict(s, text="") for s in steps]}


def _step(i, kind, claim):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": []}


def _steps(r):
    return [(s["status"], s.get("reason")) for layer in r.layers if layer.layer == "steps.refute"
            for s in layer.evidence.get("steps", [])]


def _v(ir, sol):
    return verify(ir, sol).verdict


# ------------------------------------------------------------------ (1) the binder keeps the declaration
XP = [{"name": "x", "domain": "positive_real"}, {"name": "y", "domain": "real"}]
KP = [{"name": "k", "domain": "positive_integer"}, {"name": "y", "domain": "real"}]


def _eq_y(e, v=XP):
    return _ir("solve_equation", {"equation": e, "var": "y"}, v, shape="set")


BOUND_OUTSIDE = [
    # (equation, variables, right answer, its verdict now)
    ("exp(-y) = 6 + 0*Integral(sqrt(-x), (x, -1, 0))", XP, "{-log(6)}", "CORRECT"),
    ("y + Integral(sqrt(-x), (x, -1, 0)) = 2/3", XP, "{0}", "CORRECT"),
    ("y + Sum(log(-x), (x, -3, -1)) = log(6)", XP, "{0}", None),
    ("y + Limit(log(-x), x, -1) = 1", XP, "{1}", "CORRECT"),
    ("y + Sum(sqrt(-k), (k, -2, -1)) = 1 + sqrt(2)", KP, "{0}", "CORRECT"),
]


@pytest.mark.parametrize("eq,vars_,right,now", BOUND_OUTSIDE)
def test_a_binder_outside_the_declared_domain_is_not_undefined(eq, vars_, right, now):
    assert _v(_eq_y(eq, vars_), _sol("{}", "set")) != "CORRECT"
    got = _v(_eq_y(eq, vars_), _sol(right, "set"))
    assert got != "INCORRECT"
    if now:
        assert got == now


def test_the_value_of_a_binder_outside_the_declared_domain():
    ir = _ir("evaluate", {"expr": "Integral(sqrt(-x), (x, -1, 0))"}, XP)
    assert _v(ir, _sol("2/3")) == "CORRECT"
    assert _v(ir, _sol("0")) == "INCORRECT"


def test_the_body_is_read_on_plain_dummies():
    from mathverify.certify.domain import definedness_conditions
    x = sp.Symbol("x", positive=True)
    y = sp.Symbol("y", real=True)
    with sp.evaluate(False):
        e = y + sp.Integral(sp.sqrt(-x), (x, -1, 0))
    conds = definedness_conditions(e, None)
    assert sp.false not in conds
    # and no condition on the bound variable reaches the problem's symbols
    assert all(c.free_symbols <= {y} for c in conds)
    # a real power whose exponent is the bound variable still asks its base to be positive
    t = sp.Symbol("t", real=True)
    with sp.evaluate(False):
        p = sp.Integral(t**x, (x, 0, 1))
    assert (t > 0) in definedness_conditions(p, x)
    # a body undefined on its whole range stays so (decided over the range, not by the declaration)
    k = sp.Symbol("k", positive=True, integer=True)
    with sp.evaluate(False):
        s = y + sp.Sum(sp.sqrt(-k), (k, 1, 2))
    assert sp.false in definedness_conditions(s, None)


def test_a_sum_undefined_on_its_range_is_still_undefined():
    ir = _eq_y("y + Sum(sqrt(-k), (k, 1, 2)) = 0", KP)
    assert _v(ir, _sol("{0}", "set")) != "CORRECT"


# ------------------------------------------------------------ (2) derivative, antiderivative, FTC
XK = [{"name": "x", "domain": "real"}, {"name": "k", "domain": "integer"}, {"name": "t", "domain": "real"}]
XT = [{"name": "x", "domain": "real"}, {"name": "t", "domain": "real"}]
XTP = [{"name": "x", "domain": "positive_real"}, {"name": "t", "domain": "real"}]
L = [{"name": "L", "expr": "integrate(1/t, (t, 1, x))", "args": ["x"]}]


def _der(f, v=XK):
    return _ir("derivative", {"f": f, "var": "x"}, v, shape="expression")


def _anti(f, v=XK):
    return _ir("antiderivative", {"integrand": f, "var": "x"}, v, shape="expression")


def _eq_x(e, v=XT, fn=None):
    return _ir("solve_equation", {"equation": e, "var": "x"}, v, shape="set", functions=fn)


UNDEFINED_FUNCTIONS = [
    (_der("x + Sum(k/k, (k, -1, 1))"), "1", "expression"),
    (_der("x*Sum(k/k, (k, -1, 1))"), "3", "expression"),
    (_der("x**2 + 0*Integral(sqrt(t), (t, -2, -1))"), "2*x", "expression"),
    (_anti("1 + 0*Sum(k/k, (k, -1, 1))"), "x", "expression"),
    (_anti("2*x + Sum(k/k, (k, -1, 1)) - 3"), "x**2", "expression"),
    (_anti("2*x*Integral(sqrt(t), (t, -2, -1))/Integral(sqrt(t), (t, -2, -1))"), "x**2", "expression"),
    (_ir("definite_integral", {"integrand": "x + Sum(k/k, (k, -1, 1))", "var": "x", "a": "0", "b": "1"}, XK),
     "7/2", "value"),
    (_ir("tangent_line", {"f": "x**2 + Sum(k/k, (k, -1, 1))", "var": "x", "at": "1"}, XK + [{"name": "y"}],
         shape="expression"), "y = 2*x + 1", "expression"),
]


@pytest.mark.parametrize("ir,claim,kind", UNDEFINED_FUNCTIONS)
def test_a_function_defined_nowhere_as_written_is_not_differentiated(ir, claim, kind):
    r = verify(ir, _sol(claim, kind))
    assert r.verdict == "UNKNOWN"
    assert any(layer.layer == "intake.definedness" for layer in r.layers)


FTC = [
    (_eq_x("diff(L(x), x) = -1", fn=L), "{-1}"),
    (_eq_x("diff(integrate(1/t, (t, 1, x)), x) = -1"), "{-1}"),
    (_eq_x("diff(Integral(1/t, (t, 1, x)), x) = -1"), "{-1}"),
    (_ir("evaluate", {"expr": "diff(Integral(1/t, (t, 1, x)), x)"}, XT, ["x = -1"]), "-1"),
    (_eq_x("diff(Integral(1/t, (t, 0, x)), x) = 1", XTP), "{1}"),
]


@pytest.mark.parametrize("ir,claim", FTC)
def test_the_derivative_of_a_parametric_integral_needs_the_integral(ir, claim):
    kind = "set" if claim.startswith("{") else "value"
    assert _v(ir, _sol(claim, kind)) != "CORRECT"


def test_the_derivative_of_a_divergent_parametric_integral():
    assert _v(_der("Integral(1/t, (t, 0, x))", XTP), _sol("1/x", "expression")) != "CORRECT"


CALCULUS_CONTROLS = [
    (_der("x**2 + Sum(1/(k - x), (k, 1, 3))"), "2*x + 1/(1-x)**2 + 1/(2-x)**2 + 1/(3-x)**2", "expression", "CORRECT"),
    (_der("x**2 + Sum(1/(k - x), (k, 1, 3))"), "2*x", "expression", "INCORRECT"),
    (_der("Sum(k*x, (k, 1, 3))"), "6", "expression", "CORRECT"),
    (_anti("2*x"), "x**2", "expression", "CORRECT"),
    (_der("Integral(1/t, (t, 1, x))", XTP), "1/x", "expression", "CORRECT"),
    (_eq_x("diff(Integral(sqrt(t), (t, 0, x)), x) = 2", XTP), "{4}", "set", "CORRECT"),
    (_eq_x("diff(Integral(log(t), (t, 1, x)), x) = 0", XTP), "{1}", "set", "CORRECT"),
    # the variable of a definite integral runs over [a, b], not over its declared domain
    (_ir("definite_integral", {"integrand": "sqrt(-x)", "var": "x", "a": "-2", "b": "-1"}, XTP),
     "2*(2*sqrt(2) - 1)/3", "value", "CORRECT"),
]


@pytest.mark.parametrize("ir,claim,kind,verdict", CALCULUS_CONTROLS)
def test_calculus_controls(ir, claim, kind, verdict):
    assert _v(ir, _sol(claim, kind)) == verdict


def test_the_points_a_parametric_integral_may_cover():
    from mathverify.certify.domain import _reachable
    pos = sp.Symbol("x", positive=True)
    nonneg = sp.Symbol("x", nonnegative=True)
    real = sp.Symbol("x", real=True)
    assert _reachable(sp.Integer(1), pos) == sp.Interval.open(0, sp.oo)
    assert _reachable(sp.Integer(0), pos) == sp.Interval(0, sp.oo)
    assert _reachable(sp.Integer(1), nonneg) == sp.Interval(0, sp.oo)
    assert _reachable(sp.Integer(1), real) == sp.S.Reals
    assert _reachable(-pos, sp.Integer(-1)) == sp.Interval.open(-sp.oo, 0)


# --------------------------------------------------------------------- (3) pi + E is not decided
X = [{"name": "x"}]
UNDECIDED = ["pi + E", "pi*E", "log(2) + pi"]


@pytest.mark.parametrize("v", UNDECIDED)
@pytest.mark.parametrize("expr", ["x + gcd(x, 2) - gcd(2, x)", "x + lcm(x, 2) - lcm(2, x)",
                                  "x + factorial(x) - factorial(x)"])
def test_a_value_at_an_undecided_membership_is_not_certified(expr, v):
    assert _v(_ir("evaluate", {"expr": expr}, X, [f"x = {v}"]), _sol(v)) != "CORRECT"


def test_an_undecided_membership_of_two_symbols():
    ir = _ir("evaluate", {"expr": "x + y + gcd(x + y, 2) - gcd(2, x + y)"}, [{"name": "x"}, {"name": "y"}],
             ["x = pi", "y = E"])
    assert _v(ir, _sol("pi + E")) != "CORRECT"


def test_a_root_of_undecided_membership_is_not_certified():
    ir = _ir("solve_equation", {"equation": "(x - pi - E)*(x - 1/2) = gcd(x, 2) - gcd(2, x)", "var": "x"}, X,
             shape="set")
    assert _v(ir, _sol("{1/2, pi + E}", "set")) != "CORRECT"
    assert _v(ir, _sol("{1/2}", "set")) != "CORRECT"


def test_an_undecided_solution_is_not_dropped():
    # dropped, 1/2 would be the only value left; pi + E may be a solution
    ir = _ir("evaluate", {"expr": "x + gcd(x, 2) - gcd(2, x)"}, X, ["(x - pi - E)*(x - 1/2) = 0"])
    r = verify(ir, _sol("1/2"))
    assert r.verdict != "CORRECT"
    assert any((layer.evidence or {}).get("reason") == "solution_membership_undecided" for layer in r.layers)


@pytest.mark.parametrize("ir,claim,kind,verdict", [
    (_ir("evaluate", {"expr": "x + gcd(x, 2) - gcd(2, x)"}, X, ["x = 1/2"]), "1/2", "value", "CORRECT"),
    (_ir("evaluate", {"expr": "x + factorial(x) - factorial(x)"}, X, ["x = 3"]), "3", "value", "CORRECT"),
    (_ir("solve_equation", {"equation": "(x - 2)*(x - 1/2) = gcd(x, 2) - gcd(2, x)", "var": "x"}, X, shape="set"),
     "{1/2, 2}", "set", "CORRECT"),
])
def test_decided_memberships(ir, claim, kind, verdict):
    assert _v(ir, _sol(claim, kind)) == verdict


def test_membership_undecided():
    from mathverify.certify.domain import membership_undecided
    assert membership_undecided(sp.S.Rationals, sp.pi + sp.E) is True
    assert membership_undecided(sp.S.Rationals, sp.Rational(1, 2)) is False
    assert membership_undecided(sp.S.Rationals, sp.sqrt(2)) is False
    assert membership_undecided(sp.S.Reals, sp.pi + sp.E) is False


# -------------------------------------------------------------- (4) steps and simplifications
XR = [{"name": "x", "domain": "real"}]
XY = [{"name": "x", "domain": "real"}, {"name": "y", "domain": "real"}]
XYP = [{"name": "x", "domain": "real"}, {"name": "y", "domain": "positive_real"}]

AT_PREMISES = [
    (["x = 0"], XR, "1", "eq", "x/x = 1"),
    (["x = 0"], XR, "1", "compute", "x/x = 1"),
    (["x = 2"], XR, "3", "eq", "sqrt(x - 3)**2 = x - 3"),
    (["x = 2"], XR, "3", "compute", "log(x - 3) - log(x - 3) = 0"),
    (["x = sqrt(2)"], XR, "1 + sqrt(2)", "eq", "x + gcd(x, 2) - gcd(2, x) = x"),
    (["x = -3"], XR, "-2", "eq", "x + factorial(x) - factorial(x) = x"),
    (["x = pi + E"], XR, "pi + E + 1", "eq", "x + gcd(x, 2) - gcd(2, x) = pi + E"),
    (["x = 1", "y = -1"], XY, "2", "compute", "x + log(y) - log(y) = x"),
    (["x = 1", "y = -1"], XY, "2", "eq", "x + sqrt(y) - sqrt(y) = x"),
]


@pytest.mark.parametrize("givens,vars_,answer,kind,claim", AT_PREMISES)
def test_a_step_undefined_at_the_premises_point_is_not_verified(givens, vars_, answer, kind, claim):
    r = verify(_ir("evaluate", {"expr": "x + 1"}, vars_, givens), _sol(answer, steps=[_step(1, kind, claim)]))
    assert _steps(r) == [("unknown", "claim_undefined_at_the_premises_point")]


def test_a_step_undefined_at_one_point_of_a_finite_premise_set():
    ir = _ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, XR, shape="set")
    r = verify(ir, _sol("{-2, 2}", "set", steps=[_step(1, "eq", "x**2 = 4"), _step(2, "eq", "sqrt(x)**2 = x")]))
    assert _steps(r)[1] == ("unknown", "claim_undefined_at_the_premises_point")


@pytest.mark.parametrize("kind,claim", [("eq", "x/x = 1"), ("compute", "sqrt(x + 2)**2 = x + 2")])
def test_a_step_defined_at_the_premises_point_is_verified(kind, claim):
    r = verify(_ir("evaluate", {"expr": "x + 1"}, XR, ["x = 2"]), _sol("3", steps=[_step(1, kind, claim)]))
    assert [s for s, _ in _steps(r)] == ["verified"]


def test_a_symbol_the_premises_leave_free_is_no_point():
    # x is pinned, y is not: the identity holds wherever it is defined, as without premises
    r = verify(_ir("evaluate", {"expr": "x + 1"}, XY, ["x = 2"]), _sol("3", steps=[_step(1, "eq", "x/x + y/y = 2")]))
    assert [s for s, _ in _steps(r)] == ["verified"]


@pytest.mark.parametrize("claim,verdict", [
    ("x + log(y) - log(y)", "INCORRECT"),
    ("x + sqrt(y) - sqrt(y)", "INCORRECT"),
    ("x + y/y - 1", "INCORRECT"),
    ("x + factorial(y) - factorial(y)", "UNKNOWN"),
    ("x + gcd(y, 2) - gcd(2, y)", "UNKNOWN"),
])
def test_an_extra_term_undefined_in_another_variable(claim, verdict):
    assert _v(_ir("simplify_expression", {"expr": "x"}, XY, shape="expression"), _sol(claim, "expression")) == verdict
    assert _v(_ir("evaluate", {"expr": "x"}, XY, shape="expression"), _sol(claim, "expression")) == verdict


@pytest.mark.parametrize("kind,expr,vars_", [
    ("simplify_expression", "x + sqrt(-y) - sqrt(-y)", XYP),
    ("simplify_expression", "x + log(-y) - log(-y)", XYP),
    ("simplify_expression", "x + sqrt(-y**2 - 1) - sqrt(-y**2 - 1)", XY),
    ("simplify_expression", "x + sqrt(-x**2 - 1) - sqrt(-x**2 - 1)", XR),
    ("evaluate", "x + sqrt(-y) - sqrt(-y)", XYP),
])
def test_an_expression_defined_nowhere_is_not_simplified(kind, expr, vars_):
    r = verify(_ir(kind, {"expr": expr}, vars_, shape="expression"), _sol("x", "expression"))
    assert r.verdict == "UNKNOWN"


@pytest.mark.parametrize("ir,claim,verdict", [
    (_ir("simplify_expression", {"expr": "x**2/x"}, XR, shape="expression"), "x", "CORRECT"),
    (_ir("simplify_expression", {"expr": "x + log(y) - log(y)"}, XY, shape="expression"), "x + log(y) - log(y)",
     "CORRECT"),
    (_ir("simplify_expression", {"expr": "x + log(y) - log(y)"}, XY, shape="expression"), "x", "CORRECT"),
    (_ir("simplify_expression", {"expr": "x*y/y"}, XY, shape="expression"), "x", "CORRECT"),
])
def test_simplification_controls(ir, claim, verdict):
    assert _v(ir, _sol(claim, "expression")) == verdict


def test_an_equation_defined_nowhere_has_no_solution():
    """Since the review of part d4d (decision B4, 2 Oct 2026) the parameter y's written condition -y >= 0 is read
    on the region its declaration leaves (y > 0): no point, so the problem is undefined as written (UNKNOWN),
    as with the given y > 0 or the constraint y > 0; the empty set was CORRECT before."""
    ir = _ir("solve_equation", {"equation": "x + sqrt(-y) - sqrt(-y) = 1", "var": "x"}, XYP, shape="set")
    assert _v(ir, _sol("{}", "set")) == "UNKNOWN"
