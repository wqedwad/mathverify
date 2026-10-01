"""Part 11 of the 30 Sep 2026 fixes: the step refuter refuted a claim at a point where a Sum/Product range
OF THE CLAIM runs backwards (hi < lo - 1), with SymPy's Karr value there (DECISIONS §80-§81: the value at
such a point is a convention, not the curriculum's).

Measured on 65b699e and again on 69d9ec2 (part 10 abstains only at the problem's own reversed points,
`Ctx.reversed_region`): with the given n = 1 the eq step `Sum(k, (k, 3, n)) = 0` (the empty-sum reading)
was refuted at {n: 1} with Karr's -2, and the solution with the right answer was INCORRECT; the same for
n = -2 and `Sum(k, (k, 1, n)) = 0`, `Product(k, (k, 3, n)) = 1`, the LaTeX `\\sum_{k=3}^{n} k = 0` and the
compute step `floor(Sum(k, (k, 3, n))) = 0` (floor evaluates the pinned Sum, so the parser's range check
never sees it). The step that writes Karr's value was already unknown (`claim_undefined_at_the_premises_point`):
the guard stopped the verification, not the refutation.

    A  a step at a point where the claim's own range runs backwards: not refuted, the verdict not INCORRECT
    B  controls: the range runs forward or is empty (hi = lo - 1); a wrong value is still refuted
    C  several premise points, one of them backwards: the forward one still refutes a wrong step, and a step
       true at the forward one is not refuted at the backwards one
    D  controls whose verdict must not change (identities, closed claims)

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca11/sonda.py [out.json] [groups]

Lean is not needed (MATHVERIFY_LEAN_REPL=/nonexistent). Kept out of pyflakes and pytest like the rest
of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
VER = {"verified"}
REF = {"refuted"}
NOTREF = {"verified", "unknown", "skipped"}
UNKS = {"unknown"}

N = {"name": "n", "domain": "integer"}
K = {"name": "k", "domain": "integer"}
X = {"name": "x", "domain": "real"}


def _ir(expr, vars_, givens=(), kind="evaluate", shape="scalar"):
    return {"task": {"kind": kind, "params": {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, steps=(), kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def eq(claim):
    return [("eq", claim)]


def cp(claim):
    return [("compute", claim)]


def x5(n):
    """x + 1 with x = 5 and the given n: the answer 6 does not depend on n (two symbols: the premises' route)."""
    return _ir("x + 1", [X, K, N], ["x = 5", f"n = {n}"])


def n_only(n):
    """n + 1 with the given n (one symbol: the premises' solution set)."""
    return _ir("n + 1", [K, N], [f"n = {n}"])


# (label, ir, solution, expected verdicts, expected status of the LAST step: set or None)
def cases_a():
    return [
        ("n=1: eq Sum(k,3,n) = 0", x5(1), _sol("6", eq("Sum(k, (k, 3, n)) = 0")), NOTNO, NOTREF),
        ("n=-2: eq Sum(k,1,n) = 0", x5(-2), _sol("6", eq("Sum(k, (k, 1, n)) = 0")), NOTNO, NOTREF),
        ("n=1: eq Product(k,3,n) = 1", x5(1), _sol("6", eq("Product(k, (k, 3, n)) = 1")), NOTNO, NOTREF),
        ("n=1: eq LaTeX sum_{k=3}^{n} k = 0", x5(1), _sol("6", eq(r"\sum_{k=3}^{n} k = 0")), NOTNO, NOTREF),
        ("n=1: compute floor(Sum(k,3,n)) = 0", x5(1), _sol("6", cp("floor(Sum(k, (k, 3, n))) = 0")), NOTNO, NOTREF),
        ("n=-2: compute floor(Sum(k,1,n)) = 0", x5(-2), _sol("6", cp("floor(Sum(k, (k, 1, n))) = 0")), NOTNO, NOTREF),
        ("n=1: compute floor(Product(k,3,n)) = 1", x5(1), _sol("6", cp("floor(Product(k, (k, 3, n))) = 1")),
         NOTNO, NOTREF),
        ("n=1: eq Sum(k,3,n) + 1 = 1", x5(1), _sol("6", eq("Sum(k, (k, 3, n)) + 1 = 1")), NOTNO, NOTREF),
        ("n=1: eq 2*Sum(k,3,n) = 0", x5(1), _sol("6", eq("2*Sum(k, (k, 3, n)) = 0")), NOTNO, NOTREF),
        ("n=1 alone: eq Sum(k,3,n) = 0", n_only(1), _sol("2", eq("Sum(k, (k, 3, n)) = 0")), NOTNO, NOTREF),
        ("n=-2 alone: eq Sum(k,1,n) = 0", n_only(-2), _sol("-1", eq("Sum(k, (k, 1, n)) = 0")), NOTNO, NOTREF),
        ("n=1 alone: compute floor(Sum(k,3,n)) = 0", n_only(1), _sol("2", cp("floor(Sum(k, (k, 3, n))) = 0")),
         NOTNO, NOTREF),
        ("n=1 alone: eq Product(k,3,n) = 1", n_only(1), _sol("2", eq("Product(k, (k, 3, n)) = 1")), NOTNO, NOTREF),
        ("n=1 alone: eq floor(Sum(k,3,n)) = 0", n_only(1), _sol("2", eq("floor(Sum(k, (k, 3, n))) = 0")),
         NOTNO, NOTREF),
        # wrong under every reading, but its value there is a convention: no counterexample (unknown)
        ("n=1: compute floor(Sum(k,3,n)) = 7", x5(1), _sol("6", cp("floor(Sum(k, (k, 3, n))) = 7")), NOTNO, UNKS),
        ("n=1: eq Sum(k,3,n) = 7", x5(1), _sol("6", eq("Sum(k, (k, 3, n)) = 7")), NOTNO, UNKS),
        # Karr's own value: unknown before and after (claim_undefined_at_the_premises_point)
        ("n=1: eq Sum(k,3,n) = -2 (Karr)", x5(1), _sol("6", eq("Sum(k, (k, 3, n)) = -2")), NOTNO, UNKS),
        ("n=1: compute floor(Sum(k,3,n)) = -2 (Karr)", x5(1), _sol("6", cp("floor(Sum(k, (k, 3, n))) = -2")),
         NOTNO, UNKS),
    ]


def cases_b():
    return [
        ("n=5: eq Sum(k,3,n) = 0", x5(5), _sol("6", eq("Sum(k, (k, 3, n)) = 0")), NO, REF),
        ("n=5: eq Sum(k,3,n) = 12", x5(5), _sol("6", eq("Sum(k, (k, 3, n)) = 12")), OK, VER),
        ("n=2: eq Sum(k,3,n) = 0 (empty sum)", x5(2), _sol("6", eq("Sum(k, (k, 3, n)) = 0")), OK, VER),
        ("n=2: eq Sum(k,3,n) = 1 (empty sum, wrong)", x5(2), _sol("6", eq("Sum(k, (k, 3, n)) = 1")), NO, REF),
        ("n=2: eq Product(k,3,n) = 1 (empty product)", x5(2), _sol("6", eq("Product(k, (k, 3, n)) = 1")), OK, VER),
        ("n=5: eq Product(k,3,n) = 1", x5(5), _sol("6", eq("Product(k, (k, 3, n)) = 1")), NO, REF),
        ("n=5: eq LaTeX sum_{k=3}^{n} k = 0", x5(5), _sol("6", eq(r"\sum_{k=3}^{n} k = 0")), NO, REF),
        ("n=5: compute floor(Sum(k,3,n)) = 0", x5(5), _sol("6", cp("floor(Sum(k, (k, 3, n))) = 0")), NO, REF),
        ("n=5: compute floor(Sum(k,3,n)) = 12", x5(5), _sol("6", cp("floor(Sum(k, (k, 3, n))) = 12")), OK, VER),
        ("n=5 alone: eq Sum(k,3,n) = 0", n_only(5), _sol("6", eq("Sum(k, (k, 3, n)) = 0")), NO, REF),
        ("n=5 alone: eq Sum(k,3,n) = 12", n_only(5), _sol("6", eq("Sum(k, (k, 3, n)) = 12")), OK, VER),
        ("n=3: eq Sum(k,3,n) = 3", x5(3), _sol("6", eq("Sum(k, (k, 3, n)) = 3")), OK, VER),
        ("n=1: eq x = 4 (no range in the claim)", x5(1), _sol("6", eq("x = 4")), NO, REF),
    ]


def cases_c():
    return [
        ("n^2=25, x=5: eq Sum(k,3,n) = 0 (false at 5)", _ir("x + 1", [X, K, N], ["x = 5", "n**2 = 25"]),
         _sol("6", eq("Sum(k, (k, 3, n)) = 0")), NO, REF),
        ("n^2=25, x=5: eq Sum(k,3,n) = 12 (true at 5)", _ir("x + 1", [X, K, N], ["x = 5", "n**2 = 25"]),
         _sol("6", eq("Sum(k, (k, 3, n)) = 12")), NOTNO, NOTREF),
        ("n^2=25 alone: eq Sum(k,3,n) = 0 (false at 5)", _ir("n**2", [K, N], ["n**2 = 25"]),
         _sol("25", eq("Sum(k, (k, 3, n)) = 0")), NO, REF),
        ("n^2=25 alone: eq Sum(k,3,n) = 12 (true at 5)", _ir("n**2", [K, N], ["n**2 = 25"]),
         _sol("25", eq("Sum(k, (k, 3, n)) = 12")), NOTNO, NOTREF),
        ("n^2=25 alone: eq floor(Sum(k,3,n)) = 0 (route 0, false at 5)", _ir("n**2", [K, N], ["n**2 = 25"]),
         _sol("25", eq("floor(Sum(k, (k, 3, n))) = 0")), NO, REF),
        ("n^2=25 alone: eq floor(Sum(k,3,n)) = 12 (route 0, true at 5)", _ir("n**2", [K, N], ["n**2 = 25"]),
         _sol("25", eq("floor(Sum(k, (k, 3, n))) = 12")), NOTNO, NOTREF),
        ("n^2=25: compute floor(Sum(k,3,n)) = 0 (false at 5)", _ir("n**2", [K, N], ["n**2 = 25"]),
         _sol("25", cp("floor(Sum(k, (k, 3, n))) = 0")), NO, REF),
        ("n^2=25: compute floor(Sum(k,3,n)) = 12 (true at 5)", _ir("n**2", [K, N], ["n**2 = 25"]),
         _sol("25", cp("floor(Sum(k, (k, 3, n))) = 12")), NOTNO, NOTREF),
        ("n^2=25: compute floor(Sum(k,3,n)) = 7 (Karr at -5, false at 5)", _ir("n**2", [K, N], ["n**2 = 25"]),
         _sol("25", cp("floor(Sum(k, (k, 3, n))) = 7")), NO, REF),
    ]


def cases_d():
    return [
        ("n free: compute Sum(k,1,n) = n**2 (wrong identity)", _ir("n**2", [K, N]),
         _sol("n**2", cp("Sum(k, (k, 1, n)) = n**2"), kind="expression"), NO, REF),
        ("closed: eq Sum(k,(k,1,4)) = 11", x5(1), _sol("6", eq("Sum(k, (k, 1, 4)) = 11")), NO, REF),
        ("closed: compute Sum(k,(k,1,4)) = 10", x5(1), _sol("6", cp("Sum(k, (k, 1, 4)) = 10")), OK, VER),
        ("n=3: compute Sum(k,1,n) = 6 (part 8)", _ir("n*(n + 1)/2", [{"name": "n", "domain": "positive_integer"}],
                                                   ["n = 3"]), _sol("6", cp("Sum(k, (k, 1, n)) = 6")), OK, VER),
        ("n=3: compute Sum(k,1,n) = 7 (part 8)", _ir("n*(n + 1)/2", [{"name": "n", "domain": "positive_integer"}],
                                                   ["n = 3"]), _sol("6", cp("Sum(k, (k, 1, n)) = 7")), NO, REF),
        ("n^2=4, n>0: compute n**3 = 8 (part 10)", _ir("n**3", [N], ["n**2 = 4", "n > 0"]), _sol("8", cp("n**3 = 8")),
         NOTNO, VER),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d}


def main(out_path=None, groups="ABCD"):
    import os
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    rows = []
    bad = 0
    t0 = time.time()
    for g in groups:
        for label, ir, sol, verdicts, statuses in GROUPS[g]():
            t = time.time()
            try:
                r = verify(ir, sol)
                verdict = r.verdict
                layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                steps = layer.evidence.get("steps", []) if layer is not None else []
                last = steps[-1] if steps else {}
                status = last.get("status")
                lev = last.get("evidence") or {}
                detail = {k: lev[k] for k in ("counterexample", "reason", "pinned_by_premises", "route",
                                              "reversed_range_points") if k in lev}
                if last.get("reason"):
                    detail["step_reason"] = last["reason"]
            except Exception as e:  # noqa: BLE001
                verdict, status, detail = f"EXC {type(e).__name__}: {e}", None, {}
            ok = verdict in verdicts and (statuses is None or status in statuses)
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": verdict, "status": status, "ok": ok,
                         "detail": json.loads(json.dumps(detail, default=str)), "s": round(time.time() - t, 2)})
            print(f"{'ok ' if ok else 'BAD'} {g} {verdict:9} {str(status):9} {label}  {detail}", flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else None
    grp = args[1] if len(args) > 1 else "ABCD"
    sys.exit(1 if main(out, grp) else 0)
