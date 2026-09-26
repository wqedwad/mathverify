"""C14 trig_solve: the equation is parsed with auto-simplification only; sin(x)^2/sin(x) becomes
sin(x), so the solutions x = k*pi, where the written left side is 0/0, are certified.
Ground truth: at every solution of sin(x) = 0 the written expression is undefined => empty set."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    assert (sp.Pow(sp.sin(sp.pi), 2, evaluate=False) / sp.sin(sp.pi, evaluate=False)) is sp.nan
    TS = lambda eq, iv=None: IR("trig_solve", dict({"var": "x", "equation": eq}, **({"interval": iv} if iv else {})), answer_shape="set")
    check("sin(x)^2/sin(x) = 0: {k*pi}", TS("sin(x)**2/sin(x) = 0"), SOL("set", "{k*pi}"), "CORRECT")
    check("sin(x)^2/sin(x) = 0 on [0,2pi): {0, pi}", TS("sin(x)**2/sin(x) = 0", "[0, 2*pi)"), SOL("set", "{0, pi}"), "CORRECT")
