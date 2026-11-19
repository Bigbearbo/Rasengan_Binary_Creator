"""Compare decoded multiplication-by-three answers with the audit's seven functions.

Run ``python score_answers.py answers.csv`` or ``python score_answers.py --self-test``.
UTF-8 CSV columns: arm,x,status,answer. Each arm may contain a subset of x=0..127.
Use status=valid only for submitted, fully decoded answers (unsigned decimal).
Use invalid for rejected formatting and unsubmitted for a missing submission.
Leave answer blank for both. Omit truly unobserved rows. Extra named columns are
ignored. Numeric agreement here never substitutes for the project's official score.
"""

import argparse
import csv
import io
import json
from itertools import combinations

from research import predictions


FIELDS = ('arm', 'x', 'status', 'answer')
STATUSES = ('valid', 'invalid', 'unsubmitted')


def unsigned_decimal(text, field, line):
    if not (text.isascii() and text.isdecimal()):
        raise ValueError(f'line {line}: {field} must be an unsigned decimal integer')
    return int(text)


def read_answers(stream):
    reader = csv.DictReader(stream, strict=True)
    header = reader.fieldnames or []
    if not set(FIELDS).issubset(header) or len(header) != len(set(header)) or '' in header:
        raise ValueError('expected distinct column names including arm,x,status,answer')
    arms = {}
    for row in reader:
        line = reader.line_num
        if None in row or any(row[key] is None for key in FIELDS):
            raise ValueError(f'line {line}: number of fields does not match the required columns')
        arm, x_text, status, answer_text = (row[key].strip() for key in FIELDS)
        x = unsigned_decimal(x_text, 'x', line)
        if not arm or x > 127 or status not in STATUSES:
            raise ValueError(f'line {line}: require an arm, x=0..127 and status in {STATUSES}')
        records = arms.setdefault(arm, {})
        if x in records:
            raise ValueError(f'line {line}: duplicate input {x} for arm {arm!r}')
        if status == 'valid':
            answer = unsigned_decimal(answer_text, 'answer', line)
        elif answer_text:
            raise ValueError(f'line {line}: leave answer blank when status={status}')
        else:
            answer = None
        records[x] = (status, answer)
    if not arms:
        raise ValueError('no observed rows in CSV')
    return arms


def score_arm(records):
    names = tuple(predictions(0))
    pairs = [dict(a=a, b=b, distinguishable=0, matches_a=0, matches_b=0, neither=0)
             for a, b in combinations(names, 2)]
    statuses = dict.fromkeys(STATUSES, 0)
    exact = unique = tied = unmatched = 0
    rows = []
    for x, (status, answer) in sorted(records.items()):
        statuses[status] += 1
        entry = {'x': x, 'status': status}
        rows.append(entry)
        if status != 'valid':
            continue
        values = predictions(x)
        matches = [name for name in names if values[name] == answer]
        entry.update(answer=answer, matches=matches)
        exact += int(answer == values['true_mul3'])
        unique += int(len(matches) == 1)
        tied += int(len(matches) > 1)
        unmatched += int(not matches)
        for pair in pairs:
            a, b = values[pair['a']], values[pair['b']]
            if a == b:
                continue
            pair['distinguishable'] += 1
            if answer == a:
                pair['matches_a'] += 1
            elif answer == b:
                pair['matches_b'] += 1
            else:
                pair['neither'] += 1
    return {'observed': len(records), 'unobserved_of_128': 128 - len(records),
            'status_counts': statuses, 'numeric_correct_of_valid': exact,
            'valid_by_number_of_matches': {'one': unique, 'multiple': tied, 'none': unmatched},
            'pairwise_on_valid_disagreements': pairs, 'rows': rows}


def self_test():
    header = 'arm,x,status,answer\n'
    raw = header + 'A,0,valid,0\nA,3,valid,5\nA,9,invalid,\nA,11,unsubmitted,\nB,0,valid,1\n'
    arms = read_answers(io.StringIO(raw))
    result = score_arm(arms['A'])
    assert result['status_counts'] == {'valid': 2, 'invalid': 1, 'unsubmitted': 1}
    assert result['numeric_correct_of_valid'] == 1 and result['unobserved_of_128'] == 124
    assert len(result['rows'][0]['matches']) == 7 and 'xor' in result['rows'][1]['matches']
    assert 'matches' not in result['rows'][2] and 'matches' not in result['rows'][3]
    pair = next(p for p in result['pairwise_on_valid_disagreements'] if {p['a'], p['b']} == {'xor', 'or'})
    assert pair['distinguishable'] == 1 and pair['matches_a' if pair['a'] == 'xor' else 'matches_b'] == 1
    assert score_arm(arms['B'])['valid_by_number_of_matches']['none'] == 1
    for bad in ('A,1,valid,3\nA,1,valid,3', 'A,0,invalid,3', 'A,128,valid,1',
                'A,3,valid,5.5', 'A,3,valid,', 'A,3,unknown,', 'A,-1,valid,0'):
        try:
            read_answers(io.StringIO(header + bad))
        except ValueError:
            continue
        raise AssertionError(f'should reject {bad!r}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('csv_file', nargs='?')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print('PASS synthetic fixture')
        return
    if not args.csv_file:
        parser.error('supply a CSV path or --self-test')
    try:
        with open(args.csv_file, encoding='utf-8-sig', newline='') as stream:
            arms = read_answers(stream)
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(2, f'{exc}\n')
    print(json.dumps({arm: score_arm(rows) for arm, rows in arms.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
