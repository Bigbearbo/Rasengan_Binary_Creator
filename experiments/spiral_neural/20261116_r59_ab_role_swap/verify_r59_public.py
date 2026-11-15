"""R59 stdlib-only semantic and raw-output audit; not a neural checkpoint replay.
Usage: copy this file into the portable ZIP's r56_workspace/ then run:
  python verify_r59_public.py
This file does not include checkpoints, raw responses or manifest on Git.
"""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
P=Path(__file__).resolve().parent
D=lambda p:json.loads(p.read_text())
J=lambda p:[json.loads(s) for s in p.read_text().splitlines()]
H=lambda p:sha256(p.read_bytes()).hexdigest()
p=D(P/'r59_prereg.json'); qs=J(P/'r59_manifest.jsonl'); x=J(P/'r59_outputs/raw_results.jsonl'); res=D(P/'r59_outputs/results.json')
assert H(P/'r59_manifest.jsonl')==p['manifest_sha256'] and H(P/'r59_role_swap_frozen.py')==p['runner_sha256']
assert H(P/'r59_prereg.json')==res['prereg_sha256'] and H(P/'r59_outputs/raw_results.jsonl')==res['raw_sha256']
for f,h in p['source_sha256'].items():assert H(P/f)==h, f
assert len(qs)==96 and len({q['Q'] for q in qs})==96

def word(v):
    assert isinstance(v,int) and 0<=v<=29
    return format(v,'05b')+'0'
def question(row):return '01'+'010'+format(row['r'],'03b')+'0'+''.join(word(row[k]) for k in 'abcd')+'111100'
def gold(q):return word(q['a'])+(word(q['b']) if q['r']==2 else '')+'S'
by=defaultdict(list)
for q in qs:
    assert len(q['Q'])==39 and set(q['Q'])<=set('01')
    assert q['Q']==question(q) and q['expected']==gold(q) and q['a']!=q['b']
    by[q['pair_id']].append(q)
assert len(by)==48
assert Counter((q['split'],q['r'],q['stratum']) for q in qs)==Counter({(sp,r,st):n for sp,n in [('validation',8),('test',16)] for r in (1,2) for st in ('low-to-high','high-to-low')})
for k,pp in by.items():
    assert len(pp)==2 and {z['swap'] for z in pp}=={0,1}
    a,b=sorted(pp,key=lambda z:z['swap'])
    assert (a['a'],a['b'])==(b['b'],b['a']) and a['r']==b['r'] and a['c']==b['c'] and a['d']==b['d']
    assert a['Q'][9:15]==b['Q'][15:21] and a['Q'][15:21]==b['Q'][9:15] and a['Q'][:9]==b['Q'][:9] and a['Q'][21:]==b['Q'][21:]
    assert a['expected']!=b['expected']
rows={(z['pair_id'],z['swap']):z for z in qs}
assert len(x)==864 and Counter((z['arm'],z['seed']) for z in x)==Counter({(arm,s):96 for arm in ('R52','R55','R56') for s in (101,202,303)})
assert Counter((z['arm'],z['seed'],z['split']) for z in x)==Counter({(arm,s,sp):n for arm in ('R52','R55','R56') for s in (101,202,303) for sp,n in [('validation',32),('test',64)]})
seen=set();group={}
for z in x:
    base=rows[(z['pair_id'],z['swap'])]
    assert all(z[k]==base[k] for k in ('Q','expected','r','a','b','c','d','split','stratum'))
    k=(z['arm'],z['seed'],z['Q']);assert k not in seen;seen.add(k)
    assert set(z['actual'])<=set('01S') and z['exact']==(z['actual']==z['expected'])
    assert z['first']==(z['actual'][:6]==z['expected'][:6])
    assert z['second_r2']==((z['actual'][6:12]==z['expected'][6:12]) if z['r']==2 else None)
    assert z['cause'] in ('stop','cap')
    group.setdefault((z['arm'],z['split']),[]).append(z)
for arm in ('R52','R55','R56'):
    for split in ('validation','test'):
        ys=group[(arm,split)];o=res['groups'][arm][split]
        assert len(ys)==o['answers'] and sum(z['exact'] for z in ys)==o['full']
        pp=defaultdict(list)
        for z in ys:pp[(z['seed'],z['pair_id'])].append(z)
        assert sum(all(z['exact'] for z in zlist) for zlist in pp.values())==o['paired_both_full']
assert sum(z['forwards'] for z in x)==res['forward_calls'] and res['forward_calls']*p['dense_forward_MAC_per_call']==res['dense_inference_MAC']
assert res['joint_gate']=='FAIL' and sum(res['gates'].values())==4 and len(res['gates'])==6
assert res['replay']['torch']==864 and res['replay']['numpy']==864 and res['replay']['sample_logit_max_diff']<1e-5
print('PASS independent stdlib R59 semantic/raw audit; 96 legal unique Q, 48 swapped pairs, 864 responses, all frozen source hashes, 4/6 gate FAIL')
