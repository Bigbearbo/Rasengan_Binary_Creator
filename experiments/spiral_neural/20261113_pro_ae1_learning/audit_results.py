"""Bounded independent AE1 result audit; run only after all training/replay.

This file imports neither learner nor the historical Model. Neural predictions
are recomputed directly from saved float32 arrays using raw two-channel input,
tanh, and the fixed 0/1/STOP output rule. It never changes model parameters.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
from itertools import zip_longest
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
import numpy as np

MANIFEST_SHA = "460b52e7439a4645b06872c015677f530ffd2760c523f80ffb77cc2998722265"
L, H, CAP, FORWARD_MAC, TRAIN_MAC = 80, 64, 32, 10432, 21056


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def state_sha(state):
    digest = hashlib.sha256()
    for name, value in sorted(state.items()):
        digest.update(canonical([name, value.dtype.str, list(value.shape)]).encode())
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def load_arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name].copy() for name in archive.files}


def validate_state(state, seed, updates):
    require((int(state["L"]), int(state["H"]), int(state["meta_seed"]), int(state["t"]))
            == (L, H, seed, updates), "Checkpoint identity/shape/update mismatch")
    shapes = ((2 * L, H), (H,), (H, 3), (3,))
    for label in ("p", "m", "v", "birth"):
        for i, shape in enumerate(shapes):
            value = state[f"{label}{i}"]
            require(value.shape == shape, f"Wrong checkpoint shape: {label}{i}")
            require(value.dtype == np.dtype("int64" if label == "birth" else "float32"),
                    f"Wrong checkpoint dtype: {label}{i}")
            require(np.isfinite(value).all(), f"Nonfinite checkpoint array: {label}{i}")
            if label == "birth":
                require(np.count_nonzero(value) == 0, "Unexpected parameter birth/growth")
    require(int(state["meta_train_macs"]) == updates * TRAIN_MAC, "Checkpoint training MAC")
    require(int(state["meta_inference_calls"]) == int(state["meta_inference_macs"]) == 0,
            "Saved training checkpoint already includes performance inference")
    require(json.loads(str(state["meta_events"])) == [], "Unexpected growth events")


def forward(state, text, counters):
    require(0 < len(text) <= L and set(text) <= {"0", "1"}, "Invalid independent raw prefix")
    slots = np.zeros((L, 2), dtype=np.float32)
    for position, bit in enumerate(text):
        slots[position, int(bit)] = 1
    hidden = np.tanh(slots.reshape(1, -1) @ state["p0"] + state["p1"])
    logits = (hidden @ state["p2"] + state["p3"])[0]
    counters["neural_forward_calls"] += 1
    require(np.isfinite(logits).all(), "Nonfinite independent logits")
    return logits


def infer_row(state, row, counters):
    q, a = row["Q"], row["A"]
    generated, overflow, exhausted = "", False, False
    for _ in range(CAP):
        prefix = q + generated
        if len(prefix) > L:
            overflow = True
            break
        action = "01S"[int(forward(state, prefix, counters).argmax())]
        generated += action
        if action == "S":
            break
    else:
        exhausted = True
    target = a + "S"
    predictions, losses = [], []
    for position, action in enumerate(target):
        logits = forward(state, q + a[:position], counters).astype(np.float64)
        logp = logits - np.logaddexp.reduce(logits)
        predictions.append("01S"[int(logits.argmax())])
        losses.append(-float(logp["01S".index(action)]))
    tf_predictions = "".join(predictions)
    indices = [i for i in range(len(a)) if i % 6 != 5]
    stopped = generated.endswith("S")
    first_error = next((i for i, pair in enumerate(zip_longest(generated, target))
                        if pair[0] != pair[1]), None)
    return {
        "target": target, "generated": generated,
        "whole_correct": generated == target,
        "STOP_position_correct": stopped and len(generated) == len(target),
        "early_STOP": stopped and len(generated) < len(target),
        "late_STOP": stopped and len(generated) > len(target), "no_STOP": not stopped,
        "first_error": first_error, "overflow": overflow, "cap_exhausted": exhausted,
        "free_info_correct": sum(i < len(generated) and generated[i] == a[i] for i in indices),
        "free_info_total": len(indices), "tf_predictions": tf_predictions,
        "tf_correct": sum(p == t for p, t in zip(tf_predictions, target)),
        "tf_targets": len(target),
        "tf_info_correct": sum(tf_predictions[i] == a[i] for i in indices),
        "tf_info_total": len(indices), "tf_CE_mean": sum(losses) / len(losses),
        "END_at_expected_boundary": generated[len(a):len(a) + 6] == "111100",
    }


def audit(here, commit, result):
    repo = here.parents[2]
    tracked = {}

    def remember(path):
        path = Path(path)
        digest = sha(path)
        tracked[path] = digest
        return digest

    manifest_path = here / "frozen_manifest.json"
    require(remember(manifest_path) == MANIFEST_SHA, "Unexpected frozen manifest")
    require(len(commit) == 40 and all(c in "0123456789abcdef" for c in commit),
            "An exact preregistration commit is required")
    public = subprocess.run(["git", "show", f"{commit}:{manifest_path.relative_to(repo)}"],
                            cwd=repo, capture_output=True, check=True).stdout
    require(hashlib.sha256(public).hexdigest() == MANIFEST_SHA, "Git preregistration manifest differs")
    manifest = read(manifest_path)
    for rel, digest in manifest["files_sha256"].items():
        require(remember(repo / rel) == digest, f"Frozen file differs: {rel}")
    protocol = read(here / "protocol.json")
    data = read(here / "dataset.json.gz")
    cumulative = [0] + protocol["curriculum"]["cumulative_updates"]
    require(protocol["seeds"] == [101, 202, 303] and cumulative[-1] == 201840,
            "Unexpected frozen experiment")
    summaries = {}
    for seed in protocol["seeds"]:
        path = here / "runs" / f"primary_seed{seed}" / "summary.json"
        remember(path)
        summary = read(path)
        require(summary["status"] == "completed" and summary["preregistration_commit"] == commit,
                "All primary trajectories must be completed under the preregistration commit")
        require(summary["updates"] == cumulative[-1], "Incomplete primary update budget")
        summaries[seed] = summary
    replay_path = here / "runs/replay_seed101/summary.json"
    replay_gate_path = here / "replay_check.json"
    remember(replay_path)
    remember(replay_gate_path)
    replay, replay_gate = read(replay_path), read(replay_gate_path)
    require(replay["status"] == "completed" and replay["preregistration_commit"] == commit
            and replay_gate["status"] == "PASS", "Prespecified replay has not completed/passed")
    for phase in range(1, 6):
        primary_record = summaries[101]["phases"][phase - 1]
        replay_record = replay["phases"][phase - 1]
        for field in ("phase", "id", "updates", "train_dense_MAC", "epochs", "full_state_sha256"):
            require(primary_record[field] == replay_record[field], "Archived replay summary differs")
        path = here / "runs/replay_seed101" / f"phase{phase}.npz"
        require(remember(path) == replay_record["checkpoint_sha256"], "Replay checkpoint file differs")
        require(state_sha(load_arrays(path)) == primary_record["full_state_sha256"],
                "Archived replay state differs from primary")

    evaluation_path = here / "evaluation_summary.json"
    remember(evaluation_path)
    evaluation_summary = read(evaluation_path)
    require(evaluation_summary["status"] == "completed"
            and evaluation_summary["preregistration_commit"] == commit,
            "Offline evaluation must finish before this audit")
    require(len(evaluation_summary["checkpoints"]) == 18, "Expected all 18 evaluation checkpoints")
    cells = {}
    for row in data["rows"]:
        cells.setdefault((row["split"], row["N"], row["r"]), []).append(row)
    selected = []
    for cell in sorted(cells):
        selected.extend([cells[cell][0], cells[cell][-1]])
    require(len(selected) == len({r["id"] for r in selected}) == 26, "Expected 26 distinct audit rows")
    result["selection"] = {"rule": "First and last dataset row in every split/N/r cell",
                           "rows_per_checkpoint": len(selected), "cells": len(cells),
                           "row_ids": [r["id"] for r in selected]}
    result["checkpoints"] = []
    saved_calls, saved_macs, tf_targets, max_ce_error = 0, 0, 0, 0.0
    for seed in protocol["seeds"]:
        for phase in range(6):
            result["current_check"] = {"seed": seed, "phase": phase}
            path = (here / "frozen" / f"initial_seed{seed}.npz" if phase == 0 else
                    here / "runs" / f"primary_seed{seed}" / f"phase{phase}.npz")
            checkpoint_sha = remember(path)
            state = load_arrays(path)
            validate_state(state, seed, cumulative[phase])
            state_digest = state_sha(state)
            if phase == 0:
                require(state_digest == manifest["initial_full_state_sha256"][str(seed)],
                        "Initial state binding differs")
            else:
                phase_path = path.with_suffix(".json")
                remember(phase_path)
                phase_record = read(phase_path)
                require(phase_record == summaries[seed]["phases"][phase - 1], "Phase JSON/summary differ")
                require(checkpoint_sha == phase_record["checkpoint_sha256"]
                        and state_digest == phase_record["full_state_sha256"],
                        "Checkpoint differs from recorded phase state")
            eval_path = here / "evaluation" / f"seed{seed}_phase{phase}.json"
            remember(eval_path)
            observed = read(eval_path)
            require(observed["checkpoint_sha256"] == checkpoint_sha
                    and observed["updates"] == cumulative[phase], "Evaluation checkpoint binding")
            indexed = {r["id"]: r for r in observed["records"]}
            require(len(indexed) == len(data["rows"]) == len(observed["records"]),
                    "Evaluation row count or IDs differ")
            require(set(indexed) == {r["id"] for r in data["rows"]}, "Evaluation inventory differs")
            recorded_calls = sum(len(r["generated"]) + r["tf_targets"] for r in indexed.values())
            require(recorded_calls == observed["inference_calls"]
                    and recorded_calls * FORWARD_MAC == observed["inference_dense_MAC"],
                    "Full evaluation call/MAC accounting differs")
            saved_calls += recorded_calls
            saved_macs += recorded_calls * FORWARD_MAC
            start_calls = result["actual_cost"]["neural_forward_calls"]
            audit_rows = []
            for row in selected:
                result["current_check"] = {"seed": seed, "phase": phase, "row_id": row["id"]}
                recomputed = infer_row(state, row, result["actual_cost"])
                archived = indexed[row["id"]]
                for key, value in recomputed.items():
                    if key == "tf_CE_mean":
                        error = abs(value - archived[key])
                        max_ce_error = max(max_ce_error, error)
                        require(error <= 1e-12, "Independent teacher CE differs")
                    else:
                        require(value == archived[key], f"Independent evaluation differs: {key}")
                for key in ("N", "r", "split", "payload_ids"):
                    require(row[key] == archived[key], f"Evaluation metadata differs: {key}")
                tf_targets += recomputed["tf_targets"]
                audit_rows.append({"id": row["id"], "generated": recomputed["generated"],
                                   "tf_predictions": recomputed["tf_predictions"], "all_fields_match": True})
            require(state_sha(state) == state_digest, "Independent inference changed saved arrays")
            result["checkpoints"].append({"seed": seed, "phase": phase, "updates": cumulative[phase],
                "checkpoint_sha256": checkpoint_sha, "full_state_sha256": state_digest,
                "checkpoint_binding_matches": True, "audited_rows": audit_rows,
                "independent_forward_calls": result["actual_cost"]["neural_forward_calls"] - start_calls})
    require(tf_targets == 7164, "Unexpected independent TF target count")
    require(saved_calls == evaluation_summary["inference_calls"]
            and saved_macs == evaluation_summary["inference_dense_MAC"], "Evaluation aggregate costs differ")
    require(evaluation_summary["questions_evaluated"] == 18 * len(data["rows"]),
            "Evaluation aggregate question count differs")
    for path, digest in tracked.items():
        require(sha(path) == digest, f"Read-only audit changed or raced with input: {path.name}")
    result.update({"status": "PASS", "checkpoints_checked": 18, "question_evaluations_checked": 468,
                   "teacher_targets_recomputed": tf_targets, "maximum_absolute_CE_difference": max_ce_error,
                   "all_input_file_hashes_unchanged": True, "input_files_hashed": len(tracked),
                   "archived_seed101_replay_states_match": True,
                   "full_evaluation_cost_accounting_matches": {"calls": saved_calls, "dense_MAC": saved_macs}})
    result.pop("current_check", None)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--experiment-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--prereg-commit", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true",
                        help="Run the audit only after coordinator authorizes completed training/replay")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Audit not executed: --execute is required after training/replay completion")
    require(not args.out.exists(), "Audit output already exists; refusing an implicit rerun")
    start = time.perf_counter()
    result = {"status": "RUNNING", "actor": "ChatGPT Pro / neural_review",
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "audit_source_sha256": sha(Path(__file__)), "manifest_sha256": MANIFEST_SHA,
              "preregistration_commit": args.prereg_commit,
              "actual_cost": {"neural_forward_calls": 0, "optimizer_updates": 0, "Model_imports": 0},
              "scope": "Independent raw-array free/TF inference on first/last row per split/N/r at all18 checkpoints; archived state/replay/file bindings and full eval cost arithmetic. No training or parameter search. Other prediction rows are not independently re-inferred."}
    try:
        audit(args.experiment_dir.resolve(), args.prereg_commit, result)
    except Exception as exc:
        result.update({"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)})
    result["actual_cost"]["dense_forward_MAC"] = result["actual_cost"]["neural_forward_calls"] * FORWARD_MAC
    result["seconds"] = time.perf_counter() - start
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "actual_cost": result["actual_cost"],
                      "out": str(args.out), "seconds": result["seconds"]}), flush=True)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
