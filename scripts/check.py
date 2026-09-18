"""Tek komutla bütün kapılar: testler, deterministik değerlendirme, Lean taraması, adversaryal.

    .venv/Scripts/python.exe scripts/check.py            # hızlı (testler + değerlendirme)
    .venv/Scripts/python.exe scripts/check.py --full     # + Lean taraması + adversaryal + kalibrasyon

Her kapı için ölçülen sayıyı ve hedefi yazar, herhangi biri düşerse çıkış kodu 1 olur.
Hiçbir kapı tahmine dayanmaz: hepsi üretilmiş raporlardan okunur.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
if not Path(PY).exists():                       # non-Windows checkout
    PY = sys.executable
ENV = dict(os.environ, PYTHONUTF8="1")


def run(cmd: list[str], label: str) -> tuple[int, str]:
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(f"  {label}: {time.perf_counter() - t0:.0f} s (exit {p.returncode})")
    return p.returncode, p.stdout + p.stderr


def gate(name: str, value, target, ok: bool, unit: str = "") -> dict:
    return {"name": name, "value": value, "target": target, "ok": bool(ok), "unit": unit}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="Lean, adversaryal ve kalibrasyonu da koştur")
    args = ap.parse_args(argv)
    gates: list[dict] = []

    print("== testler ==")
    rc, out = run([PY, "-m", "pytest", "tests", "-q", "-o", "addopts=-p no:cacheprovider"], "pytest")
    last = [l for l in out.splitlines() if "passed" in l or "failed" in l]
    gates.append(gate("birim testleri", last[-1].strip() if last else "?", "hepsi geçer", rc == 0))

    print("== deterministik değerlendirme ==")
    rc, out = run([PY, "-m", "harness.run_eval", "--no-adversarial"], "run_eval")
    res = json.loads((ROOT / "reports" / "eval_results.json").read_text(encoding="utf-8"))
    s = res["summary"]
    a, so = s["answer_level_ABC"], s["solution_level_ABCD"]
    gates.append(gate("cevap düzeyi pozitif precision", a["pos_precision"], 0.98, (a["pos_precision"] or 0) >= 0.98))
    gates.append(gate("cevap düzeyi negatif precision", a["neg_precision"], 0.98, (a["neg_precision"] or 0) >= 0.98))
    gates.append(gate("kapsama", a["coverage"], 0.85, (a["coverage"] or 0) >= 0.85))
    gates.append(gate("B hücresi yanlış red", s["B_false_rejection"], 0.10, (s["B_false_rejection"] or 0) < 0.10))
    gates.append(gate("anahtar sızma testi", s["leakage_test_passed"], True, bool(s["leakage_test_passed"])))
    gates.append(gate("çözüm düzeyi pozitif precision", so["pos_precision"], "raporlanır", True))
    gates.append(gate("D hücresi tespit", s["D_detection"], "raporlanır", True))

    if args.full:
        print("== Lean taraması ==")
        rc, out = run([PY, "-m", "harness.run_lean", "--timeout", "45"], "run_lean")
        lean = json.loads((ROOT / "reports" / "lean_results.json").read_text(encoding="utf-8"))["records"]
        cert = [r for r in lean if r.get("clean")]
        fp = [r for r in cert if not r["answer_right"]]
        gates.append(gate("Lean FP", len(fp), 0, not fp))
        gates.append(gate("Lean sertifika", f"{len(cert)}/{len(lean)}", "raporlanır", True))

        print("== adversaryal ==")
        rc, out = run([PY, "-m", "harness.adversarial"], "adversarial")
        adv = json.loads((ROOT / "reports" / "adversarial_results.json").read_text(encoding="utf-8"))
        succ = adv["preserving"]["flipped"] + adv["changing"]["accepted_wrong"]
        rate = succ / max(1, adv["n_attacks"])
        gates.append(gate("saldırı başarısı", f"{rate:.3%}", "< %2", rate < 0.02))

        print("== kalibrasyon ==")
        rc, out = run([PY, "-m", "harness.calibrate"], "calibrate")
        cal = json.loads((ROOT / "reports" / "calibration.json").read_text(encoding="utf-8"))
        t = cal["results"]["test"]
        gates.append(gate("kalibre test precision (poz/neg)",
                          f"{t['pos_precision']}/{t['neg_precision']}", "raporlanır", True))

    print("\n== kapılar ==")
    width = max(len(g["name"]) for g in gates)
    for g in gates:
        mark = "OK  " if g["ok"] else "FAIL"
        print(f"  [{mark}] {g['name']:<{width}}  {g['value']}   (hedef: {g['target']})")
    failed = [g for g in gates if not g["ok"]]
    print(f"\n{len(gates) - len(failed)}/{len(gates)} kapı geçti")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
