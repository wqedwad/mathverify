import time

X = {"name": "x", "domain": "real"}


def ir(kind, params, givens=(), vars_=(X,), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}


def sol(p, kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": p}, "steps": []}


def der(f, at=None):
    p = {"f": f, "var": "x"}
    if at:
        p["at"] = at
    return ir("derivative", p, shape="scalar" if at else "expression")


U = "x - cos(x)"
TB = f"(1 + sin(x))*({U})/Abs({U})"
CASES = [
    ("RK1 sqrt(x**2 + x**4)' textbook [true]", der("sqrt(x**2 + x**4)"),
     sol("(x + 2*x**3)/sqrt(x**2 + x**4)", "expression")),
    ("RK1 sqrt(x**2 + 2*x**3 + x**4)' = (x + 3*x**2 + 2*x**3)/sqrt(...) [true, |x(x+1)|]",
     der("sqrt(x**2 + 2*x**3 + x**4)"),
     sol("(x + 3*x**2 + 2*x**3)/sqrt(x**2 + 2*x**3 + x**4)", "expression")),
    ("YO7 Piecewise((x - 1, x < 1), (2*x - 2, x > 1)) = 0 -> {1} [false: gap]",
     ir("solve_equation", {"var": "x", "equation": "Piecewise((x - 1, x < 1), (2*x - 2, x > 1)) = 0"}, shape="set"),
     sol("{1}", "set")),
    ("YO7 same -> EmptySet [true]",
     ir("solve_equation", {"var": "x", "equation": "Piecewise((x - 1, x < 1), (2*x - 2, x > 1)) = 0"}, shape="set"),
     sol("EmptySet", "set")),
    ("D4E4-YO1 |x - cos x|' textbook + 0*log(u) [false]", der(f"Abs({U})"), sol(f"{TB} + 0*log({U})", "expression")),
    ("D4E4-YO1 control |x - cos x|' textbook [true]", der(f"Abs({U})"), sol(TB, "expression")),
    ("D4E4-RK1 (1 - cos x)**(3/4)' everywhere-defined claim [true]", der("(1 - cos(x))**(3/4)"),
     sol("3*sin(x)/(4*(1 - cos(x))**(1/4))", "expression")),
    ("YO2-root (x**4)**(1/3)' chain-rule claim 4x^3/(3(x^4)^(2/3)) [convention: INCORRECT]", der("(x**4)**(1/3)"),
     sol("4*x**3/(3*(x**4)**(2/3))", "expression")),
]

if __name__ == "__main__":
    from mathverify.verifier import verify
    for label, q, s in CASES:
        t0 = time.time()
        try:
            r = verify(q, s)
            reasons = [f"{l.layer}" for l in r.layers][:5]
            out = r.verdict
        except Exception as e:  # noqa: BLE001
            out, reasons = f"EXC {type(e).__name__}: {e}"[:200], []
        print(f"{out:9s} {time.time() - t0:6.1f}s | {label} | {reasons}", flush=True)
