"""Part 8 of the 30 Sep 2026 fixes: a `compute` step whose symbols the givens pin, with a range binder
(DECISIONS §76 (iii) left it out).

Part (iii) re-checks a `compute` step refuted as an identity at the values the premises pin its
symbols to (`steps.deterministic._pins`, `base.closed_binding`), but only for a claim with no operation
at all. With n = 3 given, the right step `Sum(k, (k, 1, n)) = 6` was still checked as an identity in n,
refuted at a point n != 3 that is no instance of the problem (principle 5), and the verdict was
INCORRECT. The same for a Product and a definite Integral. A Limit stays out (SymPy's `Limit.subs`
replaces the bound variable too).

    A  right steps with a Sum / Product / definite Integral in pinned symbols (bound, body, both)
    B  the same steps with a wrong value: still refuted
    C  controls whose behaviour must not change: nothing pins the symbol, a Limit, an indefinite
       integral, a derivative
    D  a pinned value that makes the claim unreadable or improper (non-integer or reversed range,
       principal-value integral): never verified
    E  outside this part (an identity check that is undecided, not refuted): unchanged

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca8/sonda.py [out.json] [groups]

Lean is not needed (MATHVERIFY_LEAN_REPL=/nonexistent). Kept out of pyflakes and pytest like the rest
of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTOK = {"INCORRECT", "UNKNOWN"}      # anything but a false accept
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false reject

N = {"name": "n", "domain": "positive_integer"}
NR = {"name": "n", "domain": "real"}
K = {"name": "k", "domain": "integer"}
A = {"name": "a", "domain": "real"}
X = {"name": "x", "domain": "real"}


def _ir(expr, vars_, givens, kind="evaluate"):
    return {"task": {"kind": kind, "params": {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": "scalar"}


def _sol(payload, steps):
    return {"claimed_answer": {"kind": "value", "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


# (label, ir, solution, expected verdicts, expected status of the LAST step: set or None)
def cases_a():
    s3 = _ir("n*(n + 1)/2", [N], ["n = 3"])
    return [
        ("Sum(k,(k,1,n)) = 6, n = 3 (k bound, undeclared)", s3, _sol("6", [("compute", "Sum(k, (k, 1, n)) = 6")]),
         NOTNO, {"verified"}),
        ("Sum(k,(k,1,n)) = 6, n = 3 (k declared)", _ir("n*(n + 1)/2", [N, K], ["n = 3"]),
         _sol("6", [("compute", "Sum(k, (k, 1, n)) = 6")]), NOTNO, {"verified"}),
        ("Sum(k,(k,1,n)) = 6, n = 3, task Sum", _ir("Sum(k, (k, 1, n))", [N, K], ["n = 3"]),
         _sol("6", [("compute", "Sum(k, (k, 1, n)) = 6")]), NOTNO, {"verified"}),
        ("Product(k,(k,1,n)) = 6, n = 3", _ir("factorial(n)", [N], ["n = 3"]),
         _sol("6", [("compute", "Product(k, (k, 1, n)) = 6")]), NOTNO, {"verified"}),
        ("Integral(x,(x,0,a)) = 2, a = 2", _ir("a**2/2", [A], ["a = 2"]),
         _sol("2", [("compute", "Integral(x, (x, 0, a)) = 2")]), NOTNO, {"verified"}),
        ("Integral(x,(x,0,a)) = 2, a = 2 (x declared)", _ir("a**2/2", [A, X], ["a = 2"]),
         _sol("2", [("compute", "Integral(x, (x, 0, a)) = 2")]), NOTNO, {"verified"}),
        ("Sum(a*k,(k,1,3)) = 12, a = 2 (body)", _ir("6*a", [A], ["a = 2"]),
         _sol("12", [("compute", "Sum(a*k, (k, 1, 3)) = 12")]), NOTNO, {"verified"}),
        ("Integral(a*x,(x,0,a)) = 4, a = 2 (body and bound)", _ir("a**3/2", [A], ["a = 2"]),
         _sol("4", [("compute", "Integral(a*x, (x, 0, a)) = 4")]), NOTNO, {"verified"}),
        ("Sum(k,(k,1,n)) + n = 9, n = 3 (outside the binder too)", s3,
         _sol("6", [("compute", "Sum(k, (k, 1, n)) + n = 9")]), NOTNO, {"verified"}),
        ("n + 1 = 4 given, eq n = 3, Sum(k,(k,1,n)) = 6", _ir("n*(n + 1)/2", [N], ["n + 1 = 4"]),
         _sol("6", [("eq", "n = 3"), ("compute", "Sum(k, (k, 1, n)) = 6")]), NOTNO, {"verified"}),
        ("constraint n = 3: Sum(k,(k,1,n)) = 6", _ir("n*(n + 1)/2", [dict(N, constraints=["n = 3"])], []),
         _sol("6", [("compute", "Sum(k, (k, 1, n)) = 6")]), NOTNO, {"verified"}),
        ("a = 2: a + Sum(a,(a,1,3)) = 8 (the index is another a)", _ir("a", [{"name": "a"}], ["a = 2"]),
         _sol("2", [("compute", "a + Sum(a, (a, 1, 3)) = 8")]), NOTNO, {"verified"}),
    ]


def cases_b():
    s3 = _ir("n*(n + 1)/2", [N], ["n = 3"])
    return [
        ("Sum(k,(k,1,n)) = 7, n = 3", s3, _sol("7", [("compute", "Sum(k, (k, 1, n)) = 7")]), NO, {"refuted"}),
        ("Sum(k,(k,1,n)) = 5, n = 3", s3, _sol("5", [("compute", "Sum(k, (k, 1, n)) = 5")]), NO, {"refuted"}),
        ("Sum(k,(k,1,n)) = 7, n = 3, answer 6", s3, _sol("6", [("compute", "Sum(k, (k, 1, n)) = 7")]), NO,
         {"refuted"}),
        ("Product(k,(k,1,n)) = 7, n = 3", _ir("factorial(n)", [N], ["n = 3"]),
         _sol("6", [("compute", "Product(k, (k, 1, n)) = 7")]), NO, {"refuted"}),
        ("Integral(x,(x,0,a)) = 3, a = 2", _ir("a**2/2", [A], ["a = 2"]),
         _sol("2", [("compute", "Integral(x, (x, 0, a)) = 3")]), NO, {"refuted"}),
        ("Sum(a*k,(k,1,3)) = 13, a = 2", _ir("6*a", [A], ["a = 2"]),
         _sol("12", [("compute", "Sum(a*k, (k, 1, 3)) = 13")]), NO, {"refuted"}),
        ("Integral(a*x,(x,0,a)) = 8, a = 2", _ir("a**3/2", [A], ["a = 2"]),
         _sol("4", [("compute", "Integral(a*x, (x, 0, a)) = 8")]), NO, {"refuted"}),
        ("constraint n = 3: Sum(k,(k,1,n)) = 7", _ir("n*(n + 1)/2", [dict(N, constraints=["n = 3"])], []),
         _sol("6", [("compute", "Sum(k, (k, 1, n)) = 7")]), NO, {"refuted"}),
        ("a = 2: a + Sum(a,(a,1,3)) = 9", _ir("a", [{"name": "a"}], ["a = 2"]),
         _sol("2", [("compute", "a + Sum(a, (a, 1, 3)) = 9")]), NO, {"refuted"}),
    ]


def cases_e():
    """Outside this part, measured: the identity check of a parametric geometric series is not refuted
    but undecided (SymPy's value is a Piecewise that keeps the Sum), so the pinned re-check, which
    follows a refutation only, never runs. The wrong step "= 3" is not refuted and the right answer
    is CORRECT; unchanged here."""
    return [
        ("Sum(a**k,(k,0,oo)) = 2, a = 1/2", _ir("1/(1 - a)", [A], ["a = 1/2"]),
         _sol("2", [("compute", "Sum(a**k, (k, 0, oo)) = 2")]), OK, {"unknown"}),
        ("Sum(a**k,(k,0,oo)) = 3, a = 1/2 (wrong step, not refuted)", _ir("1/(1 - a)", [A], ["a = 1/2"]),
         _sol("2", [("compute", "Sum(a**k, (k, 0, oo)) = 3")]), OK, {"unknown"}),
    ] + _constraint_only()


def _constraint_only():
    """Outside this part, measured the same on 8d86e7c: a variable's own constraint n = 0 narrows the
    identity check's domain to {0}, where SymPy's closed form (Karr: Sum(k, (k, 2, 0)) = -1) agrees, so
    the step is verified without a refutation and the pinned re-check never runs; the definedness check
    at the premises' point does not read variable constraints. The verdict is the same as for an
    unknown step (the right answer decides)."""
    NC = lambda c: [dict(NR, constraints=[c])]  # noqa: E731
    return [
        ("constraint n = 0: Sum(k,(k,2,n)) = -1 (Karr, verified before too)", _ir("n", NC("n = 0"), []),
         _sol("0", [("compute", "Sum(k, (k, 2, n)) = -1")]), OK, {"verified"}),
        ("constraint n = 0: Product(k,(k,3,n)) = 1/2 (Karr, verified before too)", _ir("n", NC("n = 0"), []),
         _sol("0", [("compute", "Product(k, (k, 3, n)) = 1/2")]), OK, {"verified"}),
        ("constraint n = 5/2: Sum(k,(k,1,n)) = 35/8 (verified before too)", _ir("n", NC("n = 5/2"), []),
         _sol("5/2", [("compute", "Sum(k, (k, 1, n)) = 35/8")]), OK, {"verified"}),
    ]


def cases_c():
    return [
        ("no given: Sum(k,(k,1,n)) = 6 (identity, wrong)", _ir("n*(n + 1)/2", [N], []),
         _sol("6", [("compute", "Sum(k, (k, 1, n)) = 6")]), NO, {"refuted"}),
        ("n > 2 only: Sum(k,(k,1,n)) = 6", _ir("n*(n + 1)/2", [N], ["n > 2"]),
         _sol("6", [("compute", "Sum(k, (k, 1, n)) = 6")]), NO, {"refuted"}),
        ("n**2 = 9 only (not a closed binding): Sum(k,(k,1,n)) = 6", _ir("n*(n + 1)/2", [N], ["n**2 = 9"]),
         _sol("6", [("compute", "Sum(k, (k, 1, n)) = 6")]), NO, {"refuted"}),
        ("solver's own n = 3, no given: Sum(k,(k,1,n)) = 6", _ir("n*(n + 1)/2", [N], []),
         _sol("6", [("eq", "n = 3"), ("compute", "Sum(k, (k, 1, n)) = 6")]), NO, {"refuted"}),
        # a Limit stays out: measured on 8d86e7c, must not change
        ("Limit(a*x, x, 1) = 2, a = 2 (Limit left out)", _ir("a", [A], ["a = 2"]),
         _sol("2", [("compute", "Limit(a*x, x, 1) = 2")]), OK, {"unknown"}),
        ("Limit(x**2, x, a) = 4, a = 2 (Limit left out)", _ir("a", [A], ["a = 2"]),
         _sol("2", [("compute", "Limit(x**2, x, a) = 4")]), OK, {"unknown"}),
        ("a*Limit(x**2, x, 1) = 2, a = 2 (Limit left out, refuted as before)", _ir("a", [A], ["a = 2"]),
         _sol("2", [("compute", "a*Limit(x**2, x, 1) = 2")]), NO, {"refuted"}),
        ("a + Limit(x, x, 1) = 3, a = 2 (Limit left out, refuted as before)", _ir("a", [A, X], ["a = 2"]),
         _sol("2", [("compute", "a + Limit(x, x, 1) = 3")]), NO, {"refuted"}),
        ("Sum(k,(k,1,n)) + Limit(x, x, 1) = 7, n = 3 (Limit left out)", _ir("n", [N], ["n = 3"]),
         _sol("3", [("compute", "Sum(k, (k, 1, n)) + Limit(x, x, 1) = 7")]), OK, {"unknown"}),
        ("Derivative(a*x**2, x) = 4*x, a = 2 (derivative left out)", _ir("a", [A, X], ["a = 2"]),
         _sol("2", [("compute", "Derivative(a*x**2, x) = 4*x")]), NO, {"refuted"}),
        ("Integral(a*x, x) = x**2, a = 2 (indefinite)", _ir("a", [A, X], ["a = 2"]),
         _sol("2", [("compute", "Integral(a*x, x) = x**2")]), OK, {"unknown"}),
        ("Sum(k,(k,1,3)) = 6, closed (control)", _ir("6", [], []),
         _sol("6", [("compute", "Sum(k, (k, 1, 3)) = 6")]), NOTNO, {"verified"}),
        ("a*b = 6, a = 3, b = 2 (part iii, control)", _ir("a*b", [A, {"name": "b", "domain": "real"}],
                                                          ["a = 3", "b = 2"]),
         _sol("6", [("compute", "a*b = 6")]), NOTNO, {"verified"}),
    ]


ANY = {"CORRECT", "INCORRECT", "UNKNOWN"}
NOT_VERIFIED = {"refuted", "unknown"}


def cases_d():
    """The answer is right, so the verdict follows the step: a pinned value that makes the claim
    unreadable (a Sum over a range not an integer long, or reversed: Karr's -1 for Sum(k, (k, 2, 0)))
    or improper must never verify it. Pinned by a given, the definedness check at the premises' point
    also sees it; pinned by the variable's own constraint, only the pinned re-check does."""
    NC = lambda c: [dict(NR, constraints=[c])]  # noqa: E731
    AC = lambda c: [dict(A, constraints=[c])]  # noqa: E731
    return [
        ("n = 5/2: Sum(k,(k,1,n)) = 35/8 (not an integer apart)", _ir("n", [NR], ["n = 5/2"]),
         _sol("5/2", [("compute", "Sum(k, (k, 1, n)) = 35/8")]), ANY, NOT_VERIFIED),
        ("n = sqrt(2): Sum(k,(k,1,n)) = 1", _ir("n", [NR], ["n = sqrt(2)"]),
         _sol("sqrt(2)", [("compute", "Sum(k, (k, 1, n)) = 1")]), ANY, NOT_VERIFIED),
        ("n = 0: Sum(k,(k,2,n)) = -1 (Karr, reversed)", _ir("n", [NR], ["n = 0"]),
         _sol("0", [("compute", "Sum(k, (k, 2, n)) = -1")]), ANY, NOT_VERIFIED),
        ("n = 0: Product(k,(k,3,n)) = 1/2 (Karr)", _ir("n", [NR], ["n = 0"]),
         _sol("0", [("compute", "Product(k, (k, 3, n)) = 1/2")]), ANY, NOT_VERIFIED),
        ("constraint n = 0, a = 1: Sum(a*k,(k,2,n)) = -1 (Karr; only the re-check sees it)",
         _ir("a", NC("n = 0") + [A], ["a = 1"]), _sol("1", [("compute", "Sum(a*k, (k, 2, n)) = -1")]),
         ANY, NOT_VERIFIED),
        ("constraint n = 5/2, a = 1: Sum(a*k,(k,1,n)) = 35/8 (only the re-check sees it)",
         _ir("a", NC("n = 5/2") + [A], ["a = 1"]), _sol("1", [("compute", "Sum(a*k, (k, 1, n)) = 35/8")]),
         ANY, NOT_VERIFIED),
        ("a = 1: Integral(1/x,(x,-1,a)) = 0 (principal value)", _ir("a", [A], ["a = 1"]),
         _sol("1", [("compute", "Integral(1/x, (x, -1, a)) = 0")]), ANY, NOT_VERIFIED),
        ("constraint a = 1: Integral(1/x,(x,-1,a)) = 0", _ir("a", AC("a = 1"), []),
         _sol("1", [("compute", "Integral(1/x, (x, -1, a)) = 0")]), ANY, NOT_VERIFIED),
        ("a = 0: Integral(1/x,(x,a,1)) = oo (divergent)", _ir("a", [A], ["a = 0"]),
         _sol("0", [("compute", "Integral(1/x, (x, a, 1)) = oo")]), ANY, NOT_VERIFIED),
        ("a = -1: Integral(sqrt(x),(x,a,1)) = 2/3 (undefined on part)", _ir("a", [A], ["a = -1"]),
         _sol("-1", [("compute", "Integral(sqrt(x), (x, a, 1)) = 2/3")]), ANY, NOT_VERIFIED),
        ("constraint a = -1: Integral(sqrt(x),(x,a,1)) = 2/3", _ir("a", AC("a = -1"), []),
         _sol("-1", [("compute", "Integral(sqrt(x), (x, a, 1)) = 2/3")]), ANY, NOT_VERIFIED),
        ("a = 1: Integral(1/(x - a),(x,0,2)) = 0 (pole inside, principal value)", _ir("a", [A], ["a = 1"]),
         _sol("1", [("compute", "Integral(1/(x - a), (x, 0, 2)) = 0")]), ANY, NOT_VERIFIED),
        ("a = 2: Sum(1/(k - a),(k,1,3)) = 0 (a term undefined)", _ir("a", [A], ["a = 2"]),
         _sol("2", [("compute", "Sum(1/(k - a), (k, 1, 3)) = 0")]), ANY, NOT_VERIFIED),
        ("a = 2: Product(k - a,(k,1,3)) = 0 (a zero factor, defined)", _ir("a", [A], ["a = 2"]),
         _sol("2", [("compute", "Product(k - a, (k, 1, 3)) = 0")]), ANY, {"verified"}),
        ("a = 3 and a = 2: Sum(a*k,(k,1,2)) = 9 (two values)", _ir("a", [A], ["a = 3", "a = 2"]),
         _sol("3", [("compute", "Sum(a*k, (k, 1, 2)) = 9")]), ANY, {"refuted"}),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e}


def _summ(r):
    lay, steps = [], []
    for l in r.layers:
        ev = l.evidence or {}
        reason = ev.get("reason") or ""
        lay.append(f"{l.layer}:{l.verdict}{'(' + str(reason)[:120] + ')' if reason else ''}")
        if l.layer == "steps.refute":
            for s in ev.get("steps", []):
                steps.append((s.get("id"), s.get("status"),
                              str(s.get("reason") or (s.get("evidence") or {}).get("reason") or "")[:80],
                              bool((s.get("evidence") or {}).get("pinned_by_premises"))))
    return lay, steps


def main():
    import mathverify
    from mathverify.verifier import verify
    print(f"mathverify: {mathverify.__file__}", flush=True)
    out_path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".json") else None
    only = {a for a in sys.argv[1:] if not a.endswith(".json")}
    rows, bad = [], 0
    for g, fn in GROUPS.items():
        if only and g not in only:
            continue
        for label, ir, sol, exp, last in fn():
            t0 = time.perf_counter()
            try:
                r = verify(ir, sol)
                v = r.verdict
                lay, steps = _summ(r)
            except Exception as e:  # noqa: BLE001
                v, lay, steps = f"EXC {type(e).__name__}: {e}"[:200], [], []
            ok = v in exp and (last is None or (bool(steps) and steps[-1][1] in last))
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": v, "expected": sorted(exp), "ok": ok,
                         "layers": lay, "steps": [list(s) for s in steps]})
            print(f"{g} | {'ok ' if ok else 'BAD'} | {v:9s} (exp {'/'.join(sorted(exp))}) | "
                  f"{time.perf_counter() - t0:5.1f}s | {label}", flush=True)
            for s in steps:
                print(f"      step {s[0]}:{s[1]}:{s[2]}{' pinned' if s[3] else ''}", flush=True)
    print(f"\n{len(rows)} cases, {bad} not as expected")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
