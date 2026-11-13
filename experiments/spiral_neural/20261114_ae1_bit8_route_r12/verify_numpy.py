"""Independent pure-NumPy inference of fixed AE1 checkpoints, no torch, no probe import."""
import json,base64,hashlib
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
S=P/'source'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[json.loads(x) for x in (P/'logits.jsonl').read_text().splitlines()]
pairs=[json.loads(x) for x in (P/'pairs.jsonl').read_text().splitlines()]
res=json.loads((P/'results.json').read_text());assert sha(P/'logits.jsonl')==res['logits_sha256']
assert sha(P/'pairs.jsonl')==res['pairs_sha256']
def state(seed,arm):
    v=json.loads((S/'checkpoints'/f'weights_{seed}_{arm}.json').read_text())
    return {k:np.frombuffer(base64.b64decode(a['little_endian_base64']),dtype='<f4').reshape(a['shape']).copy() for k,a in v['tensors'].items()}
cache={}
def infer(st,row):
    s=row['Q']+row['prefix']
    x=np.zeros((80,2),dtype=np.float32)
    for i,t in enumerate(s):x[i,int(t)]=1.
    w=x[9:33].reshape(4,12)
    if row['arm']=='tied':e=np.tanh(w@st['enc.weight'].T+st['enc.bias'])
    else:
        e=np.stack([np.tanh(w[j]@st['enc_w'][j].T+st['enc_b'][j]) for j in range(4)])
    cursor=len(s)-39;pos=np.zeros(33,dtype=np.float32);pos[cursor]=1
    f=np.concatenate([e.reshape(64),x[5:9].reshape(8),pos])
    hidden=np.tanh(st['hidden.weight']@f+st['hidden.bias'])
    logits=st['out.weight']@hidden+st['out.bias']
    return logits,e[0 if row['role']=='first' else 1]
max_error=0.;max_embed_error=0.
lookup={}
for row in rows:
    key=(row['seed'],row['arm'])
    if key not in cache:cache[key]=state(*key)
    logits,emb=infer(cache[key],row)
    err=np.max(np.abs(logits-np.array(row['logits'])))
    ee=np.max(np.abs(emb-np.array(row['embedding'])))
    max_error=max(max_error,float(err));max_embed_error=max(max_embed_error,float(ee))
    assert err<1.5e-4 and ee<1.5e-5,(key,err,ee)
    assert abs(float(logits[1]-logits[0])-row['margin_1_minus_0'])<1.5e-4
    lookup[key+(row['role'],row['low'],row['anchor'],row['flip'])]=row
for p in pairs:
    k=(p['seed'],p['arm'],p['role'],p['low'],p['anchor'])
    old=lookup[k+(0,)];new=lookup[k+(8,)]
    assert abs(p['margin_delta']-(new['margin_1_minus_0']-old['margin_1_minus_0']))<1e-5
    assert abs(p['embedding_delta_l2']-np.linalg.norm(np.array(new['embedding'])-np.array(old['embedding'])))<1e-5
assert len(rows)==192 and len(pairs)==96 and len(cache)==6 and res['total_forward_dense_mac']==192*10920
print('INDEPENDENT_NUMPY PASS',len(rows),'logit vectors,',len(pairs),'paired interventions, max_abs_logit_err',max_error,'max_abs_emb_err',max_embed_error)
