"""No-Torch no-training independent F32 verifier for the companion SLE-AE1 c3 ZIP.
Extract the companion ZIP to a folder, then: OPENBLAS_NUM_THREADS=1 python verify_numpy.py
The repo alone does not include checkpoints/raw_cases.jsonl. Never silently use an oracle in place of real model inference.
"""
import base64, hashlib, json
from pathlib import Path
import numpy as np

P = Path(__file__).resolve().parent

def digest(data):
    return hashlib.sha256(data).hexdigest()

def weights(seed, arm):
    tag = 'conjunction' if arm == 'frozen_c1_control' else 'balanced_c'
    path = P / 'checkpoints' / f'weights_seed{seed}_{tag}.json'
    prereg = json.loads((P / 'PREREGISTRATION.json').read_text())
    assert digest(path.read_bytes()) == prereg['checkpoint_sha256'][f'{seed}_{arm}']
    blob = json.loads(path.read_text())
    tensors = {
        k: np.frombuffer(base64.b64decode(v['little_endian_base64']), '<f4').copy().reshape(v['shape'])
        for k, v in blob['tensors'].items()
    }
    h = hashlib.sha256()
    for k, v in tensors.items():
        h.update(k.encode())
        h.update(v.tobytes())
    assert h.hexdigest() == blob['weights_sha256']
    assert sum(x.size for x in tensors.values()) == 10499
    return tensors['0.weight'], tensors['0.bias'], tensors['2.weight'], tensors['2.bias']

def parse_question(q):
    assert len(q) == 39 and q.startswith('01010') and q[8] == '0'
    assert q.endswith('111100') and set(q) <= {'0', '1'}
    r = int(q[5:8], 2)
    words = [q[9 + 6 * i:15 + 6 * i] for i in range(4)]
    assert r == 2 and all(w[-1] == '0' and int(w[:5], 2) <= 29 for w in words)
    return (r,) + tuple(int(w[:5], 2) for w in words)

def next_symbol(model, prefix):
    assert 0 < len(prefix) <= 80 and set(prefix) <= {'0','1'}
    x = np.zeros(160, np.float32)
    for i, bit in enumerate(prefix):
        x[2 * i + int(bit)] = np.float32(1)
    w1, b1, w2, b2 = model
    h = np.tanh(w1 @ x + b1).astype(np.float32)
    return '01S'[int(np.argmax(w2 @ h + b2))]

def generate(model, q):
    s = ''
    for t in range(32):
        if len(q) + len(s) > 80:
            return s, 'overflow', t
        s += next_symbol(model, q + s)
        if s.endswith('S'):
            return s, 'stop', t + 1
    return s, 'cap', 32

def main():
    manifest = json.loads((P / 'RESULTS.json').read_text())
    raw = (P / 'raw_cases.jsonl').read_bytes()
    assert digest(raw) == manifest['raw_sha256']
    cases = [json.loads(line) for line in raw.decode().splitlines()]
    assert len(cases) == manifest['raw_rows'] == 448
    models = {(s,a): weights(s,a) for s in (101,202)
              for a in ('frozen_c1_control', 'balanced_c')}
    steps = 0
    index = {}
    for i, row in enumerate(cases):
        r,a,b,c,d = parse_question(row['Q'])
        assert (r,a,b,c,d) == tuple(row[k] for k in ('r','a','b','c','d'))
        assert a in (4,5) and b in (26,27) and 2 <= c <= 29 and d == 0
        assert row['split'] == ('val' if a == 4 else 'test')
        expected = f'{a:05b}0' + f'{b:05b}0' + 'S'
        assert row['expected'] == expected
        output,cause,n = generate(models[row['seed'],row['arm']], row['Q'])
        assert (output,cause,n) == (row['actual'],row['cause'],row['forward_calls']), (i,output,row['actual'])
        assert row['exact'] == (output == expected)
        assert row['proper_stop'] == (cause == 'stop' and len(output) == len(expected))
        key = row['seed'],row['arm'],a,b,c
        assert key not in index
        index[key] = row
        steps += n
    assert steps == manifest['forward_calls'] == 5824
    assert steps * 10432 == manifest['inference_dense_MAC']
    positive = []
    for seed in (101,202):
        for arm in ('frozen_c1_control','balanced_c'):
            paired = [(index[seed,arm,a,b,2], index[seed,arm,a,b,3])
                      for a in (4,5) for b in (26,27)]
            score = {
                'n': 4, 'c2_correct': sum(z['exact'] for z,w in paired),
                'c3_correct': sum(w['exact'] for z,w in paired),
                'identical_pair': sum(z['actual'] == w['actual'] for z,w in paired)
            }
            score['success'] = all(score[k] == 4 for k in ('c2_correct','c3_correct','identical_pair'))
            assert score == manifest['primary'][f'{seed}_{arm}']
            if arm == 'balanced_c': positive.append(score['success'])
    assert all(positive) == manifest['primary_gate_pass']
    print('INDEPENDENT NUMPY PASS: 448/448 generated answers; 5824 model forwards; 60755968 dense MAC; gate', manifest['primary_gate_pass'])

if __name__ == '__main__':
    main()
