"""Version pinning written into every VerificationResult (handoff §11/13)."""
from __future__ import annotations
import sys


def collect_versions() -> dict[str, str]:
    import sympy, mpmath, z3
    out = {
        "python": sys.version.split()[0],
        "sympy": sympy.__version__,
        "mpmath": mpmath.__version__,
        "z3": z3.get_version_string(),
        "mathverify": "0.1.0",
    }
    try:
        from importlib.metadata import version as _v
        out["math-verify"] = _v("math-verify")
        out["latex2sympy2_extended"] = _v("latex2sympy2_extended")
    except Exception:  # pragma: no cover
        pass
    return out
