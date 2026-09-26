from common import *
import sympy as sp

def ev(expr, claim, truth_ok, givens=None, vars_=None, name="", options=None, option=None, dod=None, functions=None, steps=None, params=None):
    p = {"expr": expr} if expr else {}
    if params: p.update(params)
    vs = vars_ if vars_ is not None else []
    s = sol("value", claim, steps, option=option)
    return run(f"evaluate[{name or expr}|{givens}]={claim}", ir("evaluate", p, vars_=vs, givens=givens or [], options=options, dod=dod, functions=functions), s, truth_ok)

if __name__ == "__main__":
    # pure computations: exactness
    ev("sqrt(2)", "1.4142135623730951", False)
    ev("sqrt(2)", "1.41421356237309504880168872420969807856967187537694807317667973799", False, name="sqrt2 65 digits")
    ev("pi", "3.14159265358979", False)
    ev("pi", "355/113", False)
    ev("E**(pi*sqrt(163))", "262537412640768744", False)
    ev("10**30 + 1", "10**30", False)
    ev("1/3", "0.333333333333333333333333333333333333333333333333333", False, name="1/3 long decimal")
    ev("1/3", "0.3333333333333333", False, name="1/3 16dig")
    ev("2/4", "0.5", True); ev("3/2", "1.5", True); ev("1/8", "0.125", True)
    ev("sqrt(12)", "2*sqrt(3)", True); ev("1/sqrt(2)", "sqrt(2)/2", True); ev("sqrt(8) + sqrt(18)", "5*sqrt(2)", True)
    ev("(sqrt(3) + 1)/(sqrt(3) - 1)", "2 + sqrt(3)", True); ev("(sqrt(3) + 1)/(sqrt(3) - 1)", "2 + sqrt(2)", False)
    ev("sqrt(5 + 2*sqrt(6))", "sqrt(2) + sqrt(3)", True)
    ev("sin(pi/6)", "1/2", True); ev("sin(30°)", "1/2", True, name="sin 30deg")
    ev("cos(pi/5)", "(1 + sqrt(5))/4", True); ev("cos(pi/5)", "(1 + sqrt(5))/5", False)
    ev("log(8, 2)", "3", True); ev("log(8)/log(2)", "3", True)
    ev("%25 * 80", "20", True, name="percent25"); ev("25% * 80", "20", True, name="percent25b")
    ev("binomial(6, 3)", "20", True); ev("factorial(5)", "120", True)
    ev("gcd(84, 120)", "12", True); ev("lcm(4, 6)", "12", True)
    # Turkish decimal comma
    ev("5/2", "2,5", True, name="decimal comma")
    # undefined targets
    ev("1/0", "0", False); ev("0/0", "1", False); ev("log(0)", "0", False)
    ev("x/x", "1", False, vars_=[{"name": "x"}], givens=["x = 0"], name="x/x at 0")
    ev("sqrt(-4)", "2*I", False, name="sqrt(-4) real problem")
    ev("tan(pi/2)", "0", False)
    ev("(-8)**(1/3)", "-2", True, name="cube root -8")
    ev("cbrt(-8)", "-2", True, name="cbrt(-8)")
    ev("root(-27, 3)", "-3", True, name="root(-27,3)")
    ev("0**0", "1", None, name="0**0")
    ev("asin(2)", "pi/2", False)
    # with givens
    V = [{"name": "a"}, {"name": "b"}]
    ev("a*b", "6", True, givens=["a + b = 5", "a - b = 1"], vars_=V)
    ev("a*b", "7", False, givens=["a + b = 5", "a - b = 1"], vars_=V)
    ev("a**2 + b**2", "13", True, givens=["a + b = 5", "a*b = 6"], vars_=V)
    ev("a - b", "1", False, givens=["a + b = 5", "a*b = 6"], vars_=V, name="a-b ambiguous")
    ev("a - b", "1", True, givens=["a + b = 5", "a*b = 6", "a > b"], vars_=V, name="a-b with ineq")
    ev("a", "3", True, givens=["a**2 = 9"], vars_=[{"name": "a", "domain": "positive_real"}])
    ev("a", "3", False, givens=["a**2 = 9"], vars_=[{"name": "a"}], name="a ambiguous sign")
    ev("a", "3", True, givens=["a**2 = 9"], vars_=[{"name": "a"}], dod="a > 0", name="a with dod")
    ev("a", "-3", False, givens=["a**2 = 9"], vars_=[{"name": "a"}], dod="a > 0", name="a -3 with dod")
    ev("a", "-3", False, givens=["a**2 = 9"], vars_=[{"name": "a"}], dod="a > 0", options={"A": "-3", "B": "1", "C": "5"}, option="A", name="a -3 dod opts")
    ev("a", "3", True, givens=["a**2 = 9"], vars_=[{"name": "a"}], dod="a > 0", options={"A": "-3", "B": "3", "C": "5"}, option="B", name="a 3 dod opts")
    # integer word problem
    V2 = [{"name": "a", "domain": "positive_integer"}, {"name": "b", "domain": "positive_integer"}]
    ev("a", "16", True, givens=["a + b = 30", "2*a + 4*b = 88"], vars_=V2)
    ev("a", "14", False, givens=["a + b = 30", "2*a + 4*b = 88"], vars_=V2)
    ev("a + b", "9", None, givens=["3*a + 5*b = 41"], vars_=V2, name="diophantine a+b")
    # 3a+5b=41 positive ints: (2,7),(7,4),(12,1) -> a+b in {9,11,13} -> not unique
    ev("a + b", "9", False, givens=["3*a + 5*b = 41"], vars_=V2, options={"A": "9", "B": "10", "C": "12"}, option="A", name="diophantine opts")
    # sqrt target definedness under givens
    ev("sqrt(a - 5)", "0", False, givens=["a = 3"], vars_=[{"name": "a"}], name="sqrt undefined")
    ev("1/sqrt(a)", "1", False, givens=["a**2 = 0"], vars_=[{"name": "a"}], name="1/sqrt(0)")
    ev("(a - 3)/(a - 3)", "1", False, givens=["a = 3"], vars_=[{"name": "a"}], name="(a-3)/(a-3) at 3")
    ev("a**2/a", "0", False, givens=["a**2 = 0"], vars_=[{"name": "a"}], name="a^2/a at 0")
    ev("sqrt(a)**2", "-1", False, givens=["a = -1"], vars_=[{"name": "a"}], name="sqrt(a)^2 at -1")
    ev("log(a) - log(a)", "0", False, givens=["a = -2"], vars_=[{"name": "a"}], name="log-log at -2")
    # functions
    F = [{"name": "f", "expr": "(2*x + 3)/(x - 1)", "args": ["x"], "params": []}]
    ev("f(2)", "7", True, functions=F); ev("f(2)", "8", False, functions=F)
    ev("f(1)", "5", False, functions=F, name="f(1) undefined")
    F2 = [{"name": "f", "expr": "x**2/x", "args": ["x"], "params": []}]
    ev("f(0)", "0", False, functions=F2, name="f=x^2/x at 0")
    F3 = [{"name": "f", "expr": "sqrt(x)**2", "args": ["x"], "params": []}]
    ev("f(-4)", "-4", False, functions=F3, name="f=sqrt(x)^2 at -4")
    F4 = [{"name": "f", "expr": "x/x", "args": ["x"], "params": []}]
    ev("f(0) + 1", "2", False, functions=F4, name="f=x/x at 0")
    # symbolic expression answers (expr with free vars, no givens)
    ev("(x**2 - 1)/(x - 1)", "x + 1", True, vars_=[{"name": "x"}], name="(x2-1)/(x-1)")
    ev("sqrt(x**2)", "x", False, vars_=[{"name": "x"}], name="sqrt(x^2)=x")
    ev("sqrt(x**2)", "Abs(x)", True, vars_=[{"name": "x"}], name="sqrt(x^2)=|x|")
    summary()
