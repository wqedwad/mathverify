"""C17 D-cells: right final answer, wrong `compute` step not refuted.
(a) `Limit(e, x, a)` is stored by SymPy with dir='+', and the step layer reads that as one-sided
    although SOLVER_FORMAT promises two-sided classification (E6);
(b) steps with Limit/Integral inside a larger expression are never checked;
(c) the calculus certificate classes of C01/C04/C05 also verify wrong steps.
Ground truth: lim_{x->0} |x|/x does not exist; 2*lim sin(x)/x = 2 != 5; 2*int x dx = x^2 (+C) != x^3."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    print("   Limit(Abs(x)/x, x, 0).args =", sp.Limit(sp.Abs(x)/x, x, 0).args,
          "; one-sided limits:", sp.limit(sp.Abs(x)/x, x, 0, "+"), sp.limit(sp.Abs(x)/x, x, 0, "-"))
    lim_ir = IR("limit", {"expr": "(x**2 - 4)/(x - 2)", "var": "x", "to": "2"})
    ok_step = {"id": "s9", "kind": "compute", "claim": "Limit(x + 2, x, 2) = 4", "from": []}
    st = lambda c: [{"id": "s1", "kind": "compute", "claim": c, "from": []}, ok_step]
    check("step Limit(Abs(x)/x, x, 0) = 1", lim_ir, SOL("value", "4", st("Limit(Abs(x)/x, x, 0) = 1")), "CORRECT")
    check("step Limit(1/x, x, 0) = oo", lim_ir, SOL("value", "4", st("Limit(1/x, x, 0) = oo")), "CORRECT")
    check("step 2*Limit(sin(x)/x, x, 0) = 5", lim_ir, SOL("value", "4", st("2*Limit(sin(x)/x, x, 0) = 5")), "CORRECT")
    check("step Limit(log(x), x, -1) = I*pi", lim_ir, SOL("value", "4", st("Limit(log(x), x, -1) = I*pi")), "CORRECT")
    anti = IR("antiderivative", {"integrand": "cos(x)", "var": "x"})
    one = lambda c: [{"id": "s1", "kind": "compute", "claim": c, "from": []}]
    check("step 2*Integral(x, x) = x**3", anti, SOL("expression", "sin(x) + C", one("2*Integral(x, x) = x**3")), "CORRECT")
    check("step Integral(1/x, x) = log(x)", anti, SOL("expression", "sin(x) + C", one("Integral(1/x, x) = log(x)")), "CORRECT")
    der = IR("derivative", {"f": "x**2", "var": "x", "at": "3"})
    check("step Subs(Derivative(Abs(x), x), x, 0) = 0", der, SOL("value", "6", one("Subs(Derivative(Abs(x), x), x, 0) = 0")), "CORRECT")
