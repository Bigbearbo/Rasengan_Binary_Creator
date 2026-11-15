"""R56 standard-library raw evidence audit (extract the full R56 ZIP first).
Usage: cd r56_workspace && python verify_r56_git.py
This verifies immutable inputs/outputs, profiles, paired comparisons and gates.
It does not independently re-run the neural network; run r56_fixed_intercept_control.py replay/numpy for that.
"""
from pathlib import Path
import hashlib,json,collections
R=Path(__file__).resolve().parent
def hashfile(f):return hashlib.sha256((R/f).read_bytes()).hexdigest()
def read(f):return json.loads((R/f).read_text())
def lines(f):return [json.loads(x) for x in (R/f).read_text().splitlines()]
def q(x):
    return '01010'+format(x['r'],'03b')+'0'+''.join(format(x[k],'05b')+'0' for k in 'abcd')+'111100'
def a(x):
    return ''.join(format(x[k],'05b')+'0' for k in 'ab'[:x['r']])+'S'
p=read('r56_prereg.json')
s=read('r56_outputs/results.json')
m=lines('r55_manifest.jsonl')
rows=lines('r56_outputs/raw_results.jsonl')
assert hashfile('r56_fixed_intercept_control.py')==p['runner_sha256']
assert hashfile('r55_manifest.jsonl')==p['manifest_sha256']
assert hashfile('r56_outputs/raw_results.jsonl')==s['raw_sha256']
for file,digest in p['source_sha256'].items():
    assert hashfile(file)==digest,(file,'source changed')
assert len(m)==96 and len({x['Q'] for x in m})==96
assert collections.Counter((x['split'],x['r']) for x in m)=={
    ('validation',1):16,('validation',2):16,('test',1):32,('test',2):32}
assert len(rows)==528 and collections.Counter(x['seed'] for x in rows)=={101:176,202:176,303:176}
seen=set()
for x in rows:
    assert x['Q']==q(x) and len(x['Q'])==39 and x['expected']==a(x)
    assert all(0<=x[k]<=29 for k in 'abcd')
    assert x['exact']==(x['actual']==x['expected'])
    assert x['R55_exact']==(x['R55_actual']==x['expected'])
    assert x['R52_exact']==(x['R52_actual']==x['expected'])
    assert x['first']==(x['actual'][:6]==x['expected'][:6])
    assert x['second']==(x['actual'][6:12]==x['expected'][6:12] if x['r']==2 else None)
    key=x['seed'],x['Q']
    assert key not in seen
    seen.add(key)
for split in ('validation','test','retention','all'):
    subset=[x for x in rows if split=='all' or x['split']==split]
    stats=s['groups'][split]
    expectations=dict(n=len(subset),R56_full=sum(x['exact'] for x in subset),
      R55_full=sum(x['R55_exact'] for x in subset),
      R52_full=sum(x['R52_exact'] for x in subset),
      first=sum(x['first'] for x in subset),
      second=sum(bool(x['second']) for x in subset),
      gain_vs_R55=sum(x['exact'] and not x['R55_exact'] for x in subset),
      loss_vs_R55=sum(x['R55_exact'] and not x['exact'] for x in subset))
    assert all(stats[k]==v for k,v in expectations.items()),(split,stats,expectations)
t=s['groups']['test'];h=s['groups']['retention'];g=s['gates']
assert g['test_full_R56_at_least_R55_44_of_192']==(t['R56_full']>=t['R55_full'])
assert g['test_full_R56_at_least_R52_45_of_192']==(t['R56_full']>=t['R52_full'])
assert g['retention_R56_at_least_R55_minus_12']==(h['R56_full']>=h['R55_full']-12)
assert g['test_R56_seed_not_less_than_R55_minus_4']==all(
 t['by_seed'][str(seed)]['full']>=t['by_seed'][str(seed)]['R55_full']-4 for seed in (101,202,303))
assert s['joint_gate']==('PASS' if all(g.values()) else 'FAIL')
print('R56 RAW AUDIT PASS: 528 predictions; joint',s['joint_gate'],
      'test R52/R55/R56',t['R52_full'],t['R55_full'],t['R56_full'])
