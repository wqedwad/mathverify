from common import *

def se(eq, payload, truth_ok, kind="set", options=None, option=None, name="", shape="set"):
    return run(f"fmt-solve_eq[{name or payload}]", ir("solve_equation", {"var": "x"}, givens=[eq], options=options, shape=shape), sol(kind, payload, option=option), truth_ok)

def si(ineq, payload, truth_ok, kind="interval", options=None, option=None, name=""):
    return run(f"fmt-solve_ineq[{name or payload}]", ir("solve_inequality", {"var": "x"}, givens=[ineq], options=options, shape="interval"), sol(kind, payload, option=option), truth_ok)

if __name__ == "__main__":
    E = "log(x - 1) + log(x - 3) = log(3)"
    for p, k in [("x = 4", "value"), ("x=4", "set"), ("{x = 4}", "set"), ("4", "value"), ("x ∈ {4}", "set"), ("Ç = {4}", "set"),
                 ("{4}", "set"), ("\\{4\\}", "set"), ("$\\{4\\}$", "set"), ("\\boxed{4}", "value"), ("{ 4 }", "set"), ("4.0", "value"), ("{4.0}", "set"), ("16/4", "value"), ("sqrt(16)", "value")]:
        se(E, p, True, kind=k, name=f"{k}:{p}")
    E2 = "x**2 - 5*x + 6 = 0"
    for p, k in [("x = 2 veya x = 3", "set"), ("x=2, x=3", "set"), ("{2; 3}", "set"), ("2 ve 3", "set"), ("{3, 2}", "set"), ("2, 3", "set"), ("{2,3}", "set"), ("[2, 3]", "set")]:
        se(E2, p, True, kind=k, name=f"{k}:{p}")
    # none / empty with MC options in Turkish
    OPT = {"A": "{1}", "B": "{2}", "C": "{1, 2}", "D": "{3}", "E": "Çözüm yok"}
    se("x/(x - 3) = 3/(x - 3) + 2", "{}", True, options=OPT, option="E", name="empty set + option 'Çözüm yok'")
    se("x/(x - 3) = 3/(x - 3) + 2", None, True, kind="none", options=OPT, option="E", name="none + option 'Çözüm yok'")
    se("x/(x - 3) = 3/(x - 3) + 2", "∅", True, kind="set", options=dict(OPT, E="∅"), option="E", name="∅ + option ∅")
    se("x/(x - 3) = 3/(x - 3) + 2", "{}", True, kind="set", options=dict(OPT, E="Boş küme"), option="E", name="{} + option 'Boş küme'")
    # interval notation variants
    I = "x**2 - 5*x - 14 < 0"
    for p in ["(-2, 7)", "]-2, 7[", "(-2; 7)", "-2 < x < 7", "Interval.open(-2, 7)", "x ∈ (-2, 7)", "(−2, 7)", "( -2 , 7 )"]:
        si(I, p, True, name=p)
    si("x**2 - 5*x - 14 > 0", "(-oo, -2) ∪ (7, +∞)", True, name="+inf")
    si("x**2 - 5*x - 14 > 0", "R - [-2, 7]", True, name="R - [-2,7]")
    si("x**2 - 5*x - 14 > 0", "ℝ \\ [-2, 7]", True, name="R backslash [-2,7]")
    si("x**2 - 5*x - 14 > 0", "x < -2 or x > 7", True, kind="condition", name="condition or")
    si("x >= 3", "x >= 3", True, kind="condition", name="condition x>=3")
    si("x**2 + 1 < 0", "(5, 1)", False, name="reversed interval as empty")
    si("x**2 + 1 < 0", "Ø", True, kind="set", name="Ø (O-stroke)")
    si("x**2 - 5*x - 14 < 0", "(-2, 7)", True, options={"A": "(-2, 7)", "B": "[-2, 7]"}, option="A", name="mc A")
    si("x**2 - 5*x - 14 < 0", "(-2, 7)", True, options={"A": "-2 < x < 7", "B": "[-2, 7]"}, option="A", name="mc A relation option")
    # prose suffix
    run("prose '5 değil'", ir("evaluate", {"expr": "2 + 3"}, vars_=[]), sol("value", "5 değil"), False)
    run("prose '5 olamaz'", ir("evaluate", {"expr": "2 + 3"}, vars_=[]), sol("value", "5 olamaz"), False)
    summary()
