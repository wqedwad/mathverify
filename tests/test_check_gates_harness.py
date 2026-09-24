"""scripts/check.py: a harness that crashes, writes no report or leaves a stale one must fail its
gates under the same names and count, and no Lean gate may pass when Lean did not run or was lost
during the run.

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
                 "records": [{"id": "x-001", "statement": True, "lean_reached": True, "errors": [],
                              "clean": True, "answer_right": True},
                             {"id": "x-002", "statement": False, "clean": None, "answer_right": False}],
                 "junk_probe": [{"label": "0/0 = 0", "statement": True, "lean_reached": True, "errors": [],
                                 "certified": False}]},
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


def _simulated_sweep(monkeypatch, tmp_path, scenario):
    """harness.run_lean end to end with Lean faked (the reviewer's simulation): Lean answers the
    start probe and proves the first statement; then, per scenario, it is lost for every later
    statement ("midrun"), lost only when re-probed after the junk probe ("end"), or never ("healthy")."""
    import mathverify.formal as formal
    from harness import run_lean
    calls = {"prove": 0, "avail": 0}

    def fake_prove(stmt, **kw):
        calls["prove"] += 1
        r = {"statement": "stmt", "kind": stmt.kind, "proved": False, "proof": None, "source": None,
             "attempts": [], "audit": {}, "calls": 0, "cost_usd": 0.0, "errors": [], "ms": 1.0}
        if calls["prove"] == 1:
            r.update(proved=True, proof="norm_num", audit={"clean": True})
        elif scenario == "midrun":
            r["errors"].append(UNAVAILABLE)
        return r

    def fake_available(timeout=300.0):
        calls["avail"] += 1
        return not (scenario == "end" and calls["avail"] > 1)

    monkeypatch.setattr(formal, "prove_statement", fake_prove)
    monkeypatch.setattr(formal, "lean_available", fake_available)
    run_lean.main(["--limit", "5", "--out", str(tmp_path)])
    assert calls["avail"] == 2                      # once before the sweep, once after the junk probe
    return json.loads((tmp_path / "lean_results.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("scenario", ["midrun", "end", "healthy"])
def test_run_lean_records_whether_each_statement_reached_lean(monkeypatch, tmp_path, scenario):
    data = _simulated_sweep(monkeypatch, tmp_path, scenario)
    assert data["lean_available"] is True and data["lean_available_end"] is (scenario != "end")
    stmt = [r for r in data["records"] + data["junk_probe"] if r["statement"]]
    no_stmt = [r for r in data["records"] + data["junk_probe"] if not r["statement"]]
    assert data["records"][0]["statement"] and data["records"][0]["clean"]        # the one certificate
    assert [j for j in data["junk_probe"] if j["statement"]]                       # some junk went to Lean
    assert all(isinstance(r["lean_reached"], bool) and isinstance(r["errors"], list) for r in stmt)
    assert not any("lean_reached" in r for r in no_stmt)
    reached = [r["lean_reached"] for r in stmt]
    if scenario == "midrun":                        # only the first statement reached Lean
        assert reached == [True] + [False] * (len(stmt) - 1)
        assert all(r["errors"] == [UNAVAILABLE] for r in stmt[1:])
    else:
        assert all(reached)
    values = {g["name"]: g for g in check.lean_gates(data)}
    if scenario == "healthy":
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
