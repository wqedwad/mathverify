"""The runtime half of the staged-check rule (scripts/check.py, DECISIONS §59).

A change to documentation skips the checks unless code reads that document, and check.py finds
the readers statically: a document is read when a string constant of the Python code names it or
DOCS_READ_UNNAMED covers it. A test that reaches a document another way (a glob over a directory,
a path built at run time, a copied directory) would make that rule let a change through unchecked.
This plugin records every document, and the --full log, that the test process opens or copies
inside the repository (audit hooks on "open", "shutil.copyfile" and "_winapi.CopyFile2": on
Windows shutil.copy2 copies through CopyFile2 and opens nothing) and fails the session when one of
them is a document the rule does not count as code, or a report the checks write (the rule never
counts reports as code, so no test may depend on one).

Loaded by tests/conftest.py for every run of the suite, and with `-p doc_read_guard` by its own
end-to-end test. Not seen: opens in child processes (a script a test runs; shell scripts are
covered by the lists in tests/test_staged_check.py instead) and os.open with dir_fd (the event
carries no directory).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPENED: set[str] = set()
_EVENTS = frozenset({"open", "shutil.copyfile", "_winapi.CopyFile2"})     # the source path comes first
_WATCHED = (".md", "check_full.log")                                       # documents, the --full log


def record(event: str, args) -> None:
    """The audit hook. Called for every audit event of the process, so it returns at once for all
    but _EVENTS. It never raises: an exception here would come out of the test's own open()."""
    if event not in _EVENTS or not args:
        return
    try:
        path = args[0]
        if isinstance(path, int):                  # open(fd)
            return
        p = os.fsdecode(path)
        if not p.lower().endswith(_WATCHED):
            if not os.path.islink(p):
                return
            p = os.path.realpath(p)                # a link whose own name hides a document
            if not p.lower().endswith(_WATCHED):
                return
        OPENED.add(os.path.realpath(p))            # resolved now: a relative path, "link/../x"
    except Exception:  # noqa: BLE001
        pass


def _check_module():
    spec = importlib.util.spec_from_file_location("check_script_doc_reads", ROOT / "scripts" / "check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def problems() -> list[str]:
    """The session's error lines: empty when every watched file the tests opened is code."""
    check = _check_module()
    try:
        bad = check.unexplained_doc_reads(ROOT, OPENED)
    except check.UnreadableSource as e:
        return [f"ERROR belge-okuma: Python kaynağı okunamadı ({e}); testlerin açtığı belgeler denetlenemedi"]
    if not bad:
        return []
    return [f"ERROR belge-okuma: testler {rel} dosyasını açtı, ama scripts/check.py'nin kademeli kuralı onu kod saymıyor"
            for rel in bad] + [
        "ERROR belge-okuma: okunan belge bir Python dizgi sabitiyle adlandırılmalı (ya da "
        "check.DOCS_READ_UNNAMED'a yazılmalı); testler üretilmiş raporları okumaz (DECISIONS §59)"]


_INSTALLED = False
_PROBLEMS: list[str] = []


def install() -> None:
    global _INSTALLED
    if not _INSTALLED:                             # an audit hook cannot be removed: add it once
        sys.addaudithook(record)
        _INSTALLED = True


def installed() -> bool:
    return _INSTALLED


install()


def pytest_sessionfinish(session, exitstatus):
    _PROBLEMS[:] = problems()
    if _PROBLEMS and session.exitstatus == pytest.ExitCode.OK:   # a worse status (interrupted, ...) stays
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter):
    """The lines go out here, each on its own line: written from pytest_sessionfinish, the first one
    was glued to the "[100%]" progress line, where check.py's pytest gate does not look for it."""
    if _PROBLEMS:
        terminalreporter.write_sep("=", "belge okuma denetimi")
        for line in _PROBLEMS:
            terminalreporter.write_line(line)
