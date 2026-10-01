"""Re-run the third audit's critic findings N1-N9 (tur3_e6712f5.json) on master aa67b20.

Usage: sonda_n19.py <group> [out.json]   group in N1..N9 or ALL
Each case: (label, ir, solution, expected) where expected is a set of acceptable verdicts.
"""
from __future__ import annotations

import json
import sys
import time


def _ir(kind, params, vars_=(), givens=(), shape="scalar", options=None, functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if options:
        d["options"] = options
    if functions:
        d["functions"] = functions
    return d


def _sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [dict(s, text=s.get("text", "")) for s in steps]}


def _step(i, kind, claim, frm=()):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": list(frm)}


OK = {"CORRECT"}
BAD = {"INCORRECT", "UNKNOWN"}        # anything but a false accept
NO = {"INCORRECT"}
UNK = {"UNKNOWN"}
NOTBAD = {"CORRECT", "UNKNOWN"}       # anything but a false reject

XT = [{"name": "x", "domain": "real"}, {"name": "t", "domain": "real"}]
XR = [{"name": "x", "domain": "real"}]
NK = [{"name": "n", "domain": "positive_integer"}, {"name": "k", "domain": "positive_integer"}]


def cases_n1():
    F = [{"name": "F", "expr": "integrate(sqrt(t), (t, 0, x))", "args": ["x"]}]
    L = [{"name": "L", "expr": "integrate(1/t, (t, 1, x))", "args": ["x"]}]
    A = [{"name": "A", "expr": "integrate(1/sqrt(1 - t**2), (t, 0, x))", "args": ["x"]}]
    G = [{"name": "g", "expr": "limit(sqrt(a + t**2), t, 0)", "args": ["a"]}]
    AT = [{"name": "a", "domain": "real"}, {"name": "t", "domain": "real"}]
    ineq = _ir("solve_inequality", {"inequality": "F(x)**2 < 0", "var": "x"}, XT, shape="interval", functions=F)
    eq = _ir("solve_equation", {"equation": "F(x)**2 = -4/9", "var": "x"}, XT, shape="set", functions=F)
    geq = _ir("solve_equation", {"equation": "g(a)**2 = -9", "var": "a"}, AT, shape="set", functions=G)
    return [
        ("F^2<0 (-oo,0)", ineq, _sol("(-oo, 0)", "interval"), BAD),
        ("F^2<0 EmptySet", ineq, _sol("{}", "set"), NOTBAD),
        ("F^2=-4/9 {-1}", eq, _sol("{-1}", "set"), BAD),
        ("F^2=-4/9 EmptySet", eq, _sol("{}", "set"), NOTBAD),
        ("L(-1)=I*pi", _ir("evaluate", {"expr": "L(-1)"}, XT, functions=L), _sol("I*pi"), UNK | NO),
        ("A(2)=asin(2)", _ir("evaluate", {"expr": "A(2)"}, XT, functions=A), _sol("asin(2)"), UNK | NO),
        ("g(a)^2=-9 {-9}", geq, _sol("{-9}", "set"), BAD),
        ("g(a)^2=-9 EmptySet", geq, _sol("{}", "set"), NOTBAD),
        ("domain_of L (0,oo)", _ir("domain_of", {"expr": "L(x)", "var": "x"}, XT, shape="interval", functions=L),
         _sol("(0, oo)", "interval"), NOTBAD),
        ("domain_of F [0,oo)", _ir("domain_of", {"expr": "F(x)", "var": "x"}, XT, shape="interval", functions=F),
         _sol("[0, oo)", "interval"), NOTBAD),
        # direct-text controls (critic: already wrong in PREV/OLD)
        ("text integrate(sqrt)^2=-4/9 {-1}",
         _ir("solve_equation", {"equation": "integrate(sqrt(t), (t, 0, x))**2 = -4/9", "var": "x"}, XT, shape="set"),
         _sol("{-1}", "set"), BAD),
        ("diff(L(x),x)=-1 {-1}",
         _ir("solve_equation", {"equation": "diff(L(x), x) = -1", "var": "x"}, XT, shape="set", functions=L),
         _sol("{-1}", "set"), BAD),
    ]


def cases_n2():
    ev = lambda e: _ir("evaluate", {"expr": e}, XR)                                   # noqa: E731
    I1 = "integrate(x**2 - 2*x, (x, 0, 3))"
    opts = {"A": "-1", "B": "0", "C": "1", "D": "2"}
    out = [
        ("I1 claim0 + eq step", ev(I1), _sol("0", steps=[_step(1, "eq", f"{I1} = 27/3 - 9")]), OK),
        ("I1 claim0", ev(I1), _sol("0"), OK),
        ("I1 claim1", ev(I1), _sol("1"), NO),
        ("I1 MC B", _ir("evaluate", {"expr": I1}, XR, options=opts), _sol(None, option="B"), OK),
        ("I1 MC A", _ir("evaluate", {"expr": I1}, XR, options=opts), _sol(None, option="A"), NO),
    ]
    for e, rhs in [("integrate(3*x**2 - 4*x, (x, 0, 2))", "8 - 8"), ("integrate(cos(x), (x, 0, pi))", "sin(pi) - sin(0)"),
                   ("integrate(x - 1, (x, 0, 2))", "2 - 2"), ("integrate(sin(2*x), (x, 0, pi))", "0")]:
        out.append((f"{e} claim0", ev(e), _sol("0"), OK))
        out.append((f"{e} eq step", ev(e), _sol("0", steps=[_step(1, "eq", f"{e} = {rhs}")]), OK))
    CI = "Integral(x**2 - 2*x, (x, 0, 3))"
    out += [
        ("I1 compute step", ev(I1), _sol("0", steps=[_step(1, "compute", f"{I1} = 0")]), OK),
        ("capital Integral eq step", ev(I1), _sol("0", steps=[_step(1, "eq", f"{CI} = 0")]), OK),
        ("capital Integral evaluate claim0", ev(CI), _sol("0"), OK),
        ("definite_integral task claim0",
         _ir("definite_integral", {"integrand": "x**2 - 2*x", "var": "x", "a": "0", "b": "3"}, XR), _sol("0"), OK),
        ("definite_integral task + Integral step",
         _ir("definite_integral", {"integrand": "x**2 - 2*x", "var": "x", "a": "0", "b": "3"}, XR),
         _sol("0", steps=[_step(1, "eq", f"{CI} = 0")]), OK),
    ]
    return out


def cases_n3():
    L1 = r"\lim_{x \to 2} \frac{|x - 2|}{x - 2}"
    L2 = r"\lim_{x \to 1} \lfloor x \rfloor"
    L3 = r"\lim_{x \to 3} \frac{1}{x - 3}"
    opts = {"A": "-1", "B": "0", "C": "1", "D": "2", "E": "Yoktur"}
    out = []
    for vs, tag in [(XR, "real"), ([{"name": "x"}], "undecl")]:
        out += [
            (f"[{tag}] {L1} = 1", _ir("evaluate", {"expr": L1}, vs), _sol("1"), BAD),
            (f"[{tag}] {L2} = 1", _ir("evaluate", {"expr": L2}, vs), _sol("1"), BAD),
            (f"[{tag}] {L3} = oo", _ir("evaluate", {"expr": L3}, vs), _sol("oo"), BAD),
            (f"[{tag}] MC C", _ir("evaluate", {"expr": L1}, vs, options=opts), _sol(None, option="C"), BAD),
        ]
    lim = _ir("limit", {"expr": "Abs(x - 2)/(x - 2)", "var": "x", "to": "2", "side": "+"}, XR)
    lim3 = _ir("limit", {"expr": "1/(x - 3)", "var": "x", "to": "3", "side": "+"}, XR)
    out += [
        ("limit+ task, compute step L1=1", lim, _sol("1", steps=[_step(1, "compute", f"{L1} = 1")]), NO),
        ("limit+ task, eq step L1=1", lim, _sol("1", steps=[_step(1, "eq", f"{L1} = 1")]), NO),
        ("limit+ task, eq step L3=oo", lim3, _sol("oo", steps=[_step(1, "eq", f"{L3} = \\infty")]), NO),
        ("limit+ task, compute step L3=oo", lim3, _sol("oo", steps=[_step(1, "compute", f"{L3} = \\infty")]), NO),
        # controls: written one-sided LaTeX keeps its side
        ("ctrl lim_{x->2^+} = 1", _ir("evaluate", {"expr": r"\lim_{x \to 2^+} \frac{|x - 2|}{x - 2}"}, XR),
         _sol("1"), NOTBAD),
        ("ctrl canonical limit(Abs(x-2)/(x-2),x,2)=1",
         _ir("evaluate", {"expr": "limit(Abs(x - 2)/(x - 2), x, 2)"}, XR), _sol("1"), BAD),
    ]
    return out


def cases_n8():
    V = [{"name": "n", "domain": "positive_integer"}, {"name": "a", "domain": "real"}]
    E = "limit(a*n*tan(pi/n), n, oo)"
    G = [{"name": "g", "expr": E, "args": ["a"]}]
    seq = _ir("solve_equation", {"equation": "limit(a*n*sin(pi/n), n, oo) = 2*pi", "var": "a"}, V, shape="set")
    return [
        ("simplify claim 0", _ir("simplify_expression", {"expr": E}, V), _sol("0", "expression"), BAD),
        ("simplify claim pi*a", _ir("simplify_expression", {"expr": E}, V), _sol("pi*a", "expression"), NOTBAD),
        ("evaluate a=2 claim 0", _ir("evaluate", {"expr": E}, V, ["a = 2"]), _sol("0"), BAD),
        ("evaluate a=2 claim 2pi", _ir("evaluate", {"expr": E}, V, ["a = 2"]), _sol("2*pi"), NOTBAD),
        ("g(1) claim 0", _ir("evaluate", {"expr": "g(1)"}, V, functions=G), _sol("0"), BAD),
        ("g(1) claim pi", _ir("evaluate", {"expr": "g(1)"}, V, functions=G), _sol("pi"), NOTBAD),
        ("eq sin EmptySet", seq, _sol("{}", "set"), BAD),
        ("eq sin {2}", seq, _sol("{2}", "set"), NOTBAD),
        ("ctrl closed limit(n*tan(pi/n)) = 0", _ir("evaluate", {"expr": "limit(n*tan(pi/n), n, oo)"}, V), _sol("0"), BAD),
    ]


def cases_n4():
    out = []
    for e in ["Sum(cos(k*pi/2), (k, 1, 4*n))", "Sum(sin(k*pi/2), (k, 1, 4*n))", "Sum(cos(2*pi*k/3), (k, 1, 3*n))",
              "Sum(sin(2*pi*k/3), (k, 1, 3*n))", "Sum(cos(pi*k/3), (k, 1, 6*n))"]:
        out.append((f"{e} = 0", _ir("simplify_expression", {"expr": e}, NK), _sol("0", "expression"), NOTBAD))
    out.append(("Sum(cos(2pi k/3),(k,1,3n)) + 1 = 1",
                _ir("simplify_expression", {"expr": "Sum(cos(2*pi*k/3), (k, 1, 3*n)) + 1"}, NK),
                _sol("1", "expression"), NOTBAD))
    out.append(("ctrl wrong claim 1 for cos(k pi/2) sum",
                _ir("simplify_expression", {"expr": "Sum(cos(k*pi/2), (k, 1, 4*n))"}, NK), _sol("1", "expression"), NO))
    return out


def cases_n5():
    out = []
    for D in ["x > 0", "(0, oo)", "x in (0, oo)", "x > 0 and x < 3", "R+", "[0, oo)", "x > 0, x < 3"]:
        fn = [{"name": "f", "expr": "x**2 + 1", "args": ["x"], "domain": D}]
        ir = _ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, XR, shape="set", functions=fn)
        out.append((f"D={D!r} {{-2,2}}", ir, _sol("{-2, 2}", "set"), BAD))
        out.append((f"D={D!r} {{2}}", ir, _sol("{2}", "set"), NOTBAD))
    fn = [{"name": "f", "expr": "x**2 + 1", "args": ["x"], "domain": "x > a"}]
    ir = _ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, XR + [{"name": "a", "domain": "real"}],
             ["a = 0"], shape="set", functions=fn)
    out.append(("D='x > a', a=0, {2}", ir, _sol("{2}", "set"), NOTBAD))
    out.append(("D='x > a', a=0, {-2,2}", ir, _sol("{-2, 2}", "set"), BAD))
    return out


def cases_n9():
    fn = [{"name": "f", "expr": "x**2 + 1", "args": ["x"], "domain": "x > 0"}]
    return [
        ("integrate(f,(x,-2,-1)) = 10/3", _ir("evaluate", {"expr": "integrate(f(x), (x, -2, -1))"}, XR, functions=fn),
         _sol("10/3"), UNK),
        ("limit(f(x),x,-1) = 2", _ir("evaluate", {"expr": "limit(f(x), x, -1)"}, XR, functions=fn), _sol("2"), UNK),
        ("ctrl definite_integral task f on [-2,-1]",
         _ir("definite_integral", {"integrand": "f(x)", "var": "x", "a": "-2", "b": "-1"}, XR, functions=fn),
         _sol("10/3"), UNK),
        ("ctrl integrate(f,(x,1,2)) = 10/3", _ir("evaluate", {"expr": "integrate(f(x), (x, 1, 2))"}, XR, functions=fn),
         _sol("10/3"), NOTBAD),
    ]


def cases_n6():
    return [
        ("Integral(t^2-2t,(t,0,x)) claim +1", _ir("simplify_expression", {"expr": "Integral(t**2 - 2*t, (t, 0, x))"}, XT),
         _sol("x**3/3 - x**2 + 1", "expression"), NO),
        ("Integral(t^2-2t,(t,0,x)) ctrl right", _ir("simplify_expression", {"expr": "Integral(t**2 - 2*t, (t, 0, x))"}, XT),
         _sol("x**3/3 - x**2", "expression"), NOTBAD),
        ("Sum(k,(k,1,1000n)) claim wrong", _ir("simplify_expression", {"expr": "Sum(k, (k, 1, 1000*n))"}, NK),
         _sol("500*n*(1000*n - 1)", "expression"), NO),
        ("Sum(k,(k,1,1000n)) ctrl right", _ir("simplify_expression", {"expr": "Sum(k, (k, 1, 1000*n))"}, NK),
         _sol("500*n*(1000*n + 1)", "expression"), NOTBAD),
    ]


def cases_n7():
    XA = [{"name": "x", "domain": "real"}, {"name": "a", "domain": "real"}]
    XY = [{"name": "x", "domain": "real"}, {"name": "y", "domain": "real"}]
    return [
        ("x^2=a, a=4, {-2,2}", _ir("solve_equation", {"equation": "x**2 = a", "var": "x"}, XA, ["a = 4"], shape="set"),
         _sol("{-2, 2}", "set"), OK),
        ("x^2=a, a=integrate(2x,(x,0,2)), {-2,2}",
         _ir("solve_equation", {"equation": "x**2 = a", "var": "x"}, XA, ["a = integrate(2*x, (x, 0, 2))"], shape="set"),
         _sol("{-2, 2}", "set"), OK),
        ("sqrt(y-x)=2, x=1, {5}", _ir("solve_equation", {"equation": "sqrt(y - x) = 2", "var": "y"}, XY, ["x = 1"], shape="set"),
         _sol("{5}", "set"), OK),
        ("ctrl x^2=a, a=4, {2}", _ir("solve_equation", {"equation": "x**2 = a", "var": "x"}, XA, ["a = 4"], shape="set"),
         _sol("{2}", "set"), NO),
    ]


GROUPS = {"N1": cases_n1, "N2": cases_n2, "N3": cases_n3, "N8": cases_n8, "N4": cases_n4, "N5": cases_n5,
          "N9": cases_n9, "N6": cases_n6, "N7": cases_n7}


def _summ(r):
    lay = []
    steps = []
    for l in r.layers:
        ev = l.evidence or {}
        reason = ev.get("reason") or ev.get("why") or ev.get("error") or ""
        lay.append(f"{l.layer}:{l.verdict}{'(' + str(reason)[:140] + ')' if reason else ''}")
        if l.layer == "steps.refute":
            for s in ev.get("steps", []):
                steps.append(f"{s.get('id')}:{s.get('status')}:{str(s.get('route') or s.get('reason') or '')[:80]}")
    return lay, steps


def main():
    from mathverify.verifier import verify
    sel = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    groups = list(GROUPS) if sel == "ALL" else sel.split(",")
    rows = []
    for g in groups:
        for label, ir, sol, exp in GROUPS[g]():
            t0 = time.perf_counter()
            try:
                r = verify(ir, sol)
                v = r.verdict
                lay, steps = _summ(r)
                fbs = r.first_bad_step
            except Exception as e:  # noqa: BLE001
                v, lay, steps, fbs = f"EXC {type(e).__name__}: {e}"[:200], [], [], None
            dt = time.perf_counter() - t0
            ok = v in exp
            rows.append({"group": g, "label": label, "verdict": v, "expected": sorted(exp), "ok": ok,
                         "secs": round(dt, 1), "first_bad_step": fbs, "layers": lay, "steps": steps})
            print(f"{g} | {'ok ' if ok else 'BAD'} | {v:9s} (exp {'/'.join(sorted(exp))}) | {dt:5.1f}s | {label}", flush=True)
            for x in lay:
                print(f"      {x}", flush=True)
            for x in steps:
                print(f"      step {x}", flush=True)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
