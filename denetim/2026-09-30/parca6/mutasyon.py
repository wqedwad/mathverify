"""Mutation check of part (vi) of the N1-N9 re-run (30 Sep 2026): a condition on the solved variable
that names another symbol is read with the values the givens fix, or the certificate abstains
(certify.base Ctx.domain_for / side_conditions / on_var / discourse, certify.algebra, certify.counting,
certify.domain, certify.extremum). The machinery (throwaway clones of the committed HEAD, exit codes,
clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-30/parca6/mutasyon.py [-j N] [--list] [name ...]

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

BASE = "src/mathverify/certify/base.py"
ALG = "src/mathverify/certify/algebra.py"
CNT = "src/mathverify/certify/counting.py"
DOMF = "src/mathverify/certify/domain.py"
EXT = "src/mathverify/certify/extremum.py"
T = "tests/test_parca6_sembollu_kisit.py"

MUTATIONS = [
    # --- (B) certify.base: the domain, the side conditions, the relations read on the variable
    ("B01 tanım evreni verilen değeri okumaz", BASE,
     "        ns.update({s_.name: v for s_, v in self.bindings().items() if s_ != var})\n", "", T),
    ("B02 tanım evreninin serbest sembolü listelenmez", BASE,
     "        if dom.free_symbols - {var}:\n            unapplied.append(str(self.ir.domain_of_discourse))",
     "        if False:\n            unapplied.append(str(self.ir.domain_of_discourse))", T),
    ("B03 kısıtın serbest sembolü listelenmez", BASE,
     "                        elif var in r.free_symbols:\n                            unapplied.append(c)",
     "                        elif False:\n                            unapplied.append(c)", T),
    ("B04 yan koşulun serbest sembolü listelenmez", BASE,
     '        unapplied += self.cache.get(f"side_unbound:{var.name}", [])\n', "", T),
    ("B05 yazılı koşulun serbest sembolü listelenmez", BASE,
     "                if fs and var in fs:\n                    unapplied.append(c)",
     "                if False:\n                    unapplied.append(c)", T),
    ("B06 yan koşula verilen değer konmaz", BASE,
     "                rel = self._with_bound_values(rel, var)\n                if rel is sp.false:",
     "                if rel is sp.false:", T),
    ("B07 verilenin yanlışladığı yan koşul atlanır", BASE,
     "                if rel is sp.false:                     # the values the givens fix contradict it\n"
     "                    sets.append(S.EmptySet)\n                    continue\n", "", T),
    ("B08 verilen denklem yan koşul değil", BASE,
     "                if not isinstance(rel, sp.core.relational.Relational) or var not in rel.free_symbols \\\n",
     "                if not isinstance(rel, sp.core.relational.Relational) or isinstance(rel, sp.Eq) \\\n"
     "                        or var not in rel.free_symbols \\\n", T),
    ("B09 görevin kendi denklemi yan koşul sayılır", BASE,
     "                        or rel == main:\n", "                        or False:\n", T),
    ("B10 count_roots ve domain_of yan koşul okumaz", BASE,
     '"count_roots": "expr",\n                      "domain_of": "expr"}', "}", T),
    ("B11 tanımsız sembollü verilen atlanır", BASE,
     "                except UndeclaredSymbolError:\n                    unapplied.append(g)\n                    continue",
     "                except UndeclaredSymbolError:\n                    continue", T),
    ("B12 on_var verilen değeri koymaz", BASE, "            r2 = r.xreplace(bind) if bind else r\n",
     "            r2 = r\n", T),
    ("B13 on_var serbest sembolü listelemez", BASE,
     '            if getattr(r2, "free_symbols", set()) - {var}:\n                unbound.append(r)',
     "            if False:\n                unbound.append(r)", T),
    ("B14 denetlenen koşul muafiyeti her koşulu kapsar", BASE,
     "                if not (isinstance(c, sp.Basic) and c in enforced and not is_range_span(c))]",
     "                if not isinstance(c, sp.Basic)]", T),
    # --- (C) the certificates
    ("C01 cebir denklemin kendi koşulunu muaf tutmaz", ALG,
     "ctx.unapplied_conditions(var, enforced=definedness_conditions(rel, var)) + unbound",
     "ctx.unapplied_conditions(var) + unbound", T),
    ("C02 cebir verilen denklemi atlar", ALG,
     "    rels = [g for g in ctx.givens() if g != exclude and isinstance(g, (sp.core.relational.Relational, And))",
     "    rels = [g for g in ctx.givens() if g != exclude and not isinstance(g, Eq)\n"
     "            and isinstance(g, (sp.core.relational.Relational, And))", T),
    ("C03 eşitsizlik bağsız koşulda çekimser değil", ALG,
     "    unbound = ctx.unapplied_conditions(var) + unbound\n    if unbound:\n        return condition_not_applied(LAYER, unbound)\n    if not rels:",
     "    if not rels:", T),
    ("C04 count_roots tanım kümesini okumaz", CNT,
     '        if m is False:\n            rejected.append((str(rt), "outside_the_domain"))',
     '        if False:\n            rejected.append((str(rt), "outside_the_domain"))', T),
    ("C05 count_integers verileni değişkende okumaz", CNT,
     "    rels, unbound = ctx.on_var(ctx.givens(), var)\n", "    rels, unbound = ctx.givens(), []\n", T),
    ("C06 count_solutions tanım evrenini okumaz", CNT, "domains=doms)", "domains=None)", T),
    ("C07 domain_of bağsız koşulda çekimser değil", DOMF,
     "        if unbound:\n            # a condition on x that names a symbol no given fixes",
     "        if False:\n            # a condition on x that names a symbol no given fixes", T),
    ("C08 extremum bağsız koşulda çekimser değil", EXT,
     '        if not p.get("interval") and ctx.unapplied_conditions(var):', "        if False:", T),
    ("C09 karar verilemeyen aday tamlığı bozmaz", ALG,
     "            complete = complete and not any(_undecided(why) for _, why in rejected)\n", "", T),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
