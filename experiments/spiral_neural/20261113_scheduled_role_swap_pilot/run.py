"""SLE-AE1 role-swap matched pilot. Pure raw-01 student, no teacher oracle in input.
Fixed protocol commit: 8cc0cfe6011300cc0ca54fe2f8900b3c969725db.
"""
import copy, hashlib, json, math, time, base64
from pathlib import Path
import numpy as np
import torch
from torch import nn

OUT=Path(__file__).parent
L,H,EPOCHS,BATCH=80,64,250,64
SEEDS=(101,202)
MODES=('HIGH_FIRST','HIGH_SECOND')

def word(v):
    assert isinstance(v,int) and 0<=v<=29
    return f'{v:05b}0'
def qbits(r,a,b,c=0,d=0):
    assert r in (1,2)
    q='01'+'010'+f'{r:03b}'+'0'+''.join(word(v) for v in (a,b,c,d))+'111100'
    assert len(q)==39 and q.count('S')==0
    return q
def answer(r,a,b): return word(a)+(word(b) if r==2 else '')+'S'
def base_split(a,b):
    x=(a+b)%6
    return 'val' if x==0 else 'test' if x==1 else 'train'
def base_rows(which):
    return [(r,a,b) for a in range(6) for b in range(6) if base_split(a,b)==which for r in (1,2)]
def supp_rows(mode,lo_max=3):
    return [(2,v,s) if mode=='HIGH_FIRST' else (2,s,v)
            for v in range(6,15) for s in range(lo_max+1)]
def high_rows(lo_min,lo_max):
    return {mode:[(2,v,s) if mode=='HIGH_FIRST' else (2,s,v)
      for v in range(6,15) for s in range(lo_min,lo_max+1)] for mode in MODES}
def xvec(s):
    assert s and len(s)<=L and set(s)<={'0','1'}
    z=np.zeros(2*L,dtype=np.float32)
    for i,ch in enumerate(s):z[2*i+int(ch)]=1
    return z
def teacher(cases):
    X=[];y=[]
    for r,a,b in cases:
        q=qbits(r,a,b); ans=answer(r,a,b)
        for j,t in enumerate(ans):
            X.append(xvec(q+ans[:j]));y.append('01S'.index(t))
    return torch.from_numpy(np.stack(X)),torch.tensor(y,dtype=torch.int64)
def network(seed):
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(2*L,H),nn.Tanh(),nn.Linear(H,3))
def weights_sha(m):
    h=hashlib.sha256()
    for k,v in m.state_dict().items():h.update(k.encode());h.update(v.detach().cpu().numpy().tobytes())
    return h.hexdigest()
def checkpoint(m,seed,mode):
    return {'schema':'AE1-ROLE-SWAP-F32-v1','seed':seed,'mode':mode,'weights_sha256':weights_sha(m),
            'tensors':{k:{'shape':list(v.shape),'dtype':'float32',
              'little_endian_base64':base64.b64encode(v.detach().numpy().astype('<f4').tobytes()).decode('ascii')}
              for k,v in m.state_dict().items()}}
@torch.no_grad()
def free(m,q):
    out=''; steps=0
    for _ in range(32):
        if len(q)+len(out)>L:return out,'overflow',steps
        z=m(torch.from_numpy(xvec(q+out)).unsqueeze(0))[0]
        out+='01S'[z.argmax().item()];steps+=1
        if out.endswith('S'):return out,'stop',steps
    return out,'cap',steps

def selftest():
    assert len(base_rows('train'))==48
    assert len(base_rows('val'))==12 and len(base_rows('test'))==12
    assert len(supp_rows('HIGH_FIRST'))==36 and len(supp_rows('HIGH_SECOND'))==36
    assert all(len(v)==18 for v in high_rows(4,5).values())
    assert qbits(2,0,6)=='010100100000000001100000000000000111100', qbits(2,0,6)
    assert qbits(2,6,0)=='010100100001100000000000000000000111100', qbits(2,6,0)
    assert answer(2,0,6)=='000000001100S' and answer(2,6,0)=='001100000000S'
    for mode in MODES:
        X,y=teacher(base_rows('train')+supp_rows(mode))
        assert X.shape==(948,160) and y.shape==(948,)
        assert sum(p.numel() for p in network(101).parameters())==10499
        assert all(qbits(*t).endswith('111100') for t in supp_rows(mode))
    assert {(v,s) for _,v,s in supp_rows('HIGH_FIRST')}=={(v,s) for _,s,v in supp_rows('HIGH_SECOND')}
    print('GATE PASS: Q39 legal, 24/6/6 base, 36+18 new pairs, 948 targets, 10499 parameters, raw examples')

def training():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    selftest()
    results={'protocol_commit':'8cc0cfe6011300cc0ca54fe2f8900b3c969725db',
             'software':{'torch':torch.__version__,'numpy':np.__version__},
             'epochs':EPOCHS,'parameters':10499,'learning_rate':0.003,'seeds':list(SEEDS),
             'models':[],'raw_case_count':0,'total_train_forward_targets':0,'total_optimizer_steps':0}
    samples=[];start=time.perf_counter()
    for seed in SEEDS:
        init=network(seed);init_sha=weights_sha(init)
        permutations=[np.random.default_rng(seed+87000+e).permutation(948) for e in range(EPOCHS)]
        for mode in MODES:
            m=copy.deepcopy(init)
            assert weights_sha(m)==init_sha
            X,y=teacher(base_rows('train')+supp_rows(mode))
            opt=torch.optim.Adam(m.parameters(),lr=.003)
            updates=0;lastloss={}
            for epoch in range(EPOCHS):
                for i in range(0,948,BATCH):
                    ii=permutations[epoch][i:i+BATCH]
                    z=m(X[ii]);loss=nn.functional.cross_entropy(z,y[ii]);opt.zero_grad();loss.backward()
                    nn.utils.clip_grad_norm_(m.parameters(),1.);opt.step();updates+=1
                if epoch+1 in (1,100,250): lastloss[str(epoch+1)]=float(loss.detach())
            assert updates==3750
            chk=checkpoint(m,seed,mode)
            cp=OUT/f'weights_seed{seed}_{mode.lower()}.json'
            cp.write_text(json.dumps(chk,separators=(',',':'))+'\n')
            results['total_train_forward_targets']+=948*EPOCHS
            results['total_optimizer_steps']+=updates
            metrics={}
            sets={'base_train':base_rows('train'), 'base_val':base_rows('val'),'base_test':base_rows('test')}
            for place,arr in high_rows(0,3).items():sets['exposed_'+place]=arr
            for place,arr in high_rows(4,5).items():sets['heldout_'+place]=arr
            for label,queries in sets.items():
                stats={'n':len(queries),'exact':0,'first_word_correct':0,'second_word_correct':0,'stop_correct':0,'bad_cap':0,'forward_calls':0,'high_bit8_generated_second':0}
                for r,a,b in queries:
                    Q=qbits(r,a,b);exp=answer(r,a,b);got,why,nf=free(m,Q)
                    item={'seed':seed,'arm':mode,'split':label,'r':r,'a':a,'b':b,'c':0,'d':0,'Q':Q,'expected':exp,'actual':got,'cause':why}
                    samples.append(item)
                    stats['n']+=0;stats['exact']+=got==exp
                    stats['first_word_correct']+=got[:6]==word(a)
                    stats['second_word_correct']+=r==2 and got[6:12]==word(b)
                    stats['stop_correct']+=got.endswith('S') and len(got)==len(exp)
                    stats['bad_cap']+=why!='stop';stats['forward_calls']+=nf
                    stats['high_bit8_generated_second']+=r==2 and len(got)>=12 and got[7]=='1'
                metrics[label]=stats
            results['models'].append({'seed':seed,'arm':mode,'init_sha256':init_sha,'final_sha256':weights_sha(m),'updates':updates,
                   'target_exposures':948*EPOCHS,'loss_anchor':lastloss,'metrics':metrics,'checkpoint_path':cp.name})
            print('MODEL',seed,mode,'time',round(time.perf_counter()-start,1),'heldout-second',metrics['heldout_HIGH_SECOND']['exact'],'/18',
                'inrole',metrics['exposed_'+mode]['exact'],'/36',flush=True)
    results['raw_case_count']=len(samples)
    results['evaluation_forward_calls']=sum(stats['forward_calls'] for m in results['models'] for stats in m['metrics'].values())
    results['evaluation_dense_forward_mac']=results['evaluation_forward_calls']*10432
    results['training_dense_forward_mac']=results['total_train_forward_targets']*10432
    results['training_backward_mac_not_counted']=True
    results['wall_seconds']=time.perf_counter()-start
    rawpath=OUT/'raw_cases.jsonl';rawpath.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in samples))
    results['raw_sha256']=hashlib.sha256(rawpath.read_bytes()).hexdigest()
    (OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('RESULT',results['raw_case_count'],'cases',results['total_optimizer_steps'],'steps',results['evaluation_forward_calls'],'eval forwards','elapsed',round(results['wall_seconds'],1),flush=True)

if __name__=='__main__':
    import sys
    if len(sys.argv)==2 and sys.argv[1]=='selftest':selftest()
    elif len(sys.argv)==2 and sys.argv[1]=='train':training()
    else:raise SystemExit('usage: python run.py {selftest|train}')
