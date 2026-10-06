"""Part d4c of the fourth audit's fixes (1 Oct 2026): numeric evidence and the exact zero (findings S1-S6 of
the `sifir` angle and D4-ADIM-C of the `adim` angle, `denetim/2026-10-01/d4/`).

    A  S1  a zero claim with no symbolic certificate: 2π·I_50(1) = 1.8e-79 and SymPy's wrong 0 for
           ∫_{-1}^{1} (x + |cos x|/10^80) dx are not certified 0; the true small value is not refuted
    B  S2  no exact value from SymPy: a quadrature alone never accepts (narrow peak missed at every level)
    C  S3, D4-ADIM-C  infinite-range integrals: evalf's '-0.e+0' / '1.6' (no significant digits) is no value,
           so true Dirichlet/Fresnel/Laplace steps are not refuted and their solutions not INCORRECT
    D  S4  long sums: verify returns within 60 s (sandboxed, time-limited evaluation)
    E  S5  a zero with no significant bits ('0.e-168') is no proof of equality
    F  S6  an odd, absolutely integrable integrand with an interior singularity: the 0 is certified
    G  controls whose verdict must not change (N2 zero integrals, refutations, identities, exact values)
    H  review of d4c: narrow peaks both quadratures miss, infinite ranges, declared tolerances; decided
       only by a rigorous (interval) enclosure, and wrong values outside it still refuted
    I  sibling paths (6 Oct 2026): nsum's value alone refuted a series (a term far out never seen); SymPy's
       value confirmed by nsum still decides

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \
        .venv/bin/python denetim/2026-10-01/d4c/sonda.py [out.json] [groups]

Measured on 158c220 (src = 1df0558) and after the fix: see the report of part d4c. Kept out of pyflakes and
pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import signal
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTOK = {"INCORRECT", "UNKNOWN"}      # anything but a false acceptance
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
UNK = {"UNKNOWN"}
ANY = {"CORRECT", "INCORRECT", "UNKNOWN"}
VER = {"verified"}
REF = {"refuted"}
NOTREF = {"verified", "unknown", "skipped"}
NOTVER = {"refuted", "unknown", "skipped"}

X = {"name": "x", "domain": "real"}
K = {"name": "k", "domain": "positive_integer"}
N = {"name": "n", "domain": "positive_integer"}
A_HALF = {"name": "a", "domain": "real", "constraints": ["a > -1/2", "a < 1/2"]}
X_10_20 = {"name": "x", "domain": "real", "constraints": ["x > 10", "x < 20"]}
X_POS = {"name": "x", "domain": "real", "constraints": ["x > 0"]}
X_11 = {"name": "x", "domain": "real", "constraints": ["x > -1", "x < 1"]}


def _task(kind, params, vars_, givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def dint(f, a, b):
    return _task("definite_integral", {"integrand": f, "var": "x", "a": str(a), "b": str(b)}, [X])


def ev(e, vars_=(X,)):
    return _task("evaluate", {"expr": e}, vars_)


def simp(e, vars_):
    return _task("simplify_expression", {"expr": e}, vars_, shape="expression")


def _sol(payload, steps=(), kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def cp(c):
    return [("compute", c)]


def eqs(c):
    return [("eq", c)]


X1 = _task("evaluate", {"expr": "x + 1"}, [X], ["x = 1"])          # the answer 2, a step about a closed form
ABSCOS = "Integral(x + Abs(cos(x))/10**80, (x, -1, 1))"            # SymPy: 0; true 2 sin(1)/10^80
PEAK = "exp(-10**8*(x - 1/3)**2)"


# (label, ir, solution, expected verdicts, expected status of the LAST step: set or None)
def cases_a():
    return [
        ("e^cos x cos50x [0,2pi] claim 0 (2pi I50(1) = 1.8e-79)", dint("exp(cos(x))*cos(50*x)", 0, "2*pi"), _sol("0"), NOTOK, None),
        ("e^cos x cos50x [0,pi] claim 0", dint("exp(cos(x))*cos(50*x)", 0, "pi"), _sol("0"), NOTOK, None),
        ("e^cos x cos55x [0,2pi] claim 0", dint("exp(cos(x))*cos(55*x)", 0, "2*pi"), _sol("0"), NOTOK, None),
        ("e^cos x cos60x [0,2pi] claim 0", dint("exp(cos(x))*cos(60*x)", 0, "2*pi"), _sol("0"), NOTOK, None),
        ("e^sin x cos60x [0,2pi] claim 0", dint("exp(sin(x))*cos(60*x)", 0, "2*pi"), _sol("0"), NOTOK, None),
        ("cos(cos x) cos60x [0,2pi] claim 0", dint("cos(cos(x))*cos(60*x)", 0, "2*pi"), _sol("0"), NOTOK, None),
        ("e^cos x cos50x [0,2pi] claim '0.0'", dint("exp(cos(x))*cos(50*x)", 0, "2*pi"), _sol("0.0"), NOTOK, None),
        ("sin(x^5)e^cos x + 10^-80 [-1,1] claim 0", dint("sin(x**5)*exp(cos(x)) + 10**(-80)", -1, 1), _sol("0"), NOTOK, None),
        ("sin(x^5)e^cos x + 10^-75 [-1,1] claim 0", dint("sin(x**5)*exp(cos(x)) + 10**(-75)", -1, 1), _sol("0"), NOTOK, None),
        ("evaluate |cos| form claim 0 (SymPy's wrong 0)", ev(ABSCOS), _sol("0"), NOTOK, None),
        ("evaluate sin x + |cos|*10^-75 form claim 0", ev("Integral(sin(x) + Abs(cos(x))*10**(-75), (x, -1, 1))"), _sol("0"), NOTOK, None),
        ("definite_integral x + |cos|/10^80 claim 0", dint("x + Abs(cos(x))/10**80", -1, 1), _sol("0"), NOTOK, None),
        ("step '|cos| form = 0' not verified", X1, _sol("2", cp(f"{ABSCOS} = 0")), ANY, NOTVER),
        ("step '|cos| form = 2 sin(1)/10^80' not refuted", X1, _sol("2", cp(f"{ABSCOS} = 2*sin(1)/10**80")), NOTNO, NOTREF),
        ("definite_integral true value 2 sin(1)/10^80 not refuted", dint("x + Abs(cos(x))/10**80", -1, 1), _sol("2*sin(1)/10**80"), NOTNO, None),
        ("step 'e^cos cos50x form = 0' not verified", X1, _sol("2", cp("Integral(exp(cos(x))*cos(50*x), (x, 0, 2*pi)) = 0")), NOTNO, NOTVER),
    ]


def cases_b():
    return [
        ("1 + peak*e^cos [0,1] claim 1 (true 1.000456)", dint(f"1 + {PEAK}*exp(cos(x))", 0, 1), _sol("1"), NOTOK, None),
        ("odd + peak [-1,1] claim 0 (true 1.77e-4)", dint(f"sin(x**5)*exp(cos(x)) + {PEAK}", -1, 1), _sol("0"), NOTOK, None),
        ("odd + 10^8 peak^2 [-1,1] claim 0", dint("sin(x**5)*exp(cos(x)) + 10**8*exp(-10**16*(x - 1/3)**2)", -1, 1), _sol("0"), NOTOK, None),
        ("peak*e^cos + sin(x^3) [-1,1] claim 0", dint(f"{PEAK}*exp(cos(x)) + sin(x**3)", -1, 1), _sol("0"), NOTOK, None),
        ("1 + odd + peak [-1,1] claim 2", dint(f"1 + sin(x**5)*exp(cos(x)) + {PEAK}", -1, 1), _sol("2"), NOTOK, None),
        ("odd + 1 [-1,1] claim 2 + 10^-40 (true 2)", dint("sin(x**5)*exp(cos(x)) + 1", -1, 1), _sol("2 + 10**(-40)"), NOTOK, None),
        ("odd + 1 [-1,1] claim 2 (true, no exact value from SymPy)", dint("sin(x**5)*exp(cos(x)) + 1", -1, 1), _sol("2"), NOTNO, None),
    ]


def cases_c():
    L = [("Dirichlet sin x/x = pi/2", "Integral(sin(x)/x, (x, 0, oo)) = pi/2"),
         ("Dirichlet on R = pi", "Integral(sin(x)/x, (x, -oo, oo)) = pi"),
         ("2*Dirichlet = pi", "2*Integral(sin(x)/x, (x, 0, oo)) = pi"),
         ("sin^3 x/x = pi/4", "Integral(sin(x)**3/x, (x, 0, oo)) = pi/4"),
         ("Fresnel sin x^2 = sqrt(2pi)/4", "Integral(sin(x**2), (x, 0, oo)) = sqrt(2*pi)/4"),
         ("Fresnel cos x^2 = sqrt(2pi)/4", "Integral(cos(x**2), (x, 0, oo)) = sqrt(2*pi)/4"),
         ("Laplace cos x/(1+x^2) = pi/(2e)", "Integral(cos(x)/(1 + x**2), (x, 0, oo)) = pi/(2*E)"),
         ("sin^2 x/x^2 = pi/2", "Integral(sin(x)**2/x**2, (x, 0, oo)) = pi/2"),
         ("sin x sin 3x/x^2 = pi/2", "Integral(sin(x)*sin(3*x)/x**2, (x, 0, oo)) = pi/2"),
         ("cos x/sqrt x = sqrt(pi/2)", "Integral(cos(x)/sqrt(x), (x, 0, oo)) = sqrt(pi/2)"),
         ("e^(-x/100) cos x = 100/10001", "Integral(exp(-x/100)*cos(x), (x, 0, oo)) = 100/10001"),
         ("Dirichlet + int_0^1 x = pi/2 + 1/2", "Integral(sin(x)/x, (x, 0, oo)) + Integral(x, (x, 0, 1)) = pi/2 + 1/2"),
         ("1/x on [1,oo) = oo (divergence convention)", "Integral(1/x, (x, 1, oo)) = oo")]
    out = []
    for label, c in L:
        out.append((f"compute {label}", X1, _sol("2", cp(c)), NOTNO, NOTREF))
        out.append((f"eq {label}", X1, _sol("2", eqs(c)), NOTNO, NOTREF))
    dirichlet = ev("Integral(sin(x)/x, (x, 0, oo))")
    out += [
        ("evaluate Dirichlet, pi/2 + true step", dirichlet, _sol("pi/2", cp("Integral(sin(x)/x, (x, 0, oo)) = pi/2")), NOTNO, NOTREF),
        ("evaluate Dirichlet, pi/2", dirichlet, _sol("pi/2"), NOTNO, None),
        ("evaluate sin^2/x^2, pi/2 + eq step", ev("Integral(sin(x)**2/x**2, (x, 0, oo))"),
         _sol("pi/2", eqs("Integral(sin(x)**2/x**2, (x, 0, oo)) = pi/2")), NOTNO, NOTREF),
        ("definite_integral sin^3 x/x claim pi/4 + true step", dint("sin(x)**3/x", 0, "oo"),
         _sol("pi/4", cp("Integral(sin(x)**3/x, (x, 0, oo)) = pi/4")), NOTNO, NOTREF),
        ("definite_integral Dirichlet claim pi/2", dint("sin(x)/x", 0, "oo"), _sol("pi/2"), NOTNO, None),
        ("step 'Dirichlet = 0' (wrong) not verified", X1, _sol("2", cp("Integral(sin(x)/x, (x, 0, oo)) = 0")), NOTNO, NOTVER),
        ("evaluate Dirichlet claim 0 (wrong)", dirichlet, _sol("0"), NOTOK, None),
    ]
    return out


def cases_d():
    return [
        ("Sum x^k/k! 0..3000 -> exp(x)", simp("Sum(x**k/factorial(k), (k, 0, 3000))", [X, K]), _sol("exp(x)", kind="expression"), NOTOK, None),
        ("Sum x^k/k! 0..2001 -> exp(x)", simp("Sum(x**k/factorial(k), (k, 0, 2001))", [X, K]), _sol("exp(x)", kind="expression"), NOTOK, None),
        ("Sum x^k/k! 0..100000 -> exp(x)", simp("Sum(x**k/factorial(k), (k, 0, 100000))", [X, K]), _sol("exp(x)", kind="expression"), NOTOK, None),
        ("Sum a^k 0..10^7 -> 1/(1-a)", simp("Sum(a**k, (k, 0, 10**7))", [A_HALF, K]), _sol("1/(1 - a)", kind="expression"), NOTOK, None),
        ("Sum x^2k/(2k)! 0..2500 -> cosh(x)", simp("Sum(x**(2*k)/factorial(2*k), (k, 0, 2500))", [X, K]), _sol("cosh(x)", kind="expression"), NOTOK, None),
        ("step Sum x^k/k! 0..3000 = exp(x)", _task("evaluate", {"expr": "x + 1"}, [X, K], ["x = 1"]),
         _sol("2", cp("Sum(x**k/factorial(k), (k, 0, 3000)) = exp(x)")), NOTNO, NOTVER),
    ]


def cases_e():
    S = lambda e, v: simp(e, v)  # noqa: E731
    return [
        ("Sum a^k 0..5000 -> 1/(1-a)", S("Sum(a**k, (k, 0, 5000))", [A_HALF, K]), _sol("1/(1 - a)", kind="expression"), NOTOK, None),
        ("Sum k a^k 0..2500 -> a/(1-a)^2", S("Sum(k*a**k, (k, 0, 2500))", [A_HALF, K]), _sol("a/(1 - a)**2", kind="expression"), NOTOK, None),
        ("Sum a^k 1..2001 -> a/(1-a)", S("Sum(a**k, (k, 1, 2001))", [A_HALF, K]), _sol("a/(1 - a)", kind="expression"), NOTOK, None),
        ("Sum a^2k 0..2001 -> 1/(1-a^2)", S("Sum(a**(2*k), (k, 0, 2001))", [A_HALF, K]), _sol("1/(1 - a**2)", kind="expression"), NOTOK, None),
        ("Sum a^k 0..5000 -> 1/(1-a) + a^6000", S("Sum(a**k, (k, 0, 5000))", [A_HALF, K]), _sol("1/(1 - a) + a**6000", kind="expression"), NOTOK, None),
        ("evaluate Sum a^k 0..5000 -> 1/(1-a)", _task("evaluate", {"expr": "Sum(a**k, (k, 0, 5000))"}, [A_HALF, K], shape="expression"),
         _sol("1/(1 - a)", kind="expression"), NOTOK, None),
        ("tanh(100x) -> 1 on (10,20)", S("tanh(100*x)", [X_10_20]), _sol("1", kind="expression"), NOTOK, None),
        ("x tanh(100x) -> x on (10,20)", S("x*tanh(100*x)", [X_10_20]), _sol("x", kind="expression"), NOTOK, None),
        ("sqrt(1 + x^2/10^600) -> 1 on (10,20)", S("sqrt(1 + x**2/10**600)", [X_10_20]), _sol("1", kind="expression"), NOTOK, None),
        ("cos(x/10^300) -> 1 on (10,20)", S("cos(x/10**300)", [X_10_20]), _sol("1", kind="expression"), NOTOK, None),
        ("exp(x/10^600) -> 1 on (10,20)", S("exp(x/10**600)", [X_10_20]), _sol("1", kind="expression"), NOTOK, None),
        ("atan(10^600 x) -> pi/2 on (10,20)", S("atan(10**600*x)", [X_10_20]), _sol("pi/2", kind="expression"), NOTOK, None),
        ("log(1 + x/10^600) -> 0 on (10,20)", S("log(1 + x/10**600)", [X_10_20]), _sol("0", kind="expression"), NOTOK, None),
        ("1/(1 - e^-1000x) -> 1 on (10,20)", S("1/(1 - exp(-1000*x))", [X_10_20]), _sol("1", kind="expression"), NOTOK, None),
        ("sqrt(x^2 + e^-1000) -> x on (10,20)", S("sqrt(x**2 + exp(-1000))", [X_10_20]), _sol("x", kind="expression"), NOTOK, None),
        ("evaluate tanh(100x) -> 1 on (10,20)", _task("evaluate", {"expr": "tanh(100*x)"}, [X_10_20], shape="expression"),
         _sol("1", kind="expression"), NOTOK, None),
        ("d/dx tanh(100x) -> 0 on (10,20)", _task("derivative", {"f": "tanh(100*x)", "var": "x"}, [X_10_20], shape="expression"),
         _sol("0", kind="expression"), NOTOK, None),
        ("step 'tanh(100*x) = 1' not verified", _task("evaluate", {"expr": "x + 1"}, [X_10_20], shape="expression"),
         _sol("x + 1", cp("tanh(100*x) = 1"), kind="expression"), NOTOK | OK, NOTVER),
        ("step 'Sum(a**k,(k,0,5000)) = 1/(1-a)' not verified", _task("evaluate", {"expr": "a + 1"}, [A_HALF, K], shape="expression"),
         _sol("a + 1", cp("Sum(a**k, (k, 0, 5000)) = 1/(1 - a)"), kind="expression"), NOTOK | OK, NOTVER),
    ]


def cases_f():
    return [
        ("sign(x)/sqrt|x| [-1,1] claim 0", dint("sign(x)/sqrt(Abs(x))", -1, 1), _sol("0"), OK, None),
        ("sign(x)|x|^(-2/3) [-1,1] claim 0", dint("sign(x)*Abs(x)**(-2/3)", -1, 1), _sol("0"), OK, None),
        ("sign(x)|x|^(-3/4) [-2,2] claim 0", dint("sign(x)*Abs(x)**(-3/4)", -2, 2), _sol("0"), OK, None),
        ("x/|x|^(3/2) [-1,1] claim 0", dint("x/Abs(x)**(3/2)", -1, 1), _sol("0"), OK, None),
        ("evaluate Integral(sign(x)/sqrt|x|) claim 0", ev("Integral(sign(x)/sqrt(Abs(x)), (x, -1, 1))"), _sol("0"), OK, None),
        ("step 'Integral(sign(x)/sqrt|x|) = 0' verified", X1, _sol("2", cp("Integral(sign(x)/sqrt(Abs(x)), (x, -1, 1)) = 0")), OK, VER),
        ("sign(x)/sqrt|x| [-1,1] claim 1 (wrong)", dint("sign(x)/sqrt(Abs(x))", -1, 1), _sol("1"), NO, None),
        ("sign(x)|x|^(-1/3) [-1,1] claim 0 (control)", dint("sign(x)*Abs(x)**(-1/3)", -1, 1), _sol("0"), OK, None),
        ("1/sqrt|x| [-1,1] claim 4 (control)", dint("1/sqrt(Abs(x))", -1, 1), _sol("4"), OK, None),
        ("1/x [-1,1] claim 0 (divergent, PV only)", dint("1/x", -1, 1), _sol("0"), NOTOK, None),
        ("x/|x|^2 [-1,1] claim 0 (divergent)", dint("x/Abs(x)**2", -1, 1), _sol("0"), NOTOK, None),
        ("x e^(1/x^2) [-1,1] claim 0 (divergent; SymPy says 0)", dint("x*exp(x**(-2))", -1, 1), _sol("0"), NOTOK, None),
        ("1/x^3 [-1,1] claim 0 (divergent)", dint("1/x**3", -1, 1), _sol("0"), NOTOK, None),
        ("sin(x^5) e^cos x [-1,1] claim 0 (odd, no closed form)", dint("sin(x**5)*exp(cos(x))", -1, 1), _sol("0"), OK, None),
        ("x/(1+x^2) on R claim 0 (divergent; PV 0)", dint("x/(1 + x**2)", "-oo", "oo"), _sol("0"), NOTOK, None),
        ("x e^(-x^2) on R claim 0 (odd, integrable)", dint("x*exp(-x**2)", "-oo", "oo"), _sol("0"), NOTNO, None),
    ]


def cases_g():
    return [
        ("N2: int_0^3 (x^2-2x) claim 0", dint("x**2 - 2*x", 0, 3), _sol("0"), OK, None),
        ("N2: int_0^3 (x^2-2x) claim 1", dint("x**2 - 2*x", 0, 3), _sol("1"), NO, None),
        ("N2: int_0^3 (x^2-2x) claim 10^-30", dint("x**2 - 2*x", 0, 3), _sol("10**(-30)"), NO, None),
        ("N2: eq Integral(x^2-2x,(x,0,3)) = 0", ev("integrate(x**2 - 2*x, (x, 0, 3))"),
         _sol("0", eqs("Integral(x**2 - 2*x, (x, 0, 3)) = 0")), OK, VER),
        ("N2: 10^20 sin x [0,2pi] claim 0", dint("10**20*sin(x)", 0, "2*pi"), _sol("0"), OK, None),
        ("sin(sin x) [0,2pi] claim 0 (no closed form, odd about pi)", dint("sin(sin(x))", 0, "2*pi"), _sol("0"), OK, None),
        ("sin(sin x) [0,2pi] claim 1/10", dint("sin(sin(x))", 0, "2*pi"), _sol("1/10"), NO, None),
        ("step sin(sin x) form = 10^-30 refuted", ev("integrate(sin(x), (x, 0, 2*pi))"),
         _sol("0", eqs("Integral(sin(sin(x)), (x, 0, 2*pi)) = 10**(-30)")), NO, REF),
        ("step |cos| form = 0 [-1,1] refuted (numbers)", ev("integrate(sin(x), (x, 0, 2*pi))"),
         _sol("0", eqs("Integral(Abs(cos(x)), (x, -1, 1)) = 0")), NO, REF),
        ("10^-40 on [0,1] claim 0", dint("10**(-40)", 0, 1), _sol("0"), NO, None),
        ("step int 10^-40 = 0 refuted", ev("integrate(10**(-40), (x, 0, 1))"),
         _sol("10**(-40)", eqs("integrate(10**(-40), (x, 0, 1)) = 0")), NO, REF),
        ("sin x [0,2pi] claim 10^-40", dint("sin(x)", 0, "2*pi"), _sol("10**(-40)"), NO, None),
        ("sin x [0,2pi] claim 0", dint("sin(x)", 0, "2*pi"), _sol("0"), OK, None),
        ("log x + 1 [0,1] claim 0", dint("log(x) + 1", 0, 1), _sol("0"), OK, None),
        ("|x| - 1/2 [-1,1] claim 0", dint("Abs(x) - 1/2", -1, 1), _sol("0"), OK, None),
        ("x^2 [0,1] claim 1/3", dint("x**2", 0, 1), _sol("1/3"), OK, None),
        ("x^2 [0,1] claim 1/2", dint("x**2", 0, 1), _sol("1/2"), NO, None),
        ("e^x [0, pi sqrt163] claim the nearby integer", dint("exp(x)", 0, "pi*sqrt(163)"), _sol("262537412640768743"), NO, None),
        ("log x/sqrt x [0,1] claim -4", dint("log(x)/sqrt(x)", 0, 1), _sol("-4"), OK, None),
        ("e^-x [0,oo) claim 1 (no numeric value on an infinite range)", dint("exp(-x)", 0, "oo"), _sol("1"), NOTNO, None),
        ("step int_0^oo e^-x = 1 verified", X1, _sol("2", cp("Integral(exp(-x), (x, 0, oo)) = 1")), OK, VER),
        ("step int_0^oo e^-x = 2 refuted", X1, _sol("2", cp("Integral(exp(-x), (x, 0, oo)) = 2")), NO, REF),
        ("step Gauss = sqrt(pi) verified", X1, _sol("2", cp("Integral(exp(-x**2), (x, -oo, oo)) = sqrt(pi)")), OK, VER),
        ("Sum(k,1,1000n) wrong -> INCORRECT", simp("Sum(k, (k, 1, 1000*n))", [N, K]), _sol("500*n*(1000*n - 1)", kind="expression"), NO, None),
        ("Sum(k,1,1000n) right", simp("Sum(k, (k, 1, 1000*n))", [N, K]), _sol("500*n*(1000*n + 1)", kind="expression"), NOTNO, None),
        ("Sum a^k 0..5000 -> 1/(1-a), a free (counterexample)", simp("Sum(a**k, (k, 0, 5000))", [{"name": "a", "domain": "real"}, K]),
         _sol("1/(1 - a)", kind="expression"), NO, None),
        ("tanh(100x) -> 1, x free (counterexample)", simp("tanh(100*x)", [X]), _sol("1", kind="expression"), NO, None),
        ("sin^2 x + cos^2 x -> 1", simp("sin(x)**2 + cos(x)**2", [X]), _sol("1", kind="expression"), OK, None),
        ("1/(x-1) + e^-1000 -> 1/(x-1) (gap 1e-435)", simp("1/(x - 1) + exp(-1000)", [X]), _sol("1/(x - 1)", kind="expression"), NO, None),
        ("Sum cos(k pi/2), k=1..4n -> 0", simp("Sum(cos(k*pi/2), (k, 1, 4*n))", [N, K]), _sol("0", kind="expression"), NOTNO, None),
        # identities that only random points decided: evalf's zero is no proof now, an exact one is
        ("atan(x) + atan(1/x) -> pi/2 (x > 0)", simp("atan(x) + atan(1/x)", [X_POS]), _sol("pi/2", kind="expression"), OK, None),
        ("asin(x) + acos(x) -> pi/2 on (-1,1)", simp("asin(x) + acos(x)", [X_11]), _sol("pi/2", kind="expression"), OK, None),
        ("atan(2x/(1-x^2)) -> 2 atan(x) on (-1,1)", simp("atan(2*x/(1 - x**2))", [X_11]), _sol("2*atan(x)", kind="expression"), OK, None),
        ("atan(x) - atan(x/2) -> atan(x/(2+x^2))", simp("atan(x) - atan(x/2)", [X]), _sol("atan(x/(2 + x**2))", kind="expression"), OK, None),
        ("tanh(x) -> (e^2x - 1)/(e^2x + 1)", simp("tanh(x)", [X]), _sol("(exp(2*x) - 1)/(exp(2*x) + 1)", kind="expression"), OK, None),
        ("tan(x/2) -> sin x/(1 + cos x) on (-1,1)", simp("tan(x/2)", [X_11]), _sol("sin(x)/(1 + cos(x))", kind="expression"), OK, None),
        ("atan(e^x) + atan(e^-x) -> pi/2 (Gudermann)", simp("atan(exp(x)) + atan(exp(-x))", [X_POS]), _sol("pi/2", kind="expression"), OK, None),
        ("asin(tanh x) -> atan(sinh x) (Gudermann)", simp("asin(tanh(x))", [X_POS]), _sol("atan(sinh(x))", kind="expression"), OK, None),
        ("2 atan(tanh(x/2)) -> atan(sinh x) (Gudermann)", simp("2*atan(tanh(x/2))", [X_POS]), _sol("atan(sinh(x))", kind="expression"), OK, None),
        ("asin(tanh x) -> atan(sinh x) + 1/10^30 (wrong)", simp("asin(tanh(x))", [X_POS]), _sol("atan(sinh(x)) + 1/10**30", kind="expression"), NO, None),
        ("atan(x) + atan(1/x) -> pi/2, x free (counterexample)", simp("atan(x) + atan(1/x)", [X]), _sol("pi/2", kind="expression"), NO, None),
        ("odd + 1 [-1,1] claim 2 (even part 1)", dint("sin(x**5)*exp(cos(x)) + 1", -1, 1), _sol("2"), OK, None),
        ("odd + 1 [-1,1] claim 3", dint("sin(x**5)*exp(cos(x)) + 1", -1, 1), _sol("3"), NO, None),
        ("sign(x)|x|^(-2/3) e^cos x [-1,1] claim 0 (no antiderivative)", dint("sign(x)*Abs(x)**(-2/3)*exp(cos(x))", -1, 1), _sol("0"), OK, None),
        ("log x/sqrt x [0,1] step = -4 (manual antiderivative)", X1, _sol("2", eqs("Integral(log(x)/sqrt(x), (x, 0, 1)) = -4")), OK, VER),
    ]


P8 = "exp(-10**8*(x - 1/3)**2)"
PK = f"x**2 + {P8}"
PK_T = "1/3 + sqrt(pi)*(erf(20000/3) + erf(10000/3))/20000"
PK2 = "2 + sin(x) + exp(-10**9*(x - pi/4)**2)"
PK2_T = "3 - cos(1) + sqrt(pi)*(erf(sqrt(10**9)*(1 - pi/4)) + erf(sqrt(10**9)*pi/4))/(2*sqrt(10**9))"
SE = "x**2 + 10**4/cosh(10**4*(x - 1/3))**2"
SE_T = "1/3 + tanh(20000/3) + tanh(10000/3)"
SE2 = "sin(x) + 2 + 1/cosh(10**6*(x - sqrt(2)/2))**2"
SE2_T = "3 - cos(1) + (tanh(10**6*(1 - sqrt(2)/2)) + tanh(10**6*sqrt(2)/2))/10**6"
SE3 = "x**2 + cos(x)*exp(sin(x))*tanh(10**4*(x - 1/3)) + 10**4*exp(sin(x))/cosh(10**4*(x - 1/3))**2"
SE3_T = "1/3 + exp(sin(1))*tanh(20000/3) + tanh(10000/3)"


def dtol(f, a, b, tol):
    ir = dint(f, a, b)
    ir["task"]["params"]["rel_tol"] = tol
    return ir


def cases_h():
    """Review of d4c (2 Oct 2026): narrow peaks both quadratures miss; only a rigorous enclosure decides."""
    I1, I2, I3, I4 = (f"Integral({PK}, (x, 0, 1))", f"Integral({SE}, (x, 0, 1))", f"Integral({SE2}, (x, 0, 1))",
                      f"Integral({SE3}, (x, 0, 1))")
    return [
        ("gauss peak: step true value", X1, _sol("2", cp(f"{I1} = {PK_T}")), OK, NOTREF),
        ("gauss peak: eq true value", X1, _sol("2", eqs(f"{I1} = {PK_T}")), OK, NOTREF),
        ("gauss peak: step 1/3 (peak left out)", X1, _sol("2", cp(f"{I1} = 1/3")), NO, REF),
        ("gauss peak: evaluate true", ev(I1), _sol(PK_T), NOTNO, None),
        ("gauss peak: evaluate 1/3", ev(I1), _sol("1/3"), NOTOK, None),
        ("gauss peak: dint true", dint(PK, 0, 1), _sol(PK_T), NOTNO, None),
        ("gauss peak: dint 1/3", dint(PK, 0, 1), _sol("1/3"), NO, None),
        ("gauss peak pi/4: dint true", dint(PK2, 0, 1), _sol(PK2_T), NOTNO, None),
        ("gauss peak pi/4: dint 3 - cos 1 (peak left out)", dint(PK2, 0, 1), _sol("3 - cos(1)"), NOTOK, None),
        ("gauss peak pi/4: rel_tol 1e-3 claim 2.4597537", dtol(PK2, 0, 1, "1e-3"), _sol("2.4597537"), NOTNO, None),
        ("sech2 peak: step true", X1, _sol("2", cp(f"{I2} = {SE_T}")), OK, NOTREF),
        ("sech2 peak: eq true", X1, _sol("2", eqs(f"{I2} = {SE_T}")), OK, NOTREF),
        ("sech2 peak: step 1/3", X1, _sol("2", cp(f"{I2} = 1/3")), NO, REF),
        ("sech2 peak: evaluate true + step", ev(I2), _sol(SE_T, cp(f"{I2} = {SE_T}")), NOTNO, NOTREF),
        ("sech2 peak: dint true", dint(SE, 0, 1), _sol(SE_T), NOTNO, None),
        ("sech2 peak: dint 1/3", dint(SE, 0, 1), _sol("1/3"), NO, None),
        ("sech2 peak: dint 7/3 (off by e^-6666)", dint(SE, 0, 1), _sol("7/3"), NOTOK, None),
        ("sech2 10^6 peak: step true", X1, _sol("2", cp(f"{I3} = {SE2_T}")), OK, NOTREF),
        ("sech2 10^6 peak: dint true", dint(SE2, 0, 1), _sol(SE2_T), NOTNO, None),
        ("sech2 10^6 peak: dint 3 - cos 1 (peak left out, 2e-6)", dint(SE2, 0, 1), _sol("3 - cos(1)"), NOTOK, None),
        ("sech2 e^sin peak: step true", X1, _sol("2", cp(f"{I4} = {SE3_T}")), OK, NOTREF),
        ("sech2 e^sin peak: dint true", dint(SE3, 0, 1), _sol(SE3_T), NOTNO, None),
        ("sech2 e^sin peak: dint wrong", dint(SE3, 0, 1), _sol("1/3 + exp(sin(1)) - 1"), NO, None),
        ("x^3 + 10^3 sech2(10^3(x - 1/pi)) dint true", dint("x**3 + 10**3/cosh(10**3*(x - 1/pi))**2", 0, 1),
         _sol("1/4 + tanh(10**3*(1 - 1/pi)) + tanh(10**3/pi)"), NOTNO, None),
        ("sin 3x + 10^5 sech2 dint true", dint("sin(3*x) + 10**5/cosh(10**5*(x - 1/7))**2", 0, 1),
         _sol("(1 - cos(3))/3 + tanh(10**5*6/7) + tanh(10**5/7)"), NOTNO, None),
        ("Lorentz 10^6 dint true", dint("x**2 + 10**3/(1 + 10**6*(x - 1/3)**2)", 0, 1),
         _sol("1/3 + atan(2000/3) + atan(1000/3)"), NOTNO, None),
        # infinite ranges: no rigorous enclosure, nothing refuted by numbers
        ("inf: step gauss + sech2 on R", X1, _sol("2", cp("Integral(exp(-x**2) + 1/cosh(10**4*(x - 1/3))**2, (x, -oo, oo)) = sqrt(pi) + 2/10**4")), NOTNO, NOTREF),
        ("inf: step e^-x + 10^4 sech2 [0,oo)", X1, _sol("2", cp("Integral(exp(-x) + 10**4/cosh(10**4*(x - 1/3))**2, (x, 0, oo)) = 2 + tanh(10**4/3)")), NOTNO, NOTREF),
        ("inf: dint e^-x + 10^4 sech2 [0,oo)", dint("exp(-x) + 10**4/cosh(10**4*(x - 1/3))**2", 0, "oo"), _sol("2 + tanh(10**4/3)"), NOTNO, None),
        ("inf: dint e^-x^2 + sech2 on R", dint("exp(-x**2) + 1/cosh(10**4*(x - 1/3))**2", "-oo", "oo"), _sol("sqrt(pi) + 2/10**4"), NOTNO, None),
        ("inf: step gauss shifted 100", X1, _sol("2", cp("Integral(exp(-(x - 100)**2), (x, -oo, oo)) = sqrt(pi)")), NOTNO, NOTREF),
        ("inf: dint gauss shifted 1000", dint("exp(-(x - 1000)**2)", "-oo", "oo"), _sol("sqrt(pi)"), NOTNO, None),
        ("inf: step sech2(x - 1000) [0,oo)", X1, _sol("2", cp("Integral(1/cosh(x - 1000)**2, (x, 0, oo)) = 1 + tanh(1000)")), NOTNO, NOTREF),
        ("inf: step E[X^2] N(60,1)", X1, _sol("2", cp("Integral(x**2*exp(-(x - 60)**2/2), (x, -oo, oo)) = 3601*sqrt(2*pi)")), NOTNO, NOTREF),
        ("inf: eq normal density N(100,1) = 1", X1, _sol("2", eqs("Integral(exp(-(x - 100)**2/2), (x, -oo, oo))/sqrt(2*pi) = 1")), NOTNO, NOTREF),
        # a declared tolerance with no exact value from SymPy
        ("tol: sin(sin x) [0,1] 0.4306 rel_tol 1e-3", dtol("sin(sin(x))", 0, 1, "1e-3"), _sol("0.4306"), OK, None),
        ("tol: sin(sin x) [0,1] 0.5 rel_tol 1e-3 (wrong)", dtol("sin(sin(x))", 0, 1, "1e-3"), _sol("0.5"), NO, None),
        ("tol: sin(sin x) [0,1] 0.43060610312069 rel_tol 1e-10", dtol("sin(sin(x))", 0, 1, "1e-10"), _sol("0.43060610312069"), NOTNO, None),
        ("tol: e^cos x [0,1] 2.3416 rel_tol 1e-4", dtol("exp(cos(x))", 0, 1, "1e-4"), _sol("2.3416"), OK, None),
        ("tol: e^cos x [0,1] 2.35 rel_tol 1e-4 (wrong)", dtol("exp(cos(x))", 0, 1, "1e-4"), _sol("2.35"), NO, None),
        ("no tol: sin(sin x) [0,1] 0.4306 (an exact claim)", dint("sin(sin(x))", 0, 1), _sol("0.4306"), NO, None),
    ]


def series(term, lo="1"):
    return _task("series_sum", {"term": term, "var": "k", "lo": lo, "hi": "oo"}, [K])


def cases_i():
    """Sibling paths of the enclosure (6 Oct 2026): nsum's value alone refuted a series whose term far out
    it never saw (one-signed terms, the same value at 30 and 50 digits). Truths: π²/6 + Σ_j c·e^(-j²/w)
    (Jacobi θ₃; 50-digit mpmath sum of the bump)."""
    b1, t1 = "1/k**2 + exp(-(k - 1000)**2)", "3.41757127167487858950366571780"
    b2, t2 = "1/k**2 + 1000000*exp(-(k - 1000)**2)", "1772638.84976071900125768702357"
    b3, t3 = "1/k**2 + exp(-(k - 1000)**2/100)", "19.3694725759033867094540900001"
    return [
        ("bump e^-(k-1000)^2: true value", series(b1), _sol(t1), NOTNO, None),
        ("bump 10^6 e^-(k-1000)^2: true value", series(b2), _sol(t2), NOTNO, None),
        ("bump e^-(k-1000)^2/100: true value", series(b3), _sol(t3), NOTNO, None),
        ("bump: evaluate Sum true value", ev(f"Sum({b1}, (k, 1, oo))", (K,)), _sol(t1), NOTNO, None),
        ("bump: claim pi^2/6 (bump left out)", series(b1), _sol("pi**2/6"), NOTOK, None),
        ("1/(k log k) diverges: oo", series("1/(k*log(k))", "2"), _sol("oo"), NOTNO, None),
        ("1/(k log^2 k): 2.1097428012368919745", series("1/(k*log(k)**2)", "2"), _sol("2.1097428012368919745"),
         NOTNO, None),
        # controls: SymPy's value confirmed by nsum still decides
        ("control: 1/k^2 = pi^2/6", series("1/k**2"), _sol("pi**2/6"), OK, None),
        ("control: 1/k^2 + 1/2^k = pi^2/6 + 1 (nsum off by 6e-5: undecided)", series("1/k**2 + 1/2**k"),
         _sol("pi**2/6 + 1"), NOTNO, None),
        ("control: 1/(k(k+1)) = 1", series("1/(k*(k + 1))"), _sol("1"), OK, None),
        ("control: 1/(k(k+1)) = 1/2 (wrong)", series("1/(k*(k + 1))"), _sol("1/2"), NO, None),
        ("control: sin(pi k/2)/k = pi/4", series("sin(pi*k/2)/k"), _sol("pi/4"), NOTNO, None),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g,
          "H": cases_h, "I": cases_i}
SLOW = 60.0           # group D: every verify returns within this many seconds
CASE_LIMIT = 240      # seconds before a case is abandoned (SIGALRM; the unfixed tree hangs on group D)


class CaseTimeout(BaseException):          # not swallowed by an `except Exception` inside verify
    pass


def _alarm(signum, frame):
    raise CaseTimeout(f"no verdict within {CASE_LIMIT} s")


def main(out_path=None, groups="ABCDEFGHI"):
    import os
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    signal.signal(signal.SIGALRM, _alarm)
    rows = []
    bad = 0
    t0 = time.time()
    for g in groups:
        for label, ir, sol, verdicts, statuses in GROUPS[g]():
            t = time.time()
            signal.alarm(CASE_LIMIT)
            try:
                r = verify(ir, sol)
                signal.alarm(0)
                verdict = r.verdict
                layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                steps = layer.evidence.get("steps", []) if layer is not None else []
                last = steps[-1] if steps else {}
                status = last.get("status")
                lev = last.get("evidence") or {}
                detail = {k: lev[k] for k in ("reason",) if k in lev}
            except (Exception, CaseTimeout) as e:  # noqa: BLE001
                signal.alarm(0)
                if isinstance(e, CaseTimeout):
                    # a call may be left running in the sandbox worker: start a fresh one
                    from mathverify.sandbox import get_sandbox
                    get_sandbox().close()
                verdict, status, detail = f"EXC {type(e).__name__}: {e}", None, {}
            s = round(time.time() - t, 2)
            ok = verdict in verdicts and (statuses is None or status in statuses) and (g != "D" or s <= SLOW)
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": verdict, "status": status, "ok": ok,
                         "detail": json.loads(json.dumps(detail, default=str)), "s": s})
            print(f"{'ok ' if ok else 'BAD'} {g} {verdict:9} {str(status):9} {s:6.1f}s {label}  {str(detail)[:120]}",
                  flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else None
    grp = args[1] if len(args) > 1 else "ABCDEFGHI"
    sys.exit(1 if main(out, grp) else 0)
