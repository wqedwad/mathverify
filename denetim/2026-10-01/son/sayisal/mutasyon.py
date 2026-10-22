"""Mutation check of the A+ final attack's lens 1 fixes (16 Oct 2026): G1YO-1 (a part of a strict value decides only
with significant bits of its own, measured against the error of the whole number; a real argument evaluated with an
imaginary part of noise is not read off it) and G1YO-2 (a progression's window too far out for a float index is left
unsolved). The machinery is the one of denetim/2026-09-26/mutasyon.py.

    .venv/bin/python denetim/2026-10-01/son/sayisal/mutasyon.py [-j N] [--list] [name ...]

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

G = "src/mathverify/_sympy_guards.py"
O = "src/mathverify/sandbox/ops.py"
X = "src/mathverify/certify/extremum.py"
E = "src/mathverify/sandbox/exactsets.py"
P = "src/mathverify/normalize/parse.py"
V = "src/mathverify/verifier.py"
T = "tests/test_d4_son_sayisal.py::"

MUTATIONS = [
    ("S01 sanal kısmın işareti bitsiz okunur", G,
     '    s_im = _part_sign(im_)\n    if s_im is None:\n        return None\n    if s_im:\n        return "nonreal"\n'
     "    return _part_sign(re_)",
     '    if _number_sign(im_):\n        return "nonreal"\n    return _number_sign(re_)',
     T + "test_an_imaginary_part_of_noise_is_neither_real_nor_nonreal"),
    ("S02 parçanın bit eşiği yok", G, '    if not m[1] or getattr(v, "_prec", 0) < _PART_BITS:\n',
     "    if not m[1]:\n", T + "test_an_imaginary_part_of_noise_is_neither_real_nor_nonreal"),
    ("S03 gürültü sanal kısım gerçel değil sayılır", G, '    if s_im is None:\n        return None\n',
     '    if s_im is None:\n        return "nonreal"\n', T + "test_an_imaginary_part_of_noise_is_neither_real_nor_nonreal"),
    ("S04 çarpımın parça doğruluğu düzeltilmez", G, "        return _part_accuracies(inner(x, prec, options))\n",
     "        return inner(x, prec, options)\n", T + "test_a_product_measures_each_part_against_the_whole_number"),
    ("S05 parça kendi doğruluğunu korur", G,
     "    return re_, im_, min(re_acc, size_re - err), min(im_acc, size_im - err)",
     "    return re_, im_, re_acc, im_acc", T + "test_a_product_measures_each_part_against_the_whole_number"),
    ("S06 bütünün hatası en küçük parçadan", G, "    err = max(size_re - re_acc, size_im - im_acc)",
     "    err = min(size_re - re_acc, size_im - im_acc)", T + "test_a_product_measures_each_part_against_the_whole_number"),
    ("S07 gerçel argümanın değeri denetlenmez", G, "(x.args[0], _evaluated_real,", "(x.args[0], lambda r: True,",
     T + "test_a_real_argument_evaluated_with_noise_has_no_reading_off_it"),
    ("S08 gerçel tabanın kesimi denetlenmez", G, "(x.base, _clear_of_the_cut,", "(x.base, lambda r: True,",
     T + "test_a_real_argument_evaluated_with_noise_has_no_reading_off_it"),
    ("S09 negatif gerçel kısım da kesimden uzak", G,
     "    return bool(re_ and re_[1] and not re_[0] and re_acc is not None and re_acc >= _PART_BITS)",
     "    return bool(re_ and re_[1] and re_acc is not None and re_acc >= _PART_BITS)",
     T + "test_a_real_argument_evaluated_with_noise_has_no_reading_off_it"),
    ("S10 pozitif gerçel kısım okunmaz", G,
     "    return bool(re_ and re_[1] and not re_[0] and re_acc is not None and re_acc >= _PART_BITS)",
     "    return False", T + "test_a_real_argument_evaluated_with_noise_has_no_reading_off_it"),
    ("S11 argümandan istenen hiç sorulmaz", G, "        if asked is not None and asked[0] is x and not asked[1](r):\n",
     "        if False:\n", T + "test_a_real_argument_evaluated_with_noise_has_no_reading_off_it"),
    ("S12 karmaşık değer gerçel sayılır", G, "    return r is not sp.S.ComplexInfinity and not r[1]\n",
     "    return r is not sp.S.ComplexInfinity\n", T + "test_a_real_argument_evaluated_with_noise_has_no_reading_off_it"),
    ("S13 SymPy'nin gerçel bildiği sayı gerçel değil okunur", G,
     '        if s == "nonreal" and self.is_extended_real is True:\n            s = None\n', "",
     T + "test_a_nonreal_reading_of_a_number_sympy_knows_real_decides_no_sign"),
    ("S14 uzak pencere sınırı yok", E,
     "            if not (fs > 0 and (max(abs(flo), abs(fhi)) + abs(fp)) / fs < _FLOAT_INDEX):   # nan and inf fail too\n",
     "            if not fs > 0:\n", T + "test_a_progression_far_out_is_left_unsolved"),
    ("S15 sınır 2^60", E, "_FLOAT_INDEX = 2.0 ** 48\n", "_FLOAT_INDEX = 2.0 ** 60\n",
     T + "test_a_progression_far_out_is_left_unsolved"),
    ("S16 sınır 2^40", E, "_FLOAT_INDEX = 2.0 ** 48\n", "_FLOAT_INDEX = 2.0 ** 40\n",
     T + "test_a_progression_far_out_is_left_unsolved"),
    ("S17 başlangıç noktası sınırda sayılmaz", E, "(max(abs(flo), abs(fhi)) + abs(fp)) / fs", "max(abs(flo), abs(fhi)) / fs",
     T + "test_a_progression_far_out_is_left_unsolved"),
    ("S18 [0, 2π) okumasında 2π eklenmez", P, "            return a + 2 * sp.pi\n", "            return a\n",
     T + "test_a_principal_argument_right_in_one_convention_is_undecided"),
    ("S19 arg tek okunur", V, "    layers, flags = _verify_arg_readings(problem_ir, solution, seed, timeout, run_steps)\n",
     "    layers, flags = _verify_layers_read(problem_ir, solution, seed, timeout, run_steps)\n",
     T + "test_a_principal_argument_right_in_one_convention_is_undecided"),
    ("S20 yazılı aralık okunmaz", V, "    if inconsistent_a != inconsistent_b:\n", "    if False:\n",
     T + "test_a_written_range_reads_the_principal_argument_in_it"),
    ("S21 ayrışan okumada SymPy'ninki", V, "    if v_a == v_b:\n        return layers, flags + [\"arg_readings_agree\"]\n",
     "    if True:\n        return layers, flags + [\"arg_readings_agree\"]\n",
     T + "test_a_principal_argument_right_in_one_convention_is_undecided"),
    ("S22 arg yazımı görülmez", V, '_ARG_WRITTEN = re.compile(r"(?<![A-Za-z_])arg\\s*\\(|\\\\arg(?![A-Za-z])")',
     '_ARG_WRITTEN = re.compile(r"(?!x)x")', T + "test_a_principal_argument_right_in_one_convention_is_undecided"),
    ("S23 üst yarı düzlem de kaydırılır", P, "        if s in (0, 1):\n            return a\n",
     "        if s in (0, 1):\n            return a + 2 * sp.pi\n",
     T + "test_a_principal_argument_wrong_in_both_conventions_is_refuted"),
    # second round (son-sayisal audit, 21 Oct 2026)
    ("S24 critical_points hatada boş liste", O, "    except Exception:\n        return None\n    cps = []\n",
     "    except Exception:\n        return []\n    cps = []\n", T + "test_critical_points_report_a_failure_as_none"),
    ("S25 sıfırlar yine ham solveset'ten", O, "        sets = (exact_solveset(classical(d), var, interval), singularities(d, var, interval))\n",
     "        sets = (sp.solveset(d, var, interval), singularities(d, var, interval))\n",
     T + "test_an_interior_maximum_of_an_abs_or_max_of_trig_is_found"),
    ("S26 kısmi küme de kabul", O,
     "        if not (s_ is S.EmptySet or isinstance(s_, sp.FiniteSet)) or not all(c.is_number for c in s_):\n            return None\n",
     "        if not (s_ is S.EmptySet or isinstance(s_, sp.FiniteSet)):\n            continue\n",
     T + "test_critical_points_are_the_complete_set_or_none"),
    ("S27 None aday kümesi tam sayılır", X, "    if r.ok and r.value is None:\n",
     "    if r.ok and r.value is None:\n        r = CasResult(ok=True, value=[])\n    if False:\n",
     T + "test_a_failed_candidate_search_is_never_complete"),
    ("S28 kırık noktasının gerçelliği okunmaz", X,
     "                complete = complete and all(p.is_number and p.is_real is True for p in r.value)\n", "",
     T + "test_a_point_of_undecided_realness_leaves_the_list_incomplete"),
    ("S29 yerel ekstremumda gerçellik okunmaz", X,
     "    if not all(c.is_number and c.is_real is True for c in list(rd.value) + list(rs.value)):\n",
     "    if False:\n", T + "test_a_point_of_undecided_realness_leaves_the_list_incomplete"),
    ("S30 noktada kayma çözülmez", P, "    if at and all(s_.name in at for s_ in u.free_symbols):\n", "    if False:\n",
     T + "test_a_pointwise_task_reads_the_shift_of_arg_at_its_point"),
    ("S31 görevin noktası okunmaz", V,
     "    elif isinstance(v, sp.Expr) and v.is_number and not v.has(sp.oo, -sp.oo, sp.zoo, sp.nan):\n        out[var] = v\n",
     "    elif False:\n        out[var] = v\n",
     T + "test_a_pointwise_task_reads_the_shift_of_arg_at_its_point"),
    ("S32 kararsız okuma gelenek sayılır", V, '    if "UNKNOWN" in (v_a, v_b):\n', "    if False:\n",
     T + "test_a_pointwise_task_reads_the_shift_of_arg_at_its_point"),
    ("S33 ortak başarısızlıksız INCORRECT uyuşur", V, "    if not common and not both:\n        return None\n",
     "    if False:\n        return None\n", T + "test_two_incorrect_readings_merge_their_steps"),
    ("S34 tek okumada çürütülen adım çürütülmüş kalır", V,
     '                        and "refuted" in (e.get("status"), sb.get(e.get("index"))):\n                    e["status"] = "unknown"\n',
     '                        and "refuted" in (e.get("status"), sb.get(e.get("index"))):\n                    e["status"] = e["status"]\n', T + "test_two_incorrect_readings_merge_their_steps"),
    ("S35 ilk kötü adım A okumasından", V, "                la = replace(la, evidence=ev, first_bad_step=both[0])\n",
     "                la = replace(la, evidence=ev)\n", T + "test_two_incorrect_readings_merge_their_steps"),
    ("S36 şıklar aralık bildirmez", V, "    if by_options is not None:\n", "    if False:\n",
     T + "test_options_of_one_range_declare_it"),
    ("S37 derece şıkları da aralık bildirir", V, " or _UNIT_MARK.search(str(o)) for o in opts.values()):",
     " for o in opts.values()):", T + "test_options_that_do_not_pick_a_range_leave_the_convention"),
    ("S38 iki değer de şıklardayken A okunur", V, "    if held == [True, False]:\n", "    if held[0]:\n",
     T + "test_options_that_do_not_pick_a_range_leave_the_convention"),
    # third round (22 Oct 2026)
    ("S39 gelenek adımı çürütme sayılır", V, "    layers, layers_b = _convention_steps_unknown(layers, layers_b)\n", "",
     T + "test_a_principal_value_step_is_no_refutation_in_any_reading"),
    ("S40 yalnız A'da çürütülen adım gelenek", V,
     '    conv = {i for i in set(sa) | set(sb) if {sa.get(i), sb.get(i)} == {"refuted", "verified"}}\n',
     '    conv = {i for i in set(sa) | set(sb) if sa.get(i) == "refuted" and sb.get(i) == "verified"}\n',
     T + "test_a_principal_value_step_is_no_refutation_in_any_reading"),
    ("S41 ilk kötü adım gelenek adımında kalır", V, "                    la = replace(la, evidence=ev, first_bad_step=left[0])\n",
     "                    la = replace(la, evidence=ev)\n", T + "test_a_declared_range_does_not_refute_the_principal_step"),
    ("S42 adımsız kalan katman yine fail", V, '                    la = unknown(la.layer, "no_step_refuted", la.latency_ms, ev)\n',
     "                    la = replace(la, evidence=ev)\n", T + "test_a_principal_value_step_is_no_refutation_in_any_reading"),
    ("S43 şıklar süresiz okunur", V, '    r = sb_run("mathverify.verifier:arg_options_worker", expr, [str(o) for o in opts.values()], timeout=8.0)\n',
     '    r = sb_run("mathverify.verifier:arg_options_worker", expr, [str(o) for o in opts.values()], timeout=600.0)\n',
     T + "test_an_oversized_option_reads_no_range_within_the_budget"),
    ("S44 sonsuzdaki nokta okunmaz", V, '    if v in (sp.oo, -sp.oo) and kind == "limit":\n', "    if False:\n",
     T + "test_the_shift_of_arg_is_read_at_infinity_and_at_a_pinned_parameter"),
    ("S45 verilen parametre okunmaz", V, "    out.update({k: vs[0] for k, vs in pins.items() if len(vs) == 1})\n",
     "    out.update({})\n", T + "test_the_shift_of_arg_is_read_at_infinity_and_at_a_pinned_parameter"),
    ("S46 -oo'da tek derece dönmez", P, "    return -s if end == -sp.oo and p.degree() % 2 else s\n", "    return s\n",
     T + "test_the_shift_of_arg_is_read_at_infinity_and_at_a_pinned_parameter"),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
