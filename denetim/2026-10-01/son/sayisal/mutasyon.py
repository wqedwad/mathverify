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
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
