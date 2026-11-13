"""Fixed-checkpoint AE1 novel-word role swap. No optimizer or new student.
Source WordStudent is the byte-frozen prior experiment; only inputs are raw 01.
Pass 1: gate (static). Pass 2: probe (Torch free+teacher-forced diagnostics).
"""
from pathlib import Path
import sys, json, hashlib, base64, collections
import numpy as np
import torch
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'source'))
import run as prior
S=P/'source'
J=(6,7,10,11,12,13,14)
H=(18,19)
SEEDS=(101,202,303)
ARMS=('tied','untied')
MAC=10920

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cases():
    for j in J:
        for h in H:
            split='diagnostic_val' if j in (6,7) else 'diagnostic_test'
            for role,a,b in [('first',j,h),('second',h,j)]:
                yield {'split':split,'role':role,'j':j,'h':h,'r':2,'a':a,'b':b,'c':0,'d':1,'Q':prior.question(2,a,b,0,1),'expected':prior.answer(2,a,b)}

def get_state(seed,arm):
    path=S/'checkpoints'/f'weights_{seed}_{arm}.json'
    report=json.loads((S/'results.json').read_text())
    block=next(z for z in report['blocks'] if z['seed']==seed and z['arm']==arm)
    assert digest(path)==block['checkpoint_sha256'],('source state',seed,arm)
    item=json.loads(path.read_text())
    model=prior.WordStudent(arm=='tied')
    state={}
    for key,val in item['tensors'].items():
        arr=np.frombuffer(base64.b64decode(val['little_endian_base64']),dtype='<f4').reshape(val['shape']).copy()
        state[key]=torch.from_numpy(arr)
    model.load_state_dict(state,strict=True)
    model.eval()
    assert sum(p.numel() for p in model.parameters())==(10457 if arm=='tied' else 11081)
    return model

def gate():
    spec=json.loads((P/'prereg.json').read_text())
    assert spec['source_zip_sha256']=='53f6e312f30570ef7d458f35b25c17b49eb7b161415bb5d3b165645aeb8f10a0'
    assert spec['probe_sha256']==digest(P/'probe.py')
    assert spec['case_manifest_sha256']==digest(P/'cases.jsonl')
    assert spec['source_runner_sha256']==digest(S/'run.py')
    assert spec['source_results_sha256']==digest(S/'results.json')
    expected=[json.loads(x) for x in (P/'cases.jsonl').read_text().splitlines()]
    assert expected==list(cases()) and len(expected)==28 and len({z['Q'] for z in expected})==28
    assert all(len(z['Q'])==39 and len(z['expected'])==13 for z in expected)
    assert all(z['Q'].startswith('01010') and z['Q'].endswith('111100') for z in expected)
    assert not set(J)&set(v for row in prior.course() for v in row[1:])
    archived=[json.loads(z) for z in (S/'raw_cases.jsonl').read_text().splitlines()]
    assert len(archived)==936 and digest(S/'raw_cases.jsonl')==json.loads((S/'results.json').read_text())['raw_sha256']
    look={(z['seed'],z['arm'],z['Q']):z for z in archived}
    for seed in SEEDS:
        for arm in ARMS:
            for row in expected:
                if row['role']=='first':
                    old=look[(seed,arm,row['Q'])]
                    assert old['split']=='test_new_first' and old['expected']==row['expected']
    print('STATIC-GATE PASS: 28 native Q, 14 role pairs, 6 authentic F32 states, prior first-role raw reuse; 0 forward',flush=True)
    return expected,look

def teacher(m,q,expected):
    checks=[];margins=[]
    for i,target in enumerate(expected):
        with torch.no_grad():
            logits=m(torch.from_numpy(prior.xvec(q+expected[:i])).unsqueeze(0))[0]
        vec=logits.numpy().astype(float)
        pred='01S'[int(vec.argmax())]
        checks.append(pred==target)
        margins.append(round(float(vec['01S'.index(target)]-max(vec[k] for k in range(3) if k!='01S'.index(target))),7))
    return checks,margins

def experiment():
    torch.set_num_threads(1)
    manifest,look=gate()
    raw=[];counts=collections.defaultdict(lambda:dict(n=0,exact=0,first_word=0,second_word=0,stop=0,tf_first=0,tf_second=0))
    forward=0;new_forward=0
    for seed in SEEDS:
      for arm in ARMS:
        m=get_state(seed,arm)
        for row in manifest:
            key=(seed,arm,row['Q']); expected=row['expected']
            if row['role']=='first':
                old=look[key];actual=old['actual'];cause=old['cause'];n=old['forward_calls'];source='PR55_archive'
            else:
                with torch.no_grad():actual,cause,n=prior.free(m,row['Q'])
                new_forward+=n;source='new_torch'
            truth,margins=teacher(m,row['Q'],expected)
            forward+=len(expected)
            c=counts[(seed,arm,row['role'],row['split'])]
            c['n']+=1;c['exact']+=actual==expected
            c['first_word']+=actual[:6]==expected[:6]
            c['second_word']+=actual[6:12]==expected[6:12]
            c['stop']+=cause=='stop' and len(actual)==13
            c['tf_first']+=sum(truth[:6]);c['tf_second']+=sum(truth[6:12])
            first_error=next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None)
            if first_error is None and len(actual)!=len(expected):first_error=min(len(actual),len(expected))
            raw.append(dict(seed=seed,arm=arm,**row,actual=actual,cause=cause,forward_calls=n,source=source,exact=actual==expected,
                first_error=first_error,tf_correct=truth,tf_margins=margins))
    # Primary test is strictly the j=10..14 portion; diagnostic val j6/7 is also reported.
    gates=[]
    for seed in SEEDS:
        old={arm:{role:counts[(seed,arm,role,'diagnostic_test')] for role in ('first','second')} for arm in ARMS}
        t=old['tied'];u=old['untied']
        gates.append(dict(seed=seed,tied_first=t['first']['exact'],tied_second=t['second']['exact'],
            untied_first=u['first']['exact'],untied_second=u['second']['exact'],
            pass_gate=t['first']['exact']<=1 and t['second']['exact']>=3 and t['second']['exact']-u['second']['exact']>=2))
    outcome=dict(work_id='SLE-AE1-ROLE-SWAP-20261114-R11',source_zip_sha256=json.loads((P/'prereg.json').read_text())['source_zip_sha256'],
        raw_rows=len(raw),new_free_generations=sum(r['source']=='new_torch' for r in raw),reused_free_generations=sum(r['source']=='PR55_archive' for r in raw),
        new_free_forwards=new_forward,new_teacher_forwards=forward,new_forward_MAC=(new_forward+forward)*MAC,
        parameter_counts=dict(tied=10457,untied=11081),training_updates=0,primary_gate='PASS' if sum(x['pass_gate'] for x in gates)>=2 else 'FAIL',
        seed_gates=gates,counts={f'{s}_{a}_{r}_{sp}':dict(x) for (s,a,r,sp),x in counts.items()})
    (P/'raw_cases.jsonl').write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in raw))
    outcome['raw_sha256']=digest(P/'raw_cases.jsonl')
    (P/'results.json').write_text(json.dumps(outcome,indent=2)+'\n')
    print('RESULT',outcome['primary_gate'],'gates=',gates,'new_free=',outcome['new_free_generations'],'new_forward=',new_forward+forward,flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['gate']:gate()
    elif sys.argv[1:]==['run']:experiment()
    elif sys.argv[1:]==['manifest']:
        for item in cases():print(json.dumps(item,separators=(',',':')))
    else:raise SystemExit('usage: python probe.py gate|manifest|run')
