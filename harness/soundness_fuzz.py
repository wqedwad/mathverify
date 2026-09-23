"""Metamorphic / differential soundness sweep of the deterministic verifier.

    python -m harness.soundness_fuzz [--limit N] [--out reports]

The evaluation set measures the verifier on the answers someone chose to write. This sweep
measures it on answers SymPy manufactures from each problem's gold answer, where the ground
truth is known by construction:

  WRONG variants       provably different from the gold answer (gold ± 1, ×2, a dropped or an
                       extra set member, a closed endpoint, a 1e-9 perturbation, …).
                       A CORRECT verdict on one of these is a FALSE ACCEPT — the failure the
                       product exists to prevent. Target: 0.
  EQUIVALENT variants  provably the same answer written differently (expanded, factored,
                       decimal, permuted set, Interval(...) form, a scaled equation, …).
                       An INCORRECT verdict on one of these is a FALSE REJECTION (template
                       sensitivity, [10]). UNKNOWN is reported separately as lost coverage.

Every variant is checked with SymPy before it is used: a "wrong" variant that SymPy cannot
prove different, or an "equivalent" one it cannot prove equal, is discarded rather than
scored. The solutions carry no steps and no option letter, so this isolates the answer-level
certificates (the step refuter and the option path have their own sweeps in adversarial.py).

This is the technique program-verifier testing calls metamorphic testing (equivalent inputs
must give equal outputs) and differential testing (an independent oracle — here exact SymPy
arithmetic on the gold answer — cross-checks every output).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from harness.loader import load_items, split_for_verifier  # noqa: E402

KIND_OF_SHAPE = {"scalar": "value", "expression": "expression", "set": "set", "interval": "interval",
                 "count": "count", "equation": "equation", "dne_or_scalar": "value"}


def _is_zero(e) -> bool | None:
    import sympy as sp
    try:
        z = sp.simplify(e)
    except Exception:  # noqa: BLE001
        return None
    if z == 0:
        return True
    if getattr(z, "free_symbols", None):
        return False if z.is_zero is False else None
    try:
        return abs(complex(sp.N(z, 40))) < 1e-35
    except (TypeError, ValueError):
        return None


def _eq_ratio(a, b):
    """For two equations: (l1 - r1) / (l2 - r2), simplified. A nonzero constant means the same
    curve; anything with a free symbol means different curves (for the lines, circles and
    tangent lines this set contains)."""
    import sympy as sp
    try:
        return sp.simplify((a.lhs - a.rhs) / (b.lhs - b.rhs))
    except Exception:  # noqa: BLE001
        return None


def _differs(a, b, *, mod_constant: bool = False) -> bool:
    """True only when SymPy can PROVE a != b (up to an additive constant if asked)."""
    import sympy as sp
    if isinstance(a, sp.Equality) or isinstance(b, sp.Equality):
        if not (isinstance(a, sp.Equality) and isinstance(b, sp.Equality)):
            return False
        r = _eq_ratio(a, b)
        return r is not None and (bool(r.free_symbols) or r == 0)
    if isinstance(a, sp.Set) or isinstance(b, sp.Set):
        try:
            return (a == b) is False and bool(sp.Complement(a, b) != sp.S.EmptySet
                                             or sp.Complement(b, a) != sp.S.EmptySet)
        except Exception:  # noqa: BLE001
            return False
    if isinstance(a, sp.MatrixBase) or isinstance(b, sp.MatrixBase):
        try:
            return a.shape == b.shape and any(_is_zero(x - y) is False for x, y in zip(a, b))
        except Exception:  # noqa: BLE001
            return False
    d = a - b
    if mod_constant:
        free = getattr(d, "free_symbols", set())
        if not free:
            return False                           # differs only by a constant: equivalent
        try:
            return any(_is_zero(sp.diff(d, s)) is False for s in free)
        except Exception:  # noqa: BLE001
            return False
    return _is_zero(d) is False


def _equal(a, b, *, mod_constant: bool = False) -> bool:
    import sympy as sp
    if isinstance(a, sp.Equality) or isinstance(b, sp.Equality):
        if not (isinstance(a, sp.Equality) and isinstance(b, sp.Equality)):
            return False
        r = _eq_ratio(a, b)
        return r is not None and not r.free_symbols and r != 0 and r.is_finite is not False
    if isinstance(a, sp.Set) or isinstance(b, sp.Set):
        try:
            return bool(a == b) or (sp.Complement(a, b) == sp.S.EmptySet and sp.Complement(b, a) == sp.S.EmptySet)
        except Exception:  # noqa: BLE001
            return False
    if isinstance(a, sp.MatrixBase) or isinstance(b, sp.MatrixBase):
        try:
            return a.shape == b.shape and all(_is_zero(x - y) is True for x, y in zip(a, b))
        except Exception:  # noqa: BLE001
            return False
    d = a - b
    if mod_constant:
        free = getattr(d, "free_symbols", set())
        return all(_is_zero(sp.diff(d, s)) is True for s in free) if free else True
    return _is_zero(d) is True


def _pstr(e) -> str:
    """A payload string the verifier's canonical parser accepts."""
    import sympy as sp
    if isinstance(e, sp.Equality):
        return f"{sp.sstr(e.lhs)} = {sp.sstr(e.rhs)}"
    return sp.sstr(e)


def variants(gold, shape: str, kind_task: str, ns) -> tuple[list[tuple[str, Any]], list[tuple[str, Any]]]:
    """(wrong, equivalent) lists of (name, sympy object)."""
    import sympy as sp
    wrong: list[tuple[str, Any]] = []
    equiv: list[tuple[str, Any]] = []
    if isinstance(gold, sp.MatrixBase):
        g = gold.as_mutable()
        w = g.copy()
        w[0] = w[0] + 1
        wrong.append(("entry_plus_one", w))
        wrong.append(("negated", -g))
        equiv.append(("same_matrix_rebuilt", sp.Matrix(g.tolist())))
        return wrong, equiv
    if isinstance(gold, sp.Equality):
        lhs, rhs = gold.lhs, gold.rhs
        wrong.append(("rhs_plus_one", sp.Eq(lhs, rhs + 1, evaluate=False)))
        wrong.append(("rhs_doubled", sp.Eq(lhs, 2 * rhs, evaluate=False)))
        equiv.append(("moved_to_one_side", sp.Eq(sp.expand(lhs - rhs), 0, evaluate=False)))
        equiv.append(("scaled_by_2", sp.Eq(sp.expand(2 * lhs), sp.expand(2 * rhs), evaluate=False)))
        equiv.append(("sides_swapped", sp.Eq(rhs, lhs, evaluate=False)))
        return wrong, equiv
    if isinstance(gold, sp.FiniteSet):
        els = list(gold.args)
        if len(els) > 1:
            wrong.append(("dropped_member", sp.FiniteSet(*els[:-1])))
            equiv.append(("permuted", sp.FiniteSet(*reversed(els))))
        if els and all(getattr(e, "is_number", False) for e in els):
            extra = els[-1] + 1
            if extra not in gold:
                wrong.append(("extra_member", sp.FiniteSet(*els, extra)))
            wrong.append(("shifted", sp.FiniteSet(*[e + 1 for e in els])))
        return wrong, equiv
    if isinstance(gold, (sp.Interval, sp.Union)):
        ivs = list(gold.args) if isinstance(gold, sp.Union) else [gold]
        first = ivs[0]
        if isinstance(first, sp.Interval) and first.inf.is_finite:
            flipped = sp.Interval(first.inf, first.sup, not first.left_open, first.right_open)
            wrong.append(("left_endpoint_flipped", sp.Union(flipped, *ivs[1:])))
        last = ivs[-1]
        if isinstance(last, sp.Interval) and last.sup.is_finite:
            flipped = sp.Interval(last.inf, last.sup, last.left_open, not last.right_open)
            wrong.append(("right_endpoint_flipped", sp.Union(*ivs[:-1], flipped)))
        if isinstance(first, sp.Interval) and first.inf.is_finite:
            wrong.append(("left_endpoint_shifted",
                          sp.Union(sp.Interval(first.inf - 1, first.sup, first.left_open, first.right_open), *ivs[1:])))
        equiv.append(("same_set_rebuilt", sp.Union(*ivs)))
        return wrong, equiv
    if not isinstance(gold, sp.Expr):
        return wrong, equiv
    free = sorted(gold.free_symbols, key=lambda s: s.name)
    mod_c = kind_task == "antiderivative"
    if not free:                                          # a number
        if gold != 0:
            wrong += [("negated", -gold), ("doubled", 2 * gold)]
        wrong += [("plus_one", gold + 1), ("minus_one", gold - 1), ("plus_half", gold + sp.Rational(1, 2)),
                  ("perturbed_1e-9", gold + sp.Rational(1, 10**9)),
                  ("relative_1e-6", gold * (1 + sp.Rational(1, 10**6)) if gold != 0 else sp.Rational(1, 10**6))]
        equiv += [("times_one_unevaluated", sp.Mul(1, gold, evaluate=False)),
                  ("nsimplified", sp.nsimplify(gold)),
                  ("radsimp", sp.radsimp(gold))]
        # Only a TERMINATING decimal is the same number. The parser reads decimals as exact
        # rationals (0.5 -> 1/2), so a truncated 2.666…67 is not 8/3, and scoring it as an
        # "equivalent" would reward the old tolerance accident that accepted ≥21-digit
        # truncations and rejected shorter ones.
        if gold.is_Rational and not gold.is_Integer:
            q = int(gold.q)
            while q % 2 == 0:
                q //= 2
            while q % 5 == 0:
                q //= 5
            if q == 1:
                from decimal import Decimal
                equiv.append(("decimal", sp.Float(str(Decimal(int(gold.p)) / Decimal(int(gold.q))), 30)))
    else:                                                 # an expression in the problem's symbols
        x = free[0]
        wrong += [("plus_x", gold + x), ("doubled", 2 * gold), ("shifted_argument", gold.subs(x, x + 1))]
        if not mod_c:
            wrong.append(("plus_one", gold + 1))
        equiv += [("expanded", sp.expand(gold)), ("factored", sp.factor(gold)),
                  ("together", sp.together(gold))]
        if mod_c:
            equiv.append(("plus_constant", gold + 7))
    return wrong, equiv


def non_answers(ir: dict[str, Any]) -> list[tuple[str, str]]:
    """Payloads that are not answers at all: the question written back, or a request for the
    CAS to compute it. Before claims were parsed in a value-only namespace, every one of these
    was certified CORRECT — the verifier was producing the answer it was meant to check."""
    t, p = ir["task"]["kind"], ir["task"].get("params") or {}
    out: list[tuple[str, str]] = []
    if t == "evaluate" and p.get("expr"):
        out.append(("restates_target", str(p["expr"])))
    if t == "antiderivative":
        out.append(("integrate_call", f"integrate({p['integrand']}, {p.get('var', 'x')})"))
    if t == "definite_integral":
        out.append(("integrate_call", f"integrate({p['integrand']}, ({p.get('var', 'x')}, {p['a']}, {p['b']}))"))
        out.append(("latex_integral", f"\\int_{{{p['a']}}}^{{{p['b']}}} {p['integrand']} \\, d{p.get('var', 'x')}"))
    if t == "derivative" and p.get("f"):
        out.append(("diff_call", f"diff({p['f']}, {p.get('var', 'x')})"))
    if t == "limit" and p.get("expr"):
        out.append(("limit_call", f"limit({p['expr']}, {p.get('var', 'x')}, {p['to']})"))
    if t == "series_sum" and p.get("term"):
        out.append(("sum_object", f"Sum({p['term']}, ({p.get('var', 'k')}, {p.get('lo', 1)}, {p.get('hi', 'oo')}))"))
    for fn in ir.get("functions") or []:
        out.append(("own_function", f"{fn['name']}(1)"))
    return out


_STEP_EQUIV = {
    # the perturbation families of "Beyond the Answer Key" (arXiv:2608.28725), which measured
    # 75–85% false rejection of VALID non-canonical steps in LLM step verifiers
    "add_to_both_sides": lambda l, r: (f"({l}) + 7", f"({r}) + 7"),
    "scale_both_sides": lambda l, r: (f"2*({l})", f"2*({r})"),
    "swap_sides": lambda l, r: (r, l),
    "move_to_one_side": lambda l, r: (f"({l}) - ({r})", "0"),
}


# Why the step refuter may stay silent on a broken step, by design. A miss for any other
# reason is unexplained and fails a gate in scripts/check.py. The report used to print one
# fixed sentence ("the solver's own symbols `t`, `u`, or premises with no solution") whatever
# the sweep measured; checked one by one on 23 Sep it held, but the symbols were n, a, t, u, t
# and nothing would have noticed a new kind of miss.
ACCEPTED_MISS_REASONS = {
    "undeclared_symbol": "çözücünün kendi sembolü: özdeşlik mi çözülen denklem mi olduğu belirsiz, "
                         "bilerek atlanır (DECISIONS §3.3)",
    "premises_have_no_solution": "öncüllerin hiç çözümü yok (altın cevap boş küme): karşı örnek "
                                 "olabilecek nokta yok",
}


def _missed_step_reason(res, step_id: str, gold_is_empty) -> dict[str, str]:
    """Why a broken step did not stop a CORRECT verdict, read from the step layer's evidence.
    `gold_is_empty` is a thunk so the gold answer is only parsed when the reason needs it."""
    import re
    for layer in res.layers:
        if layer.layer != "steps.refute":
            continue
        for e in (layer.evidence or {}).get("steps", []):
            if e.get("id") != step_id:
                continue
            raw = e.get("reason") or (e.get("evidence") or {}).get("reason") or ""
            reason = raw.split(":", 1)[0] or str(e.get("status"))
            detail = ""
            if reason == "undeclared_symbol":
                m = re.search(r"\[([^\]]*)\]", raw)
                detail = m.group(1).replace("'", "") if m else ""
            elif reason == "premises_inconsistent_or_unsolved" and gold_is_empty():
                # "or_unsolved" alone could hide a solver failure; only a problem whose answer
                # is the empty set proves the premises are inconsistent
                reason = "premises_have_no_solution"
            return {"status": str(e.get("status")), "reason": reason, "detail": detail}
        return {"status": "absent", "reason": "step_not_in_evidence", "detail": ""}
    return {"status": "absent", "reason": "steps_layer_absent", "detail": ""}


def step_perturbations(items) -> dict[str, Any]:
    """Rewrite one `eq` step of a correct solution. A valid rewrite must never make the verdict
    INCORRECT (the refuter only refutes with a counterexample); a rewrite that makes the step
    false while leaving the final answer right is a D cell and should be caught."""
    import sympy as sp
    from mathverify.verifier import verify
    from mathverify.intake.structured import load_problem_ir
    from mathverify.normalize.parse import _split_top_level, build_namespace, parse_answer, preclean

    def _empty_gold(ir, gold) -> bool:
        try:
            return parse_answer("set", str(gold), build_namespace(load_problem_ir(ir))) == sp.S.EmptySet
        except Exception:  # noqa: BLE001
            return False
    out = {"equiv": Counter(), "broken": Counter(), "false_rejects": [], "missed_breaks": []}
    for it in items:
        if it["cell"] not in ("A", "B"):
            continue
        ir, sol, labels = split_for_verifier(it)
        try:
            base = verify(ir, sol).verdict
        except Exception:  # noqa: BLE001
            continue
        if base != "CORRECT":
            continue
        for idx, st in enumerate(sol.get("steps") or []):
            if st.get("kind") != "eq" or not st.get("claim"):
                continue
            parts = _split_top_level(preclean(st["claim"]))
            if len(parts) != 2 or parts[1][0] not in ("=", "=="):
                continue
            lhs, rhs = parts[0][1].strip(), parts[1][1].strip()
            for name, fn in _STEP_EQUIV.items():
                l2, r2 = fn(lhs, rhs)
                s2 = json.loads(json.dumps(sol))
                s2["steps"][idx]["claim"] = f"{l2} = {r2}"
                v = verify(ir, s2).verdict
                out["equiv"]["n"] += 1
                out["equiv"][v] += 1
                if v == "INCORRECT":
                    out["false_rejects"].append({"id": labels["id"], "step": st["id"], "family": name,
                                                 "claim": s2["steps"][idx]["claim"]})
            s3 = json.loads(json.dumps(sol))
            s3["steps"][idx]["claim"] = f"{lhs} = ({rhs}) + 1"
            res = verify(ir, s3)
            v = res.verdict
            out["broken"]["n"] += 1
            out["broken"][v] += 1
            if v == "CORRECT":
                why = _missed_step_reason(res, st["id"], lambda: _empty_gold(ir, labels["gold_answer"]))
                out["missed_breaks"].append({"id": labels["id"], "step": st["id"],
                                             "claim": s3["steps"][idx]["claim"], **why,
                                             "accepted": why["reason"] in ACCEPTED_MISS_REASONS})
            break                                         # one step per item keeps it tractable
    return {"equiv": dict(out["equiv"]), "broken": dict(out["broken"]),
            "false_rejects": out["false_rejects"], "missed_breaks": out["missed_breaks"]}


def run(items, limit_unique: int | None = None) -> dict[str, Any]:
    import sympy as sp
    from mathverify.verifier import verify
    from mathverify.intake.structured import load_problem_ir
    from mathverify.normalize.parse import build_namespace, parse_answer

    seen: set[str] = set()
    per_variant: dict[str, Counter] = {}
    false_accepts: list[dict] = []
    false_rejects: list[dict] = []
    skipped: Counter = Counter()
    n_problems = 0
    t0 = time.perf_counter()
    for it in items:
        if it["cell"] not in ("A", "B"):
            continue                                       # gold is the claim's truth only there
        ir, sol, labels = split_for_verifier(it)
        key = json.dumps(ir, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        if limit_unique and n_problems >= limit_unique:
            break
        n_problems += 1
        shape = ir.get("answer_shape", "scalar")
        kind = sol["claimed_answer"]["kind"]
        if kind in ("dne", "infinite", "none", "condition"):
            skipped["answer_kind_" + kind] += 1
            continue
        try:
            ns = build_namespace(load_problem_ir(ir))
            gold = parse_answer(kind, str(it["gold_answer"]), ns)
        except Exception as e:  # noqa: BLE001
            skipped[f"gold_unparsed:{type(e).__name__}"] += 1
            continue
        task = ir["task"]["kind"]
        mod_c = task == "antiderivative"
        wrong, equiv = variants(gold, shape, task, ns)
        ir_no_opt = dict(ir, options=None)
        for name, payload in non_answers(ir):
            s2 = {"claimed_answer": {"kind": "expression" if kind == "expression" else "value",
                                     "payload": payload, "option": None}, "steps": []}
            try:
                verdict = verify(ir_no_opt, s2).verdict
            except Exception as e:  # noqa: BLE001
                verdict = f"ERROR:{type(e).__name__}"
            c = per_variant.setdefault(f"non_answer:{name}", Counter())
            c["n"] += 1
            c[verdict] += 1
            if verdict == "CORRECT":
                false_accepts.append({"id": labels["id"], "task": task, "variant": f"non_answer:{name}",
                                      "payload": payload, "gold": str(it["gold_answer"]), "verdict": verdict})
        for label, group in (("wrong", wrong), ("equiv", equiv)):
            for name, v in group:
                ok = _differs(v, gold, mod_constant=mod_c) if label == "wrong" else _equal(v, gold, mod_constant=mod_c)
                if not ok:
                    skipped[f"{label}:{name}:not_proved"] += 1
                    continue
                payload = _pstr(v)
                vkind = "equation" if isinstance(v, sp.Equality) else (
                    "set" if isinstance(v, sp.FiniteSet) else
                    "interval" if isinstance(v, (sp.Interval, sp.Union)) else
                    ("count" if kind == "count" and v.is_Integer else ("value" if kind == "count" else kind)))
                s2 = {"claimed_answer": {"kind": vkind, "payload": int(v) if vkind == "count" else payload,
                                         "option": None}, "steps": []}
                try:
                    r = verify(ir_no_opt, s2)
                    verdict = r.verdict
                except Exception as e:  # noqa: BLE001
                    verdict = f"ERROR:{type(e).__name__}"
                c = per_variant.setdefault(f"{label}:{name}", Counter())
                c["n"] += 1
                c[verdict] += 1
                rec = {"id": labels["id"], "task": task, "variant": name, "payload": payload,
                       "gold": str(it["gold_answer"]), "verdict": verdict}
                if label == "wrong" and verdict == "CORRECT":
                    false_accepts.append(rec)
                if label == "equiv" and verdict == "INCORRECT":
                    false_rejects.append(rec)
    na_n = sum(c["n"] for k, c in per_variant.items() if k.startswith("non_answer:"))
    na_acc = sum(c.get("CORRECT", 0) for k, c in per_variant.items() if k.startswith("non_answer:"))
    wrong_n = sum(c["n"] for k, c in per_variant.items() if k.startswith("wrong:"))
    equiv_n = sum(c["n"] for k, c in per_variant.items() if k.startswith("equiv:"))
    equiv_unk = sum(c["UNKNOWN"] for k, c in per_variant.items() if k.startswith("equiv:"))
    wrong_unk = sum(c["UNKNOWN"] for k, c in per_variant.items() if k.startswith("wrong:"))
    return {"n_problems": n_problems, "seconds": time.perf_counter() - t0,
            "wrong": {"n": wrong_n, "false_accepts": len(false_accepts), "unknown": wrong_unk},
            "equiv": {"n": equiv_n, "false_rejects": len(false_rejects), "unknown": equiv_unk},
            "non_answer": {"n": na_n, "accepted": na_acc},
            "per_variant": {k: dict(v) for k, v in sorted(per_variant.items())},
            "false_accepts": false_accepts, "false_rejects": false_rejects, "skipped": dict(skipped)}


def render_md(s: dict[str, Any]) -> str:
    w, e = s["wrong"], s["equiv"]
    md = "# Metamorfik sağlamlık taraması (SymPy üretimli yanlış ve eşdeğer cevaplar)\n\n"
    md += f"Problem: **{s['n_problems']}** (A/B öğelerinin tekil IR'ları) · süre: {s['seconds']:.0f} s\n\n"
    md += (f"- **Yanlış cevap varyantı: {w['n']}** — yanlış onay (CORRECT): **{w['false_accepts']}** "
           f"(hedef 0) · UNKNOWN: {w['unknown']}\n")
    md += (f"- **Eşdeğer cevap varyantı: {e['n']}** — yanlış red (INCORRECT): **{e['false_rejects']}** "
           f"(hedef 0) · UNKNOWN (kaybedilen kapsama): {e['unknown']}\n\n")
    st = s.get("steps")
    if st:
        eq_, br = st["equiv"], st["broken"]
        md += "## Adım düzeyi: geçerli dönüşüm hata değildir, bozulan adım yakalanmalıdır\n\n"
        md += (f"- **Geçerli adım dönüşümü: {eq_.get('n', 0)}** (iki tarafa ekle, 2 ile çarp, taraf "
               f"değiştir, bir tarafa topla) — yanlış red (INCORRECT): **{len(st['false_rejects'])}** "
               f"(hedef 0; [10] LLM adım doğrulayıcılarında %75–85 ölçüyor) · UNKNOWN: {eq_.get('UNKNOWN', 0)}\n")
        missed = st["missed_breaks"]
        unexplained = [r for r in missed if not r.get("accepted")]
        md += (f"- **Bir tarafı +1 bozulan adım: {br.get('n', 0)}** — yakalanan (INCORRECT): "
               f"{br.get('INCORRECT', 0)} · kaçırılan (CORRECT): {len(missed)} · "
               f"UNKNOWN: {br.get('UNKNOWN', 0)} · **nedeni açıklanmayan kaçırma: {len(unexplained)}** "
               f"(hedef 0)\n")
        by_reason = Counter(r.get("reason", "?") for r in missed)
        for reason, k in sorted(by_reason.items(), key=lambda kv: (-kv[1], kv[0])):
            why = ACCEPTED_MISS_REASONS.get(reason, "**AÇIKLANMAMIŞ** — adım reddedicinin bu nedenle "
                                                    "susması beklenmiyor, incelenmeli")
            md += f"  - `{reason}`: {k} — {why}\n"
        for r in st["false_rejects"][:20]:
            md += f"  - yanlış red: {r['id']} {r['step']} `{r['family']}`: `{r['claim']}`\n"
        for r in missed[:20]:
            sym = f", sembol `{r['detail']}`" if r.get("detail") else ""
            md += (f"  - kaçırılan: {r['id']} {r['step']}: `{r['claim']}` — adım {r.get('status', '?')}, "
                   f"`{r.get('reason', '?')}`{sym}\n")
        md += "\n"
    md += "## Varyant türüne göre\n\n| Varyant | n | CORRECT | INCORRECT | UNKNOWN |\n|---|---|---|---|---|\n"
    for k, v in s["per_variant"].items():
        md += f"| `{k}` | {v['n']} | {v.get('CORRECT', 0)} | {v.get('INCORRECT', 0)} | {v.get('UNKNOWN', 0)} |\n"
    for title, rows in (("Yanlış onaylar", s["false_accepts"]), ("Yanlış redler", s["false_rejects"])):
        md += f"\n## {title} ({len(rows)})\n\n"
        md += "\n".join(f"- {r['id']} [{r['task']}] `{r['variant']}`: `{r['payload']}` (altın: `{r['gold']}`)"
                        for r in rows[:60]) or "yok"
        md += "\n"
    if s["skipped"]:
        md += "\n## Atlananlar (SymPy'nin kanıtlayamadığı varyantlar puanlanmaz)\n\n"
        md += "\n".join(f"- {k}: {v}" for k, v in sorted(s["skipped"].items())) + "\n"
    return md


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="en fazla bu kadar tekil problem")
    ap.add_argument("--out", default=str(ROOT / "reports"))
    args = ap.parse_args(argv)
    items = load_items(ROOT / "evalset" / "items")
    s = run(items, args.limit)
    s["steps"] = step_perturbations(items if not args.limit else items[:args.limit * 3])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "soundness_results.json").write_text(json.dumps(s, ensure_ascii=False, indent=1, default=str),
                                                encoding="utf-8")
    md = render_md(s)
    (out / "soundness_report.md").write_text(md, encoding="utf-8")
    print(md)
    return s


if __name__ == "__main__":
    main()
