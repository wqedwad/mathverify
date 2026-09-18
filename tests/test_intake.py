"""D1 intake paths: structured loader validation and deterministic final-answer extraction."""
import pytest

from mathverify.intake import (load_solution, load_problem_ir, SchemaError, extract_final_answer,
                               restructure_deterministic, restructure_llm)
from mathverify import LeakageError


def test_structured_loader_validates():
    sol = load_solution({"claimed_answer": {"kind": "value", "payload": "16", "option": "c"},
                         "steps": [{"claim": "a = 16", "kind": "eq"}]})
    assert sol.claimed_answer.option == "C"
    assert sol.steps[0].id == "s1"
    with pytest.raises(SchemaError):
        load_solution({"steps": []})
    with pytest.raises(SchemaError):
        load_solution({"claimed_answer": {"kind": "vector", "payload": "1"}})
    with pytest.raises(SchemaError):
        load_solution({"claimed_answer": {"kind": "value", "payload": "1"}, "steps": [{"kind": "eq"}]})
    with pytest.raises(LeakageError):
        load_solution({"claimed_answer": {"kind": "value", "payload": "1"}, "gold_answer": "1"})


def test_problem_ir_loader_validates():
    ir = load_problem_ir('{"task": {"kind": "evaluate", "params": {"expr": "2+2"}}}')
    assert ir.task.kind == "evaluate"
    with pytest.raises(SchemaError):
        load_problem_ir({"givens": []})
    with pytest.raises(SchemaError):
        load_problem_ir({"task": {"kind": "evaluate"}, "answer_shape": "matrix"})
    with pytest.raises(SchemaError):
        load_problem_ir({"task": {"kind": "teleport"}}, strict_kind=True)


@pytest.mark.parametrize("text,kind,payload,option", [
    ("... buradan x = 4 bulunur.\nCevap: 4", "value", "4", None),
    ("Sonuç olarak $\\boxed{\\frac{\\pi}{6}}$ elde edilir.", "value", "\\frac{\\pi}{6}", None),
    ("Dolayısıyla doğru seçenek C şıkkıdır.", "value", None, "C"),
    ("Cevap: 16 (C)", "value", "16", "C"),
    ("Çözüm kümesi: {4}", "set", "{4}", None),
    ("Cevap: (-2, 7)", "interval", "(-2, 7)", None),
    ("Sağdan ve soldan limitler farklı olduğundan limit yoktur.", "dne", None, None),
    ("Cevap: 10.000 TL", "value", "10000", None),
    ("Cevap: 3,5 saat", "value", "3.5", None),
])
def test_extract_final_answer(text, kind, payload, option):
    ca = extract_final_answer(text)
    assert ca is not None
    assert ca.kind == kind
    assert ca.payload == payload
    assert ca.option == option


def test_no_marker_returns_none():
    assert extract_final_answer("Bu çözümde hiçbir sonuç belirtilmemiştir.") is None
    assert restructure_deterministic("...") is None


def test_llm_restructuring_is_deferred_to_f3():
    with pytest.raises(NotImplementedError):
        restructure_llm("Cevap: 4")
