"""F5 sweep with NO model calls: deterministic statement + Mathlib tactic ladder + audits.

    python -m harness.run_lean [--limit N] [--timeout 45] [--out reports]

Measures the F5 gate directly: how many items get a formal certificate, and whether any
item whose claimed answer is WRONG is ever proved (must be zero: a false statement is
unprovable, so a proof here would mean the statement does not say what the claim says).
`lean_results.json` also records `lean_available`: whether the Mathlib REPL booted in this run,
so "zero certificates" never reads as a clean result when Lean was simply absent.
"""
from __future__ import annotations
import argparse, json, sys, time
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))
from harness.loader import load_items, split_for_verifier  # noqa: E402


def _answer_is_right(it, ir, sol, labels) -> bool:
    """Is the CLAIMED VALUE mathematically right? (The formal layer certifies the value, not
    the reasoning, so this is the reference a Lean proof must be judged against.)

    Cells A, B and D carry a correct answer by construction — including B items whose answer is
    a valid but non-canonical representative (e.g. a different eigenvector), which a literal
    comparison with the gold string would wrongly call wrong. Only C items need the comparison,
    because some of them are wrong solely in the option letter while the value is right.
    """
    import sympy as sp
    from mathverify.normalize.parse import build_namespace, parse_answer
    from mathverify.intake.structured import load_problem_ir
    from mathverify.equiv import answers_equivalent
    if labels["cell"] in ("A", "B", "D"):
        return True
    ca = sol["claimed_answer"]
    gold = it["gold_answer"]
    try:
        ns = build_namespace(load_problem_ir(ir))
        if ca["kind"] == "dne":
            return str(gold).strip().upper() == "DNE"
        a = parse_answer(ca["kind"], ca["payload"], ns)
        shape = "set" if isinstance(a, sp.Set) else ("count" if ca["kind"] == "count" else "scalar")
        b = parse_answer("set" if shape == "set" else ("count" if shape == "count" else "value"), gold, ns)
        ok, _ = answers_equivalent(a, b, shape=shape)
        return bool(ok)
    except Exception:
        return False


# Claims that are FALSE in real mathematics but TRUE about Lean's totalised operations
# (x/0 = 0, sqrt of a negative = 0, log 0 = 0, tan(pi/2) = 0, the integral of a non-integrable
# function = 0). Before the definedness guards in formal/statement.py, five of these received
# clean, audited certificates. Every run re-checks them: a single certificate here is a false
# positive of the formal layer, whatever the evaluation set says.
def _ir(kind, params, vars_=(), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": [dict(v) for v in vars_],
            "givens": list(givens), "answer_shape": shape}


JUNK_PROBES = [
    ("tan(pi/2) = 0", _ir("evaluate", {"expr": "tan(pi/2)"}), {"kind": "value", "payload": "0"}),
    ("sqrt(2-5) = 0", _ir("evaluate", {"expr": "sqrt(2 - 5)"}), {"kind": "value", "payload": "0"}),
    ("0/0 = 0", _ir("evaluate", {"expr": "(2**2 - 4)/(2 - 2)"}), {"kind": "value", "payload": "0"}),
    ("log 0 = 0", _ir("evaluate", {"expr": "log(0)"}), {"kind": "value", "payload": "0"}),
    ("sin 0 = sqrt(-4)", _ir("evaluate", {"expr": "sin(0)"}), {"kind": "value", "payload": "sqrt(-4)"}),
    ("int_{-1}^{1} dx/x = 0", _ir("definite_integral", {"integrand": "1/x", "var": "x", "a": "-1", "b": "1"},
                                  [{"name": "x"}]), {"kind": "value", "payload": "0"}),
    ("sqrt'(-1) = 0", _ir("derivative", {"f": "sqrt(x)", "var": "x", "at": "-1"}, [{"name": "x"}]),
     {"kind": "value", "payload": "0"}),
    ("log'(-1) = -1", _ir("derivative", {"f": "log(x)", "var": "x", "at": "-1"}, [{"name": "x"}]),
     {"kind": "value", "payload": "-1"}),
    ("max -1/x^2 on [-1,1] = 0", _ir("extremum", {"f": "-1/x**2", "var": "x", "interval": "[-1, 1]", "which": "max"},
                                     [{"name": "x"}]), {"kind": "value", "payload": "0"}),
    ("sum_{k=-1}^{1} 1/k = 0", _ir("series_sum", {"term": "1/k", "var": "k", "lo": "-1", "hi": "1"},
                                   [{"name": "k", "domain": "integer"}]), {"kind": "value", "payload": "0"}),
    ("x = 2 from 1/(x-2) = 0", _ir("evaluate", {"expr": "x"}, [{"name": "x"}], ["1/(x - 2) = 0"]),
     {"kind": "value", "payload": "2"}),
    ("(sqrt(-x^2-1))' = 0", _ir("derivative", {"f": "sqrt(-x**2 - 1)", "var": "x"}, [{"name": "x"}], shape="expression"),
     {"kind": "expression", "payload": "0"}),
    # templates added 23 Sep (domain_of, simplify_expression, count_solutions)
    ("sqrt(-x^2-1) simplifies to 0", _ir("simplify_expression", {"expr": "sqrt(-x**2 - 1)"}, [{"name": "x"}],
                                        shape="expression"), {"kind": "expression", "payload": "0"}),
    ("1/(x-x) simplifies to 0", _ir("simplify_expression", {"expr": "1/(x - x)"}, [{"name": "x"}], shape="expression"),
     {"kind": "expression", "payload": "0"}),
    ("x simplifies to x^2/x", _ir("simplify_expression", {"expr": "x"}, [{"name": "x"}], shape="expression"),
     {"kind": "expression", "payload": "x**2/x"}),
    ("domain of 1/(x-2) is R", _ir("domain_of", {"expr": "1/(x - 2)", "var": "x"}, [{"name": "x"}], shape="set"),
     {"kind": "set", "payload": "(-oo, oo)"}),
    ("#{x/y = 0 in [0,2]^2} = 6 (Z division)",
     _ir("count_solutions", {"bounds": {"x": ["0", "2"], "y": ["0", "2"]}},
         [{"name": "x", "domain": "nonneg_integer"}, {"name": "y", "domain": "nonneg_integer"}], ["x/y = 0"],
         shape="count"), {"kind": "count", "payload": 6}),
]


def junk_probe(timeout: float) -> list[dict]:
    from mathverify.formal import build_statement, prove_statement
    out = []
    for label, ir, ca in JUNK_PROBES:
        st = build_statement(ir, ca)
        rec = {"label": label, "statement": bool(st), "certified": False}
        if st is not None:
            r = prove_statement(st, use_model=False, tactic_timeout=timeout)
            rec["certified"] = bool(r["proved"] and (r.get("audit") or {}).get("clean"))
            rec["proved"] = r["proved"]
        out.append(rec)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    # 45 s is what scripts/check.py and every report use; measured on 23 Sep, 60 s certifies the
    # same 107 items, so the standalone default now matches the gate
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--out", default=str(ROOT / "reports"))
    args = ap.parse_args(argv)
    from mathverify.formal import build_statement, prove_statement, lean_available
    items = load_items(ROOT / "evalset" / "items")
    if args.limit:
        items = items[:args.limit]
    t0 = time.time()
    # "Lean was available in this run" = this probe, before the sweep, came back clean. It goes
    # through the same thread-local client the sweep uses (get_lean), so the REPL it boots is the
    # one that proves the items, never a second one. Clean requires all of: the REPL process
    # started, `import Mathlib` returned an environment, LeanClient._spawn's Mathlib probe
    # ((2 : ℝ) + 2 = 4 by norm_num) compiled, and a first check on that environment compiled with
    # no error and no sorry. Without this flag a machine with no Lean at all wrote 0 certificates
    # with exit 0, and check.py's Lean gates passed vacuously on it. The sweep itself is not
    # changed: when the probe fails, every item is still attempted, exactly as before.
    lean_ok = lean_available()
    print(f"lean_available={lean_ok}", flush=True)
    recs, kinds = [], Counter()
    for i, it in enumerate(items, 1):
        ir, sol, labels = split_for_verifier(it)
        st = build_statement(ir, sol["claimed_answer"])
        rec = {"id": it["id"], "cell": labels["cell"], "topic": labels["topic"],
               # the formal layer certifies the claimed VALUE, so the reference is the value
               # itself: a C item whose only defect is the option letter has a right value
               "answer_right": _answer_is_right(it, ir, sol, labels), "task": ir["task"]["kind"],
               "statement": bool(st), "kind": st.kind if st else None, "proved": False, "clean": None}
        if st is not None:
            kinds[st.kind] += 1
            r = prove_statement(st, use_model=False, tactic_timeout=args.timeout)
            rec.update({"proved": r["proved"], "clean": (r.get("audit") or {}).get("clean"),
                        "proof": r.get("proof"), "audit": r.get("audit"), "ms": round(r["ms"]),
                        "stmt_text": r.get("statement")})
        recs.append(rec)
        if i % 20 == 0 or rec["proved"]:
            print(f"[{i}/{len(items)}] {rec['id']:<16} stmt={rec['statement']} proved={rec['proved']} clean={rec['clean']}", flush=True)
    n = len(recs)
    with_stmt = [r for r in recs if r["statement"]]
    proved = [r for r in recs if r["proved"]]
    certified = [r for r in proved if r["clean"]]
    fp = [r for r in certified if not r["answer_right"]]
    out = Path(args.out); out.mkdir(exist_ok=True)
    junk = junk_probe(args.timeout)
    (out / "lean_results.json").write_text(json.dumps({"lean_available": lean_ok, "records": recs, "junk_probe": junk},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    md = "# F5 (Lean) taraması — modelsiz, deterministik ifade + Mathlib taktik merdiveni\n\n"
    md += f"- Lean REPL (Mathlib) bu koşuda açıldı: **{'evet' if lean_ok else 'hayır'}**\n"
    md += f"- Öğe: **{n}** · Lean ifadesi üretilebilen: **{len(with_stmt)}** ({len(with_stmt)/n:.1%})\n"
    md += f"- Kanıtlanan: **{len(proved)}** · denetimden geçen (sorry/aksiyom/vakum/kullanılmayan hipotez): **{len(certified)}**\n"
    md += f"- **Yanlış cevaplı öğelerde kanıt (FP): {len(fp)}** {'✓ hedef 0' if not fp else '✗ ' + str([r['id'] for r in fp])}\n"
    md += f"- Kapsama (tüm sette formal sertifika): {len(certified)/n:.1%} · ifadesi olanlar içinde: {len(certified)/max(1,len(with_stmt)):.1%}\n"
    md += f"- Şablon türleri: {dict(kinds)}\n"
    md += f"- Süre: {time.time()-t0:.0f} s (ortalama {(time.time()-t0)/n*1000:.0f} ms/öğe)\n\n"
    bad_junk = [j["label"] for j in junk if j["certified"]]
    md += (f"- **Junk-value sondası:** {len(junk)} gerçekte yanlış iddia (Lean'in x/0 = 0, √(−1) = 0, "
           f"log 0 = 0 gibi tamamlamalarında doğru) · ifade üretilen: {sum(j['statement'] for j in junk)} · "
           f"**sertifika alan: {len(bad_junk)}** (hedef 0){' ✗ ' + str(bad_junk) if bad_junk else ' ✓'}\n\n")
    byc = Counter(r["cell"] for r in certified)
    md += f"- Sertifikalı öğelerin hücre dağılımı: {dict(byc)} (D hücresi = cevabı doğru, adımı bozuk: formal katman cevabı onaylar, adımı değil)\n"
    used = Counter(r["proof"] for r in certified)
    md += f"- Kullanılan taktikler: {dict(used)}\n"
    unproved = [r for r in with_stmt if not r["proved"]]
    md += f"\n## İfadesi üretilip kanıtlanamayanlar ({len(unproved)})\n\n"
    for r in unproved[:40]:
        md += f"- {r['id']} [{r['kind']}] {('cevap doğru' if r['answer_right'] else 'cevap YANLIŞ (kanıtlanamaması beklenir)')}: `{(r.get('stmt_text') or '')[:150]}`\n"
    (out / "lean_report.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
