"""P025B: direct fixed-window MLP, all question|prefix positions visible at once."""
from _archive_paths import ARCHIVE_ROOT, REPO_ROOT, SRC_DIR, RUNS_ROOT, PLOTS_ROOT
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import hashlib,json
from pathlib import Path
import numpy as np
import echo_prefix_separator as protocol

class Direct(protocol.Prefix):
    def __init__(self,seed):
        rng=np.random.default_rng(seed)
        self.p=[rng.normal(0,.2,(69,16)).astype(np.float32),np.zeros(16,np.float32),
                rng.normal(0,.15,(16,3)).astype(np.float32),np.zeros(3,np.float32)]
        self.m=[np.zeros_like(p) for p in self.p];self.v=[p.copy() for p in self.m]
        self.hidden=np.zeros((1,16),np.float32);self.steps=0;self.baseline=.2

    def read(self,text):
        assert len(text)<=23
        W,b,_,_=self.p
        # Three onehot channels per position; unused right-padding is all zero.
        # No correct length, next token, or teacher target enters these features.
        slots=np.zeros((23,3),dtype=W.dtype)
        for i,token in enumerate(text):slots[i,'01|'.index(token)]=1
        z=slots.reshape(1,69);h=np.tanh(z@W+b)
        return h,[(z,h)]

    def grads(self,segments,outputs,weight):
        W,b,V,a=self.p;g=[np.zeros_like(p) for p in self.p]
        for cache,(_,h,p,index) in zip(segments,outputs):
            d=p.copy();d[index]-=1;d=(d*weight).astype(h.dtype)[None,:]
            g[2]+=h.T@d;g[3]+=d[0]
            z,hn=cache[0];dz=(d@V.T)*(1-hn*hn)
            g[0]+=z.T@dz;g[1]+=dz[0]
        return g


def main():
    # Reuse the exact P025 protocol, scalar training, replay and checks, selecting
    # its constructor/output directory in this process only; no source is edited.
    protocol.Prefix=Direct
    protocol.OUT=RUNS_ROOT/'echo-prefix-direct-20261112'
    protocol.OUT.mkdir(parents=True,exist_ok=True)
    rows,train,heldout=protocol.x.material()
    plan={'id':'P025B','model':'Direct MLP:69inputs(23positions x3onehot),16tanh,3softmax,1171parameters; no recurrent state, no attention. Rebuild full question|sampledprefix at each step. Rightpadding allzero differs from bit0.',
          'limits':'20k attempts or120sec training per seed101/202/303; same fixed192/64 corpus asP025.',
          'learning':'Only wholeanswer scalar, inherited P025/P024 trajectory exploration and exact mixture correction,Adam.003,wrongretry. No teacher bit or length gradients.',
          'comparison':'Companion toP025RNN, not equalparameter comparison;1171vs371params. Fixedwindow23 limits this pilot, not arbitrarylength copying.',
          'train_values':train,'heldout_values':heldout,
          'sources':{str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [__file__,protocol.__file__,protocol.previous.__file__,protocol.x.__file__]}}
    with (protocol.OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    checks=protocol.checks();(protocol.OUT/'checks.json').write_text(json.dumps(checks,indent=2))
    results=[protocol.run(seed,rows,train,heldout) for seed in protocol.x.SEEDS]
    (protocol.OUT/'compact.json').write_text(json.dumps({'plan':plan,'checks':checks,'runs':results},indent=2))

if __name__=='__main__':main()
