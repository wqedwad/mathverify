"""L0/L1 with LLMs (F3): Turkish question -> Problem IR, with the mandatory round-trip
fidelity check judged by two model families (handoff §5, failure mode #1)."""
from .ir_extract import extract_ir, validate_ir, normalize_task, ExtractResult
from .roundtrip import render_ir, judge_roundtrip
from .prompts import EXEMPLAR_IDS

__all__ = ["extract_ir", "validate_ir", "normalize_task", "ExtractResult", "render_ir", "judge_roundtrip",
           "EXEMPLAR_IDS"]
