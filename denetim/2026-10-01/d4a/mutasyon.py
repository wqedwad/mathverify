"""Mutation check of part d4a of the fourth audit's fixes (conventions and the z3 bridge): each mutation
removes one protection, and tests/test_d4_d4a_gelenek.py must fail. The machinery (throwaway clones of the
committed HEAD, exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the list is new.

    .venv/bin/python denetim/2026-10-01/d4a/mutasyon.py [-j N] [--list] [name ...]

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

DOM = "src/mathverify/certify/domain.py"
BASE = "src/mathverify/certify/base.py"
ALG = "src/mathverify/certify/algebra.py"
WP = "src/mathverify/certify/wordproblem.py"
Z3 = "src/mathverify/certify/_z3bridge.py"
DET = "src/mathverify/steps/deterministic.py"
EQ = "src/mathverify/equiv/__init__.py"
SETS = "src/mathverify/equiv/sets.py"
CONV = "src/mathverify/equiv/conventions.py"
PARSE = "src/mathverify/normalize/parse.py"
VER = "src/mathverify/verifier.py"
LEAN = "src/mathverify/formal/statement.py"
T = "tests/test_d4_d4a_gelenek.py"

MUTATIONS = [
    # the conditions (certify.domain)
    ("D01 tek kök tabanı koşulu yok", DOM, "                    add(sp.Contains(base, ODD_ROOT_BASE))\n", "", T),
    ("D02 b**0 koşulu yok", DOM, "            add(sp.Contains(base, ZERO_POWER_BASE))     # 0**0", "            pass  # 0**0", T),
    ("D03 0**k üs koşulu yok", DOM, "            add(sp.Contains(ex, ZERO_POWER_BASE))\n", "            pass\n", T),
    ("D04 binom eski (ℕ₀ tanımsız)", DOM,
     "        conds = [sp.Contains(r_, BINOMIAL_ARGUMENT), sp.Contains(n_ - r_, BINOMIAL_ARGUMENT)]",
     "        conds = [sp.Contains(r_, S.Naturals0), sp.Contains(n_, S.Naturals0)]", T),
    ("D05 Mod bölen koşulu yok", DOM, "        add(sp.Contains(node.args[1], MOD_DIVISOR))\n",
     "        pass\n", T),
    ("D06 gelenek kümesi yanlış der", DOM, "        return sp.true if ok is True else None      # undecided, never false",
     "        return sp.true if ok is True else sp.false", T),
    ("D07 kapalı koşul her yerde tutar", DOM,
     "            return (S.Reals, S.EmptySet) if held is sp.true else (S.EmptySet, S.Reals)",
     "            return (S.Reals, S.EmptySet)", T),
    ("D08 domain_of gelenekte karar verir", DOM, "    if any(is_convention(c) for c in conds):\n        # a point where",
     "    if False:\n        # a point where", T),
    # the domain (certify.base)
    ("B01 Ctx yalnız Sum aralığını okur", BASE, "            if is_convention(c) and fs <= {var}:",
     "            if is_range_span(c) and fs <= {var}:", T),
    ("B02 denklemin gelenek koşulu uygulanmış sayılır", BASE,
     "if not (isinstance(c, sp.Basic) and c in enforced and not is_convention(c))]",
     "if not (isinstance(c, sp.Basic) and c in enforced)]", T),
    # algebra
    ("A01 gelenek kipinde değil (eski çekimserlik)", ALG,
     "    conv = [c for c in unbound if isinstance(c, sp.Basic) and is_convention(c) and c.free_symbols <= {var}]",
     "    conv = []", T),
    ("A02 gelenek bölgesindeki iddia kökü alan dışı", ALG,
     "        rejected = [(c, \"definedness_undecided: convention\" if w == \"outside_domain_of_discourse\"",
     "        rejected = [(c, w if w == \"outside_domain_of_discourse\"", T),
    ("A03 gelenek kipinde tamlık geçer", ALG,
     "    if conv:\n        return unknown(LAYER, \"convention_region_candidates\", 0, ev)\n",
     "    if False:\n        return unknown(LAYER, \"convention_region_candidates\", 0, ev)\n", T),
    ("A04 boş küme gelenek kipinde geçer", ALG, "            if sev.get(\"complete\") and not conv:",
     "            if sev.get(\"complete\"):", T),
    ("A05 değerlendirmede tek kök adayları eksik", ALG,
     "        if any(real_odd_roots(e) != e for e in eqs) and any(", "        if False and any(", T),
    # the review (attack A): comparisons on the domain without the points where a value is another value
    ("G01 sadeleştirme gelenek noktalarını okumaz", ALG,
     "    if ok is not False:\n        ok = _beyond_value_conventions(ctx, claimed, expr, syms, ok, ev)",
     "    if False:\n        ok = _beyond_value_conventions(ctx, claimed, expr, syms, ok, ev)", T),
    ("G02 verilensiz değerlendirme gelenek noktalarını okumaz", ALG,
     "        if dom and ok is not False:\n            ok = _beyond_value_conventions",
     "        if False:\n            ok = _beyond_value_conventions", T),
    ("G03 değer geleneği bölgesi boş", BASE, '        self.cache[f"valueconv:{var.name}"] = vback',
     '        self.cache[f"valueconv:{var.name}"] = S.EmptySet', T),
    ("G04 tek okumada ayrışma çürütür", BASE, "            if scalar_equal(a, b) is False:",
     "            if scalar_equal(a, b) is not True:", T),
    ("G05 iki okumada ayrışma çürütmez", ALG,
     "        ev[\"counterexample_both_readings\"] = pt\n        return False",
     "        ev[\"counterexample_both_readings\"] = pt\n        return None", T),
    ("G06 gelenek bölgesinde onay verilir", ALG,
     "                                     if ctx.ns.get(s_.name) == s_}\n    return None",
     "                                     if ctx.ns.get(s_.name) == s_}\n    return ok", T),
    ("V06 N değişken ve küme çakışması okunur", VER, "    if clash:\n        return \"clash\"",
     "    if False:\n        return \"clash\"", T),
    # z3 and word problems
    ("Z01 örneksiz verilen çürütür", WP, "        if out[\"other_unsat\"] is True:\n            return \"ir_inconsistent\"",
     "        if out[\"other_unsat\"] is True:\n            return \"refuted\"", T),
    ("Z02 tamsayı evreni z3'te düşer", WP, "    if dom in (S.Integers, S.Naturals, S.Naturals0):\n        return sp.Contains(v, dom, evaluate=False)",
     "    if dom in (S.Integers,):\n        return sp.true", T),
    ("Z03 kesişimde tamsayılık düşer", WP, "        return sp.And(*[_set_as_relation(a, v) for a in dom.args])",
     "        return sp.And(*[_set_as_relation(a, v) for a in dom.args if a not in (S.Integers,)])", T),
    ("Z04 iddiada tek kök z3'e gider", WP, "            if odd_root_powers(claimed):\n", "            if False:\n", T),
    ("Z05 köprü tek kökü çevirir", Z3, "                if q % 2 == 1 and base.is_extended_nonnegative is not True:",
     "                if False:", T),
    ("Z06 köprü negatif bölenli Mod'u çevirir", Z3, "            if e.args[1].is_positive is not True:",
     "            if False:", T),
    ("Z07 köprü IsInt'i düşürür", Z3, "            isint = z3.BoolVal(True) if z3.is_int(a) else z3.IsInt(a)",
     "            isint = z3.BoolVal(True)", T),
    ("Z08 köprü sign'ı çevirmez", Z3, "        if isinstance(e, sp.sign):\n", "        if False:\n", T),
    # the step layer
    ("S01 öncül yalnız esas dalda çözülür", DET, "    for q in dict.fromkeys([p, real_odd_roots(p)]):",
     "    for q in [p]:", T),
    ("S02 gelenek bölgesinde özdeşlik yeniden denenmez", DET,
     "    if status == \"verified\":\n        status, ev = _verified_where_conventions",
     "    if False:\n        status, ev = _verified_where_conventions", T),
    ("S03 kapalı gelenekli iddia çürütülür", DET,
     "            if status == \"refuted\" and _convention_as_written(st.claim, step_ns):",
     "            if False:", T),
    ("S04 öncül kümesi gelenek bölgesini yok sayar", DET, "        if not clear:\n            return None, False, False",
     "        if False:\n            return None, False, False", T),
    ("S05 atama gelenek noktasında alan dışı", DET,
     "    dom = sp.Union(ctx.domain_for(v), ctx.convention_region(v))\n    for part in",
     "    dom = ctx.domain_for(v)\n    for part in", T),
    ("S06 gelenek noktası doğrulamayı engellemez", DET, "        if exhaustive and not at_convention:",
     "        if exhaustive:", T),
    # the comparison engine
    ("E01 kapalı tek kök tek okunur", CONV,
     "    if not any(p.base.is_number for it in items for p in odd_root_powers(it)):\n        return None",
     "    if True:\n        return None", T),
    ("E02 iki okuma uyuşmasa da karar", EQ, "        return (r1 if r1 == r2 else None), ev", "        return r1, ev", T),
    ("E03 açık tek kök tabanı karşılaştırılır", EQ, "        if open_bases:\n", "        if False:\n", T),
    ("E04 scalar_equal tek okuma", SETS, "        return r1 if r1 == r2 else None", "        return r1", T),
    # the parse
    ("P01 cbrt esas değer", PARSE, '"cbrt": _cbrt,', '"cbrt": sp.cbrt,', T),
    ("P02 root esas değer", PARSE, '"root": _real_root,', '"root": sp.root,', T),
    ("P03 LaTeX kök esas değer", PARSE, "                if func.FUNC_SQRT() and func.root:", "                if False:", T),
    ("P04 ∛ okunmaz", PARSE, '"∛": "cbrt", ', "", T),
    ("P05 ℕ⁺ okunmaz", PARSE, "    named = number_set_named(s)\n    if named is not None:\n        return named\n    if s.startswith",
     "    named = None\n    if named is not None:\n        return named\n    if s.startswith", T),
    # the verifier
    ("V01 ℕ tek okunur", VER, "    if zero is None:\n        return layers, flags", "    if True:\n        return layers, flags", T),
    ("V02 okumalar ayrışınca da karar", VER, "    if v_pos == v_zero:", "    if True:", T),
    ("V03 çıplak N yeniden yazılmaz", VER, "        if prev_ok and next_ok:", "        if False:", T),
    ("V05 kümede tek kök tek okunur", VER, "               and not (both_ways and c.args[1].kind == \"odd_root\") for c in conds):",
     "               and c.args[1].kind != \"odd_root\" for c in conds):", T),
    ("V04 iddianın kapalı geleneği okunmaz", VER, "    if conv:\n        layers.append(", "    if False:\n        layers.append(", T),
    # Lean
    ("L01 Lean deyimi gelenekte kurulur", LEAN, "        _conventions_gate(obj, claimed_answer, ns)\n", "", T),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
