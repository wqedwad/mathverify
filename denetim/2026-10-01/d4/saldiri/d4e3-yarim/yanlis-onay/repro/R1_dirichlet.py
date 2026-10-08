"""D4E3-YO-1: Dirichlet's test reads SymPy's limit of h with a free symbol as a proof (h = t/(x**2*t**2 + 1) -> 0
'for every x', false at x = 0). Run: PYTHONPATH=<copy>/src python R1_dirichlet.py"""
from common import P, S, X, XP, T, Y, show

I0 = "Integral(t*sin(t)/(x**2*t**2 + 1), (t, 1, oo))"           # converges iff x != 0
I1 = "Integral(sin(t)*t/((x - 1)**2*t**2 + 1), (t, 1, oo))"      # converges iff x != 1
I4 = "Integral(sin(t)*(x**2*t + 1)/(x**2*t**2 + 1), (t, 1, oo))"  # converges iff x != 0
XT = [X, T]

if __name__ == "__main__":
    show([
        ("derivative x + 0*I0(x) at 0: 1", P("derivative", {"f": f"x + 0*{I0}", "var": "x", "at": "0"}, vars_=XT), S("1")),
        ("tangent x**3 + 0*I1(x) at 1: y = 3x - 2",
         P("tangent_line", {"f": f"x**3 + 0*{I1}", "var": "x", "at": "1", "dep": "y"}, vars_=XT + [Y], shape="equation"),
         S("y = 3*x - 2", "equation")),
        ("solve x**2 - 1 + 0*I1(x) = 0: {-1, 1}", P("solve_equation", {"var": "x", "equation": f"x**2 - 1 + 0*{I1} = 0"},
                                                     vars_=XT, shape="set"), S("{-1, 1}", "set")),
        ("solve x**2 + 0*I1(x) <= 1: [-1, 1]", P("solve_inequality", {"var": "x", "inequality": f"x**2 + 0*{I1} <= 1"},
                                                 vars_=XT, shape="set"), S("Interval(-1, 1)", "interval")),
        ("max -x**2 + 0*I4(x) on [-1, 1]: 0", P("extremum", {"f": f"-x**2 + 0*{I4}", "var": "x", "which": "max",
                                                              "interval": "[-1, 1]"}, vars_=XT), S("0")),
        ("series_sum k + 0*I0(k), k = -1..1: 0", P("series_sum", {"term": f"k + 0*{I0.replace('x', 'k')}", "var": "k", "lo": -1,
                                                                   "hi": 1}, vars_=[{"name": "k", "domain": "integer"}, T]), S("0")),
        ("evaluate 0*I(a) + 1, a nonneg_real: 1", P("evaluate", {"expr": "0*Integral(t*sin(t)/(a*t**2 + 1), (t, 1, oo)) + 1"},
                                                    vars_=[{"name": "a", "domain": "nonneg_real"}, T]), S("1")),
        ("[pre-existing, sign declared] derivative x**3 + 0*I1(x) at 1, x positive_real: 3",
         P("derivative", {"f": f"x**3 + 0*{I1}", "var": "x", "at": "1"}, vars_=[XP, T]), S("3")),
    ])
