"""Evaluation-set builder helpers (handoff §9).

Items are authored as Python data (one module per topic) and emitted as JSON files
under evalset/items/. The builder enforces:
  * every item has all §9 fields, a provenance, and a cell A/B/C/D;
  * the problem IR never contains key-like fields (LeakageError otherwise);
  * cell semantics: A/B => solution_is_correct True; C/D => False, D has a correct
    gold answer with an invalid step, C has a wrong claimed answer;
  * C items are derived from A/B items by explicit, named mutations (§9: sign flip,
    dropped root, sqrt ± loss, inequality direction, domain violation, unit error,
    degree/radian confusion, integration constant, chain rule, log domain).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ITEMS_DIR = ROOT / "evalset" / "items"
sys.path.insert(0, str(ROOT / "src"))

from mathverify.ir import ProblemIR  # noqa: E402
from mathverify.solution import Solution  # noqa: E402

CELLS = {"A", "B", "C", "D"}
LEVELS = {"TYT", "AYT", "UNI"}
MUTATIONS = {
    "sign_flip", "dropped_root", "sqrt_pm_loss", "inequality_direction", "root_loss",
    "domain_violation", "unit_error", "degree_radian", "integration_constant", "chain_rule",
    "log_domain", "arithmetic_slip", "wrong_option", "extraneous_root", "endpoint_error",
    "one_sided_limit", "wrong_formula", "missing_case", "wrong_identity", "off_by_one",
}


def steps(*rows) -> list[dict[str, Any]]:
    """rows: (id, kind, claim, from_ids, text)"""
    out = []
    for r in rows:
        sid, kind, claim, frm, text = (list(r) + ["", "", [], ""])[:5] if len(r) < 5 else r
        out.append({"id": sid, "kind": kind, "claim": claim, "from": list(frm), "text": text})
    return out


def item(id: str, cell: str, level: str, topic: str, question_tr: str, ir: dict, solution: dict,
         gold_answer: str, *, options: dict | None = None, solution_text: str = "",
         solution_is_correct: bool | None = None, first_bad_step: int | None = None, notes: str = "",
         provenance: str = "sentetik", mutation: str | None = None, derived_from: str | None = None) -> dict:
    assert cell in CELLS, cell
    assert level in LEVELS, level
    if solution_is_correct is None:
        solution_is_correct = cell in ("A", "B")
    if cell in ("A", "B"):
        assert solution_is_correct and first_bad_step is None, id
    if cell == "C":
        assert not solution_is_correct, id
    if cell == "D":
        assert not solution_is_correct and first_bad_step is not None, id
    if mutation is not None:
        assert mutation in MUTATIONS, mutation
    ir = copy.deepcopy(ir)
    if options is not None and "options" not in ir:
        ir["options"] = options
    ir.setdefault("level", level)
    ir.setdefault("topic", topic)
    ProblemIR.from_dict(ir)            # raises LeakageError / schema errors early
    Solution.from_dict(solution)
    return {
        "id": id, "cell": cell, "level": level, "topic": topic, "question_tr": question_tr,
        "options": options, "gold_answer": gold_answer, "problem_ir": ir, "solution": solution,
        "solution_text": solution_text, "solution_is_correct": solution_is_correct,
        "first_bad_step": first_bad_step, "notes": notes, "provenance": provenance,
        "mutation": mutation, "derived_from": derived_from,
    }


def mutate(base: dict, new_id: str, *, mutation: str, claimed: dict | None = None, steps_: list | None = None,
           first_bad_step: int | None = None, notes: str = "", solution_text: str | None = None,
           cell: str = "C") -> dict:
    """Derive a C (wrong answer) or D (right answer, invalid step) item from a base item."""
    sol = copy.deepcopy(base["solution"])
    if claimed is not None:
        sol["claimed_answer"] = claimed
    if steps_ is not None:
        sol["steps"] = steps_
    return item(new_id, cell, base["level"], base["topic"], base["question_tr"], base["problem_ir"], sol,
                base["gold_answer"], options=base.get("options"),
                solution_text=solution_text if solution_text is not None else base.get("solution_text", ""),
                solution_is_correct=False, first_bad_step=first_bad_step,
                notes=notes or f"{mutation} mutation of {base['id']}", provenance=base["provenance"],
                mutation=mutation, derived_from=base["id"])


def mc(*vals: str) -> dict[str, str]:
    return dict(zip("ABCDE", [str(v) for v in vals]))


def write_items(items: list[dict], clear_prefix: str | None = None) -> int:
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    if clear_prefix:
        for f in ITEMS_DIR.glob(f"{clear_prefix}*.json"):
            f.unlink()
    ids = set()
    for it in items:
        assert it["id"] not in ids, f"duplicate id {it['id']}"
        ids.add(it["id"])
        (ITEMS_DIR / f"{it['id']}.json").write_text(json.dumps(it, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(items)
