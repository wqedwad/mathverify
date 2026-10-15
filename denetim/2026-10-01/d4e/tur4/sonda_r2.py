"""d4e round 3 attack, second pass (lens: unjust rejection, coverage loss, robustness) on d342778.
    python sonda_r2.py out.json GROUPS [label-substring]
Expected sets: OK (CORRECT), NOTNO (never INCORRECT), NOTOK (never CORRECT), UNK (UNKNOWN only)."""
from __future__ import annotations

import json
import sys
import time

from sonda_rk import OK, NO, NOTOK, NOTNO, UNK, X, XP, T_, K_, NP_, AP_, AR_, ir, sol, der, ss, ev1, lim, ext

Y = {"name": "y", "domain": "real"}
XPOS = {"name": "x", "domain": "positive_real"}


def tan_(f, at, givens=(), vars_=None):
    return ir("tangent_line", {"f": f, "var": "x", "at": at, "dep": "y"}, givens, list(vars_ or [X]) + [Y],
              shape="equation")


def dern(f, order, vars_=None, givens=()):
    return ir("derivative", {"f": f, "var": "x", "order": order}, givens, vars_, shape="expression")


def cases_k():
    """smooth_at reads a power whose base is nonnegative by its form as analytic at the base's zero."""
    out = []
    S4 = "sqrt(x**2 + x**4)"
    out.append(("K", f"der {S4}: sign(x)*(1 + 2*x**2)/sqrt(1 + x**2) [value at corner: convention]", der(S4),
                sol("sign(x)*(1 + 2*x**2)/sqrt(1 + x**2)", "expression"), UNK))
    out.append(("K", f"der {S4}: x*(1 + 2*x**2)/(Abs(x)*sqrt(1 + x**2)) [textbook]", der(S4),
                sol("x*(1 + 2*x**2)/(Abs(x)*sqrt(1 + x**2))", "expression"), NOTNO))
    out.append(("K", f"der {S4}: x*sqrt(1 + x**2)/Abs(x) + x*Abs(x)/sqrt(1 + x**2) [product rule]", der(S4),
                sol("x*sqrt(1 + x**2)/Abs(x) + x*Abs(x)/sqrt(1 + x**2)", "expression"), NOTNO))
    out.append(("K", "der sqrt(x**2 + 2*x**3 + x**4) = |x(1+x)|: textbook", der("sqrt(x**2 + 2*x**3 + x**4)"),
                sol("(x + 3*x**2 + 2*x**3)/sqrt(x**2 + 2*x**3 + x**4)", "expression"), NOTNO))
    out.append(("K", "der (x**2 + x**4)**(1/4): textbook (cusp)", der("(x**2 + x**4)**(1/4)"),
                sol("(2*x + 4*x**3)/(4*(x**2 + x**4)**(3/4))", "expression"), NOTNO))
    out.append(("K", f"der {S4}*exp(x): textbook", der(f"{S4}*exp(x)"),
                sol(f"exp(x)*{S4} + exp(x)*(x + 2*x**3)/{S4}", "expression"), NOTNO))
    out.append(("K", f"der exp({S4}): textbook", der(f"exp({S4})"),
                sol(f"exp({S4})*(x + 2*x**3)/{S4}", "expression"), NOTNO))
    out.append(("K", f"der log(1 + {S4}): textbook", der(f"log(1 + {S4})"),
                sol(f"(x + 2*x**3)/({S4}*(1 + {S4}))", "expression"), NOTNO))
    out.append(("K", f"der {S4}, given x > -1: textbook", der(S4, None, ["x > -1"]),
                sol(f"(x + 2*x**3)/{S4}", "expression"), NOTNO))
    out.append(("K", f"der {S4} + Abs(x - 1): textbook", der(f"{S4} + Abs(x - 1)"),
                sol(f"(x + 2*x**3)/{S4} + (x - 1)/Abs(x - 1)", "expression"), NOTNO))
    out.append(("K", "der sqrt(sin(x)**2 + (1 - cos(x))**2) = 2|sin(x/2)|: textbook",
                der("sqrt(sin(x)**2 + (1 - cos(x))**2)"),
                sol("sin(x)/sqrt(sin(x)**2 + (1 - cos(x))**2)", "expression"), NOTNO))
    out.append(("K", f"der order 2 {S4}: textbook", dern(S4, 2),
                sol("(1 + 6*x**2)/sqrt(x**2 + x**4) - (x + 2*x**3)**2/(x**2 + x**4)**(3/2)", "expression"), NOTNO))
    out.append(("K", "der order 3 sqrt(x**6 + x**8) = |x|^3 sqrt(1+x^2): SymPy's d3", dern("sqrt(x**6 + x**8)", 3),
                sol("DIFF3", "expression"), NOTNO))
    # controls: RK-8 (claim undefined where f has a derivative) and wrong claims
    out.append(("K", "ctrl der sqrt(x**4 + x**6) (= x^2 sqrt(1+x^2), f'(0)=0): (2x^3+3x^5)/sqrt(...) [RK-8]",
                der("sqrt(x**4 + x**6)"), sol("(2*x**3 + 3*x**5)/sqrt(x**4 + x**6)", "expression"), NOTOK))
    out.append(("K", "ctrl der (x**2 + x**4)**(2/3) (f'(0)=0): claim undefined at 0 [RK-8]", der("(x**2 + x**4)**(2/3)"),
                sol("2*(2*x + 4*x**3)/(3*(x**2 + x**4)**(1/3))", "expression"), NOTOK))
    out.append(("K", f"ctrl der {S4}: textbook + 1 [wrong]", der(S4), sol(f"(x + 2*x**3)/{S4} + 1", "expression"), NOTOK))
    out.append(("K", f"ctrl der {S4} at 0: DNE", der(S4, "0"), {"claimed_answer": {"kind": "dne", "payload": "DNE"},
                                                                  "steps": []}, OK))
    out.append(("K", f"ctrl tangent {S4} at 0: DNE", tan_(S4, "0"), {"claimed_answer": {"kind": "dne", "payload": "DNE"},
                                                                       "steps": []}, NOTNO))
    out.append(("K", f"ctrl tangent {S4} at 0: y = 0 [wrong]", tan_(S4, "0"), sol("y = 0", "equation"), NOTOK))
    return out


def cases_p():
    """written_undefined_in None (a written condition naming a declared-sign parameter): derivative at a point,
    tangent, extremum, series_sum now abstain (849ea4e proceeded)."""
    out = []
    V = [X, AP_]
    out.append(("P", "der sqrt(a - x) at 0, a positive: -1/(2*sqrt(a))", der("sqrt(a - x)", "0", (), V),
                sol("-1/(2*sqrt(a))"), NOTNO))
    out.append(("P", "der log(a*x) at 1, a positive: 1", der("log(a*x)", "1", (), V), sol("1"), NOTNO))
    out.append(("P", "der 1/(x + a) at 0, a positive: -1/a**2", der("1/(x + a)", "0", (), V), sol("-1/a**2"), NOTNO))
    out.append(("P", "der asin(x/a) at 0, a positive: 1/a", der("asin(x/a)", "0", (), V), sol("1/a"), NOTNO))
    out.append(("P", "der x**2 + sqrt(a) at 1, a positive: 2", der("x**2 + sqrt(a)", "1", (), V), sol("2"), NOTNO))
    out.append(("P", "der x**2 + log(a) at 1, a positive: 2", der("x**2 + log(a)", "1", (), V), sol("2"), NOTNO))
    out.append(("P", "der sqrt(a - x) at 0, a positive: 1/(2*sqrt(a)) [wrong]", der("sqrt(a - x)", "0", (), V),
                sol("1/(2*sqrt(a))"), NOTOK))
    out.append(("P", "tangent sqrt(a - x) at 0, a positive", tan_("sqrt(a - x)", "0", (), V),
                sol("y = sqrt(a) - x/(2*sqrt(a))", "equation"), NOTNO))
    out.append(("P", "tangent log(a*x) at 1, a positive", tan_("log(a*x)", "1", (), V),
                sol("y = x - 1 + log(a)", "equation"), NOTNO))
    out.append(("P", "tangent x**2 + log(a) at 1, a positive", tan_("x**2 + log(a)", "1", (), V),
                sol("y = 2*x - 1 + log(a)", "equation"), NOTNO))
    out.append(("P", "tangent x**2 + 1/a at 1, a positive", tan_("x**2 + 1/a", "1", (), V),
                sol("y = 2*x - 1 + 1/a", "equation"), NOTNO))
    out.append(("P", "max x + 0*sqrt(a) on [0, 1], a positive: 1", ext("x + 0*sqrt(a)", "max", "[0, 1]", (), V),
                sol("1"), NOTNO))
    VK = [K_, AP_]
    out.append(("P", "series 1/(k + a), k=1..3, a positive", ss("1/(k + a)", "1", "3", (), VK),
                sol("1/(a + 1) + 1/(a + 2) + 1/(a + 3)"), NOTNO))
    out.append(("P", "series 1/(a*k), k=1..3, a positive: 11/(6a)", ss("1/(a*k)", "1", "3", (), VK), sol("11/(6*a)"),
                NOTNO))
    out.append(("P", "series sqrt(a*k), k=1..2, a positive", ss("sqrt(a*k)", "1", "2", (), VK),
                sol("sqrt(a) + sqrt(2)*sqrt(a)"), NOTNO))
    out.append(("P", "series log(a*k), k=1..2, a positive: 2*log(a) + log(2)", ss("log(a*k)", "1", "2", (), VK),
                sol("2*log(a) + log(2)"), NOTNO))
    out.append(("P", "series k/a, k=1..3, a positive: 6/a", ss("k/a", "1", "3", (), VK), sol("6/a"), NOTNO))
    out.append(("P", "series 1/(k + a), k=1..3, a positive: wrong", ss("1/(k + a)", "1", "3", (), VK),
                sol("3/(a + 2)"), NOTOK))
    VR = [K_, {"name": "r", "domain": "real", "constraints": ["r > 0", "r < 1"]}]
    out.append(("P", "series r**k, k=0..oo, 0<r<1: 1/(1 - r)", ss("r**k", "0", "oo", (), VR), sol("1/(1 - r)"), NOTNO))
    out.append(("P", "series r**k, k=1..oo, 0<r<1: r/(1 - r)", ss("r**k", "1", "oo", (), VR), sol("r/(1 - r)"), NOTNO))
    out.append(("P", "series r**k, k=0..3, r positive: 1 + r + r**2 + r**3", ss("r**k", "0", "3", (),
                [K_, {"name": "r", "domain": "positive_real"}]), sol("1 + r + r**2 + r**3"), NOTNO))
    out.append(("P", "series a**k/k, k=1..2, a positive: a + a**2/2", ss("a**k/k", "1", "2", (), VK),
                sol("a + a**2/2"), NOTNO))
    return out


def cases_d():
    """Dirichlet's test after d342778 (h holds no symbol but t): a declared-positive parameter in h."""
    out = []
    V = [X, T_, AP_]
    for e in ("0*Integral(sin(t)/(t + a), (t, 1, oo)) + 1", "0*Integral(a*sin(t)/t, (t, 1, oo)) + 1",
              "0*Integral(cos(t)/sqrt(t + a), (t, 0, oo)) + 1", "0*Integral(sin(t)/(a*t), (t, 1, oo)) + 1",
              "0*Integral(sin(t)/t**a, (t, 1, oo)) + 1"):
        out.append(("D", f"evaluate {e}, a positive: 1", ir("evaluate", {"expr": e}, (), [T_, AP_], shape="scalar"),
                    sol("1"), NOTNO))
    out.append(("D", "der x + 0*Integral(sin(t)/(t + a), (t, 1, oo)) at 0, a positive: 1",
                der("x + 0*Integral(sin(t)/(t + a), (t, 1, oo))", "0", (), V), sol("1"), NOTNO))
    out.append(("D", "der Integral(sin(t)/(t + a), (t, x, oo)), a, x positive: -sin(x)/(x + a)",
                der("Integral(sin(t)/(t + a), (t, x, oo))", None, (), [XPOS, T_, AP_]),
                sol("-sin(x)/(x + a)", "expression"), NOTNO))
    out.append(("D", "der x + 0*Integral(sin(t)/(t + x), (t, 1, oo)), x positive: 1",
                der("x + 0*Integral(sin(t)/(t + x), (t, 1, oo))", None, (), [XPOS, T_]), sol("1", "expression"), NOTNO))
    out.append(("D", "der x + 0*Integral(sin(t)/(t + x), (t, 1, oo)) at 1, x positive: 1",
                der("x + 0*Integral(sin(t)/(t + x), (t, 1, oo))", "1", (), [XPOS, T_]), sol("1"), NOTNO))
    out.append(("D", "evaluate 0*Integral(sin(t)/(t + a), (t, 1, oo)) + 1, given a = 2: 1",
                ir("evaluate", {"expr": "0*Integral(sin(t)/(t + a), (t, 1, oo)) + 1"}, ["a = 2"],
                   [T_, AR_], shape="scalar"), sol("1"), NOTNO))
    out.append(("D", "evaluate 0*Integral(sin(t)/(t + a), (t, 1, oo)) + 1, given 2*a = 4: 1",
                ir("evaluate", {"expr": "0*Integral(sin(t)/(t + a), (t, 1, oo)) + 1"}, ["2*a = 4"],
                   [T_, AR_], shape="scalar"), sol("1"), NOTNO))
    # controls
    out.append(("D", "ctrl evaluate 0*Integral(sin(t)/t, (t, 1, oo)) + 1: 1",
                ir("evaluate", {"expr": "0*Integral(sin(t)/t, (t, 1, oo)) + 1"}, (), [T_], shape="scalar"),
                sol("1"), OK))
    out.append(("D", "ctrl evaluate 0*Integral(sin(t)/(t + 2), (t, 1, oo)) + 1: 1",
                ir("evaluate", {"expr": "0*Integral(sin(t)/(t + 2), (t, 1, oo)) + 1"}, (), [T_], shape="scalar"),
                sol("1"), OK))
    return out


def cases_w():
    """Switches (Max, Min, sign, Piecewise, Abs) where f is differentiable at the switch: the claim's value there
    is f's derivative, never a convention."""
    out = []
    for f, c in (("Max(x, 0)**2", "2*Max(x, 0)"), ("x*Max(x, 0)", "2*Max(x, 0)"), ("x*Abs(x)", "2*Abs(x)"),
                 ("sign(x)*x**2", "2*x*sign(x)"), ("Abs(x)**3", "3*x*Abs(x)"), ("Abs(x - 1)*(x - 1)", "2*Abs(x - 1)"),
                 ("Max(sin(x), 0)**2", "2*cos(x)*Max(sin(x), 0)"), ("Abs(x)*sin(x)", "sign(x)*sin(x) + Abs(x)*cos(x)"),
                 ("Abs(x**2 - 1)*(x**2 - 1)", "4*x*Abs(x**2 - 1)"), ("Min(x, 0)**2", "2*Min(x, 0)"),
                 ("Max(x**3, 0)", "3*Max(x, 0)**2"), ("Abs(x**3)", "3*x*Abs(x)"),
                 ("Piecewise((x**2, x < 0), (x**3, x >= 0))", "Piecewise((2*x, x < 0), (3*x**2, x >= 0))"),
                 ("Piecewise((x**2, x < 1), (2*x - 1, x >= 1))", "Piecewise((2*x, x < 1), (2, x >= 1))"),
                 ("Max(x**2, x**4)", "Piecewise((2*x, Abs(x) < 1), (4*x**3, Abs(x) > 1))"),
                 ("Min(x**2, 1)", "Piecewise((2*x, Abs(x) < 1), (0, Abs(x) > 1))"),
                 ("Max(x, 2*x)", "Piecewise((1, x < 0), (2, x > 0))"),
                 ("x*sign(x)*x", "2*Abs(x)"), ("Max(x, -x)**2", "2*x")):
        out.append(("W", f"der {f}: {c}", der(f), sol(c, "expression"), NOTNO))
    return out


def cases_r():
    """RK-3 (integer n: no negative-base convention), RK-7 (compute step at(diff)), YO-5 limit regions."""
    out = []
    NI = {"name": "n", "domain": "integer"}
    NN = {"name": "n", "domain": "natural"}
    for vv, lab in ((NI, "integer"), (NN, "natural"), (NP_, "positive_integer")):
        out.append(("R", f"der x**2*(-1)**n, n {lab}: 2*x*(-1)**n", der("x**2*(-1)**n", None, (), [X, vv]),
                    sol("2*x*(-1)**n", "expression"), NOTNO))
        out.append(("R", f"der x**2*(-1)**n at 1, n {lab}: 2*(-1)**n", der("x**2*(-1)**n", "1", (), [X, vv]),
                    sol("2*(-1)**n"), NOTNO))
        out.append(("R", f"der x*(-2)**n, n {lab}: (-2)**n", der("x*(-2)**n", None, (), [X, vv]),
                    sol("(-2)**n", "expression"), NOTNO))
    q = ir("evaluate", {"expr": "x + 1"}, ["x = 1"], [X], shape="scalar")
    for c in ("at(diff(1/(x - cos(x)), x), x, 0) = -1", "at(diff(sqrt(x + exp(x)), x), x, 0) = 1",
              "at(diff(log(x - sin(x)), x), x, 1) = (1 - cos(1))/(1 - sin(1))", "at(diff(x**2, x), x, 3) = 6",
              "at(diff(tan(x**2), x), x, 1) = 2/cos(1)**2"):
        out.append(("R", f"compute step {c}", q, sol("2", steps=[("compute", c)]), OK))
    # YO-5: the givens' written conditions shape the limit's region
    out.append(("R", "limit sin(x)/x at 0, given 1/x > 0: 1", lim("sin(x)/x", "0", ["1/x > 0"]), sol("1"), NOTNO))
    out.append(("R", "limit (x**2 - 1)/(x - 1) at 1, given log(x) > -10: 2", lim("(x**2 - 1)/(x - 1)", "1",
                ["log(x) > -10"]), sol("2"), NOTNO))
    out.append(("R", "limit Abs(x - 1)/(x - 1) at 1, given log(x) > 0: 1", lim("Abs(x - 1)/(x - 1)", "1",
                ["log(x) > 0"]), sol("1"), NOTNO))
    out.append(("R", "limit Abs(x)/x at 0, given sqrt(x) > 0: 1", lim("Abs(x)/x", "0", ["sqrt(x) > 0"]), sol("1"),
                NOTNO))
    out.append(("R", "limit x**2 at 2, given sqrt(x) >= 0: 4", lim("x**2", "2", ["sqrt(x) >= 0"]), sol("4"), NOTNO))
    out.append(("R", "limit x**2 at 2, constraint log(x) > 0: 4", lim("x**2", "2", (),
                [{"name": "x", "domain": "real", "constraints": ["log(x) > 0"]}]), sol("4"), NOTNO))
    out.append(("R", "limit x**2 at 2, dod sqrt(x) > 1: 4", lim("x**2", "2", (), None, "sqrt(x) > 1"), sol("4"), NOTNO))
    return out


import sonda_rk as _rk
GROUPS = {"K": cases_k, "P": cases_p, "D": cases_d, "W": cases_w, "R": cases_r,
          "H": lambda: [c + (None,) if False else c for c in _rk.cases_h()], "A": _rk.cases_a, "G": _rk.cases_g,
          "J": _rk.cases_j, "B": _rk.cases_b, "E": _rk.cases_e, "F": _rk.cases_f}


def _fill(s, q):
    """DIFF3: SymPy's third derivative of f, as a string."""
    if s["claimed_answer"]["payload"] == "DIFF3":
        import sympy as sp
        x = sp.Symbol("x", real=True)
        f = sp.sympify(q["task"]["params"]["f"], locals={"x": x})
        s = json.loads(json.dumps(s))
        s["claimed_answer"]["payload"] = str(sp.diff(f, x, 3))
    return s


def main(out_path, groups, only=None):
    from mathverify.verifier import verify
    rows = []
    t0 = time.time()
    for g in ([x for x in groups.split(",") if x] if "," in groups else groups):
        for grp, label, q, s, verdicts in GROUPS[g]():
            if only and only not in label:
                continue
            s = _fill(s, q)
            t = time.time()
            reason = None
            try:
                r = verify(q, s)
                verdict = r.verdict
                flags = sorted({f for la in r.layers for f in (la.flags or [])})[:6]
                for la in r.layers:
                    ev = la.evidence or {}
                    if isinstance(ev, dict):
                        cmp_ = ev.get("compare")
                        if isinstance(cmp_, dict):
                            reason = {k: cmp_.get(k) for k in ("method", "reason", "claim_as_written", "kinks",
                                                                "smooth_witness") if k in cmp_}
                        elif ev.get("reason"):
                            reason = reason or ev.get("reason")
                        if la.layer == "steps.refute" and ev.get("steps"):
                            reason = {"step": ev["steps"][-1].get("status")}
            except Exception as e:  # noqa: BLE001
                verdict, flags = f"EXC {type(e).__name__}: {e}", []
            dt = time.time() - t
            ok = verdict in verdicts and dt < 60
            rows.append({"group": grp, "label": label, "verdict": verdict, "ok": ok, "flags": flags,
                         "reason": str(reason)[:300], "s": round(dt, 1)})
            print(f"{'ok ' if ok else 'BAD'} {grp} {verdict:9} {dt:6.1f}s {label} | {str(reason)[:220]} {flags}",
                  flush=True)
    print(f"{len(rows)} cases, {sum(not r['ok'] for r in rows)} not as expected, {time.time() - t0:.0f} s")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)




def cases_m():
    """More coverage of the claim's written conditions (YO-3) and of switch families."""
    out = []
    AC = {"name": "a", "domain": "real", "constraints": ["a != 0"]}
    for f, c in (("atan(x/a)", "a/(a**2 + x**2)"), ("log(x)/a", "1/(a*x)"), ("sqrt(x)/a", "1/(2*a*sqrt(x))"),
                 ("sqrt(x**2 + a**2)", "x/sqrt(x**2 + a**2)"), ("asin(x/a)", "1/sqrt(a**2 - x**2)"),
                 ("log(Abs(a*x))", "1/x"), ("x/a + 1/x", "1/a - 1/x**2")):
        out.append(("M", f"der {f}, constraint a != 0: {c}", der(f, None, (), [X, AC]), sol(c, "expression"), NOTNO))
        out.append(("M", f"der {f}, given a != 0: {c}", der(f, None, ["a != 0"], [X, AR_]), sol(c, "expression"), NOTNO))
    out.append(("M", "der atan(x/a), given a != 0: a/(a**2 + x**2) + 1 [wrong]", der("atan(x/a)", None, ["a != 0"],
                [X, AR_]), sol("a/(a**2 + x**2) + 1", "expression"), NOTOK))
    for f, c in (("sqrt(x + sin(x))", "(1 + cos(x))/(2*sqrt(x + sin(x)))"),
                 ("sqrt(exp(x) - 1 - x)", "(exp(x) - 1)/(2*sqrt(exp(x) - 1 - x))"),
                 ("sqrt(1 + sin(x))", "cos(x)/(2*sqrt(1 + sin(x)))"),
                 ("sqrt(2 + sin(x))", "cos(x)/(2*sqrt(2 + sin(x)))"),
                 ("sqrt(cos(x))", "-sin(x)/(2*sqrt(cos(x)))"),
                 ("sqrt(x - log(x))", "(1 - 1/x)/(2*sqrt(x - log(x)))"),
                 ("sqrt(x**2 + sin(x)**2)", "(x + sin(x)*cos(x))/sqrt(x**2 + sin(x)**2)"),
                 ("(x - cos(x))**(3/2)", "3*(1 + sin(x))*sqrt(x - cos(x))/2"),
                 ("1/sqrt(x - cos(x))", "-(1 + sin(x))/(2*(x - cos(x))**(3/2))"),
                 ("Abs(x - cos(x))", "(1 + sin(x))*(x - cos(x))/Abs(x - cos(x))"),
                 ("Abs(sin(x))**3", "3*sin(x)*cos(x)*Abs(sin(x))"),
                 ("Abs(cos(x))**3", "-3*sin(x)*cos(x)*Abs(cos(x))"),
                 ("sqrt(Abs(sin(x)))", "cos(x)*sin(x)/(2*Abs(sin(x))**(3/2))"),
                 ("Max(cos(x), 0)**2", "-2*sin(x)*Max(cos(x), 0)"),
                 ("Abs(sin(x))", "cos(x)*sin(x)/Abs(sin(x))"),
                 ("Abs(sin(x))", "cos(x)*sign(sin(x))"),
                 ("x*Abs(sin(x))", "Abs(sin(x)) + x*cos(x)*sin(x)/Abs(sin(x))")):
        exp_ = UNK if "sign(" in c else NOTNO
        out.append(("M", f"der {f}: {c}", der(f), sol(c, "expression"), exp_))
    return out


GROUPS["M"] = cases_m


def cases_s():
    """Hash-seed sensitivity: readings with several switches, families, witnesses."""
    out = []
    for f, c, e in (("Abs(log(x)) + Abs(tan(x))", "0", NOTOK), ("Abs(sqrt(x) - 1) + Abs(tan(x))", "0", NOTOK),
                    ("Abs(log(x))*Abs(tan(x))", "0", NOTOK), ("Abs(tan(x)) + Abs(x - 1) + Abs(x - 2)", "1", NOTOK),
                    ("Abs(tan(x)) + Abs(log(x)) + Abs(x - 3)", "1/cos(x)**2", NOTOK),
                    ("Abs(tan(x)) + Abs(log(x))", "tan(x)/(cos(x)**2*Abs(tan(x))) + log(x)/(x*Abs(log(x)))", NOTNO),
                    ("sqrt(x**2 + x**4)", "sign(x)*(1 + 2*x**2)/sqrt(1 + x**2)", UNK),
                    ("Abs(x**2 - 2) + Abs(sin(x))", "2*x", NOTOK),
                    ("Max(x, x**2) + Abs(sin(x))", "1", NOTOK),
                    ("Abs(x - cos(x)) + Abs(x - 1)", "1 + sin(x) + 1", NOTOK)):
        out.append(("S", f"der {f}: {c}", der(f), sol(c, "expression"), e))
    return out


GROUPS["S"] = cases_s


def cases_q():
    """series_sum after the fail-closed change: common finite and infinite sums keep their verdicts."""
    out = []
    VK = [K_]
    for t, lo, hi, v in (("(-1)**(k + 1)/k", "1", "oo", "log(2)"), ("(-1)**k/(2*k + 1)", "0", "oo", "pi/4"),
                         ("1/2**k", "1", "oo", "1"), ("k/2**k", "1", "oo", "2"), ("1/k**2", "1", "oo", "pi**2/6"),
                         ("1/factorial(k)", "0", "oo", "E"), ("1/(k*(k + 1))", "1", "oo", "1"),
                         ("(-1)**k*k", "1", "5", "-3"), ("(-2)**k", "0", "4", "11"),
                         ("(-1)**k*binomial(3, k)", "0", "3", "0"), ("log(k)", "1", "3", "log(6)"),
                         ("0**k", "1", "3", "0"), ("sqrt(k)", "1", "4", "3 + sqrt(2) + sqrt(3)"),
                         ("1/(k - 1/2)", "1", "3", "46/15"), ("(1/2)**k", "0", "oo", "2"),
                         ("(-1/2)**k", "0", "oo", "2/3"), ("1/(4*k**2 - 1)", "1", "oo", "1/2"),
                         ("k**2", "-2", "2", "10"), ("1/k", "-3", "-1", "-11/6"),
                         ("(-1)**(k*(k + 1)/2)", "0", "3", "0"), ("cos(pi*k)", "0", "3", "0"),
                         ("(-1)**k/factorial(k)", "0", "oo", "exp(-1)")):
        out.append(("Q", f"series {t}, k={lo}..{hi}: {v}", ss(t, lo, hi, (), VK), sol(v), NOTNO))
    out.append(("Q", "series (-1)**(k+1)/k, k=1..oo: log(3) [wrong]", ss("(-1)**(k + 1)/k", "1", "oo", (), VK), sol("log(3)"),
                NOTOK))
    return out


GROUPS["Q"] = cases_q


def cases_f2():
    """factorial / binomial terms in series_sum (written definedness of factorial(k) at integer k)."""
    out = []
    VK = [K_]
    for t, lo, hi, v in (("1/factorial(k)", "0", "3", "8/3"), ("2**k/factorial(k)", "0", "oo", "exp(2)"),
                         ("factorial(k)", "0", "3", "10"), ("k*factorial(k)", "1", "4", "119"),
                         ("binomial(4, k)", "0", "4", "16"), ("binomial(k, 2)", "0", "4", "10"),
                         ("1/factorial(2*k)", "0", "oo", "cosh(1)"), ("k/factorial(k)", "1", "oo", "E"),
                         ("1/factorial(k + 1)", "0", "oo", "E - 1"), ("factorial(k)/factorial(k)", "0", "3", "4"),
                         ("1/factorial(k)", "0", "oo", "E + 1")):
        exp_ = NOTOK if t == "1/factorial(k)" and v == "E + 1" else NOTNO
        out.append(("F2", f"series {t}, k={lo}..{hi}: {v}", ss(t, lo, hi, (), VK), sol(v), exp_))
    out.append(("F2", "series 1/factorial(k), k=0..oo, n natural decl: E", ss("1/factorial(k)", "0", "oo", (),
                [{"name": "k", "domain": "nonneg_integer"}]), sol("E"), NOTNO))
    return out


GROUPS["F2"] = cases_f2


def cases_x():
    """Extremum, derivative at a point and tangent whose written condition no exact class solves (None now
    abstains; 849ea4e went on)."""
    out = []
    for f, w, iv, v in (("sqrt(exp(x) - x)", "max", "[0, 1]", "sqrt(E - 1)"), ("sqrt(exp(x) - x)", "min", "[0, 1]", "1"),
                        ("log(exp(x) + x)", "min", "[0, 1]", "0"), ("1/(exp(x) - x)", "max", "[0, 1]", "1"),
                        ("log(x + exp(x))", "min", "[0, 1]", "0"), ("x**2 + log(exp(x) + 1)", "min", "[0, 1]", "log(2)"),
                        ("sqrt(x + exp(x))", "min", "[0, 1]", "1"), ("1/(x + exp(x))", "max", "[0, 1]", "1"),
                        ("x*exp(-x) + 0*log(exp(x) - x)", "max", "[0, 2]", "exp(-1)"),
                        ("sqrt(exp(x) - x)", "max", "[0, 1]", "2")):
        exp_ = NOTOK if v == "2" else NOTNO
        out.append(("X", f"{w} {f} on {iv}: {v}", ext(f, w, iv), sol(v), exp_))
    out.append(("X", "der sqrt(exp(x) - x) at 0: 0", der("sqrt(exp(x) - x)", "0"), sol("0"), NOTNO))
    out.append(("X", "der log(x + exp(x)) at 0: 2", der("log(x + exp(x))", "0"), sol("2"), NOTNO))
    out.append(("X", "der 1/(exp(x) - x) at 0: 0", der("1/(exp(x) - x)", "0"), sol("0"), NOTNO))
    out.append(("X", "tangent log(x + exp(x)) at 0: y = 2x", tan_("log(x + exp(x))", "0"), sol("y = 2*x", "equation"),
                NOTNO))
    out.append(("X", "tangent sqrt(exp(x) - x) at 0: y = 1", tan_("sqrt(exp(x) - x)", "0"), sol("y = 1", "equation"),
                NOTNO))
    return out


GROUPS["X"] = cases_x


def cases_z():
    """Robustness: odd switch structures (no exception, no unjust INCORRECT on the textbook claim)."""
    out = []
    for f, c in (("Max(Min(x, 1), -1)", "Piecewise((0, x < -1), (1, x < 1), (0, x > 1))"),
                 ("Abs(Abs(x) - 1)", "x*(Abs(x) - 1)/(Abs(x)*Abs(Abs(x) - 1))"),
                 ("Max(Abs(x), 1)", "Piecewise((x/Abs(x), Abs(x) > 1), (0, Abs(x) < 1))"),
                 ("Max(x, 0, -x)", "x/Abs(x)"), ("sign(x)**2", "0"), ("Abs(x)*sign(x)", "2*Abs(x)/x*0 + 2*x/x*Abs(x)/Abs(x)"),
                 ("Piecewise((x**2, Eq(x, 0)), (x, x > 0), (-x, x < 0))", "x/Abs(x)"),
                 ("Min(x**2, Abs(x))", "Piecewise((2*x, Abs(x) < 1), (x/Abs(x), Abs(x) > 1))"),
                 ("Abs(x)**x", "Abs(x)**x*(log(Abs(x)) + 1)"),
                 ("Abs(sin(x))**(1/3)", "cos(x)*sin(x)/(3*Abs(sin(x))**(7/3))*Abs(sin(x))**2"),
                 ("Max(x**2 - 1, 1 - x**2)", "2*x*(x**2 - 1)/Abs(x**2 - 1)"),
                 ("Abs(x - 1)*Abs(x + 1)", "2*x*(x**2 - 1)/Abs(x**2 - 1)"),
                 ("sqrt((x - 1)**2)", "(x - 1)/Abs(x - 1)"),
                 ("Abs(x)/x", "0"), ("x/Abs(x)", "0")):
        out.append(("Z", f"der {f}: {c}", der(f), sol(c, "expression"), NOTNO))
    for f, c in (("Abs(x)", "x/Abs(x)"), ("Max(x, -x)", "x/Abs(x)")):
        out.append(("Z", f"der order 2 {f}: 0", dern(f, 2), sol("0", "expression"), NOTNO))
    return out


GROUPS["Z"] = cases_z
GROUPS["RD"] = _rk.cases_d


def cases_l():
    """Limit (YO-5): givens/constraints on OTHER symbols carry written conditions; the limit in x is unaffected."""
    out = []
    B = {"name": "b", "domain": "real"}
    C = {"name": "c", "domain": "real"}
    for g in (["b = log(c)"], ["b = sqrt(c)"], ["b = 1/c"], ["b*c = 1"], ["c = sqrt(b) + 1"], ["b = acos(c)"]):
        out.append(("L", f"limit sin(x)/x at 0, given {g}: 1", lim("sin(x)/x", "0", g, [X, B, C]), sol("1"), NOTNO))
        out.append(("L", f"limit (x**2 - 4)/(x - 2) at 2, given {g}: 4", lim("(x**2 - 4)/(x - 2)", "2", g, [X, B, C]),
                    sol("4"), NOTNO))
    CC = {"name": "c", "domain": "real", "constraints": ["log(c) > 0"]}
    out.append(("L", "limit sin(x)/x at 0, constraint log(c) > 0 on c: 1", lim("sin(x)/x", "0", (), [X, CC]), sol("1"),
                NOTNO))
    out.append(("L", "limit sin(x)/x at 0, dod c > 0 and sqrt(c) < 2 ... (dod sqrt(c) < 2): 1",
                lim("sin(x)/x", "0", (), [X, C], "sqrt(c) < 2"), sol("1"), NOTNO))
    out.append(("L", "limit sin(x)/x at 0, given y = sqrt(t): 1", lim("sin(x)/x", "0", ["y = sqrt(t)"],
                [X, {"name": "y", "domain": "real"}, T_]), sol("1"), NOTNO))
    out.append(("L", "limit x*sin(1/x) at 0, given y = log(x**2): 0", lim("x*sin(1/x)", "0", ["y = log(x**2)"],
                [X, {"name": "y", "domain": "real"}]), sol("0"), NOTNO))
    out.append(("L", "limit sin(x)/x at 0, given y = 1/x: 1", lim("sin(x)/x", "0", ["y = 1/x"],
                [X, {"name": "y", "domain": "real"}]), sol("1"), NOTNO))
    out.append(("L", "limit (x**2 - 1)/(x - 1) at 1, given y = (x**2 - 1)/(x - 1): 2", lim("(x**2 - 1)/(x - 1)", "1",
                ["y = (x**2 - 1)/(x - 1)"], [X, {"name": "y", "domain": "real"}]), sol("2"), NOTNO))
    return out


GROUPS["L"] = cases_l


def cases_k2():
    out = []
    out.append(("K2", "der sqrt(x**2 + a**2*x**4), a real: textbook", der("sqrt(x**2 + a**2*x**4)", None, (), [X, AR_]),
                sol("(x + 2*a**2*x**3)/sqrt(x**2 + a**2*x**4)", "expression"), NOTNO))
    out.append(("K2", "der sqrt(4*x**2 + x**4): textbook", der("sqrt(4*x**2 + x**4)"),
                sol("(4*x + 2*x**3)/sqrt(4*x**2 + x**4)", "expression"), NOTNO))
    out.append(("K2", "der sqrt(x**4 + x**2) [reordered]: textbook", der("sqrt(x**4 + x**2)"),
                sol("(2*x**3 + x)/sqrt(x**4 + x**2)", "expression"), NOTNO))
    out.append(("K2", "der x**3 + sqrt(x**2 + x**4), given x < 5: textbook", der("x**3 + sqrt(x**2 + x**4)", None, ["x < 5"]),
                sol("3*x**2 + (x + 2*x**3)/sqrt(x**2 + x**4)", "expression"), NOTNO))
    out.append(("K2", "ctrl der Abs(x)*sqrt(1 + x**2): x*(1 + 2*x**2)/(Abs(x)*sqrt(1 + x**2))", der("Abs(x)*sqrt(1 + x**2)"),
                sol("x*(1 + 2*x**2)/(Abs(x)*sqrt(1 + x**2))", "expression"), NOTNO))
    out.append(("K2", "ctrl der x*sqrt(x**2 + x**4) (f'(0) = 0): claim undefined at 0 [RK-8]", der("x*sqrt(x**2 + x**4)"),
                sol("sqrt(x**2 + x**4) + x*(x + 2*x**3)/sqrt(x**2 + x**4)", "expression"), NOTOK))
    return out


GROUPS["K2"] = cases_k2


def cases_t():
    """Timing of the claim's written-condition reading (claim_where_derivative) with nested-radical zero sets."""
    out = []
    U2, U3 = "x**4 - 10*x**2 + 1", "x**3 - 3*x + 1"
    out.append(("T", "der sqrt(U2): textbook", der(f"sqrt({U2})"), sol(f"(2*x**3 - 10*x)/sqrt({U2})", "expression"), NOTNO))
    out.append(("T", "der sqrt(U2*U3): textbook", der(f"sqrt(({U2})*({U3}))"),
                sol(f"((4*x**3 - 20*x)*({U3}) + (3*x**2 - 3)*({U2}))/(2*sqrt(({U2})*({U3})))", "expression"), NOTNO))
    out.append(("T", "der log(U2**2) : textbook", der(f"log(({U2})**2)"), sol(f"2*(4*x**3 - 20*x)/({U2})", "expression"),
                NOTNO))
    out.append(("T", "der x**2: 2x + 0/U2 + 0/U3 [RK-8 INCORRECT]", der("x**2"), sol(f"2*x + 0/({U2}) + 0/({U3})", "expression"),
                NOTOK))
    out.append(("T", "der 1/U2 + 1/U3: textbook", der(f"1/({U2}) + 1/({U3})"),
                sol(f"-(4*x**3 - 20*x)/({U2})**2 - (3*x**2 - 3)/({U3})**2", "expression"), NOTNO))
    out.append(("T", "der sqrt(Abs(U2)): textbook", der(f"sqrt(Abs({U2}))"),
                sol(f"(4*x**3 - 20*x)*({U2})/(2*Abs({U2})**(3/2))", "expression"), NOTNO))
    out.append(("T", "der Abs(U2)*U3: textbook", der(f"Abs({U2})*({U3})"),
                sol(f"(4*x**3 - 20*x)*({U2})*({U3})/Abs({U2}) + (3*x**2 - 3)*Abs({U2})", "expression"), NOTNO))
    return out


GROUPS["T"] = cases_t


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2] if len(a) > 2 else None)
