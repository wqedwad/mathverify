"""Mutation check of V14 and of its adversarial audit (29 Sep 2026, DECISIONS §72): the parser's
integer gcd/lcm, the assumption-free (or integer) variable of a range binder, arccot in (0, pi), and
the paths the audit closed (numbers confirming SymPy's value of a closed integral/sum/product, closed
step claims, the exact confirmation of a random-point disagreement, the domain and definedness
checks). The machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is the one of
denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-29/v14/mutasyon_v14.py [-j N] [--list] [name ...]

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

P = "src/mathverify/normalize/parse.py"
RP = "src/mathverify/equiv/random_point.py"
NUM = "src/mathverify/equiv/numeric.py"
EQ = "src/mathverify/equiv/__init__.py"
FO = "src/mathverify/equiv/forms.py"
LIM = "src/mathverify/certify/limits.py"
DOM = "src/mathverify/certify/domain.py"
BASE = "src/mathverify/certify/base.py"
CAL = "src/mathverify/certify/calculus.py"
DET = "src/mathverify/steps/deterministic.py"
TC = "tests/test_parse_conventions.py"
TA = "tests/test_audit_2026_09_29_v14.py"

MUTATIONS = [
    # --- (G) gcd / lcm
    ("G01 gcd sembolde polinom gcd'si", P,
     "        if _number_args(cls, args):\n            out = args[0]\n            for a in args[1:]:\n                out = sp.gcd(out, a)",
     "        if True:\n            out = args[0]\n            for a in args[1:]:\n                out = sp.gcd(out, a)", TC),
    ("G02 lcm sembolde polinom lcm'i", P,
     "        if _number_args(cls, args):\n            out = args[0]\n            for a in args[1:]:\n                out = sp.lcm(out, a)",
     "        if True:\n            out = args[0]\n            for a in args[1:]:\n                out = sp.lcm(out, a)", TC),
    ("G03 üç argümanda ilk ikisi", P, "            for a in args[1:]:\n                out = sp.lcm(out, a)",
     "            for a in args[1:2]:\n                out = sp.lcm(out, a)", TC),
    ("G04 her gcd tam sayı", P, "    def _eval_is_integer(self):\n        return True if all(a.is_integer for a in self.args) else None",
     "    def _eval_is_integer(self):\n        return True", TC, 2),
    ("G05 gcd'nin sayısal değeri yok", P, "    _imp_ = _numeric_integer_op(math.gcd)\n", "", TA),
    ("G06 gcd pürüzsüz sayılır", RP, '            if isinstance(n, _NONSMOOTH) or type(n).__name__ in ("gcd", "lcm")]',
     "            if isinstance(n, _NONSMOOTH)]", TA),
    ("G07 liste biçimi açılmaz", P, "        if len(args) == 1 and isinstance(args[0], (list, tuple, sp.Tuple)):",
     "        if False:", TC),
    ("G08 LaTeX gcd polinom gcd'si", P,
     '    s = _LATEX_GCD.sub(lambda m: r"\\mathrm{%s}" % (m.group(1) or m.group(2)), _LATEX_ARCCOT.sub(r"\\\\arccot ", s))',
     '    s = _LATEX_ARCCOT.sub(r"\\\\arccot ", s)', TA),
    ("G10 gcd'nin tanım kuralı negatif almaz", DOM, '        if name in ("gcd", "lcm"):',
     '        if name in ("gcd", "lcm") and False:', TA),
    # --- (B) the variable of a range binder
    ("B01 compute sarmalayıcısı bağlayıcı değil", P, '        or getattr(obj, "binds_range", False) is True', "", TA),
    ("B02 sembol olmayan ad da yeniden adlandırılır", P,
     "                    and isinstance(local_dict.get(v), Symbol)):", "                    ):", TC),
    ("B03 bir bağlayıcıda iki kez bağlanabilir", P, "            if named.count(v) > 1:", "            if False:", TC),
    ("B04 iç içe aynı ad", P, "            if owner.get(id(sub), bi) != bi:", "            if False:", TC),
    ("B05 önceki sınırların uçları kapsam dışı", P,
     "        roots = [call.args[0]] + [e for inner in limits[:m] if isinstance(inner, (ast.Tuple, ast.List))\n",
     "        roots = [call.args[0]] + [e for inner in [] if isinstance(inner, (ast.Tuple, ast.List))\n", TC),
    ("B06 liste sınırı sınır değil", P,
     "            if not (isinstance(lim, (ast.Tuple, ast.List)) and len(lim.elts) == 3 and v is not None",
     "            if not (isinstance(lim, ast.Tuple) and len(lim.elts) == 3 and v is not None", TC),
    ("B07 tam sayı indis yok", P, "        if evaluate:\n            out = _integer_indices(out)",
     "        if evaluate:\n            pass", TA),
    ("B08 tam sayı olmayan sınırda da tam sayı indis", P,
     "            if all(b.is_integer or b in (sp.oo, -sp.oo) for b in lim[1:]):", "            if True:", TC),
    ("B09 ters aralık okunur", P, "                        and (lim[2] - lim[1] + 1).is_extended_negative is True:",
     "                        and False:", TC),
    ("B10 tam sayı olmayan aralık farkı okunur", P, "                        and span.is_finite and span.is_integer is False:",
     "                        and False:", TC),
    ("B11 yazıldığı-biçim okumada yeniden adlandırma", P,
     "transformations=_TRANSFORMS, evaluate=False, rebind=False))", "transformations=_TRANSFORMS, evaluate=False))", TA),
    # --- (A) arccot
    ("A01 arccot SymPy'nin acot'u", P, "    def eval(cls, x):\n        return pi / 2 - sp.atan(x)",
     "    def eval(cls, x):\n        return sp.acot(x)", TC),
    ("A02 LaTeX acot çevrilmez", P, "            return e.replace(sp.acot, arccot) if e.has(sp.acot) else e",
     "            return e", TA),
    ("A03 LaTeX dönüşümü ilişkiyi yeniden değerlendirir", P,
     "        expr = _on_sides(expr, lambda e: _integer_indices(convert(e)))",
     "        expr = _integer_indices(convert(expr))", TA),
    ("A04 LaTeX'te işlev adı sembol sayılır", P, "                         if not isinstance(ns.get(fs.name), Symbol)})",
     "                         if fs.name not in ns})", TA),
    ("A05 arccot yazıldığı biçimde toplam değil", DOM, '        if type(node).__name__ == "arccot":',
     '        if False:', TA),
    ("A06 LaTeX UnevaluatedExpr kalır", P,
     "            e = e.replace(lambda n: isinstance(n, sp.UnevaluatedExpr), lambda n: n.args[0])\n", "", TA),
    # --- (N) numbers confirm SymPy's value of a closed form
    ("N01 karşılaştırıcı biçimi denetlemez", EQ, "    if has_closed_form(claimed) or has_closed_form(truth):",
     "    if False:", TA),
    ("N02 sayısal onay aranmaz", FO, "                if ok is not True:", "                if False:", TA),
    ("N03 compute adımı biçimi denetlemez", DET,
     "        lhs, rhs = checked_forms(lhs, ctx.timeout), checked_forms(rhs, ctx.timeout)", "        pass", TA),
    ("N04 _decide biçimi denetlemez", DET, "        a, b = checked_forms(a, ctx.timeout), checked_forms(b, ctx.timeout)",
     "        pass", TA),
    ("N05 to_mp biçimi sayısal değerlendirir", NUM,
     '            raise ValueError("an unevaluated integral, sum or product has no confirmed value")',
     "            expr = expr.doit()", TA),
    # --- (S) steps
    ("S01 kapalı iddia öncül yolundan", DET,
     '        return _closed_claim(claim, ctx), {"n_premises": len(premises), "route": "closed_claim"}',
     "        pass", TA),
    ("S02 kapalı Limit iddiası karara bağlanır", DET, "    if isinstance(claim, sp.Basic) and claim.has(sp.Limit):",
     "    if False:", TA),
    ("S03 biçimli iddiada sayısal yedek", DET,
     "        if not isinstance(claim, sp.Basic) or not claim.has(sp.Integral, sp.Sum, sp.Product, sp.Derivative):",
     "        if True:", TA),
    ("S05 integral değeri reddetmez", DET, "        elif _integrals_refute(claim, ctx):", "        elif False:", TA),
    ("S06 compute adımında integral değeri reddetmez", DET,
     "        if _integrals_refute(claim, ctx):\n            return \"refuted\"", "        if False:\n            return \"refuted\"", TA),
    ("S04 kapalı eşitsizlik adımı atlanır", DET, "            status = _closed_claim(claim, ctx)\n",
     '            status = "unknown"\n', TA),
    # --- (R) random points, signs, limits
    ("R01 sayısal fark kesin denetimsiz karşı örnek", RP,
     "            c = _exact_counterexample(a, b, syms, pt)\n            if isinstance(c, dict):\n                ev[\"evaluated\"] += 1",
     "            c = {\"point\": {}, \"exact\": \"numeric\"}\n            if isinstance(c, dict):\n                ev[\"evaluated\"] += 1", TA),
    ("R02 doğrulanmamış fark eşitliği engellemez", RP,
     '    if unconfirmed:\n        ev["reason"] = "disagreement_not_confirmed_exactly"\n        return None, ev\n', "", TA),
    ("R03 sonsuz Range listelenir", RP, "        if dom.is_finite_set:\n", "        if True:\n", TA),
    ("R04 değerlendirilemeyen kalıntı işaret taşır", NUM, '    if not getattr(f, "is_Number", False):', "    if False:", TA),
    ("R05 limitte boş sonda karar verir", LIM, "        if all(x_ is None for x_ in vals):", "        if False:", TA),
    # --- (D) domains and definedness
    ("D01 solveset'in kümesi denetlenmez", DOM, "        if _solveset_contradicted(cond, var, r.value):",
     "        if False:", TA),
    ("D02 kanıtlanmamış kapalı koşul tanımlı", BASE,
     "        return any(isinstance(c, sp.core.relational.Relational) and not c.free_symbols and not proved(c)",
     "        return any(False and not proved(c)", TA),
    ("D03 toplamın terimleri denetlenmez", BASE, "        if any(c is sp.false for c in conds) or self._undefined_term(e):",
     "        if any(c is sp.false for c in conds):", TA),
    ("D04 belirli integral bildirilmiş değişkenle", CAL, "            var = sp.Symbol(var.name, real=True)\n",
     "            var = ctx.sym(var.name)\n", TA),
    # --- (C) claims
    ("C01 alt indisli LaTeX bağlayıcısı değer", P,
     '_LATEX_COMPUTING = re.compile(r"\\\\(?:int|iint|oint|lim|sum|prod)(?![A-Za-z])|',
     '_LATEX_COMPUTING = re.compile(r"\\\\(?:int|iint|oint|lim|sum|prod)\\b|', TA),
    ("C02 küme öğeleri denetlenmez", P, "    if isinstance(text, (list, tuple)):\n        for t in text:",
     "    if False:\n        for t in text:", TA),
    ("C03 LaTeX ilişki hatası sızar", P,
     "        except ParseError:\n            raise\n        except Exception as e:  # noqa: BLE001 - latex2sympy raises a bare Exception",
     "        except ParseError:\n            raise\n        except ZeroDivisionError as e:  # noqa: BLE001 - latex2sympy raises a bare Exception", TA),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
