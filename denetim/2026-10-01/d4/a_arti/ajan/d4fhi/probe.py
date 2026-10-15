"""Status probes for the d4f/d4h/d4i inventory (read-only; run inside a git-archive copy)."""
import sys
import time

X = {"name": "x", "domain": "real"}


def ir(kind, params, givens=(), vars_=None, shape="scalar", **extra):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    d.update(extra)
    return d


def sol(payload, kind="value", steps=(), option=None):
    s = {"claimed_answer": {"kind": kind, "payload": payload},
         "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": fr, "text": ""}
                   for i, (k, c, fr) in enumerate(steps)]}
    if option is not None:
        s["claimed_answer"]["option"] = option
    return s


def solve(eq, vars_=None, givens=()):
    return ir("solve_equation", {"var": "x", "equation": eq}, givens, vars_, shape="set")


def group_edison():
    out = []
    # D4-ADIM-I: case premise in the compute pool
    q = ir("evaluate", {"expr": "x**3"}, ["x**2 = 4"])
    out.append(("ADIM-I case x=2, compute x**3 = 8", q,
                sol("8", steps=[("case", "x = 2", []), ("compute", "x**3 = 8", ["s1"])])))
    # small gap: x**a = 4 with given a = 2
    out.append(("gap x**a = 4, a = 2 -> {-2, 2}",
                solve("x**a = 4", [X, {"name": "a", "domain": "real"}], ["a = 2"]), sol("{-2, 2}", "set")))
    # small gap: evaluate Limit(|x|/x) declaration vs constraint
    out.append(("gap Limit(|x|/x,x,0) x positive_real -> 1",
                ir("evaluate", {"expr": "Limit(Abs(x)/x, x, 0)"}, [], [{"name": "x", "domain": "positive_real"}]),
                sol("1")))
    out.append(("gap Limit(|x|/x,x,0) constraint x > 0 -> 1",
                ir("evaluate", {"expr": "Limit(Abs(x)/x, x, 0)"}, [], [{"name": "x", "domain": "real",
                                                                          "constraints": ["x > 0"]}]),
                sol("1")))
    return out


def group_d4e4():
    out = []
    for con in ["x > sqrt(-1)**2", "x > log(-1)*0"]:
        v = {"name": "x", "domain": "real", "constraints": [con]}
        out.append((f"A-YO-4 solve x**2=1 constraint {con} -> {{1}}", solve("x**2 = 1", [v]), sol("{1}", "set")))
    for ans in ["{-1, 0, 1}", "{-1, 1}"]:
        v = {"name": "x", "domain": "real", "constraints": ["x/x > 0"]}
        out.append((f"A-YO-4 solve x**3=x constraint x/x > 0 -> {ans}", solve("x**3 = x", [v]), sol(ans, "set")))
    out.append(("A-YO-4 limit Abs(x)/x at 0 given x > log(-1)*0 -> 1",
                ir("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"}, ["x > log(-1)*0"]), sol("1")))
    return out


def group_d4b10():
    K = [{"name": "k", "domain": "integer"}]
    out = []
    for lab, expr, pay, steps in [
        ("B-YO-1 core step sum_{1}^{log_3 27} k^2 = 15", "Sum(k**2, (k, 1, 3))", "14",
         [("compute", r"\sum_{k=1}^{\log_3 27} k^{2} = 15", [])]),
        ("B-YO-1 v7 step sum_{1}^{log_3 27} k = 7", "Sum(k, (k, 1, 3))", "6",
         [("compute", r"\sum_{k=1}^{\log_3 27} k = 7", [])]),
        ("B-YO-1 good step = 14", "Sum(k**2, (k, 1, 3))", "14",
         [("compute", r"\sum_{k=1}^{\log_3 27} k^{2} = 14", [])]),
    ]:
        out.append((lab, ir("evaluate", {"expr": expr}, [], K), sol(pay, steps=steps)))
    out.append(("B-RK-3 evaluate sum_{1}^{log_3 27} k -> 6",
                ir("evaluate", {"expr": r"\sum_{k=1}^{\log_{3} 27} k"}), sol("6")))
    out.append(("B-RK-3 evaluate sum_{1}^{log_3 27} k -> 7 (wrong)",
                ir("evaluate", {"expr": r"\sum_{k=1}^{\log_{3} 27} k"}), sol("7")))
    return out


def group_d4h():
    out = []
    q = ir("solve_inequality", {"var": "x"}, ["x**3 > -8"], [{"name": "x"}], shape="interval",
           options={"A": "x > -2", "B": "(100, 200)"})
    out.append(("ONCEKI-1 option 'x > -2'", q, sol("(-2, oo)", "interval", option="A")))
    q = ir("evaluate", {"expr": "3/2"}, [], [], options={"A": "1,5", "B": "123456"})
    out.append(("ONCEKI-1 option '1,5'", q, sol("3/2", option="A")))
    q = {"task": {"kind": "synthetic_geometry", "params": {"points": ["P", "Q", "R"], "constraints": [
        "dist(P,Q) = 6", "dist(Q,R) = 8", "angle(P,Q,R) = 90"], "target": "dist(P,R)"}},
         "vars": [], "givens": [], "answer_shape": "scalar"}
    out.append(("B-RK-1 geometry PQR -> 10", q, sol("10")))
    return out


def group_sweep():
    """One representative case per d4f round-2 attack finding (D4F2*)."""
    out = []
    ev = lambda e, v=None, **kw: ir("evaluate", {"expr": e}, [], v if v is not None else [X], **kw)  # noqa: E731
    out.append(("A-YO-1 trace([[0**0,0],[0,0]]) -> 1", ev("trace(Matrix([[0**0, 0], [0, 0]]))"), sol("1")))
    out.append(("A-YO-2 oo**(x - x) -> 1", ev("oo**(x - x)"), sol("1")))
    out.append(("A-YO-2 0**(x - x) -> 1", ev("0**(x - x)"), sol("1")))
    out.append(("A-YO-3 C: 1/factorial(-1) -> 0", ev("1/factorial(-1)", [], domain_of_discourse="complex"), sol("0")))
    out.append(("A-YO-5 0*sin(oo) -> 0", ev("0*sin(oo)"), sol("0")))
    NR = {"name": "n", "domain": "real"}
    KI = {"name": "k", "domain": "integer"}
    out.append(("A-RK-1 Sum(k,(k,n**2,n**2+2)) n real -> 3n^2+3+sin(pi n^2)",
                ev("Sum(k, (k, n**2, n**2 + 2))", [NR, KI]), sol("3*n**2 + 3 + sin(pi*n**2)")))
    out.append(("B-RK-2 lim 1/(2**x - 1000) x->oo pos int -> 0",
                ir("limit", {"expr": "1/(2**x - 1000)", "var": "x", "to": "oo"}, [],
                   [{"name": "x", "domain": "positive_integer"}]), sol("0")))
    NP = {"name": "n", "domain": "positive_integer"}
    out.append(("B-RK-4 Sum(1,(k,1,n(n+1)/2)) n pos int -> n(n+1)/2",
                ev("Sum(1, (k, 1, n*(n + 1)/2))", [NP, KI]), sol("n*(n + 1)/2")))
    out.append(("B-RK-5 1/det([[sqrt2,1],[1,sqrt2]]) -> 1",
                ev("1/det(Matrix([[sqrt(2), 1], [1, sqrt(2)]]))", []), sol("1")))
    return out


def group_d4horig():
    """d4h original findings and round-1 attack PRE-RK-4/5/6 (no slow F1/H1 cases)."""
    out = []
    f = [{"name": "f", "expr": "x**2 + 1", "args": ["x"], "domain": r"$x \notin [0, 3]$"}]
    q = {"task": {"kind": "solve_equation", "params": {"equation": "f(x) = 5", "var": "x"}}, "vars": [X],
         "givens": [], "answer_shape": "set", "functions": f}
    out.append(("D1 f dom x notin [0,3], f(x)=5 -> {-2, 2} (wrong)", q, sol("{-2, 2}", "set")))
    f = [{"name": "f", "expr": "x**2 + 1", "args": ["x"], "domain": "(-oo, -1), (1, oo)"}]
    q = {"task": {"kind": "solve_equation", "params": {"equation": "f(x) = 5", "var": "x"}}, "vars": [X],
         "givens": [], "answer_shape": "set", "functions": f}
    out.append(("D2 f dom '(-oo,-1), (1,oo)', f(x)=5 -> {} (ambiguous)", q, sol("{}", "set")))
    vs = [{"name": n, "domain": d} for n, d in [("n", "positive_integer"), ("x", "real"), ("d", "real"),
                                                 ("dn", "real"), ("dx", "real")]]
    q = {"task": {"kind": "simplify_expression", "params": {"expr": r"\frac{d^2}{dn^2}(n \sin(\pi n))"}},
         "vars": vs, "givens": [], "answer_shape": "expression"}
    out.append(("I2 d,dn declared, d^2/dn^2(n sin pi n) -> 0 (wrong)", q, sol("0", "expression")))
    out.append(("CAP-G1 \\mathit{gcd}(120,84) for gcd(84,120)", ir("evaluate", {"expr": "gcd(84, 120)"}, [], []),
                sol(r"\mathit{gcd}(120,84)")))
    q = solve("x**2 - x - 2 = 0", [X])
    out.append(("PRE-RK-4 params.equation, {-1,2} + step x + 2 = x**2", q,
                sol("{-1, 2}", "set", steps=[("eq", "x + 2 = x**2", [])])))
    q = solve("x**2 = 4", [X])
    out.append(("PRE-RK-5 claim $x \\in \\{-2, 2\\}$", q, sol(r"$x \in \{-2, 2\}$", "set")))
    out.append(("PRE-RK-6 claim S = {-2, 2}", q, sol("S = {-2, 2}", "set")))
    return out


def run(cases):
    from mathverify.verifier import verify
    for label, q, s in cases:
        t = time.time()
        try:
            r = verify(q, s)
            verdict = r.verdict
            layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
            steps = layer.evidence.get("steps", []) if layer is not None else []
            st = [(x.get("id"), x.get("status")) for x in steps]
            flags = sorted({f for la in r.layers for f in (la.flags or [])} | set(r.flags))
            flags = [f for f in flags if f != "answer_level_only"][:5]
        except Exception as e:  # noqa: BLE001
            verdict, st, flags = f"EXC {type(e).__name__}: {str(e)[:80]}", [], []
        print(f"{verdict:9} {str(st):40} {time.time() - t:6.1f}s {label}  {flags}", flush=True)


if __name__ == "__main__":
    groups = {"edison": group_edison, "d4e4": group_d4e4, "d4b10": group_d4b10, "d4h": group_d4h,
              "sweep": group_sweep, "d4horig": group_d4horig}
    for g in sys.argv[1:]:
        print(f"## {g}", flush=True)
        run(groups[g]())
