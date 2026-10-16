"""Fourth audit, part d4j ("the rest", 15 Oct 2026, plan A+, DECISIONS §89): the findings no branch had fixed
(`denetim/2026-10-01/d4/a_arti/kararlar_kalan.txt`; the d4f round 2 findings in `d4/saldiri/d4f2/bulgular.json` with the
decisions of `kararlar_tur3.txt`; CAP-K1 in `d4/kararlar_fhi.txt`). Each assertion failed on 5e88d41 unless it is
marked as a control.

Realistic: RK-1 (a bare name of a list parameter is a label), RK-2 (a sequence's tail proved by the limit of a
condition), ONCEKI-1 (an option read as a claim of the answer's shape; a decimal comma not guessed).
Artificial, narrow fail-closed rules: A-YO-1 (0**0 entries), A-YO-2 (an exponent identically 0), A-YO-3 (ℂ keeps the
operations with no value and the conventions), A-YO-4 (guard), A-YO-5 (a closed infinite argument), A-RK-1 (a bound
that is no linear one), B-YO-1/RK-3 (log bounds), D4B9-E2-R1 (atan2's branch cut), GAP-NE (a Float's tolerant
equality), GAP-LFLOOR (a claim applying the target's own operation), CAP-K1 (the fusion's abstention kinds).
"""
import ast
import pathlib
from fractions import Fraction
from itertools import combinations, permutations, product

import pytest
import sympy as sp

from mathverify.certify.base import result, unknown
from mathverify.fuse import fuse
from mathverify.fuse import rules
from mathverify.verifier import fuse_layers, verify

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
K = {"name": "k", "domain": "integer"}
NR = {"name": "n", "domain": "real"}
NI = {"name": "n", "domain": "integer"}
NP = {"name": "n", "domain": "positive_integer"}


def _ir(kind, params, givens=(), vars_=None, shape="scalar", **extra):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    d.update(extra)
    return d


def _sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": "compute", "claim": c, "from": [], "text": ""}
                                            for i, c in enumerate(steps)]}


def _v(q, s):
    return verify(q, s).verdict


def _ev(expr, vars_=None, givens=(), **extra):
    return _ir("evaluate", {"expr": expr}, givens, vars_, **extra)


def _step_status(claim, vars_=None):
    r = verify(_ev("x", vars_, ("x = 1",)), _sol("1", steps=[claim]))
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    st = layer.evidence["steps"][-1]
    return r.verdict, st.get("status"), (st.get("evidence") or {}).get("reason") or st.get("reason")


# RK-1: labels ---------------------------------------------------------------------------------------------------
def _geo(pts, claim="10"):
    a, b, c = pts
    return _ir("synthetic_geometry", {"points": list(pts), "constraints": [f"dist({a},{b}) = 6", f"dist({b},{c}) = 8",
                                                                          f"angle({a},{b},{c}) = 90"],
                                      "target": f"dist({a},{c})"}, vars_=[]), _sol(claim)


def _prob(st, el, k, event, shift=0):
    space = {"sequence": lambda: list(product(el, repeat=k)), "permutation": lambda: list(permutations(el, k)),
             "combination": lambda: list(combinations(el, k))}[st]()
    p = Fraction(sum(1 for t in space if eval(event, {"t": t})), len(space)) + shift
    return _ir("probability", {"space": {"structure": st, "elements": el, "k": k}, "event": event}, vars_=[]), _sol(str(p))


@pytest.mark.parametrize("pts", [("P", "Q", "R"), ("A", "B", "S"), ("P", "Q", "S")])
def test_rk1_point_names_are_labels(pts):
    # PQ = 6, QR = 8, ∠PQR = 90°: PR = 10; P is the permutation count, S SymPy's registry in the namespace
    assert _v(*_geo(pts)) == "CORRECT"
    assert _v(*_geo(pts, "11")) == "INCORRECT"


@pytest.mark.parametrize("args", [("combination", ["S", "K", "M", "B", "Y"], 2, "'S' in t"),
                                  ("sequence", ["S", "K"], 3, "'S' in t"), ("sequence", ["P", "Q"], 2, "t[0] == t[1]"),
                                  ("permutation", ["P", "R", "S", "T"], 4, "t[0] == 'S'"),
                                  ("combination", ["sqrt", "det", "Sum", "gcd"], 2, "'det' in t")])
def test_rk1_outcome_names_are_labels(args):
    # 2/5, 7/8, 1/2, 1/4, 1/2 (itertools)
    assert _v(*_prob(*args)) == "CORRECT"
    assert _v(*_prob(*args, shift=1)) == "INCORRECT"


def test_rk1_count_of_permutations_of_labels():
    q = _ir("count_structures", {"space": {"structure": "permutation", "elements": ["P", "R", "S", "T", "U"], "k": 3},
                                 "predicate": "True"}, vars_=[], shape="count")
    assert _v(q, _sol(60, kind="count")) == "CORRECT"            # P(5, 3)
    assert _v(q, _sol(61, kind="count")) == "INCORRECT"


def test_rk1_control_a_name_with_a_value_is_no_label():
    # zoo among the outcomes has no value: the problem stays undefined as written (review of d4f, YO-6)
    q, s = _prob("combination", ["S", "zoo", "K"], 2, "'S' in t")
    assert _v(q, s) == "UNKNOWN"


# RK-2: tails ----------------------------------------------------------------------------------------------------
def _lim(expr, val, var="n"):
    return _ir("limit", {"expr": expr, "var": var, "to": "oo"}, (), [{"name": var, "domain": "positive_integer"}]), \
        _sol(val)


@pytest.mark.parametrize("expr,val", [("1/(2**n - 1000)", "0"), ("1/(3**n - 7)", "0"), ("1/(factorial(n) - 100)", "0"),
                                      ("n**2/(n**2 - 2**n)", "0"), ("1/(n - 10*log(n))", "0"),
                                      ("log(n)/(n - log(n))", "0"), ("1/floor(n/2)", "0"), ("n/floor(n/2)", "2"),
                                      ("(3**n + 2**n)/(3**n - 5)", "1"), ("n**2/(n**2 - n*log(n))", "1"),
                                      ("1/(1 - 1/factorial(n))", "1")])
def test_rk2_textbook_sequence_limits(expr, val):
    # each condition's violation set is bounded (2**n = 1000 at log2(1000) only, n**2 = 2**n at 2, 4 and one
    # negative point, n - log n > 0 for n > 0, floor(n/2) = 0 on [0, 2), 1 - 1/n! = 0 at n <= 1)
    assert _v(*_lim(expr, val)) == "CORRECT"


def test_rk2_wrong_limits_refuted_and_variable_x():
    assert _v(*_lim("1/(2**n - 1000)", "1")) == "INCORRECT"
    assert _v(*_lim("n/floor(n/2)", "1")) == "INCORRECT"
    assert _v(*_lim("x/(2**x - 1000)", "0", var="x")) == "CORRECT"


@pytest.mark.parametrize("expr,val", [("cos(pi*n/2)/cos(pi*n/2)", "1"), ("1/(1 - (-1)**n)", "0"),
                                      ("(1 - (-1)**n)/(1 - (-1)**n)", "1")])
def test_rk2_control_infinitely_many_bad_indices_stay_unknown(expr, val):
    assert _v(*_lim(expr, val)) == "UNKNOWN"


@pytest.mark.parametrize("expr", ["sqrt(10*log(n) - n)", "sqrt(5 - n)", "log(5 - n)"])
def test_rk2_control_a_condition_failing_on_the_whole_tail(expr):
    # 10 log n - n >= 0 fails from n = 36 on, 5 - n from n = 6: no tail where the sequence has a value (the limit of
    # the condition is -oo, on the wrong side of 0)
    assert _v(*_lim(expr, "0")) == "UNKNOWN"


# ONCEKI-1: options ----------------------------------------------------------------------------------------------
def _ineq(given, opts, payload, opt, shape="interval", kind="interval"):
    return _ir("solve_inequality", {"var": "x"}, [given], [{"name": "x"}], shape, options=opts), \
        _sol(payload, kind, option=opt)


@pytest.mark.parametrize("given,option,payload", [("x**3 > -8", "x > -2", "(-2, oo)"), ("x**3 > -8", "x>-2", "(-2, oo)"),
                                                  ("2*x - 2 >= 0", "x ≥ 1", "[1, oo)"), ("x - 3 < 0", "x < 3", "(-oo, 3)"),
                                                  ("2*x - 2 >= 0", r"x \geq 1", "[1, oo)")])
def test_onceki1_relation_option_is_the_solution_set(given, option, payload):
    assert _v(*_ineq(given, {"A": option, "B": "(100, 200)"}, payload, "A")) == "CORRECT"


def test_onceki1_relation_option_set_shape_condition_claim_and_letter_only():
    assert _v(*_ineq("x**3 > -8", {"A": "x > -2", "B": "(100, 200)"}, "(-2, oo)", "A", shape="set")) == "CORRECT"
    assert _v(*_ineq("x**3 > -8", {"A": "x > -2", "B": "(100, 200)"}, "x > -2", "A", kind="condition")) == "CORRECT"
    assert _v(*_ineq("x**3 > -8", {"A": "x > -2", "B": "(100, 200)"}, "", "A")) == "CORRECT"
    assert _v(*_ineq("x**3 > -8", {"A": "x > 2", "B": "x > -2"}, "", "A")) == "INCORRECT"
    assert _v(*_ineq("x**3 > -8", {"A": "x > 2", "B": "(100, 200)"}, "(-2, oo)", "A")) == "INCORRECT"


@pytest.mark.parametrize("payload", ["3/2", ""])
def test_onceki1_decimal_comma_option_is_not_guessed(payload):
    r = verify(_ev("3/2 + 0", [], options={"A": "1,5", "B": "7"}), _sol(payload, option="A"))
    assert r.verdict == "UNKNOWN"
    assert "decimal_comma_ambiguous" in {f for la in r.layers for f in la.flags}


@pytest.mark.parametrize("q,s", [
    (_ev("1 + 2", [], options={"A": "(1, 5)", "B": "3"}), _sol("3", option="A")),
    _ineq("x**2 < 4", {"A": "x**2 < 4", "B": "(100, 200)"}, "(-2, 2)", "A")])
def test_onceki1_an_option_of_another_kind_abstains(q, s):
    # a pair for a number, the question's own inequality for a set: what the letter names is not read
    r = verify(q, s)
    assert r.verdict == "UNKNOWN" and "option_unreadable" in r.flags


def test_onceki1_control_a_condition_on_another_symbol_is_not_the_answer_set():
    q = _ir("solve_inequality", {"var": "x"}, ["x**3 > -8"], [{"name": "x"}, {"name": "y"}], "interval",
            options={"A": "y > -2", "B": "(100, 200)"})
    # a condition on y names no set of x: the option is not read as the answer's kind, and abstains
    assert _v(q, _sol("(-2, oo)", "interval", option="A")) == "UNKNOWN"


def test_onceki1_control_a_value_claim_against_a_set_answer_option():
    # evalset ayt-trig-004: a set answer, the claim pi/3 as a value, the option read as {pi/3}: the same kind (a first
    # reading of "another kind" made it UNKNOWN; measured by the verdict diff)
    q = _ir("trig_solve", {"var": "x", "interval": "[0, pi)"}, ["tan(x) = sqrt(3)"], [{"name": "x"}], "set",
            options={"A": "pi/6", "B": "pi/3", "C": "2*pi/3"})
    assert _v(q, _sol("pi/3", option="B")) == "CORRECT"


def test_onceki1_controls():
    assert _v(_ev("3/2 + 0", [], options={"A": "1.5", "B": "7"}), _sol("3/2", option="A")) == "CORRECT"
    assert _v(_ev("1 + 2", [], options={"A": "7", "B": "3"}), _sol("3", option="A")) == "INCORRECT"
    assert _v(*_ineq("x**2 < 1", {"A": "-1 < x < 1", "B": "(100, 200)"}, "(-1, 1)", "A")) == "CORRECT"
    assert _v(*_ineq("x**3 > -8", {"A": "-2 < x", "B": "(100, 200)"}, "(-2, oo)", "A")) == "CORRECT"


# A-YO-1: a 0**0 entry -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("expr,val", [("det(Matrix([[0**0, 0], [0, 1]]))", "1"), ("trace(Matrix([[0**0, 0], [0, 0]]))", "1"),
                                      ("trace(Matrix([[(2 - 2)**0, 1], [1, 1]]))", "2"),
                                      ("det(Matrix([[1/0**0, 0], [0, 1]]))", "1"),
                                      (r"\det\begin{pmatrix} 0^0 & 0 \\ 0 & 1 \end{pmatrix}", "1")])
def test_a_yo1_zero_power_entry_is_a_convention(expr, val):
    assert _v(_ev(expr), _sol(val)) == "UNKNOWN"


def test_a_yo1_step_and_controls():
    assert _step_status("trace(Matrix([[0**0, 0], [0, 0]])) = 1")[1] != "verified"
    assert _v(_ev("det(Matrix([[2**0, 1], [1, 2]]))"), _sol("1")) == "CORRECT"
    assert _v(_ev("det(Matrix([[1/2, 1], [1, 4]]))"), _sol("1")) == "CORRECT"
    assert _v(_ev("det(Matrix([[1/2, 1], [1, 4]]))"), _sol("2")) == "INCORRECT"


# A-YO-2: an exponent identically 0 ------------------------------------------------------------------------------
@pytest.mark.parametrize("expr", ["oo**(x - x)", "(-oo)**(x - x)", "oo**(floor(x) - floor(x))", "0**(x - x)",
                                  "0**(sin(x)**2 + cos(x)**2 - 1)", "(oo*x)**0", "(oo*x)**(x - x)"])
def test_a_yo2_zero_exponent_on_zero_or_infinity(expr):
    assert _v(_ev(expr), _sol("1")) == "UNKNOWN"


@pytest.mark.parametrize("expr", ["x**(x - x)", "2**(x - x)", "2**(sin(x)**2 + cos(x)**2 - 1)"])
def test_a_yo2_control_other_bases(expr):
    assert _v(_ev(expr), _sol("1")) == "CORRECT"


# A-YO-3: ℂ ------------------------------------------------------------------------------------------------------
def _evc(expr):
    return _ev(expr, [], domain_of_discourse="complex")


@pytest.mark.parametrize("expr,val", [("1/factorial(-1)", "0"), (r"\frac{1}{\Gamma(0)}", "0"), ("1/(1/0)", "0"),
                                      ("0**0", "1"), ("oo**0", "1"), ("Mod(7, -5)", "-3"), ("sqrt(-4) + 0**0", "2*I + 1")])
def test_a_yo3_complex_keeps_no_value_and_conventions(expr, val):
    assert _v(_evc(expr), _sol(val)) == "UNKNOWN"


def test_a_yo3_control_principal_values():
    assert _v(_evc("sqrt(-4)"), _sol("2*I")) == "CORRECT"
    assert _v(_evc("sqrt(-4)"), _sol("-2*I")) == "INCORRECT"
    assert _v(_evc("log(-1)"), _sol("I*pi")) == "CORRECT"
    assert _v(_evc("asin(2) - asin(2) + 1"), _sol("1")) == "CORRECT"


# A-YO-4 (closed on the merged branch; guards) -------------------------------------------------------------------
@pytest.mark.parametrize("c", ["x > sqrt(-1)**2", "x > log(-1)*0", "x > asin(2)*0"])
def test_a_yo4_guard_closed_undefined_constraint(c):
    q = _ir("solve_equation", {"var": "x", "equation": "x**2 = 1"}, (), [{"name": "x", "domain": "real",
                                                                         "constraints": [c]}], "set")
    assert _v(q, _sol("{1}", "set")) == "UNKNOWN"


@pytest.mark.parametrize("c,ok,wrong", [("x/x > 0", "{-1, 1}", "{-1, 0, 1}"), ("sqrt(x)**2 >= -1", "{0, 1}", "{-1, 0, 1}"),
                                        ("log(x) - log(x) >= 0", "{1}", "{-1, 1}")])
def test_a_yo4_guard_constraint_written_definedness(c, ok, wrong):
    q = _ir("solve_equation", {"var": "x", "equation": "x**3 = x"}, (), [{"name": "x", "domain": "real",
                                                                         "constraints": [c]}], "set")
    assert _v(q, _sol(ok, "set")) == "CORRECT"
    assert _v(q, _sol(wrong, "set")) == "INCORRECT"


# A-YO-5: a closed infinite argument -----------------------------------------------------------------------------
@pytest.mark.parametrize("expr,val", [("0*sin(oo)", "0"), ("0*frac(oo)", "0"), ("2**(-oo)", "0"), ("exp(-oo)", "0"),
                                      ("atan(oo)", "pi/2"), ("tanh(oo)", "1"), ("E**(-oo)", "0"), ("(1/2)**oo", "0")])
def test_a_yo5_infinite_argument_has_no_value(expr, val):
    assert _v(_ev(expr), _sol(val)) == "UNKNOWN"


def test_a_yo5_step_and_limits_untouched():
    assert _step_status("0*sin(oo) = 0")[1] != "verified"
    for expr, val in [("exp(-x)", "0"), ("atan(x)", "pi/2"), ("sin(x)/x", "0")]:
        assert _v(_ir("limit", {"expr": expr, "var": "x", "to": "oo"}), _sol(val)) == "CORRECT"
    assert _v(_ir("limit", {"expr": "exp(-x)", "var": "x", "to": "oo"}), _sol("1")) == "INCORRECT"
    assert _v(_ir("series_sum", {"var": "k", "lo": "0", "hi": "oo", "term": "(1/2)**k"}, (), [K]), _sol("2")) == "CORRECT"


# A-RK-1: a bound that is no linear one --------------------------------------------------------------------------
def test_a_rk1_nonlinear_bound_is_never_refuted_off_the_integers():
    q = _ev("Sum(k, (k, n**2, n**2 + 2))", [NR, K])
    assert _v(q, _sol("3*n**2 + 3 + sin(pi*n**2)")) == "UNKNOWN"
    assert _v(_ev("Sum(k, (k, sqrt(n), sqrt(n) + 2))", [NP, K]), _sol("3*sqrt(n) + 3 + sin(pi*sqrt(n))")) == "UNKNOWN"


def test_a_rk1_integer_valued_bound_of_an_integer():
    # n**2 and n(n + 1)/2 are integers at every integer n: no convention there (B-RK-4's reading)
    assert _v(_ev("Sum(k, (k, n**2, n**2 + 2))", [NI, K]), _sol("3*n**2 + 3")) == "CORRECT"
    assert _v(_ev("Sum(k, (k, n**2, n**2 + 2))", [NI, K]), _sol("3*n**2 + 4")) == "INCORRECT"
    q = _ev("Sum(k, (k, 1, n*(n + 1)/2))", [NP, K])
    assert _v(q, _sol("n*(n + 1)*(n**2 + n + 2)/8")) == "CORRECT"
    assert _v(q, _sol("n*(n + 1)*(n**2 + n + 2)/8 + 1")) == "INCORRECT"
    assert _v(_ev("Sum(k, (k, 1, n/2))", [NP, K]), _sol("n*(n + 2)/8")) == "UNKNOWN"      # n/2: a convention


# B-YO-1 / RK-3: log bounds --------------------------------------------------------------------------------------
@pytest.mark.parametrize("bound,m", [(r"\frac{\ln 8}{\ln 2}", 3), (r"\log_{3} 3^{4}", 4)])
def test_rk3_log_bounds_read_as_written(bound, m):
    e = r"\sum_{k=1}^{%s} k" % bound
    v = m * (m + 1) // 2
    assert _v(_ev(e), _sol(str(v))) == "CORRECT"
    assert _v(_ev(e), _sol(str(v + 1))) == "INCORRECT"
    assert _step_status(f"{e} = {v}")[1] == "verified"


def test_rk3_wrong_step_with_a_log_bound_refuted():
    r = verify(_ev("Sum(k, (k, 1, 3))", [K]), _sol("6", steps=[r"\sum_{k=1}^{\frac{\ln 8}{\ln 2}} k = 7"]))
    assert (r.verdict, r.first_bad_step) == ("INCORRECT", 1)


def test_rk3_an_unread_step_is_not_called_undefined():
    # the as-written reading does not take Range: the step is not read, not undefined
    assert _step_status("Range(1, 4) = Range(1, 4)")[2] == "claim_not_read_as_written"


# D4B9-E2-R1: atan2 / arg ----------------------------------------------------------------------------------------
def _der(f, at=None, var="x", vars_=None, givens=(), shape="expression"):
    p = {"f": f, "var": var}
    if at is not None:
        p["at"] = at
    return _ir("derivative", p, givens, vars_, "scalar" if at is not None else shape)


@pytest.mark.parametrize("f,claim", [("atan2(x, -1)", "-1/(x**2 + 1)"), ("atan2(x - 1, -2)", "-2/((x - 1)**2 + 4)"),
                                     ("arg(-1 + I*x)", "-1/(x**2 + 1)")])
def test_e2_r1_branch_cut_is_a_kink(f, claim):
    # atan2(x, -1) jumps from -π to π at x = 0: no derivative there, and the claim has a value there
    assert _v(_der(f), _sol(claim)) == "UNKNOWN"


def test_e2_r1_controls():
    assert _v(_der("atan2(x, -1)"), _sol("1/(x**2 + 1)")) == "INCORRECT"
    assert _v(_der("atan2(x, 1)"), _sol("1/(x**2 + 1)")) == "CORRECT"
    assert _v(_der("atan2(1, x)"), _sol("-1/(x**2 + 1)")) == "CORRECT"
    assert _v(_der("atan2(x**2 + 1, x)"), _sol("(x**2 - 1)/(x**4 + 3*x**2 + 1)")) == "CORRECT"
    assert _v(_der("atan2(x, -1)", "1"), _sol("-1/2")) == "CORRECT"


# GAP-NE: a Float's tolerant equality ----------------------------------------------------------------------------
def test_gap_ne_tolerant_equality_decides_nothing():
    from mathverify.certify.domain import relation_holds_at
    x = sp.Symbol("x", real=True)
    F = sp.Float
    assert relation_holds_at(sp.Eq(x, 1), x, F("1.00000000000001")) is None
    assert relation_holds_at(sp.Ne(x, 1), x, F("1.00000000000001")) is None
    assert relation_holds_at(sp.Ge(x, sp.Rational(1, 3)), x, F("0.333333333333333")) is None
    assert relation_holds_at(sp.Lt(x, sp.Rational(1, 3)), x, F("0.333333333333333")) is None
    # controls: an exact zero difference, a difference beyond the precision, exact operands
    assert relation_holds_at(sp.Eq(2 * x, 1), x, F("0.5")) is True
    assert relation_holds_at(sp.Le(x, 1), x, F("1.0")) is True
    assert relation_holds_at(sp.Lt(x, 1), x, F("1.0")) is False
    assert relation_holds_at(sp.Ne(x, 1), x, F("1.5")) is True
    assert relation_holds_at(sp.Eq(x, 1), x, F("1.5")) is False
    assert relation_holds_at(sp.Ne(x, sp.Rational(1, 3)), x, sp.Rational(1, 3)) is False


# GAP-LFLOOR: the target's own operation in the claim ------------------------------------------------------------
@pytest.mark.parametrize("target,claim", [("floor(17/5)", r"\lfloor\frac{17}{5}\rfloor"),
                                          ("floor(17/5)", r"\lfloor\frac{18}{5}\rfloor"),
                                          ("ceiling(17/5)", r"\lceil\frac{17}{5}\rceil"), ("factorial(5)", "5!"),
                                          ("binomial(5, 2)", r"\binom{5}{2}"), ("Mod(17, 5)", "Mod(17, 5) + 0")])
def test_lfloor_claim_computing_the_target_operation(target, claim):
    r = verify(_ev(target, []), _sol(claim))
    assert r.verdict == "UNKNOWN" and "claim_is_not_a_value" in r.flags


def test_lfloor_controls():
    assert _v(_ev("floor(17/5)", []), _sol("3")) == "CORRECT"
    assert _v(_ev("floor(17/5)", []), _sol("4")) == "INCORRECT"
    assert _v(_ev("17/5 - 2/5", []), _sol(r"\lfloor\frac{17}{5}\rfloor")) == "CORRECT"   # the target has no floor
    assert _v(_ev("floor(x) + floor(x)"), _sol("2*floor(x)")) == "CORRECT"               # not closed: a value
    assert _v(_ev("sqrt(8)", []), _sol("2*sqrt(2)")) == "CORRECT"


# CAP-K1: the fusion ---------------------------------------------------------------------------------------------
_LEAN = result("formal.lean", "pass", 0.995, True, {"stand_in": True}, 0.0, primary=True, flags=["lean_proved"])


def _with_lean(q, s):
    return fuse_layers(list(verify(q, s).layers) + [_LEAN]).verdict


@pytest.mark.parametrize("q,s", [
    (_ev("integrate(x, (x, 0, a))", [{"name": "a"}, {"name": "x"}]), _sol("a**2/2", "expression")),
    (_der("x**2", "0", vars_=[{"name": "x", "domain": "positive_real"}]), _sol("0")),
    (_ir("series_sum", {"var": "k", "lo": "3", "hi": "1", "term": "k"}, (), [K]), _sol("-2")),
    (_ir("limit", {"expr": "factorial(x)", "var": "x", "to": "0"}, (), [{"name": "x"}]), _sol("1")),
    (_ir("limit", {"expr": "a*x/x", "var": "x", "to": "0"}, (), [{"name": "x"}, {"name": "a"}]), _sol("a"))])
def test_cap_k1_meaning_abstention_not_turned_correct_by_a_later_layer(q, s):
    assert _v(q, s) == "UNKNOWN"
    assert _with_lean(q, s) == "UNKNOWN"


@pytest.mark.parametrize("q,s", [
    (_ir("count_integers", {"var": "n"}, ["Mod(n, 3) = 0", "n >= 1", "n <= 9"], [NI], "count"), _sol(3, kind="count")),
    (_ir("recurrence_term", {"recurrence": "a(n) = (n - 5)**2", "initial": {"1": "1"}, "index": 3, "name": "a",
                             "var": "n"}, (), []), _sol("4")),
    (_ir("recurrence_term", {"recurrence": "a(n) = n - 5", "initial": {"1": "1"}, "index": 3, "name": "a", "var": "n"},
         (), []), _sol("-2"))])
def test_cap_k1_control_the_measured_lean_rescues_stay(q, s):
    assert _v(q, s) == "UNKNOWN"
    assert _with_lean(q, s) == "CORRECT"


# getattr: the file is also run on the code before the part, where the lists do not exist
_QUIET = sorted(getattr(rules, "_NOT_PROVEN_FLAGS", set()) | getattr(rules, "_NOTE_FLAGS", set()))


@pytest.mark.parametrize("flag", _QUIET)
def test_cap_k1_a_not_proved_abstention_or_a_note_does_not_block(flag):
    assert rules._meaning_blocks([flag], [_LEAN]) == []


@pytest.mark.parametrize("flag", sorted(getattr(rules, "_MEANING_FLAGS", set())) + ["a_flag_no_list_names"])
def test_cap_k1_a_meaning_or_unlisted_abstention_blocks(flag):
    assert rules._meaning_blocks([flag], [_LEAN]) == [flag]
    assert fuse([unknown("certify.algebra", "undecided", flags=[flag]), _LEAN])["verdict"] == "UNKNOWN"


def test_cap_k1_control_a_not_proved_abstention_and_a_later_pass():
    assert fuse([unknown("certify.counting", "solveset_failed", flags=["cas_failed"]), _LEAN])["verdict"] == "CORRECT"


def test_cap_k1_control_a_deterministic_certificate_is_not_blocked():
    det = result("certify.algebra", "pass", 0.99, True, {}, 0.0, primary=True)
    assert fuse([det, unknown("certify.wordproblem", "x", flags=["condition_not_applied"])])["verdict"] == "CORRECT"


def _emitted_flags() -> set[str]:
    """Every flag literal the code passes as `flags=[...]`, appends to a `*flags` list, or puts under a "flags" key."""
    out: set[str] = set()

    def strs(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return [s for e in node.elts for s in strs(e)]
        if isinstance(node, ast.IfExp):
            return strs(node.body) + strs(node.orelse)
        if isinstance(node, ast.BinOp):
            return strs(node.left) + strs(node.right)
        return []

    def flags_name(n):
        return (isinstance(n, ast.Name) and n.id.endswith("flags")) or (isinstance(n, ast.Attribute)
                                                                         and n.attr.endswith("flags"))
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "mathverify"
    for p in src.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "flags":
                        out.update(strs(kw.value))
                if isinstance(node.func, ast.Attribute) and node.func.attr in ("append", "extend", "add") \
                        and flags_name(node.func.value):
                    for a in node.args:
                        out.update(strs(a))
            elif isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(flags_name(t) for t in targets):
                    out.update(strs(node.value))
            elif isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
                for e in node.value.elts:
                    if isinstance(e, ast.BinOp) and flags_name(e.left):
                        out.update(strs(e.right))
    return out


def test_cap_k1_every_emitted_flag_is_classified():
    # a flag no written list names blocks a later layer's CORRECT (fail-closed); this gate makes each new one a
    # decision: blocking always (_BLOCK_POSITIVE_FLAGS), a meaning abstention, a not proved one, or a note
    emitted = _emitted_flags()
    assert len(emitted) > 50
    known = rules._BLOCK_POSITIVE_FLAGS | rules._MEANING_FLAGS | rules._NOT_PROVEN_FLAGS | rules._NOTE_FLAGS \
        | set(rules._CONFIDENCE_PENALTY)
    assert sorted(emitted - known) == []
    lists = [rules._MEANING_FLAGS, rules._NOT_PROVEN_FLAGS, rules._NOTE_FLAGS]
    assert all(not (a & b) for i, a in enumerate(lists) for b in lists[i + 1:])
