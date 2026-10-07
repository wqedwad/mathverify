"""Shared helpers for the d4e3 false-accept probes (copied from denetim/2026-10-01/d4e/sonda.py)."""
import json, sys, time, os

OK = {"CORRECT"}; NO = {"INCORRECT"}; NOTOK = {"INCORRECT", "UNKNOWN"}; NOTNO = {"CORRECT", "UNKNOWN"}; UNK = {"UNKNOWN"}
X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_real"}
Y = {"name": "y", "domain": "real"}
T_ = {"name": "t", "domain": "real"}
A_ = {"name": "a", "domain": "real"}
K_ = {"name": "k", "domain": "integer"}


def xc(*cs):
    return {"name": "x", "domain": "real", "constraints": list(cs)}


def ir(kind, params, givens=(), vars_=None, shape="set", dod=None, functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if dod:
        d["domain_of_discourse"] = dod
    if functions:
        d["functions"] = functions
    return d


def sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


DNE = {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}


def lim(expr, to, givens=(), vars_=None, dod=None, side=None):
    p = {"expr": expr, "var": "x", "to": to}
    if side:
        p["side"] = side
    return ir("limit", p, givens, vars_, shape="scalar", dod=dod)


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


def ss(term, lo, hi, givens=(), vars_=None):
    return ir("series_sum", {"term": term, "var": "k", "lo": lo, "hi": hi}, givens, vars_ or [K_, A_], shape="scalar")


def ev1(expr, vars_=None, givens=()):
    return ir("evaluate", {"expr": expr}, givens, vars_ or [T_], shape="scalar")


def run(cases, out_path=None):
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    rows, bad, t0 = [], 0, time.time()
    for label, q, s, verdicts, statuses in cases:
        t = time.time()
        try:
            r = verify(q, s)
            verdict = r.verdict
            layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
            steps = layer.evidence.get("steps", []) if layer is not None else []
            status = steps[-1].get("status") if steps else None
            flags = sorted({f for la in r.layers for f in (la.flags or [])})[:6]
            reasons = [f"{la.layer}:{la.verdict}:{str(la.evidence.get('reason', ''))[:90]}" for la in r.layers
                       if la.layer.startswith("certify")][:3]
        except Exception as e:  # noqa: BLE001
            verdict, status, flags, reasons = f"EXC {type(e).__name__}: {e}"[:200], None, [], []
        ok = verdict in verdicts and (statuses is None or status in statuses)
        bad += not ok
        rows.append({"label": label, "verdict": verdict, "status": status, "ok": ok, "flags": flags,
                     "reasons": reasons, "s": round(time.time() - t, 2)})
        print(f"{'ok ' if ok else 'BAD'} {verdict:9} {str(status):9} {time.time() - t:5.1f}s {label}  {flags} {reasons}",
              flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad
