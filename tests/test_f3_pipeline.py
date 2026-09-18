"""F3 pipeline tests that run OFFLINE from the record/replay cache (MATHVERIFY_LLM_CACHE=replay).
They are skipped when the cache has no recording for the prompts (fresh checkout without
llm_cache/) — never call the network from the test-suite."""
import os

import pytest

from harness.loader import load_items, split_for_verifier
from mathverify.llm.cache import CacheMiss, LLMCache
from mathverify.llm.schemas import IR_SCHEMA, JUDGE_SCHEMA, SOLUTION_SCHEMA, ir_from_llm, ir_to_llm, solution_from_llm
from mathverify.extract.roundtrip import render_ir
from mathverify.meta.metamorphic import perturb_ir


@pytest.fixture(scope="module")
def replay(monkeypatch_module=None):
    os.environ["MATHVERIFY_LLM_CACHE"] = "replay"
    import mathverify.llm.cache as c
    c._DEFAULT = None                       # force a fresh cache object in replay mode
    yield
    os.environ["MATHVERIFY_LLM_CACHE"] = "auto"
    c._DEFAULT = None


def _item(evalset_items, iid):
    return next(it for it in evalset_items if it["id"] == iid)


def test_schemas_have_no_union_types():
    def walk(s):
        assert "anyOf" not in s and "oneOf" not in s, s
        for v in s.get("properties", {}).values():
            walk(v)
        if "items" in s:
            walk(s["items"])
    for sch in (IR_SCHEMA, JUDGE_SCHEMA, SOLUTION_SCHEMA):
        walk(sch)
        assert sch["additionalProperties"] is False


def test_ir_roundtrip_converters(evalset_items):
    it = _item(evalset_items, "tyt-prob-001")
    llm_form = ir_to_llm(it["problem_ir"], question_en="q", topic=it["topic"], level=it["level"])
    back = ir_from_llm(llm_form)
    assert back["task"] == it["problem_ir"]["task"]
    assert back["givens"] == it["problem_ir"]["givens"]
    assert back["options"] == it["problem_ir"]["options"]
    it2 = _item(evalset_items, "tyt-ola-001")
    back2 = ir_from_llm(ir_to_llm(it2["problem_ir"]))
    assert back2["task"]["params"]["space"] == it2["problem_ir"]["task"]["params"]["space"]
    it3 = _item(evalset_items, "ayt-diz-001")
    back3 = ir_from_llm(ir_to_llm(it3["problem_ir"]))
    assert back3["task"]["params"]["initial"] == it3["problem_ir"]["task"]["params"]["initial"]


def test_render_ir_mentions_every_given(evalset_items):
    for it in evalset_items[:40]:
        txt = render_ir(it["problem_ir"])
        for g in it["problem_ir"].get("givens") or []:
            assert g in txt
        assert "Task:" in txt


def test_perturbation_has_known_unique_answer(evalset_items):
    it = _item(evalset_items, "tyt-prob-001")
    vs = perturb_ir(it["problem_ir"], seed=1, k=3)
    assert len(vs) == 3
    for v in vs:
        assert v["expected"] == v["values"]["a"]          # target is a itself
        assert v["ir"]["options"] is None
        assert any(a != b for a, b in v["changed"])
    it2 = _item(evalset_items, "ayt-lim-001")
    assert perturb_ir(it2["problem_ir"]) == []               # not applicable: no equational givens


def test_solution_from_llm_normalises_empty_strings():
    d = {"claimed_answer": {"kind": "value", "payload": "16", "option": ""}, "steps": [], "final_answer_text": "16"}
    s = solution_from_llm(d)
    assert s["claimed_answer"]["option"] is None


@pytest.mark.usefixtures("replay")
def test_pipeline_replays_from_cache(evalset_items):
    from mathverify.pipeline import run_pipeline
    it = _item(evalset_items, "tyt-prob-003")
    ir_hand, sol, labels = split_for_verifier(it)
    try:
        pr = run_pipeline(it["question_tr"], it.get("options"), it["level"], solution=sol, use_l4=True, use_l5=True)
    except CacheMiss:
        pytest.skip("no cached LLM responses for this item")
    assert pr.ir_source == "extracted" and pr.extraction["accepted"]
    assert pr.result.verdict == "CORRECT"
    assert "ir_extracted" in pr.result.flags and "l4_agree" in pr.result.flags
    assert all(l.hard is False for l in pr.result.layers if l.layer.startswith(("resolve.", "meta.")))


@pytest.mark.usefixtures("replay")
def test_pipeline_wrong_answer_stays_incorrect_with_l4(evalset_items):
    from mathverify.pipeline import run_pipeline
    it = _item(evalset_items, "tyt-den-009")
    ir_hand, sol, labels = split_for_verifier(it)
    try:
        pr = run_pipeline(it["question_tr"], it.get("options"), it["level"], solution=sol, use_l4=True, use_l5=False)
    except CacheMiss:
        pytest.skip("no cached LLM responses for this item")
    assert pr.result.verdict == "INCORRECT"
    assert "l4_confirms_refutation" in pr.result.flags or "l4_disagree_certified" in pr.result.flags


@pytest.mark.usefixtures("replay")
def test_path_b_llm_restructure_keeps_wrong_step(evalset_items):
    from mathverify.pipeline import run_pipeline
    it = _item(evalset_items, "tyt-prob-019")             # D: right answer, refutable step
    ir_hand, sol, labels = split_for_verifier(it)
    try:
        pr = run_pipeline(it["question_tr"], it.get("options"), it["level"], ir=ir_hand,
                          solution_text=it["solution_text"], use_l4=False, use_l5=False)
    except CacheMiss:
        pytest.skip("no cached LLM responses for this item")
    assert pr.solution_source == "text_llm"
    assert pr.result.verdict == "INCORRECT" and pr.result.first_bad_step is not None
