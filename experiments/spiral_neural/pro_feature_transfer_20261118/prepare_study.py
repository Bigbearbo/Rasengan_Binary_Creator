"""Prepare a self-contained, zero-update feature-transfer study.

Copies immutable source checkpoints and split evidence, creates a fresh
unordered-pair split, feature banks, paired batch streams, and preregistration.
It never evaluates a source network or trains a new head.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np

ROOT = Path(__file__).resolve().parent
PR130 = ROOT.parent/"growth_channel_20261117"
SEEDS = (101, 202, 303)
ARMS = ("mature_hidden", "random_hidden", "raw_projection")
DATA_SEED = 2026111801
PROJECTION_SEED = 2026111802


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def main():
    for name in ("data.json", "protocol.json", "source_manifest.json", "projection_receipt.json"):
        if (ROOT/name).exists():
            raise FileExistsError("Refusing to overwrite "+name)
    (ROOT/"sources").mkdir(exist_ok=True)
    (ROOT/"banks").mkdir(exist_ok=True)
    (ROOT/"batches").mkdir(exist_ok=True)
    copies = {
        "codec.py": "sources/codec.py",
        "neural_growth.py": "sources/neural_growth.py",
        "data.json": "sources/pr130_data.json",
        "protocol.json": "sources/pr130_protocol.json",
        "source_lock.json": "sources/pr130_source_lock.json",
        "results/run_metadata.json": "sources/pr130_run_metadata.json",
        "parents/data.json": "sources/pr129_data.json",
    }
    for seed in SEEDS:
        copies[f"results/demand/receiver_seed{seed}/checkpoints/step_4096.npz"] = f"sources/receiver_seed{seed}.npz"
        copies[f"parents/receiver_seed{seed}.npz"] = f"sources/parent_receiver_seed{seed}.npz"
    provenance = []
    for original, copied in copies.items():
        destination = ROOT/copied
        if destination.exists():
            raise FileExistsError(destination)
        shutil.copy2(PR130/original, destination)
        provenance.append({"path": copied, "sha256": sha(destination), "size_bytes": destination.stat().st_size,
                           "original_study": "growth_channel_20261117", "original_path": original})
    prior = json.loads((ROOT/"sources/pr130_data.json").read_text(encoding="utf-8"))
    unused = set(map(tuple, prior["new_pair_splits"]["unused"]))
    closed = {(a, b) for a, b in unused if (b, a) in unused}
    groups = sorted({tuple(sorted(pair)) for pair in closed})
    unequal = [pair for pair in groups if pair[0] != pair[1]]
    equal = [pair for pair in groups if pair[0] == pair[1]]
    if (len(unused), len(closed), len(unequal), len(equal)) != (5168, 3598, 1781, 36):
        raise AssertionError("Unexpected untouched source pool")
    excluded = set()
    for collection in ("old_pair_splits", "new_pair_splits"):
        for split in ("train", "val", "test"):
            excluded.update(tuple(sorted(pair)) for pair in prior[collection][split])
    if set(groups) & excluded:
        raise AssertionError("A fresh unordered group was exposed to the source")
    rng = np.random.default_rng(DATA_SEED)
    unequal = [unequal[int(i)] for i in rng.permutation(len(unequal))]
    equal = [equal[int(i)] for i in rng.permutation(len(equal))]
    group_splits = {"train": unequal[:1024]+equal[:12],
                    "val": unequal[1024:1280]+equal[12:24],
                    "test": unequal[1280:1664]+equal[24:],
                    "unused": unequal[1664:]}
    # Import the byte-identical original codec only after copying it locally.
    from sources.codec import make_row
    panels = {}
    for split in ("train", "val", "test"):
        rows = []
        for lo, hi in group_splits[split]:
            directions = [(lo, hi)] if lo == hi else [(lo, hi), (hi, lo)]
            for a, b in directions:
                for op in range(4):
                    row = make_row(op, a, b, 7)
                    # The original source operation stays intact in the frame.
                    # MAX is the fixed experiment head, not a changed opcode.
                    row["source_operation_answer"] = row.pop("answer")
                    row["max_answer"] = max(a, b)
                    row["target_bits"] = format(max(a, b), "07b")
                    row["unordered_pair"] = [lo, hi]
                    rows.append(row)
        panels[split] = rows
    if {key: len(value) for key, value in panels.items()} != {"train": 8240, "val": 2096, "test": 3120}:
        raise AssertionError("Unexpected fresh panel counts")
    dataset = {"schema": "feature-transfer-max-dataset-v1", "source_profile": prior["profile"],
        "data_seed": DATA_SEED, "scope": "Fixed MAX readout on existing valid n7 frames; opcodes are nuisance factors, not redefined",
        "source_exclusion": "Both orderings are in PR130 unused. No unordered group occurs in source old/new train, val or test.",
        "group_splits": {key: [list(pair) for pair in value] for key, value in group_splits.items()},
        "panels": panels, "panel_counts": {key: len(value) for key, value in panels.items()},
        "pool_counts": {"source_unused_ordered": len(unused), "both_orders_unused": len(closed),
            "eligible_unequal_groups": 1781, "eligible_equal_groups": 36, "retained_unused_unequal_groups": 117},
        "source_data_sha256": sha(ROOT/"sources/pr130_data.json")}
    dump(ROOT/"data.json", dataset)

    train_x = np.asarray([[int(bit) for bit in row["frame_bits"]] for row in panels["train"]], dtype=np.float64)
    variable = np.flatnonzero(train_x.min(axis=0) != train_x.max(axis=0))
    expected = np.array([13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31, 32])
    if not np.array_equal(variable, expected):
        raise AssertionError("Training input variation differs from the fixed n7 profile")
    projection_rng = np.random.default_rng(PROJECTION_SEED)
    q, r = np.linalg.qr(projection_rng.normal(size=(24, 24)))
    # Fix otherwise arbitrary QR column signs so the stored construction has
    # one explicit convention.  The saved matrix is the replay authority.
    signs = np.where(np.diag(r) < 0, -1.0, 1.0)
    q = q*signs[None, :]
    basis = q[:len(variable), :]
    projection = np.zeros((34, 24), dtype=np.float64)
    projection[variable] = basis
    bias = -.5*basis.sum(axis=0)
    singular = np.linalg.svd(basis, compute_uv=False)
    gram_delta = float(np.max(np.abs(basis @ basis.T-np.eye(18))))
    if gram_delta > 1e-12 or not np.allclose(singular, 1, atol=1e-12, rtol=0):
        raise AssertionError("Raw projection is not isometric on its variable-coordinate subspace")
    np.savez_compressed(ROOT/"banks/raw_projection.npz", W1=projection, b1=bias,
        variable_positions=variable,
        metadata_json=np.array(json.dumps({"schema": "feature-bank-v1", "kind": "raw_projection",
            "seed": PROJECTION_SEED, "shape": [34, 24], "activation": "identity"}, sort_keys=True)))
    projection_receipt = {"variable_zero_based_positions": variable.tolist(), "variable_coordinates": 18,
        "constant_coordinates": 16, "matrix_shape": [34, 24], "stored_values_including_bias": 840,
        "matrix_nonzero_values": int(np.count_nonzero(projection)), "bias_nonzero_values": int(np.count_nonzero(bias)),
        "rank_on_variable_coordinate_subspace": int(np.linalg.matrix_rank(basis)),
        "singular_values": singular.tolist(), "condition_number": float(singular.max()/singular.min()),
        "max_row_gram_identity_error": gram_delta, "projection_seed": PROJECTION_SEED,
        "normalization_note": "A training-only mean vector and one common scalar preserve condition number 1. Per-feature scaling is forbidden.",
        "prior_note": "Constant-coordinate removal uses unlabeled train frame variation and the declared fixed n7 layout; no operand values are parsed or provided to the head.",
        "not_claimed": "18 varying coordinates do not mean four legal opcodes contain four independent bits of information."}
    dump(ROOT/"projection_receipt.json", projection_receipt)
    for seed in SEEDS:
        bank_rng = np.random.default_rng(1800000+seed)
        weights = bank_rng.normal(0, np.sqrt(2/(34+24)), size=(34, 24))
        np.savez_compressed(ROOT/"banks"/f"random_seed{seed}.npz", W1=weights, b1=np.zeros(24),
            metadata_json=np.array(json.dumps({"schema": "feature-bank-v1", "kind": "random_hidden",
                "seed": 1800000+seed, "shape": [34, 24], "activation": "tanh"}, sort_keys=True)))
        batch_rng = np.random.default_rng(2000000+seed)
        indices = batch_rng.integers(0, len(panels["train"]), size=(4096, 128))
        np.savez_compressed(ROOT/"batches"/f"seed{seed}.npz", indices=indices.astype(np.uint32),
            metadata_json=np.array(json.dumps({"seed": 2000000+seed, "shape": [4096, 128],
                "dtype_at_draw": "int64", "storage_dtype": "uint32", "paired_across_all_arms": True}, sort_keys=True)))
    spec = {
        "schema": "feature-transfer-preregistration-v1", "run": "pro_feature_transfer_20261118_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "question": "Does a small new MAX head learn more efficiently from a mature raw-frame receiver's actual hidden computation than from fixed random nonlinear features or an information-preserving raw projection?",
        "provenance": {"U": "User mature-network reuse, growing small branches, and permitted temporary regression/recovery concepts",
            "F": "Existing PR130 demand receivers and original Fable W candidate frame profile; PR131 identified missing lateral reuse but is not rerun",
            "A": "This fixed MAX readout, three equal-head feature conditions, fresh unordered split and accounting",
            "T": "No experimental training or model inference at preparation; actual execution receipts follow separately"},
        "source": {"study": "PR130", "head_commit": "c35ff7d13ae427fc2ed6c5959665d121edd6bf50",
            "archive_sha256": "a908a726571d5337cefe71dd193256e656bde8f729a181cf57109d2c93e5b579",
            "arm": "demand", "role": "receiver", "seeds": list(SEEDS), "shape": [34, 24, 18],
            "full_parameters_per_source": 1290, "active_encoder_parameters": 840, "retained_readout_parameters": 450,
            "source_split_evidence": ["sources/pr130_data.json", "sources/pr129_data.json"],
            "inherited_updates_per_source_lineage": 5120, "inherited_presentations_per_source_lineage": 655360,
            "new_source_updates": 0, "new_source_pretraining": False,
            "frozen_reason": "Causal feature-bank control only; not a claim that future adaptation must freeze the parent or never regress"},
        "task": {"name": "fixed_MAX_readout", "target": "max(a,b), 7 binary bits", "input": "Actual source-profile n7 frame,34rawbits; Fable W candidate,not formal canonical SLE",
            "source_opcodes": {"ADD": 12, "XOR": 9, "AND": 7, "OR": 8},
            "opcode_role": "Nuisance variation for this fixed MAX head; original operation meanings remain unchanged",
            "external_task_identity": "Experiment caller selects the MAX readout; no learned new-opcode detection or task router",
            "output_scope": "Seven answer bits, not a complete canonical SLE response or a newly assigned formal MAX opcode",
            "teacher_scope": "True operands generate supervised MAX labels only. No true operands, MAX answers, source-oracle answers, or test outcomes enter feature inputs.",
            "source_output_scope": "Mature hidden activations are actual frozen-model computations. Full source predictions may be audited after all training; they are not replaced by truth or fed as MAX labels."},
        "data": {"data_seed": DATA_SEED, "counts": dataset["panel_counts"], "pool_counts": dataset["pool_counts"],
            "split_rule": "Sort unordered groups, permute unequal groups then ties using one RNG. Non-equal groups: 1024train/256val/384test/117unused; ties12/12/12. Expand both directions when unequal and all4opcodes within the same split.",
            "exclusions": "Both directions must be in source unused; exclude all source old/new train,val,test unordered groups, including source growth-selection validation.",
            "new_test_features": "No test feature generation, source prediction, normalization fitting, or head prediction until all nine heads have completed all4096updates.",
            "benchmark_scope": "Fresh held semantic pairs within the bounded n7 source domain, including both operand orders and held ties; not unbounded arithmetic or unseen numeric vocabulary."},
        "features": {"dimension": 24, "arms": {
            "mature_hidden": "tanh(raw34 @ source.W1 + source.b1), using actual PR130 weights",
            "random_hidden": "Same34to24tanh architecture, fixed Xavier-normal W1 andzero b1; seed1800000+seed",
            "raw_projection": "Fixed34x24 affine map;18 variable rows form an orthonormal basis,constant rowszero. Preserves all input differences in the variable-coordinate subspace. StoredP,bias authoritative."},
            "normalization": "For each arm/seed, fit mean24 on train features, then one global RMS scalar sqrt(mean((f-mean)^2)), floor1e-8. Val/test use frozen train statistics.25fixednumbers. Raw singular values shareone common rescaling,condition1 maintained.",
            "raw_projection_seed": PROJECTION_SEED, "raw_projection_prior": projection_receipt["prior_note"],
            "no_bypass": True, "feature_banks_fixed": True,
            "cache": "Compute and save train/validation features once per arm/seed; test only after all training. Count actual feature rows and cache storage, plus per-query deployment feature cost."},
        "head": {"shape": [24, 8, 7], "activation": "tanh", "trainable_parameters": 263,
            "initialization": "Paired per seed across all arms: seed1900000+seed; W1normalstdsqrt(2/32), W2normalstdsqrt(2/15), zero biases",
            "output": "Seven logits threshold>=0; primary correctness requires all seven bits correct",
            "architecture_search": "None; H8 fixed, no adaptive growth, no H sweep"},
        "training": {"models": 9, "seeds": list(SEEDS), "arms": list(ARMS), "updates_per_model": 4096,
            "batch_size": 128, "batch_seed_offset": 2000000, "batch_rule": "Same saved4096x128indices per seed across all arms; replacement sampling from fresh train frames",
            "loss": "Mean binary cross entropy over all seven output bits and all rows",
            "optimizer": "Adam arithmetic reused from PR130", "lr": .01, "beta1": .9, "beta2": .999,
            "eps": 1e-8, "clip_global_norm": 5.0, "optimizer_resets": "At initialization only",
            "checkpoints": [0, 16, 64, 128, 256, 512, 1024, 2048, 4096],
            "actual_updates_budget": 36864, "presentations_budget": 4718592,
            "stopping": "Always4096, regardless of95threshold, regressions, or poor scores. No reseeding, test-tuned repair, or curriculum adjustment.",
            "execution": "One automated loop; source-lock check before and after; no LLM choices inside updates"},
        "metrics": {"primary": "Validation exact seven-bit MAX accuracy by seed/checkpoint; first observed95%; first checkpoint ending two consecutive observed evaluations>=95%; final fresh test exactaccuracy",
            "secondary": "AUC of validation exactaccuracy over update count using trapezoids at fixed checkpoints; opcode/operand-order/tie strata; copy-a/copy-b baselines; all errors retained; one final all-train exactaccuracy evaluation after all9headsfinish using cached trainfeatures, never a continuation criterion",
            "threshold_note": "95% markers do not stop or promote based on test. Missing crossing remains null; continuous safety or every-update monotonicity not required.",
            "source_audit": "After all training, decode mature source on fresh test from actual cached hidden and retained readout; report source tuple correctness and head errors by source correctness. No truth substitution.",
            "comparison_claim": "Matched new-head capacity and data; full-system storage differs because mature source retains its original450parameter readout. Conditional additional learning efficiency, not training-from-scratch total cost superiority."},
        "accounting": {"head_parameters": 263, "bank_active_parameters_each": 840, "normalizer_values_each": 25,
            "active_inference_values_each": 1128, "mature_full_source_plus_head_normalizer_values": 1578,
            "raw_random_bank_plus_head_normalizer_values": 1128,
            "head_forward_dense_mac_per_row": 248, "bank_forward_dense_mac_per_row": 816,
            "new_head_forward_training_mac_budget": 1170210816,
            "final_train_head_forward_rows_budget": 74160, "final_train_head_forward_mac_budget": 18391680,
            "dense_note": "Raw zero rows are stored and still counted by the dense implementation; rawP432nonzero+bias24. Tanh,normalization,backprop,Adam,evaluation,IO excluded from dense MAC and reported separately.",
            "inherited_lineage_updates_total": 15360, "inherited_lineage_presentations_total": 1966080,
            "inherited_search_cost_note": "These are the chosen source lineages only, not all historical project experiments."},
        "constraints": ["No changes to source artifacts or other experiments", "No test exposure before all9trainingrunsfinish",
            "No complete SLE pipeline claim", "No learned arithmetic source oracle", "No lifelong learning/free-parent recovery claim",
            "No guarantee of 95% success", "All failure cases and temporary regressions retained"],
        "workers": {"nvidia_status": "skipped_unavailable", "nvidia_actual_calls": 0,
            "reason": "Root verified no callable NVIDIA/OpenRouter tools and no configured NVIDIA_API_KEY/OPENROUTER_API_KEY; independent local method review instead",
            "external_teacher_calls": 0}
    }
    dump(ROOT/"protocol.json", spec)
    manifest = {"schema": "feature-transfer-source-manifest-v1", "copied_sources": provenance,
        "generated_files": {str(p.relative_to(ROOT)): {"sha256": sha(p), "size_bytes": p.stat().st_size}
            for p in [ROOT/"data.json", ROOT/"protocol.json", ROOT/"projection_receipt.json",
                      *sorted((ROOT/"banks").glob("*.npz")), *sorted((ROOT/"batches").glob("*.npz"))]},
        "preparation_training_updates": 0, "preparation_neural_forward_rows": 0}
    dump(ROOT/"source_manifest.json", manifest)
    print(json.dumps({"status": "prepared_not_trained", "counts": dataset["panel_counts"],
        "projection_rank": 18, "projection_condition": projection_receipt["condition_number"],
        "new_training_updates": 0, "neural_forward_rows": 0}))


if __name__ == "__main__":
    main()
