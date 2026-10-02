"""Mutation check of part d4b of the fourth audit's fixes (1 Oct 2026): periodic conditions and solver
completeness. Each mutation removes one guard (`sandbox.exactsets`, `Ctx.domain_for` / `cut_by`, the
abstentions, `algebra._complete_solutions`, `trig._region`, ...); the test it names must then fail. The
machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is the one of
denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-10-01/d4b/mutasyon.py [-j N] [--list] [name ...]

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

EX = "src/mathverify/sandbox/exactsets.py"
OPS = "src/mathverify/sandbox/ops.py"
BASE = "src/mathverify/certify/base.py"
DOM = "src/mathverify/certify/domain.py"
ALG = "src/mathverify/certify/algebra.py"
CNT = "src/mathverify/certify/counting.py"
EXT = "src/mathverify/certify/extremum.py"
LIM = "src/mathverify/certify/limits.py"
SER = "src/mathverify/certify/series.py"
TRIG = "src/mathverify/certify/trig.py"
FORM = "src/mathverify/formal/statement.py"
PARSE = "src/mathverify/normalize/parse.py"
DET = "src/mathverify/steps/deterministic.py"
VER = "src/mathverify/verifier.py"
T = "tests/test_d4_d4b_periyodik.py::"
_RATIO_MID = ("\n        else:\n            return None\n    L = sp.expand(L)\n"
              "    if var in sp.diff(L, var, 2).free_symbols or sp.diff(L, var, 2) != 0:\n"
              "        return None                                  # not linear in var\n"
              "    sign = 1 if c > 0 else -1\n")
_MONO_MID = ("\n        m = max(0, -min(ks.values()))\n"
             "        bt = sp.expand(base.xreplace({n: sp.exp(exps[n][1]) * t ** ks[n] for n in exps}) * t ** m)\n"
             "        if bt.free_symbols != {t}:\n            return None\n        g = sp.Poly(bt, t)\n"
             "        back = bt.subs(t, sp.exp(c0 * var)) - base * sp.exp(m * c0 * var)\n")

MUTATIONS = [
    # --- sandbox.exactsets / ops
    ("P01 solveset_in korumasız", OPS, "    return exact_solveset(rel, var, domain)\n",
     "    return sp.solveset(rel, var, domain)\n", T + "test_an_inequality_on_the_reals_is_not_one_period"),
    ("P02 trigonometri riski görülmez", EX, "    if isinstance(rel, sp.Expr):\n        return oscillates(rel, var)\n"
     "    return any(oscillates(r.lhs - r.rhs, var) for r in _relations(rel))",
     "    return False", T + "test_a_bounded_domain_is_rebuilt_on_every_period"),
    ("P08 periyodik nokta kümesi okunmaz", EX, "    discrete = _on_periodic_points(rel, var, domain, P)\n",
     "    discrete = None\n", T + "test_a_set_of_points_repeating_with_a_period"),
    ("P09 noktasal sonlu küme yolu yok", EX, "        keep = _on_points(rel, var, domain)            # point by point\n",
     "        keep = None\n", T + "test_equations_keep_their_exact_sets"),
    ("P10 boşluk tek periyotta okunmaz", EX, "    periods = set_periods(s_)\n    L = _common_period(periods) if periods else None",
     "    L = None", T + "test_a_set_of_points_repeating_with_a_period"),
    # --- the exact classes (review of 2 Oct 2026)
    ("K01 hücreler SymPy'nin kümesinden", EX, "    else:\n        zp, pp, _ = _structure(e, var)\n    pp = pp + _written_poles",
     "    else:\n        zp, pp = [(z, S.Zero) for z in sp.solveset(sp.Eq(e, 0), var, sp.Interval(lo, hi))], []\n    pp = pp + _written_poles",
     T + "test_only_the_exact_classes_give_a_set"),
    ("K02 nokta sınırı yok", EX, "            if n1 - n0 > LIMIT:\n                raise _Unsolved", "            if False:\n                raise _Unsolved",
     T + "test_the_work_of_one_call_is_bounded"),
    ("K03 |r| > 1 de çözüm sayılır", EX, "    if _certified(1 - abs(r)) < 0:\n        return []", "    if False:\n        return []",
     T + "test_only_the_exact_classes_give_a_set"),
    ("K04 tan'ın kutbu yok", EX, "        poles = [((sp.pi / 2 - b) / a, sp.pi / abs(a))]", "        poles = []",
     T + "test_a_bounded_domain_is_rebuilt_on_every_period"),
    ("K05 paydanın sıfırı sıfır sayılır", EX, "            (zeros if is_num else poles).extend(z)", "            zeros.extend(z)",
     T + "test_only_the_exact_classes_give_a_set"),
    ("K06 sınırsız denklemde kutup düşülmez", EX, "        return sp.Intersection(sp.Complement(zs, union(pp)) if pp else zs, domain)",
     "        return sp.Intersection(zs, domain)", T + "test_only_the_exact_classes_give_a_set"),
    ("K07 sınırsızda hiçbir yer / her yer okunmaz", EX,
     "    if w is S.EmptySet:\n        return S.EmptySet\n    if w == sp.Interval(0, P):\n        return domain\n", "",
     T + "test_equations_keep_their_exact_sets"),
    ("K08 sınıfın periyodu yok", EX, "    return _common_period(periods) if periods else None", "    return None",
     T + "test_only_the_exact_classes_give_a_set"),
    ("K09 cebirsel katsayılı kökler okunmaz", EX, "    except Exception:  # noqa: BLE001 - not over ZZ/QQ\n        pass",
     "    except Exception:  # noqa: BLE001 - not over ZZ/QQ\n        raise _Unsolved('mutated')",
     T + "test_steps_on_tan_with_its_window_stay_verified"),
    ("K10 çözülmemiş trig tanımlılığı tanımlı sayılır", DOM, "            return True if at_risk(bad, var) else None",
     "            return None", T + "test_a_definedness_condition_out_of_the_classes_is_not_taken_as_defined"),
    ("K11 sınıf dışında solve listesi tam sayılır", ALG,
     '        return None, f"no_equation_with_a_finite_proved_solution_set_on {window}"',
     '        return sols, "mutated"', T + "test_evaluate_with_a_non_class_equation_keeps_unknown"),
    ("K12 parantezli tanım evreni küme okunur", PARSE,
     '    if any(op in s for op in ("<", ">", "!=")) and not s.startswith(("Interval", "Union")):',
     '    if any(op in s for op in ("<", ">", "!=")) and not s.startswith(("Interval", "Union", "(", "[")):',
     T + "test_review_b3_b4_b5"),
    # --- round 4: the classes (iv) monotone, (v) sin/cos combination, (vi) products; polynomial systems
    ("K13 φ atan(B/A) (denetimli)", EX, "    R, phi = sp.sqrt(A ** 2 + B ** 2), sp.atan2(B, A)\n",
     "    R, phi = sp.sqrt(A ** 2 + B ** 2), sp.atan(B / A)\n", T + "test_the_combination_reading_is_checked"),
    ("K14 φ atan(B/A), birleşim denetimi yok", EX,
     "    R, phi = sp.sqrt(A ** 2 + B ** 2), sp.atan2(B, A)\n    if sp.simplify(sp.expand_trig(R * sp.sin(u + phi) + D) - base) != 0:",
     "    R, phi = sp.sqrt(A ** 2 + B ** 2), sp.atan(B / A)\n    if False:", T + "test_the_combination_reading_is_checked"),
    ("K15 üsler tek üreteçte yanlış (denetimli)", EX, "        ks = {n: int(ratios[n] * L) for n in exps}",
     "        ks = {n: 1 for n in exps}", T + "test_monotone_class_sets"),
    ("K16 üsler yanlış, monoton denetim yok", EX,
     "        ks = {n: int(ratios[n] * L) for n in exps}" + _MONO_MID + "        if sp.simplify(sp.expand(sp.powsimp(back.rewrite(sp.exp)))) != 0:",
     "        ks = {n: 1 for n in exps}" + _MONO_MID + "        if False:", T + "test_monotone_class_sets"),
    ("K17 exp'in değer kümesi dışı kök", EX, "            if _certified(r_) <= 0:\n                continue",
     "            if False:\n                continue", T + "test_mono_zeros_keep_to_the_range"),
    ("K18 atan'ın değer kümesi dışı kök", EX, "            if _certified(sp.pi / 2 - abs(r_)) <= 0:\n                continue",
     "            if False:\n                continue", T + "test_monotone_class_sets"),
    ("K19 log'un tanımsız noktası yok", EX, "    poles = [((-b) / a, S.Zero)] if h is sp.log else []",
     "    poles = []", T + "test_monotone_class_sets"),
    ("K20 log'un gerçel olmadığı hücre tek noktadan okunur", EX,
     "        if outside(mid):\n            continue", "        if False:\n            continue", T + "test_monotone_class_sets"),
    ("K23 sınırsız eşitlikte log'un gerçel olmadığı sıfır", EX,
     "            zp = [(p0, step) for p0, step in zp if not outside(p0)]", "            pass", T + "test_monotone_class_sets"),
    ("K24 sınırsız eşitlikte log'lu ilerleme", EX,
     "            if any(step != 0 for _, step in zp + pp):\n                raise _Unsolved",
     "            if False:\n                raise _Unsolved", T + "test_a_log_factor_with_a_progression_on_the_reals"),
    ("K22 log'un gerçel olmadığı sıfır", EX, " if not _same(z, poles) and not outside(z)]", " if not _same(z, poles)]",
     T + "test_a_log_factor_with_a_progression_on_the_reals"),
    ("K21 solve_guarded sınıfları okumaz", ALG, "    if \"numerator_real_roots\" not in ev:\n        # not rational",
     "    if False:\n        # not rational", T + "test_solve_guarded_uses_the_classes_on_the_reals"),
    ("K25 tamlık önce gövdede (ters aralık adayı düşer)", ALG,
     "        for w in ([S.Reals, window] if window != S.Reals else [S.Reals]):", "        for w in [window]:",
     "tests/test_parca9_ters_aralik.py::test_a_value_that_rests_on_a_reversed_range_is_not_certified"),
    ("G01 çözüm sayısı boyutla karşılaştırılmaz", ALG, "    if len(found) != dim:", "    if False:",
     T + "test_polynomial_system_with_solutions_solve_misses_is_not_certified"),
    ("G02 radikal yerine ideal (katlı kök)", ALG,
     '    R = sp.groebner(polys + [sp.Poly(q, *plain) for q in extra], *plain, order="lex")', "    R = G",
     T + "test_polynomial_system_completeness"),
    ("G03 sıfır boyut denetimi yok", ALG, '        if not elim:\n            return None', '        if not elim:\n            continue',
     T + "test_polynomial_system_completeness"),
    ("G04 gerçel olmayan çözüm kalır", ALG, "        if not all(real):\n            continue", "        if False:\n            continue",
     T + "test_polynomial_system_completeness"),
    ("G05 tekrarlanan nokta ayrı sayılır", ALG, "            if all(eq_):", "            if False:",
     T + "test_polynomial_system_solve_list_with_a_repeated_or_false_point"),
    ("G06 çözüm olmayan nokta sayılır", ALG, "            if z is not True:\n", "            if z is False and z:\n",
     T + "test_polynomial_system_solve_list_with_a_repeated_or_false_point"),
    ("G07 doğrusal olmayan sistem doğrusal sayılır", ALG, "    if all(p.total_degree() <= 1 for p in polys)", "    if True",
     T + "test_polynomial_system_with_solutions_solve_misses_is_not_certified"),
    ("G08 çok değişkende solve listesi alınır", ALG,
     '    if all(_algebraic(e, syms) for e in eqs) and len(syms) > 1:\n',
     '    if all(_algebraic(e, syms) for e in eqs) and len(syms) > 1:\n        return sols, "mutated"\n',
     T + "test_complete_solutions_does_not_take_the_solver_list"),
    # --- round 5: no complete set out of the classes; the classes (vii)-(xi), identities as written
    ("R01 iki çözücünün uyuşması tamlık sayılır", ALG,
     '        ev["complete"] = None\n        ev["completeness_method"] = ("none (odd roots read as real roots)" if odd_rewritten',
     '        ev["complete"] = not odd_rewritten and r1.ok and r2.ok and isinstance(r2.value, FiniteSet)\n'
     '        ev["completeness_method"] = ("none (odd roots read as real roots)" if odd_rewritten',
     T + "test_round5_solve_equation"),
    ("R02 sınıf dışında SymPy kümesi", EX, '    if var not in getattr(rel, "free_symbols", set()):\n        return sp.solveset(rel, var, domain)',
     '    if var not in getattr(rel, "free_symbols", set()) or not at_risk(rel, var):\n        return sp.solveset(rel, var, domain)',
     T + "test_out_of_the_classes_no_set"),
    ("R03 aynı işaretli iki üstel sıfırlanır", EX, "    if s1 == s2:\n        return []", "    if False:\n        return []",
     T + "test_ratio_of_two_positive_terms_has_no_zero"),
    ("R04 üssün logaritması yanlış (denetimli)", EX, "            L += f.exp * sp.log(f.base)", "            L += f.exp",
     T + "test_round5_class_sets"),
    ("R05 üssün logaritması yanlış, denetim yok", EX,
     "            L += f.exp * sp.log(f.base)" + _RATIO_MID + "    if sp.simplify((term - sign * sp.exp(L)).rewrite(sp.exp)) != 0:",
     "            L += f.exp" + _RATIO_MID + "    if False:", T + "test_round5_class_sets"),
    ("R06 Abs hücresinde işaret okunmaz", EX,
     "            sub[at] = sg * at.args[0] if isinstance(at, sp.Abs) else sp.Integer(sg)",
     "            sub[at] = at.args[0] if isinstance(at, sp.Abs) else sp.Integer(1)", T + "test_round5_class_sets"),
    ("R07 kök adayı denetlenmez", EX, "        if _certified(base.subs(var, c)) == 0:\n            zeros.append((c, S.Zero))",
     "        if True:\n            zeros.append((c, S.Zero))", T + "test_round5_class_sets"),
    ("R08 özdeşliğin yazıldığı kutupları yok", EX,
     "    pp = pp + _written_poles(e, var)\n    poles = _sorted_unique(_on(pp, lo, hi))",
     "    poles = _sorted_unique(_on(pp, lo, hi))", T + "test_an_identity_keeps_its_written_poles"),
    ("R09 özdeşlik tanınmaz", EX, "    ident = _identity(e, var)              # x**2", "    ident = False              # x**2",
     T + "test_round5_class_sets"),
    ("R10 SymPy'nin False ilişkisi okunmaz", EX, "    if rel is sp.false:\n        # SymPy decided",
     "    if False:\n        # SymPy decided", T + "test_round5_solve_equation"),
    ("R11 count_roots sınıfı okumaz", CNT, '        if not distinct:\n            return None, "not_a_rational_function_of_var: multiplicities"',
     '        if True:\n            return None, "not_a_rational_function_of_var: multiplicities"', T + "test_count_roots_of_a_class"),
    ("R12 adım katmanı solve listesine güvenir", DET,
     '    r = sb_run("mathverify.certify.algebra:_polynomial_system_worker", eqs, order, timeout=ctx.timeout)\n'
     '    if not r.ok or not isinstance(r.value, tuple) or r.value[0] is None:\n        return None\n    pts = r.value[0]',
     '    r = sb_run("mathverify.sandbox.ops:solve_system", eqs, order, True, timeout=ctx.timeout)\n'
     '    if not r.ok:\n        return None\n    pts = r.value', T + "test_step_completeness_needs_a_proof"),
    ("R13 açık tanım okunmaz", DET, "    if set(defs) == set(order):\n        sols = [defs]", "    if False:\n        sols = [defs]",
     T + "test_step_completeness_needs_a_proof"),
    ("P12 sürekli alan korumasız", OPS, "    if oscillates(expr, var):\n        # SymPy solves the conditions",
     "    if False:\n        # SymPy solves the conditions", T + "test_continuous_domain_of_a_trigonometric_expression"),
    # --- certify.domain
    ("D01 parça başına tek yoklama", DOM, "        return [lo + (hi - lo) * sp.Rational(k, 8) for k in (1, 3, 4, 5, 7)]\n"
     "    steps = (1, 2, 3, 5, 8, 13, 21)", "        return [(lo + hi) / 2]\n    steps = (1,)",
     T + "test_the_exact_check_probes_every_piece_more_than_once"),
    ("D02 sınırsız parça yoklanmaz", DOM, "isinstance(p, sp.Interval) and p.measure.is_extended_positive:",
     "isinstance(p, sp.Interval) and p.measure.is_positive:", T + "test_the_exact_check_probes_every_piece_more_than_once"),
    ("D03 yazılı tanımlılık tek periyot", DOM, "            s = exact_solveset(bad, var, region)\n",
     "            s = sp.solveset(bad, var, region)\n", T + "test_written_undefined_on_an_interval_past_the_first_period"),
    ("D04 ConditionSet üyeliği yok", DOM, "    if isinstance(dom, sp.ConditionSet):\n        # a condition Ctx.domain_for",
     "    if False:\n        # a condition Ctx.domain_for", T + "test_membership_in_an_unsolved_condition"),
    ("D05 domain_of çözülmemiş koşulda çekimser değil", DOM, "        if ctx.unsolved_conditions(var):\n            # the domain is cut",
     "        if False:\n            # the domain is cut", T + "test_domain_of_under_a_periodic_condition_solved_on_a_bounded_domain"),
    ("D08 ConditionSet üyeliği SymPy'ye sorulur", DOM, "    if isinstance(dom, sp.Set) and dom.has(sp.ConditionSet):\n        try:\n            if certified_sign(c) == NONREAL:",
     "    if False:\n        try:\n            if certified_sign(c) == NONREAL:", T + "test_a_wrong_zero_of_a_non_periodic_condition_is_not_trusted"),
    ("D07 çelişki denetimi ℝ'de tümleyen alır", DOM, "        out = sp.Complement(within, s)", "        out = sp.Complement(S.Reals, s)",
     T + "test_domain_of_under_a_periodic_condition_solved_on_a_bounded_domain"),
    ("D06 domain_of koşulu tabanda çözülmez", DOM, "        within = base if at_risk(cond, var) and _hull(base) is not None else S.Reals\n",
     "        within = S.Reals\n", T + "test_domain_of_under_a_periodic_condition_solved_on_a_bounded_domain"),
    # --- Ctx
    ("B01 kısıt ertelenmez", BASE, "                        if r.free_symbols == {var} and at_risk(r, var):",
     "                        if False:", T + "test_a_constraint_with_a_period_cuts_the_domain_point_by_point"),
    ("B02 yazılı koşul ertelenmez", BASE, "            if at_risk(c, var):\n                deferred.append(c)\n                continue\n",
     "", T + "test_written_conditions_of_tan_and_log_sin"),
    ("B03 yan koşul eski yol", BASE, "                if at_risk(rel_r, var):\n                    # solved by domain_for",
     "                if False:\n                    # solved by domain_for", T + "test_a_side_condition_with_a_period_is_not_applied"),
    ("B04 tanım evreni ertelenmez", BASE, "        dom = self._periodic_parts(self.discourse(var), var, deferred)",
     "        dom = self.discourse(var)", T + "test_domain_of_under_a_periodic_condition_solved_on_a_bounded_domain"),
    ("B05 çözülemeyen koşul düşer", BASE, "                unsolved.append(r)\n                dom = sp.Intersection(dom, sp.ConditionSet(var, r, S.Reals))",
     "                unsolved.append(r)", T + "test_a_constraint_with_a_period_cuts_the_domain_point_by_point"),
    ("B06 cut_by ℝ'de çözer", BASE, "            rr = sb_run(\"mathverify.sandbox.ops:solveset_in\", g, var, dom if risky else S.Reals,",
     "            rr = sb_run(\"mathverify.sandbox.ops:solveset_in\", g, var, S.Reals,",
     T + "test_steps_under_a_periodic_premise_on_a_bounded_window"),
    ("B07 çözülemeyen yan koşul uygulanmış sayılır", VER,
     "            unapplied = unapplied + [str(r) for r in ctx.unsolved_side_conditions(ctx.sym(tvar))]",
     "            pass", T + "test_a_side_condition_with_a_period_is_not_applied"),
    ("B08 tanım evreni tek periyot", PARSE, "            dom = Intersection(dom, exact_solveset(rel, var, S.Reals))",
     "            dom = Intersection(dom, sp.solveset(rel, var, S.Reals))", T + "test_a_domain_of_discourse_with_a_period"),
    # --- algebra
    ("A01 verilenler ℝ'de tek periyot", ALG, "    dom = ctx.cut_by(var, dom, [real_odd_roots(g) for g in rels])",
     "    dom = ctx.cut_by(var, dom, [])\n    for g in rels:\n        dom = sp.Intersection(dom, sp.solveset(real_odd_roots(g), var, S.Reals))",
     T + "test_an_equation_given_with_a_periodic_given"),
    ("A02 eşitsizlik çözülmemiş alanda çekimser değil", ALG, "    if ctx.unsolved_conditions(var):\n        # the domain is cut",
     "    if False:\n        # the domain is cut", T + "test_an_inequality_under_an_unsolved_domain_abstains"),
    ("A03 eşitsizlikte periyodik ilişki ℝ'de", ALG, "truth if at_risk(one, var) else dom,", "dom,",
     T + "test_solve_inequality_system_with_a_periodic_given"),
    ("A04 sp.solve listesi tam sayılır", ALG, "        sols, how = _complete_solutions(eqs, ineqs, syms, sols, ctx)\n",
     "        how = 'mutated'\n", T + "test_evaluate_needs_a_complete_solution_set"),
    ("A05 tamlık penceresi hep ℝ", ALG, "                window = sp.Interval(lo, hi)\n", "                pass\n",
     T + "test_evaluate_with_a_proved_complete_set"),
    ("A06 sınırlı gövdede tamlık yok", ALG, "sp.Interval(*hull) if hull is not None else S.Reals, timeout=timeout)",
     "S.Reals, timeout=timeout)",
     T + "test_tan_on_a_bounded_window_is_not_refuted"),
    # --- counting / extremum / limits / series / formal / steps
    ("C01 periyodik verilen sayımı durdurur", CNT, "(isinstance(r.value, sp.ConditionSet) and not at_risk(rel, var))",
     "isinstance(r.value, sp.ConditionSet)", T + "test_count_integers_with_a_periodic_given"),
    ("C02 count_solutions nowhere okumaz", CNT, "                rels = rels + [sp.false]\n", "                pass\n",
     T + "test_count_solutions_with_a_condition_defined_nowhere"),
    ("E01 extremum koşulu ℝ'de", EXT, "region if region is not None and at_risk(r, var) else S.Reals", "S.Reals",
     T + "test_extremum_under_periodic_conditions"),
    ("L01 limit yanı periyodik koşulu çözer", LIM, "    if any(at_risk(c, var) or c.has(HyperbolicFunction) for c in conds):",
     "    if any(c.has(HyperbolicFunction) for c in conds):", T + "test_limit_side_of_a_periodic_condition_is_not_solved"),
    ("S01 seri indis koşulu tek periyot", SER, "            s = exact_solveset(bad, v, sp.S.Reals)\n",
     "            s = sp.solveset(bad, v, sp.S.Reals)\n", T + "test_series_index_conditions_past_the_first_period"),
    ("F01 Lean ihlal kümesi tek periyot", FORM, "        s = exact_solveset(bad, var, region)\n",
     "        s = sp.solveset(bad, var, region)\n", T + "test_lean_regions_and_violations_of_a_periodic_condition"),
    ("F02 Lean bölgesi tek periyot", FORM, "            s = exact_solveset(c, var, S.Reals)        # one period",
     "            s = sp.solveset(c, var, S.Reals)        # one period", T + "test_lean_regions_and_violations_of_a_periodic_condition"),
    ("S02 adım öncüllerinde periyodik olan çözülmez", DET,
     "        region = ctx.cut_by(v, region, periodic)\n", "        return None, False, False\n",
     T + "test_steps_on_tan_with_its_window_stay_verified"),
    # --- trig_solve
    ("T01 öteki verilenler okunmaz", TRIG, "            if var in r.free_symbols:\n                rels.append(r)\n",
     "            pass\n", T + "test_trig_solve_applies_the_other_conditions"),
    ("T02 denklemin nowhere'i okunmaz", TRIG, "        dom = S.EmptySet                       # the equation as written is defined nowhere",
     "        pass", T + "test_trig_solve_of_an_equation_defined_nowhere"),
    ("T03 bölge süzgeci yok", TRIG, "            drop = m is False\n", "            drop = False\n",
     T + "test_trig_solve_applies_the_other_conditions"),
    ("T04 periyotsuz bölge ℝ sayılır", TRIG, "            periods = set_periods(region)\n", "            periods = []\n",
     T + "test_trig_solve_with_a_free_bound_or_a_general_solution_on_a_restricted_variable"),
    ("T05 uygulanamayan koşulda çekimser değil", TRIG, "    if unbound or unb:\n        return None, unbound + unb\n", "",
     T + "test_trig_solve_with_a_free_bound_or_a_general_solution_on_a_restricted_variable"),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
