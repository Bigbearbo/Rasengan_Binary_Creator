"""Independently verify the raw-frame interpretation, inherited decoder and grouped splits."""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np

BITS = np.array([64, 32, 16, 8, 4, 2, 1])
CODES = [14, 15, 4, 5, 6, 7, 8, 16, 17, 9, 10, 11, 12, 13]
SEEDS = (101, 202, 303)


def digest(arr):
    return hashlib.sha256(arr.tobytes(order='C')).hexdigest()


def audit(root):
    src = root / "inherited"
    data = json.loads((src / "data.json").read_bytes())
    cache_hashes = json.loads((src / "pr133_cache_hashes.json").read_bytes())
    groups_seen = set()
    unique_raw = set()
    counts = {}
    for panel_name, rows in data['panels'].items():
        codes = np.array([row['op'] for row in rows])
        left = np.array([row['a'] for row in rows])
        right = np.array([row['b'] for row in rows])
        ids = np.array([row['case_id'] for row in rows])
        raw_str = [row['frame_bits'] for row in rows]
        assert len(set(raw_str)) == len(raw_str)
        assert not unique_raw.intersection(raw_str)
        unique_raw.update(raw_str)
        ordered = {(int(a), int(b)) for a, b in zip(left, right)}
        groups = {tuple(sorted(pair)) for pair in ordered}
        assert groups == {tuple(p) for p in data['group_splits'][panel_name]}
        assert not groups_seen.intersection(groups)
        groups_seen |= groups
        assert all((b,a) in ordered for a,b in ordered)
        assert len(rows) == 4 * len(ordered)
        raw = (np.frombuffer(''.join(raw_str).encode('ascii'),dtype=np.uint8).reshape(-1,34) - 48)
        assert np.all((raw == 0) | (raw == 1))
        assert np.all(left+right < 128)
        for seed in SEEDS:
            with np.load(src / 'sources' / f'receiver_seed{seed}.npz', allow_pickle=False) as src_ckpt:
                w1,b1,w2,b2 = (src_ckpt['param_'+k] for k in ('W1','b1','W2','b2'))
            hidden = np.tanh(raw @ w1 + b1)
            readout = hidden @ w2 + b2
            pred_op = readout[:,:4].argmax(1)
            words = np.asarray(readout[:,CODES]>=0,dtype=np.uint8)
            assert np.array_equal(pred_op,codes)
            assert np.array_equal(words[:,:7] @ BITS, left)
            assert np.array_equal(words[:,7:] @ BITS, right)
            for k,arr in [('pred_op',pred_op),('words',words),('case_ids',ids)]:
                assert digest(arr) == cache_hashes[str(seed)][panel_name][k]
        counts[panel_name] = {'frames':len(rows),'unordered_pairs':len(groups),
                              'ordered_pairs':len(ordered),'ties':int(np.sum(left==right)),
                              'operand_predictions_correct_per_seed':len(rows)}
    return {'raw_source_check':'PASS','seeds':list(SEEDS),'panels':counts,
            'unique_raw_frames':len(unique_raw),'total_across_receivers':len(unique_raw)*len(SEEDS),
            'unique_unordered_pairs':len(groups_seen),
            'claim':'Recomputed from raw frames and source weights. SHA256 of actual decoded words matches all saved PR133 source cache records.'}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment",type=Path)
    print(json.dumps(audit(parser.parse_args().experiment),indent=2))
