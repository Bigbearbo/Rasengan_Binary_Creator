"""Independent checkpoint/raw output replay and curriculum integrity audit for SLE AE1 role-swap pilot."""
import base64, hashlib, json, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import torch
from torch import nn
sys.path.insert(0, str(Path(__file__).parent))
import run
P=Path(__file__).parent
report=json.loads((P/'results.json').read_text())
raw=(P/'raw_cases.jsonl').read_bytes()
assert hashlib.sha256(raw).hexdigest()==report['raw_sha256']
rows=[json.loads(z) for z in raw.splitlines()]
assert len(rows)==report['raw_case_count']==720
unique=set(); costs=0
for x in rows:
  key=(x['seed'],x['arm'],x['split'],x['r'],x['a'],x['b'])
  assert key not in unique,key
  unique.add(key)
  assert x['Q']==run.qbits(x['r'],x['a'],x['b'],x['c'],x['d'])
  assert x['expected']==run.answer(x['r'],x['a'],x['b'])
  assert x['c']==x['d']==0
  assert len(x['Q'])==39 and set(x['Q'])=={'0','1'}
  if x['split']=='base_train': assert (x['a']+x['b'])%6>=2
  elif x['split']=='base_val': assert (x['a']+x['b'])%6==0
  elif x['split']=='base_test': assert (x['a']+x['b'])%6==1
  else:
    role=x['split'].rsplit('_',2)[-2:]
    assert role in [ ['HIGH','FIRST'],['HIGH','SECOND'] ],key
    assert x['r']==2
    hi=x['a'] if role[1]=='FIRST' else x['b']
    lo=x['b'] if role[1]=='FIRST' else x['a']
    assert 6<=hi<=14
    assert 0<=lo<=(3 if x['split'].startswith('exposed') else 5)
    if x['split'].startswith('heldout'):assert 4<=lo<=5
    else:assert lo<=3

replayed=0
for model in report['models']:
  cp=json.loads((P/model['checkpoint_path']).read_text())
  assert cp['weights_sha256']==model['final_sha256']
  m=run.network(model['seed'])
  weights={}
  for name,v in cp['tensors'].items():
    values=np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').copy()
    assert values.size==np.prod(v['shape'])
    weights[name]=torch.from_numpy(values.reshape(v['shape']))
  m.load_state_dict(weights)
  assert run.weights_sha(m)==model['final_sha256']
  for x in rows:
    if x['seed']==model['seed'] and x['arm']==model['arm']:
      predicted,why,n=run.free(m,x['Q'])
      assert predicted==x['actual'] and why==x['cause'],(model['seed'],model['arm'],x)
      replayed+=1
  assert sum(x['split']=='base_train' for x in rows if x['seed']==model['seed'] and x['arm']==model['arm'])==48
  assert sum(x['split']=='heldout_HIGH_SECOND' for x in rows if x['seed']==model['seed'] and x['arm']==model['arm'])==18
assert replayed==720
print('PASS verifier: sha256/raw legal; unique 720; four checkpoints exact; 720/720 fresh-load free generation exact')
print('PASS splits: base 24/6/6, exposure 36 each, heldout 18 each; 0 overlap')
