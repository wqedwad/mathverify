"""F3 — NL -> IR extraction, validation and the two-family round-trip audit, exercised
offline against scripted clients (no network, no keys, no cost)."""
import copy

import pytest

from conftest_llm import pin, unpin, ir_reply, judge_reply
from mathverify.extract import extract_ir, validate_ir, normalize_task, render_ir
from mathverify.llm import LLMError, LLMCreditError

# The message the provider actually sends when the balance is empty. The old test used a
# 24-character stand-in, which is why it kept passing while the real thing was silently
# truncated below the word the harness greps for. Length is part of the fixture.
REAL_CREDIT_MESSAGE = (
    "anthropic API error 400: Error code: 400 - {'type': 'error', 'error': "
    "{'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access "
    "the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}}")

IR_OK = {
    "task": {"kind": "evaluate", "params": {"expr": "a"}},
    "vars": [{"name": "a", "domain": "positive_integer", "constraints": []},
             {"name": "b", "domain": "positive_integer", "constraints": []}],
    "givens": ["a + b = 30", "2*a + 4*b = 88"],
    "functions": [], "unknown_of_interest": "a", "answer_shape": "scalar",
    "options": {"A": "12", "B": "14", "C": "16", "D": "18", "E": "20"},
    "units": None, "sanity": ["ans > 0"], "domain_of_discourse": None, "topic": "problemler", "level": "TYT",
}
Q = "Tavuk ve koyunların baş sayısı 30, ayak sayısı 88. Kaç tavuk vardır?"
OPTS = IR_OK["options"]


@pytest.fixture(autouse=True)
def _clean():
    yield
    unpin()


# ------------------------------------------------------------------ validation (pure)
def test_validate_accepts_a_good_ir():
    assert validate_ir(IR_OK) == []


def test_validate_rejects_unparseable_given():
    bad = copy.deepcopy(IR_OK)
    bad["givens"] = ["a + = 30"]
    errs = validate_ir(bad)
    assert errs and "does not parse" in errs[0]


def test_validate_rejects_undeclared_symbol():
    bad = copy.deepcopy(IR_OK)
    bad["givens"] = ["a + z = 30"]
    assert any("z" in e for e in validate_ir(bad))


def test_validate_rejects_options_that_do_not_match_the_shape():
    bad = copy.deepcopy(IR_OK)
    bad["answer_shape"] = "set"
    bad["options"] = {"A": "12", "B": "not a set ("}
    assert any("option" in e for e in validate_ir(bad))


def test_validate_rejects_a_leaked_answer_key():
    bad = copy.deepcopy(IR_OK)
    bad["gold_answer"] = "16"
    errs = validate_ir(bad)
    assert errs and "forbidden key" in errs[0].lower()


def test_validate_requires_the_params_each_kind_needs():
    bad = copy.deepcopy(IR_OK)
    bad["task"] = {"kind": "limit", "params": {"expr": "sin(x)/x"}}     # no `to`
    bad["vars"] = [{"name": "x", "domain": "real", "constraints": []}]
    bad["givens"] = []
    assert any("limit needs" in e for e in validate_ir(bad))


def test_normalize_task_moves_a_multi_equation_solve_to_evaluate():
    d = copy.deepcopy(IR_OK)
    d["task"] = {"kind": "solve_equation", "params": {"solve_for": "a", "system": ["a + b = 30", "2*a + 4*b = 88"]}}
    d["givens"] = []
    out = normalize_task(d)
    assert out["task"]["kind"] == "evaluate" and out["task"]["params"]["expr"] == "a"
    assert out["givens"] == ["a + b = 30", "2*a + 4*b = 88"]


# ------------------------------------------------------------------ extraction loop
def test_happy_path_is_accepted_in_one_round():
    a, m = pin({"ir_extract": ir_reply(IR_OK), "roundtrip_judge": judge_reply(10)})
    res = extract_ir(Q, OPTS, "TYT")
    assert res.accepted and res.reason == "roundtrip_passed"
    assert len(res.rounds) == 1
    assert res.ir["task"]["kind"] == "evaluate"
    assert a.count("ir_extract") == 1 and a.count("roundtrip_judge") == 1 and m.count("roundtrip_judge") == 1


def test_both_families_must_agree_for_acceptance():
    pin({"ir_extract": ir_reply(IR_OK), "roundtrip_judge": judge_reply(10)},
        {"roundtrip_judge": judge_reply(6, ["the second given is missing"])})
    res = extract_ir(Q, OPTS, "TYT", max_repairs=0)
    assert not res.accepted and res.reason == "roundtrip_failed"
    assert res.rounds[-1]["roundtrip"]["judges"]["meta"]["score"] == 6


def test_validation_failure_triggers_a_repair_round_with_feedback():
    broken = copy.deepcopy(IR_OK)
    broken["givens"] = ["a + = 30"]
    a, _ = pin({"ir_extract": [ir_reply(broken), ir_reply(IR_OK)], "roundtrip_judge": judge_reply(10)})
    res = extract_ir(Q, OPTS, "TYT")
    assert res.accepted and len(res.rounds) == 2
    assert res.rounds[0]["validation_errors"]
    assert "Deterministic validation failed" in a.calls[1][1] or "Findings to fix" in a.calls[1][1]


def test_roundtrip_failure_feeds_the_discrepancies_back():
    a, _ = pin({"ir_extract": [ir_reply(IR_OK), ir_reply(IR_OK)],
                "roundtrip_judge": [judge_reply(5, ["units dropped"]), judge_reply(10)]})
    res = extract_ir(Q, OPTS, "TYT", max_repairs=1)
    assert res.accepted
    assert any("units dropped" in c[1] for c in a.calls)


def test_repair_budget_is_bounded():
    pin({"ir_extract": ir_reply(IR_OK), "roundtrip_judge": judge_reply(4, ["wrong task"])})
    res = extract_ir(Q, OPTS, "TYT", max_repairs=2)
    assert not res.accepted and len(res.rounds) == 3


def test_model_returning_no_json_is_not_a_crash():
    pin({"ir_extract": [None, ir_reply(IR_OK)], "roundtrip_judge": judge_reply(10)})
    res = extract_ir(Q, OPTS, "TYT")
    assert res.accepted and res.rounds[0]["error"] == "no_json"


def test_a_recoverable_llm_error_stops_the_loop_and_is_reported_whole():
    """A non-fatal failure is a measurement: the item is recorded, the sweep continues, and
    the reason is kept ENTIRE. Truncating it here is how a billing message lost the word the
    harness was grepping for."""
    pin({"ir_extract": LLMError(REAL_CREDIT_MESSAGE)})
    res = extract_ir(Q, OPTS, "TYT")
    assert not res.accepted
    assert res.reason.endswith(REAL_CREDIT_MESSAGE), "the reason must not be truncated"


def test_a_credit_failure_is_not_swallowed_as_a_measurement():
    """DECISIONS §23. LLMCreditError is deliberately NOT an LLMError, so the per-call handler
    cannot turn an empty balance into 218 quietly recorded 'unavailable' items."""
    pin({"ir_extract": LLMCreditError(REAL_CREDIT_MESSAGE)})
    with pytest.raises(LLMCreditError):
        extract_ir(Q, OPTS, "TYT")


def test_an_unknown_top_level_field_from_the_model_is_dropped():
    """D2, first line of defence: `ir_from_llm` copies only known fields, so a model that
    volunteers the answer at top level cannot get it into the problem object."""
    payload = ir_reply(IR_OK)
    payload["gold_answer"] = "16"
    pin({"ir_extract": payload, "roundtrip_judge": judge_reply(10)})
    res = extract_ir(Q, OPTS, "TYT", max_repairs=0)
    assert res.accepted
    assert "gold_answer" not in str(res.ir).lower()


def test_a_key_smuggled_into_task_params_is_rejected_not_silently_kept():
    """Second line: a key-like task parameter does get copied, and the structural scan in
    ProblemIR.from_dict then refuses the whole IR — reject, never accept-with-leak."""
    payload = ir_reply(IR_OK)
    payload["task"]["params"].append({"key": "answer_key", "value": "16", "list": []})
    pin({"ir_extract": payload, "roundtrip_judge": judge_reply(10)})
    res = extract_ir(Q, OPTS, "TYT", max_repairs=0)
    assert not res.accepted and res.reason == "validation_failed"
    assert any("answer-key isolation" in e or "forbidden key" in e.lower()
               for e in res.rounds[0]["validation_errors"])


def test_extraction_never_returns_an_unvalidated_ir():
    broken = copy.deepcopy(IR_OK)
    broken["givens"] = ["a + = 30"]
    pin({"ir_extract": ir_reply(broken), "roundtrip_judge": judge_reply(10)})
    res = extract_ir(Q, OPTS, "TYT", max_repairs=0)
    assert not res.accepted


# ------------------------------------------------------------------ rendering
def test_render_mentions_givens_task_and_options():
    txt = render_ir(IR_OK)
    assert "a + b = 30" in txt and "2*a + 4*b = 88" in txt
    assert "Find the value of: a" in txt
    assert "A) 12" in txt and "positive integer" in txt


def test_render_states_the_domain_restriction_when_present():
    ir = copy.deepcopy(IR_OK)
    ir["domain_of_discourse"] = "a > 10"
    assert "Domain restriction stated by the problem: a > 10" in render_ir(ir)
