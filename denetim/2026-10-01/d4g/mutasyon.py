"""Mutation check of part d4g of the fourth audit's fixes (the step refuter): each mutation removes one
protection, and tests/test_d4_d4g_adim.py must fail. The machinery (throwaway clones of the committed HEAD,
exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the list is new.

    .venv/bin/python denetim/2026-10-01/d4g/mutasyon.py [-j N] [--list] [name ...]

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

DET = "src/mathverify/steps/deterministic.py"
T = "tests/test_d4_d4g_adim.py"

MUTATIONS = [
    # D4-ADIM-A: sample agreement
    ("A01 analitik olmayan baş da kanıt", DET,
     "    if not (_analytic_off_discrete(sp.sympify(a)) and _analytic_off_discrete(sp.sympify(b))):\n"
     "        return _analytic_on_interval(",
     "    if False:\n        return _analytic_on_interval(", T),
    ("A07 log argümanının pozitifliği sınanmaz", DET,
     "            return arg_ok(e.args[0]) and _proved_empty(sp.Le(e.args[0], 0), v, iv, ctx)",
     "            return arg_ok(e.args[0])", T),
    ("A08 aralıkta analitiklik okunmaz", DET, "    return ok(a) and ok(b)", "    return False", T),
    ("A09 tek değerli hücre örnek sayılır", DET, "    if not dom:\n        return True\n", "    if not dom:\n        return False\n", T),
    ("A02 ayrık küme de kanıt", DET, "    return all(_has_interior(d) for d in dom.values())", "    return True", T),
    ("A03 hücre ispatı kabul edilmez", DET,
     '    if isinstance(proof, str) and (proof.startswith("cells_proved") or proof.startswith("period_")):\n        return True\n',
     "", T),
    ("A04 son karşılaştırmada kapı yok", DET,
     "        if ok is True and not _agreement_proves(rhs, val, dom, cev, ctx):", "        if False:", T),
    ("A05 beyaz listede log", DET, "_ENTIRE = (sp.exp, sp.sin, sp.cos, sp.sinh, sp.cosh)",
     "_ENTIRE = (sp.exp, sp.sin, sp.cos, sp.sinh, sp.cosh, sp.log, sp.asin)", T),
    ("A06 sembolik olmayan Pow tabanı", DET,
     "        if b.is_number and not b.free_symbols and b.is_positive is True and b.is_finite is True:",
     "        if True:", T),
    # D4-ADIM-B: withdrawal of a refutation with a range that may run backwards
    ("B01 geri noktada her ret geri çekilir", DET, "        return not _reading_free(nodes, point, ctx)",
     "        return True", T),
    ("B02 geri noktada hiçbir ret geri çekilmez", DET, "        return not _reading_free(nodes, point, ctx)",
     "        return False", T),
    ("B03 okunmayan noktada yeniden sınama yok", DET,
     "    return not _refuted_in_both_readings(claim, ranges, nodes, ctx, list(premises), recheck)",
     "    return True", T),
    ("B04 ileri noktada sınama yok", DET,
     '    for pt in fwd:\n        _tick()\n        if recheck(_substituted(claim, pt)) == "refuted":\n            return True\n',
     "", T),
    ("B05 geri adayda okuma bağımsızlığı aranmaz", DET,
     "        if _reading_free(nodes, pt, ctx) and recheck(", "        if recheck(", T),
    ("B06 adaylar öncülü sağlamak zorunda değil", DET,
     "        if any(_holds_exactly(p, pt, ctx) is not True for p in on):\n            continue\n", "", T),
    ("B07 Karr değeri boş değerle karşılaştırılmaz", DET,
     "        if not d.ok or d.value != 0:\n            return False\n", "", T),
    # D4-ADIM-E: the task's interval, the antiderivative's point, symbols a point does not fix
    ("E01 görev aralığı havuzda yok", DET, "pool = (list(givens) + list(restrictions) + list(window)",
     "pool = (list(givens) + list(restrictions)", T),
    ("E02 ilkel sertifikasının noktası okunmaz", DET, "    if cx is None:\n        # an antiderivative", "    if False:\n        # an antiderivative", T),
    ("E03 sabitlenmeyen sembol öncülü dışlar", DET,
     "            elif p.free_symbols & fixed:\n                return False\n",
     "            else:\n                return False\n", T),
    # D4-ADIM-F: budget, sets not in closed form
    ("F01 bütçe hiç dolmaz", DET, "    if d is not None and time.monotonic() > d:\n        raise _OutOfTime()",
     "    if False:\n        raise _OutOfTime()", T),
    ("F02 kapalı biçimde olmayan bölge örneklenir", DET,
     "        if not all(_closed_form_set(d) for d in doms.values()):\n            # a set SymPy",
     "        if False:\n            # a set SymPy", T),
    # D4-ADIM-H: Karr-only identities
    ("H01 ileri aralık denetimi yok", DET,
     '    if not ranges:\n        return "verified", ev\n    syms = set().union(*(c.free_symbols for c in ranges))\n    nodes',
     '    if True:\n        return "verified", ev\n    syms = set().union(*(c.free_symbols for c in ranges))\n    nodes', T),
    ("H02 boş okuma sınanmadan doğrulanır", DET,
     '    if s2 == "verified":\n        return "verified", {**ev, "empty_reading_where_a_range_runs_backwards"',
     '    if True:\n        return "verified", {**ev, "empty_reading_where_a_range_runs_backwards"', T),
    ("H03 bölgede yeniden sınama yok", DET,
     '    if status == "refuted" or (status == "unknown" and ev.get("reason") in ("parametric_form", _KARR_ONLY)):',
     '    if status == "refuted" or (status == "unknown" and ev.get("reason") in ("parametric_form",)):', T),
    # D4-ADIM-J: a point where the claim has no value
    ("J01 noktada tanımsızlık denetlenmez", DET,
     '    if _undefined_at(conds, point, ctx):\n        return "unknown", {"reason": "claim_undefined_at_the_point"}\n',
     "", T),
    ("J02 retten sonra tanımsız nokta denetlenmez", DET,
     '                if status == "refuted" and _counterexample_where_undefined(claim, ev, conds, ctx):',
     "                if False:", T),
    ("J03 bölge yolunda yazılı koşul yok", DET,
     "    own = [c for c in conds if c.free_symbols <= syms and c not in direct]", "    own = []", T),
    ("J04 tanımlı bölgede doğrulanır", DET, '        if narrowed and status == "refuted":', "        if False:", T),
    # D4-ADIM-D, TAN-11: definedness on the premises' sets
    ("D01 sonlu küme noktadan noktaya okunmaz", DET,
     "    if isinstance(s, sp.Range) and s.is_finite_set is True and s.size <= _MAX_DEFINED_POINTS:\n        s = sp.FiniteSet(*s)\n    if not isinstance(s, sp.FiniteSet)",
     "    if True:\n        return None\n    if not isinstance(s, sp.FiniteSet)", T),
    ("D02 büyük kümede ispat aranmaz", DET,
     "            if not _holds_on(c2, u, sets[u], ctx):\n                return True", "            if False:\n                return True", T),
    ("D03 iki sembolde sonsuz küme kanıtsız geçer", DET,
     "                return True                  # several symbols on infinite sets: not proved",
     "                continue", T),
    ("D04 alanı daraltmayan öncül de okunur", DET, "        if region is not None and not whole:",
     "        if region is not None:", T),
    ("D05 tek sembollü öncül okunmaz", DET,
     "        if not own:\n            continue\n        region = ctx.domain_for(v)", "        if True:\n            continue\n        region = ctx.domain_for(v)", T),
    ("D06 gelenek koşulu kanıtsız sayılır", DET,
     "        elif is_convention(c):\n            return True", "        elif is_convention(c):\n            return False", T),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
