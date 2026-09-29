"""K4: a real AI solver's own solutions, checked by the deterministic verifier.

    python -m harness.run_solver --family meta --max-cost 5 [--limit N] [--ids a,b] [--workers 4]
                                 [--effort xhigh] [--out reports] [--tag solver_meta]

Per item the solver of `--family` (the app's own solver, path (a): mathverify.resolve.solve_with_family)
gets the Turkish question, the options and the IR's notation hints, never the answer key, and writes
a structured solution. The deterministic verifier (certificates, step refuter, fusion; no LLM layer)
checks it against the item's hand-written IR. Only then, here in the harness, the solver's final
answer is compared with the key (D2: the key never enters the verification path):

  right      SymPy proves the claimed answer equal to the key
  wrong      SymPy proves it different
  undecided  neither could be proved (read by hand)

A CORRECT verdict on a wrong answer is a false acceptance, the number that matters. An INCORRECT
verdict on a right answer is listed for a person to read: the refuted step may really be wrong
(a right answer reached through a wrong step is an INCORRECT solution, DECISIONS §2), or the
refuter may be wrong. There is no solution-level label for these solutions, so the harness cannot
tell the two apart (HANDOFF K4).

A spend cap is required. A billing or credential failure (LLMFatalError) stops the run: it is not a
measurement (principle 10).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
import threading
import time
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from harness.loader import load_items, split_for_verifier  # noqa: E402

LABELS = ("right", "wrong", "undecided")


def _claimed_value(ir: dict[str, Any], solution: dict[str, Any]) -> tuple[str, Any]:
    """(kind, payload) of the solver's final answer; a bare option letter reads the option's text."""
    ca = solution.get("claimed_answer") or {}
    kind, payload = ca.get("kind") or "value", ca.get("payload")
    opts = ir.get("options") or {}
    opt = ca.get("option")
    if payload in (None, "") and isinstance(opt, str) and opt in opts:     # a list as the letter crashed
        payload = opts[opt]
        if kind == "option":
            kind = "value"
    return kind, payload


def _is_dne(kind: str, payload: Any) -> bool:
    """"The limit does not exist", however it is written: the `dne` kind, or a payload that is only
    one of the verifier's own DNE phrases (`DNE`, `limit yoktur`, …)."""
    from mathverify.intake.restructure import _DNE
    return kind == "dne" or (isinstance(payload, str) and _DNE.fullmatch(payload.strip().rstrip(".").strip()) is not None)


def _unwrap_singleton(c, g):
    """(c, g) made comparable: a one-member set against a scalar compares the member (the parser reads
    `{pi/3}` of kind `value` as a Python set, of kind `set` as a FiniteSet); Python sets become
    FiniteSets; a listing written without braces (`-1, 4`: a tuple, or a set holding one tuple) against
    a set of plain members becomes the set of its members (audit of 29 Sep 2026). Anything that does not
    convert (`{1, 2, ...}` holds an Ellipsis) is returned as it came: it crashed outside any try."""
    try:
        return _comparable(c, g)
    except Exception:  # noqa: BLE001
        return c, g


def _comparable(c, g):
    import sympy as sp

    def scalar(v):
        return isinstance(v, sp.Expr) and not isinstance(v, sp.MatrixBase)

    def member(v):
        if isinstance(v, (sp.FiniteSet, set, frozenset)) and len(v) == 1:
            m = next(iter(v))
            return m if scalar(m) else None
        return None
    if member(c) is not None and scalar(g):
        return member(c), g
    if member(g) is not None and scalar(c):
        return c, member(g)
    # two Python sets were never compared (set - set is no SymPy difference): as FiniteSets they are
    c, g = (sp.FiniteSet(*v) if isinstance(v, (set, frozenset)) else v for v in (c, g))

    def plain_set(v):
        return isinstance(v, sp.FiniteSet) and not any(isinstance(m, (sp.Tuple, tuple)) for m in v)

    def listing(v):
        if isinstance(v, (tuple, list, sp.Tuple)):
            return sp.FiniteSet(*v)
        if isinstance(v, sp.FiniteSet) and len(v) == 1 and isinstance(next(iter(v)), sp.Tuple):
            return sp.FiniteSet(*next(iter(v)))
        return None
    if plain_set(g) and listing(c) is not None:
        c = listing(c)
    elif plain_set(c) and listing(g) is not None:
        g = listing(g)
    return c, g


def _sequence_label(c, g, *, scale_free: bool, admissible=None) -> tuple[str, str] | None:
    """A tuple or list answer ((16, 14), [1, 1]) against the key's, element by element. An eigenvector
    is right up to a nonzero factor, so a different one is not proved wrong."""
    from harness.soundness_fuzz import _differs, _equal
    import sympy as sp
    try:
        c, g = [sp.sympify(x) for x in c], [sp.sympify(x) for x in g]
        if len(c) == len(g) and all(_equal(x, y) for x, y in zip(c, g)):
            return "right", "equal element by element"
        if scale_free:
            return "undecided", "an eigenvector is not compared up to its factor"
        if len(c) != len(g) or any(_differs(x, y, admissible=admissible) for x, y in zip(c, g)):
            return "wrong", "different element by element"
    except Exception:  # noqa: BLE001
        return None
    return None


def answer_label(ir: dict[str, Any], solution: dict[str, Any], gold: Any, gold_kind: str) -> tuple[str, str]:
    """(label, why): the solver's final answer against the key, decided only when SymPy proves it."""
    import sympy as sp
    from harness.soundness_fuzz import _differs, _equal, admissible_points
    from mathverify.intake.structured import load_problem_ir
    from mathverify.normalize.parse import build_namespace, parse_answer
    kind, payload = _claimed_value(ir, solution)
    task = (ir.get("task") or {}).get("kind")
    try:
        ns = build_namespace(load_problem_ir(ir))
    except Exception as e:  # noqa: BLE001
        return "undecided", f"IR unparsed: {type(e).__name__}"
    # A key of `DNE` and a claim of "limit yoktur" were `undecided` (K4, 28 Sep 2026: ayt-lim-009).
    # Nonexistence against a finite number is a proved difference; against an infinite limit it is a
    # matter of convention and stays undecided.
    g_dne, c_dne = _is_dne(gold_kind, gold), _is_dne(kind, payload)
    if g_dne or c_dne:
        if g_dne and c_dne:
            return "right", "both do not exist"
        other_kind, other = (kind, payload) if g_dne else (gold_kind, gold)
        try:
            v = parse_answer(other_kind if other_kind != "dne" else "value", str(other), ns)
        except Exception:  # noqa: BLE001
            return "undecided", "does not exist vs unparsed"
        if isinstance(v, sp.Expr) and v.is_number and v.is_finite:
            return "wrong", "does not exist vs a finite value"
        return "undecided", "does not exist vs a non-finite answer"
    if payload in (None, ""):
        return "undecided", "no answer"
    params = (ir.get("task") or {}).get("params") or {}
    if task == "synthetic_geometry" and "angle(" in str(params.get("target", "")):
        # angle() is in degrees: `70°` is 70, as the geometry certificate reads it. The generic parser
        # made it 7*pi/18 and three right answers were labelled wrong (tyt-geo-002/-008/-013).
        from mathverify.certify.geometry_numeric import strip_degree_marks
        gold, payload = strip_degree_marks(str(gold)), strip_degree_marks(str(payload))
    int_params = ()
    if task == "trig_solve":
        # a general solution's integer parameter, as the trig certificate declares it (ayt-trig-002)
        int_params = tuple(sp.Symbol(n_, integer=True) for n_ in ("k", "n"))
        ns = dict(ns, **{s_.name: s_ for s_ in int_params})
    mod_c = task == "antiderivative"
    var = ns.get(params.get("var") or "") if mod_c else None
    adm = admissible_points(ir)
    if mod_c:
        # the key is written `F + C` and was never parsed: `C` is the binomial in the parser's
        # namespace (ayt-int-005/-010/-014/-021). As in the antiderivative certificate, a trailing
        # `+ C` is dropped and any other `C` is a symbol set to 0.
        from mathverify.certify.calculus import _TRAILING_C
        ns = dict(ns, C=sp.Symbol("C"))
        gold, payload = _TRAILING_C.sub("", str(gold)), _TRAILING_C.sub("", str(payload))
    try:
        g = parse_answer(gold_kind, str(gold), ns)
    except Exception as e:  # noqa: BLE001
        return "undecided", f"key unparsed: {type(e).__name__}"
    if mod_c and isinstance(g, sp.Basic):
        g = g.subs(ns["C"], 0)
    for k in dict.fromkeys((kind, gold_kind)):
        try:
            # a JSON list stays a list: stringified, [-1, 4] read as the interval [-1, 4] (audit of 29 Sep 2026)
            raw = payload if isinstance(payload, list) or (k == "count" and isinstance(payload, int)) else str(payload)
            c = parse_answer(k, raw, ns)
        except Exception:  # noqa: BLE001
            continue
        if mod_c and isinstance(c, sp.Basic):
            c = c.subs(ns["C"], 0)
        if mod_c and isinstance(c, (set, frozenset)):
            # `{F + C}`: the trailing `+ C` sits before the brace and was never stripped (audit of 29 Sep 2026)
            c = {e.subs(ns["C"], 0) if isinstance(e, sp.Basic) else e for e in c}
        if isinstance(c, (tuple, list)) and isinstance(g, (tuple, list)):
            label = _sequence_label(c, g, scale_free=params.get("op") == "eigenvector", admissible=adm)
            if label:
                return label
            continue
        if int_params and any(getattr(v, "free_symbols", set()) & set(int_params) for v in (c, g)):
            # sets with a symbolic integer parameter: only the same set is decided. A difference of
            # two such sets is not proved by SymPy (k and n name the same integers)
            k_, n_ = int_params
            # renaming n to k is sound only when each side has one parameter: a key with k and n
            # independent is a larger set than a claim that couples them (audit of 29 Sep 2026)
            one = all(len({k_, n_} & getattr(v, "free_symbols", set())) <= 1 for v in (c, g))
            if one and isinstance(c, sp.Basic) and isinstance(g, sp.Basic) and c.xreplace({n_: k_}) == g.xreplace({n_: k_}):
                return "right", f"same general solution as {k}"
            return "undecided", "general solutions are not compared"
        # one value against the set of that one value ("çözümü kaçtır" keyed as {pi/3}): the member is
        # compared (ayt-trig-004, 29 Sep 2026). A set of two or more stays a set.
        c, g = _unwrap_singleton(c, g)
        try:
            if _equal(c, g, mod_constant=mod_c, var=var):
                return "right", f"equal as {k}"
            if _differs(c, g, mod_constant=mod_c, var=var, admissible=adm):
                return "wrong", f"different as {k}"
        except Exception:  # noqa: BLE001
            continue
        if isinstance(c, sp.Basic) and isinstance(g, sp.Basic) and c == g:
            return "right", f"identical as {k}"
    return "undecided", f"not proved ({kind} vs {gold_kind})"


def _request_lock(args, it: dict[str, Any], ir: dict[str, Any]):
    """One call at a time per distinct request. The A/B/C/D items of one question send the same
    request (280 items, 86 distinct requests); two of them in flight together were both paid for,
    since the cache is written only when a call returns. The second now waits and reads the first
    one's answer from the cache."""
    locks = getattr(args, "request_locks", None)
    if locks is None:
        return contextlib.nullcontext()
    from mathverify.resolve.cross_family import _solver_user_prompt
    key = _solver_user_prompt(it["question_tr"], it.get("options"), ir, None)
    with args.lock:
        return locks.setdefault(key, threading.Lock())


def run_item(it: dict[str, Any], args) -> dict[str, Any]:
    from mathverify.llm import LLMFatalError
    from mathverify.resolve import solve_with_family
    t0 = time.perf_counter()
    ir, key_solution, labels = split_for_verifier(it)
    rec: dict[str, Any] = {"id": it["id"], "cell": it["cell"], "level": it["level"], "topic": it["topic"],
                           "family": args.family}
    stop = getattr(args, "stop", None)
    if stop is not None and stop.is_set():       # the run was stopped: no new paid call
        return {**rec, "skipped": True}
    with _request_lock(args, it, ir):
        if stop is not None and stop.is_set():
            return {**rec, "skipped": True}
        try:
            r = solve_with_family(it["question_tr"], it.get("options"), ir, args.family, effort=args.effort,
                                  tag=f"solver_{args.family}")
        except LLMFatalError as e:
            # accounted for (and the run stopped) before the lock is released: an item waiting for
            # the same request must see the stop, not start a paid call of its own
            rec.update(fatal=f"{type(e).__name__}: {str(e)[:300]}", ms=(time.perf_counter() - t0) * 1000)
            _account(args, rec)
            return rec
        except Exception as e:  # noqa: BLE001  (a crash is recorded, the sweep goes on)
            rec.update(error=f"{type(e).__name__}: {str(e)[:200]}", tb=traceback.format_exc()[-1500:],
                       cost_usd=0.0, ms=(time.perf_counter() - t0) * 1000)
            return rec
    sol = r.get("solution")
    rec.update(model=r.get("model"), cost_usd=r.get("cost_usd", 0.0), calls=r.get("calls", 0),
               stop_reason=r.get("stop_reason"), errors=r.get("errors") or [], solution=sol,
               verdict=r.get("verdict"), flags=r.get("flags") or [], first_bad_step=r.get("first_bad_step"),
               downgraded_steps=r.get("downgraded_steps") or [], trace=r.get("trace"))
    if sol is not None:
        rec["n_steps"] = len(sol.get("steps") or [])
        # the key is read only now, after the verdict exists (D2)
        gold_kind = (key_solution.get("claimed_answer") or {}).get("kind") or "value"
        rec["answer"], rec["answer_why"] = answer_label(ir, sol, labels["gold_answer"], gold_kind)
        rec["claimed"] = _claimed_value(ir, sol)[1]
        rec["gold"] = labels["gold_answer"]
    rec["ms"] = (time.perf_counter() - t0) * 1000
    _account(args, rec)
    return rec


def _account(args, rec: dict[str, Any]) -> None:
    """Add the item's cost to the run's total in the worker itself and stop the run there, so no
    worker starts another paid call after the cap or a billing failure (the main thread sees the
    record only later)."""
    lock = getattr(args, "lock", None)
    if lock is None:
        return
    with lock:
        args.spent_so_far += rec.get("cost_usd", 0.0)
        if rec.get("fatal") or args.spent_so_far >= args.max_cost:
            args.stop.set()


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    solved = [r for r in records if r.get("solution") is not None]
    matrix = Counter((r.get("verdict") or "NONE", r.get("answer")) for r in solved)
    tp, fp = matrix[("CORRECT", "right")], matrix[("CORRECT", "wrong")]
    tn, fr = matrix[("INCORRECT", "wrong")], matrix[("INCORRECT", "right")]
    decided = [r for r in solved if r.get("verdict") in ("CORRECT", "INCORRECT")]
    labelled = [r for r in solved if r.get("answer") in ("right", "wrong")]
    return {
        "n": len(records), "solved": len(solved),
        "no_solution": sum(1 for r in records if r.get("solution") is None and not r.get("fatal")),
        "answers": dict(Counter(r.get("answer") for r in solved)),
        "verdicts": dict(Counter(r.get("verdict") or "NONE" for r in solved)),
        "matrix": {f"{v}|{a}": n for (v, a), n in sorted(matrix.items(), key=str)},
        "false_accepts": fp,
        "pos_precision": tp / (tp + fp) if tp + fp else None,
        "neg_precision_answer_level": tn / (tn + fr) if tn + fr else None,
        "coverage": len(decided) / len(solved) if solved else None,
        "solver_accuracy": (sum(1 for r in labelled if r["answer"] == "right") / len(labelled)) if labelled else None,
        "wrong_answer_caught": (tn / sum(1 for r in solved if r.get("answer") == "wrong"))
        if any(r.get("answer") == "wrong" for r in solved) else None,
        "cost_usd": round(sum(r.get("cost_usd", 0.0) for r in records), 4),
        "models": dict(Counter(r.get("model") for r in records if r.get("model"))),
    }


def _fmt(x) -> str:
    return "n/a" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def render_md(s: dict[str, Any], records: list[dict[str, Any]], args) -> str:
    md = f"# Gerçek çözücü ölçümü (K4): `{args.family}` ailesi\n\n"
    md += (f"Model(ler): {', '.join(f'`{m}` ({n})' for m, n in s['models'].items()) or 'yok'} · öğe {s['n']} · "
           f"çözüm üretilen {s['solved']} · çözümsüz {s['no_solution']} · harcama ${s['cost_usd']:.2f}"
           + (f" · **DURDURULDU: {s['aborted']}**" if s.get("aborted") else "") + "\n\n")
    md += ("Doğrulama yalnız deterministik (sertifikalar, adım reddedici, füzyon; LLM katmanı yok), öğenin el "
           "yazısı IR'ıyla. Cevap etiketi kararın ardından harness'ta: SymPy çözücünün cevabını anahtara eşit "
           "(`right`) ya da farklı (`wrong`) kanıtlarsa; kanıtlayamazsa `undecided`. Çözüm düzeyinde etiket yok.\n\n")
    md += "| Ölçüt | Değer |\n|---|---|\n"
    for name, key in (("**Yanlış onay** (CORRECT, cevap yanlış)", "false_accepts"),
                      ("Pozitif precision (cevap düzeyi)", "pos_precision"),
                      ("Negatif precision (cevap düzeyi; alt sınır, aşağıya bkz.)", "neg_precision_answer_level"),
                      ("Kapsama (CORRECT/INCORRECT kararı)", "coverage"),
                      ("Yanlış cevabı INCORRECT bulma oranı", "wrong_answer_caught"),
                      ("Çözücünün cevap doğruluğu (etiketlenenlerde)", "solver_accuracy")):
        md += f"| {name} | {_fmt(s[key])} |\n"
    md += "\n## Karar × cevap etiketi\n\n| Karar | right | wrong | undecided |\n|---|---|---|---|\n"
    for v in ("CORRECT", "INCORRECT", "UNKNOWN", "NONE"):
        row = [s["matrix"].get(f"{v}|{a}", 0) for a in LABELS]
        if any(row):
            md += f"| {v} | " + " | ".join(map(str, row)) + " |\n"
    fa = [r for r in records if r.get("verdict") == "CORRECT" and r.get("answer") == "wrong"]
    md += "\n## Yanlış onaylar\n\n" + ("yok\n" if not fa else "".join(
        f"- `{r['id']}`: iddia `{r.get('claimed')}`, anahtar `{r.get('gold')}`\n" for r in fa))
    fr = [r for r in records if r.get("verdict") == "INCORRECT" and r.get("answer") == "right"]
    md += ("\n## Doğru cevapta INCORRECT (elle okunacak)\n\nReddedilen adım gerçekten yanlış olabilir (doğru "
           "cevaba yanlış adımla varan çözüm INCORRECT'tir) ya da reddedici yanılıyor olabilir.\n\n")
    md += "yok\n" if not fr else "".join(
        f"- `{r['id']}`: ilk kötü adım {r.get('first_bad_step')}, bayraklar {sorted(r.get('flags') or [])[:6]}\n"
        for r in fr)
    un = [r for r in records if r.get("answer") == "undecided"]
    md += "\n## Cevabı etiketlenemeyenler\n\n" + ("yok\n" if not un else "".join(
        f"- `{r['id']}` ({r.get('verdict')}): iddia `{str(r.get('claimed'))[:80]}`, anahtar `{r.get('gold')}` "
        f"({r.get('answer_why')})\n" for r in un))
    bad = [r for r in records if r.get("solution") is None]
    md += "\n## Çözüm üretilemeyenler\n\n" + ("yok\n" if not bad else "".join(
        f"- `{r['id']}`: {(r.get('fatal') or r.get('error') or '; '.join(r.get('errors') or []) or '?')[:160]}\n"
        for r in bad))
    md += f"\nSüre: {s['total_ms'] / 1000:.0f} s · `--effort {args.effort}` · `--workers {args.workers}`\n"
    return md


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--family", choices=["anthropic", "meta"], required=True, help="çözümleri üreten aile")
    ap.add_argument("--max-cost", type=float, required=True, help="harcama bu dolara ulaşınca dur (zorunlu)")
    ap.add_argument("--items", default=str(ROOT / "evalset" / "items"))
    ap.add_argument("--out", default=str(ROOT / "reports"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--effort", default="xhigh")
    ap.add_argument("--tag", default=None, help="çıktı adı (varsayılan solver_<aile>)")
    args = ap.parse_args(argv)
    tag = args.tag or f"solver_{args.family}"
    items = load_items(Path(args.items))
    if args.ids:
        want = set(args.ids.split(","))
        items = [it for it in items if it["id"] in want]
    if args.limit:
        items = items[:args.limit]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    progress = out / f"{tag}_progress.jsonl"
    progress.write_text("", encoding="utf-8")
    records: list[dict[str, Any]] = []
    t_all = time.perf_counter()
    aborted, spent = None, 0.0
    args.stop, args.lock, args.spent_so_far, args.request_locks = threading.Event(), threading.Lock(), 0.0, {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_item, it, args): it for it in items}
        # After a stop the loop keeps collecting: a call already running when the run stopped is
        # paid for, so its record and cost belong in the report. Nothing new starts (run_item).
        for k, fut in enumerate(as_completed(futs), start=1):
            if fut.cancelled():
                continue
            rec = fut.result()
            if rec.get("skipped"):
                continue
            records.append(rec)
            spent += rec.get("cost_usd", 0.0)
            with progress.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({k_: v for k_, v in rec.items() if k_ != "tb"}, ensure_ascii=False, default=str) + "\n")
            if not aborted and rec.get("fatal"):
                aborted = rec["fatal"]
                print(f"\n!! DURDURULDU: sağlayıcı faturalama/kimlik hatası — {aborted}\n", flush=True)
            elif not aborted and spent >= args.max_cost:
                aborted = f"spend cap reached: ${spent:.2f} >= ${args.max_cost:.2f}"
                print("\n!! DURDURULDU: harcama sınırı — " + aborted + "\n", flush=True)
            if aborted:
                args.stop.set()
                for f in futs:
                    f.cancel()
                continue
            print(f"[{k}/{len(items)}] {rec['id']:<18} {rec['cell']} -> {str(rec.get('verdict')):<9} "
                  f"cevap={rec.get('answer')} adım={rec.get('n_steps')} ${rec.get('cost_usd', 0):.3f} "
                  f"(toplam ${spent:.2f}) {rec.get('ms', 0) / 1000:.0f}s"
                  + (f" ERR {'; '.join(rec.get('errors') or [])[:120]}" if rec.get("errors") else "")
                  + (f" ERR {rec['error']}" if rec.get("error") else ""), flush=True)
    records.sort(key=lambda r: r["id"])
    s = summarize(records)
    s["total_ms"] = (time.perf_counter() - t_all) * 1000
    s["aborted"] = aborted
    (out / f"{tag}_results.json").write_text(json.dumps({"summary": s, "records": records}, ensure_ascii=False,
                                                        indent=1, default=str), encoding="utf-8")
    md = render_md(s, records, args)
    (out / f"{tag}_report.md").write_text(md, encoding="utf-8")
    print(md)
    return s


if __name__ == "__main__":
    main()
