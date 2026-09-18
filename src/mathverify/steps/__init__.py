"""L6 (deterministic part only): per-step refutation with SymPy/z3.

Phase 1 contains NO critic model. This layer can only REFUTE a step by exhibiting a
concrete counterexample inside the problem's domain; it never fails a step it merely
could not verify (handoff [10]: template-sensitive step checkers false-reject 75–85%
of non-canonical valid solutions — we avoid that class of error by construction).
"""
from .deterministic import check_steps, LAYER

__all__ = ["check_steps", "LAYER"]
