"""Domain guard (E2, E4): definedness conditions, root guarding, domain-of-expression.

The most frequent AYT trap: log argument > 0, even root radicand >= 0, denominator != 0,
tan/cot poles, asin/acos range. Every candidate root produced by ANY solver API is
checked here against (a) the problem's domain of discourse, (b) the definedness
conditions of the ORIGINAL expression, and (c) the original relation itself.
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import S, Eq, Ne, Interval, oo

from ..equiv.numeric import num_equal, to_mp
from ..equiv.symbolic import sym_equal
from ..equiv.sets import set_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.domain"


# ---------------------------------------------------------------------------
def definedness_conditions(expr, var) -> list[Any]:
    """Collect conditions under which `expr` is a well-defined real number."""
    conds: list[Any] = []
    seen: set = set()

    def add(c):
        if c is sp.true:
            return
        if c not in seen:
            seen.add(c)
            conds.append(c)

    for node in sp.preorder_traversal(sp.sympify(expr)):
        if isinstance(node, sp.log):
            add(node.args[0] > 0)
            if len(node.args) > 1:
                add(node.args[1] > 0)
                add(Ne(node.args[1], 1))
        elif isinstance(node, sp.Pow):
            base, ex = node.args
            ex = _numeric_exponent(ex)
            if isinstance(ex, sp.Rational) and not ex.is_Integer:
                if ex.q % 2 == 0:
                    add(base >= 0 if ex > 0 else base > 0)
                elif ex < 0:
                    add(Ne(base, 0))
            elif ex.is_Integer and ex < 0:
                add(Ne(base, 0))
            elif ex.is_number and not ex.is_rational:
                add(base > 0)
            elif not ex.is_number and base.free_symbols and (var is None or var in ex.free_symbols):
                add(base > 0)          # x^y style real power (var None: every symbol counts)
        elif isinstance(node, sp.tan):
            add(Ne(sp.cos(node.args[0]), 0))
        elif isinstance(node, sp.sec):
            add(Ne(sp.cos(node.args[0]), 0))
        elif isinstance(node, sp.cot):
            add(Ne(sp.sin(node.args[0]), 0))
        elif isinstance(node, sp.csc):
            add(Ne(sp.sin(node.args[0]), 0))
        elif isinstance(node, (sp.asin, sp.acos)):
            add(node.args[0] >= -1)
            add(node.args[0] <= 1)
        elif isinstance(node, sp.acosh):
            add(node.args[0] >= 1)
        elif isinstance(node, sp.atanh):
            add(node.args[0] > -1)
            add(node.args[0] < 1)
    return conds


def _numeric_exponent(ex):
    """An exponent that is a number but was left unevaluated (`x**(1/2)` read as written is
    Pow(x, Mul(1, Pow(2, -1)))), evaluated exactly so that the Rational rules above apply.
    Measured 25 Sep 2026: read as written, `x**(1/2)` produced NO condition, and the formal layer
    certified "the domain of x**(1/2) is ℝ"."""
    if getattr(ex, "is_number", False) and not ex.is_Atom:
        try:
            return sp.simplify(ex)
        except Exception:  # noqa: BLE001
            return ex
    return ex


# Functions defined on all of ℝ (no condition), and the ones the rules above bound. Anything
# else — factorial or gamma of a variable, Mod, atan2, an undefined function, an integral — has a
# real domain these rules do not describe.
_TOTAL_FUNCS = (sp.sin, sp.cos, sp.exp, sp.Abs, sp.atan, sp.acot, sp.sinh, sp.cosh, sp.tanh,
                sp.asinh, sp.floor, sp.ceiling, sp.frac, sp.sign, sp.Max, sp.Min)
_BOUNDED_FUNCS = (sp.log, sp.tan, sp.sec, sp.cot, sp.csc, sp.asin, sp.acos, sp.acosh, sp.atanh)
# sets are containers: their elements are checked (an ImageSet's Lambda is not, so it refuses)
_CONTAINERS = (sp.Tuple, sp.Set, sp.core.relational.Relational, sp.And, sp.Or, sp.Not)


def _closed_int(e) -> int | None:
    try:
        v = sp.simplify(e)
    except Exception:  # noqa: BLE001
        return None
    return int(v) if isinstance(v, sp.Integer) else None


def definedness_conditions_strict(expr, var=None) -> list[Any] | None:
    """`definedness_conditions`, but EXACT or nothing: None when the expression contains an
    operation whose real domain the rules do not describe (factorial/gamma/gcd of a variable,
    `Mod`, a power with a variable exponent whose base is not a positive constant, an undefined
    function, ...). Measured 25 Sep 2026 (formal-layer audit): `0**x`, `(-2)**x` and
    `factorial(x)` produced no condition, so "the domain is ℝ" was certified both by Lean and by
    the deterministic domain_of certificate. A caller that has to be exact abstains on None."""
    if isinstance(expr, str):
        return None                               # never sympify raw text here
    try:
        e = sp.sympify(expr)
    except (sp.SympifyError, TypeError):
        return None
    for node in sp.preorder_traversal(e):
        if node.is_Atom or isinstance(node, (sp.Add, sp.Mul) + _CONTAINERS + _TOTAL_FUNCS + _BOUNDED_FUNCS):
            continue
        if isinstance(node, sp.Pow):
            base, ex = node.args
            ex = _numeric_exponent(ex)
            if ex.is_number:
                if ex.is_real is True:
                    continue                      # the rules of definedness_conditions apply
                return None
            if base.is_number:
                try:
                    b = sp.simplify(base)
                except Exception:  # noqa: BLE001
                    return None
                if b.is_positive is True:
                    continue                      # c**x with c > 0: defined for every real x
            return None                           # 0**x, (-2)**x, x**x, x**y: no interval rule
        name = type(node).__name__
        if name in ("factorial", "binomial", "gcd", "lcm"):
            if node.free_symbols:
                return None
            ints = [_closed_int(a) for a in node.args]
            if any(i is None for i in ints) or any(i < 0 for i in ints):
                return None
            continue
        return None                               # unknown operation: no exact domain
    conds = definedness_conditions(e, var)
    for node in sp.preorder_traversal(e):
        if isinstance(node, sp.Pow):
            ex = _numeric_exponent(node.args[1])
            if ex.is_number and not ex.is_rational and ex.is_positive is True:
                # 0**pi = 0: a positive irrational exponent needs base >= 0, not > 0
                strict = node.args[0] > 0
                conds = [node.args[0] >= 0 if c == strict else c for c in conds]
    return conds


def _num_relation_holds(rel, var, c) -> bool | None:
    """Evaluate a relational at var=c numerically (exact-ish, ladder)."""
    if rel is sp.true:
        return True
    if rel is sp.false:
        return False
    if not isinstance(rel, sp.core.relational.Relational):
        return None
    lhs = rel.lhs.subs(var, c)
    rhs = rel.rhs.subs(var, c)
    if isinstance(rel, Eq):
        # exact structural first, then numeric
        okS, _ = sym_equal(lhs, rhs)
        if okS:
            return True
        okN, _ = num_equal(lhs, rhs)
        return okN
    if isinstance(rel, Ne):
        okS, _ = sym_equal(lhs, rhs)
        if okS:
            return False
        okN, _ = num_equal(lhs, rhs)
        return None if okN is None else (not okN)
    try:
        a, b = to_mp(lhs, 40), to_mp(rhs, 40)
    except Exception:
        return None
    import mpmath as mp
    if isinstance(a, mp.mpc) or isinstance(b, mp.mpc):
        return False                      # non-real value: relation is not satisfied in R
    eq, _ = num_equal(lhs, rhs)
    if isinstance(rel, sp.StrictLessThan):
        return (a < b) and not eq
    if isinstance(rel, sp.LessThan):
        return (a < b) or bool(eq)
    if isinstance(rel, sp.StrictGreaterThan):
        return (a > b) and not eq
    if isinstance(rel, sp.GreaterThan):
        return (a > b) or bool(eq)
    return None


def relation_holds_at(rel, var, c) -> bool | None:
    """Does the (original) relation hold at var=c? Tri-state."""
    if isinstance(rel, (sp.And, sp.Or)):
        parts = [relation_holds_at(a, var, c) for a in rel.args]
        if isinstance(rel, sp.And):
            if any(p is False for p in parts):
                return False
            return True if all(p is True for p in parts) else None
        if any(p is True for p in parts):
            return True
        return False if all(p is False for p in parts) else None
    if rel is sp.true:
        return True
    if rel is sp.false:
        return False
    if not isinstance(rel, sp.core.relational.Relational):
        return None
    # never let `rel.subs` auto-evaluate a numeric Eq/inequality: Float rounding would
    # turn a true identity into False. Substitute the sides and compare tolerantly.
    return _num_relation_holds(rel, var, c)


def in_domain(dom: sp.Set, c) -> bool | None:
    try:
        r = dom.contains(c)
    except Exception:
        return None
    if r is sp.true:
        return True
    if r is sp.false:
        return False
    # numeric fallback for intervals
    try:
        cv = to_mp(c, 40)
        import mpmath as mp
        if isinstance(cv, mp.mpc):
            return False
        for part in (dom.args if isinstance(dom, sp.Union) else [dom]):
            if isinstance(part, Interval):
                lo = -mp.inf if part.inf == -oo else to_mp(part.inf, 40)
                hi = mp.inf if part.sup == oo else to_mp(part.sup, 40)
                ok_lo = cv > lo if part.left_open else cv >= lo
                ok_hi = cv < hi if part.right_open else cv <= hi
                if ok_lo and ok_hi:
                    return True
        return False
    except Exception:
        return None


def guard_roots(rel, var, candidates, domain: sp.Set = S.Reals) -> tuple[list, list[tuple[Any, str]]]:
    """Return (kept, rejected[(candidate, reason)]) for candidate roots of `rel`."""
    conds = definedness_conditions(rel, var)
    kept, rejected = [], []
    for c in candidates:
        c = sp.sympify(c)
        if c.is_real is False or (c.is_number and not c.is_real and c.is_real is not None):
            rejected.append((c, "not_real"))
            continue
        d = in_domain(domain, c)
        if d is False:
            rejected.append((c, "outside_domain_of_discourse"))
            continue
        bad = None
        for cond in conds:
            h = relation_holds_at(cond, var, c)
            if h is False:
                bad = f"definedness_violated: {cond}"
                break
            if h is None:
                bad = f"definedness_undecided: {cond}"
                break
        if bad:
            rejected.append((c, bad))
            continue
        h = relation_holds_at(rel, var, c)
        if h is True:
            kept.append(c)
        elif h is False:
            rejected.append((c, "does_not_satisfy_original"))
        else:
            rejected.append((c, "undecided_original"))
    return kept, rejected


def written_definedness(src: str, ns: dict[str, Any]) -> tuple[list[Any], set]:
    """Definedness of an IR expression or relation AS WRITTEN (see `parse_as_written`): the open
    conditions, and the symbols of an expression that is defined NOWHERE (a closed condition
    that fails, e.g. `1/(x - x)`). Empty when the text cannot be read that way."""
    from ..normalize.parse import parse_as_written
    e = parse_as_written(src, ns)
    if e is None:
        return [], set()
    conds, nowhere = [], set()
    try:
        found = definedness_conditions(e, None)
    except Exception:  # noqa: BLE001
        return [], set()
    for c in found:
        if c is sp.false:
            nowhere |= e.free_symbols
        elif getattr(c, "free_symbols", None) and c not in conds:
            conds.append(c)
    return conds, nowhere


def written_undefined_in(src: str, ns: dict[str, Any], var, region: sp.Set) -> bool | None:
    """Is the expression, AS WRITTEN, undefined somewhere in `region` (a point set, an interval, an
    index Range)? None when that cannot be decided. Measured 23 Sep 2026 on kinds that keep their
    own domain handling: "(x²/x)' at 0 is 1", "max of x/x − x² on [−1, 1] is 1" (never attained)
    and "Σ_{k=−1}^{1} k/k = 3" were certified CORRECT."""
    conds, nowhere = written_definedness(src, ns)
    if var in nowhere:
        return True
    for c in conds:
        if c.free_symbols - {var}:
            return None
        bad = Eq(c.lhs, c.rhs) if isinstance(c, Ne) else sp.Not(c)
        try:
            s = sp.solveset(bad, var, region)
        except Exception:  # noqa: BLE001
            return None
        if isinstance(s, sp.ConditionSet):
            return None
        if s != S.EmptySet:
            return True
    return False


def domain_of_expression(expr, var, base: sp.Set = S.Reals, timeout: float = 8.0) -> tuple[sp.Set | None, dict]:
    """Domain where `expr` is real-valued: conditions -> solveset intersection; fallback continuous_domain."""
    conds = definedness_conditions_strict(expr, var)
    if conds is None:
        # an operation whose real domain the rules do not describe (0**x, (-2)**x, factorial(x)):
        # no domain rather than ℝ (measured 25 Sep 2026: "the domain of factorial(x) is ℝ" CORRECT)
        return None, {"error": "definedness_unknown", "expr": str(expr)}
    ev: dict[str, Any] = {"conditions": [str(c) for c in conds]}
    dom = base
    for cond in conds:
        r = sb_run("mathverify.sandbox.ops:solveset_in", cond, var, S.Reals, timeout=timeout)
        if not r.ok or isinstance(r.value, sp.ConditionSet):
            ev["fallback"] = "continuous_domain"
            r2 = sb_run("mathverify.sandbox.ops:continuous_domain", expr, var, base, timeout=timeout)
            if r2.ok and not isinstance(r2.value, sp.ConditionSet):
                return r2.value, ev
            ev["error"] = r.error or r2.error
            return None, ev
        dom = sp.Intersection(dom, r.value)
    ev["domain"] = str(dom)
    return dom, ev


# ---------------------------------------------------------------------------
def verify(ir, solution, ctx: Ctx):
    """Task kind `domain_of`: params {"expr": str, "var": str}. Claimed: set/interval."""
    if ir.task.kind != "domain_of":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        var = ctx.sym(ir.task.params.get("var", "x"))
        expr, err = parse_or_unknown(LAYER, ctx.expr, ir.task.params["expr"])
        if err:
            return err
        claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
        if err:
            return err
        if not isinstance(claimed, sp.Set):
            return unknown(LAYER, "claimed_answer_is_not_a_set", t.ms if hasattr(t, "ms") else 0)
        # the expression AS WRITTEN must have a domain the rules describe exactly, too: the normal
        # parse folds `factorial(x)/factorial(x)` to 1 before any rule sees it
        from ..normalize.parse import parse_as_written
        written = parse_as_written(ir.task.params["expr"], ctx.ns)
        if written is not None and any(definedness_conditions_strict(w, var) is None for w in written):
            return unknown(LAYER, "domain_undecidable", 0, {"error": "definedness_unknown_as_written"},
                           flags=["cas_failed"])
        base = ctx.domain_for(var)
        truth, ev = domain_of_expression(expr, var, base, ctx.timeout)
        if truth is None:
            return unknown(LAYER, "domain_undecidable", 0, ev, flags=["cas_failed"])
        ok, sev = set_equal(claimed, truth)
        ev["compare"] = sev
        ev["truth"] = str(truth)
        ev["claimed"] = str(claimed)
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, "set_comparison_undecided", t.ms, ev)
