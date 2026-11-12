"""Frozen P034 B1 six-learner experiment and full exact update replay.

Consumes verified P033 lesson files; never samples a new course. This runner
does not alter the separately frozen learner, tests, or historical controls.
"""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import platform
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "work/sle-p034/b1"
BASELINE = ROOT / "work/sle-p034/baseline"
sys.path.insert(0, str(HERE / "reference"))
import numpy as np
import p033
from attention_model import Model

ref, old = p033.ref, p033.old
PROFILE = ref.PHASES[4]
SNAPSHOTS = (0, 1000, 1500, 3000)
MODEL_SHA = "d0bd2432354e90709f2aad11d542055e991580c6a86e7ae850e1f5fdb2154e79"
TEST_SHA = "6e205b425af1cfbd1bcb45e328638401634160173e5657c10960fdafa56a6730"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value, *, exclusive=False):
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2,
                  allow_nan=False)
        stream.write("\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_digest(net):
    """All p/m/v/birth, step, architecture, optimizer metadata and RNG states."""
    digest = hashlib.sha256()
    for key, value in sorted(net.state().items()):
        digest.update(key.encode("utf-8") + b"\0")
        digest.update(value.dtype.str.encode("ascii") + b"\0")
        digest.update(json.dumps(value.shape).encode("ascii") + b"\0")
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def check_finite_state(net):
    for label in ("p", "m", "v"):
        for array in getattr(net, label):
            assert array.dtype == np.float32 and np.isfinite(array).all(), label
    assert all(np.count_nonzero(a) == 0 for a in net.birth)


def truth(net, split):
    rows = []
    for op in (0, 1):
        for value in range(8):
            row = old.truth_row(net, PROFILE, op, value)
            row["split"] = next(name for name in ("train", "val", "test")
                                if value in split[name])
            row["first_error_position_zero_based"] = next(
                (i for i, pair in enumerate(zip_longest(row["generated"], row["target"]))
                 if pair[0] != pair[1]), None)
            row["information_bit_correct"] = row["bit_correct"][:3]
            row["syntax_tail_correct"] = row["bit_correct"][3]
            row["teacher_forcing_correct"] = sum(
                r["target"] == r["prediction"] for r in row["teacher_forcing"])
            rows.append(row)
    return rows


def measure(net, split, at):
    check_finite_state(net)
    saved = net.state()
    result = {
        "presentations": at, "target_updates": net.t,
        "metrics_all_values": ref.small(ref.metrics(net, PROFILE, list(range(8)))),
        "metrics": {name: ref.small(ref.metrics(net, PROFILE, split[name]))
                    for name in ("train", "val", "test")},
        "finite_float32_parameters_and_moments": True,
    }
    assert ref.equal_state(saved, net.state())
    return result


def preflight():
    protocol_path = HERE / "protocol.json"
    baseline_path = BASELINE / "compact.json"
    engineering_path = ROOT / "work/sle-p034/attention-engineering/checks.json"
    protocol, baseline, engineering = map(read_json,
                                         (protocol_path, baseline_path, engineering_path))
    assert protocol["B1"]["params"] == 2596
    assert protocol["B1"]["presentations"] == 3000
    assert protocol["B1"]["target_updates"] == 15000
    assert protocol["B1"]["snapshots"] == list(SNAPSHOTS)
    assert baseline["status"] == "passed" and baseline["learners"] == 6
    assert baseline["new_B0_training"] is False and baseline["read_only_Qs"] == 96
    assert all(row["all_sixteen_truth_rows_recomputed_equal"] for row in baseline["rows"])
    assert engineering["passed"] and engineering["tests_run"] == 8
    assert sha(HERE / "attention_model.py") == MODEL_SHA
    assert sha(HERE / "test_attention.py") == TEST_SHA
    assert engineering["source_sha256"]["attention_model.py"] == MODEL_SHA
    assert engineering["source_sha256"]["test_attention.py"] == TEST_SHA
    assert (PROFILE.nop, PROFILE.nd, PROFILE.end, PROFILE.qlen) == (2, 3, False, 9)
    source_hashes = {}
    for name, expected in baseline["source_sha256"].items():
        actual = sha(HERE / "reference" / name)
        assert actual == expected, name
        source_hashes[f"reference/{name}"] = actual
    source_hashes.update({"b1_trial.py": sha(Path(__file__)),
                          "attention_model.py": MODEL_SHA, "test_attention.py": TEST_SHA})
    specs = []
    for group, split_name in (("G0", "S0"), ("G1", "C1")):
        split = p033.SPLITS[split_name]
        assert split["train"] == protocol["B1"]["train_values"][split_name]
        assert split["val"] == protocol["B1"]["val"][split_name]
        assert split["test"] == protocol["B1"]["test"][split_name]
        for seed in (101, 202, 303):
            catalog = next(c for c in baseline["courses"] if
                           c["group"] == group and c["seed"] == seed)
            course_path = BASELINE / f"lessons-{group}-{seed}.json"
            digest = sha(course_path)
            assert digest == catalog["sha256"]
            lessons = read_json(course_path)
            assert len(lessons) == 3000
            assert Counter(tuple(pair) for pair in lessons) == Counter({
                (op, value): 250 for op in (0, 1) for value in split["train"]})
            for op, value in set(map(tuple, lessons)):
                q, a = ref.encode(PROFILE, op, value), ref.answer(op, 3, value)
                assert len(q) == 9 and len(a) == 4 and not set(q+a)-set("01")
            specs.append({"group": group, "split_name": split_name, "split": split,
                          "seed": seed, "course_path": str(course_path),
                          "course_sha256": digest, "lessons": lessons})
    paths = {"protocol.json": protocol_path, "baseline/compact.json": baseline_path,
             "attention-engineering/checks.json": engineering_path}
    prerequisite_hashes = {name: sha(path) for name, path in paths.items()}
    return protocol, baseline, specs, source_hashes, paths, prerequisite_hashes


def learning(net, spec, folder, *, expected=None):
    phase = "primary" if expected is None else "replay"
    token_trace, lesson_trace, curve = [], [], []
    snapshot_digests = {}
    training_seconds = 0.
    started = time.perf_counter()

    def snapshot(at):
        rows = truth(net, spec["split"])
        saved = net.state()
        snapshot_digests[str(at)] = state_digest(net)
        if expected is None:
            net.save_checkpoint(folder / f"state-{at}.npz")
            dump(folder / f"truth-table-{at}.json", rows)
        else:
            checkpoint = Model.load_checkpoint(folder / f"state-{at}.npz")
            assert ref.equal_state(saved, checkpoint.state()), (phase, at, "full checkpoint")
            assert rows == read_json(folder / f"truth-table-{at}.json"), (phase, at, "truth")
            assert snapshot_digests[str(at)] == expected["snapshot_digests"][str(at)]

    try:
        curve.append(measure(net, spec["split"], 0))
        snapshot(0)
        for n, (op, value) in enumerate(spec["lessons"], 1):
            q, a = ref.encode(PROFILE, op, value), ref.answer(op, 3, value)
            predictions, total_loss = "", 0.
            # Teacher appears only as the training target and allowed prior
            # answer prefix. Free generation always receives Q alone.
            for i, target in enumerate(a+"S"):
                prefix = q+a[:i]
                before_step = time.perf_counter()
                prediction, loss = net.step(prefix, target)
                training_seconds += time.perf_counter()-before_step
                assert np.isfinite(loss), (phase, n, i)
                record = [n, i, prefix, target, prediction, loss,
                          net.last_gradient_norm, net.last_gradient_scale,
                          net.t, state_digest(net)]
                if expected is not None:
                    assert record == expected["token_trace"][len(token_trace)], (
                        phase, spec["group"], spec["seed"], n, i, "full update digest or trace")
                token_trace.append(record)
                predictions += prediction
                total_loss += loss
            row = [op, value, predictions, total_loss]
            if expected is not None:
                assert row == expected["lesson_trace"][n-1], (phase, n, "lesson trace")
            lesson_trace.append(row)
            if n % 100 == 0:
                curve.append(measure(net, spec["split"], n))
                if expected is not None:
                    assert curve[-1] == expected["curve"][len(curve)-1], (phase, n, "curve")
            if n in SNAPSHOTS:
                snapshot(n)
            if n % 1000 == 0:
                print(json.dumps({"family": "B1", "phase": phase, "group": spec["group"],
                                  "seed": spec["seed"], "presentations": n,
                                  "target_updates": net.t}), flush=True)
        assert net.t == 15000 and len(token_trace) == 15000
        assert net.train_macs == 1208880000
        assert len(curve) == 31 and set(snapshot_digests) == set(map(str, SNAPSHOTS))
        check_finite_state(net)
    except Exception:
        # Preserve the actual failing attempt and stop; never restart/tune.
        dump(folder / f"{phase}-partial-token-trace.json", token_trace)
        dump(folder / f"{phase}-partial-curve.json", curve)
        net.save_checkpoint(folder / f"{phase}-failure-state.npz")
        raise
    return {"token_trace": token_trace, "lesson_trace": lesson_trace,
            "curve": curve, "snapshot_digests": snapshot_digests,
            "seconds_training_updates": training_seconds,
            "seconds_loop_training_probes_state_fingerprints": time.perf_counter()-started}


def trial(spec, baseline_row):
    folder = OUT / f"{spec['group']}-seed{spec['seed']}"
    folder.mkdir()
    initial = Model(spec["seed"])
    initial_state = initial.state()
    net = Model.from_state(initial_state)
    actual = learning(net, spec, folder)
    frozen = net.state()
    dump(folder / "token-trace.json", actual["token_trace"])
    dump(folder / "trace.json", actual["lesson_trace"])
    dump(folder / "curve.json", actual["curve"])
    replay = Model.from_state(initial_state)
    repeated = learning(replay, spec, folder, expected=actual)
    assert actual["curve"] == repeated["curve"]
    assert actual["token_trace"] == repeated["token_trace"]
    assert actual["lesson_trace"] == repeated["lesson_trace"]
    assert ref.equal_state(frozen, replay.state())
    assert net.costs == replay.costs and net.inference_calls == replay.inference_calls
    final_truth = read_json(folder / "truth-table-3000.json")
    failures = [r for r in final_truth if not r["whole_correct"]]
    dump(folder / "final-failures.json", failures)
    metrics = actual["curve"][-1]["metrics"]
    costs = {phase: dict(values) for phase, values in net.costs.items()}
    result = {
        "group": spec["group"], "split": spec["split_name"], "seed": spec["seed"],
        "architecture": net.architecture, "parameters": net.parameters,
        "course_sha256": spec["course_sha256"], "presentations": 3000,
        "target_updates": net.t, "metrics": metrics,
        "whole_correct": {name: sum(v["whole"] for v in metrics[name]["by_op"].values())
                          for name in ("train", "val", "test")},
        "strong_success_this_learner": all(r["whole_correct"] for r in final_truth),
        "final_failure_count": len(failures),
        "raw_question_bits": 27000, "teacher_answer_bits": 12000,
        "train_MACs": net.train_macs, "inference_MACs": net.inference_macs,
        "inference_calls": net.inference_calls, "costs": costs,
        "array_bytes": net.array_bytes(),
        "seconds_training_updates": actual["seconds_training_updates"],
        "seconds_primary_loop_training_probes_state_fingerprints":
            actual["seconds_loop_training_probes_state_fingerprints"],
        "seconds_replay_loop": repeated["seconds_loop_training_probes_state_fingerprints"],
        "all15000_update_full_state_digests_equal": True,
        "replay_predictions_losses_curves_snapshot_arrays_final_optimizer_RNG_exact": True,
        "initial_state_digest": actual["snapshot_digests"]["0"],
        "snapshot_state_digests": actual["snapshot_digests"],
        "baseline": {"kind": "historical P033 T1 control, verified read-only this session",
                     "source_commit": "e217bd0fd6cfe654062c3615ee2aa73a36d1ca71",
                     "new_B0_training": False, "parameters": 2595,
                     "metrics": baseline_row["metrics"],
                     "source_checkpoint_sha256": baseline_row["source_checkpoint_sha256"]},
    }
    dump(folder / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    protocol, baseline, specs, sources, prerequisite_paths, prerequisite_hashes = preflight()
    if args.preflight_only:
        probe = Model(101)
        before = probe.state()
        # Read-only full sixteen-question schema exercise; zero updates.
        metrics = measure(probe, specs[0]["split"], 0)
        rows = truth(probe, specs[0]["split"])
        assert len(rows) == 16 and ref.equal_state(before, probe.state()) and probe.t == 0
        dump(OUT / "preflight.json", {"status": "passed", "scientific_updates": 0,
                                      "courses_validated": len(specs),
                                      "source_sha256": sources,
                                      "prerequisite_sha256": prerequisite_hashes,
                                      "initial_metric_schema_checked": bool(metrics)})
        print(json.dumps({"status": "preflight_passed", "scientific_updates": 0,
                          "courses_validated": len(specs)}), flush=True)
        return 0
    if (OUT / "manifest.json").exists():
        raise FileExistsError("Frozen attempt already exists; do not restart/tune")
    manifest = {
        "id": "P034-B1-fixed-six-learners", "execution_author": "Codex T",
        "frozen_utc_before_first_update": datetime.now(timezone.utc).isoformat(),
        "source_sha256": sources, "prerequisite_sha256": prerequisite_hashes,
        "protocol": protocol["B1"], "python": platform.python_version(),
        "numpy": np.__version__, "threads": {"OPENBLAS_NUM_THREADS": 1, "OMP_NUM_THREADS": 1},
        "courses": [{k: v for k, v in spec.items() if k != "lessons"} for spec in specs],
        "initialization_order": list(Model.PARAMETER_NAMES),
        "no_warmup": True, "input_visibility": "native binary Q+current answer prefix",
        "teacher_visibility": "loss target and teacher-forced previous answer prefix only; generate(Q) only",
        "optimizer_all_parameters_trainable": True,
        "freeze": "all six fixed courses/seeds complete, no holdout decisions or extra runs",
        "measurements": "all16 plus train/val/test every100; snapshots0/1000/1500/3000",
        "replay": "every target record and complete state digest; all snapshot/final arrays and RNG exact",
        "historical_B0_control": "read-only verified P033 T1; not newly trained; unequal MAC",
        "cost_definition": "dense masked matmuls include future cells; F=2080n+32n^2+48,B=2F",
        "non_MAC_counts": "attention softmax n^2 with valid n(n+1)/2; LN32n per direction; output softmax3 per target",
        "array_bytes_scope": "persistent parameter/Adam/birth arrays; excludes peak RSS and temporary activations",
    }
    dump(OUT / "manifest.json", manifest, exclusive=True)
    started, results = time.perf_counter(), []
    current = None
    try:
        for spec in specs:
            current = {k: spec[k] for k in ("group", "split_name", "seed")}
            baseline_row = next(r for r in baseline["rows"] if
                                r["group"] == spec["group"] and r["seed"] == spec["seed"])
            results.append(trial(spec, baseline_row))
            dump(OUT / "progress.json", {"completed_learners": len(results),
                                         "required_learners": 6, "results": results})
        for name, digest in sources.items():
            assert sha(HERE / name) == digest, (name, "source changed after freeze")
        for name, path in prerequisite_paths.items():
            assert sha(path) == prerequisite_hashes[name], (name, "prerequisite changed")
        for spec in specs:
            assert sha(Path(spec["course_path"])) == spec["course_sha256"]
        assert len(results) == 6
        compact = {
            "status": "passed", "meaning": "execution and full replay passed; scores are separate",
            "learners": 6, "scientific_training_presentations": 18000,
            "scientific_target_updates": 90000, "verification_replay_target_updates": 90000,
            "all_updates_and_full_optimizer_RNG_replayed_exact": True,
            "strong_success": all(r["strong_success_this_learner"] for r in results),
            "totals_whole_correct": {name: sum(r["whole_correct"][name] for r in results)
                                     for name in ("train", "val", "test")},
            "denominators": {"train": 72, "val": 12, "test": 12},
            "train_MACs_excluding_replay": sum(r["train_MACs"] for r in results),
            "train_MACs_replay_additional": sum(r["train_MACs"] for r in results),
            "inference_MACs_primary": sum(r["inference_MACs"] for r in results),
            "seconds_with_replay_and_evidence": time.perf_counter()-started,
            "baseline_kind": "historical P033 T1; six controls verified read-only, no new B0 training",
            "not_equal_MAC": True,
            "limits": ["exposed three-bit mechanism domain, not new blind evaluation",
                       "B1 bundle includes learned positions/LN/attention/FFN; no single-component attribution",
                       "no holdout tuning, seed selection, extended budgets or other configurations"],
            "results": results,
        }
        dump(OUT / "results.json", results)
        dump(OUT / "compact.json", compact)
        print(json.dumps({k: v for k, v in compact.items() if k != "results"}), flush=True)
    except Exception:
        dump(OUT / "failure.json", {"status": "stopped_failure_no_restart", "current": current,
                                    "completed_learners": len(results),
                                    "seconds": time.perf_counter()-started,
                                    "traceback": traceback.format_exc()})
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
