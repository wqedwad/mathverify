"""Common LLM client contract. Two model *families* are used (handoff §3 rule 3): the solver
and every verifier-side judgement of that solver's work must come from different families."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

__all__ = ["LLMResponse", "LLMClient", "LLMError", "LLMFatalError", "LLMCreditError", "LLMAuthError",
           "extract_json", "PRICING", "cost_usd"]


class LLMError(RuntimeError):
    """A call failed for a reason that is still a *measurement*: the item is recorded as
    unavailable and the sweep continues. Every layer catches this and degrades gracefully."""


class LLMFatalError(RuntimeError):
    """A failure that is NOT a measurement (DECISIONS §23): the run must stop.

    Deliberately **not** a subclass of `LLMError`. Every layer wraps its single call in
    `except LLMError` and turns the failure into a recorded, unavailable item; if these were
    LLMErrors, an empty balance would be silently recorded 218 times instead of stopping the
    sweep once. Measured: the F3 run of 18 Sep 2026 burned 151 items this way, because the
    swallowed message was then truncated below the word the harness was grepping for.
    Whoever genuinely wants to continue must catch this class by name."""


class LLMCreditError(LLMFatalError):
    """The account cannot pay for the call (empty balance / quota). Retrying is pointless:
    the harness aborts the run instead of burning the remaining items."""


class LLMAuthError(LLMFatalError):
    """Bad or missing credentials."""


@dataclass
class LLMResponse:
    text: str
    parsed: Any | None
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    cached: bool = False
    stop_reason: str | None = None
    request_id: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.stop_reason not in ("refusal", "error", "max_tokens") and bool(self.text or self.parsed is not None)


class LLMClient(Protocol):
    provider: str
    family: str
    model: str

    def complete(self, system: str, user: str, *, schema: dict | None = None, effort: str = "xhigh",
                 max_tokens: int = 16000, tag: str = "") -> LLMResponse: ...


# USD per million tokens (input, output). Anthropic first-party rates (claude-api skill,
# cached 2026-06-24). Meta Model API rates from dev.meta.ai at the time of writing; when a
# model is missing here the cost is reported as 0 and flagged in the evidence.
PRICING: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # Meta Model API standard tier (dev.meta.ai/docs/pricing-rate-limits, fetched 2026-09-18)
    "muse-spark-1.3": (1.25, 4.25),
    "muse-spark-1.2": (1.25, 4.25),
    "muse-spark-1.1": (1.25, 4.25),
    "muse-spark-1.3-contributor": (0.10, 0.20),
    "muse-spark-1.2-contributor": (0.10, 0.20),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICING.get(model, (0.0, 0.0))
    return (input_tokens * pin + output_tokens * pout) / 1_000_000


_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Parse JSON from a model reply: raw JSON, fenced JSON, or the outermost {...} block."""
    if text is None:
        raise LLMError("empty reply")
    t = text.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    m = _FENCE.search(t)
    if m:
        return json.loads(m.group(1))
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        return json.loads(t[start:end + 1])
    raise LLMError(f"no JSON object in reply: {t[:200]!r}")


def now_ms() -> float:
    return time.perf_counter() * 1000
