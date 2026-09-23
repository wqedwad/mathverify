"""harness.soundness_fuzz: a missed broken step carries the reason the step layer measured.

The report used to print one fixed explanation for every miss. The classification below is
what the `nedeni açıklanmayan kaçırılan bozuk adım` gate in scripts/check.py reads."""
import json
from pathlib import Path
from types import SimpleNamespace as NS

from harness.soundness_fuzz import ACCEPTED_MISS_REASONS, _missed_step_reason, step_perturbations

ITEMS = Path(__file__).resolve().parents[1] / "evalset" / "items"


def _res(*entries):
    return NS(layers=[NS(layer="certify.algebra", evidence={}),
                      NS(layer="steps.refute", evidence={"steps": list(entries)})])


def test_an_undeclared_symbol_is_named():
    e = {"id": "s2", "status": "skipped",
         "reason": "undeclared_symbol: unknown identifier(s) ['u'] in 'u ' (declare them in the IR)"}
    assert _missed_step_reason(_res(e), "s2", lambda: False) == {
        "status": "skipped", "reason": "undeclared_symbol", "detail": "u"}


def test_unsolved_premises_are_accepted_only_when_the_answer_is_the_empty_set():
    e = {"id": "s2", "status": "unknown", "evidence": {"reason": "premises_inconsistent_or_unsolved"}}
    assert _missed_step_reason(_res(e), "s2", lambda: True)["reason"] == "premises_have_no_solution"
    # a solver that merely failed to solve must not pass as "no solution"
    r = _missed_step_reason(_res(e), "s2", lambda: False)
    assert r["reason"] == "premises_inconsistent_or_unsolved" and r["reason"] not in ACCEPTED_MISS_REASONS


def test_a_verified_or_refuted_broken_step_is_never_an_accepted_miss():
    for status in ("verified", "refuted"):
        r = _missed_step_reason(_res({"id": "s1", "status": status, "evidence": {}}), "s1", lambda: True)
        assert r["reason"] == status and r["reason"] not in ACCEPTED_MISS_REASONS
    assert _missed_step_reason(_res(), "s1", lambda: True)["reason"] == "step_not_in_evidence"
    assert _missed_step_reason(NS(layers=[]), "s1", lambda: True)["reason"] == "steps_layer_absent"


def test_real_misses_are_classified_from_the_step_layer():
    items = [json.loads((ITEMS / f"{i}.json").read_text(encoding="utf-8"))
             for i in ("tyt-den-003", "tyt-den-007")]
    out = step_perturbations(items)
    got = {m["id"]: (m["reason"], m["detail"], m["accepted"]) for m in out["missed_breaks"]}
    assert got == {"tyt-den-003": ("premises_have_no_solution", "", True),
                   "tyt-den-007": ("undeclared_symbol", "u", True)}
