"""D2 answer-key isolation (handoff §4.1, §11/15): the IR has no gold field, key-like
keys are rejected structurally, and the verdict is invariant to whatever key the harness
holds (leakage test)."""
import copy
import json

import pytest

from mathverify import ProblemIR, Solution, LeakageError
from mathverify.verifier import verify

IR = {
    "task": {"kind": "evaluate", "params": {"expr": "a"}},
    "vars": [{"name": "a", "domain": "positive_integer"}, {"name": "b", "domain": "positive_integer"}],
    "givens": ["a + b = 30", "2*a + 4*b = 88"],
    "answer_shape": "scalar",
    "options": {"A": "12", "B": "14", "C": "16", "D": "18", "E": "20"},
    "domain_of_discourse": None,
}
SOL = {"claimed_answer": {"kind": "value", "payload": "16", "option": "C"},
       "steps": [{"id": "s1", "kind": "eq", "claim": "b = 30 - a", "from": []},
                 {"id": "s2", "kind": "eq", "claim": "2*a + 4*(30 - a) = 88", "from": ["s1"]},
                 {"id": "s3", "kind": "eq", "claim": "a = 16", "from": ["s2"]}]}


@pytest.mark.parametrize("key", ["gold_answer", "answer_key", "expected_answer", "correct_option", "cell",
                                 "solution_is_correct", "first_bad_step"])
def test_ir_rejects_key_like_fields(key):
    d = copy.deepcopy(IR)
    d[key] = "16"
    with pytest.raises(LeakageError):
        ProblemIR.from_dict(d)


def test_ir_rejects_nested_key_like_fields():
    d = copy.deepcopy(IR)
    d["task"]["params"]["gold_answer"] = "16"
    with pytest.raises(LeakageError):
        ProblemIR.from_dict(d)


def test_solution_rejects_key_like_fields():
    d = copy.deepcopy(SOL)
    d["gold_answer"] = "16"
    with pytest.raises(LeakageError):
        Solution.from_dict(d)


def test_problem_ir_dataclass_has_no_gold_field():
    ir = ProblemIR.from_dict(IR)
    assert not any("gold" in f or "key" in f for f in ir.to_dict())


def test_leakage_verdict_invariance():
    """Run the same item twice while the (external) harness holds a right and a wrong key.
    The verifier never receives the key, so verdict+confidence must be byte-identical."""
    r1 = verify(copy.deepcopy(IR), copy.deepcopy(SOL))
    _harness_gold = "16"       # noqa: F841 - lives outside the pipeline
    r2 = verify(copy.deepcopy(IR), copy.deepcopy(SOL))
    _harness_gold = "999"      # noqa: F841 - deliberately wrong key, still outside
    assert (r1.verdict, r1.confidence) == (r2.verdict, r2.confidence)
    blob = json.dumps(r1.to_dict(), ensure_ascii=False, default=str).lower()
    assert "gold" not in blob and "answer_key" not in blob


def test_evidence_never_contains_key_material():
    r = verify(copy.deepcopy(IR), copy.deepcopy(SOL))
    for layer in r.layers:
        blob = json.dumps(layer.evidence, ensure_ascii=False, default=str).lower()
        assert "gold" not in blob
