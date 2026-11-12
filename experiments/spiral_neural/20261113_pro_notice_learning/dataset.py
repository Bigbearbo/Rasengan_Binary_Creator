"""Frozen legal UR1 message pairs; metadata never enters the neural interface."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from dataclasses import replace

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CODEC_PATH = HERE.parent / "20261113_pro_upgrade_notice/notice_codec.py"
CODEC_SHA = "2e2078fb3782156d91dd7c43ade69d42ee20ac7d19d2aeed8ad812d06d9a5ed8"
PATHS = ((0,), (1,), (2,), (5, 0), (5, 1), (5, 5, 0))
HELD_WIDTHS = (4, 5, 6, 4, 6, 5)
WIDTHS = (4, 5, 6)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def json_sha(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_codec():
    if file_sha(CODEC_PATH) != CODEC_SHA:
        raise ValueError("Pinned UR1 codec source differs")
    spec = importlib.util.spec_from_file_location("pro_notice_frozen_codec", CODEC_PATH)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


codec = load_codec()


def teacher_tree(path, target):
    """An independent valid pre-event snapshot, not a live shuffled event stream."""
    tree = codec.fixture_tree()
    branch = codec.branch_at(tree, path)
    return codec._replace_branch(tree, tuple(path), replace(branch, n=target - 1))


def make_rows():
    rows = []
    for index, (path, held_width) in enumerate(zip(PATHS, HELD_WIDTHS, strict=True)):
        for target in WIDTHS:
            tree = teacher_tree(path, target)
            before = codec.branch_at(tree, path)
            q = codec.encode_notice(path, target, tree)
            notice = codec.decode_notice(q, tree, profile_id=codec.PROFILE_ID)
            a = codec.encode_reply(notice)
            codec.verify_reply(notice, a, tree, profile_id=codec.PROFILE_ID)
            assert before.k == 1 and notice.current_n == target - 1
            assert len(q) == 8 + 4 * (len(path) + 1) + 4 * (target + 1)
            assert len(a) == 4 * (len(path) + 1) + target + 1
            rows.append({"id": f"p{index}_m{target}", "path": list(path),
                         "target_n": target, "current_n": target - 1, "k": 1,
                         "role": before.role, "highwater": before.highwater,
                         "ordinary_ids": list(before.ordinary_ids),
                         "split": "heldout" if target == held_width else "train",
                         "Q": q, "A": a, "address_bits": notice.address_bits,
                         "up_bits": notice.up_bits, "end_bits": notice.end_bits,
                         "target_updates": len(a) + 1})
    return rows


def validate_rows(rows):
    train = [row for row in rows if row["split"] == "train"]
    heldout = [row for row in rows if row["split"] == "heldout"]
    assert len(rows) == 18 and len(train) == 12 and len(heldout) == 6
    assert len({row["Q"] for row in rows}) == 18
    assert sum(row["target_updates"] for row in train) == 212
    assert sum(row["target_updates"] for row in heldout) == 106
    assert max(len(row["Q"] + row["A"]) for row in rows) == 75
    assert max(row["target_updates"] for row in rows) == 24
    assert max(len(row["Q"] + row["A"]) for row in train) == 75
    assert {row["up_bits"] for row in train} == {row["up_bits"] for row in rows}
    assert {row["end_bits"] for row in train} == {row["end_bits"] for row in rows}
    assert {m: sum(r["target_n"] == m for r in train) for m in WIDTHS} == {4: 4, 5: 4, 6: 4}
    assert {m: sum(r["target_updates"] for r in train if r["target_n"] == m)
            for m in WIDTHS} == {4: 68, 5: 68, 6: 76}
    labels = {}
    for row in rows:
        assert set(row["Q"] + row["A"]) <= {"0", "1"}
        for position, target in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            assert prefix not in labels or labels[prefix] == target
            labels[prefix] = target
    for path in PATHS:
        assert sum(tuple(r["path"]) == path for r in train) == 2
        assert sum(tuple(r["path"]) == path for r in heldout) == 1
    return {"rows": 18, "train": 12, "heldout": 6,
            "train_targets_per_epoch": 212, "heldout_targets": 106,
            "max_prefix": 75, "max_generation_steps_including_STOP": 24,
            "all_symbols_and_maximum_prefix_length_seen_in_train": True,
            "consistent_teacher_prefix_labels": len(labels)}


def exposure_ledger(rows, epochs):
    train = [row for row in rows if row["split"] == "train"]
    return {
        "per_seed_presentations_by_width": {str(m): epochs * sum(r["target_n"] == m for r in train) for m in WIDTHS},
        "per_seed_targets_by_width": {str(m): epochs * sum(r["target_updates"] for r in train if r["target_n"] == m) for m in WIDTHS},
        "per_seed_input_bit_exposures": epochs * sum(len(r["Q"]) for r in train),
        "per_seed_teacher_answer_bit_exposures": epochs * sum(len(r["A"]) for r in train),
        "per_seed_STOP_targets": epochs * len(train),
        "per_row": [{"id": r["id"], "split": r["split"],
                     "training_presentations_per_seed": epochs if r["split"] == "train" else 0,
                     "Q_bits": len(r["Q"]), "A_bits": len(r["A"]),
                     "UP_words_per_input": 3, "UP_words_per_teacher_reply": 1}
                    for r in rows],
    }


def make_curricula(rows, seeds, epochs, seed_offset):
    train_ids = [row["id"] for row in rows if row["split"] == "train"]
    by_id = {row["id"]: row for row in rows}
    result = {}
    for seed in seeds:
        rng = np.random.default_rng(seed + seed_offset)
        orders = [rng.permutation(train_ids).tolist() for _ in range(epochs)]
        assert all(sorted(order) == sorted(train_ids) for order in orders)
        stream = hashlib.sha256()
        for order in orders:
            for row_id in order:
                row = by_id[row_id]
                for position, target in enumerate(row["A"] + "S"):
                    stream.update((canonical([row["Q"] + row["A"][:position], target]) + "\n").encode())
        result[str(seed)] = {"schedule_seed": seed + seed_offset, "epochs": orders,
                             "curriculum_sha256": json_sha(orders),
                             "raw_teacher_target_stream_sha256": stream.hexdigest()}
    return result
