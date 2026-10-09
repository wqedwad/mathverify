"""Mutation check of part d4h of the fourth audit's fixes (7 Oct 2026): each mutation removes one guard of the
parser's fixes (`normalize.parse`: rewrites and deciding helpers over forms, matrices and containers, LaTeX set
membership and Leibniz notation, domain lists, the gcd/lcm record; `equiv.forms` on containers; the verifier's
claim checks; `certify.trig` two-parameter families). The machinery (exit codes, clean-up) is the one of
denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

Round 2 (8 Oct 2026, the attack on round 1): R01-R97 remove the new guards (no evalf of a closed form while a text
is read, Leibniz fractions in any typography, rewrites by keyword, domain lists on any argument and in two readings,
the family names a problem uses, memberships in the line, the task's relation as a premise, conditions as notation,
SymPy's registry S, the structure of the target). The copies are clones of the committed HEAD; `--calisma-agaci`
copies the working tree instead (round 1: its commit was refused in its session).

    .venv/bin/python denetim/2026-10-01/d4h/mutasyon.py [-j N] [--list] [name ...]

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mutasyon_0926", HERE.parents[1] / "2026-09-26" / "mutasyon.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

PAR = "src/mathverify/normalize/parse.py"
FRM = "src/mathverify/equiv/forms.py"
VER = "src/mathverify/verifier.py"
TRG = "src/mathverify/certify/trig.py"
STP = "src/mathverify/steps/deterministic.py"
T = "tests/test_d4_d4h_ayristirici.py"
T2 = "tests/test_d4_d4h_tur2.py"

MUTATIONS = [
    # --- F1: rewrites and deciding helpers over a form
    ("D01 yeniden yazım formu hesaplar", PAR,
     "        if contains_form(list(args) + list(kwargs.values())):\n            return _rewritten_argument(",
     "        if False:\n            return _rewritten_argument(", T),
    ("D02 karar veren yardımcı evalf ile karar verir", PAR,
     "        if has_closed_form_node(list(args)):\n            with sp.evaluate(False):\n                return cls(*args, **kwargs)",
     "        if False:\n            with sp.evaluate(False):\n                return cls(*args, **kwargs)", T),
    ("D04 formlu matriste rank/eigmax okunur", PAR, "        if contains_form(mat):", "        if False:", T),
    ("D05 gerçelliği belirsiz özdeğer düşer", PAR, "        if any(r is None for r in real):", "        if False:", T),
    ("D06 çıplak ad SymPy sınıfı değil", PAR, "    def _sympy_(self):\n        return self._base",
     "    def _sympy_unused(self):\n        return self._base", T),
    ("D07 karar veren yeniden kurulurken değerlendirilir", PAR,
     "    if isinstance(e, _DECIDING) and has_closed_form_node(args):\n        with sp.evaluate(False):\n            return e.func(*args)",
     "    if False:\n        with sp.evaluate(False):\n            return e.func(*args)", T),
    ("D08 substitute_free karar vereni değerlendirir", PAR,
     "        return rebuilt(e, args) if any(a is not b for a, b in zip(args, e.args)) else e",
     "        return e.func(*args) if any(a is not b for a, b in zip(args, e.args)) else e", T),
    ("D40 hold_parametric karar vereni değerlendirir", PAR,
     "        if any(a is not b for a, b in zip(args, e.args)):\n            e = rebuilt(e, args)\n        if isinstance(e, (sp.Integral",
     "        if any(a is not b for a, b in zip(args, e.args)):\n            e = e.func(*args)\n        if isinstance(e, (sp.Integral", T),
    ("D41 tam sayı indisi karar vereni değerlendirir", PAR, "            e = rebuilt(e, args)\n        return upgrade(e)",
     "            e = e.func(*args)\n        return upgrade(e)", T),
    # --- H1: containers
    ("D09 _hold_value kapsayıcıya girmez", PAR,
     "        return map_entries(out, lambda e: _hold_value(e, pins, protected))", "        return out", T),
    ("D10 hold_parametric kapsayıcıya girmez", PAR,
     "        return map_entries(expr, lambda e: hold_parametric(e, pins, protected))", "        return expr", T),
    ("D11 entries liste/demete girmez", PAR,
     "    if isinstance(obj, (list, tuple)):\n        return [y for x in obj for y in entries(x)]",
     "    if False:\n        return [y for x in obj for y in entries(x)]", T),
    ("D12 map_entries matrise girmez", PAR, "    if isinstance(obj, sp.MatrixBase):\n        return obj.applyfunc(f)",
     "    if False:\n        return obj.applyfunc(f)", T),
    ("D13 has_closed_form kapsayıcıya girmez", FRM,
     "    return any(_closed(n) for x in entries(e) for n in sp.preorder_traversal(x))",
     "    return isinstance(e, sp.Basic) and any(_closed(n) for n in sp.preorder_traversal(e))", T),
    ("D14 checked_forms kapsayıcıya girmez", FRM, "        return map_entries(e, lambda x: checked_forms(x, timeout))",
     "        return e", T),
    ("D15 has_parametric_form kapsayıcıya girmez", FRM,
     "               for x in entries(e) for n in sp.preorder_traversal(x))",
     "               for x in ([e] if isinstance(e, sp.Basic) else []) for n in sp.preorder_traversal(x))", T),
    # --- D1: LaTeX membership
    ("D16 LaTeX üyeliği eşitlik kalır", PAR, "        expr = _latex_membership(expr)\n", "", T),
    ("D17 LaTeX notin okunmaz", PAR,
     "    expr = expr.replace(lambda n: isinstance(n, Not) and member(n.args[0]), lambda n: condition(n.args[0], True))\n",
     "", T),
    ("D18 notin {c} eşitsizlik değil", PAR,
     "        if negated and isinstance(st, FiniteSet):\n            return And(*[Ne(el, a) for a in st.args])",
     "        if False:\n            return And(*[Ne(el, a) for a in st.args])", T),
    ("D19 sonsuz uç koşul olur", PAR, "    if st.start != -oo:\n        out.append", "    if True:\n        out.append", T),
    # --- D2: domain lists
    ("D20 küme listesi kesişim okunur", PAR, "    if _set_listed(read):", "    if False:", T2),
    ("D21 küme + dışlama okunmaz", PAR,
     "            if j != i and names & onames and other != key and not (other is None and excludes):",
     "            if j != i and names & onames and other != key:", T),
    ("D22 aynı küme iki kez okunmaz", PAR,
     "            if j != i and names & onames and other != key and not (other is None and excludes):",
     "            if j != i and names & onames and not (other is None and excludes):", T),
    # --- I2: Leibniz notation
    ("D24 Leibniz çarpımı okunur", PAR, "    _refuse_leibniz_products(s, ns, expr)\n", "", T),
    ("D25 her Leibniz kesri reddedilir", PAR,
     "        if names and any(isinstance(ns.get(n), Symbol) for n in names):", "        if names:", T),
    # --- CAP-G1: the gcd/lcm record and the LaTeX restatement
    ("D27 gcd/lcm kaydı yok", PAR, "        _record_integer_op(cls.__name__, args)\n", "", T),
    ("D28 igcd/ilcm kaydı yok", PAR, "        _record_integer_op(name, args)\n", "", T),
    ("D29 LaTeX gcd kayıtsız sınıf", PAR, 'ops = {"gcd": _GCD_CALL, "lcm": _LCM_CALL}', 'ops = {"gcd": gcd, "lcm": lcm}', T),
    ("D30 sembollü gcd de kaydedilir", PAR,
     '    if rec is not None and args and not any(getattr(a, "free_symbols", None) for a in args):',
     "    if rec is not None and args:", T),
    ("D31 kayıt karara bağlanmaz", VER, "    if computed:\n        return unknown(", "    if False:\n        return unknown(", T),
    ("D32 LaTeX yeniden yazımı değerlendirilir", VER, "    if not is_latex(t):\n        # strict:",
     "    if True:\n        # strict:", T),
    ("D33 LaTeX binom eylemsiz değil", VER,
     "        return e.replace(lambda n: isinstance(n, sp.Function) and type(n).__name__ in _INERT,",
     "        return e.replace(lambda n: False,", T),
    # --- G11: two family parameters
    ("D34 iki parametre ilkine indirgenir", TRG, "        if len(ints) > 1:", "        if False:", T),
    ("D35 kafes gcd'si alınmaz", TRG,
     "    g = sp.Rational(sp.gcd_list([r.p for r in ratios]), sp.lcm_list([r.q for r in ratios]))",
     "    g = sp.Integer(1)", T),
    ("D36 oranın rasyonelliği denetlenmez", TRG,
     "    if not all(isinstance(r, sp.Rational) for r in ratios):\n        return None\n", "", T),
    ("D37 katsayıda parametre denetlenmez", TRG, "    if any(c.free_symbols & set(ints) for c in coeffs):\n        return None\n",
     "", T),
    ("D38 sabit öğe aile sayılır", TRG, "    if not nonzero:\n        return c0, None\n", "", T),
    ("D39 indirgenemeyen öğe çekimser değil", TRG, "        if claimed_g is None:\n            return unknown(",
     "        if False:\n            return unknown(", T),
    # ================= round 2
    # --- YO-1: no evalf of a closed form while a text is read
    ("R01 okuma sırasında evalf tutulmaz", PAR, "            if _FORMS_HELD.get():\n                raise NotImplementedError(",
     "            if False:\n                raise NotImplementedError(", T2),
    ("R02 bağlam açılmaz", PAR, "        token = _FORMS_HELD.set(True)", "        token = _FORMS_HELD.set(False)", T2),
    ("R03 kanonik ayrıştırma tutmaz", PAR, "@_holds_forms\ndef guarded_parse_expr(", "def guarded_parse_expr(", T2),
    ("R04 LaTeX ayrıştırma tutmaz", PAR, "@_holds_forms\ndef _latex_to_sympy(", "def _latex_to_sympy(", T2),
    ("R05 ilişki kurulumu tutmaz", PAR, "@_holds_forms\ndef parse_relation(", "def parse_relation(", T2),
    ("R06 küme kurulumu tutmaz", PAR, "@_holds_forms\ndef parse_set_str(", "def parse_set_str(", T2),
    ("R07 tanım evreni kurulumu tutmaz", PAR, "@_holds_forms\ndef parse_domain(", "def parse_domain(", T2),
    # --- YO-2: Leibniz fractions in any typography
    ("R10 adların hepsi bildirilmeli", PAR, "        if names and any(isinstance(ns.get(n), Symbol) for n in names):",
     "        if names and all(isinstance(ns.get(n), Symbol) for n in names):", T2),
    ("R11 yazım gürültüsü soyulmaz", PAR, '    return _LATEX_LEIBNIZ_NOISE.sub("", _LATEX_UPRIGHT_D.sub("d", t))',
     '    return re.sub(r"\\s+", "", _LATEX_UPRIGHT_D.sub("d", t))', T2),
    ("R12 dik d okunmaz", PAR, '    return _LATEX_LEIBNIZ_NOISE.sub("", _LATEX_UPRIGHT_D.sub("d", t))',
     '    return _LATEX_LEIBNIZ_NOISE.sub("", t)', T2),
    ("R13 ağaçta bölüm denetimi yok", PAR, "    names = _quotient_d_names(expr, ns)\n", "    names = set()\n", T2),
    ("R14 dfrac/tfrac eşleşmez", PAR, '_LATEX_FRAC = re.compile(r"\\\\[dtc]?frac(?![A-Za-z])")',
     '_LATEX_FRAC = re.compile(r"\\\\frac(?![A-Za-z])")', T2),
    ("R15 paydanın dv adı alınmaz", PAR, '    names = {"d"} | {"d" + v for v in _LEIBNIZ_DEN_PART.findall(den)}',
     '    names = {"d"}', T2),
    # --- YO-3: rewrites by keyword
    ("R20 anahtar kelime denetlenmez", PAR, "        if contains_form(list(args) + list(kwargs.values())):",
     "        if contains_form(list(args)):", T2),
    ("R21 birden çok anahtar kelime kabul", PAR, "    if len(exprs) != 1:\n        raise ParseError(",
     "    if not exprs:\n        raise ParseError(", T2),
    ("R22 yazılı okuma anahtar kelimeyi almaz", PAR, '    return _rewritten_argument("rewrite", args, kwargs)',
     "    return args[0]", T2),
    # --- YO-4 / RK-2: domain lists
    ("R30 argüman başına boşluk denetimi yok", PAR, "            if on_v:\n                _refuse_empty_list(on_v, v, spec)",
     "            if False:\n                _refuse_empty_list(on_v, v, spec)", T2),
    ("R31 yalnız ilk argüman", PAR, "        for v in argsyms:\n            on_v =", "        for v in argsyms[:1]:\n            on_v =", T2),
    ("R32 belirsiz liste kesişim okunur", PAR, "        if which is None:\n            raise DomainListAmbiguous(",
     "        if False:\n            raise DomainListAmbiguous(", T2),
    ("R33 birleşim okuması yok", PAR, '        if which == "union":\n            conds = _union_reading(',
     '        if False:\n            conds = _union_reading(', T2),
    ("R34 iki okuma ayrışsa da karar", VER, '    if verdicts["union"] == verdicts["intersection"]:', "    if True:", T2),
    ("R35 birleşim birden çok argümanda", PAR, "    if len(names) != 1:\n        raise ParseError(",
     "    if False:\n        raise ParseError(", T2),
    ("R36 birleşim aralığa inmese de okunur", PAR, "    if st.is_empty is not False or not isinstance(hull, Interval) or not (",
     "    if False and (", T2),
    # --- YO-5: family names a problem uses
    ("R40 problem adı aile indisi okunur", TRG, "            if taken:\n                return unknown(",
     "            if False:\n                return unknown(", T2),
    ("R41 kısıtlar okunmaz", TRG, "    for src in list(ir.givens) + [c for v in ir.vars for c in v.constraints]:",
     "    for src in list(ir.givens):", T2),
    ("R42 okunamayan verilenin adları alınmaz", TRG, '            names |= set(re.findall(r"[A-Za-z_]\\w*", str(src)))',
     "            pass", T2),
    # --- RK-1: membership in the line
    ("R50 x ∈ ℝ ilişkiye çöker", PAR, "        if S.Reals.is_subset(st) is True:", "        if False:", T2),
    ("R51 yeniden bağlama üyeliği katlar", PAR, "    if isinstance(expr, sp.Contains):\n        # a membership too",
     "    if False:\n        # a membership too", T2),
    ("R52 tanım kümesinde x ∈ ℝ kısıt sayılır", PAR,
     "    return rel.replace(lambda n: isinstance(n, sp.Contains) and n.args[0] in argsyms",
     "    return rel\n    return rel.replace(lambda n: isinstance(n, sp.Contains) and n.args[0] in argsyms", T2),
    ("R53 yazılı okumada LaTeX üyeliği yok", PAR, "        m = _LATEX_MEMBER_RE.match(strip_presentation(_strip_invisible(s)))",
     "        m = None", T2),
    ("R54 yazılı okumada küme işlemi bölünmez", PAR, "        if len(cup) > 1:", "        if False:", T2),
    ("R55 yazılı okumada koşul kenarları yok", PAR,
     "        if isinstance(e, sp.logic.boolalg.Boolean):\n            # a condition", "        if False:\n            # a condition", T),
    ("R56 yazılı okumada $ soyulmaz", PAR, "        m = _LATEX_MEMBER_RE.match(strip_presentation(_strip_invisible(s)))",
     "        m = _LATEX_MEMBER_RE.match(s)", T),
    # --- PRE-RK-4: the task's relation is a premise
    ("R70 görev bağıntısı öncül değil", STP, "        givens = givens + [r for r in _task_relations(ir, ctx) if r not in givens]",
     "        givens = givens", T2),
    ("R71 eşitsizlik öncül değil", STP, '_TASK_RELATION_PARAMS = {"solve_equation": "equation", "solve_inequality": "inequality"}',
     '_TASK_RELATION_PARAMS = {"solve_equation": "equation"}', T2),
    # --- PRE-RK-5: conditions as notation
    ("R80 gösterim okunmaz", VER, "        named = _notation_set(text, ctx.ns.get(tvar), ctx)", "        named = None", T2),
    ("R81 her ilişki çözülür", VER, '    else:\n        return None\n    if op == "==" and isinstance(k, sp.Set):',
     '    else:\n        return c.as_set()\n    if op == "==" and isinstance(k, sp.Set):', T2),
    ("R82 eşitlikte küme üyelik değil", VER, '    if op == "==" and isinstance(k, sp.Set):', "    if False:", T2),
    ("R83 küme olmayan sınır kabul", VER, "    if not isinstance(k, sp.Expr):", "    if False:", T2),
    ("R84 okunmayan iddia çürütülür", VER, '        if claim_not_read and lr.verdict == "fail":',
     '        if False and lr.verdict == "fail":', T2),
    ("R85 aralık iddiası denetlenmez", VER, 'ca.kind in ("value", "set", "count", "interval"))', 'ca.kind in ("value", "set", "count"))',
     T2),
    ("R86 küme görevinde koşul iddiası denetlenmez", VER, '            or (set_task and ca.kind == "condition"):', "            or False:",
     T2),
    # --- PRE-RK-6: SymPy's registry S
    ("R90 S kayıt defteri ad alanında", PAR, '"S": _SINGLETON_NAMES,', '"S": S,', T2),
    ("R91 yazılı okuma istisna sızdırır", PAR, "    try:\n        return sp.Tuple(*out)\n    except Exception:",
     "    if True:\n        return sp.Tuple(*out)\n    try:\n        pass\n    except Exception:", T2),
    ("R92 S.Half okunmaz", PAR, '        if f"S.{name}" in _ALLOWED_DOTTED:', "        if False:", T2),
    ("R93 S(2) okunmaz", PAR, "        return sympify_nontext(value)", '        raise ParseError("S")', T2),
    # --- PRE-RK-7/8: the structure of the target
    ("R95 matris işlemleri yapıda hesaplanır", VER, "        ns = dict(ctx.ns, **{n: sp.Function(n) for n in _MATRIX_OPS})",
     "        ns = dict(ctx.ns)", T2),
    ("R96 yapı değerine düşer", VER, "        return parse_structural(text, ns, strict=True)",
     "        return parse_structural(text, ns, strict=False)", T2),
    ("R97 sözdizimi okuması yok", VER, "        sa, sb = _syntax(a, ctx), _syntax(b, ctx)", "        return False", T2),
]


def _copy_tree(dest: Path) -> None:
    """The working tree (not the committed HEAD, see the module docstring), without .git, the venv, caches
    and .env."""
    shutil.copytree(base.REPO, dest, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".env", "llm_cache",
                                                                    ".pytest_cache"))


if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    if "--calisma-agaci" in sys.argv:          # copies of the working tree (round 1: its commit was refused)
        sys.argv.remove("--calisma-agaci")
        base.clone = _copy_tree
    sys.exit(base.main())
