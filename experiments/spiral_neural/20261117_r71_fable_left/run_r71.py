#!/usr/bin/env python3
"""R71 Fable151 paired A handfill / B trained / C random H110 LEFT.
Original Fable code/weights stay private; this runner only references locally verified external inputs.
No inference-time parser or teacher substitution. Prepared under frozen Git prereg a380e132.
"""
from __future__ import annotations
import argparse, json, hashlib, os, sys, time
from pathlib import Path
import numpy as np

FIELDS=('W1','b1','Wo','bo')
END=[1,1,1,1,1,1,0,0]
MIX=(('REVERSE4',12),('REVERSE3',4),('REVERSE2',4),('COPY4',4),('COPY3',2),('COPY2',2),('DIRTY-COPY1',2),('CLEAN-COPY1',1),('PUNCT',1))
SEEDS=(101,202,303)
CHECKS=(0,128,256,512,1024,2048,4096)
PROVENANCE={'hand.py':'166ef00fce69386f89a1f832785a77e2fb465b3831c5d78854ac85083deceed8',
 'compiler.py':'bf6e9e84d6b2ddc2462b586fd25c5cb8a2f4fc913bc7803655ccf39591d085ab',
 'filltrain.py':'a5e6c4eaf5ff4d1e8d8ad7bdf1da0ceb42c291629cddf79adc820a286bea9b1c',
 'handfilled_H86_9families.npz':'97d671b42f735bea818878652a4d209e4dcfec3037049327dcb6014095e4e523'}

def hashbytes(b):return hashlib.sha256(b).hexdigest()
def hfile(p):return hashbytes(p.read_bytes())
def serial_bits(a):return ''.join(str(int(v)) for v in a)
def sigmoid(z):
    e=np.exp(-np.abs(z));return np.where(z>=0,1/(1+e),e/(1+e))
def forward(p,x):return np.tanh(x@p['W1']+p['b1'])@p['Wo']+p['bo']
def paramcount(p):return int(sum(v.size for v in p.values()))
def params_from_npz(d):return {k:d['p_'+k].copy() for k in FIELDS}

def rand_unique(S,rng,count,n):
    S=np.asarray(S,dtype=np.int64);idx=rng.integers(0,len(S),(count,n))
    for _ in range(100):
        invalid=np.array([len(set(row))<n for row in idx])
        if not invalid.any():return S[idx]
        idx[invalid]=rng.integers(0,len(S),(int(invalid.sum()),n))
    raise AssertionError('unique sampling failed')

def spec(n,op):
    if op==0:return list(range(n))
    if op==3:return list(range(n))[::-1]
    if op==1:return list(range(1,n))+[0]
    raise ValueError(op)

def make_case(hand,compiler,op,vals):
    vals=np.asarray(vals,dtype=int);n=vals.shape[1]
    x,y,m=compiler.qa(op,vals,{(op,n):spec(n,op)},remaining=3)
    orig_x=hand.build(op,vals)[0]
    assert np.array_equal(x,orig_x),('Fable compiler vs hand input mismatch',op,n)
    assert x.shape==(len(vals),151) and y.shape==(len(vals),40)
    assert np.all(m[:,8*n:8*n+8]==1)
    return x,y,m

def paired_panel(hand,compiler,S,seed):
    rng=np.random.default_rng(seed);records=[];matrix=[];pairkeys=[]
    for n in (3,4):
        used=set();vals=[]
        while len(vals)<48:
            row=tuple(map(int,rand_unique(S,rng,1,n)[0]))
            key=tuple(sorted(row))
            if key in used:continue
            used.add(key);vals.append(row)
        a=np.array(vals,int)
        assert len(set(map(tuple,a)))==48
        for op in (0,3,1):
            x,y,m=make_case(hand,compiler,op,a)
            for i,row in enumerate(vals):
                records.append({'n':n,'paired_id':f'{n}-{i:03d}','op':op,'payload':list(row),
                  'raw_input_151':serial_bits(x[i]),'gold_40':serial_bits(y[i]),
                  'mask_40':serial_bits(m[i]),'submit':1})
            matrix.append({'n':n,'op':op,'vals':a,'x':x,'y':y,'m':m})
    # each (n,id) must have three distinct answers and exactly one ECHO/REV/LEFT version
    for n in (3,4):
        for i in range(48):
            x=[r for r in records if r['paired_id']==f'{n}-{i:03d}']
            assert len(x)==3 and len(set(r['gold_40'] for r in x))==3
            assert len(set(x[0]['payload'][j] for j in range(n)))==n
    # coverage of EACH of seven bits per position (MSB first) separately for 3/4 word cases
    coverage={}
    for n in (3,4):
        rows=[r['payload'] for r in records if r['n']==n and r['op']==1]
        coverage[str(n)]={str(pos):{'bit'+str(b):sorted({int((v[pos]>>(6-b))&1) for v in rows}) for b in range(7)} for pos in range(n)}
        assert all(states==[0,1] for pos in coverage[str(n)].values() for states in pos.values()),('coverage failure',n)
    return records,matrix,coverage

def eval_pair(p,panel,write_fail=None):
    data={};per_id={};bad=[]
    for grp in panel:
        n,op,x,y,m,vals=grp['n'],grp['op'],grp['x'],grp['y'],grp['m'],grp['vals']
        pred=forward(p,x)>0
        exact=((((pred[:,:40]==y)|(m==0)).all(1))&pred[:,40])
        ok_frame=np.array([bool(pred[i,40]) and all(not pred[i,8*j+7] for j in range(n)) and
            np.array_equal(pred[i,8*n:8*n+8],END) for i in range(len(x))],bool)
        wrong_echo=wrong_rev=wrong_other=invalid=0
        for i,row in enumerate(vals):
            pair_id=f'{n}-{i:03d}'
            per_id.setdefault(pair_id,{})[op]=bool(exact[i])
            if exact[i]:continue
            if not ok_frame[i]:invalid+=1
            else:
                decoded=tuple(int(''.join(str(int(z)) for z in pred[i,8*j:8*j+7]),2) for j in range(n))
                orig=tuple(map(int,row));v_echo=orig;v_rev=orig[::-1];v_left=orig[1:]+orig[:1]
                if op==1 and decoded==v_echo:wrong_echo+=1
                elif op==1 and decoded==v_rev:wrong_rev+=1
                else:wrong_other+=1
            if write_fail is not None:
                bad.append({'n':n,'paired_id':pair_id,'op':op,'payload':list(map(int,row)),
                 'raw_input_151':serial_bits(x[i]),'gold_40':serial_bits(y[i]),
                 'mask_40':serial_bits(m[i]),'prediction_41':serial_bits(pred[i]),'valid_frame':bool(ok_frame[i])})
        data[f'{op}/{n}']={'correct':int(exact.sum()),'total':len(x),'frame_valid':int(ok_frame.sum()),
            'wrong_as_echo':wrong_echo,'wrong_as_rev':wrong_rev,'wrong_other':wrong_other,'frame_invalid':invalid}
    triad=sum(all(v.get(op,False) for op in (0,3,1)) for v in per_id.values())
    leftc=sum(data[f'1/{n}']['correct'] for n in (3,4))
    ret={'per_operator_n':data,'triad_success':triad,'triad_total':len(per_id),'left_exact':leftc,
         'left_total':96,'left_ge95':leftc>=92,'left_each_n_ge95':all(data[f'1/{n}']['correct']>=46 for n in (3,4))}
    if write_fail is not None:
        write_fail.parent.mkdir(parents=True,exist_ok=True)
        with write_fail.open('w') as f:
            for v in bad:f.write(json.dumps(v,separators=(',',':'))+'\n')
    return ret

def score_old(p,panel):
    res={}
    for fam,x,y,m in panel:
        z=forward(p,x);a=((((z[:,:40]>0)==y)|(m==0)).all(1)&(z[:,40]>0))
        res[fam]={'correct':int(a.sum()),'total':len(a),'pct':100*float(a.mean())}
    return res

def new_batch(hand,compiler,TR,rng):
    X=[];Y=[];M=[];payloads=[]
    for n in (3,4):
        vals=rand_unique(TR,rng,16,n);x,y,m=make_case(hand,compiler,1,vals)
        X.append(x);Y.append(y);M.append(m)
        payloads.extend([(n,)+tuple(map(int,row)) for row in vals])
    for fam,c in MIX:
        x,y,m=hand.sample(fam,TR,rng,c)
        if len(x)!=c:assert len(x)==1; x=np.repeat(x,c,0);y=np.repeat(y,c,0);m=np.repeat(m,c,0)
        X.append(x);Y.append(y);M.append(m)
    x=np.vstack(X);y=np.vstack(Y);m=np.vstack(M)
    assert x.shape==(64,151) and y.shape==(64,40) and m.shape==(64,40)
    return x,y,m,payloads

def gradient(p,x,y,m):
    target=np.hstack([y,np.ones((len(y),1))]);mask=np.hstack([m,np.ones((len(y),1))]);
    h=np.tanh(x@p['W1']+p['b1']);z=h@p['Wo']+p['bo'];w=np.zeros_like(mask)
    w[:,:40]=mask[:,:40]/mask[:,:40].sum();w[:,40]=.25/len(y)
    dz=(sigmoid(z)-target)*w;dh=(dz@p['Wo'].T)*(1-h*h)
    return {'W1':x.T@dh,'b1':dh.sum(0),'Wo':h.T@dz,'bo':dz.sum(0)}

def adamstep(p,g,m,v,t):
    nm=np.sqrt(sum((ar*ar).sum() for ar in g.values()));sc=min(1.,1/max(nm,1e-12))
    for k in FIELDS:
        grad=g[k]*sc;m[k]=.9*m[k]+.1*grad;v[k]=.999*v[k]+.001*(grad**2)
        p[k]-=.003*(m[k]/(1-.9**t))/(np.sqrt(v[k]/(1-.999**t))+1e-8)

def write_ck(path,p,m,v,step,seed,group,rng):
    np.savez_compressed(path,**{'p_'+k:val for k,val in p.items()},
        **{'m_'+k:val for k,val in m.items()},**{'v_'+k:val for k,val in v.items()},
        meta=np.array(json.dumps({'run':'R71','seed':seed,'group':group,'step':step,'rng':rng.bit_generator.state},sort_keys=True)))

def init_group(group,seed,fable,R70):
    g=np.random.default_rng(770000+seed)
    # COMMON A/B new neurons (same even if group order varies).
    w_new=g.normal(0,1/np.sqrt(151),(151,24));
    if group=='A':
        orig=np.load(fable/'handfilled_H86_9families.npz',allow_pickle=False);base=params_from_npz(orig)
    elif group=='B':
        orig=np.load(R70/f'r70_results/B_seed{seed}_step8192.npz',allow_pickle=False)
        assert json.loads(str(orig['meta']))['step']==8192
        base=params_from_npz(orig)
    elif group=='C':
        rng=np.random.default_rng(780000+seed)
        return {'W1':rng.normal(0,1/np.sqrt(151),(151,110)), 'b1':np.zeros(110),
         'Wo':rng.normal(0,1/np.sqrt(110),(110,41)),'bo':np.zeros(41)},None
    else:raise ValueError(group)
    before={k:v.copy() for k,v in base.items()}
    p={'W1':np.hstack((base['W1'],w_new)), 'b1':np.concatenate((base['b1'],np.zeros(24))),
       'Wo':np.vstack((base['Wo'],np.zeros((24,41)))),'bo':base['bo'].copy()}
    return p,before

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fable-dir',required=True);ap.add_argument('--r70-dir',required=True);ap.add_argument('--out',required=True);ap.add_argument('--max-updates',type=int,default=4096);ap.add_argument('--seed',type=int,choices=SEEDS);ap.add_argument('--group',choices=('A','B','C'));ap.add_argument('--finalize-only',action='store_true')
    args=ap.parse_args();assert args.max_updates==4096,'prereg budget is exactly 4096'
    fable=Path(args.fable_dir);r70=Path(args.r70_dir);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    assert {k:hfile(fable/k) for k in PROVENANCE}==PROVENANCE,'source sha mismatch'
    sys.path.insert(0,str(fable));import hand,compiler
    sys.path.insert(0,str(r70));import run_r69 as r69
    TR,VA,TE=hand.sets(2603)
    assert (len(TR),len(VA),len(TE))==(96,16,16)
    assert not(set(TR)&set(VA) or set(TR)&set(TE) or set(VA)&set(TE))
    valrec,val,vcov=paired_panel(hand,compiler,VA,7113)
    testrec,test,tcov=paired_panel(hand,compiler,TE,7114)
    oldrecords,oldval=r69.build_panel(hand,VA,9911,256)
    assert oldrecords==[json.loads(x) for x in (r70/'results/validation_raw.jsonl').read_text().splitlines()]
    for name,records in [('val_paired_raw.jsonl',valrec),('test_paired_raw.jsonl',testrec)]:
        with (out/name).open('w') as f:
            for row in records:f.write(json.dumps(row,separators=(',',':'))+'\n')
    (out/'source_splits.json').write_text(json.dumps({'TR':list(map(int,TR)),'VA':list(map(int,VA)),'TE':list(map(int,TE))},indent=2))
    output={'work_id':'R71_FABLE_H110_LEFT_AB_C','frozen_git_prereg_commit':'a380e132ae2f7d21ff0724de34d8ead20bb20ab6',
      'source_sha':PROVENANCE,'profile':'Fable151 experimental, not normative SLE-AE1','split':{'TR':len(TR),'VA':len(VA),'TE':len(TE)},
      'val_panel_sha256':hfile(out/'val_paired_raw.jsonl'),'test_panel_sha256':hfile(out/'test_paired_raw.jsonl'),
      'val_coverage':vcov,'test_coverage':tcov,'seeds':SEEDS,'updates':4096,'batch_size':64,
      'left_per_batch':32,'params':21271,'forward_mac':21120,'B_old_skill_pretrain_updates':8192,
      'B_old_skill_pretrain_presentations':8192*64,'test_used_for_selection':False,'groups':{},'diagnostics':{},'checkpoint_schedule':CHECKS}
    for seed in (() if args.finalize_only else (args.seed,)):
        paired_first=None;first_hash=None
        for group in (args.group,):
            p,before=init_group(group,seed,fable,r70)
            assert paramcount(p)==21271 and p['W1'].shape==(151,110)
            rng=np.random.default_rng(720000+seed)
            m={k:np.zeros_like(a) for k,a in p.items()};v={k:np.zeros_like(a) for k,a in p.items()}
            before_x=np.array([np.fromiter((int(a) for a in s['raw_input_151']),dtype=np.float64) for s in valrec[:24]])
            logits_diff=None
            if before is not None:
                logits_diff=float(np.max(np.abs(forward(before,before_x)-forward(p,before_x))))
                assert logits_diff==0,'growth did not preserve logits'
            baseline_old=score_old(p,oldval);elig=all(q['pct']>=95 for q in baseline_old.values())
            assert elig if group!='C' else True,'A/B legacy eligibility failed'
            entry={'seed':seed,'group':group,'old_init_eligible':elig,'max_zero_growth_logit_diff':logits_diff,
                   'checkpoint_metrics':[],'train_hash':None,'new_grad_and_step_diagnostics':[],
                   'B_pretrain_updates':8192 if group=='B' else 0,'A_handfill_time':'unmeasured human' if group=='A' else None}
            digest=hashlib.sha256();seen_left=set();tstart=time.perf_counter()
            for t in range(0,4097):
                if t in CHECKS:
                    ev=eval_pair(p,val)
                    old=score_old(p,oldval)
                    kept=all(q['pct']>=95 and q['pct']>=baseline_old[fam]['pct']-5 for fam,q in old.items())
                    (out/'checkpoints').mkdir(exist_ok=True)
                    ckname=f'{group}_seed{seed}_step{t}.npz';write_ck(out/'checkpoints'/ckname,p,m,v,t,seed,group,rng)
                    entry['checkpoint_metrics'].append({'step':t,'full_presentations':64*t,'left_presentations':32*t,
                     'distinct_ordered_left_payloads':len(seen_left),'left_val':ev,'old_val':old,'old_retained':kept,'checkpoint':ckname})
                if t==4096:break
                x,y,mask,payloads=new_batch(hand,compiler,TR,rng)
                for row in payloads:seen_left.add(row)
                digest.update(x.astype(np.uint8).tobytes());digest.update(y.astype(np.uint8).tobytes());digest.update(mask.astype(np.uint8).tobytes())
                if t==0:
                    fh=hashbytes(x.astype(np.uint8).tobytes()+y.astype(np.uint8).tobytes()+mask.astype(np.uint8).tobytes())
                    if paired_first is None:
                        paired_first=(x.copy(),y.copy(),mask.copy())
                        first_hash=fh
                        with (out/f'first_batch_seed{seed}.jsonl').open('w') as f:
                            for j in range(64):f.write(json.dumps({'i':j,'raw_input_151':serial_bits(x[j]),'gold_40':serial_bits(y[j]),'mask_40':serial_bits(mask[j]),'submit':1},separators=(',',':'))+'\n')
                    else:
                        assert fh==first_hash and all(np.array_equal(aa,bb) for aa,bb in zip((x,y,mask),paired_first))
                gr=gradient(p,x,y,mask)
                report=None
                if t<2:
                    report={'update_before':t,'gradient_norm_new_W1':float(np.linalg.norm(gr['W1'][:,86:])),
                        'gradient_norm_new_b1':float(np.linalg.norm(gr['b1'][86:])),
                        'gradient_norm_new_Wo':float(np.linalg.norm(gr['Wo'][86:,:]))}
                    snapshot={k:arr.copy() for k,arr in p.items()}
                adamstep(p,gr,m,v,t+1)
                if t<2:
                    report.update({'delta_norm_new_W1':float(np.linalg.norm(p['W1'][:,86:]-snapshot['W1'][:,86:])),
                        'delta_norm_new_b1':float(np.linalg.norm(p['b1'][86:]-snapshot['b1'][86:])),
                        'delta_norm_new_Wo':float(np.linalg.norm(p['Wo'][86:,:]-snapshot['Wo'][86:,:])),
                        'old_W1_changed':bool(np.any(p['W1'][:,:86]!=snapshot['W1'][:,:86]))})
                    entry['new_grad_and_step_diagnostics'].append(report)
            entry['train_stream_sha256']=digest.hexdigest();entry['seconds']=time.perf_counter()-tstart
            entry['first_observed_left95']=next((i['step'] for i in entry['checkpoint_metrics'] if i['left_val']['left_ge95']),None)
            entry['first_observed_both_left95_and_old_retained']=next((i['step'] for i in entry['checkpoint_metrics'] if i['left_val']['left_ge95'] and i['old_retained']),None)
            output['groups'][f'{group}{seed}']=entry
            print('DONE',group,seed,'secs',round(entry['seconds'],1),'LEFT',[(a['step'],a['left_val']['left_exact'],a['old_retained']) for a in entry['checkpoint_metrics']],flush=True)
        # Check paired A/B new unit source for given seed is same.
        xa,_=init_group('A',seed,fable,r70);xb,_=init_group('B',seed,fable,r70)
        assert np.array_equal(xa['W1'][:,86:],xb['W1'][:,86:]) and np.array_equal(xa['Wo'][86:,:],xb['Wo'][86:,:])
    if not args.finalize_only:
        (out/f'{args.group}{args.seed}_partial.json').write_text(json.dumps(output['groups'],ensure_ascii=False,indent=2))
        print('GROUP_PARTIAL_SAVED',args.group,args.seed,flush=True)
        return
    for seed in SEEDS:
        for group in ('A','B','C'):
            partial=out/f'{group}{seed}_partial.json'
            assert partial.exists(),f'missing {group} seed {seed} results'
            output['groups'].update(json.loads(partial.read_text()))
    # AFTER all training only: final evaluation of frozen test exactly once per student. No checkpoint selection by test.
    for seed in SEEDS:
        for group in ('A','B','C'):
            entry=output['groups'][f'{group}{seed}']
            d=np.load(out/'checkpoints'/f'{group}_seed{seed}_step4096.npz',allow_pickle=False)
            p=params_from_npz(d)
            entry['final_test']=eval_pair(p,test,out/'failures'/f'{group}_seed{seed}_test_failures.jsonl')
            ev=eval_pair(p,val,out/'failures'/f'{group}_seed{seed}_val_failures.jsonl')
            assert entry['checkpoint_metrics'][-1]['left_val']==ev,'postrun validation replay mismatch'
    output['all_completed']=True
    (out/'RESULTS.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print('RUN_COMPLETE result',out/'RESULTS.json',flush=True)
if __name__=='__main__':main()