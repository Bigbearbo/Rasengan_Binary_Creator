#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

base = Path(__file__).resolve().parents[1]
rows = [json.loads(line) for line in (base/'fixtures/math_v0_1.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(rows) == 652
assert len({r['case_id'] for r in rows}) == 652
payload = ''.join(f"{r['l1_order']} {r['max_layer']} {r['bits']}\n" for r in rows)
run = subprocess.run([str(base/'build/math_profile_cli')], input=payload, text=True,
                     capture_output=True, check=True)
actual = run.stdout.splitlines()
assert len(actual) == len(rows)
for row, answer in zip(rows, actual):
    assert row['profile'] == 'math-v0.1'
    expected = row['expected']
    assert answer == f"{expected['answer_bits']} {expected['value']}", row['case_id']
print(f"PASS independent JSONL fixture: {len(rows)} cases, unique IDs, exact answers")
bad = [
    (5, 1, '01' + '100000' + '11110', 'UNKNOWN_TOKEN 2'),
    (4, 1, '01' + '10100' + '11010' + '11110', 'NUMERIC_RANGE 7'),
]
probe = subprocess.run([str(base/'build/math_profile_cli')],
                       input=''.join(f'{n} {layer} {bits}\n' for n, layer, bits, _ in bad),
                       text=True, capture_output=True, check=True)
assert probe.stdout.splitlines() == [expected for _, _, _, expected in bad]
