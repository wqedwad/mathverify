import json,sys
p=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 700
d=json.load(open(p))
bs=d['bulgular'] if isinstance(d,dict) else d
for b in bs:
    v=b.get('verdict') or {}
    print('=====', b.get('id'), b.get('klass'), 'sev', b.get('severity'), '->', v.get('severity'), 'intro', b.get('introduced_by_piece'), '->', v.get('introduced_by_piece'))
    print('T:', b.get('title'))
    print('REPRO:', (b.get('repro') or '')[:n])
    print('EXP:', (b.get('expected') or '')[:300])
    print('NOTE:', (v.get('note') or '')[:400])
