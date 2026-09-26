"""H05 tangent_line: a vertical tangent builds the 'truth' Eq(y, zoo*x) and refutes x = 0.
Ground truth: cbrt continuous at 0 with |f'| -> oo, vertical tangent x = 0 (for the real branch x>=0
under SymPy's principal cbrt as well)."""
from _r import IR, SOL, check

if __name__ == "__main__":
    check("tangent to cbrt(x) at 0: x = 0", IR("tangent_line", {"f": "cbrt(x)", "var": "x", "at": "0"}, vars_=("x", "y")), SOL("equation", "x = 0"), "INCORRECT")
