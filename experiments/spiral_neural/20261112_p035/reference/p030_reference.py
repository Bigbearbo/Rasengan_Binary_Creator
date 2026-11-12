"""P030 pilot: binary-only growing MLP, continuous Echo/Neg/Zero/delayed END."""
import os,sys
sys.dont_write_bytecode=True
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import hashlib,json,time
from pathlib import Path
from dataclasses import dataclass,asdict
import numpy as np

ROOT=Path('D:/Codex用')
OUT=ROOT/'work/sle-research-review/p030-binary-continual-20261112'
SEEDS=[101,202,303]
CAP=3000

@dataclass(frozen=True)
class Profile:
    name:str
    nop:int
    nd:int
    ops:tuple
    end:bool=False
    new:int|None=None
    @property
    def qlen(self):return 2+self.nop+1+self.nd+1+(self.nop+1 if self.end else 0)
    @property
    def context(self):return self.qlen+self.nd+1
    @property
    def reserved(self):return ['1'*self.nop+'0'] if self.end else []

PHASES=[Profile('0_echo_n1',1,1,(0,)),Profile('1a_echo_n2',1,2,(0,)),Profile('1b_echo_n3',1,3,(0,)),
        Profile('2a_echo_op2',2,3,(0,)),Profile('2b_add_neg',2,3,(0,1),new=1),
        Profile('2c_add_zero',2,3,(0,1,2),new=2),Profile('3_enable_end',2,3,(0,1,2),True)]
REGISTRY={p.name:p for p in PHASES}
NAMES={0:'echo',1:'neg',2:'zero'}

def answer(op,nd,value):
    data=format(value,f'0{nd}b')+'0'
    if op==0:return data
    if op==1:return ''.join('1' if b=='0' else '0' for b in data[:-1])+'0'
    if op==2:return '0'*(nd+1)
    raise ValueError('Unknown operation')

def encode(p,op,value):
    if op not in p.ops or not 0<=value<2**p.nd:raise ValueError('Unknown op/value')
    code=format(op,f'0{p.nop}b')+'0'
    if code in p.reserved:raise ValueError('Reserved END cannot be ordinary operator')
    return '01'+code+format(value,f'0{p.nd}b')+'0'+('1'*p.nop+'0' if p.end else '')

def parse(name,raw):
    if name not in REGISTRY:raise ValueError('Unknown grammar version')
    p=REGISTRY[name]
    if len(raw)!=p.qlen or set(raw)-set('01') or not raw.startswith('01'):raise ValueError('Invalid frame')
    i=2;opword=raw[i:i+p.nop+1];i+=p.nop+1;data=raw[i:i+p.nd+1];i+=p.nd+1
    if not opword.endswith('0') or not data.endswith('0'):raise ValueError('Illegal syntax tail')
    op=int(opword[:-1],2);value=int(data[:-1],2)
    if op not in p.ops or opword in p.reserved:raise ValueError('Unknown/reserved operator')
    if p.end and raw[i:]!='1'*p.nop+'0':raise ValueError('Missing/wrong END')
    if not p.end and i!=len(raw):raise ValueError('Unexpected END')
    return op,value

def split(p):
    if p.nd<=2:return list(range(2**p.nd)),list(range(2**p.nd)),[]
    return [0,1,2,3,4,7],[5],[6]

class Model:
    def __init__(self,seed,L=8,H=64):
        self.L=L;self.H=H;self.t=0;self.seed=seed;self.growth_rng=np.random.default_rng(seed+73000)
        rng=np.random.default_rng(seed)
        self.p=[rng.normal(0,.2,(2*L,H)).astype(np.float32),np.zeros(H,np.float32),
                rng.normal(0,.15,(H,3)).astype(np.float32),np.zeros(3,np.float32)]
        self.m=[np.zeros_like(p) for p in self.p];self.v=[p.copy() for p in self.m]
        self.birth=[np.zeros(p.shape,np.int64) for p in self.p]
        self.events=[];self.train_macs=0;self.inference_macs=0;self.inference_calls=0
    @property
    def parameters(self):return sum(p.size for p in self.p)
    def state(self):
        return {f'{label}{i}':p.copy() for label,arr in [('p',self.p),('m',self.m),('v',self.v),('birth',self.birth)] for i,p in enumerate(arr)}|{
            't':np.array(self.t),'L':np.array(self.L),'H':np.array(self.H),'growth_rng':np.array(json.dumps(self.growth_rng.bit_generator.state,sort_keys=True))}
    def forward(self,text,training=False):
        if not text or set(text)-set('01') or len(text)>self.L:raise ValueError('Only actual binary prefix within context accepted')
        slots=np.zeros((self.L,2),dtype=self.p[0].dtype)
        for i,bit in enumerate(text):slots[i,int(bit)]=1
        x=slots.reshape(1,-1);h=np.tanh(x@self.p[0]+self.p[1]);z=(h@self.p[2]+self.p[3])[0]
        if not training:
            self.inference_calls+=1;self.inference_macs+=2*self.L*self.H+3*self.H
        return x,h,z
    def loss_grad(self,text,target):
        x,h,z=self.forward(text,True);zz=z.astype(np.float64);lp=zz-np.logaddexp.reduce(zz);prob=np.exp(lp)
        index='01S'.index(target);d=prob.copy();d[index]-=1;d=d.astype(h.dtype)[None,:]
        dz=(d@self.p[2].T)*(1-h*h)
        return -float(lp[index]),[x.T@dz,dz[0],h.T@d,d[0]],'01S'[int(z.argmax())]
    def step(self,text,target):
        loss,g,pred=self.loss_grad(text,target);norm=np.sqrt(sum(float((q*q).sum()) for q in g));scale=min(1.,1/max(norm,1e-12));self.t+=1
        for i,grad in enumerate(g):
            grad*=scale;self.m[i]=.9*self.m[i]+.1*grad;self.v[i]=.999*self.v[i]+.001*grad*grad
            age=self.t-self.birth[i]
            self.p[i]-=.003*(self.m[i]/(1-np.power(.9,age)))/(np.sqrt(self.v[i]/(1-np.power(.999,age)))+1e-8)
        self.train_macs+=4*self.L*self.H+9*self.H
        return pred,loss
    def lesson(self,q,a):
        predictions='';loss=0.
        for i,target in enumerate(a+'S'):
            pred,l=self.step(q+a[:i],target);predictions+=pred;loss+=l
        return predictions,loss
    def generate(self,q):
        tokens=''
        for _ in range(8):
            if len(q+tokens)>self.L:return tokens,True
            token='01S'[int(self.forward(q+tokens)[2].argmax())];tokens+=token
            if token=='S':return tokens,False
        return tokens,False
    def grow(self,L,H,reason):
        if L<self.L or H<self.H:raise ValueError('Growth never shrinks')
        if (L,H)==(self.L,self.H):return
        oldL,oldH=self.L,self.H;oldp=[p.copy() for p in self.p];oldm=[p.copy() for p in self.m];oldv=[p.copy() for p in self.v];oldbirth=[p.copy() for p in self.birth]
        tests=['0','1','010000','010010','01000000'];before=[self.forward(s)[2].copy() for s in tests];old_count=self.parameters
        shapes=[(2*L,H),(H,),(H,3),(3,)]
        pp=[self.growth_rng.normal(0,.2,shapes[0]).astype(np.float32),np.zeros(H,np.float32),np.zeros((H,3),np.float32),np.zeros(3,np.float32)]
        mm=[np.zeros(shape,np.float32) for shape in shapes];vv=[q.copy() for q in mm];birth=[np.full(shape,self.t,np.int64) for shape in shapes]
        slices=[(slice(0,2*oldL),slice(0,oldH)),(slice(0,oldH),),(slice(0,oldH),slice(None)),(slice(None),)]
        for destination,source in [(pp,oldp),(mm,oldm),(vv,oldv),(birth,oldbirth)]:
            for i,sl in enumerate(slices):destination[i][sl]=source[i];assert np.array_equal(destination[i][sl],source[i])
        self.L=L;self.H=H;self.p=pp;self.m=mm;self.v=vv;self.birth=birth
        error=max(float(np.max(abs(a-self.forward(s)[2]))) for s,a in zip(tests,before))
        assert error<2e-6
        self.events.append({'at_update':self.t,'reason':reason,'from':[oldL,oldH,old_count],'to':[L,H,self.parameters],
                            'old_parameter_moments_birth_preserved':True,'same_old_prefix_max_logit_difference':error})

def metrics(net,p,values,ops=None):
    saved=net.state();records=[];byop={};total_ce=targets=0;loss=0.
    for op in p.ops if ops is None else ops:
        whole=stop=overflow=0;bit=np.zeros(p.nd+1,dtype=int);tf_correct=0;tc=0
        for value in values:
            q=encode(p,op,value);a=answer(op,p.nd,value);tokens,over=net.generate(q)
            stopped=tokens.endswith('S');actual=tokens[:-1] if stopped else tokens
            correct=tokens==a+'S' and not over;timing=stopped and len(actual)==len(a)
            whole+=correct;stop+=timing;overflow+=over;bit+=[i<len(actual) and b==actual[i] for i,b in enumerate(a)]
            for i,target in enumerate(a+'S'):
                z=net.forward(q+a[:i])[2].astype(np.float64);lp=z-np.logaddexp.reduce(z);loss-=float(lp['01S'.index(target)])
                tf_correct+='01S'[int(z.argmax())]==target;tc+=1
            records.append([op,value,tokens,over,correct,timing])
        byop[NAMES[op]]={'whole':int(whole),'stop':int(stop),'total':len(values),'overflow':int(overflow),
                        'bit_correct':bit.tolist(),'teacher_correct':int(tf_correct),'teacher_targets':tc}
        total_ce+=tf_correct;targets+=tc
    assert equal_state(saved,net.state())
    return {'by_op':byop,'ce_mean':loss/targets if targets else None,'teacher_correct':int(total_ce),'teacher_targets':targets,'records':records}

def small(m):return {k:v for k,v in m.items() if k!='records'}
def equal_state(a,b):return a.keys()==b.keys() and all(np.array_equal(v,b[k]) for k,v in a.items())
def passed(train,val):
    return all(m['whole']>=int(np.ceil(.95*m['total'])) for m in train['by_op'].values()) and all(
        m['whole']>=int(np.ceil(.95*m['total'])) and m['stop']>=int(np.ceil(.99*m['total'])) for m in val['by_op'].values())

class Schedule:
    def __init__(self,p,seed):
        self.p=p;self.rng=np.random.default_rng(seed+51000);self.trains=split(p)[0]
        self.value_rng={op:np.random.default_rng(seed+52000+op) for op in p.ops};self.queues={op:[] for op in p.ops};self.ops=[];self.old_cursor=0;self.all_cursor=0
    def next(self):
        if not self.ops:
            if self.p.new is not None:
                known=[op for op in self.p.ops if op!=self.p.new];seq=[self.p.new]*7
                for _ in range(3):seq.append(known[self.old_cursor%len(known)]);self.old_cursor+=1
                self.ops=self.rng.permutation(seq).tolist()
            else:
                self.ops=self.rng.permutation(self.p.ops).tolist()
        op=int(self.ops.pop(0))
        if not self.queues[op]:self.queues[op]=self.value_rng[op].permutation(self.trains).tolist()
        return op,int(self.queues[op].pop(0))

def checks():
    roundtrips=0;labels=0
    for p in PHASES:
        seen={}
        for op in p.ops:
            for value in range(2**p.nd):
                q=encode(p,op,value);a=answer(op,p.nd,value);assert parse(p.name,q)==(op,value)
                assert encode(p,*parse(p.name,q))==q and set(q)<=set('01') and len(q+a)==p.context<=16
                for i,target in enumerate(a+'S'):
                    prefix=q+a[:i];assert prefix not in seen or seen[prefix]==target;seen[prefix]=target;labels+=1
                roundtrips+=1
        if p.end:
            try:parse(p.name,encode(p,p.ops[0],0)[:-p.nop-1])
            except ValueError:pass
            else:raise AssertionError('Missing END accepted')
        sch=Schedule(p,9)
        if p.new is not None:
            for _ in range(3):assert sum(sch.next()[0]==p.new for _ in range(10))==7
    fixtures=[(Profile('q1',1,1,(0,)),0,0,'010000','00'),(Profile('q2',1,1,(0,)),0,1,'010010','10'),
              (Profile('q3',1,2,(0,)),0,1,'0100010','010'),(Profile('q4',2,2,(0,1,2)),1,2,'01010100','010'),
              (Profile('q5',2,2,(0,1,2)),2,1,'01100010','000'),(Profile('q6',2,2,(0,1,2),True),2,1,'01100010110','000')]
    for p,op,v,q,a in fixtures:assert encode(p,op,v)==q and answer(op,p.nd,v)==a
    p=Profile('collision',2,2,(0,1,2),True);q=encode(p,0,3);assert q.endswith('110110') and answer(0,2,3)=='110'
    try:parse('unknown','010000')
    except ValueError:pass
    else:raise AssertionError('Unknown profile accepted')
    net=Model(8);net.lesson('010000','00');saved=net.state();net.grow(10,66,'check')
    assert net.t==int(saved['t']) and net.birth[0][-1,-1]==net.t and net.birth[0][0,0]==0
    net.lesson('0100010','010');assert net.t==7
    g=Model(8);g.p=[p.astype(np.float64) for p in g.p];finite=[];rng=np.random.default_rng(7)
    for target in '01S':
        loss,grads,_=g.loss_grad('010010',target);maximum=0.;count=0
        for par,grad in zip(g.p,grads):
            for i in rng.choice(par.size,min(8,par.size),replace=False):
                old=par.flat[i];par.flat[i]=old+1e-5;plus=g.loss_grad('010010',target)[0];par.flat[i]=old-1e-5;minus=g.loss_grad('010010',target)[0];par.flat[i]=old
                error=abs((plus-minus)/2e-5-grad.flat[i]);assert error<1e-7;maximum=max(maximum,error);count+=1
        finite.append({'target':target,'checked':count,'max_error':maximum})
    g=Model(1);g.p[2][:]=0;g.p[3][:]=[50,0,0];tokens,over=g.generate('010000');assert over and not tokens.endswith('S')
    return {'roundtrips':roundtrips,'consistent_teacher_labels':labels,'Q1_Q6_fixtures':True,'data_END_collision_valid':True,
            'missing_END_and_unknown_profile_rejected':True,'pure_binary_context_overflow':True,
            'growth_old_weights_moments_birth_and_function_preserved':True,'new_parameter_age_starts_fresh':True,
            'per10_new_task70percent':True,'finite_differences':finite}

def execute_stage(net,p,policy,seed,folder,replay=False):
    # Context changes are capacity changes, not extra input features.
    if p.context>net.L:
        net.grow(p.context,net.H+(p.context-net.L) if policy=='dynamic' else net.H,'context_requirement')
    initial=net.state();start_events=len(net.events);start_t=net.t
    train_values,val_values,test_values=split(p);schedule=Schedule(p,seed);trace=[];curve=[];stable=0;stale=0;best=-1;grown=False;unique=set();start=time.perf_counter()
    def measure(exposure):
        train=metrics(net,p,train_values);val=train if p.nd<=2 else metrics(net,p,val_values)
        row={'presentations':exposure,'updates':net.t,'L':net.L,'H':net.H,'parameters':net.parameters,'train':small(train),'validation':small(val),'passed':passed(train,val)}
        curve.append(row);return row
    measure(0);reason='presentation_cap'
    points={0,25,50,100,192,384,768,1536,CAP};roundsize=len(train_values)*len(p.ops)
    for exposure in range(1,CAP+1):
        op,value=schedule.next();q=encode(p,op,value);a=answer(op,p.nd,value)
        pred,loss=net.lesson(q,a);trace.append([op,value,pred]);unique.add((op,value))
        if exposure in points or exposure%roundsize==0:
            row=measure(exposure);stable=stable+1 if row['passed'] else 0
            if stable>=3:reason='three_train_validation_passes';break
            score=sum(m['whole'] for data in [row['train'],row['validation']] for m in data['by_op'].values())
            if score>best:best=score;stale=0
            else:stale+=1
            if policy=='bottleneck' and exposure>=192 and stale>=3 and not grown and net.H<72:
                net.grow(net.L,min(72,net.H+4),'predeclared_train_validation_plateau');grown=True;stale=0
        if not replay and time.perf_counter()-start>120:reason='wall_time_cap';break
    seconds=time.perf_counter()-start
    if curve[-1]['presentations']!=len(trace):measure(len(trace))
    test=metrics(net,p,test_values) if test_values else None
    result={'profile':asdict(p),'presentations':len(trace),'token_updates':net.t-start_t,'global_updates':net.t,
            'parameters':net.parameters,'L':net.L,'H':net.H,'unique_train_questions':len(unique),'unique_possible_train':roundsize,
            'stop_reason':reason,'first_pass':next((r['presentations'] for r in curve if r['presentations'] and r['passed']),None),
            'confirmed_points':[r['presentations'] for r in curve[-3:]] if stable>=3 else None,
            'train_validation':curve[-1],'final_test':None if test is None else small(test),'seconds_training_and_probes':seconds}
    if not replay:
        folder.mkdir();np.savez(folder/'state.npz',**net.state())
        (folder/'trace.json').write_text(json.dumps(trace));(folder/'curve.json').write_text(json.dumps(curve,indent=2))
        (folder/'test.json').write_text(json.dumps(test,indent=2));(folder/'summary.json').write_text(json.dumps(result,indent=2))
    return result,trace,curve

def run(seed,policy,start_profile=None,shape=None):
    scratch=start_profile is not None;name=(f'scratch_{start_profile.name}' if scratch else policy)+f'-{seed}'
    folder=OUT/name;folder.mkdir()
    net=Model(seed,*(shape or (8,64)))
    if policy=='fixed' and not scratch:net.grow(16,72,'fixed_capacity_before_training')
    initial_shape=(net.L,net.H);stages=[];records=[];control_requests=[];cost_start=(net.train_macs,net.inference_macs)
    for i,p in enumerate([start_profile] if scratch else PHASES):
        result,trace,curve=execute_stage(net,p,'fixed' if scratch else policy,seed+100*i,folder/p.name)
        stages.append(result);records.append((p,result,trace,curve))
        print(json.dumps({'run':name,'phase':p.name,'presentations':result['presentations'],'parameters':net.parameters,
                          'stop_reason':result['stop_reason'],'test':result['final_test']}),flush=True)
        if not scratch and policy=='dynamic' and p.name in ['2a_echo_op2','2b_add_neg','3_enable_end']:
            control_requests.append((p,(result['L'],result['H']),seed+100*i))
        if result['stop_reason']!='three_train_validation_passes':break
    final=net.state();np.savez(folder/'final-state.npz',**final)
    # Exact replay of all actual updates, measurements, capacity decisions and Adam ages.
    replay=Model(seed,*initial_shape) if scratch else Model(seed)
    if policy=='fixed' and not scratch:replay.grow(16,72,'fixed_capacity_before_training')
    for i,(p,result,trace,curve) in enumerate(records):
        rr,tt,cc=execute_stage(replay,p,'fixed' if scratch else policy,seed+100*i,folder/p.name,True)
        assert tt==trace and cc==curve
        assert rr['stop_reason']==result['stop_reason'] and rr['final_test']==result['final_test']
    assert equal_state(final,replay.state()) and net.events==replay.events
    result={'run':name,'policy':policy,'seed':seed,'scratch':scratch,'stages':stages,'reached_END':stages[-1]['profile']['end'],
            'passed_END':stages[-1]['profile']['end'] and stages[-1]['stop_reason']=='three_train_validation_passes',
            'total_presentations':sum(r['presentations'] for r in stages),'total_updates':net.t,'parameters':net.parameters,
            'train_dense_MACs':net.train_macs,'inference_dense_MACs':net.inference_macs,'inference_calls':net.inference_calls,
            'parameter_optimizer_arrays_bytes':sum(a.nbytes for arrays in [net.p,net.m,net.v,net.birth] for a in arrays),
            'growth_events':net.events,'all_trace_measurement_growth_and_optimizer_replay_equal':True}
    (folder/'summary.json').write_text(json.dumps(result,indent=2));return result,control_requests

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest={'profiles':[asdict(p)|{'Q_length':p.qlen,'context':p.context,'reserved_END_codes':p.reserved,'split':split(p)} for p in PHASES],
              'input_alphabet':['0','1'],'output_alphabet':['0','1','STOP'],'max_context':16,'source_commit':'ad6281c'}
    plan={'id':'P030-first-pilot','manifest':manifest,'seeds':SEEDS,'arms':['dynamic','fixed','bottleneck'],
          'scope':'Only planned0-3,7subphases. NoONE/CUT/AND/twolayer/versions yet. New student, no claimed P029 weight transplant.',
          'budget':'3000presentations/120sec perphase;3train+val passes perop95percent,STOP99percent. Test onlyafterstop.',
          'optimizer':'Adam.003 norm1clip; globalsteps preserved; entrybirthstep preserves oldage and gives newentries freshbiascorrection.',
          'source_sha':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'numpy':np.__version__,'python':sys.version}
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    (OUT/'lesson-manifest.json').write_text(json.dumps(manifest,indent=2))
    validation=checks();(OUT/'checks.json').write_text(json.dumps(validation,indent=2))
    results=[];controls=[]
    for policy in plan['arms']:
        for seed in SEEDS:
            result,requests=run(seed,policy);results.append(result)
            # Keep the exact schedule seed of the continuous phase for controls.
            if policy=='dynamic':controls.extend((seed,p,shape,schedule_seed) for p,shape,schedule_seed in requests)
            (OUT/'progress.json').write_text(json.dumps(results,indent=2))
    control_results=[]
    for seed,p,shape,schedule_seed in controls:
        # Scratch initial seed remains seed; run stage uses seed+100*0. Record
        # schedule equality explicitly by temporarily passing a separate schedule seed.
        result,_=run_scratch(seed,p,shape,schedule_seed);control_results.append(result)
        (OUT/'control-progress.json').write_text(json.dumps(control_results,indent=2))
    (OUT/'compact.json').write_text(json.dumps({'plan':plan,'checks':validation,'runs':results,'scratch_controls':control_results},indent=2))

def run_scratch(seed,p,shape,schedule_seed):
    folder=OUT/f'scratch_{p.name}-{seed}';folder.mkdir();net=Model(seed,*shape)
    result,trace,curve=execute_stage(net,p,'fixed',schedule_seed,folder/p.name)
    replay=Model(seed,*shape);rr,tt,cc=execute_stage(replay,p,'fixed',schedule_seed,folder/p.name,True)
    assert trace==tt and curve==cc and equal_state(net.state(),replay.state()) and result['final_test']==rr['final_test']
    summary={'seed':seed,'profile':p.name,'L':shape[0],'H':shape[1],'schedule_seed':schedule_seed,'stage':result,
             'all_trace_measurement_and_optimizer_replay_equal':True,'train_dense_MACs':net.train_macs}
    (folder/'summary.json').write_text(json.dumps(summary,indent=2));return summary,None

if __name__=='__main__':main()
