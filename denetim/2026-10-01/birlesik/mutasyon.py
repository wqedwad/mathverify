"""Mutation check of the merged state of the fourth audit's fixes (A+, 15 Oct 2026; DECISIONS §89): the guards the
merge itself added (`equiv.numeric._monotone_sign`, d4c round 3's `_stands` inside d4b round 10's `_evalf_sign`;
`certify.domain.convention_null_on` in the integral, derivative and limit gates, the zero_power point of
`certify.calculus._exact_conditions`; with d4h round 2: a closed form's checked value in a certified sign, a jump over a
form built unevaluated, count_roots' expression as a step premise). The machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is
the one of denetim/2026-09-26/mutasyon.py.

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
# M06/M07: the d4c round 3 test no longer reaches the filter (d4b round 10 does not read its case strictly); the
# mechanism is checked directly (survived on 5e88d41 with T3 as their test)
STANDS = TB + "test_a_strict_reading_that_does_not_stand_higher_is_dropped"
DOM = "src/mathverify/certify/domain.py"
CAL = "src/mathverify/certify/calculus.py"
LIM = "src/mathverify/certify/limits.py"
PAR = "src/mathverify/normalize/parse.py"
DET = "src/mathverify/steps/deterministic.py"
FORM = TB + "test_a_form_has_the_sign_of_its_checked_value"
CR = TB + "test_count_roots_reads_its_expression_as_a_premise"
GCD = TB + "test_a_gcd_of_numbers_written_unevaluated_has_its_exact_value"
NULL = TB + "test_a_convention_on_finitely_many_points_does_not_stop_an_integral"
PTS = TB + "test_the_points_where_a_convention_may_fail"

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
     "    reads = [p for p in (_evalf_strict(e),) if p is not None]\n", STANDS),
    ("M07 negatif okuma yüksek hassasiyette denetlenmez", NUM,
     "        if q is not None and _stands(-e, q):\n", "        if q is not None:\n", STANDS),
    ("M08 integral ve türev sonlu kümeyi atlamaz", CAL,
     "\n               and not any(convention_null_on(c, var, r) for r in regions)]", "]", NULL),
    ("M09 limit sonlu kümeyi atlamaz", LIM,
     "\n                   and not any(convention_null_on(c, var, r) for r in near)]", "]",
     TB + "test_a_limit_does_not_read_its_point"),
    ("M10 yalnız boş küme ihmal edilir", DOM, "    return isinstance(pts, (sp.FiniteSet, type(S.EmptySet)))\n",
     "    return pts is S.EmptySet\n", NULL),
    ("M11 pozitif uzunluklu küme de ihmal edilir", DOM,
     "    return isinstance(pts, (sp.FiniteSet, type(S.EmptySet)))\n", "    return True\n", PTS),
    ("M12 kesin bulunmayan küme ihmal edilir", DOM, "    return isinstance(pts, (sp.FiniteSet, type(S.EmptySet)))\n",
     "    return isinstance(pts, (sp.FiniteSet, type(S.EmptySet), sp.ConditionSet))\n", PTS),
    ("M13 real_power okunmaz", DOM, ', "real_power": lambda u: sp.Le(u[0], 0)}', "}", NULL),
    ("M14 zero_power okunmaz", DOM, ' "zero_power": lambda u: Eq(u, 0),\n', "\n", NULL),
    ("M15 origin okunmaz", DOM, '"origin": lambda u: Eq(u, 0), ', "", PTS),
    ("M16 mod_divisor okunmaz", DOM, ' "mod_divisor": lambda u: sp.Le(u, 0),', "", PTS),
    ("M17 odd_root okunmaz", DOM, '{"odd_root": lambda u: sp.Lt(u, 0),', "{", NULL),
    ("M18 TTK'da zero_power noktası kural değil", CAL, "            c = Ne(c.args[0], 0)\n", "            pass\n",
     TB + "test_the_fundamental_theorem_with_an_irrational_power"),
    ("M19 kapalı biçimin işareti okunmaz", NUM,
     "    v = _forms_valued(e, timeout)\n    if v is not None:\n        return certified_sign(v, timeout)\n", "", FORM),
    ("M20 metin okunurken de biçim değerlenir", NUM, "    if _FORMS_HELD.get() or not has_closed_form(e):\n",
     "    if not has_closed_form(e):\n", FORM),
    ("M21 biçim üzerindeki sıçrama kurulurken değerlenir", PAR,
     "    if has_closed_form_node(list(args)):\n        return None\n", "", FORM),
    ("M22 count_roots ifadesi öncül değil", DET, '_TASK_ZERO_PARAMS = {"count_roots": "expr"}', "_TASK_ZERO_PARAMS = {}",
     CR),
    ("M23 count_roots ifadesi ilişki diye okunur", DET, "        rel = Eq(ctx.expr(src), 0) if zero else ctx.rel(src)\n",
     "        rel = ctx.rel(src)\n", CR),
    ("M24 sayıların gcd/lcm'i kesin değerlenmez", NUM,
     "            v = n.func(*[_evaluated(a) for a in n.args])        # the class evaluates at rationals only\n",
     "            v = None\n", GCD),
    ("M25 gcd argümanı yazıldığı gibi okunur", NUM, "    with sp.evaluate(True):\n        return e.func(*[_evaluated(a)",
     "    with sp.evaluate(False):\n        return e.func(*[_evaluated(a)", GCD),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
