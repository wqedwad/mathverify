"""Part (v-a) of the 30 Sep 2026 fixes (HANDOFF V17, DECISIONS §74): the two false accepts `franklin`'s
completeness audit found and the U04 test gap.

    T  the family parameter of a trig general solution took the IR's declaration of k/n/m
       (k a positive integer: {Abs(k)*pi} for sin x = 0 was CORRECT);
    D  a derivative in a variable declared an integer, inside an expression or a step
       (n a positive integer: diff(sin(pi*n), n) was 0, so 0 was CORRECT at n = 2 and pi INCORRECT);
    U  an endpoint pair unify_endpoints cannot decide is refused (the U04 mutant accepted
       (-oo, 3) U (sqrt(9 + exp(-10000)), oo) as the domain of 1/(x - 3)).

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca5/sonda.py [out.json]

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


def _ir(kind, params, vars_=(), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [dict(s, text="") for s in steps]}


def _st(i, kind, claim, frm=()):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": list(frm)}


X = {"name": "x", "domain": "real"}


def _trig(eq, par=None, dom=None, interval=None):
    vars_ = [X] + ([{"name": par, "domain": dom}] if dom else [])
    p = {"equation": eq, "var": "x"}
    if interval:
        p["interval"] = interval
    return _ir("trig_solve", p, vars_, shape="set")


def cases_t():
    rows = []
    for dom in ("positive_integer", "natural", "nonneg_integer"):
        rows += [
            (f"sin x = 0, k {dom}, {{Abs(k)*pi}}", _trig("sin(x) = 0", "k", dom), _sol("{Abs(k)*pi}", "set"), BAD),
            (f"sin x = 0, k {dom}, {{sqrt(k**2)*pi}}", _trig("sin(x) = 0", "k", dom), _sol("{sqrt(k**2)*pi}", "set"), BAD),
            (f"sin x = 0, k {dom}, value Abs(k)*pi", _trig("sin(x) = 0", "k", dom), _sol("Abs(k)*pi"), BAD),
            (f"cos x = 1, k {dom}, {{2*pi*Abs(k)}}", _trig("cos(x) = 1", "k", dom), _sol("{2*pi*Abs(k)}", "set"), BAD),
            (f"cos x = 1, n {dom}, {{2*pi*sqrt(n**2)}}", _trig("cos(x) = 1", "n", dom), _sol("{2*pi*sqrt(n**2)}", "set"), BAD),
            (f"cos x = 1, n {dom}, {{2*pi*Max(n, 0)}}", _trig("cos(x) = 1", "n", dom), _sol("{2*pi*Max(n, 0)}", "set"), BAD),
            (f"cos x = 1, m {dom}, {{2*pi*Abs(m)}}", _trig("cos(x) = 1", "m", dom), _sol("{2*pi*Abs(m)}", "set"), BAD),
            # the right families stay CORRECT whatever the IR declares
            (f"sin x = 0, k {dom}, {{k*pi}}", _trig("sin(x) = 0", "k", dom), _sol("{k*pi}", "set"), OK),
            (f"cos x = 1, k {dom}, {{2*k*pi}}", _trig("cos(x) = 1", "k", dom), _sol("{2*k*pi}", "set"), OK),
            (f"cos x = 1, n {dom}, {{2*n*pi}}", _trig("cos(x) = 1", "n", dom), _sol("{2*n*pi}", "set"), OK),
            (f"cos x = 1, m {dom}, {{2*m*pi}}", _trig("cos(x) = 1", "m", dom), _sol("{2*m*pi}", "set"), OK),
            (f"sin x = 0, k {dom}, {{2*k*pi}} (half)", _trig("sin(x) = 0", "k", dom), _sol("{2*k*pi}", "set"), NO),
        ]
    for dom in ("integer", "real", None):
        tag = dom or "undeclared"
        rows += [
            (f"sin x = 0, k {tag}, {{Abs(k)*pi}}", _trig("sin(x) = 0", "k", dom), _sol("{Abs(k)*pi}", "set"), BAD),
            (f"sin x = 0, k {tag}, {{k*pi}}", _trig("sin(x) = 0", "k", dom), _sol("{k*pi}", "set"), OK),
            (f"sin x = 0, k {tag}, {{2*k*pi}}", _trig("sin(x) = 0", "k", dom), _sol("{2*k*pi}", "set"), NO),
            (f"cos x = 1, n {tag}, {{2*n*pi}}", _trig("cos(x) = 1", "n", dom), _sol("{2*n*pi}", "set"), OK),
        ]
    rows += [
        ("sin x = 1/2, k positive_integer, two families", _trig("sin(x) = 1/2", "k", "positive_integer"),
         _sol("{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", "set"), OK),
        ("sin x = 1/2, k positive_integer, abs families", _trig("sin(x) = 1/2", "k", "positive_integer"),
         _sol("{pi/6 + 2*Abs(k)*pi, 5*pi/6 + 2*Abs(k)*pi}", "set"), BAD),
        # the family written as SymPy's own image set: Lambda binds k, with the IR's declaration
        ("sin x = 0, k positive_integer, ImageSet(Lambda(k, Abs(k)*pi), Integers)", _trig("sin(x) = 0", "k", "positive_integer"),
         _sol("ImageSet(Lambda(k, Abs(k)*pi), Integers)", "set"), BAD),
        ("sin x = 0, k positive_integer, ImageSet(Lambda(k, k*pi), Integers)", _trig("sin(x) = 0", "k", "positive_integer"),
         _sol("ImageSet(Lambda(k, k*pi), Integers)", "set"), NOTBAD),
        # a window: the family parameter plays no part
        ("sin x = 0 on [0, 2pi), k positive_integer, {0, pi}",
         _trig("sin(x) = 0", "k", "positive_integer", "[0, 2*pi)"), _sol("{0, pi}", "set"), OK),
        ("sin x = 0 on [0, 2pi), k positive_integer, {pi}",
         _trig("sin(x) = 0", "k", "positive_integer", "[0, 2*pi)"), _sol("{pi}", "set"), NO),
    ]
    return rows


NP = [{"name": "n", "domain": "positive_integer"}]
NI = [{"name": "n", "domain": "integer"}]
NR = [{"name": "n", "domain": "real"}]
XNP = [X] + NP


def cases_d():
    ev = lambda e, v=NP, g=("n = 2",): _ir("evaluate", {"expr": e}, v, g)  # noqa: E731
    lim_n = _ir("limit", {"expr": "diff(sin(pi*n), n)", "var": "n", "to": "oo"}, NP)
    der_x = _ir("derivative", {"f": "x*diff(sin(pi*n), n)", "var": "x"}, XNP, (), "expression")
    lim_x = _ir("limit", {"expr": "x*diff(sin(pi*n), n)", "var": "x", "to": "1"}, XNP)
    sq = _ir("evaluate", {"expr": "n**2"}, NP, ["n = 2"])
    return [
        ("evaluate diff(sin(pi*n), n), n=2: 0", ev("diff(sin(pi*n), n)"), _sol("0"), BAD),
        ("evaluate diff(sin(pi*n), n), n=2: pi", ev("diff(sin(pi*n), n)"), _sol("pi"), NOTBAD),
        ("evaluate Derivative(sin(pi*n), n), n=2: 0", ev("Derivative(sin(pi*n), n)"), _sol("0"), BAD),
        ("evaluate Derivative(sin(pi*n), n), n=2: pi", ev("Derivative(sin(pi*n), n)"), _sol("pi"), NOTBAD),
        ("evaluate diff(cos(pi*n), n), n=2: I*pi", ev("diff(cos(pi*n), n)"), _sol("I*pi"), BAD),
        ("evaluate diff(cos(pi*n), n), n=2: 0", ev("diff(cos(pi*n), n)"), _sol("0"), NOTBAD),
        ("evaluate diff(sin(pi*n)) (no variable), n=2: 0", ev("diff(sin(pi*n))"), _sol("0"), BAD),
        ("evaluate diff(sin(pi*n), n + 0), n=2: 0", ev("diff(sin(pi*n), n + 0)"), _sol("0"), BAD),
        ("evaluate diff(sin(pi*n), (n, 2)), n=2: 0 (true 0)", ev("diff(sin(pi*n), (n, 2))"), _sol("0"), BAD | OK),
        ("evaluate diff(cos(pi*n), (n, 2)), n=2: 0 (true -pi**2)", ev("diff(cos(pi*n), (n, 2))"), _sol("0"), BAD),
        ("evaluate diff(sin(pi*n), n), n integer, n=2: 0", ev("diff(sin(pi*n), n)", NI), _sol("0"), BAD),
        ("evaluate Limit(diff(sin(pi*n), n), n, oo): 0", ev("Limit(diff(sin(pi*n), n), n, oo)", NP, ()), _sol("0"), BAD),
        ("limit task diff(sin(pi*n), n), n -> oo: 0", lim_n, _sol("0"), BAD),
        ("derivative in x of x*diff(sin(pi*n), n): 0", der_x, _sol("0", "expression"), BAD),
        ("derivative in x of x*diff(sin(pi*n), n): pi*(-1)**n", der_x, _sol("pi*(-1)**n", "expression"), NOTBAD),
        ("limit x -> 1 of x*diff(sin(pi*n), n): 0", lim_x, _sol("0"), BAD),
        ("step compute diff(sin(pi*n), n) = 0", sq, _sol("4", steps=[_st(1, "compute", "diff(sin(pi*n), n) = 0")]), BAD | OK),
        ("step eq Derivative(sin(pi*n), n) = 0", sq, _sol("4", steps=[_st(1, "eq", "Derivative(sin(pi*n), n) = 0")]), BAD | OK),
        # an indefinite integral in the integer variable folds the same way (its variable is not rebound)
        ("step compute Integral(sin(pi*n), n) = 7", sq, _sol("4", steps=[_st(1, "compute", "Integral(sin(pi*n), n) = 7")]), BAD | OK),
        ("step compute integrate(sin(pi*n), n) = 0", sq, _sol("4", steps=[_st(1, "compute", "integrate(sin(pi*n), n) = 0")]), BAD | OK),
        # LaTeX: latex2sympy differentiates in its own symbol and substitutes n afterwards (Subs)
        ("evaluate LaTeX d/dn sin(pi n), n=2: 0", ev(r"\frac{d}{dn} \sin(\pi n)"), _sol("0"), BAD),
        ("evaluate LaTeX d/dn sin(pi n), n=2: pi", ev(r"\frac{d}{dn} \sin(\pi n)"), _sol("pi"), NOTBAD),
        # controls: a real or undeclared variable, the derivative at a point, the task level
        ("control n real, n=2: pi", ev("diff(sin(pi*n), n)", NR), _sol("pi"), OK),
        ("control n real, n=2: 0", ev("diff(sin(pi*n), n)", NR), _sol("0"), NO),
        ("control n undeclared, n=2: pi", ev("diff(sin(pi*n), n)", [{"name": "n"}]), _sol("pi"), OK),
        ("control at(diff(sin(pi*n), n), n, 1): -pi", ev("at(diff(sin(pi*n), n), n, 1)", NP, ()), _sol("-pi"), OK),
        ("control at(diff(sin(pi*n), n), n, 1): 0", ev("at(diff(sin(pi*n), n), n, 1)", NP, ()), _sol("0"), NO),
        ("control Sum(diff(sin(pi*n), n), (n, 1, 3)): -pi", ev("Sum(diff(sin(pi*n), n), (n, 1, 3))", NP, ()), _sol("-pi"), NOTBAD),
        ("control Sum(diff(sin(pi*n), n), (n, 1, 3)): 0", ev("Sum(diff(sin(pi*n), n), (n, 1, 3))", NP, ()), _sol("0"), BAD),
        ("control derivative task in n (positive integer)", _ir("derivative", {"f": "sin(pi*n)", "var": "n", "at": "2"}, NP),
         _sol("pi"), UNK),
        ("control diff(exp(2*x), x) with n declared: 2*exp(2*x)", _ir("evaluate", {"expr": "diff(exp(2*x), x)"}, XNP),
         _sol("2*exp(2*x)", "expression"), NOTBAD),
        ("control step compute at(diff(sin(pi*n), n), n, 1) = -pi", sq,
         _sol("4", steps=[_st(1, "compute", "at(diff(sin(pi*n), n), n, 1) = -pi")]), OK),
        ("control step compute at(diff(sin(pi*n), n), n, 1) = 0", sq,
         _sol("4", steps=[_st(1, "compute", "at(diff(sin(pi*n), n), n, 1) = 0")]), NO),
    ]


R = "sqrt(9 + exp(-10000))"


def cases_u():
    dom = _ir("domain_of", {"expr": "1/(x - 3)", "var": "x"}, [{"name": "x"}], shape="set")
    ineq = _ir("solve_inequality", {"var": "x"}, [{"name": "x"}], ["x > 0"], "interval")
    return [
        ("domain 1/(x-3): (-oo, 3) U (R', oo)", dom, _sol(f"(-oo, 3) U ({R}, oo)", "set"), UNK),
        ("domain 1/(x-3): Union(Interval.open...)", dom,
         _sol(f"Union(Interval.open(-oo, 3), Interval.open({R}, oo))", "set"), UNK),
        ("domain 1/(x-3): right answer", dom, _sol("(-oo, 3) U (3, oo)", "set"), OK),
        ("step Or(x < 3, x > R')", ineq, _sol("(0, oo)", "interval", [_st(1, "eq", f"Or(x < 3, x > {R})")]), BAD | OK),
    ]


GROUPS = {"T": cases_t, "D": cases_d, "U": cases_u}


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
STEP_NOT_VERIFIED = {"step compute diff(sin(pi*n), n) = 0", "step eq Derivative(sin(pi*n), n) = 0",
                     "step compute Integral(sin(pi*n), n) = 7", "step compute integrate(sin(pi*n), n) = 0",
                     "step Or(x < 3, x > R')"}
STEP_VERIFIED = {"control step compute at(diff(sin(pi*n), n), n, 1) = -pi"}


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
                lay, steps = _summ(r)
            except Exception as e:  # noqa: BLE001
                v, lay, steps = f"EXC {type(e).__name__}: {e}"[:200], [], []
            ok = v in exp
            if label in STEP_NOT_VERIFIED and any(":verified:" in s for s in steps):
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
