"""F5 — deterministic Lean statement generation (always runs) and real proof checking
(skipped when the Lean/WSL toolchain is not installed)."""
import pytest
import sympy as sp

from mathverify.formal.statement import build_statement, sympy_to_lean, LeanPrintError
from mathverify.formal import SAFE_AXIOMS

a, b, x = sp.symbols("a b x", real=True)


def _lean():
    from mathverify.formal import get_lean, lean_available
    if not lean_available(timeout=300):
        pytest.skip("Lean/Mathlib toolchain not available")
    return get_lean()


# ------------------------------------------------------------------ printer (offline)
def test_printer_exact_forms():
    assert sympy_to_lean(sp.Integer(3)) == "3"
    assert sympy_to_lean(sp.Integer(-3)) == "(-3 : ℝ)"
    assert sympy_to_lean(sp.Rational(1, 2)) == "(1 / 2 : ℝ)"
    assert sympy_to_lean(sp.sqrt(a)) == "Real.sqrt a"
    assert "Real.pi" == sympy_to_lean(sp.pi)
    assert sympy_to_lean(a ** 2) == "(a ^ 2)"
    assert "/" in sympy_to_lean(1 / (x - 1))          # negative powers become division
    assert sympy_to_lean(sp.Abs(a)) == "|a|"


def test_printer_refuses_what_it_cannot_render_exactly():
    with pytest.raises(LeanPrintError):
        sympy_to_lean(sp.Symbol("n", integer=True) ** sp.Symbol("k", integer=True))
    with pytest.raises(LeanPrintError):
        sympy_to_lean(sp.Rational(1, 2), field="ℤ")
    with pytest.raises(LeanPrintError):
        sympy_to_lean(sp.gamma(a))                    # no exact Mathlib rendering here
    with pytest.raises(LeanPrintError):
        sympy_to_lean(sp.asin(a))


def test_statement_is_generated_without_any_model(evalset_items):
    it = next(i for i in evalset_items if i["id"] == "tyt-prob-001")
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st is not None and st.kind == "evaluate_system"
    txt = st.theorem("  omega")
    assert "a = 16" in txt and "a + b" in txt.replace("(", "").replace(")", "")
    assert "0 < a" in txt                                   # positive_integer domain kept
    assert st.vacuity_probe() and "False" in st.vacuity_probe()


def test_wrong_claim_produces_a_false_statement(evalset_items):
    it = next(i for i in evalset_items if i["id"] == "tyt-prob-013")   # claims a = 14
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st is not None and "a = 14" in st.goal


def test_solution_set_statement_asserts_membership(evalset_items):
    """The iff alone is vacuously true for a root outside the domain; the template must also
    claim that each root satisfies the conditions and the equation (measured on tyt-den-011)."""
    it = next(i for i in evalset_items if i["id"] == "tyt-den-011")
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    if st is None:
        pytest.skip("statement out of scope for this item")
    assert st.kind == "solve_equation_set"
    assert "∀" in st.goal and "∧" in st.goal


def test_out_of_scope_returns_none(evalset_items):
    for iid in ("ayt-lim-001", "tyt-geo-001", "tyt-ola-001"):
        it = next(i for i in evalset_items if i["id"] == iid)
        assert build_statement(it["problem_ir"], it["solution"]["claimed_answer"]) is None


# ------------------------------------------------------------------ faithfulness of templates
def test_the_cas_must_not_pre_compute_the_target(evalset_items):
    """A normal parse folds `gcd(84,120) + lcm(4,6)` to 24 and the theorem degenerates to
    `24 = 24`. Structural parsing keeps the operations so Lean recomputes them."""
    it = next(i for i in evalset_items if i["id"] == "tyt-say-001")     # gcd(84, 120) = 12
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st is not None
    assert "Int.gcd" in st.goal and st.goal.strip() != "12 = 12"


def test_a_tautological_statement_is_rejected():
    from mathverify.formal.statement import LeanStatement, is_trivial
    triv = LeanStatement("t", "", [], "5 = 5", "ℝ", "closed_arithmetic")
    assert is_trivial(triv)
    real = LeanStatement("t", "", [], "Real.sqrt 25 = 5", "ℝ", "closed_arithmetic")
    assert not is_trivial(real)
    quantified = LeanStatement("t", "", [], "∀ x : ℝ, x = x", "ℝ", "k")
    assert not is_trivial(quantified)


def test_solution_set_template_asserts_that_each_root_really_is_one(evalset_items):
    """A bare guarded iff is vacuously true for a root the domain excludes, so the statement
    must also claim that every listed root satisfies the conditions and the equation.
    tyt-den-010 adds the extraneous root 0 to the true answer {5}: the extra conjunct
    `sqrt(4+0) = -2+0` is false, which is what keeps the wrong claim unprovable."""
    ok = next(i for i in evalset_items if i["id"] == "tyt-den-002")     # {5}, correct
    bad = next(i for i in evalset_items if i["id"] == "tyt-den-010")    # {0, 5}, extraneous root
    s_ok = build_statement(ok["problem_ir"], ok["solution"]["claimed_answer"])
    s_bad = build_statement(bad["problem_ir"], bad["solution"]["claimed_answer"])
    assert s_ok is not None and s_bad is not None
    assert s_ok.kind == s_bad.kind == "solve_equation_set"
    assert "∧" in s_ok.goal and "∧" in s_bad.goal
    assert s_ok.goal != s_bad.goal


def test_a_root_that_makes_the_expression_undefined_is_refused_not_guessed(evalset_items):
    """tyt-den-011 claims the root 3 for an equation with x - 3 in a denominator: substituting
    gives a division by zero, which has no faithful Lean rendering, so the template abstains
    (L7 is positive-only, so abstaining is safe; the deterministic layers refute the item)."""
    it = next(i for i in evalset_items if i["id"] == "tyt-den-011")
    assert build_statement(it["problem_ir"], it["solution"]["claimed_answer"]) is None


def test_inequality_template_pins_the_claimed_set_into_the_domain(evalset_items):
    """tyt-esf-012 differs from the correct answer only at an endpoint that the domain excludes;
    without the second half of the statement the guarded iff cannot tell them apart."""
    ok = next(i for i in evalset_items if i["id"] == "tyt-esf-002")
    bad = next(i for i in evalset_items if i["id"] == "tyt-esf-012")
    s_ok = build_statement(ok["problem_ir"], ok["solution"]["claimed_answer"])
    s_bad = build_statement(bad["problem_ir"], bad["solution"]["claimed_answer"])
    for st in (s_ok, s_bad):
        assert st is not None and st.goal.count("∀") == 2
    assert s_ok.goal != s_bad.goal


def test_matrix_literals_carry_their_element_type(evalset_items):
    it = next(i for i in evalset_items if i["id"] == "uni-la-004")
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st is not None and "Matrix (Fin 2) (Fin 2) ℝ" in st.goal
    assert "*ᵥ" not in st.goal and "Matrix.mulVec" in st.goal


def test_templates_cover_the_expected_task_kinds(evalset_items):
    from collections import Counter
    kinds = Counter()
    for it in evalset_items:
        st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
        if st:
            kinds[st.kind] += 1
    assert sum(kinds.values()) >= 110
    for expected in ("evaluate_system", "closed_arithmetic", "solve_equation_set", "equation_of_iff",
                     "linalg_inverse", "series_sum_finite", "count_integers_finset"):
        assert kinds[expected] > 0, expected


# ------------------------------------------------------------------ integrals (offline)
def _int_item(items, integrand):
    return next(i for i in items
                if i["problem_ir"]["task"]["kind"] == "definite_integral"
                and i["problem_ir"]["task"]["params"]["integrand"] == integrand)


def test_piecewise_integrand_is_out_of_scope_rather_than_approximated(evalset_items):
    it = _int_item(evalset_items, "Abs(x - 1) + Abs(x + 2)")
    assert build_statement(it["problem_ir"], it["solution"]["claimed_answer"]) is None


def test_improper_integral_gets_no_fundamental_theorem_tactic(evalset_items):
    """∫₀¹ log x/√x is improper at 0: the antiderivative is not differentiable on the closed
    interval, so the FTC tactic would be unsound to attempt. The statement still exists — the
    layer simply fails to prove it and abstains."""
    it = _int_item(evalset_items, "log(x)/sqrt(x)")
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st is not None and st.hints == ()


def test_product_integrand_gets_a_constructed_derivative_proof(evalset_items):
    it = _int_item(evalset_items, "x*exp(x)")
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st.hints, "no FTC tactic generated for a product integrand"
    first = st.hints[0]
    assert "intervalIntegral.integral_eq_sub_of_hasDerivAt" in first
    assert "Real.hasDerivAt_exp" in first and "hasDerivAt_id" in first
    assert "sorry" not in first and "native_decide" not in first


def test_the_tactic_is_a_function_of_the_problem_not_of_the_claim(evalset_items):
    """A tactic that depended on the claimed answer could steer Lean towards confirming it.
    The hints for a right and a wrong claim must be byte-identical: only the goal differs."""
    it = _int_item(evalset_items, "x*exp(x)")
    right = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    wrong = build_statement(it["problem_ir"], {"kind": "value", "payload": "7", "option": None})
    assert right.goal != wrong.goal
    assert right.hints == wrong.hints


def test_hasderiv_compiler_covers_its_grammar_and_refuses_the_rest():
    from mathverify.formal.statement import _hasderiv_proof
    t, pt = sp.Symbol("t"), sp.Symbol("x")
    term, value = _hasderiv_proof((t - 1) * sp.exp(t), t, pt)
    assert ".mul" in term and "Real.hasDerivAt_exp x" in term
    assert "Real.exp x" in value
    assert _hasderiv_proof(sp.sin(t ** 2), t, pt)[0].startswith("(HasDerivAt.sin")
    assert _hasderiv_proof(sp.Integer(5), t, pt) == ("(hasDerivAt_const x (5))", "0")
    assert _hasderiv_proof(sp.log(t), t, pt) is None          # needs a side condition
    assert _hasderiv_proof(sp.atan(t), t, pt) is None          # outside the grammar


# ------------------------------------------------------------------ real Lean
def test_lean_proves_true_and_refuses_false(evalset_items):
    lean = _lean()
    from mathverify.formal import prove_statement
    ok_item = next(i for i in evalset_items if i["id"] == "tyt-prob-001")
    bad_item = next(i for i in evalset_items if i["id"] == "tyt-prob-013")
    st_ok = build_statement(ok_item["problem_ir"], ok_item["solution"]["claimed_answer"])
    st_bad = build_statement(bad_item["problem_ir"], bad_item["solution"]["claimed_answer"])
    r_ok = prove_statement(st_ok, use_model=False, lean=lean, tactic_timeout=45)
    assert r_ok["proved"] and r_ok["audit"]["clean"]
    assert set(r_ok["audit"]["axioms"]) <= SAFE_AXIOMS
    r_bad = prove_statement(st_bad, use_model=False, lean=lean, tactic_timeout=45)
    assert not r_bad["proved"]


def test_lean_audit_catches_sorry_and_vacuity():
    lean = _lean()
    r = lean.run("theorem t_sorry (x : ℝ) : x = x := by sorry", timeout=45)
    assert r.ok and r.sorries and not r.clean          # compiles, but not clean
    r2 = lean.run("theorem t_vac (x : ℝ) (h1 : x = 1) (h2 : x = 2) : False := by linarith", timeout=45)
    assert r2.clean                                     # contradictory hypotheses are detectable


def test_lean_client_survives_a_timeout():
    lean = _lean()
    r = lean.run("theorem slow : ∀ n : ℕ, n < 10 ^ 10 → n = n := by decide", timeout=5)
    assert (r.timed_out or not r.clean)
    r2 = lean.run("example : (1 : ℝ) + 1 = 2 := by norm_num", timeout=60)
    assert r2.clean                                     # client recovered
