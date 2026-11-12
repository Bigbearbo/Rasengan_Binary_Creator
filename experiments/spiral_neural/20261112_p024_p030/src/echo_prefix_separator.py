"""P025: reread question|generated-prefix from zero for every next token."""
from _archive_paths import ARCHIVE_ROOT, REPO_ROOT, SRC_DIR, RUNS_ROOT, PLOTS_ROOT
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import copy,hashlib,json,time
from pathlib import Path
import numpy as np
import echo_serial_stop as previous
x=previous.x
OUT=RUNS_ROOT/'echo-prefix-separator-20261112'
LIMIT=20000

class Prefix(previous.Serial):
    def __init__(self,seed):
        rng=np.random.default_rng(seed)
        self.p=[rng.normal(0,.2,(19,16)).astype(np.float32),np.zeros(16,np.float32),
                rng.normal(0,.15,(16,3)).astype(np.float32),np.zeros(3,np.float32)]
        self.m=[np.zeros_like(p) for p in self.p];self.v=[p.copy() for p in self.m]
        self.hidden=np.zeros((1,16),np.float32);self.steps=0;self.baseline=.2

    def read(self,text):
        W,b,V,a=self.p;h=np.zeros((1,16),dtype=W.dtype);cache=[]
        for token in text:
            onehot=np.zeros((1,3),dtype=W.dtype);onehot[0,'01|'.index(token)]=1
            z=np.concatenate([onehot,h],axis=1);h=np.tanh(z@W+b);cache.append((z,h))
        return h,cache

    def roll(self,bits,rng=None,forced=None):
        _,_,V,a=self.p;tokens='';segments=[];outputs=[];logp=0.
        for step in range(previous.CAP):
            text=bits+'|'+tokens
            h,cache=self.read(text)  # Always a fresh zero hidden; full prefix retained externally.
            z=(h@V+a)[0].astype(np.float64);lp=z-np.logaddexp.reduce(z);p=np.exp(lp)
            token=forced[step] if forced is not None else ('01S'[int(rng.choice(3,p=p))] if rng is not None else '01S'[int(p.argmax())])
            index='01S'.index(token);logp+=lp[index]
            segments.append(cache);outputs.append((text,h,p,index));tokens+=token
            if token=='S':break
        if forced is not None:assert tokens==forced
        return tokens,np.zeros_like(self.hidden),segments,outputs,float(logp)

    def grads(self,segments,outputs,weight):
        W,b,V,a=self.p;g=[np.zeros_like(p) for p in self.p]
        for cache,(_,h,p,index) in zip(segments,outputs):
            d=p.copy();d[index]-=1;d=(d*weight).astype(h.dtype)[None,:]
            g[2]+=h.T@d;g[3]+=d[0];dh=d@V.T
            for z,hn in reversed(cache):
                dz=dh*(1-hn*hn);g[0]+=z.T@dz;g[1]+=dz[0];dh=(dz@W.T)[:,3:]
        return g


def checks():
    net=Prefix(8);example='010010110100';answer='10110100'
    tokens,_,_,outputs,_=net.roll(example,forced=answer+'S')
    actual=[row[0] for row in outputs]
    assert actual==[example+'|'+answer[:i] for i in range(len(answer)+1)]
    # This fixture verifies input construction, not that the model learned the example.
    fixture=[{'input':r[0],'forced_output':'01S'[r[3]]} for r in outputs]
    before=net.roll(example,forced='10S');net.hidden[:]=.99
    after=net.roll(example,forced='10S')
    assert before[-1]==after[-1]
    assert all(np.array_equal(a[1],b[1]) for a,b in zip(before[3],after[3]))
    results=[];rng=np.random.default_rng(77)
    for tokens in ['S','01S','101001010S','1111111111']:
        net=Prefix(8);net.p=[p.astype(np.float64) for p in net.p];bits='0100101001010'
        _,_,cache,outputs,lp=net.roll(bits,forced=tokens)
        q=1/x.COUNT if tokens.endswith('S') and 2<=len(tokens)-1<=9 else 0.
        adv=-.2 if tokens=='S' else .7;pi=np.exp(lp);mix=(1-x.EPS)*pi+x.EPS*q
        grads=net.grads(cache,outputs,adv*(1-x.EPS)*pi/mix)
        def loss():return -adv*np.log((1-x.EPS)*np.exp(net.roll(bits,forced=tokens)[-1])+x.EPS*q)
        maximum=0.;count=0
        for p,g in zip(net.p,grads):
            for i in rng.choice(p.size,min(8,p.size),replace=False):
                old=p.flat[i];p.flat[i]=old+1e-5;plus=loss();p.flat[i]=old-1e-5;minus=loss();p.flat[i]=old
                err=abs((plus-minus)/2e-5-g.flat[i]);assert err<1e-7,err
                maximum=max(maximum,err);count+=1
        results.append({'tokens':tokens,'checked':count,'max_error':maximum})
    net=Prefix(1);net.p[2][:]=0;net.p[3][:]=[0,0,50]
    assert net.predict(example)=='S'
    net.p[3][:]=[50,0,0];assert net.predict(example)=='0'*10
    class NoStop(Prefix):
        def roll(self,bits,rng=None,forced=None):return super().roll(bits,forced='0'*10)
    assert NoStop(1).attempt(example,lambda _:True,np.random.default_rng(3))[1]==0
    return {'user_example_forced_fixture':fixture,'not_a_learned_example':True,
            'prior_hidden_ignored':True,'stop_cap_no_stop_reward':True,'finite_difference':results}


def evaluate(net,values,rows):
    records=[]
    for v in values:
        bits,expected=rows[v];tokens=net.predict(bits);stop=tokens.endswith('S')
        answer=tokens[:-1] if stop else tokens
        records.append({'value':v,'answer':answer,'stopped':stop,'correct':stop and answer==expected})
    # Repeat in another order to verify no cross-question state dependence.
    reference={r['value']:r['answer']+('S' if r['stopped'] else '') for r in records}
    for v in np.random.default_rng(73000).permutation(values):assert net.predict(rows[int(v)][0])==reference[int(v)]
    return {'correct':sum(r['correct'] for r in records),'total':len(records),
            'stopped':sum(r['stopped'] for r in records),
            'length9':sum(r['stopped'] and len(r['answer'])==9 for r in records),
            'order_invariance':True,'records':records}


def run(seed,rows,train,heldout):
    net=Prefix(seed);rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(train).tolist();index=0;rounds=0;trace=[];touched=set();start=time.perf_counter()
    for attempt in range(LIMIT):
        value=order[index];bits,expected=rows[value]
        action,reward=net.attempt(bits,lambda a:a==expected,rng)
        trace.append([value,action,reward]);touched.add(value)
        if reward:
            index+=1
            if index==len(order):index=0;rounds+=1;order=shuffle.permutation(train).tolist()
        if time.perf_counter()-start>120:break
    for a,b in zip(trace,trace[1:]):
        if not a[2]:assert a[0]==b[0]
    assert not touched&set(heldout)
    folder=OUT/f'seed{seed}';folder.mkdir()
    (folder/'trace.json').write_text(json.dumps(trace))
    np.savez(folder/'state.npz',**{f'{label}{i}':p for label,arr in [('p',net.p),('m',net.m),('v',net.v)] for i,p in enumerate(arr)},steps=net.steps,baseline=net.baseline)
    summary={'seed':seed,'parameters':sum(p.size for p in net.p),'attempts':len(trace),
             'training_seconds':time.perf_counter()-start,'reward_count':sum(r[2] for r in trace),
             'unique_presented':len(touched),'complete_rounds':rounds,
             'train_probe':evaluate(net,train,rows),'heldout_probe':evaluate(net,heldout,rows)}
    replay=Prefix(seed);rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(train).tolist();index=0
    for value,action,reward in trace:
        assert value==order[index];bits,expected=rows[value]
        assert replay.attempt(bits,lambda a:a==expected,rng)==(action,reward)
        if reward:
            index+=1
            if index==len(order):index=0;order=shuffle.permutation(train).tolist()
    saved=np.load(folder/'state.npz')
    for label,arr in [('p',replay.p),('m',replay.m),('v',replay.v)]:
        assert all(np.array_equal(p,saved[f'{label}{i}']) for i,p in enumerate(arr))
    assert replay.steps==saved['steps'] and replay.baseline==saved['baseline']
    assert evaluate(replay,train,rows)==summary['train_probe']
    assert evaluate(replay,heldout,rows)==summary['heldout_probe']
    summary['full_replay_equal']=True
    (folder/'summary.json').write_text(json.dumps(summary,indent=2))
    compact={k:v for k,v in summary.items() if k not in ('train_probe','heldout_probe')}
    compact.update({key:{k:v for k,v in summary[key].items() if k!='records'} for key in ['train_probe','heldout_probe']})
    print(json.dumps(compact),flush=True);return compact


def main():
    OUT.mkdir(parents=True,exist_ok=True);rows,train,heldout=x.material()
    plan={'id':'P025','seeds':x.SEEDS,'attempt_limit':LIMIT,'time_cap_training_per_seed':120,
          'input':'Every next-token prediction rereads full rawquestion + literal separator | + sampled answer prefix from ZERO hidden. Onehot inputs 0/1/|; output0/1/STOP. No cached hidden across tokens or questions. This deliberately replaces the earlier persistent-hidden condition to test the user-specified explicit-prefix protocol.',
          'model':'RNN16,371params; output uses final state after full prefix. No attention/random-access prefix head. No claim this removes all recurrent compression.',
          'feedback':'Wholeanswer scalar only, wrongretry, shuffled complete rounds,Adam.003,EMA baseline; inherited .15uniform1020trajectory exploration withSTOP, same asP024. 10action cap; noSTOP fails.',
          'dataset':'SameP021 13bitrawquestions and9bitencodedanswers,192train64heldout. User12bitexample used ONLY as a forced input-construction test, not an extra training example or claim of learned decoding.',
          'evaluation':'One pass per set plus reordered invariance check; no hidden contexts. Fixed budget; no heldout tuning. EarlierP024 comparative numbers are historical, not rerun controls; heads/input/reset conditions all differ.',
          'train_values':train,'heldout_values':heldout,
          'sources':{str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [__file__,previous.__file__,x.__file__,x.e.__file__]}}
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    check=checks();(OUT/'checks.json').write_text(json.dumps(check,indent=2))
    results=[run(seed,rows,train,heldout) for seed in x.SEEDS]
    (OUT/'compact.json').write_text(json.dumps({'plan':plan,'checks':check,'runs':results},indent=2))

if __name__=='__main__':main()
