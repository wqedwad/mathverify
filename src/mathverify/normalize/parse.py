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
import contextvars
import math
import re
import threading
from fractions import Fraction
from typing import Any

import sympy as sp
from sympy.core.parameters import global_parameters
from sympy import (S, Symbol, Rational, Integer, Interval, FiniteSet, Union, Intersection,
                   Complement, EmptySet, Eq, Ne, Lt, Le, Gt, Ge, And, Or, Not, pi, E, I, oo, zoo, nan)
from sympy.parsing.sympy_parser import (parse_expr, standard_transformations, convert_xor,
                                        stringify_expr)

__all__ = ["ParseError", "UndeclaredSymbolError", "ClaimNotAValue", "COMPUTING_OPERATORS",
           "claim_namespace", "check_claim_is_value", "build_namespace", "parse_expr_str", "parse_relation", "parse_answer",
           "parse_domain", "parse_set_str", "is_latex", "preclean", "parse_as_written"]


class ParseError(ValueError):
    pass


# ----------------------------------------------------------------------------
# no closed form is evaluated numerically while a text is read
# ----------------------------------------------------------------------------
_FORMS_HELD: contextvars.ContextVar = contextvars.ContextVar("forms_held", default=False)


def _install_form_evalf_hold() -> None:
    """SymPy evaluates a closed Integral, Sum or Product with evalf wherever a node decides on its numeric value:
    floor, ceiling, `//`, `%`, a comparison (`>`, `<=`), Max/Min, Abs, sign, Piecewise conditions, the ends of an
    Interval, a membership in a FiniteSet, and every rebuild after `subs` (at()). evalf misses the peak of
    ∫_{-1}^{1} 1000·exp(-10⁶(x - 1/3)²) dx ≈ 1.77 (it gives 2.9e-834): read as a problem's text, floor(∫) was 0,
    `∫ // 1` 0, Interval(1, ∫) empty, `∫ > 1` false, and each was certified (fourth audit F1, attack on d4h YO-1).
    While a text is parsed (`_holds_forms`) evalf of these three forms raises NotImplementedError, the error
    SymPy's own evalf reads as "no number" (a Limit has no evalf at all): every such node stays as written, and
    the value is taken later only from `equiv.forms.checked_forms`, confirmed by numbers. Outside a parse evalf is
    SymPy's."""
    from sympy.core import evalf as evalf_mod
    if not evalf_mod.evalf_table:
        evalf_mod._create_evalf_table()
    for cls in (sp.Integral, sp.Sum, sp.Product):
        orig = evalf_mod.evalf_table.get(cls)
        if orig is None or getattr(orig, "forms_held", False):
            continue

        def held(x, prec, options, _orig=orig):
            if _FORMS_HELD.get():
                raise NotImplementedError("a closed form has no numeric value while a text is parsed")
            return _orig(x, prec, options)
        held.forms_held = True  # type: ignore[attr-defined]
        evalf_mod.evalf_table[cls] = held


_install_form_evalf_hold()


def _holds_forms(fn):
    """`fn` (a reader of text) run with the closed forms' numeric evaluation held (`_install_form_evalf_hold`): the
    readers that build a set with evaluation on (`parse_set_str`, `parse_domain`: the ends of an interval over a form are
    not compared). latex2sympy and `parse_relation` need no hold of their own: SymPy takes a form with a bound symbol for
    a symbolic term, the relations are built unevaluated, and the deciding nodes rebuilt over a form stay so (`rebuilt`):
    with or without a hold there, no case of the d4h sonda and no parse of 69 texts over the spike integral differed
    (round 2 of d4h, completed). Nor does `guarded_parse_expr` once merged with d4b round 10, whose strict evaluation
    reads no number off a form (`_sympy_guards`): without its hold the 657 cases of the d4h sonda and 86 texts over the
    spike read the same (merge of 16 Oct 2026), and the hold was removed."""
    def call(*args, **kwargs):
        token = _FORMS_HELD.set(True)
        try:
            return fn(*args, **kwargs)
        finally:
            _FORMS_HELD.reset(token)
    call.__name__ = getattr(fn, "__name__", "reader")
    call.__qualname__ = getattr(fn, "__qualname__", call.__name__)
    call.__doc__ = fn.__doc__
    call.__wrapped__ = fn  # type: ignore[attr-defined]
    return call


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


# the gcd/lcm calls a parse makes on numbers alone, while `recording_integer_ops` is active
_INTEGER_OP_RECORD: contextvars.ContextVar = contextvars.ContextVar("integer_op_record", default=None)


class recording_integer_ops:  # noqa: N801 - used as a context manager
    """Within it, every gcd/lcm the parse computes from closed arguments (no free symbol) is recorded in the
    list it yields: a claimed answer that makes the parse compute one is a computation, not a value
    (GCD-10, principle 2), whatever its spelling (\\gcd, \\mathit{gcd}, \\textbf{lcm}, (gcd)(24, 18), igcd) and
    wherever it stands (gcd(120, 84)*a); the text regex this replaced missed most of them (fourth audit
    CAP-G1)."""

    def __enter__(self) -> list:
        self._seen: list = []
        self._token = _INTEGER_OP_RECORD.set(self._seen)
        return self._seen

    def __exit__(self, *exc) -> None:
        _INTEGER_OP_RECORD.reset(self._token)


def _record_integer_op(name: str, args) -> None:
    rec = _INTEGER_OP_RECORD.get()
    if rec is not None and args and not any(getattr(a, "free_symbols", None) for a in args):
        rec.append(f"{name}{tuple(args)}")


def _integer_op(cls):
    """The callable the namespace gives for gcd/lcm: SymPy's `gcd([84, 120])` list form stays
    readable (the class itself takes the numbers as arguments)."""
    def call(*args):
        if len(args) == 1 and isinstance(args[0], (list, tuple, sp.Tuple)):
            args = tuple(args[0])
        _record_integer_op(cls.__name__, args)
        return cls(*args)
    call.__name__ = cls.__name__
    return call


_GCD_CALL, _LCM_CALL = _integer_op(gcd), _integer_op(lcm)


def _integer_only_op(cls, name):
    """`igcd`/`ilcm`: SymPy's integer-only spellings. SymPy's own refused a symbol, so igcd(n, 2)
    with n an integer was unreadable (30 Sep 2026); here it is the integer gcd/lcm, still refused
    for an argument not known to be an integer (no fraction rule under the integer name)."""
    def call(*args):
        args = tuple(sympify_nontext(a) for a in args)
        if any(getattr(a, "is_integer", None) is not True for a in args):
            raise ValueError(f"{name} takes integers")
        _record_integer_op(name, args)
        return cls(*args)
    call.__name__ = name
    return call


def _set_op(op):
    """Union/Intersection/Complement written in SymPy's own syntax, their arguments' endpoints made
    one spelling first (equiv.sets.unify_endpoints), as for the `U` notation: SymPy merged
    `Union(Interval.open(-oo, R), Interval.open(3, oo))`, R = sqrt(11 + 6*sqrt(2)) - sqrt(2) = 3,
    into the whole line before anything could compare R with 3 (V14, 30 Sep 2026)."""
    def build(*sets, **kw):
        from ..equiv.sets import EndpointsIncomparable, unify_endpoints
        try:
            sets = unify_endpoints(list(sets))
        except EndpointsIncomparable as e:
            raise ParseError(f"set endpoints cannot be compared exactly: {e}") from e
        return op(*sets, **kw)
    build.__name__ = op.__name__
    build.builds_set = True  # type: ignore[attr-defined]
    return build


def _names_a_set(obj) -> bool:
    """A namespace entry that is a set or builds one (Reals, Interval, FiniteSet, Union, S)."""
    return isinstance(obj, sp.Set) or (isinstance(obj, type) and issubclass(obj, sp.Set)) \
        or getattr(obj, "builds_set", False) is True or isinstance(obj, _SingletonNames)


_UNION_OP, _COMPLEMENT_OP = _set_op(Union), _set_op(Complement)


def _as_set(v):
    """`v` as the operand of a set operation: what SymPy's own `Set.__add__` accepts (a set, or a Python
    set it converts to a FiniteSet), None otherwise."""
    if isinstance(v, sp.Set):
        return v
    if isinstance(v, (set, frozenset)):
        return FiniteSet(*[sympify_nontext(e) for e in v])
    return None


def _set_add(a, b):
    """`a + b`; the union of two sets through `_set_op`, see `_route_set_arithmetic`."""
    other = _as_set(b) if isinstance(a, sp.Set) else None
    return _UNION_OP(a, other) if other is not None else a + b


def _set_sub(a, b):
    """`a - b`; the complement of two sets through `_set_op`, see `_route_set_arithmetic`."""
    other = _as_set(b) if isinstance(a, sp.Set) else None
    return _COMPLEMENT_OP(a, other) if other is not None else a - b


_SET_ARITHMETIC = {"_mv_set_add": _set_add, "_mv_set_sub": _set_sub}


def _routed_binop(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        fn = ast.copy_location(ast.Name("_mv_set_add" if isinstance(node.op, ast.Add) else "_mv_set_sub",
                                        ast.Load()), node)
        return ast.copy_location(ast.Call(fn, [node.left, node.right], []), node)
    return node


def _route_set_arithmetic(code: str, names: dict[str, Any]):
    """The code compiled with every `+`/`-` a call that routes a set's union and complement through
    `_set_op`, when it names a set; None otherwise (it is then evaluated as it stands). SymPy's
    `Set.__add__`/`__sub__` build Union/Complement directly, so the endpoints were not made one spelling
    first: Interval.open(-oo, R) + Interval.open(3, oo), R = sqrt(11 + 6*sqrt(2)) - sqrt(2) = 3, was the
    whole line, certified as the domain of x + 1 (V16, 30 Sep 2026). Anything that is not a set is added
    as before. The walk is iterative and the tree is compiled as it is (`ast.unparse` recursed out at a
    sum of 500 terms)."""
    try:
        tree = ast.parse(code, mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None                               # parse_expr reports it
    nodes = list(ast.walk(tree))
    if not any(isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)) for n in nodes) or not any(
            isinstance(n, ast.Name) and _names_a_set(names.get(n.id)) for n in nodes):
        return None
    stack: list = [tree]
    while stack:
        node = stack.pop()
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for i, v in enumerate(value):
                    if isinstance(v, ast.AST):
                        value[i] = _routed_binop(v)
                        stack.append(value[i])
            elif isinstance(value, ast.AST):
                new = _routed_binop(value)
                setattr(node, field, new)
                stack.append(new)
    return compile(tree, "<expression>", "eval")


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


class HeldIntegral(sp.Integral):
    """An integral with a parameter (a free symbol) or without a range, held as the form: SymPy's
    value of it is taken nowhere (DECISIONS §80, F9). SymPy's parametric result is wrong in some
    regions of the parameter: integrate(1/t, (t, 1, x)) is log(x), so L(-1) = I*pi was certified for
    L(x) = ∫_1^x dt/t, and an integral computed with a parameter that a given then fixed was taken
    unconfirmed (∫_{-1}^{1} a|cos x| dx = 0 with a = 1; the value is 2 sin 1; third audit of 30 Sep
    2026). `doit` (and so `simplify`) leaves it as it is; once its parameters have values it is a
    closed form, whose value only `equiv.forms.checked_forms` takes, confirmed by numbers."""

    def doit(self, **hints):
        return self


class HeldLimit(sp.Limit):
    """A limit with a parameter, held as the form (see HeldIntegral): with n an integer SymPy's
    limit of a*n*sin(pi/n) at oo is 0 (it is a*pi), and the root set of limit(...) = 2*pi was
    certified empty (third audit of 30 Sep 2026, N8)."""

    def doit(self, **hints):
        return self


HELD_FORMS = (HeldIntegral, HeldLimit)
# a non-identifier key of the namespace: the values the givens pin symbols to (`given_bindings`),
# read by `hold_parametric`; no text can name it
PINS_KEY = "<pins>"
# the names a pin never replaces (the task's own variable, `build_namespace`): F(x) = ∫_0^x t² dt with the
# given x = 2 was parsed as the constant 8/3, and F'(2) = 0 was certified (fourth audit P1)
PROTECTED_KEY = "<pins-protected>"


class PinnedBoundVariable(ParseError):
    """A symbol a given pins occurs inside an Integral or a Limit where an enclosing operator binds it
    (d/da, a Sum's index) or where it is the task's own variable: whether the value goes in before or
    after the operator is the reading of the problem, and the parse does not choose one (part d4d)."""


def _closed_form(form) -> bool:
    """A limit, or an integral definite in every variable, with no free symbol."""
    if form.free_symbols:
        return False
    return not isinstance(form, sp.Integral) or (bool(form.limits) and all(len(lim) == 3 for lim in form.limits))


def unhold(form):
    """The plain Integral or Limit of a held form (any other expression unchanged)."""
    if isinstance(form, HeldIntegral):
        return sp.Integral(*form.args)
    if isinstance(form, HeldLimit):
        return sp.Limit(*form.args)
    return form


def _held(form):
    """`form` (an Integral or a Limit) held when it is not closed, plain when it is."""
    if _closed_form(form):
        return unhold(form)
    if isinstance(form, sp.Integral):
        return form if isinstance(form, HeldIntegral) else HeldIntegral(*form.args)
    return form if isinstance(form, HeldLimit) else HeldLimit(*form.args)


def _pinned(form, pins: dict):
    """`form` with each of its free symbols that a given pins to a number replaced by it. Never a
    bound variable: an indefinite integral's variable is free in SymPy and is kept, and a Limit is
    rebuilt from its parts (SymPy's Limit.subs also rewrites the variable it binds)."""
    if isinstance(form, sp.Integral):
        sub = {s_: v for s_, v in pins.items() if s_ in form.free_symbols and s_ not in form.variables}
        return form.subs(sub) if sub else form
    e, z, z0, d = form.args
    sub = {s_: v for s_, v in pins.items() if s_ in form.free_symbols and s_ != z}
    if not sub:
        return form
    return type(form)(e.subs(sub), z, z0.subs(sub), d)


def binder_variables(e) -> set:
    """The variables the operator `e` binds in its arguments: d/dx's x, a Sum's or an Integral's index,
    a Limit's variable, a Subs' or a Lambda's variables (empty for anything else)."""
    if isinstance(e, sp.Derivative):
        return set(e.variables)
    if isinstance(e, (sp.Sum, sp.Product, sp.Integral)):
        return {lim[0] for lim in e.limits}
    if isinstance(e, sp.Limit):
        return {e.args[1]}
    if isinstance(e, (sp.Subs, sp.Lambda)):
        return set(e.variables)
    return set()


def rebuilt(e, args):
    """`e` rebuilt from new `args` (evaluation as the caller's), but UNEVALUATED when `e` decides on the numeric
    value of an argument (floor, Max, |·|, ...) and one holds a closed form: rebuilt evaluated, evalf decided it
    (`_form_unevaluated`): floor(∫ + a) once a given fixed a, floor(Σ 1/k²) once the index became an integer."""
    if isinstance(e, _DECIDING) and has_closed_form_node(args):
        with sp.evaluate(False):
            return e.func(*args)
    return e.func(*args)


def substitute_free(expr, mapping: dict):
    """`expr` with the FREE occurrences of the symbols of `mapping` replaced: never a variable an
    enclosing operator binds (`binder_variables`), whose own range or point is still substituted.
    `xreplace` rewrites bound variables too (Sum(k**2, (k, 1, n)) with k = 5 became a sum over 5), and
    Limit.subs rewrites its own variable. Evaluation follows the caller's `sp.evaluate` setting."""
    if not mapping or not isinstance(expr, sp.Basic):
        return expr

    def walk(e, sub):
        if not sub or not isinstance(e, sp.Basic) or not (e.free_symbols & set(sub)):
            return e
        if e in sub:
            return sub[e]
        if not e.args:
            return e
        bound = binder_variables(e)
        inner = {s_: v for s_, v in sub.items() if s_ not in bound} if bound else sub
        args = [walk(a, inner) for a in e.args]
        return rebuilt(e, args) if any(a is not b for a, b in zip(args, e.args)) else e

    return walk(expr, dict(mapping))


def hold_parametric(expr, pins: dict | None = None, protected=()):
    """`expr` with every Integral and Limit that has a parameter held (HeldIntegral, HeldLimit), after
    the parameters the givens pin to a number (`pins`) are replaced by it: such a form is then closed
    and plain, and its value is the one numbers confirm (equiv.forms, DECISIONS §72 (a)).

    A pin never reaches a variable an enclosing operator binds, nor a name in `protected` (the task's
    own variable): d/da ∫_0^1 a·t dt with a = 2 became d/da of the constant 1, and F(x) = ∫_0^x t² dt
    with the given x = 2 the constant 8/3, so 0 was certified for both (fourth audit P1). Such a form
    raises PinnedBoundVariable: whether the value goes in before or after the operator is a reading
    of the problem, and the verifier abstains on it (part d4d)."""
    if not isinstance(expr, sp.Basic):
        return map_entries(expr, lambda e: hold_parametric(e, pins, protected))
    if not expr.has(sp.Integral, sp.Limit):
        return expr
    pins = pins or {}
    protected = frozenset(protected or ())

    def walk(e, bound):
        if not isinstance(e, sp.Basic) or not e.has(sp.Integral, sp.Limit):
            return e
        inner = bound | binder_variables(e)
        args = [walk(a, inner) for a in e.args]
        if any(a is not b for a, b in zip(args, e.args)):
            e = rebuilt(e, args)
        if isinstance(e, (sp.Integral, sp.Limit)):
            own = binder_variables(e)
            blocked = sorted(str(s_) for s_ in pins if s_ in e.free_symbols and s_ not in own
                             and (s_ in bound or s_.name in protected))
            if blocked:
                raise PinnedBoundVariable(f"a given pins {blocked} inside {e}, where an enclosing operator or "
                                          "the task binds it: not read")
            e = _held(_pinned(e, pins) if pins else e)
        return e

    return walk(expr, frozenset())


def _hold_value(out, pins, protected=()):
    """A value parse's result with its parametric forms held (`hold_parametric`), on each side of a
    relation (rebuilt unevaluated, `_on_sides`), in each entry of a matrix, list or tuple (`map_entries`);
    anything without an Integral or a Limit unchanged. A Matrix is no Basic: Matrix([[Limit(a*n*sin(pi/n),
    n, oo)]]) with a = 2 kept the plain limit, the evaluate certificate's simplify took SymPy's 0 for it,
    and Matrix([[0]]) was certified (fourth audit H1)."""
    if not isinstance(out, sp.Basic):
        return map_entries(out, lambda e: _hold_value(e, pins, protected))
    if not out.has(sp.Integral, sp.Limit):
        return out
    return _on_sides(out, lambda e: hold_parametric(e, pins, protected))


# the forms whose value only `equiv.forms.checked_forms` takes (numbers confirm SymPy's)
FORM_TYPES = (sp.Integral, sp.Sum, sp.Product, sp.Limit)


def map_entries(obj, f):
    """`f` applied to each entry of a matrix (`applyfunc`, same class), a list or a tuple (recursively), or
    to `obj` itself when it is a Basic; anything else unchanged. The containers a parse returns that are
    no Basic: Matrix(...) and the Python list or tuple of a bracketed text."""
    if isinstance(obj, sp.MatrixBase):
        return obj.applyfunc(f)
    if isinstance(obj, (list, tuple)):
        return type(obj)(map_entries(x, f) for x in obj)
    if isinstance(obj, sp.Basic):
        return f(obj)
    return obj


def entries(obj) -> list:
    """The Basic entries of `obj` (a matrix, a list or a tuple, recursively), or [obj] for a Basic."""
    if isinstance(obj, sp.MatrixBase):
        return [x for x in obj if isinstance(x, sp.Basic)]
    if isinstance(obj, (list, tuple)):
        return [y for x in obj for y in entries(x)]
    return [obj] if isinstance(obj, sp.Basic) else []


def contains_form(obj) -> bool:
    """Does `obj` (any container a parse builds) hold an Integral, a Sum, a Product or a Limit?"""
    return any(e.has(*FORM_TYPES) for e in entries(obj))


def _form_kept(fn):
    """`fn`, a rewrite that keeps the value (simplify, expand, factor, ...), except on an argument that holds
    an Integral, a Sum, a Product or a Limit: that argument is returned as written, its value is the one
    numbers confirm later (`equiv.forms.checked_forms`). SymPy's simplify ends with doit: inside a problem's
    text simplify(Limit(n*sin(pi/n), n, oo)) was SymPy's 0 with n an integer (the limit is pi),
    simplify(2*Integral(Abs(cos(x)), (x, -1, 1))) 0 (it is 4 sin 1), the value was taken unconfirmed and 0
    was certified; read as written under evaluation off the same call ran for 35-130 s (fourth audit F1).
    A form held from doit (HeldIntegral) is no help: simplify rebuilds a Sum as a plain one and sums it."""
    def call(*args, **kwargs):
        # the expression may be passed by keyword too (simplify(expr=...), expand(e=...)): with the form there and
        # no positional argument SymPy's simplify ran, and the step simplify(expr=2∫|cos x|) = 0 was verified, the
        # true one (= 4 sin 1) refuted (attack on d4h, YO-3)
        if contains_form(list(args) + list(kwargs.values())):
            return _rewritten_argument(getattr(fn, "__name__", "rewrite"), args, kwargs)
        return fn(*args, **kwargs)
    call.__name__ = getattr(fn, "__name__", "rewrite")
    return call


def _rewritten_argument(name: str, args, kwargs):
    """The expression a value-keeping rewrite (simplify, expand, ...) is called on: its first positional argument,
    or, with none, its one keyword argument that is an expression (simplify(expr=...)); ParseError otherwise."""
    if args:
        return args[0]
    exprs = [v for v in kwargs.values() if isinstance(v, (sp.Basic, sp.MatrixBase))]
    if len(exprs) != 1:
        raise ParseError(f"{name} called with the keyword arguments {sorted(kwargs)}: not read")
    return exprs[0]


def has_closed_form_node(obj) -> bool:
    """Does `obj` (any container a parse builds) hold an Integral, Sum, Product or Limit with no free symbol?"""
    return any(isinstance(n, FORM_TYPES) and not n.free_symbols
               for e in entries(obj) if e.has(*FORM_TYPES) for n in sp.preorder_traversal(e))


# the helpers whose value DECIDES on the numeric value of an argument (its integer part, its sign, which
# argument is larger, whether a relation holds)
_DECIDING = (sp.floor, sp.ceiling, sp.frac, sp.sign, sp.Abs, sp.Max, sp.Min, sp.Mod, sp.re, sp.im, sp.arg,
             sp.conjugate, sp.atan2, sp.Piecewise, sp.core.relational.Relational)


class _ClassCall:
    """A namespace helper standing for SymPy's class `base`: called, it runs `call`; named bare it is `base`
    itself (`_sympy_`). The parameter which = "min" is read as written with the problem's namespace, and a
    plain function in Min's place could not be sympified: every extremum task abstained (review, part d4h)."""

    def __init__(self, base, call):
        self._base, self._call = base, call
        self.__name__ = base.__name__

    def __call__(self, *args, **kwargs):
        return self._call(*args, **kwargs)

    def _sympy_(self):
        return self._base


def _form_unevaluated(cls):
    """SymPy's `cls`, a helper whose value decides on the numeric value of its argument (floor, Max, sign,
    ...), built UNEVALUATED over a closed Integral, Sum, Product or Limit: SymPy decides it with evalf, and
    evalf misses the peak of ∫_{-1}^{1} 1000·exp(-10⁶(x - 1/3)²) dx = √π·erf(...) ≈ 1.77, so its floor was 0 and
    certified (claim 0 CORRECT, the true 1 INCORRECT), ceiling 1 and Max(∫, 1) = 1 too, while the integral alone
    is UNKNOWN: its value is never confirmed (fourth audit F1, review of part d4h). Built unevaluated the form
    stays, and `equiv.forms.checked_forms` takes its value, confirmed by numbers, before anything decides."""
    def call(*args, **kwargs):
        if has_closed_form_node(list(args)):
            with sp.evaluate(False):
                return cls(*args, **kwargs)
        return cls(*args, **kwargs)
    return _ClassCall(cls, call)


def _matrix_decision(name: str, fn):
    """A helper whose value DECIDES on the entries of a matrix (rank: which entries are 0; eigmax/eigmin:
    which eigenvalues are real): refused (ParseError) on a matrix that holds a form, whose value SymPy
    decided unconfirmed (the rank of [[L, 1], [L, 2]] with L = lim n·sin(π/n) was 1: SymPy's 0 for L; an
    eigenvalue ∫_{-1}^{1}|cos x| dx, of undecided realness, was dropped from eigmax), and on an eigenvalue
    whose realness SymPy does not decide (it was dropped, not read)."""
    def call(m, *args, **kwargs):
        mat = sp.Matrix(m)
        if contains_form(mat):
            raise ParseError(f"{name} of a matrix holding an integral, sum, product or limit: not read")
        return fn(mat, *args, **kwargs)
    call.__name__ = name
    return call


def _real_eigen(pick):
    def value(mat):
        ev = list(mat.eigenvals())
        real = [k.is_real for k in ev]
        if any(r is None for r in real):
            raise ParseError(f"an eigenvalue of {mat} whose realness is not decided: not read")
        return pick(*[k for k, r in zip(ev, real) if r])
    return value


def _limit(e, v, p, d=None):
    """`limit` never computes: a closed limit stays the form, and a value is taken only when numbers
    confirm SymPy's (equiv.forms). With n an integer SymPy's limit of n*tan(pi/n) at oo is 0 (the
    limit is pi), and the parse certified 0 (audit of 29 Sep 2026). A limit with a parameter is held
    (HeldLimit): its parameter pinned by a given makes it closed (`hold_parametric`), otherwise it has
    no value."""
    form = _Limit(e, v, p, d)
    return _held(form) if isinstance(form, sp.Limit) else form


def _integrate(*args, **kwargs):
    """`integrate` never computes: an integral definite in every variable and closed stays the form,
    as `Integral` does, and its value is confirmed by numbers (equiv.forms). SymPy integrates |cos x|
    over [-1, 1] to 0 (the value is 2 sin 1), and the parse certified 0 (audit of 29 Sep 2026). An
    antiderivative or an integral with a parameter is held (HeldIntegral, DECISIONS §80)."""
    form = sp.Integral(*args, **kwargs)
    return _held(form) if isinstance(form, sp.Integral) else form


_integrate.binds_range = True  # type: ignore[attr-defined]


_JUMP_CACHE: dict = {}
_JUMP_CACHE_LOCK = threading.Lock()


def _jump_eval(cls, base, args):
    """The evaluation of a jump function of the namespace (`floor`, `ceiling`, `frac`, `sign`, `Mod` below): with
    constant arguments not all rational, the value from CERTIFIED signs and floors (equiv.numeric.jump_value), or
    None (the node stays as written) when they do not settle it; SymPy's own evaluation otherwise. SymPy reads a
    constant argument off rounding noise: (2*atan(tanh(1/2)) - atan(sinh(1)))**2 is exactly 0, and the parse
    made its ceiling 1 and the floor of its negative -1, so 1 and -1 were certified and the right 0 refuted
    (round 9 of part d4b, YO-4). The class is SymPy's subclass, so a rebuilt node (subs, a sandbox worker's
    unpickling) is held the same way. A closed integral, sum, product or limit among the arguments is read by strict
    evaluation alone here, not by its checked value (`equiv.numeric.forms_unvalued`): a form's value comes from
    `equiv.forms.checked_forms` where a certificate reads it, and a jump over the spike integral stays as written,
    while floor(Σ_{k=3}^{5} k), a sum strict evaluation reads, is 12 at the point a step is checked at (merge of d4h
    round 2; refused outright over every form, the wrong step floor(Σ_{k=3}^{n} k) = 0 under n² = 25 was no longer
    refuted at n = 5: tests/test_parca11_ters_aralik_adim.py)."""
    if all(isinstance(a, sp.Expr) and a.is_number is True and not a.free_symbols for a in args) \
            and not all(a.is_Rational for a in args) \
            and not any(a.has(sp.oo, -sp.oo, sp.zoo, sp.nan) for a in args):
        key = (base.__name__, tuple(args))
        with _JUMP_CACHE_LOCK:
            if key in _JUMP_CACHE:
                return _JUMP_CACHE[key]
        from ..equiv.numeric import forms_unvalued, jump_value
        with forms_unvalued():
            v = jump_value(base(*args, evaluate=False))
        with _JUMP_CACHE_LOCK:
            if len(_JUMP_CACHE) > 512:
                _JUMP_CACHE.clear()
            _JUMP_CACHE[key] = v
        return v
    return base.eval.__func__(cls, *args)


class floor(sp.floor):  # noqa: N801 - the name is the notation
    """SymPy's floor, evaluated at a constant only exactly (`_jump_eval`)."""

    @classmethod
    def eval(cls, arg):
        return _jump_eval(cls, sp.floor, (arg,))


class ceiling(sp.ceiling):  # noqa: N801 - the name is the notation
    """SymPy's ceiling, evaluated at a constant only exactly (`_jump_eval`)."""

    @classmethod
    def eval(cls, arg):
        return _jump_eval(cls, sp.ceiling, (arg,))


class frac(sp.frac):  # noqa: N801 - the name is the notation
    """SymPy's frac, evaluated at a constant only exactly (`_jump_eval`)."""

    @classmethod
    def eval(cls, arg):
        return _jump_eval(cls, sp.frac, (arg,))


class sign(sp.sign):  # noqa: N801 - the name is the notation
    """SymPy's sign, evaluated at a constant only exactly (`_jump_eval`)."""

    @classmethod
    def eval(cls, arg):
        return _jump_eval(cls, sp.sign, (arg,))


class Mod(sp.Mod):
    """SymPy's Mod, evaluated at constants only exactly (`_jump_eval`)."""

    @classmethod
    def eval(cls, p, q):
        return _jump_eval(cls, sp.Mod, (p, q))


JUMP_CLASSES = {sp.floor: floor, sp.ceiling: ceiling, sp.frac: frac, sp.sign: sign, sp.Mod: Mod}


def held_jumps(e):
    """`e` with SymPy's own floor, ceiling, frac, sign and Mod nodes (latex2sympy builds them) as the namespace's
    (`_jump_eval`), rebuilt as they stand: evaluated only where certified signs settle them."""
    if not isinstance(e, sp.Basic) or not e.has(*JUMP_CLASSES):
        return e
    return e.replace(lambda n: type(n) in JUMP_CLASSES,
                     lambda n: JUMP_CLASSES[type(n)](*n.args, evaluate=global_parameters.evaluate))


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


def _real_root(b, n=3, *k, **_kw):
    """A root WRITTEN as a root (`cbrt`, `root(b, n)`, `real_root`, `\\sqrt[n]{b}`, ∛) of odd index n: the
    real root, sign(b)·|b|^(1/n) (∛(-8) = -2), the curriculum's reading. SymPy's cbrt and root are the
    principal complex value, which is also what b**(1/3) is: (-8)**(1/3), cbrt(-8) and root(-8, 3) were
    one expression read under two conventions, and both -2 and 1 + √3 i were certified (fourth audit of
    1 Oct 2026, CAP-C1). The power notation b**(p/q) keeps its own node: at a negative base its value is a
    convention (certify.domain.Convention). An even index (√ itself) or a branch index `k` is SymPy's root."""
    n = sp.sympify(n)
    ni = int(n) if isinstance(n, Integer) else None        # Python ints: read as written, n > 1 is a Gt
    if not k and ni is not None and ni > 1 and ni % 2 == 1:
        return sign(b) * sp.Abs(b) ** Rational(1, ni)
    return sp.root(b, n, *k)


def _cbrt(b, **_kw):           # `evaluate=False` is passed by a parse as written
    return _real_root(b, 3)


class _SingletonNames:
    """`S` in a text: its singletons (S.Reals, S.Half, ... `_ALLOWED_DOTTED`) and S(2), a number; never a value
    itself. SymPy's registry named bare is no expression: the claim `S = {-2, 2}` read it as the left side and
    SymPy's SympifyError leaked out of verify, `{S}` was a layer exception (fourth audit PRE-RK-6, principle 13).
    Taken as a value (sympify), it raises ParseError."""

    def __getattr__(self, name):
        if f"S.{name}" in _ALLOWED_DOTTED:
            return getattr(S, name)
        raise AttributeError(name)

    def __call__(self, value, *args, **kwargs):
        if args or kwargs:
            raise ParseError("S(...) takes one number: not read")
        return sympify_nontext(value)

    def _sympy_(self):
        raise ParseError("S names SymPy's registry of singletons, not a value: not read")


_SINGLETON_NAMES = _SingletonNames()


_SAFE_NAMES: dict[str, Any] = {
    # constants
    "pi": pi, "E": E, "e": E, "I": I, "i": I, "oo": oo, "inf": oo, "zoo": zoo, "nan": nan,
    # elementary
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "acot": arccot, "atan2": sp.atan2,
    "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan, "arccot": arccot,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "exp": sp.exp, "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt, "cbrt": _cbrt, "root": _real_root,
    "real_root": _real_root,
    "Abs": sp.Abs, "abs": sp.Abs, "floor": floor, "ceiling": ceiling, "ceil": ceiling,
    "frac": frac, "sign": sign, "Mod": Mod, "mod": Mod,
    "gcd": _GCD_CALL, "lcm": _LCM_CALL, "igcd": _integer_only_op(gcd, "igcd"),
    "ilcm": _integer_only_op(lcm, "ilcm"),
    "factorial": sp.factorial, "binomial": sp.binomial, "C": sp.binomial, "comb": sp.binomial,
    "P": _perm, "perm": _perm, "deg": _deg,
    "dist": _dist, "slope": _slope, "tri_area": _tri_area, "dot": _dot, "point_line_dist": _point_line_dist,
    "at": _at,                                               # at(diff(f(x), x), x, 1)
    "eigmax": _matrix_decision("eigmax", _real_eigen(sp.Max)),
    "eigmin": _matrix_decision("eigmin", _real_eigen(sp.Min)),
    "trace": lambda m: sp.Matrix(m).trace(), "rank": _matrix_decision("rank", lambda m: m.rank()),
    "Max": sp.Max, "Min": sp.Min, "max": sp.Max, "min": sp.Min,
    "re": sp.re, "im": sp.im, "conjugate": sp.conjugate, "arg": sp.arg,
    # calculus (unevaluated forms allowed in step claims)
    "Sum": sp.Sum, "Product": sp.Product, "Integral": sp.Integral, "Derivative": sp.Derivative,
    "Limit": _Limit, "diff": sp.diff, "integrate": _integrate, "limit": _limit,
    # numbers
    "Rational": Rational, "Integer": Integer, "Float": sp.Float, "S": _SINGLETON_NAMES,
    "nsimplify": _form_kept(sp.nsimplify),
    # relations / logic
    "Eq": Eq, "Ne": Ne, "Lt": Lt, "Le": Le, "Gt": Gt, "Ge": Ge, "And": And, "Or": Or, "Not": Not,
    "Piecewise": sp.Piecewise,
    # sets
    "Interval": Interval, "FiniteSet": FiniteSet, "Union": _set_op(Union), "Intersection": _set_op(Intersection),
    "Complement": _set_op(Complement), "EmptySet": EmptySet, "Reals": S.Reals, "Integers": S.Integers,
    "Naturals": S.Naturals, "Naturals0": S.Naturals0, "Complexes": S.Complexes,
    "Range": sp.Range, "ImageSet": sp.ImageSet, "Lambda": sp.Lambda, "ConditionSet": sp.ConditionSet,
    # linear algebra
    "Matrix": sp.Matrix, "det": lambda m: sp.Matrix(m).det(), "eye": sp.eye, "zeros": sp.zeros,
    "Transpose": sp.Transpose,
    # polynomials / algebra helpers (pure, no solving)
    "expand": _form_kept(sp.expand), "factor": _form_kept(sp.factor), "simplify": _form_kept(sp.simplify),
    "cancel": _form_kept(sp.cancel), "together": _form_kept(sp.together), "apart": _form_kept(sp.apart),
    "Poly": sp.Poly, "degree": sp.degree,
    "Symbol": Symbol, "symbols": sp.symbols,
}
# the value-deciding helpers are built unevaluated over a closed form (`_form_unevaluated`)
for _name in ("Abs", "abs", "floor", "ceiling", "ceil", "frac", "sign", "Mod", "mod", "Max", "Min", "max", "min",
              "re", "im", "conjugate", "arg", "atan2", "Piecewise", "Eq", "Ne", "Lt", "Le", "Gt", "Ge"):
    _SAFE_NAMES[_name] = _form_unevaluated(_SAFE_NAMES[_name])
del _name

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
        bindings = given_bindings(ir, ns) if ir.givens else {}
        if bindings:
            # an integral or a limit whose parameter a given pins is read at that value (hold_parametric);
            # never the task's own variable (part d4d, P1)
            ns[PINS_KEY] = dict(bindings)
            ns[PROTECTED_KEY] = frozenset(task_variables(ir))
        for f in ir.functions:
            ns[f.name] = _make_function(f, ns, bindings)
    if extra:
        ns.update(extra)
    return ns


# the task's own variable when params name none: the certificates' defaults (certify.series reads n or k)
_TASK_VAR_DEFAULT = {"series_sum": "k", "recurrence_term": "n", "closed_form": "n"}
_TASK_VAR_KINDS = {"solve_equation", "solve_inequality", "count_roots", "count_integers", "count_solutions",
                   "domain_of", "limit", "antiderivative", "definite_integral", "derivative", "tangent_line",
                   "extremum", "trig_solve", "series_sum", "recurrence_term", "closed_form"}


def task_variables(ir) -> set[str]:
    """The name of the variable the task itself is about (`params["var"]`, or the certificate's default):
    the unknown of an equation, the variable of a derivative, a limit or an integral, a series' index."""
    kind = ir.task.kind
    v = (ir.task.params or {}).get("var")
    if isinstance(v, str) and v.strip():
        return {v.strip()}
    return {_TASK_VAR_DEFAULT.get(kind, "x")} if kind in _TASK_VAR_KINDS else set()


def given_bindings(ir, ns: dict[str, Any]) -> dict:
    """Symbols a given fixes to one real number (`a = 0`), read in the value namespace: a given that
    computes its value (`a = integrate(...)`) or calls a problem function binds nothing, and a symbol
    two givens bind to different values is left free (see `given_binding_report`)."""
    return given_binding_report(ir, ns)[0]


def same_value(a, b) -> bool:
    """Are the closed numbers a and b PROVED equal: the same expression, or an exact difference that
    simplifies to 0 (3 and log(8)/log(2)). Anything else counts as two values."""
    if a == b:
        return True
    try:
        return sp.simplify(sp.expand_log(sp.sympify(a) - sp.sympify(b), force=False)) == 0
    except Exception:  # noqa: BLE001
        return False


def given_binding_report(ir, ns: dict[str, Any]) -> tuple[dict, dict, dict]:
    """(`given_bindings`, the symbols two givens bind to different values with those values, the givens
    each symbol is bound by). A binding is only read here: whether it agrees with the rest of the
    problem is `certify.base.Ctx.binding_issues`'s question."""
    fnames = [f.name for f in ir.functions]
    vns = claim_namespace(ns, fnames)
    found: dict = {}
    clash: dict = {}
    sources: dict = {}
    for g in ir.givens:
        try:
            check_claim_is_value(g, fnames)
            rel = parse_relation(g, vns)
        except Exception:  # noqa: BLE001 - not a plain binding
            continue
        if not isinstance(rel, Eq):
            continue
        for s_, v in ((rel.lhs, rel.rhs), (rel.rhs, rel.lhs)):
            if isinstance(s_, Symbol) and isinstance(v, sp.Expr) and not v.free_symbols and v.is_real is True:
                if s_ in found and not same_value(found[s_], v):
                    clash.setdefault(s_, [found[s_]]).append(v)
                found.setdefault(s_, v)
                sources.setdefault(s_, []).append(g)
    return {s_: v for s_, v in found.items() if s_ not in clash}, clash, sources


def _make_function(fdef, ns, bindings: dict | None = None):
    # A formal argument is the function's own real variable. Taken from the namespace, it carried
    # the domain of a problem variable with the same name: with x declared positive the body
    # sqrt(x**2) + x was folded to 2*x, so f(-1) was -2 and the sum of f(k) over -2..2 was 0 (it is
    # 6; audit of 29 Sep 2026). A call substitutes its argument, whose own assumptions apply then.
    body_ns = dict(ns)
    body_ns.update({a: Symbol(a, real=True) for a in fdef.args})
    if body_ns.get(PINS_KEY):
        # a formal argument is no parameter of the problem, whatever a given fixes under its name
        body_ns[PINS_KEY] = {s_: v for s_, v in body_ns[PINS_KEY].items() if s_.name not in fdef.args}
        body_ns[PROTECTED_KEY] = frozenset(n for n in body_ns.get(PROTECTED_KEY, ()) if n not in fdef.args)
    argsyms = [body_ns[a] for a in fdef.args]
    body = parse_expr_str(fdef.expr, body_ns)

    def _f(*args):
        if len(args) != len(argsyms):
            raise ParseError(f"function {fdef.name} expects {len(argsyms)} args, got {len(args)}")
        # a sum over 1..2n in the body gets an integer index once n is an integer argument (the formal
        # n is real, so the parse left the index plain; second audit of 29 Sep 2026)
        return _integer_indices(body.subs(dict(zip(argsyms, args)), simultaneous=True))

    _f.__name__ = fdef.name
    _f.body = body            # type: ignore[attr-defined]
    _f.argsyms = argsyms      # type: ignore[attr-defined]
    _f.fdef = fdef            # type: ignore[attr-defined]
    _f.body_ns = body_ns      # type: ignore[attr-defined]
    # the declared domain (`"x > 0"`), a condition on the formal arguments; None when there is none.
    # A domain that cannot be read raises (the problem is not verified): it was dropped silently
    # unless it was one relation, and "(0, oo)", "x in (0, oo)", "x > 0 and x < 3" or "[0, oo)"
    # certified {-2, 2} for f(x) = 5 with f = x**2 + 1 (third audit of 30 Sep 2026, N5). A symbol
    # a given fixes (`x > a` with a = 0) is read with its value; one no given fixes is listed in
    # `domain_unbound` and the verifier abstains (the domain would be read for every a).
    _f.domain_rel = None      # type: ignore[attr-defined]
    _f.domain_unbound = ()    # type: ignore[attr-defined]
    if isinstance(getattr(fdef, "domain", None), str) and fdef.domain.strip():
        rel = read_domain_condition(fdef.domain, argsyms, body_ns)
        if rel is not None:
            rel = _conjunction(rel.xreplace({s_: v for s_, v in (bindings or {}).items()
                                             if s_.name not in fdef.args}), fdef.domain)
        _f.domain_rel = rel
        if rel is not None:
            _f.domain_unbound = tuple(sorted(s_.name for s_ in rel.free_symbols if s_.name not in fdef.args))
    return _f


class written_domain(sp.Function):  # noqa: N801 - a marker read by certify.domain
    """A call f(a) of an IR function read AS WRITTEN: its body as written with a substituted, and the
    condition the function's declared domain puts on a. Only definedness reads it (the value parse
    never builds it). The declared domain was ignored everywhere: f(x) = x**2 + 1 on x > 0 gave
    f(-2) = 5 and {-2, 2} for f(x) = 5 (second audit of 29 Sep 2026). The derivative of a call keeps
    the condition: without it `diff` of such a call raised and the whole text lost its conditions."""
    nargs = 2

    def _eval_derivative(self, s):
        return written_domain(self.args[0].diff(s), self.args[1])


def _written_call(fn, ns, depth=0):
    """An IR function called inside a text read as written: its body AS WRITTEN (so its conditions,
    x**2/x at 0, survive) with the arguments substituted unevaluated, inner calls expanded the same
    way. The evaluated call folded the body first: the derivative of f(x) = (x - 1)**2/(x - 1) at 1,
    the minimum on [1, 3], a sum over its terms and g(x) = f(x) + 3 at 1 were certified. A body that
    cannot be read that way gives the evaluated call, as before."""
    def call(*args):
        if len(args) != len(fn.argsyms) or depth > 20:
            return fn(*args)
        w = parse_as_written(fn.fdef.expr, dict(ns, **dict(zip(fn.fdef.args, fn.argsyms))), _depth=depth + 1)
        if w is None or len(w) != 1:
            return fn(*args)
        sub = dict(zip(fn.argsyms, args))
        with sp.evaluate(False):
            out = w[0].xreplace(sub)
            if fn.domain_rel is not None:
                out = written_domain(out, fn.domain_rel.xreplace(sub))
        return out
    return call


# ----------------------------------------------------------------------------
# pre-cleaning (unicode math, degrees, percents)
# ----------------------------------------------------------------------------
_UNICODE_MAP = {
    "π": "pi", "∞": "oo", "·": "*", "×": "*", "÷": "/", "−": "-", "–": "-", "—": "-",
    "≤": "<=", "≥": ">=", "≠": "!=", "√": "sqrt", "∛": "cbrt", "∅": "EmptySet", "∪": " U ", "∩": " N ",
    "²": "**2", "³": "**3", "⁴": "**4", "½": "(1/2)", "¼": "(1/4)", "¾": "(3/4)", "⅓": "(1/3)",
    "ℝ": "Reals", "ℤ": "Integers", "ℕ": "Naturals", "∈": " in ",
}
# `5π/6` is how a free-text solution writes 5*pi/6, but the unicode map alone turns it into
# `5pi/6`, which is a syntax error — and implicit multiplication is deliberately NOT enabled
# globally (it would silently read `zzz` as `z*z*z`). So the product is made explicit only
# where a digit or a closing bracket meets a unicode VALUE symbol, which is never anything but
# a product. Measured: 4 of 5 recovered trig answer sets were unparseable for exactly this.
_UNI_VALUE_RE = re.compile(r"([0-9)\]])\s*([π∞√∛ℝℤℕ∅])")
_DEG_NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:°|\bderece\b|\bdeg\b)")
_DEG_PAREN_RE = re.compile(r"\(([^()]*)\)\s*°")
_PCT_RE = re.compile(r"%\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*%")
_SQRT_BARE_RE = re.compile(r"(sqrt|cbrt)\s*(\d+(?:\.\d+)?|[A-Za-z_]\w*)(?![\w(])")


def _strip_invisible(s: str) -> str:
    """Remove format/invisible code points (Cf: zero-width space/joiner, BOM, soft hyphen, …).
    Measured: Python's tokenizer accepts U+200B inside a NAME, so 'E\\u200b' silently became
    an unknown Symbol instead of Euler's number — an invisible-character injection vector."""
    import unicodedata
    # no NFKC here: it would turn '²' into '2' and '½' into '1⁄2' before _UNICODE_MAP runs
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cf")


# ---- a factor written next to a divisor (final attack G4YO-2) --------------------------------------------------------
# '1/2π', '1/2√x', 'x/2π': read left to right it is (1/2)·π, read as many textbooks write it (and as latex2sympy reads
# '1/2\pi') it is 1/(2π). Which one is meant is the writer's convention, so such a text is read neither way: the
# canonical branch makes no product of it (`preclean` leaves '1/2pi', which no parse takes, as the ASCII '1/2pi' always
# was), the LaTeX branch refuses it (`_latex_to_sympy`), and the verifier names it (`ambiguous_juxtaposition`). An
# explicit operator (1/2·π, 1/2 \cdot \pi), parentheses ((1/2)π, 1/(2π)) and \frac are read as before.

def _atom_start(s: str, j: int) -> int | None:
    """The index where the canonical operand atom ending at `s[j]` starts: a run of letters, digits, '_' and '.' (2, 2.5,
    x2), or a bracket group with the function name before it (sqrt(2), (x + 1)); None when `s[j]` ends no atom."""
    if s[j] in ")]":
        depth, k = 0, j
        while k >= 0:
            if s[k] in ")]":
                depth += 1
            elif s[k] in "([":
                depth -= 1
                if depth == 0:
                    break
            k -= 1
        if k < 0:
            return None
    elif s[j].isalnum() or s[j] in "_.":
        k = j
    else:
        return None
    while k > 0 and (s[k - 1].isalnum() or s[k - 1] in "_."):
        k -= 1
    return k


def _closes_divisor(s: str, i: int) -> bool:
    """Does `s[i]` (a digit or a closing bracket a unicode value symbol follows) end the right operand of a '/' (or
    '÷') in the canonical text `s`? The operand is an atom (`_atom_start`) with a root sign before it and powers after
    it (√2, 2^3, (x + 1)**2), and a sign (1/-2π)."""
    j = i
    while True:
        k = _atom_start(s, j)
        if k is None:
            return False
        k -= 1
        while k >= 0 and s[k] in "√∛":
            k -= 1
        while k >= 0 and s[k].isspace():
            k -= 1
        if k >= 0 and s[k] == "^":
            j = k - 1
        elif k >= 1 and s[k - 1:k + 1] == "**":
            j = k - 2
        else:
            break
        while j >= 0 and s[j].isspace():
            j -= 1
        if j < 0:
            return False
    if k >= 0 and s[k] in _SIGNS:
        k -= 1
        while k >= 0 and s[k].isspace():
            k -= 1
    return k >= 0 and s[k] in "/÷"


def _juxtaposed_product(m) -> str:
    """`_UNI_VALUE_RE`'s product of a digit (or a bracket) and a value symbol, except after a divisor (G4YO-2)."""
    if _closes_divisor(m.string, m.start(1)):
        return m.group(0)
    return f"{m.group(1)}*{m.group(2)}"


# LaTeX macros that start no factor: operators, relations, spacing, closing delimiters, prose
_LATEX_NO_FACTOR = frozenset({
    "cdot", "times", "div", "pm", "mp", "ast", "le", "leq", "leqslant", "ge", "geq", "geqslant", "ne", "neq", "lt", "gt",
    "approx", "equiv", "sim", "simeq", "cong", "to", "rightarrow", "Rightarrow", "leftarrow", "Leftarrow",
    "leftrightarrow", "Leftrightarrow", "iff", "implies", "in", "notin", "ni", "cup", "cap", "setminus", "land", "lor",
    "wedge", "vee", "neg", "lnot", "right", "rbrace", "rangle", "rfloor", "rceil", "rvert", "rVert", "end", "quad",
    "qquad", "mid", "colon", "dots", "ldots", "cdots", "text", "textrm", "mbox", "circ", "degree", "%"})
# LaTeX function macros: the atom after one is its argument (1/\sin x is 1/sin(x), no product)
_LATEX_FUNCTIONS = frozenset({
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "arccot", "sinh", "cosh", "tanh", "coth",
    "log", "ln", "lg", "exp"})
# LaTeX macros with braced arguments: how many
_LATEX_ARGS = {"sqrt": 1, "frac": 2, "dfrac": 2, "tfrac": 2, "binom": 2, "dbinom": 2, "tbinom": 2, "mathrm": 1,
               "operatorname": 1, "mathbb": 1, "overline": 1, "bar": 1, "hat": 1, "vec": 1}
_LATEX_SPACE = re.compile(r"(?:\s|~|\\[,;:! ])*")
_LATEX_MACRO = re.compile(r"\\([A-Za-z]+)")


_LATEX_LEFT = re.compile(r"\\left(?![A-Za-z])")
_LATEX_RIGHT = re.compile(r"\\right(?![A-Za-z])")


def _latex_delimiter_end(s: str, k: int) -> int | None:
    """The index after the delimiter at `s[k]` that follows \\left or \\right ('(', '.', '\\{', '\\rangle')."""
    if k >= len(s):
        return None
    if s[k] != "\\":
        return k + 1
    m = _LATEX_MACRO.match(s, k)
    return m.end() if m is not None else (k + 2 if k + 1 < len(s) else None)


def _latex_group_end(s: str, j: int) -> int | None:
    """The index after the bracket group opening at `s[j]` ('(', '[', '{'), or after '\\left<d> ... \\right<d>'."""
    if _LATEX_LEFT.match(s, j):
        depth, k = 0, j
        while k < len(s):
            if _LATEX_LEFT.match(s, k):
                depth += 1
                k += 5
            elif _LATEX_RIGHT.match(s, k):
                depth -= 1
                k += 6
                if depth == 0:
                    return _latex_delimiter_end(s, k)
            else:
                k += 1
        return None
    close = {"(": ")", "[": "]", "{": "}"}.get(s[j])
    if close is None:
        return None
    depth, k = 0, j
    while k < len(s):
        if s[k] == "\\":
            k += 2
            continue
        if s[k] == s[j]:
            depth += 1
        elif s[k] == close:
            depth -= 1
            if depth == 0:
                return k + 1
        k += 1
    return None


def _latex_atom_end(s: str, j: int) -> int | None:
    """The index after the LaTeX atom starting at `s[j]` (a number, a letter, a constant or a macro with its arguments,
    a bracket group), its powers and subscripts after it; None when none starts there."""
    if j >= len(s):
        return None
    c = s[j]
    if c.isdigit() or c == ".":
        k = j
        while k < len(s) and (s[k].isdigit() or s[k] == "."):
            k += 1
    elif c.isalpha():
        k = j + 1
    elif c in "({[" or _LATEX_LEFT.match(s, j):
        k = _latex_group_end(s, j)
    elif c == "\\":
        m = _LATEX_MACRO.match(s, j)
        if m is None or m.group(1) in _LATEX_NO_FACTOR:
            return None
        k = m.end()
        name = m.group(1)
        if name in _LATEX_ARGS:
            k = k + len(_LATEX_SPACE.match(s, k).group(0))
            if k < len(s) and s[k] == "[":
                k = _latex_group_end(s, k)
            for _ in range(_LATEX_ARGS[name]):
                if k is None:
                    return None
                k = k + len(_LATEX_SPACE.match(s, k).group(0))
                k = _latex_group_end(s, k) if k < len(s) and s[k] == "{" else (k + 1 if k < len(s) else None)
        elif name in _LATEX_FUNCTIONS:
            k = k + len(_LATEX_SPACE.match(s, k).group(0))
            if k < len(s) and s[k] == "^":            # \sin^2 x
                k = _latex_atom_end(s, k + 1)
                if k is None:
                    return None
                k = k + len(_LATEX_SPACE.match(s, k).group(0))
            k = _latex_atom_end(s, k)                 # its argument
    else:
        return None
    while k is not None and k < len(s) and s[k] in "^_":
        k = k + 1 + len(_LATEX_SPACE.match(s, k + 1).group(0))
        k = _latex_group_end(s, k) if k < len(s) and s[k] == "{" else _latex_atom_end(s, k)
    return k


# signs before a divisor's operand: ASCII and the Unicode minus, en and em dashes (audit SA-YO-4: '1/−2π')
_SIGNS = "+-−–—"
# a unit mark on a divisor's operand in LaTeX: 1/2\%, 180/2^\circ, 180/2^{\circ}, 180/2\degree (audit SA-YO-4)
_LATEX_UNIT_AFTER = re.compile(r"(?:\d+(?:\.\d+)?|[A-Za-z]|\{[^{}]*\}|\([^()]*\))\s*"
                               r"(?:\^\s*\{?\s*\\circ\s*\}?|\\degree(?![A-Za-z])|\\%|%)")
# what ends a function's argument written without brackets
_LATEX_ARGUMENT_END = frozenset({"cdot", "times", "div", "pm", "mp", "le", "leq", "leqslant", "ge", "geq", "geqslant",
                                 "ne", "neq", "lt", "gt", "approx", "equiv", "to", "in", "notin", "cup", "cap", "right",
                                 "rbrace", "rangle", "rfloor", "rceil", "end", "quad", "qquad", "text", "mbox", "mid",
                                 "land", "lor", "wedge", "vee", "implies", "iff"})
# a factor of its own: after the argument's first item it is no part of the argument, as latex2sympy reads it
# (\sin x \sqrt{2} is sin(x)·√2; audit of the second round, RK-T2-1, YO-T2-3)
_LATEX_FACTOR_MACROS = frozenset({"sqrt", "frac", "dfrac", "tfrac", "binom", "dbinom", "tbinom", "mathrm", "operatorname",
                                  "mathbb", "overline", "bar", "hat", "vec", "int", "iint", "oint", "sum", "prod", "lim"})
_NUMERIC_GROUP = re.compile(r"\{\s*\d+(?:\.\d+)?\s*\}")
_NUMERIC_FRAC = re.compile(r"\\[dt]?frac\s*\{\s*\d+(?:\.\d+)?\s*\}\s*\{\s*\d+(?:\.\d+)?\s*\}")


def _latex_script_end(s: str, j: int) -> int | None:
    """The index after the power or subscript at `s[j]` ('^' or '_'): a braced group, a macro with its arguments
    (^\\circ too) or one character."""
    k = j + 1 + len(_LATEX_SPACE.match(s, j + 1).group(0))
    if k >= len(s):
        return None
    if s[k] == "{":
        return _latex_group_end(s, k)
    if s[k] == "\\":
        m = _LATEX_MACRO.match(s, k)
        if m is None:
            return k + 2 if k + 1 < len(s) else None
        return (_latex_atom_end(s, k) if m.group(1) not in _LATEX_NO_FACTOR else None) or m.end()
    return k + 1


def _bar_group_end(s: str, j: int) -> int | None:
    """The index after the '|...|' group opening at `s[j]`."""
    k = s.find("|", j + 1)
    return None if k < 0 else k + 1


def _function_argument(s: str, m) -> tuple[int, int, str] | None:
    """The argument of the LaTeX function macro matched by `m` when it is written without brackets, its base and power
    skipped (\\log_2 8, \\sin^2 x): (start, end, how it ends); None when it is bracketed ((x), \\left(x\\right)) or empty.
    It is a term: numbers, letters and constants (2x, 3\\pi, x y) with their powers, subscripts, braced groups and
    factorials; a fraction, a root or a bracket group only as its first item, a bracket group after a number too
    ('\\sin 2(x + 1)' is sin(2(x + 1)), '\\ln 2|x|' ln(2|x|): latex2sympy's reading and the A sin B(x - C) of the
    textbook; YO-T2-1). How it ends:
      'op'     at an operator or a relation (+, -, =, ',', \\cdot, \\times, ...), a closing bracket, the next function
               macro or the end: the argument is read to the first operator (EK 3)
      'slash'  at a '/' (\\ln 2/2: (ln 2)/2 or ln(2/2)? `_latex_divisor_juxtaposed`)
      'factor' before a factor of its own written right after it (e^x, \\sqrt{2}, \\frac{..}{..}): no part of it, as
               latex2sympy reads it (\\sin x e^x is sin(x)·e^x; RK-T2-1, YO-T2-3)
      'group'  before a bracket or '|...|' group right after a term with a letter (\\tan x(1 + \\tan^2 x): tan(x)·(1 +
               tan²x) in the textbook, tan(x(1 + tan²x)) for latex2sympy): a convention of the writer (RK-T2-3)."""
    sp_ = lambda i: i + len(_LATEX_SPACE.match(s, i).group(0))  # noqa: E731
    k = sp_(m.end())
    while k is not None and k < len(s) and s[k] in "_^":
        k = sp_(k + 1)
        k = _latex_group_end(s, k) if k < len(s) and s[k] == "{" else _latex_atom_end(s, k)
        k = None if k is None else sp_(k)
    if k is None or k >= len(s) or s[k] == "(" or _LATEX_LEFT.match(s, k):
        return None
    j = last = k
    numeric = True                               # the term so far is a number
    stop = "op"
    while True:
        j = sp_(j)
        if j >= len(s):
            break
        c = s[j]
        if c == "/":
            stop = "slash"
            break
        if c in ")]}&=<>,;:+*" or c in _SIGNS:
            break
        if c == "!":
            j = last = j + 1
            continue
        if c in "^_":
            e = _latex_script_end(s, j)
            if e is None:
                return None
            j = last = e
            continue
        if c.isdigit() or c == ".":
            while j < len(s) and (s[j].isdigit() or s[j] == "."):
                j += 1
            last = j
            continue
        if c.isalpha():
            if c == "e" and last > k and s[sp_(j + 1):sp_(j + 1) + 1] == "^":
                stop = "factor"                  # e^x
                break
            j = last = j + 1
            numeric = False
            continue
        if c == "{":
            e = _latex_group_end(s, j)
            if e is None:
                return None
            numeric = numeric and bool(_NUMERIC_GROUP.fullmatch(s, j, e))
            j = last = e
            continue
        if c in "([|" or _LATEX_LEFT.match(s, j):
            if last > k and not numeric:
                stop = "group"
                break
            e = _bar_group_end(s, j) if c == "|" else _latex_group_end(s, j)
            if e is None:
                return None
            j = last = e
            numeric = False
            continue
        if c == "\\":
            mm = _LATEX_MACRO.match(s, j)
            if mm is None:
                break                            # \{, \|, \\: a delimiter
            name = mm.group(1)
            if name in _LATEX_ARGUMENT_END or name in _LATEX_FUNCTIONS or name in _LATEX_NO_FACTOR:
                break
            if name in _LATEX_FACTOR_MACROS:
                if last > k:
                    stop = "factor"
                    break
                e = _latex_atom_end(s, j)
                if e is None:
                    return None
                numeric = bool(_NUMERIC_FRAC.fullmatch(s, j, e))
                j = last = e
                continue
            j = last = mm.end()                  # a constant or a letter: \pi, \theta, \infty
            numeric = False
            continue
        break
    return (k, last, stop) if last > k else None


def _function_arguments(s: str) -> list[tuple[int, int, str]]:
    """`_function_argument` of every LaTeX function macro of `s` whose argument is written without brackets."""
    return [a for m in _LATEX_MACRO.finditer(s) if m.group(1) in _LATEX_FUNCTIONS
            for a in [_function_argument(s, m)] if a is not None]


def _bracket_spans(s: str, spans) -> str:
    """`s` with each span (start, end, ...) put in \\left( ... \\right), an inner one inside its outer one: inserted
    one after another from the right, an inner span shifted the outer's end and '\\left' was cut in two
    (\\cos x e^{\\sin x}; audit of the second round, RK-T2-2)."""
    events = []
    for a in spans:
        events.append((a[0], 1, -a[1], "\\left("))       # at one place: the closings first, the longer opening first
        events.append((a[1], 0, -a[0], "\\right)"))      # ... the inner closing first
    out, i = [], 0
    for pos, _, _, text in sorted(events, key=lambda t: t[:3]):
        out.append(s[i:pos])
        out.append(text)
        i = pos
    out.append(s[i:])
    return "".join(out)


def _latex_argument_ambiguous(s: str) -> bool:
    """Is a function's argument written without brackets followed by a bracket group after a letter (`_function_argument`
    'group': \\tan x(1 + \\tan^2 x)), or by a factor latex2sympy does not read as a factor of its own? A reading of the
    argument other than latex2sympy's is taken only where the decision (EK 3: to the first operator) gives it; anywhere
    else the two must agree, or the text is read neither way (audit of the second round, YO-T2-1, YO-T2-3)."""
    spans = _function_arguments(s)
    if any(a[2] == "group" for a in spans):
        return True
    if not any(a[2] == "factor" for a in spans):
        return False
    try:
        return _latex2sympy(_latex_prepared(_bracket_spans(s, [a for a in spans if a[2] != "slash"]))) != \
            _latex2sympy(_latex_prepared(_bracket_spans(s, [a for a in spans if a[2] == "op"])))
    except Exception:  # noqa: BLE001 - not read either way: no reading is taken
        return True


def _bracket_function_arguments(s: str) -> str:
    """`s` with each function argument written without brackets (`_function_argument`) bracketed: latex2sympy took a
    product after it into the argument, \\sin x \\cdot \\cos x was sin(x*cos(x)) and \\sin x \\cdot 3 was sin(3x); the
    argument is read up to the first operator (audit SA-YO-3, SA-RK-4: the decision's reading). An argument a factor
    follows is bracketed as latex2sympy reads it (`_latex_argument_ambiguous` refuses the text otherwise)."""
    spans = [a for a in _function_arguments(s) if a[2] in ("op", "factor")]
    return _bracket_spans(s, spans) if spans else s


def _latex_divisor_juxtaposed(s: str) -> bool:
    """Does a LaTeX text write a factor (a unit mark included: \\%, ^\\circ) right after the operand of a '/' (1/2\\pi,
    x/2\\pi, 3/4\\sqrt{2}, \\pi/2x, 1/2\\%, 180/2^\\circ), or a '/' inside a function's argument written without brackets
    (\\ln 2/2, \\sin x/2, \\log_2 8/3, `_function_argument_divides`)?"""
    for p in [m.start() for m in re.finditer(r"(?<!\\)/", s)]:
        j = p + 1 + len(_LATEX_SPACE.match(s, p + 1).group(0))
        if j < len(s) and s[j] in _SIGNS:
            j += 1 + len(_LATEX_SPACE.match(s, j + 1).group(0))
        if _LATEX_UNIT_AFTER.match(s, j):
            return True
        end = _latex_atom_end(s, j)
        if end is None:
            continue
        k = end + len(_LATEX_SPACE.match(s, end).group(0))
        if k < len(s) and (s[k].isalpha() or s[k] in "({√∛∞" or _LATEX_LEFT.match(s, k)):
            return True
        if k < len(s) and s[k] == "\\":
            m = _LATEX_MACRO.match(s, k)
            if m is not None and m.group(1) not in _LATEX_NO_FACTOR:
                return True
    # the dual: a function's argument written without brackets holding a '/' (\ln 2/2: (ln 2)/2 or ln(2/2)?);
    # latex2sympy took the division into the argument, \ln{2}/2 too, and read 0 for (ln 2)/2 (sibling of G4YO-2)
    return any(a[2] == "slash" for a in _function_arguments(s))


def ambiguous_juxtaposition(text) -> bool:
    """Does `text` write a factor right after the operand of a division, with no operator ('1/2π', '1/2√x', 'x/2π',
    '$1/2\\pi$'), a unit mark included ('1/2%', '180/2°')? It reads (1/2)·π left to right and 1/(2π) as the textbooks
    write it: it is read neither way (G4YO-2)."""
    if not isinstance(text, str):
        return False
    t = strip_presentation(_strip_invisible(text))
    if is_latex(t):
        return _latex_divisor_juxtaposed(t) or _latex_argument_ambiguous(t)
    return any(_closes_divisor(m.string, m.start(1)) for m in _UNI_VALUE_RE.finditer(t)) \
        or any(_closes_divisor(m.string, m.end(1)) for m in _DEG_PAREN_RE.finditer(t)) \
        or any(_closes_divisor(m.string, m.end(1) - 1) for m in _DEG_NUM_RE.finditer(t)) \
        or any(m.group(2) and _closes_divisor(m.string, m.end(2) - 1) for m in _PCT_RE.finditer(t))


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
    s = _UNI_VALUE_RE.sub(_juxtaposed_product, s)
    for k, v in _UNICODE_MAP.items():
        s = s.replace(k, v)
    # a unit mark is a factor too: 1/2% is not 1/(2/100) = 50, 180/2° not 180/(2°) (sibling of G4YO-2)
    s = _DEG_PAREN_RE.sub(lambda m: m.group(0) if _closes_divisor(m.string, m.end(1)) else f"(({m.group(1)})*pi/180)", s)
    s = _DEG_NUM_RE.sub(lambda m: m.group(0) if _closes_divisor(m.string, m.end(1) - 1) else f"(({m.group(1)})*pi/180)", s)
    s = _PCT_RE.sub(lambda m: m.group(0) if m.group(2) and _closes_divisor(m.string, m.end(2) - 1)
                    else f"(({m.group(1) or m.group(2)})/100)", s)
    s = _SQRT_BARE_RE.sub(r"\1(\2)", s)            # "sqrt 3" -> sqrt(3), "∛8" -> cbrt(8)
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
# A Limit, at() and Subs bind their variable too: see `_rebind_point_dummies`.
_RANGE_BINDERS = ("Sum", "Product", "Integral", "integrate")


def _binds_range(obj) -> bool:
    """SymPy's range binders, or a callable that says it builds one: the step namespace keeps an
    Integral unevaluated through its own function, and `compute` claims were not rebound (audit of
    29 Sep 2026: the wrong step "Integral(Abs(x), (x, -1, 1)) = 0" stayed verified)."""
    return any(obj is b for b in (sp.Sum, sp.Product, sp.Integral, sp.integrate)) \
        or getattr(obj, "binds_range", False) is True


def _bare_name(node):
    """The Name a binder's variable is written as (`+k` is k), or None."""
    while isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        node = node.operand
    return node if isinstance(node, ast.Name) else None


def _limit_var(lim) -> str | None:
    """The name a limit binds: the k of (k, a, b), [k, a, b], (+k, a, b), (k,) or a bare k."""
    if isinstance(lim, ast.Name):
        return lim.id
    if isinstance(lim, (ast.Tuple, ast.List)) and lim.elts and _bare_name(lim.elts[0]) is not None:
        return _bare_name(lim.elts[0]).id
    return None


def _check_limit_syntax(call: ast.Call, raw: str) -> None:
    """A range binder's limits are written (variable, lower, upper), its variable as a name; an
    integral also takes a bare variable or (variable,) (indefinite). Anything else reached SymPy as a
    binding the renaming did not see, so the IR's assumptions leaked into it: with k positive,
    `Sum(0**k, (k,) + (0, 3))` and `Sum(0**k, (1*k, 0, 3))` were 0 (true 1); or it is a notation no
    school text has: `Integral(f, (x, 1))` is an antiderivative evaluated at 1, `(x, 0, 1, 2)`
    SymPy's substitution form (audit of V14, 30 Sep 2026). They are not read."""
    name = call.func.id
    integral = name in ("Integral", "integrate")
    for lim in call.args[1:]:
        if isinstance(lim, ast.Name) and integral:
            continue
        if isinstance(lim, (ast.Tuple, ast.List)) and (len(lim.elts) == 3 or (integral and len(lim.elts) == 1)) \
                and _bare_name(lim.elts[0]) is not None:
            continue
        raise ParseError(f"{raw!r}: the limits of {name} must be written (variable, lower, upper): not read")


# A bound that is itself an operation: SymPy asks the assumptions of each bound while it builds the
# binder (and so does every function around it, Abs or floor), and each question re-evaluates the
# inner operation: Sum(k, (k, -1, Sum(k, (k, -1, ...)))) nested four deep took 86 s to parse and
# Abs of it three deep 32 s (audit and review of V14, 30 Sep 2026). Refused before anything is built.
_BOUND_OPERATIONS = frozenset({"Sum", "Product", "Integral", "integrate", "Limit", "limit", "diff",
                               "Derivative", "Subs", "at"})


def _literal_number(node, depth: int = 0) -> Fraction | None:
    """The exact value of a bound written with numbers only (Integer(3), -Integer(1), 10**3, 7/2),
    or None. Read from the code, before SymPy builds anything, and in Python's own fractions: the
    as-written reading runs with SymPy's evaluation off."""
    if depth > 30:
        return None
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return Fraction(node.value)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("Integer", "Rational") \
            and not node.keywords and 1 <= len(node.args) <= 2:
        vals = [_literal_number(a, depth + 1) for a in node.args]
        if any(v is None or v.denominator != 1 for v in vals) or (len(vals) == 2 and vals[1] == 0):
            return None
        return vals[0] if len(vals) == 1 else vals[0] / vals[1]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _literal_number(node.operand, depth + 1)
        return None if v is None else (-v if isinstance(node.op, ast.USub) else v)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
        a, b = _literal_number(node.left, depth + 1), _literal_number(node.right, depth + 1)
        if a is None or b is None:
            return None
        if isinstance(node.op, ast.Pow):
            if b.denominator != 1 or abs(b) > 64 or abs(a) > 10**6 or (a == 0 and b < 0):
                return None
            return a ** int(b)
        if isinstance(node.op, ast.Div):
            return None if b == 0 else a / b
        return a + b if isinstance(node.op, ast.Add) else a - b if isinstance(node.op, ast.Sub) else a * b
    return None


def _constant_bound(node, names: dict[str, Any]):
    """The value of a bound written as a constant that is not a plain number (sqrt(1), exp(0), pi - 2),
    evaluated on its own in the namespace the whole code is evaluated in (the code is already checked);
    None when it names a symbol or has no numeric value."""
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and (n.id not in names or isinstance(names[n.id], sp.Basic)
                                        and getattr(names[n.id], "free_symbols", None)):
            return None
    try:
        v = sympify_nontext(eval(compile(ast.Expression(body=node), "<bound>", "eval"),  # noqa: S307
                                 {"__builtins__": {}}, dict(names)))
        # evaluated whatever the caller's setting: read as written (evaluation off) a bound in nested roots
        # equal to 1/2 was "not an integer" for certain, the as-written reading refused the text and every
        # condition around it was lost (x/x at the given x = 0, review of d4f, YO-1)
        v = _evaluated_bound(v)
    except Exception:  # noqa: BLE001 - the whole parse reports it
        return None
    return v if isinstance(v, sp.Expr) and v.is_number and not v.free_symbols else None


def _refuse_constant_range(name: str, lo, hi, raw: str) -> None:
    """The checks of `_refuse_reversed_ranges` on bounds known before SymPy builds the binder. Computed with
    SymPy's evaluation on: read as written (evaluation off), 1 - 3 + 1 stayed a sum of unknown sign and the
    reversed range \\sum_{j_{0}=3}^{1} was not refused there."""
    with sp.evaluate(True):
        if (hi - lo + 1).is_extended_negative is True:
            raise ParseError(f"{raw!r} has a {name} over a reversed range: not read")
        span = hi - lo
        if span.is_number and span.is_finite and span.is_integer is False:
            raise ParseError(f"{raw!r} has a {name} whose limits are not an integer apart: not read")
        if any(_not_an_integer(b) for b in (lo, hi)):
            raise ParseError(f"{raw!r} has a {name} whose limits are not integers: not read")


def _not_an_integer(b) -> bool:
    """Is the finite number `b` certainly not an integer? A Sum/Product with such a limit has no index
    reading: Σ_{k=1/2}^{5/2} k is 9/2 stepping from the lower limit (SymPy) and 1 + 2 = 3 over the integers
    between the limits; 9/2 was certified and 3 refuted (fourth audit TAN-10/C1). A limit it cannot decide
    is the domain's (`certify.domain._one_range_conditions`)."""
    return isinstance(b, sp.Expr) and b.is_number is True and b.is_finite is True and b.is_integer is False


def _refuse_computed_bounds(code: str, raw: str, names: dict[str, Any] | None = None) -> None:
    """Also the range checks of `_refuse_reversed_ranges` for bounds written with numbers, here, before
    SymPy builds the expression: a function around a Sum computes it at once (floor, ceiling), and
    floor(Sum(k, (k, 3, 1))) = -2 (Karr) was certified past the later refusal (review of V14,
    30 Sep 2026). A bound that is a constant written otherwise (sqrt(1), exp(0)) is evaluated on its own
    first: floor(Sum(k, (k, 3, sqrt(1)))) = -2 was certified the same way (V16, 30 Sep 2026)."""
    try:
        tree = ast.parse(code, mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return                                    # parse_expr reports it
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _RANGE_BINDERS):
            continue
        for lim in node.args[1:]:
            if not isinstance(lim, (ast.Tuple, ast.List)):
                continue
            for b in lim.elts[1:]:
                if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _BOUND_OPERATIONS
                       for n in ast.walk(b)):
                    raise ParseError(f"{raw!r} has a {node.func.id} whose limit is itself an operation: not read")
            if node.func.id in ("Sum", "Product") and len(lim.elts) == 3:
                lo, hi = _literal_number(lim.elts[1]), _literal_number(lim.elts[2])
                if lo is None or hi is None:
                    if names is not None:
                        lo_c, hi_c = [(sp.Rational(v.numerator, v.denominator) if v is not None
                                       else _constant_bound(b, names)) for v, b in ((lo, lim.elts[1]), (hi, lim.elts[2]))]
                        if lo_c is not None and hi_c is not None:
                            _refuse_constant_range(node.func.id, lo_c, hi_c, raw)
                    continue
                if hi - lo + 1 < 0:
                    raise ParseError(f"{raw!r} has a {node.func.id} over a reversed range: not read")
                if (hi - lo).denominator != 1:
                    raise ParseError(f"{raw!r} has a {node.func.id} whose limits are not an integer apart: "
                                     "not read")
                if lo.denominator != 1 or hi.denominator != 1:
                    raise ParseError(f"{raw!r} has a {node.func.id} whose limits are not integers: not read")


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
        _check_limit_syntax(node, raw)
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
        for sub in mine + [_bare_name(lim.elts[0])]:
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


# Binders of a POINT: the variable of a limit approaches its point, the variable of at()/Subs is
# evaluated at it. Read with the IR symbol of the same name, the body took that symbol's declaration
# before the point was even seen: with x declared positive, sqrt(x**2)/x was 1, so
# Limit(sqrt(x**2)/x, x, -oo) = 1, Limit(Abs(x)/x, x, 0, '-') = 1 and at(sqrt(x**2), x, -1) = -1
# were certified CORRECT, and the compute step "at(sqrt(x**2), x, -1) = -1" was verified. The IR
# symbol as a Limit's variable was also reached by every substitution of it (SymPy's Limit.subs
# rewrites its variable: Limit(Abs(x)/x, x, 0).subs(x, 5) is Limit(1, 5, 0)), so the eq step
# "x*Limit(Abs(x)/x, x, 0) = x" was verified at the premises' point x = 5 (V14, 30 Sep 2026).
# ConditionSet binds its variable over its base set: with x positive, ConditionSet(x, x < 0, Reals)
# was the empty set.
_POINT_BINDERS = ("Limit", "limit", "at", "Subs", "ConditionSet")
# the argument positions of (variable, body, point); a ConditionSet's "point" is its base set
_POINT_LAYOUT = {"Limit": (1, 0, 2), "limit": (1, 0, 2), "at": (1, 0, 2), "Subs": (1, 0, 2),
                 "ConditionSet": (0, 1, 2)}
_LIMIT_SIDE_KEYWORDS = frozenset({"dir", "d"})
# a point written with one of these is not evaluated to decide the facts of the variable (it would
# be computed twice, and an unevaluated operation answers an assumption query by recomputing it)
_NO_FACT_CALLS = frozenset(COMPUTING_OPERATORS) | frozenset(_POINT_BINDERS) | frozenset(_RANGE_BINDERS)
_POINT_OPERATIONS = (sp.Sum, sp.Product, sp.Integral, sp.Limit, sp.Derivative, sp.Subs)
_POINT_DUMMIES: dict[tuple[str, frozenset], sp.Dummy] = {}
_POINT_DUMMIES_LOCK = threading.Lock()


def _binds_point(obj) -> bool:
    """SymPy's point binders, this module's, or a callable that says it builds one (the step
    namespace's unevaluated `Limit` and `at`)."""
    return any(obj is b for b in (_Limit, _limit, _at, sp.Limit, sp.limit, sp.Subs, sp.ConditionSet)) \
        or getattr(obj, "binds_point", False) is True


def _point_dummy(name: str, facts: frozenset) -> sp.Dummy:
    """THE bound variable of this name and these facts: one Dummy per pair, so two readings of one
    binder are the same expression, and never the IR's Symbol, which a substitution would reach."""
    key = (name, frozenset(facts))
    with _POINT_DUMMIES_LOCK:
        d = _POINT_DUMMIES.get(key)
        if d is None:
            d = _POINT_DUMMIES[key] = sp.Dummy(name, **{f: True for f in sorted(key[1])})
    return d


def _point_facts(kind: str, declared, p, side) -> frozenset:
    """The facts the bound variable has near its point `p` (a value, or None when it was not
    evaluated). A limit at oo keeps the declaration (an integer n makes it the limit of a sequence:
    sin(pi*n) -> 0, which as a function has none); at -oo only integrality; at a real point the
    variable is real, and positive when the point is positive or it is 0 approached from the right.
    at()/Subs: real at a real point, positive at a positive one (a neighbourhood: a derivative there
    is two-sided). ConditionSet: real over a set of reals, integer over a set of integers. Anything
    else: no fact at all, the most general reading."""
    if p is None or isinstance(p, (str, bytes)):
        return frozenset()
    try:
        with sp.evaluate(True):
            p = sympify_nontext(p)
            if p.has(*_POINT_OPERATIONS):
                return frozenset()
            if kind == "ConditionSet":
                if not isinstance(p, sp.Set) or p.is_subset(S.Reals) is not True:
                    return frozenset()
                return frozenset({"real", "integer"} if p.is_subset(S.Integers) is True else {"real"})
            if kind in ("Limit", "limit"):
                if p == oo:
                    return frozenset({"real"} | {f for f in ("integer", "positive", "nonnegative")
                                                 if getattr(declared, f"is_{f}", None) is True})
                if p == -oo:
                    return frozenset({"real"} | ({"integer"} if getattr(declared, "is_integer", None) is True
                                                 else set()))
                if p.is_real is not True:
                    return frozenset()
                # at the closed end 0 of a nonnegative declared variable an undirected limit is the
                # limit over the domain, as the limit task reads it (`_domain_end_limits`)
                right = p.is_positive is True or (p.is_zero is True and (side == "+" or (
                    side in (None, "+-") and getattr(declared, "is_nonnegative", None) is True)))
                return frozenset({"real", "positive"} if right else {"real"})
            if p.is_real is not True:
                return frozenset()
            return frozenset({"real", "positive"} if p.is_positive is True else {"real"})
    except Exception:  # noqa: BLE001 - no decision: the variable then has no fact
        return frozenset()


def _rebind_point_dummies(code: str, local_dict: dict[str, Any], global_dict: dict[str, Any], raw: str,
                          names) -> tuple[str, dict[str, Any]] | None:
    """`code` with the variable of every Limit, limit, at, Subs and ConditionSet renamed, inside its body only, to
    a fresh name for the bound variable (`_point_dummy`) with the facts of its point; None when there
    is nothing to rename. The point and the side are read in the enclosing scope. A binder inside
    another of the same name is refused. A variable that is not written as a name bound to a symbol
    (`at(x**2, 2*x, 1)`, `Subs(f, (x,), (1,))`, `Limit(f, Symbol('x'), 0)`), or that is passed by
    keyword, is refused: it would be read as the IR's symbol or as a substitution of an expression."""
    try:
        tree = ast.parse(code, mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None                               # parse_expr reports it
    nodes = list(ast.walk(tree))
    bindings: list[tuple[ast.Call, ast.Name, str]] = []
    for node in nodes:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _POINT_BINDERS
                and _binds_point(local_dict.get(node.func.id))):
            continue
        kind = node.func.id
        allowed = _LIMIT_SIDE_KEYWORDS if kind in ("Limit", "limit") else frozenset()
        if any(kw.arg not in allowed for kw in node.keywords):
            raise ParseError(f"{raw!r} passes an argument of {kind} by keyword: not read")
        iv, ib, ip = _POINT_LAYOUT[kind]
        if len(node.args) <= max(iv, ib) or (kind != "ConditionSet" and len(node.args) <= ip):
            continue                              # SymPy refuses it
        var = _bare_name(node.args[iv])
        if var is None or not isinstance(local_dict.get(var.id), Symbol):
            raise ParseError(f"{raw!r}: the variable of {kind} is not written as a variable: not read")
        bindings.append((node, var, var.id))
    if not bindings:
        return None
    # A binder inside the body of another of the same name is refused, as for the range binders: the
    # two share one bound variable when their facts agree, and the outer substitution then rewrote
    # the inner limit's variable (at(x + Limit(x/(x + 1), x, 5), x, 7) read as 7 + Limit(7/8, 7, 5),
    # review of 30 Sep 2026).
    calls = {id(c): v for c, _, v in bindings}
    for call, _, v in bindings:
        body = call.args[_POINT_LAYOUT[call.func.id][1]]
        if any(calls.get(id(n)) == v for n in ast.walk(body) if n is not call):
            raise ParseError(f"{raw!r} binds {v!r} inside a binder of the same name: not read")
    owner: dict[int, int] = {}                    # id(Name node) -> index of the binding it belongs to
    for bi in reversed(range(len(bindings))):
        call, var, v = bindings[bi]
        body = call.args[_POINT_LAYOUT[call.func.id][1]]
        for sub in [var] + [n for n in ast.walk(body) if isinstance(n, ast.Name) and n.id == v]:
            owner.setdefault(id(sub), bi)
    used = set(local_dict) | set(global_dict) | {n.id for n in nodes if isinstance(n, ast.Name)}
    fresh: list[str] = []
    for _, _, v in bindings:
        i = 0
        while f"_point_{v}_{i}" in used:
            i += 1
        used.add(f"_point_{v}_{i}")
        fresh.append(f"_point_{v}_{i}")
    edits = sorted(((n.lineno, n.col_offset, n.end_col_offset, fresh[owner[id(n)]])
                    for n in nodes if isinstance(n, ast.Name) and id(n) in owner), reverse=True)
    lines = code.encode("utf-8").split(b"\n")
    for lineno, start, end, new in edits:          # offsets are UTF-8 byte offsets of the line
        line = lines[lineno - 1]
        lines[lineno - 1] = line[:start] + new.encode("ascii") + line[end:]
    new_code = b"\n".join(lines).decode("utf-8")
    _check_code(new_code, raw, set(names) | set(fresh))
    # the same tree with the names replaced: its walk visits the nodes in the same order
    new_nodes = list(ast.walk(ast.parse(new_code, mode="eval")))
    if len(new_nodes) != len(nodes):
        raise ParseError(f"{raw!r}: the bound variables could not be renamed: not read")
    position = {id(n): i for i, n in enumerate(nodes)}
    dummies: dict[str, Any] = {}
    # outer binders first (ast.walk is breadth-first): a point may name an enclosing binder's variable
    for bi, (call, var, v) in enumerate(bindings):
        ip = _POINT_LAYOUT[call.func.id][2]
        point = new_nodes[position[id(call.args[ip])]] if len(call.args) > ip else None
        side = None
        if call.func.id in ("Limit", "limit") and len(call.args) > 3 and isinstance(call.args[3], ast.Constant):
            side = call.args[3].value
        for kw in call.keywords:
            if isinstance(kw.value, ast.Constant):
                side = kw.value.value
        value = None
        if point is not None and not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                                         and n.func.id in _NO_FACT_CALLS for n in ast.walk(point)):
            try:
                expr = compile(ast.fix_missing_locations(ast.Expression(body=point)), "<point>", "eval")
                with sp.evaluate(True):
                    value = eval(expr, dict(global_dict, __builtins__={}),  # noqa: S307 - checked above
                                 dict(local_dict, **dummies))
            except Exception:  # noqa: BLE001 - no decision: the variable then has no fact
                value = None
        declared = local_dict[v]                  # a Symbol (checked above), maybe a range dummy
        dummies[fresh[bi]] = _point_dummy(declared.name, _point_facts(call.func.id, declared, value, side))
    return new_code, dummies


# A derivative or an antiderivative IN a variable declared an integer. SymPy applies the declaration to
# the function before it differentiates or integrates (sin(pi*n) is 0 and cos(pi*n) is (-1)**n for an
# integer n): with n a positive integer, diff(sin(pi*n), n) was 0 (the derivative is pi*cos(pi*n), pi at
# n = 2) and diff(cos(pi*n), n) was I*pi*(-1)**n, so 0 and I*pi were certified at n = 2, pi was refuted,
# the limit of the "derivative" at oo was 0, the steps "diff(sin(pi*n), n) = 0" and
# "Integral(sin(pi*n), n) = 7" were verified, and so was the derivative in x of x*diff(sin(pi*n), n)
# (V17, franklin's completeness audit, DECISIONS §74). A derivative is taken in a real variable; one in
# a variable declared an integer is no question (the derivative, antiderivative, tangent and extremum
# certificates abstain on such a task variable, `variable_declared_integer`), and it is not read. at()
# and Subs bind their variable to a real dummy at a real point (`_point_facts`), a Sum/Integral with
# limits binds an assumption-free one (`_rebind_range_dummies`): at(diff(sin(pi*n), n), n, 1) stays
# readable. Checked by name on the code after that rebinding, on every variable argument (diff(f, x, n)
# differentiates in n too; the order of (x, n) is no variable) and, when none is written, on the body,
# whose only free symbol SymPy then takes (diff(sin(pi*n)) was 0 as well).
_DIFFERENTIATING = ("diff", "Derivative")
_ANTIDIFFERENTIATING = ("Integral", "integrate")


def _refuse_integer_calculus(code: str, local_dict: dict[str, Any], raw: str, rebound: bool) -> None:
    """Raise ParseError when `code` differentiates, or integrates indefinitely, in a variable
    `local_dict` declares an integer. `rebound=False` is the as-written reading, which keeps the
    declared symbols inside the binders: an operation nested in a binder is not judged there (the
    normal reading judges it with the binder's own variable), so this reading never refuses a text
    the normal reading reads, and never loses the conditions of one."""
    if not any(name in code for name in _DIFFERENTIATING + _ANTIDIFFERENTIATING):
        return
    try:
        tree = ast.parse(code, mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return                                    # parse_expr reports it
    nested: set[int] = set()
    if not rebound:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id in _POINT_BINDERS + _RANGE_BINDERS:
                nested.update(id(sub) for arg in node.args for sub in ast.walk(arg))
    seq = (ast.Tuple, ast.List)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)) or id(node) in nested:
            continue
        if node.func.id in _DIFFERENTIATING:
            spec = [a.elts[0] if isinstance(a, seq) and a.elts else a for a in node.args[1:]]
        elif node.func.id in _ANTIDIFFERENTIATING:
            # an indefinite integral: a bare variable or (variable,); (variable, lower, upper) binds a range
            spec = [a.elts[0] if isinstance(a, seq) else a for a in node.args[1:]
                    if not isinstance(a, seq) or len(a.elts) == 1]
            if len(node.args) > 1 and not spec:
                continue
        else:
            continue
        if len(node.args) == 1:
            spec = node.args[:1]
        for root in spec:
            for sub in ast.walk(root):
                v = local_dict.get(sub.id) if isinstance(sub, ast.Name) else None
                if isinstance(v, Symbol) and v.is_integer is True:
                    raise ParseError(f"{raw!r} takes {node.func.id} in {v.name!r}, a variable declared an "
                                     "integer: not read")


# Operations SymPy keeps unevaluated: asking an assumption of a bound that holds one rebuilds it, and
# Sum(k, (k, -1, Sum(k, (k, -1, ...)))) nested four deep took 86 s to parse (audit of V14, 30 Sep 2026).
_OPERATIONS = (sp.Sum, sp.Product, sp.Integral, sp.Limit, sp.Derivative, sp.Subs)


def _computed_bounds(lim) -> bool:
    return any(isinstance(b, sp.Basic) and b.has(*_OPERATIONS) for b in lim[1:])


def _assumed_integer(b) -> bool:
    """`b.is_integer` is True; asking it failed with SymPy's PolynomialError for log_3 3^4 held unevaluated (the
    LaTeX Σ_{k=1}^{\\log_3 3^4} k was not read as written, attack on d4f round 2, RK-3): not known then."""
    try:
        return b.is_integer is True
    except Exception:  # noqa: BLE001
        return False


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
                    or lim[0].assumptions0 != Symbol(lim[0].name).assumptions0 or _computed_bounds(lim):
                continue
            if all(b in (sp.oo, -sp.oo) or _assumed_integer(b) for b in lim[1:]):
                reps[lim[0]] = Symbol(lim[0].name, integer=True)
        return n.xreplace(reps) if reps else n

    def walk(e):
        # bottom up, as `replace` does; a floor or Max over the upgraded sum is rebuilt unevaluated: rebuilt
        # evaluated, evalf decided floor(Σ_{k≥1} 1/k²) at parse (`rebuilt`, review of part d4h)
        if not isinstance(e, sp.Basic) or not e.has(sp.Sum, sp.Product):
            return e
        args = [walk(a) for a in e.args]
        if any(a is not b for a, b in zip(args, e.args)):
            e = rebuilt(e, args)
        return upgrade(e) if isinstance(e, (sp.Sum, sp.Product)) else e
    return walk(expr)


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
                if isinstance(node, (sp.Sum, sp.Product)) and _computed_bounds(lim):
                    # whether the range is reversed (Karr) is not asked of a bound SymPy computes
                    raise ParseError(f"{raw!r} has a {type(node).__name__} whose limit is itself an "
                                     "operation: not read")
                if isinstance(node, (sp.Sum, sp.Product)) and len(lim) == 3:
                    # reversed (Karr), not an integer apart (Σ_{k=1}^{7/2} k is 63/8 stepping from the lower limit),
                    # not integers (Σ_{k=1/2}^{5/2} k: 9/2 stepping, 3 over the integers, TAN-10/C1), on the bounds
                    # evaluated, as the value reading has them: read as written sqrt(1) - 3 was "not an integer",
                    # and SymPy's sign of the unevaluated n - 5 - 1 + 1 raised; either refused the text (and every
                    # condition around it) in that reading alone (review of d4f, YO-1). A question SymPy cannot
                    # answer refuses nothing here: the domain reads the range (`certify.domain`).
                    with sp.evaluate(True):
                        lo, hi = _evaluated_bound(lim[1]), _evaluated_bound(lim[2])
                    try:
                        _refuse_constant_range(type(node).__name__, lo, hi, raw)
                    except ParseError:
                        raise
                    except Exception:  # noqa: BLE001 - see above
                        pass


def guarded_parse_expr(s: str, *, local_dict: dict[str, Any], global_dict: dict[str, Any],
                       transformations, evaluate: bool = True, rebind: bool = True,
                       rebind_points: bool | None = None):
    """parse_expr, after checking that the code it is about to evaluate is plain arithmetic.
    `rebind=False` keeps the declared symbols inside the range binders (the reading of definedness,
    see `parse_as_written`); `rebind_points` (default: `rebind`) binds the variable of a point binder
    (Limit, at, Subs, ConditionSet) to its own symbol all the same."""
    names = set(local_dict) | set(global_dict)
    code = stringify_expr(s, local_dict, global_dict, transformations)
    _check_code(code, s, names)
    binds_range = any(b in code for b in _RANGE_BINDERS)
    if binds_range:
        _refuse_computed_bounds(code, s, {**global_dict, **local_dict})
    rebound = _rebind_range_dummies(code, local_dict, s) if rebind and binds_range else None
    dummies: dict[str, Any] = {}
    if rebound is not None:
        code, dummies = rebound
        _check_code(code, s, names | set(dummies))
    if rebind_points is None:
        rebind_points = rebind
    pointed = _rebind_point_dummies(code, dict(local_dict, **dummies), global_dict, s, names | set(dummies)) \
        if rebind_points and any(b in code for b in _POINT_BINDERS) else None
    if pointed is not None:
        code, more = pointed
        dummies = dict(dummies, **more)
    _refuse_integer_calculus(code, dict(local_dict, **dummies), s, rebind)
    # with evaluation off parse_expr builds Add(a, b, evaluate=False) itself: no set operation runs
    routed = _route_set_arithmetic(code, {**global_dict, **local_dict, **dummies}) if evaluate else None
    if routed is not None:
        out = eval(routed, global_dict, {**local_dict, **dummies, **_SET_ARITHMETIC})  # noqa: S307 - checked code
    elif rebound is None and pointed is None:
        out = parse_expr(s, local_dict=local_dict, global_dict=global_dict,
                         transformations=transformations, evaluate=evaluate)
    else:
        # the code is already transformed: no transformation runs twice on it
        out = parse_expr(code, local_dict=dict(local_dict, **dummies), global_dict=global_dict,
                         transformations=(), evaluate=evaluate)
    if rebound is not None:
        if evaluate:
            out = _integer_indices(out)
        else:
            with sp.evaluate(False):
                out = _integer_indices(out)
    if pointed is not None and evaluate:
        out = _domain_end_limits(out)
    _refuse_reversed_ranges(out, s)
    if _names_the_registry(out):
        # `S`, `{S}`, `[S, 1]`: the registry itself came back as the "value" (a sum or a sympified S raises in
        # `_SingletonNames`); a caller took it for an expression (PRE-RK-6, principle 13)
        raise ParseError(f"{s!r} names SymPy's registry S bare: no value, not read")
    if evaluate:
        out = _hold_value(out, local_dict.get(PINS_KEY), local_dict.get(PROTECTED_KEY, ()))
    return out


def _names_the_registry(out) -> bool:
    """Is `out` (a parse's result, or the Python list, tuple, set or dict a bracketed text builds) or one of its
    items SymPy's registry `S` named bare (`_SingletonNames`)?"""
    if isinstance(out, _SingletonNames):
        return True
    if isinstance(out, dict):
        return any(_names_the_registry(x) for x in list(out) + list(out.values()))
    if isinstance(out, (list, tuple, set, frozenset)):
        return any(_names_the_registry(x) for x in out)
    return False


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


def _latex_prepared(s: str) -> str:
    """A LaTeX text as `_latex_to_sympy` gives it to latex2sympy (\\gcd, \\operatorname{arccot}, exact decimals)."""
    return _exact_latex_decimals(_LATEX_GCD.sub(lambda m: r"\mathrm{%s}" % (m.group(1) or m.group(2)),
                                                _LATEX_ARCCOT.sub(r"\\arccot ", s)))


_LATEX_CONVERTER = None


def _latex2sympy(s: str):
    """latex2sympy (pinned 1.11.0: its `latex2sympy` is this body) with one convention of the
    canonical parser: a limit written without a side is two-sided (`_Limit`). The library reads
    `\\lim_{x \\to 0}` from the right, exactly like `0^{+}`, so `\\lim_{x\\to 0} \\frac{|x|}{x}` = 1 was
    certified and the compute step stating it verified (V14 tests, 30 Sep 2026). The side is read
    from the tokens of the limit's subscript itself (`x \\to 2^{3}` is the point 8, no side)."""
    global _LATEX_CONVERTER
    from latex2sympy2_extended.latex2sympy2 import (ConversionConfig, NormalizationConfig, _Latex2Sympy,
                                                    normalize_latex)
    if _LATEX_CONVERTER is None:
        class _TwoSidedLimits(_Latex2Sympy):
            def convert_func(self, func):
                # \sqrt[3]{b}: a root written as a root is the real root (_real_root, part d4a)
                if func.FUNC_SQRT() and func.root:
                    r = self.convert_expr(func.root)
                    if isinstance(r, Integer) and int(r) > 1 and int(r) % 2 == 1:
                        return _real_root(self.convert_expr(func.base), r)
                held = self._held_matrix_func(func) if not global_parameters.evaluate else None
                if held is not None:
                    return held
                return super().convert_func(func)

            def _held_matrix_func(self, func):
                """\\det A, \\operatorname{rank} A, \\operatorname{tr} A read as written: `_held_matrix_op` (the
                entries, not the computed value: review of d4f, YO-2); None for any other function."""
                single = func.func_normal_single_arg()
                if not single:
                    return None
                name = single.start.text[1:]
                if name == "operatorname":
                    name = {"rank": "rank", "tr": "trace", "trace": "trace"}.get(
                        single.func_operator_name.getText() if single.func_operator_name else "")
                elif name != "det":
                    name = None
                if name is None:
                    return None
                arg = self.convert_func_arg(func.func_single_arg() if func.func_single_arg()
                                            else func.func_single_arg_noparens())
                expr = _held_matrix_op(name)(arg)
                if func.supexpr():
                    sup = func.supexpr()
                    expr = sp.Pow(expr, self.convert_expr(sup.expr()) if sup.expr() else self.convert_atom(sup.atom()),
                                  evaluate=False)
                return expr

            def convert_comp(self, comp):
                if not global_parameters.evaluate and comp.det():
                    # a vmatrix read as written: its entries, not its determinant (review of d4f, YO-2)
                    return _held_matrix_op("det")(self.convert_matrix(comp.det()).subs(self.variances))
                return super().convert_comp(comp)

            def convert_frac(self, frac):
                # a fraction of integers over 0 is a written division by zero, like the canonical 1/0, not
                # SymPy's zoo or nan, which `certify.domain` reads as a value written out (review of d4f, RK-F4)
                return _written_zero_division(super().convert_frac(frac),
                                              lambda: (self.convert_expr(frac.upper), self.convert_expr(frac.lower)))

            def convert_mp(self, mp):
                return _written_zero_division(super().convert_mp(mp), lambda: _mp_sides(self, mp))

            def handle_limit(self, func):
                lim = super().handle_limit(func)
                sub = func.limit_sub()
                if isinstance(lim, sp.Limit) and sub.ADD() is None and sub.SUB() is None:
                    return sp.Limit(lim.args[0], lim.args[1], lim.args[2], _two_sided(lim.args[2]))
                return lim
        _LATEX_CONVERTER = _TwoSidedLimits
    converter = _LATEX_CONVERTER(None, None, False, config=ConversionConfig())
    return converter.parse(normalize_latex(s, NormalizationConfig()))


def _written_zero_division(out, sides):
    """`out` (latex2sympy's value of a quotient), or the quotient as written when that value is SymPy's zoo or
    nan of an integer over 0: num * 0**(-1), unevaluated. Only read as written (evaluation off): the value
    reading keeps latex2sympy's zoo and nan, as 1/0 evaluates to zoo."""
    if not global_parameters.evaluate and (out is S.ComplexInfinity or out is S.NaN):
        top, bot = sides()
        if getattr(bot, "is_zero", None) is True and getattr(top, "is_Integer", False):
            return sp.Mul(top, sp.Pow(bot, -1, evaluate=False), evaluate=False)
    return out


def _mp_sides(conv, mp):
    """The operands of a latex2sympy division node."""
    if hasattr(mp, "mp") and mp.mp(0) is not None:
        return conv.convert_mp(mp.mp(0)), conv.convert_mp(mp.mp(1))
    return conv.convert_mp(mp.mp_nofunc(0)), conv.convert_mp(mp.mp_nofunc(1))


def _domain_end_limits(expr):
    """An undirected limit at 0 whose bound variable is positive (`_point_facts`: the declared
    variable is nonnegative) is the right-hand limit, the limit over the declared domain, as the limit
    task reads it: with x > 0, Limit(x*log(x), x, 0) = 0 was certified before the point binders and
    UNKNOWN after them (review of 30 Sep 2026)."""
    if not isinstance(expr, sp.Basic) or not expr.has(sp.Limit):
        return expr

    def side(n):
        e, z, z0, d = n.args
        if str(d) == "+-" and z0 == 0 and getattr(z, "is_positive", None) is True:
            return sp.Limit(e, z, z0, "+")
        return n
    return expr.replace(lambda n: isinstance(n, sp.Limit), side)


def _latex_limit_variables(expr, ns: dict[str, Any]):
    """Every LaTeX limit's variable bound as the canonical branch binds it (`_point_facts`,
    `_point_dummy`), before the free symbols are rebound to the IR's. latex2sympy gives the variable an
    assumption-free symbol, and a Limit is no ExprWithLimits: that substitution reached its variable
    only when the same name was also free, so with x > 0 `x\\cdot\\lim_{x\\to -\\infty}
    \\frac{\\sqrt{x^2}}{x}` came out x (it is -x), and alone the variable stayed complex (V14 tests,
    30 Sep 2026). Keeping the declared symbol unless the point was proved to leave its sign certified
    lim_{x->a} |x|/x = 1 for x > 0 and a = -2 (review of 30 Sep 2026): the facts come from the point."""
    if not isinstance(expr, sp.Basic) or not expr.has(sp.Limit):
        return expr

    def bind(n):
        body, v, p, d = n.args
        decl = ns.get(v.name) if isinstance(v, Symbol) else None
        if not isinstance(decl, Symbol):
            return n
        w = _point_dummy(decl.name, _point_facts("Limit", decl, p, str(d)))
        return _domain_end_limits(sp.Limit(body.xreplace({v: w}), w, p, d))
    return expr.replace(lambda n: isinstance(n, sp.Limit), bind)


_LATEX_RANGE_BINDER = re.compile(r"\\(?:sum|prod)(?![A-Za-z])")


def _evaluated_bound(e):
    """A limit of the as-written tree, evaluated: \\sqrt{1} is Pow(1, 1/2) there."""
    with sp.evaluate(True):
        return e.func(*[_evaluated_bound(a) for a in e.args]) if isinstance(e, sp.Basic) and e.args else e


def _refuse_latex_ranges(s: str) -> None:
    """The LaTeX counterpart of `_refuse_computed_bounds` and `_refuse_reversed_ranges`, read on the TREE
    latex2sympy builds with SymPy's evaluation off, before anything computes the sum: a function around it
    does at once (a floor, once the index is an integer), and \\lfloor \\sum_{k=3}^{1} k \\rfloor = -2 (Karr)
    was certified (review of V14, 30 Sep 2026). A sum or product whose limit is itself an operation, or
    whose limits are a reversed range, not an integer apart or not integers, is not read. This check read
    the limits from the text, with the index written [A-Za-z]\\w* and nothing around the `=`: an index
    \\alpha, k_{1} or \\mathrm{k}, or k\\,=\\,3, left \\lfloor \\sum_{\\alpha=3}^{\\sqrt{1}} \\alpha \\rfloor = -2
    certified (fourth audit B1)."""
    if not _LATEX_RANGE_BINDER.search(s):
        return
    with sp.evaluate(False):
        held = _latex2sympy(_exact_latex_decimals(s))      # a text latex2sympy cannot read fails here already
    if not isinstance(held, sp.Basic):
        return
    for node in sp.preorder_traversal(held):
        if not isinstance(node, (sp.Sum, sp.Product)):
            continue
        for lim in node.limits:
            if len(lim) != 3:
                continue
            if any(isinstance(b, sp.Basic) and b.has(*_OPERATIONS) for b in lim[1:]):
                raise ParseError(f"{s!r} has a sum or product whose limit is itself an operation: not read")
            _refuse_constant_range("sum or product", _evaluated_bound(lim[1]), _evaluated_bound(lim[2]), s)


def _refuse_latex_integer_calculus(expr, ns: dict[str, Any], raw: str) -> None:
    """The LaTeX counterpart of `_refuse_integer_calculus`, judged on latex2sympy's result while its
    symbols are still assumption-free, by name: a derivative or an indefinite integral in a name the IR
    declares an integer is not read, whatever binds it. latex2sympy keeps a first derivative
    unevaluated, as Subs(Derivative(f(n'), n'), n', n), and an indefinite integral too; a later
    substitution that reaches n' (a limit's variable, a sum's integer index) puts the declaration inside
    them: with n a positive integer lim_{n->oo} d/dn sin(pi n) was 0 (no limit) and
    sum_{n=1}^{3} d/dn sin(pi n) was 0 (it is -pi) (V17, parca5). Outside a binder the Subs form came
    out right; it is refused too, as the canonical diff(f, n) is. \\frac{d^2}{dn^2} is no derivative to
    latex2sympy (the product of the undeclared names d**2 and 1/dn**2, see `_latex_to_sympy`)."""
    if not isinstance(expr, sp.Basic) or not expr.has(sp.Derivative, sp.Integral):
        return
    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.Derivative):
            names = [v.name for v in node.variables if isinstance(v, Symbol)]
        elif isinstance(node, sp.Integral):
            names = [lim[0].name for lim in node.limits if len(lim) == 1 and isinstance(lim[0], Symbol)]
        else:
            continue
        for name in names:
            declared = ns.get(name)
            if isinstance(declared, Symbol) and declared.is_integer is True:
                raise ParseError(f"{raw!r} takes {type(node).__name__} in {name!r}, a variable declared an "
                                 "integer: not read")


_LATEX_FRAC = re.compile(r"\\[dtc]?frac(?![A-Za-z])")
# what a Leibniz fraction's typography adds around d and its variable: an upright or styled d, thin and other
# spaces, \left/\right, products written out, braces and brackets (d{n}^{2}, (dn)^2, {d}^2, d\,n, dn\,dn)
_LATEX_UPRIGHT_D = re.compile(r"\\(?:mathrm|operatorname\*?|text|textrm|textup|textit|mathit|mathsf|mathbf|mathbb|rm|up|it)"
                              r"\s*\{\s*d\s*\}")
_LATEX_LEIBNIZ_NOISE = re.compile(r"\\[,;:!> ]|\\q?quad(?![A-Za-z])|\\(?:left|right|big|Big|bigl|bigr|Bigl|Bigr)"
                                  r"(?![A-Za-z])|\\(?:cdot|times|ast)(?![A-Za-z])|[~*{}()\[\]\s]")
_LEIBNIZ_DEN = re.compile(r"(?:d(\\[A-Za-z]+|[A-Za-z]\w*?)(?:\^\d+)?)+")
_LEIBNIZ_DEN_PART = re.compile(r"d(\\[A-Za-z]+|[A-Za-z]\w*?)(?:\^\d+)?(?=d|$)")
_LEIBNIZ_NUM = re.compile(r"d(\^\d+)?(.*)", re.S)


def _leibniz_plain(t: str) -> str:
    """`t` without the typography a Leibniz fraction may carry (`_LATEX_LEIBNIZ_NOISE`), an upright d read as d."""
    return _LATEX_LEIBNIZ_NOISE.sub("", _LATEX_UPRIGHT_D.sub("d", t))


def _latex_group(s: str, i: int) -> tuple[str | None, int]:
    """The argument of a LaTeX command starting at s[i] (a brace group, a control word or one character) and
    the index after it; None when there is none."""
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s):
        return None, i
    if s[i] == "{":
        depth = 0
        for j in range(i, len(s)):
            depth += {"{": 1, "}": -1}.get(s[j], 0)
            if depth == 0:
                return s[i + 1:j], j + 1
        return None, len(s)
    m = re.match(r"\\[A-Za-z]+", s[i:])
    return (m.group(0), i + m.end()) if m else (s[i], i + 1)


def _leibniz_names(num: str, den: str) -> set | None:
    """The names latex2sympy's PRODUCT reading of \\frac{num}{den} takes when the fraction is a derivative in
    Leibniz notation (d/dx, d^2/dn^2, dy/dx, written with any of the typography `_leibniz_plain` removes): d, and
    dn for d^2/dn^2 (d·n read apart, dn read as one name). None when it is no such fraction."""
    num, den = _leibniz_plain(num), _leibniz_plain(den)
    mnum = _LEIBNIZ_NUM.fullmatch(num)
    if mnum is None or _LEIBNIZ_DEN.fullmatch(den) is None:
        return None
    rest = mnum.group(2)
    names = {"d"} | {"d" + v for v in _LEIBNIZ_DEN_PART.findall(den)}
    if mnum.group(1) is None and re.fullmatch(r"[A-Za-z]\w*", rest or "-"):
        names.add("d" + rest)                         # dy/dx
    return names


def _d_factors(e, names) -> set:
    """The names among the factors of the product `e` that a differential reading takes: d itself, and d<v> for a
    name v of the problem or of the text (`names`): dn, dx; not d_1 or delta."""
    out = set()
    for f in sp.Mul.make_args(e):
        b = f.base if isinstance(f, sp.Pow) else f
        if isinstance(b, Symbol) and (b.name == "d" or (b.name[:1] == "d" and b.name[1:] in names)):
            out.add(b.name)
    return out


def _quotient_d_names(expr, ns: dict[str, Any]) -> set:
    """The d-names (`_d_factors`) of each quotient in the tree latex2sympy built (unevaluated, as written) whose
    numerator AND denominator both have one as a factor: d·x²/(d·x), d²·n/(d·n²), d/d·x (a slash too)."""
    out: set = set()
    if not isinstance(expr, sp.Basic):
        return out
    names = {k for k, v in ns.items() if isinstance(v, Symbol)} | {s_.name for s_ in expr.free_symbols}
    for node in sp.preorder_traversal(expr):
        if not isinstance(node, sp.Mul):
            continue
        num = [a for a in node.args if not (isinstance(a, sp.Pow) and a.exp.is_negative)]
        den = [a.base for a in node.args if isinstance(a, sp.Pow) and a.exp.is_negative]
        top = set().union(*[_d_factors(a, names) for a in num]) if num else set()
        bottom = set().union(*[_d_factors(a, names) for a in den]) if den else set()
        if top and bottom:
            out |= top | bottom
    return out


def _refuse_leibniz_products(s: str, ns: dict[str, Any], expr=None) -> None:
    """ParseError for a derivative written in Leibniz notation whose product reading is a valid expression of
    the problem: with d and dn declared, latex2sympy reads \\frac{d^2}{dn^2}(n \\sin(\\pi n)) as the product
    d**2*n*sin(pi*n)/dn**2, 0 for n an integer, and 0 was certified for a second derivative that is 2π(-1)^n
    (fourth audit I2; with the names undeclared `_check_symbols_declared` refuses it, V17). The text is a
    derivative or a product of declared symbols: the verifier does not choose. One declared name is enough (d
    alone is a distance, a common difference): \\frac{d}{d\\,x}(x^2) with d declared was d·x²/(d·x) = x, and
    'x' was certified while 2x was refuted; the fraction is found whatever its typography (\\, \\; d{n}^2 (dn)^2
    dn\\,dn \\mathrm{d} \\dfrac, `_leibniz_names`) and, in the tree latex2sympy built, as any quotient with a
    differential name above and below (a slash d/d\\,x too, `_quotient_d_names`; attack on d4h, YO-2)."""
    for m in _LATEX_FRAC.finditer(s):
        num, i = _latex_group(s, m.end())
        den, _ = _latex_group(s, i) if num is not None else (None, i)
        names = _leibniz_names(num, den) if num is not None and den is not None else None
        if names and any(isinstance(ns.get(n), Symbol) for n in names):
            raise ParseError(f"LaTeX {s!r}: \\frac{{{num}}}{{{den}}} is a derivative or a product of the declared "
                             f"{sorted(n for n in names if isinstance(ns.get(n), Symbol))}: not read")
    names = _quotient_d_names(expr, ns)
    if any(isinstance(ns.get(n), Symbol) for n in names):
        raise ParseError(f"LaTeX {s!r} divides by a differential ({sorted(names)}) of the declared "
                         f"{sorted(n for n in names if isinstance(ns.get(n), Symbol))}: a derivative or a product, "
                         "not read")


def _set_relations(st, el):
    """`el ∈ st` as relations for an interval, a finite set or a union of those, no infinite bound written
    (x ∈ [1, oo) is x >= 1, x ∈ R no condition)."""
    if isinstance(st, Union):
        return Or(*[_set_relations(p, el) for p in st.args])
    if isinstance(st, FiniteSet):
        return Or(*[Eq(el, a) for a in st.args])
    if not isinstance(st, Interval):
        return sp.Contains(el, st, evaluate=False)
    return And(*_interval_conditions(st, el, ""))


def _latex_membership(expr):
    """latex2sympy writes `x \\in S` as Eq(x, S) and `x \\notin S` as Not(Eq(x, S)): SymPy reads both as the
    EQUALITY of a number and a set, false for every x, so rebinding the symbols folded `x \\notin [0, 3]` to
    True; as a function's domain it restricted nothing and {-2, 2} was certified for f(x) = 5 with
    f = x² + 1 (fourth audit D1). Read here as the membership it is (Contains: an interval turns it into
    relations on x, `x \\notin [0, 3]` into x < 0 ∨ x > 3); one no relation states stays a Contains, which the
    condition readers refuse or read themselves."""
    if not isinstance(expr, sp.Basic) or not expr.has(sp.Set):
        return expr

    def member(n):
        return isinstance(n, Eq) and isinstance(n.lhs, sp.Set) != isinstance(n.rhs, sp.Set)

    def condition(eq, negated: bool):
        el, st = (eq.lhs, eq.rhs) if isinstance(eq.rhs, sp.Set) else (eq.rhs, eq.lhs)
        if S.Reals.is_subset(st) is True:
            # x ∈ ℝ (or a set holding it): a membership, which a real x meets and a complex one does not; as
            # relations it was And() = True, which names x and so was "not read", and the given x ∈ ℝ made four
            # task kinds abstain (attack on d4h, RK-1)
            c = sp.Contains(el, st, evaluate=False)
            return Not(c) if negated else c
        if negated and isinstance(st, FiniteSet):
            return And(*[Ne(el, a) for a in st.args])
        if all(isinstance(p, (Interval, FiniteSet)) for p in (st.args if isinstance(st, Union) else (st,))):
            return _set_relations(Complement(S.Reals, st) if negated else st, el)
        c = sp.Contains(el, st, evaluate=False)
        return Not(c) if negated else c
    expr = expr.replace(lambda n: isinstance(n, Not) and member(n.args[0]), lambda n: condition(n.args[0], True))
    return expr.replace(member, lambda n: condition(n, False))


def _latex_to_sympy(s: str, ns: dict[str, Any]):
    if _latex_divisor_juxtaposed(s):
        # latex2sympy reads 1/2\pi as 1/(2π) and \ln 2/2 as ln(2/2); left to right they are (1/2)π and (ln 2)/2: a
        # convention of the writer, not guessed (G4YO-2)
        raise ParseError(f"{s!r} writes a product or a function's argument next to a '/' without brackets "
                         "((1/2)\\pi or 1/(2\\pi)?): not read")
    if _latex_argument_ambiguous(s):
        # \tan x(1 + \tan^2 x): tan(x)·(1 + tan²x) or tan(x(1 + tan²x))? a convention of the writer (audit of the second
        # round, YO-T2-1, YO-T2-3, RK-T2-3)
        raise ParseError(f"{s!r} writes a factor right after a function's argument without brackets "
                         "(\\tan x(1 + \\tan^2 x): inside the argument or after it?): not read")
    s = _LATEX_GCD.sub(lambda m: r"\mathrm{%s}" % (m.group(1) or m.group(2)),
                       _LATEX_ARCCOT.sub(r"\\arccot ", _bracket_function_arguments(s)))
    _refuse_latex_ranges(s)
    expr = _latex2sympy(_exact_latex_decimals(s))
    # the names are checked before the IR's symbols bring their declarations too (and again after): with
    # n an integer, latex2sympy's reading of \frac{d^2}{dn^2} (n \sin(\pi n)), the product
    # d**2*n*sin(pi*n)/dn**2, folded to 0 and took the undeclared d and dn with it, so 0 was read for a
    # second derivative that is 2*pi*(-1)**n there (V17, parca5)
    _check_symbols_declared(expr, ns, s)
    _refuse_latex_integer_calculus(expr, ns, s)
    _refuse_leibniz_products(s, ns, expr)
    if isinstance(expr, sp.Basic):
        from sympy.core.function import AppliedUndef
        expr = _latex_membership(expr)
        ops = {"gcd": _GCD_CALL, "lcm": _LCM_CALL}

        def convert(e):
            e = e.replace(lambda n: isinstance(n, AppliedUndef) and n.func.__name__ in _LATEX_INTEGER_OPS,
                          lambda n: ops[_LATEX_INTEGER_OPS[n.func.__name__]](*n.args))
            # the only other UnevaluatedExpr latex2sympy writes is the 1/100 of a percent
            e = e.replace(lambda n: isinstance(n, sp.UnevaluatedExpr), lambda n: n.args[0])
            e = held_jumps(e)                          # \lfloor, \lceil, \bmod: the namespace's (round 9, YO-4)
            return e.replace(sp.acot, arccot) if e.has(sp.acot) else e   # (0, pi), as in the canonical branch
        expr = _on_sides(expr, lambda e: _latex_limit_variables(_integer_indices(convert(e)), ns))
        _refuse_reversed_ranges(expr, s)
        # a variable applied as a function: latex2sympy reads x(1) as the undefined function x at 1, which no certificate
        # decides (it took 47-58 s on \tan \left(x(1\right) + \tan^2 x); audit of the second round, RK-T2-3)
        applied = sorted({n.func.__name__ for n in expr.atoms(AppliedUndef) if isinstance(ns.get(n.func.__name__), Symbol)})
        if applied:
            raise ParseError(f"LaTeX {s!r} applies the variable(s) {applied} as a function: not read")
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
    if isinstance(expr, sp.Contains):
        # a membership too (`x \in \mathbb{R}`): rebinding x to the declared real symbol folded it to True
        return sp.Contains(f(expr.args[0]), f(expr.args[1]), evaluate=False)
    if isinstance(expr, (And, Or)) and all(_is_condition(a) for a in expr.args):
        return type(expr)(*[_on_sides(a, f) for a in expr.args], evaluate=False)
    return f(expr)


def _is_condition(e) -> bool:
    """A relation, a membership, or an And/Or of those (what `_on_sides` rebuilds unevaluated)."""
    if isinstance(e, (sp.core.relational.Relational, sp.Contains)):
        return True
    return isinstance(e, (And, Or)) and all(_is_condition(a) for a in e.args)


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
            return _hold_value(_latex_to_sympy(s, ns), ns.get(PINS_KEY), ns.get(PROTECTED_KEY, ()))
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


def _kinks(a, v) -> list:
    """|a| has no derivative where a = 0 and a' != 0: those roots one by one when a = 0 has finitely
    many (|x**2 - 4| at +-2; |x**3| keeps 0), else the condition itself."""
    da = sp.diff(a, v)
    try:
        roots = sp.solveset(a, v, sp.S.Reals)
    except Exception:  # noqa: BLE001
        roots = None
    if isinstance(roots, sp.FiniteSet) and len(roots) <= 12:
        out = []
        for r in roots:
            z = sp.simplify(da.subs(v, r))
            if z.is_zero is not True:
                out.append(sp.Ne(v, r))
        return out
    return [sp.Or(sp.Ne(a, 0), sp.Eq(da, 0))]


def _differentiability(u, v) -> list:
    """Where the operand `u` has a derivative in `v`: its own written conditions made strict (a
    derivative needs a neighbourhood: x*sqrt(x) has none at 0, formal.statement.interior_defined_at)
    and the kinks and jumps of |a|, sign, Heaviside, Max/Min and floor/ceiling/frac. Without them
    the derivative of |x - 2| was read as defined on all of R, and f'(0) of x*sqrt(x) was certified
    (third audit of 30 Sep 2026)."""
    from ..certify.domain import definedness_conditions
    out = []
    for c in definedness_conditions(u, None):
        if isinstance(c, sp.Ge) and v in c.free_symbols:
            c = sp.Gt(c.lhs, c.rhs)
        elif isinstance(c, sp.Le) and v in c.free_symbols:
            c = sp.Lt(c.lhs, c.rhs)
        out.append(c)
    for n in sp.preorder_traversal(u):
        if not getattr(n, "args", None) or v not in n.free_symbols:
            continue
        if isinstance(n, sp.Abs):
            out += _kinks(n.args[0], v)
        elif isinstance(n, (sp.sign, sp.Heaviside)):
            out.append(sp.Ne(n.args[0], 0))
        elif isinstance(n, (sp.Max, sp.Min)) and len(n.args) == 2:
            a, b = n.args
            out.append(sp.Or(sp.Ne(a, b), sp.Eq(sp.diff(a, v), sp.diff(b, v))))
        elif isinstance(n, (sp.floor, sp.ceiling, sp.frac)):
            out.append(sp.Ne(sp.sin(sp.pi * n.args[0]), 0))
    return [c for c in out if c is not sp.true]


def _written_diff(e, *args, **kwargs):
    """`diff` read as written. SymPy differentiates with evaluation off into the raw power rule,
    x**3 -> x**3*(0*log(x) + 3/x), whose log and 1/x are conditions the problem never imposed: {1}
    was certified for f'(x) = 0 with f = x**3 - 3x, and (0, 1) for f'(x) < 0 (critic of the V14
    audit, 29 Sep 2026). The derivative is taken with evaluation on, and carries where it exists
    (`_differentiability`, order by order) as a written_domain condition. The tree is for
    definedness only."""
    seq = []
    rest = list(args)
    while rest:
        v = rest.pop(0)
        n = rest.pop(0) if rest and getattr(rest[0], "is_Integer", False) else 1
        seq += [v] * int(n)
    if not seq or kwargs or not all(isinstance(v, sp.Symbol) for v in seq):
        with sp.evaluate(True):
            return sp.diff(e, *args, **kwargs)
    with sp.evaluate(True):
        conds, cur = [], e
        for v in seq:
            conds += _differentiability(cur, v)
            cur = sp.diff(cur, v)
        cond = sp.And(*conds)
    if cond is sp.true:
        return cur
    return written_domain(cur, cond)


def _written_integrate(*args, **kwargs):
    """`integrate` read as written is the form, as `Integral` is: with evaluation off an integral
    with a parameter bound (x from 0 to y) raised, the reading returned None and every condition
    of the text was lost (y/y at y = 0 was certified)."""
    return sp.Integral(*args, **kwargs)


# computing helpers of the namespace read as forms (or, for diff, computed with evaluation on)
# when a text is read as written
def _matrix_entries(m) -> list:
    """The entries of a matrix (or of nested lists) as they were written."""
    if isinstance(m, sp.MatrixBase):
        return list(m)
    if isinstance(m, (list, tuple, sp.Tuple)):
        return [x for e in m for x in _matrix_entries(e)]
    return [m]


def _rational_as_written(e) -> bool:
    """Is a matrix entry, as written, a rational number made of integers by +, -, * and integer powers, with no
    division by zero and no 0**0? Such an entry carries no condition a computed operation could fold away. 0**0 is
    a convention (1 or no value): computed, trace [[0**0, 0], [0, 0]] = 1 was certified (attack on d4f round 2,
    A-YO-1)."""
    if isinstance(e, sp.Rational):
        return True
    if isinstance(e, (sp.Add, sp.Mul)):
        return all(_rational_as_written(a) for a in e.args)
    if isinstance(e, sp.Pow) and isinstance(e.exp, sp.Integer) and _rational_as_written(e.base):
        return not (e.exp <= 0 and _evaluated_bound(e.base) == 0)
    return False


def _held_matrix_op(name: str):
    """A matrix operation read as written, for definedness only: an undefined function of the entries. Computed,
    det [[√x, 1], [-1, √x]] folded √x·√x into x and the condition x >= 0 was lost ({-3} certified for = -2), and
    eigmax failed the whole reading (review of d4f, YO-2). The determinant, trace and rank of rational entries
    are computed: no condition is lost, and 30/det [[1, 1], [2, 4]] keeps its value for the condition det != 0
    (held, Cramer's rule steps of uni-la-009 were no longer verified)."""
    held = sp.Function(f"written_{name}")

    def op(m, *_rest, **_kw):
        entries = _matrix_entries(m)
        if name in ("det", "trace", "rank") and isinstance(m, sp.MatrixBase) and entries \
                and all(_rational_as_written(x) for x in entries):
            with sp.evaluate(True):
                return _SAFE_NAMES[name](m.applyfunc(_evaluated_bound))
        return held(*entries)
    return op


def _written_rewrite(*args, **kwargs):
    """factor(e), expand(e), simplify(e), ... read as written: `e` itself, whose value the rewrite keeps where `e`
    has one, and whose conditions are the claim's. Computed with evaluation off they failed the reading, and once
    such a text counted as not proved defined the step factor(x**2 - 4) = (x - 2)*(x + 2) was no longer verified
    (review of d4f, YO-1). `e` passed by keyword (simplify(expr=e)) too (`_rewritten_argument`)."""
    return _rewritten_argument("rewrite", args, kwargs)


_WRITTEN_COMPUTING = {"diff": (sp.diff, _written_diff), "integrate": (_integrate, _written_integrate),
                      "limit": (_limit, _Limit),
                      **{name: (_SAFE_NAMES[name], _held_matrix_op(name))
                         for name in ("det", "trace", "rank", "eigmax", "eigmin")},
                      **{name: (_SAFE_NAMES[name], _written_rewrite)
                         for name in ("simplify", "expand", "factor", "cancel", "together", "apart")}}


def _condition_sides(c) -> list | None:
    """The expressions a condition compares (the sides of its relations, the element and the set of a membership,
    through And/Or/Not), or None for anything else."""
    if c is sp.true or c is sp.false:
        return []
    if isinstance(c, sp.core.relational.Relational):
        return [c.lhs, c.rhs]
    if isinstance(c, sp.Contains):
        return list(c.args[:2])
    if isinstance(c, (And, Or, Not)):
        out: list = []
        for a in c.args:
            sides = _condition_sides(a)
            if sides is None:
                return None
            out += sides
        return out
    return None


def parse_as_written(s: str, ns: dict[str, Any] | None = None, _depth: int = 0):
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
        if isinstance(e, sp.logic.boolalg.Boolean):
            # a condition (`x \in (0, 3)`, `x \notin \mathbb{Z}`: relations and memberships since part d4h): the
            # sides of its relations; read as no text at all, every LaTeX membership given made the problem
            # undecided (merge of d4h with d4f's YO-1)
            sides = _condition_sides(e)
            return None if sides is None else sp.Tuple(*sides)
        if isinstance(e, sp.MatrixBase):
            # a matrix (\begin{bmatrix} ...): its entries; read as no text at all, a matrix parameter made the
            # problem undecided (review of d4f, YO-1)
            return sp.Tuple(*_matrix_entries(e))
        if isinstance(e, sp.Basic) and not isinstance(e, sp.logic.boolalg.Boolean):
            return sp.Tuple(e)
        return None
    s = preclean(s)
    local = dict(ns, Add=sp.Add, Mul=sp.Mul, Pow=sp.Pow)
    for name, (computing, written) in _WRITTEN_COMPUTING.items():
        if local.get(name) is computing:
            local[name] = written
    for name, value in list(local.items()):
        if callable(value) and getattr(value, "fdef", None) is not None:
            local[name] = _written_call(value, ns, _depth)
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
                # [1, e]; audit of 29 Sep 2026). The variable of a POINT binder is bound all the same:
                # read as the declared symbol, with x positive at(diff(sqrt(-x), x), x, -1) was undefined
                # (-x > 0 is false for x > 0) and the empty solution set of y + at(...) = -1/2 was
                # certified, and Limit(sqrt(x)**2/x, x, -oo) took its region from x's declaration
                # (fourth audit TAN-05)
                out.append(guarded_parse_expr(chunk, local_dict=local, global_dict={},
                                              transformations=_TRANSFORMS, evaluate=False, rebind=False,
                                              rebind_points=True))
        except Exception:  # noqa: BLE001 - the normal parse reports errors; this only adds facts
            return None
    try:
        return sp.Tuple(*out)
    except Exception:  # noqa: BLE001 - a part that is no expression (a set, a dict): not read, never raised
        return None


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
            return _hold_value(_latex_to_sympy(s, ns), ns.get(PINS_KEY), ns.get(PROTECTED_KEY, ()))
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
        # An order between things that are not expressions is no relation: "x > 0, x < 3" read as
        # x > (0, x) and (0, x) < 3, which SymPy cannot evaluate. Built unevaluated it passed as a
        # relation, and every sandbox worker it was sent to died unpickling it (TypeError; third
        # audit of 30 Sep 2026, N5).
        if op in ("<", "<=", ">", ">=") and not (isinstance(exprs[k - 1], sp.Expr) and isinstance(exprs[k], sp.Expr)):
            raise ParseError(f"{s!r}: an order between non-expressions ({parts[k - 1][1].strip()!r} "
                             f"{op} {parts[k][1].strip()!r}) is not read")
        # evaluate=False everywhere: a relation on an assumption-carrying symbol (x positive)
        # would otherwise collapse to True/False and silently disappear as a constraint
        rels.append(_REL_CLASS[op](exprs[k - 1], exprs[k], evaluate=False))
    return rels[0] if len(rels) == 1 else And(*rels)


# ----------------------------------------------------------------------------
# sets / intervals / domains
# ----------------------------------------------------------------------------
_INTERVAL_RE = re.compile(r"^\s*([\(\[])\s*(.+?)\s*[,;]\s*(.+?)\s*([\)\]])\s*$")


_NUMBER_SET_NAMES = {
    "R": S.Reals, "Reals": S.Reals, "Z": S.Integers, "Integers": S.Integers,
    # ℕ, N and Naturals: {1, 2, ...} here; whether 0 belongs is a convention (the Turkish curriculum and
    # ISO 80000-2 include it), so the verifier reads a problem that writes them both ways and decides
    # only when the two verdicts agree (verifier._naturals_zero_reading, part d4a)
    "N": S.Naturals, "Naturals": S.Naturals,
    "N+": S.Naturals, "Naturals+": S.Naturals, "Z+": S.Naturals, "Integers+": S.Naturals, "N*": S.Naturals,
    "Naturals*": S.Naturals,
    "N0": S.Naturals0, "Naturals0": S.Naturals0,
}


def number_set_named(s: str):
    """The number set a name denotes (`Reals`, `Z`, `ℕ⁺`, `N+`, `Z+`, `ℕ0`, `N_0`, `\\mathbb{N}`; after
    `preclean`), or None. ℕ⁺ and N+ raised a ParseError that surfaced as a layer exception (CAP-N1)."""
    t = re.sub(r"\s+", "", str(s))
    t = re.sub(r"^S\.", "", t)
    t = re.sub(r"^\\mathbb\{?([A-Z])\}?", r"\1", t)
    for a, b in (("ℕ", "Naturals"), ("ℤ", "Integers"), ("ℝ", "Reals"), ("⁺", "+"), ("₀", "0"), ("^{+}", "+"), ("^+", "+"), ("_{+}", "+"), ("_+", "+"),
                 ("_{0}", "0"), ("_0", "0"), ("^{*}", "*"), ("^*", "*")):
        t = t.replace(a, b)
    return _NUMBER_SET_NAMES.get(t)


def _parse_single_set(s: str, ns):
    s = s.strip()
    if s in ("EmptySet", "{}", "S.EmptySet", "∅"):
        return S.EmptySet
    named = number_set_named(s)
    if named is not None:
        return named
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


def _union_parts(s2: str) -> list[str]:
    """`s2` (precleaned) split at top level on " U " ("∪" is already mapped to it)."""
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
    return parts


def _top_level_terms(s: str) -> list[str]:
    """`s` split at the + and - signs outside brackets (a sign after another operator, an `e` of 1e-3 or the
    start is no split)."""
    out, depth, cur, prev = [], 0, "", ""
    for i, c in enumerate(s):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if depth == 0 and c in "+-" and cur.strip() and prev not in "*/^(,eE" and not s[:i].rstrip().endswith(("*", "/", "^")):
            out.append(cur)
            cur = ""
        else:
            cur += c
        if not c.isspace():
            prev = c
    out.append(cur)
    return [p for p in out if p.strip()]


class _WrittenInterval:
    """`Interval` read for definedness only (`parse_set_as_written`): its arguments as written, in a Tuple.
    SymPy's Interval compares its ends when it is built, and an end with no value ((-1)!) failed the whole
    reading, so the claim Interval(1/factorial(-1), 2) was compared as [0, 2] and certified (fourth audit,
    CAP-F1)."""
    def __new__(cls, *args, **_kw):
        return sp.Tuple(*args)

    @staticmethod
    def open(*args, **_kw):
        return sp.Tuple(*args)

    Lopen = Ropen = open


def _written_set_args(*args, **_kw):
    return sp.Tuple(*args)


_WRITTEN_SETS = {"Interval": _WrittenInterval, "Union": _written_set_args, "Intersection": _written_set_args,
                 "Complement": _written_set_args}


# and/or between relations; `|` only between bracketed ones ((x < -3) | (x > 1)): elsewhere it is |x - 1|
_COMPOUND_RE = re.compile(r"\s+(?:or|and)\s+|\s*[∧∨&]\s*|(?<=\))\s*\|\s*(?=\()")
_LATEX_ORDER_RE = re.compile(r"\\(?:leqslant|geqslant|leq|geq|le|ge|lt|gt)(?![A-Za-z])|<=|>=|<|>")


def _latex_chain_sides(s: str) -> list[str]:
    """The sides of a LaTeX order chain (0 < x \\le 3) cut at the top-level order relations (not inside braces
    or brackets); one piece when there is none."""
    out, depth, cur, i = [], 0, "", 0
    while i < len(s):
        c = s[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        m = _LATEX_ORDER_RE.match(s, i) if depth == 0 else None
        if m is not None:
            out.append(cur)
            cur, i = "", m.end()
            continue
        cur += c
        i += 1
    return out + [cur]


def parse_set_as_written(s: str, ns: dict[str, Any] | None = None):
    """A text that may be set notation, read AS WRITTEN for definedness only (see `parse_as_written`): the set
    constructors hold their arguments as a Tuple, and a text the whole reading cannot take is cut the way
    `parse_set_str` reads it (the parts of A U B, the ends of (a, b], the elements of {a, b}), each part read
    as written; a compound condition (x = 1 or x = 2) and a membership (x in {0, 4}) part by part. None when a
    part is not read."""
    if ns is None:
        ns = dict(_SAFE_NAMES)
    if not isinstance(s, str):
        return None
    wns = dict(ns, **_WRITTEN_SETS)
    whole = parse_as_written(s, wns)
    if whole is not None:
        return whole
    if is_latex(s):
        # `$x \notin \mathbb{Z}$`, `$x \in (0, \infty)$` too: with the delimiters the text matched nothing, the
        # membership is no text latex2sympy reads with evaluation off (its ℤ and ∞ fail there), and every such given
        # made the problem undecided (merge of d4h with d4f's YO-1; RK-1)
        m = _LATEX_MEMBER_RE.match(strip_presentation(_strip_invisible(s)))
        if m is not None:
            return parse_set_as_written(m.group(2), ns)           # x \in S, x \notin S: the set
        cup = _LATEX_SET_OP_RE.split(strip_presentation(_strip_invisible(s)))
        if len(cup) > 1:
            # a union, intersection or difference of sets: each part as written
            read = [parse_set_as_written(p, ns) for p in cup]
            return None if any(r is None for r in read) else sp.Tuple(*[a for r in read for a in r.args])
        sides = _latex_chain_sides(s)
        if len(sides) > 2:
            # a chain (0 < x \le 3), which the reading with evaluation off does not take: each side
            read = [parse_as_written(p, wns) for p in sides]
            return None if any(r is None for r in read) else sp.Tuple(*[a for r in read for a in r.args])
    s2 = preclean(strip_presentation(_strip_invisible(s))).strip()
    if number_set_named(s2) is not None or number_set_named(s) is not None:
        return sp.Tuple()                           # ℕ⁺, Z+, N0: a set by its name, no condition
    parts = _COMPOUND_RE.split(s2)
    if len(parts) > 1:
        # a compound condition (x < -1 or x > 3, x = 1 or x = 2): each part as written
        read = [parse_set_as_written(p, ns) for p in parts]
        return None if any(r is None for r in read) else sp.Tuple(*[a for r in read for a in r.args])
    member = _NOT_IN_RE.match(s2) or _DOMAIN_MEMBER_RE.match(s2)
    if member:
        # x in [a, b], x ∈ Interval(a, b): the set's ends (review of d4f, YO-6)
        return parse_set_as_written(member.group(2), ns)
    pieces: list[str] = []
    for part in _union_parts(s2):
        part = part.strip()
        m = _INTERVAL_RE.match(part)
        if part.startswith("{") and part.endswith("}"):
            pieces += _split_commas(part[1:-1])
        elif m:
            pieces += [m.group(2), m.group(3)]
        elif part and number_set_named(part) is None:
            # set arithmetic (Interval.Ropen(0, 1) + Interval(1, oo)): its operands; the definedness of a sum or a
            # difference is that of its operands, so a split of an expression loses no condition either
            pieces += [p for p in _top_level_terms(part) if number_set_named(p.strip()) is None]
    pieces = [p for p in pieces if p.strip()]
    if not pieces:
        return sp.Tuple()                           # named sets only (Reals U Integers)
    read = [parse_as_written(p, wns) for p in pieces]
    if any(w is None for w in read):
        return None                                 # a part no reading takes: the whole is not read
    return sp.Tuple(*[a for w in read for a in w.args])


@_holds_forms
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
    sets = [_parse_single_set(p, ns) for p in _union_parts(preclean(s)) if p.strip()]
    from ..equiv.sets import unify_endpoints, EndpointsIncomparable
    try:
        sets = unify_endpoints(sets)
    except EndpointsIncomparable as e:
        raise ParseError(f"set endpoints cannot be compared exactly: {e}") from e
    return Union(*sets) if len(sets) > 1 else sets[0]


@_holds_forms
def parse_domain(spec: str | None, var, ns: dict[str, Any] | None = None) -> sp.Set:
    """Domain of discourse for `var`, from the *problem* (E4). None -> Reals."""
    if ns is None:
        ns = dict(_SAFE_NAMES)
    if spec is None or str(spec).strip() == "":
        return S.Reals
    s = preclean(str(spec))
    s = re.sub(r"^\s*" + re.escape(str(var)) + r"\s+in\s+", "", s)
    # relational spec like "x > 0 and x != 1"
    # a relation that opens with a bracket, "(sqrt(3)*sin(x) - cos(x) - 1)**3 > 0", is a relation too: read as
    # a set it was {that relation}, a domain no real number is in, and {} was certified for x**2 = 4 under it
    # (review of d4b, 2 Oct 2026); an interval or set literal has no comparison in it
    if any(op in s for op in ("<", ">", "!=")) and not s.startswith(("Interval", "Union")):
        conds = re.split(r"\s+and\s+|\s*&\s*|\s*∧\s*", s)
        dom = S.Reals
        from ..sandbox.exactsets import exact_solveset
        for c in conds:
            rel = parse_relation(c, ns)
            # guarded: a trigonometric relation is no single period of the line (sandbox.exactsets);
            # unsolved it stays a ConditionSet, which Ctx.domain_for solves on what the rest leaves
            dom = Intersection(dom, exact_solveset(rel, var, S.Reals))
        return dom
    return parse_set_str(s, ns)


_DOMAIN_JOIN_RE = re.compile(r"\s*(?:,|&|∧)\s*|\s+and\s+")
_DOMAIN_MEMBER_RE = re.compile(r"^([A-Za-z_]\w*)\s+in\s+(.+)$", re.S)
_RELATION_OP_RE = re.compile(r"[<>=]")


def _conjunction(rel, spec: str):
    """`rel` as a declared domain: a relation whose two sides are expressions, or an And of them;
    None for True (no restriction). Anything else raises ParseError: a relation with a tuple side
    (`x > (0, x)`, how "x > 0, x < 3" read) crashed the sandbox workers that unpickled it."""
    if rel is sp.true:
        return None
    parts = rel.args if isinstance(rel, And) else (rel,)
    for r in parts:
        if not (isinstance(r, sp.core.relational.Relational) and isinstance(r.lhs, sp.Expr)
                and isinstance(r.rhs, sp.Expr)):
            raise ParseError(f"domain {spec!r} is not read as relations between expressions ({r})")
    return rel


def _interval_conditions(st, v, spec: str) -> list:
    """A set of reals written as a domain (`(0, oo)`, `[0, 3)`) as relations on `v` (none for ℝ,
    SymPy's Interval(-oo, oo))."""
    if not isinstance(st, Interval):
        raise ParseError(f"domain {spec!r} is not an interval of reals")
    out = []
    if st.start != -oo:
        out.append((Gt if st.left_open else Ge)(v, st.start, evaluate=False))
    if st.end != oo:
        out.append((Lt if st.right_open else Le)(v, st.end, evaluate=False))
    return out


def read_domain_condition(spec: str, argsyms: list, ns: dict[str, Any]):
    """An IR function's declared domain as a condition on its formal arguments `argsyms`: a
    relation, or an And of relations, each side an expression; None when it restricts nothing.
    Read: relations (`x > 0`, `0 < x < 3`), several joined by `,`, `&`, `∧` or `and`, and, for a
    function of one argument, an interval of reals (`(0, oo)`, `x in [0, oo)`). Each relation must
    name an argument. Anything else raises ParseError; the caller does not drop it."""
    if is_latex(spec):
        pieces, latex = [spec], True
    else:
        pieces, latex = _split_domain(preclean(strip_presentation(_strip_invisible(spec)))), False
    conds: list = []
    # per piece: (argument, set) for a set, None for relations; the arguments it names; whether it only excludes
    read: list = []
    pieces_read: list = []          # per piece: its `read` entry and the conditions it states
    for p in pieces:
        if not p:
            raise ParseError(f"domain {spec!r} has an empty part")
        m = None if latex else _DOMAIN_MEMBER_RE.match(p)
        if m is not None or (not latex and not _RELATION_OP_RE.search(p)):
            name, set_txt = (m.group(1), m.group(2)) if m is not None else (None, p)
            if name is None and len(argsyms) != 1:
                raise ParseError(f"domain {spec!r}: a set names no argument of a function of several")
            v = argsyms[0] if name is None else next((a for a in argsyms if a.name == name), None)
            if v is None:
                raise ParseError(f"domain {spec!r}: {name} is not an argument")
            st = parse_set_str(set_txt, ns)
            found = _interval_conditions(st, v, spec)
            read.append(((v, st), {v}, False))
        else:
            # LaTeX `x \notin [0, 3]` is x < 0 ∨ x > 3 (`_latex_membership`), no relation list: not read; `x \in
            # \mathbb{R}` restricts no real argument (RK-1)
            rel = _conjunction(_line_members_true(parse_relation(p, ns), argsyms), spec)
            found = [] if rel is None else list(rel.args if isinstance(rel, And) else (rel,))
            read.append((None, {s_ for c in found for s_ in c.free_symbols} & set(argsyms),
                         bool(found) and all(isinstance(c, Ne) for c in found)))
        for c in found:
            if not c.free_symbols & set(argsyms):
                raise ParseError(f"domain {spec!r}: {c} is not a condition on the arguments")
            if c not in conds:
                conds.append(c)
        pieces_read.append((read[-1], list(found)))
    if _set_listed(read):
        # a set listed next to another condition on the same argument: a union as often as an intersection
        # (fourth audit D2); read one way only when the verifier asks for it (`domain_list_reading`)
        which = _DOMAIN_LIST_READING.get()
        if which is None:
            raise DomainListAmbiguous(f"domain {spec!r} lists a set next to another condition on the same argument: "
                                      "a union or an intersection")
        if which == "union":
            conds = _union_reading(pieces_read, argsyms, spec)
    if not conds:
        return None
    if len(pieces) > 1:
        # no number meets what the list says on one argument (`x < -1, x > 1`, whatever the other arguments): the
        # list meant a union as often (D2; with two arguments it was read as the empty domain, attack on d4h YO-4)
        for v in argsyms:
            on_v = [c for c in conds if c.free_symbols == {v}]
            if on_v:
                _refuse_empty_list(on_v, v, spec)
    return _conjunction(conds[0] if len(conds) == 1 else And(*conds), spec)


class DomainListAmbiguous(ParseError):
    """A function's domain that lists a set next to another condition on the same argument (`(0, 3), (1, 5)`,
    `(0, oo), x <= 5`): the verifier reads it as the union and as the intersection and decides only when both
    readings agree (`verifier.verify_layers`, attack on d4h RK-2)."""


# how a domain list of `DomainListAmbiguous` is read: None (not read), "union" or "intersection"
_DOMAIN_LIST_READING: contextvars.ContextVar = contextvars.ContextVar("domain_list_reading", default=None)


class domain_list_reading:  # noqa: N801 - used as a context manager
    """Within it, a domain list of `DomainListAmbiguous` is read as the union or the intersection of its parts."""

    def __init__(self, which: str):
        if which not in ("union", "intersection"):
            raise ValueError(which)
        self.which = which

    def __enter__(self):
        self._token = _DOMAIN_LIST_READING.set(self.which)
        return self

    def __exit__(self, *exc) -> None:
        _DOMAIN_LIST_READING.reset(self._token)


def _line_members_true(rel, argsyms):
    """`rel` with each membership of a (real) argument in a set holding the whole line (`x \\in \\mathbb{R}`,
    `_latex_membership`) replaced by true: it restricts no argument."""
    if not isinstance(rel, sp.Basic) or not rel.has(sp.Contains):
        return rel
    return rel.replace(lambda n: isinstance(n, sp.Contains) and n.args[0] in argsyms
                       and S.Reals.is_subset(n.args[1]) is True, lambda n: sp.true)


def _set_listed(read: list) -> bool:
    """Does a domain list a set next to another condition on the same argument (`_refuse_set_lists`' case)?"""
    try:
        _refuse_set_lists(read, "")
    except ParseError:
        return True
    return False


def _union_reading(pieces_read: list, argsyms: list, spec: str) -> list:
    """The conditions of a domain list read as the UNION of its parts: every part a condition on one and the same
    argument v; the union, solved exactly, written back as relations (an interval, with points left out:
    `_set_as_relations`). ParseError when it is not one argument or the union is no such set."""
    from ..sandbox.exactsets import exact_solveset
    names = set().union(*[names for (_, names, _), _found in pieces_read])
    if len(names) != 1:
        raise ParseError(f"domain {spec!r}: a union of conditions on several arguments is not read")
    v = next(iter(names))
    parts = []
    for (key, _, _), found in pieces_read:
        if key is not None:
            parts.append(key[1])
        else:
            part = S.Reals
            for c in found:
                part = Intersection(part, exact_solveset(c, v, S.Reals))
            parts.append(part)
    return _set_as_relations(Union(*parts), v, spec)


def _set_as_relations(st, v, spec: str) -> list:
    """`v ∈ st` as relations for a set of reals that is an interval with finitely many points left out (ℝ: none);
    ParseError for anything else (the empty set, two pieces apart, an unsolved part)."""
    if isinstance(st, Interval):                     # ℝ too: no condition
        return _interval_conditions(st, v, spec)
    try:
        lo, hi = st.inf, st.sup
        hull = Interval(lo, hi, st.contains(lo) != sp.true, st.contains(hi) != sp.true)
        holes = Complement(hull, st)
    except Exception as e:  # noqa: BLE001 - an unsolved part, an empty set
        raise ParseError(f"domain {spec!r}: the union {st} is not read as relations") from e
    if st.is_empty is not False or not isinstance(hull, Interval) or not (holes is S.EmptySet
                                                                           or isinstance(holes, FiniteSet)):
        raise ParseError(f"domain {spec!r}: the union {st} is not one interval with points left out")
    return _interval_conditions(hull, v, spec) + [Ne(v, h, evaluate=False) for h in getattr(holes, "args", ())]


def _refuse_empty_list(conds: list, v, spec: str) -> None:
    """ParseError when the conditions a domain LISTS (`x < -1, x > 1`, `x < -1 and x > 1`) hold for no number:
    read as all holding, a list meant as "x < -1 or x > 1" was the empty domain, and {} was certified for
    f(x) = 5 and 0 roots for f(x) - 5 (fourth audit D2). A declared domain no number is in is no problem's;
    the verifier abstains (decided exactly, `sandbox.exactsets`; undecided, the conditions are kept)."""
    from ..sandbox.exactsets import exact_solveset
    try:
        dom = S.Reals
        for c in conds:
            dom = Intersection(dom, exact_solveset(c, v, S.Reals))
        empty = dom.is_empty
    except Exception:  # noqa: BLE001 - undecided: the conditions are read as they are
        return
    if empty is True:
        raise ParseError(f"domain {spec!r} lists conditions no number meets: a union or an intersection, not read")


def _refuse_set_lists(read: list, spec: str) -> None:
    """ParseError when a domain lists a set next to another condition on the same argument
    (`(-oo, -1), (1, oo)`, `(0, 3) and (4, 5)`, `x in (0, 3), x in (1, 5)`, `(0, 3), x > 1`): a list of
    intervals is a union as often as an intersection, and read as the intersection the domain was empty and
    {} certified for f(x) = 5 with f = x² + 1 (fourth audit D2). Read as all holding: the same set twice (either
    reading), relations alone (`x > 0, x < 3`, DECISIONS §76 (ii)) and a set with exclusions only
    (`x in [0, 3), x != 1`: as a union, the line or the line without a point, no domain a text lists so)."""
    for i, (key, names, _) in enumerate(read):
        if key is None:
            continue
        for j, (other, onames, excludes) in enumerate(read):
            if j != i and names & onames and other != key and not (other is None and excludes):
                raise ParseError(f"domain {spec!r} lists a set next to another condition on {key[0]}: "
                                 "a union or an intersection, not read")


_OR_JOIN_RE = re.compile(r"\s+or\s+|\s*∨\s*|\s*\|\|\s*|(?<=\))\s*\|\s*(?=\()")


def _reals_set(st, spec: str):
    """`st` when it is a set of real numbers, else ParseError: `x in {(2, 3)}` or `x in (2,)` read as a set of
    tuples, which meets the reals nowhere, and the empty set was certified for x² = 4 (review of d4d, B3)."""
    if not isinstance(st, sp.Set) or st.is_subset(S.Reals) is not True:
        raise ParseError(f"{spec!r}: {st} is not a set of real numbers")
    return st


def _set_text(txt: str, ns: dict[str, Any], spec: str):
    try:
        return _reals_set(parse_set_str(txt, ns), spec)
    except ParseError:
        raise
    except Exception as e:  # noqa: BLE001 - `[2]` raised AttributeError
        raise ParseError(f"{spec!r}: the set {txt!r} is not read ({type(e).__name__})") from e


def _condition_atom(c, spec: str):
    """One part of a condition: a relation between expressions, a membership of a symbol in a set of
    reals, or an And/Or of those; anything else raises ParseError."""
    if c is sp.true or c is sp.false:
        return c
    if isinstance(c, (And, Or)):
        return type(c)(*[_condition_atom(a, spec) for a in c.args])
    # LaTeX `x \in (0, 3)` is read as membership by the parse itself (`_latex_membership`, part d4h); an
    # equation between a number and a set (`x = Interval(0, 3)`) is no condition here
    if isinstance(c, sp.Contains) and isinstance(c.args[1], sp.Set):
        return sp.Contains(c.args[0], _reals_set(c.args[1], spec), evaluate=False)
    if isinstance(c, sp.core.relational.Relational) and isinstance(c.lhs, sp.Expr) and isinstance(c.rhs, sp.Expr):
        return c
    raise ParseError(f"{spec!r} is not read as a condition on real numbers ({c})")


_LATEX_NOTIN_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*\\notin\s*(.+?)\s*$", re.S)
# the operations between LaTeX sets (each part read as written by `parse_set_as_written`)
_LATEX_SET_OP_RE = re.compile(r"\\(?:cup|cap|setminus)(?![A-Za-z])")
# a variable's membership in a set (the set read as written by `parse_set_as_written`)
_LATEX_MEMBER_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*\\(?:in|notin)(?![A-Za-z])\s*(.+?)\s*$", re.S)
_NOT_IN_RE = re.compile(r"^([A-Za-z_]\w*)\s+not\s+in\s+(.+)$", re.S)
# a congruence (x \equiv 2 \mod 5) is no equation: latex2sympy read it as x = Mod(2, 5), i.e. x = 2
_LATEX_CONGRUENCE_RE = re.compile(r"\\(equiv|pmod|bmod|mod)(?![A-Za-z])")


def refuse_congruence(spec: str) -> None:
    """ParseError for a LaTeX congruence (`x \\equiv 2 \\mod 5`), which no relation between reals states."""
    if is_latex(spec) and _LATEX_CONGRUENCE_RE.search(spec):
        raise ParseError(f"{spec!r} is a congruence, not a relation between real numbers: not read")


def _mentions_variable(spec: str, ns: dict[str, Any]) -> bool:
    return any(isinstance(ns.get(t), Symbol) for t in re.findall(r"[A-Za-z_]\w*", spec))


def not_collapsed(rel, spec: str, ns: dict[str, Any]):
    """`rel` unless the text names a variable and still read as plain true or false: LaTeX `x \\notin (-3, 3)`
    read as True, and {-2, 2} was certified for x² = 4 next to it (review of d4d, B2). Such a text is not
    read (ParseError); a closed one (`pi < 3`) keeps its truth value."""
    if (rel is sp.true or rel is sp.false) and _mentions_variable(spec, ns):
        raise ParseError(f"{spec!r} names a variable but reads as {rel}: not read")
    return rel


def _not_in(name: str, txt: str, ns: dict[str, Any], spec: str):
    v = ns.get(name)
    if not isinstance(v, Symbol):
        raise ParseError(f"condition {spec!r}: {name} is not a variable")
    return sp.Contains(v, sp.Complement(S.Reals, _set_text(txt, ns, spec)), evaluate=False)


def read_condition(spec: str, ns: dict[str, Any]):
    """A given read as a CONDITION: a relation, a chain (`0 < x < 3`), relations joined by `and`, `,`,
    `&`, `∧` (all of them hold) or by `or`, `∨`, `|` between brackets (one of them holds), And(...) and
    Or(...), the membership of a variable in a set of reals (`x in (0, 3)`, `x ∈ [0, oo)`) and its
    negation (`x not in S`, LaTeX `x \\notin S`). The result is a relation, a Contains, an And/Or of those,
    or true/false. Anything else raises ParseError: such a given is never dropped (Ctx.side_conditions
    abstains, `given_not_applied`). Only the relations were read before, so the given `0 < x < 3`,
    `x > 0 and x < 3` or Or(x < -3, x > 1) next to x² < 4 or x² − 4 was dropped and (−2, 2) or the count 2
    certified (fourth audit G1).

    Not read (ParseError), so never guessed: a text that joins parts with both kinds of separator at its top
    level (`x != 6, x < 1 or x > 5`, `x < 3 and x < 1 or x > 5`: which binds first is a convention; read with
    `or` first, the count 2 of x² − 36 was certified, review of d4d B1), a congruence, a set that is not one
    of real numbers, and a text with a variable that collapses to true or false (`not_collapsed`)."""
    if not isinstance(spec, str):
        raise ParseError(f"not a condition: {type(spec).__name__}")
    if is_latex(spec):
        refuse_congruence(spec)
        # `$x \notin \mathbb{Z}$` too: the delimiters kept the text from the reading, and the given was not applied
        m = _LATEX_NOTIN_RE.match(strip_presentation(_strip_invisible(spec)))
        if m is not None:
            return _not_in(m.group(1), m.group(2), ns, spec)
        return not_collapsed(_condition_atom(parse_relation(spec, ns), spec), spec, ns)
    try:
        return not_collapsed(_condition_atom(parse_relation(spec, ns), spec), spec, ns)
    except UndeclaredSymbolError:
        raise
    except ParseError:
        pass
    s = preclean(strip_presentation(_strip_invisible(spec)))
    parts = [_split_domain(d) for d in _split_top(s, _OR_JOIN_RE)]
    if len(parts) > 1 and any(len(c) > 1 for c in parts):
        raise ParseError(f"condition {spec!r} joins parts with both `and` and `or` at the same level: not read")
    disjuncts = []
    for pieces in parts:
        conj = []
        for p in pieces:
            if not p:
                raise ParseError(f"condition {spec!r} has an empty part")
            m = _DOMAIN_MEMBER_RE.match(p)
            n = _NOT_IN_RE.match(p)
            if n is not None:
                conj.append(_not_in(n.group(1), n.group(2), ns, spec))
            elif m is not None:
                v = ns.get(m.group(1))
                if not isinstance(v, Symbol):
                    raise ParseError(f"condition {spec!r}: {m.group(1)} is not a variable")
                conj.append(sp.Contains(v, _set_text(m.group(2), ns, spec), evaluate=False))
            else:
                conj.append(not_collapsed(_condition_atom(parse_relation(p, ns), spec), p, ns))
        disjuncts.append(conj[0] if len(conj) == 1 else And(*conj))
    return disjuncts[0] if len(disjuncts) == 1 else Or(*disjuncts)


def _split_top(s: str, join_re) -> list[str]:
    """The top-level parts of `s` joined by `join_re` (not inside brackets)."""
    parts, depth, cur, i = [], 0, "", 0
    while i < len(s):
        c = s[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        m = join_re.match(s, i) if depth == 0 else None
        if m is not None and m.end() > i:
            parts.append(cur.strip())
            cur, i = "", m.end()
            continue
        cur += c
        i += 1
    parts.append(cur.strip())
    return parts


def _split_domain(s: str) -> list[str]:
    """The top-level parts of a domain joined by `,`, `&`, `∧` or `and` (not inside brackets)."""
    parts, depth, cur, i = [], 0, "", 0
    while i < len(s):
        c = s[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        m = _DOMAIN_JOIN_RE.match(s, i) if depth == 0 else None
        if m is not None and m.end() > i:
            parts.append(cur.strip())
            cur, i = "", m.end()
            continue
        cur += c
        i += 1
    parts.append(cur.strip())
    return parts


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
