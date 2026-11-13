"""Preregistered AE1 high-word mixed-role curriculum. See protocol.json.
Run inside full repository checkout, alongside PR36's unmodified role-swap pilot.
Only trains a new MIX arm; exclusive arms are referenced from PR36, never retrained here.
"""
import base64
import copy
import hashlib
import json
import sys
import time
from pathlib import Path
import numpy as np
import torch
from torch import nn

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'20261113_scheduled_role_swap_pilot'
sys.path.insert(0,str(PARENT))
import run as parent

PROTOCOL=json.loads((HERE/'protocol.json').read_text())
SEEDS=(101,202)
EPOCHS=250
BATCH=64
TARGETS=948
PARENT_RUN_SHA='05e2d730eecefcb50fa92392697556ffde313f5ecb59c2f4e583aad52e321303'

def mixed_rows():
    return [(2,v,s) if (v-6+s)%2==0 else (2,s,v)
            for v in range(6,15) for s in range(4)]

def inverse_rows():
    return [(2,s,v) if (v-6+s)%2==0 else (2,v,s)
            for v in range(6,15) for s in range(4)]

def heldout_rows(s):
    return {'HIGH_FIRST':[(2,v,s) for v in range(6,15)],
            'HIGH_SECOND':[(2,s,v) for v in range(6,15)]}

def source_gate():
    assert hashlib.sha256((PARENT/'run.py').read_bytes()).hexdigest()==PARENT_RUN_SHA
    original=json.loads((PARENT/'results.json').read_text())
    assert len(original['models'])==4
    assert original['raw_case_count']==720
    assert original['raw_sha256']=='698fc69c95d7a8c3227c6387f0119908def86fa4efc3c24bdb920117a643ed5a'
    assert hashlib.sha256((PARENT/'raw_cases.jsonl').read_bytes()).hexdigest()==original['raw_sha256']
    return original

def selftest():
    original=source_gate()
    parent.selftest()
    supplement=mixed_rows(); inverse=inverse_rows()
    assert len(supplement)==len(inverse)==36 and len(set(supplement))==36
    assert set(supplement).isdisjoint(inverse)
    assert len(set(supplement+inverse))==72
    assert sum(a>=6 for _,a,b in supplement)==18
    assert sum(b>=6 for _,a,b in supplement)==18
    assert all(sum((a==v or b==v) for _,a,b in supplement)==4 for v in range(6,15))
    assert all(sum((a==s or b==s) for _,a,b in supplement)==9 for s in range(4))
    assert all(sum(a==v for _,a,b in supplement)==2 and sum(b==v for _,a,b in supplement)==2 for v in range(6,15))
    assert len(parent.base_rows('train'))==48 and len(parent.base_rows('val'))==12 and len(parent.base_rows('test'))==12
    train=parent.base_rows('train')+supplement
    X,y=parent.teacher(train)
    assert X.shape==(TARGETS,160) and y.shape==(TARGETS,)
    assert sum(p.numel() for p in parent.network(101).parameters())==10499
    assert parent.qbits(2,0,6)==PROTOCOL['profile']['fixture_question_second_high']
    assert parent.qbits(2,6,0)==PROTOCOL['profile']['fixture_question_first_high']
    assert parent.answer(2,0,6)==PROTOCOL['profile']['fixture_answer_second_high']
    assert parent.answer(2,6,0)==PROTOCOL['profile']['fixture_answer_first_high']
    all_rows=train+inverse+[case for s in (4,5) for rows in heldout_rows(s).values() for case in rows]
    for r,a,b in all_rows:
        assert a<=29 and b<=29
        q=parent.qbits(r,a,b)
        assert len(q)==39 and set(q)<={'0','1'} and q.endswith('111100')
        ans=parent.answer(r,a,b)
        assert ans.endswith('S') and (len(ans)==7 if r==1 else len(ans)==13)
        assert q.count('S')==0
    assert all(((a+b)%6>=2) for r,a,b in parent.base_rows('train'))
    assert all(((a+b)%6==0) for r,a,b in parent.base_rows('val'))
    assert all(((a+b)%6==1) for r,a,b in parent.base_rows('test'))
    assert {(a,b) for r,a,b in supplement}.isdisjoint({(a,b) for r,a,b in inverse})
    assert set(a for _,a,b in supplement if a>=6)==set(range(6,15))
    for seed in SEEDS:
        startsha=parent.weights_sha(parent.network(seed))
        assert all(m['init_sha256']==startsha for m in original['models'] if m['seed']==seed)
    print('GATE PASS: frozen PR36 source; 39 bit/valid profile; 24/6/6 base; 36 mixed +36 inverse; 18+18 val/test; 948 targets; paired init sha',flush=True)

@torch.no_grad()
def scored(m,seed,split,cases):
    rows=[]
    metrics={'n':len(cases),'exact':0,'first_word_correct':0,'second_word_correct':0,'stop_correct':0,'terminal_zero_correct':0,
             'bad_cap':0,'forward_calls':0}
    for r,a,b in cases:
        q=parent.qbits(r,a,b); exp=parent.answer(r,a,b)
        got,why,n=parent.free(m,q)
        record={'seed':seed,'arm':'MIX_PARITY','split':split,'r':r,'a':a,'b':b,'c':0,'d':0,
                'Q':q,'expected':exp,'actual':got,'cause':why,'forward_calls':n}
        rows.append(record)
        metrics['exact']+=int(got==exp)
        metrics['first_word_correct']+=int(got[:6]==parent.word(a))
        metrics['second_word_correct']+=int(r==2 and got[6:12]==parent.word(b))
        metrics['stop_correct']+=int(got.endswith('S') and len(got)==len(exp))
        metrics['terminal_zero_correct']+=int(len(got)>=6 and got[5]=='0' and (r==1 or len(got)>=12 and got[11]=='0'))
        metrics['bad_cap']+=int(why!='stop')
        metrics['forward_calls']+=n
    return rows,metrics

def main():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    selftest()
    src=source_gate()
    results={'work_id':PROTOCOL['work_id'],'preregistered_before_run':True,
             'protocol_sha256':hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),
             'source_pr36_commit':PROTOCOL['source']['base_head_commit'],
             'software':{'torch':torch.__version__,'numpy':np.__version__},
             'seeds':list(SEEDS),'epochs':EPOCHS,'batch':BATCH,'parameters':10499,
             'learning_rate':0.003,'models':[], 'all_new_optimizer_steps':0,'all_new_target_exposures':0}
    all_samples=[]
    started=time.perf_counter()
    for seed in SEEDS:
        initial=parent.network(seed)
        init_sha=parent.weights_sha(initial)
        m=copy.deepcopy(initial)
        X,y=parent.teacher(parent.base_rows('train')+mixed_rows())
        opt=torch.optim.Adam(m.parameters(),lr=.003)
        permutations=[np.random.default_rng(seed+87000+epoch).permutation(TARGETS) for epoch in range(EPOCHS)]
        steps=0;loss_anchor={}
        for epoch in range(EPOCHS):
            for i in range(0,TARGETS,BATCH):
                ii=permutations[epoch][i:i+BATCH]
                logits=m(X[ii]);loss=nn.functional.cross_entropy(logits,y[ii]);opt.zero_grad();loss.backward()
                nn.utils.clip_grad_norm_(m.parameters(),1.0)
                opt.step();steps+=1
            if epoch+1 in (1,100,250):loss_anchor[str(epoch+1)]=float(loss.detach())
        assert steps==3750
        stats={}
        cases={'base_train':parent.base_rows('train'), 'base_val':parent.base_rows('val'), 'base_test':parent.base_rows('test'),
               'mixed_taught_orientation':mixed_rows(), 'inverse_not_taught':inverse_rows(),
               'heldout_s4_high_first':heldout_rows(4)['HIGH_FIRST'],
               'heldout_s4_high_second':heldout_rows(4)['HIGH_SECOND'],
               'heldout_s5_high_first':heldout_rows(5)['HIGH_FIRST'],
               'heldout_s5_high_second':heldout_rows(5)['HIGH_SECOND']}
        for split,questions in cases.items():
            new,metrics=scored(m,seed,split,questions)
            all_samples.extend(new);stats[split]=metrics
        ck=parent.checkpoint(m,seed,'MIX_PARITY');ck['schema']='AE1-ROLE-MIX-F32-v1'
        filename=f'weights_seed{seed}_mix_parity.json'
        (HERE/filename).write_text(json.dumps(ck,separators=(',',':'))+'\n')
        results['models'].append({'seed':seed,'arm':'MIX_PARITY','initial_sha256':init_sha,
             'final_sha256':parent.weights_sha(m),'checkpoint':filename,'updates':steps,
             'target_exposures':EPOCHS*TARGETS,'loss_anchor':loss_anchor,'metrics':stats})
        results['all_new_optimizer_steps']+=steps
        results['all_new_target_exposures']+=EPOCHS*TARGETS
        print('MODEL',seed,'fitted',stats['mixed_taught_orientation']['exact'],'/36',
              'inverse',stats['inverse_not_taught']['exact'],'/36',
              'hold s4 first/second',stats['heldout_s4_high_first']['exact'],stats['heldout_s4_high_second']['exact'],
              'hold s5 first/second',stats['heldout_s5_high_first']['exact'],stats['heldout_s5_high_second']['exact'],flush=True)
    results['all_new_training_dense_forward_MAC']=results['all_new_target_exposures']*10432
    results['all_new_eval_forward_calls']=sum(z['forward_calls'] for m in results['models'] for z in m['metrics'].values())
    results['all_new_eval_dense_forward_MAC']=results['all_new_eval_forward_calls']*10432
    results['total_raw_cases']=len(all_samples)
    results['elapsed_seconds']=time.perf_counter()-started
    payload=''.join(json.dumps(z,separators=(',',':'))+'\n' for z in all_samples)
    (HERE/'raw_cases.jsonl').write_text(payload)
    results['raw_sha256']=hashlib.sha256(payload.encode()).hexdigest()
    (HERE/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('RESULT',len(all_samples),'raw',results['all_new_optimizer_steps'],'new updates',results['all_new_eval_forward_calls'],'evaluation forward',round(results['elapsed_seconds'],3),'sec',flush=True)

if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='selftest': selftest()
    elif len(sys.argv)==2 and sys.argv[1]=='train':main()
    else: raise SystemExit('Usage: python run.py {selftest|train}')
