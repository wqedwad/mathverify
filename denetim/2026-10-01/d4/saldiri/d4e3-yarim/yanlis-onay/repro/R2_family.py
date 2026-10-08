"""D4E3-YO-2: claim_where_derivative tries a claim's undefined family only at n = 0, 1, -1, 2. Run as R1."""
from common import P, S, X, show


def der(f, givens=(), vars_=(X,)):
    return P("derivative", {"f": f, "var": "x"}, givens, vars_, shape="expression")


if __name__ == "__main__":
    XC = [{"name": "x", "domain": "real", "constraints": ["x > 30"]}]
    show([
        ("(log(x - 20))' = 1/(x - 20) + 0*cot(x)", der("log(x - 20)"), S("1/(x - 20) + 0*cot(x)", "expression")),
        ("(log(x - 20))' = cot(x)*tan(x)/(x - 20)", der("log(x - 20)"), S("cot(x)*tan(x)/(x - 20)", "expression")),
        ("(sqrt(x - 20))' = sin(x)/(2*sqrt(x - 20)*sin(x))", der("sqrt(x - 20)"),
         S("sin(x)/(2*sqrt(x - 20)*sin(x))", "expression")),
        ("(x**2)', given x > 10 = 2*x + 0*cot(4*x)", der("x**2", ["x > 10"]), S("2*x + 0*cot(4*x)", "expression")),
        ("(x*sin x)', given x > 10 = sin x + x cos x tan(4x) cot(4x)", der("x*sin(x)", ["x > 10"]),
         S("sin(x) + x*cos(x)*tan(4*x)*cot(4*x)", "expression")),
        ("(x**3)', constraint x > 30 = 3*x**2 + 0*csc(x)", der("x**3", (), XC), S("3*x**2 + 0*csc(x)", "expression")),
        ("ctrl (x**2)', given x > 10 = 2*x*sin(x)/sin(x) [4pi, 5pi among the samples]", der("x**2", ["x > 10"]),
         S("2*x*sin(x)/sin(x)", "expression")),
        ("ctrl antiderivative of 2x, given x > 10: x**2 + 0*cot(4*x)",
         P("antiderivative", {"integrand": "2*x", "var": "x"}, ["x > 10"], [X], shape="expression"),
         S("x**2 + 0*cot(4*x)", "expression")),
    ])
