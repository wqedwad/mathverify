"""Fourth audit (1 Oct 2026), part d4c: numeric evidence and the exact zero (`denetim/2026-10-01/d4c/`).

Each case was measured wrong on 158c220 (src = 1df0558):

* S1: the residue test took a nonzero integral below 10^-70·∫|f| for 0. ∫_0^{2π} e^(cos x)·cos 50x dx =
  2π·I_50(1) = 1.8e-79 and the claim 0 was CORRECT; SymPy's wrong 0 for ∫_{-1}^{1} (x + |cos x|/10^80) dx
  was confirmed, and the true step "= 2 sin(1)/10^80" refuted. A 0 now needs a symbolic certificate.
* S2: with no exact value from SymPy, a tanh-sinh value that missed a narrow peak at every level (error
  estimate 0) decided alone: ∫_0^1 (1 + e^(-10^8 (x - 1/3)^2)·e^(cos x)) dx = 1 was CORRECT (it is
  1.000456). Numbers alone never accept; they refute only with two methods at two precisions.
* S3 / D4-ADIM-C: evalf's '-0.e+0' (Dirichlet) and '1.6' (∫_0^oo sin²x/x²) were read as 40-digit values
  and the true steps refuted, the solutions INCORRECT.
* S4: a sum of more than 2000 terms was evaluated without a time limit in the verifier's own process.
* S5: an evalf zero with no significant bits ('0.e-168') counted as a proof of equality: tanh(100x) -> 1
  on (10, 20) and Σ_{k=0}^{5000} a^k -> 1/(1 - a) were CORRECT.
* S6: the odd ∫_{-1}^{1} sign(x)/√|x| dx = 0 was UNKNOWN (coverage lost in #14); the symmetry certificate
  gives it back.
"""
import time

import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
K = {"name": "k", "domain": "positive_integer"}
A_HALF = {"name": "a", "domain": "real", "constraints": ["a > -1/2", "a < 1/2"]}
X_10_20 = {"name": "x", "domain": "real", "constraints": ["x > 10", "x < 20"]}
PEAK = "exp(-10**8*(x - 1/3)**2)"
ABSCOS = "Integral(x + Abs(cos(x))/10**80, (x, -1, 1))"


def _task(kind, params, vars_, givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _dint(f, a, b):
    return _task("definite_integral", {"integrand": f, "var": "x", "a": str(a), "b": str(b)}, [X])


def _run(ir, payload, steps=(), kind="value"):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _steps(r):
    for layer in r.layers:
        if layer.layer == "steps.refute":
            return [s["status"] for s in layer.evidence.get("steps", [])]
    return []


X1 = _task("evaluate", {"expr": "x + 1"}, [X], ["x = 1"])


# --- S1 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("f,b", [("exp(cos(x))*cos(50*x)", "2*pi"), ("exp(cos(x))*cos(50*x)", "pi"),
                                 ("exp(sin(x))*cos(60*x)", "2*pi")])
def test_a_tiny_fourier_coefficient_is_not_certified_zero(f, b):
    assert _run(_dint(f, 0, b), "0").verdict != "CORRECT"


def test_sympys_wrong_zero_is_not_confirmed():
    assert _run(_task("evaluate", {"expr": ABSCOS}, [X]), "0").verdict != "CORRECT"
    assert _run(_dint("x + Abs(cos(x))/10**80", -1, 1), "0").verdict != "CORRECT"
    assert _steps(_run(X1, "2", [("compute", f"{ABSCOS} = 0")])) != ["verified"]
    # the true value is not refuted any more (it was INCORRECT before #14 too)
    assert _steps(_run(X1, "2", [("compute", f"{ABSCOS} = 2*sin(1)/10**80")])) != ["refuted"]
    assert _run(_dint("x + Abs(cos(x))/10**80", -1, 1), "2*sin(1)/10**80").verdict != "INCORRECT"


def test_the_zero_certificate():
    from mathverify.certify.calculus import certified_integral_value, zero_integral_certificate
    x = sp.Symbol("x", real=True)
    assert zero_integral_certificate(sp.exp(sp.cos(x)) * sp.cos(50 * x), x, 0, 2 * sp.pi)[0] is None
    assert zero_integral_certificate(x + sp.Abs(sp.cos(x)) / 10**80, x, -1, 1)[0] is None
    assert zero_integral_certificate(sp.sin(sp.sin(x)), x, 0, 2 * sp.pi)[0] is True       # odd about pi
    assert zero_integral_certificate(sp.sin(x**5) * sp.exp(sp.cos(x)), x, -1, 1)[0] is True
    assert zero_integral_certificate(x * sp.exp(-x**2), x, -sp.oo, sp.oo)[0] is True       # tails x^-2
    assert zero_integral_certificate(x / (1 + x**2), x, -sp.oo, sp.oo)[0] is None          # PV only
    v, ev = certified_integral_value(sp.log(x) / sp.sqrt(x), x, 0, 1)                     # manual antiderivative,
    assert v == -4 and ev["certificate"] == "fundamental_theorem_of_calculus"           # limit at 0 probed deep
    assert certified_integral_value(sp.cos(x), x, sp.pi, 0)[0] == 0
    assert certified_integral_value(x**2, x, 1, 0)[0] == sp.Rational(-1, 3)              # reversed range
    assert certified_integral_value(sp.Abs(x), x, -1, 2)[0] == sp.Rational(5, 2)          # split at 0
    assert certified_integral_value(1 / x**2, x, -1, 1)[0] is None      # F = -1/x jumps inside: divergent
    # the odd part has no antiderivative; the part even about the midpoint does
    v, ev = certified_integral_value(sp.sin(x**5) * sp.exp(sp.cos(x)) + 1, x, -1, 1)
    assert v == 2 and ev["symmetrized"] == "1"
    assert certified_integral_value(1 / x + 1, x, -1, 1)[0] is None      # even part 1, odd part not integrable
    from mathverify.certify.calculus import _checked_difference
    assert _checked_difference(x**3, x**2, x, sp.S.Zero, sp.S.One, 8.0) is None          # F' != g
    assert _checked_difference(x**3 / 3, x**2, x, sp.S.Zero, sp.S.One, 8.0) == sp.Rational(1, 3)


def test_a_divergent_integral_has_no_antiderivative_value():
    assert _run(_dint("1/x**2", -1, 1), "-2").verdict != "CORRECT"


# --- S2 ---------------------------------------------------------------------------------------------
def test_a_quadrature_alone_never_accepts():
    assert _run(_dint(f"1 + {PEAK}*exp(cos(x))", 0, 1), "1").verdict != "CORRECT"
    assert _run(_dint(f"sin(x**5)*exp(cos(x)) + {PEAK}", -1, 1), "0").verdict != "CORRECT"
    assert _run(_dint("sin(x**5)*exp(cos(x)) + 1", -1, 1), "2 + 10**(-40)").verdict != "CORRECT"


def test_a_numeric_refutation_needs_two_methods_and_a_nonzero_error():
    from mathverify.certify.calculus import integral_enclosure, integral_excludes
    x = sp.Symbol("x", real=True)
    peak = 1 + sp.exp(-10**8 * (x - sp.Rational(1, 3))**2) * sp.exp(sp.cos(x))
    assert integral_excludes(peak, x, 0, 1, sp.Rational(1000456, 10**6))[0] is False   # an error estimate of 0
    assert integral_enclosure(x**sp.Rational(-999, 1000), x, 0, 1) is None             # the methods disagree
    # Gauss-Legendre's own error (0.1) widens the enclosure of an end-singular integrand: nothing refuted
    assert integral_excludes(sp.log(x) / sp.sqrt(x), x, 0, 1, -3)[0] is False
    no, _ = integral_excludes(sp.Abs(sp.cos(x)), x, -1, 1, 0)
    assert no is True


def test_a_step_is_refuted_only_outside_the_enclosure():
    """SymPy has no value for ∫_0^1 e^(cos x) dx = 2.34157484171305316492...: both methods, both precisions."""
    r = _run(X1, "2", [("compute", "Integral(exp(cos(x)), (x, 0, 1)) = 2")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]
    # 30 digits of the value: inside the enclosure (width ~2e-17), so not refuted
    r = _run(X1, "2", [("compute", "Integral(exp(cos(x)), (x, 0, 1)) = 2341574841713053164922975186216/10**30")])
    assert _steps(r) != ["refuted"]


def test_methods_that_disagree_give_no_enclosure(monkeypatch):
    """Gauss-Legendre's error estimates were honest in every case measured, so the guard is exercised with
    made-up quadratures: two methods that disagree beyond their estimates enclose nothing."""
    from mathverify.certify import calculus
    from mathverify.sandbox import CasResult

    def fake(fn, *args, **kw):
        if fn.endswith(":breakpoints_of"):
            return CasResult(ok=True, value=[])
        if fn.endswith(":quad_breakpoints"):
            return CasResult(ok=True, value=("1.0" if args[6] == "tanh-sinh" else "1.5", "1e-30"))
        raise AssertionError(fn)

    monkeypatch.setattr(calculus, "sb_run", fake)
    x = sp.Symbol("x", real=True)
    assert calculus.integral_enclosure(sp.exp(sp.cos(x)), x, 0, 1) is None


def test_sympys_zero_without_a_certificate_is_no_exact_value(monkeypatch):
    """A SymPy 0 nothing proves (here made up for ∫_0^1 e^(cos x) dx = 2.3416) is dropped: the claim 0
    is then refuted by the two quadratures, not left UNKNOWN by a 'symbolic-numeric disagreement'."""
    from mathverify.certify import calculus
    real = calculus.sb_run

    def fake(fn, *args, **kw):
        if fn.endswith(":integrate_symbolic") and len(args) == 4:
            from mathverify.sandbox import CasResult
            return CasResult(ok=True, value=sp.S.Zero)
        return real(fn, *args, **kw)

    monkeypatch.setattr(calculus, "sb_run", fake)
    r = _run(_dint("exp(cos(x))", 0, 1), "0")
    assert r.verdict == "INCORRECT"


def test_checked_forms_takes_no_uncertified_zero(monkeypatch):
    """SymPy's 0 (made up here for ∫_0^1 e^(cos x) dx) with no certificate is no value of the form."""
    import mathverify.sandbox as sandbox
    from mathverify.equiv.forms import UnverifiedForm, checked_forms
    real = sandbox.run

    def fake(fn, *args, **kw):
        if fn.endswith(":doit_expr"):
            from mathverify.sandbox import CasResult
            return CasResult(ok=True, value=sp.S.Zero)
        return real(fn, *args, **kw)

    monkeypatch.setattr(sandbox, "run", fake)
    x = sp.Symbol("x", real=True)
    with pytest.raises(UnverifiedForm):
        checked_forms(sp.Integral(sp.exp(sp.cos(x)), (x, 0, 1)))
    assert checked_forms(sp.Integral(sp.sin(sp.sin(x)), (x, 0, 2 * sp.pi))) == 0     # certified: odd about pi


def test_an_odd_singular_integrand_without_antiderivative_needs_the_power_bound():
    """sign(x)·|x|^(-2/3)·e^(cos x): no antiderivative, odd, |f|·|x|^(2/3) -> e at 0."""
    assert _run(_dint("sign(x)*Abs(x)**(-2/3)*exp(cos(x))", -1, 1), "0").verdict == "CORRECT"
    assert _run(_dint("sign(x)*Abs(x)**(-1)*exp(cos(x))", -1, 1), "0").verdict != "CORRECT"   # divergent


# --- S3 / D4-ADIM-C ---------------------------------------------------------------------------------
@pytest.mark.parametrize("claim", ["Integral(sin(x)/x, (x, 0, oo)) = pi/2",
                                   "Integral(sin(x)**2/x**2, (x, 0, oo)) = pi/2",
                                   "2*Integral(sin(x)/x, (x, 0, oo)) = pi",
                                   "Integral(cos(x)/(1 + x**2), (x, 0, oo)) = pi/(2*E)"])
def test_a_true_infinite_range_step_is_not_refuted(claim):
    for kind in ("compute", "eq"):
        r = _run(X1, "2", [(kind, claim)])
        assert r.verdict == "CORRECT" and _steps(r) != ["refuted"], (kind, claim)


def test_evalf_without_significant_digits_is_no_value():
    from mathverify.equiv.forms import _numeric
    x = sp.Symbol("x", real=True)
    assert _numeric(sp.Integral(sp.sin(x) / x, (x, 0, sp.oo)), 8.0) is None
    assert _numeric(sp.Integral(sp.sin(x)**2 / x**2, (x, 0, sp.oo)), 8.0) is None
    v, _ = _numeric(sp.Integral(sp.exp(-x), (x, 0, sp.oo)), 8.0)
    assert abs(v - 1) < 1e-30


def test_an_infinite_range_has_a_numeric_value_now():
    """The quadrature takes an infinite end (it raised before), so SymPy's exact value is confirmed."""
    assert _run(_dint("exp(-x)", 0, "oo"), "1").verdict == "CORRECT"
    assert _run(_dint("exp(-x)", 0, "oo"), "2").verdict == "INCORRECT"


def test_a_wrong_infinite_range_step_is_still_refuted():
    r = _run(X1, "2", [("compute", "Integral(exp(-x), (x, 0, oo)) = 2")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]
    r = _run(X1, "2", [("compute", "Integral(exp(-x), (x, 0, oo)) = 1")])
    assert r.verdict == "CORRECT" and _steps(r) == ["verified"]


# --- S4 ---------------------------------------------------------------------------------------------
def test_a_sum_too_long_to_evaluate_is_not_evaluated():
    ir = _task("simplify_expression", {"expr": "Sum(a**k, (k, 0, 10**7))"}, [A_HALF, K], shape="expression")
    t0 = time.time()
    assert _run(ir, "1/(1 - a)", kind="expression").verdict != "CORRECT" and time.time() - t0 < 60


@pytest.mark.parametrize("hi", ["3000", "100000"])
def test_a_long_sum_returns_in_time(hi):
    ir = _task("simplify_expression", {"expr": f"Sum(x**k/factorial(k), (k, 0, {hi}))"}, [X, K], shape="expression")
    t0 = time.time()
    r = _run(ir, "exp(x)", kind="expression")
    assert r.verdict != "CORRECT" and time.time() - t0 < 60


# --- S5 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("expr,claim,vars_", [("Sum(a**k, (k, 0, 5000))", "1/(1 - a)", [A_HALF, K]),
                                              ("tanh(100*x)", "1", [X_10_20]),
                                              ("cos(x/10**300)", "1", [X_10_20]),
                                              ("log(1 + x/10**600)", "0", [X_10_20])])
def test_a_zero_without_significant_bits_proves_nothing(expr, claim, vars_):
    """evalf's '0.e-168', and its exact 0 for log(1 + 15/10^600) (rounded to log 1), are no proof."""
    ir = _task("simplify_expression", {"expr": expr}, vars_, shape="expression")
    assert _run(ir, claim, kind="expression").verdict != "CORRECT"


def test_the_difference_check_itself():
    from mathverify.equiv.random_point import _definite_nonzero_difference
    x = sp.Symbol("x", real=True)
    pts = [{x: sp.Rational(15)}, {x: sp.Rational(31, 2)}]
    w, unsure = _definite_nonzero_difference(sp.tanh(100 * x) - 1, [x], pts, sp.tanh(100 * x), sp.S.One)
    assert w is None and unsure == 2
    w, unsure = _definite_nonzero_difference(sp.sin(x)**2 + sp.cos(x)**2 - 1, [x], pts,
                                             sp.sin(x)**2 + sp.cos(x)**2, sp.S.One)
    assert w is None and unsure == 0           # equal at each point: proved there, not read off evalf


def test_exact_zeros_of_angle_sums_and_exponentials():
    """With evalf's zero no longer a proof, a point is decided by exact methods; these two keep the
    textbook identities that only random points had decided (atan x + atan(1/x) = π/2 for x > 0, ...)."""
    from mathverify.sandbox import run as sb_run

    def zero(d):          # in the sandbox, as the verifier runs it: the rewrites of a nonzero d can take long
        r = sb_run("mathverify.equiv.numeric:exact_zero_test", d, timeout=10.0)
        return r.ok and r.value is True

    r = sp.Rational
    assert zero(sp.atan(r(3, 7)) + sp.atan(r(7, 3)) - sp.pi / 2)
    assert zero(4 * sp.atan(r(1, 5)) - sp.atan(r(1, 239)) - sp.pi / 4)      # Machin
    assert zero(sp.asin(r(1, 3)) + sp.acos(r(1, 3)) - sp.pi / 2)
    assert not zero(sp.atan(r(1, 2)) + sp.atan(r(1, 3)) - sp.pi / 4 - 2 * sp.pi)   # e^(iNd) = 1 only
    assert not zero(sp.atan(r(3, 7)) + sp.atan(r(7, 3)) - sp.pi / 2 + r(1, 10**50))
    c = r(123456, 1000)
    assert zero(sp.tanh(c) - (sp.exp(2 * c) - 1) / (sp.exp(2 * c) + 1))
    assert not zero(sp.tanh(c) - (sp.exp(2 * c) - 1) / (sp.exp(2 * c) + 1) + sp.exp(-1000))
    XP = {"name": "x", "domain": "real", "constraints": ["x > 0"]}
    for expr, claim, v in [("atan(x) + atan(1/x)", "pi/2", XP), ("tanh(x)", "(exp(2*x) - 1)/(exp(2*x) + 1)", X),
                           ("atan(x) - atan(x/2)", "atan(x/(2 + x**2))", X)]:
        ir = _task("simplify_expression", {"expr": expr}, [v], shape="expression")
        assert _run(ir, claim, kind="expression").verdict == "CORRECT", expr


def test_controls_keep_their_verdicts():
    ir = _task("simplify_expression", {"expr": "tanh(100*x)"}, [X], shape="expression")
    assert _run(ir, "1", kind="expression").verdict == "INCORRECT"
    ir = _task("simplify_expression", {"expr": "sin(x)**2 + cos(x)**2"}, [X], shape="expression")
    assert _run(ir, "1", kind="expression").verdict == "CORRECT"
    ir = _task("simplify_expression", {"expr": "1/(x - 1) + exp(-1000)"}, [X], shape="expression")
    assert _run(ir, "1/(x - 1)", kind="expression").verdict == "INCORRECT"


# --- S6 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("f", ["sign(x)/sqrt(Abs(x))", "sign(x)*Abs(x)**(-2/3)"])
def test_an_odd_integrable_singular_integrand_has_integral_zero(f):
    assert _run(_dint(f, -1, 1), "0").verdict == "CORRECT"
    assert _run(_dint(f, -1, 1), "1").verdict == "INCORRECT"


@pytest.mark.parametrize("f", ["1/x", "x/Abs(x)**2", "x*exp(x**(-2))"])
def test_a_divergent_odd_integrand_is_not_zero(f):
    assert _run(_dint(f, -1, 1), "0").verdict != "CORRECT"
