"""Load evaluation items and split them into (verifier input, harness-held labels)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GOLD_FIELDS = ("gold_answer", "solution_is_correct", "first_bad_step", "cell", "notes",
               "mutation", "derived_from")


def load_items(items_dir: Path) -> list[dict[str, Any]]:
    items = []
    for f in sorted(Path(items_dir).glob("*.json")):
        items.append(json.loads(f.read_text(encoding="utf-8")))
    return items


def split_for_verifier(it: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return (problem_ir, solution, labels). The first two contain no key material."""
    ir = json.loads(json.dumps(it["problem_ir"]))
    sol = json.loads(json.dumps(it["solution"]))
    labels = {k: it.get(k) for k in GOLD_FIELDS}
    labels["id"] = it["id"]
    labels["level"] = it["level"]
    labels["topic"] = it["topic"]
    for k in GOLD_FIELDS:
        assert k not in ir and k not in sol, f"{it['id']}: key-like field leaked into verifier input"
    return ir, sol, labels
