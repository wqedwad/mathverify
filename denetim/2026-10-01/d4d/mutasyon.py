"""Mutation check of part d4d of the fourth audit's fixes (2 Oct 2026): each mutation removes one guard of the
givens' bindings and conditions (`normalize.parse.read_condition`, `hold_parametric`, `substitute_free`,
`certify.base.Ctx.binding_issues`, `side_conditions`, `domain_for`, `written_conditions`,
`certify.domain.guard_roots` / `written_definedness`, `certify.algebra._filter_solutions` /
`_meets_inequalities`, `certify.extremum._conditions_on`, the verifier's intake). The machinery (throwaway
clones of the committed HEAD, exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the
list of mutations is new.

    .venv/bin/python denetim/2026-10-01/d4d/mutasyon.py [-j N] [--list] [name ...]

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

PAR = "src/mathverify/normalize/parse.py"
BAS = "src/mathverify/certify/base.py"
DOM = "src/mathverify/certify/domain.py"
ALG = "src/mathverify/certify/algebra.py"
EXT = "src/mathverify/certify/extremum.py"
LIM = "src/mathverify/certify/limits.py"
VER = "src/mathverify/verifier.py"
T = "tests/test_d4_d4d_baglama.py"

MUTATIONS = [
    # --- G1: conditions
    ("M01 'or' ayrılmaz", PAR, '_OR_JOIN_RE = re.compile(r"\\s+or\\s+|\\s*∨\\s*|\\s*\\|\\|\\s*|(?<=\\))\\s*\\|\\s*(?=\\()")',
     '_OR_JOIN_RE = re.compile(r"(?!x)x")', T),
    ("M02 üyelik okunmaz", PAR, "            m = _DOMAIN_MEMBER_RE.match(p)\n            n = _NOT_IN_RE.match(p)",
     "            m = None\n            n = _NOT_IN_RE.match(p)", T),
    ("M03 LaTeX x \\in S okunmaz", PAR,
     "        return sp.Contains(c.lhs, _reals_set(c.rhs, spec), evaluate=False)", "        return c", T),
    ("M04 okunamayan yan koşul düşer", BAS,
     "                except Exception:  # noqa: BLE001 - UndeclaredSymbolError, ParseError: not applied\n"
     "                    unapplied.append(g)\n",
     "                except Exception:  # noqa: BLE001 - UndeclaredSymbolError, ParseError: not applied\n", T),
    ("M05 bileşik yan koşul düşer", BAS,
     "                    if sol is None:\n                        unapplied.append(g)\n                    else:\n"
     "                        sets.append(sol)\n                    continue\n",
     "                    continue\n", T),
    ("M06 condition_set Or'u kesişim okur", BAS,
     "            return sp.Intersection(*parts) if isinstance(cond, sp.And) else sp.Union(*parts)",
     "            return sp.Intersection(*parts)", T),
    ("M07 extremum Or'u okumaz", EXT, "            rel = read_condition(s_, ctx.ns)\n",
     "            rel = __import__('mathverify.normalize.parse', fromlist=['x']).parse_relation(s_, ctx.ns)\n", T),
    ("M08 extremum bileşik koşulu düşürür", EXT, "        sets.append(sol)\n    if with_interval:",
     "    if with_interval:", T),
    ("M09 extremum okunamayanı düşürür", EXT,
     "        except Exception:  # noqa: BLE001 - UndeclaredSymbolError, ParseError: the certificate abstains\n"
     "            unread.append(s_)\n",
     "        except Exception:  # noqa: BLE001 - UndeclaredSymbolError, ParseError: the certificate abstains\n", T),
    ("M10 eşitlik yolunda 'and' okunmaz", ALG, "        g = read_condition(src, ctx.ns)\n        try:\n",
     "        g = ctx.rel(src)\n        try:\n", T),
    ("M11 eşitsizlik denetimi bileşiği geçirir", ALG,
     "        if h is sp.true or getattr(h, \"free_symbols\", None):\n            continue\n        hv = relation_holds_at",
     "        if h is sp.true or getattr(h, \"free_symbols\", None) or not isinstance(h, sp.core.relational.Relational):\n"
     "            continue\n        hv = relation_holds_at", T),
    # --- G7, G8, G9, TAN-01/03/04: the bindings
    ("M12 kapı çağrılmaz", VER, "    issue = ctx.binding_issues()\n", "    issue = None\n", T),
    ("M13 çakışan iki değer", BAS,
     '            note("ir_inconsistent" if any(d not in (0, None) for d in diff) else "given_binding_undecided",',
     '            (lambda *a: None)("ir_inconsistent" if any(d not in (0, None) for d in diff) else "x",', T),
    ("M14 bildirim denetlenmez", BAS, "            if dset is not None:\n                d = in_domain(dset, v)",
     "            if False:\n                d = in_domain(dset, v)", T),
    ("M15 tanım evreni denetlenmez", BAS, "            if self._dod_mentions(s_):\n                try:",
     "            if False:\n                try:", T),
    ("M16 değerlendirilmiş False (varsayım) okunmaz", BAS,
     "                if substitute_free(rel, allb) is sp.false:", "                if False:", T),
    ("M17 kapalı verilen kararı okunmaz", BAS,
     "            h = closed_verdict(r2)\n            if h is not True:", "            h = closed_verdict(r2)\n            if False:", T),
    ("M18 kapalı verilen bağlamasız atlanır", BAS, "            if fs and not fs & set(allb):", "            if not fs & set(allb):", T),
    ("M19 yazılı koşul değerde okunmaz", BAS,
     "                h = closed_verdict(c)\n                if h is not True:", "                h = closed_verdict(c)\n                if False:", T),
    ("M20 yazılı koşula değer konmaz", BAS, "                    e2 = substitute_free(e, pins)", "                    e2 = e", T),
    ("M21 kısıt bağlaması yok", BAS, "        cbind, _ctexts = self._constraint_bindings()",
     "        cbind, _ctexts = {}, []", T),
    ("M23 bağlamayla False kısıt düşer", BAS,
     "                            # Ctx.binding_issues abstains on the problem before any certificate reads this\n"
     "                            dom = S.EmptySet\n",
     "                            # Ctx.binding_issues abstains on the problem before any certificate reads this\n", T),
    ("M24 kapalı kısıt düşer", BAS,
     "                            if h is False:\n                                dom = S.EmptySet\n"
     "                            elif h is None:\n                                unapplied.append(c)\n",
     "                            pass\n", T),
    # --- TAN-09
    ("M25 yazılı koşullar bağlamadan önce okunur", BAS, "            cs, nw = written_definedness(s_, self.ns, pins)",
     "            cs, nw = written_definedness(s_, self.ns)", T),
    ("M26 written_definedness değer koymaz", DOM,
     "    if pins:\n        try:\n            with sp.evaluate(False):\n                e = substitute_free(e, pins)",
     "    if False:\n        try:\n            with sp.evaluate(False):\n                e = substitute_free(e, pins)", T),
    ("M27 limit koşulları bağlamadan önce", LIM, "        written, nowhere = written_definedness(p[\"expr\"], ctx.ns, pins)",
     "        written, nowhere = written_definedness(p[\"expr\"], ctx.ns)", T),
    # --- G10
    ("M28 guard_roots kararsız üyeliği tutar", DOM,
     "        if d is None:\n            # no exact check decides it",
     "        if d is None and membership_undecided(domain, c):\n            # no exact check decides it", T),
    ("M29 _filter_solutions kararsız tanım kümesini tutar", ALG,
     "                if d is None:\n                    # no exact check decides the membership",
     "                if False:\n                    # no exact check decides the membership", T),
    ("M30 _filter_solutions kararsız kısıtı tutar", ALG,
     "                        if hv is None:\n                            held = True\n", "", T),
    ("M31 _meets_inequalities kararsızı sağlar sayar", ALG,
     "        if hv is None:\n            out = None\n", "", T),
    ("M32 kabul edilenlerde kararsız aranmaz", ALG,
     "        undecided += [s_ for s_ in admissible if _meets_inequalities(s_, ineqs) is None]\n", "", T),
    # --- P1
    ("M33 pin bağlı değişkende engellenmez", PAR,
     "            if blocked:\n                raise PinnedBoundVariable(", "            if False:\n                raise PinnedBoundVariable(", T),
    ("M34 kapsayan bağlayıcı sayılmaz", PAR,
     "                             and (s_ in bound or s_.name in protected))", "                             and (s_.name in protected))", T),
    ("M35 görev değişkeni korunmaz", PAR,
     "                             and (s_ in bound or s_.name in protected))", "                             and (s_ in bound))", T),
    ("M36 ad alanında koruma yok", PAR, "            ns[PROTECTED_KEY] = frozenset(task_variables(ir))\n", "", T),
    ("M37 substitute_free bağlı değişkeni de değiştirir", PAR,
     "        inner = {s_: v for s_, v in sub.items() if s_ not in bound} if bound else sub",
     "        inner = sub", T),
    ("M38 kapı sızmayı not etmez", BAS, "        for c in conflicts:\n            note(\"given_binds_a_bound_variable\", c)\n", "", T),
    # --- review of d4d
    ("N01 and/or aynı düzeyde okunur", PAR, "    if len(parts) > 1 and any(len(c) > 1 for c in parts):",
     "    if False:", T),
    ("N02 gerçel olmayan küme kabul", PAR, "    if not isinstance(st, sp.Set) or st.is_subset(S.Reals) is not True:",
     "    if not isinstance(st, sp.Set):", T),
    ("N03 küme okuma hatası sarılmaz", PAR, "    except Exception as e:  # noqa: BLE001 - `[2]` raised AttributeError",
     "    except ZeroDivisionError as e:  # noqa: BLE001 - `[2]` raised AttributeError", T),
    ("N04 true/false'a inen metin okunur", PAR,
     "    if (rel is sp.true or rel is sp.false) and _mentions_variable(spec, ns):", "    if False:", T),
    ("N05 LaTeX notin okunmaz", PAR, "        m = _LATEX_NOTIN_RE.match(spec)", "        m = None", T),
    ("N06 'not in' okunmaz", PAR, "            n = _NOT_IN_RE.match(p)", "            n = None", T),
    ("N07 denklik okunur", PAR, "    if is_latex(spec) and _LATEX_CONGRUENCE_RE.search(spec):", "    if False:", T),
    ("N08 Ctx.rel çökmeyi geçirir", BAS,
     "            return self._confirmed(s, not_collapsed(parse_relation(s, self.ns), s, self.ns))",
     "            return self._confirmed(s, parse_relation(s, self.ns))", T),
    ("N09 aynı değer iki yazımda çakışma", PAR, "                if s_ in found and not same_value(found[s_], v):",
     "                if s_ in found and found[s_] != v:", T),
    ("N10 kısıt ve verilen aynı değerde çakışma", BAS,
     "            if all(d == 0 for d in diff):\n                continue", "            if False:\n                continue", T),
    ("N11 görev değişkeni sabitlenebilir", BAS,
     "        if self.ir.task.kind in self._OPERATOR_VAR_KINDS and {s_.name for s_ in bind} & tv:",
     "        if False:", T),
    ("N12 parametre koşulu okunmaz", BAS, "                verdict = self._parameter_condition(c)",
     "                verdict = True", T),
    ("N13 boş ortak bölge okunmaz", BAS,
     "            if reg is not None and (reg is S.EmptySet or reg.is_empty is True):", "            if False:", T),
    ("N14 yan koşullar bölgeye girmez", BAS, "        if side:\n            sets, unapplied", "        if False:\n            sets, unapplied", T),
    ("N15 gcd(0, 0) tanımlı", DOM, '            if type(node).__name__ == "gcd":', "            if False:", T),
    ("N16 kapalı koşullar bağlamasız okunmaz", BAS,
     "        # closed conditions with no value too (`a = root(-8, 3)`: an odd root of a negative number)\n",
     "        # closed conditions with no value too (`a = root(-8, 3)`: an odd root of a negative number)\n"
     "        if not allb and not self.ir.vars[1:]:\n            return self._first_issue(found)\n", T),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
