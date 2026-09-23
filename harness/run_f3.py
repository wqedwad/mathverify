"""F3 evaluation: the fully automatic pipeline on raw questions.

    python -m harness.run_f3 [--limit N] [--ids a,b] [--filter PREFIX] [--workers 6]
                             [--no-l4] [--no-l5] [--pathb] [--include-exemplars] [--out reports]

Per item (labels stay in the harness, D2):
  auto   question_tr + options -> extract_ir (two-family round-trip) -> verify the item's
         STRUCTURED solution against the extracted IR (+ L4/L5) -> verdict
         compared with (a) the label and (b) the verdict obtained with the hand-written IR
  pathb  hand IR + solution_text -> LLM restructuring -> verify -> verdict vs label (fidelity
         of path b; D detection through restructured steps)
Metrics: extraction accept rate, round-trip scores, verdict agreement, precision/coverage of
the automatic pipeline, L4/L5 flag effects, cost and latency. Exemplar items (few-shot) are
excluded from the metrics unless --include-exemplars.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from harness.loader import load_items, split_for_verifier  # noqa: E402
from harness.metrics import summarize, fmt  # noqa: E402


def _expected_ok(labels, verdict):
    if verdict == "UNKNOWN":
        return None
    return (verdict == "CORRECT") == bool(labels["solution_is_correct"])


def _l6_record(pr):
    """What the F4 critic said, and what happened to it afterwards. The layer's own flag is the
    interesting part: an error report that a certificate overruled is a different outcome from
    one the meta-verifier confirmed, and only the per-item record can tell them apart."""
    rep = pr.critic.get("report") or {}
    layer = next((l for l in pr.result.layers if l.layer == "critic.steps"), None)
    return {"assessment": rep.get("assessment"),
            "first_bad_step": rep.get("first_bad_step") or None,
            "error_kind": rep.get("error_kind") or None,
            "answer_correct_regardless": rep.get("answer_correct_regardless"),
            "confidence": rep.get("confidence"),
            "meta": pr.critic.get("meta"),
            "outcome": (layer.evidence.get("reason") if layer else None),
            "flags": list(layer.flags) if layer else [],
            "errors": pr.critic.get("errors"),
            "cost_usd": round(pr.critic.get("cost_usd", 0.0), 4),
            "calls": pr.critic.get("calls", 0)}


def run_item(it, args):
    from mathverify.pipeline import run_pipeline
    from mathverify.verifier import verify
    from mathverify.extract import EXEMPLAR_IDS
    from mathverify.llm import LLMFatalError
    ir_hand, sol, labels = split_for_verifier(it)
    rec = {"labels": labels, "exemplar": it["id"] in EXEMPLAR_IDS}
    t0 = time.perf_counter()
    try:
        v_hand = verify(ir_hand, sol)
        rec["hand_verdict"] = v_hand.verdict
        pr = run_pipeline(it["question_tr"], it.get("options"), it["level"], solution=sol,
                          solver_family=getattr(args, "solver_family", None),
                          use_l4=not args.no_l4, use_l5=not args.no_l5, use_l6=not args.no_l6,
                          exclude_exemplar_ids=[it["id"]] if it["id"] in EXEMPLAR_IDS else None)
        r = pr.result
        ex = pr.extraction or {}
        last_rt = (ex.get("rounds") or [{}])[-1].get("roundtrip", {}) if ex else {}
        rec.update({
            "verdict": r.verdict, "confidence": r.confidence, "first_bad_step": r.first_bad_step, "flags": r.flags,
            "stage": pr.stage, "ir_accepted": bool(ex.get("accepted")), "ir_reason": ex.get("reason"),
            "ir_rounds": len(ex.get("rounds") or []),
            "judge_scores": {f: j.get("score") for f, j in last_rt.get("judges", {}).items()},
            "ir_task_kind": (pr.ir or {}).get("task", {}).get("kind"), "hand_task_kind": ir_hand["task"]["kind"],
            "l4": {k: pr.resolve.get(k) for k in ("family", "model", "verdict", "errors")} if pr.resolve else None,
            "l5": {k: pr.metamorphic.get(k) for k in ("applicable", "n", "failed", "passed", "undecided")} if pr.metamorphic else None,
            "l6": _l6_record(pr) if pr.critic else None,
            "cost_usd": round(pr.cost_usd, 4), "calls": pr.calls, "ms": pr.latency_ms,
            "layers": [{"layer": l.layer, "verdict": l.verdict, "reason": l.evidence.get("reason"), "flags": l.flags} for l in r.layers],
            "extracted_ir": pr.ir,
        })
        if args.pathb and it.get("solution_text"):
            pb = run_pipeline(it["question_tr"], it.get("options"), it["level"], ir=ir_hand,
                              solver_family=getattr(args, "solver_family", None),
                              solution_text=it["solution_text"], use_l4=False, use_l5=False)
            rec["pathb"] = {"verdict": pb.result.verdict, "confidence": pb.result.confidence,
                            "first_bad_step": pb.result.first_bad_step, "flags": pb.result.flags,
                            "answers_agree": (pb.restructure or {}).get("answers_agree"),
                            "downgraded": (pb.restructure or {}).get("downgraded_steps"),
                            "n_steps": len((pb.solution or {}).get("steps") or []),
                            "cost_usd": round(pb.cost_usd, 4), "calls": pb.calls}
    except LLMFatalError as e:
        # Credit or auth: not a measurement. Marked structurally (not by grepping a message
        # that truncation can mangle) so `main` stops the sweep on the FIRST one, from any
        # layer — IR extraction, L4, L5, the critic or the Lean prover.
        rec.update({"verdict": "UNKNOWN", "confidence": 0.0, "first_bad_step": None,
                    "flags": ["llm_fatal"], "fatal": f"{type(e).__name__}: {e}",
                    "error": f"{type(e).__name__}: {e}", "cost_usd": 0.0, "calls": 0,
                    "ms": (time.perf_counter() - t0) * 1000})
    except Exception as e:  # noqa: BLE001
        rec.update({"verdict": "UNKNOWN", "confidence": 0.0, "first_bad_step": None, "flags": ["harness_exception"],
                    "error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-800:], "cost_usd": 0.0,
                    "calls": 0, "ms": (time.perf_counter() - t0) * 1000})
    return rec


def render_md(s, records, args):
    n = len(records)
    md = "# F3 raporu — tam otomatik hat (soru metni → IR → sertifikalar → L4/L5)\n\n"
    md += f"Öğe: **{n}** (örnekler {'dahil' if args.include_exemplars else 'hariç'}) · L4 {'kapalı' if args.no_l4 else 'açık'} · L5 {'kapalı' if args.no_l5 else 'açık'}\n\n"
    acc = [r for r in records if r.get("ir_accepted")]
    md += "## IR çıkarımı (L0/L1)\n\n"
    md += f"- Kabul (round-trip iki aile ≥ 9): **{len(acc)}/{n} = {fmt(len(acc)/n if n else None)}**\n"
    reasons = Counter(r.get("ir_reason") for r in records if not r.get("ir_accepted"))
    md += f"- Reddedilme nedenleri: {dict(reasons) if reasons else 'yok'}\n"
    rounds = Counter(r.get("ir_rounds") for r in records)
    md += f"- Tur sayısı dağılımı (1 = onarım yok): {dict(sorted(rounds.items()))}\n"
    sc = {}
    for r in acc:
        for f, v in (r.get("judge_scores") or {}).items():
            sc.setdefault(f, []).append(v)
    md += "- Ortalama round-trip puanı: " + ", ".join(f"{f}: {sum(x for x in v if x is not None)/max(1,len([x for x in v if x is not None])):.2f}" for f, v in sc.items()) + "\n"
    same_kind = sum(1 for r in acc if r.get("ir_task_kind") == r.get("hand_task_kind"))
    md += f"- Görev türü elle yazılanla aynı: {same_kind}/{len(acc)}\n"
    agree = sum(1 for r in acc if r.get("verdict") == r.get("hand_verdict"))
    md += f"- **Karar uyumu (çıkarılan IR vs elle IR, kabul edilenlerde): {agree}/{len(acc)} = {fmt(agree/len(acc) if acc else None)}**\n"
    md += "\n## Otomatik hattın kararları (etiketlere karşı)\n\n| Görünüm | n | Pozitif precision | Negatif precision | Kapsama | Sayımlar |\n|---|---|---|---|---|---|\n"
    from harness.run_eval import _blk
    md += _blk("Cevap düzeyi (A+B+C)", s["answer_level_ABC"])
    md += _blk("Çözüm düzeyi (A+B+C+D)", s["solution_level_ABCD"])
    md += f"\n- B hücresi false rejection: {fmt(s['B_false_rejection'])} · D tespit: {fmt(s['D_detection'])}\n"
    unk = Counter()
    for r in records:
        if r.get("verdict") == "UNKNOWN":
            unk[r.get("stage") or "?"] += 1
    md += f"- UNKNOWN kaynakları: {dict(unk) if unk else 'yok'}\n"
    md += "\n## L4 / L5 sinyalleri\n\n"
    fl = Counter()
    for r in records:
        for f in r.get("flags", []):
            if f.startswith(("l4_", "l5_", "ir_", "roundtrip")):
                fl[f] += 1
    md += "- Bayraklar: " + ", ".join(f"{k}: {v}" for k, v in sorted(fl.items())) + "\n"
    l4v = Counter((r.get("l4") or {}).get("verdict") for r in records if r.get("l4"))
    md += f"- L4 yeniden çözücünün kendi çözümünün deterministik kararı: {dict(l4v)}\n"
    l5 = [r["l5"] for r in records if r.get("l5") and r["l5"].get("applicable")]
    if l5:
        md += f"- L5 uygulanabilen öğe: {len(l5)}; başarısız yöntem (≥2/3): {sum(1 for x in l5 if x['failed'] >= 2)}; D hücresinde yakalanan: " \
              f"{sum(1 for r in records if r['labels']['cell']=='D' and 'l5_method_failed' in r.get('flags', []))}/{sum(1 for r in records if r['labels']['cell']=='D' and r.get('l5') and r['l5'].get('applicable'))}\n"
    l6 = [r["l6"] for r in records if r.get("l6")]
    if l6:
        md += "\n## L6 kritik + meta-doğrulama (F4)\n\n"
        md += f"- Kritik çalışan öğe: {len(l6)} · LLM çağrısı: {sum(x['calls'] for x in l6)} · " \
              f"maliyet: ${sum(x['cost_usd'] for x in l6):.2f}\n"
        md += f"- Değerlendirme: {dict(Counter(x['assessment'] for x in l6))}\n"
        md += f"- Sonuç: {dict(Counter(x['outcome'] for x in l6))}\n"
        md += f"- Meta-doğrulayıcı: {dict(Counter(str(x['meta']) for x in l6 if x['assessment'] == 'error_found'))}\n"
        # the number that decides whether F4 earns its place: does it catch the D cell without
        # refusing correct solutions?
        dcell = [r for r in records if r["labels"]["cell"] == "D" and r.get("l6")]
        caught = [r for r in dcell if "critic_error_confirmed" in r["l6"]["flags"]]
        right = [r for r in records if r["labels"]["solution_is_correct"] and r.get("l6")]
        wrongly = [r for r in right if "critic_error_confirmed" in r["l6"]["flags"]]
        md += f"- **D hücresi tespiti: {len(caught)}/{len(dcell)}**\n"
        md += f"- **Doğru çözümde yanlış suçlama: {len(wrongly)}/{len(right)}** (hedef 0)\n"
        overruled = [x for x in l6 if "critic_overruled_by_certificate" in x["flags"]]
        if overruled:
            md += f"- Sertifikanın iptal ettiği kritik raporu: {len(overruled)} " \
                  f"(adım kimlikleri: {[x['first_bad_step'] for x in overruled][:8]})\n"
    elif not args.no_l6:
        md += "\n## L6 kritik + meta-doğrulama (F4)\n\n- Hiçbir öğede çalışmadı.\n"

    if args.pathb:
        pb = [r for r in records if r.get("pathb")]
        md += "\n## Yol (b): serbest metin → LLM yeniden yapılandırma (elle IR ile)\n\n"

        def _block(rows, title):
            okb = sum(1 for r in rows if _expected_ok(r["labels"], r["pathb"]["verdict"]) is True)
            unkb = sum(1 for r in rows if r["pathb"]["verdict"] == "UNKNOWN")
            badb = sum(1 for r in rows if _expected_ok(r["labels"], r["pathb"]["verdict"]) is False)
            dd = [r for r in rows if r["labels"]["cell"] == "D"]
            det = sum(1 for r in dd if r["pathb"]["verdict"] == "INCORRECT")
            out = (f"- **{title}:** öğe {len(rows)} · doğru karar {okb} · UNKNOWN {unkb} · "
                   f"yanlış karar {badb} · D tespiti {det}/{len(dd)}\n")
            return out

        # An item whose LLM restructuring did not run fell back to the deterministic
        # answer-only extractor, which produces NO steps — so it cannot detect a D cell by
        # construction. Mixing those into one rate is how the first sweep reported "218 items,
        # 37 wrong decisions, D detection 3/39" for a path that had actually run on 34 items.
        real = [r for r in pb if r["pathb"]["n_steps"] > 0]
        fell_back = [r for r in pb if r["pathb"]["n_steps"] == 0]
        md += _block(pb, "Tümü (karışık)")
        md += _block(real, "Gerçekten yeniden yapılandırılan (adım üretildi)")
        if fell_back:
            md += (f"- Deterministik cevap-çıkarıcıya düşen: **{len(fell_back)}/{len(pb)}** — bunlarda adım "
                   f"yoktur, dolayısıyla D hücresi yapısal olarak yakalanamaz; yukarıdaki 'karışık' satır "
                   f"yol (b)'nin değil bu geri-düşmenin ölçümüdür.\n")
        md += f"- Cevap çapraz kontrolü uyuşmazlığı: {sum(1 for r in pb if r['pathb'].get('answers_agree') is False)}\n"
        md += f"- Nota indirgenen adımı olan öğe: {sum(1 for r in pb if r['pathb'].get('downgraded'))}\n"
        scope = sum(1 for r in pb if "answer_level_only" in (r["pathb"].get("flags") or []))
        md += (f"- Yalnız cevap düzeyinde doğrulanan (adım yok, `answer_level_only`): {scope}/{len(pb)}\n")
    cost = sum(r.get("cost_usd", 0) for r in records) + sum((r.get("pathb") or {}).get("cost_usd", 0) for r in records)
    ms = [r.get("ms", 0) for r in records]
    md += f"\n## Maliyet / süre\n\n- Toplam maliyet: **${cost:.2f}** · öğe başına ${cost/n:.3f}\n" if n else ""
    md += f"- Ortalama süre/öğe: {sum(ms)/n/1000:.1f} s · toplam LLM çağrısı: {sum(r.get('calls', 0) for r in records)}\n" if n else ""
    md += "\n## Hatalı / UNKNOWN öğeler\n\n"
    for r in records:
        ok = _expected_ok(r["labels"], r.get("verdict"))
        if ok is not True:
            md += (f"- {r['labels']['id']} ({r['labels']['cell']}): {r.get('verdict')} [hand={r.get('hand_verdict')}] "
                   f"ir={r.get('ir_accepted')}/{r.get('ir_reason')} kind={r.get('ir_task_kind')} vs {r.get('hand_task_kind')} "
                   f"flags={r.get('flags')} {('ERR ' + r['error']) if r.get('error') else ''}\n")
    return md


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default=str(ROOT / "evalset" / "items"))
    ap.add_argument("--out", default=str(ROOT / "reports"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--filter", default=None)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-l4", action="store_true")
    ap.add_argument("--no-l5", action="store_true")
    ap.add_argument("--no-l6", action="store_true", help="F4 kritik + meta-doğrulama katmanını kapat")
    ap.add_argument("--solver-family", choices=["anthropic", "meta"], default=None,
                    help="çözümleri üreten aile (DECISIONS §17). Verilmezse yargılayan katmanlar "
                         "varsayılana düşer ve her kayda `solver_family_unknown` bayrağı konur; "
                         "gerçek bir AI çözücünün çıktıları ölçülürken BU BAYRAK VERİLMELİDİR.")
    ap.add_argument("--max-cost", type=float, default=None,
                    help="toplam harcama bu dolar değerine ulaşınca taramayı durdur")
    ap.add_argument("--pathb", action="store_true")
    ap.add_argument("--include-exemplars", action="store_true")
    ap.add_argument("--tag", default="f3")
    args = ap.parse_args(argv)
    from mathverify.extract import EXEMPLAR_IDS
    items = load_items(Path(args.items))
    if args.ids:
        want = set(args.ids.split(","))
        items = [it for it in items if it["id"] in want]
    if args.filter:
        items = [it for it in items if it["id"].startswith(args.filter)]
    if not args.include_exemplars:
        items = [it for it in items if it["id"] not in EXEMPLAR_IDS]
    if args.limit:
        items = items[:args.limit]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    progress = out / f"{args.tag}_progress.jsonl"
    progress.write_text("", encoding="utf-8")
    records = []
    t_all = time.perf_counter()
    aborted = None
    spent = 0.0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_item, it, args): it for it in items}
        for k, fut in enumerate(as_completed(futs), start=1):
            rec = fut.result()
            records.append(rec)
            # A billing/auth failure is not a measurement: stop instead of burning the rest.
            # Primary signal is structural (`fatal`, set from LLMFatalError in run_item). The
            # substring scan is only a backstop for a provider wording the client has not
            # learned to classify yet, and it now reads the WHOLE reason: truncating it is how
            # this guard silently failed on the 18 Sep run (151 items burned, aborted=None).
            blob = (rec.get("ir_reason") or "") + " " + (rec.get("error") or "")
            fatal = rec.get("fatal") or (blob if any(
                w in blob.lower() for w in ("credit", "billing", "balance", "quota", "insufficient_quota")) else None)
            if fatal:
                aborted = str(fatal)[:300]
                print(f"\n!! DURDURULDU: sağlayıcı faturalama/kimlik hatası — {aborted}\n", flush=True)
                for f in futs:
                    f.cancel()
                break
            spent += rec.get("cost_usd", 0.0)
            # a spend cap is not an optimisation: an unattended sweep that loops or picks an
            # unexpectedly expensive effort can drain a balance, and the run is worth nothing
            # once it is out of money anyway
            if args.max_cost and spent >= args.max_cost:
                aborted = f"spend cap reached: ${spent:.2f} >= ${args.max_cost:.2f}"
                print("\n!! DURDURULDU: harcama sınırı — " + aborted + "\n", flush=True)
                for f in futs:
                    f.cancel()
                break
            lab = rec["labels"]
            line = (f"[{k}/{len(items)}] {lab['id']:<18} {lab['cell']} -> {rec.get('verdict'):<9} hand={rec.get('hand_verdict')} "
                    f"ir={rec.get('ir_accepted')} rounds={rec.get('ir_rounds')} scores={rec.get('judge_scores')} "
                    f"kind={rec.get('ir_task_kind')} flags={[f for f in rec.get('flags', []) if f.startswith(('l4','l5','ir_','round'))]} "
                    f"${rec.get('cost_usd', 0):.2f} (toplam ${spent:.2f}) {rec.get('ms', 0)/1000:.0f}s"
                    + (f" ERR {rec['error']}" if rec.get("error") else ""))
            print(line, flush=True)
            with progress.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({k_: v for k_, v in rec.items() if k_ not in ("extracted_ir", "tb")}, ensure_ascii=False, default=str) + "\n")
    records.sort(key=lambda r: r["labels"]["id"])
    summary = summarize(records)
    summary["total_ms"] = (time.perf_counter() - t_all) * 1000
    summary["aborted"] = aborted
    summary["spent_usd"] = round(spent, 4)
    (out / f"{args.tag}_results.json").write_text(json.dumps({"summary": summary, "records": records}, ensure_ascii=False,
                                                              indent=1, default=str), encoding="utf-8")
    md = render_md(summary, records, args)
    (out / f"{args.tag}_report.md").write_text(md, encoding="utf-8")
    print(md)
    return summary


if __name__ == "__main__":
    main()
