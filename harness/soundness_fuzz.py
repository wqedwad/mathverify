"""Metamorphic / differential soundness sweep of the deterministic verifier.

    python -m harness.soundness_fuzz [--limit N] [--out reports]

The evaluation set measures the verifier on the answers someone chose to write. This sweep
measures it on answers SymPy manufactures from each problem's gold answer, where the ground
truth is known by construction:

  WRONG variants       provably different from the gold answer (gold ± 1, ×2, a dropped or an
                       extra set member, a closed endpoint, a 1e-9 perturbation, …).
                       A CORRECT verdict on one of these is a FALSE ACCEPT — the failure the
                       product exists to prevent. Target: 0.
  EQUIVALENT variants  provably the same answer written differently (expanded, factored,
                       decimal, permuted set, Interval(...) form, a scaled equation, …).
                       An INCORRECT verdict on one of these is a FALSE REJECTION (template
                       sensitivity, [10]). UNKNOWN is reported separately as lost coverage.

Every variant is checked with SymPy before it is used: a "wrong" variant that SymPy cannot
prove different, or an "equivalent" one it cannot prove equal, is discarded rather than
scored. The solutions carry no steps and no option letter, so this isolates the answer-level
certificates (the step refuter and the option path have their own sweeps in adversarial.py).

This is the technique program-verifier testing calls metamorphic testing (equivalent inputs
must give equal outputs) and differential testing (an independent oracle — here exact SymPy
arithmetic on the gold answer — cross-checks every output).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from harness.loader import load_items, split_for_verifier  # noqa: E402

KIND_OF_SHAPE = {"scalar": "value", "expression": "expression", "set": "set", "interval": "interval",
                 "count": "count", "equation": "equation", "dne_or_scalar": "value"}


_DISCONTINUOUS = ("sign", "floor", "ceiling", "frac", "Heaviside", "Piecewise", "Mod")


def _exact(e):
    """Floats read as the decimals they print as (0.1 is 1/10, a 39-digit 2.666…7 is not 8/3)."""
    import sympy as sp
    if not isinstance(e, sp.Basic):
        return e
    floats = e.atoms(sp.Float)
    return e.xreplace({f: sp.Rational(str(f)) for f in floats}) if floats else e


def _number_is_zero(z) -> bool | None:
    """A number without symbols: SymPy's exact decision, else the precision ladder. An exact zero
    evaluates far below each rung's accuracy and keeps shrinking (1e-172, 1e-250, 1e-328 at 40, 80,
    160 digits); a nonzero keeps its value. The old test, |N(z, 40)| < 1e-35, called 10**-40, a
    39-digit decimal of 8/3 and one of E "zero" (audit of 29 Sep 2026). A discontinuous function of
    an exact zero (sign(8*cos(pi/9)*cos(2*pi/9)*cos(4*pi/9) - 1)) flips with the precision: no decision."""
    import sympy as sp
    z0 = z.is_zero
    if z0 is not None:
        return z0
    if any(f.func.__name__ in _DISCONTINUOUS for f in z.atoms(sp.Function)) or z.has(sp.Piecewise, sp.Mod):
        return None
    try:
        v80, v160 = (sp.Abs(sp.N(z, p)).evalf(p) for p in (80, 160))
    except Exception:  # noqa: BLE001
        return None
    if v80 < sp.Float("1e-70") and v160 < sp.Float("1e-150"):
        return True
    if v160 > sp.Float("1e-140") and abs(v80 - v160) <= sp.Float("1e-10") * v160:
        return False
    return None


def _jump_at_a_possible_zero(e) -> bool:
    """A discontinuous function (sign, floor, …) of a number that may be exactly zero (or an integer,
    for floor): simplify() and N() evaluate it on one side and the result depends on the precision."""
    import sympy as sp
    for f in e.atoms(sp.Function):
        if f.func.__name__ in _DISCONTINUOUS and f.args and not f.args[0].free_symbols:
            arg = f.args[0]
            if f.func.__name__ in ("floor", "ceiling", "frac"):
                arg = arg - sp.floor(sp.N(arg, 30))    # the nearest integer below: the jump
            if _number_is_zero(arg) is not False:
                return True
    return False


def _heavy(e) -> bool:
    import sympy as sp
    return isinstance(e, sp.Basic) and e.has(sp.Sum, sp.Product, sp.Integral, sp.Limit, sp.Derivative, sp.Subs,
                                             sp.factorial, sp.binomial, sp.gamma, sp.RisingFactorial,
                                             sp.FallingFactorial)


def _simplify(e):
    """simplify(), in the sandbox with a time limit when the expression holds a sum, a product or a
    special function: simplify() of Sum(1/factorial(k), (k, 0, n)) minus its reindexed form did not
    return in 120 s, and one such claim would stall the labelling of a whole K4 run (audit of
    29 Sep 2026). None when it does not finish."""
    import sympy as sp
    if not _heavy(e):
        return sp.simplify(e)
    from mathverify.sandbox import run as sb_run
    r = sb_run("mathverify.sandbox.ops:simplify_diff", e, sp.Integer(0), timeout=10)
    return r.value if r.ok else None


def _is_zero(e) -> bool | None:
    import sympy as sp
    try:
        e = _exact(e)
        if isinstance(e, sp.Basic) and not e.free_symbols and _jump_at_a_possible_zero(e):
            return None
        z = _simplify(e)
        if z is None:
            return None
    except Exception:  # noqa: BLE001
        return None
    if z == 0:
        return True
    if z.has(sp.nan):
        return None                                # oo - oo is nan: no decision (it read as "nonzero")
    if z in (sp.oo, -sp.oo, sp.zoo):
        return False                               # an infinity against a finite value
    if getattr(z, "free_symbols", None):
        return False if z.is_zero is False else None
    try:
        return _number_is_zero(z)
    except (TypeError, ValueError):
        return None


def _real_roots(e):
    """Odd roots of negative NUMBERS read as real roots, the curriculum's convention: (-8)**(1/3) is
    -2, not SymPy's principal complex root, which made the right answer -2 "different" (audit of
    29 Sep 2026). The harness keeps its own reading, independent of the verifier's."""
    import sympy as sp
    if not isinstance(e, sp.Basic) or not e.has(sp.Pow):
        return e
    return e.replace(
        lambda t: (isinstance(t, sp.Pow) and t.exp.is_Rational and not t.exp.is_Integer and t.exp.q % 2 == 1
                   and not t.base.free_symbols and t.base.is_negative is True),
        lambda t: (-1) ** t.exp.p * sp.Abs(t.base) ** t.exp)


def _points(syms) -> list[dict]:
    """A fixed grid of exact points, each symbol drawn from the values its assumptions allow (the
    IR's domain: a positive integer n takes 1..5, a real x also negative and fractional values).
    The caller narrows it to the problem's domain (`admissible`)."""
    import itertools
    import sympy as sp
    half, third = sp.Rational(1, 2), sp.Rational(1, 3)

    def values(s):
        if s.is_integer:
            return [1, 2, 3, 4, 5] if s.is_positive else [0, 1, 2, 3, 4] if s.is_nonnegative else [1, 2, -1, 3, 0, -2]
        if s.is_positive:
            return [half, 2, 3, third, sp.Rational(5, 2)]
        if s.is_nonnegative:
            return [half, 2, 0, 3, third]
        return [half, 2, -half, 3, -2, third]
    syms = sorted(syms, key=lambda s_: s_.name)
    return [dict(zip(syms, map(sp.sympify, combo)))
            for combo in itertools.islice(itertools.product(*(values(s) for s in syms)), 64)]


def _real_value(e, pt):
    """The value of `e` at the point when EVERY part of it is a finite real number there, else None.
    Checking the result alone let sqrt(x - 1)*sqrt(x + 1) be "defined" at x = -2 (its value -sqrt(3)
    is real, its factors are not) and differ from sqrt(x**2 - 1) there (audit of 29 Sep 2026)."""
    import sympy as sp
    try:
        e = _real_roots(e)
        for part in sp.preorder_traversal(e):
            if not getattr(part, "free_symbols", None):
                continue
            if not isinstance(part, sp.Expr):
                return None
            if isinstance(part, (sp.Sum, sp.Product)):
                # a range read backwards: SymPy's Karr convention gives Sum(1, (k, 1, -1)) = -1, the
                # school reading an empty sum 0; a point where they differ is no point (audit of 29 Sep 2026)
                for _, lo, hi in part.limits:
                    lo_v, hi_v = sp.sympify(lo).subs(pt), sp.sympify(hi).subs(pt)
                    if lo_v.is_number and hi_v.is_number and (hi_v < lo_v) is sp.true:
                        return None
            v = _real_roots(part.subs(pt))
            if getattr(v, "free_symbols", None) or v.has(sp.zoo, sp.oo, -sp.oo, sp.nan):
                return None
            z = complex(sp.N(v, 30))
            if z.imag != 0 or z.real != z.real or abs(z.real) == float("inf"):
                return None
        return _real_roots(e.subs(pt))
    except Exception:  # noqa: BLE001
        return None


def _nonzero(v) -> bool:
    """True only when the number is proved nonzero (`_is_zero`)."""
    return _is_zero(v) is False


def _differs_at_a_point(a, b, *, mod_constant: bool = False, var=None, admissible=None) -> bool:
    """A difference proved by exact evaluation at a point of the problem's domain (`admissible`, from
    the IR: domains, constraints, written conditions, givens) where both sides are defined. Up to an
    additive constant: a point where the derivatives in the variable of integration `var` differ, so
    a parameter (a**3/3) or a different constant on each piece of the domain is no difference.
    SymPy's own `is_zero` cannot decide 3*2**(n-1) - 3**n or (1 - 2x)/(x² + 1): the K4 labeller left
    26 wrong options of the dataset `undecided`, and this sweep dropped 9 wrong variants (29 Sep 2026)."""
    import sympy as sp
    free = set(getattr(a, "free_symbols", set())) | set(getattr(b, "free_symbols", set()))
    if not free or not all(isinstance(s, sp.Symbol) for s in free):
        return False
    if mod_constant and (var is None or var not in free):
        return False
    slope = None
    if mod_constant:
        try:
            slope = sp.diff(a - b, var)
        except Exception:  # noqa: BLE001
            return False
    for pt in _points(free):
        try:
            if admissible is not None and not admissible(pt):
                continue
        except Exception:  # noqa: BLE001
            continue
        av, bv = _real_value(a, pt), _real_value(b, pt)
        if av is None or bv is None:
            continue
        d = av - bv if slope is None else _real_value(slope, pt)
        if d is not None and _nonzero(d):
            return True
    return False


def admissible_points(ir: dict):
    """The problem's domain as a test on a point, for the point proof of `_differs`: each symbol in its
    domain (`domain_for`: the IR's domains, constraints, side conditions), every variable constraint
    and written condition (`var_constraints`) and every given true there, and a sequence's index not
    below its first given term. A condition about symbols the point leaves unset rejects the point.
    Without it the grid took x = -1/2 where the problem says x > 0, and x and |x|, atan(x) + atan(1/x)
    and pi/2, 2x and sqrt(x)*sqrt(4x) came out "different" (audit of 29 Sep 2026)."""
    import sympy as sp
    from mathverify.certify.base import make_ctx
    from mathverify.intake.structured import load_problem_ir
    try:
        ctx = make_ctx(load_problem_ir(ir))
        conds = list(ctx.var_constraints()) + list(ctx.givens())
    except Exception:  # noqa: BLE001 - an IR whose domain cannot be read allows no point
        return lambda pt: False
    params = (ir.get("task") or {}).get("params") or {}
    first = None
    if isinstance(params.get("initial"), dict) and isinstance(params.get("var"), str):
        try:
            first = (params["var"], min(int(k) for k in params["initial"]))
        except (TypeError, ValueError):
            first = None
    doms: dict = {}

    def ok(pt) -> bool:
        sub = {}
        for s_, v in pt.items():
            sym = ctx.ns.get(s_.name)
            if not isinstance(sym, sp.Symbol):
                continue
            if first is not None and s_.name == first[0] and v < first[1]:
                return False
            if s_.name not in doms:
                doms[s_.name] = ctx.domain_for(sym)
            if doms[s_.name].contains(v) is not sp.true:
                return False
            sub[sym] = v
        for c in conds:
            fs = getattr(c, "free_symbols", set())
            if not fs & set(sub):
                continue
            if not fs <= set(sub) or c.subs(sub) is not sp.true:
                return False
        return True
    return ok


def _integer_parameter(s) -> bool:
    import sympy as sp
    return any(x.is_integer for x in getattr(s, "free_symbols", set()) if isinstance(x, sp.Symbol))


def _curves_differ(a, b, admissible=None) -> bool:
    """A point of the curve `a` (grid values for all its symbols but one, the last one solved for
    exactly) where `b` is defined and does not hold. Only polynomial equations are solved."""
    import sympy as sp
    syms = sorted(set(a.free_symbols) | set(b.free_symbols), key=lambda s_: s_.name)
    if not syms or not all(isinstance(s_, sp.Symbol) for s_ in syms):
        return False
    fa = a.lhs - a.rhs
    solve_for, rest = syms[-1], syms[:-1]
    if not fa.has(solve_for) or not fa.is_polynomial(solve_for):
        return False
    for pt in (_points(rest) if rest else [{}])[:16]:
        try:
            roots = sp.solveset(fa.subs(pt), solve_for, sp.S.Reals)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(roots, sp.FiniteSet):
            continue
        for r in list(roots)[:4]:
            full = {**pt, solve_for: r}
            try:
                if admissible is not None and not admissible(full):
                    continue
            except Exception:  # noqa: BLE001
                continue
            lv, rv = _real_value(b.lhs, full), _real_value(b.rhs, full)
            if lv is not None and rv is not None and _is_zero(fa.subs(full)) is True and _nonzero(lv - rv):
                return True
    return False


def _eq_ratio(a, b):
    """For two equations: (l1 - r1) / (l2 - r2), simplified. A nonzero constant means the same
    curve; anything with a free symbol means different curves (for the lines, circles and
    tangent lines this set contains)."""
    import sympy as sp
    try:
        return sp.simplify((a.lhs - a.rhs) / (b.lhs - b.rhs))
    except Exception:  # noqa: BLE001
        return None


def _differs(a, b, *, mod_constant: bool = False, var=None, admissible=None) -> bool:
    """True only when SymPy can PROVE a != b (up to an additive constant if asked; `var` is the
    variable of integration, `admissible` the problem's domain for a point proof)."""
    import sympy as sp
    if isinstance(a, sp.Equality) or isinstance(b, sp.Equality):
        if not (isinstance(a, sp.Equality) and isinstance(b, sp.Equality)):
            return False
        r = _eq_ratio(a, b)
        if r is not None and not r.free_symbols:
            return r == 0
        # a ratio SymPy could not reduce is no proof: the same circle with a nested radical on the
        # right, sqrt(...) = 3 against its square (audit of 29 Sep 2026). A point of one curve that
        # is not on the other is.
        return _curves_differ(a, b, admissible) or _curves_differ(b, a, admissible)
    if isinstance(a, sp.Set) or isinstance(b, sp.Set):
        try:
            a, b = _exact(a), _exact(b)
            if a == b or _integer_parameter(a) or _integer_parameter(b):
                return False                       # a set over k in Z is not compared member by member
            # only a complement SymPy REDUCED to a nonempty set proves a difference; an unevaluated
            # one (a member it cannot compare, an endpoint written as a nested radical) does not
            return any(c.is_empty is False and not isinstance(c, sp.Complement)
                       for c in (sp.Complement(a, b), sp.Complement(b, a)))
        except Exception:  # noqa: BLE001
            return False
    if isinstance(a, sp.MatrixBase) or isinstance(b, sp.MatrixBase):
        try:
            return a.shape == b.shape and any(_is_zero(x - y) is False for x, y in zip(a, b))
        except Exception:  # noqa: BLE001
            return False
    try:
        if a == b:
            return False                           # oo and oo, the same expression
        a, b = _real_roots(a), _real_roots(b)
        d = a - b
    except Exception:  # noqa: BLE001 - a Boolean or anything without a difference
        return False
    if mod_constant:
        free = getattr(d, "free_symbols", set())
        if not free:
            return False                           # differs only by a constant: equivalent
        # only the variable of integration: a parameter's term (a**3/3) is a constant
        wrt = [var] if var is not None else list(free)
        try:
            if any(_is_zero(sp.diff(d, s)) is False for s in wrt):
                return True
        except Exception:  # noqa: BLE001
            pass
        return _differs_at_a_point(a, b, mod_constant=True, var=var, admissible=admissible)
    return _is_zero(d) is False or _differs_at_a_point(a, b, admissible=admissible)


def _equal(a, b, *, mod_constant: bool = False, var=None) -> bool:
    import sympy as sp
    if isinstance(a, sp.Equality) or isinstance(b, sp.Equality):
        if not (isinstance(a, sp.Equality) and isinstance(b, sp.Equality)):
            return False
        r = _eq_ratio(a, b)
        return r is not None and not r.free_symbols and r != 0 and r.is_finite is not False
    if isinstance(a, sp.Set) or isinstance(b, sp.Set):
        try:
            return bool(a == b) or (sp.Complement(a, b) == sp.S.EmptySet and sp.Complement(b, a) == sp.S.EmptySet)
        except Exception:  # noqa: BLE001
            return False
    if isinstance(a, sp.MatrixBase) or isinstance(b, sp.MatrixBase):
        try:
            return a.shape == b.shape and all(_is_zero(x - y) is True for x, y in zip(a, b))
        except Exception:  # noqa: BLE001
            return False
    try:
        d = _real_roots(a) - _real_roots(b)
    except Exception:  # noqa: BLE001
        return False
    if mod_constant:
        free = getattr(d, "free_symbols", set())
        wrt = [var] if var is not None else list(free)
        return all(_is_zero(sp.diff(d, s)) is True for s in wrt) if free else True
    return _is_zero(d) is True


def _pstr(e) -> str:
    """A payload string the verifier's canonical parser accepts."""
    import sympy as sp
    if isinstance(e, sp.Equality):
        return f"{sp.sstr(e.lhs)} = {sp.sstr(e.rhs)}"
    return sp.sstr(e)


def variants(gold, shape: str, kind_task: str, ns, var=None) -> tuple[list[tuple[str, Any]], list[tuple[str, Any]]]:
    """(wrong, equivalent) lists of (name, sympy object). `var` is the task's own variable: a parameter
    picked by name (a before x) made `plus_x` of an antiderivative gold + a, a constant apart, not wrong
    (audit of 29 Sep 2026)."""
    import sympy as sp
    wrong: list[tuple[str, Any]] = []
    equiv: list[tuple[str, Any]] = []
    if isinstance(gold, sp.MatrixBase):
        g = gold.as_mutable()
        w = g.copy()
        w[0] = w[0] + 1
        wrong.append(("entry_plus_one", w))
        wrong.append(("negated", -g))
        equiv.append(("same_matrix_rebuilt", sp.Matrix(g.tolist())))
        return wrong, equiv
    if isinstance(gold, sp.Equality):
        lhs, rhs = gold.lhs, gold.rhs
        wrong.append(("rhs_plus_one", sp.Eq(lhs, rhs + 1, evaluate=False)))
        wrong.append(("rhs_doubled", sp.Eq(lhs, 2 * rhs, evaluate=False)))
        equiv.append(("moved_to_one_side", sp.Eq(sp.expand(lhs - rhs), 0, evaluate=False)))
        equiv.append(("scaled_by_2", sp.Eq(sp.expand(2 * lhs), sp.expand(2 * rhs), evaluate=False)))
        equiv.append(("sides_swapped", sp.Eq(rhs, lhs, evaluate=False)))
        return wrong, equiv
    if isinstance(gold, sp.FiniteSet):
        els = list(gold.args)
        if len(els) > 1:
            wrong.append(("dropped_member", sp.FiniteSet(*els[:-1])))
            equiv.append(("permuted", sp.FiniteSet(*reversed(els))))
        if els and all(getattr(e, "is_number", False) for e in els):
            extra = els[-1] + 1
            if extra not in gold:
                wrong.append(("extra_member", sp.FiniteSet(*els, extra)))
            wrong.append(("shifted", sp.FiniteSet(*[e + 1 for e in els])))
        return wrong, equiv
    if isinstance(gold, (sp.Interval, sp.Union)):
        ivs = list(gold.args) if isinstance(gold, sp.Union) else [gold]
        first = ivs[0]
        if isinstance(first, sp.Interval) and first.inf.is_finite:
            flipped = sp.Interval(first.inf, first.sup, not first.left_open, first.right_open)
            wrong.append(("left_endpoint_flipped", sp.Union(flipped, *ivs[1:])))
        last = ivs[-1]
        if isinstance(last, sp.Interval) and last.sup.is_finite:
            flipped = sp.Interval(last.inf, last.sup, last.left_open, not last.right_open)
            wrong.append(("right_endpoint_flipped", sp.Union(*ivs[:-1], flipped)))
        if isinstance(first, sp.Interval) and first.inf.is_finite:
            wrong.append(("left_endpoint_shifted",
                          sp.Union(sp.Interval(first.inf - 1, first.sup, first.left_open, first.right_open), *ivs[1:])))
        equiv.append(("same_set_rebuilt", sp.Union(*ivs)))
        return wrong, equiv
    if not isinstance(gold, sp.Expr):
        return wrong, equiv
    free = sorted(gold.free_symbols, key=lambda s: s.name)
    mod_c = kind_task == "antiderivative"
    if not free:                                          # a number
        if gold != 0:
            wrong += [("negated", -gold), ("doubled", 2 * gold)]
        wrong += [("plus_one", gold + 1), ("minus_one", gold - 1), ("plus_half", gold + sp.Rational(1, 2)),
                  ("perturbed_1e-9", gold + sp.Rational(1, 10**9)),
                  ("relative_1e-6", gold * (1 + sp.Rational(1, 10**6)) if gold != 0 else sp.Rational(1, 10**6))]
        equiv += [("times_one_unevaluated", sp.Mul(1, gold, evaluate=False)),
                  ("nsimplified", sp.nsimplify(gold)),
                  ("radsimp", sp.radsimp(gold))]
        # Only a TERMINATING decimal is the same number. The parser reads decimals as exact
        # rationals (0.5 -> 1/2), so a truncated 2.666…67 is not 8/3, and scoring it as an
        # "equivalent" would reward the old tolerance accident that accepted ≥21-digit
        # truncations and rejected shorter ones.
        if gold.is_Rational and not gold.is_Integer:
            q = int(gold.q)
            while q % 2 == 0:
                q //= 2
            while q % 5 == 0:
                q //= 5
            if q == 1:
                from decimal import Decimal
                equiv.append(("decimal", sp.Float(str(Decimal(int(gold.p)) / Decimal(int(gold.q))), 30)))
    else:                                                 # an expression in the problem's symbols
        x = var if var in free else free[0]
        wrong += [("plus_x", gold + x), ("doubled", 2 * gold), ("shifted_argument", gold.subs(x, x + 1))]
        if not mod_c:
            wrong.append(("plus_one", gold + 1))
        equiv += [("expanded", sp.expand(gold)), ("factored", sp.factor(gold)),
                  ("together", sp.together(gold))]
        if mod_c:
            equiv.append(("plus_constant", gold + 7))
    return wrong, equiv


def non_answers(ir: dict[str, Any]) -> list[tuple[str, str]]:
    """Payloads that are not answers at all: the question written back, or a request for the
    CAS to compute it. Before claims were parsed in a value-only namespace, every one of these
    was certified CORRECT — the verifier was producing the answer it was meant to check."""
    t, p = ir["task"]["kind"], ir["task"].get("params") or {}
    out: list[tuple[str, str]] = []
    if t == "evaluate" and p.get("expr"):
        out.append(("restates_target", str(p["expr"])))
    if t == "antiderivative":
        out.append(("integrate_call", f"integrate({p['integrand']}, {p.get('var', 'x')})"))
    if t == "definite_integral":
        out.append(("integrate_call", f"integrate({p['integrand']}, ({p.get('var', 'x')}, {p['a']}, {p['b']}))"))
        out.append(("latex_integral", f"\\int_{{{p['a']}}}^{{{p['b']}}} {p['integrand']} \\, d{p.get('var', 'x')}"))
    if t == "derivative" and p.get("f"):
        out.append(("diff_call", f"diff({p['f']}, {p.get('var', 'x')})"))
    if t == "limit" and p.get("expr"):
        out.append(("limit_call", f"limit({p['expr']}, {p.get('var', 'x')}, {p['to']})"))
    if t == "series_sum" and p.get("term"):
        out.append(("sum_object", f"Sum({p['term']}, ({p.get('var', 'k')}, {p.get('lo', 1)}, {p.get('hi', 'oo')}))"))
    for fn in ir.get("functions") or []:
        out.append(("own_function", f"{fn['name']}(1)"))
    return out


_STEP_EQUIV = {
    # the perturbation families of "Beyond the Answer Key" (arXiv:2608.28725), which measured
    # 75–85% false rejection of VALID non-canonical steps in LLM step verifiers
    "add_to_both_sides": lambda l, r: (f"({l}) + 7", f"({r}) + 7"),
    "scale_both_sides": lambda l, r: (f"2*({l})", f"2*({r})"),
    "swap_sides": lambda l, r: (r, l),
    "move_to_one_side": lambda l, r: (f"({l}) - ({r})", "0"),
}


# Why the step refuter may stay silent on a broken step, by design. A miss for any other
# reason is unexplained and fails a gate in scripts/check.py. The report used to print one
# fixed sentence ("the solver's own symbols `t`, `u`, or premises with no solution") whatever
# the sweep measured; checked one by one on 23 Sep it held, but the symbols were n, a, t, u, t
# and nothing would have noticed a new kind of miss.
ACCEPTED_MISS_REASONS = {
    "undeclared_symbol": "çözücünün kendi sembolü: özdeşlik mi çözülen denklem mi olduğu belirsiz, "
                         "bilerek atlanır (DECISIONS §3.3)",
    "premises_have_no_solution": "öncüllerin hiç çözümü yok (altın cevap boş küme): karşı örnek "
                                 "olabilecek nokta yok",
}


def _missed_step_reason(res, step_id: str, gold_is_empty) -> dict[str, str]:
    """Why a broken step did not stop a CORRECT verdict, read from the step layer's evidence.
    `gold_is_empty` is a thunk so the gold answer is only parsed when the reason needs it."""
    import re
    for layer in res.layers:
        if layer.layer != "steps.refute":
            continue
        for e in (layer.evidence or {}).get("steps", []):
            if e.get("id") != step_id:
                continue
            raw = e.get("reason") or (e.get("evidence") or {}).get("reason") or ""
            reason = raw.split(":", 1)[0] or str(e.get("status"))
            detail = ""
            if reason == "undeclared_symbol":
                m = re.search(r"\[([^\]]*)\]", raw)
                detail = m.group(1).replace("'", "") if m else ""
            elif reason == "premises_inconsistent_or_unsolved" and gold_is_empty():
                # "or_unsolved" alone could hide a solver failure; only a problem whose answer
                # is the empty set proves the premises are inconsistent
                reason = "premises_have_no_solution"
            return {"status": str(e.get("status")), "reason": reason, "detail": detail}
        return {"status": "absent", "reason": "step_not_in_evidence", "detail": ""}
    return {"status": "absent", "reason": "steps_layer_absent", "detail": ""}


def step_perturbations(items) -> dict[str, Any]:
    """Rewrite one `eq` step of a correct solution. A valid rewrite must never make the verdict
    INCORRECT (the refuter only refutes with a counterexample); a rewrite that makes the step
    false while leaving the final answer right is a D cell and should be caught."""
    import sympy as sp
    from mathverify.verifier import verify
    from mathverify.intake.structured import load_problem_ir
    from mathverify.normalize.parse import _split_top_level, build_namespace, parse_answer, preclean

    def _empty_gold(ir, gold) -> bool:
        try:
            return parse_answer("set", str(gold), build_namespace(load_problem_ir(ir))) == sp.S.EmptySet
        except Exception:  # noqa: BLE001
            return False
    out = {"equiv": Counter(), "broken": Counter(), "false_rejects": [], "missed_breaks": []}
    for it in items:
        if it["cell"] not in ("A", "B"):
            continue
        ir, sol, labels = split_for_verifier(it)
        try:
            base = verify(ir, sol).verdict
        except Exception:  # noqa: BLE001
            continue
        if base != "CORRECT":
            continue
        for idx, st in enumerate(sol.get("steps") or []):
            if st.get("kind") != "eq" or not st.get("claim"):
                continue
            parts = _split_top_level(preclean(st["claim"]))
            if len(parts) != 2 or parts[1][0] not in ("=", "=="):
                continue
            lhs, rhs = parts[0][1].strip(), parts[1][1].strip()
            for name, fn in _STEP_EQUIV.items():
                l2, r2 = fn(lhs, rhs)
                s2 = json.loads(json.dumps(sol))
                s2["steps"][idx]["claim"] = f"{l2} = {r2}"
                v = verify(ir, s2).verdict
                out["equiv"]["n"] += 1
                out["equiv"][v] += 1
                if v == "INCORRECT":
                    out["false_rejects"].append({"id": labels["id"], "step": st["id"], "family": name,
                                                 "claim": s2["steps"][idx]["claim"]})
            s3 = json.loads(json.dumps(sol))
            s3["steps"][idx]["claim"] = f"{lhs} = ({rhs}) + 1"
            res = verify(ir, s3)
            v = res.verdict
            out["broken"]["n"] += 1
            out["broken"][v] += 1
            if v == "CORRECT":
                why = _missed_step_reason(res, st["id"], lambda: _empty_gold(ir, labels["gold_answer"]))
                out["missed_breaks"].append({"id": labels["id"], "step": st["id"],
                                             "claim": s3["steps"][idx]["claim"], **why,
                                             "accepted": why["reason"] in ACCEPTED_MISS_REASONS})
            break                                         # one step per item keeps it tractable
    return {"equiv": dict(out["equiv"]), "broken": dict(out["broken"]),
            "false_rejects": out["false_rejects"], "missed_breaks": out["missed_breaks"]}


def run(items, limit_unique: int | None = None) -> dict[str, Any]:
    import sympy as sp
    from mathverify.verifier import verify
    from mathverify.intake.structured import load_problem_ir
    from mathverify.normalize.parse import build_namespace, parse_answer

    seen: set[str] = set()
    per_variant: dict[str, Counter] = {}
    false_accepts: list[dict] = []
    false_rejects: list[dict] = []
    skipped: Counter = Counter()
    n_problems = 0
    t0 = time.perf_counter()
    for it in items:
        if it["cell"] not in ("A", "B"):
            continue                                       # gold is the claim's truth only there
        ir, sol, labels = split_for_verifier(it)
        key = json.dumps(ir, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        if limit_unique and n_problems >= limit_unique:
            break
        n_problems += 1
        shape = ir.get("answer_shape", "scalar")
        kind = sol["claimed_answer"]["kind"]
        if kind in ("dne", "infinite", "none", "condition"):
            skipped["answer_kind_" + kind] += 1
            continue
        try:
            ns = build_namespace(load_problem_ir(ir))
            gold = parse_answer(kind, str(it["gold_answer"]), ns)
        except Exception as e:  # noqa: BLE001
            skipped[f"gold_unparsed:{type(e).__name__}"] += 1
            continue
        task = ir["task"]["kind"]
        mod_c = task == "antiderivative"
        task_var = ns.get((ir["task"].get("params") or {}).get("var") or "")
        var = task_var if mod_c else None
        adm = admissible_points(ir)
        wrong, equiv = variants(gold, shape, task, ns, var=task_var)
        ir_no_opt = dict(ir, options=None)
        for name, payload in non_answers(ir):
            s2 = {"claimed_answer": {"kind": "expression" if kind == "expression" else "value",
                                     "payload": payload, "option": None}, "steps": []}
            try:
                verdict = verify(ir_no_opt, s2).verdict
            except Exception as e:  # noqa: BLE001
                verdict = f"ERROR:{type(e).__name__}"
            c = per_variant.setdefault(f"non_answer:{name}", Counter())
            c["n"] += 1
            c[verdict] += 1
            if verdict == "CORRECT":
                false_accepts.append({"id": labels["id"], "task": task, "variant": f"non_answer:{name}",
                                      "payload": payload, "gold": str(it["gold_answer"]), "verdict": verdict})
        for label, group in (("wrong", wrong), ("equiv", equiv)):
            for name, v in group:
                ok = (_differs(v, gold, mod_constant=mod_c, var=var, admissible=adm) if label == "wrong"
                      else _equal(v, gold, mod_constant=mod_c, var=var))
                if not ok:
                    skipped[f"{label}:{name}:not_proved"] += 1
                    continue
                payload = _pstr(v)
                vkind = "equation" if isinstance(v, sp.Equality) else (
                    "set" if isinstance(v, sp.FiniteSet) else
                    "interval" if isinstance(v, (sp.Interval, sp.Union)) else
                    ("count" if kind == "count" and v.is_Integer else ("value" if kind == "count" else kind)))
                s2 = {"claimed_answer": {"kind": vkind, "payload": int(v) if vkind == "count" else payload,
                                         "option": None}, "steps": []}
                try:
                    r = verify(ir_no_opt, s2)
                    verdict = r.verdict
                except Exception as e:  # noqa: BLE001
                    verdict = f"ERROR:{type(e).__name__}"
                c = per_variant.setdefault(f"{label}:{name}", Counter())
                c["n"] += 1
                c[verdict] += 1
                rec = {"id": labels["id"], "task": task, "variant": name, "payload": payload,
                       "gold": str(it["gold_answer"]), "verdict": verdict}
                if label == "wrong" and verdict == "CORRECT":
                    false_accepts.append(rec)
                if label == "equiv" and verdict == "INCORRECT":
                    false_rejects.append(rec)
    na_n = sum(c["n"] for k, c in per_variant.items() if k.startswith("non_answer:"))
    na_acc = sum(c.get("CORRECT", 0) for k, c in per_variant.items() if k.startswith("non_answer:"))
    wrong_n = sum(c["n"] for k, c in per_variant.items() if k.startswith("wrong:"))
    equiv_n = sum(c["n"] for k, c in per_variant.items() if k.startswith("equiv:"))
    equiv_unk = sum(c["UNKNOWN"] for k, c in per_variant.items() if k.startswith("equiv:"))
    wrong_unk = sum(c["UNKNOWN"] for k, c in per_variant.items() if k.startswith("wrong:"))
    return {"n_problems": n_problems, "seconds": time.perf_counter() - t0,
            "wrong": {"n": wrong_n, "false_accepts": len(false_accepts), "unknown": wrong_unk},
            "equiv": {"n": equiv_n, "false_rejects": len(false_rejects), "unknown": equiv_unk},
            "non_answer": {"n": na_n, "accepted": na_acc},
            "per_variant": {k: dict(v) for k, v in sorted(per_variant.items())},
            "false_accepts": false_accepts, "false_rejects": false_rejects, "skipped": dict(skipped)}


def render_md(s: dict[str, Any]) -> str:
    w, e = s["wrong"], s["equiv"]
    md = "# Metamorfik sağlamlık taraması (SymPy üretimli yanlış ve eşdeğer cevaplar)\n\n"
    md += f"Problem: **{s['n_problems']}** (A/B öğelerinin tekil IR'ları) · süre: {s['seconds']:.0f} s\n\n"
    md += (f"- **Yanlış cevap varyantı: {w['n']}** — yanlış onay (CORRECT): **{w['false_accepts']}** "
           f"(hedef 0) · UNKNOWN: {w['unknown']}\n")
    md += (f"- **Eşdeğer cevap varyantı: {e['n']}** — yanlış red (INCORRECT): **{e['false_rejects']}** "
           f"(hedef 0) · UNKNOWN (kaybedilen kapsama): {e['unknown']}\n\n")
    st = s.get("steps")
    if st:
        eq_, br = st["equiv"], st["broken"]
        md += "## Adım düzeyi: geçerli dönüşüm hata değildir, bozulan adım yakalanmalıdır\n\n"
        md += (f"- **Geçerli adım dönüşümü: {eq_.get('n', 0)}** (iki tarafa ekle, 2 ile çarp, taraf "
               f"değiştir, bir tarafa topla) — yanlış red (INCORRECT): **{len(st['false_rejects'])}** "
               f"(hedef 0; [10] LLM adım doğrulayıcılarında %75–85 ölçüyor) · UNKNOWN: {eq_.get('UNKNOWN', 0)}\n")
        missed = st["missed_breaks"]
        unexplained = [r for r in missed if not r.get("accepted")]
        md += (f"- **Bir tarafı +1 bozulan adım: {br.get('n', 0)}** — yakalanan (INCORRECT): "
               f"{br.get('INCORRECT', 0)} · kaçırılan (CORRECT): {len(missed)} · "
               f"UNKNOWN: {br.get('UNKNOWN', 0)} · **nedeni açıklanmayan kaçırma: {len(unexplained)}** "
               f"(hedef 0)\n")
        by_reason = Counter(r.get("reason", "?") for r in missed)
        for reason, k in sorted(by_reason.items(), key=lambda kv: (-kv[1], kv[0])):
            why = ACCEPTED_MISS_REASONS.get(reason, "**AÇIKLANMAMIŞ** — adım reddedicinin bu nedenle "
                                                    "susması beklenmiyor, incelenmeli")
            md += f"  - `{reason}`: {k} — {why}\n"
        for r in st["false_rejects"][:20]:
            md += f"  - yanlış red: {r['id']} {r['step']} `{r['family']}`: `{r['claim']}`\n"
        for r in missed[:20]:
            sym = f", sembol `{r['detail']}`" if r.get("detail") else ""
            md += (f"  - kaçırılan: {r['id']} {r['step']}: `{r['claim']}` — adım {r.get('status', '?')}, "
                   f"`{r.get('reason', '?')}`{sym}\n")
        md += "\n"
    md += "## Varyant türüne göre\n\n| Varyant | n | CORRECT | INCORRECT | UNKNOWN |\n|---|---|---|---|---|\n"
    for k, v in s["per_variant"].items():
        md += f"| `{k}` | {v['n']} | {v.get('CORRECT', 0)} | {v.get('INCORRECT', 0)} | {v.get('UNKNOWN', 0)} |\n"
    for title, rows in (("Yanlış onaylar", s["false_accepts"]), ("Yanlış redler", s["false_rejects"])):
        md += f"\n## {title} ({len(rows)})\n\n"
        md += "\n".join(f"- {r['id']} [{r['task']}] `{r['variant']}`: `{r['payload']}` (altın: `{r['gold']}`)"
                        for r in rows[:60]) or "yok"
        md += "\n"
    if s["skipped"]:
        md += "\n## Atlananlar (SymPy'nin kanıtlayamadığı varyantlar puanlanmaz)\n\n"
        md += "\n".join(f"- {k}: {v}" for k, v in sorted(s["skipped"].items())) + "\n"
    return md


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="en fazla bu kadar tekil problem")
    ap.add_argument("--out", default=str(ROOT / "reports"))
    args = ap.parse_args(argv)
    items = load_items(ROOT / "evalset" / "items")
    s = run(items, args.limit)
    s["steps"] = step_perturbations(items if not args.limit else items[:args.limit * 3])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "soundness_results.json").write_text(json.dumps(s, ensure_ascii=False, indent=1, default=str),
                                                encoding="utf-8")
    md = render_md(s)
    (out / "soundness_report.md").write_text(md, encoding="utf-8")
    print(md)
    return s


if __name__ == "__main__":
    main()
