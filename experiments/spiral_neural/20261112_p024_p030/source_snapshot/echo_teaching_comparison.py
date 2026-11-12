"""P027: fixed MLP, reward/scheduling control and teacher-forced CE learning."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import hashlib,json,time
from pathlib import Path
import numpy as np
import echo_bit_feedback as old
Direct=old.Direct
x=old.x
OUT=Path('D:/Codex用/work/sle-research-review/echo-teaching-comparison-20261112')
LIMIT=20000
ANCHOR=100000

def snapshot(net):
    return {f'{label}{i}':p.copy() for label,arr in [('p',net.p),('m',net.m),('v',net.v)] for i,p in enumerate(arr)}|{'steps':np.array(net.steps),'baseline':np.array(net.baseline)}

def anchor(net):
    if net.steps==ANCHOR:net.anchor=snapshot(net)

class Reward(old.Immediate):
    def one(self,*args,**kwargs):
        result=super().one(*args,**kwargs);anchor(self);return result

class Supervised(Direct):
    def one_target(self,text,target):
        h,cache=self.read(text);z=(h@self.p[2]+self.p[3])[0].astype(np.float64)
        lp=z-np.logaddexp.reduce(z);p=np.exp(lp);index='01S'.index(target)
        self.cached_grads=self.grads([cache],[(text,h,p,index)],1.)
        x.Net.update(self,None,None,None);anchor(self)
        return '01S'[int(p.argmax())]

    def lesson(self,bits,expected):
        predictions=''
        for pos,target in enumerate(expected+'S'):
            predictions+=self.one_target(bits+'|'+expected[:pos],target)
        return predictions


def evaluate(net,values,rows):
    bit_counts=np.zeros(9,dtype=int);teacher_counts=np.zeros(10,dtype=int);records=[]
    for value in values:
        bits,expected=rows[value];tokens=net.predict(bits);stopped=tokens.endswith('S')
        answer=tokens[:-1] if stopped else tokens
        correct=[i<len(answer) and answer[i]==b for i,b in enumerate(expected)]
        bit_counts+=correct
        teacher=''
        for pos in range(10):
            h,_=net.read(bits+'|'+expected[:pos]);teacher+='01S'[int((h@net.p[2]+net.p[3])[0].argmax())]
        teacher_counts+=[a==b for a,b in zip(teacher,expected+'S')]
        records.append({'value':value,'generated':tokens,'expected':expected+'S','whole_correct':tokens==expected+'S',
                        'stopped':stopped,'stop_at_correct_position':stopped and len(answer)==len(expected),
                        'bit_correct':correct,'teacher_prefix_predictions':teacher})
    reference={r['value']:r['generated'] for r in records}
    for value in np.random.default_rng(73000).permutation(values):assert net.predict(rows[int(value)][0])==reference[int(value)]
    n=len(values)
    return {'whole_correct':sum(r['whole_correct'] for r in records),'total':n,
            'bit_correct_by_position':bit_counts.tolist(),'bit_denominator_per_position':n,
            'bit_accuracy':float(bit_counts.sum()/(9*n)),
            'any_stop':sum(r['stopped'] for r in records),
            'stop_at_correct_position':sum(r['stop_at_correct_position'] for r in records),
            'teacher_prefix_correct_by_position':teacher_counts.tolist(),
            'order_invariance':True,'records':records}

def trim(probe):return {k:v for k,v in probe.items() if k!='records'}


def checks():
    errors=[];rng=np.random.default_rng(77)
    for target in '01S':
        net=Supervised(8);net.p=[p.astype(np.float64) for p in net.p]
        text='0100101001010|101';h,cache=net.read(text);z=(h@net.p[2]+net.p[3])[0]
        p=np.exp(z-np.logaddexp.reduce(z));index='01S'.index(target)
        grads=net.grads([cache],[(text,h,p,index)],1.)
        def loss():
            h,_=net.read(text);z=(h@net.p[2]+net.p[3])[0]
            return np.logaddexp.reduce(z)-z[index]
        maximum=0.;count=0
        for par,g in zip(net.p,grads):
            for i in rng.choice(par.size,min(8,par.size),replace=False):
                saved=par.flat[i];par.flat[i]=saved+1e-5;plus=loss();par.flat[i]=saved-1e-5;minus=loss();par.flat[i]=saved
                err=abs((plus-minus)/2e-5-g.flat[i]);assert err<1e-7,err
                maximum=max(maximum,err);count+=1
        errors.append({'target':target,'checked':count,'max_error':maximum})
    class Record(Supervised):
        def one_target(self,text,target):self.inputs.append((text,target));return super().one_target(text,target)
    net=Record(1);net.inputs=[];net.lesson('010010','10')
    assert net.inputs==[('010010|','1'),('010010|1','0'),('010010|10','S')]
    assert net.steps==3
    for seed in x.SEEDS:
        a=Reward(seed);b=Supervised(seed)
        assert all(np.array_equal(p,q) for p,q in zip(a.p,b.p))
    return {'crossentropy_finite_differences':errors,'correct_prefix_and_stop_targets':True,'initial_weights_identical_across_arms':True,
            'reward_checks_rerun':old.checks()}


def train(seed,arm,rows,bank,heldout):
    net=Supervised(seed) if arm=='ce_shuffle' else Reward(seed)
    rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(bank).tolist();index=0;rounds=0;trace=[];counts={v:0 for v in bank};start=time.perf_counter()
    for episode in range(LIMIT):
        value=order[index];bits,expected=rows[value]
        if arm=='ce_shuffle':record=[value,net.lesson(bits,expected)];advance=True
        else:
            tokens,rewards=net.episode(bits,lambda pos,t:old.local_grade(expected,pos,t),rng)
            record=[value,tokens,rewards];advance=arm=='reward_shuffle' or tokens==expected+'S'
        trace.append(record);counts[value]+=1
        if advance:
            index+=1
            if index==len(order):index=0;rounds+=1;order=shuffle.permutation(bank).tolist()
        if time.perf_counter()-start>120:break
    seconds=time.perf_counter()-start
    assert not set(counts)&set(heldout) and net.steps<=200000
    if arm!='reward_repeat':
        assert max(counts.values())-min(counts.values())<=1
        assert all(len({r[0] for r in trace[i:i+192]})==192 for i in range(0,len(trace)-191,192))
    folder=OUT/f'{arm}-{seed}';folder.mkdir()
    (folder/'trace.json').write_text(json.dumps(trace))
    final=snapshot(net);np.savez(folder/'state.npz',**final)
    if hasattr(net,'anchor'):np.savez(folder/'equal-update-100000.npz',**net.anchor)
    probes={key:evaluate(net,values,rows) for key,values in [('train',bank),('heldout',heldout)]}
    anchor_probes=None
    if hasattr(net,'anchor'):
        clone=Supervised(seed);clone.p=[net.anchor[f'p{i}'].copy() for i in range(4)]
        anchor_probes={key:evaluate(clone,values,rows) for key,values in [('train',bank),('heldout',heldout)]}
    # Replay every fresh training trajectory; do not reuse a prior PASS.
    replay=Supervised(seed) if arm=='ce_shuffle' else Reward(seed)
    rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(bank).tolist();index=0
    for record in trace:
        value=record[0];assert value==order[index];bits,expected=rows[value]
        if arm=='ce_shuffle':assert replay.lesson(bits,expected)==record[1];advance=True
        else:
            tokens,rewards=replay.episode(bits,lambda pos,t:old.local_grade(expected,pos,t),rng)
            assert [value,tokens,rewards]==record;advance=arm=='reward_shuffle' or tokens==expected+'S'
        if advance:
            index+=1
            if index==len(order):index=0;order=shuffle.permutation(bank).tolist()
    assert all(np.array_equal(v,snapshot(replay)[k]) for k,v in final.items())
    if hasattr(net,'anchor'):assert all(np.array_equal(v,replay.anchor[k]) for k,v in net.anchor.items())
    for key,values in [('train',bank),('heldout',heldout)]:assert evaluate(replay,values,rows)==probes[key]
    result={'arm':arm,'seed':seed,'question_presentations':len(trace),'token_updates':net.steps,'training_seconds':seconds,
            'unique_presented':sum(v>0 for v in counts.values()),'complete_rounds':rounds,
            'exposure_min':min(counts.values()),'exposure_max':max(counts.values()),'all_trajectory_optimizer_and_anchor_replay_equal':True,
            'probes':{key:trim(p) for key,p in probes.items()},
            'at_equal_100000_updates':None if anchor_probes is None else {key:trim(p) for key,p in anchor_probes.items()}}
    (folder/'probes.json').write_text(json.dumps({'final':probes,'equal_update':anchor_probes},indent=2))
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True);return result


def main():
    OUT.mkdir(parents=True,exist_ok=True);rows,bank,heldout=x.material()
    plan={'id':'P027','seeds':x.SEEDS,'arms':{
          'reward_repeat':'Fresh rerun P026 pertoken+/-1 policygradient, own prefixes, wholecorrect required to advance.',
          'reward_shuffle':'Identical reward learner and initialization; advance every question regardless of correctness, reshuffle after192.',
          'ce_shuffle':'Same1171param MLP; correctbit/STOP crossentropy, correctanswerprefixes, everyquestion advances, reshuffle after192.'},
          'budgets':'Each arm/seed20kquestionpresentations,200ktokenupdate upperbound,120sec training upperbound; final actualupdates/time reported. Additional checkpoint exactly100koptimizerupdates for all arms; this equates updates, NOT exposure counts or exact FLOPs/walltime. No claim both resources matched simultaneously.',
          'data':'Same192/64 P021codec 13bitquestion9bitanswer. All heldout eval only after training; neither earlystop nor tuning.',
          'evaluation':'Freeautoregressive generation on selfoutputs, eachbit missingcountswrong,wholeexact,anySTOP,STOPatcorrectposition. Teacherprefix accuracy separately labelled; fixedlengthstop not proof ofEcho. No arbitrarylength claim.',
          'causal_scope':'Repeat vs shuffle reward isolates scheduling intervention at same episodebudget. CEvsreward_shuffle changes objective AND trainingprefixsource; package comparison, not isolated objective effect.100kcheckpoint is separate updatebudget comparison.',
          'train_values':bank,'heldout_values':heldout,
          'sources':{str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [__file__,old.__file__,__import__('inspect').getfile(Direct),old.protocol.__file__,x.__file__]}}
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    check=checks();(OUT/'checks.json').write_text(json.dumps(check,indent=2))
    records=[]
    for arm in ['ce_shuffle','reward_shuffle','reward_repeat']:
        for seed in x.SEEDS:
            records.append(train(seed,arm,rows,bank,heldout))
            (OUT/'progress.json').write_text(json.dumps(records,indent=2))
    (OUT/'compact.json').write_text(json.dumps({'plan':plan,'checks':check,'runs':records},indent=2))

if __name__=='__main__':main()
