"""R28 archive result verifier; stdlib only, no neural inference or training.
Full PyTorch and independent NumPy replay live in the attached R28 ZIP.
Usage: python r28_public_verify.py /path/to/unzipped/R28
"""
import collections
import hashlib
import json
import pathlib
import sys

SEEDS = (101, 202, 303)
ARMS = ('R20_prior', 'R27_highonly', 'R28_half_near')
SPLITS = {'validation_taught_high': 8, 'test_unseen_high': 16,
          'test_near_transfer': 16, 'legacy_near_diagnostic': 16,
          'seen_baseline': 48, 'taught_high': 32}
FROZEN = {
    'r28_experiment/r28_runner.py': '606b7e3446c02fc00169e379988b99cd181e048a57877ef763f999aed38ed8a2',
    'r28_experiment/prereg.json': '8ca9f71039e207834f03bd3931885ac10c36c1be9b8a0ded0af0fed4317ed704',
    'r28_experiment/manifest.jsonl': 'e935dd9bc3836168ea93ce3a50860a25876c821b939172d000e87660b76cd9c9',
    'r28_outputs/raw_results.jsonl': 'dbe5015ff430c0e2a4e85845fa7e1eb77d1218efbec246c8c67ed7ea2e84dbcb',
    'r28_outputs/results.json': '15bc08dd00836762a16d3826f14e24eeb0d465d5a1307c17f46355de268a49b3',
    'r28_outputs/numpy_audit.json': '90b34e86b0d0cd26689d02376cbb525403c900151a7812859f70429d472a5379',
    'r28_outputs/weights_101_dual.json': '8558e0c71f6e0a964f1eb5974903f63cb863c8ea0c57e0fd89867193b3122b0c',
    'r28_outputs/weights_202_dual.json': '7f2d011cdf5bed155523823ea575ed0be640db8b0fdd2e6b062a65938443e44c',
    'r28_outputs/weights_303_dual.json': 'b395b800b2497c963c5ed1dcd58f8090b333fcb5b6780c1ec56311b7ccb1e5b6',
}

def check(root):
    root = pathlib.Path(root)
    for file, expected in FROZEN.items():
        assert hashlib.sha256((root / file).read_bytes()).hexdigest() == expected, file
    q = [json.loads(s) for s in (root/'r28_experiment/manifest.jsonl').read_text().splitlines()]
    assert len(q) == 136 and len({x['Q'] for x in q}) == 136
    assert collections.Counter(x['split'] for x in q) == SPLITS
    assert all(len(x['Q']) == 39 and x['Q'].startswith('01') and set(x['Q']) <= {'0', '1'} for x in q)
    rows = [json.loads(s) for s in (root/'r28_outputs/raw_results.jsonl').read_text().splitlines()]
    assert len(rows) == 136 * 3 * 3
    assert collections.Counter((x['arm'],x['seed'],x['split']) for x in rows) == {
        (arm,seed,split): n for arm in ARMS for seed in SEEDS for split,n in SPLITS.items()}
    d = {}
    for arm in ARMS:
        for seed in SEEDS:
            for split, count in SPLITS.items():
                sub = [z for z in rows if z['arm']==arm and z['seed']==seed and z['split']==split]
                assert len(sub)==count
                for z in sub:
                    assert z['first_correct'] == (z['actual'][:6] == z['expected'][:6])
                    assert z['exact'] == (z['actual'] == z['expected'])
                    if z['r']==2:
                        assert z['stop_at_correct_prefix'] is None
                d[(arm,seed,split,'first')] = sum(z['first_correct'] for z in sub)
                d[(arm,seed,split,'exact')] = sum(z['exact'] for z in sub)
                d[(arm,seed,split,'STOP')] = sum(z['stop_at_correct_prefix'] for z in sub if z['r']==1)
    score=lambda arm,split,metric: sum(d[(arm,s,split,metric)] for s in SEEDS)
    old,new='R27_highonly','R28_half_near'
    near=score(new,'test_near_transfer','first')-score(old,'test_near_transfer','first')
    high=score(new,'test_unseen_high','first')-score(old,'test_unseen_high','first')
    stop=score(new,'test_unseen_high','STOP')-score(old,'test_unseen_high','STOP')
    seed_high={s:d[(new,s,'test_unseen_high','first')]-d[(old,s,'test_unseen_high','first')] for s in SEEDS}
    retention=all(d[(new,s,sp,'exact')]-d[(old,s,sp,'exact')] >= -4 for s in SEEDS for sp in ('seen_baseline','taught_high'))
    success = near>=8 and high>=-6 and all(x>=-4 for x in seed_high.values()) and stop>=-6 and retention
    assert (near,high,stop,seed_high,success)==(16,-8,1,{101:0,202:-16,303:8},False)
    recorded=json.loads((root/'r28_outputs/results.json').read_text())
    assert recorded['status'] == ('PASS' if success else 'FAIL')
    assert (recorded['test_near_first_gain_48'],recorded['test_unseen_first_delta_48'],recorded['test_unseen_STOP_delta_48']) == (near,high,stop)
    numpy=json.loads((root/'r28_outputs/numpy_audit.json').read_text())
    assert numpy['raw01_full_generation_rows_verified'] == 1224
    print('R28 PUBLIC INTEGRITY + RECORDED-METRIC AUDIT PASS; gate=FAIL; near=',near,'high=',high,'stop=',stop,'seed_deltas=',seed_high)
    print('This checks the recorded raw01 log and hashes, NOT new NN inference; run the archive PyTorch and NumPy replay separately.')

if __name__ == '__main__':
    check(sys.argv[1] if len(sys.argv)>1 else '.')
