"""Solution schema — the *structured* intake format (D1 path (a)).

A solver that feeds this verifier must emit each step as a single-result lemma
with explicit premise references (handoff §3, "structure buys verifiability").
Path (b) (external free-text solutions) goes through `intake/restructure.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from .ir import _scan_forbidden

ANSWER_KINDS = {"value", "set", "expression", "count", "interval", "dne",
                "infinite", "condition", "equation", "none"}
STEP_KINDS = {"eq", "compute", "assert", "case", "note", "conclude"}


@dataclass
class ClaimedAnswer:
    kind: str                       # one of ANSWER_KINDS
    payload: str | list[str] | int | None = None   # sympy/LaTeX text, list of texts, or count
    option: str | None = None       # "A".."E" for multiple choice
    raw: str | None = None          # untouched text from the solver (never parsed for logic)

    def __post_init__(self):
        if self.kind not in ANSWER_KINDS:
            raise ValueError(f"unknown answer kind {self.kind!r}")
        if self.option is not None:
            self.option = self.option.strip().upper()


@dataclass
class Step:
    id: str
    claim: str                      # machine-readable (sympy syntax / LaTeX); "" for prose-only
    kind: str = "eq"
    from_ids: list[str] = field(default_factory=list)
    text: str = ""                  # human justification; ignored by deterministic checks

    def __post_init__(self):
        if self.kind not in STEP_KINDS:
            raise ValueError(f"unknown step kind {self.kind!r}")


@dataclass
class Solution:
    claimed_answer: ClaimedAnswer
    steps: list[Step] = field(default_factory=list)
    raw_text: str = ""
    source: str = "structured"       # "structured" (path a) | "restructured" (path b)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Solution":
        _scan_forbidden(d)
        ca = d["claimed_answer"]
        if isinstance(ca, str):
            ca = {"kind": "value", "payload": ca}
        ca_obj = ClaimedAnswer(**ca)
        steps = []
        for i, s in enumerate(d.get("steps", [])):
            s = dict(s)
            s.setdefault("id", f"s{i+1}")
            if "from" in s:
                s["from_ids"] = s.pop("from")
            steps.append(Step(**s))
        return cls(claimed_answer=ca_obj, steps=steps,
                   raw_text=d.get("raw_text", ""), source=d.get("source", "structured"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def step_index(self, step_id: str) -> int | None:
        for i, s in enumerate(self.steps):
            if s.id == step_id:
                return i + 1
        return None
