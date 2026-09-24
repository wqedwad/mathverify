"""scripts/check.py: a harness that crashes, writes no report or leaves a stale one must fail its
gates under the same names and count, and no Lean gate may pass when Lean did not run or was lost
during the run, nor the FP and junk gates on a statement Lean never answered (all attempts timed out).

No real harness runs here: `check.run` is replaced by a fake that writes fixture reports into a
temporary REPORTS directory (or does not, and returns the exit code under test). The run_lean
tests at the end drive harness.run_lean itself with Lean faked.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_script_harness", ROOT / "scripts" / "check.py")
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

REPORT = {"run_eval": "eval_results.json", "run_lean": "lean_results.json",
          "adversarial": "adversarial_results.json", "soundness_fuzz": "soundness_results.json",
          "calibrate": "calibration.json"}
OWNED = {"run_eval": check.EVAL_GATES, "run_lean": check.LEAN_GATES, "adversarial": check.ADVERSARIAL_GATES,
         "soundness_fuzz": check.SOUNDNESS_GATES, "calibrate": check.CALIBRATION_GATES}
GOOD = {
    "run_eval": {"summary": {"answer_level_ABC": {"pos_precision": 1.0, "neg_precision": 1.0, "coverage": 0.9},
                             "solution_level_ABCD": {"pos_precision": 0.99}, "B_false_rejection": 0.0,
                             "leakage_test_passed": True, "D_detection": 0.5,
                             "restructure_fidelity": {"payload_faithful": 3, "payload_n": 3},
                             "l5_applicability": {"n": 1, "total": 2}}},
    "run_lean": {"lean_available": True, "lean_available_end": True,
                 "records": [{"id": "x-001", "statement": True, "lean_reached": True, "lean_answered": True,
                              "errors": [], "clean": True, "answer_right": True},
                             {"id": "x-002", "statement": False, "clean": None, "answer_right": False}],
                 "junk_probe": [{"label": "0/0 = 0", "statement": True, "lean_reached": True, "lean_answered": True,
                                 "errors": [], "certified": False}]},
    "adversarial": {"preserving": {"flipped": 0}, "changing": {"accepted_wrong": 0}, "n_attacks": 100,
                    "per_attack": {"neg": 1, "mc:swap": 1, "step:drop": 1}},
    "soundness_fuzz": {"wrong": {"false_accepts": 0, "n": 5}, "equiv": {"false_rejects": 0, "n": 5},
                       "non_answer": {"accepted": 0, "n": 3},
                       "steps": {"false_rejects": [], "equiv": {"n": 4}, "missed_breaks": [{"accepted": True}]}},
    "calibrate": {"results": {"test": {"pos_precision": 1.0, "neg_precision": 1.0}}},
}
QUICK = ["birim testleri", "pyflakes temiz", *(n for n, _ in check.EVAL_GATES), "ölçülmeyen görev türü"]
FULL = QUICK + [n for label in ("run_lean", "adversarial", "soundness_fuzz", "calibrate") for n, _ in OWNED[label]]


class FakeRun:
    """Stands in for check.run: pytest/pyflakes pass; each harness writes REPORT[label] unless told not to."""

    def __init__(self, reports: Path, rc=None, write=None, content=None):
        self.reports, self.rc, self.content = reports, rc or {}, content or {}
        self.write = set(REPORT) if write is None else set(write)
        self.report_existed = {}                     # did the report exist when the harness started?

    def __call__(self, cmd, label):
        if label == "pytest":
            return 0, "3 passed in 0.10s"
        if label == "pyflakes":
            return 0, ""
        path = self.reports / REPORT[label]
        self.report_existed[label] = path.exists()
        if label in self.write:
            data = self.content.get(label, GOOD[label])
            path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return self.rc.get(label, 0), "Traceback (most recent call last):\nRuntimeError: boom\n"


REAL_GATE = check.gate


def _gates(monkeypatch, tmp_path, full=True, **fake):
    """Run check._main against the fake harnesses; return (exit code, gates by name, gate names in order)."""
    captured = []
    monkeypatch.setattr(check, "REPORTS", tmp_path)
    monkeypatch.setattr(check, "run", FakeRun(tmp_path, **fake))
    monkeypatch.setattr(check, "gate", lambda *a, **k: captured.append(REAL_GATE(*a, **k)) or captured[-1])
    rc = check._main(argparse.Namespace(full=full))
    return rc, {g["name"]: g for g in captured}, [g["name"] for g in captured]


def test_happy_path_is_unchanged_and_counts_are_24_and_12(monkeypatch, tmp_path):
    rc, by_name, names = _gates(monkeypatch, tmp_path)
    assert rc == 0 and names == FULL and len(names) == 24
    assert all(g["ok"] for g in by_name.values())
    assert by_name["Lean erişilebilir"]["value"] == "evet (1 sertifika)"
    assert by_name["Lean sertifika"]["value"] == "1/2" and by_name["Lean FP"]["value"] == 0
    assert by_name["Lean junk-value sertifikası"]["value"] == "0/1"
    assert by_name["saldırı başarısı"]["value"] == "0.000%"
    assert by_name["saldırı yüzeyleri"]["value"] == "cevap,şık,adım"
    assert by_name["kalibre test precision (poz/neg)"]["value"] == "1.0/1.0"
    assert names.index("Lean erişilebilir") + 1 == names.index("Lean FP")
    rc, by_name, names = _gates(monkeypatch, tmp_path, full=False)
    assert rc == 0 and names == QUICK and len(names) == 12


def test_owned_names_and_targets_match_the_success_path():
    """The (name, target) pairs a failed step emits are exactly the ones its report produces."""
    builders = {"run_eval": check.eval_gates, "run_lean": check.lean_gates, "adversarial": check.adversarial_gates,
                "soundness_fuzz": check.soundness_gates, "calibrate": check.calibration_gates}
    for label, build in builders.items():
        assert [(g["name"], g["target"]) for g in build(GOOD[label])] == list(OWNED[label]), label


@pytest.mark.parametrize("label", sorted(REPORT))
def test_a_crashed_harness_fails_its_gates_under_the_same_names(monkeypatch, tmp_path, label):
    # the harness even wrote a perfect report before crashing: the exit code alone decides
    rc, by_name, names = _gates(monkeypatch, tmp_path, rc={label: 3})
    assert rc == 1 and names == FULL
    owned = [n for n, _ in OWNED[label]]
    for n in owned:
        assert not by_name[n]["ok"] and by_name[n]["value"] == "çalışmadı (çıkış 3)", n
    assert all(g["ok"] for n, g in by_name.items() if n not in owned)


@pytest.mark.parametrize("label", sorted(REPORT))
def test_a_missing_report_fails_its_gates(monkeypatch, tmp_path, label):
    rc, by_name, names = _gates(monkeypatch, tmp_path, write=set(REPORT) - {label})
    assert rc == 1 and names == FULL
    assert [by_name[n]["value"] for n, _ in OWNED[label]] == ["rapor yok"] * len(OWNED[label])
    assert not any(by_name[n]["ok"] for n, _ in OWNED[label])


@pytest.mark.parametrize("label", sorted(REPORT))
def test_a_stale_report_is_deleted_not_read(monkeypatch, tmp_path, label):
    """A perfect report left by an earlier run must not pass for a run that crashed."""
    for lb in REPORT:
        (tmp_path / REPORT[lb]).write_text(json.dumps(GOOD[lb]), encoding="utf-8")
    fake_rc = {label: 1}
    rc, by_name, names = _gates(monkeypatch, tmp_path, rc=fake_rc, write=set(REPORT) - {label})
    fake = check.run
    assert fake.report_existed == {lb: False for lb in REPORT}      # every report deleted before its harness
    assert not (tmp_path / REPORT[label]).exists()
    assert rc == 1 and names == FULL
    assert [by_name[n]["value"] for n, _ in OWNED[label]] == ["çalışmadı (çıkış 1)"] * len(OWNED[label])


@pytest.mark.parametrize("content", ["{", "[]", json.dumps({"unexpected": 1})])
def test_an_unreadable_report_fails_its_gates(monkeypatch, tmp_path, content):
    for label in REPORT:
        rc, by_name, names = _gates(monkeypatch, tmp_path, content={label: content})
        assert rc == 1 and names == FULL, (label, content)
        assert all(not by_name[n]["ok"] and by_name[n]["value"].startswith("rapor okunamadı")
                   for n, _ in OWNED[label]), (label, content)


@pytest.mark.parametrize("flag", [False, None, "true", 1])
def test_lean_not_available_fails_all_four_lean_gates(monkeypatch, tmp_path, flag):
    lean = dict(GOOD["run_lean"])
    if flag is None:
        del lean["lean_available"]                  # a report that does not say Lean ran
    else:
        lean["lean_available"] = flag
    # exactly what a box with no Lean produced before: 0 certificates, junk probe all uncertified
    lean["records"] = [{"clean": None, "answer_right": True}]
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 1 and names == FULL
    values = [by_name[n]["value"] for n, _ in check.LEAN_GATES]
    assert values == ["hayır", "Lean çalışmadı", "Lean çalışmadı", "Lean çalışmadı"]
    assert not any(by_name[n]["ok"] for n, _ in check.LEAN_GATES)
    assert all(g["ok"] for n, g in by_name.items() if n not in dict(check.LEAN_GATES))


def test_lean_available_without_a_certificate_fails_only_the_access_gate(monkeypatch, tmp_path):
    lean = dict(GOOD["run_lean"], records=[{"statement": True, "lean_reached": True, "errors": [],
                                            "clean": False, "answer_right": True}])
    rc, by_name, _ = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 1
    assert by_name["Lean erişilebilir"]["value"] == "evet (0 sertifika)" and not by_name["Lean erişilebilir"]["ok"]
    assert by_name["Lean FP"]["ok"] and by_name["Lean junk-value sertifikası"]["ok"]


# --- Lean lost DURING the run -------------------------------------------------------------------
# lean_available is probed once, before the sweep. When the REPL was OOM-killed afterwards and could
# not respawn, prove_statement returned proved=False with a `lean_unavailable` error for every later
# statement, run_lean did not save that error, and all four Lean gates passed: the reviewer's
# simulation showed "evet (1 sertifika)" and junk "0/17" although no junk statement reached Lean.
UNAVAILABLE = "lean_unavailable: REPL did not start: ['lean timeout after 300s']"
LOST = {"statement": True, "lean_reached": False, "errors": [UNAVAILABLE]}


def _lost_item(d):
    d["records"].append(dict(LOST, id="x-003", clean=None, answer_right=False))


def _lost_junk(d):
    d["junk_probe"][0].update(LOST)


def _end_lost(d):
    d["lean_available_end"] = False


def _end_missing(d):
    del d["lean_available_end"]            # a report from before the re-probe existed


def _reached_missing(d):
    del d["records"][0]["lean_reached"]


def _statement_field_missing(d):
    d["records"][1] = {"id": "x-002", "clean": None, "answer_right": False}   # counts as having one


def _error_only(d):
    d["records"][0]["errors"] = [UNAVAILABLE]      # lean_reached claims True: the error still counts


LOSS_CASES = {  # mutation of GOOD["run_lean"] -> expected "Lean erişilebilir" value
    "item_lost": (_lost_item, "yarıda kesildi (Lean'e ulaşmayan ifade 1/3, sonda erişilebilir: evet)"),
    "junk_lost": (_lost_junk, "yarıda kesildi (Lean'e ulaşmayan ifade 1/2, sonda erişilebilir: evet)"),
    "end_lost": (_end_lost, "yarıda kesildi (Lean'e ulaşmayan ifade 0/2, sonda erişilebilir: hayır)"),
    "end_missing": (_end_missing, "yarıda kesildi (Lean'e ulaşmayan ifade 0/2, sonda erişilebilir: hayır)"),
    "reached_missing": (_reached_missing, "yarıda kesildi (Lean'e ulaşmayan ifade 1/2, sonda erişilebilir: evet)"),
    "statement_field_missing": (_statement_field_missing,
                                "yarıda kesildi (Lean'e ulaşmayan ifade 1/3, sonda erişilebilir: evet)"),
    "error_only": (_error_only, "yarıda kesildi (Lean'e ulaşmayan ifade 1/2, sonda erişilebilir: evet)"),
}


@pytest.mark.parametrize("case", sorted(LOSS_CASES))
def test_lean_lost_mid_run_fails_all_four_lean_gates(monkeypatch, tmp_path, case):
    mutate, first = LOSS_CASES[case]
    lean = json.loads(json.dumps(GOOD["run_lean"]))
    mutate(lean)
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 1 and names == FULL and len(names) == 24
    values = [by_name[n]["value"] for n, _ in check.LEAN_GATES]
    assert values == [first, "Lean yarıda kesildi", "Lean yarıda kesildi", "Lean yarıda kesildi"]
    assert not any(by_name[n]["ok"] for n, _ in check.LEAN_GATES)
    assert all(g["ok"] for n, g in by_name.items() if n not in dict(check.LEAN_GATES))


def test_no_statement_needs_no_lean(monkeypatch, tmp_path):
    """A record without a statement never went to Lean, so it neither needs nor has lean_reached."""
    lean = GOOD["run_lean"]
    assert lean["records"][1]["statement"] is False and "lean_reached" not in lean["records"][1]
    assert check.lean_unreached(lean) == []
    lean = json.loads(json.dumps(lean))
    lean["junk_probe"].append({"label": "log 0 = 0", "statement": False, "certified": False})
    rc, by_name, _ = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 0 and by_name["Lean junk-value sertifikası"]["value"] == "0/2"


# --- Lean reached but never answered --------------------------------------------------------------
# When every tactic attempt on a statement hits the timeout, the REPL is killed and respawned each
# time: no lean_unavailable error, lean_reached True, and the junk probe read "0/17" although Lean
# had judged no junk statement (reviewer's timeout_vacuity.py). Each attempt now counts as answered
# only when Lean itself replied, and every junk statement and every wrong-answer item statement needs
# at least one such attempt (a right-answer item that only timed out just has no certificate).
TIMEOUT = "lean timeout after 45s"


def _attempt(ok=False, *errors):
    return {"source": "tactic", "proof": "norm_num", "ok": ok, "errors": list(errors), "ms": 1}


@pytest.mark.parametrize("attempt, answered", [
    (_attempt(True), True),                                             # compiled
    (_attempt(False, "linarith failed"), True),                         # Lean rejected the proof
    (_attempt(False, TIMEOUT, "unsolved goals"), True),                 # any real Lean error counts
    (_attempt(False, TIMEOUT), False),
    (_attempt(False, "empty reply (REPL died)"), False),
    (_attempt(False, "write failed: [Errno 32] Broken pipe"), False),
    (_attempt(False, "bad JSON from REPL: Expecting value: {"), False),
    (_attempt(False), False),                                           # no verdict at all: fail closed
])
def test_attempt_answered(attempt, answered):
    from harness import run_lean
    assert run_lean.attempt_answered(attempt) is answered


_FAKE_REPL = {  # child script standing in for the REPL -> is the attempt Lean's own answer?
    "compiled": ('print(json.dumps({"env": 1})); print("")', True),
    "lean_error": ('print(json.dumps({"messages": [{"severity": "error", "data": "linarith failed"}]})); print("")',
                   True),
    "timeout": ("time.sleep(60)", False),
    "died": ("sys.exit(0)", False),
    "bad_json": ('print("not json"); print("")', False),
    "repl_message": ('print(json.dumps({"message": "Unknown environment."})); print("")', False),
    "write_failed": (None, False),
}


@pytest.mark.parametrize("case", sorted(_FAKE_REPL))
def test_attempt_answered_on_what_lean_client_really_returns(case):
    """NO_VERDICT must match the errors LeanClient._send_raw actually produces, so drive it against a
    child process that answers, stays silent, dies, garbles, or is gone before the write."""
    import subprocess
    import mathverify.formal.lean_client as lc
    from harness import run_lean
    body, answered = _FAKE_REPL[case]
    script = ("import json, sys, time\n" + ("" if body is None else "sys.stdin.readline()\n" + body
                                           + "\nsys.stdout.flush()\ntime.sleep(5)\n"))
    extra = {"start_new_session": True} if sys.platform != "win32" else {}
    client = lc.LeanClient()
    client._proc = subprocess.Popen([sys.executable, "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1, **extra)
    proc = client._proc
    try:
        if body is None:
            proc.wait(timeout=30)                    # gone before anything is sent
        r = client._send_raw({"cmd": "example : True := trivial", "env": 0}, timeout=3.0)
    finally:
        client._kill()
        try:                                         # the failed write is still buffered: drop it here,
            proc.stdin.close()                       # not in a finalizer (unraisable-exception warning)
        except OSError:
            pass
    attempt = {"source": "tactic", "proof": "norm_num", "ok": r.clean, "errors": r.errors[:2], "ms": round(r.ms)}
    assert run_lean.attempt_answered(attempt) is answered, (case, r.errors)
    if not answered and case != "repl_message":
        assert r.errors and str(r.errors[0]).startswith(run_lean.NO_VERDICT), (case, r.errors)


def test_lean_fields_of_an_all_timeouts_statement():
    """The reviewer's prove_statement result: three ladder tactics, each timed out."""
    from harness import run_lean
    r = {"proved": False, "errors": [], "attempts": [dict(_attempt(False, TIMEOUT), proof=t, ms=45000)
                                                     for t in ("simp", "norm_num", "positivity")]}
    assert run_lean.lean_fields(r) == {"lean_reached": True, "lean_answered": False, "n_attempts": 3,
                                       "n_unanswered": 3, "errors": []}
    r["attempts"][1] = _attempt(False, "linarith failed")
    assert run_lean.lean_fields(r)["lean_answered"] is True and run_lean.lean_fields(r)["n_unanswered"] == 2
    assert run_lean.lean_fields({"proved": False, "errors": [], "attempts": []})["lean_answered"] is False


def _junk_timed_out(d):
    d["junk_probe"][0]["lean_answered"] = False


def _junk_answer_missing(d):
    del d["junk_probe"][0]["lean_answered"]          # a report from before the field existed


def _one_of_two(d):
    d["junk_probe"].append(dict(d["junk_probe"][0], label="log 0 = 0"))
    d["junk_probe"][0]["lean_answered"] = False


def _certified_and_unanswered(d):
    d["junk_probe"].append(dict(d["junk_probe"][0], label="log 0 = 0", certified=True))
    d["junk_probe"][0]["lean_answered"] = False


def _reviewer_17(d):
    """timeout_vacuity.py: 17 junk statements, every attempt on each timed out."""
    from harness import run_lean
    r = {"proved": False, "errors": [], "attempts": [_attempt(False, TIMEOUT)] * 3}
    d["junk_probe"] = [dict(label=f"j{i}", statement=True, certified=False, proved=False, **run_lean.lean_fields(r))
                       for i in range(17)]


UNANSWERED_CASES = {  # mutation of GOOD["run_lean"] -> expected junk gate value
    "junk_timed_out": (_junk_timed_out, "Lean cevap vermedi 1/1"),
    "junk_answer_missing": (_junk_answer_missing, "Lean cevap vermedi 1/1"),
    "one_of_two": (_one_of_two, "Lean cevap vermedi 1/2"),
    "certified_and_unanswered": (_certified_and_unanswered, "Lean cevap vermedi 1/2, sertifika 1/2"),
    "reviewer_17": (_reviewer_17, "Lean cevap vermedi 17/17"),
}


@pytest.mark.parametrize("case", sorted(UNANSWERED_CASES))
def test_an_unanswered_junk_statement_fails_the_junk_gate(monkeypatch, tmp_path, case):
    mutate, value = UNANSWERED_CASES[case]
    lean = json.loads(json.dumps(GOOD["run_lean"]))
    mutate(lean)
    assert check.lean_unreached(lean) == []          # Lean was there the whole time
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 1 and names == FULL and len(names) == 24
    junk = by_name["Lean junk-value sertifikası"]
    assert junk["value"] == value and not junk["ok"] and junk["target"] == 0
    assert all(g["ok"] for n, g in by_name.items() if n != "Lean junk-value sertifikası")
    assert by_name["Lean erişilebilir"]["value"] == "evet (1 sertifika)"


def _timed_out_item(answer_right, **extra):
    return dict({"id": "x-003", "statement": True, "lean_reached": True, "lean_answered": False, "errors": [],
                 "clean": None, "answer_right": answer_right}, **extra)


def test_a_right_answer_item_that_only_timed_out_fails_no_gate(monkeypatch, tmp_path):
    """Its whole ladder timed out: it only lost its certificate, and no gate is about it."""
    lean = json.loads(json.dumps(GOOD["run_lean"]))
    lean["records"].append(_timed_out_item(True))
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 0 and names == FULL and all(g["ok"] for g in by_name.values())
    assert by_name["Lean sertifika"]["value"] == "1/3" and by_name["Lean FP"]["value"] == 0
    assert by_name["Lean junk-value sertifikası"]["value"] == "0/1"


WRONG_ITEM_CASES = {  # records appended to GOOD["run_lean"] -> expected "Lean FP" value
    "timed_out": ([_timed_out_item(False)], "Lean cevap vermedi 1/1"),
    "field_missing": ([{k: v for k, v in _timed_out_item(False).items() if k != "lean_answered"}],
                      "Lean cevap vermedi 1/1"),
    "one_of_two": ([_timed_out_item(False), _timed_out_item(False, id="x-004", lean_answered=True)],
                   "Lean cevap vermedi 1/2"),
    "with_an_fp": ([_timed_out_item(False), _timed_out_item(False, id="x-004", lean_answered=True, clean=True)],
                   "Lean cevap vermedi 1/2, FP 1"),
}


@pytest.mark.parametrize("case", sorted(WRONG_ITEM_CASES))
def test_an_unanswered_wrong_answer_item_fails_the_fp_gate(monkeypatch, tmp_path, case):
    """An FP count of 0 is a claim about every wrong-answer statement; one Lean never judged makes it vacuous."""
    extra, value = WRONG_ITEM_CASES[case]
    lean = json.loads(json.dumps(GOOD["run_lean"]))
    lean["records"] += json.loads(json.dumps(extra))
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 1 and names == FULL and len(names) == 24
    fp = by_name["Lean FP"]
    assert fp["value"] == value and not fp["ok"] and fp["target"] == 0
    assert all(g["ok"] for n, g in by_name.items() if n != "Lean FP")


def _simulated_sweep(monkeypatch, tmp_path, scenario):
    """harness.run_lean end to end with Lean faked (the reviewer's simulations): Lean answers the
    start probe and proves the first statement; then, per scenario, it is lost for every later
    statement ("midrun"), lost only when re-probed after the junk probe ("end"), there but timing
    out on every attempt of every later statement ("timeouts"; "timeouts_wrong" also marks every
    item after the first as having a wrong answer), or healthy ("healthy": one Lean error and one
    timeout per later statement)."""
    import mathverify.formal as formal
    from harness import run_lean
    calls = {"prove": 0, "avail": 0, "right": 0}

    def fake_right(it, *a):
        calls["right"] += 1
        return calls["right"] == 1

    def fake_prove(stmt, **kw):
        calls["prove"] += 1
        r = {"statement": "stmt", "kind": stmt.kind, "proved": False, "proof": None, "source": None,
             "attempts": [], "audit": {}, "calls": 0, "cost_usd": 0.0, "errors": [], "ms": 1.0}
        if calls["prove"] == 1:
            r.update(proved=True, proof="norm_num", audit={"clean": True}, attempts=[_attempt(True)])
        elif scenario == "midrun":
            r["errors"].append(UNAVAILABLE)
        elif scenario.startswith("timeouts"):
            r["attempts"] = [_attempt(False, TIMEOUT), _attempt(False, TIMEOUT)]
        else:
            r["attempts"] = [_attempt(False, "linarith failed"), _attempt(False, TIMEOUT)]
        return r

    def fake_available(timeout=300.0):
        calls["avail"] += 1
        return not (scenario == "end" and calls["avail"] > 1)

    monkeypatch.setattr(formal, "prove_statement", fake_prove)
    monkeypatch.setattr(formal, "lean_available", fake_available)
    if scenario == "timeouts_wrong":
        monkeypatch.setattr(run_lean, "_answer_is_right", fake_right)
    run_lean.main(["--limit", "5", "--out", str(tmp_path)])
    assert calls["avail"] == 2                      # once before the sweep, once after the junk probe
    return json.loads((tmp_path / "lean_results.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("scenario", ["midrun", "end", "timeouts", "timeouts_wrong", "healthy"])
def test_run_lean_records_whether_each_statement_reached_lean(monkeypatch, tmp_path, scenario):
    data = _simulated_sweep(monkeypatch, tmp_path, scenario)
    assert data["lean_available"] is True and data["lean_available_end"] is (scenario != "end")
    stmt = [r for r in data["records"] + data["junk_probe"] if r["statement"]]
    no_stmt = [r for r in data["records"] + data["junk_probe"] if not r["statement"]]
    assert data["records"][0]["statement"] and data["records"][0]["clean"]        # the one certificate
    junk_stmt = [j for j in data["junk_probe"] if j["statement"]]
    assert junk_stmt                                                               # some junk went to Lean
    assert all(isinstance(r["lean_reached"], bool) and isinstance(r["lean_answered"], bool)
               and isinstance(r["errors"], list) for r in stmt)
    assert not any("lean_reached" in r or "lean_answered" in r for r in no_stmt)
    reached = [r["lean_reached"] for r in stmt]
    answered = [r["lean_answered"] for r in stmt]
    if scenario == "midrun":                        # only the first statement reached Lean
        assert reached == [True] + [False] * (len(stmt) - 1)
        assert all(r["errors"] == [UNAVAILABLE] for r in stmt[1:])
    else:
        assert all(reached)
    if scenario in ("midrun", "timeouts", "timeouts_wrong"):    # only the first statement got a Lean verdict
        assert answered == [True] + [False] * (len(stmt) - 1)
    else:
        assert all(answered)
    counts = [(r["n_attempts"], r["n_unanswered"]) for r in stmt[1:]]
    assert counts == [{"midrun": (0, 0), "healthy": (2, 1), "end": (2, 1)}.get(scenario, (2, 2))] * len(counts)
    values = {g["name"]: g for g in check.lean_gates(data)}
    wrong = [r for r in data["records"] if r["statement"] and not r["answer_right"]]
    if scenario == "timeouts_wrong":
        assert wrong and not any(r["lean_answered"] for r in wrong)
    if scenario == "healthy":
        assert all(g["ok"] for g in values.values())
        assert values["Lean erişilebilir"]["value"] == "evet (1 sertifika)"
        assert values["Lean junk-value sertifikası"]["value"] == f"0/{len(data['junk_probe'])}"
    elif scenario.startswith("timeouts"):           # right-answer items may time out; junk and wrong ones may not
        junk = values.pop("Lean junk-value sertifikası")
        assert not junk["ok"] and junk["value"] == f"Lean cevap vermedi {len(junk_stmt)}/{len(junk_stmt)}"
        if wrong:
            fp = values.pop("Lean FP")
            assert not fp["ok"] and fp["value"] == f"Lean cevap vermedi {len(wrong)}/{len(wrong)}"
        assert all(g["ok"] for g in values.values())
        assert values["Lean erişilebilir"]["value"] == "evet (1 sertifika)"
    else:
        assert not any(g["ok"] for g in values.values())
        assert values["Lean erişilebilir"]["value"].startswith("yarıda kesildi")


def test_venv_python_per_platform(tmp_path):
    assert check.venv_python(tmp_path, windows=True) == sys.executable      # no venv at all
    assert check.venv_python(tmp_path, windows=False) == sys.executable
    posix = tmp_path / ".venv" / "bin" / "python"
    posix.parent.mkdir(parents=True)
    posix.write_text("")
    assert check.venv_python(tmp_path, windows=False) == str(posix)
    assert check.venv_python(tmp_path, windows=True) == sys.executable      # never the other OS's layout
    win = tmp_path / ".venv" / "Scripts" / "python.exe"
    win.parent.mkdir(parents=True)
    win.write_text("")
    assert check.venv_python(tmp_path, windows=True) == str(win)
    assert check.venv_python(tmp_path, windows=False) == str(posix)


def test_py_is_this_platforms_venv_interpreter():
    assert check.PY == check.venv_python(check.ROOT)
    if sys.platform == "win32" and (ROOT / ".venv" / "Scripts" / "python.exe").exists():
        assert check.PY == str(ROOT / ".venv" / "Scripts" / "python.exe")      # unchanged on Windows
