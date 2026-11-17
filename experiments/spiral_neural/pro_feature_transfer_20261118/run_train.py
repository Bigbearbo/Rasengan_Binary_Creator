"""One automated, fixed-budget feature-transfer study with a test barrier.

All nine heads finish before any fresh test feature or prediction is computed.
Source encoders remain fixed; only the 263-parameter new head is optimized.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
from feature_model import (ARMS, PARAMETER_KEYS, load_bank, extract_features,
    fit_normalizer, normalize, init_head, forward, loss_output_grad, loss_grads,
    optimizer_state, adam_step, source_readout, save_checkpoint, load_checkpoint)

ROOT = Path(__file__).resolve().parent
SEEDS = (101, 202, 303)
UPDATES = 4096
CHECKPOINTS = (0, 16, 64, 128, 256, 512, 1024, 2048, 4096)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def params_digest(params):
    digest = hashlib.sha256()
    for key in PARAMETER_KEYS:
        digest.update(key.encode())
        digest.update(str(params[key].shape).encode())
        digest.update(params[key].astype("<f8", copy=False).tobytes(order="C"))
    return digest.hexdigest()


def verify_lock(path):
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = lock.get("source_sha256", {})
    required = {"run_train.py", "feature_model.py", "protocol.json", "data.json", "sources/neural_growth.py",
        "source_manifest.json", "banks/raw_projection.npz"}
    required.update(f"sources/receiver_seed{seed}.npz" for seed in SEEDS)
    required.update(f"banks/random_seed{seed}.npz" for seed in SEEDS)
    required.update(f"batches/seed{seed}.npz" for seed in SEEDS)
    if not required <= set(expected):
        raise ValueError("Source lock missing mandatory inputs")
    actual = {}
    for name, wanted in expected.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Source-lock path must remain inside the study")
        actual[name] = sha(ROOT/relative)
        if actual[name] != wanted:
            raise ValueError("Locked file changed: "+name)
    return actual


def arrays(rows):
    x = np.array([[int(v) for v in row["frame_bits"]] for row in rows], dtype=np.float64)
    y = np.array([[int(v) for v in row["target_bits"]] for row in rows], dtype=np.float64)
    if x.shape != (len(rows), 34) or y.shape != (len(rows), 7):
        raise ValueError("Bad fixed-profile row shapes")
    return x, y


def metrics(logits, target, rows):
    hard = (logits >= 0).astype(np.uint8)
    exact = np.all(hard == target, axis=1)
    answer = hard @ np.array([64, 32, 16, 8, 4, 2, 1], dtype=np.int64)
    strata = {}
    for name, selected in [(f"opcode_{op}", np.array([r["op"] == op for r in rows])) for op in range(4)]+[
        ("a_lt_b", np.array([r["a"] < r["b"] for r in rows])),
        ("a_gt_b", np.array([r["a"] > r["b"] for r in rows])),
        ("a_eq_b", np.array([r["a"] == r["b"] for r in rows]))]:
        count = int(selected.sum())
        strata[name] = {"cases": count, "correct": int(exact[selected].sum()),
                        "accuracy": float(exact[selected].mean()) if count else None}
    result = {"cases": len(rows), "complete_correct": int(exact.sum()), "complete_accuracy": float(exact.mean()),
        "bit_accuracy_diagnostic": float(np.mean(hard == target)), "loss": loss_output_grad(logits, target)[0],
        "strata": strata, "copy_a_baseline": sum(r["a"] == r["max_answer"] for r in rows)/len(rows),
        "copy_b_baseline": sum(r["b"] == r["max_answer"] for r in rows)/len(rows)}
    return result, hard, answer, exact


def save_prediction(path, logits, target, rows, arm, seed, step, panel):
    result, hard, answer, exact = metrics(logits, target, rows)
    np.savez_compressed(path, logits=logits, targets=target.astype(np.uint8), hard_bits=hard,
        predicted_answer=answer, complete_correct=exact,
        case_ids=np.asarray([r["case_id"] for r in rows]),
        source_op=np.asarray([r["op"] for r in rows], dtype=np.uint8),
        a=np.asarray([r["a"] for r in rows], dtype=np.uint8), b=np.asarray([r["b"] for r in rows], dtype=np.uint8),
        metadata_json=np.array(json.dumps({"schema": "feature-transfer-predictions-v1", "arm": arm,
            "seed": seed, "step": step, "panel": panel, "metrics": result}, sort_keys=True)))
    return result


def save_feature_cache(path, raw_features, normalized, rows, bank, norm, panel):
    metadata = {"schema": "feature-transfer-cache-v1", "panel": panel,
        "bank_path": str(bank["path"].relative_to(ROOT)), "bank_sha256": sha(bank["path"]),
        "arm": bank["arm"], "seed": bank["seed"], "feature_rows": len(rows),
        "normalizer_fit_panel": "train", "normalizer_fit_rows": norm["fit_rows"], "normalizer_fixed_values": 25}
    np.savez_compressed(path, raw_features=raw_features, normalized_features=normalized,
        case_ids=np.asarray([r["case_id"] for r in rows]), metadata_json=np.array(json.dumps(metadata, sort_keys=True)))


def parameter_account(bank):
    mature = bank["arm"] == "mature_hidden"
    return {"new_head_trainable_parameters": 263, "active_feature_bank_parameters": 840,
        "feature_bank_nonzero_values": int(np.count_nonzero(bank["W1"])+np.count_nonzero(bank["b1"])),
        "normalizer_fixed_values": 25, "active_inference_values": 1128,
        "retained_source_readout_parameters": 450 if mature else 0,
        "retained_model_values_excluding_optimizer_provenance": 1578 if mature else 1128,
        "new_head_adam_values": 526, "head_parameter_bytes_float64": 2104,
        "new_head_adam_bytes_float64": 4208,
        "retained_source_optimizer_values_provenance_only": 2580 if mature else 0,
        "head_forward_dense_mac_per_row": 248, "feature_forward_dense_mac_per_row": 816,
        "source_readout_forward_mac_per_row": 432 if mature else 0,
        "feature_tanh_units_per_row": 24 if bank["arm"] != "raw_projection" else 0,
        "head_tanh_units_per_row": 8,
        "note": "Matched head capacity and feature dimension; full retained system storage is not equal across conditions."}


def run_one(arm, seed, panels, raw_train, target_train, raw_val, target_val, output, lock_hashes, batch_indices, expected_initial_digest):
    folder = output/arm/f"seed{seed}"
    if folder.exists():
        raise FileExistsError(folder)
    for name in ("checkpoints", "validation", "features"):
        (folder/name).mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    bank = load_bank(arm, seed)
    bank_before = {key: bank[key].copy() for key in PARAMETER_KEYS if key in bank}
    train_features = extract_features(bank, raw_train)
    normalizer = fit_normalizer(train_features)
    normalized_train = normalize(train_features, normalizer)
    val_features = extract_features(bank, raw_val)
    normalized_val = normalize(val_features, normalizer)
    norm_json = {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in normalizer.items()}
    norm_json.update(fit_panel="train", feature_dimension=24, scaling="one_global_RMS_scalar")
    dump(folder/"normalizer.json", norm_json)
    save_feature_cache(folder/"features/train.npz", train_features, normalized_train, panels["train"], bank, normalizer, "train")
    save_feature_cache(folder/"features/val.npz", val_features, normalized_val, panels["val"], bank, normalizer, "val")
    params = init_head(seed)
    if params_digest(params) != expected_initial_digest:
        raise AssertionError("Head initialization differs across feature arms")
    m, v, t = optimizer_state(params)
    validation, trace = {}, []
    meta = {"bank_path": str(bank["path"].relative_to(ROOT)), "bank_sha256": sha(bank["path"]),
        "normalizer_path": str((folder/"normalizer.json").relative_to(ROOT)),
        "normalizer_sha256": sha(folder/"normalizer.json"), "source_lock": lock_hashes,
        "initial_head_parameter_digest": expected_initial_digest,
        "batch_path": f"batches/seed{seed}.npz", "batch_sha256": sha(ROOT/"batches"/f"seed{seed}.npz")}

    def checkpoint(step):
        save_checkpoint(folder/"checkpoints"/f"step_{step:04d}.npz", params, m, v, t, seed, arm, step, meta)
        logits = forward(params, normalized_val)
        validation[str(step)] = save_prediction(folder/"validation"/f"val_{step:04d}.npz",
            logits, target_val, panels["val"], arm, seed, step, "val")
        dump(folder/"training_trace.json", trace)

    checkpoint(0)
    update_seconds = 0.0
    for step in range(1, UPDATES+1):
        ids = batch_indices[step-1]
        begin = time.perf_counter()
        value, grads = loss_grads(params, normalized_train[ids], target_train[ids])
        t, info = adam_step(params, m, v, t, grads)
        seconds = time.perf_counter()-begin
        update_seconds += seconds
        trace.append({"step": step, "optimizer_step": t, "loss": value, **info,
                      "gradient_and_optimizer_seconds": seconds})
        if step in CHECKPOINTS:
            checkpoint(step)
    if any(not np.array_equal(bank[key], value) for key, value in bank_before.items()):
        raise AssertionError("Fixed feature bank changed")
    first = next((step for step in CHECKPOINTS if validation[str(step)]["complete_accuracy"] >= .95), None)
    confirmed = next((step for previous, step in zip(CHECKPOINTS[:-1], CHECKPOINTS[1:])
        if validation[str(previous)]["complete_accuracy"] >= .95 and validation[str(step)]["complete_accuracy"] >= .95), None)
    accuracies = np.asarray([validation[str(step)]["complete_accuracy"] for step in CHECKPOINTS])
    validation_auc = float(np.trapezoid(accuracies, np.asarray(CHECKPOINTS))/UPDATES)
    feature_rows = len(raw_train)+len(raw_val)
    summary = {"arm": arm, "seed": seed, "status": "trained_test_not_evaluated", "head_shape": [24, 8, 7],
        "parameters": parameter_account(bank), "validation": validation,
        "first_validation_95": first, "first_two_consecutive_validation_95_ending_at": confirmed,
        "validation_accuracy_auc_by_update": validation_auc,
        "gradient_updates": UPDATES, "training_presentations": UPDATES*128,
        "head_forward_training_mac": UPDATES*128*248,
        "feature_rows_precomputed_train_val": feature_rows, "feature_mac_precomputed_train_val": feature_rows*816,
        "validation_head_forward_rows": len(CHECKPOINTS)*len(raw_val),
        "validation_head_forward_mac": len(CHECKPOINTS)*len(raw_val)*248,
        "source_feature_bank_memory_unchanged": True,
        "feature_cache_bytes_train_val": sum((folder/"features"/(panel+".npz")).stat().st_size for panel in ("train", "val")),
        "source_bank_path": meta["bank_path"], "source_bank_sha256": meta["bank_sha256"],
        "initial_head_parameter_digest": expected_initial_digest,
        "final_checkpoint_path": str((folder/"checkpoints/step_4096.npz").relative_to(ROOT)),
        "final_checkpoint_sha256": sha(folder/"checkpoints/step_4096.npz"),
        "batch_sha256": meta["batch_sha256"], "normalizer_sha256": meta["normalizer_sha256"],
        "gradient_and_optimizer_seconds": update_seconds, "training_phase_elapsed_seconds": time.perf_counter()-started}
    dump(folder/"summary.json", summary)
    print(json.dumps({"trained": f"{arm}/{seed}", "first_validation95": first,
        "confirmed_validation95": confirmed, "final_validation": validation["4096"]["complete_accuracy"],
        "test_evaluated": False}), flush=True)
    return summary


def evaluate_fresh_test(models, panels, output):
    # The only call to arrays(test) in the entire experiment occurs here,
    # after a durable all-nine-head training-completed receipt.
    barrier = json.loads((output/"all_training_completed.json").read_text(encoding="utf-8"))
    if barrier["models"] != 9 or barrier["actual_gradient_updates"] != 36864 or len(models) != 9:
        raise AssertionError("Test barrier not satisfied")
    x, target = arrays(panels["test"])
    final_train_target = np.asarray([[int(v) for v in row["target_bits"]] for row in panels["train"]], dtype=np.float64)
    all_source_audits = []
    for summary in models:
        arm, seed = summary["arm"], summary["seed"]
        folder = output/arm/f"seed{seed}"
        bank = load_bank(arm, seed)
        state = load_checkpoint(folder/"checkpoints/step_4096.npz")
        # One preregistered secondary fit diagnostic after every head has
        # finished; cached train features avoid additional source inference.
        with np.load(folder/"features/train.npz", allow_pickle=False) as z:
            final_train_features = z["normalized_features"].copy()
        final_train_logits = forward(state["params"], final_train_features)
        summary["final_train"] = save_prediction(folder/"final_train_predictions.npz", final_train_logits,
            final_train_target, panels["train"], arm, seed, UPDATES, "final_train")
        norm = json.loads((folder/"normalizer.json").read_text(encoding="utf-8"))
        norm["mean"] = np.asarray(norm["mean"], dtype=np.float64)
        raw_features = extract_features(bank, x)
        normalized = normalize(raw_features, norm)
        save_feature_cache(folder/"features/test.npz", raw_features, normalized, panels["test"], bank, norm, "test")
        logits = forward(state["params"], normalized)
        summary["test"] = save_prediction(folder/"test_predictions.npz", logits, target, panels["test"], arm, seed, UPDATES, "test")
        summary.update(status="completed", test_feature_rows=len(x), test_feature_mac=len(x)*816,
            test_head_forward_rows=len(x), test_head_forward_mac=len(x)*248,
            final_train_head_forward_rows=len(final_train_features),
            final_train_head_forward_mac=len(final_train_features)*248,
            test_feature_cache_bytes=(folder/"features/test.npz").stat().st_size,
            source_readout_audit_rows=0, source_readout_audit_mac=0,
            test_features_computed_after_all_training=True)
        if arm == "mature_hidden":
            decoded = source_readout(bank, raw_features)
            truth_op = np.asarray([r["op"] for r in panels["test"]])
            truth_a = np.asarray([r["a"] for r in panels["test"]])
            truth_b = np.asarray([r["b"] for r in panels["test"]])
            source_correct = ((decoded["pred_op"] == truth_op) & (decoded["pred_a"] == truth_a) & (decoded["pred_b"] == truth_b))
            head_correct = np.all((logits >= 0) == target, axis=1)
            audit = {"seed": seed, "cases": len(x), "source_tuple_correct": int(source_correct.sum()),
                "head_correct_when_source_correct": int(head_correct[source_correct].sum()),
                "cases_source_correct": int(source_correct.sum()),
                "head_correct_when_source_incorrect": int(head_correct[~source_correct].sum()),
                "cases_source_incorrect": int((~source_correct).sum()),
                "source_readout_rows": len(x), "source_readout_dense_mac": len(x)*432,
                "scope": "Actual retained source readout on cached raw hidden; truth used only for offline correctness scoring, no oracle replacement"}
            np.savez_compressed(folder/"source_test_audit.npz", **decoded,
                source_tuple_correct=source_correct, max_head_correct=head_correct,
                case_ids=np.asarray([r["case_id"] for r in panels["test"]]),
                metadata_json=np.array(json.dumps(audit, sort_keys=True)))
            summary["actual_source_readout_audit"] = audit
            summary["source_readout_audit_rows"], summary["source_readout_audit_mac"] = len(x), len(x)*432
            all_source_audits.append(audit)
        dump(folder/"summary.json", summary)
        print(json.dumps({"completed": f"{arm}/{seed}", "test_exact": summary["test"]["complete_accuracy"],
                          "test_correct": summary["test"]["complete_correct"], "cases": len(x)}), flush=True)
    return all_source_audits


def run(output, lock_path):
    output = Path(output).resolve()
    hashes = verify_lock(lock_path)
    protocol = json.loads((ROOT/"protocol.json").read_text(encoding="utf-8"))
    config = protocol["training"]
    for key, expected in {"models": 9, "updates_per_model": UPDATES, "batch_size": 128, "lr": .01,
                          "beta1": .9, "beta2": .999, "eps": 1e-8, "clip_global_norm": 5.0}.items():
        if config[key] != expected:
            raise ValueError("Protocol and fixed trainer differ: "+key)
    if tuple(config["checkpoints"]) != CHECKPOINTS or tuple(config["arms"]) != ARMS or tuple(config["seeds"]) != SEEDS:
        raise ValueError("Protocol schedule differs")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(output)
    output.mkdir(parents=True, exist_ok=True)
    begun = time.perf_counter()
    started = datetime.now(timezone.utc).isoformat()
    metadata = {"schema": "feature-transfer-run-v1", "status": "running", "started_utc": started,
        "python": platform.python_version(), "numpy": np.__version__, "source_lock_sha256": sha(lock_path),
        "source_sha256": hashes, "new_source_training_updates": 0, "external_model_calls": 0,
        "W_calls": 0, "manual_training_interventions": 0, "test_tuned_continuations": 0,
        "new_head_updates_budget": 36864, "fresh_test_feature_rows_before_training_completion": 0}
    dump(output/"run_metadata.json", metadata)
    data = json.loads((ROOT/"data.json").read_text(encoding="utf-8"))
    panels = data["panels"]
    raw_train, target_train = arrays(panels["train"])
    raw_val, target_val = arrays(panels["val"])
    models = []
    for seed in SEEDS:
        with np.load(ROOT/"batches"/f"seed{seed}.npz", allow_pickle=False) as z:
            batches = z["indices"].astype(np.int64)
        if batches.shape != (UPDATES, 128) or batches.min() < 0 or batches.max() >= len(raw_train):
            raise ValueError("Unexpected batch indices")
        initial_digest = params_digest(init_head(seed))
        for arm in ARMS:
            models.append(run_one(arm, seed, panels, raw_train, target_train, raw_val, target_val,
                                  output, hashes, batches, initial_digest))
    training_finished = datetime.now(timezone.utc).isoformat()
    barrier = {"schema": "feature-transfer-test-barrier-v1", "models": len(models),
        "actual_gradient_updates": sum(m["gradient_updates"] for m in models),
        "training_finished_utc": training_finished, "fresh_test_feature_rows_so_far": 0,
        "checkpoint_sha256": {m["final_checkpoint_path"]: m["final_checkpoint_sha256"] for m in models}}
    dump(output/"all_training_completed.json", barrier)
    audit = evaluate_fresh_test(models, panels, output)
    if verify_lock(lock_path) != hashes:
        raise AssertionError("Fixed source files changed")
    for model in models:
        if sha(ROOT/model["final_checkpoint_path"]) != model["final_checkpoint_sha256"]:
            raise AssertionError("Test inference changed a final checkpoint")
    metadata.update(status="completed", training_finished_utc=training_finished,
        finished_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter()-begun,
        models=len(models), actual_new_head_updates=sum(m["gradient_updates"] for m in models),
        actual_training_presentations=sum(m["training_presentations"] for m in models),
        actual_head_forward_training_mac=sum(m["head_forward_training_mac"] for m in models),
        actual_feature_forward_rows=sum(m["feature_rows_precomputed_train_val"]+m["test_feature_rows"] for m in models),
        actual_feature_forward_mac=sum(m["feature_mac_precomputed_train_val"]+m["test_feature_mac"] for m in models),
        actual_evaluation_head_forward_rows=sum(m["validation_head_forward_rows"]+m["test_head_forward_rows"]+m["final_train_head_forward_rows"] for m in models),
        actual_evaluation_head_forward_mac=sum(m["validation_head_forward_mac"]+m["test_head_forward_mac"]+m["final_train_head_forward_mac"] for m in models),
        actual_source_readout_audit_rows=sum(m["source_readout_audit_rows"] for m in models),
        actual_source_readout_audit_mac=sum(m["source_readout_audit_mac"] for m in models),
        feature_cache_bytes=sum(m["feature_cache_bytes_train_val"]+m["test_feature_cache_bytes"] for m in models),
        checkpoint_files=sum(1 for _ in output.glob("*/seed*/checkpoints/*.npz")),
        full_frozen_source_lock_unchanged=True)
    dump(output/"summary.json", {"schema": "feature-transfer-results-v1", "models": models,
        "source_test_audits": audit, "scope": protocol["task"]})
    dump(output/"run_metadata.json", metadata)
    print(json.dumps(metadata), flush=True)
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT/"results")
    parser.add_argument("--lock", type=Path, default=ROOT/"source_lock.json")
    args = parser.parse_args()
    run(args.output, args.lock)
