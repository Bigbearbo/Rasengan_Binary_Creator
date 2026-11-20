"""Learn move size from endpoint feedback, timing, or a local demonstration."""
import argparse
from itertools import product
import json
from pathlib import Path

import numpy as np


def encode(a_bank, b_bank, position, width):
    """Index four directly observed tags. Missing observations are zero."""
    a0 = np.bitwise_and(np.right_shift(a_bank, position), 1)
    a1 = np.bitwise_and(np.right_shift(a_bank, position + 1), 1)
    b0 = np.bitwise_and(np.right_shift(b_bank, position), 1)
    b1 = np.bitwise_and(np.right_shift(b_bank, position + 1), 1)
    return 8 * a0 + 4 * a1 + 2 * b0 + b1


def model(s, k, table):
    return {"s": s, "k": k, "table": list(table)}


def action(readout, remaining, group_index):
    wide = np.asarray(readout["table"], dtype=np.int8)[group_index]
    answer = np.where(remaining <= readout["s"], 0,
                      1 + ((remaining >= readout["k"]) & (wide != 0)))
    return int(answer) if np.ndim(answer) == 0 else answer


FINE = model(0, 2, [0] * 16)
ALWAYS_TWO = model(0, 0, [1] * 16)
ORACLE = model(0, 2, [int((a0 == a1) and (b0 == b1))
                      for a0, a1, b0, b1 in product(range(2), repeat=4)])


class Episodes:
    def __init__(self, width, a, b, a_bank, b_bank):
        self.width = width
        self.a, self.b, self.a_bank, self.b_bank = [
            np.asarray(x, dtype=np.int64) for x in (a, b, a_bank, b_bank)
        ]
        self.n = len(self.a_bank)
        self.indices = np.arange(self.n)
        self.codes = np.stack([encode(self.a_bank, self.b_bank, p, width)
                               for p in range(width + 1)])
        # The independent physical checker reads bank bitfields directly.
        self.can_pair = np.zeros((width + 1, self.n), dtype=bool)
        for p in range(width - 1):
            lane_a_changes = ((self.a_bank >> p) ^ (self.a_bank >> (p + 1))) & 1
            lane_b_changes = ((self.b_bank >> p) ^ (self.b_bank >> (p + 1))) & 1
            self.can_pair[p] = (lane_a_changes | lane_b_changes) == 0
        # Independent shortest path over physically legal read operations.
        distance = np.zeros((width + 1, self.n), dtype=np.int16)
        for p in reversed(range(width)):
            distance[p] = 1 + distance[p + 1]
            if p + 2 <= width:
                distance[p] = np.where(self.can_pair[p],
                                       np.minimum(distance[p], 1 + distance[p + 2]),
                                       distance[p])
        self.optimum = distance[0]

    def examples(self):
        return np.stack((self.a, self.b, self.a_bank, self.b_bank), axis=1).tolist()


def training(seed):
    rng = np.random.default_rng(seed)
    operand = rng.integers(0, 256, (2, 64))
    masks = rng.integers(0, 256, (2, 64))
    masks[:, ::4] = rng.integers(0, 2, (2, 16)) * 255
    return Episodes(8, *operand, *masks)


def rollout(data, readout):
    n, w = data.n, data.width
    active = np.ones(n, dtype=bool)
    stopped_correctly = np.zeros(n, dtype=bool)
    pos = np.zeros(n, dtype=np.int64)
    steps = np.zeros(n, dtype=np.int16)
    partial = np.zeros(n, dtype=np.int64)
    carry = np.zeros(n, dtype=np.int64)
    greedy = np.ones(n, dtype=bool)
    for _ in range(w + 1):
        moves = action(readout, w - pos, data.codes[pos, data.indices])
        expected = np.where(pos == w, 0, 1 + data.can_pair[pos, data.indices])
        greedy &= ~active | (moves == expected)
        complete = active & (moves == 0) & (pos == w)
        stopped_correctly |= complete & ((partial | (carry << w)) == data.a + data.b)
        legal = ((moves == 1) & (pos < w)) | ((moves == 2) & data.can_pair[pos, data.indices])
        advance = active & legal
        shift = np.where(advance, moves, 0)
        mask = (1 << shift) - 1
        chunk = ((data.a >> pos) & mask) + ((data.b >> pos) & mask) + carry
        partial |= (chunk & mask) << pos
        carry = np.where(advance, chunk >> shift, carry)
        pos += shift
        steps += advance
        active = advance
        if not np.any(active):
            break
    return stopped_correctly, steps, greedy & stopped_correctly


def scores(data, readout):
    correct, steps, exact = rollout(data, readout)
    values, counts = np.unique(steps[correct], return_counts=True)
    return {"episodes": data.n, "legal_correct_stop": int(np.sum(correct)),
            "minimum_rounds": int(np.sum(correct & (steps == data.optimum))),
            "matches_greedy": int(np.sum(exact)), "sum_successful_rounds": int(steps[correct].sum()),
            "round_histogram_successful": {str(int(s)): int(n) for s, n in zip(values, counts)}}


def demo_examples(data):
    obs = []
    for i in range(data.n):
        pos = 0
        while True:
            mv = 0 if pos == data.width else (2 if data.can_pair[pos, i] else 1)
            obs.append((data.width - pos, data.codes[pos, i], mv))
            if mv == 0:
                break
            pos += mv
    return np.asarray(obs, dtype=np.int64).T


def neighbors(readout):
    for s in [-1, 0, 1]:
        if s != readout["s"]:
            yield model(s, readout["k"], readout["table"])
    for k in [1, 2, 3]:
        if k != readout["k"]:
            yield model(readout["s"], k, readout["table"])
    for idx in range(16):
        wires = readout["table"].copy()
        wires[idx] ^= 1
        yield model(readout["s"], readout["k"], wires)


def train(data, supervision, initial=FINE):
    if supervision == "I":
        remaining, tags, target = demo_examples(data)

        def objective(readout):
            return (int(np.sum(action(readout, remaining, tags) == target)),)
    else:
        def objective(readout):
            passed, steps, _ = rollout(data, readout)
            n_pass = int(np.sum(passed))
            return ((n_pass, -int(steps[passed].sum()))
                    if supervision == "EC" else (n_pass,))

    readout = initial
    score = objective(readout)
    history = [{"model": readout, "objective": list(score)}]
    probes = 1
    for _ in range(32):
        best, best_score = readout, score
        for candidate in neighbors(readout):
            value = objective(candidate)
            probes += 1
            if value > best_score:
                best, best_score = candidate, value
        if best_score == score:
            break
        readout, score = best, best_score
        history.append({"model": readout, "objective": list(score)})
    return readout, history, probes


def test_sets():
    pairs = np.arange(65536)
    zero = np.zeros_like(pairs)
    yield "flat_8_operand_exhaustive", Episodes(8, pairs >> 8, pairs & 255, zero, zero)
    for width in [7, 8]:
        base = 1 << width
        ids = np.arange(base ** 2)
        # Operand pairs permuted so layout enumeration does not imply a full Cartesian product.
        a = (ids * 17 + 11) % base
        b = ((ids // base) * 23 + 3) % base
        yield "layouts_exhaustive_" + str(width), Episodes(width, a, b, ids // base, ids % base)
    rng = np.random.default_rng(20263199)
    for width in [1, 5, 9, 12]:
        yield "held_out_" + str(width), Episodes(width, *rng.integers(0, 1 << width, (4, 2048)))


def signature(readout):
    return (readout["s"], readout["k"], *readout["table"])


def spot_trace(readout, a_bank, b_bank):
    w, p = 8, 0
    paper = []
    while p <= w and len(paper) < 10:
        move = action(readout, w - p, encode(a_bank, b_bank, p, w))
        paper.append(move)
        if not move:
            break
        p += move
    return paper


def run():
    records = []
    registry = {}
    arms = {}
    for seed in range(20263101, 20263117):
        data = training(seed)
        models = {"fixed_one": FINE, "fixed_two": ALWAYS_TWO, "oracle": ORACLE}
        history = {}
        for arm in ("E", "EC", "I"):
            models[arm], hist, probes = train(data, arm)
            history[arm] = {"accepted": hist, "objective_evaluations": probes}
        assignment = {}
        for arm, m in models.items():
            s = signature(m)
            if s not in registry:
                registry[s] = len(registry)
            assignment[arm] = registry[s]
        arms[str(seed)] = assignment
        records.append({"seed": seed, "train_a_b_a_bank_b_bank": data.examples(),
                        "models": models, "history": history, "model_ids": assignment,
                        "train_scores": {arm: scores(data, m) for arm, m in models.items()}})
    results = {}
    for name, data in test_sets():
        results[name] = {str(ident): scores(data, model(sig[0], sig[1], sig[2:]))
                         for sig, ident in registry.items()}
    ablate = {str(ident): [spot_trace(model(sig[0], sig[1], sig[2:]), 0, 0),
                           spot_trace(model(sig[0], sig[1], sig[2:]), 2, 0)]
              for sig, ident in registry.items()}
    return {"trials": records, "test_scores_by_model_id": results,
            "spot_moves_flat_and_flip_A_bank_column1": ablate, "cost": {
                 "controller": "16 binary group weights (4-tag decoder) + two discrete scalar cutoffs",
                 "supervision_E_EC": "64 complete width-eight episodes, endpoint or endpoint and total rounds",
                 "supervision_I": "64 greedy demonstration traces, including STOP",
                 "arithmetic": "exact one- or two-column chunk per arithmetic round plus one STOP action",
                 "correct_stop": "timely stop on exactly W bits, all legal moves, correct sum including carry"
            }}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="result.json")
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(run(), indent=2) + "\n", encoding="utf-8")
