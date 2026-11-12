"""Freeze or preflight by explicit mode. Formal training requires an approved hash.

--execute runs all three fixed primary trajectories, all three independent
target-loop replays, then (and only then) evaluates the heldout combinations.
"""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time

if sys.flags.optimize:
    raise RuntimeError("Optimized Python (-O/-OO) is disabled: validation assertions are required")

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np
import dataset as data
import learner

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "protocol.json"
CORE_FILES = ("dataset.py", "learner.py", "run_trial.py", "test_engineering.py", "protocol.json")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def protocol():
    p = read(PROTOCOL)
    assert p["id"] == "PRO-UR1-ACK-20261113"
    assert p["seeds"] == [101, 202, 303] and p["epochs"] == 128
    assert p["paths"] == [list(path) for path in data.PATHS]
    assert p["target_widths"] == list(data.WIDTHS)
    assert p["heldout_width_by_path"] == list(data.HELD_WIDTHS) and p["k"] == 1
    assert p["model"] == {"L": 80, "H": 64, "parameters": 10499, "generation_cap_including_STOP": 24}
    assert p["checkpoint_epochs"] == [0, 16, 32, 64, 96, 128]
    assert p["schedule_seed_offset"] == 61000
    assert p["targets_per_epoch"] == 212 and p["targets_per_seed"] == 27136
    assert p["lessons_per_seed"] == 1536
    assert p["training_dense_MAC_per_target"] == learner.H * (4 * learner.L + 9) == 21056
    assert p["training_dense_MAC_per_seed"] == 571375616
    assert p["primary_targets_all_seeds"] == 81408
    assert p["primary_training_dense_MAC_all_seeds"] == 1714126848
    assert p["including_replay_targets"] == 162816
    assert p["including_replay_training_dense_MAC"] == 3428253696
    return p


def build_manifest():
    p = protocol()
    rows = data.make_rows()
    checks = data.validate_rows(rows)
    curricula = data.make_curricula(rows, p["seeds"], p["epochs"], p["schedule_seed_offset"])
    files = [HERE / name for name in CORE_FILES] + [data.CODEC_PATH, learner.REFERENCE_PATH]
    hashes = {str(path.relative_to(data.REPO)): data.file_sha(path) for path in files}
    return {"id": p["id"], "status": "frozen_before_formal_neural_training",
            "protocol": p, "protocol_sha256": data.file_sha(PROTOCOL),
            "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                        "OPENBLAS_NUM_THREADS": os.environ["OPENBLAS_NUM_THREADS"],
                        "OMP_NUM_THREADS": os.environ["OMP_NUM_THREADS"]},
            "source_hashes": hashes, "data_checks": checks,
            "rows": rows, "data_sha256": data.json_sha(rows), "curricula": curricula,
            "exposure": data.exposure_ledger(rows, p["epochs"])}


def validate_manifest(path, approved_sha):
    if not approved_sha or data.file_sha(path) != approved_sha:
        raise ValueError("Explicit approved manifest SHA256 is missing or differs")
    saved = read(path)
    if saved != build_manifest():
        raise ValueError("Frozen source, protocol, data, curriculum, or runtime differs")
    return saved


def preflight():
    """Six synthetic update calls only; no formal student or heldout neural score."""
    p = protocol()
    rows = data.make_rows()
    checks = data.validate_rows(rows)
    curricula = data.make_curricula(rows, p["seeds"], p["epochs"], p["schedule_seed_offset"])
    by_id = {row["id"]: row for row in rows}
    for item in curricula.values():
        assert sum(by_id[row_id]["target_updates"] for order in item["epochs"] for row_id in order) == 27136
    primary = learner.new_student(910013)
    replay = copy.deepcopy(primary)
    with tempfile.TemporaryDirectory(prefix="ur1-engineering-") as tmp:
        synthetic = {"id": "engineering", "Q": "010", "A": "01", "target_updates": 3}
        trace_path = Path(tmp) / "targets.jsonl.gz"
        trace = Trace(trace_path, False)
        one_lesson(primary, synthetic, 1, trace, False)
        primary_trace = trace.close()
        trace = Trace(trace_path, True)
        one_lesson(replay, synthetic, 1, trace, True)
        assert trace.close() == primary_trace
        assert learner.reference.equal_state(learner.full_state(primary), learner.full_state(replay))
        path = Path(tmp) / "state.npz"
        learner.save_state(path, primary)
        restored = learner.load_state(path)
        assert learner.reference.equal_state(learner.full_state(primary), learner.full_state(restored))
    constant = learner.new_student(910014)
    constant.p[2][:] = 0
    constant.p[3][:] = [1, 0, -1]
    generated = learner.generate(constant, "010")
    assert generated["tokens"] == "0" * 24 and generated["cap_exhausted"]
    assert learner.generate(constant, "0" * 81)["overflow"]
    constant.p[3][:] = [0, 0, 1]
    assert learner.generate(constant, "010")["tokens"] == "S"
    assert primary.parameters == 10499
    assert sum(a.nbytes for label in ("p", "m", "v", "birth") for a in getattr(primary, label)) == 209980
    return {"status": "PASS", "data": checks, "synthetic_optimizer_update_calls": 6,
            "synthetic_seed": 910013, "formal_student_updates": 0,
            "formal_heldout_neural_evaluations": 0,
            "native_lesson_vs_independent_target_loop": "exact",
            "complete_state_save_load": "exact", "generation_cap_and_overflow": "PASS"}


class Trace:
    def __init__(self, path, replay):
        self.stream = gzip.open(path, "rt" if replay else "xt", encoding="utf-8", newline="\n")
        self.replay = replay
        self.count = 0
        self.digest = hashlib.sha256()

    def observe(self, record):
        line = data.canonical(record) + "\n"
        if self.replay:
            assert self.stream.readline() == line, f"Target replay mismatch at {self.count}"
        else:
            self.stream.write(line)
        self.digest.update(line.encode())
        self.count += 1

    def close(self):
        if self.replay:
            assert not self.stream.readline(), "Replay omitted target records"
        self.stream.close()
        return {"targets": self.count, "uncompressed_stream_sha256": self.digest.hexdigest()}


def one_lesson(net, row, epoch, trace, replay):
    q, a = row["Q"], row["A"]

    def observe(position, prediction, loss):
        assert np.isfinite(loss)
        trace.observe({"epoch": epoch, "row_id": row["id"], "position": position,
                       "prefix": q + a[:position], "target": (a + "S")[position],
                       "prediction": prediction, "loss": loss, "global_update": net.t,
                       "train_dense_MAC": net.train_macs,
                       "full_state_sha256": learner.state_sha(learner.full_state(net))})

    if replay:
        for position, target in enumerate(a + "S"):
            prediction, loss = net.step(q + a[:position], target)
            observe(position, prediction, loss)
        return
    native, position = net.step, 0

    def observed_step(prefix, target):
        nonlocal position
        assert prefix == q + a[:position] and target == (a + "S")[position]
        assert set(prefix) <= {"0", "1"} and len(prefix) <= net.L
        result = native(prefix, target)
        observe(position, *result)
        position += 1
        return result

    net.step = observed_step
    try:
        net.lesson(q, a)
    finally:
        net.step = native
    assert position == row["target_updates"]


def train_seed(manifest, seed, output, replay=False):
    p = manifest["protocol"]
    folder = output / f"seed{seed}"
    if not replay:
        folder.mkdir()
    net = learner.new_student(seed)
    if replay:
        assert learner.reference.equal_state(learner.full_state(net), learner.full_state(learner.load_state(folder / "initial-state.npz")))
    else:
        learner.save_state(folder / "initial-state.npz", net)
    train = [row for row in manifest["rows"] if row["split"] == "train"]
    by_id = {row["id"]: row for row in train}
    trace_path = folder / "targets.jsonl.gz"
    trace = Trace(trace_path, replay)
    curve = []
    started = time.perf_counter()

    def checkpoint(epoch):
        for label in ("p", "m", "v"):
            assert all(a.dtype == np.float32 and np.isfinite(a).all() for a in getattr(net, label))
        assert net.t == epoch * 212 and net.train_macs == net.t * 21056
        truth = learner.evaluate(net, train)
        record = {"epoch": epoch, "target_updates": net.t, "training_dense_MAC": net.train_macs,
                  "metrics": learner.metrics(truth), "state_sha256": learner.state_sha(learner.full_state(net))}
        curve.append(record)
        state_path, truth_path = folder / f"state-{epoch:03}.npz", folder / f"train-truth-{epoch:03}.json"
        if replay:
            assert learner.reference.equal_state(learner.full_state(net), learner.full_state(learner.load_state(state_path)))
            assert truth == read(truth_path)
        else:
            learner.save_state(state_path, net)
            write(truth_path, truth)

    try:
        checkpoint(0)
        for epoch, order in enumerate(manifest["curricula"][str(seed)]["epochs"], 1):
            for row_id in order:
                one_lesson(net, by_id[row_id], epoch, trace, replay)
            if epoch in p["checkpoint_epochs"]:
                checkpoint(epoch)
                print(data.canonical({"mode": "replay" if replay else "primary", "seed": seed,
                                      "epoch": epoch, "updates": net.t}), flush=True)
        trace_result = trace.close()
        assert net.t == p["targets_per_seed"] and trace_result["targets"] == net.t
        assert net.train_macs == p["training_dense_MAC_per_seed"]
        summary = {"seed": seed, "targets": net.t, "lessons": p["lessons_per_seed"],
                   "parameters": net.parameters, "training_dense_MAC": net.train_macs,
                   "training_diagnostic_inference_calls": net.inference_calls,
                   "training_diagnostic_dense_MAC": net.inference_macs,
                   "state_sha256": learner.state_sha(learner.full_state(net)),
                   "trace": trace_result, "trace_file_sha256": data.file_sha(trace_path)}
        if replay:
            assert summary == read(folder / "training-summary.json")
            assert curve == read(folder / "curve.json")
            assert learner.reference.equal_state(learner.full_state(net), learner.full_state(learner.load_state(folder / "final-state.npz")))
        else:
            learner.save_state(folder / "final-state.npz", net)
            write(folder / "training-summary.json", summary)
            write(folder / "curve.json", curve)
        return {"seed": seed, "mode": "replay" if replay else "primary", "seconds": time.perf_counter() - started}
    except Exception:
        trace.stream.close()
        learner.save_state(folder / ("replay-failure-state.npz" if replay else "primary-failure-state.npz"), net)
        raise


def execute(manifest_path, approved_sha, output):
    manifest = validate_manifest(manifest_path, approved_sha)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "manifest.json", manifest)
    write(output / "execution-start.json", {"manifest_sha256": approved_sha,
                                           "runtime": manifest["runtime"], "formal_started": True})
    started = time.perf_counter()
    timings = []
    try:
        for replay in (False, True):
            for seed in manifest["protocol"]["seeds"]:
                timings.append(train_seed(manifest, seed, output, replay))
        validate_manifest(manifest_path, approved_sha)
        # No heldout neural call occurs until all fixed trajectories and replays finish.
        students = []
        for seed in manifest["protocol"]["seeds"]:
            folder = output / f"seed{seed}"
            offline_curve = []
            for epoch in manifest["protocol"]["checkpoint_epochs"]:
                state_path = folder / f"state-{epoch:03}.npz"
                net = learner.load_state(state_path)
                before = learner.state_sha(net.state())
                calls, macs = net.inference_calls, net.inference_macs
                truth = learner.evaluate(net, manifest["rows"])
                assert before == learner.state_sha(net.state())
                score = learner.metrics(truth)
                truth_name = "final-truth.json" if epoch == 128 else f"offline-truth-{epoch:03}.json"
                write(folder / truth_name, truth)
                offline_curve.append({"epoch": epoch, "target_updates": net.t,
                                      "training_dense_MAC": net.train_macs, "metrics": score,
                                      "truth_file": truth_name, "checkpoint_file": state_path.name,
                                      "checkpoint_sha256": data.file_sha(state_path),
                                      "diagnostic_inference_calls": net.inference_calls - calls,
                                      "diagnostic_dense_MAC": net.inference_macs - macs})
            # The last offline point is the final evaluation; no second inference pass.
            assert offline_curve[-1]["epoch"] == 128
            write(folder / "offline-curve.json", offline_curve)
            write(folder / "final-failures.json", [row for row in truth if not row["whole_correct"]])
            students.append({"seed": seed, "metrics": score,
                             "strong_gate": score["train"]["whole_correct"] == 12 and score["heldout"]["whole_correct"] == 6,
                             "offline_diagnostic_inference_calls": sum(point["diagnostic_inference_calls"] for point in offline_curve),
                             "offline_diagnostic_dense_MAC": sum(point["diagnostic_dense_MAC"] for point in offline_curve),
                             "final_diagnostic_inference_calls_subset": offline_curve[-1]["diagnostic_inference_calls"],
                             "final_diagnostic_dense_MAC_subset": offline_curve[-1]["diagnostic_dense_MAC"],
                             "checkpoint_sha256": data.file_sha(folder / "final-state.npz")})
        training_summaries = [read(output / f"seed{seed}" / "training-summary.json")
                              for seed in manifest["protocol"]["seeds"]]
        diagnostic_macs = sum(item["training_diagnostic_dense_MAC"] for item in training_summaries)
        summary = {"id": manifest["id"], "status": "complete", "author": "ChatGPT Pro",
                   "manifest_sha256": approved_sha, "students": students,
                   "strong_gate_all_three": all(row["strong_gate"] for row in students),
                   "primary_targets": 81408, "replay_targets": 81408,
                   "primary_training_dense_MAC": 1714126848,
                   "replay_training_dense_MAC": 1714126848,
                   "primary_training_diagnostic_dense_MAC": diagnostic_macs,
                   "replay_training_diagnostic_dense_MAC": diagnostic_macs,
                   "offline_evaluation_dense_MAC": sum(item["offline_diagnostic_dense_MAC"] for item in students),
                   "offline_evaluation_inference_calls": sum(item["offline_diagnostic_inference_calls"] for item in students),
                   "p_m_v_birth_array_bytes_per_student": 209980,
                   "complete_trajectories": 3, "exact_replays": 3,
                   "scope": manifest["protocol"]["scope"],
                   "nvidia_status": manifest["protocol"]["nvidia_status"], "nvidia_calls": 0}
        write(output / "summary.json", summary)
        write(output / "timing.json", {"trajectories": timings, "total_seconds": time.perf_counter() - started,
                                      "scope": "training, traces, checkpoints, replay and diagnostic evaluation; not pure kernel time"})
        print(data.canonical(summary), flush=True)
    except Exception as error:
        write(output / "failure.json", {"status": "incomplete", "error_type": type(error).__name__,
                                        "message": str(error), "timings_completed": timings})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--make-manifest", type=Path)
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--approved-manifest-sha")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.preflight:
        print(data.canonical(preflight()))
    elif args.make_manifest:
        manifest = build_manifest()
        write(args.make_manifest, manifest)
        frozen = {"manifest_sha256": data.file_sha(args.make_manifest),
                  "source_hashes": manifest["source_hashes"], "data_sha256": manifest["data_sha256"],
                  "curriculum_sha256": {seed: item["curriculum_sha256"] for seed, item in manifest["curricula"].items()}}
        write(args.make_manifest.with_name("source-freeze.json"), frozen)
        print(data.canonical(frozen))
    else:
        if args.manifest is None or args.out is None or not args.approved_manifest_sha:
            parser.error("--execute requires --manifest, --approved-manifest-sha and a new --out")
        execute(args.manifest, args.approved_manifest_sha, args.out)


if __name__ == "__main__":
    main()
