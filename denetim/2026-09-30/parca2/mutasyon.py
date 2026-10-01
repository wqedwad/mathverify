"""Mutation check of part (ii), N5 of the third audit (30 Sep 2026, DECISIONS §75): an IR function's
declared domain read in every written form or refused (normalize.parse.read_domain_condition), the
symbols a given fixes put into it (given_bindings), an order between non-expressions refused by
parse_relation, the sandbox worker surviving a request it cannot rebuild, and the same silent drop
closed for declared constraints and written conditions on two variables (certify.base, verifier).
The machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is the one of
denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-30/parca2/mutasyon.py [-j N] [--list] [name ...]

Not mutated, a deliberate equivalent: the two new flags in fuse.rules' blocking set. The intake
returns right after the layer that carries them, so no other layer can ground a verdict. A first
run (62aee6f) had A11, "ℝ is not an interval": it lived, because SymPy's Reals is an Interval; the
redundant check was removed from the code instead.

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
BASE = "src/mathverify/certify/base.py"
VER = "src/mathverify/verifier.py"
POOL = "src/mathverify/sandbox/pool.py"
T = "tests/test_parca2_fonksiyon_alani.py"

MUTATIONS = [
    # --- (A) the declared domain of a function
    ("A01 okunamayan alan düşer", P, "        rel = read_domain_condition(fdef.domain, argsyms, body_ns)\n",
     "        try:\n            rel = read_domain_condition(fdef.domain, argsyms, body_ns)\n"
     "        except ParseError:\n            rel = None\n", T),
    ("A02 verilenin değeri alana konmaz", P, "for s_, v in (bindings or {}).items()", "for s_, v in {}.items()", T),
    ("A03 biçimsel argüman da yerine konur", P, "                                             if s_.name not in fdef.args}), fdef.domain)",
     "                                             }), fdef.domain)", T),
    ("A04 bağlanmamış sembol listelenmez", P,
     "            _f.domain_unbound = tuple(sorted(s_.name for s_ in rel.free_symbols if s_.name not in fdef.args))",
     "            _f.domain_unbound = ()", T),
    ("A05 virgül ayırıcı değil", P, '_DOMAIN_JOIN_RE = re.compile(r"\\s*(?:,|&|∧)\\s*|\\s+and\\s+")',
     '_DOMAIN_JOIN_RE = re.compile(r"\\s*(?:&|∧)\\s*|\\s+and\\s+")', T),
    ("A06 and ayırıcı değil", P, '_DOMAIN_JOIN_RE = re.compile(r"\\s*(?:,|&|∧)\\s*|\\s+and\\s+")',
     '_DOMAIN_JOIN_RE = re.compile(r"\\s*(?:,|&|∧)\\s*")', T),
    ("A07 parantez içinde de bölünür", P, "        m = _DOMAIN_JOIN_RE.match(s, i) if depth == 0 else None",
     "        m = _DOMAIN_JOIN_RE.match(s, i)", T),
    ("A08 üyelik okunmaz", P, "        m = None if latex else _DOMAIN_MEMBER_RE.match(p)", "        m = None", T),
    ("A09 açık uç kapalı okunur", P, "        out.append((Gt if st.left_open else Ge)(v, st.start, evaluate=False))",
     "        out.append(Ge(v, st.start, evaluate=False))", T),
    ("A10 aralık olmayan küme kabul", P,
     '    if not isinstance(st, Interval):\n        raise ParseError(f"domain {spec!r} is not an interval of reals")',
     '    if False:\n        raise ParseError(f"domain {spec!r} is not an interval of reals")', T),
    ("A12 iki argümanda çıplak küme ilkine", P, "            if name is None and len(argsyms) != 1:",
     "            if False:", T),
    ("A13 argümanı anmayan koşul kabul", P, "            if not c.free_symbols & set(argsyms):", "            if False:", T),
    ("A14 kenarı ifade olmayan ilişki kabul", P,
     "        if not (isinstance(r, sp.core.relational.Relational) and isinstance(r.lhs, sp.Expr)\n"
     "                and isinstance(r.rhs, sp.Expr)):",
     "        if not isinstance(r, sp.core.relational.Relational):", T),
    ("A15 True alan kısıt sayılır", P, "    if rel is sp.true:\n        return None\n    parts = rel.args",
     "    parts = rel.args", T),
    # --- (B) the bindings
    ("B01 çakışan bağlama denetlenmez", P, "                if s_ in found and found[s_] != v:\n                    clash.add(s_)",
     "                if False:\n                    clash.add(s_)", T),
    ("B02 hesaplanan değer de bağlar", P,
     "            check_claim_is_value(g, fnames)\n            rel = parse_relation(g, vns)",
     "            rel = parse_relation(g, ns)", T),
    # --- (R) parse_relation
    ("R01 sıralama kenarı denetlenmez", P, '        if op in ("<", "<=", ">", ">=") and not (isinstance(exprs[k - 1], sp.Expr)',
     '        if False and not (isinstance(exprs[k - 1], sp.Expr)', T),
    # --- (S) the sandbox worker
    ("S01 okunamayan istek işçiyi öldürür", POOL,
     "        except Exception as e:  # noqa: BLE001 - the message was read whole; only rebuilding it failed",
     "        except ZeroDivisionError as e:  # noqa: BLE001 - the message was read whole; only rebuilding it failed", T),
    ("S02 yanıtsız devam", POOL,
     '            conn.send(("err", type(e).__name__, f"request not readable: {e}", traceback.format_exc(), 0.0))\n            continue',
     "            continue", T),
    ("S03 hatadan sonra işçi biter", POOL,
     'f"request not readable: {e}", traceback.format_exc(), 0.0))\n            continue',
     'f"request not readable: {e}", traceback.format_exc(), 0.0))\n            break', T),
    # --- (C) certify.base: constraints and written conditions
    ("C01 yazılı koşula verilen konmaz", BASE,
     "        return c.xreplace({s_: bind[s_] for s_ in free if s_ != var and s_ in bind})", "        return c", T),
    ("C02 değişkenin kendisi de yerine konur", BASE,
     "        return c.xreplace({s_: bind[s_] for s_ in free if s_ != var and s_ in bind})",
     "        return c.xreplace({s_: bind[s_] for s_ in free if s_ in bind})", T),
    ("C03 hiçbir yerde tanımsız koşul atlanır", BASE, "            if c is sp.false:\n                dom = S.EmptySet\n                continue",
     "            if False:\n                dom = S.EmptySet\n                continue", T),
    ("C04 zincir kısıt bölünmez", BASE, "                for r in (rel.args if isinstance(rel, sp.And) else (rel,)):",
     "                for r in (rel,):", T),
    ("C05 kısıta verilen konmaz", BASE, "                        r = self._with_bound_values(r, var)\n", "", T),
    ("C06 okunamayan kısıt listelenmez", BASE, "                if not ok:\n                    out.append(c)",
     "                if False:\n                    out.append(c)", T),
    ("C07 kısıtın kenarı denetlenmez", BASE,
     "                    ok = all(isinstance(r, sp.core.relational.Relational) and isinstance(r.lhs, sp.Expr)\n"
     "                             and isinstance(r.rhs, sp.Expr) for r in",
     "                    ok = all(True for r in", T),
    # --- (V) the verifier's intake
    ("V01 bağlanmamış alanda çekimser kalınmaz", VER,
     '    if unbound:\n        layers.append(unknown("intake.domain", f"function_domain_not_applied',
     '    if False:\n        layers.append(unknown("intake.domain", f"function_domain_not_applied', T),
    ("V02 okunamayan kısıtta çekimser kalınmaz", VER,
     '    if unreadable:\n        layers.append(unknown("intake.domain", f"constraint_unreadable',
     '    if False:\n        layers.append(unknown("intake.domain", f"constraint_unreadable', T),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
