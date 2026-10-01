"""Mutation check of part 9 of the 30 Sep 2026 fixes: a reversed symbolic Sum/Product range decides
nothing (DECISIONS §80; `certify.domain.ForwardSpans`, `Ctx.reversed_region`, `algebra._filter_solutions`).
The machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is the one of
denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    MATHVERIFY_LEAN_REPL=/nonexistent .venv/bin/python denetim/2026-09-30/parca9/mutasyon.py [-j N] [--list] [name ...]

Not in the list: the fallback of `Ctx._forward_ranges` for a span solveset cannot split (no task in the
tests reaches it; such a span leaves `dom` as it was and every point undecided).

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

DOMAIN = "src/mathverify/certify/domain.py"
BASE = "src/mathverify/certify/base.py"
ALG = "src/mathverify/certify/algebra.py"
TP = "tests/test_parca9_ters_aralik.py"

MUTATIONS = [
    ("R01 ters span false okunur (eski hâl: nokta düşer)", DOMAIN,
     "        return None                                 # negative or open: undecided, never false\n",
     "        return sp.false if isinstance(other, sp.Expr) and other.is_extended_negative is True else None\n", TP),
    ("R02 ters bölge kaydedilmez", BASE,
     '        self.cache[f"reversed:{var.name}"] = back\n',
     '        self.cache[f"reversed:{var.name}"] = S.EmptySet\n', TP),
    ("R03 ters bölge unapplied'a girmez", BASE,
     "        if back is not S.EmptySet:\n            unapplied +=",
     "        if False:\n            unapplied +=", TP),
    ("R04 enforced aralık koşulunu bağışlar", BASE,
     "c in enforced and not is_range_span(c))]", "c in enforced)]", TP),
    ("R05 eşitsizliğin dışladığı çekimser çözüm de sayılır", ALG,
     "        undecided = [s_ for s_ in undecided if _meets_inequalities(s_, ineqs)]\n",
     "        pass\n", TP),
    ("R06 sonlu aday kümesinde ters nokta doğrudan değerlendirmede bakılmaz", ALG,
     "        if ok is True and dom and any(_finite_nonempty(ctx.reversed_region(s_)) for s_ in dom):\n",
     "        if False:\n", TP),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
