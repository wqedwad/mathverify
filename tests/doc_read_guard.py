"""The runtime half of the staged-check rule (scripts/check.py, DECISIONS §59).

A change to documentation skips the checks unless code reads that document, and check.py finds
the readers statically: a document is read when a string constant of the Python code names it or
DOCS_READ_UNNAMED covers it. A test that reaches a document another way (a glob over a directory,
a path built at run time, a copied directory) would make that rule let a change through unchecked.
This plugin records every document, and the --full log, that the test process opens, copies or
links inside the repository (audit hooks on "open", "shutil.copyfile", "_winapi.CopyFile2",
"os.link" and "os.symlink"; on Windows shutil.copy2 copies through CopyFile2 and opens nothing)
and fails the session when one of them is a document the rule does not count as code, or a
report the checks write (the rule never counts reports as code, so no test may depend on one).
A relative link target is read from the link's directory; "_winapi.CreateJunction" (a Windows
directory link) is watched like a linked directory.

Loaded by tests/conftest.py for every run of the suite, and with `-p doc_read_guard` by its own
end-to-end test. Not seen: child processes (the harnesses of a --full, a script a test runs:
tests/test_staged_check.py pins instead every .md-shaped constant of the code outside tests/, and
every document mention and directory walk in the shell scripts) and os.open with dir_fd (the
event carries no directory).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPENED: set[str] = set()
# The source path comes first in each. os.link and os.symlink give a document a second name that
# a later read (in this process or a child) would not show; _winapi.CreateJunction is Windows's
# directory link that needs no privilege.
_EVENTS = frozenset({"open", "shutil.copyfile", "_winapi.CopyFile2", "os.link", "os.symlink", "_winapi.CreateJunction"})
_DIRECTORY_LINKS = ("os.symlink", "_winapi.CreateJunction")
_WATCHED = (".md", "check_full.log")                                       # documents, the --full log


def _windows_name(p: str) -> str:
    """Windows opens "X.md." and "X.md " and "X.md::$DATA" as X.md: drop what it drops. The name is
    what follows the last backslash, or the whole path when it has none: a "/" path's only colon
    before its name is a drive ("C:/r/x.md", "C:x.md"), since a Windows name cannot hold one."""
    head, sep, tail = p.rpartition("\\")
    if not sep and p[1:2] == ":":                  # the drive stays
        head, tail = p[:2], p[2:]
    return head + sep + tail.split(":", 1)[0].rstrip(". ")


def _watch(event: str, p: str) -> None:
    if event in _DIRECTORY_LINKS and os.path.isdir(p):  # a linked directory: every watched file in it
        for d, _, files in os.walk(p):
            OPENED.update(os.path.realpath(os.path.join(d, f)) for f in files if f.lower().endswith(_WATCHED))
        return
    if os.name == "nt":
        p = _windows_name(p)
    if not p.lower().endswith(_WATCHED):
        if not os.path.islink(p):
            return
        p = os.path.realpath(p)                    # a link whose own name hides a document
        if not p.lower().endswith(_WATCHED):
            return
    OPENED.add(os.path.realpath(p))                # resolved now: a relative path, "link/../x"


def record(event: str, args) -> None:
    """The audit hook. Called for every audit event of the process, so it returns at once for all
    but _EVENTS. It never raises: an exception here would come out of the test's own open()."""
    if event not in _EVENTS or not args:
        return
    try:
        path = args[0]
        if isinstance(path, int):                  # open(fd)
            return
        path = os.fsdecode(path)
        if event == "os.symlink" and not os.path.isabs(path) and len(args) > 1 and not isinstance(args[1], int):
            # a link's target is relative to the link's own directory, not to the working one
            path = os.path.join(os.path.dirname(os.fsdecode(args[1])), path)
        _watch(event, path)
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
