"""Train a new recurrent borrow bit on frozen 8-bit S1. Pass the original serial_adder.py."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

import numpy as np


SOURCE_SHA = "6d5523276727d265211b1c35a950006053220b97c4489578a10540217e4e0d8d"
SOURCE_NAMES = {"Net", "full_add_bit", "build_S1", "board_of", "val"}
COLUMNS = [f"A{i}" for i in range(8)] + [f"B{i}" for i in range(9)] + ["C", "borrow", "bias"]


def source_network(path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError("Unexpected source revision.")
    definitions = [
        node for node in ast.parse(raw, filename=str(path)).body
        if getattr(node, "name", "") in SOURCE_NAMES or
        (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "M")
    ]
    namespace = {"np": np}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["build_S1"]()


def build_snapshots(path):
    model, encode, decode = source_network(path)
    assert model.pos == {"A": (0, 8), "B": (8, 9), "C": (17, 1)}
    pairs = np.arange(65536, dtype=np.int32)
    a, b = pairs // 256, pairs % 256
    w1, bias, w2 = (array.astype(np.int32) for array in model.mats())
    board = encode(a, b).astype(np.int32)
    boards = np.empty((8, len(pairs), model.nin), dtype=np.int32)
    truth = np.empty((8, len(pairs)), dtype=np.int32)
    for bit in range(8):
        boards[bit] = board
        mask = (1 << (bit + 1)) - 1
        truth[bit] = (a & mask) < (b & mask)
        hidden = ((board @ w1.T + bias) >= 0).astype(np.int32)
        out = hidden @ w2.T
        assert ((out == 0) | (out == 1)).all() and (out[:, -1] == int(bit == 7)).all()
        board = out[:, :-1]
    assert (decode(board) == a + b).all()
    return boards, truth


def train(boards, truth, size, seed):
    rng = np.random.default_rng(seed)
    draws = rng.choice(size * size, size=64, replace=False)
    ids = (draws // size) * 256 + draws % size
    targets = truth[:, ids].T
    x = np.ones((64, 8, 20), dtype=np.int32)
    x[:, :, :18] = boards[:, ids, :].transpose(1, 0, 2)
    x[:, 0, 18] = 0
    x[:, 1:, 18] = targets[:, :-1]
    x = x.reshape(512, 20)
    y = targets.reshape(512)
    weight = np.zeros(20, dtype=np.int32)
    updates = 0
    for epoch in range(1, 65):
        for row in rng.permutation(len(y)):
            pred = int((x[row] @ weight) >= 0)
            if pred != y[row]:
                weight += (y[row] - pred) * x[row]
                updates += 1
        train_correct = int(((x @ weight >= 0) == y).sum())
        if train_correct == len(y):
            break
    outside = np.delete(weight[:19], [0, 8, 18])
    return {
        "seed": seed,
        "ids_sha256": hashlib.sha256(ids.astype("<u4").tobytes()).hexdigest(),
        "epochs": epoch, "updates": updates, "fit": train_correct == 512,
        "training_rows_correct": train_correct, "weights": weight.tolist(),
        "nonzero_outside_three_fields": int(np.count_nonzero(outside)),
    }


def autonomous_scores(boards, truth, rows):
    # All columns have integer precision. Each trial has its own previous prediction.
    weights = np.array([r["weights"] for r in rows], dtype=np.int32)
    own_readback = np.zeros((65536, len(rows)), dtype=np.int32)
    correct = np.ones_like(own_readback, dtype=bool)
    for bit in range(8):
        preactivation = boards[bit] @ weights[:, :18].T
        preactivation += own_readback * weights[:, 18]
        preactivation += weights[:, 19]
        own_readback = (preactivation >= 0).astype(np.int32)
        correct &= own_readback == truth[bit, :, None]
    for row, count in zip(rows, correct.sum(axis=0)):
        row["exact_sequences_correct"] = int(count)


def summary(rows):
    scores = [r["exact_sequences_correct"] for r in rows]
    outside = [r["nonzero_outside_three_fields"] for r in rows]
    return {
        "seeds": len(rows), "table_fit_seeds": sum(r["fit"] for r in rows),
        "all_domain_perfect_seeds": sum(v == 65536 for v in scores),
        "min_exact_sequences_correct": min(scores),
        "median_exact_sequences_correct": float(np.median(scores)),
        "max_exact_sequences_correct": max(scores),
        "median_exact_sequence_fraction": float(np.median(scores) / 65536),
        "median_nonzero_outside_three_fields": float(np.median(outside)),
        "min_nonzero_outside_three_fields": min(outside), "max_nonzero_outside_three_fields": max(outside),
        "min_updates": min(r["updates"] for r in rows), "max_updates": max(r["updates"] for r in rows),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    boards, truth = build_snapshots(args.source)
    groups = {name: [train(boards, truth, size, 20261120 + i) for i in range(16)]
              for name, size in (("full", 256), ("short", 16))}
    autonomous_scores(boards, truth, groups["full"] + groups["short"])
    result = {
        "source_sha256": SOURCE_SHA, "weight_column_order": COLUMNS,
        "domains": {"full": [0, 255], "short": [0, 15]}, "cases_per_seed": 64,
        "training_rows_per_seed": 512, "maximum_epochs": 64, "sequence_length": 8,
        "exhaustive_test_pairs": 65536, "exhaustive_original_addition_matches": 65536,
        "summary": {name: summary(rows) for name, rows in groups.items()}, "trials": groups,
    }
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
