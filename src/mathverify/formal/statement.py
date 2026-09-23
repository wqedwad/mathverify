"""Deterministic IR -> Lean 4 theorem statement.

Handoff [5] measures the real F5 risk: 89.5% of autoformalised statements compile but only
60.5% say what the problem says. We avoid that gap entirely by NOT asking a model for the
statement: it is generated from the (already round-trip audited) IR by a template, with a
SymPy -> Lean printer that refuses anything it cannot translate exactly.

Two rules keep the statements honest:
  * substitution never lets SymPy decide anything — `_subs_rel` rewrites both sides and
    rebuilds the relation with evaluate=False, so `sqrt(4+5) = -2+5` reaches Lean as a claim
    to check rather than as SymPy's `True`;
  * a template that cannot express a claim exactly returns None, and L7 then does not run.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Callable

import sympy as sp
from sympy import S

from ..intake.structured import load_problem_ir
from ..normalize.parse import (ParseError, build_namespace, parse_relation, parse_expr_str,
                               parse_answer, parse_set_str, preclean, strip_presentation,
                               _TRANSFORMS)

__all__ = ["LeanStatement", "build_statement", "sympy_to_lean", "relation_to_lean", "LeanPrintError",
           "TEMPLATES", "structural_ns", "parse_structural"]


class LeanPrintError(ValueError):
    """The expression has no exact Lean/Mathlib rendering — never guess one."""


_DOMAIN_COND = {"positive_real": "0 < {v}", "nonneg_real": "0 ≤ {v}",
                "positive_integer": "0 < {v}", "nonneg_integer": "0 ≤ {v}", "natural": "0 < {v}"}

# classes only — `sp.sqrt` is a function (isinstance would raise); sqrt is handled by Pow(1/2)
_FUNC: dict[type, str] = {
    sp.sin: "Real.sin", sp.cos: "Real.cos", sp.tan: "Real.tan", sp.exp: "Real.exp",
}


def _paren(s: str) -> str:
    return s if (s.isidentifier() or s.isdigit() or (s.startswith("(") and s.endswith(")"))) else f"({s})"


# ---------------------------------------------------------------------------- structural parse
# The Lean layer must verify the arithmetic itself. A normal parse lets SymPy fold the whole
# target ("gcd(84,120) + lcm(4,6)" -> 24), which would turn the theorem into "24 = 24" — a
# tautology that proves nothing about the problem (handoff failure mode #6, trivial proofs).
# Structural parsing keeps the operations: the eager helpers become inert Function symbols and
# arithmetic is built unevaluated, so Lean recomputes `Int.gcd 84 120 + Int.lcm 4 6 = 24`.
_INERT = ("gcd", "lcm", "binomial", "factorial")


def structural_ns(ns: dict[str, Any]) -> dict[str, Any]:
    out = dict(ns)
    out.update({"Add": sp.Add, "Mul": sp.Mul, "Pow": sp.Pow})
    for nm in _INERT:
        out[nm] = sp.Function(nm)
    out["C"] = out["comb"] = sp.Function("binomial")
    return out


def parse_structural(src: str, ns: dict[str, Any]):
    """Parse without letting SymPy evaluate the arithmetic. Falls back to the normal parse when
    the unevaluated form cannot be built (the caller then gets a possibly-trivial statement,
    which the triviality guard rejects)."""
    from sympy.parsing.sympy_parser import parse_expr
    s = preclean(src)
    try:
        with sp.evaluate(False):
            return parse_expr(s, local_dict=structural_ns(ns), global_dict={},
                              transformations=_TRANSFORMS, evaluate=False)
    except Exception:
        return parse_expr_str(src, ns)


def parse_relation_structural(src: str, ns: dict[str, Any]):
    from ..normalize.parse import _split_top_level, _REL_CLASS
    s = preclean(src)
    parts = _split_top_level(s)
    if len(parts) == 1:
        return parse_structural(src, ns)
    exprs = [parse_structural(chunk, ns) for _, chunk in parts]
    rels = [_REL_CLASS[parts[k][0]](exprs[k - 1], exprs[k], evaluate=False) for k in range(1, len(parts))]
    return rels[0] if len(rels) == 1 else sp.And(*rels)


# ---------------------------------------------------------------------------- junk values
# Lean and Mathlib make every partial operation TOTAL by assigning a "junk" value outside the
# domain: `x / 0 = 0`, `Real.sqrt x = 0` for `x < 0`, `Real.log 0 = 0`, `Real.log (-x) =
# Real.log x`, `Real.tan (π/2) = 0`, and an interval integral of a non-integrable function is 0.
# A statement that reaches such a point is a statement about the junk value, not about the
# mathematics — and it can be PROVED. Measured before this section existed: "tan(π/2) = 0",
# "√(2−5) = 0", "(2²−4)/(2−2) = 0", "log 0 = 0" and "sin 0 = √(−4)" all received clean, audited
# certificates (no sorry, safe axioms, non-vacuous), and with `--lean` the first one came out
# of the whole verifier as CORRECT, confidence 0.995. The axiom/vacuity/unused-hypothesis audits
# cannot see this: the proofs are genuine proofs of the junk statements.
# (The hazard classes follow "Faults in Our Formal Benchmarking", arXiv:2606.29493: division by
# zero, analytic-domain totalisation, and their checkers.)
#
# The rule, applied uniformly:
#   * a CLOSED partial operation (no free symbols) is decided here — undefined or undecidable
#     means no statement at all (`LeanPrintError`); this is enforced inside `sympy_to_lean`, so
#     every printed value (claims, bounds, roots, matrix entries) is covered automatically;
#   * an OPEN one (depends on a variable) is each template's job: it becomes a guard hypothesis,
#     or it must provably hold on the region the statement quantifies over, or the template
#     declines. Never a silent junk value.
# Definedness comes from `certify.domain.definedness_conditions` — the same definition the
# deterministic layer uses, so the two layers cannot disagree about what "defined" means.

def _definedness(expr, var=None) -> list:
    from ..certify.domain import definedness_conditions
    conds = list(definedness_conditions(expr, var))
    for node in sp.preorder_traversal(expr):              # `a % 0 = a` in Lean
        if isinstance(node, sp.Mod):
            conds.append(sp.Ne(node.args[1], 0))
    return conds


def _closed_truth(c) -> bool | None:
    """Truth of a variable-free definedness condition; None when it cannot be decided."""
    if c is sp.true or c is True:
        return True
    if c is sp.false or c is False:
        return False
    if not isinstance(c, sp.core.relational.Relational) or c.free_symbols:
        return None
    d = c.lhs - c.rhs
    try:
        if sp.simplify(d) == 0:
            return isinstance(c, (sp.GreaterThan, sp.LessThan))     # ≥ / ≤ hold at equality
        v = complex(sp.N(d, 50))
    except (TypeError, ValueError, ZeroDivisionError, AttributeError):
        return None
    if not (math.isfinite(v.real) and math.isfinite(v.imag)):
        return False
    if abs(v.imag) > 1e-30:
        return False                            # a non-real argument is outside the real domain
    x = v.real
    if abs(x) < 1e-40:
        return None                             # numerically zero but not provably so
    if isinstance(c, sp.Unequality):
        return True
    if isinstance(c, (sp.StrictGreaterThan, sp.GreaterThan)):
        return x > 0
    if isinstance(c, (sp.StrictLessThan, sp.LessThan)):
        return x < 0
    return None


def _check_closed_definedness(e) -> None:
    items = list(e) if isinstance(e, sp.MatrixBase) else [e]
    for it in items:
        for c in _definedness(it):
            if getattr(c, "free_symbols", None):
                continue                        # open: the template's responsibility
            ok = _closed_truth(c)
            if ok is not True:
                raise LeanPrintError(f"junk value: {c} {'fails' if ok is False else 'is undecidable'} "
                                     f"in {e} (Lean would totalise it)")


def sympy_to_lean(e, field: str = "ℝ") -> str:
    """Exact printer. Raises LeanPrintError on anything not covered, and on any closed partial
    operation whose argument is outside its real domain (see the junk-value section above)."""
    e = sp.sympify(e)
    _check_closed_definedness(e)
    return _print_lean(e, field)


def open_guards(exprs, field: str = "ℝ", var=None) -> list[str]:
    """Lean propositions that make every partial operation in `exprs` well defined, for the
    conditions that depend on a variable. Closed conditions are decided by the printer."""
    out: list[str] = []
    for e in exprs:
        for c in _definedness(e, var):
            if not getattr(c, "free_symbols", None):
                continue
            txt = relation_to_lean(c, field)
            if txt not in out:
                out.append(txt)
    return out


def _violation_set(c, var, region):
    """Points of `region` where the definedness condition `c` fails, or None if undecidable."""
    if isinstance(c, sp.Unequality):
        bad = sp.Eq(c.lhs, c.rhs)
    elif isinstance(c, (sp.StrictGreaterThan, sp.GreaterThan, sp.StrictLessThan, sp.LessThan)):
        bad = sp.Not(c)
    else:
        return None
    try:
        s = sp.solveset(bad, var, region)
    except (NotImplementedError, TypeError, ValueError, AttributeError, RecursionError):
        return None
    if isinstance(s, (sp.ConditionSet, sp.ImageSet)) or s.has(sp.ConditionSet):
        return None
    return s


def defined_on(expr, var, region) -> bool:
    """Every partial operation in `expr` is defined at every point of `region` (a SymPy set).
    Anything SymPy cannot decide counts as NOT defined — the template then declines."""
    for c in _definedness(expr, var):
        if not getattr(c, "free_symbols", None):
            if _closed_truth(c) is not True:
                return False
            continue
        if c.free_symbols - {var}:
            return False
        bad = _violation_set(c, var, region)
        if bad is None or bad != sp.S.EmptySet:
            return False
    return True


def interior_defined_at(expr, var, point) -> bool:
    """`expr` is defined on a neighbourhood of `point` — what a derivative there needs. For a
    `≥ 0` condition that means strictly positive: `Real.sqrt` is constant 0 on (−∞, 0], so
    `HasDerivAt Real.sqrt 0 (-1)` is TRUE in Lean although √x has no derivative at −1."""
    for c in _definedness(expr, var):
        if not getattr(c, "free_symbols", None):
            if _closed_truth(c) is not True:
                return False
            continue
        cc = c.subs(var, point)
        if isinstance(c, sp.GreaterThan):
            cc = sp.StrictGreaterThan(c.lhs.subs(var, point), c.rhs.subs(var, point))
        elif isinstance(c, sp.LessThan):
            cc = sp.StrictLessThan(c.lhs.subs(var, point), c.rhs.subs(var, point))
        if _closed_truth(cc) is not True:
            return False
    return True


_PROBE_POINTS = (sp.Integer(1), sp.Integer(2), sp.Rational(1, 2), sp.Integer(3), sp.Integer(10),
                 sp.Integer(0), sp.Integer(-1), sp.Rational(-1, 2), sp.Integer(-2), sp.Integer(-10),
                 sp.pi / 7)


def has_interior_point(exprs, var) -> bool:
    """Some real point where every expression is defined on a neighbourhood. A `∀ x, … →
    HasDerivAt …` statement about a function defined NOWHERE on the reals would be proved
    entirely about junk values (e.g. `√(−x² − 1)` is constantly 0 in Lean)."""
    return any(all(interior_defined_at(e, var, p) for e in exprs) for p in _PROBE_POINTS)


def _print_lean(e, field: str = "ℝ") -> str:
    """Exact printer. Raises LeanPrintError on anything not covered."""
    e = sp.sympify(e)
    if isinstance(e, sp.MatrixBase):
        rows = "; ".join(", ".join(_print_lean(e[i, j], field) for j in range(e.shape[1]))
                         for i in range(e.shape[0]))
        # always ascribe the element type: bare numeric literals otherwise elaborate as ℕ and
        # the goal fails with "failed to synthesize CommRing ℕ"
        return f"(!![{rows}] : Matrix (Fin {e.shape[0]}) (Fin {e.shape[1]}) {field})"
    if isinstance(e, sp.Integer):
        n = int(e)
        return f"({n} : {field})" if n < 0 else str(n)
    if isinstance(e, sp.Rational):
        p, q = int(e.p), int(e.q)
        if field == "ℤ":
            raise LeanPrintError(f"non-integer rational {e} in {field}")
        return f"({p} / {q} : {field})"
    if isinstance(e, sp.Float):
        r = sp.nsimplify(e, rational=True)
        if isinstance(r, sp.Rational):
            return _print_lean(r, field)
        raise LeanPrintError(f"float {e}")
    if e is sp.pi:
        return "Real.pi"
    if e is sp.E:
        return "Real.exp 1"
    if isinstance(e, sp.Symbol):
        return e.name
    if isinstance(e, sp.Add):
        args = [_print_lean(a, field) for a in e.args]
        out = args[0]
        for a in args[1:]:
            out = f"{out} - {a[1:]}" if a.startswith("-") else f"{out} + {a}"
        return f"({out})"
    if isinstance(e, sp.Mul):
        coeff, rest = e.as_coeff_Mul()
        if coeff == -1:
            return f"(-{_print_lean(rest, field)})"
        num, den = e.as_numer_denom()
        if den != 1:
            if field == "ℤ":
                raise LeanPrintError("division over ℤ")
            return f"({_print_lean(num, field)} / {_print_lean(den, field)})"
        args = [_print_lean(a, field) for a in e.args]
        return "(" + " * ".join(args) + ")"
    if isinstance(e, (sp.MatPow, sp.MatMul, sp.MatAdd)):
        if isinstance(e, sp.MatPow):
            return f"({_print_lean(e.args[0], field)} ^ {_print_lean(e.args[1], field)})"
        op = " * " if isinstance(e, sp.MatMul) else " + "
        return "(" + op.join(_print_lean(a, field) for a in e.args) + ")"
    if isinstance(e, sp.Pow):
        b, x = e.args
        if isinstance(b, sp.MatrixBase) and isinstance(x, sp.Integer):
            return f"({_print_lean(b, field)} ^ {int(x)})"
        if isinstance(x, sp.Integer):
            n = int(x)
            if n >= 0:
                return f"({_print_lean(b, field)} ^ {n})"
            if field == "ℤ":
                raise LeanPrintError("negative integer power over ℤ")
            inner = _print_lean(b, field)
            return f"(1 / {inner})" if n == -1 else f"(1 / ({inner} ^ {-n}))"
        if x == sp.Rational(1, 2):
            return f"Real.sqrt {_paren(_print_lean(b, field))}"
        raise LeanPrintError(f"power {e}")
    if isinstance(e, sp.Abs):
        return f"|{_print_lean(e.args[0], field)}|"
    for cls, nm in _FUNC.items():
        if isinstance(e, cls):
            return f"{nm} {_paren(_print_lean(e.args[0], field))}"
    if isinstance(e, sp.log):
        if len(e.args) == 1:
            return f"Real.log {_paren(_print_lean(e.args[0], field))}"
        raise LeanPrintError("log with explicit base")
    if isinstance(e, sp.Mod):
        return f"({_print_lean(e.args[0], field)} % {_print_lean(e.args[1], field)})"
    # inert or evaluated forms of the integer helpers print the same way
    cname = e.__class__.__name__
    if cname == "gcd" and len(e.args) == 2:
        return f"(Int.gcd {_paren(_print_lean(e.args[0], 'ℤ'))} {_paren(_print_lean(e.args[1], 'ℤ'))} : {field})"
    if cname == "lcm" and len(e.args) == 2:
        return f"(Int.lcm {_paren(_print_lean(e.args[0], 'ℤ'))} {_paren(_print_lean(e.args[1], 'ℤ'))} : {field})"
    if cname == "factorial":
        return f"(Nat.factorial {_paren(_print_lean(e.args[0], 'ℤ'))} : {field})"
    if cname == "binomial":
        return f"(Nat.choose {_paren(_print_lean(e.args[0], 'ℤ'))} {_paren(_print_lean(e.args[1], 'ℤ'))} : {field})"
    raise LeanPrintError(f"cannot print {type(e).__name__}: {e}")


_REL_OP = {sp.Equality: "=", sp.Unequality: "≠", sp.StrictLessThan: "<", sp.LessThan: "≤",
           sp.StrictGreaterThan: ">", sp.GreaterThan: "≥"}


def relation_to_lean(rel, field: str = "ℝ") -> str:
    if rel is sp.true:
        return "True"
    if rel is sp.false:
        return "False"
    for cls, op in _REL_OP.items():
        if isinstance(rel, cls):
            return f"{sympy_to_lean(rel.lhs, field)} {op} {sympy_to_lean(rel.rhs, field)}"
    if isinstance(rel, sp.And):
        return " ∧ ".join(f"({relation_to_lean(a, field)})" for a in rel.args)
    if isinstance(rel, sp.Or):
        return " ∨ ".join(f"({relation_to_lean(a, field)})" for a in rel.args)
    if isinstance(rel, sp.Not):
        return f"¬({relation_to_lean(rel.args[0], field)})"
    raise LeanPrintError(f"cannot print relation {rel}")


def _subs_rel(rel, var, val):
    """Substitute into both sides and rebuild WITHOUT evaluation, so the resulting claim is
    something Lean checks rather than something SymPy already decided."""
    if isinstance(rel, (sp.And, sp.Or)):
        return rel.func(*[_subs_rel(a, var, val) for a in rel.args])
    if isinstance(rel, sp.core.relational.Relational):
        return rel.func(rel.lhs.subs(var, val), rel.rhs.subs(var, val), evaluate=False)
    return rel.subs(var, val)


def _interval_to_lean(s: sp.Set, var: str, field: str = "ℝ") -> str:
    """Membership predicate for a (union of) interval(s) / finite set, as a proposition in `var`."""
    if s is S.EmptySet:
        return "False"
    if isinstance(s, sp.Union):
        return " ∨ ".join(f"({_interval_to_lean(a, var, field)})" for a in s.args)
    if isinstance(s, sp.FiniteSet):
        return " ∨ ".join(f"{var} = {sympy_to_lean(e, field)}" for e in s.args)
    if isinstance(s, sp.Interval):
        parts = []
        if s.inf != -sp.oo:
            parts.append(f"{sympy_to_lean(s.inf, field)} {'<' if s.left_open else '≤'} {var}")
        if s.sup != sp.oo:
            parts.append(f"{var} {'<' if s.right_open else '≤'} {sympy_to_lean(s.sup, field)}")
        return " ∧ ".join(parts) if parts else "True"
    raise LeanPrintError(f"cannot print set {s}")


@dataclass
class LeanStatement:
    name: str
    binders: str                 # "(a b : ℝ)"
    hypotheses: list[str]        # rendered hypothesis propositions (without names)
    goal: str
    field: str
    kind: str                    # which template produced it
    note: str = ""
    hints: tuple[str, ...] = ()  # goal-specific tactics the template can supply (tried first)

    def theorem(self, proof: str) -> str:
        hs = " ".join(f"(h{i} : {h})" for i, h in enumerate(self.hypotheses, start=1))
        head = " ".join(x for x in [f"theorem {self.name}", self.binders, hs] if x)
        return f"{head} : {self.goal} := by\n{proof}"

    def vacuity_probe(self) -> str | None:
        """Theorem asking for False from the same hypotheses: if it compiles, the hypotheses
        are contradictory and the real theorem is vacuously true (handoff failure mode #5/#6)."""
        if not self.hypotheses:
            return None
        hs = " ".join(f"(h{i} : {h})" for i, h in enumerate(self.hypotheses, start=1))
        head = " ".join(x for x in [f"theorem {self.name}_vacuity", self.binders, hs] if x)
        # The probe must be at least as strong as the proof search, or a proof can use a
        # contradiction the probe cannot see. Measured: with the guard `x - 2 ≠ 0` next to
        # `1/(x-2) = 0` the hypotheses ARE contradictory, the ladder proved `x = 2` with
        # `simp_all; linarith`, and the old single-tactic probe failed to derive False — so the
        # certificate passed its audit. Hence the ladder's own combinations, plus, for every
        # `≠` hypothesis, an attempt to prove the equality it forbids.
        #
        # Every alternative is wrapped in `(…; done)`. `first` commits to the first alternative
        # that RUNS, not the first that CLOSES the goal, and `norm_num at *` runs happily while
        # leaving the goal open — so in the original probe `norm_num at *` silently shadowed
        # `simp_all` behind it. HANDOFF §6 records the same trap for the proof ladders; the
        # probe had been left in the old form since F5.
        closers = ["linarith", "nlinarith", "simp at *; linarith", "norm_num at *; linarith",
                   "field_simp at *; linarith", "simp at *; nlinarith"]
        inner = "first | " + " | ".join(f"({c}; done)" for c in closers)
        alts = ["omega", "linarith", "nlinarith", "norm_num at *", "simp_all",
                "simp_all; linarith", "simp_all; nlinarith", "norm_num at *; linarith",
                "simp at *; linarith", "field_simp at *; linarith"]
        alts += [f"exact h{i} (by {inner})" for i, h in enumerate(self.hypotheses, start=1)
                 if " ≠ " in h and "∀" not in h and "∃" not in h]
        return f"{head} : False := by\n  first | " + " | ".join(f"({a}; done)" for a in alts)

    def no_hyp_probe(self, proof: str) -> str | None:
        """Same goal without the hypotheses: if it still proves, the data were never used."""
        if not self.hypotheses:
            return None
        head = " ".join(x for x in [f"theorem {self.name}_nohyp", self.binders] if x)
        return f"{head} : {self.goal} := by\n{proof}"


def _field_for(ir_obj) -> str:
    doms = {v.domain for v in ir_obj.vars}
    if doms and doms <= {"integer", "positive_integer", "nonneg_integer", "natural"}:
        return "ℤ"
    return "ℝ"


def _domain_hyps(obj, ns, field: str, only: str | None = None) -> list[str]:
    out = []
    for v in obj.vars:
        if only and v.name != only:
            continue
        cond = _DOMAIN_COND.get(v.domain)
        if cond:
            out.append(cond.format(v=v.name))
        for c in v.constraints:
            out.append(relation_to_lean(parse_relation(c, ns), field))
    return out


# ---------------------------------------------------------------------------- templates
def _t_evaluate(obj, ns, ca, name) -> LeanStatement | None:
    p = obj.task.params
    field = _field_for(obj)
    expr_src = p.get("expr") or obj.unknown_of_interest
    if not expr_src:
        return None
    target = parse_structural(expr_src, ns)
    claimed = parse_structural(str(ca["payload"]), ns) if ca["kind"] in ("value", "expression") \
        else parse_answer(ca["kind"], ca["payload"], ns)
    if isinstance(claimed, sp.Set) or claimed is None:
        return None
    if isinstance(target, sp.MatrixBase) or isinstance(claimed, sp.MatrixBase):
        field = "ℝ"
    given_rels = [parse_relation_structural(g, ns) for g in obj.givens]
    hyps = [relation_to_lean(r, field) for r in given_rels]
    hyps += _domain_hyps(obj, ns, field)
    # Junk values (see the section at the top): a claim whose value depends on where a variable
    # sits is out of scope, and every open partial operation in the givens or the target becomes
    # a guard hypothesis. Without the guard, `1/(x-2) = 0` is satisfied by x = 2 in Lean, so
    # "evaluate x" would be proved = 2 for a system that has no solution at all; with it, the
    # hypotheses are contradictory and the vacuity probe rejects the proof.
    if not isinstance(claimed, sp.MatrixBase) and open_guards([claimed], field):
        return None
    if not isinstance(target, sp.MatrixBase):
        hyps += [g for g in open_guards(given_rels + [target], field) if g not in hyps]
    tgt_txt, cl_txt = sympy_to_lean(target, field), sympy_to_lean(claimed, field)
    goal = f"{tgt_txt} = {cl_txt}"
    binders = f"({' '.join(v.name for v in obj.vars)} : {field})" if obj.vars else ""
    kind = "closed_arithmetic" if (not obj.vars and not hyps) else "evaluate_system"
    hints: list[str] = []
    # `Real.sqrt X = v` needs the square witness; the template knows both sides
    if tgt_txt.startswith("Real.sqrt ") and not target.free_symbols:
        inner = tgt_txt[len("Real.sqrt "):]
        hints.append(f"  rw [show {inner} = {cl_txt} ^ 2 by norm_num,\n"
                     f"     Real.sqrt_sq (by norm_num : (0:ℝ) ≤ {cl_txt})]")
    hints += _trig_hints(target, field)
    return LeanStatement(name, binders, hyps, goal, field, kind, hints=tuple(hints))


_STD_ANGLE = {30: "Real.pi / 6", 45: "Real.pi / 4", 60: "Real.pi / 3", 90: "Real.pi / 2",
              180: "Real.pi", 0: "0"}
_STD_LEMMAS = ("Real.sin_pi_div_four", "Real.cos_pi_div_four", "Real.sin_pi_div_six",
               "Real.cos_pi_div_six", "Real.sin_pi_div_three", "Real.cos_pi_div_three",
               "Real.sin_pi_div_two", "Real.cos_pi_div_two")


def _trig_hints(target, field: str) -> list[str]:
    """sin/cos of a non-standard degree angle that splits into two standard ones: rewrite with
    the addition formula and the standard values, then split √6 into √2·√3 so `ring` closes."""
    out: list[str] = []
    for node in sp.preorder_traversal(target):
        if not isinstance(node, (sp.sin, sp.cos)):
            continue
        arg = sp.simplify(node.args[0] / sp.pi * 180)
        if not arg.is_Integer:
            continue
        deg = int(arg)
        if deg in _STD_ANGLE:
            continue
        for a in (30, 45, 60, 90):
            for b in (30, 45, 60, 90):
                for sign, law in ((1, "add"), (-1, "sub")):
                    if a + sign * b != deg:
                        continue
                    fn = "Real.sin" if isinstance(node, sp.sin) else "Real.cos"
                    law_lemma = f"{fn}_{law}"
                    arg_txt = sympy_to_lean(node.args[0], "ℝ")
                    combo = f"{_STD_ANGLE[a]} {'+' if sign > 0 else '-'} {_STD_ANGLE[b]}"
                    # `simp only` for the standard values: a `rw` list fails unless EVERY
                    # lemma in it fires, and only two of the eight apply to a given angle
                    head = (f"  rw [show {arg_txt} = {combo} by ring, {law_lemma}]\n"
                            f"  simp only [" + ", ".join(_STD_LEMMAS) + "]\n")
                    out.append(head +
                               "  rw [show Real.sqrt 6 = Real.sqrt 2 * Real.sqrt 3 from by\n"
                               "        rw [← Real.sqrt_mul (by norm_num : (0:ℝ) ≤ 2)]; norm_num]\n  ring")
                    out.append(head + "  ring")
        if out:
            break
    return out[:4]


def _t_solve_equation(obj, ns, ca, name) -> LeanStatement | None:
    from ..certify.domain import definedness_conditions
    p = obj.task.params
    field = _field_for(obj)
    var = ns.get(p.get("var", "x"))
    if not isinstance(var, sp.Symbol):
        return None
    eq_src = p.get("equation") or (obj.givens[0] if obj.givens else None)
    if not eq_src:
        return None
    rel = parse_relation(eq_src, ns)
    shape = ca["kind"] if ca["kind"] in ("set", "interval") else "set"
    claimed = parse_answer(shape, ca["payload"], ns)
    if claimed is S.EmptySet:
        roots: list = []
    elif isinstance(claimed, sp.FiniteSet):
        roots = list(claimed.args)
    else:
        return None
    conds = []
    for v in obj.vars:
        if v.name == var.name:
            c = _DOMAIN_COND.get(v.domain)
            if c:
                conds.append(parse_relation(c.format(v=v.name), ns))
    conds += list(definedness_conditions(rel, var))
    guard = "".join(f"({relation_to_lean(c, field)}) → " for c in conds)
    eq_txt = relation_to_lean(rel, field)
    if roots:
        disj = " ∨ ".join(f"{var.name} = {sympy_to_lean(r, field)}" for r in roots)
        parts = [f"(∀ {var.name} : {field}, {guard}(({eq_txt}) ↔ ({disj})))"]
    else:
        parts = [f"(∀ {var.name} : {field}, {guard}¬({eq_txt}))"]
    # each claimed root must itself satisfy the conditions and the equation
    memberships: list[str] = []
    for r in roots:
        for c in conds:
            memberships.append(relation_to_lean(_subs_rel(c, var, r), field))
        memberships.append(relation_to_lean(_subs_rel(rel, var, r), field))
    parts += [f"({m})" for m in memberships]
    goal = " ∧ ".join(parts)
    hints = _solve_equation_hints(rel, var, roots, conds, memberships, field)
    return LeanStatement(name, "", [], goal, field, "solve_equation_set", hints=hints)


def _membership_tactic(txt: str) -> str:
    """Closer for one `root satisfies ...` conjunct. A square root needs its square witness."""
    if "Real.sqrt" in txt and " = " in txt:
        return "by rw [show (0:ℝ) = 0 from rfl]; norm_num [Real.sqrt_eq_iff_mul_self_eq]"
    return "by norm_num"


def _solve_equation_hints(rel, var, roots, conds, memberships, field) -> tuple[str, ...]:
    """Complete candidate proofs built from the statement's own shape (arity of the conjunction,
    number of guard hypotheses, and which pattern the equation follows)."""
    intro = " ".join(["fun", var.name] + [f"h{i}" for i in range(1, len(conds) + 1)]) + " => ?_"
    n_mem = len(memberships)
    has_sqrt = rel.has(sp.Pow) and any(a.args[1] == sp.Rational(1, 2) for a in rel.atoms(sp.Pow)
                                       if len(a.args) == 2)
    has_abs = rel.has(sp.Abs)
    has_log = rel.has(sp.log)
    radicand = None
    if has_sqrt:
        for a in rel.atoms(sp.Pow):
            if len(a.args) == 2 and a.args[1] == sp.Rational(1, 2):
                radicand = sympy_to_lean(a.args[0], field)
                break
    forwards: list[str] = []
    if has_sqrt and radicand:
        forwards.append(
            f"  constructor\n"
            f"  · intro h\n"
            f"    have hnn : (0:ℝ) ≤ Real.sqrt {_paren(radicand)} := Real.sqrt_nonneg _\n"
            f"    have hsq := Real.sq_sqrt (show (0:ℝ) ≤ {radicand} by linarith)\n"
            f"    nlinarith [h, hsq, hnn]\n"
            f"  · rintro rfl\n    norm_num")
    if has_abs:
        rhs = sympy_to_lean(rel.rhs, field) if isinstance(rel, sp.Equality) else None
        if rhs:
            forwards.append(
                f"  constructor\n"
                f"  · intro h\n"
                f"    rcases (abs_eq (by norm_num : (0:ℝ) ≤ {rhs})).mp h with h' | h'\n"
                f"    · right; linarith\n    · left; linarith\n"
                f"  · rintro (rfl | rfl) <;> rw [abs_eq (by norm_num : (0:ℝ) ≤ {rhs})] <;> norm_num")
    if has_log and isinstance(rel, sp.Equality):
        # log A + log B = log C with A, B > 0: combine the logs and use injectivity on (0, ∞)
        logs = [a for a in rel.lhs.atoms(sp.log)] if rel.lhs.has(sp.log) else []
        rhs_log = list(rel.rhs.atoms(sp.log))
        if len(logs) == 2 and len(rhs_log) == 1 and len(conds) >= 2:
            c_txt = sympy_to_lean(rhs_log[0].args[0], field)
            forwards.append(
                f"  rw [← Real.log_mul (by linarith) (by linarith)]\n"
                f"  constructor\n"
                f"  · intro h\n"
                f"    have hinj := Real.log_injOn_pos (Set.mem_Ioi.mpr (by nlinarith)) "
                f"(Set.mem_Ioi.mpr (by norm_num : (0:ℝ) < {c_txt})) h\n"
                f"    nlinarith [hinj]\n"
                f"  · rintro rfl\n    norm_num")
    if not (has_sqrt or has_abs or has_log):
        forwards.append("  constructor <;> intro h <;> linarith")
        forwards.append("  constructor <;> intro h <;> nlinarith")
        if len(conds) == 1:
            forwards.append("  rw [div_eq_iff h1]\n  constructor <;> intro h <;> linarith")
    if not roots:                                  # empty solution set: derive a contradiction
        names = " ".join(f"h{i}" for i in range(1, len(conds) + 1))
        bodies = ["  intro h\n  field_simp at h\n  exact h1 (by linarith)",
                  "  intro h\n  field_simp at h\n  linarith",
                  "  intro h\n  linarith", "  intro h\n  nlinarith [h]"]
        return tuple(f"  refine fun {var.name} {names} => ?_\n{b}" for b in bodies)
    mem = ", ".join(_membership_tactic(m) for m in memberships) if n_mem else ""
    out = []
    for f in forwards:
        head = f"  refine ⟨{intro}" + (f", {mem}" if mem else "") + "⟩\n"
        out.append(head + f)
    return tuple(out)


def _t_solve_inequality(obj, ns, ca, name) -> LeanStatement | None:
    from ..certify.domain import definedness_conditions
    p = obj.task.params
    field = _field_for(obj)
    var = ns.get(p.get("var", "x"))
    if not isinstance(var, sp.Symbol):
        return None
    src = p.get("inequality") or (obj.givens[0] if obj.givens else None)
    if not src or len(obj.givens) > 1:
        return None
    rel = parse_relation(src, ns)
    claimed = parse_answer("set" if ca["kind"] in ("set", "interval") else "set", ca["payload"], ns)
    if not isinstance(claimed, sp.Set):
        return None
    conds = list(definedness_conditions(rel, var))
    guard = "".join(f"({relation_to_lean(c, field)}) → " for c in conds)
    memb = _interval_to_lean(claimed, var.name, field)
    parts = [f"(∀ {var.name} : {field}, {guard}(({relation_to_lean(rel, field)}) ↔ ({memb})))"]
    # Without this second half the guarded iff cannot tell "x < -2" from "x ≤ -2" when x = -2 is
    # outside the domain: both sides are simply never reached there. Asserting that every
    # claimed point IS in the domain makes the statement say what "solution set" means (measured
    # on tyt-esf-012, whose only defect is exactly that endpoint).
    if conds:
        cond_txt = " ∧ ".join(f"({relation_to_lean(c, field)})" for c in conds)
        parts.append(f"(∀ {var.name} : {field}, ({memb}) → ({cond_txt}))")
    hints: tuple[str, ...] = ()
    if conds:
        hints = (f"  refine ⟨fun {var.name} hx => ?_, fun {var.name} hm => ?_⟩\n"
                 f"  · rw [ge_iff_le, div_nonneg_iff]\n"
                 f"    constructor\n"
                 f"    · rintro (⟨h1, h2⟩ | ⟨h1, h2⟩)\n      · right; linarith\n"
                 f"      · left\n        rcases lt_or_eq_of_le h2 with h3 | h3\n"
                 f"        · linarith\n        · exact absurd h3 hx\n"
                 f"    · rintro (h | h)\n      · right; constructor <;> linarith\n"
                 f"      · left; constructor <;> linarith\n"
                 f"  · rcases hm with h | h <;> intro hc <;> linarith",)
    return LeanStatement(name, "", [], " ∧ ".join(parts), field, "solve_inequality_iff", hints=hints)


def _t_equation_of(obj, ns, ca, name) -> LeanStatement | None:
    """Claimed curve equation vs the one the stated conditions determine: same solution set."""
    from ..certify.geometry import truth_equation
    from ..certify.base import Ctx
    p = obj.task.params
    x, y = ns.get(p.get("x", "x")), ns.get(p.get("y", "y"))
    if not (isinstance(x, sp.Symbol) and isinstance(y, sp.Symbol)):
        return None
    ctx = Ctx(ir=obj, ns=ns)
    try:
        truth = truth_equation(ctx, p, x, y)
    except Exception:
        return None
    claimed = parse_answer(ca["kind"] if ca["kind"] == "equation" else "value", ca["payload"], ns)
    if not isinstance(claimed, sp.Equality):
        if isinstance(claimed, sp.Expr):
            claimed = sp.Eq(claimed, 0, evaluate=False)
        else:
            return None
    # A curve written with a partial operation in x or y (`y = 1/x`) takes junk values off its
    # domain, so the iff would be about points that are not on either curve. Out of scope.
    if open_guards([claimed, truth], "ℝ"):
        return None
    goal = (f"∀ {x.name} {y.name} : ℝ, (({relation_to_lean(claimed, 'ℝ')}) ↔ "
            f"({relation_to_lean(truth, 'ℝ')}))")
    return LeanStatement(name, "", [], goal, "ℝ", "equation_of_iff")


def _t_series_sum(obj, ns, ca, name) -> LeanStatement | None:
    p = obj.task.params
    var = ns.get(p.get("var", "k"))
    if not isinstance(var, sp.Symbol):
        return None
    lo = parse_expr_str(str(p.get("lo", "1")), ns)
    hi = parse_expr_str(str(p.get("hi", "oo")), ns)
    if hi == sp.oo or lo == -sp.oo or not (lo.is_Integer and hi.is_Integer):
        return None                                   # only finite sums are exactly expressible
    if int(hi) - int(lo) > 200:
        return None
    term = parse_expr_str(p["term"], ns)
    claimed = parse_answer(ca["kind"], ca["payload"], ns)
    if isinstance(claimed, sp.Set) or claimed is None:
        return None
    # every summand must be defined: ∑_{k=-1}^{1} 1/k is undefined, but Lean adds −1 + 0 + 1 = 0
    for k in range(int(lo), int(hi) + 1):
        for c in _definedness(term, var):
            if getattr(c, "free_symbols", None) and _closed_truth(c.subs(var, k)) is not True:
                return None
    field = "ℤ" if (term.is_polynomial(var) and all(c.is_Integer for c in sp.Poly(term, var).coeffs())
                    and claimed.is_Integer) else "ℝ"
    body = sympy_to_lean(term.subs(var, sp.Symbol(var.name)), field)
    goal = (f"(∑ {var.name} ∈ Finset.Icc ({sympy_to_lean(lo, 'ℤ')} : ℤ) {sympy_to_lean(hi, 'ℤ')}, "
            f"({body} : {field})) = {sympy_to_lean(claimed, field)}")
    return LeanStatement(name, "", [], goal, field, "series_sum_finite")


def _t_extremum(obj, ns, ca, name) -> LeanStatement | None:
    p = obj.task.params
    which = p.get("which", "max")
    if which not in ("max", "min"):
        return None
    var = ns.get(p.get("var", "x"))
    if not isinstance(var, sp.Symbol):
        return None
    iv = parse_set_str(p.get("interval", "Reals"), ns) if p.get("interval") else None
    if not isinstance(iv, sp.Interval) or iv.inf == -sp.oo or iv.sup == sp.oo:
        return None
    f = parse_expr_str(p["f"], ns)
    claimed = parse_answer(ca["kind"], ca["payload"], ns)
    if isinstance(claimed, sp.Set) or claimed is None:
        return None
    # f must be defined on the whole interval: at a pole Lean's f is 0, so e.g. −1/x² on [−1, 1]
    # would have a provable "maximum 0" attained at the junk point x = 0
    if not defined_on(f, var, iv):
        return None
    memb = _interval_to_lean(iv, var.name, "ℝ")
    fx = sympy_to_lean(f, "ℝ")
    v = sympy_to_lean(claimed, "ℝ")
    op = "≤" if which == "max" else "≥"
    goal = (f"(∃ {var.name} : ℝ, ({memb}) ∧ {fx} = {v}) ∧ "
            f"(∀ {var.name} : ℝ, ({memb}) → {fx} {op} {v})")
    # the existence half needs a witness; the deterministic certificate already knows where the
    # extremum is attained, so the template supplies it as a proof hint (Lean still checks it)
    hints: list[str] = []
    try:
        from ..certify.extremum import certify_extremum
        ok, ev = certify_extremum(f, var, iv, which, claimed, timeout=5.0)
        # nlinarith needs the right products; derive them from the factorisation of f - v:
        # each quadratic cofactor a*x^2 + b*x + c contributes sq_nonneg (x + b/(2a)), and each
        # bound of the interval contributes a non-negative factor to multiply it with.
        terms = [f"sq_nonneg ({var.name} - {sympy_to_lean(sp.nsimplify(w), 'ℝ')})"
                 for w in (ev.get("attained_at") or [])[:2]]
        diff = sp.factor(sp.expand(f - claimed))
        for fac, _mult in sp.factor_list(diff)[1]:
            try:
                poly = sp.Poly(fac, var)
            except sp.PolynomialError:
                continue
            if poly.degree() == 2:
                a2, b2, _c2 = poly.all_coeffs()
                shift = sp.nsimplify(b2 / (2 * a2))
                terms.append(f"sq_nonneg ({var.name} + {sympy_to_lean(shift, 'ℝ')})")
        lo_txt, hi_txt = sympy_to_lean(iv.inf, "ℝ"), sympy_to_lean(iv.sup, "ℝ")
        prods = [f"mul_nonneg (by linarith : (0:ℝ) ≤ {hi_txt} - {var.name}) ({t})" for t in terms]
        prods += [f"mul_nonneg (by linarith : (0:ℝ) ≤ {var.name} - {lo_txt}) ({t})" for t in terms]
        hint_terms = ", ".join(["h1", "h2"] + terms + prods)
        for w in (ev.get("attained_at") or [])[:2]:
            wl = sympy_to_lean(sp.nsimplify(w), "ℝ")
            hints.append(f"  refine ⟨⟨{wl}, by norm_num, by norm_num⟩, fun {var.name} hx => ?_⟩\n"
                         f"  obtain ⟨h1, h2⟩ := hx\n"
                         f"  nlinarith [{hint_terms}]")
    except Exception:
        pass
    return LeanStatement(name, "", [], goal, "ℝ", f"extremum_{which}", hints=tuple(hints))


def _t_count_integers(obj, ns, ca, name) -> LeanStatement | None:
    p = obj.task.params
    var = ns.get(p.get("var", "x"))
    if not isinstance(var, sp.Symbol) or not obj.givens:
        return None
    rels = [parse_relation(g, ns) for g in obj.givens]
    if open_guards(rels, "ℤ"):
        return None                         # a partial operation in the predicate: junk-prone
    from ..equiv import exact_integer
    n = exact_integer(ca["payload"])     # never int(): a claimed 3.5 would become a proof of 3
    if n is None:
        return None
    sol = sp.solveset(rels[0] if len(rels) == 1 else sp.And(*rels), var, S.Reals)
    if not isinstance(sol, sp.Interval) or sol.inf == -sp.oo or sol.sup == sp.oo:
        return None
    lo, hi = sp.ceiling(sol.inf), sp.floor(sol.sup)
    if not (lo.is_Integer and hi.is_Integer) or int(hi) - int(lo) > 300:
        return None
    pred = " ∧ ".join(f"({relation_to_lean(r, 'ℤ')})" for r in rels)
    goal = (f"(∀ {var.name} : ℤ, ({pred}) → {var.name} ∈ Finset.Icc ({int(lo)} : ℤ) {int(hi)}) ∧ "
            f"((Finset.Icc ({int(lo)} : ℤ) {int(hi)}).filter (fun {var.name} => {pred})).card = {n}")
    return LeanStatement(name, "", [], goal, "ℤ", "count_integers_finset")


def _t_linalg(obj, ns, ca, name) -> LeanStatement | None:
    p = obj.task.params
    op = p.get("op")
    claimed = parse_answer(ca["kind"] if ca["kind"] in ("set",) else "value", ca["payload"], ns) \
        if ca.get("payload") is not None else None
    def M(src):
        m = parse_expr_str(src, ns)
        return sp.Matrix(m) if isinstance(m, sp.MatrixBase) else None
    if op == "inverse":
        A, C = M(p["matrix"]), (sp.Matrix(claimed) if isinstance(claimed, sp.MatrixBase) else None)
        if A is None or C is None or A.shape != C.shape:
            return None
        goal = (f"({sympy_to_lean(A)} * {sympy_to_lean(C)} = 1) ∧ "
                f"({sympy_to_lean(C)} * {sympy_to_lean(A)} = 1)")
        return LeanStatement(name, "", [], goal, "ℝ", "linalg_inverse")
    if op == "matrix_expr":
        T = parse_structural(p["expr"], ns)          # keep the power/product unevaluated
        C = claimed
        if not isinstance(C, sp.MatrixBase):
            return None
        if not (isinstance(T, (sp.MatrixBase, sp.MatPow, sp.MatMul, sp.MatAdd))
                or (isinstance(T, sp.Pow) and isinstance(T.args[0], sp.MatrixBase))):
            return None
        return LeanStatement(name, "", [], f"{sympy_to_lean(T)} = {sympy_to_lean(C)}", "ℝ",
                             "linalg_matrix_expr")
    if op == "eigenvector":
        A = M(p["matrix"])
        lam = parse_expr_str(str(p["eigenvalue"]), ns)
        v = claimed
        if A is None or v is None:
            return None
        vm = sp.Matrix(v)
        if vm.shape[0] == 1:
            vm = vm.T
        if vm.shape != (A.shape[0], 1):
            return None
        vec = "![" + ", ".join(sympy_to_lean(vm[i, 0]) for i in range(vm.shape[0])) + "]"
        # explicit `Matrix.mulVec`: the `*ᵥ` notation does not elaborate in this toolchain
        goal = (f"(Matrix.mulVec {sympy_to_lean(A)} {vec} = {sympy_to_lean(lam)} • {vec}) ∧ "
                f"(({vec} : Fin {vm.shape[0]} → ℝ) ≠ 0)")
        return LeanStatement(name, "", [], goal, "ℝ", "linalg_eigenvector")
    if op == "solve_system":
        A, b = M(p["A"]), parse_expr_str(p["b"], ns)
        x = claimed
        if A is None or b is None or x is None:
            return None
        bm, xm = sp.Matrix(b), sp.Matrix(x)
        if bm.shape[0] == 1:
            bm = bm.T
        if xm.shape[0] == 1:
            xm = xm.T
        bv = "![" + ", ".join(sympy_to_lean(bm[i, 0]) for i in range(bm.shape[0])) + "]"
        xv = "![" + ", ".join(sympy_to_lean(xm[i, 0]) for i in range(xm.shape[0])) + "]"
        goal = (f"(Matrix.mulVec {sympy_to_lean(A)} {xv} = {bv}) ∧ "
                f"({sympy_to_lean(A)}.det ≠ 0)")
        return LeanStatement(name, "", [], goal, "ℝ", "linalg_solve_system")
    if op == "eigenvalues":
        A = M(p["matrix"])
        cl = parse_answer("set", ca["payload"], ns) if ca["kind"] in ("set", "interval") else None
        if A is None or not isinstance(cl, sp.FiniteSet) or A.shape != (2, 2):
            return None
        disj = " ∨ ".join(f"t = {sympy_to_lean(e)}" for e in cl.args)
        goal = (f"∀ t : ℝ, (({sympy_to_lean(A)} - t • (1 : Matrix (Fin 2) (Fin 2) ℝ)).det = 0) ↔ ({disj})")
        # the characteristic polynomial factors over the claimed roots; hand Lean that factorisation
        hints: tuple[str, ...] = ()
        if len(cl.args) == 2:
            r1, r2 = (sympy_to_lean(e) for e in cl.args)
            hints = (
                f"  norm_num [Matrix.det_fin_two, Matrix.one_fin_two]\n"
                f"  intro t\n  constructor\n"
                f"  · intro h\n"
                f"    have hf : (t - {r1}) * (t - {r2}) = 0 := by nlinarith\n"
                f"    rcases mul_eq_zero.mp hf with h1 | h1\n"
                f"    · left; linarith\n    · right; linarith\n"
                f"  · rintro (h | h) <;> subst h <;> norm_num",)
        return LeanStatement(name, "", [], goal, "ℝ", "linalg_eigenvalues", hints=hints)
    return None


def _t_definite_integral(obj, ns, ca, name) -> LeanStatement | None:
    p = obj.task.params
    var = ns.get(p.get("var", "x"))
    if not isinstance(var, sp.Symbol):
        return None
    integrand = parse_expr_str(p["integrand"], ns)
    # piecewise integrands (Abs, floor, sign) need a split Mathlib will not do on its own
    if integrand.has(sp.Abs, sp.floor, sp.ceiling, sp.sign, sp.Piecewise):
        return None
    a = parse_structural(str(p["a"]), ns)
    b = parse_structural(str(p["b"]), ns)
    claimed = parse_structural(str(ca["payload"]), ns) if ca["kind"] in ("value", "expression") \
        else parse_answer(ca["kind"], ca["payload"], ns)
    if claimed is None or isinstance(claimed, sp.Set):
        return None
    # Mathlib's interval integral of a function that is not integrable is 0 BY DEFINITION, so
    # "∫_{-1}^{1} dx/x = 0" — the classic principal-value mistake — is a true Lean statement.
    # The integrand must be defined on the whole closed interval; then it is continuous there
    # (every function the printer accepts is), and Lean's integral is the real one.
    if a.free_symbols or b.free_symbols:
        return None
    lo, hi = (a, b) if bool(sp.N(a - b, 30) <= 0) else (b, a)
    if not defined_on(integrand, var, sp.Interval(lo, hi)):
        return None
    body = sympy_to_lean(integrand, "ℝ")
    goal = (f"∫ {var.name} in ({sympy_to_lean(a, 'ℝ')} : ℝ)..({sympy_to_lean(b, 'ℝ')}), {body} "
            f"= {sympy_to_lean(claimed, 'ℝ')}")
    return LeanStatement(name, "", [], goal, "ℝ", "definite_integral",
                         hints=_ftc_hints(integrand, var, a, b, body))


def _finite_at(expr, var, pt) -> bool:
    try:
        v = complex(sp.N(expr.subs(var, pt), 20))
    except (TypeError, ValueError, ZeroDivisionError, AttributeError):
        return False
    return all(math.isfinite(c) for c in (v.real, v.imag))


def _ftc_hints(integrand, var, a, b, body: str) -> tuple[str, ...]:
    """Tactics built on the fundamental theorem of calculus: SymPy *proposes* an antiderivative
    and Lean proves, independently, both that it is one (`HasDerivAt`) and what it evaluates to.

    The antiderivative never enters the theorem statement, so a wrong proposal costs a failed
    proof, never a false certificate — the same separation of the generating calculation from the
    checking calculation that the rest of the system runs on.  Returns () when the shape is out
    of reach, which simply leaves the generic ladder to try."""
    try:
        used = set(integrand.free_symbols) | set(a.free_symbols) | set(b.free_symbols)
        if any(sym.name == "t" for sym in used) or used - {var}:
            return ()
        lo, hi = sorted([float(sp.N(a)), float(sp.N(b))])
        anti = sp.integrate(integrand, var)
        if anti is None or anti.has(sp.Integral, sp.Piecewise, sp.Abs) or (anti.free_symbols - {var}):
            return ()
        if sp.simplify(sp.diff(anti, var) - integrand) != 0:
            return ()
        # an improper integral has no FTC proof: both functions must stay finite on the *closed*
        # interval, endpoints included, or `fun_prop` cannot discharge differentiability there
        for k in range(21):
            pt = sp.Float(lo) + sp.Rational(k, 20) * (sp.Float(hi) - sp.Float(lo))
            if not _finite_at(integrand, var, pt) or not _finite_at(anti, var, pt):
                return ()
        anti_lean = sympy_to_lean(anti.subs(var, sp.Symbol("t")), "ℝ")
        a_lean, b_lean = sympy_to_lean(a, "ℝ"), sympy_to_lean(b, "ℝ")
    except (TypeError, ValueError, AttributeError, NotImplementedError, sp.SympifyError):
        return ()
    vn = var.name
    t = sp.Symbol("t")
    # (a) constructed route: the derivative proof is assembled term by term from the same tree,
    #     so Lean re-derives it from first principles instead of trusting SymPy
    # (b) `deriv` route: cheap fallback for whatever `simp` can differentiate on its own
    witnesses = [_hasderiv_block(_hasderiv_proof(anti.subs(var, t), t, sp.Symbol(vn)), 4, ()),
                 ["    have hd : DifferentiableAt ℝ (fun t : ℝ => " + anti_lean + f") {vn} := by fun_prop",
                  "    have h := hd.hasDerivAt", "    convert h using 1", _closers(4, ())]]
    out: list[str] = []
    for wit in witnesses:
        if not wit:
            continue
        head = "\n".join([
            f"  have key : ∀ {vn} ∈ Set.uIcc ({a_lean} : ℝ) ({b_lean}), "
            f"HasDerivAt (fun t : ℝ => {anti_lean}) ({body}) {vn} := by",
            f"    intro {vn} hx",
            *wit,
            "  rw [intervalIntegral.integral_eq_sub_of_hasDerivAt key "
            "(by apply Continuous.intervalIntegrable; fun_prop)]",
            "",
        ])
        out += [head + tail for tail in ("  norm_num", "  simp\n  norm_num",
                                         "  field_simp\n  ring_nf\n  norm_num")]
    return tuple(out)


# Mathlib states the derivative combinators with pointwise operations on *functions* (`f * g`),
# so what Lean infers is only definitionally equal to our lambda. These let `simp` bridge that.
_PI_APPLY = "Pi.add_apply, Pi.sub_apply, Pi.mul_apply, Pi.pow_apply, Pi.neg_apply"
# Every alternative must *close* the goal: `simp` can report success while leaving one behind,
# which would silently skip the alternative that actually works.
_CLOSERS = ("rfl", f"funext y; simp [{_PI_APPLY}]; ring", f"funext y; simp [{_PI_APPLY}]",
            "funext y; ring", "simp [{X}]; ring", "simp [{X}]", "field_simp{F}; ring",
            "field_simp{F}", "norm_num [{X}]; ring", "norm_num [{X}]", "ring", "push_cast; ring",
            "nlinarith")
_SIDE_CLOSERS = ("assumption", "positivity", "simp only []; positivity", "intro hc; nlinarith",
                 "nlinarith", "norm_num", "field_simp")


def _closers(indent: int, guards: tuple[str, ...]) -> str:
    x = _PI_APPLY + "".join(", " + g for g in guards)
    f = (" [" + ", ".join(guards) + "]") if guards else ""
    alts = [c.replace("{X}", x).replace("{F}", f) for c in _CLOSERS]
    return " " * indent + "all_goals first | " + " | ".join(f"({a}; done)" for a in alts)


def _hasderiv_block(built, indent: int, guards: tuple[str, ...]) -> list[str]:
    """The tactic lines that turn a compiled `HasDerivAt` term into a proof of the goal.

    Lean infers the derivative itself from the term; the only thing left to show is that the
    *claimed* value equals it. The claim never enters the term, so it cannot steer the proof."""
    if built is None:
        return []
    term, sides = built
    pad = " " * indent
    lines = [f"{pad}have hs{i} : ({s}) ≠ 0 := by first | "
             + " | ".join(f"({c}; done)" for c in _SIDE_CLOSERS)
             for i, s in enumerate(sides)]
    return lines + [f"{pad}have h := {term}", f"{pad}convert h using 1", _closers(indent, guards)]


# `Real.hasDerivAt_f x : HasDerivAt Real.f (<derivative at x>) x`, and the chain-rule version
# `HasDerivAt.f (hg : HasDerivAt g g' x) : HasDerivAt (fun y => Real.f (g y)) (<d> * g') x`.
_HD_UNARY: dict[Any, tuple[str, str]] = {
    sp.exp: ("Real.hasDerivAt_exp", "HasDerivAt.exp"),
    sp.sin: ("Real.hasDerivAt_sin", "HasDerivAt.sin"),
    sp.cos: ("Real.hasDerivAt_cos", "HasDerivAt.cos"),
}


def _hasderiv_proof(e, t, x, point: str | None = None) -> tuple[str, list[str]] | None:
    """Compile `fun t : ℝ => e` into a Lean proof term for `HasDerivAt … at x`.

    The term is built bottom-up from the same expression tree, so nothing about the derivative is
    taken on trust from SymPy: Lean infers the derivative from the term and type-checks every
    step. Nothing about the *claimed* value goes in, which is what keeps the layer honest.
    `x` is what the variable becomes at the evaluation point (a symbol for a ∀-statement, a
    literal for "the derivative at 2"); `point` overrides how that point is printed.

    Returns `(term, sides)`, where `sides` are the expressions a lemma requires to be non-zero —
    emitted as their own Lean goals, never assumed. None means the shape is outside this grammar.
    """
    pt = point if point is not None else x.name
    sides: list[str] = []

    def at_x(sub) -> str:
        return sympy_to_lean(sub.subs(t, x), "ℝ")

    def need_nonzero(expr_lean: str) -> str:
        if expr_lean not in sides:
            sides.append(expr_lean)
        return f"hs{sides.index(expr_lean)}"

    def go(sub) -> str | None:
        if sub == t:
            return f"(hasDerivAt_id' ({pt}))"
        if not sub.has(t):
            return f"(hasDerivAt_const ({pt}) ({sympy_to_lean(sub, 'ℝ')}))"
        if sub.func is sp.log and len(sub.args) == 1:
            if sub.args[0] == t:
                return f"(Real.hasDerivAt_log (x := ({pt})) {need_nonzero(pt)})"
            inner = go(sub.args[0])
            return None if inner is None else \
                f"(HasDerivAt.log {inner} {need_nonzero(at_x(sub.args[0]))})"
        if sub.is_Add:
            acc = go(sub.args[0])
            for nxt in sub.args[1:]:
                rhs = go(nxt)
                if acc is None or rhs is None:
                    return None
                acc = f"({acc}.add {rhs})"
            return acc
        if sub.is_Mul:
            const = sp.Mul(*[f for f in sub.args if not f.has(t)])
            rest = sp.Mul(*[f for f in sub.args if f.has(t)])
            if const != 1 and rest != 1:
                inner = go(rest)
                return None if inner is None else \
                    f"(HasDerivAt.const_mul ({sympy_to_lean(const, 'ℝ')}) {inner})"
            acc = go(sub.args[0])
            for nxt in sub.args[1:]:
                rhs = go(nxt)
                if acc is None or rhs is None:
                    return None
                acc = f"({acc}.mul {rhs})"
            return acc
        if sub.is_Pow and sub.exp.is_Integer and sub.exp >= 2:
            base = go(sub.base)
            return None if base is None else f"({base}.pow {int(sub.exp)})"
        spec = _HD_UNARY.get(sub.func)
        if spec is not None and len(sub.args) == 1:
            direct, chain = spec[0], spec[1]
            if sub.args[0] == t:
                return f"({direct} ({pt}))"
            inner = go(sub.args[0])
            return None if inner is None else f"({chain} {inner})"
        return None

    try:
        term = go(e)
    except (LeanPrintError, AttributeError, TypeError, ValueError):
        return None
    return None if term is None else (term, sides)


def _real_singularities(expr, var) -> list | None:
    """The real points at which `expr` has no value. `None` means SymPy could not decide, and the
    template then declines rather than guessing a domain."""
    try:
        s = sp.singularities(expr, var)
    except (NotImplementedError, TypeError, ValueError, AttributeError, RecursionError):
        return None
    if s == sp.S.EmptySet:
        return []
    if isinstance(s, sp.FiniteSet) and all(p.is_real and p.is_finite for p in s):
        return sorted(s, key=str)
    return None


def _hasderiv_tactics(built, intro: list[str], guards: list[str]) -> tuple[str, ...]:
    """Tactics for a `HasDerivAt` goal. Returns () when the shape is out of the compiler's reach,
    which leaves the statement in place and the layer abstaining."""
    names = tuple(f"hg{i}" for i in range(len(guards)))
    block = _hasderiv_block(built, 2, names)
    if not block:
        return ()
    return ("\n".join(intro + block),)


def _forall_head(vn: str, guards: list[str]) -> tuple[str, list[str]]:
    head = f"∀ {vn} : ℝ, " + "".join(f"{g} → " for g in guards)
    intro = ["  intro " + " ".join([vn] + [f"hg{i}" for i in range(len(guards))])]
    return head, intro


def _t_derivative(obj, ns, ca, name) -> LeanStatement | None:
    """`f'(a) = v` and `f' = g` both become `HasDerivAt`, which asserts differentiability as well
    as the value — unlike `deriv f a = v`, which is vacuously true where `f` is not differentiable
    and would hand out a certificate for the wrong reason."""
    p = obj.task.params
    var = ns.get(p.get("var", "x"))
    if not isinstance(var, sp.Symbol) or ca["kind"] not in ("value", "expression"):
        return None
    t = sp.Symbol("t")
    f = parse_expr_str(p["f"], ns)
    if f.has(sp.Abs, sp.floor, sp.ceiling, sp.sign, sp.Piecewise) or (f.free_symbols - {var}):
        return None
    if any(s.name == "t" for s in f.free_symbols):
        return None
    f_t = f.subs(var, t)
    f_lean = sympy_to_lean(f_t, "ℝ")
    claimed = parse_structural(str(ca["payload"]), ns)
    if claimed is None or isinstance(claimed, sp.Set) or (claimed.free_symbols - {var}):
        return None
    sing = _real_singularities(f, var)
    if sing is None:
        return None
    at = p.get("at")
    if at not in (None, ""):
        pt = parse_structural(str(at), ns)
        if pt.free_symbols or claimed.free_symbols:
            return None
        if any(sp.simplify(s - pt) == 0 for s in sing):
            return None                                   # not differentiable there: out of scope
        # a singularity check is not a domain check: √x and log x have no singularity at −1,
        # yet in Lean `HasDerivAt Real.sqrt 0 (-1)` and `HasDerivAt Real.log (-1) (-1)` are TRUE
        # (both functions are totalised there). The point must be interior to the real domain.
        if not interior_defined_at(f, var, pt):
            return None
        pt_lean = f"({sympy_to_lean(pt, 'ℝ')})"
        goal = f"HasDerivAt (fun t : ℝ => {f_lean}) ({sympy_to_lean(claimed, 'ℝ')}) {pt_lean}"
        return LeanStatement(name, "", [], goal, "ℝ", "derivative_at",
                             hints=_hasderiv_tactics(_hasderiv_proof(f_t, t, pt, pt_lean),
                                                     [], []))
    vn = var.name
    # The ∀ below covers junk regions too (for √x, all of x < 0). That keeps the statement SOUND
    # for the real domain — Lean agrees with the reals at every interior point of it — as long
    # as the real domain is not empty; √(−x² − 1) is 0 everywhere in Lean and has derivative 0.
    if not has_interior_point([f], var):
        return None
    guards = [f"{vn} ≠ {sympy_to_lean(s, 'ℝ')}" for s in sing]
    head, intro = _forall_head(vn, guards)
    goal = head + f"HasDerivAt (fun t : ℝ => {f_lean}) ({sympy_to_lean(claimed, 'ℝ')}) {vn}"
    return LeanStatement(name, "", [], goal, "ℝ", "derivative_fun",
                         hints=_hasderiv_tactics(_hasderiv_proof(f_t, t, var, vn),
                                                 intro, guards))


_PLUS_C = re.compile(r"\s*[+]\s*[Cc]\s*$")


def _t_antiderivative(obj, ns, ca, name) -> LeanStatement | None:
    """"∫ f dx = F + C" says exactly that F' = f wherever both are defined, which is what the
    theorem asserts. The excluded points come from SymPy's singularity set of the two expressions,
    never from the claim, so a wrong claim cannot shrink the statement it has to satisfy."""
    p = obj.task.params
    var = ns.get(p.get("var", "x"))
    if not isinstance(var, sp.Symbol) or ca["kind"] not in ("expression", "value"):
        return None
    t = sp.Symbol("t")
    integrand = parse_expr_str(p["integrand"], ns)
    payload = _PLUS_C.sub("", strip_presentation(str(ca["payload"])))
    try:
        anti = parse_expr_str(payload, ns)
    except (ParseError, LeanPrintError):
        return None
    if anti is None or isinstance(anti, sp.Set):
        return None
    for expr in (integrand, anti):
        if expr.has(sp.Abs, sp.floor, sp.ceiling, sp.sign, sp.Piecewise) or (expr.free_symbols - {var}):
            return None
    if any(s.name == "t" for s in integrand.free_symbols | anti.free_symbols):
        return None
    sing_f, sing_F = _real_singularities(integrand, var), _real_singularities(anti, var)
    if sing_f is None or sing_F is None:
        return None
    if not has_interior_point([integrand, anti], var):
        return None                          # defined nowhere on ℝ: the ∀ would be all junk
    vn = var.name
    pts = sorted(set(sing_f + sing_F), key=str)       # exact points; no nsimplify snapping
    guards = [f"{vn} ≠ {sympy_to_lean(s, 'ℝ')}" for s in pts]
    head, intro = _forall_head(vn, guards)
    anti_lean = sympy_to_lean(anti.subs(var, t), "ℝ")
    goal = head + (f"HasDerivAt (fun t : ℝ => {anti_lean}) "
                   f"({sympy_to_lean(integrand, 'ℝ')}) {vn}")
    return LeanStatement(name, "", [], goal, "ℝ", "antiderivative_hasderiv",
                         hints=_hasderiv_tactics(_hasderiv_proof(anti.subs(var, t), t, var, vn),
                                                 intro, guards))


def _t_count_structures(obj, ns, ca, name) -> LeanStatement | None:
    """A counting claim is checked against Lean's *own* definition of the thing being counted —
    permutations of a finite type, k-element subsets, injections — not against our formula for it.
    That is the whole point: if we wrote `Nat.factorial 5 = 120` the theorem would only confirm
    our own choice of formula, which is the generating calculation, not a check of it."""
    p = obj.task.params
    if (p.get("predicate") or "").strip():
        return None                     # a filtered count needs the predicate translated as well
    if ca["kind"] != "count":
        return None
    try:
        claimed = int(ca["payload"])
    except (TypeError, ValueError):
        return None
    space = p.get("space") or {}
    structure = space.get("structure")
    n, k = space.get("n"), space.get("k")
    if n is None and isinstance(space.get("elements"), list):
        n = len(space["elements"])
    if not isinstance(n, int) or claimed < 0 or not (0 < n <= 20):
        return None
    if structure == "arrangement_all":
        return LeanStatement(name, "", [], f"Fintype.card (Equiv.Perm (Fin {n})) = {claimed}", "ℕ",
                             "count_arrangements",
                             hints=("  simp only [Fintype.card_perm, Fintype.card_fin]\n  decide",
                                    "  simp [Fintype.card_perm]\n  decide",
                                    "  norm_num [Fintype.card_perm, Nat.factorial]"))
    if not isinstance(k, int) or not (0 <= k <= n):
        return None
    if structure == "combination":
        return LeanStatement(name, "", [],
                             f"((Finset.univ : Finset (Fin {n})).powersetCard {k}).card = {claimed}",
                             "ℕ", "count_subsets",
                             hints=("  simp only [Finset.card_powersetCard, Finset.card_univ,"
                                    " Fintype.card_fin]\n  decide",
                                    "  simp [Finset.card_powersetCard, Nat.choose]", "  decide"))
    if structure == "permutation":
        return LeanStatement(name, "", [], f"Fintype.card (Fin {k} ↪ Fin {n}) = {claimed}", "ℕ",
                             "count_injections",
                             hints=("  simp [Fintype.card_embedding_eq]",
                                    "  simp only [Fintype.card_embedding_eq, Fintype.card_fin]\n"
                                    "  decide",
                                    "  norm_num [Fintype.card_embedding_eq, Nat.descFactorial]"))
    return None


def _rec_to_lean(expr, f, nvar, fname: str) -> str:
    """Render a recurrence right-hand side, where `f(n-k)` has no direct SymPy->Lean rendering.
    Each application is swapped for a placeholder symbol, the exact printer does the rest, and the
    placeholders are put back — so the term still goes through the printer that refuses to guess."""
    subs, back = {}, {}
    for app in sorted(expr.atoms(sp.core.function.AppliedUndef), key=str):
        if app.func is not f or len(app.args) != 1:
            raise LeanPrintError(f"unsupported application {app}")
        shift = sp.simplify(app.args[0] - nvar)
        if not shift.is_Integer or shift > 0:
            raise LeanPrintError(f"non-constant or forward index {app}")
        tag = sp.Symbol(f"RECPLACEHOLDER{abs(int(shift))}")
        subs[app] = tag
        back[tag.name] = f"{fname} {nvar.name}" if shift == 0 \
            else f"{fname} ({nvar.name} - {abs(int(shift))})"
    out = sympy_to_lean(expr.xreplace(subs), "ℝ")
    for tag_name, rendered in back.items():
        out = out.replace(tag_name, rendered)
    return out


def _t_recurrence_term(obj, ns, ca, name) -> LeanStatement | None:
    """"a(6) = 43 for a(n) = a(n-1) + 2a(n-2), a(1)=1, a(2)=3" becomes a theorem whose hypotheses
    are the recurrence and the initial terms. Lean does the iteration itself; we supply no value
    along the way, and the unused-hypothesis probe checks the data were actually needed."""
    p = obj.task.params
    fname, vname = p.get("name", "a"), p.get("var", "n")
    if not (fname.isidentifier() and fname.isalpha() and len(fname) <= 2):
        return None
    ns2 = dict(ns)
    f = sp.Function(fname)
    ns2[fname] = f
    nvar = ns2.get(vname)
    if not isinstance(nvar, sp.Symbol):
        nvar = sp.Symbol(vname, integer=True)
        ns2[vname] = nvar
    try:
        rel = parse_relation(p["recurrence"], ns2)
        initial = {int(sp.sympify(str(k))): parse_expr_str(str(v), ns2)
                   for k, v in (p.get("initial") or {}).items()}
        index = int(p["index"])
        claimed = parse_structural(str(ca["payload"]), ns2) if ca["kind"] in ("value", "expression") \
            else None
    except (ParseError, LeanPrintError, TypeError, ValueError, KeyError, sp.SympifyError):
        return None
    if not isinstance(rel, sp.Equality) or rel.lhs != f(nvar) or claimed is None:
        return None
    if claimed.free_symbols or not initial or any(v.free_symbols for v in initial.values()):
        return None
    start = max(initial) + 1
    if sorted(initial) != list(range(min(initial), start)) or min(initial) < 0:
        return None
    if not (start <= index <= start + 40) or rel.rhs.has(f(nvar)):
        return None
    # `a(n) = 1/a(n-1)` with a term that reaches 0: Lean iterates through 1/0 = 0 and proves a
    # value for a sequence that does not exist. A partial operation in the recurrence is out.
    if open_guards([rel.rhs], "ℝ"):
        return None
    try:
        rhs = _rec_to_lean(rel.rhs, f, nvar, fname)
        hyps = [f"{fname} {k} = {sympy_to_lean(v, 'ℝ')}" for k, v in sorted(initial.items())]
        hyps.append(f"∀ {vname} : ℕ, {start} ≤ {vname} → {fname} {vname} = {rhs}")
        goal = f"{fname} {index} = {sympy_to_lean(claimed, 'ℝ')}"
    except LeanPrintError:
        return None
    hn = f"h{len(hyps)}"                                   # the recurrence hypothesis
    steps = [f"  have e{k} := {hn} {k} (by norm_num)" for k in range(start, index + 1)]
    ev = " ".join(f"e{k}" for k in range(start, index + 1))
    facts = ", ".join([f"h{i}" for i in range(1, len(hyps))] + [f"e{k}" for k in range(start, index + 1)])
    hints = ("\n".join(steps + [f"  norm_num at {ev}", f"  linarith [{facts}]"]),
             "\n".join(steps + [f"  norm_num at {ev} ⊢", f"  linarith [{facts}]"]),
             "\n".join(steps + [f"  norm_num at {ev}", f"  nlinarith [{facts}]"]))
    return LeanStatement(name, f"({fname} : ℕ → ℝ)", hyps, goal, "ℝ", "recurrence_term",
                         hints=hints)


TEMPLATES: dict[str, Callable] = {
    "evaluate": _t_evaluate,
    "definite_integral": _t_definite_integral,
    "derivative": _t_derivative,
    "antiderivative": _t_antiderivative,
    "count_structures": _t_count_structures,
    "recurrence_term": _t_recurrence_term,
    "solve_equation": _t_solve_equation,
    "solve_inequality": _t_solve_inequality,
    "equation_of": _t_equation_of,
    "series_sum": _t_series_sum,
    "extremum": _t_extremum,
    "count_integers": _t_count_integers,
    "linalg": _t_linalg,
}


_TRIVIAL_SPLIT = " = "


def is_trivial(stmt: LeanStatement) -> bool:
    """A goal whose two sides are syntactically identical proves nothing about the problem —
    it means the CAS already did the work and Lean would only confirm reflexivity. Such a
    statement is rejected rather than counted as a formal certificate (handoff failure #6)."""
    g = stmt.goal.strip()
    if g.startswith("(") and g.endswith(")") and "∧" not in g and "∀" not in g:
        g = g[1:-1].strip()
    if "∀" in g or "↔" in g or "∧" in g or "∨" in g:
        return False
    if _TRIVIAL_SPLIT in g:
        lhs, _, rhs = g.partition(_TRIVIAL_SPLIT)
        norm = lambda s: s.strip().strip("()").replace(" ", "")   # noqa: E731
        return norm(lhs) == norm(rhs)
    return False


def build_statement(ir: dict[str, Any], claimed_answer: dict[str, Any], name: str = "mv_claim"
                    ) -> LeanStatement | None:
    """Deterministic statement for the claim, or None when the shape is out of F5 scope or the
    statement would be a tautology."""
    try:
        obj = load_problem_ir(ir)
        ns = build_namespace(obj)
    except Exception:
        return None
    # A claim that is a computation (`integrate(…)`) or the problem's own function applied
    # (`f(g(2))`) is not an answer; a proof about it would certify the question, not a claim.
    from ..normalize.parse import ClaimNotAValue, check_claim_is_value
    try:
        check_claim_is_value(claimed_answer.get("payload"), [f.name for f in obj.functions])
    except ClaimNotAValue:
        return None
    fn = TEMPLATES.get(obj.task.kind)
    if fn is None:
        return None
    try:
        st = fn(obj, ns, claimed_answer, name)
    except LeanPrintError:
        return None
    except Exception:
        return None
    if st is None or is_trivial(st):
        return None
    return st
