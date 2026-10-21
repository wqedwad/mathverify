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
