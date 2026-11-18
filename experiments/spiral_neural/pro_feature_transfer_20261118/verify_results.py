"""Independent result audit; never imports experiment/trainer implementations.

Recomputes saved features and predictions. Replays only the first sixteen
updates of each of nine heads (144 audit recurrences, not experimental work).
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time
import numpy as np

ROOT = Path(__file__).resolve().parent
KEYS = ("W1", "b1", "W2", "b2")
ARMS = ("mature_hidden", "random_hidden", "raw_projection")
SEEDS = (101, 202, 303)
STEPS = (0, 16, 64, 128, 256, 512, 1024, 2048, 4096)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key].copy() for key in archive.files}


def metadata(archive):
    return json.loads(str(archive["metadata_json"]))


def head_state(path):
    archive = npz(path)
    return ({key: archive["param_"+key] for key in KEYS},
            {key: archive["adam_m_"+key] for key in KEYS},
            {key: archive["adam_v_"+key] for key in KEYS}, metadata(archive))


def digest(params):
    result = hashlib.sha256()
    for key in KEYS:
        result.update(key.encode())
        result.update(str(params[key].shape).encode())
        result.update(params[key].astype("<f8", copy=False).tobytes(order="C"))
    return result.hexdigest()


def head_forward(params, x):
    return np.tanh(x @ params["W1"]+params["b1"]) @ params["W2"]+params["b2"]


def head_gradient(params, x, target):
    hidden = np.tanh(x @ params["W1"]+params["b1"])
    logits = hidden @ params["W2"]+params["b2"]
    loss = float(np.mean(np.logaddexp(0, logits)-target*logits))
    derivative = (np.exp(-np.logaddexp(0, -logits))-target)/target.size
    incoming = (derivative @ params["W2"].T)*(1-hidden*hidden)
    return loss, {"W1": x.T @ incoming, "b1": incoming.sum(0),
                  "W2": hidden.T @ derivative, "b2": derivative.sum(0)}


def adam(params, first, second, step, gradient):
    norm = float(np.sqrt(sum(float(np.sum(gradient[key]**2)) for key in KEYS)))
    scale = min(1., 5./norm) if norm else 1.
    for key in KEYS:
        g = gradient[key]*scale
        first[key] *= .9
        first[key] += (1-.9)*g
        second[key] *= .999
        second[key] += (1-.999)*g**2
        params[key] -= .01*(first[key]/(1-.9**step))/(np.sqrt(second[key]/(1-.999**step))+1e-8)
    return norm, scale


class Audit:
    def __init__(self):
        self.max_error = {}
        self.prediction_files = 0
        self.prediction_rows = 0
        self.feature_files = 0
        self.feature_rows = 0
        self.checkpoints = 0
        self.recurrences = 0
        self.source_readout_rows = 0

    def close(self, label, actual, expected, tolerance=1e-10):
        actual, expected = np.asarray(actual), np.asarray(expected)
        assert actual.shape == expected.shape, (label, actual.shape, expected.shape)
        assert np.isfinite(actual).all() and np.isfinite(expected).all(), label
        error = float(np.max(np.abs(actual-expected))) if actual.size else 0.
        self.max_error[label] = max(self.max_error.get(label, 0.), error)
        assert error <= tolerance, (label, error, tolerance)

    def same(self, label, actual, expected):
        assert np.array_equal(actual, expected), label

    def prediction(self, path, logits, target, rows, arm, seed, step, panel):
        archive = npz(path)
        meta = metadata(archive)
        assert (meta["arm"], meta["seed"], meta["step"], meta["panel"]) == (arm, seed, step, panel)
        hard = (logits >= 0).astype(np.uint8)
        exact = np.all(hard == target, axis=1)
        answer = hard @ np.array([64, 32, 16, 8, 4, 2, 1])
        self.close("prediction_logits", archive["logits"], logits)
        for key, expected in {"targets": target, "hard_bits": hard, "predicted_answer": answer,
                              "complete_correct": exact, "case_ids": [r["case_id"] for r in rows],
                              "source_op": [r["op"] for r in rows], "a": [r["a"] for r in rows],
                              "b": [r["b"] for r in rows]}.items():
            self.same(key, archive[key], expected)
        stats = meta["metrics"]
        assert stats["cases"] == len(rows) and stats["complete_correct"] == int(exact.sum())
        self.close("metric_accuracy", stats["complete_accuracy"], float(exact.mean()))
        self.close("metric_bit_accuracy", stats["bit_accuracy_diagnostic"], float((hard == target).mean()))
        loss = float(np.mean(np.logaddexp(0, logits)-target*logits))
        self.close("metric_loss", stats["loss"], loss)
        for which in ("a", "b"):
            self.close("copy_baseline", stats["copy_"+which+"_baseline"],
                       sum(r[which] == max(r["a"], r["b"]) for r in rows)/len(rows))
        strata = {"opcode_"+str(op): np.array([r["op"] == op for r in rows]) for op in range(4)}
        strata.update(a_lt_b=np.array([r["a"] < r["b"] for r in rows]),
                      a_gt_b=np.array([r["a"] > r["b"] for r in rows]),
                      a_eq_b=np.array([r["a"] == r["b"] for r in rows]))
        for name, selected in strata.items():
            s = stats["strata"][name]
            assert s["cases"] == int(selected.sum()) and s["correct"] == int(exact[selected].sum())
            self.close("stratum_accuracy", s["accuracy"], float(exact[selected].mean()))
        self.prediction_files += 1
        self.prediction_rows += len(rows)
        return stats, exact


def run():
    began = time.perf_counter()
    results = ROOT/"results"
    run_info = read(results/"run_metadata.json")
    assert run_info["status"] == "completed", "Audit requires completed formal run"
    preparation = read(ROOT/"receipts/preparation_audit.json")
    assert preparation["status"] == "PASS_complete_independent_preflight"
    lock = read(ROOT/"source_lock.json")["source_sha256"]
    for relative, expected in lock.items():
        assert sha(ROOT/relative) == expected, "Source changed: "+relative
    for relative, expected in preparation["final_reviewed_code_sha256"].items():
        assert sha(ROOT/relative) == expected, "Preflight code changed: "+relative
    assert run_info["source_sha256"] == lock
    assert run_info["source_lock_sha256"] == sha(ROOT/"source_lock.json")
    barrier_path = results/"all_training_completed.json"
    barrier = read(barrier_path)
    assert barrier["models"] == 9 and barrier["actual_gradient_updates"] == 36864
    assert barrier["fresh_test_feature_rows_so_far"] == 0
    times = [datetime.fromisoformat(run_info[k]) for k in ("started_utc", "training_finished_utc", "finished_utc")]
    assert times[0] <= times[1] <= times[2]
    assert barrier["training_finished_utc"] == run_info["training_finished_utc"]
    barrier_ns = barrier_path.stat().st_mtime_ns
    data = read(ROOT/"data.json")
    panels = data["panels"]
    inputs = {name: np.array([[int(bit) for bit in row["frame_bits"]] for row in rows], dtype=float)
              for name, rows in panels.items()}
    targets = {name: np.array([[int(bit) for bit in row["target_bits"]] for row in rows], dtype=float)
               for name, rows in panels.items()}
    audit = Audit()
    global_summary = read(results/"summary.json")
    models = {(m["arm"], m["seed"]): m for m in global_summary["models"]}
    assert set(models) == {(a, s) for a in ARMS for s in SEEDS}
    output_models = []
    head_digest_by_seed = {}
    trace_count = 0
    temporal_files = 0
    total_source_correct = 0
    for seed in SEEDS:
        batches = npz(ROOT/f"batches/seed{seed}.npz")["indices"].astype(np.int64)
        rng = np.random.default_rng(1900000+seed)
        initial = {"W1": rng.normal(0, np.sqrt(2/32), (24, 8)), "b1": np.zeros(8),
                   "W2": rng.normal(0, np.sqrt(2/15), (8, 7)), "b2": np.zeros(7)}
        head_digest_by_seed[str(seed)] = digest(initial)
        for arm in ARMS:
            folder = results/arm/f"seed{seed}"
            summary = read(folder/"summary.json")
            assert summary == models[(arm, seed)]
            source_path = ROOT/(f"sources/receiver_seed{seed}.npz" if arm == "mature_hidden" else
                               f"banks/random_seed{seed}.npz" if arm == "random_hidden" else "banks/raw_projection.npz")
            bank_archive = npz(source_path)
            prefix = "param_" if arm == "mature_hidden" else ""
            bank = {key: bank_archive[prefix+key] for key in (("W1", "b1", "W2", "b2") if prefix else ("W1", "b1"))}
            assert summary["source_bank_sha256"] == sha(source_path)
            assert summary["batch_sha256"] == sha(ROOT/f"batches/seed{seed}.npz")
            assert summary["initial_head_parameter_digest"] == digest(initial)
            assert summary["source_feature_bank_memory_unchanged"] is True
            assert summary["gradient_updates"] == 4096 and summary["training_presentations"] == 4096*128
            feature = {}
            for panel in ("train", "val", "test"):
                projected = inputs[panel] @ bank["W1"]+bank["b1"]
                feature[panel] = projected if arm == "raw_projection" else np.tanh(projected)
            mean = feature["train"].mean(0)
            rms = float(np.sqrt(np.mean((feature["train"]-mean)**2)))
            scale = max(rms, 1e-8)
            normalizer = read(folder/"normalizer.json")
            audit.close("normalizer_mean", normalizer["mean"], mean)
            audit.close("normalizer_scalar", normalizer["scale"], scale)
            audit.close("normalizer_rms", normalizer["unclamped_global_rms"], rms)
            assert normalizer["fit_panel"] == "train" and normalizer["fit_rows"] == 8240
            assert normalizer["fixed_values"] == 25 and normalizer["scaling"] == "one_global_RMS_scalar"
            assert summary["normalizer_sha256"] == sha(folder/"normalizer.json")
            normalized = {name: (values-mean)/scale for name, values in feature.items()}
            for panel in ("train", "val", "test"):
                cache_path = folder/f"features/{panel}.npz"
                cache = npz(cache_path)
                cm = metadata(cache)
                assert cm["panel"] == panel and cm["normalizer_fit_panel"] == "train"
                assert cm["normalizer_fit_rows"] == 8240 and cm["bank_sha256"] == sha(source_path)
                audit.close("raw_feature_cache", cache["raw_features"], feature[panel])
                audit.close("normalized_feature_cache", cache["normalized_features"], normalized[panel])
                audit.same("feature_case_ids", cache["case_ids"], [r["case_id"] for r in panels[panel]])
                assert (cache_path.stat().st_mtime_ns >= barrier_ns) if panel == "test" else (cache_path.stat().st_mtime_ns <= barrier_ns)
                audit.feature_files += 1
                audit.feature_rows += len(feature[panel])
                temporal_files += 1
            trace = read(folder/"training_trace.json")
            assert len(trace) == 4096
            for index, row in enumerate(trace, 1):
                assert row["step"] == index and row["optimizer_step"] == index
                assert np.isfinite(row["loss"]) and row["gradient_and_optimizer_seconds"] >= 0
            trace_count += len(trace)
            accuracies = []
            for step in STEPS:
                cp = folder/f"checkpoints/step_{step:04d}.npz"
                params, first, second, meta = head_state(cp)
                assert meta["step"] == step and meta["optimizer_step"] == step
                assert (meta["arm"], meta["seed"], meta["shape"], meta["trainable_parameters"]) == (arm, seed, [24, 8, 7], 263)
                assert meta["initial_head_parameter_digest"] == digest(initial)
                assert meta["batch_sha256"] == summary["batch_sha256"]
                assert meta["source_lock"] == lock and meta["bank_sha256"] == sha(source_path)
                assert sum(a.size for a in params.values()) == 263
                for values in (params, first, second):
                    assert all(np.isfinite(a).all() for a in values.values())
                if step == 0:
                    for key in KEYS:
                        audit.same("initial_params", params[key], initial[key])
                        audit.same("initial_adam_m", first[key], np.zeros_like(first[key]))
                        audit.same("initial_adam_v", second[key], np.zeros_like(second[key]))
                logits = head_forward(params, normalized["val"])
                stats, _ = audit.prediction(folder/f"validation/val_{step:04d}.npz", logits,
                                           targets["val"], panels["val"], arm, seed, step, "val")
                assert stats == summary["validation"][str(step)]
                accuracies.append(stats["complete_accuracy"])
                assert cp.stat().st_mtime_ns <= barrier_ns
                audit.checkpoints += 1
                temporal_files += 1
            first95 = next((step for step, acc in zip(STEPS, accuracies) if acc >= .95), None)
            confirmed = next((STEPS[i] for i in range(1, len(STEPS)) if min(accuracies[i-1:i+1]) >= .95), None)
            assert summary["first_validation_95"] == first95
            assert summary["first_two_consecutive_validation_95_ending_at"] == confirmed
            audit.close("validation_auc", summary["validation_accuracy_auc_by_update"],
                        float(np.trapezoid(accuracies, np.asarray(STEPS))/4096))
            replay = {key: initial[key].copy() for key in KEYS}
            m = {key: np.zeros_like(replay[key]) for key in KEYS}
            v = {key: np.zeros_like(replay[key]) for key in KEYS}
            for index in range(16):
                ids = batches[index]
                loss, gradient = head_gradient(replay, normalized["train"][ids], targets["train"][ids])
                norm, clipping = adam(replay, m, v, index+1, gradient)
                audit.close("prefix_loss", trace[index]["loss"], loss)
                audit.close("prefix_gradient_norm", trace[index]["grad_norm_before"], norm)
                audit.close("prefix_clip_scale", trace[index]["clip_scale"], clipping)
                audit.recurrences += 1
            saved, sm, sv, _ = head_state(folder/"checkpoints/step_0016.npz")
            for key in KEYS:
                audit.close("prefix_params", saved[key], replay[key])
                audit.close("prefix_adam_m", sm[key], m[key])
                audit.close("prefix_adam_v", sv[key], v[key])
            final_path = folder/"checkpoints/step_4096.npz"
            relative_final = str(final_path.relative_to(ROOT))
            assert sha(final_path) == summary["final_checkpoint_sha256"] == barrier["checkpoint_sha256"][relative_final]
            final_params, _, _, _ = head_state(final_path)
            correctness = {}
            for panel, filename, metric_name in (("train", "final_train_predictions.npz", "final_train"),
                                                   ("test", "test_predictions.npz", "test")):
                logits = head_forward(final_params, normalized[panel])
                stats, correctness[panel] = audit.prediction(folder/filename, logits, targets[panel],
                            panels[panel], arm, seed, 4096, "final_train" if panel == "train" else "test")
                assert stats == summary[metric_name]
                assert (folder/filename).stat().st_mtime_ns >= barrier_ns
                temporal_files += 1
            if arm == "mature_hidden":
                source_logits = feature["test"] @ bank["W2"]+bank["b2"]
                bits = (source_logits[:, 4:] >= 0).astype(np.uint8)
                low, high = np.array([16, 8, 4, 2, 1]), np.array([64, 32])
                op = source_logits[:, :4].argmax(1)
                a = bits[:, :5] @ low+bits[:, 10:12] @ high
                b = bits[:, 5:10] @ low+bits[:, 12:14] @ high
                correct = ((op == np.array([r["op"] for r in panels["test"]])) &
                           (a == np.array([r["a"] for r in panels["test"]])) &
                           (b == np.array([r["b"] for r in panels["test"]])))
                source_path_saved = folder/"source_test_audit.npz"
                source_saved = npz(source_path_saved)
                audit.close("source_readout_logits", source_saved["logits"], source_logits)
                for key, expected in {"operand_bits": bits, "pred_op": op, "pred_a": a, "pred_b": b,
                                      "source_tuple_correct": correct, "max_head_correct": correctness["test"],
                                      "case_ids": [r["case_id"] for r in panels["test"]]}.items():
                    audit.same("source_audit_"+key, source_saved[key], expected)
                sa = metadata(source_saved)
                assert sa == summary["actual_source_readout_audit"]
                assert sa["source_tuple_correct"] == int(correct.sum())
                assert sa["head_correct_when_source_correct"] == int(correctness["test"][correct].sum())
                assert sa["head_correct_when_source_incorrect"] == int(correctness["test"][~correct].sum())
                assert source_path_saved.stat().st_mtime_ns >= barrier_ns
                audit.source_readout_rows += len(correct)
                total_source_correct += int(correct.sum())
                temporal_files += 1
            output_models.append({"arm": arm, "seed": seed, "first_validation_95": first95,
                "validation_auc": summary["validation_accuracy_auc_by_update"],
                "train": summary["final_train"]["complete_accuracy"],
                "validation": summary["validation"]["4096"]["complete_accuracy"],
                "test": summary["test"]["complete_accuracy"]})
    expected_counts = {"models": 9, "actual_new_head_updates": 36864,
        "actual_training_presentations": 36864*128,
        "actual_head_forward_training_mac": 36864*128*248,
        "actual_feature_forward_rows": 121104, "actual_feature_forward_mac": 121104*816,
        "actual_evaluation_head_forward_rows": 272016, "actual_evaluation_head_forward_mac": 272016*248,
        "actual_source_readout_audit_rows": 9360, "actual_source_readout_audit_mac": 9360*432,
        "checkpoint_files": 81, "new_source_training_updates": 0,
        "manual_training_interventions": 0, "test_tuned_continuations": 0,
        "fresh_test_feature_rows_before_training_completion": 0}
    for key, value in expected_counts.items():
        assert run_info[key] == value, (key, run_info[key], value)
    assert audit.prediction_files == 99 and audit.prediction_rows == 272016
    assert audit.feature_files == 27 and audit.feature_rows == 121104
    assert audit.recurrences == 144 and audit.checkpoints == 81 and trace_count == 36864
    assert len(barrier["checkpoint_sha256"]) == 9
    assert len(list(results.glob("*/seed*/checkpoints/*.npz"))) == 81
    assert run_info["feature_cache_bytes"] == sum(p.stat().st_size for p in results.glob("*/seed*/features/*.npz"))
    for relative, expected in lock.items():
        assert sha(ROOT/relative) == expected, "Source changed during audit: "+relative
    receipt = {"schema": "independent-feature-transfer-result-audit-v1", "status": "PASS",
        "created_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.perf_counter()-began,
        "author": "retention_method; independent of experiment implementation",
        "verifier_sha256": sha(Path(__file__)), "preparation_audit_sha256": sha(ROOT/"receipts/preparation_audit.json"),
        "source_lock_sha256": sha(ROOT/"source_lock.json"), "run_metadata_sha256": sha(results/"run_metadata.json"),
        "formal_experimental_updates_verified_by_saved_trace_structure": trace_count,
        "audit_recurrences": audit.recurrences, "audit_recurrence_scope": "Only step0 to step16 for each of nine heads",
        "new_experimental_updates": 0, "full_training_replays": 0,
        "checkpoint_files_checked": audit.checkpoints, "prediction_files_checked": audit.prediction_files,
        "prediction_rows_recomputed": audit.prediction_rows, "feature_cache_files_checked": audit.feature_files,
        "feature_rows_recomputed": audit.feature_rows, "source_readout_rows_recomputed": audit.source_readout_rows,
        "source_readout_correct": total_source_correct, "max_abs_errors": audit.max_error,
        "temporal_order_files_checked": temporal_files,
        "test_barrier_evidence": "Locked call path, durable all-nine completion receipt, all final checkpoint hashes, UTC ordering and file modification ordering agree; not an OS security boundary",
        "fixed_source_hashes_rechecked_before_and_after": len(lock), "paired_initial_head_digest_by_seed": head_digest_by_seed,
        "split_and_exposure_checks": "Referenced immutable independent preparation audit and its data hashes; no repeated dataset redesign",
        "expected_formal_counts": expected_counts, "models": output_models,
        "limits": ["No complete 4096-step recurrence replay; later optimizer history verified structurally, predictions recomputed from every saved checkpoint",
                   "Fixed-bank transfer only; not a test of free-parent regression or recovery",
                   "A failed MAX head does not prove the frozen representation lacks operand information or cannot support another head/budget"]}
    destination = ROOT/"receipts/result_audit.json"
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
