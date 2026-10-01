"""Part (v-b B) of the 30 Sep 2026 fixes (HANDOFF V16, DECISIONS §73 "Açık kalanlar"): definedness and
step items of V16.

    A  a binder's variable kept the IR's declaration in the first condition loop (certify.domain
       _outer_nodes): with x declared positive, sqrt(-x) in ∫_{-1}^{0} sqrt(-x) dx gave the closed
       condition false, the expression was read as defined nowhere and the empty solution set certified
       (the right answer {-log 6} INCORRECT);
    B  the derivative (no point) and the antiderivative certified a function undefined because of a
       binder (x + Σ_{k=-1}^{1} k/k, 0·∫_{-2}^{-1} √t dt), and the fundamental theorem dropped the
       improper point of a parametric integral: diff(L(x), x) = -1 with L = ∫_1^x dt/t had {-1} CORRECT
       (N1's side finding, denetim/2026-09-30/n19/sonda_n19.py N1);
    C  a constant whose rationality no check decides (pi + E): the value path of gcd/lcm kept the point
       (the value x + gcd(x, 2) - gcd(2, x) at x = pi + E, the root pi + E);
    D  a step undefined as written at the premises' point was verified (x/x = 1 under x = 0), and an
       extra term undefined in another variable was ignored in a simplification (x + log(y) - log(y) as
       the simplification of x; gcd, n!, sqrt and log alike), and so was an expression defined nowhere
       (x + sqrt(-y) - sqrt(-y) with y > 0 simplified to x).

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca7b/sonda.py [out.json] [groups]

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


def _ir(kind, params, vars_=(), givens=(), shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def _sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [dict(s, text="") for s in steps]}


def _st(i, kind, claim):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": []}


XP = [{"name": "x", "domain": "positive_real"}, {"name": "y", "domain": "real"}]
KP = [{"name": "k", "domain": "positive_integer"}, {"name": "y", "domain": "real"}]


def cases_a():
    eq = lambda e, v=XP: _ir("solve_equation", {"equation": e, "var": "y"}, v, shape="set")  # noqa: E731
    e1 = eq("exp(-y) = 6 + 0*Integral(sqrt(-x), (x, -1, 0))")
    e2 = eq("y + Integral(sqrt(-x), (x, -1, 0)) = 2/3")
    e3 = eq("y + Sum(log(-x), (x, -3, -1)) = log(6)")
    e4 = eq("y + Limit(log(-x), x, -1) = 1")
    e5 = eq("y + Sum(sqrt(-k), (k, -2, -1)) = 1 + sqrt(2)", KP)
    e6 = eq("y + Sum(sqrt(-k), (k, 1, 2)) = 0", KP)
    ev = _ir("evaluate", {"expr": "Integral(sqrt(-x), (x, -1, 0))"}, XP)
    return [
        ("int sqrt(-x) (x>0 declared), exp(-y) = 6: {-log 6}", e1, _sol("{-log(6)}", "set"), NOTBAD),
        ("int sqrt(-x) (x>0 declared), exp(-y) = 6: {}", e1, _sol("{}", "set"), BAD),
        ("y + int sqrt(-x) = 2/3: {0}", e2, _sol("{0}", "set"), NOTBAD),
        ("y + int sqrt(-x) = 2/3: {}", e2, _sol("{}", "set"), BAD),
        ("y + Sum_x log(-x) = log 6: {0}", e3, _sol("{0}", "set"), NOTBAD),
        ("y + Sum_x log(-x) = log 6: {}", e3, _sol("{}", "set"), BAD),
        ("y + Limit(log(-x), x, -1) = 1: {1}", e4, _sol("{1}", "set"), NOTBAD),
        ("y + Limit(log(-x), x, -1) = 1: {}", e4, _sol("{}", "set"), BAD),
        ("y + Sum_k sqrt(-k), k>0 declared, k in [-2,-1]: {0}", e5, _sol("{0}", "set"), NOTBAD),
        ("y + Sum_k sqrt(-k), k>0 declared, k in [-2,-1]: {}", e5, _sol("{}", "set"), BAD),
        ("evaluate int sqrt(-x), x>0 declared: 2/3", ev, _sol("2/3"), NOTBAD),
        ("evaluate int sqrt(-x), x>0 declared: 0", ev, _sol("0"), BAD),
        # controls: a sum really undefined on its range stays so
        ("control y + Sum_k sqrt(-k), k in [1,2]: {}", e6, _sol("{}", "set"), NOTBAD),
        ("control y + Sum_k sqrt(-k), k in [1,2]: {0}", e6, _sol("{0}", "set"), BAD),
    ]


XK = [{"name": "x", "domain": "real"}, {"name": "k", "domain": "integer"}, {"name": "t", "domain": "real"}]
XT = [{"name": "x", "domain": "real"}, {"name": "t", "domain": "real"}]
XTP = [{"name": "x", "domain": "positive_real"}, {"name": "t", "domain": "real"}]
L = [{"name": "L", "expr": "integrate(1/t, (t, 1, x))", "args": ["x"]}]


def cases_b():
    der = lambda f, v=XK: _ir("derivative", {"f": f, "var": "x"}, v, shape="expression")  # noqa: E731
    anti = lambda f, v=XK: _ir("antiderivative", {"integrand": f, "var": "x"}, v, shape="expression")  # noqa: E731
    seq = lambda e, v=XT, fn=None: _ir("solve_equation", {"equation": e, "var": "x"}, v, shape="set",  # noqa: E731
                                       functions=fn)
    dint = _ir("definite_integral", {"integrand": "x + Sum(k/k, (k, -1, 1))", "var": "x", "a": "0", "b": "1"}, XK)
    return [
        ("derivative of x + Sum(k/k, (k,-1,1)): 1", der("x + Sum(k/k, (k, -1, 1))"), _sol("1", "expression"), BAD),
        ("derivative of x*Sum(k/k, (k,-1,1)): 3", der("x*Sum(k/k, (k, -1, 1))"), _sol("3", "expression"), BAD),
        ("derivative of x**2 + 0*Integral(sqrt(t), (t,-2,-1)): 2x", der("x**2 + 0*Integral(sqrt(t), (t, -2, -1))"),
         _sol("2*x", "expression"), BAD),
        ("antiderivative of 1 + 0*Sum(k/k, (k,-1,1)): x", anti("1 + 0*Sum(k/k, (k, -1, 1))"), _sol("x", "expression"), BAD),
        ("antiderivative of 2x + Sum(k/k,(k,-1,1)) - 3: x**2", anti("2*x + Sum(k/k, (k, -1, 1)) - 3"),
         _sol("x**2", "expression"), BAD),
        ("antiderivative of 2x*I/I, I = int_{-2}^{-1} sqrt(t): x**2",
         anti("2*x*Integral(sqrt(t), (t, -2, -1))/Integral(sqrt(t), (t, -2, -1))"), _sol("x**2", "expression"), BAD),
        ("definite integral of x + Sum(k/k) on [0,1]: 7/2", dint, _sol("7/2"), BAD),
        # N1's side finding and the fundamental theorem on a parametric integral
        ("diff(L(x), x) = -1, L = int_1^x dt/t: {-1}", seq("diff(L(x), x) = -1", fn=L), _sol("{-1}", "set"), BAD),
        ("diff(integrate(1/t, (t,1,x)), x) = -1: {-1}", seq("diff(integrate(1/t, (t, 1, x)), x) = -1"),
         _sol("{-1}", "set"), BAD),
        ("diff(Integral(1/t, (t,1,x)), x) = -1: {-1}", seq("diff(Integral(1/t, (t, 1, x)), x) = -1"),
         _sol("{-1}", "set"), BAD),
        ("evaluate diff(Integral(1/t,(t,1,x)), x) at x = -1: -1",
         _ir("evaluate", {"expr": "diff(Integral(1/t, (t, 1, x)), x)"}, XT, ["x = -1"]), _sol("-1"), BAD),
        ("diff(Integral(1/t, (t,0,x)), x) = 1, x > 0 (diverges): {1}", seq("diff(Integral(1/t, (t, 0, x)), x) = 1", XTP),
         _sol("{1}", "set"), BAD),
        ("derivative of Integral(1/t, (t,0,x)), x > 0 (diverges): 1/x", der("Integral(1/t, (t, 0, x))", XTP),
         _sol("1/x", "expression"), BAD),
        # controls
        ("control derivative of x**2 + Sum(1/(k-x), (k,1,3))", der("x**2 + Sum(1/(k - x), (k, 1, 3))"),
         _sol("2*x + 1/(1-x)**2 + 1/(2-x)**2 + 1/(3-x)**2", "expression"), OK),
        ("control derivative of x**2 + Sum(1/(k-x), (k,1,3)): 2x", der("x**2 + Sum(1/(k - x), (k, 1, 3))"),
         _sol("2*x", "expression"), NO),
        ("control derivative of Sum(k*x, (k,1,3)): 6", der("Sum(k*x, (k, 1, 3))"), _sol("6", "expression"), OK),
        ("control antiderivative of 2x: x**2", anti("2*x"), _sol("x**2", "expression"), OK),
        ("control derivative of Integral(1/t, (t,1,x)), x > 0: 1/x", der("Integral(1/t, (t, 1, x))", XTP),
         _sol("1/x", "expression"), OK),
        ("control diff(Integral(sqrt(t), (t,0,x)), x) = 2, x > 0: {4}", seq("diff(Integral(sqrt(t), (t, 0, x)), x) = 2", XTP),
         _sol("{4}", "set"), OK),
        ("control diff(Integral(log(t), (t,1,x)), x) = 0, x > 0: {1}", seq("diff(Integral(log(t), (t, 1, x)), x) = 0", XTP),
         _sol("{1}", "set"), OK),
        # (a sum inside a definite integral is not integrated numerically: UNKNOWN before this part too)
        ("control definite integral of x + Sum(k, (k,1,2)) on [0,1]: 7/2",
         _ir("definite_integral", {"integrand": "x + Sum(k, (k, 1, 2))", "var": "x", "a": "0", "b": "1"}, XK), _sol("7/2"), NOTBAD),
        # the variable of a definite integral runs over [a, b], not over its declared domain
        ("control definite integral of sqrt(-x) on [-2,-1], x > 0 declared",
         _ir("definite_integral", {"integrand": "sqrt(-x)", "var": "x", "a": "-2", "b": "-1"}, XTP),
         _sol("2*(2*sqrt(2) - 1)/3"), OK),
    ]


X = [{"name": "x"}]


def cases_c():
    ev = lambda e, g: _ir("evaluate", {"expr": e}, X, [g])  # noqa: E731
    rows = []
    for v in ("pi + E", "pi*E", "log(2) + pi"):
        rows += [
            (f"evaluate x + gcd(x,2) - gcd(2,x) at x = {v}: {v}", ev("x + gcd(x, 2) - gcd(2, x)", f"x = {v}"), _sol(v), BAD),
            (f"evaluate x + lcm(x,2) - lcm(2,x) at x = {v}: {v}", ev("x + lcm(x, 2) - lcm(2, x)", f"x = {v}"), _sol(v), BAD),
            (f"evaluate x + x! - x! at x = {v}: {v}", ev("x + factorial(x) - factorial(x)", f"x = {v}"), _sol(v), BAD),
        ]
    s1 = _ir("solve_equation", {"equation": "(x - pi - E)*(x - 1/2) = gcd(x, 2) - gcd(2, x)", "var": "x"}, X, shape="set")
    s2 = _ir("evaluate", {"expr": "x + gcd(x, 2) - gcd(2, x)"}, X, ["(x - pi - E)*(x - 1/2) = 0"])
    rows += [
        ("solve (x-pi-E)(x-1/2) = gcd(x,2)-gcd(2,x): {1/2, pi+E}", s1, _sol("{1/2, pi + E}", "set"), BAD),
        ("solve (x-pi-E)(x-1/2) = gcd(x,2)-gcd(2,x): {1/2}", s1, _sol("{1/2}", "set"), BAD),
        # the undecided solution is not dropped: 1/2 would be the only value left
        ("evaluate x + gcd(x,2) - gcd(2,x) where (x - pi - E)(x - 1/2) = 0: 1/2", s2, _sol("1/2"), BAD),
        # the condition names two symbols (not in the domain of either): read among the constraints
        ("evaluate x + y + gcd(x + y, 2) - gcd(2, x + y) at x = pi, y = E: pi + E",
         _ir("evaluate", {"expr": "x + y + gcd(x + y, 2) - gcd(2, x + y)"}, [{"name": "x"}, {"name": "y"}],
             ["x = pi", "y = E"]), _sol("pi + E"), BAD),
        # controls: a decided membership
        ("control evaluate gcd at x = 1/2: 1/2", ev("x + gcd(x, 2) - gcd(2, x)", "x = 1/2"), _sol("1/2"), OK),
        ("control evaluate x! at x = 3: 3", ev("x + factorial(x) - factorial(x)", "x = 3"), _sol("3"), OK),
        ("control evaluate gcd at x = sqrt(2) + sqrt(3)", ev("x + gcd(x, 2) - gcd(2, x)", "x = sqrt(2) + sqrt(3)"),
         _sol("sqrt(2) + sqrt(3)"), BAD),
        ("control solve (x-2)(x-1/2) = gcd(x,2)-gcd(2,x): {1/2, 2}",
         _ir("solve_equation", {"equation": "(x - 2)*(x - 1/2) = gcd(x, 2) - gcd(2, x)", "var": "x"}, X, shape="set"),
         _sol("{1/2, 2}", "set"), OK),
    ]
    return rows


XR = [{"name": "x", "domain": "real"}]
XY = [{"name": "x", "domain": "real"}, {"name": "y", "domain": "real"}]
XYP = [{"name": "x", "domain": "real"}, {"name": "y", "domain": "positive_real"}]


def cases_d():
    ev0 = _ir("evaluate", {"expr": "x + 1"}, XR, ["x = 0"])
    ev2 = _ir("evaluate", {"expr": "x + 1"}, XR, ["x = 2"])
    evr2 = _ir("evaluate", {"expr": "x + 1"}, XR, ["x = sqrt(2)"])
    evm3 = _ir("evaluate", {"expr": "x + 1"}, XR, ["x = -3"])
    evpe = _ir("evaluate", {"expr": "x"}, X, ["x = pi + E"])
    sq4 = _ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, XR, shape="set")
    evy = _ir("evaluate", {"expr": "x + y"}, XY, ["x = 1", "y = -1"])
    sim = lambda e, v=XY: _ir("simplify_expression", {"expr": e}, v, shape="expression")  # noqa: E731
    sx = sim("x")
    return [
        # steps undefined as written at the premises' point
        ("step eq x/x = 1 under x = 0", ev0, _sol("1", steps=[_st(1, "eq", "x/x = 1")]), BAD | OK),
        ("step compute x/x = 1 under x = 0", ev0, _sol("1", steps=[_st(1, "compute", "x/x = 1")]), BAD | OK),
        ("step eq sqrt(x - 3)**2 = x - 3 under x = 2", ev2, _sol("3", steps=[_st(1, "eq", "sqrt(x - 3)**2 = x - 3")]), BAD | OK),
        ("step compute log(x - 3) - log(x - 3) = 0 under x = 2", ev2,
         _sol("3", steps=[_st(1, "compute", "log(x - 3) - log(x - 3) = 0")]), BAD | OK),
        ("step eq x + gcd(x,2) - gcd(2,x) = x under x = sqrt(2)", evr2,
         _sol("1 + sqrt(2)", steps=[_st(1, "eq", "x + gcd(x, 2) - gcd(2, x) = x")]), BAD | OK),
        ("step eq x + x! - x! = x under x = -3", evm3, _sol("-2", steps=[_st(1, "eq", "x + factorial(x) - factorial(x) = x")]),
         BAD | OK),
        ("step eq x + gcd(x,2) - gcd(2,x) = pi + E under x = pi + E", evpe,
         _sol("pi + E", steps=[_st(1, "eq", "x + gcd(x, 2) - gcd(2, x) = pi + E")]), BAD | OK),
        ("step eq sqrt(x)**2 = x under x**2 = 4", sq4,
         _sol("{-2, 2}", "set", steps=[_st(1, "eq", "x**2 = 4"), _st(2, "eq", "sqrt(x)**2 = x")]), BAD | OK),
        ("step compute x + log(y) - log(y) = x under y = -1", evy, _sol("0", steps=[_st(1, "compute", "x + log(y) - log(y) = x")]),
         BAD | OK),
        ("step eq x + sqrt(y) - sqrt(y) = x under y = -1", evy, _sol("0", steps=[_st(1, "eq", "x + sqrt(y) - sqrt(y) = x")]),
         BAD | OK),
        # an extra term undefined in another variable: the claim of a simplification
        ("simplify x: claim x + log(y) - log(y)", sx, _sol("x + log(y) - log(y)", "expression"), BAD),
        ("simplify x: claim x + sqrt(y) - sqrt(y)", sx, _sol("x + sqrt(y) - sqrt(y)", "expression"), BAD),
        ("simplify x: claim x + factorial(y) - factorial(y)", sx, _sol("x + factorial(y) - factorial(y)", "expression"), BAD),
        ("simplify x: claim x + gcd(y, 2) - gcd(2, y)", sx, _sol("x + gcd(y, 2) - gcd(2, y)", "expression"), BAD),
        ("simplify x: claim x + y/y - 1", sx, _sol("x + y/y - 1", "expression"), BAD),
        ("evaluate x (no givens): claim x + log(y) - log(y)", _ir("evaluate", {"expr": "x"}, XY, shape="expression"),
         _sol("x + log(y) - log(y)", "expression"), BAD),
        # ... and an expression defined nowhere as written
        ("simplify x + sqrt(-y) - sqrt(-y), y > 0: x", sim("x + sqrt(-y) - sqrt(-y)", XYP), _sol("x", "expression"), BAD),
        ("simplify x + log(-y) - log(-y), y > 0: x", sim("x + log(-y) - log(-y)", XYP), _sol("x", "expression"), BAD),
        ("simplify x + sqrt(-y**2 - 1) - sqrt(-y**2 - 1): x", sim("x + sqrt(-y**2 - 1) - sqrt(-y**2 - 1)"), _sol("x", "expression"), BAD),
        ("simplify x + sqrt(-x**2 - 1) - sqrt(-x**2 - 1): x", sim("x + sqrt(-x**2 - 1) - sqrt(-x**2 - 1)", XR),
         _sol("x", "expression"), BAD),
        ("evaluate x + sqrt(-y) - sqrt(-y), y > 0: x", _ir("evaluate", {"expr": "x + sqrt(-y) - sqrt(-y)"}, XYP, shape="expression"),
         _sol("x", "expression"), BAD),
        # controls
        ("control step eq x/x = 1 under x = 2", ev2, _sol("3", steps=[_st(1, "eq", "x/x = 1")]), OK),
        ("control step compute sqrt(x + 2)**2 = x + 2 under x = 2", ev2,
         _sol("3", steps=[_st(1, "compute", "sqrt(x + 2)**2 = x + 2")]), OK),
        ("control simplify x**2/x: x", sim("x**2/x", XR), _sol("x", "expression"), OK),
        ("control simplify x + log(y) - log(y): x + log(y) - log(y)", sim("x + log(y) - log(y)"),
         _sol("x + log(y) - log(y)", "expression"), OK),
        ("control simplify x + log(y) - log(y): x", sim("x + log(y) - log(y)"), _sol("x", "expression"), OK),
        ("control simplify x*y/y: x", sim("x*y/y"), _sol("x", "expression"), OK),
        ("control solve x + sqrt(-y) - sqrt(-y) = 1, y > 0: {}",
         _ir("solve_equation", {"equation": "x + sqrt(-y) - sqrt(-y) = 1", "var": "x"}, XYP, shape="set"), _sol("{}", "set"), OK),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d}


def _summ(r):
    lay, steps = [], []
    for l in r.layers:
        ev = l.evidence or {}
        reason = ev.get("reason") or ev.get("why") or ev.get("error") or ""
        lay.append(f"{l.layer}:{l.verdict}{'(' + str(reason)[:140] + ')' if reason else ''}")
        if l.layer == "steps.refute":
            for s in ev.get("steps", []):
                steps.append(f"{s.get('id')}:{s.get('status')}:"
                             f"{str(s.get('reason') or (s.get('evidence') or {}).get('reason') or '')[:80]}")
    return lay, steps


# A step case also fails when a step the verifier should not prove is "verified".
STEP_NOT_VERIFIED = {
    "step eq x/x = 1 under x = 0", "step compute x/x = 1 under x = 0", "step eq sqrt(x - 3)**2 = x - 3 under x = 2",
    "step compute log(x - 3) - log(x - 3) = 0 under x = 2", "step eq x + gcd(x,2) - gcd(2,x) = x under x = sqrt(2)",
    "step eq x + x! - x! = x under x = -3", "step eq x + gcd(x,2) - gcd(2,x) = pi + E under x = pi + E",
    "step eq sqrt(x)**2 = x under x**2 = 4", "step compute x + log(y) - log(y) = x under y = -1",
    "step eq x + sqrt(y) - sqrt(y) = x under y = -1"}
STEP_VERIFIED = {"control step eq x/x = 1 under x = 2", "control step compute sqrt(x + 2)**2 = x + 2 under x = 2"}


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
        for label, ir, sol, exp in fn():
            t0 = time.perf_counter()
            try:
                r = verify(ir, sol)
                v = r.verdict
                lay, steps = _summ(r)
            except Exception as e:  # noqa: BLE001
                v, lay, steps = f"EXC {type(e).__name__}: {e}"[:200], [], []
            ok = v in exp
            if label in STEP_NOT_VERIFIED and (any(":verified:" in s for s in steps) or not steps):
                ok = False
            if label in STEP_VERIFIED and not any(":verified:" in s for s in steps):
                ok = False
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": v, "expected": sorted(exp), "ok": ok,
                         "layers": lay, "steps": steps})
            print(f"{g} | {'ok ' if ok else 'BAD'} | {v:9s} (exp {'/'.join(sorted(exp))}) | "
                  f"{time.perf_counter() - t0:5.1f}s | {label}", flush=True)
            for x in steps:
                print(f"      step {x}", flush=True)
    print(f"\n{len(rows)} cases, {bad} not as expected")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
