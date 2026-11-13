"""Preregistered native 01 AE1 matched-payload r-assignment experiment.
Identical input payload multiset, r1/r2 counts and target budgets; changes
which payload class (new-high b vs ordinary-low b) gets r2 target exposure.
Parent PR36 code must have immutable SHA; no large-model solver is used.
"""
import base64, copy, hashlib, json, sys, time
from pathlib import Path
import numpy as np
import torch
from torch import nn

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'20261113_scheduled_role_swap_pilot'
sys.path.insert(0,str(PARENT))
import run as parent

PROTOCOL=json.loads((HERE/'PREREGISTRATION.json').read_text())
SEEDS=(101,202)
ARMS=('HIGH_OUTPUT','HIGH_INPUT_ONLY')
EPOCHS=200
BATCH=64
TARGETS=1200
MAC=10432
PARENT_SHA='05e2d730eecefcb50fa92392697556ffde313f5ecb59c2f4e583aad52e321303'

def high_items(r):
    return [(r,s,v,0,0) for v in range(15,24) for s in range(4)]

def low_items(r):
    pairs=[(a,b) for a in range(6) for b in range(6) if parent.base_split(a,b)=='train']
    assert len(pairs)==24
    return [(r,*pairs[i%24],i//24,0) for i in range(36)]

def base_items(split):
    return [(r,a,b,0,0) for r,a,b in parent.base_rows(split)]

def rows(arm):
    assert arm in ARMS
    return base_items('train')+(high_items(2) if arm=='HIGH_OUTPUT' else high_items(1))+(low_items(1) if arm=='HIGH_OUTPUT' else low_items(2))

def teacher(items):
    X=[]; Y=[]
    for r,a,b,c,d in items:
        q=parent.qbits(r,a,b,c,d)
        answer=parent.answer(r,a,b)
        for j,t in enumerate(answer):
            X.append(parent.xvec(q+answer[:j]));Y.append('01S'.index(t))
    return torch.from_numpy(np.stack(X)),torch.tensor(Y,dtype=torch.int64)

def all_eval_items():
    return {'base_train':base_items('train'), 'base_val':base_items('val'), 'base_test':base_items('test'),
            'high_r1_train_values':high_items(1),'high_r2_train_values':high_items(2),
            'high_r2_val_low4':[(2,4,v,0,0) for v in range(15,24)],
            'high_r2_test_low5':[(2,5,v,0,0) for v in range(15,24)],
            'low_block_r1':low_items(1),'low_block_r2':low_items(2)}

def selftest():
    assert hashlib.sha256((PARENT/'run.py').read_bytes()).hexdigest()==PARENT_SHA
    assert len(base_items('train'))==48 and len(base_items('val'))==len(base_items('test'))==12
    assert len(high_items(1))==len(high_items(2))==len(low_items(1))==len(low_items(2))==36
    assert len(set((a,b,c,d) for _,a,b,c,d in high_items(1)))==36
    assert len(set((a,b,c,d) for _,a,b,c,d in low_items(1)))==36
    assert set((a,b,c,d) for _,a,b,c,d in high_items(1)).isdisjoint(
           (a,b,c,d) for _,a,b,c,d in low_items(1))
    for arm in ARMS:
        batch=rows(arm)
        assert len(batch)==120
        assert sum(r==1 for r,a,b,c,d in batch)==60 and sum(r==2 for r,a,b,c,d in batch)==60
        X,Y=teacher(batch)
        assert X.shape==(TARGETS,160) and Y.shape==(TARGETS,)
    p1=sorted((a,b,c,d) for _,a,b,c,d in rows(ARMS[0]))
    p2=sorted((a,b,c,d) for _,a,b,c,d in rows(ARMS[1]))
    assert p1==p2, 'same data payload multiset required'
    assert len(high_items(1))==36 and all(b>=15 and a<=3 for _,a,b,c,d in high_items(1))
    assert all(parent.base_split(a,b)=='train' for _,a,b,c,d in low_items(1))
    assert all((r,a,b,c,d) not in rows('HIGH_OUTPUT') and (r,a,b,c,d) not in rows('HIGH_INPUT_ONLY')
               for items in [all_eval_items()['high_r2_val_low4'],all_eval_items()['high_r2_test_low5']]
               for r,a,b,c,d in items)
    for items in [rows(x) for x in ARMS]+list(all_eval_items().values()):
        for r,a,b,c,d in items:
            Q=parent.qbits(r,a,b,c,d); A=parent.answer(r,a,b)
            assert len(Q)==39 and set(Q)=={'0','1'} and Q.endswith('111100')
            assert len(A)==(7 if r==1 else 13) and A.endswith('S')
            assert 0<=min(a,b,c,d)<=max(a,b,c,d)<=29
    assert parent.qbits(2,0,15)=='010100100000000011110000000000000111100'
    assert parent.answer(2,0,15)=='000000011110S'
    assert sum(p.numel() for p in parent.network(101).parameters())==10499
    assert PROTOCOL['epochs']==EPOCHS and PROTOCOL['target_per_epoch']==TARGETS
    assert PROTOCOL['source_sha256']==PARENT_SHA
    print('GATE PASS source_sha, Q39, input payload multiset, r1/r2 counts, 24/6/6 base, new high val/test, 1200 targets, 10499 params', flush=True)

@torch.no_grad()
def evaluate(m,seed,arm):
    all_rec=[]; M={}; nf=0
    for split,items in all_eval_items().items():
        stats={'n':len(items),'exact':0,'first_word':0,'second_word':0,'stop_position':0,'bad_cap':0,'forward_calls':0}
        for r,a,b,c,d in items:
            Q=parent.qbits(r,a,b,c,d);exp=parent.answer(r,a,b)
            got,reason,calls=parent.free(m,Q)
            rec={'seed':seed,'arm':arm,'split':split,'r':r,'a':a,'b':b,'c':c,'d':d,
                 'Q':Q,'expected':exp,'actual':got,'cause':reason,'forward_calls':calls}
            all_rec.append(rec)
            stats['exact']+=int(got==exp)
            stats['first_word']+=int(got[:6]==parent.word(a))
            stats['second_word']+=int(r==2 and got[6:12]==parent.word(b))
            stats['stop_position']+=int(got.endswith('S') and len(got)==len(exp))
            stats['bad_cap']+=int(reason!='stop')
            stats['forward_calls']+=calls;nf+=calls
        M[split]=stats
    return all_rec,M,nf

def run():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    selftest()
    results={'work_id':PROTOCOL['work_id'],'source_sha256':PARENT_SHA,
             'prereg_sha256':hashlib.sha256((HERE/'PREREGISTRATION.json').read_bytes()).hexdigest(),
             'torch':torch.__version__,'numpy':np.__version__,
             'seeds':list(SEEDS),'arms':list(ARMS),'epochs':EPOCHS,'batch':BATCH,'parameters':10499,
             'targets_per_epoch':TARGETS,'models':[],'total_updates':0,'total_train_targets':0,'eval_forward':0}
    records=[];begin=time.perf_counter()
    for seed in SEEDS:
        initial=parent.network(seed)
        initsha=parent.weights_sha(initial)
        schedule=[np.random.default_rng(seed+97000+epoch).permutation(TARGETS) for epoch in range(EPOCHS)]
        for arm in ARMS:
            model=copy.deepcopy(initial)
            assert parent.weights_sha(model)==initsha
            X,Y=teacher(rows(arm)); optimizer=torch.optim.Adam(model.parameters(),lr=0.003)
            updates=0
            for epoch in range(EPOCHS):
                for start in range(0,TARGETS,BATCH):
                    ii=schedule[epoch][start:start+BATCH]
                    Z=model(X[ii]);loss=nn.functional.cross_entropy(Z,Y[ii]); optimizer.zero_grad();loss.backward()
                    nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step();updates+=1
            assert updates==3800
            cases,metrics,nf=evaluate(model,seed,arm)
            records.extend(cases)
            filename=f'weights_seed{seed}_{arm.lower()}.json'
            ckp=parent.checkpoint(model,seed,arm)
            (HERE/filename).write_text(json.dumps(ckp,separators=(',',':'))+'\n')
            results['models'].append({'seed':seed,'arm':arm,'init_sha256':initsha,
               'weights_sha256':parent.weights_sha(model),'checkpoint':filename,'updates':updates,
               'metrics':metrics})
            results['total_updates']+=updates
            results['total_train_targets']+=TARGETS*EPOCHS
            results['eval_forward']+=nf
            print('MODEL',seed,arm,'high-exposed',metrics['high_r2_train_values']['exact'],'/36',
                  'val',metrics['high_r2_val_low4']['exact'],'/9','test',metrics['high_r2_test_low5']['exact'],'/9',
                  'base',metrics['base_train']['exact'],'/48',flush=True)
    payload=''.join(json.dumps(x,separators=(',',':'))+'\n' for x in records).encode()
    (HERE/'raw_cases.jsonl').write_bytes(payload)
    results['raw_sha256']=hashlib.sha256(payload).hexdigest()
    results['raw_count']=len(records)
    results['training_forward_dense_MAC']=results['total_train_targets']*MAC
    results['eval_forward_dense_MAC']=results['eval_forward']*MAC
    results['backward_MAC_excluded']=True
    results['seconds']=time.perf_counter()-begin
    (HERE/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('COMPLETE',results['raw_count'],'raw',results['total_updates'],'optimizer updates',results['eval_forward'],'eval forward',round(results['seconds'],2),'secs',flush=True)

if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='selftest':selftest()
    elif len(sys.argv)==2 and sys.argv[1]=='train':run()
    else:raise SystemExit('usage: python run.py {selftest|train}')
