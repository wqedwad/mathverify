from common import *
import json, time
from mathverify.verifier import verify
if __name__ == "__main__":
    cases = [("solve_equation", "x**3 - 3*x + 1 = 0", "set", "{2*cos(2*pi/9), 2*cos(4*pi/9), 2*cos(8*pi/9)}"),
             ("solve_equation", "x**3 - 3*x + 1 = 0", "set", "{2*cos(2*pi/9), 2*cos(4*pi/9), 2*cos(8*pi/9), 1}"),
             ("solve_equation", "x**5 - x - 1 = 0", "set", "{1}"),
             ("solve_inequality", "x**3 - 3*x + 1 > 0", "interval", "(2*cos(8*pi/9), 2*cos(4*pi/9)) U (2*cos(2*pi/9), oo)")]
    for kind, g, ck, claim in cases:
        t0 = time.time()
        r = verify(ir(kind, {"var": "x"}, givens=[g]), sol(ck, claim))
        print(f"{kind} {g} {claim} -> {r.verdict} total={time.time()-t0:.1f}s", [(l.layer, l.verdict, l.latency_ms) for l in r.layers])
