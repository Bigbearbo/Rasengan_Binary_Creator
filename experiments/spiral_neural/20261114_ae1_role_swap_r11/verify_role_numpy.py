"""Independent no-Torch NumPy audit. First audits source 936 rows, then new role-swap raw.
Source verify_numpy.py implements its own F32 model and does NOT import the Torch runner.
"""
from pathlib import Path
import sys,json,hashlib,collections
import numpy as np
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'source'))
import verify_numpy as baseline
spec=json.loads((P/'prereg.json').read_text())
result=json.loads((P/'results.json').read_text())
raw_bytes=(P/'raw_cases.jsonl').read_bytes()
assert hashlib.sha256(raw_bytes).hexdigest()==result['raw_sha256']
rows=[json.loads(l) for l in raw_bytes.splitlines()]
assert len(rows)==168 and len(baseline.cache)==6

def logits(st,s,tied):
    assert 39<=len(s)<=80 and s[:9]=='010100100' and all(ch in '01' for ch in s)
    x=np.zeros((80,2),dtype='<f4')
    for i,ch in enumerate(s):x[i,int(ch)]=1
    data=x[9:33,:].reshape(4,12)
    if tied: emb=np.tanh(data@st['enc.weight'].T+st['enc.bias'])
    else:
        emb=np.empty((4,16),dtype='<f4')
        for i in range(4):emb[i]=np.tanh(data[i]@st['enc_w'][i].T+st['enc_b'][i])
    pos=np.zeros(33,dtype='<f4');pos[len(s)-39]=1
    feat=np.concatenate((emb.reshape(64),x[5:9,:].reshape(8),pos))
    hidden=np.tanh(st['hidden.weight']@feat+st['hidden.bias'])
    return st['out.weight']@hidden+st['out.bias']

steps=0;free_errors=[];tf_errors=[];count=collections.Counter();tolerance=0.00005
for i,row in enumerate(rows):
    seed,arm=row['seed'],row['arm']
    st=baseline.cache[(seed,arm)]
    q=row['Q'];answer=row['expected']
    assert len(q)==39 and q.startswith('01010') and q.endswith('111100')
    assert answer==q[9:15]+q[15:21]+'S',i
    actual='';cause='cap';n=0
    for _ in range(32):
        if len(q)+len(actual)>80:cause='overflow';break
        out=logits(st,q+actual,arm=='tied')
        actual+='01S'[int(out.argmax())];n+=1;steps+=1
        if actual[-1]=='S':cause='stop';break
    if (actual,cause,n)!=(row['actual'],row['cause'],row['forward_calls']):free_errors.append(i)
    assert n*10920>=0
    checks=[];margins=[]
    for k,target in enumerate(answer):
        p=logits(st,q+answer[:k],arm=='tied');steps+=1
        idx='01S'.index(target)
        checks.append(int(p.argmax())==idx)
        margins.append(float(p[idx]-max(p[j] for j in range(3) if j!=idx)))
    if checks!=row['tf_correct'] or any(abs(v-w)>tolerance for v,w in zip(margins,row['tf_margins'])):tf_errors.append((i,checks==row['tf_correct'],max(abs(v-w) for v,w in zip(margins,row['tf_margins']))))
    count[(seed,arm,row['role'],row['split'])]+=(actual==answer)
assert not free_errors and not tf_errors,(free_errors[:3],tf_errors[:3])
assert steps==sum(r['forward_calls']+len(r['expected']) for r in rows)
assert sum(r['source']=='new_torch' for r in rows)==84
assert result['new_free_forwards']==sum(r['forward_calls'] for r in rows if r['source']=='new_torch')
assert result['new_teacher_forwards']==sum(len(r['expected']) for r in rows)
for name,v in result['counts'].items():
    seed,arm,role,split=name.split('_',3)
    assert count[(int(seed),arm,role,split)]==v['exact']
print('INDEPENDENT-NUMPY PASS',len(rows),'complete responses,',steps,'all forward/teacher positions; zero mismatches')
