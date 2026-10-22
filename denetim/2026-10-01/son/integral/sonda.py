"""The last attack on the merged state, lens 2 (integrals and tolerances; DECISIONS §89-§91, decisions of 16 Oct 2026 in
`kararlar.txt` "MERCEK 2"): the findings G2YO-1..4 and G2RK-1..12 of the integral group.

  False acceptances:
    A  G2YO-1  sgn/Abs/Max/Min change branch at a pole of their argument too: the fundamental theorem was cut at the
               zeros alone (∫_{-2}^{4} sgn((x - 1)/(x + 1)) dx: 0 CORRECT, the true 2 INCORRECT), on every path
               (definite_integral, evaluate, a compute step, an option); a certified 0 is checked against the numbers
    B  G2YO-2  without converged numbers the certificate's value is taken only inside a rigorous enclosure (planted
               wrong certificates, the divergent max(x, 1/x))
    F  G2YO-3  the cell proof of random_point cuts at the poles of a non-smooth function's argument
    M  G2YO-6  a sample point whose difference has no certified sign is no agreement (d4c round 3 YO-B, sibling)
    G  G2YO-4  a declared absolute tolerance is decided exactly (evaluate, and definite_integral, which did not read it)
  Unjust rejections, crashes, coverage:
    C  G2RK-1  the real cube root sign(u)|u|^(1/3) in a primitive is no jump where the primitive is continuous
    D  G2RK-7  a complex quadrature value is no value (the certificate decides, confirmed by an enclosure)
    E  G2RK-10 a convention condition of the primitive (Contains) is met on the region, never an exception
    H  G2RK-2  a declared tolerance against a value with erf, S, C, Si of an irrational argument
    I  G2RK-3/4 the convention gate reads the declared region (x > 0) of a derivative function or an antiderivative
    J  G2RK-5  a Piecewise integrand is cut at its conditions' boundaries
    L  G2RK-9  x**x is real for x > 0 in the fundamental theorem
    N  second round (21 Oct 2026): SI-YO-2 (a planted finite value of a divergent integral; true values of strong
               integrable singularities), SI-YO-3 (a planted 0 of a principal value), SON-INT-RK-1 (a complex claim
               within a declared tolerance), SON-INT-RK-2 (fast oscillations: the time of the certificate's check)
    K  controls whose verdict must not change

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/son/integral/sonda.py [out.json] [groups]

Measured (21 Oct 2026): 189 cases, 110 not as expected on 0e93ed5 (A 17, B 6, C 13, D 9, E 3, F 3, G 8, H 19, I 21,
J 5, L 2, M 4; one held over 300 s), 0 on 4f294aa. The derivative of x·∛x (group C) is G2RK-13's, the calculus group's:
here only no false verdict. Group M's last case is a recorded residual of the narrow G2YO-6 rule.
Second round (22 Oct 2026): 223 cases with group N, not as expected 120 on 0e93ed5 (N 10), 15 on 3afddba (all N: 8
planted, 7 complex tolerances), 0 on 14769a8; with the three SG-1 cases of group N, 226 cases, 0 on cbaea02 (197 s).
Group N's |x|^(-19/20) case is a recorded residual of SI-YO-2.

Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
UNK = {"UNKNOWN"}
NOTOK = {"INCORRECT", "UNKNOWN"}      # anything but a false acceptance
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
ANY = {"CORRECT", "INCORRECT", "UNKNOWN"}
VER = {"verified"}
REF = {"refuted"}
NOTREF = {"verified", "unknown", "skipped"}
NOTVER = {"refuted", "unknown", "skipped"}
EXC = "layer_exception"

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "real", "constraints": ["x > 0"]}
XPOS = {"name": "x", "domain": "positive_real"}


def ir(kind, params, vars_=(X,), givens=(), shape="scalar", options=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}
    if options:
        d["options"] = options
    return d


def dint(f, a, b, options=None, **tol):
    return ir("definite_integral", dict({"integrand": f, "var": "x", "a": str(a), "b": str(b)}, **tol), options=options)


def ev(e, vars_=(X,), **tol):
    return ir("evaluate", dict({"expr": e}, **tol), vars_)


def anti(f, vars_=(X,)):
    return ir("antiderivative", {"integrand": f, "var": "x"}, vars_, shape="expression")


def der(f, vars_=(X,), at=None):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = str(at)
    return ir("derivative", p, vars_, shape="scalar" if at is not None else "expression")


def simp(e, vars_=(X,)):
    return ir("simplify_expression", {"expr": e}, vars_, shape="expression")


def sol(payload, steps=(), kind="value", option=None):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": "compute", "claim": c, "from": [], "text": ""}
                                            for i, c in enumerate(steps)]}


X1 = ir("evaluate", {"expr": "x + 1"}, (X,), ["x = 1"])           # the right answer is 2


def step(claim):
    """A compute step next to the right answer 2 of x + 1 at x = 1: only the step's status is asked."""
    return X1, sol("2", [claim])


SG = "sign((x - 1)/(x + 1))"            # +1 on (-2, -1), -1 on (-1, 1), +1 on (1, 4): ∫_{-2}^{4} = 2
SG2 = "sign((x - 1)/(x + 2))"           # ∫_{-3}^{3} = 1 - 3 + 2 = 0
OPT = {"A": "-2", "B": "0", "C": "1", "D": "2", "E": "3"}


# A: G2YO-1 ------------------------------------------------------------------------------------------------------
def cases_a():
    return [
        ("dint sgn((x-1)/(x+1)) [-2,4] claim 0 (true 2)", dint(SG, -2, 4), sol("0"), NOTOK, None, EXC),
        ("dint sgn((x-1)/(x+1)) [-2,4] claim 2", dint(SG, -2, 4), sol("2"), NOTNO, None, EXC),
        ("MC option B = 0 (wrong)", dint(SG, -2, 4, options=OPT), sol("0", option="B"), NOTOK, None),
        ("MC option D = 2", dint(SG, -2, 4, options=OPT), sol("2", option="D"), NOTNO, None),
        ("dint g/|g| [-2,4] claim 0 (true 2)", dint("((x - 1)/(x + 1))/Abs((x - 1)/(x + 1))", -2, 4), sol("0"), NOTOK, None),
        ("dint g/|g| [-2,4] claim 2", dint("((x - 1)/(x + 1))/Abs((x - 1)/(x + 1))", -2, 4), sol("2"), NOTNO, None),
        ("evaluate Integral(sgn((x-1)/(x+2)), (x,-3,3)) claim -2 (true 0)", ev(f"Integral({SG2}, (x, -3, 3))"), sol("-2"),
         NOTOK, None),
        ("evaluate same claim 0", ev(f"Integral({SG2}, (x, -3, 3))"), sol("0"), NOTNO, None),
        ("evaluate Integral(sgn((x-2)/(x+1)), (x,-3,3)) claim -4 (true 0)",
         ev("Integral(sign((x - 2)/(x + 1)), (x, -3, 3))"), sol("-4"), NOTOK, None),
        ("evaluate Integral(sgn((x-2)/(x+1)), (x,-3,3)) claim 0", ev("Integral(sign((x - 2)/(x + 1)), (x, -3, 3))"),
         sol("0"), NOTNO, None),
        ("dint sgn((x-1)/(x+2)) [-3,3] claim 0 with true steps", dint(SG2, -3, 3),
         sol("0", [f"Integral({SG2}, (x, -3, 3)) = Integral(1, (x, -3, -2)) + Integral(-1, (x, -2, 1))"
                   " + Integral(1, (x, 1, 3))",
                   "Integral(1, (x, -3, -2)) + Integral(-1, (x, -2, 1)) + Integral(1, (x, 1, 3)) = 0"]), NOTNO, NOTREF),
        ("step 'Integral(sgn((x-1)/(x+1)), (x,-2,4)) = 0' not verified", *step(f"Integral({SG}, (x, -2, 4)) = 0"),
         ANY, NOTVER),
        ("step '... = 2' not refuted", *step(f"Integral({SG}, (x, -2, 4)) = 2"), NOTNO, NOTREF),
        ("dint sgn(x/(x+1)) [-3/2,3/2] claim 0 (true 1)", dint("sign(x/(x + 1))", "-3/2", "3/2"), sol("0"), NOTOK, None),
        ("dint sgn(x/(x+1)) [-3/2,3/2] claim 1", dint("sign(x/(x + 1))", "-3/2", "3/2"), sol("1"), NOTNO, None),
        ("dint sgn(1/(x-1)) [0,3] claim 3 (true 1: the pole is the only switch)", dint("sign(1/(x - 1))", 0, 3), sol("3"),
         NOTOK, None),
        ("dint sgn(1/(x-1)) [0,3] claim 1", dint("sign(1/(x - 1))", 0, 3), sol("1"), NOTNO, None),
        ("dint Max(x, x + 1/(x - 1/3) - 10) [-1,1] claim 0 (divergent)", dint("Max(x, x + 1/(x - 1/3) - 10)", -1, 1),
         sol("0"), NOTOK, None),
        ("dint Min(x, 1/x) [-1/4,2] claim log2 + 15/32 (divergent)", dint("Min(x, 1/x)", "-1/4", 2),
         sol("log(2) + 15/32"), NOTOK, None),
        ("evaluate Integral(Max(x, 1/x), (x,-2,1/4)) claim -log2 - 15/32 (divergent)",
         ev("Integral(Max(x, 1/x), (x, -2, 1/4))"), sol("-log(2) - 15/32"), NOTOK, None),
        ("dint Max(1, 1/x) [1/2,2] = log2 + 1 (no pole inside)", dint("Max(1, 1/x)", "1/2", 2), sol("log(2) + 1"), OK, None),
        ("dint sgn((x-1)(x+1)) [-2,4] = 2 (zeros only)", dint("sign((x - 1)*(x + 1))", -2, 4), sol("2"), OK, None),
    ]


# B: G2YO-2 ------------------------------------------------------------------------------------------------------
def planted(q, s, value, numbers=False):
    """verify with the certificate made to prove `value`; without `numbers` the quadrature gives no value either."""
    def run():
        import sympy as sp
        from mathverify.certify import calculus
        from mathverify.verifier import verify
        saved = calculus.certified_integral_value, calculus.definite_integral_numeric
        calculus.certified_integral_value = lambda *a, **k: (sp.sympify(value), {"certificate": "planted"})
        if not numbers:
            calculus.definite_integral_numeric = lambda *a, **k: (None, {"converged": False, "error": "planted"})
        try:
            return verify(q, s).verdict
        finally:
            calculus.certified_integral_value, calculus.definite_integral_numeric = saved
    return run


def cases_b():
    return [
        ("dint Max(x, 1/x) [-2,1/4] claim -log2 - 15/32 (divergent)", dint("Max(x, 1/x)", -2, "1/4"),
         sol("-log(2) - 15/32"), NOTOK, None),
        ("planted wrong 1 for ∫_0^1 x², no numbers: claim 1", planted(dint("x**2", 0, 1), sol("1"), "1"), None, NOTOK, None),
        ("planted wrong 1 for ∫_0^1 x², no numbers: claim 1/3 not refuted",
         planted(dint("x**2", 0, 1), sol("1/3"), "1"), None, NOTNO, None),
        ("planted true 1/3, no numbers: claim 1/3", planted(dint("x**2", 0, 1), sol("1/3"), "1/3"), None, OK, None),
        ("planted wrong 2 for ∫_0^1 asinh x, no numbers, no enclosure (no interval asinh): claim 2",
         planted(dint("asinh(x)", 0, 1), sol("2"), "2"), None, NOTOK, None),
        ("planted wrong 0 for ∫_-1^1 1/x, no numbers, enclosure (-oo, oo): claim 0",
         planted(dint("1/x", -1, 1), sol("0"), "0"), None, NOTOK, None),
        ("an infinite range runs no ladder: ∫_0^oo e^-x = 1 (the certificate decides, d4c J)", dint("exp(-x)", 0, "oo"),
         sol("1"), OK, None),
        ("an infinite range: ∫_1^oo 1/x² = 1/2 (wrong)", dint("1/x**2", 1, "oo"), sol("1/2"), NO, None),
        ("a ladder that settles (interior singularity): ∫_-1^8 x^(-1/3) = 9/2", dint("1/cbrt(x)", -1, 8), sol("9/2"), OK,
         None),
        ("a ladder that settles: ∫_-1^8 x^(-1/3) = 5 (wrong)", dint("1/cbrt(x)", -1, 8), sol("5"), NO, None),
        ("planted wrong 0 for ∫_{-1}^{2} x dx = 3/2, numbers: claim 0",
         planted(dint("x", -1, 2), sol("0"), "0", numbers=True), None, NOTOK, None),
        ("planted wrong 0, numbers: claim 3/2 not refuted", planted(dint("x", -1, 2), sol("3/2"), "0", numbers=True),
         None, NOTNO, None),
        ("planted true 0 for ∫_{-1}^{1} x³ dx, numbers: claim 0", planted(dint("x**3", -1, 1), sol("0"), "0", numbers=True),
         None, OK, None),
    ]


# C: G2RK-1 ------------------------------------------------------------------------------------------------------
def cases_c():
    opts = {"A": "3*x*cbrt(x)/4", "B": "4*x*cbrt(x)/3", "C": "3*cbrt(x)/4", "D": "cbrt(x)**2/3", "E": "x*cbrt(x)"}
    mc = anti("cbrt(x)")
    mc["options"] = opts
    return [
        ("∫ cbrt x = 3x cbrt x/4", anti("cbrt(x)"), sol("3*x*cbrt(x)/4"), OK, None),
        ("∫ cbrt x = 3 cbrt(x^4)/4", anti("cbrt(x)"), sol("3*cbrt(x**4)/4"), NOTNO, None),
        ("∫ cbrt x, LaTeX claim", anti("cbrt(x)"), sol(r"\frac{3}{4}x\sqrt[3]{x}"), OK, None),
        ("∫ cbrt x + C", anti("cbrt(x)"), sol("3*x*cbrt(x)/4 + C"), OK, None),
        ("∫ cbrt x, option A", mc, sol("3*x*cbrt(x)/4", option="A"), OK, None),
        ("∫ root(x,3)", anti("root(x, 3)"), sol("3*x*root(x, 3)/4"), OK, None),
        ("∫ cbrt(x²) = 3x cbrt(x²)/5", anti("cbrt(x**2)"), sol("3*x*cbrt(x**2)/5"), OK, None),
        ("∫ x cbrt x = 3x² cbrt x/7", anti("x*cbrt(x)"), sol("3*x**2*cbrt(x)/7"), OK, None),
        ("∫ cbrt(x-1)", anti("cbrt(x - 1)"), sol("3*(x - 1)*cbrt(x - 1)/4"), OK, None),
        ("∫ cbrt x + 1", anti("cbrt(x) + 1"), sol("3*x*cbrt(x)/4 + x"), OK, None),
        ("∫ cbrt(2x+1)", anti("cbrt(2*x + 1)"), sol("3*(2*x + 1)*cbrt(2*x + 1)/8"), OK, None),
        ("∫ x² cbrt(x³+1)", anti("x**2*cbrt(x**3 + 1)"), sol("(x**3 + 1)*cbrt(x**3 + 1)/4"), OK, None),
        ("∫ 5th root", anti("root(x, 5)"), sol("5*x*root(x, 5)/6"), OK, None),
        ("∫ cbrt x = x cbrt x (wrong)", anti("cbrt(x)"), sol("x*cbrt(x)"), NO, None),
        ("∫ cbrt x = 3x cbrt x/4 + sign(x) (jump at 0)", anti("cbrt(x)"), sol("3*x*cbrt(x)/4 + sign(x)"), NO, None),
        ("∫ 2x = x² + sign(x)·x (continuous, wrong derivative)", anti("2*x"), sol("x**2 + x*sign(x)"), NO, None),
        ("∫ |x| = x|x|/2 (sign-free control)", anti("Abs(x)"), sol("x*Abs(x)/2"), OK, None),
        # the derivative path is G2RK-13's (the calculus group): here only no false verdict
        ("d/dx x cbrt x = 4 cbrt x/3", der("x*cbrt(x)"), sol("4*cbrt(x)/3"), NOTNO, None),
        ("d/dx x cbrt x = 4 cbrt x/3 + 1 - |sign x| (wrong at 0 only)", der("x*cbrt(x)"),
         sol("4*cbrt(x)/3 + 1 - Abs(sign(x))"), NOTOK, None),
        ("d/dx x cbrt x = cbrt x (wrong)", der("x*cbrt(x)"), sol("cbrt(x)"), NO, None),
    ]


# D: G2RK-7 ------------------------------------------------------------------------------------------------------
def cases_d():
    return [
        ("√(cos x) sin x [0,π/2] = 2/3", dint("sqrt(cos(x))*sin(x)", 0, "pi/2"), sol("2/3"), OK, None, EXC),
        ("√(cos x) sin x [0,π/2] = 1/2 (wrong)", dint("sqrt(cos(x))*sin(x)", 0, "pi/2"), sol("1/2"), NO, None, EXC),
        ("√(cos x) sin x option C = 2/3", dint("sqrt(cos(x))*sin(x)", 0, "pi/2",
                                               options={"A": "1/3", "B": "1/2", "C": "2/3", "D": "1", "E": "3/2"}),
         sol("2/3", option="C"), OK, None, EXC),
        ("cos^(3/2) x sin x [0,π/2] = 2/5", dint("cos(x)**(3/2)*sin(x)", 0, "pi/2"), sol("2/5"), OK, None, EXC),
        ("√(sin x) cos x [π/2,π] = -2/3", dint("sqrt(sin(x))*cos(x)", "pi/2", "pi"), sol("-2/3"), OK, None, EXC),
        ("√(ln 2 - x) [0,ln 2] = 2(ln 2)^(3/2)/3", dint("sqrt(log(2) - x)", 0, "log(2)"), sol("2*log(2)**(3/2)/3"), OK, None,
         EXC),
        ("√(tan x) [0,π/2] = π/√2: no exception", dint("sqrt(tan(x))", 0, "pi/2"), sol("pi/sqrt(2)"), NOTNO, None, EXC),
        ("√sin/(√sin + √cos) [0,π/2] = π/4: no exception", dint("sqrt(sin(x))/(sqrt(sin(x)) + sqrt(cos(x)))", 0, "pi/2"),
         sol("pi/4"), NOTNO, None, EXC),
        ("1/(1 + tan^√2) [0,π/2] = π/4: no exception", dint("1/(1 + tan(x)**sqrt(2))", 0, "pi/2"), sol("pi/4"), NOTNO, None,
         EXC),
    ]


# E: G2RK-10 -----------------------------------------------------------------------------------------------------
def cases_e():
    return [
        ("∫ cbrt(x²) = 3x^(5/3)/5 (x > 0)", anti("cbrt(x**2)", (XP,)), sol("3*x**(5/3)/5"), OK, None, EXC),
        ("∫ cbrt x = 3x^(4/3)/4 (x > 0)", anti("cbrt(x)", (XP,)), sol("3*x**(4/3)/4"), OK, None, EXC),
        ("∫ 1/cbrt x = 3x^(2/3)/2 (x > 0)", anti("1/cbrt(x)", (XP,)), sol("3*x**(2/3)/2"), OK, None, EXC),
        ("∫ cbrt x = x^(4/3) (x > 0, wrong)", anti("cbrt(x)", (XP,)), sol("x**(4/3)"), NO, None, EXC),
        ("∫ cbrt x = 3x^(4/3)/4 (real: the convention at x < 0)", anti("cbrt(x)"), sol("3*x**(4/3)/4"), UNK, None, EXC),
    ]


# F: G2YO-3 ------------------------------------------------------------------------------------------------------
def cases_f():
    return [
        ("simplify Max(x, x + 1/(x - 1/3) - 10^6) = x", simp("Max(x, x + 1/(x - 1/3) - 10**6)"), sol("x", kind="expression"),
         NOTOK, None),
        ("simplify Min(x, x - 1/(x - 1/3) + 10^6) = x", simp("Min(x, x - 1/(x - 1/3) + 10**6)"), sol("x", kind="expression"),
         NOTOK, None),
        ("simplify Piecewise((x², 1/(x - 1/3) > 10^6), (x, 1/(x - 1/3) <= 10^6)) = x",
         simp("Piecewise((x**2, 1/(x - 1/3) > 10**6), (x, 1/(x - 1/3) <= 10**6))"), sol("x", kind="expression"), NOTOK,
         None),
        ("simplify |x| + |1/(x-1/3) - 10^6| - (1/(x-1/3) - 10^6) = |x|",
         simp("Abs(x) + Abs(1/(x - 1/3) - 10**6) - (1/(x - 1/3) - 10**6)"), sol("Abs(x)", kind="expression"), NOTOK, None),
        ("simplify |1/(x-1)|·(x-1)² = |x-1| (control)", simp("Abs(1/(x - 1))*(x - 1)**2"), sol("Abs(x - 1)", kind="expression"),
         NOTNO, None),
        ("simplify sqrt(x²-2x+1) = |x-1| (control)", simp("sqrt(x**2 - 2*x + 1)"), sol("Abs(x - 1)", kind="expression"), OK,
         None),
        ("simplify Max(x, x²) on x > 1 = x² (control)", simp("Max(x, x**2)", ({"name": "x", "domain": "real",
                                                                             "constraints": ["x > 1"]},)),
         sol("x**2", kind="expression"), OK, None),
    ]


# G: G2YO-4 ------------------------------------------------------------------------------------------------------
def cases_g():
    import sympy as sp
    V = sp.floor(10 ** 40 * sp.pi)
    return [
        ("evaluate e^(π√163) abs_tol 1e-15 claim 262537412640768744", ev("exp(pi*sqrt(163))", (), abs_tol="1e-15"),
         sol("262537412640768744"), NO, None),
        ("evaluate √2 abs_tol 1e-25 claim 1.414213562373095048801", ev("sqrt(2)", (), abs_tol="1e-25"),
         sol("1.414213562373095048801"), NO, None),
        ("evaluate √2 rel 1e-25 abs 1e-30 claim 1.414213562373095048801",
         ev("sqrt(2)", (), rel_tol="1e-25", abs_tol="1e-30"), sol("1.414213562373095048801"), NO, None),
        ("evaluate 10^40 π abs_tol 1/2 claim floor + 10^8", ev("10**40*pi", (), abs_tol="1/2"), sol(str(V + 10 ** 8)), NO,
         None),
        ("evaluate 10^40 π abs_tol 1/2 claim floor (0.69 away)", ev("10**40*pi", (), abs_tol="1/2"), sol(str(V)), NO, None),
        ("evaluate 10^40 π abs_tol 1/2 claim floor + 1 (0.31 away)", ev("10**40*pi", (), abs_tol="1/2"), sol(str(V + 1)), OK,
         None),
        ("evaluate √2 abs_tol 1e-25 claim 1.41421356237309504880168872", ev("sqrt(2)", (), abs_tol="1e-25"),
         sol("1.41421356237309504880168872"), OK, None),
        ("evaluate π abs_tol 0.005 claim 3.14", ev("pi", (), abs_tol="0.005"), sol("3.14"), OK, None),
        ("evaluate π abs_tol 0.005 claim 3.15", ev("pi", (), abs_tol="0.005"), sol("3.15"), NO, None),
        ("evaluate π rel 1e-6 abs 0.01 claim 3.14 (abs holds)", ev("pi", (), rel_tol="1e-6", abs_tol="0.01"), sol("3.14"),
         OK, None),
        ("dint x² [0,1] abs_tol 1e-3 claim 0.333", dint("x**2", 0, 1, abs_tol="1e-3"), sol("0.333"), OK, None),
        ("dint x² [0,1] abs_tol 1e-3 claim 0.34", dint("x**2", 0, 1, abs_tol="1e-3"), sol("0.34"), NO, None),
        ("dint √(1+x³) [0,1] abs_tol 1e-3 claim 1.1114 (no certificate)", dint("sqrt(1 + x**3)", 0, 1, abs_tol="1e-3"),
         sol("1.1114"), OK, None),
        ("dint √(1+x³) [0,1] abs_tol 1e-3 claim 1.12 (no certificate)", dint("sqrt(1 + x**3)", 0, 1, abs_tol="1e-3"),
         sol("1.12"), NO, None),
        ("dint x² [0,1] abs_tol -1 malformed", dint("x**2", 0, 1, abs_tol="-1"), sol("1/3"), UNK, None),
    ]


# H: G2RK-2 ------------------------------------------------------------------------------------------------------
PHI = "exp(-x**2/2)/sqrt(2*pi)"


def cases_h():
    t = {"rel_tol": "1e-3"}
    return [
        ("P(0<Z<1) 0.3413", dint(PHI, 0, 1, **t), sol("0.3413"), OK, None),
        ("P(-1<Z<1) 0.6827", dint(PHI, -1, 1, **t), sol("0.6827"), OK, None),
        ("P(-2<Z<2) 0.9545", dint(PHI, -2, 2, **t), sol("0.9545"), OK, None),
        ("P(-1.96<Z<1.96) 0.95", dint(PHI, "-1.96", "1.96", **t), sol("0.95"), OK, None),
        ("∫_0^1 e^(-2x²) 0.5981", dint("exp(-2*x**2)", 0, 1, **t), sol("0.5981"), OK, None),
        ("∫_0^√2 e^(-x²) 0.8459", dint("exp(-x**2)", 0, "sqrt(2)", **t), sol("0.8459"), OK, None),
        ("∫_-1^1 x² φ 0.1987", dint("x**2*" + PHI, -1, 1, **t), sol("0.1987"), OK, None),
        ("∫_0^1 sin(x²) 0.3103", dint("sin(x**2)", 0, 1, **t), sol("0.3103"), OK, None),
        ("∫_0^1 cos(x²) 0.9045", dint("cos(x**2)", 0, 1, **t), sol("0.9045"), OK, None),
        ("evaluate Integral(φ, (x,0,1)) 0.3413", ev(f"Integral({PHI}, (x, 0, 1))", **t), sol("0.3413"), OK, None),
        ("evaluate Integral(e^(-x²), (x,0,√2)) 0.8459 (erf)", ev("Integral(exp(-x**2), (x, 0, sqrt(2)))", **t),
         sol("0.8459"), OK, None),
        ("evaluate Integral(sin(x²), (x,0,1)) 0.3103 (Fresnel S)", ev("Integral(sin(x**2), (x, 0, 1))", **t), sol("0.3103"),
         OK, None),
        ("evaluate Integral(sin x/x, (x,0,2π)) 1.4182 (Si)", ev("Integral(sin(x)/x, (x, 0, 2*pi))", **t), sol("1.4182"),
         OK, None),
        ("∫_1^√2 cos x/x 0.1262 (Ci: no interval, the enclosure decides)", dint("cos(x)/x", 1, "sqrt(2)", **t),
         sol("0.126249"), OK, None),
        ("P(0<Z<1) 0.35 (wrong)", dint(PHI, 0, 1, **t), sol("0.35"), NO, None),
        ("∫_0^1 sin(x²) 0.32 (wrong)", dint("sin(x**2)", 0, 1, **t), sol("0.32"), NO, None),
        ("evaluate Integral(e^(-x²), (x,0,√2)) 0.86 (wrong)", ev("Integral(exp(-x**2), (x, 0, sqrt(2)))", **t),
         sol("0.86"), NO, None),
        ("evaluate Integral(sin x/x, (x,0,2π)) 1.5 (wrong)", ev("Integral(sin(x)/x, (x, 0, 2*pi))", **t), sol("1.5"),
         NO, None),
        ("∫_1^√2 cos x/x 0.1275 (Ci, wrong)", dint("cos(x)/x", 1, "sqrt(2)", **t), sol("0.127511"), NO, None),
    ]


# I: G2RK-3 / G2RK-4 ---------------------------------------------------------------------------------------------
def cases_i():
    return [
        ("(x^x)' = x^x(ln x + 1) (x > 0)", der("x**x", (XP,)), sol("x**x*(log(x) + 1)"), OK, None),
        ("(x^π)' = πx^(π-1) (x > 0)", der("x**pi", (XP,)), sol("pi*x**(pi - 1)"), OK, None),
        ("(x^√2)' (x > 0)", der("x**sqrt(2)", (XP,)), sol("sqrt(2)*x**(sqrt(2) - 1)"), OK, None),
        ("(x^e)' (x > 0)", der("x**E", (XP,)), sol("E*x**(E - 1)"), OK, None),
        ("(x^ln x)' (x > 0)", der("x**log(x)", (XP,)), sol("2*log(x)*x**log(x)/x"), OK, None),
        ("((1+1/x)^x)' (x > 0)", der("(1 + 1/x)**x", (XP,)), sol("(1 + 1/x)**x*(log(1 + 1/x) - 1/(x + 1))"), OK, None),
        ("(x^sin x)' (x > 0)", der("x**sin(x)", (XP,)), sol("x**sin(x)*(cos(x)*log(x) + sin(x)/x)"), OK, None),
        ("(x^(1/x))' (x > 0)", der("x**(1/x)", (XP,)), sol("x**(1/x)*(1 - log(x))/x**2"), OK, None),
        ("∫ x^π = x^(π+1)/(π+1) (x > 0)", anti("x**pi", (XP,)), sol("x**(pi + 1)/(pi + 1)"), OK, None),
        ("∫ x^√2 (x > 0)", anti("x**sqrt(2)", (XP,)), sol("x**(1 + sqrt(2))/(1 + sqrt(2))"), OK, None),
        ("∫ x^e (x > 0)", anti("x**E", (XP,)), sol("x**(E + 1)/(E + 1)"), OK, None),
        ("∫ x^x(ln x + 1) = x^x (x > 0)", anti("x**x*(log(x) + 1)", (XP,)), sol("x**x"), OK, None),
        ("∫ x^(1/3) = 3x^(4/3)/4 (x > 0)", anti("x**(1/3)", (XP,)), sol("3*x**(4/3)/4"), OK, None),
        ("∫ x^(1/3) = 3x cbrt x/4 (x > 0)", anti("x**(1/3)", (XP,)), sol("3*x*cbrt(x)/4"), OK, None),
        ("(x^(2/3))' = 2/(3x^(1/3)) (x > 0)", der("x**(2/3)", (XP,)), sol("2/(3*x**(1/3))"), OK, None),
        ("∫ (x+1)^(1/3) (x > -1)", anti("(x + 1)**(1/3)", ({"name": "x", "domain": "real", "constraints": ["x > -1"]},)),
         sol("3*(x + 1)**(4/3)/4"), OK, None),
        ("(x^x)' = x^x ln x (x > 0, wrong)", der("x**x", (XP,)), sol("x**x*log(x)"), NO, None),
        ("(x^π)' = πx^π (x > 0, wrong)", der("x**pi", (XP,)), sol("pi*x**pi"), NO, None),
        ("∫ x^π = x^(π+1) (x > 0, wrong)", anti("x**pi", (XP,)), sol("x**(pi + 1)"), NO, None),
        ("(x^x)' = x^x ln x (positive_real, wrong: exact points kept small)", der("x**x", (XPOS,)), sol("x**x*log(x)"), NO,
         None),
        ("((1+1/x)^x)' = (1+1/x)^x ln(1+1/x) (x > 0, wrong)", der("(1 + 1/x)**x", (XP,)),
         sol("(1 + 1/x)**x*log(1 + 1/x)"), NO, None),
        ("(x^x)' on ℝ (two readings at x < 0)", der("x**x"), sol("x**x*(log(x) + 1)"), NOTNO, None),
        ("∫ x^(1/3) = 3x^(4/3)/4 on ℝ (the convention at x < 0)", anti("x**(1/3)"), sol("3*x**(4/3)/4"), NOTOK, None),
    ]


# J: G2RK-5 ------------------------------------------------------------------------------------------------------
PW = "Piecewise((x**2, x < 1), (2*x - 1, x >= 1))"


def cases_j():
    f = dint("f(x)", 0, 2)
    f["functions"] = [{"name": "f", "expr": PW, "args": ["x"]}]
    return [
        ("∫_0^2 Piecewise = 7/3", dint(PW, 0, 2), sol("7/3"), OK, None),
        ("∫_0^2 Piecewise = 3 (wrong)", dint(PW, 0, 2), sol("3"), NO, None),
        ("∫_0^2 jump Piecewise = 3", dint("Piecewise((1, x < 1), (x + 1/2, x >= 1))", 0, 2), sol("3"), OK, None),
        ("∫_0^2 jump Piecewise = 5/2 (wrong)", dint("Piecewise((1, x < 1), (x + 1/2, x >= 1))", 0, 2), sol("5/2"), NO, None),
        ("∫_0^2 f(x), f a Piecewise = 7/3", f, sol("7/3"), NOTNO, None),
        ("∫_-1^1 Piecewise((-x, x < 0), (x, x >= 0)) = 1", dint("Piecewise((-x, x < 0), (x, x >= 0))", -1, 1), sol("1"), OK,
         None),
        ("∫_0^3 Piecewise with a gap (undefined on [1,2)) = 1", dint("Piecewise((1, x < 1), (1, x >= 2))", 0, 3), sol("2"),
         NOTOK, None),
        ("∫_0^2 Piecewise steps", dint(PW, 0, 2),
         sol("7/3", [f"Integral({PW}, (x, 0, 2)) = Integral(x**2, (x, 0, 1)) + Integral(2*x - 1, (x, 1, 2))",
                     "Integral(x**2, (x, 0, 1)) + Integral(2*x - 1, (x, 1, 2)) = 1/3 + 2", "1/3 + 2 = 7/3"]), NOTNO, NOTREF),
    ]


# L: G2RK-9 ------------------------------------------------------------------------------------------------------
def cases_l():
    return [
        ("∫_1^2 x^x(1 + ln x) = 3", dint("x**x*(1 + log(x))", 1, 2), sol("3"), OK, None),
        ("∫_1^e x^x(1 + ln x) = e^e - 1", dint("x**x*(1 + log(x))", 1, "E"), sol("exp(E) - 1"), OK, None),
        ("∫_0^1 x^x(1 + ln x) = 0", dint("x**x*(1 + log(x))", 0, 1), sol("0"), NOTNO, None),
        ("∫_1^2 x^x(1 + ln x) = 4 (wrong)", dint("x**x*(1 + log(x))", 1, 2), sol("4"), NO, None),
        ("∫_{-1}^{1} x^x (no real value on x < 0)", dint("x**x", -1, 1), sol("0"), NOTOK, None),
    ]


# K: controls ----------------------------------------------------------------------------------------------------
def cases_k():
    return [
        ("x² [0,1] = 1/3", dint("x**2", 0, 1), sol("1/3"), OK, None),
        ("|x-1| [0,3] = 5/2", dint("Abs(x - 1)", 0, 3), sol("5/2"), OK, None),
        ("sign(x) [-1,2] = 1", dint("sign(x)", -1, 2), sol("1"), OK, None),
        ("max(x,1-x) [0,1] = 3/4", dint("Max(x, 1 - x)", 0, 1), sol("3/4"), OK, None),
        ("|x²-1| [0,2] = 2", dint("Abs(x**2 - 1)", 0, 2), sol("2"), OK, None),
        ("|sin x| [0,2π] = 4", dint("Abs(sin(x))", 0, "2*pi"), sol("4"), NOTNO, None),
        ("x|x| [-1,1] = 0", dint("x*Abs(x)", -1, 1), sol("0"), OK, None),
        ("x³ + x [-2,2] = 0", dint("x**3 + x", -2, 2), sol("0"), OK, None),
        ("sin(x⁵)e^cos x + 1 [-1,1] = 2", dint("sin(x**5)*exp(cos(x)) + 1", -1, 1), sol("2"), NOTNO, None),
        ("ln x [0,1] = -1", dint("log(x)", 0, 1), sol("-1"), OK, None),
        ("1/sqrt x [0,1] = 2", dint("1/sqrt(x)", 0, 1), sol("2"), OK, None),
        ("e^-x [0,oo) = 1", dint("exp(-x)", 0, "oo"), sol("1"), OK, None),
        ("1/(1+x²) on ℝ = π", dint("1/(1 + x**2)", "-oo", "oo"), sol("pi"), OK, None),
        ("Dirichlet sin x/x [0,oo) = π/2", dint("sin(x)/x", 0, "oo"), sol("pi/2"), NOTNO, None),
        ("cbrt x [0,8] = 12", dint("cbrt(x)", 0, 8), sol("12"), OK, None),
        ("cbrt x [-8,8] = 0", dint("cbrt(x)", -8, 8), sol("0"), OK, None),
        ("x^(1/3) [0,8] = 16 (wrong)", dint("x**(1/3)", 0, 8), sol("16"), NO, None),
        ("tan [0,π/4] = ln 2 (wrong)", dint("tan(x)", 0, "pi/4"), sol("log(2)"), NO, None),
        ("1/x² [-1,1] = -2 (divergent)", dint("1/x**2", -1, 1), sol("-2"), NOTOK, None),
        ("1/x [0,1] = oo", dint("1/x", 0, 1), sol("oo"), NOTNO, None),
        ("tol π/4 0.785 rel 1e-3", dint("1/(1 + x**2)", 0, 1, rel_tol="1e-3"), sol("0.785"), OK, None),
        ("tol gauss 0.7468 rel 1e-3", dint("exp(-x**2)", 0, 1, rel_tol="1e-3"), sol("0.7468"), OK, None),
        ("tol ln 2 0.70 rel 1e-3 (wrong)", dint("1/x", 1, 2, rel_tol="1e-3"), sol("0.70"), NO, None),
        ("tol x^x [0,1] 0.7834 rel 1e-3", dint("x**x", 0, 1, rel_tol="1e-3"), sol("0.7834"), OK, None),
        ("evaluate √2 rel 1e-25 claim 1.414213562373095048801 (wrong)", ev("sqrt(2)", (), rel_tol="1e-25"),
         sol("1.414213562373095048801"), NO, None),
        ("evaluate Integral(|cos x|, (x,-1,1)) = 0 (wrong)", ev("Integral(Abs(cos(x)), (x, -1, 1))"), sol("0"), NOTOK, None),
        ("∫ 1/x = log x (wrong on ℝ)", anti("1/x"), sol("log(x)"), NOTOK, None),
        ("∫ x e^x = (x - 1)e^x", anti("x*exp(x)"), sol("(x - 1)*exp(x)"), OK, None),
        ("d/dx |x| = sign(x)", der("Abs(x)"), sol("sign(x)"), NOTNO, None),
        ("d/dx |x| at 0 = 0 (no derivative)", der("Abs(x)", at=0), sol("0"), NOTOK, None),
        ("extremum max sign((x-1)/(x+1)) on [-2,4] = 1", ir("extremum", {"f": SG, "var": "x", "which": "max",
                                                                         "interval": "[-2, 4]"}), sol("1"), NOTNO, None),
    ]


# M: G2YO-6 ------------------------------------------------------------------------------------------------------
NPR = 6 * 1000003 * 999983 * 1000033 * 999979 * 1000037 * 999961 * 1000039 * 999959


def cases_m():
    tiny = f"10**(-300)*sin({NPR}*pi*x)"
    return [
        ("simplify x² + 10^-300 sin(Nπx) = (x-1)(x+1)+1 (x > 0)", simp(f"x**2 + {tiny}", (XPOS,)),
         sol("(x - 1)*(x + 1) + 1", kind="expression"), NOTOK, None),
        ("simplify 2x + 10^-300 sin(Nπx) = (x+1)² - x² - 1 (x > 0)", simp(f"2*x + {tiny}", (XPOS,)),
         sol("(x + 1)**2 - x**2 - 1", kind="expression"), NOTOK, None),
        ("simplify x² + 10^-300 sin(Nπx) = x(x+1) - x (x > 0)", simp(f"x**2 + {tiny}", (XPOS,)),
         sol("x*(x + 1) - x", kind="expression"), NOTOK, None),
        ("d/dx (x³/3 - 10^-300 cos(Nπx)/(Nπ)) = (x-1)(x+1)+1 (x > 0)",
         der(f"x**3/3 - 10**(-300)*cos({NPR}*pi*x)/({NPR}*pi)", (XPOS,)), sol("(x - 1)*(x + 1) + 1"), NOTOK, None),
        ("simplify x² + 10^-300 sin(Nπx) = x² (control)", simp(f"x**2 + {tiny}", (XPOS,)), sol("x**2", kind="expression"),
         NO, None),
        ("simplify (x+1)² - x² - 1 = 2x (control: true)", simp("(x + 1)**2 - x**2 - 1", (XPOS,)), sol("2*x", kind="expression"),
         OK, None),
        ("simplify sin(atan x) = x/sqrt(1+x²) (control: true)", simp("sin(atan(x))"), sol("x/sqrt(1 + x**2)", kind="expression"),
         OK, None),
        ("simplify cos(2 atan x) = (1-x²)/(1+x²) (control: true)", simp("cos(2*atan(x))"),
         sol("(1 - x**2)/(1 + x**2)", kind="expression"), OK, None),
        ("simplify atan x - atan(x/2) = atan(x/(x²+2)) (control: true)", simp("atan(x) - atan(x/2)"),
         sol("atan(x/(x**2 + 2))", kind="expression"), OK, None),
        ("simplify asin(tanh x) = atan(sinh x) on x > 0 (control: true)", simp("asin(tanh(x))", (XPOS,)),
         sol("atan(sinh(x))", kind="expression"), OK, None),
        ("simplify tan(x/2) = sin x/(1 + cos x) (control: true)", simp("sin(x)/(1 + cos(x))"),
         sol("tan(x/2)", kind="expression"), OK, None),
        ("residual (record): a 10^-300 term behind exp = cosh + sinh in the claim, which no expansion exposes",
         simp(f"x**2 + {tiny}", (XPOS,)), sol("x**2 + 10**(-300)*(exp(x) - cosh(x) - sinh(x))", kind="expression"), ANY,
         None),
    ]


# N: second round (independent audit of the branch, 21 Oct 2026) --------------------------------------------------------
def cases_n():
    out = []
    # SI-YO-2: a planted finite value of a divergent integral meets a half-infinite enclosure and the real ladder
    for f, a, b, v in [("1/x", 0, 1, "10**6"), ("1/(x*Abs(log(x)))", 0, "1/2", "10"), ("-1/x", 0, 1, "-10**6"),
                       ("1/(1 - x)", "1/2", 1, "100")]:
        out.append((f"SI-YO-2 planted {v} for the divergent ∫_{a}^{b} {f}, numbers", planted(dint(f, a, b), sol(v), v,
                                                                                            numbers=True), None, NOTOK, None))
    # SI-YO-3: a planted 0 for a divergent integral whose principal value is 0; mpmath's failed 0.0 (error 2.0)
    for f, a, b in [("1/x", -1, 1), ("1/x**3", -1, 1), ("x/(x**2 - 1)", -2, 2), ("sign(x)/Abs(x)**(3/2)", -1, 1)]:
        out.append((f"SI-YO-3 planted 0 for the divergent ∫_{a}^{b} {f}, numbers", planted(dint(f, a, b), sol("0"), "0",
                                                                                           numbers=True), None, NOTOK, None))
    # true values of strong integrable singularities: an interior one next to the last rung, a power at an end a weight
    for f, a, b, v in [("1/cbrt((x - 1)**2)", 0, 2, "6"), ("Abs(x - 1)**(-9/10)", 0, 2, "20"),
                       ("Abs(x)**(-9/10)", -1, 2, "10*(2**(1/10) + 1)"), ("x**(-99/100)", 0, 1, "100"),
                       ("(1 - x)**(-19/20)", 0, 1, "20"), ("x**(-9/10)", 0, 1, "10"), ("Abs(x - 1)**(-4/5)", 0, 2, "10")]:
        out.append((f"SI-YO-2 true ∫_{a}^{b} {f} = {v}", dint(f, a, b), sol(v), OK, None))
    out.append(("SI-YO-2 ∫_0^1 x^(-99/100) = 101 (wrong)", dint("x**(-99/100)", 0, 1), sol("101"), NO, None))
    out.append(("SI-YO-2 residual (record): ∫_{-1}^{2} |x|^(-19/20) = 20(1 + 2^(1/20)), an interior singularity whose "
                "last rung's estimate is 5e-6 of the value", dint("Abs(x)**(-19/20)", -1, 2), sol("20*(1 + 2**(1/20))"),
                NOTNO, None))
    # SON-INT-RK-1: a complex claim within a declared tolerance
    for e, tol, c, v in [("exp(I*pi/3)", {"abs_tol": "0.001"}, "0.5 + 0.866*I", OK),
                         ("2*exp(I*pi/4)", {"abs_tol": "0.01"}, "1.41 + 1.41*I", OK),
                         ("exp(I)", {"abs_tol": "0.0001"}, "0.5403 + 0.8415*I", OK),
                         ("exp(I)", {"abs_tol": "0.0001", "rel_tol": "0.0001"}, "0.5403 + 0.8415*I", OK),
                         ("exp(I)", {"rel_tol": "0.0001"}, "0.5403 + 0.8415*I", OK),
                         ("exp(I*pi/3)", {"abs_tol": "0.001"}, "0.5 + 0.87*I", NO),
                         ("exp(I*pi/3)", {"abs_tol": "0.001"}, "0.502 + 0.866*I", NO),
                         ("exp(I)", {"rel_tol": "0.0001"}, "0.5403 + 0.8515*I", NO),
                         ("sqrt(3) + I", {"abs_tol": "0.01"}, "1.73 + I", OK),
                         # a nonreal claim for a real value within the tolerance: undecided (d4c SG-1)
                         ("E", {"abs_tol": "0.001"}, "2.71828 + I/10**9", UNK),
                         ("E", {"rel_tol": "0.001"}, "2.71828 + I/10**9", UNK),
                         ("E", {"abs_tol": "0.001"}, "2.71828 + I/10**2", NO)]:
        out.append((f"SON-INT-RK-1 {e} ≈ {c} {tol}", ev(e, (), **tol), sol(c), v, None))
    # SON-INT-RK-2: fast oscillations whose ladder does not converge (the time is in the row)
    for f, a, b, v in [("cos(500*pi*x)**2", 0, 1, "1/2"), ("cos(1000*pi*x)**2", 0, 1, "1/2"),
                       ("sin(2000*x)**2", 0, "pi", "pi/2"), ("x**3*cos(2000*x)", 0, "2*pi", "3*pi**2/1000000"),
                       ("sin(300*x)**4", 0, "pi", "3*pi/8"), ("cos(x)*exp(200*sin(x))", 0, "pi", "0"),
                       ("1/(x**2 + 10**(-8))", -1, 1, "20000*atan(10000)"),
                       ("exp(-x)*sin(2000*x)**2", 0, 1,
                        "(-8000001 + cos(2000)**2 - 2000*sin(4000) + 8000000*E)*exp(-1)/16000001")]:
        out.append((f"SON-INT-RK-2 ∫_{a}^{b} {f} = {v}", dint(f, a, b), sol(v), OK, None))
    return out


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g,
          "H": cases_h, "I": cases_i, "J": cases_j, "L": cases_l, "M": cases_m, "N": cases_n, "K": cases_k}


CASE_LIMIT = 300            # seconds per case: the old code held (x^x)' = x^x·ln x for over twenty minutes


class CaseTimeout(BaseException):
    pass


def _alarm(signum, frame):
    raise CaseTimeout(f"over {CASE_LIMIT} s")


def main(out_path=None, groups="ABCDEFGHIJLMNK"):
    import os
    import signal
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    signal.signal(signal.SIGALRM, _alarm)
    rows = []
    bad = 0
    t0 = time.time()
    for g in groups:
        for case in GROUPS[g]():
            label, q, s, verdicts, statuses = case[:5]
            absent = case[5] if len(case) > 5 else None          # a flag that must not be raised
            t = time.time()
            status, flags, allflags = None, [], set()
            signal.alarm(CASE_LIMIT)
            try:
                if callable(q):
                    verdict = q()
                else:
                    r = verify(q, s)
                    verdict = r.verdict
                    layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                    steps = layer.evidence.get("steps", []) if layer is not None else []
                    status = steps[-1].get("status") if steps else None
                    allflags = {f for la in r.layers for f in (la.flags or [])} | set(r.flags)
                    flags = sorted(allflags)[:6]
            except (Exception, CaseTimeout) as e:  # noqa: BLE001
                if isinstance(e, CaseTimeout):
                    from mathverify.sandbox import get_sandbox
                    get_sandbox().close()
                verdict = f"EXC {type(e).__name__}: {e}"
            finally:
                signal.alarm(0)
            ok = verdict in verdicts and (statuses is None or status in statuses)
            ok = ok and (absent is None or absent not in allflags)
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": verdict, "status": status, "ok": ok, "flags": flags,
                         "s": round(time.time() - t, 2)})
            print(f"{'ok ' if ok else 'BAD'} {g} {verdict:9} {str(status):9} {time.time() - t:5.1f}s {label}  {flags}",
                  flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else None
    grp = args[1] if len(args) > 1 else "ABCDEFGHIJLMNK"
    sys.exit(1 if main(out, grp) else 0)
