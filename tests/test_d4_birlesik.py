"""Merged state of the fourth audit's fixes (A+, 15 Oct 2026; DECISIONS §89): interactions of the parts.

d4b round 10 trusts strict evalf only on the nodes SymPy tracks the accuracy of, and d4c round 3 checks each significant
reading again at a higher precision. Merged, asin(tanh x) at a large x had no sign (tanh x within the working precision
of 1), and the true identity asin(tanh x) = atan(sinh x) on x > 0 fell to UNKNOWN. The sign of an odd increasing function
of a real argument is the argument's sign (exact facts, `numeric._monotone_sign`).

d4b round 10 reads x**x through a convention (`Convention` real_power: 0**0 and a negative base are undecided), and the
integral certificate abstained when the convention failed anywhere on the closed range: d4c's refutation of
∫_0^1 x**x dx = 100 by its enclosure fell to UNKNOWN. An integral does not read its integrand on a finite set; a
convention that fails at finitely many points of the range at most (`domain.convention_null_on`) no longer stops it, one
that fails on a piece of positive length still does. The same holds for a limit (its point is not read: lim_{x->0+} x**x
= 1 had fallen to UNKNOWN) and a derivative (its neighbourhood shrinks; its point is read as written). d4b's zero_power
of x**sqrt(2) also closed the fundamental theorem of calculus (`calculus._exact_conditions`) on every range: its point
is read like a pole there."""
import pytest
import sympy as sp

from mathverify.certify.calculus import certified_integral_value
from mathverify.certify.domain import Convention, convention_null_on
from mathverify.equiv import numeric
from mathverify.equiv.numeric import NONREAL, certified_sign
from mathverify.equiv.random_point import random_point_equal
from mathverify.verifier import verify

C = sp.Rational(982817908, 1000033)                     # tanh C = 1 - 2e-854
Q = sp.log(6) - sp.log(2) - sp.log(3)                   # exactly 0
x = sp.Symbol("x", real=True)


@pytest.mark.parametrize("e, s", [
    (sp.asin(sp.tanh(C)), 1), (sp.asin(sp.tanh(-C)), -1), (sp.acos(sp.tanh(C)), 1), (sp.atanh(sp.tanh(C)), 1),
    (sp.erf(C), 1), (sp.erf(-C), -1), (sp.sinh(C), 1), (sp.cosh(-C), 1), (-2 * sp.pi * sp.asin(sp.tanh(C)), -1),
    (sp.asin(Q), 0), (sp.sinh(Q), 0), (sp.asin(sp.tanh(Q)), 0), (Q * sp.pi, 0),
])
def test_monotone_functions_take_their_arguments_sign(e, s):
    assert certified_sign(e) == s


def test_monotone_rule_reads_nothing_off_a_domain_it_cannot_prove():
    assert numeric._monotone_sign(sp.asin(2), 5.0) is None and certified_sign(sp.asin(2)) == NONREAL
    assert numeric._monotone_sign(sp.atanh(sp.cos(0, evaluate=False)), 5.0) is None    # cos 0 = 1: not inside (-1, 1)
    assert numeric._monotone_sign(sp.acos(sp.cos(sp.Rational(1, 7)) / 3), 5.0) == 1     # |cos(1/7)/3| < 1, certified
    assert numeric._monotone_sign(sp.I * sp.pi, 5.0) is None                               # a nonreal factor: no product


def test_a_strict_reading_that_does_not_stand_higher_is_dropped(monkeypatch):
    # d4c round 3's `_stands` inside d4b round 10's `_evalf_sign`, the reading of e and of -e alike: a sign that turns
    # at the higher precision decides nothing (the asin(tanh x) case itself is no longer read by the strict evaluation,
    # so the filter is checked on its mechanism)
    lo = (sp.Float(1, 30), sp.Integer(0), "value", "zero")
    hi = (sp.Float(-1, 60), sp.Integer(0), "value", "zero")
    monkeypatch.setattr(numeric, "_evalf_strict",
                        lambda e, dps=numeric._SIGN_DPS: lo if dps == numeric._SIGN_DPS else hi)
    assert numeric._evalf_sign(sp.sqrt(2) - 1, 5.0) is numeric._NOT_READ


def test_the_gudermann_identity_holds_on_the_positive_reals():
    ok, ev = random_point_equal(sp.asin(sp.tanh(x)), sp.atan(sp.sinh(x)), x, sp.Interval.open(0, sp.oo))
    assert ok is True, ev
    ok, ev = random_point_equal(sp.asin(sp.tanh(x)), sp.atan(sp.sinh(x)) + sp.Rational(1, 10**30), x,
                                sp.Interval.open(0, sp.oo))
    assert ok is False


# --- a convention on a null set of an integral's range (d4b round 10 x d4c round 4) ---------------------------------
def _ir(kind, params):
    return {"task": {"kind": kind, "params": params}, "vars": [{"name": "x", "domain": "real"}], "givens": [],
            "answer_shape": "scalar"}


def _dint(f, a, b):
    return _ir("definite_integral", {"integrand": f, "var": "x", "a": str(a), "b": str(b)})


def _run(ir, payload):
    return verify(ir, {"claimed_answer": {"kind": "value", "payload": payload}, "steps": []})


def _reasons(r):
    return [layer.evidence.get("reason") for layer in r.layers if layer.layer.startswith("certify")]


@pytest.mark.parametrize("f, a, b, claim, verdict", [
    ("x**x", 0, 1, "100", "INCORRECT"),               # real_power: 0**0 at an end
    ("x**x", 1, 0, "-100", "INCORRECT"),
    ("(x - 1)**x", 1, 2, "100", "INCORRECT"),
    ("sin(x)**x", 0, 1, "100", "INCORRECT"),          # the base's sign read on the range itself, not on one period
    ("x**sqrt(2)", 0, 1, "sqrt(2) - 1", "CORRECT"),   # zero_power: 0**sqrt(2) at an end, then the FTC
    ("x**sqrt(2)", 0, 1, "1", "INCORRECT"),
    ("x**0", -1, 1, "2", "CORRECT"),                  # zero_power: 0**0 inside the range, one point
    ("x**0", -1, 1, "3", "INCORRECT"),
    ("x**(1/3)", 0, 1, "3/4", "CORRECT"),             # odd_root: the base is >= 0 on the whole range
])
def test_a_convention_on_finitely_many_points_does_not_stop_an_integral(f, a, b, claim, verdict):
    assert _run(_dint(f, a, b), claim).verdict == verdict


@pytest.mark.parametrize("f, a, b, claim", [
    ("x**x", -1, 1, "100"), ("x**x", -1, 0, "100"), ("(x - 1)**x", 0, 2, "100"), ("x**(1/3)", -1, 1, "0"),
    ("(-1)**x", 0, 1, "100"), ("binomial(x, 2)", 0, 3, "100"), ("Mod(7, x)", -1, 1, "100"),
])
def test_a_convention_on_a_piece_of_positive_length_still_stops_it(f, a, b, claim):
    r = _run(_dint(f, a, b), claim)
    assert r.verdict == "UNKNOWN" and "membership_condition_on_variable" in _reasons(r)


def test_a_derivative_reads_its_point_and_a_small_neighbourhood():
    # x**0 is 1 off 0; at 0 it is 1 or undefined, and so is its derivative there
    assert _run(_ir("derivative", {"f": "x**0", "var": "x", "at": "0"}), "0").verdict == "UNKNOWN"
    assert _run(_ir("derivative", {"f": "x**0", "var": "x", "at": "1"}), "0").verdict == "CORRECT"
    # a convention point 1/2000 away is passed by a smaller neighbourhood; at it, the point is read as written
    f = "x + 0*(x - 1/2000)**0"
    assert _run(_ir("derivative", {"f": f, "var": "x", "at": "0"}), "1").verdict == "CORRECT"
    assert _run(_ir("derivative", {"f": f, "var": "x", "at": "1/2000"}), "1").verdict == "UNKNOWN"


@pytest.mark.parametrize("expr, to, side, claim, verdict", [
    ("x**x", "0", "+", "1", "CORRECT"), ("x**x", "0", "+", "0", "INCORRECT"),     # 0**0 at the point is not read
    ("x**x", "0", None, "1", "UNKNOWN"), ("x**x", "0", "-", "1", "UNKNOWN"),      # x**x on (-d, 0): two readings
    ("x**0", "0", None, "1", "CORRECT"), ("x**sqrt(2)", "0", "+", "0", "CORRECT"),
    ("atan2(x, x)", "0", "+", "pi/4", "CORRECT"), ("atan2(x, x)", "0", None, "pi/4", "INCORRECT"),
])
def test_a_limit_does_not_read_its_point(expr, to, side, claim, verdict):
    p = {"expr": expr, "var": "x", "to": to}
    if side:
        p["side"] = side
    assert _run(_ir("limit", p), claim).verdict == verdict


def test_the_points_where_a_convention_may_fail():
    def c(u, kind):
        return sp.Contains(u, Convention(kind))
    one, line = sp.Interval(0, 1), sp.Interval(-1, 1)
    assert convention_null_on(c(sp.Tuple(x, x), "real_power"), x, one)
    assert convention_null_on(c(sp.Tuple(x, x), "real_power"), x, sp.Interval(0, sp.oo))
    assert convention_null_on(c(sp.Tuple(x, x), "real_power"), x, sp.Interval(0, 0))         # [0, 0] = {0}
    assert not convention_null_on(c(sp.Tuple(x, x), "real_power"), x, line)
    assert convention_null_on(c(x, "zero_power"), x, line)                                    # {0}
    assert convention_null_on(c(2 * x**2, "origin"), x, line)
    assert convention_null_on(c(x, "mod_divisor"), x, sp.Interval(1, 2))
    assert not convention_null_on(c(x, "mod_divisor"), x, line)
    assert convention_null_on(c(x, "odd_root"), x, one)
    assert not convention_null_on(c(x, "odd_root"), x, line)
    for kind in ("negative_base", "integer_bound", "binomial"):                              # off the integers
        assert not convention_null_on(c(x, kind), x, one)
    assert not convention_null_on(sp.Contains(x, sp.Complement(sp.S.Reals, sp.FiniteSet(0))), x, one)
    # a set no exact class gives proves nothing (x + sin(x**2) > 0 on (0, 1], unproved)
    assert not convention_null_on(c(sp.Tuple(x + sp.sin(x**2), x), "real_power"), x, one)


def test_the_fundamental_theorem_with_an_irrational_power():
    r2 = 1 + sp.sqrt(2)
    assert sp.simplify(certified_integral_value(x**sp.sqrt(2), x, 1, 2)[0] - (2**r2 - 1) / r2) == 0
    assert certified_integral_value(x**sp.sqrt(2), x, 0, 1)[0] == 1 / r2
    assert certified_integral_value(x**sp.sqrt(2), x, -1, 1)[0] is None                    # undefined on [-1, 0)


# --- a closed form's sign (d4b round 10 x d4h round 2) ------------------------------------------------------------
# d4b round 10 reads no strict sign off a form (its evaluation is not tracked); d4h keeps a form unevaluated wherever a
# value decides, its value from `equiv.forms.checked_forms` alone. Merged, the step floor(∫_0^3 x dx) = 3 and the given
# x > ∫_0^3 x dx with x = 5 had no sign; a certified sign now reads a form through its checked value, never while a
# text is read, and a jump over a form is not evaluated when it is built (`numeric._forms_valued`, `parse._jump_eval`).
I3 = sp.Integral(x, (x, 0, 3))                                                       # 9/2
SPK = sp.Integral(1000 * sp.exp(-10**6 * (x - sp.Rational(1, 3))**2), (x, -1, 1))   # sqrt(pi)*(erf + erf)/2 ~ 1.77


def test_a_form_has_the_sign_of_its_checked_value():
    from mathverify.normalize import parse
    assert certified_sign(5 - I3) == 1 and certified_sign(I3 - 5) == -1 and certified_sign(I3 - sp.Rational(9, 2)) == 0
    assert certified_sign(SPK - 1) == 1                    # SymPy's evalf of it is 2.9e-834: the sign was -1
    token = parse._FORMS_HELD.set(True)
    try:
        assert certified_sign(5 - I3) is None              # a text being read keeps its forms as written
    finally:
        parse._FORMS_HELD.reset(token)
    assert isinstance(parse.floor(I3), sp.floor)           # not evaluated when built; checked_forms gives 4
    ev = {"task": {"kind": "evaluate", "params": {"expr": "x"}}, "vars": [{"name": "x", "domain": "real"}],
          "givens": [f"x > {I3}", "x = 5"], "answer_shape": "scalar"}
    assert _run(ev, "5").verdict == "CORRECT"
    one = _ir("evaluate", {"expr": "1"})
    for step, status in ((f"floor({I3}) = 4", "verified"), (f"floor({I3}) = 3", "refuted")):
        r = verify(one, {"claimed_answer": {"kind": "value", "payload": "1"},
                         "steps": [{"id": "s1", "kind": "compute", "claim": step, "from": [], "text": ""}]})
        assert [s["status"] for layer in r.layers if layer.layer == "steps.refute"
                for s in layer.evidence.get("steps", [])] == [status], step


# --- count_roots: its expression = 0 is a premise of the steps (d4h's _TASK_RELATION_PARAMS) ---------------------
def _count_roots(expr, n, steps, **kw):
    ir = {"task": {"kind": "count_roots", "params": {"expr": expr, "var": "x", **kw}},
          "vars": [{"name": "x", "domain": "real"}], "givens": [], "answer_shape": "count"}
    r = verify(ir, {"claimed_answer": {"kind": "count", "payload": n},
                    "steps": [{"id": f"s{i}", "kind": "eq", "claim": c, "from": [], "text": ""}
                              for i, c in enumerate(steps)]})
    return r.verdict, [s["status"] for layer in r.layers if layer.layer == "steps.refute"
                       for s in layer.evidence.get("steps", [])]


@pytest.mark.parametrize("steps, n, kw, verdict, statuses", [
    (["x + 2 = x**2"], 2, {}, "CORRECT", ["verified"]),          # refuted and INCORRECT without the premise
    (["(x - 2)*(x + 1) = 0"], 2, {}, "CORRECT", ["verified"]),
    (["x + 2 = x**2"], 1, {"lo": "0"}, "CORRECT", ["verified"]),
    (["x + 2 = x**3"], 2, {}, "INCORRECT", ["refuted"]),
])
def test_count_roots_reads_its_expression_as_a_premise(steps, n, kw, verdict, statuses):
    assert _count_roots("x**2 - x - 2", n, steps, **kw) == (verdict, statuses)


# --- a gcd or lcm of numbers written unevaluated (d4b round 10) -----------------------------------------------------
def test_a_gcd_of_numbers_written_unevaluated_has_its_exact_value():
    # \\gcd(2^{2}, 6) is read with 2^{2} as written; d4b round 10 tracks no evaluation of the class, and the wrong
    # claim 4 had fallen from INCORRECT (81acaff) to UNKNOWN
    from mathverify.normalize.parse import gcd, lcm
    four = sp.Pow(2, 2, evaluate=False)
    with sp.evaluate(False):
        g, m = gcd(6, four), lcm(6, four)
    assert certified_sign(g - 4) == -1 and certified_sign(g - 2) == 0 and certified_sign(m - 12) == 0
    near = 3 + sp.exp(-sp.exp(10))                      # no integer: its numeric value (_imp_) rounds it to 3
    with sp.evaluate(False):
        assert certified_sign(gcd(near, 6) - 3) != 0
        assert certified_sign(gcd(sp.log(8) / sp.log(2), 6) - 3) in (0, None)      # exactly 3: proved, or undecided
    ir = _ir("evaluate", {"expr": "\\gcd(2^{2}, 6)"})
    assert _run(ir, "4").verdict == "INCORRECT" and _run(ir, "2").verdict == "CORRECT"
