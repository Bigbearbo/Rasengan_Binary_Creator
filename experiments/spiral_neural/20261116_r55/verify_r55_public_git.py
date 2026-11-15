"""R55 public stdlib audit of downloaded portable ZIP; no NN imports.
Extract ZIP, then run: python r54_workspace/verify_r55_public_git.py
This checks legality, complete free answers, prereg hash and aggregate scores.
Use r55_value_conditioned_gate.py replay/numpy for actual neural inference replays.
"""
import json, hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
def load(p):return json.loads((R/p).read_text())
def question(x):
    return '01'+'010'+format(x['r'],'03b')+'0'+''.join(format(x[k],'05b')+'0' for k in 'abcd')+'111100'
def answer(x):
    return ''.join(format(x[k],'05b')+'0' for k in 'ab'[:x['r']])+'S'
def run():
    p=load('r55_prereg.json'); r=load('r55_outputs/results.json')
    assert digest('r55_manifest.jsonl')==p['manifest_sha256']
    assert digest('r55_value_conditioned_gate.py')==p['runner_sha256']
    assert digest('r55_outputs/raw_results.jsonl')==r['raw_sha256']
    for f,h in p['source_sha256'].items():assert digest(f)==h,(f,'source changed')
    manifest=[json.loads(v) for v in (R/'r55_manifest.jsonl').read_text().splitlines()]
    assert len(manifest)==96 and len({v['Q'] for v in manifest})==96
    assert sum(v['split']=='test' for v in manifest)==64
    assert sum(v['split']=='validation' for v in manifest)==32
    for x in manifest:
        assert x['Q']==question(x) and len(x['Q'])==39 and x['expected']==answer(x)
        assert all(0<=x[k]<=29 for k in 'abcd')
    rows=[json.loads(v) for v in (R/'r55_outputs/raw_results.jsonl').read_text().splitlines()]
    assert len(rows)==528 and len({(x['seed'],x['Q']) for x in rows})==528
    for x in rows:
        assert x['Q']==question(x) and x['expected']==answer(x)
        assert x['exact']==(x['actual']==x['expected'])
        assert x['baseline_exact']==(x['baseline']==x['expected'])
        assert x['first']==(x['actual'][:6]==x['expected'][:6])
        if x['r']==2:assert x['second']==(x['actual'][6:12]==x['expected'][6:12])
    for group in ['validation','test','retention','all']:
        a=[x for x in rows if group=='all' or x['split']==group]
        d=r['groups'][group]
        vals={'n':len(a),'first':sum(x['first'] for x in a),'full':sum(x['exact'] for x in a),
            'baseline_full':sum(x['baseline_exact'] for x in a),
            'gain':sum(x['exact'] and not x['baseline_exact'] for x in a),
            'loss':sum(x['baseline_exact'] and not x['exact'] for x in a)}
        assert all(d[k]==v for k,v in vals.items()),group
    t=r['groups']['test']
    assert r['gates']['test_full_R55_ge_R52_plus_8_of_192']==(t['full']>=t['baseline_full']+8)
    assert r['joint_gate']==('PASS' if all(r['gates'].values()) else 'FAIL')
    print('R55 public audit PASS; recorded scientific gate',r['joint_gate'])
    print('fresh exact test full',t['baseline_full'],'->',t['full'],'/',t['n'])
if __name__=='__main__':run()
