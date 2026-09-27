"""tests/lean_warmup.py: a session that selects a Lean test starts Lean once, before that test and
outside its timeout (HANDOFF B6). Each case runs pytest in a child process on a small suite whose
conftest loads the plugin with a fake LeanClient; the fake's warm-up outlasts the child's test
timeout, so a warm-up inside a test would fail it."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import lean_warmup

TESTS = Path(__file__).resolve().parent

CONFTEST = '''
import json, os, sys, time, types
sys.path.insert(0, {tests!r})
LOG = {log!r}


def _rec(event, **kw):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(event=event, **kw)) + "\\n")


class _Result:
    def __init__(self, clean, errors):
        self.clean, self.errors = clean, errors


class LeanClient:
    def __init__(self, boot_timeout=300.0):
        _rec("init", boot_timeout=boot_timeout)

    def run(self, code, timeout=120.0):
        _rec("run", code=code)
        time.sleep(float(os.environ.get("FAKE_LEAN_SECS", "0")))
        mode = os.environ.get("FAKE_LEAN", "ok")
        if mode == "raise":
            raise RuntimeError("no toolchain")
        return _Result(mode == "ok", [] if mode == "ok" else ["boom"])

    def close(self):
        _rec("close")


for name in ("mathverify", "mathverify.formal"):
    sys.modules[name] = types.ModuleType(name)
sys.modules["mathverify.formal.lean_client"] = mod = types.ModuleType("mathverify.formal.lean_client")
mod.LeanClient = LeanClient

from lean_warmup import pytest_runtestloop  # noqa: E402,F401
'''

SUITE = '''
import json
import pytest

LOG = {log!r}


def _events():
    try:
        with open(LOG, encoding="utf-8") as f:
            return [json.loads(l)["event"] for l in f]
    except FileNotFoundError:
        return []


def _lean():
    return "client"


@pytest.fixture
def lean():
    return "client"


def test_helper():
    _lean()
    assert _events()[:3] == ["init", "run", "close"]      # the warm-up ran before this test


def test_fixture(lean):
    assert _events()[:3] == ["init", "run", "close"]


def test_plain():
    pass
'''


def _run(tmp_path: Path, *args: str, **env: str):
    log = tmp_path / "lean.log"
    (tmp_path / "conftest.py").write_text(CONFTEST.format(tests=str(TESTS), log=str(log)), encoding="utf-8")
    (tmp_path / "test_suite.py").write_text(SUITE.format(log=str(log)), encoding="utf-8")
    keep = {k: v for k, v in os.environ.items() if not k.startswith(("PYTEST_", "FAKE_LEAN"))}
    r = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-o", "timeout=2",
                        "-o", "addopts=", "-rA", *args, "test_suite.py"],
                       cwd=tmp_path, env={**keep, "FAKE_LEAN_SECS": "3", **env},
                       capture_output=True, text=True, timeout=120)
    events = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    return r, events


@pytest.mark.parametrize("select", ["helper", "fixture", "helper or fixture or plain"])
def test_a_lean_test_gets_one_warm_up_outside_its_timeout(tmp_path, select):
    r, events = _run(tmp_path, "-k", select)
    assert r.returncode == 0, r.stdout + r.stderr          # 3 s of warm-up against a 2 s test timeout
    assert [e["event"] for e in events] == ["init", "run", "close"], events
    assert events[0]["boot_timeout"] == 900.0 and events[1]["code"] == lean_warmup.PROBE
    assert "Lean ısınması: 3 s, hazır" in r.stdout, r.stdout


@pytest.mark.parametrize("args", [("-k", "plain"), ("--collect-only",)])
def test_no_lean_test_no_warm_up(tmp_path, args):
    r, events = _run(tmp_path, *args)
    assert r.returncode == 0, r.stdout + r.stderr
    assert events == [] and "Lean ısınması" not in r.stdout


@pytest.mark.parametrize("mode,why", [("raise", "RuntimeError: no toolchain"), ("unclean", "boom")])
def test_a_failed_warm_up_is_reported_and_the_tests_still_run(tmp_path, mode, why):
    r, events = _run(tmp_path, "-k", "plain or helper", FAKE_LEAN=mode, FAKE_LEAN_SECS="0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert [e["event"] for e in events] == ["init", "run", "close"], events
    assert f"Lean ısınması: 0 s, hazır değil ({why})" in r.stdout, r.stdout
    assert "PASSED test_suite.py::test_plain" in r.stdout and "PASSED test_suite.py::test_helper" in r.stdout


def test_the_suite_loads_the_warm_up(request):
    impls = request.config.pluginmanager.hook.pytest_runtestloop.get_hookimpls()
    assert any(getattr(i.function, "__module__", "") == "lean_warmup" for i in impls)


def _calls(tree: ast.AST, names: set[str]):
    """(enclosing function, called name) for every call of one of `names`."""
    out = []

    def visit(node, owner):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, child.name)
                continue
            if isinstance(child, ast.Call):
                f = child.func
                name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                if name in names:
                    out.append((owner, name))
            visit(child, owner)
    visit(tree, None)
    return out


def test_the_suite_reaches_a_live_lean_only_through_the_names_the_warm_up_knows():
    """needs_lean() recognises a Lean test by the `_lean()` helper or the `lean` fixture. A test that
    started Lean another way would get no warm-up and would again meet a cold Lean inside its
    300 s timeout."""
    found = {}
    for path in sorted(TESTS.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for owner, name in _calls(tree, {"lean_available", "get_lean"}):
            found.setdefault(owner, set()).add(path.name)
    assert found, "no live-Lean entry point found: the scan is broken"
    assert set(found) <= lean_warmup.LEAN_HELPERS | lean_warmup.LEAN_FIXTURES, found
