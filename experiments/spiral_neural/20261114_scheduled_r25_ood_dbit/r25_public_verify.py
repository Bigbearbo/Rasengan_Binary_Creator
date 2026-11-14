"""Pure NumPy independent replay for R25 raw-bit experiment.
Usage: python r25_public_verify.py <extracted_companion_zip_directory>
Never trains or changes historical checkpoint files.
"""
import hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main(root):
    spec=json.loads((root/'prereg.json').read_text())
    assert sha(root/'manifest.jsonl')==spec['manifest_sha256']
    assert sha(root/'r25_probe.py')==spec['runner_sha256']
    for rel,digest in spec['frozen_sources_sha256'].items():
        assert sha(root/rel)==digest, rel
    rows=[json.loads(line) for line in (root/'raw_results.jsonl').read_text().splitlines()]
    stored=json.loads((root/'results.json').read_text())
    assert len(rows)==576 and sha(root/'raw_results.jsonl')==stored['raw_sha256']
    module=importlib.util.spec_from_file_location('r25_numpy', root/'r23_experiment/verify_numpy.py')
    npmod=importlib.util.module_from_spec(module)
    module.loader.exec_module(npmod)
    weights={}
    max_error=0.0
    greedy_forwards=0
    for x in rows:
        prefix='outputs_r20' if x['arm']=='R20' else 'r23_outputs'
        key=(prefix,x['seed'])
        if key not in weights:
            weights[key]=npmod.arrays(root/prefix/f'weights_{x["seed"]}_dual.json')
        w=weights[key]
        response,cause,steps=npmod.generate(x['Q'],w)
        assert (response,cause,steps)==(x['actual'],x['cause'],x['greedy_forwards'])
        logits=npmod.logits(x['Q'],x['expected'][:6],w)
        error=float(np.max(np.abs(logits-np.array(x['STOP_logits']))))
        max_error=max(max_error,error)
        assert error<5e-5
        assert abs(float(logits[2]-max(logits[0],logits[1]))-x['STOP_margin'])<5e-5
        assert bool(int(logits.argmax())==2)==x['STOP_correct']
        greedy_forwards+=steps
    assert stored['greedy_forwards']==greedy_forwards
    assert stored['inference_dense_MAC']==(greedy_forwards+len(rows))*10920
    print('PASS',len(rows),'independently replayed full native-01 predictions + STOP logits; max error',max_error)
if __name__=='__main__':
    assert len(sys.argv)==2, 'usage: python r25_public_verify.py EXTRACTED_R25_ROOT'
    main(Path(sys.argv[1]).resolve())
