"""Audit of 25 Sep 2026, calculus kinds (limit, antiderivative, definite_integral, derivative,
tangent_line, extremum, trig_solve) and the step refuter.

Every WRONG claim below was certified CORRECT before the fix, and every RIGHT claim marked
"not INCORRECT" was refuted — each measured with an independent ground truth (exact SymPy or a
hand proof, recorded next to the case). Controls pin ordinary right answers to CORRECT.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from mathverify.verifier import verify

ROOT = Path(__file__).resolve().parents[1]


def _v(kind, params, ck, payload, vars_=("x",), steps=(), givens=(), shape="scalar"):
    ir = {"task": {"kind": kind, "params": params}, "vars": [{"name": v} for v in vars_],
          "givens": list(givens), "answer_shape": shape}
    sol = {"claimed_answer": {"kind": ck, "payload": payload, "option": None}, "steps": list(steps)}
    return verify(ir, sol).verdict


def _lim(expr, to, ck, payload, side=None, steps=()):
    p = {"expr": expr, "var": "x", "to": to}
    if side:
        p["side"] = side
    return _v("limit", p, ck, payload, steps=steps)


def _step(claim, kind="compute", sid="s1"):
    return {"id": sid, "kind": kind, "claim": claim, "from": [], "text": ""}


# --------------------------------------------------------------------------- limits
def test_c01_a_real_limit_never_uses_complex_values():
    # sqrt(x-1) is not real for x < 1: the limit at 0 does not exist (it is not I)
    assert _lim("sqrt(x - 1)", "0", "value", "I") != "CORRECT"
    assert _lim("sqrt(x - 1)", "0", "dne", None) != "INCORRECT"
    # sqrt / log are undefined left of 0; asin right of 1
    assert _lim("sqrt(x)", "0", "value", "0", side="-") != "CORRECT"
    assert _lim("sqrt(x)", "0", "dne", None, side="-") != "INCORRECT"
    assert _lim("log(x)", "0", "infinite", "-oo", side="-") != "CORRECT"
    assert _lim("asin(x)", "1", "value", "pi/2", side="+") != "CORRECT"


def test_c01_controls():
    assert _lim("x*log(x)", "0", "value", "0", side="+") == "CORRECT"
    assert _lim("(sqrt(x) - 1)/(x - 1)", "1", "value", "1/2") == "CORRECT"
    assert _lim("sqrt(x)", "0", "value", "0", side="+") == "CORRECT"


def test_c02_accumbounds_is_not_a_proof_of_divergence():
    # sin^2 + cos^2 == 1 identically: the limit exists
    assert _lim("sin(x)**2 + cos(x)**2", "oo", "dne", None) != "CORRECT"
    assert _lim("sin(x)**2 + cos(x)**2", "oo", "value", "1") != "INCORRECT"
    assert _lim("sin(x)*cos(x) - sin(2*x)/2", "oo", "dne", None) != "CORRECT"
    # sign(sin x) does oscillate: "does not exist" is right
    assert _lim("sign(sin(x))", "oo", "dne", None) != "INCORRECT"


def test_c02_controls():
    assert _lim("sin(x)", "oo", "dne", None) == "CORRECT"
    assert _lim("sin(1/x)", "0", "dne", None) == "CORRECT"
    assert _lim("Abs(x)/x", "0", "dne", None) == "CORRECT"
    assert _lim("Abs(x)/x", "0", "value", "1") == "INCORRECT"


def test_c03_oscillating_factor_inside_a_power_is_not_trusted():
    # |sin(k pi)|^(1/(k pi)) = 0 for every k while the value is 1 at k pi + pi/2: no limit
    assert _lim("Abs(sin(x))**(1/x)", "oo", "value", "1") != "CORRECT"
    assert _lim("(1 + 1/x)**x", "oo", "value", "E") == "CORRECT"


def test_c03_guard_holds_without_definedness_conditions():
    # the domain check alone abstains here (|sin x| > 0 is a periodic condition); the oscillation
    # guard must hold on its own, e.g. for a caller that passes no conditions
    import sympy as sp
    from mathverify.certify.limits import classify_limit
    x = sp.Symbol("x", real=True)
    assert classify_limit(sp.Abs(sp.sin(x)) ** (1 / x), x, sp.oo, conds=[])["kind"] != "VAR"
    assert classify_limit((1 + 1 / x) ** x, x, sp.oo, conds=[])["kind"] == "VAR"


def test_h04_infinity_written_in_latex_is_infinite():
    for p in (r"\infty", r"+\infty", "S.Infinity"):
        assert _lim("1/x**2", "0", "value", p) == "CORRECT", p
    assert _lim("-1/x**2", "0", "value", r"-\infty") == "CORRECT"
    assert _lim("1/x**2", "0", "value", r"-\infty") == "INCORRECT"


def test_m01_the_numeric_probe_is_time_bounded():
    code = ("import sys; sys.path.insert(0, %r)\n"
            "from mathverify.verifier import verify\n"
            "r = verify({'task': {'kind': 'limit', 'params': {'expr': 'exp(-exp(x))', 'var': 'x', 'to': 'oo'}},"
            " 'vars': [{'name': 'x'}], 'givens': []}, {'claimed_answer': {'kind': 'value', 'payload': '0'}, 'steps': []})\n"
            "print(r.verdict)\n") % str(ROOT / "src")
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180)
    assert p.returncode == 0, p.stderr[-2000:]
    assert p.stdout.strip().splitlines()[-1] in ("CORRECT", "UNKNOWN")


def test_unknown_side_is_not_guessed():
    assert _lim("Abs(x)/x", "0", "value", "1", side="right") == "UNKNOWN"


# --------------------------------------------------------------------------- derivative / tangent
def _der(f, at, ck, payload, order=None):
    p = {"f": f, "var": "x", "at": at}
    if order:
        p["order"] = order
    return _v("derivative", p, ck, payload)


def test_c04_no_derivative_at_a_corner():
    # one-sided slopes of |x| at 0 are -1 and 1; Max(x, 0): 0 and 1; e^|x|: -1 and 1
    assert _der("Abs(x)", "0", "value", "0") != "CORRECT"
    assert _der("Abs(x)", "0", "dne", None) != "INCORRECT"
    assert _der("Max(x, 0)", "0", "value", "1/2") != "CORRECT"
    assert _der("exp(Abs(x))", "0", "value", "0") != "CORRECT"
    # f jumps at 1 (1 from the left, 2 at 1): not differentiable there
    assert _der("Piecewise((x**2, x < 1), (2*x, x >= 1))", "1", "value", "2") != "CORRECT"
    # (x|x|)' = 2|x| has a corner at 0
    assert _der("x*Abs(x)", "0", "value", "0", order=2) != "CORRECT"


def test_c04_tangent_needs_a_derivative():
    t = {"f": "Abs(x)", "var": "x", "at": "0"}
    assert _v("tangent_line", t, "equation", "y = 0", vars_=("x", "y")) != "CORRECT"
    t = {"f": "Max(x, 0)", "var": "x", "at": "0"}
    assert _v("tangent_line", t, "equation", "y = x/2", vars_=("x", "y")) != "CORRECT"


def test_c04_controls():
    assert _der("x**2*exp(x)", "0", "value", "0") == "CORRECT"
    assert _der("x**2*exp(x)", "0", "value", "2") == "INCORRECT"
    assert _der("x*Abs(x)", "0", "value", "0") == "CORRECT"          # differentiable, f'(0) = 0
    assert _der("x**4", "1", "value", "24", order=3) == "CORRECT"
    t = {"f": "x**2", "var": "x", "at": "1", "dep": "y"}
    assert _v("tangent_line", t, "equation", "y = 2*x - 1", vars_=("x", "y")) == "CORRECT"
    assert _v("tangent_line", t, "equation", "2*x - y - 1 = 0", vars_=("x", "y")) == "CORRECT"
    assert _v("tangent_line", t, "expression", "2*x - 1", vars_=("x", "y")) == "CORRECT"
    assert _v("tangent_line", t, "equation", "y = x", vars_=("x", "y")) == "INCORRECT"


def test_c08_a_tangent_claim_is_compared_as_a_line():
    # (0, 5) satisfies the claim but is not on y = 2x - 1
    t = {"f": "x**2", "var": "x", "at": "1", "dep": "y"}
    assert _v("tangent_line", t, "equation", "(y - 2*x + 1)*(y - 5) = 0", vars_=("x", "y")) != "CORRECT"
    assert _v("tangent_line", t, "equation", "y*(y - 2*x + 1) = 0", vars_=("x", "y")) != "CORRECT"


def test_h05_vertical_tangent_is_not_refuted():
    t = {"f": "cbrt(x)", "var": "x", "at": "0"}
    assert _v("tangent_line", t, "equation", "x = 0", vars_=("x", "y")) != "INCORRECT"


def test_h01_distributional_terms_do_not_refute():
    # (x|x|)'' = 2 sign(x) off 0; SymPy adds 2x·DiracDelta(x)
    assert _v("derivative", {"f": "x*Abs(x)", "var": "x", "order": 2}, "expression", "2*sign(x)") != "INCORRECT"
    # -1/x + sign(x) differs from -1/x by a constant on each half-line of the domain x != 0
    assert _v("antiderivative", {"integrand": "1/x**2", "var": "x"}, "expression", "-1/x + sign(x)") != "INCORRECT"


# --------------------------------------------------------------------------- antiderivative
def _anti(g, payload):
    return _v("antiderivative", {"integrand": g, "var": "x"}, "expression", payload)


def test_c05_antiderivative_must_live_on_the_integrands_domain():
    assert _anti("1/x", "log(x) + C") != "CORRECT"                    # log(-1) is not real
    assert _anti("1/(x - 1)", "log(x - 1)") != "CORRECT"
    assert _anti("tan(x)", "-log(cos(x)) + C") != "CORRECT"
    assert _anti("1/(1 + x**2)", "-atan(1/x) + C") != "CORRECT"        # jumps by pi at 0
    assert _anti("1/(2 + cos(x))", "2*atan(tan(x/2)/sqrt(3))/sqrt(3) + C") != "CORRECT"   # jumps at pi
    assert _anti("1", "x**2/x + C") != "CORRECT"                      # undefined at 0 as written
    assert _anti("x", "x**2/2 + sign(x)") != "CORRECT"                # jumps at 0


def test_c05_controls():
    assert _anti("1/x", "log(Abs(x)) + C") == "CORRECT"
    assert _anti("log(x)", "x*log(x) - x + C") == "CORRECT"
    assert _anti("1/sqrt(x)", "2*sqrt(x) + C") == "CORRECT"
    assert _anti("1/sqrt(1 - x**2)", "asin(x) + C") == "CORRECT"
    assert _anti("1/(x**2 - 1)", "log(Abs((x - 1)/(x + 1)))/2 + C") == "CORRECT"
    assert _anti("tan(x)**2", "tan(x) - x + C") == "CORRECT"
    assert _anti("2*sin(x)*cos(x)", "-cos(2*x)/2 + C") == "CORRECT"
    assert _anti("log(x)", "x*log(x) + C") == "INCORRECT"


def test_c06_the_constant_must_be_additive():
    assert _anti("cos(x)", "sin(x + C)") != "CORRECT"
    assert _anti("cos(x)", "sin(x) + C*x") != "CORRECT"
    assert _anti("cos(x)", "(1 + C)*sin(x)") != "CORRECT"
    assert _anti("cos(x)", "sin(x) + C") == "CORRECT"
    assert _anti("cos(x)", "sin(x) + C**2") == "CORRECT"


# --------------------------------------------------------------------------- definite integral
def _di(g, a, b, payload, **extra):
    return _v("definite_integral", dict({"integrand": g, "var": "x", "a": a, "b": b}, **extra), "value", payload)


def test_c09_an_exact_integral_is_compared_exactly():
    # ∫_0^{π√163} e^x dx = e^(π√163) - 1 = 262537412640768742.99999999999925...
    assert _di("exp(x)", "0", "pi*sqrt(163)", "262537412640768743") != "CORRECT"
    assert _di("x**2", "0", "1", "1/3 + 10**(-30)") != "CORRECT"


def test_c09_controls():
    assert _di("x**2", "0", "1", "1/3") == "CORRECT"
    assert _di("Abs(x - 1) + Abs(x + 2)", "-3", "3", "23") == "CORRECT"
    assert _di("log(x)/sqrt(x)", "0", "1", "-4") == "CORRECT"          # no closed form from SymPy
    assert _di("x**2", "0", "1", "0.333", rel_tol=0.01) == "CORRECT"   # declared tolerance
    assert _di("sin(x)", "0", "pi", "0") == "INCORRECT"


def test_h02_a_numeric_value_that_did_not_converge_never_refutes():
    assert _di("x**(-999/1000)", "0", "1", "1000") != "INCORRECT"
    assert _di("2*x*sin(x**2)", "0", "100", "1 - cos(10000)") != "INCORRECT"


def test_integrand_undefined_on_the_interval_as_written():
    # exp(log(x)) parses to x, sqrt(x)**2 to x; both are undefined for x < 0
    assert _di("exp(log(x))", "-2", "-1", "-3/2") != "CORRECT"
    assert _di("sqrt(x)**2", "-1", "0", "-1/2") != "CORRECT"


# --------------------------------------------------------------------------- extremum
def _ext(f, interval, which, payload):
    p = {"f": f, "var": "x", "which": which}
    if interval:
        p["interval"] = interval
    return _v("extremum", p, "value", payload)


def test_c11_argmax_must_be_unique():
    assert _ext("floor(x)", "[1/2, 3]", "argmin", "1/2") != "CORRECT"   # argmin set is [1/2, 1)
    assert _ext("Min(x, 1)", "[0, 2]", "argmax", "2") != "CORRECT"      # argmax set is [1, 2]
    assert _ext("x**2 - 4*Abs(x - 1)", "[-3, 3]", "argmax", "3") != "CORRECT"   # f(1) = f(3) = 1


def test_c12_kinks_are_candidates():
    # f increases on [0, 1], decreases on [1, ln 100]: max e/100 at 1, not the endpoint value
    f = "exp(x)/100 - Abs(x - 1)"
    assert _ext(f, "[0, 5]", "max", "-99/100") != "CORRECT"
    assert _ext(f, "[0, 5]", "max", "E/100") != "INCORRECT"
    # x^2 - 4|x - 1|: local minima -8 (x=-2) and 0 (x=2), local maximum 1 at the kink x = 1
    assert _ext("x**2 - 4*Abs(x - 1)", None, "local_min", "-8") != "CORRECT"
    assert _ext("x**2 - 4*Abs(x - 1)", None, "local_max", "1") != "INCORRECT"


def test_h03_an_incomplete_candidate_set_does_not_refute_the_claim():
    assert _ext("exp(-x**2)*cos(50*x)", "[-1, 1]", "max", "1") != "INCORRECT"
    assert _ext("x**2/4 - Abs(x - 1)", "[0, 5/2]", "max", "1/4") != "INCORRECT"


def test_c13_unknown_which_abstains():
    assert _ext("4 - (x - 1)**2", "[0, 3]", "maximum", "3") == "UNKNOWN"


def test_extremum_controls():
    assert _ext("x**3 - 3*x", "[-2, 3]", "max", "18") == "CORRECT"
    assert _ext("x**3 - 3*x", "[-2, 3]", "max", "2") == "INCORRECT"
    assert _ext("x**3 - 3*x", "[-2, 3]", "argmax", "3") == "CORRECT"
    assert _ext("x**3 - 6*x**2 + 9*x + 1", None, "local_max", "5") == "CORRECT"
    assert _ext("-Abs(x)", None, "local_max", "0") == "CORRECT"


# --------------------------------------------------------------------------- trig_solve
def _ts(eq, payload, interval=None):
    p = {"var": "x", "equation": eq}
    if interval:
        p["interval"] = interval
    return _v("trig_solve", p, "set", payload, shape="set")


def test_c14_definedness_as_written():
    # every root of sin(x) makes sin(x)^2/sin(x) a 0/0
    assert _ts("sin(x)**2/sin(x) = 0", "{k*pi}") != "CORRECT"
    assert _ts("sin(x)**2/sin(x) = 0", "{0, pi}", "[0, 2*pi)") != "CORRECT"


def test_c15_both_sides_must_be_real():
    # at 5pi/4 sin = cos < 0: sqrt/log of both sides are not real
    assert _ts("sqrt(sin(x)) = sqrt(cos(x))", "{pi/4 + k*pi}") != "CORRECT"
    assert _ts("sqrt(sin(x)) = sqrt(cos(x))", "{pi/4 + 2*k*pi}") != "INCORRECT"
    assert _ts("log(sin(x)) = log(cos(x))", "{pi/4 + k*pi}") != "CORRECT"


def test_c16_a_root_solveset_missed_blocks_the_certificate():
    # 2 sin(x - pi/6) = 1: x = pi/3 or x = pi; SymPy's solveset returns only pi/3
    assert _ts("sqrt(3)*sin(x) - cos(x) = 1", "{pi/3}", "[0, 2*pi)") != "CORRECT"
    assert _ts("sqrt(3)*sin(x) - cos(x) = 1", "{pi/3, pi}", "[0, 2*pi)") != "INCORRECT"
    assert _ts("sqrt(3)*sin(x) - cos(x) = 1", "{pi/3 + 2*k*pi}") != "CORRECT"


def test_trig_controls():
    assert _ts("sin(x) = 1/2", "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}") == "CORRECT"
    assert _ts("sin(x) = 1/2", "{pi/6 + k*pi}") == "INCORRECT"
    assert _ts("cos(2*x) = 1/2", "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", "[0, 2*pi)") == "CORRECT"
    assert _ts("tan(x)*cos(x) = 0", "{k*pi}") == "CORRECT"
    assert _ts("sin(x) = 2", "EmptySet") == "CORRECT"


# --------------------------------------------------------------------------- steps (D cells)
LIM_IR = {"expr": "(x**2 - 4)/(x - 2)", "var": "x", "to": "2"}


@pytest.mark.parametrize("claim", ["Limit(Abs(x)/x, x, 0) = 1", "1 = Limit(Abs(x)/x, x, 0)",
                                   "2*Limit(sin(x)/x, x, 0) = 5", "Limit(log(x), x, -1) = I*pi"])
def test_c17_wrong_limit_steps_are_refuted(claim):
    steps = [_step(claim), _step("Limit(x + 2, x, 2) = 4", sid="s2")]
    assert _v("limit", LIM_IR, "value", "4", steps=steps) != "CORRECT"


def test_c17_wrong_calculus_steps_are_refuted():
    anti = {"integrand": "cos(x)", "var": "x"}
    assert _v("antiderivative", anti, "expression", "sin(x) + C", steps=[_step("2*Integral(x, x) = x**3")]) != "CORRECT"
    assert _v("antiderivative", anti, "expression", "sin(x) + C", steps=[_step("Integral(1/x, x) = log(x)")]) != "CORRECT"
    der = {"f": "x**2", "var": "x", "at": "3"}
    for c in ("Subs(Derivative(Abs(x), x), x, 0) = 0", "at(diff(Abs(x), x), x, 0) = 0"):
        assert _v("derivative", der, "value", "6", steps=[_step(c)]) != "CORRECT", c


def test_c17_controls():
    steps = [_step("(x**2 - 4)/(x - 2) = x + 2", kind="eq"), _step("Limit(x + 2, x, 2) = 4", sid="s2")]
    assert _v("limit", LIM_IR, "value", "4", steps=steps) == "CORRECT"
    anti = {"integrand": "log(x)", "var": "x"}
    assert _v("antiderivative", anti, "expression", "x*log(x) - x + C",
              steps=[_step("Integral(log(x), x) = x*log(x) - x")]) == "CORRECT"
    der = {"f": "x**2*exp(x)", "var": "x", "at": "0"}
    assert _v("derivative", der, "value", "0",
              steps=[_step("diff(x**2*exp(x), x) = (2*x + x**2)*exp(x)"),
                     _step("at((2*x + x**2)*exp(x), x, 0) = 0", sid="s2")]) == "CORRECT"


@pytest.mark.parametrize("kind,params,givens,ck,payload,claim", [
    ("solve_inequality", {"var": "x"}, ["x**2 < 2"], "interval", "(-sqrt(2), sqrt(2))", "x < 1.4"),
    ("solve_inequality", {"var": "x"}, ["(x - 3)/(x + 2) <= 0"], "interval", "(-2, 3]", "x != 3"),
    ("solve_inequality", {"var": "x"}, ["x**2 - 5*x - 14 <= 0"], "interval", "[-2, 7]", "-2 < x"),
    ("domain_of", {"expr": "sqrt(x - 3)", "var": "x"}, [], "interval", "[3, oo)", "x - 3 > 0"),
])
def test_wrong_eq_step_on_a_thin_set_is_refuted(kind, params, givens, ck, payload, claim):
    # x = 1.41, 3, -2 and 3 satisfy every premise and violate the step
    assert _v(kind, params, ck, payload, givens=givens, shape="interval",
              steps=[_step(claim, kind="eq")]) != "CORRECT"


def test_eq_step_controls():
    steps = [_step("x**2 - 5*x - 14 = (x - 7)*(x + 2)", kind="eq"), _step("-2 <= x", kind="eq", sid="s2"),
             _step("x <= 7", kind="eq", sid="s3")]
    assert _v("solve_inequality", {"var": "x"}, "interval", "[-2, 7]", givens=["x**2 - 5*x - 14 <= 0"],
              shape="interval", steps=steps) == "CORRECT"
    assert _v("domain_of", {"expr": "sqrt(x - 3)", "var": "x"}, "interval", "[3, oo)", shape="interval",
              steps=[_step("x - 3 >= 0", kind="eq")]) == "CORRECT"


def test_matrix_eq_step_is_compared_entrywise():
    # [[1,2],[3,4]] * [[-2,1],[3/2,-1/2]] is the identity, not diag(1, 2)
    ir = {"op": "inverse", "matrix": "Matrix([[1,2],[3,4]])"}
    good = "Matrix([[-2, 1], [3/2, -1/2]])"
    lhs = "Matrix([[1,2],[3,4]])*Matrix([[-2, 1], [3/2, -1/2]])"
    wrong = [_step(f"{lhs} = Matrix([[1,0],[0,2]])", kind="eq")]
    right = [_step(f"{lhs} = Matrix([[1,0],[0,1]])", kind="eq")]
    assert _v("linalg", ir, "expression", good, vars_=(), steps=wrong, shape="expression") != "CORRECT"
    assert _v("linalg", ir, "expression", good, vars_=(), steps=right, shape="expression") == "CORRECT"
