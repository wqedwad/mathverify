import sys
from ortak import *

K = {"name": "k", "domain": "integer"}
AR = {"name": "a", "domain": "real"}
AP = {"name": "a", "domain": "positive_real"}
NR = {"name": "n", "domain": "positive_integer"}


def s(term, lo, hi, claim, label, givens=(), vars_=None, exp=NOTOK):
    return (label, ss(term, lo, hi, givens, vars_ or [K, AR]), sol(claim), exp, None)


def cases():
    out = []
    out.append(s("a*k", 1, 3, "12", "SP 2a + 0*log(a - 5) = 4 [given undefined at a=2]", ["2*a + 0*log(a - 5) = 4"]))
    out.append(s("a*k", 1, 3, "12", "SP a + 0*sqrt(a - 5) = 2", ["a + 0*sqrt(a - 5) = 2"]))
    out.append(s("a*k", 1, 3, "12", "SP a*a/a = 2 ctrl ok", ["a*a/a = 2"], exp={"CORRECT", "UNKNOWN"}))
    out.append(s("a*k", 1, 3, "0", "SP a**2/a = 0 [a=0 undefined]", ["a**2/a = 0"]))
    out.append(s("(k - a)/(k - a)", 1, 3, "3", "SP (k-a)/(k-a), a**2 = 4, a > 0", ["a**2 = 4", "a > 0"]))
    out.append(s("(k - a)/(k - a)", 1, 3, "3", "SP (k-a)/(k-a), floor(a) = 2 [a in [2,3)]", ["floor(a) = 2"]))
    out.append(s("(k - a)/(k - a)", 1, 3, "3", "SP (k-a)/(k-a), a in [2, 2.5] (a**2 <= 4, a >= 2)", ["a**2 <= 4", "a >= 2"]))
    out.append(s("(k - a)/(k - a)", 1, 3, "3", "SP (k-a)/(k-a), exp(a) = exp(2)", ["exp(a) = exp(2)"]))
    out.append(s("(k - a)/(k - a)", 1, 3, "3", "SP (k-a)/(k-a), sin(pi*a/4) = 1, 0<a<4", ["sin(pi*a/4) = 1", "a > 0", "a < 4"]))
    out.append(s("(k - a)/(k - a)", 1, 3, "3", "SP (k-a)/(k-a), Abs(a - 2) <= 0", ["Abs(a - 2) <= 0"]))
    out.append(s("(k - a)/(k - a)", 1, 3, "3", "SP (k-a)/(k-a), (a - 2)**2 = 0", ["(a - 2)**2 = 0"]))
    out.append(s("(k - a)/(k - a)", 1, 3, "3", "SP (k-a)/(k-a), a = b, b**2 = 4, b > 0", ["a = b", "b**2 = 4", "b > 0"], vars_=[K, AR, {"name": "b", "domain": "real"}]))
    out.append(s("(k - a)/(k - a)", 1, "n", "3", "SP (k-a)/(k-a) k=1..n, n = 3, a = 2", ["n = 3", "a = 2"], vars_=[K, AR, NR]))
    out.append(s("(k - a)/(k - a)", 1, "n", "3", "SP (k-a)/(k-a) k=1..n, 2n = 6, 2a = 4", ["2*n = 6", "2*a = 4"], vars_=[K, AR, NR]))
    out.append(s("1/(k - a)", 1, "n", "3", "SP 1/(k-a) k=1..n, n**2=9, a = 5/2 [sum -2 - 2/3 + 2... ] wrong claim", ["n**2 = 9", "2*a = 5"], vars_=[K, AR, NR]))
    out.append(s("k/k", "m", 1, "3", "SP k/k k=m..1, m = -1 [0/0 at 0]", ["m = -1"], vars_=[K, {"name": "m", "domain": "integer"}]))
    out.append(s("k/k", "m", 1, "3", "SP k/k k=m..1, 2m = -2", ["2*m = -2"], vars_=[K, {"name": "m", "domain": "integer"}]))
    out.append(s("k/k", "m", 3, "3", "SP k/k k=m..3, m positive integer free -> claim? [fine k>=1]", [], vars_=[K, {"name": "m", "domain": "positive_integer"}], exp={"CORRECT", "UNKNOWN", "INCORRECT"}))
    out.append(s("(-1)**(k/a)", 1, 2, "0", "SP (-1)^(k/a) a**2 = 4 a>0 [(-1)^(1/2) complex]", ["a**2 = 4", "a > 0"]))
    out.append(s("(-1)**(k*a)", 1, 2, "0", "SP (-1)^(k a), 2a = 1 [(-1)^(1/2)]", ["2*a = 1"]))
    out.append(s("k**a", -1, 1, "0", "SP k^a a**2 = 1 a < 0 [0^-1]", ["a**2 = 1", "a < 0"]))
    out.append(s("0**(k - a)", 1, 3, "1", "SP 0^(k-a), 2a = 4 [0^0 at k=2]", ["2*a = 4"]))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
