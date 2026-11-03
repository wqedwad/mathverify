"""Formal-layer (L7) audit of 25 Sep 2026: every certified wrong claim, as a regression.

The audit fed 98 wrong claims to build_statement + prove_statement (tactic ladder, live Lean) and
53 received clean, audited certificates; 22 of them came out of the fused verifier as CORRECT
0.995. The causes, and what now stops each one:

  C1  principle 12 — templates read the problem through SymPy's simplifying parse (`x**2/x = 0`
      reached Lean as `x = 0`, `exp(log x)` as `x`, `k/k` as `1`); the claim too (`y = x**2/x`).
      Now: definedness is read AS WRITTEN (guards, or refusal).
  C2  restrictions dropped — var constraints, domain_of_discourse, every given but the first,
      complex/rational domains. Now: stated as guards, or the template refuses.
  C3  closed goals elaborated in ℕ (`7 / 2 = 3`). Now: typed.
  C4  Mod: ℤ `%` is Euclidean in Lean, `x % 0 = x`, ℝ `%` is identically 0. Now: refused, except
      an integer mod a positive integer literal, printed in ℤ (Int.emod = SymPy's Mod there).
  C5  recurrences: ℕ subtraction turned an undefined a(-1) into a(0). Now: refused.
  C6  vacuity probe weaker than the proof search. Now: stronger probe AND a positive proof that
      the hypotheses hold at a witness (the sat probe), for every proof source.
  C7  count_structures read the payload with int() (6.5 → 6). Now: exact_integer.
  C8  antiderivative quantified over the claim's junk region (Real.log x = log|x|). Now: the claim
      must be defined on the integrand's whole domain.
  C9  domain_of had no condition for 0**x, (-2)**x, factorial(x), and none for x**(1/2) as
      written. Now: exact conditions or none (the deterministic certificate abstains too).
  E04 a value claim containing the problem's unknowns (`10 - b`). Now: refused.

Offline tests pin the statements; live tests (skipped without the Lean toolchain) run every
formerly certified wrong claim through the real ladder and audit, and the model-written proofs of
the audit through the real audit.
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.formal import prove as P
from mathverify.formal.lean_client import LeanResult
from mathverify.formal.statement import AUTOIMPLICIT_OFF, build_statement, relation_to_lean


def _ir(kind, params, vars_=(), givens=(), shape="scalar", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": [dict(v) for v in vars_],
         "givens": list(givens), "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


X = [{"name": "x"}]
XY = [{"name": "x"}, {"name": "y"}]
AB = [{"name": "a"}, {"name": "b"}]


def _val(p):
    return {"kind": "value", "payload": p}


def _set(p):
    return {"kind": "set", "payload": p}


def _iv(p):
    return {"kind": "interval", "payload": p}


def _cnt(p):
    return {"kind": "count", "payload": p}


def _ex(p):
    return {"kind": "expression", "payload": p}


# (label, ir, claim): every wrong claim that received a clean certificate in the audit
CERTIFIED_WRONG = [
    # C2 restrictions
    ("A07 x^2=-1 over complex, claim {}", _ir("solve_equation", {"equation": "x**2 = -1", "var": "x"},
                                               [{"name": "x", "domain": "complex"}], shape="set"), _set("EmptySet")),
    ("A10 x^2<4 positive_real, (-2,2)", _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"},
                                            [{"name": "x", "domain": "positive_real"}], shape="interval"), _iv("(-2, 2)")),
    ("A11 x^2<4 dod x>0, (-2,2)", _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"}, X,
                                      shape="interval", dod="x > 0"), _iv("(-2, 2)")),
    ("A12 x^2<4 constraint x>0, (-2,2)", _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"},
                                             [{"name": "x", "constraints": ["x > 0"]}], shape="interval"), _iv("(-2, 2)")),
    ("A13 x^2<4 + given x>0, (-2,2)", _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"}, X,
                                          ["x > 0"], shape="interval"), _iv("(-2, 2)")),
    ("A14 x^2<4 positive_integer, (-2,2)", _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"},
                                               [{"name": "x", "domain": "positive_integer"}], shape="interval"), _iv("(-2, 2)")),
    ("A20 count x^2<10 positive_integer, 7", _ir("count_integers", {"var": "x"},
                                                 [{"name": "x", "domain": "positive_integer"}], ["x**2 < 10"],
                                                 shape="count"), _cnt(7)),
    ("A21 count x^2<10 constraint x>0, 7", _ir("count_integers", {"var": "x"},
                                               [{"name": "x", "domain": "integer", "constraints": ["x > 0"]}],
                                               ["x**2 < 10"], shape="count"), _cnt(7)),
    ("C01 2x=4 dod x>5, {2}", _ir("solve_equation", {"equation": "2*x = 4", "var": "x"}, X, shape="set",
                                  dod="x > 5"), _set("{2}")),
    ("C02 2x=4 constraint x>5, {2}", _ir("solve_equation", {"equation": "2*x = 4", "var": "x"},
                                         [{"name": "x", "constraints": ["x > 5"]}], shape="set"), _set("{2}")),
    ("C03 2x=4 + given x>5, {2}", _ir("solve_equation", {"var": "x"}, X, ["2*x = 4", "x > 5"], shape="set"),
     _set("{2}")),
    ("C04 |x-1|=2 dod x>0, {-1,3}", _ir("solve_equation", {"equation": "Abs(x - 1) = 2", "var": "x"}, X,
                                        shape="set", dod="x > 0"), _set("{-1, 3}")),
    ("C06 x=sqrt2 over rational, {sqrt2}", _ir("solve_equation", {"equation": "x = sqrt(2)", "var": "x"},
                                               [{"name": "x", "domain": "rational"}], shape="set"), _set("{sqrt(2)}")),
    ("C25 x<3 nonneg_integer, (-oo,3)", _ir("solve_inequality", {"inequality": "x < 3", "var": "x"},
                                            [{"name": "x", "domain": "nonneg_integer"}], shape="interval"), _iv("(-oo, 3)")),
    ("B50 x^4=1 complex, x^2+1=2", _ir("evaluate", {"expr": "x**2 + 1"}, [{"name": "x", "domain": "complex"}],
                                       ["x**4 = 1"]), _val("2")),
    # C1 principle 12 (problem side and claim side)
    ("A30 x^2/x=0, {0}", _ir("solve_equation", {"equation": "x**2/x = 0", "var": "x"}, X, shape="set"), _set("{0}")),
    ("A31 sqrt(x)^2=-1, {-1}", _ir("solve_equation", {"equation": "sqrt(x)**2 = -1", "var": "x"}, X, shape="set"),
     _set("{-1}")),
    ("A32 x/x>0, R", _ir("solve_inequality", {"inequality": "x/x > 0", "var": "x"}, X, shape="interval"),
     _iv("(-oo, oo)")),
    ("A33 sqrt(x)^2<0, (-oo,0)", _ir("solve_inequality", {"inequality": "sqrt(x)**2 < 0", "var": "x"}, X,
                                     shape="interval"), _iv("(-oo, 0)")),
    ("A34 log x - log x >= 0, R", _ir("solve_inequality", {"inequality": "log(x) - log(x) >= 0", "var": "x"}, X,
                                      shape="interval"), _iv("(-oo, oo)")),
    ("A36 (sqrt(x)^2)'(-1)=1", _ir("derivative", {"f": "sqrt(x)**2", "var": "x", "at": "-1"}, X), _val("1")),
    ("A37 (exp(log x))'(-1)=1", _ir("derivative", {"f": "exp(log(x))", "var": "x", "at": "-1"}, X), _val("1")),
    ("A38 max x/x-x^2 on [-1,1]=1", _ir("extremum", {"f": "x/x - x**2", "var": "x", "interval": "[-1, 1]",
                                                     "which": "max"}, X), _val("1")),
    ("A39 max exp(log x) on [-2,-1]=-1", _ir("extremum", {"f": "exp(log(x))", "var": "x", "interval": "[-2, -1]",
                                                          "which": "max"}, X), _val("-1")),
    ("A40 sum k/k, k=-1..1 = 3", _ir("series_sum", {"term": "k/k", "var": "k", "lo": "-1", "hi": "1"},
                                     [{"name": "k", "domain": "integer"}]), _val("3")),
    ("A41 int exp(log x) on [-2,-1]", _ir("definite_integral", {"integrand": "exp(log(x))", "var": "x", "a": "-2",
                                                                "b": "-1"}, X), _val("-3/2")),
    ("A42 int sqrt(x)^2 on [-1,0]", _ir("definite_integral", {"integrand": "sqrt(x)**2", "var": "x", "a": "-1",
                                                              "b": "0"}, X), _val("-1/2")),
    ("A43 count x/x+x^2<5 = 3", _ir("count_integers", {"var": "x"}, [{"name": "x", "domain": "integer"}],
                                    ["x/x + x**2 < 5"], shape="count"), _cnt(3)),
    ("A44 count x/x=1, x^2<=9 = 7", _ir("count_solutions", {"bounds": {"x": ["-3", "3"]}},
                                        [{"name": "x", "domain": "integer"}], ["x/x = 1", "x**2 <= 9"],
                                        shape="count"), _cnt(7)),
    ("C32 antiderivative of 1 = x^2/x", _ir("antiderivative", {"integrand": "1", "var": "x"}, X, shape="expression"),
     _ex("x**2/x + C")),
    ("E01 line through 0,0 and 1,1: y = x^2/x", _ir("equation_of", {"object": "line_points", "p1": ["0", "0"],
                                                                     "p2": ["1", "1"]}, XY, shape="equation"),
     {"kind": "equation", "payload": "y = x**2/x"}),
    ("E03 unit circle: x^2+y^2 = x/x", _ir("equation_of", {"object": "circle_center_radius", "center": ["0", "0"],
                                                           "radius": "1"}, XY, shape="equation"),
     {"kind": "equation", "payload": "x**2 + y**2 = x/x"}),
    # C9 domain_of
    ("A45 domain x**(1/2) = R", _ir("domain_of", {"expr": "x**(1/2)", "var": "x"}, X, shape="interval"),
     _iv("(-oo, oo)")),
    ("A46 domain 0**x = R", _ir("domain_of", {"expr": "0**x", "var": "x"}, X, shape="interval"), _iv("(-oo, oo)")),
    ("A47 domain (-2)**x = R", _ir("domain_of", {"expr": "(-2)**x", "var": "x"}, X, shape="interval"),
     _iv("(-oo, oo)")),
    ("A48 domain factorial(x) = R", _ir("domain_of", {"expr": "factorial(x)", "var": "x"}, X, shape="interval"),
     _iv("(-oo, oo)")),
    # C6 vacuity
    ("B01 a+b from a^2+b^2<2ab = 42", _ir("evaluate", {"expr": "a + b"}, AB, ["a**2 + b**2 < 2*a*b"]), _val("42")),
    ("B05 a*b from a^2+b^2<2ab, a=1 = 3", _ir("evaluate", {"expr": "a*b"}, AB, ["a**2 + b**2 < 2*a*b", "a = 1"]),
     _val("3")),
    # C5 recurrences
    ("B10 a(n)=a(n-1)+a(n-2), a0 only: a3=5", _ir("recurrence_term", {"name": "a", "var": "n",
                                                                     "recurrence": "a(n) = a(n-1) + a(n-2)",
                                                                     "initial": {"0": "1"}, "index": 3},
                                                 [{"name": "n", "domain": "integer"}]), _val("5")),
    ("B12 a(n)=2a(n-3)+1: a4=5", _ir("recurrence_term", {"name": "a", "var": "n", "recurrence": "a(n) = 2*a(n-3) + 1",
                                                         "initial": {"0": "1", "1": "2"}, "index": 4},
                                     [{"name": "n", "domain": "integer"}]), _val("5")),
    # C7 int()
    ("B20 arrangements of 3 = 6.5", _ir("count_structures", {"space": {"structure": "arrangement_all", "n": 3}},
                                        shape="count"), _cnt(6.5)),
    ("B21 2-subsets of 5 = 10.9", _ir("count_structures", {"space": {"structure": "combination", "n": 5, "k": 2}},
                                      shape="count"), _cnt(10.9)),
    # C8 antiderivative
    ("B40 int dx/x = log x", _ir("antiderivative", {"integrand": "1/x", "var": "x"}, X, shape="expression"),
     _ex("log(x) + C")),
    # E04
    ("E04 a from a+b=10 = 10-b", _ir("evaluate", {"expr": "a"}, AB, ["a + b = 10"]), _val("10 - b")),
    # C4 Mod
    ("E13 sum k mod 2, k=1..4 = 0", _ir("series_sum", {"term": "Mod(k, 2)", "var": "k", "lo": "1", "hi": "4"},
                                        [{"name": "k", "domain": "integer"}]), _val("0")),
    ("E15 Mod(x,2) simplifies to 0", _ir("simplify_expression", {"expr": "Mod(x, 2)"}, X, shape="expression"),
     _ex("0")),
    # C3 ℕ elaboration of closed goals
    ("F01 7/2 = 3", _ir("evaluate", {"expr": "7/2"}), _val("3")),
    ("F02 1/2 + 1/3 = 0", _ir("evaluate", {"expr": "1/2 + 1/3"}), _val("0")),
    ("F03 10/4 = 2", _ir("evaluate", {"expr": "10/4"}), _val("2")),
    ("F04 2**(-1) = 0", _ir("evaluate", {"expr": "2**(-1)"}), _val("0")),
    ("F05 3 = 7/2", _ir("evaluate", {"expr": "3"}), _val("7/2")),
    ("F06 (1+2)/(2*2) = 0", _ir("evaluate", {"expr": "(1 + 2)/(2*2)"}), _val("0")),
    ("F09 2**10/1000 = 1", _ir("evaluate", {"expr": "2**10/1000"}), _val("1")),
]


def _build(ir, claim):
    return build_statement(ir, claim)


# ------------------------------------------------------------------ offline: what each template now states
def _goal(ir, claim):
    st = _build(ir, claim)
    assert st is not None
    return st.goal


REFUSED = {  # label prefix -> must produce NO statement
    "A07", "C06", "B50",                       # complex / rational variable
    "A36", "A37", "A38", "A39", "A40", "A41", "A42", "A43", "A44",   # undefined as written
    "C32", "E01", "E03",                       # claim undefined as written
    "A46", "A47", "A48",                       # no exact domain rule
    "B10", "B12",                              # ℕ subtraction below the initial terms
    "B20", "B21",                              # non-integer count
    "B40",                                     # claim undefined on the integrand's domain
    "E04",                                     # claim in the problem's unknowns
    "E15",                                     # Mod of a real variable
}


@pytest.mark.parametrize("label,ir,claim", [c for c in CERTIFIED_WRONG if c[0][:3] in REFUSED],
                         ids=[c[0] for c in CERTIFIED_WRONG if c[0][:3] in REFUSED])
def test_formerly_certified_wrong_claim_gets_no_statement(label, ir, claim):
    st = _build(ir, claim)
    assert st is None, f"{label}: {st and st.goal}"


def test_c2_domain_of_discourse_constraint_and_second_given_are_guards_and_root_conditions():
    for ir_ in (CERTIFIED_WRONG[8][1], CERTIFIED_WRONG[9][1], CERTIFIED_WRONG[10][1]):   # C01, C02, C03
        g = _goal(ir_, _set("{2}"))
        assert "(x > 5) →" in g and "((2 : ℝ) > 5)" in g, g                            # root must satisfy it
    right = _build(_ir("solve_equation", {"equation": "2*x = 4", "var": "x"}, X, shape="set", dod="x > 0"),
                   _set("{2}"))
    assert right is not None and "(x > 0) →" in right.goal


def test_c2_inequality_solution_set_must_lie_in_the_declared_domain():
    for label, ir_, claim in CERTIFIED_WRONG:
        if label[:3] in ("A10", "A11", "A12", "A13", "A14", "C25"):
            g = _goal(ir_, claim)
            assert g.count("∀") == 2, (label, g)          # guarded iff AND claimed ⊆ restrictions


def test_c2_count_integers_counts_only_the_declared_domain():
    g = _goal(CERTIFIED_WRONG[6][1], _cnt(3))                                       # A20
    assert "(0 < x)" in g and g.endswith(".card = 3")


def test_c2_templates_that_state_no_restriction_refuse_one():
    base = {"f": "x**2", "var": "x", "interval": "[-1, 1]", "which": "max"}
    assert _build(_ir("extremum", base, X), _val("1")) is not None
    assert _build(_ir("extremum", base, [{"name": "x", "constraints": ["x > 0"]}]), _val("1")) is None
    assert _build(_ir("extremum", base, X, dod="x > 0"), _val("1")) is None
    assert _build(_ir("extremum", base, X, ["x > 0"]), _val("1")) is None
    assert _build(_ir("extremum", base, [{"name": "x", "domain": "positive_real"}]), _val("1")) is None


def test_c2_an_integer_unknown_in_a_real_statement_is_refused():
    ir_ = _ir("evaluate", {"expr": "n + x"}, [{"name": "n", "domain": "integer"}, {"name": "x"}],
              ["2*n = 1", "x = 0"])
    assert _build(ir_, _val("1/2")) is None


def test_c1_solve_templates_guard_with_the_written_domain():
    assert "(x ≠ 0) →" in _goal(CERTIFIED_WRONG[15][1], _set("{0}"))              # A30
    assert "((0 : ℝ) ≠ 0)" in _goal(CERTIFIED_WRONG[15][1], _set("{0}"))          # the root is excluded
    assert "(x ≥ 0) →" in _goal(CERTIFIED_WRONG[16][1], _set("{-1}"))             # A31
    g = _goal(CERTIFIED_WRONG[17][1], _iv("(-oo, oo)"))                           # A32
    assert "(x ≠ 0) →" in g and "→ ((x ≠ 0)))" in g
    # the right answers still get statements
    assert _build(CERTIFIED_WRONG[15][1], _set("EmptySet")) is not None


def test_c1_a_function_body_whose_domain_the_parse_changes_is_refused():
    ir_ = _ir("evaluate", {"expr": "f(2)"}, [])
    ir_["functions"] = [{"name": "f", "expr": "x**2/x", "args": ["x"]}]
    assert _build(ir_, _val("2")) is None
    ir_["functions"] = [{"name": "f", "expr": "x**2 + 1", "args": ["x"]}]
    assert _build(ir_, _val("5")) is not None


def test_c1_a_closed_claim_undefined_as_written_is_refused():
    assert _build(_ir("evaluate", {"expr": "-1"}), _val("sqrt(-1)**2")) is None
    assert _build(_ir("solve_equation", {"equation": "x + 1 = 0", "var": "x"}, X, shape="set"),
                  _set("{sqrt(-1)**2}")) is None
    assert _build(_ir("solve_equation", {"equation": "x + 1 = 0", "var": "x"}, X, shape="set"),
                  _set("{-1}")) is not None


def test_c1_a_latex_claim_is_read_as_written_not_evaluated():
    st = _build(_ir("simplify_expression", {"expr": "x"}, X, shape="expression"), _ex("\\frac{x^2}{x}"))
    assert st is not None and "(x ≠ 0) ∧" in st.goal, st and st.goal              # a GOAL, not dropped


def test_c3_closed_goals_and_relations_are_typed():
    assert _goal(*CERTIFIED_WRONG[[c[0][:3] for c in CERTIFIED_WRONG].index("F01")][1:]) == "((7 / 2) : ℝ) = 3"
    assert _goal(_ir("evaluate", {"expr": "3"}), _val("7/2")) == "(3 : ℝ) = (7 / 2)"
    rel = sp.Eq(sp.Mul(1, sp.Pow(2, -1, evaluate=False), evaluate=False), 0, evaluate=False)
    assert relation_to_lean(rel).startswith("((1 / 2) : ℝ) =")


MOD_REFUSED = [   # no faithful Lean rendering: every template refuses
    ("negative divisor", _ir("evaluate", {"expr": "Mod(x, -2)"}, [{"name": "x", "domain": "integer"}], ["x = 7"]),
     _val("1")),
    ("negative divisor, closed", _ir("evaluate", {"expr": "Mod(7, -2)"}), _val("-1")),
    ("zero divisor", _ir("evaluate", {"expr": "Mod(7, 0)"}), _val("7")),
    ("symbolic divisor", _ir("evaluate", {"expr": "Mod(x, n)"}, [{"name": "x", "domain": "integer"},
                                                                 {"name": "n", "domain": "integer"}],
                             ["x = 7", "n = 2"]), _val("1")),
    ("real dividend", _ir("evaluate", {"expr": "Mod(x, 3)"}, X, ["x = 7"]), _val("1")),
    ("rational dividend", _ir("evaluate", {"expr": "Mod(7/2, 2)"}), _val("3/2")),
    ("negative divisor in a sum", _ir("series_sum", {"term": "Mod(k, -3)", "var": "k", "lo": "1", "hi": "3"},
                                      [{"name": "k", "domain": "integer"}]), _val("3")),
    ("real variable in a simplification", _ir("simplify_expression", {"expr": "Mod(x, 2)"}, X, shape="expression"),
     _ex("0")),
]


@pytest.mark.parametrize("label,ir,claim", MOD_REFUSED, ids=[m[0] for m in MOD_REFUSED])
def test_c4_mod_outside_the_safe_subset_is_refused(label, ir, claim):
    assert _build(ir, claim) is None, label


# integer mod a positive literal: printed in ℤ, where Lean's Int.emod equals SymPy's Mod
MOD_SAFE = [  # (label, ir, claim, right?)
    ("5^100 mod 7 = 2", _ir("evaluate", {"expr": "Mod(5**100, 7)"}), _val("2"), True),
    ("5^100 mod 7 = 3", _ir("evaluate", {"expr": "Mod(5**100, 7)"}), _val("3"), False),
    ("-7 mod 3 = 2 (negative dividend)", _ir("evaluate", {"expr": "Mod(-7, 3)"}), _val("2"), True),
    ("-7 mod 3 = -1 (truncated-division answer)", _ir("evaluate", {"expr": "Mod(-7, 3)"}), _val("-1"), False),
    ("n + 4 = 28, n even, 3n + 6 = 78", _ir("evaluate", {"expr": "n + 4"}, [{"name": "n", "domain": "nonneg_integer"}],
                                            ["Mod(n, 2) = 0", "n + (n + 2) + (n + 4) = 78"]), _val("28"), True),
    ("n + 4 = 30, n even, 3n + 6 = 78", _ir("evaluate", {"expr": "n + 4"}, [{"name": "n", "domain": "nonneg_integer"}],
                                            ["Mod(n, 2) = 0", "n + (n + 2) + (n + 4) = 78"]), _val("30"), False),
    ("sum k mod 2, k = 1..4 = 2", _ir("series_sum", {"term": "Mod(k, 2)", "var": "k", "lo": "1", "hi": "4"},
                                      [{"name": "k", "domain": "integer"}]), _val("2"), True),
    ("sum k mod 2, k = 1..4 = 0", _ir("series_sum", {"term": "Mod(k, 2)", "var": "k", "lo": "1", "hi": "4"},
                                      [{"name": "k", "domain": "integer"}]), _val("0"), False),
    ("even x with x^2 < 9: 3", _ir("count_integers", {"var": "x"}, [{"name": "x", "domain": "integer"}],
                                   ["Mod(x, 2) = 0", "x**2 < 9"], shape="count"), _cnt(3), True),
    ("even x with x^2 < 9: 2", _ir("count_integers", {"var": "x"}, [{"name": "x", "domain": "integer"}],
                                   ["Mod(x, 2) = 0", "x**2 < 9"], shape="count"), _cnt(2), False),
]


def test_c4_safe_mod_is_printed_in_the_integers():
    st = _build(MOD_SAFE[0][1], MOD_SAFE[0][2])
    assert st is not None and st.goal.startswith("((((5 ^ 100) % 7 : ℤ) : ℝ) : ℝ) = 2"), st and st.goal
    st = _build(MOD_SAFE[4][1], MOD_SAFE[4][2])
    assert st is not None and "(n % 2 : ℤ) = 0" in st.hypotheses and st.witness == ("24",)
    for label, ir_, claim, _right in MOD_SAFE:
        assert _build(ir_, claim) is not None, label


def test_c5_recurrence_with_enough_initial_terms_is_kept():
    st = _build(_ir("recurrence_term", {"name": "a", "var": "n", "recurrence": "a(n) = a(n-1) + a(n-2)",
                                        "initial": {"0": "1", "1": "1"}, "index": 3},
                    [{"name": "n", "domain": "integer"}]), _val("3"))
    assert st is not None and st.sat_by_construction


def test_c6_vacuity_probe_contains_the_ladder_hint_sets():
    st = _build(CERTIFIED_WRONG[[c[0][:3] for c in CERTIFIED_WRONG].index("B01")][1], _val("42"))
    probe = st.vacuity_probe()
    assert "(nlinarith [sq_nonneg (a - b), sq_nonneg (a + b)]; done)" in probe
    assert "(field_simp at *; nlinarith; done)" in probe


def test_c6_contradictory_givens_have_no_witness_and_no_sat_probe():
    for label in ("B01", "B05"):
        ir_, claim = next(c[1:] for c in CERTIFIED_WRONG if c[0].startswith(label))
        st = _build(ir_, claim)
        assert st is not None and st.hypotheses and st.witness is None and st.sat_probe() is None


def test_c6_a_consistent_system_gets_an_exactly_checked_witness():
    st = _build(_ir("evaluate", {"expr": "a + b"}, AB, ["a - b = 2", "a + 2*b = 11"]), _val("8"))
    assert st.witness == ("5", "3")
    probe = st.sat_probe()
    assert probe.startswith(AUTOIMPLICIT_OFF + "theorem mv_claim_sat : ∃ a b : ℝ, ")
    assert "refine ⟨5, 3, ?_⟩" in probe
    # a Diophantine system: the witness is searched over the integers
    st2 = _build(_ir("evaluate", {"expr": "x + y"}, [{"name": "x", "domain": "positive_integer"},
                                                     {"name": "y", "domain": "positive_integer"}],
                     ["3*x + 5*y = 41", "x < y"]), _val("9"))
    assert st2.witness == ("2", "7")


def test_c6_a_guard_that_contradicts_the_givens_leaves_no_witness():
    st = _build(_ir("evaluate", {"expr": "x"}, X, ["1/(x - 2) = 0"]), _val("2"))
    assert st is not None and st.witness is None


class _FakeLean:
    """The proof compiles, the axioms are safe, the vacuity and no-hypothesis probes fail (Lean
    'finds the hypotheses consistent and used'); the sat probe answers `sat`."""

    def __init__(self, sat):
        self.sat, self.calls = sat, []

    def run(self, code, timeout=120.0, env=-1):
        body = code.removeprefix(AUTOIMPLICIT_OFF)
        if code.startswith("#print axioms"):
            self.calls.append("axioms")
            return LeanResult(ok=True, infos=["'mv_claim' depends on axioms: [propext]"])
        for kind in ("vacuity", "nohyp", "sat"):
            if body.startswith(f"theorem mv_claim_{kind} "):
                self.calls.append(kind)
                if kind == "sat":
                    return self.sat
                return LeanResult(ok=False, errors=["linarith failed"])
        self.calls.append("proof")
        return LeanResult(ok=True, env=3)


def test_c6_audit_refuses_hypotheses_without_a_satisfiability_proof():
    st = _build(CERTIFIED_WRONG[[c[0][:3] for c in CERTIFIED_WRONG].index("B01")][1], _val("42"))
    r = P.prove_statement(st, use_model=False, lean=_FakeLean(LeanResult(ok=True)), tactic_timeout=45)
    a = r["audit"]
    assert r["proved"] and a["satisfiable"] is False and a["clean"] is False
    assert "sat" not in r and a["satisfiable_how"] == "no witness"


@pytest.mark.parametrize("answer,clean,unanswered", [
    (LeanResult(ok=True), True, []),
    (LeanResult(ok=False, errors=["unsolved goals"]), False, []),
    (LeanResult(ok=False, errors=["lean timeout after 45s"], timed_out=True), False, ["sat"]),
], ids=["proved", "refuted", "timeout"])
def test_c6_audit_needs_the_sat_probe_to_compile(answer, clean, unanswered):
    st = _build(_ir("evaluate", {"expr": "a + b"}, AB, ["a - b = 2", "a + 2*b = 11"]), _val("8"))
    lean = _FakeLean(answer)
    r = P.prove_statement(st, use_model=False, lean=lean, tactic_timeout=45)
    a = r["audit"]
    assert a["clean"] is clean and a["unanswered"] == unanswered
    assert lean.calls[-1] == "sat"


def test_c6_a_model_written_proof_passes_the_same_gate(monkeypatch):
    from mathverify.llm.base import LLMResponse

    class _Model:
        def complete(self, system, user, **kw):
            return LLMResponse(text="", parsed={"proof": "  nlinarith [Real.sqrt_nonneg x]"}, provider="f", model="f")

    monkeypatch.setattr(P, "get_client", lambda family, model=None: _Model())
    st = _build(_ir("evaluate", {"expr": "x"}, X, ["sqrt(x) = -1"]), _val("5"))       # audit D10
    assert st is not None and st.witness is None

    class _Lean(_FakeLean):
        def run(self, code, timeout=120.0, env=-1):
            if code.endswith(":= by\n  nlinarith [Real.sqrt_nonneg x]") or code.startswith("#print") \
                    or "_vacuity " in code or "_nohyp " in code or "_sat " in code:
                return super().run(code, timeout, env)
            return LeanResult(ok=False, errors=["linarith failed"])

    r = P.prove_statement(st, use_model=True, model_attempts=1, lean=_Lean(LeanResult(ok=True)), tactic_timeout=45)
    assert r["proved"] and r["source"].startswith("model:")
    assert r["audit"]["satisfiable"] is False and r["audit"]["clean"] is False


def test_c7_a_non_integer_count_payload_is_never_truncated():
    ir_ = CERTIFIED_WRONG[[c[0][:3] for c in CERTIFIED_WRONG].index("B20")][1]
    assert _build(ir_, _cnt(6.5)) is None and _build(ir_, _cnt("6.5")) is None
    assert _build(ir_, _cnt(6)) is not None


def test_c8_antiderivative_region_is_the_integrands_domain():
    st = _build(_ir("antiderivative", {"integrand": "log(x)", "var": "x"}, X, shape="expression"),
                _ex("x*log(x) - x + C"))
    assert st is not None and st.goal.startswith("∀ x : ℝ, x ≠ 0 → x > 0 → HasDerivAt ")
    assert _build(_ir("antiderivative", {"integrand": "1/(x - 1)", "var": "x"}, X, shape="expression"),
                  _ex("log(x - 1) + C")) is None


def test_c8_derivative_function_is_stated_on_the_interior_of_the_domain():
    st = _build(_ir("derivative", {"f": "x*log(x)", "var": "x"}, X, shape="expression"), _ex("log(x) + 1"))
    assert st is not None and "x > 0 →" in st.goal
    # a claimed derivative undefined inside that region: refused (x/x at 0 for f = x²)
    assert _build(_ir("derivative", {"f": "x**2", "var": "x"}, X, shape="expression"), _ex("2*x*(x/x)")) is None


def test_c9_definedness_is_exact_or_nothing():
    from mathverify.certify.domain import definedness_conditions_strict as strict
    x = sp.Symbol("x", real=True)
    for e in (sp.Pow(0, x, evaluate=False), sp.Pow(-2, x, evaluate=False), sp.factorial(x), sp.Mod(x, 2),
              sp.gamma(x), sp.Pow(x, x), sp.Function("g")(x)):
        assert strict(e, x) is None, e
    half = sp.Pow(x, sp.Mul(1, sp.Pow(2, -1, evaluate=False), evaluate=False), evaluate=False)
    assert strict(half, x) == [x >= 0]                                      # x**(1/2) as written
    # 0**pi: 0 by the strict rule, undefined read through exp(pi*log x): a convention point, not a value
    # (round 10 of part d4b, RK-1, DECISIONS §90); a Lean template refuses a convention atom
    from mathverify.certify.domain import ZERO_POWER_BASE
    assert strict(sp.Pow(2, x), x) == [] and strict(sp.Pow(x, sp.pi), x) == [x >= 0, sp.Contains(x, ZERO_POWER_BASE)]
    assert _goal(CERTIFIED_WRONG[[c[0][:3] for c in CERTIFIED_WRONG].index("A45")][1], _iv("[0, oo)")) \
        == "∀ x : ℝ, (((x ≥ 0)) ↔ (0 ≤ x))"


def test_c9_the_deterministic_domain_certificate_abstains_too():
    from mathverify.verifier import verify
    for expr in ("factorial(x)", "0**x", "(-2)**x"):
        r = verify(_ir("domain_of", {"expr": expr, "var": "x"}, X, shape="interval"),
                   {"claimed_answer": _iv("(-oo, oo)"), "steps": []})
        layer = next(l for l in r.layers if l.layer == "certify.domain")
        assert layer.verdict == "unknown", (expr, layer.evidence)
        assert r.verdict != "CORRECT", expr


def test_derivative_at_point_is_typed():
    st = _build(_ir("derivative", {"f": "x**3", "var": "x", "at": "2"}, X), _val("12"))
    assert st.goal.endswith("(2 : ℝ)") and "hasDerivAt_id' ((2 : ℝ))" in st.hints[0]


# ------------------------------------------------------------------ live Lean
@pytest.fixture(scope="module")
def lean():
    from mathverify.formal import get_lean, lean_available
    if not lean_available(timeout=300):
        pytest.skip("Lean/Mathlib toolchain not available")
    return get_lean()


@pytest.mark.parametrize("label,ir,claim", CERTIFIED_WRONG, ids=[c[0] for c in CERTIFIED_WRONG])
def test_live_no_formerly_certified_wrong_claim_is_certified(lean, label, ir, claim):
    st = _build(ir, claim)
    if st is None:
        return
    r = P.prove_statement(st, use_model=False, lean=lean, tactic_timeout=45)
    assert not (r["proved"] and r["audit"].get("clean")), (label, r.get("proof"), r.get("audit"))


# The audit's model-written proofs (the use_model=True path), each through the real audit.
HAND = [
    ("D01 x^2=4 with x>0 claimed {-2,2}", _ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, X, shape="set",
                                               dod="x > 0"), _set("{-2, 2}"),
     "  refine ⟨fun x => ?_, by norm_num, by norm_num⟩\n  constructor\n  · intro h\n"
     "    have h' : (x + 2) * (x - 2) = 0 := by ring_nf; linarith\n"
     "    rcases mul_eq_zero.mp h' with h1 | h1\n    · left; linarith\n    · right; linarith\n"
     "  · rintro (rfl | rfl) <;> norm_num"),
    ("D10 x from sqrt x = -1", _ir("evaluate", {"expr": "x"}, X, ["sqrt(x) = -1"]), _val("5"),
     "  nlinarith [Real.sqrt_nonneg x]"),
    ("D11 x from exp x = -1", _ir("evaluate", {"expr": "x"}, X, ["exp(x) = -1"]), _val("5"),
     "  nlinarith [Real.exp_pos x]"),
    ("D12 x from sin x = 2", _ir("evaluate", {"expr": "x"}, X, ["sin(x) = 2"]), _val("5"),
     "  nlinarith [Real.sin_le_one x]"),
    ("D13 x from cos x + 3 = 0", _ir("evaluate", {"expr": "x"}, X, ["cos(x) + 3 = 0"]), _val("1"),
     "  nlinarith [Real.neg_one_le_cos x]"),
    ("D14 x from |x| = -1", _ir("evaluate", {"expr": "x"}, X, ["Abs(x) = -1"]), _val("5"),
     "  nlinarith [abs_nonneg x]"),
    ("D15 a+b from a^2+b^2+2 < 2a+2b", _ir("evaluate", {"expr": "a + b"}, AB, ["a**2 + b**2 + 2 < 2*a + 2*b"]),
     _val("5"), "  nlinarith [sq_nonneg (a - 1), sq_nonneg (b - 1)]"),
    ("D16 x from x^2+1 < 2x", _ir("evaluate", {"expr": "x"}, X, ["x**2 + 1 < 2*x"]), _val("7"),
     "  nlinarith [sq_nonneg (x - 1)]"),
]


@pytest.mark.parametrize("label,ir,claim,proof", HAND, ids=[h[0] for h in HAND])
def test_live_model_written_proofs_of_the_audit_get_no_certificate(lean, label, ir, claim, proof):
    st = _build(ir, claim)
    if st is None:
        return
    r = lean.run(st.theorem(proof), timeout=60)
    if not r.clean:
        return                                   # the statement now says what the problem says
    out = {"proof": proof, "env": r.env, "errors": []}
    audit = P._audit(st, out, lean, 60.0)
    assert audit["clean"] is False, (label, audit)


# Right answers that must stay certified: the fixes cost coverage only where they refuse.
KEEP = [
    ("evaluate with an exact witness", _ir("evaluate", {"expr": "a + b"}, AB, ["a - b = 2", "a + 2*b = 11"]),
     _val("8")),
    ("Diophantine witness", _ir("evaluate", {"expr": "x + y"}, [{"name": "x", "domain": "positive_integer"},
                                                                {"name": "y", "domain": "positive_integer"}],
                                ["3*x + 5*y = 41", "x < y"]), _val("9")),
    ("solve with a domain of discourse", _ir("solve_equation", {"equation": "2*x = 4", "var": "x"}, X, shape="set",
                                             dod="x > 0"), _set("{2}")),
    ("solve with the restriction excluding the root", _ir("solve_equation", {"equation": "2*x = 4", "var": "x"}, X,
                                                          shape="set", dod="x > 5"), _set("EmptySet")),
    ("typed closed arithmetic", _ir("evaluate", {"expr": "12/4 + 1"}), _val("4")),
    ("count over the declared domain", _ir("count_integers", {"var": "x"},
                                           [{"name": "x", "domain": "positive_integer"}], ["x**2 < 10"],
                                           shape="count"), _cnt(3)),
    ("antiderivative on the integrand's domain", _ir("antiderivative", {"integrand": "log(x)", "var": "x"}, X,
                                                     shape="expression"), _ex("x*log(x) - x + C")),
    ("derivative at a typed point", _ir("derivative", {"f": "x**3", "var": "x", "at": "2"}, X), _val("12")),
]


@pytest.mark.parametrize("label,ir,claim", KEEP, ids=[k[0] for k in KEEP])
def test_live_right_answers_keep_their_certificate(lean, label, ir, claim):
    st = _build(ir, claim)
    assert st is not None, label
    r = P.prove_statement(st, use_model=False, lean=lean, tactic_timeout=45)
    assert r["proved"] and r["audit"]["clean"], (label, [a.get("errors") for a in r["attempts"]][:3], r.get("audit"))


@pytest.mark.parametrize("label,ir,claim,right", MOD_SAFE, ids=[m[0] for m in MOD_SAFE])
def test_live_safe_mod_certifies_exactly_the_right_answers(lean, label, ir, claim, right):
    st = _build(ir, claim)
    assert st is not None, label
    r = P.prove_statement(st, use_model=False, lean=lean, tactic_timeout=45)
    certified = bool(r["proved"] and r["audit"]["clean"])
    if right:
        assert certified, (label, [a.get("errors") for a in r["attempts"]][:3], r.get("audit"))
    else:
        assert not certified, (label, r.get("proof"), r.get("audit"))
