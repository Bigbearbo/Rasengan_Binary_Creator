"""Independent NumPy-only full-answer replay. No probe import, no Torch.
Run after `probe.py run`, checks SHA + every expected and observed output.
"""
from pathlib import Path
import json,base64,hashlib,numpy as np
P=Path(__file__).resolve().parent
rows=[json.loads(x) for x in (P/'raw_cases.jsonl').read_text().splitlines()]
res=json.loads((P/'results.json').read_text())
assert hashlib.sha256((P/'raw_cases.jsonl').read_bytes()).hexdigest()==res['raw_sha256']
def state(seed,arm):
 j=json.loads((P/'checkpoints'/f'weights_seed{seed}_{arm}.json').read_text());d={};h=hashlib.sha256()
 for k,v in j['tensors'].items():
  x=np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').copy().reshape(v['shape']);d[k]=x
  h.update(k.encode());h.update(x.tobytes())
 assert h.hexdigest()==j['weights_sha256']
 return d
def step(st,bits):
 x=np.zeros(160,np.float32)
 for i,b in enumerate(bits):x[2*i+int(b)]=1
 hid=np.tanh(np.matmul(st['0.weight'],x).astype(np.float32)+st['0.bias'])
 logits=(np.matmul(st['2.weight'],hid).astype(np.float32)+st['2.bias'])
 return '01S'[int(np.argmax(logits))]
cache={};steps=0;errors=[];correct=0
for i,r in enumerate(rows):
 key=(r['seed'],r['arm'])
 if key not in cache:cache[key]=state(*key)
 st=cache[key];a='';cause='cap';n=0
 for _ in range(32):
  if len(r['Q'])+len(a)>80:cause='overflow';break
  c=step(st,r['Q']+a);a+=c;n+=1
  if c=='S':cause='stop';break
 word=lambda x:format(x,'05b')+'0'
 q='01'+'010'+'010'+'0'+''.join(word(x) for x in (r['a'],r['b'],0,0))+'111100'
 truth=word(r['a'])+word(r['b'])+'S'
 if not(r['Q']==q and r['expected']==truth and r['actual']==a and r['cause']==cause and n==r['forward_calls'] and r['exact']==(a==truth)):
  errors.append((i,r['actual'],a))
 steps+=n;correct+=a==truth
assert len(rows)==res['rows']==192 and steps==res['inference_forward'] and steps*10432==res['inference_dense_MAC']
print('INDEPENDENT-NUMPY',len(rows)-len(errors),'/',len(rows),'steps',steps,'exact',correct,'errors',errors[:3])
assert not errors
