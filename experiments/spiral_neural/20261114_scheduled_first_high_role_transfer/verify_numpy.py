"""Independent NumPy F32 replay; does not import run.py or PyTorch."""
from pathlib import Path
import json,base64,hashlib,collections
import numpy as np
P=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
res=json.loads((P/'results.json').read_text())
rows=[json.loads(x) for x in (P/'raw_cases.jsonl').read_text().splitlines()]
assert sha((P/'raw_cases.jsonl').read_bytes())==res['raw_sha256']
weights={}
def load(s,arm):
 path=P/'checkpoints'/f'weights_seed{s}_{arm}.json'
 b=path.read_bytes()
 block=next(r for r in res['blocks'] if r['seed']==s and r['arm']==arm)
 assert sha(b)==block['weights_file_sha256']
 j=json.loads(b);h=hashlib.sha256();st={}
 for k,v in j['tensors'].items():
  x=np.frombuffer(base64.b64decode(v['little_endian_base64']),'<f4').copy().reshape(v['shape']);st[k]=x
  h.update(k.encode());h.update(x.tobytes())
 assert h.hexdigest()==j['weights_sha256']==block['weights_sha256']
 return st

def infer(st,bits):
 x=np.zeros(160,dtype=np.float32)
 for i,b in enumerate(bits):x[i*2+int(b)]=1.0
 hidden=np.tanh((st['0.weight']@x).astype(np.float32)+st['0.bias'])
 z=st['2.weight']@hidden+st['2.bias']
 return '01S'[int(np.argmax(z))]

def word(x):return f'{x:05b}0'
counts=collections.Counter();calls=0;fail=[]
for i,r in enumerate(rows):
 key=(r['seed'],r['arm'])
 if key not in weights:weights[key]=load(*key)
 Q='01'+'010'+format(r['r'],'03b')+'0'+''.join(word(r[k]) for k in ('a','b','c','d'))+'111100'
 truth=word(r['a'])+(word(r['b']) if r['r']==2 else '')+'S'
 assert Q==r['Q'] and len(Q)==39 and truth==r['expected']
 actual='';cause='cap';n=0
 for _ in range(32):
  if len(Q)+len(actual)>80:cause='overflow';break
  actual+=infer(weights[key],Q+actual);n+=1
  if actual[-1]=='S':cause='stop';break
 calls+=n
 if (actual,cause,n,actual==truth)!=(r['actual'],r['cause'],r['forward_calls'],r['exact']):fail.append((i,r['actual'],actual))
 counts[(r['seed'],r['arm'],r['split'])]+=(actual==truth)
assert len(rows)==512 and len(weights)==4 and calls==res['inference_forward_calls']
assert calls*10432==res['inference_dense_MAC']
for b in res['blocks']:
 for split,m in b['metrics'].items():
  assert counts[(b['seed'],b['arm'],split)]==m['exact']
print('NUMPY-REPLAY',len(rows)-len(fail),'/',len(rows),'forward',calls,'errors',fail[:5],flush=True)
assert not fail
