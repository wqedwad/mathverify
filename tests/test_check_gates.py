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
