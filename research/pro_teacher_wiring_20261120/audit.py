"""Read-only post-training audit of S1 edge-hint checkpoints. Run with Python and NumPy."""

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
ROLES = [f"A{i}" for i in range(8)] + [f"B{i}" for i in range(9)] + ["C", "borrow", "bias"]
TEACHER = ["A0", "B0", "borrow"]
KEEP = [ROLES.index(name) for name in TEACHER + ["bias"]]
ARMS = ["A", "B", "S", "C", "F"]
PAIR_COUNT = 256 * 256
SEEDS = list(range(20261120, 20261136))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def read(path):
    return json.loads(path.read_text())


def checkpoint_table(results, old):
    """Use each physical-label layout to place checkpoint weights, then align for batched evaluation."""
    assert results["semantic_roles"] == ROLES
    assert results["seeds"] == old["seeds"] == SEEDS
    assert results["unsigned_packet"] == TEACHER
    assert results["signed_packet"] == [dict(role=r, sign=s) for r, s in zip(TEACHER, [-1, 1, 1])]
    weights = []
    metadata = []
    physical_indices = []
    for i, seed in enumerate(SEEDS):
        pair = results["pair_metadata"][i]
        assert pair["seed"] == seed
        order = np.random.default_rng(np.random.SeedSequence([seed, 901])).permutation(19)
        layout = [ROLES[j] for j in order] + ["bias"]
        assert layout[:-1] == pair["permuted_physical_roles"]
        assert sorted(layout) == sorted(ROLES)
        train = np.random.default_rng(seed).choice(PAIR_COUNT, 64, replace=False)
        assert train.tolist() == pair["training_ids"] == old["ids_by_seed"][i]
        blind_rng = np.random.default_rng(np.random.SeedSequence([seed, 902]))
        blind = [f"A{blind_rng.integers(8)}", f"B{blind_rng.integers(8)}", "borrow"]
        assert blind == pair["blind_roles"]
        for arm in ARMS:
            record = results["trials"][arm][i]
            assert record["seed"] == seed
            cp = record["checkpoints"]
            assert cp["0"]["weights_canonical"] == [0.] * 20
            canonical = np.asarray(cp["256"]["weights_canonical"], dtype=float)
            at64 = np.asarray(cp["64"]["weights_canonical"], dtype=float)
            assert canonical.shape == at64.shape == (20,) and np.isfinite(canonical).all()
            permitted = set(ROLES if arm == "A" else (blind if arm == "C" else TEACHER) + ["bias"])
            outside = [j for j, role in enumerate(ROLES) if role not in permitted]
            assert np.all(at64[outside] == 0)
            if arm == "F":
                assert np.all(canonical[outside] == 0)
            if arm == "S":
                assert np.all(at64[KEEP[:3]] * [-1, 1, 1] >= 0)
            physical = np.array([canonical[ROLES.index(role)] for role in layout])
            physical_indices.append([layout.index(role) for role in ROLES])
            weights.append(physical)
            item = {"seed": seed, "arm": arm, "allowed_at_update_64": sorted(permitted),
                    "nonzero_after_release_outside_early_mask": int(np.count_nonzero(canonical[outside])),
                    "nonzero_final_outside_teacher_mask": int(np.count_nonzero(np.delete(canonical, KEEP)))}
            if arm == "F":
                baseline = old["trials"]["straight"][i]
                assert baseline["seed"] == seed
                item["pr137_four_weights_exact"] = canonical[KEEP].tolist() == baseline["float"]["weights"]
                item["pr137_changed_updates_exact"] = cp["256"]["actual_updates"] == baseline["changed_updates"]
            metadata.append(item)
    # Columns refer to independent models. Fetch weights from their permuted physical sockets
    # in the declared semantic reduction order; changing float64 order can change exact-zero ties.
    aligned = np.take_along_axis(np.stack(weights), np.stack(physical_indices), axis=1)
    return metadata, aligned, np.argsort(np.stack(physical_indices), axis=1)


def physical_s1_boards(ordered_ids):
    """Plain integer serial-adder state, zero borrow at entry. No neural matrix or training code."""
    a = np.right_shift(ordered_ids, 8)
    b = ordered_ids & 255
    left = a.copy()
    right = b | 256
    carry = np.zeros_like(a)
    borrow = np.zeros_like(a)
    oracle = np.zeros((len(a), 8), dtype=bool)
    rounds = []
    for r in range(8):
        boards = ((left[:, None] >> np.arange(8)) & 1, (right[:, None] >> np.arange(9)) & 1, carry[:, None])
        rounds.append(np.column_stack(boards).astype(bool))
        stop = (right >> 1) == 1
        assert np.all(stop == (r == 7))
        bit_a, bit_b = left & 1, right & 1
        borrow = (bit_a < bit_b + borrow)
        oracle[:, r] = borrow
        assert np.array_equal(borrow, (a % (2 << r)) < (b % (2 << r)))
        total = bit_a + bit_b + carry
        left = (left >> 1) | ((total & 1) << 7)
        right >>= 1
        carry = total >> 1
    assert np.array_equal(left + (carry << 8), a + b)
    assert np.array_equal(oracle[:, -1], a < b)
    return rounds, np.packbits(oracle, axis=1, bitorder="little")[:, 0]


def predict(rounds, weights):
    size, width = rounds[0].shape
    count = len(weights)
    borrow = np.zeros((size, count), dtype=bool)
    traces = np.zeros((size, count), dtype=np.uint8)
    for r, bits in enumerate(rounds):
        total = np.zeros((size, count), dtype=np.float64)
        for j in range(width):
            # Same reduction order as the specification, independent of BLAS implementation.
            total += bits[:, j, None] * weights[None, :, j]
        total += borrow * weights[None, :, 18]
        total += weights[None, :, 19]
        borrow = total >= 0
        traces |= borrow.astype(np.uint8) << r
    return traces


def predict_in_socket_order(rounds, weights, sockets):
    """Diagnostic only. Float64 addition follows physical input sockets; bias is still last."""
    n = len(rounds[0])
    all_traces = np.zeros((n, len(weights)), dtype=np.uint8)
    for i in range(0, len(weights), len(ARMS)):
        group = slice(i, i + len(ARMS))
        q = np.zeros((n, len(ARMS)), dtype=bool)
        for r, board in enumerate(rounds):
            total = np.zeros((n, len(ARMS)), dtype=float)
            for j in sockets[i, :-1]:
                bit = q if j == 18 else board[:, j, None]
                total += bit * weights[group, j]
            q = total + weights[group, 19] >= 0
            all_traces[:, group] |= q.astype(np.uint8) << r
    return all_traces


def pruned_tables(weights):
    """Compute the eight independent truth rows of the pruned physical unit."""
    rows = np.arange(8)
    a, b, q = rows >> 2, (rows >> 1) & 1, rows & 1
    w = weights[:, KEEP]
    hi = (a[:, None] * w[:, 0] + b[:, None] * w[:, 1] + q[:, None] * w[:, 2] + w[:, 3]) >= 0
    return (hi * (1 << rows[:, None])).sum(axis=0).astype(np.int64)


def score_pruned(all_ids, truth, codes):
    """Compute autonomous scores for each observed local function once, with free-running q."""
    scores = {}
    a, b = all_ids >> 8, all_ids & 255
    for code in np.unique(codes):
        q = np.zeros(len(a), dtype=np.uint8)
        trace = np.zeros_like(q)
        for r in range(8):
            row = (((a >> r) & 1) << 2) | (((b >> r) & 1) << 1) | q
            q = ((int(code) >> row) & 1).astype(np.uint8)
            trace |= q << r
        scores[int(code)] = (int(np.count_nonzero(trace == truth)),
                             int(np.count_nonzero((trace >> 7) == (truth >> 7))))
    return scores


def main():
    results_path = ROOT / "results.json"
    old_path = ROOT / "upstream" / "pr137_results.json"
    results, old = read(results_path), read(old_path)
    meta, weights, sockets = checkpoint_table(results, old)
    all_ids = np.arange(PAIR_COUNT)
    predictions = np.zeros((PAIR_COUNT, len(meta)), dtype=np.uint8)
    physical_order_changes = np.zeros(len(meta), dtype=np.int64)
    physical_order_endpoint_changes = np.zeros(len(meta), dtype=np.int64)
    truth = np.empty(PAIR_COUNT, dtype=np.uint8)
    for start in range(0, PAIR_COUNT, 1024):
        end = start + 1024
        rounds, truth[start:end] = physical_s1_boards(all_ids[start:end])
        predictions[start:end] = predict(rounds, weights)
        alt = predict_in_socket_order(rounds, weights, sockets)
        xor = alt ^ predictions[start:end]
        physical_order_changes += (xor != 0).sum(axis=0)
        physical_order_endpoint_changes += ((xor >> 7) != 0).sum(axis=0)
    raw = np.column_stack((all_ids >> 8, all_ids & 255, truth)).astype(np.uint8).tobytes()
    assert raw == (ROOT / "raw_internal.bin").read_bytes()
    spot = np.unique(np.r_[np.random.default_rng(20261198).choice(PAIR_COUNT, 1024, replace=False),
                            [0, 1, 255, 256, 257, 255 * 256, 255 * 256 + 254, PAIR_COUNT - 1]])
    agree = predictions == truth[:, None]
    endpoint = (predictions >> 7) == (truth[:, None] >> 7)
    codes = pruned_tables(weights)
    trimmed = score_pruned(all_ids, truth, codes)
    for j, item in enumerate(meta):
        arm, seed = item["arm"], item["seed"]
        i = SEEDS.index(seed)
        ckp = results["trials"][arm][i]["checkpoints"]["256"]
        train = results["pair_metadata"][i]["training_ids"]
        full = int(agree[:, j].sum())
        end = int(endpoint[:, j].sum())
        train_end = int(endpoint[train, j].sum())
        item.update(full_trace=full, full_endpoint=end, train_endpoint=train_end,
                    holdout_trace=full - int(agree[train, j].sum()), holdout_endpoint=end-train_end,
                    spot_trace=int(agree[spot, j].sum()), spot_endpoint=int(endpoint[spot, j].sum()),
                    full_round_correct=np.count_nonzero(((predictions[:, j] ^ truth)[:, None] >> np.arange(8)) % 2 == 0, axis=0).tolist(),
                    independent_counts_match=(full, end, train_end) == (ckp["full_trace"], ckp["full_endpoint"], ckp["train_endpoint"]),
                    physical_order_changed_trace_count=int(physical_order_changes[j]),
                    physical_order_changed_endpoint_count=int(physical_order_endpoint_changes[j]),
                    pruned_local_code=int(codes[j]), pruned_trace=trimmed[int(codes[j])][0],
                    pruned_endpoint=trimmed[int(codes[j])][1])
        if arm == "F":
            ref = old["trials"]["straight"][i]["float"]
            item["pr137_scores_exact"] = (full, end, train_end, int(codes[j])) == (ref["sequence_correct"], ref["endpoint_correct"],
                                                                                ref["train_endpoint_correct_of_64"], ref["truth_table_code"])
    summary = {}
    for arm in ARMS:
        group = [item for item in meta if item["arm"] == arm]
        summary[arm] = {
            "independent_trace_and_endpoint_and_train_counts_match": sum(m["independent_counts_match"] for m in group),
            "changing_reduction_to_physical_socket_order_changed_any_case": sum(m["physical_order_changed_trace_count"] > 0 for m in group),
            "perfect_before_pruning": sum(m["full_trace"] == PAIR_COUNT for m in group),
            "perfect_after_pruning": sum(m["pruned_trace"] == PAIR_COUNT for m in group),
            "pruning_improved_trace": sum(m["pruned_trace"] > m["full_trace"] for m in group),
            "pruning_worsened_trace": sum(m["pruned_trace"] < m["full_trace"] for m in group),
            "perfect_only_after_pruning": [m["seed"] for m in group if m["pruned_trace"] == PAIR_COUNT and m["full_trace"] < PAIR_COUNT],
            "active_non_teacher_weights_at_end": sum(m["nonzero_final_outside_teacher_mask"] > 0 for m in group),
            "active_previously_forbidden_weights_at_end": sum(m["nonzero_after_release_outside_early_mask"] > 0 for m in group),
        }
    assert all(m["independent_counts_match"] for m in meta)
    assert all(m["pr137_four_weights_exact"] and m["pr137_scores_exact"] and m["pr137_changed_updates_exact"] for m in meta if m["arm"] == "F")
    report = {"method": "Independent integer S1 registers and per-round borrow oracle, physical role permutations reconstructed, ordered float64 accumulation A0..7,B0..8,C,q,bias. No model code imported and no retraining.",
              "evidence_scope": {"packet": "Checkpoint self-description lists only unsigned role names, or those roles plus ternary signs. All 80 initial checkpoints are zero. Source inspection: teacher() emits names/signs only; arrange() constructs masks/sign projections; target is the final label only. Raw weights alone cannot prove which inputs were supplied to training.",
                                 "released_masks": "Trainer source allows all 20 coefficients in A/B/S/C from update 65; F remains on 3 roles plus bias. For all 80 checkpoints early-mask and sign restrictions tested where applicable. A zero post-training coefficient need not mean it was frozen.",
                                 "pruning": "Post-hoc analysis only: zero the 16 off-teacher coefficients, keep the learned three teacher-addressed coefficients and original learned bias. Re-evaluate without retraining. No change to any model."},
              "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in (results_path, old_path, ROOT/"transfer.py", ROOT/"protocol.md", ROOT/"upstream"/"serial_adder.py", ROOT/"upstream"/"run_borrow.py", ROOT/"raw_internal.bin")},
              "case_count": PAIR_COUNT, "ordered_pair_mapping": "256*a+b", "rounds": 8,
              "spot": {"seed": 20261198, "size_including_boundaries": len(spot), "ids_sha256_little_endian_uint16": sha(spot.astype("<u2").tobytes())},
              "exhaustive_ground_truth_raw_matches_archive": True, "all_9bit_sums_and_stop_schedule_correct": True,
              "summary": summary, "checkpoints": meta}
    (ROOT / "audit.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
