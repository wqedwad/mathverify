"""H04 limit: an infinite value written as LaTeX (\\infty, +\\infty, $\\infty$, -\\infty) or S.Infinity
with kind 'value' is not recognised as infinite and is refuted. Ground truth: lim_{x->0} 1/x^2 = +oo."""
from _r import IR, SOL, check

if __name__ == "__main__":
    L = lambda e: IR("limit", {"expr": e, "var": "x", "to": "0"})
    for p in (r"\infty", r"+\infty", r"$\infty$", "S.Infinity"):
        check(f"lim 1/x^2 = {p}", L("1/x**2"), SOL("value", p), "INCORRECT")
    check(r"lim -1/x^2 = -\infty", L("-1/x**2"), SOL("value", r"-\infty"), "INCORRECT")
