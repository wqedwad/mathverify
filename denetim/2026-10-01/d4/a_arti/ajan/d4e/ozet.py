import json,sys
p=sys.argv[1]
d=json.load(open(p))
bs=d['bulgular'] if isinstance(d,dict) else d
if isinstance(d,dict): print(d['parca'], d['toplam'], d['dogrulanan'])
for b in bs:
    v=b.get('verdict') or {}
    print('==', b.get('id'), b.get('lens'), b.get('klass'), b.get('severity'), 'intro:', b.get('introduced_by_piece'))
    print('   T:', b.get('title'))
    print('   V: real=%s sev=%s intro=%s' % (v.get('real'), v.get('severity'), v.get('introduced_by_piece')))
    if len(sys.argv)>2: print('   MECH:', (b.get('mechanism') or '')[:600])
