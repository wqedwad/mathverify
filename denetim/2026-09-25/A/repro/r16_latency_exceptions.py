"""MEDIUM: ~65 s in certify.algebra for a cubic with trig-form roots (timeout=8); caught layer exceptions."""
import time
from _r import show
if __name__ == "__main__":
    t0 = time.time()
    r = show("x**3 - 3*x + 1 = 0 (right, trig form)", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**3 - 3*x + 1 = 0"]},
             {"claimed_answer": {"kind": "set", "payload": "{2*cos(2*pi/9), 2*cos(4*pi/9), 2*cos(8*pi/9)}"}, "steps": []}, True)
    print(f"      elapsed {time.time() - t0:.1f}s; layer latencies:", [(l.layer, l.latency_ms) for l in r.layers])
    for label, ir, sol, exp in [
        ("simplify (a**2-b**2)/(a-b) -> a - b (wrong)", {"task": {"kind": "simplify_expression", "params": {"expr": "(a**2 - b**2)/(a - b)"}}, "vars": [{"name": "a"}, {"name": "b"}], "givens": []},
         {"claimed_answer": {"kind": "expression", "payload": "a - b"}, "steps": []}, False),
        ("count_solutions cbrt(x) <= 1 on -5..5", {"task": {"kind": "count_solutions", "params": {"bounds": {"x": ["-5", "5"]}}}, "vars": [{"name": "x", "domain": "integer"}], "givens": ["cbrt(x) <= 1"]},
         {"claimed_answer": {"kind": "count", "payload": 7}, "steps": []}, True),
        ("count_integers x*log(2) < log(8), x>=0", {"task": {"kind": "count_integers", "params": {"var": "x"}}, "vars": [{"name": "x", "domain": "nonneg_integer"}], "givens": ["x*log(2) < log(8)"]},
         {"claimed_answer": {"kind": "count", "payload": 3}, "steps": []}, True)]:
        r = show(label, ir, sol, exp)
        print("      reasons:", [l.evidence.get("reason") for l in r.layers])
