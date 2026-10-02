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
from ..sandbox.exactsets import exact_solveset
from ..normalize.parse import (ParseError, build_namespace, parse_relation, parse_expr_str,
                               parse_answer, parse_set_str, preclean, strip_presentation,
                               _TRANSFORMS)

__all__ = ["LeanStatement", "build_statement", "sympy_to_lean", "relation_to_lean", "LeanPrintError",
           "TEMPLATES", "structural_ns", "parse_structural", "AUTOIMPLICIT_OFF"]

# Every Lean command rendered for a statement (the theorem, the vacuity probe, the no-hypothesis
# probe) opens with this. Lean's default is autoImplicit ON: an unknown single-word identifier in a
# declaration header is silently bound as an implicit variable instead of being an error. Measured
# on 24 Sep (live Lean, reviewer's autoimplicit_verifier_probe.py): `(x : ℝ) (h1 : x - brokenk = 0)
# : x = brokenk` was proved by `linarith` and passed every audit (clean certificate), because
# `brokenk` became a universally quantified real. With the option off it is "Unknown identifier".
# harness/run_lean.py's elaboration check reuses this constant (ELAB_PREFIX).
AUTOIMPLICIT_OFF = "set_option autoImplicit false in\n"


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


def parse_structural(src: str, ns: dict[str, Any], strict: bool = False):
    """Parse without letting SymPy evaluate the arithmetic. Falls back to the normal parse when
    the unevaluated form cannot be built (the caller then gets a possibly-trivial statement,
    which the triviality guard rejects).

    strict=True: no fallback. The normal parse simplifies (`x/x` → 1, `sqrt(x)**2` → x) and so
    loses the points where the text is undefined (CLAUDE.md principle 12); a template that must
    read the expression AS WRITTEN gets a LeanPrintError instead and abstains."""
    from ..normalize.parse import guarded_parse_expr
    s = preclean(src)
    try:
        with sp.evaluate(False):
            return guarded_parse_expr(s, local_dict=structural_ns(ns), global_dict={},
                                      transformations=_TRANSFORMS, evaluate=False)
    except Exception as e:
        if strict:
            raise LeanPrintError(f"{src!r} cannot be read as written: {type(e).__name__}") from e
        return parse_expr_str(src, ns)


def parse_relation_structural(src: str, ns: dict[str, Any], strict: bool = False):
    from ..normalize.parse import _split_top_level, _REL_CLASS
    s = preclean(src)
    parts = _split_top_level(s)
    if len(parts) == 1:
        return parse_structural(src, ns, strict)
    exprs = [parse_structural(chunk, ns, strict) for _, chunk in parts]
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

def _safe_mod(node) -> bool:
    """The one `Mod` Lean states faithfully: an INTEGER dividend and a positive integer literal
    divisor d. Then SymPy's floored Mod and Lean's `Int.emod` are the same number in [0, d)."""
    a, d = node.args
    return isinstance(d, sp.Integer) and int(d) > 0 and a.is_integer is True


def _definedness(expr, var=None) -> list:
    """Definedness conditions of `expr`, EXACT or a LeanPrintError (the template abstains).

    * `Mod`/`%` is refused (audit 25 Sep 2026, C4) unless `_safe_mod`: Lean's ℤ `%` is Euclidean
      where SymPy's is floored (7 % -2: 1 vs -1), `x % 0 = x` in Lean, and ℝ `%` is Mathlib's
      EuclideanDomain remainder of a field, i.e. identically 0 — "Σ_{k=1}^{4} k mod 2 = 0" and
      "x mod 2 simplifies to 0" were certified. A safe Mod is printed in ℤ (`_print_lean`).
    * any operation whose real domain the rules do not describe (0**x, (-2)**x, factorial(x), …)
      is refused (`certify.domain.definedness_conditions_strict`, C9).
    * a matrix contributes the conditions of its entries."""
    from ..certify.domain import definedness_conditions_strict
    if isinstance(expr, (sp.MatrixBase, sp.MatrixExpr)) or any(
            isinstance(n, sp.MatrixBase) for n in sp.preorder_traversal(expr)):
        # matrix sums, products and natural powers are total: the entries decide
        out: list = []
        for node in sp.preorder_traversal(expr):
            if isinstance(node, sp.MatrixBase):
                for it in node:
                    out += [c for c in _definedness(it, var) if c not in out]
        return out
    mods = [n for n in sp.preorder_traversal(expr) if isinstance(n, sp.Mod)]
    back: dict = {}
    extra: list = []
    if mods:
        for m in mods:
            if not _safe_mod(m):
                raise LeanPrintError(f"Mod in {expr}: only an integer mod a positive literal is faithful")
        reps = {}
        for m in mods:
            dm = sp.Dummy(integer=True)
            reps[m], back[dm] = dm, m
            extra += [c for c in _definedness(m.args[0], var) if c not in extra]
        with sp.evaluate(False):
            expr = expr.xreplace(reps)                 # a safe Mod is total: its dividend decides
    conds = definedness_conditions_strict(expr, var)
    if conds is None:
        raise LeanPrintError(f"the real domain of {expr} is not known exactly")
    conds = [c.xreplace(back) if back and hasattr(c, "xreplace") else c for c in conds]
    return list(conds) + [c for c in extra if c not in conds]


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
        # guarded: SymPy reads a trigonometric relation on one period of ℝ (sandbox.exactsets), and the
        # violations of sin(x) >= 0 on [10, 12] were empty: a junk value would have been certified
        s = exact_solveset(bad, var, region)
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
        # only an integer mod a positive literal, computed in ℤ (Int.emod = SymPy's Mod there) and
        # cast: ℤ `%` is Euclidean in Lean (SymPy floors) and ℝ `%` is identically 0 (C4, 25 Sep)
        if not _safe_mod(e):
            raise LeanPrintError("Mod has no faithful Lean rendering here")
        txt = f"({_print_lean(e.args[0], 'ℤ')} % {int(e.args[1])} : ℤ)"
        return txt if field == "ℤ" else f"({txt} : {field})"
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
            lhs = sympy_to_lean(rel.lhs, field)
            if _closed_scalar(rel.lhs) and _closed_scalar(rel.rhs):
                # a relation between closed numbers has no variable to fix its type: Lean then
                # reads the literals in ℕ, where 7 / 2 = 3 and 1 / 2 = 0 (C3, 25 Sep 2026)
                lhs = f"({lhs} : {field})"
            return f"{lhs} {op} {sympy_to_lean(rel.rhs, field)}"
    if isinstance(rel, sp.And):
        return " ∧ ".join(f"({relation_to_lean(a, field)})" for a in rel.args)
    if isinstance(rel, sp.Or):
        return " ∨ ".join(f"({relation_to_lean(a, field)})" for a in rel.args)
    if isinstance(rel, sp.Not):
        return f"¬({relation_to_lean(rel.args[0], field)})"
    raise LeanPrintError(f"cannot print relation {rel}")


def _closed_scalar(e) -> bool:
    e = sp.sympify(e)
    return not isinstance(e, (sp.MatrixBase, sp.MatrixExpr)) and not e.free_symbols


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
    # Satisfiability of the hypotheses (audit 25 Sep 2026, C6): a vacuity probe can only show that
    # hypotheses ARE contradictory, and a stronger proof search (the ladder's nlinarith hints, a
    # model-written proof) found contradictions it did not — "a + b = 42 from a² + b² < 2ab" was
    # certified. So a statement with hypotheses needs a POSITIVE proof that they can hold: a point
    # (`witness`, one value per `sat_vars` binder) that the template found and checked exactly,
    # which Lean checks again in the audit (`sat_probe`). `sat_by_construction`: the hypotheses
    # define the object (a recurrence with its initial terms), so they hold for the one it defines.
    sat_vars: tuple[str, ...] = ()
    witness: tuple[str, ...] | None = None
    sat_by_construction: bool = False

    def theorem(self, proof: str) -> str:
        """The Lean command that proves the statement with `proof`, autoImplicit off
        (AUTOIMPLICIT_OFF), as are both audit probes below."""
        hs = " ".join(f"(h{i} : {h})" for i, h in enumerate(self.hypotheses, start=1))
        head = " ".join(x for x in [f"theorem {self.name}", self.binders, hs] if x)
        return f"{AUTOIMPLICIT_OFF}{head} : {self.goal} := by\n{proof}"

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
        # `simp_all` behind it. docs/arsiv/HANDOFF-2026-09-26.md §4 records the same trap for the
        # proof ladders; the probe had been left in the old form since F5.
        closers = ["linarith", "nlinarith", "simp at *; linarith", "norm_num at *; linarith",
                   "field_simp at *; linarith", "simp at *; nlinarith"]
        inner = "first | " + " | ".join(f"({c}; done)" for c in closers)
        # the generic proof ladder (prove.TACTIC_LADDER) is in here too, hint sets included: the
        # probe must not be weaker than the search (25 Sep 2026: `nlinarith [sq_nonneg (a - b), …]`
        # proved a goal from a² + b² < 2ab and the probe missed the contradiction). The positive
        # satisfiability proof (sat_probe) is what closes the gap for stronger searches.
        alts = ["omega", "linarith", "nlinarith", "norm_num at *", "simp_all",
                "simp_all; linarith", "simp_all; nlinarith", "norm_num at *; linarith",
                "simp at *; linarith", "field_simp at *; linarith", "field_simp at *; nlinarith",
                "nlinarith [sq_nonneg (a - b), sq_nonneg (a + b)]", "norm_num", "decide"]
        alts += [f"exact h{i} (by {inner})" for i, h in enumerate(self.hypotheses, start=1)
                 if " ≠ " in h and "∀" not in h and "∃" not in h]
        return f"{AUTOIMPLICIT_OFF}{head} : False := by\n  first | " + " | ".join(f"({a}; done)" for a in alts)

    def sat_probe(self) -> str | None:
        """`∃ binders, h1 ∧ … ∧ hn`, proved at the template's witness. None when there is nothing
        to prove it with (no witness): the audit then refuses the certificate."""
        if not self.hypotheses or self.witness is None or len(self.witness) != len(self.sat_vars):
            return None
        body = " ∧ ".join(f"({h})" for h in self.hypotheses)
        n = len(self.hypotheses)
        each = "first | " + " | ".join(f"({c}; done)" for c in (
            "norm_num", "simp", "positivity", "norm_num [Real.sqrt_eq_iff_mul_self_eq]", "nlinarith"))
        split = "" if n == 1 else "refine ⟨" + ", ".join(["?_"] * n) + "⟩ <;> "
        close = f"first | (norm_num; done) | ({split}({each}); done)"
        if not self.sat_vars:
            return f"{AUTOIMPLICIT_OFF}theorem {self.name}_sat : {body} := by\n  {close}"
        head = f"theorem {self.name}_sat : ∃ {' '.join(self.sat_vars)} : {self.field}, {body} := by"
        return (f"{AUTOIMPLICIT_OFF}{head}\n  refine ⟨{', '.join(self.witness)}, ?_⟩\n  {close}")

    def no_hyp_probe(self, proof: str) -> str | None:
        """Same goal without the hypotheses: if it still proves, the data were never used."""
        if not self.hypotheses:
            return None
        head = " ".join(x for x in [f"theorem {self.name}_nohyp", self.binders] if x)
        return f"{AUTOIMPLICIT_OFF}{head} : {self.goal} := by\n{proof}"


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


# ---------------------------------------------------------------------------- faithfulness
# The formal-layer audit of 25 Sep 2026 had 53 of 98 wrong claims certified. Apart from the junk
# values above, three causes, each closed here by stating what the problem SAYS or refusing:
#   * restrictions dropped (C2): var constraints, domain_of_discourse, every given but the first,
#     and complex/rational domains never reached the statement — "2x = 4 with x > 5 has the
#     root 2" and "x² = −1 over ℂ has no root" were certified;
#   * the simplifying parse (C1, CLAUDE.md principle 12): `x**2/x = 0` reached Lean as `x = 0`,
#     `exp(log x)` as `x`, `k/k` as `1`, so the points where the problem is undefined vanished;
#   * the claim rewritten before comparison (principle 3): `y = x**2/x` became `y = x`.
_INT_DOMAINS = frozenset({"integer", "positive_integer", "nonneg_integer", "natural"})
_UNSUPPORTED_DOMAINS = frozenset({"complex", "rational"})
# the same conditions as _DOMAIN_COND, as unevaluated relations (a positive symbol would fold
# `0 < x` to True if it were parsed)
_DOMAIN_REL = {
    "positive_real": lambda s: sp.StrictLessThan(0, s, evaluate=False),
    "nonneg_real": lambda s: sp.LessThan(0, s, evaluate=False),
    "positive_integer": lambda s: sp.StrictLessThan(0, s, evaluate=False),
    "nonneg_integer": lambda s: sp.LessThan(0, s, evaluate=False),
    "natural": lambda s: sp.StrictLessThan(0, s, evaluate=False),
}


def _as_written(src, ns) -> list:
    """The sides of an IR text exactly as written (no automatic simplification), or a refusal."""
    from ..normalize.parse import parse_as_written
    if not isinstance(src, str):
        raise LeanPrintError("a problem expression that is not text cannot be read as written")
    w = parse_as_written(src, ns)
    if w is None:
        raise LeanPrintError(f"{src!r} cannot be read as written")
    return list(w)


def _latex_written(s: str, ns) -> Any:
    """A LaTeX text AS WRITTEN (latex2sympy with evaluation off), its symbols rebound to the
    problem's; a refusal for anything undeclared or unreadable."""
    from latex2sympy2_extended import latex2sympy
    from ..normalize.parse import is_latex
    if not is_latex(s):
        raise LeanPrintError(f"{s!r} is not LaTeX")
    try:
        with sp.evaluate(False):
            e = latex2sympy(s)
    except Exception as ex:  # noqa: BLE001
        raise LeanPrintError(f"LaTeX {s!r} cannot be read as written") from ex
    if not isinstance(e, sp.Basic):
        raise LeanPrintError(f"LaTeX {s!r} is not an expression")
    reps = {}
    for fs in e.free_symbols:
        tgt = ns.get(fs.name)
        if not isinstance(tgt, sp.Symbol):
            raise LeanPrintError(f"LaTeX {s!r} uses the undeclared symbol {fs}")
        reps[fs] = tgt
    with sp.evaluate(False):
        return e.xreplace(reps)


def _parse_written(src, ns) -> Any:
    """A claim or problem value AS WRITTEN: the structural parse, or the LaTeX reader."""
    try:
        return parse_structural(str(src), ns, strict=True)
    except LeanPrintError:
        return _latex_written(strip_presentation(str(src)), ns)


def _written_conds(srcs, ns, var=None) -> list:
    """Open definedness conditions of IR texts AS WRITTEN. A closed one that fails refuses."""
    out: list = []
    for s in srcs:
        for side in _as_written(s, ns):
            for c in _definedness(side, var):
                if not getattr(c, "free_symbols", None):
                    if _closed_truth(c) is not True:
                        raise LeanPrintError(f"{s!r} is undefined as written ({c})")
                    continue
                if c not in out:
                    out.append(c)
    return out


def _open(conds) -> list:
    return [c for c in conds if getattr(c, "free_symbols", None)]


def _solve_region(conds, var) -> sp.Set:
    """Where all the conditions hold (one variable), or a refusal when SymPy cannot say."""
    region: sp.Set = S.Reals
    for c in conds:
        if c is sp.true:
            continue
        if c is sp.false:
            return S.EmptySet
        if c.free_symbols - {var}:
            raise LeanPrintError(f"condition {c} is not in {var} alone")
        try:
            s = exact_solveset(c, var, S.Reals)        # one period is no region (sandbox.exactsets)
        except (NotImplementedError, TypeError, ValueError, AttributeError, RecursionError) as e:
            raise LeanPrintError(f"cannot solve {c}") from e
        if isinstance(s, (sp.ConditionSet, sp.ImageSet)) or s.has(sp.ConditionSet):
            raise LeanPrintError(f"cannot solve {c}")
        region = sp.Intersection(region, s)
    return region


def _merge_written(parsed, written, var) -> list:
    """Guards for a one-variable statement whose relation went through the simplifying parse: the
    parsed form's own conditions plus every as-written condition they do not already imply.
    Refuses when the simplified form is undefined somewhere the written one is defined (its Lean
    junk values would then be inside the region the statement is about), or when undecidable."""
    parsed, written = _open(parsed), _open(written)
    dw = _solve_region(written, var)
    for c in parsed:
        bad = _violation_set(c, var, dw)
        if bad is None or bad != S.EmptySet:
            raise LeanPrintError(f"the simplified form needs {c} where the written one is defined")
    out = list(parsed)
    dp = _solve_region(parsed, var)
    for c in written:
        if c in out:
            continue
        if dp.is_subset(_solve_region([c], var)) is True:
            continue                                  # already implied by the parsed guards
        out.append(c)
    return out


def _interior(conds) -> list:
    """The open version of each condition (≥ → >, ≤ → <): where a derivative can exist."""
    out: list = []
    for c in conds:
        if isinstance(c, sp.GreaterThan):
            c = sp.StrictGreaterThan(c.lhs, c.rhs, evaluate=False)
        elif isinstance(c, sp.LessThan):
            c = sp.StrictLessThan(c.lhs, c.rhs, evaluate=False)
        if c not in out:
            out.append(c)
    return out


def _set_relation(s: sp.Set, var):
    """A domain of discourse as a relation in `var` (a union of intervals or a finite set)."""
    if s == S.Reals:
        return sp.true
    if isinstance(s, sp.Interval):
        parts = []
        if s.inf != -sp.oo:
            parts.append((sp.StrictGreaterThan if s.left_open else sp.GreaterThan)(var, s.inf, evaluate=False))
        if s.sup != sp.oo:
            parts.append((sp.StrictLessThan if s.right_open else sp.LessThan)(var, s.sup, evaluate=False))
        return parts[0] if len(parts) == 1 else sp.And(*parts)
    if isinstance(s, sp.Union):
        return sp.Or(*[_set_relation(a, var) for a in s.args])
    if isinstance(s, sp.FiniteSet) and s.args:
        return sp.Or(*[sp.Eq(var, e, evaluate=False) for e in s.args])
    raise LeanPrintError(f"domain of discourse {s} is not a union of intervals")


def _var_restrictions(obj, ns, var, field: str, main_src: str, main_rel) -> tuple[list, list]:
    """Every condition the problem puts on `var` besides the relation the template states: its
    declared domain, its constraints, every OTHER given and the domain of discourse, with the
    source texts (for the as-written check). Refuses what it cannot state: a constraint or a given
    in another variable, a domain of discourse that is not a union of intervals, or a variable
    whose integrality differs from the statement's field."""
    from ..normalize.parse import parse_domain
    vd = next((v for v in obj.vars if v.name == var.name), None)
    dom = vd.domain if vd is not None else "real"
    if (dom in _INT_DOMAINS) != (field == "ℤ"):
        raise LeanPrintError(f"{var} is {dom} but the statement quantifies over {field}")
    if any(v.constraints for v in obj.vars if v.name != var.name):
        raise LeanPrintError("a constraint on another variable")
    conds: list = []
    srcs: list = []
    mk = _DOMAIN_REL.get(dom)
    if mk:
        conds.append(mk(var))
    others = [g for g in obj.givens if g.strip() != str(main_src).strip()]
    for src in list(vd.constraints if vd is not None else []) + others:
        r = parse_relation(src, ns)
        srcs.append(src)
        if r is sp.true or r == main_rel:
            continue
        if r is not sp.false and getattr(r, "free_symbols", set()) - {var}:
            raise LeanPrintError(f"{src!r} is not a condition on {var} alone")
        conds.append(r)
    if obj.domain_of_discourse:
        if len(obj.vars) > 1:
            raise LeanPrintError("domain of discourse with several variables")
        r = _set_relation(parse_domain(obj.domain_of_discourse, var, ns), var)
        if r is not sp.true:
            conds.append(r)
    return conds, srcs


def _dedupe(rels, field: str) -> list:
    out, seen = [], set()
    for r in rels:
        t = relation_to_lean(r, field)
        if t not in seen:
            seen.add(t)
            out.append(r)
    return out


def _guard_rels(exprs, var=None) -> list:
    """The open definedness conditions of `exprs`, as relations (closed ones: the printer)."""
    out: list = []
    for e in exprs:
        for c in _definedness(e, var):
            if getattr(c, "free_symbols", None) and c not in out:
                out.append(c)
    return out


def _exact_truth(rel) -> bool | None:
    """Truth of a CLOSED relation, decided exactly (no numeric tolerance): None when SymPy cannot
    decide it. A side that is not a real number makes the relation false (it is about ℝ)."""
    if rel is sp.true or rel is True:
        return True
    if rel is sp.false or rel is False:
        return False
    if isinstance(rel, (sp.And, sp.Or)):
        parts = [_exact_truth(a) for a in rel.args]
        if isinstance(rel, sp.And):
            return False if False in parts else (True if all(p is True for p in parts) else None)
        return True if True in parts else (False if all(p is False for p in parts) else None)
    if not isinstance(rel, sp.core.relational.Relational) or rel.free_symbols:
        return None
    try:
        lhs, rhs = sp.simplify(rel.lhs), sp.simplify(rel.rhs)
        for v in (lhs, rhs):
            if v.has(sp.nan, sp.zoo, sp.oo, -sp.oo):
                return False
            if v.is_extended_real is not True:
                return False if v.is_extended_real is False else None
        d = sp.simplify(lhs - rhs)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(rel, sp.Equality):
        return True if d == 0 else (False if d.is_zero is False else None)
    if isinstance(rel, sp.Unequality):
        return False if d == 0 else (True if d.is_zero is False else None)
    if isinstance(rel, sp.StrictGreaterThan):
        return d.is_positive
    if isinstance(rel, sp.GreaterThan):
        return d.is_nonnegative
    if isinstance(rel, sp.StrictLessThan):
        return d.is_negative
    if isinstance(rel, sp.LessThan):
        return d.is_nonpositive
    return None


def _subst(rel, assign: dict):
    """Put the witness into a relation WITHOUT letting SymPy decide it on the way."""
    if isinstance(rel, (sp.And, sp.Or)):
        return rel.func(*[_subst(a, assign) for a in rel.args])
    if isinstance(rel, sp.core.relational.Relational):
        with sp.evaluate(False):
            lhs, rhs = rel.lhs.xreplace(assign), rel.rhs.xreplace(assign)
        return rel.func(lhs, rhs, evaluate=False)
    return rel.xreplace(assign)


_WITNESS_GRID = (sp.Integer(0), sp.Integer(1), sp.Integer(2), sp.Integer(-1), sp.Rational(1, 2),
                 sp.Integer(3), sp.Integer(-2), sp.Integer(5), sp.Rational(-1, 2), sp.Integer(10))
# integer unknowns (a Diophantine given leaves one free): 0, ±1, ±2, …, ±40
_WITNESS_GRID_Z = tuple(sp.Integer(s * k) for k in range(41) for s in ((1,) if k == 0 else (1, -1)))


def _find_witness(obj, ns, syms, hyp_rels, field: str) -> list | None:
    """A point where EVERY hypothesis holds, checked exactly on the hypotheses as written
    (definedness guards included). SymPy proposes candidates — the solutions of the given
    equations, then a small grid for whatever they leave free — and only proposes: the audit has
    Lean prove `∃ …, hypotheses` at the point again. None when no candidate passes."""
    from ..sandbox import run as sb_run
    eqs = []
    for src in list(obj.givens) + [c for v in obj.vars for c in v.constraints]:
        try:
            r = parse_relation(src, ns)
        except Exception:  # noqa: BLE001
            return None
        if r is sp.false:
            return None
        if isinstance(r, sp.Equality):
            eqs.append(r)
    cands: list = [{}]
    if eqs:
        res = sb_run("mathverify.sandbox.ops:solve_system", eqs, list(syms), timeout=10.0)
        if not res.ok or not isinstance(res.value, list):
            return None
        cands = [d for d in res.value if isinstance(d, dict)][:12]
    for cand in cands:
        vals = {s: sp.sympify(cand.get(s, s)) for s in syms}
        free = sorted({f for v in vals.values() for f in v.free_symbols}, key=str)
        if set(free) - set(syms):
            continue
        tried = 0
        grid = _WITNESS_GRID_Z if field == "ℤ" else _WITNESS_GRID
        for combo in __import__("itertools").product(grid, repeat=len(free)):
            tried += 1
            if tried > 1500:
                break
            sub = dict(zip(free, combo))
            assign = {s: vals[s].xreplace(sub) for s in syms}
            if any((not v.is_Integer) if field == "ℤ" else (v.is_extended_real is not True or not v.is_finite)
                   for v in assign.values()):
                continue
            if all(_exact_truth(_subst(r, assign)) is True for r in hyp_rels):
                return [assign[s] for s in syms]
    return None


# ---------------------------------------------------------------------------- templates
def _t_evaluate(obj, ns, ca, name) -> LeanStatement | None:
    p = obj.task.params
    field = _field_for(obj)
    if field == "ℝ" and any(v.domain in _INT_DOMAINS for v in obj.vars):
        return None          # an integer unknown in a real binder: ℝ-solvable is not ℤ-solvable
    expr_src = p.get("expr") or obj.unknown_of_interest
    if not expr_src:
        return None
    # target, givens, constraints and claim are all read AS WRITTEN (principles 3 and 12)
    target = parse_structural(expr_src, ns, strict=True)
    claimed = _parse_written(ca["payload"], ns) if ca["kind"] in ("value", "expression") \
        else parse_answer(ca["kind"], ca["payload"], ns)
    if isinstance(claimed, sp.Set) or claimed is None:
        return None
    matrix = isinstance(target, sp.MatrixBase) or isinstance(claimed, sp.MatrixBase)
    if matrix:
        field = "ℝ"
    elif claimed.free_symbols and (obj.givens or obj.answer_shape != "expression"):
        # "evaluate a given a + b = 10": `10 - b` restates a given, it is not a value (audit E04)
        return None
    given_rels = [parse_relation_structural(g, ns, strict=True) for g in obj.givens]
    cons_rels = [parse_relation_structural(c, ns, strict=True) for v in obj.vars for c in v.constraints]
    rels = list(given_rels)
    for v in obj.vars:
        mk = _DOMAIN_REL.get(v.domain)
        if mk:
            rels.append(mk(ns[v.name]))
    rels += cons_rels
    # Junk values (see the section at the top): a claim whose value depends on where a variable
    # sits is out of scope, and every open partial operation in the givens or the target becomes
    # a guard hypothesis. Without the guard, `1/(x-2) = 0` is satisfied by x = 2 in Lean, so
    # "evaluate x" would be proved = 2 for a system that has no solution at all; with it, the
    # hypotheses are contradictory and no witness exists (sat_probe), nor passes the vacuity probe.
    if not matrix and open_guards([claimed], field):
        return None
    if not matrix:
        rels += _guard_rels(given_rels + cons_rels + [target])
    hyp_rels = _dedupe(rels, field)
    hyps = [relation_to_lean(r, field) for r in hyp_rels]
    tgt_txt, cl_txt = sympy_to_lean(target, field), sympy_to_lean(claimed, field)
    if tgt_txt == cl_txt:
        return None
    # a closed target has no variable to fix its type: Lean would read `7 / 2 = 3` in ℕ (C3)
    goal = f"({tgt_txt} : {field}) = {cl_txt}" if (not matrix and not target.free_symbols) \
        else f"{tgt_txt} = {cl_txt}"
    binders = f"({' '.join(v.name for v in obj.vars)} : {field})" if obj.vars else ""
    kind = "closed_arithmetic" if (not obj.vars and not hyps) else "evaluate_system"
    witness = None
    if hyps:
        w = _find_witness(obj, ns, [ns[v.name] for v in obj.vars], hyp_rels, field)
        if w is not None:
            try:
                witness = tuple(sympy_to_lean(val, field) for val in w)
            except LeanPrintError:
                witness = None
    hints: list[str] = []
    # `Real.sqrt X = v` needs the square witness; the template knows both sides
    if tgt_txt.startswith("Real.sqrt ") and not target.free_symbols:
        inner = tgt_txt[len("Real.sqrt "):]
        hints.append(f"  rw [show {inner} = {cl_txt} ^ 2 by norm_num,\n"
                     f"     Real.sqrt_sq (by norm_num : (0:ℝ) ≤ {cl_txt})]")
    hints += _trig_hints(target, field)
    return LeanStatement(name, binders, hyps, goal, field, kind, hints=tuple(hints),
                         sat_vars=tuple(v.name for v in obj.vars), witness=witness)


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
    if any(getattr(r, "free_symbols", None) for r in roots):
        return None                             # a "root" in the unknown itself is not a value
    # every restriction of the problem is a guard of the iff AND a condition each root must meet
    restr, rsrcs = _var_restrictions(obj, ns, var, field, eq_src, rel)
    parsed_defs = [c for r in [rel] + restr for c in _definedness(r, var)]
    defs = _merge_written(parsed_defs, _written_conds([eq_src] + rsrcs, ns, var), var)
    conds = _dedupe(restr + defs, field)
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
    p = obj.task.params
    field = _field_for(obj)
    var = ns.get(p.get("var", "x"))
    if not isinstance(var, sp.Symbol):
        return None
    src = p.get("inequality") or (obj.givens[0] if obj.givens else None)
    if not src:
        return None
    rel = parse_relation(src, ns)
    claimed = parse_answer("set" if ca["kind"] in ("set", "interval") else "set", ca["payload"], ns)
    if not isinstance(claimed, sp.Set) or claimed.free_symbols:
        return None
    # every other given, the variable's domain and constraints and the domain of discourse are
    # conditions of the solution set too (audit 25 Sep 2026: all four were dropped)
    restr, rsrcs = _var_restrictions(obj, ns, var, field, src, rel)
    parsed_defs = [c for r in [rel] + restr for c in _definedness(r, var)]
    defs = _merge_written(parsed_defs, _written_conds([src] + rsrcs, ns, var), var)
    conds = _dedupe(restr + defs, field)
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
    # domain, so the iff would be about points that are not on either curve. Out of scope — and
    # that is decided on the claim AS WRITTEN: `y = x**2/x` parses to `y = x` and was certified
    # as the line through the origin, which it misses (audit 25 Sep 2026).
    if open_guards([claimed, truth], "ℝ"):
        return None
    if not isinstance(ca["payload"], str) or _written_conds([ca["payload"]], ns):
        return None
    goal = (f"∀ {x.name} {y.name} : ℝ, (({relation_to_lean(claimed, 'ℝ')}) ↔ "
            f"({relation_to_lean(truth, 'ℝ')}))")
    return LeanStatement(name, "", [], goal, "ℝ", "equation_of_iff")


def _t_series_sum(obj, ns, ca, name) -> LeanStatement | None:
    p = obj.task.params
    if not isinstance(ns.get(p.get("var", "k")), sp.Symbol):
        return None
    # the index runs over [lo, hi] (an integer and nothing more, as in certify.series): with k
    # declared positive, Abs(k) folded to k and "∑_{k=-2}^{2} k = 0" was stated for the wrong claim 0
    # (audit of 29 Sep 2026)
    var = sp.Symbol(p.get("var", "k"), integer=True)
    ns = dict(ns, **{var.name: var})
    lo = parse_expr_str(str(p.get("lo", "1")), ns)
    hi = parse_expr_str(str(p.get("hi", "oo")), ns)
    if hi == sp.oo or lo == -sp.oo or not (lo.is_Integer and hi.is_Integer):
        return None                                   # only finite sums are exactly expressible
    if int(hi) - int(lo) > 200 or int(hi) < int(lo) - 1:
        return None                                   # reversed bounds: no convention (certify.series)
    term = parse_expr_str(p["term"], ns)
    claimed = parse_answer(ca["kind"], ca["payload"], ns)
    if isinstance(claimed, sp.Set) or claimed is None:
        return None
    # every summand must be defined: ∑_{k=-1}^{1} 1/k is undefined, but Lean adds −1 + 0 + 1 = 0;
    # and defined AS WRITTEN: the normal parse folds k/k to 1 (audit 25 Sep 2026: "Σ k/k = 3")
    for e in [term] + _as_written(p["term"], ns):
        for c in _definedness(e, var):
            for k in range(int(lo), int(hi) + 1):
                cc = c.subs(var, k) if getattr(c, "free_symbols", None) else c
                if _closed_truth(cc) is not True:
                    return None
    # the ∑ binds the index over ℤ: say so, so that an integer-only operation (a safe Mod) prints
    term_z = term.subs(var, sp.Symbol(var.name, integer=True))
    field = "ℤ" if (term.is_polynomial(var) and all(c.is_Integer for c in sp.Poly(term, var).coeffs())
                    and claimed.is_Integer) else "ℝ"
    if field == "ℝ" and claimed.is_Integer and term_z.is_integer is True:
        # an integer-valued summand (k mod 2) sums to the same number in ℤ, where `decide` works
        try:
            sympy_to_lean(term_z, "ℤ")
            field = "ℤ"
        except LeanPrintError:
            pass
    body = sympy_to_lean(term_z, field)
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
    # ... and so must f AS WRITTEN: `x/x − x²` parses to 1 − x², whose maximum 1 at x = 0 is a
    # point where the problem's f does not exist (audit 25 Sep 2026)
    if not all(defined_on(w, var, iv) for w in _as_written(p["f"], ns)):
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
    if any(v.name != var.name for v in obj.vars):
        return None                         # another unknown: the count would be of pairs
    vd = next((v for v in obj.vars if v.name == var.name), None)
    cons = list(vd.constraints) if vd is not None else []
    rels = [parse_relation(g, ns) for g in list(obj.givens) + cons]
    if open_guards(rels, "ℤ"):
        return None                         # a partial operation in the predicate: junk-prone
    if _written_conds(list(obj.givens) + cons, ns, var):
        return None                         # ... also one the normal parse folded away (x/x)
    # the declared domain restricts what is counted (audit 25 Sep 2026: "positive x with x² < 10"
    # was counted over all of ℤ)
    mk = _DOMAIN_REL.get(vd.domain if vd is not None else "real")
    if mk:
        rels.append(mk(var))
    from ..equiv import exact_integer
    n = exact_integer(ca["payload"])     # never int(): a claimed 3.5 would become a proof of 3
    if n is None:
        return None
    # the box only has to CONTAIN the solutions (Lean proves that below), so it is cut from the
    # relations solveset can solve (one at a time: an And of several was a ValueError, i.e. no
    # statement at all); one it cannot (`Mod(x, 2) = 0`) only filters inside the box
    sol: sp.Set = S.Reals
    for r in rels:
        try:
            sol = sp.Intersection(sol, _solve_region([r], var))
        except LeanPrintError:
            continue
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
        T = parse_structural(p["expr"], ns, strict=True)   # keep the power/product unevaluated
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
    a = parse_structural(str(p["a"]), ns, strict=True)
    b = parse_structural(str(p["b"]), ns, strict=True)
    claimed = _parse_written(ca["payload"], ns) if ca["kind"] in ("value", "expression") \
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
    # as written, too: `exp(log(x))` parses to x, and "∫_{-2}^{-1} exp(log x) dx = −3/2" was
    # certified for an integrand that is nowhere real on the interval (audit 25 Sep 2026)
    if not all(defined_on(w, var, sp.Interval(lo, hi)) for w in _as_written(p["integrand"], ns)):
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
    # f AS WRITTEN decides where it exists: `sqrt(x)**2` parses to x, and "its derivative at −1
    # is 1" was certified (audit 25 Sep 2026)
    f_w = _as_written(p["f"], ns)
    if len(f_w) != 1:
        return None
    f_w = f_w[0]
    f_t = f.subs(var, t)
    f_lean = sympy_to_lean(f_t, "ℝ")
    claimed = _parse_written(ca["payload"], ns)
    if claimed is None or isinstance(claimed, sp.Set) or (claimed.free_symbols - {var}):
        return None
    sing = _real_singularities(f, var)
    if sing is None:
        return None
    at = p.get("at")
    if at not in (None, ""):
        pt = parse_structural(str(at), ns, strict=True)
        if pt.free_symbols or claimed.free_symbols:
            return None
        if any(sp.simplify(s - pt) == 0 for s in sing):
            return None                                   # not differentiable there: out of scope
        # a singularity check is not a domain check: √x and log x have no singularity at −1,
        # yet in Lean `HasDerivAt Real.sqrt 0 (-1)` and `HasDerivAt Real.log (-1) (-1)` are TRUE
        # (both functions are totalised there). The point must be interior to the real domain.
        if not interior_defined_at(f, var, pt) or not interior_defined_at(f_w, var, pt):
            return None
        # typed: an untyped `(2)` in the hint `hasDerivAt_id' (2)` elaborated in ℕ
        pt_lean = f"({sympy_to_lean(pt, 'ℝ')} : ℝ)"
        goal = f"HasDerivAt (fun t : ℝ => {f_lean}) ({sympy_to_lean(claimed, 'ℝ')}) {pt_lean}"
        return LeanStatement(name, "", [], goal, "ℝ", "derivative_at",
                             hints=_hasderiv_tactics(_hasderiv_proof(f_t, t, pt, pt_lean),
                                                     [], []))
    vn = var.name
    if not has_interior_point([f, f_w], var):
        return None
    # The ∀ ranges over the INTERIOR of f's real domain (as written and as parsed), minus its
    # poles: there Lean's f is the real f, and nowhere else is the derivative a question. The
    # claimed derivative must be defined on all of it, or the statement is about its junk values.
    dom_conds = _interior(_open(_definedness(f_w, var) + _definedness(f, var)))
    region = sp.Complement(_solve_region(dom_conds, var), sp.FiniteSet(*sing))
    for c in _open(_definedness(claimed, var)):
        bad = _violation_set(c, var, region)
        if bad is None or bad != S.EmptySet:
            return None
    guards: list[str] = []
    for g in [f"{vn} ≠ {sympy_to_lean(s, 'ℝ')}" for s in sing] + [relation_to_lean(c, "ℝ") for c in dom_conds]:
        if g not in guards:
            guards.append(g)
    head, intro = _forall_head(vn, guards)
    goal = head + f"HasDerivAt (fun t : ℝ => {f_lean}) ({sympy_to_lean(claimed, 'ℝ')}) {vn}"
    return LeanStatement(name, "", [], goal, "ℝ", "derivative_fun",
                         hints=_hasderiv_tactics(_hasderiv_proof(f_t, t, var, vn),
                                                 intro, guards))


_PLUS_C = re.compile(r"\s*[+]\s*[Cc]\s*$")


def _t_antiderivative(obj, ns, ca, name) -> LeanStatement | None:
    """"∫ f dx = F + C" says exactly that F' = f on the domain of f, which is what the theorem
    asserts. The region comes from the INTEGRAND (as written and as parsed), never from the claim,
    so a wrong claim cannot shrink the statement it has to satisfy; and the claim must be defined
    on ALL of that region (audit 25 Sep 2026, C8): Lean's `Real.log t` is log|t|, so
    "∫ dx/x = ln x + C" was certified although ln x does not exist for x < 0."""
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
    f_w, F_w = _as_written(p["integrand"], ns), _as_written(payload, ns)
    if len(f_w) != 1 or len(F_w) != 1:
        return None
    sing_f, sing_F = _real_singularities(integrand, var), _real_singularities(anti, var)
    if sing_f is None or sing_F is None:
        return None
    if not has_interior_point([integrand, f_w[0]], var):
        return None                          # defined nowhere on ℝ: the ∀ would be all junk
    vn = var.name
    dom_conds = _interior(_open(_definedness(f_w[0], var) + _definedness(integrand, var)))
    region = sp.Complement(_solve_region(dom_conds, var), sp.FiniteSet(*sing_f))
    for c in _open(_definedness(F_w[0], var) + _definedness(anti, var)):
        bad = _violation_set(c, var, region)
        if bad is None or bad != S.EmptySet:
            return None                      # the claim is undefined where the integrand is not
    if any(region.contains(s) is not sp.false for s in sing_F):
        return None                          # a pole of the claim inside the integrand's domain
    guards: list[str] = []
    for g in [f"{vn} ≠ {sympy_to_lean(s, 'ℝ')}" for s in sing_f] + [relation_to_lean(c, "ℝ") for c in dom_conds]:
        if g not in guards:
            guards.append(g)
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
    from ..equiv import exact_integer
    claimed = exact_integer(ca["payload"])    # never int(): 6.5 became a proof of 6 (audit 25 Sep)
    if claimed is None:
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


def _rec_placeholders(expr, f, nvar):
    """`expr` with each `f(n-k)` swapped for a placeholder symbol: (new expr, {tag: k})."""
    subs, shifts = {}, {}
    for app in sorted(expr.atoms(sp.core.function.AppliedUndef), key=str):
        if app.func is not f or len(app.args) != 1:
            raise LeanPrintError(f"unsupported application {app}")
        shift = sp.simplify(app.args[0] - nvar)
        if not shift.is_Integer or shift > 0:
            raise LeanPrintError(f"non-constant or forward index {app}")
        tag = sp.Symbol(f"RECPLACEHOLDER{abs(int(shift))}")
        subs[app] = tag
        shifts[tag.name] = abs(int(shift))
    return expr.xreplace(subs), shifts


def _rec_to_lean(expr, f, nvar, fname: str) -> str:
    """Render a recurrence right-hand side, where `f(n-k)` has no direct SymPy->Lean rendering.
    Each application is swapped for a placeholder symbol, the exact printer does the rest, and the
    placeholders are put back — so the term still goes through the printer that refuses to guess."""
    sub, shifts = _rec_placeholders(expr, f, nvar)
    out = sympy_to_lean(sub, "ℝ")
    for tag_name, k in shifts.items():
        out = out.replace(tag_name, f"{fname} {nvar.name}" if k == 0 else f"{fname} ({nvar.name} - {k})")
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
    from ..equiv import exact_integer
    try:
        rel = parse_relation(p["recurrence"], ns2)
        initial = {}
        for k, v in (p.get("initial") or {}).items():
            ki = exact_integer(k)             # never int(sympify(...)): 1.5 would become 1
            if ki is None or _written_conds([str(v)], ns2):
                return None
            initial[ki] = parse_expr_str(str(v), ns2)
        index = exact_integer(p["index"])
        if index is None:
            return None
        claimed = _parse_written(ca["payload"], ns2) if ca["kind"] in ("value", "expression") \
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
    # value for a sequence that does not exist. A partial operation in the recurrence is out —
    # read on the placeholder form (an applied `a(n-1)` has no domain rule) and AS WRITTEN.
    rhs_sub, shifts = _rec_placeholders(rel.rhs, f, nvar)
    if open_guards([rhs_sub], "ℝ"):
        return None
    for side in _as_written(p["recurrence"], ns2):
        if _open(_definedness(_rec_placeholders(side, f, nvar)[0])):
            return None
    # ℕ subtraction truncates: with only a(0) given, `a(n-2)` at n = 1 is a(1 - 2) = a(0) in Lean,
    # a term the problem never defined (audit 25 Sep 2026, C5: "a(3) = 5" was certified). Every
    # backward reach from the first recurrence index must land on a given term.
    if start - max(shifts.values(), default=0) < min(initial):
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
    # the hypotheses define the sequence (initial terms, then each term from earlier ones only),
    # so exactly one sequence satisfies them: satisfiable by construction
    return LeanStatement(name, f"({fname} : ℕ → ℝ)", hyps, goal, "ℝ", "recurrence_term",
                         hints=hints, sat_by_construction=True)


# ---------------------------------------------------------------------------- domain_of
def _real_only(obj, ns, names) -> bool:
    """The variables are plain reals: no declared domain, no constraints, and no domain of
    discourse. A narrower domain would have to enter the statement, and a symbol carrying a
    positivity assumption lets SymPy fold conditions such as `x > 0` to True before printing."""
    if obj.domain_of_discourse:
        return False
    for v in obj.vars:
        if v.name in names and (v.domain not in (None, "real") or v.constraints):
            return False
    return True


def _set_pieces(s: sp.Set) -> list[sp.Set]:
    """The pieces `_interval_to_lean` prints, in the same order (one per ∨-disjunct)."""
    return list(s.args) if isinstance(s, sp.Union) else [s]


def _piece_parts(piece: sp.Set) -> int:
    """How many conjuncts `_interval_to_lean` prints for one Interval piece (0 = `True`)."""
    return int(piece.inf != -sp.oo) + int(piece.sup != sp.oo)


def _truth(rel, var, pt) -> bool | None:
    try:
        v = rel.subs(var, pt)
    except (TypeError, ValueError):
        return None
    return True if v is sp.true else False if v is sp.false else None


def _region_iff_hints(var, conds, claimed) -> tuple[str, ...]:
    """A proof of `∀ x, (conds) ↔ (x ∈ claimed)` that splits ℝ at every critical point (the real
    roots of the conditions and the endpoints of the claim), then closes each open region and each
    point on its own. SymPy decides the split points and which side holds where, but only to write
    TACTICS: Lean re-proves every region, and a wrong claim (the two sides differ somewhere) gets
    no hint at all (decision 9: the generating calculation never enters the statement)."""
    pts: set = set()
    for c in conds:
        try:
            poly = sp.Poly(c.lhs - c.rhs, var)
        except sp.PolynomialError:
            return ()
        for r in poly.real_roots():
            if not r.is_Rational:
                return ()
            pts.add(r)
    for piece in _set_pieces(claimed):
        if isinstance(piece, sp.Interval):
            ends = [e for e in (piece.inf, piece.sup) if e not in (-sp.oo, sp.oo)]
        elif isinstance(piece, sp.FiniteSet):
            ends = list(piece.args)
        else:
            return ()
        if not all(e.is_Rational for e in ends):
            return ()
        pts.update(ends)
    pts_l = sorted(pts)
    if len(pts_l) > 8:
        return ()
    vn = var.name
    pieces = _set_pieces(claimed)

    def side_truth(pt) -> tuple[bool, bool] | None:
        lt = [_truth(c, var, pt) for c in conds]
        if any(t is None for t in lt):
            return None
        rt = claimed.contains(pt)
        if rt not in (sp.true, sp.false):
            return None
        return all(lt), rt is sp.true

    def closers(hyps: list[str]) -> str:
        nl = f"nlinarith [{', '.join(hyps)}]" if hyps else "nlinarith"
        nl_hc = f"nlinarith [{', '.join(hyps + ['hc'])}]"
        return f"first | (linarith; done) | ({nl}; done) | (intro hc; {nl_hc}; done)"

    def prove_conds(hyps: list[str]) -> str:
        one = f"({closers(hyps)})"
        if not conds:
            return "trivial"
        if len(conds) == 1:
            return one
        return "exact ⟨" + ", ".join(f"by {one}" for _ in conds) + "⟩"

    def refute_conds(hyps: list[str], pt) -> str | None:
        n = len(conds)
        for k, c in enumerate(conds):
            if _truth(c, var, pt) is False:
                acc = "h" if n == 1 else ("h" + ".2" * k + (".1" if k < n - 1 else ""))
                hs = ", ".join(hyps + ["hk"])
                return f"have hk := {acc}\n{{i}}first | (linarith; done) | (nlinarith [{hs}]; done)"
        return None

    def prove_claim(pt) -> str | None:
        n = len(pieces)
        for j, piece in enumerate(pieces):
            if piece.contains(pt) is not sp.true:
                continue
            nav = [] if n == 1 else (["right"] * j + (["left"] if j < n - 1 else []))
            if isinstance(piece, sp.Interval):
                k = _piece_parts(piece)
                close = "trivial" if k == 0 else "linarith" if k == 1 else "exact ⟨by linarith, by linarith⟩"
            else:
                return None
            return "; ".join(nav + [close])
        return None

    def piece_pattern(piece, idx: int) -> str:
        if isinstance(piece, sp.Interval):
            return f"⟨ra{idx}, rb{idx}⟩" if _piece_parts(piece) == 2 else f"ra{idx}"
        names = [f"re{idx}_{t}" for t in range(len(piece.args))]
        return names[0] if len(names) == 1 else "(" + " | ".join(names) + ")"

    refute_claim = ("rcases h with " + " | ".join(piece_pattern(p_, i) for i, p_ in enumerate(pieces))
                    + " <;> first | (linarith; done) | (nlinarith; done)")

    def region(lo, hi, hyps: list[str], ind: int) -> list[str] | None:
        if lo is None and hi is None:
            pt = sp.Integer(0)
        elif lo is None:
            pt = hi - 1
        elif hi is None:
            pt = lo + 1
        else:
            pt = (lo + hi) / 2
        st = side_truth(pt)
        if st is None or st[0] != st[1]:
            return None                  # the claim is wrong here: no hint, the proof will fail
        i1, i2 = " " * ind, " " * (ind + 2)       # a bullet's block continues at the column of
        if st[0]:                                  # its first tactic, i.e. two past the `·`
            pc = prove_claim(pt)
            if pc is None:
                return None
            return [f"{i1}constructor", f"{i1}· intro _", f"{i2}{pc}",
                    f"{i1}· intro _", f"{i2}{prove_conds(hyps)}"]
        rc = refute_conds(hyps, pt)
        if rc is None:
            return None
        return [f"{i1}constructor", f"{i1}· intro h", f"{i2}exfalso", f"{i2}" + rc.format(i=i2),
                f"{i1}· intro h", f"{i2}exfalso", f"{i2}{refute_claim}"]

    def point(c, ind: int, name: str) -> list[str] | None:
        st = side_truth(c)
        if st is None or st[0] != st[1]:
            return None
        i1 = " " * ind
        return [f"{i1}subst {name}",
                f"{i1}first | (norm_num; done) | (constructor <;> intro h <;> norm_num at h ⊢; done)"]

    def split(i: int, lower, lower_hyp: str | None, ind: int) -> list[str] | None:
        hyps = [lower_hyp] if lower_hyp else []
        if i == len(pts_l):
            return region(lower, None, hyps, ind)
        c = pts_l[i]
        i1 = " " * ind
        left = region(lower, c, hyps + [f"hlt{i}"], ind + 2)
        mid = point(c, ind + 2, f"heq{i}")
        right = split(i + 1, c, f"hgt{i}", ind + 2)
        if left is None or mid is None or right is None:
            return None
        head = f"{i1}rcases lt_trichotomy {vn} {_paren(sympy_to_lean(c, 'ℝ'))} with hlt{i} | heq{i} | hgt{i}"

        def bullet(block):
            return [f"{i1}· {block[0].lstrip()}"] + block[1:]
        return [head] + bullet(left) + bullet(mid) + bullet(right)

    body = split(0, None, None, 2)
    if body is None:
        return ()
    return ("\n".join([f"  intro {vn}"] + body),)


def _t_domain_of(obj, ns, ca, name) -> LeanStatement | None:
    """"The domain of f is S" becomes `∀ x, (definedness conditions of f) ↔ x ∈ S`. The conditions
    are the definition the deterministic layer uses (`definedness_conditions`); Lean checks that S
    is exactly where they hold. The statement never contains f itself, so no junk value can enter
    it, and a condition that itself holds a partial operation (`log(√x − 1)` needs `√x − 1 > 0`)
    is out of scope rather than printed."""
    p = obj.task.params
    var = ns.get(p.get("var", "x"))
    if not isinstance(var, sp.Symbol) or ca["kind"] not in ("set", "interval"):
        return None
    if not _real_only(obj, ns, {var.name}):
        return None
    expr = parse_structural(p["expr"], ns, strict=True)
    if expr.free_symbols - {var}:
        return None
    claimed = parse_answer(ca["kind"], ca["payload"], ns)
    if not isinstance(claimed, sp.Set):
        return None
    conds = []
    # exact or nothing: `0**x`, `(-2)**x`, `factorial(x)` have no condition list and were
    # certified "domain ℝ" (audit 25 Sep 2026, C9); _definedness refuses them
    for c in _definedness(expr, var):
        if not getattr(c, "free_symbols", None):
            if _closed_truth(c) is not True:
                return None
            continue
        if not isinstance(c, sp.core.relational.Relational) or (c.free_symbols - {var}):
            return None
        if open_guards([c.lhs, c.rhs]):
            return None                           # a partial operation inside the condition
        conds.append(c)
    for node in sp.preorder_traversal(expr):       # `Mod` has no definedness_conditions entry
        if isinstance(node, sp.Mod):
            return None
    lhs = " ∧ ".join(f"({relation_to_lean(c, 'ℝ')})" for c in conds) if conds else "True"
    rhs = _interval_to_lean(claimed, var.name, "ℝ")
    goal = f"∀ {var.name} : ℝ, (({lhs}) ↔ ({rhs}))"
    return LeanStatement(name, "", [], goal, "ℝ", "domain_of_iff",
                         hints=_region_iff_hints(var, conds, claimed))


# ---------------------------------------------------------------------------- simplify_expression
def _ne_from_guards(q, guards: list[tuple[str, Any]]) -> str | None:
    """Proof term of `q ≠ 0` from guard hypotheses `name : g ≠ 0` when q is a constant multiple of
    a product of some of the g — e.g. `x ^ 2 + x ≠ 0` from `x ≠ 0` and `x + 1 ≠ 0`."""
    from itertools import combinations
    for r in range(1, min(len(guards), 4) + 1):
        for sub in combinations(guards, r):
            prod = sp.Mul(*[g for _, g in sub])
            ratio = sp.cancel(sp.sympify(q) / prod)
            if ratio.is_Rational and ratio != 0:
                term = sub[0][0]
                for nm, _ in sub[1:]:
                    term = f"(mul_ne_zero {term} {nm})"
                return f"fun hc => {term} (by linear_combination ({sympy_to_lean(1 / ratio, 'ℝ')}) * hc)"
    return None


def _t_simplify_expression(obj, ns, ca, name) -> LeanStatement | None:
    """"expr simplifies to e" becomes: wherever expr is defined, e is defined as well and equal to
    it. The guards come from the problem's expression alone, so a wrong claim cannot shrink the
    region it must hold on; the claim's own definedness is part of the GOAL. A claim that loses
    points of expr's domain (`x` → `x²/x`) is therefore not provable, and the layer abstains."""
    p = obj.task.params
    if ca["kind"] not in ("expression", "value") or not p.get("expr"):
        return None
    # both AS WRITTEN, with no fallback to the simplifying parse (principles 3 and 12): a LaTeX
    # claim is read by an evaluating parser, so it abstains rather than being compared rewritten
    target = parse_structural(p["expr"], ns, strict=True)
    claimed = _parse_written(ca["payload"], ns)
    if claimed is None or isinstance(claimed, (sp.Set, sp.MatrixBase)) or isinstance(target, sp.MatrixBase):
        return None
    syms = sorted(target.free_symbols, key=lambda s_: s_.name)
    if not syms or (claimed.free_symbols - target.free_symbols):
        return None
    if not _real_only(obj, ns, {s_.name for s_ in syms}) or any(s_.name == "hc" for s_ in syms):
        return None
    t_conds = [c for c in _definedness(target) if getattr(c, "free_symbols", None)]
    c_conds = [c for c in _definedness(claimed) if getattr(c, "free_symbols", None)]
    if (t_conds or c_conds) and len(syms) != 1:
        return None                     # a guarded identity in several variables: out of scope
    if t_conds and not has_interior_point([target], syms[0]):
        return None                     # defined nowhere: the ∀ would be about junk values only
    tgt_txt, cl_txt = sympy_to_lean(target, "ℝ"), sympy_to_lean(claimed, "ℝ")
    if tgt_txt == cl_txt:
        return None                     # the "simplification" is the expression itself
    guards = [relation_to_lean(c, "ℝ") for c in t_conds]
    goal_conds = []
    for c in c_conds:
        txt = relation_to_lean(c, "ℝ")
        if txt not in guards and txt not in goal_conds:
            goal_conds.append(txt)
    body = " ∧ ".join([f"({g})" for g in goal_conds] + [f"({tgt_txt} = {cl_txt})"])
    names = " ".join(s_.name for s_ in syms)
    goal = f"∀ {names} : ℝ, " + "".join(f"({g}) → " for g in guards) + f"({body})"
    # hints: intro the guards, prove each goal condition from them, then clear denominators
    hnames = [f"h{i}" for i in range(1, len(guards) + 1)]
    ne_guards = [(hn, c.lhs - c.rhs) for hn, c in zip(hnames, t_conds) if isinstance(c, sp.Unequality)]
    intro = f"  intro {' '.join([names] + hnames)}"
    haves: list[str] = []
    for k, txt in enumerate(goal_conds, start=1):
        c = next(c for c in c_conds if relation_to_lean(c, "ℝ") == txt)
        pf = _ne_from_guards(c.lhs - c.rhs, ne_guards) if isinstance(c, sp.Unequality) else None
        if pf is None:
            nl = f"nlinarith [{', '.join(hnames)}]" if hnames else "nlinarith"
            pf = (f"by first | (assumption; done) | (positivity; done) | (linarith; done) "
                  f"| ({nl}; done)")
        haves.append(f"  have c{k} : {txt} := {pf}")
    cnames = [f"c{k}" for k in range(1, len(goal_conds) + 1)]
    # field_simp looks for `d ≠ 0` in the exact printed form of each denominator (`1 + x`, not the
    # guard's `x + 1`), so every denominator of the goal gets its own fact, derived from the guards
    # (the printer writes a Mul's denominator from `as_numer_denom()`, in SymPy's canonical order,
    # and a bare Pow's base as parsed — so both are collected)
    dens: dict[str, Any] = {}
    for e in (target, claimed):
        for node in sp.preorder_traversal(e):
            bases = []
            if isinstance(node, sp.Mul):
                den = node.as_numer_denom()[1]
                if den != 1:
                    bases.append(den)
            elif isinstance(node, sp.Pow) and node.args[1].is_Integer and node.args[1] < 0:
                bases.append(node.args[0])
            for b in list(bases):
                if isinstance(b, sp.Mul):
                    bases.extend(b.args)
            for b in bases:
                if b.free_symbols:
                    dens.setdefault(_print_lean(b, "ℝ"), b)
    for k, (txt, b) in enumerate(dens.items(), start=1):
        pf = _ne_from_guards(b, ne_guards)
        if pf is not None:
            haves.append(f"  have d{k} : {txt} ≠ 0 := {pf}")
    head = [intro] + haves + ([f"  refine ⟨{', '.join(cnames)}, ?_⟩"] if cnames else [])
    hints = tuple("\n".join(head + tail)
                  for tail in (["  field_simp", "  ring"], ["  field_simp"], ["  ring"], ["  ring_nf"]))
    return LeanStatement(name, "", [], goal, "ℝ", "simplify_identity", hints=hints)


# ---------------------------------------------------------------------------- count_solutions
def _t_count_solutions(obj, ns, ca, name) -> LeanStatement | None:
    """"How many integer solutions" becomes two facts Lean proves itself: every solution lies in
    the box, and the box holds exactly n of them. The box comes from the IR's bounds, but since the
    first half is proved, a box that is too small cannot certify a count (the deterministic layer,
    by contrast, trusts the bounds)."""
    from ..equiv import exact_integer
    p = obj.task.params
    bounds = p.get("bounds") or {}
    vars_ = list(obj.vars)
    if not (1 <= len(vars_) <= 3) or not obj.givens or obj.domain_of_discourse:
        return None
    if any(v.domain not in ("integer", "positive_integer", "nonneg_integer", "natural") for v in vars_):
        return None
    if any(v.name in ("sol", "h") for v in vars_):
        return None
    n = exact_integer(ca["payload"])          # never int(): a claimed 3.5 would become 3
    if n is None or n < 0:
        return None
    box, size = [], 1
    for v in vars_:
        b = bounds.get(v.name)
        if not isinstance(b, (list, tuple)) or len(b) != 2:
            return None
        lo, hi = exact_integer(b[0]), exact_integer(b[1])
        if lo is None or hi is None or hi < lo:
            return None
        size *= hi - lo + 1
        box.append((v, lo, hi))
    if size > 2000:
        return None
    rels = [parse_relation(g, ns) for g in obj.givens]
    rels += [parse_relation(c, ns) for v in vars_ for c in v.constraints]
    if open_guards(rels, "ℤ"):
        return None                           # a partial operation in the predicate: junk-prone
    if _written_conds(list(obj.givens) + [c for v in vars_ for c in v.constraints], ns):
        return None                           # ... also one the normal parse folded away (x/x = 1)
    for r in rels:
        for node in sp.preorder_traversal(r):
            if isinstance(node, sp.Mod):
                return None                   # ℤ `%` in Lean is Euclidean, SymPy's is floored
    syms = [ns.get(v.name) for v in vars_]
    if not all(isinstance(s_, sp.Symbol) for s_ in syms):
        return None
    paths = ["sol"] if len(vars_) == 1 else (["sol.1", "sol.2"] if len(vars_) == 2
                                              else ["sol.1", "sol.2.1", "sol.2.2"])

    def pred(names: list[str]) -> str:
        sub = {s_: sp.Symbol(nm) for s_, nm in zip(syms, names)}
        parts = [relation_to_lean(r.xreplace(sub), "ℤ") for r in rels]
        # the domain condition is written as text: parsed, `0 < x` folds to True on a positive symbol
        parts += [_DOMAIN_COND[v.domain].format(v=nm) for v, nm in zip(vars_, names)
                  if _DOMAIN_COND.get(v.domain)]
        return " ∧ ".join(f"({t})" for t in parts)

    icc = [f"Finset.Icc ({sympy_to_lean(sp.Integer(lo), 'ℤ')} : ℤ) {sympy_to_lean(sp.Integer(hi), 'ℤ')}"
           for _, lo, hi in box]
    finset = icc[0] if len(icc) == 1 else (f"({icc[0]} ×ˢ {icc[1]})" if len(icc) == 2
                                          else f"({icc[0]} ×ˢ ({icc[1]} ×ˢ {icc[2]}))")
    typ = " × ".join(["ℤ"] * len(vars_))
    names = [v.name for v in vars_]
    inside = " ∧ ".join(f"({sympy_to_lean(sp.Integer(lo), 'ℤ')} ≤ {v.name} ∧ {v.name} ≤ "
                        f"{sympy_to_lean(sp.Integer(hi), 'ℤ')})" for v, lo, hi in box)
    goal = (f"(∀ {' '.join(names)} : ℤ, ({pred(names)}) → ({inside})) ∧ "
            f"(({finset}).filter (fun sol : {typ} => {pred(paths)})).card = {n}")
    k = len(rels) + sum(1 for v in vars_ if _DOMAIN_COND.get(v.domain))
    hyp_pat = "h" if k == 1 else "⟨" + ", ".join(f"h{i}" for i in range(1, k + 1)) + "⟩"
    intro = f"  refine ⟨fun {' '.join(names)} h => ?_, by decide⟩"
    split_goal = "⟨?_, ?_⟩" if len(vars_) == 1 else "⟨" + ", ".join(["⟨?_, ?_⟩"] * len(vars_)) + "⟩"
    hints = (f"{intro}\n  omega",
             f"{intro}\n  obtain {hyp_pat} := h\n  omega",
             f"{intro}\n  obtain {hyp_pat} := h\n  refine {split_goal} <;> nlinarith")
    return LeanStatement(name, "", [], goal, "ℤ", "count_solutions_finset", hints=hints)


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
    "domain_of": _t_domain_of,
    "simplify_expression": _t_simplify_expression,
    "count_solutions": _t_count_solutions,
}


# What each template states of the problem's restrictions. A restriction a template does not
# state makes it refuse (audit 25 Sep 2026, C2): dropping one changed the question — "x² < 4 over
# x > 0" was certified as (−2, 2). `index`: the variable is a summation / sequence index, whose
# integrality is the template's own.
_ENCODES: dict[str, frozenset] = {
    "evaluate": frozenset({"givens", "constraints", "domains"}),
    "solve_equation": frozenset({"givens", "constraints", "domains", "dod"}),
    "solve_inequality": frozenset({"givens", "constraints", "domains", "dod"}),
    "count_integers": frozenset({"givens", "constraints", "domains"}),
    "count_solutions": frozenset({"givens", "constraints", "domains"}),
    "series_sum": frozenset({"index"}),
    "recurrence_term": frozenset({"index"}),
}


def _restrictions_gate(obj) -> None:
    enc = _ENCODES.get(obj.task.kind, frozenset())
    if any(v.domain in _UNSUPPORTED_DOMAINS for v in obj.vars):
        raise LeanPrintError("complex/rational variables have no faithful ℝ/ℤ statement")
    if obj.domain_of_discourse and "dod" not in enc:
        raise LeanPrintError("domain of discourse not stated by this template")
    if any(v.constraints for v in obj.vars) and "constraints" not in enc:
        raise LeanPrintError("variable constraints not stated by this template")
    if obj.givens and "givens" not in enc:
        raise LeanPrintError("givens not stated by this template")
    if "domains" not in enc:
        allowed = {None, "real"} | (set(_INT_DOMAINS) if "index" in enc else set())
        if any(v.domain not in allowed for v in obj.vars):
            raise LeanPrintError("variable domain not stated by this template")


def _functions_faithful(obj, ns) -> None:
    """A problem function's body is parsed with simplification (`f(x) = x/x` becomes 1): refuse
    unless its domain as written is exactly its domain as parsed."""
    for fd in obj.functions:
        declared = isinstance(getattr(fd, "domain", None), str) and bool(fd.domain.strip())
        fn = ns.get(fd.name)
        body, argsyms = getattr(fn, "body", None), getattr(fn, "argsyms", None)
        if body is None or argsyms is None or len(argsyms) != len(fd.args):
            raise LeanPrintError(f"function {fd.name} has no parsed body")
        # read with the function's own arguments, as its body was parsed (parse._make_function)
        w = _as_written(fd.expr, dict(ns, **dict(zip(fd.args, argsyms))))
        if len(w) != 1:
            raise LeanPrintError(f"function {fd.name} is not one expression")
        wc, pc = _open(_definedness(w[0])), _open(_definedness(body))
        if len(fd.args) == 1 and isinstance(argsyms[0], sp.Symbol):
            v = argsyms[0]
            dw, dp = _solve_region(wc, v), _solve_region(pc, v)
            for c, region in [(c, dw) for c in pc] + [(c, dp) for c in wc]:
                bad = _violation_set(c, v, region)
                if bad is None or bad != S.EmptySet:
                    raise LeanPrintError(f"function {fd.name}: simplification changed its domain")
            if declared:
                # the templates state the body, not the declared domain (Lean proved f(-2) = 5 for
                # f(x) = x**2 + 1 on x > 0, second audit of 29 Sep 2026): a domain is stated only
                # when the body's own written conditions already imply it ("x != 1" for (2x+3)/(x-1))
                rel = getattr(fn, "domain_rel", None)
                if rel is None:
                    raise LeanPrintError(f"function {fd.name}: its declared domain cannot be read")
                for c in (rel.args if isinstance(rel, sp.And) else (rel,)):
                    bad = _violation_set(c, v, dw)
                    if bad is None or bad != S.EmptySet:
                        raise LeanPrintError(f"function {fd.name}: its declared domain is not stated")
        elif declared:
            raise LeanPrintError(f"function {fd.name}: its declared domain is not stated")
        elif set(map(str, wc)) != set(map(str, pc)):
            raise LeanPrintError(f"function {fd.name}: simplification changed its domain")


# a claim that cannot be read as written may still be a plain number set; one with an operation
# that can be undefined cannot (the evaluating parse would already have rewritten it)
_RISKY_CLAIM = re.compile(r"sqrt|log|ln|tan|cot|sec|csc|asin|acos|atan|root|exp|\*\*|\^|/|%|mod|"
                          r"factorial|binomial|gcd|lcm|frac|√|÷", re.IGNORECASE)


def _claim_written_ok(obj, ca, ns) -> None:
    """The claim is compared as written (principle 3): a closed part of it that is undefined as
    written — `sqrt(-1)**2`, which evaluates to −1 — refuses, as does an operation with no exact
    domain rule. Its OPEN conditions are each template's business."""
    from ..normalize.parse import parse_as_written
    payload = ca.get("payload")
    for txt in (payload if isinstance(payload, list) else [payload]):
        if not isinstance(txt, str):
            continue
        s = strip_presentation(txt)
        if obj.task.kind == "antiderivative":
            s = _PLUS_C.sub("", s)
        w = parse_as_written(s, ns)
        if w is None:
            try:
                w = [_latex_written(s, ns)]
            except LeanPrintError:
                if _RISKY_CLAIM.search(s):
                    raise LeanPrintError(f"claim {txt!r} cannot be read as written") from None
                continue
        for side in w:
            if isinstance(side, sp.Dict) and not side:
                continue                              # `{}`: the empty set
            for c in _definedness(side):
                if not getattr(c, "free_symbols", None) and _closed_truth(c) is not True:
                    raise LeanPrintError(f"claim {txt!r} is undefined as written ({c})")


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
        _restrictions_gate(obj)
        _functions_faithful(obj, ns)
        _claim_written_ok(obj, claimed_answer, ns)
        st = fn(obj, ns, claimed_answer, name)
    except LeanPrintError:
        return None
    except Exception:
        return None
    if st is None or is_trivial(st):
        return None
    return st
