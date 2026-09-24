"""Anthropic family client (official `anthropic` SDK).

Defaults follow the claude-api skill: model `claude-opus-5` (override with
MATHVERIFY_ANTHROPIC_MODEL, e.g. claude-fable-5-1), adaptive thinking, `output_config.effort`
(xhigh by default, max for correctness-critical roles), streaming with `get_final_message()`
so long generations never hit HTTP timeouts, structured outputs via `output_config.format`,
and server-side refusal fallbacks (`fallbacks="default"`, beta server-side-fallback-2026-07-01)
enabled by default. Sampling parameters are not available on this model generation, so
determinism comes from the record/replay cache.
"""
from __future__ import annotations

import os
import time
from typing import Any

from .base import LLMResponse, LLMError, LLMCreditError, LLMAuthError, extract_json, cost_usd
from .cache import LLMCache, default_cache

__all__ = ["AnthropicClient", "DEFAULT_BASE_URL", "resolve_base_url"]

_FALLBACK_BETA = "server-side-fallback-2026-07-01"

# The SDK's own default endpoint (anthropic==1.7.0, `Anthropic.__init__`); a test pins the two
# together so an SDK upgrade that moves the default cannot change this project's endpoint silently.
DEFAULT_BASE_URL = "https://api.anthropic.com"
BASE_URL_ENV = "MATHVERIFY_ANTHROPIC_BASE_URL"


def resolve_base_url() -> str:
    """Endpoint for this project's Anthropic calls.

    The SDK falls back to ANTHROPIC_BASE_URL when `base_url` is omitted. Hosts that run Claude
    Code (the Claude Code cloud sessions, the desktop app) set that variable for Claude Code's
    own traffic, and every child process inherits it; this project must never route its own
    calls, or send its own key, there by accident. The endpoint is therefore always passed
    explicitly: MATHVERIFY_ANTHROPIC_BASE_URL when set and non-empty, else the SDK default.
    """
    return (os.environ.get(BASE_URL_ENV) or "").strip() or DEFAULT_BASE_URL


class AnthropicClient:
    provider = "anthropic"
    family = "anthropic"

    def __init__(self, model: str | None = None, cache: LLMCache | None = None, timeout: float = 1200.0,
                 max_retries: int = 4):
        import anthropic
        self.model = model or os.environ.get("MATHVERIFY_ANTHROPIC_MODEL", "claude-opus-5")
        self.cache = cache or default_cache()
        self._anthropic = anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        # base_url is explicit in both branches (see resolve_base_url). Without a key the SDK still
        # resolves its own credentials (ANTHROPIC_AUTH_TOKEN, then a profile); an explicit base_url
        # only stops a profile's stored endpoint from replacing it.
        base_url = resolve_base_url()
        self._client = anthropic.Anthropic(api_key=api_key, base_url=base_url, timeout=timeout,
                                           max_retries=max_retries) if api_key \
            else anthropic.Anthropic(base_url=base_url, timeout=timeout, max_retries=max_retries)

    def _request(self, system: str | list[str], user: str, schema: dict | None, effort: str,
                 max_tokens: int) -> dict[str, Any]:
        output_config: dict[str, Any] = {"effort": effort}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        # `system` may be a list of stable prefix blocks: the last one carries cache_control so
        # the (large, identical) instruction + exemplar prefix is billed at ~10% on every later
        # call. Order is tools -> system -> messages, so only the volatile question follows it.
        blocks = [system] if isinstance(system, str) else list(system)
        sys_param: list[dict[str, Any]] = [{"type": "text", "text": b} for b in blocks if b]
        if sys_param:
            sys_param[-1]["cache_control"] = {"type": "ephemeral"}
        req: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": sys_param,
            "messages": [{"role": "user", "content": user}],
            "thinking": {"type": "adaptive"},
            "output_config": output_config,
            "betas": [_FALLBACK_BETA],
            "fallbacks": "default",
        }
        return req

    def complete(self, system: str | list[str], user: str, *, schema: dict | None = None, effort: str = "xhigh",
                 max_tokens: int = 16000, tag: str = "") -> LLMResponse:
        req = self._request(system, user, schema, effort, max_tokens)
        key = self.cache.key(self.provider, self.model, req)
        rec = self.cache.get(key)
        t0 = time.perf_counter()
        if rec is not None:
            resp = LLMResponse(**{k: v for k, v in rec["response"].items() if k in LLMResponse.__dataclass_fields__})
            resp.cached = True
            resp.latency_ms = (time.perf_counter() - t0) * 1000
            if schema is not None and resp.parsed is None and resp.text:
                try:
                    resp.parsed = extract_json(resp.text)
                except Exception:
                    pass
            return resp
        anthropic = self._anthropic
        try:
            with self._client.beta.messages.stream(**req) as stream:
                msg = stream.get_final_message()
        except anthropic.RateLimitError as e:
            raise LLMError(f"rate limited: {e}") from e
        except anthropic.AuthenticationError as e:
            raise LLMAuthError(f"anthropic auth error: {e.message}") from e
        except anthropic.APIStatusError as e:
            msg = str(getattr(e, "message", "") or e)
            if "credit balance" in msg.lower() or "quota" in msg.lower() or "billing" in msg.lower():
                raise LLMCreditError(f"anthropic credit/billing: {msg}") from e
            raise LLMError(f"anthropic API error {e.status_code}: {msg}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError(f"anthropic connection error: {e}") from e
        latency = (time.perf_counter() - t0) * 1000
        stop = msg.stop_reason
        text = ""
        if stop != "refusal":
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        parsed = None
        if schema is not None and text:
            try:
                parsed = extract_json(text)
            except Exception:
                parsed = None
        usage = msg.usage
        fresh = int(getattr(usage, "input_tokens", 0) or 0)
        cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        in_tok = fresh + cache_read + cache_write
        out_tok = int(getattr(usage, "output_tokens", 0) or 0)
        served_by = getattr(msg, "model", self.model)
        # cache reads bill at ~0.1x and writes at ~1.25x of the input rate
        cost = cost_usd(served_by, fresh, out_tok) + cost_usd(served_by, cache_read, 0) * 0.1 \
            + cost_usd(served_by, cache_write, 0) * 1.25
        resp = LLMResponse(text=text, parsed=parsed, provider=self.provider, model=served_by,
                           input_tokens=in_tok, output_tokens=out_tok,
                           cost_usd=cost, latency_ms=latency, cached=False,
                           stop_reason=stop, request_id=getattr(msg, "_request_id", None),
                           meta={"effort": effort, "tag": tag, "cache_read": cache_read, "cache_write": cache_write,
                                 "stop_details": (msg.stop_details.model_dump() if getattr(msg, "stop_details", None) else None)})
        self.cache.put(key, {"provider": self.provider, "model": self.model, "tag": tag, "request": req,
                             "response": {k: getattr(resp, k) for k in LLMResponse.__dataclass_fields__ if k != "cached"}})
        return resp
