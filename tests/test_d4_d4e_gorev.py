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
    # a trigonometric condition left unsolved: the side is not decided (never two-sided)
    assert _dne(_lim("Abs(x)/x", "0", [], [xc("sin(x) > 0")])) != "CORRECT"
    # floor(1/x) > 0 is x in (0, 1]: a region no exact cut decides near 0 is approached from no side (two-sided,
    # DNE would be certified)
    assert _dne(_lim("Abs(x)/x", "0", [], [xc("floor(1/x) > 0")])) != "CORRECT"


def test_limit_of_a_sequence_reads_its_region():
    N = {"name": "n", "domain": "positive_integer"}
    q = _ir("limit", {"expr": "1/n", "var": "n", "to": "oo"}, [], [N])
    assert _v(q, "0") == "CORRECT"
    q = _ir("limit", {"expr": "1/n", "var": "n", "to": "oo"}, [], [{"name": "n", "domain": "integer",
                                                                   "constraints": ["n < 10"]}])
    assert _v(q, "0") == "UNKNOWN"


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
    assert _v(_der("Abs(x)", None, ["x > b"], XB), "1", "expression") == "UNKNOWN"
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
    assert _v(q, "0") == "INCORRECT" and _v(q, "3") == "CORRECT" and _v(q, "a") == "CORRECT"
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


def test_closed_form_a_pin_makes_is_read_by_numbers():
    # ∫_{-1}^{1} |cos t| dt = 2 sin 1; SymPy's own value is 0
    q = _ext("x*Integral(Abs(cos(t)), (t, -a, a))", "max", "[0, 1]", ["a = 1"], [X, A, T_])
    assert _v(q, "0") == "INCORRECT"
    assert _v(q, "2*sin(1)") == "CORRECT"
    assert _v(_lim("x*Integral(Abs(cos(t)), (t, -a, a))", "1", ["a = 1"], [X, A, T_]), "0") == "INCORRECT"
    q = _der("x*Integral(Abs(cos(t)), (t, -a, a))", None, ["a = 1"], [X, A, T_])
    assert _v(q, "0", "expression") == "INCORRECT"


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
    # a parameter (or the constant C) left in the claim is a real constant
    assert _v(_anti("a", [], XA), "a*x", "expression") == "CORRECT"
    assert _v(_anti("1", [], XA), "x + I*(a**2 + 1)", "expression") == "INCORRECT"
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
    assert _v(_anti("1/x"), "log(x**2)/2", "expression") == "CORRECT"


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
    # compared off sin(x) = 0, where the claim has no value and SymPy's derivative 0
    assert _v(_der("sqrt(sin(x))**3"), "3*cos(x)*sin(x)/(2*sqrt(sin(x)))", "expression") != "INCORRECT"
    assert _v(_der("sqrt(sin(x))**2*sign(sin(x))"), "cos(x)", "expression") != "INCORRECT"   # sign(0) = 0 at the ends


def test_trigonometric_derivatives_stay_decided():
    for f, at, c in (("tan(x)", "pi/4", "2"), ("sec(x)", "pi/4", "sqrt(2)"), ("1/(1 + cos(x))", "pi/2", "1")):
        assert _v(_der(f, at), c) == "CORRECT"
        assert _v(_der(f, at), "0") == "INCORRECT"
    assert _v(_tan("tan(x)", "pi/4"), "y = 2*x - pi/2 + 1", "equation") == "CORRECT"
    assert _v(_der("tan(x)"), "1/cos(x)**2", "expression") == "CORRECT"
    assert _v(_der("tan(x)"), "1/sin(x)**2", "expression") == "INCORRECT"
    assert _v(_anti("1/cos(x)**2"), "tan(x)", "expression") == "CORRECT"
    # a condition that is tight at the point but holds all around it: solved on the window, not strict there
    assert _v(_der("x + 0*sqrt(1 - cos(x))", "0"), "1") == "CORRECT"
    assert _v(_der("x + 0*sqrt(cos(x)**2)", "pi/2"), "1") == "CORRECT"
    assert _v(_der("x + 0*sqrt(cos(x) - cos(x)**3)", "0"), "1") == "CORRECT"     # cos(x)*sin(x)**2 >= 0 near 0


# --- TAN-07: an infinite bound ----------------------------------------------------------------------------------
def test_infinite_bound_reaches_its_end_and_must_converge():
    V = [XP, T_]
    for f, c in (("Integral(1/t, (t, -oo, x))", "1/x"), ("Integral(exp(t)/t, (t, -oo, x))", "exp(x)/x"),
                 ("Integral(1/(t + 1), (t, x, oo))", "-1/(x + 1)"), ("Integral(1, (t, x, oo))", "-1"),
                 ("Integral(t, (t, -oo, x))", "x")):
        assert _v(_ir("derivative", {"f": f, "var": "x"}, [], V, "expression"), c, "expression") == "UNKNOWN"
    for f, c in (("Integral(1/t, (t, -oo, x), (s, 0, 1))", "1/x"), ("Integral(1, (t, -oo, x), (s, 0, 1))", "1")):
        q = _ir("derivative", {"f": f, "var": "x"}, [], V + [{"name": "s", "domain": "real"}], "expression")
        assert _v(q, c, "expression") == "UNKNOWN"
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
        assert _v(_der("a*x**2", "1", g, v), "2*a") == "CORRECT"
        assert _v(_der("x**3", "a", g, v), "27") == "CORRECT"
        assert _v(_tan("a*x**2", "1", g, v), "y = 6*x - 3", "equation") == "CORRECT"
        assert _v(_tan("a*x**2", "1", g, v), "y = 2*a*x - a", "equation") == "CORRECT"
        assert _v(_anti("a*x", g, v), "3*x**2/2", "expression") == "CORRECT"
        assert _v(_anti("a*x", g, v), "x**2/2", "expression") == "INCORRECT"
        assert _v(_anti("a*x", g, v), "a*x**2/2", "expression") == "CORRECT"
        assert _v(_lim("a*x", "1", g, v), "3") == "CORRECT"
        assert _v(_lim("a*x", "1", g, v), "a") == "CORRECT"
        q = _ir("definite_integral", {"integrand": "a*x", "var": "x", "a": "0", "b": "1"}, g, v)
        assert _v(q, "3/2") == "CORRECT" and _v(q, "1/2") == "INCORRECT"
        q = _ir("definite_integral", {"integrand": "x", "var": "x", "a": "0", "b": "a"}, g, v)
        assert _v(q, "9/2") == "CORRECT" and _v(q, "a**2/2") == "CORRECT"


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
    # bounded from one side only, the side the region leaves open: a half-line for every value of a
    assert _v(_der("sqrt(x - a)", None, [], XA), "1/(2*sqrt(x - a))", "expression") == "CORRECT"
    assert _v(_der("sqrt(a - x)", None, [], XA), "-1/(2*sqrt(a - x))", "expression") == "CORRECT"
    assert _v(_der("sqrt(x - a)", None, [], XA), "1/sqrt(x - a)", "expression") == "INCORRECT"
    assert _v(_der("x + 0*sqrt(x - a) + 0*sqrt(5 - x)", None, [], XA), "1", "expression") == "UNKNOWN"
    assert _v(_der(S1, None, ["b = 2"], XB), "1", "expression") == "UNKNOWN"
    assert _v(_der(S1, "2", ["b = 2"], XB), "1") == "UNKNOWN"
    assert _v(_anti("1 + 0*sqrt(b - x) + 0*sqrt(x - b)", [], XB), "x", "expression") == "UNKNOWN"
    assert _v(_der(S0, "0", [], XB), "1") == "UNKNOWN"
    assert _v(_der(S0, "0", ["b = 1"], XB), "1") == "CORRECT"
    assert _v(_tan(S0, "0", [], XB), "y = x", "equation") == "UNKNOWN"


def test_tangent_dependent_variable_is_never_pinned():
    assert _v(_tan("x**2", "1", ["y = 1"]), "y = 2*x - 1", "equation") == "CORRECT"


# --- round 2 (attack on d4e, 6 Oct 2026): false accepts YO-1..YO-6 ---------------------------------------------
K = {"name": "k", "domain": "integer"}
AC2 = {"name": "a", "domain": "real", "constraints": ["a = 2"]}


def _ss(term, lo, hi, givens=(), vars_=None):
    return _ir("series_sum", {"term": term, "var": "k", "lo": lo, "hi": hi}, givens, vars_ or [K, A])


def _cf(rec, initial, givens=()):
    return _ir("closed_form", {"recurrence": rec, "initial": initial, "var": "n", "name": "a"}, givens,
               [{"name": "n", "domain": "positive_integer"}, {"name": "c", "domain": "real"}], "expression")


def test_series_and_closed_form_read_the_pinned_value():
    for g, v in ((["a = 2"], [K, A]), ([], [K, AC2])):
        assert _v(_ss("(k - a)/(k - a)", 1, 3, g, v), "3") == "UNKNOWN"
        assert _v(_ss("1/(k - a)", 1, 3, g, v), "1/(1 - a) + 1/(2 - a) + 1/(3 - a)") == "UNKNOWN"
        assert _v(_ss("a*k", 1, 3, g, v), "12") == "CORRECT"
        assert _v(_ss("a*k", 1, 3, g, v), "6*a") == "CORRECT"
        assert _v(_ss("a*k", 1, 3, g, v), "6") == "INCORRECT"
        assert _v(_ss("a**k", 0, 3, g, v), "15") == "CORRECT"
    assert _v(_ss("a**k", 0, 3, ["a = 1"]), "(a**4 - 1)/(a - 1)") == "UNKNOWN"
    assert _v(_ss("a**k", 0, 3, ["a = 1"]), "4") == "CORRECT"
    assert _v(_ss("a**k", 0, 3, ["a = 0"]), "1") == "UNKNOWN"
    assert _v(_ss("1/(k - a)", 1, 3, ["a = 5"]), "-13/12") == "CORRECT"
    assert _v(_ss("0**k", 0, 3, [], [K]), "1") == "UNKNOWN"
    assert _v(_cf("a(n) = c*a(n - 1)", {"1": "1"}, ["c = 0"]), "c**(n - 1)", "expression") == "UNKNOWN"
    assert _v(_cf("a(n) = c*a(n - 1)", {"1": "1"}, ["c = 2"]), "2**(n - 1)", "expression") == "CORRECT"
    assert _v(_cf("a(n) = c*a(n - 1)", {"1": "1"}, ["c = 2"]), "c**(n - 1)", "expression") == "CORRECT"
    assert _v(_cf("a(n) = c*a(n - 1)", {"1": "1"}, ["c = 2"]), "3**(n - 1)", "expression") == "INCORRECT"
    # the claim itself is read at the pinned value: 0**0 and 0/0 with a = 0
    assert _v(_ss("k", 1, 3, ["a = 0"]), "6*a**a") == "UNKNOWN"
    assert _v(_ss("k", 1, 3, ["a = 0"]), "6 + 0/a") == "UNKNOWN"


def test_integral_with_numbers_for_bounds_must_converge():
    i, V = "Integral(1/t, (t, 1, oo))", [T_]
    for e, c in ((f"{i} - {i}", "0"), (f"0*{i} + 1", "1"), (f"{i}/{i}", "1"), (f"{i}**0", "1"),
                 ("0*Integral(1/(t - 1/2), (t, 0, 1)) + 1", "1"), ("0*Integral(1/t**2, (t, -1, 1)) + 1", "1")):
        assert _v(_ir("evaluate", {"expr": e}, [], V), c) == "UNKNOWN"
    q = _ir("derivative", {"f": "x + 0*Integral(1/(t - 1/2), (t, 0, 1))", "var": "x"}, [], [X, T_], "expression")
    assert _v(q, "1", "expression") == "UNKNOWN"
    for e, c in (("0*Integral(1/t**2, (t, 1, oo)) + 1", "1"), ("Integral(exp(-t), (t, 0, oo))", "1"),
                 ("Integral(1/sqrt(t), (t, 0, 1))", "2"), ("Integral(log(t), (t, 0, 1))", "-1"),
                 ("Integral(exp(-t**2), (t, -oo, oo))", "sqrt(pi)"), ("Integral(1/(1 + t**2), (t, -oo, oo))", "pi")):
        assert _v(_ir("evaluate", {"expr": e}, [], V), c) == "CORRECT"
    # Dirichlet's test: sin(t)/t converges at oo (not absolutely), sin(t)**2/t does not
    sol = {"claimed_answer": {"kind": "value", "payload": "pi/2"}, "steps": []}
    r = verify(_ir("evaluate", {"expr": "Integral(sin(t)/t, (t, 0, oo))"}, [], V), sol)
    assert "problem_definedness_undecided" not in {f for la in r.layers for f in (la.flags or [])}
    assert _v(_ir("evaluate", {"expr": "0*Integral(sin(t)**2/t, (t, 1, oo)) + 1"}, [], V), "1") == "UNKNOWN"


def test_subs_body_is_read_at_its_point():
    for g, c in ((["x = 1"], "Subs(sqrt(x - 2), x, 1)**2 = -1"), (["x = 1"], "Subs(1/(x - 1), x, 1)*0 = 0"),
                 (["x = 1"], "at(diff(log(x - 2) - log(x - 2) + x, x), x, 1) = 1"),
                 (["x = -5"], "Subs(sqrt(x)**2, x, -1) = -1"), (["x = -5"], "at(diff(sqrt(x)**2, x), x, -1) = 1"),
                 (["x = 3"], "at(diff(sqrt(x)**2, x), x, 0) = 1")):
        q = _ir("evaluate", {"expr": "x + 1"}, g, [X])
        assert _step(q, str(int(g[0].split("= ")[1]) + 1), "value", [("compute", c)])[1] != "verified"
    q = _ir("evaluate", {"expr": "x + 1"}, ["x = 1"], [X])
    assert _step(q, "2", "value", [("compute", "Subs(sqrt(x), x, 4) = 2")]) == ("CORRECT", "verified")
    assert _step(q, "2", "value", [("compute", "at(diff(x**2, x), x, 3) = 6")]) == ("CORRECT", "verified")


def test_pinned_value_that_makes_a_sum_term_undefined():
    for g, v in ((["a = 2"], [X, A, K]), ([], [X, AC2, K])):
        assert _v(_anti("1 + Sum((k - a)/(k - a), (k, 1, 3)) - 3", g, v), "x", "expression") == "UNKNOWN"
        assert _v(_anti("1 + Product((k - a)/(k - a), (k, 1, 3)) - 1", g, v), "x", "expression") == "UNKNOWN"
        assert _v(_der("x + Sum((k - a)/(k - a), (k, 1, 3)) - 3", None, g, v), "1", "expression") == "UNKNOWN"
    assert _v(_anti("1 + Sum((k - a)/(k - a), (k, 1, 3)) - 3", ["a = 5"], [X, A, K]), "x", "expression") != "INCORRECT"


def test_negative_base_with_a_variable_exponent_is_a_convention():
    assert _v(_der("x + (-1)**x - (-1)**x", None), "1", "expression") == "UNKNOWN"
    assert _v(_der("x + 0*(-2)**x", "1/2"), "1") == "UNKNOWN"
    assert _v(_tan("x + 0*(-2)**x", "1/2"), "y = x", "equation") == "UNKNOWN"
    assert _v(_anti("1 + (-1)**x - (-1)**x"), "x", "expression") == "UNKNOWN"
    assert _v(_lim("x + 0*(-1)**x", "1/2"), "1/2") == "UNKNOWN"
    assert _v(_lim("(-1)**x", "0"), "1") == "UNKNOWN"
    assert _dne(_lim("(-1)**x", "0")) == "UNKNOWN"
    assert _v(_simp("x + (-1)**x - (-1)**x"), "x", "expression") == "UNKNOWN"
    # an integer exponent has the curriculum's value
    assert _v(_ss("(-1)**(k + 1)/k**2", 1, 3, [], [K]), "31/36") == "CORRECT"
    assert _v(_ss("(-1)**(k + 1)/k**2", 1, "oo", [], [K]), "pi**2/12") == "CORRECT"
    assert _v(_ir("evaluate", {"expr": "Sum((-1)**(k + 1)/k**2, (k, 1, oo))"}, [], [K]), "pi**2/12") == "CORRECT"
    q = _ir("evaluate", {"expr": "(-1)**n"}, ["n = 3"], [{"name": "n", "domain": "integer"}])
    assert _v(q, "-1") == "CORRECT"


def test_limit_of_an_expression_defined_nowhere_in_the_region():
    for g, v, dod in _writings("x > 0", "positive_real"):
        assert _dne(_lim("x + 0*sqrt(-x)", "0", g, v, dod)) == "UNKNOWN"
        assert _v(_lim("x + 0*sqrt(-x)", "0", g, v, dod), "0") == "UNKNOWN"
        assert _dne(_lim("x + 0*log(-x)", "2", g, v, dod)) == "UNKNOWN"
        assert _dne(_lim("x + 0*sqrt(-x)", "oo", g, v, dod)) == "UNKNOWN"
    assert _dne(_lim("x + 0*log(a*x) + 0*log(-x)", "1", ["a = 1"], XA)) == "UNKNOWN"
    assert _dne(_lim("sqrt(x)", "-1")) != "INCORRECT"


# --- round 2: the unjust rejection R8 and the coverage R1..R7, decided by proof ----------------------------------
AP = {"name": "a", "domain": "positive_real"}
BP = {"name": "b", "domain": "positive_real"}
KP = {"name": "k", "domain": "positive_real"}
NP = {"name": "n", "domain": "positive_integer"}


def test_derivative_of_an_absolute_value_lives_where_f_is_differentiable():
    for f, c in (("Abs(x)", "x/Abs(x)"), ("Abs(x)", "Abs(x)/x"), ("Abs(x)", "x/sqrt(x**2)"),
                 ("Abs(x)", "Piecewise((1, x > 0), (-1, x < 0))"), ("Abs(x - 1)", "(x - 1)/Abs(x - 1)"),
                 ("Abs(x**2 - 1)", "2*x*(x**2 - 1)/Abs(x**2 - 1)"), ("Abs(sin(x))", "cos(x)*sin(x)/Abs(sin(x))"),
                 ("Abs(x)**3", "3*x*Abs(x)")):
        assert _v(_der(f), c, "expression") == "CORRECT", (f, c)
    assert _v(_der("Abs(x)"), "sign(x)", "expression") == "UNKNOWN"          # sign(0) = 0: a value at the corner
    for f, c in (("Abs(x)", "-x/Abs(x)"), ("Abs(sin(x))", "-cos(x)*sin(x)/Abs(sin(x))"),
                 ("Abs(x)**3", "3*x**5/Abs(x)**3"), ("x*Abs(x)", "2*x**2/Abs(x)")):   # a derivative 0 at 0
        assert _v(_der(f), c, "expression") == "INCORRECT", (f, c)
    # sin(x)*|sin(x)| has the derivative 0 at every k*pi: no corner there, the claim has no value there
    assert _v(_der("sin(x)*Abs(sin(x))"), "2*cos(x)*sin(x)**2/Abs(sin(x))", "expression") == "INCORRECT"
    assert _v(_der("sin(x)*Abs(sin(x))"), "2*cos(x)*Abs(sin(x))", "expression") == "CORRECT"
    q = _ir("derivative", {"f": "Abs(x)", "var": "x", "order": 2}, [], [X], "expression")
    assert _v(q, "0", "expression") == "UNKNOWN"                          # 0 at 0, where |x|' jumps


def test_interior_point_proved_by_a_strict_condition():
    assert _v(_der("tan(x**2)", "1"), "2 + 2*tan(1)**2") == "CORRECT"
    assert _v(_der("tan(x**2)", "1"), "2") == "INCORRECT"
    assert _v(_der("tan(x**2)"), "2*x/cos(x**2)**2", "expression") == "CORRECT"
    assert _v(_der("tan(x**2)"), "2/cos(x**2)**2", "expression") == "INCORRECT"
    assert _v(_tan("tan(x**2)", "1"), "y = (2 + 2*tan(1)**2)*(x - 1) + tan(1)", "equation") == "CORRECT"
    assert _v(_anti("2*x/cos(x**2)**2"), "tan(x**2)", "expression") == "CORRECT"
    assert _v(_anti("2*x/cos(x**2)**2"), "2*tan(x**2)", "expression") == "INCORRECT"
    assert _v(_der("1/(x - cos(x))", "pi"), "-1/(pi + 1)**2") == "CORRECT"
    assert _v(_der("1/(x + exp(x))", "0"), "-2") == "CORRECT"
    assert _v(_der("x + 0/floor(x)", "1"), "1") == "UNKNOWN"              # floor jumps at 1


def test_parameter_of_declared_sign_for_every_value():
    assert _v(_der("asin(x/a)", None, [], [X, AP]), "1/sqrt(a**2 - x**2)", "expression") == "CORRECT"
    assert _v(_der("asin(x/a)", None, [], [X, AP]), "2/sqrt(a**2 - x**2)", "expression") == "INCORRECT"
    assert _v(_der("sqrt(a**2 - x**2)", None, [], [X, AP]), "-x/sqrt(a**2 - x**2)", "expression") == "CORRECT"
    assert _v(_der("log(a*x + b)", None, [], [X, AP, BP]), "a/(a*x + b)", "expression") == "CORRECT"
    assert _v(_der("log(a*x + b)", None, [], [X, AP, BP]), "2*a/(a*x + b)", "expression") == "INCORRECT"
    assert _v(_der("log(k*x)", None, [], [X, KP]), "1/x", "expression") == "CORRECT"
    assert _v(_der("log(x**n)", None, [], [X, NP]), "n/x", "expression") == "CORRECT"
    assert _v(_der("log(a*x + 1)", None, ["a > 0"], XA), "a/(a*x + 1)", "expression") == "CORRECT"
    # a free: a = 0 leaves sqrt(a**2 - x**2) the point 0 alone
    assert _v(_der("sqrt(a**2 - x**2)", None, [], XA), "-x/sqrt(a**2 - x**2)", "expression") == "UNKNOWN"


def test_primitive_with_declared_parameters_is_real():
    for f, F in (("exp(k*x)", "exp(k*x)/k"), ("sin(k*x)", "-cos(k*x)/k"), ("exp(-k*x)", "-exp(-k*x)/k")):
        assert _v(_anti(f, [], [X, KP]), F, "expression") == "CORRECT"
    assert _v(_anti("x**n", [], [X, NP]), "x**(n + 1)/(n + 1)", "expression") == "CORRECT"
    assert _v(_anti("1/(x**2 + a**2)", [], [X, AP]), "atan(x/a)/a", "expression") == "CORRECT"
    assert _v(_anti("exp(k*x)", [], [X, KP]), "exp(k*x)", "expression") != "CORRECT"


def test_given_that_restates_the_curve():
    assert _v(_tan("x**3", "1", ["y = x**3"]), "y = 3*x - 2", "equation") == "CORRECT"
    assert _v(_tan("x**3", "1", ["y = x**3"]), "y = 3*x", "equation") == "INCORRECT"
    assert _v(_tan("sqrt(x)", "4", ["y = sqrt(x)"]), "y = x/4 + 1", "equation") == "CORRECT"
    assert _v(_der("x**2", "1", ["y = x**2"], [X, Y]), "2") == "CORRECT"
    assert _v(_anti("2*x", ["y = x**2"], [X, Y]), "x**2", "expression") == "CORRECT"
    assert _v(_lim("x**2", "1", ["y = x**2"], [X, Y]), "1") == "CORRECT"
    # y declared positive, or y > 1 given too: the given restricts x (x > 0, x > 1)
    assert _v(_der("x**3", "-1", ["y = x**3"], [X, {"name": "y", "domain": "positive_real"}]), "3") == "UNKNOWN"
    assert _v(_der("x**3", "0", ["y = x**3", "y > 1"], [X, Y]), "0") == "UNKNOWN"


def test_periodic_given_read_near_the_point():
    assert _v(_der("x**2", "1", ["cos(x) > 0"]), "2") == "CORRECT"
    assert _v(_der("x**2", "1", ["cos(x) > 0"]), "3") == "INCORRECT"
    assert _v(_der("x**2", "2", ["cos(x) > 0"]), "4") == "UNKNOWN"         # cos(2) < 0: outside
    assert _v(_anti("cos(x)", ["cos(x) > 0"]), "sin(x)", "expression") == "CORRECT"
    assert _v(_anti("cos(x)", ["cos(x) > 0"]), "-sin(x)", "expression") == "INCORRECT"
    assert _v(_lim("x*cos(x)", "pi", ["cos(x) < 0"]), "-pi") == "CORRECT"
    assert _v(_lim("x*cos(x)", "pi", ["cos(x) < 0"]), "pi") == "INCORRECT"
    assert _v(_lim("sin(x)/x", "0", ["sin(x) != 0"]), "1") == "CORRECT"


def test_primitive_continuous_across_the_gap_has_one_constant():
    assert _v(_anti("x/Abs(x)"), "Abs(x)", "expression") == "CORRECT"
    assert _v(_anti("x/Abs(x)"), "Abs(x) + sign(x)", "expression") == "UNKNOWN"
    assert _v(_anti("log(Abs(x)) + 1"), "x*log(Abs(x))", "expression") == "CORRECT"
    # atan(tan(x**2)) - x**2 is constant on each piece of cos(x**2) != 0, another constant on each
    assert _v(_anti("2*x/cos(x**2)**2"), "tan(x**2) + atan(tan(x**2)) - x**2", "expression") != "CORRECT"


def test_convergence_at_an_infinite_end_with_a_declared_parameter():
    q = _ir("derivative", {"f": "Integral(exp(-a*t), (t, x, oo))", "var": "x"}, [], [X, T_, AP], "expression")
    assert _v(q, "-exp(-a*x)", "expression") == "CORRECT"
    assert _v(q, "exp(-a*x)", "expression") == "INCORRECT"
    q = _ir("derivative", {"f": "Integral(t**(-21/20), (t, x, oo))", "var": "x"}, [], [XP, T_], "expression")
    assert _v(q, "-x**(-21/20)", "expression") == "CORRECT"
    q = _ir("derivative", {"f": "Integral(exp(-a*t), (t, x, oo))", "var": "x"}, [], [X, T_, A], "expression")
    assert _v(q, "-exp(-a*x)", "expression") == "UNKNOWN"


# --- round 3: the attack on round 2 (`d4/saldiri/d4e2/`): false accepts YO-1..YO-5, the convention RK-8, coverage and
# robustness RK-1..RK-7 ---------------------------------------------------------------------------------------------
NI = {"name": "n", "domain": "integer"}
NN = {"name": "n", "domain": "natural"}
D1 = "Integral(1/(1 + t**2*sin(t)**2), (t, 0, oo))"


def test_round3_a_sympy_limit_is_no_proof_of_convergence():
    # 1/(1 + t**2*sin(t)**2) >= 1/(1 + T**2*u**2) around n*pi: the integral diverges, SymPy's limit of t**(3/2)*g is 0
    for e, c in ((f"0*{D1} + 1", "1"), (f"{D1} - {D1}", "0"),
                 ("0*Integral(1/(1 + t**2*cos(t)**2), (t, 0, oo)) + 1", "1"),
                 ("0*Integral(t**2/(1 + t**6*sin(t)**2), (t, 1, oo)) + 1", "1"),
                 ("0*Integral(1/(t**2 + cos(1/t)**2), (t, 0, 1)) + 1", "1")):
        assert _v(_ir("evaluate", {"expr": e}, [], [T_]), c) != "CORRECT", e
    q = _ir("derivative", {"f": "Integral(1/(1 + t**2*cos(t)**2), (t, x, oo))", "var": "x"}, [], [X, T_], "expression")
    assert _v(q, "-1/(1 + x**2*cos(x)**2)", "expression") == "UNKNOWN"
    q = _ir("evaluate", {"expr": "x + 1"}, ["x = 1"], [X, T_])
    assert _step(q, "2", "value", [("compute", f"{D1}*0 = 0")]) == ("CORRECT", "unknown")
    # a majorant: |sin| <= 1, e^(-t)
    for e in ("0*Integral(sin(t)/t**2, (t, 1, oo)) + 1", "0*Integral(exp(-t)*cos(t), (t, 0, oo)) + 1"):
        assert _v(_ir("evaluate", {"expr": e}, [], [T_]), "1") == "CORRECT", e


def test_round3_series_sum_undecided_term_and_a_pin_in_any_form():
    KAB = [K, A, B]
    for g, v in ((["2*a = 4"], None), (["a - 2 = 0"], None), (["a**2 = 4", "a > 0"], None), (["a = b", "b = 2"], KAB),
                 ([], [K, {"name": "a", "domain": "real", "constraints": ["2*a = 4"]}])):
        assert _v(_ss("(k - a)/(k - a)", 1, 3, g, v), "3") == "UNKNOWN", g
        assert _v(_ss("a*k", 1, 3, g, v), "12") == "CORRECT", g
        assert _v(_ss("a*k", 1, 3, g, v), "13") == "INCORRECT", g
    assert _v(_ss("0*log(k - a) + 1", 1, 2, ["a > 5"]), "2") == "UNKNOWN"
    assert _v(_ss("(k - a)/(k - a)", 1, 3), "3") == "UNKNOWN"                 # a free: 0/0 at a = 1, 2, 3
    for term, lo, hi, val in (("(-1)**(k/2)", 0, 3, "0"), ("(-9)**(k/2)", 0, 2, "-8 + 3*I")):
        assert _v(_ss(term, lo, hi, [], [K]), val) == "UNKNOWN", term
    assert _v(_ss("a**(k/2)", 0, 3, ["a = -1"]), "0") == "UNKNOWN"
    assert _v(_ss("(k - 7)/(k - 7)", 1, 3, [], [K]), "3") == "CORRECT"
    assert _v(_cf("a(n) = c*a(n - 1)", {"1": "1"}, ["2*c = 0"]), "c**(n - 1)", "expression") == "UNKNOWN"
    q = _ir("recurrence_term", {"recurrence": "a(n) = c*a(n - 1)", "initial": {"1": "1"}, "var": "n", "name": "a",
                                "index": "4"}, ["2*c = 4"], [{"name": "n", "domain": "positive_integer"}, {"name": "c"}])
    assert _v(q, "8") == "CORRECT"


def test_round3_claim_has_a_value_where_the_derivative_exists():
    AN = {"name": "a", "domain": "nonneg_real"}
    # a = 0 is allowed: the claim has no value there (YO-3)
    assert _v(_der("log(a*x + 1)", None, [], [X, AN]), "1/(x + 1/a)", "expression") == "UNKNOWN"
    assert _v(_der("log(a*x + 1)", None, ["a >= 0"], XA), "1/(x + 1/a)", "expression") == "UNKNOWN"
    assert _v(_der("asin(x/a)", None, [], [X, AP]), "(a - 1)/((a - 1)*sqrt(a**2 - x**2))", "expression") == "UNKNOWN"
    assert _v(_der("log(a*x + 1)", None, [], [X, AP]), "1/(x + 1/a)", "expression") == "CORRECT"
    assert _v(_der("log(a*x + 1)", None, [], [X, AP]), "a/(a*x + 1)", "expression") == "CORRECT"
    # no value on part of the derivative's domain, where f has a derivative: INCORRECT (RK-8)
    for f, c, v in (("log(a*x)", "1/x + 0*sqrt(-x)", [X, AP]), ("log(x**n)", "n/x + 0*sqrt(-x)", [X, NP]),
                    ("Abs(x)", "x/Abs(x) + 0*sqrt(x)", None), ("tan(x**2)", "2*x*sec(x**2)**2 + 0*sqrt(x)", None),
                    ("x**2", "2*x**2/x", None), ("x**2", "2*x + log(x) - log(x)", None), ("x**2", "2*sqrt(x)**2", None),
                    ("x**3", "x**3*(3/x)", None), ("x*Abs(x)", "2*x*Abs(x)/x", None),
                    ("x**2*exp(x)", "x**2*exp(x)*(2/x + 1)", None), ("x**2*sin(x)", "x**2*sin(x)*(2/x + cos(x)/sin(x))", None)):
        assert _v(_der(f, None, [], v), c, "expression") == "INCORRECT", (f, c)
    for f, c in (("x**2", "2*x"), ("Abs(x)", "x/Abs(x)"), ("x**2/x", "x/x"), ("tan(x)", "1/cos(x)**2")):
        assert _v(_der(f), c, "expression") == "CORRECT", (f, c)
    assert _v(_der("x**2", None, ["x > 0"]), "2*x**2/x", "expression") == "CORRECT"


def test_round3_kinks_of_every_switch():
    for f, c in (("Max(x, -x)", "sign(x)"), ("x*sign(x)", "sign(x)"), ("Min(x, -x)", "-sign(x)"),
                 ("Max(x, 0)", "(1 + sign(x))/2"), ("sign(x)", "0"), ("sign(x) + x", "1"), ("sign(sin(x))", "0"),
                 ("tan(x**2) + sign(x)", "2*x*sec(x**2)**2"), ("Piecewise((x, x > 0), (-x, x <= 0))", "sign(x)")):
        assert _v(_der(f), c, "expression") == "UNKNOWN", (f, c)
    q = _ir("derivative", {"f": "x*Max(x, -x)", "var": "x", "order": 2}, [], [X], "expression")
    assert _v(q, "2*sign(x)", "expression") == "UNKNOWN"
    assert _v(_der("Max(cos(x), -cos(x))", None, ["sin(x) > 0"]), "-sign(cos(x))*sin(x)", "expression") == "UNKNOWN"
    assert _v(_der("Max(x, -x)"), "x/Abs(x)", "expression") == "CORRECT"
    assert _v(_der("Max(x, -x)"), "Piecewise((1, x > 0), (-1, x < 0))", "expression") == "CORRECT"
    assert _v(_der("x**2*sign(x)"), "2*Abs(x)", "expression") == "CORRECT"
    assert _v(_der("x**2*sign(x)"), "2*x", "expression") == "INCORRECT"


def test_round3_written_givens_constraints_and_domain_of_discourse():
    G = "x + 0*sqrt(x - 1) > 0"                                         # x >= 1 as written
    for g, v, dod in _writings(G):
        assert _dne(_lim("Abs(x - 1)/(x - 1)", "1", g, v, dod)) == "INCORRECT"
        assert _v(_lim("Abs(x - 1)/(x - 1)", "1", g, v, dod), "1") == "CORRECT"
        q = _ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, g, v, "set", dod)
        assert _v(q, "{1/2}", "set") != "CORRECT"
    assert _v(_lim("x", "1/2", ["0*log(x - 1) >= 0"]), "1/2") == "UNKNOWN"
    q = _ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, [], [xc("sqrt(x)**2 = x")], "set")
    assert _v(q, "{-1/2, 1/2}", "set") == "INCORRECT"
    assert _v(q, "{1/2}", "set") == "CORRECT"


def test_round3_a_simple_zero_of_u_is_a_corner():
    for f, c in (("Abs(log(x))", "log(x)/(x*Abs(log(x)))"), ("Abs(sqrt(x) - 1)", "(sqrt(x) - 1)/(2*sqrt(x)*Abs(sqrt(x) - 1))"),
                 ("x*Abs(log(x))", "Abs(log(x)) + log(x)/Abs(log(x))"), ("Abs(log(x))", "Piecewise((1/x, x > 1), (-1/x, x < 1))")):
        assert _v(_der(f), c, "expression") == "CORRECT", (f, c)
    assert _v(_der("Abs(log(x))"), "-log(x)/(x*Abs(log(x)))", "expression") == "INCORRECT"
    assert _v(_der("Abs(log(x))"), "sign(log(x))/x", "expression") == "UNKNOWN"


def test_round3_refutation_off_kinks_not_listed():
    XPOS = [{"name": "x", "domain": "positive_real"}]
    for f, c, v in (("Abs(tan(x))", "1/cos(x)**2", None), ("Abs(sin(x))", "cos(x)", XPOS), ("Abs(x**2 + x + 1)", "2*x", None)):
        assert _v(_der(f, None, [], v), c, "expression") == "INCORRECT", (f, c)
    assert _v(_der("Abs(sin(x))", None, [], XPOS), "cos(x)*Abs(sin(x))/sin(x)", "expression") == "CORRECT"
    assert _v(_der("Abs(cot(x))"), "-cot(x)/(sin(x)**2*Abs(cot(x)))", "expression") == "CORRECT"
    # x = cos(x) is solved by no exact class: the refutation stands at a point where f is analytic (0: f' = -1)
    assert _v(_der("Abs(x - cos(x))"), "1 + sin(x)", "expression") == "INCORRECT"
    # every zero of x - cos(x) is simple (1 + sin(x) = 0 only where x - cos(x) != 0): a corner, where the claim has no
    # value (round 4, RK-6): CORRECT or UNKNOWN, never INCORRECT
    assert _v(_der("Abs(x - cos(x))"), "(1 + sin(x))*(x - cos(x))/Abs(x - cos(x))", "expression") != "INCORRECT"


def test_round3_an_integer_exponent_is_no_convention():
    for nv in (NI, NN):
        assert _v(_der("x**2*(-1)**n", None, [], [X, nv]), "2*x*(-1)**n", "expression") == "CORRECT"
        assert _v(_der("x**2*(-1)**n", None, [], [X, nv]), "2*x", "expression") == "INCORRECT"
        assert _v(_ext("(-1)**(2*n)*x**2", "max", "[0, 2]", [], [X, nv]), "4") == "CORRECT"
        assert _v(_ss("k*(-1)**n", 1, 3, [], [K, nv]), "6*(-1)**n") == "CORRECT"
    assert _v(_der("x**2*(-1)**n", None, [], [X, {"name": "n", "domain": "real"}]), "2*x*(-1)**n", "expression") == "UNKNOWN"


def test_round3_convergence_by_a_majorant():
    for I, val, wrong in (("exp(-sqrt(t))", "2", "3"), ("exp(-t**(1/3))", "6", "5")):
        q = _ir("evaluate", {"expr": f"Integral({I}, (t, 0, oo))"}, [], [T_])
        assert _v(q, val) == "CORRECT" and _v(q, wrong) == "INCORRECT", I
    q = _ir("derivative", {"f": "Integral(exp(-t)*(x + t), (t, 0, oo))", "var": "x"}, [], [X, T_], "expression")
    assert _v(q, "1", "expression") == "CORRECT"
    assert _v(q, "2", "expression") == "INCORRECT"
    q = _ir("derivative", {"f": "Integral(exp(-t)*cos(x*t), (t, 0, oo))", "var": "x"}, [], [X, T_], "expression")
    assert _v(q, "2*x/(1 + x**2)**2", "expression") == "INCORRECT"
    # SymPy's limit of t**2/(x**2*t**3 + 1) at oo is 0 for x != 0 alone; at x = 0 the integral diverges: x is bounded
    # by |x|, and no majorant decays
    q = _ir("derivative", {"f": "x + 0*Integral(1/(x**2*t**3 + 1), (t, 0, oo))", "var": "x"}, [], [X, T_], "expression")
    assert _v(q, "1", "expression") != "CORRECT"


def test_round3_kink_reading_has_a_budget(monkeypatch):
    import mathverify.certify.calculus as cal
    calls = []
    real = cal.derivative_at_point

    def counted(*a, **k):
        calls.append(a)
        return real(*a, **k)
    monkeypatch.setattr(cal, "derivative_at_point", counted)
    # seven nested-radical kinks, each decided by the exact rule (a simple zero, gcd 1): no limit taken
    assert _v(_der("Abs(x**3 - 3*x + 1) + Abs(x**4 - 10*x**2 + 1)"), "0", "expression") == "INCORRECT"
    assert calls == []
    calls.clear()
    assert _v(_der("Abs(x**4 - 10*x**2 + 1)**3"), "0", "expression") == "INCORRECT"
    assert calls == []
    calls.clear()
    assert _v(_der("Piecewise((x, x > 0), (-x, x <= 0)) + Piecewise((x - 1, x > 1), (1 - x, x <= 1))"
                   " + Piecewise((x - 2, x > 2), (2 - x, x <= 2)) + Piecewise((x - 3, x > 3), (3 - x, x <= 3))"),
              "0", "expression") == "INCORRECT"
    assert len(calls) <= cal._KINK_BUDGET


def test_round3_kink_reading_does_not_hang_on_the_hash_seed():
    import os
    import subprocess
    import sys
    code = ("from mathverify.verifier import verify\n"
            "q = {'task': {'kind': 'derivative', 'params': {'f': 'Abs(log(x)) + Abs(tan(x))', 'var': 'x'}},"
            " 'vars': [{'name': 'x', 'domain': 'real'}], 'givens': [], 'answer_shape': 'expression'}\n"
            "print(verify(q, {'claimed_answer': {'kind': 'expression', 'payload': '0'}, 'steps': []}).verdict)\n")
    for seed in ("3", "5"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=300)
        assert out.stdout.strip().splitlines()[-1] == "INCORRECT", (seed, out.stdout, out.stderr[-500:])


def test_round3_subs_body_defined_near_its_point_by_a_strict_condition():
    q = _ir("evaluate", {"expr": "x + 1"}, ["x = 1"], [X])
    for c in ("at(diff(1/(x - cos(x)), x), x, pi) = -1/(pi + 1)**2", "at(diff(tan(x**2), x), x, 1) = 2 + 2*tan(1)**2",
              "at(diff(1/(x + exp(x)), x), x, 0) = -2"):
        assert _step(q, "2", "value", [("compute", c)]) == ("CORRECT", "verified"), c
    assert _step(q, "2", "value", [("compute", "at(diff(1/(x + exp(x)), x), x, 0) = -3")])[1] == "refuted"


def test_round3_guards_of_the_new_readings():
    # Max/Min read as |.|: a family of corners, the claim undefined exactly there
    assert _v(_der("Max(sin(x), -sin(x))"), "cos(x)*sin(x)/Abs(sin(x))", "expression") == "CORRECT"
    # a double zero of u is no corner: |x**3 - x**2| has the derivative 0 at 0, where the claim has no value
    assert _v(_der("Abs(x**3 - x**2)"), "(3*x**2 - 2*x)*(x**3 - x**2)/Abs(x**3 - x**2)", "expression") == "INCORRECT"
    # a written condition not strict at the point (x**4 - 2*x**2 + 1 >= 0 at 1): f is |x**2 - 1| there, no derivative
    assert _v(_der("sqrt(x**4 - 2*x**2 + 1)"), "(2*x**3 - 2*x)/sqrt(x**4 - 2*x**2 + 1)", "expression") != "INCORRECT"
    # acosh has no written condition: never read as analytic
    assert _v(_der("acosh(x)"), "1/sqrt(x**2 - 1)", "expression") != "INCORRECT"
    # a - x >= 0 is not x - a >= 0: the sign of the ratio counts
    assert _v(_der("sqrt(x - a)", None, [], XA), "1/(2*sqrt(x - a)) + 0*sqrt(a - x)", "expression") != "CORRECT"
    assert _v(_der("sqrt(x - a)", None, [], XA), "1/(2*sqrt(x - a))", "expression") == "CORRECT"
    # a claim condition not proved on the region: never CORRECT
    assert _v(_der("tan(x)", None, ["cos(x) > 0"]), "sec(x)**2 + 0*sqrt(sin(x))", "expression") != "CORRECT"
    # a symbol of undeclared sign in the integrand is bounded by its absolute value: e^(-x*t) diverges for x <= 0
    q = _ir("derivative", {"f": "x + 0*Integral(exp(-x*t), (t, 0, oo))", "var": "x"}, [], [X, T_], "expression")
    assert _v(q, "1", "expression") != "CORRECT"
    # a function no rule reads is never analytic, a fraction of a step is (unit)
    import sympy as sp
    from mathverify.certify.calculus import smooth_at
    x = sp.Symbol("x", real=True)
    assert smooth_at(sp.Function("g")(x), x, sp.S.Zero, [], []) is False
    assert smooth_at(sp.sin(x) + sp.Abs(x - 1), x, sp.S.Zero, [x - 1], []) is True
    assert smooth_at(sp.Abs(x - 1), x, sp.S.One, [x - 1], []) is False
    # the extremum of a function or on an interval naming a free symbol: no value
    assert _v(_ext("a*x", "max", "[0, 1]", [], XA), "a") == "UNKNOWN"
    assert _v(_ext("x", "max", "[0, b]", [], XB), "b") == "UNKNOWN"
    # the zeros of sin(x) are ends of sqrt(sin(x))**3's region, not points of the comparison: the claim keeps its value
    assert _v(_der("sqrt(sin(x))**3"), "3*cos(x)*sin(x)/(2*sqrt(sin(x)))", "expression") == "CORRECT"


def test_round3_a_written_condition_no_class_solves_is_not_defined():
    # d4b round 8, YO-2: 2**x + x - 3 >= 0 (x >= 1) and -1 <= 2**x + x - 2 <= 1 (0 <= x <= 1) are solved by no exact
    # class; written_undefined_in is None there, and every caller abstains on it
    SQ, AC = "sqrt(2**x + x - 3)", "acos(2**x + x - 2)"
    assert _v(_ext(f"x**2 + {SQ} - {SQ}", "min", None), "0") == "UNKNOWN"
    assert _v(_ext(f"x**2 + {SQ} - {SQ}", "min", None), "1") != "INCORRECT"
    assert _v(_ext(f"-(x - 3)**2 + 0*{AC}", "max", "[-5, 5]"), "0") == "UNKNOWN"
    assert _v(_ss("k + sqrt(2**k + k - 3) - sqrt(2**k + k - 3)", 0, 3, [], [K]), "6") == "UNKNOWN"
    assert _v(_ss("sqrt(2**k + k - 3)", 0, 3, [], [K]), "sqrt(3) + 2*sqrt(2) + sqrt(2)*I") == "UNKNOWN"
    assert _v(_der(f"x + {SQ} - {SQ}", "0"), "1") == "UNKNOWN"
    assert _v(_der(f"x + {SQ} - {SQ}", "2"), "1") == "CORRECT"


def test_round3_dirichlet_test_takes_no_parameter():
    # attack on d4e round 3, D4E3-YO-1: SymPy's limit of t/(x**2*t**2 + 1) is 0 for a generic x; at x = 0 the
    # integral of t*sin(t) diverges, so x + 0*I(x) has no value at 0
    I = "Integral(t*sin(t)/(x**2*t**2 + 1), (t, 1, oo))"
    V = [X, T_]
    assert _v(_ir("derivative", {"f": f"x + 0*{I}", "var": "x", "at": "0"}, [], V), "1") == "UNKNOWN"
    assert _v(_ir("solve_equation", {"var": "x", "equation": f"x**2 + 0*{I} = 0"}, [], V, "set"), "{0}",
              "set") == "UNKNOWN"
    assert _v(_ir("extremum", {"f": f"x**2 + 0*{I}", "var": "x", "which": "min", "interval": "[-1, 1]"}, [], V),
              "0") == "UNKNOWN"
    # without a parameter the test still reads sin(t)/t
    assert _v(_ir("derivative", {"f": "x + 0*Integral(sin(t)/t, (t, 1, oo))", "var": "x", "at": "0"}, [], V),
              "1") == "CORRECT"
