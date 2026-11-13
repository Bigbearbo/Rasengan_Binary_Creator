"""Standalone independent native-bit generator and checkpoint-free generation replay.
Does not call the trainer's xvec, qbits, answer, model factory or free-generation helpers.
"""
import base64,hashlib,json
from pathlib import Path
import numpy as np
import torch
from torch import nn
P=Path(__file__).parent
protocol=json.loads((P/'protocol.json').read_text())
r=json.loads((P/'results.json').read_text())
raw=(P/'raw_cases.jsonl').read_bytes()
assert hashlib.sha256(raw).hexdigest()==r['raw_sha256']
rows=[json.loads(ln) for ln in raw.splitlines()]
assert len(rows)==r['total_raw_cases']==360

def word(v):
    assert 0<=v<=29
    return format(v,'05b')+'0'

def mkq(r,a,b): return '01010'+format(r,'03b')+'0'+word(a)+word(b)+word(0)+word(0)+'111100'

def truth(r,a,b):return word(a)+(word(b) if r==2 else '')+'S'

def inp(s):
    assert 0<len(s)<=80 and all(c in '01' for c in s)
    v=np.zeros(160,dtype=np.float32)
    for i,c in enumerate(s):v[2*i+(c=='1')]=1
    return torch.from_numpy(v).unsqueeze(0)

@torch.no_grad()
def generate(m,q):
    a=''
    for step in range(32):
        if len(q)+len(a)>80:return a,'overflow',step
        pred=int(torch.argmax(m(inp(q+a))[0]).item())
        a+='01S'[pred]
        if pred==2:return a,'stop',step+1
    return a,'cap',32

unique=set()
for x in rows:
    key=tuple(x[k] for k in ('seed','split','r','a','b'))
    assert key not in unique,key
    unique.add(key)
    assert x['arm']=='MIX_PARITY' and x['Q']==mkq(x['r'],x['a'],x['b']) and x['expected']==truth(x['r'],x['a'],x['b'])
    assert x['c']==x['d']==0 and len(x['Q'])==39
    a,b=x['a'],x['b'];s=x['split']
    if s.startswith('base_'):
        assert a<6 and b<6
        assert (a+b)%6==({'base_val':0,'base_test':1}.get(s,2) if s!='base_train' else (a+b)%6)
        if s=='base_train':assert (a+b)%6 not in (0,1)
    elif s=='mixed_taught_orientation':
        assert x['r']==2
        assert ((a>=6 and b<=3 and (a-6+b)%2==0) or (b>=6 and a<=3 and (b-6+a)%2==1))
    elif s=='inverse_not_taught':
        assert x['r']==2
        assert ((a>=6 and b<=3 and (a-6+b)%2==1) or (b>=6 and a<=3 and (b-6+a)%2==0))
    elif s.startswith('heldout_'):
        assert x['r']==2
        assert (b if a>=6 else a)==(4 if 's4_' in s else 5)
        assert (a>=6 if s.endswith('high_first') else b>=6)
    else:raise AssertionError(s)

seen=0
for model in r['models']:
    seed=model['seed'];cp=json.loads((P/model['checkpoint']).read_text())
    assert cp['seed']==seed and cp['mode']=='MIX_PARITY'
    assert cp['weights_sha256']==model['final_sha256']
    m=nn.Sequential(nn.Linear(160,64),nn.Tanh(),nn.Linear(64,3))
    sd={}
    for name,v in cp['tensors'].items():
        arr=np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').copy().reshape(v['shape'])
        sd[name]=torch.from_numpy(arr)
    m.load_state_dict(sd)
    sha=hashlib.sha256()
    for name,t in m.state_dict().items():sha.update(name.encode());sha.update(t.numpy().tobytes())
    assert sha.hexdigest()==model['final_sha256']
    for case in rows:
        if case['seed']!=seed:continue
        actual,why,n=generate(m,case['Q'])
        assert actual==case['actual'] and why==case['cause'] and n==case['forward_calls'],(seed,case)
        seen+=1
    assert sum(c['seed']==seed for c in rows)==180
assert seen==360
assert r['all_new_optimizer_steps']==7500 and r['all_new_target_exposures']==474000
assert r['all_new_training_dense_forward_MAC']==474000*10432
print('PASS 360/360 independent checkpoint reload + native Q/answer + free generation, exact per-case; splits and costs verified')