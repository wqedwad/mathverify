"""F4 — L6 critic + meta-verification (handoff §4 L6, §11/12, [4]).

A cross-family critic reviews the structured steps and reports the first invalid step; the
report is (a) cross-checked deterministically (its counter-check relation is evaluated, and a
step the deterministic refuter already *verified* cannot be flagged) and (b) meta-verified by
the other family ("is the reported error real?"). Only a confirmed report becomes a signal, and
that signal is soft: it blocks CORRECT (-> UNKNOWN) and localises the step; it never produces
INCORRECT by itself (§4 fusion rules)."""
from .critique import critique_solution, meta_verify, l6_critic_layer, CRITIC_SCHEMA, META_SCHEMA

__all__ = ["critique_solution", "meta_verify", "l6_critic_layer", "CRITIC_SCHEMA", "META_SCHEMA"]
