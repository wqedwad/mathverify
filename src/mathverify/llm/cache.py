"""Deterministic record/replay cache for LLM calls (handoff §11/13, §12).

Sampling parameters are not available on current Claude models, so determinism of the
LLM layers comes from this cache: every call is keyed by a SHA-256 of (provider, model,
request parameters, system prompt, user prompt, output schema) and the first response is
replayed on every later run. Modes (env MATHVERIFY_LLM_CACHE):
  auto   - replay when present, call and record otherwise (default)
  replay - never call the network; a miss raises CacheMiss (offline tests / CI)
  off    - always call, never record
Records never contain credentials; they contain prompts and responses only.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

__all__ = ["LLMCache", "CacheMiss", "default_cache"]


class CacheMiss(RuntimeError):
    pass


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


class LLMCache:
    def __init__(self, root: Path | str | None = None, mode: str | None = None):
        root = root or os.environ.get("MATHVERIFY_LLM_CACHE_DIR") or (Path(__file__).resolve().parents[3] / "llm_cache")
        self.root = Path(root)
        self.mode = (mode or os.environ.get("MATHVERIFY_LLM_CACHE", "auto")).lower()
        if self.mode not in ("auto", "replay", "off"):
            raise ValueError(f"bad cache mode {self.mode!r}")
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def key(self, provider: str, model: str, request: dict[str, Any]) -> str:
        h = hashlib.sha256()
        h.update(_canonical({"provider": provider, "model": model, "request": request}).encode("utf-8"))
        return h.hexdigest()

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        if self.mode == "off":
            return None
        p = self._path(key)
        if p.exists():
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
                with self._lock:
                    self.hits += 1
                return rec
            except json.JSONDecodeError:
                return None
        with self._lock:
            self.misses += 1
        if self.mode == "replay":
            raise CacheMiss(f"no cached response for {key[:12]}… (cache mode = replay)")
        return None

    def put(self, key: str, record: dict[str, Any]) -> None:
        if self.mode == "off":
            return
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        record = dict(record)
        record.setdefault("recorded_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
        tmp = p.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, p)


_DEFAULT: LLMCache | None = None
_DEFAULT_LOCK = threading.Lock()


def default_cache() -> LLMCache:
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = LLMCache()
        return _DEFAULT
