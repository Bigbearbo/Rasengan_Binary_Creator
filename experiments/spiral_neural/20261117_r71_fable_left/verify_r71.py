#!/usr/bin/env python3
"""R71 independent raw-bit / checkpoint verification, no new students/selection.
Recomputes all 63 validation snapshots with independent forward/scorer and
first 128 optimizer steps with separate gradient/Adam math.
Requires original SHA-locked Fable source, R70 extracted corpus, and R71 output.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--fable-dir',required=True);p.add_argument('--r70-dir',required=True);p.add_argument('--out',required=True);a=p.parse_args()
fable=Path(a.fable_dir);r70=Path(a.r70_dir);out=Path(a.out)
sys.path.insert(0,str(fable));import hand,compiler
sys.path.insert(0,str(Path(__file__).resolve().parent));import run_r71 as r71
res=json.loads((out/'RESULTS.json').read_text()); assert res['all_completed']

def raw_rows(name):return [json.loads(z) for z in (out/name).read_text().splitlines()]
val=raw_rows('val_paired_raw.jsonl');test=raw_rows('test_paired_raw.jsonl')
assert r71.hfile(out/'val_paired_raw.jsonl')==res['val_panel_sha256']
assert r71.hfile(out/'test_paired_raw.jsonl')==res['test_panel_sha256']
assert len(val)==len(test)==288
assert len(set(tuple(row['payload']) for row in val if row['op']==1))==96
assert len(set(tuple(row['payload']) for row in test if row['op']==1))==96

def evaluate_raw(p,rows):
    X=np.array([[int(z) for z in row['raw_input_151']] for row in rows],float)
    Y=np.array([[int(z) for z in row['gold_40']] for row in rows],int)
    M=np.array([[int(z) for z in row['mask_40']] for row in rows],bool)
    logits=np.tanh(X@p['W1']+p['b1'])@p['Wo']+p['bo']; bits=logits>0
    exact=np.all((bits[:,:40]==Y)|~M,axis=1)&bits[:,40]
    groups={}
    for i,row in enumerate(rows):
        key=f"{row['op']}/{row['n']}";v=groups.setdefault(key,[0,0]);v[0]+=int(exact[i]);v[1]+=1
    return groups

def eval_legacy(p):
    rows=[json.loads(z) for z in (r70/'results/validation_raw.jsonl').read_text().splitlines()]
    gs={}
    X=np.array([[int(t) for t in x['raw_input_151']] for x in rows],float)
    Y=np.array([[int(t) for t in x['gold_answer_40']] for x in rows],int)
    M=np.array([[int(t) for t in x['answer_mask_40']] for x in rows],bool)
    z=np.tanh(X@p['W1']+p['b1'])@p['Wo']+p['bo'];bits=z>0
    full=np.all((bits[:,:40]==Y)|~M,axis=1)&bits[:,40]
    for i,row in enumerate(rows):
        fam=row['family'];k=gs.setdefault(fam,[0,0]);k[0]+=int(full[i]);k[1]+=1
    return gs

def load(ck):
    d=np.load(out/'checkpoints'/ck,allow_pickle=False)
    return {k:d['p_'+k].copy() for k in r71.FIELDS}, {k:d['m_'+k].copy() for k in r71.FIELDS}, {k:d['v_'+k].copy() for k in r71.FIELDS},json.loads(str(d['meta']))

def grad_alt(p,x,y,mask):
    H=np.tanh(x@p['W1']+p['b1']); Z=H@p['Wo']+p['bo'];out=np.zeros((64,41))
    out[:,:40]=y;out[:,40]=1
    ez=np.exp(-np.abs(Z));sig=np.where(Z>=0,1/(1+ez),ez/(1+ez))
    weights=np.concatenate([mask/mask.sum(),np.ones((64,1))*(.25/64)],axis=1)
    D=(sig-out)*weights
    d_hidden=(D@p['Wo'].T)*(1-H**2)
    return {'Wo':H.T@D,'bo':D.sum(0),'W1':x.T@d_hidden,'b1':d_hidden.sum(0)}

def step_alt(p,m,v,g,t):
    n=np.sqrt(sum(np.sum(grad**2) for grad in g.values())); scale=min(1,1/max(n,1e-12))
    for key in r71.FIELDS:
        q=g[key]*scale;m[key]=.9*m[key]+.1*q;v[key]=.999*v[key]+.001*q*q
        p[key]-=.003*m[key]/(1-.9**t)/(np.sqrt(v[key]/(1-.999**t))+1e-8)

assert all(hashlib.sha256((fable/k).read_bytes()).hexdigest()==sha for k,sha in r71.PROVENANCE.items())
TR,VA,TE=hand.sets(2603)
assert not(set(TR)&set(VA) or set(TR)&set(TE) or set(VA)&set(TE))
checked=0;max_replay=0.0;firsthashes={}
for seed in r71.SEEDS:
    trainhashes=set()
    for group in ('A','B','C'):
        entry=res['groups'][f'{group}{seed}'];trainhashes.add(entry['train_stream_sha256'])
        for ck in entry['checkpoint_metrics']:
            q,_,_,meta=load(ck['checkpoint'])
            assert meta['group']==group and meta['seed']==seed and meta['step']==ck['step']
            s=evaluate_raw(q,val)
            assert all(q['correct']==s[k][0] and q['total']==s[k][1] for k,q in ck['left_val']['per_operator_n'].items()),(seed,group,ck['step'],'paired val')
            o=eval_legacy(q)
            assert all(q['correct']==o[k][0] and q['total']==o[k][1] for k,q in ck['old_val'].items()),(seed,group,ck['step'],'legacy val')
            checked+=1
        final,_,_,_=load(f'{group}_seed{seed}_step4096.npz')
        fixed=evaluate_raw(final,test)
        assert all(q['correct']==fixed[k][0] and q['total']==fixed[k][1] for k,q in entry['final_test']['per_operator_n'].items())
        # Independently re-compute training gradient/Adam from frozen step-0 to step-128.
        q,m,v,meta=load(f'{group}_seed{seed}_step0.npz')
        gen=np.random.default_rng();gen.bit_generator.state=meta['rng']
        for t in range(1,129):
            x,y,mask,_=r71.new_batch(hand,compiler,TR,gen)
            g=grad_alt(q,x,y,mask)
            step_alt(q,m,v,g,t)
        expected,em,ev,meta=load(f'{group}_seed{seed}_step128.npz')
        mx=max(np.max(np.abs(q[k]-expected[k])) for k in r71.FIELDS)
        mx=max(mx,max(np.max(np.abs(m[k]-em[k])) for k in r71.FIELDS))
        mx=max(mx,max(np.max(np.abs(v[k]-ev[k])) for k in r71.FIELDS))
        max_replay=max(max_replay,float(mx))
        assert mx<1e-10,(seed,group,mx)
        d=entry['new_grad_and_step_diagnostics']
        if group!='C':
            assert d[0]['gradient_norm_new_W1']==d[0]['gradient_norm_new_b1']==0
            assert d[0]['gradient_norm_new_Wo']>0 and d[1]['gradient_norm_new_W1']>0 and d[1]['gradient_norm_new_b1']>0
            assert d[1]['delta_norm_new_W1']>0 and d[1]['delta_norm_new_b1']>0
    assert len(trainhashes)==1,('unpaired training stream',seed)
print(json.dumps({'verification':'PASS','checkpoints_validation_replayed':checked,'test_models_replayed':9,
 'first_128_updates_independent_replays':9,'max_abs_state_difference_first128':max_replay,
 'source_sha_verified':4,'train_stream_paired_per_seed':True,'profiles':'Fable151 candidate, not normative SLE-AE1'},indent=2))
(out/'INDEPENDENT_VERIFY.json').write_text(json.dumps({'verification':'PASS','checkpoints_validation_replayed':checked,'test_models_replayed':9,'first_128_updates_independent_replays':9,'max_abs_state_difference_first128':max_replay,'source_sha_verified':4,'train_stream_paired_per_seed':True},indent=2))
