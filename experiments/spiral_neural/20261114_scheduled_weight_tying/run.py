"""Preregistered SLE-AE1-n5-v1 small-NN word-weight tying study.
Freeze run.py, prereg.json, manifest.jsonl, parent_course.json remotely BEFORE train.
python run.py gate; python run.py train
Student receives 01 only; codec produces teacher labels but not learner output.
"""
import os,sys,json,hashlib,base64,time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
P=Path(__file__).resolve().parent
SEEDS=(101,202,303); ARMS=('tied','untied')
EPOCHS=150; BATCH=64; H=94; EMB=16; L=80; QLEN=39; FORWARD_MAC=4*12*16+105*H+H*3
HIGH=(16,17,18,19); LOW=(0,1,2,3); B=(18,19,22,23)
# shared initial encoder weights, independent after optimizer starts (only factor: tying)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def word(n):
    assert isinstance(n,int) and 0<=n<=29
    return f'{n:05b}0'
def question(r,a,b,c=0,d=0):
    assert r in (1,2)
    s='01'+'010'+f'{r:03b}0'+''.join(word(z) for z in (a,b,c,d))+'111100'
    assert len(s)==39 and set(s)<={'0','1'}
    return s
def answer(r,a,b):return word(a)+(word(b) if r==2 else '')+'S'
def parent():return [tuple(z) for z in json.loads((P/'parent_course.json').read_text())]
def inject():return [(2,h,lo,0,1) for lo in LOW for h in HIGH]
def course():return parent()+inject()
def eval_rows():
    for r in (1,2):
        for a in range(6):
            for b in B: yield dict(split='seen_baseline',r=r,a=a,b=b,c=0,d=0)
    for r,a,b,c,d in inject():yield dict(split='taught_injection',r=r,a=a,b=b,c=c,d=d)
    for a in (8,9):
        for b in B:yield dict(split='val_new_first',r=2,a=a,b=b,c=0,d=1)
    for a in (6,7,10,11,12,13,14):
        for b in B:yield dict(split='test_new_first',r=2,a=a,b=b,c=0,d=1)
    for b in (6,7,10,11,12,13,14):
        for a in (0,1,2,3):yield dict(split='test_new_second',r=2,a=a,b=b,c=0,d=1)
    for a in (6,7,10,11,12,13,14):
        for b in B:yield dict(split='context_c1',r=2,a=a,b=b,c=1,d=1)

def xvec(seq):
    assert len(seq)<=L and set(seq)<={'0','1'}
    x=np.zeros((L,2),dtype=np.float32)
    for i,s in enumerate(seq):x[i,int(s)]=1
    return x.reshape(2*L)

class WordStudent(nn.Module):
    def __init__(self,tied):
        super().__init__(); self.tied=tied
        if tied: self.enc=nn.Linear(12,EMB)
        else:
            self.enc_w=nn.Parameter(torch.empty((4,EMB,12)))
            self.enc_b=nn.Parameter(torch.empty((4,EMB)))
        self.hidden=nn.Linear(4*EMB+8+33,H)
        self.out=nn.Linear(H,3)
    def forward(self,x):
        z=x.reshape(-1,L,2)
        q=z[:,9:33,:].reshape(-1,4,12)
        if self.tied: e=torch.tanh(self.enc(q))
        else:e=torch.tanh(torch.einsum('bik,ijk->bij',q,self.enc_w)+self.enc_b)
        # Student has a raw string; occupancy derives its own current output position.
        cursor=z.sum(-1).sum(-1).long()-QLEN
        pos=F.one_hot(cursor.clamp(0,32),num_classes=33).to(x.dtype)
        header=z[:,5:9,:].reshape(-1,8)
        feat=torch.cat([e.reshape(-1,64),header,pos],dim=-1)
        return self.out(torch.tanh(self.hidden(feat)))

def init_pair(seed):
    torch.manual_seed(seed+12000)
    t=WordStudent(True)
    u=WordStudent(False)
    with torch.no_grad():
        u.enc_w.copy_(t.enc.weight.unsqueeze(0).expand(4,-1,-1))
        u.enc_b.copy_(t.enc.bias.unsqueeze(0).expand(4,-1))
        u.hidden.load_state_dict(t.hidden.state_dict())
        u.out.load_state_dict(t.out.state_dict())
    return t,u

def make_teacher():
    X=[];Y=[]
    for r,a,b,c,d in course():
        q=question(r,a,b,c,d);ans=answer(r,a,b)
        for i,t in enumerate(ans):X.append(xvec(q+ans[:i]));Y.append('01S'.index(t))
    return torch.from_numpy(np.stack(X)),torch.tensor(Y,dtype=torch.long)

def save(m,seed,arm):
    state={}
    for k,v in m.state_dict().items():
        arr=v.detach().cpu().numpy().astype('<f4')
        state[k]=dict(shape=list(arr.shape),little_endian_base64=base64.b64encode(arr.tobytes()).decode())
    out=dict(schema='AE1-WEIGHT-TYING-F32-v1',seed=seed,arm=arm,tied=(arm=='tied'),tensors=state)
    (P/'checkpoints'/f'weights_{seed}_{arm}.json').write_text(json.dumps(out,separators=(',',':'))+'\n')

@torch.no_grad()
def free(m,q):
    actual='';n=0;cause='cap'
    for _ in range(32):
        if len(q)+len(actual)>L:cause='overflow';break
        logits=m(torch.from_numpy(xvec(q+actual)).unsqueeze(0))[0]
        actual+='01S'[int(logits.argmax())]; n+=1
        if actual[-1]=='S':cause='stop';break
    return actual,cause,n

def gate():
    spec=json.loads((P/'prereg.json').read_text())
    assert spec['runner_sha256']==sha(P/'run.py')
    assert spec['manifest_sha256']==sha(P/'manifest.jsonl')
    assert spec['parent_sha256']==sha(P/'parent_course.json')
    assert spec['profile']=='SLE-AE1-n5-v1'
    assert SEEDS==tuple(spec['seeds']) and EPOCHS==spec['epochs']
    manifest=[json.loads(x) for x in (P/'manifest.jsonl').read_text().splitlines()]
    assert len(manifest)==len(list(eval_rows()))==156
    assert manifest==[{**v,'Q':question(v['r'],v['a'],v['b'],v['c'],v['d']),'expected':answer(v['r'],v['a'],v['b'])} for v in eval_rows()]
    assert len({r['Q'] for r in manifest})==len(manifest)
    assert len(course())==136 and len(set(course()))==112 and len(parent())==120
    values=set().union(*(set(c[1:5]) for c in course()))
    assert not values.intersection({6,7,8,9,10,11,12,13,14,24,25,26,27,28,29})
    assert sum(v[0]==1 for v in course())==60
    X,Y=make_teacher();assert X.shape==(1408,160) and len(Y)==1408
    tied,untied=init_pair(101)
    assert sum(p.numel() for p in tied.parameters())==10457
    assert sum(p.numel() for p in untied.parameters())==11081
    assert FORWARD_MAC==10920
    assert spec['updates_per_student']==EPOCHS*22
    print('PREFLIGHT PASS 136 lessons/112 distinct; 1408 targets; 156 legal raw Q; no unexposed values in course; tied10457 untied11081; MAC10920; no optimizer',flush=True)

def train():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    gate();before=time.monotonic();spec=json.loads((P/'prereg.json').read_text());X,Y=make_teacher()
    rows=[];blocks=[];total_fw=0
    manifest=[json.loads(x) for x in (P/'manifest.jsonl').read_text().splitlines()]
    for seed in SEEDS:
        tied,untied=init_pair(seed)
        with torch.no_grad():
            probe=X[:14];d=(tied(probe)-untied(probe)).abs().max().item()
        assert d<1e-6,('initial_function_mismatch',seed,d)
        for arm,m in (('tied',tied),('untied',untied)):
            opt=torch.optim.Adam(m.parameters(),lr=0.003)
            updates=0
            for ep in range(EPOCHS):
                order=np.random.default_rng(seed+201000+ep).permutation(len(Y))
                for k in range(0,len(Y),BATCH):
                    b=order[k:k+BATCH];loss=F.cross_entropy(m(X[b]),Y[b]);opt.zero_grad();loss.backward()
                    nn.utils.clip_grad_norm_(m.parameters(),1.0);opt.step();updates+=1
            assert updates==3300
            save(m,seed,arm)
            totals={}
            for v in manifest:
                actual,cause,n=free(m,v['Q']);total_fw+=n
                row=dict(seed=seed,arm=arm,**v,actual=actual,cause=cause,forward_calls=n,exact=(actual==v['expected']))
                rows.append(row)
                if v['split'] not in totals:totals[v['split']]=dict(correct=0,n=0,stop=0)
                totals[v['split']]['n']+=1;totals[v['split']]['correct']+=row['exact'];totals[v['split']]['stop']+=(cause=='stop' and len(actual)==len(v['expected']))
            blocks.append(dict(seed=seed,arm=arm,params=sum(p.numel() for p in m.parameters()),updates=updates,
                checkpoint_sha256=sha(P/'checkpoints'/f'weights_{seed}_{arm}.json'),metrics=totals))
            print('STUDENT',seed,arm,{k:v['correct'] for k,v in totals.items()},flush=True)
    gates=[]
    for seed in SEEDS:
        a=next(x for x in blocks if x['seed']==seed and x['arm']=='tied')['metrics']
        b=next(x for x in blocks if x['seed']==seed and x['arm']=='untied')['metrics']
        gates.append(dict(seed=seed,shared=a['test_new_first']['correct'],untied=b['test_new_first']['correct'],
            baseline_shared=a['seen_baseline']['correct'],baseline_untied=b['seen_baseline']['correct'],
            pass_gate=(a['test_new_first']['correct']>=12 and a['test_new_first']['correct']-b['test_new_first']['correct']>=6 and a['seen_baseline']['correct']>=40 and b['seen_baseline']['correct']>=40)))
    successful=sum(x['pass_gate'] for x in gates)
    raw=''.join(json.dumps(x,separators=(',',':'))+'\n' for x in rows).encode()
    (P/'raw_cases.jsonl').write_bytes(raw)
    result=dict(work_id=spec['work_id'],profile=spec['profile'],source_branch=spec['source_branch'],
        freeze_commit=os.getenv('NN_FREEZE_SHA','UNSET'),source_checkpoint_used=False,
        seeds=list(SEEDS),epochs=EPOCHS,updates_per_student=3300,total_updates=3300*len(blocks),
        teacher_targets_per_epoch=len(Y),train_forward_MAC=1408*EPOCHS*len(blocks)*FORWARD_MAC,
        backward_MAC_excluded=True,inference_forward_calls=total_fw,inference_MAC=total_fw*FORWARD_MAC,
        raw_rows=len(rows),raw_sha256=hashlib.sha256(raw).hexdigest(),student_count=len(blocks),
        status='PASS' if successful>=2 else 'FAIL',seed_gates=gates,blocks=blocks,wall_seconds=time.monotonic()-before,
        independent_audit_pending=True)
    (P/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('OUTCOME',result['status'],'passing seeds',successful,'/',len(SEEDS),'raw',len(rows),'forward',total_fw,flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['gate']:gate()
    elif sys.argv[1:]==['train']:train()
    elif sys.argv[1:]==['manifest']:
        for v in eval_rows():
            print(json.dumps({**v,'Q':question(v['r'],v['a'],v['b'],v['c'],v['d']),'expected':answer(v['r'],v['a'],v['b'])},separators=(',',':')))
    else:raise SystemExit('usage: python run.py gate|train|manifest')
