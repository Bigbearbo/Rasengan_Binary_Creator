"""AE1 legal-bit matched suffix-exposure NN control (independent small diagnostic).
No Codex/Pro checkpoint, no external oracle in student. Requires torch, numpy.
"""
import argparse, copy, hashlib, json, math, time
from pathlib import Path
import numpy as np
import torch
from torch import nn

BASE = Path(__file__).resolve().parent
SEEDS=(101,202)
EPOCHS=200
BATCH=64
LR=.003
L,H=80,64
STOP='S'
MODES=('fixed','varied')

def sh(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def word(v):
    assert 0<=v<30
    return f'{v:05b}0'
def qbits(r,a,b,c,d):
    assert r in (1,2)
    return '01'+'010'+f'{r:03b}'+'0'+''.join(word(v) for v in (a,b,c,d))+'111100'
def answer(r,a,b):return (word(a) if r==1 else word(a)+word(b))+'S'
def split(a,b):return ('val' if (a+b)%6==0 else 'test' if (a+b)%6==1 else 'train')
def suffix(a,b,epoch=0,mode='fixed'):
    c=(7*a+3*b)%15;d=(5*a+11*b)%15
    if mode=='varied': c=(c+epoch)%15;d=(d+7*epoch)%15
    return c,d
def eval_suffix(a,b,mode):
    c,d=suffix(a,b)
    if mode=='seen':return c,d
    if mode=='changed_low':return (c+8)%15,(d+9)%15
    if mode=='unseen_high':return c+15,d+15
    raise KeyError(mode)
def rows(which,epoch=0,mode='fixed',suffix_mode='seen'):
    out=[]
    for a in range(6):
      for b in range(6):
        if split(a,b)!=which:continue
        c,d=(suffix(a,b,epoch,mode) if which=='train' else eval_suffix(a,b,suffix_mode))
        for r in (1,2):out.append((qbits(r,a,b,c,d),answer(r,a,b),a,b,r,c,d))
    return out

def xvec(text):
    assert len(text)<=L and text and set(text)<={'0','1'}
    x=np.zeros(2*L,np.float32)
    for i,ch in enumerate(text):x[2*i+int(ch)]=1
    return x

def teacher(rows_):
    contexts=[];targets=[]
    for q,answer_,*rest in rows_:
        for j,target in enumerate(answer_):
            contexts.append(xvec(q+answer_[:j]));targets.append('01S'.index(target))
    return torch.from_numpy(np.stack(contexts)),torch.tensor(targets,dtype=torch.long)

def network(seed):
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(2*L,H),nn.Tanh(),nn.Linear(H,3))

def weights_sha(m):
    h=hashlib.sha256()
    for k,v in m.state_dict().items():h.update(k.encode());h.update(v.detach().numpy().tobytes())
    return h.hexdigest()

@torch.no_grad()
def run_free(model,q):
    output=''
    for _ in range(32):
        if len(q)+len(output)>L:return output,'overflow'
        z=model(torch.from_numpy(xvec(q+output)).unsqueeze(0))[0]
        token='01S'[int(z.argmax())];output+=token
        if token=='S':return output,'stop'
    return output,'cap'

@torch.no_grad()
def measure(model,which,suffix_mode):
    data=rows(which,suffix_mode=suffix_mode)
    by_r={}
    for r in (1,2):
      items=[v for v in data if v[4]==r]
      exact=0;stop=0;bits=0;totalbits=0;first=[];examples=[];preds=[]
      for q,expect,a,b,rr,c,d in items:
          produced,why=run_free(model,q)
          preds.append([a,b,c,d,r,produced]);exact+=produced==expect
          stop+=produced.endswith('S') and len(produced)==len(expect)
          for j,bit in enumerate(expect[:-1]):
              bits+=j<len(produced) and produced[j]==bit
          totalbits+=len(expect)-1
          if produced!=expect and len(examples)<3:examples.append({'Q':q,'expected':expect,'actual':produced,'cause':why})
      by_r[str(r)]={'exact':exact,'n':len(items),'stop_position':stop,'bits_correct':bits,'bits_total':totalbits,'failed_examples':examples,'predictions':preds}
    return by_r

def prepare():
    cases=[{'a':a,'b':b,'split':split(a,b),'suffix_fixed':list(suffix(a,b))} for a in range(6) for b in range(6)]
    schedule={str(seed):[np.random.default_rng(seed+41000+e).permutation(480).tolist() for e in range(EPOCHS)] for seed in SEEDS}
    # schedule JSON large; retain only deterministic RNG formula and exact digest.
    manifest={'id':'AE1-NUISANCE-SUFFIX-EXPOSURE-20261113','source':'Codex AE1 PR26 head 7213cce112a8411b13dc128c49f9e88acfc9d65f; independent model implementation',
      'single_variable':'training suffix exposure: fixed third/fourth words per first-two pair versus epoch-varying (both answer-irrelevant)',
      'profile':'SLE-AE1-n5-v1: raw 01+010+r(3 information bits+0)+4*(5 info+0)+END111100; r in {1,2}; answer prefix complete words then external STOP',
      'data':{'first_two_vocabulary':list(range(6)),'train_pairs':24,'val_pairs':6,'test_pairs':6,'split_rule':'(a+b)%6: val0,test1,other train',
              'suffix_fixed':'c=(7a+3b)%15,d=(5a+11b)%15','suffix_varied':'c=(c0+epoch)%15,d=(d0+7epoch)%15; epoch0 fixed',
              'eval_variants':{'seen':'(c0,d0)','changed_low':'((c0+8)%15,(d0+9)%15)','unseen_high':'(15+c0,15+d0)'},
              'cases':cases,'example_raw':{'Q_r1':qbits(1,0,0,*suffix(0,0)),'Q_r2':qbits(2,0,0,*suffix(0,0)),'A_r1':answer(1,0,0),'A_r2':answer(2,0,0)}},
      'network':{'architecture':'one-hot slots (zero/one; pad all zeros) -> tanh FC (160,64) -> 3 logits [0,1,S]','L':80,'H':64,'parameters':10499,'optimizer':'torch Adam(lr=.003) batched CE, global gradient clip1; differs from original P030 sequential per-target optimizer','initial_seeds':list(SEEDS)},
      'frozen_budget':{'epochs':EPOCHS,'batch_size':BATCH,'teacher_targets_per_epoch':24*(7+13),'optimizer_steps_per_model':EPOCHS*math.ceil(480/BATCH),'total_model_runs':len(SEEDS)*len(MODES),'no_early_stop':True,'train_MAC_per_target_reference_approx':21056,'val_test_during_training':False},
      'acceptance':'Report all four models and all three suffix conditions for train/val/test separately, actual optimizer steps, bit/full/STOP correctness and failures. No hyperparameter retuning or claimed transfer of Pro/Codex checkpoints. Differences do not prove general SLE advantages.'}
    manifest['schedule_sha256_by_seed']={str(s):sh(canonical(schedule[str(s)]).encode()) for s in SEEDS}
    Path('/mnt/data/sle_ae1_suffix_prereg.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print('PREPARED',sh(Path('/mnt/data/sle_ae1_suffix_prereg.json').read_bytes()),{k:sum(c['split']==k for c in cases) for k in ('train','val','test')})

def selftest():
    assert len(rows('train'))==48 and len(rows('val'))==12 and len(rows('test'))==12
    assert sum(split(a,b)=='train' for a in range(6) for b in range(6))==24
    for r in (1,2):
        q=qbits(r,0,2,17,29);assert len(q)==39 and q.startswith('01010') and q.endswith('111100')
        assert len(answer(r,0,2))==6*r+1
        assert q[:9]=='01010'+f'{r:03b}'+'0'
    for e in range(200):
        for a in range(6):
            for b in range(6):
                assert suffix(a,b,e,'varied')==suffix(a,b,e,'varied')
                for r in (1,2):
                    assert answer(r,a,b)==answer(r,a,b)
    x,y=teacher(rows('train'));assert x.shape==(480,160) and len(y)==480
    assert network(101)[0].in_features==160 and sum(p.numel() for p in network(101).parameters())==10499
    print('PASS selftest: legal Q bits, split, deterministic suffix, teacher targets, 10499 parameters')

def train():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    frozen=Path('/mnt/data/sle_ae1_suffix_prereg.json').read_bytes()
    manifest=json.loads(frozen)
    assert manifest['id']=='AE1-NUISANCE-SUFFIX-EXPOSURE-20261113'
    report={'protocol_sha256':sh(frozen),'source_sha256':sh(Path(__file__).read_bytes()),'environment':{'torch':torch.__version__,'numpy':np.__version__},'per_model':[]}
    start=time.perf_counter()
    for seed in SEEDS:
      init=network(seed);init_sha=weights_sha(init)
      permutations=[np.random.default_rng(seed+41000+e).permutation(480) for e in range(EPOCHS)]
      assert sh(canonical([x.tolist() for x in permutations]).encode())==manifest['schedule_sha256_by_seed'][str(seed)]
      for mode in MODES:
        net=copy.deepcopy(init);assert weights_sha(net)==init_sha
        opt=torch.optim.Adam(net.parameters(),lr=LR)
        updates=0;firstlast=[]
        for epoch in range(EPOCHS):
          X,y=teacher(rows('train',epoch,mode))
          perm=permutations[epoch]
          for offset in range(0,len(y),BATCH):
            ids=perm[offset:offset+BATCH];z=net(X[ids]);loss=nn.functional.cross_entropy(z,y[ids]);
            opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(net.parameters(),1.0);opt.step();updates+=1
          if epoch in (0,99,199):firstlast.append({'epoch':epoch+1,'last_minibatch_loss':float(loss.detach())})
        assert updates==EPOCHS*math.ceil(480/BATCH)
        result={'seed':seed,'mode':mode,'initial_sha256':init_sha,'final_weights_sha256':weights_sha(net),'optimizer_steps':updates,'training_target_exposures':480*EPOCHS,'loss_anchors':firstlast,'evaluation':{}}
        for which in ('train','val','test'):
          result['evaluation'][which]={suffix_mode:measure(net,which,suffix_mode) for suffix_mode in ('seen','changed_low','unseen_high')}
        report['per_model'].append(result)
        print('MODEL',seed,mode,'elapsed',round(time.perf_counter()-start,2),'train/seen',sum(result['evaluation']['train']['seen'][str(r)]['exact'] for r in (1,2)),'train/high',sum(result['evaluation']['train']['unseen_high'][str(r)]['exact'] for r in (1,2)),flush=True)
    report['wall_seconds']=time.perf_counter()-start
    # Keep every failure example, avoid publishing huge predictions file if not needed (all 3 variants x 36 x 2 x4).
    target=Path('/mnt/data/sle_ae1_suffix_results.json');target.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
    print('RESULT',target,sh(target.read_bytes()),round(report['wall_seconds'],2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('selftest','prepare','train'));mode=p.parse_args().command
    if mode=='selftest':selftest()
    elif mode=='prepare':prepare()
    else:train()
