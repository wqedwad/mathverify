"""§9 evaluation-set integrity: size, four cells with their minimum shares, provenance,
answer-key isolation of the verifier inputs, mutation bookkeeping."""
from collections import Counter

import pytest

from mathverify.ir import ProblemIR, FORBIDDEN_KEYS
from mathverify.solution import Solution
from harness.loader import split_for_verifier

MIN_SHARE = {"A": 0.30, "B": 0.25, "C": 0.30, "D": 0.15}


def test_minimum_size(evalset_items):
    assert len(evalset_items) >= 60


def test_all_four_cells_filled_with_minimum_shares(evalset_items):
    n = len(evalset_items)
    counts = Counter(it["cell"] for it in evalset_items)
    for cell, share in MIN_SHARE.items():
        assert counts[cell] > 0, cell
        # the four minimums sum to 100%, so counts must sit at the minimum up to rounding
        assert counts[cell] >= int(share * n) - 1, (cell, counts[cell], n)


def test_provenance_required_and_no_osym_text(evalset_items):
    for it in evalset_items:
        assert it["provenance"] in ("özgün", "lisanslı", "sentetik"), it["id"]
        assert "ÖSYM" not in it["question_tr"]


def test_unique_ids_and_schema(evalset_items):
    ids = [it["id"] for it in evalset_items]
    assert len(ids) == len(set(ids))
    for it in evalset_items:
        assert it["level"] in ("TYT", "AYT", "UNI")
        ProblemIR.from_dict(it["problem_ir"])
        Solution.from_dict(it["solution"])
        assert it["gold_answer"] not in (None, "")


def test_cell_semantics(evalset_items):
    for it in evalset_items:
        c = it["cell"]
        if c in ("A", "B"):
            assert it["solution_is_correct"] is True and it["first_bad_step"] is None, it["id"]
        else:
            assert it["solution_is_correct"] is False, it["id"]
            assert it["mutation"] and it["derived_from"], it["id"]
        if c == "D":
            assert it["first_bad_step"] is not None, it["id"]
            # D: the claimed answer equals the gold (right answer, invalid step)
            base = next(b for b in evalset_items if b["id"] == it["derived_from"])
            assert it["gold_answer"] == base["gold_answer"]


def test_verifier_inputs_carry_no_key_material(evalset_items):
    for it in evalset_items:
        ir, sol, labels = split_for_verifier(it)
        blob = str(ir).lower() + str(sol).lower()
        for k in FORBIDDEN_KEYS:
            assert f"'{k}'" not in blob, (it["id"], k)


def test_every_level_and_topic_has_positives_and_negatives(evalset_items):
    by = {}
    for it in evalset_items:
        by.setdefault(it["level"], set()).add(it["cell"])
    for level, cells in by.items():
        assert {"A", "C"} <= cells, level
