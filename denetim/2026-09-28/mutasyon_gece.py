"""Mutation check of the night of 28 Sep 2026 (DECISIONS §65 onward): the fixes of the targeted audit
of the step refuter's #11 relaxations. (W) the task window is dropped when the premises have no
instance inside it. (X) an assignment no value of its variable's domain satisfies is no definition.
(Y) a point assignment the premises leave free over a continuum is a choice (V13). The machinery
(throwaway clones of the committed HEAD, exit codes, clean-up) is
the one of denetim/2026-09-26/mutasyon.py; only the list of mutations is new. The list of the same
day's evening (mutasyon.py, next to this file) is the record of its own measurement at 3e1805d and is
not edited: its V05 names a line this audit rewrote (W06 is its successor). Measured equivalent
and left out: an undecided emptiness of the premise set counted as empty (W07). On the set route
the set has one variable and no parameter, and SymPy decided it in each of the ten regions tried
(tan, sin, cos, exp, log and sums of them on intervals). Also left out: an assignment of several
variables checked for one of them (X04). It survived and it is sound: SymPy calls the set empty
only when no value of the other variables allowed by their assumptions meets the domain, so the
mutant refutes only genuine contradictions; restricting the check to one variable is a choice of
scope, not a guard.

    .venv/bin/python denetim/2026-09-28/mutasyon_gece.py [-j N] [--list] [name ...]

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

DET = "src/mathverify/steps/deterministic.py"
TK = "tests/test_step_refuter_k4.py"

MUTATIONS = [
    # --- (W) a window the premises miss
    ("W01 aralık boşken düşürülmez", DET, "    if ev.pop(\"_window_without_instance\", False):\n",
     "    if False:\n", TK),
    ("W02 küme yolunda boşluk bayrağı yok", DET, "        if empty and window:\n", "        if False:\n", TK),
    ("W03 çözüm yolunda bayrak yok", DET, "    if outside and not inside:\n", "    if False:\n", TK),
    ("W04 örnekleme yolunda bayrak yok", DET, "        if window and not points and any(",
     "        if False and not points and any(", TK),
    ("W05 aralığın değişkeni aralıktan örneklenmez", DET, "        wdoms = _window_domains(doms, window, ctx)\n",
     "        wdoms = doms\n", TK),
    ("W06 boş bölge kanıt sayılır", DET, "return None, bool(e.ok and e.value is False), bool(e.ok and e.value is True)",
     "return None, bool(e.ok), bool(e.ok and e.value is True)", TK),
    ("W08 aralık dışı nokta içeride sayılır", DET, "            outside += 1\n            continue\n",
     "            outside += 1\n", TK),
    ("W09 aralık düşünce de aralıklı sonuç döner", DET,
     "        status, ev = _check_eq_in(claim, premises, ctx, restrictions, ())\n", "        pass\n", TK),
    # --- (X) an assignment outside the domain
    ("X01 alan dışı atama tanımsal kalır", DET,
     "    binds = not _is_assignment(claim) or (not claim.free_symbols <= prem_syms and _outside_domain(claim, ctx))\n",
     "    binds = not _is_assignment(claim)\n", TK),
    ("X02 alan içi çözüm de alan dışı sayılır", DET, "        if not (e.ok and e.value is True):\n            return False\n",
     "        if not e.ok:\n            return False\n", TK),
    ("X03 seçeneğin bir parçası alan dışıysa yeter", DET,
     "        if not (e.ok and e.value is True):\n            return False\n    return True\n",
     "        if e.ok and e.value is True:\n            return True\n    return False\n", TK),
    # --- (Y) a choice of a free symbol
    ("Y01 seçim yok", DET, "                        if w is not None:\n", "                        if False:\n", TK),
    ("Y02 seçimler öncül değil", DET,
     "                    extra = [c for s_, c in choices.items() if s_ != point] if point is not None else []\n",
     "                    extra = []\n", TK),
    ("Y03 seçim havuza girer", DET,
     "                if isinstance(claim, Eq):\n                    choices[point] = claim\n                continue\n",
     "                if isinstance(claim, Eq):\n                    choices[point] = claim\n", TK),
    ("Y04 ayrık küme de serbest", DET, "    return bool(r.ok and r.value is True)\n", "    return bool(r.ok)\n", TK),
    ("Y05 tanık aranmaz", DET,
     "            if _in_domains(ctx, point) and all(_decide(p, point, ctx) is True for p in premises):\n",
     "            if True:\n", TK),
    ("Y06 seçimden türeyen olgu havuza girer", DET,
     "                        chosen = _check_eq(claim, premises, ctx, restrictions, window)[0] == \"refuted\"\n",
     "                        chosen = False\n", TK),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
