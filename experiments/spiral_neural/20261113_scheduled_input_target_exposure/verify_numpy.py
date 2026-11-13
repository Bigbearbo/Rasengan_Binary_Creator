"""Independent NumPy-only replay of four frozen trained PyTorch checkpoints.
No import of the training implementation, and no optimizer or teacher model.
"""
import base64
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
EXPECTED_ROWS = 936
PARAMS = 10499

def word(x):
    assert isinstance(x,int) and 0 <= x <= 29
    return format(x, '05b')+'0'

def native_q(r,a,b,c,d):
    assert r in (1,2)
    return '01010'+format(r,'03b')+'0'+''.join(word(x) for x in (a,b,c,d))+'111100'

def native_answer(r,a,b):
    return word(a)+(word(b) if r==2 else '')+'S'

def load_model(name, expected_sha):
    ck = json.loads((HERE/name).read_text())
    tensors={}
    checksum=hashlib.sha256()
    for k in ['0.weight','0.bias','2.weight','2.bias']:
        item=ck['tensors'][k]
        raw=base64.b64decode(item['little_endian_base64'], validate=True)
        shape=tuple(item['shape'])
        arr=np.frombuffer(raw,dtype='<f4').reshape(shape)
        assert arr.size*4 == len(raw)
        checksum.update(k.encode()); checksum.update(raw)
        tensors[k]=arr
    assert sum(x.size for x in tensors.values())==PARAMS
    assert checksum.hexdigest()==expected_sha==ck['weights_sha256']
    return tensors

def predict(t,Q):
    out=''
    n=0
    for _ in range(32):
        s=Q+out
        if len(s)>80:
            return out,'overflow',n
        # Independent vectorized version of 80 binary one-hot slots.
        x=np.zeros(160,dtype=np.float32)
        for i,bit in enumerate(s):
            assert bit in '01'
            x[2*i+int(bit)]=1
        hidden=np.tanh(t['0.weight']@x + t['0.bias'])
        logits=t['2.weight']@hidden+t['2.bias']
        out+='01S'[int(np.argmax(logits))]
        n+=1
        if out.endswith('S'):
            return out,'stop',n
    return out,'cap',n

def main():
    results=json.loads((HERE/'results.json').read_text())
    raw=(HERE/'raw_cases.jsonl').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==results['raw_sha256']
    rows=[json.loads(x) for x in raw.decode().splitlines()]
    assert len(rows)==results['raw_count']==EXPECTED_ROWS
    refs={(m['seed'],m['arm']):m for m in results['models']}
    assert set(refs)=={(s,a) for s in [101,202] for a in ['HIGH_OUTPUT','HIGH_INPUT_ONLY']}
    models={key:load_model(m['checkpoint'],m['weights_sha256']) for key,m in refs.items()}
    grouped=Counter(); forward=Counter(); wrong_examples=[]
    for row in rows:
        k=(row['seed'],row['arm'])
        assert len(row['Q'])==39 and row['Q']==native_q(*(row[z] for z in ['r','a','b','c','d']))
        assert row['expected']==native_answer(*(row[z] for z in ['r','a','b']))
        predicted,cause,n=predict(models[k],row['Q'])
        assert (predicted,cause,n)==(row['actual'],row['cause'],row['forward_calls']), (k,row['split'],row['Q'],predicted,row['actual'])
        grouped[(k,row['split'])]+=1
        forward[k]+=n
    assert len(grouped)==len(refs)*9
    assert sum(forward.values())==results['eval_forward']
    for key, ref in refs.items():
        assert forward[key]==sum(x['forward_calls'] for x in ref['metrics'].values())
        for split,agg in ref['metrics'].items():
            part=[x for x in rows if (x['seed'],x['arm'],x['split'])==(key[0],key[1],split)]
            assert len(part)==agg['n']==grouped[(key,split)]
            assert sum(x['actual']==x['expected'] for x in part)==agg['exact']
            assert sum(x['actual'].endswith('S') and len(x['actual'])==len(x['expected']) for x in part)==agg['stop_position']
    assert results['total_updates']==15200
    assert results['total_train_targets']==960000
    assert results['training_forward_dense_MAC']==10014720000
    assert results['eval_forward_dense_MAC']==99907264
    print('NUMPY VERIFY PASS; rows=936; four float32 checkpoints/weights SHA verified;')
    print('independent 9577 forward greedy decisions; all raw 0/1/S, cause and steps exact; gate/metrics/MAC exact')
    print('RAW SHA256',hashlib.sha256(raw).hexdigest())

if __name__=='__main__': main()
