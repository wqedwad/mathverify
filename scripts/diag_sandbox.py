import time, sympy as sp
from mathverify.sandbox import get_sandbox, SandboxTimeout

if __name__ == "__main__":
    sb = get_sandbox()
    x = sp.Symbol('x')
    print("call1:", sb.call("mathverify.sandbox.ops:simplify_diff", x+1, x+1), "mem_mode:", sb.mem_mode)
    t0 = time.time()
    try:
        sb.call("mathverify.sandbox.ops:integrate_symbolic", sp.exp(sp.sin(x)**7)*sp.log(x), x, timeout=1.0)
    except SandboxTimeout as e:
        print("timeout ok:", e, f"{time.time()-t0:.1f}s")
    print("call after restart:", sb.call("mathverify.sandbox.ops:simplify_diff", 2*x, x+x))
    print("stats calls/timeouts/restarts:", sb.calls, sb.timeouts, sb.restarts)
    sb.close()
    print("closed cleanly")
