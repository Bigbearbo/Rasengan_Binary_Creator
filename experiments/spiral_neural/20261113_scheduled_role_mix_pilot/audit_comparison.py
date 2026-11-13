"""Read-only, non-NN paired audit of preexisting PR36 and new mix-run holdouts.
Must never perform a student forward or relabel observations after the fact.
"""
import json
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent
PR36=HERE.parent/'20261113_scheduled_role_swap_pilot'
def load(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def key(x):
    return x['seed'],x['r'],x['a'],x['b']

def main():
    old=load(PR36/'raw_cases.jsonl');new=load(HERE/'raw_cases.jsonl')
    assert len(old)==720 and len(new)==360
    table={}
    for x in old:
        if x['split'].startswith('heldout_'):
            k=(x['seed'],x['arm'],x['r'],x['a'],x['b'])
            assert k not in table
            table[k]=x
    assert len(table)==144
    out=defaultdict(lambda: {'n':0,'mix_correct':0,'exclusive_first_correct':0,'exclusive_second_correct':0})
    for x in new:
        if not x['split'].startswith('heldout_s'):continue
        assert x['r']==2 and 6<=max(x['a'],x['b'])<=14
        role='HIGH_FIRST' if x['a']>=6 else 'HIGH_SECOND'
        assert x['split']==('heldout_s'+str(x['b'] if role=='HIGH_FIRST' else x['a'])+'_high_'+role.split('_')[-1].lower())
        group=out[(x['seed'],role)]
        group['n']+=1
        group['mix_correct']+=x['actual']==x['expected']
        for mode,label in [('HIGH_FIRST','exclusive_first_correct'),('HIGH_SECOND','exclusive_second_correct')]:
            prev=table[(x['seed'],mode,x['r'],x['a'],x['b'])]
            assert x['Q']==prev['Q'] and x['expected']==prev['expected']
            group[label]+=prev['actual']==prev['expected']
    assert len(out)==4
    for (seed,role),d in sorted(out.items()):
        assert d['n']==18
        assert d['mix_correct']>=12
        assert d['exclusive_first_correct']==(18 if role=='HIGH_FIRST' else 0)
        assert d['exclusive_second_correct']==(18 if role=='HIGH_SECOND' else 0)
        print(seed,role,d)
    assert sum(d['mix_correct'] for d in out.values())==66
    print('PASS: 72 paired holdouts matched exactly to old PR36 Q/expected; new MIX 66/72; old role-exclusive each 36/72 across both seeds.')
if __name__=='__main__':main()
