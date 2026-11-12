"""One preregistered UR1 target-order diagnostic; original scientific files stay intact.

--preflight performs synthetic engineering only. --make-manifest freezes the
actual pool, every target order, and copies of the three control initial states.
--execute requires the exact approved manifest SHA and a new output directory.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time

if sys.flags.optimize:
    raise RuntimeError("Optimized Python is disabled: exact validation assertions are required")
sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "protocol.json"
ORIGINAL_DIR = Path("experiments/spiral_neural/20261113_pro_notice_learning")
CONTROL_MANIFEST_SHA = "d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0"
LOCAL_SOURCES = ("run_target_order.py", "protocol.json", "test_target_order.py")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha(value):
    return sha_bytes(canonical(value).encode("utf-8"))


def json_file_sha(value):
    text = json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    return sha_bytes(text.encode("utf-8"))


def array_sha(value):
    return sha_bytes(canonical([value.dtype.str, list(value.shape)]).encode("utf-8") + value.tobytes(order="C"))


def runtime():
    return {"python": platform.python_version(), "numpy": np.__version__,
            "OPENBLAS_NUM_THREADS": os.environ["OPENBLAS_NUM_THREADS"],
            "OMP_NUM_THREADS": os.environ["OMP_NUM_THREADS"]}


def protocol():
    p = read(PROTOCOL)
    assert p["id"] == "CODEX-UR1-TARGET-ORDER-20261113"
    assert p["seeds"] == [101, 202, 303] and p["epochs"] == 128
    assert p["checkpoint_epochs"] == [0, 16, 32, 64, 96, 128]
    assert p["control_manifest_sha256"] == CONTROL_MANIFEST_SHA
    assert p["model"] == {"L": 80, "H": 64, "parameters": 10499, "generation_cap_including_STOP": 24}
    assert p["target_schedule"]["seed_offset"] == 81000
    assert p["target_schedule"]["targets_per_epoch"] == 212
    assert p["target_schedule"]["targets_per_epoch_by_width"] == {"4": 68, "5": 68, "6": 76}
    assert p["target_schedule"]["STOP_targets_per_epoch"] == 12
    assert p["targets_per_seed"] == 27136 and p["training_dense_MAC_per_target"] == 21056
    assert p["training_dense_MAC_per_seed"] == 571375616
    assert p["primary_targets_all_seeds"] == 81408
    assert p["primary_training_dense_MAC_all_seeds"] == 1714126848
    assert p["including_replay_targets"] == 162816
    assert p["including_replay_training_dense_MAC"] == 3428253696
    assert p["fixed_control"] == {"train_whole_correct": [7, 5, 5], "train_address_correct": [7, 6, 6],
                                  "heldout_whole_correct": [0, 0, 0]}
    return p


def normalized_hashes(hashes):
    return {name.replace("\\", "/"): value for name, value in hashes.items()}


def load_original(source_root):
    """Verify all seven sources against the original pinned manifest before import."""
    source_root = Path(source_root).resolve()
    folder = source_root / ORIGINAL_DIR
    frozen_path = folder / "frozen_manifest.json"
    assert file_sha(frozen_path) == CONTROL_MANIFEST_SHA, "Original manifest differs"
    frozen = read(frozen_path)
    hashes = normalized_hashes(frozen["source_hashes"])
    assert len(hashes) == 7
    for name, expected in hashes.items():
        path = (source_root / name).resolve()
        assert path.is_relative_to(source_root) and file_sha(path) == expected, name
    # Original imports are intentionally preserved, including their own source guards.
    for name in ("dataset", "learner", "run_trial"):
        if name in sys.modules:
            assert Path(sys.modules[name].__file__).resolve() == folder / f"{name}.py", "Conflicting original module"
            continue
        spec = importlib.util.spec_from_file_location(name, folder / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    data, learner, trial = (sys.modules[name] for name in ("dataset", "learner", "run_trial"))
    assert data.make_rows() == frozen["rows"]
    assert normalized_hashes(trial.build_manifest()["source_hashes"]) == hashes
    assert runtime() == frozen["runtime"], "Runtime differs from fixed control"
    return {"root": source_root, "frozen": frozen, "hashes": hashes,
            "data": data, "learner": learner, "trial": trial}


def target_pool(rows):
    pool = []
    for row in rows:
        if row["split"] != "train":
            continue
        for position, target in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            assert prefix and set(prefix) <= {"0", "1"} and len(prefix) <= 80
            pool.append({"index": len(pool), "row_id": row["id"], "position": position,
                         "prefix": prefix, "target": target, "target_n": row["target_n"]})
    return pool


def target_multiset(pool):
    return Counter((item["prefix"], item["target"]) for item in pool)


def make_schedules(pool, seeds, epochs, seed_offset):
    orders, descriptions = {}, {}
    expected = np.arange(len(pool), dtype="<i8")
    for seed in seeds:
        rng = np.random.default_rng(seed + seed_offset)
        sequence = np.stack([rng.permutation(len(pool)) for _ in range(epochs)]).astype("<i8")
        assert all(np.array_equal(np.sort(order), expected) for order in sequence)
        digest = hashlib.sha256()
        for order in sequence:
            for index in order:
                item = pool[int(index)]
                digest.update((canonical([item["prefix"], item["target"]]) + "\n").encode("utf-8"))
        key = f"seed{seed}"
        orders[key] = sequence
        descriptions[str(seed)] = {"schedule_seed": seed + seed_offset, "file": "schedules.npz", "key": key,
                                   "shape": list(sequence.shape), "dtype": sequence.dtype.str,
                                   "array_sha256": array_sha(sequence), "orders_json_sha256": json_sha(sequence.tolist()),
                                   "raw_teacher_target_stream_sha256": digest.hexdigest(),
                                   "final_schedule_RNG": copy.deepcopy(rng.bit_generator.state)}
    buffer = io.BytesIO()
    np.savez(buffer, **orders)
    return orders, descriptions, buffer.getvalue()


def control_inputs(control_root, seeds, checkpoints):
    """Only the 12 public inputs consumed by this diagnostic, without old traces."""
    names = ["manifest.json", "summary.json", "codex-execution-provenance.json"]
    for seed in seeds:
        base = f"seed{seed}/"
        names.extend(base + name for name in ("initial-state.npz", "curve.json", "offline-curve.json"))
    return {name: file_sha(Path(control_root) / name) for name in names}


def inspect_control(original, control_root, p):
    learner, data = original["learner"], original["data"]
    control_root = Path(control_root).resolve()
    assert file_sha(control_root / "manifest.json") == CONTROL_MANIFEST_SHA
    assert read(control_root / "manifest.json") == original["frozen"]
    summary = read(control_root / "summary.json")
    assert summary["status"] == "complete" and summary["exact_replays"] == 3
    assert summary["complete_trajectories"] == 3 and summary["manifest_sha256"] == CONTROL_MANIFEST_SHA
    provenance = read(control_root / "codex-execution-provenance.json")
    assert provenance["execution_author"] == "Codex" and provenance["status"] == "complete"
    students = {}
    for ordinal, seed in enumerate(p["seeds"]):
        folder = control_root / f"seed{seed}"
        initial = learner.load_state(folder / "initial-state.npz")
        assert learner.reference.equal_state(learner.full_state(initial), learner.full_state(learner.new_student(seed)))
        assert initial.t == initial.train_macs == initial.inference_macs == initial.inference_calls == 0
        assert initial.parameters == 10499 and initial.events == []
        assert all(a.dtype == np.float32 and np.isfinite(a).all() for label in ("p", "m", "v") for a in getattr(initial, label))
        assert all(not np.any(a) for label in ("m", "v", "birth") for a in getattr(initial, label))
        assert sum(a.nbytes for label in ("p", "m", "v", "birth") for a in getattr(initial, label)) == 209980
        curve, offline = read(folder / "curve.json"), read(folder / "offline-curve.json")
        assert [x["epoch"] for x in curve] == [x["epoch"] for x in offline] == p["checkpoint_epochs"]
        points = {}
        state_digests = {}
        for point, offline_point in zip(curve, offline, strict=True):
            epoch = point["epoch"]
            assert point["metrics"]["train"] == offline_point["metrics"]["train"]
            assert offline_point["metrics"]["train"]["total"] == 12
            assert offline_point["metrics"]["train"]["teacher_targets"] == 212
            assert offline_point["metrics"]["heldout"]["total"] == 6
            assert offline_point["metrics"]["heldout"]["teacher_targets"] == 106
            assert point["target_updates"] == epoch * 212 and point["training_dense_MAC"] == epoch * 212 * 21056
            assert offline_point["target_updates"] == point["target_updates"]
            assert offline_point["training_dense_MAC"] == point["training_dense_MAC"]
            assert len(point["state_sha256"]) == 64
            state_digests[str(epoch)] = point["state_sha256"]
            points[str(epoch)] = offline_point["metrics"]
        final = points["128"]
        assert final["train"]["whole_correct"] == p["fixed_control"]["train_whole_correct"][ordinal]
        assert final["train"]["address_correct"] == p["fixed_control"]["train_address_correct"][ordinal]
        assert final["heldout"]["whole_correct"] == p["fixed_control"]["heldout_whole_correct"][ordinal]
        assert next(x for x in summary["students"] if x["seed"] == seed)["metrics"] == final
        students[str(seed)] = {"initial_state_sha256": learner.state_sha(learner.full_state(initial)),
                               "initial_file": f"initial-state-seed{seed}.npz", "points": points,
                               "checkpoint_full_state_sha256": state_digests}
    return {"manifest_sha256": CONTROL_MANIFEST_SHA, "execution_author": "Codex",
            "attribution": "Verified Windows replication of Pro's fixed original-order experiment; not new independent scientific evidence",
            "prior_audit_scope": "Coordinator separately verified all original control truth/state checkpoints. This driver consumes only original initial states and six-point curve metrics/digests; it does not repeat that inference audit or require the old checkpoint/truth archives",
            "input_hashes": control_inputs(control_root, p["seeds"], p["checkpoint_epochs"]), "students": students}


def build_plan(source_root, control_root):
    p = protocol()
    original = load_original(source_root)
    data = original["data"]
    rows = original["frozen"]["rows"]
    checks = data.validate_rows(rows)
    pool = target_pool(rows)
    assert len(pool) == 212 and sum(x["target"] == "S" for x in pool) == 12
    assert {str(width): sum(x["target_n"] == width for x in pool) for width in (4, 5, 6)} == {"4": 68, "5": 68, "6": 76}
    by_id = {row["id"]: row for row in rows}
    expected = target_multiset(pool)
    for course in original["frozen"]["curricula"].values():
        for order in course["epochs"]:
            assert Counter((by_id[row_id]["Q"] + by_id[row_id]["A"][:i], target)
                           for row_id in order for i, target in enumerate(by_id[row_id]["A"] + "S")) == expected
    orders, descriptions, schedule_bytes = make_schedules(pool, p["seeds"], p["epochs"], p["target_schedule"]["seed_offset"])
    control = inspect_control(original, control_root, p)
    manifest = {"schema": "sle-target-order-manifest-v1", "id": p["id"],
                "status": "frozen_before_target_order_formal_training", "author": "Codex",
                "protocol": p, "runtime": runtime(), "protocol_sha256": file_sha(PROTOCOL),
                "local_source_hashes": {name: file_sha(HERE / name) for name in LOCAL_SOURCES},
                "original_source_hashes": original["hashes"], "original_manifest_sha256": CONTROL_MANIFEST_SHA,
                "data_checks": checks, "rows": rows, "data_sha256": json_sha(rows),
                "target_pool": pool, "target_pool_sha256": json_sha(pool),
                "target_pool_file": "target-pool.json", "target_pool_file_sha256": json_file_sha(pool),
                "schedules": descriptions,
                "schedules_file_sha256": sha_bytes(schedule_bytes), "control": control,
                "original_lesson_exposure_ledger": data.exposure_ledger(rows, p["epochs"]),
                "exposure": {"per_epoch_teacher_prefix_bit_elements": sum(len(item["prefix"]) for item in pool),
                             "per_seed_teacher_prefix_bit_elements": p["epochs"] * sum(len(item["prefix"]) for item in pool),
                             "per_epoch_labels": dict(sorted(Counter(item["target"] for item in pool).items())),
                             "per_seed_labels": {label: count * p["epochs"] for label, count in sorted(Counter(item["target"] for item in pool).items())},
                             "each_original_training_row_target_multiset_repeated_epochs": p["epochs"],
                             "heldout_training_targets": 0,
                             "note": "Original lesson ledger counts source examples; shuffled targets are individual optimizer calls, not contiguous lessons. Actual prefix bit/label exposure is unchanged by permutation"},
                "formal_targets_before_manifest": 0, "external_model_calls": 0}
    return original, manifest, orders, schedule_bytes


def make_manifest(source_root, control_root, output):
    _, manifest, _, schedule_bytes = build_plan(source_root, control_root)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "target-pool.json", manifest["target_pool"])
    with (output / "schedules.npz").open("xb") as stream:
        stream.write(schedule_bytes)
    for seed in manifest["protocol"]["seeds"]:
        target = output / manifest["control"]["students"][str(seed)]["initial_file"]
        with target.open("xb") as stream:
            stream.write((Path(control_root) / f"seed{seed}/initial-state.npz").read_bytes())
    write(output / "manifest.json", manifest)
    frozen = {"manifest_sha256": file_sha(output / "manifest.json"), "author": "Codex",
              "local_source_hashes": manifest["local_source_hashes"], "original_source_hashes": manifest["original_source_hashes"],
              "target_pool_sha256": manifest["target_pool_sha256"], "target_pool_file_sha256": manifest["target_pool_file_sha256"],
              "schedules_file_sha256": manifest["schedules_file_sha256"],
              "schedule_stream_sha256": {seed: value["raw_teacher_target_stream_sha256"] for seed, value in manifest["schedules"].items()},
              "formal_updates": 0, "external_model_calls": 0}
    write(output / "source-freeze.json", frozen)
    return frozen


def validate_manifest(source_root, control_root, path, approved_sha):
    path = Path(path).resolve()
    assert approved_sha and file_sha(path) == approved_sha, "Explicit approved manifest SHA is missing or differs"
    saved = read(path)
    original, actual, generated, _ = build_plan(source_root, control_root)
    assert saved == actual, "Source, control, runtime, protocol, data or schedule differs"
    assert read(path.parent / "target-pool.json") == saved["target_pool"]
    assert file_sha(path.parent / "target-pool.json") == saved["target_pool_file_sha256"]
    assert file_sha(path.parent / "schedules.npz") == saved["schedules_file_sha256"]
    with np.load(path.parent / "schedules.npz", allow_pickle=False) as archive:
        assert set(archive.files) == set(generated)
        saved_orders = {}
        for name, order in generated.items():
            assert np.array_equal(order, archive[name]) and archive[name].dtype.str == "<i8"
            saved_orders[name] = archive[name].copy()
    for seed in saved["protocol"]["seeds"]:
        initial = path.parent / saved["control"]["students"][str(seed)]["initial_file"]
        assert file_sha(initial) == saved["control"]["input_hashes"][f"seed{seed}/initial-state.npz"]
        net = original["learner"].load_state(initial)
        assert original["learner"].state_sha(original["learner"].full_state(net)) == saved["control"]["students"][str(seed)]["initial_state_sha256"]
    return original, saved, saved_orders


def apply_target(net, item, epoch, ordinal, trace, learner):
    assert set(item["prefix"]) <= {"0", "1"} and 0 < len(item["prefix"]) <= net.L
    prediction, loss = net.step(item["prefix"], item["target"])
    assert np.isfinite(loss)
    trace.observe({"epoch": epoch, "epoch_target_ordinal_zero_based": ordinal, "pool_index": item["index"],
                   "row_id": item["row_id"], "position": item["position"], "prefix": item["prefix"],
                   "target": item["target"], "prediction": prediction, "loss": loss,
                   "global_update": net.t, "train_dense_MAC": net.train_macs,
                   "inference_calls": net.inference_calls, "inference_dense_MAC": net.inference_macs,
                   "full_state_sha256": learner.state_sha(learner.full_state(net))})
    return prediction, loss


def preflight(source_root, control_root, output):
    original, manifest, orders, schedule_bytes = build_plan(source_root, control_root)
    learner, trial = original["learner"], original["trial"]
    before_source = manifest["original_source_hashes"].copy()
    before_control = manifest["control"]["input_hashes"].copy()
    pool = target_pool([{"id": "synthetic-only", "split": "train", "Q": "010", "A": "01", "target_n": 1}])
    tiny, _, _ = make_schedules(pool, [910021], 1, 81000)
    order = tiny["seed910021"][0]
    primary = learner.new_student(910021)
    replay = copy.deepcopy(primary)
    with tempfile.TemporaryDirectory(prefix="target-order-synthetic-") as temporary:
        folder = Path(temporary)
        trace_path = folder / "targets.jsonl.gz"
        trace = trial.Trace(trace_path, False)
        for ordinal, index in enumerate(order):
            apply_target(primary, pool[int(index)], 1, ordinal, trace, learner)
            if ordinal == 1:
                learner.save_state(folder / "middle.npz", primary)
        result = trace.close()
        trace = trial.Trace(trace_path, True)
        for ordinal, index in enumerate(order):
            apply_target(replay, pool[int(index)], 1, ordinal, trace, learner)
        assert trace.close() == result
        assert learner.reference.equal_state(learner.full_state(primary), learner.full_state(replay))
        resumed = learner.load_state(folder / "middle.npz")
        last = pool[int(order[-1])]
        resumed.step(last["prefix"], last["target"])
        assert learner.reference.equal_state(learner.full_state(primary), learner.full_state(resumed))
        # Synthetic row only: generation and teacher-forcing preserve learning state.
        synthetic_row = {"id": "synthetic-only", "split": "train", "path": [0], "target_n": 1,
                         "Q": "010", "A": "01", "address_bits": "0", "up_bits": "1"}
        before = resumed.state()
        learner.evaluate(resumed, [synthetic_row])
        assert learner.reference.equal_state(before, resumed.state())
        resumed.p[2][:] = 0
        resumed.p[3][:] = [1, 0, -1]
        assert learner.generate(resumed, "010")["tokens"] == "0" * 24
        assert learner.generate(resumed, "010")["cap_exhausted"]
        assert learner.generate(resumed, "0" * 81)["overflow"]
        resumed.p[3][:] = [0, 0, 1]
        assert learner.generate(resumed, "010")["tokens"] == "S"
    # This is a reconstruction check, never fitting formal prefixes or scoring holdout.
    _, repeated, repeated_bytes = make_schedules(manifest["target_pool"], [101, 202, 303], 128, 81000)
    assert repeated == manifest["schedules"] and schedule_bytes == repeated_bytes
    assert before_control == control_inputs(control_root, [101, 202, 303], [0, 16, 32, 64, 96, 128])
    assert all(file_sha(Path(source_root) / name) == value for name, value in before_source.items())
    report = {"schema": "target-order-engineering-v1", "status": "PASS", "author": "Codex",
              "local_source_hashes": manifest["local_source_hashes"], "protocol_sha256": manifest["protocol_sha256"],
              "original_source_files_verified_unchanged": len(before_source),
              "control_input_files_verified_unchanged": len(before_control),
              "original_initial_states_fully_loaded_and_matched": 3,
              "initial_match_scope": "All p/m/v/birth arrays, t, shape, seed, growth RNG, events, train/inference counters",
              "target_pool_size": len(manifest["target_pool"]), "each_epoch_original_multiset_exact": True,
              "orders_per_seed": {key: list(value.shape) for key, value in orders.items()},
              "schedule_bytes_deterministic": True, "synthetic_native_optimizer_update_calls": 7,
              "synthetic_full_trace_replay": "exact", "synthetic_checkpoint_resume": "exact",
              "generation_STOP_overflow_cap": "PASS", "formal_student_updates": 0,
              "formal_heldout_neural_evaluations": 0, "external_model_calls": 0}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "checks.json", report)
    return report


def train_seed(original, manifest, orders, manifest_dir, output, seed, replay=False):
    learner, trial = original["learner"], original["trial"]
    p = manifest["protocol"]
    folder = output / f"seed{seed}"
    if not replay:
        folder.mkdir()
    source_initial = manifest_dir / manifest["control"]["students"][str(seed)]["initial_file"]
    net = learner.load_state(source_initial)
    assert learner.state_sha(learner.full_state(net)) == manifest["control"]["students"][str(seed)]["initial_state_sha256"]
    if replay:
        assert learner.reference.equal_state(learner.full_state(net), learner.full_state(learner.load_state(folder / "initial-state.npz")))
    else:
        with (folder / "initial-state.npz").open("xb") as stream:
            stream.write(source_initial.read_bytes())
    pool = manifest["target_pool"]
    train = [row for row in manifest["rows"] if row["split"] == "train"]
    trace_path = folder / "targets.jsonl.gz"
    trace = trial.Trace(trace_path, replay)
    curve = []
    started = time.perf_counter()

    def checkpoint(epoch):
        assert all(a.dtype == np.float32 and np.isfinite(a).all() for label in ("p", "m", "v") for a in getattr(net, label))
        assert net.t == epoch * 212 and net.train_macs == net.t * 21056
        truth = learner.evaluate(net, train)
        record = {"epoch": epoch, "target_updates": net.t, "training_dense_MAC": net.train_macs,
                  "metrics": learner.metrics(truth), "state_sha256": learner.state_sha(learner.full_state(net)),
                  "inference_calls": net.inference_calls, "inference_dense_MAC": net.inference_macs}
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
        for epoch, order in enumerate(orders[f"seed{seed}"], 1):
            for ordinal, index in enumerate(order):
                apply_target(net, pool[int(index)], epoch, ordinal, trace, learner)
            if epoch in p["checkpoint_epochs"]:
                checkpoint(epoch)
                print(canonical({"mode": "replay" if replay else "primary", "seed": seed, "epoch": epoch, "updates": net.t}), flush=True)
        trace_result = trace.close()
        assert net.t == p["targets_per_seed"] == trace_result["targets"]
        assert net.train_macs == p["training_dense_MAC_per_seed"]
        summary = {"seed": seed, "author": "Codex", "targets": net.t, "epochs": 128,
                   "parameters": net.parameters, "training_dense_MAC": net.train_macs,
                   "training_diagnostic_inference_calls": net.inference_calls,
                   "training_diagnostic_dense_MAC": net.inference_macs,
                   "state_sha256": learner.state_sha(learner.full_state(net)),
                   "trace": trace_result, "trace_file_sha256": file_sha(trace_path),
                   "p_m_v_birth_array_bytes": sum(a.nbytes for label in ("p", "m", "v", "birth") for a in getattr(net, label))}
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
        if not trace.stream.closed:
            trace.stream.close()
        learner.save_state(folder / ("replay-failure-state.npz" if replay else "primary-failure-state.npz"), net)
        raise


def paired_difference(new, control):
    return {"train_whole_correct": new["train"]["whole_correct"] - control["train"]["whole_correct"],
            "train_address_correct": new["train"]["address_correct"] - control["train"]["address_correct"],
            "heldout_whole_correct_diagnostic": new["heldout"]["whole_correct"] - control["heldout"]["whole_correct"]}


def offline_evaluate(original, manifest, output):
    learner = original["learner"]
    students = []
    for seed in manifest["protocol"]["seeds"]:
        folder = output / f"seed{seed}"
        offline = []
        for epoch in manifest["protocol"]["checkpoint_epochs"]:
            state_path = folder / f"state-{epoch:03}.npz"
            net = learner.load_state(state_path)
            before = net.state()
            calls, macs = net.inference_calls, net.inference_macs
            truth = learner.evaluate(net, manifest["rows"])
            assert learner.reference.equal_state(before, net.state())
            score = learner.metrics(truth)
            truth_name = "final-truth.json" if epoch == 128 else f"offline-truth-{epoch:03}.json"
            write(folder / truth_name, truth)
            control = manifest["control"]["students"][str(seed)]["points"][str(epoch)]
            offline.append({"epoch": epoch, "target_updates": net.t, "training_dense_MAC": net.train_macs,
                            "metrics": score, "fixed_control_metrics": control,
                            "paired_difference": paired_difference(score, control),
                            "truth_file": truth_name, "checkpoint_file": state_path.name,
                            "checkpoint_sha256": file_sha(state_path),
                            "diagnostic_inference_calls": net.inference_calls - calls,
                            "diagnostic_dense_MAC": net.inference_macs - macs})
        write(folder / "offline-curve.json", offline)
        write(folder / "final-failures.json", [row for row in truth if not row["whole_correct"]])
        score = offline[-1]["metrics"]
        students.append({"seed": seed, "metrics": score,
                         "strong_fit_gate": score["train"]["whole_correct"] == score["train"]["address_correct"] == 12,
                         "paired_difference": offline[-1]["paired_difference"],
                         "stability": [point for point in offline if point["epoch"] in (96, 128)],
                         "offline_diagnostic_inference_calls": sum(point["diagnostic_inference_calls"] for point in offline),
                         "offline_diagnostic_dense_MAC": sum(point["diagnostic_dense_MAC"] for point in offline),
                         "final_state_sha256": file_sha(folder / "final-state.npz")})
    return students


def execute(source_root, control_root, manifest_path, approved_sha, output):
    original, manifest, orders = validate_manifest(source_root, control_root, manifest_path, approved_sha)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "manifest.json", manifest)
    write(output / "execution-start.json", {"author": "Codex", "manifest_sha256": approved_sha,
                                           "runtime": runtime(), "formal_started": True,
                                           "external_model_calls": 0, "auto_retry": False})
    timings = []
    started = time.perf_counter()
    try:
        # Deliberately finish every primary before the first replay or heldout call.
        for replay in (False, True):
            for seed in manifest["protocol"]["seeds"]:
                timings.append(train_seed(original, manifest, orders, Path(manifest_path).resolve().parent, output, seed, replay))
        validate_manifest(source_root, control_root, manifest_path, approved_sha)
        students = offline_evaluate(original, manifest, output)
        summaries = [read(output / f"seed{seed}/training-summary.json") for seed in manifest["protocol"]["seeds"]]
        diagnostic_macs = sum(row["training_diagnostic_dense_MAC"] for row in summaries)
        diagnostic_calls = sum(row["training_diagnostic_inference_calls"] for row in summaries)
        summary = {"id": manifest["id"], "status": "complete", "author": "Codex",
                   "design_lineage": "ChatGPT Pro fixed UR1 model/task and target-order proposal; Codex new driver and actual execution",
                   "manifest_sha256": approved_sha, "students": students,
                   "strong_fit_gate_all_three": all(row["strong_fit_gate"] for row in students),
                   "primary_targets": 81408, "replay_targets": 81408,
                   "primary_training_dense_MAC": 1714126848, "replay_training_dense_MAC": 1714126848,
                   "primary_training_diagnostic_dense_MAC": diagnostic_macs,
                   "replay_training_diagnostic_dense_MAC": diagnostic_macs,
                   "primary_training_diagnostic_inference_calls": diagnostic_calls,
                   "replay_training_diagnostic_inference_calls": diagnostic_calls,
                   "offline_evaluation_dense_MAC": sum(row["offline_diagnostic_dense_MAC"] for row in students),
                   "offline_evaluation_inference_calls": sum(row["offline_diagnostic_inference_calls"] for row in students),
                   "p_m_v_birth_array_bytes_per_student": 209980, "complete_trajectories": 3, "exact_replays": 3,
                   "control_attribution": manifest["control"]["attribution"],
                   "heldout_status": "Previously viewed exposed diagnostic, not new blind test",
                   "scope": manifest["protocol"]["scope"], "external_model_calls": 0}
        write(output / "summary.json", summary)
        write(output / "timing.json", {"trajectories": timings, "total_seconds": time.perf_counter() - started,
                                      "scope": "Primary, trace/checkpoint I/O, full replay, source/control guards and offline diagnostics; not pure kernel time"})
        print(canonical(summary), flush=True)
    except Exception as error:
        write(output / "failure.json", {"status": "incomplete", "error_type": type(error).__name__,
                                        "message": str(error), "timings_completed": timings, "auto_retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--make-manifest", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--source-root", type=Path, required=True, help="Unmodified original source repository root")
    parser.add_argument("--control-root", type=Path, required=True, help="Verified fixed original-order Codex replication science directory")
    parser.add_argument("--out", type=Path, required=True, help="New directory; never overwrite or resume")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--approved-manifest-sha")
    args = parser.parse_args()
    if args.preflight:
        print(canonical(preflight(args.source_root, args.control_root, args.out)))
    elif args.make_manifest:
        print(canonical(make_manifest(args.source_root, args.control_root, args.out)))
    else:
        if not args.manifest or not args.approved_manifest_sha:
            parser.error("--execute requires --manifest and --approved-manifest-sha from the preregistration gate")
        execute(args.source_root, args.control_root, args.manifest, args.approved_manifest_sha, args.out)


if __name__ == "__main__":
    main()
