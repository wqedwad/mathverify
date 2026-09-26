"""Tek komutla bütün kapılar: testler, deterministik değerlendirme, Lean taraması, adversaryal.

    .venv/Scripts/python.exe scripts/check.py            # Windows: hızlı (testler + değerlendirme)
    .venv/Scripts/python.exe scripts/check.py --full     # + Lean taraması + adversaryal + kalibrasyon
    .venv/bin/python scripts/check.py [--full]           # Linux/macOS: aynı kapılar
    .venv/Scripts/python.exe scripts/check.py --plan     # Windows: hangi kontrol gerekli (DECISIONS §59)
    .venv/bin/python scripts/check.py --plan [--no-fetch] # Linux/macOS: aynısı

Her kapı için ölçülen sayıyı ve hedefi yazar, herhangi biri düşerse çıkış kodu 1 olur.
Kademeli kural (CLAUDE.md, DECISIONS §59): yalnız hiçbir kodun okumadığı belgeler (kökte ve `docs/`
altında) değiştiyse kontrol gerekmez; `reports/` altındaki raporlar onları yazan geçerli bir
`--full`a bağlı olmalı; başka her değişiklik koddur ve birleştirmeden önce son hâlde bir `--full`
ister; karar verilemeyen durum TAM'dır. `--plan` yalnız kararı yazar (çıkış 0: birleştirmeden önce
başka bir şey gerekmez, 1: bir şey gerekli, ne olduğunu karar satırı söyler: `--full`, push, fetch,
tabanı birleştirme...); hızlı koşu kararı kapılardan sonra hatırlatır. `--full` çıktısını ayrıca
`reports/check_full.log`a yazar (başta ve sonda UTC saat, dal, commit ve kirli dosya sayısı; ortam ve
requirements.lock denetimi; sonda raporların özeti).
Hiçbir kapı tahmine dayanmaz: hepsi bu koşuda üretilmiş raporlardan okunur. Bir harness'ın
raporu koşudan önce silinir; harness çökerse ya da rapor yoksa/okunamıyorsa o harness'ın bütün
kapıları aynı adlarla FAIL olur.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import ntpath
import os
import posixpath
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
# the sandbox's in-process debugging mode (no process isolation, no hard timeouts), and the fitted
# fusion thresholds (MATHVERIFY_CALIBRATION=on turned 21 of 280 CORRECT verdicts into UNKNOWN in
# review, 26 Sep 2026). These are the only variables src/ reads that change a verdict; the log
# names the MATHVERIFY_* variables that remain (environment_lines). Colour codes hid pytest's SKIPPED lines
# from the log (FORCE_COLOR, PY_COLORS=1), and PYTEST_DISABLE_PLUGIN_AUTOLOAD turned pytest-timeout off
# (review, 26 Sep 2026): no colour, plugins as installed. PYTHONOPTIMIZE strips the asserts the
# harnesses guard with (the answer-key check in harness/loader.py), and a pinned PYTHONHASHSEED
# reaches the sandbox, which pins its own seed only when none is set (review, 26 Sep 2026).
for _var in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "MATHVERIFY_SANDBOX",
             "MATHVERIFY_CALIBRATION", "FORCE_COLOR", "PYTHONOPTIMIZE", "PYTHONHASHSEED"):
    ENV.pop(_var, None)
ENV["PY_COLORS"] = "0"


def venv_python(root: Path, windows: bool | None = None) -> str:
    """The project venv's interpreter (`Scripts/python.exe` on Windows, `bin/python` elsewhere),
    or the running interpreter when that venv does not exist."""
    if windows is None:
        windows = os.name == "nt"
    p = root / ".venv" / ("Scripts/python.exe" if windows else "bin/python")
    return str(p) if p.exists() else sys.executable


PY = venv_python(ROOT)


# No step may hold the run for ever: a deadlock in the sweep's pool left a harness hanging with no
# end in review (26 Sep 2026). The longest step measured took 3764 s (the single-process sweep); a
# step past this fails its gates instead (exit 124, as timeout(1) says it).
STEP_TIMEOUT = 3 * 3600


def run(cmd: list[str], label: str, timeout: float = STEP_TIMEOUT) -> tuple[int, str]:
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        rc, out = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:      # the child is killed; its output comes as bytes
        rc = 124
        out = b"".join(x for x in (e.stdout, e.stderr) if x).decode("utf-8", "replace")
        out += f"\n{label}: {timeout:.0f} s içinde bitmedi, durduruldu"
    print(f"  {label}: {time.perf_counter() - t0:.0f} s (exit {rc})")
    return rc, out


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
    or restarted, verifications with a sandbox or layer error, and the items attacked again alone
    because of them (harness.adversarial). None when the report is missing or unreadable (the gates
    already say so)."""
    try:
        adv = json.loads(path.read_text(encoding="utf-8"))
        return (f"    adversarial: {adv['workers']} süreç · sandbox zaman aşımı {adv['sandbox_timeouts']} · "
                f"yeniden başlatma {adv['sandbox_restarts']} · sandbox/katman hatası {adv['sandbox_errors']} · "
                f"tek başına yeniden denenen {len(adv['rechecked'])}")
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
    lines = (_ANSI.sub("", l) for l in out.splitlines())
    return [l.strip() for l in lines if l.startswith(keep)]


_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


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
# The files that make the decision, the allowlists of tests/test_staged_check.py among them. A branch
# that changes them would judge itself with its own rule, so their change never gets TAMAM: after its
# --full the merge is a person's call. The base's list counts too (base_rule_files): a branch cannot
# take a file off it.
RULE_FILES = ("scripts/check.py", "tests/doc_read_guard.py", "tests/conftest.py", "tests/test_staged_check.py")
# The reports a --full writes again; the rest (the F3 reports) it only binds, so a change to one
# before the run is uncommitted change, not output.
REWRITTEN = frozenset(f"reports/{name}_report" + DOC_SUFFIX
                      for name in ("eval", "lean", "adversarial", "soundness", "calibration")) | {REPORT_LOG}
# A file name ending in .md inside a string: "BULUT.md", "docs/x.md", "*.md", the constant tail
# "_report.md" of f"{tag}_report.md". Built from DOC_SUFFIX so that the pattern's own text holds no
# such name.
_MD_TOKEN = re.compile(r"[\w.*?\[\]/\\-]*" + re.escape(DOC_SUFFIX) + r"(?!\w)", re.IGNORECASE)
_RUN_LINE = (r" · (?P<when>.+?) · (?P<branch>.+) @ (?P<commit>[0-9a-f]{4,40}) · "
             r"commit edilmemiş değişiklik: (?P<dirty>\d+|\?) dosya")
_LOG_HEADER = re.compile(r"check\.py --full" + _RUN_LINE)
_LOG_END = re.compile(r"check\.py --full sonu" + _RUN_LINE)
_LOG_REPORTS = re.compile(r"check\.py --full raporları ·(?P<list>.*)")
_LOG_TOTAL = re.compile(r"(?P<ok>\d+)/(?P<n>\d+) kapı geçti")
_LOG_ENV = re.compile(r"ortam: (?P<items>.+)")
_LOG_LOCK = re.compile(r"kilit: (?P<rest>.*)")
_LOCK_OK = re.compile(r"(?P<file>\S+) (?P<digest>[0-9a-f]{16}) · (?P<n>\d+) paket · uyuşmayan: (?P<bad>.+)")
LOCK_FILE = "requirements.lock"
_LOG_WARMUP = re.compile(r"lean_warmup: \d+ s \(exit (?P<rc>-?\d+)\)")
# pytest's skip reason for the Lean tests (tests/test_f5_lean.py and friends): a --full whose Lean
# tests did not run proves nothing about them, even if the Lean sweep later found a warm Lean.
_LEAN_SKIPPED = "toolchain not available"
REPORTS_CHANGED = "raporlar --full'dan sonra değişmiş"
_WORD = re.compile(r"\w")


class UnreadableSource(Exception):
    """A Python file the scan cannot parse: which documents it reads is unknown."""


def _git_run(root: Path, *a: str, timeout: float | None = None, env: dict | None = None, input: bytes | None = None):
    try:
        return subprocess.run(["git", *a], cwd=root, capture_output=True, timeout=timeout, env=env, input=input)
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


def _head_branch(root: Path) -> str | None:
    """The branch HEAD is on, from its full name: `symbolic-ref --short` gives "heads/dal" when a tag
    is also named dal (review, 26 Sep 2026). None for a detached HEAD."""
    full = _git_value(root, "symbolic-ref", "--quiet", "HEAD")
    return full[len("refs/heads/"):] if full and full.startswith("refs/heads/") else None


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def is_report(path: str) -> bool:
    """A file the checks write: `reports/<name>.md` (a harness report, produced and never written
    by hand) or the --full log. A change to one is the output of a check, not a reason for one.
    Case-insensitive, like the Windows file system."""
    p = _norm(path).lower()
    head, _, name = p.rpartition("/")
    return p == REPORT_LOG or (head == "reports" and name.endswith(DOC_SUFFIX))


def is_doc(path: str) -> bool:
    """A .md file in a documentation place (the root, DOC_DIRS): the only files that can be
    "belge". Everywhere else a .md file is code by its place."""
    p = _norm(path).lower()
    return p.endswith(DOC_SUFFIX) and not is_report(p) and ("/" not in p or p.startswith(DOC_DIRS))


def read_unnamed(doc: str) -> str | None:
    """Why code reads `doc` without naming it (DOCS_READ_UNNAMED), or None."""
    d = _norm(doc)
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
    """(file:line, text, tail) of every string and bytes constant in the repository's Python code,
    f-string parts included (bytes decoded: `open(b"docs/x.md")` is a read too). `tail` marks text
    appended to a value only known at run time: an f-string part after a {field}, the right side of
    `+`, the argument of `with_suffix`. Docstrings and other bare string statements are left out:
    like comments, they are prose (a test's docstring citing a document does not read it). Raises
    UnreadableSource for a file that cannot be read or parsed (parsed from bytes, as Python itself
    reads it: a UTF-8 BOM or a coding cookie is honoured)."""
    import ast
    import warnings
    # f-strings, and Python 3.14's t-strings: a part after a field is completed at run time
    templates = (ast.JoinedStr, *([ast.TemplateStr] if hasattr(ast, "TemplateStr") else []))
    fields = (ast.FormattedValue, *([ast.Interpolation] if hasattr(ast, "Interpolation") else []))
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
            elif isinstance(n, templates):
                tails.update(id(v) for i, v in enumerate(n.values)
                             if i and isinstance(n.values[i - 1], fields))
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                tails.add(id(n.right))
            elif isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "with_suffix":
                tails.update(id(a) for a in n.args)
        consts = sorted((n for n in ast.walk(tree) if isinstance(n, ast.Constant)
                         and isinstance(n.value, (str, bytes)) and id(n) not in prose),
                        key=lambda n: (n.lineno, n.col_offset))
        out += [(f"{rel}:{n.lineno}",
                 n.value if isinstance(n.value, str) else n.value.decode("utf-8", "replace"),
                 id(n) in tails) for n in consts]
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
    glob names what it matches ("*.md" every document), and when only its end is known what ends in
    a match ("{stem}[12].md"); a suffix token names every document whose name ends with it
    ("_report.md"; the bare extension: every document). The bare extension as a whole token is a
    type test (`p.endswith(".md")`), not a name."""
    t, d = _norm(token).lower(), _norm(doc).lower()
    base, tbase = d.rpartition("/")[2], t.rpartition("/")[2]
    if any(c in t for c in "*?["):
        if suffix:
            t, tbase = "*" + t, "*" + tbase
        return fnmatch.fnmatchcase(d, t) or fnmatch.fnmatchcase(base, tbase)
    if suffix:
        return base.endswith(tbase)
    if tbase == DOC_SUFFIX:
        return False
    return base == tbase or (base.endswith(tbase) and not _WORD.match(base[-len(tbase) - 1]))


def linked_docs(root: Path, docs) -> dict[str, str]:
    """{document: link} for the documents in `docs` that a tracked symbolic link points to, or
    lies under a linked directory of: code that reads the link reads the document, under a name
    that is not its own."""
    rows = _git_lines(root, "ls-files", "-s", "-z") or []
    out = {}
    for row in rows:
        meta, _, path = row.partition("\t")
        if not meta.startswith("120000"):
            continue
        # the target from git's blob, not the disk: Windows checks links out as plain files
        link = _git_value(root, "cat-file", "blob", meta.split()[1])
        link = None if link is None else _norm(link)
        if link is None or link.startswith("/") or ntpath.splitdrive(link)[0]:
            hits = docs                            # unreadable, absolute or on a drive: it may be any of them
        else:                                      # git's paths, the same on every OS (review)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), link)).rstrip("/").lower()
            hits = [d for d in docs if _norm(d).lower() == target or _norm(d).lower().startswith(target + "/")]
        for d in hits:
            out.setdefault(d, f"bağlantı: {path}")
    return out


def docs_named_by_code(root: Path, docs) -> dict[str, str]:
    """{document: why it counts as read} for the documents in `docs` that DOCS_READ_UNNAMED covers,
    that a tracked symbolic link points to, or that a string or bytes constant of the repository's
    Python code names (the first place found). A read document is code: a change to it can change
    what the checks or the verifier do. A name assembled without a constant that ends in .md
    (`"".join(...)`) is not seen here; tests/doc_read_guard.py catches it at run time in the tests,
    and tests/test_staged_check.py pins every .md-shaped constant of the code the tests do not run
    in-process. Raises UnreadableSource."""
    docs = sorted(set(docs))
    found = {d: f"adsız okuyucu: {read_unnamed(d)}" for d in docs if read_unnamed(d)}
    if len(found) == len(docs):
        return found
    found.update({d: why for d, why in linked_docs(root, docs).items() if d not in found})
    if len(found) == len(docs):
        return found
    for where, text, tail in code_strings(root):
        for token, suffix in doc_tokens(text, tail):
            for d in docs:
                if d not in found and names_doc(token, d, suffix):
                    found[d] = where
    return found


def changed_since(root: Path, rev: str) -> list[str] | None:
    """Files that differ between commit `rev` and any state that could be run or merged: HEAD's
    tree (what a pull request merges: a commit reverted only in the working tree is still in it),
    the index, and the working tree; deletions, both sides of a rename (--no-renames), submodule
    moves whatever .gitmodules or the user's config say (--ignore-submodules=none), and every
    untracked file that the repository's .gitignore files do not ignore (personal excludes and
    status.showUntrackedFiles hide nothing here; a nested repository or worktree is not content).
    None if git fails."""
    diff = ("diff", "--name-only", "-z", "--no-renames", "--ignore-submodules=none")
    lists = [_git_lines(root, *diff, rev, "--"), _git_lines(root, *diff, "--cached", rev, "--"),
             _git_lines(root, *diff, rev, "HEAD", "--"),
             _git_lines(root, "ls-files", "--others", "--exclude-per-directory=.gitignore", "-z")]
    if any(x is None for x in lists):
        return None
    return sorted({f for x in lists for f in x if not f.endswith("/")})


def hidden_files(root: Path) -> list[str] | None:
    """Files whose changes git would not show, so nothing about them can be decided: tracked files
    marked assume-unchanged or skip-worktree; tracked files a filter rewrites before git compares
    them (a clean filter from .git/info/attributes: the edit on disk never reaches a diff); and
    untracked .gitignore files that ignore by their own rule (a tool's "*" ignores itself and any
    untracked code beside it). The last two were found in review, 26 Sep 2026. None if git fails."""
    rows = _git_lines(root, "ls-files", "-v", "-z")
    if rows is None:
        return None
    tracked = [r[2:] for r in rows if len(r) > 2]
    out = {r[2:] for r in rows if len(r) > 2 and (r[0].islower() or r[0] == "S")}
    if tracked:
        attrs = _git_run(root, "check-attr", "-z", "--stdin", "filter", input="\0".join(tracked).encode())
        if attrs is None or attrs.returncode:
            return None
        parts = attrs.stdout.decode("utf-8", "replace").split("\0")
        out |= {parts[i] for i in range(0, len(parts) - 2, 3) if parts[i + 2] not in ("unspecified", "unset")}
    ignored = _git_lines(root, "ls-files", "--others", "--ignored", "--exclude-per-directory=.gitignore", "-z",
                         "--", ":(glob)**/.gitignore")
    if ignored is None:
        return None
    if ignored:
        why = _git_run(root, "check-ignore", "-v", "-z", "--stdin", input="\0".join(ignored).encode())
        if why is None or why.returncode not in (0, 1):
            return None
        fields, known = why.stdout.decode("utf-8", "replace").split("\0"), set(tracked)
        out |= {fields[i + 3] for i in range(0, len(fields) - 3, 4) if fields[i] not in known}
    return sorted(out)


def dirty_files(root: Path) -> list[str] | None:
    """What a --full run's log counts as uncommitted: every change against HEAD that could shape
    the run or ride on it (changed_since, hidden_files), but the reports the run writes again
    (REWRITTEN, by their exact names): an F3 report edited before the run would be bound by the
    run's digest otherwise. None if git fails."""
    changed, hidden = changed_since(root, "HEAD"), hidden_files(root)
    if changed is None or hidden is None:
        return None
    return sorted({f for f in changed + hidden if _norm(f) not in REWRITTEN})


def classify(files, named: dict[str, str]) -> dict[str, str]:
    """"rapor" (written by the checks), "belge" (documentation no code reads) or "kod"."""
    return {f: "rapor" if is_report(f) else "belge" if is_doc(f) and f not in named else "kod"
            for f in files}


def _code_of(root: Path, files) -> list[str]:
    return [f for f, c in classify(files, docs_named_by_code(root, [f for f in files if is_doc(f)])).items()
            if c == "kod"]


def report_digests(root: Path) -> dict[str, str]:
    """{reports/<name>.md: sha256 prefix} for the reports on disk: the closing lines of a --full log
    bind the reports it wrote, so a report changed afterwards (by hand, or by a partial harness run
    into reports/) no longer rides on the run."""
    import hashlib
    out = {}
    folder = root / "reports"
    for p in sorted(folder.iterdir()) if folder.is_dir() else []:
        rel = f"reports/{p.name}"
        if not is_report(rel) or _norm(rel).lower() == REPORT_LOG:
            continue
        if p.is_symlink() or not p.is_file():
            out[rel] = "okunamadı"
            continue
        # line endings as git stores them: a Windows checkout (text=auto) has CRLF on disk
        out[rel] = hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]
    return out


def last_full_run(root: Path) -> dict:
    """What `reports/check_full.log` proves. {"ok": True, "commit": sha, ...} only for a --full run
    that finished with every gate passed, whose tree was clean (no uncommitted change but the reports
    it writes again, REWRITTEN) when it started and when it ended, on the same commit, which this
    repository has; that ran in the environment requirements.lock pins (its one "kilit:" line, for
    the lock as it is now); whose Lean warm-up succeeded and whose Lean tests ran (none skipped for
    want of the toolchain); and whose reports are still the ones it wrote. Otherwise {"ok": False,
    "why": ...}, with "advice" when something other than another --full settles it. It reads the
    log on disk: whether it is committed is the plan's question."""
    try:
        text = (root / REPORT_LOG).read_text(encoding="utf-8")
    except OSError:
        return {"ok": False, "why": "günlük yok"}
    except UnicodeDecodeError:
        return {"ok": False, "why": "günlük okunamadı (UTF-8 değil)"}
    lines = [_ANSI.sub("", l).strip() for l in text.splitlines()]
    head = _LOG_HEADER.fullmatch(lines[0]) if lines else None
    if head is None:
        return {"ok": False, "why": "günlüğün başlığı okunamadı"}
    info = {"when": head["when"], "branch": head["branch"], "short": head["commit"]}
    if head["dirty"] == "?":                   # the run's own warning said so
        return {**info, "ok": False, "why": "koşunun başında git değişiklikleri veremedi"}
    if int(head["dirty"]):
        return {**info, "ok": False, "why": f"koşu commit edilmemiş {head['dirty']} değişiklikle başlamış"}
    if sum(1 for l in lines if _LOG_ENV.fullmatch(l)) != 1:
        return {**info, "ok": False, "why": "ortam satırı yok ya da birden çok"}
    locks = [m["rest"] for m in map(_LOG_LOCK.fullmatch, lines) if m]
    if len(locks) != 1:
        return {**info, "ok": False, "why": "kilit satırı yok ya da birden çok"}
    lock = _LOCK_OK.fullmatch(locks[0])
    if lock is None:
        return {**info, "ok": False, "why": f"kilit denetlenemedi ({locks[0]})", "advice": _ADVICE_LOCK}
    if lock["bad"] != "yok":
        return {**info, "ok": False, "why": f"ortam kilitle uyuşmuyor ({lock['bad']})", "advice": _ADVICE_LOCK}
    if lock["file"] != LOCK_FILE or lock["digest"] != lock_digest(root):
        return {**info, "ok": False, "why": "kilit koşudan sonra değişti ya da okunamıyor"}
    totals = [(i, m) for i, m in enumerate(map(_LOG_TOTAL.fullmatch, lines)) if m]
    if not totals:
        return {**info, "ok": False, "why": "koşu bitmemiş (kapı özeti yok)"}
    at, total = totals[-1]
    ok, n = int(total["ok"]), int(total["n"])
    marks = [l[:6] for l in lines if l.startswith("[OK  ]") or l.startswith("[FAIL]")]
    info["gates"] = f"{ok}/{n}"
    if n == 0 or ok != n or len(totals) > 1 or marks.count("[FAIL]") or marks.count("[OK  ]") != n:
        return {**info, "ok": False, "why": f"kapılar geçmedi ({ok}/{n})"}
    warmups = [m for m in map(_LOG_WARMUP.fullmatch, lines) if m]
    if len(warmups) != 1 or int(warmups[0]["rc"]):
        return {**info, "ok": False, "why": "Lean ısınması başarısız ya da kayıtsız"}
    if any(l.startswith("SKIPPED") and _LEAN_SKIPPED in l for l in lines):
        return {**info, "ok": False, "why": "Lean testleri atlanmış (toolchain yok)"}
    ends = [m for m in map(_LOG_END.fullmatch, lines[at + 1:]) if m]
    if not ends:
        return {**info, "ok": False, "why": "koşunun sonu kaydedilmemiş"}
    if ends[-1]["commit"] != head["commit"] or ends[-1]["dirty"] != "0":
        return {**info, "ok": False, "why": f"ağaç koşu sırasında değişti (sonda {ends[-1]['commit']}, "
                                           f"commit edilmemiş {ends[-1]['dirty']} değişiklik)"}
    listed = [m for m in map(_LOG_REPORTS.fullmatch, lines[at + 1:]) if m]
    if not listed:
        return {**info, "ok": False, "why": "raporların özeti kaydedilmemiş"}
    pairs = [x.strip().split(" ", 1) for x in listed[-1]["list"].split(" · ") if x.strip()]
    now = report_digests(root)
    if not all(len(p) == 2 for p in pairs) or dict(pairs) != now:
        listed = dict(p for p in pairs if len(p) == 2)
        changed = sorted(k for k in set(listed) | set(now) if listed.get(k) != now.get(k))
        return {**info, "ok": False, "why": REPORTS_CHANGED, "changed_reports": changed}     # advice: _full_advice
    sha = _git_value(root, "rev-parse", "--verify", "--quiet", f"{head['commit']}^{{commit}}")
    if sha is None:
        return {**info, "ok": False, "why": f"günlüğün commit'i {head['commit']} bu depoda yok"}
    return {**info, "ok": True, "commit": sha}


def lock_digest(root: Path) -> str | None:
    """sha256 prefix of requirements.lock as git stores it (CRLF read as LF), or None without one."""
    import hashlib
    try:
        return hashlib.sha256((root / LOCK_FILE).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]
    except OSError:
        return None


# Run by PY, the interpreter of the gates, with requirements.lock on stdin: which pins apply here
# (their environment markers evaluated by PY) and what PY has installed.
_ENV_PROBE = """
import json, platform, re, sys
from importlib import metadata
try:
    from packaging.markers import Marker
except ImportError:
    Marker = None
def version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None
pins, unsure = {}, []
for line in sys.stdin.read().splitlines():
    m = re.match(r"([A-Za-z0-9_.-]+)==([^\\s;]+)\\s*(?:;\\s*(.+))?$", line.strip())
    if not m:
        continue
    name, pinned, marker = m.groups()
    if marker:
        try:
            if not Marker(marker).evaluate():
                continue
        except Exception:
            unsure.append(name)
            continue
    pins[name] = pinned
core = ("sympy", "mpmath", "z3-solver", "math-verify", "pytest")
print(json.dumps({"python": platform.python_version(), "executable": sys.executable,
                  "platform": platform.platform(), "core": {n: version(n) for n in core},
                  "pins": pins, "found": {n: version(n) for n in pins}, "unsure": unsure}))
"""


def environment_lines(root: Path) -> tuple[str, str]:
    """The --full log's "ortam:" and "kilit:" lines, read by running PY: check.py itself may run
    under another interpreter (review, 26 Sep 2026). "ortam:": Python, platform, the core packages
    and the names (never the values) of the MATHVERIFY_* variables the gates inherit. "kilit:":
    every package requirements.lock pins for this platform against what PY has (a verdict can
    change with SymPy's or latex2sympy2's version), with the lock's digest."""
    names = ", ".join(sorted(k for k in ENV if k.startswith("MATHVERIFY_"))) or "yok"
    digest = lock_digest(root)
    lock_text, lock_why = None, "yok"
    if digest is not None:
        try:
            lock_text = (root / LOCK_FILE).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            lock_why = f"{LOCK_FILE} okunamadı (UTF-8 değil)"
        except OSError:
            lock_why = f"{LOCK_FILE} okunamadı"
    try:
        p = subprocess.run([PY, "-c", _ENV_PROBE], input=lock_text or "", cwd=root, env=ENV, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120)
        info = json.loads(p.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        return f"ortam: {PY} okunamadı ({type(e).__name__}) · MATHVERIFY_*: {names}", "kilit: ortam okunamadı"
    core = " · ".join(f"{n} {v or 'yok'}" for n, v in info["core"].items())
    env = f"ortam: Python {info['python']} ({info['executable']}) · {info['platform']} · {core} · MATHVERIFY_*: {names}"
    if lock_text is None:
        return env, f"kilit: {lock_why}"
    bad = [f"{n} {info['found'][n] or 'yok'} ≠ {v}" for n, v in info["pins"].items() if info["found"][n] != v]
    bad += [f"{n} işareti okunamadı" for n in info["unsure"]]
    return env, f"kilit: {LOCK_FILE} {digest} · {len(info['pins'])} paket · uyuşmayan: {', '.join(bad) or 'yok'}"


def local_origin(url: str) -> bool:
    """Is origin a path on this machine (a clone of another checkout, a recovery clone of a bundle),
    whose master is only as fresh as that copy? git's own rule (url_is_local_not_ssh): a file: URL,
    or a URL with no scheme and no scp-like "host:" before its first slash; a Windows drive ("C:")
    is a path. Whether the path exists does not matter: git adds ".git" and ".bundle" itself, and
    reads file://localhost/ (review, 26 Sep 2026)."""
    if url.startswith("file:"):
        return True
    if "://" in url:
        return False
    colon, slash = url.find(":"), url.find("/")
    return colon < 0 or 0 <= slash < colon or (colon == 1 and url[0].isalpha())


def fetch_origin(root: Path) -> str:
    """Bring origin/master up to date: "tamam", "uzak yok" (a repository without remotes: the local
    refs are all there is), or why it did not. A remote under another name, or an origin on this
    machine (local_origin), cannot vouch for the real master. The destination is explicit, so a
    clone whose fetch refspec does not map master (a single-branch clone) still gets origin/master,
    and FETCH_HEAD must then equal it."""
    remotes = _git_lines(root, "remote")
    if remotes is None:
        return "başarısız (uzaklar okunamadı)"
    url = _git_value(root, "remote", "get-url", "origin")
    if url is None:
        return "origin yok (başka uzak var)" if remotes else "uzak yok"
    if local_origin(url):
        return "origin bu makinede bir yol: tazeliği bilinmiyor"
    p = _git_run(root, "fetch", "--quiet", "origin", "+refs/heads/master:refs/remotes/origin/master", timeout=60,
                 env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never"))
    if p is None:
        return "başarısız (git çalışmadı ya da 60 s'de bitmedi)"
    if p.returncode:
        return f"başarısız (çıkış {p.returncode})"
    fetched = _git_value(root, "rev-parse", "--verify", "--quiet", "FETCH_HEAD^{commit}")
    tip = _git_value(root, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/master^{commit}")
    return "tamam" if fetched and fetched == tip else "başarısız (origin/master güncellenmedi)"


def choose_base(root: Path, base: str | None = None) -> tuple:
    """(base, merge base with HEAD), or (None, why none can be used, advice). By default
    origin/master, which is what a pull request merges into, and master only in a repository
    without it; `base` is for the tests. Local master may hold merges that were never pushed, or be
    the branch itself: on master with an unpushed commit, master's merge base with HEAD is HEAD and
    the commit would vanish (review finding, 26 Sep 2026). An existing base without a merge base
    (unrelated history, a shallow clone cut before it) decides nothing: no fallback; nor do two
    merge bases (a criss-cross history), where what the branch and the base changed depends on which
    one is taken."""
    for b in ([base] if base else ["origin/master", "master"]):
        if _git_value(root, "rev-parse", "--verify", "--quiet", f"{b}^{{commit}}") is None:
            continue
        if _head_branch(root) == b:
            return None, f"HEAD {b} dalının kendisi: karşılaştırılacak bağımsız taban yok", _ADVICE_BASE
        mbs = (_git_value(root, "merge-base", "--all", b, "HEAD") or "").split()
        if len(mbs) > 1:
            return None, f"{b} ile HEAD'in birden çok ortak atası var (çapraz birleşme): önce {b} bu dala birleştirilir", _ADVICE_MERGE
        if not mbs:
            shallow = _git_value(root, "rev-parse", "--is-shallow-repository") == "true"
            return None, f"{b} ile HEAD'in ortak atası yok", _ADVICE_SHALLOW if shallow else _ADVICE_BASE
        return b, mbs[0]
    return None, f"taban bulunamadı ({base or 'origin/master, master'})", _ADVICE_BASE


def plan(root: Path, base: str | None = None, fetch: bool = True) -> dict:
    """The staged-check decision for HEAD, the index and the working tree against the base
    (choose_base; origin/master is fetched first unless `fetch` is False). "level": "yok" (no check:
    only documentation no code reads and reports changed; changed documentation also needs a fresh
    base that received no code, and HEAD pushed as its branch; changed reports need a valid --full
    that binds them), "tamam" (code changed, and the last --full passed on exactly this code: nothing
    that differs from its commit is code, its log and reports are committed, the base received no
    code since the branch left it and is fresh, HEAD is what its branch on origin holds, and the
    rule's own files are unchanged) or "tam" (the --full is still needed, or the decision could not
    be made). "files" stays None when the decision came before git listed them."""
    out: dict = {"base": base, "files": None, "named": {}, "full": None, "base_ahead": [], "hidden": []}
    try:
        return _plan(out, root, base, fetch)
    except UnreadableSource as e:
        return {**out, "level": "tam", "why": f"Python kaynağı okunamadı ({e}): hangi belgeleri okuduğu bilinmiyor"}


def _push_problem(root: Path, fetch: bool, absent_ok: bool = False) -> tuple[str, str | None] | None:
    """(why, advice) when HEAD may not be what a pull request merges, else None. The PR merges the
    branch as origin holds it, read there with ls-remote (the exact ref: its pattern also matches
    a/refs/heads/<branch>), not from a local tracking ref that may be stale, missing or origin/master
    (review, 26 Sep 2026). The branch is HEAD's, or the one its upstream names on origin when that
    is not master (pushed as dal:other). `absent_ok`: a branch origin does not have is no pull
    request yet. On master itself (a local merge) and without remotes there is none either."""
    branch = _head_branch(root)
    if branch is None:
        return "HEAD bir dala bağlı değil: birleştirilecek hâl bilinmiyor", _ADVICE_SWITCH
    remotes = _git_lines(root, "remote")
    if remotes is None:
        return "uzaklar okunamadı", None
    if branch == "master" or not remotes:
        return None
    target, merge = branch, _git_value(root, "config", f"branch.{branch}.merge") or ""
    if _git_value(root, "config", f"branch.{branch}.remote") == "origin" and merge.startswith("refs/heads/") \
            and merge != "refs/heads/master":
        target = merge[len("refs/heads/"):]
    if not fetch:
        return f"origin'deki {target} okunmadı (--no-fetch)", _ADVICE_NO_FETCH
    ref = f"refs/heads/{target}"
    p = _git_run(root, "ls-remote", "origin", ref, timeout=60,
                 env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never"))
    if p is None or p.returncode:
        return f"origin'deki {target} okunamadı", _ADVICE_FETCH
    shas = [sha for sha, _, name in (l.partition("\t") for l in p.stdout.decode("utf-8", "replace").splitlines())
            if name == ref]
    if not shas:
        return None if absent_ok else (f"origin'de {target} dalı yok (push edilmemiş)", _ADVICE_PUSH)
    if shas[0] != _git_value(root, "rev-parse", "HEAD"):
        return f"origin'deki {target} HEAD ile aynı değil (push edilmemiş commit ya da başkasının push'u)", _ADVICE_SYNC
    return None


def base_rule_files(root: Path, base: str) -> tuple[str, ...] | None:
    """RULE_FILES as the base's scripts/check.py sets them: a branch that takes a file off its own
    list is still judged by the base's. () when the base has no such file or no RULE_FILES (older
    bases); None when it has one that cannot be read as literals (built from other names, assigned
    by unpacking, added to, or a file that does not parse): the list is unknown (review)."""
    import ast
    text = _git_value(root, "show", f"{base}:scripts/check.py")
    if text is None:
        return ()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)}
            if "RULE_FILES" not in names:
                continue
            simple = isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None \
                and all(isinstance(t, ast.Name) for t in targets)
            try:
                value = ast.literal_eval(node.value) if simple else None
            except (ValueError, TypeError, SyntaxError):
                value = None
            if not isinstance(value, (tuple, list, set, frozenset)) or not all(isinstance(v, str) for v in value):
                return None
            found |= set(value)
    return tuple(sorted(found))


def _reports_uncommitted(root: Path) -> list[str] | None:
    """Reports or the --full log that differ between the working tree, the index and HEAD: the log
    and the digests are read from disk, but a pull request merges what is committed."""
    changed = changed_since(root, "HEAD")
    return None if changed is None else [f for f in changed if is_report(f)]


def _full_advice(root: Path, full: dict) -> str | None:
    """What settles a refused --full log, when another --full is not the only way. Reports changed
    after a run whose log is not committed yet cannot be brought back, and `git restore reports/`
    would also throw the new log away (review, 26 Sep 2026)."""
    if full["why"] != REPORTS_CHANGED:
        return full.get("advice")
    uncommitted = _reports_uncommitted(root)
    if uncommitted is None or REPORT_LOG in uncommitted:
        return _ADVICE_REPORTS_LOST
    return _ADVICE_REPORTS.format(paths=", ".join(full.get("changed_reports") or []) or "?")


def _fresh_advice(state: str) -> str:
    """What makes the base fresh, by how the fetch went (fetch_origin)."""
    if state.startswith("yapılmadı"):
        return _ADVICE_NO_FETCH
    if state.startswith("başarısız"):
        return _ADVICE_FETCH
    return _ADVICE_ORIGIN                          # origin on this machine, or no origin at all


def _plan(out: dict, root: Path, base: str | None, fetch: bool) -> dict:
    # without remotes there is nothing to fetch: --no-fetch changes nothing there
    out["fetch"] = fetch_origin(root) if fetch or _git_lines(root, "remote") == [] else "yapılmadı (--no-fetch)"
    out["head"] = _git_value(root, "rev-parse", "HEAD") or "?"
    hidden = hidden_files(root)
    if hidden is None:
        return {**out, "level": "tam", "why": "git okunamadı"}
    if hidden:
        out["hidden"] = hidden
        return {**out, "level": "tam", "why": "git bazı dosyalardaki değişiklikleri göstermiyor (assume-unchanged, "
                                              "skip-worktree, süzgeç ya da kendini gizleyen .gitignore)",
                "advice": _ADVICE_HIDDEN}
    chosen = choose_base(root, base)
    if chosen[0] is None:
        return {**out, "level": "tam", "why": chosen[1], "advice": chosen[2]}
    out.update(base=chosen[0], merge_base=chosen[1],
               base_tip=_git_value(root, "rev-parse", "--verify", "--quiet", f"{chosen[0]}^{{commit}}") or "?")
    origin_tip = _git_value(root, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/master^{commit}")
    fresh = out["fetch"] == "uzak yok" or (out["fetch"] == "tamam" and out["base_tip"] == origin_tip)

    def stale() -> dict:
        # built when it is returned: a copy taken here would render the files found below as none
        return {**out, "level": "tam", "why": f"tabanın güncelliği bilinmiyor (fetch: {out['fetch']})",
                "advice": _fresh_advice(out["fetch"])}

    files = changed_since(root, out["merge_base"])
    if files is None:
        return {**out, "level": "tam", "why": "git değişen dosyaları veremedi"}
    out["files"] = {f: "?" for f in files}
    named = docs_named_by_code(root, [f for f in files if is_doc(f)])
    out.update(files=classify(files, named), named=named)
    kinds = set(out["files"].values())
    # Code the base received after the branch left it, from the merge base choose_base found (the
    # same one: `HEAD...base` picks its own when there are several): merged, it is code no run has
    # seen, and it may read a document this branch changed (the scan above saw only this branch's
    # code). Local master's unpushed commits count too: a local merge brings them in.
    diff = ("diff", "--name-only", "-z", "--no-renames", "--ignore-submodules=none")
    ahead = _git_lines(root, *diff, out["merge_base"], out["base"], "--")
    if ahead is None:
        return {**out, "level": "tam", "why": "tabanın dal ayrıldıktan sonra ne aldığı okunamadı"}
    local: list[str] = []
    if out["base"] != "master" and _git_value(root, "rev-parse", "--verify", "--quiet", "master^{commit}"):
        unpushed = _git_run(root, "rev-list", "-1", f"{out['base']}..master")
        if unpushed is None or unpushed.returncode:
            return {**out, "level": "tam", "why": "yerel master'ın push edilmemiş commit'leri okunamadı"}
        if unpushed.stdout.strip():
            mbs = (_git_value(root, "merge-base", "--all", "master", "HEAD") or "").split()
            if len(mbs) != 1:
                return {**out, "level": "tam", "why": "yerel master'da push edilmemiş commit var ve HEAD ile "
                                                      f"{'birden çok' if mbs else 'hiç'} ortak atası var",
                        "advice": _ADVICE_LOCAL_MASTER}
            more = _git_lines(root, *diff, mbs[0], "master", "--")
            if more is None:
                return {**out, "level": "tam", "why": "yerel master'ın push edilmemiş commit'leri okunamadı"}
            local = _code_of(root, more)
    remote = _code_of(root, ahead)
    out["base_ahead"] = sorted(set(remote) | set(local))
    merge_first = f"önce {out['base']} bu dala birleştirilir, sonra --plan yeniden"
    if remote:
        received = {"why": f"taban bu daldan sonra kod aldı: {merge_first}", "advice": _ADVICE_MERGE}
    else:                                          # only local master has it: merging origin/master is a no-op
        received = {"why": f"yerel master'da push edilmemiş kod var ({', '.join(local)}): yerel birleştirme onu da "
                           f"getirir", "advice": _ADVICE_LOCAL_MASTER}
    if not kinds:
        # nothing here to merge; but origin's copy of the branch may hold what this checkout lacks
        pushed = _push_problem(root, fetch, absent_ok=True)
        if pushed:
            return {**out, "level": "tam", "why": f"burada değişiklik yok, ama {pushed[0]}", "advice": pushed[1]}
        return {**out, "level": "yok", "why": "hiçbir şey değişmedi"}
    if "kod" not in kinds:
        if "belge" in kinds:
            if out["base_ahead"]:                  # that code may read a document this branch changed
                return {**out, "level": "tam", "why": received["why"] + "; o kod değişen belgeleri okuyor olabilir",
                        "advice": received["advice"]}
            if not fresh:
                return stale()
        if "rapor" in kinds:
            # a report is a --full's output: it rides on a run that produced it for this code
            full = out["full"] = last_full_run(root)
            if not full["ok"]:
                return {**out, "level": "tam", "why": f"rapor değişti ama geçerli bir --full'a bağlı değil: {full['why']}",
                        "advice": _full_advice(root, full)}
            since = changed_since(root, full["commit"])
            full["code_since"] = None if since is None else _code_of(root, since)
            if full["code_since"] != []:
                return {**out, "level": "tam", "why": f"rapor değişti; son --full ({full['short']}) bu kodda değil"}
            if _reports_uncommitted(root) != []:
                return {**out, "level": "tam", "why": "raporlar ya da günlük commit edilmemiş", "advice": _ADVICE_COMMIT}
        # what a pull request merges is the pushed branch: it may hold what this checkout lacks
        pushed = _push_problem(root, fetch)
        if pushed:
            return {**out, "level": "tam", "why": pushed[0], "advice": pushed[1]}
        return {**out, "level": "yok", "why": "kod değişmedi"}
    # code: first what no --full can settle, so the run it asks for is not thrown away (review)
    if out["base_ahead"]:
        return {**out, "level": "tam", "why": received["why"] + "; --full birleşik hâlde", "advice": received["advice"]}
    if not fresh:
        return stale()
    full = out["full"] = last_full_run(root)
    if not full["ok"]:
        return {**out, "level": "tam", "why": f"kod değişti; son --full bu kodu kapsamıyor: {full['why']}",
                "advice": _full_advice(root, full)}
    since = changed_since(root, full["commit"])
    if since is None:
        return {**out, "level": "tam", "why": "son --full'dan bu yana değişenler okunamadı"}
    full["code_since"] = _code_of(root, since)
    if full["code_since"]:
        return {**out, "level": "tam", "why": f"kod, son --full'dan ({full['short']}) bu yana değişti"}
    if _reports_uncommitted(root) != []:
        return {**out, "level": "tam", "why": "raporlar ya da günlük commit edilmemiş", "advice": _ADVICE_COMMIT}
    pushed = _push_problem(root, fetch)
    if pushed:
        return {**out, "level": "tam", "why": pushed[0], "advice": pushed[1]}
    base_rules = base_rule_files(root, out["base"])
    if base_rules is None:
        return {**out, "level": "tam", "why": f"son --full ({full['gates']}, {full['short']}) bu kodda geçti, ama "
                                              f"{out['base']}'in kural listesi (RULE_FILES) okunamadı",
                "advice": _ADVICE_RULES}
    rules = sorted(f for f in set(RULE_FILES) | set(base_rules) if f in out["files"])
    if rules:
        return {**out, "level": "tam", "why": f"son --full ({full['gates']}, {full['short']}) bu kodda geçti ve başka her "
                                              f"koşul tuttu, ama kuralın kendi dosyaları değişti ({', '.join(rules)})",
                "advice": _ADVICE_RULES}
    return {**out, "level": "tamam", "why": f"son --full ({full['gates']}, {full['short']}) bu kodda geçti"}


_PLAN_ADVICE = {
    "yok": "kontrol gerekmez",
    "tamam": "tam kontrol bu kodda yapılmış; birleştirmeden önce başka kontrol gerekmez",
    "tam": "çalışırken hızlı check.py; birleştirmeden önce son hâlde bir kez check.py --full",
}
# A TAM that another --full would not settle says what would.
_ADVICE_HIDDEN = ("gizleme kaldırılır (git update-index --no-assume-unchanged / --no-skip-worktree; süzgeç özniteliği "
                  "silinir; izlenmeyen .gitignore silinir ya da commit edilir), sonra --plan yeniden")
_ADVICE_MERGE = "taban bu dala birleştirilir, sonra --plan yeniden (kod değiştiyse birleşik hâlde --full)"
_ADVICE_FETCH = "git fetch origin master çalışınca --plan yeniden; çalışmıyorsa birleştirme beklenir"
_ADVICE_NO_FETCH = "--no-fetch'siz koşulur: taban ve dalın origin'deki hâli ancak okununca karar verilir"
_ADVICE_ORIGIN = ("--plan, origin'i sunucudaki depo (GitHub) olan bir checkout'ta koşulur: bu checkout master'ın "
                  "tazeliğini bilemez")
_ADVICE_PUSH = "commit'ler push edilir (PR dalı origin'deki hâliyle birleştirir), sonra --plan yeniden"
_ADVICE_SYNC = ("HEAD origin'deki dalla aynı yapılır (push edilmemiş commit'ler push edilir, başkasınınkiler çekilir), "
                "sonra --plan yeniden")
_ADVICE_SWITCH = "birleştirilecek dala geçilir (git switch <dal>), sonra --plan yeniden"
_ADVICE_BASE = "--plan bir daldan, origin/master (ya da master) varken koşulur; birleştirme PR ile ya da orada yapılır"
_ADVICE_SHALLOW = "ortak ata getirilir (git fetch --unshallow origin ya da --deepen), sonra --plan yeniden"
_ADVICE_RULES = "--full başka bir şey kanıtlamaz: kuralın kendi değişikliğini birleştirme kararı kişinin"
_ADVICE_REPORTS = ("değişen raporlar ({paths}) --full'un yazdığı hâle döndürülür, günlüğe dokunulmaz (commit "
                   "edilmemişse git restore -- <yol>, sonradan eklenen rapor silinir, commit edildiyse o değişiklik geri "
                   "alınır) ya da --full yeniden koşulur; sonra --plan yeniden")
_ADVICE_REPORTS_LOST = ("koşunun raporları commit edilmeden değişti, geri getirilemez: --full yeniden koşulur ve günlükle "
                        "raporlar hemen, değiştirilmeden commit edilir")
_ADVICE_LOCAL_MASTER = ("yerel master'ın push edilmemiş commit'leri önce PR ile birleştirilir ya da yerel master "
                        "origin/master'a döndürülür (git branch -f master origin/master), sonra --plan yeniden")
_ADVICE_COMMIT = "--full'un raporları ve günlüğü değiştirilmeden commit ve push edilir, sonra --plan yeniden"
_ADVICE_LOCK = (".venv requirements.lock'a eşitlenir (pip install -r requirements.lock ya da uv pip sync "
                "requirements.lock), sonra --full")


def render_plan(p: dict) -> list[str]:
    lines = ["== kademeli kontrol (DECISIONS §59) =="]
    if p.get("fetch"):
        lines.append(f"  origin/master fetch: {p['fetch']}")
    if p.get("head"):
        lines.append(f"  HEAD: {p['head'][:7]}")
    if p.get("merge_base"):
        lines.append(f"  taban: {p['base']} {p.get('base_tip', '?')[:7]} (ortak ata {p['merge_base'][:7]})")
    files = p.get("files")
    if files is None:                              # decided before git listed them: not "0 dosya"
        lines.append("  değişen: okunmadı")
        files = {}
    else:
        counts = {c: sum(1 for v in files.values() if v == c) for c in ("kod", "belge", "rapor", "?")}
        unsorted = f", sınıflanmadı {counts['?']}" if counts["?"] else ""     # not zero of each kind
        lines.append(f"  değişen: {len(files)} dosya (kod {counts['kod']}, belge {counts['belge']}, "
                     f"rapor {counts['rapor']}{unsorted})")
    order = ("kod", "belge", "rapor", "?")
    for f, c in sorted(files.items(), key=lambda kv: (order.index(kv[1]), kv[0])):
        why = f"  (okuyan: {p['named'][f]})" if f in p.get("named", {}) else ""
        lines.append(f"    {c:<5} {f}{why}")
    for f in p.get("hidden") or []:
        lines.append(f"    gizli {f}")
    for f in p.get("base_ahead") or []:
        lines.append(f"    taban {f}  (taban bu daldan sonra aldı)")
    full = p.get("full")
    if full is not None:
        state = "geçerli" if full["ok"] else f"geçersiz: {full['why']}"
        where = f"{full.get('gates', '?')} · {full.get('when', '?')} · {full.get('branch', '?')} @ {full.get('short', '?')}"
        lines.append(f"  son --full: {where} ({state})")
        for f in full.get("code_since") or []:
            lines.append(f"    o koşudan bu yana değişen kod: {f}")
    lines.append(f"  karar: {p['level'].upper()} · {p['why']} → {p.get('advice') or _PLAN_ADVICE[p['level']]}")
    return lines


def plan_report(root: Path, base: str | None = None, fetch: bool = True) -> tuple[int, list[str]]:
    """(exit code, lines): 0 when nothing more is needed before merging, 1 when something is (the
    verdict line says what: a --full, a push, a fetch, a merge of the base). Never raises: a failure
    to decide is itself the decision "tam"."""
    try:
        p = plan(root, base, fetch)
        return (0 if p["level"] in ("yok", "tamam") else 1), render_plan(p)
    except Exception as e:  # noqa: BLE001 - an undecidable change needs the full check
        return 1, ["== kademeli kontrol (DECISIONS §59) ==",
                   f"  karar: TAM · karar verilemedi ({type(e).__name__}: {e}) → {_PLAN_ADVICE['tam']}"]


def unexplained_doc_reads(root: Path, opened) -> list[str]:
    """The files among `opened` (paths a process opened) inside `root` that the staged-check rule
    does not count as code (classify): a document neither named nor in DOCS_READ_UNNAMED, or a
    report (the rule never counts one as code, so no test may depend on one). Ignored: paths
    outside the repository, under _SKIP_DIRS, and gone by now (pytest's own temporary cache
    directory). Raises UnreadableSource."""
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


def _utc() -> str:
    """The log's time stamps: UTC, the same on every machine and in the cloud."""
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def _count(files) -> str:
    return "?" if files is None else str(len(files))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="Lean, adversaryal ve kalibrasyonu da koştur")
    ap.add_argument("--plan", action="store_true",
                    help="yalnız kademeli kontrol kararını yaz (çıkış 0: başka bir şey gerekmez, 1: gerekli; "
                         "ne olduğunu karar satırı söyler)")
    ap.add_argument("--no-fetch", action="store_true",
                    help="origin/master'ı çekme, dalın origin'deki hâlini okuma: uzaklı bir depoda master dışındaki "
                         "her dalda, master'da belge ya da kod değiştiyse karar TAM olur")
    args = ap.parse_args(argv)
    if args.plan:
        rc, lines = plan_report(ROOT, fetch=not args.no_fetch)
        print("\n".join(lines))
        return rc
    if not args.full:
        rc = _main(args)
        print()
        print("\n".join(plan_report(ROOT, fetch=not args.no_fetch)[1]))   # a reminder: the exit code is the gates'
        return rc
    # The full run writes its own log. The 21/21 run of 23 Sep lived only in a session's temp
    # file while reports/check_full.log still said 12/12 from 19 Sep; the header ties the log
    # to the code it measured, and the closing lines show the tree was the same at the end and
    # bind the reports the run wrote: the staged-check rule accepts the log as proof for that
    # commit only then (last_full_run).
    log = ROOT / "reports" / "check_full.log"
    with log.open("w", encoding="utf-8") as fh:
        out = sys.stdout
        sys.stdout = _Tee(out, fh)
        try:
            # The reports the run writes again are not counted (REWRITTEN: the open log among them;
            # counted, it made the header say 1 on a clean tree until 26 Sep 2026), and a quick
            # check.py before the --full leaves reports/eval_report.md modified. Any other report
            # changed before the run is (review, 26 Sep 2026).
            dirty = dirty_files(ROOT)
            print(f"check.py --full · {_utc()} · "
                  f"{_git('rev-parse', '--abbrev-ref', 'HEAD')} @ {_git('rev-parse', '--short', 'HEAD')} · "
                  f"commit edilmemiş değişiklik: {_count(dirty)} dosya")
            env, lock = environment_lines(ROOT)
            print(env)
            print(lock)
            # measured all the same, but not proof for --plan: the log names no commit that holds this code
            if dirty is None:
                print("UYARI: git değişiklikleri veremedi, bu koşu --plan için kanıt olmaz")
            elif dirty:
                print(f"UYARI: ağaç temiz değil, bu koşu --plan için kanıt olmaz: {', '.join(dirty[:10])}"
                      + (f" ve {len(dirty) - 10} dosya daha" if len(dirty) > 10 else ""))
            if not lock.endswith("uyuşmayan: yok"):
                print("UYARI: ortam requirements.lock'la uyuşmuyor ya da denetlenemedi, bu koşu --plan için kanıt olmaz")
            print()
            rc = _main(args)
            print(f"\ncheck.py --full sonu · {_utc()} · "
                  f"{_git('rev-parse', '--abbrev-ref', 'HEAD')} @ {_git('rev-parse', '--short', 'HEAD')} · "
                  f"commit edilmemiş değişiklik: {_count(dirty_files(ROOT))} dosya")
            print("check.py --full raporları · " + " · ".join(f"{k} {v}" for k, v in report_digests(ROOT).items()))
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
