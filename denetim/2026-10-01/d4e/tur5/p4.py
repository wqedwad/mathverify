"""p4: Piecewise gaps in sibling tasks (extremum, derivative at a point, tangent, solve), solved_pins definedness."""
import sys
from ortak import *

AR = {"name": "a", "domain": "real"}
AP = {"name": "a", "domain": "positive_real"}
PWG = "Piecewise((x**2, x < 0), (x**2, x > 0))"


def cases():
    out = []
    # extremum over a gap: min of x**2 off 0 is not attained
    out.append(("ext min PW gap at 0 (no interval): 0", ext(PWG, "min", None), sol("0"), NOTOK, None))
    out.append(("ext min PW gap at 0 on [-1,1]: 0", ext(PWG, "min", "[-1, 1]"), sol("0"), NOTOK, None))
    out.append(("ext max -PW gap on [-1,1]: 0", ext("Piecewise((-x**2, x < 0), (-x**2, x > 0))", "max", "[-1, 1]"),
                sol("0"), NOTOK, None))
    out.append(("ext min PW gap: argmin 0?", ext(PWG, "min", "[-1, 1]"), sol("0"), NOTOK, None))
    # derivative at the gap point, tangent there
    out.append(("der PW gap at 0: 0", der(PWG, "0"), sol("0"), NOTOK, None))
    out.append(("tan PW gap at 0: y = 0", tan(PWG, "0"), sol("y = 0", "equation"), NOTOK, None))
    # claim Piecewise with a gap where f has a derivative
    out.append(("(x^2)' claim PW gap at 0", der("x**2"), sol("Piecewise((2*x, x < 0), (2*x, x > 0))", "expression"),
                NOTOK, None))
    out.append(("(x^2)' claim PW gap [0,1]", der("x**2"), sol("Piecewise((2*x, x < 0), (2*x, x > 1))", "expression"),
                NOTOK, None))
    out.append(("(x^2)' claim PW gap at 1 Ne-written", der("x**2"),
                sol("Piecewise((2*x, x < 1), (2*x, x > 1))", "expression"), NOTOK, None))
    out.append(("(x^2)' ctrl claim PW full", der("x**2"),
                sol("Piecewise((2*x, x <= 0), (2*x, x > 0))", "expression"), NOTNO, None))
    # solve with an interval gap
    out.append(("solve PW((x, x<0),(x, x>1)) = 1/2 : {1/2}",
                ir("solve_equation", {"var": "x", "equation": "Piecewise((x, x < 0), (x, x > 1)) = 1/2"}),
                sol("{1/2}", "set"), NOTOK, None))
    out.append(("solve ineq PW((x, x<0),(x, x>1)) > -1 : (-1, oo)",
                ir("solve_inequality", {"var": "x", "inequality": "Piecewise((x, x < 0), (x, x > 1)) > -1"}),
                sol("Interval.open(-1, oo)", "interval"), NOTOK, None))
    # limit of a Piecewise defined nowhere near the point: lim_{x->1/2} PW((x, x<0),(x, x>1)) DNE/undefined
    out.append(("lim x->1/2 PW gap [0,1]: 1/2", lim("Piecewise((x, x < 0), (x, x > 1))", "1/2"), sol("1/2"), NOTOK, None))
    # integral over the gap interval
    out.append(("evaluate Integral(PW gap [0,1], (t, 0, 1)) = 1/2",
                ev1("Integral(Piecewise((t, t < 0), (t, t > 1)), (t, 0, 1))"), sol("1/2"), NOTOK, None))
    out.append(("definite integral PW gap [0,1] over [0,1]: 1/2",
                ir("definite_integral", {"integrand": "Piecewise((x, x < 0), (x, x > 1))", "var": "x", "lo": "0", "hi": "1"},
                   shape="scalar"), sol("1/2"), NOTOK, None))
    # solved_pins: a value fixed in another form that leaves f undefined as written
    out.append(("2a=4: (a x^2 + 0*sqrt(1-a))' = 4x", der("a*x**2 + 0*sqrt(1 - a)", givens=["2*a = 4"], vars_=[X, AR]),
                sol("4*x", "expression"), NOTOK, None))
    out.append(("2a=4: lim x->0 a x + 0*log(1-a) = 0", lim("a*x + 0*log(1 - a)", "0", givens=["2*a = 4"], vars_=[X, AR]),
                sol("0"), NOTOK, None))
    out.append(("2a=4: max a x + 0*sqrt(1-a) on [0,1] = 2", ext("a*x + 0*sqrt(1 - a)", "max", "[0, 1]", givens=["2*a = 4"],
                                                              vars_=[X, AR]), sol("2"), NOTOK, None))
    out.append(("2a=4: tangent a x^2 + 0*sqrt(1-a) at 1", tan("a*x**2 + 0*sqrt(1 - a)", "1", givens=["2*a = 4"],
                                                            vars_=[X, AR]), sol("y = 4*x - 2", "equation"), NOTOK, None))
    out.append(("2a=4: antideriv of a x + 0*sqrt(1-a) = x^2", anti("a*x + 0*sqrt(1 - a)", givens=["2*a = 4"], vars_=[X, AR]),
                sol("x**2", "expression"), NOTOK, None))
    out.append(("a^2=4 a real: (a x^2)' = 4x", der("a*x**2", givens=["a**2 = 4"], vars_=[X, AR]),
                sol("4*x", "expression"), NOTOK, None))
    out.append(("a^2=4 a real: lim (a x)/x x->0 = 2", lim("a*x/x", "0", givens=["a**2 = 4"], vars_=[X, AR]),
                sol("2"), NOTOK, None))
    out.append(("|a|=2: max a*x on [0,1] = 2", ext("a*x", "max", "[0, 1]", givens=["Abs(a) = 2"], vars_=[X, AR]),
                sol("2"), NOTOK, None))
    out.append(("sin a = 0, 0<a<4: (a x)' = pi", der("a*x", givens=["sin(a) = 0"], vars_=[X, {"name": "a", "domain": "real", "constraints": ["0 < a", "a < 4"]}]),
                sol("pi", "expression"), NOTNO, None))
    out.append(("sin a = 0, 0<a<7: (a x)' = pi", der("a*x", givens=["sin(a) = 0"], vars_=[X, {"name": "a", "domain": "real", "constraints": ["0 < a", "a < 7"]}]),
                sol("pi", "expression"), NOTOK, None))
    out.append(("floor(a)=1 : (a x)' = 1", der("a*x", givens=["floor(a) = 1"], vars_=[X, AR]),
                sol("1", "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
