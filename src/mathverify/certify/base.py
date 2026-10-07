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
                               claim_namespace, given_bindings, not_collapsed, same_value,
                               substitute_free, task_variables)
from ..sandbox.exactsets import at_risk, exact_intersection, exact_solveset
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
        # conditions on var that name a symbol no given fixes: dropped here, listed for the
        # certificates (unapplied_conditions)
        unapplied: list = []
        # relations with a trigonometric function: solved last, on the domain the others leave
        # (sandbox.exactsets: SymPy reads them on one period only)
        deferred: list = []
        dom = self._periodic_parts(self.discourse(var), var, deferred)
        if dom.free_symbols - {var}:
            unapplied.append(str(self.ir.domain_of_discourse))
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
                except Exception:  # noqa: BLE001 - the verifier abstains on it (unreadable_constraints)
                    continue
                # a chain (0 < x < 3) is an And, which solveset does not read: each relation alone
                for r in (rel.args if isinstance(rel, sp.And) else (rel,)):
                    try:
                        r = self._with_bound_values(r, var)
                        if r is sp.false:
                            # the values the givens fix contradict it (x < a with a = 0 and x positive): no
                            # point is left. It was dropped, and {2} was certified for x² = 4 (fourth audit G8);
                            # Ctx.binding_issues abstains on the problem before any certificate reads this
                            dom = S.EmptySet
                            continue
                        if r is sp.true:
                            continue
                        if not r.free_symbols:
                            # closed: decided exactly, never dropped
                            from .domain import relation_holds_at
                            h = relation_holds_at(r, var, 0)
                            if h is False:
                                dom = S.EmptySet
                            elif h is None:
                                unapplied.append(c)
                            continue
                        if r.free_symbols == {var} and at_risk(r, var):
                            deferred.append(r)
                        elif r.free_symbols == {var}:
                            dom = exact_intersection(dom, sp.solveset(r, var, S.Reals))
                        elif var in r.free_symbols:
                            unapplied.append(c)
                    except Exception:
                        pass
        # A given inequality on this variable alone restricts it like a declared constraint when
        # the task carries its own relation in params: "x² < 4" with the given "x > 0" is (0, 2),
        # but only the parameter was solved and (−2, 2) was certified (audit of 25 Sep 2026). When
        # the relation itself is a given, the algebra certificates solve the givens as a system.
        # Odd roots are real roots (equiv.numeric.real_odd_roots), as everywhere else.
        rs, _ = self.side_conditions(var)
        side: list = []
        for sol in rs:
            if isinstance(sol, sp.ConditionSet) and sol.sym == var and at_risk(sol.condition, var):
                deferred.append(sol.condition)
                side.append(sol.condition)
            else:
                dom = exact_intersection(dom, sol)
        unapplied += self.cache.get(f"side_unbound:{var.name}", [])
        # the problem's own expressions must be defined, as written (see written_conditions)
        conds, nowhere = self.written_conditions()
        if var in nowhere:
            dom = S.EmptySet
        from .domain import is_convention, is_range_span
        spans: list = []
        for c in conds:
            c = self._with_bound_values(c, var)
            if c is sp.false:
                dom = S.EmptySet
                continue
            fs = getattr(c, "free_symbols", None)
            if is_convention(c) and fs <= {var}:
                spans.append(c)                        # see _forward_ranges
                continue
            if fs != {var}:
                if fs and var in fs:
                    unapplied.append(c)                # the condition itself: see unapplied_conditions
                continue                               # several variables: var_constraints only
            if isinstance(c, sp.Contains):
                # a gcd/lcm argument must be rational (certify.domain); solveset cannot read the
                # condition and it was dropped: (x - 1/2)(x - sqrt(2)) = gcd(x, 2) - gcd(2, x) had
                # its root sqrt(2) certified (30 Sep 2026)
                dom = sp.Intersection(dom, c.args[1]) if c.args[0] == var else sp.ConditionSet(var, c, dom)
                continue
            if at_risk(c, var):
                deferred.append(c)
                continue
            try:
                sol = sp.solveset(c, var, S.Reals)
            except Exception:  # noqa: BLE001
                sol = None
            if sol is None or isinstance(sol, sp.ConditionSet) or sol.has(sp.ConditionSet):
                # never dropped: solved exactly below, or left a ConditionSet the certificates abstain on
                # (`unsolved_conditions`); 2**x + x - 2 <= 1 of an acos was dropped and the domain read as
                # all of x >= 0 (round 8 of part d4b, YO-1)
                deferred.append(c)
                continue
            dom = exact_intersection(dom, sol)           # one writing per endpoint (round 8)
        # the trigonometric conditions before the convention regions: a convention point is one of the
        # domain, and sin(x) > 0 cuts the negative bases of x**(1/3) too
        dom, unsolved = self._periodic_conditions(dom, deferred, var)
        self.cache[f"unsolved:{var.name}"] = unsolved
        from .domain import is_value_convention
        # the points where a value of the problem is ANOTHER value under the other reading (an odd root:
        # the principal value; Mod: Euclidean): see value_convention_region
        _, vback = self._forward_ranges(dom, [c for c in spans if is_value_convention(c)
                                              and not is_range_span(c)], var)
        self.cache[f"valueconv:{var.name}"] = vback
        dom, back = self._forward_ranges(dom, spans, var)
        if back is not S.EmptySet:
            unapplied += [c for c in spans if c not in unapplied]
        self.cache[f"unsolved_side:{var.name}"] = [r for r in unsolved if r in side]
        self.cache[f"reversed:{var.name}"] = back
        self.cache[f"unapplied:{var.name}"] = unapplied
        self.cache[key] = dom
        return dom

    @staticmethod
    def _periodic_parts(dom: sp.Set, var: sp.Symbol, deferred: list) -> sp.Set:
        """`dom` without its unsolved trigonometric conditions (a domain of discourse `sin(x) > 0`
        reads as ConditionSet(x, sin(x) > 0, Reals), normalize.parse.parse_domain), which go to
        `deferred`: they are solved with the others, on what the rest leaves."""
        if isinstance(dom, sp.ConditionSet) and dom.sym == var and at_risk(dom.condition, var):
            deferred.append(dom.condition)
            return Ctx._periodic_parts(dom.base_set, var, deferred)
        if isinstance(dom, sp.Intersection):
            return sp.Intersection(*[Ctx._periodic_parts(a, var, deferred) for a in dom.args])
        return dom

    @staticmethod
    def _periodic_conditions(dom: sp.Set, rels: list, var: sp.Symbol) -> tuple[sp.Set, list]:
        """`dom` cut by relations with a trigonometric function, each solved on the domain the others
        leave (`sandbox.exactsets.exact_solveset`): on a bounded domain the set is rebuilt and checked;
        `cos(x) != 0` on ℝ is ℝ minus the progressions pi/2 + n*pi. SymPy solved them on ℝ and returned
        ONE period: (0, pi) was the domain of log(sin x), so {} was certified for x**2 = 49 with
        sin(x) > 0 and the domain of tan(x) was [0, 2*pi) minus two points (fourth audit G2, 1 Oct 2026).
        One that stays unsolved (sin(x) > 0 on ℝ) cuts `dom` as a ConditionSet: membership of a point
        is still decided, the set is not known in closed form; it is listed (`unsolved_conditions`)."""
        unsolved: list = []
        for r in rels:
            try:
                s_ = exact_solveset(r, var, dom)
            except Exception:  # noqa: BLE001 - unsolved, as below
                s_ = sp.ConditionSet(var, r, dom)
            if isinstance(s_, sp.ConditionSet) or s_.has(sp.ConditionSet):
                unsolved.append(r)
                dom = sp.Intersection(dom, sp.ConditionSet(var, r, S.Reals))
            else:
                dom = s_
        return dom, unsolved

    def cut_by(self, var: sp.Symbol, dom: sp.Set, rels) -> sp.Set | None:
        """`dom` cut by the relations on `var` alone, or None when one cannot be solved. A relation with
        a trigonometric function is solved last, on the domain the others leave (sandbox.exactsets: on
        ℝ SymPy gave ONE period, (0, pi) for sin(x) > 0, and {} was certified for x**2 = 49 with that
        given, fourth audit G2); one that stays unsolved there cuts `dom` as a ConditionSet, which
        decides the membership of each point exactly and nothing more."""
        from ..sandbox import run as sb_run
        late = [g for g in rels if at_risk(g, var)]
        for g in [g for g in rels if not at_risk(g, var)] + late:
            risky = at_risk(g, var)
            rr = sb_run("mathverify.sandbox.ops:solveset_in", g, var, dom if risky else S.Reals,
                        timeout=self.timeout)
            if not rr.ok:
                return None
            if isinstance(rr.value, sp.ConditionSet) or rr.value.has(sp.ConditionSet):
                if not risky:
                    return None
                dom = sp.Intersection(dom, sp.ConditionSet(var, g, S.Reals))
            else:
                dom = rr.value if risky else exact_intersection(dom, rr.value)
        return dom

    @staticmethod
    def condition_set(cond, var: sp.Symbol) -> sp.Set | None:
        """The reals where a condition on `var` alone holds (`normalize.parse.read_condition`): an And is
        the intersection of its parts, an Or their union, a membership of `var` its set, a relation its
        exact solution set (odd roots real). A closed part is decided exactly. None when a part cannot be
        solved exactly, is undecided, or has a trigonometric function (SymPy reads it on one period)."""
        from ..equiv.numeric import real_odd_roots
        from .domain import relation_holds_at
        if cond is sp.true:
            return S.Reals
        if cond is sp.false:
            return S.EmptySet
        if isinstance(cond, (sp.And, sp.Or)):
            parts = [Ctx.condition_set(a, var) for a in cond.args]
            if any(p is None for p in parts):
                return None
            return sp.Intersection(*parts) if isinstance(cond, sp.And) else sp.Union(*parts)
        if not getattr(cond, "free_symbols", None):
            try:
                h = relation_holds_at(cond, sp.Dummy("_closed"), 0)
            except Exception:  # noqa: BLE001
                return None
            return None if h is None else (S.Reals if h else S.EmptySet)
        if cond.free_symbols != {var}:
            return None
        if isinstance(cond, sp.Contains):
            st = cond.args[1]
            return sp.Intersection(st, S.Reals) if cond.args[0] == var and not st.free_symbols else None
        if not isinstance(cond, sp.core.relational.Relational):
            return None
        r = real_odd_roots(cond)
        if at_risk(r, var):
            return None
        try:
            sol = sp.solveset(r, var, S.Reals)
        except Exception:  # noqa: BLE001
            return None
        if isinstance(sol, sp.ConditionSet) or sol.has(sp.ConditionSet):
            return None
        return sol

    def unsolved_side_conditions(self, var: sp.Symbol) -> list:
        """The side conditions (`side_conditions`) among `unsolved_conditions`: a given like sin(x) > 0
        next to the task's own relation that no bounded domain lets `domain_for` solve. The verifier
        abstains on it as on any side condition it cannot solve (`given_not_applied`)."""
        self.domain_for(var)
        return list(self.cache.get(f"unsolved_side:{var.name}", []))

    def unsolved_conditions(self, var: sp.Symbol) -> list:
        """The relations on `var` (a trigonometric one, or a written condition no exact class solves, round 8)
        that cut its domain unsolved (as a
        ConditionSet, see `_periodic_conditions`). A certificate that reads the domain as a solved set
        (compares it, enumerates it, takes its ends) abstains while this is not empty
        (`condition_unsolved`); one that only decides the membership of points reads it as it is."""
        self.domain_for(var)
        return list(self.cache.get(f"unsolved:{var.name}", []))

    @staticmethod
    def _forward_ranges(dom: sp.Set, spans: list, var: sp.Symbol) -> tuple[sp.Set, sp.Set]:
        """(the points of `dom` where every convention condition of the problem holds (a Sum/Product
        range runs forward or is empty, an odd root's base is not negative, ...: `certify.domain.
        Convention`), the points where one does not): see `convention_region`. A condition solveset
        cannot split keeps `dom` as it was (the condition was not applied before either) and makes
        every point undecided."""
        from .domain import convention_split
        if not spans:
            return dom, S.EmptySet
        fwd_all, back_all = S.Reals, S.EmptySet
        for c in spans:
            fwd, back = convention_split(c, var)
            fwd_all = sp.Intersection(fwd_all, fwd)
            back_all = sp.Union(back_all, back)
        back = sp.Intersection(dom, back_all)
        try:
            empty = back.is_empty
        except Exception:  # noqa: BLE001
            empty = None
        return sp.Intersection(dom, fwd_all), (S.EmptySet if empty is True else back)

    def convention_region(self, var: sp.Symbol) -> sp.Set:
        """The points of `var`'s domain where the value of one of the problem's expressions is a
        convention, not the curriculum's (`reversed_region` for every `certify.domain.Convention`, part
        d4a): an odd root of a negative base (x**(1/3) at x = -8: -2 or 1 + √3 i), 0**0, C(n, r) outside
        0 <= r <= n, Mod with a divisor that is not positive, a Sum/Product range that runs backwards.
        `domain_for` leaves them out, and a candidate there is neither kept nor dropped."""
        return self.reversed_region(var)

    def value_convention_region(self, var: sp.Symbol) -> sp.Set:
        """The part of `convention_region` where the other reading gives ANOTHER value, not "undefined":
        an odd root of a negative base (real root or principal value), Mod by a divisor that is not
        positive (floored or Euclidean). There a comparison made on `domain_for` alone decides nothing:
        (x**3)**(1/3) agrees with Abs(x) on x >= 0 and Abs(x) was certified (part d4a, attack A). See
        `convention_counterexample`. A Sum range that runs backwards is left to §80's own rules."""
        self.domain_for(var)
        return self.cache.get(f"valueconv:{var.name}", S.EmptySet)

    def reversed_region(self, var: sp.Symbol) -> sp.Set:
        """The points of `var`'s domain (the declarations, constraints, side conditions and written
        conditions other than the ranges) where a Sum/Product range of the problem runs backwards
        (hi < lo - 1): Σ_{k=1}^{n} k at n = -2. The value there is a convention (Karr's sum, the empty
        sum), not undefined: `domain_for` leaves these points out, so an expression is compared where
        its value is no convention, but a candidate, root or solution there is neither kept nor dropped
        (DECISIONS §80). Dropped like an undefined point, it made the value 3 of Σ_{k=1}^{n} k with
        n**2 = 4 certified (1 Oct 2026). While this is not empty the ranges' conditions are listed in
        `unapplied_conditions`, so a certificate that reads its answer on the domain abstains. The same
        region holds the points of every other convention (`convention_region`, part d4a)."""
        self.domain_for(var)
        return self.cache.get(f"reversed:{var.name}", S.EmptySet)

    def unapplied_conditions(self, var: sp.Symbol, enforced=()) -> list:
        """The conditions on `var` that `domain_for` could not read on `var` alone: a declared
        constraint, the domain of discourse or a side-condition given (as written in the IR), or a
        written condition (the SymPy relation) that still names a symbol no given fixes to a value
        (`x > b` with b free). The domain dropped them silently, so a certificate answered on all of
        ℝ: {-2, 2} for x² = 4 under x > b, (-2, 2) for x² < 4 under x > b, 2 roots of x² − 4 (part vi
        of the third audit, 30 Sep 2026). A certificate whose answer is read on this domain abstains
        while the list is not empty. `enforced`: the written conditions the certificate checks itself,
        with the other symbols left symbolic (guard_roots at each root of √(x − a) = 2, so {a + 4}
        stays certified). A range's condition is never enforced that way (`reversed_region`): the
        domain the certificate checks a root against has already left the reversed points out."""
        from .domain import is_convention
        self.domain_for(var)
        return [c for c in self.cache.get(f"unapplied:{var.name}", [])
                if not (isinstance(c, sp.Basic) and c in enforced and not is_convention(c))]

    def discourse(self, var: sp.Symbol) -> sp.Set:
        """The domain of discourse for `var` (ℝ when it does not mention var), with each other symbol a
        given fixes read as its value: `x > b` with the given b = 0 is (0, oo). Read with b as a symbol
        it was the interval (b, oo), which no certificate could compare or sample."""
        if not self._dod_mentions(var):
            return S.Reals
        ns = dict(self.ns)
        ns.update({s_.name: v for s_, v in self.bindings().items() if s_ != var})
        return parse_domain(self.ir.domain_of_discourse, var, ns)

    def parameter_pins(self) -> dict:
        """`bindings` without the task's own variable (`normalize.parse.task_variables`)."""
        names = task_variables(self.ir)
        return {s_: v for s_, v in self.bindings().items() if s_.name not in names}

    _DECLARED_SETS = {"integer": S.Integers, "positive_integer": S.Naturals, "natural": S.Naturals,
                      "nonneg_integer": S.Naturals0, "positive_real": sp.Interval.open(0, sp.oo),
                      "nonneg_real": sp.Interval(0, sp.oo)}

    def binding_issues(self) -> tuple[str, list[str]] | None:
        """Why the values the givens fix (`bindings`, and a declared constraint `a = c`) cannot be used,
        or None. Each binding was used unchecked (fourth audit G7, G8, G9, TAN-01, TAN-03, TAN-04, P1):
        x² < 4 with x > a, a = 1 and a < 0 had (1, 2) certified; a = 0 with a declared positive, a > 1 or
        a − 1 = 0 next to it had {2} certified for x² = 4 under x > a; x < a with a = 0 and x positive
        was dropped from the domain; x + log(a) − log(a) = 2 had {2} certified with a = −1, and so did
        every task with log(a), √a, acos(a), a/a, tan(a), a!, C(a, 2), gcd(a, 2) or a Σ_{k=1}^{a} at a
        value where it is undefined, a convention or a reversed range; d/dx F(x) for F(x) = ∫_0^x t² dt
        with the given x = 2 was 0. The verifier abstains (UNKNOWN) with the first reason found:

          ir_inconsistent               a given or a constraint is false at the values (or closed and false
                                        with no value at all: `pi < 3`), a value is outside
                                        its symbol's declaration or domain, two givens fix one symbol to
                                        two values: the problem has no instance
          problem_undefined_as_written  an expression of the problem, read as written, is undefined at the
                                        values (the value a given writes, log(−1) or 0**0, too)
          given_binds_a_bound_variable  a given fixes a symbol inside an Integral or a Limit where an
                                        enclosing operator binds it (d/da, a Sum's index) or where it is
                                        the task's own variable (`normalize.parse.hold_parametric`)
          given_binding_undecided       one of those checks is not decided exactly (a convention value
                                        such as a reversed range or 0**0, an undecided comparison)"""
        key = "binding_issues"
        if key not in self.cache:
            try:
                self.cache[key] = self._binding_issues()
            except Exception as e:  # noqa: BLE001 - a binding no check reads is not used
                self.cache[key] = ("given_binding_undecided", [f"check failed: {type(e).__name__}"])
        return self.cache[key]

    def _constraint_bindings(self) -> tuple[dict, list]:
        """Declared constraints of the form `a = c` (c a closed real number), and the texts."""
        found: dict = {}
        texts: list = []
        for v in self.ir.vars:
            for c in v.constraints:
                try:
                    rel = parse_relation(c, self.ns)
                except Exception:  # noqa: BLE001 - unreadable_constraints abstains on it
                    continue
                if not isinstance(rel, sp.Eq):
                    continue
                for s_, val in ((rel.lhs, rel.rhs), (rel.rhs, rel.lhs)):
                    if isinstance(s_, sp.Symbol) and isinstance(val, sp.Expr) and not val.free_symbols \
                            and val.is_real is True and s_ not in found:
                        found[s_] = val
                        texts.append(c)
        return found, texts

    def _implied_values(self, known: dict) -> dict:
        """Symbols a given `s = expr` fixes once the symbols of expr have their values in `known`, repeated
        until nothing new comes (b = 2 and a = b - 3 give a = -1)."""
        out: dict = {}
        rels = []
        for g in self.ir.givens:
            try:
                rel = parse_relation(g, self.ns)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(rel, sp.Eq):
                rels.append(rel)
        for _ in range(len(rels)):
            have = {**known, **out}
            grew = False
            for rel in rels:
                for s_, val in ((rel.lhs, rel.rhs), (rel.rhs, rel.lhs)):
                    if not isinstance(s_, sp.Symbol) or s_ in have or not isinstance(val, sp.Expr) \
                            or not val.free_symbols or not val.free_symbols <= set(have):
                        continue
                    v = val.xreplace(have)
                    if not v.free_symbols and v.is_real is True:
                        out[s_] = have[s_] = v
                        grew = True
            if not grew:
                break
        return out

    def _binding_issues(self) -> tuple[str, list[str]] | None:
        from ..normalize.parse import (PinnedBoundVariable, given_binding_report, hold_parametric,
                                       parse_as_written, read_condition)
        from .domain import _certified_compare, definedness_conditions, in_domain, relation_holds_at
        if (self.ir.domain_of_discourse or "").strip().lower() in ("complex", "complexes", "c", "ℂ"):
            return None                          # the conditions are the real ones (written_undefined too)
        bind, clash, _sources = given_binding_report(self.ir, self.ns)
        cbind, _ctexts = self._constraint_bindings()
        allb = dict(cbind)
        for s_, v in bind.items():
            if s_ in allb and not same_value(allb[s_], v):
                clash.setdefault(s_, [allb[s_]]).append(v)
            allb[s_] = v
        # a value the givens imply through other values (b = 2, a = b - 3): checked like the others, never a
        # pin (x + log(a) - log(a) = 2 with a = b - 3, b = 2 is undefined as written all the same)
        implied = self._implied_values(allb)
        allb.update(implied)
        found: dict[str, list[str]] = {}

        def note(reason, what):
            found.setdefault(reason, [])
            if str(what) not in found[reason]:
                found[reason].append(str(what))

        def closed_verdict(c):
            """True/False/None for a closed condition, decided exactly."""
            if c is sp.true or c is sp.false:
                return bool(c)
            try:
                return relation_holds_at(c, sp.Dummy("_closed"), 0)
            except Exception:  # noqa: BLE001
                return None

        # (1) one symbol, two values
        for s_, vals in clash.items():
            diff = [_certified_compare(vals[0], w) for w in vals[1:]]
            note("ir_inconsistent" if any(d not in (0, None) for d in diff) else "given_binding_undecided",
                 f"{s_} = {', '.join(str(w) for w in vals)}")
        # (2) each value in its symbol's declaration and domain of discourse
        for s_, v in allb.items():
            vd = next((d for d in self.ir.vars if d.name == s_.name), None)
            dset = self._DECLARED_SETS.get(vd.domain) if vd is not None else None
            if dset is not None:
                d = in_domain(dset, v)
                if d is not True:
                    note("ir_inconsistent" if d is False else "given_binding_undecided",
                         f"{s_} = {v} (declared {vd.domain})")
            if self._dod_mentions(s_):
                try:
                    ds = self.discourse(s_)
                    # a domain of discourse that only names s_ as a parameter of another variable (x > b) is
                    # a condition (3) reads at the values, not a set of values for s_
                    d = True if ds.free_symbols - {s_} else in_domain(ds, v)
                except Exception:  # noqa: BLE001 - the domain itself is the certificates' question
                    d = True
                if d is not True:
                    note("ir_inconsistent" if d is False else "given_binding_undecided",
                         f"{s_} = {v} (domain of discourse {self.ir.domain_of_discourse})")
        # (3) every given and constraint at the values
        texts = list(self.ir.givens) + [c for v in self.ir.vars for c in v.constraints]
        dod = self.ir.domain_of_discourse
        for t in texts + ([dod] if isinstance(dod, str) and dod.strip() else []):
            try:
                rel = read_condition(t, self.ns)
            except Exception:  # noqa: BLE001 - side_conditions / unreadable_constraints abstain on it
                continue
            if rel is sp.false:
                note("ir_inconsistent", t)
                continue
            fs = getattr(rel, "free_symbols", set())
            if fs and not fs & set(allb):
                continue                        # a closed one is decided too: `pi < 3` is no instance
            try:
                # evaluated: SymPy's assumptions (x < 0 with x declared positive is false)
                if substitute_free(rel, allb) is sp.false:
                    note("ir_inconsistent", t)
                    continue
                with sp.evaluate(False):
                    r2 = substitute_free(rel, allb)
            except Exception:  # noqa: BLE001
                note("given_binding_undecided", t)
                continue
            if getattr(r2, "free_symbols", None):
                continue
            h = closed_verdict(r2)
            if h is not True:
                note("ir_inconsistent" if h is False else "given_binding_undecided", t)
        # (4) every expression of the problem, as written, at the values (never the task's own variable). The
        # symbols are read as plain reals here: a declaration (y positive) is the parameter's region in (6),
        # not a fact SymPy folds into its condition. A closed condition counts where the text holds a value a
        # given fixes (`a = 4 + log(-1) - log(-1)`, x + log(a) - log(a) with a = -1); any other is the
        # certificates' and `written_undefined`'s (an equation defined nowhere has no solution, 30 Sep 2026)
        tv = task_variables(self.ir)
        plain = {v.name: sp.Symbol(v.name, real=True) for v in self.ir.vars}
        pns = dict(self.ns, **plain)
        pins = {plain.get(s_.name, s_): v for s_, v in allb.items() if s_.name not in tv}
        params = self.ir.task.params or {}
        srcs = texts + [v for k, v in params.items() if isinstance(v, str) and k != "var"]
        conflicts: list = []
        open_conds: list = []
        for src in srcs:
            e = parse_as_written(src, self.ns)
            if e is not None:
                try:
                    with sp.evaluate(False):
                        hold_parametric(e, bind, tv)
                except PinnedBoundVariable:
                    conflicts.append(src)
                except Exception:  # noqa: BLE001 - the value parse reports it
                    pass
            ew = parse_as_written(src, pns)
            if ew is None:
                continue
            try:
                pinned_here = bool(ew.free_symbols & set(pins))
                with sp.evaluate(False):
                    e2 = substitute_free(ew, pins)
                conds = definedness_conditions(e2, None)
            except Exception:  # noqa: BLE001 - not read as written: the old reading
                continue
            for c in conds:
                if getattr(c, "free_symbols", None):
                    open_conds.append((c, src))
                    continue
                if not pinned_here:
                    continue
                h = closed_verdict(c)
                if h is not True:
                    note("problem_undefined_as_written" if h is False else "given_binding_undecided", src)
                    break
        # an IR function's call is read with its body as written (parse_as_written), so its conditions and its
        # Integrals/Limits are among the above; a body that leaks a pin fails at the namespace already
        # (5) a value a pin would put where an operator or the task binds the symbol, or a value for the
        # variable the task's operator binds (d/dx at x, the index of a series: fourth audit P1)
        for c in conflicts:
            note("given_binds_a_bound_variable", c)
        if self.ir.task.kind in self._OPERATOR_VAR_KINDS and {s_.name for s_ in bind} & tv:
            note("given_binds_a_bound_variable", f"task variable {sorted({s_.name for s_ in bind} & tv)}")
        # (6) a written condition on the parameters alone (no task variable), read on the region the
        # declarations, the domain of discourse, the constraints and the givens leave them
        if tv and self.ir.task.kind not in ("count_solutions",):     # there every variable is an unknown
            for c, src in open_conds:
                if {s_.name for s_ in c.free_symbols} & tv:
                    continue
                verdict = self._parameter_condition(c)
                if verdict is not True:
                    note("problem_undefined_as_written" if verdict is False else "parameter_condition_not_proved",
                         f"{c} ({src})")
        # (7) a variable no point is left for by its declaration, the domain of discourse, its constraints and
        # (the task's variable) the side conditions: no instance, with a value fixed or not (review of d4d, 6b)
        for v in self.ir.vars:
            reg = self._declared_region(self.sym(v.name), side=v.name in tv)
            if reg is not None and (reg is S.EmptySet or reg.is_empty is True):
                note("ir_inconsistent", f"no value of {v.name} is left")
        return self._first_issue(found)

    # the kinds whose own variable an operator binds (d/dx, lim x->, an integral's dx, a series' index): a given
    # that fixes it is no side condition (fourth audit P1)
    _OPERATOR_VAR_KINDS = {"limit", "antiderivative", "definite_integral", "derivative", "tangent_line",
                           "extremum", "series_sum", "recurrence_term", "closed_form"}

    def _declared_region(self, p: sp.Symbol, side: bool = False, givens: bool = False):
        """The reals the declaration, the domain of discourse (a set of numbers), the constraints and, with
        `side`, the side conditions (`side_conditions`), with `givens`, every given on `p` alone leave `p`, each
        other value a given fixes read as its value; None when one of them cannot be solved exactly."""
        from ..normalize.parse import read_condition
        vd = next((d for d in self.ir.vars if d.name == p.name), None)
        reg = self._DECLARED_SETS.get(vd.domain, S.Reals) if vd is not None else S.Reals
        if self._dod_mentions(p):
            try:
                ds = self.discourse(p)
            except Exception:  # noqa: BLE001
                return None
            if ds.free_symbols - {p}:
                return None
            reg = sp.Intersection(reg, ds)
        cons = list(vd.constraints) if vd is not None else []
        texts = cons + (list(self.ir.givens) if givens else [])
        bind = {s_: v for s_, v in self.bindings().items() if s_ != p}
        for t in texts:
            try:
                cond = read_condition(t, self.ns)
            except Exception:  # noqa: BLE001
                return None
            cond = cond.xreplace(bind) if bind else cond
            fs = getattr(cond, "free_symbols", set())
            if p not in fs:
                continue
            if fs != {p}:
                if t in cons:
                    return None
                continue                         # a given on several symbols says nothing of p alone
            cut = self.condition_set(cond, p)
            if cut is None:
                return None
            reg = sp.Intersection(reg, cut)
        if side:
            sets, unapplied = self.side_conditions(p)
            if unapplied:
                return None
            for st in sets:
                reg = sp.Intersection(reg, st)
        return reg

    def _parameter_condition(self, c) -> bool | None:
        """Does the definedness condition `c` on parameters hold at every point their region leaves (True),
        at none (False), or neither / undecided (None)? x + log(a) - log(a) = 2 had {2} certified with the
        given a < 0, where the equation is defined nowhere, and with a free, where the answer is the empty set
        for a <= 0 (review of d4d, B4 and 6a)."""
        fs = c.free_symbols
        if len(fs) != 1:
            return None
        (p,) = fs                                # a plain real symbol (see (4) of `_binding_issues`)
        if not any(v.name == p.name for v in self.ir.vars):
            return None
        reg = self._declared_region(self.sym(p.name), givens=True)
        cut = self.condition_set(c, p)
        if reg is None or cut is None:
            return None
        try:
            if reg.is_subset(cut) is True:
                return True
            if sp.Intersection(reg, cut).is_empty is True:
                return False
        except Exception:  # noqa: BLE001
            return None
        return None

    @staticmethod
    def _first_issue(found: dict) -> tuple[str, list[str]] | None:
        for reason in ("ir_inconsistent", "problem_undefined_as_written", "given_binds_a_bound_variable",
                       "given_binding_undecided", "parameter_condition_not_proved"):
            if reason in found:
                return reason, found[reason]
        return None

    def bindings(self) -> dict:
        """The symbols the givens fix to one real number (`normalize.parse.given_bindings`)."""
        if "bindings" not in self.cache:
            self.cache["bindings"] = given_bindings(self.ir, self.ns)
        return self.cache["bindings"]

    def pinned_values(self, var: sp.Symbol | None = None) -> dict:
        """The value of each symbol other than `var` that a given (`bindings`) or a declared constraint
        `a = c` fixes; `binding_issues` has checked them (the verifier abstains before any certificate
        otherwise). The extremum certificate read neither: with b = 3 the maximum 0 of x on [0, b] and
        with a = 3 the maximum 0 of a*x on [0, 1] were certified (fourth audit G4, TAN-02)."""
        out = dict(self._constraint_bindings()[0])
        out.update(self.bindings())
        return {s_: v for s_, v in out.items() if s_ != var}

    def task_pins(self, var: sp.Symbol, *keep: str) -> dict:
        """`pinned_values(var)` without the symbols named in `keep` (a tangent line's dependent variable): the
        values a task certificate puts in its function, its point, its interval and the claim. The calculus
        certificates read none: with a = 3 the derivative 6*x of a*x**2 was refuted (it was compared with
        2*a*x), and the written conditions of x + 0*sqrt(b - x) were dropped, so with b = 1/2 its maximum 1
        on [0, 1] and its integral 1/2 over [0, 1] were certified (fourth audit TAN-02, review of d4e)."""
        return {s_: v for s_, v in self.pinned_values(var).items() if s_.name not in keep}

    def with_pins(self, e, pins: dict):
        """`e` with the values `pins` holds put in (never a bound variable: `substitute_free`), and the closed
        forms this makes (Σ_{k=1}^{n} k with n = 3: 6) by values numbers confirm (`_confirmed`, ParseError
        otherwise), as `expr` reads the problem's own: left a form, the maximum 6 of x*Σ_{k=1}^{n} k on [0, 1]
        with n = 3 was left undecided."""
        if not pins or not isinstance(e, sp.Basic) or not (e.free_symbols & set(pins)):
            return e
        return self._confirmed(None, substitute_free(e, pins))

    def on_var(self, rels, var: sp.Symbol) -> tuple[list, list]:
        """The relations `rels` read on `var` alone, each other symbol a given fixes read as its value
        (`x > b` with b = 0 is x > 0). A relation that then always holds is left out: the binding
        b = 0 itself became 0 = 0, where solveset(b = 0, x) had read it as the empty set, so any given
        binding made the solution set of an inequality system empty and a count of integers 0, and
        both were certified (part vi, 30 Sep 2026). The second item lists the relations that still
        name another symbol: the certificate cannot read them on `var` and abstains."""
        bind = {s_: v for s_, v in self.bindings().items() if s_ != var}
        kept: list = []
        unbound: list = []
        for r in rels:
            r2 = r.xreplace(bind) if bind else r
            if r2 is sp.true:
                continue
            if getattr(r2, "free_symbols", set()) - {var}:
                unbound.append(r)
            else:
                kept.append(r2)
        return kept, unbound

    def _with_bound_values(self, c, var: sp.Symbol):
        """A condition on `var` and other symbols, with each symbol a given fixes (`a = 0`) read as
        its value. A condition on two variables was dropped from the domain: log(x - a) with the
        given a = 0 is defined on x > 0, yet {-2, 2} was certified for x**2 + 1 + 0*log(x - a) = 5,
        and a constraint x > a the same (third audit of 30 Sep 2026, N5)."""
        free = getattr(c, "free_symbols", set())
        if var not in free or free == {var}:
            return c
        bind = self.bindings()
        return c.xreplace({s_: bind[s_] for s_ in free if s_ != var and s_ in bind})

    def unreadable_constraints(self) -> list[str]:
        """Declared constraints (`vars[].constraints`) that do not read as relations between
        expressions. The domain dropped them silently: `(0, oo)` (a tuple) certified {-2, 2} for
        x**2 + 1 = 5, and `x > 0 and x < 3`, `x in (0, oo)` or `[0, oo)` refuted the right {2}
        (third audit of 30 Sep 2026, N5). The verifier abstains on them."""
        out = []
        for v in self.ir.vars:
            for c in v.constraints:
                try:
                    rel = parse_relation(c, self.ns)
                    ok = all(isinstance(r, sp.core.relational.Relational) and isinstance(r.lhs, sp.Expr)
                             and isinstance(r.rhs, sp.Expr) for r in (rel.args if isinstance(rel, sp.And) else (rel,)))
                except Exception:  # noqa: BLE001
                    ok = False
                if not ok:
                    out.append(c)
        return out

    # Params that hold the problem's own expression, per task kind. `limit` is absent on purpose,
    # and its givens are skipped too: the point a limit approaches is typically exactly where the
    # expression is undefined (lim x→0 of x/x is 1). The calculus kinds keep their own handling.
    _WRITTEN_PARAMS = {"evaluate": ("expr",), "simplify_expression": ("expr",), "domain_of": ("expr",),
                       "solve_equation": ("equation",), "solve_inequality": ("inequality",),
                       "count_roots": ("expr",)}
    # The expression of a kind whose certificates read only its OPEN written conditions: one defined
    # nowhere as written (a closed condition that fails) or with a binder not proved to exist over its
    # range was differentiated, integrated and simplified as if it existed: the derivative 1 of
    # x + Σ_{k=-1}^{1} k/k, the antiderivative x of 1 + 0·Σ_{k=-1}^{1} k/k and x as the simplification
    # of x + sqrt(-y) - sqrt(-y) with y > 0 were certified (V16, 30 Sep 2026). Such an expression makes
    # the problem undefined as written (`written_undefined`). An equation or a domain defined nowhere
    # has an answer (no solution, the empty set) and is not listed.
    _NOWHERE_PARAMS = {"derivative": "f", "tangent_line": "f", "antiderivative": "integrand",
                       "definite_integral": "integrand", "simplify_expression": "expr", "evaluate": "expr"}

    # the task's own relation or expression, in params: a given next to it is a side condition.
    # count_roots and domain_of read no given at all before, so `x > 0` next to x² − 4 left the count
    # at 2 and the domain of √(4 − x²) at [-2, 2] (part vi, 30 Sep 2026)
    # The calculus kinds read a given on their variable as a region too: a limit, a derivative, a tangent
    # line and an antiderivative are taken on the variable's region, and the same condition gave one
    # verdict as a declaration and another as a given (fourth audit G6, G12): with the given x > 0,
    # lim_{x->0} |x|/x was certified DNE and the derivative of |x| at 0 under x >= 0 DNE, and log(-x)
    # was refuted as an antiderivative of 1/x under the given x < 0.
    _MAIN_RELATION = {"solve_equation": "equation", "solve_inequality": "inequality", "count_roots": "expr",
                      "domain_of": "expr", "limit": "expr", "derivative": "f", "tangent_line": "f",
                      "antiderivative": "integrand"}

    def side_conditions(self, var: sp.Symbol) -> tuple[list[sp.Set], list[str]]:
        """Solution sets of the given relations on `var` that are SIDE conditions (the task's own
        relation is in params), and the ones that could not be solved exactly. A side condition that
        cannot be applied leaves the certificates answering another question, so the verifier abstains
        on it (`given_not_applied`) instead of dropping it silently; so does a given that names a
        symbol the problem does not declare. A symbol another given fixes (`x > b` with b = 0) is read
        as its value; a side condition that still names another symbol is listed for
        `unapplied_conditions`. A given equation on `var` restricts it too: x³ = 8 next to x² = 4
        left {-2, 2} certified (part vi, 30 Sep 2026); the task's own relation repeated among the
        givens is no side condition."""
        key = f"side:{var.name}"
        if key in self.cache:
            return self.cache[key]
        sets: list[sp.Set] = []
        unapplied: list[str] = []
        unbound: list[str] = []
        params = self.ir.task.params or {}
        pk = self._MAIN_RELATION.get(self.ir.task.kind)
        if pk and isinstance(params.get(pk), str):
            from ..equiv.numeric import real_odd_roots
            from ..normalize.parse import read_condition
            try:
                main = parse_relation(params[pk], self.ns)
            except Exception:  # noqa: BLE001 - the certificate reports it
                main = None
            for g in self.ir.givens:
                # a chain, an And/Or, `and`/`,`/`or`, a membership `x in (0, 3)` are read too, and a given
                # that reads as no condition is never dropped: it was, and (−2, 2) was certified for
                # x² < 4 next to 0 < x < 3 (fourth audit G1)
                try:
                    rel = read_condition(g, self.ns)
                except Exception:  # noqa: BLE001 - UndeclaredSymbolError, ParseError: not applied
                    unapplied.append(g)
                    continue
                if var not in getattr(rel, "free_symbols", set()) or rel == main:
                    continue
                rel = self._with_bound_values(rel, var)
                if rel is sp.false:                     # the values the givens fix contradict it
                    sets.append(S.EmptySet)
                    continue
                if rel is sp.true:
                    continue
                if rel.free_symbols != {var}:
                    unbound.append(g)
                    continue
                if not isinstance(rel, sp.core.relational.Relational):
                    sol = self.condition_set(rel, var)
                    if sol is None:
                        unapplied.append(g)
                    else:
                        sets.append(sol)
                    continue
                rel_r = real_odd_roots(rel)
                if at_risk(rel_r, var):
                    # solved by domain_for on the domain the other conditions leave (one period otherwise)
                    sets.append(sp.ConditionSet(var, rel_r, S.Reals))
                    continue
                try:
                    sol = sp.solveset(rel_r, var, S.Reals)
                except Exception:  # noqa: BLE001
                    sol = None
                if sol is None or isinstance(sol, sp.ConditionSet) or sol.has(sp.ConditionSet):
                    unapplied.append(g)
                else:
                    sets.append(sol)
        self.cache[f"side_unbound:{var.name}"] = unbound
        self.cache[key] = (sets, unapplied)
        return sets, unapplied

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
        found: dict[str, list[str]] = {"undefined": [], "undecided": []}

        def note(src, state):
            if state is not None and src not in found[state]:
                found[state].append(src)

        # a value a given fixes is put in before the conditions are read (x**a with a = 2 is x**2, defined
        # everywhere; TAN-09); never the task's own variable, which a given only restricts
        pins = self.parameter_pins()
        for s_ in srcs:
            cs, nw = written_definedness(s_, self.ns, pins)
            nowhere |= nw
            conds += [c for c in cs if c not in conds]
            note(s_, self._undefined_constant(s_, pins))
        cs, nw, calls = self._function_call_conditions(srcs)
        nowhere |= nw
        conds += [c for c in cs if c not in conds]
        for c in calls:
            note(c, "undefined")
        fsrc = params.get(self._NOWHERE_PARAMS.get(kind, ""))
        if isinstance(fsrc, str):
            note(fsrc, self._undefined_function(fsrc, kind, pins))
        # every other text of the problem (a point, a bound, an interval, a term, a constraint, a limit's
        # expression): one with a closed operation that has no value ((-1)!, Γ(0), zoo), or closed and
        # undefined itself. The point 1/(-1)! of a derivative, the bound of an integral and the interval
        # [1/(1/0), 1] of an extremum were read as SymPy's 1/zoo = 0 and certified (CAP-F1)
        others = [v for k, v in params.items() if isinstance(v, str) and k != "var"]
        others += list(self.ir.givens) + [c for v in self.ir.vars for c in v.constraints]
        if isinstance(self.ir.domain_of_discourse, str):
            others.append(self.ir.domain_of_discourse)
        for t in others:
            if t not in srcs and t != fsrc:
                note(t, self._text_without_value(t, pins))
        self.cache[key] = (conds, nowhere)
        self.cache["written_undefined"] = found["undefined"]
        self.cache["written_undecided"] = [u for u in found["undecided"] if u not in found["undefined"]]
        return conds, nowhere

    def written_undefined(self) -> list[str]:
        """The problem's expressions that are undefined AS WRITTEN with no variable left to choose:
        `log(-1) - log(-1) - 1`, or `f(-1)` for f(x) = log(x) − log(x) + x. The closed condition
        fails, but `nowhere` only records free symbols, so the value SymPy simplified to (−1) was
        certified (audit of 25 Sep 2026). Also any text with a closed operation that has no value
        (`certify.domain.NO_VALUE`: x + 1/(-1)! = 2 is no equation defined nowhere, CAP-F1). Empty over the
        complex numbers, where the conditions are the real ones."""
        self.written_conditions()
        if (self.ir.domain_of_discourse or "").lower() in ("complex", "c", "ℂ"):
            return []
        return list(self.cache.get("written_undefined", []))

    def written_undecided(self) -> list[str]:
        """The problem's expressions whose definedness AS WRITTEN rests on a closed condition no exact check
        decides: a binder not proved to exist over its range (DEFINEDNESS_UNDECIDED), a convention value
        (0**0), a comparison left standing (tan(arccot(2) + arccot(1/2))). The callers abstain as on
        `written_undefined`, but the problem is not proved undefined: Π_{k=1}^{n} Σ_{j=1}^{k} 1 with n free
        was "problem_undefined_as_written" (fourth audit, TAN-12)."""
        self.written_conditions()
        if (self.ir.domain_of_discourse or "").lower() in ("complex", "c", "ℂ"):
            return []
        return list(self.cache.get("written_undecided", []))

    @staticmethod
    def _pinned(e, pins: dict | None):
        """The as-written tree `e` with the values the givens fix (see `parameter_pins`), unevaluated."""
        if not pins or e is None:
            return e
        from ..normalize.parse import substitute_free
        try:
            with sp.evaluate(False):
                return substitute_free(e, pins)
        except Exception:  # noqa: BLE001 - read without the values (the old reading)
            return e

    def _undefined_constant(self, src: str, pins: dict | None = None) -> str | None:
        """"undefined" when `src`, read as written at the values the givens fix (TAN-12: Π_{k=1}^{n} Σ_{j=1}^{k}
        1 with n = 3 has every inner range forward), has no value whatever its free symbols are: a closed
        operation with none (NO_VALUE), or a condition that fails with no symbol left; "undecided" when a
        closed condition no exact check decides stands; None otherwise."""
        from ..normalize.parse import parse_as_written
        from .domain import closed_condition_undecided, definedness_conditions, is_no_value
        e = self._pinned(parse_as_written(src, self.ns), pins)
        if e is None:
            return None
        conds = definedness_conditions(e, None)
        if any(is_no_value(c) for c in conds):
            return "undefined"
        if not e.free_symbols and (any(c is sp.false for c in conds) or self._undefined_term(e)):
            return "undefined"
        # a closed condition SymPy left standing is one it could not decide: it counts only when it
        # is proved. tan(arccot(2) + arccot(1/2)) is tan(pi/2); its condition cos(...) != 0 stayed
        # symbolic and the value oo was certified (-oo before V14; audit of 29 Sep 2026). Inside an
        # expression with a variable (x + tan(...) - tan(...) = 1) the condition was dropped too.
        return "undecided" if closed_condition_undecided(conds) else None

    def _undefined_function(self, src: str, kind: str, pins: dict | None = None) -> str | None:
        """Is the expression of the task (`_NOWHERE_PARAMS`), read as written, defined nowhere
        ("undefined") or undecided through a closed condition ("undecided")? The variable of a definite
        integral is read as a plain real symbol: it runs over [a, b], not over its declared domain
        (certify.calculus)."""
        from ..normalize.parse import parse_as_written
        from .domain import closed_condition_undecided, definedness_conditions, open_conditions_empty
        ns = self.ns
        v = (self.ir.task.params or {}).get("var", "x")
        if kind == "definite_integral" and isinstance(v, str) and isinstance(ns.get(v), sp.Symbol):
            ns = dict(ns, **{v: sp.Symbol(v, real=True)})
        e = self._pinned(parse_as_written(src, ns), pins)
        if e is None:
            return None
        conds = definedness_conditions(e, None)
        # open conditions that hold nowhere together (x > 0 and -x > 0) too: the simplification x of
        # x + log(x) - log(x) + log(-x) - log(-x) was certified (fourth audit TAN-06)
        if any(c is sp.false for c in conds) or self._undefined_term(e) \
                or open_conditions_empty(conds, timeout=self.timeout):          # NO_VALUE comes with `false`
            return "undefined"
        return "undecided" if closed_condition_undecided(conds) else None

    def _text_without_value(self, src: str, pins: dict | None = None) -> str | None:
        """Any other text of the problem, read as written: "undefined" when it holds a closed operation
        with no value (NO_VALUE) or is closed and undefined, "undecided" when it is closed and a condition
        no exact check decides stands; None otherwise (open conditions are the certificates')."""
        from ..normalize.parse import parse_set_as_written
        from .domain import closed_condition_undecided, definedness_conditions, is_no_value, tree_free_symbols
        try:
            # an interval's ends too: Interval.open(1/(-1)!, oo), [1/(1/0), 1)
            e = self._pinned(parse_set_as_written(src, self.ns), pins)
            if e is None:
                return None
            conds = definedness_conditions(e, None)
            if any(is_no_value(c) for c in conds):
                return "undefined"
            if tree_free_symbols(e):
                return None
        except Exception:  # noqa: BLE001 - a text no reading reads adds no fact (it was not read before)
            return None
        if any(c is sp.false for c in conds):
            return "undefined"
        return "undecided" if closed_condition_undecided(conds) else None

    @staticmethod
    def _undefined_term(e) -> bool:
        """A finite Sum or Product (as written) with a term undefined at one of its indices:
        Σ_{k=-1}^{1} k/k = 3 was certified, because k/k read as 1 and the condition k != 0 only
        concerned the index (audit of 29 Sep 2026). The series_sum certificate checks this for its
        own term; here it is checked for a sum inside any closed expression."""
        from .domain import definedness_conditions, relation_holds_at
        for n in sp.preorder_traversal(e):
            if not isinstance(n, (sp.Sum, sp.Product)) or len(n.limits) != 1:
                continue
            k0, lo, hi = n.limits[0]
            if not (getattr(lo, "is_Integer", False) and getattr(hi, "is_Integer", False)) or hi - lo > 200:
                continue
            # the index without the declaration of its name: k declared positive made k != 0 true
            k = sp.Symbol(k0.name)
            try:
                with sp.evaluate(False):
                    body = n.function.xreplace({k0: k})
                conds = [c for c in definedness_conditions(body, None) if c.has(k)]
            except Exception:  # noqa: BLE001
                continue
            for i in range(int(lo), int(hi) + 1):
                for c in conds:
                    if c.free_symbols - {k}:
                        continue
                    try:
                        if relation_holds_at(c, k, sp.Integer(i)) is False:
                            return True
                    except Exception:  # noqa: BLE001
                        continue
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
                # the body's own real arguments, as the callable was built (parse._make_function)
                body_ns = dict(self.ns)
                arg_syms = [sp.Symbol(a, real=True) for a in fd.args]
                body_ns.update(zip(fd.args, arg_syms))
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
        """A relation of the problem. A text with a variable that reads as plain true or false, or a LaTeX
        congruence, raises ParseError (`normalize.parse.not_collapsed`, review of d4d B2): `x \\notin (-3, 3)`
        read as True and dropped out of the givens."""
        from ..normalize.parse import refuse_congruence
        if isinstance(s, str):
            refuse_congruence(s)
            return self._confirmed(s, not_collapsed(parse_relation(s, self.ns), s, self.ns))
        return self._confirmed(s, parse_relation(s, self.ns))

    def expr(self, s: str):
        return self._confirmed(s, parse_expr_str(s, self.ns))

    def _confirmed(self, src, e):
        """The problem's closed integrals, sums, products and limits by values numbers confirm
        (equiv.forms), or a ParseError: the certificate then abstains. Left as forms, they reached
        solveset, z3 and simplify, which evaluated them unconfirmed (|cos x| on [-1, 1] to 0: the
        value 1 of x = 1 + integral with a given was certified) or could not solve at all (third
        audit of 30 Sep 2026)."""
        from ..equiv.forms import UnverifiedForm, checked_forms, has_closed_form
        if not has_closed_form(e):
            return e
        key = ("confirmed", src if isinstance(src, str) else sp.srepr(e))
        if key not in self.cache:
            try:
                self.cache[key] = checked_forms(e, timeout=self.timeout)
            except UnverifiedForm as ex:
                self.cache[key] = ParseError(f"a closed form with no confirmed value: {ex}")
        out = self.cache[key]
        if isinstance(out, ParseError):
            raise out
        return out

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


def condition_unsolved(layer: str, conds, ms: float = 0.0, evidence: dict | None = None) -> LayerResult:
    """The certificate abstains: a condition on the variable (one with a trigonometric function, see
    Ctx.unsolved_conditions) cuts its domain in no closed form, and the certificate reads that domain
    as a solved set."""
    return unknown(layer, f"condition_unsolved: {[str(c) for c in conds][:3]}", ms, evidence,
                   flags=["condition_unsolved"])


def convention_counterexample(ctx: Ctx, claimed, truth, syms, n: int = 12) -> tuple[bool, dict | None]:
    """(whether a symbol of the comparison has points where a value of the problem is another value under
    the other convention (`Ctx.value_convention_region`), a point there where the two sides differ under
    BOTH readings or None). The comparisons read the sides on `domain_for`, which leaves those points
    out, so agreement there certifies nothing: a claim equal to the problem's expression on x >= 0 only
    (Abs(x) for (x**3)**(1/3)) was CORRECT (part d4a, attack A). A point where the readings differ on
    whether the sides agree (cbrt(x) for x**(1/3) at -8) decides nothing; one where both readings
    differ (Abs(-2) = 2 against -2 and 1 + √3 i) refutes the claim."""
    from ..equiv.random_point import sample_points
    from ..equiv.sets import scalar_equal
    regions = {}
    for s_ in syms:
        if self_ok(ctx, s_):
            r = ctx.value_convention_region(s_)
            try:
                empty = r.is_empty
            except Exception:  # noqa: BLE001
                empty = None
            if empty is not True:
                regions[s_] = r
    if not regions:
        return False, None
    doms = {s_: regions.get(s_, ctx.domain_for(s_) if self_ok(ctx, s_) else S.Reals) for s_ in syms}
    pts: list[dict] = []
    for v, r in regions.items():
        for c in (-1, -2, -8, sp.Rational(-1, 2), -27, -3, 1, 2):
            try:
                if r.contains(c) is sp.true:
                    pts.append({v: sp.Integer(c) if isinstance(c, int) else c})
            except Exception:  # noqa: BLE001
                continue
    try:
        pts += sample_points(doms, n, ctx.seed)
    except Exception:  # noqa: BLE001
        pass
    for pt in pts:
        full = dict(pt)
        for s_ in syms:
            if s_ not in full:
                full[s_] = sp.Integer(1) if doms[s_].contains(1) is sp.true else None
        if any(v is None for v in full.values()):
            continue
        try:
            a, b = sp.sympify(claimed).xreplace(full), sp.sympify(truth).xreplace(full)
            if a.free_symbols or b.free_symbols or a.has(sp.nan, sp.zoo) or b.has(sp.nan, sp.zoo):
                continue
            if scalar_equal(a, b) is False:
                return True, {str(k): str(v) for k, v in full.items()}
        except Exception:  # noqa: BLE001
            continue
    return True, None


def self_ok(ctx: Ctx, s_) -> bool:
    return isinstance(s_, sp.Symbol) and ctx.ns.get(s_.name) == s_


def condition_not_applied(layer: str, conds, ms: float = 0.0, evidence: dict | None = None) -> LayerResult:
    """The certificate abstains: a condition on the variable names a symbol no given fixes (see
    Ctx.unapplied_conditions and Ctx.on_var), so its answer would be read on too large a domain."""
    return unknown(layer, f"condition_not_applied: {[str(c) for c in conds][:3]}", ms, evidence,
                   flags=["condition_not_applied"])


def parse_or_unknown(layer: str, fn, *args, **kw):
    """Run a parse; on ParseError return (None, LayerResult unknown)."""
    try:
        return fn(*args, **kw), None
    except ParseError as e:
        return None, unknown(layer, f"parse_error: {e}", flags=["parse_error"])
    except Exception as e:  # noqa: BLE001
        return None, unknown(layer, f"parse_error: {type(e).__name__}: {e}", flags=["parse_error"])


_OPERATIONS = (sp.Integral, sp.Sum, sp.Product, sp.Limit, sp.Derivative, sp.Subs)


def closed_binding(rel) -> tuple[sp.Symbol, Any] | None:
    """`s = c` or `c = s`, with `c` a finite real number and no operation left in it: the relation
    pins the symbol `s` to that one value. None for any other relation (`a**2 = 16`, `a + 1 = 5`)."""
    if not isinstance(rel, sp.Eq):
        return None
    for s_, c in ((rel.lhs, rel.rhs), (rel.rhs, rel.lhs)):
        if isinstance(s_, sp.Symbol) and isinstance(c, sp.Expr) and not c.free_symbols \
                and not c.has(*_OPERATIONS) and c.is_real is True:    # a real number is finite (not oo)
            return s_, c
    return None
