"""mathverify — three-valued deterministic verifier for AI math solutions.

Phase 1 (F0 + F1-TYT + F1-AYT): only deterministic layers (CAS / z3 / numeric).
No LLM layer is present in this package by design (handoff §11/1).
"""
from ._sympy_guards import install as _install_sympy_guards
from .types import LayerResult, VerificationResult, Verdict
from .ir import ProblemIR, LeakageError
from .solution import Solution, ClaimedAnswer, Step

_install_sympy_guards()     # SymPy's precision budget and significant comparisons, in every process

__all__ = ["LayerResult", "VerificationResult", "Verdict", "ProblemIR",
           "LeakageError", "Solution", "ClaimedAnswer", "Step"]
__version__ = "0.1.0"
