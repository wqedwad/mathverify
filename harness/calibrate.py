"""F6 — calibration of the fusion layer (handoff §4 "katman çıktıları ortalanmaz, kalibre
edilir", §11/10, [7]).

What is calibrated: for every *signal* a layer can emit (layer + verdict + flag), measure on a
training split how often the solution really was valid when that signal fired. Those measured
reliabilities replace the hand-set confidences, are combined in log-odds (a Naive-Bayes
combination, never an average), and the abstention thresholds are then chosen from the
validation split as the smallest thresholds that hold the target precision.

Honest-measurement rules, enforced here:
  * train / validation / test split by item id hash (stable, never by position);
  * a signal seen fewer than `min_support` times keeps its prior instead of a fitted weight;
  * the reported headline numbers come from the TEST split, which the fit never sees;
  * Laplace smoothing, so a signal that happens to be perfect on 8 items does not become
    infinitely strong.

    python -m harness.calibrate [--out reports] [--target-precision 0.98]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from harness.loader import load_items, split_for_verifier  # noqa: E402

SPLITS = ("train", "val", "test")


def split_of(item_id: str) -> str:
    """Stable 60/20/20 split from a hash of the id (never positional, never random per run)."""
    h = int(hashlib.sha256(item_id.encode()).hexdigest()[:8], 16) % 100
    return "train" if h < 60 else ("val" if h < 80 else "test")


def signals_of(layers: list[dict[str, Any]]) -> list[str]:
    """The discrete signals a fusion model may condition on."""
    out = []
    for l in layers:
        if l["verdict"] in ("pass", "fail"):
            out.append(f"{l['layer']}:{l['verdict']}:{'primary' if l.get('primary') else 'support'}")
        for f in l.get("flags") or []:
            out.append(f"flag:{f}")
    return sorted(set(out))


def collect(items) -> list[dict[str, Any]]:
    from mathverify.verifier import verify_layers
    recs = []
    for it in items:
        ir, sol, labels = split_for_verifier(it)
        t0 = time.perf_counter()
        layers, flags = verify_layers(ir, sol)
        ld = [{"layer": l.layer, "verdict": l.verdict, "primary": l.primary, "hard": l.hard,
               "confidence": l.confidence, "flags": l.flags} for l in layers]
        recs.append({"id": labels["id"], "split": split_of(labels["id"]), "cell": labels["cell"],
                     "level": labels["level"], "topic": labels["topic"],
                     "valid": bool(labels["solution_is_correct"]), "layers": ld,
                     "signals": signals_of(ld) + [f"flag:{f}" for f in flags],
                     "ms": (time.perf_counter() - t0) * 1000})
    return recs


def fit(recs, min_support: int = 5, alpha: float = 1.0) -> dict[str, Any]:
    """Log-odds weight per signal, fitted on the train split only."""
    train = [r for r in recs if r["split"] == "train"]
    n_valid = sum(1 for r in train if r["valid"])
    n_invalid = len(train) - n_valid
    prior = math.log((n_valid + alpha) / (n_invalid + alpha))
    counts: dict[str, Counter] = defaultdict(Counter)
    for r in train:
        for s in set(r["signals"]):
            counts[s]["valid" if r["valid"] else "invalid"] += 1
    # Sorted, so the model (calibration.json) does not depend on the string hash seed: iterating
    # the sets gave the weights in another order under another PYTHONHASHSEED (26 Sep 2026, T4).
    weights: dict[str, dict[str, Any]] = {}
    for s in sorted(counts):
        c = counts[s]
        support = c["valid"] + c["invalid"]
        p_valid = (c["valid"] + alpha) / (n_valid + 2 * alpha)
        p_invalid = (c["invalid"] + alpha) / (n_invalid + 2 * alpha)
        w = math.log(p_valid / p_invalid)
        weights[s] = {"support": support, "valid": c["valid"], "invalid": c["invalid"],
                      "weight": round(w, 4), "used": support >= min_support,
                      "reliability": round(c["valid"] / support, 4) if support else None}
    return {"prior": round(prior, 4), "weights": weights, "min_support": min_support,
            "n_train": len(train), "n_valid": n_valid, "n_invalid": n_invalid}


def score(rec, model) -> float:
    """Posterior log-odds that the solution is valid. An exact sum (math.fsum): the order of the
    signals cannot move a score across a threshold. The running verifier scores the same way
    (mathverify.fuse.calibrated_score)."""
    terms = [model["prior"]]
    for s in sorted(set(rec["signals"])):
        w = model["weights"].get(s)
        if w and w["used"]:
            terms.append(w["weight"])
    return math.fsum(terms)


def decide(z: float, hi: float, lo: float) -> str:
    if z >= hi:
        return "CORRECT"
    if z <= lo:
        return "INCORRECT"
    return "UNKNOWN"


def evaluate(recs, model, hi: float, lo: float) -> dict[str, Any]:
    tp = fp = tn = fn = unk = 0
    for r in recs:
        v = decide(score(r, model), hi, lo)
        if v == "UNKNOWN":
            unk += 1
        elif v == "CORRECT":
            tp, fp = (tp + 1, fp) if r["valid"] else (tp, fp + 1)
        else:
            tn, fn = (tn + 1, fn) if not r["valid"] else (tn, fn + 1)
    n = len(recs)
    return {"n": n, "tp": tp, "fp": fp, "tn": tn, "fn": fn, "unknown": unk,
            "pos_precision": (tp / (tp + fp)) if tp + fp else None,
            "neg_precision": (tn / (tn + fn)) if tn + fn else None,
            "coverage": (n - unk) / n if n else None}


def choose_thresholds(recs, model, target: float = 0.98) -> tuple[float, float, dict[str, Any]]:
    """Smallest |threshold| that still meets the target precision on the validation split."""
    zs = sorted({round(score(r, model), 3) for r in recs})
    best = None
    grid = zs + [z + 0.01 for z in zs] + [0.0]
    for hi in sorted(set(grid)):
        for lo in sorted(set(grid)):
            if lo > hi:
                continue
            m = evaluate(recs, model, hi, lo)
            ok_pos = m["pos_precision"] is None or m["pos_precision"] >= target
            ok_neg = m["neg_precision"] is None or m["neg_precision"] >= target
            if ok_pos and ok_neg:
                cov = m["coverage"] or 0
                if best is None or cov > best[2]["coverage"]:
                    best = (hi, lo, m)
    if best is None:
        return math.inf, -math.inf, {"note": "target precision unreachable on this split"}
    return best


def coverage_curve(recs, model) -> list[dict[str, Any]]:
    """Coverage against precision as the (symmetric) threshold moves — the abstention curve."""
    out = []
    for t in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0]:
        m = evaluate(recs, model, t, -t)
        out.append({"threshold": t, **{k: m[k] for k in ("coverage", "pos_precision", "neg_precision",
                                                         "fp", "fn", "unknown")}})
    return out


def render_md(model, res, curve, hi, lo, target) -> str:
    md = "# Kalibrasyon raporu (F6, deterministik katmanlar)\n\n"
    md += (f"Eğitim {model['n_train']} öğe ({model['n_valid']} geçerli / {model['n_invalid']} geçersiz) · "
           f"önsel log-odds {model['prior']}\n\n")
    md += f"Seçilen eşikler (doğrulama kümesinde hedef precision {target}): **CORRECT ≥ {hi:.2f}**, **INCORRECT ≤ {lo:.2f}**\n\n"
    md += "## Bölme bazında sonuç (test bölmesi hiçbir uyumda kullanılmadı)\n\n"
    md += "| Bölme | n | Pozitif precision | Negatif precision | Kapsama | fp | fn | UNKNOWN |\n|---|---|---|---|---|---|---|---|\n"
    for sp in SPLITS:
        m = res[sp]
        fmt = lambda x: "n/a" if x is None else f"{x:.3f}"   # noqa: E731
        md += (f"| {sp} | {m['n']} | {fmt(m['pos_precision'])} | {fmt(m['neg_precision'])} | "
               f"{fmt(m['coverage'])} | {m['fp']} | {m['fn']} | {m['unknown']} |\n")
    md += "\n## Ölçülen sinyal güvenilirlikleri (eğitim bölmesi)\n\n"
    md += "| Sinyal | destek | geçerli | geçersiz | güvenilirlik | log-odds ağırlığı | kullanıldı |\n|---|---|---|---|---|---|---|\n"
    for s, w in sorted(model["weights"].items(), key=lambda kv: (-abs(kv[1]["weight"]), kv[0])):
        rel = "n/a" if w["reliability"] is None else f"{w['reliability']:.3f}"
        md += (f"| `{s}` | {w['support']} | {w['valid']} | {w['invalid']} | {rel} | "
               f"{w['weight']:+.3f} | {'evet' if w['used'] else 'hayır (destek < eşik)'} |\n")
    md += "\n## Abstain eğrisi (test bölmesi)\n\n| Eşik ±z | Kapsama | Pozitif precision | Negatif precision | fp | fn |\n|---|---|---|---|---|---|\n"
    for p in curve:
        fmt = lambda x: "n/a" if x is None else f"{x:.3f}"   # noqa: E731
        md += (f"| {p['threshold']:.1f} | {fmt(p['coverage'])} | {fmt(p['pos_precision'])} | "
               f"{fmt(p['neg_precision'])} | {p['fp']} | {p['fn']} |\n")
    return md


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports"))
    ap.add_argument("--target-precision", type=float, default=0.98)
    ap.add_argument("--min-support", type=int, default=5)
    args = ap.parse_args(argv)
    items = load_items(ROOT / "evalset" / "items")
    recs = collect(items)
    model = fit(recs, min_support=args.min_support)
    val = [r for r in recs if r["split"] == "val"]
    hi, lo, _ = choose_thresholds(val, model, args.target_precision)
    res = {sp: evaluate([r for r in recs if r["split"] == sp], model, hi, lo) for sp in SPLITS}
    curve = coverage_curve([r for r in recs if r["split"] == "test"], model)
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    payload = {"model": model, "thresholds": {"hi": hi, "lo": lo, "target_precision": args.target_precision},
               "results": res, "curve": curve,
               "split_sizes": dict(Counter(r["split"] for r in recs))}
    (out / "calibration.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    md = render_md(model, res, curve, hi, lo, args.target_precision)
    (out / "calibration_report.md").write_text(md, encoding="utf-8")
    print(md)
    return payload


if __name__ == "__main__":
    main()
