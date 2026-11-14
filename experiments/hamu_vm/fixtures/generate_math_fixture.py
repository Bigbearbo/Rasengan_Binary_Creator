#!/usr/bin/env python3
"""Independent integer oracle; run manually when changing the fixed profile."""
import json
from pathlib import Path

def word(value, width, layer=1):
    return format(value, f'0{width}b') + '0' * layer

rows = []
for width in (4, 5):
    for layer in (1, 2):
        prefix = '01' if layer == 1 else '001' + word(1, 3, 2) + word(6, 3, 2) + word(7, 3, 2)
        questions = []
        questions += [(f'E_{a}', a, None, None, a) for a in range(11)]
        questions += [(f'N_{a}', a, 13, None, a + 1) for a in range(10)]
        questions += [(f'P_{a}', a, 14, None, a - 1) for a in range(1, 11)]
        questions += [(f'A_{a}_{b}', a, 12, b, a + b) for a in range(11) for b in range(11 - a)]
        questions += [(f'S_{a}_{b}', a, 11, b, a - b) for a in range(11) for b in range(a + 1)]
        assert len(questions) == 163
        for name, a, op, b, value in questions:
            body = word(a, width)
            if op is not None:
                body += word(op, width)
            if b is not None:
                body += word(b, width)
            body += word(15, width)
            rows.append(dict(case_id=f'{name}_n{width}_L{layer}', profile='math-v0.1', l1_order=width,
                             max_layer=layer, bits=prefix + body,
                             expected=dict(answer_bits=word(value, width) + word(15, width), value=value)))
assert len(rows) == 652
out = Path(__file__).with_name('math_v0_1.jsonl')
out.write_text(''.join(json.dumps(row, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')
