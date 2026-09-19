"""Two intake paths (D1).

(a) `structured`  — the app's own solver is forced to emit the structured format
    (docs/SOLVER_FORMAT.md); loading validates the schema and rejects key-like fields.
(b) `restructure` — an external free-text solution is converted to the same schema.
    This module is the deterministic final-answer extractor; the LLM pass that also
    reconstructs the steps is `extract/restructure_llm.py`, and its fidelity is reported
    under "Yol (b)" by `harness/run_f3.py --pathb`.
"""
from .structured import load_solution, load_problem_ir, SchemaError
from .restructure import extract_final_answer, restructure_deterministic

__all__ = ["load_solution", "load_problem_ir", "SchemaError", "extract_final_answer",
           "restructure_deterministic"]
