"""Mutation check of the final attack's lens 1/4 fixes (16 Oct 2026, branch wip/son-adim): the boundary equation of an
inequality premise (G1RK-2), '%' and '°' read both ways (G1RK-3) and the option read by the claim's reader (G1RK-1). The
machinery is the one of denetim/2026-09-26/mutasyon.py.

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
T = "tests/test_d4_son_adim.py::"

MUTATIONS = [
    # G1RK-2
    ("S01 sınır kuralı yok", DET, '                        if status in ("refuted", "unknown"):\n',
     "                        if False:\n", T + "test_g1rk2_the_boundary_equation_of_the_sign_table_is_not_refuted"),
    ("S02 sınırda doğrulanan doğrulanmış sayılır", DET,
     '    return "unknown", {**ev, "reason": "claim_holds_nowhere_inside_an_inequality_premise", "on_boundary": status}',
     "    return status, ev", T + "test_g1rk2_the_boundary_equation_of_the_sign_table_is_not_refuted"),
    ("S03 sınırdaki çürütme düşer", DET, '    if status == "refuted":\n        return "refuted", ev\n    return "unknown"',
     '    if False:\n        return "refuted", ev\n    return "unknown"', T + "test_g1rk2_a_wrong_critical_point_is_still_refuted"),
    ("S04 kesin olmayan eşitsizlik kendisiyle", DET, "sp.LessThan: sp.StrictLessThan,", "sp.LessThan: sp.LessThan,",
     T + "test_g1rk2_other_boundaries"),
    ("S05 boş sınır öncülü de değiştirilir", DET, "    return None if e.ok and e.value is True else (out, hit)",
     "    return out, hit", T + "test_g1rk2_an_inequality_given_next_to_an_equation_is_no_boundary"),
    ("S06 önceki adımın eşitsizliği değişmez", DET,
     "swapped = _boundary_premises(claim, used, [p for p in premises if p not in my_cases], ctx)",
     "swapped = _boundary_premises(claim, used, list(givens), ctx)",
     T + "test_g1rk2_a_restated_inequality_before_the_critical_points"),
    ("S07 hiçbir yerde sağlanmamak kanıtlanmaz", DET, "    return bool(e.ok and e.value is True)\n\n\ndef _boundary",
     "    return False\n\n\ndef _boundary", T + "test_g1rk2_the_boundary_equation_of_the_sign_table_is_not_refuted"),
    # G1RK-3
    ("S08 şıkta iki okuma yok", VER, "        other = _mc_unit_reading(ir, solution, ctx, ov, cv, t)\n",
     "        other = None\n", T + "test_g1rk3_a_right_answer_with_a_unit_mark_is_not_refuted"),
    ("S09 iddiada iki okuma yok", VER, "    marks = ctx.open_unit_marks(solution.claimed_answer.payload)\n    if not marks:",
     "    marks = ctx.open_unit_marks(solution.claimed_answer.payload)\n    if True:",
     T + "test_g1rk3_a_right_answer_with_a_unit_mark_is_not_refuted"),
    ("S10 iki okumada da yanlış veto edilmez", VER, "    if unit_state == plain_state:\n", "    if False:\n",
     T + "test_g1rk3_a_wrong_answer_with_a_unit_mark_is_refuted"),
    ("S11 IR'ın kendi birimi okunmaz", BAS, "        marks = marks - self.cache[key]\n", "        marks = marks\n",
     T + "test_g1rk3_latex_degree_is_a_degree"),
    ("S12 trig_solve radyanı okunmaz", BAS, " or self.angles_in_radians():", ":",
     T + "test_g1rk3_trig_solve_keeps_its_radians"),
    ("S13 derece sayımı da radyan", BAS, "            if poly.degree() != 1 or not poly.LC().is_Rational:\n",
     "            if poly.degree() != 1:\n", T + "test_g1rk3_a_count_of_degrees_in_trig_solve_is_read_both_ways"),
    ("S14 LaTeX derecesi sayı", PAR, '    s = _LATEX_DEG_RE.sub(r"\\\\cdot\\\\frac{\\\\pi}{180}", s)',
     "    s = s", T + "test_g1rk3_latex_degree_is_a_degree"),
    ("S15 LaTeX yüzdesi işaret değil", PAR, '    if _PCT_RE.search(text) or "\\\\%" in text:',
     "    if _PCT_RE.search(text):", T + "test_g1rk3_a_right_answer_with_a_unit_mark_is_not_refuted"),
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
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
