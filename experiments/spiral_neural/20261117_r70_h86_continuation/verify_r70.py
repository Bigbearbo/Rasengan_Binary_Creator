#!/usr/bin/env python3
"""Independent immutable raw-bit replay of H86 checkpoints and seed/split assertions."""
import json, hashlib
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent
D=json.loads((R/'r70_results'/'results.json').read_text())
orig=json.loads((R/'results'/'results.json').read_text())
assert len(D['seeds'])==3
R70={}
for seed in (101,202,303):
 entry=D['seeds'][str(seed)]
 for entrycp in entry['checkpoints']:
  t=entrycp['update']
  f=(R/'results'/f'B_seed{seed}_step4096.npz') if t==4096 else (R/'r70_results'/f'B_seed{seed}_step{t}.npz')
  with np.load(f,allow_pickle=False) as z:
   st=json.loads(str(z['meta']))
   assert int(st['step'])==t and int(st['seed'])==seed
   p={k:z['p_'+k] for k in ('W1','b1','Wo','bo')}
   assert all(np.all(np.isfinite(v)) for v in p.values())
   assert p['W1'].shape==(151,86) and p['Wo'].shape==(86,41)
   assert all(np.all(np.isfinite(z['m_'+k])) and np.all(np.isfinite(z['v_'+k])) for k in p)
   def check(file,label):
    rows=[json.loads(x) for x in (R/'results'/file).read_text().splitlines()]
    fam_stats={}
    for fam in ['PUNCT','CLEAN-COPY1','DIRTY-COPY1','COPY2','REVERSE2','COPY3','REVERSE3','COPY4','REVERSE4']:
     a=[v for v in rows if v['family']==fam]
     X=np.fromiter((int(b) for v in a for b in v['raw_input_151']),dtype=np.float64).reshape(-1,151)
     Y=np.fromiter((int(b) for v in a for b in v['gold_answer_40']),dtype=np.float64).reshape(-1,40)
     M=np.fromiter((int(b) for v in a for b in v['answer_mask_40']),dtype=np.float64).reshape(-1,40)
     h=np.tanh(X@p['W1']+p['b1']); logits=h@p['Wo']+p['bo']
     hit=np.all((logits[:,:40]>0)==Y,axis=1) if M.all() else np.all(np.logical_or((logits[:,:40]>0)==Y,M==0),axis=1)
     hit=hit & (logits[:,40]>0)
     fam_stats[fam]={'correct':int(hit.sum()),'total':len(a),'pct':float(100*hit.mean())}
    want=entrycp['val'] if label=='val' else entry['final_test']
    assert fam_stats==want,(seed,t,label,fam_stats,want)
    return sum(q['correct'] for q in fam_stats.values()),sum(q['total'] for q in fam_stats.values())
   n=check('validation_raw.jsonl','val');assert n[1]==2049
   if t==8192:
    j=check('test_raw.jsonl','test');assert j[1]==4097
   if t==4096:assert entrycp['val']==orig['B'][str(seed)]['final_val']
  R70.setdefault(str(seed),[]).append(t)
print('R70_INDEPENDENT_REPLAY_PASS',R70,'checkpoints',sum(map(len,R70.values())),'final_test_seed_replays',3)