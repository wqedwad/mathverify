"""Deterministic expression parsing.

Two syntaxes are accepted:
  * canonical sympy-like text  ("3*x + 2*y = 12", "sqrt(x+4) = x - 2", "Interval.open(-2, 7)")
  * LaTeX                      ("\\frac{\\pi}{6}", "x^{2}-5x")  via latex2sympy2_extended
Relations are split at the top level (=, ==, !=, <=, >=, <, >) and rebuilt with
sympy relational classes, because `parse_expr("a == b")` would evaluate to a bool.

Security: `parse_expr` uses eval. Every identifier is whitelisted before eval, and
the caller is expected to run parsing inside the sandbox worker for untrusted text.
"""
from __future__ import annotations

import ast
import math
import re
from typing import Any

import sympy as sp
from sympy import (S, Symbol, Rational, Integer, Interval, FiniteSet, Union, Intersection,
                   Complement, EmptySet, Eq, Ne, Lt, Le, Gt, Ge, And, Or, Not, pi, E, I, oo, zoo, nan)
from sympy.parsing.sympy_parser import (parse_expr, standard_transformations, convert_xor,
                                        stringify_expr)

__all__ = ["ParseError", "UndeclaredSymbolError", "ClaimNotAValue", "COMPUTING_OPERATORS",
           "claim_namespace", "check_claim_is_value", "build_namespace", "parse_expr_str", "parse_relation", "parse_answer",
           "parse_domain", "parse_set_str", "is_latex", "preclean", "parse_as_written"]


class ParseError(ValueError):
    pass


class UndeclaredSymbolError(ParseError):
    """The text is well-formed mathematics that names something the problem never declared —
    typically a solver's own substitution (`u = sqrt(x+4)`).

    Kept apart from a plain syntax error on purpose. A step the verifier cannot read because
    of an undeclared symbol is legitimately skipped without penalty (§3 rule: the refuter only
    refutes). A step that is simply malformed is a different thing: the solution does not meet
    the structured contract, and accepting it would let an attacker cancel a refutation by
    corrupting the claim (measured: appending `}` to a refuted step turned INCORRECT into
    CORRECT on 4 items)."""


# ----------------------------------------------------------------------------
# namespace / assumptions
# ----------------------------------------------------------------------------
DOMAIN_ASSUMPTIONS: dict[str, dict[str, bool]] = {
    "real": {"real": True},
    "positive_real": {"real": True, "positive": True},
    "nonneg_real": {"real": True, "nonnegative": True},
    "integer": {"integer": True},
    "positive_integer": {"integer": True, "positive": True},
    "nonneg_integer": {"integer": True, "nonnegative": True},
    "natural": {"integer": True, "positive": True},
    "rational": {"rational": True},
    "complex": {},
}


def _deg(v):
    # exact: nsimplify(30.0000001) is 30, i.e. it would rewrite the angle that was written
    v = sp.sympify(v)
    if v.has(sp.Float):
        v = v.xreplace({f: sp.Rational(str(f)) for f in v.atoms(sp.Float)})
    return v * pi / 180


def _perm(n_, k_):
    return sp.factorial(n_) / sp.factorial(n_ - k_)


def _dist(x1, y1, x2, y2):
    return sp.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def _slope(x1, y1, x2, y2):
    return (y2 - y1) / (x2 - x1)


def _tri_area(x1, y1, x2, y2, x3, y3):
    return sp.Abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2


def _dot(x1, y1, x2, y2):
    return x1 * x2 + y1 * y2


def _point_line_dist(x0, y0, a, b, c):
    """distance from (x0,y0) to the line a*x + b*y + c = 0"""
    return sp.Abs(a * x0 + b * y0 + c) / sp.sqrt(a ** 2 + b ** 2)


# SymPy's `gcd`/`lcm` are the POLYNOMIAL gcd/lcm: with a symbol, `gcd(n, 4)` is 1 and `lcm(n, 2)` is
# 2*n, so for "n = 12, gcd(n, 4) = ?" the answer 1 was certified and 4 refuted (V14, 29 Sep 2026).
# Here they are the gcd/lcm of numbers, left unevaluated until every argument is one. Numbers keep
# SymPy's reading: integers exactly, fractions by the school rule gcd(a/b, c/d) = gcd(a, c)/lcm(b, d).
# The class names are `gcd`/`lcm` on purpose: printed, the expression reads back the same, and the
# Lean printer and the domain rules recognise the operation by that name.
def _number_args(cls, args) -> bool:
    if len(args) < 2:
        raise TypeError(f"{cls.__name__} takes at least two arguments")
    return all(isinstance(a, sp.Rational) for a in args)


def _canonical_order(cls, args):
    """gcd and lcm are symmetric: the arguments in SymPy's canonical order, so gcd(4, n) is gcd(n, 4)
    (the two were not recognised as equal; audit of 29 Sep 2026)."""
    ordered = tuple(sorted(args, key=sp.default_sort_key))
    return cls(*ordered) if ordered != tuple(args) else None


def _numeric_integer_op(op):
    """The numeric value (lambdify, evalf) of gcd/lcm: exact at integer points, none elsewhere. The
    random-point check could not evaluate the class at all and read that as "defined on one side
    only": gcd(n, n + 1) = 1 was refuted at n = 109 (audit of 29 Sep 2026)."""
    def value(*args):
        import mpmath
        ints = []
        for a in args:
            v = mpmath.mpf(a)
            if not mpmath.isint(v):
                raise ValueError("gcd/lcm of a number that is not an integer has no numeric value here")
            ints.append(int(v))
        out = ints[0]
        for i in ints[1:]:
            out = op(out, i)
        return mpmath.mpf(abs(out))
    return staticmethod(value)


class gcd(sp.Function):  # noqa: N801 - the name is the notation
    _imp_ = _numeric_integer_op(math.gcd)

    @classmethod
    def eval(cls, *args):
        if _number_args(cls, args):
            out = args[0]
            for a in args[1:]:
                out = sp.gcd(out, a)
            return out
        return _canonical_order(cls, args)

    def _eval_is_integer(self):
        return True if all(a.is_integer for a in self.args) else None

    def _eval_is_nonnegative(self):
        return True if all(a.is_integer for a in self.args) else None


class lcm(sp.Function):  # noqa: N801 - the name is the notation
    _imp_ = _numeric_integer_op(math.lcm)

    @classmethod
    def eval(cls, *args):
        if _number_args(cls, args):
            out = args[0]
            for a in args[1:]:
                out = sp.lcm(out, a)
            return out
        return _canonical_order(cls, args)

    def _eval_is_integer(self):
        return True if all(a.is_integer for a in self.args) else None

    def _eval_is_nonnegative(self):
        return True if all(a.is_integer for a in self.args) else None


def _integer_op(cls):
    """The callable the namespace gives for gcd/lcm: SymPy's `gcd([84, 120])` list form stays
    readable (the class itself takes the numbers as arguments)."""
    def call(*args):
        if len(args) == 1 and isinstance(args[0], (list, tuple, sp.Tuple)):
            args = tuple(args[0])
        return cls(*args)
    call.__name__ = cls.__name__
    return call


def _at(e, v, val):
    """e at v = val. A derivative at a corner is no derivative: diff(Abs(x), x) is sign(x), and
    sign(0) = 0 certified "the derivative of |x| at 0 is 0" (audit of 29 Sep 2026). A sign, Heaviside
    or DiracDelta whose argument vanishes at the point is refused, not read."""
    e = sp.sympify(e)
    for n in e.atoms(sp.sign, sp.Heaviside, sp.DiracDelta):
        if n.args[0].subs(v, val).is_zero:
            raise ParseError(f"at({e}, {v}, {val}): {n} is taken where its argument is 0")
    return e.subs(v, val)


def _two_sided(p) -> str:
    return "-" if p == oo else "+" if p == -oo else "+-"


def _Limit(e, v, p, d=None):  # noqa: N802 - the name is the notation
    """A limit written without a direction is two-sided (SOLVER_FORMAT, E6), as in compute steps.
    SymPy's default is the right side: Limit(Abs(x)/x, x, 0) was 1 and certified (audit of
    29 Sep 2026)."""
    return sp.Limit(e, v, p, d if d is not None else _two_sided(p))


def _limit(e, v, p, d=None):
    """`limit` computes, unless the limit is closed: then it stays the form, and a value is taken
    only when numbers confirm SymPy's (equiv.forms). With n an integer SymPy's limit of n*tan(pi/n)
    at oo is 0 (the limit is pi), and the parse certified 0 (audit of 29 Sep 2026)."""
    form = _Limit(e, v, p, d)
    if isinstance(form, sp.Limit) and not form.free_symbols:
        return form
    return sp.limit(e, v, p, d if d is not None else _two_sided(p))


def _integrate(*args, **kwargs):
    """`integrate` computes, unless the integral is definite in every variable and closed: then it
    stays the form, as `Integral` does, and its value is confirmed by numbers (equiv.forms). SymPy
    integrates |cos x| over [-1, 1] to 0 (the value is 2 sin 1), and the parse certified 0 (audit
    of 29 Sep 2026). An antiderivative or an integral with a parameter is computed as before."""
    form = sp.Integral(*args, **kwargs)
    if isinstance(form, sp.Integral) and not form.free_symbols and form.limits \
            and all(len(lim) == 3 for lim in form.limits):
        return form
    return sp.integrate(*args, **kwargs)


_integrate.binds_range = True  # type: ignore[attr-defined]


class arccot(sp.Function):  # noqa: N801 - the name is the notation
    """arccot with values in (0, pi), the convention of the Turkish curriculum (AYT). SymPy's `acot`
    takes values in (-pi/2, pi/2]: acot(-1) = -pi/4 where AYT reads 3*pi/4, so the right answer was
    refuted and -pi/4 certified (V14, 29 Sep 2026). Evaluated, it is pi/2 - atan(x), that function on
    all of R. Read as written (evaluation off) it stays one node: pi/2 - atan(x) built unevaluated is
    a nest of Adds that SymPy's sin misreads as a multiple of pi, so 1/sin(arccot(x) + arccot(2)) was
    "defined nowhere" and the empty domain certified (audit of 29 Sep 2026)."""
    nargs = 1

    @classmethod
    def eval(cls, x):
        return pi / 2 - sp.atan(x)

    def _eval_evalf(self, prec):
        return (pi / 2 - sp.atan(self.args[0]))._eval_evalf(prec)

    def _eval_rewrite_as_atan(self, x, **kwargs):
        return pi / 2 - sp.atan(x)

    def fdiff(self, argindex=1):
        return -1 / (1 + self.args[0] ** 2)

    def _eval_is_extended_real(self):
        return self.args[0].is_extended_real

    def _eval_is_positive(self):
        return True if self.args[0].is_extended_real else None


_SAFE_NAMES: dict[str, Any] = {
    # constants
    "pi": pi, "E": E, "e": E, "I": I, "i": I, "oo": oo, "inf": oo, "zoo": zoo, "nan": nan,
    # elementary
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "acot": arccot, "atan2": sp.atan2,
    "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan, "arccot": arccot,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "exp": sp.exp, "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt, "cbrt": sp.cbrt, "root": sp.root,
    "Abs": sp.Abs, "abs": sp.Abs, "floor": sp.floor, "ceiling": sp.ceiling, "ceil": sp.ceiling,
    "frac": sp.frac, "sign": sp.sign, "Mod": sp.Mod, "mod": sp.Mod,
    "gcd": _integer_op(gcd), "lcm": _integer_op(lcm), "igcd": sp.igcd, "ilcm": sp.ilcm,
    "factorial": sp.factorial, "binomial": sp.binomial, "C": sp.binomial, "comb": sp.binomial,
    "P": _perm, "perm": _perm, "deg": _deg,
    "dist": _dist, "slope": _slope, "tri_area": _tri_area, "dot": _dot, "point_line_dist": _point_line_dist,
    "at": _at,                                               # at(diff(f(x), x), x, 1)
    "eigmax": lambda m: sp.Max(*[k for k in sp.Matrix(m).eigenvals() if k.is_real]),
    "eigmin": lambda m: sp.Min(*[k for k in sp.Matrix(m).eigenvals() if k.is_real]),
    "trace": lambda m: sp.Matrix(m).trace(), "rank": lambda m: sp.Matrix(m).rank(),
    "Max": sp.Max, "Min": sp.Min, "max": sp.Max, "min": sp.Min,
    "re": sp.re, "im": sp.im, "conjugate": sp.conjugate, "arg": sp.arg,
    # calculus (unevaluated forms allowed in step claims)
    "Sum": sp.Sum, "Product": sp.Product, "Integral": sp.Integral, "Derivative": sp.Derivative,
    "Limit": _Limit, "diff": sp.diff, "integrate": _integrate, "limit": _limit,
    # numbers
    "Rational": Rational, "Integer": Integer, "Float": sp.Float, "S": S, "nsimplify": sp.nsimplify,
    # relations / logic
    "Eq": Eq, "Ne": Ne, "Lt": Lt, "Le": Le, "Gt": Gt, "Ge": Ge, "And": And, "Or": Or, "Not": Not,
    "Piecewise": sp.Piecewise,
    # sets
    "Interval": Interval, "FiniteSet": FiniteSet, "Union": Union, "Intersection": Intersection,
    "Complement": Complement, "EmptySet": EmptySet, "Reals": S.Reals, "Integers": S.Integers,
    "Naturals": S.Naturals, "Naturals0": S.Naturals0, "Complexes": S.Complexes,
    "Range": sp.Range, "ImageSet": sp.ImageSet, "Lambda": sp.Lambda, "ConditionSet": sp.ConditionSet,
    # linear algebra
    "Matrix": sp.Matrix, "det": lambda m: sp.Matrix(m).det(), "eye": sp.eye, "zeros": sp.zeros,
    "Transpose": sp.Transpose,
    # polynomials / algebra helpers (pure, no solving)
    "expand": sp.expand, "factor": sp.factor, "simplify": sp.simplify, "cancel": sp.cancel,
    "together": sp.together, "apart": sp.apart, "Poly": sp.Poly, "degree": sp.degree,
    "Symbol": Symbol, "symbols": sp.symbols,
}

# ----------------------------------------------------------------------------
# claims are values, not computations
# ----------------------------------------------------------------------------
# Operators that COMPUTE an answer. They belong in the statement of a problem ("find the
# integral of …"), never in a claimed answer: a claim written as `integrate(log(x), x)` or
# `limit(sin(x)/x, x, 0)` asks the verifier to PRODUCE the answer, which is the one thing this
# system must not do ("karar üretilerek değil, kanıtlanarak verilir"). Measured before this
# existed: 7 of 7 such claims — including `f(g(2))` for "evaluate f(g(2))" and
# `nsimplify(500000003/3000000000)` for a probability of 1/6 — were certified CORRECT.
# The problem's own functions (`f`, `g`) are excluded for the same reason: `f(g(2))` restates
# the question. Closed forms such as `binomial(6, 3)` or `factorial(5)` stay allowed.
COMPUTING_OPERATORS = frozenset({
    "integrate", "Integral", "diff", "Derivative", "limit", "Limit", "Sum", "Product",
    "simplify", "nsimplify", "expand", "factor", "cancel", "together", "apart", "Poly",
    "at", "Symbol", "symbols", "det", "trace", "rank", "eigmax", "eigmin",
    "dist", "slope", "tri_area", "dot", "point_line_dist",
})
# `\b` does not end `\sum_{k=1}` (the underscore is a word character): subscripted binders passed
_LATEX_COMPUTING = re.compile(r"\\(?:int|iint|oint|lim|sum|prod)(?![A-Za-z])|\\frac\s*\{\s*d\s*\}|\\frac\s*\{\s*\\partial")
_CALL_RE = re.compile(r"(?<![\w.])([A-Za-z_]\w*)\s*\(")


class ClaimNotAValue(ParseError):
    """A claimed answer that is a computation or a restatement of the question, not a value."""


def claim_namespace(ns: dict[str, Any], function_names=()) -> dict[str, Any]:
    """The namespace a CLAIMED answer is parsed in: the problem's namespace without the
    operators that would compute the answer and without the problem's own functions."""
    banned = COMPUTING_OPERATORS | set(function_names)
    return {k: v for k, v in ns.items() if k not in banned}


def check_claim_is_value(text: Any, function_names=()) -> None:
    """Raise ClaimNotAValue when a payload asks for a computation instead of stating a value."""
    if isinstance(text, (list, tuple)):
        for t in text:                    # a set's elements are claims too
            check_claim_is_value(t, function_names)
        return
    if text is None or not isinstance(text, str):
        return
    banned = COMPUTING_OPERATORS | set(function_names)
    for m in _CALL_RE.finditer(text):
        if m.group(1) in banned:
            raise ClaimNotAValue(f"claimed answer {text!r} is a computation ({m.group(1)}(…)), "
                                 "not a value: the verifier checks answers, it does not produce them")
    if _LATEX_COMPUTING.search(text):
        raise ClaimNotAValue(f"claimed answer {text!r} is an unevaluated integral/limit/sum/derivative")


_ALLOWED_DOTTED = {
    "Interval.open", "Interval.Lopen", "Interval.Ropen", "S.Reals", "S.Integers", "S.Naturals",
    "S.Naturals0", "S.EmptySet", "S.Complexes", "S.Half", "S.Zero", "S.One", "S.Infinity",
    "S.NegativeInfinity", "S.UniversalSet",
}

_IDENT_RE = re.compile(r"(?<![\w.])[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*")  # skips the e in 1e3
_FORBIDDEN_SUBSTR = ("__", "import", "lambda", "exec", "eval", "getattr", "setattr",
                     "globals", "locals", "compile", "input", "os.", "sys.", "subprocess")
# `open(` used to be in the substring list above, which also matched `Interval.open(1, oo)` —
# a form this module explicitly allows in `_ALLOWED_DOTTED` and `docs/SOLVER_FORMAT.md`
# documents. The notation was therefore unusable, silently, since Phase 1. Match only a BARE
# call: an attribute access is not the builtin.
_FORBIDDEN_CALL_RE = re.compile(r"(?<![\w.])open\s*\(")


def build_namespace(ir=None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Symbols carry assumptions from the IR var domains; functions become callables."""
    ns: dict[str, Any] = dict(_SAFE_NAMES)
    if ir is not None:
        for v in ir.vars:
            ns[v.name] = Symbol(v.name, **DOMAIN_ASSUMPTIONS.get(v.domain, {"real": True}))
        # function params are free real symbols
        for f in ir.functions:
            for p in f.params:
                ns.setdefault(p, Symbol(p, real=True))
            for a in f.args:
                ns.setdefault(a, Symbol(a, real=True))
        for f in ir.functions:
            ns[f.name] = _make_function(f, ns)
    if extra:
        ns.update(extra)
    return ns


def _make_function(fdef, ns):
    # A formal argument is the function's own real variable. Taken from the namespace, it carried
    # the domain of a problem variable with the same name: with x declared positive the body
    # sqrt(x**2) + x was folded to 2*x, so f(-1) was -2 and the sum of f(k) over -2..2 was 0 (it is
    # 6; audit of 29 Sep 2026). A call substitutes its argument, whose own assumptions apply then.
    body_ns = dict(ns)
    body_ns.update({a: Symbol(a, real=True) for a in fdef.args})
    argsyms = [body_ns[a] for a in fdef.args]
    body = parse_expr_str(fdef.expr, body_ns)

    def _f(*args):
        if len(args) != len(argsyms):
            raise ParseError(f"function {fdef.name} expects {len(argsyms)} args, got {len(args)}")
        return body.subs(dict(zip(argsyms, args)), simultaneous=True)

    _f.__name__ = fdef.name
    _f.body = body            # type: ignore[attr-defined]
    _f.argsyms = argsyms      # type: ignore[attr-defined]
    return _f


# ----------------------------------------------------------------------------
# pre-cleaning (unicode math, degrees, percents)
# ----------------------------------------------------------------------------
_UNICODE_MAP = {
    "π": "pi", "∞": "oo", "·": "*", "×": "*", "÷": "/", "−": "-", "–": "-", "—": "-",
    "≤": "<=", "≥": ">=", "≠": "!=", "√": "sqrt", "∅": "EmptySet", "∪": " U ", "∩": " N ",
    "²": "**2", "³": "**3", "⁴": "**4", "½": "(1/2)", "¼": "(1/4)", "¾": "(3/4)", "⅓": "(1/3)",
    "ℝ": "Reals", "ℤ": "Integers", "ℕ": "Naturals", "∈": " in ",
}
# `5π/6` is how a free-text solution writes 5*pi/6, but the unicode map alone turns it into
# `5pi/6`, which is a syntax error — and implicit multiplication is deliberately NOT enabled
# globally (it would silently read `zzz` as `z*z*z`). So the product is made explicit only
# where a digit or a closing bracket meets a unicode VALUE symbol, which is never anything but
# a product. Measured: 4 of 5 recovered trig answer sets were unparseable for exactly this.
_UNI_VALUE_RE = re.compile(r"([0-9)\]])\s*([π∞√ℝℤℕ∅])")
_DEG_NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:°|\bderece\b|\bdeg\b)")
_DEG_PAREN_RE = re.compile(r"\(([^()]*)\)\s*°")
_PCT_RE = re.compile(r"%\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*%")
_SQRT_BARE_RE = re.compile(r"sqrt\s*(\d+(?:\.\d+)?|[A-Za-z_]\w*)(?![\w(])")


def _strip_invisible(s: str) -> str:
    """Remove format/invisible code points (Cf: zero-width space/joiner, BOM, soft hyphen, …).
    Measured: Python's tokenizer accepts U+200B inside a NAME, so 'E\\u200b' silently became
    an unknown Symbol instead of Euler's number — an invisible-character injection vector."""
    import unicodedata
    # no NFKC here: it would turn '²' into '2' and '½' into '1⁄2' before _UNICODE_MAP runs
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cf")


_PRESENTATION = re.compile(r"^\s*(?:\$\$|\$|\\\(|\\\[)?\s*\\(?:boxed|text|mathrm|displaystyle)\s*\{(.*)\}\s*"
                           r"(?:\$\$|\$|\\\)|\\\])?\s*$", re.DOTALL)
_MATH_DELIM = re.compile(r"^\s*(?:\$\$(.*)\$\$|\$(.*)\$|\\\((.*)\\\)|\\\[(.*)\\\])\s*$", re.DOTALL)


def strip_presentation(s: str) -> str:
    """Remove display-only wrappers (\\boxed{}, \\text{}, $...$). They carry no mathematics, and
    leaving them in makes an otherwise valid claim unparseable or, worse, parseable as something
    else (measured: `\\boxed{exp(1)}` flipped a verdict)."""
    prev = None
    while prev != s:
        prev = s
        m = _PRESENTATION.match(s)
        if m:
            s = m.group(1).strip()
            continue
        m = _MATH_DELIM.match(s)
        if m:
            s = next(g for g in m.groups() if g is not None).strip()
    return s


def preclean(s: str) -> str:
    """Canonicalise unicode/degree/percent notation. Idempotent."""
    s = strip_presentation(_strip_invisible(s).strip()).strip()
    s = _UNI_VALUE_RE.sub(r"\1*\2", s)
    for k, v in _UNICODE_MAP.items():
        s = s.replace(k, v)
    s = _DEG_PAREN_RE.sub(r"((\1)*pi/180)", s)
    s = _DEG_NUM_RE.sub(r"((\1)*pi/180)", s)
    s = _PCT_RE.sub(lambda m: f"(({m.group(1) or m.group(2)})/100)", s)
    s = _SQRT_BARE_RE.sub(r"sqrt(\1)", s)           # "sqrt 3" -> sqrt(3)
    s = re.sub(r"\bln\s*\(", "log(", s)
    s = s.replace("^", "**")
    return s


def is_latex(s: str) -> bool:
    return "\\" in s or bool(re.search(r"\^\{|_\{|\\frac|\\sqrt|\\pi|\\infty|\\cdot", s))


# ----------------------------------------------------------------------------
# core parsing
# ----------------------------------------------------------------------------
from sympy.parsing.sympy_parser import rationalize as _rationalize  # noqa: E402

_TRANSFORMS = standard_transformations + (convert_xor, _rationalize)   # 0.5 -> 1/2 exactly
_TRANSFORMS_FLOAT = standard_transformations + (convert_xor,)


_PARSER_KEYWORDS = {"in", "U", "N", "and", "or", "not"}

# What the text becomes after SymPy's token transformations is plain Python that `eval` runs. Only
# arithmetic, calls, literals and containers mean mathematics there; everything else has PYTHON
# semantics that silently replace the mathematics (audit of 25 Sep 2026): `and`/`or` return one of
# their operands by truthiness, so the step claim `a = 20 and a = 16` became `a = 16` and the false
# `a = 20` was never checked, and the payload `0 or 7/2` was certified as 7/2 (113 of 141 correct
# evalset answers wrapped that way were CORRECT). `==`, `in` and `is` give Python booleans, a
# conditional picks a branch, a comprehension or walrus runs code. They are rejected, not guessed.
_ALLOWED_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load,
                  ast.Constant, ast.Tuple, ast.List, ast.Set, ast.Dict, ast.Attribute,
                  ast.keyword, ast.Subscript, ast.Slice, ast.Compare,
                  ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
                  ast.UAdd, ast.USub, ast.Lt, ast.LtE, ast.Gt, ast.GtE)


# SymPy's own transformations write these calls with a string argument (Symbol('x'),
# Rational('3.5')); any other string literal is text that some callee may hand to `sympify`, which
# evaluates it with Python's builtins in reach.
_STR_ARG_CALLS = frozenset({"Symbol", "Function", "Rational", "Float", "Integer"})
_STR_LITERAL_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z_0-9]*|[0-9.]+(?:[eE][-+]?[0-9]+)?)$")
# the side of a one-sided limit, `Limit(f, x, 0, '+')`: a sign, never text a callee could run
_DIRECTION_LITERALS = frozenset({"+", "-", "+-", "-+"})


def _check_code(code: str, raw: str, names) -> None:
    """Raise ParseError unless the transformed code is plain arithmetic (see _ALLOWED_NODES) over
    the given names only: `eval` adds Python's builtins (`__import__`, `getattr`, `exit`...) to
    any namespace that lacks them, so a name outside `names` is never evaluated."""
    try:
        tree = ast.parse(code, mode="eval")
    except SyntaxError:
        return                                   # parse_expr reports the syntax error itself
    str_ok: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in _STR_ARG_CALLS and len(node.args) == 1:
            str_ok.add(id(node.args[0]))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in names:
            raise ParseError(f"{raw!r} names {node.id!r}, which is not in the namespace: not read")
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)) \
                and node.value not in _DIRECTION_LITERALS and not (
                id(node) in str_ok and isinstance(node.value, str) and _STR_LITERAL_RE.match(node.value)):
            raise ParseError(f"{raw!r} contains a string literal: not read")
        if not isinstance(node, _ALLOWED_NODES):
            raise ParseError(f"{raw!r} uses Python syntax that is not mathematics here "
                             f"({type(node).__name__}): not read")
        if isinstance(node, ast.Compare) and len(node.ops) != 1:
            raise ParseError(f"{raw!r} chains comparisons inside an expression: not read")
        if isinstance(node, ast.Attribute) and not (
                isinstance(node.value, ast.Name) and f"{node.value.id}.{node.attr}" in _ALLOWED_DOTTED):
            raise ParseError(f"{raw!r} accesses an attribute: not read")
        if isinstance(node, ast.Subscript) and not isinstance(node.value, ast.Name):
            # `a[n]` names a term; `[3][0]` or `(1, 2)[1]` computes the value the claim should state
            raise ParseError(f"{raw!r} indexes a computed value: not read")


def sympify_nontext(v):
    """`sympify` for a value that is NOT text: a number or an object SymPy already built. Anything
    else is refused. `strict=True` is not enough: SymPy converts a dict (and a tuple) through
    `Tuple`, which sympifies the strings inside WITHOUT strict, i.e. evaluates them with Python's
    builtins in reach — `{"k": "__import__(...)"}` as a problem parameter ran code (audit of
    25 Sep 2026)."""
    if isinstance(v, bool) or not isinstance(v, (int, float, sp.Basic)):
        raise ParseError(f"not a number or an expression: {type(v).__name__}")
    return sp.sympify(v, strict=True)


# Binders whose TEXT gives the range of their variable: the index of a Sum or a Product runs over the
# integers between its limits, the variable of a definite integral over the interval between them.
# A declaration of the same name in the IR describes the problem's free variable, not this dummy:
# with k declared positive, `Sum(Abs(k), (k, -2, 2))` was read as Sum(k, ...) = 0 and `0**k` became
# 0 before the sum was even built, so a wrong answer was certified (V14, 29 Sep 2026). The dummy is
# read without assumptions, as the LaTeX branch (latex2sympy's own symbol) and an undeclared index
# (`steps.deterministic._with_bound_dummies`) already read it; SymPy sums and integrates such a
# symbol like the declared one (measured on the common sums and integrals), and an integer
# assumption would be wrong for limits that are not integers (`Sum(sin(pi*k), (k, 1/2, 5/2))`).
# A Limit keeps the declared symbol: there the declaration IS the range (an integer n makes
# n → oo a limit of a sequence: sin(pi*n) → 0, which as a function has no limit).
_RANGE_BINDERS = ("Sum", "Product", "Integral", "integrate")


def _binds_range(obj) -> bool:
    """SymPy's range binders, or a callable that says it builds one: the step namespace keeps an
    Integral unevaluated through its own function, and `compute` claims were not rebound (audit of
    29 Sep 2026: the wrong step "Integral(Abs(x), (x, -1, 1)) = 0" stayed verified)."""
    return any(obj is b for b in (sp.Sum, sp.Product, sp.Integral, sp.integrate)) \
        or getattr(obj, "binds_range", False) is True


def _limit_var(lim) -> str | None:
    """The name a limit binds: the k of (k, a, b), [k, a, b], (k, a), (k,) or a bare k."""
    if isinstance(lim, ast.Name):
        return lim.id
    if isinstance(lim, (ast.Tuple, ast.List)) and lim.elts and isinstance(lim.elts[0], ast.Name):
        return lim.elts[0].id
    return None


def _rebind_range_dummies(code: str, local_dict: dict[str, Any], raw: str) -> tuple[str, dict[str, Any]] | None:
    """`code` with the variable of every range binder renamed, inside the binder only, to a fresh
    name for an assumption-free symbol of the same name; None when there is nothing to rename.

    Only a name the namespace reads as a symbol is rebound (`pi`, `E` or `oo` as an index is not
    mathematics and stays unreadable). A name bound twice, by two limits of one binder or by a binder
    inside another, is refused: `integrate(x**2, x, (x, 0, 1))` split x between the IR symbol and the
    dummy (x/3 was certified for 1/12), and SymPy flattens nested sums of one name and evaluates them
    wrongly (Σ_{k=1}^{2} Σ_{k=-1}^{1} (|k| + 1) = 10 came out 0). The walk is iterative and the names
    are replaced in the text, so a long sum of terms does not hit the recursion limit."""
    try:
        tree = ast.parse(code, mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None                               # parse_expr reports it
    nodes = list(ast.walk(tree))
    bindings: list[tuple[ast.Call, int, Any, str]] = []
    for node in nodes:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _RANGE_BINDERS
                and node.args and _binds_range(local_dict.get(node.func.id))):
            continue
        limits = node.args[1:]
        named = [_limit_var(lim) for lim in limits]
        for m, lim in enumerate(limits):
            v = named[m]
            if not (isinstance(lim, (ast.Tuple, ast.List)) and len(lim.elts) == 3 and v is not None
                    and isinstance(local_dict.get(v), Symbol)):
                continue
            if named.count(v) > 1:
                raise ParseError(f"{raw!r} binds {v!r} twice in one {node.func.id}: not read")
            bindings.append((node, m, lim, v))
    if not bindings:
        return None
    owner: dict[int, int] = {}                    # id(Name node) -> index of the binding it belongs to
    for bi, (call, m, lim, v) in enumerate(bindings):
        limits = call.args[1:]
        # the variable of limit m binds the body and the bounds of the limits listed before it
        # (SymPy: the first limit is the innermost), and itself
        roots = [call.args[0]] + [e for inner in limits[:m] if isinstance(inner, (ast.Tuple, ast.List))
                                  for e in inner.elts[1:]]
        mine = [sub for root in roots for sub in ast.walk(root) if isinstance(sub, ast.Name) and sub.id == v]
        for sub in mine + [lim.elts[0]]:
            if owner.get(id(sub), bi) != bi:
                raise ParseError(f"{raw!r} binds {v!r} inside a binder of the same name: not read")
            owner[id(sub)] = bi
    used = set(local_dict) | {n.id for n in nodes if isinstance(n, ast.Name)}
    fresh: list[str] = []
    for _, _, _, v in bindings:
        i = 0
        while f"_bound_{v}_{i}" in used:
            i += 1
        used.add(f"_bound_{v}_{i}")
        fresh.append(f"_bound_{v}_{i}")
    edits = sorted(((n.lineno, n.col_offset, n.end_col_offset, fresh[owner[id(n)]])
                    for n in nodes if isinstance(n, ast.Name) and id(n) in owner), reverse=True)
    lines = code.encode("utf-8").split(b"\n")
    for lineno, start, end, new in edits:          # offsets are UTF-8 byte offsets of the line
        line = lines[lineno - 1]
        lines[lineno - 1] = line[:start] + new.encode("ascii") + line[end:]
    return b"\n".join(lines).decode("utf-8"), {f: Symbol(v) for f, (_, _, _, v) in zip(fresh, bindings)}


def _integer_indices(expr):
    """The index of a Sum/Product whose limits are integers (or ±oo) runs over integers: the dummy
    becomes an integer symbol there. Without it SymPy no longer closed Σ cos(πk)/k² and the numeric
    fallback (Euler-Maclaurin) is wrong for oscillating terms, so -π²/12 was refuted (audit of
    29 Sep 2026). Limits that are not integers keep the assumption-free dummy (Σ_{k=1/2}^{5/2})."""
    if not isinstance(expr, sp.Basic) or not expr.has(sp.Sum, sp.Product):
        return expr

    def upgrade(n):
        reps = {}
        for lim in n.limits:
            if len(lim) != 3 or not isinstance(lim[0], Symbol) \
                    or lim[0].assumptions0 != Symbol(lim[0].name).assumptions0:
                continue
            if all(b.is_integer or b in (sp.oo, -sp.oo) for b in lim[1:]):
                reps[lim[0]] = Symbol(lim[0].name, integer=True)
        return n.xreplace(reps) if reps else n
    return expr.replace(lambda n: isinstance(n, (sp.Sum, sp.Product)), upgrade)


def _refuse_reversed_ranges(expr, raw: str) -> None:
    """A Sum or Product whose upper limit is below its lower limit minus one is not an empty sum in
    SymPy: Karr's convention makes Σ_{k=3}^{1} k = -2, which was certified (audit of 29 Sep 2026).
    The school reading (empty, or undefined) differs, so the text is not read. Nor is a binder whose
    variable is not a symbol (`Sum(k, (Symbol, 1, 3))` built one around the class itself)."""
    if not isinstance(expr, sp.Basic) or not expr.has(sp.Sum, sp.Product, sp.Integral):
        return
    for node in sp.preorder_traversal(expr):
        if isinstance(node, (sp.Sum, sp.Product, sp.Integral)):
            for lim in node.limits:
                if not isinstance(lim[0], Symbol):
                    raise ParseError(f"{raw!r} binds {lim[0]!r}, which is not a variable: not read")
                if isinstance(node, (sp.Sum, sp.Product)) and len(lim) == 3 \
                        and (lim[2] - lim[1] + 1).is_extended_negative is True:
                    raise ParseError(f"{raw!r} has a {type(node).__name__} over a reversed range: not read")
                span = lim[2] - lim[1] if len(lim) == 3 else None
                if isinstance(node, (sp.Sum, sp.Product)) and span is not None and span.is_number \
                        and span.is_finite and span.is_integer is False:
                    # Σ_{k=1}^{7/2} k is 63/8 in SymPy, 1 + 2 + 3 stepping from the lower limit
                    raise ParseError(f"{raw!r} has a {type(node).__name__} whose limits are not an "
                                     "integer apart: not read")


def guarded_parse_expr(s: str, *, local_dict: dict[str, Any], global_dict: dict[str, Any],
                       transformations, evaluate: bool = True, rebind: bool = True):
    """parse_expr, after checking that the code it is about to evaluate is plain arithmetic.
    `rebind=False` keeps the declared symbols inside the range binders (the reading of definedness,
    see `parse_as_written`)."""
    names = set(local_dict) | set(global_dict)
    code = stringify_expr(s, local_dict, global_dict, transformations)
    _check_code(code, s, names)
    rebound = _rebind_range_dummies(code, local_dict, s) \
        if rebind and any(b in code for b in _RANGE_BINDERS) else None
    if rebound is None:
        out = parse_expr(s, local_dict=local_dict, global_dict=global_dict,
                         transformations=transformations, evaluate=evaluate)
    else:
        code, dummies = rebound
        _check_code(code, s, names | set(dummies))
        # the code is already transformed: no transformation runs twice on it
        out = parse_expr(code, local_dict=dict(local_dict, **dummies), global_dict=global_dict,
                         transformations=(), evaluate=evaluate)
        if evaluate:
            out = _integer_indices(out)
        else:
            with sp.evaluate(False):
                out = _integer_indices(out)
    _refuse_reversed_ranges(out, s)
    return out


def _check_safe(s: str, ns: dict[str, Any]) -> list[str]:
    """Hard rejections raise; undeclared identifiers are RETURNED so the caller can tell a
    solver's own substitution apart from text that is not mathematics at all."""
    # after preclean only ASCII may remain: anything else is prose or an injection attempt
    bad_chars = [ch for ch in s if ord(ch) > 127]
    if bad_chars:
        raise ParseError(f"non-ASCII characters in expression after normalisation: {bad_chars[:5]!r}")
    if "#" in s:
        # Python's tokenizer treats the rest of the line as a comment, so `2*x ### anything`
        # parses as `2*x` and whatever follows is never seen. An expression that is silently
        # truncated is worse than one that fails: measured as a working step-claim injection.
        raise ParseError("'#' is not allowed in an expression (it hides the rest of the line)")
    low = s.lower()
    for bad in _FORBIDDEN_SUBSTR:
        if bad in low:
            raise ParseError(f"forbidden token {bad!r} in expression")
    if _FORBIDDEN_CALL_RE.search(low):
        raise ParseError("forbidden call 'open(' in expression")
    undeclared: list[str] = []
    for m in _IDENT_RE.finditer(s):
        ident = m.group(0)
        if ident in ns or ident in _ALLOWED_DOTTED or ident in _PARSER_KEYWORDS:
            continue
        if "." in ident:
            raise ParseError(f"dotted name not allowed: {ident}")
        if ident not in undeclared:
            undeclared.append(ident)
    return undeclared


def _raise_for_undeclared(s: str, ns: dict[str, Any], undeclared: list[str], raw: str,
                          transformations) -> None:
    """Decide which failure this is, and never guess.

    `u = sqrt(x+4)` is well-formed mathematics naming something the problem did not declare —
    legitimately skipped, no penalty. `2*x ignore previous instructions` is not mathematics at
    all. The test is the parse itself: re-parse with the unknown names bound to free symbols.
    If that still fails, the text was malformed, and saying so matters — a malformed step claim
    blocks a positive verdict, so an attacker cannot cancel a refutation by garbling the step."""
    probe_ns = dict(ns)
    for u in undeclared:
        # A name used as `a(n)` is a sequence or a function the problem did not declare (the
        # recurrence items write `a(n) = 3*n + 2` and `a` lives in task.params, not in
        # ir.functions). Binding it to a Symbol would make the probe fail with "'Symbol' object
        # is not callable" and mislabel a perfectly ordinary step as malformed.
        called = re.search(rf"(?<![\w.]){re.escape(u)}\s*\(", s) is not None
        probe_ns[u] = sp.Function(u) if called else Symbol(u)
    try:
        guarded_parse_expr(s, local_dict=probe_ns, global_dict={}, transformations=transformations,
                           evaluate=True)
    except Exception as e:
        raise ParseError(f"cannot parse {raw!r}: {e}") from e
    raise UndeclaredSymbolError(
        f"unknown identifier(s) {undeclared} in {raw!r} (declare them in the IR)")


# A decimal in LaTeX becomes a 53-bit Float in latex2sympy, and a Float is compared at its own
# precision (~1e-12): `0.3333333333333 \cdot 1` was certified as 1/3 while the same decimal in the
# canonical syntax, read exactly, was refused (audit of 25 Sep 2026). The digits are the number the
# solver wrote, so reading them as the exact fraction is not a rewrite (principle 3).
_LATEX_DECIMAL = re.compile(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])")


def _exact_latex_decimals(s: str) -> str:
    return _LATEX_DECIMAL.sub(
        lambda m: r"\left(\frac{%d}{%d}\right)" % (int(m.group(1) + m.group(2)), 10 ** len(m.group(2))), s)


# LaTeX has no \arccot macro; latex2sympy reads \arccot and \cot^{-1} but not the usual spellings
# (\text{arccot} became the product of a symbol "arccot" and the argument)
_LATEX_ARCCOT = re.compile(r"\\(?:operatorname\*?|mathrm|text|textrm)\s*\{\s*(?:arccot|acot|arcctg)\s*\}")
# latex2sympy computes \gcd and \operatorname{lcm} with SymPy's POLYNOMIAL gcd/lcm before anything
# else sees them (\gcd(n, 4) with n = 12 certified 1) and wraps the result in UnevaluatedExpr, which
# then kept a closed step "\gcd(84, 120) = 7" from evaluating (it was "verified"; audit of 29 Sep 2026).
# Written as \mathrm{gcd} they come back as an undefined function, which becomes the integer gcd here.
_LATEX_GCD = re.compile(r"\\(?:(gcd|lcm)(?![A-Za-z])|operatorname\s*\{\s*(gcd|lcm)\s*\})")
_LATEX_INTEGER_OPS = {"\\text{gcd}": "gcd", "\\text{lcm}": "lcm"}


def _latex_to_sympy(s: str, ns: dict[str, Any]):
    from latex2sympy2_extended import latex2sympy
    s = _LATEX_GCD.sub(lambda m: r"\mathrm{%s}" % (m.group(1) or m.group(2)), _LATEX_ARCCOT.sub(r"\\arccot ", s))
    expr = latex2sympy(_exact_latex_decimals(s))
    if isinstance(expr, sp.Basic):
        from sympy.core.function import AppliedUndef
        ops = {"gcd": gcd, "lcm": lcm}

        def convert(e):
            e = e.replace(lambda n: isinstance(n, AppliedUndef) and n.func.__name__ in _LATEX_INTEGER_OPS,
                          lambda n: ops[_LATEX_INTEGER_OPS[n.func.__name__]](*n.args))
            # the only other UnevaluatedExpr latex2sympy writes is the 1/100 of a percent
            e = e.replace(lambda n: isinstance(n, sp.UnevaluatedExpr), lambda n: n.args[0])
            return e.replace(sp.acot, arccot) if e.has(sp.acot) else e   # (0, pi), as in the canonical branch
        expr = _on_sides(expr, lambda e: _integer_indices(convert(e)))
        _refuse_reversed_ranges(expr, s)
    # rebind free symbols to the IR symbols (assumptions)
    reps = {}
    for fs in expr.free_symbols:
        if fs.name in ns and isinstance(ns[fs.name], Symbol):
            reps[fs] = ns[fs.name]
    if reps:
        expr = _on_sides(expr, lambda e: e.subs(reps, simultaneous=True))
    _check_symbols_declared(expr, ns, s)
    return expr


def _on_sides(expr, f):
    """`f` applied to the sides of a relation (or of an And/Or of relations), rebuilt WITHOUT
    evaluation: replacing inside a closed relation re-evaluated it, so the false LaTeX step
    "\\cot^{-1}(-1) = -\\frac{\\pi}{4}" collapsed to False and was skipped as not a relation, while
    the same step written canonically was refuted (audit of 29 Sep 2026)."""
    if isinstance(expr, sp.core.relational.Relational):
        return type(expr)(f(expr.lhs), f(expr.rhs), evaluate=False)
    if isinstance(expr, (And, Or)) and all(isinstance(a, (sp.core.relational.Relational, And, Or)) for a in expr.args):
        return type(expr)(*[_on_sides(a, f) for a in expr.args], evaluate=False)
    return f(expr)


def _check_symbols_declared(expr, ns: dict[str, Any], raw: str) -> None:
    """The canonical branch refuses an undeclared identifier; the LaTeX branch must too.

    `_check_safe` is a check on the TEXT and cannot run here, because latex2sympy does its own
    tokenisation — including implicit multiplication, which the canonical parser deliberately
    does not enable. Measured: `\\frac{zzz}{2}` silently became `z*z*z/2` with a symbol `z`
    that appears nowhere in the problem, while `zzz + 1` was rejected. A solver writing
    `\\frac{ab}{2}` for a single unknown `ab` would have had its claim quietly rewritten.
    So the same rule is enforced on the RESULT: every free symbol must be declared."""
    # a name the namespace gives to a function or a constant is no symbol either: \text{arccot}(-1)
    # was the symbol "arccot" times -1 (audit of 29 Sep 2026)
    undeclared = sorted({fs.name for fs in getattr(expr, "free_symbols", ())
                         if not isinstance(ns.get(fs.name), Symbol)}) if hasattr(expr, "free_symbols") else []
    if undeclared:
        raise UndeclaredSymbolError(f"LaTeX {raw!r} introduces undeclared symbol(s) {undeclared} "
                                    "(declare them in the IR; latex2sympy splits unknown names "
                                    "into implicit products)")


def parse_expr_str(s: str, ns: dict[str, Any] | None = None, *, rational: bool = True):
    """Parse a single expression (no top-level relation)."""
    if ns is None:
        ns = dict(_SAFE_NAMES)
    if not isinstance(s, str):
        try:
            return sympify_nontext(s)             # a container of strings is never evaluated
        except (sp.SympifyError, TypeError) as e:
            raise ParseError(f"not an expression: {type(s).__name__}") from e
    raw = s
    s = strip_presentation(_strip_invisible(s))
    if is_latex(s):
        try:
            return _latex_to_sympy(s, ns)
        except Exception as e:  # pragma: no cover - fall through to canonical
            raise ParseError(f"LaTeX parse failed for {raw!r}: {e}") from e
    s = preclean(s)
    transformations = _TRANSFORMS if rational else _TRANSFORMS_FLOAT
    undeclared = _check_safe(s, ns)
    if undeclared:
        _raise_for_undeclared(s, ns, undeclared, raw, transformations)
    try:
        return guarded_parse_expr(s, local_dict=ns, global_dict={},
                                  transformations=transformations, evaluate=True)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"cannot parse {raw!r}: {e}") from e


_REL_OPS = ["<=", ">=", "!=", "==", "=", "<", ">"]
_REL_CLASS = {"<=": Le, ">=": Ge, "!=": Ne, "==": Eq, "=": Eq, "<": Lt, ">": Gt}


def parse_as_written(s: str, ns: dict[str, Any] | None = None):
    """The sides of `s` EXACTLY AS WRITTEN, with SymPy's automatic simplification switched off,
    as a Tuple — for reading DEFINEDNESS only, never values. With evaluation on, `x/x` becomes 1,
    `sqrt(x)**2` becomes x and `x**2/x` becomes x before any condition can be read, so the points
    where the problem's own expression is undefined disappear (measured 23 Sep 2026: wrong answers
    to domain_of, solve_equation, solve_inequality and evaluate were certified CORRECT, and the
    right ones refuted). LaTeX is read by latex2sympy with evaluation off. Returns None for
    anything this cannot read faithfully (undeclared or forbidden names); the caller then adds no
    condition, which is the old behaviour."""
    if ns is None:
        ns = dict(_SAFE_NAMES)
    if not isinstance(s, str):
        return None
    s = strip_presentation(_strip_invisible(s))
    if is_latex(s):
        # LaTeX used to return None here, so `\frac{x}{x}` carried no condition at all and every
        # undefined point of a LaTeX-written problem was lost (audit of 25 Sep 2026). latex2sympy
        # keeps the written structure when SymPy's evaluation is off.
        try:
            with sp.evaluate(False):
                e = _latex_to_sympy(s, ns)
        except Exception:  # noqa: BLE001 - the normal parse reports errors; this only adds facts
            return None
        if isinstance(e, sp.core.relational.Relational):
            return sp.Tuple(e.lhs, e.rhs)
        if isinstance(e, sp.Basic) and not isinstance(e, sp.logic.boolalg.Boolean):
            return sp.Tuple(e)
        return None
    s = preclean(s)
    local = dict(ns, Add=sp.Add, Mul=sp.Mul, Pow=sp.Pow)
    out = []
    for _, chunk in _split_top_level(s):
        try:
            if _check_safe(chunk, ns):
                return None
            with sp.evaluate(False):
                # the declared symbols stay inside the binders here: the conditions of a sum's or an
                # integral's body are read as conditions on the variable of that name, which is what
                # a solver's steps about x in an integral over x are checked against (rebinding them
                # to the dummy left "x**2 + 1 = 0" unchecked and refuted "log(x**2) = 2*log(x)" on
                # [1, e]; audit of 29 Sep 2026)
                out.append(guarded_parse_expr(chunk, local_dict=local, global_dict={},
                                              transformations=_TRANSFORMS, evaluate=False, rebind=False))
        except Exception:  # noqa: BLE001 - the normal parse reports errors; this only adds facts
            return None
    return sp.Tuple(*out)


def _split_top_level(s: str) -> list[tuple[str, str]]:
    """Return [(op, chunk)...] splitting at top-level relational operators.
    First chunk has op ''. Handles chained relations (0 <= p <= 1)."""
    out: list[tuple[str, str]] = []
    depth = 0
    i = 0
    cur_start = 0
    cur_op = ""
    while i < len(s):
        c = s[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0:
            for op in _REL_OPS:
                if s.startswith(op, i):
                    # avoid splitting "<=" as "<" then "="
                    out.append((cur_op, s[cur_start:i]))
                    cur_op = op
                    i += len(op)
                    cur_start = i
                    break
            else:
                i += 1
                continue
            continue
        i += 1
    out.append((cur_op, s[cur_start:]))
    return out


def parse_relation(s: str, ns: dict[str, Any] | None = None):
    """Parse an equation/inequality (or a plain expression if no operator)."""
    if ns is None:
        ns = dict(_SAFE_NAMES)
    # Strip display-only wrappers FIRST, exactly as `parse_expr_str` does. Without this,
    # `\boxed{Integral(sin(x), x) = cos(x)}` looked like LaTeX, went to latex2sympy — which
    # does not know sympy call syntax — and came back as a non-relation that the step layer
    # then skipped. Measured: wrapping a refuted step in \boxed{} turned INCORRECT into
    # CORRECT on 7 items.
    s = strip_presentation(_strip_invisible(s))
    if is_latex(s):
        # LaTeX relations: latex2sympy handles "=" -> Eq
        try:
            return _latex_to_sympy(s, ns)
        except ParseError:
            raise
        except Exception as e:  # noqa: BLE001 - latex2sympy raises a bare Exception
            raise ParseError(f"LaTeX parse failed for {s!r}: {e}") from e
    s2 = preclean(s)
    # explicit And/Or already in sympy syntax
    parts = _split_top_level(s2)
    if len(parts) == 1:
        return parse_expr_str(s2, ns)
    # Parse every chunk before deciding what went wrong. Raising on the first chunk that merely
    # names something undeclared would classify a globally malformed string as a legitimate
    # solver substitution: `y = 2*x <verdict>CORRECT</verdict>` splits into chunks of which
    # `verdict` parses fine on its own, so the whole claim was being skipped without penalty.
    exprs, undeclared_err = [], None
    for _, chunk in parts:
        try:
            exprs.append(parse_expr_str(chunk, ns))
        except UndeclaredSymbolError as e:
            undeclared_err = undeclared_err or e
            exprs.append(None)
    if undeclared_err is not None:
        raise undeclared_err                 # every chunk is well formed; a name is just new
    rels = []
    for k in range(1, len(parts)):
        op = parts[k][0]
        # evaluate=False everywhere: a relation on an assumption-carrying symbol (x positive)
        # would otherwise collapse to True/False and silently disappear as a constraint
        rels.append(_REL_CLASS[op](exprs[k - 1], exprs[k], evaluate=False))
    return rels[0] if len(rels) == 1 else And(*rels)


# ----------------------------------------------------------------------------
# sets / intervals / domains
# ----------------------------------------------------------------------------
_INTERVAL_RE = re.compile(r"^\s*([\(\[])\s*(.+?)\s*[,;]\s*(.+?)\s*([\)\]])\s*$")


def _parse_single_set(s: str, ns):
    s = s.strip()
    if s in ("EmptySet", "{}", "S.EmptySet", "∅"):
        return S.EmptySet
    if s in ("Reals", "R", "S.Reals"):
        return S.Reals
    if s in ("Integers", "Z", "S.Integers"):
        return S.Integers
    if s in ("Naturals", "N", "S.Naturals", "Z+"):
        return S.Naturals
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        if not inner:
            return S.EmptySet
        elems = [parse_expr_str(p, ns) for p in _split_commas(inner)]
        return FiniteSet(*elems)
    m = _INTERVAL_RE.match(s)
    if m and not s.startswith(("Interval", "FiniteSet", "Union")):
        lo = parse_expr_str(m.group(2), ns)
        hi = parse_expr_str(m.group(3), ns)
        # A reversed interval "(5, 1)" is not notation for the empty set: SymPy's Interval(5, 1)
        # is EmptySet, so the right answer to "x² + 1 < 0" was certified from a claim that
        # names no interval at all (audit of 25 Sep 2026). A degenerate "(a, a)" is refused too.
        try:
            order = sp.sympify(hi - lo).is_positive if lo.is_real is not False and hi.is_real is not False else None
        except Exception:  # noqa: BLE001
            order = None
        if order is False and not (lo == hi and m.group(1) == "[" and m.group(4) == "]"):
            raise ParseError(f"interval {s!r} has its end before its start: not an interval")
        return Interval(lo, hi, left_open=(m.group(1) == "("), right_open=(m.group(4) == ")"))
    val = parse_expr_str(s, ns)
    if isinstance(val, sp.Set):
        return val
    return FiniteSet(val)


def _split_commas(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for c in s:
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += c
    if cur.strip():
        out.append(cur)
    return out


def parse_set_str(s: str, ns: dict[str, Any] | None = None) -> sp.Set:
    """Parse set notation: {a, b}, (a, b], [a,b) U (c, d), EmptySet, Reals, sympy Set syntax."""
    if ns is None:
        ns = dict(_SAFE_NAMES)
    if not isinstance(s, str):
        try:
            val = sympify_nontext(s)                # see parse_expr_str: containers are refused
        except (sp.SympifyError, TypeError) as e:
            raise ParseError(f"not a set: {type(s).__name__}") from e
        return val if isinstance(val, sp.Set) else FiniteSet(val)
    s2 = preclean(s)
    # union split at top level on " U " / "∪" (already mapped to " U ")
    parts, depth, cur = [], 0, ""
    i = 0
    while i < len(s2):
        c = s2[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if depth == 0 and s2.startswith(" U ", i):
            parts.append(cur)
            cur = ""
            i += 3
            continue
        cur += c
        i += 1
    parts.append(cur)
    sets = [_parse_single_set(p, ns) for p in parts if p.strip()]
    return Union(*sets) if len(sets) > 1 else sets[0]


def parse_domain(spec: str | None, var, ns: dict[str, Any] | None = None) -> sp.Set:
    """Domain of discourse for `var`, from the *problem* (E4). None -> Reals."""
    if ns is None:
        ns = dict(_SAFE_NAMES)
    if spec is None or str(spec).strip() == "":
        return S.Reals
    s = preclean(str(spec))
    s = re.sub(r"^\s*" + re.escape(str(var)) + r"\s+in\s+", "", s)
    if s in ("Reals", "R"):
        return S.Reals
    if s in ("Integers", "Z"):
        return S.Integers
    if s in ("Naturals", "Z+", "N"):
        return S.Naturals
    if s in ("Naturals0", "N0"):
        return S.Naturals0
    # relational spec like "x > 0 and x != 1"
    if any(op in s for op in ("<", ">", "!=")) and not s.startswith(("Interval", "Union", "(", "[")):
        conds = re.split(r"\s+and\s+|\s*&\s*|\s*∧\s*", s)
        dom = S.Reals
        for c in conds:
            rel = parse_relation(c, ns)
            dom = Intersection(dom, sp.solveset(rel, var, S.Reals))
        return dom
    return parse_set_str(s, ns)


# ----------------------------------------------------------------------------
# claimed-answer parsing
# ----------------------------------------------------------------------------
def parse_answer(kind: str, payload, ns: dict[str, Any] | None = None):
    """Return a sympy object for a ClaimedAnswer. Raises ParseError."""
    if ns is None:
        ns = dict(_SAFE_NAMES)
    if kind in ("value", "expression"):
        if isinstance(payload, (list, tuple)):
            raise ParseError("value answer must be a single expression")
        return parse_expr_str(str(payload), ns)
    if kind == "count":
        # never int(): it truncates 3.7 to 3 (principle 3)
        from ..equiv import exact_integer
        n = exact_integer(payload)
        if n is None:
            raise ParseError(f"count must be an integer, got {payload!r}")
        return Integer(n)
    if kind == "set":
        if isinstance(payload, (list, tuple)):
            return FiniteSet(*[parse_expr_str(str(p), ns) for p in payload])
        return parse_set_str(str(payload), ns)
    if kind == "interval":
        return parse_set_str(str(payload), ns)
    if kind == "dne":
        return sp.Symbol("DNE")
    if kind == "infinite":
        return parse_expr_str(str(payload), ns) if payload not in (None, "") else oo
    if kind in ("condition", "equation"):
        return parse_relation(str(payload), ns)
    if kind == "none":
        return None
    raise ParseError(f"unknown answer kind {kind!r}")
