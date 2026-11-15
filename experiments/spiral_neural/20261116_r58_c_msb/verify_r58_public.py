"""R58 public stdlib verifier. Run in extracted full R58 ZIP / r56_workspace.
This checks legal 39-bit manifest, R58 SHA receipts, 864 raw predictions,
paired causal outcomes, and preregistered gates. Neural replay additionally
requires: python r58_cmsb_frozen_probe.py torch ; python ... numpy.
"""
import collections, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def read(path): return json.loads((ROOT/path).read_text())
def question(x):
    return '01'+'010'+format(x['r'],'03b')+'0'+''.join(format(x[k],'05b')+'0' for k in 'abcd')+'111100'
def truth(x):
    return format(x['a'],'05b')+'0'+(format(x['b'],'05b')+'0' if x['r']==2 else '')+'S'
def main():
    p=read('r58_prereg.json')
    rows=[json.loads(t) for t in (ROOT/'r58_manifest.jsonl').read_text().splitlines()]
    raw=[json.loads(t) for t in (ROOT/'r58_outputs/raw_results.jsonl').read_text().splitlines()]
    result=read('r58_outputs/results.json')
    assert sha('r58_prereg.json')==result['prereg_sha256']
    assert sha('r58_manifest.jsonl')==p['manifest_sha256']
    assert sha('r58_cmsb_frozen_probe.py')==p['runner_sha256']
    assert sha('r58_outputs/raw_results.jsonl')==result['raw_sha256']
    for name,digest in p['source_sha256'].items(): assert sha(name)==digest,name
    assert len(rows)==96 and len({x['Q'] for x in rows})==96
    pairs=collections.defaultdict(list)
    for x in rows:
        assert len(x['Q'])==39 and x['Q']==question(x) and x['expected']==truth(x)
        assert all(0<=x[k]<=29 for k in 'abcd')
        pairs[x['pair_id']].append(x)
    assert len(pairs)==48
    for v in pairs.values():
        assert len(v)==2
        lo,hi=sorted(v,key=lambda z:z['c_bit5'])
        assert hi['c']==lo['c']+16 and 0<=lo['c']<=13
        assert [i for i,(x,y) in enumerate(zip(lo['Q'],hi['Q'])) if x!=y]==[21]
        assert lo['expected']==hi['expected']
        assert all(lo[k]==hi[k] for k in ('r','a','b','d','split','stratum'))
    distribution=collections.Counter((x['split'],x['r'],x['stratum']) for x in rows)
    expected=collections.Counter({(split,r,st):n for split,n in [('validation',8),('test',16)] for r in (1,2) for st in ('low','high')})
    assert distribution==expected
    assert len(raw)==864
    assert collections.Counter((x['arm'],x['seed']) for x in raw)==collections.Counter({(arm,seed):96 for arm in ('R52','R55','R56') for seed in (101,202,303)})
    mapped={x['Q']:x for x in rows}
    aggregate={}
    for arm in ('R52','R55','R56'):
        aggregate[arm]={}
        for split in ('validation','test','all'):
            subset=[x for x in raw if x['arm']==arm and (split=='all' or x['split']==split)]
            by=collections.defaultdict(list)
            for x in subset:
                assert all(x[k]==value for k,value in mapped[x['Q']].items())
                assert x['exact']==(x['actual']==x['expected'])
                assert x['first']==(x['actual'][:6]==x['expected'][:6])
                assert x['second_r2']==(x['actual'][6:12]==x['expected'][6:12] if x['r']==2 else None)
                assert x['cause'] in ('stop','cap')
                by[(x['seed'],x['pair_id'])].append(x)
            assert all(len(v)==2 for v in by.values())
            flips=sum(v[0]['actual'][:6]!=v[1]['actual'][:6] for v in by.values())
            changed=sum(v[0]['exact']!=v[1]['exact'] for v in by.values())
            both=sum(all(x['exact'] for x in v) for v in by.values())
            saved=result['groups'][arm][split]
            assert saved['full']==sum(x['exact'] for x in subset)
            assert (saved['firstword_flips'],saved['full_correctness_flips'],saved['both_full_correct'])==(flips,changed,both)
            aggregate[arm][split]=(flips,changed,both)
    a=aggregate['R55']['test'];z=aggregate['R56']['test'];g=result['gates']
    assert g['R55_test_firstword_flips_at_least_8_fewer_than_R56']==(a[0]<=z[0]-8)
    assert g['R55_test_full_correctness_flips_at_least_8_fewer_than_R56']==(a[1]<=z[1]-8)
    assert g['R55_test_both_correct_pairs_at_least_4_more_than_R56']==(a[2]>=z[2]+4)
    assert g['R55_test_full_correct_no_more_than_4_below_R52']==(result['groups']['R55']['test']['full']>=result['groups']['R52']['test']['full']-4)
    assert result['joint_gate']==('PASS' if all(g.values()) else 'FAIL')
    print('R58 public raw audit PASS, manifest 96 Q, neural records 864, joint',result['joint_gate'])
if __name__=='__main__':main()
