"""Read-only R38 integrity checker for extracted conversation companion ZIP.

No neural student is trained or inferred by this script. For actual 01 NN
generation replay, use the SHA-frozen r38_b_curriculum.py from the companion.
"""
from pathlib import Path
import hashlib
import json
import collections

R = Path(__file__).resolve().parent
digest = lambda path: hashlib.sha256((R / path).read_bytes()).hexdigest()
prereg = json.loads((R / 'r38_prereg.json').read_text())
assert digest('r38_b_curriculum.py') == prereg['runner_sha256']
assert digest('r38_manifest.jsonl') == prereg['manifest_sha256']
assert prereg['work_id'] == 'SLE-AE1-R38-SS-B-CURRICULUM-20261115'
cases = [json.loads(line) for line in (R / 'r38_manifest.jsonl').read_text().splitlines()]
assert len(cases) == 128 and len({c['Q'] for c in cases}) == 128
assert all(len(c['Q']) == 39 and set(c['Q']) <= set('01') for c in cases)
res = json.loads((R / 'r38_outputs/results.json').read_text())
records = [json.loads(line) for line in (R / 'r38_outputs/raw_results.jsonl').read_text().splitlines()]
assert res['raw_sha'] == digest('r38_outputs/raw_results.jsonl')
assert len(records) == 768
expected = {
    (arm, seed, split): n
    for arm in ('R31_original', 'R38_lessons')
    for seed in (101, 202, 303)
    for split, n in (
        ('heldout_high_b', 16), ('known_b', 16),
        ('removed_b', 16), ('prior_r1_retention', 80),
    )
}
assert collections.Counter(
    (r['arm'], r['seed'], r['split']) for r in records
) == expected
for seed, sha256 in res['new_student_shas'].items():
    assert digest('r38_outputs/weights_' + seed + '_dual.json') == sha256
for arm in ('R31_original', 'R38_lessons'):
    for split, group in res['by_arm'][arm].items():
        rows = [r for r in records if r['arm'] == arm and r['split'] == split]
        assert len(rows) == group['n']
        assert sum(r['exact'] for r in rows) == group['exact']
        assert sum(r['second_correct'] or False for r in rows) == group['second_correct']
assert res['gate'] == 'PASS' and all(res['checks'].values())
assert res['by_arm']['R31_original']['heldout_high_b']['second_correct'] == 0
assert res['by_arm']['R38_lessons']['heldout_high_b']['second_correct'] == 48
print('R38 RECORD PASS 768 rows, 3 weight SHAs, 4 frozen prereg gates')
