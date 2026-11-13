"""Independent no-Torch verifier for immutable SLE-AE1 heldout-pair context panel.
No imports of experiment.py; no optimizer or teacher oracle. Usage: python verify_numpy.py
"""
import base64, hashlib, json
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent

def filehash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def tensor(seed,arm):
    p=P/'checkpoints'/f'weights_seed{seed}_{"conjunction" if arm=="frozen_c1_control" else "balanced_c"}.json'
    obj=json.loads(p.read_text());sha=hashlib.sha256();out={}
    for name,entry in obj['tensors'].items():
        arr=np.frombuffer(base64.b64decode(entry['little_endian_base64']),dtype='<f4').copy().reshape(entry['shape'])
        sha.update(name.encode());sha.update(arr.tobytes());out[name]=arr
    assert sha.hexdigest()==obj['weights_sha256'] and sum(a.size for a in out.values())==10499
    return out

def step(state,bits):
    z=np.zeros((160,),dtype=np.float32)
    for i,b in enumerate(bits):z[2*i+int(b)]=np.float32(1)
    h=np.tanh(np.matmul(state['0.weight'],z).astype(np.float32)+state['0.bias'])
    logits=(np.matmul(state['2.weight'],h).astype(np.float32)+state['2.bias'])
    return '01S'[int(np.argmax(logits))]

def main():
    spec=json.loads((P/'PREREGISTRATION.json').read_text())
    assert filehash(P/'raw_cases.jsonl')==json.loads((P/'RESULTS.json').read_text())['raw_sha256']
    assert filehash(P/'experiment.py')==spec['runner_sha256']
    data=[json.loads(x) for x in (P/'raw_cases.jsonl').read_text().splitlines()]
    assert len(data)==384
    cache={};steps=0;fail=[];correct=0
    for idx,r in enumerate(data):
        k=(r['seed'],r['arm'])
        if k not in cache:cache[k]=tensor(*k)
        out='';cause='cap';n=0
        for _ in range(32):
            if len(r['Q'])+len(out)>80:cause='overflow';break
            bit=step(cache[k],r['Q']+out);out+=bit;n+=1
            if bit=='S':cause='stop';break
        valid=('01'+'010'+'010'+'0'+''.join(format(x,'05b')+'0' for x in (r['a'],r['b'],r['c'],r['d']))+'111100')
        target=(format(r['a'],'05b')+'0'+format(r['b'],'05b')+'0'+'S')
        if not (r['Q']==valid and r['expected']==target and r['actual']==out and r['cause']==cause and r['forward_calls']==n and r['exact']==(out==target)):
            fail.append((idx,r['actual'],out))
        correct+=out==target;steps+=n
    result=json.loads((P/'RESULTS.json').read_text());assert result['inference_forward_calls']==steps
    assert result['rows']==len(data) and result['inference_dense_MAC']==steps*10432
    print('NUMPY CHECK',len(data)-len(fail),'/',len(data),'steps',steps,'exact',correct,'FAIL',fail[:3])
    assert not fail
if __name__=='__main__':main()
