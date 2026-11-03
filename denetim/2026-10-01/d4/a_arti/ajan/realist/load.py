import json, glob
S='/tmp/claude-0/-home-user-asd/f97a07bd-dea8-5bbe-88dc-ada419b43e01/scratchpad'
def load():
    items={}
    for f in sorted(glob.glob(S+'/ed/evalset/items/*.json')):
        it=json.load(open(f)); items[it['id']]=it
    k4={}
    for r in json.load(open(S+'/ed/reports/arsiv/2026-09-28/solver_meta_results.json'))['records']:
        if r.get('solution') is not None: k4[r['id']]=r
    verd=json.load(open(S+'/ed/denetim/2026-10-01/d4/fark_782431c.json'))
    return items,k4,verd
def ir_text(it):
    ir=dict(it['problem_ir']); ir.pop('options',None); ir.pop('level',None); ir.pop('topic',None)
    return json.dumps(ir,ensure_ascii=False)
def opt_text(it):
    return json.dumps(it['problem_ir'].get('options') or {},ensure_ascii=False)
def sol_texts(sol):
    """list of (where, text) for claim-like fields of a solution"""
    out=[]
    ca=sol.get('claimed_answer') or {}
    out.append(('answer',str(ca.get('payload',''))))
    for s in sol.get('steps',[]):
        if s.get('claim'): out.append(('claim:'+s['id'],s['claim']))
    return out
def sol_prose(sol):
    return ' '.join((s.get('text') or '') for s in sol.get('steps',[]))+' '+(sol.get('raw_text') or '')
