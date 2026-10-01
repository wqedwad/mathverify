"""Part 10 of the 30 Sep 2026 fixes: a `compute` step whose symbols the premises confine to finitely many
values (part 9's finding; before part 3 and part 8 only a single pin `s = c` was recognised).

`steps.deterministic.check_steps` checks a `compute` step as an identity in its free symbols; when that
fails it re-checks the step at the values the premises pin its symbols to (`_pins`, `base.closed_binding`),
but only for a premise of the form `s = c`. With n an integer and the givens n**2 = 4, n > 0 (n = 2) the
right step `n**3 = 8` was refuted at n = 48, no instance of the problem (principle 5): INCORRECT.

    A  premises confine the step's symbols to a finite set, the step is right there: not refuted
    B  the same, the step is wrong at one instance: refuted, at that instance
    C  a point of the set where the problem's range runs backwards (part 9, Ctx.reversed_region): no
       decision there
    D  premises that do not confine to a finite set: a refutation only at a point that satisfies them
    E  controls whose verdict must not change

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca10/sonda.py [out.json] [groups]

Lean is not needed (MATHVERIFY_LEAN_REPL=/nonexistent). Kept out of pyflakes and pytest like the rest
of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
UNK = {"UNKNOWN"}
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
VER = {"verified"}
REF = {"refuted"}
NOTREF = {"verified", "unknown", "skipped"}

N = {"name": "n", "domain": "integer"}
NP = {"name": "n", "domain": "positive_integer"}
K = {"name": "k", "domain": "integer"}
X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
S = "Sum(k, (k, 1, n))"


def _ir(expr, vars_, givens=(), kind="evaluate", shape="scalar"):
    return {"task": {"kind": kind, "params": {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, steps=(), kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def c1(claim):
    return [("compute", claim)]


# (label, ir, solution, expected verdicts, expected status of the LAST step: set or None)
def cases_a():
    return [
        ("n^2=4, n>0: n**3 = 8", _ir("n**3", [N], ["n**2 = 4", "n > 0"]), _sol("8", c1("n**3 = 8")), NOTNO, VER),
        ("n^2=4, n>0: n + 1 = 3", _ir("n + 1", [N], ["n**2 = 4", "n > 0"]), _sol("3", c1("n + 1 = 3")), NOTNO, VER),
        ("n pos, n^2=4: Sum = 3", _ir("n*(n + 1)/2", [NP], ["n**2 = 4"]), _sol("3", c1(f"{S} = 3")), NOTNO, VER),
        ("n pos, n^2=4, k decl: Sum = 3", _ir("n*(n + 1)/2", [NP, K], ["n**2 = 4"]), _sol("3", c1(f"{S} = 3")),
         NOTNO, VER),
        ("n^2=4 (both): n**4 = 16", _ir("n**4", [N], ["n**2 = 4"]), _sol("16", c1("n**4 = 16")), NOTNO, VER),
        ("n^2=4 (both): n**2 + 1 = 5", _ir("n**2 + 1", [N], ["n**2 = 4"]), _sol("5", c1("n**2 + 1 = 5")),
         NOTNO, VER),
        ("n^2=9, n>0: Sum = 6", _ir("n*(n + 1)/2", [N], ["n**2 = 9", "n > 0"]), _sol("6", c1(f"{S} = 6")),
         NOTNO, VER),
        ("n pos, n^2=9: Sum = 6 (part 8 control)", _ir("n*(n + 1)/2", [NP], ["n**2 = 9"]), _sol("6", c1(f"{S} = 6")),
         NOTNO, VER),
        ("n^2=9, n>0: Product = 6", _ir("factorial(n)", [N], ["n**2 = 9", "n > 0"]),
         _sol("6", c1("Product(k, (k, 1, n)) = 6")), NOTNO, VER),
        ("x^2-5x+6=0: x**2 - 5*x + 7 = 1", _ir("x**2 - 5*x + 7", [X], ["x**2 - 5*x + 6 = 0"]),
         _sol("1", c1("x**2 - 5*x + 7 = 1")), NOTNO, VER),
        ("x^2-5x+6=0: x*(5 - x) = 6", _ir("x*(5 - x)", [X], ["x**2 - 5*x + 6 = 0"]), _sol("6", c1("x*(5 - x) = 6")),
         NOTNO, VER),
        ("x^2-5x+6=0, x>2: x**2 = 9", _ir("x**2", [X], ["x**2 - 5*x + 6 = 0", "x > 2"]), _sol("9", c1("x**2 = 9")),
         NOTNO, VER),
        ("x^2=2, x>0: x**4 = 4", _ir("x**4", [X], ["x**2 = 2", "x > 0"]), _sol("4", c1("x**4 = 4")), NOTNO, VER),
        ("x^2=4, y^2=9, x,y>0: x + y = 5", _ir("x + y", [X, Y], ["x**2 = 4", "y**2 = 9", "x > 0", "y > 0"]),
         _sol("5", c1("x + y = 5")), NOTNO, VER),
        ("x^2=4, y^2=9: x**2 + y**2 = 13", _ir("x**2 + y**2", [X, Y], ["x**2 = 4", "y**2 = 9"]),
         _sol("13", c1("x**2 + y**2 = 13")), NOTNO, VER),
        ("x^2=4, y=x+1, x>0: x*y = 6", _ir("x*y", [X, Y], ["x**2 = 4", "y = x + 1", "x > 0"]),
         _sol("6", c1("x*y = 6")), NOTNO, VER),
        ("x^2=4, y=x+1, x>0: y**2 = 9 (y through x)", _ir("y**2", [X, Y], ["x**2 = 4", "y = x + 1", "x > 0"]),
         _sol("9", c1("y**2 = 9")), NOTNO, VER),
        ("constraints n^2=4, n>0: n**3 = 8", _ir("n**3", [dict(N, constraints=["n**2 = 4", "n > 0"])]),
         _sol("8", c1("n**3 = 8")), NOTNO, VER),
        # a verified eq step joins the premises: x = 3 from the system, then y through x + y = 5
        ("x+y=5, x-y=1, eq x = 3: x*y = 6", _ir("x*y", [X, Y], ["x + y = 5", "x - y = 1"]),
         _sol("6", [("eq", "x = 3"), ("compute", "x*y = 6")]), NOTNO, VER),
        ("n^2=4, eq n > 0 (unproved): n**3 = 8", _ir("n**3", [N], ["n**2 = 4"]),
         _sol("8", [("eq", "n > 0"), ("compute", "n**3 = 8")]), {"INCORRECT", "UNKNOWN"}, None),
        # the problem's sign written as a chain (an And premise)
        ("n^2=4, 0 < n < 5: n**3 = 8", _ir("n**3", [N], ["n**2 = 4", "0 < n < 5"]), _sol("8", c1("n**3 = 8")),
         NOTNO, VER),
    ]


def cases_b():
    return [
        ("n^2=4, n>0: n**3 = 9", _ir("n**3", [N], ["n**2 = 4", "n > 0"]), _sol("8", c1("n**3 = 9")), NO, REF),
        ("n^2=4 (both): n**3 = 8 (false at -2)", _ir("n**4", [N], ["n**2 = 4"]), _sol("16", c1("n**3 = 8")), NO, REF),
        ("n pos, n^2=4: Sum = 4", _ir("n*(n + 1)/2", [NP], ["n**2 = 4"]), _sol("3", c1(f"{S} = 4")), NO, REF),
        ("n^2=9, n>0: Sum = 7", _ir("n*(n + 1)/2", [N], ["n**2 = 9", "n > 0"]), _sol("6", c1(f"{S} = 7")), NO, REF),
        ("x^2-5x+6=0: x**2 = 4 (false at 3)", _ir("x**2 - 5*x + 7", [X], ["x**2 - 5*x + 6 = 0"]),
         _sol("1", c1("x**2 = 4")), NO, REF),
        ("x^2-5x+6=0: x*(5 - x) = 7", _ir("x*(5 - x)", [X], ["x**2 - 5*x + 6 = 0"]), _sol("6", c1("x*(5 - x) = 7")),
         NO, REF),
        ("x^2=4, y^2=9, x,y>0: x + y = 6", _ir("x + y", [X, Y], ["x**2 = 4", "y**2 = 9", "x > 0", "y > 0"]),
         _sol("5", c1("x + y = 6")), NO, REF),
        ("x^2=4, y^2=9: x + y = 5 (false at x=-2)", _ir("x**2 + y**2", [X, Y], ["x**2 = 4", "y**2 = 9"]),
         _sol("13", c1("x + y = 5")), NO, REF),
        ("x^2=4, y=x+1, x>0: x*y = 7", _ir("x*y", [X, Y], ["x**2 = 4", "y = x + 1", "x > 0"]),
         _sol("6", c1("x*y = 7")), NO, REF),
        ("x^2=4, y=x+1 (both): y**2 = 9 (false at x=-2)", _ir("x*y", [X, Y], ["x**2 = 4", "y = x + 1"]),
         _sol("6", c1("y**2 = 9")), NO, REF),
        ("x+y=5, x-y=1, eq x = 3: x*y = 7", _ir("x*y", [X, Y], ["x + y = 5", "x - y = 1"]),
         _sol("6", [("eq", "x = 3"), ("compute", "x*y = 7")]), NO, REF),
        ("n^2=9, n>0: Product = 7", _ir("factorial(n)", [N], ["n**2 = 9", "n > 0"]),
         _sol("6", c1("Product(k, (k, 1, n)) = 7")), NO, REF),
    ]


def cases_c():
    return [
        # n = -2 runs the problem's own range backwards: no decision there
        ("n^2=4, problem Sum: Sum = 3", _ir(S, [N, K], ["n**2 = 4"]), _sol("3", c1(f"{S} = 3")), UNK, NOTREF - VER),
        ("n^2=4, problem Sum: n**4 = 16 (true at both)", _ir(S, [N, K], ["n**2 = 4"]), _sol("3", c1("n**4 = 16")),
         UNK, VER),
        ("n^2=4, problem Sum: Sum = 1 (false at 2)", _ir(S, [N, K], ["n**2 = 4"]), _sol("1", c1(f"{S} = 1")), NO, REF),
        ("n^2=4, problem Sum: n**3 = 8 (-2 reversed)", _ir(S, [N, K], ["n**2 = 4"]), _sol("3", c1("n**3 = 8")),
         UNK, NOTREF - VER),
        ("n^2=4, problem Sum: n**3 = -8 (false at 2)", _ir(S, [N, K], ["n**2 = 4"]), _sol("3", c1("n**3 = -8")), NO, REF),
        # the problem has no range; the step's own Sum runs backwards at n = -2
        ("n^2=4, no range in problem: Sum = 3", _ir("n*(n + 1)/2", [N], ["n**2 = 4"]), _sol("3", c1(f"{S} = 3")),
         NOTNO, NOTREF - VER),
        ("n^2=4, no range in problem: Sum = 1", _ir("n*(n + 1)/2", [N], ["n**2 = 4"]), _sol("3", c1(f"{S} = 1")),
         NO, REF),
        ("n^2=4, problem Sum: n**2 = 4 (true at both)", _ir(S, [N, K], ["n**2 = 4"]), _sol("3", c1("n**2 = 4")),
         UNK, VER),
        ("n^2=4, problem Product: Product = 132", _ir("Product(k + 10, (k, 1, n))", [N, K], ["n**2 = 4"]),
         _sol("132", c1("Product(k + 10, (k, 1, n)) = 132")), UNK, NOTREF - VER),
        # part 9's test: the eq step n = 2 is a pin, the existing route
        ("n^2=4, problem Sum: eq n = 2, Sum = 3 (part 9)", _ir(S, [N, K], ["n**2 = 4"]),
         _sol("3", [("eq", "n = 2"), ("compute", f"{S} = 3")]), UNK, None),
    ]


def cases_d():
    return [
        ("x>0: Abs(x) = x", _ir("Abs(x) + 1", [X], ["x > 0"]), _sol("x + 1", c1("Abs(x) = x")), NOTNO, NOTREF),
        ("x>3: sqrt(x**2) = x", _ir("sqrt(x**2)", [X], ["x > 3"]), _sol("x", c1("sqrt(x**2) = x")), NOTNO, NOTREF),
        ("n>5: Max(n, 5) = n", _ir("Max(n, 5)", [N], ["n > 5"]), _sol("n", c1("Max(n, 5) = n")), NOTNO, NOTREF),
        ("x^2>4, x>0: Abs(x) = x", _ir("Abs(x) + 1", [X], ["x**2 > 4", "x > 0"]), _sol("x + 1", c1("Abs(x) = x")),
         NOTNO, NOTREF),
        ("x>0: Abs(x) = -x", _ir("Abs(x) + 1", [X], ["x > 0"]), _sol("x + 1", c1("Abs(x) = -x")), NO, REF),
        ("x>0: Abs(x) = x + 1", _ir("Abs(x) + 1", [X], ["x > 0"]), _sol("x + 1", c1("Abs(x) = x + 1")), NO, REF),
        ("x>0: x**2 = x", _ir("x**2", [X], ["x > 0"]), _sol("x**2", c1("x**2 = x")), NO, REF),
        ("x<0: Abs(x) = x (false everywhere x<0)", _ir("Abs(x)", [X], ["x < 0"]), _sol("-x", c1("Abs(x) = x")),
         NO, REF),
        ("n>5: Max(n, 5) = 5", _ir("Max(n, 5)", [N], ["n > 5"]), _sol("n", c1("Max(n, 5) = 5")), NO, REF),
        # two symbols in one premise: nothing narrows one symbol alone
        ("x>y: Abs(x - y) = x - y", _ir("Abs(x - y)", [X, Y], ["x > y"]), _sol("x - y", c1("Abs(x - y) = x - y")),
         NOTNO, NOTREF),
        ("x>y: Abs(x - y) = y - x", _ir("Abs(x - y)", [X, Y], ["x > y"]), _sol("x - y", c1("Abs(x - y) = y - x")),
         {"INCORRECT", "UNKNOWN"}, None),
        # known limit: x > 0 follows from x > y > 0, which no premise on x alone says; refuted as before
        ("x>y, y>0: Abs(x) = x (known limit)", _ir("Abs(x) + y", [X, Y], ["x > y", "y > 0"]),
         _sol("x + y", c1("Abs(x) = x")), {"INCORRECT", "UNKNOWN"}, None),
        # more values than _MAX_INSTANCES: the region route
        ("0 <= n <= 30: Abs(n) = n", _ir("Abs(n)", [N], ["0 <= n", "n <= 30"]), _sol("n", c1("Abs(n) = n")),
         NOTNO, NOTREF),
        ("0 <= n <= 30: Abs(n - 1) = n - 1 (false at 0)", _ir("Abs(n - 1)", [N], ["0 <= n", "n <= 30"]),
         _sol("n - 1", c1("Abs(n - 1) = n - 1")), {"INCORRECT", "UNKNOWN"}, None),
    ]


def cases_e():
    return [
        ("no premise: Abs(x) = x", _ir("Abs(x)", [X]), _sol("Abs(x)", c1("Abs(x) = x")), NO, REF),
        ("no premise: (x+1)**2 = x**2 + 1", _ir("(x + 1)**2", [X], kind="simplify_expression", shape="expression"),
         _sol("x**2 + 2*x + 1", c1("(x + 1)**2 = x**2 + 1"), kind="expression"), NO, REF),
        ("n = 3: Sum = 6 (part 8)", _ir("n*(n + 1)/2", [NP], ["n = 3"]), _sol("6", c1(f"{S} = 6")), OK, VER),
        ("n = 3: Sum = 7 (part 8)", _ir("n*(n + 1)/2", [NP], ["n = 3"]), _sol("6", c1(f"{S} = 7")), NO, REF),
        ("n > 2: Sum = 6 (part 8 control)", _ir("n*(n + 1)/2", [NP], ["n > 2"]), _sol("6", c1(f"{S} = 6")), NO, REF),
        ("a = 3, a = 2: Sum(a*k) = 9 (part 8 control)", _ir("a", [{"name": "a", "domain": "real"}], ["a = 3", "a = 2"]),
         _sol("6", c1("Sum(a*k, (k, 1, 2)) = 9")), {"INCORRECT", "UNKNOWN"}, REF),
        ("x>0: x + 1 = x + 1", _ir("x + 1", [X], ["x > 0"]), _sol("x + 1", c1("x + 1 = x + 1")), NOTNO, VER),
        ("n**2 = 4, n > 0: answer 9 (wrong answer, right step)", _ir("n**3", [N], ["n**2 = 4", "n > 0"]),
         _sol("9", c1("n**3 = 8")), NO, VER),
        # five values, the step true at each and false beyond
        ("1 <= n <= 5: floor(n/6) = 0", _ir("floor(n/6)", [N], ["1 <= n", "n <= 5"]), _sol("0", c1("floor(n/6) = 0")),
         NOTNO, VER),
        ("1 <= n <= 5: floor(n/5) = 0 (false at 5)", _ir("floor(n/6)", [N], ["1 <= n", "n <= 5"]),
         _sol("0", c1("floor(n/5) = 0")), NO, REF),
        ("closed: 2 + 2 = 5", _ir("n**3", [N], ["n**2 = 4", "n > 0"]), _sol("8", c1("2 + 2 = 5")), NO, REF),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e}


def main(out_path=None, groups="ABCDE"):
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
                detail = {k: lev[k] for k in ("instances_by_premises", "counterexample", "reason", "pinned_by_premises",
                                              "premise_region") if k in lev}
                if last.get("reason"):
                    detail["step_reason"] = last["reason"]
            except Exception as e:  # noqa: BLE001
                verdict, status, detail = f"EXC {type(e).__name__}: {e}", None, {}
            ok = verdict in verdicts and (statuses is None or status in statuses)
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": verdict, "status": status, "ok": ok,
                         "detail": json.loads(json.dumps(detail, default=str)), "s": round(time.time() - t, 2)})
            print(f"{'ok ' if ok else 'BAD'} {g} {verdict:9} {str(status):9} {label}  {detail if not ok else ''}",
                  flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else None
    grp = args[1] if len(args) > 1 else "ABCDE"
    sys.exit(1 if main(out, grp) else 0)
