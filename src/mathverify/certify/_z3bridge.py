"""sympy -> z3 translation for word-problem / uniqueness certificates (E7).

Supported: + - * / integer and rational powers, Abs, Max/Min, Mod (ints), floor/ceiling,
relations, And/Or/Not, Piecewise, integer/real sorts. Transcendental functions raise
`Unsupported` (the certificate then returns unknown; it never guesses).
Runs inside the sandbox worker (z3 objects are not picklable across processes).
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

import sympy as sp
import z3


class Unsupported(ValueError):
    pass


class _Tr:
    def __init__(self, syms_info: dict[str, str]):
        self.z: dict[str, Any] = {}
        self.side: list[Any] = []       # side constraints (denominators != 0, roots >= 0)
        self._assumed: set[str] = set()
        self.fresh = 0
        for name, kind in syms_info.items():
            self.z[name] = z3.Int(name) if kind == "int" else z3.Real(name)

    def _fresh_real(self, tag="t"):
        self.fresh += 1
        return z3.Real(f"__{tag}{self.fresh}")

    def tr(self, e):
        if isinstance(e, sp.Symbol):
            if e.name not in self.z:
                self.z[e.name] = z3.Int(e.name) if e.is_integer else z3.Real(e.name)
            if e.name not in self._assumed:
                # SymPy silently evaluates `x > 0` to True for a positive symbol, so the
                # assumption would otherwise be LOST in translation (measured: 3x+5y=41
                # became satisfiable with x=-3). Mirror the assumptions as constraints.
                self._assumed.add(e.name)
                zv = self.z[e.name]
                if e.is_positive:
                    self.side.append(zv > 0)
                elif e.is_nonnegative:
                    self.side.append(zv >= 0)
                elif e.is_negative:
                    self.side.append(zv < 0)
                elif e.is_nonpositive:
                    self.side.append(zv <= 0)
                if e.is_nonzero and not (e.is_positive or e.is_negative):
                    self.side.append(zv != 0)
            return self.z[e.name]
        if isinstance(e, sp.Integer):
            return z3.IntVal(int(e))
        if isinstance(e, sp.Rational):
            return z3.RealVal(f"{e.p}/{e.q}")
        if isinstance(e, sp.Float):
            fr = Fraction(str(e))
            return z3.RealVal(f"{fr.numerator}/{fr.denominator}")
        if e is sp.true:
            return z3.BoolVal(True)
        if e is sp.false:
            return z3.BoolVal(False)
        if isinstance(e, sp.Add):
            return sum((self.tr(a) for a in e.args[1:]), self.tr(e.args[0]))
        if isinstance(e, sp.Mul):
            r = self.tr(e.args[0])
            for a in e.args[1:]:
                r = r * self.tr(a)
            return r
        if isinstance(e, sp.Pow):
            base, ex = e.args
            zb = self.tr(base)
            if isinstance(ex, sp.Integer):
                n = int(ex)
                if n == 0:
                    return z3.IntVal(1)
                if n > 0:
                    r = zb
                    for _ in range(n - 1):
                        r = r * zb
                    return r
                self.side.append(zb != 0)
                r = zb
                for _ in range(-n - 1):
                    r = r * zb
                return z3.RealVal(1) / r
            if isinstance(ex, sp.Rational):
                p, q = int(ex.p), int(ex.q)
                t = self._fresh_real("root")
                # t^q == base^p, t >= 0 for even q (principal root)
                bp = self.tr(base ** p) if p > 0 else z3.RealVal(1) / self.tr(base ** (-p))
                tq = t
                for _ in range(q - 1):
                    tq = tq * t
                self.side.append(tq == bp)
                if q % 2 == 0:
                    self.side.append(t >= 0)
                    self.side.append(zb >= 0)
                return t
            raise Unsupported(f"non-rational exponent {ex}")
        if isinstance(e, sp.Abs):
            a = self.tr(e.args[0])
            return z3.If(a >= 0, a, -a)
        if isinstance(e, sp.Max):
            args = [self.tr(a) for a in e.args]
            r = args[0]
            for a in args[1:]:
                r = z3.If(a > r, a, r)
            return r
        if isinstance(e, sp.Min):
            args = [self.tr(a) for a in e.args]
            r = args[0]
            for a in args[1:]:
                r = z3.If(a < r, a, r)
            return r
        if isinstance(e, sp.Mod):
            a, b = self.tr(e.args[0]), self.tr(e.args[1])
            if not (z3.is_int(a) and z3.is_int(b)):
                raise Unsupported("Mod on non-integers")
            return a % b
        if isinstance(e, sp.floor):
            a = self.tr(e.args[0])
            if z3.is_int(a):
                return a
            t = z3.Int(f"__floor{self._bump()}")
            self.side.append(z3.ToReal(t) <= a)
            self.side.append(a < z3.ToReal(t) + 1)
            return t
        if isinstance(e, sp.ceiling):
            a = self.tr(e.args[0])
            if z3.is_int(a):
                return a
            t = z3.Int(f"__ceil{self._bump()}")
            self.side.append(z3.ToReal(t) >= a)
            self.side.append(a > z3.ToReal(t) - 1)
            return t
        if isinstance(e, sp.Piecewise):
            expr = None
            for val, cond in reversed(e.args):
                v = self.tr(val)
                if expr is None or cond is sp.true:
                    expr = v
                else:
                    expr = z3.If(self.tr(cond), v, expr)
            return expr
        if isinstance(e, sp.Equality):
            return self.tr(e.lhs) == self.tr(e.rhs)
        if isinstance(e, sp.Unequality):
            return self.tr(e.lhs) != self.tr(e.rhs)
        if isinstance(e, sp.StrictLessThan):
            return self.tr(e.lhs) < self.tr(e.rhs)
        if isinstance(e, sp.LessThan):
            return self.tr(e.lhs) <= self.tr(e.rhs)
        if isinstance(e, sp.StrictGreaterThan):
            return self.tr(e.lhs) > self.tr(e.rhs)
        if isinstance(e, sp.GreaterThan):
            return self.tr(e.lhs) >= self.tr(e.rhs)
        if isinstance(e, sp.And):
            return z3.And(*[self.tr(a) for a in e.args])
        if isinstance(e, sp.Or):
            return z3.Or(*[self.tr(a) for a in e.args])
        if isinstance(e, sp.Not):
            return z3.Not(self.tr(e.args[0]))
        if isinstance(e, sp.factorial) and e.args[0].is_Integer:
            return z3.IntVal(int(e))
        if isinstance(e, sp.binomial) and all(a.is_Integer for a in e.args):
            return z3.IntVal(int(e))
        if e.is_number:
            # exact rational?
            try:
                r = sp.nsimplify(e, rational=True)
                if isinstance(r, sp.Rational):
                    return z3.RealVal(f"{r.p}/{r.q}")
            except Exception:
                pass
        raise Unsupported(f"cannot translate {type(e).__name__}: {e}")

    def _bump(self):
        self.fresh += 1
        return self.fresh


def _model_value(m, zsym):
    v = m.eval(zsym, model_completion=True)
    if z3.is_int_value(v):
        return sp.Integer(v.as_long())
    if z3.is_rational_value(v):
        fr = v.as_fraction()
        return sp.Rational(fr.numerator, fr.denominator)
    if z3.is_algebraic_value(v):
        return sp.Float(v.as_decimal(30).rstrip("?"), 30)
    return sp.sympify(str(v))


def build(constraints, syms_info, extra):
    tr = _Tr(syms_info)
    zc = [tr.tr(sp.sympify(c)) for c in constraints]
    ze = [tr.tr(sp.sympify(c)) for c in extra]
    return tr, zc + ze + tr.side


def check_sat(constraints, syms_info, extra, timeout_ms=4000):
    try:
        tr, zs = build(constraints, syms_info, extra)
    except Unsupported as e:
        return "unsupported", str(e)
    s = z3.Solver()
    s.set("timeout", int(timeout_ms))
    for c in zs:
        s.add(c)
    r = s.check()
    if r == z3.sat:
        m = s.model()
        model = {name: str(_model_value(m, z)) for name, z in tr.z.items() if not name.startswith("__")}
        return "sat", model
    if r == z3.unsat:
        return "unsat", None
    return "unknown", None


def enumerate_target(constraints, syms_info, target, timeout_ms=4000, max_models=50):
    """Enumerate distinct values of `target` satisfying constraints (blocking clauses)."""
    try:
        tr, zs = build(constraints, syms_info, [])
        zt = tr.tr(sp.sympify(target))
        zs += tr.side
    except Unsupported as e:
        return "unsupported", str(e)
    s = z3.Solver()
    s.set("timeout", int(timeout_ms))
    for c in zs:
        s.add(c)
    vals = []
    for _ in range(max_models):
        r = s.check()
        if r == z3.unknown:
            return "unknown", vals
        if r == z3.unsat:
            return "complete", vals
        m = s.model()
        v = m.eval(zt, model_completion=True)
        vals.append(str(_model_value(m, zt)))
        s.add(zt != v)
    return "truncated", vals
