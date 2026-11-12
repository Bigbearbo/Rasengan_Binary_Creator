"""Bounded read-only PR13 audit: package/conditions and 54 final-checkpoint rows.

No training, full replay, intermediate-checkpoint inference, or external models.
All archives are read in memory; only this audit's requested JSON is written.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import zipfile

if not __debug__:
    raise RuntimeError("Run without -O; validation assertions must remain enabled")
sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

HERE = Path(__file__).resolve().parent
CODEX_COMMIT = "15b7788c1d50269f477b0681d64cbbd08708d65f"
PACKAGE_SHA = "947af4a1406bb463a11b17a823e0301bd98b4d790d6ea8352622af421a257748"
MANIFEST_SHA = "db37000543b4e8e7ef4b294883ad2346fddfd61b771a17857a1c525f1df189cc"
CONTROL_MANIFEST_SHA = "d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0"
BASELINE_PACKAGE_SHA = "51253e19dd24e69594b5233ec601dac94b30126a9be186d7bced2c3b3191e015"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def jsha(value):
    return sha(canonical(value).encode("utf-8"))


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_bytes(raw, info):
    assert len(raw) == info["bytes"] and sha(raw) == info["sha256"]
    if "Git_blob" in info:
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == info["Git_blob"]


def audit(package, source_root):
    import numpy as np

    before = {str(p.relative_to(package)): sha(p.read_bytes()) for p in package.rglob("*") if p.is_file()}
    assert before["package-manifest.json"] == PACKAGE_SHA
    assert before["baseline-inputs-manifest.json"] == BASELINE_PACKAGE_SHA
    assert before["prereg/manifest.json"] == MANIFEST_SHA
    published = read(package / "package-manifest.json")
    baseline_package = read(package / "baseline-inputs-manifest.json")
    for name, info in published["files"].items():
        verify_bytes((package / name).read_bytes(), info)
    assert published["manifest_sha256"] == MANIFEST_SHA
    assert published["prepublished_dependencies"]["manifest_sha256"] == BASELINE_PACKAGE_SHA

    # Validate every published archive member without extracting any path.
    archive_data, archive_counts = {}, {}
    for item in published["archives"] + baseline_package["archives"]:
        raw = (package / item["file"]).read_bytes()
        verify_bytes(raw, item)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)) == item["entry_count"] == len(item["entries"])
            assert set(names) == {entry["path"] for entry in item["entries"]}
            for entry in item["entries"]:
                content = archive.read(entry["path"])
                verify_bytes(content, entry)
                assert entry["path"] not in archive_data
                archive_data[entry["path"]] = content
            archive_counts[item["file"]] = len(names)

    def aj(name):
        return json.loads(archive_data[name])

    def arrays(raw):
        with np.load(io.BytesIO(raw), allow_pickle=False) as saved:
            return {name: saved[name].copy() for name in saved.files}

    def equal_arrays(a, b):
        return a.keys() == b.keys() and all(np.array_equal(a[k], b[k]) for k in a)

    manifest = read(package / "prereg/manifest.json")
    freeze = read(package / "prereg/source-freeze.json")
    protocol = read(package / "protocol.json")
    assert manifest == aj("prereg/manifest.json") == aj("run/manifest.json")
    assert freeze == aj("prereg/source-freeze.json")
    assert freeze["manifest_sha256"] == MANIFEST_SHA
    assert manifest["protocol"] == protocol
    for name, expected in manifest["local_source_hashes"].items():
        assert sha((package / name).read_bytes()) == expected == freeze["local_source_hashes"][name]
        assert (package / name).read_bytes() == archive_data["code/" + name]
    for name, expected in manifest["original_source_hashes"].items():
        assert sha((source_root / name).read_bytes()) == expected == freeze["original_source_hashes"][name]
    original_folder = source_root / "experiments/spiral_neural/20261113_pro_notice_learning"
    assert sha((original_folder / "frozen_manifest.json").read_bytes()) == CONTROL_MANIFEST_SHA
    baseline_manifest = aj("baseline/manifest.json")
    assert sha(archive_data["baseline/manifest.json"]) == CONTROL_MANIFEST_SHA
    assert baseline_manifest == read(original_folder / "frozen_manifest.json")
    assert manifest["rows"] == baseline_manifest["rows"]
    assert jsha(manifest["rows"]) == manifest["data_sha256"] == baseline_manifest["data_sha256"]
    assert manifest["runtime"] == baseline_manifest["runtime"]

    rows = manifest["rows"]
    train = [row for row in rows if row["split"] == "train"]
    held = [row for row in rows if row["split"] == "heldout"]
    assert (len(rows), len(train), len(held)) == (18, 12, 6)
    pool = [{"index": index, **item} for index, item in enumerate(
        {"row_id": row["id"], "position": position, "prefix": row["Q"] + row["A"][:position],
         "target": target, "target_n": row["target_n"]}
        for row in train for position, target in enumerate(row["A"] + "S"))]
    assert pool == manifest["target_pool"] == read(package / "prereg/target-pool.json")
    assert jsha(pool) == manifest["target_pool_sha256"]
    assert len(pool) == 212 and sum(item["target"] == "S" for item in pool) == 12
    expected_multiset = Counter((item["prefix"], item["target"]) for item in pool)
    by_id = {row["id"]: row for row in train}
    for course in baseline_manifest["curricula"].values():
        assert len(course["epochs"]) == 128
        for order in course["epochs"]:
            observed = Counter((by_id[rid]["Q"] + by_id[rid]["A"][:position], target)
                               for rid in order for position, target in enumerate(by_id[rid]["A"] + "S"))
            assert observed == expected_multiset
    schedule_bytes = (package / "prereg/schedules.npz").read_bytes()
    assert sha(schedule_bytes) == manifest["schedules_file_sha256"]
    schedules = arrays(schedule_bytes)
    assert set(schedules) == {"seed101", "seed202", "seed303"}
    for seed in (101, 202, 303):
        orders = schedules[f"seed{seed}"]
        assert orders.shape == (128, 212) and orders.dtype.str == "<i8"
        rng = np.random.default_rng(seed + 81000)
        regenerated = np.stack([rng.permutation(212) for _ in range(128)]).astype("<i8")
        assert np.array_equal(orders, regenerated)
        description = manifest["schedules"][str(seed)]
        assert sha(canonical([orders.dtype.str, list(orders.shape)]).encode() + orders.tobytes()) == description["array_sha256"]
        stream = hashlib.sha256()
        for order in orders:
            assert np.array_equal(np.sort(order), np.arange(212))
            for index in order:
                item = pool[int(index)]
                stream.update((canonical([item["prefix"], item["target"]]) + "\n").encode())
        assert stream.hexdigest() == description["raw_teacher_target_stream_sha256"]

    # Only now import the byte-verified inherited model and permanently forbid training.
    sys.path.insert(0, str(original_folder))
    import learner
    assert Path(learner.__file__).resolve() == original_folder / "learner.py"
    forbidden_calls = []
    def forbid(name):
        def blocked(*args, **kwargs):
            forbidden_calls.append(name)
            raise AssertionError("Training or growth is forbidden in this audit: " + name)
        return blocked
    for name in ("step", "lesson", "loss_grad", "grow"):
        setattr(learner.reference.Model, name, forbid(name))

    def restore(saved):
        net = learner.new_student(int(saved["meta_seed"]))
        for label in ("p", "m", "v", "birth"):
            setattr(net, label, [saved[f"{label}{i}"].copy() for i in range(4)])
        net.t = int(saved["t"])
        net.growth_rng.bit_generator.state = json.loads(str(saved["growth_rng"]))
        for name in ("train_macs", "inference_macs", "inference_calls"):
            setattr(net, name, int(saved["meta_" + name]))
        net.events = json.loads(str(saved["meta_events"]))
        assert equal_arrays(saved, learner.full_state(net))
        return net

    compact = read(package / "compact.json")
    summary, baseline_summary = aj("run/summary.json"), aj("baseline/summary.json")
    assert summary["status"] == baseline_summary["status"] == "complete"
    actual_rows, comparisons, initial_matches = [], [], []
    calls_total = macs_total = 0
    maximum_tf_delta = maximum_free_delta = 0.0
    for seed in (101, 202, 303):
        prior = arrays(archive_data[f"baseline/seed{seed}/initial-state.npz"])
        frozen_initial = arrays((package / f"prereg/initial-state-seed{seed}.npz").read_bytes())
        run_initial = arrays(archive_data[f"seed{seed}/initial-state.npz"])
        assert equal_arrays(prior, frozen_initial) and equal_arrays(prior, run_initial)
        assert learner.state_sha(prior) == manifest["control"]["students"][str(seed)]["initial_state_sha256"]
        assert int(prior["t"]) == int(prior["meta_train_macs"]) == 0
        initial_matches.append(seed)

        saved = arrays(archive_data[f"seed{seed}/final-state.npz"])
        net = restore(saved)
        assert net.t == 27136 and net.train_macs == 571375616 and net.parameters == 10499
        assert (net.L, net.H) == (80, 64)
        before_state = net.state()
        before_calls, before_macs = net.inference_calls, net.inference_macs
        actual = learner.evaluate(net, rows)  # Exactly 18 rows once per final checkpoint.
        assert equal_arrays(before_state, net.state())
        calls, macs = net.inference_calls - before_calls, net.inference_macs - before_macs
        assert calls == sum(len(row["free_run"]) + len(row["teacher_forcing"]) for row in actual)
        assert macs == calls * 64 * (2 * 80 + 3)
        calls_total += calls
        macs_total += macs
        archived = aj(f"seed{seed}/final-truth.json")
        assert len(actual) == len(archived) == 18
        for new, old in zip(actual, archived, strict=True):
            for key in ("id", "split", "path", "target_n", "Q", "target", "generated", "whole_correct",
                        "address_correct", "UP_correct_at_expected_position", "STOP_position_correct",
                        "first_error_position_zero_based", "overflow", "cap_exhausted"):
                assert new[key] == old[key], (seed, new["id"], key)
            for key in ("teacher_forcing", "free_run"):
                assert len(new[key]) == len(old[key])
                for a, b in zip(new[key], old[key], strict=True):
                    assert a["prediction"] == b["prediction"]
                    if key == "teacher_forcing":
                        assert a["position"] == b["position"] and a["target"] == b["target"]
                    else:
                        assert a["prefix"] == b["prefix"]
                    delta = float(np.max(np.abs(np.array(a["logits"]) - np.array(b["logits"]))))
                    if key == "teacher_forcing":
                        maximum_tf_delta = max(maximum_tf_delta, delta)
                    else:
                        maximum_free_delta = max(maximum_free_delta, delta)
                    np.testing.assert_allclose(a["logits"], b["logits"], atol=1e-5, rtol=1e-6)
        assert aj(f"seed{seed}/final-failures.json") == [row for row in archived if not row["whole_correct"]]
        score = learner.metrics(actual)
        published_student = next(row for row in compact["students"] if row["seed"] == seed)
        baseline_score = next(row for row in baseline_summary["students"] if row["seed"] == seed)["metrics"]
        for split in ("train", "heldout"):
            for key, value in score[split].items():
                if key == "teacher_CE_mean":
                    assert np.isclose(value, published_student["metrics"][split][key], atol=1e-5, rtol=1e-6)
                else:
                    assert value == published_student["metrics"][split][key]
        delta = {"train_whole_correct": score["train"]["whole_correct"] - baseline_score["train"]["whole_correct"],
                 "train_address_correct": score["train"]["address_correct"] - baseline_score["train"]["address_correct"],
                 "heldout_whole_correct_diagnostic": score["heldout"]["whole_correct"] - baseline_score["heldout"]["whole_correct"]}
        assert delta == published_student["paired_difference"]
        training_summary = aj(f"seed{seed}/training-summary.json")
        assert training_summary["targets"] == 27136 and training_summary["training_dense_MAC"] == 571375616
        assert training_summary["state_sha256"] == learner.state_sha(saved)
        comparisons.append({"seed": seed, "baseline_final_metrics": baseline_score,
                            "actual_final_metrics": score, "paired_difference": delta,
                            "actual_inference_calls": calls, "actual_inference_dense_MAC": macs,
                            "final_checkpoint_sha256": sha(archive_data[f"seed{seed}/final-state.npz"]),
                            "learning_state_unchanged": True})
        actual_rows.extend(actual)

    assert not forbidden_calls
    after = {str(p.relative_to(package)): sha(p.read_bytes()) for p in package.rglob("*") if p.is_file()}
    assert before == after
    assert all(sha((source_root / name).read_bytes()) == value for name, value in manifest["original_source_hashes"].items())
    return {
        "schema": "PRO-PR13-TARGET-ORDER-READONLY-v1", "author": "ChatGPT Pro",
        "status": "passed_no_findings_in_scope", "source_commit": CODEX_COMMIT,
        "package_manifest_sha256": PACKAGE_SHA, "prereg_manifest_sha256": MANIFEST_SHA,
        "control_manifest_sha256": CONTROL_MANIFEST_SHA, "baseline_package_manifest_sha256": BASELINE_PACKAGE_SHA,
        "audit_script_sha256": sha(Path(__file__).read_bytes()),
        "command": "python -B audit_target_order.py --out results.json",
        "working_directory": "experiments/spiral_neural/20261113_pro_echo_review",
        "python": platform.python_version(), "numpy": np.__version__,
        "package_file_hashes_verified": len(published["files"]),
        "archive_entries_verified": archive_counts, "total_archive_entries_verified": sum(archive_counts.values()),
        "local_scientific_sources_verified": len(manifest["local_source_hashes"]),
        "inherited_scientific_sources_verified": len(manifest["original_source_hashes"]),
        "paired_initial_states_verified": initial_matches,
        "original_and_shuffled_target_multiset_exact": True,
        "epochs_verified_per_seed": 128, "targets_per_epoch": 212,
        "frozen_target_streams_regenerated": 3, "actual_final_checkpoint_rows": len(actual_rows),
        "comparisons": comparisons,
        "pooled_final_train_whole": [sum(r["whole_correct"] for r in actual_rows if r["split"] == "train"), 36],
        "pooled_final_train_address": [sum(r["address_correct"] for r in actual_rows if r["split"] == "train"), 36],
        "pooled_final_heldout_whole": [sum(r["whole_correct"] for r in actual_rows if r["split"] == "heldout"), 18],
        "pooled_final_heldout_address": [sum(r["address_correct"] for r in actual_rows if r["split"] == "heldout"), 18],
        "final_cap_exhausted": sum(r["cap_exhausted"] for r in actual_rows),
        "final_overflow": sum(r["overflow"] for r in actual_rows),
        "max_actual_vs_archived_TF_logit_difference": maximum_tf_delta,
        "max_actual_vs_archived_free_run_logit_difference": maximum_free_delta,
        "actual_audit_inference_calls": calls_total, "actual_audit_inference_dense_MAC": macs_total,
        "inference_cost_scope": "New forward calls only; subtract copied checkpoint inference counters; includes free generation and TF",
        "forbidden_methods": ["Model.step", "Model.lesson", "Model.loss_grad", "Model.grow"],
        "forbidden_method_calls": forbidden_calls, "new_training_target_updates": 0,
        "new_students": 0, "full_training_replays": 0, "intermediate_checkpoint_inferences": 0,
        "source_package_and_inherited_sources_unchanged": True,
        "nvidia_status": "skipped_unavailable", "NVIDIA_calls_this_review": 0,
        "findings_in_scope": [],
        "limitations": [
            "Bounded audit of three final checkpoints, not a repeat of all 18 checkpoints or 324 responses.",
            "Large target traces are not republished; actual training trajectories and full replay were not independently rerun here.",
            "The fixed control scores come from pinned archived results, not new baseline inference or training.",
            "Identical target multisets, initial states, inherited sources and training budgets support an update-order comparison in this configuration.",
            "ACK fitting does not establish semantic Echo, unseen-combination success, SLE superiority, or a universal claim about fully connected networks.",
            "Historical Codex external-worker calls are separate from this review's zero calls.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=HERE.parent / "20261113_codex_target_order")
    parser.add_argument("--source-root", type=Path, default=HERE.parents[2])
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    args = parser.parse_args()
    output = args.out.resolve()
    assert output.is_relative_to(HERE), "Audit output must remain inside its own review directory"
    report = audit(args.package.resolve(), args.source_root.resolve())
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "status", "total_archive_entries_verified", "actual_final_checkpoint_rows",
        "pooled_final_train_whole", "pooled_final_heldout_whole", "actual_audit_inference_calls",
        "actual_audit_inference_dense_MAC", "max_actual_vs_archived_TF_logit_difference",
        "new_training_target_updates", "full_training_replays")}, indent=2))


if __name__ == "__main__":
    main()
