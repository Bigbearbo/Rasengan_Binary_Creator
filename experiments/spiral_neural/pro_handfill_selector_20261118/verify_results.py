"""Independent completed-run replay, without importing experiment modules.

The checker independently executes source matrices, saved sparse-gate wiring,
comparator checkpoints and a bounded Adam recurrence audit. It cannot train or
modify an experimental checkpoint.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import time
import numpy as np

ROOT = Path(__file__).resolve().parent
SEEDS = (101, 202, 303)
ARMS = ("handfilled_frozen", "random_train", "handfilled_train")
STEPS = (0, 16, 64, 128, 256, 512, 1024, 2048, 4096)
KEYS = ("w", "b")
ORDER = [14, 15, 4, 5, 6, 7, 8, 16, 17, 9, 10, 11, 12, 13]
PLACES = np.array([64, 32, 16, 8, 4, 2, 1])


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def meta(archive):
    return json.loads(str(archive["metadata_json"]))


def checkpoint(path):
    z = arrays(path)
    return ({k: z["param_" + k] for k in KEYS},
            {k: z["adam_m_" + k] for k in KEYS},
            {k: z["adam_v_" + k] for k in KEYS}, meta(z))


def init(arm, seed):
    if arm == "random_train":
        return {"w": np.random.default_rng(2100000 + seed).normal(0, np.sqrt(2 / 15), 14),
                "b": np.zeros(1)}
    return {"w": np.r_[PLACES, -PLACES].astype(float), "b": np.array([.5])}


def decode(parameters, raw):
    hidden = np.tanh(raw @ parameters["W1"] + parameters["b1"])
    logits = hidden @ parameters["W2"] + parameters["b2"]
    words = (logits[:, ORDER] >= 0).astype(np.uint8)
    return {"hidden": hidden, "logits": logits, "operand_logits": logits[:, ORDER],
            "words": words, "pred_op": logits[:, :4].argmax(1),
            "pred_a": words[:, :7] @ PLACES, "pred_b": words[:, 7:] @ PLACES}


def expand_gate_matrix(indices, weights, n_inputs):
    matrix = np.zeros((n_inputs, len(indices)))
    for unit in range(len(indices)):
        for slot, incoming in enumerate(indices[unit]):
            matrix[incoming, unit] += weights[unit, slot]
    return matrix


def mux_forward(mux, words, selection):
    # Alternative dense execution of the saved sparse graph; no max/where path.
    joined = np.c_[words, selection]
    first = joined @ mux["dense1"] + mux["layer1_bias"]
    hidden = (first >= 0).astype(np.uint8)
    last = hidden @ mux["dense2"] + mux["layer2_bias"]
    return {"layer1_logits": first, "layer1_bits": hidden,
            "output_logits": last, "output_bits": (last >= 0).astype(np.uint8)}


def forward(parameters, mux, words):
    score = words @ parameters["w"] + parameters["b"][0]
    selection = (score >= 0).astype(np.uint8)
    result = mux_forward(mux, words, selection)
    result.update(selector_logits=score, selection=selection)
    return result


def gradient(parameters, words, target):
    score = words @ parameters["w"] + parameters["b"][0]
    loss = float(np.mean(np.logaddexp(0., score) - target * score))
    dscore = (np.exp(-np.logaddexp(0., -score)) - target) / len(words)
    return loss, {"w": words.T @ dscore, "b": np.array([dscore.sum()])}


def adam(parameters, first, second, step, gradients):
    norm = float(np.sqrt(sum(float(np.sum(v * v)) for v in gradients.values())))
    scale = min(1., 5. / norm) if norm else 1.
    for key in KEYS:
        g = gradients[key] * scale
        first[key] *= .9
        first[key] += (1 - .9) * g
        second[key] *= .999
        second[key] += (1 - .999) * g * g
        parameters[key] -= .01 * (first[key] / (1 - .9 ** step)) / (np.sqrt(second[key] / (1 - .999 ** step)) + 1e-8)
    return norm, scale


class Auditor:
    def __init__(self):
        self.errors = {}
        self.prediction_files = 0
        self.prediction_rows = 0
        self.cache_files = 0
        self.cache_rows = 0
        self.checkpoints = 0
        self.recurrences = 0
        self.temporal_files = 0

    def close(self, name, observed, expected, tolerance=1e-10):
        observed, expected = np.asarray(observed), np.asarray(expected)
        assert observed.shape == expected.shape, (name, observed.shape, expected.shape)
        assert np.isfinite(observed).all() and np.isfinite(expected).all(), name
        delta = float(np.max(np.abs(observed - expected))) if observed.size else 0.
        self.errors[name] = max(self.errors.get(name, 0.), delta)
        assert delta <= tolerance, (name, delta, tolerance)

    def same(self, name, observed, expected):
        assert np.array_equal(observed, expected), name

    def tree(self, name, observed, expected):
        if isinstance(expected, dict):
            assert isinstance(observed, dict) and set(observed) == set(expected), name
            for key, value in expected.items():
                self.tree(name + "." + key, observed[key], value)
        elif isinstance(expected, list):
            assert isinstance(observed, list) and len(observed) == len(expected), name
            for index, value in enumerate(expected):
                self.tree(name + "." + str(index), observed[index], value)
        elif isinstance(expected, float):
            self.close(name, observed, expected)
        else:
            assert observed == expected, (name, observed, expected)

    def check_prediction(self, path, parameters, mux, words, rows, arm, seed, step, panel):
        z = arrays(path)
        m = meta(z)
        assert (m["arm"], m["seed"], m["step"], m["panel"]) == (arm, seed, step, panel)
        result = forward(parameters, mux, words)
        for key, expected in result.items():
            if "logits" in key:
                self.close(key, z[key], expected)
            else:
                self.same(key, z[key], expected)
        target = np.array([[int(c) for c in row["target_bits"]] for row in rows], dtype=np.uint8)
        decision = np.array([int(row["a"] >= row["b"]) for row in rows], dtype=np.uint8)
        correct = np.all(result["output_bits"] == target, axis=1)
        answer = result["output_bits"] @ PLACES
        for key, expected in {"targets": target, "selector_targets": decision,
                              "complete_correct": correct, "predicted_answer": answer,
                              "selector_correct": result["selection"] == decision,
                              "decoded_a": words[:, :7] @ PLACES,
                              "decoded_b": words[:, 7:] @ PLACES,
                              "case_ids": [r["case_id"] for r in rows]}.items():
            self.same(key, z[key], expected)
        calculated = calculate_metrics(result, words, rows)
        self.tree("prediction_metrics", m["metrics"], calculated)
        self.prediction_files += 1
        self.prediction_rows += len(rows)
        return m, result, correct


def subset(correct, mask):
    n = int(mask.sum())
    return {"cases": n, "correct": int(correct[mask].sum()),
            "accuracy": float(correct[mask].mean()) if n else None}


def calculate_metrics(result, words, rows):
    a = np.array([r["a"] for r in rows])
    b = np.array([r["b"] for r in rows])
    targets = np.array([[int(c) for c in r["target_bits"]] for r in rows], dtype=np.uint8)
    decisions = (a >= b).astype(np.uint8)
    correct = np.all(result["output_bits"] == targets, axis=1)
    decision_correct = result["selection"] == decisions
    answer = result["output_bits"] @ PLACES
    decoded_a, decoded_b = words[:, :7] @ PLACES, words[:, 7:] @ PLACES
    source_ok = (decoded_a == a) & (decoded_b == b)
    z = result["selector_logits"]
    strata = [("a_lt_b", a < b), ("a_gt_b", a > b), ("ties", a == b),
              ("source_domain_a_plus_b_lt128", a + b < 128),
              ("outside_source_domain", a + b >= 128)]
    strata += [(f"opcode_{op}", np.array([r.get("op", -1) == op for r in rows])) for op in range(4)]
    return {"cases": len(rows), "complete_correct": int(correct.sum()),
            "complete_accuracy": float(correct.mean()),
            "bit_accuracy": float(np.mean(result["output_bits"] == targets)),
            "selector_correct": int(decision_correct.sum()),
            "selector_accuracy": float(decision_correct.mean()),
            "selector_bce": float(np.mean(np.logaddexp(0, z) - decisions * z)),
            "minimum_signed_selector_margin": float(np.min(z * (2 * decisions.astype(float) - 1))),
            "output_neither_decoded_operand": int(((answer != decoded_a) & (answer != decoded_b)).sum()),
            "output_neither_true_operand": int(((answer != a) & (answer != b)).sum()),
            "source_operand_correct_cases": int(source_ok.sum()),
            "answer_when_source_correct": subset(correct, source_ok),
            "answer_when_source_incorrect": subset(correct, ~source_ok),
            "strata": {name: {"answer": subset(correct, mask), "selector": subset(decision_correct, mask)}
                       for name, mask in strata}}


def run():
    began = time.perf_counter()
    receipt_path = ROOT / "receipts/result_audit.json"
    if receipt_path.exists():
        raise FileExistsError(receipt_path)
    folder = ROOT / "results"
    run_info = read(folder / "run_metadata.json")
    assert run_info["status"] == "completed_after_metadata_recovery"
    recovery = read(ROOT / "receipts/metadata_recovery.json")
    assert recovery["status"] == "PASS_METADATA_ONLY_RECOVERY"
    assert recovery["finalizer_sha256"] == sha(ROOT / "finalize_existing.py")
    assert recovery["training_stderr_sha256"] == sha(ROOT / "training_stderr.log")
    assert recovery["original_run_metadata_sha256"] == sha(ROOT / "receipts/run_metadata_before_recovery.json")
    assert recovery["new_run_metadata_sha256"] == sha(folder / "run_metadata.json")
    assert recovery["reconstructed_summary_sha256"] == sha(folder / "summary.json")
    assert recovery["source_lock_sha256"] == sha(ROOT / "source_lock.json")
    assert recovery["new_training_updates"] == recovery["new_model_inference_rows"] == recovery["new_weight_updates"] == 0
    assert recovery["preserved_scientific_file_count"] == len(recovery["preserved_scientific_sha256"]) == 190
    for name, digest in recovery["preserved_scientific_sha256"].items():
        assert sha(ROOT / name) == digest, "Metadata recovery changed a scientific artifact: " + name
    original_metadata = read(ROOT / "receipts/run_metadata_before_recovery.json")
    assert original_metadata["status"] == "running"
    for key, value in original_metadata.items():
        if key != "status":
            assert run_info[key] == value, "Recovery altered original metadata: " + key
    assert run_info["recovery_new_training_updates"] == run_info["recovery_new_model_inference_rows"] == 0
    error_text = (ROOT / "training_stderr.log").read_text(encoding="utf-8")
    assert "TypeError: 'PosixPath' object is not subscriptable" in error_text
    assert "final_checkpoint_path" in error_text
    assert 'sha(ROOT[m["final_checkpoint_path"]])' in (ROOT / "run_train.py").read_text(encoding="utf-8")
    assert run_info["original_perf_counter_elapsed_seconds"] is None
    assert recovery["lost_perf_counter_elapsed_seconds"] is None
    assert datetime.fromisoformat(run_info["metadata_recovered_utc"]) >= datetime.fromisoformat(run_info["finished_utc"])
    stamp_span = (datetime.fromisoformat(run_info["finished_utc"]) - datetime.fromisoformat(run_info["started_utc"])).total_seconds()
    assert run_info["elapsed_seconds"] == recovery["elapsed_timestamp_span_seconds"] == stamp_span
    preparation = read(ROOT / "receipts/preparation_audit.json")
    assert preparation["status"] == "PASS_complete_independent_preflight"
    locked = read(ROOT / "source_lock.json")["source_sha256"]
    assert run_info["source_sha256"] == locked
    assert run_info["source_lock_sha256"] == sha(ROOT / "source_lock.json")
    for name, digest in locked.items():
        assert sha(ROOT / name) == digest, "Locked input changed: " + name
    for name, digest in preparation["final_reviewed_code_sha256"].items():
        assert sha(ROOT / name) == digest
    barrier_path = folder / "all_training_completed.json"
    barrier = read(barrier_path)
    assert barrier["trained_models"] == 6 and barrier["zero_update_controls"] == 3
    assert barrier["actual_gradient_updates"] == 24576
    assert barrier["fresh_challenge_inference_rows_so_far"] == 0
    assert barrier["reused_test_inference_rows_this_run_so_far"] == 0
    times = [datetime.fromisoformat(run_info[k]) for k in ("started_utc", "training_finished_utc", "finished_utc")]
    assert times[0] <= times[1] <= times[2]
    assert barrier["training_finished_utc"] == run_info["training_finished_utc"]
    barrier_ns = barrier_path.stat().st_mtime_ns
    for path, digest in barrier["checkpoint_sha256"].items():
        assert sha(ROOT / path) == digest
    data = read(ROOT / "data.json")
    panels = data["panels"]
    raw = {name: np.array([[int(c) for c in r["frame_bits"]] for r in rows], dtype=float)
           for name, rows in panels.items()}
    mux = arrays(ROOT / "handfilled_mux.npz")
    mux["dense1"] = expand_gate_matrix(mux["layer1_indices"], mux["layer1_weights"], 15)
    mux["dense2"] = expand_gate_matrix(mux["layer2_indices"], mux["layer2_weights"], 14)
    audit = Auditor()
    global_summary = read(folder / "summary.json")
    models = {(m["arm"], m["seed"]): m for m in global_summary["models"]}
    assert set(models) == {(a, s) for a in ARMS for s in SEEDS}
    reported_sources = {(r["seed"], r["panel"]): r for r in global_summary["source_audits"]}
    assert set(reported_sources) == {(s, p) for s in SEEDS for p in panels}
    decoded = {}
    source_counts = []
    for seed in SEEDS:
        z = arrays(ROOT / f"sources/receiver_seed{seed}.npz")
        source = {k: z["param_" + k] for k in ("W1", "b1", "W2", "b2")}
        assert sum(v.size for v in source.values()) == 1290
        decoded[seed] = {}
        for panel, rows in panels.items():
            values = decode(source, raw[panel])
            decoded[seed][panel] = values
            path = folder / "source_cache" / f"seed{seed}" / (panel + ".npz")
            stored = arrays(path)
            for key, expected in values.items():
                if key in ("hidden", "logits", "operand_logits"):
                    audit.close("source_" + key, stored[key], expected)
                else:
                    audit.same("source_" + key, stored[key], expected)
            audit.same("source_case_ids", stored["case_ids"], [r["case_id"] for r in rows])
            a = np.array([r["a"] for r in rows])
            b = np.array([r["b"] for r in rows])
            op = np.array([r["op"] for r in rows])
            operand_ok = (values["pred_a"] == a) & (values["pred_b"] == b)
            tuple_ok = operand_ok & (values["pred_op"] == op)
            ideal = np.c_[(a[:, None] >> np.arange(6, -1, -1)) & 1,
                          (b[:, None] >> np.arange(6, -1, -1)) & 1]
            margin = values["operand_logits"] * (2 * ideal.astype(float) - 1)
            audit.same("source_operand_correct", stored["source_operand_correct"], operand_ok)
            audit.same("source_tuple_correct", stored["source_tuple_correct"], tuple_ok)
            audit.close("source_signed_margin", stored["signed_operand_bit_margin"], margin)
            m = meta(stored)
            assert m == reported_sources[seed, panel]
            expected_meta = {"seed": seed, "panel": panel, "cases": len(rows),
                             "operand_correct": int(operand_ok.sum()), "tuple_correct": int(tuple_ok.sum()),
                             "operand_accuracy": float(operand_ok.mean()), "tuple_accuracy": float(tuple_ok.mean()),
                             "minimum_signed_operand_bit_margin": float(margin.min()),
                             "median_minimum_row_operand_margin": float(np.median(margin.min(1))),
                             "source_parameter_values": 1290, "source_dense_mac_per_row": 1248,
                             "source_forward_rows": len(rows), "source_forward_mac": len(rows) * 1248,
                             "source_path": f"sources/receiver_seed{seed}.npz",
                             "source_sha256": sha(ROOT / f"sources/receiver_seed{seed}.npz"),
                             "source_weights_unchanged": True}
            for key, value in expected_meta.items():
                audit.tree("source_metrics." + key, m[key], value)
            if panel in ("test", "challenge"):
                assert path.stat().st_mtime_ns >= barrier_ns
                assert datetime.fromisoformat(m["created_utc"]) >= times[1]
            else:
                assert path.stat().st_mtime_ns <= barrier_ns
            audit.cache_files += 1
            audit.cache_rows += len(rows)
            audit.temporal_files += 1
            source_counts.append({"seed": seed, "panel": panel, "cases": len(rows),
                                  "operand_correct": int(operand_ok.sum()), "tuple_correct": int(tuple_ok.sum())})

    summaries = []
    total_trace_rows = 0
    for seed in SEEDS:
        batch_path = ROOT / f"batches/seed{seed}.npz"
        batches = arrays(batch_path)["indices"].astype(np.int64)
        assert batches.shape == (4096, 128)
        assert np.array_equal(batches, np.random.default_rng(2000000 + seed).integers(0, 8240, size=(4096, 128)))
        train_decision = np.array([r["a"] >= r["b"] for r in panels["train"]], dtype=float)
        for arm in ARMS:
            directory = folder / arm / f"seed{seed}"
            summary = read(directory / "summary.json")
            assert summary == models[arm, seed]
            trained = arm != "handfilled_frozen"
            updates = 4096 if trained else 0
            schedule = STEPS if trained else (0,)
            assert summary["status"] == "completed"
            assert summary["gradient_updates"] == updates
            assert summary["training_presentations"] == updates * 128
            assert summary["selector_training_forward_mac"] == updates * 128 * 14
            assert summary["selector_parameter_values"] == 15
            assert summary["selector_trainable_parameters"] == (15 if trained else 0)
            assert summary["fixed_copy_numeric_values"] == 63
            assert summary["retained_inference_model_values"] == 1368
            assert summary["new_inference_numeric_values"] == 78
            assert summary["gate_connectivity_indices"] == 42
            assert summary["source_output_reordering_indices"] == 14
            assert summary["active_new_optimizer_values"] == (30 if trained else 0)
            assert summary["checkpoint_serialized_optimizer_values"] == 30
            assert summary["allocated_optimizer_values"] == 30
            assert summary["source_weights_trained"] is False
            assert summary["copy_weights_trained"] is False
            initial = init(arm, seed)
            trace = read(directory / "training_trace.json")
            assert len(trace) == updates
            for index, row in enumerate(trace, 1):
                assert row["step"] == row["optimizer_step"] == index
                assert np.isfinite(row["loss"]) and np.isfinite(row["grad_norm_before"])
                assert 0 < row["clip_scale"] <= 1
            total_trace_rows += len(trace)
            scores = []
            for step in schedule:
                path = directory / "checkpoints" / f"step_{step:04d}.npz"
                parameters, first, second, m = checkpoint(path)
                assert (m["arm"], m["seed"], m["step"], m["optimizer_step"]) == (arm, seed, step, step)
                assert m["selector_parameters"] == 15
                assert m["selector_trainable_parameters"] == (15 if trained else 0)
                assert m["source_sha256"] == sha(ROOT / f"sources/receiver_seed{seed}.npz")
                assert m["batch_sha256"] == sha(batch_path)
                assert m["lock_hashes"] == locked
                assert sum(v.size for v in parameters.values()) == 15
                for values in (parameters, first, second):
                    assert all(np.isfinite(v).all() for v in values.values())
                if step == 0:
                    for key in KEYS:
                        audit.same("initial_selector", parameters[key], initial[key])
                        audit.same("initial_first_moment", first[key], np.zeros_like(first[key]))
                        audit.same("initial_second_moment", second[key], np.zeros_like(second[key]))
                pm, _, _ = audit.check_prediction(directory / "validation" / f"val_{step:04d}.npz",
                    parameters, mux, decoded[seed]["val"]["words"], panels["val"], arm, seed, step, "val")
                assert pm["metrics"] == summary["validation"][str(step)]
                scores.append(pm["metrics"]["complete_accuracy"])
                assert path.stat().st_mtime_ns <= barrier_ns
                assert (directory / "validation" / f"val_{step:04d}.npz").stat().st_mtime_ns <= barrier_ns
                audit.temporal_files += 2
                audit.checkpoints += 1
            first95 = next((s for s, value in zip(schedule, scores) if value >= .95), None)
            twice95 = next((schedule[i] for i in range(1, len(scores)) if min(scores[i-1:i+1]) >= .95), None)
            assert summary["first_validation_95"] == first95
            assert summary["first_two_consecutive_validation_95_ending_at"] == twice95
            assert summary["minimum_recorded_validation_accuracy"] == min(scores)
            assert summary["validation_degraded_from_initial_at_recorded_checkpoint"] == any(s < scores[0] for s in scores)
            if trained:
                audit.close("validation_auc", summary["validation_accuracy_auc_by_update"],
                            float(np.trapezoid(scores, np.array(schedule)) / 4096))
                replay = {k: v.copy() for k, v in initial.items()}
                first = {k: np.zeros_like(v) for k, v in replay.items()}
                second = {k: np.zeros_like(v) for k, v in replay.items()}
                for step in range(1, 17):
                    indices = batches[step - 1]
                    loss, grads = gradient(replay, decoded[seed]["train"]["words"][indices], train_decision[indices])
                    norm, scale = adam(replay, first, second, step, grads)
                    audit.close("first16_trace_loss", trace[step-1]["loss"], loss)
                    audit.close("first16_trace_norm", trace[step-1]["grad_norm_before"], norm)
                    audit.close("first16_trace_clip", trace[step-1]["clip_scale"], scale)
                    audit.recurrences += 1
                expected, efirst, esecond, _ = checkpoint(directory / "checkpoints/step_0016.npz")
                for key in KEYS:
                    audit.close("first16_parameters", replay[key], expected[key])
                    audit.close("first16_first_moment", first[key], efirst[key])
                    audit.close("first16_second_moment", second[key], esecond[key])
            else:
                assert summary["validation_accuracy_auc_by_update"] is None
            final_path = ROOT / summary["final_checkpoint_path"]
            assert sha(final_path) == summary["final_checkpoint_sha256"]
            assert barrier["checkpoint_sha256"][summary["final_checkpoint_path"]] == sha(final_path)
            final, _, _, _ = checkpoint(final_path)
            for panel in ("train", "test", "challenge"):
                label = "final_train" if panel == "train" else panel
                path = directory / (label + "_predictions.npz")
                pm, _, _ = audit.check_prediction(path, final, mux, decoded[seed][panel]["words"],
                                                 panels[panel], arm, seed, updates, label)
                assert pm["metrics"] == summary[label]
                assert path.stat().st_mtime_ns >= barrier_ns
                assert datetime.fromisoformat(pm["created_utc"]) >= times[1]
                audit.temporal_files += 1
            summaries.append({"arm": arm, "seed": seed, "gradient_updates": updates,
                              "first_validation_95": first95, "two_consecutive95": twice95,
                              "train_correct": summary["final_train"]["complete_correct"],
                              "test_correct": summary["test"]["complete_correct"],
                              "challenge_correct": summary["challenge"]["complete_correct"]})

    pipeline_prediction_files = audit.prediction_files
    pipeline_prediction_rows = audit.prediction_rows
    assert pipeline_prediction_files == 84 and audit.checkpoints == 57
    assert pipeline_prediction_rows == 230136
    assert audit.cache_files == 12 and audit.cache_rows == 43176
    assert audit.recurrences == 96 and total_trace_rows == 24576

    capacity_path = folder / "component_capacity"
    capacity = read(capacity_path / "summary.json")
    assert capacity["endpoint_files"] == len(capacity["endpoints"]) == 15
    a, b = np.repeat(np.arange(128), 128), np.tile(np.arange(128), 128)
    ideal = np.c_[(a[:, None] >> np.arange(6, -1, -1)) & 1,
                  (b[:, None] >> np.arange(6, -1, -1)) & 1].astype(np.uint8)
    ideal_data = arrays(capacity_path / "ideal_words.npz")
    for key, expected in (("a", a), ("b", b), ("words", ideal)):
        audit.same("ideal_" + key, ideal_data[key], expected)
    ideal_rows = [{"case_id": f"ideal_a{int(x):03d}_b{int(y):03d}", "a": int(x), "b": int(y),
                   "target_bits": format(max(int(x), int(y)), "07b"), "op": -1}
                  for x, y in zip(a, b)]
    audit.same("ideal_case_ids", ideal_data["case_ids"], [r["case_id"] for r in ideal_rows])
    expected_endpoints = {(arm, seed, step) for arm in ARMS for seed in SEEDS
                          for step in ((0,) if arm == "handfilled_frozen" else (0, 4096))}
    assert {(e["arm"], e["seed"], e["step"]) for e in capacity["endpoints"]} == expected_endpoints
    component_summaries = []
    for endpoint in capacity["endpoints"]:
        arm, seed, step = endpoint["arm"], endpoint["seed"], endpoint["step"]
        parameters, _, _, _ = checkpoint(folder / arm / f"seed{seed}" / "checkpoints" / f"step_{step:04d}.npz")
        path = capacity_path / arm / f"seed{seed}" / f"step_{step:04d}.npz"
        pm, _, _ = audit.check_prediction(path, parameters, mux, ideal, ideal_rows, arm, seed, step, "ideal_component_exhaustive")
        assert pm["metrics"] == endpoint["metrics"]
        assert path.stat().st_mtime_ns >= barrier_ns
        assert datetime.fromisoformat(pm["created_utc"]) >= times[1]
        audit.temporal_files += 1
        component_summaries.append({"arm": arm, "seed": seed, "step": step,
                                   "correct": endpoint["metrics"]["complete_correct"],
                                   "selector_correct": endpoint["metrics"]["selector_correct"],
                                   "source_domain_correct": endpoint["metrics"]["strata"]["source_domain_a_plus_b_lt128"]["answer"]["correct"],
                                   "outside_source_domain_correct": endpoint["metrics"]["strata"]["outside_source_domain"]["answer"]["correct"]})
    mux_test = arrays(capacity_path / "mux_truth_table.npz")
    both_words = np.repeat(ideal, 2, axis=0)
    selections = np.tile(np.array([0, 1], dtype=np.uint8), len(ideal))
    audit.same("mux_exhaustive_words", mux_test["words"], both_words)
    audit.same("mux_exhaustive_selection", mux_test["selection"], selections)
    actual_mux = mux_forward(mux, both_words, selections)
    target = selections[:, None] * both_words[:, :7] + (1 - selections[:, None]) * both_words[:, 7:]
    for key, expected in actual_mux.items():
        audit.same("mux_exhaustive_" + key, mux_test[key], expected)
    audit.same("mux_exhaustive_targets", mux_test["targets"], target)
    correct = np.all(actual_mux["output_bits"] == target, axis=1)
    audit.same("mux_exhaustive_correct", mux_test["complete_correct"], correct)
    assert int(correct.sum()) == len(correct) == 32768
    assert capacity["mux_only_cases"] == capacity["mux_only_correct"] == 32768
    assert capacity["cases_per_endpoint"] == 16384
    assert capacity["endpoint_forward_rows"] == 245760
    assert capacity["endpoint_forward_mac"] == 245760 * 56
    assert capacity["mux_only_sparse_mac"] == 32768 * 42
    assert capacity["source_decoder_forward_rows"] == 0
    assert audit.prediction_files == 99 and audit.prediction_rows == 475896

    expected_costs = {
        "trained_models": 6, "zero_update_controls": 3, "actual_gradient_updates": 24576,
        "actual_training_presentations": 3145728, "actual_selector_training_forward_mac": 3145728 * 14,
        "actual_source_forward_rows": 43176, "actual_source_forward_mac": 43176 * 1248,
        "actual_hybrid_evaluation_rows": 230136, "actual_hybrid_evaluation_forward_mac": 230136 * 56,
        "component_endpoint_forward_rows": 245760, "component_endpoint_forward_mac": 245760 * 56,
        "component_mux_only_rows": 32768, "component_mux_only_mac": 32768 * 42,
        "source_cache_files": 12, "checkpoint_files": 57,
        "source_cache_bytes": sum(p.stat().st_size for p in (folder / "source_cache").glob("seed*/*.npz")),
        "source_weights_unchanged": True, "copy_weights_unchanged": True,
        "new_source_training_updates": 0, "manual_training_interventions": 0,
        "external_model_calls": 0, "W_calls": 0, "test_tuned_continuations": 0,
        "fresh_challenge_inference_before_barrier": 0, "reused_test_inference_before_barrier": 0
    }
    for key, expected in expected_costs.items():
        assert run_info[key] == expected, (key, run_info[key], expected)
    for name, digest in locked.items():
        assert sha(ROOT / name) == digest
    receipt = {
        "status": "PASS_independent_result_replay", "created_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.perf_counter() - began,
        "verifier_sha256": sha(__file__), "source_lock_sha256": sha(ROOT / "source_lock.json"),
        "observed_run_status": run_info["status"],
        "metadata_recovery_review": {
            "receipt_sha256": sha(ROOT / "receipts/metadata_recovery.json"),
            "finalizer_sha256": sha(ROOT / "finalize_existing.py"),
            "preserved_scientific_files_hash_checked": 190,
            "original_running_metadata_and_exception_preserved": True,
            "finalizer_code_review": "Read-only inventory/hash and saved-array shape checks; does not import trainer/model or call neural inference/optimizer. Only metadata/global summary and recovery evidence are written.",
            "recovery_new_training_updates": 0, "recovery_new_model_inference_rows": 0,
            "original_perf_counter_elapsed_seconds": None,
            "observed_utc_span_to_last_saved_component_summary_seconds": stamp_span,
            "note": "Original batch completed all scientific outputs but crashed during final checkpoint-hash bookkeeping. Explicit metadata recovery is not represented as an error-free original invocation."
        },
        "locked_hashes_verified_unchanged": len(locked), "imported_experiment_modules": False,
        "source_cache_files": audit.cache_files, "source_forward_rows": audit.cache_rows,
        "source_forward_mac": audit.cache_rows * 1248, "checkpoints_verified": audit.checkpoints,
        "pipeline_prediction_files": pipeline_prediction_files, "pipeline_prediction_rows": pipeline_prediction_rows,
        "component_endpoint_prediction_files": 15, "component_endpoint_prediction_rows": 245760,
        "all_prediction_files": audit.prediction_files, "all_prediction_rows": audit.prediction_rows,
        "independent_mux_truth_table_rows": 32768,
        "optimizer_recurrences_verification_only": audit.recurrences,
        "verification_optimizer_presentations": audit.recurrences * 128,
        "formal_experimental_updates_added": 0, "trace_rows_structurally_checked": total_trace_rows,
        "temporal_file_order_checks": audit.temporal_files,
        "maximum_absolute_error_by_comparison": audit.errors,
        "source_audit": source_counts, "model_summary": summaries,
        "component_summary": component_summaries, "accounting_recomputed": expected_costs,
        "scope": "All saved predictions/caches/checkpoints and full ideal-component diagnostics independently recomputed; only first16updates of each of6trainedheads replayed (96verificationrecurrences), not entire4096steptraining. File-order, code-lock and durable barrier checks support declared execution order; no new learning or post-test tuning."
    }
    receipt_path.parent.mkdir(exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("status", "wall_seconds", "verifier_sha256", "locked_hashes_verified_unchanged",
          "source_forward_rows", "checkpoints_verified", "all_prediction_files", "all_prediction_rows",
          "optimizer_recurrences_verification_only", "temporal_file_order_checks")}, indent=2))


if __name__ == "__main__":
    run()
