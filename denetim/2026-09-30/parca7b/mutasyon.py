"""Mutation check of part (v-b B) of 30 Sep 2026 (HANDOFF V16, DECISIONS §73 "Açık kalanlar"): the
binder body read on plain symbols, the calculus/simplification function undefined as written, the
parametric integral's reachable improper point, the undecided number-set membership, the step undefined
at the premises' point and the claim's condition on another variable. The machinery (throwaway clones of
the committed HEAD, exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py; a target may name
several test files, space-separated (as in denetim/2026-09-30/parca5/mutasyon.py).

    MATHVERIFY_LEAN_REPL=/nonexistent .venv/bin/python denetim/2026-09-30/parca7b/mutasyon.py [-j N] [--list] [name ...]

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

DOM = "src/mathverify/certify/domain.py"
BASE = "src/mathverify/certify/base.py"
ALG = "src/mathverify/certify/algebra.py"
DET = "src/mathverify/steps/deterministic.py"
# this part's tests first (the fastest kill), then the V14 files
T = "tests/test_parca7b_tanimlilik.py tests/test_v14_parser_conventions.py tests/test_audit_2026_09_29_v14.py"

MUTATIONS = [
    # --- (1) the binder's body on plain symbols
    ("B01 gövde bildirimli sembolle okunur", DOM,
     "            plain = {v: sp.Symbol(v.name) for v in bound if isinstance(v, sp.Symbol)}\n",
     "            plain = {}\n", T),
    ("B02 düz semboller gizlenmez", DOM, "            hidden = bound | set(plain.values())\n",
     "            hidden = bound\n", T),
    ("B03 okumanın değişkeni gövdeye eşlenmez", DOM,
     "            for c in definedness_conditions(body, plain.get(var, var)):\n",
     "            for c in definedness_conditions(body, var):\n", T),
    # --- (2) the parametric integral's improper point, the function undefined as written
    ("I01 sembolik sınırda uygunsuz nokta değerin işi", DOM,
     "        if symbolic and bad.is_empty is not True:\n", "        if False:\n", T),
    ("I02 erişim aralığı hep kapalı", DOM,
     "    return Interval(lo, hi, left_open=u.contains(lo) is not sp.true, right_open=u.contains(hi) is not sp.true)\n",
     "    return Interval(lo, hi)\n", T),
    ("I03 pozitif sınır 0'a ulaşır", DOM, "            parts.append(Interval.open(0, oo))\n",
     "            parts.append(Interval(0, oo))\n", T),
    ("I04 işaretsiz sınır bir nokta", DOM,
     "        else:\n            return S.Reals\n    u = sp.Union(*parts)\n",
     "        else:\n            parts.append(S.EmptySet)\n    u = sp.Union(*parts)\n", T),
    ("F01 görev fonksiyonu yazıldığı biçimde okunmaz", BASE,
     "        if isinstance(fsrc, str) and fsrc not in undefined and self._undefined_function(fsrc, kind):\n",
     "        if False:\n", T),
    ("F02 belirli integralin değişkeni bildirimle", BASE,
     "            ns = dict(ns, **{v: sp.Symbol(v, real=True)})\n", "            pass\n", T),
    ("F03 kapalı karar verilemeyen koşul sayılmaz", BASE,
     "            return any(c is sp.false for c in conds) or self._undefined_term(e) or closed_condition_undecided(conds)\n",
     "            return any(c is sp.false for c in conds) or self._undefined_term(e)\n", T),
    ("F04 hiçbir yerde tanımsız sayılmaz", BASE,
     "            return any(c is sp.false for c in conds) or self._undefined_term(e) or closed_condition_undecided(conds)\n",
     "            return self._undefined_term(e) or closed_condition_undecided(conds)\n", T),
    ("F05 sadeleştirme ve değer listede yok", BASE,
     "                       \"definite_integral\": \"integrand\", \"simplify_expression\": \"expr\", \"evaluate\": \"expr\"}\n",
     "                       \"definite_integral\": \"integrand\"}\n", T),
    # --- (3) an undecided number-set membership
    ("M01 kökte karar verilemeyen üyelik içeride", DOM,
     "        if d is None and membership_undecided(domain, c):\n", "        if False:\n", T),
    ("M02 değer yolunda karar verilemeyen üyelik tutulur", ALG,
     "                        if m is False or (m is None and undecided is not None):\n",
     "                        if m is False:\n", T),
    ("M03 karar verilemeyen çözüm düşürülür", ALG,
     "        if undecided:\n            ev[\"membership_undecided\"]", "        if False:\n            ev[\"membership_undecided\"]", T),
    # --- (4) steps and simplifications
    ("S01 öncül noktasında tanımsız adım", DET,
     "                elif _undefined_at_premises(st.claim, step_ns, list(givens) + [\n",
     "                elif False and _undefined_at_premises(st.claim, step_ns, list(givens) + [\n", T),
    ("S02 sonlu öncül kümesi okunmaz", DET,
     "        if not isinstance(region, sp.FiniteSet) or len(region) > 12:\n            return False\n",
     "        return False\n", T),
    ("S03 karar verilemeyen koşul tanımlı sayılır", DET,
     "            if held is not True:\n                return True\n", "            if held is False:\n                return True\n", T),
    ("S04 serbest sembol de nokta sayılır", DET, "    if set(pins) == syms:\n", "    if pins:\n", T),
    ("S05 öbür değişkenin alanı eklenmez", ALG, "                dom[s_] = ctx.domain_for(s_)\n", "                pass\n", T),
]


def run_tests(where: Path, test: str) -> subprocess.CompletedProcess:
    """base.run_tests with several test files: the target string is split at spaces (as in parca5)."""
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
