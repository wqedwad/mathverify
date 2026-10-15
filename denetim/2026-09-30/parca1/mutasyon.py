"""Mutation check of part (i) of the third audit's critic findings (30 Sep 2026): N2 (the exact zero of
a closed integral, measured against the integrand's scale at every rung), N3 (an eq step with a closed
limit that does not exist), N4 (a high-precision difference confirmed exactly before it counts) and
N6 (a form that cannot be written out takes SymPy's value confirmed by numbers). The machinery
(throwaway clones of the committed HEAD, exit codes, clean-up) is the one of
denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-30/parca1/mutasyon.py [-j N] [--list] [name ...]

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

CAL = "src/mathverify/certify/calculus.py"
FO = "src/mathverify/equiv/forms.py"
RP = "src/mathverify/equiv/random_point.py"
DET = "src/mathverify/steps/deterministic.py"
TP = "tests/test_parca1_sayisal_sifir.py"

MUTATIONS = [
    # --- (Z) the zero test of a closed integral (N2)
    ("Z01 sıfır hiç onaylanmaz", CAL,
     "    if all(mp.isfinite(v) and abs(v) <= bound and err <= bound for _, v, err, bound in rungs):",
     "    if False:", TP),
    ("Z02 yalnız ilk basamak", CAL,
     "    if all(mp.isfinite(v) and abs(v) <= bound and err <= bound for _, v, err, bound in rungs):",
     "    if all(mp.isfinite(v) and abs(v) <= bound and err <= bound for _, v, err, bound in rungs[:1]):", TP),
    ("Z03 hata tahmini sınırla karşılaştırılmaz", CAL,
     "    if all(mp.isfinite(v) and abs(v) <= bound and err <= bound for _, v, err, bound in rungs):",
     "    if all(mp.isfinite(v) and abs(v) <= bound for _, v, err, bound in rungs):", TP),
    ("Z04 ölçeğin yakınsaması denetlenmez", CAL, '        if abs(s30 - s20) > mp.mpf("1e-3") * s30:',
     "        if False:", TP),
    ("Z05 sıfır olmayan değer hiç ayrılmaz", CAL,
     "    if all(mp.isfinite(x_) for x_ in (v1, v2, e1, e2)) and abs(v1) > 10 * (b1 + e1) \\",
     "    if False and abs(v1) > 10 * (b1 + e1) \\", TP),
    ("Z06 checked_forms'ta kesin sıfır göreli", FO, "            if r.value == 0 and _finite_integral(n):",
     "            if False:", TP),
    ("Z07 sertifikada SymPy'nin sıfırı göreli", CAL, "            exact_zero = exact is not None and exact == 0",
     "            exact_zero = False", TP),
    # Z08 ("sertifikada iddia 0 göreli") dropped in d4c round 3 (7 Oct 2026): the claim 0 is no special case any
    # more, every definite integral's value is the certificate's or none (d4c's Y01/Y02/Y04 mutate that)
    ("Z09 integral adımı göreli reddedilir", DET, "                      abs_tol=float(100 * slack))",
     "                      abs_tol=None)", TP),
    ("Z10 kesin kesir farkının işareti yok", DET, "    elif isinstance(d, sp.Rational):", "    elif False:", TP),
    # --- (L) a closed limit in an eq step (N3)
    ("L01 kapalı limit eq adımını reddetmez", DET,
     "        elif _integrals_refute(claim, ctx) or _limits_refute(claim, ctx):",
     "        elif _integrals_refute(claim, ctx):", TP),
    ("L02 var olmayan limit reddetmez", DET, '        if cls.get("kind") == "DNE":\n            return True',
     '        if cls.get("kind") == "DNE":\n            return False', TP),
    ("L03 sonsuz/sonlu çelişkisi yok", DET,
     '        if L in (claim.lhs, claim.rhs) and cls.get("kind") in ("VAR", "INF") and cls.get("value") is not None:',
     '        if False:', TP),
    # --- (R) random points: an exact witness (N4), forms that cannot be written out (N6)
    ("R01 tanık kesin doğrulanmaz", RP,
     "            c = _exact_counterexample(a, b, syms, pt, budget)\n            if isinstance(c, dict):\n                return",
     '            c = {"exact": "numeric"}\n            if isinstance(c, dict):\n                return', TP),
    ("R02 doğrulanamayan tanık eşitlik sayılır", RP, "    if unsure:\n", "    if False:\n", TP),
    ("R03 yazılamayan biçim hiç değerlenmez", RP, "                if not budget or budget[0] <= 0:",
     "                if True:", TP),
    ("R04 bütçe azalmaz", RP, "                budget[0] -= 1\n", "", TP),
    ("R05 biçim yolunda yakınlık denetimi yok", RP,
     '            if abs(va - vb) <= mp.mpf("1e-12") * max(abs(va), abs(vb), 1):', "            if False:", TP),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
