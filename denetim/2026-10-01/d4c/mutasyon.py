"""Mutation check of part d4c of the fourth audit's fixes (1 Oct 2026): each mutation removes one guard of the
exact zero and the numeric evidence (`certify.calculus` certificates and enclosure, `equiv.forms`,
`steps.deterministic._integrals_refute`, `equiv.random_point`, the sandbox ops). The machinery (throwaway
clones of the committed HEAD, exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the
list of mutations is new.

    .venv/bin/python denetim/2026-10-01/d4c/mutasyon.py [-j N] [--list] [name ...]

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
FRM = "src/mathverify/equiv/forms.py"
DET = "src/mathverify/steps/deterministic.py"
RP = "src/mathverify/equiv/random_point.py"
OPS = "src/mathverify/sandbox/ops.py"
NUM = "src/mathverify/equiv/numeric.py"
T = "tests/test_d4_d4c_sayisal.py"
T4 = "tests/test_parca4_parametreli_bicim.py"

MUTATIONS = [
    ("Z01 SymPy'nin sertifikasız 0'ı kesin değer kalır", CAL,
     '                    ev["symbolic_zero_uncertified"] = True\n                    exact = None\n',
     '                    ev["symbolic_zero_uncertified"] = True\n', T),
    ("Z02 kesin değer yokken kareleme kabul eder", CAL,
     '                return unknown(LAYER, "no_exact_value", t.ms, ev, flags=["no_exact_value"])\n',
     '                ok = True if converged and num_equal(claimed, val, rel_tol=tol)[0] else None\n', T),
    ("Z03 sıfır hata tahmini reddi durdurmaz", CAL,
     "            if not (mp.isfinite(v) and mp.isfinite(err)) or err == 0:\n",
     "            if not (mp.isfinite(v) and mp.isfinite(err)):\n", T),
    ("Z04 yöntemler çelişse de kutu kurulur", CAL,
     "            if abs(v1 - v2) > 10 * (e1 + e2):\n                return None\n",
     "            if False:\n                return None\n", T),
    ("Z05 mutlak integrallenebilirlik varsayılır", CAL,
     "    if f.has(*_JUMPY):\n        return False\n    pts = _bad_points(f, var, lo, hi, timeout)\n",
     "    return True\n    pts = _bad_points(f, var, lo, hi, timeout)\n", T),
    ("Z06 yerel üsler yalnız 0 ve 1/2", CAL,
     "_LOCAL_EXPONENTS = (S.Zero, S.Half, sp.Rational(2, 3), sp.Rational(3, 4), sp.Rational(4, 5), sp.Rational(9, 10))\n",
     "_LOCAL_EXPONENTS = (S.Zero, S.Half)\n", T),
    ("Z07 kuyruk sınırı aranmaz", CAL,
     "        if end in (sp.oo, -sp.oo) and not any(\n",
     "        if False and not any(\n", T),
    ("Z08 tek simetri yerine çift simetri", CAL,
     "f.xreplace({var: mirror}), -f, timeout=timeout)", "f.xreplace({var: mirror}), f, timeout=timeout)", T),
    ("Z09 ilkel içte tanımsız olabilir", CAL,
     "    if bad_F is None or any(x_ != p and x_ != q for x_ in bad_F):\n",
     "    if bad_F is None:\n", T),
    ("Z10 ilkelin türevi denetlenmez", CAL,
     "    if not rs.ok or rs.value != 0:\n        return None\n    bad_F",
     "    if not rs.ok:\n        return None\n    bad_F", T),
    ("Z11 manuel ilkel denenmez", OPS,
     '    for kw in ({}, {"manual": True}):\n', '    for kw in ({},):\n', T),
    ("Z12 derin sonda yok", CAL,
     "    if cls.get(\"kind\") != \"UNKNOWN\" or \"symbolic_numeric_disagreement\" not in (cls.get(\"flags\") or []):\n        return None\n",
     "    return None\n", T),
    ("Z13 Abs/sign kırılmalarında bölünmez", CAL,
     "    cuts = _switch_points(f, var, lo, hi, timeout) if _nonsmooth(f) else []\n",
     "    cuts = []\n", T),
    ("Z14 checked_forms SymPy'nin 0'ını sertifikasız alır", FRM,
     '                    raise UnverifiedForm(f"{n}: SymPy 0 without a certificate ({cev.get(\'reason\')})")\n',
     "                    reps[key] = r.value\n                    continue\n", T),
    ("Z15 evalf bitleri okunmaz", FRM,
     "    if bits is not None and bits < _MIN_BITS:\n        return None\n", "", T),
    ("Z16 adım reddinde kutu genişliği yok", DET,
     "reps = {n: sp.Float(mp.nstr(v + c * w, 65), 65)", "reps = {n: sp.Float(mp.nstr(v, 65), 65)", T),
    ("Z17 evalf'in sıfırı ya da bitsiz sıfırı eşitlik sayılır (eski hâl)", RP,
     "        c = _exact_counterexample(a, b, syms, pt, budget)\n        if isinstance(c, dict):\n            return {\"point\"",
     "        v = sp.N(dp, 30)\n        if v == 0 or (getattr(v, \"_prec\", 0) or 0) < 50:\n            continue\n"
     "        c = _exact_counterexample(a, b, syms, pt, budget)\n        if isinstance(c, dict):\n            return {\"point\"", T),
    ("Z18 karar verilemeyen nokta sayılmaz", RP,
     "        unsure += c is None\n    return None, unsure\n", "    return None, unsure\n", T),
    ("Z19 terim sınırı yok", RP,
     "        if _terms_at(a, syms, pt) > _EVAL_TERMS or _terms_at(b, syms, pt) > _EVAL_TERMS:\n",
     "        if False:\n", T),
    ("Z20 değerlendirme süresi sınırsız", RP,
     "        if spent[0] > _EVAL_BUDGET:\n            ev[\"evaluation_time_budget\"] = True    # the points left",
     "        if False:\n            ev[\"evaluation_time_budget\"] = True    # the points left", T),
    ("Z21 karelemede sonsuz uç yok", OPS,
     "        if e in (oo, -oo):\n            return mp.inf if e is oo else -mp.inf      # mpmath maps an infinite range itself\n",
     "", T),
    ("Z22 sertifikanın sıfır olmayan değeri alınmaz", FRM,
     "                if cval is not None:\n                    reps[key] = cval\n",
     "                if cval is not None and cval == 0:\n                    reps[key] = cval\n", T4),
    ("Z23 sıfır iddiası küçük sayıyla kabul (eski kalıntı sınaması)", CAL,
     "            elif excluded():\n                ok = False\n",
     "            elif claimed_zero and converged and abs(val) < 1e-60:\n                ok = True\n"
     "            elif excluded():\n                ok = False\n", T),
    ("Z24 simetrikleştirilmiş integralde mutlak integrallenebilirlik aranmaz", CAL,
     "        if v is not None and not _absolutely_integrable(f, var, a, b, timeout):\n",
     "        if False:\n", T),
    ("Z25 açı toplamında |Nd| < 1 aranmaz", NUM,
     "            return bool(abs(n * total) < 1)\n", "            return True\n", T),
    ("Z26 açı toplamı kesin sıfır sınamasında yok", NUM,
     "    if _angle_sum_is_zero(d) or _exp_generator_is_zero(d):\n", "    if _exp_generator_is_zero(d):\n", T),
    ("Z27 üstel üreteç kesin sıfır sınamasında yok", NUM,
     "    if _angle_sum_is_zero(d) or _exp_generator_is_zero(d):\n", "    if _angle_sum_is_zero(d):\n", T),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
