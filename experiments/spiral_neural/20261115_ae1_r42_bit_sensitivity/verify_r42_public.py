#!/usr/bin/env python3
"""Public read-only R42 summary audit. Requires extracted companion ZIP (not Git-only)."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
out = root / 'r42_outputs'
result = json.loads((out / 'results.json').read_text())

def records(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def verify_hash(path, expected):
    got = sha256(path.read_bytes()).hexdigest()
    assert got == expected, (path.name, got, expected)

verify_hash(root / 'r42_prereg.json', result['prereg_sha'])
verify_hash(root / 'r42_manifest.jsonl', result['manifest_sha'])
verify_hash(root / 'r42_bitprobe.py', result['runner_sha'])
verify_hash(out / 'raw_answers.jsonl', result['raw_answers_sha'])
verify_hash(out / 'raw_edges.jsonl', result['raw_edges_sha'])
a = records(out / 'raw_answers.jsonl')
e = records(out / 'raw_edges.jsonl')
assert len(a) == 288 and len(e) == 288
assert set(x['arm'] for x in a) == {'R38_hard', 'R41_paired'}
assert all(len(x['Q']) == 39 and set(x['Q']) <= set('01') for x in a)
for arm in ('R38_hard', 'R41_paired'):
    aa = [x for x in a if x['arm'] == arm]
    assert len(aa) == 144
    assert sum(x['second_correct'] for x in aa) == 96
    assert sum(x['exact'] for x in aa) == 1
    assert sum(x['second_correct'] for x in aa if x['b'] in (24, 25)) == 0
    for lo, hi, bit in ((18,26,1),(19,27,1),(24,26,3),(25,27,3),(24,25,4),(26,27,4)):
        ee = [x for x in e if x['arm']==arm and x['low_b']==lo and x['high_b']==hi]
        assert len(ee)==24 and all(x['flipped_information_bit']==bit for x in ee)
        assert all(x['positive_shift'] for x in ee)
        assert sum(x['both_bit_correct'] for x in ee) == (0 if lo in (24,25) and hi in (26,27) else 24)
assert result['gate'] == 'FAIL' and result['training_updates_this_run'] == 0
assert result['totals']['forward_calls'] == 8462
print('R42 read-only audit PASS: sha256, 288 answers, 288 paired bit responses, 0/48 low-b generalization; predeclared FAIL')
print('NOTE: This is a data integrity check, not a neural forward-pass replay.')
