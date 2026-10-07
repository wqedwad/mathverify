"""Self-contained helpers for the d4e round-3 false-accept repros (no project test helpers)."""
X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_real"}
T = {"name": "t", "domain": "real"}
Y = {"name": "y", "domain": "real"}


def P(kind, params, givens=(), vars_=(X,), shape="scalar", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}
    if dod:
        d["domain_of_discourse"] = dod
    return d


def S(payload, kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []}


def show(cases):
    from mathverify.verifier import verify
    for label, q, s in cases:
        print(f"{verify(q, s).verdict:9} {label}")
