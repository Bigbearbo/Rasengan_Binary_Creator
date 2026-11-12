"""Read-only result audit. Run only after the executor explicitly confirms completion.

No optimizer, gradient, lesson, growth, or training replay is permitted. This
audit recomputes free generation and teacher-prefix predictions at the eighteen
fixed checkpoints, checks the saved target transcript, and writes only its own
review JSON. --confirmed-complete is required in addition to a complete summary.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
from itertools import zip_longest
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time

if sys.flags.optimize:
    raise RuntimeError("Result review requires assertions and rejects optimized Python")

import dataset
import learner
import numpy as np

HERE = Path(__file__).resolve().parent
REGISTRATION_COMMIT = "0b6de1d24481c2886833e412d173645fca98609c"
MANIFEST_SHA = "d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0"
CHECKPOINTS = (0, 16, 32, 64, 96, 128)
SEEDS = (101, 202, 303)
SHAPES = ((160, 64), (64,), (64, 3), (3,))
FORWARD_MAC = 64 * (2 * 80 + 3)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_hashes(folder):
    return {str(path.relative_to(folder)): dataset.file_sha(path)
            for path in sorted(folder.rglob("*")) if path.is_file()}


def arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name].copy() for name in archive.files}


def equal_arrays(left, right):
    return left.keys() == right.keys() and all(np.array_equal(value, right[name]) for name, value in left.items())


def independent_metrics(records):
    result = {}
    for split in ("train", "heldout"):
        part = [record for record in records if record["split"] == split]
        if not part:
            continue
        tf = [token for record in part for token in record["teacher_forcing"]]
        result[split] = {"total": len(part),
                        **{name: sum(bool(record[name]) for record in part) for name in
                           ("whole_correct", "address_correct", "UP_correct_at_expected_position",
                            "STOP_position_correct", "overflow", "cap_exhausted")},
                        "teacher_targets": len(tf),
                        "teacher_correct": sum(token["prediction"] == token["target"] for token in tf),
                        "teacher_CE_mean": sum(token["target_CE"] for token in tf) / len(tf)}
    return result


def independent_truth(net, rows):
    """Only frozen net.forward is used; generation is independent of learner.evaluate."""
    records = []
    for row in rows:
        q, tokens, free = row["Q"], "", []
        overflow = exhausted = False
        for _ in range(24):
            prefix = q + tokens
            if len(prefix) > net.L:
                overflow = True
                break
            logits = net.forward(prefix)[2].copy()
            prediction = "01S"[int(np.argmax(logits))]
            free.append({"prefix": prefix, "prediction": prediction, "logits": logits.tolist()})
            tokens += prediction
            if prediction == "S":
                break
        else:
            exhausted = True
        # Labels and address boundaries are consulted only after free generation.
        a, tf = row["A"], []
        for position, target in enumerate(a + "S"):
            logits = net.forward(q + a[:position])[2].astype(np.float64)
            logp = logits - np.logaddexp.reduce(logits)
            tf.append({"position": position, "target": target,
                       "prediction": "01S"[int(np.argmax(logits))], "logits": logits.tolist(),
                       "probabilities_01S": np.exp(logp).tolist(),
                       "target_CE": -float(logp["01S".index(target)])})
        expected = a + "S"
        first_error = next((index for index, pair in enumerate(zip_longest(tokens, expected)) if pair[0] != pair[1]), None)
        boundary = len(row["address_bits"])
        records.append({"id": row["id"], "split": row["split"], "path": row["path"],
                        "target_n": row["target_n"], "Q": q, "target": expected,
                        "generated": tokens, "whole_correct": tokens == expected,
                        "address_correct": tokens[:boundary] == row["address_bits"],
                        "UP_correct_at_expected_position": tokens[boundary:len(a)] == row["up_bits"],
                        "STOP_position_correct": tokens.endswith("S") and len(tokens) == len(expected),
                        "first_error_position_zero_based": first_error,
                        "overflow": overflow, "cap_exhausted": exhausted,
                        "teacher_forcing": tf, "free_run": free})
    return records


class Audit:
    def __init__(self):
        self.inference_calls = self.inference_macs = self.forbidden_calls = 0
        self.cases = self.teacher_targets = self.trace_targets = self.boundary_hashes = 0
        self.max_logit_error = 0.0
        self.checkpoint_records = []

    def forbid_training(self):
        def forbidden(*args, **kwargs):
            self.forbidden_calls += 1
            raise RuntimeError("Independent review forbids optimizer, gradient, lesson, and growth calls")
        for name in ("step", "lesson", "loss_grad", "grow"):
            setattr(learner.reference.Model, name, forbidden)

    def check_sources(self):
        manifest_path = HERE / "frozen_manifest.json"
        require(dataset.file_sha(manifest_path) == MANIFEST_SHA, "approved manifest SHA")
        manifest = read(manifest_path)
        rel = str(manifest_path.relative_to(dataset.REPO))
        frozen_blob = subprocess.run(["git", "show", f"{REGISTRATION_COMMIT}:{rel}"], cwd=dataset.REPO,
                                     check=True, capture_output=True).stdout
        require(hashlib.sha256(frozen_blob).hexdigest() == MANIFEST_SHA, "manifest existed in preregistered Git commit")
        for rel, expected in manifest["source_hashes"].items():
            require(dataset.file_sha(dataset.REPO / rel) == expected, f"local frozen source {rel}")
            blob = subprocess.run(["git", "show", f"{REGISTRATION_COMMIT}:{rel}"], cwd=dataset.REPO,
                                  check=True, capture_output=True).stdout
            require(hashlib.sha256(blob).hexdigest() == expected, f"committed frozen source {rel}")
        require(manifest["rows"] == dataset.make_rows(), "frozen dataset regenerated exactly")
        p = manifest["protocol"]
        require(p == read(HERE / "protocol.json"), "frozen protocol")
        require(p["seeds"] == list(SEEDS) and p["checkpoint_epochs"] == list(CHECKPOINTS), "frozen seeds/checkpoints")
        courses = dataset.make_curricula(manifest["rows"], p["seeds"], p["epochs"], p["schedule_seed_offset"])
        require(courses == manifest["curricula"], "all frozen curricula and raw target-stream hashes")
        require(read(HERE / "source-freeze.json")["manifest_sha256"] == MANIFEST_SHA, "source-freeze manifest hash")
        return manifest

    def check_state(self, saved, seed, epoch, initial):
        require(set(saved) == set(initial), "complete state keys including optimizer and metadata")
        require((int(saved["L"]), int(saved["H"]), int(saved["meta_seed"])) == (80, 64, seed), "state architecture/seed")
        require(int(saved["t"]) == epoch * 212 and int(saved["meta_train_macs"]) == epoch * 212 * 21056, "state update/MAC budget")
        for group in ("p", "m", "v", "birth"):
            for index, shape in enumerate(SHAPES):
                value = saved[f"{group}{index}"]
                require(value.shape == shape, "state array shape")
                require(value.dtype == (np.int64 if group == "birth" else np.float32), "state array dtype")
                require(np.isfinite(value).all(), "finite state arrays")
                if group == "birth":
                    require(np.count_nonzero(value) == 0, "no unregistered growth/birth event")
        require(str(saved["growth_rng"]) == str(initial["growth_rng"]), "fixed network growth RNG unchanged")
        require(str(saved["meta_events"]) == "[]", "no growth events")

    def check_trace(self, path, manifest, seed, summary, boundaries):
        rows = {row["id"]: row for row in manifest["rows"] if row["split"] == "train"}
        digest, raw_digest, counts = hashlib.sha256(), hashlib.sha256(), Counter()
        total = 0
        with gzip.open(path, "rt", encoding="utf-8", newline="\n") as stream:
            for epoch, order in enumerate(manifest["curricula"][str(seed)]["epochs"], 1):
                for row_id in order:
                    row = rows[row_id]
                    counts[row_id] += 1
                    for position, target in enumerate(row["A"] + "S"):
                        line = stream.readline()
                        require(bool(line), "complete target trace")
                        record = json.loads(line)
                        total += 1
                        prefix = row["Q"] + row["A"][:position]
                        require((record["epoch"], record["row_id"], record["position"], record["prefix"], record["target"])
                                == (epoch, row_id, position, prefix, target), "trace follows frozen curriculum/prefix/label")
                        require(record["global_update"] == total and record["train_dense_MAC"] == total * 21056, "trace update/MAC count")
                        require(record["prediction"] in "01S" and math.isfinite(record["loss"]) and record["loss"] >= 0, "trace prediction/loss")
                        require(len(record["full_state_sha256"]) == 64, "trace state hash present")
                        require(line == dataset.canonical(record) + "\n", "canonical saved trace")
                        digest.update(line.encode())
                        raw_digest.update((dataset.canonical([prefix, target]) + "\n").encode())
                        if total in boundaries:
                            require(record["full_state_sha256"] == boundaries[total], "checkpoint state matches pre-diagnostic last-target hash")
                            self.boundary_hashes += 1
            require(not stream.readline(), "no extra target records")
        require(total == 27136 and all(count == 128 for count in counts.values()) and len(counts) == 12, "complete fixed exposure budget")
        require(summary["trace"] == {"targets": total, "uncompressed_stream_sha256": digest.hexdigest()}, "trace summary hash")
        require(summary["trace_file_sha256"] == dataset.file_sha(path), "compressed trace hash")
        require(raw_digest.hexdigest() == manifest["curricula"][str(seed)]["raw_teacher_target_stream_sha256"], "raw teacher stream hash")
        self.trace_targets += total
        return {"targets": total, "uncompressed_stream_sha256": digest.hexdigest(),
                "raw_teacher_target_stream_sha256": raw_digest.hexdigest(), "lessons_per_combination": 128}

    def run(self, folder):
        # This is the first formal artifact read; the caller has confirmed completion.
        summary = read(folder / "summary.json")
        require(summary["status"] == "complete", "executor summary reports complete")
        self.forbid_training()
        started = time.perf_counter()
        original_hashes = file_hashes(folder)
        manifest = self.check_sources()
        require(read(folder / "manifest.json") == manifest, "executed manifest exactly matches registration")
        require(summary["manifest_sha256"] == MANIFEST_SHA, "result manifest SHA")
        start = read(folder / "execution-start.json")
        require(start["formal_started"] is True and start["manifest_sha256"] == MANIFEST_SHA, "execution manifest record")
        timings = read(folder / "timing.json")["trajectories"]
        require([(item["mode"], item["seed"]) for item in timings]
                == [(mode, seed) for mode in ("primary", "replay") for seed in SEEDS], "all primary then replay completion records")
        require(not (folder / "failure.json").exists(), "no incomplete execution marker")
        rows = manifest["rows"]
        students, traces = [], []
        original_diagnostic_macs = 0
        original_offline_macs = original_offline_calls = 0
        for seed in SEEDS:
            case_folder = folder / f"seed{seed}"
            initial = arrays(case_folder / "initial-state.npz")
            require(equal_arrays(initial, learner.full_state(learner.new_student(seed))), "deterministic saved initial complete state")
            train_curve = read(case_folder / "curve.json")
            offline_curve = read(case_folder / "offline-curve.json")
            require([point["epoch"] for point in train_curve] == list(CHECKPOINTS), "train checkpoints fixed")
            require([point["epoch"] for point in offline_curve] == list(CHECKPOINTS), "offline checkpoints fixed")
            previous_calls = previous_macs = 0
            boundaries = {}
            for epoch, train_point, offline_point in zip(CHECKPOINTS, train_curve, offline_curve, strict=True):
                path = case_folder / f"state-{epoch:03}.npz"
                saved = arrays(path)
                self.check_state(saved, seed, epoch, initial)
                require(learner.state_sha(saved) == train_point["state_sha256"], "training curve complete-state hash")
                require(dataset.file_sha(path) == offline_point["checkpoint_sha256"], "offline checkpoint file hash")
                if epoch:
                    before_diagnostic = {name: value.copy() for name, value in saved.items()}
                    before_diagnostic["meta_inference_calls"] = np.array(previous_calls, dtype=saved["meta_inference_calls"].dtype)
                    before_diagnostic["meta_inference_macs"] = np.array(previous_macs, dtype=saved["meta_inference_macs"].dtype)
                    boundaries[epoch * 212] = learner.state_sha(before_diagnostic)
                net = learner.load_state(path)
                require(equal_arrays(saved, learner.full_state(net)), "all saved arrays and metadata restore exactly")
                before_learning = net.state()
                calls, macs = net.inference_calls, net.inference_macs
                actual = independent_truth(net, rows)
                require(equal_arrays(before_learning, net.state()), "inference does not change parameters/Adam/birth/t/RNG")
                new_calls, new_macs = net.inference_calls - calls, net.inference_macs - macs
                self.inference_calls += new_calls
                self.inference_macs += new_macs
                require(new_macs == new_calls * FORWARD_MAC, "actual review inference MAC")
                truth_name = "final-truth.json" if epoch == 128 else f"offline-truth-{epoch:03}.json"
                expected = read(case_folder / truth_name)
                require(len(expected) == 18 and actual == expected, "all autonomous/TF logits and truth fields exactly reproduce")
                for actual_row, expected_row in zip(actual, expected, strict=True):
                    for mode in ("free_run", "teacher_forcing"):
                        for left, right in zip(actual_row[mode], expected_row[mode], strict=True):
                            error = float(np.max(np.abs(np.array(left["logits"]) - np.array(right["logits"]))))
                            self.max_logit_error = max(self.max_logit_error, error)
                score = independent_metrics(actual)
                require(score == offline_point["metrics"], "offline metrics independently aggregate")
                require(new_calls == offline_point["diagnostic_inference_calls"] and new_macs == offline_point["diagnostic_dense_MAC"], "saved offline inference counters")
                train_truth = [item for item in actual if item["split"] == "train"]
                require(train_truth == read(case_folder / f"train-truth-{epoch:03}.json"), "training-only diagnostic truth reproduces")
                require(independent_metrics(train_truth) == train_point["metrics"], "training-only curve aggregation")
                train_calls = sum(len(item["free_run"]) + len(item["teacher_forcing"]) for item in train_truth)
                previous_calls += train_calls
                previous_macs += train_calls * FORWARD_MAC
                require(int(saved["meta_inference_calls"]) == previous_calls and int(saved["meta_inference_macs"]) == previous_macs, "saved cumulative training-diagnostic counters")
                self.cases += len(actual)
                self.teacher_targets += sum(len(item["teacher_forcing"]) for item in actual)
                self.checkpoint_records.append({"seed": seed, "epoch": epoch, "cases": len(actual),
                                                "state_file_sha256": dataset.file_sha(path),
                                                "actual_inference_calls": new_calls, "actual_inference_dense_MAC": new_macs,
                                                "train_whole": score["train"]["whole_correct"],
                                                "heldout_whole": score["heldout"]["whole_correct"]})
            final = arrays(case_folder / "final-state.npz")
            require(equal_arrays(final, saved), "final-state equals fixed epoch128 state")
            training = read(case_folder / "training-summary.json")
            require(training["targets"] == 27136 and training["lessons"] == 1536 and training["training_dense_MAC"] == 571375616, "student training budget")
            require(training["state_sha256"] == learner.state_sha(final), "training summary final state")
            require(training["training_diagnostic_inference_calls"] == previous_calls and training["training_diagnostic_dense_MAC"] == previous_macs, "training diagnostic summary")
            original_diagnostic_macs += previous_macs
            original_offline_calls += sum(point["diagnostic_inference_calls"] for point in offline_curve)
            original_offline_macs += sum(point["diagnostic_dense_MAC"] for point in offline_curve)
            traces.append({"seed": seed, **self.check_trace(case_folder / "targets.jsonl.gz", manifest, seed, training, boundaries)})
            require(read(case_folder / "final-failures.json") == [item for item in actual if not item["whole_correct"]], "all final failures retained")
            recorded = next(item for item in summary["students"] if item["seed"] == seed)
            require(recorded["metrics"] == score and recorded["checkpoint_sha256"] == dataset.file_sha(case_folder / "final-state.npz"), "final summary metrics and source")
            gate = score["train"]["whole_correct"] == 12 and score["heldout"]["whole_correct"] == 6
            require(recorded["strong_gate"] == gate, "unchanged per-student strong gate")
            students.append({"seed": seed, "train_whole": score["train"]["whole_correct"],
                             "heldout_whole": score["heldout"]["whole_correct"], "strong_gate": gate})
        for name, value in {"primary_targets": 81408, "replay_targets": 81408,
                            "primary_training_dense_MAC": 1714126848, "replay_training_dense_MAC": 1714126848,
                            "complete_trajectories": 3, "exact_replays": 3,
                            "p_m_v_birth_array_bytes_per_student": 209980}.items():
            require(summary[name] == value, f"overall budget {name}")
        require(summary["primary_training_diagnostic_dense_MAC"] == summary["replay_training_diagnostic_dense_MAC"] == original_diagnostic_macs, "primary/replay diagnostic costs")
        require(summary["offline_evaluation_dense_MAC"] == original_offline_macs and summary["offline_evaluation_inference_calls"] == original_offline_calls, "offline cost totals")
        require(summary["strong_gate_all_three"] == all(item["strong_gate"] for item in students), "overall frozen strong criterion")
        require(self.cases == 324 and self.trace_targets == 81408 and self.boundary_hashes == 15, "complete bounded audit coverage")
        require(file_hashes(folder) == original_hashes, "all formal artifacts unchanged during review")
        require(self.forbidden_calls == 0, "no forbidden training call")
        return {"passed": True, "status": "passed_no_findings_in_scope", "students": students,
                "strong_gate_all_three": all(item["strong_gate"] for item in students),
                "fixed_checkpoints_recomputed": 18, "other_initial_final_state_archives_checked": 6,
                "complete_cases_regenerated": self.cases, "teacher_prefix_predictions_recomputed": self.teacher_targets,
                "maximum_absolute_logit_difference": self.max_logit_error,
                "trace_targets_checked_without_training": self.trace_targets,
                "checkpoint_boundary_full_state_hashes_matched": self.boundary_hashes,
                "trace_reviews": traces, "checkpoints": self.checkpoint_records,
                "formal_artifact_hashes": original_hashes, "formal_artifacts_unchanged": True,
                "source_hashes": manifest["source_hashes"], "review_wall_seconds": time.perf_counter() - started,
                "limitations": [
                    "This audit does not rerun gradients or training; the formal replay completion is verified from fixed-driver evidence and saved completion records.",
                    "All transcript records are checked against the fixed curriculum and hashes; only saved checkpoint boundary state hashes are independently reconstructed.",
                    "The 324 cases are repeated checkpoint evaluations of eighteen fixed combinations, not 324 independent generalization examples.",
                    "ACK transduction does not establish branch grounding, semantic growth, malformed-frame rejection, or notification benefit.",
                ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmed-complete", action="store_true", help="Required after an explicit executor completion notification")
    parser.add_argument("--out", type=Path, default=HERE / "independent_result_review.json")
    args = parser.parse_args()
    if not args.confirmed_complete:
        parser.error("Wait for explicit executor completion and then supply --confirmed-complete")
    audit = Audit()
    try:
        report = audit.run(HERE / "formal_run")
    except Exception as error:
        report = {"passed": False, "error": type(error).__name__, "detail": str(error),
                  "fixed_checkpoints_completed": len(audit.checkpoint_records)}
    report.update({"author": "ChatGPT Pro / independent delegated result review",
                   "registration_commit": REGISTRATION_COMMIT, "approved_manifest_sha256": MANIFEST_SHA,
                   "command": "python -B independent_result_review.py --confirmed-complete --out independent_result_review.json",
                   "python_version": platform.python_version(), "numpy_version": np.__version__,
                   "review_training_updates": 0, "review_training_replays": 0,
                   "forbidden_training_calls": audit.forbidden_calls,
                   "review_actual_inference_calls": audit.inference_calls,
                   "review_actual_inference_dense_MAC": audit.inference_macs,
                   "review_script_sha256": dataset.file_sha(Path(__file__)),
                   "nvidia": {"status": "skipped_unavailable", "calls": 0}})
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({name: report[name] for name in ("passed", "students", "complete_cases_regenerated",
                     "teacher_prefix_predictions_recomputed", "review_actual_inference_calls",
                     "review_actual_inference_dense_MAC", "error", "detail") if name in report}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
