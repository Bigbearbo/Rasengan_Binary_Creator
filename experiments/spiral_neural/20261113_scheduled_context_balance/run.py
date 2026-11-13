"""AE1 contextual generalization: replace 8/16 c1 training suffixes with c0.
Pure native SLE 0/1 questions, true PyTorch student, no answer oracle at inference.
Run: python run.py gate ; python run.py train (after remote prereg freeze).
"""
import base64, copy, hashlib, json, sys, time
from pathlib import Path
import numpy as np
import torch
from torch import nn

HERE=Path(__file__).resolve().parent
IN=HERE/'frozen_inputs'
SEEDS=(101,202)
L,H,MAC,BATCH,EPOCHS=80,64,10432,64,100
VALUES=(24,25,28,29)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def word(x):
    assert type(x)==int and 0<=x<=29
    return f'{x:05b}0'
def qbits(r,a,b,c=0,d=0):
    assert r in (1,2)
    q='01'+'010'+f'{r:03b}'+'0'+''.join(word(x) for x in (a,b,c,d))+'111100'
    assert len(q)==39 and set(q)<={'0','1'}
    return q
def ans(r,a,b):return word(a)+(word(b) if r==2 else '')+'S'
def xvec(s):
    assert 0<len(s)<=L and set(s)<={'0','1'}
    z=np.zeros(160,np.float32)
    for i,c in enumerate(s):z[2*i+int(c)]=1.0
    return z
def new_model():return nn.Sequential(nn.Linear(160,H),nn.Tanh(),nn.Linear(H,3))
def modelhash(m):
    h=hashlib.sha256()
    for k,v in m.state_dict().items():h.update(k.encode());h.update(v.detach().numpy().tobytes())
    return h.hexdigest()
def load(seed,suffix):
    j=json.loads((IN/f'weights_seed{seed}_{suffix}.json').read_text())
    m=new_model(); states={}
    for k,z in j['tensors'].items():
        arr=np.frombuffer(base64.b64decode(z['little_endian_base64']),'<f4').copy().reshape(z['shape'])
        states[k]=torch.from_numpy(arr)
    m.load_state_dict(states)
    assert modelhash(m)==j['weights_sha256'],('checkpoint-corruption',seed,suffix)
    return m
def save(m,seed):
    obj={'schema':'AE1-CONTEXT-BALANCE-F32-v1','seed':seed,'arm':'balanced_c',
         'weights_sha256':modelhash(m),'tensors':{
         k:{'shape':list(v.shape),'little_endian_base64':base64.b64encode(v.detach().numpy().astype('<f4').tobytes()).decode()}
         for k,v in m.state_dict().items()}}
    (HERE/f'weights_seed{seed}_balanced_c.json').write_text(json.dumps(obj,separators=(',',':'))+'\n')
def parent_course():return [tuple(x) for x in json.loads((IN/'parent_course.json').read_text())]
def injection(c_policy):
    assert c_policy in ('c1_only','balanced_c')
    # Same r,a,b,d and exact same target string; only c differs in eight Q.
    return [(2,a,v,1 if c_policy=='c1_only' else ((a+j)%2),0)
            for j,v in enumerate(VALUES) for a in range(4)]
def rows(policy):return parent_course()+injection(policy)
def teacher(items):
    X=[];Y=[]
    for r,a,b,c,d in items:
        q=qbits(r,a,b,c,d);y=ans(r,a,b)
        for i,z in enumerate(y):
            X.append(xvec(q+y[:i]));Y.append('01S'.index(z))
    return torch.from_numpy(np.stack(X)),torch.tensor(Y,dtype=torch.int64)
@torch.no_grad()
def free(m,q):
    out=''
    for i in range(32):
        if len(q)+len(out)>L:return out,'overflow',i
        logits=m(torch.from_numpy(xvec(q+out)).unsqueeze(0))[0]
        out+='01S'[int(logits.argmax())]
        if out.endswith('S'):return out,'stop',i+1
    return out,'cap',32

def eval_sets():
    low=lambda split:[(r,a,b,0,0) for a in range(6) for b in range(6)
        if ('val' if (a+b)%6==0 else 'test' if (a+b)%6==1 else 'train')==split for r in (1,2)]
    return {
       'base_train':low('train'),'base_val':low('val'),'base_test':low('test'),
       'seen_high_r2':[(2,a,b,0,0) for b in range(16,22) for a in range(6)],
       'taught_bit_conjunction_c0':[(2,a,b,0,0) for b in VALUES for a in range(4)],
       'taught_bit_conjunction_c1':[(2,a,b,1,0) for b in VALUES for a in range(4)],
       'heldout_b26_27_c0_trainpartner':[(2,a,b,0,0) for b in (26,27) for a in range(4)],
       'heldout_b26_27_c1_trainpartner':[(2,a,b,1,0) for b in (26,27) for a in range(4)],
       'heldout_b26_27_c0_val':[(2,4,b,0,0) for b in (26,27)],
       'heldout_b26_27_c0_test':[(2,5,b,0,0) for b in (26,27)],
       'heldout_b26_27_c1_val':[(2,4,b,1,0) for b in (26,27)],
       'heldout_b26_27_c1_test':[(2,5,b,1,0) for b in (26,27)],
       'heldout_b26_27_c2_stress':[(2,a,b,2,0) for b in (26,27) for a in range(6)],
       'r1_ignores_new_b':[(1,a,b,0,0) for b in range(24,30) for a in (4,5)]
    }
@torch.no_grad()
def evaluate(m,seed,arm):
    rec=[];metrics={};forward=0
    for tag,items in eval_sets().items():
        correct=stop=first=second=0;fail=[]
        for r,a,b,c,d in items:
            q=qbits(r,a,b,c,d);expected=ans(r,a,b);actual,why,n=free(m,q)
            rec.append({'seed':seed,'arm':arm,'split':tag,'r':r,'a':a,'b':b,'c':c,'d':d,
                        'Q':q,'expected':expected,'actual':actual,'cause':why,'forward_calls':n})
            forward+=n;correct+=actual==expected
            stop+=actual.endswith('S') and len(actual)==len(expected)
            first+=actual[:6]==word(a)
            second+=r==2 and actual[6:12]==word(b)
            if actual!=expected:fail.append({'r':r,'a':a,'b':b,'c':c,'d':d,'Q':q,'expected':expected,'actual':actual})
        metrics[tag]={'n':len(items),'exact':int(correct),'stop_position':int(stop),'first_word':int(first),'second_word':int(second),'failures':fail}
    return rec,metrics,forward

def gate():
    spec=json.loads((HERE/'PREREGISTRATION.json').read_text())
    assert sha(HERE/'run.py')==spec['runner_sha256']
    assert sha(IN/'parent_course.json')==spec['source_sha256']['parent_course']
    torch.set_num_threads(1)
    for seed in SEEDS:
        for suffix in ('mixed','conjunction'):
            assert sha(IN/f'weights_seed{seed}_{suffix}.json')==spec['source_sha256'][f'{seed}_{suffix}']
            assert sum(p.numel() for p in load(seed,suffix).parameters())==10499
        control=load(seed,'conjunction')
        # Independently inspect frozen old control; no baseline retraining.
        rec,stats,n=evaluate(control,seed,'frozen_c1_control')
        c0=stats['heldout_b26_27_c0_val']['exact']+stats['heldout_b26_27_c0_test']['exact']
        c1=stats['heldout_b26_27_c1_val']['exact']+stats['heldout_b26_27_c1_test']['exact']
        assert c0==0 and c1==spec['source_control_c1_4'][str(seed)],(seed,c0,c1)
        assert stats['seen_high_r2']['exact']==36
        print('PR44 CONTROL GATE',seed,'heldout c0',c0,'/4, c1',c1,'/4, known36/36',flush=True)
    p=parent_course()
    assert len(p)==120 and len(set(p))==96 and sum(x[0]==1 for x in p)==60 and sum(x[0]==2 for x in p)==60
    z=injection('c1_only');m=injection('balanced_c')
    assert len(z)==len(m)==16 and len(set(z))==len(set(m))==16
    assert all((r,a,b,d)==(R,A,B,D) for (r,a,b,c,d),(R,A,B,C,D) in zip(z,m))
    assert all(ans(r,a,b)==ans(R,A,B) for (r,a,b,c,d),(R,A,B,C,D) in zip(z,m))
    assert sum(c!=C for (_,_,_,c,_),(_,_,_,C,_) in zip(z,m))==8
    assert sum(x[3]==0 for x in m)==8 and sum(x[3]==1 for x in m)==8
    assert all(sum(x[3]==c for x in m if x[1]==a)==2 for a in range(4) for c in (0,1))
    assert all(sum(x[3]==c for x in m if x[2]==b)==2 for b in VALUES for c in (0,1))
    for policy in ('c1_only','balanced_c'):
        rs=rows(policy);X,Y=teacher(rs)
        assert len(rs)==136 and len(set(rs))==112 and X.shape==(1408,160) and Y.shape==(1408,)
        assert set(rs).isdisjoint(eval_sets()['heldout_b26_27_c0_test'])
        assert set(rs).isdisjoint(eval_sets()['heldout_b26_27_c1_val'])
        assert set(rs).isdisjoint(eval_sets()['heldout_b26_27_c2_stress'])
    X,Y=teacher(rows('balanced_c'));x,y=teacher(rows('c1_only'))
    assert torch.equal(Y,y), 'answer teaching sequence changed!'
    assert (X!=x).any() and (X!=x).sum().item()>0
    assert qbits(2,0,24,0,0)==spec['fixtures']['Q_c0']
    assert qbits(2,0,24,1,0)==spec['fixtures']['Q_c1']
    assert ans(2,0,24)==spec['fixtures']['answer']
    assert spec['new_students']==2 and spec['updates_per_student']==2200 and spec['train_forward_dense_MAC']==2937651200
    print('PRETRAIN GATE PASS: 8/16 Q c changed, Y identical, 1408 targets, 10499 params, frozen control verified',flush=True)


def train():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);gate()
    spec=json.loads((HERE/'PREREGISTRATION.json').read_text())
    t0=time.perf_counter();recs=[];rows_out=[];eval_fw=0
    # Checkpoint-based control: exact PR44 weights already verified by gate.
    for seed in SEEDS:
        ctl=load(seed,'conjunction');x,metric,n=evaluate(ctl,seed,'frozen_c1_control')
        recs+=x;eval_fw+=n
        rows_out.append({'seed':seed,'arm':'frozen_c1_control','parent_file_sha256':sha(IN/f'weights_seed{seed}_conjunction.json'),
                         'updates_this_run':0,'metrics':metric,'final_weights_sha256':modelhash(ctl)})
        parent=load(seed,'mixed');student=copy.deepcopy(parent);assert modelhash(parent)==modelhash(student)
        X,Y=teacher(rows('balanced_c'))
        opt=torch.optim.Adam(student.parameters(),lr=0.003)
        updates=0
        for ep in range(EPOCHS):
            ii=np.random.default_rng(seed+131000+ep).permutation(1408)
            for k in range(0,1408,BATCH):
                batch=ii[k:k+BATCH]
                loss=nn.functional.cross_entropy(student(X[batch]),Y[batch]);opt.zero_grad()
                loss.backward();nn.utils.clip_grad_norm_(student.parameters(),1.0);opt.step();updates+=1
        assert updates==2200
        save(student,seed)
        x,metric,n=evaluate(student,seed,'balanced_c')
        recs+=x;eval_fw+=n
        rows_out.append({'seed':seed,'arm':'balanced_c','parent_file_sha256':sha(IN/f'weights_seed{seed}_mixed.json'),
                         'updates_this_run':2200,'metrics':metric,'final_weights_sha256':modelhash(student)})
        print('TRAIN',seed,'c0',metric['heldout_b26_27_c0_val']['exact']+metric['heldout_b26_27_c0_test']['exact'],'/4',
              'c1',metric['heldout_b26_27_c1_val']['exact']+metric['heldout_b26_27_c1_test']['exact'],'/4',flush=True)
    raw=''.join(json.dumps(z,separators=(',',':'))+'\n' for z in recs).encode()
    (HERE/'raw_cases.jsonl').write_bytes(raw)
    seeds=[]
    for seed in SEEDS:
        control=next(x for x in rows_out if x['seed']==seed and x['arm']=='frozen_c1_control')['metrics']
        treated=next(x for x in rows_out if x['seed']==seed and x['arm']=='balanced_c')['metrics']
        sc=lambda m,c:m[f'heldout_b26_27_c{c}_val']['exact']+m[f'heldout_b26_27_c{c}_test']['exact']
        a,b,c,d=sc(control,0),sc(control,1),sc(treated,0),sc(treated,1)
        seeds.append({'seed':seed,'frozen_c0':a,'frozen_c1':b,'balanced_c0':c,'balanced_c1':d,
                      'gate':c-a>=2 and d>=b-1})
    out={'work_id':spec['work_id'],'frozen_pr44_sha':spec['source_git_pr44_head'],
         'profile':spec['profile'],'source':'U user learning objective; F PR40 & PR44; T local PyTorch and independent NumPy; A c-suffix augmentation',
         'new_student_count':2,'reused_control_checkpoints':2,'new_optimizer_updates':4400,'new_target_exposures':281600,
         'parameters_per_student':10499,'train_forward_dense_MAC':2937651200,'excludes_backward_and_optimizer_MAC':True,
         'evaluation_forward_calls':eval_fw,'evaluation_dense_MAC':eval_fw*MAC,'raw_rows':len(recs),
         'raw_sha256':hashlib.sha256(raw).hexdigest(),'seconds':time.perf_counter()-t0,
         'all_models':rows_out,'primary_gate':{'pass':all(x['gate'] for x in seeds),'seed_results':seeds},
         'c2_stress_not_heldout_of_parent_value':True,'known_researcher_exposed_test':True,
         'nvidia_actual_calls':0,'codex_actual_calls':0,'external_llm_oracle_calls':0}
    (HERE/'RESULTS.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('DONE',len(recs),'rows',eval_fw,'eval forward, 4400 updates, primary',out['primary_gate']['pass'],flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['gate']:gate()
    elif sys.argv[1:]==['train']:train()
    else:raise SystemExit('usage: python run.py gate|train')
