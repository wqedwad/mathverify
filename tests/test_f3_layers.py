"""F3/F4 — L4 cross-family re-solve, L5 metamorphic, L6 critic + meta-verification and the
end-to-end pipeline, exercised offline against scripted clients.

The point of these tests is the *authority* of each signal (handoff §4.1, §11/16): an LLM
layer may lower confidence or force UNKNOWN, and may never turn a hard certificate into the
opposite verdict.
"""
import copy

import pytest

from conftest_llm import pin, unpin, ir_reply, judge_reply, solution_reply, critic_reply, meta_reply
from mathverify.pipeline import run_pipeline
from mathverify.resolve import l4_layer
from mathverify.meta import metamorphic_check, l5_layer, perturb_ir
from mathverify.critic import l6_critic_layer

IR = {
    "task": {"kind": "evaluate", "params": {"expr": "a"}},
    "vars": [{"name": "a", "domain": "positive_integer", "constraints": []},
             {"name": "b", "domain": "positive_integer", "constraints": []}],
    "givens": ["a + b = 30", "2*a + 4*b = 88"],
    "functions": [], "unknown_of_interest": "a", "answer_shape": "scalar",
    "options": {"A": "12", "B": "14", "C": "16", "D": "18", "E": "20"},
    "units": None, "sanity": [], "domain_of_discourse": None, "topic": "problemler", "level": "TYT",
}
Q = "Tavuk ve koyunların baş sayısı 30, ayak sayısı 88. Kaç tavuk vardır?"
OPTS = IR["options"]
SOL_RIGHT = {"claimed_answer": {"kind": "value", "payload": "16", "option": "C"},
             "steps": [{"id": "s1", "kind": "eq", "claim": "b = 30 - a", "from": [], "text": ""},
                       {"id": "s2", "kind": "eq", "claim": "a = 16", "from": ["s1"], "text": ""}]}
SOL_WRONG = {"claimed_answer": {"kind": "value", "payload": "14", "option": "B"},
             "steps": [{"id": "s1", "kind": "eq", "claim": "a = 14", "from": [], "text": ""}]}


@pytest.fixture(autouse=True)
def _clean():
    yield
    unpin()


def _base_script(resolver_answer="16", critic=None, meta=None):
    return {"ir_extract": ir_reply(IR), "roundtrip_judge": judge_reply(10),
            "resolve": solution_reply("value", resolver_answer, "C"),
            "metamorphic": solution_reply("value", "0"),
            "critic": critic if critic is not None else critic_reply(),
            "meta_verify": meta if meta is not None else meta_reply(False)}


# ------------------------------------------------------------------ L4
def test_l4_agreement_does_not_create_a_verdict_by_itself():
    pin(_base_script())
    lr = l4_layer(IR, SOL_RIGHT, {"family": "meta", "model": "m", "verdict": "CORRECT",
                                  "solution": SOL_RIGHT, "cost_usd": 0.0, "calls": 1})
    assert lr.verdict == "unknown" and lr.hard is False and lr.primary is False
    assert "l4_agree" in lr.flags


def test_l4_certified_disagreement_blocks_a_positive_verdict():
    from mathverify.fuse import fuse
    from mathverify.types import LayerResult
    pin(_base_script())
    lr = l4_layer(IR, SOL_RIGHT, {"family": "meta", "verdict": "CORRECT", "solution": SOL_WRONG,
                                  "cost_usd": 0.0, "calls": 1})
    assert "l4_disagree_certified" in lr.flags
    cert = LayerResult("certify.algebra", "pass", 0.99, True, {}, 1.0, primary=True)
    assert fuse([cert, lr])["verdict"] == "UNKNOWN"


def test_l4_uncertified_disagreement_only_costs_confidence():
    from mathverify.fuse import fuse
    from mathverify.types import LayerResult
    pin(_base_script())
    lr = l4_layer(IR, SOL_RIGHT, {"family": "meta", "verdict": "UNKNOWN", "solution": SOL_WRONG,
                                  "cost_usd": 0.0, "calls": 1})
    assert "l4_disagree_uncertified" in lr.flags
    cert = LayerResult("certify.algebra", "pass", 0.99, True, {}, 1.0, primary=True)
    out = fuse([cert, lr])
    assert out["verdict"] == "CORRECT" and out["confidence"] < 0.99


def test_l4_disagreement_with_an_already_refuted_claim_is_just_confirmation():
    pin(_base_script())
    lr = l4_layer(IR, SOL_WRONG, {"family": "meta", "verdict": "CORRECT", "solution": SOL_RIGHT,
                                  "cost_usd": 0.0, "calls": 1}, original_verdict="INCORRECT")
    assert "l4_confirms_refutation" in lr.flags


def test_l4_never_produces_correct_or_incorrect_on_its_own():
    from mathverify.fuse import fuse
    pin(_base_script())
    for rec in ({"family": "meta", "verdict": "CORRECT", "solution": SOL_RIGHT},
                {"family": "meta", "verdict": "CORRECT", "solution": SOL_WRONG}):
        lr = l4_layer(IR, SOL_RIGHT, dict(rec, cost_usd=0.0, calls=1))
        assert fuse([lr])["verdict"] == "UNKNOWN"


# ------------------------------------------------------------------ L5
def test_perturbed_instances_have_a_known_unique_answer():
    vs = perturb_ir(IR, seed=2, k=3)
    assert len(vs) == 3
    for v in vs:
        assert v["expected"] == v["values"]["a"]
        assert v["ir"]["options"] is None and v["ir"]["givens"] != IR["givens"]


def test_l5_flags_a_method_that_fails_on_perturbed_instances():
    # the scripted solver always answers 0, which is wrong for every perturbed instance
    pin(_base_script())
    mt = metamorphic_check(Q, IR, SOL_RIGHT, "anthropic", k=3, seed=2)
    assert mt["applicable"] and mt["failed"] >= 2
    lr = l5_layer(mt)
    assert "l5_method_failed" in lr.flags and lr.hard is False


def test_l5_is_silent_when_the_method_reproduces_the_known_answers():
    def solver(system, user, n):
        # read the perturbed data out of the prompt and answer correctly
        import re
        m = re.search(r"a \+ b = (\d+)", user)
        m2 = re.search(r"2\*a \+ 4\*b = (\d+)", user)
        if not (m and m2):
            return solution_reply("value", "0")
        s, f = int(m.group(1)), int(m2.group(1))
        a = (4 * s - f) // 2
        return solution_reply("value", str(a))
    pin(dict(_base_script(), metamorphic=solver))
    mt = metamorphic_check(Q, IR, SOL_RIGHT, "anthropic", k=3, seed=2)
    assert mt["passed"] == mt["n"] and mt["failed"] == 0
    assert "l5_method_ok" in l5_layer(mt).flags


def test_l5_reports_not_applicable_instead_of_guessing():
    ir = copy.deepcopy(IR)
    ir["task"] = {"kind": "limit", "params": {"expr": "sin(x)/x", "var": "x", "to": "0"}}
    ir["givens"] = []
    ir["vars"] = [{"name": "x", "domain": "real", "constraints": []}]
    pin(_base_script())
    mt = metamorphic_check(Q, ir, SOL_RIGHT, "anthropic")
    assert not mt["applicable"] and mt["calls"] == 0


# ------------------------------------------------------------------ L6 critic
def test_critic_clean_report_is_not_positive_evidence():
    from mathverify.fuse import fuse
    pin(_base_script())
    lr, rec = l6_critic_layer(Q, OPTS, IR, SOL_RIGHT, "anthropic")
    assert "critic_clean" in lr.flags and lr.hard is False
    assert fuse([lr])["verdict"] == "UNKNOWN"


def test_a_critic_error_on_a_certificate_verified_step_is_overruled():
    pin(_base_script(critic=critic_reply("error_found", "s2", "algebra", "wrong", "")))
    step_ev = {"steps": [{"id": "s2", "status": "verified"}]}
    lr, rec = l6_critic_layer(Q, OPTS, IR, SOL_RIGHT, "anthropic", step_ev)
    assert "critic_overruled_by_certificate" in lr.flags
    assert rec["meta"] is None                      # meta-verification not even spent


def test_a_false_counter_check_overrules_the_critic():
    pin(_base_script(critic=critic_reply("error_found", "s1", "arith", "no", "2 + 2 = 5")))
    lr, rec = l6_critic_layer(Q, OPTS, IR, SOL_RIGHT, "anthropic")
    assert "critic_overruled_by_certificate" in lr.flags
    assert lr.evidence["cross_check"]["counter_check_holds"] is False


def test_a_confirmed_error_blocks_correct_but_never_flips_it():
    from mathverify.fuse import fuse
    from mathverify.types import LayerResult
    pin(_base_script(critic=critic_reply("error_found", "s1", "arith", "b is not 30 - a", "30 - 16 = 14"),
                     meta=meta_reply(True, 9)))
    lr, rec = l6_critic_layer(Q, OPTS, IR, SOL_RIGHT, "anthropic")
    assert "critic_error_confirmed" in lr.flags and lr.first_bad_step == 1
    cert = LayerResult("certify.algebra", "pass", 0.99, True, {}, 1.0, primary=True)
    out = fuse([cert, lr])
    assert out["verdict"] == "UNKNOWN" and out["first_bad_step"] == 1


def test_an_unconfirmed_error_does_not_block_correct():
    from mathverify.fuse import fuse
    from mathverify.types import LayerResult
    pin(_base_script(critic=critic_reply("error_found", "s1", "arith", "maybe", ""),
                     meta=meta_reply(False, 9)))
    lr, rec = l6_critic_layer(Q, OPTS, IR, SOL_RIGHT, "anthropic")
    assert "critic_error_unconfirmed" in lr.flags and lr.first_bad_step is None
    cert = LayerResult("certify.algebra", "pass", 0.99, True, {}, 1.0, primary=True)
    assert fuse([cert, lr])["verdict"] == "CORRECT"


def test_a_low_confidence_meta_verdict_does_not_confirm():
    pin(_base_script(critic=critic_reply("error_found", "s1", "arith", "x", ""),
                     meta=meta_reply(True, 3)))
    lr, _ = l6_critic_layer(Q, OPTS, IR, SOL_RIGHT, "anthropic")
    assert "critic_error_unconfirmed" in lr.flags


def test_a_true_but_unjustified_step_is_still_overruled_by_its_certificate():
    """Measured limitation, pinned deliberately.

    A certificate proves a step's CLAIM is true. That contradicts a critic who says the claim is
    false. It does not contradict a critic who says a true claim does not follow from the cited
    premises, which is exactly the open defect on `tyt-prob-018`. The cross-check does not tell
    the two apart, so F4 as written cannot close that defect.

    Narrowing the rule would let an unsupported "unjustified" report refute a solution that a
    certificate accepted, which is the failure mode the handoff warns about most loudly. Which
    way to go is a precision/recall trade-off, and the handoff allows only measurement to settle
    it. Until the F4 sweep runs, the conservative reading stays, and this test makes any change
    to it a deliberate one rather than an accident."""
    pin(_base_script(critic=critic_reply("error_found", "s1", "unjustified",
                                         "true, but not derivable from the cited premises", ""),
                     meta=meta_reply(True, 10)))
    step_ev = {"steps": [{"id": "s1", "status": "verified"}]}
    lr, rec = l6_critic_layer(Q, OPTS, IR, SOL_RIGHT, "anthropic", step_ev)
    assert "critic_overruled_by_certificate" in lr.flags
    assert lr.evidence["cross_check"]["flagged_step_status"] == "verified"
    assert rec["meta"] is None                      # the meta-verifier is never even asked
    assert lr.first_bad_step is None


# ------------------------------------------------------------------ pipeline
def test_pipeline_end_to_end_correct():
    pin(_base_script())
    pr = run_pipeline(Q, OPTS, "TYT", solution=SOL_RIGHT, use_l4=True, use_l5=False, use_l6=True)
    assert pr.result.verdict == "CORRECT"
    assert pr.ir_source == "extracted" and pr.base_verdict == "CORRECT"
    assert {"ir_extracted", "l4_agree"} <= set(pr.result.flags)


def test_pipeline_end_to_end_incorrect_is_decided_deterministically():
    pin(_base_script(resolver_answer="16"))
    pr = run_pipeline(Q, OPTS, "TYT", solution=SOL_WRONG, use_l4=True, use_l5=False, use_l6=True)
    assert pr.result.verdict == "INCORRECT" and pr.base_verdict == "INCORRECT"


def test_pipeline_abstains_when_the_ir_cannot_be_trusted():
    pin({"ir_extract": ir_reply(IR), "roundtrip_judge": judge_reply(5, ["a given is missing"])})
    pr = run_pipeline(Q, OPTS, "TYT", solution=SOL_RIGHT, use_l4=False, use_l5=False, use_l6=False)
    assert pr.result.verdict == "UNKNOWN" and pr.stage == "ir_extraction_failed"
    assert "ir_unavailable" in pr.result.flags


def test_pipeline_records_versions_and_costs():
    pin(_base_script())
    pr = run_pipeline(Q, OPTS, "TYT", solution=SOL_RIGHT, use_l4=True, use_l5=True, use_l6=True)
    assert pr.result.versions["sympy"] == "1.14.0"
    assert "llm.anthropic" in pr.result.versions and "llm.cache_mode" in pr.result.versions
    assert pr.calls >= 4 and pr.cost_usd >= 0.0


def test_the_harness_records_what_happened_to_the_critic_report():
    """F4 produced no numbers in the first sweep because the harness dropped `pr.critic`. The
    outcome field is the whole point: a report a certificate overruled and a report the
    meta-verifier confirmed are different results and must not collapse into one count."""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    from harness.run_f3 import _l6_record
    pin(_base_script(critic=critic_reply("error_found", "s1", "unjustified", "does not follow", ""),
                     meta=meta_reply(True, 9)))
    pr = run_pipeline(Q, OPTS, "TYT", solution=SOL_RIGHT, use_l4=False, use_l5=False, use_l6=True)
    assert any(l.layer == "critic.steps" for l in pr.result.layers), "L6 did not run at all"
    rec = _l6_record(pr)
    assert rec["assessment"] == "error_found" and rec["first_bad_step"] == "s1"
    assert rec["error_kind"] == "unjustified" and rec["outcome"]
    assert isinstance(rec["flags"], list) and rec["calls"] >= 1


def test_turning_the_critic_off_removes_the_layer_entirely():
    pin(_base_script())
    pr = run_pipeline(Q, OPTS, "TYT", solution=SOL_RIGHT, use_l4=False, use_l5=False, use_l6=False)
    assert not any(l.layer == "critic.steps" for l in pr.result.layers)
    assert pr.critic is None


# ------------------------------------------------------------------ fatal provider failures
# DECISIONS §23: a billing/auth failure is not a measurement. It must reach the harness from
# EVERY layer, not only from IR extraction — the 18 Sep sweep spent its remaining items
# because the guard looked at one truncated string from one layer.
REAL_CREDIT_MESSAGE = (
    "anthropic API error 400: Error code: 400 - {'type': 'error', 'error': "
    "{'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access "
    "the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}}")


@pytest.mark.parametrize("tag,kw", [
    ("resolve", dict(use_l4=True, use_l5=False, use_l6=False)),
    ("metamorphic", dict(use_l4=False, use_l5=True, use_l6=False)),
    ("critic", dict(use_l4=False, use_l5=False, use_l6=True)),
])
def test_a_credit_failure_in_any_layer_reaches_the_caller(tag, kw):
    from mathverify.llm import LLMCreditError
    script = _base_script()
    script[tag] = LLMCreditError(REAL_CREDIT_MESSAGE)
    pin(script)
    with pytest.raises(LLMCreditError):
        run_pipeline(Q, OPTS, "TYT", ir=IR, solution=SOL_RIGHT, **kw)


def test_a_credit_failure_in_the_meta_verifier_also_reaches_the_caller():
    from mathverify.llm import LLMCreditError
    # flag a step the deterministic layer has no verdict on, so the cross-check does not
    # overrule the report before the meta-verifier is reached
    script = _base_script(critic=critic_reply("error_found", "s9", "bad", "does not follow", ""))
    script["meta_verify"] = LLMCreditError(REAL_CREDIT_MESSAGE)
    pin(script)
    with pytest.raises(LLMCreditError):
        run_pipeline(Q, OPTS, "TYT", ir=IR, solution=SOL_RIGHT, use_l4=False, use_l5=False, use_l6=True)


def test_the_sweep_stops_on_the_first_fatal_instead_of_burning_the_rest():
    """The regression this exists for: `aborted` was None in f3_results.json while 151 items
    had failed on billing, because the abort grepped a message truncated one character before
    the word 'credit'. The signal is now structural."""
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from harness.run_f3 import run_item
    from mathverify.llm import LLMCreditError

    class _Args:
        no_l4 = no_l5 = no_l6 = True
        pathb = False

    item = {"id": "tyt-x-001", "level": "TYT", "topic": "problemler", "cell": "A",
            "question_tr": Q, "options": OPTS, "problem_ir": copy.deepcopy(IR),
            "solution": copy.deepcopy(SOL_RIGHT), "solution_is_correct": True,
            "first_bad_step": None, "gold_answer": "16"}
    pin({"ir_extract": LLMCreditError(REAL_CREDIT_MESSAGE)})
    rec = run_item(item, _Args())
    assert rec["fatal"], "a fatal failure must be marked structurally, not by substring luck"
    assert "llm_fatal" in rec["flags"]


# ------------------------------------------------------------------ cross-family separation (B6)
def test_the_record_says_so_when_the_solver_family_is_unknown():
    """DECISIONS §17: the family that wrote a solution may not judge it. Every judging layer
    derives its family from `solver_family`, and with None they all fall back to one family.
    That is harmless for the synthetic set and wrong the moment a real Claude solver is
    plugged in, so the absence of the rule is recorded rather than assumed away."""
    pin(_base_script())
    pr = run_pipeline(Q, OPTS, "TYT", ir=IR, solution=SOL_RIGHT, use_l4=True, use_l5=False, use_l6=False)
    assert "solver_family_unknown" in pr.result.flags


def test_naming_the_solver_family_removes_the_flag_and_flips_the_judges():
    from mathverify.llm import other_family
    a, m = pin(_base_script())
    pr = run_pipeline(Q, OPTS, "TYT", ir=IR, solution=SOL_RIGHT, solver_family="anthropic",
                      use_l4=True, use_l5=False, use_l6=False)
    assert "solver_family_unknown" not in pr.result.flags
    assert pr.resolve["family"] == other_family("anthropic") == "meta"


def test_fixed_roles_come_from_one_table_not_from_string_literals():
    from mathverify.llm import ROLE_FAMILY, client_for_role, judge_families
    a, m = pin(_base_script())
    assert client_for_role("extractor") is (a if ROLE_FAMILY["extractor"] == "anthropic" else m)
    assert set(judge_families()) == {ROLE_FAMILY["judge_a"], ROLE_FAMILY["judge_b"]}
    assert len(judge_families()) == 2, "the round-trip must not collapse to a single family"
    with pytest.raises(ValueError):
        client_for_role("no_such_role")
