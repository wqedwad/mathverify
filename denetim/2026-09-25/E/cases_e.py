"""Batch E: equation_of claim-side simplification, under-determined evaluate claim, derivative at a
typed (non-integer) point, antiderivative log(x-1) latent, coverage extras."""
from cases_a import ir

X = [{"name": "x"}]
XY = [{"name": "x"}, {"name": "y"}]
AB = [{"name": "a"}, {"name": "b"}]
CASES = [
    dict(label="E01 equation_of line (0,0),(1,1), claim y = x**2/x",
         ir=ir("equation_of", {"object": "line_points", "p1": ["0", "0"], "p2": ["1", "1"]}, XY, shape="equation"),
         claim={"kind": "equation", "payload": "y = x**2/x"}, right=False, truth="y = x; claimed curve misses (0,0)"),
    dict(label="E02 equation_of line (0,0),(1,1), claim y = x (right)",
         ir=ir("equation_of", {"object": "line_points", "p1": ["0", "0"], "p2": ["1", "1"]}, XY, shape="equation"),
         claim={"kind": "equation", "payload": "y = x"}, right=True, truth="y = x"),
    dict(label="E03 equation_of circle center (0,0) r=1, claim x^2 + y^2 = sqrt(x**2)**2/x**2... (y**2 = 1 - x**2)",
         ir=ir("equation_of", {"object": "circle_center_radius", "center": ["0", "0"], "radius": "1"}, XY,
               shape="equation"),
         claim={"kind": "equation", "payload": "x**2 + y**2 = x/x"}, right=False,
         truth="x^2+y^2=1; claimed curve misses (0,+-1)"),
    dict(label="E04 evaluate a given a + b = 10 (underdetermined), claim 10 - b",
         ir=ir("evaluate", {"expr": "a"}, AB, ["a + b = 10"]),
         claim={"kind": "value", "payload": "10 - b"}, right=False, truth="not determined (claim restates the given)"),
    dict(label="E05 derivative of x^3 at 1/2, claim 3/4 (right, typed point)",
         ir=ir("derivative", {"f": "x**3", "var": "x", "at": "1/2"}, X), claim={"kind": "value", "payload": "3/4"},
         right=True, truth="3/4"),
    dict(label="E06 derivative of x^3 at -2, claim 12 (right, typed negative point)",
         ir=ir("derivative", {"f": "x**3", "var": "x", "at": "-2"}, X), claim={"kind": "value", "payload": "12"},
         right=True, truth="12"),
    dict(label="E07 derivative of x^3 at -2, claim -12 (wrong)",
         ir=ir("derivative", {"f": "x**3", "var": "x", "at": "-2"}, X), claim={"kind": "value", "payload": "-12"},
         right=False, truth="12"),
    dict(label="E08 simplify tan(x)*cos(x), claim sin(x) (right)",
         ir=ir("simplify_expression", {"expr": "tan(x)*cos(x)"}, X, shape="expression"),
         claim={"kind": "expression", "payload": "sin(x)"}, right=True, truth="sin x (cos x != 0)"),
    dict(label="E09 simplify log(x**2), claim 2*log(x)",
         ir=ir("simplify_expression", {"expr": "log(x**2)"}, X, shape="expression"),
         claim={"kind": "expression", "payload": "2*log(x)"}, right=False, truth="2 log|x|"),
    dict(label="E10 simplify x, claim sqrt(x)**2",
         ir=ir("simplify_expression", {"expr": "x"}, X, shape="expression"),
         claim={"kind": "expression", "payload": "sqrt(x)**2"}, right=False, truth="x (claim undefined for x<0)"),
]
CASES += [
    dict(label="E11 evaluate Mod(7, 2) closed (ℝ), claim 0",
         ir=ir("evaluate", {"expr": "Mod(7, 2)"}), claim={"kind": "value", "payload": "0"}, right=False, truth="1"),
    dict(label="E12 evaluate Mod(7, 2) closed (ℝ), claim 1 (right)",
         ir=ir("evaluate", {"expr": "Mod(7, 2)"}), claim={"kind": "value", "payload": "1"}, right=True, truth="1"),
    dict(label="E13 sum_{k=1}^{4} Mod(k, 2), claim 0",
         ir=ir("series_sum", {"term": "Mod(k, 2)", "var": "k", "lo": "1", "hi": "4"}, [{"name": "k", "domain": "integer"}]),
         claim={"kind": "value", "payload": "0"}, right=False, truth="2"),
    dict(label="E14 evaluate Mod(x, 3) given x = 7 (real x), claim 0",
         ir=ir("evaluate", {"expr": "Mod(x, 3)"}, X, ["x = 7"]), claim={"kind": "value", "payload": "0"},
         right=False, truth="1"),
    dict(label="E15 simplify Mod(x, 2), claim 0",
         ir=ir("simplify_expression", {"expr": "Mod(x, 2)"}, X, shape="expression"),
         claim={"kind": "expression", "payload": "0"}, right=False, truth="Mod(x,2) is not identically 0"),
    dict(label="E16 evaluate Mod(17, 5) + 1 closed (ℝ), claim 1",
         ir=ir("evaluate", {"expr": "Mod(17, 5) + 1"}), claim={"kind": "value", "payload": "1"}, right=False, truth="3"),
]
