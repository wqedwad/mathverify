"""L4 — cross-family re-solve (handoff §4.1). The re-solver's answer NEVER produces a verdict;
it can only lower confidence or push to UNKNOWN. Its solution is itself run through the
deterministic certificates, so 'the other family agrees/disagrees' is weighed by whether that
independent answer was certified."""
from .cross_family import solve_with_family, cross_family_resolve, l4_layer

__all__ = ["solve_with_family", "cross_family_resolve", "l4_layer"]
