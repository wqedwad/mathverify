"""Mutation check of part 11 of the 30 Sep 2026 fixes: a point where a Sum/Product range of the step's own
claim runs backwards (hi < lo - 1) is no counterexample (`steps.deterministic._range_spans`,
`_runs_backwards_at`): the premises' routes skip it, the check at a point abstains there, and a refutation
found there anyway is withdrawn in `check_steps`. The machinery (throwaway clones of the committed HEAD, exit
codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-30/parca11/mutasyon.py [-j N] [--list] [name ...]

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
TP = "tests/test_parca11_ters_aralik_adim.py"

MUTATIONS = [
    ("Y01 ters aralıktaki karşı örnek geri çekilmez (eski hâl)", DET,
     "            if status == \"refuted\" and _refuted_where_backwards(claim, ev):\n",
     "            if False:\n", TP),
    ("Y02 öncül çözümlerinde ters aralık noktası atlanmaz", DET,
     "        if _runs_backwards_at(spans, pt):\n            # a range of the claim runs backwards here",
     "        if False:\n            # a range of the claim runs backwards here", TP),
    ("Y03 öncül kümesinde ters aralık noktası atlanmaz", DET,
     "        if _runs_backwards_at(spans, point):\n            continue                         # the claim's",
     "        if False:\n            continue                         # the claim's", TP),
    ("Y04 noktada denetimde ters aralık karar verir", DET,
     "    if _runs_backwards_at(_range_spans(claim), point):\n        return \"unknown\"",
     "    if False:\n        return \"unknown\"", TP),
    ("Y05 noktası okunamayan ret durur", DET,
     "    return pt is None or _runs_backwards_at(spans, pt)\n",
     "    return pt is not None and _runs_backwards_at(spans, pt)\n", TP),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
