"""Matched AE1 bit8+bit16 conjunction teaching. Actual PyTorch native-01 learners.
Pre-registered curriculum only; not a parser, oracle NN, or HAMU VM.
Run \`python run.py gate\` then \`python run.py train\` exactly once.
"""
import base64,copy,hashlib,json,sys,time
from pathlib import Path
import numpy as np
import torch
from torch import nn
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'20261113_scheduled_high_r_mixed'
L,H,MAC,BATCH,EPOCHS=80,64,10432,64,100
SEEDS=(101,202)
ARMS={'control':(16,17,20,21),'conjunction':(24,25,28,29)}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def word(x):
    assert type(x)==int and 0<=x<=29
    return f'{x:05b}0'
def qbits(r,a,b,c=0,d=0):
    assert r in (1,2)
    q='01'+'010'+f'{r:03b}'+'0'+''.join(word(x) for x in (a,b,c,d))+'111100'
    assert len(q)==39
    return q
def ans(r,a,b):return word(a)+(word(b) if r==2 else '')+'S'
def xvec(s):
    assert len(s)<=L and s and set(s)<={'0','1'}
    z=np.zeros(160,np.float32)
    for i,c in enumerate(s):z[2*i+int(c)]=1.0
    return z
def new_model():return nn.Sequential(nn.Linear(160,64),nn.Tanh(),nn.Linear(64,3))
def load_parent(seed):
    p=PARENT/f'weights_seed{seed}_mixed.json'
    j=json.loads(p.read_text());m=new_model();states={}
    for k,z in j['tensors'].items():
        arr=np.frombuffer(base64.b64decode(z['little_endian_base64']),'<f4').copy().reshape(z['shape'])
        states[k]=torch.from_numpy(arr)
    m.load_state_dict(states)
    assert modelhash(m)==j['weights_sha256']
    return m
def modelhash(m):
    h=hashlib.sha256()
    for k,v in m.state_dict().items():
        h.update(k.encode());h.update(v.detach().numpy().tobytes())
    return h.hexdigest()
def save_state(m,seed,arm):
    j={'schema':'AE1-BIT8-CONJUNCTION-F32-v1','seed':seed,'arm':arm,'weights_sha256':modelhash(m),
       'tensors':{k:{'shape':list(v.shape),'little_endian_base64':base64.b64encode(v.detach().numpy().astype('<f4').tobytes()).decode()}
       for k,v in m.state_dict().items()}}
    (HERE/f'weights_seed{seed}_{arm}.json').write_text(json.dumps(j,separators=(',',':'))+'\n')
def course():return [tuple(z) for z in json.loads((HERE/'parent_course.json').read_text())]
def new_items(arm):return [(2,s,v,1,0) for v in ARMS[arm] for s in range(4)]
def rows(arm):return course()+new_items(arm)
def teacher(items):
    X=[];Y=[]
    for r,a,b,c,d in items:
        q=qbits(r,a,b,c,d);answer=ans(r,a,b)
        for i,z in enumerate(answer):
            X.append(xvec(q+answer[:i]));Y.append('01S'.index(z))
    return torch.from_numpy(np.stack(X)),torch.tensor(Y,dtype=torch.int64)
@torch.no_grad()
def free(m,q):
    out=''
    for t in range(32):
        if len(q)+len(out)>L:return out,'overflow',t
        logits=m(torch.from_numpy(xvec(q+out)).unsqueeze(0))[0]
        out+='01S'[int(logits.argmax())]
        if out.endswith('S'):return out,'stop',t+1
    return out,'cap',32

def eval_sets():
    base=lambda split:[(r,a,b,0,0) for a in range(6) for b in range(6) if ('val' if (a+b)%6==0 else 'test' if (a+b)%6==1 else 'train')==split for r in (1,2)]
    return {
      'base_train':base('train'),'base_val':base('val'),'base_test':base('test'),
      'seen_high_r2':[(2,s,v,0,0) for v in range(16,22) for s in range(6)],
      'new_conjunction_training_domain':[(2,s,v,1,0) for v in (24,25,28,29) for s in range(4)],
      'heldout_novel_lower_bits_train_partner':[(2,s,v,1,0) for v in (26,27) for s in range(4)],
      'heldout_novel_lower_bits_val_partner':[(2,s,v,1,0) for v in (26,27) for s in (4,)],
      'heldout_novel_lower_bits_test_partner':[(2,s,v,1,0) for v in (26,27) for s in (5,)],
      'r1_ignores_new_b':[(1,s,v,0,0) for v in range(24,30) for s in (4,5)],
      'heldout_original_c0':[(2,s,v,0,0) for v in (26,27) for s in range(6)]
    }

def gate():
    spec=json.loads((HERE/'PREREGISTRATION.json').read_text())
    assert sha(HERE/'parent_course.json')==spec['parent_course_sha256']
    assert sha(PARENT/'weights_seed101_mixed.json')==spec['parent_checkpoint_file_sha256']['101']
    assert sha(PARENT/'weights_seed202_mixed.json')==spec['parent_checkpoint_file_sha256']['202']
    assert sha(HERE/'run.py')==spec['runner_sha256']
    assert len(course())==120
    assert all(qbits(*r).endswith('111100') and len(qbits(*r))==39 for r in course())
    assert sum(r[0]==1 for r in course())==60 and sum(r[0]==2 for r in course())==60
    for arm in ARMS:
        assert len(rows(arm))==136
        assert len(set(course()))==96 and len(set(rows(arm)))==112
        assert len(set(new_items(arm)))==16 and set(course()).isdisjoint(new_items(arm))
        assert len(new_items(arm))==16
        X,Y=teacher(rows(arm))
        assert X.shape==(1408,160) and Y.shape==(1408,)
        assert len(set(map(tuple,rows(arm)))&set(eval_sets()['heldout_novel_lower_bits_test_partner']))==0
        assert len(set(map(tuple,rows(arm)))&set(eval_sets()['heldout_novel_lower_bits_val_partner']))==0
    assert 10499==sum(p.numel() for p in new_model().parameters())
    assert qbits(2,0,24,1,0)=='010100100000000110000000010000000111100'
    assert ans(2,0,24)=='000000110000S'
    torch.set_num_threads(1)
    for seed in SEEDS:
        m=load_parent(seed)
        old=sum(free(m,qbits(2,s,v))[0]==ans(2,s,v) for s in range(6) for v in range(16,22))
        novelty=sum(free(m,qbits(2,s,v))[0]==ans(2,s,v) for s in range(6) for v in range(24,30))
        assert (old,novelty)==(36,0),(seed,old,novelty)
        print('PARENT GATE',seed,'known',old,'/36; bit8+16',novelty,'/36')
    assert spec['epochs']==EPOCHS and spec['updates_per_student']==2200
    print('PRE-TRAIN GATE PASS: 136 presented Q/arm (112 unique; parent 24 intentional duplicates), 1408 target/epoch, split, profile, parent frozen, 10499 params')

@torch.no_grad()
def evaluate(m,seed,arm):
    rec=[];meta={};nf=0
    for tag,items in eval_sets().items():
        exact=stops=first=second=0;fail=[]
        for r,a,b,c,d in items:
            q=qbits(r,a,b,c,d);target=ans(r,a,b);actual,why,n=free(m,q)
            rec.append({'seed':seed,'arm':arm,'split':tag,'r':r,'a':a,'b':b,'c':c,'d':d,'Q':q,'expected':target,'actual':actual,'cause':why,'forward_calls':n})
            nf+=n;exact+=actual==target;stops+=actual.endswith('S') and len(actual)==len(target)
            first+=actual[:6]==word(a);second+=r==2 and actual[6:12]==word(b)
            if actual!=target:fail.append({'a':a,'b':b,'r':r,'actual':actual,'expected':target})
        meta[tag]={'n':len(items),'exact':int(exact),'stop_position':int(stops),'first_word':int(first),'second_word':int(second),'failures':fail}
    return rec,meta,nf

def train():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);gate()
    spec=json.loads((HERE/'PREREGISTRATION.json').read_text());t0=time.perf_counter()
    total=0;raw=[];stats=[];allnf=0
    for seed in SEEDS:
        parent=load_parent(seed)
        for arm in ('control','conjunction'):
            m=copy.deepcopy(parent);assert modelhash(m)==modelhash(parent)
            X,Y=teacher(rows(arm));opt=torch.optim.Adam(m.parameters(),lr=0.003)
            steps=0
            for ep in range(EPOCHS):
                ii=np.random.default_rng(seed+131000+ep).permutation(1408)
                for k in range(0,1408,BATCH):
                    batch=ii[k:k+BATCH]
                    loss=nn.functional.cross_entropy(m(X[batch]),Y[batch]);opt.zero_grad()
                    loss.backward();nn.utils.clip_grad_norm_(m.parameters(),1.0);opt.step();steps+=1
            assert steps==2200;total+=steps
            records,metrics,nf=evaluate(m,seed,arm);allnf+=nf;raw+=records
            save_state(m,seed,arm)
            stats.append({'seed':seed,'arm':arm,'initial_weights_sha256':modelhash(parent),'final_weights_sha256':modelhash(m),'updates':steps,'metrics':metrics})
            print('TRAIN',seed,arm,'heldout a4',metrics['heldout_novel_lower_bits_val_partner']['exact'],'/2','a5',metrics['heldout_novel_lower_bits_test_partner']['exact'],'/2','old',metrics['seen_high_r2']['exact'],'/36',flush=True)
    rawbytes=''.join(json.dumps(x,separators=(',',':'))+'\n' for x in raw).encode()
    (HERE/'raw_cases.jsonl').write_bytes(rawbytes)
    metrics={ (s['seed'],s['arm']):s['metrics'] for s in stats}
    primary=[]
    for seed in SEEDS:
        cn=metrics[(seed,'control')];tr=metrics[(seed,'conjunction')]
        c=cn['heldout_novel_lower_bits_val_partner']['exact']+cn['heldout_novel_lower_bits_test_partner']['exact']
        t=tr['heldout_novel_lower_bits_val_partner']['exact']+tr['heldout_novel_lower_bits_test_partner']['exact']
        primary.append({'seed':seed,'control':c,'conjunction':t,'n':4,'per_seed_gate':t>=3 and c<=1})
    out={'work_id':spec['work_id'],'provenance':'T local CPU PyTorch; parents F PR40 frozen; U user requested; A high conjunction transfer hypothesis',
         'torch':torch.__version__,'numpy':np.__version__,'new_models':4,'parameter_count_each':10499,
         'new_training_updates':total,'new_target_exposures':4*1408*EPOCHS,'train_forward_dense_MAC':4*1408*EPOCHS*MAC,
         'backward_and_optimizer_MAC_excluded':True,'evaluation_forward_calls':allnf,'evaluation_dense_MAC':allnf*MAC,
         'raw_rows':len(raw),'raw_sha256':hashlib.sha256(rawbytes).hexdigest(),'seconds':time.perf_counter()-t0,
         'models':stats,'primary_gate':{'pass':all(x['per_seed_gate'] for x in primary),'pairs':primary},
         'no_claim_of_blind_researcher_split':True,'extra_model_oracle_calls':0}
    (HERE/'RESULTS.json').write_text(json.dumps(out,indent=2)+'\n')
    print('DONE',total,'updates',len(raw),'raw',allnf,'eval-forward','primary',out['primary_gate']['pass'])

if __name__=='__main__':
    if sys.argv[1:]==['gate']:gate()
    elif sys.argv[1:]==['train']:train()
    else:raise SystemExit('usage: python run.py gate|train')
