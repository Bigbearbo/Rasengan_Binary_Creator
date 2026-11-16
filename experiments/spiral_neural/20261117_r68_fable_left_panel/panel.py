#!/usr/bin/env python3
"""R68 paired LEFT evaluation panel. Only synthetic payload words; NOT full Fable Q/A."""
import argparse
import hashlib
import itertools
import json
import platform
import random
from collections import Counter, defaultdict
from pathlib import Path

SEED = 20261117
OPS = ('ECHO', 'REV', 'LEFT')
SPLITS = ('train', 'val', 'test')
COUNTS = {'train': 72, 'val': 24, 'test': 24}  # per word count


def target(op, words):
    if op == 'ECHO':
        return list(words)
    if op == 'REV':
        return list(reversed(words))
    if op == 'LEFT':
        return list(words[1:]) + [words[0]]
    raise ValueError('unknown operation')


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def build():
    rng = random.Random(SEED)
    vocab = [f'{v:07b}0' for v in range(1, 17)]
    rows = []
    for n in (3, 4):
        candidates = list(itertools.combinations(vocab, n))
        rng.shuffle(candidates)
        selected = candidates[:sum(COUNTS.values())]
        for i, chosen in enumerate(selected):
            split = ('train' if i < COUNTS['train']
                     else 'val' if i < COUNTS['train']+COUNTS['val'] else 'test')
            words = list(chosen)
            rng.shuffle(words)
            group_id = checksum(('R68|' + '|'.join(sorted(words))).encode())[:20]
            order_targets = {op: target(op, words) for op in OPS}
            if len({tuple(t) for t in order_targets.values()}) != 3:
                raise AssertionError('operator targets collided')
            for op in OPS:
                rows.append({
                    'case_id': f'{group_id}:{op}',
                    'group_id': group_id,
                    'split': split,
                    'n_words': n,
                    'op': op,
                    'synthetic_payload_word_bits': words,
                    'expected_decoded_word_bits': order_targets[op],
                    'expected_full_41bit_answer': None,
                    'question_raw_151_bits': None,
                    'status': 'SYNTHETIC_PAYLOAD_ONLY_NOT_FABLE_CODEC_VERIFIED',
                })
    return rows


def audit(rows):
    by_group = defaultdict(list)
    splitgroups = defaultdict(set)
    splitops = Counter()
    ids = set()
    for row in rows:
        caseid = row['case_id']
        assert caseid not in ids, f'duplicate case {caseid}'
        ids.add(caseid)
        words = row['synthetic_payload_word_bits']
        assert len(words) in (3, 4) and len(words) == row['n_words']
        assert len(set(words)) == len(words)
        assert all(len(w) == 8 and w[-1] == '0' and set(w) <= {'0', '1'} for w in words)
        assert row['expected_decoded_word_bits'] == target(row['op'], words)
        assert row['question_raw_151_bits'] is None
        assert row['expected_full_41bit_answer'] is None
        splitops[(row['n_words'], row['split'], row['op'])] += 1
        by_group[row['group_id']].append(row)
        splitgroups[(row['n_words'], row['split'])].add(row['group_id'])
    assert len(rows) == 720 and len(by_group) == 240
    for _, triple in by_group.items():
        assert len(triple) == 3 and {x['op'] for x in triple} == set(OPS)
        assert len({tuple(x['synthetic_payload_word_bits']) for x in triple}) == 1
        assert len({x['split'] for x in triple}) == 1
        assert len({tuple(x['expected_decoded_word_bits']) for x in triple}) == 3
    for n in (3, 4):
        a = [splitgroups[(n, s)] for s in SPLITS]
        assert all(len(a[i] & a[j]) == 0 for i in range(3) for j in range(i+1, 3))
        for split in SPLITS:
            assert len(splitgroups[(n, split)]) == COUNTS[split]
            for op in OPS:
                assert splitops[(n, split, op)] == COUNTS[split]
    # Unordered word sets, including any permutations, do not straddle split boundaries.
    canonical_to_split = {}
    for triple in by_group.values():
        row = triple[0]
        canonical = tuple(sorted(row['synthetic_payload_word_bits']))
        if canonical in canonical_to_split:
            assert canonical_to_split[canonical] == row['split']
        canonical_to_split[canonical] = row['split']
    assert len(canonical_to_split) == 240
    return {'gate': 'PASS', 'rows': 720, 'groups': 240, 'split_rows': {
        s: sum(1 for x in rows if x['split'] == s) for s in SPLITS},
        'split_groups_by_length': {str(n): {s: len(splitgroups[(n, s)]) for s in SPLITS} for n in (3, 4)},
        'pairwise_distinct_target_groups': 240,
        'full_fable_codec_legality': 'NOT_TESTED_MISSING_ORIGINAL_COMPILER',
        'students_trained': 0, 'student_updates': 0, 'student_forward_passes': 0}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit('ERROR: output directory must not exist')
    rows = build()
    report = audit(rows)
    a.out.mkdir(parents=True)
    payload = ''.join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for x in rows).encode('utf-8')
    (a.out / 'panel.jsonl').write_bytes(payload)
    report.update({'seed': SEED, 'python_version': platform.python_version(),
                   'panel_sha256': checksum(payload), 'raw_question_bits_generated': 0,
                   'unverified_synthetic_candidate_words': 16})
    (a.out / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps(report, sort_keys=True))

if __name__ == '__main__':
    main()