"""Skeptic probes (read-only; run inside a git-archive copy): realistic variants of open findings."""
import sys
import time

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}


def ir(kind, params, givens=(), vars_=None, shape="scalar", **extra):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    d.update(extra)
    return d


def sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def solve(eq, vars_=None, givens=()):
    return ir("solve_equation", {"var": "x", "equation": eq}, givens, vars_, shape="set")


def deriv(f):
    return ir("derivative", {"f": f, "var": "x"}, [], [X], "expression")


def group_edison():
    out = []
    # D4D-WP: word-problem style composite givens (realistic Turkish wording)
    q = ir("evaluate", {"expr": "x + 5"}, ["x**2 = 9 ve x < 0"])
    out.append(("WP evaluate x+5, given 'x**2 = 9 ve x < 0' -> 8 (wrong; true 2)", q, sol("8")))
    out.append(("WP evaluate x+5, given 'x**2 = 9 ve x < 0' -> 2 (right)", q, sol("2")))
    q = ir("evaluate", {"expr": "x + 5"}, ["x**2 = 9", "x ∈ (-oo, 0)"])
    out.append(("WP evaluate x+5, givens x**2=9, 'x ∈ (-oo, 0)' -> 8 (wrong)", q, sol("8")))
    q = ir("evaluate", {"expr": "x"}, ["x + y = 7", "x*y = 12", "x > y ve y > 0"], [X, Y])
    out.append(("WP evaluate x, x+y=7, xy=12, 'x > y ve y > 0' -> 3 (wrong; true 4)", q, sol("3")))
    out.append(("WP evaluate x, x+y=7, xy=12, 'x > y ve y > 0' -> 4 (right)", q, sol("4")))
    # D4B10-LINEAR realistic variant: constant base that is exactly 1 written with logarithms
    q = solve("(log(2, 10) + log(5, 10))**(x - 3) = 1")
    out.append(("LIN (log2+log5)^(x-3) = 1 -> {3} (wrong; true R)", q, sol("{3}", "set")))
    q = solve("(log(6, 2) - log(3, 2))**x = 1")
    out.append(("LIN (log2 6 - log2 3)^x = 1 -> {0} (wrong; true R)", q, sol("{0}", "set")))
    q = solve("x*(log(6, 2) - log(3, 2) - 1) = 0")
    out.append(("LIN x*(log2 6 - log2 3 - 1) = 0 -> {0} (wrong; true R)", q, sol("{0}", "set")))
    return out


def group_d4e4():
    out = []
    # D4E4-YO-1 realistic variant: forgetting the absolute value inside a root
    out.append(("YO-1v f=sqrt|x-cos x|, claim (1+sin x)/(2 sqrt(x-cos x)) (wrong on u<0)",
                deriv("sqrt(Abs(x - cos(x)))"), sol("(1 + sin(x))/(2*sqrt(x - cos(x)))", "expression")))
    out.append(("YO-1c f=|x-cos x|, claim 1+sin x (wrong on u<0)",
                deriv("Abs(x - cos(x))"), sol("1 + sin(x)", "expression")))
    # D4E4-YO-2 realistic-ish variant: family of double zeros, r*m = 3/2 > 1 (f differentiable, f'=0 there)
    out.append(("YO-2v f=(sin^2 x)^(3/4), chain-rule claim 0/0 at k*pi",
                deriv("(sin(x)**2)**(3/4)"), sol("3*sin(x)*cos(x)/(2*(sin(x)**2)**(1/4))", "expression")))
    # rule-risk controls: correct textbook derivatives a broad YO-2 / YO-3 fail-closed rule would hit
    out.append(("CTRL f=sqrt(1+sin x), claim cos x/(2 sqrt(1+sin x))",
                deriv("sqrt(1 + sin(x))"), sol("cos(x)/(2*sqrt(1 + sin(x)))", "expression")))
    out.append(("CTRL f=sqrt(x-cos x), claim (1+sin x)/(2 sqrt(x-cos x))",
                deriv("sqrt(x - cos(x))"), sol("(1 + sin(x))/(2*sqrt(x - cos(x)))", "expression")))
    return out


def group_d4b10():
    return [x for x in group_edison() if x[0].startswith("LIN")]


def run(cases):
    from mathverify.verifier import verify
    for label, q, s in cases:
        t = time.time()
        try:
            r = verify(q, s)
            verdict = r.verdict
            flags = sorted({f for la in r.layers for f in (la.flags or [])} | set(r.flags))
            flags = [f for f in flags if f != "answer_level_only"][:6]
            lay = [(la.layer, la.verdict) for la in r.layers if la.verdict in ("pass", "fail")][:4]
        except Exception as e:  # noqa: BLE001
            verdict, flags, lay = f"EXC {type(e).__name__}: {str(e)[:80]}", [], []
        print(f"{verdict:9} {time.time() - t:6.1f}s {label} | {lay} {flags}", flush=True)


if __name__ == "__main__":
    groups = {"edison": group_edison, "d4e4": group_d4e4, "d4b10": group_d4b10}
    for g in sys.argv[1:]:
        if g not in groups:
            continue
        print(f"## {g}", flush=True)
        run(groups[g]())


def group_open():
    out = []
    f = [{"name": "f", "expr": "x**2 + 1", "args": ["x"], "domain": r"$x \notin [0, 3]$"}]
    q = {"task": {"kind": "solve_equation", "params": {"equation": "f(x) = 5", "var": "x"}}, "vars": [X],
         "givens": [], "answer_shape": "set", "functions": f}
    out.append(("D1 f dom x notin [0,3], f(x)=5 -> {-2, 2} (wrong; true {-2})", q, sol("{-2, 2}", "set")))
    out.append(("D1 same -> {-2} (right)", q, sol("{-2}", "set")))
    q = ir("solve_inequality", {"var": "x"}, ["x**3 > -8"], [{"name": "x"}], shape="interval",
           options={"A": "x > -2", "B": "(100, 200)"})
    s = sol("(-2, oo)", "interval")
    s["claimed_answer"]["option"] = "A"
    out.append(("ONCEKI-1 option A 'x > -2', claim (-2, oo) (right)", q, s))
    q = {"task": {"kind": "synthetic_geometry", "params": {"points": ["P", "Q", "R"], "constraints": [
        "dist(P,Q) = 6", "dist(Q,R) = 8", "angle(P,Q,R) = 90"], "target": "dist(P,R)"}},
         "vars": [], "givens": [], "answer_shape": "scalar"}
    out.append(("B-RK-1 geometry PQR -> 10 (right)", q, sol("10")))
    return out


if __name__ == "__main__" and "open" in sys.argv:
    print("## open", flush=True)
    run(group_open())
