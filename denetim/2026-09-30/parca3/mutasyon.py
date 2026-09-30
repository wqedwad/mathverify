"""Mutation check of part (iii) of the N1-N9 re-run (30 Sep 2026, DECISIONS §75): the givens of a
`solve_equation` reach the z3 certificate (N7), and a `compute` step in parameters the proved premises
pin is checked at their values (V15 S1). The machinery (throwaway clones of the committed HEAD, exit
codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-30/parca3/mutasyon.py [-j N] [--list] [name ...]

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

WP = "src/mathverify/certify/wordproblem.py"
BASE = "src/mathverify/certify/base.py"
DET = "src/mathverify/steps/deterministic.py"
TP = "tests/test_parca3_verilen_parametre.py"

MUTATIONS = [
    # --- (W) the givens of solve_equation in z3
    ("W01 eski verilen seçimi", WP,
     "                extra, tied = _equation_givens(ctx, rel, var, claimed.free_symbols, others)\n",
     "                extra = [g for g in ctx.givens() if not isinstance(g, Eq) and g.free_symbols == {var}]\n"
     "                tied = set(rel.free_symbols)\n", TP),
    ("W02 verilen zinciri izlenmez", WP, "                syms |= fs\n                grew = True",
     "                grew = True", TP),
    ("W03 denklemin kendisi verilenlerden ayıklanmaz", WP, "    rest = [(g, True) for g in ctx.givens() if g != rel]",
     "    rest = [(g, True) for g in ctx.givens()]", TP),
    ("W10 değişken kısıtı ve tanım evreni zincire girmez", WP, " + [(c, False) for c in others]\n", "\n", TP),
    ("W11 bağlı semboller yalnız denklemden", WP,
     "            free_params = sorted(s_.name for s_ in tied - pinned - {var})",
     "            free_params = sorted(s_.name for s_ in rel.free_symbols - pinned - {var})", TP),
    ("W04 değişkende ikinci denklem sistem sayılmaz", WP, "            raise _GivenSystem(str(g))", "            pass", TP),
    ("W05 çelişen verilenler denetlenmez", WP, "            if params:\n", "            if False:\n", TP),
    ("W06 serbest parametreyle de onay", WP,
     '                    cert["status"] = "certified" if not free_params else "parameters_not_pinned"',
     '                    cert["status"] = "certified"', TP),
    ("W07 hiçbir parametre sabitlenmiş sayılmaz", WP,
     "            pinned = {b[0] for b in map(closed_binding, extra + others) if b is not None}",
     "            pinned = set()", TP),
    ("W08 gerçel olmayan değer de sabitler", BASE, "and not c.has(*_OPERATIONS) and c.is_real is True:",
     "and not c.has(*_OPERATIONS):", TP),
    ("W09 sembollü değer de sabitler", BASE, "isinstance(c, sp.Expr) and not c.free_symbols \\\n",
     "isinstance(c, sp.Expr) \\\n", TP),
    # --- (S) compute steps at the pinned values
    ("S01 sabitlenmiş değerde yeniden denetim yok", DET, "                        if pins:\n", "                        if False:\n", TP),
    ("S02 kanıtlanmamış adım da sabitler", DET, "                                     + [parsed[k] for k in verified\n",
     "                                     + [parsed[k] for k in parsed\n", TP),
    ("S03 başka dalın değeri de sabitler", DET,
     "                                        if k in parsed and parsed_cases.get(k, frozenset()) <= my_case_ids])",
     "                                        if k in parsed])", TP),
    ("S04 sabitlenmemiş sembol kalabilir", DET, "    if set(vals) != syms:\n        return None", "    if not vals:\n        return None", TP),
    ("S05 iki farklı değer denetlenmez", DET,
     "    if any(exact_equal(v, vs[0]) is not True for vs in vals.values() for v in vs[1:]):\n        return None\n", "", TP),
    ("S06 işlemli iddia da yerine koyulur", DET,
     "claim.has(sp.Integral, sp.Sum, sp.Product, sp.Limit, sp.Derivative, sp.Subs, sp.Lambda):",
     "False:", TP),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
