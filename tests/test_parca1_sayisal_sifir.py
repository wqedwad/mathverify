"""Third audit's critic findings N2, N3 (eq step), N4 and N6, re-run on master aa67b20 (30 Sep 2026,
`denetim/2026-09-30/n19/sonda_n19.py`). Each case below was measured wrong before its fix:

* N2: a closed integral whose exact value is 0 was never confirmed. Its quadrature is a residue of
  1e-51...1e-59, compared RELATIVELY with SymPy's exact 0: the claim 0 stayed UNKNOWN and the true
  steps "∫_0^3 (x² - 2x) dx = 0" were refuted (18/18 probe cases wrong). The residue is now measured
  against the integrand's scale ∫|f| at every rung of the precision ladder; a small nonzero value
  (∫_0^1 10^-40 dx) is never taken for 0.
* N3: an eq step with a closed limit that does not exist ("lim_{x->2} |x - 2|/(x - 2) = 1") was not
  refuted, and its solution was CORRECT.
* N4: full-period trig sums (Σ_{k=1}^{4n} cos(kπ/2) = 0) were refuted: strict evalf of the sum gave
  a "significant" difference of 1.6e-35 at n = 109, taken as a counterexample without exact check.
* N6: a wrong claim about a parametric Integral or a sum of more than 2000 terms stayed UNKNOWN
  (no exact value at a sample point: the form could not be written out).
"""
import pytest
import sympy as sp

from mathverify.verifier import verify

XR = [{"name": "x", "domain": "real"}]
XT = [{"name": "x", "domain": "real"}, {"name": "t", "domain": "real"}]
NK = [{"name": "n", "domain": "positive_integer"}, {"name": "k", "domain": "positive_integer"}]


def _ir(kind, params, vars_=XR, options=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": [], "answer_shape": "scalar"}
    if options:
        d["options"] = options
    return d


def _run(ir, payload, steps=(), kind="value", option=None):
    ca = {"kind": kind, "payload": payload}
    if option:
        ca["option"] = option
    sol = {"claimed_answer": ca,
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _steps(r):
    for layer in r.layers:
        if layer.layer == "steps.refute":
            return [s["status"] for s in layer.evidence.get("steps", [])]
    return []


def _ev(e, vars_=XR):
    return _ir("evaluate", {"expr": e}, vars_)


def _di(f, a, b):
    return _ir("definite_integral", {"integrand": f, "var": "x", "a": a, "b": b})


# --- N2: the exact zero of a closed integral ---------------------------------------------------------

I1 = "integrate(x**2 - 2*x, (x, 0, 3))"
CI = "Integral(x**2 - 2*x, (x, 0, 3))"
ZERO_INTEGRALS = [("integrate(3*x**2 - 4*x, (x, 0, 2))", "8 - 8"), ("integrate(cos(x), (x, 0, pi))", "sin(pi) - sin(0)"),
                  ("integrate(x - 1, (x, 0, 2))", "2 - 2"), ("integrate(sin(2*x), (x, 0, pi))", "0"),
                  (I1, "27/3 - 9")]


@pytest.mark.parametrize("expr,rhs", ZERO_INTEGRALS)
def test_a_closed_integral_whose_value_is_zero_is_confirmed(expr, rhs):
    """The claim 0 was UNKNOWN and the true eq step refuted (the solution INCORRECT)."""
    assert _run(_ev(expr), "0").verdict == "CORRECT"
    r = _run(_ev(expr), "0", [("eq", f"{expr} = {rhs}")])
    assert r.verdict == "CORRECT" and _steps(r) == ["verified"]


def test_every_form_of_the_zero_integral_is_confirmed():
    assert _run(_ev(I1), "1").verdict == "INCORRECT"
    r = _run(_ev(I1), "0", [("compute", f"{I1} = 0")])
    assert r.verdict == "CORRECT" and _steps(r) == ["verified"]
    r = _run(_ev(I1), "0", [("eq", f"{CI} = 0")])
    assert r.verdict == "CORRECT" and _steps(r) == ["verified"]
    assert _run(_ev(CI), "0").verdict == "CORRECT"
    opts = {"A": "-1", "B": "0", "C": "1", "D": "2"}
    assert _run(_ir("evaluate", {"expr": I1}, options=opts), None, option="B").verdict == "CORRECT"
    assert _run(_ir("evaluate", {"expr": I1}, options=opts), None, option="A").verdict == "INCORRECT"


def test_the_definite_integral_certificate_confirms_an_exact_zero():
    """SymPy's 0 disagreed with the residue ("symbolic_numeric_disagreement"): UNKNOWN, and the true
    step refuted."""
    di = _di("x**2 - 2*x", "0", "3")
    assert _run(di, "0").verdict == "CORRECT"
    assert _run(di, "1").verdict == "INCORRECT"
    assert _run(di, "10**(-30)").verdict == "INCORRECT"
    r = _run(di, "0", [("eq", f"{CI} = 0")])
    assert r.verdict == "CORRECT" and _steps(r) == ["verified"]
    assert _run(_di("10**20*sin(x)", "0", "2*pi"), "0").verdict == "CORRECT"      # the residue is 1e-18 at 30 digits
    assert _run(_ev("integrate(10**20*sin(x), (x, 0, 2*pi))"), "0").verdict == "CORRECT"


def test_a_zero_integral_sympy_cannot_evaluate_is_decided_by_the_scale_alone():
    """With no exact value the claim 0 was compared relatively with the residue and REFUTED. SymPy
    has no value for ∫_0^{2π} sin(sin x) dx; its quadrature is -4.4e-58 at 50 digits (on [-1, 1] the
    symmetric nodes give 0.0 exactly, which no relative comparison misreads: not a probe here)."""
    di = _di("sin(sin(x))", "0", "2*pi")
    assert _run(di, "0").verdict == "CORRECT"
    assert _run(di, "1/10").verdict == "INCORRECT"
    ev = _ev("integrate(sin(x), (x, 0, 2*pi))")
    r = _run(ev, "0", [("eq", "Integral(sin(sin(x)), (x, 0, 2*pi)) = 0")])
    assert r.verdict == "CORRECT" and _steps(r) != ["refuted"]
    r = _run(ev, "0", [("eq", "Integral(sin(sin(x)), (x, 0, 2*pi)) = 10**(-30)")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]


@pytest.mark.parametrize("make", [lambda f, a, b: _di(f, a, b),
                                  lambda f, a, b: _ev(f"integrate({f}, (x, {a}, {b}))")])
def test_a_small_nonzero_integral_is_never_taken_for_zero(make):
    """The absolute criterion must not certify a value that is merely small."""
    assert _run(make("10**(-40)", "0", "1"), "0").verdict == "INCORRECT"
    assert _run(make("sin(x) + 10**(-40)", "0", "2*pi"), "0").verdict != "CORRECT"
    assert _run(make("sin(x) + 10**(-60)", "0", "2*pi"), "0").verdict != "CORRECT"
    assert _run(make("x**2 - 2*x + 10**(-30)", "0", "3"), "0").verdict != "CORRECT"
    assert _run(make("sin(x)", "0", "2*pi"), "10**(-40)").verdict == "INCORRECT"
    assert _run(make("sin(x)", "0", "2*pi"), "0").verdict == "CORRECT"


def test_a_step_equating_a_small_integral_with_zero_is_refuted():
    r = _run(_ev("integrate(10**(-40), (x, 0, 1))"), "10**(-40)", [("eq", "integrate(10**(-40), (x, 0, 1)) = 0")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]
    r = _run(_ev("integrate(sin(x), (x, 0, 2*pi))"), "0", [("eq", "integrate(sin(x), (x, 0, 2*pi)) = 10**(-40)")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]


@pytest.mark.parametrize("make", [lambda f, a, b: _di(f, a, b),
                                  lambda f, a, b: _ev(f"integrate({f}, (x, {a}, {b}))")])
@pytest.mark.parametrize("f", ["x*exp(x**(-2))", "1/x**3", "1/x"])
def test_a_divergent_odd_integral_is_not_zero(make, f):
    """Symmetric quadrature nodes give 0 for an odd integrand, integrable or not, and SymPy's value of
    ∫_{-1}^{1} x·e^(1/x²) dx is 0: the scale ∫|f| must itself converge."""
    assert _run(make(f, "-1", "1"), "0").verdict != "CORRECT"


def test_the_zero_test_itself():
    """Since the fourth audit (1 Oct 2026, S1) the zero is a symbolic certificate
    (`zero_integral_certificate`): numbers only bound a value, they never show it is 0."""
    from mathverify.certify.calculus import zero_integral_certificate
    x = sp.Symbol("x", real=True)
    for f, a, b in [(x**2 - 2*x, 0, 3), (sp.cos(x), 0, sp.pi), (sp.log(x) + 1, 0, 1), (sp.tan(x), -1, 1),
                    (sp.Abs(x) - sp.Rational(1, 2), -1, 1)]:
        assert zero_integral_certificate(f, x, a, b)[0] is True, f
    assert zero_integral_certificate(sp.Rational(1, 10**40), x, 0, 1)[0] is None
    assert zero_integral_certificate(x, x, 0, 1)[0] is None
    for f in (sp.sin(x) + sp.Rational(1, 10**40), sp.sin(x) + sp.Rational(1, 10**60)):
        assert zero_integral_certificate(f, x, 0, 2 * sp.pi)[0] is None, f
    for f in (x * sp.exp(x**-2), 1 / x**5, 1 / x):
        assert zero_integral_certificate(f, x, -1, 1)[0] is None, f
    # odd and absolutely integrable (|f| <= |x|^(-1/2)): 0 by symmetry, which no quadrature showed
    assert zero_integral_certificate(sp.sign(x) / sp.sqrt(sp.Abs(x)), x, -1, 1)[0] is True


def test_checked_forms_takes_an_exact_zero_only_when_confirmed():
    from mathverify.equiv.forms import UnverifiedForm, checked_forms
    x = sp.Symbol("x", real=True)
    assert checked_forms(sp.Integral(x**2 - 2*x, (x, 0, 3))) == 0
    assert checked_forms(sp.Integral(sp.sin(x), (x, 0, 2 * sp.pi)) + 1) == 1
    with pytest.raises(UnverifiedForm):
        checked_forms(sp.Integral(x * sp.exp(x**-2), (x, -1, 1)))     # SymPy says 0; it diverges


# --- N3: an eq step with a closed limit ---------------------------------------------------------------

L1 = r"\lim_{x \to 2} \frac{|x - 2|}{x - 2}"
L3 = r"\lim_{x \to 3} \frac{1}{x - 3}"
LIM = _ir("limit", {"expr": "Abs(x - 2)/(x - 2)", "var": "x", "to": "2", "side": "+"})
LIM3 = _ir("limit", {"expr": "1/(x - 3)", "var": "x", "to": "3", "side": "+"})
LIMQ = _ir("limit", {"expr": "(x**2 - 4)/(x - 2)", "var": "x", "to": "2"})


@pytest.mark.parametrize("ir,payload,claim", [
    (LIM, "1", f"{L1} = 1"), (LIM3, "oo", f"{L3} = \\infty"),
    (LIM, "1", "Limit(Abs(x - 2)/(x - 2), x, 2) = 1"), (LIM, "1", "limit(Abs(x - 2)/(x - 2), x, 2) = 1"),
    (LIM, "1", "1 = Limit(Abs(x - 2)/(x - 2), x, 2)"), (LIM, "1", "limit(sin(1/x), x, 0) = 0"),
    (LIMQ, "4", "Limit(1/(x - 3)**2, x, 3) = 5"), (LIMQ, "4", "Limit(1/(x - 3)**2, x, 3) = -oo"),
    (LIMQ, "4", "Limit(1/x, x, oo) = oo"), (LIMQ, "4", "Limit((x**2 - 4)/(x - 2), x, 2) = 5"),
])
def test_an_eq_step_with_a_false_closed_limit_is_refuted(ir, payload, claim):
    """A two-sided limit that does not exist equals nothing; an infinite limit no finite number."""
    r = _run(ir, payload, [("eq", claim)])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]


@pytest.mark.parametrize("ir,payload,claim", [
    (LIM, "1", "Limit(Abs(x - 2)/(x - 2), x, 2, '+') = 1"),
    (LIM, "1", r"\lim_{x \to 2^{+}} \frac{|x - 2|}{x - 2} = 1"),
    (LIMQ, "4", "Limit((x**2 - 4)/(x - 2), x, 2) = 4"), (LIMQ, "4", r"\lim_{x \to 2} \frac{x^2 - 4}{x - 2} = 4"),
    (LIMQ, "4", "Limit(1/(x - 3)**2, x, 3) = oo"), (LIMQ, "4", "Limit(1/x, x, oo) = 0"),
    (LIMQ, "4", "limit(sin(x)/x, x, 0) = 1"),
])
def test_an_eq_step_with_a_true_closed_limit_is_not_refuted(ir, payload, claim):
    r = _run(ir, payload, [("eq", claim)])
    assert r.verdict == "CORRECT" and _steps(r) != ["refuted"]


@pytest.mark.parametrize("step_kind", ["compute", "eq"])
def test_the_compute_and_eq_steps_agree_on_a_limit_that_does_not_exist(step_kind):
    r = _run(LIM, "1", [(step_kind, f"{L1} = 1")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]


@pytest.mark.parametrize("vars_", [XR, [{"name": "x"}]])
@pytest.mark.parametrize("expr,claim", [(L1, "1"), (r"\lim_{x \to 1} \lfloor x \rfloor", "1"), (L3, "oo"),
                                        ("limit(Abs(x - 2)/(x - 2), x, 2)", "1")])
def test_a_limit_that_does_not_exist_has_no_value(vars_, expr, claim):
    assert _run(_ev(expr, vars_), claim).verdict in ("INCORRECT", "UNKNOWN")


# --- N4: full-period trig sums --------------------------------------------------------------------------

@pytest.mark.parametrize("expr,claim", [
    ("Sum(cos(k*pi/2), (k, 1, 4*n))", "0"), ("Sum(sin(k*pi/2), (k, 1, 4*n))", "0"),
    ("Sum(cos(2*pi*k/3), (k, 1, 3*n))", "0"), ("Sum(sin(2*pi*k/3), (k, 1, 3*n))", "0"),
    ("Sum(cos(pi*k/3), (k, 1, 6*n))", "0"), ("Sum(cos(2*pi*k/3), (k, 1, 3*n)) + 1", "1"),
])
def test_a_full_period_trig_sum_is_not_refuted(expr, claim):
    r = _run(_ir("simplify_expression", {"expr": expr}, NK), claim, kind="expression")
    assert r.verdict in ("CORRECT", "UNKNOWN")


@pytest.mark.parametrize("expr,claim", [("Sum(cos(k*pi/2), (k, 1, 4*n))", "1"),
                                        ("Sum(cos(2*pi*k/3), (k, 1, 3*n)) + 1", "0")])
def test_a_wrong_trig_sum_claim_is_still_refuted(expr, claim):
    assert _run(_ir("simplify_expression", {"expr": expr}, NK), claim, kind="expression").verdict == "INCORRECT"


def test_a_nonzero_difference_needs_an_exact_witness():
    from mathverify.equiv.random_point import random_point_equal
    n = sp.Symbol("n", integer=True, positive=True)
    k = sp.Symbol("k", integer=True, positive=True)
    x = sp.Symbol("x", real=True)
    ok, ev = random_point_equal(sp.Sum(sp.cos(k * sp.pi / 2), (k, 1, 4 * n)), sp.S(0), n, sp.Naturals)
    assert ok is True, ev
    ok, ev = random_point_equal(1 / (x - 1), 1 / (x - 1) + sp.exp(-1000), x, sp.Reals)
    assert ok is False and ev["reason"] == "difference_below_working_precision_but_nonzero"
    assert ev["counterexample"]["exact"] == "values_differ"


def test_a_significant_looking_difference_is_confirmed_exactly_before_it_counts():
    """The high-precision difference only nominates a point; the exact values decide it. A point they
    cannot decide is no witness, and the comparison abstains rather than calling the sides equal."""
    from mathverify.equiv.random_point import _definite_nonzero_difference, random_point_equal
    x = sp.Symbol("x", real=True)
    t = sp.Symbol("t", real=True)
    pts = [{x: sp.Rational(1, 3)}]
    assert _definite_nonzero_difference(sp.exp(-1000), [x], pts, x, x) == (None, 0)
    w, unsure = _definite_nonzero_difference(sp.exp(-1000), [x], pts, x + sp.exp(-1000), x)
    assert w is not None and w["exact"] == "values_differ" and unsure == 0
    a = x + sp.exp(-1000) * sp.Integral(sp.exp(sp.sin(t)), (t, 0, 1))     # no exact value at any point
    ok, ev = random_point_equal(a, x, x, sp.Reals)
    assert ok is not True and ev.get("unconfirmed_difference_points")


# --- N6: a parametric integral, a sum of more than 2000 terms ------------------------------------------

def test_a_wrong_claim_about_a_parametric_integral_is_refuted():
    ir = _ir("simplify_expression", {"expr": "Integral(t**2 - 2*t, (t, 0, x))"}, XT)
    assert _run(ir, "x**3/3 - x**2 + 1", kind="expression").verdict == "INCORRECT"
    assert _run(ir, "x**3/3 - 2*x**2", kind="expression").verdict == "INCORRECT"
    assert _run(ir, "x**3/3 - x**2", kind="expression").verdict in ("CORRECT", "UNKNOWN")


def test_a_wrong_claim_about_a_long_sum_is_refuted():
    ir = _ir("simplify_expression", {"expr": "Sum(k, (k, 1, 1000*n))"}, NK)
    assert _run(ir, "500*n*(1000*n - 1)", kind="expression").verdict == "INCORRECT"
    assert _run(ir, "500*n*(1000*n + 1)", kind="expression").verdict in ("CORRECT", "UNKNOWN")


def test_a_counterexample_through_checked_forms_stands_clear_of_the_numbers():
    """A form that cannot be written out takes SymPy's value confirmed by numbers; a difference inside
    the numbers' tolerance is no counterexample, and the number of such points is bounded."""
    from mathverify.equiv.random_point import _exact_counterexample
    x = sp.Symbol("x", real=True)
    t = sp.Symbol("t", real=True)
    a = sp.Integral(t**2 - 2 * t, (t, 0, x))
    pt = {x: sp.Rational(1, 2)}
    budget = [1]
    c = _exact_counterexample(a, x**3 / 3 - x**2 + 1, [x], pt, budget)
    assert isinstance(c, dict) and c["via"] == "checked_forms" and budget == [0]
    assert _exact_counterexample(a, x**3 / 3 - x**2, [x], pt, [1]) is False
    assert _exact_counterexample(a, x**3 / 3 - x**2 + sp.Rational(1, 10**20), [x], pt, [1]) is None
    assert _exact_counterexample(a, x**3 / 3 - x**2 + 1, [x], pt, [0]) is None
    assert _exact_counterexample(a, x**3 / 3 - x**2 + 1, [x], pt) is None
