"""Read-only post-hoc aggregation of the completed feature-transfer study.

No model/codec/trainer imports and no new neural inference, optimizer update,
or source rerun.  Unordered pairs, rather than their repeated opcode/order
variants, are the unit for descriptive paired error comparisons.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
ARMS = ("mature_hidden", "random_hidden", "raw_projection")
SEEDS = (101, 202, 303)
WEIGHTS = np.array([64, 32, 16, 8, 4, 2, 1], dtype=np.int64)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def read_predictions(path):
    with np.load(path, allow_pickle=False) as z:
        result = {key: z[key].copy() for key in ("logits", "targets", "hard_bits", "predicted_answer",
            "complete_correct", "case_ids", "source_op", "a", "b")}
        result["metadata"] = json.loads(str(z["metadata_json"]))
    if not np.array_equal(result["complete_correct"], np.all(result["hard_bits"] == result["targets"], axis=1)):
        raise AssertionError("Saved exact-correct flags disagree with saved hard outputs")
    if not np.array_equal(result["predicted_answer"], result["hard_bits"] @ WEIGHTS):
        raise AssertionError("Saved answer value differs from saved hard bits")
    result["target_answer"] = result["targets"] @ WEIGHTS
    result["source_path"] = str(path.relative_to(ROOT))
    return result


def group_predictions(pred):
    indices = {}
    for i, (a, b) in enumerate(zip(pred["a"], pred["b"])):
        key = tuple(sorted((int(a), int(b))))
        indices.setdefault(key, []).append(i)
    groups = {}
    order_disagreements, order_checks = 0, 0
    opcode_disagreements, ordered_groups = 0, 0
    for pair, local in sorted(indices.items()):
        rows = np.asarray(local, dtype=np.int64)
        expected = 4 if pair[0] == pair[1] else 8
        if len(rows) != expected:
            raise AssertionError("Incomplete within-pair opcode/order variants")
        variants = {(int(pred["a"][i]), int(pred["b"][i]), int(pred["source_op"][i])): i for i in rows}
        if len(variants) != expected:
            raise AssertionError("Duplicate variants")
        directions = [(pair[0], pair[1])] if pair[0] == pair[1] else [(pair[0], pair[1]), (pair[1], pair[0])]
        same_op_prediction = []
        for a, b in directions:
            values = [int(pred["predicted_answer"][variants[(a, b, op)]]) for op in range(4)]
            consistent = len(set(values)) == 1
            same_op_prediction.append(consistent)
            opcode_disagreements += int(not consistent)
            ordered_groups += 1
        swaps = []
        if len(directions) == 2:
            for op in range(4):
                same = pred["predicted_answer"][variants[(pair[0], pair[1], op)]] == pred["predicted_answer"][variants[(pair[1], pair[0], op)]]
                swaps.append(bool(same))
                order_disagreements += int(not same)
                order_checks += 1
        correct = pred["complete_correct"][rows]
        groups[pair] = {"pair": list(pair), "variants": len(rows), "correct_variants": int(correct.sum()),
            "variant_accuracy": float(correct.mean()), "all_variants_correct": bool(correct.all()),
            "any_variant_correct": bool(correct.any()), "all_opcode_predictions_consistent": all(same_op_prediction),
            "all_swapped_predictions_consistent": all(swaps) if swaps else None,
            "source_row_indices": rows.tolist()}
    summary = {"unordered_pairs": len(groups), "equal_pairs": sum(a == b for a, b in groups),
        "non_equal_pairs": sum(a != b for a, b in groups),
        "all_variants_correct_pairs": sum(g["all_variants_correct"] for g in groups.values()),
        "all_variants_correct_pair_accuracy": sum(g["all_variants_correct"] for g in groups.values())/len(groups),
        "mean_within_pair_accuracy_equal_pair_weight": float(np.mean([g["variant_accuracy"] for g in groups.values()])),
        "any_variant_wrong_pairs": sum(not g["all_variants_correct"] for g in groups.values()),
        "ordered_pairs_with_opcode_disagreement": opcode_disagreements,
        "ordered_pairs_checked_for_opcode_consistency": ordered_groups,
        "pair_opcode_swaps_disagree": order_disagreements, "pair_opcode_swaps_checked": order_checks,
        "scope": "Descriptive group-aware summaries; repeated opcode/order variants are not independent pairs or seeds"}
    return groups, summary


def failure_diagnostics(pred):
    wrong = ~pred["complete_correct"]
    bits_wrong = pred["hard_bits"] != pred["targets"]
    smaller = np.minimum(pred["a"], pred["b"])
    return {"failed_frames": int(wrong.sum()), "failed_bits": int(bits_wrong.sum()),
        "wrong_bits_by_value": {str(int(value)): int(bits_wrong[:, i].sum()) for i, value in enumerate(WEIGHTS)},
        "zero_to_one": int(np.sum(bits_wrong & (pred["targets"] == 0))),
        "one_to_zero": int(np.sum(bits_wrong & (pred["targets"] == 1))),
        "wrong_answer_is_smaller_operand": int(np.sum(wrong & (pred["predicted_answer"] == smaller))),
        "wrong_answer_is_neither_operand": int(np.sum(wrong & (pred["predicted_answer"] != pred["a"]) &
                                                       (pred["predicted_answer"] != pred["b"]))) }


def contrast_pairs(a_groups, b_groups, arm_a, arm_b, seed):
    if set(a_groups) != set(b_groups):
        raise AssertionError("Matched models were scored on different unordered test pairs")
    counts = Counter()
    rows = []
    for pair in sorted(a_groups):
        a, b = a_groups[pair], b_groups[pair]
        label = ("both_all_correct" if a["all_variants_correct"] and b["all_variants_correct"] else
                 "a_only_all_correct" if a["all_variants_correct"] else
                 "b_only_all_correct" if b["all_variants_correct"] else "neither_all_correct")
        counts[label] += 1
        rows.append({"pair": list(pair), "a_correct_variants": a["correct_variants"],
            "b_correct_variants": b["correct_variants"], "variants": a["variants"], "category": label})
    return {"seed": seed, "arm_a": arm_a, "arm_b": arm_b, "unordered_pairs": len(a_groups),
        "counts": {name: counts[name] for name in ("both_all_correct", "a_only_all_correct", "b_only_all_correct", "neither_all_correct")},
        "mean_pair_accuracy_a_minus_b": float(np.mean([a_groups[p]["variant_accuracy"]-b_groups[p]["variant_accuracy"] for p in a_groups])),
        "all_variants_pair_accuracy_a_minus_b": (counts["a_only_all_correct"]-counts["b_only_all_correct"])/len(a_groups),
        "pair_rows": rows,
        "not_claimed": "No eight-variants-as-independent binomial test or across-seed significance inference"}


def main():
    outputs = [ROOT/name for name in ("posthoc_analysis.json", "posthoc_test_failures.jsonl", "posthoc_analysis.md")]
    if any(path.exists() for path in outputs):
        raise FileExistsError("Refusing to overwrite a completed post-hoc report")
    result_path, metadata_path = ROOT/"results/summary.json", ROOT/"results/run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source = json.loads(result_path.read_text(encoding="utf-8"))
    if metadata["status"] != "completed" or len(source["models"]) != 9:
        raise ValueError("Run must finish before post-hoc analysis")
    hashes = {str(path.relative_to(ROOT)): sha(path) for path in (result_path, metadata_path)}
    model_summaries, predictions, grouped, contrasts = [], {}, {}, []
    total_failure_rows = 0
    with outputs[1].open("w", encoding="utf-8") as failures:
        for model in source["models"]:
            arm, seed = model["arm"], model["seed"]
            path = ROOT/"results"/arm/f"seed{seed}"/"test_predictions.npz"
            hashes[str(path.relative_to(ROOT))] = sha(path)
            pred = read_predictions(path)
            predictions[(arm, seed)] = pred
            groups, pair_stats = group_predictions(pred)
            if pair_stats["unordered_pairs"] != 396 or pair_stats["equal_pairs"] != 12:
                raise AssertionError("Unexpected test pair groups")
            grouped[(arm, seed)] = groups
            stats = {"arm": arm, "seed": seed,
                "final_train": model["final_train"], "final_validation": model["validation"]["4096"],
                "final_test": model["test"], "first_validation_95": model["first_validation_95"],
                "first_two_consecutive_validation_95_ending_at": model["first_two_consecutive_validation_95_ending_at"],
                "validation_accuracy_auc_by_update": model["validation_accuracy_auc_by_update"],
                "training_minus_test_accuracy": model["final_train"]["complete_accuracy"]-model["test"]["complete_accuracy"],
                "validation_by_checkpoint": model["validation"], "pair_aware_test": pair_stats,
                "test_failure_diagnostics": failure_diagnostics(pred),
                "source_test_predictions": str(path.relative_to(ROOT)), "parameters": model["parameters"],
                "actual_source_readout_audit": model.get("actual_source_readout_audit")}
            model_summaries.append(stats)
            for index in np.flatnonzero(~pred["complete_correct"]):
                i = int(index)
                row = {"arm": arm, "seed": seed, "case_id": str(pred["case_ids"][i]),
                    "unordered_pair": sorted([int(pred["a"][i]), int(pred["b"][i])]),
                    "a": int(pred["a"][i]), "b": int(pred["b"][i]), "source_opcode_class": int(pred["source_op"][i]),
                    "target_max": int(pred["target_answer"][i]), "predicted_max": int(pred["predicted_answer"][i]),
                    "target_bits": "".join(map(str, pred["targets"][i].tolist())),
                    "predicted_bits": "".join(map(str, pred["hard_bits"][i].tolist())),
                    "wrong_bit_values": [int(WEIGHTS[j]) for j in np.flatnonzero(pred["hard_bits"][i] != pred["targets"][i])],
                    "source_predictions": str(path.relative_to(ROOT)), "row_index": i}
                failures.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"))+"\n")
                total_failure_rows += 1
    associations = []
    for seed in SEEDS:
        for arm_a, arm_b in (("mature_hidden", "random_hidden"), ("mature_hidden", "raw_projection"), ("raw_projection", "random_hidden")):
            contrasts.append(contrast_pairs(grouped[(arm_a, seed)], grouped[(arm_b, seed)], arm_a, arm_b, seed))
        source_audit_path = ROOT/"results/mature_hidden"/f"seed{seed}"/"source_test_audit.npz"
        hashes[str(source_audit_path.relative_to(ROOT))] = sha(source_audit_path)
        with np.load(source_audit_path, allow_pickle=False) as z:
            source_correct, source_ids = z["source_tuple_correct"].copy(), z["case_ids"].copy()
        arm_scores = {}
        for arm in ARMS:
            pred = predictions[(arm, seed)]
            if not np.array_equal(pred["case_ids"], source_ids):
                raise AssertionError("Source/head test row alignment changed")
            arm_scores[arm] = {}
            for label, mask in (("source_correct", source_correct), ("source_incorrect", ~source_correct)):
                n = int(mask.sum())
                right = int(pred["complete_correct"][mask].sum())
                arm_scores[arm][label] = {"cases": n, "head_correct": right, "head_accuracy": right/n if n else None}
        associations.append({"seed": seed, "source_cases": len(source_correct),
            "source_tuple_correct": int(source_correct.sum()), "by_arm": arm_scores,
            "scope": "Conditional association on the same saved source predictions; not a causal corruption intervention"})
    aggregate = {}
    for arm in ARMS:
        rows = sorted([m for m in model_summaries if m["arm"] == arm], key=lambda m: m["seed"])
        aggregate[arm] = {"seeds": [m["seed"] for m in rows],
            "train_accuracy": [m["final_train"]["complete_accuracy"] for m in rows],
            "validation_accuracy": [m["final_validation"]["complete_accuracy"] for m in rows],
            "test_accuracy": [m["final_test"]["complete_accuracy"] for m in rows],
            "test_all_variants_pair_accuracy": [m["pair_aware_test"]["all_variants_correct_pair_accuracy"] for m in rows],
            "first_validation95": [m["first_validation_95"] for m in rows],
            "confirmed_validation95": [m["first_two_consecutive_validation_95_ending_at"] for m in rows],
            "validation_auc": [m["validation_accuracy_auc_by_update"] for m in rows]}
    report = {"schema": "feature-transfer-posthoc-analysis-v1", "status": "posthoc_read_only_analysis",
        "new_training_updates": 0, "new_neural_forward_passes": 0, "new_source_inference_rows": 0,
        "new_W_calls": 0, "source_sha256": hashes, "model_results": model_summaries,
        "arm_aggregates": aggregate, "paired_unordered_test_comparisons": contrasts,
        "source_correctness_associations": associations,
        "test_failure_records": {"path": outputs[1].name, "sha256": sha(outputs[1]), "model_variant_failures": total_failure_rows,
            "definition": "Repeated model×seed×opcode/order cases; do not confuse this count with independent unordered pairs"},
        "actual_experiment_costs": metadata,
        "interpretation_boundaries": [
            "The preregistered threshold is validation whole-answer accuracy; no test-selected model, checkpoint, seed, or threshold.",
            "Pair-aware summaries are post-hoc diagnostics, not replacement promotion gates.",
            "Three paired model seeds and396 shared unordered test groups; the8variants of a non-equal pair are dependent.",
            "A mature-versus-random difference supports conditional reuse under this fixed head, not a universal superiority of pretrained features.",
            "Raw has a declared lossless encoding-coordinate prior; all heads have263 trainable parameters but retained source storage differs.",
            "Fit/generalization gaps do not by themselves identify capacity, optimization, or feature information loss as the unique cause.",
            "Source decoder correctness is an observed association; a different new head may use hidden information that the old readout misdecodes.",
            "The new task is a fixed MAX readout, not a new SLE opcode, complete SLE response, learned task routing, or a lifelong-learning result."
        ]}
    dump(outputs[0], report)
    lines = ["# 成熟特徵轉移：事後唯讀分析", "", "新增訓練 0、神經 forward 0、來源推論 0。以下只整理已保存的結果。", "",
        "主要驗收仍看事前定義的 validation whole-answer 指標；不以 test 或事後 pair 指標替換。", "",
        "|條件|Seed|Train 正確|Val 正確|Test 正確|首次 Val95|連續兩點 Val95|Val AUC|全部 variants 都對的無序 pair|",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for model in sorted(model_summaries, key=lambda m: (ARMS.index(m["arm"]), m["seed"])):
        cells = [model["arm"], str(model["seed"])]
        for panel in ("final_train", "final_validation", "final_test"):
            cells.append(f'{model[panel]["complete_correct"]}/{model[panel]["cases"]}')
        cells += [str(model["first_validation_95"]), str(model["first_two_consecutive_validation_95_ending_at"]),
            f'{model["validation_accuracy_auc_by_update"]:.4f}',
            f'{model["pair_aware_test"]["all_variants_correct_pairs"]}/396']
        lines.append("|"+"|".join(cells)+"|")
    lines += ["", "## 無序 pair 的配對錯誤", "",
        "每個非等 pair 的兩個方向、四個 opcode 共八種變體不視為八個獨立 pair。每個 test seed 都是相同 396 個無序 pair，其中 12 組相等。", "",
        "|Seed|A|B|兩者整組全對|僅 A 整組全對|僅 B 整組全對|兩者都非整組全對|", "|---|---|---|---:|---:|---:|---:|"]
    for comparison in contrasts:
        count = comparison["counts"]
        lines.append("|"+"|".join([str(comparison["seed"]), comparison["arm_a"], comparison["arm_b"],
            str(count["both_all_correct"]), str(count["a_only_all_correct"]), str(count["b_only_all_correct"]),
            str(count["neither_all_correct"])])+"|")
    lines += ["", "各 opcode、方向、tie、交換一致性、錯 bit 分布與來源 decoder 正確性條件關聯，完整保留於 JSON。全部 test 錯例逐列保存，並附原 NPZ 與 row index。", "",
        "## 可支持的判讀範圍", "",
        "成熟與隨機組的配對差異可以回答：在已存在該來源銀行、相同 263 參數新 head 與固定教材預算下，成熟表徵是否有額外幫助。raw 組具有明示的保資訊編碼座標先驗，需同時報告，不能只挑成熟對隨機的有利對照。", "",
        "Train 與 heldout 分數可辨認是否明顯只記住訓練題；即使 train 本身也低，仍不能僅憑這一輪就把原因唯一歸給 head 容量、最佳化或表徵壓縮。下一個測試應事前固定、另用乾淨保留資料，不回頭挑這輪最有利 seed/checkpoint。", "",
        "這不是新的正式 MAX 算符、完整 SLE 管線或自主終身成長成果。", ""]
    outputs[2].write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "completed_posthoc", "model_results": len(model_summaries),
        "test_unordered_pairs_per_model": 396, "test_model_variant_failures": total_failure_rows,
        "new_training_updates": 0, "new_neural_forward_passes": 0}))


if __name__ == "__main__":
    main()
