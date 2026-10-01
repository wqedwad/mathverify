"""Aggregate verifier results from all workflow journals -> d4/dogrulama.json; print a table."""
import glob, json, re, sys
W = "/root/.claude/projects/-home-user-asd/fce620cb-7571-5f23-8c9b-4899ea468c22/subagents/workflows"
S = "$SP/d4"
res = {}
for J in glob.glob(W + "/*/journal.jsonl"):
    lab = {}
    for line in open(J):
        e = json.loads(line)
        if "label" in e:
            lab[e["agentId"]] = e["label"]
        if "result" in e and e["agentId"] in lab:
            m = re.match(r"(yeniden|supheci):([^:]+):(.+)", lab[e["agentId"]])
            if m and isinstance(e["result"], dict):
                k = (m.group(2), m.group(3))
                res.setdefault(k, {})["A" if m.group(1) == "yeniden" else "B"] = e["result"]
finds = {}
for p in glob.glob(S + "/*/bulgular.json"):
    a = p.split("/")[-2]
    d = json.load(open(p)); fs = d["findings"] if isinstance(d, dict) else d
    for f in fs:
        finds[(a, f["id"])] = f
out = []
for k in sorted(finds):
    f = finds[k]; r = res.get(k, {})
    A, B = r.get("A"), r.get("B")
    st = "?"
    if A and B:
        a_ok = A["reproduced"] and A["real_bug"]
        st = "DOGRULANDI" if a_ok and not B["refuted"] else ("CURUTULDU" if (not a_ok and B["refuted"]) else "CEKISMELI")
    elif A or B:
        st = "yarim"
    out.append({"key": k[0], "id": k[1], "status": st, "finding": f, "A": A, "B": B})
    if "-q" not in sys.argv:
        print(f"{k[0]:11s} {k[1]:7s} {st:10s} {f['klass']:20s} {f['severity']:6s} known={f.get('known')} "
              f"A={'-' if not A else (A['reproduced'], A['real_bug'], A['pre_existing'])} "
              f"B={'-' if not B else ('refuted' if B['refuted'] else 'ok')}")
json.dump(out, open(S + "/dogrulama.json", "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(Counter(o["status"] for o in out))
