"""Probe helpers (ret/kapsama attack on d4e round 4)."""
import json, sys, time, os

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_real"}
Y = {"name": "y", "domain": "real"}
T_ = {"name": "t", "domain": "real"}
AR = {"name": "a", "domain": "real"}
AP = {"name": "a", "domain": "positive_real"}
K_ = {"name": "k", "domain": "integer"}
NI = {"name": "n", "domain": "integer"}


def xc(*cs, dom="real"):
    return {"name": "x", "domain": dom, "constraints": list(cs)}


def vc(name, dom, *cs):
    return {"name": name, "domain": dom, "constraints": list(cs)}


def ir(kind, params, givens=(), vars_=None, shape="set", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if dod:
        d["domain_of_discourse"] = dod
    return d


def sol(payload, kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []}


DNE = {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}


def der(f, at=None, givens=(), vars_=None, dod=None, order=None):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    if order:
        p["order"] = order
    return ir("derivative", p, givens, vars_, shape="scalar" if at is not None else "expression", dod=dod)


def tan(f, at, givens=(), vars_=None, dod=None):
    return ir("tangent_line", {"f": f, "var": "x", "at": at, "dep": "y"}, givens, list(vars_ or [X]) + [Y],
              shape="equation", dod=dod)


def anti(f, givens=(), vars_=None, dod=None):
    return ir("antiderivative", {"integrand": f, "var": "x"}, givens, vars_, shape="expression", dod=dod)


def ext(f, which, interval, givens=(), vars_=None, dod=None):
    p = {"f": f, "var": "x", "which": which}
    if interval is not None:
        p["interval"] = interval
    return ir("extremum", p, givens, vars_, shape="scalar", dod=dod)


def lim(expr, to, givens=(), vars_=None, dod=None, side=None):
    p = {"expr": expr, "var": "x", "to": to}
    if side:
        p["side"] = side
    return ir("limit", p, givens, vars_, shape="scalar", dod=dod)


def ss(term, lo, hi, givens=(), vars_=None):
    return ir("series_sum", {"term": term, "var": "k", "lo": lo, "hi": hi}, givens, vars_ or [K_], shape="scalar")


def ev1(expr, vars_=None, givens=()):
    return ir("evaluate", {"expr": expr}, givens, vars_ or [T_], shape="scalar")


def solve(eq, givens=(), vars_=None, dod=None):
    return ir("solve_equation", {"var": "x", "equation": eq}, givens, vars_, "set", dod)


def ineq(e, givens=(), vars_=None, dod=None):
    return ir("solve_inequality", {"var": "x", "inequality": e}, givens, vars_, "set", dod)


def run(cases, tag, only=None):
    import mathverify
    from mathverify.verifier import verify
    print("# mathverify:", os.path.dirname(mathverify.__file__), flush=True)
    rows = []
    for label, q, s in cases:
        if only and not any(o in label for o in only):
            continue
        t = time.time()
        try:
            r = verify(q, s)
            verdict = r.verdict
            reasons = [f"{la.layer}:{la.verdict}:{str(la.evidence.get('reason', la.evidence.get('error', '')))[:110]}"
                       for la in r.layers if la.layer.startswith("certify")][:2]
        except Exception as e:  # noqa: BLE001
            verdict, reasons = f"EXC {type(e).__name__}: {e}"[:160], []
        dt = time.time() - t
        rows.append({"label": label, "verdict": verdict, "s": round(dt, 1), "reasons": reasons})
        print(f"{verdict:9} {dt:5.1f}s {label} | {reasons}", flush=True)
    return rows
