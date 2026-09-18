"""F3 — schema/converter contracts and the record/replay cache that gives the LLM layers
their determinism (handoff §11/13). Everything here runs offline."""
import json

import pytest

from mathverify.llm.cache import CacheMiss, LLMCache
from mathverify.llm.schemas import (IR_SCHEMA, JUDGE_SCHEMA, SOLUTION_SCHEMA, ir_from_llm, ir_to_llm,
                                    solution_from_llm)
from mathverify.extract.roundtrip import render_ir
from mathverify.meta.metamorphic import perturb_ir


# ------------------------------------------------------------------ schemas / converters
def test_schemas_are_union_free_and_closed():
    def walk(s):
        assert "anyOf" not in s and "oneOf" not in s, s
        assert "minimum" not in s and "maximum" not in s, s   # rejected by the API compiler
        for v in s.get("properties", {}).values():
            walk(v)
        if "items" in s:
            walk(s["items"])
    for sch in (IR_SCHEMA, JUDGE_SCHEMA, SOLUTION_SCHEMA):
        walk(sch)
        assert sch["additionalProperties"] is False
        assert set(sch["required"]) == set(sch["properties"])


def test_ir_converters_round_trip_every_item(evalset_items):
    """ir_to_llm -> ir_from_llm must be the identity on the task, givens and options of every
    hand-written IR: the extractor's output format has to be able to express the whole set.
    Empty-string parameters are normalised away on the way back (an empty predicate means
    "no filter", which is how every consumer reads a missing one)."""
    def norm(params):
        return {k: v for k, v in (params or {}).items() if v != ""}
    for it in evalset_items:
        src = it["problem_ir"]
        back = ir_from_llm(ir_to_llm(src, question_en="q"))
        assert back["task"]["kind"] == src["task"]["kind"], it["id"]
        assert norm(back["task"]["params"]) == norm(src["task"].get("params")), it["id"]
        assert back["givens"] == (src.get("givens") or []), it["id"]
        assert back["options"] == src.get("options"), it["id"]
        assert back["answer_shape"] == src.get("answer_shape", "scalar"), it["id"]
        assert [v["name"] for v in back["vars"]] == [v["name"] for v in (src.get("vars") or [])], it["id"]
        assert back["domain_of_discourse"] == (src.get("domain_of_discourse") or None), it["id"]


def test_solution_converter_normalises_empty_strings():
    s = solution_from_llm({"claimed_answer": {"kind": "value", "payload": "16", "option": ""},
                           "steps": [{"id": "", "kind": "eq", "claim": "a = 16", "from": [], "text": ""}],
                           "final_answer_text": "16"})
    assert s["claimed_answer"]["option"] is None
    assert s["steps"][0]["id"] == "s1"
    s2 = solution_from_llm({"claimed_answer": {"kind": "dne", "payload": "", "option": "E"},
                            "steps": [], "final_answer_text": ""})
    assert s2["claimed_answer"]["payload"] is None and s2["claimed_answer"]["option"] == "E"


def test_render_ir_covers_every_task_kind_in_the_set(evalset_items):
    kinds = set()
    for it in evalset_items:
        txt = render_ir(it["problem_ir"])
        kinds.add(it["problem_ir"]["task"]["kind"])
        assert "Task:" in txt and "Task kind" not in txt, it["id"]   # no fallback rendering
    assert len(kinds) >= 15


def test_perturbation_is_deterministic_and_bounded(evalset_items):
    it = next(i for i in evalset_items if i["id"] == "tyt-prob-001")
    a = perturb_ir(it["problem_ir"], seed=5, k=3)
    b = perturb_ir(it["problem_ir"], seed=5, k=3)
    assert [x["values"] for x in a] == [x["values"] for x in b]
    assert len(a) <= 3


# ------------------------------------------------------------------ cache
def _req(prompt="hello"):
    return {"model": "m", "system": "s", "messages": [{"role": "user", "content": prompt}]}


def test_cache_key_depends_on_every_part_of_the_request(tmp_path):
    c = LLMCache(tmp_path, mode="auto")
    k1 = c.key("anthropic", "claude-opus-5", _req())
    assert k1 == c.key("anthropic", "claude-opus-5", _req())
    assert k1 != c.key("anthropic", "claude-opus-5", _req("hello!"))
    assert k1 != c.key("anthropic", "claude-fable-5-1", _req())
    assert k1 != c.key("meta", "claude-opus-5", _req())


def test_record_then_replay_returns_the_same_response(tmp_path):
    rec = LLMCache(tmp_path, mode="auto")
    key = rec.key("meta", "muse-spark-1.3", _req())
    assert rec.get(key) is None
    rec.put(key, {"provider": "meta", "model": "muse-spark-1.3", "request": _req(),
                  "response": {"text": "42", "parsed": {"x": 1}}})
    got = rec.get(key)
    assert got["response"]["text"] == "42" and got["response"]["parsed"] == {"x": 1}
    replay = LLMCache(tmp_path, mode="replay")
    assert replay.get(key)["response"]["text"] == "42"


def test_replay_mode_refuses_to_go_to_the_network(tmp_path):
    replay = LLMCache(tmp_path, mode="replay")
    with pytest.raises(CacheMiss):
        replay.get(replay.key("anthropic", "claude-opus-5", _req("never recorded")))


def test_off_mode_neither_reads_nor_writes(tmp_path):
    off = LLMCache(tmp_path, mode="off")
    key = off.key("meta", "m", _req())
    off.put(key, {"response": {"text": "x"}})
    assert off.get(key) is None
    assert not list(tmp_path.rglob("*.json"))


def test_cache_records_hold_no_credentials(tmp_path):
    c = LLMCache(tmp_path, mode="auto")
    key = c.key("anthropic", "claude-opus-5", _req())
    c.put(key, {"provider": "anthropic", "model": "claude-opus-5", "request": _req(),
                "response": {"text": "ok"}})
    blob = "".join(p.read_text(encoding="utf-8") for p in tmp_path.rglob("*.json")).lower()
    for secret in ("sk-ant", "api_key", "authorization", "bearer", "llm_"):
        assert secret not in blob
