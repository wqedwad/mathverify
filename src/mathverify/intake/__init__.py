"""Two intake paths (D1).

(a) `structured`  — the app's own solver is forced to emit the structured format
    (docs/SOLVER_FORMAT.md); loading validates the schema and rejects key-like fields.
(b) `restructure` — an external free-text solution is converted to the same schema.
    Phase 1 ships only the deterministic final-answer extractor; the LLM restructuring
    pass is F3 and its fidelity is measured separately (harness/restructure_fidelity.py).
"""
from .structured import load_solution, load_problem_ir, SchemaError
from .restructure import extract_final_answer, restructure_deterministic, restructure_llm

__all__ = ["load_solution", "load_problem_ir", "SchemaError", "extract_final_answer",
           "restructure_deterministic", "restructure_llm"]
