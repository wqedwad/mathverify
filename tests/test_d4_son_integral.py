"""The last attack on the merged state, lens 2: integrals and tolerances (decisions of 16 Oct 2026, "MERCEK 2";
the findings in `denetim/2026-10-01/son/` and the probe `denetim/2026-10-01/son/integral/sonda.py`).

False acceptances: G2YO-1 (sgn/Abs/Max/Min change branch at a pole of their argument too; a certified 0 is checked
against the numbers), G2YO-2 (without converged numbers the certificate's value is taken only inside a rigorous
enclosure), G2YO-3 (the cell proof cuts at the argument's poles), G2YO-4 (a declared absolute tolerance is decided
exactly). Unjust rejections and crashes: G2RK-1 (the real cube root's sign(u) is no jump where the primitive is
continuous), G2RK-7 (a complex quadrature value is no value), G2RK-10 (a convention condition of the primitive).
Coverage: G2RK-2 (tolerance against erf/S/C/Si values), G2RK-3/4 (the declared region x > 0 in the convention gate),
G2RK-5 (Piecewise integrands), G2RK-9 (x**x in the fundamental theorem).

Second round (independent audit of the branch, 21 Oct 2026): SI-YO-3 (a settled ladder reads its rungs' error
estimates), SI-YO-2 (a half-infinite enclosure says something only next to a close last rung; a power at an end is a
weight of the enclosure), SON-INT-RK-1 (a complex claim within a declared tolerance), SON-INT-RK-2 (the certificate's
enclosure settles once it stops narrowing).

New names are imported inside the tests, so that the old code fails each test on its own.
"""
from __future__ import annotations

import mpmath as mp
import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "real", "constraints": ["x > 0"]}
x = sp.Symbol("x", real=True)


def _ir(kind, params, vars_=(X,), givens=(), shape="scalar", options=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}
    if options:
        d["options"] = options
    return d


def _dint(f, a, b, options=None, **tol):
    return _ir("definite_integral", dict({"integrand": f, "var": "x", "a": str(a), "b": str(b)}, **tol), options=options)


def _ev(e, vars_=(X,), **tol):
    return _ir("evaluate", dict({"expr": e}, **tol), vars_)


def _anti(f, vars_=(X,)):
    return _ir("antiderivative", {"integrand": f, "var": "x"}, vars_, shape="expression")


def _der(f, vars_=(X,)):
    return _ir("derivative", {"f": f, "var": "x"}, vars_, shape="expression")


def _sol(payload, steps=(), option=None, kind="value"):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": "compute", "claim": c, "from": [], "text": ""}
                                            for i, c in enumerate(steps)]}


def _v(q, payload, **kw):
    return verify(q, _sol(payload, **kw)).verdict


def _step(claim):
    r = verify(_ir("evaluate", {"expr": "x + 1"}, (X,), ["x = 1"]), _sol("2", [claim]))
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    return layer.evidence["steps"][-1]["status"]


def _no_exception(r):
    return not any("layer_exception" in (la.flags or []) for la in r.layers)


SG = "sign((x - 1)/(x + 1))"
SG2 = "sign((x - 1)/(x + 2))"


# G2YO-1 ---------------------------------------------------------------------------------------------------------
def test_the_switch_points_hold_the_poles_of_the_argument():
    from mathverify.certify.calculus import _switch_points
    assert _switch_points(sp.sign((x - 1) / (x + 1)), x, -2, 4, 8) == [-1, 1]
    assert _switch_points(sp.sign(1 / (x - 1)), x, 0, 3, 8) == [1]
    assert _switch_points(sp.Max(x, 1 / x), x, -2, sp.Rational(1, 4), 8) == [-1, 0]
    # an argument with no real value on a piece of the range: no cut list, no certificate
    assert _switch_points(sp.sign(sp.sqrt(x) - 1), x, -1, 4, 8) is None


@pytest.mark.parametrize("q,wrong,true", [
    (_dint(SG, -2, 4), "0", "2"),
    (_dint("((x - 1)/(x + 1))/Abs((x - 1)/(x + 1))", -2, 4), "0", "2"),
    (_dint("sign(x/(x + 1))", "-3/2", "3/2"), "0", "1"),
    (_dint("sign(1/(x - 1))", 0, 3), "3", "1"),
    (_ev(f"Integral({SG2}, (x, -3, 3))"), "-2", "0"),
    (_ev("Integral(sign((x - 2)/(x + 1)), (x, -3, 3))"), "-4", "0"),
])
def test_a_sign_through_a_pole(q, wrong, true):
    assert _v(q, wrong) == "INCORRECT"
    assert _v(q, true) == "CORRECT"


def test_the_options_and_the_steps_of_a_sign_through_a_pole():
    opt = {"A": "-2", "B": "0", "C": "1", "D": "2", "E": "3"}
    assert _v(_dint(SG, -2, 4, options=opt), "0", option="B") != "CORRECT"
    assert _v(_dint(SG, -2, 4, options=opt), "2", option="D") != "INCORRECT"
    assert _step(f"Integral({SG}, (x, -2, 4)) = 0") != "verified"
    assert _step(f"Integral({SG}, (x, -2, 4)) = 2") != "refuted"


@pytest.mark.parametrize("q,claim", [
    (_dint("Max(x, x + 1/(x - 1/3) - 10)", -1, 1), "0"),
    (_dint("Min(x, 1/x)", "-1/4", 2), "log(2) + 15/32"),
    (_dint("Max(x, 1/x)", -2, "1/4"), "-log(2) - 15/32"),
    (_ev("Integral(Max(x, 1/x), (x, -2, 1/4))"), "-log(2) - 15/32"),
    # an argument that is no real number on [-1, 0): no integral, and no cut at its zero alone
    (_ev("Integral(sign(sqrt(x) - 1), (x, -1, 4))"), "1"),
])
def test_a_divergent_or_undefined_integral_has_no_finite_value(q, claim):
    assert _v(q, claim) != "CORRECT"


def _planted(monkeypatch, value, numbers=False):
    from mathverify.certify import calculus
    monkeypatch.setattr(calculus, "certified_integral_value", lambda *a, **k: (sp.sympify(value), {"planted": True}))
    if not numbers:
        monkeypatch.setattr(calculus, "definite_integral_numeric", lambda *a, **k: (None, {"converged": False}))


def test_a_certified_zero_is_checked_against_converged_numbers(monkeypatch):
    _planted(monkeypatch, "0", numbers=True)
    assert _v(_dint("x", -1, 2), "0") == "INCORRECT"          # the enclosure misses 0: the claim meets it alone
    assert _v(_dint("x", -1, 2), "3/2") != "INCORRECT"
    assert _v(_dint("x**3", -1, 1), "0") == "CORRECT"         # a true 0 against the quadrature's noise


# G2YO-2 ---------------------------------------------------------------------------------------------------------
def test_without_numbers_the_certificate_needs_an_enclosure(monkeypatch):
    _planted(monkeypatch, "1")
    assert _v(_dint("x**2", 0, 1), "1") == "INCORRECT"
    assert _v(_dint("x**2", 0, 1), "1/3") != "INCORRECT"
    _planted(monkeypatch, "1/3")
    assert _v(_dint("x**2", 0, 1), "1/3") == "CORRECT"


def test_a_ladder_whose_values_settle_confirms_the_certificate():
    # the error estimates misjudge an interior singularity and the ladder fails its own test, but its values settle
    from mathverify.certify.calculus import _stable_ladder_holds
    lad = [{"dps": 50, "value": "4.4999999999999999999999999999999999999091245780504", "err": "1.1e-60"},
           {"dps": 80, "value": "4.4999999999999999999999999999999999999999999999999999999964569206801977790531049",
            "err": "1.1e-104"}]
    assert _stable_ladder_holds(lad, (mp.mpf("4.5"), mp.mpf("4.5"))) is True
    assert _stable_ladder_holds(lad, (mp.mpf("4.5000000001"), mp.mpf("4.5000000001"))) is False
    diverging = [{"dps": 30, "value": "123.81", "err": "1e-30"}, {"dps": 50, "value": "193.01", "err": "1e-30"}]
    assert _stable_ladder_holds(diverging, (mp.mpf("193.01"), mp.mpf("193.01"))) is False
    assert _v(_dint("1/cbrt(x)", -1, 8), "9/2") == "CORRECT"
    assert _v(_dint("1/cbrt(x)", -1, 8), "5") == "INCORRECT"


def test_without_numbers_and_without_an_enclosure_nothing_is_accepted(monkeypatch):
    _planted(monkeypatch, "2")
    assert _v(_dint("asinh(x)", 0, 1), "2") == "UNKNOWN"      # asinh has no interval extension: no enclosure
    _planted(monkeypatch, "0")
    assert _v(_dint("1/x", -1, 1), "0") == "UNKNOWN"          # the enclosure is (-oo, oo): it says nothing


def test_an_infinite_range_has_no_numbers_and_the_certificate_decides():
    # the ladder does not run on an infinite range (d4c, 6 Oct 2026): the rule is for a ladder that ran
    assert _v(_dint("exp(-x)", 0, "oo"), "1") == "CORRECT"
    assert _v(_dint("1/x**2", 1, "oo"), "1/2") == "INCORRECT"
    assert _v(_dint("1/(1 + x**2)", "-oo", "oo"), "pi") == "CORRECT"


# G2YO-3 ---------------------------------------------------------------------------------------------------------
def test_the_cell_proof_cuts_at_the_poles_of_an_argument():
    from mathverify.equiv.random_point import _breakpoints
    g = sp.Max(x, x + 1 / (x - sp.Rational(1, 3)) - 10 ** 6)
    assert sp.Rational(1, 3) in _breakpoints([g, x], x, sp.S.Reals, poles=True)
    assert _v(_ir("simplify_expression", {"expr": "Max(x, x + 1/(x - 1/3) - 10**6)"}, shape="expression"), "x",
              kind="expression") != "CORRECT"
    assert _v(_ir("simplify_expression", {"expr": "Piecewise((x**2, 1/(x - 1/3) > 10**6), (x, 1/(x - 1/3) <= 10**6))"},
                  shape="expression"), "x", kind="expression") != "CORRECT"
    # control: a true identity whose argument has a pole
    assert _v(_ir("simplify_expression", {"expr": "sqrt(x**2 - 2*x + 1)"}, shape="expression"), "Abs(x - 1)",
              kind="expression") == "CORRECT"


# G2YO-4 ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("expr,tol,claim,verdict", [
    ("exp(pi*sqrt(163))", {"abs_tol": "1e-15"}, "262537412640768744", "INCORRECT"),
    ("sqrt(2)", {"abs_tol": "1e-25"}, "1.414213562373095048801", "INCORRECT"),
    ("sqrt(2)", {"rel_tol": "1e-25", "abs_tol": "1e-30"}, "1.414213562373095048801", "INCORRECT"),
    ("10**40*pi", {"abs_tol": "1/2"}, "31415926535897932384626433832795128841971", "INCORRECT"),
    ("10**40*pi", {"abs_tol": "1/2"}, "31415926535897932384626433832795028841972", "CORRECT"),
    ("sqrt(2)", {"abs_tol": "1e-25"}, "1.41421356237309504880168872", "CORRECT"),
    ("pi", {"abs_tol": "0.005"}, "3.14", "CORRECT"),
    ("pi", {"abs_tol": "0.005"}, "3.15", "INCORRECT"),
    ("pi", {"rel_tol": "1e-6", "abs_tol": "0.01"}, "3.14", "CORRECT"),     # one tolerance holding is enough
])
def test_a_declared_absolute_tolerance_is_decided_exactly(expr, tol, claim, verdict):
    assert _v(_ev(expr, (), **tol), claim) == verdict


def test_within_abs_tol():
    from mathverify.equiv.numeric import within_abs_tol, within_tolerance
    assert within_abs_tol(sp.Rational(314, 100), sp.pi, sp.Rational(1, 200)) is True
    assert within_abs_tol(sp.Rational(315, 100), sp.pi, sp.Rational(1, 200)) is False
    assert within_abs_tol(sp.Integer(262537412640768744), sp.exp(sp.pi * sp.sqrt(163)), sp.Rational(1, 10 ** 15)) is False
    assert within_abs_tol(1 + sp.I, sp.Integer(1), sp.Rational(1, 2)) is False
    assert within_tolerance(sp.Rational(314, 100), sp.pi, sp.Rational(1, 10 ** 6), sp.Rational(1, 100)) is True
    assert within_tolerance(sp.Rational(3, 1), sp.pi, sp.Rational(1, 10 ** 6), sp.Rational(1, 100)) is False


@pytest.mark.parametrize("f,claim,verdict", [
    ("x**2", "0.333", "CORRECT"), ("x**2", "0.34", "INCORRECT"),
    ("sqrt(1 + x**3)", "1.1114", "CORRECT"), ("sqrt(1 + x**3)", "1.12", "INCORRECT"),
])
def test_a_definite_integral_reads_its_absolute_tolerance(f, claim, verdict):
    assert _v(_dint(f, 0, 1, abs_tol="1e-3"), claim) == verdict


def test_a_malformed_absolute_tolerance_of_an_integral():
    assert _v(_dint("x**2", 0, 1, abs_tol="-1"), "1/3") == "UNKNOWN"


# G2RK-1 ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("f,claim", [
    ("cbrt(x)", "3*x*cbrt(x)/4"), ("cbrt(x)", r"\frac{3}{4}x\sqrt[3]{x}"), ("cbrt(x)", "3*x*cbrt(x)/4 + C"),
    ("root(x, 3)", "3*x*root(x, 3)/4"), ("cbrt(x**2)", "3*x*cbrt(x**2)/5"), ("x*cbrt(x)", "3*x**2*cbrt(x)/7"),
    ("cbrt(x - 1)", "3*(x - 1)*cbrt(x - 1)/4"), ("cbrt(2*x + 1)", "3*(2*x + 1)*cbrt(2*x + 1)/8"),
    ("x**2*cbrt(x**3 + 1)", "(x**3 + 1)*cbrt(x**3 + 1)/4"), ("root(x, 5)", "5*x*root(x, 5)/6"),
])
def test_a_continuous_real_root_primitive_is_certified(f, claim):
    assert _v(_anti(f), claim) == "CORRECT"


def test_a_real_root_primitive_is_still_refuted_when_wrong_or_jumping():
    assert _v(_anti("cbrt(x)"), "x*cbrt(x)") == "INCORRECT"
    assert _v(_anti("cbrt(x)"), "3*x*cbrt(x)/4 + sign(x)") == "INCORRECT"
    # sign(x)·sign(x³) is 1 off 0 and 0 at 0: a removable jump the sides do not read; no certificate
    assert _v(_anti("x"), "x**2/2 + sign(x)*sign(x**3)") != "CORRECT"
    opts = {"A": "3*x*cbrt(x)/4", "B": "4*x*cbrt(x)/3", "C": "3*cbrt(x)/4", "D": "cbrt(x)**2/3", "E": "x*cbrt(x)"}
    q = _anti("cbrt(x)")
    q["options"] = opts
    assert _v(q, "3*x*cbrt(x)/4", option="A") == "CORRECT"


def test_a_real_root_primitive_of_a_principal_power_on_the_region():
    assert verify(_anti("x**(1/3)", (XP,)), _sol("3*x*cbrt(x)/4", kind="expression")).verdict == "CORRECT"


def test_the_jump_of_a_sign_in_a_primitive():
    from mathverify.certify.calculus import _sign_jump_at
    s = sp.sign(x)
    assert _sign_jump_at(3 * x * s * sp.Abs(x) ** sp.Rational(1, 3) / 4, s, x, 0) is False
    assert _sign_jump_at(x ** 2 / 2 + s, s, x, 0) is True
    # one side equal to the value, the other not: which side is which is not read, no verdict
    s2 = sp.sign(x ** 2)
    assert _sign_jump_at(x ** 2 / 2 + s2 ** 2 - s2, s2, x, 0) is None
    # another sign vanishing at the same point: the sides are not continuous
    assert _sign_jump_at(s * sp.sign(x ** 3) + x, s, x, 0) is None


# G2RK-7 ---------------------------------------------------------------------------------------------------------
def test_a_complex_quadrature_value_is_no_value():
    from mathverify.certify.calculus import definite_integral_numeric
    v, ev = definite_integral_numeric(sp.sqrt(sp.cos(x)) * sp.sin(x), x, 0, sp.pi / 2)
    assert v is None and ev.get("error") == "nonreal_or_unreadable_value"


@pytest.mark.parametrize("f,a,b,true,wrong", [
    ("sqrt(cos(x))*sin(x)", 0, "pi/2", "2/3", "1/2"),
    ("cos(x)**(3/2)*sin(x)", 0, "pi/2", "2/5", "1/2"),
    ("sqrt(sin(x))*cos(x)", "pi/2", "pi", "-2/3", "-1/2"),
    ("sqrt(log(2) - x)", 0, "log(2)", "2*log(2)**(3/2)/3", "1/2"),
])
def test_a_root_vanishing_at_an_irrational_end(f, a, b, true, wrong):
    r = verify(_dint(f, a, b), _sol(true))
    assert r.verdict == "CORRECT" and _no_exception(r)
    assert _v(_dint(f, a, b), wrong) == "INCORRECT"


def test_an_even_root_at_an_end_is_read_on_the_range_only():
    from mathverify.certify.calculus import rigorous_integral
    f = sp.sqrt(sp.cos(x)) * sp.sin(x)
    lo, hi = rigorous_integral(f, x, 0, sp.pi / 2, inside=(mp.mpf("0.66"), mp.mpf("0.67")), defined=True)
    assert mp.mpf("0.66") <= lo <= sp.Rational(2, 3) <= hi <= mp.mpf("0.67")
    # without the caller's proof that the integrand is defined on the range: no reading past the end
    enc = rigorous_integral(f, x, 0, sp.pi / 2, inside=(mp.mpf("0.66"), mp.mpf("0.67")))
    assert enc is None or not (mp.isfinite(enc[0]) and mp.isfinite(enc[1]))


def test_an_odd_root_is_never_read_past_zero():
    from mathverify.certify.enclosure import Unsupported, _EVEN_ROOTS, iv_eval
    _EVEN_ROOTS.on = True
    try:
        mp.iv.dps = 30
        with pytest.raises(Unsupported):
            iv_eval(x ** sp.Rational(1, 3), {x: mp.iv.mpf([-1, 1])})
        assert iv_eval(sp.sqrt(x), {x: mp.iv.mpf([-1, 4])}).b == 2
    finally:
        _EVEN_ROOTS.on = False
    with pytest.raises(Unsupported):
        iv_eval(sp.sqrt(x), {x: mp.iv.mpf([-1, 4])})


def test_the_edge_reading_stays_in_the_edge():
    from mathverify.certify.enclosure import _EVEN_ROOTS, rigorous_enclosure
    out = rigorous_enclosure(sp.sqrt(sp.cos(x)) * sp.sin(x), x, 0, sp.pi / 2, None, None, 50, 60.0, True)
    assert out is not None and _EVEN_ROOTS.on is False


# G2RK-10 --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("f,claim,verdict", [
    ("cbrt(x**2)", "3*x**(5/3)/5", "CORRECT"), ("cbrt(x)", "3*x**(4/3)/4", "CORRECT"),
    ("1/cbrt(x)", "3*x**(2/3)/2", "CORRECT"), ("cbrt(x)", "x**(4/3)", "INCORRECT"),
])
def test_a_convention_of_the_primitive_on_the_region(f, claim, verdict):
    r = verify(_anti(f, (XP,)), _sol(claim))
    assert r.verdict == verdict and _no_exception(r)


def test_a_convention_condition_of_the_primitive_is_read_on_the_region():
    from mathverify.certify.calculus import antiderivative_domain_check
    F = 3 * x ** sp.Rational(4, 3) / 4
    f = sp.sign(x) * sp.Abs(x) ** sp.Rational(1, 3)
    ok, ev = antiderivative_domain_check(F, f, x, sp.S.Reals)
    assert ok is None and "Contains" in ev["reason"]
    assert antiderivative_domain_check(F, f, x, sp.Interval.open(0, sp.oo))[0] is True


def test_a_convention_of_the_primitive_that_can_fail_is_undecided():
    # on ℝ, 3x^(4/3)/4 is a primitive of ∛x under the real root and complex at x < 0 under the principal value: the two
    # readings differ, the reasoned UNKNOWN of the decision (neither CORRECT nor INCORRECT)
    r = verify(_anti("cbrt(x)"), _sol("3*x**(4/3)/4"))
    assert r.verdict == "UNKNOWN" and _no_exception(r)


# G2RK-2 ---------------------------------------------------------------------------------------------------------
PHI = "exp(-x**2/2)/sqrt(2*pi)"


@pytest.mark.parametrize("q,claim,verdict", [
    (_dint(PHI, 0, 1, rel_tol="1e-3"), "0.3413", "CORRECT"),
    (_dint(PHI, -2, 2, rel_tol="1e-3"), "0.9545", "CORRECT"),
    (_dint("sin(x**2)", 0, 1, rel_tol="1e-3"), "0.3103", "CORRECT"),
    (_dint("cos(x**2)", 0, 1, rel_tol="1e-3"), "0.9045", "CORRECT"),
    (_dint(PHI, 0, 1, rel_tol="1e-3"), "0.35", "INCORRECT"),
    (_dint("sin(x**2)", 0, 1, rel_tol="1e-3"), "0.32", "INCORRECT"),
    (_ev(f"Integral({PHI}, (x, 0, 1))", rel_tol="1e-3"), "0.3413", "CORRECT"),
    (_ev("Integral(exp(-x**2), (x, 0, sqrt(2)))", rel_tol="1e-3"), "0.8459", "CORRECT"),
    (_ev("Integral(exp(-x**2), (x, 0, sqrt(2)))", rel_tol="1e-3"), "0.86", "INCORRECT"),
    (_ev("Integral(sin(x**2), (x, 0, 1))", rel_tol="1e-3"), "0.3103", "CORRECT"),
    (_ev("Integral(sin(x)/x, (x, 0, 2*pi))", rel_tol="1e-3"), "1.4182", "CORRECT"),
    (_ev("Integral(sin(x)/x, (x, 0, 2*pi))", rel_tol="1e-3"), "1.5", "INCORRECT"),
])
def test_a_tolerance_against_a_special_function_value(q, claim, verdict):
    assert _v(q, claim) == verdict


def test_interval_extensions_of_erf_si_and_the_fresnel_integrals():
    from mathverify.certify.enclosure import constant_interval, iv_eval
    with mp.workdps(60):
        vals = ((sp.erf(sp.sqrt(2)), mp.erf(mp.sqrt(2))), (sp.erfc(sp.Rational(1, 3)), mp.erfc(mp.mpf(1) / 3)),
                (sp.Si(2 * sp.pi), mp.si(2 * mp.pi)), (sp.fresnels(1), mp.fresnels(1)), (sp.fresnelc(1), mp.fresnelc(1)))
    for e, v in vals:
        lo, hi = constant_interval(e)
        assert lo <= v <= hi and hi - lo < mp.mpf(10) ** -25
    mp.iv.dps = 30
    cell = iv_eval(sp.Si(x), {x: mp.iv.mpf([0, 1])})     # Si on a cell holds Si of both ends
    assert cell.a <= 0 and cell.b >= mp.si(1)
    cell = iv_eval(sp.fresnels(x), {x: mp.iv.mpf([0, 2])})
    assert cell.a <= 0 and cell.b >= mp.fresnels(1)


def test_an_undecided_distance_falls_back_on_the_integrals_enclosure():
    # Ci has no interval extension, and strict evalf reads it at rational arguments only: the certificate's value
    # Ci(√2) - Ci(1) has no certified distance to the claim; the integrand's own enclosure decides the tolerance
    from mathverify.equiv.numeric import within_rel_tol
    true = mp.ci(mp.sqrt(2)) - mp.ci(1)
    good, bad = mp.nstr(true, 6), mp.nstr(true * mp.mpf("1.01"), 6)
    assert within_rel_tol(sp.Rational(good), sp.Ci(sp.sqrt(2)) - sp.Ci(1), sp.Rational(1, 1000)) is None
    assert _v(_dint("cos(x)/x", 1, "sqrt(2)", rel_tol="1e-3"), good) == "CORRECT"
    assert _v(_dint("cos(x)/x", 1, "sqrt(2)", rel_tol="1e-3"), bad) == "INCORRECT"


# G2RK-3 / G2RK-4 ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("q,claim", [
    (_der("x**x", (XP,)), "x**x*(log(x) + 1)"),
    (_der("x**pi", (XP,)), "pi*x**(pi - 1)"),
    (_der("x**log(x)", (XP,)), "2*log(x)*x**log(x)/x"),
    (_der("(1 + 1/x)**x", (XP,)), "(1 + 1/x)**x*(log(1 + 1/x) - 1/(x + 1))"),
    (_anti("x**pi", (XP,)), "x**(pi + 1)/(pi + 1)"),
    (_anti("x**x*(log(x) + 1)", (XP,)), "x**x"),
    (_anti("x**(1/3)", (XP,)), "3*x**(4/3)/4"),
    (_der("x**(2/3)", (XP,)), "2/(3*x**(1/3))"),
])
def test_the_convention_gate_reads_the_declared_region(q, claim):
    assert _v(q, claim) == "CORRECT"


def test_no_exact_substitution_writes_out_a_huge_rational_power():
    from mathverify.equiv.random_point import _definite_nonzero_difference, _exact_counterexample, _heavy_power_at
    pt = {x: sp.Rational(7579840, 1000039)}
    assert _heavy_power_at(x ** x, pt) is True and _heavy_power_at(x ** 2 + 2 ** x, pt) is False
    assert _heavy_power_at(x ** x, {x: sp.Rational(3, 2)}) is False
    assert _exact_counterexample(x ** x * sp.log(x), x ** x * (sp.log(x) + 1), [x], pt) is None
    assert _definite_nonzero_difference(-x ** x, [x], [pt], x ** x * sp.log(x), x ** x * (sp.log(x) + 1)) == (None, 1)
    # the wrong derivative is refuted at a small point all the same, in seconds (it held a verify for minutes)
    assert _v(_der("x**x", ({"name": "x", "domain": "positive_real"},)), "x**x*log(x)", kind="expression") == "INCORRECT"


def test_the_convention_gate_on_the_declared_region_still_refutes():
    assert _v(_der("x**x", (XP,)), "x**x*log(x)") == "INCORRECT"
    assert _v(_anti("x**pi", (XP,)), "x**(pi + 1)") == "INCORRECT"
    assert _v(_anti("x**(1/3)"), "3*x**(4/3)/4") != "CORRECT"         # on ℝ the convention at x < 0 stays


def test_declared_regions():
    from mathverify.certify.base import Ctx
    from mathverify.certify.calculus import _declared_regions
    from mathverify.intake.structured import load_problem_ir
    from mathverify.normalize.parse import build_namespace
    for q, want in ((_der("x**x", (XP,)), [sp.Interval.open(0, sp.oo)]), (_der("x**x"), [])):
        obj = load_problem_ir(q)
        ctx = Ctx(obj, build_namespace(obj))
        assert _declared_regions(ctx, ctx.sym("x")) == want


# G2RK-5 ---------------------------------------------------------------------------------------------------------
PW = "Piecewise((x**2, x < 1), (2*x - 1, x >= 1))"


def test_a_piecewise_integrand_is_cut_at_its_conditions():
    assert _v(_dint(PW, 0, 2), "7/3") == "CORRECT"
    assert _v(_dint(PW, 0, 2), "3") == "INCORRECT"
    assert _v(_dint("Piecewise((1, x < 1), (x + 1/2, x >= 1))", 0, 2), "3") == "CORRECT"
    assert _v(_dint("Piecewise((1, x < 1), (x + 1/2, x >= 1))", 0, 2), "5/2") == "INCORRECT"
    # a piece where no branch holds: no value
    assert _v(_dint("Piecewise((1, x < 1), (1, x >= 2))", 0, 3), "2") != "CORRECT"


# G2RK-9 ---------------------------------------------------------------------------------------------------------
def test_x_to_the_x_in_the_fundamental_theorem():
    from mathverify.certify.calculus import _exact_conditions
    assert _exact_conditions(x ** x, x) == [x > 0]
    assert _v(_dint("x**x*(1 + log(x))", 1, 2), "3") == "CORRECT"
    assert _v(_dint("x**x*(1 + log(x))", 1, "E"), "exp(E) - 1") == "CORRECT"
    assert _v(_dint("x**x*(1 + log(x))", 1, 2), "4") == "INCORRECT"


# G2YO-6 ---------------------------------------------------------------------------------------------------------
NPR = 6 * 1000003 * 999983 * 1000033 * 999979 * 1000037 * 999961 * 1000039 * 999959
XPOS = {"name": "x", "domain": "positive_real"}


def test_a_point_whose_difference_has_no_sign_is_no_agreement():
    from mathverify.equiv.random_point import point_signs
    tiny = sp.Integer(10) ** -300 * sp.sin(NPR * sp.pi * x)
    pts = [{x: sp.sqrt(2) / 2}, {x: sp.pi / 7}]
    # the claim's (x - 1)(x + 1) cancels against x² no closer than 10^-234: read expanded, the 10^-300 term has a sign
    assert point_signs(x ** 2 + tiny - ((x - 1) * (x + 1) + 1), [x], pts) == ([0, 1], [])
    # a true identity's difference is proved 0 at each point
    assert point_signs((x - 1) * (x + 1) + 1 - x ** 2, [x], pts) == ([], [])
    # a point too large to write out is not read
    assert point_signs(x ** x - x ** x, [x], [{x: sp.Rational(7579840, 1000039)}]) == ([], [])
    assert point_signs(x ** x * sp.log(x) - x ** x * (sp.log(x) + 1), [x], [{x: sp.Rational(7579840, 1000039)}]) == ([], [0])


@pytest.mark.parametrize("q,claim", [
    (_ir("simplify_expression", {"expr": f"x**2 + 10**(-300)*sin({NPR}*pi*x)"}, (XPOS,), shape="expression"),
     "(x - 1)*(x + 1) + 1"),
    (_ir("simplify_expression", {"expr": f"2*x + 10**(-300)*sin({NPR}*pi*x)"}, (XPOS,), shape="expression"),
     "(x + 1)**2 - x**2 - 1"),
    (_ir("derivative", {"f": f"x**3/3 - 10**(-300)*cos({NPR}*pi*x)/({NPR}*pi)", "var": "x"}, (XPOS,),
         shape="expression"), "(x - 1)*(x + 1) + 1"),
])
def test_a_difference_below_every_interval_is_not_certified(q, claim):
    assert _v(q, claim, kind="expression") != "CORRECT"


def test_a_signed_point_not_confirmed_is_no_agreement(monkeypatch):
    # a difference the interval signs at a point, which the exact values cannot confirm there: no witness, and no
    # agreement either (it was skipped, as if the sides agreed)
    from mathverify.equiv import random_point
    monkeypatch.setattr(random_point, "_exact_counterexample", lambda *a, **k: None)
    d = x - x + sp.Integer(1) / 10 ** 300
    assert random_point._nonzero_elsewhere(d, [x], [{x: sp.sqrt(2) / 2}], x, x, [0]) == (None, True)
    assert random_point._nonzero_elsewhere(x - x, [x], [{x: sp.sqrt(2) / 2}], x, x, [0]) == (None, False)


# Second round (independent audit of the branch, 21 Oct 2026) -------------------------------------------------------
# SI-YO-3: the settled ladder reads the rungs' own error estimates
def test_a_ladder_that_fails_settles_nothing():
    from mathverify.certify.calculus import _stable_ladder_holds
    # mpmath's quad returns 0.0 with an error estimate of 2.0 for ∫_{-1}^{1} dx/x at every precision: a failure
    failed = [{"dps": 30, "value": "0.0", "err": "2.0"}, {"dps": 50, "value": "0.0", "err": "0.2"},
              {"dps": 80, "value": "0.0", "err": "2.0"}]
    assert _stable_ladder_holds(failed, (mp.mpf(0), mp.mpf(0))) is False
    small = [dict(r, err="1.1e-60") for r in failed]
    assert _stable_ladder_holds(small, (mp.mpf(0), mp.mpf(0))) is True
    # one rung's estimate past 10^-10 of max(1, |v|) is enough to refuse; a missing estimate refuses
    assert _stable_ladder_holds(small[:2] + [dict(small[2], err="2e-10")], (mp.mpf(0), mp.mpf(0))) is False
    assert _stable_ladder_holds(small[:1] + [dict(small[1], err="2e-10")] + small[2:], (mp.mpf(0), mp.mpf(0))) is False
    assert _stable_ladder_holds([{"dps": 50, "value": "0.0"}, {"dps": 80, "value": "0.0"}], (mp.mpf(0), mp.mpf(0))) \
        is False


@pytest.mark.parametrize("f,a,b", [
    ("1/x", -1, 1), ("1/x**3", -1, 1), ("x/(x**2 - 1)", -2, 2), ("sign(x)/Abs(x)**(3/2)", -1, 1),
])
def test_a_planted_zero_of_a_principal_value_is_not_taken(monkeypatch, f, a, b):
    # the improper integral diverges (only its principal value is 0): a wrong certificate 0 meets the real ladder
    _planted(monkeypatch, "0", numbers=True)
    assert _v(_dint(f, a, b), "0") != "CORRECT"


# SI-YO-2: a half-infinite enclosure says something only next to a close rung of the ladder
def test_the_last_rung_near_the_certificate():
    from mathverify.certify.calculus import _near_last_rung
    six = [{"dps": 30, "value": "5.99999999997790565034", "err": "2.0e-12"},
           {"dps": 50, "value": "5.99999999999999999520", "err": "2.0e-19"},
           {"dps": 80, "value": "5.9999999999999999999999999995400000000000000000000000000000000000000000000000",
            "err": "2.0e-28"}]
    assert _near_last_rung(six, (mp.mpf(6), mp.mpf(6))) is True
    with mp.workdps(60):
        off = mp.mpf("6.0000000000000000000000001")               # 1e-25 from 6: five times the margin, 100·err
    assert _near_last_rung(six, (off, off)) is False
    # the last rung's estimate: at most 10^-8 of max(1, |v|)
    assert _near_last_rung([{"dps": 80, "value": "20.0", "err": "1.9e-7"}], (mp.mpf(20), mp.mpf(20))) is True
    assert _near_last_rung([{"dps": 80, "value": "20.0", "err": "2.1e-7"}], (mp.mpf(20), mp.mpf(20))) is False
    diverging = [{"dps": 30, "value": "78.97", "err": "1.0"}, {"dps": 50, "value": "125.0", "err": "0.1"},
                 {"dps": 80, "value": "194.2", "err": "1.0"}]
    assert _near_last_rung(diverging, (mp.mpf("194.2"), mp.mpf("194.2"))) is False
    assert _near_last_rung([], (mp.mpf(6), mp.mpf(6))) is False


@pytest.mark.parametrize("f,a,b,plant", [
    ("1/x", 0, 1, "10**6"), ("1/(x*Abs(log(x)))", 0, "1/2", "10"), ("-1/x", 0, 1, "-10**6"),
    ("1/(1 - x)", "1/2", 1, "100"),
])
def test_a_planted_finite_value_of_a_divergent_integral_is_not_taken(monkeypatch, f, a, b, plant):
    # the enclosure is (L, oo): every number past L meets it
    _planted(monkeypatch, plant, numbers=True)
    assert _v(_dint(f, a, b), plant) != "CORRECT"


@pytest.mark.parametrize("f,a,b,claim", [
    # interior singularities: half-infinite enclosures, ladders whose error estimates fall short (2.3 and 37 times)
    ("1/cbrt((x - 1)**2)", 0, 2, "6"), ("Abs(x - 1)**(-2/3)", 0, 2, "6"),
    ("Abs(x)**(-9/10)", -1, 2, "10*(2**(1/10) + 1)"), ("Abs(x - 1)**(-9/10)", 0, 2, "20"),
    # a power at an end: the weight rule bounds the end cell (no ladder converges to 100)
    ("x**(-99/100)", 0, 1, "100"), ("(1 - x)**(-19/20)", 0, 1, "20"), ("x**(-9/10)", 0, 1, "10"),
])
def test_a_strong_integrable_singularity_keeps_its_value(f, a, b, claim):
    assert _v(_dint(f, a, b), claim) == "CORRECT"


def test_a_power_at_an_end_is_a_weight():
    from mathverify.certify.enclosure import from_raw, rigorous_enclosure
    R = sp.Rational

    def enc(f, a, b):
        r = rigorous_enclosure(f, x, a, b, None, None, 600, 120.0)
        return None if r is None else tuple(from_raw(v) for v in r)
    lo, hi = enc(x ** R(-99, 100), 0, 1)
    assert lo <= 100 <= hi and hi - lo < mp.mpf("1e-6")
    lo, hi = enc(sp.Abs(x - 1) ** R(-99, 100), 0, 1)
    assert lo <= 100 <= hi and hi - lo < mp.mpf("1e-6")
    # u < 0 on the cell: no weight (the principal power is not real there, the real cube root has the other sign)
    assert enc(2 * x ** R(-1, 3), -1, 0) == (-mp.inf, mp.inf)
    assert enc(x ** R(-1, 2), -1, 0) == (-mp.inf, mp.inf)
    # a divergent power is no weight
    assert enc(1 / x, 0, 1)[1] == mp.inf


def test_a_wrong_value_of_a_power_at_an_end_is_refuted():
    assert _v(_dint("x**(-99/100)", 0, 1), "101") == "INCORRECT"
    assert _v(_dint("x**(-99/100)", 0, 1, rel_tol="0.001"), "100.05") == "CORRECT"


# SON-INT-RK-1: a complex claim within a declared tolerance
@pytest.mark.parametrize("expr,tol,claim,verdict", [
    ("exp(I*pi/3)", {"abs_tol": "0.001"}, "0.5 + 0.866*I", "CORRECT"),
    ("2*exp(I*pi/4)", {"abs_tol": "0.01"}, "1.41 + 1.41*I", "CORRECT"),
    ("exp(I)", {"abs_tol": "0.0001"}, "0.5403 + 0.8415*I", "CORRECT"),
    ("exp(I)", {"abs_tol": "0.0001", "rel_tol": "0.0001"}, "0.5403 + 0.8415*I", "CORRECT"),
    ("exp(I)", {"rel_tol": "0.0001"}, "0.5403 + 0.8415*I", "CORRECT"),
    ("exp(I*pi/3)", {"abs_tol": "0.001"}, "0.5 + 0.87*I", "INCORRECT"),        # |Im d| = 4.0e-3
    ("exp(I*pi/3)", {"abs_tol": "0.001"}, "0.502 + 0.866*I", "INCORRECT"),     # |Im d| < t < |d| = 2.0e-3
    ("exp(I)", {"rel_tol": "0.0001"}, "0.5403 + 0.8515*I", "INCORRECT"),
    ("sqrt(3) + I", {"abs_tol": "0.01"}, "1.73 + I", "CORRECT"),              # a real difference, as before
])
def test_a_complex_claim_within_a_declared_tolerance(expr, tol, claim, verdict):
    assert _v(_ev(expr, (), **tol), claim) == verdict


def test_complex_differences_against_a_tolerance():
    from mathverify.equiv.numeric import within_abs_tol, within_rel_tol
    c, v = sp.Rational(1, 2) + sp.Float("0.866") * sp.I, sp.exp(sp.I * sp.pi / 3)
    assert within_abs_tol(c, v, sp.Rational(1, 1000)) is True
    assert within_abs_tol(c, v, sp.Rational(1, 100000)) is False
    assert within_rel_tol(c, v, sp.Rational(1, 1000)) is True              # |v| = 1
    assert within_rel_tol(c, 2 * v, sp.Rational(1, 1000)) is False
    # a real value, a complex claim: |c - v|² = Re² + Im² against t²·v²
    assert within_rel_tol(2 + sp.I / 10 ** 4, sp.Integer(2), sp.Rational(1, 1000)) is True
    assert within_rel_tol(2 + sp.I / 10 ** 2, sp.Integer(2), sp.Rational(1, 1000)) is False
    assert within_rel_tol(sp.I, sp.Integer(0), sp.Rational(1, 1000)) is None  # no relative error against 0


# SON-INT-RK-2: the certificate's enclosure settles once a finite sum holding the value stops narrowing
def test_an_enclosure_that_stops_narrowing_settles():
    from mathverify.certify.calculus import _raw_pair
    from mathverify.certify.enclosure import from_raw, rigorous_enclosure
    half = _raw_pair(mp.mpf("0.5"), mp.mpf("0.5"))
    # the cells of cos² 1000πx are [0, 1]·h until they are shorter than its period: the sum stays [0, 1] and settles
    lo, hi = (from_raw(v) for v in rigorous_enclosure(sp.cos(1000 * sp.pi * x) ** 2, x, 0, 1, half, None, 4000, 120.0,
                                                      False, 8))
    assert lo <= mp.mpf("0.5") <= hi and hi - lo > mp.mpf("0.5")
    # a sum that keeps narrowing is not stopped
    lo, hi = (from_raw(v) for v in rigorous_enclosure(x ** 2 * sp.exp(x), x, 0, 1, None, None, 300, 120.0, False, 8))
    assert hi - lo < mp.mpf("1e-4")


def test_the_certificate_check_spends_little_on_a_fast_oscillation():
    from mathverify.certify.calculus import _certificate_check
    nev = {"converged": False, "ladder": [{"dps": 30, "value": "0.4886", "err": "1.0"}]}
    state, ev = _certificate_check(sp.cos(1000 * sp.pi * x) ** 2, x, 0, 1, sp.Rational(1, 2), None, nev, 8.0,
                                   defined=True)
    # a small budget and settling: the enclosure is still [0, 1] (4000 cells narrowed it to [0.4786, 0.5214] in 11 s)
    assert state == "agrees" and mp.mpf(ev["enclosure"][1]) - mp.mpf(ev["enclosure"][0]) > mp.mpf("0.5")


def test_a_settling_enclosure_still_refutes_a_close_wrong_certificate(monkeypatch):
    # e - 2 + 10^-4: the sum narrows past it in some 25 rounds, without settling
    _planted(monkeypatch, "E - 2 + 1/10000")
    assert _v(_dint("x**2*exp(x)", 0, 1), "E - 2 + 1/10000") == "INCORRECT"
    _planted(monkeypatch, "E - 2")
    assert _v(_dint("x**2*exp(x)", 0, 1), "E - 2") == "CORRECT"
