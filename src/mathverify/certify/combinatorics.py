"""Combinatorics / probability by exhaustive enumeration (F2, handoff §7 `combinatorics`).

The sample space is described structurally (permutations / combinations / sequences /
cartesian products of explicit sets) and the event or counted set by a predicate over the
tuple `t`, evaluated with a whitelisted AST (no eval of arbitrary code). Small spaces are
enumerated exactly; when the space exceeds the cap a Monte-Carlo estimate is used ONLY to
refute (an 8-sigma miss) — never to certify.
"""
from __future__ import annotations

import ast
import itertools
import math
import random
from typing import Any, Iterable

import sympy as sp
from sympy import Rational

from ..equiv import answers_equivalent, exact_integer
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.combinatorics"
ENUM_CAP = 3_000_000
MC_SAMPLES = 200_000

# ---------------------------------------------------------------------------
# safe predicate language
# ---------------------------------------------------------------------------
_ALLOWED_NODES = (ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Name,
                  ast.Constant, ast.Subscript, ast.Slice, ast.Tuple, ast.List, ast.Set, ast.GeneratorExp,
                  ast.ListComp, ast.SetComp, ast.comprehension, ast.IfExp, ast.Attribute, ast.Load, ast.Store,
                  ast.And, ast.Or, ast.Not, ast.USub, ast.UAdd, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv,
                  ast.Mod, ast.Pow, ast.Div, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In,
                  ast.NotIn, ast.Is, ast.IsNot)
_ALLOWED_CALLS = {"sum", "len", "set", "sorted", "list", "tuple", "min", "max", "abs", "all", "any",
                  "range", "enumerate", "zip", "reversed", "int", "str", "gcd", "isqrt", "prod"}
_ALLOWED_ATTRS = {"count", "index"}
_SAFE_GLOBALS = {"sum": sum, "len": len, "set": set, "sorted": sorted, "list": list, "tuple": tuple,
                 "min": min, "max": max, "abs": abs, "all": all, "any": any, "range": range,
                 "enumerate": enumerate, "zip": zip, "reversed": reversed, "int": int, "str": str,
                 "gcd": math.gcd, "isqrt": math.isqrt, "prod": math.prod, "__builtins__": {}}


class PredicateError(ValueError):
    pass


def compile_predicate(src: str):
    """Compile a predicate over `t` into a callable; raises PredicateError on disallowed syntax."""
    if not src or not src.strip():
        return lambda t: True
    try:
        tree = ast.parse(src.strip(), mode="eval")
    except SyntaxError as e:
        raise PredicateError(f"syntax: {e}") from e
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise PredicateError(f"disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in _ALLOWED_CALLS:
                    raise PredicateError(f"disallowed call: {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr not in _ALLOWED_ATTRS:
                    raise PredicateError(f"disallowed method: {node.func.attr}")
            else:
                raise PredicateError("disallowed call form")
        if isinstance(node, ast.Attribute) and node.attr not in _ALLOWED_ATTRS:
            raise PredicateError(f"disallowed attribute: {node.attr}")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise PredicateError("dunder names are not allowed")
    code = compile(tree, "<predicate>", "eval")

    def fn(t):
        return bool(eval(code, dict(_SAFE_GLOBALS), {"t": t}))  # noqa: S307 - AST whitelisted above
    return fn


# ---------------------------------------------------------------------------
# sample spaces
# ---------------------------------------------------------------------------
def _elements(space: dict[str, Any]) -> list:
    if "elements" in space:
        return list(space["elements"])
    n = int(space["n"])
    return list(range(1, n + 1))


def space_size(space: dict[str, Any]) -> int:
    st = space["structure"]
    if st == "product":
        return math.prod(len(s) for s in space["sets"])
    els = _elements(space)
    n, k = len(els), int(space.get("k", len(els)))
    if st == "permutation":
        return math.perm(n, k)
    if st == "combination":
        return math.comb(n, k)
    if st == "sequence":
        return n ** k
    if st == "multiset_combination":
        return math.comb(n + k - 1, k)
    if st == "arrangement_all":
        return math.factorial(n)
    raise ValueError(f"unknown structure {st}")


def iterate_space(space: dict[str, Any]) -> Iterable[tuple]:
    st = space["structure"]
    if st == "product":
        return itertools.product(*[list(s) for s in space["sets"]])
    els = _elements(space)
    k = int(space.get("k", len(els)))
    if st == "permutation":
        return itertools.permutations(els, k)
    if st == "combination":
        return itertools.combinations(els, k)
    if st == "sequence":
        return itertools.product(els, repeat=k)
    if st == "multiset_combination":
        return itertools.combinations_with_replacement(els, k)
    if st == "arrangement_all":
        return itertools.permutations(els)
    raise ValueError(f"unknown structure {st}")


def sample_space(space: dict[str, Any], rng: random.Random) -> tuple:
    st = space["structure"]
    if st == "product":
        return tuple(rng.choice(list(s)) for s in space["sets"])
    els = _elements(space)
    k = int(space.get("k", len(els)))
    if st in ("permutation", "arrangement_all"):
        return tuple(rng.sample(els, k))
    if st == "combination":
        return tuple(sorted(rng.sample(els, k), key=els.index))
    if st == "sequence":
        return tuple(rng.choice(els) for _ in range(k))
    if st == "multiset_combination":
        return tuple(sorted(rng.choices(els, k=k), key=els.index))
    raise ValueError(st)


# ---------------------------------------------------------------------------
def count_exact(space: dict[str, Any], predicate: str) -> int:
    fn = compile_predicate(predicate)
    return sum(1 for t in iterate_space(space) if fn(t))


def _count_worker(space, predicate):
    return count_exact(space, predicate)


def _mc_worker(space, predicate, n, seed):
    fn = compile_predicate(predicate)
    rng = random.Random(seed)
    hits = 0
    for _ in range(n):
        if fn(sample_space(space, rng)):
            hits += 1
    return hits


def certify_count(space: dict[str, Any], predicate: str, claimed: int, seed: int = 0, timeout: float = 60.0
                  ) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"space": space, "predicate": predicate, "claimed": claimed}
    try:
        size = space_size(space)
    except Exception as e:  # noqa: BLE001
        ev["error"] = f"space: {e}"
        return None, ev
    ev["space_size"] = size
    try:
        compile_predicate(predicate)
    except PredicateError as e:
        ev["error"] = f"predicate: {e}"
        return None, ev
    if size <= ENUM_CAP:
        r = sb_run("mathverify.certify.combinatorics:_count_worker", space, predicate, timeout=timeout)
        if not r.ok:
            ev["error"] = r.error
            ev["flags"] = r.flags
            return None, ev
        ev["count"] = r.value
        ev["method"] = "exhaustive"
        return (r.value == int(claimed)), ev
    # too big: Monte Carlo can only refute
    r = sb_run("mathverify.certify.combinatorics:_mc_worker", space, predicate, MC_SAMPLES, seed, timeout=timeout)
    if not r.ok:
        ev["error"] = r.error
        return None, ev
    p_hat = r.value / MC_SAMPLES
    p_claim = int(claimed) / size
    sigma = math.sqrt(max(p_hat * (1 - p_hat), 1e-9) / MC_SAMPLES)
    ev.update({"method": "monte_carlo", "p_hat": p_hat, "p_claim": p_claim, "sigma": sigma})
    if abs(p_hat - p_claim) > 8 * sigma + 1e-4:
        ev["reason"] = "monte_carlo_refutes"
        return False, ev
    ev["reason"] = "space_too_large_for_certificate"
    return None, ev


def certify_probability(space: dict[str, Any], event: str, claimed, seed: int = 0, timeout: float = 60.0
                        ) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"space": space, "event": event, "claimed": str(claimed)}
    # The claim is compared AS STATED. `nsimplify` used to run here and it snaps to the nearest
    # "nice" number: 500000003/3000000000 became 1/6 and was certified against an exact
    # enumeration of 1/6 (measured). Decimal claims keep their own precision through
    # answers_equivalent's float floor; exact claims are compared exactly.
    c = sp.sympify(claimed)
    try:
        cf = float(c)
    except Exception:
        ev["error"] = "claimed_probability_not_numeric"
        return None, ev
    if cf < 0 or cf > 1:
        ev["reason"] = "probability_out_of_[0,1]"
        return False, ev
    try:
        size = space_size(space)
    except Exception as e:  # noqa: BLE001
        ev["error"] = f"space: {e}"
        return None, ev
    ev["space_size"] = size
    if size <= ENUM_CAP:
        r = sb_run("mathverify.certify.combinatorics:_count_worker", space, event, timeout=timeout)
        if not r.ok:
            ev["error"] = r.error
            ev["flags"] = r.flags
            return None, ev
        p = Rational(r.value, size)
        ev.update({"favourable": r.value, "probability": str(p), "method": "exhaustive"})
        ok, cev = answers_equivalent(c, p, shape="scalar")
        ev["compare"] = cev
        return ok, ev
    r = sb_run("mathverify.certify.combinatorics:_mc_worker", space, event, MC_SAMPLES, seed, timeout=timeout)
    if not r.ok:
        ev["error"] = r.error
        return None, ev
    p_hat = r.value / MC_SAMPLES
    sigma = math.sqrt(max(p_hat * (1 - p_hat), 1e-9) / MC_SAMPLES)
    ev.update({"method": "monte_carlo", "p_hat": p_hat, "sigma": sigma})
    if abs(p_hat - cf) > 8 * sigma + 1e-4:
        ev["reason"] = "monte_carlo_refutes"
        return False, ev
    ev["reason"] = "space_too_large_for_certificate"
    return None, ev


def verify(ir, solution, ctx: Ctx):
    kind = ir.task.kind
    if kind not in ("count_structures", "probability"):
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        space = p.get("space")
        if not isinstance(space, dict):
            return unknown(LAYER, "no_space")
        if kind == "count_structures":
            ca = solution.claimed_answer
            try:
                raw = ca.payload if ca.kind == "count" else ctx.claimed(solution)
            except Exception as e:  # noqa: BLE001
                return unknown(LAYER, f"claimed_not_parsed: {e}", flags=["parse_error"])
            # `int()` truncated a claimed 241/2 to 120 and certified it (measured); a count that
            # is not an integer is a wrong count
            claimed = exact_integer(raw)
            if claimed is None:
                return result(LAYER, "fail", 0.99, True, {"claimed": str(raw),
                              "reason": "claimed_count_is_not_an_integer"}, t.ms, primary=True)
            ok, ev = certify_count(space, p.get("predicate", ""), claimed, seed=ctx.seed)
        else:
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            ok, ev = certify_probability(space, p.get("event", ""), claimed, seed=ctx.seed)
    conf = 0.99 if ev.get("method") == "exhaustive" else 0.95
    if ok is True:
        return result(LAYER, "pass", conf, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", conf, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("reason", ev.get("error", "undecided")), t.ms, ev, flags=ev.get("flags", []))
