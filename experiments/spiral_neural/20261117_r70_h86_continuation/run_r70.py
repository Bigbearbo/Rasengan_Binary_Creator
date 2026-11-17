#!/usr/bin/env python3
"""R70 frozen-budget continuation. Resumes R69 Adam + RNG exactly, no new task/architecture."""
import json, hashlib, sys, time, os
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import run_r69 as r69
FABLE=ROOT/'fable'
sys.path.insert(0,str(FABLE)); import hand
OUT=ROOT/'r70_results'; OUT.mkdir(exist_ok=True)
EXPECT={'hand.py':'166ef00fce69386f89a1f832785a77e2fb465b3831c5d78854ac85083deceed8','compiler.py':'bf6e9e84d6b2ddc2462b586fd25c5cb8a2f4fc913bc7803655ccf39591d085ab','filltrain.py':'a5e6c4eaf5ff4d1e8d8ad7bdf1da0ceb42c291629cddf79adc820a286bea9b1c','handfilled_H86_9families.npz':'97d671b42f735bea818878652a4d209e4dcfec3037049327dcb6014095e4e523'}
assert all(hashlib.sha256((FABLE/k).read_bytes()).hexdigest()==v for k,v in EXPECT.items())
TR,VA,TE=hand.sets(2603)
val_recs, val=r69.build_panel(hand,VA,9911,256)
orig_recs=[json.loads(x) for x in (ROOT/'results'/'validation_raw.jsonl').read_text().splitlines()]
assert orig_recs==val_recs,'source 4096 validation panel differs!'
orig=json.loads((ROOT/'results'/'results.json').read_text())
CHECKS=(4096,4608,5120,6144,8192)
outputs={'source_r69_results_sha256':hashlib.sha256((ROOT/'results'/'results.json').read_bytes()).hexdigest(),'source_r69_archive_sha256':'22179e2b944c616d3559195361901dc36c941b788b0340ab58ea9fcb0be94890','source_sha256':EXPECT,'seeds':{},'start':4096,'end':8192,'profile':'Fable151 candidate, nonnormative; left not taught','validation_rows':len(val_recs),'train_values':len(TR),'val_values':len(VA),'test_values':len(TE),'train_rows_added_per_seed':4096*64,'params':16639,'forward_dense_MAC':16512,'train_forward_dense_MAC_added_per_seed':4096*64*16512,'training_test_status':'test used only once final, already inspected in R69 history'}
for seed in (101,202,303):
    ck=np.load(ROOT/'results'/f'B_seed{seed}_step4096.npz',allow_pickle=False)
    meta=json.loads(str(ck['meta']))
    assert meta['step']==4096 and meta['seed']==seed
    p={k:ck['p_'+k].copy() for k in ('W1','b1','Wo','bo')}
    m={k:ck['m_'+k].copy() for k in p}
    v={k:ck['v_'+k].copy() for k in p}
    rng=np.random.default_rng();rng.bit_generator.state=meta['rng']
    entry={'seed':seed,'checkpoints':[]}
    digest=hashlib.sha256();started=time.perf_counter()
    for t in range(4096,8193):
        if t in CHECKS:
            ev=r69.eval_panel(p,val)
            original=orig['B'][str(seed)]['final_val']
            if t==4096:
                assert ev==original,('frozen baseline mismatch',seed,ev,original)
            gate=all(x['pct']>=95 for x in ev.values())
            if t>4096:
                r69.snapshot(OUT/f'B_seed{seed}_step{t}.npz',p,m,v,t,seed,rng,EXPECT)
            entry['checkpoints'].append({'update':t,'val':ev,'gate_9families_ge95':gate,'checkpoint':f'B_seed{seed}_step{t}.npz' if t>4096 else f'R69 B_seed{seed}_step4096.npz'})
        if t==8192:break
        xs=[];ys=[];ms=[]
        for fam,c in r69.MIX:
            x,y,mask=hand.sample(fam,TR,rng,c)
            if len(x)<c:x=np.repeat(x,c,axis=0);y=np.repeat(y,c,axis=0);mask=np.repeat(mask,c,axis=0)
            xs.append(x);ys.append(y);ms.append(mask)
        x=np.vstack(xs);yy=np.vstack(ys);mm=np.vstack(ms);assert x.shape==(64,151)
        digest.update(x.astype(np.uint8).tobytes());digest.update(yy.astype(np.uint8).tobytes());digest.update(mm.astype(np.uint8).tobytes())
        y=np.hstack((yy,np.ones((64,1))));mask=np.hstack((mm,np.ones((64,1))))
        h=np.tanh(x@p['W1']+p['b1']);z=h@p['Wo']+p['bo']
        w=np.zeros_like(mask);w[:,:40]=mask[:,:40]/mask[:,:40].sum();w[:,40]=.25/64
        dz=(r69.sig(z)-y)*w;dh=(dz@p['Wo'].T)*(1-h*h)
        grads={'W1':x.T@dh,'b1':dh.sum(0),'Wo':h.T@dz,'bo':dz.sum(0)}
        nm=np.sqrt(sum((ar*ar).sum() for ar in grads.values()));sc=min(1.,1/max(nm,1e-12))
        for k in grads:
            gr=grads[k]*sc;m[k]=.9*m[k]+.1*gr;v[k]=.999*v[k]+.001*(gr*gr)
            p[k]-=.003*(m[k]/(1-.9**(t+1)))/(np.sqrt(v[k]/(1-.999**(t+1)))+1e-8)
    entry['train_stream_sha256_added']=digest.hexdigest()
    entry['first_observed_gate']=next((q['update'] for q in entry['checkpoints'] if q['gate_9families_ge95']),None)
    entry['wall_seconds']=time.perf_counter()-started
    outputs['seeds'][str(seed)]=entry
    print('SEED',seed,[(q['update'],q['val']['COPY4']['correct'],q['val']['REVERSE3']['correct'],q['gate_9families_ge95']) for q in entry['checkpoints']],flush=True)
# Only now evaluate the already-inspected fixed test panel. No selection by test.
test_recs,test=r69.build_panel(hand,TE,9922,512)
assert test_recs==[json.loads(x) for x in (ROOT/'results'/'test_raw.jsonl').read_text().splitlines()]
for seed in (101,202,303):
    ck=np.load(OUT/f'B_seed{seed}_step8192.npz',allow_pickle=False)
    p={k:ck['p_'+k] for k in ('W1','b1','Wo','bo')}
    outputs['seeds'][str(seed)]['final_test']=r69.eval_panel(p,test,OUT/f'B_seed{seed}_step8192_failures.jsonl')
(OUT/'results.json').write_text(json.dumps(outputs,indent=2,ensure_ascii=False))
print('DONE',OUT/'results.json',flush=True)