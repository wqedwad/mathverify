"""Mutation check of the integral group of the last attack on the merged state (16 Oct 2026; decisions "MERCEK 2"):
the poles of a switch's argument (G2YO-1), the certificate's check against numbers and enclosures (G2YO-1, G2YO-2),
the cell proof's poles (G2YO-3), the exact absolute tolerance (G2YO-4), the jump of a real root's sign (G2RK-1),
a complex quadrature value and the edge reading of an even root (G2RK-7), a convention of the primitive (G2RK-10),
the interval extensions of erf/Si/S/C and the enclosure fallback (G2RK-2), the declared region in the convention gate
(G2RK-3/4), Piecewise cuts (G2RK-5) and x**x (G2RK-9). The machinery is the one of denetim/2026-09-26/mutasyon.py.

    MATHVERIFY_LEAN_REPL=/nonexistent .venv/bin/python denetim/2026-10-01/son/integral/mutasyon.py [-j N] [--list] [name ...]

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

CAL = "src/mathverify/certify/calculus.py"
ENC = "src/mathverify/certify/enclosure.py"
NUM = "src/mathverify/equiv/numeric.py"
RP = "src/mathverify/equiv/random_point.py"
T = "tests/test_d4_son_integral.py::"

MUTATIONS = [
    # --- G2YO-1: the switch points
    ("I01 argümanın kutbu kesme noktası değil", CAL, "        poles = _bad_points(g, var, lo, hi, timeout)\n",
     "        poles = []\n", T + "test_the_switch_points_hold_the_poles_of_the_argument"),
    ("I02 kutuplar bulunamayınca da kesilir", CAL,
     "        poles = _bad_points(g, var, lo, hi, timeout)\n        if poles is None:\n            return None\n",
     "        poles = _bad_points(g, var, lo, hi, timeout) or []\n",
     T + "test_the_switch_points_hold_the_poles_of_the_argument"),
    ("I03 Piecewise kesilmez", CAL, "        elif isinstance(n, sp.Piecewise):\n            for _, cond in n.args:\n"
     "                for r_ in sp.preorder_traversal(cond):\n",
     "        elif False:\n            for _, cond in n.args:\n                for r_ in sp.preorder_traversal(cond):\n",
     T + "test_a_piecewise_integrand_is_cut_at_its_conditions"),
    # --- G2YO-1/2: the certificate's check
    ("I04 sertifikalı 0 sayıyla denetlenmez", CAL, "                differ = abs(v) > rel_err * max(abs(v), 1)\n",
     "                differ = False\n", T + "test_a_certified_zero_is_checked_against_converged_numbers"),
    ("I05 yakınsamayan sayıda zarf sorulmaz", CAL,
     "    enc = rigorous_integral(integrand, var, a, b, outside=c, inside=inside, timeout=timeout, defined=defined)\n",
     "    return \"agrees\", ev\n", T + "test_without_numbers_the_certificate_needs_an_enclosure"),
    ("I06 (-oo, oo) zarfı bilgi sayılır", CAL,
     "    if enc is None or not (mp.isfinite(enc[0]) or mp.isfinite(enc[1])):\n",
     "    if enc is None:\n", T + "test_without_numbers_and_without_an_enclosure_nothing_is_accepted"),
    ("I07 zarf yokken sertifika kabul", CAL,
     "        ev[\"reason\"] = \"no_converged_value_and_no_enclosure\"\n        return \"unconfirmed\", ev\n",
     "        ev[\"reason\"] = \"no_converged_value_and_no_enclosure\"\n        return \"agrees\", ev\n",
     T + "test_without_numbers_and_without_an_enclosure_nothing_is_accepted"),
    ("I08 zarfın dışladığı sertifika yine karar verir", CAL,
     "                if state == \"excluded\":\n                    cval = None", "                if state == \"excluded\":\n"
     "                    pass", T + "test_without_numbers_the_certificate_needs_an_enclosure"),
    # --- G2RK-7
    ("I09 karmaşık değer istisna atar", CAL, "            except (TypeError, ValueError):\n                # a complex",
     "            except (TypeError, KeyError):\n                # a complex", T + "test_a_complex_quadrature_value_is_no_value"),
    ("I10 uçtaki çift kök okunmaz", ENC, "        _EVEN_ROOTS.on = bool(defined)\n", "        _EVEN_ROOTS.on = False\n",
     T + "test_an_even_root_at_an_end_is_read_on_the_range_only"),
    ("I11 çift kök kanıtsız da okunur", ENC, "        _EVEN_ROOTS.on = bool(defined)\n", "        _EVEN_ROOTS.on = True\n",
     T + "test_an_even_root_at_an_end_is_read_on_the_range_only"),
    ("I12 tek dereceli kök de okunur", ENC, "ex.q % 2 == 0 and lo < 0 <= hi", "ex.q % 1 == 0 and lo < 0 <= hi",
     T + "test_an_odd_root_is_never_read_past_zero"),
    ("I13 kenar okuması kenarda kalmaz", ENC, "        finally:\n            _EVEN_ROOTS.on = False\n",
     "        finally:\n            pass\n", T + "test_the_edge_reading_stays_in_the_edge"),
    # --- G2RK-1
    ("I14 bir yan eşitse sıçrama yok", CAL, "    if up is True and down is True:\n        return False\n",
     "    if up is True or down is True:\n        return False\n", T + "test_the_jump_of_a_sign_in_a_primitive"),
    ("I15 bir yan farklıysa sıçrama", CAL, "    if up is False and down is False:\n        return True\n",
     "    if up is False or down is False:\n        return True\n", T + "test_the_jump_of_a_sign_in_a_primitive"),
    ("I16 başka sign sıfırı okunmaz", CAL,
     "        if t_ != s_ and t_.args[0].has(var) and certified_sign(t_.args[0].subs(var, z)) not in (1, -1):\n",
     "        if False:\n", T + "test_the_jump_of_a_sign_in_a_primitive"),
    ("I17 kesin sıçrama reddetmez", CAL, "        if jump is True:\n            ev[\"reason\"] = \"antiderivative_not_defined",
     "        if False:\n            ev[\"reason\"] = \"antiderivative_not_defined",
     T + "test_a_real_root_primitive_is_still_refuted_when_wrong_or_jumping"),
    ("I18 kararsız sıçrama geçer", CAL, "        if jump is None:\n            ev[\"reason\"] = f\"undecided: jump of",
     "        if False:\n            ev[\"reason\"] = f\"undecided: jump of",
     T + "test_a_real_root_primitive_is_still_refuted_when_wrong_or_jumping"),
    ("I19 sign her yerde sıçrar (eski kural)", CAL,
     "        j = _sign_jump_at(F, s_, var, z) if here is True else None\n", "        j = True if here is True else None\n",
     T + "test_a_continuous_real_root_primitive_is_certified"),
    # --- G2RK-10
    ("I20 gelenek koşulu hep karşılanır", CAL,
     "            if _contains_met_on(c, var, discourse):\n                continue\n",
     "            if True:\n                continue\n", T + "test_a_convention_of_the_primitive_that_can_fail_is_undecided"),
    ("I21 gelenek koşulu hiç karşılanmaz", CAL,
     "            return exact_solveset(fails(c.args[0]), var, region) is S.EmptySet\n", "            return False\n",
     T + "test_a_convention_of_the_primitive_on_the_region"),
    # --- G2RK-3/4
    ("I22 beyan bölgesi okunmaz", CAL,
     "    return [] if region == S.Reals or not isinstance(region, sp.Set) else [region]\n", "    return []\n",
     T + "test_declared_regions"),
    ("I23 noktasız türevde bölge yok", CAL,
     "                                              else _declared_regions(ctx, var), pins)\n",
     "                                              else [], pins)\n",
     T + "test_the_convention_gate_reads_the_declared_region"),
    # --- G2RK-9
    ("I24 x**x koşulsuz", CAL, "                   if isinstance(node, sp.Pow) and node.base.has(var) and node.exp.has(var)}\n",
     "                   if False}\n", T + "test_x_to_the_x_in_the_fundamental_theorem"),
    ("I25 x**x döngüde atlanmaz", CAL, "            if node in real_powers:\n                continue"
     "                              # read above: base > 0\n", "", T + "test_x_to_the_x_in_the_fundamental_theorem"),
    # --- G2YO-3
    ("I26 hücre kanıtı kutupta kesmez", RP, "    bps = _breakpoints([a, b], sym, dom, poles=True)\n",
     "    bps = _breakpoints([a, b], sym, dom)\n", T + "test_the_cell_proof_cuts_at_the_poles_of_an_argument"),
    ("I27 kutup kümesinin sınırı okunmaz", RP, "            edge = r.value.boundary\n", "            edge = sp.S.EmptySet\n",
     T + "test_the_cell_proof_cuts_at_the_poles_of_an_argument"),
    # --- G2YO-4
    ("I28 mutlak tolerans merdivende", NUM, "    if abs_tol is not None:\n        # a declared absolute tolerance",
     "    if False:\n        # a declared absolute tolerance", T + "test_a_declared_absolute_tolerance_is_decided_exactly"),
    ("I29 iki tolerans birlikte gerekir", NUM, "    if any(r is True for r in results):\n",
     "    if results and all(r is True for r in results):\n", T + "test_within_abs_tol"),
    ("I30 integralde abs_tol okunmaz", CAL,
     "            declared_abs, bad_abs = read_tolerance(p.get(\"abs_tol\"), relative=False)\n",
     "            declared_abs, bad_abs = None, False\n", T + "test_a_definite_integral_reads_its_absolute_tolerance"),
    ("I31 mutlak pencere geniş", CAL,
     "            inside = (mp.make_mpf(down._mpi_[1]), mp.make_mpf(up._mpi_[0]))\n",
     "            inside = (mp.make_mpf(down._mpi_[0]) - 1, mp.make_mpf(up._mpi_[1]) + 1)\n",
     T + "test_a_definite_integral_reads_its_absolute_tolerance"),
    # --- G2RK-2
    ("I32 aralık yedeği yok", NUM, "    if s is None:\n        from ..certify.enclosure import constant_sign\n",
     "    if False:\n        from ..certify.enclosure import constant_sign\n",
     T + "test_a_tolerance_against_a_special_function_value"),
    ("I33 erf aralığı yok", ENC, "    if isinstance(e, sp.erf):\n", "    if False:\n",
     T + "test_interval_extensions_of_erf_si_and_the_fresnel_integrals"),
    ("I34 Lipschitz yarıçapı yok", ENC,
     "        r = bound * ((hi - lo) * (1 + eps) + eps * (1 + abs(lo) + abs(hi)))\n", "        r = 0\n",
     T + "test_interval_extensions_of_erf_si_and_the_fresnel_integrals"),
    ("I35 zarf yedeği yok", CAL, "                    if ok is None and a.is_finite and b.is_finite:\n",
     "                    if False:\n", T + "test_an_undecided_distance_falls_back_on_the_integrals_enclosure"),
    # --- G2RK-1 (derivative) and G2RK-4
    ("I39 bölgede gelenek integrand bölgesinde okunmaz", CAL,
     "        if isinstance(cc, sp.Contains) and _contains_met_on(cc, var, discourse):\n", "        if False:\n",
     T + "test_a_real_root_primitive_of_a_principal_power_on_the_region"),
    # --- the sibling found on the way: a huge rational power written out in this process
    ("I40 büyük rasyonel kuvvet açılır", RP,
     "                if isinstance(ex, sp.Rational) and (abs(ex.p) > _POWER_PARTS or ex.q > _POWER_PARTS):\n                    return True\n",
     "                if isinstance(ex, sp.Rational) and (abs(ex.p) > _POWER_PARTS or ex.q > _POWER_PARTS):\n                    return False\n",
     T + "test_no_exact_substitution_writes_out_a_huge_rational_power"),
    ("I41 farkın noktası büyük kuvveti açar", RP,
     "        if _heavy_power_at(d, pt):\n            unsure += 1", "        if False:\n            unsure += 1",
     T + "test_no_exact_substitution_writes_out_a_huge_rational_power"),
    ("I42 sonsuz aralıkta sertifika onaylanmaz", CAL,
     "        ev[\"unchecked\"] = \"infinite_range_has_no_numbers\"\n        return \"agrees\", ev\n",
     "        ev[\"unchecked\"] = \"infinite_range_has_no_numbers\"\n        return \"unconfirmed\", ev\n",
     T + "test_an_infinite_range_has_no_numbers_and_the_certificate_decides"),
    ("I43 sonlu aralıkta da sayısız kabul", CAL,
     "    if not nev.get(\"ladder\") and not (sp.sympify(a).is_finite and sp.sympify(b).is_finite):\n",
     "    if not nev.get(\"ladder\"):\n", T + "test_without_numbers_and_without_an_enclosure_nothing_is_accepted"),
    ("I44 duran merdiven sertifikayı onaylamaz", CAL, "            if not spread <= mp.mpf(10) ** -20 * scale:\n",
     "            if True:\n", T + "test_a_ladder_whose_values_settle_confirms_the_certificate"),
    ("I45 duran merdivenin penceresi geniş", CAL,
     "            r = 10 * spread + mp.mpf(10) ** (-(int(ladder[-1][\"dps\"]) - 5)) * scale\n",
     "            r = mp.mpf(1)\n", T + "test_a_ladder_whose_values_settle_confirms_the_certificate"),
    ("I46 ıraksayan merdiven de durmuş sayılır", CAL,
     "            if not spread <= mp.mpf(10) ** -20 * scale:\n                return False\n", "",
     T + "test_a_ladder_whose_values_settle_confirms_the_certificate"),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
