"""LLM layer (F3+). Two model families, strictly separated roles (handoff §3 rule 3, §11/9):

  family "anthropic"  — Claude (claude-opus-5 by default; MATHVERIFY_ANTHROPIC_MODEL overrides)
  family "meta"       — Muse Spark (muse-spark-1.3; MATHVERIFY_META_MODEL overrides)

Roles:
  extractor      NL question -> Problem IR                       (anthropic)
  judges         IR round-trip fidelity, BOTH families must agree (anthropic + meta)
  solver         the app's own solver, path (a)                  (meta by default)
  resolver(fam)  L4 cross-family re-solve: the family that is NOT `fam`
  critic(fam)    F4 step critic: the family that is NOT `fam`
Credentials come from the environment / a git-ignored .env file and are never logged.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import (LLMResponse, LLMClient, LLMError, LLMCreditError, LLMAuthError, extract_json,
                   PRICING, cost_usd)
from .cache import LLMCache, CacheMiss, default_cache

__all__ = ["LLMResponse", "LLMClient", "LLMError", "LLMCreditError", "LLMAuthError", "extract_json",
           "PRICING", "cost_usd", "LLMCache", "CacheMiss", "default_cache", "load_env", "get_client",
           "other_family", "available_families", "FAMILIES", "ROLE_FAMILY", "llm_versions"]

FAMILIES = ("anthropic", "meta")
ROLE_FAMILY = {"extractor": "anthropic", "judge_a": "anthropic", "judge_b": "meta", "solver": "meta"}

_ENV_LOADED = False
_CLIENTS: dict[str, Any] = {}


def load_env() -> None:
    """Load a project-root .env once (python-dotenv); silently no-op when absent."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return
    root = Path(__file__).resolve().parents[3]
    load_dotenv(root / ".env", override=False)
    load_dotenv(override=False)


def available_families() -> list[str]:
    load_env()
    out = []
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        out.append("anthropic")
    if os.environ.get("META_MODEL_API_KEY"):
        out.append("meta")
    return out


def other_family(family: str) -> str:
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}")
    return "meta" if family == "anthropic" else "anthropic"


def get_client(family: str, model: str | None = None):
    load_env()
    key = f"{family}:{model or ''}"
    if key in _CLIENTS:
        return _CLIENTS[key]
    if family == "anthropic":
        from .anthropic_client import AnthropicClient
        c = AnthropicClient(model=model)
    elif family == "meta":
        from .meta_client import MetaClient
        c = MetaClient(model=model)
    else:
        raise ValueError(f"unknown family {family!r}")
    _CLIENTS[key] = c
    return c


def llm_versions() -> dict[str, str]:
    """Model identifiers written into VerificationResult.versions (§11/13)."""
    load_env()
    return {"llm.anthropic": os.environ.get("MATHVERIFY_ANTHROPIC_MODEL", "claude-opus-5"),
            "llm.meta": os.environ.get("MATHVERIFY_META_MODEL", "muse-spark-1.3"),
            "llm.cache_mode": os.environ.get("MATHVERIFY_LLM_CACHE", "auto")}
