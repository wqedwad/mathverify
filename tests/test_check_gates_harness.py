"""scripts/check.py: a harness that crashes, writes no report or leaves a stale one must fail its
gates under the same names and count, and no Lean gate may pass when Lean did not run or was lost
during the run, nor the FP and junk gates on a statement where Lean left any tactic attempt
unanswered (all of them timed out, or only some) or, for a proved statement, any audit probe, or
that Lean did not show to elaborate (its elaboration check: rejected, unanswered or missing).

No real harness runs here: `check.run` is replaced by a fake that writes fixture reports into a
temporary REPORTS directory (or does not, and returns the exit code under test). The run_lean
tests drive harness.run_lean itself (and, for the junk probe's audit, the real prove_statement)
with Lean faked.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from mathverify.formal.lean_client import LeanResult, LeanUnavailable

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
                              "n_attempts": 1, "n_unanswered": 0, "audit_unanswered": [], "errors": [],
                              "proved": True, "clean": True, "answer_right": True, "elaborates": True},
                             {"id": "x-002", "statement": False, "proved": False, "clean": None, "answer_right": False}],
                 "junk_probe": [{"label": "0/0 = 0", "statement": True, "lean_reached": True, "lean_answered": True,
                                 "n_attempts": 11, "n_unanswered": 0, "audit_unanswered": [], "errors": [],
                                 "proved": False, "certified": False, "elaborates": True}]},
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
        self.labels = getattr(self, "labels", []) + [label]
        if label == "lean_warmup":
            return 0, ""
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


def test_the_full_run_warms_lean_up_before_the_tests_and_the_quick_run_does_not(monkeypatch, tmp_path):
    """Right after a container restart the first Lean start took ~400 s, longer than the 300 s the
    Lean tests wait: a --full run skipped 87 of them and failed one (26 Sep 2026). The warm-up is not
    a gate: the gate count stays 24."""
    fake = FakeRun(tmp_path)
    monkeypatch.setattr(check, "REPORTS", tmp_path)
    monkeypatch.setattr(check, "run", fake)
    check._main(argparse.Namespace(full=True))
    assert fake.labels[:2] == ["lean_warmup", "pytest"]
    fake2 = FakeRun(tmp_path)
    monkeypatch.setattr(check, "run", fake2)
    check._main(argparse.Namespace(full=False))
    assert "lean_warmup" not in fake2.labels
    assert "timeout=900" in check._LEAN_WARMUP


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
# such answers (a right-answer item that only timed out just has no certificate): here at least one;
# the later sections tighten it to every attempt, and every audit probe of a proof.
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


def _reply_from_child(body, cmd="example : True := trivial"):
    """What LeanClient._send_raw really returns when the REPL is a child process running `body` after
    reading the request (None: the child is gone before anything is sent)."""
    import subprocess
    import mathverify.formal.lean_client as lc
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
        return client._send_raw({"cmd": cmd, "env": 0}, timeout=3.0)
    finally:
        client._kill()
        try:                                         # the failed write is still buffered: drop it here,
            proc.stdin.close()                       # not in a finalizer (unraisable-exception warning)
        except OSError:
            pass


@pytest.mark.parametrize("case", sorted(_FAKE_REPL))
def test_attempt_answered_on_what_lean_client_really_returns(case):
    """NO_VERDICT must match the errors LeanClient._send_raw actually produces, so drive it against a
    child process that answers, stays silent, dies, garbles, or is gone before the write."""
    from harness import run_lean
    body, answered = _FAKE_REPL[case]
    r = _reply_from_child(body)
    attempt ={"source": "tactic", "proof": "norm_num", "ok": r.clean, "errors": r.errors[:2], "ms": round(r.ms)}
    assert run_lean.attempt_answered(attempt) is answered, (case, r.errors)
    if not answered and case != "repl_message":
        assert r.errors and str(r.errors[0]).startswith(run_lean.NO_VERDICT), (case, r.errors)


def test_lean_fields_of_an_all_timeouts_statement():
    """The reviewer's prove_statement result: three ladder tactics, each timed out."""
    from harness import run_lean
    r = {"proved": False, "errors": [], "attempts": [dict(_attempt(False, TIMEOUT), proof=t, ms=45000)
                                                     for t in ("simp", "norm_num", "positivity")]}
    assert run_lean.lean_fields(r) == {"lean_reached": True, "lean_answered": False, "n_attempts": 3,
                                       "n_unanswered": 3, "audit_unanswered": [], "errors": []}
    r["attempts"][1] = _attempt(False, "linarith failed")
    assert run_lean.lean_fields(r)["lean_answered"] is True and run_lean.lean_fields(r)["n_unanswered"] == 2
    assert run_lean.lean_fields({"proved": False, "errors": [], "attempts": []})["lean_answered"] is False


def test_no_verdict_is_proves_own():
    """One classification of "Lean gave no verdict" for the ladder, the audit and the sweep: run_lean
    uses prove.NO_VERDICT / prove.lean_judged instead of a copy (behaviour pinned by test_attempt_answered)."""
    from harness import run_lean
    from mathverify.formal import prove as P
    assert run_lean.NO_VERDICT is P.NO_VERDICT and run_lean.lean_judged is P.lean_judged


SAFE = ["Classical.choice", "Quot.sound", "propext"]


AUDIT_TABLE = {  # id -> (a prove_statement record, run_lean.audit_unanswered of it)
    "unproved": ({"proved": False, "audit": {}}, []),                       # never audited
    "unproved_no_audit": ({"proved": False}, []),
    "answered": ({"proved": True, "audit": {"unanswered": [], "axioms": SAFE}}, []),
    "no_axioms": ({"proved": True, "audit": {"unanswered": [], "axioms": []}}, []),  # "does not depend on any axioms"
    "probes_timed_out": ({"proved": True, "audit": {"unanswered": ["vacuity", "no_hyp"], "axioms": SAFE}},
                         ["vacuity", "no_hyp"]),
    "axioms_timed_out": ({"proved": True, "audit": {"unanswered": [], "axioms": ["<unknown>"]}}, ["axioms"]),
    "both": ({"proved": True, "audit": {"unanswered": ["vacuity"], "axioms": ["<unknown>"]}}, ["vacuity", "axioms"]),
    "axioms_missing": ({"proved": True, "audit": {"unanswered": []}}, ["axioms"]),  # not recorded: fail closed
    "axioms_a_string": ({"proved": True, "audit": {"unanswered": [], "axioms": "propext"}}, ["axioms"]),
    "axioms_none": ({"proved": True, "audit": {"unanswered": [], "axioms": None}}, ["axioms"]),
    "old_audit": ({"proved": True, "audit": {"clean": True}}, ["audit"]),   # an audit without `unanswered`
    "empty_audit": ({"proved": True, "audit": {}}, ["audit"]),
    "audit_none": ({"proved": True, "audit": None}, ["audit"]),
    "audit_missing": ({"proved": True}, ["audit"]),
}


@pytest.mark.parametrize("case", list(AUDIT_TABLE))
def test_audit_unanswered(case):
    from harness import run_lean
    r, expected = AUDIT_TABLE[case]
    assert run_lean.audit_unanswered(r) == expected
    assert run_lean.lean_fields(dict(r, errors=[], attempts=[_attempt(True)]))["audit_unanswered"] == expected


@pytest.mark.parametrize("case", list(AUDIT_TABLE))
def test_check_reads_the_raw_audit_with_run_leans_rule(case):
    """check.unanswered_audit reads a row's raw audit with run_lean.audit_unanswered's rule, so a derived
    field emptied by hand (reviewer's axioms_probe.py G2: `audit_unanswered` [] next to axioms
    ["<unknown>"], which passed "Lean FP 0") cannot hide a probe. A raw audit run_lean itself cannot
    read ("audit") is no usable record for check.py (None)."""
    from harness import run_lean
    r, expected = AUDIT_TABLE[case]
    row = dict(r, audit_unanswered=[])
    if not r["proved"] or "audit" not in r:           # never audited / only the derived field to read
        assert check.unanswered_audit(row) == []
    elif expected == ["audit"]:
        assert check.unanswered_audit(row) is None
    else:
        assert check.unanswered_audit(row) == expected == run_lean.audit_unanswered(r)


def test_axioms_placeholder_is_proves_own():
    """check.py keeps "<unknown>" as a literal: it must be what prove._axioms_of records when `#print
    axioms` gets no verdict, and run_lean's AXIOMS_UNKNOWN."""
    from harness import run_lean
    from mathverify.formal import prove as P

    class _Silent:
        def run(self, code, timeout=120.0, env=-1):
            return TIMED_OUT
    ax, _ = P._axioms_of(_Silent(), "mv_claim", 7, 45)
    assert ax == {check.AXIOMS_UNKNOWN} == {run_lean.AXIOMS_UNKNOWN}


# --- the reviewer's probe: real junk_probe + real prove_statement + real lean_gates, Lean faked ------
JUNK_TARGET = "x = 2 from 1/(x-2) = 0"
TIMED_OUT = LeanResult(ok=False, errors=[TIMEOUT], timed_out=True)
SAFE_AXIOMS_REPLY = LeanResult(ok=True, infos=["'mv_claim' depends on axioms: [propext, Classical.choice, Quot.sound]"])
# what LeanClient returns for a statement that elaborates, sent with the body `sorry` (measured shape:
# no error, the sorry warning, exactly one sorry)
_SORRY_WARNING = {"severity": "warning", "data": "declaration uses `sorry`"}
ELABORATED = LeanResult(ok=True, warnings=[_SORRY_WARNING["data"]], sorries=[{"goal": "⊢ True"}], env=3,
                        raw={"messages": [_SORRY_WARNING], "sorries": [{"goal": "⊢ True"}], "env": 3})
_UNKNOWN = "Unknown constant `Real.brokenTemplateFn`"
NOT_ELABORATED = LeanResult(ok=False, errors=[_UNKNOWN], sorries=[{"goal": "⊢ True"}], env=3,
                            raw={"messages": [{"severity": "error", "data": _UNKNOWN}], "env": 3})
# Lean gone for good (the REPL cannot be respawned) when the elaboration check is sent
ELAB_LOST = LeanUnavailable("REPL did not start: ['lean timeout after 300s']")
ELAB_LOST_ERROR = f"lean_unavailable: {ELAB_LOST}"


def _is_elaboration_check(code):
    from harness.run_lean import ELAB_PREFIX
    return code.startswith(ELAB_PREFIX) and code.endswith("\n  sorry")


class _JunkLean:
    """Only the vacuous junk statement `x = 2 from 1/(x-2) = 0` compiles (it does in the real sweep);
    every other ladder attempt gets a Lean error. `#print axioms` and the two audit probes of its
    proof answer as the scenario says; every statement elaborates. The satisfiability probe (since
    25 Sep 2026 part of every audit of a statement with hypotheses) compiles when it is sent."""

    def __init__(self, target_head, *, vacuity, nohyp, axioms=SAFE_AXIOMS_REPLY):
        self.target_head, self.vacuity, self.nohyp, self.axioms = target_head, vacuity, nohyp, axioms

    def run(self, code, timeout=120.0, env=-1):
        if _is_elaboration_check(code):
            return ELABORATED
        if code.startswith("#print axioms"):
            return self.axioms
        from harness.run_lean import ELAB_PREFIX
        head = code.removeprefix(ELAB_PREFIX).split("\n", 1)[0]       # every statement command opens with it
        if "_vacuity" in head:
            return self.vacuity
        if "_nohyp" in head:
            return self.nohyp
        if "_sat" in head:
            return LeanResult(ok=True)
        if code.startswith(self.target_head):
            return LeanResult(ok=True, env=7)
        return LeanResult(ok=False, errors=["linarith failed"])


def _n_junk() -> int:
    from harness.run_lean import JUNK_PROBES
    return len(JUNK_PROBES)          # 17 until 25 Sep 2026, then the formal-audit families


JUNK_AUDIT_SCENARIOS = {  # name -> (vacuity, nohyp, axioms, audit_unanswered, junk gate value, gate ok)
    "A_both_probes_timed_out": (TIMED_OUT, TIMED_OUT, SAFE_AXIOMS_REPLY, ["vacuity", "no_hyp"],
                                "Lean denetim cevapsız 1/1 kanıtlanan ifade", False),
    "B_vacuity_answered_contradictory": (LeanResult(ok=True), LeanResult(ok=False, errors=["linarith failed"]),
                                         SAFE_AXIOMS_REPLY, [], f"0/{_n_junk()}", True),
    "C_axiom_print_timed_out": (LeanResult(ok=False, errors=["linarith failed"]),
                                LeanResult(ok=False, errors=["unsolved goals"]), TIMED_OUT, ["axioms"],
                                "Lean denetim cevapsız 1/1 kanıtlanan ifade", False),
    "D_vacuity_repl_died": (LeanResult(ok=False, errors=["empty reply (REPL died)"]),
                            LeanResult(ok=False, errors=["unsolved goals"]), SAFE_AXIOMS_REPLY, ["vacuity"],
                            "Lean denetim cevapsız 1/1 kanıtlanan ifade", False),
    # every probe answered and none objects: a real certificate, which the gate still counts
    "E_answered_and_clean": (LeanResult(ok=False, errors=["linarith failed"]),
                             LeanResult(ok=False, errors=["unsolved goals"]), SAFE_AXIOMS_REPLY, [], f"1/{_n_junk()}", False),
}


@pytest.mark.parametrize("scenario", sorted(JUNK_AUDIT_SCENARIOS))
def test_junk_probe_with_an_unanswered_audit_fails_the_junk_gate(monkeypatch, scenario):
    """Reviewer's junk_audit_silence_probe.py: before the fix A read "0/17" OK exactly like B."""
    from harness import run_lean
    from mathverify.formal import build_statement
    from mathverify.formal import prove as P
    vacuity, nohyp, axioms, unanswered, value, ok = JUNK_AUDIT_SCENARIOS[scenario]
    _, ir, ca = next(p for p in run_lean.JUNK_PROBES if p[0] == JUNK_TARGET)
    target_head = build_statement(ir, ca).theorem("").split(":= by")[0]
    fake = _JunkLean(target_head, vacuity=vacuity, nohyp=nohyp, axioms=axioms)
    monkeypatch.setattr(P, "get_lean", lambda: fake)
    if scenario.startswith("E_"):
        # Since 25 Sep 2026 an audit is clean only when Lean also proves the hypotheses satisfiable
        # at the template's witness, and this junk statement has none (its hypotheses contradict
        # each other). To keep testing the GATE on a clean certificate, scenario E hands the
        # template a witness and the fake Lean accepts it.
        import sympy as sp
        from mathverify.formal import statement as S
        monkeypatch.setattr(S, "_find_witness", lambda *a, **k: [sp.Integer(2)])
    junk = run_lean.junk_probe(45)
    target = next(j for j in junk if j["label"] == JUNK_TARGET)
    assert target["proved"] is True and target["lean_answered"] is True and target["n_unanswered"] == 0
    assert all(j["elaborates"] is True and j["elab_errors"] == [] for j in junk if j["statement"])
    assert target["certified"] is (scenario.startswith("E_"))
    assert target["audit_unanswered"] == unanswered and target["audit"]["unanswered"] == [
        p for p in unanswered if p != "axioms"]
    assert [j["label"] for j in junk if j.get("proved")] == [JUNK_TARGET]
    data = {"lean_available": True, "lean_available_end": True,
            "records": json.loads(json.dumps(GOOD["run_lean"]["records"])), "junk_probe": junk}
    gates = {g["name"]: g for g in check.lean_gates(data)}
    junk_gate = gates.pop("Lean junk-value sertifikası")
    assert junk_gate["value"] == value and junk_gate["ok"] is ok
    assert all(g["ok"] for g in gates.values())


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
    d["junk_probe"] = [dict(label=f"j{i}", statement=True, certified=False, proved=False, elaborates=True,
                            **run_lean.lean_fields(r)) for i in range(17)]


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
                 "proved": False, "audit_unanswered": [], "clean": None, "answer_right": answer_right,
                 "elaborates": True}, **extra)


ANSWERED = {"lean_answered": True, "n_attempts": 1, "n_unanswered": 0}


def _partly_answered_fields():
    """The reviewer's case, as run_lean records it: one cheap tactic got a Lean verdict, the eight
    heavy ones all timed out."""
    from harness import run_lean
    r = {"proved": False, "errors": [], "attempts": [_attempt(False, "linarith failed")]
         + [dict(_attempt(False, TIMEOUT), ms=45000) for _ in range(8)]}
    fields = run_lean.lean_fields(r)
    assert fields == {"lean_reached": True, "lean_answered": True, "n_attempts": 9, "n_unanswered": 8,
                      "audit_unanswered": [], "errors": []}
    return fields


@pytest.mark.parametrize("partly", [False, True])
def test_a_right_answer_item_that_timed_out_fails_no_gate(monkeypatch, tmp_path, partly):
    """Its whole ladder (or all but one tactic) timed out: it only lost its certificate, and no gate
    is about it."""
    lean = json.loads(json.dumps(GOOD["run_lean"]))
    lean["records"].append(_timed_out_item(True, **(_partly_answered_fields() if partly else {})))
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 0 and names == FULL and all(g["ok"] for g in by_name.values())
    assert by_name["Lean sertifika"]["value"] == "1/3" and by_name["Lean FP"]["value"] == 0
    assert by_name["Lean junk-value sertifikası"]["value"] == "0/1"


WRONG_ITEM_CASES = {  # records appended to GOOD["run_lean"] -> expected "Lean FP" value
    "timed_out": ([_timed_out_item(False)], "Lean cevap vermedi 1/1"),
    "field_missing": ([{k: v for k, v in _timed_out_item(False).items() if k != "lean_answered"}],
                      "Lean cevap vermedi 1/1"),
    "one_of_two": ([_timed_out_item(False), _timed_out_item(False, id="x-004", **ANSWERED)],
                   "Lean cevap vermedi 1/2"),
    "with_an_fp": ([_timed_out_item(False), _timed_out_item(False, id="x-004", clean=True, **ANSWERED)],
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


# --- Lean answered some attempts on a statement but not all ---------------------------------------
# `lean_answered` means "at least one attempt got a Lean verdict", so a junk statement or a wrong-answer
# item on which one cheap tactic was answered and all eight heavy ones timed out still let the junk and
# FP gates read 0 (reviewer's finding): the heavy tactics are the ones that could have proved it. Every
# attempt must now be answered (`n_unanswered` == 0); a missing or inconsistent count fails closed.
PARTLY = "partly"                      # stands for _partly_answered_fields() (needs harness.run_lean)
SILENT = {"lean_answered": False, "n_attempts": 3, "n_unanswered": 3}
NO_COUNT = {"lean_answered": True}


def _counted(n_attempts, n_unanswered):
    return {"lean_answered": True, "n_attempts": n_attempts, "n_unanswered": n_unanswered}


PARTIAL_CASES = {  # fields of each junk statement / wrong-answer item -> expected gate value
    "reviewer": ([PARTLY], "Lean kısmen cevap vermedi 8/9 deneme"),
    "next_to_a_healthy_one": ([PARTLY, _counted(1, 0)], "Lean kısmen cevap vermedi 8/10 deneme"),
    "next_to_a_silent_one": ([PARTLY, SILENT], "Lean cevap vermedi 1/2, kısmen cevap vermedi 8/9 deneme"),
    "next_to_a_certificate": ([PARTLY, dict(_counted(1, 0), hit=True)], "Lean kısmen cevap vermedi 8/10 deneme"),
    "next_to_an_uncounted_one": ([PARTLY, NO_COUNT],
                                 "Lean kısmen cevap vermedi 8/9 deneme, deneme sayımı yok 1/2 ifade"),
    "count_missing": ([{"lean_answered": True, "n_attempts": 9}], "Lean deneme sayımı yok 1/1 ifade"),
    "attempts_missing": ([{"lean_answered": True, "n_unanswered": 0}], "Lean deneme sayımı yok 1/1 ifade"),
    "both_missing": ([NO_COUNT], "Lean deneme sayımı yok 1/1 ifade"),
    "count_is_a_bool": ([{"lean_answered": True, "n_attempts": 9, "n_unanswered": False}],
                        "Lean deneme sayımı yok 1/1 ifade"),
    "count_is_a_string": ([_counted(9, "0")], "Lean deneme sayımı yok 1/1 ifade"),
    "negative_count": ([_counted(9, -1)], "Lean deneme sayımı yok 1/1 ifade"),
    "more_unanswered_than_attempts": ([_counted(2, 3)], "Lean deneme sayımı yok 1/1 ifade"),
    "no_attempt": ([_counted(0, 0)], "Lean deneme sayımı yok 1/1 ifade"),
}
PARTIAL_GATE = {"junk": "Lean junk-value sertifikası", "wrong": "Lean FP"}


DROP = object()                        # spec value: leave this field out of the row


def _with_statements(target, specs):
    """GOOD["run_lean"] whose junk probe (target "junk") is, or whose wrong-answer items (target
    "wrong") are, one statement per spec; `hit` marks a certified junk statement / a clean proof.
    A spec's fields override the row's (an unproved statement with no audit gap by default)."""
    lean = json.loads(json.dumps(GOOD["run_lean"]))
    rows = []
    for i, spec in enumerate(specs):
        spec = dict(_partly_answered_fields() if spec == PARTLY else spec)
        hit = spec.pop("hit", False)
        row = {"statement": True, "lean_reached": True, "errors": [], "proved": hit, "audit_unanswered": [],
               "elaborates": True}
        if target == "junk":
            row.update(label=f"j{i}", certified=hit)
        else:
            row.update(id=f"x-1{i:02d}", clean=True if hit else None, answer_right=False)
        row.update(spec)
        rows.append({k: v for k, v in row.items() if v is not DROP})
    if target == "junk":
        lean["junk_probe"] = rows
    else:
        lean["records"] += rows
    return lean


@pytest.mark.parametrize("target", sorted(PARTIAL_GATE))
@pytest.mark.parametrize("case", sorted(PARTIAL_CASES))
def test_a_partly_unanswered_statement_fails_its_gate(monkeypatch, tmp_path, case, target):
    specs, value = PARTIAL_CASES[case]
    if any(isinstance(s, dict) and s.get("hit") for s in specs):
        value += ", sertifika 1/2" if target == "junk" else ", FP 1"
    lean = _with_statements(target, specs)
    assert check.lean_unreached(lean) == []          # Lean was there the whole time
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 1 and names == FULL and len(names) == 24
    failed = by_name[PARTIAL_GATE[target]]
    assert failed["value"] == value and not failed["ok"] and failed["target"] == 0
    assert all(g["ok"] for n, g in by_name.items() if n != PARTIAL_GATE[target])


@pytest.mark.parametrize("target", sorted(PARTIAL_GATE))
def test_every_attempt_answered_passes(monkeypatch, tmp_path, target):
    """What the measured Windows full sweeps of 24 Sep recorded: every attempt answered (0/645 on
    the 50 wrong-answer items, 0/33 on the 3 junk statements), and the one proved junk statement
    (`x = 2 from 1/(x-2) = 0`) kept from a certificate by an audit Lean answered."""
    answered_proof = dict(_counted(1, 0), proved=True, audit_unanswered=[])
    raw_audit = {"unanswered": [], "axioms": SAFE, "hypotheses_contradictory": True, "clean": False}
    lean = _with_statements(target, [_counted(9, 0), _counted(1, 0), _counted(23, 0), answered_proof,
                                     dict(answered_proof, audit=raw_audit)])
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 0 and names == FULL and all(g["ok"] for g in by_name.values())
    assert by_name["Lean FP"]["value"] == 0
    assert by_name["Lean junk-value sertifikası"]["value"] == ("0/5" if target == "junk" else "0/1")
    assert check.lean_silence(lean["junk_probe"]) is None
    assert check.lean_silence([r for r in lean["records"] if r.get("statement") and not r["answer_right"]]) is None


# --- a proved statement whose audit Lean did not answer -------------------------------------------
# A compiled proof gets its certificate from the audit (axioms, vacuity, no-hypothesis probes). When
# those probes time out the audit is not clean, so the proof gets no certificate, and the junk gate
# read "0/17" although Lean never judged the probe that matters: the junk statement
# `x = 2 from 1/(x-2) = 0` is proved in the real sweep and only its answered vacuity probe keeps it
# uncertified (reviewer's junk_audit_silence_probe.py, scenario A). The same holds for a proved
# wrong-answer item and "Lean FP 0". run_lean now stores `audit_unanswered`; a proved row without
# it (every report before this field, whose junk rows carried no audit at all) fails closed.
def _proof(unanswered=(), **extra):
    """A statement whose first tactic compiled; `unanswered` are the audit probes Lean left silent.
    `extra` overrides any field (DROP leaves it out)."""
    row = dict(_counted(1, 0), proved=True, audit_unanswered=list(unanswered))
    row.update(extra)
    return row


AUDIT_CASES = {  # fields of each junk statement / wrong-answer item -> expected gate value
    "both_probes_timed_out": ([_proof(["vacuity", "no_hyp"])], "Lean denetim cevapsız 1/1 kanıtlanan ifade"),
    "vacuity_timed_out": ([_proof(["vacuity"])], "Lean denetim cevapsız 1/1 kanıtlanan ifade"),
    "axioms_timed_out": ([_proof(["axioms"])], "Lean denetim cevapsız 1/1 kanıtlanan ifade"),
    "audit_itself_missing": ([_proof(["audit"])], "Lean denetim cevapsız 1/1 kanıtlanan ifade"),
    "next_to_an_answered_proof_and_an_unproved_one": ([_proof(["no_hyp"]), _proof(), _counted(9, 0)],
                                                       "Lean denetim cevapsız 1/2 kanıtlanan ifade"),
    "next_to_a_certificate": ([_proof(["vacuity"]), _proof(hit=True)],
                              "Lean denetim cevapsız 1/2 kanıtlanan ifade"),
    "with_partly_answered_attempts": ([PARTLY, _proof(["vacuity"])],
                                      "Lean kısmen cevap vermedi 8/10 deneme, denetim cevapsız 1/1 kanıtlanan ifade"),
    "round4_report": ([_proof(audit_unanswered=DROP)], "Lean denetim kaydı yok 1/1 kanıtlanan ifade"),
    "record_is_a_string": ([_proof(audit_unanswered="vacuity")], "Lean denetim kaydı yok 1/1 kanıtlanan ifade"),
    "record_is_none": ([_proof(audit_unanswered=None)], "Lean denetim kaydı yok 1/1 kanıtlanan ifade"),
    "record_holds_no_names": ([_proof(audit_unanswered=[1])], "Lean denetim kaydı yok 1/1 kanıtlanan ifade"),
    "proved_field_missing": ([dict(_counted(1, 0), proved=DROP, audit_unanswered=DROP)],
                             "Lean denetim kaydı yok 1/1 kanıtlanan ifade"),
    "silent_and_missing": ([_proof(["vacuity"]), _proof(audit_unanswered=DROP), _counted(3, 0)],
                           "Lean denetim cevapsız 1/2 kanıtlanan ifade, denetim kaydı yok 1/2 kanıtlanan ifade"),
    # the derived field says "all answered" but the raw audit stored next to it does not
    "raw_audit_unanswered": ([_proof(audit={"unanswered": ["vacuity"]})], "Lean denetim cevapsız 1/1 kanıtlanan ifade"),
    "raw_audit_without_its_list": ([_proof(audit={"clean": False})], "Lean denetim kaydı yok 1/1 kanıtlanan ifade"),
    # reviewer's axioms_probe.py G2: `#print axioms` unanswered in the raw audit, derived field emptied
    "raw_audit_axioms_unknown": ([_proof(audit={"unanswered": [], "axioms": ["<unknown>"], "clean": False})],
                                 "Lean denetim cevapsız 1/1 kanıtlanan ifade"),
    "raw_audit_axioms_not_a_list": ([_proof(audit={"unanswered": [], "axioms": "propext"})],
                                    "Lean denetim cevapsız 1/1 kanıtlanan ifade"),
    "raw_audit_axioms_missing": ([_proof(audit={"unanswered": []})], "Lean denetim cevapsız 1/1 kanıtlanan ifade"),
    "raw_audit_axioms_unknown_next_to_answered": (
        [_proof(audit={"unanswered": [], "axioms": ["<unknown>"]}), _proof(audit={"unanswered": [], "axioms": SAFE})],
        "Lean denetim cevapsız 1/2 kanıtlanan ifade"),
}


@pytest.mark.parametrize("target", sorted(PARTIAL_GATE))
@pytest.mark.parametrize("case", sorted(AUDIT_CASES))
def test_a_proof_with_an_unanswered_audit_fails_its_gate(monkeypatch, tmp_path, case, target):
    specs, value = AUDIT_CASES[case]
    if any(isinstance(s, dict) and s.get("hit") for s in specs):
        value += ", sertifika 1/2" if target == "junk" else ", FP 1"
    lean = _with_statements(target, specs)
    assert check.lean_unreached(lean) == []          # Lean was there the whole time
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 1 and names == FULL and len(names) == 24
    failed = by_name[PARTIAL_GATE[target]]
    assert failed["value"] == value and not failed["ok"] and failed["target"] == 0
    assert all(g["ok"] for n, g in by_name.items() if n != PARTIAL_GATE[target])


def test_a_right_answer_proof_with_an_unanswered_audit_fails_no_gate(monkeypatch, tmp_path):
    """It only loses its certificate, as when its ladder timed out."""
    lean = json.loads(json.dumps(GOOD["run_lean"]))
    lean["records"].append(dict(_timed_out_item(True), **_proof(["vacuity", "no_hyp", "axioms"])))
    no_record = dict(_timed_out_item(True), id="x-004", **_proof())
    del no_record["audit_unanswered"]                # and one from a report without the field
    lean["records"].append(no_record)
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 0 and names == FULL and all(g["ok"] for g in by_name.values())
    assert by_name["Lean sertifika"]["value"] == "1/4" and by_name["Lean FP"]["value"] == 0


@pytest.mark.parametrize("row, expected", [
    ({"proved": False}, []),
    ({"proved": False, "audit_unanswered": "junk"}, []),             # never audited: the field is not read
    ({"proved": True, "audit_unanswered": []}, []),
    ({"proved": True, "audit_unanswered": ["vacuity"]}, ["vacuity"]),
    ({"proved": True}, None),
    ({"proved": True, "audit_unanswered": ("vacuity",)}, None),       # JSON never gives a tuple: not a list
    ({"audit_unanswered": []}, []),                                   # `proved` missing: counts as proved
    ({}, None),
    ({"proved": False, "clean": True}, None),                         # inconsistent: a certificate is a proof
    ({"proved": False, "certified": True, "audit_unanswered": []}, []),
    # the raw audit (prove._audit) is read too: the derived field can add probes, never hide one
    ({"proved": True, "audit_unanswered": [], "audit": {"unanswered": [], "axioms": SAFE}}, []),
    ({"proved": True, "audit_unanswered": [], "audit": {"unanswered": [], "axioms": []}}, []),
    ({"proved": True, "audit_unanswered": [], "audit": {"unanswered": ["no_hyp"], "axioms": SAFE}}, ["no_hyp"]),
    ({"proved": True, "audit_unanswered": ["vacuity", "axioms"], "audit": {"unanswered": ["vacuity"]}},
     ["vacuity", "axioms"]),
    ({"proved": True, "audit_unanswered": ["vacuity", "axioms"],
      "audit": {"unanswered": ["vacuity"], "axioms": ["<unknown>"]}}, ["vacuity", "axioms"]),   # no duplicate
    # ... including its axioms, with run_lean.audit_unanswered's rule (reviewer's axioms_probe.py G2)
    ({"proved": True, "audit_unanswered": [], "audit": {"unanswered": [], "axioms": ["<unknown>"]}}, ["axioms"]),
    ({"proved": True, "audit_unanswered": [], "audit": {"unanswered": [], "axioms": ["propext", "<unknown>"]}},
     ["axioms"]),
    ({"proved": True, "audit_unanswered": [], "audit": {"unanswered": []}}, ["axioms"]),
    ({"proved": True, "audit_unanswered": [], "audit": {"unanswered": [], "axioms": "propext"}}, ["axioms"]),
    ({"proved": True, "audit_unanswered": [], "audit": {"unanswered": [], "axioms": None}}, ["axioms"]),
    ({"proved": True, "audit_unanswered": ["no_hyp"], "audit": {"unanswered": ["vacuity"], "axioms": None}},
     ["no_hyp", "vacuity", "axioms"]),
    ({"proved": True, "audit_unanswered": [], "audit": {}}, None),    # a raw audit without its list
    ({"proved": True, "audit_unanswered": ["audit"], "audit": {"clean": False}}, None),
    ({"proved": True, "audit_unanswered": [], "audit": None}, None),
    ({"proved": True, "audit_unanswered": [], "audit": {"unanswered": "vacuity"}}, None),
    ({"proved": True, "audit": {"unanswered": []}}, None),            # the derived field is still required
    ({"proved": False, "audit_unanswered": [], "audit": {"unanswered": ["vacuity"]}}, []),
    ({"proved": False, "audit": {}}, []),                             # an unproved statement is never audited
])
def test_unanswered_audit(row, expected):
    assert check.unanswered_audit(row) == expected


# --- a statement Lean rejects itself --------------------------------------------------------------
# An attempt that fails because the STATEMENT does not elaborate (unknown identifier from a broken
# template, a type error) carries a real Lean error, so it counts as answered, and a wrong-answer item
# or a junk statement made only of such attempts passed "Lean FP 0" / junk "0/17" although Lean never
# judged the claimed value (reviewer's unelaborated_probe.py). run_lean now sends every statement once
# with the body `sorry` (autoImplicit off) and stores `elaborates`; a junk statement or a wrong-answer
# item without `elaborates` True fails its gate, a right-answer item fails none.
@pytest.mark.parametrize("reply, expected", [
    (ELABORATED, True),
    (NOT_ELABORATED, False),
    (LeanResult(ok=False, errors=["unexpected token ')'; expected term"],
                raw={"messages": [{"severity": "error", "data": "unexpected token ')'; expected term"}]}), False),
    (LeanResult(ok=True, env=3, raw={"env": 3}), False),                  # answered, body never reached
    (LeanResult(ok=True, warnings=["unused variable `x`"], sorries=[{"goal": "⊢ True"}], env=3,
                raw={"env": 3, "messages": [{"severity": "warning", "data": "unused variable `x`"}]}), True),
    (TIMED_OUT, None),
    (LeanResult(ok=False, errors=["empty reply (REPL died)"]), None),
    (LeanResult(ok=False, errors=["bad JSON from REPL: Expecting value: {"]), None),
    (LeanResult(ok=False, raw={"message": "Unknown environment."}), None),
    (LeanResult(ok=True, sorries=[{"goal": "⊢ True"}]), None),          # no raw reply: not Lean's answer
], ids=["elaborates", "unknown_constant", "parse_error", "no_sorry", "other_warning", "timeout", "died", "bad_json",
        "repl_message", "no_raw"])
def test_elaboration_verdict(reply, expected):
    from harness import run_lean
    assert run_lean.elaboration_verdict(reply) is expected


_ELAB_REPL = {  # child script standing in for the REPL -> elaboration verdict
    "elaborates": ('print(json.dumps({"messages": [{"severity": "warning", "data": "declaration uses `sorry`"}], '
                   '"sorries": [{"goal": "True", "proofState": 0}], "env": 1})); print("")', True),
    "unknown_constant": ('print(json.dumps({"messages": [{"severity": "error", "data": "Unknown constant `Real.f`"}], '
                         '"sorries": [{"goal": "True", "proofState": 0}], "env": 1})); print("")', False),
    "no_sorry": ('print(json.dumps({"env": 1})); print("")', False),
    "timeout": ("time.sleep(60)", None),
    "died": ("sys.exit(0)", None),
    "bad_json": ('print("not json"); print("")', None),
    "repl_message": ('print(json.dumps({"message": "Unknown environment."})); print("")', None),
    "write_failed": (None, None),
}


@pytest.mark.parametrize("case", sorted(_ELAB_REPL))
def test_elaboration_verdict_on_what_lean_client_really_returns(case):
    from harness import run_lean
    body, expected = _ELAB_REPL[case]
    r = _reply_from_child(body, cmd=run_lean.ELAB_PREFIX + "theorem mv_claim : True := by\n  sorry")
    assert run_lean.elaboration_verdict(r) is expected, (case, r)


class _ElabLean:
    """Answers only the elaboration check, with `reply` (a LeanResult, or an exception to raise)."""

    def __init__(self, reply):
        self.reply, self.codes = reply, []

    def run(self, code, timeout=120.0, env=-1):
        self.codes.append(code)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def _junk_statement():
    from harness import run_lean
    from mathverify.formal import build_statement
    _, ir, ca = next(p for p in run_lean.JUNK_PROBES if p[0] == JUNK_TARGET)
    return build_statement(ir, ca)


@pytest.mark.parametrize("case", ["elaborates", "rejected", "timed_out", "repl_message", "lost"])
def test_add_elaboration(monkeypatch, case):
    from harness import run_lean
    from mathverify.formal import prove as P
    lost = ELAB_LOST
    reply = {"elaborates": ELABORATED, "rejected": NOT_ELABORATED, "timed_out": TIMED_OUT,
             "repl_message": LeanResult(ok=False, raw={"message": "Unknown environment."}), "lost": lost}[case]
    fake = _ElabLean(reply)
    monkeypatch.setattr(P, "get_lean", lambda: fake)   # the client prove_statement uses
    st = _junk_statement()
    rec = {"label": JUNK_TARGET, "statement": True, "lean_reached": True, "errors": ["kept"]}
    assert run_lean.add_elaboration(rec, st, 45) is rec
    # the statement the ladder ran, with the body `sorry` and autoImplicit off (st.theorem already
    # opens with the option since the verifier compiles with it too): nothing else, option once
    assert fake.codes == [st.theorem("  sorry")]
    assert fake.codes[0].startswith("set_option autoImplicit false in\n")
    assert fake.codes[0].count("autoImplicit") == 1
    assert run_lean.elaboration_code(st) == fake.codes[0]
    expected = {"elaborates": (True, []), "rejected": (False, [_UNKNOWN]), "timed_out": (None, [TIMEOUT]),
                "repl_message": (None, ["REPL message: Unknown environment."]),
                "lost": (None, [f"lean_unavailable: {lost}"])}[case]
    assert (rec["elaborates"], rec["elab_errors"]) == expected
    assert run_lean.statement_unelaborated(rec) is (case != "elaborates")
    # Lean gone for good during the check: the statement did not reach Lean, as for the ladder
    assert rec["lean_reached"] is (case != "lost")
    assert rec["errors"] == ["kept"] + ([f"lean_unavailable: {lost}"] if case == "lost" else [])


def test_no_elaboration_check_once_lean_is_lost_for_the_statement(monkeypatch):
    """prove_statement already found Lean gone (lean_reached False): no second respawn attempt."""
    from harness import run_lean
    from mathverify.formal import prove as P
    fake = _ElabLean(ELABORATED)
    monkeypatch.setattr(P, "get_lean", lambda: fake)
    rec = {"label": JUNK_TARGET, "statement": True, "lean_reached": False, "errors": [UNAVAILABLE]}
    run_lean.add_elaboration(rec, _junk_statement(), 45)
    assert fake.codes == []
    assert rec == {"label": JUNK_TARGET, "statement": True, "lean_reached": False, "errors": [UNAVAILABLE],
                   "elaborates": None, "elab_errors": [run_lean.ELAB_NOT_SENT]}
    assert run_lean.statement_unelaborated(rec)


ELAB_CASES = {  # `elaborates` of each junk statement / wrong-answer item -> expected gate value
    "rejected": ([False], "ifade Lean'de derlenmedi 1/1"),
    "unanswered": ([None], "Lean derleme sondası cevapsız 1/1 ifade"),
    "missing": ([DROP], "Lean derleme kaydı yok 1/1 ifade"),             # a report from before the check
    "a_string": (["true"], "Lean derleme kaydı yok 1/1 ifade"),
    "a_number": ([1], "Lean derleme kaydı yok 1/1 ifade"),
    "one_of_three": ([False, True, True], "ifade Lean'de derlenmedi 1/3"),
    "all_three_kinds": ([False, None, DROP, True],
                        "Lean derleme sondası cevapsız 1/4 ifade, derleme kaydı yok 1/4 ifade, "
                        "ifade Lean'de derlenmedi 1/4"),
}


@pytest.mark.parametrize("target", sorted(PARTIAL_GATE))
@pytest.mark.parametrize("case", sorted(ELAB_CASES))
def test_a_statement_that_does_not_elaborate_fails_its_gate(monkeypatch, tmp_path, case, target):
    values, value = ELAB_CASES[case]
    lean = _with_statements(target, [dict(_counted(2, 0), elaborates=v) for v in values])
    assert check.lean_unreached(lean) == []          # Lean was there the whole time
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 1 and names == FULL and len(names) == 24
    failed = by_name[PARTIAL_GATE[target]]
    assert failed["value"] == value and not failed["ok"] and failed["target"] == 0
    assert all(g["ok"] for n, g in by_name.items() if n != PARTIAL_GATE[target])


@pytest.mark.parametrize("target", sorted(PARTIAL_GATE))
@pytest.mark.parametrize("spec, value", [
    # next to the other kinds of silence and to a real hit: every reason is named
    (dict(_counted(9, 8), elaborates=False), "Lean kısmen cevap vermedi 8/9 deneme, ifade Lean'de derlenmedi 1/1"),
    (dict(_counted(9, 8), elaborates=None), "Lean kısmen cevap vermedi 8/9 deneme, derleme sondası cevapsız 1/1 ifade"),
    (_proof(["vacuity"], elaborates=False), "Lean denetim cevapsız 1/1 kanıtlanan ifade, ifade Lean'de derlenmedi 1/1"),
    (dict(_counted(1, 0), elaborates=False, hit=True), "ifade Lean'de derlenmedi 1/1"),
], ids=["partly_answered", "partly_answered_check_unanswered", "silent_audit", "with_a_hit"])
def test_unelaborated_next_to_other_silence(monkeypatch, tmp_path, target, spec, value):
    if spec.get("hit"):
        value += ", sertifika 1/1" if target == "junk" else ", FP 1"
    lean = _with_statements(target, [spec])
    rc, by_name, _ = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    failed = by_name[PARTIAL_GATE[target]]
    assert rc == 1 and failed["value"] == value and not failed["ok"]


@pytest.mark.parametrize("elaborates", [False, None, DROP, "true"])
def test_a_right_answer_item_that_does_not_elaborate_fails_no_gate(monkeypatch, tmp_path, elaborates):
    lean = json.loads(json.dumps(GOOD["run_lean"]))
    row = dict(_timed_out_item(True), **_counted(2, 0), elaborates=elaborates)
    lean["records"].append({k: v for k, v in row.items() if v is not DROP})
    rc, by_name, names = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 0 and names == FULL and all(g["ok"] for g in by_name.values())
    assert by_name["Lean FP"]["value"] == 0 and by_name["Lean junk-value sertifikası"]["value"] == "0/1"


class _BrokenTemplateLean:
    """The reviewer's unelaborated_probe.py: Lean rejects every statement itself, so every attempt, and
    the elaboration check, gets the same elaboration error."""

    def __init__(self):
        self.codes = []

    def run(self, code, timeout=120.0, env=-1):
        self.codes.append(code)
        return NOT_ELABORATED


@pytest.mark.parametrize("target", sorted(PARTIAL_GATE))
def test_reviewer_unelaborated_probe(monkeypatch, target):
    """Real prove_statement, run_lean and lean_gates, Lean faked. Before the check the FP gate read 0
    and the junk gate 0/17 on these statements: every attempt carried a real Lean error, so counted as
    answered."""
    from harness import run_lean
    from mathverify.formal import prove as P
    fake = _BrokenTemplateLean()
    monkeypatch.setattr(P, "get_lean", lambda: fake)
    data = {"lean_available": True, "lean_available_end": True,
            "records": json.loads(json.dumps(GOOD["run_lean"]["records"])),
            "junk_probe": json.loads(json.dumps(GOOD["run_lean"]["junk_probe"]))}
    if target == "junk":
        data["junk_probe"] = run_lean.junk_probe(45)
        rows = [j for j in data["junk_probe"] if j["statement"]]
    else:
        st = _junk_statement()
        r = P.prove_statement(st, use_model=False, tactic_timeout=45)
        rec = {"id": "wrong-1", "statement": True, "answer_right": False, "proved": r["proved"],
               "clean": (r.get("audit") or {}).get("clean"), "audit": r.get("audit"), **run_lean.lean_fields(r)}
        rows = [run_lean.add_elaboration(rec, st, 45)]
        data["records"] += rows
    assert rows and all(r["lean_answered"] and r["n_unanswered"] == 0 and not r["proved"] for r in rows)
    assert all(r["elaborates"] is False and r["elab_errors"] == [_UNKNOWN] for r in rows)
    assert sum(1 for c in fake.codes if _is_elaboration_check(c)) == len(rows)
    gates = {g["name"]: g for g in check.lean_gates(data)}
    failed = gates.pop(PARTIAL_GATE[target])
    assert failed["value"] == f"ifade Lean'de derlenmedi {len(rows)}/{len(rows)}" and not failed["ok"]
    assert all(g["ok"] for g in gates.values())


def test_attempt_counts():
    assert check.attempt_counts(_counted(9, 8)) == (8, 9)
    assert check.attempt_counts(_counted(1, 0)) == (0, 1)
    assert check.attempt_counts(_counted(3, 3)) == (3, 3)
    for bad in (NO_COUNT, {"n_attempts": 9}, {"n_unanswered": 0}, _counted(9, False), _counted(True, 0),
                _counted(9, 1.0), _counted(9, None), _counted(9, -1), _counted(2, 3), _counted(0, 0)):
        assert check.attempt_counts(bad) is None, bad


def _simulated_sweep(monkeypatch, tmp_path, scenario):
    """harness.run_lean end to end with Lean faked (the reviewer's simulations): Lean answers the
    start probe and proves the first statement; then, per scenario, it is lost for every later
    statement ("midrun"), lost only when re-probed after the junk probe ("end"), there but timing
    out on every attempt of every later statement ("timeouts"), answering one of the two attempts
    on every later statement and timing out on the other ("partial"), proving every later statement
    with both audit probes of each proof timed out ("audit_timeouts") or answered and objecting
    ("audit_answered": hypotheses contradictory), or healthy ("healthy": two Lean errors per later
    statement). Each statement's elaboration check (after its ladder) elaborates, except for the
    later statements of "unelaborated" (Lean rejects the statement itself: the two attempts and the
    check get the same elaboration error), "elab_timeouts" (healthy ladder, check timed out),
    "elab_lost" (healthy ladder, Lean gone for good at the check) and "midrun" (Lean gone: no check).
    A "_wrong" suffix also marks every item after the first as having a wrong answer."""
    import mathverify.formal as formal
    from harness import run_lean
    from mathverify.formal import prove as P
    calls = {"prove": 0, "avail": 0, "right": 0, "elab": 0}

    class _Lean:                                     # prove's client: only the elaboration check reaches it
        def run(self, code, timeout=120.0, env=-1):
            assert _is_elaboration_check(code)
            calls["elab"] += 1
            assert not (calls["prove"] > 1 and scenario == "midrun")   # Lean already lost: not sent
            if calls["prove"] > 1 and scenario == "elab_lost":
                raise ELAB_LOST
            if calls["prove"] > 1 and scenario.startswith("unelaborated"):
                return NOT_ELABORATED
            if calls["prove"] > 1 and scenario.startswith("elab_timeouts"):
                return TIMED_OUT
            return ELABORATED

    def fake_right(it, *a):
        calls["right"] += 1
        return calls["right"] == 1

    def fake_prove(stmt, **kw):
        calls["prove"] += 1
        r = {"statement": "stmt", "kind": stmt.kind, "proved": False, "proof": None, "source": None,
             "attempts": [], "audit": {}, "calls": 0, "cost_usd": 0.0, "errors": [], "ms": 1.0}
        if calls["prove"] == 1:
            r.update(proved=True, proof="norm_num", attempts=[_attempt(True)],
                     audit={"clean": True, "unanswered": [], "axioms": SAFE, "hypotheses_contradictory": False})
        elif scenario == "midrun":
            r["errors"].append(UNAVAILABLE)
        elif scenario.startswith("timeouts"):
            r["attempts"] = [_attempt(False, TIMEOUT), _attempt(False, TIMEOUT)]
        elif scenario.startswith("partial"):
            r["attempts"] = [_attempt(False, "linarith failed"), _attempt(False, TIMEOUT)]
        elif scenario.startswith("audit_timeouts"):
            r.update(proved=True, proof="norm_num", attempts=[_attempt(True)],
                     audit={"clean": False, "unanswered": ["vacuity", "no_hyp"], "axioms": SAFE,
                            "hypotheses_contradictory": None})
        elif scenario.startswith("audit_answered"):
            r.update(proved=True, proof="norm_num", attempts=[_attempt(True)],
                     audit={"clean": False, "unanswered": [], "axioms": SAFE, "hypotheses_contradictory": True})
        elif scenario.startswith("unelaborated"):
            r["attempts"] = [_attempt(False, _UNKNOWN), _attempt(False, _UNKNOWN)]
        else:
            r["attempts"] = [_attempt(False, "linarith failed"), _attempt(False, "unsolved goals")]
        return r

    def fake_available(timeout=300.0):
        calls["avail"] += 1
        return not (scenario == "end" and calls["avail"] > 1)

    monkeypatch.setattr(formal, "prove_statement", fake_prove)
    monkeypatch.setattr(formal, "lean_available", fake_available)
    monkeypatch.setattr(P, "get_lean", _Lean)
    if scenario.endswith("_wrong"):
        monkeypatch.setattr(run_lean, "_answer_is_right", fake_right)
    run_lean.main(["--limit", "5", "--out", str(tmp_path)])
    assert calls["avail"] == 2                      # once before the sweep, once after the junk probe
    # one elaboration check per statement that reached Lean
    assert calls["elab"] == (1 if scenario == "midrun" else calls["prove"])
    return json.loads((tmp_path / "lean_results.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("scenario", ["midrun", "end", "timeouts", "timeouts_wrong", "partial", "partial_wrong",
                                      "audit_timeouts", "audit_timeouts_wrong", "audit_answered_wrong", "healthy",
                                      "unelaborated", "unelaborated_wrong", "elab_timeouts_wrong", "elab_lost"])
def test_run_lean_records_whether_each_statement_reached_lean(monkeypatch, tmp_path, scenario):
    from harness import run_lean
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
    if scenario in ("midrun", "elab_lost"):         # only the first statement reached Lean
        assert reached == [True] + [False] * (len(stmt) - 1)
        lost = [UNAVAILABLE] if scenario == "midrun" else [ELAB_LOST_ERROR]
        assert all(r["errors"] == lost for r in stmt[1:])
        assert all(r["elab_errors"] == ([run_lean.ELAB_NOT_SENT] if scenario == "midrun" else [ELAB_LOST_ERROR])
                   for r in stmt[1:])
    else:
        assert all(reached)
    if scenario in ("midrun", "timeouts", "timeouts_wrong"):    # only the first statement got a Lean verdict
        assert answered == [True] + [False] * (len(stmt) - 1)
    else:
        assert all(answered)
    # the elaboration check, stored on every statement (right-answer items too)
    later_elab = (False if scenario.startswith("unelaborated") else
                  None if scenario in ("midrun", "elab_lost") or scenario.startswith("elab_timeouts") else True)
    assert [r["elaborates"] for r in stmt] == [True] + [later_elab] * (len(stmt) - 1)
    assert not any("elaborates" in r for r in no_stmt)
    counts = [(r["n_attempts"], r["n_unanswered"]) for r in stmt[1:]]
    expected = {"midrun": (0, 0), "healthy": (2, 0), "end": (2, 0), "partial": (2, 1), "partial_wrong": (2, 1),
                "unelaborated": (2, 0), "unelaborated_wrong": (2, 0), "elab_timeouts_wrong": (2, 0),
                "elab_lost": (2, 0)}
    audited = scenario.startswith("audit")
    assert counts == [(1, 0) if audited else expected.get(scenario, (2, 2))] * len(counts)
    assert all(isinstance(r["audit_unanswered"], list) and "audit" in r for r in junk_stmt)
    audit_silent = scenario.startswith("audit_timeouts")
    assert [r["audit_unanswered"] for r in stmt] == [[]] + [["vacuity", "no_hyp"] if audit_silent else []] * (
        len(stmt) - 1)
    later = len(stmt) - 1
    wrong = [r for r in data["records"] if r["statement"] and not r["answer_right"]]
    # what the sweep reports: unanswered attempts, proofs with a silent audit, silent junk / wrong items
    md = (tmp_path / "lean_report.md").read_text(encoding="utf-8")
    n_att = sum(r["n_attempts"] for r in stmt)
    n_un = {"timeouts": 2 * later, "timeouts_wrong": 2 * later, "partial": later, "partial_wrong": later}.get(scenario, 0)
    assert f"taktik denemesi (zaman aşımı ya da REPL çökmesi): **{n_un}/{n_att}**" in md
    assert f"cevapsız kalan kanıt: **{later if audit_silent else 0}/{1 + (later if audited else 0)}**" in md
    silent = scenario in ("midrun", "timeouts", "timeouts_wrong", "partial", "partial_wrong", "audit_timeouts",
                          "audit_timeouts_wrong")
    silent_junk = [j["label"] for j in junk_stmt] if silent else []
    assert f"junk sondası (junk kapısı düşer): **{len(silent_junk)}**" in md
    assert (f" ✗ {silent_junk}" in md) is bool(silent_junk)
    if scenario.endswith("_wrong"):
        silent_wrong = [r["id"] for r in wrong] if silent else []
        assert f"bunlardan cevabı yanlış (FP kapısı düşer): **{len(silent_wrong)}**" in md
        assert (f" ✗ {silent_wrong}" in md) is bool(silent_wrong)
    right = [r for r in data["records"] if r["statement"] and r["answer_right"]]

    def elab_count(rows):
        return f"**{sum(r['elaborates'] is True for r in rows)}/{len(rows)}**"
    assert f"cevabı doğru öğe {elab_count(right)}" in md
    assert f"cevabı yanlış öğe (FP kapısı) {elab_count(wrong)}" in md
    assert f"junk sondası (junk kapısı) {elab_count(junk_stmt)}" in md
    if later_elab is not True:                      # every later junk statement is named
        assert f"(junk kapısı) {elab_count(junk_stmt)} ✗ {[j['label'] for j in junk_stmt]}" in md
    values = {g["name"]: g for g in check.lean_gates(data)}
    if scenario.endswith("_wrong"):
        assert wrong and all(r is not data["records"][0] for r in wrong)
    if scenario == "timeouts_wrong":
        assert not any(r["lean_answered"] for r in wrong)
    if scenario in ("healthy", "audit_answered_wrong"):     # proved but refused by an answered audit: no FP
        if audited:
            assert all(r["proved"] and not r["clean"] for r in wrong)
            assert values["Lean sertifika"]["value"] == f"1/{len(data['records'])}"
        assert all(g["ok"] for g in values.values())
        assert values["Lean erişilebilir"]["value"] == "evet (1 sertifika)"
        assert values["Lean junk-value sertifikası"]["value"] == f"0/{len(data['junk_probe'])}"
    elif scenario.startswith(("timeouts", "partial", "audit")):  # right-answer items may; junk and wrong may not
        def silence(n):                             # "partial": one of each statement's two attempts unanswered
            if scenario.startswith("timeouts"):
                return f"Lean cevap vermedi {n}/{n}"
            if audit_silent:
                return f"Lean denetim cevapsız {n}/{n} kanıtlanan ifade"
            return f"Lean kısmen cevap vermedi {n}/{2 * n} deneme"
        junk = values.pop("Lean junk-value sertifikası")
        assert not junk["ok"] and junk["value"] == silence(len(junk_stmt))
        if wrong:
            fp = values.pop("Lean FP")
            assert not fp["ok"] and fp["value"] == silence(len(wrong))
        assert all(g["ok"] for g in values.values())
        assert values["Lean erişilebilir"]["value"] == "evet (1 sertifika)"
    elif scenario.startswith(("unelaborated", "elab_timeouts")):   # every attempt answered, yet no verdict
        def unjudged(n):                            # on the claimed value
            if later_elab is False:
                return f"ifade Lean'de derlenmedi {n}/{n}"
            return f"Lean derleme sondası cevapsız {n}/{n} ifade"
        junk = values.pop("Lean junk-value sertifikası")
        assert not junk["ok"] and junk["value"] == unjudged(len(junk_stmt))
        assert bool(wrong) is scenario.endswith("_wrong")
        if wrong:
            fp = values.pop("Lean FP")
            assert not fp["ok"] and fp["value"] == unjudged(len(wrong))
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
