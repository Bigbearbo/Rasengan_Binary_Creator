"""Frozen AE1 preparation, fixed-budget training/replay, and offline evaluation."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
import numpy as np
import learner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FROZEN = HERE / "frozen"
RUNS = HERE / "runs"
SOURCE_NAMES = ["protocol.json", "dataset.py", "dataset.json.gz", "data_checks.json",
                "learner.py", "run_trial.py", "preflight.py", "preflight_checks.json"]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    path = Path(path)
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return json.loads(raw.decode("utf-8"))


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def inputs():
    protocol, data = read(HERE / "protocol.json"), read(HERE / "dataset.json.gz")
    rows = {r["id"]: r for r in data["rows"]}
    require(len(rows) == len(data["rows"]), "Duplicate row IDs")
    targets, lookup = [], {}
    for row in data["rows"]:
        if row["split"] != "train":
            continue
        for i, target in enumerate(row["A"] + "S"):
            lookup[row["id"], i] = len(targets)
            targets.append((row["Q"] + row["A"][:i], target, row["id"], i))
    pools = []
    for index, phase in enumerate(data["phases"]):
        pool = [lookup[rid, i] for rid in phase["row_ids"]
                for i in range(len(rows[rid]["A"]) + 1)]
        require(len(pool) == protocol["curriculum"]["targets_per_epoch"][index],
                "Phase target count differs from protocol")
        require(phase["epochs"] == protocol["curriculum"]["epochs"][index],
                "Phase epoch count differs from protocol")
        require(len(pool) == len(set(pool)), "Repeated target within phase pool")
        pools.append(np.array(pool, dtype=np.int32))
    require(len(pools) == 5, "Expected five phases")
    require(sum(len(p) * e for p, e in zip(pools, protocol["curriculum"]["epochs"]))
            == 201840, "Wrong per-student update total")
    return protocol, data, targets, pools


def prepare():
    protocol, data, targets, pools = inputs()
    FROZEN.mkdir(exist_ok=False)
    started = time.perf_counter()
    files, states, schedules = {}, {}, {}
    source_paths = [HERE / name for name in SOURCE_NAMES]
    source_paths += [ROOT / protocol["model"]["reference"],
                     HERE.parent / "20261113_pro_advanced_echo/codec.py"]
    for path in source_paths:
        files[str(path.relative_to(ROOT))] = sha(path)
    require(sha(ROOT / protocol["model"]["reference"])
            == protocol["model"]["reference_sha256"], "Reference source changed")
    for seed in protocol["seeds"]:
        net = learner.new_student(seed)
        require(net.parameters == 10499 and net.t == 0, "Unexpected initial model")
        initial = FROZEN / f"initial_seed{seed}.npz"
        learner.save_state(initial, net)
        saved = learner.load_state(initial)
        require(learner.state_sha(learner.full_state(saved))
                == learner.state_sha(learner.full_state(net)), "Initial state roundtrip")
        states[str(seed)] = learner.state_sha(learner.full_state(net))
        orders = {}
        for index, pool in enumerate(pools):
            rng = np.random.default_rng(seed + 81000 + 1000 * index)
            orders[f"phase{index+1}"] = np.stack([
                rng.permutation(pool) for _ in range(protocol["curriculum"]["epochs"][index])])
            for order in orders[f"phase{index+1}"]:
                require(np.array_equal(np.sort(order), np.sort(pool)), "Schedule multiset changed")
        schedule = FROZEN / f"schedule_seed{seed}.npz"
        with schedule.open("xb") as stream:
            np.savez_compressed(stream, **orders)
        for path in (initial, schedule):
            files[str(path.relative_to(ROOT))] = sha(path)
        schedules[str(seed)] = {key: list(value.shape) for key, value in orders.items()}
    require(Counter(row["split"] for row in data["rows"]) == {"train": 750, "test": 360},
            "Question split counts differ")
    all_prefixes = {}
    for row in data["rows"]:
        for i, target in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:i]
            require(all_prefixes.setdefault(prefix, target) == target, "Conflicting raw target")
    manifest = {
        "id": protocol["id"], "created_utc": utc(), "base_commit": protocol["base_commit"],
        "files_sha256": files, "initial_full_state_sha256": states,
        "schedule_shapes": schedules, "global_train_targets": len(targets),
        "consistent_train_test_teacher_prefixes": len(all_prefixes),
        "source_preflight": "PASS", "preparation_seconds": time.perf_counter() - started,
        "actual_neural_forward_calls": 0, "actual_optimizer_updates": 0,
        "environment": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
                        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
        "note": "Initial states are instantiated and serialized; no neural inference or learning in prepare."
    }
    write_new(HERE / "frozen_manifest.json", manifest)
    print(json.dumps({"prepare": "PASS", "manifest_sha256": sha(HERE / "frozen_manifest.json"),
                      "global_train_targets": len(targets), "updates_per_seed": 201840}), flush=True)


def verify_frozen(commit):
    require(len(commit) == 40 and all(c in "0123456789abcdef" for c in commit),
            "An exact preregistration commit SHA is required")
    manifest = read(HERE / "frozen_manifest.json")
    pinned = dict(manifest["files_sha256"])
    pinned[str((HERE / "frozen_manifest.json").relative_to(ROOT))] = sha(HERE / "frozen_manifest.json")
    for rel, digest in pinned.items():
        require(sha(ROOT / rel) == digest, f"Frozen file changed: {rel}")
        public = subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=ROOT,
                                check=True, capture_output=True).stdout
        require(hashlib.sha256(public).hexdigest() == digest,
                f"Preregistration commit differs: {rel}")
    return manifest


def train(seed, commit, replay=False):
    manifest = verify_frozen(commit)
    protocol, data, targets, pools = inputs()
    require(seed in protocol["seeds"], "Unregistered seed")
    require(not replay or seed == 101, "Only seed101 full replay is prespecified")
    folder = RUNS / (f"replay_seed{seed}" if replay else f"primary_seed{seed}")
    folder.mkdir(parents=True, exist_ok=False)
    net = learner.load_state(FROZEN / f"initial_seed{seed}.npz")
    require(learner.state_sha(learner.full_state(net))
            == manifest["initial_full_state_sha256"][str(seed)], "Wrong initial full state")
    started_utc, start = utc(), time.perf_counter()
    summary = {"seed": seed, "role": "replay" if replay else "primary",
               "preregistration_commit": commit, "started_utc": started_utc, "phases": []}
    archive = np.load(FROZEN / f"schedule_seed{seed}.npz", allow_pickle=False)
    for index, phase in enumerate(data["phases"]):
        phase_start = time.perf_counter()
        epochs = []
        for epoch, order in enumerate(archive[f"phase{index+1}"]):
            loss_sum, correct = 0.0, 0
            for target_index in order:
                prefix, target, _, _ = targets[int(target_index)]
                prediction, loss = net.step(prefix, target)
                require(np.isfinite(loss), "Nonfinite training loss; abort without replacement run")
                loss_sum += loss
                correct += prediction == target
            epochs.append({"epoch": epoch + 1, "updates": net.t,
                           "targets": len(order), "correct_before_step": int(correct),
                           "loss_sum": loss_sum})
            print(json.dumps({"seed": seed, "role": summary["role"], "phase": index + 1,
                              "epoch": epoch + 1, "updates": net.t}), flush=True)
        require(net.t == protocol["curriculum"]["cumulative_updates"][index], "Update budget mismatch")
        require(all(np.isfinite(a).all() for arrays in (net.p, net.m, net.v) for a in arrays),
                "Nonfinite checkpoint; abort without replacement run")
        require(net.L == 80 and net.H == 64 and not net.events, "Unexpected model growth")
        require(net.inference_calls == 0, "Performance evaluation occurred during training")
        path = folder / f"phase{index+1}.npz"
        learner.save_state(path, net)
        record = {"phase": index + 1, "id": phase["id"], "updates": net.t,
                  "train_dense_MAC": net.train_macs, "epochs": epochs,
                  "full_state_sha256": learner.state_sha(learner.full_state(net)),
                  "checkpoint_sha256": sha(path), "seconds": time.perf_counter() - phase_start}
        write_new(folder / f"phase{index+1}.json", record)
        summary["phases"].append(record)
    archive.close()
    summary.update({"finished_utc": utc(), "seconds": time.perf_counter() - start,
                    "updates": net.t, "train_dense_MAC": net.train_macs,
                    "actual_inference_calls_during_training": net.inference_calls,
                    "status": "completed"})
    write_new(folder / "summary.json", summary)
    print(json.dumps({"seed": seed, "role": summary["role"], "status": "completed",
                      "updates": net.t, "seconds": summary["seconds"]}), flush=True)


def verify_replay():
    primary, replay = [read(RUNS / f"{role}_seed101/summary.json") for role in ("primary", "replay")]
    require(primary["preregistration_commit"] == replay["preregistration_commit"], "Replay protocol differs")
    compared = []
    for p, r in zip(primary["phases"], replay["phases"]):
        for field in ("phase", "id", "updates", "train_dense_MAC", "epochs", "full_state_sha256"):
            require(p[field] == r[field], f"Replay differs at phase{p['phase']} field{field}")
        compared.append(p["phase"])
    require(compared == [1, 2, 3, 4, 5], "Incomplete replay")
    result = {"status": "PASS", "seed": 101, "phase_endpoints_compared": compared,
              "epoch_statistics_exact": True, "complete_learning_and_metadata_states_exact": True,
              "replay_updates": replay["updates"], "replay_train_dense_MAC": replay["train_dense_MAC"],
              "finished_utc": utc(), "scope": "Only seed101 full replay; no new independent student."}
    write_new(HERE / "replay_check.json", result)
    return result


def evaluate_all(commit):
    verify_frozen(commit)
    protocol, data, _, _ = inputs()
    for seed in protocol["seeds"]:
        require(read(RUNS / f"primary_seed{seed}/summary.json")["status"] == "completed",
                "All three trajectories must finish before performance evaluation")
    require(read(HERE / "replay_check.json")["status"] == "PASS", "Replay not verified")
    folder = HERE / "evaluation"
    folder.mkdir(exist_ok=False)
    start, started_utc = time.perf_counter(), utc()
    summaries, calls, macs = [], 0, 0
    for seed in protocol["seeds"]:
        for phase in range(6):
            path = FROZEN / f"initial_seed{seed}.npz" if phase == 0 else RUNS / f"primary_seed{seed}/phase{phase}.npz"
            net = learner.load_state(path)
            records = learner.evaluate(net, data["rows"])
            metrics = learner.metrics(records)
            taught = {rid for p in data["phases"][:phase] for rid in p["row_ids"]}
            result = {"seed": seed, "phase": phase, "updates": net.t,
                      "checkpoint_sha256": sha(path), "metrics": metrics,
                      "taught_so_far_metrics": learner.metrics([r for r in records if r["id"] in taught]),
                      "not_yet_taught_train_inventory_metrics": learner.metrics([
                          r for r in records if r["split"] == "train" and r["id"] not in taught]),
                      "inference_calls": net.inference_calls, "inference_dense_MAC": net.inference_macs,
                      "records": records}
            write_new(folder / f"seed{seed}_phase{phase}.json", result)
            summaries.append({k: v for k, v in result.items() if k != "records"})
            calls += net.inference_calls
            macs += net.inference_macs
            print(json.dumps({"evaluation_seed": seed, "phase": phase,
                              "inference_calls": net.inference_calls}), flush=True)
    result = {"status": "completed", "started_utc": started_utc, "finished_utc": utc(),
              "seconds": time.perf_counter() - start, "checkpoints": summaries,
              "inference_calls": calls, "inference_dense_MAC": macs,
              "questions_evaluated": len(data["rows"]) * len(summaries),
              "optimizer_updates": 0, "preregistration_commit": commit}
    write_new(HERE / "evaluation_summary.json", result)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=("prepare", "train", "replay", "verify-replay", "evaluate"))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--prereg-commit")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command in ("train", "replay"):
        train(args.seed, args.prereg_commit, replay=args.command == "replay")
    elif args.command == "verify-replay":
        print(json.dumps(verify_replay()), flush=True)
    else:
        evaluate_all(args.prereg_commit)


if __name__ == "__main__":
    main()
