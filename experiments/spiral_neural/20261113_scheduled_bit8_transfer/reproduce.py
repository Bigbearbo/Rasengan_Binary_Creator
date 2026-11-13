"""Independent NumPy replay of PR40 checkpoint and bit8 transfer probe.

python reproduce.py /path/to/sle_ae1_high_r_mixed_20261113.zip outdir
No training, no model-generated answers supplied by an oracle.
Preregistered at ead3e96c7f982061bb5fdd41b1961a7d43f1389d.
"""
import base64, hashlib, json, pathlib, sys, zipfile
from collections import defaultdict
import numpy as np

ROOT='experiments/spiral_neural/20261113_scheduled_high_r_mixed/'
SHA={
 'PREREGISTRATION.json':'e5693803ab1ef45b95d7a39971430ae12140da0e3ae53674c5400eb803b15703',
 'run.py':'79dc4dca3c8e03f3889258a33532b639f5db11c0d3a6cf12dcba79443c826193',
 'raw_cases.jsonl':'6a7ed2df3751a8130e337ac41541b1e4169accdfa16cd2141b0614d045fe354f',
 'weights_seed101_mixed.json':'ac022fdcac1c6e9de5b78e1667519a6443e05c7f8e48fe4b84514432a1576009',
 'weights_seed202_mixed.json':'048c719e8c2afbbcac579b80a2f820989eb68ba030a1f2ce7c2747474897a157'}
ARCHIVE_SHA='1562ebeb5069e217d4d1396c14b9ea9e3fe969db0ce93237e9fcd635fc6fd94e'

def digest(b):return hashlib.sha256(b).hexdigest()
def word(i):return f'{i:05b}0'
def qbits(r,a,b,c=0,d=0):return '01010'+f'{r:03b}'+'0'+''.join(word(v) for v in (a,b,c,d))+'111100'
def answer(r,a,b):return word(a)+(word(b) if r==2 else '')+'S'

def load(data):
    obj=json.loads(data);w={};h=hashlib.sha256()
    for k,shape in [('0.weight',(64,160)),('0.bias',(64,)),('2.weight',(3,64)),('2.bias',(3,))]:
        raw=base64.b64decode(obj['tensors'][k]['little_endian_base64'])
        w[k]=np.frombuffer(raw,dtype='<f4').reshape(shape).copy()
        assert np.isfinite(w[k]).all();h.update(k.encode()+raw)
    assert h.hexdigest()==obj['weights_sha256'];return w

def generate(w,q):
    out=''
    for n in range(32):
        if len(q)+len(out)>80:return out,'overflow',n
        x=np.zeros(160,np.float32)
        for i,ch in enumerate(q+out):x[2*i+int(ch)]=1
        logits=w['2.weight']@np.tanh(w['0.weight']@x+w['0.bias'])+w['2.bias']
        out+='01S'[int(np.argmax(logits))]
        if out.endswith('S'):return out,'stop',n+1
    return out,'cap',32

def main(archive,outdir):
    assert digest(archive.read_bytes())==ARCHIVE_SHA
    with zipfile.ZipFile(archive) as z:raw={n:z.read(ROOT+n) for n in SHA}
    for n,h in SHA.items():assert digest(raw[n])==h,n
    weights={seed:load(raw[f'weights_seed{seed}_mixed.json']) for seed in (101,202)}
    old=[json.loads(s) for s in raw['raw_cases.jsonl'].splitlines()]
    assert len(old)==288
    for z in old:
        assert generate(weights[z['seed']],z['Q'])==(z['actual'],z['cause'],z['forward_calls'])
    rows=[];stats=defaultdict(lambda:{'n':0,'exact':0,'stop':0,'forward':0})
    for seed in (101,202):
        for a in range(6):
            for b in range(16,22):
                for r in (1,2):
                    outputs=[]
                    for domain,v in [('seen',b),('new',b+8)]:
                        q=qbits(r,a,v)
                        assert len(q)==39 and set(q)==set('01')
                        got,reason,n=generate(weights[seed],q);want=answer(r,a,v)
                        z=dict(seed=seed,a=a,b=v,r=r,domain=domain,Q=q,expected=want,actual=got,cause=reason,
                               forward_calls=n,exact=got==want,stop=got.endswith('S') and len(got)==len(want))
                        rows.append(z);outputs.append(z)
                        key=(seed,'heldout' if a>=4 else 'exposed',r,domain)
                        m=stats[key];m['n']+=1;m['exact']+=z['exact'];m['stop']+=z['stop'];m['forward']+=n
                    x,y=outputs
                    assert [i for i,(u,v) in enumerate(zip(x['Q'],y['Q'])) if u!=v]==[16]
                    key=(seed,'heldout' if a>=4 else 'exposed',r,'pairs')
                    m=stats[key];m['n']+=1;m['invariant']=m.get('invariant',0)+(x['actual']==y['actual'])
                    m['exact_bit8_flip']=m.get('exact_bit8_flip',0)+(r==2 and len(x['actual'])==len(y['actual'])==13 and
                         [i for i,(u,v) in enumerate(zip(x['actual'],y['actual'])) if u!=v]==[7])
    assert len(rows)==288
    outdir.mkdir(parents=True,exist_ok=True)
    data=''.join(json.dumps(x,separators=(',',':'))+'\n' for x in rows)
    (outdir/'raw_cases.jsonl').write_text(data)
    report={'old_replayed':288,'new_rows':len(rows),'raw_sha256':digest(data.encode()),
            'metrics':{'/'.join(map(str,k)):v for k,v in sorted(stats.items())},'new_training_updates':0}
    (outdir/'replay_results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('OLD 288/288 replay, NEW',len(rows),'rows, RAW SHA',report['raw_sha256'])
    for seed in (101,202):
        for r in (1,2):
            for domain in ('seen','new'):
                k=(seed,'heldout',r,domain)
                print(seed,'heldout',r,domain,stats[k]['exact'],'/',stats[k]['n'])

if __name__=='__main__':
    main(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]))
