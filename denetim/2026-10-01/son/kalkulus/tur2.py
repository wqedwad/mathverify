"""Cases of the second round on wip/son-kalkulus (kararlar.txt "EK 6", 21-22 Oct 2026), group G of sonda.py:

    k1, k1b  YO-K1 = RK-PW-EQ = SK-RK-2: a Piecewise with a point branch of its own (at(diff), the pinned diff, an
             option, f' + f, f'(x) = 0 and f'(x) > 0, a step, the derivative task at the point, order 2)
    k2       YO-K2 + SK-RK-3: the derivative function at a kink where f has a derivative and SymPy's formula another
             value (the point branch's 0, sign(0) = 0)
    k3       YO-K3: Derivative(...), diff(f, (x, n)) and nested diff keep where the derivative exists
    k4       YO-K4: R - A U B written without brackets, read both ways; R - ({2} U {3}) read
    k5       YO-K5: an integer n with n >= L declared read on its region, as a positive integer is
    k6       SK-RK-6: |a|**(2k) of a real a is no switch
    k7       SK-RK-7: (a*x + b)**irrational primitives (no layer exception in the merged state)
    k8       controls and siblings: removable transcendental points, sign products, x*|x|

Kept out of pyflakes and pytest like the rest of denetim/.
"""

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
OK, NO, OKU, NOU = {"CORRECT"}, {"INCORRECT"}, {"CORRECT", "UNKNOWN"}, {"INCORRECT", "UNKNOWN"}


def ir(kind, params, givens=(), vars_=None, shape="scalar", **extra):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    d.update({k: v for k, v in extra.items() if v is not None})
    return d


def sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": "compute", "claim": c, "from": [], "text": ""}
                                            for i, c in enumerate(steps)]}


def fn(body):
    return [{"name": "f", "expr": body, "args": ["x"], "params": []}] if body else None


def ev(expr, f=None, givens=(), vars_=None, options=None):
    return ir("evaluate", {"expr": expr}, givens, vars_, functions=fn(f), options=options)


def der(f, at=None, vars_=None, order=None):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    if order is not None:
        p["order"] = order
    return ir("derivative", p, (), vars_, "scalar" if at is not None else "expression")


def se(eq, f=None):
    return ir("solve_equation", {"var": "x", "equation": eq}, (), None, "set", functions=fn(f))


def si(ineq, f=None):
    return ir("solve_inequality", {"var": "x", "inequality": ineq}, (), None, "interval", functions=fn(f))


PT = "Piecewise((x**2, x < 1), (1, Eq(x, 1)), (2*x - 1, x > 1))"       # f'(1) = 2
PT6 = "Piecewise((2*x + 1, x < 1), (3, Eq(x, 1)), (x**2 + 2, x > 1))"   # f'(1) = 2
NE1 = "Piecewise((x**2, Ne(x, 1)), (1, Eq(x, 1)))"                     # f'(1) = 2
NE3 = "Piecewise((x**2, Ne(x, 3)), (9, Eq(x, 3)))"                     # f'(3) = 6
REM1 = "Piecewise(((x**2 - 1)/(x - 1), Ne(x, 1)), (2, Eq(x, 1)))"      # x + 1, f'(1) = 1
REM2 = "Piecewise(((x**2 - 4)/(x - 2), Ne(x, 2)), (4, Eq(x, 2)))"      # x + 2, f'(2) = 1
CUBE = "Piecewise((x**3, x < 1), (1, Eq(x, 1)), (x**3, x > 1))"        # f'(1) = 3, f''(1) = 6
X3 = "Piecewise((x**3, Ne(x, 2)), (8, Eq(x, 2)))"                      # f'(2) = 12
XE = "Piecewise((x*exp(x), Ne(x, 0)), (0, Eq(x, 0)))"                  # f'(0) = 1
PT1 = "Piecewise((x**2 + 1, x < 1), (2, Eq(x, 1)), (2*x, x > 1))"      # f'(1) = 2
XS = "Piecewise((x*sin(1/x), Ne(x, 0)), (0, Eq(x, 0)))"                 # no f'(0)
X2S = "Piecewise((x**2*sin(1/x), Ne(x, 0)), (0, Eq(x, 0)))"             # f'(0) = 0
JUMP = "Piecewise((x**2, x < 1), (5, Eq(x, 1)), (2*x - 1, x > 1))"      # no f'(1)
MC = {"A": "0", "B": "1", "C": "2", "D": "3", "E": "4"}


def at_cases(f, p, right, wrong=("0",), order=1):
    d = "diff(f(x), x)" if order == 1 else f"diff(f(x), x, {order})"
    out = [(f"at {f} {p} right={right}", ev(f"at({d}, x, {p})", f), sol(right), OK)]
    out += [(f"at {f} {p} wrong={w}", ev(f"at({d}, x, {p})", f), sol(w), NOU) for w in wrong]
    return out


def g_k1():
    c = []
    for f, p, r in ((PT, 1, "2"), (PT6, 1, "2"), (NE1, 1, "2"), (NE3, 3, "6"), (REM1, 1, "1"), (REM2, 2, "1"),
                    (CUBE, 1, "3"), (X3, 2, "12"), (XE, 0, "1"), (PT1, 1, "2")):
        c += at_cases(f, p, r)
        c.append((f"der-at {f} {p} right={r}", der(f, at=str(p)), sol(r), OKU))
        c.append((f"der-at {f} {p} wrong=0", der(f, at=str(p)), sol("0"), NOU))
    c.append(("at XS 0 claim 0", ev("at(diff(f(x), x), x, 0)", XS), sol("0"), NOU))
    c.append(("at X2S 0 claim 0", ev("at(diff(f(x), x), x, 0)", X2S), sol("0"), OKU))
    c.append(("at JUMP 1 claim 0", ev("at(diff(f(x), x), x, 1)", JUMP), sol("0"), NOU))
    c.append(("at JUMP 1 claim 2", ev("at(diff(f(x), x), x, 1)", JUMP), sol("2"), NOU))
    c.append(("at CUBE f''(1)=6", ev("at(diff(f(x), x, 2), x, 1)", CUBE), sol("6"), OKU))
    c.append(("at CUBE f''(1)=0", ev("at(diff(f(x), x, 2), x, 1)", CUBE), sol("0"), NOU))
    # given x = p
    c.append(("given x=1 PT diff=2", ev("diff(f(x), x)", PT, givens=["x = 1"]), sol("2"), OKU))
    c.append(("given x=1 PT diff=0", ev("diff(f(x), x)", PT, givens=["x = 1"]), sol("0"), NOU))
    # options
    c.append(("MC PT A=0", ev("at(diff(f(x), x), x, 1)", PT, options=MC), sol("0", option="A"), NOU))
    c.append(("MC PT C=2", ev("at(diff(f(x), x), x, 1)", PT, options=MC), sol("2", option="C"), OKU))
    c.append(("MC REM2 A=0", ev("at(diff(f(x), x), x, 2)", REM2, options=MC), sol("0", option="A"), NOU))
    c.append(("MC REM2 B=1", ev("at(diff(f(x), x), x, 2)", REM2, options=MC), sol("1", option="B"), OKU))
    # composite
    c.append(("f'+f REM2 = 5", ev("at(diff(f(x), x), x, 2) + f(2)", REM2), sol("5"), OKU))
    c.append(("f'+f REM2 = 4", ev("at(diff(f(x), x), x, 2) + f(2)", REM2), sol("4"), NOU))
    c.append(("f'+f REM1 = 3", ev("at(diff(f(x), x), x, 1) + f(1)", REM1), sol("3"), OKU))
    # solution sets
    for f, right, wrongs in ((NE1, "{0}", ("{0, 1}",)), (PT, "{0}", ("{0, 1}",)), (PT6, "EmptySet", ("{1}",)),
                             (CUBE, "{0}", ("{0, 1}",)), (X3, "{0}", ("{0, 2}",))):
        c.append((f"se f'=0 {f} right {right}", se("diff(f(x), x) = 0", f), sol(right, kind="set"), OKU))
        for w in wrongs:
            c.append((f"se f'=0 {f} wrong {w}", se("diff(f(x), x) = 0", f), sol(w, kind="set"), NOU))
    c.append(("se f'=6 NE3 {3}", se("diff(f(x), x) = 6", NE3), sol("{3}", kind="set"), OKU))
    c.append(("se f'=6 NE3 empty", se("diff(f(x), x) = 6", NE3), sol("EmptySet", kind="set"), NOU))
    c.append(("si f'>0 X3 R-{0}", si("diff(f(x), x) > 0", X3), sol("Union(Interval.open(-oo, 0), Interval.open(0, oo))", kind="interval"), OKU))
    c.append(("si f'>0 X3 R-{0,2}", si("diff(f(x), x) > 0", X3), sol("Union(Interval.open(-oo, 0), Interval.open(0, 2), Interval.open(2, oo))", kind="interval"), NOU))
    # step
    c.append(("step X3 =12", ev("at(diff(f(x), x), x, 2)", X3), sol("12", steps=["at(diff(f(x), x), x, 2) = 12"]), OKU))
    return c


def g_k2():
    c = []
    for f, right, wrong in (
            (PT6, ("Piecewise((2, x < 1), (2*x, x >= 1))", "Piecewise((2, x <= 1), (2*x, x > 1))"),
             "Piecewise((2, x < 1), (0, Eq(x, 1)), (2*x, x > 1))"),
            (PT, ("Piecewise((2*x, x < 1), (2, x >= 1))",), "Piecewise((2*x, x < 1), (0, Eq(x, 1)), (2, x > 1))"),
            (NE1, ("2*x",), "Piecewise((2*x, Ne(x, 1)), (0, Eq(x, 1)))"),
            (CUBE, ("3*x**2",), "Piecewise((3*x**2, Ne(x, 1)), (0, Eq(x, 1)))")):
        for r in right:
            c.append((f"der {f} right {r}", der(f), sol(r, kind="expression"), OKU))
        c.append((f"der {f} wrong {wrong}", der(f), sol(wrong, kind="expression"), NOU))
    for f, r in (("cbrt(x)**3", "1"), ("cbrt(x**3)", "1"), ("cbrt(x**3) + x**2", "1 + 2*x"),
                 ("cbrt((x - 1)**3)", "1"), ("cbrt(8*x**3)", "2"), ("Abs(x)*sign(x)", "1")):
        c.append((f"der {f} right {r}", der(f), sol(r, kind="expression"), OKU))
        c.append((f"der {f} wrong 0", der(f), sol("0", kind="expression"), NOU))
        c.append((f"der {f} wrong sign(x)**2", der(f), sol("sign(x)**2", kind="expression"), NOU))
    return c


def g_k1b():
    c = []
    J2 = "Piecewise((x**2, x < 1), (x**2 + 5, x >= 1))"                 # jump at 1: no f'(1), no f''(1)
    c.append(("der-at J2 order2 claim 2", der(J2, at="1", order=2), sol("2"), NOU))
    c.append(("der-at J2 order2 dne", der(J2, at="1", order=2), {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}, OKU))
    c.append(("at J2 f''(1)=2", ev("at(diff(f(x), x, 2), x, 1)", J2), sol("2"), NOU))
    c.append(("der-at CUBE order2 claim 6", der(CUBE, at="1", order=2), sol("6"), OKU))
    c.append(("der-at CUBE order2 claim 0", der(CUBE, at="1", order=2), sol("0"), NOU))
    c.append(("der-at CUBE order2 dne", der(CUBE, at="1", order=2), {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}, NOU))
    c.append(("der-at PT order2 dne", der(PT, at="1", order=2), {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}, OKU))
    c.append(("der-at PT order2 0", der(PT, at="1", order=2), sol("0"), NOU))
    SG = "Abs(x)*sign(x)"
    c.append(("se SG f'=0 {0}", se("diff(f(x), x) = 0", SG), sol("{0}", kind="set"), NOU))
    c.append(("se SG f'=0 empty", se("diff(f(x), x) = 0", SG), sol("EmptySet", kind="set"), OKU))
    c.append(("se CB3 f'=0 {0}", se("diff(f(x), x) = 0", "cbrt(x)**3"), sol("{0}", kind="set"), NOU))
    c.append(("si SG f'>0 R-{0}", si("diff(f(x), x) > 0", SG), sol("Union(Interval.open(-oo, 0), Interval.open(0, oo))", kind="interval"), NOU))
    c.append(("si SG f'>0 R", si("diff(f(x), x) > 0", SG), sol("Interval(-oo, oo)", kind="interval"), OKU))
    c.append(("at SG f'(0)=0", ev("at(diff(f(x), x), x, 0)", SG), sol("0"), NOU))
    c.append(("at SG f'(0)=1", ev("at(diff(f(x), x), x, 0)", SG), sol("1"), OKU))
    c.append(("der-at SG 0 =1", der(SG, at="0"), sol("1"), OKU))
    c.append(("der-at SG 0 =0", der(SG, at="0"), sol("0"), NOU))
    c.append(("der-at CB3 0 =1", der("cbrt(x)**3", at="0"), sol("1"), OKU))
    c.append(("der-at CB3 0 =0", der("cbrt(x)**3", at="0"), sol("0"), NOU))
    # C1 junction must stay right
    C1 = "Piecewise((x**2, x <= 1), (2*x - 1, x > 1))"
    c.append(("at C1 f'(1)=2", ev("at(diff(f(x), x), x, 1)", C1), sol("2"), OK))
    c.append(("at C1 f'(1)=0", ev("at(diff(f(x), x), x, 1)", C1), sol("0"), NO))
    c.append(("der-at C1 =2", der(C1, at="1"), sol("2"), OK))
    c.append(("der C1 fn", der(C1), sol("Piecewise((2*x, x <= 1), (2, x > 1))", kind="expression"), OK))
    c.append(("se C1 f'=2", se("diff(f(x), x) = 2", C1), sol("Interval(1, oo)", kind="set"), OKU))
    return c


def g_k3():
    c = []
    MC5 = {"A": "-4", "B": "0", "C": "4", "D": "2", "E": "Yoktur"}
    PWA = "Piecewise((-x, x < 0), (x, x >= 0))"
    for f, p, w in (("Abs(x - 2)", 2, "0"), ("Abs(x**2 - 4)", 2, "0"), ("Abs(sin(x))", "pi", "0"), ("Max(x, 2 - x)", 1, "0"),
                    ("Abs(x)", 0, "0"), (PWA, 0, "1"), ("Piecewise((x**2, x < 1), (2*x, x >= 1))", 1, "2")):
        for d in ("Derivative(f(x), x)", "diff(f(x), (x, 1))", "diff(f(x), x, 1)", "Derivative(f(x), (x, 1))"):
            c.append((f"at {d} {f} {p} = {w}", ev(f"at({d}, x, {p})", f), sol(w), NOU))
    c.append(("MC Derivative |x-2| B", ev("at(Derivative(f(x), x), x, 2)", "Abs(x - 2)", options=MC5), sol("0", option="B"), NOU))
    c.append(("Derivative x|x| order2 0", ev("at(Derivative(x*Abs(x), x, 2), x, 0)"), sol("0"), NOU))
    c.append(("Derivative x|x| (x,2) 0", ev("at(Derivative(x*Abs(x), (x, 2)), x, 0)"), sol("0"), NOU))
    c.append(("diff x|x| (x,2) 0", ev("at(diff(x*Abs(x), (x, 2)), x, 0)"), sol("0"), NOU))
    c.append(("diff diff x|x| 0", ev("at(diff(diff(x*Abs(x), x), x), x, 0)"), sol("0"), NOU))
    c.append(("diff x x x|x| 0", ev("at(diff(x*Abs(x), x, x), x, 0)"), sol("0"), NOU))
    for f, w in (("Abs(x - 2)", "0"), ("cbrt(x - 2)", "0"), ("Abs(x - 2) + x", "1")):
        c.append((f"given x=2 Derivative {f} = {w}", ev("Derivative(f(x), x)", f, givens=["x = 2"]), sol(w), NOU))
    # right answers stay
    c.append(("Derivative |x-2| at 3 = 1", ev("at(Derivative(f(x), x), x, 3)", "Abs(x - 2)"), sol("1"), OKU))
    c.append(("Derivative x|x| (x,2) at 1 = 2", ev("at(Derivative(x*Abs(x), (x, 2)), x, 1)"), sol("2"), OKU))
    c.append(("diff x**3 (x,2) at 1 = 6", ev("at(diff(x**3, (x, 2)), x, 1)"), sol("6"), OK))
    c.append(("Derivative x**3 at 2 = 12", ev("at(Derivative(x**3, x), x, 2)"), sol("12"), OK))
    c.append(("Derivative PT at 1 = 0", ev("at(Derivative(f(x), x), x, 1)", PT), sol("0"), NOU))
    c.append(("Derivative PT at 1 = 2", ev("at(Derivative(f(x), x), x, 1)", PT), sol("2"), OKU))
    c.append(("diff PT (x,1) at 1 = 0", ev("at(diff(f(x), (x, 1)), x, 1)", PT), sol("0"), NOU))
    return c


def dom(expr):
    return ir("domain_of", {"expr": expr, "var": "x"}, (), None, "set")


def g_k4():
    c = []
    for e, txt, exp in (
            ("1/((x - 2)*(x - 3))", "R - {2} ∪ {3}", OKU - OK), ("1/((x - 2)*(x - 3))", "R - {2} U {3}", OKU - OK),
            ("1/((x - 2)*(x - 3))", r"\mathbb{R} \setminus \{2\} \cup \{3\}", OKU - OK),
            ("1/((x - 2)*(x - 3))", r"\mathbb{R} - \{2\} \cup \{3\}", OKU - OK),
            ("1/(x**2 - 9)", "R - {-3} ∪ {3}", OKU - OK), ("1/(x**2 - 9)", "ℝ∖{-3}∪{3}", OKU - OK),
            ("log(x - 2)/(x - 5)", "R - (-oo, 2] ∪ {5}", OKU - OK), ("sqrt(x - 1)/(x - 3)", "R - (-oo, 1) ∪ {3}", OKU - OK),
            ("1/(x - 2)", "R - {2} ∪ {3}", OKU - OK), ("sqrt(x - 1)", "R - (-oo, 1) ∪ {3}", OKU - OK),
            ("log(x - 2)", "R - (-oo, 2] ∪ {5}", OKU - OK),
            ("1/((x - 2)*(x - 3))", "R - ({2} ∪ {3})", OK), ("1/((x - 2)*(x - 3))", "R - {2, 3}", OK),
            ("1/((x - 2)*(x - 3))", "R - ({2} ∪ {4})", NO),
            ("1/((x - 2)*(x - 3))", "R - {2} ∪ {4}", NO),          # both readings wrong
            ("1/(x - 2)", "R - {2} ∪ {2}", OK),                    # R - {2} both ways? left: (R-{2}) U {2} = R: wrong
            ("1/(x - 2)", "R - {2}", OK), ("1/(x - 2)", "R - {3}", NO)):
        if txt == "R - {2} ∪ {2}":
            exp = OKU - OK
        c.append((f"dom {e} {txt}", dom(e), sol(txt, kind="set"), exp))
    MC = {"A": "R - {2}", "B": "R - {3}", "C": "R - {2, 3}", "D": "R - {2} ∪ {3}", "E": "R"}
    c.append(("MC D", ir("domain_of", {"expr": "1/((x - 2)*(x - 3))", "var": "x"}, (), None, "set", options=MC),
              sol("R - {2} ∪ {3}", kind="set", option="D"), OKU - OK))
    c.append(("MC C", ir("domain_of", {"expr": "1/((x - 2)*(x - 3))", "var": "x"}, (), None, "set", options=MC),
              sol("R - {2, 3}", kind="set", option="C"), OKU))
    c.append(("ineq R - [2,3] U (3,5]", si("(x - 2)*(x - 5) > 0"), sol("R - [2, 3] ∪ (3, 5]", kind="interval"), OKU - OK))
    c.append(("ineq R - [2,5]", si("(x - 2)*(x - 5) > 0"), sol("R - [2, 5]", kind="interval"), OK))
    return c


def g_k5():
    c = []
    NI1 = {"name": "n", "domain": "integer", "constraints": ["n >= 1"]}
    NP = {"name": "n", "domain": "positive_integer"}
    NI2 = {"name": "n", "domain": "integer", "constraints": ["n >= 2"]}
    NP2 = {"name": "n", "domain": "positive_integer", "constraints": ["n >= 2"]}
    for nv, tag in ((NI1, "int n>=1"), (NP, "posint")):
        for f, claim, exp in (("x**n", "n*x**n/x", NOU), ("x**n", "n*x**(n - 1) + 0/x", NOU),
                              ("x**(n + 1)", "(n + 1)*x**(n + 1)/x", NOU), ("(x - 1)**n", "n*(x - 1)**n/(x - 1)", NOU),
                              ("x**n", "n*x**(n - 1)", OKU)):
            c.append((f"{tag} ({f})' = {claim}", ir("derivative", {"f": f, "var": "x"}, (), [X, nv], "expression"),
                      sol(claim, kind="expression"), exp))
    for nv, tag in ((NI2, "int n>=2"), (NP2, "posint n>=2")):
        for f, order, claim, exp in (("x**n", 2, "n*(n - 1)*x**n/x**2", NOU), ("x**n", 3, "n*(n - 1)*(n - 2)*x**(n - 3)", NOU),
                                     ("x**n", 2, "n*(n - 1)*x**(n - 2)", OKU)):
            c.append((f"{tag} ({f})^({order}) = {claim}", ir("derivative", {"f": f, "var": "x", "order": order}, (), [X, nv],
                                                              "expression"), sol(claim, kind="expression"), exp))
    return c


def g_k7():
    c = []
    for f, F in (("(2*x + 1)**pi", "(2*x + 1)**(pi + 1)/(2*(pi + 1)) + C"), ("(x + 1)**sqrt(2)", "(x + 1)**(sqrt(2) + 1)/(sqrt(2) + 1) + C"),
                 ("(x + 2)**E", "(x + 2)**(E + 1)/(E + 1) + C"), ("(x/2)**pi", "2*(x/2)**(pi + 1)/(pi + 1) + C"),
                 ("(2*x + 1)**E", "(2*x + 1)**(E + 1)/(2*(E + 1)) + C")):
        c.append((f"anti {f}", ir("antiderivative", {"integrand": f, "var": "x"}, (), None, "expression"),
                  sol(F, kind="expression"), OKU))
        c.append((f"anti {f} wrong", ir("antiderivative", {"integrand": f, "var": "x"}, (), None, "expression"),
                  sol(F.replace("+ 1)/", "+ 2)/", 1), kind="expression"), NOU))
    return c


def g_k6():
    c = []
    for f, p, r, w in (("Abs(cos(x))**2", "pi/2", "0", "1"), ("Abs(sin(x))**2", "pi", "0", "1"), ("Abs(sin(x))**4", "pi", "0", "1"),
                       ("Abs(cos(x))**2", "pi/4", "-1", "1")):
        c.append((f"at {f} {p} = {r}", ev(f"at(diff(f(x), x), x, {p})", f), sol(r), OKU))
        c.append((f"at {f} {p} = {w}", ev(f"at(diff(f(x), x), x, {p})", f), sol(w), NOU))
    c.append(("at |sin x| pi = 0", ev("at(diff(f(x), x), x, pi)", "Abs(sin(x))"), sol("0"), NOU))
    c.append(("at |sin x|**3 pi = 0", ev("at(diff(f(x), x), x, pi)", "Abs(sin(x))**3"), sol("0"), OKU))
    return c


def g_k8():
    c = []
    EX = "Piecewise(((exp(x) - 1)/x, Ne(x, 0)), (1, Eq(x, 0)))"          # f'(0) = 1/2
    SC = "Piecewise((sin(x)/x, Ne(x, 0)), (1, Eq(x, 0)))"               # f'(0) = 0
    CS = "Piecewise(((1 - cos(x))/x, Ne(x, 0)), (0, Eq(x, 0)))"          # f'(0) = 1/2
    for f, r, w in ((EX, "1/2", "0"), (SC, "0", "1"), (CS, "1/2", "0")):
        c.append((f"at {f} 0 = {r}", ev("at(diff(f(x), x), x, 0)", f), sol(r), OKU))
        c.append((f"at {f} 0 = {w}", ev("at(diff(f(x), x), x, 0)", f), sol(w), NOU))
        c.append((f"der-at {f} 0 = {r}", der(f, at="0"), sol(r), OKU))
        c.append((f"der-at {f} 0 = {w}", der(f, at="0"), sol(w), NOU))
    SG = "Abs(x)*sign(x)"
    c.append(("at SG 0 = 1", ev("at(diff(f(x), x), x, 0)", SG), sol("1"), OKU))
    c.append(("at SG 0 = 0", ev("at(diff(f(x), x), x, 0)", SG), sol("0"), NOU))
    c.append(("at x|x| 0 = 0", ev("at(diff(f(x), x), x, 0)", "x*Abs(x)"), sol("0"), OKU))
    c.append(("at |x|^3 0 = 0", ev("at(diff(f(x), x), x, 0)", "Abs(x)**3"), sol("0"), OKU))
    c.append(("at cbrt^3 0 = 1", ev("at(diff(f(x), x), x, 0)", "cbrt(x)**3"), sol("1"), OKU))
    c.append(("at cbrt^3 0 = 0", ev("at(diff(f(x), x), x, 0)", "cbrt(x)**3"), sol("0"), NOU))
    c.append(("se (x|x|)' = 0 {0}", se("diff(x*Abs(x), x) = 0"), sol("{0}", kind="set"), OK))
    c.append(("se (x|x|)' = 0 empty", se("diff(x*Abs(x), x) = 0"), sol("EmptySet", kind="set"), NO))
    c.append(("se f (x|x|)' = 0 {0}", se("diff(f(x), x) = 0", "x*Abs(x)"), sol("{0}", kind="set"), OK))
    c.append(("si (x|x|)' > 0", si("diff(x*Abs(x), x) > 0"), sol("Union(Interval.open(-oo, 0), Interval.open(0, oo))", kind="interval"), OKU))
    c.append(("si (|x|^3)' >= 0", si("diff(Abs(x)**3, x) >= 0"), sol("Interval(0, oo)", kind="interval"), OKU))
    c.append(("at |x| 0 = 0", ev("at(diff(f(x), x), x, 0)", "Abs(x)"), sol("0"), NOU))
    c.append(("at x|x| 1 = 2", ev("at(diff(f(x), x), x, 1)", "x*Abs(x)"), sol("2"), OK))
    SX = "Piecewise((sin(x)/x + x, Ne(x, 0)), (1, Eq(x, 0)))"            # f'(0) = 1
    c.append(("at SX 0 = 0", ev("at(diff(f(x), x), x, 0)", SX), sol("0"), NOU))
    c.append(("at SX 0 = 1", ev("at(diff(f(x), x), x, 0)", SX), sol("1"), OKU))
    c.append(("der-at SX 0 = 1", der(SX, at="0"), sol("1"), OKU))
    c.append(("der-at SX 0 = 0", der(SX, at="0"), sol("0"), NOU))
    c.append(("se SX f'=0 has 0?", se("diff(f(x), x) = 0", SX), sol("{0}", kind="set"), NOU))
    return c


GROUPS = {"k1": g_k1, "k1b": g_k1b, "k2": g_k2, "k3": g_k3, "k4": g_k4, "k5": g_k5, "k6": g_k6, "k7": g_k7, "k8": g_k8}



def cases():
    return [c for g in GROUPS.values() for c in g()]


# the verdict measured on the fixed code (son-kalkulus second round) where a case allows two: a right answer CORRECT,
# a wrong one INCORRECT; a later change that loses it is reported
EXPECT = {
    'Derivative x|x| (x,2) at 1 = 2': 'CORRECT',
    'MC C': 'CORRECT',
    'MC PT A=0': 'INCORRECT',
    'MC PT C=2': 'CORRECT',
    'MC REM2 A=0': 'INCORRECT',
    'MC REM2 B=1': 'CORRECT',
    'at Abs(cos(x))**2 pi/2 = 0': 'CORRECT',
    'at Abs(cos(x))**2 pi/2 = 1': 'INCORRECT',
    'at Abs(cos(x))**2 pi/4 = -1': 'CORRECT',
    'at Abs(cos(x))**2 pi/4 = 1': 'INCORRECT',
    'at Abs(sin(x))**2 pi = 0': 'CORRECT',
    'at Abs(sin(x))**2 pi = 1': 'INCORRECT',
    'at Abs(sin(x))**4 pi = 0': 'CORRECT',
    'at Abs(sin(x))**4 pi = 1': 'INCORRECT',
    "at CUBE f''(1)=0": 'INCORRECT',
    "at CUBE f''(1)=6": 'CORRECT',
    'at Piecewise(((x**2 - 1)/(x - 1), Ne(x, 1)), (2, Eq(x, 1))) 1 wrong=0': 'INCORRECT',
    'at Piecewise(((x**2 - 4)/(x - 2), Ne(x, 2)), (4, Eq(x, 2))) 2 wrong=0': 'INCORRECT',
    'at Piecewise((2*x + 1, x < 1), (3, Eq(x, 1)), (x**2 + 2, x > 1)) 1 wrong=0': 'INCORRECT',
    'at Piecewise((sin(x)/x, Ne(x, 0)), (1, Eq(x, 0))) 0 = 0': 'CORRECT',
    'at Piecewise((sin(x)/x, Ne(x, 0)), (1, Eq(x, 0))) 0 = 1': 'INCORRECT',
    'at Piecewise((x**2 + 1, x < 1), (2, Eq(x, 1)), (2*x, x > 1)) 1 wrong=0': 'INCORRECT',
    'at Piecewise((x**2, Ne(x, 1)), (1, Eq(x, 1))) 1 wrong=0': 'INCORRECT',
    'at Piecewise((x**2, Ne(x, 3)), (9, Eq(x, 3))) 3 wrong=0': 'INCORRECT',
    'at Piecewise((x**2, x < 1), (1, Eq(x, 1)), (2*x - 1, x > 1)) 1 wrong=0': 'INCORRECT',
    'at Piecewise((x**3, Ne(x, 2)), (8, Eq(x, 2))) 2 wrong=0': 'INCORRECT',
    'at Piecewise((x**3, x < 1), (1, Eq(x, 1)), (x**3, x > 1)) 1 wrong=0': 'INCORRECT',
    'at Piecewise((x*exp(x), Ne(x, 0)), (0, Eq(x, 0))) 0 wrong=0': 'INCORRECT',
    'at SG 0 = 0': 'INCORRECT',
    'at SG 0 = 1': 'CORRECT',
    "at SG f'(0)=0": 'INCORRECT',
    "at SG f'(0)=1": 'CORRECT',
    'at cbrt^3 0 = 0': 'INCORRECT',
    'at cbrt^3 0 = 1': 'CORRECT',
    'der Abs(x)*sign(x) right 1': 'CORRECT',
    'der Abs(x)*sign(x) wrong 0': 'INCORRECT',
    'der Abs(x)*sign(x) wrong sign(x)**2': 'INCORRECT',
    'der Piecewise((2*x + 1, x < 1), (3, Eq(x, 1)), (x**2 + 2, x > 1)) right Piecewise((2, x < 1), (2*x, x >= 1))': 'CORRECT',
    'der Piecewise((2*x + 1, x < 1), (3, Eq(x, 1)), (x**2 + 2, x > 1)) right Piecewise((2, x <= 1), (2*x, x > 1))': 'CORRECT',
    'der Piecewise((2*x + 1, x < 1), (3, Eq(x, 1)), (x**2 + 2, x > 1)) wrong Piecewise((2, x < 1), (0, Eq(x, 1)), (2*x, x > 1))': 'INCORRECT',
    'der Piecewise((x**2, Ne(x, 1)), (1, Eq(x, 1))) right 2*x': 'CORRECT',
    'der Piecewise((x**2, Ne(x, 1)), (1, Eq(x, 1))) wrong Piecewise((2*x, Ne(x, 1)), (0, Eq(x, 1)))': 'INCORRECT',
    'der Piecewise((x**2, x < 1), (1, Eq(x, 1)), (2*x - 1, x > 1)) right Piecewise((2*x, x < 1), (2, x >= 1))': 'CORRECT',
    'der Piecewise((x**2, x < 1), (1, Eq(x, 1)), (2*x - 1, x > 1)) wrong Piecewise((2*x, x < 1), (0, Eq(x, 1)), (2, x > 1))': 'INCORRECT',
    'der Piecewise((x**3, x < 1), (1, Eq(x, 1)), (x**3, x > 1)) right 3*x**2': 'CORRECT',
    'der Piecewise((x**3, x < 1), (1, Eq(x, 1)), (x**3, x > 1)) wrong Piecewise((3*x**2, Ne(x, 1)), (0, Eq(x, 1)))': 'INCORRECT',
    'der cbrt((x - 1)**3) right 1': 'CORRECT',
    'der cbrt((x - 1)**3) wrong 0': 'INCORRECT',
    'der cbrt((x - 1)**3) wrong sign(x)**2': 'INCORRECT',
    'der cbrt(8*x**3) right 2': 'CORRECT',
    'der cbrt(8*x**3) wrong 0': 'INCORRECT',
    'der cbrt(8*x**3) wrong sign(x)**2': 'INCORRECT',
    'der cbrt(x)**3 right 1': 'CORRECT',
    'der cbrt(x)**3 wrong 0': 'INCORRECT',
    'der cbrt(x)**3 wrong sign(x)**2': 'INCORRECT',
    'der cbrt(x**3) + x**2 right 1 + 2*x': 'CORRECT',
    'der cbrt(x**3) + x**2 wrong 0': 'INCORRECT',
    'der cbrt(x**3) + x**2 wrong sign(x)**2': 'INCORRECT',
    'der cbrt(x**3) right 1': 'CORRECT',
    'der cbrt(x**3) wrong 0': 'INCORRECT',
    'der cbrt(x**3) wrong sign(x)**2': 'INCORRECT',
    'der-at CB3 0 =0': 'INCORRECT',
    'der-at CB3 0 =1': 'CORRECT',
    'der-at CUBE order2 claim 0': 'INCORRECT',
    'der-at CUBE order2 claim 6': 'CORRECT',
    'der-at CUBE order2 dne': 'INCORRECT',
    'der-at J2 order2 claim 2': 'INCORRECT',
    'der-at J2 order2 dne': 'CORRECT',
    'der-at PT order2 0': 'INCORRECT',
    'der-at PT order2 dne': 'CORRECT',
    'der-at Piecewise(((x**2 - 1)/(x - 1), Ne(x, 1)), (2, Eq(x, 1))) 1 right=1': 'CORRECT',
    'der-at Piecewise(((x**2 - 1)/(x - 1), Ne(x, 1)), (2, Eq(x, 1))) 1 wrong=0': 'INCORRECT',
    'der-at Piecewise(((x**2 - 4)/(x - 2), Ne(x, 2)), (4, Eq(x, 2))) 2 right=1': 'CORRECT',
    'der-at Piecewise(((x**2 - 4)/(x - 2), Ne(x, 2)), (4, Eq(x, 2))) 2 wrong=0': 'INCORRECT',
    'der-at Piecewise((2*x + 1, x < 1), (3, Eq(x, 1)), (x**2 + 2, x > 1)) 1 right=2': 'CORRECT',
    'der-at Piecewise((2*x + 1, x < 1), (3, Eq(x, 1)), (x**2 + 2, x > 1)) 1 wrong=0': 'INCORRECT',
    'der-at Piecewise((sin(x)/x, Ne(x, 0)), (1, Eq(x, 0))) 0 = 0': 'CORRECT',
    'der-at Piecewise((sin(x)/x, Ne(x, 0)), (1, Eq(x, 0))) 0 = 1': 'INCORRECT',
    'der-at Piecewise((x**2 + 1, x < 1), (2, Eq(x, 1)), (2*x, x > 1)) 1 right=2': 'CORRECT',
    'der-at Piecewise((x**2 + 1, x < 1), (2, Eq(x, 1)), (2*x, x > 1)) 1 wrong=0': 'INCORRECT',
    'der-at Piecewise((x**2, Ne(x, 1)), (1, Eq(x, 1))) 1 right=2': 'CORRECT',
    'der-at Piecewise((x**2, Ne(x, 1)), (1, Eq(x, 1))) 1 wrong=0': 'INCORRECT',
    'der-at Piecewise((x**2, Ne(x, 3)), (9, Eq(x, 3))) 3 right=6': 'CORRECT',
    'der-at Piecewise((x**2, Ne(x, 3)), (9, Eq(x, 3))) 3 wrong=0': 'INCORRECT',
    'der-at Piecewise((x**2, x < 1), (1, Eq(x, 1)), (2*x - 1, x > 1)) 1 right=2': 'CORRECT',
    'der-at Piecewise((x**2, x < 1), (1, Eq(x, 1)), (2*x - 1, x > 1)) 1 wrong=0': 'INCORRECT',
    'der-at Piecewise((x**3, Ne(x, 2)), (8, Eq(x, 2))) 2 right=12': 'CORRECT',
    'der-at Piecewise((x**3, Ne(x, 2)), (8, Eq(x, 2))) 2 wrong=0': 'INCORRECT',
    'der-at Piecewise((x**3, x < 1), (1, Eq(x, 1)), (x**3, x > 1)) 1 right=3': 'CORRECT',
    'der-at Piecewise((x**3, x < 1), (1, Eq(x, 1)), (x**3, x > 1)) 1 wrong=0': 'INCORRECT',
    'der-at Piecewise((x*exp(x), Ne(x, 0)), (0, Eq(x, 0))) 0 right=1': 'CORRECT',
    'der-at Piecewise((x*exp(x), Ne(x, 0)), (0, Eq(x, 0))) 0 wrong=0': 'INCORRECT',
    'der-at SG 0 =0': 'INCORRECT',
    'der-at SG 0 =1': 'CORRECT',
    'diff PT (x,1) at 1 = 0': 'INCORRECT',
    "f'+f REM1 = 3": 'CORRECT',
    "f'+f REM2 = 4": 'INCORRECT',
    "f'+f REM2 = 5": 'CORRECT',
    'given x=1 PT diff=0': 'INCORRECT',
    'given x=1 PT diff=2': 'CORRECT',
    "int n>=1 (x**n)' = n*x**(n - 1)": 'CORRECT',
    'int n>=2 (x**n)^(2) = n*(n - 1)*x**(n - 2)': 'CORRECT',
    "posint (x**n)' = n*x**(n - 1)": 'CORRECT',
    'posint n>=2 (x**n)^(2) = n*(n - 1)*x**(n - 2)': 'CORRECT',
    "se CB3 f'=0 {0}": 'INCORRECT',
    "se SG f'=0 {0}": 'INCORRECT',
    "se f'=0 Piecewise((2*x + 1, x < 1), (3, Eq(x, 1)), (x**2 + 2, x > 1)) wrong {1}": 'INCORRECT',
    "se f'=0 Piecewise((x**2, Ne(x, 1)), (1, Eq(x, 1))) right {0}": 'CORRECT',
    "se f'=0 Piecewise((x**2, Ne(x, 1)), (1, Eq(x, 1))) wrong {0, 1}": 'INCORRECT',
    "se f'=0 Piecewise((x**2, x < 1), (1, Eq(x, 1)), (2*x - 1, x > 1)) right {0}": 'CORRECT',
    "se f'=0 Piecewise((x**2, x < 1), (1, Eq(x, 1)), (2*x - 1, x > 1)) wrong {0, 1}": 'INCORRECT',
    "se f'=0 Piecewise((x**3, Ne(x, 2)), (8, Eq(x, 2))) right {0}": 'CORRECT',
    "se f'=0 Piecewise((x**3, Ne(x, 2)), (8, Eq(x, 2))) wrong {0, 2}": 'INCORRECT',
    "se f'=0 Piecewise((x**3, x < 1), (1, Eq(x, 1)), (x**3, x > 1)) right {0}": 'CORRECT',
    "se f'=0 Piecewise((x**3, x < 1), (1, Eq(x, 1)), (x**3, x > 1)) wrong {0, 1}": 'INCORRECT',
    "se f'=6 NE3 {3}": 'CORRECT',
    "si (x|x|)' > 0": 'CORRECT',
    "si (|x|^3)' >= 0": 'CORRECT',
    "si SG f'>0 R-{0}": 'INCORRECT',
    "si f'>0 X3 R-{0,2}": 'INCORRECT',
    'step X3 =12': 'CORRECT',
}


def expected(label, verdicts):
    return {EXPECT[label]} if label in EXPECT else set(verdicts)
