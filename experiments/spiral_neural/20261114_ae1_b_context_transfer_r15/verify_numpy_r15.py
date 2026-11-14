"""AE1 R15 independent NumPy 01 greedy inference; zero Torch/LLM or optimizer."""
from pathlib import Path
from collections import Counter
import base64,hashlib,json
import numpy as np
P=Path(__file__).resolve().parent;S=P/'source_r14'
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
pre=json.loads((P/'prereg.json').read_text());result=json.loads((P/'results.json').read_text())
assert H(P/'manifest.jsonl')==pre['manifest_sha256']
assert H(P/'run_r15.py')==pre['runner_sha256']
assert H(P/'raw_results.jsonl')==result['raw_sha256']
rows=[json.loads(s) for s in (P/'raw_results.jsonl').read_text().splitlines()]
assert len(rows)==459 and len(set((z['seed'],z['arm'],z['Q']) for z in rows))==459

def model(key):
    seed,arm=key
    if arm=='balanced8_16':path=S/'checkpoints_new'/f'weights_{seed}_balanced.json'
    elif arm=='control8':path=S/'checkpoints_controls'/f'weights_{seed}_treatment8.json'
    else:path=S/'checkpoints_controls'/f'weights_{seed}_tied.json'
    assert H(path)==result['source_checkpoint_shas'][f'{seed}_{arm}']
    j=json.loads(path.read_text())
    st={k:np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').copy().reshape(v['shape']) for k,v in j['tensors'].items()}
    assert sum(x.size for x in st.values())==10457
    return st

def forward(st,bits):
    assert 39<=len(bits)<=80 and set(bits)<={'0','1'} and bits.startswith('01010')
    x=np.zeros((80,2),dtype=np.float32)
    for k,z in enumerate(bits):x[k,int(z)]=1
    q=x[9:33,:].reshape(4,12)
    e=np.tanh(q@st['enc.weight'].T+st['enc.bias'])
    pos=np.zeros(33,dtype=np.float32);pos[len(bits)-39]=1
    h=np.tanh(st['hidden.weight']@np.concatenate((e.reshape(64),x[5:9,:].reshape(8),pos))+st['hidden.bias'])
    return '01S'[int(np.argmax(st['out.weight']@h+st['out.bias']))]

states={};forward_count=0;errors=[];cnt=Counter()
for i,r in enumerate(rows):
    key=(r['seed'],r['arm'])
    if key not in states:states[key]=model(key)
    pred='';cause='cap';fw=0
    for t in range(32):
        if len(pred)+len(r['Q'])>80: cause='overflow';break
        pred+=forward(states[key],r['Q']+pred);fw+=1
        if pred[-1]=='S':cause='stop';break
    forward_count+=fw
    expect=r['expected']
    observed=(pred,cause,fw,pred==expect,pred[:6]==expect[:6],pred[6:12]==expect[6:12],cause=='stop' and len(pred)==len(expect))
    given=(r['actual'],r['cause'],r['forward_calls'],r['exact'],r['first_word'],r['second_word'],r['stop_correct'])
    if observed!=given:errors.append((i,observed,given))
    cnt[key,r['split']]+=int(pred==expect)
assert not errors,errors[:5]
assert forward_count==result['forward_calls'] and forward_count*10920==result['inference_dense_MAC']
assert len(states)==9
for b in result['blocks']:
    for split,stats in b['metrics'].items():
        assert cnt[(b['seed'],b['arm']),split]==stats['exact']
print('NUMPY INDEPENDENT REPLAY PASS',len(rows),'/',len(rows),'full native 01 outputs;',forward_count,'forward;',len(states),'immutable checkpoints; 0 optimizer')
