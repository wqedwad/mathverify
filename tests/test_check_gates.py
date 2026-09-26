"""scripts/check.py: the pyflakes gate must fail on a real finding and on pyflakes not running."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_script", ROOT / "scripts" / "check.py")
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def test_an_undefined_name_is_a_finding(tmp_path):
    (tmp_path / "m.py").write_text("def f():\n    return undefined_name\n", encoding="utf-8")
    findings, unparsed = check.pyflakes_findings("m.py:2:12: undefined name 'undefined_name'\n", 1, tmp_path)
    assert findings == ["m.py:2:12: undefined name 'undefined_name'"] and not unparsed


def test_noqa_on_the_reported_line_waives_it(tmp_path):
    (tmp_path / "m.py").write_text("import sympy  # noqa: F401  (warm import)\n", encoding="utf-8")
    findings, unparsed = check.pyflakes_findings("m.py:1:1: 'sympy' imported but unused\n", 1, tmp_path)
    assert findings == [] and not unparsed


def test_pyflakes_not_running_is_not_a_pass(tmp_path):
    findings, unparsed = check.pyflakes_findings("No module named pyflakes\n", 1, tmp_path)
    assert findings == [] and unparsed
    assert check.pyflakes_findings("", 0, tmp_path) == ([], False)         # clean run


def test_the_real_tree_is_clean_except_waived_lines():
    import subprocess
    import sys
    p = subprocess.run([sys.executable, "-m", "pyflakes", "src", "harness", "scripts", "tests", "evalset/build"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert check.pyflakes_findings(p.stdout + p.stderr, p.returncode, ROOT) == ([], False)


def test_the_log_names_the_failed_and_skipped_tests():
    """A '1 failed ... 92 skipped' gate line alone did not say which test failed (26 Sep 2026)."""
    out = ("....F\nFAILED tests/test_x.py::test_a - AssertionError\n"
           "SKIPPED [87] tests/test_lean_audit_2026_09_25.py:471: Lean/Mathlib toolchain not available\n"
           "ERROR tests/test_y.py - ImportError\n1 failed, 3 passed, 87 skipped in 1.00s\n")
    assert check.pytest_problems(out) == [
        "FAILED tests/test_x.py::test_a - AssertionError",
        "SKIPPED [87] tests/test_lean_audit_2026_09_25.py:471: Lean/Mathlib toolchain not available",
        "ERROR tests/test_y.py - ImportError"]
    assert check.pytest_problems("5 passed in 1.0s\n") == []


def test_the_log_header_does_not_count_the_log_itself(tmp_path, monkeypatch):
    """The log is open for writing when git is asked, so it always looked modified and a clean
    tree read '1 dosya' (26 Sep 2026). A real repository, since the exclusion is git's."""
    import subprocess

    def git(*a):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a],
                       cwd=tmp_path, check=True, capture_output=True)

    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "check_full.log").write_text("old log\n", encoding="utf-8")
    (tmp_path / "code.py").write_text("x = 1\n", encoding="utf-8")
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "clean")
    monkeypatch.setattr(check, "ROOT", tmp_path)
    monkeypatch.setattr(check, "_main", lambda args: 0)

    def header():
        assert check.main(["--full"]) == 0
        return (tmp_path / "reports" / "check_full.log").read_text(encoding="utf-8").splitlines()[0]

    assert header().endswith("commit edilmemiş değişiklik: 0 dosya")
    (tmp_path / "code.py").write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "new.py").write_text("y = 1\n", encoding="utf-8")
    assert header().endswith("commit edilmemiş değişiklik: 2 dosya")
