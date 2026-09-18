"""Task-kind -> certificate modules (handoff §8 router table, Phase-1 subset).

The router key is `ir.task.kind`, set by the IR author (Phase 1) or by the L0/L1
extraction (F3). `ir.topic` is informational and only used for reporting.
"""
from __future__ import annotations

ROUTES: dict[str, list[str]] = {
    # TYT (F1-TYT)
    "solve_equation":       ["certify.algebra", "certify.wordproblem"],
    "solve_inequality":     ["certify.algebra"],
    "evaluate":             ["certify.wordproblem", "certify.algebra"],
    "simplify_expression":  ["certify.algebra"],
    "count_roots":          ["certify.counting"],
    "count_integers":       ["certify.counting"],
    "count_solutions":      ["certify.counting"],
    "domain_of":            ["certify.domain"],
    # AYT (F1-AYT)
    "limit":                ["certify.limits"],
    "antiderivative":       ["certify.calculus"],
    "definite_integral":    ["certify.calculus"],
    "derivative":           ["certify.calculus"],
    "tangent_line":         ["certify.calculus"],
    "extremum":             ["certify.extremum"],
    "trig_solve":           ["certify.trig"],
    "equation_of":          ["certify.geometry"],
    # F2
    "synthetic_geometry":   ["certify.geometry_numeric"],
    "count_structures":     ["certify.combinatorics"],
    "probability":          ["certify.combinatorics"],
    "recurrence_term":      ["certify.series"],
    "closed_form":          ["certify.series"],
    "series_sum":           ["certify.series"],
    "linalg":               ["certify.linalg"],
}

# Task kinds that exist in the product spec but are out of scope so far: the verifier
# returns UNKNOWN with flag `unsupported_task_kind` instead of guessing.
DEFERRED_KINDS = {
    "proof": "F5 (Lean)",
    "ode": "F2+ (certify.calculus ODE substitution not yet implemented)",
    "solid_geometry": "F2+ (3-D realisation not implemented; formula-based solids use `evaluate`)",
}


def route(ir) -> list[str]:
    return list(ROUTES.get(ir.task.kind, []))


def known_kinds() -> set[str]:
    return set(ROUTES)
