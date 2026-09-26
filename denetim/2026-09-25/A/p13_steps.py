from common import *
import sympy as sp

def st(i, kind, claim, frm=None):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": frm or [], "text": ""}

def se_steps(eq, claim, steps, truth_ok, name, dod=None, vars_=None):
    return run(f"D-solve_eq[{name}]", ir("solve_equation", {"var": "x"}, vars_=vars_ or [{"name": "x"}], givens=[eq], dod=dod), sol("set", claim, steps), truth_ok)

def si_steps(ineq, claim, steps, truth_ok, name):
    return run(f"D-solve_ineq[{name}]", ir("solve_inequality", {"var": "x"}, givens=[ineq]), sol("interval", claim, steps), truth_ok)

def ev_steps(expr, claim, steps, truth_ok, name, givens=None, vars_=None):
    return run(f"D-evaluate[{name}]", ir("evaluate", {"expr": expr}, vars_=vars_ or [], givens=givens or []), sol("value", claim, steps), truth_ok)

if __name__ == "__main__":
    # control: correct steps
    se_steps("x**2 - 5*x + 6 = 0", "{2, 3}", [st(1, "eq", "(x - 2)*(x - 3) = 0"), st(2, "eq", "x in {2, 3}")], True, "control ok")
    se_steps("x**2 - 5*x + 6 = 0", "{2, 3}", [st(1, "compute", "2 + 3 = 6"), st(2, "eq", "x in {2, 3}")], False, "wrong arithmetic compute")
    # compute step numerically-equal-but-wrong
    ev_steps("sqrt(10**100 + 1) - 10**50", "0", [], False, "answer sqrt(1e100+1)-1e50 = 0")
    se_steps("x**2 - 5*x + 6 = 0", "{2, 3}", [st(1, "compute", "sqrt(10**100 + 1) = 10**50"), st(2, "eq", "x in {2, 3}")], False, "compute sqrt(1e100+1)=1e50")
    se_steps("x**2 - 5*x + 6 = 0", "{2, 3}", [st(1, "compute", "tanh(100) = 1"), st(2, "eq", "x in {2, 3}")], False, "compute tanh(100)=1")
    se_steps("x**2 - 5*x + 6 = 0", "{2, 3}", [st(1, "compute", "floor(x) + floor(-x) = -1"), st(2, "eq", "x in {2, 3}")], False, "compute floor identity")
    se_steps("x**2 - 5*x + 6 = 0", "{2, 3}", [st(1, "compute", "Abs(x - 2025) + Abs(x + 2025) = 4050"), st(2, "eq", "x in {2, 3}")], False, "compute |x-2025|+|x+2025|")
    # eq step with exactly-zero expression evaluated numerically
    se_steps("x**2 - 2*x - 1 = 0", "{1 - sqrt(2), 1 + sqrt(2)}", [st(1, "eq", "x**2 - 2*x - 1 < 0"), st(2, "eq", "x in {1 - sqrt(2), 1 + sqrt(2)}")], False, "eq strict at exact zero (<0)")
    se_steps("x**2 - 2*x - 1 = 0", "{1 - sqrt(2), 1 + sqrt(2)}", [st(1, "eq", "x**2 - 2*x - 1 >= 0"), st(2, "eq", "x in {1 - sqrt(2), 1 + sqrt(2)}")], True, "eq >=0 at exact zero (true step)")
    se_steps("x**2 + x - 1 = 0", "{-1/2 + sqrt(5)/2, -sqrt(5)/2 - 1/2}", [st(1, "eq", "x**2 + x - 1 <= 0")], True, "eq <=0 golden (true step)")
    # wrong factorisation that vanishes on the solution set
    se_steps("x**2 - 5*x + 6 = 0", "{2, 3}", [st(1, "eq", "x**2 - 5*x + 6 = 2*(x - 2)*(x - 3)"), st(2, "eq", "x in {2, 3}")], False, "wrong factor constant")
    # wrong steps in inequality solved by sampling
    si_steps("x**2 < 2", "(-sqrt(2), sqrt(2))", [st(1, "eq", "x < 1.4")], False, "x<1.4 for x^2<2")
    si_steps("x**2 - 5*x - 14 < 0", "(-2, 7)", [st(1, "eq", "x < 6")], False, "x<6 for (-2,7)")
    si_steps("x**2 - 5*x - 14 < 0", "(-2, 7)", [st(1, "eq", "x > -1.9")], False, "x>-1.9 for (-2,7)")
    si_steps("x**2 - 5*x - 14 < 0", "(-2, 7)", [st(1, "eq", "x**2 - 5*x - 14 = (x - 7)*(x + 2.01)")], False, "wrong factor 2.01")
    si_steps("x**2 - 5*x - 14 < 0", "(-2, 7)", [st(1, "eq", "x**2 - 5*x - 14 = (x - 7)*(x + 2)"), st(2, "eq", "-2 < x"), st(3, "eq", "x < 7")], True, "ineq correct steps")
    si_steps("(x - 3)/(x + 2) <= 0", "(-2, 3]", [st(1, "eq", "x != 3")], False, "wrong x!=3")
    # case analysis: wrong claim in a branch
    se_steps("Abs(x - 1) = 3", "{-2, 4}", [st(1, "case", "x - 1 >= 0"), st(2, "eq", "x - 1 = 3", ["s1"]), st(3, "case", "x - 1 < 0"), st(4, "eq", "x = -3", ["s3"]), st(5, "eq", "x in {-2, 4}")], False, "wrong claim in case branch")
    se_steps("Abs(x - 1) = 3", "{-2, 4}", [st(1, "case", "x - 1 >= 0"), st(2, "eq", "x - 1 = 3", ["s1"]), st(3, "case", "x - 1 < 0"), st(4, "eq", "1 - x = 3", ["s3"]), st(5, "eq", "x in {-2, 4}")], True, "correct case branches")
    # a wrong unrefuted step poisoning premises: a log equation where solve fails
    se_steps("x**2 - 5*x + 6 = 0", "{2, 3}", [st(1, "eq", "x**2 = 5*x - 7"), st(2, "eq", "x in {2, 3}")], False, "wrong step x^2=5x-7")
    # wrong step on integer word problem
    V2 = [{"name": "a", "domain": "positive_integer"}, {"name": "b", "domain": "positive_integer"}]
    ev_steps("a", "16", [st(1, "eq", "b = 30 - a"), st(2, "eq", "2*a + 4*(30 - a) = 86"), st(3, "eq", "a = 16")], False, "wrong substituted eq", givens=["a + b = 30", "2*a + 4*b = 88"], vars_=V2)
    ev_steps("a", "16", [st(1, "eq", "b = 30 - a"), st(2, "compute", "120 - 88 = 34"), st(3, "eq", "a = 16")], False, "wrong compute 120-88=34", givens=["a + b = 30", "2*a + 4*b = 88"], vars_=V2)
    summary()
