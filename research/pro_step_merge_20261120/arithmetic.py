"""Train direct one- and two-bit threshold students; exhaustively score actual rollouts."""

import argparse
import collections
import hashlib
import json
from pathlib import Path

import numpy as np


SEEDS = range(20261120, 20261136)
SIZES = (1, 2, 4, 8, 16, 32, 64)


def role_features(a, b, carry):
    return np.stack([a & 1, (a >> 1) & 1, b & 1, (b >> 1) & 1,
                     carry, np.ones_like(carry)], axis=-1)


def context_id(width, a, b, carry):
    return a | (b << width) | (carry << (2 * width))


def conjunction_fit(width, a, b, carry, targets):
    """One active context feature per example, signed readout delta at rate one."""
    size = 1 << (2 * width + 1)
    weights = np.zeros((size, width + 1), dtype=np.int8)
    changed = 0
    for addr, target in zip(context_id(width, a, b, carry), targets):
        signs = 2 * ((int(target) >> np.arange(width + 1)) & 1) - 1
        delta = signs - weights[addr]
        changed += int(np.any(delta))
        weights[addr] += delta.astype(np.int8)
    return weights.tolist(), changed


def get_fine_skill():
    addr = np.arange(8)
    a, b, c = addr & 1, (addr >> 1) & 1, (addr >> 2) & 1
    return conjunction_fit(1, a, b, c, a + b + c)[0]


def read_conjunction(width, weights, a, b, carry):
    active = weights[context_id(width, a, b, carry)] > 0
    return (active.astype(np.int16) * (1 << np.arange(width + 1))).sum(axis=-1)


def student_step(model, width, a_chunk, b_chunk, carry):
    """Return (predicted output digit, own next carry); no internal fine-step call."""
    a, b, c = np.broadcast_arrays(np.asarray(a_chunk, dtype=np.int16),
                                  np.asarray(b_chunk, dtype=np.int16),
                                  np.asarray(carry, dtype=np.int16))
    if width == 1:
        packed = read_conjunction(1, np.asarray(model["fine"]), a, b, c)
    elif width == 2 and model["hardware"] == "lut":
        packed = read_conjunction(2, np.asarray(model["weights"]), a, b, c)
    elif width == 2 and model["hardware"] == "linear":
        w = np.asarray(model["weights"])
        packed = np.clip(role_features(a, b, c) @ w, 0, 7)
    else:
        raise ValueError("unsupported width or arithmetic model")
    return packed & ((1 << width) - 1), packed >> width


def own_training_records(a, b, fine):
    model = {"fine": fine}
    carry = np.zeros_like(a)
    outputs, inputs = [], []
    for offset in range(0, 8, 2):
        da, db = (a >> offset) & 3, (b >> offset) & 3
        inputs.append(np.stack([da, db, carry], axis=-1))
        lo, internal = student_step(model, 1, da & 1, db & 1, carry)
        hi, carry = student_step(model, 1, da >> 1, db >> 1, internal)
        outputs.append(lo | (hi << 1) | (carry << 2))
    return np.stack(inputs, axis=1), np.stack(outputs, axis=1)


def teacher_training_records(a, b):
    inputs, outputs = [], []
    for offset in (0, 2, 4, 6):
        mask = (1 << offset) - 1
        carry = ((a & mask) + (b & mask)) >> offset
        da, db = (a >> offset) & 3, (b >> offset) & 3
        inputs.append(np.stack([da, db, carry], axis=-1))
        outputs.append(da + db + carry)
    return np.stack(inputs, axis=1), np.stack(outputs, axis=1)


def fit_models(inputs, targets, fine):
    a, b, carry = inputs.reshape(-1, 3).T
    target = targets.reshape(-1)
    features = role_features(a, b, carry).astype(np.int64)
    gram = features.T @ features
    rhs = features.T @ target
    values, vectors = np.linalg.eigh(gram)
    good = values > 1e-10
    basis = vectors[:, good]
    continuous = basis @ ((basis.T @ rhs) / values[good])
    w = np.rint(continuous).astype(np.int64).tolist()
    lut, changed = conjunction_fit(2, a, b, carry, target)
    info = {"contexts_seen_of_32": int(len(np.unique(context_id(2, a, b, carry)))),
            "feature_rank_of_6": int(good.sum()), "local_records": int(target.size),
            "lut_parameter_changing_presentations": changed,
            "integer_gram": gram.tolist(), "integer_rhs": rhs.tolist()}
    return {"lut": {"fine": fine, "hardware": "lut", "weights": lut},
            "linear": {"fine": fine, "hardware": "linear", "weights": w}}, info


def rollout(model, width, a, b):
    carry = np.zeros_like(a)
    answer = np.zeros_like(a)
    valid = np.ones(a.size, dtype=bool)
    updates = 0
    parts = []
    stop_count = 0
    positions = []
    pos = 0
    while pos < 8:
        before = pos
        mask = (1 << width) - 1
        digit, carry = student_step(model, width, (a >> pos) & mask, (b >> pos) & mask, carry)
        answer = answer | (digit << pos)
        pos += width
        legal_mask = (1 << pos) - 1
        expected = (a & legal_mask) + (b & legal_mask)
        valid &= (carry == (expected >> pos)) & (answer == (expected & legal_mask))
        stop = pos == 8
        stop_count += int(stop)
        assert pos - before == width
        parts.append(digit | (carry << width))
        positions.append(pos)
        updates += 1
    valid_stop = pos == 8 and stop_count == 1 and positions[:-1].count(8) == 0
    complete = answer | (carry << pos)
    return {"trace": valid & valid_stop, "endpoint": complete == (a + b),
            "stop": bool(valid_stop), "cycles": updates, "positions": positions,
            "outputs": np.stack(parts, axis=1)}


class ExhaustiveScorer:
    def __init__(self):
        ids = np.arange(65536, dtype=np.int32)
        self.a, self.b = ids >> 8, ids & 255
        self.cache = {}

    def score(self, model, width, ids):
        key = (width, model.get("hardware"), json.dumps(model.get("weights")))
        if key not in self.cache:
            trial = rollout(model, width, self.a, self.b)
            domain = np.arange(1 << (2 * width + 1))
            mask = (1 << width) - 1
            da, db, c = domain & mask, (domain >> width) & mask, domain >> (2 * width)
            d, co = student_step(model, width, da, db, c)
            truth = da + db + c
            correct = (d | (co << width)) == truth
            self.cache[key] = (np.packbits(trial["trace"], bitorder="little"),
                               np.packbits(trial["endpoint"], bitorder="little"),
                               dict(trace_exact=int(trial["trace"].sum()),
                                    endpoint_exact=int(trial["endpoint"].sum()),
                                    stop_exact=65536 * int(trial["stop"]),
                                    local_truth_exact=int(correct.sum()),
                                    cycles=trial["cycles"], cursor=trial["positions"]))
        packed_trace, packed_endpoint, score = self.cache[key]
        select = lambda bits: int(((bits[ids >> 3] >> (ids & 7)) & 1).sum())
        train_trace, train_end = select(packed_trace), select(packed_endpoint)
        return {**score, "training_trace_exact": train_trace, "training_endpoint_exact": train_end,
                "unseen_n": 65536 - len(ids),
                "unseen_trace_exact": score["trace_exact"] - train_trace,
                "unseen_endpoint_exact": score["endpoint_exact"] - train_end}


def experiment(out, raw):
    fine = get_fine_skill()
    scorer = ExhaustiveScorer()
    baseline = scorer.score({"fine": fine}, 1, np.arange(0, dtype=np.int32))
    assert baseline["trace_exact"] == baseline["endpoint_exact"] == baseline["stop_exact"] == 65536
    trials = []
    agg = {}
    for seed in SEEDS:
        ids = np.random.default_rng(seed).choice(65536, 64, replace=False)
        a, b = ids >> 8, ids & 255
        own = own_training_records(a, b, fine)
        teacher = teacher_training_records(a, b)
        assert np.array_equal(own[0], teacher[0]) and np.array_equal(own[1], teacher[1])
        checkpoints = {}
        for n in SIZES:
            cp = {}
            for name, (x, y) in (("self", own), ("teacher", teacher)):
                cells, info = fit_models(x[:n], y[:n], fine)
                cp[name + "_training"] = info
                for hw, model in cells.items():
                    score = scorer.score(model, 2, ids[:n])
                    cp[name + "_" + hw] = {**model, "score": score}
                    agg.setdefault((n, name + "_" + hw), []).append(score)
            for hw in ("lut", "linear"):
                assert cp["teacher_" + hw] == cp["self_" + hw]
            checkpoints[str(n)] = cp
        scrambled, _ = fit_models(own[0], np.roll(own[1], 1, axis=1), fine)
        scramble = scrambled["linear"]
        scratch_score = scorer.score(scramble, 2, ids)
        agg.setdefault((64, "scrambled_linear"), []).append(scratch_score)
        trials.append({"seed": seed, "training_ids": ids.tolist(), "checkpoints": checkpoints,
                       "target_records_identical_all_64x4": True,
                       "scrambled_linear": {**scramble, "score": scratch_score}})
    selected = trials[0]["checkpoints"]["64"]["self_linear"]
    raw_result = rollout(selected, 2, scorer.a, scorer.b)["outputs"]
    np.column_stack([scorer.a, scorer.b, raw_result]).astype(np.uint8).tofile(raw)
    summary = {}
    for (n, k), entries in agg.items():
        grades = [s["trace_exact"] for s in entries]
        summary.setdefault(str(n), {})[k] = {
            "perfect_all_rows": sum(x == 65536 for x in grades),
            "at_least_95pct": sum(x * 100 >= 65536 * 95 for x in grades),
            "trace_range": [min(grades), max(grades)],
            "median_trace": float(np.median(grades)),
            "perfect_endpoint": sum(s["endpoint_exact"] == 65536 for s in entries),
        }
    files = [Path(__file__), Path(__file__).with_name("ARITHMETIC_PROTOCOL.md")]
    document = {
        "software": {"numpy": np.__version__, "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}},
        "fine_baseline": baseline, "fine_weights": fine,
        "setup": {"seeds": list(SEEDS), "example_counts": list(SIZES), "ordered_id": "256*A+B",
                  "fine_teaching": "one signed delta presentation of each 1-bit local context",
                  "fine_weights": 16, "coarse_lut_weights": 96, "coarse_linear_weights": 6,
                  "fine_detector_bank": "8 equality features for 3 bits",
                  "coarse_lut_detector_bank": "32 equality features for 5 bits",
                  "coarse_linear_encoder": "clip affine scalar to [0,7], fixed binary encoder",
                  "recurrent_carry_bits": 1, "coarse_operand_input_bits_per_tick": 4,
                  "fine_operand_input_bits_per_tick": 2, "shared_additional_controller_cost_counted": False,
                  "raw_schema": "A,B,four bytes(digit+4*carry), uint8, A/B lexicographic, first seed at 64 examples, self_linear"},
        "sha256_raw": hashlib.sha256(raw.read_bytes()).hexdigest(), "summary": summary, "trials": trials,
    }
    out.write_text(json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("arithmetic_results.json"))
    parser.add_argument("--raw", type=Path, default=Path("arithmetic_raw.bin"))
    args = parser.parse_args()
    experiment(args.out, args.raw)
