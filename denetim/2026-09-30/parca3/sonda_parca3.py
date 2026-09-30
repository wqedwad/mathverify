"""Part (iii) of the N1-N9 re-run (DECISIONS §75): N7 (a parameter of `solve_equation` bound by a
given) and V15 S1 (a `compute` step whose symbols the givens fix). Every case of N7 from
denetim/2026-09-30/n19/sonda_n19.py, the wrong sets that must never be accepted, the given shapes
the z3 layer must not ignore, and the three S1 variants of the second audit round
(denetim/2026-09-29/v14/bulgular/tur2_bc967af.json -> attack:functions, id S1).

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca3/sonda_parca3.py [out.json]

Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
BAD = {"INCORRECT", "UNKNOWN"}        # anything but a false accept
NOTBAD = {"CORRECT", "UNKNOWN"}       # anything but a false reject

XA = [{"name": "x", "domain": "real"}, {"name": "a", "domain": "real"}]
XY = [{"name": "x", "domain": "real"}, {"name": "y", "domain": "real"}]
XB = [{"name": "x", "domain": "real"}, {"name": "b", "domain": "real"}]
XBC = [{"name": "x", "domain": "real", "constraints": ["x > b"]}, {"name": "b", "domain": "real"}]


def _eq(equation, var, vars_, givens):
    return {"task": {"kind": "solve_equation", "params": {"equation": equation, "var": var}},
            "vars": vars_, "givens": list(givens), "answer_shape": "set"}


def _set(payload, steps=()):
    return {"claimed_answer": {"kind": "set", "payload": payload}, "steps": list(steps)}


def _st(i, kind, claim, frm=()):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": list(frm), "text": ""}


def cases_n7():
    a4 = _eq("x**2 = a", "x", XA, ["a = 4"])
    ai = _eq("x**2 = a", "x", XA, ["a = integrate(2*x, (x, 0, 2))"])
    sq = _eq("sqrt(y - x) = 2", "y", XY, ["x = 1"])
    return [
        # the audit's three right answers
        ("N7 x^2=a, a=4, {-2,2}", a4, _set("{-2, 2}"), OK),
        ("N7 x^2=a, a=integrate(2x,(x,0,2)), {-2,2}", ai, _set("{-2, 2}"), OK),
        ("N7 sqrt(y-x)=2, x=1, {5}", sq, _set("{5}"), OK),
        # wrong sets: never CORRECT, INCORRECT where the z3 layer can now decide
        ("N7 a=4 {2}", a4, _set("{2}"), NO),
        ("N7 a=4 {-2,2,3}", a4, _set("{-2, 2, 3}"), NO),
        ("N7 a=4 {4}", a4, _set("{4}"), NO),
        ("N7 a=4 {-4,4}", a4, _set("{-4, 4}"), NO),
        ("N7 a=4 {}", a4, _set("{}"), NO),
        ("N7 integrate {2}", ai, _set("{2}"), NO),
        ("N7 integrate {4}", ai, _set("{4}"), NO),
        ("N7 sqrt {3}", sq, _set("{3}"), NO),
        ("N7 sqrt {4,5}", sq, _set("{4, 5}"), NO),
        # the binding written the other way round, and a parameter bound to a non-integer
        ("bind 4 = a {-2,2}", _eq("x**2 = a", "x", XA, ["4 = a"]), _set("{-2, 2}"), OK),
        ("bind a=9/4 {-3/2,3/2}", _eq("x**2 = a", "x", XA, ["a = 9/4"]), _set("{-3/2, 3/2}"), OK),
        ("bind a=9/4 {3/2}", _eq("x**2 = a", "x", XA, ["a = 9/4"]), _set("{3/2}"), NO),
        # a given the z3 layer used to ignore must now rule the model out (was it a false accept?)
        ("x^2+a^2=0, a=4, {0}", _eq("x**2 + a**2 = 0", "x", XA, ["a = 4"]), _set("{0}"), NO),
        ("x^2+a^2=0, a=0, {0}", _eq("x**2 + a**2 = 0", "x", XA, ["a = 0"]), _set("{0}"), OK),
        ("x=a+1 (lin), a=2, {3}", _eq("x - a = 1", "x", XA, ["a = 2"]), _set("{3}"), OK),
        ("x=a+1 (lin), a=2, {0}", _eq("x - a = 1", "x", XA, ["a = 2"]), _set("{0}"), NO),
        # givens the binding rule does not cover: the z3 layer must not decide with them ignored
        ("mixed x > a-4, a=4, {-2,2}", _eq("x**2 = a", "x", XA, ["a = 4", "x > a - 4"]), _set("{-2, 2}"), BAD),
        ("mixed x > a-4, a=4, {2}", _eq("x**2 = a", "x", XA, ["a = 4", "x > a - 4"]), _set("{2}"), NOTBAD),
        ("a^2=16 (not a binding), {-2,2}", _eq("x**2 = a", "x", XA, ["a**2 = 16"]), _set("{-2, 2}"), BAD),
        ("a+1=5 (not a binding), {-2,2}", _eq("x**2 = a", "x", XA, ["a + 1 = 5"]), _set("{-2, 2}"), NOTBAD),
        ("a > 0 only, {-2,2}", _eq("x**2 = a", "x", XA, ["a > 0"]), _set("{-2, 2}"), BAD),
        ("two bindings a=4, a=9, {-2,2}", _eq("x**2 = a", "x", XA, ["a = 4", "a = 9"]), _set("{-2, 2}"), BAD),
        ("x = 2 given (var bound), {-2,2}", _eq("x**2 = 4", "x", [XA[0]], ["x = 2"]), _set("{-2, 2}"), NOTBAD),
        # a free parameter no given binds (pre-existing: the root check is existential)
        ("free a, x^2+a^2=0, {0}", _eq("x**2 + a**2 = 0", "x", XA, []), _set("{0}"), BAD),
        ("free a, x^2=a, {-2,2}", _eq("x**2 = a", "x", XA, []), _set("{-2, 2}"), BAD),
        ("a >= 0, x^2+a^2=0, {0}", _eq("x**2 + a**2 = 0", "x", XA, ["a >= 0"]), _set("{0}"), BAD),
        # a parameter of a constraint on the variable (the constraint, a given, the domain of discourse)
        ("x^2=4, var constraint x > b, b=0, {-2,2}", _eq("x**2 = 4", "x", XBC, ["b = 0"]), _set("{-2, 2}"), BAD),
        ("x^2=4, var constraint x > b, b=0, {2}", _eq("x**2 = 4", "x", XBC, ["b = 0"]), _set("{2}"), NOTBAD),
        ("x^2=4, given x > b, b=0, {-2,2}", _eq("x**2 = 4", "x", XB, ["x > b", "b = 0"]), _set("{-2, 2}"), BAD),
        ("x^2=4, given x > b, b=0, {2}", _eq("x**2 = 4", "x", XB, ["x > b", "b = 0"]), _set("{2}"), NOTBAD),
        ("x^2=4, dod x > b, b=0, {-2,2}", dict(_eq("x**2 = 4", "x", XB, ["b = 0"]), domain_of_discourse="x > b"),
         _set("{-2, 2}"), BAD),
        # the equation as the first given, next to the binding (the evalset writes it this way)
        ("eq in givens, a=4, {-2,2}",
         {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": XA,
          "givens": ["x**2 = a", "a = 4"], "answer_shape": "set"}, _set("{-2, 2}"), OK),
        ("eq in givens, a=4, {2}",
         {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": XA,
          "givens": ["x**2 = a", "a = 4"], "answer_shape": "set"}, _set("{2}"), NO),
    ]


def cases_s1():
    ab = [{"name": "a"}, {"name": "b"}]
    tur = {"task": {"kind": "evaluate", "params": {"expr": "f(2)"}}, "vars": ab,
           "functions": [{"name": "f", "expr": "x**3 + a*x**2 + b*x", "args": ["x"], "params": ["a", "b"]}],
           "givens": ["at(diff(f(x), x), x, 1) = 0", "f(1) = -3"], "answer_shape": "scalar"}
    plain = {"task": {"kind": "evaluate", "params": {"expr": "a*b"}}, "vars": ab,
             "givens": ["a + b = 5", "a - b = 1"], "answer_shape": "scalar"}
    lin = {"task": {"kind": "evaluate", "params": {"expr": "f(4)"}}, "vars": ab,
           "functions": [{"name": "f", "expr": "a*x + b", "args": ["x"], "params": ["a", "b"]}],
           "givens": ["a + b = 5", "a - b = 1"], "answer_shape": "scalar"}
    s_tur = [_st(1, "eq", "3 + 2*a + b = 0"), _st(2, "eq", "1 + a + b = -3"), _st(3, "eq", "a = 1", ["s1", "s2"]),
             _st(4, "eq", "b = -5", ["s3"])]
    s_ab = [_st(1, "eq", "a = 3"), _st(2, "eq", "b = 2")]
    val = lambda p, steps: {"claimed_answer": {"kind": "value", "payload": p}, "steps": steps}  # noqa: E731
    return [
        ("S1 ayt-tur-007 compute f(2) = 2", tur, val("2", s_tur + [_st(5, "compute", "f(2) = 2", ["s3", "s4"])]), OK),
        ("S1 ayt-tur-007 eq f(2) = 2 (control)", tur, val("2", s_tur + [_st(5, "eq", "f(2) = 2", ["s3", "s4"])]), OK),
        ("S1 ayt-tur-007 compute 8+4*1+2*(-5)=2", tur,
         val("2", s_tur + [_st(5, "compute", "8 + 4*1 + 2*(-5) = 2", ["s3", "s4"])]), OK),
        ("S1 plain compute a*b = 6", plain, val("6", s_ab + [_st(3, "compute", "a*b = 6", ["s1", "s2"])]), OK),
        ("S1 f=ax+b compute f(4) = 14", lin, val("14", s_ab + [_st(3, "compute", "f(4) = 14", ["s1", "s2"])]), OK),
        # wrong compute values must stay refuted
        ("S1 ayt-tur-007 compute f(2) = 3 (wrong)", tur, val("2", s_tur + [_st(5, "compute", "f(2) = 3", ["s3", "s4"])]), NO),
        ("S1 plain compute a*b = 5 (wrong)", plain, val("6", s_ab + [_st(3, "compute", "a*b = 5", ["s1", "s2"])]), NO),
        ("S1 f=ax+b compute f(4) = 13 (wrong)", lin, val("14", s_ab + [_st(3, "compute", "f(4) = 13", ["s1", "s2"])]), NO),
        # a wrong identity (no given fixes x): must stay refuted
        ("S1 ctrl simplify wrong identity",
         {"task": {"kind": "simplify_expression", "params": {"expr": "(x + 1)**2"}}, "vars": [{"name": "x", "domain": "real"}],
          "givens": [], "answer_shape": "expression"},
         {"claimed_answer": {"kind": "expression", "payload": "x**2 + 2*x + 1"},
          "steps": [_st(1, "compute", "(x + 1)**2 = x**2 + 1")]}, NO),
    ]


GROUPS = {"N7": cases_n7, "S1": cases_s1}


def _summ(r):
    lay, steps = [], []
    for l in r.layers:
        ev = l.evidence or {}
        reason = ev.get("reason") or ev.get("why") or ev.get("error") or ""
        lay.append(f"{l.layer}:{l.verdict}{'(' + str(reason)[:140] + ')' if reason else ''}")
        if l.layer == "steps.refute":
            for s in ev.get("steps", []):
                steps.append(f"{s.get('id')}:{s.get('status')}:{str(s.get('reason') or (s.get('evidence') or {}).get('reason') or '')[:80]}")
    return lay, steps


def main():
    from mathverify.verifier import verify
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    rows, bad = [], 0
    for g, fn in GROUPS.items():
        for label, ir, sol, exp in fn():
            t0 = time.perf_counter()
            try:
                r = verify(ir, sol)
                v = r.verdict
                lay, steps = _summ(r)
            except Exception as e:  # noqa: BLE001
                v, lay, steps = f"EXC {type(e).__name__}: {e}"[:200], [], []
            ok = v in exp
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": v, "expected": sorted(exp), "ok": ok,
                         "layers": lay, "steps": steps})
            print(f"{g} | {'ok ' if ok else 'BAD'} | {v:9s} (exp {'/'.join(sorted(exp))}) | "
                  f"{time.perf_counter() - t0:5.1f}s | {label}", flush=True)
            for x in lay:
                print(f"      {x}", flush=True)
            for x in steps:
                print(f"      step {x}", flush=True)
    print(f"\n{len(rows)} cases, {bad} not as expected")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
