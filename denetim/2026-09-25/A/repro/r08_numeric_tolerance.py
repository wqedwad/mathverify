"""num_equal's last rung (dps 80) accepts relative differences below 1e-70 as equality; exact-but-unequal
values that agree to 70+ significant digits are certified equal (claims and compute steps)."""
from _r import show
import sympy as sp, mpmath as mp
if __name__ == "__main__":
    print("GT: (10**50)**2 =", "10**100 != 10**100 + 1 -> sqrt(10**100+1) != 10**50 (exact integer argument)")
    print("GT: tanh(100) = 1 - 2/(e^200+1) < 1;  atan(10**80) = pi/2 - atan(10**-80) < pi/2;  pi is irrational, a 75-digit decimal is rational")
    E = lambda e: {"task": {"kind": "evaluate", "params": {"expr": e}}, "vars": [], "givens": []}
    S = lambda p, steps=(): {"claimed_answer": {"kind": "value", "payload": p}, "steps": list(steps)}
    show("sqrt(10**100 + 1) = 10**50", E("sqrt(10**100 + 1)"), S("10**50"), False)
    show("tanh(100) = 1", E("tanh(100)"), S("1"), False)
    show("atan(10**80) = pi/2", E("atan(10**80)"), S("pi/2"), False)
    show("10**80*pi = 10**80*pi + 1", E("10**80*pi"), S("10**80*pi + 1"), False)
    with mp.workdps(90):
        p75 = mp.nstr(+mp.pi, 75, strip_zeros=False)
    show("pi = 75-digit decimal", E("pi"), S(p75), False)
    st = {"id": "s1", "kind": "compute", "claim": "sqrt(10**100 + 1) = 10**50", "from": [], "text": ""}
    show("D-cell: compute step sqrt(10**100+1) = 10**50 in a correct solution",
         {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**2 - 5*x + 6 = 0"]},
         {"claimed_answer": {"kind": "set", "payload": "{2, 3}"}, "steps": [st]}, False)
