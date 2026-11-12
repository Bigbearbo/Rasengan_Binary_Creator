#!/usr/bin/env python3
"""After completion only: summarize saved AE1 records without importing a model.

Usage: python -B export_results.py --after-complete --prereg-commit SHA
Optional --independent-review FILE may be repeated. Raw independent reports are
preserved; only explicitly recognized accounting fields enter combined costs.
This file was added after preregistration and cannot change the frozen learner.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREG_COMMIT = "beb6dd7d4ce78d4f79e61164f838aaa881eafcd5"
SEEDS = (101, 202, 303)
ROW_TYPES = ((1, 1), (2, 2), (3, 3), (4, 1), (4, 2), (4, 3), (4, 4))
BOOL_FIELDS = ("whole_correct", "STOP_position_correct", "early_STOP", "late_STOP",
               "no_STOP", "overflow", "cap_exhausted", "END_at_expected_boundary")
SUM_FIELDS = ("free_info_correct", "free_info_total", "tf_correct", "tf_targets",
              "tf_info_correct", "tf_info_total")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def threshold_count(fraction, total):
    value = Fraction(str(fraction))
    return (value.numerator * total + value.denominator - 1) // value.denominator


class Inputs:
    """Hash every consumed input, and reject changes before publishing output."""

    def __init__(self):
        self.hashes = {}

    def label(self, path):
        resolved = Path(path).resolve()
        return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)

    def bytes(self, path):
        path = Path(path).resolve()
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        old = self.hashes.get(str(path))
        require(old is None or old == digest, f"Input changed during export: {path}")
        self.hashes[str(path)] = digest
        return raw

    def json(self, path):
        path = Path(path)
        raw = self.bytes(path)
        if path.suffix == ".gz":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))

    def digest(self, path):
        return hashlib.sha256(self.bytes(path)).hexdigest()

    def verify_unchanged(self):
        for path, digest in self.hashes.items():
            require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest,
                    f"Input changed before output: {path}")

    def inventory(self):
        return {self.label(path): digest for path, digest in sorted(self.hashes.items())}


def verify_public_freeze(inputs, commit):
    require(commit == PREREG_COMMIT, "This exporter is for the exact AE1 preregistration commit")
    manifest_path = HERE / "frozen_manifest.json"
    manifest = inputs.json(manifest_path)
    files = dict(manifest["files_sha256"])
    files[str(manifest_path.relative_to(ROOT))] = inputs.digest(manifest_path)
    for rel, expected in files.items():
        path = (ROOT / rel).resolve()
        require(path.is_relative_to(ROOT), "Frozen manifest path escapes repository")
        require(inputs.digest(path) == expected, f"Local frozen input differs: {rel}")
        raw = subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=ROOT,
                             check=True, capture_output=True).stdout
        require(hashlib.sha256(raw).hexdigest() == expected, f"Public freeze differs: {rel}")
    return manifest


def aggregate(records):
    records = list(records)
    result = {"total": len(records)}
    result.update({key: sum(bool(row[key]) for row in records) for key in BOOL_FIELDS})
    result.update({key: sum(row[key] for row in records) for key in SUM_FIELDS})
    result["tf_CE_mean"] = (sum(row["tf_CE_mean"] * row["tf_targets"] for row in records)
                            / result["tf_targets"] if result["tf_targets"] else None)
    result["whole_fraction"] = ratio(result["whole_correct"], result["total"])
    result["STOP_position_fraction"] = ratio(result["STOP_position_correct"], result["total"])
    result["free_information_bit_accuracy"] = ratio(result["free_info_correct"], result["free_info_total"])
    result["teacher_information_bit_accuracy"] = ratio(result["tf_info_correct"], result["tf_info_total"])
    result["teacher_all_token_accuracy"] = ratio(result["tf_correct"], result["tf_targets"])
    return result


def quartets(records):
    groups = {}
    for row in records:
        if row["N"] != 4:
            continue
        group = groups.setdefault(tuple(row["payload_ids"]), {})
        require(row["r"] not in group, "Duplicate count in N4 payload quartet")
        group[row["r"]] = row
    require(all(set(group) == {1, 2, 3, 4} for group in groups.values()), "Incomplete N4 quartet")
    whole = stop = boundary = all_boundaries = same_adjacent = 0
    distinct_outputs = Counter()
    for group in groups.values():
        whole += all(row["whole_correct"] for row in group.values())
        stop += all(row["STOP_position_correct"] for row in group.values())
        passed = []
        for r in (1, 2, 3):
            position = 6 * r
            passed.append(group[r]["tf_predictions"][position] == "S" and
                          group[r + 1]["tf_predictions"][position] == group[r + 1]["target"][position])
            same_adjacent += group[r]["generated"] == group[r + 1]["generated"]
        boundary += sum(passed)
        all_boundaries += all(passed)
        distinct_outputs[len({row["generated"] for row in group.values()})] += 1
    return {"payload_groups": len(groups), "whole_correct": whole, "whole_total": len(groups),
            "whole_fraction": ratio(whole, len(groups)), "STOP_quartet_correct": stop,
            "STOP_quartet_total": len(groups), "STOP_quartet_fraction": ratio(stop, len(groups)),
            "TF_adjacent_count_boundary_correct": boundary,
            "TF_adjacent_count_boundary_total": 3 * len(groups),
            "TF_all_three_boundaries_correct": all_boundaries,
            "TF_all_three_boundaries_total": len(groups),
            "descriptive_same_generation_on_adjacent_counts": same_adjacent,
            "descriptive_adjacent_count_pairs": 3 * len(groups),
            "descriptive_distinct_generated_strings_per_quartet":
                {str(i): distinct_outputs[i] for i in range(1, 5)},
            "descriptive_note": "Identical predictions are a behavior diagnostic, not proof that the model internally ignores count."}


def validate_records(point, data):
    expected_rows, records = data["rows"], point["records"]
    require([row["id"] for row in records] == [row["id"] for row in expected_rows],
            "Checkpoint has missing, duplicate or reordered row IDs")
    calls = 0
    for row, source in zip(records, expected_rows):
        for key in ("id", "N", "r", "split", "payload_ids"):
            require(row[key] == source[key], f"Record metadata differs: {row['id']} {key}")
        expected, actual, tf = source["A"] + "S", row["generated"], row["tf_predictions"]
        require(row["target"] == expected, "Stored target differs from frozen raw answer")
        require(isinstance(actual, str) and set(actual) <= {"0", "1", "S"} and len(actual) <= 32,
                "Invalid autonomous token string")
        require("S" not in actual[:-1] and actual.count("S") <= 1, "Generation continued after STOP")
        require(len(tf) == len(expected) and set(tf) <= {"0", "1", "S"}, "Invalid teacher predictions")
        info = [i for i in range(len(source["A"])) if i % 6 < 5]
        first_error = next((i for i in range(max(len(actual), len(expected)))
                            if (actual[i] if i < len(actual) else None)
                            != (expected[i] if i < len(expected) else None)), None)
        computed = {
            "whole_correct": actual == expected,
            "STOP_position_correct": actual.endswith("S") and len(actual) == len(expected),
            "early_STOP": actual.endswith("S") and len(actual) < len(expected),
            "late_STOP": actual.endswith("S") and len(actual) > len(expected),
            "no_STOP": not actual.endswith("S"), "first_error": first_error,
            "free_info_correct": sum(i < len(actual) and actual[i] == expected[i] for i in info),
            "free_info_total": 5 * source["r"],
            "tf_correct": sum(a == b for a, b in zip(tf, expected)),
            "tf_targets": len(expected),
            "tf_info_correct": sum(tf[i] == expected[i] for i in info),
            "tf_info_total": 5 * source["r"],
            "END_at_expected_boundary": actual[len(source["A"]):len(source["A"]) + 6] == "111100",
        }
        for key, value in computed.items():
            require(row[key] == value, f"Stored metric differs from saved tokens: {row['id']} {key}")
        require(not row["overflow"], "AE1 cap32 and L80 should never overflow")
        require(row["cap_exhausted"] == (not actual.endswith("S") and len(actual) == 32),
                "Cap flag differs from saved generation")
        require(actual.endswith("S") or row["cap_exhausted"], "Unexplained generation termination")
        require(math.isfinite(row["tf_CE_mean"]) and row["tf_CE_mean"] >= -1e-12,
                "Invalid stored teacher CE")
        calls += len(actual) + len(expected)
    require(point["inference_calls"] == calls, "Inference calls differ from generated/teacher token counts")
    require(point["inference_dense_MAC"] == calls * 10432, "Inference MAC differs from frozen forward cost")
    for split in ("train", "test"):
        chosen = [row for row in records if row["split"] == split]
        calculated = aggregate(chosen)
        saved = point["metrics"]["by_split"][split]
        for key in ("total",) + BOOL_FIELDS + SUM_FIELDS + ("tf_CE_mean",):
            require(calculated[key] == saved[key], f"Saved aggregate differs: {split}/{key}")
        q = quartets(chosen)
        for key in ("payload_groups", "whole_correct", "whole_total", "STOP_quartet_correct",
                    "STOP_quartet_total", "TF_adjacent_count_boundary_correct",
                    "TF_adjacent_count_boundary_total", "TF_all_three_boundaries_correct",
                    "TF_all_three_boundaries_total"):
            require(q[key] == saved["N4_quartets"][key], f"Saved quartet aggregate differs: {split}/{key}")
    return records


def full_echo_retention(before, after):
    old = {row["id"]: row for row in before}
    new = {row["id"]: row for row in after}
    require(old.keys() == new.keys(), "Retention checkpoint row identities differ")

    def table(ids):
        cells = {name: [] for name in ("retained", "lost", "gained", "both_wrong")}
        for rid in ids:
            was, now = old[rid]["whole_correct"], new[rid]["whole_correct"]
            name = "retained" if was and now else "lost" if was else "gained" if now else "both_wrong"
            cells[name].append(rid)
        counts = {key: len(value) for key, value in cells.items()}
        return {"total": len(ids), "phase4_whole_correct": counts["retained"] + counts["lost"],
                "phase5_whole_correct": counts["retained"] + counts["gained"],
                "counts": counts, "row_ids": cells}

    result = {}
    for split in ("train", "test"):
        selected = [row for row in before if row["split"] == split and row["N"] == row["r"]]
        result[split] = {"overall": table([row["id"] for row in selected]),
                         "by_N": {str(n): table([row["id"] for row in selected if row["N"] == n])
                                  for n in sorted({row["N"] for row in selected})}}
    return result


def exposure_subgroups(records, data_by_id):
    tests = [row for row in records if row["split"] == "test"]
    result = {"interpretation": "These overlapping descriptive subsets concern prior answer/payload exposure. They do not imply all-role novel content or independent samples.",
              "cells": {}}
    for n, r in sorted({(row["N"], row["r"]) for row in tests}):
        chosen = [row for row in tests if (row["N"], row["r"]) == (n, r)]
        cells = {}
        for label, key in (
            ("A_complete_answer", "A_equals_train_complete_answer_count"),
            ("A_proper_answer_prefix", "A_is_proper_prefix_of_train_answer_count"),
            ("A_complete_or_prefix", "A_is_prefix_or_equal_to_train_answer_count"),
            ("payload_prefix_of_longer_Q", "payload_prefix_of_longer_train_payload_count"),
            ("payload_contiguous_in_longer_Q", "payload_contiguous_in_longer_train_payload_count"),
        ):
            cells[label] = {
                "exposed": aggregate(row for row in chosen if data_by_id[row["id"]]["test_exposure"][key] > 0),
                "not_exposed_by_this_definition": aggregate(row for row in chosen if data_by_id[row["id"]]["test_exposure"][key] == 0)}
        result["cells"][f"{n}/{r}"] = cells
    result["N4_r_at_least_3"] = aggregate(row for row in tests if row["N"] == 4 and row["r"] >= 3)
    result["N4_r3"] = aggregate(row for row in tests if (row["N"], row["r"]) == (4, 3))
    result["N4_r4"] = aggregate(row for row in tests if (row["N"], row["r"]) == (4, 4))
    return result


def final_screen(records, protocol):
    criteria = protocol["evaluation"]["screening_success_per_seed"]
    train_cells = {}
    for n, r in ROW_TYPES:
        stats = aggregate(row for row in records if row["split"] == "train" and (row["N"], row["r"]) == (n, r))
        require(stats["total"] == (30 if n == 1 else 120), "Wrong train criterion denominator")
        minimum = threshold_count(criteria["final_train_whole_fraction_at_least_each_N_r"], stats["total"])
        train_cells[f"{n}/{r}"] = stats | {"whole_required": minimum, "criterion_pass": stats["whole_correct"] >= minimum}
    n4_rows = [row for row in records if row["split"] == "test" and row["N"] == 4]
    n4, quartet = aggregate(n4_rows), quartets(n4_rows)
    require(n4["total"] == 240 and quartet["whole_total"] == 60
            and quartet["TF_adjacent_count_boundary_total"] == 180, "Wrong N4 criterion denominator")
    required = {
        "whole_correct": threshold_count(criteria["final_N4_test_whole_fraction_at_least"], 240),
        "STOP_position_correct": threshold_count(criteria["final_N4_test_STOP_position_fraction_at_least"], 240),
        "whole_quartet_correct": threshold_count(criteria["final_N4_test_all_four_r_exact_quartet_fraction_at_least"], 60)}
    require(required == {"whole_correct": 228, "STOP_position_correct": 238, "whole_quartet_correct": 54},
            "Frozen criterion arithmetic changed")
    passes = {"all_train_N_r_cells": all(cell["criterion_pass"] for cell in train_cells.values()),
              "N4_test_whole": n4["whole_correct"] >= required["whole_correct"],
              "N4_test_STOP": n4["STOP_position_correct"] >= required["STOP_position_correct"],
              "N4_test_whole_quartets": quartet["whole_correct"] >= required["whole_quartet_correct"]}
    return {"final_train_by_N_r": train_cells, "final_train_all": aggregate(row for row in records if row["split"] == "train"),
            "final_test_all": aggregate(row for row in records if row["split"] == "test"),
            "final_test_by_N_r": {f"{n}/{r}": aggregate(row for row in records if row["split"] == "test"
                                                        and (row["N"], row["r"]) == (n, r))
                                  for n, r in ROW_TYPES if n > 1},
            "final_N4_test": n4, "final_N4_test_quartets": quartet,
            "integer_thresholds": required, "criterion_parts": passes,
            "screening_success": all(passes.values())}


def phase_curve(point, records, data):
    phase = point["phase"]
    taught = {rid for item in data["phases"][:phase] for rid in item["row_ids"]}
    trained = [row for row in records if row["id"] in taught]
    future = [row for row in records if row["split"] == "train" and row["id"] not in taught]
    for name, selected in (("taught_so_far_metrics", trained),
                           ("not_yet_taught_train_inventory_metrics", future)):
        actual = aggregate(selected)
        saved = point[name]["overall"]
        for key in ("total",) + BOOL_FIELDS + SUM_FIELDS + ("tf_CE_mean",):
            require(actual[key] == saved[key], f"Incorrect taught/future inventory metric: {phase}/{name}/{key}")
    train = [row for row in records if row["split"] == "train"]
    test = [row for row in records if row["split"] == "test"]
    return {"phase": phase, "updates": point["updates"],
            "phase_label": "initial" if phase == 0 else data["phases"][phase - 1]["id"],
            "taught_so_far": aggregate(trained), "not_yet_taught_train_inventory": aggregate(future),
            "final_train_inventory": aggregate(train), "test_inventory": aggregate(test),
            "full_echo_train": aggregate(row for row in train if row["N"] == row["r"]),
            "full_echo_test": aggregate(row for row in test if row["N"] == row["r"]),
            "N4_test": aggregate(row for row in test if row["N"] == 4),
            "N4_test_quartets": quartets(test),
            "scope_note": "Final inventories include rows not taught yet at early checkpoints; phase0 taught denominator is0, with undefined rates."}


def independent_report(inputs, path):
    report = inputs.json(path)
    recognized = None
    candidates = [report] + [report[key] for key in ("cost", "actual_cost", "actual_model_cost")
                             if isinstance(report.get(key), dict)]
    names = (("inference_calls", "inference_dense_MAC", "optimizer_updates"),
             ("NN_forward_calls", "NN_MAC", "training_updates"),
             ("actual_inference_calls", "actual_inference_dense_MAC", "actual_optimizer_updates"),
             ("neural_forward_calls", "dense_forward_MAC", "optimizer_updates"))
    for candidate in candidates:
        for calls, macs, updates in names:
            if all(key in candidate for key in (calls, macs, updates)):
                recognized = {"inference_calls": candidate[calls], "inference_dense_MAC": candidate[macs],
                              "optimizer_updates": candidate[updates]}
                require(all(type(value) is int and value >= 0 for value in recognized.values()),
                        "Invalid independent accounting values")
                break
        if recognized is not None:
            break
    return {"file": inputs.label(path), "sha256": inputs.digest(path), "recognized_cost": recognized,
            "cost_added_to_known_total": recognized is not None,
            "report": report}


def export_results(commit, independent_paths=()):
    """Must be invoked only after coordinator confirms all formal work completed."""
    independent_paths = [Path(path).resolve() for path in independent_paths]
    require(len(set(independent_paths)) == len(independent_paths),
            "Repeated independent report path would double-count the same audit")
    completion_files = [HERE / "runs" / f"primary_seed{seed}" / "summary.json" for seed in SEEDS]
    completion_files += [HERE / "runs/replay_seed101/summary.json", HERE / "replay_check.json",
                         HERE / "evaluation_summary.json"]
    require(all(path.is_file() for path in completion_files), "Formal work has not produced all completion records")
    inputs = Inputs()
    manifest = verify_public_freeze(inputs, commit)
    protocol, data, data_checks = (inputs.json(HERE / name) for name in
                                  ("protocol.json", "dataset.json.gz", "data_checks.json"))
    require(protocol["seeds"] == list(SEEDS), "Wrong seed set")
    require(Counter(row["split"] for row in data["rows"]) == {"train": 750, "test": 360}, "Wrong frozen row counts")
    data_by_id = {row["id"]: row for row in data["rows"]}
    require(len(data_by_id) == 1110, "Duplicate frozen row IDs")
    training = {}
    for role, seed in [("primary", seed) for seed in SEEDS] + [("replay", 101)]:
        folder = HERE / "runs" / f"{role}_seed{seed}"
        summary = inputs.json(folder / "summary.json")
        require(summary["status"] == "completed" and summary["role"] == role and summary["seed"] == seed,
                "Training trajectory not complete or mislabeled")
        require(summary["preregistration_commit"] == commit, "Training preregistration differs")
        require(summary["updates"] == 201840 and summary["train_dense_MAC"] == 201840 * 21056,
                "Training total budget differs")
        require(summary["actual_inference_calls_during_training"] == 0, "Unexpected performance evaluation during training")
        require([phase["phase"] for phase in summary["phases"]] == [1, 2, 3, 4, 5], "Missing training phase")
        for index, phase in enumerate(summary["phases"]):
            require(inputs.json(folder / f"phase{index + 1}.json") == phase, "Phase summary differs")
            require(phase["updates"] == protocol["curriculum"]["cumulative_updates"][index]
                    and phase["train_dense_MAC"] == phase["updates"] * 21056, "Phase budget differs")
            require(phase["id"] == data["phases"][index]["id"], "Phase curriculum ID differs")
            require(inputs.digest(folder / f"phase{index + 1}.npz") == phase["checkpoint_sha256"],
                    "Saved checkpoint file differs from training record")
        training[f"{role}_seed{seed}"] = summary
    replay = inputs.json(HERE / "replay_check.json")
    require(replay["status"] == "PASS" and replay["seed"] == 101
            and replay["phase_endpoints_compared"] == [1, 2, 3, 4, 5], "Replay was not fully verified")
    for first, second in zip(training["primary_seed101"]["phases"], training["replay_seed101"]["phases"]):
        for field in ("phase", "id", "updates", "train_dense_MAC", "epochs", "full_state_sha256"):
            require(first[field] == second[field], f"Replay mismatch in {field}")
    evaluation = inputs.json(HERE / "evaluation_summary.json")
    require(evaluation["status"] == "completed" and evaluation["preregistration_commit"] == commit
            and evaluation["optimizer_updates"] == 0, "Evaluation has not completed correctly")
    require(datetime.fromisoformat(evaluation["started_utc"]) >= max(
        datetime.fromisoformat(summary["finished_utc"]) for summary in training.values()),
        "Evaluation started before all primary/replay trajectories finished")
    require(datetime.fromisoformat(evaluation["started_utc"]) >= datetime.fromisoformat(replay["finished_utc"]),
            "Evaluation started before replay verification")
    summary_points = {(p["seed"], p["phase"]): p for p in evaluation["checkpoints"]}
    require(len(evaluation["checkpoints"]) == 18 and set(summary_points) == {(s, p) for s in SEEDS for p in range(6)},
            "Missing or duplicate evaluation checkpoints")
    students, actual_calls, actual_macs, question_evaluations = [], 0, 0, 0
    for seed in SEEDS:
        curves, phase4, final = [], None, None
        for phase in range(6):
            point = inputs.json(HERE / "evaluation" / f"seed{seed}_phase{phase}.json")
            require(point["seed"] == seed and point["phase"] == phase, "Wrong evaluation file identity")
            require({key: value for key, value in point.items() if key != "records"} == summary_points[seed, phase],
                    "Evaluation point and summary differ")
            checkpoint = HERE / "frozen" / f"initial_seed{seed}.npz" if phase == 0 else HERE / "runs" / f"primary_seed{seed}" / f"phase{phase}.npz"
            require(inputs.digest(checkpoint) == point["checkpoint_sha256"], "Evaluated checkpoint hash differs")
            require(point["updates"] == (0 if phase == 0 else protocol["curriculum"]["cumulative_updates"][phase - 1]),
                    "Wrong evaluated update budget")
            records = validate_records(point, data)
            curves.append(phase_curve(point, records, data))
            actual_calls += point["inference_calls"]
            actual_macs += point["inference_dense_MAC"]
            question_evaluations += len(records)
            if phase == 4:
                phase4 = records
            if phase == 5:
                final = records
        require(phase4 is not None and final is not None, "Missing retention endpoint")
        students.append({"seed": seed, "final": final_screen(final, protocol), "phase_curve": curves,
                         "full_echo_phase4_to_phase5": full_echo_retention(phase4, final),
                         "final_test_exposure_subgroups": exposure_subgroups(final, data_by_id)})
    require(evaluation["inference_calls"] == actual_calls and evaluation["inference_dense_MAC"] == actual_macs,
            "Evaluation total cost differs from checkpoint sum")
    require(question_evaluations == evaluation["questions_evaluated"] == 19980, "Evaluation question count differs")
    primary = [training[f"primary_seed{seed}"] for seed in SEEDS]
    replay_training = training["replay_seed101"]
    primary_updates = sum(item["updates"] for item in primary)
    primary_macs = sum(item["train_dense_MAC"] for item in primary)
    require(primary_updates == 605520 and primary_macs == 12749829120, "Actual primary total differs from freeze")
    independent = [independent_report(inputs, path) for path in independent_paths]
    require(len({item["sha256"] for item in independent}) == len(independent),
            "Identical independent report files would double-count the same audit")
    recognized = [item["recognized_cost"] for item in independent if item["recognized_cost"] is not None]
    result = {
        "id": "PRO-AE1-LEARNING-RESULTS-20261113", "status": "completed",
        "actor": "ChatGPT Pro / delegated memory_review; saved-record postprocessing only",
        "created_utc": datetime.now(timezone.utc).isoformat(), "preregistration_commit": commit,
        "profile": data["profile"], "seeds": list(SEEDS), "students": students,
        "all_three_seed_screening_success": all(student["final"]["screening_success"] for student in students),
        "successful_seeds": [student["seed"] for student in students if student["final"]["screening_success"]],
        "criteria_scope": "Frozen integer thresholds apply separately to every seed; all criteria are ANDed. No checkpoint or seed was selected by its score.",
        "question_counts": {"unique_questions": 1110, "unique_train_questions": 750, "unique_test_questions": 360,
                            "unique_N4_test_questions": 240, "unique_N4_test_payload_quartets": 60,
                            "checkpoints_per_seed": 6, "checkpoints_total": 18,
                            "question_evaluations_total": question_evaluations,
                            "train_question_evaluations_total": 750 * 18,
                            "test_question_evaluations_total": 360 * 18,
                            "note": "Checkpoint and seed repetitions are not new independent questions."},
        "negative_controls_from_frozen_data_checks": data_checks["negative_controls"],
        "costs": {"primary_training_updates": primary_updates, "primary_training_dense_MAC": primary_macs,
                  "seed101_replay_updates": replay_training["updates"],
                  "seed101_replay_training_dense_MAC": replay_training["train_dense_MAC"],
                  "training_updates_including_replay": primary_updates + replay_training["updates"],
                  "training_dense_MAC_including_replay": primary_macs + replay_training["train_dense_MAC"],
                  "formal_evaluation_inference_calls": actual_calls,
                  "formal_evaluation_inference_dense_MAC": actual_macs,
                  "independent_review_known_inference_calls": sum(c["inference_calls"] for c in recognized),
                  "independent_review_known_inference_dense_MAC": sum(c["inference_dense_MAC"] for c in recognized),
                  "independent_review_known_optimizer_updates": sum(c["optimizer_updates"] for c in recognized),
                  "unknown_independent_cost_reports": [item["file"] for item in independent if item["recognized_cost"] is None],
                  "postprocess_NN_forward_calls": 0, "postprocess_NN_MAC": 0, "postprocess_optimizer_updates": 0,
                  "primary_trajectory_seconds_sum": sum(item["seconds"] for item in primary),
                  "seed101_replay_seconds": replay_training["seconds"],
                  "formal_evaluation_seconds": evaluation["seconds"],
                  "timing_note": "Trajectory sums and evaluator elapsed time describe these recorded scopes; they are not end-to-end research walltime or a causal efficiency comparison."},
        "training_process_records": training, "replay_verification": replay,
        "independent_reviews": independent,
        "limitations": [
            "One fixed curriculum arm and three seeds do not establish curriculum superiority or research-workflow speedup.",
            "All data use fixedn5 and familiar ordinary IDs. Heldout means untrained complete payload question combinations, not all-role novel content.",
            "Only N4 has count contrasts; N2r1 and N3r1/r2 are outside this run.",
            "TF count-boundary success is a conditional prediction diagnostic, distinct from autonomous whole-answer success.",
            "Only seed101 received full training replay; seed202/303 were not fully retrained for verification.",
            "This exporter recomputes metrics from saved outputs and verifies their file provenance; it does not independently rerun neural inference or inspect checkpoint arrays.",
        ],
        "exporter_sha256": inputs.digest(__file__),
        "verified_frozen_file_count": len(manifest["files_sha256"]) + 1,
    }
    inputs.verify_unchanged()
    result["input_files_sha256"] = inputs.inventory()
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--after-complete", action="store_true",
                        help="Coordinator confirms all primary, replay and evaluation work is complete")
    parser.add_argument("--prereg-commit", required=True)
    parser.add_argument("--independent-review", action="append", default=[], type=Path)
    parser.add_argument("--out", type=Path, default=HERE / "results_summary.json")
    args = parser.parse_args()
    require(args.after_complete, "Do not read performance outputs until completion is explicitly confirmed")
    require(not args.out.exists(), "Refusing to overwrite an existing result export")
    result = export_results(args.prereg_commit, args.independent_review)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "seeds": result["seeds"],
                      "successful_seeds": result["successful_seeds"],
                      "postprocess_NN_forward_calls": 0, "postprocess_optimizer_updates": 0,
                      "output": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
