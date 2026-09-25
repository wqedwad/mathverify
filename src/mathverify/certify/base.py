"""Shared helpers for certificate modules."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import sympy as sp
from sympy import S

from ..ir import ProblemIR
from ..normalize.parse import (build_namespace, parse_relation, parse_expr_str, parse_domain,
                               parse_answer, ParseError, ClaimNotAValue, check_claim_is_value,
                               claim_namespace)
from ..solution import Solution
from ..types import LayerResult


@dataclass
class Ctx:
    """Per-verification context: parsed namespace, symbols, domains, seed, evidence sink."""
    ir: ProblemIR
    ns: dict[str, Any]
    seed: int = 0
    timeout: float = 8.0
    cache: dict[str, Any] = field(default_factory=dict)

    # ---- symbols / domains ------------------------------------------------
    def sym(self, name: str) -> sp.Symbol:
        v = self.ns.get(name)
        if not isinstance(v, sp.Symbol):
            v = sp.Symbol(name, real=True)
            self.ns[name] = v
        return v

    def syms(self) -> list[sp.Symbol]:
        return [self.sym(v.name) for v in self.ir.vars]

    def syms_info(self) -> dict[str, str]:
        out = {}
        for v in self.ir.vars:
            out[v.name] = "int" if v.domain in ("integer", "positive_integer", "nonneg_integer", "natural") else "real"
        return out

    def domain_for(self, var: sp.Symbol) -> sp.Set:
        """Domain of discourse for `var`: IR field ∩ var-domain ∩ var constraints."""
        key = f"dom:{var.name}"
        if key in self.cache:
            return self.cache[key]
        dom = parse_domain(self.ir.domain_of_discourse, var, self.ns) if self._dod_mentions(var) else S.Reals
        vd = next((v for v in self.ir.vars if v.name == var.name), None)
        if vd is not None:
            if vd.domain in ("integer",):
                dom = sp.Intersection(dom, S.Integers)
            elif vd.domain in ("positive_integer", "natural"):
                dom = sp.Intersection(dom, S.Naturals)
            elif vd.domain == "nonneg_integer":
                dom = sp.Intersection(dom, S.Naturals0)
            elif vd.domain == "positive_real":
                dom = sp.Intersection(dom, sp.Interval.open(0, sp.oo))
            elif vd.domain == "nonneg_real":
                dom = sp.Intersection(dom, sp.Interval(0, sp.oo))
            for c in vd.constraints:
                try:
                    rel = parse_relation(c, self.ns)
                    if rel.free_symbols == {var}:
                        dom = sp.Intersection(dom, sp.solveset(rel, var, S.Reals))
                except Exception:
                    pass
        # the problem's own expressions must be defined, as written (see written_conditions)
        conds, nowhere = self.written_conditions()
        if var in nowhere:
            dom = S.EmptySet
        for c in conds:
            if c.free_symbols != {var}:
                continue                               # several variables: var_constraints only
            try:
                sol = sp.solveset(c, var, S.Reals)
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(sol, sp.ConditionSet):
                dom = sp.Intersection(dom, sol)
        self.cache[key] = dom
        return dom

    # Params that hold the problem's own expression, per task kind. `limit` is absent on purpose,
    # and its givens are skipped too: the point a limit approaches is typically exactly where the
    # expression is undefined (lim x→0 of x/x is 1). The calculus kinds keep their own handling.
    _WRITTEN_PARAMS = {"evaluate": ("expr",), "simplify_expression": ("expr",), "domain_of": ("expr",),
                       "solve_equation": ("equation",), "solve_inequality": ("inequality",),
                       "count_roots": ("expr",)}

    def written_conditions(self) -> tuple[list[Any], set]:
        """Definedness of the problem's expressions AS WRITTEN (open conditions, and symbols of an
        expression defined nowhere). SymPy's automatic simplification removes undefined points
        before any condition is read: `x/x` → 1, `sqrt(x)**2` → x, `x**2/x` → x, `log(x) − log(x)`
        → 0. Measured 23 Sep 2026: "the domain of x/x is ℝ", "x²/x = 0 has the root 0",
        "(√x)² = −1 has the root −1", "x/x > 0 on all of ℝ" and "x/x at x = 0 is 1" were all
        certified CORRECT, and the right answers to the first four were refuted. The conditions
        restrict `domain_for` (one variable) and join `var_constraints` (any number)."""
        key = "written_conditions"
        if key in self.cache:
            return self.cache[key]
        from .domain import written_definedness
        kind = self.ir.task.kind
        srcs = [] if kind == "limit" else list(self.ir.givens)
        params = self.ir.task.params or {}
        for k in self._WRITTEN_PARAMS.get(kind, ()):
            if isinstance(params.get(k), str):
                srcs.append(params[k])
        if kind == "evaluate" and not params.get("expr") and self.ir.unknown_of_interest:
            srcs.append(self.ir.unknown_of_interest)
        conds: list[Any] = []
        nowhere: set = set()
        undefined: list[str] = []
        for s_ in srcs:
            cs, nw = written_definedness(s_, self.ns)
            nowhere |= nw
            conds += [c for c in cs if c not in conds]
            if self._undefined_constant(s_):
                undefined.append(s_)
        cs, nw, calls = self._function_call_conditions(srcs)
        nowhere |= nw
        conds += [c for c in cs if c not in conds]
        undefined += calls
        self.cache[key] = (conds, nowhere)
        self.cache["written_undefined"] = undefined
        return conds, nowhere

    def written_undefined(self) -> list[str]:
        """The problem's expressions that are undefined AS WRITTEN with no variable left to choose:
        `log(-1) - log(-1) - 1`, or `f(-1)` for f(x) = log(x) − log(x) + x. The closed condition
        fails, but `nowhere` only records free symbols, so the value SymPy simplified to (−1) was
        certified (audit of 25 Sep 2026). Empty over the complex numbers, where the conditions are
        the real ones."""
        self.written_conditions()
        if (self.ir.domain_of_discourse or "").lower() in ("complex", "c", "ℂ"):
            return []
        return list(self.cache.get("written_undefined", []))

    def _undefined_constant(self, src: str) -> bool:
        from ..normalize.parse import parse_as_written
        from .domain import definedness_conditions
        e = parse_as_written(src, self.ns)
        if e is None or e.free_symbols:
            return False
        try:
            return any(c is sp.false for c in definedness_conditions(e, None))
        except Exception:  # noqa: BLE001
            return False

    def _function_call_conditions(self, srcs: list[str]) -> tuple[list[Any], set, list[str]]:
        """The written definedness of the problem's FUNCTIONS at each point they are called. A body
        is parsed once, with simplification, into the callable the namespace holds, so `f(x) = 0`
        with f = x²/x read as x = 0 and the root 0 was certified (audit of 25 Sep 2026: every task
        kind that calls a problem function). Each call f(a) gets the body's own written conditions
        with the arguments substituted. The third item names the calls undefined at a constant
        point."""
        from sympy.core.function import AppliedUndef
        from ..normalize.parse import parse_as_written
        from .domain import written_definedness
        fdefs = {f.name: f for f in self.ir.functions}
        if not fdefs:
            return [], set(), []
        wns = dict(self.ns)
        wns.update({n: sp.Function(n) for n in fdefs})

        def real_calls(e):
            return e.replace(lambda z: isinstance(z, AppliedUndef) and z.func.__name__ in fdefs,
                             lambda z: self.ns[z.func.__name__](*z.args))

        conds: list[Any] = []
        nowhere: set = set()
        undefined: list[str] = []
        for s_ in srcs:
            tree = parse_as_written(s_, wns)
            if tree is None:
                continue
            for call in tree.atoms(AppliedUndef):
                fd = fdefs.get(call.func.__name__)
                if fd is None or len(call.args) != len(fd.args):
                    continue
                body_ns = dict(self.ns)
                arg_syms = []
                for a in fd.args:
                    body_ns[a] = self.ns.get(a) if isinstance(self.ns.get(a), sp.Symbol) else sp.Symbol(a)
                    arg_syms.append(body_ns[a])
                cs, nw = written_definedness(fd.expr, body_ns)
                args = [real_calls(a) for a in call.args]
                sub = dict(zip(arg_syms, args))
                free = set().union(*(getattr(a, "free_symbols", set()) for a in args))
                if nw:
                    nowhere |= free
                for c in cs:
                    c2 = c.subs(sub, simultaneous=True)
                    if c2 is sp.false:
                        nowhere |= free
                        if not free:
                            undefined.append(str(call))
                    elif getattr(c2, "free_symbols", None) and c2 not in conds:
                        conds.append(c2)
                if nw and not free:
                    undefined.append(str(call))
        return conds, nowhere, undefined

    def _dod_mentions(self, var: sp.Symbol) -> bool:
        d = self.ir.domain_of_discourse
        if not d:
            return False
        d = str(d)
        if " in " in d or any(op in d for op in ("<", ">", "!=")):
            import re
            return re.search(r"\b" + re.escape(var.name) + r"\b", d) is not None
        return len(self.ir.vars) <= 1 or True   # a bare set applies to the single variable

    # ---- parsing ------------------------------------------------------------
    def rel(self, s: str):
        return parse_relation(s, self.ns)

    def expr(self, s: str):
        return parse_expr_str(s, self.ns)

    def givens(self) -> list[Any]:
        return [self.rel(g) for g in self.ir.givens]

    def var_constraints(self) -> list[Any]:
        out = []
        for v in self.ir.vars:
            s_ = self.sym(v.name)
            # evaluate=False: with a positive symbol SymPy would collapse `s > 0` to True and
            # the constraint would vanish before reaching z3 / the samplers
            if v.domain in ("positive_integer", "natural", "positive_real"):
                out.append(sp.Gt(s_, 0, evaluate=False))
            elif v.domain in ("nonneg_integer", "nonneg_real"):
                out.append(sp.Ge(s_, 0, evaluate=False))
            for c in v.constraints:
                out.append(self.rel(c))
        out += [c for c in self.written_conditions()[0] if c not in out]
        return out

    def claim_ns(self, solution: Solution | None = None, **extra) -> dict[str, Any]:
        """Namespace for parsing a CLAIM: the problem's, minus the operators that would compute
        the answer and minus the problem's own functions (see COMPUTING_OPERATORS). Every
        certificate that reads the payload itself must use this — four of them used the full
        namespace, so `integrate(log(x), x)` still passed inside `certify.calculus`."""
        fnames = [f.name for f in self.ir.functions]
        if solution is not None:
            check_claim_is_value(solution.claimed_answer.payload, fnames)
        ns = claim_namespace(self.ns, fnames)
        ns.update(extra)
        return ns

    def claimed(self, solution: Solution):
        """The claimed answer, parsed as a VALUE (see `claim_ns`)."""
        ca = solution.claimed_answer
        v = parse_answer(ca.kind, ca.payload, self.claim_ns(solution))
        calc = (sp.Integral, sp.Derivative, sp.Limit, sp.Sum, sp.Product)
        if getattr(v, "has", None) and v.has(*calc):
            raise ClaimNotAValue(f"claimed answer {ca.payload!r} is an unevaluated computation")
        return v

    def option_value(self, letter: str):
        if not self.ir.options or letter not in self.ir.options:
            return None
        return parse_answer(self.ir.answer_shape if self.ir.answer_shape in ("set", "interval") else "value",
                            self.ir.options[letter], self.ns)


def make_ctx(ir: ProblemIR, seed: int = 0, timeout: float = 8.0) -> Ctx:
    return Ctx(ir=ir, ns=build_namespace(ir), seed=seed, timeout=timeout)


class Timer:
    """Context timer; `.ms` is live inside the block and frozen after exit."""

    def __enter__(self):
        self.t0 = time.perf_counter()
        self._ms = None
        return self

    def __exit__(self, *a):
        self._ms = (time.perf_counter() - self.t0) * 1000

    @property
    def ms(self) -> float:
        if self._ms is not None:
            return self._ms
        return (time.perf_counter() - self.t0) * 1000


def result(layer: str, verdict: str, confidence: float, hard: bool, evidence: dict, ms: float,
           primary: bool = False, first_bad_step: int | None = None,
           flags: list[str] | None = None) -> LayerResult:
    return LayerResult(layer=layer, verdict=verdict, confidence=float(confidence), hard=hard,
                       evidence=evidence, latency_ms=round(ms, 2), primary=primary,
                       first_bad_step=first_bad_step, flags=list(flags or []))


def unknown(layer: str, reason: str, ms: float = 0.0, evidence: dict | None = None,
            flags: list[str] | None = None) -> LayerResult:
    ev = dict(evidence or {})
    ev["reason"] = reason
    return result(layer, "unknown", 0.0, False, ev, ms, flags=flags)


def parse_or_unknown(layer: str, fn, *args, **kw):
    """Run a parse; on ParseError return (None, LayerResult unknown)."""
    try:
        return fn(*args, **kw), None
    except ParseError as e:
        return None, unknown(layer, f"parse_error: {e}", flags=["parse_error"])
    except Exception as e:  # noqa: BLE001
        return None, unknown(layer, f"parse_error: {type(e).__name__}: {e}", flags=["parse_error"])
