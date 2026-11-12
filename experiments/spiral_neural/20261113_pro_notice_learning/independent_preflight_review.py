"""Independent arithmetic/data/adapter checks; never runs formal training."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import dataset
import learner
import numpy as np

HERE = Path(__file__).resolve().parent
EXPECTED_PATHS = ((0,), (1,), (2,), (5, 0), (5, 1), (5, 5, 0))
EXPECTED_HELD = (4, 5, 6, 4, 6, 5)
REVIEWED_RUNNER_SHA = "4b6e70445a75c206b1bc61acfc1183a866a932f6e528b656e917345fef5e09cb"


def require(condition, description):
    if not condition:
        raise AssertionError(description)


def prefix_set(rows):
    return {row["Q"] + row["A"][:i] for row in rows for i in range(len(row["A"]) + 1)}


class ScriptedForward:
    """A non-neural test double checks the generation loop's actual arguments."""
    L = 80

    def __init__(self, sequence):
        self.sequence, self.prefixes = sequence, []

    def forward(self, prefix):
        token = self.sequence[min(len(self.prefixes), len(self.sequence) - 1)]
        self.prefixes.append(prefix)
        logits = np.full(3, -10, dtype=np.float32)
        logits["01S".index(token)] = 10
        return None, None, logits


def review():
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    rows = dataset.make_rows()
    require(len(rows) == 18, "18 complete cases")
    require(protocol["paths"] == [list(path) for path in EXPECTED_PATHS], "six specified addresses")
    require(protocol["heldout_width_by_path"] == list(EXPECTED_HELD), "specified holdout vector")
    require(protocol["target_widths"] == [4, 5, 6], "three specified widths")
    require(protocol["seeds"] == [101, 202, 303] and protocol["epochs"] == 128, "fixed seeds and epochs")
    by_pair = {(tuple(row["path"]), row["target_n"]): row for row in rows}
    require(len(by_pair) == 18, "unique address/width pairs")
    for path, held in zip(EXPECTED_PATHS, EXPECTED_HELD, strict=True):
        # Reconstruct directly from the published bit rule, without codec helpers.
        address = format(len(path), "03b") + "0"
        address += "".join(format(child, "03b") + "0" for child in path)
        for width in (4, 5, 6):
            row = by_pair[path, width]
            up, end = "1" * width + "0", "1" * (width - 1) + "00"
            require(row["Q"] == "00111100" + address + up * 3 + end, "Q exact bit construction")
            require(row["A"] == address + up, "A exact bit construction")
            require(row["split"] == ("heldout" if width == held else "train"), "split by frozen pair")
            require((row["k"], row["current_n"]) == (1, width - 1), "independent legal pre-event profile")
            require(row["highwater"] < (1 << (width - 1)) - (2 if row["role"] in ("operator", "control") else 0),
                    "old width accommodates branch highwater")

    train = [row for row in rows if row["split"] == "train"]
    heldout = [row for row in rows if row["split"] == "heldout"]
    require((len(train), len(heldout)) == (12, 6), "12 train and 6 heldout")
    require(len({row["Q"] for row in rows}) == len({row["A"] for row in rows}) == 18,
            "complete questions and answers individually unique")
    train_prefixes, heldout_prefixes = prefix_set(train), prefix_set(heldout)
    require(not train_prefixes.intersection(heldout_prefixes), "no heldout target prefix occurs in training")
    require({row["address_bits"] for row in train} == {row["address_bits"] for row in rows}, "all addresses seen")
    for field in ("up_bits", "end_bits"):
        require({row[field] for row in train} == {row[field] for row in rows}, f"all {field} seen")

    L, H, cap, epochs, seeds = 80, 64, 24, 128, 3
    epoch_targets = sum(len(row["A"]) + 1 for row in train)
    mac_per_target = H * (4 * L + 9)
    per_seed_targets = epoch_targets * epochs
    expected_costs = {
        "targets_per_epoch": epoch_targets,
        "targets_per_seed": per_seed_targets,
        "lessons_per_seed": len(train) * epochs,
        "training_dense_MAC_per_target": mac_per_target,
        "training_dense_MAC_per_seed": per_seed_targets * mac_per_target,
        "primary_targets_all_seeds": per_seed_targets * seeds,
        "primary_training_dense_MAC_all_seeds": per_seed_targets * seeds * mac_per_target,
        "including_replay_targets": per_seed_targets * seeds * 2,
        "including_replay_training_dense_MAC": per_seed_targets * seeds * mac_per_target * 2,
    }
    for key, value in expected_costs.items():
        require(protocol[key] == value, f"protocol cost {key}")
    require(epoch_targets == 212, "independently derived 212 targets/epoch")
    parameters = H * (2 * L + 4) + 3
    require(protocol["model"] == {"L": L, "H": H, "parameters": parameters,
                                 "generation_cap_including_STOP": cap}, "model configuration")
    model = learner.new_student(999003)  # Untrained engineering instance; never calls step/lesson.
    array_bytes = sum(array.nbytes for group in (model.p, model.m, model.v, model.birth) for array in group)
    require(model.parameters == parameters == 10499 and array_bytes == 209980, "actual parameter/array counts")
    require(model.t == model.train_macs == 0, "zero engineering training updates")

    max_q = max(len(row["Q"]) for row in rows)
    max_a = max(len(row["A"]) for row in rows)
    max_prefix = max(len(row["Q"] + row["A"]) for row in rows)
    require((max_q, max_a, max_prefix) == (52, 23, 75), "maximum Q/A/prefix")
    require(max(len(row["Q"] + row["A"]) for row in train) == max_prefix, "maximum length occurs in train")
    require(max_q + cap - 1 <= L and max_a + 1 <= cap, "correct and incorrect generation fit the context")

    q = max(rows, key=lambda row: len(row["Q"]))["Q"]
    scripted = ScriptedForward("10S")
    generated = learner.generate(scripted, q)
    require(generated["tokens"] == "10S" and scripted.prefixes == [q, q + "1", q + "10"],
            "each generation step uses its own preceding prediction")
    never_stop = ScriptedForward("0")
    exhausted = learner.generate(never_stop, q)
    require(exhausted["tokens"] == "0" * 24 and exhausted["cap_exhausted"] and not exhausted["overflow"],
            "cap24 does not force an oracle STOP")
    overflow = ScriptedForward("0")
    result = learner.generate(overflow, "0" * 80)
    require(result["overflow"] and result["tokens"] == "0" and len(overflow.prefixes) == 1,
            "overflow is detected before forwarding an oversized prefix")

    width_exposure = []
    for width in (4, 5, 6):
        subset = [row for row in train if row["target_n"] == width]
        lessons = len(subset) * epochs
        optimizer_prefixes = sum(len(row["A"]) + 1 for row in subset) * epochs
        width_exposure.append({"target_n": width, "train_combinations": len(subset),
                               "lessons_per_seed": lessons,
                               "optimizer_prefixes_per_seed": optimizer_prefixes,
                               "question_UP_role_words_per_seed_at_lesson_level": 3 * lessons,
                               "question_END_role_words_per_seed_at_lesson_level": lessons,
                               "answer_UP_role_words_per_seed_at_lesson_level": lessons,
                               "question_UP_role_words_across_optimizer_prefixes_per_seed": 3 * optimizer_prefixes})
    require(protocol["targets_per_epoch_by_width"] == {"4": 68, "5": 68, "6": 76}, "documented unequal width exposure")
    require(dataset.file_sha(HERE / "run_trial.py") == REVIEWED_RUNNER_SHA, "runner matches the independently inspected revision")
    optimized = subprocess.run([sys.executable, "-B", "-O", str(HERE / "run_trial.py"), "--help"],
                               capture_output=True, text=True, timeout=10)
    require(optimized.returncode != 0 and "Optimized Python (-O/-OO) is disabled" in optimized.stderr,
            "optimized Python is rejected before argument handling or training")
    return {
        "passed": True,
        "author": "ChatGPT Pro / independent delegated preflight review",
        "scope": "Independent preflight only: exact bit rules, split/prefix separation, costs, exposure, model size, generation adapter.",
        "training_updates": 0, "formal_students_executed": 0, "heldout_neural_scores_computed": 0,
        "engineering_model_instances_initialized_without_training": 1,
        "non_neural_generation_fixture_forward_calls": sum(len(net.prefixes) for net in (scripted, never_stop, overflow)),
        "dataset_sha256": dataset.json_sha(rows),
        "cases": {"total": len(rows), "train": len(train), "heldout": len(heldout),
                  "train_target_prefixes": len(train_prefixes), "heldout_target_prefixes": len(heldout_prefixes),
                  "train_heldout_prefix_overlap": 0,
                  "path_train_counts": {str(path): sum(tuple(row["path"]) == path for row in train) for path in EXPECTED_PATHS},
                  "heldout_width_counts": dict(Counter(row["target_n"] for row in heldout))},
        "lengths": {"max_Q": max_q, "max_A": max_a, "max_Q_plus_A": max_prefix,
                    "max_generation_prefix_even_without_STOP": max_q + cap - 1,
                    "max_generation_actions_including_STOP": max_a + 1,
                    "longest_case_in_train": True},
        "model": {"parameters": parameters, "parameter_moment_birth_array_bytes": array_bytes},
        "costs": expected_costs,
        "width_exposure_per_seed": width_exposure,
        "generation_checks": {"own_prefix_only": True, "no_forced_STOP": True, "overflow_guard": True},
        "driver_static_review": {
            "method": "Source inspection pinned to the exact runner SHA; no formal execution invoked.",
            "runner_sha256": REVIEWED_RUNNER_SHA,
            "optimizer_row_lookup_contains_only_train": True,
            "all_three_primary_and_three_replays_finish_before_heldout": True,
            "offline_checkpoints_per_seed": [0, 16, 32, 64, 96, 128],
            "offline_examples_per_checkpoint": 18,
            "final_metrics_reuse_epoch_128": True,
            "offline_inference_cost_is_separate_and_final_subset_not_added_twice": True,
            "native_lesson_vs_target_loop_checks_actual_prefix_target_and_full_state": True,
            "manifest_source_data_curriculum_runtime_checked_before_execution": True,
            "existing_output_directory_and_files_cannot_be_overwritten": True,
        },
        "optimized_mode_guard": {"command": "python -B -O run_trial.py --help",
                                 "exit_code": optimized.returncode,
                                 "rejected_before_training": True},
        "limitations": [
            "Only legal k=1 notices are used; no malformed-frame or ordinary-frame classification claim.",
            "The target width can also be inferred from Q length and address depth; ACK success does not establish control semantics.",
            "All widths have equal lesson counts, but m=6 has more optimizer-prefix exposure because answers are longer.",
            "No ordinary mathematics, position-specific adaptation, persistent profile state, or semantic growth is tested.",
            "Formal driver policy is a pinned static review; this script never invokes execution or preflight runner commands.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "independent_preflight_review.json")
    args = parser.parse_args()
    try:
        report = review()
    except Exception as error:
        report = {"passed": False, "error": type(error).__name__, "detail": str(error),
                  "formal_students_executed": 0}
    report["command"] = "python -B independent_preflight_review.py --out independent_preflight_review.json"
    report["python_version"] = platform.python_version()
    report["source_sha256"] = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                for name in ("dataset.py", "learner.py", "run_trial.py", "test_engineering.py", "protocol.json", "independent_preflight_review.py")}
    report["human_spec_sha256"] = dataset.file_sha(dataset.REPO / "docs/ai_orchestration/PRO_NOTICE_LEARNING_PROTOCOL_20261113.md")
    report["dependency_sha256"] = {"UR1_codec": dataset.file_sha(dataset.CODEC_PATH),
                                    "P030_reference": dataset.file_sha(learner.REFERENCE_PATH)}
    report["nvidia"] = {"status": "skipped_unavailable", "calls": 0}
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("passed", "costs", "lengths", "error", "detail") if key in report}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
