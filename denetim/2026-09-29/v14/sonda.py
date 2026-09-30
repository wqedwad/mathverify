"""V14 probe (29 Sep 2026): the parser's conventions for gcd/lcm with symbols, the bound index of a
Sum/Product, and arccot. Run from the root of the checkout under test (the old code in a separate
worktree, the new one in place):

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-29/v14/sonda.py [out.json]

Prints (1) what each text parses to, (2) the verdict of small artificial problems whose answer or
step depends on the convention. Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import sys


def _parse_rows():
    import sympy as sp
    from mathverify.normalize.parse import build_namespace, parse_expr_str, parse_relation
    from mathverify.ir import ProblemIR

    def ns_for(vars_):
        ir = ProblemIR.from_dict({"task": {"kind": "evaluate", "params": {"expr": "1"}}, "vars": vars_,
                                  "givens": [], "answer_shape": "scalar"})
        return build_namespace(ir)

    nsk = ns_for([{"name": "k", "domain": "positive_integer"}, {"name": "n", "domain": "positive_integer"},
                  {"name": "x", "domain": "positive_real"}, {"name": "y", "domain": "real"}])
    ns0 = ns_for([{"name": "n", "domain": "positive_integer"}, {"name": "y", "domain": "real"}])
    cases = [
        # gcd / lcm
        ("gcd", nsk, "lcm(n, 2)"), ("gcd", nsk, "gcd(n, 4)"), ("gcd", nsk, "gcd(84, 120)"),
        ("gcd", nsk, "lcm(4, 6)"), ("gcd", nsk, "gcd(84, 120) + lcm(4, 6)"), ("gcd", nsk, "gcd(12, 18, 24)"),
        ("gcd", nsk, "lcm(4, 6, 10)"), ("gcd", nsk, "gcd(1/2, 1/3)"), ("gcd", nsk, "lcm(1/2, 1/3)"),
        ("gcd", nsk, "gcd(x**2 - 1, x - 1)"), ("gcd", nsk, "gcd(0, 0)"), ("gcd", nsk, "lcm(0, 5)"),
        ("gcd", nsk, "gcd(-4, 6)"), ("gcd", nsk, "lcm(-4, 6)"), ("gcd", nsk, "gcd(2.5, 5)"),
        ("gcd", nsk, "gcd(sqrt(2), 2)"), ("gcd", nsk, "gcd(pi, 2)"), ("gcd", nsk, "gcd(2*n, n)"),
        ("gcd", nsk, "lcm(n, n + 1)"), ("gcd", nsk, "gcd(n, 2).subs(n, 6)"),
        # bound index
        ("sum", nsk, "Sum(0**k, (k, 0, n))"), ("sum", nsk, "Sum(0**k, (k, 0, 3))"),
        ("sum", nsk, "Sum(Abs(k), (k, -2, 2))"), ("sum", nsk, "Sum(k/k, (k, -1, 1))"),
        ("sum", nsk, "Product(sign(k), (k, -1, -1))"), ("sum", nsk, "Sum(sqrt(k**2), (k, -3, -1))"),
        ("sum", nsk, "Sum(1/(k*(k + 1)), (k, 1, oo))"), ("sum", nsk, "Sum(1/k - 1/(k + 1), (k, 1, n))"),
        ("sum", nsk, "Sum(k, (k, 1, 10))"), ("sum", nsk, "Sum(1/2**k, (k, 1, n))"),
        ("sum", nsk, "Sum((-1)**(2*k), (k, 1, n))"), ("sum", nsk, "Sum(sin(pi*k), (k, 1/2, 5/2))"),
        ("sum", nsk, "Sum(k, (k, 1, 3)) + k"), ("sum", nsk, "Sum(Sum(k*j, (j, 1, k)), (k, 1, 3))"),
        ("sum", ns0, "Sum(0**k, (k, 0, n))"), ("sum", nsk, "Integral(Abs(x), (x, -1, 1))"),
        ("sum", nsk, "Limit(Abs(x), x, -2)"),
        # arccot
        ("acot", nsk, "arccot(-1)"), ("acot", nsk, "acot(-1)"), ("acot", nsk, "arccot(0)"),
        ("acot", nsk, "arccot(sqrt(3))"), ("acot", nsk, "arccot(-sqrt(3))"),
        ("acot", nsk, r"\operatorname{arccot}(-1)"), ("acot", nsk, r"\cot^{-1}(-1)"), ("acot", nsk, r"\arccot(-1)"),
    ]
    rows = []
    for group, ns, text in cases:
        if text.endswith(".subs(n, 6)"):
            try:
                v = parse_expr_str(text[: -len(".subs(n, 6)")], ns).subs(ns["n"], 6)
                rows.append((group, text, str(v), str(sp.N(v)) if isinstance(v, sp.Expr) else ""))
            except Exception as e:  # noqa: BLE001
                rows.append((group, text, f"ERR {type(e).__name__}: {e}"[:160], ""))
            continue
        try:
            e = parse_relation(text, ns) if "=" in text else parse_expr_str(text, ns)
            val = e.doit() if hasattr(e, "doit") else e
            num = ""
            try:
                num = str(sp.N(val, 15)) if isinstance(val, sp.Expr) else ""
            except Exception:  # noqa: BLE001
                pass
            rows.append((group, text, f"{e}  ->  {val}", num))
        except Exception as ex:  # noqa: BLE001
            rows.append((group, text, f"ERR {type(ex).__name__}: {ex}"[:160], ""))
    return rows


def _ir(expr, vars_, givens=(), options=None, kind="evaluate", params=None):
    d = {"task": {"kind": kind, "params": params if params is not None else {"expr": expr}},
         "vars": list(vars_), "givens": list(givens), "answer_shape": "scalar"}
    if options:
        d["options"] = options
    return d


def _sol(payload, steps=(), kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


NK = [{"name": "k", "domain": "positive_integer"}, {"name": "n", "domain": "positive_integer"}]
NN = [{"name": "n", "domain": "positive_integer"}]
XR = [{"name": "x", "domain": "real"}]

# (name, expected verdict under the stated convention, ir, solution)
VERDICT_CASES = [
    # arccot: AYT reads arccot in (0, pi); arccot(-1) = 3pi/4
    ("acot_dogru_3pi4", "CORRECT", _ir("arccot(-1)", []), _sol("3*pi/4")),
    ("acot_yanlis_-pi4", "INCORRECT", _ir("arccot(-1)", []), _sol("-pi/4")),
    ("acot_sympy_adi_dogru", "CORRECT", _ir("acot(-1)", []), _sol("3*pi/4")),
    ("acot_sympy_adi_yanlis", "INCORRECT", _ir("acot(-1)", []), _sol("-pi/4")),
    ("acot_toplam_dogru", "CORRECT", _ir("arctan(-1) + arccot(-1)", []), _sol("pi/2")),
    ("acot_toplam_yanlis", "INCORRECT", _ir("arctan(-1) + arccot(-1)", []), _sol("-pi/2")),
    ("acot_adim_yanlis", "INCORRECT", _ir("arccot(-1)", []),
     _sol("3*pi/4", [("compute", "arccot(-1) = -pi/4"), ("compute", "-pi/4 + pi = 3*pi/4")])),
    ("acot_adim_dogru", "CORRECT", _ir("arccot(-1)", []),
     _sol("3*pi/4", [("compute", "arccot(-1) = pi/2 - arctan(-1)"), ("compute", "pi/2 + pi/4 = 3*pi/4")])),
    ("acot_latex_dogru", "CORRECT", _ir(r"\operatorname{arccot}(-1)", []), _sol("3*pi/4")),
    ("acot_latex_yanlis", "INCORRECT", _ir(r"\operatorname{arccot}(-1)", []), _sol("-pi/4")),
    # lcm/gcd with a symbol: n even -> lcm(n, 2) = n; the polynomial lcm says 2n
    ("lcm_cift_dogru_n", "CORRECT", _ir("lcm(n, 2)", NN, ["Mod(n, 2) = 0"]), _sol("n")),
    ("lcm_cift_yanlis_2n", "INCORRECT", _ir("lcm(n, 2)", NN, ["Mod(n, 2) = 0"]), _sol("2*n")),
    ("gcd_4_dogru", "CORRECT", _ir("gcd(n, 4)", NN, ["n = 12"]), _sol("4")),
    ("gcd_4_yanlis_1", "INCORRECT", _ir("gcd(n, 4)", NN, ["n = 12"]), _sol("1")),
    ("gcd_sayi_dogru", "CORRECT", _ir("gcd(84, 120)", []), _sol("12")),
    ("gcd_sayi_yanlis", "INCORRECT", _ir("gcd(84, 120)", []), _sol("6")),
    ("gcd_adim_yanlis", "INCORRECT", _ir("gcd(84, 120)", []),
     _sol("12", [("compute", "gcd(84, 120) = 6"), ("compute", "2*6 = 12")])),
    ("lcm_adim_sembol_yanlis", "INCORRECT", _ir("lcm(n, 2)", NN, ["n = 6"]),
     _sol("6", [("eq", "lcm(n, 2) = 2*n"), ("compute", "lcm(6, 2) = 6")])),
    # bound index: k declared positive_integer in the IR, the sum starts at 0 (0**0 = 1)
    ("sum_0k_dogru_1", "CORRECT", _ir("Sum(0**k, (k, 0, 5))", NK), _sol("1")),
    ("sum_0k_yanlis_0", "INCORRECT", _ir("Sum(0**k, (k, 0, 5))", NK), _sol("0")),
    ("sum_abs_dogru_6", "CORRECT", _ir("Sum(Abs(k), (k, -2, 2))", NK), _sol("6")),
    ("sum_abs_yanlis_0", "INCORRECT", _ir("Sum(Abs(k), (k, -2, 2))", NK), _sol("0")),
    ("sum_adim_yanlis", "INCORRECT", _ir("Sum(1/(k*(k + 1)), (k, 1, oo))", NK),
     _sol("1", [("compute", "Sum(Abs(k), (k, -2, 2)) = 0"), ("compute", "Sum(1/(k*(k + 1)), (k, 1, oo)) = 1")])),
    ("sum_teleskop_dogru", "CORRECT", _ir("Sum(1/(k*(k + 1)), (k, 1, oo))", NK),
     _sol("1", [("eq", "1/(k*(k + 1)) = 1/k - 1/(k + 1)"),
                ("compute", "Sum(1/k - 1/(k + 1), (k, 1, n)) = 1 - 1/(n + 1)"),
                ("compute", "Limit(1 - 1/(n + 1), n, oo) = 1")])),
    ("prod_sign_dogru", "CORRECT", _ir("Product(sign(k), (k, -3, -1))", NK), _sol("-1")),
    ("prod_sign_yanlis", "INCORRECT", _ir("Product(sign(k), (k, -3, -1))", NK), _sol("1")),
    ("latex_sum_dogru", "CORRECT", _ir(r"\sum_{k=0}^{5} 0^{k}", NK), _sol("1")),
    ("latex_sum_yanlis", "INCORRECT", _ir(r"\sum_{k=0}^{5} 0^{k}", NK), _sol("0")),
    ("i_indis_adim_yanlis", "INCORRECT", _ir("Sum(1/(k*(k + 1)), (k, 1, oo))", NK),
     _sol("1", [("compute", "Sum(i, (i, 1, 4)) = 11"), ("compute", "Sum(1/(k*(k + 1)), (k, 1, oo)) = 1")])),
    # the variable of a definite integral: x declared positive, the range is [-1, 1]
    ("int_abs_dogru", "CORRECT", _ir("Integral(Abs(x), (x, -1, 1))", [{"name": "x", "domain": "positive_real"}]),
     _sol("1")),
    ("int_abs_yanlis", "INCORRECT", _ir("Integral(Abs(x), (x, -1, 1))", [{"name": "x", "domain": "positive_real"}]),
     _sol("0")),
    # a Limit keeps the declared symbol: n integer makes it the limit of a sequence
    ("limit_dizi_dogru", "CORRECT", _ir("Limit(sin(pi*n), n, oo)", NN), _sol("0")),
    ("limit_dizi_yanlis", "INCORRECT", _ir("Limit(sin(pi*n), n, oo)", NN), _sol("1")),
]


def _verdict_rows():
    from mathverify.verifier import verify
    rows = []
    for name, want, ir, sol in VERDICT_CASES:
        try:
            r = verify(ir, sol)
            refuted = []
            for layer in r.layers:
                if layer.layer == "steps.refute":
                    refuted = [s["id"] for s in layer.evidence.get("steps", []) if s.get("status") == "refuted"]
            rows.append((name, want, r.verdict, r.first_bad_step, refuted,
                         [f"{l.layer}:{l.verdict}" for l in r.layers if l.verdict in ("pass", "fail")]))
        except Exception as e:  # noqa: BLE001
            rows.append((name, want, f"ERR {type(e).__name__}: {e}"[:120], None, [], []))
    return rows


if __name__ == "__main__":
    out = {"parse": _parse_rows(), "verdict": _verdict_rows()}
    for g, text, res, num in out["parse"]:
        print(f"[{g}] {text:42s} {res}   {num}")
    print()
    bad = flipped = 0
    for name, want, got, fbs, ref, hard in out["verdict"]:
        flip = {want, got} == {"CORRECT", "INCORRECT"}
        mark = "OK " if got == want else ("TERS" if flip else "?? ")
        bad += got != want
        flipped += flip
        print(f"{mark:4s}{name:26s} beklenen {want:9s} bulunan {got:9s} ilk_kotu={fbs} red={ref} {hard}")
    print(f"\nbeklenenden farklı: {bad}/{len(out['verdict'])}; ters karar (CORRECT <-> INCORRECT): {flipped}")
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
