"""L5 — metamorphic testing of a solution's *method* (handoff §7 `meta/metamorphic.py`,
target: 'doğru cevap yanlış yöntem' detection). Soft signal only."""
from .metamorphic import perturb_ir, metamorphic_check, l5_layer

__all__ = ["perturb_ir", "metamorphic_check", "l5_layer"]
