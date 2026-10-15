"""Verdicts of selected textbook (d4e r4 kap/kap2) cases on the checkout in PYTHONPATH.

usage: python probe_tb.py <label> [<label> ...]   (labels as in kap.py/kap2.py; 'ALL' for every case)
Prints: verdict, seconds, label, edison verdict (kap_eski), d4e-r4 verdict (kap_now).
"""
import json
import sys
import time

sys.path.insert(0, '/tmp/claude-0/-home-user-asd/f97a07bd-dea8-5bbe-88dc-ada419b43e01/scratchpad/wf/realist')


def cases():
    import textbook
    return textbook.load_textbook()


if __name__ == '__main__':
    want = set(sys.argv[1:])
    tb = cases()
    for k in [k for k in sys.modules if k == 'mathverify' or k.startswith('mathverify.')]:
        del sys.modules[k]
    from mathverify.verifier import verify
    out = []
    for c in tb:
        if 'ALL' not in want and c['label'] not in want:
            continue
        t0 = time.time()
        try:
            v = verify(c['ir'], c['sol']).verdict
        except Exception as e:  # noqa: BLE001
            v = 'EXC:' + type(e).__name__
        out.append((c['label'], v, c['verdict'], c['verdict_d4e4']))
        print(f"{v:9} {time.time() - t0:5.1f}s  edison={c['verdict']:9} d4e4={c['verdict_d4e4']:9} {c['label']}", flush=True)
    json.dump(out, open(sys.argv[0] + '.' + str(int(time.time())) + '.json', 'w'))
