"""Verdict + step statuses of chosen corpus units (evalset/<id>, k4/<id>) on the checkout in PYTHONPATH,
compared with denetim/2026-10-01/d4/fark_782431c.json (edison's recorded dump). Run from the checkout root.

usage: python probe_units.py evalset/uni-002 k4/ayt-lim-003 ...
"""
import json
import sys
import time
from pathlib import Path

ED = '/tmp/claude-0/-home-user-asd/f97a07bd-dea8-5bbe-88dc-ada419b43e01/scratchpad/ed'

if __name__ == '__main__':
    from harness.loader import load_items, split_for_verifier
    from mathverify.verifier import verify
    ref = json.loads(Path(ED + '/denetim/2026-10-01/d4/fark_782431c.json').read_text(encoding='utf-8'))
    items = {it['id']: it for it in load_items(Path('evalset/items'))}
    recs = {r['id']: r for r in json.loads(Path(ED + '/reports/arsiv/2026-09-28/solver_meta_results.json')
                                           .read_text(encoding='utf-8'))['records']}
    for key in sys.argv[1:]:
        corp, iid = key.split('/')
        ir, sol, _ = split_for_verifier(items[iid])
        if corp == 'k4':
            sol = recs[iid]['solution']
        t0 = time.time()
        try:
            r = verify(ir, sol)
            steps = {}
            for layer in r.layers:
                if layer.layer == 'steps.refute':
                    steps = {s['id']: s.get('status') for s in layer.evidence.get('steps', [])}
            v, fbs = r.verdict, r.first_bad_step
        except Exception as e:  # noqa: BLE001
            v, fbs, steps = 'EXC:' + type(e).__name__, None, {}
        old = ref[key]
        dsteps = {k: (old['steps'].get(k), steps.get(k)) for k in set(old['steps']) | set(steps)
                  if old['steps'].get(k) != steps.get(k)}
        same = 'SAME' if (v == old['verdict'] and fbs == old['first_bad_step'] and not dsteps) else 'DIFF'
        print(f"{same} {key:22} {time.time() - t0:5.1f}s verdict {old['verdict']}->{v} fbs {old['first_bad_step']}->{fbs}"
              f" steps {dsteps}", flush=True)
