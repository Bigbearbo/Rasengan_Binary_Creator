"""SLE-AE1-n5-v1 frozen students: heldout high word-pair × irrelevant-context transfer.
Usage: python experiment.py preflight | run. Torch for actual NN forwards; no training.
"""
import base64, collections, hashlib, json, sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
SEEDS=(101,202)
ARMS=('frozen_c1_control','balanced_c')
A=(0,1,2,3)
B=(18,19,22,23)
C=(0,2,3)
D=(0,8)
MAC=10432

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def word(v):
    assert type(v)==int and 0<=v<=29
    return format(v,'05b')+'0'
def qbits(a,b,c,d):
    q='01'+'010'+'010'+'0'+''.join(word(x) for x in (a,b,c,d))+'111100'
    assert len(q)==39 and all(x in '01' for x in q)
    return q
def expected(a,b):return word(a)+word(b)+'S'
def seen_r2(a,b):return (b-15+a)%2==1

def cases():
    return [{'seed':seed,'arm':arm,'a':a,'b':b,'c':c,'d':d,
             'split':('train-domain-probe' if a<2 else 'validation-probe' if a==2 else 'test-probe'),
             'pair_exposure':'r2_seen' if seen_r2(a,b) else 'r2_unseen',
             'Q':qbits(a,b,c,d),'expected':expected(a,b)}
            for seed in SEEDS for arm in ARMS for a in A for b in B for c in C for d in D]

def checkpoint_path(seed,arm):
    name='conjunction' if arm=='frozen_c1_control' else 'balanced_c'
    return P/'checkpoints'/f'weights_seed{seed}_{name}.json'
def unpack(seed,arm):
    j=json.loads(checkpoint_path(seed,arm).read_text()); state={};h=hashlib.sha256()
    for k,entry in j['tensors'].items():
        v=np.frombuffer(base64.b64decode(entry['little_endian_base64']),'<f4').copy().reshape(entry['shape'])
        h.update(k.encode());h.update(v.tobytes());state[k]=v
    assert j['weights_sha256']==h.hexdigest() and sum(v.size for v in state.values())==10499
    return state

def preflight():
    manifest=json.loads((P/'PREREGISTRATION.json').read_text())
    assert manifest['runner_sha256']==sha(P/'experiment.py')
    assert manifest['case_manifest_sha256']==sha(P/'cases_preregistered.jsonl')
    for seed in SEEDS:
        for arm in ARMS:
            assert sha(checkpoint_path(seed,arm))==manifest['checkpoints'][f'{seed}_{arm}']
            unpack(seed,arm)  # only tensor decoding/checks, no neural forward
    rows=cases()
    assert len(rows)==384
    assert len(set(r['Q'] for r in rows))==96
    assert sum(r['pair_exposure']=='r2_unseen' for r in rows)==192
    assert sum(r['pair_exposure']=='r2_seen' for r in rows)==192
    assert all(x['Q']==y['Q'] and x['expected']==y['expected'] for x,y in zip(rows,json.loads('['+','.join((P/'cases_preregistered.jsonl').read_text().splitlines())+']')))
    assert all(r['Q'].endswith('111100') and len(r['Q'])==39 for r in rows)
    assert qbits(0,18,2,0)!=qbits(0,18,3,0) and sum(x!=y for x,y in zip(qbits(0,18,2,0),qbits(0,18,3,0)))==1
    assert sum(x!=y for x,y in zip(qbits(0,18,2,0),qbits(0,18,2,8)))==1
    assert all(r['expected']==expected(r['a'],r['b']) for r in rows)
    assert len([r for r in rows if r['c']==0 and r['d']==0])==64
    assert len([r for r in rows if r['c'] in (2,3)])==256
    assert manifest['updates']==0 and manifest['params_per_student']==10499
    print('PREFLIGHT PASS: 384 planned rows/96 unique Q; 192 unseen-r2, 192 seen-r2; legal Q39, bit-pair controls, four checkpoints, 0 NN forwards')

def features(bits):
    z=np.zeros(160,np.float32)
    for i,b in enumerate(bits):z[2*i+int(b)]=1.
    return z

def evaluate():
    import torch
    from torch import nn
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    results=[]
    for seed in SEEDS:
        for arm in ARMS:
            weights=unpack(seed,arm)
            m=nn.Sequential(nn.Linear(160,64),nn.Tanh(),nn.Linear(64,3))
            m.load_state_dict({k:torch.from_numpy(v) for k,v in weights.items()});m.eval()
            with torch.no_grad():
                for row in cases():
                    if row['seed']!=seed or row['arm']!=arm:continue
                    q=row['Q'];out='';why='cap';n=0
                    for _ in range(32):
                        if len(q)+len(out)>80:why='overflow';break
                        logits=m(torch.from_numpy(features(q+out)).unsqueeze(0))[0]
                        char='01S'[int(torch.argmax(logits).item())];out+=char;n+=1
                        if char=='S':why='stop';break
                    results.append({**row,'actual':out,'cause':why,'forward_calls':n,
                                    'exact':out==row['expected'],'proper_stop':why=='stop' and len(out)==13})
    return results

def summarize(rows):
    data={(r['seed'],r['arm'],r['a'],r['b'],r['c'],r['d']):r for r in rows}
    groups={}
    for seed in SEEDS:
        for arm in ARMS:
            for pair in ('r2_seen','r2_unseen'):
                rr=[r for r in rows if r['seed']==seed and r['arm']==arm and r['pair_exposure']==pair]
                g={'total':len(rr),'exact':sum(r['exact'] for r in rr),'proper_stop':sum(r['proper_stop'] for r in rr)}
                for c in C:
                    for d in D:
                        rrs=[r for r in rr if r['c']==c and r['d']==d]
                        g[f'c{c}_d{d}']={'exact':sum(r['exact'] for r in rrs),'n':len(rrs)}
                g['c2_c3_equal'] = sum(data[seed,arm,a,b,2,d]['actual']==data[seed,arm,a,b,3,d]['actual'] for a in A for b in B if seen_r2(a,b)==(pair=='r2_seen') for d in D)
                g['d0_d8_equal'] = sum(data[seed,arm,a,b,c,0]['actual']==data[seed,arm,a,b,c,8]['actual'] for a in A for b in B if seen_r2(a,b)==(pair=='r2_seen') for c in C)
                g['c2_c3_pairs']=16;g['d0_d8_pairs']=24
                groups[f'{arm}_seed{seed}_{pair}']=g
    # Two balanced-c seeds: heldout r2 combinations, c2 & c3, both d values 24/32 correct;
    # same d0/d8 output 24/24 for unseen pair (across all 3 c conditions), no posthoc relaxation.
    primary=all(groups[f'balanced_c_seed{seed}_r2_unseen']['exact']>=40
      and (groups[f'balanced_c_seed{seed}_r2_unseen']['c2_d0']['exact']+
           groups[f'balanced_c_seed{seed}_r2_unseen']['c3_d0']['exact']+
           groups[f'balanced_c_seed{seed}_r2_unseen']['c2_d8']['exact']+
           groups[f'balanced_c_seed{seed}_r2_unseen']['c3_d8']['exact'])>=24
      and groups[f'balanced_c_seed{seed}_r2_unseen']['d0_d8_equal']==24 for seed in SEEDS)
    # Note overall exact 40/48 is stricter than 24/32; both frozen a priori.
    return primary,groups

def run():
    preflight()
    rows=evaluate()
    result,groups=summarize(rows)
    raw=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows).encode()
    (P/'raw_cases.jsonl').write_bytes(raw)
    calls=sum(r['forward_calls'] for r in rows)
    obj={'work_id':'SLE-AE1-NEW-PAIR-CONTEXT-20261114','primary_pass':result,
         'source_pr48_head':'acb2947e558addfac1912870d61be439df4d9b7f',
         'optimizer_updates':0,'rows':len(rows),'unique_Q':96,'params_per_student':10499,
         'inference_forward_calls':calls,'dense_MAC_per_forward':MAC,'inference_dense_MAC':calls*MAC,
         'raw_sha256':hashlib.sha256(raw).hexdigest(),'groups':groups}
    (P/'RESULTS.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    print('RUN rows',len(rows),'forwards',calls,'dense MAC',calls*MAC,'PRIMARY',result)
    for k,v in groups.items():print(k,json.dumps(v,separators=(',',':')))

if __name__=='__main__':
    if sys.argv[1:]==['preflight']:preflight()
    elif sys.argv[1:]==['run']:run()
    else:raise SystemExit('Usage: python experiment.py preflight|run')
