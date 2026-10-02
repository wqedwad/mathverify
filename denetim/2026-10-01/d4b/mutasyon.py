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
    ("K01 hücreler SymPy'nin kümesinden", EX, "    zp, pp, _ = _structure(e, var)\n    poles = _sorted_unique",
     "    zp, pp = [(z, S.Zero) for z in sp.solveset(sp.Eq(e, 0), var, sp.Interval(lo, hi))], []\n    poles = _sorted_unique",
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
     "            return None", T + "test_review_b3_b4_b5"),
    ("K11 tamlık sınıfı aranmaz", ALG, "        if not (_algebraic(er, [v]) or at_risk(er, v)):\n            continue",
     "        if False:\n            continue", T + "test_evaluate_with_a_proved_complete_set"),
    ("K12 parantezli tanım evreni küme okunur", PARSE,
     '    if any(op in s for op in ("<", ">", "!=")) and not s.startswith(("Interval", "Union")):',
     '    if any(op in s for op in ("<", ">", "!=")) and not s.startswith(("Interval", "Union", "(", "[")):',
     T + "test_review_b3_b4_b5"),
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
    ("A06 sınırlı gövdede tamlık yok", ALG, "    if hull is not None and at_risk(rel_r, var):", "    if False:",
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
