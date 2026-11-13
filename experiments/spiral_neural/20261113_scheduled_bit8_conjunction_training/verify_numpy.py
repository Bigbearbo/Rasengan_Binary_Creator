"""Independent NumPy-only full free-generation verifier; no torch, no import from run.py."""
import base64,collections,hashlib,json,sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent

def model(seed,arm):
    src=json.loads((P/f'weights_seed{seed}_{arm}.json').read_text())
    tensors={}
    for key,z in src['tensors'].items():
        tensors[key]=np.frombuffer(base64.b64decode(z['little_endian_base64']),dtype='<f4').copy().reshape(z['shape'])
    h=hashlib.sha256()
    for key,value in tensors.items():h.update(key.encode());h.update(value.tobytes())
    assert h.hexdigest()==src['weights_sha256'],(seed,arm,'statehash')
    return [tensors['0.weight'],tensors['0.bias'],tensors['2.weight'],tensors['2.bias']]

def parse_q(q):
    assert len(q)==39 and q.startswith('01010') and q.endswith('111100') and set(q)<={'0','1'}
    r=int(q[5:8],2)
    assert r in (1,2) and q[8]=='0'
    words=[q[9+6*i:9+6*(i+1)] for i in range(4)]
    assert all(z[-1]=='0' and int(z[:5],2)<30 for z in words)
    return r,*[int(z[:5],2) for z in words]

def fwd(tensors,s):
    assert 0<len(s)<=80 and set(s)<={'0','1'}
    x=np.zeros(160,np.float32)
    for i,ch in enumerate(s):x[2*i+int(ch)]=1.
    w1,b1,w2,b2=tensors
    h=np.tanh(w1@x+b1).astype(np.float32)
    logits=w2@h+b2
    return '01S'[int(np.argmax(logits))]

def generate(w,q):
    output=''
    for n in range(32):
        if len(q)+len(output)>80:return output,'overflow',n
        output+=fwd(w,q+output)
        if output[-1]=='S':return output,'stop',n+1
    return output,'cap',32

def main():
    lines=(P/'raw_cases.jsonl').read_bytes()
    results=json.loads((P/'RESULTS.json').read_text())
    assert hashlib.sha256(lines).hexdigest()==results['raw_sha256']
    records=[json.loads(z) for z in lines.decode().splitlines()]
    assert len(records)==640==results['raw_rows']
    models={(seed,arm):model(seed,arm) for seed in (101,202) for arm in ('control','conjunction')}
    counter=collections.defaultdict(lambda:[0,0,0])
    total_forwards=0
    for i,z in enumerate(records):
        seed,arm,tag=z['seed'],z['arm'],z['split']
        r,a,b,c,d=parse_q(z['Q'])
        assert (r,a,b,c,d)==(z['r'],z['a'],z['b'],z['c'],z['d']),(i,'bits')
        ans=f'{a:05b}0'+(f'{b:05b}0' if r==2 else '')+'S'
        assert z['expected']==ans,(i,'label')
        response,cause,n=generate(models[(seed,arm)],z['Q'])
        assert (response,cause,n)==(z['actual'],z['cause'],z['forward_calls']),(i,'forward_mismatch',response,z['actual'])
        counter[(seed,arm,tag)][0]+=1
        counter[(seed,arm,tag)][1]+=int(response==ans)
        counter[(seed,arm,tag)][2]+=n
        total_forwards+=n
    assert total_forwards==results['evaluation_forward_calls']
    for block in results['models']:
        for tag,m in block['metrics'].items():
            n,c,fw=counter[block['seed'],block['arm'],tag]
            assert (n,c)==(m['n'],m['exact']),(block['seed'],block['arm'],tag,'counts')
    print('INDEPENDENT NUMPY FULL REPLAY PASS',len(records),'/',len(records),'answers',total_forwards,'forward',results['evaluation_dense_MAC'],'dense MAC')
    print('STRICT SPLIT AND RAW 01 PARSE 640/640 PASS; all 4 F32 checkpoint SHA validated')
    print('PRIMARY',results['primary_gate'])
if __name__=='__main__':main()
