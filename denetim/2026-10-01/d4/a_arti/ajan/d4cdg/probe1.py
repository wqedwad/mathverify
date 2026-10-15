import sys, time
from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}


def dint(f, a, b, tol=None):
    p = {"integrand": f, "var": "x", "a": a, "b": b}
    if tol:
        p["rel_tol"] = tol
    return {"task": {"kind": "definite_integral", "params": p}, "vars": [X], "givens": [], "answer_shape": "scalar"}


def ext(f, which, iv):
    return {"task": {"kind": "extremum", "params": {"f": f, "var": "x", "which": which, "interval": iv}},
            "vars": [X], "givens": [], "answer_shape": "scalar"}


def sol(c):
    return {"claimed_answer": {"kind": "value", "payload": c}, "steps": []}


if __name__ == "__main__":
    cases = [
        ("YO4 tol=1 claim 100", dint("exp(cos(x))", "0", "1", "1"), "100"),
        ("YO4 tol=5 claim 10", dint("exp(cos(x))", "0", "1", "5"), "10"),
        ("YO1 max 1+x/10^50 claim 1", ext("1 + x/10**50", "max", "[0, 1]"), "1"),
        ("YOA atan(tan x) [0,2] tol1e-3 claim 2", dint("atan(tan(x))", "0", "2", "1e-3"), "2"),
    ]
    for label, ir, c in cases:
        t = time.time()
        try:
            v = verify(ir, sol(c)).verdict
        except Exception as e:  # noqa: BLE001
            v = f"EXC {type(e).__name__}"
        print(sys.argv[1] if len(sys.argv) > 1 else "", label, v, round(time.time() - t, 1), flush=True)
