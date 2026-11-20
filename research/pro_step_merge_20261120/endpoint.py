"""Identify a compact local arithmetic rule from whole answers or labeled transitions."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np


BUDGETS = (1, 2, 4, 8, 16, 32, 64)


def local_table(weights):
    """Rows are indexed (A_digit * 4 + B_digit) * 2 + previous carry."""
    features = np.array([
        [a & 1, a >> 1, b & 1, b >> 1, carry, 1]
        for a in range(4) for b in range(4) for carry in range(2)
    ], dtype=np.int16)
    return np.clip(weights @ features.T, 0, 7).astype(np.uint8)


def filter_paper(survivors, tables, a, b, use_steps):
    carry = np.zeros(survivors.size, dtype=np.uint8)
    partial = np.zeros(survivors.size, dtype=np.int16)
    keep = np.ones(survivors.size, dtype=bool)
    for shift in (0, 2, 4, 6):
        da, db = (a >> shift) & 3, (b >> shift) & 3
        output = tables[survivors, (da * 4 + db) * 2 + carry]
        carry = output >> 2
        partial |= (output.astype(np.int16) & 3) << shift
        if use_steps:
            prefix_mask = (1 << (shift + 2)) - 1
            exact_prefix = (a & prefix_mask) + (b & prefix_mask)
            keep &= (partial == (exact_prefix & prefix_mask)) & (carry == (exact_prefix >> (shift + 2)))
    keep &= (partial + (carry.astype(np.int16) << 8)) == a + b
    return survivors[keep]


def exhaustive(table):
    a = np.repeat(np.arange(256, dtype=np.int32), 256)
    b = np.tile(np.arange(256, dtype=np.int32), 256)
    partial = np.zeros_like(a)
    carry = np.zeros_like(a)
    trace = np.ones(a.size, dtype=bool)
    for shift in (0, 2, 4, 6):
        da, db = (a >> shift) & 3, (b >> shift) & 3
        out = table[(da * 4 + db) * 2 + carry].astype(np.int32)
        partial |= (out & 3) << shift
        carry = out >> 2
        mask = (1 << (shift + 2)) - 1
        true_prefix = (a & mask) + (b & mask)
        trace &= partial + (carry << (shift + 2)) == true_prefix
    return {'final_correct':int(np.sum(partial + (carry << 8) == a+b)),
            'every_prefix_and_final_correct':int(trace.sum())}


def run():
    weights = np.array(sorted(itertools.product(range(-2,3), repeat=6),
                             key=lambda w:(sum(v*v for v in w), w)),dtype=np.int16)
    tables = local_table(weights)
    cache = {}
    trials = []
    summary = {}
    for seed in range(20261120,20261136):
        pair_ids = np.random.default_rng(seed).choice(65536,64,replace=False).tolist()
        trial = {'seed':seed, 'training_pairs':pair_ids,'arms':{}}
        for arm in ('endpoint','local'):
            survivors = np.arange(len(weights))
            checkpoints = []
            for n,pair in enumerate(pair_ids,start=1):
                a,b = divmod(pair,256)
                survivors = filter_paper(survivors,tables,a,b,arm=='local')
                if n in BUDGETS:
                    index = int(survivors[0])
                    cache_key = tables[index].tobytes()
                    if cache_key not in cache:
                        cache[cache_key] = exhaustive(tables[index])
                    record = dict(cache[cache_key],papers=n,remaining=int(survivors.size),
                                  selected_weights=weights[index].tolist(),table=tables[index].tolist())
                    checkpoints.append(record)
            trial['arms'][arm] = checkpoints
        trials.append(trial)
    for arm in ('endpoint','local'):
        summary[arm]={}
        for i,n in enumerate(BUDGETS):
            v=[t['arms'][arm][i] for t in trials]
            counts=[k['remaining'] for k in v]
            summary[arm][n]={'seeds':len(v),'unique_coefficients':counts.count(1),
                'median_remaining':float(np.median(counts)), 'range_remaining':[min(counts),max(counts)],
                'perfect_trace':sum(r['every_prefix_and_final_correct']==65536 for r in v),
                'perfect_final':sum(r['final_correct']==65536 for r in v)}
    return {'candidate_count':len(weights),'distinct_truth_tables_checked':len(cache),'summary':summary,'trials':trials}


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--out',type=Path,default=Path('endpoint.json'))
    args=cli.parse_args()
    data=run()
    args.out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(data['summary']))
