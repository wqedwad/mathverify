"""Part (v-b C) of 30 Sep 2026: the task certificates of limit, derivative, tangent line, the integrals
and extremum (HANDOFF V16 and V18; the audit of the §73 port, its "open" list; §74 (g); §77 "open").

(1) A task expression undefined AS WRITTEN with no free symbol left to choose: log(-1) - log(-1) + 2 is 2
    after parsing, and its limit 2, its derivative 0, the tangent y = 2 and its maximum 2 on [0, 1] were
    certified. A closed undefined part next to the variable (x + acos(2) - acos(2), x*log(-1)) passed
    the derivative without a point and both integrals, and a closed condition no exact check proves
    (tan(arccot(2) + arccot(1/2)), i.e. tan(pi/2)) did too.
(2) A variable declared positive or nonnegative: the parse folds |x| and sqrt(x**2) to x, so at 0 (outside
    the domain, or its closed end) the derivative 1 and the tangent y = x were certified. A derivative
    and a tangent line are two-sided: the point must be an interior point of the variable's domain.
(3) The membership conditions of gcd/lcm, n! and C(n, r) (Contains) were dropped by the limit,
    derivative, tangent line, integral and extremum certificates: x + x! - x! is x after parsing, its
    limit -3 at -3, its derivative 1, the integral -4 over [-3, -1] and the maximum -1 on [-3, -1] were
    certified. Such an expression has a value at the natural (for gcd: rational) numbers alone.
(4) With x declared positive, the right limit of log(-x) at 0 read from complex values: already closed by
    the "undefined as written" check of the limit certificate (6e0323d); pinned here.
(5) V18: an explicit extremum interval was read without the variable's constraints, the given relations
    and the domain of discourse: the maximum 3 of x on [-2, 3] with x < 1 was certified, the right 1
    with x <= 1 refuted. They now cut the interval (a symbol a given fixes read as its value; a free one
    makes the certificate abstain); an empty region is UNKNOWN. Without an interval the givens cut the
    domain too.
Measured on the code before the change (20d4edf): 101 of these 140 tests fail; the other 39 are controls
(defined expressions, interior points, a real variable, declared memberships, the real side of
log(-x), extremum without a cutting condition), the pins of (4) and the derivative at a point of
tan(pi/2)'s case in (1), which the point's own written check already held.
"""
from __future__ import annotations

import pytest

from mathverify.verifier import verify


def _ir(kind, params, vars_=(), givens=(), shape="scalar", dod=None, functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    if functions:
        d["functions"] = functions
    return d


def _sol(payload, kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []}


def _run(ir, payload, kind="value"):
    return verify(ir, _sol(payload, kind))


X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
B = {"name": "b", "domain": "real"}
T = {"name": "t", "domain": "real"}


def _xv(dom="real", cons=None):
    v = {"name": "x", "domain": dom}
    if cons:
        v["constraints"] = list(cons)
    return v


def lim(expr, to, vars_=(X,), side=None, **kw):
    p = {"expr": expr, "var": "x", "to": to}
    if side:
        p["side"] = side
    return _ir("limit", p, vars_, **kw)


def der(f, at=None, vars_=(X,), **kw):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    return _ir("derivative", p, vars_, shape="scalar" if at is not None else "expression", **kw)


def tan_(f, at, vars_=(X, Y), **kw):
    return _ir("tangent_line", {"f": f, "var": "x", "at": at, "dep": "y"}, vars_, shape="equation", **kw)


def ext(f, which="max", interval=None, vars_=(X,), **kw):
    p = {"f": f, "var": "x", "which": which}
    if interval is not None:
        p["interval"] = interval
    return _ir("extremum", p, vars_, **kw)


def dint(f, a, b, vars_=(X,)):
    return _ir("definite_integral", {"integrand": f, "var": "x", "a": a, "b": b}, vars_)


def anti(f, vars_=(X,)):
    return _ir("antiderivative", {"integrand": f, "var": "x"}, vars_, shape="expression")


# ---------------------------------------------------------------- (1) undefined as written, no symbol left
C0 = "log(-1) - log(-1) + 2"
C1 = "sqrt(-1)**2 + 3"
C2 = "acos(2) - acos(2) + 5"
X1 = "x + acos(2) - acos(2)"
TU = "x + 0*tan(arccot(2) + arccot(1/2))"        # tan(pi/2): a closed condition no check proves
FN = {"name": "f", "args": ["x"], "expr": "log(-1) - log(-1) + x"}


@pytest.mark.parametrize("ir,claim,kind", [
    (lim(C0, "0"), "2", "value"),
    (lim(C1, "0"), "2", "value"),
    (lim(C2, "0"), "5", "value"),
    (lim(C0, "oo"), "2", "value"),
    (lim(r"\ln(-1) - \ln(-1) + 2", "0"), "2", "value"),
    (der(C0, "1"), "0", "value"),
    (der(C1, "1"), "0", "value"),
    (der(TU, "1"), "1", "value"),
    (der(C0), "0", "expression"),
    (der(C2), "0", "expression"),
    (der("x + log(-1) - log(-1)"), "1", "expression"),
    (der(X1), "1", "expression"),
    (der("x**2 + 0*log(-2)"), "2*x", "expression"),
    (der("x*log(-1)"), "I*pi", "expression"),
    (der(TU), "1", "expression"),
    (der(r"x + \ln(-1) - \ln(-1)"), "1", "expression"),
    (der("f(x)", functions=[FN]), "1", "expression"),
    (tan_(C0, "1"), "y = 2", "equation"),
    (tan_(C2, "1"), "y = 5", "equation"),
    (ext(C0, "max", "[0, 1]"), "2", "value"),
    (ext(C1, "min", "[0, 1]"), "2", "value"),
    (dint(C0, "0", "1"), "2", "value"),
    (dint(X1, "0", "1"), "1/2", "value"),
    (dint(TU, "0", "1"), "1/2", "value"),
    (anti(C0), "2*x", "expression"),
    (anti(X1), "x**2/2", "expression"),
    (anti(TU), "x**2/2", "expression"),
    # the intake rule (part v-b B) does not read a limit task, so only this certificate stops these
    # (mutation G02 of this part survived on the combined code without them, 30 Sep 2026)
    (lim(TU, "0"), "0", "value"),
    (ext(TU, "max", "[0, 1]"), "1", "value"),
])
def test_a_task_expression_undefined_as_written_is_not_certified(ir, claim, kind):
    r = _run(ir, claim, kind)
    assert r.verdict == "UNKNOWN"
    # the certificate's own reason, or the intake's (part v-b B reads the task expression as written
    # before any certificate runs: tests/test_parca7b_tanimlilik.py)
    assert "problem_undefined_as_written" in r.flags or any(
        l.evidence.get("reason") in ("expression_undefined_as_written", "f_undefined_as_written",
                                     "f_undefined_at_point_as_written") for l in r.layers)


@pytest.mark.parametrize("ir,right,wrong,kind", [
    (lim("x + 2", "1"), "3", "4", "value"),
    (lim("log(2) - log(2) + 2", "0"), "2", "3", "value"),
    (lim("x/x", "0"), "1", "0", "value"),
    (der("x**2", "1"), "2", "3", "value"),
    (der("5", "1"), "0", "1", "value"),
    (der("x**2"), "2*x", "3*x", "expression"),
    (der("x*Integral(t, (t, 0, 1))", None, (X, T)), "1/2", "1", "expression"),
    (tan_("x**2", "1"), "y = 2*x - 1", "y = 2*x", "equation"),
    (ext("x**3 - 3*x", "max", "[-2, 3]"), "18", "2", "value"),
    (dint("x", "0", "1"), "1/2", "1", "value"),
    (anti("cos(x)"), "sin(x)", "-sin(x)", "expression"),
])
def test_defined_task_expressions_keep_their_verdicts(ir, right, wrong, kind):
    assert _run(ir, right, kind).verdict == "CORRECT"
    assert _run(ir, wrong, kind).verdict == "INCORRECT"


# ---------------------------------------------------------------- (2) the point of a derivative, a tangent
@pytest.mark.parametrize("dom", ["positive_real", "nonneg_real"])
@pytest.mark.parametrize("ir_of,claim,kind", [
    (lambda v: der("Abs(x)", "0", v), "1", "value"),
    (lambda v: der("Abs(x)", "0", v), "0", "value"),
    (lambda v: der("Abs(x)", "0", v), "", "dne"),
    (lambda v: der("sqrt(x**2)", "0", v), "1", "value"),
    (lambda v: der("x*Abs(x)", "0", v), "0", "value"),
    (lambda v: der("x**2", "0", v), "0", "value"),
    (lambda v: _ir("derivative", {"f": "Abs(x)", "var": "x", "at": "0", "order": 2}, v), "0", "value"),
    (lambda v: tan_("Abs(x)", "0", v + [Y]), "y = x", "equation"),
    (lambda v: tan_("sqrt(x**2)", "0", v + [Y]), "y = x", "equation"),
    (lambda v: tan_("Abs(x)", "0", v + [Y]), "", "dne"),
    (lambda v: tan_("x**2", "0", v + [Y]), "y = 0", "equation"),
])
def test_no_derivative_or_tangent_at_the_end_or_outside_of_a_declared_domain(dom, ir_of, claim, kind):
    r = _run(ir_of([_xv(dom)]), claim, kind)
    assert r.verdict == "UNKNOWN"
    assert "point_not_interior" in r.flags


@pytest.mark.parametrize("dom", ["positive_real", "nonneg_real"])
@pytest.mark.parametrize("ir_of,right,wrong,kind", [
    (lambda v: der("Abs(x)", "1", v), "1", "-1", "value"),
    (lambda v: der("x**2", "1/2", v), "1", "2", "value"),
    (lambda v: tan_("Abs(x)", "2", v + [Y]), "y = x", "y = -x", "equation"),
])
def test_interior_points_of_a_declared_domain_are_read(dom, ir_of, right, wrong, kind):
    ir = ir_of([_xv(dom)])
    assert _run(ir, right, kind).verdict == "CORRECT"
    assert _run(ir, wrong, kind).verdict == "INCORRECT"


@pytest.mark.parametrize("ir", [
    der("x**2", "0", [_xv("real", ["x >= 0"])]),
    tan_("x**2", "0", [_xv("real", ["x >= 0"]), Y]),
    der("x**2", "0", [X], dod="x >= 0"),
    der("x**2", "0", [_xv("real", ["x >= b"]), B], givens=["b = 0"]),
])
def test_the_closed_end_of_a_constraint_or_discourse_is_no_interior_point(ir):
    claim = "y = 0" if ir["task"]["kind"] == "tangent_line" else "0"
    kind = "equation" if ir["task"]["kind"] == "tangent_line" else "value"
    r = _run(ir, claim, kind)
    assert r.verdict == "UNKNOWN"
    assert "point_not_interior" in r.flags


def test_a_free_symbol_in_a_constraint_leaves_the_point_undecided():
    r = _run(der("x**2", "0", [_xv("real", ["x >= b"]), B]), "0")
    assert r.verdict == "UNKNOWN"
    assert "condition_not_applied" in r.flags
    assert _run(der("x**2", "0", [_xv("real", ["x >= b"]), B], givens=["b = -1"]), "0").verdict == "CORRECT"


@pytest.mark.parametrize("ir,right,wrong,kind", [
    (der("Abs(x)", "0"), "", "1", "dne"),
    (der("x**2", "0"), "0", "1", "value"),
    (der("x**2", "0", [_xv("real", ["x > -1"])]), "0", "1", "value"),
])
def test_a_real_variable_keeps_the_two_sided_derivative(ir, right, wrong, kind):
    assert _run(ir, right, kind).verdict == "CORRECT"
    assert _run(ir, wrong, "value").verdict == "INCORRECT"


# ---------------------------------------------------------------- (3) membership conditions
F = "x + factorial(x) - factorial(x)"
G = "x + gcd(x, 2) - gcd(2, x)"


@pytest.mark.parametrize("ir,claim,kind", [
    (lim(F, "-3"), "-3", "value"),
    (lim(F, "3"), "3", "value"),
    (lim(F, "1/2"), "1/2", "value"),
    (lim(f"({F})/x", "oo"), "1", "value"),
    (lim(G, "0"), "0", "value"),
    (lim(G, "sqrt(2)"), "sqrt(2)", "value"),
    (lim("x + binomial(x, 2) - binomial(x, 2)", "-3"), "-3", "value"),
    (der(F, "-3"), "1", "value"),
    (der("x**2 + factorial(x) - factorial(x)", "2"), "4", "value"),
    (der(G, "sqrt(2)"), "1", "value"),
    (der(F), "1", "expression"),
    (der(G), "1", "expression"),
    (tan_(F, "-3"), "y = x", "equation"),
    (tan_(F, "2"), "y = x", "equation"),
    (dint(F, "-3", "-1"), "-4", "value"),
    (dint(F, "0", "1"), "1/2", "value"),
    (dint(G, "0", "1"), "1/2", "value"),
    (anti(F), "x**2/2", "expression"),
    (ext("-(x - 2)**2 + factorial(x) - factorial(x)", "max", "[1/2, 3/2]"), "-1/4", "value"),
    (ext(F, "max", "[-3, -1]"), "-1", "value"),
    (ext(G, "max", "[0, 1]"), "1", "value"),
])
def test_a_membership_condition_on_the_variable_is_not_dropped(ir, claim, kind):
    r = _run(ir, claim, kind)
    assert r.verdict == "UNKNOWN"
    assert "membership_condition" in r.flags


@pytest.mark.parametrize("ir,right,wrong", [
    # a sequence: n a positive integer, n! has its value
    (_ir("limit", {"expr": "2**n/factorial(n)", "var": "n", "to": "oo"}, [{"name": "n", "domain": "positive_integer"}]),
     "0", "1"),
    (lim("x + factorial(3)", "1"), "7", "8"),
    (der("x*factorial(3)", "1"), "6", "3"),
    (dint("x*factorial(2)", "0", "1"), "1", "2"),
])
def test_a_membership_the_declaration_or_a_number_settles_is_read(ir, right, wrong):
    assert _run(ir, right).verdict == "CORRECT"
    assert _run(ir, wrong).verdict == "INCORRECT"


# ---------------------------------------------------------------- (4) log(-x) with x declared positive
P = [_xv("positive_real")]


@pytest.mark.parametrize("ir,claim", [
    (lim("x*log(-x)", "0", P, "+"), "0"),
    (lim("x*log(-x)", "0", P), "0"),
    (lim("log(-x)", "0", P, "+"), "-oo"),
    (lim("x*sqrt(-x)", "0", P, "+"), "0"),
    (lim(r"x \ln(-x)", "0", P, "+"), "0"),
    (_ir("evaluate", {"expr": "Limit(x*log(-x), x, 0, '+')"}, P), "0"),
])
def test_no_limit_from_complex_values_of_a_positive_variable(ir, claim):
    assert _run(ir, claim).verdict == "UNKNOWN"


def test_the_real_side_of_log_minus_x_keeps_its_limit():
    assert _run(lim("x*log(-x)", "0", [X], "-"), "0").verdict == "CORRECT"
    assert _run(lim("x*log(-x)", "0", [_xv("real", ["x > 0"])], "+"), "0").verdict == "INCORRECT"
    assert _run(lim("x*log(x)", "0", P, "+"), "0").verdict == "CORRECT"


# ---------------------------------------------------------------- (5) V18: the extremum interval is cut
LT1 = [_xv("real", ["x < 1"])]
LE1 = [_xv("real", ["x <= 1"])]


@pytest.mark.parametrize("ir,right,wrong", [
    (ext("x", "max", "[-2, 3]", LE1), "1", "3"),
    (ext("x", "max", "[-2, 3]", givens=["x <= 1"]), "1", "3"),
    (ext("x", "max", "[-2, 3]", dod="x <= 1"), "1", "3"),
    (ext("x", "max", "[-2, 3]", dod="[0, 2]"), "2", "3"),
    (ext("x", "max", "[-2, 3]", givens=["x**2 <= 1"]), "1", "3"),
    (ext("x", "max", "[-2, 3]", givens=["0 < x <= 2"]), "2", "3"),
    (ext("x", "argmax", "[-2, 3]", LE1), "1", "3"),
    (ext("x**2", "min", "[-2, 3]", [_xv("real", ["1 <= x"])]), "1", "0"),
    (ext("x", "max", r"\left[-2, 3\right]", LE1), "1", "3"),
    (ext("x", "max", "[-2, 3]", [_xv("real", ["x <= b"]), B], givens=["b = 1"]), "1", "3"),
    (ext("-(x - 2)**2", "max", None, givens=["x <= 1"]), "-1", "0"),
    (ext("(x - 3)**2", "min", None, [X, B], givens=["x >= b", "b = 4"]), "1", "0"),
])
def test_the_extremum_region_is_cut_by_constraints_givens_and_discourse(ir, right, wrong):
    assert _run(ir, right).verdict == "CORRECT"
    assert _run(ir, wrong).verdict == "INCORRECT"


@pytest.mark.parametrize("ir,claim", [
    (ext("x", "max", "[-2, 3]", LT1), "3"),                     # V18: the supremum 1 is not attained
    (ext("x", "max", "[-2, 3]", givens=["x < 1"]), "3"),
    (ext("x", "max", "[-2, 3]", [_xv("real", ["x < b"]), B], givens=["b = 1"]), "3"),
    (ext("x*(x - 2)**2", "local_max", "[-2, 3]", [_xv("real", ["x >= 1"])]), "32/27"),
    (ext("-x**2", "max", "[-1, 1]", [_xv("real", ["x != 0"])]), "0"),
    (ext("x", "max", "[-2, 3]", givens=["x = 2"]), "3"),
    (ext("-(x - 2)**2", "max", None, givens=["x < 1"]), "0"),
])
def test_a_value_outside_the_cut_region_is_not_certified(ir, claim):
    assert _run(ir, claim).verdict != "CORRECT"


@pytest.mark.parametrize("ir", [
    ext("x", "max", "[-2, 3]", givens=["x + sin(x) < 1"]),
    ext("x", "max", "[-2, 3]", [_xv("real", ["x + exp(x) < 3"])]),
    ext("-(x - 5)**2", "max", None, givens=["x + exp(x) < 3"]),
])
def test_a_condition_solveset_cannot_solve_makes_the_extremum_abstain(ir):
    r = _run(ir, "3" if ir["task"]["params"]["f"] == "x" else "0")
    assert r.verdict == "UNKNOWN"
    assert any(l.evidence.get("reason") == "condition_unsolved" for l in r.layers)


def test_an_empty_region_is_unknown():
    r = _run(ext("x", "max", "[-2, 3]", [_xv("real", ["x > 5"])]), "3")
    assert r.verdict == "UNKNOWN"
    assert any(l.evidence.get("reason") == "interval_empty_under_the_conditions" for l in r.layers)
    r = _run(ext("x", "max", "[1, 3]", [_xv("positive_real")], givens=["x < 0"]), "3")
    assert r.verdict == "UNKNOWN"
    assert any(l.evidence.get("reason") == "interval_empty_under_the_conditions" for l in r.layers)


@pytest.mark.parametrize("ir", [
    ext("x", "max", "[-2, 3]", [_xv("real", ["x < b"]), B]),
    ext("x", "max", "[-2, 3]", [X, B], givens=["x < b"]),
    ext("(x - 3)**2", "min", None, [X, B], givens=["x > b"]),
    ext("x", "max", "[-2, 3]", [X, B], dod="x < b"),
])
def test_a_free_symbol_in_a_condition_makes_the_extremum_abstain(ir):
    r = _run(ir, "3" if ir["task"]["params"]["f"] == "x" else "0")
    assert r.verdict == "UNKNOWN"
    assert "condition_not_applied" in r.flags


@pytest.mark.parametrize("ir,right,wrong", [
    (ext("x**3 - 3*x", "max", "[-2, 3]"), "18", "2"),
    (ext("x + 4/x", "min", "(0, oo)", [_xv("positive_real")], dod="x > 0"), "4", "2"),
    (ext("x**3 - 6*x**2 + 9*x + 1", "local_max"), "5", "1"),
    (ext("x", "max", "[-2, 3]", [_xv("real", ["x > -5"])]), "3", "2"),
    (ext("x", "max", "[-2, 3]", [X, Y], givens=["y = 2"]), "3", "2"),
    # a given that does not name the variable cuts nothing, even with a free symbol
    (ext("x", "max", "[-2, 3]", [X, {"name": "a", "domain": "real"}], givens=["a > 0"]), "3", "2"),
    (ext("-(x - 2)**2", "max", None, [X, {"name": "a", "domain": "real"}], givens=["a > 0"]), "0", "1"),
])
def test_extremum_without_a_cutting_condition_is_unchanged(ir, right, wrong):
    assert _run(ir, right).verdict == "CORRECT"
    assert _run(ir, wrong).verdict == "INCORRECT"


def test_the_task_expression_helpers_decide_a_closed_undecided_condition():
    # direct: the intake rule (part v-b B) runs first on the derivative, tangent, antiderivative and
    # integral tasks, so the verdict tests alone keep G02 and G04 alive there (combined mutation run)
    from mathverify.certify.base import make_ctx
    from mathverify.certify.calculus import _unreadable_task_expression
    from mathverify.certify.limits import written_undefined_everywhere
    from mathverify.ir import ProblemIR
    ctx = make_ctx(ProblemIR.from_dict(lim(TU, "0")))
    assert written_undefined_everywhere(TU, ctx.ns) is True
    assert written_undefined_everywhere("x + 2", ctx.ns) is False
    x = ctx.ns["x"]
    bad = _unreadable_task_expression(TU, x, x, ctx.ns, 0)
    assert bad is not None and bad.verdict == "unknown" and bad.evidence.get("reason") == "expression_undefined_as_written"
    assert _unreadable_task_expression("x + 2", x + 2, x, ctx.ns, 0) is None
