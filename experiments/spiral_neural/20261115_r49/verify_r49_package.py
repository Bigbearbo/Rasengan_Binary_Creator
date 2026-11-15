"""Lightweight source-free R49 artifact auditor: SHA + raw split/scores, no NN."""
import hashlib,json,sys
from pathlib import Path
p=Path(__file__).resolve().parent
sha=lambda x:hashlib.sha256((p/x).read_bytes()).hexdigest()
spec=json.loads((p/'r49_prereg.json').read_text()); results=json.loads((p/'r49_outputs/results.json').read_text())
assert sha('r49_frozen_rescue.py')==spec['existing_source_sha256']['r49_frozen_rescue.py']
assert sha('r49_manifest.jsonl')==spec['manifest_SHA256']
assert sha('r49_prereg.json')==results['prereg_sha256']
assert sha('r49_outputs/raw_results.jsonl')==results['raw_sha256']
assert results['gate']=='FAIL' and len(results['qualifying_arms'])==0
for arm in (45,46,47,48):
 assert sha(f'r{arm}_outputs/raw_results.jsonl')==spec['historical_raw_sha256'][str(arm)]
 for seed in (101,202,303):
  assert sha(f'r{arm}_outputs/weights_{seed}_dual.json')==spec['weights_sha256'][str(arm)][str(seed)]
rows=[json.loads(x) for x in (p/'r49_outputs/raw_results.jsonl').read_text().splitlines()]
assert len(rows)==2112 and len({(z['source_arm'],z['seed'],z['Q']) for z in rows})==2112
for arm in (45,46,47,48):
 part=[x for x in rows if x['source_arm']==arm and x['split']!='historical_retention']
 a=results['arms'][str(arm)]
 assert len(part)==288
 assert sum(bool(x['second_correct']) for x in part)==a['second_after']
 assert sum(bool(x['before_second_correct']) for x in part)==a['second_before']
 assert sum(bool(x['exact']) for x in part)==a['full_after']
 for x in part:
  assert len(x['Q'])==39 and set(x['Q'])<={'0','1'}
print('R49 evidence SHA and 2,112 distinct rows PASS; no NN executed')
