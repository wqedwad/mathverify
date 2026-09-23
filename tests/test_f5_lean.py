"""F5 — deterministic Lean statement generation (always runs) and real proof checking
(skipped when the Lean/WSL toolchain is not installed)."""
import copy

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


def test_improper_integral_gets_no_statement(evalset_items):
    """∫₀¹ log x/√x is improper at 0. It used to get a statement without FTC hints and simply
    fail to prove; now the integrand must be defined on the whole closed interval, because
    Mathlib's interval integral of a non-integrable function is 0 by definition and an
    improper integral is exactly where a junk value can enter. Nothing was ever certified
    here, so no coverage is lost (measured: 4 statements dropped, 0 certificates)."""
    it = _int_item(evalset_items, "log(x)/sqrt(x)")
    assert build_statement(it["problem_ir"], it["solution"]["claimed_answer"]) is None


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
    term, sides = _hasderiv_proof((t - 1) * sp.exp(t), t, pt)
    assert ".mul" in term and "Real.hasDerivAt_exp (x)" in term and sides == []
    assert _hasderiv_proof(sp.sin(t ** 2), t, pt)[0].startswith("(HasDerivAt.sin")
    assert _hasderiv_proof(sp.Integer(5), t, pt) == ("(hasDerivAt_const (x) (5))", [])
    assert _hasderiv_proof(sp.atan(t), t, pt) is None           # outside the grammar


def test_a_side_condition_is_proved_not_assumed():
    """`Real.log` is only differentiable away from 0. The compiler records that as its own Lean
    goal, so Lean proves it — it is never silently taken for granted."""
    from mathverify.formal.statement import _hasderiv_proof, _hasderiv_block
    t, pt = sp.Symbol("t"), sp.Symbol("x")
    built = _hasderiv_proof(t * sp.log(t), t, pt)
    assert built[1] == ["x"], built
    block = "\n".join(_hasderiv_block(built, 2, ("hg0",)))
    assert "have hs0 : (x) ≠ 0 := by" in block
    assert "sorry" not in block and "assumption; done" in block


def test_derivative_becomes_hasderivat_not_a_deriv_equation(evalset_items):
    """`deriv f a = v` is vacuously true where f is not differentiable; `HasDerivAt` is not.
    The stronger form is the one that may hand out a certificate."""
    it = next(i for i in evalset_items if i["id"] == "ayt-tur-002")
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st.goal.startswith("HasDerivAt ") and "deriv " not in st.goal
    assert "Real.exp" in st.goal and st.kind == "derivative_at"
    wrong = build_statement(it["problem_ir"], {"kind": "value", "payload": "7", "option": None})
    assert wrong.goal != st.goal and wrong.hints == st.hints


def test_antiderivative_states_the_derivative_claim_with_its_own_guard(evalset_items):
    """"∫ log x dx = x log x − x + C" is the claim that the derivative of the right-hand side is
    log x wherever both sides exist. The excluded point comes from SymPy's singularity set of the
    two expressions, never from the claim."""
    it = next(i for i in evalset_items
              if i["problem_ir"]["task"]["kind"] == "antiderivative" and i["id"] == "ayt-int-001")
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st.goal.startswith("∀ x : ℝ, x ≠ 0 → HasDerivAt ")
    assert "Real.log x" in st.goal and "+ C" not in st.goal and "C" not in st.goal.split("=>")[1]
    assert st.kind == "antiderivative_hasderiv" and st.hints


def test_a_wrong_antiderivative_still_gets_a_statement_to_fail_on(evalset_items):
    it = next(i for i in evalset_items if i["id"] == "ayt-int-014")      # claims 1/x + C
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st is not None and "1 / t" in st.goal
    assert st.hints == ()            # 1/t is outside the compiler's grammar: no tactic, no proof


# ------------------------------------------------------------------ counting (offline)
def test_counting_statements_use_leans_own_definitions(evalset_items):
    """`Nat.factorial 5 = 120` would only confirm our choice of formula. The theorem has to be
    about the objects themselves: permutations, k-subsets, injections."""
    by_id = {i["id"]: i for i in evalset_items}
    want = {"tyt-ola-002": "Fintype.card (Equiv.Perm (Fin 5)) = 120",
            "tyt-ola-003": "((Finset.univ : Finset (Fin 6)).powersetCard 3).card = 20",
            "tyt-ola-004": "Fintype.card (Fin 3 ↪ Fin 5) = 60"}
    for item_id, goal in want.items():
        it = by_id[item_id]
        st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
        assert st is not None and st.goal == goal, (item_id, st.goal if st else None)
        assert "factorial" not in st.goal and "choose" not in st.goal
        assert st.hints


def test_a_filtered_count_is_out_of_scope_rather_than_approximated(evalset_items):
    it = next(i for i in evalset_items if i["problem_ir"]["task"]["kind"] == "count_structures")
    ir = copy.deepcopy(it["problem_ir"])
    ir["task"]["params"]["predicate"] = "x % 2 == 0"
    assert build_statement(ir, it["solution"]["claimed_answer"]) is None


def test_probability_items_get_no_lean_statement(evalset_items):
    """Translating the event predicate is where an unfaithful statement would come from, so the
    layer declines and abstains instead of guessing."""
    for it in evalset_items:
        if it["problem_ir"]["task"]["kind"] == "probability":
            assert build_statement(it["problem_ir"], it["solution"]["claimed_answer"]) is None


def test_a_wrong_count_gets_a_statement_that_is_simply_false(evalset_items):
    it = next(i for i in evalset_items if i["id"] == "tyt-ola-013")          # claims 25, not 120
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st is not None and st.goal.endswith("= 25")


# ------------------------------------------------------------------ recurrences (offline)
def test_recurrence_states_the_data_as_hypotheses_not_as_a_computation(evalset_items):
    it = next(i for i in evalset_items if i["id"] == "ayt-diz-001")     # a(6)=43, order 2
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st is not None and st.kind == "recurrence_term"
    assert st.binders == "(a : ℕ → ℝ)"
    assert st.hypotheses[:2] == ["a 1 = 1", "a 2 = 3"]
    assert st.hypotheses[2].startswith("∀ n : ℕ, 3 ≤ n → a n =")
    assert "a (n - 1)" in st.hypotheses[2] and "a (n - 2)" in st.hypotheses[2]
    assert st.goal == "a 6 = 43"
    # no intermediate term is handed to Lean: it has to iterate the recurrence itself
    for value in ("7", "17", "23"):
        assert f"= {value}" not in st.goal and all(f"= {value}" not in h for h in st.hypotheses)
    assert st.vacuity_probe() and st.no_hyp_probe("  linarith")


def test_recurrence_claim_only_changes_the_goal(evalset_items):
    right = next(i for i in evalset_items if i["id"] == "ayt-diz-001")
    wrong = next(i for i in evalset_items if i["id"] == "ayt-diz-012")   # same problem, claims 21
    a = build_statement(right["problem_ir"], right["solution"]["claimed_answer"])
    b = build_statement(wrong["problem_ir"], wrong["solution"]["claimed_answer"])
    assert a.hypotheses == b.hypotheses and a.hints == b.hints
    assert a.goal == "a 6 = 43" and b.goal == "a 6 = 21"


def test_recurrence_out_of_scope_cases_are_declined(evalset_items):
    it = next(i for i in evalset_items if i["id"] == "ayt-diz-001")
    far = copy.deepcopy(it["problem_ir"])
    far["task"]["params"]["index"] = 500                      # would unroll 498 tactic lines
    assert build_statement(far, it["solution"]["claimed_answer"]) is None
    gappy = copy.deepcopy(it["problem_ir"])
    gappy["task"]["params"]["initial"] = {"1": "1", "3": "3"}  # not contiguous: cannot iterate
    assert build_statement(gappy, it["solution"]["claimed_answer"]) is None


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


# ------------------------------------------------------------------ L7 inside the fusion (B9)
# `l7_layer` was reachable only from verify_cli and run_pipeline(use_l7=True); no harness set
# that flag and no test imported it, so the mapping from a Lean record to a LayerResult — the
# part that decides whether a proof may ground CORRECT — was never exercised. These tests pin
# it without needing the toolchain.
_IR_EVAL = {"task": {"kind": "evaluate", "params": {"expr": "gcd(84, 120)"}}, "vars": [],
            "givens": [], "answer_shape": "scalar"}
_CLAIM_OK = {"kind": "value", "payload": "12", "option": None}


def _fake_prove(monkeypatch, *, proved, clean):
    import mathverify.formal.prove as P

    def fake(stmt, **kw):
        return {"statement": "theorem mv_claim : True", "kind": stmt.kind, "proved": proved,
                "proof": "  norm_num" if proved else None, "source": "tactic_ladder",
                "attempts": [], "audit": ({"clean": clean, "axioms": [], "axioms_ok": True,
                                           "sorry_free": True} if proved else {}),
                "calls": 0, "cost_usd": 0.0, "errors": [], "ms": 1.0}
    monkeypatch.setattr(P, "prove_statement", fake)


def test_a_clean_lean_proof_is_a_primary_certificate(monkeypatch):
    from mathverify.formal import l7_layer
    from mathverify.fuse import fuse
    _fake_prove(monkeypatch, proved=True, clean=True)
    lr, _ = l7_layer(_IR_EVAL, {"claimed_answer": _CLAIM_OK, "steps": []}, use_model=False)
    assert (lr.verdict, lr.hard, lr.primary) == ("pass", True, True)
    assert fuse([lr])["verdict"] == "CORRECT"


def test_a_proof_that_fails_its_audit_grounds_nothing(monkeypatch):
    from mathverify.formal import l7_layer
    from mathverify.fuse import fuse
    _fake_prove(monkeypatch, proved=True, clean=False)
    lr, _ = l7_layer(_IR_EVAL, {"claimed_answer": _CLAIM_OK, "steps": []}, use_model=False)
    assert lr.verdict == "unknown" and not lr.primary and "lean_audit_failed" in lr.flags
    assert fuse([lr])["verdict"] == "UNKNOWN"


def test_failing_to_prove_is_never_evidence_against_the_claim(monkeypatch):
    from mathverify.formal import l7_layer
    from mathverify.fuse import fuse
    _fake_prove(monkeypatch, proved=False, clean=False)
    lr, _ = l7_layer(_IR_EVAL, {"claimed_answer": _CLAIM_OK, "steps": []}, use_model=False)
    assert lr.verdict == "unknown" and "lean_unproved" in lr.flags
    assert fuse([lr])["verdict"] == "UNKNOWN"


def test_a_lean_certificate_does_not_rescue_a_refuted_step(monkeypatch):
    """The D cell, measured: 24 items with a broken step still get a Lean certificate, because
    the formal layer certifies the ANSWER. The step refuter's veto must win, or the formal
    layer would quietly turn every D item into CORRECT."""
    from mathverify.formal import l7_layer
    from mathverify.fuse import fuse
    from mathverify.types import LayerResult
    _fake_prove(monkeypatch, proved=True, clean=True)
    lr, _ = l7_layer(_IR_EVAL, {"claimed_answer": _CLAIM_OK, "steps": []}, use_model=False)
    refuted = LayerResult("steps.refute", "fail", 0.99, True, {"reason": "counterexample"}, 1.0,
                          primary=False, first_bad_step=1, flags=["step_refuted"])
    out = fuse([lr, refuted])
    assert out["verdict"] == "INCORRECT" and out["first_bad_step"] == 1


def test_out_of_scope_items_abstain_without_touching_lean():
    from mathverify.formal import l7_layer
    ir = {"task": {"kind": "probability", "params": {"space": {}, "event": "x"}}, "vars": [],
          "givens": [], "answer_shape": "scalar"}
    lr, rec = l7_layer(ir, {"claimed_answer": _CLAIM_OK, "steps": []}, use_model=False)
    assert lr.verdict == "unknown" and rec["calls"] == 0


# ------------------------------------------------------------------ junk values (Lean totality)
# Lean totalises every partial operation: x/0 = 0, Real.sqrt of a negative = 0, Real.log 0 = 0,
# Real.tan (π/2) = 0, and the interval integral of a non-integrable function is 0. Before these
# guards, five of the claims below received CLEAN, audited certificates, and with --lean the
# first came out of the whole verifier as CORRECT (0.995). See the section in statement.py.
def _ir(kind, params, vars_=(), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": [dict(v) for v in vars_],
            "givens": list(givens), "answer_shape": shape}


JUNK_CLAIMS = [
    ("tan(pi/2) = 0", _ir("evaluate", {"expr": "tan(pi/2)"}), "0"),
    ("sqrt(2-5) = 0", _ir("evaluate", {"expr": "sqrt(2 - 5)"}), "0"),
    ("0/0 = 0", _ir("evaluate", {"expr": "(2**2 - 4)/(2 - 2)"}), "0"),
    ("log 0 = 0", _ir("evaluate", {"expr": "log(0)"}), "0"),
    ("claim-side sqrt(-4)", _ir("evaluate", {"expr": "sin(0)"}), "sqrt(-4)"),
    ("int 1/x over [-1,1]", _ir("definite_integral", {"integrand": "1/x", "var": "x", "a": "-1", "b": "1"},
                                [{"name": "x"}]), "0"),
    ("sqrt'(-1)", _ir("derivative", {"f": "sqrt(x)", "var": "x", "at": "-1"}, [{"name": "x"}]), "0"),
    ("log'(-1)", _ir("derivative", {"f": "log(x)", "var": "x", "at": "-1"}, [{"name": "x"}]), "-1"),
    ("max -1/x^2 on [-1,1]", _ir("extremum", {"f": "-1/x**2", "var": "x", "interval": "[-1, 1]",
                                              "which": "max"}, [{"name": "x"}]), "0"),
    ("sum 1/k, k=-1..1", _ir("series_sum", {"term": "1/k", "var": "k", "lo": "-1", "hi": "1"},
                             [{"name": "k", "domain": "integer"}]), "0"),
    ("f nowhere defined", _ir("derivative", {"f": "sqrt(-x**2 - 1)", "var": "x"}, [{"name": "x"}],
                              shape="expression"), "0"),
]


@pytest.mark.parametrize("label,ir,claim", JUNK_CLAIMS, ids=[c[0] for c in JUNK_CLAIMS])
def test_no_statement_is_built_on_a_junk_value(label, ir, claim):
    st = build_statement(ir, {"kind": "value" if ir["answer_shape"] == "scalar" else "expression",
                              "payload": claim})
    assert st is None, f"{label}: a Lean statement would be about a junk value: {st and st.goal}"


def test_an_open_partial_operation_in_the_givens_becomes_a_guard_hypothesis():
    """`1/(x-2) = 0` holds at x = 2 in Lean. With the guard the hypotheses contradict each other,
    which is exactly what the vacuity probe is there to notice."""
    st = build_statement(_ir("evaluate", {"expr": "x"}, [{"name": "x"}], ["1/(x - 2) = 0"]),
                         {"kind": "value", "payload": "2"})
    assert st is not None
    assert any("≠ 0" in h for h in st.hypotheses), st.hypotheses


def test_the_printer_refuses_a_closed_value_outside_its_domain():
    for bad in (sp.sqrt(sp.Integer(-3), evaluate=False), sp.log(sp.Integer(0), evaluate=False),
                sp.tan(sp.pi / 2, evaluate=False), sp.Mul(1, sp.Pow(0, -1, evaluate=False), evaluate=False)):
        with pytest.raises(LeanPrintError):
            sympy_to_lean(bad)
    assert sympy_to_lean(sp.sqrt(sp.Integer(4), evaluate=False)) == "Real.sqrt 4"
    assert sympy_to_lean(sp.log(sp.Integer(2), evaluate=False)) == "Real.log 2"


def test_every_vacuity_probe_alternative_must_close_the_goal():
    """`first` commits to the first alternative that RUNS; `norm_num at *` runs without closing
    and used to shadow everything after it. Every alternative now ends in `done`."""
    st = build_statement(_ir("evaluate", {"expr": "x"}, [{"name": "x"}], ["1/(x - 2) = 0"]),
                         {"kind": "value", "payload": "2"})
    body = st.vacuity_probe().split(":= by", 1)[1].strip()
    assert body.startswith("first | ")
    alts, depth, cur = [], 0, ""
    for ch in body[len("first | "):]:                  # split on top-level `|`
        depth += (ch == "(") - (ch == ")")
        if ch == "|" and depth == 0:
            alts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    alts.append(cur.strip())
    assert len(alts) > 5
    bad = [a for a in alts if not (a.startswith("(") and a.endswith("done)"))]
    assert not bad, bad


def test_lean_sees_the_contradiction_the_guard_creates():
    from mathverify.formal.prove import prove_statement
    lean = _lean()
    st = build_statement(_ir("evaluate", {"expr": "x"}, [{"name": "x"}], ["1/(x - 2) = 0"]),
                         {"kind": "value", "payload": "2"})
    r = prove_statement(st, use_model=False, lean=lean, tactic_timeout=45)
    assert not (r["proved"] and r["audit"].get("clean")), "a system with no solution was certified"
