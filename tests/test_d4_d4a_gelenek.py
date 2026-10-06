"""Fourth audit, part d4a (1 Oct 2026): conventions and the z3 bridge.

An operation whose value at some point is a convention, not the curriculum's, gets no verdict that
depends on that value (DECISIONS §80): an odd root written as a power at a negative base (real root or
principal value; a root written as a root is the real root), 0**0, C(n, r) outside 0 <= r <= n, Mod by a
divisor that is not positive, and ℕ written without a mark (0 in it or not). z3 reads the integrality of
the domain of discourse, and givens with no instance refute nothing (CAP-C1, D4-ADIM-K, CAP-N1, CAP-B1,
G13, CAP-M1, CAP-D1, CAP-Z1; probe: denetim/2026-10-01/d4a/sonda.py).
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_real"}
N = {"name": "n", "domain": "integer"}
M = {"name": "m", "domain": "integer"}
CPLX = "1 + sqrt(3)*I"


def ev(expr, vars_=(), givens=(), dod=None, options=None):
    d = {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": "scalar"}
    if dod is not None:
        d["domain_of_discourse"] = dod
    if options:
        d["options"] = options
    return d


def solve(eq, var="x", vars_=(X,), givens=(), dod=None, kind="solve_equation"):
    key = "equation" if kind == "solve_equation" else "inequality"
    d = {"task": {"kind": kind, "params": {"var": var, key: eq}}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": "set"}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def sol(payload, steps=(), kind="value", option=None):
    return {"claimed_answer": {"kind": kind, "payload": payload, "option": option},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def verdict(ir, s):
    return verify(ir, s).verdict


def step_statuses(ir, s):
    r = verify(ir, s)
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    return r.verdict, [st["status"] for st in layer.evidence["steps"]]


# ---------------------------------------------------------------------------- odd roots (CAP-C1)
@pytest.mark.parametrize("e", ["(-8)**(1/3)", "(-8)^(1/3)"])
def test_power_notation_at_a_negative_base_is_a_convention(e):
    assert verdict(ev(e), sol("-2")) == "UNKNOWN"
    assert verdict(ev(e), sol(CPLX)) != "CORRECT"


@pytest.mark.parametrize("e", ["cbrt(-8)", "root(-8, 3)", r"\sqrt[3]{-8}", "∛(-8)", "real_root(-8, 3)"])
def test_a_written_root_is_the_real_root(e):
    assert verdict(ev(e), sol("-2")) == "CORRECT"
    assert verdict(ev(e), sol(CPLX)) == "INCORRECT"
    assert verdict(ev(e), sol("2*exp(I*pi/3)")) == "INCORRECT"


def test_two_values_are_never_both_certified():
    for e in ("(-1)**(1/3)", "(-8)**(2/3)", "(-8)**(-1/3)", "(-27)**(1/3)*(-8)**(1/3)"):
        got = {verdict(ev(e), sol(c)) for c in {"(-1)**(1/3)": ("-1", "1/2 + sqrt(3)*I/2"),
                                                 "(-8)**(2/3)": ("4", "-2 + 2*sqrt(3)*I"),
                                                 "(-8)**(-1/3)": ("-1/2", "1/4 - sqrt(3)*I/4"),
                                                 "(-27)**(1/3)*(-8)**(1/3)": ("6", "-3 + 3*sqrt(3)*I")}[e]}
        assert got == {"UNKNOWN"}, (e, got)


def test_a_symbol_bound_to_a_negative_number():
    assert verdict(ev("x**(1/3)", [X], ["x = -8"]), sol("-2")) == "UNKNOWN"
    assert verdict(ev("x**(1/3)", [X], ["x = -8"]), sol(CPLX)) != "CORRECT"
    assert verdict(ev("cbrt(x)", [X], ["x = -8"]), sol("-2")) == "CORRECT"
    assert verdict(ev("cbrt(x)", [X], ["x = -8"]), sol(CPLX)) != "CORRECT"
    assert verdict(ev("x**(1/3)", [X], ["x = 8"]), sol("2")) == "CORRECT"


def test_the_given_written_as_a_power_no_longer_refutes_the_real_root():
    assert verdict(ev("x", [X], ["x = (-8)**(1/3)"]), sol("-2")) == "UNKNOWN"
    assert verdict(ev("x", [X], ["x = cbrt(-8)"]), sol("-2")) == "CORRECT"
    assert verdict(solve("x = (-8)**(1/3)"), sol("{-2}", kind="set")) == "UNKNOWN"


def test_the_claim_written_as_a_power():
    assert verdict(ev("-2"), sol("(-8)**(1/3)")) == "UNKNOWN"
    assert verdict(ev("3"), sol("(-8)**(1/3)")) == "INCORRECT"        # wrong under both readings
    assert verdict(ev("x", [X], ["x = -2"]), sol("(-8)**(1/3)")) == "UNKNOWN"
    assert verdict(ev("-2"), sol("cbrt(-8)")) == "CORRECT"


def test_contradictory_steps_are_not_both_verified():
    v, st = step_statuses(ev("cbrt(-8)"), sol("-2", [("compute", "(-8)**(1/3) = -2"),
                                                     ("compute", f"(-8)**(1/3) = {CPLX}")]))
    assert "verified" not in st and "refuted" not in st, st
    v, st = step_statuses(ev("cbrt(-8)"), sol("-2", [("compute", "cbrt(-8) = -2"), ("compute", f"cbrt(-8) = {CPLX}")]))
    assert st == ["verified", "refuted"]


def test_odd_root_equations_and_inequalities():
    assert verdict(solve("x**(1/3) = x"), sol("{-1, 0, 1}", kind="set")) == "UNKNOWN"
    assert verdict(solve("x**(1/3) = x"), sol("{0, 1}", kind="set")) == "UNKNOWN"
    assert verdict(solve("x**(1/3) = 2"), sol("{}", kind="set")) == "INCORRECT"   # 8 is a root either way
    assert verdict(solve("x**(1/3) < 1", kind="solve_inequality"), sol("Interval.open(-oo, 1)", kind="interval")) \
        == "UNKNOWN"
    assert verdict(solve("cbrt(x) < 1", kind="solve_inequality"), sol("Interval.open(-oo, 1)", kind="interval")) \
        != "INCORRECT"
    assert verdict(solve("cbrt(x) = x"), sol("{0, 1}", kind="set")) == "INCORRECT"
    # z3 reads the written root, sign(x)·|x|**(1/3), and certifies the completeness the algebra cannot
    assert verdict(solve("cbrt(x) = -2"), sol("{-8}", kind="set")) == "CORRECT"
    assert verdict(solve("cbrt(x) = x"), sol("{-1, 0, 1}", kind="set")) == "CORRECT"


# ---------------------------------------------------------------------------- the step layer (D4-ADIM-K)
def test_premise_solved_under_both_readings():
    _, st = step_statuses(ev("x", [X], ["x**(1/3) = x"]), sol("x", [("compute", "Abs(x) = x")]))
    assert st != ["verified"]
    _, st = step_statuses(ev("x", [X], ["cbrt(x) = x"]), sol("x", [("compute", "Abs(x) = x")]))
    assert st == ["refuted"]                                    # x = -1 is an instance of the real root


def test_solved_both_readings_helper():
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.steps.deterministic import _solved_both_readings
    ctx = make_ctx(ProblemIR.from_dict(ev("x", [X], ["x**(1/3) = x"])))
    x = ctx.sym("x")
    got = _solved_both_readings(sp.Eq(x ** sp.Rational(1, 3), x), x, ctx)
    assert got == sp.FiniteSet(-1, 0, 1)


def test_an_instance_where_a_value_is_a_convention_blocks_verification():
    # n**2 = 4 next to C(n, 2): n = -2 is neither an instance nor excluded
    _, st = step_statuses(ev("binomial(n, 2)", [N], ["n**2 = 4"]), sol("1", [("eq", "n = 2")]))
    assert st != ["verified"]
    # x = 0 next to x**0 is not outside the domain
    _, st = step_statuses(ev("x**0 + x", [X], ["x**2 = 0"]), sol("1", [("eq", "x = 0")]))
    assert st != ["refuted"]


# ---------------------------------------------------------------------------- ℕ (CAP-N1)
@pytest.mark.parametrize("dod", ["ℕ", "N", "Naturals", "x ∈ ℕ", "x in N", r"\mathbb{N}"])
def test_naturals_without_a_mark_decide_only_when_both_readings_agree(dod):
    assert verdict(solve("x**2 - 3*x = 0", dod=dod), sol("{3}", kind="set")) == "UNKNOWN"
    assert verdict(solve("x**2 - 3*x = 0", dod=dod), sol("{0, 3}", kind="set")) == "UNKNOWN"


def test_naturals_agreeing_readings_and_unambiguous_spellings():
    assert verdict(solve("x**2 = 4", dod="ℕ"), sol("{2}", kind="set")) == "CORRECT"
    assert verdict(solve("x**2 = 4", dod="ℕ"), sol("{-2, 2}", kind="set")) == "INCORRECT"
    assert verdict(solve("x**2 = 0", dod="N0"), sol("{0}", kind="set")) == "CORRECT"
    assert verdict(solve("x**2 = 0", dod="ℕ0"), sol("{0}", kind="set")) == "CORRECT"
    assert verdict(solve("x**2 = 0", dod="Z+"), sol("{}", kind="set")) == "CORRECT"
    assert verdict(solve("x**2 - 3*x = 0", dod="ℕ⁺"), sol("{3}", kind="set")) == "CORRECT"
    r = verify(solve("x**2 = 0", dod="N+"), sol("{}", kind="set"))
    assert "layer_exception" not in r.flags and r.verdict == "CORRECT"


def test_naturals_in_counts_values_and_claims():
    cnt = {"task": {"kind": "count_integers", "params": {"var": "x"}}, "vars": [X], "givens": ["x <= 5"],
           "answer_shape": "count", "domain_of_discourse": "ℕ"}
    assert verdict(cnt, sol(5, kind="count")) == "UNKNOWN"
    assert verdict(cnt, sol(6, kind="count")) == "UNKNOWN"
    assert verdict(ev("x", [X], ["x*(x - 4) = 0"], dod="ℕ"), sol("4")) == "UNKNOWN"
    assert verdict(solve("x >= 0", dod="Integers", kind="solve_inequality"), sol("ℕ", kind="set")) == "UNKNOWN"
    assert verdict(ev("n", [{"name": "n", "domain": "natural"}], ["n*(n - 4) = 0"]), sol("4")) == "CORRECT"
    assert verdict(ev("N", [{"name": "N", "domain": "real"}], ["N = 3"]), sol("3")) == "CORRECT"


def test_naturals_rewriting():
    from mathverify.normalize.parse import number_set_named
    from mathverify.verifier import _bare_n_as_set, _naturals_zero_reading
    assert _bare_n_as_set("x in N") == "x in N0" and _bare_n_as_set("A N B") == "A N B"
    assert _naturals_zero_reading({"domain_of_discourse": "ℕ⁺"}, {"claimed_answer": {"payload": "N0"}}) is None
    assert _naturals_zero_reading({"domain_of_discourse": "ℕ"}, {})[0]["domain_of_discourse"] == "ℕ0"
    assert number_set_named("ℕ₀") == sp.S.Naturals0 and number_set_named("ℤ⁺") == sp.S.Naturals
    assert number_set_named("N_0") == sp.S.Naturals0


# ---------------------------------------------------------------------------- binomial (CAP-B1)
@pytest.mark.parametrize("vars_", [[N], [{"name": "n", "domain": "real"}]])
def test_generalized_binomial_is_a_convention(vars_):
    q = solve("binomial(n, 2) = 3", "n", vars_)
    assert verdict(q, sol("{-2, 3}", kind="set")) == "UNKNOWN"
    assert verdict(q, sol("{3}", kind="set")) == "UNKNOWN"
    assert verdict(q, sol("{-2}", kind="set")) == "INCORRECT"     # misses 3, a root under every reading
    assert verdict(q, sol("{}", kind="set")) == "INCORRECT"


def test_binomial_values_outside_the_curriculum():
    assert verdict(ev("binomial(n, 2)", [N], ["n**2 = 4"]), sol("1")) == "UNKNOWN"
    assert verdict(ev("n", [N], ["binomial(n, 2) = 3"]), sol("3")) == "UNKNOWN"
    assert verdict(ev("binomial(2, 5)"), sol("0")) == "UNKNOWN"
    assert verdict(solve("binomial(n, 2) = 0", "n", [N]), sol("{}", kind="set")) == "UNKNOWN"
    assert verdict(ev("binomial(5, 2)"), sol("10")) == "CORRECT"
    assert verdict(ev("10"), sol("binomial(5, 2) + binomial(2, 5)")) == "UNKNOWN"


# ---------------------------------------------------------------------------- 0**0 (G13)
@pytest.mark.parametrize("e", ["0**0", "0^0", "0**0 + 2", "(2 - 2)**0", "0**(3 - 3)*5", "0^{0}"])
def test_zero_to_the_zero_is_a_convention(e):
    assert verdict(ev(e), sol(str(sp.sympify(e.replace("^{0}", "**0").replace("^", "**"))))) == "UNKNOWN"


def test_zero_power_at_a_point_and_in_sets():
    assert verdict(ev("x**0", [X], ["x = 0"]), sol("1")) == "UNKNOWN"
    assert verdict(ev("a + 1", [{"name": "a", "domain": "real"}], ["a = 0**0"]), sol("2")) == "UNKNOWN"
    assert verdict(solve("x**0 = 1"), sol("Reals", kind="interval")) == "UNKNOWN"
    assert verdict(solve("x**0 = 1"), sol("Union(Interval.open(-oo, 0), Interval.open(0, oo))", kind="interval")) \
        == "UNKNOWN"
    assert verdict(solve("x**0 + x = 1"), sol("{0}", kind="set")) == "UNKNOWN"
    dom = {"task": {"kind": "domain_of", "params": {"expr": "(x - 1)**0", "var": "x"}}, "vars": [X], "givens": [],
           "answer_shape": "set"}
    assert verdict(dom, sol("Reals", kind="interval")) == "UNKNOWN"
    assert verdict(ev("Sum(0**k, (k, 0, 3))", [{"name": "k", "domain": "integer"}]), sol("1")) == "UNKNOWN"
    assert verdict(ev("5"), sol("0**0 + 4")) == "UNKNOWN"
    _, st = step_statuses(ev("x", [X], ["x = 2"]), sol("2", [("compute", "0**0 = 1")]))
    assert st != ["verified"]


def test_zero_power_away_from_zero():
    assert verdict(ev("5**0"), sol("1")) == "CORRECT"
    assert verdict(ev("x**0", [X], ["x = 3"]), sol("1")) == "CORRECT"
    assert verdict(solve("x**0 = 1", vars_=[XP]), sol("Interval.open(0, oo)", kind="interval")) == "CORRECT"


# ---------------------------------------------------------------------------- Mod (CAP-M1)
def test_negative_divisor_is_a_convention():
    for e, vals in (("Mod(7, -5)", ("-3", "2")), ("Mod(-7, -5)", ("-2", "3"))):
        assert {verdict(ev(e), sol(v)) for v in vals} == {"UNKNOWN"}
    G = ["n = Mod(7, m)", "floor(m/2) = -3", "Mod(m, 2) = 1"]
    assert {verdict(ev("n", [N, M], G), sol(v)) for v in ("2", "-3")} == {"UNKNOWN"}
    assert verdict(ev("n", [N], ["Mod(n, -5) = -3", "n >= 0", "n < 5"]), sol("2")) == "UNKNOWN"
    assert {verdict(ev("Mod(n, -5)", [N], ["n > 6", "n < 8"]), sol(v)) for v in ("2", "-3")} == {"UNKNOWN"}
    v, st = step_statuses(ev("n", [N], ["n = 1"]), sol("1", [("compute", "Mod(7, -5) = 2")]))
    assert st != ["refuted"] and v != "INCORRECT"
    assert verdict(ev("2"), sol("Mod(12, -5) + 5")) == "UNKNOWN"


def test_positive_divisor_keeps_its_reading():
    assert verdict(ev("Mod(-7, 5)"), sol("3")) == "CORRECT"
    assert verdict(ev("Mod(-7, 5)"), sol("-2")) == "INCORRECT"
    assert verdict(ev("n", [N], ["Mod(n, 5) = 2", "n >= 0", "n < 5"]), sol("2")) == "CORRECT"
    pos = [N, {"name": "m", "domain": "positive_integer"}]
    assert verdict(ev("n", pos, ["n = Mod(7, m)", "floor(m/2) = 2", "Mod(m, 2) = 1"]), sol("2")) == "CORRECT"


# ---------------------------------------------------------------------------- z3 (CAP-D1, CAP-Z1)
@pytest.mark.parametrize("dod", ["Integers", "Z", "ℤ", "x in Integers", "Complement(Integers, {0})", "N0"])
def test_z3_reads_an_integer_domain_of_discourse(dod):
    assert verdict(ev("x", [X], ["floor(x) + x = 5/2"], dod=dod), sol("3/2")) != "CORRECT"


def test_z3_integer_domain_controls():
    assert verdict(ev("x", [X], ["floor(x) + x = 5/2"], dod="Integers",
                      options={"A": "3/2", "B": "1", "C": "2"}), sol(None, option="A")) != "CORRECT"
    assert verdict(ev("x", [X], ["floor(x) + x = 4"], dod="Integers"), sol("2")) != "INCORRECT"
    assert verdict(ev("x", [X], ["floor(x) + x = 5/2"]), sol("3/2")) == "CORRECT"


@pytest.mark.parametrize("givens,claim", [(["x = 1", "x = 2"], "1"), (["x**2 = 4", "x > 2"], "2"),
                                          (["sqrt(x) = -1"], "1"), (["1/x = 0"], "1")])
def test_givens_without_an_instance_refute_nothing(givens, claim):
    r = verify(ev("x", [X], givens), sol(claim))
    assert r.verdict == "UNKNOWN" and "ir_inconsistent" in r.flags


def test_payload_and_option_letter_agree_on_inconsistent_givens():
    q = ev("x", [X], ["x = 1", "x = 2"], options={"A": "1", "B": "2"})
    assert {verdict(q, sol(None, option="A")), verdict(q, sol("1", option="A")),
            verdict(ev("x", [X], ["x = 1", "x = 2"]), sol("1"))} == {"UNKNOWN"}
    assert verdict(ev("n", [N], ["2*n = 3"]), sol("3/2")) == "UNKNOWN"
    assert verdict(ev("x", [X], ["x = 3"]), sol("4")) == "INCORRECT"


def test_claim_status_helper():
    from mathverify.certify.wordproblem import _claim_status
    assert _claim_status({"claim_sat": False, "other_unsat": True}) == "ir_inconsistent"
    assert _claim_status({"claim_sat": False, "other_unsat": False}) == "refuted"
    assert _claim_status({"claim_sat": False, "other_unsat": None, "status": "unknown"}) == "unknown"
    assert _claim_status({"claim_sat": True, "other_unsat": True}) == "certified"


def test_z3_bridge_refuses_conventions():
    from mathverify.certify._z3bridge import check_sat
    x = sp.Symbol("x", real=True)
    m = sp.Symbol("m", integer=True)
    n = sp.Symbol("n", integer=True)
    assert check_sat([sp.Eq(x, x ** sp.Rational(1, 3))], {"x": "real"}, [])[0] == "unsupported"
    assert check_sat([sp.Eq(n, sp.Mod(7, m))], {"n": "int", "m": "int"}, [])[0] == "unsupported"
    st, _ = check_sat([sp.Contains(x, sp.S.Integers, evaluate=False), sp.Eq(2 * x, 3)], {"x": "real"}, [])
    assert st == "unsat"


# ---------------------------------------------------------------------------- the mechanism
def test_convention_sets_are_never_false():
    from mathverify.certify.domain import (BINOMIAL_ARGUMENT, MOD_DIVISOR, ODD_ROOT_BASE, ZERO_POWER_BASE,
                                           convention_split, decide_membership, is_convention)
    for s, bad, good in ((ODD_ROOT_BASE, -8, 8), (ZERO_POWER_BASE, 0, 3), (BINOMIAL_ARGUMENT, -3, 2),
                         (MOD_DIVISOR, -5, 5)):
        assert decide_membership(sp.Integer(bad), s) is None
        assert decide_membership(sp.Integer(good), s) is True
        assert is_convention(sp.Contains(sp.Symbol("x"), s))
    x = sp.Symbol("x", real=True)
    assert convention_split(sp.Contains(x, ODD_ROOT_BASE), x) == (sp.Interval(0, sp.oo), sp.Interval.open(-sp.oo, 0))
    assert convention_split(sp.Contains(x - 1, ZERO_POWER_BASE), x)[1] == sp.FiniteSet(1)


def test_convention_split_closed_and_domain_of_expression():
    from mathverify.certify.domain import MOD_DIVISOR, ODD_ROOT_BASE, convention_split, domain_of_expression
    x = sp.Symbol("x", real=True)
    assert convention_split(sp.Contains(sp.Integer(-5), MOD_DIVISOR), x) == (sp.S.EmptySet, sp.S.Reals)
    assert convention_split(sp.Contains(sp.Integer(5), MOD_DIVISOR, evaluate=False), x) == (sp.S.Reals, sp.S.EmptySet)
    assert convention_split(sp.Contains(sp.Integer(2), ODD_ROOT_BASE, evaluate=False), x) == (sp.S.Reals, sp.S.EmptySet)
    dom, ev_ = domain_of_expression(x ** sp.Rational(1, 3), x)
    assert dom is None and ev_.get("error") == "convention_dependent_domain"


def test_convention_mode_of_the_equation_certificate():
    # x**0·(x - 1)·x = 0: {0, 1} if 0**0 = 1, {1} if undefined; x**0 + x = 1: {0} or no solution
    assert verdict(solve("x**0*(x - 1)*x = 0"), sol("{1}", kind="set")) == "UNKNOWN"
    assert verdict(solve("x**0*(x - 1)*x = 0"), sol("{0, 1}", kind="set")) == "UNKNOWN"
    assert verdict(solve("x**0*(x - 1)*x = 0"), sol("{0}", kind="set")) == "INCORRECT"   # misses 1
    assert verdict(solve("x**0 + x = 1"), sol("{}", kind="set")) == "UNKNOWN"


def test_odd_root_candidates_of_an_evaluation():
    # x**(1/3) = x, x != 0: x = 1 (principal) or x in {-1, 1} (real root)
    assert verdict(ev("x", [X], ["x**(1/3) = x", "x != 0"]), sol("1")) == "UNKNOWN"
    assert verdict(ev("x", [X], ["x**(1/3) = x", "x != 0"]), sol("-1")) == "UNKNOWN"
    _, st = step_statuses(ev("x**2", [X], ["x**(1/3) = x", "x != 0"]), sol("1", [("eq", "x >= 0")]))
    assert st != ["verified"]


def test_a_premise_set_reaching_a_convention_point_proves_nothing():
    # x(x - 1) = 0 next to x**0: x = 0 is an instance if 0**0 = 1, and "x >= 1" fails there
    v, st = step_statuses(ev("x**0 + x", [X], ["x*(x - 1) = 0"]), sol("2", [("eq", "x >= 1")]))
    assert st != ["verified"] and v == "UNKNOWN"
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.steps.deterministic import _set_counterexample
    ctx = make_ctx(ProblemIR.from_dict(ev("x**0 + x", [X], ["x*(x - 1) = 0"])))
    x = ctx.sym("x")
    assert _set_counterexample(x >= 1, [sp.Eq(x * (x - 1), 0)], x, ctx) == (None, False, False)


def test_a_definitional_assignment_at_a_convention_point_is_not_refuted():
    _, st = step_statuses(ev("x**0 + y", [X, {"name": "y", "domain": "real"}], ["y = 1"]),
                          sol("2", [("eq", "x = 0")]))
    assert st != ["refuted"]


def test_set_claims_with_an_odd_root_of_a_negative_number():
    q = {"task": {"kind": "solve_equation", "params": {"equation": "x**3 = -8", "var": "x"}}, "vars": [X],
         "givens": [], "answer_shape": "set"}
    assert verdict(q, sol("{(-8)**(1/3)}", kind="set")) == "UNKNOWN"     # was INCORRECT ("not real")
    assert verdict(q, sol("{cbrt(-8)}", kind="set")) == "CORRECT"


def test_comparison_engine_reads_odd_roots_both_ways():
    from mathverify.equiv import answers_equivalent, scalar_equal
    x = sp.Symbol("x", real=True)
    c = 2 * (-1) ** sp.Rational(1, 3)
    assert scalar_equal(c, -2) is None and scalar_equal(c, 1 + sp.sqrt(3) * sp.I) is None
    assert scalar_equal(c, 5) is False
    assert answers_equivalent(x ** sp.Rational(1, 3), sp.sign(x) * sp.Abs(x) ** sp.Rational(1, 3),
                              shape="expression", domain={x: sp.S.Reals})[0] is None
    assert answers_equivalent(x ** sp.Rational(1, 3), sp.sign(x) * sp.Abs(x) ** sp.Rational(1, 3),
                              shape="expression", domain={x: sp.Interval(0, sp.oo)})[0] is True
    # equal under the real root everywhere, not under the principal value: random points read the real root
    r = sp.Rational(1, 3)
    assert answers_equivalent(x ** r, -(-x) ** r, shape="expression", domain={x: sp.Interval(0, sp.oo)})[0] is None
    assert answers_equivalent((x ** 3) ** r, x, shape="expression", domain={x: sp.S.Reals})[0] is None
    der = {"task": {"kind": "derivative", "params": {"f": "cbrt(x)", "var": "x"}}, "vars": [X], "givens": [],
           "answer_shape": "expression"}
    assert verdict(der, sol("x**(-2/3)/3", kind="expression")) == "UNKNOWN"


def test_z3_reads_integrality_inside_an_intersection():
    from mathverify.certify.wordproblem import _set_as_relation
    x = sp.Symbol("x", real=True)
    rel = _set_as_relation(sp.Intersection(sp.S.Integers, sp.Interval(-10, 10), evaluate=False), x)
    assert rel.has(sp.Contains)


def test_lean_statement_refuses_conventions():
    from mathverify.formal.statement import build_statement
    assert build_statement(ev("0**0"), {"kind": "value", "payload": "1"}) is None
    assert build_statement(ev("binomial(2, 5)"), {"kind": "value", "payload": "0"}) is None
    dom = {"task": {"kind": "domain_of", "params": {"expr": "(x - 1)**0", "var": "x"}}, "vars": [X], "givens": [],
           "answer_shape": "set"}
    assert build_statement(dom, {"kind": "interval", "payload": "Reals"}) is None
    assert build_statement(ev("binomial(5, 2)"), {"kind": "value", "payload": "10"}) is not None


# ---------------------------------------------------------------------------- review of part d4a (attack A)
def simp(e, vars_=(X,)):
    return {"task": {"kind": "simplify_expression", "params": {"expr": e}}, "vars": list(vars_), "givens": [],
            "answer_shape": "expression"}


@pytest.mark.parametrize("e,claim", [("(x**3)**(1/3)", "Abs(x)"), ("x**(1/3)", "Abs(x)**(1/3)"),
                                     ("(x**5)**(1/5)", "Abs(x)"), ("((x - 1)**3)**(1/3)", "Abs(x - 1)"),
                                     ("x**(1/3)*x**(2/3)", "Abs(x)"), ("x**(1/3) + cbrt(x)", "2*Abs(x)**(1/3)"),
                                     (r"x^{\frac{1}{3}}", "Abs(x)**(1/3)")])
def test_a_claim_true_on_the_nonnegative_side_only_is_refuted(e, claim):
    # wrong at x = -2 under both readings (real root -2, principal value 2·e^{iπ/3}, against 2)
    assert verdict(simp(e), sol(claim, kind="expression")) == "INCORRECT"


def test_evaluate_without_givens_reads_the_convention_points():
    assert verdict(ev("(a**3)**(1/3)", [{"name": "a", "domain": "real"}]), sol("Abs(a)", kind="expression")) \
        == "INCORRECT"


@pytest.mark.parametrize("e,claim", [("x**(1/3)", "cbrt(x)"), ("x**(2/3)", "cbrt(x)**2"), ("(x**3)**(2/3)", "x**2"),
                                     ("x**(1/3)*x**(2/3)", "x"), ("(x**3)**(1/3) + x", "2*x"),
                                     ("x**(2/3)", "Abs(x)**(2/3)")])
def test_a_claim_true_under_one_reading_only_decides_nothing(e, claim):
    assert verdict(simp(e), sol(claim, kind="expression")) == "UNKNOWN"


def test_no_value_convention_keeps_the_verdict():
    assert verdict(simp("x**(1/3)*x**(2/3)", [XP]), sol("x", kind="expression")) == "CORRECT"
    assert verdict(simp("cbrt(x)**3"), sol("x", kind="expression")) == "CORRECT"
    assert verdict(simp("x**0"), sol("1", kind="expression")) == "CORRECT"


def test_convention_counterexample_helper():
    from mathverify.certify.base import convention_counterexample, make_ctx
    from mathverify.ir import ProblemIR
    ctx = make_ctx(ProblemIR.from_dict(simp("(x**3)**(1/3)")))
    x = ctx.sym("x")
    t = (x ** 3) ** sp.Rational(1, 3)
    present, pt = convention_counterexample(ctx, sp.Abs(x), t, [x])
    assert present and pt is not None and sp.sympify(pt["x"]) < 0
    present, pt = convention_counterexample(ctx, x, t, [x])
    assert present and pt is None
    assert ctx.value_convention_region(x) == sp.Interval.open(-sp.oo, 0)
    ctx2 = make_ctx(ProblemIR.from_dict(simp("x**0")))
    assert convention_counterexample(ctx2, sp.Integer(1), sp.Integer(1), [ctx2.sym("x")]) == (False, None)


def test_a_variable_named_n_next_to_the_set_n():
    q = {**solve("x**2 - 3*x = 0", dod="N"), "vars": [X, {"name": "N", "domain": "real"}]}
    r = verify(q, sol("{3}", kind="set"))
    assert r.verdict == "UNKNOWN" and "naturals_convention" in r.flags
    assert verdict(ev("N", [{"name": "N", "domain": "real"}], ["N = 3"]), sol("3")) == "CORRECT"


def test_z3_reads_the_written_real_root():
    """The z3 layer itself certifies cbrt(x) = -2 → {-8}: it reads sign(x)·|x|**(1/3). Since round 5 of
    part d4b the algebra layer proves it too (the cells of sign and Abs), so the verdict alone no longer
    shows the bridge (mutation Z08 survived)."""
    r = verify(solve("cbrt(x) = -2"), sol("{-8}", kind="set"))
    assert next(la for la in r.layers if la.layer == "certify.wordproblem").verdict == "pass"


def test_evaluate_with_a_root_only_the_principal_reading_has():
    """(x - 8)(x**(2/3) - x**(1/3) + 1) = 0: the real root reads t**2 - t + 1 > 0, so x = 8 alone; on the
    principal branch x = -1 is a root too ((-1)**(1/3) = e^{iπ/3}, e^{2iπ/3} - e^{iπ/3} + 1 = 0). The
    candidates of the real reading leave -1 out, so `_filter_solutions` never sees it: the guard of
    `_verify_evaluate` on a written odd root (mutation A05) is what keeps 8 from being certified (round 6
    of part d4b, 6 Oct 2026: without it 8 was CORRECT)."""
    g = ["(x - 8)*(x**(2/3) - x**(1/3) + 1) = 0"]
    assert verdict(ev("x", [X], g), sol("8")) == "UNKNOWN"
    assert verdict(ev("x**2", [X], g), sol("64")) == "UNKNOWN"
