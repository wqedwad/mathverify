"""Mutation check of the harness oracle fixes of 29 Sep 2026 (DECISIONS §70): the K4 labeller and the
soundness sweep's `_differs` / `_equal` (a difference proved at a point of the problem's domain, exact
numbers compared exactly, what SymPy cannot reduce is no difference, the labeller's odd payloads).
Measured equivalent and left out: the nan guard of `_is_zero` (Z06): without it the precision ladder
compares nan and raises, which the same function turns into no decision.
The machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is the one of
denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-29/mutasyon_etiket.py [-j N] [--list] [name ...]

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mutasyon_0926", HERE.parent / "2026-09-26" / "mutasyon.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

SF, RS = "harness/soundness_fuzz.py", "harness/run_solver.py"
TSF, TR = "tests/test_soundness_fuzz.py", "tests/test_run_solver.py"

MUTATIONS = [
    # --- the point proof
    ("Z01 nokta kanıtı yok", SF, "    return _is_zero(d) is False or _differs_at_a_point(a, b, admissible=admissible)\n",
     "    return _is_zero(d) is False\n", TSF),
    ("Z02 yalnız sonuç gerçel", SF, "        for part in sp.preorder_traversal(e):\n", "        for part in [e]:\n", TSF),
    ("Z03 tanım kümesi süzgeci yok", SF, "            if admissible is not None and not admissible(pt):\n",
     "            if False:\n", TSF),
    ("Z04 ilkelde her sembol değişken", SF, "        wrt = [var] if var is not None else list(free)\n        try:\n",
     "        wrt = list(free)\n        try:\n", TSF),
    ("Z05 ilkelde türev yerine fark", SF, "        d = av - bv if slope is None else _real_value(slope, pt)\n",
     "        d = av - bv\n", TSF),
    ("Z23 plus_x ada göre", SF, "        x = var if var in free else free[0]\n", "        x = free[0]\n", TSF),
    # --- exact numbers
    ("Z07 ondalık yazıldığı gibi okunmaz", SF,
     "    return e.xreplace({f: sp.Rational(str(f)) for f in floats}) if floats else e\n", "    return e\n", TSF),
    ("Z08 mutlak tolerans", SF, "    if v80 < sp.Float(\"1e-70\") and v160 < sp.Float(\"1e-150\"):\n",
     "    if v80 < sp.Float(\"1e-35\"):\n", TSF),
    ("Z09 süreksizlik koruması yok", SF,
     "        if isinstance(e, sp.Basic) and not e.free_symbols and _jump_at_a_possible_zero(e):\n",
     "        if False:\n", TSF),
    ("Z15 tek kök gerçel okunmaz", SF, "    if not isinstance(e, sp.Basic) or not e.has(sp.Pow):\n        return e\n",
     "    if True:\n        return e\n", TSF),
    # --- what SymPy cannot reduce
    ("Z10 indirgenmemiş fark kanıt", SF, "            return any(c.is_empty is False and not isinstance(c, sp.Complement)\n",
     "            return any(c != sp.S.EmptySet\n", TSF),
    ("Z11 parametreli küme karşılaştırılır", SF,
     "            if a == b or _integer_parameter(a) or _integer_parameter(b):\n", "            if a == b:\n", TSF),
    ("Z12 oran sadeleşmezse farklı eğri", SF,
     "        return _curves_differ(a, b, admissible) or _curves_differ(b, a, admissible)\n", "        return True\n", TSF),
    ("Z13 pahalı sadeleştirme süresiz", SF, "    if not _heavy(e):\n        return sp.simplify(e)\n",
     "    if True:\n        return sp.simplify(e)\n", TSF),
    ("Z14 ters aralık nokta sayılır", SF,
     "                    if lo_v.is_number and hi_v.is_number and (hi_v < lo_v) is sp.true:\n",
     "                    if False:\n", TSF),
    # --- the labeller
    ("Z16 tek eleman açılmaz", RS, "        c, g = _unwrap_singleton(c, g)\n", "", TR),
    ("Z17 parantezsiz sıralama küme değil", RS, "    if plain_set(g) and listing(c) is not None:\n", "    if False:\n", TR),
    ("Z18 JSON listesi metne çevrilir", RS,
     "            raw = payload if isinstance(payload, list) or (k == \"count\" and isinstance(payload, int)) else str(payload)\n",
     "            raw = payload if (k == \"count\" and isinstance(payload, int)) else str(payload)\n", TR),
    ("Z19 k ve n birleştirilir", RS, "            if one and isinstance(c, sp.Basic)", "            if isinstance(c, sp.Basic)", TR),
    ("Z20 parantez içi C kalır", RS, "        if mod_c and isinstance(c, (set, frozenset)):\n", "        if False:\n", TR),
    ("Z21 şık türü denetlenmez", RS, "    if payload in (None, \"\") and isinstance(opt, str) and opt in opts:",
     "    if payload in (None, \"\") and opt in opts:", TR),
    ("Z22 dönüşüm istisnası korunmaz", RS,
     "    try:\n        return _comparable(c, g)\n    except Exception:  # noqa: BLE001\n        return c, g\n",
     "    return _comparable(c, g)\n", TR),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
