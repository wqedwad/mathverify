"""D1 intake paths: structured loader validation and deterministic final-answer extraction."""
import pytest

from mathverify.intake import (load_solution, load_problem_ir, SchemaError, extract_final_answer,
                               restructure_deterministic)
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


def test_tuple_vs_interval_disambiguation():
    # the IR's answer_shape (never the solution) decides what "(a, b)" means
    assert extract_final_answer("Cevap: (1, 1)", answer_shape="expression").kind == "value"
    assert extract_final_answer("Cevap: (-2, 7)", answer_shape="interval").kind == "interval"
    assert extract_final_answer("Özvektör (1, 1) bulunur. Cevap: (1, 1)").kind == "value"     # context word
    assert extract_final_answer("Cevap: (-2, 7)").kind == "interval"                          # default


def test_no_marker_returns_none():
    assert extract_final_answer("Bu çözümde hiçbir sonuç belirtilmemiştir.") is None
    assert restructure_deterministic("...") is None


def test_deterministic_path_b_never_invents_steps():
    """Path (b) without a model may read the final answer and nothing else. Reconstructing steps
    is the LLM pass in `extract/restructure_llm.py`; if this module ever started guessing them,
    the step layer would be judging text we made up rather than the solver's reasoning."""
    sol = restructure_deterministic("Once 3 ile carpariz, sonra 2 ekleriz. Cevap: 4")
    assert sol is not None and sol.claimed_answer.payload == "4"
    assert sol.steps == [] and sol.source == "restructured"


def test_the_llm_restructuring_pass_lives_outside_intake():
    import mathverify.intake as intake
    assert not hasattr(intake, "restructure_llm")
    from mathverify.extract.restructure_llm import restructure_solution
    assert callable(restructure_solution)


# ------------------------------------------------------------------ B2: what the letter hides
def test_a_set_claim_is_recovered_when_only_the_option_letter_was_marked():
    """Measured hole: for "x ∈ {30, 150, 210, 330}. Cevap: B" the extractor kept only the
    letter, the verifier then filled the payload from that same letter and checked the option
    against itself — a wrong solution was called CORRECT."""
    ca = extract_final_answer("x ∈ {30, 150, 210, 330}. Cevap: B", answer_shape="set")
    assert ca.option == "B"
    assert ca.kind == "set" and ca.payload == "{30, 150, 210, 330}"
    assert ca.payload_source == "recovered_text"


def test_recovery_stays_out_of_scalar_answers():
    """The first version of this recovery read any `<sym> = <token>` and was wrong on 59 of 94
    items: it picked up intermediate steps and truncated `y = 2x + 1` to `2x`. Only set and
    interval literals are unambiguous enough."""
    ca = extract_final_answer("2a = 32, a = 16. Cevap: C", answer_shape="scalar")
    assert ca.option == "C" and ca.payload is None


def test_a_recovered_claim_can_abstain_but_never_refute():
    from mathverify.verifier import verify
    ir = {"task": {"kind": "solve_equation", "params": {"var": "x"}},
          "vars": [{"name": "x"}], "givens": ["x**2 = 4"], "answer_shape": "set",
          "options": {"A": "{-2, 2}", "B": "{2}"}}
    sol = restructure_deterministic("x ∈ {7, 9}. Cevap: A", answer_shape="set")
    assert sol.claimed_answer.payload_source == "recovered_text"
    r = verify(ir, sol)
    assert "recovered_answer_mismatch" in r.flags
    assert r.verdict != "CORRECT"          # the disagreement blocks a positive verdict
    assert any(l.layer == "mc.consistency" and l.verdict == "unknown" for l in r.layers), \
        "a reconstruction mistake must not be able to produce a hard refutation"


def test_unicode_pi_next_to_a_number_is_a_product():
    """`5π/6` is how free text writes 5*pi/6; the unicode map alone made it `5pi/6`, a syntax
    error. 4 of 5 recovered trig answer sets were unparseable for exactly this reason."""
    from mathverify.normalize.parse import parse_set_str, build_namespace
    ns = build_namespace()
    s = parse_set_str("{π/6, 5π/6, 7π/6, 11π/6}", ns)
    assert len(s.args) == 4
