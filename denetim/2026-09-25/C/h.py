import sys, json
sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
from mathverify.verifier import verify

def ir(kind, params, **kw):
    d = {"task": {"kind": kind, "params": params}, "vars": kw.pop("vars", []), "givens": kw.pop("givens", []),
         "answer_shape": kw.pop("answer_shape", "scalar")}
    d.update(kw)
    return d

def sol(payload, kind="value", steps=None):
    return {"claimed_answer": {"kind": kind, "payload": payload}, "steps": steps or []}

def run(label, pir, s, expect=None, show=False):
    try:
        r = verify(pir, s)
    except Exception as e:
        print(f"[{label}] EXCEPTION {type(e).__name__}: {e}")
        return None
    mark = ""
    if expect is not None:
        mark = "OK " if r.verdict == expect else "!!! MISMATCH (expected %s)" % expect
    print(f"[{label}] {r.verdict} conf={r.confidence:.2f} flags={r.flags} {mark}")
    if show or (expect is not None and r.verdict != expect):
        for l in r.layers:
            ev = {k: v for k, v in l.evidence.items() if k in ("reason","compare","value","count","probability","method","sum","symbolic","numeric","truth","claimed","centre_radius2_truth","centre_radius2_claimed","sample_values","spread","error","terms","rsolve","residual","det","eigenvalues","realisations","n_free","scale_fixed")}
            print("    ", l.layer, l.verdict, str(ev)[:600])
    return r
