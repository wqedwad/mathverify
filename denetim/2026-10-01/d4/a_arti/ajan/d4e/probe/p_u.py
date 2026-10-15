import sys, time

X = {"name": "x", "domain": "real"}
A = {"name": "a", "domain": "real"}
AP = {"name": "a", "domain": "positive_real"}
T = {"name": "t", "domain": "real"}
NP = {"name": "n", "domain": "positive_integer"}


def ir(kind, params, givens=(), vars_=(X,), shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def sol(p, kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": p}, "steps": []}


PW = "Piecewise((x**2, x < 1), (2*x, x >= 1))"
F = [{"name": "f", "expr": PW, "args": ["x"], "params": []}]
CASES = [
    ("U2 evaluate f(2), f piecewise -> 4 [true]", ir("evaluate", {"expr": "f(2)"}, functions=F), sol("4")),
    ("U2 evaluate f(2), f piecewise -> 3 [false]", ir("evaluate", {"expr": "f(2)"}, functions=F), sol("3")),
    ("U2 evaluate PW, given x = 2 -> 4 [true]", ir("evaluate", {"expr": PW}, ["x = 2"]), sol("4")),
    ("U2 solve PW(x) = 4 -> {-2, 2} [true]", ir("solve_equation", {"var": "x", "equation": PW + " = 4"}, shape="set"),
     sol("{-2, 2}", "set")),
    ("U2 solve PW(x) = 4 -> {2} [false]", ir("solve_equation", {"var": "x", "equation": PW + " = 4"}, shape="set"),
     sol("{2}", "set")),
    ("U2 solve PW with a, a = 2: Piecewise((a*x, x < 1), (x + a, x >= 1)) = 4 -> {2} [true]",
     ir("solve_equation", {"var": "x", "equation": "Piecewise((a*x, x < 1), (x + a, x >= 1)) = 4"}, ["a = 2"],
        (X, A), "set"), sol("{2}", "set")),
    ("U2 limit PW at 2 -> 4 [true]", ir("limit", {"expr": PW, "var": "x", "to": "2"}), sol("4")),
    ("U5 derivative (x**2)**n, n Z+ -> 2*n*x**(2*n - 1) [true]",
     ir("derivative", {"f": "(x**2)**n", "var": "x"}, (), (X, NP), "expression"),
     sol("2*n*x**(2*n - 1)", "expression")),
    ("U5 derivative x**n, n Z+ -> n*x**(n - 1) [true, control]",
     ir("derivative", {"f": "x**n", "var": "x"}, (), (X, NP), "expression"), sol("n*x**(n - 1)", "expression")),
    ("U1 evaluate Integral(1/(t**2 + a**2), (t, 0, oo)), a > 0 -> pi/(2*a) [true]",
     ir("evaluate", {"expr": "Integral(1/(t**2 + a**2), (t, 0, oo))"}, (), (T, AP)), sol("pi/(2*a)")),
    ("U1 evaluate Integral(exp(-a*t), (t, 0, oo)), a > 0 -> 1/a [true]",
     ir("evaluate", {"expr": "Integral(exp(-a*t), (t, 0, oo))"}, (), (T, AP)), sol("1/a")),
    ("U1 derivative Integral(1/(t**2 + a**2), (t, x, oo)), a > 0 -> -1/(x**2 + a**2) [true]",
     ir("derivative", {"f": "Integral(1/(t**2 + a**2), (t, x, oo))", "var": "x"}, (), (X, T, AP), "expression"),
     sol("-1/(x**2 + a**2)", "expression")),
]

if __name__ == "__main__":
    from mathverify.verifier import verify
    for label, q, s in CASES:
        t0 = time.time()
        try:
            r = verify(q, s)
            reasons = [f"{l.layer}:{getattr(l, 'status', '')}" for l in r.layers][:6]
            out = r.verdict
        except Exception as e:  # noqa: BLE001
            out, reasons = f"EXC {type(e).__name__}: {e}"[:200], []
        print(f"{out:9s} {time.time() - t0:6.1f}s | {label} | {reasons}", flush=True)
