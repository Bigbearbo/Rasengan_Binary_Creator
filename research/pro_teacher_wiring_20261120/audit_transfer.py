"""Independent arithmetic reconstruction of every archived checkpoint's student behavior."""
import argparse
import json
from pathlib import Path

import numpy as np


def make_boards():
    ids = np.arange(65536)
    a, b = ids // 256, ids % 256
    boards = []
    gold = []
    for k in range(8):
        mask = (1 << k) - 1
        # Shift the unconsumed operand right. Already emitted low sum bits fill A's high end.
        stored_a = (a >> k) | (((a+b) & mask) << (8-k))
        stored_b = (256+b) >> k
        carry = (((a & mask)+(b & mask)) >> k).astype(bool)
        columns = [((stored_a >> j) & 1).astype(bool) for j in range(8)]
        columns.extend(((stored_b >> j) & 1).astype(bool) for j in range(9))
        columns.append(carry)
        boards.append(columns)
        next_mask = (1 << (k+1))-1
        gold.append((a & next_mask) < (b & next_mask))
    return boards, gold


def replay(params, boards, gold):
    state = np.zeros(65536,dtype=bool)
    matched = np.ones_like(state)
    for inputs, y in zip(boards,gold,strict=True):
        z = np.zeros(len(state))
        for channel,weight in zip(inputs,params[:18],strict=True):
            if weight:
                z += np.where(channel,weight,0.)
        state = z + np.where(state,params[18],0.) + params[19] >= 0
        matched &= state==y
    return (state == gold[-1]), matched


def run(path):
    j = json.loads(path.read_text())
    boards, gold = make_boards()
    matched, cache = 0, {}
    for arm,rows in j["trials"].items():
        for meta,row in zip(j["pair_metadata"],rows,strict=True):
            assert meta["seed"]==row["seed"]
            for t,c in row["checkpoints"].items():
                w=tuple(c["weights_canonical"])
                if w not in cache:
                    end,trace = replay(w,boards,gold)
                    cache[w] = (end, int(end.sum()),int(trace.sum()))
                end,ec,tc=cache[w]
                assert ec==c["full_endpoint"] and tc==c["full_trace"], (arm,row["seed"],t,ec,tc)
                assert int(end[meta["training_ids"]].sum())==c["train_endpoint"]
                matched+=1
    print(json.dumps({"checkpoint_rows_verified":matched,"distinct_parameter_vectors":len(cache),
                      "exhaustive_ordered_8bit_pairs":65536,"rounds":8,
                      "metrics":["endpoint","all eight borrows","training endpoints"],
                      "oracle":"closed-form original board from operand prefixes; distinct direct weighted forward"}))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results",type=Path)
    run(parser.parse_args().results)
