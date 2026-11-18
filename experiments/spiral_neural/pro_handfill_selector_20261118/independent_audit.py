"""Independent preparation audit; only 32 training rows/source are inferred.

Reads experiment implementation to compare analytic gradients, but independently
parses frames, computes source outputs, derives labels, and checks the copy net.
No optimizer step or held-out source inference is performed here.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import time
import numpy as np

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent / "feature_transfer_20261118"
SEEDS = (101, 202, 303)
WEIGHTS = np.array([64, 32, 16, 8, 4, 2, 1])
ORDER = [14, 15, 4, 5, 6, 7, 8, 16, 17, 9, 10, 11, 12, 13]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_frame(bits):
    assert len(bits) == 34 and set(bits) <= {"0", "1"}
    assert bits[:13] == "1111011111110"
    assert bits[17] == bits[25] == bits[33] == "0"
    operation = (12, 9, 7, 8).index(int(bits[13:17], 2))
    return operation, int(bits[18:25], 2), int(bits[26:33], 2)


def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def independently_decode(parameters, x):
    hidden = np.tanh(x @ parameters["W1"] + parameters["b1"])
    logits = hidden @ parameters["W2"] + parameters["b2"]
    words = (logits[:, ORDER] >= 0).astype(np.uint8)
    return hidden, logits, words


def independent_loss(parameters, words, target):
    logits = words @ parameters["w"] + parameters["b"][0]
    return float(np.mean(np.logaddexp(0., logits) - target * logits))


def run():
    import hybrid_model as implementation
    started = time.perf_counter()
    receipt_path = ROOT / "receipts/preparation_audit.json"
    if receipt_path.exists():
        raise FileExistsError(receipt_path)
    assert not (ROOT / "results").exists(), "Preparation audit must precede formal run"
    lock = read(ROOT / "source_lock.json")
    hashes = lock.get("source_sha256", lock.get("sha256"))
    assert isinstance(hashes, dict)
    for relative, digest in hashes.items():
        assert sha(ROOT / relative) == digest, relative
    data = read(ROOT / "data.json")
    previous = read(PREVIOUS / "data.json")
    panels = data["panels"]
    assert {k: len(v) for k, v in panels.items()} == {
        "train": 8240, "val": 2096, "test": 3120, "challenge": 936}
    examined_rows = 0
    grouping = {}
    for panel, rows in panels.items():
        observed = {}
        identifiers = set()
        for row in rows:
            op, a, b = parse_frame(row["frame_bits"])
            assert (op, a, b) == (row["op"], row["a"], row["b"])
            assert a + b < 128
            assert row["target_bits"] == format(max(a, b), "07b")
            assert row["max_answer"] == max(a, b)
            assert row["case_id"] == f"n7_o{op}_a{a:03d}_b{b:03d}"
            assert row["case_id"] not in identifiers
            identifiers.add(row["case_id"])
            pair = tuple(sorted((a, b)))
            observed.setdefault(pair, set()).add((op, a, b))
            examined_rows += 1
        for (lo, hi), variants in observed.items():
            orders = {(lo, hi), (hi, lo)}
            assert variants == {(op, a, b) for a, b in orders for op in range(4)}
        grouping[panel] = set(observed)
    for index, left in enumerate(grouping):
        for right in list(grouping)[index + 1:]:
            assert not grouping[left] & grouping[right], (left, right)
    for panel in ("train", "val", "test"):
        assert len(panels[panel]) == len(previous["panels"][panel])
        for now, before in zip(panels[panel], previous["panels"][panel]):
            assert all(now[k] == value for k, value in before.items())
        assert grouping[panel] == set(map(tuple, previous["group_splits"][panel]))
    assert grouping["challenge"] == set(map(tuple, previous["group_splits"]["unused"]))
    assert len(grouping["challenge"]) == 117

    old = read(PREVIOUS / "sources/pr130_data.json")
    exposed = set()
    for collection in ("old_pair_splits", "new_pair_splits"):
        for panel in ("train", "val", "test"):
            exposed.update(tuple(sorted(p)) for p in old[collection][panel])
    ancestor = read(PREVIOUS / "sources/pr129_data.json")
    for panel in ("train", "val", "test"):
        exposed.update(tuple(sorted(p)) for p in ancestor["pair_splits"][panel])
    assert not set.union(*grouping.values()) & exposed
    source_unused = set(map(tuple, old["new_pair_splits"]["unused"]))
    for pair in set.union(*grouping.values()):
        assert pair in source_unused and pair[::-1] in source_unused

    numerical_error = 0.
    source_error = 0.
    finite_difference_coordinates = 0
    training_source_rows = 0
    subset = panels["train"][:32]
    raw = np.array([[int(c) for c in row["frame_bits"]] for row in subset], dtype=float)
    target = np.array([int(row["a"] >= row["b"]) for row in subset], dtype=float)
    source_hashes = {}
    batch_hashes = {}
    for seed in SEEDS:
        source = ROOT / f"sources/receiver_seed{seed}.npz"
        prior_source = PREVIOUS / f"sources/receiver_seed{seed}.npz"
        assert source.read_bytes() == prior_source.read_bytes()
        source_hashes[str(seed)] = sha(source)
        z = arrays(source)
        p = {k: z["param_" + k] for k in ("W1", "b1", "W2", "b2")}
        assert sum(v.size for v in p.values()) == 1290
        expected_h, expected_z, words = independently_decode(p, raw)
        actual = implementation.decode(implementation.load_source(seed), raw)
        for key, expected in (("hidden", expected_h), ("logits", expected_z),
                              ("operand_logits", expected_z[:, ORDER])):
            error = float(np.max(np.abs(actual[key] - expected)))
            source_error = max(source_error, error)
            assert error < 1e-12
        assert np.array_equal(actual["words"], words)
        assert np.array_equal(actual["pred_op"], expected_z[:, :4].argmax(1))
        assert np.array_equal(actual["pred_a"], words[:, :7] @ WEIGHTS)
        assert np.array_equal(actual["pred_b"], words[:, 7:] @ WEIGHTS)
        training_source_rows += len(raw)
        head = implementation.init_comparator("random_train", seed)
        assert head["w"].shape == (14,) and head["b"].shape == (1,)
        expected_rng = np.random.default_rng(2100000 + seed)
        assert np.array_equal(head["w"], expected_rng.normal(0, np.sqrt(2 / 15), 14))
        assert np.array_equal(head["b"], np.zeros(1))
        value, gradients = implementation.loss_grads(head, words, target)
        assert abs(value - independent_loss(head, words, target)) < 1e-12
        epsilon = 1e-6
        for key in ("w", "b"):
            for index in range(head[key].size):
                plus, minus = ({k: v.copy() for k, v in head.items()} for _ in range(2))
                plus[key][index] += epsilon
                minus[key][index] -= epsilon
                numeric = (independent_loss(plus, words, target) - independent_loss(minus, words, target)) / (2 * epsilon)
                numerical_error = max(numerical_error, abs(numeric - gradients[key][index]))
                finite_difference_coordinates += 1
        batch = ROOT / f"batches/seed{seed}.npz"
        assert batch.read_bytes() == (PREVIOUS / f"batches/seed{seed}.npz").read_bytes()
        batch_hashes[str(seed)] = sha(batch)
        indices = arrays(batch)["indices"]
        expected_indices = np.random.default_rng(2000000 + seed).integers(0, 8240, size=(4096, 128))
        assert np.array_equal(indices, expected_indices)
    assert numerical_error < 1e-8

    exact = implementation.exact_comparator()
    assert np.array_equal(exact["w"], np.r_[WEIGHTS, -WEIGHTS])
    assert np.array_equal(exact["b"], [.5])
    for seed in SEEDS:
        for arm in ("handfilled_frozen", "handfilled_train"):
            state = implementation.init_comparator(arm, seed)
            assert all(np.array_equal(state[k], exact[k]) for k in ("w", "b"))
    mux = implementation.load_mux()
    expected_indices = np.array([[j, 14] for j in range(7)] + [[7 + j, 14] for j in range(7)])
    # Allow a semantically identical ordering only if separately documented.
    assert np.array_equal(mux["layer1_indices"], expected_indices)
    assert np.array_equal(mux["layer1_weights"], np.array([[1., 1.]] * 7 + [[1., -1.]] * 7))
    assert np.array_equal(mux["layer1_bias"], np.r_[np.full(7, -1.5), np.full(7, -.5)])
    assert np.array_equal(mux["layer2_indices"], np.array([[j, j + 7] for j in range(7)]))
    assert np.array_equal(mux["layer2_weights"], np.ones((7, 2)))
    assert np.array_equal(mux["layer2_bias"], np.full(7, -.5))
    mux_values = sum(mux[k].size for k in ("layer1_weights", "layer1_bias", "layer2_weights", "layer2_bias"))
    mux_indices = mux["layer1_indices"].size + mux["layer2_indices"].size
    assert mux_values == 63 and mux_indices == 42
    # All eight Boolean triples at every bit position; no source-model call.
    truth = np.array([(a, b, s) for a in (0, 1) for b in (0, 1) for s in (0, 1)], dtype=np.uint8)
    synthetic_words = np.c_[np.repeat(truth[:, :1], 7, axis=1), np.repeat(truth[:, 1:2], 7, axis=1)]
    observed = implementation.mux_forward(mux, synthetic_words, truth[:, 2])["output_bits"]
    selected = truth[:, 0] * truth[:, 2] + truth[:, 1] * (1 - truth[:, 2])
    assert np.array_equal(observed, np.repeat(selected[:, None], 7, axis=1))

    for relative, digest in hashes.items():
        assert sha(ROOT / relative) == digest, relative
    code_files = ("prepare_study.py", "hybrid_model.py", "run_train.py", "preflight.py")
    receipt = {
        "status": "PASS_complete_independent_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.perf_counter() - started,
        "audit_scope": "Independent raw parsing, data/exclusion/reuse audit, actual source arithmetic on32train rows/source, selector finite differences and full per-bit copy truth table; no heldout source inference or training",
        "dataset_rows_checked": examined_rows,
        "group_counts": {k: len(v) for k, v in grouping.items()},
        "source_training_rows": training_source_rows,
        "source_training_rows_per_seed": 32,
        "source_forward_row_executions": 2 * training_source_rows,
        "source_forward_dense_mac": 2 * training_source_rows * 1248,
        "source_max_absolute_error": source_error,
        "finite_difference_coordinates": finite_difference_coordinates,
        "finite_difference_epsilon": 1e-6,
        "finite_difference_max_absolute_error": numerical_error,
        "mux_boolean_triples_per_bit": 8,
        "mux_numeric_values": mux_values,
        "mux_connectivity_indices": mux_indices,
        "comparator_values": 15,
        "total_added_numeric_values": 78,
        "source_parameters": 1290,
        "full_retained_model_numeric_values": 1368,
        "executed_sparse_weight_products_per_row": 56,
        "source_dense_mac_per_row": 1248,
        "complete_forward_dense_plus_sparse_mac_per_row": 1304,
        "decoder_reorder_indices": 14,
        "source_hashes": source_hashes,
        "batch_hashes": batch_hashes,
        "locked_file_count": len(hashes),
        "final_reviewed_code_sha256": {name: sha(ROOT / name) for name in code_files},
        "actual_gradient_updates": 0,
        "heldout_model_forward_rows": 0,
        "limitations": [
            "PR132 test is reused and already inspected; only117challenge groups are newly unqueried within this continuation.",
            "Selector supervision and manual wiring/numeric place-value priors differ from PR132seven-bit supervision.",
            "Frozen source isolates reuse; no freely adapting-parent recovery or autonomous-growth claim.",
            "Full handfilled comparator capacity is not learned rule discovery."
        ]
    }
    receipt_path.parent.mkdir(exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
