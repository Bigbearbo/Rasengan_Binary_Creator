"""Independent NumPy-only F32 inference of 01 SLE native string outputs.
Does not import run.py, torch or reuse trained model's inference function.
"""
import json,base64,hashlib,collections
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
spec=json.loads((P/'prereg.json').read_text()); report=json.loads((P/'results.json').read_text())
raw=(P/'raw_cases.jsonl').read_bytes(); rows=[json.loads(z) for z in raw.splitlines()]
assert hashlib.sha256(raw).hexdigest()==report['raw_sha256']
assert hashlib.sha256((P/'run.py').read_bytes()).hexdigest()==spec['runner_sha256']
assert hashlib.sha256((P/'manifest.jsonl').read_bytes()).hexdigest()==spec['manifest_sha256']
assert hashlib.sha256((P/'parent_course.json').read_bytes()).hexdigest()==spec['parent_sha256']
manifest=[json.loads(z) for z in (P/'manifest.jsonl').read_text().splitlines()]
assert len(manifest)==156

cache={}
def get(seed,arm):
    path=P/'checkpoints'/f'weights_{seed}_{arm}.json'
    meta=next(x for x in report['blocks'] if x['seed']==seed and x['arm']==arm)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['checkpoint_sha256']
    j=json.loads(path.read_text())
    assert j['seed']==seed and j['arm']==arm and j['tied']==(arm=='tied')
    return {k:np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').reshape(v['shape']).copy() for k,v in j['tensors'].items()}

def step(st,s,tied):
    assert len(s)<=80 and set(s)<={'0','1'} and s[:5]=='01010'
    cur=len(s)-39
    assert 0<=cur<=32
    x=np.zeros((80,2),dtype=np.float32)
    for i,v in enumerate(s): x[i,int(v)]=1
    word=x[9:33,:].reshape(4,12)
    if tied:
        embed=np.tanh((word@st['enc.weight'].T).astype('<f4')+st['enc.bias'])
    else:
        embed=np.empty((4,16),dtype='<f4')
        for k in range(4):embed[k]=np.tanh(word[k]@st['enc_w'][k].T+st['enc_b'][k])
    pos=np.zeros(33,dtype=np.float32);pos[cur]=1
    feature=np.concatenate((embed.reshape(64),x[5:9,:].reshape(8),pos))
    h=np.tanh(st['hidden.weight']@feature+st['hidden.bias'])
    logits=st['out.weight']@h+st['out.bias']
    return '01S'[int(np.argmax(logits))]

tot=0;errors=[];counts=collections.Counter()
for i,v in enumerate(rows):
    id=(v['seed'],v['arm'])
    if id not in cache:cache[id]=get(*id)
    st=cache[id];q=v['Q'];actual='';cause='cap';n=0
    for _ in range(32):
        if len(q)+len(actual)>80:cause='overflow';break
        actual+=step(st,q+actual,v['arm']=='tied');n+=1
        if actual[-1]=='S':cause='stop';break
    tot+=n
    if (actual,cause,n,actual==v['expected'])!=(v['actual'],v['cause'],v['forward_calls'],v['exact']):
        errors.append((i,v['actual'],actual,v['cause'],cause))
    counts[(v['seed'],v['arm'],v['split'])]+=(actual==v['expected'])
assert len(rows)==936 and len(cache)==6 and tot==report['inference_forward_calls']
assert tot*10920==report['inference_MAC']
for b in report['blocks']:
    for split,m in b['metrics'].items():
        assert counts[(b['seed'],b['arm'],split)]==m['correct']
print('NUMPY-INDEPENDENT',len(rows)-len(errors),'/',len(rows), 'forward',tot,'errors',errors[:3]);assert not errors
