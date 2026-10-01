"""Mutation check of part 8 of the 30 Sep 2026 fixes: a `compute` step with a Sum, Product or definite
Integral in symbols the premises pin is checked at their values (`steps.deterministic._pins`,
`_binders_keep_clear_of`). The machinery (throwaway clones of the committed HEAD, exit codes, clean-up)
is the one of denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-30/parca8/mutasyon.py [-j N] [--list] [name ...]

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
TP = "tests/test_parca8_sabitlenmis_toplam.py"

MUTATIONS = [
    ("P01 işlemli iddia hiç sabitlenmez (eski hâl)", DET,
     "    if not isinstance(claim, Eq) or not syms or not _binders_keep_clear_of(claim, syms):",
     "    if not isinstance(claim, Eq) or not syms or claim.has(sp.Integral, sp.Sum, sp.Product, sp.Limit, "
     "sp.Derivative, sp.Subs, sp.Lambda):", TP),
    ("P02 Limit de sabitlenir", DET, "    if claim.has(sp.Limit, sp.Derivative, sp.Order):",
     "    if claim.has(sp.Derivative, sp.Order):", TP),
    ("P03 bağlı değişkenle çakışma denetlenmez", DET,
     "            if any(len(lim) != 3 or lim[0] in syms for lim in node.limits):",
     "            if any(len(lim) != 3 for lim in node.limits):", TP),
    ("P04 tek sınırlı Integral de sabitlenir", DET,
     "            if any(len(lim) != 3 or lim[0] in syms for lim in node.limits):",
     "            if any(lim[0] in syms for lim in node.limits):", TP),
    ("P05 başka bağlayıcı (Subs) da sabitlenir", DET,
     '        elif getattr(node, "bound_symbols", None):', "        elif False:", TP),
    ("P06 sabitlenmiş aralık ayrıştırıcı denetiminden geçmez", DET,
     "                                _refuse_reversed_ranges(pinned, st.claim)\n",
     "                                pass\n", TP),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
