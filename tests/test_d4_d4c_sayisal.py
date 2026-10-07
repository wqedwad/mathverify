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
    # 30 digits of ∫_0^1 e^(cos x) dx: the quadrature agrees, no enclosure is that narrow, no exact value
    assert _run(_dint("exp(cos(x))", 0, 1), "2341574841713053164922975186216/10**30").verdict == "UNKNOWN"


SECH = "x**2 + 10**4/cosh(10**4*(x - 1/3))**2"                     # a peak of width 1e-4 at 1/3
SECH_TRUE = "1/3 + tanh(20000/3) + tanh(10000/3)"


def test_a_numeric_refutation_needs_a_rigorous_enclosure():
    """Review of d4c (2 Oct 2026): tanh-sinh and Gauss-Legendre missed a narrow peak together, with an
    error estimate small but not 0, and refuted true values. The interval enclosure cannot miss it."""
    import mpmath as mp
    from mathverify.certify.calculus import integral_excludes, rigorous_integral
    x = sp.Symbol("x", real=True)
    peak = 1 + sp.exp(-10**8 * (x - sp.Rational(1, 3))**2) * sp.exp(sp.cos(x))
    assert integral_excludes(peak, x, 0, 1, 1)[0] is True               # the quadratures said 1
    true = sp.Rational(1000455999664210, 10**15)                         # mpmath with the peak split off
    assert integral_excludes(peak, x, 0, 1, true)[0] is False
    f = sp.sympify(SECH, locals={"x": x})
    assert integral_excludes(f, x, 0, 1, sp.sympify(SECH_TRUE))[0] is False
    assert integral_excludes(f, x, 0, 1, sp.Rational(1, 3))[0] is True
    lo, hi = rigorous_integral(sp.exp(sp.cos(x)), x, 0, 1)
    assert lo <= mp.mpf("2.341574841713053164922975186216") <= hi and hi - lo < 1e-9
    assert rigorous_integral(sp.erf(x), x, 0, 1) is None                 # no interval extension
    assert rigorous_integral(sp.exp(-x), x, 0, sp.oo) is None            # no infinite range
    lo, hi = rigorous_integral(1 / x, x, -1, 1)                          # a singularity: unbounded
    assert not (mp.isfinite(lo) and mp.isfinite(hi))
    assert integral_excludes(1 / x, x, -1, 1, 0)[0] is False
    assert integral_excludes(sp.Abs(sp.cos(x)), x, -1, 1, 0)[0] is True


def test_an_end_that_is_not_a_binary_number_is_enclosed():
    """π as an end is an interval; the piece between it and the binary cells counts (here 10^40 per unit)."""
    from mathverify.certify.calculus import integral_excludes
    x = sp.Symbol("x", real=True)
    assert integral_excludes(sp.Integer(10)**40, x, 0, sp.pi, 10**40 * sp.pi)[0] is False
    assert integral_excludes(sp.Integer(10)**40, x, sp.pi, 4, 10**40 * (4 - sp.pi))[0] is False
    # ends 10^20·π - 1 and 10^20·π are intervals ~1e-10 wide at 30 digits: ∫ 1 over the range is exactly 1,
    # and without the end pieces the enclosure would stop 1e-10 short of it and refute it
    E = sp.pi * 10**20
    assert integral_excludes(sp.Integer(1), x, E - 1, E, 1)[0] is False
    assert integral_excludes(sp.Integer(1), x, E - 1, E, 1 + sp.Rational(1, 10**6))[0] is True


def test_sympys_value_refutes_only_with_a_proof_or_an_enclosure(monkeypatch):
    """A claim SymPy's exact value contradicts is refuted by a value proved symbolically (e^x has the
    antiderivative e^x) or by a rigorous enclosure. Without a proof (taken away here) a difference of
    10^-40 from SymPy's sin(1) decides nothing; one of 10^-3 is outside the enclosure."""
    assert _run(_dint("exp(x)", "0", "pi*sqrt(163)"), "262537412640768743").verdict == "INCORRECT"
    from mathverify.certify import calculus
    monkeypatch.setattr(calculus, "certified_integral_value", lambda *a, **k: (None, {}))
    assert _run(_dint("cos(x)", "0", "1"), "sin(1) + 10**(-40)").verdict == "UNKNOWN"
    assert _run(_dint("cos(x)", "0", "1"), "sin(1) + 10**(-3)").verdict == "INCORRECT"
    # and without a proof SymPy's value accepts nothing either (round 3, YO-2)
    assert _run(_dint("cos(x)", "0", "1"), "sin(1)").verdict == "UNKNOWN"


def test_a_proved_value_overrides_a_wrong_sympy_value(monkeypatch):
    """SymPy's value (made up wrong here: sin 1 + 1 for ∫_0^1 cos x dx) loses to the antiderivative's."""
    from mathverify.certify import calculus
    from mathverify.sandbox import CasResult
    real = calculus.sb_run

    def fake(fn, *args, **kw):
        if fn.endswith(":integrate_symbolic") and len(args) == 4:
            return CasResult(ok=True, value=sp.sin(1) + 1)
        return real(fn, *args, **kw)

    monkeypatch.setattr(calculus, "sb_run", fake)
    assert _run(_dint("cos(x)", "0", "1"), "sin(1)").verdict == "CORRECT"
    assert _run(_dint("cos(x)", "0", "1"), "sin(1) + 1").verdict == "INCORRECT"


def test_a_true_value_with_a_narrow_peak_is_not_refuted():
    assert _run(_dint(SECH, 0, 1), SECH_TRUE).verdict != "INCORRECT"
    assert _run(_dint(SECH, 0, 1), "1/3").verdict == "INCORRECT"
    r = _run(X1, "2", [("compute", f"Integral({SECH}, (x, 0, 1)) = {SECH_TRUE}")])
    assert r.verdict == "CORRECT" and _steps(r) != ["refuted"]
    r = _run(X1, "2", [("compute", f"Integral({SECH}, (x, 0, 1)) = 1/3")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]


def test_a_declared_tolerance_is_decided_by_the_enclosure():
    """SymPy has no value for ∫_0^1 sin(sin x) dx = 0.4306061031...: the tolerance window holds a
    rigorous enclosure (accepted) or misses it (refuted)."""
    def di(tol):
        ir = _dint("sin(sin(x))", 0, 1)
        ir["task"]["params"]["rel_tol"] = tol
        return ir
    assert _run(di("1e-3"), "0.4306").verdict == "CORRECT"
    assert _run(di("1e-3"), "0.5").verdict == "INCORRECT"
    assert _run(_dint("sin(sin(x))", 0, 1), "0.4306").verdict == "INCORRECT"      # no tolerance: exact claim


def test_a_step_is_refuted_only_outside_the_enclosure():
    """SymPy has no value for ∫_0^1 e^(cos x) dx = 2.34157484171305316492..."""
    r = _run(X1, "2", [("compute", "Integral(exp(cos(x)), (x, 0, 1)) = 2")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]
    # 30 digits of the value: no enclosure is that narrow, so not refuted
    r = _run(X1, "2", [("compute", "Integral(exp(cos(x)), (x, 0, 1)) = 2341574841713053164922975186216/10**30")])
    assert _steps(r) != ["refuted"]
    # two integrals: lhs - rhs evaluated with both enclosures
    r = _run(X1, "2", [("compute", "Integral(exp(cos(x)), (x, 0, 1)) + Integral(x, (x, 0, 1)) = 3")])
    assert _steps(r) == ["refuted"]
    r = _run(X1, "2", [("compute", "Integral(exp(cos(x)), (x, 0, 1)) + Integral(x, (x, 0, 1)) = "
                                   "2841574841713053164922975186216/10**30")])
    assert _steps(r) != ["refuted"]


def test_sympys_zero_without_a_certificate_is_no_exact_value(monkeypatch):
    """A SymPy 0 nothing proves (here made up for ∫_0^1 e^(cos x) dx = 2.3416) is dropped: the claim 0
    is then refuted by the rigorous enclosure, not left UNKNOWN by a 'symbolic-numeric disagreement'."""
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


def test_an_infinite_range_is_never_refuted_by_numbers():
    """No rigorous enclosure over an infinite range: the quadratures missed a peak there too (review)."""
    assert _run(_dint("exp(-x) + 10**4/cosh(10**4*(x - 1/3))**2", 0, "oo"), "2 + tanh(10**4/3)").verdict != "INCORRECT"
    r = _run(X1, "2", [("compute", "Integral(exp(-(x - 100)**2), (x, -oo, oo)) = sqrt(pi)")])
    assert r.verdict != "INCORRECT" and _steps(r) != ["refuted"]


def test_an_infinite_range_value_proved_symbolically_still_decides():
    """No numeric value on an infinite range, but the fundamental theorem with its end limits proves the
    value: it decides (coverage lost in the review of d4c, given back 6 Oct 2026)."""
    assert _run(_dint("exp(-x)", 0, "oo"), "1").verdict == "CORRECT"
    assert _run(_dint("exp(-x)", 0, "oo"), "2").verdict == "INCORRECT"
    assert _run(_dint("1/(1 + x**2)", "-oo", "oo"), "pi").verdict == "CORRECT"
    assert _run(_dint("exp(-x**2)", "-oo", "oo"), "sqrt(pi)").verdict != "INCORRECT"


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
    e = r(37, 10)                    # angles of numbers algebraic in e^(1/10): the Gudermann identities
    assert zero(sp.atan(sp.exp(e)) + sp.atan(sp.exp(-e)) - sp.pi / 2)
    assert zero(sp.asin(sp.tanh(e)) - sp.atan(sp.sinh(e)))
    assert zero(2 * sp.atan(sp.tanh(e / 2)) - sp.atan(sp.sinh(e)))
    assert not zero(sp.asin(sp.tanh(e)) - sp.atan(sp.sinh(e)) + sp.pi)
    assert not zero(sp.atan(sp.exp(e)) - sp.atan(sp.exp(-e)))
    c = r(123456, 1000)
    assert zero(sp.tanh(c) - (sp.exp(2 * c) - 1) / (sp.exp(2 * c) + 1))
    assert not zero(sp.tanh(c) - (sp.exp(2 * c) - 1) / (sp.exp(2 * c) + 1) + sp.exp(-1000))
    XP = {"name": "x", "domain": "real", "constraints": ["x > 0"]}
    for expr, claim, v in [("atan(x) + atan(1/x)", "pi/2", XP), ("tanh(x)", "(exp(2*x) - 1)/(exp(2*x) + 1)", X),
                           ("atan(exp(x)) + atan(exp(-x))", "pi/2", XP), ("asin(tanh(x))", "atan(sinh(x))", XP),
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


# --- sibling paths of the enclosure (6 Oct 2026) ------------------------------------------------------
# nsum's value alone refuted a series: with one-signed terms and the same value at 30 and 50 digits,
# Σ (1/k² + c·e^(-(k - 1000)²/w)) came out π²/6 (the term far out never seen) and the true value was
# INCORRECT. A number alone refutes no series now; SymPy's value confirmed by nsum still decides.
def _series(term):
    return _task("series_sum", {"term": term, "var": "k", "lo": "1", "hi": "oo"}, [K])


@pytest.mark.parametrize("term,truth", [
    ("1/k**2 + exp(-(k - 1000)**2)", "3.41757127167487858950366571780"),
    ("1/k**2 + 1000000*exp(-(k - 1000)**2)", "1772638.84976071900125768702357"),
    ("1/k**2 + exp(-(k - 1000)**2/100)", "19.3694725759033867094540900001"),
])
def test_nsum_alone_refutes_no_series(term, truth):
    # truth: π²/6 + Σ_j c·e^(-j²/w) (Jacobi θ₃), a 50-digit sum of the bump
    assert _run(_series(term), truth).verdict != "INCORRECT"


def test_a_series_value_sympy_and_nsum_agree_on_still_decides():
    assert _run(_series("1/(k*(k + 1))"), "1/2").verdict == "INCORRECT"
    assert _run(_series("1/(k*(k + 1))"), "1").verdict == "CORRECT"
    assert _run(_series("1/k**2"), "pi**2/6").verdict == "CORRECT"


# === round 3: the attack on round 2 (7 Oct 2026, d4/saldiri/d4c2) =========================================
def _ext(f, which, interval):
    return _task("extremum", {"f": f, "var": "x", "which": which, "interval": interval}, [X])


def _dtol(f, a, b, tol):
    ir = _dint(f, a, b)
    ir["task"]["params"]["rel_tol"] = tol
    return ir


# --- YO-1: the direction of a difference below 40 digits ------------------------------------------------------
@pytest.mark.parametrize("f,which,interval,wrong,right", [
    ("1 + x/10**50", "max", "[0, 1]", "1", "1 + 10**(-50)"),
    ("x*(tanh(100) - 1) + 1", "max", "[0, 1]", "tanh(100)", "1"),
    ("sqrt(10**100 + x)", "max", "[0, 1]", "10**50", "sqrt(10**100 + 1)"),
    ("1 - x/10**50", "min", "[0, 1]", "1", "1 - 10**(-50)"),
    ("x**2", "max", "[-1, 1 + 10**(-50)]", "1", "(1 + 10**(-50))**2"),
])
def test_an_extremum_below_forty_digits_is_compared_by_a_certified_sign(f, which, interval, wrong, right):
    assert _run(_ext(f, which, interval), wrong).verdict == "INCORRECT"
    assert _run(_ext(f, which, interval), right).verdict == "CORRECT"


def test_strictly_better_is_three_valued():
    from mathverify.certify.extremum import _num, _strictly_better
    one, more = sp.Integer(1), 1 + sp.Rational(1, 10**50)
    assert _strictly_better(more, _num(more), one, _num(one), True) is True
    assert _strictly_better(one, _num(one), more, _num(more), True) is False
    assert _strictly_better(more, _num(more), one, _num(one), False) is False
    assert _strictly_better(one, _num(one), one, _num(one), True) is False
    assert _strictly_better(one, None, one, _num(one), True) is None


def test_a_non_empty_superlevel_set_closes_the_evt_route(monkeypatch):
    """No candidate beats the claim (made so here), but SymPy's set of better points is not empty: the extreme
    value theorem proves nothing."""
    from mathverify.certify import extremum
    assert _run(_ext("Max(1, 1 + x/10**50)", "max", "[0, 1]"), "1").verdict != "CORRECT"
    monkeypatch.setattr(extremum, "_strictly_better", lambda *a: False)
    assert _run(_ext("1 + x/10**50", "max", "[0, 1]"), "1").verdict == "UNKNOWN"


def test_an_undecided_candidate_closes_the_evt_route(monkeypatch):
    """A candidate whose comparison with the claim is undecided (made so here), and no set of better points
    from SymPy (taken away here): the extreme value theorem proves nothing."""
    from mathverify.certify import extremum
    from mathverify.sandbox import CasResult
    real = extremum.sb_run

    def fake(fn, *args, **kw):
        if fn.endswith(":solveset_in") and isinstance(args[0], (sp.StrictGreaterThan, sp.StrictLessThan)):
            return CasResult(ok=False, error="taken away")
        return real(fn, *args, **kw)

    monkeypatch.setattr(extremum, "sb_run", fake)
    monkeypatch.setattr(extremum, "_strictly_better", lambda *a: None)
    assert _run(_ext("x*(1 - x)", "max", "[0, 1]"), "1/4").verdict == "UNKNOWN"


# --- YO-2: SymPy's value only with a certificate ----------------------------------------------------------
YO2_F = "atan(tan(x)) + 1 + pi**2/(2*sqrt(pi))*10**4*exp(-10**8*(x - 1/3)**2)"   # ∫_0^π = π + π²/2


def test_sympys_value_and_an_agreeing_quadrature_accept_nothing():
    """SymPy's π for ∫_0^π F (the value is π + π²/2) and tanh-sinh agreed: 3.14159265358979 was accepted with
    rel_tol 1e-9 (the declared tolerance also let the two "agree")."""
    assert _run(_dtol(YO2_F, 0, "pi", "1e-9"), "3.14159265358979").verdict != "CORRECT"
    ev = _task("evaluate", {"expr": f"Integral({YO2_F}, (x, 0, pi))", "rel_tol": "1e-9"}, [X])
    assert _run(ev, "3.14159265358979").verdict != "CORRECT"
    G = "atan(tan(x)) + 174"                                                           # ∫_0^π = 174π
    assert _run(_dtol(G, 0, "pi", "0.01"), "536.4").verdict == "INCORRECT"
    assert _run(_dtol(G, 0, "pi", "0.01"), "546").verdict == "CORRECT"


def test_a_proof_that_a_converged_quadrature_contradicts_decides_nothing(monkeypatch):
    """A certificate's value (made up wrong here: sin 1 + 1 for ∫_0^1 cos x dx) that the converged quadrature
    contradicts: something is wrong, nothing is decided."""
    from mathverify.certify import calculus
    monkeypatch.setattr(calculus, "certified_integral_value", lambda *a, **k: (sp.sin(1) + 1, {}))
    assert _run(_dint("cos(x)", 0, 1), "sin(1) + 1").verdict == "UNKNOWN"
    assert _run(_dtol("cos(x)", 0, 1, "1e-3"), "1.8414").verdict == "UNKNOWN"


def test_sympys_value_off_by_less_than_any_enclosure_is_not_taken():
    """SymPy gives 2 for ∫_{-1}^{1} (1 + |cos x|/10^80) dx; it is 2 + 2 sin(1)/10^80."""
    f = "1 + Abs(cos(x))/10**80"
    assert _run(_dint(f, -1, 1), "2").verdict != "CORRECT"
    assert _run(_task("evaluate", {"expr": f"Integral({f}, (x, -1, 1))"}, [X]), "2").verdict != "CORRECT"
    assert _run(_dint(f, -1, 1), "2 + 2*sin(1)/10**80").verdict == "CORRECT"


# --- YO-3: sample points off the decimal grid ---------------------------------------------------------------
@pytest.mark.parametrize("expr,claim", [("x**2", "x**2 + sin(3000000*pi*x)"), ("sin(3000000*pi*x)", "0"),
                                        ("cos(6000000*pi*x)", "1"), ("x", "x + sin(2000000*pi*x)/1000000")])
def test_a_periodic_term_is_not_hidden_by_the_sample_grid(expr, claim):
    ir = _task("simplify_expression", {"expr": expr}, [X], shape="expression")
    assert _run(ir, claim, kind="expression").verdict != "CORRECT"


def test_identity_samples_are_off_the_decimal_grid():
    from mathverify.equiv.random_point import _PRIMES, _RATIONAL_POINTS, sample_points
    x = sp.Symbol("x", real=True)
    pts = [p[x] for p in sample_points({x: sp.S.Reals}, 30, 0, off_grid=True)]
    assert all(isinstance(v, sp.Rational) and v.q in _PRIMES for v in pts[:_RATIONAL_POINTS])
    assert all(not v.is_rational for v in pts[_RATIONAL_POINTS:])
    grid = [p[x] for p in sample_points({x: sp.S.Reals}, 30, 0)]          # a counterexample search: as before
    assert all(isinstance(v, sp.Rational) and 10**6 % v.q == 0 for v in grid)


def test_random_points_and_probes_each_see_a_periodic_term(monkeypatch):
    """The off-grid samples alone (probes taken away) and the irrational probes alone (samples on the old
    6-decimal grid) each find the difference sin(3·10^6·πx)."""
    from mathverify.equiv import random_point as rp
    x = sp.Symbol("x", real=True)
    a, b = x**2 + sp.sin(3000000 * sp.pi * x), x**2
    real_special, real_sample = rp._special_values, rp.sample_points
    monkeypatch.setattr(rp, "_special_values", lambda *a_, **k: [])
    assert rp.random_point_equal(a, b, x, sp.S.Reals)[0] is False
    monkeypatch.setattr(rp, "_special_values", real_special)
    monkeypatch.setattr(rp, "sample_points", lambda d, n, s, special=False, off_grid=False: real_sample(d, n, s))
    assert rp.random_point_equal(a, b, x, sp.S.Reals)[0] is False


def test_a_sign_must_stand_at_a_higher_precision():
    """Strict evalf gave asin(tanh x) - atan(sinh x) = 6.5e-61 with 103 significant bits at x = 139278301/1000033
    (asin evaluated where it is ill-conditioned); the difference is 0 (the Gudermann identity), and an off-grid
    sample point refuted the true identity."""
    from mathverify.equiv.numeric import certified_sign
    r = sp.Rational(139278301, 1000033)
    assert certified_sign(sp.asin(sp.tanh(r)) - sp.atan(sp.sinh(r))) in (0, None)
    assert certified_sign(sp.asin(sp.tanh(r)) - sp.atan(sp.sinh(r)) + sp.Rational(1, 10**40)) == 1
    X139 = _task("evaluate", {"expr": "x + 1"}, [X], ["x = 139278301/1000033"])
    r_ = _run(X139, "140278334/1000033", [("eq", "asin(tanh(x)) = atan(sinh(x))")])
    assert _steps(r_) != ["refuted"]


def test_sympy_equals_false_is_not_overruled_by_agreement(monkeypatch):
    import mathverify.equiv as equiv
    monkeypatch.setattr(equiv, "random_point_equal", lambda *a, **k: (True, {}))
    x = sp.Symbol("x", real=True)
    ok, ev = equiv.answers_equivalent(x**2 + sp.sin(3000000 * sp.pi * x), x**2, shape="expression",
                                      domain={x: sp.S.Reals})
    assert ok is None and ev.get("conflict") == "sympy_equals_false"
    ok, _ = equiv.answers_equivalent(sp.sin(x)**2 + sp.cos(x)**2 + x, x + 1, shape="expression", domain={x: sp.S.Reals})
    assert ok is True


# --- YO-4, RK-E, RK-F: one reading of a declared tolerance -------------------------------------------------
def test_read_tolerance_and_the_relative_error():
    from mathverify.equiv.numeric import num_equal, read_tolerance, within_rel_tol
    assert read_tolerance("1e-3") == (sp.Rational(1, 1000), False)
    assert read_tolerance(None) == (None, False)
    for bad in ("0", "-1e-3", "1", "2", "inf", "nan", "abc", True):
        assert read_tolerance(bad) == (None, True), bad
    assert read_tolerance("5", relative=False) == (5, False)
    t = sp.Rational(1, 1000)
    assert within_rel_tol(sp.Float("0.8406299346"), sp.sin(1), t) is True          # 9.995e-4 against v
    assert within_rel_tol(sp.Float("0.8405454"), sp.sin(1), t) is False
    assert within_rel_tol(sp.Float("0.0001"), 0, t) is None                         # v = 0: undefined
    assert within_rel_tol(0, 0, t) is True                                          # ... but the claim is v
    assert num_equal(sp.S.Zero, sp.Float(0), rel_tol=1e-25)[0] is True              # a form's 0 and its number
    assert num_equal(sp.Float("2.716"), sp.E, rel_tol=t)[0] is True
    assert num_equal(sp.Float("2.7155"), sp.E, rel_tol=t)[0] is False
    # against the reference b, not max(|a|, |b|): 0.105 of 2.3416, 0.095 of 2.5874
    assert num_equal(sp.Float("2.5874"), sp.Float("2.341574841713053"), rel_tol=0.1)[0] is False
    # exactly on the boundary, and two Rationals take the tolerance too
    assert num_equal(sp.Rational(1001, 3000), sp.Rational(1, 3), rel_tol=t)[0] is True
    assert num_equal(sp.Rational(1002, 3000), sp.Rational(1, 3), rel_tol=t)[0] is False


@pytest.mark.parametrize("tol,claim", [("1", "100"), ("2", "-5"), ("5", "10"), ("-1e-3", "2.34"), ("inf", "100"),
                                       ("nan", "2.34"), ("0", "2.34")])
def test_a_malformed_tolerance_decides_nothing(tol, claim):
    r = _run(_dtol("exp(cos(x))", 0, 1, tol), claim)
    assert r.verdict == "UNKNOWN"
    assert _run(_task("evaluate", {"expr": "E", "rel_tol": tol}, [X]), "E").verdict == "UNKNOWN"


def test_a_declared_tolerance_is_relative_to_the_true_value():
    assert _run(_dtol("exp(cos(x))", 0, 1, "0.1"), "2.5874").verdict == "INCORRECT"     # 0.105 against v
    assert _run(_dtol("exp(cos(x))", 0, 1, "0.1"), "2.12").verdict == "CORRECT"         # 0.0946
    assert _run(_dtol("cos(x)", 0, 1, "1e-3"), "0.8406299346").verdict == "CORRECT"     # 9.995e-4
    assert _run(_dtol("cos(x)", 0, 1, "1e-3"), "0.8405454").verdict == "INCORRECT"      # 1.1e-3
    assert _run(_dtol("sin(x)", -1, 1, "1e-3"), "0.0001").verdict == "UNKNOWN"          # v = 0
    ev = _task("evaluate", {"expr": "E", "rel_tol": "1e-3"}, [X])
    assert _run(ev, "2.716").verdict == "CORRECT"
    assert _run(ev, "2.7155").verdict == "INCORRECT"


# --- YO-5: the enclosure rounds outward ---------------------------------------------------------------------
def test_the_interval_of_abs_cosh_sech_holds_the_true_value():
    import mpmath as mp
    from mathverify.certify.enclosure import _DPS, _hull, iv_eval
    x = sp.Symbol("x", real=True)
    lo_ = mp.mpf("-2.92508604710079023192292879684828221797943115234375")
    hi_ = mp.mpf("-2.803578732815290575075550805195234715938568115234375")
    mp.iv.dps = _DPS
    with mp.workdps(_DPS):
        for e, true_lo, true_hi in ((sp.Abs(sp.atan(2 * x)), lambda: -mp.atan(2 * hi_), lambda: -mp.atan(2 * lo_)),
                                    (sp.cosh(sp.atan(2 * x)), lambda: mp.cosh(mp.atan(2 * hi_)),
                                     lambda: mp.cosh(mp.atan(2 * lo_))),
                                    (sp.sech(sp.atan(2 * x)), lambda: mp.sech(mp.atan(2 * lo_)),
                                     lambda: mp.sech(mp.atan(2 * hi_)))):
            B = iv_eval(e, {x: _hull(lo_, hi_)})
            blo, bhi = mp.make_mpf(B._mpi_[0]), mp.make_mpf(B._mpi_[1])
            with mp.workdps(80):
                assert blo <= true_lo() and true_hi() <= bhi, e
        # a Float with more bits than the working precision is taken exactly, not rounded
        f = sp.Float("1.000000000000000000000000000000000000000000000001", 60)
        B = iv_eval(f, {})
        with mp.workdps(80):
            assert mp.make_mpf(B._mpi_[0]) <= mp.mpf(f._mpf_) <= mp.make_mpf(B._mpi_[1]) and mp.make_mpf(B._mpi_[0]) > 1


# --- RK-A: erf on infinite ranges ---------------------------------------------------------------------------
@pytest.mark.parametrize("f,a,b,right,wrong", [("exp(-x**2)", "-oo", "oo", "sqrt(pi)", "2"),
                                               ("x**2*exp(-x**2/2)/sqrt(2*pi)", "-oo", "oo", "1", "2"),
                                               ("sqrt(x)*exp(-x)", 0, "oo", "sqrt(pi)/2", "1")])
def test_an_erf_primitive_proves_an_infinite_range_value(f, a, b, right, wrong):
    assert _run(_dint(f, a, b), right).verdict == "CORRECT"
    assert _run(_dint(f, a, b), wrong).verdict == "INCORRECT"


def test_the_domain_of_special_functions():
    from mathverify.certify.domain import definedness_conditions_strict
    x = sp.Symbol("x", real=True)
    for f in (sp.erf(x), sp.erfc(x), sp.erfi(x), sp.Si(x), sp.Shi(x), sp.fresnels(x)):
        assert definedness_conditions_strict(f, x) == [], f
    assert definedness_conditions_strict(sp.Ci(x), x) == [x > 0]
    assert definedness_conditions_strict(sp.polylog(2, x), x) == [x <= 1]


# --- RK-B: a singularity at an end of a finite range ---------------------------------------------------------
@pytest.mark.parametrize("f,claim", [("sinh(x)/x", "-100"), ("atan(x)/x", "-100"), ("asin(x)/x", "100"),
                                     ("log(1 + x)/x", "1"), ("(1 - cos(x))/x**2", "1"), ("log(x)/(1 + x)", "-1"),
                                     ("x**x", "100")])
def test_a_wrong_claim_with_an_end_singularity_is_refuted(f, claim):
    assert _run(_dint(f, 0, 1), claim).verdict == "INCORRECT"


def test_end_cells_are_bounded():
    import mpmath as mp
    from mathverify.certify.enclosure import _raw, _removable, from_raw, rigorous_enclosure
    x = sp.Symbol("x", real=True)
    assert _removable(sp.sin(x) / x, x, 0) == (sp.cos(x), 1)
    assert _removable(1 / x, x, 0) is None
    out = (_raw(mp.mpf("0.49")), _raw(mp.mpf("0.51")))
    lo, hi = (from_raw(v) for v in rigorous_enclosure(sp.log(x) * sp.log(1 - x), x, 0, 1, out, None, 4000, 120.0))
    assert lo <= 2 - mp.pi**2 / 6 <= hi < mp.mpf("0.49")
    lo, hi = (from_raw(v) for v in rigorous_enclosure(sp.sin(x) / x, x, 0, 1, None, None, 4000, 120.0))
    assert lo <= mp.mpf("0.946083070367183014941353313823") <= hi and hi - lo < 1e-6
    # a log weight is used only where it keeps its sign: log(2x) changes sign at 1/2 on the first cell [0, 1]
    true = mp.log(2) * 3 / 2 - mp.mpf(5) / 4                         # ∫_0^1 (1 + x) log(2x) dx
    c = (_raw(true - mp.mpf(10)**-12), _raw(true + mp.mpf(10)**-12))
    lo, hi = (from_raw(v) for v in rigorous_enclosure((1 + x) * sp.log(2 * x), x, 0, 1, c, None, 4000, 120.0))
    assert lo <= true <= hi


# --- RK-C: the enclosure's budget is the number of cells -------------------------------------------------------
def test_the_enclosure_budget_is_deterministic():
    from mathverify.certify.enclosure import rigorous_enclosure
    x = sp.Symbol("x", real=True)
    f = sp.exp(sp.sin(x) * sp.cos(x**2)) * sp.atan(x + 1)
    r1 = rigorous_enclosure(f, x, 0, 1, None, None, 300, 120.0)
    r2 = rigorous_enclosure(f, x, 0, 1, None, None, 300, 120.0)
    assert r1 is not None and r1 == r2
    assert rigorous_enclosure(f, x, 0, 1, None, None, 300, 0.0) is None     # the safety stop: no enclosure
