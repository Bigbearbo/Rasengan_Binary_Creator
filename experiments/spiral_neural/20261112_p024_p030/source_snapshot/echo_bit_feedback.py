"""P026: immediate per-token +/-1 feedback on self-generated prefixes."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import hashlib,json,time
from pathlib import Path
import numpy as np
from echo_prefix_direct import Direct,protocol
x=protocol.x
OUT=Path('D:/Codex用/work/sle-research-review/echo-bit-feedback-20261112')
EPS=.15
LIMIT=20000

def local_grade(expected,position,token):
    required=expected[position] if position<len(expected) else 'S'
    return 1 if token==required else -1

class Immediate(Direct):
    def __init__(self,seed):
        super().__init__(seed);self.baseline=0.

    def one(self,text,rng,feedback,forced=None):
        h,cache=self.read(text);V,a=self.p[2:]
        z=(h@V+a)[0].astype(np.float64);p=np.exp(z-np.logaddexp.reduce(z))
        mixture=(1-EPS)*p+EPS/3
        index=int(rng.choice(3,p=mixture)) if forced is None else '01S'.index(forced)
        token='01S'[index]
        reward=feedback(token)  # Only the numeric judgement reaches the learner.
        assert reward in (-1,1)
        weight=(reward-self.baseline)*(1-EPS)*p[index]/mixture[index]
        self.cached_grads=self.grads([cache],[(text,h,p,index)],weight)
        x.Net.update(self,None,None,None)  # Update BEFORE producing the next token.
        self.baseline=.98*self.baseline+.02*reward
        return token,reward

    def episode(self,bits,feedback,rng,forced=None):
        tokens='';rewards=[]
        for position in range(10):
            text=bits+'|'+tokens
            token,reward=self.one(text,rng,lambda t:feedback(position,t),None if forced is None else forced[position])
            tokens+=token;rewards.append(reward)
            if token=='S':break
        if forced is not None:assert tokens==forced
        return tokens,rewards


def checks():
    # Wrong content does not get repaired in the next input. Late STOP can be
    # locally correct even when an earlier bit made the whole answer wrong.
    class Recording(Immediate):
        def read(self,text):
            self.inputs.append(text);return super().read(text)
    net=Recording(1);net.inputs=[];steps=net.steps
    tokens,rewards=net.episode('010010',lambda pos,t:local_grade('10',pos,t),np.random.default_rng(1),forced='00S')
    assert tokens=='00S' and rewards==[-1,1,1]
    assert net.inputs==['010010|','010010|0','010010|00']
    assert net.steps-steps==3
    net=Immediate(1)
    assert net.episode('010010',lambda pos,t:local_grade('10',pos,t),np.random.default_rng(1),forced='S')[1]==[-1]
    assert local_grade('10',2,'0')==-1 and local_grade('10',2,'S')==1
    assert local_grade('10',3,'S')==1
    net=Immediate(1)
    tokens,rewards=net.episode('010010',lambda pos,t:local_grade('10',pos,t),np.random.default_rng(1),forced='0'*10)
    assert not tokens.endswith('S') and len(rewards)==10 and net.steps==10
    rng=np.random.default_rng(77);errors=[]
    for index,reward in [(0,-1),(1,1),(2,-1),(2,1)]:
        net=Immediate(8);net.p=[p.astype(np.float64) for p in net.p]
        text='0100101001010|101';h,cache=net.read(text);z=(h@net.p[2]+net.p[3])[0]
        p=np.exp(z-np.logaddexp.reduce(z));mix=(1-EPS)*p+EPS/3
        baseline=.2;adv=reward-baseline
        g=net.grads([cache],[(text,h,p,index)],adv*(1-EPS)*p[index]/mix[index])
        def loss():
            h,_=net.read(text);z=(h@net.p[2]+net.p[3])[0];p=np.exp(z-np.logaddexp.reduce(z))
            return -adv*np.log((1-EPS)*p[index]+EPS/3)
        maximum=0.;count=0
        for par,grad in zip(net.p,g):
            for i in rng.choice(par.size,min(8,par.size),replace=False):
                old=par.flat[i];par.flat[i]=old+1e-5;plus=loss();par.flat[i]=old-1e-5;minus=loss();par.flat[i]=old
                err=abs((plus-minus)/2e-5-grad.flat[i]);assert err<1e-7,err
                maximum=max(maximum,err);count+=1
        errors.append({'action':'01S'[index],'reward':reward,'checked':count,'max_error':maximum})
    return {'wrong_prefix_kept':True,'update_after_every_token':True,'early_stop_and_cap':True,
            'local_vs_whole_reward_distinguished':True,'finite_difference':errors}


def run(seed,rows,train,heldout):
    net=Immediate(seed);rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(train).tolist();index=0;rounds=0;trace=[];touched=set();start=time.perf_counter()
    for attempt in range(LIMIT):
        value=order[index];bits,expected=rows[value]
        tokens,rewards=net.episode(bits,lambda pos,t:local_grade(expected,pos,t),rng)
        whole=tokens==expected+'S'
        trace.append([value,tokens,rewards]);touched.add(value)
        if whole:
            index+=1
            if index==len(order):index=0;rounds+=1;order=shuffle.permutation(train).tolist()
        if time.perf_counter()-start>120:break
    assert not touched&set(heldout)
    for a,b in zip(trace,trace[1:]):
        if a[1]!=rows[a[0]][1]+'S':assert a[0]==b[0]
    folder=OUT/f'seed{seed}';folder.mkdir()
    (folder/'trace.json').write_text(json.dumps(trace))
    np.savez(folder/'state.npz',**{f'{label}{i}':p for label,arr in [('p',net.p),('m',net.m),('v',net.v)] for i,p in enumerate(arr)},steps=net.steps,baseline=net.baseline)
    summary={'seed':seed,'parameters':sum(p.size for p in net.p),'episodes':len(trace),
             'token_updates':net.steps,'training_seconds':time.perf_counter()-start,
             'positive_token_rewards':sum(sum(r==1 for r in t[2]) for t in trace),
             'negative_token_rewards':sum(sum(r==-1 for r in t[2]) for t in trace),
             'sampled_whole_correct':sum(t[1]==rows[t[0]][1]+'S' for t in trace),
             'unique_presented':len(touched),'complete_rounds':rounds,
             'train_probe':protocol.evaluate(net,train,rows),'heldout_probe':protocol.evaluate(net,heldout,rows)}
    replay=Immediate(seed);rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(train).tolist();index=0
    for value,tokens,rewards in trace:
        assert value==order[index];bits,expected=rows[value]
        actual,grades=replay.episode(bits,lambda pos,t:local_grade(expected,pos,t),rng)
        assert actual==tokens and grades==rewards
        if tokens==expected+'S':
            index+=1
            if index==len(order):index=0;order=shuffle.permutation(train).tolist()
    saved=np.load(folder/'state.npz')
    for label,arr in [('p',replay.p),('m',replay.m),('v',replay.v)]:
        assert all(np.array_equal(p,saved[f'{label}{i}']) for i,p in enumerate(arr))
    assert replay.steps==saved['steps'] and replay.baseline==saved['baseline']
    assert protocol.evaluate(replay,train,rows)==summary['train_probe']
    assert protocol.evaluate(replay,heldout,rows)==summary['heldout_probe']
    summary['full_token_reward_optimizer_replay_equal']=True
    (folder/'summary.json').write_text(json.dumps(summary,indent=2))
    compact={k:v for k,v in summary.items() if k not in ('train_probe','heldout_probe')}
    compact.update({key:{k:v for k,v in summary[key].items() if k!='records'} for key in ['train_probe','heldout_probe']})
    print(json.dumps(compact),flush=True);return compact


def main():
    OUT.mkdir(parents=True,exist_ok=True);rows,train,heldout=x.material()
    plan={'id':'P026','seeds':x.SEEDS,'episodes_per_seed':LIMIT,'training_seconds_limit_per_seed':120,
          'model':'Fresh same P025B DirectMLP1171params,69input16tanh3softmax. Full question|own generated prefix each step; no recurrent state.',
          'feedback':'Immediate local +/-1 for sampled0/1/STOP at current position. Learner receives scalar only; checker compares expected bit orSTOP. Wrong prefix retained, no correction/teacher forcing; STOP ends even if wrong. Each token updated before next inference.',
          'curriculum':'Same192train64heldout P021codec. Wrong whole-answer repeats question; complete training round reshuffles. No short curriculum or heldout stopping.',
          'optimizer':'Adam.003 inherited clipping; pertoken EMA baseline initial0. epsilon.15 independent uniform3 action mixture EACH STEP, exact posterior correction.',
          'interpretation':'Per-token correctness reveals extra target information and STOP/length correctness, especially binarybit feedback. Not original wholeanswer-scalar learning. Changed feedback density/timing, exploration distribution, update count and baseline; package comparison to historicalP025B, not isolated feedback causal test.',
          'train_values':train,'heldout_values':heldout,
          'sources':{str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [__file__,__import__('inspect').getfile(Direct),protocol.__file__,x.__file__]}}
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    check=checks();(OUT/'checks.json').write_text(json.dumps(check,indent=2))
    records=[run(seed,rows,train,heldout) for seed in x.SEEDS]
    (OUT/'compact.json').write_text(json.dumps({'plan':plan,'checks':check,'runs':records},indent=2))

if __name__=='__main__':main()
