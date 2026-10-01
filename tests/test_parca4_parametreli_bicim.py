"""An integral or a limit with a parameter: SymPy's value of it is taken nowhere (part iv, 1 Oct 2026;
DECISIONS §80 "F9", §72 V15 F9, N1 and N8 of the third audit).

The parse computed `integrate(f, (x, a, b))` with a free parameter, an antiderivative `integrate(f, x)`
and `limit(f, n, p)` with a parameter through SymPy, and a written `Integral`/`Limit` with a parameter
was computed by `simplify` (it ends with doit), by SymPy's `equals` and by the step checker. SymPy's
parametric result is wrong in some regions of the parameter: with n an integer the limit of a*n*sin(pi/n)
at oo is 0 (it is a*pi), ∫_1^x dt/t is log(x) (so L(-1) = I*pi), and ∫_{-1}^{1} a|cos x| dx stays 0 at
a = 1 (2 sin 1). Now such a form is held (`normalize.parse.HeldIntegral`, `HeldLimit`: doit returns it);
a parameter a given pins to a number is replaced by it first, and the closed form then takes the value
numbers confirm (`equiv.forms.checked_forms`, DECISIONS §72 (a)). A comparison that needs the value of a
form with a free parameter is undecided: agreement at sample points is no proof (principle 4), a
counterexample at one value still refutes. The limit task reads a pinned parameter at its value and
abstains on a free one.

Every case marked "351f901" was measured wrong there (denetim/2026-09-30/parca4/sonda.py: 99 cases,
33 not as expected before, 0 after).
"""
import pytest
import sympy as sp

from mathverify.normalize.parse import build_namespace, parse_expr_str
from mathverify.verifier import verify

A = {"name": "a", "domain": "real"}
X = {"name": "x", "domain": "real"}
T = {"name": "t", "domain": "real"}
Y = {"name": "y", "domain": "real"}
NP = {"name": "n", "domain": "positive_integer"}
NR = {"name": "n", "domain": "real"}

CORRECT, INCORRECT, UNKNOWN = "CORRECT", "INCORRECT", "UNKNOWN"
NOT_CORRECT = {INCORRECT, UNKNOWN}


def _ir(kind, params, vars_=(), givens=(), shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def _ev(expr, vars_, givens=(), functions=None):
    return _ir("evaluate", {"expr": expr}, vars_, givens, functions=functions)


def _simp(expr, vars_, givens=()):
    return _ir("simplify_expression", {"expr": expr}, vars_, givens)


def _sol(payload, steps=(), kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def _steps(r):
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    return layer.evidence.get("steps", [])


L = [{"name": "L", "expr": "integrate(1/t, (t, 1, x))", "args": ["x"]}]
LN = "limit(a*n*sin(pi/n), n, oo)"
I0A = "integrate(x, (x, 0, a))"
PG = "integrate(a*Abs(cos(x)), (x, -1, 1))"
PN = "integrate(integrate(y*Abs(cos(x)), (x, -1, 1)), (y, 0, 1))"
SEQ = _ir("solve_equation", {"equation": "limit(a*n*sin(pi/n), n, oo) = 2*pi", "var": "a"}, [NP, A], shape="set")
LIM = lambda e, var, vs, gv=(), to="oo": _ir("limit", {"expr": e, "var": var, "to": to}, vs, gv)  # noqa: E731

# (ir, solution, the verdicts allowed): each was a false accept or a false reject on 351f901
WRONG_BEFORE = [
    (SEQ, _sol("{}", kind="set"), NOT_CORRECT),                                       # N8: CORRECT
    (SEQ, _sol("{2}", kind="set"), {CORRECT, UNKNOWN}),                               # N8: INCORRECT
    (_ev("L(-1)", [X, T], functions=L), _sol("I*pi"), NOT_CORRECT),                   # N1: CORRECT
    (_ev("L(-2)", [X, T], functions=L), _sol("log(2) + I*pi"), NOT_CORRECT),          # N1: CORRECT
    (_ev(PG, [A, X], ["a = 1"]), _sol("0"), NOT_CORRECT),                             # F9 par_giv: CORRECT
    (_ev(PG, [A, X], ["a = 1"]), _sol("2*sin(1)"), {CORRECT, UNKNOWN}),               # F9 par_giv: INCORRECT
    (_ev(PN, [X, Y]), _sol("0"), NOT_CORRECT),                                        # F9 par_nest: CORRECT
    (_ev(PN, [X, Y]), _sol("sin(1)"), {CORRECT, UNKNOWN}),                            # F9 par_nest: INCORRECT
    (_ev(LN, [NP, A], ["a = 2"]), _sol("0"), NOT_CORRECT),
    (_ev(LN, [NP, A], ["a = 2"]), _sol("2*pi"), {CORRECT, UNKNOWN}),
    (_ev(LN.replace("limit", "Limit"), [NP, A], ["a = 2"]), _sol("0"), NOT_CORRECT),   # a written Limit
    (_ev(LN, [NP, A], ["a + 1 = 3"]), _sol("0"), NOT_CORRECT),                        # solved, not pinned
    (_ev(LN.replace("limit", "Limit"), [NP, A], ["a + 1 = 3"]), _sol("0"), NOT_CORRECT),
    (_ev(LN, [NP, A]), _sol("0"), NOT_CORRECT),
    (_simp(LN, [NP, A]), _sol("0", kind="expression"), NOT_CORRECT),
    (_simp(LN, [NP, A]), _sol("pi*a", kind="expression"), {CORRECT, UNKNOWN}),
    (_simp(LN.replace("limit", "Limit"), [NP, A]), _sol("0", kind="expression"), NOT_CORRECT),
    (_ev(r"\lim_{n \to \infty} a n \sin(\pi/n)", [NP, A], ["a = 2"]), _sol("0"), NOT_CORRECT),     # LaTeX
    (_simp(r"\lim_{n \to \infty} a n \sin(\pi/n)", [NP, A]), _sol("0", kind="expression"), NOT_CORRECT),
    (_simp(r"\int_{-1}^{1} a |\cos x|\,dx", [A, X]), _sol("0", kind="expression"), NOT_CORRECT),
    (_simp("integrate(a*x, x)", [A, X], ["a = 2"]), _sol("x**2", kind="expression"), {CORRECT, UNKNOWN}),
    (LIM("a*n*sin(pi/n)", "n", [NP, A]), _sol("0"), NOT_CORRECT),                     # the limit task
    (LIM("a*n*sin(pi/n)", "n", [NP, A], ["a = 2"]), _sol("0"), NOT_CORRECT),
    (LIM("a*n*sin(pi/n)", "n", [NP, A], ["a = 2"]), _sol("2*pi"), {CORRECT, UNKNOWN}),
]


@pytest.mark.parametrize("ir,sol,allowed", WRONG_BEFORE)
def test_a_parametric_value_of_sympy_decides_nothing(ir, sol, allowed):
    """351f901: each of these was a false accept or a false reject."""
    r = verify(ir, sol)
    assert r.verdict in allowed, [(la.layer, la.verdict, (la.evidence or {}).get("reason")) for la in r.layers]


@pytest.mark.parametrize("ir,sol,verdict", [
    (LIM("a*n*sin(pi/n)", "n", [NR, A], ["a = 2"]), _sol("2*pi"), CORRECT),
    (LIM("a*n*sin(pi/n)", "n", [NR, A], ["a = 2"]), _sol("0"), INCORRECT),
    (LIM("sin(a*x)/x", "x", [X, A], ["a = 3"], "0"), _sol("3"), CORRECT),
])
def test_the_limit_task_reads_a_pinned_parameter_at_its_value(ir, sol, verdict):
    """351f901: UNKNOWN (SymPy's value had the free parameter)."""
    assert verify(ir, sol).verdict == verdict


@pytest.mark.parametrize("ir,claim", [
    (LIM("a*n*sin(pi/n)", "n", [NR, A]), "pi*a"),
    (LIM("sin(a*x)/x", "x", [X, A], (), "0"), "a"),
])
def test_the_limit_task_abstains_on_a_free_parameter(ir, claim):
    r = verify(ir, _sol(claim))
    lay = next(la for la in r.layers if la.layer == "certify.limits")
    assert r.verdict == UNKNOWN and lay.evidence["reason"] == "parametric_limit"


@pytest.mark.parametrize("ir,sol,verdict", [
    (_ev(I0A, [A, X], ["a = 2"]), _sol("2"), CORRECT),
    (_ev(I0A, [A, X], ["a = 2"]), _sol("3"), INCORRECT),
    (_ev(I0A.replace("integrate", "Integral"), [A, X], ["a = 2"]), _sol("2"), CORRECT),
    (_ev(I0A, [A, X], ["2 = a"]), _sol("2"), CORRECT),
    (_ev("limit(sin(a*x)/x, x, 0)", [A, X], ["a = 3"]), _sol("3"), CORRECT),
    (_ev("limit(sin(a*x)/x, x, 0)", [A, X], ["a = 3"]), _sol("0"), INCORRECT),
    (_ev(r"\int_0^a x\,dx", [A, X], ["a = 2"]), _sol("2"), CORRECT),
    (_ev(r"\int_0^a x\,dx", [A, X], ["a = 2"]), _sol("3"), INCORRECT),
    (_ev("f(3)", [A, X, T], ["a = 2"], [{"name": "f", "expr": "integrate(a*t, (t, 0, x))", "args": ["x"]}]),
     _sol("9"), CORRECT),
    (_ev("f(3)", [A, X, T], ["a = 2"], [{"name": "f", "expr": "integrate(a*t, (t, 0, x))", "args": ["x"]}]),
     _sol("18"), INCORRECT),
    # a given on a formal argument's name pins no argument: f(2) is ∫_0^2 t dt, not ∫_0^3
    (_ev("f(2)", [X, T], ["x = 3"], [{"name": "f", "expr": "integrate(t, (t, 0, x))", "args": ["x"]}]),
     _sol("2"), CORRECT),
    (_ev("f(2)", [X, T], ["x = 3"], [{"name": "f", "expr": "integrate(t, (t, 0, x))", "args": ["x"]}]),
     _sol("9/2"), INCORRECT),
    (_ir("solve_equation", {"equation": "x**2 = integrate(t, (t, 0, a))", "var": "x"}, [A, X, T], ["a = 2"],
         shape="set"), _sol("{-sqrt(2), sqrt(2)}", kind="set"), CORRECT),
    (_ev("L(2)", [X, T], functions=L), _sol("log(2)"), CORRECT),                   # closed at the call
    # closed forms: unchanged
    (_ev("integrate(x**2, (x, 0, 3))", [X]), _sol("9"), CORRECT),
    (_ev("integrate(x**2, (x, 0, 3))", [X]), _sol("8"), INCORRECT),
    (_ev("limit(sin(x)/x, x, 0)", [X]), _sol("1"), CORRECT),
    (_ev("limit(sin(x)/x, x, 0)", [X]), _sol("0"), INCORRECT),
])
def test_a_pinned_parameter_is_read_at_its_value_and_closed_forms_are_unchanged(ir, sol, verdict):
    assert verify(ir, sol).verdict == verdict


@pytest.mark.parametrize("ir,sol", [
    (_simp(I0A, [A, X]), _sol("a**2/2", kind="expression")),
    (_simp("limit(sin(a*x)/x, x, 0)", [A, X]), _sol("a", kind="expression")),
    (_simp("integrate(2*x, x)", [X]), _sol("x**2", kind="expression")),
    (_ir("solve_equation", {"equation": "integrate(t, (t, 0, x)) = 2", "var": "x"}, [X, T], shape="set"),
     _sol("{-2, 2}", kind="set")),
])
def test_a_free_parameter_leaves_the_value_undecided(ir, sol):
    """The coverage this costs (DECISIONS §80): CORRECT on 351f901 through SymPy's parametric value."""
    assert verify(ir, sol).verdict == UNKNOWN


def test_a_counterexample_at_a_value_of_the_parameter_still_refutes():
    assert verify(_simp(I0A, [A, X]), _sol("a**2", kind="expression")).verdict == INCORRECT


@pytest.mark.parametrize("ir,sol,status", [
    # SymPy's doit verified the first two and classify_limit (with a free a) the third; it refuted the right fourth
    (_simp(I0A, [A, X]), _sol("a**2/2", [("compute", f"{I0A} = a**2/2")], kind="expression"), "unknown"),
    (_simp(I0A, [A, X]), _sol("a**2/2", [("compute", "Integral(x, (x, 0, a)) = a**2/2")], kind="expression"),
     "unknown"),
    (_simp(LN, [NP, A]), _sol("pi*a", [("compute", f"{LN} = 0")], kind="expression"), "unknown"),
    (_simp(LN, [NP, A]), _sol("pi*a", [("compute", f"{LN} = pi*a")], kind="expression"), "unknown"),
    (_ev("L(-1)", [X, T], functions=L), _sol("I*pi", [("compute", "L(-1) = I*pi")]), "unknown"),
    # a counterexample at a value of the parameter, and the pins of the givens, of a constraint, of a step
    (_simp(I0A, [A, X]), _sol("a**2/2", [("compute", f"{I0A} = a**2")], kind="expression"), "refuted"),
    (_ev(I0A, [A, X], ["a = 2"]), _sol("2", [("compute", f"{I0A} = 2")]), "verified"),
    (_ev(I0A, [A, X], ["a = 2"]), _sol("2", [("compute", f"{I0A} = 3")]), "refuted"),
    (_ev("a**2/2", [dict(A, constraints=["a = 2"]), X]), _sol("2", [("compute", f"{I0A} = 3")]), "refuted"),
    (_ev("a**2/2", [dict(A, constraints=["a = 2"]), X]), _sol("2", [("compute", f"{I0A} = 2")]), "verified"),
    (_ev("a**2/2", [A, X], ["a + 1 = 3"]), _sol("2", [("eq", "a = 2"), ("compute", f"{I0A} = 3")]), "refuted"),
    (_ev("limit(sin(a*x)/x, x, 0)", [A, X], ["a = 3"]), _sol("3", [("compute", "limit(sin(a*x)/x, x, 0) = 3")]),
     "verified"),
    (_simp("integrate(2*x, x)", [X]), _sol("x**2", [("compute", "integrate(2*x, x) = x**2")], kind="expression"),
     "verified"),                                                    # the antiderivative certificate
])
def test_a_compute_step_with_a_parametric_form(ir, sol, status):
    st = _steps(verify(ir, sol))
    assert st[-1]["status"] == status, [(s["status"], s.get("reason")) for s in st]


def test_a_parametric_form_is_held_and_neither_doit_nor_simplify_computes_it():
    from mathverify.normalize.parse import HeldIntegral, HeldLimit
    a, x = sp.Symbol("a", real=True), sp.Symbol("x", real=True)
    n = sp.Symbol("n", integer=True, positive=True)
    ns = build_namespace(None, {"a": a, "x": x, "n": n})
    for text, cls in [(I0A, HeldIntegral), ("Integral(x, (x, 0, a))", HeldIntegral), ("integrate(2*x, x)", HeldIntegral),
                      (LN, HeldLimit), ("Limit(a*n*sin(pi/n), n, oo)", HeldLimit),
                      (r"\int_0^a x\,dx", HeldIntegral)]:
        e = parse_expr_str(text, ns)
        assert isinstance(e, cls), (text, type(e))
        assert e.doit() == e and sp.simplify(1 + e).has(cls), text
    # closed: the plain forms, as before
    assert type(parse_expr_str("integrate(x**2, (x, 0, 3))", ns)) is sp.Integral
    assert type(parse_expr_str("limit(sin(x)/x, x, 0)", ns)) is sp.Limit


def test_a_given_pins_the_parameter_inside_the_form_never_its_bound_variable():
    ir = _ev(I0A, [A, X], ["a = 2", "x = 5"])
    from mathverify.ir import ProblemIR
    ns = build_namespace(ProblemIR.from_dict(ir))
    e = parse_expr_str(I0A, ns)
    assert type(e) is sp.Integral and e.limits[0][1:] == (0, 2) and e.function == e.limits[0][0]
    lim = parse_expr_str("limit(sin(a*x)/x, x, 0)", ns)
    assert type(lim) is sp.Limit and not lim.free_symbols and lim.args[2] == 0


def test_checked_forms_takes_a_closed_held_form_by_numbers():
    from mathverify.equiv.forms import UnverifiedForm, checked_forms
    from mathverify.normalize.parse import HeldIntegral
    x = sp.Symbol("x", real=True)
    assert checked_forms(HeldIntegral(x, (x, 0, 2))) == 2
    with pytest.raises(UnverifiedForm):        # SymPy's 0 for ∫_{-1}^{1} |cos x| dx: numbers say 2 sin 1
        checked_forms(HeldIntegral(sp.Abs(sp.cos(x)), (x, -1, 1)))


def test_agreement_at_sample_points_is_no_proof_for_a_parametric_form():
    from mathverify.equiv import answers_equivalent
    from mathverify.normalize.parse import HeldIntegral
    a, x = sp.Symbol("a", real=True), sp.Symbol("x", real=True)
    held = HeldIntegral(x, (x, 0, a))
    assert answers_equivalent(a**2 / 2, held, shape="expression", domain={a: sp.S.Reals})[0] is None
    assert answers_equivalent(a**2, held, shape="expression", domain={a: sp.S.Reals})[0] is False
    # a plain parametric form is held for the comparison too
    plain = sp.Integral(x, (x, 0, a))
    assert answers_equivalent(a**2 / 2, plain, shape="expression", domain={a: sp.S.Reals})[0] is None
