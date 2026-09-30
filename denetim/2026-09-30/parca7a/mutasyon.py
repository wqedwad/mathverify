"""Mutation check of part (v-b A) of 30 Sep 2026 (HANDOFF V16): set `+`/`-` through `_set_op`, the exact
order of `normalize_set`, the constant bounds of a Sum/Product (text and LaTeX), the gcd check of a list
payload and the size limit of `unify_endpoints` (rationals counted). The machinery (throwaway clones of the
committed HEAD, exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py, with the several-files
target of denetim/2026-09-30/parca5/mutasyon.py.

    MATHVERIFY_LEAN_REPL=/nonexistent .venv/bin/python denetim/2026-09-30/parca7a/mutasyon.py [-j N] [--list] [name ...]

Not in the list, equivalent: the symbol guard of `_constant_bound` removed (a bound naming a symbol then
evaluates to a non-number, or raises NameError, and is skipped all the same).

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mutasyon_parca5", HERE.parent / "parca5" / "mutasyon.py")
p5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p5)
base = p5.base

PARSE = "src/mathverify/normalize/parse.py"
SETS = "src/mathverify/equiv/sets.py"
VER = "src/mathverify/verifier.py"
# this part's tests first (the fastest kill), then the V14 files
T = "tests/test_parca7a_kume_ayristirici.py tests/test_v14_parser_conventions.py tests/test_audit_2026_09_29_v14.py"

MUTATIONS = [
    # --- (1) set + and -
    ("K01 küme işleci yönlendirilmez", PARSE,
     "    routed = _route_set_arithmetic(code, {**global_dict, **local_dict, **dummies}) if evaluate else None\n",
     "    routed = None\n", T),
    ("K02 birleşim yönlendirilmez", PARSE,
     "    return _UNION_OP(a, other) if other is not None else a + b\n", "    return a + b\n", T),
    ("K03 fark yönlendirilmez", PARSE,
     "    return _COMPLEMENT_OP(a, other) if other is not None else a - b\n", "    return a - b\n", T),
    ("K04 Python kümesi FiniteSet olmaz", PARSE,
     "    if isinstance(v, (set, frozenset)):\n        return FiniteSet(",
     "    if False:\n        return FiniteSet(", T),
    ("K05 yazıldığı-biçim okuması da yönlendirilir", PARSE,
     "{**global_dict, **local_dict, **dummies}) if evaluate else None\n",
     "{**global_dict, **local_dict, **dummies}) if True else None\n", T),
    ("K06 S küme adı sayılmaz", PARSE,
     "        or getattr(obj, \"builds_set\", False) is True or obj is S\n",
     "        or getattr(obj, \"builds_set\", False) is True\n", T),
    ("K07 çağrı argümanındaki işleç yönlendirilmez", PARSE,
     "                        value[i] = _routed_binop(v)\n                        stack.append(value[i])\n",
     "                        value[i] = _routed_binop(v)\n", T),
    ("K08 kökteki işlecin altı yönlendirilmez", PARSE,
     "                setattr(node, field, new)\n                stack.append(new)\n",
     "                setattr(node, field, new)\n", T),
    # --- (2) exact order of normalize_set
    ("F01 float sıralama", SETS,
     "            ivs = sorted(ivs, key=cmp_to_key(_inf_cmp))\n",
     "            ivs = sorted(ivs, key=lambda i: (float(i.inf) if i.inf.is_number and i.inf != -oo else -1e300))\n", T),
    ("F02 sıralanamayan başlangıç tahmin edilir", SETS,
     "        raise _Unordered(f\"{a.inf} and {b.inf}\")\n", "        return -1\n", T),
    # --- (3) constant bounds
    ("B01 sabit sınır değerlendirilmez", PARSE,
     "                    if names is not None:\n                        lo_c, hi_c",
     "                    if False:\n                        lo_c, hi_c", T),
    ("B02 ad alanı verilmez", PARSE,
     "        _refuse_computed_bounds(code, s, {**global_dict, **local_dict})\n",
     "        _refuse_computed_bounds(code, s)\n", T),
    ("B03 ters sabit aralık okunur", PARSE,
     "    if (hi - lo + 1).is_extended_negative is True:\n        raise ParseError(f\"{raw!r} has a {name} over a reversed range",
     "    if False:\n        raise ParseError(f\"{raw!r} has a {name} over a reversed range", T),
    ("B04 tam sayı aralığı denetlenmez", PARSE,
     "    if span.is_number and span.is_finite and span.is_integer is False:\n        raise ParseError(f\"{raw!r} has a {name} whose",
     "    if False:\n        raise ParseError(f\"{raw!r} has a {name} whose", T),
    ("B05 LaTeX sabit sınırı denetlenmez", PARSE,
     "        elif \"_\" in scripts and \"^\" in scripts:\n", "        elif False:\n", T),
    ("B06 LaTeX sınırında ad önekinden sonra değer okunmaz", PARSE,
     "    text = re.sub(r\"^\\s*[A-Za-z]\\w*\\s*=\", \"\", text)\n", "", T),
    # --- (5) gcd in a list payload
    ("G01 liste yükünde gcd denetimi yok", VER,
     "        return _claim_computes_integer_op(solution, ctx) if isinstance(ca.payload, list) else None\n",
     "        return None\n", T),
    # --- (6) the size limit
    ("U01 sınır rasyonelleri saymaz", SETS, "            n_const += 1\n",
     "            n_const += not isinstance(e, sp.Rational)\n", T),
]


if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    base.run_tests = p5.run_tests
    sys.exit(base.main())
