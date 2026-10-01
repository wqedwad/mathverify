"""Mutation check of part (v-b C) of 30 Sep 2026 (HANDOFF V16 and V18): the task certificates of limit,
derivative, tangent line, the integrals and extremum. Each mutation undoes one piece of the change; the
part's test file must fail on it. The machinery (throwaway clones of the committed HEAD, exit codes,
clean-up) is the one of denetim/2026-09-26/mutasyon.py, with the several-files runner of parca5.

    MATHVERIFY_LEAN_REPL=/nonexistent .venv/bin/python denetim/2026-09-30/parca7c/mutasyon.py [-j N] [--list] [name ...]

Not in the list, deliberately:
  * the value parse's conditions in `membership_conditions` (only the written ones kept): no input was
    found where the as-written reading fails while the value parse carries a membership condition
    (gcd/lcm, factorial, binomial, their LaTeX spellings and a zero factor were tried); a guard for a
    reading that returns None, not proved equivalent;
  * `inside is not True` weakened to `inside is False` in `_point_not_interior`: it differs only on a
    point whose membership in the domain's interior no exact comparison decides, and no such point of a
    declared domain was found.

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

LIM = "src/mathverify/certify/limits.py"
CALC = "src/mathverify/certify/calculus.py"
EXT = "src/mathverify/certify/extremum.py"
T = "tests/test_parca7c_gorev_sertifikalari.py"

MUTATIONS = [
    # --- (1) undefined as written, no symbol left
    ("G01 kapalı yanlış koşul sayılmaz", LIM,
     "    return any(c is sp.false for c in conds) or closed_condition_undecided(conds)\n",
     "    return closed_condition_undecided(conds)\n", T),
    ("G02 karar verilemeyen kapalı koşul sayılmaz", LIM,
     "    return any(c is sp.false for c in conds) or closed_condition_undecided(conds)\n",
     "    return any(c is sp.false for c in conds)\n", T),
    ("G03 limit görevi eski denetimle", LIM,
     "        if nowhere or written_undefined_everywhere(p[\"expr\"], ctx.ns):\n", "        if nowhere:\n", T),
    ("G04 kalkülüs yardımcısı yazıldığı biçime bakmaz", CALC,
     "    if written_undefined_everywhere(src, ns):\n", "    if False:\n", T),
    ("G05 ilkel görevi denetlenmez", CALC,
     "            bad = _unreadable_task_expression(p[\"integrand\"], integrand, var, ctx.ns, t.ms)\n",
     "            bad = None\n", T),
    ("G06 belirli integral görevi denetlenmez", CALC,
     "            bad = _unreadable_task_expression(p[\"integrand\"], integrand, var, ns_i, t.ms)\n",
     "            bad = None\n", T),
    ("G07 türev görevi denetlenmez", CALC,
     "            bad = _unreadable_task_expression(p[\"f\"], f, var, ctx.ns, t.ms)\n            if bad is not None:\n",
     "            bad = None\n            if bad is not None:\n", T),
    ("G08 teğet görevi denetlenmez", CALC,
     "            bad = _unreadable_task_expression(p[\"f\"], f, var, ctx.ns, t.ms) \\\n"
     "                or _point_not_interior(ctx, var, at, t.ms)\n",
     "            bad = _point_not_interior(ctx, var, at, t.ms)\n", T),
    ("G09 ekstremum görevi denetlenmez", EXT, "        if written_undefined_everywhere(p[\"f\"], ctx.ns):\n",
     "        if False:\n", T),
    # --- (2) the point of a derivative or a tangent line
    ("P01 türevde iç nokta denetlenmez", CALC, "                bad = _point_not_interior(ctx, var, at, t.ms)\n",
     "                bad = None\n", T),
    ("P02 teğette iç nokta denetlenmez", CALC,
     "            bad = _unreadable_task_expression(p[\"f\"], f, var, ctx.ns, t.ms) \\\n"
     "                or _point_not_interior(ctx, var, at, t.ms)\n",
     "            bad = _unreadable_task_expression(p[\"f\"], f, var, ctx.ns, t.ms)\n", T),
    ("P03 iç yerine alanın kendisi", CALC, "        inside = in_domain(ctx.domain_for(var).interior, at)\n",
     "        inside = in_domain(ctx.domain_for(var), at)\n", T),
    ("P04 serbest sembollü kısıtta çekimserlik yok", CALC,
     "    unapplied = ctx.unapplied_conditions(var)\n    if unapplied:\n",
     "    unapplied = ctx.unapplied_conditions(var)\n    if False:\n", T),
    # --- (3) membership conditions
    ("M01 üyelik koşulu hiç bulunmaz", LIM,
     "    return [c for c in dict.fromkeys(conds) if isinstance(c, sp.Contains) and var in c.free_symbols]\n",
     "    return []\n", T),
    ("M02 yalnız ayrıştırılmış ifadenin koşulları", LIM, "    conds = list(written_definedness(src, ns)[0])\n",
     "    conds = []\n", T),
    ("M03 limit görevi üyeliği okumaz", LIM,
     "        if members:\n            return unknown(LAYER, \"membership_condition_on_variable\", t.ms,\n",
     "        if False:\n            return unknown(LAYER, \"membership_condition_on_variable\", t.ms,\n", T),
    ("M04 kalkülüs görevleri üyeliği okumaz", CALC, "    if members:\n", "    if False:\n", T),
    ("M05 ekstremum görevi üyeliği okumaz", EXT, "        if members:\n", "        if False:\n", T),
    # --- (5) V18: the extremum region
    ("E01 kesişim uygulanmaz", EXT, "            iv = sp.Intersection(iv, *cut) if cut else iv\n", "            pass\n", T),
    ("E02 kısıt aralıkla okunmaz", EXT,
     "        srcs = (list(vd.constraints) if vd is not None else []) + srcs\n", "        pass\n", T),
    ("E03 verilen okunmaz", EXT, "    srcs = list(ctx.ir.givens)\n", "    srcs = []\n", T),
    ("E04 tanım evreni aralıkla okunmaz", EXT, "            sets.append(ds)\n", "            pass\n", T),
    ("E05 serbest sembolde çekimserlik yok", EXT,
     "        if unbound:\n            return condition_not_applied(LAYER, unbound, t.ms)\n",
     "        if False:\n            return condition_not_applied(LAYER, unbound, t.ms)\n", T),
    ("E06 çözülemeyen koşul düşer", EXT,
     "        if isinstance(sol, ConditionSet) or sol.has(ConditionSet):\n            return None, unbound + unread\n",
     "        if isinstance(sol, ConditionSet) or sol.has(ConditionSet):\n            continue\n", T),
    ("E07 değişkeni anmayan verilen de okunur", EXT,
     "            if isinstance(r, sp.core.relational.Relational) and var in r.free_symbols:\n",
     "            if isinstance(r, sp.core.relational.Relational):\n", T),
    ("E08 sabitlenen sembol yerine konmaz", EXT, "    kept, unbound = ctx.on_var(rels, var)\n",
     "    kept, unbound = rels, []\n", T),
    ("E09 boş bölge nedeni yok", EXT,
     "            if iv is S.EmptySet:\n                return unknown(LAYER, \"interval_empty_under_the_conditions\"",
     "            if False:\n                return unknown(LAYER, \"interval_empty_under_the_conditions\"", T),
    ("E10 aralıksız görevde verilen okunmaz", EXT,
     "        cut, unbound = _conditions_on(ctx, var, bool(p.get(\"interval\")))\n",
     "        cut, unbound = _conditions_on(ctx, var, True) if p.get(\"interval\") else ([], [])\n", T),
    ("E11 zincir eşitsizlik bölünmez", EXT,
     "        for r in (rel.args if isinstance(rel, sp.And) else (rel,)):\n            # parse_relation",
     "        for r in (rel,):\n            # parse_relation", T),
]


def run_tests(where: Path, test: str) -> subprocess.CompletedProcess:
    """base.run_tests with several test files: the target string is split at spaces (as parca5)."""
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
