"""Fourth audit (1 Oct 2026), part d4c, round 3: the attack on round 2 (7 Oct 2026, d4/saldiri/d4c2).

Each case was measured wrong on 62a40e9:

* YO-1: an extremum below 40 digits (max of 1 + x/10^50 on [0, 1] certified 1 next to the true 1 + 10^-50): the
  direction of a difference is a certified sign, an undecided candidate or a non-empty superlevel set closes EVT.
* YO-2: SymPy's value and an agreeing quadrature accepted a wrong approximate claim (a narrow peak both miss); a
  definite integral's value is now the certificate's or none, approximate claims are decided by an enclosure.
* YO-3: random points on a 6-decimal grid hid sin(3·10^6·πx); samples are off the grid, SymPy's `equals` False is
  not overruled on the real line, and a sign must stand at a higher precision too.
* YO-4, RK-E, RK-F: one reading of a declared tolerance, |c - v|/|v| <= t; t outside (0, 1) is malformed.
* YO-5: the enclosure rounds outward. RK-A: erf on infinite ranges. RK-B: end singularities. RK-C: a budget of cells.
"""
import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}


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
    contradicts: something is wrong, and the certificate decides nothing. Since the last attack (G2YO-1, G2YO-2, 16 Oct
    2026) a rigorous enclosure that misses the certificate's value drops it, and the claim meets the enclosure alone:
    sin 1 + 1 lies outside it and is refuted (it was UNKNOWN); the true sin 1 is not."""
    from mathverify.certify import calculus
    monkeypatch.setattr(calculus, "certified_integral_value", lambda *a, **k: (sp.sin(1) + 1, {}))
    assert _run(_dint("cos(x)", 0, 1), "sin(1) + 1").verdict == "INCORRECT"
    assert _run(_dtol("cos(x)", 0, 1, "1e-3"), "1.8414").verdict == "INCORRECT"
    assert _run(_dint("cos(x)", 0, 1), "sin(1)").verdict != "INCORRECT"


def test_a_proof_stands_against_a_quadrature_the_enclosure_shows_wrong():
    """The erf primitive proves ∫_0^1 (x² + e^(-10^8 (x - 1/3)²)) dx = 1/3 + √π(erf(20000/3) + erf(10000/3))/20000;
    tanh-sinh missed the peak and gave 1/3. The rigorous enclosure excludes 1/3, so the proof stands and the
    claim 1/3 is refuted (it was UNKNOWN: "symbolic-numeric disagreement")."""
    assert _run(_dint("x**2 + exp(-10**8*(x - 1/3)**2)", 0, 1), "1/3").verdict == "INCORRECT"


def test_a_closed_integral_takes_no_value_without_a_certificate(monkeypatch):
    """With the certificate taken away, SymPy's value of a closed integral (here even the right 1/3) is no
    value: evaluate, a step and checked_forms decide nothing."""
    from mathverify.certify import calculus
    from mathverify.equiv.forms import UnverifiedForm, checked_forms
    monkeypatch.setattr(calculus, "certified_integral_value", lambda *a, **k: (None, {}))
    I = "Integral(x**2, (x, 0, 1))"
    assert _run(_task("evaluate", {"expr": I}, [X]), "1/3").verdict == "UNKNOWN"
    x = sp.Symbol("x", real=True)
    with pytest.raises(UnverifiedForm):
        checked_forms(sp.Integral(x**2, (x, 0, 1)))


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


def test_one_false_from_sympys_equals_is_no_fact():
    """SymPy's `equals` draws random points: it said False at some seeds for the true identity
    atan(x) - atan(x/2) = atan(x/(x² + 2)), and the identity went UNKNOWN or CORRECT from run to run."""
    from mathverify.equiv import _equals_false_stands
    x = sp.Symbol("x", real=True)
    assert _equals_false_stands(sp.atan(x) - sp.atan(x / 2), sp.atan(x / (x**2 + 2))) is False
    assert _equals_false_stands(x**2 + sp.sin(3000000 * sp.pi * x), x**2) is True


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
    assert _removable(sp.sin(x) / x, x, 0) == (sp.sin(x), sp.cos(x), 1)
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
