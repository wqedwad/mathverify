"""The F3 report renderer, exercised offline.

`render_md` only runs when a sweep has credit, so a crash or a misleading line in it stays
invisible until money is being spent. Both happened: the "Yol (b)" section reported 218 items
for a path that had actually run on 34, because the other 184 had silently fallen back to the
deterministic answer-only extractor.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.run_f3 import render_md  # noqa: E402
from harness.metrics import summarize  # noqa: E402


class _Args:
    no_l4 = no_l5 = no_l6 = False
    pathb = True
    include_exemplars = False


def _rec(id_, cell, verdict, *, n_steps, pb_verdict=None, flags=()):
    return {"labels": {"id": id_, "cell": cell, "level": "TYT", "topic": "problemler",
                       "solution_is_correct": cell in ("A", "B"), "first_bad_step": None},
            "verdict": verdict, "confidence": 0.99, "first_bad_step": None, "flags": [],
            "stage": "done", "ir_accepted": True, "ir_reason": "roundtrip_passed", "ir_rounds": 1,
            "judge_scores": {"anthropic": 10, "meta": 10}, "ir_task_kind": "evaluate",
            "hand_task_kind": "evaluate", "hand_verdict": verdict, "cost_usd": 0.1, "calls": 3,
            "ms": 1000.0, "layers": [], "l4": None, "l5": None, "l6": None,
            "pathb": {"verdict": pb_verdict or verdict, "confidence": 0.99, "first_bad_step": None,
                      "flags": list(flags), "answers_agree": True, "downgraded": [],
                      "n_steps": n_steps, "cost_usd": 0.02, "calls": 1}}


def test_the_path_b_section_separates_real_restructuring_from_the_fallback():
    records = [
        # genuinely restructured: steps exist, the broken one is caught
        _rec("i1", "D", "INCORRECT", n_steps=3, pb_verdict="INCORRECT"),
        # fell back to the answer-only extractor: no steps, so a D cell cannot be caught
        _rec("i2", "D", "INCORRECT", n_steps=0, pb_verdict="CORRECT",
             flags=("answer_level_only",)),
        _rec("i3", "A", "CORRECT", n_steps=0, pb_verdict="CORRECT",
             flags=("answer_level_only",)),
    ]
    md = render_md(summarize(records), records, _Args())
    assert "Gerçekten yeniden yapılandırılan" in md
    assert "Deterministik cevap-çıkarıcıya düşen: **2/3**" in md
    assert "D tespiti 1/1" in md, "the real-restructuring block must not be diluted by fallbacks"
    assert "answer_level_only`): 2/3" in md


def test_the_renderer_survives_a_sweep_with_no_path_b_records():
    records = [_rec("i1", "A", "CORRECT", n_steps=2)]
    for r in records:
        r.pop("pathb")

    class _NoPathB(_Args):
        pathb = False

    md = render_md(summarize(records), records, _NoPathB())
    assert "Yol (b)" not in md


def test_a_fatal_record_is_visible_in_the_report():
    """A sweep stopped by an empty balance must not look like a sweep that simply abstained."""
    rec = _rec("i1", "A", "UNKNOWN", n_steps=0)
    rec["fatal"] = "LLMCreditError: credit balance is too low"
    rec["flags"] = ["llm_fatal"]
    rec["ir_accepted"] = False
    rec["ir_reason"] = "llm_error: credit balance is too low"
    md = render_md(summarize([rec]), [rec], _Args())
    assert "i1" in md and "UNKNOWN" in md
