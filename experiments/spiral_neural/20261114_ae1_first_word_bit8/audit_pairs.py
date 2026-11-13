"""Post-forward descriptive integrity audit of frozen raw responses; never train or alter gates."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
rows=[json.loads(x) for x in (p/'raw_cases.jsonl').read_text().splitlines()]
idx={(r['seed'],r['arm'],r['a'],r['b']):r for r in rows}
result={}
for seed in (101,202):
 for arm in ('conjunction','balanced_c'):
  matching=[];response_change=[];second_ok=[];stop_ok=[]
  for a in range(6):
   for b in (18,19,22,23):
    old=idx[seed,arm,a,b];new=idx[seed,arm,a+8,b]
    qdelta=[i for i,(x,y) in enumerate(zip(old['Q'],new['Q'])) if x!=y]
    ansdelta=[i for i,(x,y) in enumerate(zip(old['expected'],new['expected'])) if x!=y]
    assert qdelta==[10] and ansdelta==[1]
    diff=[i for i,(x,y) in enumerate(zip(old['actual'],new['actual'])) if x!=y]
    matching.append(len(old['actual'])==len(new['actual'])==13 and diff==[1])
    response_change.append(old['actual']!=new['actual'])
    second_ok.append(old['actual'][6:12]==new['actual'][6:12])
    stop_ok.append(old['correct_STOP'] and new['correct_STOP'])
  key=f'{arm}_{seed}'
  result[key]={'output_position_1_exact_single_bit_flip':sum(matching),'any_change':sum(response_change),'second_word_same':sum(second_ok),'STOP_both_right':sum(stop_ok),'pairs':24}
print(json.dumps(result,indent=2))
assert all(v['any_change']==0 and v['output_position_1_exact_single_bit_flip']==0 for v in result.values())
