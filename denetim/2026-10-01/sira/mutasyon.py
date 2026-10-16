"""Mutation check of the guard on SymPy's Mul._eval_is_even (16 Oct 2026; DECISIONS §90): an unevaluated product
with an exactly-0 factor is even. The machinery is the one of denetim/2026-09-26/mutasyon.py.

    .venv/bin/python denetim/2026-10-01/sira/mutasyon.py [-j N] [--list] [name ...]

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mutasyon_0926", HERE.parents[1] / "2026-09-26" / "mutasyon.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

GRD = "src/mathverify/_sympy_guards.py"
T = "tests/test_d4_sira.py::"

MUTATIONS = [
    ("S01 Mul çiftlik koruması kurulmaz", GRD,
     '    if not getattr(sp.Mul._eval_is_even, "mathverify_guard", False):\n', "    if False:\n",
     T + "test_a_written_zero_product_stays_zero_whatever_is_asked_first"),
    ("S02 tablo güncellenmez", GRD, '        sp.Mul._prop_handler["even"] = sp.Mul._eval_is_even', "        pass",
     T + "test_a_written_zero_product_stays_zero_whatever_is_asked_first"),
    ("S03 sonsuz olabilen çarpan sınanmaz", GRD,
     "            return True if all(a.is_finite is True for a in self.args if a is not sp.S.Zero) else None\n",
     "            return True\n", T + "test_a_zero_product_with_a_factor_that_may_be_infinite_is_not_decided"),
    ("S04 sıfırsız çarpım da sıfır sayılır", GRD, "        if any(a is sp.S.Zero for a in self.args):\n",
     "        if True:\n", T + "test_an_evaluated_product_keeps_sympys_answer"),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
