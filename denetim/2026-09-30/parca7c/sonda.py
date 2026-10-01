"""Part (v-b C) of the 30 Sep 2026 fixes (HANDOFF V16 and V18, DECISIONS §73 "Açık kalanlar", §74 (g),
§77 "Açık (yeni)"): the task certificates of limit, derivative, tangent line, definite integral and
extremum.

    A  a task expression undefined AS WRITTEN with no free symbol left to choose (log(-1) - log(-1) + 2,
       sqrt(-1)**2 + 3) or with a closed undefined part (x + acos(2) - acos(2)): limit, derivative,
       tangent line and extremum;
    B  a variable declared positive (positive_real) or nonnegative (nonneg_real): the derivative and
       the tangent line at 0 (|x| and sqrt(x**2) at 0 had the derivative 1 and the tangent y = x);
    C  the membership conditions of gcd/lcm, n! and C(n, r) (Contains) in the limit, derivative,
       tangent line, definite and indefinite integral and extremum tasks (lim_{x->-3} x + x! - x!);
    D  x declared positive: the right limit of log(-x) at 0 read from complex values;
    E  V18: an explicit extremum interval read without the variable's constraints, the given
       inequalities and the domain of discourse (max of x on [-2, 3] with x < 1 was 3).

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca7c/sonda.py [out.json] [A B ...]

Lean is not needed (MATHVERIFY_LEAN_REPL=/nonexistent). Kept out of pyflakes and pytest like the rest
of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
BAD = {"INCORRECT", "UNKNOWN"}        # anything but a false accept
NOTBAD = {"CORRECT", "UNKNOWN"}       # anything but a false reject
UNK = {"UNKNOWN"}


def _ir(kind, params, vars_=(), givens=(), shape="scalar", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def _sol(payload, kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []}


X = {"name": "x", "domain": "real"}
XY = [X, {"name": "y", "domain": "real"}]


def _xv(dom=None, cons=None):
    v = {"name": "x"}
    if dom:
        v["domain"] = dom
    if cons:
        v["constraints"] = list(cons)
    return v


def lim(expr, to, vars_=(X,), side=None, givens=(), dod=None):
    p = {"expr": expr, "var": "x", "to": to}
    if side:
        p["side"] = side
    return _ir("limit", p, vars_, givens, dod=dod)


def der(f, at=None, vars_=(X,), givens=()):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    return _ir("derivative", p, vars_, givens, "scalar" if at is not None else "expression")


def tan_(f, at, vars_=None, givens=()):
    return _ir("tangent_line", {"f": f, "var": "x", "at": at, "dep": "y"}, vars_ or XY, givens, "equation")


def ext(f, which="max", interval=None, vars_=(X,), givens=(), dod=None):
    p = {"f": f, "var": "x", "which": which}
    if interval is not None:
        p["interval"] = interval
    return _ir("extremum", p, vars_, givens, dod=dod)


def dint(f, a, b, vars_=(X,)):
    return _ir("definite_integral", {"integrand": f, "var": "x", "a": a, "b": b}, vars_)


def anti(f, vars_=(X,)):
    return _ir("antiderivative", {"integrand": f, "var": "x"}, vars_, shape="expression")


# ---------------------------------------------------------------------------------------------------
C0 = "log(-1) - log(-1) + 2"          # no free symbol, undefined as written, value 2
C1 = "sqrt(-1)**2 + 3"                # no free symbol, value 2
C2 = "acos(2) - acos(2) + 5"          # no free symbol, value 5
C3 = "Sum(k/k, (k, -1, 1))"           # a closed sum with a term undefined at k = 0, value 3
X0 = "x + log(-1) - log(-1)"          # x, with a closed undefined part
X1 = "x + acos(2) - acos(2)"
X2 = "x**2 + 0*log(-2)"
X3 = "x*log(-1)"                      # I*pi*x
X4 = "sqrt(-1)*x"                     # I*x


def cases_a():
    return [
        # limit
        ("lim 0: log(-1)-log(-1)+2 = 2", lim(C0, "0"), _sol("2"), BAD),
        ("lim 0: sqrt(-1)**2+3 = 2", lim(C1, "0"), _sol("2"), BAD),
        ("lim 0: acos(2)-acos(2)+5 = 5", lim(C2, "0"), _sol("5"), BAD),
        ("lim 0: Sum(k/k,(k,-1,1)) = 3", lim(C3, "0"), _sol("3"), BAD),
        ("lim oo: log(-1)-log(-1)+2 = 2", lim(C0, "oo"), _sol("2"), BAD),
        ("lim 1: x+log(-1)-log(-1) = 1", lim(X0, "1"), _sol("1"), BAD),
        ("lim 1: x+acos(2)-acos(2) = 1", lim(X1, "1"), _sol("1"), BAD),
        ("lim 1: x**2+0*log(-2) = 1", lim(X2, "1"), _sol("1"), BAD),
        ("lim 1: x*log(-1) = I*pi", lim(X3, "1"), _sol("I*pi"), BAD),
        ("lim 1: sqrt(-1)*x = I", lim(X4, "1"), _sol("I"), BAD),
        ("control lim 1: x + 2 = 3", lim("x + 2", "1"), _sol("3"), OK),
        ("control lim 1: x + 2 = 4", lim("x + 2", "1"), _sol("4"), NO),
        ("control lim 0: x/x = 1", lim("x/x", "0"), _sol("1"), OK),
        ("control lim 0: 5 = 5 (constant)", lim("5", "0"), _sol("5"), OK),
        ("control lim 0: log(2) - log(2) + 2 = 2", lim("log(2) - log(2) + 2", "0"), _sol("2"), OK),
        # derivative at a point
        ("der at 1: log(-1)-log(-1)+2 -> 0", der(C0, "1"), _sol("0"), BAD),
        ("der at 1: sqrt(-1)**2+3 -> 0", der(C1, "1"), _sol("0"), BAD),
        ("der at 1: Sum(k/k,(k,-1,1)) -> 0", der(C3, "1"), _sol("0"), BAD),
        ("der at 1: x+acos(2)-acos(2) -> 1", der(X1, "1"), _sol("1"), BAD),
        ("der at 1: x**2+0*log(-2) -> 2", der(X2, "1"), _sol("2"), BAD),
        ("control der at 1: x**2 -> 2", der("x**2", "1"), _sol("2"), OK),
        ("control der at 1: x**2 -> 3", der("x**2", "1"), _sol("3"), NO),
        ("control der at 1: 5 -> 0", der("5", "1"), _sol("0"), OK),
        # derivative, no point
        ("der: log(-1)-log(-1)+2 -> 0", der(C0), _sol("0", "expression"), BAD),
        ("der: acos(2)-acos(2)+5 -> 0", der(C2), _sol("0", "expression"), BAD),
        ("der: x+log(-1)-log(-1) -> 1", der(X0), _sol("1", "expression"), BAD),
        ("der: x+acos(2)-acos(2) -> 1", der(X1), _sol("1", "expression"), BAD),
        ("der: x**2+0*log(-2) -> 2*x", der(X2), _sol("2*x", "expression"), BAD),
        ("der: x*log(-1) -> I*pi", der(X3), _sol("I*pi", "expression"), BAD),
        ("der: x + Sum(k/k,(k,-1,1)) -> 1", der("x + Sum(k/k, (k, -1, 1))"), _sol("1", "expression"), BAD),
        ("control der: x**2 -> 2*x", der("x**2"), _sol("2*x", "expression"), OK),
        ("control der: x**2 -> 3*x", der("x**2"), _sol("3*x", "expression"), NO),
        ("control der: log(x) - log(x) + x -> 1", der("log(x) - log(x) + x"), _sol("1", "expression"), NOTBAD),
        # tangent line
        ("tan at 1: log(-1)-log(-1)+2 -> y = 2", tan_(C0, "1"), _sol("y = 2", "equation"), BAD),
        ("tan at 1: acos(2)-acos(2)+5 -> y = 5", tan_(C2, "1"), _sol("y = 5", "equation"), BAD),
        ("tan at 1: x+acos(2)-acos(2) -> y = x", tan_(X1, "1"), _sol("y = x", "equation"), BAD),
        ("tan at 1: x**2+0*log(-2) -> y = 2x-1", tan_(X2, "1"), _sol("y = 2*x - 1", "equation"), BAD),
        ("control tan at 1: x**2 -> y = 2x-1", tan_("x**2", "1"), _sol("y = 2*x - 1", "equation"), OK),
        ("control tan at 1: x**2 -> y = 2x", tan_("x**2", "1"), _sol("y = 2*x", "equation"), NO),
        # extremum
        ("ext max [0,1]: log(-1)-log(-1)+2 = 2", ext(C0, "max", "[0, 1]"), _sol("2"), BAD),
        ("ext min [0,1]: sqrt(-1)**2+3 = 2", ext(C1, "min", "[0, 1]"), _sol("2"), BAD),
        ("ext max [0,1]: Sum(k/k,(k,-1,1)) = 3", ext(C3, "max", "[0, 1]"), _sol("3"), BAD),
        ("ext max R: -(x-1)**2 + log(-1)-log(-1) = 0", ext("-(x - 1)**2 + log(-1) - log(-1)", "max"), _sol("0"), BAD),
        ("ext local_max: -(x-1)**2 + acos(2)-acos(2) = 0",
         ext("-(x - 1)**2 + acos(2) - acos(2)", "local_max"), _sol("0"), BAD),
        ("ext max [0,1]: x+acos(2)-acos(2) = 1", ext(X1, "max", "[0, 1]"), _sol("1"), BAD),
        ("ext argmax [0,1]: x+log(-1)-log(-1) = 1", ext(X0, "argmax", "[0, 1]"), _sol("1"), BAD),
        ("control ext max [-2,3]: x**3-3x = 18", ext("x**3 - 3*x", "max", "[-2, 3]"), _sol("18"), OK),
        ("control ext max [-2,3]: x**3-3x = 2", ext("x**3 - 3*x", "max", "[-2, 3]"), _sol("2"), NO),
        ("control ext max [0,1]: 7 = 7", ext("7", "max", "[0, 1]"), _sol("7"), NOTBAD),
        # the same in LaTeX and through a problem function
        ("lim 0 LaTeX: ln(-1) - ln(-1) + 2 = 2", lim(r"\ln(-1) - \ln(-1) + 2", "0"), _sol("2"), BAD),
        ("der LaTeX: x + ln(-1) - ln(-1) -> 1", der(r"x + \ln(-1) - \ln(-1)"), _sol("1", "expression"), BAD),
        ("lim 1: f(x), f = log(-1) - log(-1) + x", dict(lim("f(x)", "1"), functions=[FN]), _sol("1"), BAD),
        ("der: f(x), f = log(-1) - log(-1) + x -> 1", dict(der("f(x)"), functions=[FN]), _sol("1", "expression"), BAD),
        ("ext max [0,1]: f(x), f = log(-1) - log(-1) + x", dict(ext("f(x)", "max", "[0, 1]"), functions=[FN]),
         _sol("1"), BAD),
        ("control der: g(x), g = x**2 -> 2*x", dict(der("g(x)"), functions=[GN]), _sol("2*x", "expression"), OK),
        # the integrals take the same expression
        ("dint [0,1]: log(-1)-log(-1)+2 = 2", dint(C0, "0", "1"), _sol("2"), BAD),
        ("dint [0,1]: x+acos(2)-acos(2) = 1/2", dint(X1, "0", "1"), _sol("1/2"), BAD),
        ("anti: log(-1)-log(-1)+2 -> 2*x", anti(C0), _sol("2*x", "expression"), BAD),
        ("anti: x+acos(2)-acos(2) -> x**2/2", anti(X1), _sol("x**2/2", "expression"), BAD),
        ("anti: x + Sum(k/k,(k,-1,1)) -> x**2/2 + 3*x", anti("x + Sum(k/k, (k, -1, 1))"),
         _sol("x**2/2 + 3*x", "expression"), BAD),
        # a closed condition no exact check proves: tan(arccot(2) + arccot(1/2)) is tan(pi/2)
        ("der: x + 0*tan(arccot(2)+arccot(1/2)) -> 1", der(TU), _sol("1", "expression"), BAD),
        ("anti: x + 0*tan(arccot(2)+arccot(1/2)) -> x**2/2", anti(TU), _sol("x**2/2", "expression"), BAD),
        ("dint [0,1]: x + 0*tan(arccot(2)+arccot(1/2)) = 1/2", dint(TU, "0", "1"), _sol("1/2"), BAD),
        ("der at 1: x + 0*tan(arccot(2)+arccot(1/2)) -> 1", der(TU, "1"), _sol("1"), BAD),
        # a closed form whose value numbers confirm is no undecided condition
        ("control der: x*Integral(t, (t, 0, 1)) -> 1/2", der("x*Integral(t, (t, 0, 1))", None, XT),
         _sol("1/2", "expression"), OK),
        ("control der: x*Limit(sin(t)/t, t, 0) -> 1", der("x*Limit(sin(t)/t, t, 0)", None, XT),
         _sol("1", "expression"), NOTBAD),
        ("control anti: x*Integral(t, (t, 0, 1)) -> x**2/4", anti("x*Integral(t, (t, 0, 1))", XT),
         _sol("x**2/4", "expression"), NOTBAD),
        ("control dint [0,1]: x = 1/2", dint("x", "0", "1"), _sol("1/2"), OK),
        ("control dint [0,1]: x = 1", dint("x", "0", "1"), _sol("1"), NO),
        ("control anti: cos(x) -> sin(x)", anti("cos(x)"), _sol("sin(x)", "expression"), OK),
        ("control anti: cos(x) -> -sin(x)", anti("cos(x)"), _sol("-sin(x)", "expression"), NO),
    ]


TU = "x + 0*tan(arccot(2) + arccot(1/2))"
XT = [X, {"name": "t", "domain": "real"}]
FN = {"name": "f", "args": ["x"], "expr": "log(-1) - log(-1) + x"}
GN = {"name": "g", "args": ["x"], "expr": "x**2"}


def cases_b():
    rows = []
    for dom in ("positive_real", "nonneg_real"):
        v = [_xv(dom)]
        vy = [_xv(dom), {"name": "y", "domain": "real"}]
        rows += [
            (f"{dom}: der Abs(x) at 0 -> 1", der("Abs(x)", "0", v), _sol("1"), UNK),
            (f"{dom}: der Abs(x) at 0 -> 0", der("Abs(x)", "0", v), _sol("0"), UNK),
            (f"{dom}: der Abs(x) at 0 -> DNE", der("Abs(x)", "0", v), _sol("", "dne"), UNK),
            (f"{dom}: der sqrt(x**2) at 0 -> 1", der("sqrt(x**2)", "0", v), _sol("1"), UNK),
            (f"{dom}: der x*Abs(x) at 0 -> 0", der("x*Abs(x)", "0", v), _sol("0"), UNK),
            (f"{dom}: der x**2 at 0 -> 0", der("x**2", "0", v), _sol("0"), UNK),
            (f"{dom}: der Abs(x) at 0, 2nd order -> 0", _ir("derivative", {"f": "Abs(x)", "var": "x", "at": "0",
                                                                             "order": 2}, v), _sol("0"), UNK),
            (f"{dom}: der sqrt(x) at 0 -> oo", der("sqrt(x)", "0", v), _sol("oo"), UNK),
            (f"{dom}: tan Abs(x) at 0 -> y = x", tan_("Abs(x)", "0", vy), _sol("y = x", "equation"), UNK),
            (f"{dom}: tan sqrt(x**2) at 0 -> y = x", tan_("sqrt(x**2)", "0", vy), _sol("y = x", "equation"), UNK),
            (f"{dom}: tan Abs(x) at 0 -> DNE", tan_("Abs(x)", "0", vy), _sol("", "dne"), UNK),
            (f"{dom}: tan x**2 at 0 -> y = 0", tan_("x**2", "0", vy), _sol("y = 0", "equation"), UNK),
            (f"{dom}: der Abs(x) at -1 -> -1", der("Abs(x)", "-1", v), _sol("-1"), UNK),
            (f"control {dom}: der Abs(x) at 1 -> 1", der("Abs(x)", "1", v), _sol("1"), OK),
            (f"control {dom}: der Abs(x) at 1 -> -1", der("Abs(x)", "1", v), _sol("-1"), NO),
            (f"control {dom}: der x**2 at 1/2 -> 1", der("x**2", "1/2", v), _sol("1"), OK),
            (f"control {dom}: tan Abs(x) at 2 -> y = x", tan_("Abs(x)", "2", vy), _sol("y = x", "equation"), OK),
            (f"control {dom}: tan x**2 at 1 -> y = 2x", tan_("x**2", "1", vy), _sol("y = 2*x", "equation"), NO),
            (f"control {dom}: der Abs(x) (no point) -> 1", der("Abs(x)", None, v), _sol("1", "expression"), NOTBAD),
        ]
    rows += [
        # the constraint written as a relation keeps the same rule: 0 is no interior point
        ("constraint x > 0: der Abs(x) at 0 -> 1", der("Abs(x)", "0", [_xv("real", ["x > 0"])]), _sol("1"), BAD),
        ("constraint x >= 0: der x**2 at 0 -> 0", der("x**2", "0", [_xv("real", ["x >= 0"])]), _sol("0"), UNK),
        ("constraint x >= 0: tan x**2 at 0 -> y = 0",
         tan_("x**2", "0", [_xv("real", ["x >= 0"]), {"name": "y", "domain": "real"}]), _sol("y = 0", "equation"), UNK),
        ("constraint x >= b, b free: der x**2 at 0 -> 0",
         der("x**2", "0", [_xv("real", ["x >= b"]), {"name": "b", "domain": "real"}]), _sol("0"), UNK),
        ("constraint x >= b, b = 0: der x**2 at 0 -> 0",
         der("x**2", "0", [_xv("real", ["x >= b"]), {"name": "b", "domain": "real"}], ["b = 0"]), _sol("0"), UNK),
        ("control constraint x >= b, b = -1: der x**2 at 0 -> 0",
         der("x**2", "0", [_xv("real", ["x >= b"]), {"name": "b", "domain": "real"}], ["b = -1"]), _sol("0"), OK),
        ("dod x >= 0: der x**2 at 0 -> 0", _ir("derivative", {"f": "x**2", "var": "x", "at": "0"}, [X], dod="x >= 0"),
         _sol("0"), UNK),
        ("control real: der Abs(x) at 0 -> DNE", der("Abs(x)", "0"), _sol("", "dne"), OK),
        ("control real: der Abs(x) at 0 -> 1", der("Abs(x)", "0"), _sol("1"), NO),
        ("control real: tan Abs(x) at 0 -> y = x", tan_("Abs(x)", "0"), _sol("y = x", "equation"), NO),
        ("control real: der x**2 at 0 -> 0", der("x**2", "0"), _sol("0"), OK),
        ("control constraint x > -1: der x**2 at 0 -> 0", der("x**2", "0", [_xv("real", ["x > -1"])]), _sol("0"), OK),
    ]
    return rows


def cases_c():
    F = "x + factorial(x) - factorial(x)"
    G = "x + gcd(x, 2) - gcd(2, x)"
    B = "x + binomial(x, 2) - binomial(x, 2)"
    return [
        ("lim -3: x + x! - x! = -3", lim(F, "-3"), _sol("-3"), BAD),
        ("lim 3: x + x! - x! = 3", lim(F, "3"), _sol("3"), BAD),
        ("lim 1/2: x + x! - x! = 1/2", lim(F, "1/2"), _sol("1/2"), BAD),
        ("lim oo: (x + x! - x!)/x = 1", lim(f"({F})/x", "oo"), _sol("1"), BAD),
        ("lim 0: x + gcd(x,2) - gcd(2,x) = 0", lim(G, "0"), _sol("0"), BAD),
        ("lim sqrt(2): x + gcd(x,2) - gcd(2,x) = sqrt(2)", lim(G, "sqrt(2)"), _sol("sqrt(2)"), BAD),
        ("lim -3: x + C(x,2) - C(x,2) = -3", lim(B, "-3"), _sol("-3"), BAD),
        ("der at -3: x + x! - x! -> 1", der(F, "-3"), _sol("1"), BAD),
        ("der at 2: x**2 + x! - x! -> 4", der("x**2 + factorial(x) - factorial(x)", "2"), _sol("4"), BAD),
        ("der at sqrt(2): x + gcd -> 1", der(G, "sqrt(2)"), _sol("1"), BAD),
        ("der: x + x! - x! -> 1", der(F), _sol("1", "expression"), BAD),
        ("der: x + gcd(x,2) - gcd(2,x) -> 1", der(G), _sol("1", "expression"), BAD),
        ("tan at -3: x + x! - x! -> y = x", tan_(F, "-3"), _sol("y = x", "equation"), BAD),
        ("tan at 2: x + x! - x! -> y = x", tan_(F, "2"), _sol("y = x", "equation"), BAD),
        ("dint [-3,-1]: x + x! - x! = -4", dint(F, "-3", "-1"), _sol("-4"), BAD),
        ("dint [0,1]: x + x! - x! = 1/2", dint(F, "0", "1"), _sol("1/2"), BAD),
        ("dint [0,1]: x + gcd(x,2) - gcd(2,x) = 1/2", dint(G, "0", "1"), _sol("1/2"), BAD),
        ("anti: x + x! - x! -> x**2/2", anti(F), _sol("x**2/2", "expression"), BAD),
        ("ext max [1/2, 3/2]: -(x-2)**2 + x! - x! = -1/4",
         ext("-(x - 2)**2 + factorial(x) - factorial(x)", "max", "[1/2, 3/2]"), _sol("-1/4"), BAD),
        ("ext max [-3, -1]: x + x! - x! = -1", ext(F, "max", "[-3, -1]"), _sol("-1"), BAD),
        ("ext max [0, 1]: x + gcd = 1", ext(G, "max", "[0, 1]"), _sol("1"), BAD),
        # a sequence: n a positive integer, n! has its value
        ("control seq lim oo: 2**n/n! = 0", _ir("limit", {"expr": "2**n/factorial(n)", "var": "n", "to": "oo"},
                                                 [{"name": "n", "domain": "positive_integer"}]), _sol("0"), NOTBAD),
        ("control seq lim oo: 2**n/n! = 1", _ir("limit", {"expr": "2**n/factorial(n)", "var": "n", "to": "oo"},
                                                 [{"name": "n", "domain": "positive_integer"}]), _sol("1"), BAD),
        ("control lim 1: x + factorial(3) = 7", lim("x + factorial(3)", "1"), _sol("7"), OK),
        ("control der at 1: x*factorial(3) -> 6", der("x*factorial(3)", "1"), _sol("6"), OK),
        ("control dint [0,1]: x*factorial(2) = 1", dint("x*factorial(2)", "0", "1"), _sol("1"), OK),
    ]


def cases_d():
    P = [_xv("positive_real")]
    N = [_xv("nonneg_real")]
    return [
        ("x>0: lim 0+ x*log(-x) = 0", lim("x*log(-x)", "0", P, "+"), _sol("0"), BAD),
        ("x>0: lim 0 x*log(-x) = 0", lim("x*log(-x)", "0", P), _sol("0"), BAD),
        ("x>0: lim 0+ log(-x) = -oo", lim("log(-x)", "0", P, "+"), _sol("-oo"), BAD),
        ("x>0: lim 0+ x*log(-x) = DNE", lim("x*log(-x)", "0", P, "+"), _sol("", "dne"), NOTBAD),
        ("x>0: lim 1 log(-x) = I*pi", lim("log(-x)", "1", P), _sol("I*pi"), BAD),
        ("x>0: lim oo exp(-x)*log(-x) = 0", lim("exp(-x)*log(-x)", "oo", P), _sol("0"), BAD),
        ("x>0: lim 0+ x*sqrt(-x) = 0", lim("x*sqrt(-x)", "0", P, "+"), _sol("0"), BAD),
        ("x>=0: lim 0 x*log(-x) = 0", lim("x*log(-x)", "0", N), _sol("0"), BAD),
        ("constraint x>0: lim 0+ x*log(-x) = 0", lim("x*log(-x)", "0", [_xv("real", ["x > 0"])], "+"), _sol("0"), BAD),
        ("dod x>0: lim 0+ x*log(-x) = 0", lim("x*log(-x)", "0", [X], "+", dod="x > 0"), _sol("0"), BAD),
        ("given x>0: lim 0+ x*log(-x) = 0", lim("x*log(-x)", "0", [X], "+", givens=["x > 0"]), _sol("0"), BAD),
        ("x>0: der at 1 log(-x) -> -1", der("log(-x)", "1", P), _sol("1"), BAD),
        ("x>0: ext max [1,2] log(-x)", ext("log(-x)", "max", "[1, 2]", P), _sol("log(2)"), BAD),
        # the same limit written inside an expression (a point binder) or in LaTeX
        ("x>0: evaluate Limit(x*log(-x), x, 0, '+') = 0",
         _ir("evaluate", {"expr": "Limit(x*log(-x), x, 0, '+')"}, P), _sol("0"), BAD),
        ("x>0: evaluate Limit(x*log(-x), x, 0) = 0", _ir("evaluate", {"expr": "Limit(x*log(-x), x, 0)"}, P),
         _sol("0"), BAD),
        ("x>0: evaluate limit(x*log(-x), x, 0) = 0", _ir("evaluate", {"expr": "limit(x*log(-x), x, 0)"}, P),
         _sol("0"), BAD),
        ("x>0: evaluate LaTeX lim_{x->0+} x ln(-x) = 0",
         _ir("evaluate", {"expr": r"\lim_{x \to 0^+} x \ln(-x)"}, P), _sol("0"), BAD),
        ("x>0: limit task LaTeX x ln(-x) at 0+ = 0", lim(r"x \ln(-x)", "0", P, "+"), _sol("0"), BAD),
        ("x>0: evaluate Limit(t*log(-t), t, 0, '+') + x, x=1 = 1",
         _ir("evaluate", {"expr": "Limit(t*log(-t), t, 0, '+') + x"}, P + [{"name": "t", "domain": "positive_real"}],
             ["x = 1"]), _sol("1"), BAD),
        ("x>0: lim 0+ x*log(-x) + t, t positive", lim("x*log(-x)", "0", P, "+"), _sol("0"), BAD),
        ("real: lim 0- x*log(-x) = 0", lim("x*log(-x)", "0", [X], "-"), _sol("0"), OK),
        ("control x>0: lim 0+ x*log(x) = 0", lim("x*log(x)", "0", P, "+"), _sol("0"), OK),
        ("control x>0: lim 0+ x*log(x) = 1", lim("x*log(x)", "0", P, "+"), _sol("1"), NO),
    ]


def cases_e():
    lt1 = [_xv("real", ["x < 1"])]
    return [
        # V18's example and its siblings: a constraint, a given, the domain of discourse
        ("V18 constraint x<1: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", lt1), _sol("3"), BAD),
        ("constraint x<1: max x on [-2,3] = 1 (not attained)", ext("x", "max", "[-2, 3]", lt1), _sol("1"), BAD),
        ("constraint x<=1: max x on [-2,3] = 1", ext("x", "max", "[-2, 3]", [_xv("real", ["x <= 1"])]), _sol("1"), OK),
        ("constraint x<=1: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", [_xv("real", ["x <= 1"])]), _sol("3"), NO),
        ("given x<1: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", givens=["x < 1"]), _sol("3"), BAD),
        ("given x<=1: max x on [-2,3] = 1", ext("x", "max", "[-2, 3]", givens=["x <= 1"]), _sol("1"), OK),
        ("given x<=1: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", givens=["x <= 1"]), _sol("3"), NO),
        ("dod x<=1: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", dod="x <= 1"), _sol("3"), BAD),
        ("dod x<=1: max x on [-2,3] = 1", ext("x", "max", "[-2, 3]", dod="x <= 1"), _sol("1"), OK),
        ("dod [0, 2]: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", dod="[0, 2]"), _sol("3"), BAD),
        ("constraint 0<x<=2: min x**2 on [-2,3] = 0", ext("x**2", "min", "[-2, 3]", [_xv("real", ["0 < x <= 2"])]),
         _sol("0"), BAD),
        ("constraint x<=1: argmax x on [-2,3] = 3", ext("x", "argmax", "[-2, 3]", [_xv("real", ["x <= 1"])]), _sol("3"), BAD),
        ("constraint x<=1: argmax x on [-2,3] = 1", ext("x", "argmax", "[-2, 3]", [_xv("real", ["x <= 1"])]), _sol("1"), OK),
        ("constraint x>=1: local_max -(x)(x-2)**2... ", ext("x*(x - 2)**2", "local_max", "[-2, 3]",
                                                           [_xv("real", ["x >= 1"])]), _sol("32/27"), BAD),
        ("constraint x<=1: min -(x-2)**2 on [-2,3]", ext("-(x - 2)**2", "max", "[-2, 3]", [_xv("real", ["x <= 1"])]),
         _sol("0"), BAD),
        ("constraint x != 0: max -x**2 on [-1,1] = 0", ext("-x**2", "max", "[-1, 1]", [_xv("real", ["x != 0"])]),
         _sol("0"), BAD),
        # the intersection is empty
        ("constraint x>5: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", [_xv("real", ["x > 5"])]), _sol("3"), UNK),
        # another symbol: fixed by a given, or free (abstain)
        ("constraint x<b, b=1: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", [_xv("real", ["x < b"]),
                                                                              {"name": "b", "domain": "real"}],
                                                          givens=["b = 1"]), _sol("3"), BAD),
        ("constraint x<=b, b=1: max x on [-2,3] = 1", ext("x", "max", "[-2, 3]", [_xv("real", ["x <= b"]),
                                                                               {"name": "b", "domain": "real"}],
                                                           givens=["b = 1"]), _sol("1"), OK),
        ("constraint x<b, b free: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", [_xv("real", ["x < b"]),
                                                                                 {"name": "b", "domain": "real"}]),
         _sol("3"), UNK),
        ("given x<b, b free: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", [X, {"name": "b", "domain": "real"}],
                                                       givens=["x < b"]), _sol("3"), UNK),
        ("given x**2 <= 1: max x on [-2,3] = 1", ext("x", "max", "[-2, 3]", givens=["x**2 <= 1"]), _sol("1"), OK),
        ("given x**2 <= 1: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", givens=["x**2 <= 1"]), _sol("3"), NO),
        ("given 0 < x <= 2 (chain): max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", givens=["0 < x <= 2"]),
         _sol("3"), BAD),
        ("given x = 2: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", givens=["x = 2"]), _sol("3"), BAD),
        # a relation solveset leaves as a ConditionSet: the region is not known
        ("given x + sin(x) < 1: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", givens=["x + sin(x) < 1"]),
         _sol("3"), UNK),
        ("constraint x + exp(x) < 3: max x on [-2,3] = 3",
         ext("x", "max", "[-2, 3]", [_xv("real", ["x + exp(x) < 3"])]), _sol("3"), UNK),
        ("given x < 0, x positive: max x on [1,3] = 3", ext("x", "max", "[1, 3]", [_xv("positive_real")],
                                                           givens=["x < 0"]), _sol("3"), UNK),
        ("LaTeX interval, constraint x<=1: max x on [-2,3] = 3",
         ext("x", "max", r"\left[-2, 3\right]", [_xv("real", ["x <= 1"])]), _sol("3"), BAD),
        # no interval: a given inequality on x is read too
        ("no interval, given x>b, b free: min (x-3)**2 = 0", ext("(x - 3)**2", "min", None,
                                                               [X, {"name": "b", "domain": "real"}], ["x > b"]),
         _sol("0"), UNK),
        ("no interval, given x>b, b=1: min (x-3)**2 = 0", ext("(x - 3)**2", "min", None,
                                                            [X, {"name": "b", "domain": "real"}], ["x > b", "b = 1"]),
         _sol("0"), OK),
        ("no interval, given x>b, b=4: min (x-3)**2 = 0", ext("(x - 3)**2", "min", None,
                                                            [X, {"name": "b", "domain": "real"}], ["x > b", "b = 4"]),
         _sol("0"), BAD),
        ("no interval, given x<1: max -(x-2)**2 = 0", ext("-(x - 2)**2", "max", None, givens=["x < 1"]), _sol("0"), BAD),
        ("no interval, given x<=1: max -(x-2)**2 = -1", ext("-(x - 2)**2", "max", None, givens=["x <= 1"]),
         _sol("-1"), NOTBAD),
        ("no interval, constraint x<1: max -(x-2)**2 = 0", ext("-(x - 2)**2", "max", None, lt1), _sol("0"), BAD),
        # controls: the data set's shapes
        ("control max x**3-3x on [-2,3] = 18", ext("x**3 - 3*x", "max", "[-2, 3]"), _sol("18"), OK),
        ("control max x**3-3x on [-2,3] = 2", ext("x**3 - 3*x", "max", "[-2, 3]"), _sol("2"), NO),
        ("control x>0 dod: min x + 4/x on (0, oo) = 4",
         ext("x + 4/x", "min", "(0, oo)", [_xv("positive_real")], dod="x > 0"), _sol("4"), OK),
        ("control x>0 dod: min x + 4/x on (0, oo) = 2",
         ext("x + 4/x", "min", "(0, oo)", [_xv("positive_real")], dod="x > 0"), _sol("2"), NO),
        ("control local_max x**3-6x**2+9x+1 = 5", ext("x**3 - 6*x**2 + 9*x + 1", "local_max"), _sol("5"), OK),
        ("control constraint x>-5: max x on [-2,3] = 3", ext("x", "max", "[-2, 3]", [_xv("real", ["x > -5"])]),
         _sol("3"), OK),
        ("control given y = 2 (other var): max x on [-2,3] = 3",
         ext("x", "max", "[-2, 3]", [X, {"name": "y", "domain": "real"}], givens=["y = 2"]), _sol("3"), OK),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e}


def _summ(r):
    lay = []
    for l in r.layers:
        ev = l.evidence or {}
        reason = ev.get("reason") or ev.get("why") or ev.get("error") or ""
        lay.append(f"{l.layer}:{l.verdict}{'(' + str(reason)[:140] + ')' if reason else ''}")
    return lay


def main():
    import mathverify
    from mathverify.verifier import verify
    print(f"mathverify: {mathverify.__file__}", flush=True)
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    only = set(sys.argv[2:])
    rows, bad = [], 0
    for g, fn in GROUPS.items():
        if only and g not in only:
            continue
        for label, ir, sol, exp in fn():
            t0 = time.perf_counter()
            try:
                r = verify(ir, sol)
                v = r.verdict
                lay = _summ(r)
            except Exception as e:  # noqa: BLE001
                v, lay = f"EXC {type(e).__name__}: {e}"[:200], []
            ok = v in exp
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": v, "expected": sorted(exp), "ok": ok, "layers": lay})
            print(f"{g} | {'ok ' if ok else 'BAD'} | {v:9s} (exp {'/'.join(sorted(exp))}) | "
                  f"{time.perf_counter() - t0:5.1f}s | {label}", flush=True)
            if not ok:
                for x in lay:
                    print(f"      {x}", flush=True)
    print(f"\n{len(rows)} cases, {bad} not as expected")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
