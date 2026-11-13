"""SLE AE1 high-value r1/r2 mixed-teaching experiment, fixed prior to training.
Compare to historical matched payload arms in PR39. Native raw 01 input only.
"""
import base64, copy, hashlib, json, sys, time, importlib.util
from pathlib import Path
import numpy as np
import torch
from torch import nn

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE.parent/'20261113_scheduled_input_target_exposure'
src=HERE.parent/'20261113_scheduled_role_swap_pilot'/'run.py'
spec=importlib.util.spec_from_file_location('run',src)
parent=importlib.util.module_from_spec(spec)
sys.modules['run']=parent
spec.loader.exec_module(parent)
spec2=importlib.util.spec_from_file_location('ae1_previous',PREVIOUS/'run.py')
previous=importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(previous)
p=HERE.parent
SPEC=json.loads((HERE/'PREREGISTRATION.json').read_text())
SEEDS=(101,202)
EPOCHS=200
BATCH=64
TARGETS=1200
MAC=10432

def train_rows():
    base=previous.base_items('train')
    hi=[(1 if (v-15+s)%2==0 else 2,s,v,0,0) for v in range(15,24) for s in range(4)]
    low=[(1 if i%2 else 2,a,b,c,d) for i,(_,a,b,c,d) in enumerate(previous.low_items(1))]
    return base+hi+low

def eval_sets():
    high=lambda r,s:[(r,s,v,0,0) for v in range(15,24)]
    return {'base_train':previous.base_items('train'),
            'base_val':previous.base_items('val'),
            'base_test':previous.base_items('test'),
            'high_train_r1':[z for z in train_rows()[48:84] if z[0]==1],
            'high_train_r2':[z for z in train_rows()[48:84] if z[0]==2],
            'high_val_r1':high(1,4),'high_val_r2':high(2,4),
            'high_test_r1':high(1,5),'high_test_r2':high(2,5)}

def gate():
    assert hashlib.sha256((p/'20261113_scheduled_role_swap_pilot'/'run.py').read_bytes()).hexdigest()==SPEC['source_parent_sha256']
    assert hashlib.sha256((PREVIOUS/'run.py').read_bytes()).hexdigest()==SPEC['source_previous_sha256']
    assert len(train_rows())==120 and sum(z[0]==1 for z in train_rows())==60 and sum(z[0]==2 for z in train_rows())==60
    assert sorted(z[1:] for z in train_rows())==sorted(z[1:] for z in previous.rows('HIGH_OUTPUT'))
    assert len(train_rows()[48:84])==36
    assert len(eval_sets()['high_train_r1'])==len(eval_sets()['high_train_r2'])==18
    for v in range(15,24):
        assert sorted(r for r,a,b,c,d in train_rows()[48:84] if b==v)==[1,1,2,2]
    X,Y=previous.teacher(train_rows())
    assert X.shape==(1200,160) and len(Y)==1200
    assert p.joinpath('20261113_scheduled_role_swap_pilot/run.py').exists()
    assert p.joinpath('20261113_scheduled_input_target_exposure/results.json').exists()
    assert previous.parent.qbits(2,0,15)=='010100100000000011110000000000000111100'
    assert previous.parent.answer(2,0,15)=='000000011110S'
    assert sum(z.numel() for z in previous.parent.network(101).parameters())==10499
    for split,arr in eval_sets().items():
        for r,a,b,c,d in arr:
            Q=previous.parent.qbits(r,a,b,c,d)
            assert len(Q)==39 and Q.endswith('111100') and set(Q)<={'0','1'}
            assert len(previous.parent.answer(r,a,b))==(7 if r==1 else 13)
    for k in ('high_val_r1','high_val_r2','high_test_r1','high_test_r2'):
        assert all(z not in train_rows() for z in eval_sets()[k])
    assert SPEC['epochs']==EPOCHS and SPEC['targets_per_epoch']==TARGETS
    print('GATE PASS 120 payloads, 60/60 r allocation, 18/18 high train, heldout s4/s5, Q39, 10499 params')

@torch.no_grad()
def evaluate(model,seed):
    records=[]; metrics={}; total=0
    for split,items in eval_sets().items():
        correct=first=second=stops=nf=0
        for r,a,b,c,d in items:
            Q=previous.parent.qbits(r,a,b,c,d); target=previous.parent.answer(r,a,b)
            actual,reason,calls=previous.parent.free(model,Q)
            rec={'seed':seed,'split':split,'r':r,'a':a,'b':b,'c':c,'d':d,
                 'Q':Q,'expected':target,'actual':actual,'cause':reason,'forward_calls':calls}
            records.append(rec)
            correct+=actual==target
            first+=actual[:6]==previous.parent.word(a)
            second+=r==2 and actual[6:12]==previous.parent.word(b)
            stops+=actual.endswith('S') and len(actual)==len(target)
            nf+=calls
        metrics[split]={'n':len(items),'exact':int(correct),'first_word':int(first),
                        'second_word':int(second),'stop_position':int(stops),'forward_calls':nf}
        total+=nf
    return records,metrics,total

def main():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    gate()
    output={'work_id':SPEC['work_id'],'source_previous_sha256':SPEC['source_previous_sha256'],
            'pre_sha256':hashlib.sha256((HERE/'PREREGISTRATION.json').read_bytes()).hexdigest(),
            'torch':torch.__version__,'numpy':np.__version__,'epochs':EPOCHS,'batch':BATCH,'parameters':10499,
            'models':[],'train_targets_total':0,'optimizer_updates_total':0,'eval_forward_total':0}
    raw=[];t0=time.perf_counter()
    X,Y=previous.teacher(train_rows())
    for seed in SEEDS:
        model=previous.parent.network(seed)
        initial=previous.parent.weights_sha(model)
        opt=torch.optim.Adam(model.parameters(),lr=0.003)
        updates=0
        for ep in range(EPOCHS):
            permutation=np.random.default_rng(seed+97000+ep).permutation(TARGETS)
            for i in range(0,TARGETS,BATCH):
                indices=permutation[i:i+BATCH]
                loss=nn.functional.cross_entropy(model(X[indices]),Y[indices])
                opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.0);opt.step();updates+=1
        assert updates==3800
        records,metrics,nf=evaluate(model,seed);raw.extend(records)
        name=f'weights_seed{seed}_mixed.json'
        (HERE/name).write_text(json.dumps(previous.parent.checkpoint(model,seed,'HIGH_R_MIXED'),separators=(',',':'))+'\n')
        output['models'].append({'seed':seed,'init_sha256':initial,
            'weights_sha256':previous.parent.weights_sha(model),'checkpoint':name,
            'updates':updates,'metrics':metrics})
        output['train_targets_total']+=EPOCHS*TARGETS
        output['optimizer_updates_total']+=updates
        output['eval_forward_total']+=nf
        print('MODEL',seed,'train',metrics['high_train_r1']['exact'],metrics['high_train_r2']['exact'],
              'val',metrics['high_val_r1']['exact'],metrics['high_val_r2']['exact'],
              'test',metrics['high_test_r1']['exact'],metrics['high_test_r2']['exact'],flush=True)
    rawbytes=''.join(json.dumps(x,separators=(',',':'))+'\n' for x in raw).encode()
    (HERE/'raw_cases.jsonl').write_bytes(rawbytes)
    output['raw_count']=len(raw);output['raw_sha256']=hashlib.sha256(rawbytes).hexdigest()
    output['train_forward_dense_MAC']=output['train_targets_total']*MAC
    output['eval_forward_dense_MAC']=output['eval_forward_total']*MAC
    output['backprop_MAC_not_counted']=True
    output['seconds']=time.perf_counter()-t0
    (HERE/'results.json').write_text(json.dumps(output,indent=2)+'\n')
    print('DONE',output['raw_count'],'rows',output['optimizer_updates_total'],'updates',output['eval_forward_total'],'forwards')

if __name__=='__main__':
    if sys.argv[1:]==['gate']:gate()
    elif sys.argv[1:]==['train']:main()
    else:raise SystemExit('usage: run.py gate|train')
