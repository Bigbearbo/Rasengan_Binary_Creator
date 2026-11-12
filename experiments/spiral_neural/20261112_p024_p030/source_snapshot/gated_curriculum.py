"""Paired raw-bit RNN/LSTM curriculum; NumPy only, no parser features."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import hashlib,json,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'work/spiral-blank-model/gated-curriculum-20261111'

def encode(frames):
    bits='';target=[]
    for f in frames:
        n=f['width'];op=f['op'];d=f['data']
        bits+='010010'+format(op,f'0{n}b')+'0'+format(d,'03b')+'0'
        target.extend([(v>>i)&1 for v in [op,d] for i in [2,1,0]])
    return bits,target
def sample(rng,count,high):
    trans=int(rng.integers(1,count)) if high else count
    frames=[]
    for i in range(count):
        n=2 if i<trans else 3
        op=int(rng.integers(1,4)) if n==2 else (int(rng.choice([1,3,5,7])) if i==trans else int(rng.integers(8)))
        frames.append({'width':n,'op':op,'data':int(rng.integers(8))})
    bits,target=encode(frames)
    return bits,target,frames
def held(bits):return int(hashlib.sha256(bits.encode()).hexdigest()[:8],16)%5==0
def batch(rng,count,high,size=32):
    rows=[];length=None
    while len(rows)<size:
        row=sample(rng,count,high)
        if held(row[0]):continue
        if length is None:length=len(row[0])
        if len(row[0])==length:rows.append(row)
    x=np.array([[int(c) for c in r[0]] for r in rows],np.float32)[:,:,None]
    y=np.zeros((size,24),np.float32);mask=np.zeros_like(y)
    for i,row in enumerate(rows):y[i,:len(row[1])]=row[1];mask[i,:len(row[1])]=1
    return x,y,mask
def sigmoid(x):return 1/(1+np.exp(-np.clip(x,-30,30)))
class Net:
    def __init__(self,kind,seed):
        self.kind=kind;self.h=34 if kind=='lstm' else 64;rng=np.random.default_rng(seed);h=self.h
        self.p=[rng.normal(0,1/np.sqrt(h),(h+1,h*(4 if kind=='lstm' else 1))).astype(np.float32),np.zeros(h*(4 if kind=='lstm' else 1),np.float32),rng.normal(0,.1,(h,24)).astype(np.float32),np.zeros(24,np.float32)]
        if kind=='lstm':self.p[1][h:2*h]=1
        self.m=[np.zeros_like(p) for p in self.p];self.v=[p.copy() for p in self.m];self.steps=0
    def forward(self,x):
        W,b,V,a=self.p;h=np.zeros((len(x),self.h),dtype=W.dtype);c=h.copy();cache=[]
        for t in range(x.shape[1]):
            z=np.concatenate([x[:,t],h],axis=1)
            if self.kind=='lstm':
                g=z@W+b;i,f,o=sigmoid(g[:,:self.h]),sigmoid(g[:,self.h:2*self.h]),sigmoid(g[:,2*self.h:3*self.h]);q=np.tanh(g[:,3*self.h:]);cp=c;c=f*c+i*q;h=o*np.tanh(c);cache.append((z,i,f,o,q,cp,c))
            else:h=np.tanh(z@W+b);cache.append((z,h))
        return h@V+a,(h,cache)
    def loss_grad(self,x,y,mask):
        logits,(h,cache)=self.forward(x);den=mask.sum();loss=float(((np.logaddexp(0,logits)-y*logits)*mask).sum()/den)
        d=(sigmoid(logits)-y)*mask/den;W,b,V,a=self.p
        grads=[np.zeros_like(W),np.zeros_like(b),h.T@d,d.sum(0)];dh=d@V.T;dc=np.zeros_like(dh)
        for item in reversed(cache):
            if self.kind=='lstm':
                z,i,f,o,q,cp,c=item;tc=np.tanh(c);do=dh*tc;dc=dc+dh*o*(1-tc*tc)
                di=dc*q;df=dc*cp;dq=dc*i;dc=dc*f
                dz=np.concatenate([di*i*(1-i),df*f*(1-f),do*o*(1-o),dq*(1-q*q)],axis=1)
            else:z,hn=item;dz=dh*(1-hn*hn)
            grads[0]+=z.T@dz;grads[1]+=dz.sum(0);dh=(dz@W.T)[:,1:]
        return loss,grads
    def update(self,x,y,mask):
        loss,g=self.loss_grad(x,y,mask);norm=np.sqrt(sum(float((p*p).sum()) for p in g));scale=min(1,1/max(norm,1e-12));self.steps+=1
        for i,grad in enumerate(g):
            grad*=scale;self.m[i]=.9*self.m[i]+.1*grad;self.v[i]=.999*self.v[i]+.001*grad*grad
            self.p[i]-=.003*(self.m[i]/(1-.9**self.steps))/(np.sqrt(self.v[i]/(1-.999**self.steps))+1e-8)
        return loss

def gradient_check():
    checks=[];rng=np.random.default_rng(42)
    for kind in ['rnn','lstm']:
        net=Net(kind,7);net.p=[p.astype(np.float64) for p in net.p]
        x=rng.integers(2,size=(2,7,1)).astype(float);y=rng.integers(2,size=(2,24)).astype(float);mask=np.ones_like(y)
        _,g=net.loss_grad(x,y,mask);maxerr=0
        for j,p in enumerate(net.p):
            ids=rng.choice(p.size,size=min(8,p.size),replace=False)
            for idx in ids:
                old=p.flat[idx];p.flat[idx]=old+1e-5;plus=net.loss_grad(x,y,mask)[0];p.flat[idx]=old-1e-5;minus=net.loss_grad(x,y,mask)[0];p.flat[idx]=old
                numeric=(plus-minus)/2e-5;analytic=g[j].flat[idx];err=abs(numeric-analytic);assert err<1e-7,(kind,j,int(idx),numeric,analytic);maxerr=max(maxerr,err)
        checks.append({'kind':kind,'probed_parameters':sum(min(8,p.size) for p in net.p),'max_absolute_error':maxerr})
    return checks
def tests():
    source=OUT.parent/'raw-full-episode-20261111/seed101-adapt0/predictions.json';raw=json.loads(source.read_text());result={}
    for name,rows in raw.items():
        result[name]=[(r['bits'],encode(r['frames'])[1],r['frames']) for r in rows]
    return result
def evaluate(net,ts):
    scores={};predictions={}
    for name,rows in ts.items():
        pred=[];labels=[];records=[]
        for bits,target,frames in rows:
            x=np.array([[[int(c)] for c in bits]],np.float32);p=(net.forward(x)[0][0]>=0).astype(int)
            pred.append(p);labels.append(target);records.append({'bits':bits,'frames':frames,'predicted':p.tolist()})
        p=np.array(pred);y=np.array(labels)
        scores[name]={'whole_exact':float((p==y).all(1).mean()),'bit_accuracy':float((p==y).mean()),'frame_exact':[float((p[:,6*i:6*i+6]==y[:,6*i:6*i+6]).all(1).mean()) for i in range(4)],'episodes':len(rows)};predictions[name]=records
    return scores,predictions
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'plan.json').exists():raise RuntimeError('No overwrite')
    checks=gradient_check();(OUT/'gradient-check.json').write_text(json.dumps(checks,indent=2))
    plan={'models':{'rnn':5784,'lstm':5736},'seeds':[101,202],'curriculum':[[1,600],[2,1000],[4,2000]],'adapt_updates':500,'adapt_mix':'3 promoted batches then1 old batch, repeated125times;375promoted+125old','batch':32,'learning_rate':.003,'inputs':'raw 0/1 only, episode reset/end known, no boundaries or length metadata','targets':'final decoded operator/data of 1,2,4frames; unused output positions masked in loss only','test':'Same128old+128promoted heldout sequences as previous stricter pilot, no test-based selection','time_cap_per_training_block_seconds':120,'purpose':'Fixed new paired curriculum comparison; does not separately isolate curriculum effect from prior trial.'}
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2));ts=tests();records=[];start=time.perf_counter()
    for seed in plan['seeds']:
        for kind in ['rnn','lstm']:
            net=Net(kind,seed);rng=np.random.default_rng(seed+1000)
            for count,updates in plan['curriculum']+[(4,500)]:
                adaptation=updates==500;blockstart=time.perf_counter()
                for step in range(updates):
                    high=adaptation and step%4!=3;net.update(*batch(rng,count,high))
                    if time.perf_counter()-blockstart>120:raise TimeoutError('Block limit')
                label='adapt' if adaptation else f'old{count}'
                folder=OUT/f'{kind}-{seed}-{label}';folder.mkdir();np.savez(folder/'weights.npz',**{f'p{i}':p for i,p in enumerate(net.p)})
                z=np.load(folder/'weights.npz');assert all(np.array_equal(p,z[f'p{i}']) for i,p in enumerate(net.p))
                scores,raw=evaluate(net,ts);(folder/'predictions.json').write_text(json.dumps(raw))
                records.append({'kind':kind,'seed':seed,'stage':label,'updates_total':net.steps,'scores':scores});(OUT/'progress.json').write_text(json.dumps(records,indent=2))
    s={'status':'completed','plan':plan,'gradient_checks':checks,'seconds':time.perf_counter()-start,'records':records,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/'compact.json').write_text(json.dumps(s,indent=2));(ROOT/'gated-curriculum-result.json').write_text(json.dumps(s,indent=2));print(json.dumps({'status':s['status'],'seconds':s['seconds'],'records':[r for r in records if r['stage'] in ['old4','adapt']]}))
if __name__=='__main__':main()
