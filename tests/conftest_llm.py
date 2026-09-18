"""Scripted LLM clients for offline tests of the F3/F4 layers.

Every LLM role in this project goes through `mathverify.llm.get_client(family)`, so a test
can pin both families to a scripted client and exercise the real extraction / round-trip /
re-solve / critic code paths with no network, no keys and no cost.
"""
from __future__ import annotations

from typing import Any, Callable

from mathverify.llm import LLMResponse, LLMError, set_client_override, clear_client_overrides
from mathverify.llm.schemas import ir_to_llm

__all__ = ["ScriptedClient", "pin", "unpin", "ir_reply", "judge_reply", "solution_reply",
           "critic_reply", "meta_reply"]


class ScriptedClient:
    """Returns a scripted payload per call. `script` maps a tag to either a payload dict, a
    list of payloads (one per successive call) or a callable(system, user, n) -> payload.
    A payload of None means "reply with no parseable JSON"; an LLMError instance is raised."""

    def __init__(self, family: str, script: dict[str, Any], model: str | None = None):
        self.family = self.provider = family
        self.model = model or f"scripted-{family}"
        self.script = script
        self.calls: list[tuple[str, str]] = []
        self._counts: dict[str, int] = {}

    def complete(self, system, user: str, *, schema=None, effort: str = "xhigh",
                 max_tokens: int = 16000, tag: str = "") -> LLMResponse:
        n = self._counts.get(tag, 0)
        self._counts[tag] = n + 1
        self.calls.append((tag, user))
        spec = self.script.get(tag, None)
        if isinstance(spec, list):
            payload = spec[min(n, len(spec) - 1)] if spec else None
        elif callable(spec):
            payload = spec(system, user, n)
        else:
            payload = spec
        if isinstance(payload, LLMError):
            raise payload
        if isinstance(payload, Exception):
            raise payload
        return LLMResponse(text="{}" if payload is None else "scripted", parsed=payload,
                           provider=self.provider, model=self.model, input_tokens=10, output_tokens=10,
                           cost_usd=0.0, latency_ms=1.0, cached=False, stop_reason="end_turn",
                           meta={"tag": tag, "effort": effort})

    def count(self, tag: str) -> int:
        return self._counts.get(tag, 0)


def pin(anthropic_script: dict[str, Any], meta_script: dict[str, Any] | None = None
        ) -> tuple[ScriptedClient, ScriptedClient]:
    a = ScriptedClient("anthropic", anthropic_script)
    m = ScriptedClient("meta", meta_script if meta_script is not None else anthropic_script)
    set_client_override("anthropic", a)
    set_client_override("meta", m)
    return a, m


def unpin() -> None:
    clear_client_overrides()


# ---------------------------------------------------------------- payload helpers
def ir_reply(ir: dict[str, Any], *, question_en: str = "q", confidence: int = 10,
             assumptions: list[str] | None = None) -> dict[str, Any]:
    """Render a hand-written IR dict in the extractor's output format."""
    d = ir_to_llm(ir, question_en=question_en, topic=ir.get("topic") or "", level=ir.get("level") or "TYT")
    d["confidence"] = confidence
    d["assumptions"] = assumptions or []
    return d


def judge_reply(score: int, discrepancies: list[str] | None = None, notes: str = "") -> dict[str, Any]:
    return {"score": score, "faithful": score >= 9, "discrepancies": discrepancies or [], "notes": notes}


def solution_reply(kind: str, payload: str | None, option: str = "", steps: list[dict] | None = None,
                   final: str = "") -> dict[str, Any]:
    return {"claimed_answer": {"kind": kind, "payload": payload if payload is not None else "",
                               "option": option},
            "steps": steps or [], "final_answer_text": final or str(payload)}


def critic_reply(assessment: str = "all_steps_valid", first_bad_step: str = "", error_kind: str = "",
                 explanation: str = "", counter_check: str = "", answer_correct_regardless: bool = True,
                 confidence: int = 8) -> dict[str, Any]:
    return {"assessment": assessment, "first_bad_step": first_bad_step, "error_kind": error_kind,
            "explanation": explanation, "counter_check": counter_check,
            "answer_correct_regardless": answer_correct_regardless, "confidence": confidence}


def meta_reply(error_is_real: bool, confidence: int = 9, explanation: str = "",
               corrected_step: str = "") -> dict[str, Any]:
    return {"error_is_real": error_is_real, "confidence": confidence, "explanation": explanation,
            "corrected_step": corrected_step}
