"""C16 trig_solve: SymPy's solveset is the only oracle and loses the root x = pi of
sqrt(3) sin x - cos x = 1 (= 2 sin(x - pi/6) = 1 -> x = pi/3 or pi). Ground truth checked exactly."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    e = sp.sqrt(3)*sp.sin(x) - sp.cos(x) - 1
    assert sp.simplify(e.subs(x, sp.pi)) == 0 and sp.simplify(e.subs(x, sp.pi/3)) == 0
    print("   sympy solveset on [0,2pi):", sp.solveset(e, x, sp.Interval.Ropen(0, 2*sp.pi)))
    TS = lambda eq, iv=None: IR("trig_solve", dict({"var": "x", "equation": eq}, **({"interval": iv} if iv else {})), answer_shape="set")
    check("sqrt3 sin x - cos x = 1 on [0,2pi): {pi/3}", TS("sqrt(3)*sin(x) - cos(x) = 1", "[0, 2*pi)"), SOL("set", "{pi/3}"), "CORRECT")
    check("sqrt3 sin x - cos x = 1: {pi/3 + 2k pi}", TS("sqrt(3)*sin(x) - cos(x) = 1"), SOL("set", "{pi/3 + 2*k*pi}"), "CORRECT")
    check("sqrt3 sin x - cos x = 1 on [0,2pi): {pi/3, pi} (right answer)", TS("sqrt(3)*sin(x) - cos(x) = 1", "[0, 2*pi)"), SOL("set", "{pi/3, pi}"), "INCORRECT")
    check("sin x + sqrt3 cos x = -sqrt3 on [0,2pi): {4pi/3} (misses pi)", TS("sin(x) + sqrt(3)*cos(x) = -sqrt(3)", "[0, 2*pi)"), SOL("set", "{4*pi/3}"), "CORRECT")
    # SymPy returns a spurious root 0 (e(0) = 1 - sqrt(3) != 0) plus an opaque expression, and
    # misses 3pi/2. True roots: 2 sin(x - pi/3) = -1 -> x = pi/6, 3pi/2.
    e2 = sp.sin(x) - sp.sqrt(3)*sp.cos(x) + 1
    assert sp.simplify(e2.subs(x, 0)) != 0 and sp.simplify(e2.subs(x, sp.pi/6)) == 0 and sp.simplify(e2.subs(x, 3*sp.pi/2)) == 0
    print("   sympy solveset(sin x - sqrt3 cos x = -1) numerically:", [sp.N(v, 8) for v in sp.solveset(e2, x, sp.Interval.Ropen(0, 2*sp.pi))])
    check("sin x - sqrt3 cos x = -1 on [0,2pi): {0, pi/6} (0 is not a root)", TS("sin(x) - sqrt(3)*cos(x) = -1", "[0, 2*pi)"), SOL("set", "{0, pi/6}"), "CORRECT")
    check("sin x - sqrt3 cos x = -1 on [0,2pi): {pi/6, 3pi/2} (right answer)", TS("sin(x) - sqrt(3)*cos(x) = -1", "[0, 2*pi)"), SOL("set", "{pi/6, 3*pi/2}"), "INCORRECT")
    check("sin x - sqrt3 cos x = -1 general: {2k pi, pi/6 + 2k pi}", TS("sin(x) - sqrt(3)*cos(x) = -1"), SOL("set", "{2*k*pi, pi/6 + 2*k*pi}"), "CORRECT")
