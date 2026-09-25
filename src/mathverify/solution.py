"""Solution schema — the *structured* intake format (D1 path (a)).

A solver that feeds this verifier must emit each step as a single-result lemma
with explicit premise references (handoff §3, "structure buys verifiability").
Path (b) (external free-text solutions) goes through `intake/restructure.py`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any

from .ir import _scan_forbidden

# "(D)", "D)", "D.", "[D]", "D şıkkı" are the letter D; anything else is kept as written (and is then
# not a letter of the question). Before this, "(D)" with the right payload was INCORRECT.
_OPTION_RE = re.compile(r"^[\s(\[]*([A-Za-z])[\s)\].:]*(?:ş[ıi]kk?[ıi]?|şık|sik|sikki)?\s*$", re.IGNORECASE)


def _normalize_option(opt: Any) -> Any:
    if not isinstance(opt, str):
        return opt
    m = _OPTION_RE.match(opt.strip())
    return m.group(1).upper() if m else opt.strip().upper()


ANSWER_KINDS = {"value", "set", "expression", "count", "interval", "dne",
                "infinite", "condition", "equation", "none"}
STEP_KINDS = {"eq", "compute", "assert", "case", "note", "conclude"}


@dataclass
class ClaimedAnswer:
    kind: str                       # one of ANSWER_KINDS
    payload: str | list[str] | int | None = None   # sympy/LaTeX text, list of texts, or count
    option: str | None = None       # "A".."E" for multiple choice
    raw: str | None = None          # untouched text from the solver (never parsed for logic)
    # How confident we are that `payload` is what the solver actually claimed:
    #   None / "solver"  - the solver stated it (path a, or an explicit answer marker)
    #   "option_letter"  - copied from the chosen option; it is the LETTER that was verified
    #   "recovered_text" - reconstructed from free text by the deterministic extractor. Advisory
    #                      only: a mismatch with the option abstains, it never refutes, because
    #                      a recovery mistake must not be able to produce a wrong INCORRECT.
    payload_source: str | None = None

    def __post_init__(self):
        if self.kind not in ANSWER_KINDS:
            raise ValueError(f"unknown answer kind {self.kind!r}")
        if self.option is not None:
            self.option = _normalize_option(self.option)


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


class MalformedSolution(ValueError):
    """The solution does not have the structured shape (a step that is not an object, an id that is
    not text, `from` that is not a list of ids...). Before this existed such a step crashed the
    step layer, the crash was reported as a non-blocking `layer_exception`, and every refutation in
    the solution vanished: one junk step appended to a refuted solution turned INCORRECT into
    CORRECT (audit of 25 Sep 2026). The verifier abstains on it instead."""


def _step_id(v: Any) -> str | None:
    """A step id is a label: `1` and `"1"` name the same step. Anything else is not an id."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def _check_step_shape(n: int, s: dict[str, Any]) -> None:
    sid = _step_id(s.get("id"))
    if sid is None:
        raise MalformedSolution(f"step {n}: id must be non-empty text or an integer")
    s["id"] = sid
    ids = s.get("from_ids", [])
    if ids is None:
        ids = []
    elif not isinstance(ids, (list, tuple)):
        ids = [ids]                              # `"from": "s1"` or `"from": 1` names one step
    labels = [_step_id(x) for x in ids]
    if any(x is None for x in labels):
        raise MalformedSolution(f"step {n}: `from` must list step ids")
    s["from_ids"] = labels
    for key in ("claim", "text", "kind"):
        if s.get(key) is not None and not isinstance(s[key], str):
            raise MalformedSolution(f"step {n}: {key} must be text")


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
        raw_steps = d.get("steps", [])
        if raw_steps is None:
            raw_steps = []
        if not isinstance(raw_steps, (list, tuple)):
            raise MalformedSolution(f"steps must be a list, got {type(raw_steps).__name__}")
        for i, s in enumerate(raw_steps):
            if not isinstance(s, dict):
                raise MalformedSolution(f"step {i + 1} is not an object")
            s = dict(s)
            s.setdefault("id", f"s{i+1}")
            if "from" in s:
                s["from_ids"] = s.pop("from")
            _check_step_shape(i + 1, s)
            if s.get("claim") is None:
                s["claim"] = ""
            if s.get("text") is None:
                s.pop("text", None)
            try:
                steps.append(Step(**s))
            except (TypeError, ValueError) as e:
                raise MalformedSolution(f"step {i + 1}: {e}") from e
        return cls(claimed_answer=ca_obj, steps=steps,
                   raw_text=d.get("raw_text", ""), source=d.get("source", "structured"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def step_index(self, step_id: str) -> int | None:
        for i, s in enumerate(self.steps):
            if s.id == step_id:
                return i + 1
        return None
