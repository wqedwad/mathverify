"""Tek komutla bütün kapılar: testler, deterministik değerlendirme, Lean taraması, adversaryal.

    .venv/Scripts/python.exe scripts/check.py            # Windows: hızlı (testler + değerlendirme)
    .venv/Scripts/python.exe scripts/check.py --full     # + Lean taraması + adversaryal + kalibrasyon
    .venv/bin/python scripts/check.py [--full]           # Linux/macOS: aynı kapılar

Her kapı için ölçülen sayıyı ve hedefi yazar, herhangi biri düşerse çıkış kodu 1 olur.
`--full` çıktısını ayrıca `reports/check_full.log`a yazar (tarih, dal, commit ve kirli dosya
sayısıyla birlikte).
Hiçbir kapı tahmine dayanmaz: hepsi bu koşuda üretilmiş raporlardan okunur. Bir harness'ın
raporu koşudan önce silinir; harness çökerse ya da rapor yoksa/okunamıyorsa o harness'ın bütün
kapıları aynı adlarla FAIL olur.
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
REPORTS = ROOT / "reports"
ENV = dict(os.environ, PYTHONUTF8="1")


def venv_python(root: Path, windows: bool | None = None) -> str:
    """The project venv's interpreter (`Scripts/python.exe` on Windows, `bin/python` elsewhere),
    or the running interpreter when that venv does not exist."""
    if windows is None:
        windows = os.name == "nt"
    p = root / ".venv" / ("Scripts/python.exe" if windows else "bin/python")
    return str(p) if p.exists() else sys.executable


PY = venv_python(ROOT)


def run(cmd: list[str], label: str) -> tuple[int, str]:
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(f"  {label}: {time.perf_counter() - t0:.0f} s (exit {p.returncode})")
    return p.returncode, p.stdout + p.stderr


def gate(name: str, value, target, ok: bool, unit: str = "") -> dict:
    return {"name": name, "value": value, "target": target, "ok": bool(ok), "unit": unit}


def harness_step(cmd: list[str], label: str, report: str, owned: tuple, build) -> list[dict]:
    """Run one harness that writes REPORTS/<report> and turn that report into its gates.

    check.py used to ignore the exit code and read whatever JSON was on disk. `reports/*.json`
    is git-ignored, so on a fresh clone a crashed harness crashed check.py, and with an older
    JSON present a crashed harness passed silently on the old numbers. The report is now
    deleted first; a non-zero exit, a missing report or one that cannot be read fails every
    gate in `owned` ((name, target) pairs, the same gates `build` returns on success), so the
    gate names and count do not depend on whether the harness ran.
    """
    path = REPORTS / report
    path.unlink(missing_ok=True)                 # a stale report must never stand in for this run
    rc, out = run(cmd, label)
    if rc != 0:
        why = f"çalışmadı (çıkış {rc})"
    elif not path.exists():
        why = "rapor yok"
    else:
        try:
            return build(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, KeyError, TypeError, AttributeError) as e:   # JSONDecodeError is a ValueError
            why = f"rapor okunamadı ({type(e).__name__})"
    print(f"    {label}: {why}")
    for line in [l for l in out.splitlines() if l.strip()][-5:]:
        print(f"    | {line}")
    return [gate(name, why, target, False) for name, target in owned]


EVAL_GATES = (("cevap düzeyi pozitif precision", 0.98), ("cevap düzeyi negatif precision", 0.98),
              ("kapsama", 0.85), ("B hücresi yanlış red", 0.10), ("anahtar sızma testi", True),
              ("çözüm düzeyi pozitif precision", "raporlanır"), ("D hücresi tespit", "raporlanır"),
              ("yol (b) cevabın kendisi karşılaştırılan öğe", "raporlanır"),
              ("L5 uygulanabilirlik tavanı", "raporlanır"))
LEAN_GATES = (("Lean erişilebilir", "evet, ≥1 sertifika"), ("Lean FP", 0), ("Lean sertifika", "raporlanır"),
              ("Lean junk-value sertifikası", 0))
ADVERSARIAL_GATES = (("saldırı başarısı", "< %2"), ("saldırı yüzeyleri", "cevap+şık+adım"))
SOUNDNESS_GATES = (("SymPy üretimli yanlış cevapta yanlış onay", 0),
                   ("SymPy üretimli eşdeğer cevapta yanlış red", 0),
                   ("cevap olmayan iddiada (soru/hesaplama) CORRECT", 0),
                   ("geçerli adım dönüşümünde yanlış red", 0),
                   ("nedeni açıklanmayan kaçırılan bozuk adım", 0))
CALIBRATION_GATES = (("kalibre test precision (poz/neg)", "raporlanır"),)


def eval_gates(res: dict) -> list[dict]:
    gates: list[dict] = []
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
    return gates


def lean_unreached(data: dict) -> list[str]:
    """Records whose statement did not (fully) reach Lean: `lean_reached` not True, or an error
    from prove_statement that starts with `lean_unavailable`. A record without a `statement`
    field counts as having one, so a report that drops these fields fails closed."""
    bad = []
    for r in list(data["records"]) + list(data.get("junk_probe") or []):
        if not r.get("statement", True):
            continue
        errors = r.get("errors") or []
        if r.get("lean_reached") is not True or any(str(e).startswith("lean_unavailable") for e in errors):
            bad.append(str(r.get("id") or r.get("label")))
    return bad


def lean_unanswered(rows) -> list[str]:
    """Statements Lean never judged: `lean_answered` not True (every attempt timed out, or a report
    without the field). A row without a statement never went to Lean and is skipped."""
    return [str(r.get("id") or r.get("label")) for r in rows
            if r.get("statement", True) and r.get("lean_answered") is not True]


def attempt_counts(r: dict) -> tuple[int, int] | None:
    """(n_unanswered, n_attempts) as harness.run_lean wrote them for a statement Lean answered, or
    None when either is missing or they are not a consistent count (a bool, a negative number, more
    unanswered attempts than attempts, or no attempt at all): fail closed."""
    n_un, n_att = r.get("n_unanswered"), r.get("n_attempts")
    if type(n_un) is not int or type(n_att) is not int or n_att < 1 or not 0 <= n_un <= n_att:
        return None
    return n_un, n_att


def was_proved(r: dict) -> bool:
    """Did a proof of this statement compile, so that its audit decided the certificate? Only an
    explicit `proved` False with no certificate says no; a row without the field counts as proved
    (fail closed: it must then carry its audit record)."""
    return r.get("proved") is not False or bool(r.get("clean")) or bool(r.get("certified"))


# prove._axioms_of's placeholder when `#print axioms` gave no verdict (harness.run_lean.AXIOMS_UNKNOWN;
# a test keeps them equal). Kept as a literal so this script does not import the formal layer.
AXIOMS_UNKNOWN = "<unknown>"


def unanswered_audit(r: dict) -> list[str] | None:
    """The audit probes of a proved statement that Lean did not answer (`audit_unanswered`, written
    by harness.run_lean: "vacuity", "no_hyp", "axioms"), [] for an unproved statement (never
    audited), or None when a proved statement carries no usable record (missing, or not a list of
    probe names): fail closed. A report written before run_lean recorded the field gives None for
    every proved statement. When the row also carries the raw audit (prove._audit's record), it is
    read with run_lean.audit_unanswered's own rule, so the derived field can add probes but never
    hide one: its `unanswered` list counts, and "axioms" is added when its `axioms` is not a list or
    holds AXIOMS_UNKNOWN (`#print axioms` unanswered; a row whose derived field said [] next to
    that passed before). A raw audit without its `unanswered` list is no usable record either."""
    if not was_proved(r):
        return []
    u = r.get("audit_unanswered")
    if not isinstance(u, list) or not all(isinstance(p, str) for p in u):
        return None
    if "audit" not in r:
        return u
    audit = r["audit"]
    raw = audit.get("unanswered") if isinstance(audit, dict) else None
    if not isinstance(raw, list):
        return None
    out = u + [str(p) for p in raw if str(p) not in u]
    axioms = audit.get("axioms")
    if (not isinstance(axioms, list) or AXIOMS_UNKNOWN in axioms) and "axioms" not in out:
        out.append("axioms")
    return out


def elaboration(r: dict) -> bool | None | str:
    """A statement's elaboration check as harness.run_lean recorded it (`elaborates`: the statement
    once with the body `sorry`, autoImplicit off): True (elaborates), False (Lean rejected the
    statement itself), None (Lean gave no verdict), or "missing" when the field is absent or not
    one of those (a report from before the check): fail closed."""
    if "elaborates" not in r:
        return "missing"
    e = r["elaborates"]
    return e if e is None or isinstance(e, bool) else "missing"


def lean_silence(rows) -> str | None:
    """Why a "0" from the FP or junk gate would not be a claim about every statement in `rows`, or
    None when it is. Lean must have answered every tactic attempt on every statement, and every
    audit probe of every proof among them:
    - "Lean cevap vermedi s/N": s of the N statements got no answer at all (`lean_answered`);
    - "kısmen cevap vermedi k/M deneme": of the M attempts on the statements Lean did answer, k got
      no answer (`n_unanswered`), e.g. one cheap tactic answered and every heavy one timed out;
    - "deneme sayımı yok u/N ifade": u answered statements carry no usable attempt count;
    - "denetim cevapsız a/P kanıtlanan ifade": of the P proved statements, a have an audit probe
      Lean did not answer (`audit_unanswered`), so their missing certificate is silence, not a
      verdict (a vacuous junk statement whose vacuity probe timed out);
    - "denetim kaydı yok d/P kanıtlanan ifade": d proved statements carry no usable audit record;
    - "derleme sondası cevapsız e/N ifade", "derleme kaydı yok e/N ifade": Lean gave no verdict on
      the elaboration check of e statements (`elaborates` None), or e carry no usable record of it;
    - "ifade Lean'de derlenmedi e/N" (not under "Lean ..."): Lean rejected e statements themselves
      (`elaborates` False), so every attempt on them failed on the statement, never on the claimed
      value, and each still counted as answered (reviewer's unelaborated_probe.py).
    """
    stmt = [r for r in rows if r.get("statement", True)]
    silent = lean_unanswered(stmt)
    counts = [attempt_counts(r) for r in stmt if r.get("lean_answered") is True]
    k = sum(c[0] for c in counts if c)
    m = sum(c[1] for c in counts if c)
    uncounted = sum(1 for c in counts if c is None)
    proved = [r for r in stmt if was_proved(r)]
    audits = [unanswered_audit(r) for r in proved]
    audit_silent = sum(1 for a in audits if a)
    audit_missing = sum(1 for a in audits if a is None)
    parts = []
    if silent:
        parts.append(f"cevap vermedi {len(silent)}/{len(stmt)}")
    if k:
        parts.append(f"kısmen cevap vermedi {k}/{m} deneme")
    if uncounted:
        parts.append(f"deneme sayımı yok {uncounted}/{len(stmt)} ifade")
    if audit_silent:
        parts.append(f"denetim cevapsız {audit_silent}/{len(proved)} kanıtlanan ifade")
    if audit_missing:
        parts.append(f"denetim kaydı yok {audit_missing}/{len(proved)} kanıtlanan ifade")
    elab = [elaboration(r) for r in stmt]
    if elab.count(None):
        parts.append(f"derleme sondası cevapsız {elab.count(None)}/{len(stmt)} ifade")
    if elab.count("missing"):
        parts.append(f"derleme kaydı yok {elab.count('missing')}/{len(stmt)} ifade")
    why = ["Lean " + ", ".join(parts)] if parts else []
    rejected = sum(1 for e in elab if e is False)
    if rejected:
        why.append(f"ifade Lean'de derlenmedi {rejected}/{len(stmt)}")
    return ", ".join(why) or None


def lean_gates(data: dict) -> list[dict]:
    # Without Lean the sweep still exits 0 with zero certificates, so "Lean FP = 0" and "no junk
    # probe certified" held vacuously and a box with no Lean showed 23/23. `lean_available` is
    # written by harness.run_lean (the REPL booted with Mathlib in this run); a report without it
    # counts as Lean not having run.
    lean = data["records"]
    if data.get("lean_available") is not True:
        return [gate(name, "hayır" if i == 0 else "Lean çalışmadı", target, False)
                for i, (name, target) in enumerate(LEAN_GATES)]
    # Lean can also be lost MID-RUN (REPL OOM-killed, respawn fails): the records after that
    # point are proved=False with a lean_unavailable error, and the gates passed on them
    # vacuously (simulated: "evet (1 sertifika)" and junk "0/17" with no junk statement
    # reaching Lean). Lean must still answer after the junk probe (`lean_available_end`) and
    # every statement must have reached it; a report without these fields fails too.
    unreached = lean_unreached(data)
    end_ok = data.get("lean_available_end") is True
    if unreached or not end_ok:
        n_stmt = sum(1 for r in list(lean) + list(data.get("junk_probe") or []) if r.get("statement", True))
        why = (f"yarıda kesildi (Lean'e ulaşmayan ifade {len(unreached)}/{n_stmt}, "
               f"sonda erişilebilir: {'evet' if end_ok else 'hayır'})")
        return [gate(name, why if i == 0 else "Lean yarıda kesildi", target, False)
                for i, (name, target) in enumerate(LEAN_GATES)]
    gates: list[dict] = []
    cert = [r for r in lean if r.get("clean")]
    fp = [r for r in cert if not r["answer_right"]]
    # A reached REPL can still judge nothing: when every tactic attempt on a statement timed out,
    # the junk probe read "0/17" without Lean having evaluated that junk statement. A "0" from
    # the FP and junk gates needs a real Lean answer on EVERY tactic attempt (`lean_answered` and
    # `n_unanswered` == 0, written by harness.run_lean; a missing field counts as unanswered) on
    # every statement it is about: each junk statement, and each item whose claimed value is
    # wrong. "Answered at least once" was not enough: one cheap tactic answered and all heavy ones
    # timed out still passed, although the heavy tactics are the ones that could have proved it.
    # A statement that IS proved gets its certificate from the audit (axioms, vacuity,
    # no-hypothesis probes), so every audit probe of such a proof needs a Lean verdict too
    # (`audit_unanswered` == [], written by harness.run_lean; a proved row without it fails): the
    # junk statement `x = 2 from 1/(x-2) = 0` compiles in the real sweep and only the vacuity
    # probe keeps it uncertified, so with that probe timed out "0/17" said nothing about it.
    # An item with a right value is exempt: timing out only costs it its certificate. Measured on
    # 24 Sep (two full Windows sweeps, 45 s timeout; both reports fed to this function): 0 of 869
    # attempts unanswered, 0/645 on the 50 wrong-answer items and 0/33 on the 3 junk statements,
    # slowest attempt 3.0 s. Audit rule, measured the same day: a new full Windows sweep (45 s)
    # has 0 of 122 proved statements (121 items + that junk statement) with an unanswered audit
    # probe, no wrong-answer item proved, the junk statement refused by an answered vacuity probe
    # (hypotheses contradictory), all four gates OK with 121 certificates. So the rule does not
    # fail a healthy run; a report from before `audit_unanswered` fails the junk gate ("denetim
    # kaydı yok 1/1": its junk rows carry no audit) and keeps FP 0 (no wrong-answer item proved).
    # An answer is not yet a verdict on the claimed VALUE: an attempt that fails because the
    # statement itself does not elaborate (a broken template's unknown identifier) carries a real
    # Lean error, so it counts as answered, and a wrong-answer item or junk statement made only of
    # such attempts read "FP 0" / "0/17". Each of those statements must also have `elaborates`
    # True (harness.run_lean: sent once with the body `sorry`, autoImplicit off; see lean_silence).
    # Measured 24 Sep on two new full Windows sweeps (45 s): all 175 statements elaborate (122
    # right-answer items, 50 wrong-answer items, 3 junk), sweep 79.6 / 79.8 s wall against 74 s
    # before (the 175 checks alone took 2.2-2.5 s in a separate probe), all four gates OK with 121
    # certificates, FP 0, junk 0/17; the previous full sweep's report (no
    # `elaborates`) fails FP ("derleme kaydı yok 50/50 ifade") and junk ("... 3/3 ifade").
    wrong = [r for r in lean if r.get("statement", True) and not r.get("answer_right")]
    silence = lean_silence(wrong)
    fp_value = len(fp)
    if silence:
        fp_value = silence + (f", FP {len(fp)}" if fp else "")
    gates.append(gate("Lean erişilebilir", f"evet ({len(cert)} sertifika)", "evet, ≥1 sertifika", bool(cert)))
    gates.append(gate("Lean FP", fp_value, 0, not fp and not silence))
    gates.append(gate("Lean sertifika", f"{len(cert)}/{len(lean)}", "raporlanır", True))
    junk = data.get("junk_probe") or []
    bad = [j["label"] for j in junk if j.get("certified")]
    value = f"{len(bad)}/{len(junk)}"
    silence = lean_silence(junk)
    if silence:
        value = silence + (f", sertifika {value}" if bad else "")
    gates.append(gate("Lean junk-value sertifikası", value, 0, bool(junk) and not bad and not silence))
    return gates


def adversarial_gates(adv: dict) -> list[dict]:
    gates: list[dict] = []
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
    return gates


def soundness_gates(sf: dict) -> list[dict]:
    gates: list[dict] = []
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
    return gates


def calibration_gates(cal: dict) -> list[dict]:
    t = cal["results"]["test"]
    return [gate("kalibre test precision (poz/neg)", f"{t['pos_precision']}/{t['neg_precision']}", "raporlanır", True)]


def pytest_problems(out: str) -> list[str]:
    """The FAILED/ERROR lines of a pytest run and its skip-reason totals. check.py printed only the
    last summary line, so a run with "1 failed ... 92 skipped" left no trace of which test failed
    or why Lean tests were skipped (26 Sep 2026: first Lean use after a resumed session)."""
    keep = ("FAILED ", "ERROR ", "SKIPPED ")
    return [l.strip() for l in out.splitlines() if l.startswith(keep)]


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
            # The log is already open for writing, so git sees it modified; counted, it made the
            # header say 1 on a clean tree (every log until 26 Sep 2026).
            own = log.relative_to(ROOT).as_posix()
            dirty = [l for l in _git("status", "--porcelain", "--", f":(exclude){own}").splitlines()
                     if l.strip()]
            print(f"check.py --full · {time.strftime('%Y-%m-%d %H:%M:%S')} · "
                  f"{_git('rev-parse', '--abbrev-ref', 'HEAD')} @ {_git('rev-parse', '--short', 'HEAD')} · "
                  f"commit edilmemiş değişiklik: {len(dirty)} dosya\n")
            return _main(args)
        finally:
            sys.stdout = out


# The first Lean start after a container restart read Mathlib from a cold disk for ~400 s (measured
# 26 Sep 2026), longer than the 300 s the Lean tests wait before skipping: a --full run right after a
# restart skipped 87 Lean tests and failed one. The warm-up waits once, up to 15 min, outside the gates.
# It owns its client: lean_available(timeout=900) bounded only the probe, `import Mathlib` still had
# the client's 300 s boot budget, and the warm-up gave up after 302 s on a real restart (26 Sep 2026).
_LEAN_WARMUP = ("import sys\nfrom mathverify.formal.lean_client import LeanClient\n"
                "c = LeanClient(boot_timeout=900)\n"
                "try:\n"
                "    ok = c.run('example : (2 : Nat) + 2 = 4 := by norm_num', timeout=120).clean\n"
                "except Exception:\n"
                "    ok = False\n"
                "finally:\n"
                "    c.close()\n"
                "sys.exit(0 if ok else 1)\n")


def _main(args) -> int:
    gates: list[dict] = []

    if args.full:
        print("== Lean ısınma ==")
        run([PY, "-c", _LEAN_WARMUP], "lean_warmup")

    print("== testler ==")
    rc, out = run([PY, "-m", "pytest", "tests", "-q", "-rfEs", "-o", "addopts=-p no:cacheprovider"], "pytest")
    last = [l for l in out.splitlines() if "passed" in l or "failed" in l]
    gates.append(gate("birim testleri", last[-1].strip() if last else "?", "hepsi geçer", rc == 0))
    for line in pytest_problems(out)[:40]:
        print(f"    {line}")

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
    gates += harness_step([PY, "-m", "harness.run_eval", "--no-adversarial"], "run_eval", "eval_results.json",
                          EVAL_GATES, eval_gates)
    # Every routed task kind must have items, or the precision above says nothing about it.
    from harness.loader import load_items
    from mathverify.router import ROUTES
    kinds = {it["problem_ir"]["task"]["kind"] for it in load_items(ROOT / "evalset" / "items")}
    missing = sorted(set(ROUTES) - kinds)
    gates.append(gate("ölçülmeyen görev türü", missing or "yok", "yok", not missing))

    if args.full:
        print("== Lean taraması ==")
        gates += harness_step([PY, "-m", "harness.run_lean", "--timeout", "45"], "run_lean", "lean_results.json",
                              LEAN_GATES, lean_gates)

        print("== adversaryal ==")
        gates += harness_step([PY, "-m", "harness.adversarial"], "adversarial", "adversarial_results.json",
                              ADVERSARIAL_GATES, adversarial_gates)

        print("== metamorfik sağlamlık ==")
        gates += harness_step([PY, "-m", "harness.soundness_fuzz"], "soundness_fuzz", "soundness_results.json",
                              SOUNDNESS_GATES, soundness_gates)

        print("== kalibrasyon ==")
        gates += harness_step([PY, "-m", "harness.calibrate"], "calibrate", "calibration.json",
                              CALIBRATION_GATES, calibration_gates)

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
