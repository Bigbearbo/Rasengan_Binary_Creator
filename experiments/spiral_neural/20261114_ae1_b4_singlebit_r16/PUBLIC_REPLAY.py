"""R16 public 01 checkpoint replay. Place beside source_r14/ and raw_results.jsonl from companion ZIP."""
from pathlib import Path
import base64, hashlib, json
import numpy as np
P=Path(__file__).resolve().parent
rows=[json.loads(s) for s in (P/'raw_results.jsonl').read_text().splitlines()]
results=json.loads((P/'results.json').read_text())
assert len(rows)==54
cache={}
def forward(state,bits):
    x=np.zeros((80,2),np.float32)
    for i,b in enumerate(bits): x[i,int(b)]=1
    emb=np.tanh(x[9:33].reshape(4,12)@state['enc.weight'].T+state['enc.bias'])
    pos=np.zeros(33,np.float32);pos[len(bits)-39]=1
    z=np.concatenate((emb.reshape(64),x[5:9].reshape(8),pos))
    hid=np.tanh(state['hidden.weight']@z+state['hidden.bias'])
    return '01S'[int(np.argmax(state['out.weight']@hid+state['out.bias']))]
def load(seed,arm):
    part='checkpoints_new' if arm=='balanced8_16' else 'checkpoints_controls'
    suffix='balanced' if arm=='balanced8_16' else ('treatment8' if arm=='control8' else 'tied')
    p=P/'source_r14'/part/f'weights_{seed}_{suffix}.json'
    assert hashlib.sha256(p.read_bytes()).hexdigest()==results['checkpoint_shas'][f'{seed}_{arm}']
    obj=json.loads(p.read_text())
    return {k:np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').copy().reshape(v['shape']) for k,v in obj['tensors'].items()}
for row in rows:
    key=(row['seed'],row['arm'])
    if key not in cache:cache[key]=load(*key)
    q=row['Q'];actual=''
    for _ in range(32):
        actual+=forward(cache[key],q+actual)
        if actual[-1]=='S':break
    assert actual==row['actual'],(key,row['a'],row['b'],actual,row['actual'])
print('PUBLIC NUMPY REPLAY PASS 54/54; 9 checkpoints; no training')
