"""Mutation check of part (v-a) of 30 Sep 2026 (HANDOFF V17, DECISIONS §74): (a) this part's fixes (the
trig family parameter, calculus in a variable declared an integer), (b) `franklin`'s U01-U07 on the set
endpoints, adapted to this code (from `claude/inspiring-franklin-l3cocz:denetim/2026-09-30/mutasyon_v14.py`),
(c) the rest of the §73 port (point binders, reversed ranges, binder definedness, the declared domain of a
task's variable). The machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is the one
of denetim/2026-09-26/mutasyon.py; a mutation's target may name several test files, space-separated.

    MATHVERIFY_LEAN_REPL=/nonexistent .venv/bin/python denetim/2026-09-30/parca5/mutasyon.py [-j N] [--list] [name ...]

Not in the list: `franklin`'s U06 (the `_near` bucket of `unify_endpoints` removed), a deliberate
equivalent. The bucket only skips the exact comparison of two endpoints whose 20-digit values are more
than 1e-9 apart; `exact_equal` (and `certified_sign` for floats) is expected to call such a pair
different, so the mutant decides the same and is only slower (every pair compared exactly: a 1000-element
set took 90 s, DECISIONS §72). Not proved for every pair: a pair that far apart which `exact_equal` could
not decide would make the mutant refuse a set the bucket reads.

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mutasyon_0926", HERE.parents[1] / "2026-09-26" / "mutasyon.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

PARSE = "src/mathverify/normalize/parse.py"
TRIG = "src/mathverify/certify/trig.py"
SETS = "src/mathverify/equiv/sets.py"
DET = "src/mathverify/steps/deterministic.py"
DOM = "src/mathverify/certify/domain.py"
LIM = "src/mathverify/certify/limits.py"
CALC = "src/mathverify/certify/calculus.py"
EXT = "src/mathverify/certify/extremum.py"
# this part's tests first (the fastest kill), then the V14 files; then the parser's binder tests and part
# 7a's (R01 and R02: since the range condition makes the problem UNKNOWN they are the second defence, held
# directly by the parse of floor(Sum(k, (k, 3, 1))) and its LaTeX twin, part 11)
T = ("tests/test_parca5_v17.py tests/test_v14_parser_conventions.py tests/test_audit_2026_09_29_v14.py "
     "tests/test_parse_conventions.py tests/test_parca7a_kume_ayristirici.py")

MUTATIONS = [
    # --- (a) this part: the trig family parameter
    ("V01 aile parametresi IR bildirimini alır", TRIG,
     "            ns_claim = dict(ns2, **family) if not p.get(\"interval\") else ns2\n",
     "            ns_claim = ns2\n", T),
    ("V14 pencereli iddiada da aile parametresi", TRIG,
     "            ns_claim = dict(ns2, **family) if not p.get(\"interval\") else ns2\n",
     "            ns_claim = dict(ns2, **family)\n", T),
    ("V02 m aile parametresi sayılmaz", TRIG,
     "            family = {nm: sp.Symbol(nm, integer=True) for nm in _FAMILY_NAMES\n",
     "            family = {nm: sp.Symbol(nm, integer=True) for nm in (\"n\", \"k\")\n", T),
    # --- (a) this part: calculus in a variable declared an integer
    ("V03 tam sayı değişkende türev okunur", PARSE,
     "    _refuse_integer_calculus(code, dict(local_dict, **dummies), s, rebind)\n", "", T),
    ("V04 türev değişkeni denetlenmez", PARSE,
     "            spec = [a.elts[0] if isinstance(a, seq) and a.elts else a for a in node.args[1:]]\n",
     "            spec = []\n", T),
    ("V05 değişkensiz türevde gövde denetlenmez", PARSE,
     "        if len(node.args) == 1:\n            spec = node.args[:1]\n",
     "        if False:\n            spec = node.args[:1]\n", T),
    ("V06 belirsiz integral denetlenmez", PARSE, "        elif node.func.id in _ANTIDIFFERENTIATING:\n",
     "        elif False:\n", T),
    ("V07 yazıldığı-biçim okuması bağlayıcı içini de yargılar", PARSE,
     "    nested: set[int] = set()\n    if not rebound:\n", "    nested: set[int] = set()\n    if False:\n", T),
    ("V08 yeniden bağlanmış adlar görülmez", PARSE,
     "    _refuse_integer_calculus(code, dict(local_dict, **dummies), s, rebind)\n",
     "    _refuse_integer_calculus(code, local_dict, s, rebind)\n", T),
    ("V09 türev mertebesi de değişken sayılır", PARSE,
     "            spec = [a.elts[0] if isinstance(a, seq) and a.elts else a for a in node.args[1:]]\n",
     "            spec = [a for a in node.args[1:]]\n", T),
    ("V10 belirli integralin değişkeni de yargılanır", PARSE,
     "            spec = [a.elts[0] if isinstance(a, seq) else a for a in node.args[1:]\n"
     "                    if not isinstance(a, seq) or len(a.elts) == 1]\n",
     "            spec = [a.elts[0] if isinstance(a, seq) else a for a in node.args[1:]]\n", T),
    ("V11 LaTeX türevi tam sayı değişkende okunur", PARSE, "    _refuse_latex_integer_calculus(expr, ns, s)\n", "", T),
    ("V12 LaTeX adları yalnız bildirimden sonra denetlenir", PARSE,
     "    _check_symbols_declared(expr, ns, s)\n    _refuse_latex_integer_calculus(expr, ns, s)\n",
     "    _refuse_latex_integer_calculus(expr, ns, s)\n", T),
    ("V13 LaTeX belirsiz integrali denetlenmez", PARSE,
     "            names = [lim[0].name for lim in node.limits if len(lim) == 1 and isinstance(lim[0], Symbol)]\n",
     "            names = []\n", T),
    # --- (b) franklin's U01-U07 (U06: equivalent, see the docstring)
    ("U01 küme okunurken uçlar eşitlenmez", PARSE, "        sets = unify_endpoints(sets)\n", "        pass\n", T),
    ("U02 adım kümesinde uçlar eşitlenmez", DET,
     "    region, *sets = unify_endpoints([region, *sets])      # raises when two endpoints are undecided\n",
     "    pass\n", T),
    ("U03 yozlaşmış aralık nokta olmaz", SETS, "        if c == 0:                               # Interval(3,",
     "        if False:                               # Interval(3,", T),
    ("U04 karar verilemeyen uç eşitlenir", SETS,
     "                if eq is None:\n                    raise EndpointsIncomparable(f\"{e} and {r}\")\n",
     "                if eq is None:\n                    mapping[e] = r\n                    break\n", T),
    ("U05 SymPy küme kurucusu eşitlemez", PARSE, '"Union": _set_op(Union),', '"Union": Union,', T),
    ("U07 sınırsız sayıda uç", SETS, "            if n_const > _UNIFY_LIMIT:\n", "            if False:\n", T),
    # --- (c) the rest of the §73 port
    ("P01 nokta bağlayıcısı yeniden adlandırılmaz", PARSE,
     "        if rebind and any(b in code for b in _POINT_BINDERS) else None\n", "        if False else None\n", T),
    ("P02 sonsuzdaki limit bildirimi düşürür", PARSE,
     "                    return frozenset({\"real\"} | {f for f in (\"integer\", \"positive\", \"nonnegative\")\n"
     "                                                 if getattr(declared, f\"is_{f}\", None) is True})\n",
     "                    return frozenset({\"real\"})\n", T),
    ("P03 aynı adlı iç içe nokta bağlayıcısı okunur", PARSE,
     "        if any(calls.get(id(n)) == v for n in ast.walk(body) if n is not call):\n",
     "        if False:\n", T),
    ("P04 anahtar sözcükle verilen değişken okunur", PARSE,
     "        if any(kw.arg not in allowed for kw in node.keywords):\n", "        if False:\n", T),
    ("R01 sayılı ters aralık AST'de okunur", PARSE, "                if hi - lo + 1 < 0:\n", "                if False:\n", T),
    ("R02 LaTeX ters aralık okunur", PARSE, "    _refuse_latex_ranges(s)\n", "    pass\n", T),
    ("D01 toplam bağlayıcısının koşulu yok", DOM, "                out = _range_conditions(n, var)\n",
     "                out = []\n", T),
    ("D02 integral bağlayıcısının koşulu yok", DOM, "                out = _integral_conditions(n, var)\n",
     "                out = []\n", T),
    ("D03 limit bağlayıcısının koşulu yok", DOM, "                out = _limit_conditions(n, var)\n",
     "                out = []\n", T),
    ("L01 dizi limiti sonlu noktada", LIM,
     "        return side if point == oo or (point == -oo and not nonneg) else False\n", "        return side\n", T),
    ("L02 alanın kapalı ucunda iki yönlü limit", LIM,
     "    if getattr(point, \"is_zero\", None) and side in (None, \"+\"):\n        return \"+\"\n",
     "    if getattr(point, \"is_zero\", None) and side in (None, \"+\"):\n        return side\n", T),
    ("L03 ayrıştırmada alan ucu limiti iki yönlü", PARSE,
     "        if str(d) == \"+-\" and z0 == 0 and getattr(z, \"is_positive\", None) is True:\n",
     "        if False:\n", T),
    ("T01 tam sayı değişkende türev görevi", CALC,
     "        if kind != \"definite_integral\" and getattr(var, \"is_integer\", None):\n", "        if False:\n", T),
    ("T02 tam sayı değişkende ekstremum görevi", EXT, "        if getattr(var, \"is_integer\", None):\n",
     "        if False:\n", T),
]


def run_tests(where: Path, test: str) -> subprocess.CompletedProcess:
    """base.run_tests with several test files: the target string is split at spaces."""
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
               PYTHONPATH=os.pathsep.join([str(where / "src"), str(where)]))
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "--timeout", "300", *test.split()]
    with subprocess.Popen(cmd, cwd=where, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="utf-8", errors="replace") as proc:
        with base._LOCK:
            base._RUNNING.add(proc)
        try:
            out, _ = proc.communicate()
        finally:
            with base._LOCK:
                base._RUNNING.discard(proc)
    return subprocess.CompletedProcess(cmd, proc.returncode, out, "")


if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    base.run_tests = run_tests
    sys.exit(base.main())
