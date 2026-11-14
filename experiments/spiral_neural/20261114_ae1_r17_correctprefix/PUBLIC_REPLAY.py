"""Replay R17 from the companion ZIP; no training and no teacher oracle on model side.
Usage: python PUBLIC_REPLAY.py --source-root <extracted R16 folder>
"""
from pathlib import Path
import argparse,base64,hashlib,json,importlib.util
import numpy as np
R=Path(__file__).resolve().parent
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);args=ap.parse_args()
src=Path(args.source_root).resolve();spec=json.loads((R/'prereg.json').read_text())
assert h(R/'manifest.jsonl')==spec['manifest_sha256']
assert h(src/'raw_results.jsonl')==spec['source_r16_raw_sha256']
assert h(R/'raw_tf.jsonl')==json.loads((R/'results.json').read_text())['raw_sha256']
rows=[json.loads(x) for x in (R/'raw_tf.jsonl').read_text().splitlines()]
assert len(rows)==54 and all(len(x['tf_logits'])==13 for x in rows)
ss=importlib.util.spec_from_file_location('r16',src/'run_r16.py');m=importlib.util.module_from_spec(ss);ss.loader.exec_module(m);model_source=m.source()
import torch
with torch.no_grad():
 for seed,arm,p,sha in m.weights():
  net=m.load(p,model_source)
  group=[x for x in rows if x['seed']==seed and x['arm']==arm]
  assert len(group)==6
  for r in group:
   assert r['source_checkpoint_sha256']==sha
   out=''
   for i,c in enumerate(r['expected']):
    logits=net(torch.from_numpy(model_source.xvec(r['Q']+r['expected'][:i])).unsqueeze(0))[0].numpy()
    assert np.allclose(logits,r['tf_logits'][i],atol=1e-6,rtol=0)
    out+='01S'[int(np.argmax(logits))]
   assert out==r['tf_greedy']
print('PUBLIC REPLAY PASS: 54 cases, 702 torch teacher-forced logits; 9 source-verified checkpoints, no training')
