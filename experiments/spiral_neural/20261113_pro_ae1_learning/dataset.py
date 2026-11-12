#!/usr/bin/env python3
"""Frozen AE1 data preparation and pure-data checks; never imports a learner."""

import gzip
import hashlib
import importlib.util
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
CODEC_PATH = HERE.parent / "20261113_pro_advanced_echo" / "codec.py"
BASE_HEAD = "685c6f92d9e5a335a2f2a7193d9b501918d90b00"
DATA_SEED = 20261113
BLOCKED_PAYLOADS = {(1, 6, 11, 17)}
SEEDS = [101, 202, 303]

spec = importlib.util.spec_from_file_location("ae1_learning_codec", CODEC_PATH)
codec = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = codec
spec.loader.exec_module(codec)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _target_pool(rows):
    result = []
    for row in rows:
        if row["split"] != "train":
            continue
        for position, target in enumerate(row["A"] + "S"):
            result.append({"index": len(result), "row_id": row["id"],
                           "position": position,
                           "prefix": row["Q"] + row["A"][:position], "target": target})
    return result


def _exposure(rows, groups):
    train_groups = [g for g in groups if g["split"] == "train"]
    train_rows = [r for r in rows if r["split"] == "train"]
    by_group = {}
    for group in groups:
        if group["split"] != "test":
            continue
        body = tuple(group["payload_ids"])
        same, prefix, contiguous = [], [], []
        for source in train_groups:
            value = tuple(source["payload_ids"])
            if len(value) == len(body) and value == body:
                same.append(source["id"])
            if len(value) > len(body):
                if value[:len(body)] == body:
                    prefix.append(source["id"])
                if any(value[start:start + len(body)] == body
                       for start in range(len(value) - len(body) + 1)):
                    contiguous.append(source["id"])
        by_group[group["id"]] = {
            "same_length_complete_payload_train_count": len(same),
            "payload_prefix_of_longer_train_payload_count": len(prefix),
            "payload_contiguous_in_longer_train_payload_count": len(contiguous),
            "prefix_source_group_ids": prefix,
            "contiguous_source_group_ids": contiguous,
        }
    for row in rows:
        if row["split"] != "test":
            row["test_exposure"] = None
            continue
        a = row["A"]
        exact = [source["id"] for source in train_rows if source["A"] == a]
        proper_prefix = [source["id"] for source in train_rows
                         if len(source["A"]) > len(a) and source["A"].startswith(a)]
        row["test_exposure"] = by_group[row["group_id"]] | {
            "A_equals_train_complete_answer_count": len(exact),
            "A_is_proper_prefix_of_train_answer_count": len(proper_prefix),
            "A_is_prefix_or_equal_to_train_answer_count": len(exact) + len(proper_prefix),
            "complete_answer_source_row_ids": exact,
            "answer_prefix_source_row_ids": proper_prefix,
        }


def build_dataset():
    """Return deterministic raw rows, phase IDs and teacher-target pool indices."""
    rng = np.random.default_rng(DATA_SEED)
    groups, block_log = [], []
    for value in range(30):
        groups.append({"id": f"N1-train-b00-i{value:02d}", "split": "train",
                       "N": 1, "block": 0, "row_in_block": value,
                       "payload_ids": [value]})

    for n in (2, 3, 4):
        accepted = set()
        for block in range(6):
            split = "train" if block < 4 else "test"
            rejected_duplicate = rejected_blocked = 0
            for attempt in range(1, 100001):
                columns = [rng.permutation(30).tolist() for _ in range(n)]
                tuples = [tuple(column[i] for column in columns) for i in range(30)]
                duplicate = any(body in accepted for body in tuples)
                blocked = any(body in BLOCKED_PAYLOADS for body in tuples)
                if duplicate or blocked:
                    rejected_duplicate += int(duplicate)
                    rejected_blocked += int(blocked)
                    continue
                break
            else:
                raise RuntimeError("Balanced block rejection exceeded frozen safety bound")
            require(len(set(tuples)) == 30, "A permutation block repeated a payload")
            block_log.append({"N": n, "block": block, "split": split,
                              "attempts": attempt,
                              "rejected_for_duplicate": rejected_duplicate,
                              "rejected_for_blocked_fixture": rejected_blocked,
                              "accepted_payload_sha256": hashlib.sha256(canonical(tuples).encode()).hexdigest()})
            for i, body in enumerate(tuples):
                groups.append({"id": f"N{n}-{split}-b{block:02d}-i{i:02d}",
                               "split": split, "N": n, "block": block,
                               "row_in_block": i, "payload_ids": list(body)})
            accepted.update(tuples)

    rows = []
    for group in groups:
        counts = range(1, 5) if group["N"] == 4 else (group["N"],)
        for r in counts:
            q = codec.encode(group["payload_ids"], r, profile=codec.PROFILE)
            a = codec.answer(q, profile=codec.PROFILE)
            rows.append({"id": group["id"] + f"-r{r}", "group_id": group["id"],
                         "split": group["split"], "N": group["N"], "r": r,
                         "payload_ids": group["payload_ids"], "Q": q, "A": a,
                         "kind": "full_echo" if r == group["N"] else "prefix_echo",
                         "first_training_phase": None, "planned_question_exposures": 0})

    pool = _target_pool(rows)
    phases = []
    for limit, epochs in ((1, 24), (2, 8), (3, 8), (4, 8), (5, 8)):
        phase_id = f"full_N{limit}" if limit <= 4 else "count_N4"
        selected = [row for row in rows if row["split"] == "train" and
                    (limit == 5 or (row["N"] <= limit and row["r"] == row["N"]))]
        row_ids = [row["id"] for row in selected]
        ids = set(row_ids)
        indices = [item["index"] for item in pool if item["row_id"] in ids]
        for row in selected:
            row["planned_question_exposures"] += epochs
            if row["first_training_phase"] is None:
                row["first_training_phase"] = phase_id
        phases.append({"id": phase_id, "row_ids": row_ids, "epochs": epochs,
                       "targets_per_epoch": len(indices), "target_pool_indices": indices,
                       "planned_target_updates": len(indices) * epochs})
    _exposure(rows, groups)
    return {
        "id": "PRO-AE1-LEARNING-DATA-20261113", "profile": codec.PROFILE,
        "base_head": BASE_HEAD, "data_seed": DATA_SEED,
        "generator": {"rng": "numpy.random.default_rng(20261113)",
                      "order": "N=2,3,4; block=0..5; independent permutation(30) for each column; rows zip columns",
                      "split": "blocks0..3 train; blocks4..5 test; N1 all30 train",
                      "rejection": "Reject entire 30-row block if any same-N payload was accepted before or is blocked",
                      "max_attempts_per_block": 100000,
                      "blocked_complete_payloads": [list(x) for x in sorted(BLOCKED_PAYLOADS)],
                      "block_log": block_log,
                      "final_data_rng_state": rng.bit_generator.state},
        "scope": {"row_types": [[1, 1], [2, 2], [3, 3], [4, 1], [4, 2], [4, 3], [4, 4]],
                  "test_label": "held-out complete payload question combinations",
                  "not_claimed": "Not all-role unseen content, unseen IDs, unseen lengths, or a curriculum-efficiency comparison",
                  "N2_N3_partial_count_probes_included": False,
                  "no_validation_split": "All budgets/checkpoints are fixed, with no model or checkpoint selection"},
        "payload_groups": groups, "rows": rows, "phases": phases,
        "teacher_target_pool": pool,
        "target_pool_order": "Dataset order of train rows, then ascending position0..len(A), including external STOP",
        "source_sha256": {"codec.py": file_sha(CODEC_PATH), "dataset.py": file_sha(__file__)},
    }


def check_dataset(data):
    rows, groups, phases, pool = (data[name] for name in
                                  ("rows", "payload_groups", "phases", "teacher_target_pool"))
    require(data["profile"] == "SLE-AE1-n5-v1", "wrong profile")
    require(len(rows) == 1110 and len(groups) == 570, "wrong finite dataset size")
    require(Counter(row["split"] for row in rows) == {"train": 750, "test": 360}, "row split counts")
    require(len({(g["N"], tuple(g["payload_ids"])) for g in groups}) == len(groups),
            "duplicate complete payload across groups or splits")
    require(not any(tuple(g["payload_ids"]) in BLOCKED_PAYLOADS for g in groups), "public fixture leaked")
    require(len({row["id"] for row in rows}) == len(rows), "duplicate row ID")
    require(len({row["Q"] for row in rows}) == len(rows), "duplicate raw Q")
    by_id = {row["id"]: row for row in rows}
    group_rows = {g["id"]: [] for g in groups}
    for row in rows:
        group_rows[row["group_id"]].append(row)
        # Independent fixed-width reference, separate from codec encode/decode.
        expected_q = "01010" + format(row["r"], "03b") + "0" + "".join(
            format(v, "05b") + "0" for v in row["payload_ids"]) + "111100"
        expected_a = "".join(format(v, "05b") + "0" for v in row["payload_ids"][:row["r"]])
        require(row["Q"] == expected_q and row["A"] == expected_a, "raw question/answer mismatch")
        decoded = codec.decode(row["Q"], profile=codec.PROFILE)
        require(decoded.payload == tuple(row["payload_ids"]) and decoded.r == row["r"], "codec round-trip")
        require(len(row["Q"]) == 15 + 6 * row["N"] and len(row["A"]) == 6 * row["r"], "length mismatch")
        if row["split"] == "test":
            require(row["planned_question_exposures"] == 0 and row["first_training_phase"] is None, "test in curriculum")
            require(row["test_exposure"]["same_length_complete_payload_train_count"] == 0, "test exact payload taught")
    for group in groups:
        members = group_rows[group["id"]]
        require({row["split"] for row in members} == {group["split"]}, "payload family split leak")
        require([row["r"] for row in members] == (list(range(1, 5)) if group["N"] == 4 else [group["N"]]),
                "wrong count variants per family")

    coverage = []
    for n in (1, 2, 3, 4):
        for split in ("train", "test"):
            chosen = [g for g in groups if g["N"] == n and g["split"] == split]
            if not chosen:
                continue
            per_id = 1 if n == 1 else (4 if split == "train" else 2)
            positions = []
            for position in range(n):
                counts = Counter(g["payload_ids"][position] for g in chosen)
                require(counts == {v: per_id for v in range(30)}, "ordinary ID position imbalance")
                bit_ones = [sum(int(format(g["payload_ids"][position], "05b")[bit])
                                for g in chosen) for bit in range(5)]
                require(bit_ones == [14 * per_id] * 4 + [15 * per_id], "information bit marginal mismatch")
                positions.append({"position_zero_based": position,
                                  "ID_counts": {str(v): counts[v] for v in range(30)},
                                  "information_bit_ones_MSB_first": bit_ones,
                                  "information_bit_observations_per_bit": len(chosen),
                                  "suffix_zero_count": len(chosen)})
            coverage.append({"N": n, "split": split, "payload_groups": len(chosen),
                             "position_coverage": positions,
                             "groups_with_repeated_symbol": sum(len(set(g["payload_ids"])) < n for g in chosen)})

    q_sorted = sorted(row["Q"] for row in rows)
    require(not any(right.startswith(left) for left, right in zip(q_sorted, q_sorted[1:])), "complete Q prefix collision")
    teacher_labels, repeat = {}, 0
    for row in rows:
        for position, target in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            if prefix in teacher_labels:
                repeat += 1
                require(teacher_labels[prefix] == target, "teacher-prefix label contradiction")
            teacher_labels[prefix] = target
    require(repeat == 0, "different dataset rows unexpectedly shared a teacher prefix")
    require(len(pool) == 11730 and pool == _target_pool(rows), "canonical teacher target pool mismatch")
    expected_pool_sizes = [210, 1770, 4050, 7050, 11730]
    require([phase["targets_per_epoch"] for phase in phases] == expected_pool_sizes, "phase target counts")
    require([phase["epochs"] for phase in phases] == [24, 8, 8, 8, 8], "phase budgets")
    for phase in phases:
        ordered = [row for row in rows if row["id"] in set(phase["row_ids"])]
        require([row["id"] for row in ordered] == phase["row_ids"], "phase row order")
        require(all(row["split"] == "train" for row in ordered), "test row selected")
        require(sum(len(row["A"]) + 1 for row in ordered) == phase["targets_per_epoch"], "phase budget arithmetic")
        indices = [item["index"] for item in pool if item["row_id"] in set(phase["row_ids"])]
        require(indices == phase["target_pool_indices"], "phase target order/index mismatch")
    planned_updates = sum(phase["epochs"] * phase["targets_per_epoch"] for phase in phases)
    require(planned_updates == 201840, "total planned budget")
    target_labels = Counter()
    prefix_elements = 0
    for phase in phases:
        for index in phase["target_pool_indices"]:
            target_labels[pool[index]["target"]] += phase["epochs"]
            prefix_elements += len(pool[index]["prefix"]) * phase["epochs"]
    exposure_summary = []
    for n, r in ((2, 2), (3, 3), (4, 1), (4, 2), (4, 3), (4, 4)):
        selected = [row for row in rows if row["split"] == "test" and row["N"] == n and row["r"] == r]
        keys = ("payload_prefix_of_longer_train_payload_count", "payload_contiguous_in_longer_train_payload_count",
                "A_equals_train_complete_answer_count", "A_is_proper_prefix_of_train_answer_count",
                "A_is_prefix_or_equal_to_train_answer_count")
        exposure_summary.append({"N": n, "r": r, "rows": len(selected),
                                 "rows_with_exposure": {key: sum(row["test_exposure"][key] > 0 for row in selected)
                                                        for key in keys}})

    controls = {}
    for split in ("train", "test"):
        selected = [row for row in rows if row["split"] == split]
        copy_correct = wrong_correct = wrong_stop = 0
        for row in selected:
            a = row["A"]
            copy_all = "".join(format(v, "05b") + "0" for v in row["payload_ids"]) + "S"
            # Toggle first word's least significant information bit: ID xor1 stays0..29.
            wrong_bits = a[:4] + ("1" if a[4] == "0" else "0") + a[5:] + "S"
            copy_correct += int(copy_all == a + "S")
            wrong_correct += int(wrong_bits == a + "S")
            wrong_stop += int(wrong_bits.endswith("S") and len(wrong_bits) == len(a) + 1)
        require(copy_correct == sum(row["r"] == row["N"] for row in selected), "copy-to-END control")
        require(wrong_correct == 0 and wrong_stop == len(selected), "correct-count/wrong-bits control")
        controls[split] = {"rows": len(selected), "copy_to_END_whole_correct": copy_correct,
                           "correct_count_wrong_bits_whole_correct": wrong_correct,
                           "correct_count_wrong_bits_STOP_position_correct": wrong_stop}

    return {
        "status": "PASS", "actor": "ChatGPT Pro / delegated memory_review",
        "check_scope": "Deterministic data generation and pure-program checks; no learned model is loaded",
        "profile": data["profile"], "base_head": BASE_HEAD, "data_seed": DATA_SEED,
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "source_sha256": data["source_sha256"], "rows": {"train": 750, "test": 360},
        "payload_groups": {"train": 390, "test": 180},
        "coverage": coverage, "test_exposure_summary": exposure_summary,
        "raw_prefix_checks": {"unique_Q": len(q_sorted), "sorted_adjacent_Q_pairs_checked": len(q_sorted) - 1,
                              "Q_prefix_collisions": 0, "teacher_prefix_occurrences": len(teacher_labels) + repeat,
                              "unique_teacher_prefixes": len(teacher_labels), "same_prefix_repeats": repeat,
                              "teacher_label_contradictions": 0},
        "phases": [{key: phase[key] for key in ("id", "epochs", "targets_per_epoch", "planned_target_updates")}
                   | {"training_rows": len(phase["row_ids"])} for phase in phases],
        "planned_per_seed": {"target_updates": planned_updates, "training_dense_MAC_per_target": 21056,
                             "training_dense_MAC": planned_updates * 21056,
                             "question_equivalent_exposures": sum(len(p["row_ids"]) * p["epochs"] for p in phases),
                             "teacher_target_label_counts": dict(sorted(target_labels.items())),
                             "teacher_prefix_bit_elements": prefix_elements},
        "negative_controls": controls,
        "observed_lengths": {"max_Q": max(len(row["Q"]) for row in rows),
                             "max_A": max(len(row["A"]) for row in rows),
                             "max_teacher_prefix": max(len(row["Q"] + row["A"]) for row in rows),
                             "max_correct_generation_actions": max(len(row["A"]) + 1 for row in rows)},
        "actual_model_cost": {"NN_forward_calls": 0, "NN_MAC": 0, "training_updates": 0,
                              "external_model_calls": 0},
        "limitations": [
            "Only N4 has count contrasts; N2r1 and N3r1/r2 are not generated or evaluated in this round.",
            "Test means new complete payload question combinations; familiar IDs, cross-length substrings and answer prefixes are explicitly recorded.",
            "Uniform ID coverage implies information bit ones14/30 for the first four positions and15/30 for the last, not universal50/50.",
            "Cumulative phases expose shorter full questions more often and count contrasts expose earlier answer positions more often.",
            "A single staged arm with three seeds is an ability screen, not a causal curriculum or efficiency comparison.",
        ],
    }


def main():
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python -B dataset.py")
    previous_checks_path = HERE / "data_checks.json"
    previous_checks = json.loads(previous_checks_path.read_text()) if previous_checks_path.exists() else None
    old_plain = HERE / "dataset.json"
    old_plain_bytes = old_plain.read_bytes() if old_plain.exists() else None
    data = build_dataset()
    checks = check_dataset(data)
    raw = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    equivalence = None
    if old_plain_bytes is not None:
        old_data = json.loads(old_plain_bytes)
        old_sources = old_data.pop("source_sha256")
        current_science = {key: value for key, value in data.items() if key != "source_sha256"}
        require(canonical(old_data) == canonical(current_science), "Packaging changed scientific data")
        require(old_sources["codec.py"] == data["source_sha256"]["codec.py"], "Packaging changed codec source")
        equivalence = {"scientific_content_exactly_equal": True,
                       "old_plain_sha256": hashlib.sha256(old_plain_bytes).hexdigest(),
                       "only_metadata_difference": "dataset.py producer SHA changes because writer now emits gzip",
                       "old_dataset_py_sha256": old_sources["dataset.py"],
                       "new_dataset_py_sha256": data["source_sha256"]["dataset.py"]}
    target = HERE / "dataset.json.gz"
    target.write_bytes(gzip.compress(raw, mtime=0))
    require(gzip.decompress(target.read_bytes()) == raw, "Compressed artifact did not preserve exact JSON bytes")
    checks["dataset_json_gz_sha256"] = file_sha(target)
    checks["dataset_uncompressed_sha256"] = hashlib.sha256(raw).hexdigest()
    checks["artifact"] = {"file": "dataset.json.gz", "compression": "gzip.compress(raw,mtime=0)",
                          "compressed_bytes": target.stat().st_size, "uncompressed_bytes": len(raw),
                          "decompression_equals_generated_bytes": True,
                          "first_generation_equivalence": equivalence}
    checks["engineering_data_run_count"] = (previous_checks.get("engineering_data_run_count", 1)
                                             if previous_checks is not None else 0) + 1
    checks["command"] = "python -B experiments/spiral_neural/20261113_pro_ae1_learning/dataset.py"
    (HERE / "data_checks.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False) + "\n")
    if old_plain_bytes is not None:
        require(old_plain.read_bytes() == old_plain_bytes, "Plain artifact changed during compression")
        old_plain.unlink()
    print(canonical({"status": checks["status"], "rows": checks["rows"],
                     "payload_groups": checks["payload_groups"],
                     "phase_target_counts": [p["targets_per_epoch"] for p in data["phases"]],
                     "planned_updates_per_seed": checks["planned_per_seed"]["target_updates"],
                     "raw_prefix_checks": checks["raw_prefix_checks"],
                     "artifact": checks["artifact"],
                     "engineering_data_run_count": checks["engineering_data_run_count"],
                     "actual_model_cost": checks["actual_model_cost"]}))


if __name__ == "__main__":
    main()
