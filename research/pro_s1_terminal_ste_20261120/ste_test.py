"""Endpoint-only straight-through test on an actual S1 adder with one private threshold cell."""
import argparse
import ast
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

PAIR_COUNT = 65536
SEEDS = tuple(range(20261120, 20261136))
MODELS = ("hard_zero", "straight", "clipped", "straight_detached")
SOURCE_DIGEST = "6d5523276727d265211b1c35a950006053220b97c4489578a10540217e4e0d8d"
TRIPLES = np.array(list(itertools.product(range(2), repeat=3)))
LOC = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshots(path):
    raw = path.read_bytes()
    assert sha(raw) == SOURCE_DIGEST
    core_names = {"Net", "full_add_bit", "build_S1", "board_of", "val"}
    body = [node for node in ast.parse(raw).body if getattr(node, "name", None) in core_names
            or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "M" for t in node.targets))]
    namespace = {"np": np}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), namespace)
    model, encode, decode = namespace["build_S1"]()
    wi, bi, wo = (v.astype(np.int32) for v in model.mats())
    assert wi.shape == (19, 18)
    ids = np.arange(PAIR_COUNT, dtype=np.int32)
    a, b = ids // 256, ids % 256
    board = encode(a, b).astype(np.int32)
    av, bv, prefix_borrow = [], [], []
    for k in range(8):
        ai = board[:, model.c("A")]
        bj = board[:, model.c("B")]
        assert np.array_equal(ai, (a >> k) & 1)
        assert np.array_equal(bj, (b >> k) & 1)
        av.append(ai.astype(np.uint8))
        bv.append(bj.astype(np.uint8))
        mask = (2 << k) - 1
        prefix_borrow.append((a & mask) < (b & mask))
        hidden = (board @ wi.T + bi >= 0).astype(np.int32)
        out = hidden @ wo.T
        assert ((out == 0) | (out == 1)).all() and (out[:, -1] == int(k == 7)).all()
        board = out[:, :-1]
    assert np.array_equal(decode(board), a + b)
    return np.array(av), np.array(bv), np.array(prefix_borrow), {
        "units": 19, "board_bits": 18, "sum_all_nine_bits_correct": PAIR_COUNT,
        "stop_schedule_all_eight_correct": PAIR_COUNT, "sha256": SOURCE_DIGEST,
        "matrices_sha256_int32_le": sha(b"".join(w.astype("<i4").tobytes() for w in (wi, bi, wo)))}


def local_bits(w):
    a, b, prev = TRIPLES.T
    return (w[0] * a + w[1] * b + w[2] * prev + w[3] >= 0).astype(np.uint8)


def signature(w):
    return sum(int(x) << i for i, x in enumerate(local_bits(w)))


def pool(radius):
    values = itertools.product(range(-radius, radius + 1), repeat=4)
    return sorted(values, key=lambda w: (np.count_nonzero(w), w))


def traces(sig, a, b):
    table = ((sig >> np.arange(8)) & 1).astype(np.uint8)
    q = np.zeros(a.shape[1:], dtype=np.uint8)
    result = []
    for ai, bj in zip(a, b):
        q = table[(ai << 2) + (bj << 1) + q]
        result.append(q)
    return np.array(result)


def derivatives(z, kind):
    if kind == "hard_zero":
        return np.zeros_like(z)
    if kind == "clipped":
        return (np.abs(z) <= 1).astype(np.float64)
    return np.ones_like(z)


def gradient(w, a, b, y, kind, check=False):
    # Parallel seeds share the code; each has its own weights, paired data and targets.
    q = np.zeros_like(y, dtype=np.float64)
    tape = []
    sensitivities = np.zeros((*q.shape, 4)) if check else None
    for av, bv in zip(a, b):
        pre = w[:, 0, None] * av + w[:, 1, None] * bv + w[:, 2, None] * q + w[:, 3, None]
        factor = derivatives(pre, kind)
        x = np.stack([av, bv, q, np.ones_like(q)], axis=2)
        tape.append((x, factor))
        q = (pre >= 0).astype(np.float64)
        if check:
            past = 0 if kind == "straight_detached" else w[:, None, 2, None] * sensitivities
            sensitivities = factor[:, :, None] * (x + past)
    error = q-y
    grad = np.zeros_like(w)
    for x, factor in reversed(tape):
        delta = error * factor
        grad += (delta[:, :, None] * x).mean(axis=1)
        if kind == "straight_detached":
            break
        error = delta * w[:, 2, None]
    if check:
        forward_grad = ((q-y)[:, :, None] * sensitivities).mean(axis=1)
        np.testing.assert_allclose(grad, forward_grad, atol=1e-12, rtol=1e-12)
    return grad, q


def learned(a, b, y, kind):
    w = np.zeros((len(SEEDS), 4), dtype=np.float64)
    updates = np.zeros(len(SEEDS), dtype=int)
    for n in range(256):
        grad, _ = gradient(w, a, b, y, kind, check=n in {0, 1, 11, 255})
        wnew = w - 0.25 * grad
        assert np.isfinite(wnew).all()
        updates += (wnew != w).any(axis=1)
        w = wnew
    return w, updates


def scores(trace, truth):
    end = trace[-1].astype(bool)
    label = truth[-1]
    return {"endpoint_correct": int((end == label).sum()),
            "sequence_correct": int((truth == trace).all(axis=0).sum()),
            "true_positive": int((label & end).sum()), "positive_total": int(label.sum()),
            "true_negative": int((~label & ~end).sum()), "negative_total": int((~label).sum())}


def summarize(results):
    summary = {}
    for method, rows in results.items():
        summary[method] = {}
        for precision in ("float", "rounded", "truth_equivalent_integer"):
            subset = [k[precision] for k in rows if k[precision] is not None]
            stats = {"available": len(subset)}
            for metric in ("endpoint_correct", "sequence_correct"):
                vals = np.array([r[metric] for r in subset], dtype=np.int64)
                if len(vals):
                    stats[metric] = {
                        "at_least_95": int((100 * vals >= 95 * PAIR_COUNT).sum()),
                        "perfect": int((vals == PAIR_COUNT).sum()), "min": int(vals.min()),
                        "median": float(np.median(vals)), "max": int(vals.max())}
            summary[method][precision] = stats
    return summary


def run(path):
    a, b, truth, old = snapshots(path)
    ids = np.stack([np.random.default_rng(s).choice(PAIR_COUNT, 64, replace=False) for s in SEEDS])
    train_a, train_b, train_y = a[:, ids], b[:, ids], truth[-1][ids].astype(np.float64)
    candidates = pool(1)
    candidate_end = np.array([traces(signature(v), train_a, train_b)[-1] for v in candidates])
    errors = (candidate_end != train_y).sum(axis=-1)
    best_idx = errors.argmin(axis=0)
    fit_count = (errors == errors.min(axis=0)).sum(axis=0)
    exact_map = {}
    for v in pool(2):
        exact_map.setdefault(signature(v), v)
    cached = {}
    def evaluate(w, train_ids):
        sig = signature(w)
        if sig not in cached:
            bits = traces(sig, a, b)
            cached[sig] = (bits[-1].astype(bool), scores(bits, truth))
        end, counts = cached[sig]
        return {"weights": w.tolist(), "truth_table_code": sig, **counts,
                "train_endpoint_correct_of_64": int((end[train_ids] == truth[-1, train_ids]).sum())}
    result = {}
    for kind in (*MODELS, "integer_search"):
        if kind == "integer_search":
            weights = np.array([candidates[i] for i in best_idx])
            updates = [None]*len(SEEDS)
        else:
            weights, updates = learned(train_a, train_b, train_y, kind)
        trials = []
        for i, (seed, w) in enumerate(zip(SEEDS, weights)):
            integer = exact_map.get(signature(w))
            trials.append({
                "seed": seed, "changed_updates": None if updates[i] is None else int(updates[i]),
                "gradient_steps": 0 if kind == "integer_search" else 256,
                "search_min_error_hypotheses": int(fit_count[i]) if kind == "integer_search" else None,
                "float": evaluate(w, ids[i]), "rounded": evaluate(np.rint(w).astype(np.int64), ids[i]),
                "truth_equivalent_integer": evaluate(np.array(integer), ids[i]) if integer is not None else None})
        result[kind] = trials
    records = np.array([np.arange(PAIR_COUNT)//256, np.arange(PAIR_COUNT)%256,
                        np.packbits(truth.T, axis=1, bitorder="little")[:, 0]], dtype=np.uint8).T
    return {"source": old, "numpy": np.__version__, "seeds": list(SEEDS), "ids_by_seed": ids.tolist(),
            "training_targets": "only final A<B; q0=0; no intermediate teacher forcing",
            "comparison": "65536 pairs incl 64 training exposures; own output feedback; 8 bit scan",
            "new_cell": {"trainable_parameters": 4, "extra_units": 1, "extra_register_bits": 1,
                         "new_MACs_per_sequence_dense_forward": 24, "bias_additions_per_sequence": 8,
                         "definition": "3 input weights per round, one fixed output wire; excludes old network and backward pass"},
            "oracle_raw_records": {"fields": ["a_uint8", "b_uint8", "borrow_trace_packed_little_bit"],
                         "sha256": sha(records.tobytes()), "size_bytes": records.nbytes},
            "preregistered": sha((LOC/"prereg.md").read_bytes()), "script_sha": sha(Path(__file__).read_bytes()),
            "summary": summarize(result), "trials": result}, records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=LOC/"results.json")
    parser.add_argument("--raw", type=Path, default=LOC/"raw_internal.bin")
    args = parser.parse_args()
    result, records = run(args.source)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    args.raw.write_bytes(records.tobytes())
    for method, modes in result["summary"].items():
        print(method, {mode:(v["endpoint_correct"],v["sequence_correct"]) for mode,v in modes.items()})
