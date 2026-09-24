"""scripts/check.py: a harness that crashes, writes no report or leaves a stale one must fail its
gates under the same names and count, and no Lean gate may pass when Lean did not run.

No real harness runs here: `check.run` is replaced by a fake that writes fixture reports into a
temporary REPORTS directory (or does not, and returns the exit code under test).
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
    "run_lean": {"lean_available": True,
                 "records": [{"clean": True, "answer_right": True}, {"clean": None, "answer_right": False}],
                 "junk_probe": [{"label": "0/0 = 0", "certified": False}]},
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
    lean = dict(GOOD["run_lean"], records=[{"clean": False, "answer_right": True}])
    rc, by_name, _ = _gates(monkeypatch, tmp_path, content={"run_lean": lean})
    assert rc == 1
    assert by_name["Lean erişilebilir"]["value"] == "evet (0 sertifika)" and not by_name["Lean erişilebilir"]["ok"]
    assert by_name["Lean FP"]["ok"] and by_name["Lean junk-value sertifikası"]["ok"]


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
