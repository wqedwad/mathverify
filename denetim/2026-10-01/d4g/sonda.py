"""Part d4g of the fourth audit's fixes: the step refuter (`steps/deterministic.py`).

Findings (denetim/2026-10-01/d4/, adim and tanimlilik), reproduced on 21c1698 before the fix:

    A  D4-ADIM-A  a wrong step verified by agreement at random points of the premises' region: asin(sin(x)) = x
                  on 0 < x < 1.58, log(x**2) = 2*log(x) on x > -1/1000, binomial(n, 200) = 0 for n > 5, a
                  Product on 21 integers. Random agreement proves an identity only for expressions analytic off
                  a discrete set compared on sets with interior; otherwise the step is not verified.
    B  D4-ADIM-B  a refutation withdrawn because the claim has a Sum whose range may run backwards, although
                  the refutation does not depend on it (a sum that is 0 under every reading).
    C  D4-ADIM-E  the task's interval was not a premise of compute steps: right steps refuted outside it.
    D  D4-ADIM-F  a step over a cubic premise with three real roots ran 120-390 s.
    E  D4-ADIM-H  a symbolic Sum identity verified with Karr's value where the range runs backwards.
    F  D4-ADIM-J  a refutation at a point where the claim, read as written, has no value.
    G  D4-ADIM-D, TAN-11  a step undefined at a point the premises allow (a Range, two symbols, one symbol
                  pinned and another free) verified.
    K  controls whose decision must not change.

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-10-01/d4g/sonda.py [out.json] [groups]

Lean is not needed (MATHVERIFY_LEAN_REPL=/nonexistent). Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
ANY = {"CORRECT", "INCORRECT", "UNKNOWN"}
VER = {"verified"}
REF = {"refuted"}
NOTREF = {"verified", "unknown", "skipped"}
NOTVER = {"unknown", "refuted"}
UNKS = {"unknown"}

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
N = {"name": "n", "domain": "integer"}
NP = {"name": "n", "domain": "positive_integer"}
K = {"name": "k", "domain": "integer"}
M = {"name": "m", "domain": "integer"}
MP = {"name": "m", "domain": "positive_integer"}
J = {"name": "j", "domain": "integer"}


def _ir(expr, vars_, givens=(), kind="evaluate", shape="scalar", params=None):
    return {"task": {"kind": kind, "params": params or {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, steps=(), kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def cp(claim):
    return [("compute", claim)]


def eq(claim):
    return [("eq", claim)]


def four(vars_, givens=()):
    return _ir("2 + 2", vars_, givens)


# (label, ir, solution, expected verdicts, expected status of the LAST step: set or None[, max seconds])
def cases_a():
    return [
        ("asin(sin x) = x on 0 < x < 1.58", four([X], ["x > 0", "x < 1.58"]), _sol("4", cp("asin(sin(x)) = x")),
         ANY, NOTVER),
        ("log(x**2) = 2 log x on x > -1/1000", four([X], ["x > -1/1000"]), _sol("4", cp("log(x**2) = 2*log(x)")),
         ANY, NOTVER),
        ("binomial(n, 200) = 0 for n > 5", four([N], ["n > 5"]), _sol("4", cp("binomial(n, 200) = 0")), ANY, NOTVER),
        ("Product(n - k, (k, 1, 20)) = 0 on 1..21", four([N, K], ["n >= 1", "n <= 21"]),
         _sol("4", cp("Product(n - k, (k, 1, 20)) = 0")), ANY, NOTVER),
        ("atan(tan x) = x on 0 < x < 1.6", four([X], ["x > 0", "x < 1.6"]), _sol("4", cp("atan(tan(x)) = x")),
         ANY, NOTVER),
        ("acos(cos x) = x on x > -1/1000", four([X], ["x > -1/1000"]), _sol("4", cp("acos(cos(x)) = x")),
         ANY, NOTVER),
        ("sqrt(x**2) = x on x > -1/1000", four([X], ["x > -1/1000"]), _sol("4", cp("sqrt(x**2) = x")), ANY, NOTVER),
        ("binomial(n, 200) = 0, n positive (identity route)", four([NP]), _sol("4", cp("binomial(n, 200) = 0")),
         ANY, NOTVER),
        ("Product(n - k, (k, 1, 30)) = 0 on 1..31", four([N, K], ["n >= 1", "n <= 31"]),
         _sol("4", cp("Product(n - k, (k, 1, 30)) = 0")), ANY, NOTVER),
        # controls: a wrong analytic step on the region is still refuted, a right one verified
        ("ctrl x**2 = x on x > 0 (refuted)", four([X], ["x > 0"]), _sol("4", cp("x**2 = x")), NO, REF),
        ("ctrl (x+1)**2 = x**2+2x+1 on 0<x<1", four([X], ["x > 0", "x < 1"]), _sol("4", cp("(x + 1)**2 = x**2 + 2*x + 1")),
         OK, VER),
        ("ctrl Abs(x) = x on x > 0 (cell proof)", four([X], ["x > 0"]), _sol("4", cp("Abs(x) = x")), OK, VER),
        ("ctrl Sum(k,1,n) = n(n+1)/2, n positive", four([NP, K]), _sol("4", cp("Sum(k, (k, 1, n)) = n*(n + 1)/2")),
         OK, VER),
    ]


def cases_b():
    i10 = _ir("Sum(k, (k, 1, 10))", [NP, K])
    i5 = _ir("2 + 3", [X, NP, K])
    s30 = _ir("Sum(j**2, (j, 1, 4))", [M, J])
    xmj = _ir("2 + 3", [X, M, J])
    return [
        ("padded 10*11/2 + Sum(0,(k,1,n-5)) = 56", i10, _sol("55", cp("10*11/2 + Sum(0, (k, 1, n - 5)) = 56")), NO, REF),
        ("padded antiderivative", i5, _sol("5", cp("Integral(cos(x), x) = -sin(x) + Sum(0, (k, 1, n - 5))")), NO, REF),
        ("A1 +Sum(0,(j,2,m))", s30, _sol("30", cp("1 + 4 + 9 + 16 + Sum(0, (j, 2, m)) = 31")), NO, REF),
        ("A2 posint +Sum(0,(j,1,m-7))", _ir("Sum(j**2, (j, 1, 4))", [MP, J]),
         _sol("30", cp("1 + 4 + 9 + 16 + Sum(0, (j, 1, m - 7)) = 31")), NO, REF),
        ("A3 m>=10 constraint", _ir("Sum(j**2, (j, 1, 4))", [{"name": "m", "domain": "integer", "constraints": ["m >= 10"]}, J]),
         _sol("30", cp("1 + 4 + 9 + 16 + Sum(0, (j, 1, m)) = 31")), NO, REF),
        ("A4 *Product(1,(j,1,m))", _ir("6*7", [M, J]), _sol("42", cp("6*7*Product(1, (j, 1, m)) = 43")), NO, REF),
        ("A5 Sum(j-j,(j,1,m))", _ir("6*7", [M, J]), _sol("42", cp("6*7 + Sum(j - j, (j, 1, m)) = 41")), NO, REF),
        ("A6 diff wrong + Sum0", xmj, _sol("5", cp("diff(x**3, x) = 2*x**2 + Sum(0, (j, 1, m))")), NO, REF),
        ("A7 closed integral wrong + Sum0", xmj, _sol("5", cp("Integral(x, (x, 0, 2)) = 3 + Sum(0, (j, 1, m))")), NO, REF),
        ("A8 antiderivative wrong + Sum0", xmj, _sol("5", cp("Integral(2*x, x) = x**3 + Sum(0, (j, 1, m))")), NO, REF),
        ("A9 LaTeX sum 0", s30, _sol("30", cp(r"1 + 4 + 9 + 16 + \sum_{j=1}^{m} 0 = 31")), NO, REF),
        ("A10 limit DNE + Sum0", xmj, _sol("5", cp("Limit(1/x, x, 0) = 7 + Sum(0, (j, 1, m))")), NO, REF),
        ("A11 x-identity wrong + Sum0", xmj, _sol("5", cp("(x + 1)**2 = x**2 + 1 + Sum(0, (j, 1, m))")), NO, REF),
        # a definitional claim with a symbol nothing constrains: skipped, as before (the verifier's B1)
        ("B1 eq x = 4 + Sum0 given x = 5", _ir("x + 1", [X, M, J], ["x = 5"]), _sol("6", eq("x = 4 + Sum(0, (j, 1, m))")),
         OK, {"skipped"}),
        ("B3 2+2+Sum(1,(j,1,n))-n = 5", _ir("2 + 2", [N, J]), _sol("4", cp("2 + 2 + Sum(1, (j, 1, n)) - n = 5")), NO, REF),
        ("B4 Sum(j,(j,1,m)) = m(m+1)/2 + 1", _ir("2 + 2", [M, J]), _sol("4", cp("Sum(j, (j, 1, m)) = m*(m + 1)/2 + 1")),
         NO, REF),
        ("B6 given m = 7: 30 + Sum(0,(j,1,m)) = 31", _ir("x + 1", [X, M, J], ["x = 5", "m = 7"]),
         _sol("6", cp("30 + Sum(0, (j, 1, m)) = 31")), NO, REF),
        ("B8 two steps, the first wrong", _ir("Sum(j, (j, 1, 10))", [M, J]),
         _sol("55", [("compute", "10*11/2 + Sum(0, (j, 1, m)) = 56"), ("compute", "56 - 1 = 55")]), NO, None),
        # the refutation depends on the reading: withdrawn (part 11 stays)
        ("Sum(1,(j,1,n)) = Max(n, 0): Karr only", _ir("2 + 2", [N, J]), _sol("4", cp("Sum(1, (j, 1, n)) = Max(n, 0)")),
         NOTNO, NOTREF),
        ("part 11: n = 1, eq Sum(k,(k,3,n)) = 0", _ir("x + 1", [X, K, N], ["x = 5", "n = 1"]),
         _sol("6", eq("Sum(k, (k, 3, n)) = 0")), NOTNO, NOTREF),
        ("part 11: n = -2 alone, eq Sum(k,(k,1,n)) = 0", _ir("n + 1", [K, N], ["n = -2"]),
         _sol("-1", eq("Sum(k, (k, 1, n)) = 0")), NOTNO, NOTREF),
        ("part 11: n = 1, compute floor(Sum(k,(k,3,n))) = 7", _ir("x + 1", [X, K, N], ["x = 5", "n = 1"]),
         _sol("6", cp("floor(Sum(k, (k, 3, n))) = 7")), NOTNO, UNKS),
        # pinned to n = -3 the claim has a numerically reversed range, which the parser does not read
        # (`_refuse_reversed_ranges`, part 11): unknown before and after, never refuted with Karr's value
        ("n = -3, Sum(0,(k,1,n)) + 1 = 2 (both readings 0)", _ir("x + 1", [X, K, N], ["x = 5", "n = -3"]),
         _sol("6", cp("Sum(0, (k, 1, n)) + 1 = 2")), NOTNO, NOTREF),
        # a random point of the identity check where the range runs backwards (n given only as n < 0):
        # Sum(0, ...) has the same value under both readings, so the refutation stands
        ("n < 0: compute Sum(0,(k,1,n)) + x = x + 1", _ir("x + 1", [X, K, N], ["n < 0"]),
         _sol("x + 1", cp("Sum(0, (k, 1, n)) + x = x + 1"), kind="expression"), NO, REF),
    ]


def cases_c():
    ex = _ir(None, [{"name": "x"}], kind="extremum",
             params={"f": "Abs(x) + x**2", "var": "x", "interval": "[1, 3]", "which": "max"})
    di = _ir(None, [{"name": "x"}], kind="definite_integral",
             params={"integrand": "Abs(x)", "var": "x", "a": "0", "b": "2"})
    return [
        ("extremum [1,3]: diff(|x| + x**2) = 1 + 2x", ex,
         _sol("12", [("compute", "diff(Abs(x) + x**2, x) = 1 + 2*x"), ("compute", "3 + 9 = 12")]), NOTNO, None),
        ("extremum [1,3]: only the derivative step", ex, _sol("12", cp("diff(Abs(x) + x**2, x) = 1 + 2*x")), NOTNO, NOTREF),
        ("integral [0,2]: compute |x| = x", di,
         _sol("2", [("compute", "Abs(x) = x"), ("compute", "Integral(x, (x, 0, 2)) = 2")]), NOTNO, None),
        ("integral [0,2]: only compute |x| = x", di, _sol("2", cp("Abs(x) = x")), NOTNO, NOTREF),
        ("integral [0,2]: Integral(|x|, x) = x**2/2", di, _sol("2", cp("Integral(Abs(x), x) = x**2/2")), NOTNO, NOTREF),
        ("integral [0,2]: eq |x| = x", di, _sol("2", eq("Abs(x) = x")), NOTNO, NOTREF),
        # controls: wrong inside the interval still refuted
        ("ctrl extremum [1,3]: diff(|x| + x**2) = 2x", ex, _sol("12", cp("diff(Abs(x) + x**2, x) = 2*x")), NO, REF),
        ("ctrl integral [0,2]: compute |x| = -x", di, _sol("2", cp("Abs(x) = -x")), NO, REF),
        ("ctrl integral [0,2]: Integral(|x|, x) = x**3", di, _sol("2", cp("Integral(Abs(x), x) = x**3")), NO, REF),
    ]


def cases_d():
    cub = _ir("x**3 - 3*x", [X], ["x**3 - 3*x + 1 = 0"])
    return [
        ("cubic premise: x**3 - 3x = -1", cub, _sol("-1", cp("x**3 - 3*x = -1")), NOTNO, NOTREF, 60),
        ("cubic premise: two steps", cub, _sol("-1", [("compute", "x**3 - 3*x = -1"), ("compute", "x**3 = 3*x - 1")]),
         NOTNO, NOTREF, 120),
    ]


def cases_e():
    neg = _ir("n", [N, K], ["n < 0", "n > -4"])
    return [
        ("n < 0, n > -4: Sum(k,(k,1,n)) = n(n+1)/2", neg, _sol("n", cp("Sum(k, (k, 1, n)) = n*(n + 1)/2"), kind="expression"),
         ANY, UNKS),
        ("n integer: Sum(k,(k,1,n)) = n(n+1)/2", _ir("n", [N, K]),
         _sol("n", cp("Sum(k, (k, 1, n)) = n*(n + 1)/2"), kind="expression"), ANY, UNKS),
        ("n integer: Product(2,(k,1,n)) = 2**n", _ir("n", [N, K]),
         _sol("n", cp("Product(2, (k, 1, n)) = 2**n"), kind="expression"), ANY, UNKS),
        # controls
        ("ctrl n positive: Sum(k,(k,1,n)) = n(n+1)/2", _ir("n", [NP, K]),
         _sol("n", cp("Sum(k, (k, 1, n)) = n*(n + 1)/2"), kind="expression"), ANY, VER),
        ("ctrl n integer, n > 0 given: Sum(k,(k,1,n)) = n(n+1)/2", _ir("n", [N, K], ["n > 0"]),
         _sol("n", cp("Sum(k, (k, 1, n)) = n*(n + 1)/2"), kind="expression"), ANY, VER),
        ("ctrl n integer: Sum(0,(k,1,n)) = 0", _ir("n", [N, K]), _sol("n", cp("Sum(0, (k, 1, n)) = 0"), kind="expression"),
         ANY, VER),
        ("ctrl n nonneg: Product(2,(k,1,n)) = 2**n", _ir("n", [{"name": "n", "domain": "nonneg_integer"}, K]),
         _sol("n", cp("Product(2, (k, 1, n)) = 2**n"), kind="expression"), ANY, VER),
    ]


def cases_f():
    sq = _ir("x", [X], ["x**2 = 4"])
    one = _ir("x", [X], ["x**2 = 1"])
    return [
        ("x**2 = 4: compute sqrt(x**3) = x*sqrt(x)", sq, _sol("x", cp("sqrt(x**3) = x*sqrt(x)")), NOTNO, NOTREF),
        ("x**2 = 4: eq sqrt(x**3) = x*sqrt(x)", sq, _sol("x", eq("sqrt(x**3) = x*sqrt(x)")), NOTNO, NOTREF),
        ("x**2 = 1: compute log(x**2) = 2*log(x)", one, _sol("x", cp("log(x**2) = 2*log(x)")), NOTNO, NOTREF),
        ("no premise: compute sqrt(x**3) = x*sqrt(x)", _ir("x", [X]), _sol("x", cp("sqrt(x**3) = x*sqrt(x)")), NOTNO, NOTREF),
        # controls: defined at the counterexample
        ("ctrl x**2 = 4: compute sqrt(x**2) = x", sq, _sol("x", cp("sqrt(x**2) = x")), NO, REF),
        ("ctrl x**2 = 1: compute log(x**2) = 2*log(x) + 1", one, _sol("x", cp("log(x**2) = 2*log(x) + 1")), NO, REF),
        ("ctrl no premise: log(x**2) = 2*log(x) + 1", _ir("x", [X]), _sol("x", cp("log(x**2) = 2*log(x) + 1")), NO, REF),
        ("ctrl no premise: sqrt(x**2) = x", _ir("x", [X]), _sol("x", cp("sqrt(x**2) = x")), NO, REF),
    ]


def cases_g():
    rng = _ir("x", [{"name": "x", "domain": "integer"}], ["x >= -1", "x <= 10"])
    two = _ir("x", [X, Y], ["x**2 = 4", "y**2 = 1"])
    tan = _ir("x + 1", [{"name": "x"}, {"name": "y"}], ["x = 0"])
    big = _ir("x", [{"name": "x", "domain": "integer"}], ["x >= -100", "x <= 100"])
    huge = _ir("x", [{"name": "x", "domain": "integer"}], ["x >= -1000", "x <= 1000"])
    return [
        ("Range -1..10: compute x/x = 1", rng, _sol("1", cp("x/x = 1")), ANY, UNKS),
        ("Range -1..10: eq x/x = 1", rng, _sol("1", eq("x/x = 1")), ANY, UNKS),
        ("x**2 = 4, y**2 = 1: eq sqrt(x)**2 + sqrt(y)**2 = x + y", two, _sol("1", eq("sqrt(x)**2 + sqrt(y)**2 = x + y")),
         ANY, UNKS),
        ("x = 0, y free: eq x/x + sqrt(y) - sqrt(y) = 1", tan, _sol("1", eq("x/x + sqrt(y) - sqrt(y) = 1")), ANY, UNKS),
        ("x = 0: eq x/x = 1", tan, _sol("1", eq("x/x = 1")), ANY, UNKS),
        ("Range -100..100: eq x/x = 1", big, _sol("1", eq("x/x = 1")), ANY, UNKS),
        ("Range -1000..1000: eq x/x = 1", huge, _sol("1", eq("x/x = 1")), ANY, UNKS),
        ("x = 0, y free: compute x/x + y = 1 + y", tan, _sol("1", cp("x/x + y = 1 + y")), ANY, UNKS),
        # controls: defined at every point the premises allow
        ("ctrl Range 1..10: eq x/x = 1", _ir("x", [{"name": "x", "domain": "integer"}], ["x >= 1", "x <= 10"]),
         _sol("1", eq("x/x = 1")), ANY, VER),
        ("ctrl x > 0: eq sqrt(x)**2 = x", _ir("x", [X], ["x > 0"]), _sol("x", eq("sqrt(x)**2 = x")), ANY, VER),
        ("ctrl x = 2, y free: eq x/x + y = 1 + y", _ir("x + 1", [{"name": "x"}, {"name": "y"}], ["x = 2"]),
         _sol("3", eq("x/x + y = 1 + y")), ANY, NOTREF),          # the eq route leaves it unknown, before too
        ("ctrl no premise: eq x/x = 1", _ir("x", [X]), _sol("x", eq("x/x = 1")), ANY, VER),
        ("ctrl x**2 = 4, y**2 = 1: eq sqrt(x**2) + y**2 = Abs(x) + 1", two,
         _sol("1", eq("sqrt(x**2) + y**2 = Abs(x) + 1")), ANY, VER),
    ]


def cases_k():
    return [
        ("closed wrong: compute 10*11/2 = 56", _ir("Sum(k, (k, 1, 10))", [NP, K]), _sol("55", cp("10*11/2 = 56")), NO, REF),
        ("closed right: compute 10*11/2 = 55", _ir("Sum(k, (k, 1, 10))", [NP, K]), _sol("55", cp("10*11/2 = 55")), OK, VER),
        ("identity right: (x+1)**2 = x**2+2x+1", _ir("2 + 2", [X]), _sol("4", cp("(x + 1)**2 = x**2 + 2*x + 1")), OK, VER),
        ("identity wrong: (x+1)**2 = x**2+1", _ir("2 + 2", [X]), _sol("4", cp("(x + 1)**2 = x**2 + 1")), NO, REF),
        ("antiderivative right: Integral(2x, x) = x**2", _ir("2 + 2", [X]), _sol("4", cp("Integral(2*x, x) = x**2")), OK, VER),
        ("n**2 = 4, n > 0: compute n**3 = 8", _ir("n**3", [N], ["n**2 = 4", "n > 0"]), _sol("8", cp("n**3 = 8")), OK, VER),
        ("x > 0: compute Abs(x) = x", _ir("2 + 2", [X], ["x > 0"]), _sol("4", cp("Abs(x) = x")), OK, VER),
        ("n = 3: compute Sum(k,(k,1,n)) = 6", _ir("n*(n + 1)/2", [NP, K], ["n = 3"]), _sol("6", cp("Sum(k, (k, 1, n)) = 6")),
         OK, VER),
        ("n = 3: compute Sum(k,(k,1,n)) = 7", _ir("n*(n + 1)/2", [NP, K], ["n = 3"]), _sol("6", cp("Sum(k, (k, 1, n)) = 7")),
         NO, REF),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g,
          "K": cases_k}


def main(out_path=None, groups="ABCDEFGK"):
    import os
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    rows = []
    bad = 0
    t0 = time.time()
    for g in groups:
        for case in GROUPS[g]():
            label, ir, sol, verdicts, statuses = case[:5]
            limit = case[5] if len(case) > 5 else None
            t = time.time()
            try:
                r = verify(ir, sol)
                verdict = r.verdict
                layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                steps = layer.evidence.get("steps", []) if layer is not None else []
                last = steps[-1] if steps else {}
                status = last.get("status")
                lev = last.get("evidence") or {}
                detail = {k: lev[k] for k in ("counterexample", "reason", "pinned_by_premises") if k in lev}
                if last.get("reason"):
                    detail["step_reason"] = last["reason"]
                if len(steps) > 1:
                    detail["all"] = [s.get("status") for s in steps]
            except Exception as e:  # noqa: BLE001
                verdict, status, detail = f"EXC {type(e).__name__}: {e}", None, {}
            secs = round(time.time() - t, 2)
            ok = verdict in verdicts and (statuses is None or status in statuses) and (limit is None or secs <= limit)
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": verdict, "status": status, "ok": ok,
                         "detail": json.loads(json.dumps(detail, default=str)), "s": secs})
            print(f"{'ok ' if ok else 'BAD'} {g} {verdict:9} {str(status):9} {secs:6.1f}s {label}  {detail}", flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else None
    grp = args[1] if len(args) > 1 else "ABCDEFGK"
    sys.exit(1 if main(out, grp) else 0)
