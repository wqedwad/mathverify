"""Mutation check of part d4f of the fourth audit's fixes (6 Oct 2026): each mutation removes one guard of
definedness (`certify.domain` rules, NO_VALUE, the range of a Sum/Product, `_violations`; `certify.base`
written_conditions; the verifier's intake and claim check; `normalize.parse` range refusals and the LaTeX tree
check; `certify.limits.holds_on_the_tail`; the fusion's blocking flag). The machinery (throwaway clones of the
committed HEAD, exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the list of mutations
is new. Round 2 (the review of d4f, 7 Oct 2026) adds N01-N29.

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
    ("M09 köşeli metin yürünmez", DOM,
     "        if isinstance(n, (list, tuple)) or (isinstance(n, sp.MatrixBase) and not isinstance(n, sp.Basic)):",
     "        if False:", T),
    ("M10 toplam terimi NO_VALUE taşımaz", DOM,
     "    return [sp.false] + ([NO_VALUE] if any(is_no_value(c) for c in term_conds) else [])", "    return [sp.false]", T),
    # --- TAN-10: the bounds are integers
    ("M11 kesin tam sayı olmayan sınır kabul", DOM, "    if False in whole:\n        return None\n", "", T),
    ("M12 açık sınır tam sayıya bağlanmaz", DOM,
     "        b = next((b for b in finite if isinstance(b, sp.Symbol)), finite[0])\n        conds.append(sp.Contains(b, INTEGER_BOUND))\n",
     "        pass\n", T),
    ("M13 sabit sınır tam sayı denetimi yok", PAR,
     "        if any(_not_an_integer(b) for b in (lo, hi)):\n            raise", "        if False:\n            raise", T),
    ("M14 literal sınır tam sayı denetimi yok", PAR, "                if lo.denominator != 1 or hi.denominator != 1:",
     "                if False:", T),
    ("M15 ağaçta aralık denetimi yok", PAR,
     "                        _refuse_constant_range(type(node).__name__, lo, hi, raw)\n                    except ParseError:",
     "                        pass\n                    except ParseError:", T),
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
     "        if not tree_free_symbols(e) and",
     "        conds = definedness_conditions(e, None)\n        if not tree_free_symbols(e) and", T),
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
     "        conds = [c for c in conds if not is_convention(c)]",
     "        conds = list(conds)", T),
    # --- G14: the tail of a sequence
    ("M30 kuyruk okunmaz", LIM, "                   if not holds_on_the_tail(c, var, point)\n",
     "                   if True\n", T),
    ("M31 kuyruk sınırsız da kabul", LIM, '    return getattr(end, "is_finite", None) is True', "    return True", T),
    ("M32 gerçel değişkende kuyruk", LIM, '    if point not in (oo, -oo) or not getattr(var, "is_integer", None):',
     "    if point not in (oo, -oo):", T),
    ("M33 kaydırılmış üyelik işaret sorusu değil", DOM,
     "        if s in (S.Naturals0, S.Naturals, S.Integers) and region.is_subset(S.Integers) is True \\\n"
     "                and _integer_valued(e, d):", "        if False:", T),
    ("M35 küme metni parçalara bölünmez", PAR,
     "    read = [parse_as_written(p, wns) for p in pieces]\n", "    read = [sp.Tuple() for p in pieces]\n", T),
    ("M36 küme kurucuları tutulmaz", PAR, "    wns = dict(ns, **_WRITTEN_SETS)", "    wns = dict(ns)", T),
    ("M34 tam sayı katsayısı sorulmaz", DOM,
     "        return all(a.is_integer is True for a in sp.Poly(e, d).all_coeffs())", "        return True", T),
    # --- round 2 (review of d4f): YO-1 the as-written reading fails closed
    ("N01 adımda okunamayan metin tanımlı", "src/mathverify/steps/deterministic.py",
     "        if w is None:\n            return unread", "        if w is None:\n            return False", T),
    ("N02 verilende okunamayan metin koşulsuz", BAS,
     "            except Exception:  # noqa: BLE001 - not this reading\n                continue\n            return \"undecided\"",
     "            except Exception:  # noqa: BLE001 - not this reading\n                continue\n            return None", T),
    ("N03 iddiada okunamayan metin koşulsuz", VER,
     "        out += unread\n", "        pass\n", T),
    ("N04 sabit sınır değerlenmez", PAR, "        v = _evaluated_bound(v)\n", "", T),
    ("N05 ağaçtaki sınır değerlenmez", PAR,
     "                        lo, hi = _evaluated_bound(lim[1]), _evaluated_bound(lim[2])", "                        lo, hi = lim[1], lim[2]", T),
    ("N06 yeniden yazma işlemleri okunmaz", PAR,
     '                         for name in ("simplify", "expand", "factor", "cancel", "together", "apart")}}',
     '                         for name in ()}}', T),
    # --- YO-2: no matrix operation computed as written
    ("N07 matris işlemi yazılı okumada hesaplanır", PAR,
     '                      **{name: (_SAFE_NAMES[name], _held_matrix_op(name))\n'
     '                         for name in ("det", "trace", "rank", "eigmax", "eigmin")},\n',
     "", T),
    ("N08 sembollü girdide det hesaplanır", PAR,
     "                and all(_rational_as_written(x) for x in entries):", "                and True:", T),
    ("N09 LaTeX det hesaplanır", PAR, "                if not global_parameters.evaluate and comp.det():",
     "                if False:", T),
    # --- YO-3, RK-F1: the integer bound is a convention
    ("N10 açık sınır sert Z koşulu", DOM,
     "        conds.append(sp.Contains(b, INTEGER_BOUND))", "        conds.append(sp.Contains(b, S.Integers))", T),
    ("N11 tam sayı sınır bölgesinde CORRECT", "src/mathverify/certify/algebra.py",
     "    if bounds and ok is True:", "    if False:", T),
    ("N12 iddianın kendi tam sayı olmayan sınırı verified", "src/mathverify/steps/deterministic.py",
     '    if own:\n        return "unknown", {**ev, "reason": "not_verified_where_a_bound_is_not_an_integer"}',
     '    if False:\n        return "unknown", {**ev, "reason": "not_verified_where_a_bound_is_not_an_integer"}', T),
    ("N13 tam sayı sınırı ayrılmaz", DOM,
     "            fwd = S.Integers if abs(a) == 1 and b.is_integer else sp.imageset(sp.Lambda(t, (t - b) / a), S.Integers)\n"
     "            back = sp.Complement(S.Reals, fwd)\n",
     "            return S.Reals, S.Reals\n", T),
    # --- YO-4: the tail of a sequence holds every condition
    ("N14 dizi kuyruğunda Ne koşulu sorulmaz", LIM,
     '        if point in (oo, -oo) and getattr(var, "is_integer", None):\n            # a sequence:',
     '        if False:\n            # a sequence:', T),
    # --- YO-5: the claim at its pins, as written, with its option
    ("N15 iddia pinsiz okunur", VER, "    return definedness_conditions(_pinned_tree(w, _claim_pins(ctx)), None)",
     "    return definedness_conditions(w, None)", T),
    ("N16 iddia normalize edilmiş okunur", VER, "    payload = ca.payload if raw_payload is None else raw_payload",
     "    payload = ca.payload", T),
    ("N17 şık metni okunmaz", VER, "        return [options[ca.option]]", "        return []", T),
    # --- YO-6: every problem text
    ("N18 liste parametreleri okunmaz", BAS,
     '        others = [t for k, v in params.items() if k != "var" for t in _texts(v)]',
     '        others = [v for k, v in params.items() if k != "var" and isinstance(v, str)]', T),
    ("N19 üyelik verileninde küme okunmaz", PAR,
     "        return parse_set_as_written(member.group(2), ns)", "        return sp.Tuple()", T),
    ("N20 dizi terimi fonksiyon değil", "src/mathverify/steps/deterministic.py",
     "            out[n] = sp.Function(n) if called else sp.Symbol(n)", "            out[n] = sp.Symbol(n)", T),
    # --- YO-7: ∞⁰
    ("N21 ∞⁰ gelenek değil", DOM, "            ok = other.is_zero is False and other.is_infinite is False",
     "            ok = other.is_zero is False", T),
    # --- RK-F2: Γ's open condition where it is proved
    ("N22 Γ koşulu limitte kanıtlanmaz", LIM,
     "                   and not membership_holds_on(c, var, approach_regions(point, side))]", "                   ]", T),
    ("N23 Γ koşulu her bölgede kabul", LIM,
     "            if all(sp.Intersection(img, hole).is_empty is True for img in images):", "            if True:", T),
    ("N24 Γ koşulu integral/türevde kanıtlanmaz", "src/mathverify/certify/calculus.py",
     "    members = [c for c in membership_conditions(src, expr, var, ns) if not membership_holds_on(c, var, regions)]",
     "    members = membership_conditions(src, expr, var, ns)", T),
    # --- RK-F3, RK-F4
    ("N25 ℂ'de esas değer yok", VER,
     "        if complex_dod:\n            if any(is_no_value(c) for c in conds):\n                out.append(txt)\n            continue\n",
     "", T),
    ("N26 LaTeX sıfıra bölme zoo kalır", PAR,
     "    if not global_parameters.evaluate and (out is S.ComplexInfinity or out is S.NaN):",
     "    if False:", T),
    ("N27 bileşik metin bölünmez", PAR, "    parts = _COMPOUND_RE.split(s2)\n", "    parts = [s2]\n", T),
    ("N28 LaTeX zinciri okunmaz", PAR, "        sides = _latex_chain_sides(s)\n", "        sides = [s]\n", T),
    ("N29 dne metni değer sayılır", VER, '    if ca.kind in ("dne", "none"):\n        return []', "    if False:\n        return []", T),
    ("N30 kapalı tam sayı sınırı okunmaz", DOM,
     "        if c is sp.false or (not c.free_symbols and not is_integer_bound(c)):",
     "        if c is sp.false or not c.free_symbols:", T),
    ("N31 okunamayan adım çürütülür", "src/mathverify/steps/deterministic.py",
     "        w = parse_set_as_written(text, ns)\n        if w is None:\n            return True\n        return any(",
     "        w = parse_set_as_written(text, ns)\n        if w is None:\n            return False\n        return any(", T),
    ("N32 LaTeX matris fonksiyonu hesaplanır", PAR,
     "                held = self._held_matrix_func(func) if not global_parameters.evaluate else None",
     "                held = None", T),
    ("N33 LaTeX matrisi okunmaz", PAR, "        if isinstance(e, sp.MatrixBase):\n            # a matrix",
     "        if False:\n            # a matrix", T),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
