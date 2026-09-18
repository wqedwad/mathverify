"""Output contract (handoff §1). Field names/semantics are frozen."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

Verdict = Literal["CORRECT", "INCORRECT", "UNKNOWN"]
LayerVerdict = Literal["pass", "fail", "unknown"]


@dataclass
class LayerResult:
    layer: str                       # "certify.calculus", "equiv.sets", ...
    verdict: LayerVerdict
    confidence: float                # 0.0 - 1.0
    hard: bool                       # True => VETO power in fusion (deterministic proof)
    evidence: dict[str, Any]         # {"code": str, "output": str, "seed": int, ...}
    latency_ms: float
    cost_usd: float = 0.0
    # --- Phase-1 additions (do not break the §1 contract) ---
    primary: bool = False            # router-assigned: this certificate alone may ground CORRECT
    first_bad_step: int | None = None
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    verdict: Verdict
    confidence: float
    first_bad_step: int | None       # only when a deterministic layer localised it
    layers: list[LayerResult]
    decision_trace: str              # human-readable rationale
    versions: dict[str, str]         # sympy/mpmath/z3/python versions written into the decision
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "first_bad_step": self.first_bad_step,
            "layers": [l.to_dict() for l in self.layers],
            "decision_trace": self.decision_trace,
            "versions": dict(self.versions),
            "flags": list(self.flags),
        }
