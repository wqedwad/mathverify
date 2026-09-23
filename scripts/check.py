"""Tek komutla bütün kapılar: testler, deterministik değerlendirme, Lean taraması, adversaryal.

    .venv/Scripts/python.exe scripts/check.py            # hızlı (testler + değerlendirme)
    .venv/Scripts/python.exe scripts/check.py --full     # + Lean taraması + adversaryal + kalibrasyon

Her kapı için ölçülen sayıyı ve hedefi yazar, herhangi biri düşerse çıkış kodu 1 olur.
`--full` çıktısını ayrıca `reports/check_full.log`a yazar (tarih, dal, commit ve kirli dosya
sayısıyla birlikte).
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
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


def pyflakes_findings(out: str, rc: int, root: Path) -> tuple[list[str], bool]:
    """(findings not waived by a `# noqa` on their own source line, pyflakes-did-not-run)."""
    findings, parsed = [], 0
    for line in out.splitlines():
        path, _, rest = line.partition(":")
        lineno = rest.split(":", 1)[0]
        if not lineno.isdigit():
            continue
        parsed += 1
        try:
            src_line = (root / path).read_text(encoding="utf-8").splitlines()[int(lineno) - 1]
        except (OSError, IndexError):
            src_line = ""
        if "noqa" not in src_line:
            findings.append(line.strip())
    # a non-zero exit with nothing parseable is pyflakes failing (e.g. not installed), not a pass
    return findings, rc != 0 and parsed == 0


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s: str) -> int:
        for st in self.streams:          # flushed per write: a 25-minute run is watched live
            st.write(s)
            st.flush()
        return len(s)

    def flush(self) -> None:
        for st in self.streams:
            st.flush()


def _git(*a: str) -> str:
    p = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return p.stdout.strip() if p.returncode == 0 else "?"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="Lean, adversaryal ve kalibrasyonu da koştur")
    args = ap.parse_args(argv)
    if not args.full:
        return _main(args)
    # The full run writes its own log. The 21/21 run of 23 Sep lived only in a session's temp
    # file while reports/check_full.log still said 12/12 from 19 Sep; the header ties the log
    # to the code it measured.
    log = ROOT / "reports" / "check_full.log"
    with log.open("w", encoding="utf-8") as fh:
        out = sys.stdout
        sys.stdout = _Tee(out, fh)
        try:
            dirty = [l for l in _git("status", "--porcelain").splitlines() if l.strip()]
            print(f"check.py --full · {time.strftime('%Y-%m-%d %H:%M:%S')} · "
                  f"{_git('rev-parse', '--abbrev-ref', 'HEAD')} @ {_git('rev-parse', '--short', 'HEAD')} · "
                  f"commit edilmemiş değişiklik: {len(dirty)} dosya\n")
            return _main(args)
        finally:
            sys.stdout = out


def _main(args) -> int:
    gates: list[dict] = []

    print("== testler ==")
    rc, out = run([PY, "-m", "pytest", "tests", "-q", "-o", "addopts=-p no:cacheprovider"], "pytest")
    last = [l for l in out.splitlines() if "passed" in l or "failed" in l]
    gates.append(gate("birim testleri", last[-1].strip() if last else "?", "hepsi geçer", rc == 0))

    print("== pyflakes ==")
    # Tests never reach many `except` branches; an undefined name there is a NameError waiting
    # for the one input that triggers it. pyflakes ignores `# noqa`, so a finding is waived only
    # when its own source line carries one (the sandbox's deliberate warm import).
    rc, out = run([PY, "-m", "pyflakes", "src", "harness", "scripts", "tests", "evalset/build"], "pyflakes")
    findings, unparsed = pyflakes_findings(out, rc, ROOT)
    gates.append(gate("pyflakes temiz", f"{len(findings)} bulgu" + (" (pyflakes çalışmadı)" if unparsed else ""),
                      0, not findings and not unparsed))
    for f in findings[:10]:
        print(f"    {f}")

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
    rf = s["restructure_fidelity"]
    gates.append(gate("yol (b) cevabın kendisi karşılaştırılan öğe", f"{rf['payload_faithful']}/{rf['payload_n']}",
                      "raporlanır", True))
    l5 = s.get("l5_applicability") or {}
    gates.append(gate("L5 uygulanabilirlik tavanı", f"{l5.get('n')}/{l5.get('total')}", "raporlanır", True))
    # Every routed task kind must have items, or the precision above says nothing about it.
    from harness.loader import load_items
    from mathverify.router import ROUTES
    kinds = {it["problem_ir"]["task"]["kind"] for it in load_items(ROOT / "evalset" / "items")}
    missing = sorted(set(ROUTES) - kinds)
    gates.append(gate("ölçülmeyen görev türü", missing or "yok", "yok", not missing))

    if args.full:
        print("== Lean taraması ==")
        rc, out = run([PY, "-m", "harness.run_lean", "--timeout", "45"], "run_lean")
        lean = json.loads((ROOT / "reports" / "lean_results.json").read_text(encoding="utf-8"))["records"]
        cert = [r for r in lean if r.get("clean")]
        fp = [r for r in cert if not r["answer_right"]]
        gates.append(gate("Lean FP", len(fp), 0, not fp))
        gates.append(gate("Lean sertifika", f"{len(cert)}/{len(lean)}", "raporlanır", True))
        junk = json.loads((ROOT / "reports" / "lean_results.json").read_text(encoding="utf-8")).get("junk_probe") or []
        bad = [j["label"] for j in junk if j.get("certified")]
        gates.append(gate("Lean junk-value sertifikası", f"{len(bad)}/{len(junk)}", 0, bool(junk) and not bad))

        print("== adversaryal ==")
        rc, out = run([PY, "-m", "harness.adversarial"], "adversarial")
        adv = json.loads((ROOT / "reports" / "adversarial_results.json").read_text(encoding="utf-8"))
        succ = adv["preserving"]["flipped"] + adv["changing"]["accepted_wrong"]
        rate = succ / max(1, adv["n_attacks"])
        gates.append(gate("saldırı başarısı", f"{rate:.3%}", "< %2", rate < 0.02))
        # The sweep used to attack ONE surface (the claimed payload, option letter stripped).
        # Narrowing it again would keep the rate at 0% while measuring almost nothing, so the
        # surfaces themselves are a gate.
        names = adv["per_attack"].keys()
        surfaces = {"cevap": any(not k.startswith(("mc:", "step:")) for k in names),
                    "şık": any(k.startswith("mc:") for k in names),
                    "adım": any(k.startswith("step:") for k in names)}
        gates.append(gate("saldırı yüzeyleri", ",".join(k for k, v in surfaces.items() if v),
                          "cevap+şık+adım", all(surfaces.values())))

        print("== metamorfik sağlamlık ==")
        rc, out = run([PY, "-m", "harness.soundness_fuzz"], "soundness_fuzz")
        sf = json.loads((ROOT / "reports" / "soundness_results.json").read_text(encoding="utf-8"))
        gates.append(gate("SymPy üretimli yanlış cevapta yanlış onay",
                          f"{sf['wrong']['false_accepts']}/{sf['wrong']['n']}", 0, sf["wrong"]["false_accepts"] == 0))
        gates.append(gate("SymPy üretimli eşdeğer cevapta yanlış red",
                          f"{sf['equiv']['false_rejects']}/{sf['equiv']['n']}", 0, sf["equiv"]["false_rejects"] == 0))
        gates.append(gate("cevap olmayan iddiada (soru/hesaplama) CORRECT",
                          f"{sf['non_answer']['accepted']}/{sf['non_answer']['n']}", 0, sf["non_answer"]["accepted"] == 0))
        stp = sf.get("steps") or {}
        gates.append(gate("geçerli adım dönüşümünde yanlış red",
                          f"{len(stp.get('false_rejects', []))}/{(stp.get('equiv') or {}).get('n', 0)}", 0,
                          not stp.get("false_rejects")))
        # A broken step may be missed only for a reason the refuter is designed to abstain on
        # (harness.soundness_fuzz.ACCEPTED_MISS_REASONS); a record without a measured reason
        # counts as unexplained.
        missed = stp.get("missed_breaks") or []
        unexplained = [m for m in missed if not m.get("accepted")]
        gates.append(gate("nedeni açıklanmayan kaçırılan bozuk adım",
                          f"{len(unexplained)}/{len(missed)}", 0, bool(stp) and not unexplained))

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
