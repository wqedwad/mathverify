"""Part (v-b A) of the 30 Sep 2026 fixes (HANDOFF V16, DECISIONS §73 "Açık kalanlar"): the set and parser
items of V16.

    K  SymPy's set `+`/`-` build Union/Complement without the endpoint unification of `_set_op`: with
       R = sqrt(11 + 6*sqrt(2)) - sqrt(2) (= 3), Interval.open(-oo, R) + Interval.open(3, oo) was the whole
       line, so it was CORRECT as the domain of x + 1;
    F  `normalize_set` sorted intervals by `float`: two starts 1e-40 apart tie, and an interval listed
       first could swallow the one before it (a subinterval dropped);
    B  a Sum/Product bound that is a constant but not a number (sqrt(1)) escaped the AST check of reversed
       ranges, and floor/ceiling computed the Karr value at once (floor(Σ_{k=3}^{sqrt(1)} k) = -2);
    S  a sum with a symbolic bound whose GIVEN value reverses the range took the Karr value
       (Σ_{k=1}^{n} k with n = -2 is 1). Open after this part: its place is the definedness of the
       binder (certify.domain._range_conditions, another part's file), so the S rows stay "BAD";
    G  the gcd/lcm "not a value" check (GCD-10) was skipped for a payload written as a list;
    U  (coverage) more than 300 constant endpoints were not read, rationals included. Kept: the limit also
       bounds the size of a set written as text (SymPy's Union of 350 intervals took 21 s to build), see
       equiv.sets.unify_endpoints; the U rows record the limit as it stands.

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca7a/sonda.py [out.json] [group ...]

Lean is not needed (MATHVERIFY_LEAN_REPL=/nonexistent). Kept out of pyflakes and pytest like the rest
of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
BAD = {"INCORRECT", "UNKNOWN"}        # anything but a false accept
NOTBAD = {"CORRECT", "UNKNOWN"}       # anything but a false reject
UNK = {"UNKNOWN"}


def _ir(kind, params, vars_=(), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [dict(s, text="") for s in steps]}


def _st(i, kind, claim, frm=()):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": list(frm)}


X = [{"name": "x"}]
R = "(sqrt(11 + 6*sqrt(2)) - sqrt(2))"          # = 3
R_NEAR = "sqrt(9 + exp(-10000))"                # > 3, not decided


def cases_k():
    dom = lambda e: _ir("domain_of", {"expr": e, "var": "x"}, X, shape="set")  # noqa: E731
    ineq = _ir("solve_inequality", {"var": "x"}, X, ["x**2 + 1 > 0"], "interval")
    s = lambda p: _sol(p, "set")  # noqa: E731
    return [
        ("x + 1: (-oo, R) + (3, oo)", dom("x + 1"), s(f"Interval.open(-oo, {R}) + Interval.open(3, oo)"), NO),
        ("x + 1: (-oo, 3) + (R, oo)", dom("x + 1"), s(f"Interval.open(-oo, 3) + Interval.open({R}, oo)"), NO),
        ("x + 1: Reals - [R, 3]", dom("x + 1"), s(f"Reals - Interval({R}, 3)"), NO),
        ("x + 1: S.Reals - [3, R]", dom("x + 1"), s(f"S.Reals - Interval(3, {R})"), NO),
        ("x + 1: [4, oo) + ((-oo, R) + (3, 4))", dom("x + 1"),
         s(f"Interval(4, oo) + (Interval.open(-oo, {R}) + Interval.open(3, 4))"), NO),
        ("x + 1: (-oo, R) + {3 + 1} + (3, oo) (Python set)", dom("x + 1"),
         s(f"Interval.open(-oo, {R}) + {{3 + 1}} + Interval.open(3, oo)"), NO),
        ("x + 1: (-oo, R) + {7} + (3, oo)", dom("x + 1"), s(f"Interval.open(-oo, {R}) + FiniteSet(7) + Interval.open(3, oo)"), NO),
        ("x + 1: Union((-oo, R), (3, 5)) + [5, oo)", dom("x + 1"),
         s(f"Union(Interval.open(-oo, {R}), Interval.open(3, 5)) + Interval(5, oo)"), NO),
        ("sqrt(x)sqrt(5-x): [0, R) + (3, 5]", dom("sqrt(x)*sqrt(5 - x)"),
         s(f"Interval.Ropen(0, {R}) + Interval.Lopen(3, 5)"), NO),
        ("x^2 + 1 > 0: (-oo, 3) + (R, oo)", ineq, _sol(f"Interval.open(-oo, 3) + Interval.open({R}, oo)", "interval"), NO),
        ("x + 1: (-oo, 3) + (R', oo), R' undecided", dom("x + 1"),
         s(f"Interval.open(-oo, 3) + Interval.open({R_NEAR}, oo)"), BAD),
        ("1/(x-3): (-oo, 3) + (R', oo), R' undecided", dom("1/(x - 3)"),
         s(f"Interval.open(-oo, 3) + Interval.open({R_NEAR}, oo)"), UNK),
        # controls: right answers written with + and -
        ("control 1/(x-3): (-oo, R) + (3, oo)", dom("1/(x - 3)"), s(f"Interval.open(-oo, {R}) + Interval.open(3, oo)"), OK),
        ("control 1/(x-3): Reals - {3}", dom("1/(x - 3)"), s("Reals - FiniteSet(3)"), OK),
        ("control 1/(x-3): Reals - {R}", dom("1/(x - 3)"), s(f"Reals - FiniteSet({R})"), OK),
        ("control x + 1: (-oo, 3) + [3, oo)", dom("x + 1"), s("Interval.open(-oo, 3) + Interval(3, oo)"), OK),
        ("control x + 1: (-oo, R) + [3, oo)", dom("x + 1"), s(f"Interval.open(-oo, {R}) + Interval(3, oo)"), OK),
        ("control x + 1: Reals - EmptySet", dom("x + 1"), s("Reals - EmptySet"), OK),
        ("control sqrt(x): [0, 1) + [1, oo)", dom("sqrt(x)"), s("Interval.Ropen(0, 1) + Interval(1, oo)"), OK),
        ("control sqrt(x): [0, 1) + (1, oo)", dom("sqrt(x)"), s("Interval.Ropen(0, 1) + Interval.open(1, oo)"), NO),
        ("control 1/(x-3): (-oo, 3) U (3, oo)", dom("1/(x - 3)"), s("(-oo, 3) U (3, oo)"), OK),
    ]


Q = "sqrt(2)"
E40 = "10**(-40)"


def cases_f():
    ineq = lambda g: _ir("solve_inequality", {"var": "x"}, X, [g], "interval")  # noqa: E731
    i1 = ineq(f"(x - {Q})*(x - 5) < 0")                           # (sqrt(2), 5)
    i2 = ineq(f"(x - {Q} - 2*{E40})*(x - 5) < 0")                 # (sqrt(2) + 2e-40, 5)
    d1 = _ir("domain_of", {"expr": f"1/sqrt((x - {Q})*(5 - x))", "var": "x"}, X, shape="set")
    d2 = _ir("domain_of", {"expr": f"1/sqrt((x - {Q} - 2*{E40})*(5 - x))", "var": "x"}, X, shape="set")
    return [
        ("domain (sqrt2, 5): [sqrt2 - 2e, sqrt2 - e) U (sqrt2, 5)", d1,
         _sol(f"[{Q} - 2*{E40}, {Q} - {E40}) U ({Q}, 5)", "set"), NO),
        ("domain (sqrt2 + 2e, 5): [sqrt2, sqrt2 + e) U (sqrt2 + 2e, 5)", d2,
         _sol(f"[{Q}, {Q} + {E40}) U ({Q} + 2*{E40}, 5)", "set"), NO),
        ("control domain (sqrt2, 5): (sqrt2, 5)", d1, _sol(f"({Q}, 5)", "set"), OK),
        ("control domain (sqrt2 + 2e, 5): (sqrt2 + 2e, 5)", d2, _sol(f"({Q} + 2*{E40}, 5)", "set"), OK),
        ("(sqrt2, 5): [sqrt2 - 2e, sqrt2 - e) U (sqrt2, 5)", i1,
         _sol(f"[{Q} - 2*{E40}, {Q} - {E40}) U ({Q}, 5)", "interval"), NO),
        ("(sqrt2 + 2e, 5): [sqrt2, sqrt2 + e) U (sqrt2 + 2e, 5)", i2,
         _sol(f"[{Q}, {Q} + {E40}) U ({Q} + 2*{E40}, 5)", "interval"), NO),
        ("control (sqrt2, 5): (sqrt2, 5)", i1, _sol(f"({Q}, 5)", "interval"), OK),
        ("control (sqrt2 + 2e, 5): (sqrt2 + 2e, 5)", i2, _sol(f"({Q} + 2*{E40}, 5)", "interval"), OK),
        ("control (sqrt2, 5): (sqrt2, 3) U [3, 5)", i1, _sol(f"({Q}, 3) U [3, 5)", "interval"), OK),
        ("control (sqrt2, 5): (sqrt2, 3) U (3, 5)", i1, _sol(f"({Q}, 3) U (3, 5)", "interval"), NO),
    ]


KI = [{"name": "k", "domain": "integer"}]


def cases_b():
    ev = lambda e, v=KI: _ir("evaluate", {"expr": e}, v)  # noqa: E731
    sq = _ir("evaluate", {"expr": "x**2"}, [{"name": "x", "domain": "real"}], ["x = 2"])
    return [
        ("floor(Sum(k, (k, 3, sqrt(1)))): -2", ev("floor(Sum(k, (k, 3, sqrt(1))))"), _sol("-2"), UNK),
        ("ceiling(Sum(k, (k, 3, sqrt(1)))): -2", ev("ceiling(Sum(k, (k, 3, sqrt(1))))"), _sol("-2"), UNK),
        ("floor(Sum(k, (k, 3, sqrt(4) - 1))): -2", ev("floor(Sum(k, (k, 3, sqrt(4) - 1)))"), _sol("-2"), UNK),
        ("floor(Sum(k, (k, sqrt(9), 1))): -2", ev("floor(Sum(k, (k, sqrt(9), 1)))"), _sol("-2"), UNK),
        ("floor(Sum(k, (k, 3, exp(0)))): -2", ev("floor(Sum(k, (k, 3, exp(0))))"), _sol("-2"), UNK),
        ("floor(Sum(k, (k, 3, Abs(-1)))): -2", ev("floor(Sum(k, (k, 3, Abs(-1))))"), _sol("-2"), UNK),
        ("floor(Sum(k, (k, 3, log(E)))): -2", ev("floor(Sum(k, (k, 3, log(E))))"), _sol("-2"), UNK),
        ("floor(Product(k, (k, 3, sqrt(1)))): 0", ev("floor(Product(k, (k, 3, sqrt(1))))"), _sol("0"), UNK),
        ("floor(Sum(k, (k, 1, sqrt(1)/2))): non-integer apart", ev("floor(Sum(k, (k, 1, sqrt(1)/2)))"), _sol("0"), UNK),
        ("floor(Sum(k, (k, 1, sqrt(2)))): non-integer apart", ev("floor(Sum(k, (k, 1, sqrt(2))))"), _sol("1"), BAD),
        ("LaTeX lfloor sum_{k=3}^{sqrt 1} k rfloor: -2", ev(r"\left\lfloor \sum_{k=3}^{\sqrt{1}} k \right\rfloor"),
         _sol("-2"), UNK),
        ("step compute floor(Sum(k, (k, 3, sqrt(1)))) = -2", sq,
         _sol("4", steps=[_st(1, "compute", "floor(Sum(k, (k, 3, sqrt(1)))) = -2")]), BAD | OK),
        # controls: a constant bound that is right way round
        ("control floor(Sum(k, (k, 1, sqrt(9)))): 6", ev("floor(Sum(k, (k, 1, sqrt(9))))"), _sol("6"), OK),
        ("control floor(Sum(k/2, (k, 1, sqrt(4)))): 1", ev("floor(Sum(k/2, (k, 1, sqrt(4))))"), _sol("1"), OK),
        ("control floor(Sum(k/2, (k, 1, sqrt(4)))): 2", ev("floor(Sum(k/2, (k, 1, sqrt(4))))"), _sol("2"), NO),
        ("control Sum(k, (k, 1, sqrt(9))): 6", ev("Sum(k, (k, 1, sqrt(9)))"), _sol("6"), OK),
        ("control floor(Sum(k, (k, 3, 2))): empty 0", ev("floor(Sum(k, (k, 3, sqrt(4))))"), _sol("0"), NOTBAD),
        ("control floor(Sum(k, (k, 3, 1))): -2 (numbers)", ev("floor(Sum(k, (k, 3, 1)))"), _sol("-2"), UNK),
    ]


KN = [{"name": "k", "domain": "integer"}, {"name": "n", "domain": "integer"}]


def cases_s():
    ev = lambda e, g, v=KN: _ir("evaluate", {"expr": e}, v, g)  # noqa: E731
    ss = lambda g, v=KN: _ir("series_sum", {"term": "k", "var": "k", "lo": "1", "hi": "n"}, v, g)  # noqa: E731
    sq = _ir("evaluate", {"expr": "n**2"}, KN, ["n = -2"])
    return [
        ("Sum(k, (k, 1, n)), n = -2: 1 (Karr)", ev("Sum(k, (k, 1, n))", ["n = -2"]), _sol("1"), UNK),
        ("Sum(k, (k, 1, n)), n = -2: 0 (empty)", ev("Sum(k, (k, 1, n))", ["n = -2"]), _sol("0"), UNK),
        ("Sum(k, (k, 1, n)), n undeclared = -2: 1", ev("Sum(k, (k, 1, n))", ["n = -2"], KI + [{"name": "n"}]),
         _sol("1"), UNK),
        ("Sum(k, (k, n, 1)), n = 4: -5 (Karr)", ev("Sum(k, (k, n, 1))", ["n = 4"]), _sol("-5"), UNK),
        ("floor(Sum(k, (k, 3, n))), n = 1: -2", ev("floor(Sum(k, (k, 3, n)))", ["n = 1"]), _sol("-2"), UNK),
        ("Product(k, (k, 3, n)), n = 0: 1/2 (Karr)", ev("Product(k, (k, 3, n))", ["n = 0"]), _sol("1/2"), UNK),
        ("Sum(k, (k, 1, n + 1)), n = -4: 3 (Karr)", ev("Sum(k, (k, 1, n + 1))", ["n = -4"]), _sol("3"), UNK),
        ("Sum(k, (k, 1, n)) + 0, n + 2 = 0: 1", ev("Sum(k, (k, 1, n))", ["n + 2 = 0"]), _sol("1"), UNK),
        ("series_sum 1..n, n = -2: 1", ss(["n = -2"]), _sol("1"), UNK),
        ("series_sum 1..n, n = -2: 0", ss(["n = -2"]), _sol("0"), UNK),
        ("step compute Sum(k, (k, 1, n)) = 1, n = -2", sq,
         _sol("4", steps=[_st(1, "compute", "Sum(k, (k, 1, n)) = 1")]), BAD | OK),
        # controls
        ("control Sum(k, (k, 1, n)), n = 3: 6", ev("Sum(k, (k, 1, n))", ["n = 3"]), _sol("6"), OK),
        ("control Sum(k, (k, 1, n)), n = 3: 5", ev("Sum(k, (k, 1, n))", ["n = 3"]), _sol("5"), NO),
        ("control Sum(k, (k, 1, n)), n = 0: 0 (empty, hi = lo - 1)", ev("Sum(k, (k, 1, n))", ["n = 0"]), _sol("0"), NOTBAD),
        ("control series_sum 1..n, n = 3: 6", ss(["n = 3"]), _sol("6"), NOTBAD),
        ("control series_sum 1..n, n = 3: 5", ss(["n = 3"]), _sol("5"), BAD),
        ("control Sum(k, (k, 1, n)), n positive_integer = 3: 6",
         ev("Sum(k, (k, 1, n))", ["n = 3"], KI + [{"name": "n", "domain": "positive_integer"}]), _sol("6"), OK),
    ]


def cases_g():
    eq = _ir("solve_equation", {"var": "x", "equation": "x - 12 = 0"}, X, shape="set")
    ev = _ir("evaluate", {"expr": "gcd(84, 120)"}, shape="set")
    lst = lambda *p: _sol(list(p), "set")  # noqa: E731
    return [
        ("x - 12 = 0: [gcd(84, 120)]", eq, lst("gcd(84, 120)"), UNK),
        ("x - 12 = 0: [gcd(120, 84)]", eq, lst("gcd(120, 84)"), UNK),
        ("x - 12 = 0: [igcd(84, 120)]", eq, lst("igcd(84, 120)"), UNK),
        ("x - 12 = 0: [\\gcd(84, 120)]", eq, lst(r"\gcd(84, 120)"), UNK),
        ("x - 12 = 0: [lcm(4, 6)]", eq, lst("lcm(4, 6)"), UNK),
        ("x - 12 = 0: [\\operatorname{lcm}(4, 6)]", eq, lst(r"\operatorname{lcm}(4, 6)"), UNK),
        ("evaluate gcd(84, 120), set: [gcd(120, 84)]", ev, lst("gcd(120, 84)"), UNK),
        # controls
        ("control x - 12 = 0: '{gcd(84, 120)}' (text)", eq, _sol("{gcd(84, 120)}", "set"), UNK),
        ("control x - 12 = 0: [12]", eq, lst("12"), OK),
        ("control x - 12 = 0: [13]", eq, lst("13"), NO),
        ("control evaluate gcd(84, 120), set: [12]", ev, lst("12"), NOTBAD),
    ]


def cases_u():
    ineq = _ir("solve_inequality", {"var": "x"}, X, ["sin(pi*x) != 0", "x > 0", "x < 321"], "set")
    many = " U ".join(f"({i}, {i + 1})" for i in range(0, 321))
    many_q = " U ".join(f"({i}/2, {i + 1}/2)" for i in range(0, 642))
    return [
        ("321 rational intervals (0..321 minus integers)", ineq, _sol(many, "set"), UNK),
        ("642 rational half-intervals", ineq, _sol(many_q, "set"), UNK),
    ]


GROUPS = {"K": cases_k, "F": cases_f, "B": cases_b, "S": cases_s, "G": cases_g, "U": cases_u}


def _summ(r):
    lay, steps = [], []
    for l in r.layers:
        ev = l.evidence or {}
        reason = ev.get("reason") or ev.get("why") or ev.get("error") or ev.get("method") or ""
        lay.append(f"{l.layer}:{l.verdict}{'(' + str(reason)[:140] + ')' if reason else ''}")
        if l.layer == "steps.refute":
            for s in ev.get("steps", []):
                steps.append(f"{s.get('id')}:{s.get('status')}:"
                             f"{str(s.get('reason') or (s.get('evidence') or {}).get('reason') or '')[:80]}")
    return lay, steps


# A step case also fails when a step the verifier should not prove is "verified".
STEP_NOT_VERIFIED = {"step compute floor(Sum(k, (k, 3, sqrt(1)))) = -2", "step compute Sum(k, (k, 1, n)) = 1, n = -2"}


def parse_level():
    """Set parses measured directly: the coverage limit (U) and the order of normalize_set (F)."""
    from mathverify.normalize.parse import _SAFE_NAMES, ParseError, parse_set_str
    from mathverify.equiv.sets import normalize_set
    import sympy as sp
    rows, bad = [], 0
    ns = dict(_SAFE_NAMES)
    for label, text, want in [
        ("U parse 300 integers", "{" + ", ".join(str(i) for i in range(300)) + "}", "read"),
        ("U parse 400 integers", "{" + ", ".join(str(i) for i in range(400)) + "}", "refused"),
        ("U parse 350 rational intervals", " U ".join(f"({2 * i}/3, {2 * i + 1}/3)" for i in range(350)), "refused"),
        ("U parse 350 integers + sqrt(2)", "{" + ", ".join(str(i) for i in range(350)) + ", sqrt(2)}", "refused"),
        ("U parse 301 irrationals", "{" + ", ".join(f"sqrt({p})" for p in [q for q in range(2, 1000)
                                                                           if not sp.sqrt(q).is_Integer][:301]) + "}",
         "refused"),
    ]:
        t0 = time.perf_counter()
        try:
            s = parse_set_str(text, ns)
            got = "read"
            info = f"{type(s).__name__}, {len(s.args)} args"
        except ParseError as e:
            got, info = "refused", str(e)[:100]
        ok = got == want
        bad += not ok
        rows.append({"group": "U", "label": label, "verdict": got, "expected": [want], "ok": ok, "layers": [info]})
        print(f"U | {'ok ' if ok else 'BAD'} | {got:9s} (exp {want}) | {time.perf_counter() - t0:5.1f}s | {label} [{info}]",
              flush=True)
    e = sp.Rational(1, 10**40)
    q = sp.sqrt(2)
    for label, a, b in [("F normalize [q - 2e, q - e) U (q, 5)", sp.Interval.Ropen(q - 2 * e, q - e), sp.Interval.open(q, 5)),
                        ("F normalize [q, q + e) U (q + 2e, 5)", sp.Interval.Ropen(q, q + e), sp.Interval.open(q + 2 * e, 5))]:
        n = normalize_set(sp.Union(a, b))
        got = "2 intervals" if n is not None and len(n[0]) == 2 else f"{n}"[:100]
        ok = got == "2 intervals"
        bad += not ok
        rows.append({"group": "F", "label": label, "verdict": got, "expected": ["2 intervals"], "ok": ok, "layers": []})
        print(f"F | {'ok ' if ok else 'BAD'} | {got} | {label}", flush=True)
    return rows, bad


def main():
    import mathverify
    from mathverify.verifier import verify
    print(f"mathverify: {mathverify.__file__}", flush=True)
    out_path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".json") else None
    only = {a for a in sys.argv[1:] if not a.endswith(".json")}
    rows, bad = [], 0
    for g, fn in GROUPS.items():
        if only and g not in only:
            continue
        for label, ir, sol, exp in fn():
            t0 = time.perf_counter()
            try:
                r = verify(ir, sol)
                v = r.verdict
                lay, steps = _summ(r)
            except Exception as e:  # noqa: BLE001
                v, lay, steps = f"EXC {type(e).__name__}: {e}"[:200], [], []
            ok = v in exp
            if label in STEP_NOT_VERIFIED and any(":verified:" in s for s in steps):
                ok = False
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": v, "expected": sorted(exp), "ok": ok,
                         "layers": lay, "steps": steps})
            print(f"{g} | {'ok ' if ok else 'BAD'} | {v:9s} (exp {'/'.join(sorted(exp))}) | "
                  f"{time.perf_counter() - t0:5.1f}s | {label}", flush=True)
            if not ok:
                for x in lay:
                    print(f"      layer {x}", flush=True)
            for x in steps:
                print(f"      step {x}", flush=True)
    if not only or only & {"U", "F"}:
        prow, pbad = parse_level()
        rows += prow
        bad += pbad
    print(f"\n{len(rows)} cases, {bad} not as expected")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
