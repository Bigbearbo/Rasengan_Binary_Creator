"""P024: scalar-reward autoregressive 0/1/STOP pilot and fresh parallel control."""
from _archive_paths import ARCHIVE_ROOT, REPO_ROOT, SRC_DIR, RUNS_ROOT, PLOTS_ROOT
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import copy, hashlib, json, time
from pathlib import Path
import numpy as np
import echo_8bit_trial as x

OUT=RUNS_ROOT/'echo-serial-stop-20261112'
CAP=10
LIMIT=20000

class Serial:
    def __init__(self,seed):
        old=x.Policy(seed)
        self.p=[old.p[0].copy(),old.p[1].copy(),old.p[2][:,:3].copy(),np.zeros(3,np.float32)]
        self.m=[np.zeros_like(p) for p in self.p];self.v=[p.copy() for p in self.m]
        self.hidden=old.hidden.copy();self.hidden_resets=1;self.steps=0;self.baseline=.2

    def roll(self,bits,rng=None,forced=None):
        W,b,V,a=self.p;h=self.hidden.copy();cache=[];outputs=[];tokens='';logp=0.
        def feed(bit,h):
            z=np.concatenate([np.array([[int(bit)]],dtype=h.dtype),h],axis=1)
            hn=np.tanh(z@W+b);cache.append((z,hn));return hn
        for bit in bits:h=feed(bit,h)
        for step in range(CAP):
            z=h@V+a;lz=z[0].astype(np.float64);lp=lz-np.logaddexp.reduce(lz);p=np.exp(lp)
            token=forced[step] if forced is not None else ('01S'[int(rng.choice(3,p=p))] if rng is not None else '01S'[int(np.argmax(p))])
            index='01S'.index(token);tokens+=token;logp+=lp[index]
            outputs.append((len(cache)-1,h.copy(),p,index))
            if token=='S':break
            h=feed(token,h)
        if forced is not None:assert tokens==forced
        return tokens,h,cache,outputs,float(logp)

    def grads(self,cache,outputs,weight):
        W,b,V,a=self.p;g=[np.zeros_like(p) for p in self.p];inject={}
        for t,h,p,index in outputs:
            d=p.copy();d[index]-=1;d=(d*weight).astype(h.dtype)[None,:]
            g[2]+=h.T@d;g[3]+=d[0];inject[t]=inject.get(t,0)+d@V.T
        dh=np.zeros_like(self.hidden)
        for t in reversed(range(len(cache))):
            z,h=cache[t];dh=dh+inject.get(t,0);dz=dh*(1-h*h)
            g[0]+=z.T@dz;g[1]+=dz[0];dh=(dz@W.T)[:,1:]
        return g

    def loss_grad(self,*_):return 0.,self.cached_grads

    def attempt(self,bits,grade,rng):
        # Same trajectory-level .15 exploration over the old 1020 bitstrings.
        # These are sampled actions, not teacher targets; all now include STOP.
        forced=None
        if rng.random()<x.EPS:
            index=int(rng.integers(x.COUNT))
            for length in x.LENGTHS:
                if index<2**int(length):break
                index-=2**int(length)
            forced=format(index,f'0{int(length)}b')+'S'
        tokens,h,cache,outputs,logp=self.roll(bits,rng,forced)
        stopped=tokens.endswith('S');answer=tokens[:-1] if stopped else tokens
        reward=float(stopped and grade(answer))
        pi=np.exp(logp);q=1/x.COUNT if stopped and 2<=len(answer)<=9 else 0.
        weight=(reward-self.baseline)*(1-x.EPS)*pi/((1-x.EPS)*pi+x.EPS*q)
        self.cached_grads=self.grads(cache,outputs,weight);self.hidden=h
        x.Net.update(self,None,None,None)
        self.baseline=.98*self.baseline+.02*reward
        return tokens,int(reward)

    def predict(self,bits):
        tokens,h,*_=self.roll(bits);self.hidden=h;return tokens


def evaluate(net,values,rows,serial):
    original=net.hidden.copy();records=[]
    for context in range(4):
        clone=copy.deepcopy(net)
        for v in np.random.default_rng(73000+context).permutation(values):
            bits,expected=rows[int(v)]
            if serial:
                tokens=clone.predict(bits);stopped=tokens.endswith('S');answer=tokens[:-1] if stopped else tokens
            else:
                answer,_=clone.predict(bits);stopped=True
            records.append([context,int(v),answer,stopped,int(stopped and answer==expected)])
    assert np.array_equal(original,net.hidden)
    return {'correct':sum(r[4] for r in records),'total':len(records),
            'stopped':sum(r[3] for r in records),'length9':sum(r[3] and len(r[2])==9 for r in records),
            'records':records}


def gradient_check():
    errors=[];rng=np.random.default_rng(77)
    for tokens in ['S','01S','101001010S','1111111111']:
        net=Serial(8);net.p=[p.astype(np.float64) for p in net.p]
        net.hidden=rng.normal(0,.1,(1,16));bits='0100101001010'
        _,_,cache,outputs,logp=net.roll(bits,forced=tokens)
        q=1/x.COUNT if tokens.endswith('S') and 2<=len(tokens)-1<=9 else 0.
        advantage=-.2 if tokens=='S' else .7
        pi=np.exp(logp);mix=(1-x.EPS)*pi+x.EPS*q
        g=net.grads(cache,outputs,advantage*(1-x.EPS)*pi/mix)
        def loss():
            lp=net.roll(bits,forced=tokens)[-1]
            return -advantage*np.log((1-x.EPS)*np.exp(lp)+x.EPS*q)
        maximum=0.;count=0
        for p,grad in zip(net.p,g):
            for i in rng.choice(p.size,min(8,p.size),replace=False):
                old=p.flat[i];p.flat[i]=old+1e-5;plus=loss();p.flat[i]=old-1e-5;minus=loss();p.flat[i]=old
                err=abs((plus-minus)/2e-5-grad.flat[i]);assert err<1e-7,(tokens,err)
                maximum=max(maximum,err);count+=1
        errors.append({'tokens':tokens,'checked':count,'max_error':maximum})
    # Deterministic STOP and no-STOP cap guards, without teacher access.
    net=Serial(1);net.p[2][:]=0;net.p[3][:]=[0,0,50]
    assert net.predict('010')=='S'
    net.p[3][:]=[50,0,0];assert net.predict('010')=='0'*CAP
    # A correct bitstring without STOP is never rewarded.
    class NeverStop(Serial):
        def roll(self,bits,rng=None,forced=None):return super().roll(bits,forced='0'*CAP)
    net=NeverStop(1);_,reward=net.attempt('010',lambda _:True,np.random.default_rng(1));assert reward==0
    return {'finite_difference':errors,'stop_cap_and_no_stop_reward_guards':True}


def run(seed,serial,rows,train,heldout):
    net=Serial(seed) if serial else x.Policy(seed)
    rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(train).tolist();index=0;rounds=0;trace=[];touched=set();start=time.perf_counter()
    for attempt in range(LIMIT):
        value=order[index];bits,expected=rows[value]
        action,reward=net.attempt(bits,lambda a:a==expected,rng)
        trace.append([value,action,reward]);touched.add(value)
        if reward:
            index+=1
            if index==len(order):rounds+=1;index=0;order=shuffle.permutation(train).tolist()
        if time.perf_counter()-start>120:break
    assert not touched&set(heldout) and net.hidden_resets==1
    for a,b in zip(trace,trace[1:]):
        if not a[2]:assert a[0]==b[0]
    name=('serial' if serial else 'parallel')+f'-{seed}';folder=OUT/name;folder.mkdir()
    (folder/'trace.json').write_text(json.dumps(trace))
    np.savez(folder/'state.npz',**{f'{label}{i}':p for label,arr in [('p',net.p),('m',net.m),('v',net.v)] for i,p in enumerate(arr)},hidden=net.hidden,steps=net.steps,baseline=net.baseline)
    result={'name':name,'seed':seed,'serial':serial,'parameters':sum(p.size for p in net.p),
            'attempts':len(trace),'seconds':time.perf_counter()-start,'reward_count':sum(r[2] for r in trace),
            'unique_presented':len(touched),'complete_rounds':rounds,
            'train_probe':evaluate(net,train,rows,serial),'heldout_probe':evaluate(net,heldout,rows,serial)}
    # Full deterministic replay of actions, rewards, curriculum, hidden and Adam.
    replay=Serial(seed) if serial else x.Policy(seed)
    rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(train).tolist();index=0
    for value,action,reward in trace:
        assert order[index]==value;bits,expected=rows[value]
        if serial:
            # Independent hidden-state computation includes only emitted bits.
            h=replay.hidden.copy();W,b,_,_=replay.p
            for bit in bits+action.rstrip('S'):
                h=np.tanh(np.concatenate([np.array([[int(bit)]],np.float32),h],axis=1)@W+b)
        actual,grade=replay.attempt(bits,lambda a:a==expected,rng)
        assert (actual,grade)==(action,reward)
        if serial:assert np.array_equal(h,replay.hidden)
        if reward:
            index+=1
            if index==len(order):index=0;order=shuffle.permutation(train).tolist()
    saved=np.load(folder/'state.npz')
    for label,arr in [('p',replay.p),('m',replay.m),('v',replay.v)]:
        assert all(np.array_equal(p,saved[f'{label}{i}']) for i,p in enumerate(arr))
    assert np.array_equal(replay.hidden,saved['hidden']) and replay.steps==saved['steps'] and replay.baseline==saved['baseline']
    assert evaluate(replay,train,rows,serial)==result['train_probe']
    assert evaluate(replay,heldout,rows,serial)==result['heldout_probe']
    result['full_replay_and_probes_equal']=True
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True);rows,train,heldout=x.material()
    plan={'id':'P024','seeds':x.SEEDS,'attempt_limit':LIMIT,'seconds_per_training_arm':120,
          'serial':'RNN16,339params. Read13rawbits, predict0/1/STOP; feed sampled0/1 back through same RNN; STOP terminates without recurrent input. Up to10actions; missingSTOP fails, never forceSTOP. Hidden persistent across answers/questions/retries; gradients truncated at question boundary.',
          'control':'Fresh P021 parallel RNN16,577params; same seeds/split/curriculum/Adam.003. Not P022 continuation.',
          'reward':'Only whole-answer exact scalar, including realSTOP in serial; no teacher bit/length gradients. Same .15 trajectory exploration uniform over1020oldstrings length2..9, serial appendsSTOP. Remaining .85 sampled policy may emit empty/onebit or fail cap.',
          'comparison_limits':'Output head/parameter count/action space/decoder hidden dynamics differ; not a single-factor causal test. Existing fixed192/64 split, not new blind data. Greedy serial vs old whole-answer mode decoding differ. Fixed budget, no heldout stopping or tuning.',
          'train_values':train,'heldout_values':heldout,
          'sources':{str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [__file__,x.__file__,x.e.__file__,__import__('inspect').getfile(x.Net)]}}
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    checks=gradient_check();(OUT/'checks.json').write_text(json.dumps(checks,indent=2))
    summaries=[]
    for serial in [True,False]:
        for seed in x.SEEDS:
            r=run(seed,serial,rows,train,heldout);summaries.append(r)
            print(json.dumps({k:v for k,v in r.items() if k not in ('train_probe','heldout_probe')}|{'train':r['train_probe']['correct'],'heldout':r['heldout_probe']['correct']}),flush=True)
    compact={'plan':plan,'checks':checks,'runs':[{k:v for k,v in r.items() if k not in ('train_probe','heldout_probe')}|{key:{k:v for k,v in r[key].items() if k!='records'} for key in ['train_probe','heldout_probe']} for r in summaries]}
    (OUT/'compact.json').write_text(json.dumps(compact,indent=2))

if __name__=='__main__':main()
