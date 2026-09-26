"""Tek komutla bütün kapılar: testler, deterministik değerlendirme, Lean taraması, adversaryal.

    .venv/Scripts/python.exe scripts/check.py            # Windows: hızlı (testler + değerlendirme)
    .venv/Scripts/python.exe scripts/check.py --full     # + Lean taraması + adversaryal + kalibrasyon
    .venv/bin/python scripts/check.py [--full]           # Linux/macOS: aynı kapılar
    .venv/bin/python scripts/check.py --plan [--base B]  # hangi kontrol gerekli (DECISIONS §59)

Her kapı için ölçülen sayıyı ve hedefi yazar, herhangi biri düşerse çıkış kodu 1 olur.
Kademeli kural: yalnız hiçbir kodun okumadığı belgeler ve `reports/` altındaki üretilmiş raporlar
değiştiyse kontrol gerekmez; başka her değişiklik koddur ve birleştirmeden önce son hâlde bir
`--full` ister; karar verilemeyen durum da `--full` ister. `--plan` yalnız kararı yazar (çıkış 0:
başka kontrol gerekmez, 1: `--full` gerekli); hızlı koşu kararı kapılardan sonra hatırlatır.
`--full` çıktısını ayrıca `reports/check_full.log`a yazar (tarih, dal, commit ve kirli dosya
sayısıyla birlikte).
Hiçbir kapı tahmine dayanmaz: hepsi bu koşuda üretilmiş raporlardan okunur. Bir harness'ın
raporu koşudan önce silinir; harness çökerse ya da rapor yoksa/okunamıyorsa o harness'ın bütün
kapıları aynı adlarla FAIL olur.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
REPORTS = ROOT / "reports"
ENV = dict(os.environ, PYTHONUTF8="1")
# Inherited settings that would change what the gates measure and leave no trace in the log: extra
# pytest options (a `-k` deselects most of the suite and "birim testleri" still passes) and plugins,
# and the sandbox's in-process debugging mode (no process isolation, no hard timeouts).
for _var in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "MATHVERIFY_SANDBOX"):
    ENV.pop(_var, None)


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


def adversarial_note(path: Path) -> str | None:
    """One log line on how the sweep ran (not a gate): worker processes, sandbox calls that timed out
    or restarted, and the items attacked again alone because of them (harness.adversarial). None
    when the report is missing or unreadable (the gates already say so)."""
    try:
        adv = json.loads(path.read_text(encoding="utf-8"))
        return (f"    adversarial: {adv['workers']} süreç · sandbox zaman aşımı {adv['sandbox_timeouts']} · "
                f"yeniden başlatma {adv['sandbox_restarts']} · tek başına yeniden denenen {len(adv['rechecked'])}")
    except (OSError, ValueError, KeyError, TypeError):
        return None


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


# --------------------------------------------------------------------------- staged checking
# Which check a change needs (DECISIONS §59, user decision of 26 Sep 2026). A --full run took
# 59-77 min and three sessions spent most of 8-9 hours waiting, often after a documentation-only
# change. The rule: documentation that no code reads and the reports the checks write need no
# check; any other change is code and needs the quick check while working and one --full on the
# final state before it is merged into master; whatever cannot be decided needs the --full.
#
# This file names no document in a string (only in comments and docstrings): the rule below reads
# the string constants of every Python file, this one included, to find the documents code reads.

REPORT_LOG = "reports/check_full.log"
DOC_SUFFIX = ".md"
# Directories never scanned for Python code when git cannot list the files: the environment,
# caches and git's own.
_SKIP_DIRS = frozenset({".git", ".venv", "__pycache__", ".pytest_cache", ".hypothesis", "node_modules"})
# Where documentation lives: files at the repository root and everything under docs/. A .md file
# anywhere else sits next to code that may copy, hash or package it, which no scan of names can
# see: tests/test_cloud_scripts.py copies lean/ and src/ into its test beds, and the cloud scripts
# fingerprint every file under lean/ but its README. So it counts as code by its place.
DOC_DIRS = ("docs/",)
# Documents in those places that code reads without naming them in a Python string, with the
# reason; a key ending in "/" covers every document under that directory. None today.
# tests/doc_read_guard.py fails the test session when a test opens a document that is neither
# named nor covered here, and tests/test_staged_check.py fails when a shell script mentions or
# walks one that is not covered.
DOCS_READ_UNNAMED: dict[str, str] = {}
# A file name ending in .md inside a string: "BULUT.md", "docs/x.md", "*.md", the constant tail
# "_report.md" of f"{tag}_report.md". Built from DOC_SUFFIX so that the pattern's own text holds no
# such name.
_MD_TOKEN = re.compile(r"[\w.*?\[\]/\\-]*" + re.escape(DOC_SUFFIX) + r"(?!\w)", re.IGNORECASE)
_RUN_LINE = (r" · (?P<when>.+?) · (?P<branch>.+) @ (?P<commit>[0-9a-f]{4,40}) · "
             r"commit edilmemiş değişiklik: (?P<dirty>\d+) dosya")
_LOG_HEADER = re.compile(r"check\.py --full" + _RUN_LINE)
_LOG_END = re.compile(r"check\.py --full sonu" + _RUN_LINE)
_LOG_TOTAL = re.compile(r"(?P<ok>\d+)/(?P<n>\d+) kapı geçti")
_WORD = re.compile(r"\w")


class UnreadableSource(Exception):
    """A Python file the scan cannot parse: which documents it reads is unknown."""


def _git_run(root: Path, *a: str, timeout: float | None = None, env: dict | None = None):
    try:
        return subprocess.run(["git", *a], cwd=root, capture_output=True, timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _git_lines(root: Path, *a: str) -> list[str] | None:
    """git's NUL-separated output (`-z`: paths unquoted, whatever their characters) as a list,
    or None when git fails."""
    p = _git_run(root, *a)
    if p is None or p.returncode != 0:
        return None
    return [x for x in p.stdout.decode("utf-8", "replace").split("\0") if x]


def _git_value(root: Path, *a: str) -> str | None:
    p = _git_run(root, *a)
    if p is None or p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace").strip() or None


def is_report(path: str) -> bool:
    """A file the checks write: `reports/<name>.md` (a harness report, produced and never written
    by hand) or the --full log. A change to one is the output of a check, not a reason for one."""
    p = path.replace("\\", "/")
    head, _, name = p.rpartition("/")
    return p == REPORT_LOG or (head == "reports" and name.lower().endswith(DOC_SUFFIX))


def is_doc(path: str) -> bool:
    """A .md file in a documentation place (the root, DOC_DIRS): the only files that can be
    "belge". Everywhere else a .md file is code by its place."""
    p = path.replace("\\", "/")
    return (p.lower().endswith(DOC_SUFFIX) and not is_report(p)
            and ("/" not in p or p.startswith(DOC_DIRS)))


def read_unnamed(doc: str) -> str | None:
    """Why code reads `doc` without naming it (DOCS_READ_UNNAMED), or None."""
    d = doc.replace("\\", "/")
    for key, why in DOCS_READ_UNNAMED.items():
        if d == key or (key.endswith("/") and d.startswith(key)):
            return why
    return None


def python_sources(root: Path) -> list[Path]:
    """The Python files of the working tree: tracked, and untracked but not ignored (as git lists
    them, so a nested repository or worktree and ignored scratch are not the project's code).
    Without git, every .py under `root` outside _SKIP_DIRS and nested repositories."""
    listed = _git_lines(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.py")
    if listed is not None:
        return [root / p for p in sorted(set(listed)) if (root / p).is_file()]
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in _SKIP_DIRS and not (Path(d) / x / ".git").exists())
        out += [Path(d) / f for f in sorted(files) if f.endswith(".py")]
    return out


def code_strings(root: Path) -> list[tuple[str, str, bool]]:
    """(file:line, text, tail) of every string constant in the repository's Python code, f-string
    parts included. `tail` marks text appended to a value only known at run time: an f-string part
    after a {field}, the right side of `+`, the argument of `with_suffix`. Docstrings and other bare
    string statements are left out: like comments, they are prose (a test's docstring citing a
    document does not read it). Raises UnreadableSource for a file that cannot be read or parsed
    (parsed from bytes, as Python itself reads it: a UTF-8 BOM or a coding cookie is honoured)."""
    import ast
    import warnings
    out = []
    for f in python_sources(root):
        rel = f.relative_to(root).as_posix()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")        # invalid escapes etc. in the scanned files
                tree = ast.parse(f.read_bytes(), filename=str(f))
        except (OSError, SyntaxError, ValueError) as e:
            raise UnreadableSource(f"{rel}: {type(e).__name__}") from e
        prose, tails = set(), set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Expr):
                prose.add(id(n.value))
            elif isinstance(n, ast.JoinedStr):
                tails.update(id(v) for i, v in enumerate(n.values)
                             if i and isinstance(n.values[i - 1], ast.FormattedValue))
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                tails.add(id(n.right))
            elif isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "with_suffix":
                tails.update(id(a) for a in n.args)
        consts = sorted((n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                         and id(n) not in prose), key=lambda n: (n.lineno, n.col_offset))
        out += [(f"{rel}:{n.lineno}", n.value, id(n) in tails) for n in consts]
    return out


# What may stand right before a whole file name in a string: its start, a space, a quote, an opening
# bracket, a separator. Anything else ("}" of "{}.md", ")" of "%(n)s.md", "%" of "%s.md") means the
# name is completed at run time and only its ending is known.
_NAME_START = frozenset(" \t\n\"'`(,;:=<")


def doc_tokens(text: str, tail: bool = False) -> list[tuple[str, bool]]:
    """(token, suffix) for every file name ending in .md in `text`. `suffix` is True when only the
    ending is known (a tail, or a placeholder right before the token); after a printf placeholder
    the token's first letter is the conversion ("%s.md"), so it is dropped."""
    out = []
    for m in _MD_TOKEN.finditer(text):
        token, i = m.group(), m.start()
        before = text[i - 1] if i else ""
        suffix = tail if i == 0 else before not in _NAME_START
        if i and before in "%)":
            token = token[1:]
        out.append((token, suffix))
    return out


def names_doc(token: str, doc: str, suffix: bool = False) -> bool:
    """Does `token` name the document `doc` (a repository path)? Loosely, so that a doubt counts as
    a read. Case-insensitively (Windows opens BULUT.md for bulut.md), by the file name in any
    directory (`ROOT / "docs" / "X.md"` carries only "X.md"), and as the end of a longer name after
    a character that is not a letter or digit ("kurulum notu.md" leaves the token "notu.md"); a
    glob names what it matches ("*.md" every document); a suffix token names every document whose
    name ends with it ("_report.md"; the bare extension: every document). The bare extension as a
    whole token is a type test (`p.endswith(".md")`), not a name."""
    t = token.replace("\\", "/").lower()
    d = doc.replace("\\", "/").lower()
    base, tbase = d.rpartition("/")[2], t.rpartition("/")[2]
    if any(c in t for c in "*?["):
        return fnmatch.fnmatchcase(d, t) or fnmatch.fnmatchcase(base, tbase)
    if suffix:
        return base.endswith(tbase)
    if tbase == DOC_SUFFIX:
        return False
    return base == tbase or (base.endswith(tbase) and not _WORD.match(base[-len(tbase) - 1]))


def docs_named_by_code(root: Path, docs) -> dict[str, str]:
    """{document: why it counts as read} for the documents in `docs` that DOCS_READ_UNNAMED covers
    or that a string constant of the repository's Python code names (the first place found). A read
    document is code: a change to it can change what the checks or the verifier do. A name assembled
    without a constant that ends in .md (`"".join(...)`) is not seen here; in the tests
    tests/doc_read_guard.py catches it at run time. Raises UnreadableSource."""
    docs = sorted(set(docs))
    found = {d: f"adsız okuyucu: {read_unnamed(d)}" for d in docs if read_unnamed(d)}
    if len(found) == len(docs):
        return found
    for where, text, tail in code_strings(root):
        for token, suffix in doc_tokens(text, tail):
            for d in docs:
                if d not in found and names_doc(token, d, suffix):
                    found[d] = where
    return found


def changed_since(root: Path, rev: str) -> list[str] | None:
    """Files that differ between commit `rev` and the working tree: committed, staged and unstaged
    changes (`git diff <rev>` compares the commit with the working tree), deletions, both sides of
    a rename (--no-renames), and every untracked file that the repository's .gitignore files do not
    ignore (personal excludes and status.showUntrackedFiles hide nothing here). None if git fails."""
    tracked = _git_lines(root, "diff", "--name-only", "-z", "--no-renames", rev, "--")
    untracked = _git_lines(root, "ls-files", "--others", "--exclude-per-directory=.gitignore", "-z")
    if tracked is None or untracked is None:
        return None
    return sorted(set(tracked) | set(untracked))


def hidden_files(root: Path) -> list[str] | None:
    """Tracked files git is told to ignore changes in (assume-unchanged, skip-worktree): their edits
    appear in no diff, so nothing about them can be decided. None if git fails."""
    rows = _git_lines(root, "ls-files", "-v", "-z")
    if rows is None:
        return None
    return sorted(r[2:] for r in rows if len(r) > 2 and (r[0].islower() or r[0] == "S"))


def dirty_files(root: Path) -> list[str] | None:
    """What a --full run's log counts as uncommitted: every change against HEAD that could shape
    the run (changed_since, hidden_files), reports left out, since the run rewrites them itself.
    None if git fails."""
    changed, hidden = changed_since(root, "HEAD"), hidden_files(root)
    if changed is None or hidden is None:
        return None
    return sorted({f for f in changed + hidden if not is_report(f)})


def classify(files, named: dict[str, str]) -> dict[str, str]:
    """"rapor" (written by the checks), "belge" (documentation no code reads) or "kod"."""
    return {f: "rapor" if is_report(f) else "belge" if is_doc(f) and f not in named else "kod"
            for f in files}


def _code_of(root: Path, files) -> list[str]:
    return [f for f, c in classify(files, docs_named_by_code(root, [f for f in files if is_doc(f)])).items()
            if c == "kod"]


def last_full_run(root: Path) -> dict:
    """What `reports/check_full.log` proves. {"ok": True, "commit": sha, ...} only for a --full run
    that finished with every gate passed, whose tree was clean (no uncommitted change but reports)
    when it started and when it ended, on the same commit, which this repository has; otherwise
    {"ok": False, "why": ...}."""
    try:
        lines = [l.strip() for l in (root / REPORT_LOG).read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError):
        return {"ok": False, "why": "günlük yok"}
    head = _LOG_HEADER.fullmatch(lines[0]) if lines else None
    if head is None:
        return {"ok": False, "why": "günlüğün başlığı okunamadı"}
    info = {"when": head["when"], "branch": head["branch"], "short": head["commit"]}
    if int(head["dirty"]):
        return {**info, "ok": False, "why": f"koşu commit edilmemiş {head['dirty']} değişiklikle başlamış"}
    totals = [(i, m) for i, m in enumerate(map(_LOG_TOTAL.fullmatch, lines)) if m]
    if not totals:
        return {**info, "ok": False, "why": "koşu bitmemiş (kapı özeti yok)"}
    at, total = totals[-1]
    ok, n = int(total["ok"]), int(total["n"])
    marks = [l[:6] for l in lines if l.startswith("[OK  ]") or l.startswith("[FAIL]")]
    info["gates"] = f"{ok}/{n}"
    if n == 0 or ok != n or len(totals) > 1 or marks.count("[FAIL]") or marks.count("[OK  ]") != n:
        return {**info, "ok": False, "why": f"kapılar geçmedi ({ok}/{n})"}
    ends = [m for m in map(_LOG_END.fullmatch, lines[at + 1:]) if m]
    if not ends:
        return {**info, "ok": False, "why": "koşunun sonu kaydedilmemiş"}
    if ends[-1]["commit"] != head["commit"] or int(ends[-1]["dirty"]):
        return {**info, "ok": False, "why": f"ağaç koşu sırasında değişti (sonda {ends[-1]['commit']}, "
                                           f"commit edilmemiş {ends[-1]['dirty']} değişiklik)"}
    sha = _git_value(root, "rev-parse", "--verify", "--quiet", f"{head['commit']}^{{commit}}")
    if sha is None:
        return {**info, "ok": False, "why": f"günlüğün commit'i {head['commit']} bu depoda yok"}
    return {**info, "ok": True, "commit": sha}


def fetch_origin(root: Path) -> str:
    """Bring origin/master up to date: "tamam", "origin yok" (no such remote: the local refs are all
    there is) or why it failed. A stale origin/master hides code merged since, and only a fresh one
    can show that the base received none."""
    if _git_value(root, "remote", "get-url", "origin") is None:
        return "origin yok"
    p = _git_run(root, "fetch", "--quiet", "origin", "master", timeout=60,
                 env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    if p is None:
        return "başarısız (git çalışmadı ya da 60 s'de bitmedi)"
    return "tamam" if p.returncode == 0 else f"başarısız (çıkış {p.returncode})"


def choose_base(root: Path, base: str | None = None) -> tuple[str, str] | str:
    """(base, merge base with HEAD), or why none can be used. An explicit `base` is used as given;
    by default origin/master, which is what a pull request merges into, and master only in a
    repository without it. Local master may hold merges that were never pushed, or be the branch
    itself: on master with an unpushed commit, master's merge base with HEAD is HEAD and the commit
    would vanish (review finding, 26 Sep 2026). An existing base without a merge base (unrelated
    history, a shallow clone cut before it) decides nothing: no fallback."""
    for b in ([base] if base else ["origin/master", "master"]):
        if _git_value(root, "rev-parse", "--verify", "--quiet", f"{b}^{{commit}}") is None:
            continue
        if _git_value(root, "symbolic-ref", "--quiet", "--short", "HEAD") == b:
            return f"HEAD {b} dalının kendisi: karşılaştırılacak bağımsız taban yok"
        mb = _git_value(root, "merge-base", b, "HEAD")
        return (b, mb) if mb else f"{b} ile HEAD'in ortak atası yok"
    return f"taban bulunamadı ({base or 'origin/master, master'})"


def plan(root: Path, base: str | None = None, fetch: bool = True) -> dict:
    """The staged-check decision for the working tree against `base` (choose_base; origin/master is
    fetched first unless `fetch` is False). "level": "yok" (no check: only documentation no code
    reads and reports changed, and the base received no code that might read that documentation),
    "tamam" (code changed, and the last --full passed on exactly this code: nothing that differs
    from its commit is code, the base received no code since the branch left it, and the base is
    known to be fresh) or "tam" (the --full is still needed, or the decision could not be made)."""
    out: dict = {"base": base, "files": {}, "named": {}, "full": None, "base_ahead": [], "hidden": []}
    try:
        return _plan(out, root, base, fetch)
    except UnreadableSource as e:
        return {**out, "level": "tam", "why": f"Python kaynağı okunamadı ({e}): hangi belgeleri okuduğu bilinmiyor"}


def _plan(out: dict, root: Path, base: str | None, fetch: bool) -> dict:
    out["fetch"] = fetch_origin(root) if fetch else "yapılmadı (--no-fetch)"
    fresh = out["fetch"] in ("tamam", "origin yok")
    hidden = hidden_files(root)
    if hidden is None:
        return {**out, "level": "tam", "why": "git okunamadı"}
    if hidden:
        out["hidden"] = hidden
        return {**out, "level": "tam", "why": "git bazı dosyalardaki değişiklikleri gizliyor (assume-unchanged/skip-worktree)"}
    chosen = choose_base(root, base)
    if isinstance(chosen, str):
        return {**out, "level": "tam", "why": chosen}
    out.update(base=chosen[0], merge_base=chosen[1],
               base_tip=_git_value(root, "rev-parse", "--verify", "--quiet", f"{chosen[0]}^{{commit}}") or "?")
    files = changed_since(root, out["merge_base"])
    if files is None:
        return {**out, "level": "tam", "why": "git değişen dosyaları veremedi"}
    out["files"] = {f: "?" for f in files}
    named = docs_named_by_code(root, [f for f in files if is_doc(f)])
    out.update(files=classify(files, named), named=named)
    code = [f for f, c in out["files"].items() if c == "kod"]
    # Code the base received after the branch left it: merged, it is code no run has seen, and it
    # may read a document this branch changed (the scan above saw only this branch's code).
    ahead = _git_lines(root, "diff", "--name-only", "-z", "--no-renames", f"HEAD...{out['base']}", "--")
    if ahead is None:
        return {**out, "level": "tam", "why": "tabanın dal ayrıldıktan sonra ne aldığı okunamadı"}
    out["base_ahead"] = _code_of(root, ahead)
    merge_first = f"önce {out['base']} bu dala birleştirilir, sonra --plan yeniden"
    if not code:
        if "belge" not in out["files"].values():
            return {**out, "level": "yok", "why": "kod ve belge değişmedi"}
        if out["base_ahead"]:
            return {**out, "level": "tam", "why": f"{out['base']} bu daldan sonra kod aldı; o kod değişen "
                                                  f"belgeleri okuyor olabilir: {merge_first}"}
        if not fresh:
            return {**out, "level": "tam", "why": f"tabanın güncelliği bilinmiyor (fetch: {out['fetch']})"}
        return {**out, "level": "yok", "why": "kod değişmedi"}
    full = out["full"] = last_full_run(root)
    if not full["ok"]:
        return {**out, "level": "tam", "why": f"kod değişti; son --full bu kodu kapsamıyor: {full['why']}"}
    since = changed_since(root, full["commit"])
    if since is None:
        return {**out, "level": "tam", "why": "son --full'dan bu yana değişenler okunamadı"}
    full["code_since"] = _code_of(root, since)
    if full["code_since"]:
        return {**out, "level": "tam", "why": f"kod, son --full'dan ({full['short']}) bu yana değişti"}
    if out["base_ahead"]:
        return {**out, "level": "tam", "why": f"{out['base']} bu daldan sonra kod aldı: {merge_first}, sonra --full"}
    if not fresh:
        return {**out, "level": "tam", "why": f"tabanın güncelliği bilinmiyor (fetch: {out['fetch']})"}
    return {**out, "level": "tamam", "why": f"son --full ({full['gates']}, {full['short']}) bu kodda geçti"}


_PLAN_ADVICE = {
    "yok": "kontrol gerekmez",
    "tamam": "tam kontrol bu kodda yapılmış; birleştirmeden önce başka kontrol gerekmez",
    "tam": "çalışırken hızlı check.py; birleştirmeden önce son hâlde bir kez check.py --full",
}


def render_plan(p: dict) -> list[str]:
    lines = ["== kademeli kontrol (DECISIONS §59) =="]
    if p.get("fetch"):
        lines.append(f"  origin/master fetch: {p['fetch']}")
    if p.get("merge_base"):
        lines.append(f"  taban: {p['base']} {p.get('base_tip', '?')[:7]} (ortak ata {p['merge_base'][:7]})")
    files = p.get("files") or {}
    counts = {c: sum(1 for v in files.values() if v == c) for c in ("kod", "belge", "rapor")}
    lines.append(f"  değişen: {len(files)} dosya (kod {counts['kod']}, belge {counts['belge']}, "
                 f"rapor {counts['rapor']})")
    order = ("kod", "belge", "rapor", "?")
    for f, c in sorted(files.items(), key=lambda kv: (order.index(kv[1]), kv[0])):
        why = f"  (okuyan: {p['named'][f]})" if f in p.get("named", {}) else ""
        lines.append(f"    {c:<5} {f}{why}")
    for f in p.get("hidden") or []:
        lines.append(f"    gizli {f}")
    for f in p.get("base_ahead") or []:
        lines.append(f"    taban {f}  ({p['base']} bu daldan sonra aldı)")
    full = p.get("full")
    if full is not None:
        state = "geçerli" if full["ok"] else f"geçersiz: {full['why']}"
        where = f"{full.get('gates', '?')} · {full.get('when', '?')} · {full.get('branch', '?')} @ {full.get('short', '?')}"
        lines.append(f"  son --full: {where} ({state})")
        for f in full.get("code_since") or []:
            lines.append(f"    o koşudan bu yana değişen kod: {f}")
    lines.append(f"  karar: {p['level'].upper()} · {p['why']} → {_PLAN_ADVICE[p['level']]}")
    return lines


def plan_report(root: Path, base: str | None = None, fetch: bool = True) -> tuple[int, list[str]]:
    """(exit code, lines): 0 when nothing more is needed before merging, 1 when a --full is. Never
    raises: a failure to decide is itself the decision "tam"."""
    try:
        p = plan(root, base, fetch)
        return (0 if p["level"] in ("yok", "tamam") else 1), render_plan(p)
    except Exception as e:  # noqa: BLE001 - an undecidable change needs the full check
        return 1, ["== kademeli kontrol (DECISIONS §59) ==",
                   f"  karar: TAM · karar verilemedi ({type(e).__name__}: {e}) → {_PLAN_ADVICE['tam']}"]


def unexplained_doc_reads(root: Path, opened) -> list[str]:
    """The files among `opened` (paths a process opened) inside `root` that the staged-check rule
    does not count as code (classify): a document neither named nor in DOCS_READ_UNNAMED, or a
    report (the rule never counts one as code, so no test may depend on one). Ignored: paths outside the repository, under _SKIP_DIRS, and gone by now (pytest's own
    temporary cache directory). Raises UnreadableSource."""
    top = Path(root).resolve()
    rels = set()
    for p in opened:
        try:
            full = Path(p).resolve()
            rel = full.relative_to(top).as_posix()
        except (OSError, ValueError):
            continue
        if rel.split("/")[0] in _SKIP_DIRS or not full.exists():
            continue
        if rel.lower().endswith(DOC_SUFFIX) or rel == REPORT_LOG:
            rels.add(rel)
    named = docs_named_by_code(top, [r for r in rels if is_doc(r)])
    return sorted(r for r in rels if classify([r], named)[r] != "kod")


def _count(files) -> str:
    return "?" if files is None else str(len(files))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="Lean, adversaryal ve kalibrasyonu da koştur")
    ap.add_argument("--plan", action="store_true",
                    help="yalnız kademeli kontrol kararını yaz (çıkış 0: başka kontrol gerekmez, 1: --full gerekli)")
    ap.add_argument("--base", default=None, help="karşılaştırma tabanı (varsayılan origin/master, yoksa master)")
    ap.add_argument("--no-fetch", action="store_true",
                    help="origin/master'ı güncelleme; taban bayat olabileceğinden belge ya da kod değiştiyse karar TAM olur")
    args = ap.parse_args(argv)
    if args.plan:
        rc, lines = plan_report(ROOT, args.base, not args.no_fetch)
        print("\n".join(lines))
        return rc
    if not args.full:
        rc = _main(args)
        print()
        print("\n".join(plan_report(ROOT, args.base, not args.no_fetch)[1]))   # a reminder: the exit code is the gates'
        return rc
    # The full run writes its own log. The 21/21 run of 23 Sep lived only in a session's temp
    # file while reports/check_full.log still said 12/12 from 19 Sep; the header ties the log
    # to the code it measured, and the closing line shows the tree was the same at the end: the
    # staged-check rule accepts the log as proof for that commit only then (last_full_run).
    log = ROOT / "reports" / "check_full.log"
    with log.open("w", encoding="utf-8") as fh:
        out = sys.stdout
        sys.stdout = _Tee(out, fh)
        try:
            # Reports are not counted: the run rewrites them (the open log among them; counted, it
            # made the header say 1 on a clean tree until 26 Sep 2026), and a quick check.py
            # before the --full leaves reports/eval_report.md modified.
            print(f"check.py --full · {time.strftime('%Y-%m-%d %H:%M:%S')} · "
                  f"{_git('rev-parse', '--abbrev-ref', 'HEAD')} @ {_git('rev-parse', '--short', 'HEAD')} · "
                  f"commit edilmemiş değişiklik: {_count(dirty_files(ROOT))} dosya\n")
            rc = _main(args)
            print(f"\ncheck.py --full sonu · {time.strftime('%Y-%m-%d %H:%M:%S')} · "
                  f"{_git('rev-parse', '--abbrev-ref', 'HEAD')} @ {_git('rev-parse', '--short', 'HEAD')} · "
                  f"commit edilmemiş değişiklik: {_count(dirty_files(ROOT))} dosya")
            return rc
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
        note = adversarial_note(REPORTS / "adversarial_results.json")
        if note:
            print(note)

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
