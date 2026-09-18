"""F5 — deterministic Lean statement generation (always runs) and real proof checking
(skipped when the Lean/WSL toolchain is not installed)."""
import pytest
import sympy as sp

from mathverify.formal.statement import build_statement, sympy_to_lean, LeanPrintError, relation_to_lean
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
