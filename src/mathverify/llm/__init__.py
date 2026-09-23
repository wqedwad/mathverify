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

from .base import (LLMResponse, LLMClient, LLMError, LLMFatalError, LLMCreditError, LLMAuthError,
                   extract_json, PRICING, cost_usd)
from .cache import LLMCache, CacheMiss, default_cache

__all__ = ["LLMResponse", "LLMClient", "LLMError", "LLMFatalError", "LLMCreditError", "LLMAuthError",
           "extract_json",
           "PRICING", "cost_usd", "LLMCache", "CacheMiss", "default_cache", "load_env", "get_client",
           "other_family", "available_families", "FAMILIES", "ROLE_FAMILY", "JUDGE_ROLES",
           "client_for_role", "judge_families", "llm_versions",
           "set_client_override", "clear_client_overrides"]

FAMILIES = ("anthropic", "meta")
# Which family serves which fixed role (docs/LLM_LAYERS.md). Roles whose family depends on the
# solver — L4 re-solver, L6' critic, meta-verifier, Lean prover — are NOT here: they are derived
# from `solver_family` with `other_family`. Use `client_for_role` so this table is the single
# place the mapping lives; it used to be duplicated as string literals at each call site, which
# is how it became a constant nothing read.
ROLE_FAMILY = {"extractor": "anthropic", "judge_a": "anthropic", "judge_b": "meta", "solver": "meta"}
JUDGE_ROLES = ("judge_a", "judge_b")

_ENV_LOADED = False
_CLIENTS: dict[str, Any] = {}
_OVERRIDES: dict[str, Any] = {}


def set_client_override(family: str, client: Any) -> None:
    """Force `get_client(family)` to return `client`. Used to pin a specific model in
    production and to run the LLM layers against scripted clients in the test-suite."""
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}")
    _OVERRIDES[family] = client


def clear_client_overrides() -> None:
    _OVERRIDES.clear()


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
    if family in _OVERRIDES:
        return _OVERRIDES[family]
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


def client_for_role(role: str, model: str | None = None):
    """Client for a fixed role, via ROLE_FAMILY. Raises on an unknown role rather than
    silently falling back to a default family — a wrong family here breaks the §3 rule 3
    separation without any visible symptom."""
    if role not in ROLE_FAMILY:
        raise ValueError(f"unknown role {role!r}; fixed roles are {sorted(ROLE_FAMILY)}")
    return get_client(ROLE_FAMILY[role], model)


def judge_families() -> tuple[str, ...]:
    """The two families that must both accept an extracted IR (§5). Deduplicated, because a
    configuration that pins both judges to one family would silently make the round-trip a
    single-family check."""
    out: list[str] = []
    for role in JUDGE_ROLES:
        fam = ROLE_FAMILY[role]
        if fam not in out:
            out.append(fam)
    return tuple(out)


def llm_versions() -> dict[str, str]:
    """Model identifiers written into VerificationResult.versions (§11/13)."""
    load_env()
    return {"llm.anthropic": os.environ.get("MATHVERIFY_ANTHROPIC_MODEL", "claude-opus-5"),
            "llm.meta": os.environ.get("MATHVERIFY_META_MODEL", "muse-spark-1.3"),
            "llm.cache_mode": os.environ.get("MATHVERIFY_LLM_CACHE", "auto")}
