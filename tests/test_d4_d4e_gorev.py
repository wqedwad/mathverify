"""Fourth audit (1 Oct 2026), part d4e: how the task certificates read the conditions on their variable and the
written domain of their function (`denetim/2026-10-01/d4e/`).

Each case was measured wrong on 782431c (and on 158c220, src = 1df0558):

* G6: a limit read the variable's declaration only: with x > 0 as a constraint, a given or the domain of
  discourse lim_{x->0} |x|/x was certified DNE (1 refuted), the limit 0 of x at 0 under x > 1 and -oo of x at
  -oo under x > 0 were certified; the derivative and the tangent of |x| at 0 under the given x >= 0 too.
* G4, TAN-02: an extremum read neither the value a given or a constraint fixes for an end of its interval
  ([0, b], b = 3: maximum 0 certified) nor for a parameter of f (a*x, a = 3: maximum 0); a candidate whose value
  was no number was dropped and the rest called complete.
* G12: an antiderivative was compared on ℝ and its reality never checked: log(-x) certified for 1/x with x
  positive, x**2/2 refuted for |x| under the constraint x > 0, log(-x) refuted under the given x < 0.
* TAN-05: the variable of a point binder (at, Subs, Limit) carried the declaration in the written reading: with
  x positive, at(diff(sqrt(-x), x), x, -1) was undefined and the empty set certified for y + at(...) = -1/2.
* TAN-06: a derivative, tangent or antiderivative at the end of the function's written domain, on an isolated
  point of it or on an empty one was certified; |x| + sqrt(x) - sqrt(x) had its derivative 1 refuted.
* TAN-07: an integral with an infinite bound counted no point between its bounds and never had its convergence
  proved: the derivative 1/x of ∫_{-oo}^{x} dt/t (x > 0) and -1/(x + 1) of ∫_x^oo dt/(t + 1) were certified.

Found by the review of the first draft (d4e, 6 Oct 2026): the same reading in the other task certificates (a
pinned parameter in a derivative, a tangent, an antiderivative, a definite integral, a limit; a written condition
naming a parameter, x + 0*sqrt(b - x) being x), a periodic empty domain (sin(x) > 0 and -sin(x) > 0), and the
derivative of tan(x) at pi/4, which the draft's interior check on ℝ left undecided.
"""
from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_real"}
Y = {"name": "y", "domain": "real"}
T_ = {"name": "t", "domain": "real"}
A = {"name": "a", "domain": "real"}
B = {"name": "b", "domain": "real"}
XA, XB = [X, A], [X, B]
AC = {"name": "a", "domain": "real", "constraints": ["a = 3"]}
N2 = "log(x) - log(x) + log(-x) - log(-x)"           # x > 0 and -x > 0: defined nowhere
NT = "log(sin(x)) - log(sin(x)) + log(-sin(x)) - log(-sin(x))"
PT = "sqrt(sin(x)) - sqrt(sin(x)) + sqrt(-sin(x)) - sqrt(-sin(x))"   # defined at k*pi alone
S0 = "x + 0*sqrt(b - x)"
S1 = "x + 0*sqrt(b - x) + 0*sqrt(x - b)"             # defined at b alone


def xc(*cs):
    return {"name": "x", "domain": "real", "constraints": list(cs)}


def _ir(kind, params, givens=(), vars_=None, shape="scalar", dod=None, functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if dod:
        d["domain_of_discourse"] = dod
    if functions:
        d["functions"] = functions
    return d


def _v(ir, payload, kind="value", steps=()):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol).verdict


def _step(ir, payload, kind, steps):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    r = verify(ir, sol)
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    return r.verdict, layer.evidence["steps"][-1]["status"]


def _dne(ir):
    return verify(ir, {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}).verdict


def _lim(expr, to, givens=(), vars_=None, dod=None, side=None):
    p = {"expr": expr, "var": "x", "to": to}
    if side:
        p["side"] = side
    return _ir("limit", p, givens, vars_, dod=dod)


def _der(f, at=None, givens=(), vars_=None, dod=None):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    return _ir("derivative", p, givens, vars_, "scalar" if at is not None else "expression", dod)


def _tan(f, at, givens=(), vars_=None):
    return _ir("tangent_line", {"f": f, "var": "x", "at": at, "dep": "y"}, givens, list(vars_ or [X]) + [Y], "equation")


def _anti(f, givens=(), vars_=None, dod=None):
    return _ir("antiderivative", {"integrand": f, "var": "x"}, givens, vars_, "expression", dod)


def _ext(f, which, interval, givens=(), vars_=None):
    p = {"f": f, "var": "x", "which": which}
    if interval is not None:
        p["interval"] = interval
    return _ir("extremum", p, givens, vars_)


def _simp(e, givens=(), vars_=None):
    return _ir("simplify_expression", {"expr": e}, givens, vars_, "expression")


def _writings(cond, decl=None):
    out = [([], [xc(cond)], None), ([cond], [X], None), ([], [X], cond)]
    if decl:
        out.append(([], [{"name": "x", "domain": decl}], None))
    return out


# --- G6: the limit on the variable's region ------------------------------------------------------------------
def test_limit_reads_the_condition_however_it_is_written():
    for g, v, d in _writings("x > 0", "positive_real"):
        q = _lim("Abs(x)/x", "0", g, v, d)
        assert _v(q, "1") == "CORRECT"
        assert _dne(q) == "INCORRECT"
    for g, v, d in _writings("x < 0"):
        q = _lim("1/x", "0", g, v, d)
        assert _v(q, "-oo") == "CORRECT"
        assert _dne(q) == "INCORRECT"
    q = _lim("floor(x)", "1", ["x > 1"])
    assert _v(q, "1") == "CORRECT" and _dne(q) == "INCORRECT"


def test_limit_point_not_approached_inside_the_region():
    assert _v(_lim("x", "0", ["x > 1"]), "0") == "UNKNOWN"
    assert _v(_lim("x", "-oo", [], [xc("x > 0")]), "-oo") == "UNKNOWN"
    assert _v(_lim("x", "oo", [], [X], "x < 0"), "oo") == "UNKNOWN"
    assert _v(_lim("Abs(x)/x", "0", ["x > 0"], side="-"), "-1") == "UNKNOWN"
    assert _v(_lim("x", "0", ["x**2*(x - 1) >= 0"]), "0") == "UNKNOWN"        # 0 is an isolated point
    assert _v(_lim("x", "3/2", ["x < 1 or x > 2"]), "3/2") == "UNKNOWN"
    # an end of a region of two pieces is approached from inside it
    q = _lim("Abs(x - 2)/(x - 2)", "2", ["x < 1 or x > 2"])
    assert _v(q, "1") == "CORRECT" and _dne(q) == "INCORRECT"
    q = _lim("Abs(x - 1)/(x - 1)", "1", ["x**2 > 1"])
    assert _v(q, "1") == "CORRECT" and _dne(q) == "INCORRECT"


def test_limit_condition_naming_a_free_parameter():
    assert _v(_lim("Abs(x)/x", "0", ["x > b"], XB), "1") == "UNKNOWN"
    assert _dne(_lim("Abs(x)/x", "0", ["x > b"], XB)) == "UNKNOWN"
    assert _v(_lim("x", "0", [], XB, "x > b"), "0") == "UNKNOWN"
    q = _lim("Abs(x)/x", "0", ["x > b", "b = 0"], XB)
    assert _v(q, "1") == "CORRECT"


def test_controls_of_the_limit():
    assert _v(_lim("sin(x)/x", "0"), "1") == "CORRECT"
    assert _dne(_lim("Abs(x)/x", "0")) == "CORRECT"
    assert _v(_lim("sqrt(x)", "0"), "0") == "UNKNOWN"                      # one side: a convention
    assert _v(_lim("(x**2 - 1)/(x - 1)", "1", ["x > 0"]), "2") == "CORRECT"
    assert _v(_lim("sin(x)/x", "0", ["x != 0"]), "1") == "CORRECT"


# --- G6: the derivative and the tangent are two-sided ------------------------------------------------------------
def test_derivative_and_tangent_at_an_end_of_the_region():
    for g, v, d in _writings("x >= 0", "nonneg_real"):
        assert _dne(_der("Abs(x)", "0", g, v, d)) == "UNKNOWN"
        assert _v(_der("Abs(x)", "0", g, v, d), "1") == "UNKNOWN"
    assert _v(_tan("Abs(x)", "0", ["x >= 0"]), "y = x", "equation") == "UNKNOWN"
    assert _v(_der("x**2", "3", ["x < 2"]), "6") == "UNKNOWN"
    assert _v(_der("x**2", "0", ["x > 0"]), "0") == "UNKNOWN"
    assert _v(_der("x**2", "1", ["x < 2"]), "2") == "CORRECT"
    assert _v(_der("x**2", "1", ["x < 2"]), "3") == "INCORRECT"
    assert _v(_tan("x**2", "1", ["x < 2"]), "y = 2*x - 1", "equation") == "CORRECT"
    assert _v(_der("Abs(x)", "0", ["x >= b"], XB), "1") == "UNKNOWN"
    assert _v(_der("Abs(x)", "1", [], [xc("x != 0")]), "1") == "CORRECT"


def test_derivative_expression_on_the_region():
    assert _v(_der("Abs(x)", None, ["x > 0"]), "1", "expression") == "CORRECT"
    assert _v(_der("Abs(x)", None, ["x > 0"]), "-1", "expression") == "INCORRECT"
    # no interior: the derivative function has nowhere to live
    assert _v(_der("x**2", None, ["x = 2"]), "4", "expression") == "UNKNOWN"
    assert _v(_der("x**2", None, ["x = 2"]), "2*x", "expression") == "UNKNOWN"


# --- G4, TAN-02: the extremum's pinned interval and parameters ---------------------------------------------------
def test_extremum_interval_end_fixed_by_a_given_or_a_constraint():
    q = _ext("x", "max", "[0, b]", ["b = 3"], XB)
    assert _v(q, "0") == "INCORRECT" and _v(q, "3") == "CORRECT"
    q = _ext("x", "max", "[0, b]", [], [X, {"name": "b", "domain": "real", "constraints": ["b = 3"]}])
    assert _v(q, "0") == "INCORRECT" and _v(q, "3") == "CORRECT"
    q = _ext("x", "argmax", "Interval(0, b)", ["b = 3"], XB)
    assert _v(q, "0") == "INCORRECT" and _v(q, "3") == "CORRECT"
    assert _v(_ext("x", "max", "[b, 1]", ["b = 5"], XB), "1") == "UNKNOWN"           # empty
    assert _v(_ext("x", "max", "[0, b]", [], [X, {"name": "b", "domain": "positive_real"}]), "0") == "UNKNOWN"
    assert _v(_ext("x", "max", "[0, b]", ["b > 5"], XB), "0") == "UNKNOWN"
    q = _ext("cos(x)", "min", "[0, b]", ["b = 3"], XB)
    assert _v(q, "1") == "INCORRECT" and _v(q, "cos(3)") == "CORRECT"


def test_extremum_parameter_of_f_fixed_by_a_given_or_a_constraint():
    q = _ext("a*x", "max", "[0, 1]", ["a = 3"], XA)
    assert _v(q, "0") == "INCORRECT" and _v(q, "3") == "CORRECT"
    q = _ext("a*x", "argmax", "[0, 1]", ["a = 3"], XA)
    assert _v(q, "0") == "INCORRECT" and _v(q, "1") == "CORRECT"
    q = _ext("a*x", "max", "[0, 1]", [], [X, AC])
    assert _v(q, "0") == "INCORRECT" and _v(q, "3") == "CORRECT"
    assert _v(_ext("a*x", "min", "[0, 1]", ["a = -3"], XA), "-3") == "CORRECT"
    assert _v(_ext("a*x", "max", "[0, 1]", [], XA), "0") == "UNKNOWN"
    q = _ext("x*Sum(k, (k, 1, n))", "max", "[0, 1]", ["n = 3"], [X, {"name": "k", "domain": "integer"},
                                                                  {"name": "n", "domain": "integer"}])
    assert _v(q, "0") == "INCORRECT" and _v(q, "6") == "CORRECT"
    q = _ext("x**3 - 3*a*x", "local_max", "Reals", ["a = 1"], XA)
    assert _v(q, "2") == "CORRECT" and _v(q, "0") == "INCORRECT"
    assert _v(_ext("x**3 - 3*a*x", "local_max", "Reals", [], XA), "2") == "UNKNOWN"


def test_extremum_candidate_value_that_is_no_number_is_never_dropped():
    assert _v(_ext("x + x*pi**I", "max", "[0, 1]"), "0") == "UNKNOWN"


def test_extremum_closed_form_a_pin_makes_is_confirmed():
    # ∫_{-1}^{1} |cos t| dt = 2 sin 1; SymPy's own value is 0
    q = _ext("x*Integral(Abs(cos(t)), (t, -a, a))", "max", "[0, 1]", ["a = 1"], [X, A, T_])
    assert _v(q, "0") == "INCORRECT"
    assert _v(q, "2*sin(1)") == "CORRECT"


# --- G12: the antiderivative on the region, real ---------------------------------------------------------------
def test_antiderivative_on_the_region_however_it_is_written():
    for g, v, d in _writings("x > 0", "positive_real"):
        assert _v(_anti("1/x", g, v, d), "log(-x)", "expression") != "CORRECT"
        assert _v(_anti("1/x", g, v, d), "log(x)", "expression") == "CORRECT"
        assert _v(_anti("Abs(x)", g, v, d), "x**2/2", "expression") == "CORRECT"
        assert _v(_anti("Abs(x)", g, v, d), "-x**2/2", "expression") == "INCORRECT"
    for g, v, d in _writings("x < 0"):
        assert _v(_anti("1/x", g, v, d), "log(-x)", "expression") == "CORRECT"
        assert _v(_anti("1/x", g, v, d), "log(x)", "expression") != "CORRECT"
    assert _v(_anti("1/x", ["x > b"], XB), "log(x)", "expression") == "UNKNOWN"


def test_antiderivative_must_be_real():
    assert _v(_anti("1/x", [], [XP]), "log(x) + I*pi", "expression") == "INCORRECT"
    assert _v(_anti("1/x", [], [XP]), "log(-x) - log(-1)", "expression") != "CORRECT"
    assert _v(_anti("2*x", [], [XP]), "x**2 + 0*log(-x)", "expression") == "INCORRECT"
    assert _v(_anti("1"), "x + I", "expression") == "INCORRECT"
    assert _v(_anti("cos(x)"), "sin(x) + I", "expression") == "INCORRECT"
    # a region SymPy leaves unsolved (cos(x) != 0 on x > 100) is sampled at its own points
    assert _v(_anti("tan(x)**2 + 1", ["x > 100"]), "tan(x) + I", "expression") == "INCORRECT"
    assert _v(_anti("tan(x)**2 + 1", ["x > 100"]), "tan(x)", "expression") == "CORRECT"
    # no sample point where the integrand is defined: reality is not decided
    W = "tan(x)**2 + 1 + 0/((x - 101)*(7*x - 701))"
    assert _v(_anti(W, ["x > 100"]), "tan(x) + I", "expression") == "UNKNOWN"


def test_antiderivative_one_constant_over_the_pieces():
    assert _v(_anti("1/x", ["x < -1 or x > 1"]), "log(Abs(x)) + sign(x)", "expression") == "UNKNOWN"
    assert _v(_anti("1/x", ["x < -1 or x > 1"]), "log(Abs(x))", "expression") != "INCORRECT"
    assert _v(_anti("1/x"), "log(Abs(x))", "expression") == "CORRECT"
    assert _v(_anti("1/x", ["x != 0"]), "log(Abs(x))", "expression") == "CORRECT"
    assert _v(_anti("1/x"), "log(x)", "expression") == "INCORRECT"
    # atan(1/x) + atan(x) is -pi/2 on x < 0 and pi/2 on x > 0: two constants, a convention
    for F in ("log(Abs(x)) + atan(1/x) + atan(x)", "log(x**2)/2 + 2*atan(1/x) + 2*atan(x)"):
        assert _v(_anti("1/x"), F, "expression") == "UNKNOWN"
    assert _v(_anti("1/x"), "log(Abs(x)) + 5", "expression") == "CORRECT"


def test_comparison_on_a_restricted_region_keeps_its_proofs():
    # the proof at a kink reads its whole cell, (0, oo) for |x|; (1, oo) is not one
    assert _v(_anti("1/x", ["x > 1"]), "log(Abs(x))", "expression") == "CORRECT"
    assert _v(_anti("1/x", ["x > 1"]), "-log(Abs(x))", "expression") == "INCORRECT"
    assert _v(_der("log(Abs(x))", None, ["x > 1"]), "1/x", "expression") == "CORRECT"
    assert _v(_der("Abs(x)", None, ["x > 1"]), "-1", "expression") == "INCORRECT"


# --- TAN-05: the variable of a point binder is local ------------------------------------------------------------
def test_point_binder_variable_carries_no_declaration():
    for decl in ("positive_real", "nonneg_real"):
        V = [{"name": "x", "domain": decl}, Y]
        q = _ir("solve_equation", {"var": "y", "equation": "y + at(diff(sqrt(-x), x), x, -1) = -1/2"}, [], V, "set")
        assert _v(q, "{0}", "set") == "CORRECT"
        assert _v(q, "EmptySet", "set") == "INCORRECT"
        q = _ir("count_roots", {"var": "y", "expr": "y**2 - 1 + at(diff(sqrt(-x), x), x, -1) + 1/2"}, [], V, "count")
        assert _v(q, "2", "count") == "CORRECT"
    q = _ir("evaluate", {"expr": "Limit(sqrt(x)**2/x, x, -oo)"}, [], [XP])
    assert _v(q, "1") == "UNKNOWN"
    q = _ir("evaluate", {"expr": "x + 1"}, ["x = 1"], [XP])
    assert _step(q, "2", "value", [("compute", "Limit(sqrt(x)**2/x, x, -oo) = 1")])[1] != "verified"


# --- TAN-06: the function's written domain ----------------------------------------------------------------------
def test_derivative_at_an_end_or_isolated_point_of_the_written_domain():
    for f, at in (("sqrt(x)**2", "0"), ("x + acos(x) - acos(x)", "1"), ("x + sqrt(1 - x**2) - sqrt(1 - x**2)", "-1"),
                  ("x + sqrt(x) - sqrt(x) + sqrt(-x) - sqrt(-x)", "0"), ("x*sqrt(x)", "0")):
        assert _v(_der(f, at), "1") == "UNKNOWN"
    assert _v(_tan("sqrt(x)**2", "0"), "y = x", "equation") == "UNKNOWN"
    assert _v(_der("sqrt(x)**2", "1"), "1") == "CORRECT"
    assert _v(_der("x + acos(x) - acos(x)", "1/2"), "1") == "CORRECT"


def test_function_defined_nowhere_or_without_interior():
    assert _v(_der("x + " + N2), "1", "expression") == "UNKNOWN"
    assert _v(_anti("1 + " + N2), "x", "expression") == "UNKNOWN"
    assert _v(_simp("x + " + N2), "x", "expression") == "UNKNOWN"
    assert _v(_simp(N2), "0", "expression") == "UNKNOWN"
    I0 = "x + sqrt(x) - sqrt(x) + sqrt(-x) - sqrt(-x)"
    assert _v(_der(I0), "1", "expression") == "UNKNOWN"
    assert _v(_der(I0), "0", "expression") == "UNKNOWN"
    assert _v(_anti("1" + I0[1:]), "x", "expression") == "UNKNOWN"
    # compared on the domain's interior
    assert _v(_der("Abs(x) + sqrt(x) - sqrt(x)"), "1", "expression") == "CORRECT"
    assert _v(_der("Abs(x) + sqrt(x) - sqrt(x)"), "-1", "expression") == "INCORRECT"


def test_limit_of_a_function_defined_nowhere():
    assert _v(_lim("x + " + N2, "1"), "1") == "UNKNOWN"
    assert _dne(_lim("x + " + N2, "1")) == "UNKNOWN"


def test_periodic_written_domain():
    assert _v(_der("x + " + NT), "1", "expression") == "UNKNOWN"
    assert _v(_anti("1 + " + NT), "x", "expression") == "UNKNOWN"
    assert _v(_simp("x + " + NT), "x", "expression") == "UNKNOWN"
    assert _v(_lim("x + " + NT, "1"), "1") == "UNKNOWN"
    assert _v(_der("x + " + PT), "1", "expression") == "UNKNOWN"
    assert _v(_der("x + " + PT, "0"), "1") == "UNKNOWN"
    assert _v(_anti("1 + " + PT), "x", "expression") == "UNKNOWN"
    # sin(x) > 0 and sin(x/2) < 0: empty on [0, 2pi), not on [0, 4pi) (on (2pi, 3pi))
    LC = "x + log(sin(x)) - log(sin(x)) + log(-sin(x/2)) - log(-sin(x/2))"
    assert _v(_der(LC), "1", "expression") == "CORRECT"
    assert _v(_simp(LC), "x", "expression") == "CORRECT"
    AS = "Abs(sin(x)) + sqrt(sin(x)) - sqrt(sin(x))"
    assert _v(_der(AS), "cos(x)", "expression") != "INCORRECT"
    assert _v(_der(AS), "-cos(x)", "expression") == "INCORRECT"
    assert _v(_der(AS, "0"), "1") == "UNKNOWN"
    assert _v(_der(AS, "pi/2"), "0") == "CORRECT"


def test_trigonometric_derivatives_stay_decided():
    for f, at, c in (("tan(x)", "pi/4", "2"), ("sec(x)", "pi/4", "sqrt(2)"), ("1/(1 + cos(x))", "pi/2", "1")):
        assert _v(_der(f, at), c) == "CORRECT"
        assert _v(_der(f, at), "0") == "INCORRECT"
    assert _v(_tan("tan(x)", "pi/4"), "y = 2*x - pi/2 + 1", "equation") == "CORRECT"
    assert _v(_der("tan(x)"), "1/cos(x)**2", "expression") == "CORRECT"
    assert _v(_der("tan(x)"), "1/sin(x)**2", "expression") == "INCORRECT"
    assert _v(_anti("1/cos(x)**2"), "tan(x)", "expression") == "CORRECT"


# --- TAN-07: an infinite bound ----------------------------------------------------------------------------------
def test_infinite_bound_reaches_its_end_and_must_converge():
    V = [XP, T_]
    for f, c in (("Integral(1/t, (t, -oo, x))", "1/x"), ("Integral(exp(t)/t, (t, -oo, x))", "exp(x)/x"),
                 ("Integral(1/(t + 1), (t, x, oo))", "-1/(x + 1)"), ("Integral(1, (t, x, oo))", "-1"),
                 ("Integral(t, (t, -oo, x))", "x")):
        assert _v(_ir("derivative", {"f": f, "var": "x"}, [], V, "expression"), c, "expression") == "UNKNOWN"
    q = _ir("derivative", {"f": "Integral(1/t, (t, -oo, x), (s, 0, 1))", "var": "x"}, [],
            V + [{"name": "s", "domain": "real"}], "expression")
    assert _v(q, "1/x", "expression") == "UNKNOWN"
    for f, c in (("Integral(exp(-t), (t, x, oo))", "-exp(-x)"), ("Integral(exp(t), (t, -oo, x))", "exp(x)"),
                 ("Integral(1/t**2, (t, x, oo))", "-1/x**2"), ("Integral(1/(t**2 + 1), (t, -oo, x))", "1/(x**2 + 1)")):
        assert _v(_ir("derivative", {"f": f, "var": "x"}, [], V, "expression"), c, "expression") == "CORRECT"
    q = _ir("evaluate", {"expr": "x + 1"}, ["x = 1"], V)
    assert _step(q, "2", "value", [("eq", "diff(Integral(1/t, (t, -oo, x)), x) = 1/x")])[1] != "verified"


# --- review of d4e: the same reading in every task certificate --------------------------------------------------
def test_parameter_fixed_by_a_given_or_a_constraint_in_calculus():
    for g, v in ((["a = 3"], XA), ([], [X, AC])):
        assert _v(_der("a*x**2", None, g, v), "6*x", "expression") == "CORRECT"
        assert _v(_der("a*x**2", None, g, v), "2*a*x", "expression") == "CORRECT"
        assert _v(_der("a*x**2", None, g, v), "2*x", "expression") == "INCORRECT"
        assert _v(_der("a*x**2", "1", g, v), "6") == "CORRECT"
        assert _v(_der("x**3", "a", g, v), "27") == "CORRECT"
        assert _v(_tan("a*x**2", "1", g, v), "y = 6*x - 3", "equation") == "CORRECT"
        assert _v(_anti("a*x", g, v), "3*x**2/2", "expression") == "CORRECT"
        assert _v(_anti("a*x", g, v), "x**2/2", "expression") == "INCORRECT"
        assert _v(_lim("a*x", "1", g, v), "3") == "CORRECT"
        assert _v(_lim("a*x", "1", g, v), "a") == "CORRECT"
        q = _ir("definite_integral", {"integrand": "a*x", "var": "x", "a": "0", "b": "1"}, g, v)
        assert _v(q, "3/2") == "CORRECT" and _v(q, "1/2") == "INCORRECT"


def test_written_condition_naming_a_parameter():
    assert _v(_ext(S0, "max", "[0, 1]", ["b = 1/2"], XB), "1") != "CORRECT"
    assert _v(_ext(S0, "max", "[0, 1]", [], XB), "1") == "UNKNOWN"
    assert _v(_ext(S0, "max", "[0, 1]", ["b = 2"], XB), "1") == "CORRECT"
    q = _ir("definite_integral", {"integrand": S0, "var": "x", "a": "0", "b": "1"}, ["b = 1/2"], XB)
    assert _v(q, "1/2") != "CORRECT"
    q = _ir("definite_integral", {"integrand": S0, "var": "x", "a": "0", "b": "1"}, [], XB)
    assert _v(q, "1/2") == "UNKNOWN"
    assert _v(_lim(S0, "0", [], XB), "0") == "UNKNOWN"
    assert _v(_lim(S0, "0", ["b = -1"], XB), "0") != "CORRECT"
    assert _v(_der(S1, None, [], XB), "1", "expression") == "UNKNOWN"
    assert _v(_der(S1, None, ["b = 2"], XB), "1", "expression") == "UNKNOWN"
    assert _v(_der(S1, "2", ["b = 2"], XB), "1") == "UNKNOWN"
    assert _v(_anti("1 + 0*sqrt(b - x) + 0*sqrt(x - b)", [], XB), "x", "expression") == "UNKNOWN"
    assert _v(_der(S0, "0", [], XB), "1") == "UNKNOWN"
    assert _v(_der(S0, "0", ["b = 1"], XB), "1") == "CORRECT"
    assert _v(_tan(S0, "0", [], XB), "y = x", "equation") == "UNKNOWN"


def test_tangent_dependent_variable_is_never_pinned():
    assert _v(_tan("x**2", "1", ["y = 1"]), "y = 2*x - 1", "equation") == "CORRECT"
