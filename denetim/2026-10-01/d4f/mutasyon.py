"""Mutation check of part d4f of the fourth audit's fixes (6 Oct 2026): each mutation removes one guard of
definedness (`certify.domain` rules, NO_VALUE, the range of a Sum/Product, `_violations`; `certify.base`
written_conditions; the verifier's intake and claim check; `normalize.parse` range refusals and the LaTeX tree
check; `certify.limits.holds_on_the_tail`; the fusion's blocking flag). The machinery (throwaway clones of the
committed HEAD, exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the list of mutations
is new.

    .venv/bin/python denetim/2026-10-01/d4f/mutasyon.py [-j N] [--list] [name ...]

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
LIM = "src/mathverify/certify/limits.py"
VER = "src/mathverify/verifier.py"
FUS = "src/mathverify/fuse/rules.py"
T = "tests/test_d4_d4f_tanimlilik.py"

MUTATIONS = [
    # --- CAP-F1: the rules fail closed, NO_VALUE
    ("M01 kural istisnası yükselir", DOM,
     "            except Exception:  # noqa: BLE001 - see above\n                add(DEFINEDNESS_UNDECIDED)",
     "            except Exception:  # noqa: BLE001 - see above\n                raise", T),
    ("M02 yürüyüş istisnası koşulsuz", DOM,
     "    except Exception:  # noqa: BLE001 - the walk itself failed: nothing is proved\n        add(DEFINEDNESS_UNDECIDED)",
     "    except Exception:  # noqa: BLE001 - the walk itself failed: nothing is proved\n        pass", T),
    ("M03 kutup NO_VALUE değil", DOM, "    if c is sp.false:\n        add(NO_VALUE)", "    if False:\n        add(NO_VALUE)", T),
    ("M04 zoo/nan okunmaz", DOM, "    if node is S.ComplexInfinity or node is S.NaN:", "    if False:", T),
    ("M05 Γ kuralı yok", DOM, "    elif isinstance(node, sp.gamma):", "    elif False:", T),
    ("M06 n!! ve !n faktöriyel değil", DOM, "    elif isinstance(node, (sp.factorial, sp.factorial2, sp.subfactorial)):",
     "    elif isinstance(node, sp.factorial):", T),
    ("M07 yükselen/düşen faktöriyel kuralı yok", DOM, "    elif isinstance(node, (sp.RisingFactorial, sp.FallingFactorial)):",
     "    elif False:", T),
    ("M08 binom kutbu hesaplanmaz", DOM, "        if not node.free_symbols and not all(c is sp.true for c in conds):",
     "        if False:", T),
    ("M09 köşeli metin yürünmez", DOM, "        if isinstance(n, (list, tuple)):\n", "        if False:\n", T),
    ("M10 toplam terimi NO_VALUE taşımaz", DOM,
     "    return [sp.false] + ([NO_VALUE] if any(is_no_value(c) for c in term_conds) else [])", "    return [sp.false]", T),
    # --- TAN-10: the bounds are integers
    ("M11 kesin tam sayı olmayan sınır kabul", DOM, "    if False in whole:\n        return None\n", "", T),
    ("M12 açık sınır tam sayıya bağlanmaz", DOM,
     "        b = next((b for b in finite if isinstance(b, sp.Symbol)), finite[0])\n        conds.append(sp.Contains(b, S.Integers))\n",
     "        pass\n", T),
    ("M13 sabit sınır tam sayı denetimi yok", PAR,
     "        if any(_not_an_integer(b) for b in (lo, hi)):\n            raise", "        if False:\n            raise", T),
    ("M14 literal sınır tam sayı denetimi yok", PAR, "                if lo.denominator != 1 or hi.denominator != 1:",
     "                if False:", T),
    ("M15 ağaçta sınır tam sayı denetimi yok", PAR, "                        and any(_not_an_integer(b) for b in lim[1:]):",
     "                        and False:", T),
    # --- B1: the LaTeX range on the tree
    ("M16 LaTeX ağacında aralık denetlenmez", PAR,
     '            _refuse_constant_range("sum or product", _evaluated_bound(lim[1]), _evaluated_bound(lim[2]), s)',
     "            pass", T),
    ("M17 LaTeX sınırı işlem olabilir", PAR,
     "            if any(isinstance(b, sp.Basic) and b.has(*_OPERATIONS) for b in lim[1:]):", "            if False:", T),
    ("M18 aralık denetimi değerlemesiz", PAR,
     "    with sp.evaluate(True):\n        if (hi - lo + 1).is_extended_negative is True:",
     "    if True:\n        if (hi - lo + 1).is_extended_negative is True:", T),
    # --- the problem's texts: undefined / undecided, at the given values
    ("M19 NO_VALUE açık metinde tanımsız değil", BAS,
     '        conds = definedness_conditions(e, None)\n        if any(is_no_value(c) for c in conds):\n            return "undefined"\n'
     "        if not e.free_symbols and",
     "        conds = definedness_conditions(e, None)\n        if not e.free_symbols and", T),
    ("M20 tanımlılık verilensiz okunur", BAS, "            note(s_, self._undefined_constant(s_, pins))",
     "            note(s_, self._undefined_constant(s_))", T),
    ("M21 kararsız tanımsız sayılır", BAS,
     '        # expression with a variable (x + tan(...) - tan(...) = 1) the condition was dropped too.\n'
     '        return "undecided" if closed_condition_undecided(conds) else None',
     '        # expression with a variable (x + tan(...) - tan(...) = 1) the condition was dropped too.\n'
     '        return "undefined" if closed_condition_undecided(conds) else None', T),
    ("M22 öteki metinler okunmaz", BAS, "                note(t, self._text_without_value(t, pins))", "                pass", T),
    ("M23 kapalı öteki metin tanımsız değil", BAS,
     '        if any(c is sp.false for c in conds):\n            return "undefined"\n        return "undecided"',
     '        return "undecided"', T),
    ("M24 görev ifadesinde false sayılmaz", BAS,
     "        if any(c is sp.false for c in conds) or self._undefined_term(e) \\\n",
     "        if self._undefined_term(e) \\\n", T),
    ("M25 kararsız alım kapısı yok", VER, "    if undecided:\n", "    if False:\n", T),
    ("M26 kararsız bayrağı engellemez", FUS, '                         "problem_definedness_undecided",\n', "", T),
    # --- the claim
    ("M27 değersiz iddia denetlenmez", VER, "    if no_value:\n", "    if False:\n", T),
    ("M28 iddiada false sayılmaz", VER, "        if sp.false in conds or closed_condition_undecided(conds):",
     "        if closed_condition_undecided(conds):", T),
    ("M29 iddiada gelenek koşulu süzülmez", VER,
     "        conds = [c for c in definedness_conditions(w, None) if not is_convention(c)]",
     "        conds = list(definedness_conditions(w, None))", T),
    # --- G14: the tail of a sequence
    ("M30 kuyruk okunmaz", LIM, "                   if not holds_on_the_tail(c, var, point)]", "                   if True]", T),
    ("M31 kuyruk sınırsız da kabul", LIM, '    return getattr(end, "is_finite", None) is True', "    return True", T),
    ("M32 gerçel değişkende kuyruk", LIM, '    if point not in (oo, -oo) or not getattr(var, "is_integer", None):',
     "    if point not in (oo, -oo):", T),
    ("M33 kaydırılmış üyelik işaret sorusu değil", DOM,
     "        if s in (S.Naturals0, S.Naturals, S.Integers) and region.is_subset(S.Integers) is True \\\n"
     "                and _integer_valued(e, d):", "        if False:", T),
    ("M35 küme metni parçalara bölünmez", PAR,
     "    read = [w for w in (parse_as_written(p, wns) for p in pieces if p.strip()) if w is not None]",
     "    read = []", T),
    ("M36 küme kurucuları tutulmaz", PAR, "    wns = dict(ns, **_WRITTEN_SETS)", "    wns = dict(ns)", T),
    ("M34 tam sayı katsayısı sorulmaz", DOM,
     "        return all(a.is_integer is True for a in sp.Poly(e, d).all_coeffs())", "        return True", T),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
