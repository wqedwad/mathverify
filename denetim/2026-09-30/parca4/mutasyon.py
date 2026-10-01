"""Mutation check of part iv of the 30 Sep 2026 fixes: SymPy's value of an integral or a limit with a
parameter is taken nowhere (`normalize.parse.HeldIntegral`/`HeldLimit`, `hold_parametric`,
`equiv.forms.checked_forms`, `equiv.answers_equivalent`, the step checker, the limit task). The
machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is the one of
denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-30/parca4/mutasyon.py [-j N] [--list] [name ...]

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

PARSE = "src/mathverify/normalize/parse.py"
FORMS = "src/mathverify/equiv/forms.py"
EQUIV = "src/mathverify/equiv/__init__.py"
DET = "src/mathverify/steps/deterministic.py"
LIM = "src/mathverify/certify/limits.py"
TP = "tests/test_parca4_parametreli_bicim.py"

MUTATIONS = [
    ("P01 parametreli limit ayrıştırmada hesaplanır (eski hâl)", PARSE,
     "    return _held(form) if isinstance(form, sp.Limit) else form",
     "    return form if not form.free_symbols else sp.limit(e, v, p, d if d is not None else _two_sided(p))", TP),
    ("P02 parametreli/belirsiz integrate hesaplanır (eski hâl)", PARSE,
     "    return _held(form) if isinstance(form, sp.Integral) else form",
     "    return form if _closed_form(form) else sp.integrate(*args, **kwargs)", TP),
    ("P03 tutulmuş limitin doit'i hesaplar", PARSE,
     'certified empty (third audit of 30 Sep 2026, N8)."""\n\n    def doit(self, **hints):\n        return self',
     'certified empty (third audit of 30 Sep 2026, N8)."""\n\n    def doit(self, **hints):\n'
     "        return sp.Limit(*self.args).doit(**hints)", TP),
    ("P04 verilenin sabitlemesi biçimsel argümana ulaşır", PARSE,
     "        body_ns[PINS_KEY] = {s_: v for s_, v in body_ns[PINS_KEY].items() if s_.name not in fdef.args}",
     "        body_ns[PINS_KEY] = dict(body_ns[PINS_KEY])", TP),
    ("P05 checked_forms tutulmuş biçimi düz biçime çevirmez", FORMS,
     "            n = unhold(key)", "            n = key", TP),
    ("P06 parametreli biçimde örnek noktalardaki uyum kanıt sayılır", EQUIV,
     "    if okR is True and parametric:", "    if False:", TP),
    ("P07 compute adımında parametreli Limit sınıflandırılır", DET,
     "        if any(L.free_symbols for L in lims):", "        if False:", TP),
    ("P08 limit görevi serbest parametrede çekimser kalmaz", LIM,
     "            if left:", "            if False:", TP),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
