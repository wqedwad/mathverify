"""C10 equivalence: a LaTeX payload keeps decimals as 53-bit Floats, and num_equal then widens the
tolerance to the Float's own precision (~1e-12), while the same decimal in canonical syntax is
rationalised and compared exactly. Ground truth: 0.3333333333333 != 1/3 exactly."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    assert sp.Rational("0.3333333333333") != sp.Rational(1, 3)
    check("lim_{x->1} x/3 = 0.3333333333333\\cdot 1", IR("limit", {"expr": "x/3", "var": "x", "to": "1"}), SOL("value", r"0.3333333333333 \cdot 1"), "CORRECT")
    check("d/dx x^3/3 at 1 = 0.9999999999999\\cdot 1", IR("derivative", {"f": "x**3/3", "var": "x", "at": "1"}), SOL("value", r"0.9999999999999\cdot 1"), "CORRECT")
    check("max of 4-(x-1)^2 on [0,3] = 3.9999999999999\\cdot 1", IR("extremum", {"f": "4 - (x-1)**2", "var": "x", "interval": "[0, 3]", "which": "max"}), SOL("value", r"3.9999999999999\cdot 1"), "CORRECT")
    check("int_0^1 x^2 = \\frac{0.9999999999999}{3}", IR("definite_integral", {"integrand": "x**2", "var": "x", "a": "0", "b": "1"}), SOL("value", r"\frac{0.9999999999999}{3}"), "CORRECT")
    check("control: canonical 0.3333333333333 is refused", IR("limit", {"expr": "x/3", "var": "x", "to": "1"}), SOL("value", "0.3333333333333"), "CORRECT")
