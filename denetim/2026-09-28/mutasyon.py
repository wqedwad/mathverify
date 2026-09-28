"""Mutation check of the K4 fixes of 28 Sep 2026 (DECISIONS §63): the step refuter's task interval
(A), assignments bound only by domains (B), the problem's own objects (C) and "verified" meaning
proved (V); the Meta client's streaming (M); the K4 harness's answer labels and per-request lock (E). The machinery (throwaway
clones of the committed HEAD, exit codes, clean-up) is the one of denetim/2026-09-26/mutasyon.py;
only the list of mutations is new. Measured equivalent and left out: the restrictions dropped from
the premises of the search (`_in_domains` checks them at every point, `domain_for` on the set route).

    .venv/bin/python denetim/2026-09-28/mutasyon.py [-j N] [--list] [name ...]

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mutasyon_0926", HERE.parent / "2026-09-26" / "mutasyon.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

DET, META, RS = "src/mathverify/steps/deterministic.py", "src/mathverify/llm/meta_client.py", "harness/run_solver.py"
TK, TM, TR = "tests/test_step_refuter_k4.py", "tests/test_meta_retry.py", "tests/test_run_solver.py"

MUTATIONS = [
    # --- (A) the task's interval
    ("A01 aralık öncüle girmiyor", DET, "        window = _task_window(ir, ctx)\n", "        window = []\n", TK),
    ("A02 aralık sembol bağlar", DET, "    window = [w for w in window if w.free_symbols <= syms]\n",
     "    window = [w for w in window if w.free_symbols <= syms]\n"
     "    prem_syms |= set().union(*(w.free_symbols for w in window))\n", TK),
    ("A03 aralık değişken oyunda değilken de girer", DET,
     "    window = [w for w in window if w.free_symbols <= syms]\n", "    window = list(window)\n", TK),
    ("A04 And bölünmüyor", DET, "    parts = list(rel.args) if isinstance(rel, And) else [rel]\n",
     "    parts = [rel]\n", TK),
    ("A05 boş ya da tüm küme de öncül", DET,
     "    if any(r in (sp.true, sp.false) or not _is_relation(r) for r in parts):\n",
     "    if any(not _is_relation(r) for r in parts):\n", TK),
    ("A06 okunamayan aralık düşürür", DET,
     "    except Exception:  # noqa: BLE001 - an interval we cannot read restricts nothing\n        return []\n",
     "    except ZeroDivisionError:\n        return []\n", TK),
    # --- (B) assignments
    ("B01 atama da kısıtla bağlanır", DET, "        if not _is_assignment(claim):\n            prem_syms",
     "        if True:\n            prem_syms", TK),
    ("B02 hiçbir iddia kısıtla bağlanmaz", DET, "        if not _is_assignment(claim):\n            prem_syms",
     "        if False:\n            prem_syms", TK),
    ("B03 seçim atama sayılmaz", DET,
     "    return isinstance(claim, Eq) or (isinstance(claim, Or) and all(isinstance(a, Eq) for a in claim.args))",
     "    return isinstance(claim, Eq)", TK),
    ("B04 kısıtlar yine öncüllerle birlikte", DET,
     "            givens, restrictions = ctx.givens(), ctx.var_constraints()",
     "            givens, restrictions = ctx.givens() + ctx.var_constraints(), []", TK),
    # --- (C) the problem's own objects
    ("C01 teğet eğrisi tanınmıyor", DET, "                return [Eq(y, ctx.expr(p[\"f\"]))]\n",
     "                return []\n", TK),
    ("C02 verilen doğru tanınmıyor", DET, "                return [ctx.rel(p[\"line\"])]\n", "                return []\n", TK),
    ("C03 teğet çemberi tanınmıyor", DET,
     "                return [Eq((x - cx) ** 2 + (y - cy) ** 2, (px - cx) ** 2 + (py - cy) ** 2)]\n",
     "                return []\n", TK),
    ("C04 nesne adımı yine denetlenir", DET,
     "            if st.kind == \"eq\" and objects and _states_task_object(claim, objects, ctx):\n",
     "            if False:\n", TK),
    ("C05 oran sabit olmasa da nesne", DET,
     "        if r.ok and isinstance(r.value, sp.Expr) and not r.value.free_symbols and r.value.is_finite \\\n",
     "        if r.ok and isinstance(r.value, sp.Expr) and r.value.is_finite is not False \\\n", TK),
    # --- (V) "verified" means proved (a finding of the same day)
    ("V01 örneklenen sonuç verified", DET, "        if exhaustive:\n            return \"verified\", ev\n",
     "        if True:\n            return \"verified\", ev\n", TK),
    ("V02 parametrik çözüm de tam", DET, "                if rem:\n                    exhaustive = False\n",
     "                if rem:\n", TK),
    ("V03 polinom olmayan denklem de tam", DET,
     "        return bool((rel.lhs - rel.rhs).is_polynomial(*syms))\n", "        return True\n", TK),
    ("V04 And/Or küme yoluna girmez", DET,
     "    parts = _claim_parts(claim) if isinstance(claim, (And, Or)) else None\n", "    parts = None\n", TK),
    ("V05 boş bölge kanıt sayılır", DET,
     "        return None, bool(nonempty.ok and nonempty.value is True)\n", "        return None, True\n", TK),
    ("V06 küme yolu kanıt vermez", DET, "        if proved:\n", "        if False:\n", TK),
    ("V07 _decide And/Or okumaz", DET, "    if isinstance(rel, (And, Or)):\n        vals", "    if False:\n        vals", TK),
    ("V08 zincir birleşim sayılır", DET, "sets, isinstance(claim, And), timeout", "sets, False, timeout", TK),
    # --- (M) the Meta client
    ("M01 502 akışa geçirmez", META, "                if e.code in (502, 504, 524, 408) and not stream:",
     "                if e.code in (504, 524, 408) and not stream:", TM),
    ("M02 akışsız başlar", META, "                 max_retries: int = 4, stream: bool = True):",
     "                 max_retries: int = 4, stream: bool = False):", TM),
    ("M03 kip ayarı yok sayılır", META, "        stream = self.stream\n", "        stream = False\n", TM),
    ("M04 usage'sız akış kabul", META, "                if stream and not (payload or {}).get(\"usage\"):\n",
     "                if False:\n", TM),
    # --- (E) the K4 harness
    ("E01 C sembol değil", RS, "        ns = dict(ns, C=sp.Symbol(\"C\"))\n", "        ns = dict(ns)\n", TR),
    ("E02 sondaki + C ayıklanmaz", RS,
     "        gold, payload = _TRAILING_C.sub(\"\", str(gold)), _TRAILING_C.sub(\"\", str(payload))\n", "", TR),
    ("E03 anahtardaki C sıfırlanmıyor", RS, "        g = g.subs(ns[\"C\"], 0)\n", "        pass\n", TR),
    ("E03b iddiadaki C sıfırlanmıyor", RS, "            c = c.subs(ns[\"C\"], 0)\n", "            pass\n", TR),
    ("E04 DNE eşanlamlısı tanınmıyor", RS, "    return kind == \"dne\" or (isinstance(payload, str) and",
     "    return kind == \"dne\" or (False and", TR),
    ("E05 DNE metnin içinde aranır", RS, "_DNE.fullmatch(payload.strip().rstrip(\".\").strip())",
     "_DNE.search(payload)", TR),
    ("E06 DNE ile sayı karşılaştırılmaz", RS, "            return \"wrong\", \"does not exist vs a finite value\"",
     "            return \"undecided\", \"does not exist vs a finite value\"", TR),
    ("E07 DNE ile sonsuz yanlış sayılır", RS,
     "        if isinstance(v, sp.Expr) and v.is_number and v.is_finite:",
     "        if isinstance(v, sp.Expr) and v.is_number:", TR),
    ("E10 açıda derece işareti radyan", RS,
     "        gold, payload = strip_degree_marks(str(gold)), strip_degree_marks(str(payload))\n", "        pass\n", TR),
    ("E11 genel çözümde k bildirilmez", RS,
     "        int_params = tuple(sp.Symbol(n_, integer=True) for n_ in (\"k\", \"n\"))\n",
     "        int_params = ()\n", TR),
    ("E12 genel çözümler farkla karşılaştırılır", RS,
     "        if int_params and any(getattr(v, \"free_symbols\", set()) & set(int_params) for v in (c, g)):\n",
     "        if False:\n", TR),
    ("E13 demetler karşılaştırılmaz", RS,
     "        if isinstance(c, (tuple, list)) and isinstance(g, (tuple, list)):\n            label", "        if False:\n            label", TR),
    ("E14 özvektör katı yanlış sayılır", RS, "scale_free=params.get(\"op\") == \"eigenvector\")",
     "scale_free=False)", TR),
    ("E08 istek kilidi yok", RS, "    locks = getattr(args, \"request_locks\", None)\n", "    locks = None\n", TR),
    ("E09 kilitten sonra durdurma denetlenmez", RS,
     "        if stop is not None and stop.is_set():\n            return {**rec, \"skipped\": True}\n        try:\n",
     "        try:\n", TR),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
