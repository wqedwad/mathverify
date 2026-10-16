"""Mutation check of the local quality changes after the fourth audit (16 Oct 2026; DECISIONS §91): the
integer index of a Sum/Product, 0**0 inside a range, the re-check of an undecided compute step where the
premises pin it (V16) and the Mod of a function's formal argument in a Lean statement (V15 L1). The
machinery is the one of denetim/2026-09-26/mutasyon.py.

    .venv/bin/python denetim/2026-10-01/yerel/mutasyon.py [-j N] [--list] [name ...]

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

DOM = "src/mathverify/certify/domain.py"
DET = "src/mathverify/steps/deterministic.py"
STM = "src/mathverify/formal/statement.py"
T = "tests/test_yerel_kalite.py::"
L = "tests/test_v15_l1_function_mod.py::"

MUTATIONS = [
    ("Y01 indis gerçel okunur", DOM, "                plain = _index_symbols(n)\n",
     "                plain = {v: sp.Symbol(v.name) for v in bound if isinstance(v, sp.Symbol)}\n",
     T + "test_an_integer_index_asks_no_positive_base"),
    ("Y02 indisin işareti okunmaz", DOM, '                kw["nonnegative"] = True\n', "                pass\n",
     T + "test_an_integer_index_asks_no_positive_base"),
    ("Y03 negatif aralık işaretsiz", DOM, '                kw["negative"] = True\n', "                pass\n",
     T + "test_an_index_below_zero_is_negative"),
    ("Y04 aralıkta 0**0 aranmaz", DOM, "                for c in _zero_powers_in_range(n, body, plain):\n",
     "                for c in []:\n", T + "test_a_power_that_vanishes_at_an_index_of_the_range_is_a_zero_power_point"),
    ("Y05 aralık dışındaki sıfır da gelenek", DOM,
     "                if k0.is_integer is False or (k0 - lo).is_extended_negative is True \\\n",
     "                if k0.is_integer is False \\\n",
     T + "test_a_power_that_vanishes_at_an_index_of_the_range_is_a_zero_power_point"),
    ("Y06 üst sınır denetlenmez", DOM,
     "                        or (hi - k0).is_extended_negative is True:\n", "                        :\n",
     T + "test_a_power_that_vanishes_at_an_index_of_the_range_is_a_zero_power_point"),
    ("Y07 çözülemeyen hesap pinli denetlenmez", DET,
     '_RECHECKED_WHERE_PINNED = ("parametric_form", _KARR_ONLY, "cas_could_not_evaluate", "cas_could_not_evaluate_rhs")',
     '_RECHECKED_WHERE_PINNED = ("parametric_form", _KARR_ONLY)', T + "test_a_series_step_is_checked_at_the_given_value"),
    ("Y08 fonksiyon gövdesindeki Mod reddedilir", STM,
     "        wc, pc = _open(_definedness(w[0], real_mod=True)), _open(_definedness(body, real_mod=True))\n",
     "        wc, pc = _open(_definedness(w[0])), _open(_definedness(body))\n",
     L + "test_a_function_mod_by_a_positive_literal_is_stated_in_the_integers"),
    ("Y09 gerçel Mod her yerde kabul", STM, "            if not (_safe_mod(m) or real_mod and literal):\n",
     "            if not (_safe_mod(m) or literal):\n", L + "test_a_function_mod_outside_the_safe_subset_is_still_refused"),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
