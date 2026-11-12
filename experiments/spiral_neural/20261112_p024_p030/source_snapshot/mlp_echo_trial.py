"""Paper4 Q1-Q3 subset: scalar-reward Echo, monotonic data width, live RNN state.

Reuse existing word/tokenize/calc and NumPy RNN Adam. This is not the v0.6
CONFIG protocol: it is the paper's one-layer initial Echo teaching profile.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import copy,hashlib,importlib.util,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
CHECKOUT=ROOT.parent/'work/sle-research-review/checkout'
sys.path.insert(0,str(CHECKOUT/'experiments/spiral_parser'))
sys.path.insert(0,str(ROOT/'spiral-blank-model'))
from spiral_dialogue_v02 import word
from spiral_parser import tokenize
from gated_curriculum import Net,sigmoid
spec=importlib.util.spec_from_file_location('paper_teaching',CHECKOUT/'experiments/spiral_teaching/MLP_二層協議_編解碼驗證器.py')
codec=importlib.util.module_from_spec(spec);sys.modules[spec.name]=codec;spec.loader.exec_module(codec)
OUT=ROOT.parent/'work/sle-research-review/paper4-echo-reward'
ACTIONS=[format(v,f'0{length}b') for length in [2,3] for v in range(1<<length)]

class Teacher:
    def __init__(self):self.n=1;self.promotions=0;self.first_after_promotion=False
    def upgrade(self):
        if self.n!=1:raise ValueError('only one promotion in this experiment')
        self.n=2;self.promotions+=1;self.first_after_promotion=True
    def ask(self,value):
        data=word(value,self.n,1)
        if self.first_after_promotion:
            assert data[1]=='1' and data[2]=='0','old tail must become1;new tail must be0'
            self.first_after_promotion=False
        bits='01'+word(0,1,1)+data
        op=tokenize(bits,1,1,2);payload=tokenize(bits,self.n,1,4)
        assert op['value']==0 and payload['end']==len(bits)
        expected=codec.calc('echo',[payload['word']])
        return bits,expected

class Policy(Net):
    def __init__(self,seed):
        self.kind='rnn';self.h=16;rng=np.random.default_rng(seed)
        self.p=[rng.normal(0,.20,(17,16)).astype(np.float32),np.zeros(16,np.float32),rng.normal(0,.15,(16,4)).astype(np.float32),np.zeros(4,np.float32)]
        self.m=[np.zeros_like(p) for p in self.p];self.v=[p.copy() for p in self.m];self.steps=0
        self.hidden=np.zeros((1,16),np.float32);self.baseline=.2;self.hidden_resets=1
    def observe(self,bits):
        W,b,V,a=self.p;h=self.hidden.copy();cache=[]
        for bit in bits:
            x=np.array([[int(bit)]],np.float32);z=np.concatenate([x,h],axis=1)
            h=np.tanh(z@W+b);cache.append((z,h))
        return h@V+a,(h,cache)
    @staticmethod
    def distribution(logits):
        p=sigmoid(logits)[0];prob=[]
        for action in ACTIONS:
            long=len(action)==3;v=p[3] if long else 1-p[3]
            for i,bit in enumerate(action):v*=p[i] if bit=='1' else 1-p[i]
            prob.append(v)
        prob=np.array(prob,dtype=np.float64);return prob/prob.sum()
    def predict(self,bits):
        logits,(h,_)=self.observe(bits);self.hidden=h
        probs=self.distribution(logits);return ACTIONS[int(probs.argmax())],probs
    def attempt(self,bits,grade,rng,epsilon=.15):
        logits,(h,cache)=self.observe(bits);prob=self.distribution(logits)
        mixture=(1-epsilon)*prob+epsilon/len(ACTIONS)
        index=int(rng.choice(len(ACTIONS),p=mixture));action=ACTIONS[index]
        reward=float(grade(action)) # Scalar only: no correct-answer bits enter policy.
        advantage=reward-self.baseline
        posterior=(1-epsilon)*prob[index]/mixture[index]
        labels=np.zeros((1,4),np.float32);mask=np.zeros_like(labels)
        for i,bit in enumerate(action):labels[0,i]=int(bit);mask[0,i]=1
        labels[0,3]=len(action)==3;mask[0,3]=1
        self.cached=(logits,h,cache,advantage*posterior)
        self.hidden=h # Exactly one state advance per real question, including retries.
        # Reuse existing Adam; override only the cached scalar-policy gradient.
        super().update(None,labels,mask)
        self.baseline=.98*self.baseline+.02*reward
        return action,reward,float(prob[index])
    def loss_grad(self,_x,action,mask):
        logits,h,cache,weight=self.cached;W,b,V,a=self.p
        d=(sigmoid(logits)-action)*mask*weight
        grads=[np.zeros_like(W),np.zeros_like(b),h.T@d,d.sum(0)];dh=d@V.T
        for z,hn in reversed(cache):
            dz=dh*(1-hn*hn);grads[0]+=z.T@dz;grads[1]+=dz.sum(0);dh=(dz@W.T)[:,1:]
        return 0.,grads
    def update(self,*_):raise RuntimeError('Use scalar reward attempt; teacher targets forbidden')

def probe(net,n,values):
    clone=copy.deepcopy(net);rows=[]
    for value in values:
        data=word(value,n,1);bits='01'+word(0,1,1)+data;expected=codec.calc('echo',[data])
        answer,prob=clone.predict(bits)
        rows.append({'value':value,'bits':bits,'expected':expected,'predicted':answer,'correct':answer==expected,'expected_policy_probability':float(prob[ACTIONS.index(expected)])})
    return rows

def guards():
    t=Teacher();assert t.ask(0)==('010000','00');assert t.ask(1)==('010010','10')
    t.upgrade()
    try:t.ask(0)
    except AssertionError:pass
    else:raise AssertionError('invalid first promoted word accepted')
    t=Teacher();t.upgrade();assert t.ask(1)==('0100010','010')
    assert t.ask(0)[1]=='000'
    try:t.upgrade()
    except ValueError:pass
    else:raise AssertionError('unexpected further transition')
    p=Policy(5);before=p.hidden.copy();p.predict('010010');assert not np.array_equal(before,p.hidden)
    # Probability sums, variable output lengths and finite rewards are not a grammar hint.
    assert len(ACTIONS)==12 and abs(p.distribution(np.zeros((1,4))).sum()-1)<1e-12
    return {'status':'passed','first_trigger_required':True,'single_upgrade':True,'persistent_hidden_step':True,'actions':len(ACTIONS)}

def run(seed):
    net=Policy(seed);teacher=Teacher();rng=np.random.default_rng(seed+9100);trace=[];history=[];start=time.perf_counter()
    summary={'seed':seed,'parameters':sum(p.size for p in net.p),'stages':[]}
    for label,values,limit in [('low_all',[0,1],6000),('high_train',[1,0,2],10000)]:
        if label=='high_train':
            if not summary['stages'][-1]['mastered']:break
            teacher.upgrade()
            summary['zero_shot_after_upgrade']=probe(net,2,[1,0,2,3])
        index=0;attempts=0;stable=0;mastered=False
        while attempts<limit:
            value=values[index];bits,expected=teacher.ask(value)
            answer,reward,prob=net.attempt(bits,lambda a: a==expected,rng)
            trace.append({'stage':label,'n':teacher.n,'value':value,'bits':bits,'answer':answer,'reward':int(reward),'expected_for_audit':expected,'hidden_reset_count':net.hidden_resets})
            attempts+=1
            if reward:
                index=(index+1)%len(values)
                if index==0:
                    tested=probe(net,teacher.n,values)
                    good=all(r['correct'] and r['expected_policy_probability']>=.90 for r in tested)
                    stable=stable+1 if good else 0
                    if attempts%100<10:history.append({'stage':label,'attempts':attempts,'probe':tested})
                    if stable>=2:mastered=True;break
            if time.perf_counter()-start>90:break
        folder=OUT/f'seed{seed}-{label}';folder.mkdir()
        np.savez(folder/'state.npz',**{f'p{i}':p for i,p in enumerate(net.p)},hidden=net.hidden)
        summary['stages'].append({'stage':label,'n':teacher.n,'attempts':attempts,'correct_attempts':sum(r['reward'] for r in trace if r['stage']==label),'mastered':mastered,'trained_values':values,'probe':probe(net,teacher.n,values)})
        if not mastered:break
    summary['seconds']=time.perf_counter()-start;summary['promotions']=teacher.promotions;summary['hidden_resets']=net.hidden_resets
    if teacher.n==2:summary['heldout_value3']=probe(net,2,[3])[0]
    # Live curriculum invariants, including wrong-answer repetition.
    for a,b in zip(trace,trace[1:]):
        assert b['n']>=a['n']
        if not a['reward']:assert a['bits']==b['bits'],'wrong question was not repeated'
    high=[r for r in trace if r['n']==2]
    if high:assert high[0]['value']==1 and high[0]['bits'][5]=='1' and high[0]['bits'][6]=='0'
    assert all(r['value']!=3 for r in trace if r['n']==2)
    assert net.hidden_resets==1
    (OUT/f'trace-seed{seed}.json').write_text(json.dumps(trace))
    (OUT/f'probes-seed{seed}.json').write_text(json.dumps(history))
    (OUT/f'compact-seed{seed}.json').write_text(json.dumps(summary,indent=2));return summary

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'plan.json').exists():raise RuntimeError('No overwrite')
    plan={'source_profile':'Paper4 chapter5 Q1-Q3 initial Echo; teacher reuses word/tokenize/calc. No CONFIG/version lesson.','seeds':[101,202],'network':'RNN16,356params,random initialization','input':'Only01+op00+rawdata; no separator, width, version, cut labels or correct answer fed','learning':'REINFORCE scalar exact-correct reward, sampled reply, EMA baseline,epsilon.15; existing Adam. No correct-label gradient.','reply_space':'All2bit and3bit strings,12possibleactions; maximum reply length is an explicit architectural prior.','curriculum':'Low2questions all taught; wrong repeats until sampled correct. After two exhaustive greedy cycles withtarget probability>=.9, data_n1->2 once. First highdata010; train highvalues1,0,2; value3 reserved.','state':'One live state per seed, never reset at questions/retries/promotion; gradients truncate perquestion, weights+hidden carried. Probe usescopies, no updates/changes to live state.','limits':'Two independent fresh-seed runs, eachonecontinuoussession; onlyEcho/data-branch promotion, not operator/layer/version acquisition. One heldoutvalue is a minimal test, not broadgeneralization.','stops':'6000low/10000high attempts or90sec perrun; never promote unless lowmastered; no heldout-based selection.'}
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2));check=guards();(OUT/'guards.json').write_text(json.dumps(check,indent=2))
    results=[run(seed) for seed in plan['seeds']]
    s={'plan':plan,'guards':check,'runs':results,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/'compact.json').write_text(json.dumps(s,indent=2));(ROOT/'sle-research-review/paper4-echo-result.json').write_text(json.dumps(s,indent=2));print(json.dumps(results))
if __name__=='__main__':main()
