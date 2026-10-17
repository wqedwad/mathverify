"""Mutation check of the final attack's lens 4 fixes (16 Oct 2026, branch wip/son-ayristirici): the "no solution" option
read as a whole (G4YO-1), premises with no instance refute no step (G4-RK-5), a factor right after a divisor read
neither way (G4YO-2), Turkish negation with its suffixes (G4YO-3) and a given with one real point (G4-K-4). The
machinery is the one of denetim/2026-09-26/mutasyon.py.

    .venv/bin/python denetim/2026-10-01/son/ayristirici/mutasyon.py [-j N] [--list] [name ...]

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
PAR = "src/mathverify/normalize/parse.py"
T = "tests/test_d4_son_ayristirici.py::"

MUTATIONS = [
    # G4YO-1
    ("A01 boş küme kısayolu metnin içinde aranır", VER,
     "        if _NO_SOLUTION.search(opt_text):\n            # \"Çözüm yok\"",
     "        if _NO_SOLUTION_MENTION.search(opt_text):\n            # \"Çözüm yok\"",
     T + "test_g4yo1_an_option_naming_the_empty_set_in_something_more_is_no_no_solution"),
    ("A02 kısayolun başı bağlı değil", VER, '    r"^\\s*(?:\\$+|\\\\\\()?\\s*"\n', '    r"\\s*(?:\\$+|\\\\\\()?\\s*"\n',
     T + "test_g4yo1_an_option_naming_the_empty_set_in_something_more_is_no_no_solution"),
    ("A03 kısayolun sonu bağlı değil", VER, '    r"\\s*(?:\\$+|\\\\\\))?\\s*\\.?\\s*$", re.IGNORECASE)',
     '    r"\\s*(?:\\$+|\\\\\\))?\\s*\\.?\\s*", re.IGNORECASE)',
     T + "test_g4yo1_an_option_naming_the_empty_set_in_something_more_is_no_no_solution"),
    ("A04 anılan boş küme DNE kelime testine gider", VER,
     '        if not mention and re.search(r"yok|dne|tanımsız|mevcut değil|does not exist", opt_text):',
     '        if re.search(r"yok|dne|tanımsız|mevcut değil|does not exist", opt_text):',
     T + "test_g4yo1_prose_that_only_names_no_solution_is_not_refuted"),
    ("A05 Ø ve \\varnothing boş küme değil", VER, r'_EMPTY_SET_TEXT = r"(?:∅|ø|\\emptyset|\\varnothing|emptyset|',
     r'_EMPTY_SET_TEXT = r"(?:∅|\\emptyset|emptyset|', T + "test_g4yo1_the_empty_set_itself_takes_the_shortcut"),
    ("A06 'Ç = ' öneki okunmaz", VER,
     '    r"(?:(?:ç(?:\\s*\\.\\s*k\\s*\\.?)?|çözüm\\s+kümesi|s|[a-z])\\s*(?:=|:|∈|\\\\in(?![a-z]))\\s*|çözüm\\s+kümesi\\s+)?"\n',
     '    r"(?:çözüm\\s+kümesi\\s+)?"\n', T + "test_g4yo1_the_empty_set_itself_takes_the_shortcut"),
    # G4-RK-5
    ("B01 eq adımında boş öncül geri çekmez", DET,
     '        ev["window_dropped"] = "no_premise_instance_inside_the_task_interval"\n    return _vacuous(status, ev, ctx)',
     '        ev["window_dropped"] = "no_premise_instance_inside_the_task_interval"\n    return status, ev',
     T + "test_g4rk5_a_step_from_premises_with_no_instance_is_not_refuted"),
    ("B02 compute adımında boş öncül geri çekmez", DET,
     "    return _vacuous(status, ev, ctx)        # checked where premises with no instance put its symbols: nowhere (G4-RK-5)",
     "    return status, ev", T + "test_g4rk5_a_step_from_premises_with_no_instance_is_not_refuted"),
    ("B08 kapalı hesap da geri çekilir", DET,
     "    if not getattr(claim, \"free_symbols\", None):\n        return status, ev                   # a closed",
     "    if False:\n        return status, ev                   # a closed",
     T + "test_g4rk5_control_a_wrong_step_where_the_premises_have_instances_is_refuted"),
    ("B03 boşluk kanıtsız", DET, "    e = sb_run(\"mathverify.steps.deterministic:_emptiness\", region, timeout=ctx.timeout)\n"
     "    return bool(e.ok and e.value is True)\n\n\ndef _vacuous",
     "    e = sb_run(\"mathverify.steps.deterministic:_emptiness\", region, timeout=ctx.timeout)\n"
     "    return bool(e.ok)\n\n\ndef _vacuous", T + "test_g4rk5_control_a_wrong_step_where_the_premises_have_instances_is_refuted"),
    ("B04 çok bilinmeyende her liste boş sayılır", DET, "                              ctx) == []\n",
     "                              ctx) is not None\n",
     T + "test_g4rk5_control_a_wrong_step_where_the_premises_have_instances_is_refuted"),
    ("B05 tutarsız sistem okunmaz", DET, "                              ctx) == []\n", "                              ctx) is None\n",
     T + "test_g4rk5_a_step_from_premises_with_no_instance_is_not_refuted"),
    ("B06 görevin ilişkisi öncül değil", DET,
     "    premises = list(ctx.givens()) + _task_relations(ctx.ir, ctx) + list(ctx.var_constraints())\n",
     "    premises = list(ctx.givens()) + list(ctx.var_constraints())\n",
     T + "test_g4rk5_a_step_from_premises_with_no_instance_is_not_refuted"),
    ("B07 tek bilinmeyende boşluk okunmaz", DET, "    if not solved:\n        return False\n",
     "    if True:\n        return False\n", T + "test_g4rk5_a_step_from_premises_with_no_instance_is_not_refuted"),
    # G4YO-2
    ("C01 bölenden sonra çarpım yazılır", PAR, "    s = _UNI_VALUE_RE.sub(_juxtaposed_product, s)",
     '    s = _UNI_VALUE_RE.sub(r"\\1*\\2", s)', T + "test_g4yo2_the_parser_reads_neither_way"),
    ("C02 üslü bölen okunmaz", PAR, '        if k >= 0 and s[k] == "^":\n            j = k - 1\n',
     '        if False:\n            j = k - 1\n', T + "test_g4yo2_the_parser_reads_neither_way"),
    ("C03 işaretli bölen okunmaz", PAR, '    if k >= 0 and s[k] in "+-":\n        k -= 1\n',
     '    if False:\n        k -= 1\n', T + "test_g4yo2_the_parser_reads_neither_way"),
    ("C04 LaTeX bölen reddedilmez", PAR, "    if _latex_divisor_juxtaposed(s):\n        # latex2sympy",
     "    if False:\n        # latex2sympy", T + "test_g4yo2_a_factor_right_after_a_divisor_is_not_read"),
    ("C05 fonksiyon argümanı kuralı yok", PAR, "        if m.group(1) not in _LATEX_FUNCTIONS:\n            continue\n",
     "        if True:\n            continue\n", T + "test_g4yo2_a_factor_right_after_a_divisor_is_not_read"),
    ("C06 iddia işaretlenmez", VER, "    if ambiguous_juxtaposition(ca.payload):\n", "    if False:\n",
     T + "test_g4yo2_a_factor_right_after_a_divisor_is_not_read"),
    ("C07 LaTeX boşluğu yan yana sayılmaz", PAR, r'_LATEX_SPACE = re.compile(r"(?:\s|~|\\[,;:! ])*")',
     r'_LATEX_SPACE = re.compile(r"(?:\s)*")', T + "test_g4yo2_the_parser_reads_neither_way"),
    ("C08 parantezli fonksiyon argümanı da reddedilir", PAR,
     '        if k >= len(s) or s[k] == "(" or _LATEX_LEFT.match(s, k):\n            continue\n',
     "        if k >= len(s):\n            continue\n", T + "test_g4yo2_control_explicit_operators_and_brackets_are_read"),
    ("C09 \\cdot çarpan sayılır", PAR, '    "cdot", "times", "div",', '    "times", "div",',
     T + "test_g4yo2_control_explicit_operators_and_brackets_are_read"),
    ("C10 bölenden sonra yüzde dönüştürülür", PAR, "    s = _PCT_RE.sub(lambda m: m.group(0) if m.group(2) and _closes_divisor(m.string, m.end(2) - 1)\n",
     "    s = _PCT_RE.sub(lambda m: m.group(0) if False\n", T + "test_g4yo2_the_parser_reads_neither_way"),
    ("C11 bölenden sonra derece dönüştürülür", PAR,
     "    s = _DEG_NUM_RE.sub(lambda m: m.group(0) if _closes_divisor(m.string, m.end(1) - 1) else",
     "    s = _DEG_NUM_RE.sub(lambda m: m.group(0) if False else", T + "test_g4yo2_the_parser_reads_neither_way"),
    # G4YO-3
    ("D01 Türkçe kökler ek almaz", VER,
     '    r"belki|muhtemel|sanırım|sanirim|sanmı|sanmi|sanki|zannet|zanned|galiba|herhalde|tahmin|şüphe|kuşku|imkans|imkâns)\\w*"',
     '    r"belki|muhtemel|sanırım|sanirim|sanmı|sanmi|sanki|zannet|zanned|galiba|herhalde|tahmin|şüphe|kuşku|imkans|imkâns)(?!\\w)"',
     T + "test_g4yo3_a_negation_or_a_doubt_with_its_suffix_is_not_cleaned_away"),
    ("D02 olumsuz fiil eki okunmaz", VER,
     '    r"|(?<!\\w)\\w*?(?:m[ae]z|m[ıiuü]yor|m[ae]y[ae]bil|m[ae]m[ıiuü]ş|m[ae]m[ae]l[ıi])\\w*"\n', "",
     T + "test_g4yo3_a_negation_or_a_doubt_with_its_suffix_is_not_cleaned_away"),
    ("D03 soru eki okunmaz", VER, '    r"|(?<!\\w)m[ıiuü](?:d[ıiuü]r|s[ıiuü]n(?:[ıiuü]z)?|y[ıiuü]m|y[ıiuü]z)?(?!\\w)"\n', "",
     T + "test_g4yo3_a_negation_or_a_doubt_with_its_suffix_is_not_cleaned_away"),
    ("D04 olma- her ekle", VER, "olamaz|olmaz|olma[dmy]|olabil|", "olamaz|olmaz|olma|olabil|",
     T + "test_g4yo3_control_plain_prose_after_the_value_is_cleaned"),
    # G4-K-4
    ("E01 negatif olmayan toplam ayrılmaz", DET, "    parts = _real_parts(premises, ctx)\n    if any(p is sp.false",
     "    parts = _premise_parts(premises)\n    if any(p is sp.false", T + "test_g4k4_a_wrong_step_under_a_one_point_given_is_refuted"),
    ("E02 kareler tamamlanmaz", DET, "                sq = _completed_squares(d, syms_)\n", "                sq = None\n",
     T + "test_g4k4_a_wrong_step_under_a_one_point_given_is_refuted"),
    ("E03 çift kök negatif olmayan sayılmaz", DET,
     "        if e.xreplace(roots).is_nonnegative is not True:\n", "        if e.is_nonnegative is not True:\n",
     T + "test_g4k4_a_wrong_step_under_a_one_point_given_is_refuted"),
    ("E04 eq adımı sonlu noktalarda denetlenmez", DET, "    elif premises:\n        # several unknowns",
     "    elif False:\n        # several unknowns", T + "test_g4k4_a_wrong_step_under_a_one_point_given_is_refuted"),
    ("E05 kare katsayısı işaretsiz", DET, "        if a.is_positive is not True:\n            return None\n",
     "        if a.is_zero is True:\n            return None\n", T + "test_g4k4_completed_squares"),
    ("E06 artan r > 0 boş değil", DET, "    if r.is_positive is True:\n        return [sp.false]\n",
     "    if r.is_positive is True:\n        return None\n", T + "test_g4k4_completed_squares"),
    ("E07 çapraz terim de ayrılır", DET,
     "    if any(sum(1 for e in m if e) > 1 for m in poly.monoms()):\n", "    if False:\n",
     T + "test_g4k4_completed_squares"),
    ("E08 terimler denetlenmez", DET, "        if e.xreplace(roots).is_nonnegative is not True:\n            return None\n",
     "        if False:\n            return None\n", T + "test_g4rk5_control_a_wrong_step_where_the_premises_have_instances_is_refuted"),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
