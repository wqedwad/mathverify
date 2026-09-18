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

import re
from typing import Any

import sympy as sp
from sympy import (S, Symbol, Rational, Integer, Interval, FiniteSet, Union, Intersection,
                   Complement, EmptySet, Eq, Ne, Lt, Le, Gt, Ge, And, Or, Not, pi, E, I, oo, zoo, nan)
from sympy.parsing.sympy_parser import (parse_expr, standard_transformations, convert_xor)

__all__ = ["ParseError", "build_namespace", "parse_expr_str", "parse_relation", "parse_answer",
           "parse_domain", "parse_set_str", "is_latex", "preclean"]


class ParseError(ValueError):
    pass


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
    return sp.nsimplify(v) * pi / 180


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


_SAFE_NAMES: dict[str, Any] = {
    # constants
    "pi": pi, "E": E, "e": E, "I": I, "i": I, "oo": oo, "inf": oo, "zoo": zoo, "nan": nan,
    # elementary
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "acot": sp.acot, "atan2": sp.atan2,
    "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan, "arccot": sp.acot,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "exp": sp.exp, "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt, "cbrt": sp.cbrt, "root": sp.root,
    "Abs": sp.Abs, "abs": sp.Abs, "floor": sp.floor, "ceiling": sp.ceiling, "ceil": sp.ceiling,
    "frac": sp.frac, "sign": sp.sign, "Mod": sp.Mod, "mod": sp.Mod,
    "gcd": sp.gcd, "lcm": sp.lcm, "igcd": sp.igcd, "ilcm": sp.ilcm,
    "factorial": sp.factorial, "binomial": sp.binomial, "C": sp.binomial, "comb": sp.binomial,
    "P": _perm, "perm": _perm, "deg": _deg,
    "dist": _dist, "slope": _slope, "tri_area": _tri_area, "dot": _dot, "point_line_dist": _point_line_dist,
    "at": lambda e, v, val: sp.sympify(e).subs(v, val),     # at(diff(f(x), x), x, 1)
    "eigmax": lambda m: sp.Max(*[k for k in sp.Matrix(m).eigenvals() if k.is_real]),
    "eigmin": lambda m: sp.Min(*[k for k in sp.Matrix(m).eigenvals() if k.is_real]),
    "trace": lambda m: sp.Matrix(m).trace(), "rank": lambda m: sp.Matrix(m).rank(),
    "Max": sp.Max, "Min": sp.Min, "max": sp.Max, "min": sp.Min,
    "re": sp.re, "im": sp.im, "conjugate": sp.conjugate, "arg": sp.arg,
    # calculus (unevaluated forms allowed in step claims)
    "Sum": sp.Sum, "Product": sp.Product, "Integral": sp.Integral, "Derivative": sp.Derivative,
    "Limit": sp.Limit, "diff": sp.diff, "integrate": sp.integrate, "limit": sp.limit,
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

_ALLOWED_DOTTED = {
    "Interval.open", "Interval.Lopen", "Interval.Ropen", "S.Reals", "S.Integers", "S.Naturals",
    "S.Naturals0", "S.EmptySet", "S.Complexes", "S.Half", "S.Zero", "S.One", "S.Infinity",
    "S.NegativeInfinity", "S.UniversalSet",
}

_IDENT_RE = re.compile(r"(?<![\w.])[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*")  # skips the e in 1e3
_FORBIDDEN_SUBSTR = ("__", "import", "lambda", "exec", "eval", "open(", "getattr", "setattr",
                     "globals", "locals", "compile", "input", "os.", "sys.", "subprocess")


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
    argsyms = [ns[a] for a in fdef.args]
    body = parse_expr_str(fdef.expr, ns)

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


def _check_safe(s: str, ns: dict[str, Any]) -> None:
    # after preclean only ASCII may remain: anything else is prose or an injection attempt
    bad_chars = [ch for ch in s if ord(ch) > 127]
    if bad_chars:
        raise ParseError(f"non-ASCII characters in expression after normalisation: {bad_chars[:5]!r}")
    low = s.lower()
    for bad in _FORBIDDEN_SUBSTR:
        if bad in low:
            raise ParseError(f"forbidden token {bad!r} in expression")
    for m in _IDENT_RE.finditer(s):
        ident = m.group(0)
        if ident in ns or ident in _ALLOWED_DOTTED:
            continue
        if "." in ident:
            raise ParseError(f"dotted name not allowed: {ident}")
        if ident in {"in", "U", "N", "and", "or", "not"}:
            continue
        raise ParseError(f"unknown identifier {ident!r} (declare it in the IR)")


def _latex_to_sympy(s: str, ns: dict[str, Any]):
    from latex2sympy2_extended import latex2sympy
    expr = latex2sympy(s)
    # rebind free symbols to the IR symbols (assumptions)
    reps = {}
    for fs in expr.free_symbols:
        if fs.name in ns and isinstance(ns[fs.name], Symbol):
            reps[fs] = ns[fs.name]
    if reps:
        expr = expr.subs(reps, simultaneous=True)
    return expr


def parse_expr_str(s: str, ns: dict[str, Any] | None = None, *, rational: bool = True):
    """Parse a single expression (no top-level relation)."""
    if ns is None:
        ns = dict(_SAFE_NAMES)
    if not isinstance(s, str):
        return sp.sympify(s)
    raw = s
    s = strip_presentation(_strip_invisible(s))
    if is_latex(s):
        try:
            return _latex_to_sympy(s, ns)
        except Exception as e:  # pragma: no cover - fall through to canonical
            raise ParseError(f"LaTeX parse failed for {raw!r}: {e}") from e
    s = preclean(s)
    _check_safe(s, ns)
    try:
        return parse_expr(s, local_dict=ns, global_dict={},
                          transformations=_TRANSFORMS if rational else _TRANSFORMS_FLOAT, evaluate=True)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"cannot parse {raw!r}: {e}") from e


_REL_OPS = ["<=", ">=", "!=", "==", "=", "<", ">"]
_REL_CLASS = {"<=": Le, ">=": Ge, "!=": Ne, "==": Eq, "=": Eq, "<": Lt, ">": Gt}


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
    if is_latex(s):
        # LaTeX relations: latex2sympy handles "=" -> Eq
        expr = _latex_to_sympy(s, ns)
        return expr
    s2 = preclean(s)
    # explicit And/Or already in sympy syntax
    parts = _split_top_level(s2)
    if len(parts) == 1:
        return parse_expr_str(s2, ns)
    exprs = [parse_expr_str(chunk, ns) for _, chunk in parts]
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
        val = sp.sympify(s)
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
        if isinstance(payload, bool):
            raise ParseError("count must be an integer")
        return Integer(int(payload))
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
