#!/usr/bin/env python3
"""Read-only provenance and raw SLE01 verifier for archived R27 bundle.
No neural student training or teacher-answer oracle is executed.
Usage: python r27_verify_public.py /path/to/sle_ae1_r27_firstword_curriculum_20261114.zip
"""
import hashlib
import json
import sys
import zipfile
from collections import Counter

EXPECTED_ZIP_SHA256 = '73c13754de01739328547cda8dbe6f83c4aa105013b0a1a251681f57d15be0e0'
EXPECTED_FREEZE_SHA = '9fe6a3052de9e0830a331c95e2a1861deb3e827037963d93fdd4ac0c5793e421'

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def verify(path):
    blob=open(path,'rb').read()
    assert sha256(blob)==EXPECTED_ZIP_SHA256, 'archive digest mismatch'
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, 'CRC failure'
        for line in z.read('SHA256SUMS_R27').decode().splitlines()[1:]:
            h,name=line.split('  ',1)
            assert sha256(z.read(name))==h, name
        manifest=[json.loads(x) for x in z.read('r27_experiment/manifest.jsonl').decode().splitlines()]
        prereg=json.loads(z.read('r27_experiment/prereg.json'))
        result=json.loads(z.read('r27_outputs/results.json'))
        raw=[json.loads(x) for x in z.read('r27_outputs/raw_results.jsonl').decode().splitlines()]
        assert len(manifest)==120 and len(raw)==720
        assert sha256(z.read('r27_experiment/prereg.json'))==EXPECTED_FREEZE_SHA
        assert sha256(z.read('r27_experiment/run_r27.py'))==prereg['runner_sha256']
        assert sha256(z.read('r27_experiment/manifest.jsonl'))==prereg['manifest_sha256']
        assert sha256(z.read('r27_outputs/raw_results.jsonl'))==result['raw_sha256']
        assert len({x['Q'] for x in manifest})==120
        assert all(len(x['Q'])==39 and set(x['Q']) <= {'0','1'} for x in manifest)
        assert Counter(x['split'] for x in manifest)=={'seen_baseline':48,'taught_high':32,'near_high':16,'test_unseen_a':16,'validation':8}
        assert all(len(x['expected']) in (7,13) and set(x['expected'][:-1])<= {'0','1'} and x['expected'].endswith('S') for x in manifest)
        assert all(x['actual'].endswith('S') or x['actual'].startswith(('0','1')) for x in raw)
        assert all(x['Q'] in {m['Q'] for m in manifest} for x in raw)
        assert {x['seed'] for x in raw}=={101,202,303}
        assert {x['arm'] for x in raw}=={'R20_control','R27_firstword_curriculum'}
        assert result['updates']==9900 and result['train_targets']==633600
        assert result['status']=='FAIL' and result['seeds_pass']==1
        for seed,expected_gain in [('101',8),('202',0),('303',-8)]:
            t=result['by_seed'][seed]
            assert t['gain_first_unseen']==expected_gain
            assert t['pass_gate']==(seed=='101')
        # STOP metric erratum: R2 has two 6-bit words, so cursor6 is NOT STOP.
        assert all(x['expected'].endswith('S') and x['expected'][-2] in '01' for x in raw)
        assert any(x['r']==2 for x in raw)
        audit=json.loads(z.read('r27_outputs/numpy_audit.json'))
        assert audit['raw_rows']==720 and audit['original_R27_r2_stop_metric_invalid']
        for s in ('101','202','303'):
            for arm in ('R20_control','R27_firstword_curriculum'):
                assert audit['corrected_stop_metrics'][s][arm]['taught_high']['correct_stop']==32
                assert audit['corrected_stop_metrics'][s][arm]['seen_baseline']['correct_stop']==48
        print('R27 public integrity+structure audit PASS:',len(manifest),'native01 Q,',len(raw),'actual recorded NN outputs, FAIL 1/3')
        print('This script does NOT independently re-execute neural forwards. See full bundle audit_numpy_r27.py for that.')

if __name__=='__main__':
    verify(sys.argv[1])
