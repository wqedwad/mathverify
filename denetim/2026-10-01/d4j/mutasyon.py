"""Mutation check of part d4j ("the rest") of the fourth audit's fixes (15 Oct 2026, plan A+, DECISIONS §89): every
guard the part added is removed or weakened once, and the test named next to it must fail. The machinery (throwaway
clones of the committed HEAD, exit codes, clean-up, --kayit) is the one of denetim/2026-09-26/mutasyon.py.

    .venv/bin/python denetim/2026-10-01/d4j/mutasyon.py [-j N] [--list] [--kayit FILE] [name ...]

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

BASE = "src/mathverify/certify/base.py"
DOM = "src/mathverify/certify/domain.py"
LIM = "src/mathverify/certify/limits.py"
CAL = "src/mathverify/certify/calculus.py"
ALG = "src/mathverify/certify/algebra.py"
PAR = "src/mathverify/normalize/parse.py"
STP = "src/mathverify/steps/deterministic.py"
VER = "src/mathverify/verifier.py"
FUS = "src/mathverify/fuse/rules.py"
T = "tests/test_d4_d4j_kalan.py::"

MUTATIONS = [
    # RK-1: labels
    ("J01 yalın ad etiket sayılmaz", BASE, "        if not isinstance(src, str) or _is_label(src):\n",
     "        if not isinstance(src, str):\n", T + "test_rk1_point_names_are_labels"),
    # RK-2: tails
    ("J03 kuyruk limitle kanıtlanmaz", LIM, "    return _eventually(c, var, point)\n\n\ndef _eventually",
     "    return False\n\n\ndef _eventually", T + "test_rk2_textbook_sequence_limits"),
    ("J04 eksi sonsuz limit Ne'yi kanıtlamaz", LIM, "    sides = {sp.Ne: (1, -1),", "    sides = {sp.Ne: (1,),",
     T + "test_rk2_textbook_sequence_limits"),
    ("J05 sonlu sıfırdan farklı limit okunmaz", LIM, '            sign = certified_sign(cls["value"])\n',
     "            sign = None\n", T + "test_rk2_textbook_sequence_limits"),
    ("J06 sonsuz limitin işareti okunmaz", LIM,
     '            sign = 1 if cls["value"] == oo else -1 if cls["value"] == -oo else None\n',
     "            sign = 1\n", T + "test_rk2_control_a_condition_failing_on_the_whole_tail"),
    # ONCEKI-1: options
    ("J07 şık koşulu küme okunmaz", BASE,
     "        named = self.option_condition_set(letter)\n        if named is not None:\n            return named\n"
     "        return parse_answer(", "        return parse_answer(", T + "test_onceki1_relation_option_is_the_solution_set"),
    ("J08 harf-yalnız şık koşulu okunmaz", VER,
     "        named = ctx.option_condition_set(ca.option)\n        if named is not None:\n            ca.payload = str(named)\n"
     "        elif", "        if False:\n            pass\n        elif",
     T + "test_onceki1_relation_option_set_shape_condition_claim_and_letter_only"),
    ("J09 harf-yalnız ondalık virgül tahmin edilir", VER,
     '        elif problem_ir.answer_shape != "interval" and decimal_comma(ca.payload):\n', "        elif False:\n",
     T + "test_onceki1_decimal_comma_option_is_not_guessed"),
    ("J10 şıkta ondalık virgül tahmin edilir", VER,
     '        if ir.answer_shape != "interval" and decimal_comma(ir.options[ca.option]):\n', "        if False:\n",
     T + "test_onceki1_decimal_comma_option_is_not_guessed"),
    ("J11 her koşul gösterim sayılır", BASE,
     "    return isinstance(rel, sp.core.relational.Relational) and v in (rel.lhs, rel.rhs)\n",
     "    return isinstance(rel, sp.core.relational.Relational)\n", T + "test_onceki1_an_option_of_another_kind_abstains"),
    ("J41 başka türde şık reddeder", VER, "        elif _option_out_of_kind(ov, cv):\n", "        elif False:\n",
     T + "test_onceki1_an_option_of_another_kind_abstains"),
    ("J42 vektör-sayı uyuşmazlığı reddeder", VER,
     "            if (mc_ is None) != (mo_ is None):\n                # a pair",
     "            if False:\n                # a pair", T + "test_onceki1_an_option_of_another_kind_abstains"),
    # A-YO-1: a 0**0 entry
    ("J12 0**0 girdi rasyonel", PAR, "        return not (e.exp <= 0 and _evaluated_bound(e.base) == 0)\n",
     "        return not (e.exp.is_negative and _evaluated_bound(e.base) == 0)\n",
     T + "test_a_yo1_zero_power_entry_is_a_convention"),
    # A-YO-2: an exponent identically 0
    ("J13 özdeş sıfır üs tanınmaz", DOM, "            if sp.simplify(_evaluated(ex)) == 0:\n                return S.Zero\n",
     "            if False:\n                return S.Zero\n", T + "test_a_yo2_zero_exponent_on_zero_or_infinity"),
    ("J14 sonsuz içeren taban okunmaz", DOM,
     "            add(sp.Contains(S.Infinity if base.has(S.Infinity, S.NegativeInfinity) else base, ZERO_POWER_BASE))\n",
     "            add(sp.Contains(base, ZERO_POWER_BASE))\n", T + "test_a_yo2_zero_exponent_on_zero_or_infinity"),
    # A-YO-3: ℂ
    ("J15 C'de değersiz düşer", BASE, "            return self._complex_states()[0]\n", "            return []\n",
     T + "test_a_yo3_complex_keeps_no_value_and_conventions"),
    ("J16 C'de gelenek düşer", BASE, "            elif any(is_convention(c) for c in conds):\n                undecided.append(src)\n",
     "", T + "test_a_yo3_complex_keeps_no_value_and_conventions"),
    # A-YO-5: a closed infinite argument
    ("J17 sonsuz argüman değer sayılır", DOM, "    if _infinite_argument(node):\n        add(sp.false)\n        add(NO_VALUE)\n",
     "", T + "test_a_yo5_infinite_argument_has_no_value"),
    ("J18 üs sonsuzu okunmaz", DOM, "    if isinstance(node, sp.Pow):\n        args = (node.exp,)\n",
     "    if isinstance(node, sp.Pow):\n        args = ()\n", T + "test_a_yo5_infinite_argument_has_no_value"),
    # A-RK-1: a bound that is no linear one
    ("J19 doğrusal olmayan sınır bölgesi bütün", DOM, "                return S.EmptySet, S.Reals\n",
     "                return S.Reals, S.Reals\n", T + "test_a_rk1_nonlinear_bound_is_never_refuted_off_the_integers"),
    ("J20 tam sayı değerli polinom sınır okunmaz", DOM,
     "                if _integer_valued(e, var):\n                    return S.Integers, sp.Complement(S.Reals, S.Integers)\n",
     "", T + "test_a_rk1_integer_valued_bound_of_an_integer"),
    # B-YO-1 / RK-3: log bounds
    ("J21 kapalı sınır tam sayılığı kanıtlanmaz", DOM,
     "    if r is None and not b.free_symbols and certified_integer(_evaluated(b))[0] is True:\n        return True\n",
     "", T + "test_rk3_log_bounds_read_as_written"),
    ("J22 aralık farkı kesin okunmaz", DOM, "        if _proved_integer(gap) is not True:\n",
     "        if gap.is_integer is not True:\n", T + "test_rk3_log_bounds_read_as_written"),
    ("J23 is_integer hatası yutulmaz", PAR,
     "    try:\n        return b.is_integer is True\n    except Exception:  # noqa: BLE001\n        return False\n",
     "    return b.is_integer is True\n", T + "test_rk3_log_bounds_read_as_written"),
    ("J24 okunamayan adım tanımsız adlanır", STP,
     '                        why = "claim_not_read_as_written" if written == "unread" else "claim_undefined_as_written"\n',
     '                        why = "claim_undefined_as_written"\n', T + "test_rk3_an_unread_step_is_not_called_undefined"),
    # D4B9-E2-R1: atan2 / arg
    ("J25 atan2 dal kesimi okunmaz", CAL,
     "            add(n.args[0] if isinstance(n, sp.atan2) else sp.im(n.args[0]))\n", "            pass\n",
     T + "test_e2_r1_branch_cut_is_a_kink"),
    ("J26 arg'ın sanal kısmı alınmaz", CAL,
     "            add(n.args[0] if isinstance(n, sp.atan2) else sp.im(n.args[0]))\n",
     "            add(n.args[0])\n", T + "test_e2_r1_branch_cut_is_a_kink"),
    # GAP-NE
    ("J27 Eq toleransla doğru", DOM, "        return None if okN and tolerant else okN\n", "        return okN\n",
     T + "test_gap_ne_tolerant_equality_decides_nothing"),
    ("J28 Ne toleransla yanlış", DOM, "        return None if okN is None or (okN and tolerant) else (not okN)\n",
     "        return None if okN is None else (not okN)\n", T + "test_gap_ne_tolerant_equality_decides_nothing"),
    ("J29 Float sırası toleransla", DOM, "    if eq and sp.sympify(lhs - rhs).is_zero is not True:\n        return None",
     "    if False:\n        return None", T + "test_gap_ne_tolerant_equality_decides_nothing"),
    ("J30 kesin sıfır fark da kararsız", DOM, "    if eq and sp.sympify(lhs - rhs).is_zero is not True:\n",
     "    if eq:\n", T + "test_gap_ne_tolerant_equality_decides_nothing"),
    # GAP-LFLOOR
    ("J31 hedef işlemi iddiada serbest", VER, "                       or _applies_target_op(ca.payload, str(target), solution, ctx)):\n",
     "                       or False):\n", T + "test_lfloor_claim_computing_the_target_operation"),
    ("J32 açık argümanlı işlem de değer değil", VER,
     "        return any(n.func in ops and not n.free_symbols for n in sp.preorder_traversal(claim))\n",
     "        return any(n.func in ops for n in sp.preorder_traversal(claim))\n", T + "test_lfloor_controls"),
    ("J33 hedefte olmayan işlem de sayılır", VER,
     "        return any(n.func in ops and not n.free_symbols for n in sp.preorder_traversal(claim))\n",
     "        return any(isinstance(n, _TARGET_OPS) and not n.free_symbols for n in sp.preorder_traversal(claim))\n",
     T + "test_lfloor_controls"),
    # CAP-K1
    ("J34 serbest parametre bayraksız", ALG, 'flags=["parametric_form"] if held else None)', "flags=None)",
     T + "test_cap_k1_meaning_abstention_not_turned_correct_by_a_later_layer"),
    ("J35 anlam bayrağı engellemez", FUS,
     "    return [f for f in flags if f not in _NOT_PROVEN_FLAGS and f not in _NOTE_FLAGS]\n", "    return []\n",
     T + "test_cap_k1_meaning_abstention_not_turned_correct_by_a_later_layer"),
    ("J36 füzyonda anlam kuralı yok", FUS,
     "        blocked = [f for f in flags if f in _BLOCK_POSITIVE_FLAGS] or _meaning_blocks(flags, primary_pass)\n",
     "        blocked = [f for f in flags if f in _BLOCK_POSITIVE_FLAGS]\n",
     T + "test_cap_k1_meaning_abstention_not_turned_correct_by_a_later_layer"),
    ("J37 belirleyici sertifika da engellenir", FUS,
     "    if any(l.layer.startswith(_DETERMINISTIC_LAYERS) for l in primary_pass):\n        return []\n", "",
     T + "test_cap_k1_control_a_deterministic_certificate_is_not_blocked"),
    ("J38 kanıtlanamadı bayrağı engeller", FUS, '_NOT_PROVEN_FLAGS = {"cas_failed", ', "_NOT_PROVEN_FLAGS = {",
     T + "test_cap_k1_control_a_not_proved_abstention_and_a_later_pass"),
    ("J39 not bayrağı engeller", FUS, '_NOTE_FLAGS = {"answer_from_option_letter", "answer_level_only", ',
     '_NOTE_FLAGS = {"answer_from_option_letter", ',
     T + "test_cap_k1_every_emitted_flag_is_classified"),
    ("J40 sınıflanmamış bayrak", FUS, '"claim_convention", "claim_unreadable", ', '"claim_convention", ',
     T + "test_cap_k1_every_emitted_flag_is_classified"),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
