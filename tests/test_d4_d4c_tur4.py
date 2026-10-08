"""Part d4c of the fourth audit, round 4 (8 Oct 2026): the attack on round 3 (denetim/2026-10-01/d4/saldiri/d4c3).

YO-A = R-YO-1 = R-RET-1: the enclosure's Taylor bounds (midpoint and end rule) only where the integrand is proved
analytic on the cell, read as written; YO-B: the exact difference at every sample point, the equals conflict on
the antiderivative path; YO-C: sample points inside the domain; KK-1: real primitives for the fundamental theorem;
SG-1: non-numbers, complex and infinite claims on the tolerance path; KK-2: reversed ranges; BİRLEŞİK-1: the
odd-root convention of a fractional power met by its base >= 0.
"""
from __future__ import annotations

import random

import mpmath as mp
import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
X_POS = {"name": "x", "domain": "real", "constraints": ["x > 0"]}
X_N3 = {"name": "x", "domain": "real", "constraints": ["x > 3", "x < 3 + 1/10**7"]}
X_N0 = {"name": "x", "domain": "real", "constraints": ["x > 0", "x < 1/10**7"]}
T_ = {"name": "t", "domain": "real"}
NPR = 1000003 * 999983 * 1000033 * 999979 * 1000037 * 999961 * 1000039 * 999959
SN = f"sin({NPR}*pi*x)/10**40"
CN = f"cos({NPR}*pi*x)/(10**40*{NPR}*pi)"
x = sp.Symbol("x", real=True)


def _task(kind, params, vars_, givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _dint(f, a, b, tol=None):
    p = {"integrand": f, "var": "x", "a": str(a), "b": str(b)}
    if tol is not None:
        p["rel_tol"] = tol
    return _task("definite_integral", p, [X])


def _v(ir, payload, steps=(), kind="value"):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""} for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _status(r):
    layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
    steps = layer.evidence.get("steps", []) if layer is not None else []
    return steps[-1].get("status") if steps else None


def _no_exception(r):
    return not any(isinstance(la.evidence, dict) and str(la.evidence.get("reason", "")).startswith("layer_exception")
                   for la in r.layers)


def _enc(f, a, b, outside=None, inside=None, cells=4000):
    from mathverify.certify.enclosure import _raw, from_raw, rigorous_enclosure
    o = None if outside is None else (_raw(mp.mpf(outside[0])), _raw(mp.mpf(outside[1])))
    i = None if inside is None else (_raw(mp.mpf(inside[0])), _raw(mp.mpf(inside[1])))
    r = rigorous_enclosure(sp.sympify(f, locals={"x": x}), x, a, b, o, i, cells, 120.0)
    return None if r is None else (from_raw(r[0]), from_raw(r[1]))


X1 = _task("evaluate", {"expr": "x + 1"}, [X], ["x = 1"])
AT = "atan(tan(x))"


# --- YO-A: no Taylor bound on a cell not proved analytic ---------------------------------------------------------
def test_analytic_evaluation_proves_or_refuses():
    from mathverify.certify.enclosure import NotAnalytic, iv_eval
    mp.iv.dps = 30
    box = lambda lo, hi: {x: mp.iv.mpf([lo, hi])}                          # noqa: E731
    for e, lo, hi in ((sp.atan(sp.tan(x)), 1, 2), (sp.log(x), 0, 1), (sp.sqrt(x), 0, 1), (1 / x, -1, 1),
                      (sp.asin(x), 0, 1), (sp.Abs(x), -1, 1), (sp.Max(x, 1), 0, 2), (sp.sec(x), 1, 2),
                      (sp.cot(x), -1, 1), (x ** x, 0, 1), (x ** sp.Rational(3, 2), 0, 1), (sp.sign(x), -1, 1)):
        with pytest.raises(NotAnalytic):
            iv_eval(e, box(lo, hi), analytic=True)
    for e, lo, hi in ((sp.atan(sp.tan(x)), 0, 1), (sp.log(x), 1, 2), (sp.sqrt(x), 1, 2), (1 / x, 1, 2),
                      (sp.asin(x), 0, 0.5), (sp.Abs(x), 1, 2), (sp.sec(x), 0, 1), (x ** x, 1, 2),
                      (sp.sign(x), 1, 2), (sp.exp(sp.sin(x)) * sp.cosh(x), -3, 3)):
        lo_, hi_ = (mp.make_mpf(v) for v in iv_eval(e, box(lo, hi), analytic=True)._mpi_)
        assert mp.isfinite(lo_) and mp.isfinite(hi_), e
    # read as written: the value alone (atan of an unbounded tan is bounded) proves nothing
    v = iv_eval(sp.atan(sp.tan(x)), box(1, 2))
    assert mp.isfinite(mp.make_mpf(v._mpi_[0])) and mp.isfinite(mp.make_mpf(v._mpi_[1]))


def test_a_cell_with_a_hidden_jump_has_no_taylor_bound():
    from mathverify.certify.enclosure import _cell
    mp.iv.dps = 30
    f = sp.atan(sp.tan(x))
    assert sp.diff(f, x, 2) == 0                       # SymPy's f'' hides the jump of -π at π/2
    c = _cell(f, sp.diff(f, x, 2), x, mp.mpf(1), mp.mpf(2))
    lo, hi = (mp.make_mpf(v) for v in c._mpi_)
    with mp.workdps(40):
        assert lo <= ((mp.pi - 2) ** 2 - 1) / 2 <= hi and hi - lo > 1
    c = _cell(f, sp.diff(f, x, 2), x, mp.mpf(0), mp.mpf(1))      # analytic there: Taylor, f'' = 0, exact
    lo, hi = (mp.make_mpf(v) for v in c._mpi_)
    assert lo <= mp.mpf(1) / 2 <= hi and hi - lo < 1e-25


@pytest.mark.parametrize("f, a, b, true", [
    (AT, 0, 2, lambda: (2 - mp.pi) ** 2 / 2),
    (AT, 1, 2, lambda: ((mp.pi - 2) ** 2 - 1) / 2),
    (AT, 0, 3, lambda: (3 - mp.pi) ** 2 / 2),
    ("atan(cot(x))", 2, 4, lambda: 5 * mp.pi - 6 - mp.pi ** 2),
    (f"sin(x)/x + {AT}", 0, 2, lambda: mp.mpf("2.25702987016778768106867888158")),
    (f"x*{AT}", 0, 2, lambda: mp.mpf("0.259265944524557711675919283496")),
    # the end rule at 0: P = atan(tan x) - x, SymPy's P' = 0, and f is -π/x past π/2: the rule only where P is analytic
    (f"({AT} - x)/x", 0, 2, lambda: -mp.pi * mp.log(4 / mp.pi)),
])
def test_the_enclosure_holds_the_true_value_across_the_jump(f, a, b, true):
    lo, hi = _enc(f, a, b)
    with mp.workdps(40):
        assert lo <= true() <= hi and hi - lo < 1e-6, (f, lo, hi)


def test_the_end_rule_needs_p_analytic_up_to_the_cell():
    from mathverify.certify.enclosure import _removable
    P, pk, k = _removable(sp.sin(x) / x + sp.atan(sp.tan(x)), x, 0)
    assert P == sp.sin(x) + x * sp.atan(sp.tan(x)) and k == 1
    # past π/2 P is not analytic from 0 to the cell: the rule gives nothing there, and the enclosure holds the value
    lo, hi = _enc(f"sin(x)/x + {AT}", 0, 2, outside=("2.2555098", "2.2555099"))
    assert lo <= mp.mpf("2.25702987016778768") <= hi


def test_disjoint_enclosures_meet_in_their_hull():
    from mathverify.certify.enclosure import _ends, _meet
    mp.iv.dps = 30
    lo, hi = _ends(_meet(mp.iv.mpf([1, 2]), mp.iv.mpf([3, 4])))
    assert (lo, hi) == (1, 4)
    lo, hi = _ends(_meet(mp.iv.mpf([1, 3]), mp.iv.mpf([2, 4])))
    assert (lo, hi) == (2, 3)


def test_bounded_functions_of_an_unbounded_argument():
    from mathverify.certify.enclosure import Unsupported, iv_eval
    mp.iv.dps = 30
    box = {x: mp.iv.mpf([-1, 1])}
    with mp.workdps(60):
        lo, hi = (mp.make_mpf(v) for v in iv_eval(sp.atan(1 / x), box)._mpi_)
        assert lo <= -mp.pi / 2 and hi >= mp.pi / 2 and hi - lo < mp.pi + 1e-20
        lo, hi = (mp.make_mpf(v) for v in iv_eval(sp.tanh(1 / x), box)._mpi_)
        assert lo <= -1 and hi >= 1 and hi - lo < 2 + mp.mpf("1e-20")
    with pytest.raises(Unsupported):
        iv_eval(sp.sinh(1 / x), box)
    lo, hi = _enc("tanh(1/(x - 1/3))", 0, 1)            # bounded across its jump at 1/3
    with mp.workdps(30):
        true = mp.quad(lambda t: mp.tanh(1 / (t - mp.mpf(1) / 3)), [0, mp.mpf(1) / 3, 1])
        assert lo <= true <= hi and hi - lo < 1e-3


def test_unbounded_cells_are_split_first_and_stop(monkeypatch):
    import mathverify.certify.enclosure as enc
    calls = []
    real = enc._cell

    def counted(*a, **k):
        calls.append(a[3:])
        return real(*a, **k)
    monkeypatch.setattr(enc, "_cell", counted)
    for f in ("1/(x - 1/3)", "1/x"):
        calls.clear()
        lo, hi = _enc(f, 0, 1)
        assert not (mp.isfinite(lo) and mp.isfinite(hi))
        assert len(calls) < 600, f                       # a pole: given up near the precision limit, not at 4000 cells
    calls.clear()
    lo, hi = _enc("1/(x**2 - x + 1)", 0, 1)              # unbounded at first only by the dependency of x
    with mp.workdps(40):
        true = 2 * mp.pi / (3 * mp.sqrt(3))
        assert lo <= true <= hi and hi - lo < 1e-9


@pytest.mark.parametrize("f, a, b, claim, tol, bad", [
    (AT, 0, 2, "2", "1e-3", "CORRECT"),
    (AT, 0, 2, "0.6516", "1e-3", "INCORRECT"),
    (AT, 1, 2, "1.5", "1e-2", "CORRECT"),
    (AT, 1, 2, "((pi - 2)**2 - 1)/2", None, "INCORRECT"),
    (f"{AT} + exp(cos(x))", 1, 2, "1.2644", "1e-3", "INCORRECT"),
    ("atan(cot(x))", 2, 4, "pi - 6", "1e-2", "CORRECT"),
    ("atan(cot(x))", 2, 4, "5*pi - 6 - pi**2", "1e-2", "INCORRECT"),
    (f"x**2 + {AT}", 0, 2, "14/3", "1e-2", "CORRECT"),
])
def test_naive_never_accepted_true_never_refuted(f, a, b, claim, tol, bad):
    assert _v(_dint(f, a, b, tol), claim).verdict != bad


def test_naive_refuted_true_accepted_through_the_enclosure():
    assert _v(_dint(AT, 0, 2, "1e-3"), "2").verdict == "INCORRECT"
    assert _v(_dint(AT, 0, 2, "1e-3"), "0.6516").verdict == "CORRECT"


def test_a_true_step_across_the_jump_is_not_refuted():
    r = _v(X1, "2", [("compute", "Integral(atan(tan(x)), (x, 0, 2)) = (2 - pi)**2/2")])
    assert _status(r) != "refuted" and r.verdict != "INCORRECT"
    r = _v(X1, "2", [("compute", "Integral(atan(tan(x)), (x, 0, 2)) = 2")])
    assert _status(r) != "verified" and r.verdict != "CORRECT"


# --- KK-2: reversed ranges -----------------------------------------------------------------------------------------
def test_a_reversed_range_meets_its_windows():
    true = -mp.mpf("2.3415748417130531649")                   # ∫_1^0 e^(cos x)
    lo, hi = _enc("exp(cos(x))", 1, 0, inside=("-2.34158", "-2.34157"))
    assert mp.mpf("-2.34158") <= lo <= true <= hi <= mp.mpf("-2.34157")
    lo, hi = _enc("exp(cos(x))", 1, 0, outside=("-2.3416", "-2.3415"))
    assert lo <= true <= hi and hi - lo < mp.mpf("1e-4")
    lo, hi = _enc("exp(cos(x))", 1, 0, outside=("-2.351", "-2.349"))
    assert hi < mp.mpf("-2.351") or lo > mp.mpf("-2.349")


def test_reversed_range_verdicts():
    assert _v(_dint("1/(x - 2)", 1, 0, "1e-6"), "0.693147").verdict == "CORRECT"
    assert _v(_dint("exp(cos(x))", 1, 0, "1e-4"), "-2.3416").verdict == "CORRECT"
    assert _v(_dint("exp(cos(x))", 1, 0, "1e-4"), "-2.35").verdict == "INCORRECT"


# --- KK-1: real primitives ---------------------------------------------------------------------------------------
def test_real_primitive():
    from mathverify.certify.calculus import _real_primitive
    assert _real_primitive(sp.log(x - 2), x, 0, 1) == sp.log(2 - x)
    assert _real_primitive(sp.log(x), x, -2, -1) == sp.log(-x)
    assert _real_primitive(sp.log(x), x, 1, 2) == sp.log(x)
    assert _real_primitive(sp.log(x), x, -1, 1) == sp.log(x)             # changes sign: kept, and refused later
    assert _real_primitive(-sp.log(sp.sin(x) - 1) / 2 + sp.log(sp.sin(x) + 1) / 2, x, 0, sp.pi / 4) == \
        -sp.log(1 - sp.sin(x)) / 2 + sp.log(sp.sin(x) + 1) / 2
    assert _real_primitive(-sp.polylog(2, x * sp.exp_polar(sp.I * sp.pi)), x, 0, 1) == -sp.polylog(2, -x)
    assert _real_primitive(-sp.polylog(2, x * sp.exp_polar(2 * sp.I * sp.pi)), x, 0, 1) == -sp.polylog(2, x)
    assert _real_primitive(sp.polylog(2, x * sp.exp_polar(sp.I * sp.pi / 2)), x, 0, 1) is None


@pytest.mark.parametrize("f, a, b, claim, verdict", [
    ("1/x", -2, -1, "-log(2)", "CORRECT"),
    ("1/x", -2, -1, "log(2)", "INCORRECT"),
    ("1/(x - 2)", 0, 1, "-log(2)", "CORRECT"),
    ("1/cos(x)", 0, "pi/4", "log(1 + sqrt(2))", "CORRECT"),
    ("tan(x)", "2*pi/3", "3*pi/4", "-log(2)/2", "CORRECT"),
    ("log(1 + x)/x", 0, 1, "pi**2/12", "CORRECT"),
    ("log(1 + x)/x", 0, 1, "pi**2/6", "INCORRECT"),
    ("log(1 - x)/x", 0, 1, "-pi**2/6", "CORRECT"),
    ("log(x)/(1 - x)", 0, 1, "-pi**2/6", "CORRECT"),
])
def test_textbook_integrals_with_a_complex_sympy_primitive(f, a, b, claim, verdict):
    assert _v(_dint(f, a, b), claim).verdict == verdict


def test_principal_values_stay_uncertified():
    for f, a, b, c in (("1/x", -1, 1, "0"), ("1/(x - 1)", "1/2", 2, "log(2)"), ("1/(x - 2)", 1, 3, "0")):
        assert _v(_dint(f, a, b), c).verdict != "CORRECT", f


def test_the_real_primitive_on_the_evaluate_and_step_paths():
    assert _v(_task("evaluate", {"expr": "Integral(1/(x - 2), (x, 0, 1))"}, [X]), "-log(2)").verdict == "CORRECT"
    r = _v(X1, "2", [("eq", "Integral(1/(x - 2), (x, 0, 1)) = -log(2)")])
    assert _status(r) == "verified" and r.verdict == "CORRECT"


# --- SG-1: the tolerance path ------------------------------------------------------------------------------------
def test_within_rel_tol_reads_numbers_only():
    from mathverify.equiv.numeric import num_equal, within_rel_tol
    t = sp.Rational(1, 1000)
    assert within_rel_tol(sp.Float("2.716") + sp.I, sp.E, t) is False
    assert within_rel_tol(sp.Rational(2716, 1000) + sp.I / 10**9, sp.E, t) is None
    assert within_rel_tol(sp.FiniteSet(sp.Float("2.716")), sp.E, t) is None
    assert within_rel_tol(sp.Tuple(1, 2), sp.E, t) is None
    assert within_rel_tol(sp.Interval(2, 3), sp.E, t) is None
    for c in (sp.FiniteSet(sp.Float("2.716")), sp.Interval(2.7, 2.72), sp.Tuple(2.716, 2.717)):
        assert num_equal(c, sp.E, rel_tol=1e-3)[0] is None
        assert num_equal(c, sp.E)[0] is None


@pytest.mark.parametrize("ir, claim, verdict", [
    (_task("evaluate", {"expr": "E", "rel_tol": "1e-3"}, [X]), "{2.716}", "UNKNOWN"),
    (_task("evaluate", {"expr": "E", "rel_tol": "1e-3"}, [X]), "Interval(2.7, 2.72)", "UNKNOWN"),
    # a pair for a scalar: the shape rule refutes it (matrix_vs_non_matrix), before any tolerance is read
    (_task("evaluate", {"expr": "E", "rel_tol": "1e-3"}, [X]), "(2.716, 2.717)", "INCORRECT"),
    (_task("evaluate", {"expr": "E", "rel_tol": "1e-3"}, [X]), "2.716 + I", "INCORRECT"),
    (_task("evaluate", {"expr": "E", "rel_tol": "1e-3"}, [X]), "2.71828 + I/10**9", "UNKNOWN"),
    (_dint("cos(x)", 0, 1, "1e-3"), "{0.8414}", "UNKNOWN"),
    (_dint("cos(x)", 0, 1, "1e-3"), "(0.8414, 1)", "UNKNOWN"),
    (_dint("cos(x)", 0, 1, "1e-3"), "0.8414 + I", "INCORRECT"),
    (_dint("exp(cos(x))", 0, 1, "1e-3"), "2.3416 + I", "INCORRECT"),
    (_dint("exp(cos(x))", 0, 1, "1e-3"), "2.3416 + I/10**9", "UNKNOWN"),
    (_dint("sin(sin(x))", 0, 1, "1e-3"), "oo", "INCORRECT"),
    (_dint("sin(sin(x))", 0, 1, "1e-3"), "-oo", "INCORRECT"),
])
def test_the_tolerance_path_without_exceptions(ir, claim, verdict):
    r = _v(ir, claim)
    assert r.verdict == verdict and _no_exception(r)


def test_an_infinite_claim_against_a_divergent_integral_is_not_refuted():
    assert _v(_dint("1/x", 0, 1, "1e-3"), "oo").verdict != "INCORRECT"


# --- YO-B: the exact difference at every point -------------------------------------------------------------------
def test_the_difference_is_read_at_every_sample_point():
    from mathverify.equiv.random_point import _RATIONAL_POINTS, random_point_equal, sample_points
    a, b = x**2 + sp.sympify(SN, locals={"x": x}), x**2
    dom = sp.Interval.open(0, sp.oo)
    pts = sample_points({x: dom}, 30, 0, off_grid=True)
    assert all((a - b).subs(x, p[x]) == 0 for p in pts[:_RATIONAL_POINTS])     # zero at the 8 rational points
    ok, ev = random_point_equal(a, b, x, dom)
    assert ok is False and ev["counterexample"] is not None
    assert sp.sympify(ev["counterexample"]["point"]["x"]) not in [p[x] for p in pts[:_RATIONAL_POINTS]]
    ok, _ = random_point_equal(sp.atan(x) - sp.atan(x / 2), sp.atan(x / (x**2 + 2)), x, dom)
    assert ok is True


def test_the_difference_is_read_at_the_probes_too():
    from mathverify.equiv.random_point import _RATIONAL_POINTS, random_point_equal, sample_points
    dom = sp.Interval.open(0, sp.oo)
    pts = sample_points({x: dom}, 30, 0, off_grid=True)
    # 0 at every sample point: sin(Nπx) at the rational ones, a factor x - s at each shifted one; nonzero at x = 1/2,
    # and far below the numbers' tolerance at every probe
    d = sp.sin(NPR * sp.pi * x) * sp.Mul(*[x - p[x] for p in pts[_RATIONAL_POINTS:]]) / sp.Integer(10)**200
    assert all(d.subs(x, p[x]) == 0 for p in pts)
    ok, ev = random_point_equal(x**2 + d, x**2, x, dom)
    assert ok is False and ev["counterexample"] is not None


def test_points_not_read_decide_nothing(monkeypatch):
    import mathverify.equiv.random_point as rp
    monkeypatch.setattr(rp, "_ELSEWHERE_TIMEOUT", 1e-6)
    ok, ev = rp.random_point_equal(sp.sin(x)**2 + sp.cos(x)**2, sp.Integer(1), x, sp.Interval.open(0, sp.oo))
    assert ok is None and ev["reason"] == "difference_at_the_other_points_not_read"


def test_signs_at_the_other_points_are_certified_by_intervals():
    from mathverify.certify.enclosure import constant_sign
    from mathverify.equiv.random_point import random_point_equal
    p = sp.pi / 3000000 + sp.Rational(287652374, 999983)
    d = sp.asin(sp.tanh(p)) - sp.atan(sp.sinh(p))                 # 0, but strict evalf says 2.4e-125 at 30 and 70 digits
    assert constant_sign(d) is None
    assert constant_sign(sp.sin(NPR * sp.pi * (sp.Rational(1, 3) + sp.sqrt(2) / 10**5)) / 10**40) in (-1, 1)
    assert constant_sign(sp.Integer(0)) is None and constant_sign(1 + sp.I) is None
    ok, _ = random_point_equal(sp.asin(sp.tanh(x)), sp.atan(sp.sinh(x)), x, sp.Interval.open(0, sp.oo))
    assert ok is True


def test_nonzero_sign_points_reads_no_zero():
    from mathverify.equiv.random_point import nonzero_sign_points
    d = sp.sin(x)**2 + sp.cos(x)**2 - 1
    pts = [{x: sp.Rational(1, 3)}, {x: sp.sqrt(2)}, {x: 7}]
    assert nonzero_sign_points(d, [x], pts) == []
    assert nonzero_sign_points(d + sp.Integer(10)**-50, [x], pts) == [0, 1, 2]


def test_the_equals_conflict_on_the_antiderivative_path(monkeypatch):
    import mathverify.certify.calculus as cal
    monkeypatch.setattr(cal, "random_point_equal", lambda *a, **k: (True, {}))
    F = x**2 + sp.cos(3000000 * sp.pi * x) / (3000000 * sp.pi)        # dF - 2x = -sin(3e6 π x)
    ok, ev = cal.antiderivative_certificate(F, 2 * x, x)
    assert ok is None and ev.get("conflict") == "sympy_equals_false"
    # agreement read on the whole line when the region (x > 1) left it undecided: the same conflict
    monkeypatch.setattr(cal, "random_point_equal", lambda a, b, v, dom, **k: (True if dom == sp.S.Reals else None, {}))
    ok, ev = cal.antiderivative_certificate(F, 2 * x, x, discourse=sp.Interval.open(1, sp.oo))
    assert ok is None and ev.get("conflict") == "sympy_equals_false"


@pytest.mark.parametrize("ir, claim", [
    (_task("simplify_expression", {"expr": "x**2"}, [X_POS], shape="expression"), f"x**2 + {SN}"),
    (_task("antiderivative", {"integrand": "2*x", "var": "x"}, [X], shape="expression"), f"x**2 + {CN} + C"),
    (_task("antiderivative", {"integrand": "2*x", "var": "x"}, [X_POS], shape="expression"), f"x**2 + {CN} + C"),
    (_task("derivative", {"f": "x**2", "var": "x"}, [X_POS], shape="expression"), f"2*x + {SN}"),
])
def test_below_the_tolerance_on_every_path(ir, claim):
    assert _v(ir, claim, kind="expression").verdict == "INCORRECT"


# --- YO-C: points inside the domain -------------------------------------------------------------------------------
def test_sample_points_lie_inside_a_narrow_domain():
    from mathverify.equiv.random_point import _inside, sample_points
    for dom in (sp.Interval.open(3, 3 + sp.Rational(1, 10**7)), sp.Interval.open(0, sp.Rational(1, 10**7)),
                sp.Interval.Lopen(sp.pi, sp.pi + sp.Rational(1, 10**9))):
        for off in (True, False):
            pts = sample_points({x: dom}, 30, 0, off_grid=off)
            assert len(pts) == 30 and all(dom.contains(p[x]) == sp.true for p in pts), dom
    rng = random.Random(0)
    for dom in (sp.Interval.open(-sp.oo, 2), sp.Interval.open(2, sp.oo), sp.Interval.open(0, sp.Rational(1, 10**12))):
        for shift in (None, False, True):
            q = _inside(dom, rng, shift)
            assert q is not None and dom.contains(q) == sp.true
            assert (q.is_rational is False) == bool(shift)


@pytest.mark.parametrize("dom, expr, claim, verdict", [
    (X_N3, "x", "2*x - 3", "INCORRECT"),
    (X_N3, "x", "3", "INCORRECT"),
    (X_N0, "x", "x + x**2", "INCORRECT"),
    (X_N0, "x", "x", "CORRECT"),
    (X_N3, "(x - 3)**2", "x**2 - 6*x + 9", "CORRECT"),
])
def test_narrow_domains(dom, expr, claim, verdict):
    ir = _task("simplify_expression", {"expr": expr}, [dom], shape="expression")
    assert _v(ir, claim, kind="expression").verdict == verdict


# --- BİRLEŞİK-1: the odd-root convention of a fractional power ------------------------------------------------------
def test_odd_root_convention_met_by_the_fractional_power_rule():
    from mathverify.certify.calculus import _exact_conditions
    t = sp.Symbol("t", real=True)
    assert _exact_conditions(sp.exp(-t**sp.Rational(1, 3)), t) == [t >= 0]
    assert set(_exact_conditions((t - 1)**sp.Rational(-1, 3), t)) == {sp.Ne(t - 1, 0), t - 1 > 0}
    assert _exact_conditions(t + (-1)**sp.Rational(1, 3), t) is None          # a constant base: no rule here


def test_odd_root_integrals():
    G = _task("evaluate", {"expr": "Integral(exp(-t**(1/3)), (t, 0, oo))"}, [T_])
    assert _v(G, "6").verdict == "CORRECT" and _v(G, "5").verdict == "INCORRECT"
    E = _task("evaluate", {"expr": "Integral(x**(1/3), (x, 0, 1))"}, [X])
    assert _v(E, "3/4").verdict == "CORRECT" and _v(E, "1").verdict == "INCORRECT"
    assert _v(_task("evaluate", {"expr": "Integral(x**(1/3), (x, -1, 0))"}, [X]), "-3/4").verdict == "UNKNOWN"
    assert _v(_dint("x**(1/3)", -1, 0), "-3/4").verdict == "UNKNOWN"
    assert _v(_dint("x + (-1)**(1/3)", 0, 1), "-1/2").verdict == "UNKNOWN"
