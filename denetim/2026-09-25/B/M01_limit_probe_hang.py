"""M01 limit: numeric_probe evaluates f(10^3..10^12) with mpmath IN THE MAIN PROCESS (no sandbox
timeout). exp(-exp(10^6)) needs ~10^434294 digits of exponent work -> verify() never returns.
Ground truth: lim_{x->oo} exp(-exp(x)) = 0 (SymPy answers in 0.4 s inside the sandbox)."""
import multiprocessing as mpc
import sys
import time


def _run(q):
    import os; sys.path.insert(0, os.environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
    from mathverify.verifier import verify
    r = verify({"task": {"kind": "limit", "params": {"expr": "exp(-exp(x))", "var": "x", "to": "oo"}},
                "vars": [{"name": "x"}], "givens": []},
               {"claimed_answer": {"kind": "value", "payload": "0"}, "steps": []})
    q.put(r.verdict)


if __name__ == "__main__":
    q = mpc.Queue(); p = mpc.Process(target=_run, args=(q,)); t0 = time.time(); p.start(); p.join(90)
    if p.is_alive():
        p.terminate(); print("BUG verify() still running after 90 s (killed)")
    else:
        print("ok  verdict", q.get(), "in", round(time.time() - t0, 1), "s")
