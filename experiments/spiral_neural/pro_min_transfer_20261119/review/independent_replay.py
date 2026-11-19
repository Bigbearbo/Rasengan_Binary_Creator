"""Check saved hard outputs and optimizer trajectories using a separate implementation, without importing the trainer."""
import argparse
import json
from pathlib import Path

import numpy as np

from audit_source import audit as audit_source

def word_bits(a,b):
    return np.column_stack([(v[:,None] // (2**np.arange(6,-1,-1)))%2 for v in (a,b)]).astype(float)

def close(v,w):
    d=float(np.max(np.abs(v-w)))
    assert np.allclose(v,w,rtol=1e-9,atol=1e-11),d
    return d

def state_update(p, m, v, t, g, matched=False):
    t += 1
    if matched:
        m = m + .1 * (g - m)
        v = v + .001 * (g**2 - v)
    else:
        m = .9*m + .1*g
        v = .999*v + .001*g*g
    delta = .02*(m/(1-.9**t)) / (np.sqrt(v/(1-.999**t))+1.e-8)
    return p-delta,m,v,t

def check_updates(root, arm, seed, states, a,b, matched=True):
    x = np.column_stack([word_bits(a,b),np.ones(len(a))])
    c = np.r_[2**np.arange(6,-1,-1),-2**np.arange(6,-1,-1),.5]/64
    g = np.array([1.,0.])
    orig=c.copy()
    m,v=np.zeros(15),np.zeros(15)
    gm,gv=np.zeros(2),np.zeros(2)
    ct=gt=0
    order = list(states['stages'])
    diffs=[]
    alternative={}
    def verify(stage):
        i=order.index(stage)
        if not matched:
            if stage.startswith("min_"):
                alternative[stage]=float(np.max(np.abs(c-states["comparator"][i])))
                if stage=="min_512":
                    aa,bb=np.repeat(np.arange(128),128),np.tile(np.arange(128),128)
                    select=word_bits(aa,bb)@c[:-1]+c[-1]>=0
                    alternative["final_ideal_max_wrong"]=int((np.where(select,aa,bb)!=np.maximum(aa,bb)).sum())
                    select_min=g[0]*(2*select-1)+g[1]>=0
                    alternative["final_ideal_min_wrong"]=int((np.where(select_min,aa,bb)!=np.minimum(aa,bb)).sum())
            return
        for k,val in [('comparator',c),('adapter',g),('c_m',m),('c_v',v),('ab_m',gm),('ab_v',gv),('c_step',ct),('ab_step',gt)]:
            try:
                diffs.append(close(states[k][i],val))
            except AssertionError as exc:
                raise AssertionError((arm,seed,stage,k)) from exc
    verify('min_000')
    steps=0
    with np.load(root/'results'/f'batches_{seed}.npz') as batches:
        for phase in ('min','max'):
            schedule = batches[phase+'_rows']
            if phase=='max':
                tmp=c
                c=orig
                verify('restore_000')
                c=tmp
                m,v=np.zeros(15),np.zeros(15)
                ct=0
            for t, ix in enumerate(schedule,1):
                assert len(ix)==64 and np.all(a[ix]!=b[ix])
                batch_words=word_bits(a[ix],b[ix]).astype(np.uint8)
                compare_score=(batch_words @ c[:-1]+c[-1]) if matched else x[ix] @ c
                active = phase=='min' and arm!='overwrite'
                labels=(a[ix]<b[ix]) if phase=='min' else (a[ix]>b[ix])
                if active:
                    symbol=np.where(compare_score >= 0, 1.,-1.)
                    features = np.column_stack([symbol,np.ones(64)])
                    if matched:
                        z=g[0]*symbol+g[1]
                        r=(np.exp(-np.logaddexp(0,-z))-labels)/64
                        derivative=g[0]*4/(1+np.abs(4*compare_score))**2
                        adapter_grad=np.array([r @ symbol,r.sum()])
                        rc=r*derivative
                        comparator_grad=np.r_[batch_words.T @ rc,rc.sum()]
                    else:
                        z=features @ g
                        residual=(1/(1+np.exp(-z)))-labels
                        comparator_grad=x[ix].T @ (residual*g[0]*4 / (1+4*np.abs(compare_score))**2) / 64
                        adapter_grad=features.T @ residual/64
                    g,gm,gv,gt=state_update(g,gm,gv,gt,adapter_grad,matched)
                else:
                    if matched:
                        r=(np.exp(-np.logaddexp(0,-compare_score))-labels)/64
                        comparator_grad=np.r_[batch_words.T @ r,r.sum()]
                    else:
                        residual=1/(1+np.exp(-compare_score))-labels
                        comparator_grad=x[ix].T @ residual/64
                if arm!='frozen':
                    c,m,v,ct=state_update(c,m,v,ct,comparator_grad,matched)
                if active or arm!='frozen':
                    steps+=1
                stage=f'{phase}_{t:03}'
                if stage in order:
                    verify(stage)
    return (steps,max(diffs)) if matched else alternative

def audit(root):
    source=audit_source(root)
    data=json.loads((root/'inherited'/'data.json').read_text())['panels']
    panels={name:tuple(np.array([row[k] for row in rows]) for k in ('a','b'))
            for name,rows in data.items()}
    panels['ideal']=(np.repeat(np.arange(128),128), np.tile(np.arange(128),128))
    truth={name:(a,b,word_bits(a,b)) for name,(a,b) in panels.items()}
    metrics=json.loads((root/'results'/'metrics.json').read_text())
    nst=rows=updates=0
    deltas=[]
    summary={}
    sensitivity={}
    for seed in [101,202,303]:
        for arm in ['frozen','joint','overwrite']:
            name=f'{arm}_{seed}'
            loc=root/'results'/name
            summary[name]={}
            with np.load(loc/'states.npz',allow_pickle=False) as states:
                steps,e=check_updates(root,arm,seed,states,*panels['train'])
                if arm=="joint":
                    sensitivity[name]=check_updates(root,arm,seed,states,*panels["train"],matched=False)
                updates+=steps
                deltas.append(e)
                stage_names=states['stages']
                assert len(stage_names)==16
                nst+=len(stage_names)
                for panel,(a,b,x) in truth.items():
                    with np.load(loc/(panel+'.npz'),allow_pickle=False) as pred:
                        assert np.array_equal(stage_names,pred['stages'])
                        saved=pred['predictions']
                    for i,(state,cp,adapter) in enumerate(zip(stage_names,states['comparator'],states['adapter'])):
                        old=x@cp[:-1] >= -cp[-1]
                        new=(old if arm=='overwrite' else adapter[0]*(old*2-1)+adapter[1]>=0)
                        answer_max=np.where(old,a,b)
                        answer_min=np.where(new,a,b)
                        assert np.array_equal(saved[i],np.stack([old,new,answer_max,answer_min])),(name,state,panel)
                        rows+=len(x)
                        old_errors=(answer_max!=np.maximum(a,b))
                        tie=(a==b)&(old!=saved[0,0])
                        new_errors=(answer_min!=np.minimum(a,b))
                        def values(mask):
                            return dict(n=int(mask.sum()),max_correct=int((mask&~old_errors).sum()),min_correct=int((mask&~new_errors).sum()),
                                        changed_old_answers=int((mask&old_errors).sum()),changed_old_tie_choices=int((mask&tie).sum()))
                        assert metrics[name][state][panel]==values(np.ones(len(a),dtype=bool))
                        if panel=='ideal':
                            assert metrics[name][state]['ideal_in_domain']==values(a+b<128)
                            if state in ('min_512','restore_000','max_128'):
                                summary[name][state]=dict(max_wrong=int(old_errors.sum()),min_wrong=int(new_errors.sum()))
    return dict(status='PASS',source=source,checkpoints=nst,case_checkpoint_rows=rows,
                hard_values_per_row=4,verified_optimizer_batch_steps=updates,
                max_abs_checkpoint_or_moment_difference=max(deltas),
                ideal_wrong_per_16384=summary,
                posthoc_alternate_numerical_order_joint=sensitivity)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('experiment',type=Path)
    print(json.dumps(audit(ap.parse_args().experiment),indent=2))
