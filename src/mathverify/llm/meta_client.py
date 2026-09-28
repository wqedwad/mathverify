"""Meta family client — Meta Model API (Muse Spark), OpenAI-compatible chat completions.

Endpoint: POST https://api.meta.ai/v1/chat/completions, `Authorization: Bearer <key>`.
Parameters used: reasoning_effort (Muse Spark always reasons; "xhigh" is the maximum),
temperature 0 + seed 0 (determinism is *not* guaranteed by the API — the record/replay
cache provides it), max_completion_tokens, response_format json_schema for structured
output. Requests stream by default and the SSE deltas are concatenated; the last event carries
`usage` without `stream_options` (measured 28 Sep 2026). A non-streaming request (`stream=False`)
can hit a time limit on the way (HTTP 504, or 502 from a proxy) and is retried as a stream.
Implemented with the standard library (urllib) — no third-party OpenAI shim.
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

from .base import LLMResponse, LLMError, LLMCreditError, LLMAuthError, extract_json, cost_usd
from .cache import LLMCache, default_cache

__all__ = ["MetaClient"]

_URL = "https://api.meta.ai/v1/chat/completions"
_EFFORT = {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh", "max": "xhigh"}


def tls_context() -> ssl.SSLContext:
    """The default verified context without VERIFY_X509_STRICT. Python 3.13+ sets that flag, and the
    Claude Code cloud's egress proxy re-signs TLS with a CA that has no key-usage extension: every
    request failed with "CA cert does not include key usage extension" (27 Sep 2026), while curl
    passed. The chain and the host name are still verified (CERT_REQUIRED, check_hostname); only
    the stricter RFC 5280 profile checks are dropped."""
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


class MetaClient:
    provider = "meta"
    family = "meta"

    def __init__(self, model: str | None = None, cache: LLMCache | None = None, timeout: float = 900.0,
                 max_retries: int = 4, stream: bool = True):
        self.model = model or os.environ.get("MATHVERIFY_META_MODEL", "muse-spark-1.3")
        self.cache = cache or default_cache()
        self.timeout = timeout
        self.max_retries = max_retries
        # Streaming from the first attempt: through the cloud's egress proxy a non-streaming call
        # that has not answered in ~31 s ends with 502, while a stream's headers arrive at once
        # (measured 28 Sep 2026, ayt-tur-001: 502 at 31 s, then the stream finished in 58 s).
        # `stream` is not part of the cache key, so cached answers are unaffected.
        self.stream = stream
        self._key = os.environ.get("META_MODEL_API_KEY")

    def _body(self, system: str | list[str], user: str, schema: dict | None, effort: str, max_tokens: int,
              stream: bool) -> dict[str, Any]:
        # `system` may be a list of stable prefix blocks; they are sent as separate developer
        # messages in a fixed order so Meta's automatic prefix cache (cached input $0.15/MTok
        # vs $1.25) can hit on everything before the volatile question.
        blocks = [system] if isinstance(system, str) else [b for b in system if b]
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "developer", "content": b} for b in blocks] + [{"role": "user", "content": user}],
            "temperature": 0,
            "seed": 0,
            "reasoning_effort": _EFFORT.get(effort, "xhigh"),
            "max_completion_tokens": max_tokens,
            "stream": stream,
        }
        if schema is not None:
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "output", "schema": schema, "strict": True}}
        return body

    def _post(self, body: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        """Return (json_response, text). Streams when body['stream'] is True."""
        if not self._key:
            raise LLMError("META_MODEL_API_KEY is not set")
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(_URL, data=data, method="POST", headers={
            "Authorization": f"Bearer {self._key}", "Content-Type": "application/json",
            "Accept": "text/event-stream" if body.get("stream") else "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout, context=tls_context()) as resp:
            if not body.get("stream"):
                payload = json.loads(resp.read().decode("utf-8"))
                return payload, ""
            chunks: list[str] = []
            last: dict[str, Any] = {}
            for raw in resp:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                d = line[5:].strip()
                if d == "[DONE]":
                    break
                try:
                    ev = json.loads(d)
                except json.JSONDecodeError:
                    continue
                last = ev
                for ch in ev.get("choices", []):
                    delta = ch.get("delta", {}) or {}
                    if delta.get("content"):
                        chunks.append(delta["content"])
            return last, "".join(chunks)

    def complete(self, system: str | list[str], user: str, *, schema: dict | None = None, effort: str = "xhigh",
                 max_tokens: int = 16000, tag: str = "") -> LLMResponse:
        body = self._body(system, user, schema, effort, max_tokens, stream=False)
        key = self.cache.key(self.provider, self.model, {k: v for k, v in body.items() if k != "stream"})
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
        text, payload, err = "", None, None
        stream = self.stream
        for attempt in range(self.max_retries + 1):
            try:
                payload, text = self._post(dict(body, stream=stream))
                if not stream:
                    choice = (payload.get("choices") or [{}])[0]
                    text = ((choice.get("message") or {}).get("content")) or ""
                    if isinstance(text, list):
                        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
                err = None
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:300]
                err = f"HTTP {e.code}: {detail}"
                if e.code in (502, 504, 524, 408) and not stream:
                    # retry the same request as a stream, at once. The cloud's egress proxy answers
                    # a non-streaming call still running at ~31 s with 502 "upstream request failed":
                    # 61 of 179 items failed after five such attempts (K4, 28 Sep 2026)
                    stream = True
                elif e.code in (429, 500, 502, 503):
                    time.sleep(min(60, 2 ** attempt * 3))
                elif e.code in (401, 403):
                    raise LLMAuthError(f"meta auth error {err}") from e
                elif e.code == 402 or any(w in detail.lower() for w in ("credit", "quota", "billing", "balance")):
                    raise LLMCreditError(f"meta credit/billing: {err}") from e
                else:
                    raise LLMError(f"meta API error {err}") from e
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                err = f"connection: {e}"
                time.sleep(min(60, 2 ** attempt * 3))
        if err is not None:
            raise LLMError(f"meta API failed after retries: {err}")
        latency = (time.perf_counter() - t0) * 1000
        choice = (payload.get("choices") or [{}])[0] if payload else {}
        finish = choice.get("finish_reason") or ("stop" if text else None)
        stop = {"stop": "end_turn", "length": "max_tokens", "content_filter": "refusal"}.get(finish, finish)
        usage = (payload or {}).get("usage") or {}
        in_tok, out_tok = int(usage.get("prompt_tokens", 0) or 0), int(usage.get("completion_tokens", 0) or 0)
        parsed = None
        if schema is not None and text:
            try:
                parsed = extract_json(text)
            except Exception:
                parsed = None
        served = (payload or {}).get("model", self.model)
        resp = LLMResponse(text=text, parsed=parsed, provider=self.provider, model=served, input_tokens=in_tok,
                           output_tokens=out_tok, cost_usd=cost_usd(served, in_tok, out_tok), latency_ms=latency,
                           cached=False, stop_reason=stop, request_id=(payload or {}).get("id"),
                           meta={"effort": effort, "tag": tag, "streamed": stream})
        self.cache.put(key, {"provider": self.provider, "model": self.model, "tag": tag,
                             "request": {k: v for k, v in body.items() if k != "stream"},
                             "response": {k: getattr(resp, k) for k in LLMResponse.__dataclass_fields__ if k != "cached"}})
        return resp
