"""P021: eight information bits, exact scalar reward, persistent raw-bit RNN."""
import copy, hashlib, json, time
from pathlib import Path
import numpy as np
import mlp_echo_trial as e
from gated_curriculum import Net

OUT=Path('D:/Codex用/work/sle-research-review/echo-8bit-20261112')
SEEDS=[101,202,303]
LENGTHS=np.arange(2,10)
COUNT=sum(2**int(k) for k in LENGTHS)
EPS=.15

class Policy(e.Policy):
    def __init__(self,seed):
        self.kind='rnn';self.h=16;rng=np.random.default_rng(seed)
        self.p=[rng.normal(0,.20,(17,16)).astype(np.float32),np.zeros(16,np.float32),
                rng.normal(0,.15,(16,17)).astype(np.float32),np.zeros(17,np.float32)]
        self.m=[np.zeros_like(p) for p in self.p];self.v=[p.copy() for p in self.m]
        self.steps=0;self.hidden=np.zeros((1,16),np.float32);self.baseline=.2;self.hidden_resets=1
    @staticmethod
    def probabilities(logits):
        z=logits[0];q=np.exp(z[9:]-np.max(z[9:]));q=q/q.sum()
        return e.sigmoid(z[:9]),q
    @staticmethod
    def log_probability(logits,action):
        z=logits[0];length=len(action);lz=z[9:].astype(np.float64)
        logq=lz[length-2]-np.logaddexp.reduce(lz)
        bits=np.array([int(b) for b in action])
        return float(logq+np.sum(bits*z[:length]-np.logaddexp(0,z[:length].astype(np.float64))))
    def greedy(self,logits):
        z=logits[0];candidates=[''.join('1' if x>=0 else '0' for x in z[:int(k)]) for k in LENGTHS]
        return max(candidates,key=lambda a:self.log_probability(logits,a))
    def predict(self,bits):
        logits,(h,_)=self.observe(bits);self.hidden=h
        return self.greedy(logits),logits
    def attempt(self,bits,grade,rng):
        logits,(h,cache)=self.observe(bits);p,q=self.probabilities(logits)
        if rng.random()<EPS:
            index=int(rng.integers(COUNT))
            for length in LENGTHS:
                if index<2**int(length):break
                index-=2**int(length)
            action=format(index,f'0{int(length)}b')
        else:
            length=int(rng.choice(LENGTHS,p=q.astype(np.float64)/q.sum(dtype=np.float64)))
            action=''.join('1' if b else '0' for b in rng.random(length)<p[:length])
        reward=float(grade(action))
        pi=np.exp(self.log_probability(logits,action));mixture=(1-EPS)*pi+EPS/COUNT
        weight=(reward-self.baseline)*(1-EPS)*pi/mixture
        d=np.zeros((1,17),dtype=logits.dtype);length=len(action)
        d[0,:length]=p[:length]-np.array([int(b) for b in action])
        d[0,9:]=q;d[0,9+length-2]-=1;d*=weight
        self.cached=(h,cache,d);self.hidden=h
        Net.update(self,None,None,None)
        self.baseline=.98*self.baseline+.02*reward
        return action,int(reward)
    def loss_grad(self,*_):
        h,cache,d=self.cached;W,b,V,a=self.p
        grads=[np.zeros_like(W),np.zeros_like(b),h.T@d,d.sum(0)];dh=d@V.T
        for z,hn in reversed(cache):
            dz=dh*(1-hn*hn);grads[0]+=z.T@dz;grads[1]+=dz.sum(0);dh=(dz@W.T)[:,1:]
        return 0.,grads

def material():
    rows={}
    for value in range(256):
        data=e.word(value,8,1);bits='01'+e.word(0,1,1)+data
        op=e.tokenize(bits,1,1,2);payload=e.tokenize(bits,8,1,4)
        assert op['value']==0 and payload['end']==len(bits) and len(bits)==13
        expected=e.codec.calc('echo',[payload['word']]);assert expected==data and len(expected)==9
        rows[value]=(bits,expected)
    values=np.random.default_rng(8212026).permutation(256).tolist()
    train=sorted(values[:192]);heldout=sorted(values[192:])
    assert len(set(train)&set(heldout))==0 and set(train+heldout)==set(range(256))
    return rows,train,heldout

def evaluate(net,values,rows):
    saved_h=net.hidden.copy();saved_p=[p.copy() for p in net.p];records=[]
    for context in range(4):
        clone=copy.deepcopy(net);order=np.random.default_rng(73000+context).permutation(values)
        for value in order:
            value=int(value);bits,expected=rows[value];answer,logits=clone.predict(bits)
            records.append({'context':context,'value':value,'answer':answer,'correct':answer==expected,
                            'expected_probability':float(np.exp(clone.log_probability(logits,expected))),
                            'length_correct':len(answer)==9,
                            'matching_bits':sum(a==b for a,b in zip(answer,expected)) if len(answer)==9 else 0})
    assert np.array_equal(saved_h,net.hidden) and all(np.array_equal(a,b) for a,b in zip(saved_p,net.p))
    return {'correct':sum(r['correct'] for r in records),'total':len(records),
            'length_correct':sum(r['length_correct'] for r in records),
            'matching_bits_length9':sum(r['matching_bits'] for r in records),
            'mastered':all(r['correct'] and r['expected_probability']>=.9 for r in records),
            'records':records}

def gradient_check():
    rng=np.random.default_rng(77);result=[]
    for action,advantage in [('01',.7),('101001010',-.2)]:
        net=Policy(8);net.p=[p.astype(np.float64) for p in net.p];net.hidden=rng.normal(0,.1,(1,16))
        bits='0100101001010';logits,(h,cache)=net.observe(bits);p,q=net.probabilities(logits)
        pi=np.exp(net.log_probability(logits,action));mix=(1-EPS)*pi+EPS/COUNT
        d=np.zeros((1,17));length=len(action)
        d[0,:length]=p[:length]-np.array([int(b) for b in action]);d[0,9:]=q;d[0,9+length-2]-=1
        d*=advantage*(1-EPS)*pi/mix;net.cached=(h,cache,d);_,grads=net.loss_grad()
        def objective():return -advantage*np.log((1-EPS)*np.exp(net.log_probability(net.observe(bits)[0],action))+EPS/COUNT)
        maximum=0.;tested=0
        for par,g in zip(net.p,grads):
            for i in rng.choice(par.size,min(8,par.size),replace=False):
                old=par.flat[i];par.flat[i]=old+1e-5;plus=objective();par.flat[i]=old-1e-5;minus=objective();par.flat[i]=old
                err=abs((plus-minus)/2e-5-g.flat[i]);assert err<1e-7,err
                maximum=max(maximum,err);tested+=1
        result.append({'action':action,'parameters_checked':tested,'max_error':maximum})
    net=Policy(4);logits=net.observe('0100000000000')[0]
    total=sum(np.exp(net.log_probability(logits,format(v,f'0{k}b'))) for k in LENGTHS for v in range(2**int(k)))
    assert abs(total-1)<1e-7 and COUNT==1020
    return result

def run(seed,rows,train,heldout):
    net=Policy(seed);rng=np.random.default_rng(seed+9100);order_rng=np.random.default_rng(seed+18000)
    order=order_rng.permutation(train).tolist();index=0;rounds=0;stable=0;trace=[];start=time.perf_counter()
    touched=set();successes=set();mastered=False;history=[]
    for attempt in range(1,50001):
        value=order[index];bits,expected=rows[value];answer,reward=net.attempt(bits,lambda a:a==expected,rng)
        touched.add(value)
        trace.append([value,answer,reward])
        if reward:
            successes.add(value);index+=1
            if index==len(order):
                rounds+=1;probe=evaluate(net,train,rows)
                history.append({'attempt':attempt,'correct':probe['correct'],'total':probe['total'],'mastered':probe['mastered']})
                stable=stable+1 if probe['mastered'] else 0
                if stable>=2:mastered=True;break
                order=order_rng.permutation(train).tolist();index=0
        if time.perf_counter()-start>120:break
    for a,b in zip(trace,trace[1:]):
        if not a[2]:assert a[0]==b[0]
    assert not (touched & set(heldout)) and net.hidden_resets==1
    folder=OUT/f'seed{seed}';folder.mkdir()
    (folder/'trace.json').write_text(json.dumps(trace))
    np.savez(folder/'state.npz',**{f'p{i}':p for i,p in enumerate(net.p)},
             **{f'm{i}':p for i,p in enumerate(net.m)},**{f'v{i}':p for i,p in enumerate(net.v)},
             hidden=net.hidden,steps=net.steps,baseline=net.baseline)
    summary={'seed':seed,'parameters':sum(p.size for p in net.p),'attempts':len(trace),'seconds':time.perf_counter()-start,
             'reward_count':sum(r[2] for r in trace),'unique_presented':len(touched),'unique_sampled_correct':len(successes),
             'complete_rounds':rounds,'mastered':mastered,'hidden_resets':net.hidden_resets,'history':history,
             'presented_values':sorted(touched),'trained_probe':evaluate(net,train,rows),
             'heldout_probe':evaluate(net,heldout,rows)}
    (folder/'summary.json').write_text(json.dumps(summary,indent=2))
    return summary

def replay(seed,rows,train):
    trace=json.loads((OUT/f'seed{seed}/trace.json').read_text());net=Policy(seed)
    rng=np.random.default_rng(seed+9100);order_rng=np.random.default_rng(seed+18000)
    order=order_rng.permutation(train).tolist();index=0
    for value,action,reward in trace:
        assert value==order[index];bits,expected=rows[value]
        h=net.hidden.copy();W,b,V,a=net.p
        for bit in bits:h=np.tanh(np.concatenate([np.array([[int(bit)]],np.float32),h],axis=1)@W+b)
        actual,grade=net.attempt(bits,lambda a:a==expected,rng)
        assert actual==action and grade==reward and np.array_equal(h,net.hidden)
        if reward:
            index+=1
            if index==len(order):order=order_rng.permutation(train).tolist();index=0
    saved=np.load(OUT/f'seed{seed}/state.npz')
    for label,items in [('p',net.p),('m',net.m),('v',net.v)]:
        assert all(np.array_equal(p,saved[f'{label}{i}']) for i,p in enumerate(items))
    assert np.array_equal(net.hidden,saved['hidden']) and net.steps==saved['steps'] and net.baseline==saved['baseline']
    return {'seed':seed,'attempts':len(trace),'actions_rewards_hidden_optimizer_checkpoint_equal':True}

def main():
    OUT.mkdir(parents=True,exist_ok=True);rows,train,heldout=material()
    plan={'id':'P021','date':'2026-11-12','seeds':SEEDS,'information_bits':8,'data_word_bits':9,'question_bits':13,
          'start':'Fresh experiment directly at data n8; no promotion within this run, no old-width inputs.',
          'train_values':train,'heldout_values':heldout,'split_seed':8212026,
          'network':'RNN16,577params,9Bernoulli bits plus8way length softmax. All strings length2..9,1020actions. Max9 is prior; teacher does not specify per-question length.',
          'learning':'Exact scalar REINFORCE reward only; EMA baseline,.15uniform exploration over1020actions,originalAdam lr.003. No correct-bit target gradient.',
          'curriculum':'Shuffle each complete training round; wrong repeats unchanged until sampled correct. One live hidden perseed. Perquestion truncatedBPTT. Mastery four shuffled trained-only probe streams, all correct withp>=.9, two completedrounds. Heldout never controls stopping.',
          'limits':'50000attempts or120sec perseed; all seeds retained; no tuning.',
          'interpretation':'Longer task and larger output space; not controlled solely for length. More combinations do not by themselves force copying. Whole-answer reward can be sparse.',
          'sources':{Path(p).name:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [__file__,e.__file__]}}
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    checks=gradient_check();(OUT/'gradient-check.json').write_text(json.dumps(checks))
    records=[run(seed,rows,train,heldout) for seed in SEEDS]
    audits=[replay(seed,rows,train) for seed in SEEDS]
    for r in records:
        net=Policy(r['seed']);saved=np.load(OUT/f"seed{r['seed']}/state.npz")
        net.p=[saved[f'p{i}'].copy() for i in range(4)];net.hidden=saved['hidden'].copy()
        assert evaluate(net,train,rows)==r['trained_probe'] and evaluate(net,heldout,rows)==r['heldout_probe']
    result={'plan':plan,'gradient_checks':checks,'runs':records,'audit':audits}
    (OUT/'compact.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'runs':[{k:r[k] for k in ['seed','parameters','attempts','seconds','reward_count','unique_presented','unique_sampled_correct','complete_rounds','mastered']}|
                       {'trained_correct':r['trained_probe']['correct'],'trained_total':r['trained_probe']['total'],
                        'heldout_correct':r['heldout_probe']['correct'],'heldout_total':r['heldout_probe']['total']} for r in records],
                      'gradient_checks':checks,'audit':audits}))

if __name__=='__main__':main()
