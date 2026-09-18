"""Metrics (handoff §9): accuracy alone is forbidden. Reported:
positive precision, negative precision, coverage, per-cell/level/topic breakdown,
B-cell false rejection, D-cell detection, step-localisation accuracy.

Two label views are reported:
  * answer-level  (A+B+C): is the CLAIMED ANSWER right?  (D excluded: its answer is right)
  * solution-level (all cells): is the SOLUTION valid?   (D counts as invalid)
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def _prec(tp: int, fp: int) -> float | None:
    return None if tp + fp == 0 else tp / (tp + fp)


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """records: {"labels": {...}, "verdict": str, "confidence": float, "first_bad_step": int|None}"""
    out: dict[str, Any] = {"n": len(records)}

    def block(rs: list[dict[str, Any]], label_fn) -> dict[str, Any]:
        tp = fp = tn = fn = unk = 0
        for r in rs:
            truth = label_fn(r)
            v = r["verdict"]
            if v == "UNKNOWN":
                unk += 1
            elif v == "CORRECT":
                if truth:
                    tp += 1
                else:
                    fp += 1
            else:
                if truth:
                    fn += 1
                else:
                    tn += 1
        n = len(rs)
        return {"n": n, "CORRECT_tp": tp, "CORRECT_fp": fp, "INCORRECT_tn": tn, "INCORRECT_fn": fn, "UNKNOWN": unk,
                "pos_precision": _prec(tp, fp), "neg_precision": _prec(tn, fn),
                "coverage": (n - unk) / n if n else None,
                "false_positives": [r["labels"]["id"] for r in rs if r["verdict"] == "CORRECT" and not label_fn(r)],
                "false_negatives": [r["labels"]["id"] for r in rs if r["verdict"] == "INCORRECT" and label_fn(r)]}

    answer_ok = lambda r: r["labels"]["cell"] in ("A", "B", "D")      # noqa: E731
    solution_ok = lambda r: bool(r["labels"]["solution_is_correct"])  # noqa: E731

    abc = [r for r in records if r["labels"]["cell"] in ("A", "B", "C")]
    out["answer_level_ABC"] = block(abc, answer_ok)
    out["solution_level_ABCD"] = block(records, solution_ok)

    by = {"cell": defaultdict(list), "level": defaultdict(list), "topic": defaultdict(list)}
    for r in records:
        for k in by:
            by[k][r["labels"][k]].append(r)
    out["by_cell"] = {c: block(rs, solution_ok) for c, rs in sorted(by["cell"].items())}
    out["by_level"] = {c: block(rs, solution_ok) for c, rs in sorted(by["level"].items())}
    out["by_topic"] = {c: block(rs, solution_ok) for c, rs in sorted(by["topic"].items())}

    b = by["cell"].get("B", [])
    d = by["cell"].get("D", [])
    out["B_false_rejection"] = (sum(1 for r in b if r["verdict"] == "INCORRECT") / len(b)) if b else None
    out["B_coverage"] = (sum(1 for r in b if r["verdict"] != "UNKNOWN") / len(b)) if b else None
    out["D_detection"] = (sum(1 for r in d if r["verdict"] == "INCORRECT") / len(d)) if d else None
    out["D_false_accept"] = (sum(1 for r in d if r["verdict"] == "CORRECT") / len(d)) if d else None
    loc = [r for r in records if r["labels"].get("first_bad_step") and r["first_bad_step"] is not None]
    out["step_localisation"] = {
        "n_localised": len(loc),
        "exact": (sum(1 for r in loc if r["first_bad_step"] == r["labels"]["first_bad_step"]) / len(loc)) if loc else None,
        "n_labelled": sum(1 for r in records if r["labels"].get("first_bad_step")),
    }
    # level x scope subsets used by the F1 gates
    def subset(level, topics):
        rs = [r for r in records if r["labels"]["level"] == level and r["labels"]["topic"] in topics]
        return block(rs, solution_ok) if rs else None
    out["gate_F1_TYT"] = subset("TYT", {"problemler", "sayılar", "denklem", "eşitsizlik", "fonksiyonlar", "polinom", "kümeler"})
    out["gate_F1_AYT"] = subset("AYT", {"limit", "türev", "integral", "trigonometri", "analitik geometri"})
    return out


def fmt(x, digits=3):
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)
