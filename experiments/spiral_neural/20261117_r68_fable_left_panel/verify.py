#!/usr/bin/env python3
"""Independent readback of R68 synthetic payload-only panel (no model or Fable codec)."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('panel', type=Path)
p.add_argument('--sha256', default='746a07126c6e748beb1417ed30d67945d01d792505bee6a0f355e5b043f9b058')
a = p.parse_args()
b = a.panel.read_bytes()
assert hashlib.sha256(b).hexdigest() == a.sha256
rows = [json.loads(s) for s in b.splitlines()]
assert len(rows) == 720
by_group = collections.defaultdict(dict)
by_set = {}
counts = collections.Counter()
for r in rows:
    bits = r['synthetic_payload_word_bits']
    key = tuple(sorted(bits))
    assert r['status'] == 'SYNTHETIC_PAYLOAD_ONLY_NOT_FABLE_CODEC_VERIFIED'
    assert r['question_raw_151_bits'] is None and r['expected_full_41bit_answer'] is None
    assert len(bits) in (3,4) and len(bits) == len(set(bits))
    assert all(len(w)==8 and w[7]=='0' and set(w) <= {'0','1'} for w in bits)
    assert r['case_id'] == r['group_id'] + ':' + r['op']
    assert key not in by_set or by_set[key] == r['split']
    by_set[key] = r['split']
    assert r['op'] not in by_group[r['group_id']]
    by_group[r['group_id']][r['op']] = r
    counts[(len(bits),r['split'],r['op'])] += 1
assert len(by_set)==len(by_group)==240
for group in by_group.values():
    assert set(group)=={'ECHO','REV','LEFT'}
    base = group['ECHO']['synthetic_payload_word_bits']
    assert all(r['synthetic_payload_word_bits']==base for r in group.values())
    assert group['ECHO']['expected_decoded_word_bits']==base
    assert group['REV']['expected_decoded_word_bits']==base[::-1]
    assert group['LEFT']['expected_decoded_word_bits']==base[1:]+base[:1]
    assert len({tuple(x['expected_decoded_word_bits']) for x in group.values()})==3
for n in (3,4):
    for split,expected in {'train':72,'val':24,'test':24}.items():
        for op in ('ECHO','REV','LEFT'):
            assert counts[(n,split,op)]==expected
print('PASS independent file SHA, 720 cases, 240 groups, 3/4 distinct tokens, pairwise operation targets, isolated group splits, 432/144/144 cases')
print('NOT TESTED: Fable codec legality, 151-bit questions, 41-bit answer framing, model learning')
