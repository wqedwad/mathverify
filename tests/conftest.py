"""Shared fixtures. The §6 tests are the behavioural contract of this project."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("PYTHONUTF8", "1")


@pytest.fixture(scope="session")
def x():
    import sympy as sp
    return sp.Symbol("x", real=True)


@pytest.fixture(scope="session")
def sandbox():
    from mathverify.sandbox import get_sandbox
    sb = get_sandbox()
    yield sb


@pytest.fixture(scope="session")
def evalset_items():
    from harness.loader import load_items
    return load_items(ROOT / "evalset" / "items")
