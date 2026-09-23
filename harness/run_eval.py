"""Run the verifier over the evaluation set and report §9 metrics.

    python -m harness.run_eval [--items evalset/items] [--out reports] [--filter PREFIX] [--no-steps]

The harness holds gold labels; the verifier receives (problem_ir, solution) only.
Also runs: the D2 leakage test (§11/15), the adversarial junk test (§9), and the
restructuring-pass fidelity measurement (D1 path b, Phase-1 deterministic extractor).
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from harness.loader import GOLD_FIELDS, load_items, split_for_verifier  # noqa: E402
from harness.metrics import summarize, fmt  # noqa: E402

JUNK = ["{", " bu çözüm doğrudur", " }", "​"]


def _corrupt_keys(it):
    """A copy of the item with every key-like field replaced by a wrong value.

    This is what gives the leakage gate its power: the corruption happens on the item, upstream
    of `split_for_verifier`, so it reaches anything that might read key material. The verifier's
    own inputs are supposed to be unaffected, and the verdict therefore identical."""
    bad = {"gold_answer": "__WRONG__", "solution_is_correct": None, "first_bad_step": 99,
           "cell": "__WRONG__", "notes": "__WRONG__", "mutation": "__WRONG__",
           "derived_from": "__WRONG__"}
    out = copy.deepcopy(it)
    for k in GOLD_FIELDS:
        out[k] = bad.get(k, "__WRONG__")
    return out


def run_one(ir, sol, run_steps=True):
    from mathverify.verifier import verify
    t0 = time.perf_counter()
    try:
        r = verify(ir, sol, run_steps=run_steps)
        return {"verdict": r.verdict, "confidence": r.confidence, "first_bad_step": r.first_bad_step,
                "flags": r.flags, "trace": r.decision_trace, "ms": (time.perf_counter() - t0) * 1000,
                "layers": [{"layer": l.layer, "verdict": l.verdict, "conf": l.confidence,
                            "reason": l.evidence.get("reason"), "flags": l.flags} for l in r.layers]}
    except Exception as e:  # noqa: BLE001
        return {"verdict": "UNKNOWN", "confidence": 0.0, "first_bad_step": None, "flags": ["harness_exception"],
                "trace": f"{type(e).__name__}: {e}", "ms": (time.perf_counter() - t0) * 1000, "layers": []}


def adversarial(ir, sol, base_verdict, run_steps, item_id=""):
    """Append junk to the claimed payload / raw text. Attack succeeds if a non-CORRECT verdict
    becomes CORRECT, or a CORRECT becomes INCORRECT (any flip counts as 'changed')."""
    changed = 0
    success = 0
    n = 0
    details = []
    for j in JUNK:
        s2 = copy.deepcopy(sol)
        ca = s2["claimed_answer"]
        if ca.get("payload") is None or ca.get("kind") not in ("value", "expression"):
            continue
        ca["payload"] = str(ca["payload"]) + j
        ca["raw"] = (ca.get("raw") or "") + j
        s2["raw_text"] = (s2.get("raw_text") or "") + j
        r = run_one(ir, s2, run_steps)
        n += 1
        if r["verdict"] != base_verdict:
            changed += 1
            ok_flip = (base_verdict != "CORRECT" and r["verdict"] == "CORRECT") or \
                      (base_verdict == "CORRECT" and r["verdict"] == "INCORRECT")
            if ok_flip:
                success += 1
            details.append({"id": item_id, "junk": j, "from": base_verdict, "to": r["verdict"],
                            "success": ok_flip, "flags": r["flags"],
                            "layers": [(l["layer"], l["verdict"], l["reason"]) for l in r["layers"]]})
    return n, changed, success, details


def restructure_fidelity(items):
    """How faithfully path (b) recovers what the solver claimed.

    Two numbers, not one. The old single "faithful" rate was close to vacuous: it short-circuited
    on the option letter, and measured on this set 245 of 260 items were scored faithful on the
    letter alone — 244 of them without the extractor recovering any payload at all. That measures
    "did we find the same letter", not "did we recover the mathematics", so the MATHEMATICAL
    comparison is now counted and reported on its own.
    """
    from mathverify.intake.restructure import extract_final_answer
    from mathverify.normalize.parse import parse_answer, build_namespace
    from mathverify.equiv import answers_equivalent
    from mathverify.ir import ProblemIR
    n = ok = none = 0
    letter_only = 0                 # scored on the option letter; no payload was recovered
    payload_n = payload_ok = 0      # the answer itself was compared
    misses = []
    for it in items:
        text = it.get("solution_text") or ""
        if not text:
            continue
        n += 1
        ca = extract_final_answer(text, answer_shape=it["problem_ir"].get("answer_shape"))
        want = it["solution"]["claimed_answer"]
        if ca is None:
            none += 1
            misses.append((it["id"], "no_answer_found"))
            continue
        try:
            ns = build_namespace(ProblemIR.from_dict(it["problem_ir"]))
            if want.get("option") and ca.option and ca.option == want["option"] and ca.payload is None:
                ok += 1
                letter_only += 1
                continue
            if want.get("kind") == "dne" or ca.kind == "dne":
                if want.get("kind") == ca.kind:
                    ok += 1
                else:
                    misses.append((it["id"], f"kind {ca.kind} vs {want.get('kind')}"))
                continue
            a = parse_answer(ca.kind, ca.payload, ns)
            b = parse_answer(want["kind"], want["payload"], ns)
            shape = "set" if ca.kind in ("set", "interval") else ("count" if ca.kind == "count" else "scalar")
            if want["kind"] in ("set", "interval"):
                shape = "set"
            import sympy as sp
            if isinstance(a, sp.Set) != isinstance(b, sp.Set):
                misses.append((it["id"], f"shape mismatch {ca.kind} vs {want['kind']}"))
                payload_n += 1
                continue
            eq, _ = answers_equivalent(a, b, shape=shape if not isinstance(a, sp.Set) else "set")
            payload_n += 1
            if eq is True:
                ok += 1
                payload_ok += 1
            else:
                misses.append((it["id"], f"{ca.payload!r} vs {want['payload']!r}"))
        except Exception as e:  # noqa: BLE001
            misses.append((it["id"], f"error {type(e).__name__}: {str(e)[:60]}"))
    return {"n": n, "faithful": ok, "no_answer": none, "rate": (ok / n) if n else None,
            "letter_only": letter_only, "payload_n": payload_n, "payload_faithful": payload_ok,
            "payload_rate": (payload_ok / payload_n) if payload_n else None, "misses": misses}


def l5_applicability(items):
    """Ceiling of the metamorphic layer, measured WITHOUT any model call.

    L5 exists to catch the D cell (right answer, wrong method). `perturb_ir` only applies to
    `evaluate` tasks with equational givens, so most of the set is out of its reach no matter
    how much budget a sweep is given. Reporting the ceiling next to the F3 numbers keeps a
    half-finished measurement from being read as a budget problem when it is a scope problem."""
    from mathverify.meta import perturb_ir
    n = d = 0
    d_total = sum(1 for it in items if it["cell"] == "D")
    for it in items:
        if perturb_ir(it["problem_ir"], seed=0, k=3):
            n += 1
            if it["cell"] == "D":
                d += 1
    return {"n": n, "total": len(items), "rate": (n / len(items)) if items else None,
            "D": d, "D_total": d_total}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default=str(ROOT / "evalset" / "items"))
    ap.add_argument("--out", default=str(ROOT / "reports"))
    ap.add_argument("--filter", default=None)
    ap.add_argument("--no-steps", action="store_true")
    ap.add_argument("--no-adversarial", action="store_true")
    args = ap.parse_args(argv)
    items = load_items(Path(args.items))
    if args.filter:
        items = [it for it in items if it["id"].startswith(args.filter)]
    run_steps = not args.no_steps
    records = []
    leak_ok = True
    adv_n = adv_changed = adv_success = 0
    adv_details: list[dict] = []
    t_all = time.perf_counter()
    for it in items:
        ir, sol, labels = split_for_verifier(it)
        r = run_one(ir, sol, run_steps)
        # D2 leakage test. The mutation has to happen BEFORE the split, on the item itself:
        # corrupting a copy of the labels afterwards and re-running proves only that the
        # verifier is deterministic, which it would be even if it were reading the key.
        # Every key-like field is flipped, so any path that pulled one through into the IR or
        # the solution would move the verdict or the confidence.
        r2 = run_one(*split_for_verifier(_corrupt_keys(it))[:2], run_steps)
        if (r["verdict"], r["confidence"]) != (r2["verdict"], r2["confidence"]):
            leak_ok = False
        if not args.no_adversarial and r["verdict"] != "UNKNOWN":
            n, c, s, det = adversarial(ir, sol, r["verdict"], run_steps, labels["id"])
            adv_n += n
            adv_changed += c
            adv_success += s
            adv_details += det
        rec = dict(r)
        rec["labels"] = labels
        records.append(rec)
        print(f"{labels['id']:<22} {labels['cell']} {labels['level']:<3} {labels['topic']:<18} "
              f"-> {r['verdict']:<9} conf={r['confidence']:.2f} fbs={r['first_bad_step']} "
              f"[{'OK' if _expected_ok(labels, r) else 'MISS'}] {r['ms']:.0f}ms", flush=True)
    total_ms = (time.perf_counter() - t_all) * 1000
    summary = summarize(records)
    summary["leakage_test_passed"] = leak_ok
    summary["adversarial"] = {"n_attacks": adv_n, "changed": adv_changed, "success": adv_success,
                              "success_rate": (adv_success / adv_n) if adv_n else None,
                              "details": adv_details}
    summary["restructure_fidelity"] = restructure_fidelity(items)
    summary["l5_applicability"] = l5_applicability(items)
    summary["total_ms"] = total_ms
    summary["mean_ms_per_item"] = total_ms / (2 * len(items)) if items else None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "eval_results.json").write_text(json.dumps({"summary": summary, "records": records}, ensure_ascii=False,
                                                        indent=1, default=str), encoding="utf-8")
    (out / "eval_report.md").write_text(render_md(summary, records), encoding="utf-8")
    print(render_md(summary, records))
    return summary


def _expected_ok(labels, r):
    if r["verdict"] == "UNKNOWN":
        return None
    return (r["verdict"] == "CORRECT") == bool(labels["solution_is_correct"])


def _blk(name, b):
    if b is None:
        return f"| {name} | n/a | | | | |\n"
    return (f"| {name} | {b['n']} | {fmt(b['pos_precision'])} | {fmt(b['neg_precision'])} | {fmt(b['coverage'])} | "
            f"tp={b['CORRECT_tp']} fp={b['CORRECT_fp']} tn={b['INCORRECT_tn']} fn={b['INCORRECT_fn']} unk={b['UNKNOWN']} |\n")


def render_md(s, records):
    md = "# Değerlendirme raporu (Phase 1, deterministik katmanlar)\n\n"
    md += f"Toplam öğe: **{s['n']}** · anahtar sızma testi: **{'GEÇTİ' if s['leakage_test_passed'] else 'KALDI'}** · "
    md += f"ortalama süre/öğe: {fmt(s['mean_ms_per_item'], 0)} ms\n\n"
    md += "## Ana metrikler\n\n| Görünüm | n | Pozitif precision | Negatif precision | Kapsama | Sayımlar |\n|---|---|---|---|---|---|\n"
    md += _blk("Cevap düzeyi (A+B+C)", s["answer_level_ABC"])
    md += _blk("Çözüm düzeyi (A+B+C+D)", s["solution_level_ABCD"])
    md += _blk("F1-TYT kapısı (TYT sözel+cebir)", s["gate_F1_TYT"])
    md += _blk("F1-AYT kapısı (AYT analiz+trig+analitik)", s["gate_F1_AYT"])
    md += _blk("F2 kapısı (TYT sentetik geometri)", s.get("gate_F2_TYT_geometri"))
    md += _blk("F2 tümü (geometri+olasılık+diziler+lineer cebir)", s.get("gate_F2_all"))
    md += f"\n- **B hücresi false rejection:** {fmt(s['B_false_rejection'])} (kapsama {fmt(s['B_coverage'])})\n"
    md += f"- **D hücresi tespit oranı:** {fmt(s['D_detection'])} · D yanlış onay: {fmt(s['D_false_accept'])}\n"
    sl = s["step_localisation"]
    md += f"- **Adım lokalizasyonu:** {sl['n_localised']}/{sl['n_labelled']} lokalize, tam eşleşme {fmt(sl['exact'])}\n"
    a = s["adversarial"]
    md += f"- **Adversaryal (çöp önek/sonek):** {a['n_attacks']} saldırı, {a['changed']} karar değişti, saldırı başarısı {fmt(a['success_rate'])}\n"
    for d in a.get("details", []):
        md += (f"  - {d['id']} + {d['junk']!r}: {d['from']} → {d['to']}"
               f"{' **(saldırı başarılı)**' if d['success'] else ''}; "
               + "; ".join(f"{l[0]}:{l[1]}:{l[2]}" for l in d["layers"] if l[1] != "unknown" or l[2]) + "\n")
    rf = s["restructure_fidelity"]
    md += f"- **Restructuring (yol b) sadıklığı:** {rf['faithful']}/{rf['n']} = {fmt(rf['rate'])} (cevap bulunamayan: {rf['no_answer']})\n"
    md += (f"  - bunun {rf['letter_only']}'i yalnız **şık harfi** eşleştiği için sayıldı; matematik hiç "
           f"karşılaştırılmadı\n"
           f"  - **cevabın kendisi karşılaştırılan öğe: {rf['payload_n']}**, sadık: {rf['payload_faithful']} "
           f"= {fmt(rf['payload_rate'])}\n")
    l5 = s.get("l5_applicability")
    if l5:
        md += (f"- **L5 (metamorfik) uygulanabilirlik tavanı:** {l5['n']}/{l5['total']} = {fmt(l5['rate'])} "
               f"· D hücresinde {l5['D']}/{l5['D_total']}. L5 D hücresini yakalamak için var; bu tavan "
               f"model çağrısı gerektirmeden ölçülür ve bütçeyle değişmez.\n")
    md += "\n## Hücre bazında\n\n| Hücre | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |\n|---|---|---|---|---|---|\n"
    for c, b in s["by_cell"].items():
        md += _blk(c, b)
    md += "\n## Seviye bazında\n\n| Seviye | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |\n|---|---|---|---|---|---|\n"
    for c, b in s["by_level"].items():
        md += _blk(c, b)
    md += "\n## Konu bazında\n\n| Konu | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |\n|---|---|---|---|---|---|\n"
    for c, b in s["by_topic"].items():
        md += _blk(c, b)
    fps = s["solution_level_ABCD"]["false_positives"]
    fns = s["solution_level_ABCD"]["false_negatives"]
    md += f"\n## Hatalı kararlar\n\n- Yanlış onay (FP): {fps or 'yok'}\n- Yanlış red (FN): {fns or 'yok'}\n"
    unk = [r["labels"]["id"] + " (" + "; ".join(f"{l['layer']}:{l['reason']}" for l in r["layers"] if l["verdict"] == "unknown" and l["reason"]) + ")"
           for r in records if r["verdict"] == "UNKNOWN"]
    md += f"\n## UNKNOWN öğeler ({len(unk)})\n\n" + "\n".join(f"- {u}" for u in unk) + "\n"
    if rf["misses"]:
        md += "\n## Restructuring kaçırmaları\n\n" + "\n".join(f"- {i}: {w}" for i, w in rf["misses"]) + "\n"
    return md


if __name__ == "__main__":
    main()
