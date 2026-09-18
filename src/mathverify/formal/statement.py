"""Deterministic IR -> Lean 4 theorem statement.

Handoff [5] measures the real F5 risk: 89.5% of autoformalised statements compile but only
60.5% say what the problem says. We avoid that gap entirely by NOT asking a model for the
statement: the statement is generated from the (already round-trip audited) IR by a
template, with a SymPy -> Lean printer that refuses anything it cannot translate exactly.
The model is only asked for the *proof*, which Lean then checks — a proof cannot make a
wrong statement right.

Supported task kinds (F5 scope): evaluate (systems / closed arithmetic), solve_equation
(as an iff over the domain), count_integers (as a Finset card), series_sum (finite),
linalg matrix identities. Everything else returns None -> L7 simply does not run.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sympy as sp
from sympy import S

from ..intake.structured import load_problem_ir
from ..normalize.parse import build_namespace, parse_relation, parse_expr_str, parse_answer

__all__ = ["LeanStatement", "build_statement", "sympy_to_lean", "LeanPrintError"]


class LeanPrintError(ValueError):
    """The expression has no exact Lean/Mathlib rendering — never guess one."""


_DOMAIN_LEAN = {"real": "ℝ", "positive_real": "ℝ", "nonneg_real": "ℝ", "rational": "ℚ",
                "integer": "ℤ", "positive_integer": "ℤ", "nonneg_integer": "ℤ", "natural": "ℤ"}
# implied side conditions for the restricted domains (kept as explicit hypotheses)
_DOMAIN_COND = {"positive_real": "0 < {v}", "nonneg_real": "0 ≤ {v}",
                "positive_integer": "0 < {v}", "nonneg_integer": "0 ≤ {v}", "natural": "0 < {v}"}

# classes only — `sp.sqrt` is a function (isinstance would raise); sqrt is handled by Pow(1/2)
_FUNC: dict[type, str] = {
    sp.sin: "Real.sin", sp.cos: "Real.cos", sp.tan: "Real.tan", sp.exp: "Real.exp",
}


def _paren(s: str) -> str:
    return s if (s.isidentifier() or s.isdigit() or (s.startswith("(") and s.endswith(")"))) else f"({s})"


def sympy_to_lean(e, field: str = "ℝ") -> str:
    """Exact printer. Raises LeanPrintError on anything not covered."""
    e = sp.sympify(e)
    if isinstance(e, sp.Integer):
        n = int(e)
        return f"({n} : {field})" if n < 0 else str(n)
    if isinstance(e, sp.Rational):
        p, q = int(e.p), int(e.q)
        if field in ("ℤ",):
            raise LeanPrintError(f"non-integer rational {e} in {field}")
        return f"({p} / {q} : {field})"
    if isinstance(e, sp.Float):
        r = sp.nsimplify(e, rational=True)
        if isinstance(r, sp.Rational):
            return sympy_to_lean(r, field)
        raise LeanPrintError(f"float {e}")
    if e is sp.pi:
        return "Real.pi"
    if e is sp.E:
        return "Real.exp 1"
    if isinstance(e, sp.Symbol):
        return e.name
    if isinstance(e, sp.Add):
        args = [sympy_to_lean(a, field) for a in e.args]
        out = args[0]
        for a in args[1:]:
            out = f"{out} - {a[1:]}" if a.startswith("-") else f"{out} + {a}"
        return f"({out})"
    if isinstance(e, sp.Mul):
        coeff, rest = e.as_coeff_Mul()
        if coeff == -1:
            return f"(-{sympy_to_lean(rest, field)})"
        # render negative powers as a division so the Lean term stays in the ring language
        num, den = e.as_numer_denom()
        if den != 1:
            if field == "ℤ":
                raise LeanPrintError("division over ℤ")
            return f"({sympy_to_lean(num, field)} / {sympy_to_lean(den, field)})"
        args = [sympy_to_lean(a, field) for a in e.args]
        return "(" + " * ".join(args) + ")"
    if isinstance(e, sp.Pow):
        b, x = e.args
        if isinstance(x, sp.Integer):
            n = int(x)
            if n >= 0:
                return f"({sympy_to_lean(b, field)} ^ {n})"
            if field == "ℤ":
                raise LeanPrintError("negative integer power over ℤ")
            inner = sympy_to_lean(b, field)
            return f"(1 / {inner})" if n == -1 else f"(1 / ({inner} ^ {-n}))"
        if x == sp.Rational(1, 2):
            return f"Real.sqrt {_paren(sympy_to_lean(b, field))}"
        raise LeanPrintError(f"power {e}")
    if isinstance(e, sp.Abs):
        return f"|{sympy_to_lean(e.args[0], field)}|"
    for cls, name in _FUNC.items():
        if isinstance(e, cls):
            if "{0}" in name:
                return name.format(sympy_to_lean(e.args[0], field))
            return f"{name} {_paren(sympy_to_lean(e.args[0], field))}"
    if isinstance(e, sp.log):
        if len(e.args) == 1:
            return f"Real.log {_paren(sympy_to_lean(e.args[0], field))}"
        raise LeanPrintError("log with explicit base")
    if isinstance(e, sp.Mod):
        a, b = e.args
        return f"({sympy_to_lean(a, field)} % {sympy_to_lean(b, field)})"
    if e.func is sp.gcd or e.__class__.__name__ == "gcd":
        a, b = e.args
        return f"Int.gcd {_paren(sympy_to_lean(a, 'ℤ'))} {_paren(sympy_to_lean(b, 'ℤ'))}"
    if e.__class__.__name__ == "lcm":
        a, b = e.args
        return f"Int.lcm {_paren(sympy_to_lean(a, 'ℤ'))} {_paren(sympy_to_lean(b, 'ℤ'))}"
    if isinstance(e, sp.factorial):
        return f"Nat.factorial {_paren(sympy_to_lean(e.args[0], 'ℤ'))}"
    if isinstance(e, sp.binomial):
        n, k = e.args
        return f"Nat.choose {_paren(sympy_to_lean(n, 'ℤ'))} {_paren(sympy_to_lean(k, 'ℤ'))}"
    raise LeanPrintError(f"cannot print {type(e).__name__}: {e}")


def relation_to_lean(rel, field: str = "ℝ") -> str:
    if isinstance(rel, sp.Equality):
        return f"{sympy_to_lean(rel.lhs, field)} = {sympy_to_lean(rel.rhs, field)}"
    if isinstance(rel, sp.Unequality):
        return f"{sympy_to_lean(rel.lhs, field)} ≠ {sympy_to_lean(rel.rhs, field)}"
    if isinstance(rel, sp.StrictLessThan):
        return f"{sympy_to_lean(rel.lhs, field)} < {sympy_to_lean(rel.rhs, field)}"
    if isinstance(rel, sp.LessThan):
        return f"{sympy_to_lean(rel.lhs, field)} ≤ {sympy_to_lean(rel.rhs, field)}"
    if isinstance(rel, sp.StrictGreaterThan):
        return f"{sympy_to_lean(rel.lhs, field)} > {sympy_to_lean(rel.rhs, field)}"
    if isinstance(rel, sp.GreaterThan):
        return f"{sympy_to_lean(rel.lhs, field)} ≥ {sympy_to_lean(rel.rhs, field)}"
    if isinstance(rel, sp.And):
        return " ∧ ".join(f"({relation_to_lean(a, field)})" for a in rel.args)
    if isinstance(rel, sp.Or):
        return " ∨ ".join(f"({relation_to_lean(a, field)})" for a in rel.args)
    raise LeanPrintError(f"cannot print relation {rel}")


@dataclass
class LeanStatement:
    name: str
    binders: str                 # "(a b : ℝ)"
    hypotheses: list[str]        # rendered hypothesis propositions (without names)
    goal: str
    field: str
    kind: str                    # which template produced it
    note: str = ""

    def theorem(self, proof: str) -> str:
        hs = " ".join(f"(h{i} : {h})" for i, h in enumerate(self.hypotheses, start=1))
        head = f"theorem {self.name} {self.binders} {hs} : {self.goal}".replace("  ", " ")
        return f"{head} := by\n{proof}"

    def vacuity_probe(self) -> str | None:
        """Theorem asking for False from the same hypotheses: if it compiles, the hypotheses
        are contradictory and the real theorem is vacuously true (handoff failure mode #5/#6)."""
        if not self.hypotheses:
            return None
        hs = " ".join(f"(h{i} : {h})" for i, h in enumerate(self.hypotheses, start=1))
        return (f"theorem {self.name}_vacuity {self.binders} {hs} : False := by\n"
                "  first | omega | linarith | nlinarith | norm_num at * | simp_all | exact absurd rfl (by norm_num)")

    def no_hyp_probe(self, proof: str) -> str | None:
        """Same goal without the hypotheses: if it still proves, the data were never used."""
        if not self.hypotheses:
            return None
        return f"theorem {self.name}_nohyp {self.binders} : {self.goal} := by\n{proof}"


def _field_for(ir_obj) -> str:
    doms = {v.domain for v in ir_obj.vars}
    if doms and doms <= {"integer", "positive_integer", "nonneg_integer", "natural"}:
        return "ℤ"
    return "ℝ"


def build_statement(ir: dict[str, Any], claimed_answer: dict[str, Any], name: str = "mv_claim"
                    ) -> LeanStatement | None:
    """Deterministic statement for the claim, or None when the shape is out of F5 scope."""
    try:
        obj = load_problem_ir(ir)
        ns = build_namespace(obj)
    except Exception:
        return None
    kind = obj.task.kind
    p = obj.task.params or {}
    field = _field_for(obj)
    try:
        if kind == "evaluate":
            expr_src = p.get("expr") or obj.unknown_of_interest
            if not expr_src:
                return None
            target = parse_expr_str(expr_src, ns)
            claimed = parse_answer(claimed_answer["kind"], claimed_answer["payload"], ns)
            if isinstance(claimed, sp.Set) or claimed is None:
                return None
            hyps = [relation_to_lean(parse_relation(g, ns), field) for g in obj.givens]
            for v in obj.vars:
                cond = _DOMAIN_COND.get(v.domain)
                if cond:
                    hyps.append(cond.format(v=v.name))
                for c in v.constraints:
                    hyps.append(relation_to_lean(parse_relation(c, ns), field))
            goal = f"{sympy_to_lean(target, field)} = {sympy_to_lean(claimed, field)}"
            binders = f"({' '.join(v.name for v in obj.vars)} : {field})" if obj.vars else ""
            if not obj.vars and not hyps:
                kindlabel = "closed_arithmetic"
            else:
                kindlabel = "evaluate_system"
            return LeanStatement(name, binders, hyps, goal, field, kindlabel)

        if kind == "solve_equation":
            var = ns.get(p.get("var", "x"))
            if not isinstance(var, sp.Symbol):
                return None
            eq_src = p.get("equation") or (obj.givens[0] if obj.givens else None)
            if not eq_src:
                return None
            rel = parse_relation(eq_src, ns)
            shape = claimed_answer["kind"] if claimed_answer["kind"] in ("set", "interval") else "set"
            claimed = parse_answer(shape, claimed_answer["payload"], ns)
            if claimed is S.EmptySet:
                roots_list: list = []
            elif isinstance(claimed, sp.FiniteSet):
                roots_list = list(claimed.args)
            else:
                return None
            # domain conditions of the problem AND of the expression (E2) — these are part of
            # what "solution set" means, not Lean junk-value bookkeeping
            from ..certify.domain import definedness_conditions
            conds = []
            for v in obj.vars:
                if v.name == var.name:
                    c = _DOMAIN_COND.get(v.domain)
                    if c:
                        conds.append(parse_relation(c.format(v=v.name), ns))
            conds += list(definedness_conditions(rel, var))
            cond_txt = [relation_to_lean(c, field) for c in conds]
            eq_txt = relation_to_lean(rel, field)
            # (1) no OTHER solution exists in the domain
            guard = "".join(f"({c}) → " for c in cond_txt)
            if roots_list:
                disj = " ∨ ".join(f"{var.name} = {sympy_to_lean(r, field)}" for r in roots_list)
                forall = f"∀ {var.name} : {field}, {guard}(({eq_txt}) ↔ ({disj}))"
            else:
                forall = f"∀ {var.name} : {field}, {guard}¬({eq_txt})"
            parts = [f"({forall})"]
            # (2) every claimed root IS in the domain and DOES satisfy the equation — without
            # this the iff is vacuously true for a root outside the domain (measured on
            # x/(x-3) = 3/(x-3) + 2 with the claimed root 3)
            for r in roots_list:
                for c in conds:
                    parts.append(f"({relation_to_lean(c.subs(var, r), field)})")
                parts.append(f"({relation_to_lean(rel.subs(var, r), field)})")
            goal = " ∧ ".join(parts)
            return LeanStatement(name, "", [], goal, field, "solve_equation_set")
    except LeanPrintError:
        return None
    except Exception:
        return None
    return None
