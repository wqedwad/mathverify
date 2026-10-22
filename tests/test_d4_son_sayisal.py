"""The A+ final attack, lens 1 (numeric sign; 16 Oct 2026): G1YO-1 and G1YO-2.

* G1YO-1 (false acceptance, realistic): (1 + i*sqrt(3))**3 is exactly -8, and SymPy evaluates it as -8.0 + 0.e-22*I,
  an imaginary part of one bit, rounding noise. `_sympy_guards.strict_sign` read it "nonreal" without asking for its
  significant bits; the patched assumption fallback then called the number neither positive nor negative while
  SymPy knows it real (arg/pi rational), and SymPy concluded ZERO for (1 + i*sqrt(3))**3 - 5: Eq(X, 5) was True,
  simplify(X - 5) was 0, Abs(X + 30) was 0, and 5, every wrong answer of the De Moivre family, a wrong option and a
  wrong step were certified, while |X + 30| = 22 was refuted. Two more readings of the same noise: SymPy's product of
  complex factors gives both parts the accuracy of the whole (-(1 + i*sqrt(3))**3 = 8.0 - 2.8e-26*I "with 64 bits":
  2*X = 16 was CORRECT, -X "certainly not an integer"), and an argument SymPy knows real but evaluates with such a
  part was read by sin/cos/tan's untracked complex path or on the branch cut of log and sqrt by the sign of the noise
  (log(X) = log(8) - i*pi, sqrt(-X - 16) = -2*sqrt(2)*i). Decision: a part decides only with significant bits of its
  own (>= 20), measured against the error of the whole number; noise is undecided, never "nonreal".
* G1YO-2 (false acceptance, artificial): `sandbox.exactsets._on` read a progression's candidate indices in floating
  point; on [10^18, 10^18 + 20] the six zeros of sin x fell out and the empty set was certified. Decision: a window
  too far out for a float index is left unsolved.

Each test names the direction it guards (false acceptance / unjust refutation / mechanism).
"""
from __future__ import annotations

import pytest
import sympy as sp
from sympy.core.cache import clear_cache

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
x = sp.Symbol("x", real=True)
C3 = "(1 + sqrt(3)*I)**3"
P3 = sp.Pow(1 + sp.sqrt(3) * sp.I, 3)       # exactly -8, kept by SymPy as a power


def _ev(expr, claim, steps=(), options=None, option=None, dod=None, vars_=(), givens=()):
    ir = {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
          "answer_shape": "scalar"}
    if options:
        ir["options"] = options
    if dod:
        ir["domain_of_discourse"] = dod
    ca = {"kind": "value", "payload": claim}
    if option:
        ca["option"] = option
    r = verify(ir, {"claimed_answer": ca, "steps": [{"id": f"s{i}", "kind": k, "claim": c, "from": [], "text": ""}
                                                   for i, (k, c) in enumerate(steps)]})
    layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
    return r.verdict, [s.get("status") for s in (layer.evidence.get("steps", []) if layer is not None else [])]


def _task(kind, params, claim, shape="scalar", vars_=(X,), claim_kind="value"):
    ir = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": [], "answer_shape": shape}
    return verify(ir, {"claimed_answer": {"kind": claim_kind, "payload": claim}, "steps": []}).verdict


# --- G1YO-1: false acceptance ------------------------------------------------------------------------------------

@pytest.mark.parametrize("expr,right,wrongs", [
    (C3, "-8", ["5", "8", "-7"]),
    ("(1 + i*sqrt(3))^3", "-8", ["5"]),
    ("(sqrt(3) + I)**6", "-64", ["64"]),
    ("((sqrt(3) + I)/2)**12", "1", ["12"]),
    ("(cos(pi/3) + I*sin(pi/3))**3", "-1", ["1"]),
    ("(1 - sqrt(3)*I)**6", "64", ["-64", "32"]),
    ("(1 + sqrt(3)*I)**3 + (1 - sqrt(3)*I)**3", "-16", ["16"]),
])
def test_a_real_power_of_a_complex_number_certifies_its_value_only(expr, right, wrongs):
    """False acceptance: every wrong answer of the De Moivre family was CORRECT (SymPy made X - c zero)."""
    assert _ev(expr, right)[0] == "CORRECT"
    for w in wrongs:
        assert _ev(expr, w)[0] == "INCORRECT", (expr, w)


def test_a_wrong_option_and_a_wrong_step_are_not_accepted():
    """False acceptance: the wrong option E (5) was CORRECT, the step (1 + i*sqrt(3))**3 = 5 verified."""
    opts = {"A": "-8", "B": "8", "C": "-4", "D": "4", "E": "5"}
    assert _ev(C3, "5", options=opts, option="E")[0] == "INCORRECT"
    assert _ev(C3, "-8", options=opts, option="A")[0] == "CORRECT"
    assert _ev(C3, "-8", steps=[("eq", f"{C3} = 5")]) == ("INCORRECT", ["refuted"])
    assert _ev(C3, "-8", steps=[("eq", f"{C3} = -8")]) == ("CORRECT", ["verified"])


def test_a_product_holding_the_power_certifies_its_value_only():
    """False acceptance: 2*X = 16 and -X = -8 were CORRECT (the product gave its noise 64 bits)."""
    assert _ev(f"2*{C3}", "16")[0] == "INCORRECT"
    assert _ev(f"2*{C3}", "-16")[0] == "CORRECT"
    assert _ev(f"-{C3}", "-8")[0] == "INCORRECT"
    assert _ev(f"-{C3}", "8")[0] == "CORRECT"


def test_the_power_in_other_tasks_certifies_its_value_only():
    """False acceptance: lim (x + X) = 5 and (X*x)'(1) = 5 were CORRECT."""
    assert _task("limit", {"expr": f"x + {C3}", "var": "x", "to": "0"}, "5", "dne_or_scalar") == "INCORRECT"
    assert _task("derivative", {"f": f"{C3}*x", "var": "x", "at": "1"}, "5") == "INCORRECT"


# --- G1YO-1: unjust refutation -----------------------------------------------------------------------------------

def test_the_value_of_the_power_inside_abs_roots_and_extrema_is_certified():
    """Unjust refutation: |X + 30| = 22, cbrt(X + 35) = 3 and max of x**2 + X on [0, 1] = -7 were INCORRECT (Abs and
    the roots folded X + 30 to 0)."""
    assert _ev(f"Abs({C3} + 30)", "22")[0] == "CORRECT"
    assert _ev(f"Abs({C3} + 30)", "0")[0] == "INCORRECT"
    assert _ev(f"cbrt({C3} + 35)", "3")[0] == "CORRECT"
    assert _ev(f"sqrt({C3} + 12)", "2")[0] == "CORRECT"
    assert _task("extremum", {"f": f"x**2 + {C3}", "var": "x", "which": "max", "interval": "[0, 1]"}, "-7") == \
        "CORRECT"


def test_a_real_number_written_with_complex_numbers_inside_log_and_sqrt():
    """Unjust refutation (and its mirror): log(X) and sqrt(-X - 16) were read on their branch cut by the sign of the
    noise; the right principal values are certified over C, the conjugate branch is not."""
    assert _ev(f"log({C3})", "log(8) + I*pi", dod="complex")[0] == "CORRECT"
    assert _ev(f"log({C3})", "log(8) - I*pi", dod="complex")[0] == "INCORRECT"
    assert _ev(f"sqrt({C3})", "2*sqrt(2)*I", dod="complex")[0] == "CORRECT"
    assert _ev(f"sqrt({C3})", "-2*sqrt(2)*I", dod="complex")[0] == "INCORRECT"
    assert _ev(f"sin(pi*{C3}/8)", "0")[0] == "CORRECT"
    assert _ev(f"sin(pi*{C3}/8)", "1/2")[0] != "CORRECT"


# --- G1YO-1: mechanism -------------------------------------------------------------------------------------------

def test_sympy_does_not_make_the_power_equal_to_a_wrong_value():
    """Mechanism: SymPy's own relation, zero test, simplification and Abs of X - 5 and X + 30."""
    assert sp.Eq(P3, 5) is not sp.true
    assert (P3 - 5).is_zero is not True
    assert sp.simplify(P3 - 5) == -13
    assert sp.Abs(P3 + 30) != 0
    assert (P3 - 5).equals(0) is False
    assert (P3 + 8).is_zero is True                  # its true value still is (minimal polynomial t)


def test_an_imaginary_part_of_noise_is_neither_real_nor_nonreal():
    """Mechanism: strict_sign of X is undecided (its imaginary part has 1 bit); a significant one is still read."""
    from mathverify._sympy_guards import strict_sign, strict_value
    v = strict_value(P3, 15)
    assert v is not None and sp.im(v)._prec < 20      # the noise is there, and SymPy says so
    assert strict_sign(P3) is None
    assert strict_sign(-P3) is None
    assert strict_sign(5 - P3) is None
    assert strict_sign(P3 * sp.I) == "nonreal"
    assert strict_sign(P3 + 8 + sp.I / 1000) == "nonreal"
    assert strict_sign(sp.sqrt(2) + sp.I) == "nonreal"
    assert strict_sign(sp.sqrt(2) - 1) == 1


def test_a_product_measures_each_part_against_the_whole_number():
    """Mechanism: SymPy's product gives both parts the accuracy of the whole; each part is measured against the
    error of the whole (`_part_accuracies`): -X is a real 8, an integer, whose imaginary part is noise."""
    import sympy.core.evalf as evalf_mod
    from mathverify.equiv.numeric import NONREAL, certified_integer, certified_sign
    r = evalf_mod.evalf(-P3, 64, {"strict": True, "maxprec": 2048, "chop": False})
    assert r[1] is not None and r[3] < 20
    assert certified_integer(-P3) == (True, sp.Integer(8))
    assert certified_integer(2 * P3) == (True, sp.Integer(-16))
    assert certified_sign(-P3 - 9) == -1
    assert certified_sign(-P3 + sp.I / 10**20) == NONREAL     # a small part with bits of its own is still read


def test_a_real_argument_evaluated_with_noise_has_no_reading_off_it():
    """Mechanism: an argument SymPy knows real but evaluates with an imaginary part of noise is not read by the
    untracked complex path of sin, nor on the branch cut of log and sqrt; the exact tests decide instead."""
    from mathverify._sympy_guards import strict_value
    from mathverify.equiv.numeric import certified_sign
    S8 = sp.sin(sp.pi * P3 / 8)                      # exactly sin(-pi) = 0
    assert strict_value(S8, 15) is None
    assert strict_value(sp.log(P3), 15) is None
    assert strict_value(sp.sqrt(-16 - P3), 15) is None
    assert certified_sign(S8) == 0
    assert certified_sign(sp.log(P3) - sp.log(8) - sp.I * sp.pi) == 0
    assert certified_sign(sp.sqrt(-16 - P3) - 2 * sp.sqrt(2) * sp.I) == 0
    # a power of a real base off the cut by a positive real part is read: sqrt(X + 12) = 2
    v = strict_value(sp.sqrt(P3 + 12), 15)
    assert v is not None and abs(sp.re(v) - 2) < sp.Float(10) ** -12


def test_a_nonreal_reading_of_a_number_sympy_knows_real_decides_no_sign(monkeypatch):
    """Mechanism (second line): were a strict reading to call a number SymPy knows real "nonreal", the fallback
    would not make it zero."""
    from mathverify import _sympy_guards
    monkeypatch.setattr(_sympy_guards, "strict_sign", lambda e: "nonreal")
    clear_cache()
    try:
        assert (P3 - 5).is_zero is not True
        assert (sp.Pow(sp.sqrt(2) + sp.sqrt(6) * sp.I, 3) + 7).is_zero is not True
    finally:
        clear_cache()


# --- G1YO-2 ------------------------------------------------------------------------------------------------------

BIG_CONS = ["x >= 10**18", "x <= 10**18 + 20"]


def _eq(equation, cons, claim, claim_kind="set"):
    return _task("solve_equation", {"equation": equation, "var": "x"}, claim, "set",
                 (dict(X, constraints=cons),), claim_kind)


def test_a_window_far_from_zero_certifies_no_empty_set():
    """False acceptance: on [10^18, 10^18 + 20] the empty set was certified for sin x = 0 and cos x = 1, the whole
    window for |sin x| > 0 (the window holds six zeros of sin x)."""
    assert _eq("sin(x) = 0", BIG_CONS, "EmptySet") != "CORRECT"
    assert _eq("cos(x) = 1", BIG_CONS, "EmptySet") != "CORRECT"
    assert _task("solve_inequality", {"inequality": "Abs(sin(x)) > 0", "var": "x"},
                 "Interval(10**18, 10**18 + 20)", "set", (dict(X, constraints=BIG_CONS),), "interval") != "CORRECT"


def test_a_progression_far_out_is_left_unsolved():
    """Mechanism: the float index of a progression's points holds within 2^48 steps of 0; past it, unsolved."""
    from mathverify.sandbox import exactsets
    with pytest.raises(exactsets._Unsolved):
        exactsets._on([(sp.S.Zero, sp.pi)], sp.Integer(10**18), sp.Integer(10**18 + 20))
    with pytest.raises(exactsets._Unsolved):
        exactsets._on([(sp.Integer(10**17), sp.pi)], sp.S.Zero, sp.Integer(10))
    w = sp.Interval(10**18, 10**18 + 20)
    assert isinstance(exactsets.exact_solveset(sp.Eq(sp.sin(x), 0), x, w), sp.ConditionSet)
    # within the bound every point is found: 10^13 is 1.6e12 steps of 2*pi out
    pts = exactsets._on([(sp.S.Zero, 2 * sp.pi)], sp.Integer(10**13), sp.Integer(10**13 + 20))
    assert pts == [k * 2 * sp.pi for k in range(1591549430919, 1591549430923)]      # mpmath, 50 digits


def test_a_window_near_zero_keeps_its_points():
    """Unjust refutation: the fail-closed bound leaves every curriculum window solved."""
    assert _eq("sin(x) = 0", ["x >= 1", "x <= 10"], "{pi, 2*pi, 3*pi}") == "CORRECT"
    assert _eq("sin(x) = 0", ["x >= 1", "x <= 10"], "EmptySet") == "INCORRECT"
    assert _eq("cos(x) = 1", ["x >= 10**6", "x <= 10**6 + 7"], "{318310*pi, 318312*pi}") == "CORRECT"


# --- SON-G3-RK-3: the principal argument's two conventions ---------------------------------------------------------

def _arg(expr, claim, givens=(), steps=(), dod="complex"):
    return _ev(expr, claim, steps=steps, dod=dod, givens=givens)[0]


@pytest.mark.parametrize("expr,turkish,sympys", [
    ("arg(-1 - I)", "5*pi/4", "-3*pi/4"),
    ("arg(-I)", "3*pi/2", "-pi/2"),
    ("arg(1 - sqrt(3)*I)", "5*pi/3", "-pi/3"),
])
def test_a_principal_argument_right_in_one_convention_is_undecided(expr, turkish, sympys):
    """Unjust refutation: the [0, 2*pi) value (the curriculum's) was INCORRECT; false acceptance of a convention: the
    (-pi, pi] value (SymPy's) was CORRECT. Below the real axis each is right in one convention only: UNKNOWN."""
    assert _arg(expr, turkish) == "UNKNOWN"
    assert _arg(expr, sympys) == "UNKNOWN"


def test_a_principal_argument_wrong_in_both_conventions_is_refuted():
    """False acceptance: a value right in neither range, or off by a multiple of 2*pi, stays INCORRECT; where the
    ranges agree (the upper half plane, the real axis) the value is CORRECT."""
    assert _arg("arg(-1 - I)", "pi/4") == "INCORRECT"
    assert _arg("arg(-1 - I)", "13*pi/4") == "INCORRECT"
    assert _arg("2*arg(-1 - I)", "pi/2") == "INCORRECT"
    assert _arg("arg(1 + I)", "pi/4") == "CORRECT"
    assert _arg("arg(1 + I)", "9*pi/4") == "INCORRECT"
    assert _arg("arg(-1)", "pi") == "CORRECT"
    assert _arg("arg(-1)", "-pi") == "INCORRECT"
    assert _arg(f"arg({C3})", "pi") == "CORRECT"


def test_a_written_range_reads_the_principal_argument_in_it():
    """The problem's own range decides: given -pi < arg <= pi, -3*pi/4 is CORRECT and 5*pi/4 INCORRECT; given
    0 <= arg < 2*pi the other way round."""
    sympy_range = ["-pi < arg(-1 - I)", "arg(-1 - I) <= pi"]
    curriculum = ["0 <= arg(-1 - I)", "arg(-1 - I) < 2*pi"]
    assert _arg("arg(-1 - I)", "-3*pi/4", sympy_range) == "CORRECT"
    assert _arg("arg(-1 - I)", "5*pi/4", sympy_range) == "INCORRECT"
    assert _arg("arg(-1 - I)", "5*pi/4", curriculum) == "CORRECT"
    assert _arg("arg(-1 - I)", "-3*pi/4", curriculum) == "INCORRECT"


def test_atan2_keeps_its_one_range():
    """atan2, a programming function, is read in (-pi, pi] only."""
    assert _arg("atan2(-1, -1)", "-3*pi/4", dod=None) == "CORRECT"
    assert _arg("atan2(-1, -1)", "5*pi/4", dod=None) == "INCORRECT"


def test_arg_is_read_in_zero_two_pi_within_its_reading():
    """Mechanism: the parser's arg in [0, 2*pi) adds 2*pi where the imaginary part is negative, and only there;
    a text names arg as a function, not as a key."""
    from mathverify.normalize.parse import arg_reading, parse_expr_str
    from mathverify.verifier import _writes_arg
    assert parse_expr_str("arg(-1 - I)") == -3 * sp.pi / 4
    with arg_reading("zero_two_pi"):
        assert parse_expr_str("arg(-1 - I)") == 5 * sp.pi / 4
        assert parse_expr_str("arg(1 + I)") == sp.pi / 4
        assert parse_expr_str("arg(-1)") == sp.pi
    assert _writes_arg({"expr": "2*arg(z)"}) and _writes_arg(["\\arg(z)"])
    assert not _writes_arg({"arg": "x**2", "args": ["x"]}) and not _writes_arg("args(z)")


# --- SS-YO-1 (second round): the extremum's candidates are the set it calls complete ----------------------------

def _ext(f, interval, which, claim):
    return _task("extremum", {"f": f, "var": "x", "which": which, "interval": interval}, claim)


K1 = "(2 + I)*(2 - I)/5"                  # exactly 1, written with complex numbers
A_, S_, C_ = sp.Abs, sp.sin, sp.cos

# the auditors' 14 functions with Abs/Max of trigonometric functions, with the maximum found independently (mpmath, a
# 20001-point grid and the exact candidates): (f, interval, the true maximum, the larger endpoint value when it is
# not the maximum)
ABS_TRIG = [
    ("Abs(sin(x)) + x/2", "[0, 2*pi]", "sqrt(3)/2 + 5*pi/6", "pi"),
    ("Abs(cos(x)) + x/2", "[0, 2*pi]", "1 + pi", None),
    ("x - 2*Abs(sin(x))", "[0, 2*pi]", "2*pi", None),
    ("Abs(sin(x)) + cos(x)", "[0, 2*pi]", "sqrt(2)", "1"),
    ("Abs(sin(x)) - x/2", "[0, 2*pi]", "sqrt(3)/2 - pi/6", "0"),
    ("2*Abs(cos(x)) + x", "[0, pi]", "2 + pi", None),
    ("sin(x) + Abs(cos(x))", "[0, 2*pi]", "sqrt(2)", "1"),
    ("Abs(x - 1) + sin(x)", "[0, 3]", "2 + sin(3)", None),
    ("Abs(sin(x)) + Abs(cos(x))", "[0, pi]", "sqrt(2)", "1"),
    ("Abs(x) - cos(x)", "[-2, 2]", "2 - cos(2)", None),
    ("x*Abs(x - 2)", "[0, 3]", "3", None),
    ("Abs(x**2 - 2*x) + x", "[-1, 3]", "6", None),
    ("Max(sin(x), cos(x)) + x/4", "[0, 2*pi]", "1 + pi/2", None),
    ("x + Abs(sin(2*x))", "[0, pi]", "5*pi/6 + sqrt(3)/2", "pi"),
]


@pytest.mark.parametrize("f,interval,true_max,endpoint", ABS_TRIG)
def test_an_interior_maximum_of_an_abs_or_max_of_trig_is_found(f, interval, true_max, endpoint):
    """False acceptance and unjust refutation (SS-YO-1; son-kalkulus RK-EXT-1): SymPy's raw solveset of
    sign(sin x)*cos(x) + 1/2 raised, the interior critical points were lost (11 of the 14), and the larger endpoint
    value was certified the maximum while the true one was refuted (not_attained)."""
    # 13 CORRECT (6 were INCORRECT, 1 UNKNOWN in 0e93ed5); Max(sin x, cos x) + x/4 is UNKNOWN there and here, its
    # candidate set not called complete
    assert _ext(f, interval, "max", true_max) == ("UNKNOWN" if f.startswith("Max(") else "CORRECT")
    if endpoint is not None:
        assert _ext(f, interval, "max", endpoint) == "INCORRECT"


def test_an_endpoint_is_no_extremum_where_an_interior_point_beats_it():
    """False acceptance (SS-YO-1): x + 2*cos(x) with a coefficient written (2 + i)(2 - i)/5 (SymPy's raw solveset
    compared a number with an imaginary part of noise and raised): max 2, argmax 0, min pi - 2 were CORRECT; argmin 0
    of e^x + (1 + i*sqrt(3))**3*x/4 on [0, 2] too."""
    f = f"{K1}*x + 2*cos(x)"
    assert _ext(f, "[0, pi]", "max", "2") == "INCORRECT"
    assert _ext(f, "[0, pi]", "argmax", "0") == "INCORRECT"
    assert _ext(f, "[0, pi]", "min", "pi - 2") == "INCORRECT"
    assert _ext(f"exp(x) + {C3}*x/4", "[0, 2]", "argmin", "0") == "INCORRECT"
    assert _ext("Abs(sin(x)) + x/2", "[0, 2*pi]", "argmax", "2*pi") == "INCORRECT"


def test_the_true_interior_extremum_is_certified():
    """Unjust refutation (SS-YO-1): the true extrema were INCORRECT (not_attained) or, for the quadratic, lost."""
    f = f"{K1}*x + 2*cos(x)"
    assert _ext(f, "[0, pi]", "max", "pi/6 + sqrt(3)") == "CORRECT"
    assert _ext(f, "[0, pi]", "min", "5*pi/6 - sqrt(3)") == "CORRECT"
    assert _ext(f"exp(x) + {C3}*x/4", "[0, 2]", "argmin", "log(2)") == "CORRECT"
    assert _ext(f"x**2 + {C3}*x", "[-10, 10]", "min", "-16") == "CORRECT"
    assert _ext(f"-x**2 - {C3}*x", "[-10, 10]", "max", "16") == "CORRECT"


PLAIN = [
    ("x + 2*cos(x)", (0, sp.pi)), ("x - 2*sin(x)", (0, sp.pi)), ("x + 2*sin(x)", (0, 2 * sp.pi)),
    ("sin(x) + cos(x)", (0, 2 * sp.pi)), ("sin(x)*cos(x)", (0, sp.pi)), ("sin(x) + sqrt(3)*cos(x)", (0, sp.pi)),
    ("2*sin(x) + sin(2*x)", (0, 2 * sp.pi)), ("cos(x) + sin(x)**2", (0, sp.pi)), ("x - tan(x)", (-1, 1)),
    ("sin(x)/(2 + cos(x))", (0, 2 * sp.pi)), ("exp(x)*sin(x)", (0, sp.pi)), ("exp(-x)*cos(x)", (0, sp.pi)),
    ("x*sin(x) + cos(x)", (0, sp.pi)), ("sin(x)**3 + cos(x)**3", (0, sp.pi / 2)), ("x**3 - 3*x", (-3, 2)),
    ("x**4 - 4*x**3 + 4*x**2", (-1, 3)), ("x/(x**2 + 1)", (-3, 3)), ("x*log(x)", (sp.Rational(1, 10), 2)),
    ("sqrt(x)*(3 - x)", (0, 3)), ("x**(2/3)*(5 - x)", (0, 5)), ("Abs(x**2 - 4) - x", (-3, 3)),
    ("exp(x) - 2*x", (0, 2)), ("x - 2*log(x)", (1, 4)), ("cos(x)**2 - sin(x)", (0, sp.pi)),
    ("sin(2*x) + 2*cos(x)", (0, sp.pi)), ("3*sin(x) - 4*cos(x)", (0, 2 * sp.pi)), ("x + cos(2*x)", (0, sp.pi)),
    ("2*x - tan(x)", (0, sp.pi / 3)), ("sin(x) - x*cos(x)", (0, sp.pi)), ("x - sin(2*x)", (0, sp.pi)),
    ("x**2 - 2*cos(x)", (-2, 2)), ("x*exp(-x**2)", (-2, 2)), ("log(x**2 + 1) - x", (-2, 2)),
    ("cos(x) + cos(2*x)", (0, sp.pi)), ("x - 2*atan(x)", (0, 3)),
    ("Abs(sin(x)) + x/2", (0, 2 * sp.pi)), ("Abs(sin(2*x)) + x", (0, sp.pi)), ("Max(sin(x), cos(x)) + x/4", (0, 2 * sp.pi)),
]


def test_critical_points_are_the_complete_set_or_none():
    """Mechanism (SS-YO-1): `ops.critical_points` is the guarded solver's zero set of the classical f' (the set the
    certificate calls complete) with the singular points, or None; never a raw solveset's empty or partial list. The
    auditors' 36 plain functions and the Abs/Max family: wherever the complete set is found, every point of it is a
    candidate."""
    from mathverify.certify.calculus import classical
    from mathverify.sandbox import ops
    from mathverify.sandbox.exactsets import exact_solveset
    for text, (a, b) in PLAIN:
        f = sp.sympify(text, locals={"x": x})
        iv = sp.Interval(a, b)
        cps = ops.critical_points(f, x, iv)
        rd = exact_solveset(classical(sp.diff(f, x)), x, iv)
        if isinstance(rd, sp.FiniteSet) or rd is sp.S.EmptySet:
            assert cps is not None and set(rd) <= set(cps), (text, cps, rd)
        else:
            assert cps is None, (text, cps)
    assert set(ops.critical_points(A_(S_(x)) + x / 2, x, sp.Interval(0, 2 * sp.pi))) == {2 * sp.pi / 3, 5 * sp.pi / 3}
    assert ops.critical_points(x**2 / 2 + C_(x), x, sp.Interval(-1, 2)) is None       # x = sin(x): not solved


def test_critical_points_report_a_failure_as_none(monkeypatch):
    """Mechanism (SS-YO-1): a solver that raises is a failure (None), not an empty list."""
    import sys
    from mathverify.sandbox import ops
    sing = sys.modules["sympy.calculus.singularities"]        # the attribute of sympy.calculus is the function

    def raising(*a, **k):
        raise NotImplementedError("no singularities here")
    monkeypatch.setattr(sing, "singularities", raising)
    assert ops.critical_points(x + 2 * C_(x), x, sp.Interval(0, sp.pi)) is None


def test_a_failed_candidate_search_is_never_complete(monkeypatch):
    """Mechanism (SS-YO-1): critical points not found whole (None) leave the candidate set incomplete: the endpoints
    alone, called complete, certified the endpoint value 2 the maximum of x + 2*cos(x) on [0, pi]."""
    from mathverify.certify import extremum
    from mathverify.sandbox.pool import CasResult
    real = extremum.sb_run

    def run(fn, *a, **k):
        return CasResult(ok=True, value=None) if fn.endswith(":critical_points") else real(fn, *a, **k)
    monkeypatch.setattr(extremum, "sb_run", run)
    ok, ev = extremum.certify_extremum(x + 2 * C_(x), x, sp.Interval(0, sp.pi), "max", sp.Integer(2))
    assert ok is not True and ev["complete_candidates"] is False


def test_a_point_of_undecided_realness_leaves_the_list_incomplete(monkeypatch):
    """Mechanism (SS-YO-1): a kink or critical point whose realness SymPy does not decide is not dropped from a
    complete list (`p.is_real` filtered it, and the list stayed complete)."""
    from mathverify.certify import extremum
    from mathverify.sandbox.pool import CasResult
    undecided = sp.sqrt(sp.log(8) / sp.log(2) - 3)        # exactly 0; its realness is not decided
    assert undecided.is_real is None
    monkeypatch.setattr(extremum, "sb_run", lambda *a, **k: CasResult(ok=True, value=sp.FiniteSet(1, undecided)))
    pts, complete = extremum._kinks(A_(x - 1), x, sp.Interval(-2, 2), 5.0)
    assert complete is False and 1 in pts
    ok, ev = extremum.certify_local_extremum(x**2, x, sp.Interval(-2, 2), "local_min", "0")
    assert ok is None and ev["reason"] in ("critical_point_realness_undecided", "critical_points_failed")


# --- second round of the arg readings: RK-SAY-1, RK-ARG-STEP, RK-SAY-2, RK-SAY-3 ----------------------------------

def _run(ir, claim, steps=(), option=None):
    ca = {"kind": "value", "payload": claim}
    if option:
        ca["option"] = option
    r = verify(ir, {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                                                   for i, (k, c) in enumerate(steps)]})
    layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
    sts = [e.get("status") for e in (layer.evidence.get("steps", []) if layer is not None else [])]
    return r.verdict, sts, r.first_bad_step, r.flags


def _evc(expr, options=None):
    d = {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": [], "givens": [], "answer_shape": "scalar",
         "domain_of_discourse": "complex"}
    if options:
        d["options"] = options
    return d


def _pointwise(kind, f, pt):
    key, pk = ("f", "at") if kind == "derivative" else ("expr", "to")
    return {"task": {"kind": kind, "params": {key: f, "var": "x", pk: pt}}, "vars": [X], "givens": [],
            "answer_shape": "scalar" if kind == "derivative" else "dne_or_scalar"}


def test_a_pointwise_task_reads_the_shift_of_arg_at_its_point():
    """Coverage (RK-SAY-1): the derivative and the limit of arg(a + x*i) at a point off the axis are the same in both
    readings (the 2*pi shift is constant near the point) and were UNKNOWN; a wrong value is refuted again."""
    assert _run(_pointwise("derivative", "arg(1 + x*I)", "1"), "1/2")[0] == "CORRECT"
    assert _run(_pointwise("derivative", "arg(1 + x*I)", "-1"), "1/2")[0] == "CORRECT"
    assert _run(_pointwise("derivative", "arg(2 + x*I)", "2"), "1/4")[0] == "CORRECT"
    assert _run(_pointwise("limit", "arg(1 + x*I)", "1"), "pi/4")[0] == "CORRECT"
    assert _run(_pointwise("derivative", "arg(1 + x*I)", "1"), "1")[0] == "INCORRECT"
    assert _run(_pointwise("limit", "arg(1 + x*I)", "1"), "pi/2")[0] == "INCORRECT"
    # below the axis the value itself is the convention's; on it a reading decides nothing (not a convention)
    assert _run(_pointwise("limit", "arg(1 + x*I)", "-1"), "7*pi/4")[0] == "UNKNOWN"
    r = _run(_pointwise("derivative", "arg(1 + x*I)", "0"), "1")
    assert r[0] == "UNKNOWN" and "arg_reading_undecided" in r[3] and "arg_convention" not in r[3]


def test_a_step_refuted_in_one_arg_reading_only_is_unknown():
    """Unjust refutation (RK-ARG-STEP): with the answer wrong in both readings, the curriculum's step
    arg(-1 - i) = 5*pi/4 was shown refuted and the first bad step; it is unknown, the first bad step is the one
    refuted in both."""
    v, sts, fbs, _ = _run(_evc("(-1 - I)**4"), "4", [("eq", "arg(-1 - I) = 5*pi/4"), ("eq", "(-1 - I)**4 = 4")])
    assert (v, sts, fbs) == ("INCORRECT", ["unknown", "refuted"], 2)


def test_two_incorrect_readings_agree_only_on_a_failure_of_both():
    """Unjust refutation (RK-SAY-2): the principal value reached by a step and shifted by 2*pi to the answer was
    INCORRECT in both readings, each time on the other reading's arg alone; a value wrong in both stays INCORRECT."""
    steps = [("eq", "arg(-1 - I) = -3*pi/4"), ("eq", "-3*pi/4 + 2*pi = 5*pi/4")]
    assert _run(_evc("arg(-1 - I)"), "5*pi/4", steps)[0] == "UNKNOWN"
    steps = [("eq", "arg(-1 - I) = 5*pi/4"), ("eq", "5*pi/4 - 2*pi = -3*pi/4")]
    assert _run(_evc("arg(-1 - I)"), "-3*pi/4", steps)[0] == "UNKNOWN"
    assert _run(_evc("arg(1 - I)"), "7*pi/4", [("eq", "arg(1 - I) = -pi/4")])[0] == "UNKNOWN"
    assert _run(_evc("arg(-1 - I)"), "pi/4")[0] == "INCORRECT"
    assert _run(_evc("arg(-1 - I)"), "pi/4", [("eq", "arg(-1 - I) = -3*pi/4")])[:2] == ("INCORRECT", ["unknown"])


O02 = {"A": "pi/4", "B": "3*pi/4", "C": "5*pi/4", "D": "7*pi/4", "E": "3*pi/2"}
OPP = {"A": "-3*pi/4", "B": "-pi/4", "C": "pi/4", "D": "3*pi/4", "E": "pi"}


def test_options_of_one_range_declare_it():
    """Coverage and unjust refutation (RK-SAY-3): the options hold the value of one reading only: the question's
    range. The right option was UNKNOWN (or INCORRECT before the two readings); a wrong one stays INCORRECT."""
    assert _run(_evc("arg(-1 - I)", O02), "5*pi/4", option="C")[0] == "CORRECT"
    assert _run(_evc("arg(-1 - I)", O02), "pi/4", option="A")[0] == "INCORRECT"
    assert _run(_evc("arg(-1 - I)", OPP), "-3*pi/4", option="A")[0] == "CORRECT"
    assert _run(_evc("arg(-1 - I)", OPP), "pi/4", option="C")[0] == "INCORRECT"
    o5 = {"A": "pi/3", "B": "2*pi/3", "C": "4*pi/3", "D": "5*pi/3", "E": "pi/6"}
    assert _run(_evc("arg(1 - sqrt(3)*I)", o5), "5*pi/3", option="D")[0] == "CORRECT"


def test_options_that_do_not_pick_a_range_leave_the_convention():
    """No range from the options: both values among them, an option that is no number, degrees (G1RK-3's units)."""
    both = {"A": "-3*pi/4", "B": "5*pi/4", "C": "pi/4", "D": "3*pi/4", "E": "pi"}
    assert _run(_evc("arg(-1 - I)", both), "5*pi/4", option="B")[0] == "UNKNOWN"
    assert _run(_evc("arg(-1 - I)", both), "-3*pi/4", option="A")[0] == "UNKNOWN"
    none_ = dict(O02, E="Hiçbiri")
    assert _run(_evc("arg(-1 - I)", none_), "5*pi/4", option="C")[0] == "UNKNOWN"
    deg = {"A": "45°", "B": "135°", "C": "225°", "D": "315°", "E": "270°"}
    assert _run(_evc("arg(-1 - I)", deg), "225°", option="C")[0] != "CORRECT"


def test_the_options_reading_of_arg():
    """Mechanism (RK-SAY-3): `_arg_options_reading` names the reading whose value alone the options hold."""
    from mathverify.verifier import _arg_options_reading
    assert _arg_options_reading(_evc("arg(-1 - I)", O02)) == "b"
    assert _arg_options_reading(_evc("arg(-1 - I)", OPP)) == "a"
    assert _arg_options_reading(_evc("arg(1 + I)", O02)) is None              # pi/4 in both readings
    assert _arg_options_reading(_evc("arg(-1 - I)")) is None


# --- third round: a convention step, an oversized option, the point at infinity and a pinned parameter -----------

PRINCIPAL_STEPS = [("eq", "Abs(1 - I) = sqrt(2)"), ("eq", "arg(1 - I) = -pi/4"),
                   ("eq", "(1 - I)**10 = 32*(cos(-5*pi/2) + I*sin(-5*pi/2))")]


def test_a_principal_value_step_is_no_refutation_in_any_reading():
    """Coverage (SS2-RK-1): a De Moivre solution writes the principal arg(1 - i) = -pi/4, refuted in the [0, 2*pi)
    reading by no counterexample of its own: the right (1 - i)**10 = -32*i was UNKNOWN. The step is unknown in every
    reading; the answer's certificate decides, and the wrong 32*i stays INCORRECT."""
    v, sts, fbs, _ = _run(_evc("(1 - I)**10"), "-32*I", PRINCIPAL_STEPS)
    assert (v, sts, fbs) == ("CORRECT", ["verified", "unknown", "verified"], None)
    v, sts, fbs, _ = _run(_evc("(1 - I)**10"), "32*I", PRINCIPAL_STEPS)
    assert (v, sts, fbs) == ("INCORRECT", ["verified", "unknown", "verified"], None)
    st6 = [("eq", "arg(sqrt(3) - I) = -pi/6"), ("eq", "2**6*(cos(-pi) + I*sin(-pi)) = -64")]
    assert _run(_evc("(sqrt(3) - I)**6"), "-64", st6)[0] == "CORRECT"
    assert _run(_evc("(sqrt(3) - I)**6"), "64", st6)[0] == "INCORRECT"


def test_a_declared_range_does_not_refute_the_principal_step():
    """Unjust refutation (SS2-RK-2): with [0, 2*pi) options the principal value plus 2*pi, the right option D, was
    INCORRECT, its first bad step the true principal value; a step wrong in both readings is still the first bad
    one, and a wrong option stays INCORRECT."""
    o = {"A": "pi/4", "B": "3*pi/4", "C": "5*pi/4", "D": "7*pi/4", "E": "3*pi/2"}
    steps = [("eq", "arg(1 - I) = -pi/4"), ("eq", "-pi/4 + 2*pi = 7*pi/4")]
    assert _run(_evc("arg(1 - I)", o), "7*pi/4", steps, option="D")[:3] == ("CORRECT", ["unknown", "verified"], None)
    steps = [("eq", "arg(1 - I) = -pi/4"), ("eq", "-pi/4 + 2*pi = 3")]
    assert _run(_evc("arg(1 - I)", o), "7*pi/4", steps, option="D")[:3] == ("INCORRECT", ["unknown", "refuted"], 2)
    o2 = {"A": "pi/6", "B": "5*pi/6", "C": "7*pi/6", "D": "11*pi/6", "E": "3*pi/2"}
    assert _run(_evc("arg(sqrt(3) - I)", o2), "5*pi/6", [("eq", "arg(sqrt(3) - I) = -pi/6")], option="B")[0] == \
        "INCORRECT"


def test_an_oversized_option_reads_no_range_within_the_budget():
    """Time (SS2-CR-1): the options were read in this process with no time limit, and an option 10**10**10 held the
    verifier past 60 s; read in the sandbox, past its limit no range comes from the options."""
    import time
    o = {"A": "pi/4", "B": "3*pi/4", "C": "5*pi/4", "D": "7*pi/4", "E": "10**10**10"}
    t = time.time()
    v = _run(_evc("arg(-1 - I)", o), "5*pi/4", option="C")[0]
    assert time.time() - t < 40 and v != "INCORRECT"


def test_the_shift_of_arg_is_read_at_infinity_and_at_a_pinned_parameter():
    """Coverage (SS2-RK-3): the limit at oo of arg(1 + x*i) and the derivative of arg(1 + a*x*i) with a = 2 are the
    same in both readings (no shift where the imaginary part is eventually or locally positive) and were UNKNOWN;
    at -oo the shift is 2*pi and the value is the convention's."""
    xa = [X, {"name": "a", "domain": "real"}]

    def lim(f, to, givens=(), vars_=(X,)):
        return {"task": {"kind": "limit", "params": {"expr": f, "var": "x", "to": to}}, "vars": list(vars_),
                "givens": list(givens), "answer_shape": "dne_or_scalar"}

    def der(f, at, givens=(), vars_=(X,)):
        return {"task": {"kind": "derivative", "params": {"f": f, "var": "x", "at": at}}, "vars": list(vars_),
                "givens": list(givens), "answer_shape": "scalar"}
    assert _run(lim("arg(1 + x*I)", "oo"), "pi/2")[0] == "CORRECT"
    assert _run(lim("arg(1 + x*I)", "oo"), "0")[0] == "INCORRECT"
    assert _run(lim("arg(2 + x*I)", "oo"), "pi/2")[0] == "CORRECT"
    assert _run(lim("arg(1 + x*I)", "-oo"), "-pi/2")[0] == "UNKNOWN"
    assert _run(der("arg(1 + a*x*I)", "1", ["a = 2"], xa), "2/5")[0] == "CORRECT"
    assert _run(der("arg(1 + a*x*I)", "1", ["a = 2"], xa), "1/5")[0] == "INCORRECT"
    assert _run(lim("arg(a + x*I)", "1", ["a = 1"], xa), "pi/4")[0] == "CORRECT"
