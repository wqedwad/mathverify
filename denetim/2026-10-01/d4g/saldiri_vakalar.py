"""Adversarial cases of the independent review of part d4g (2 Oct 2026; review notes in the session scratchpad,
saldiri/d4g). Used by sonda.py as its lower-case groups (w r b t o s u v z q p = the review's W R B T O S U V Z
Q P). Kept out of pyflakes and pytest like the rest of denetim/."""
from __future__ import annotations

OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTNO = {"CORRECT", "UNKNOWN"}
ANY = {"CORRECT", "INCORRECT", "UNKNOWN"}
VER = {"verified"}
REF = {"refuted"}
NOTREF = {"verified", "unknown", "skipped"}
NOTVER = {"unknown", "refuted", "skipped"}

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
XI = {"name": "x", "domain": "integer"}
M = {"name": "m", "domain": "integer"}
P = {"name": "p", "domain": "integer"}
K = {"name": "k", "domain": "integer"}
J = {"name": "j", "domain": "integer"}
I_ = {"name": "i", "domain": "integer"}


def _ir(expr, vars_, givens=(), kind="evaluate", shape="scalar", params=None):
    return {"task": {"kind": kind, "params": params or {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, steps=(), kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def cp(c):
    return [("compute", c)]


def four(vars_, givens=()):
    return _ir("2 + 2", vars_, givens)


def W(label, vars_, givens, claim):
    return (label, four(vars_, givens), _sol("4", cp(claim)), ANY, NOTVER)


def R(label, vars_, givens, claim, kind="compute"):
    return (label, four(vars_, givens), _sol("4", [(kind, claim)]), NOTNO, NOTREF)


def cases_w():
    return [
        W("W1 closed log(1+exp(-exp(10))) = 0", [X], [], "log(1 + exp(-exp(10))) = 0"),
        W("W2 x=163: exp(pi sqrt x) = 640320^3+744", [X], ["x = 163"], "exp(pi*sqrt(x)) = 640320**3 + 744"),
        W("W2b closed exp(pi sqrt 163) = 640320^3+744", [X], [], "exp(pi*sqrt(163)) = 640320**3 + 744"),
        W("W3 Range 2..3: log(1+exp(-exp(10x))) = 0", [XI], ["x >= 2", "x <= 3"], "log(1 + exp(-exp(10*x))) = 0"),
        W("W3b x=2: log(1+exp(-exp(10x))) = 0", [X], ["x = 2"], "log(1 + exp(-exp(10*x))) = 0"),
        W("W4 x**2=9,x>0: exp(pi sqrt(x+160)) = ...", [X], ["x**2 = 9", "x > 0"],
          "exp(pi*sqrt(x + 160)) = 640320**3 + 744"),
        W("W4b x**2=9,x>0, y free: y + exp(pi sqrt(x+160)) = y + ...", [X, Y], ["x**2 = 9", "x > 0"],
          "y + exp(pi*sqrt(x + 160)) = y + 640320**3 + 744"),
        W("W5 Max(x,-x) = x on x > -1/1000", [X], ["x > -1/1000"], "Max(x, -x) = x"),
        W("W6 Heaviside(x) = 1 on x > -1/1000", [X], ["x > -1/1000"], "Heaviside(x) = 1"),
        W("W7 sign(x) = 1 on x > -1/1000", [X], ["x > -1/1000"], "sign(x) = 1"),
        W("W8 floor(x) = 0 on 0<x<1.0001", [X], ["x > 0", "x < 1.0001"], "floor(x) = 0"),
        W("W9 arg(x) = 0 on x > -1/1000", [X], ["x > -1/1000"], "arg(x) = 0"),
        W("W10 Abs(x) = x on x > -1/1000", [X], ["x > -1/1000"], "Abs(x) = x"),
        W("W11 sqrt(x**2) = x on x > -10**-30", [X], ["x > -10**(-30)"], "sqrt(x**2) = x"),
        W("W14 asin(2x/(1+x^2)) = 2atan x on 0<x<1.01", [X], ["x > 0", "x < 1.01"], "asin(2*x/(1 + x**2)) = 2*atan(x)"),
        W("W14b asin(2x/(1+x^2)) = 2atan x on 0<x<2", [X], ["x > 0", "x < 2"], "asin(2*x/(1 + x**2)) = 2*atan(x)"),
        W("W15 atan(1/x) = pi/2 - atan x on x>-1/1000", [X], ["x > -1/1000"], "atan(1/x) = pi/2 - atan(x)"),
        W("W15b atan(1/x) = pi/2 - atan x on x>-1", [X], ["x > -1"], "atan(1/x) = pi/2 - atan(x)"),
        W("W17 sqrt(xy) = sqrt x sqrt y on x,y > -1/1000", [X, Y], ["x > -1/1000", "y > -1/1000"],
          "sqrt(x*y) = sqrt(x)*sqrt(y)"),
        W("W19 exp(log x) = x on x > -1/1000", [X], ["x > -1/1000"], "exp(log(x)) = x"),
        W("W20 acos(cos x) = x on -1/1000 < x < 3", [X], ["x > -1/1000", "x < 3"], "acos(cos(x)) = x"),
        W("W21 (x**2)**(1/2) = x on x > -1/1000 via Rational", [X], ["x > -1/1000"], "(x**2)**(1/2) = x"),
        W("W22 x**(2/3)... (x**3)**(2/3) = x**2 on x>-1/1000", [X], ["x > -1/1000"], "(x**3)**(2/3) = x**2"),
        W("W23 2**Abs(x) = 2**x on x > -1/1000", [X], ["x > -1/1000"], "2**Abs(x) = 2**x"),
        W("W24 exp(sqrt(x**2)) = exp(x) on x > -1/1000", [X], ["x > -1/1000"], "exp(sqrt(x**2)) = exp(x)"),
        W("W25 sin(asin(x)) = x ok, asin(sin(x)) wrong 0<x<1.58", [X], ["x > 0", "x < 1.58"],
          "asin(sin(x)) + sin(asin(x/2)) = x + x/2"),
        W("W26 log(x**2) = 2 log x on (-1/1000, 5)", [X], ["x > -1/1000", "x < 5"], "log(x**2) = 2*log(x)"),
        W("W27 asin(x) + acos(x) = pi/2 trick: asin(1/x) = acsc on x>0.999", [X], ["x > 0.999"],
          "asin(1/x) = pi/2 - acos(1/x) + 0*x"),
        W("W28 int n>5 polynomial vanishing at sample ints? sin(pi*x)=0 x real >5", [X], ["x > 5"], "sin(pi*x) = 0"),
        W("W29 two-cell region x**2=4: sqrt(x**2) = x", [X], ["x**2 = 4"], "sqrt(x**2) = x"),
        W("W30 x in Range -1..1 integer: x**3 = x is TRUE; x**2 = x wrong", [XI], ["x >= -1", "x <= 1"], "x**2 = x"),
    ]


def cases_r():
    ex = lambda iv, f: _ir(None, [{"name": "x"}], kind="extremum",  # noqa: E731
                           params={"f": f, "var": "x", "interval": iv, "which": "max"})
    di = lambda a, b, f: _ir(None, [{"name": "x"}], kind="definite_integral",  # noqa: E731
                             params={"integrand": f, "var": "x", "a": a, "b": b})
    return [
        R("R1 log(exp x) = x", [X], [], "log(exp(x)) = x"),
        R("R2 exp(log x) = x, x>0", [X], ["x > 0"], "exp(log(x)) = x"),
        R("R3 asin(sin x) = x on -1<x<1", [X], ["x > -1", "x < 1"], "asin(sin(x)) = x"),
        R("R4 acos(cos x) = |x| on -3<x<3", [X], ["x > -3", "x < 3"], "acos(cos(x)) = Abs(x)"),
        R("R5 atan(tan x) = x on -3/2<x<3/2", [X], ["x > -3/2", "x < 3/2"], "atan(tan(x)) = x"),
        R("R6 sqrt x sqrt y = sqrt(xy), x,y>0", [X, Y], ["x > 0", "y > 0"], "sqrt(x)*sqrt(y) = sqrt(x*y)"),
        R("R7 sqrt(y) = x given y=x^2, x>0", [X, Y], ["y = x**2", "x > 0"], "sqrt(y) = x"),
        R("R8 log(x^2) = 2 log|x|", [X], [], "log(x**2) = 2*log(Abs(x))"),
        R("R9 (x**3)**(1/3) = x (convention)", [X], [], "(x**3)**(1/3) = x"),
        R("R17 sqrt(x-1)sqrt(x+1) = sqrt(x^2-1), x>1", [X], ["x > 1"], "sqrt(x - 1)*sqrt(x + 1) = sqrt(x**2 - 1)"),
        R("R18 sqrt(x-1)sqrt(x+1) = sqrt(x^2-1) no premise", [X], [], "sqrt(x - 1)*sqrt(x + 1) = sqrt(x**2 - 1)"),
        R("R19 log x + log y = log(xy), x,y>0", [X, Y], ["x > 0", "y > 0"], "log(x) + log(y) = log(x*y)"),
        R("R20 log(xy) = log x + log y no premise", [X, Y], [], "log(x*y) = log(x) + log(y)"),
        R("R21 sqrt(x)/sqrt(x-1)... x>1: sqrt(x/(x-1)) = sqrt(x)/sqrt(x-1)", [X], ["x > 1"],
          "sqrt(x/(x - 1)) = sqrt(x)/sqrt(x - 1)"),
        R("R22 sqrt(x/(x-1)) = sqrt(x)/sqrt(x-1) no premise", [X], [], "sqrt(x/(x - 1)) = sqrt(x)/sqrt(x - 1)"),
        R("R23 Range 1..9 int: sqrt(x**2) = x", [XI], ["x >= 1", "x <= 9"], "sqrt(x**2) = x"),
        R("R24 x>=0 given: sqrt(x**2) = x", [X], ["x >= 0"], "sqrt(x**2) = x"),
        R("R25 x in [0,1]: asin(x) + acos(x) = pi/2", [X], ["x >= 0", "x <= 1"], "asin(x) + acos(x) = pi/2"),
        R("R26 x<0: sqrt(x**2) = -x", [X], ["x < 0"], "sqrt(x**2) = -x"),
        R("R27 x<0: log(x**2) = 2*log(-x)", [X], ["x < 0"], "log(x**2) = 2*log(-x)"),
        R("R28 x>2 and y=x-2: sqrt(y**2) = x - 2", [X, Y], ["x > 2", "y = x - 2"], "sqrt(y**2) = x - 2"),
        R("R29 x>0: x**(1/2)*x**(1/3) = x**(5/6)", [X], ["x > 0"], "x**(1/2)*x**(1/3) = x**(5/6)"),
        R("R30 eq: x>0: sqrt(x**2) = x", [X], ["x > 0"], "sqrt(x**2) = x", kind="eq"),
        ("R10 integral a=2,b=0 |x|: compute |x| = x", di("2", "0", "Abs(x)"),
         _sol("-2", [("compute", "Abs(x) = x"), ("compute", "-Integral(x, (x, 0, 2)) = -2")]), NOTNO, None),
        ("R10b integral a=2,b=0: only |x| = x", di("2", "0", "Abs(x)"), _sol("-2", cp("Abs(x) = x")), NOTNO, NOTREF),
        ("R11 extremum [1,3] sqrt(x**2)=x", ex("[1, 3]", "sqrt(x**2) + x"), _sol("6", cp("sqrt(x**2) = x")), NOTNO, NOTREF),
        ("R12 extremum (0,2) open: Abs(x) = x", ex("(0, 2)", "Abs(x) - x**2"), _sol("1/4", cp("Abs(x) = x")), NOTNO, NOTREF),
        ("R13 extremum [0,2]: log-free diff(|x-3|) = -1", ex("[0, 2]", "Abs(x - 3) + x**2"),
         _sol("5", cp("diff(Abs(x - 3), x) = -1")), NOTNO, NOTREF),
        ("R14 integral [1,e]: log(x**2) = 2 log x", di("1", "E", "log(x**2)"), _sol("2", cp("log(x**2) = 2*log(x)")),
         NOTNO, NOTREF),
        ("R15 integral [-2,-1]: sqrt(x**2) = -x", di("-2", "-1", "sqrt(x**2)"), _sol("3/2", cp("sqrt(x**2) = -x")),
         NOTNO, NOTREF),
        ("R16 integral [-2,-1]: antiderivative of |x| = -x**2/2", di("-2", "-1", "Abs(x)"),
         _sol("3/2", cp("Integral(Abs(x), x) = -x**2/2")), NOTNO, NOTREF),
        ("R31 trig_solve [0,pi): tan x = sqrt3 -> step sqrt(tan(x)**2) = tan(x)",
         _ir(None, [{"name": "x"}], kind="trig_solve", params={"equation": "tan(x) = sqrt(3)", "var": "x",
                                                              "interval": "[0, pi/2)"}),
         _sol("pi/3", cp("sqrt(tan(x)**2) = tan(x)"), kind="value"), NOTNO, NOTREF),
    ]


def cases_b():
    return [
        ("B1 55 + Sum(Sum(0,(j,1,k)),(k,1,m)) = 56", _ir("Sum(k, (k, 1, 10))", [M, K, J]),
         _sol("55", cp("55 + Sum(Sum(0, (j, 1, k)), (k, 1, m)) = 56")), NO, REF),
        ("B2 m<0: 55 + Sum(1,(k,1,m)) - Sum(1,(j,1,m)) = 56", _ir("Sum(k, (k, 1, 10))", [M, K, J], ["m < 0"]),
         _sol("55", cp("55 + Sum(1, (k, 1, m)) - Sum(1, (j, 1, m)) = 56")), NO, REF),
        ("B2b m free: 55 + Sum(1,(k,1,m)) - Sum(1,(j,1,m)) = 56", _ir("Sum(k, (k, 1, 10))", [M, K, J]),
         _sol("55", cp("55 + Sum(1, (k, 1, m)) - Sum(1, (j, 1, m)) = 56")), NO, REF),
        ("B3 (x+1)^2 = x^2+1+Sum(0,(j,1,floor(x)))", _ir("2 + 2", [X, J]),
         _sol("4", cp("(x + 1)**2 = x**2 + 1 + Sum(0, (j, 1, floor(x)))")), NO, REF),
        ("B4 (x+1)^2 = (x^2+1)*Product(1,(j,1,m))", _ir("2 + 2", [X, M, J]),
         _sol("4", cp("(x + 1)**2 = (x**2 + 1)*Product(1, (j, 1, m))")), NO, REF),
        ("B5 42*Product(Product(1,(i,1,j)),(j,1,m)) = 43", _ir("6*7", [M, J, I_]),
         _sol("42", cp("6*7*Product(Product(1, (i, 1, j)), (j, 1, m)) = 43")), NO, REF),
        ("B6 55 + Sum(0,(k,m,p)) = 56", _ir("Sum(k, (k, 1, 10))", [M, P, K]),
         _sol("55", cp("55 + Sum(0, (k, m, p)) = 56")), NO, REF),
        ("B7 m>=1: Sum(1,(k,1,m)) = m", _ir("2 + 2", [M, K], ["m >= 1"]), _sol("4", cp("Sum(1, (k, 1, m)) = m")),
         OK, VER),
        ("B9 m<0 only: 55 + Sum(0,(k,1,m)) = 56", _ir("Sum(k, (k, 1, 10))", [M, K], ["m < 0"]),
         _sol("55", cp("55 + Sum(0, (k, 1, m)) = 56")), NO, REF),
        ("B10 m<0: 55 + Sum(k-k+0*m,(k,1,m)) = 56 (written zero)", _ir("Sum(k, (k, 1, 10))", [M, K], ["m < 0"]),
         _sol("55", cp("55 + Sum(k**2 - k*k, (k, 1, m)) = 56")), NO, REF),
        ("B11 m<0: 55 + Sum(k,(k,1,m))*0 + ... via Sum(k,(k,1,m))**0", _ir("Sum(k, (k, 1, 10))", [M, K], ["m < 0", "m > -5"]),
         _sol("55", cp("54 + Sum(k, (k, 1, m))**0 = 56")), NO, REF),
        ("B12 (x+1)^2 = x^2+1 + Sum(0,(j,1,m)) given m < 0", _ir("2 + 2", [X, M, J], ["m < 0"]),
         _sol("4", cp("(x + 1)**2 = x**2 + 1 + Sum(0, (j, 1, m))")), NO, REF),
        ("B13 (x+1)^2 = x^2+1 + Sum(1,(j,1,m)) - m, given m < 0", _ir("2 + 2", [X, M, J], ["m < 0"]),
         _sol("4", cp("(x + 1)**2 = x**2 + 1 + Sum(1, (j, 1, m)) - m")), ANY, None),
    ]


def cases_t():
    return [
        ("T1 quartic premise x^4-4x^2+x+1=0", _ir("x**4 - 4*x**2 + x", [X], ["x**4 - 4*x**2 + x + 1 = 0"]),
         _sol("-1", cp("x**4 - 4*x**2 + x = -1")), NOTNO, NOTREF),
        ("T2 quintic premise x^5-5x+1=0", _ir("x**5 - 5*x", [X], ["x**5 - 5*x + 1 = 0"]),
         _sol("-1", cp("x**5 - 5*x = -1")), NOTNO, NOTREF),
        ("T3 two cubics", _ir("x**3 + y**3 - 3*x - 3*y", [X, Y], ["x**3 - 3*x + 1 = 0", "y**3 - 3*y + 1 = 0"]),
         _sol("-2", cp("x**3 + y**3 - 3*x - 3*y = -2")), NOTNO, NOTREF),
        ("T4 cubic + sqrt(x**2) = x", _ir("2 + 2", [X], ["x**3 - 3*x + 1 = 0"]), _sol("4", cp("sqrt(x**2) = x")),
         ANY, NOTVER),
        ("T5 cubic, 4 steps", _ir("x**3 - 3*x", [X], ["x**3 - 3*x + 1 = 0"]),
         _sol("-1", [("compute", "x**3 - 3*x = -1"), ("compute", "x**3 = 3*x - 1"),
                     ("compute", "x**3 - 3*x + 1 = 0"), ("compute", "2*x**3 - 6*x = -2")]), NOTNO, NOTREF),
        ("T6 cubic premise, wrong + J: sqrt(x**3) = x*sqrt(x)", _ir("2 + 2", [X], ["x**3 - 3*x + 1 = 0"]),
         _sol("4", cp("sqrt(x**3) = x*sqrt(x)")), ANY, None),
        ("T7 trig heavy (sin+cos)^30", _ir("2 + 2", [X]),
         _sol("4", cp("(sin(x) + cos(x))**30 = (sin(x) + cos(x))**28*(1 + sin(2*x))")), NOTNO, NOTREF),
        ("T8 cubic in sqrt premise", _ir("2 + 2", [X], ["x**3 - 3*x + 1 = 0", "x > 0"]),
         _sol("4", cp("asin(x/2) + acos(x/2) = pi/2")), NOTNO, NOTREF),
    ]


GROUPS = {"W": cases_w, "R": cases_r, "B": cases_b, "T": cases_t}


def cases_o():
    return [
        W("O1 asin(sin x) + (-8)**(1/3) = x + (-8)**(1/3) on 0<x<1.58", [X], ["x > 0", "x < 1.58"],
          "asin(sin(x)) + (-8)**(1/3) = x + (-8)**(1/3)"),
        W("O2 log(x**2) + (-8)**(1/3) = 2 log x + (-8)**(1/3) on x>-1/1000", [X], ["x > -1/1000"],
          "log(x**2) + (-8)**(1/3) = 2*log(x) + (-8)**(1/3)"),
        W("O3 asin(sin x)*(-1)**(1/3) = x*(-1)**(1/3) on 0<x<1.58", [X], ["x > 0", "x < 1.58"],
          "asin(sin(x))*(-1)**(1/3) = x*(-1)**(1/3)"),
        W("O4 Matrix([[asin(sin x)]]) = Matrix([[x]])", [X], ["x > 0", "x < 1.58"],
          "Matrix([[asin(sin(x))]]) = Matrix([[x]])"),
        W("O5 asin(sin x) = x, no odd root, control", [X], ["x > 0", "x < 1.58"], "asin(sin(x)) = x"),
        W("O6 (-8)**(1/3)*acos(cos(x)) = (-8)**(1/3)*x on -1/1000<x<3", [X], ["x > -1/1000", "x < 3"],
          "(-8)**(1/3)*acos(cos(x)) = (-8)**(1/3)*x"),
        W("O7 n>5 int: binomial(n,200) + (-8)**(1/3) = (-8)**(1/3)", [{"name": "n", "domain": "integer"}], ["n > 5"],
          "binomial(n, 200) + (-8)**(1/3) = (-8)**(1/3)"),
        W("O8 sqrt(x**2) + (-8)**(1/3) = x + (-8)**(1/3) on x>-1/1000", [X], ["x > -1/1000"],
          "sqrt(x**2) + (-8)**(1/3) = x + (-8)**(1/3)"),
    ]


GROUPS["O"] = cases_o


T_ = {"name": "t", "domain": "real"}
XC = {"name": "x", "domain": "real", "constraints": ["x >= 3", "x <= 3"]}
XIC = {"name": "x", "domain": "integer", "constraints": ["x >= 3", "x <= 3"]}
TINY = "log(1 + exp(-exp(10*x)))"
SQ = "(1 + exp(-exp(exp(x))))**2 = 1 + 2*exp(-exp(exp(x)))"


def cases_s():
    return [
        W("S1 var constraint 3<=x<=3: 1 + log(1+exp(-exp(10x))) = 1", [XC], [], f"1 + {TINY} = 1"),
        W("S2 givens x>=3, x<=3: same", [X], ["x >= 3", "x <= 3"], f"1 + {TINY} = 1"),
        W("S3 x**2=9, x>0 + Limit: Limit(sin t/t) + tiny = 1", [X, T_], ["x**2 = 9", "x > 0"],
          f"Limit(sin(t)/t, t, 0) + {TINY} = 1"),
        W("S4 x = 3 + Limit", [X, T_], ["x = 3"], f"Limit(sin(t)/t, t, 0) + {TINY} = 1"),
        W("S5 int constraint 3<=x<=3", [XIC], [], f"1 + {TINY} = 1"),
        W("S6 x**2=9,x>0 + Derivative: diff(x**2,x) = 2x + tiny", [X], ["x**2 = 9", "x > 0"],
          f"diff(x**2, x) = 2*x + {TINY}"),
        W("S7 y free, x in {3} by constraint: y + tiny = y", [XC, Y], [], f"y + {TINY} = y"),
        W("S8 whitelist only, x > 3: (1+e^-e^e^x)^2 = 1 + 2e^-e^e^x", [X], ["x > 3"], SQ),
        W("S9 whitelist only, no premise: same", [X], [], SQ),
        W("S10 closed: (1+exp(-exp(20)))**2 = 1 + 2*exp(-exp(20))", [X], [],
          "(1 + exp(-exp(20)))**2 = 1 + 2*exp(-exp(20))"),
        W("S11 whitelist, x > 3: cosh/sinh tiny: (1+exp(-exp(exp(x))))**3 = 1 + 3*exp(-exp(exp(x)))", [X], ["x > 3"],
          "(1 + exp(-exp(exp(x))))**3 = 1 + 3*exp(-exp(exp(x))) + 3*exp(-2*exp(exp(x)))"),
        ("S12 eq route x>3: same SQ", four([X], ["x > 3"]), _sol("4", [("eq", SQ)]), ANY, NOTVER),
    ]


GROUPS["S"] = cases_s


def cases_u():
    return [
        W("U1 3<x<4 whitelist (1+t)^2 = 1+2t, t=e^-e^e^x", [X], ["x > 3", "x < 4"], SQ),
        W("U2 1<x<2 same", [X], ["x > 1", "x < 2"], SQ),
        W("U3 2<x<3 same", [X], ["x > 2", "x < 3"], SQ),
        W("U4 3<x<4 t = exp(-exp(10x)): (1+t)^2 = 1+2t", [X], ["x > 3", "x < 4"],
          "(1 + exp(-exp(10*x)))**2 = 1 + 2*exp(-exp(10*x))"),
        W("U5 no premise t = exp(-exp(10x)): (1+t)^2 = 1+2t", [X], [],
          "(1 + exp(-exp(10*x)))**2 = 1 + 2*exp(-exp(10*x))"),
        W("U6 x>3: cosh(x)**2 - sinh(x)**2 = 1 + exp(-exp(exp(x)))", [X], ["x > 3", "x < 4"],
          "cosh(x)**2 - sinh(x)**2 = 1 + exp(-exp(exp(x)))"),
        ("B14 three zero sums: 55 + S0(m) + S0(p) + S0(q) = 56",
         _ir("Sum(k, (k, 1, 10))", [M, P, {"name": "q", "domain": "integer"}, K, J, I_]),
         _sol("55", cp("55 + Sum(0, (k, 1, m)) + Sum(0, (j, 1, p)) + Sum(0, (i, 1, q)) = 56")), NO, REF),
        ("B15 Sum(Sum(0,(j,1,m)),(k,1,m)) inner indep", _ir("Sum(k, (k, 1, 10))", [M, K, J]),
         _sol("55", cp("55 + Sum(Sum(0, (j, 1, m)), (k, 1, m)) = 56")), NO, REF),
        ("B16 three zero sums wrong identity", _ir("2 + 2", [X, M, P, {"name": "q", "domain": "integer"}, K, J, I_]),
         _sol("4", cp("(x + 1)**2 = x**2 + 1 + Sum(0, (k, 1, m)) + Sum(0, (j, 1, p)) + Sum(0, (i, 1, q))")), NO, REF),
        ("R40 evaluate with Integral(|x|,(x,0,2)): compute |x| = x",
         _ir("Integral(Abs(x), (x, 0, 2))", [X]), _sol("2", cp("Abs(x) = x")), NOTNO, NOTREF),
        ("R41 extremum (0, oo): sqrt(x**2) = x",
         _ir(None, [{"name": "x"}], kind="extremum", params={"f": "sqrt(x**2) - x**2", "var": "x", "interval": "(0, oo)",
                                                           "which": "max"}),
         _sol("1/4", cp("sqrt(x**2) = x")), NOTNO, NOTREF),
    ]


GROUPS["U"] = cases_u


def cases_v():
    out = []
    for e in (20, 50, 100, 200, 400):
        out.append(W(f"V poly 3<x<4: (1 + x/10**{e})**2 = 1 + 2x/10**{e}", [X], ["x > 3", "x < 4"],
                     f"(1 + x/10**{e})**2 = 1 + 2*x/10**{e}"))
    for c in (10, 20, 40, 80):
        out.append(W(f"V exp 3<x<4: (1 + exp(-{c}x))**2 = 1 + 2exp(-{c}x)", [X], ["x > 3", "x < 4"],
                     f"(1 + exp(-{c}*x))**2 = 1 + 2*exp(-{c}*x)"))
    out.append(W("V poly no premise: (1 + x/10**400)**2 = 1 + 2x/10**400", [X], [],
                 "(1 + x/10**400)**2 = 1 + 2*x/10**400"))
    out.append(W("V exp no premise: (1 + exp(-80x))**2 = 1 + 2exp(-80x)", [X], [],
                 "(1 + exp(-80*x))**2 = 1 + 2*exp(-80*x)"))
    return out


GROUPS["V"] = cases_v


def _solc(payload, steps):
    return {"claimed_answer": {"kind": "value", "payload": payload},
            "steps": [{"id": i, "kind": k, "claim": c, "from": f, "text": ""} for i, k, c, f in steps]}


def cases_z():
    di = _ir(None, [{"name": "x"}], kind="definite_integral", params={"integrand": "Abs(x)", "var": "x", "a": "0", "b": "2"})
    ex = _ir(None, [{"name": "x"}], kind="extremum", params={"f": "Abs(x) + x**2", "var": "x", "interval": "[1, 3]",
                                                              "which": "max"})
    return [
        ("Z1 integral [0,2], case x<0 (vacuous): compute |x| = -x",
         di, _solc("2", [("c1", "case", "x < 0", []), ("s1", "compute", "Abs(x) = -x", ["c1"])]), NOTNO, NOTREF),
        ("Z2 no window, case x<0: compute |x| = -x", four([X]),
         _solc("4", [("c1", "case", "x < 0", []), ("s1", "compute", "Abs(x) = -x", ["c1"])]), NOTNO, NOTREF),
        ("Z3 integral [0,2], case x<0: eq |x| = -x", di,
         _solc("2", [("c1", "case", "x < 0", []), ("s1", "eq", "Abs(x) = -x", ["c1"])]), NOTNO, NOTREF),
        ("Z4 extremum [1,3]: general antiderivative-free derivative piecewise for x<0: case x<0, diff = -1 + 2x", ex,
         _solc("12", [("c1", "case", "x < 0", []), ("s1", "compute", "diff(Abs(x) + x**2, x) = -1 + 2*x", ["c1"])]),
         NOTNO, NOTREF),
        ("Z5 extremum [1,3]: compute diff at -2 closed", ex,
         _sol("12", cp("Subs(diff(Abs(x) + x**2, x), x, -2) = -5")), NOTNO, NOTREF),
        ("Z6 integral [0,2]: compute sqrt((x-3)**2) = 3 - x", di, _sol("2", cp("sqrt((x - 3)**2) = 3 - x")), NOTNO, NOTREF),
        ("Z7 integral [0,2]: compute Integral(Abs(x), (x, -1, 0)) = 1/2 (closed)", di,
         _sol("2", cp("Integral(Abs(x), (x, -1, 0)) = 1/2")), NOTNO, NOTREF),
        ("Z8 integral [0,2] given-free: Integral(Abs(t), (t, -1, x)) = 1/2 + x**2/2", 
         _ir(None, [{"name": "x"}, {"name": "t"}], kind="definite_integral",
             params={"integrand": "Abs(x)", "var": "x", "a": "0", "b": "2"}),
         _sol("2", cp("Integral(Abs(t), (t, -1, x)) = 1/2 + x**2/2")), NOTNO, NOTREF),
    ]


GROUPS["Z"] = cases_z


def cases_q():
    return [
        W("Q1 x+y=0, x-y=0: x/x + y = 1 + y", [X, Y], ["x + y = 0", "x - y = 0"], "x/x + y = 1 + y"),
        W("Q2 x+y=0, x-y=0 + Limit: Limit(sin t/t)*x/x = 1", [X, Y, T_], ["x + y = 0", "x - y = 0"],
          "Limit(sin(t)/t, t, 0)*x/x + y = 1 + y"),
        W("Q3 x**2 = 0 (single pt) + Limit: Limit(sin t/t)*x/x = 1", [X, T_], ["x**2 = 0"],
          "Limit(sin(t)/t, t, 0)*x/x = 1"),
        W("Q4 x**2 + y**2 = 0 + Limit: y + Limit(sin t/t)*x/x = 1 + y", [X, Y, T_], ["x**2 + y**2 = 0"],
          "y + Limit(sin(t)/t, t, 0)*x/x = 1 + y"),
        W("Q5 x>=0, x<=0 (Interval(0,0)) + Limit: Limit(sin t/t)*sqrt(x)/sqrt(x) = 1", [X, T_], ["x >= 0", "x <= 0"],
          "Limit(sin(t)/t, t, 0)*sqrt(x)/sqrt(x) = 1"),
    ]


GROUPS["Q"] = cases_q


def cases_q2():
    return [
        W("Q6 x**2 + y**2 = 0: y + x/x = 1 + y", [X, Y], ["x**2 + y**2 = 0"], "y + x/x = 1 + y"),
        W("Q7 x**2 + y**2 = 0: x/x = 1", [X, Y], ["x**2 + y**2 = 0"], "x/x = 1"),
        ("Q8 x**2 + y**2 = 0: eq x/x = 1", four([X, Y], ["x**2 + y**2 = 0"]), _sol("4", [("eq", "x/x = 1")]), ANY, NOTVER),
        W("Q9 x**4 = 0: x/x = 1", [X], ["x**4 = 0"], "x/x = 1"),
        W("Q10 x**2 + y**2 = 0 + Limit: Limit(sin t/t)*x/x = 1 (no y in claim)", [X, Y, T_], ["x**2 + y**2 = 0"],
          "Limit(sin(t)/t, t, 0)*x/x = 1"),
    ]


GROUPS["P"] = cases_q2
