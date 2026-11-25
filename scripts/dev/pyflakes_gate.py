"""The "pyflakes temiz" gate of scripts/check.py on its own, for CI: same paths, same `# noqa` rule.

    python scripts/dev/pyflakes_gate.py        # exit 0: no finding; 1: findings, or pyflakes did not run
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check  # noqa: E402  (scripts/check.py)


def main() -> int:
    p = subprocess.run([sys.executable, "-m", "pyflakes", "src", "harness", "scripts", "tests", "evalset/build"],
                       cwd=ROOT, capture_output=True, text=True)
    findings, unparsed = check.pyflakes_findings(p.stdout + p.stderr, p.returncode, ROOT)
    for f in findings:
        print(f)
    print(f"pyflakes: {len(findings)} finding(s)" + (" (pyflakes did not run)" if unparsed else ""))
    return 1 if findings or unparsed else 0


if __name__ == "__main__":
    sys.exit(main())
