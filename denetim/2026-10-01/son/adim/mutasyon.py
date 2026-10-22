"""Mutation check of the final attack's lens 1/4 fixes (16 Oct 2026, branch wip/son-adim): the boundary equation of an
inequality premise (G1RK-2), '%' and '°' read both ways (G1RK-3) and the option read by the claim's reader (G1RK-1);
S35-S57 the second round (21 Oct 2026) after the independent audit of the branch (SA-*); S58-S76 the third round
(22 Oct 2026, decisions EK 8 after the second audit, son-adim-t2). The machinery is the one of
denetim/2026-09-26/mutasyon.py.

    .venv/bin/python denetim/2026-10-01/son/adim/mutasyon.py [-j N] [--list] [name ...]

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mutasyon_0926", HERE.parents[2] / "2026-09-26" / "mutasyon.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

DET = "src/mathverify/steps/deterministic.py"
VER = "src/mathverify/verifier.py"
BAS = "src/mathverify/certify/base.py"
WP = "src/mathverify/certify/wordproblem.py"
PAR = "src/mathverify/normalize/parse.py"
CNT = "src/mathverify/certify/counting.py"
T = "tests/test_d4_son_adim.py::"

MUTATIONS = [
    # G1RK-2
    ("S01 sınır kuralı yok", DET, '                        if status in ("refuted", "unknown"):\n',
     "                        if False:\n", T + "test_g1rk2_the_boundary_equation_of_the_sign_table_is_not_refuted"),
    ("S02 sınırda doğrulanan doğrulanmış sayılır", DET,
     '    if all(st == "refuted" for st, _ in checked):\n        return "refuted", ev\n',
     '    if all(st in ("refuted", "verified") for st, _ in checked):\n        return checked[0][0], ev\n',
     T + "test_g1rk2_the_boundary_equation_of_the_sign_table_is_not_refuted"),
    ("S03 sınırdaki çürütme düşer", DET, '    if all(st == "refuted" for st, _ in checked):\n',
     "    if False:\n", T + "test_g1rk2_a_wrong_critical_point_is_still_refuted"),
    ("S04 kesin olmayan eşitsizlik kendisiyle", DET, "sp.LessThan: sp.StrictLessThan,", "sp.LessThan: sp.LessThan,",
     T + "test_g1rk2_other_boundaries"),
    ("S05 boş sınır öncülü de değiştirilir", DET, "            if e.ok and e.value is True:\n                continue\n        alts",
     "            if False:\n                continue\n        alts",
     T + "test_g1rk2_an_inequality_given_next_to_an_equation_is_no_boundary"),
    ("S06 önceki adımın eşitsizliği değişmez", DET,
     "swapped = _boundary_premises(claim, used, [p for p in premises if p not in my_cases], ctx,",
     "swapped = _boundary_premises(claim, used, list(givens), ctx,",
     T + "test_g1rk2_a_restated_inequality_before_the_critical_points"),
    ("S07 hiçbir yerde sağlanmamak kanıtlanmaz", DET, "    return bool(e.ok and e.value is True)\n\n\ndef _critical",
     "    return False\n\n\ndef _critical", T + "test_g1rk2_the_boundary_equation_of_the_sign_table_is_not_refuted"),
    # G1RK-3
    ("S08 şıkta iki okuma yok", VER, "        other = _mc_unit_reading(ir, solution, ctx, ov, cv, t)\n",
     "        other = None\n", T + "test_g1rk3_a_right_answer_with_a_unit_mark_is_not_refuted"),
    ("S09 iddiada iki okuma yok", VER, "    marks = ctx.open_unit_marks(solution.claimed_answer.payload)\n    if not marks:",
     "    marks = ctx.open_unit_marks(solution.claimed_answer.payload)\n    if True:",
     T + "test_g1rk3_a_right_answer_with_a_unit_mark_is_not_refuted"),
    ("S10 iki okumada da yanlış veto edilmez", VER, "    if unit_state == plain_state:\n", "    if False:\n",
     T + "test_g1rk3_a_wrong_answer_with_a_unit_mark_is_refuted"),
    ("S11 IR'ın kendi birimi okunmaz", BAS, "        marks = marks - (self._ir_unit_marks() - self.counted_unit_marks())\n",
     "        marks = marks\n", T + "test_g1rk3_latex_degree_is_a_degree"),
    ("S12 trig_solve radyanı okunmaz", BAS, " or self.angles_in_radians():", ":",
     T + "test_g1rk3_trig_solve_keeps_its_radians"),
    ("S13 derece sayımı da radyan", BAS, "            if poly.degree() != 1 or not poly.LC().is_Rational:\n",
     "            if poly.degree() != 1:\n", T + "test_g1rk3_a_count_of_degrees_in_trig_solve_is_read_both_ways"),
    ("S14 LaTeX derecesi sayı", PAR, '    s = _LATEX_DEG_RE.sub(r"\\\\cdot\\\\frac{\\\\pi}{180}", s)',
     "    s = s", T + "test_g1rk3_latex_degree_is_a_degree"),
    ("S15 LaTeX yüzdesi işaret değil", PAR, '    if _PCT_RE.search(text) or "\\\\%" in text:',
     "    if _PCT_RE.search(text):", T + "test_ek8_a_unit_not_proved_is_read_both_ways"),
    ("S16 adımda iki okuma yok", DET,
     '                if status in ("refuted", "verified") and recheck is not None:\n',
     "                if False:\n", T + "test_g1rk3_a_step_with_a_unit_mark_is_read_both_ways"),
    ("S17 adımda düz okuma onaylamadan geçer", DET, "    if other == status:\n        return status, ev\n",
     "    if True:\n        return status, ev\n", T + "test_g1rk3_a_step_with_a_unit_mark_is_read_both_ways"),
    # G1RK-1
    ("S18 şık eski okuyucuyla", VER, "    return _option_claim_value(ir, solution, ctx), ctx.claimed(solution)",
     "    return ctx.option_value(ca.option), ctx.claimed(solution)",
     T + "test_g1rk1_a_notation_the_claim_reads_is_read_as_an_option"),
    ("S19 harf yalnızken gösterim normalleşmez", VER,
     '    if not set_task or ca.kind not in ("set", "interval", "condition") or not isinstance(ca.payload, str):',
     '    if not set_task or ca.kind not in ("set", "interval", "condition") or not isinstance(ca.payload, str) \\\n'
     '            or ca.payload_source == "option_letter":',
     T + "test_g1rk1_a_notation_the_claim_reads_is_read_as_an_option"),
    ("S20 şık metni temizlenmez", VER, "    _normalize_set_notation(ir, sol2, ctx)\n    _sanitize_payload(sol2, ctx)\n",
     "    _normalize_set_notation(ir, sol2, ctx)\n", T + "test_g1rk1_a_notation_the_claim_reads_is_read_as_an_option"),
    ("S21 wordproblem şıkları eski okuyucuyla", WP, "options[letter] = ctx.option_as_claim(letter)",
     "options[letter] = ctx.option_value(letter)", T + "test_g1rk1_wordproblem_reads_the_options_as_the_claim"),
    # G1RK-1 (the verifier's corrected expectation), G1RK-8, G1RK-5, G2YO-5/7
    ("S22 log yazımı okunmaz", PAR, "    s = _log_notation(s)\n", "", T + "test_g1rk1_logarithm_notations_are_read"),
    ("S23 çıplak sayıdan sonrası denetlenmez", PAR,
     "            ok = n is not None and _BARE_END_RE.match(s, n.end()) is not None\n",
     "            ok = n is not None\n", T + "test_g1rk1_an_ambiguous_logarithm_is_not_read"),
    ("S24 log_{2} LaTeX sayılır", PAR, 'r"\\^\\{|(?<!log)_\\{|', 'r"\\^\\{|_\\{|', T + "test_g1rk1_logarithm_notations_are_read"),
    ("S25 okunmuş şıkkın yazıldığı biçimi denetlenmez", VER,
     "    read_options = _options_as_read(problem_ir, solution, ctx)\n", "    read_options = problem_ir.options\n",
     T + "test_g1rk1_the_option_as_read_is_read_as_written"),
    ("S26 sayımda iki okuma yolu yok", CNT, "                counts, why2 = _count_integers_both_readings(ctx, var, ev)\n",
     "                counts, why2 = None, None\n",
     T + "test_g1rk8_a_count_wrong_under_both_readings_of_zero_to_the_zero_is_refuted"),
    ("S27 0**0 tek okuma", CNT, "    return {sure, sure + zero}, None\n", "    return {sure + zero}, None\n",
     T + "test_g1rk8_a_count_wrong_under_both_readings_of_zero_to_the_zero_is_refuted"),
    ("S28 başka kararsız kuvvet de okunur", CNT, '            return None, f"power_undecided_at_{k}"\n',
     "            continue\n", T + "test_g1rk8_controls_a_power_undecided_at_a_point_decides_nothing"),
    ("S29 iç Piecewise dalına inmez", PAR,
     "        sub = dict(zip(fn.argsyms, (_closed_branches(a) for a in args)))\n",
     "        sub = dict(zip(fn.argsyms, args))\n", T + "test_g1rk5_the_composition_of_a_piecewise_function_at_a_point"),
    ("S30 dal işareti değerlendirmesiz", PAR, "        with sp.evaluate(True):                     # the signs",
     "        with sp.evaluate(False):                     # the signs",
     T + "test_g1rk5_the_composition_of_a_piecewise_function_at_a_point"),
    ("S31 toleranslı şık kuralı yok", VER, "    if mc is not None and _declared_tolerance(problem_ir):\n",
     "    if False:\n", T + "test_g2yo5_several_options_in_the_window_name_none"),
    ("S32 penceredeki tekliğe bakılmaz", VER,
     '    if any(s_ != "fail" for k, s_ in states.items() if k != ca.option):\n', "    if False:\n",
     T + "test_g2yo5_several_options_in_the_window_name_none"),
    ("S33 pencere dışı şık veto edilmez", VER, '    if chosen == "fail":\n', "    if False:\n",
     T + "test_g2yo7_the_claim_and_the_option_compared_within_the_declared_tolerance"),
    ("S34 pencerede tek şık tutarlı sayılmaz", VER,
     '    if mc.verdict == "pass" or _decided(certs) == "pass":\n', '    if mc.verdict == "pass":\n',
     T + "test_g2yo7_the_claim_and_the_option_compared_within_the_declared_tolerance"),
    # second round (21 Oct 2026): the independent audit of the branch, SA-*
    ("S35 sınırdaki adım havuza girer (SA-YO-2)", DET, 'if st.kind == "eq" and not on_boundary and not unit_open \\\n',
     'if st.kind == "eq" and not unit_open \\\n', T + "test_sa_a_wrong_step_near_a_boundary_is_refuted"),
    ("S36 eşitsizlik adımı da sınırda (SA-YO-3)", DET, "    if not _is_equation_claim(claim):\n        return None\n    hit",
     "    if False:\n        return None\n    hit", T + "test_sa_a_wrong_step_near_a_boundary_is_refuted"),
    ("S37 sistemde de sınır (SA-YO-4)", DET,
     "    if any(v in p.free_symbols and not p.free_symbols <= {v} for p in list(premises) + list(restrictions)):\n"
     "        return None\n", "    if False:\n        return None\n", T + "test_sa_yo4_no_boundary_in_a_system"),
    ("S38 içi boş eşitsizlikte de sınır (SA-RK-1)", DET, "    if not (e.ok and e.value is False):\n        return False\n",
     "    if False:\n        return False\n", T + "test_sa_rk1_no_boundary_reading_when_nothing_is_inside"),
    ("S39 payda kökü kritik nokta değil (SA-RK-7)", DET, "for e, is_den in ((num, False), (den, True))",
     "for e, is_den in ((num, False),)", T + "test_sa_rk7_the_root_of_a_denominator_is_a_critical_point"),
    ("S40 payda kökünde tanımlılık düşmez (SA-RK-7)", DET,
     "        restr = [r for r in restrictions if not (undefined_ok and r in written and v in r.free_symbols)]\n",
     "        restr = list(restrictions)\n", T + "test_sa_rk7_the_root_of_a_denominator_is_a_critical_point"),
    ("S41 payda kökü noktasal okunmaz (SA-RK-7)", DET, "    if at is None:\n        return _check_eq(",
     "    if True:\n        return _check_eq(", T + "test_sa_a_wrong_step_near_a_boundary_is_refuted"),
    ("S42 dışlanan değerli liste seçim (c1 s4)", DET, "every=on_boundary or isinstance(claim, Or))", "every=on_boundary)",
     T + "test_sa_a_wrong_step_near_a_boundary_is_refuted"),
    ("S47 şıkta bildirilen birim düz okunmaz (SA-RK-4)", VER,
     "    ca.payload = ctx.plain_unit_reading(ir.options[ca.option] if text is None else text)\n",
     "    ca.payload = ir.options[ca.option] if text is None else text\n",
     T + "test_ek8_one_marked_number_in_a_proved_unit_is_the_plain_number"),
    ("S48 evaluate değişkeni radyan değil (SA-RK-5)", BAS,
     "                if not isinstance(e, sp.Symbol):\n                    return False\n                v = e\n",
     "                return False\n", T + "test_sa_rk5_a_degree_of_a_radian_measure_is_its_unit"),
    ("S49 ters trig değeri radyan değil (SA-RK-5)", BAS,
     "                    self.cache[key] = True\n                    return True\n                e = self.expr",
     "                    pass\n                e = self.expr", T + "test_sa_rk5_a_degree_of_a_radian_measure_is_its_unit"),
    ("S50 değer adlandırmayan şık pencerede sayılır (SA-RK-6)", VER,
     "        if letter != ca.option and _meta_option(problem_ir.options[letter]):",
     "        if False and _meta_option(problem_ir.options[letter]):",
     T + "test_sa_rk6_an_option_naming_no_value_is_outside_the_window"),
    ("S51 pencere bir kez okunmaz (SA-RK-6)", VER, "        elif letter != ca.option and len(windows) == 1:\n",
     "        elif False:\n", T + "test_sa_rk6_the_window_is_read_once"),
    ("S52 evaluate penceresi kaydedilmez (SA-RK-6)", "src/mathverify/certify/algebra.py",
     "        if not dom and (rel_tol is not None or abs_tol is not None):\n", "        if False:\n",
     T + "test_sa_rk6_the_window_is_read_once"),
    # the first part of the second round (d59d282): SA-YO-1, SA-RK-3, SA-RK-8, and the flag kept for a condition option
    ("S53 şık metninde anlamlı sözcük atılır (SA-YO-1)", VER, '    strict = ca.payload_source == "option_letter"\n',
     "    strict = False\n", T + "test_sa_yo1_a_word_that_may_carry_meaning_leaves_the_option_unread"),
    ("S54 her birim sözcüğü bildirilmiş sayılır (SA-RK-3)", VER,
     '    return bool(units) and word.strip(".,;:!").lower() == units\n', "    return True\n",
     T + "test_sa_rk3_an_option_in_another_unit_is_not_refuted"),
    ("S55 bilinmeyeni anan şık değer (SA-RK-8)", VER, "    if hit:\n        raise ValueError(", "    if False:\n        raise ValueError(",
     T + "test_sa_rk8_an_option_naming_the_unknown_is_no_value"),
    ("S56 koşul şıkkı bilinmeyen korumasına düşer", VER, "        and not _option_out_of_kind(v) else []\n", "        else []\n",
     "tests/test_d4_d4j_kalan.py::test_onceki1_an_option_of_another_kind_abstains"),
    ("S57 okunmayan şık IR'ı tutarsız yapar", "src/mathverify/certify/wordproblem.py",
     '        if n == 0 and unread_carry and any(v == "unparsed" for v in out["option_status"].values()):\n',
     "        if False:\n", T + "test_sa_yo1_options_not_read_say_nothing_about_the_ir"),
    # third round (22 Oct 2026): decisions EK 8 after the second independent audit (son-adim-t2)
    ("S58 ×100 kanıtı okunmaz (EK 8)", BAS,
     '                if any(isinstance(x, sp.Integer) and x == 100 for x in f):\n                    marks.add("%")\n',
     '                if False:\n                    marks.add("%")\n', T + "test_ek8_one_marked_number_in_a_proved_unit_is_the_plain_number"),
    ("S59 /100 de yüzde kanıtı sayılır (EK 8)", BAS, "                if any(isinstance(x, sp.Integer) and x == 100 for x in f):\n",
     "                if any(x in (100, sp.Rational(1, 100)) or (isinstance(x, sp.Pow) and x.base == 100) for x in f):\n",
     T + "test_ek8_the_mechanism"),
    ("S60 ×180/π kanıtı okunmaz (EK 8)", BAS, "                if any(isinstance(x, sp.Integer) and x == 180 for x in f) and any(\n",
     "                if False and any(isinstance(x, sp.Integer) and x == 180 for x in f) and any(\n",
     T + "test_ek8_one_marked_number_in_a_proved_unit_is_the_plain_number"),
    ("S61 derece değişkeni okunmaz (EK 8)", BAS, '        if self._trig_measure() == "degrees":\n            marks.add("°")\n',
     '        if False:\n            marks.add("°")\n', T + "test_ek8_one_marked_number_in_a_proved_unit_is_the_plain_number"),
    ("S62 units yine birim kanıtı (EK 8)", BAS, '        if self._trig_measure() == "degrees":\n',
     '        if str(getattr(self.ir, "units", "") or "").strip().lower() in ("%", "yüzde", "derece", "°"):\n'
     '            marks |= {"%", "°"}\n        if self._trig_measure() == "degrees":\n',
     T + "test_ek8_a_unit_not_proved_is_read_both_ways"),
    ("S63 kanıtsız birimde de düz okuma (EK 8)", BAS,
     "        return one[1] if one is not None and one[0] in self.counted_unit_marks() else text\n",
     "        return one[1] if one is not None else text\n", T + "test_ek8_a_unit_not_proved_is_read_both_ways"),
    ("S64 tek işaretli sayı şartı yok (EK 8)", BAS,
     "        one = single_marked_number(text)\n        return one[1] if one is not None and one[0] in self.counted_unit_marks() else text\n",
     "        from ..normalize.parse import without_unit_marks\n"
     "        marks = unit_marks(text) & self.counted_unit_marks() if isinstance(text, str) else set()\n"
     "        return without_unit_marks(text, marks) if marks else text\n",
     T + "test_ek8_a_unit_not_proved_is_read_both_ways"),
    ("S65 derece katsayısı rasyonel değil de sayılır (EK 8)", BAS,
     "            if poly.degree() != 1 or not sp.simplify(poly.LC() * 180 / sp.pi).is_Rational:\n",
     "            if poly.degree() != 1:\n", T + "test_ek8_the_mechanism"),
    ("S66 ayrışan adım havuza girer (SA2-YO-1)", DET,
     '            unit_open = status != "verified" and bool(ctx.open_unit_marks(st.claim))\n',
     "            unit_open = False\n", T + "test_sa2_yo1_a_step_read_both_ways_is_no_premise"),
    ("S67 ayrışan adım doğrulanmış sayılır (SA2-YO-1)", DET,
     '            unit_open = status != "verified" and bool(ctx.open_unit_marks(st.claim))\n',
     '            unit_open = status == "refuted" and bool(ctx.open_unit_marks(st.claim))\n',
     T + "test_sa2_yo1_a_step_read_both_ways_is_no_premise"),
    ("S68 virgüllü/aralık şık pencere dışı (SA2-YO-2)", VER,
     "    if decimal_comma(text) or _RANGE_OPTION.match(text):\n        return None\n",
     "    if False:\n        return None\n", T + "test_sa2_yo2_an_option_not_read_as_a_number_is_undecided_in_the_window"),
    ("S69 sayı olmayan tür pencere dışı (SA2-YO-2)", VER,
     "        if not (isinstance(ov, sp.Expr) and ov.is_number and not isinstance(ov, sp.Tuple)):\n            ov = None\n",
     "        if False:\n            ov = None\n", T + "test_sa2_yo2_an_option_not_read_as_a_number_is_undecided_in_the_window"),
    ("S70 okunmayan şık iddiayı taşımasa da (SA2-YO-3)", "src/mathverify/certify/wordproblem.py",
     '        if n == 0 and unread_carry and any(v == "unparsed" for v in out["option_status"].values()):\n',
     '        if n == 0 and any(v == "unparsed" for v in out["option_status"].values()):\n',
     T + "test_sa2_yo3_options_not_read_must_carry_the_claim"),
    ("S71 tek değerli 'x = 6' kümesi okunur (T2-RK-3)", VER,
     '    if named is not None and ir.answer_shape not in ("set", "interval") and isinstance(named, sp.FiniteSet) \\\n',
     '    if False and ir.answer_shape not in ("set", "interval") and isinstance(named, sp.FiniteSet) \\\n',
     T + "test_t2_rk3_an_option_naming_one_value_of_the_variable"),
    ("S72 okuyucunun Python set'i kalır (T2-RK-3)", VER, "    if isinstance(v, (set, frozenset)):\n        v = sp.FiniteSet(*v)",
     "    if False:\n        v = sp.FiniteSet(*v)", T + "test_t2_rk3_an_option_naming_one_value_of_the_variable"),
    ("S73 yeniden yazımlar ayrı seçim (T2-RK-4)", DET, "        groups.setdefault(frozenset(keys), []).append(i)\n",
     "        groups.setdefault(frozenset(keys) | {(\"hit\", i)}, []).append(i)\n",
     T + "test_t2_rk4_restatements_take_one_choice_together"),
    ("S74 seçenek üst sınırı yok (T2-RK-4)", DET, "    if n_lists > _BOUNDARY_CHOICES:\n        return None\n",
     "    if False:\n        return None\n", T + "test_t2_rk4_too_many_choices_read_no_boundary"),
    ("S75 meta şık katlanmaz (T2-RK-6)", VER,
     '    t = str(text).replace("İ", "i").replace("I", "ı").lower().translate(_ASCII_FOLD)\n',
     "    t = str(text).lower()\n", T + "test_t2_rk6_a_meta_option_written_any_way_is_outside_the_window"),
    ("S76 'yukarıdakilerden' tanınmaz (T2-RK-6)", VER, "(?:yukaridakiler(?:in|den)\\s+)?", "(?:yukaridakilerin\\s+)?",
     T + "test_t2_rk6_a_meta_option_written_any_way_is_outside_the_window"),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
