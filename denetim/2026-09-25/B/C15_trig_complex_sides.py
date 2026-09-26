"""C15 trig_solve: solveset(domain=Reals) only makes x real; sqrt/log of negative values are complex
and compare equal. Ground truth: at x = 5pi/4 sin = cos = -sqrt(2)/2 < 0, so sqrt/log are undefined;
the real solution set is {pi/4 + 2k pi}."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    assert sp.sqrt(sp.sin(5*sp.pi/4)).is_real is False
    TS = lambda eq: IR("trig_solve", {"var": "x", "equation": eq}, answer_shape="set")
    check("sqrt(sin x) = sqrt(cos x): {pi/4 + k pi}", TS("sqrt(sin(x)) = sqrt(cos(x))"), SOL("set", "{pi/4 + k*pi}"), "CORRECT")
    check("log(sin x) = log(cos x): {pi/4 + k pi}", TS("log(sin(x)) = log(cos(x))"), SOL("set", "{pi/4 + k*pi}"), "CORRECT")
    check("sqrt(sin x) = sqrt(cos x): {pi/4 + 2k pi} (right answer)", TS("sqrt(sin(x)) = sqrt(cos(x))"), SOL("set", "{pi/4 + 2*k*pi}"), "INCORRECT")
