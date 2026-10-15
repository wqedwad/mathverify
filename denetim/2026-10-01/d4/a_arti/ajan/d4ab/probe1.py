"""Status probe for d4a/d4b inventory: unverified suspects and fixer-found items on a given checkout."""
import sys
import time

X = {"name": "x", "domain": "real"}
XY = [X, {"name": "y", "domain": "real"}]
Q = "(log(6) - log(2) - log(3))"
Z = "(2*atan(tanh(1/2)) - atan(sinh(1)))"


def ir(kind, params, vars_=(X,), givens=(), shape="scalar", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def cases():
    eqN = ir("solve_equation", {"equation": "x**2 - 3*x = 0", "var": "x"}, shape="set", dod="x in N and x < 10")
    eqlin = ir("solve_equation", {"equation": f"exp(x*{Q}) = 1", "var": "x"}, shape="set")
    der = ir("derivative", {"f": "atan2(x, -1)", "var": "x", "at": "0"})
    s2 = ir("evaluate", {"expr": "y + 1"}, XY, [f"x = {Z}", "y = 0"])
    return [
        ("N-and: {3}", eqN, sol("{3}", kind="set")),
        ("N-and: {0,3}", eqN, sol("{0, 3}", kind="set")),
        ("linear exp(xQ)=1: {0}", eqlin, sol("{0}", kind="set")),
        ("linear exp(xQ)=1: Reals", eqlin, sol("Reals", kind="set")),
        ("atan2(x,-1)' at 0: -1", der, sol("-1")),
        ("S2 y=ceiling(x^2), x=Z, y=0: 1", s2, sol("1", steps=[("eq", "y = ceiling(x**2)")])),
    ]


if __name__ == "__main__":
    from mathverify.verifier import verify
    for name, i, s in cases():
        t = time.time()
        try:
            r = verify(i, s)
            steps = [getattr(x, "status", x) for x in (getattr(r, "steps", None) or [])]
            layers = getattr(r, "layers", None)
            print(f"{name}: {r.verdict} steps={steps} ({time.time() - t:.1f} s)", flush=True)
            reasons = getattr(r, "reasons", None) or getattr(r, "flags", None)
            if reasons:
                print("   ", str(reasons)[:300], flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"{name}: EXC {type(e).__name__}: {str(e)[:200]} ({time.time() - t:.1f} s)", flush=True)
    sys.stdout.flush()
