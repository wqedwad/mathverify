import sys
from ortak import *

NP = {"name": "n", "domain": "positive_integer"}
C_ = {"name": "c", "domain": "real"}


def cf(rec, initial, givens=(), vars_=None):
    return ir("closed_form", {"recurrence": rec, "initial": initial, "var": "n", "name": "a"}, givens,
              vars_ or [NP, C_], shape="expression")


def rt(rec, initial, index, givens=(), vars_=None):
    return ir("recurrence_term", {"recurrence": rec, "initial": initial, "var": "n", "name": "a", "index": index}, givens,
              vars_ or [NP, C_], shape="scalar")


def cases():
    out = []
    out.append(("PIN cf a(n) = a(n-1)/c, a(1) = 1, 2*c = 0: c**(1 - n) [division by 0]", cf("a(n) = a(n - 1)/c", {"1": "1"}, ["2*c = 0"]),
                sol("c**(1 - n)", "expression"), NOTOK, None))
    out.append(("PIN rt a(n) = a(n-1)/c, a(1) = 1, 2*c = 0, a(3): 0 [division by 0]", rt("a(n) = a(n - 1)/c", {"1": "1"}, "3", ["2*c = 0"]),
                sol("0"), NOTOK, None))
    out.append(("PIN rt a(n) = a(n-1)*(n - c)/(n - c), a(1) = 1, c - 2 = 0, a(3): 1 [0/0 at n = 2]",
                rt("a(n) = a(n - 1)*(n - c)/(n - c)", {"1": "1"}, "3", ["c - 2 = 0"]), sol("1"), NOTOK, None))
    out.append(("PIN cf a(n) = a(n-1)*(n - c)/(n - c), a(1) = 1, 2*c = 4: 1 [0/0 at n = 2]",
                cf("a(n) = a(n - 1)*(n - c)/(n - c)", {"1": "1"}, ["2*c = 4"]), sol("1", "expression"), NOTOK, None))
    out.append(("PIN rt a(n) = c*a(n-1), a(1) = 1, c**2 = 4, c < 0, a(3): 4 [right]",
                rt("a(n) = c*a(n - 1)", {"1": "1"}, "3", ["c**2 = 4", "c < 0"]), sol("4"), NOTNO, None))
    out.append(("PIN rt a(n) = c*a(n-1), a(1) = 1, c**2 = 4, c < 0, a(3): -4 [wrong]",
                rt("a(n) = c*a(n - 1)", {"1": "1"}, "3", ["c**2 = 4", "c < 0"]), sol("-4"), NOTOK, None))
    out.append(("PIN rt a(n) = c*a(n-1), a(1) = 1, c**2 = 4, a(3): 4 [right for both]",
                rt("a(n) = c*a(n - 1)", {"1": "1"}, "3", ["c**2 = 4"]), sol("4"), NOTNO, None))
    out.append(("PIN rt a(n) = c*a(n-1), a(1) = 1, c**2 = 4, a(4): 8 [c = -2 gives -8]",
                rt("a(n) = c*a(n - 1)", {"1": "1"}, "4", ["c**2 = 4"]), sol("8"), NOTOK, None))
    out.append(("PIN series c*k, k=1..3, c**2 = 4: 12 [c = -2 gives -12]", ss("c*k", 1, 3, ["c**2 = 4"], [K_, C_]),
                sol("12"), NOTOK, None))
    out.append(("PIN series c**k, k=0..2, c**3 = 8: 7 [right]", ss("c**k", 0, 2, ["c**3 = 8"], [K_, C_]), sol("7"), NOTNO, None))
    out.append(("PIN series c**k, k=0..2, c**4 = 16: 7 [c = -2 gives 3]", ss("c**k", 0, 2, ["c**4 = 16"], [K_, C_]),
                sol("7"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
