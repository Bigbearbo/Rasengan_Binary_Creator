"""Independent pure NumPy replay: no import of Torch or training runner."""
import base64,collections,hashlib,json,sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent

def weights(seed,arm):
    file=(P/'frozen_inputs'/f'weights_seed{seed}_conjunction.json' if arm=='frozen_c1_control'
          else P/f'weights_seed{seed}_balanced_c.json')
    obj=json.loads(file.read_text())
    t={k:np.frombuffer(base64.b64decode(v['little_endian_base64']),'<f4').copy().reshape(v['shape'])
       for k,v in obj['tensors'].items()}
    h=hashlib.sha256()
    for k,v in t.items():h.update(k.encode());h.update(v.tobytes())
    assert h.hexdigest()==obj['weights_sha256']
    return t['0.weight'],t['0.bias'],t['2.weight'],t['2.bias']

def parse_q(q):
    assert isinstance(q,str) and len(q)==39 and q.startswith('01010') and q.endswith('111100') and set(q)<={'0','1'}
    assert q[8]=='0'
    r=int(q[5:8],2);assert r in (1,2)
    w=[q[9+6*i:15+6*i] for i in range(4)]
    assert all(z[-1]=='0' and int(z[:5],2)<=29 for z in w)
    return (r,)+tuple(int(z[:5],2) for z in w)

def one_forward(model,s):
    assert 0<len(s)<=80 and set(s)<={'0','1'}
    x=np.zeros(160,np.float32)
    for i,ch in enumerate(s):x[2*i+int(ch)]=np.float32(1)
    w1,b1,w2,b2=model
    h=np.tanh(w1@x+b1).astype(np.float32)
    return '01S'[int(np.argmax(w2@h+b2))]

def free(model,q):
    out=''
    for t in range(32):
        if len(q)+len(out)>80:return out,'overflow',t
        out+=one_forward(model,q+out)
        if out.endswith('S'):return out,'stop',t+1
    return out,'cap',32

def main():
    result=json.loads((P/'RESULTS.json').read_text());raw=(P/'raw_cases.jsonl').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==result['raw_sha256']
    rows=[json.loads(x) for x in raw.decode().splitlines()]
    assert len(rows)==result['raw_rows']==752
    models={(seed,arm):weights(seed,arm) for seed in (101,202) for arm in ('balanced_c','frozen_c1_control')}
    counts=collections.defaultdict(lambda:[0,0,0,0,0]); total=0
    for i,z in enumerate(rows):
        seed,arm,tag=z['seed'],z['arm'],z['split']
        r,a,b,c,d=parse_q(z['Q']);assert (r,a,b,c,d)==tuple(z[k] for k in ('r','a','b','c','d'))
        expected=f'{a:05b}0'+(f'{b:05b}0' if r==2 else '')+'S'
        assert z['expected']==expected,(i,'label')
        actual,cause,steps=free(models[seed,arm],z['Q'])
        assert (actual,cause,steps)==(z['actual'],z['cause'],z['forward_calls']),(i,'mismatch',actual,z['actual'])
        n=counts[seed,arm,tag];n[0]+=1;n[1]+=int(actual==expected)
        n[2]+=int(actual.endswith('S') and len(actual)==len(expected))
        n[3]+=int(actual[:6]==f'{a:05b}0')
        n[4]+=int(r==2 and actual[6:12]==f'{b:05b}0')
        total+=steps
    assert total==result['evaluation_forward_calls']
    for z in result['all_models']:
        for tag,s in z['metrics'].items():
            n=counts[z['seed'],z['arm'],tag]
            assert tuple(n)==(s['n'],s['exact'],s['stop_position'],s['first_word'],s['second_word']),(z['seed'],z['arm'],tag,n)
    for seed in (101,202):
        c=next(x for x in result['all_models'] if x['seed']==seed and x['arm']=='frozen_c1_control')['metrics']
        b=next(x for x in result['all_models'] if x['seed']==seed and x['arm']=='balanced_c')['metrics']
        sc=lambda m,k:m[f'heldout_b26_27_c{k}_val']['exact']+m[f'heldout_b26_27_c{k}_test']['exact']
        o=(sc(c,0),sc(c,1),sc(b,0),sc(b,1))
        recorded=next(x for x in result['primary_gate']['seed_results'] if x['seed']==seed)
        assert o==(recorded['frozen_c0'],recorded['frozen_c1'],recorded['balanced_c0'],recorded['balanced_c1'])
    print('PURE NUMPY INDEPENDENT REPLAY PASS',len(rows),'/',len(rows),'generated Q/answers; forward decisions',total,
          'dense MAC',total*10432)
    print('Native 01 parse, expected-answer derivation, metrics, checkpoint state hash and raw SHA all PASS')
    print('PRIMARY',result['primary_gate'])
if __name__=='__main__':main()
