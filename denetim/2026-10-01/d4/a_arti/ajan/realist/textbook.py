import sys, types, os
Q='/tmp/claude-0/-home-user-asd/f97a07bd-dea8-5bbe-88dc-ada419b43e01/scratchpad/scr/d4/duzeltme/d4e/r4'
def load_textbook():
    m=types.ModuleType('mathverify'); v=types.ModuleType('mathverify.verifier'); v.verify=None
    sys.modules.setdefault('mathverify',m); sys.modules['mathverify.verifier']=v
    sys.path.insert(0,Q+'/q')
    import importlib
    out=[]
    for name,res in (('kap','kap_eski.txt'),('kap2','kap2_eski.txt')):
        mod=importlib.import_module(name)
        lines=[l.split() for l in open(Q+'/'+res)]
        new=[l.split() for l in open(Q+'/'+res.replace('eski','now'))]
        assert len(lines)==len(mod.CASES)
        for (label,q,s),l,n in zip(mod.CASES,lines,new):
            out.append(dict(src=name,label=label,ir=q,sol=s,verdict=l[0],verdict_d4e4=n[0]))
    sys.path.pop(0)
    return out
if __name__=='__main__':
    tb=load_textbook(); print(len(tb))
    import collections; print(collections.Counter(t['verdict'] for t in tb))
