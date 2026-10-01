"""Mutation check of part 10 of the 30 Sep 2026 fixes: a `compute` step refuted as an identity is re-checked
where the premises put its symbols (`steps.deterministic._on_premises`: a finite premise set point by point,
otherwise the region the premises leave). The machinery (throwaway clones of the committed HEAD, exit
codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-30/parca10/mutasyon.py [-j N] [--list] [name ...]

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

DET = "src/mathverify/steps/deterministic.py"
TP = "tests/test_parca10_sonlu_oncul.py"

MUTATIONS = [
    ("S01 sonlu öncül kümesi okunmaz (eski hâl)", DET,
     "    if _binders_keep_clear_of(claim, syms):\n        inst = _finite_instances(",
     "    if False:\n        inst = _finite_instances(", TP),
    ("S02 kararsız noktada da ret", DET,
     "    for pt in certain:\n        s_, e_ = at(pt)\n",
     "    for pt in certain + undecided:\n        s_, e_ = at(pt)\n", TP),
    ("S03 ters aralık noktası düşürülür", DET,
     "            if inside is False and in_domain(ctx.reversed_region(q), c) is False:",
     "            if inside is False:", TP),
    ("S04 karşı örneğin öncülleri sağladığı denetlenmez", DET,
     "    if all(_holds_exactly(p, pt, ctx) is True for p in direct):\n        return status, {**ev, \"counterexample",
     "    if True:\n        return status, {**ev, \"counterexample", TP),
    ("S05 bölgede ters aralık varken doğrulanır", DET,
     "    if reversed_left:\n", "    if False:\n", TP),
    ("S06 öncül bağlantısı tek geçiş", DET,
     "                left.remove(p)\n                grew = True\n",
     "                left.remove(p)\n                pass\n", TP),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
