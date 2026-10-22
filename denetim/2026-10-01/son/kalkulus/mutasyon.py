"""Mutation check of the fixes of the last attack's lens 3 (calculus, definedness; SON-G3-YO-1..4): the switch points
of a written derivative read as certify.calculus reads a kink, the exact Piecewise rule, a closed And/Or condition,
the tangent claim as written, an infinite limit as an argument and a pole over ℂ inside any operation. The machinery is
the one of denetim/2026-09-26/mutasyon.py.

    .venv/bin/python denetim/2026-10-01/son/kalkulus/mutasyon.py [-j N] [--list] [name ...]

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

PAR = "src/mathverify/normalize/parse.py"
CAL = "src/mathverify/certify/calculus.py"
DOM = "src/mathverify/certify/domain.py"
BAS = "src/mathverify/certify/base.py"
T = "tests/test_d4_son_kalkulus.py::"

MUTATIONS = [
    # SON-G3-YO-1: the switch points of at(diff) / the pinned diff
    ("K01 köşe ve sıçrama türevli sayılır", PAR, '                if st == "value":\n                    got = slopes.get(p_)\n',
     '                if st in ("value", "corner"):\n                    got = slopes.get(p_)\n',
     T + "test_a_switch_point_with_no_derivative_has_no_value"),
    ("K02 kararsız sıfır türevsiz sayılır", PAR,
     '                c = sp.Ne(v, p_) if st == "corner" else sp.Contains(v - p_, ORIGIN)\n',
     "                c = sp.Ne(v, p_)\n", T + "test_an_undecided_zero_is_undecided_there_alone"),
    ("K03 sıfır ailesi türevsiz sayılır", PAR, "                out.append(sp.Contains(s, ORIGIN))\n",
     "                out.append(sp.Ne(s, 0))\n", T + "test_the_differentiability_conditions"),
    ("K04 anahtar sıfırları okunmaz", PAR, "        sw = _switch_differentiability(u, v, own, values)\n", "        sw = None\n",
     T + "test_a_point_with_a_derivative_stays_in_the_solution_set"),
    ("K05 floor yanında Piecewise kararsız değil", PAR,
     "        elif isinstance(n, (sp.Piecewise, sp.atan2, sp.arg, sp.Max, sp.Min)):\n", "        elif False:\n",
     T + "test_the_differentiability_conditions"),
    ("K06 arg atan2 olarak okunmaz", PAR,
     "    u = u.replace(lambda n: isinstance(n, sp.arg), lambda n: sp.atan2(sp.im(n.args[0]), sp.re(n.args[0])))\n",
     "    u = u\n", T + "test_arg_is_read_as_atan2_at_its_zero"),
    ("K07 kapalı Or/And koşulu okunmaz", DOM,
     "        if isinstance(c, (sp.core.relational.Relational, sp.And, sp.Or, sp.Not)) and not c.free_symbols:\n",
     "        if isinstance(c, sp.core.relational.Relational) and not c.free_symbols:\n",
     T + "test_a_closed_or_condition_is_read"),
    # the exact Piecewise rule and its users
    ("K08 kink okuması Piecewise kuralını kullanmaz", CAL,
     "    if st is None and f.has(sp.Piecewise):\n        by = \"piecewise_rule\"\n", "    if False:\n        by = 0\n",
     T + "test_the_derivative_task_reads_a_piecewise_corner"),
    ("K09 noktadaki türev Piecewise kuralını kullanmaz", CAL,
     "        st = _piecewise_rule(f, var, at, slope)\n", "        st = None\n",
     T + "test_the_derivative_task_reads_a_piecewise_corner"),
    ("K10 Piecewise kuralı sıçramayı görmez", CAL, '        if True in jumps:\n            return "corner"\n',
     '        if False:\n            return "corner"\n', T + "test_the_piecewise_rule"),
    ("K11 Piecewise kuralı eğimleri ayırmaz", CAL,
     '    return "corner" if slope is True else "value" if slope is False else None\n',
     '    return "value" if slope is not None else None\n', T + "test_the_piecewise_rule"),
    ("K12 Piecewise kuralı dalın analitikliğini sormaz", CAL,
     "            if var in e.free_symbols and not smooth_at(e, var, p, switch_arguments(e, var),\n",
     "            if False and not smooth_at(e, var, p, switch_arguments(e, var),\n", T + "test_the_piecewise_rule"),
    # SON-G3-YO-2: the tangent claim as written
    ("K13 teğet iddiası yazıldığı gibi okunmaz", CAL,
     "                    ok, wev = _tangent_as_written(ok, truth, var, y, claim_conds, claim_nowhere,\n",
     "                    _, wev = _tangent_as_written(ok, truth, var, y, claim_conds, claim_nowhere,\n",
     T + "test_a_tangent_undefined_at_a_point_of_the_line_is_wrong"),
    ("K14 doğrunun noktasında tanımsızlık ret değil", CAL,
     '                ev["claim_as_written"] = f"undefined_at ({pt[0]}, {pt[1]}) of the true line: {c}"\n'
     "                return False, ev\n",
     '                ev["claim_as_written"] = f"undefined_at ({pt[0]}, {pt[1]}) of the true line: {c}"\n'
     "                return None, ev\n", T + "test_a_tangent_undefined_at_a_point_of_the_line_is_wrong"),
    ("K15 koşul doğrunun tamamında aranmaz", CAL, "            if st is None or st != S.Reals:\n", "            if False:\n",
     T + "test_a_tangent_condition_not_proved_on_the_line_is_not_certified"),
    ("K16 hiç tanımlı olmayan teğet iddiası", CAL, "    if nowhere & {var, dep}:\n", "    if False:\n",
     T + "test_a_tangent_undefined_at_a_point_of_the_line_is_wrong"),
    # SON-G3-YO-3: an infinite limit as an argument
    ("K17 sonsuz limit argüman sayılmaz", DOM,
     "               and ((a.has(oo, -oo) and _no_number(_evaluated(a))) or _form_value_no_number(a)) for a in args)\n",
     "               and a.has(oo, -oo) and _no_number(_evaluated(a)) for a in args)\n",
     T + "test_an_infinite_limit_is_no_argument"),
    ("K18 sonsuz limitin tersi okunmaz", DOM,
     "                and (_no_number(_evaluated(base)) or _form_value_no_number(base)):\n",
     "                and _no_number(_evaluated(base)):\n", T + "test_an_infinite_limit_is_no_argument"),
    ("K19 AccumBounds sayı sayılır", DOM,
     "                   and (_no_number(r.value) or r.value.has(sp.AccumBounds)))\n",
     "                   and _no_number(r.value))\n", T + "test_a_limit_with_no_value_is_no_number"),
    # SON-G3-YO-4: a pole over ℂ inside any operation
    ("K20 ℂ kutbu sarmalayıcıda okunmaz", BAS,
     "            if any(is_no_value(c) for c in conds) or complex_pole(e):\n",
     "            if any(is_no_value(c) for c in conds):\n", T + "test_a_complex_pole_has_no_value_in_a_wrapper"),
    ("K21 ℂ'de sıfıra bölme kutup değil", DOM,
     "                if ex.is_number and ex.is_extended_negative is True and _exact_zero(n.base):\n",
     "                if False:\n", T + "test_complex_pole"),
    ("K22 ℂ'de tan kutbu yok", DOM, "            elif isinstance(n, (sp.tan, sp.sec)):\n", "            elif False:\n",
     T + "test_complex_pole"),
    ("K23 ℂ'de cot kutbu yok", DOM, "            elif isinstance(n, (sp.cot, sp.csc)):\n", "            elif False:\n",
     T + "test_complex_pole"),
    ("K24 ℂ'de log 0 yok", DOM, "            elif isinstance(n, sp.log):\n                if _exact_zero(n.args[0])",
     "            elif False:\n                if _exact_zero(n.args[0])", T + "test_complex_pole"),
    # found while measuring: a closed convention membership put at a point, the sign guard's polynomial error
    ("K25 noktadaki gelenek üyeliği okunmaz", DOM,
     "                    if sp.Contains(_evaluated(c.args[0]), c.args[1]) is sp.true:\n                        continue\n",
     "                    pass\n", T + "test_a_family_of_zeros_is_undecided_at_its_members_alone"),
    ("K26 işaret korumasında polinom hatası kaçar", "src/mathverify/_sympy_guards.py",
     "    except (BasePolynomialError, NotImplementedError, ValueError, TypeError, AttributeError):\n",
     "    except (NotImplementedError, ValueError, TypeError, AttributeError):\n",
     T + "test_the_written_derivative_is_read_the_same_every_time"),
    # the evening's additions (G2RK-13/14/15, SON-G3-RK-1/2/4/9)
    ("K27 gerçel kök kuralı yok", CAL,
     '        by = "real_root_rule"\n        st = _real_root_rule(fa, var, p, u, switches, fconds, slope)\n',
     '        by = "real_root_rule"\n        st = None\n', T + "test_a_real_root_has_no_derivative_at_its_zero_and_its_textbook_derivative_elsewhere"),
    ("K28 gerçel kökte g(p) = 0 türevli sayılmaz", CAL,
     "    gp = _nonzero_at(g, var, p, root_of=u)\n    if gp is False:\n        return value()\n",
     "    gp = _nonzero_at(g, var, p, root_of=u)\n    if False:\n        return value()\n",
     T + "test_the_real_root_rule"),
    ("K29 gerçel kökte r > 1 türevli sayılmaz", CAL, "    if certified_sign(r - 1) == 1:\n", "    if False:\n",
     T + "test_the_real_root_rule"),
    ("K30 iddianın geleneği bildirilen bölgede okunmaz", CAL, "                    or _convention_holds_on(c, var, dom)):\n",
     "                    or False):\n", T + "test_a_claims_odd_root_convention_is_read_on_the_declared_region"),
    ("K31 ekstremumda tek kök geleneği aralıkta okunmaz", "src/mathverify/certify/extremum.py",
     '"real_power", "odd_root")', '"real_power")', T + "test_the_extremum_of_a_fractional_or_irrational_power"),
    ("K32 tek kök tabanı kesin pozitif istenir", "src/mathverify/certify/limits.py",
     "        return _base_positive(c.args[0], var, regions, strict=False)\n",
     "        return _base_positive(c.args[0], var, regions)\n", T + "test_the_extremum_of_a_fractional_or_irrational_power"),
    ("K33 aralıkla monotonluk yok", "src/mathverify/certify/extremum.py",
     "        mono = _strictly_monotone(f, var, interval.inf, interval.sup)\n", "        mono = None\n",
     T + "test_the_extremum_of_a_fractional_or_irrational_power"),
    ("K34 azalan hücre artan sayılır", "src/mathverify/certify/extremum.py", "                    signs.add(-1)\n",
     "                    signs.add(1)\n", T + "test_strict_monotonicity_by_intervals"),
    ("K35 tanım ucu gelenek kuralı yok", CAL,
     "        members = [c for c in members if not _convention_at_domain_ends(c, var, src, ns, pins)]\n",
     "        members = list(members)\n", T + "test_an_irrational_power_on_an_unconstrained_variable"),
    ("K36 tanım ucu yalın sıfır istenmez", CAL,
     "        return all(_nonzero_at(sp.diff(b, var), var, q, root_of=b) is True for q in pts)\n",
     "        return True\n", T + "test_the_convention_at_the_ends_of_the_domain"),
    ("K37 tam sayı alt sınırı iddiada okunmaz", CAL, "    if not shift:\n        return conds, nowhere\n",
     "    if True:\n        return conds, nowhere\n",
     T + "test_an_integer_exponent_bounded_below_by_a_constraint"),
    ("K38 U5 üssü değerlendirilmiş okunmaz", DOM,
     " or _plus_one_positive(ex) or _evaluated(ex).is_nonnegative is True):", " or _plus_one_positive(ex)):",
     T + "test_an_integer_exponent_bounded_below_by_a_constraint"),
    ("K39 noktada kesin trig koşulu okunmaz", "src/mathverify/certify/limits.py",
     "        if all(strict_at(c, var, point) for c in risky):\n", "        if False:\n",
     T + "test_a_trigonometric_condition_holding_strictly_at_the_point"),
    ("K40 R - küme okunmaz", PAR, "    whole = number_set_named(m.group(1)) if m else None\n", "    whole = None\n",
     T + "test_set_difference_reading"),
    ("K41 LaTeX cup okunmaz", PAR, '_union_parts(_LATEX_CUP_RE.sub(" U ", s2))', "_union_parts(s2)",
     T + "test_textbook_set_notation"),
    ("K42 yazıldığı gibi okumada R - küme yok", PAR,
     "    diff_ = _set_difference(s2)\n    if diff_ is not None:\n        # ℝ minus a set",
     "    diff_ = _set_difference(s2)\n    if False:\n        # ℝ minus a set",
     T + "test_textbook_set_notation"),
    ("K43 gerçel kök kuralının eğimi okunmaz", CAL,
     '        cache[p] = {"status": "value", "value": slope["value"], "by": by}\n',
     "        pass\n", T + "test_the_real_root_rules_slope_is_read_where_sympys_formula_has_none"),
]

# second round (kararlar.txt "EK 6": YO-K1..K5, SK-RK-1, SK-RK-6)
MUTATIONS += [
    ("K44 değer okuması kanıtlı türevi koymaz", PAR, "            if same is not True:\n                patches.append((p_, s_))\n",
     "            if False:\n                patches.append((p_, s_))\n", T + "test_a_point_branch_is_no_derivative_value"),
    ("K45 yazılı okuma formülün noktadaki değerini denetlemez", PAR,
     "            conds += _formula_values_unproved(d_val.xreplace({canon: v}), v, values)\n", "            pass\n",
     T + "test_an_unproved_formula_value_is_undecided"),
    ("K46 Derivative yazılı okumada türev koşulu taşımaz", PAR,
     '"Derivative": (sp.Derivative, _written_derivative),', "",
     T + "test_a_derivative_in_any_notation_has_no_value_at_a_corner"),
    ("K47 (x, n) sırası okunmaz", PAR, "        if isinstance(v, (tuple, list, sp.Tuple)):\n", "        if False:\n",
     T + "test_the_order_of_a_written_derivative"),
    ("K48 türev fonksiyonunda formül değeri sorgulanmaz", CAL,
     "            if known is not None:\n                if scalar_equal(tv, known) is True:\n                    continue\n"
     "            elif _plainly_smooth(truth, var, p_):\n                continue\n",
     "            continue\n", T + "test_the_derivative_function_at_a_kink_with_a_derivative"),
    ("K49 parçalı kural eğim vermez", CAL, "        if slope is False:\n            _put_slope(out, left, var, p)\n",
     "        pass\n", T + "test_the_point_branch_rules"),
    ("K50 yan dal sadeleştirilmez", CAL,
     "        branches = [sp.cancel(e) if i != 1 and var in e.free_symbols and e.is_rational_function(var) else e\n"
     "                    for i, e in enumerate(branches)]\n", "        branches = list(branches)\n",
     T + "test_the_point_branch_rules"),
    ("K51 yüksek mertebe alt türevi istemez", CAL,
     "    if order > 1 and lower is None and not _plainly_smooth(f, var, at):\n", "    if False:\n",
     T + "test_a_higher_derivative_needs_the_lower_one"),
    ("K52 at() önce alınan dalı seçmez", PAR,
     "    if e.has(sp.Piecewise):\n        e = e.replace(lambda n: isinstance(n, sp.Piecewise), taken)\n", "    pass\n",
     T + "test_a_sign_formula_at_a_kink_with_a_derivative"),
    ("K53 R - A U B okunmadan tek okuma", PAR,
     "            if which is None:\n                raise SetDifferenceAmbiguous(",
     "            if False:\n                raise SetDifferenceAmbiguous(", T + "test_the_two_readings_of_a_set_difference"),
    ("K54 doğrulayıcı iki okumayı koşmaz", "src/mathverify/verifier.py",
     "        return any(writes_ambiguous_set_difference(t) for t in _texts(ir_d) + _texts(sol_d))\n",
     "        return False\n", T + "test_a_set_difference_before_a_union"),
    ("K55 soldan okuma bütün gibi", PAR, '            if which == "left":\n', "            if False:\n",
     T + "test_a_set_difference_before_a_union"),
    ("K56 parantezli fark okunmaz", PAR,
     "        if len(inner) > 1:\n            return whole, rest[1:-1].strip(), [rest[1:-1].strip()]\n",
     "        if False:\n            return whole, rest[1:-1].strip(), [rest[1:-1].strip()]\n",
     T + "test_a_set_difference_before_a_union"),
    ("K57 f'nin bölgesi tam sayı bölgesinde okunmaz", CAL,
     '                conds, other = task_conditions(ctx, p["f"], var, pins, regions=True)\n',
     '                conds, other = task_conditions(ctx, p["f"], var, pins)\n',
     T + "test_an_integer_exponent_bounded_below_reads_f_on_its_region"),
    ("K58 f'nin değerlendirilmiş koşulları bölgede okunmaz", CAL,
     "                    conds += [c for c in _definedness_on_integer_bounds(f, var, shift) if c not in conds\n",
     "                    conds += [c for c in definedness_conditions(f, var) if c not in conds\n",
     T + "test_an_integer_exponent_bounded_below_reads_f_on_its_region"),
    ("K59 hesap hedefi yapısal okunur", "src/mathverify/verifier.py",
     "        if target and ((not _computes(str(target)) and _same_structure(str(ca.payload), str(target), ctx))\n",
     "        if target and ((_same_structure(str(ca.payload), str(target), ctx))\n",
     T + "test_a_computing_target_is_not_read_structurally"),
    ("K60 |a|**2k anahtar sayılır", PAR,
     "                  lambda n: n.base.args[0] ** n.exp)\n", "                  lambda n: n)\n",
     T + "test_an_even_power_of_an_absolute_value_is_smooth"),
    ("K61 kırılımlı kural eğimi önbelleğe yazılmaz (parçalı)", CAL,
     '        by = "piecewise_rule"\n        st = _piecewise_rule(f, var, p, slope)\n',
     '        by = "piecewise_rule"\n        st = _piecewise_rule(f, var, p, {})\n',
     T + "test_the_derivative_function_at_a_kink_with_a_derivative"),
    ("K62 ilkelin gelenek koşulu istisna sızdırır", CAL,
     "        except AttributeError as e:\n", "        except ZeroDivisionError as e:\n",
     T + "test_a_convention_of_a_primitive_raises_nothing"),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
