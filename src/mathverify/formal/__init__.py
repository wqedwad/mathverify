"""F5 — Lean 4 / Mathlib formal layer (positive evidence only, handoff §3 rule 4, §11/11).

The theorem statement is generated deterministically from the IR (statement.py), so the
"compiles but says the wrong thing" gap ([5]: 89.5% vs 60.5%) cannot occur; the model only
supplies a proof, and every accepted proof passes a sorry / axiom / vacuity / unused-hypothesis
audit before it counts.
"""
from .lean_client import LeanClient, LeanResult, LeanUnavailable, get_lean, lean_available
from .statement import LeanStatement, build_statement, sympy_to_lean, LeanPrintError
from .prove import prove_statement, l7_layer, SAFE_AXIOMS

__all__ = ["LeanClient", "LeanResult", "LeanUnavailable", "get_lean", "lean_available",
           "LeanStatement", "build_statement", "sympy_to_lean", "LeanPrintError",
           "prove_statement", "l7_layer", "SAFE_AXIOMS"]
