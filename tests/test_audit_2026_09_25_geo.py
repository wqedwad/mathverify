"""Audit of 25 Sep 2026 (geometry / combinatorics / series / linear algebra certificates).

Every test here is a measured reproduction: before the fix the verdict was the opposite of the
mathematical truth (false CORRECT or false INCORRECT), or the layer crashed. The ground truth is
stated next to each case and was computed independently (exact iteration, brute force, a point on
one curve and not on the other)."""
import sympy as sp

from mathverify.verifier import verify


def _ir(kind, params, **kw):
    d = {"task": {"kind": kind, "params": params}, "vars": kw.pop("vars", []), "givens": [],
         "answer_shape": kw.pop("answer_shape", "scalar")}
    d.update(kw)
    return d


def _v(ir, payload, kind="value", steps=None, option=None):
    ca = {"kind": kind}
    if payload is not None:
        ca["payload"] = payload
    if option is not None:
        ca["option"] = option
    return verify(ir, {"claimed_answer": ca, "steps": steps or []}).verdict


# ------------------------------------------------------------------------------------------------
# equation_of: point sets of the plane, not solveset in x (C1, C2, H4)
# ------------------------------------------------------------------------------------------------
def _eq(params):
    return _ir("equation_of", params, answer_shape="equation")


def test_horizontal_line_rejects_other_curves_in_y():
    # truth y = 2; `y**3 = 27` is the line y = 3 — (0, 2) is on the truth and not on the claim
    ir = _eq({"object": "line_points", "p1": [0, 2], "p2": [5, 2]})
    assert _v(ir, "y**3 = 27", "equation") == "INCORRECT"
    assert _v(ir, "y**2 = 4", "equation") == "INCORRECT"            # also the line y = -2
    assert _v(ir, "y = 2", "equation") == "CORRECT"
    assert _v(ir, "(y - 2)**3 = 0", "equation") == "CORRECT"       # same zero set
    tan = _eq({"object": "tangent_to_circle_at_point", "center": [0, 0], "point": [0, 5]})
    assert _v(tan, "y**2 = 25", "equation") == "INCORRECT"         # both tangents y = ±5
    assert _v(tan, "y = 5", "equation") == "CORRECT"
    s0 = _eq({"object": "line_point_slope", "p": [3, 4], "slope": 0})
    assert _v(s0, "y**2 = 25", "equation") == "INCORRECT"
    par = _eq({"object": "line_point_parallel", "p": [1, -1], "line": "y = 3"})
    assert _v(par, "(y - 3)**2 = 0", "equation") == "INCORRECT"


def test_extra_factor_without_x_is_not_dropped():
    ir = _eq({"object": "line_points", "p1": [0, 1], "p2": [1, 3]})          # y = 2x + 1
    assert _v(ir, "y*(2*x - y + 1) = 0", "equation") == "INCORRECT"         # plus the x-axis
    assert _v(ir, "(2*x - y + 1)*(y - 5) = 0", "equation") == "INCORRECT"
    assert _v(ir, "(2*x - y + 1)*floor(y) = 0", "equation") != "CORRECT"     # a whole strip
    assert _v(ir, "(2*x - y + 1)*sin(y) = 0", "equation") != "CORRECT"
    assert _v(ir, "log(y) = log(2*x + 1)", "equation") == "INCORRECT"       # a half line
    assert _v(ir, "4*x - 2*y + 2 = 0", "equation") == "CORRECT"
    assert _v(ir, "x = (y - 1)/2", "equation") == "CORRECT"
    pb = _eq({"object": "perpendicular_bisector", "p1": [0, 0], "p2": [4, 0]})   # x = 2
    assert _v(pb, "(x - 2)*(y - 1) = 0", "equation") == "INCORRECT"


def test_claim_undefined_on_the_line_as_written():
    ir = _eq({"object": "line_points", "p1": [0, 1], "p2": [1, 3]})
    # (0, 1) is on the line, and the written claim is undefined there
    assert _v(ir, "(y - 1)/x = 2", "equation") == "INCORRECT"
    assert _v(ir, "(2*x - y + 1)/(x - 3) = 0", "equation") == "INCORRECT"   # misses (3, 7)
    assert _v(ir, "x/x*(y - 2*x - 1) = 0", "equation") == "INCORRECT"       # misses (0, 1)


def test_circle_extra_terms_are_not_ignored():
    ir = _eq({"object": "circle_center_radius", "center": [1, 2], "radius": 3})
    base = "x**2 + y**2 - 2*x - 4*y - 4"
    # (4, 2) is on the circle; the claims are 64, 16, 8, sin(4)**3, 512 there
    for extra in ("x**3", "y**4", "Abs(x*y)", "sin(x)**3", "x**3*y**3"):
        assert _v(ir, f"{base} + {extra} = 0", "equation") == "INCORRECT", extra
    assert _v(ir, f"{base} = 0", "equation") == "CORRECT"
    assert _v(ir, "2*x**2 + 2*y**2 - 4*x - 8*y - 8 = 0", "equation") == "CORRECT"
    assert _v(ir, "(x - 1)**2 + (y - 2)**2 = 9", "equation") == "CORRECT"
    assert _v(ir, "(x - 1)**2 + 2*(y - 2)**2 = 9", "equation") == "INCORRECT"
    dia = _eq({"object": "circle_diameter", "p1": [0, 0], "p2": [4, 0]})
    assert _v(dia, "x**2 - 4*x + y**2 + x**4 = 0", "equation") == "INCORRECT"
    assert _v(dia, "x**2 - 4*x + y**2 = 0", "equation") == "CORRECT"
    r5 = _eq({"object": "circle_center_radius", "center": [0, 0], "radius": "sqrt(5)"})
    assert _v(r5, "x**2 + y**2 = 5", "equation") == "CORRECT"
    assert _v(r5, "x**2 + y**2 = 6", "equation") == "INCORRECT"


def test_vertical_line_with_infinite_slope_and_bad_radius():
    ir = _eq({"object": "line_point_slope", "p": [3, 4], "slope": "oo"})
    assert _v(ir, "x = 3", "equation") == "CORRECT"
    assert _v(ir, "y = 4", "equation") == "INCORRECT"
    neg = _eq({"object": "circle_center_radius", "center": [0, 0], "radius": -2})
    assert _v(neg, "x**2 + y**2 = 4", "equation") == "UNKNOWN"
    # a value where an equation is asked for: no crash, no verdict
    c = _eq({"object": "circle_center_radius", "center": [0, 0], "radius": 1})
    assert _v(c, "1") == "UNKNOWN"


# ------------------------------------------------------------------------------------------------
# synthetic_geometry: degrees, exact comparison, no scale gauge (C3, C4, C5)
# ------------------------------------------------------------------------------------------------
def _geo(points, constraints, target, **kw):
    return _ir("synthetic_geometry", {"points": points, "constraints": constraints, "target": target}, **kw)


def test_degree_mark_means_degrees_in_constraints_and_claims():
    # tyt-geo-002 as printed: |AB| = |AC|, angle A = 40° -> angle B = (180 - 40)/2 = 70
    ir = _geo(["A", "B", "C"], ["dist(A,B)**2 = dist(A,C)**2", "angle(B,A,C) = 40°"], "angle(A,B,C)")
    assert _v(ir, "70") == "CORRECT"
    assert _v(ir, "70°") == "CORRECT"
    assert _v(ir, "90 - pi/9") == "INCORRECT"          # the value of a 2*pi/9-DEGREE apex
    rt = _geo(["A", "B", "C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90°"], "dist(A,C)")
    assert _v(rt, "10") == "CORRECT"
    assert _v(rt, "sqrt(100 - 96*cos(pi**2/360))") == "INCORRECT"
    assert _v(rt, "10°") == "UNKNOWN"                   # a degree mark on a length
    opts = {"A": "40°", "B": "50°", "C": "60°", "D": "70°", "E": "80°"}
    plain = _geo(["A", "B", "C"], ["dist(A,B)**2 = dist(A,C)**2", "angle(B,A,C) = 40"], "angle(A,B,C)",
                 options=opts)
    assert _v(plain, None, option="D") == "CORRECT"
    right = _geo(["A", "B", "C"], ["dist(A,B) = 1", "dist(A,C) = 2", "angle(B,A,C) = 60"], "angle(A,B,C)")
    assert _v(right, "90°") == "CORRECT"
    assert _v(right, "pi/2") == "UNKNOWN"               # right in radians; the unit is the question


def test_no_tolerance_shortcut_in_geometry():
    rt = _geo(["A", "B", "C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90"], "dist(A,C)")
    assert _v(rt, "10") == "CORRECT"
    assert _v(rt, "10.0") == "CORRECT"
    assert _v(rt, "10 + 10**(-19)") == "INCORRECT"
    assert _v(rt, "10000000000000000001/1000000000000000000") == "INCORRECT"
    assert _v(rt, "10 + 10**(-25)*I") == "INCORRECT"
    N = 262537412640768744                              # e^(pi*sqrt(163)) = N - 7.5e-13
    seg = _geo(["A", "B"], [f"dist(A,B) = {N}"], "dist(A,B)")
    assert _v(seg, "exp(pi*sqrt(163))") == "INCORRECT"
    assert _v(seg, str(N)) == "CORRECT"


def test_scale_is_never_fixed_by_the_gauge():
    # CA = CB = 1 alone: apex 60 for AB = 1 but 97.18 for AB = 1.5 -> not determined
    iso = _geo(["A", "B", "C"], ["dist(A,C) = 1", "dist(B,C) = 1"], "angle(A,C,B)")
    assert _v(iso, "60") == "UNKNOWN"
    iso2 = _geo(["A", "B", "C"], ["dist(A,C) = sqrt(2)", "dist(B,C) = sqrt(2)"], "angle(A,C,B)")
    assert _v(iso2, "360*asin(sqrt(2)/4)/pi") == "UNKNOWN"
    area = _geo(["A", "B", "C"], ["area(A,B,C) = 12", "dist(A,C)**2 = dist(B,C)**2"], "angle(A,C,B)")
    assert _v(area, "360*atan(1/48)/pi") == "UNKNOWN"
    equi = _geo(["A", "B", "C"], ["dist(A,C)**2 = dist(A,B)**2", "dist(B,C)**2 = dist(A,B)**2"],
                "dist(A,B)*dist(A,C)/dist(B,C)")                       # = the side, arbitrary
    assert _v(equi, "1") == "UNKNOWN"
    assert _v(_geo(["A", "B", "C"], ["dist(A,C)**2 = dist(A,B)**2", "dist(B,C)**2 = dist(A,B)**2"],
                   "angle(A,B,C)"), "60") == "CORRECT"                 # scale-free, determined
    # determined problems whose constants the old heuristic ignored were UNKNOWN (overdetermined)
    e2 = _geo(["A", "B", "C"], ["dist(A,B) = 2", "dist(A,C) = 2", "dist(B,C) = 2"], "area(A,B,C)")
    assert _v(e2, "sqrt(3)") == "CORRECT"
    r12 = _geo(["A", "B", "C"], ["dist(A,B) = 1", "dist(A,C) = 2", "perpendicular(A,B,A,C)"], "dist(B,C)")
    assert _v(r12, "sqrt(5)") == "CORRECT"
    ri = _geo(["A", "B", "C"], ["perpendicular(C,A,C,B)", "dist(C,A)**2 = dist(C,B)**2", "area(A,B,C) = 8"],
              "dist(A,B)")                                             # legs 4 -> 4*sqrt(2)
    assert _v(ri, "4*sqrt(2)") == "CORRECT"
    assert _v(ri, "8") == "INCORRECT"


# ------------------------------------------------------------------------------------------------
# count_structures / probability: exact predicates, faithful Monte Carlo, no raw-text eval (C10, H1)
# ------------------------------------------------------------------------------------------------
def _cnt(space, predicate=""):
    return _ir("count_structures", {"space": space, "predicate": predicate}, answer_shape="count")


def _prob(space, event):
    return _ir("probability", {"space": space, "event": event})


def test_predicates_use_exact_rationals():
    import itertools
    from fractions import Fraction
    space = {"structure": "sequence", "elements": [0.1, 0.2, 0.5], "k": 2}
    truth = sum(1 for t in itertools.product([Fraction(1, 10), Fraction(1, 5), Fraction(1, 2)], repeat=2)
                if sum(t) == Fraction(3, 10))
    assert truth == 2
    assert _v(_cnt(space, "sum(t) == 0.3"), "2", "count") == "CORRECT"
    assert _v(_cnt(space, "sum(t) == 0.3"), "0", "count") == "INCORRECT"
    assert _v(_prob(space, "sum(t) == 0.3"), "2/9") == "CORRECT"
    dice = {"structure": "product", "sets": [[1, 2, 3, 4, 5, 6]] * 2}
    assert _v(_prob(dice, "sum(t)/len(t) == 3.5"), "1/6") == "CORRECT"      # (1,6),(2,5)... = 6/36
    assert _v(_prob(dice, "t[0]/t[1] == 1/3"), "1/18") == "CORRECT"          # (1,3), (2,6)


def test_monte_carlo_samples_the_counted_space():
    import math
    from mathverify.certify.combinatorics import sample_space, iterate_space
    import random
    # small spaces: the sampler hits exactly the enumerated tuples, uniformly
    for space in ({"structure": "multiset_combination", "n": 4, "k": 2},
                  {"structure": "combination", "elements": [1, 1, 2, 3], "k": 2},
                  {"structure": "arrangement_all", "n": 3, "k": 2}):
        allowed = list(iterate_space(space))
        rng = random.Random(1)
        draws = [sample_space(space, rng) for _ in range(20000)]
        assert set(draws) <= set(allowed)
        freq = {t: draws.count(t) / len(draws) for t in set(draws)}
        expected = {t: allowed.count(t) / len(allowed) for t in set(allowed)}
        assert all(abs(freq.get(t, 0) - p) < 0.02 for t, p in expected.items()), space
    # C(100, 5) all-distinct 5-multisets of 100: correct, space > cap -> never refuted
    ms = {"structure": "multiset_combination", "n": 100, "k": 5}
    assert _v(_cnt(ms, "len(set(t)) == 5"), str(math.comb(100, 5)), "count") == "UNKNOWN"
    assert _v(_cnt(ms, "len(set(t)) == 5"), "1", "count") == "INCORRECT"
    arr = {"structure": "arrangement_all", "n": 12, "k": 3}
    assert _v(_cnt(arr, "len(t) == 12"), str(math.factorial(12)), "count") == "UNKNOWN"


def test_repeated_elements_positions_vs_values():
    word = {"structure": "arrangement_all", "elements": list("ANKARA")}
    assert _v(_cnt(word), "720", "count") == "UNKNOWN"      # positions
    assert _v(_cnt(word), "120", "count") == "UNKNOWN"      # different words: 6!/3!
    assert _v(_cnt(word), "100", "count") == "INCORRECT"    # neither reading
    balls = {"structure": "combination", "elements": ["k1", "k2", "k3", "m1", "m2"], "k": 2}
    assert _v(_prob(balls, "all(x[0] == 'k' for x in t)"), "3/10") == "CORRECT"


def test_count_payload_text_is_parsed_not_evaluated():
    space = {"structure": "combination", "n": 3, "k": 1}                # 3 structures
    # `sympify` would have run these as Python and produced 3 and 6
    assert _v(_cnt(space), "len('abc')", "count") == "UNKNOWN"
    assert _v(_cnt({"structure": "combination", "n": 4, "k": 2}), "sum([1, 2, 3])", "count") == "UNKNOWN"
    assert _v(_cnt(space), "3", "count") == "CORRECT"
    assert _v(_cnt(space), "binomial(3, 1)", "count") == "CORRECT"
    assert _v(_cnt(space), "7/2", "count") == "INCORRECT"
    assert _v(_cnt(space), 3, "count") == "CORRECT"


# ------------------------------------------------------------------------------------------------
# series: closed forms need a proof; definedness as written; no silent branch; exact bounds
# (C6, C7, C9, M2, LOW int bounds)
# ------------------------------------------------------------------------------------------------
_NV = [{"name": "n", "domain": "positive_integer"}]


def _cf(rec, initial):
    return _ir("closed_form", {"recurrence": rec, "initial": initial, "var": "n"}, vars=_NV,
               answer_shape="expression")


def _rt(rec, initial, index):
    return _ir("recurrence_term", {"recurrence": rec, "initial": initial, "index": index, "var": "n"}, vars=_NV)


def _iterate(rec_step, a1, upto):
    vals = {1: sp.Integer(a1)}
    for k in range(2, upto + 1):
        vals[k] = rec_step(vals[k - 1], k)
    return vals


def test_closed_form_window_is_not_a_proof():
    ar = _iterate(lambda p, k: p + 3, 2, 40)                        # a(n) = 3n - 1
    n = sp.Symbol("n")
    claim = 3 * n - 1 + 3 * sp.floor(n / 22)
    assert claim.subs(n, 22) != ar[22]                              # wrong from n = 22 on
    assert _v(_cf("a(n) = a(n-1) + 3", {"1": "2"}), "3*n - 1 + 3*floor(n/22)", "expression") != "CORRECT"
    ge = _cf("a(n) = 2*a(n-1)", {"1": "3"})
    assert _v(ge, "3*2**(n-1) + floor(n/23)", "expression") != "CORRECT"
    assert _v(ge, "3*2**(n-1) + (n-1)*exp(-100*n)", "expression") != "CORRECT"   # wrong at every n >= 2
    assert _v(_cf("a(n) = a(n-1) + 2", {"1": "2"}),
              "2*n + " + "*".join(f"(n-{j})" for j in range(1, 22)), "expression") != "CORRECT"
    assert _v(ge, "3*2**(n-1)", "expression") == "CORRECT"
    assert _v(ge, "3*2**n", "expression") == "INCORRECT"


def test_closed_form_of_arithmetic_sequence_no_longer_crashes():
    ir = _cf("a(n) = a(n-1) + 3", {"1": "2"})
    assert _v(ir, "3*n - 1", "expression") == "CORRECT"
    assert _v(ir, "3*(n-1) + 2", "expression") == "CORRECT"
    assert _v(ir, "3*n + 1", "expression") == "INCORRECT"
    fwd = _cf("a(n+1) = a(n) + 3", {"1": "2"})
    assert _v(fwd, "3*n - 1", "expression") == "CORRECT"
    # the given terms must determine the sequence: order 2 with one term is not enough (a(2) free)
    binet = "(((1+sqrt(5))/2)**n - ((1-sqrt(5))/2)**n)/sqrt(5)"
    assert _v(_cf("a(n) = a(n-1) + a(n-2)", {"1": "1"}), binet, "expression") == "UNKNOWN"
    assert _v(_cf("a(n) = a(n-1) + a(n-2)", {"1": "1", "2": "1"}), binet, "expression") == "CORRECT"
    # ... but a claim that breaks the recurrence where all its terms are in range is refuted
    assert _v(_cf("a(n) = a(n-1) + a(n-2)", {"1": "1"}), "1", "expression") == "INCORRECT"


def test_recurrence_defined_as_written():
    # (n-3)/(n-3) cancels on parsing; as written a(3) does not exist, so neither does a(5)
    assert _v(_rt("a(n) = a(n-1)*(n-3)/(n-3) + 1", {"1": "1"}, 5), "5") == "UNKNOWN"
    assert _v(_rt("a(n) = a(n-1) + 1/(n-3)", {"1": "1"}, 5), "5") == "UNKNOWN"
    assert _v(_rt("a(n) = a(n-1) + 2*a(n-2)", {"1": "1", "2": "3"}, 6), "43") == "CORRECT"
    assert _v(_rt("a(n+1) = 2*a(n) + 1", {"1": "1"}, 5), "31") == "CORRECT"          # forward form
    assert _v(_cf("a(n) = a(n-1) + 1/(n-3)", {"1": "1"}), "1", "expression") != "CORRECT"


def test_implicit_recurrence_needs_a_unique_real_value():
    # a(n)**2 = 4*a(n-1), a(1) = 4: a(2) = ±4, a(3) = ±4 on the real branches -> not unique
    ir = _rt("a(n)**2 = 4*a(n-1)", {"1": "4"}, 3)
    assert _v(ir, "4") == "UNKNOWN"
    assert _v(ir, "-4*I") == "UNKNOWN"
    # a(n)**3 = 8*a(n-1): one real cube root per step -> a(3) = 16**(1/3) = 2*2**(1/3)
    cub = _rt("a(n)**3 = 8*a(n-1)", {"1": "1"}, 3)
    assert _v(cub, "2*2**(1/3)") == "CORRECT"
    assert _v(cub, "2") == "INCORRECT"


def test_series_sum_definedness_and_integer_bounds():
    for vars_ in ([], [{"name": "k", "domain": "positive_integer"}]):
        ir = _ir("series_sum", {"term": "k/k", "var": "k", "lo": -1, "hi": 1}, vars=vars_)
        assert _v(ir, "3") == "UNKNOWN", vars_                 # 0/0 at k = 0, as written
    half = _ir("series_sum", {"term": "k", "var": "k", "lo": "1/2", "hi": 3},
               vars=[{"name": "k", "domain": "positive_integer"}])
    assert _v(half, "6") == "UNKNOWN"                           # int(1/2) = 0 was used
    ok = _ir("series_sum", {"term": "k**2", "var": "k", "lo": 1, "hi": 10},
             vars=[{"name": "k", "domain": "positive_integer"}])
    assert _v(ok, "385") == "CORRECT"
    two = _ir("series_sum", {"term": "1/(k**2 + 1)", "var": "k", "lo": "-oo", "hi": "oo"},
              vars=[{"name": "k", "domain": "integer"}])
    assert _v(two, "pi/tanh(pi)") == "CORRECT"


# ------------------------------------------------------------------------------------------------
# linalg: claims are values (C8); scalar eigenvalue (H2); tuple vectors (H3)
# ------------------------------------------------------------------------------------------------
def _la(op, **params):
    return _ir("linalg", dict(op=op, **params), answer_shape="expression")


def test_matrix_claims_that_compute_are_not_values():
    inv = _la("inverse", matrix="Matrix([[1,2],[3,4]])")
    assert _v(inv, "Matrix([[1,2],[3,4]])**-1") == "UNKNOWN"
    assert _v(inv, "Matrix([[-2, 1], [3/2, -1/2]])") == "CORRECT"
    assert _v(inv, "Matrix([[4, -2], [-3, 1]])/(-2)") == "CORRECT"      # literal / scalar is a value
    assert _v(inv, "-1/2*Matrix([[4, -2], [-3, 1]])") == "CORRECT"
    me = _la("matrix_expr", expr="Matrix([[1,1],[0,1]])**5")
    assert _v(me, "Matrix([[1,1],[0,1]])**5") == "UNKNOWN"                 # the question restated
    assert _v(me, "Matrix([[1,5],[0,1]])") == "CORRECT"
    sy = _la("solve_system", A="Matrix([[1,1],[1,-1]])", b="Matrix([3,1])")
    assert _v(sy, "Matrix([[1,1],[1,-1]])**-1*Matrix([3,1])") == "UNKNOWN"
    assert _v(sy, "(2, 1)") == "CORRECT"
    ev = _la("eigenvector", matrix="Matrix([[2,1],[1,2]])", eigenvalue=3)
    assert _v(ev, "Matrix([[2,1],[1,2]])*Matrix([1,1])") == "UNKNOWN"


def test_single_eigenvalue_and_tuple_vectors():
    assert _v(_la("eigenvalues", matrix="Matrix([[2,0],[0,2]])"), "2") == "CORRECT"
    assert _v(_la("eigenvalues", matrix="Matrix([[3,1],[0,3]])"), "3") == "CORRECT"
    assert _v(_la("eigenvalues", matrix="Matrix([[2,1],[1,2]])"), "3") == "INCORRECT"   # {1, 3}
    assert _v(_la("eigenvalues", matrix="Matrix([[2,0],[0,2]])"), "(2, 2)") == "CORRECT"
    me = _la("matrix_expr", expr="Matrix([[1,2],[3,4]])*Matrix([1,1])")
    assert _v(me, "(3, 7)") == "CORRECT"
    assert _v(me, "(3, 8)") == "INCORRECT"
    assert _v(me, "Matrix([[3, 7]])") == "INCORRECT"         # an explicit ROW is a different matrix
    assert _v(_la("matrix_expr", expr="Matrix([[1,2]])*Matrix([3,4])"), "11") == "CORRECT"
