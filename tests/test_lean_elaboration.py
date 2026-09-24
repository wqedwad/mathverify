"""autoImplicit off on every Lean command the verifier sends for a statement.

Lean's default is autoImplicit ON: an unknown single-word identifier in a declaration header is
silently bound as an implicit variable instead of being an error. prove_statement used to compile
the theorem and both audit probes that way, and the reviewer's statement
`(x : ℝ) (h1 : x - brokenk = 0) : x = brokenk` was proved by `linarith` and passed every audit
(autoimplicit_verifier_probe.py, 24 Sep, live Lean): a clean certificate for a statement about an
identifier that exists nowhere. statement.AUTOIMPLICIT_OFF now opens every command LeanStatement
renders (theorem, vacuity probe, no-hypothesis probe); harness/run_lean.py's elaboration check
imports the same constant as ELAB_PREFIX.

The offline tests pin the rendered text and every command prove_statement really sends (Lean
faked); the live tests (skipped when the Lean toolchain is missing, as in test_f5_lean.py) pin
what Lean does with them.
"""
from __future__ import annotations

import pytest

from mathverify.formal import build_statement
from mathverify.formal import prove as P
from mathverify.formal.lean_client import LeanResult
from mathverify.formal.statement import AUTOIMPLICIT_OFF, LeanStatement
from mathverify.llm.base import LLMResponse

SAFE_AXIOMS_INFO = "'mv_r6r_k' depends on axioms: [propext, Classical.choice, Quot.sound]"
REVIEWER_HEAD = "theorem mv_r6r_k (x : ℝ) (h1 : x - brokenk = 0) : x = brokenk"


def _brokenk() -> LeanStatement:
    """The reviewer's statement: `brokenk` is defined nowhere."""
    return LeanStatement(name="mv_r6r_k", binders="(x : ℝ)", hypotheses=["x - brokenk = 0"],
                         goal="x = brokenk", field="ℝ", kind="equation_root")


def _goal_only(goal: str) -> LeanStatement:
    return LeanStatement(name="mv_claim", binders="(x : ℝ)", hypotheses=[], goal=goal, field="ℝ",
                         kind="closed_arithmetic")


def _item_statement(items, item_id: str) -> LeanStatement:
    it = next(i for i in items if i["id"] == item_id)
    st = build_statement(it["problem_ir"], it["solution"]["claimed_answer"])
    assert st is not None, item_id
    return st


def _opens_once_with_the_option(code: str, head: str = "theorem ") -> bool:
    return (code.startswith(AUTOIMPLICIT_OFF) and code.count("autoImplicit") == 1
            and code[len(AUTOIMPLICIT_OFF):].startswith(head))


# ------------------------------------------------------------------ offline
def test_the_shared_constant_is_the_option_and_run_lean_reuses_it():
    from harness import run_lean
    assert AUTOIMPLICIT_OFF == "set_option autoImplicit false in\n"
    assert run_lean.ELAB_PREFIX is AUTOIMPLICIT_OFF


def test_every_rendered_command_opens_with_autoimplicit_off(evalset_items):
    """Every statement the evaluation set produces, and the reviewer's: the theorem and both probes."""
    statements = [_brokenk()] + [st for it in evalset_items
                                 if (st := build_statement(it["problem_ir"], it["solution"]["claimed_answer"]))]
    with_probes = 0
    for st in statements:
        assert _opens_once_with_the_option(st.theorem("  norm_num"), f"theorem {st.name} "), st.name
        if st.hypotheses:
            with_probes += 1
            assert _opens_once_with_the_option(st.vacuity_probe(), f"theorem {st.name}_vacuity ")
            assert _opens_once_with_the_option(st.no_hyp_probe("  norm_num"), f"theorem {st.name}_nohyp ")
        else:
            assert st.vacuity_probe() is None and st.no_hyp_probe("  norm_num") is None
    assert len(statements) > 110 and with_probes > 20


class _RecordingLean:
    """Records every command. A proof attempt compiles when `compiles(code)`; `#print axioms` answers
    with the safe axioms; both probes get a Lean error (answered: consistent and used hypotheses)."""

    def __init__(self, compiles):
        self.codes: list[str] = []
        self.compiles = compiles

    def run(self, code, timeout=120.0, env=-1):
        self.codes.append(code)
        if code.startswith("#print axioms"):
            return LeanResult(ok=True, infos=[SAFE_AXIOMS_INFO])
        if "_vacuity " in code or "_nohyp " in code:
            return LeanResult(ok=False, errors=["linarith failed"])
        if self.compiles(code):
            return LeanResult(ok=True, env=7)
        return LeanResult(ok=False, errors=["linarith failed"])


def _statement_commands(codes: list[str]) -> list[str]:
    return [c for c in codes if not c.startswith("#print axioms")]


def test_prove_statement_sends_every_ladder_and_probe_command_with_autoimplicit_off():
    st = _brokenk()
    fake = _RecordingLean(lambda code: code.endswith(":= by\n  linarith"))
    r = P.prove_statement(st, use_model=False, lean=fake, tactic_timeout=45)
    assert r["proved"] and r["proof"] == "  linarith" and r["audit"]["clean"]   # the fake's verdicts
    sent = _statement_commands(fake.codes)
    heads = [c[len(AUTOIMPLICIT_OFF):].split(" (", 1)[0] for c in sent]
    assert heads == ["theorem mv_r6r_k"] * 3 + ["theorem mv_r6r_k_vacuity", "theorem mv_r6r_k_nohyp"]
    assert all(_opens_once_with_the_option(c) for c in sent), sent
    assert fake.codes.count("#print axioms mv_r6r_k") == 1
    # the record is unchanged: the statement itself, without the compile option
    assert r["statement"] == REVIEWER_HEAD


def test_a_model_written_proof_is_compiled_with_autoimplicit_off(monkeypatch):
    """The model sees the statement exactly as before (no option); what Lean compiles carries it."""
    prompts: list[str] = []

    class _Model:
        def complete(self, system, user, **kw):
            prompts.append(user)
            return LLMResponse(text="", parsed={"proof": "  exact h1.symm ▸ rfl"}, provider="fake", model="fake")

    monkeypatch.setattr(P, "get_client", lambda family, model=None: _Model())
    fake = _RecordingLean(lambda code: code.endswith(":= by\n  exact h1.symm ▸ rfl"))
    r = P.prove_statement(_brokenk(), use_model=True, model_attempts=1, lean=fake, tactic_timeout=45)
    assert r["proved"] and r["source"] == "model:anthropic"
    sent = _statement_commands(fake.codes)
    assert len(sent) == len(P.ladder_for("equation_root")) + 1 + 2      # ladder, model proof, probes
    assert all(_opens_once_with_the_option(c) for c in sent), sent
    assert len(prompts) == 1 and "autoImplicit" not in prompts[0]
    assert f"{REVIEWER_HEAD} := by\n  <your proof here>" in prompts[0]


def test_the_elaboration_check_carries_the_option():
    from harness import run_lean
    st = _goal_only("x = brokenc")
    code = run_lean.elaboration_code(st)
    assert code.startswith(run_lean.ELAB_PREFIX) and code.endswith(st.theorem("  sorry"))


# ------------------------------------------------------------------ real Lean
def _lean():
    from mathverify.formal import get_lean, lean_available
    if not lean_available(timeout=300):
        pytest.skip("Lean/Mathlib toolchain not available")
    return get_lean()


def test_live_reviewer_statement_gets_no_certificate():
    """Before the fix: proved by `linarith`, audit clean (reviewer's probe, re-measured 24 Sep)."""
    lean = _lean()
    r = P.prove_statement(_brokenk(), use_model=False, lean=lean, tactic_timeout=45)
    assert not r["proved"] and not r["audit"]
    assert r["attempts"] and all(not a["ok"] for a in r["attempts"])
    assert all(any("brokenk" in e for e in a["errors"]) for a in r["attempts"]), r["attempts"][:2]


def test_live_a_normal_statement_still_certifies_with_both_probes_answered(evalset_items):
    lean = _lean()
    st = _item_statement(evalset_items, "tyt-prob-001")               # a = 16, four hypotheses
    assert st.hypotheses
    r = P.prove_statement(st, use_model=False, lean=lean, tactic_timeout=45)
    assert r["proved"] and r["audit"]["clean"], (r["attempts"][-1:], r["audit"])
    a = r["audit"]
    assert a["unanswered"] == [] and a["hypotheses_contradictory"] is False
    assert a["provable_without_hypotheses"] is False


def test_live_elaboration_fields_and_why_the_option_is_needed(evalset_items):
    from harness import run_lean
    lean = _lean()
    built = run_lean.elaboration_fields(_item_statement(evalset_items, "tyt-prob-001"), 45)
    assert built == {"elaborates": True, "elab_errors": []}
    atomic = run_lean.elaboration_fields(_goal_only("x = brokenc"), 45)
    assert atomic["elaborates"] is False and "brokenc" in atomic["elab_errors"][0]
    dotted = run_lean.elaboration_fields(_goal_only("x = Real.brokenFn 2"), 45)
    assert dotted["elaborates"] is False and "brokenFn" in dotted["elab_errors"][0]
    # Why: WITHOUT the option the same unknown atomic name is bound as an implicit variable, the
    # statement elaborates with exactly one sorry and no error ...
    bare = _goal_only("x = brokenc").theorem("  sorry").removeprefix(AUTOIMPLICIT_OFF)
    assert "autoImplicit" not in bare
    r = lean.run(bare, timeout=45)
    assert run_lean.elaboration_verdict(r) is True and len(r.sorries) == 1 and not r.errors, (r.errors, r.raw)
    # ... and the reviewer's statement is PROVED, with no sorry: the certificate the option prevents
    proof = _brokenk().theorem("  linarith").removeprefix(AUTOIMPLICIT_OFF)
    assert lean.run(proof, timeout=45).clean
