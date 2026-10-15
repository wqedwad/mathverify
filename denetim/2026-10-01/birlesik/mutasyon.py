"""Mutation check of the merged state of the fourth audit's fixes (A+, 15 Oct 2026; DECISIONS §89): the guards the
merge itself added (`equiv.numeric._monotone_sign`, d4c round 3's `_stands` inside d4b round 10's `_evalf_sign`). The
machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py.

    .venv/bin/python denetim/2026-10-01/birlesik/mutasyon.py [-j N] [--list] [name ...]

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

NUM = "src/mathverify/equiv/numeric.py"
TB = "tests/test_d4_birlesik.py::"
T3 = "tests/test_d4_d4c_tur3.py::test_a_sign_must_stand_at_a_higher_precision"

MUTATIONS = [
    ("M01 tekdüze işlev kuralı yok", NUM, "    s = _monotone_sign(e, timeout)\n    if s is not None:\n        return s\n",
     "", TB + "test_the_gudermann_identity_holds_on_the_positive_reals"),
    ("M02 birim aralık sınanmaz", NUM,
     "    ok = (1,) if strict else (0, 1)\n    return certified_sign(1 - u, timeout) in ok and certified_sign(1 + u, timeout) in ok\n",
     "    return True\n", TB + "test_monotone_rule_reads_nothing_off_a_domain_it_cannot_prove"),
    ("M03 sınırda kesinlik aranmaz", NUM, "        if isinstance(u, _INSIDE_THE_UNIT) or not strict:\n",
     "        if True:\n", TB + "test_monotone_rule_reads_nothing_off_a_domain_it_cannot_prove"),
    ("M04 gerçel olmayan çarpan atlanır", NUM,
     "            s = certified_sign(f, timeout)\n            if s not in (-1, 0, 1):\n                return None\n",
     "            s = certified_sign(f, timeout)\n            if s not in (-1, 0, 1):\n                continue\n",
     TB + "test_monotone_rule_reads_nothing_off_a_domain_it_cannot_prove"),
    ("M05 çarpan işaretleri çarpılmaz", NUM, "            p *= s\n", "            p = s\n",
     TB + "test_monotone_functions_take_their_arguments_sign"),
    ("M06 okuma yüksek hassasiyette denetlenmez", NUM,
     "    reads = [p for p in (_evalf_strict(e),) if p is not None and _stands(e, p)]\n",
     "    reads = [p for p in (_evalf_strict(e),) if p is not None]\n", T3),
    ("M07 negatif okuma yüksek hassasiyette denetlenmez", NUM,
     "        if q is not None and _stands(-e, q):\n", "        if q is not None:\n", T3),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
