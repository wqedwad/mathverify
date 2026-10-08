"""Mutation check of part d4h of the fourth audit's fixes (7 Oct 2026): each mutation removes one guard of the
parser's fixes (`normalize.parse`: rewrites and deciding helpers over forms, matrices and containers, LaTeX set
membership and Leibniz notation, domain lists, the gcd/lcm record; `equiv.forms` on containers; the verifier's
claim checks; `certify.trig` two-parameter families). The machinery (exit codes, clean-up) is the one of
denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

The copies are made from the WORKING TREE, not from a clone of the committed HEAD: the part's commits could not be
made in its session (the commit was refused there), so its code exists only as uncommitted changes. Once the
changes are committed and the tree is clean, both are the same.

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
T = "tests/test_d4_d4h_ayristirici.py"

MUTATIONS = [
    # --- F1: rewrites and deciding helpers over a form
    ("D01 yeniden yazım formu hesaplar", PAR, "        if args and contains_form(list(args)):\n            return args[0]",
     "        if False:\n            return args[0]", T),
    ("D02 karar veren yardımcı evalf ile karar verir", PAR,
     "        if has_closed_form_node(list(args)):\n            with sp.evaluate(False):\n                return cls(*args, **kwargs)",
     "        if False:\n            with sp.evaluate(False):\n                return cls(*args, **kwargs)", T),
    ("D04 formlu matriste rank/eigmax okunur", PAR, "        if contains_form(mat):", "        if False:", T),
    ("D05 gerçelliği belirsiz özdeğer düşer", PAR, "        if any(r is None for r in real):", "        if False:", T),
    ("D06 çıplak ad SymPy sınıfı değil", PAR, "    def _sympy_(self):", "    def _sympy_unused(self):", T),
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
    ("D20 küme listesi kesişim okunur", PAR, "    _refuse_set_lists(read, spec)\n", "", T),
    ("D21 küme + dışlama okunmaz", PAR,
     "            if j != i and names & onames and other != key and not (other is None and excludes):",
     "            if j != i and names & onames and other != key:", T),
    ("D22 aynı küme iki kez okunmaz", PAR,
     "            if j != i and names & onames and other != key and not (other is None and excludes):",
     "            if j != i and names & onames and not (other is None and excludes):", T),
    ("D23 boş liste okunur", PAR, "        _refuse_empty_list(conds, argsyms[0], spec)", "        pass", T),
    # --- I2: Leibniz notation
    ("D24 Leibniz çarpımı okunur", PAR, "    _refuse_leibniz_products(s, ns)\n", "", T),
    ("D25 her Leibniz kesri reddedilir", PAR,
     "        if names and all(isinstance(ns.get(n), Symbol) for n in names):", "        if names:", T),
    ("D26 \\mathrm{d} tanınmaz", PAR, '    num = re.sub(r"\\s+", "", _LATEX_UPRIGHT_D.sub("d", num))',
     '    num = re.sub(r"\\s+", "", num)', T),
    # --- CAP-G1: the gcd/lcm record and the LaTeX restatement
    ("D27 gcd/lcm kaydı yok", PAR, "        _record_integer_op(cls.__name__, args)\n", "", T),
    ("D28 igcd/ilcm kaydı yok", PAR, "        _record_integer_op(name, args)\n", "", T),
    ("D29 LaTeX gcd kayıtsız sınıf", PAR, 'ops = {"gcd": _GCD_CALL, "lcm": _LCM_CALL}', 'ops = {"gcd": gcd, "lcm": lcm}', T),
    ("D30 sembollü gcd de kaydedilir", PAR,
     '    if rec is not None and args and not any(getattr(a, "free_symbols", None) for a in args):',
     "    if rec is not None and args:", T),
    ("D31 kayıt karara bağlanmaz", VER, "    if computed:\n        return unknown(", "    if False:\n        return unknown(", T),
    ("D32 LaTeX yeniden yazımı değerlendirilir", VER, "    if not is_latex(t):\n        return parse_structural(text, ctx.ns)",
     "    if True:\n        return parse_structural(text, ctx.ns)", T),
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
]


def _copy_tree(dest: Path) -> None:
    """The working tree (not the committed HEAD, see the module docstring), without .git, the venv, caches
    and .env."""
    shutil.copytree(base.REPO, dest, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".env", "llm_cache",
                                                                    ".pytest_cache"))


if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    base.clone = _copy_tree
    sys.exit(base.main())
