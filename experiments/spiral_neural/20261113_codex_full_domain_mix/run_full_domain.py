"""All512 numeric8-bit Echo/Neg questions; prepare/engineering do not run formal training."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import zipfile

if sys.flags.optimize:
    raise RuntimeError("Optimized Python is disabled: exact assertions are required")
sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
CORE = ("run_full_domain.py", "protocol.json", "test_full_domain.py")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def runtime():
    return {"python": platform.python_version(), "numpy": np.__version__, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}


def protocol():
    p = read(HERE / "protocol.json")
    assert p["id"] == "FULL-DOMAIN-NUMERIC8-MIX-20261113" and p["seeds"] == [101, 202, 303]
    assert p["model"] == {"L": 23, "H": 69, "parameters": 3453}
    assert p["max_epochs"] == 40 and p["questions_per_epoch"] == 512
    assert p["targets_per_question"] == 10 and p["targets_per_epoch"] == 5120
    assert p["maximum_updates_per_seed"] == 40 * 5120 == 204800
    assert p["training_dense_MAC_per_target"] == 69 * (4 * 23 + 9) == 6969
    assert p["training_dense_MAC_per_epoch"] == 5120 * 6969 == 35681280
    assert p["maximum_training_dense_MAC_per_seed"] == 204800 * 6969 == 1427251200
    assert p["forward_dense_MAC_per_call"] == 69 * (2 * 23 + 3) == 3381
    assert p["p_m_v_birth_array_bytes"] == 3453 * 20 == 69060 and p["replay_seeds"] == [101]
    return p


def source_model(content):
    p = protocol()
    assert sha(content) == p["source_sha256"], "Pinned original source differs"
    node = next(node for node in ast.parse(content.decode("utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "Model")
    assert sha(ast.dump(node, include_attributes=False).encode("utf-8")) == p["Model_AST_sha256"]
    namespace = {"np": np, "json": json, "__name__": "original_P030_Model_AST"}
    exec(compile(ast.Module(body=[copy.deepcopy(node)], type_ignores=[]), "<unchanged-P030-Model>", "exec"), namespace)
    return namespace["Model"]


def encode(op, value):
    assert op in (0, 1) and 0 <= value < 256
    return "01" + format(op, "02b") + "0" + format(value, "08b") + "0"


def answer(op, value):
    bits = format(value, "08b")
    return (bits if op == 0 else "".join("1" if bit == "0" else "0" for bit in bits)) + "0"


def question_pool():
    return [{"input_id": op * 256 + value, "op": op, "value": value, "Q": encode(op, value), "A": answer(op, value)}
            for op in (0, 1) for value in range(256)]


def full_state(net):
    return net.state() | {"meta_seed": np.array(net.seed), "meta_events": np.array(canonical(net.events)),
                          "meta_train_macs": np.array(net.train_macs), "meta_inference_macs": np.array(net.inference_macs),
                          "meta_inference_calls": np.array(net.inference_calls)}


def state_sha(state):
    digest = hashlib.sha256()
    for name, value in sorted(state.items()):
        digest.update(canonical([name, value.dtype.str, list(value.shape)]).encode("utf-8"))
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def equal_state(a, b):
    return a.keys() == b.keys() and all(np.array_equal(value, b[name]) for name, value in a.items())


def npz_bytes(state):
    buffer = io.BytesIO()
    np.savez(buffer, **state)
    return buffer.getvalue()


def read_npz(content):
    with np.load(io.BytesIO(content), allow_pickle=False) as archive:
        return {name: archive[name].copy() for name in archive.files}


def save_state(path, net):
    with Path(path).open("xb") as stream:
        stream.write(npz_bytes(full_state(net)))


def restore(cls, saved):
    net = cls(int(saved["meta_seed"]), L=int(saved["L"]), H=int(saved["H"]))
    for label in ("p", "m", "v", "birth"):
        setattr(net, label, [saved[f"{label}{i}"].copy() for i in range(4)])
    net.t = int(saved["t"])
    net.growth_rng.bit_generator.state = json.loads(str(saved["growth_rng"]))
    net.events = json.loads(str(saved["meta_events"]))
    for name in ("train_macs", "inference_macs", "inference_calls"):
        setattr(net, name, int(saved["meta_" + name]))
    assert equal_state(saved, full_state(net))
    return net


def schedule(seed):
    rng = np.random.default_rng(seed + 221000)
    pool = np.array([(op, value) for op in (0, 1) for value in range(256)], dtype="<i8")
    actual = np.stack([pool[rng.permutation(512)] for _ in range(40)])
    assert actual.shape == (40, 512, 2)
    assert all(sorted(map(tuple, epoch.tolist())) == sorted(map(tuple, pool.tolist())) for epoch in actual)
    return actual, copy.deepcopy(rng.bit_generator.state)


def npy_bytes(array):
    buffer = io.BytesIO()
    np.save(buffer, array, allow_pickle=False)
    return buffer.getvalue()


def make_zip(contents):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, value in sorted(contents.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def prepare(source, output):
    content = Path(source).read_bytes()
    cls, p = source_model(content), protocol()
    pool = question_pool()
    contents = {"source/p030_binary_continual.py": content, "plan.json": (HERE / "protocol.json").read_bytes(),
                "question-pool.json": (canonical(pool) + "\n").encode("utf-8")}
    initials, courses = {}, {}
    for seed in p["seeds"]:
        net = cls(seed, L=23, H=69)
        assert net.parameters == 3453 and net.t == 0 and net.events == []
        assert sum(a.nbytes for label in ("p", "m", "v", "birth") for a in getattr(net, label)) == 69060
        initial_name = f"initial/seed{seed}.npz"
        contents[initial_name] = npz_bytes(full_state(net))
        initials[str(seed)] = {"file": initial_name, "full_state_sha256": state_sha(full_state(net))}
        actual, rng_final = schedule(seed)
        name = f"schedules/seed{seed}.npy"
        contents[name] = npy_bytes(actual)
        courses[str(seed)] = {"file": name, "shape": [40, 512, 2], "dtype": "<i8", "schedule_seed": seed + 221000,
                              "final_schedule_RNG": rng_final}
    archive = make_zip(contents)
    assert file_sha(source) == sha(content)
    manifest = {"schema": "full-domain-input-manifest-v1", "id": p["id"], "status": "frozen_before_formal_training",
                "author": "Codex", "protocol": p, "runtime": runtime(),
                "source_hashes": {name: file_sha(HERE / name) for name in CORE},
                "initial_states": initials, "schedules": courses, "question_pool_sha256": sha(canonical(pool).encode("utf-8")),
                "archive": {"file": "inputs.zip", "sha256": sha(archive), "bytes": len(archive)},
                "files": {name: {"sha256": sha(value), "bytes": len(value)} for name, value in sorted(contents.items())},
                "formal_optimizer_calls_before_freeze": 0, "formal_inference_calls_before_freeze": 0, "external_model_calls": 0}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with (output / "inputs.zip").open("xb") as stream:
        stream.write(archive)
    write(output / "manifest.json", manifest)
    frozen = {"manifest_sha256": file_sha(output / "manifest.json"), "source_hashes": manifest["source_hashes"],
              "inputs_zip_sha256": manifest["archive"]["sha256"], "initial_states": initials,
              "schedule_file_sha256": {seed: manifest["files"][row["file"]]["sha256"] for seed, row in courses.items()},
              "formal_optimizer_calls": 0, "formal_inference_calls": 0, "external_model_calls": 0}
    write(output / "source-freeze.json", frozen)
    return frozen


def validate_inputs(path, approved):
    path = Path(path).resolve()
    assert approved and file_sha(path) == approved, "Explicit approved manifest SHA missing or differs"
    manifest = read(path)
    assert manifest["protocol"] == protocol() and manifest["runtime"] == runtime()
    assert manifest["source_hashes"] == {name: file_sha(HERE / name) for name in CORE}
    archive_path = path.parent / manifest["archive"]["file"]
    assert file_sha(archive_path) == manifest["archive"]["sha256"]
    with zipfile.ZipFile(archive_path) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) and set(archive.namelist()) == set(manifest["files"])
        contents = {name: archive.read(name) for name in archive.namelist()}
    for name, value in contents.items():
        assert {"sha256": sha(value), "bytes": len(value)} == manifest["files"][name]
    assert contents["plan.json"] == (HERE / "protocol.json").read_bytes()
    pool = json.loads(contents["question-pool.json"].decode("utf-8"))
    assert pool == question_pool() and sha(canonical(pool).encode("utf-8")) == manifest["question_pool_sha256"]
    cls = source_model(contents["source/p030_binary_continual.py"])
    initial, courses = {}, {}
    for seed in manifest["protocol"]["seeds"]:
        key = str(seed)
        initial[key] = read_npz(contents[manifest["initial_states"][key]["file"]])
        assert equal_state(initial[key], full_state(cls(seed, L=23, H=69)))
        assert state_sha(initial[key]) == manifest["initial_states"][key]["full_state_sha256"]
        courses[key] = np.load(io.BytesIO(contents[manifest["schedules"][key]["file"]]), allow_pickle=False)
        expected, rng_final = schedule(seed)
        assert courses[key].dtype.str == "<i8" and np.array_equal(courses[key], expected)
        assert manifest["schedules"][key]["final_schedule_RNG"] == rng_final
    return manifest, cls, pool, initial, courses


class EpochTrace:
    """Tiny streaming loss/prediction digest; no per-target state copies or disk IO."""
    def __init__(self):
        self.digest = hashlib.sha256()
        self.targets = self.correct = 0
        self.loss = 0.

    def observe(self, input_id, position, prediction, loss, target):
        assert np.isfinite(loss)
        line = canonical([input_id, position, prediction, loss]) + "\n"
        self.digest.update(line.encode("utf-8"))
        self.targets += 1
        self.correct += prediction == target
        self.loss += loss

    def result(self):
        return {"targets": self.targets, "pre_update_prediction_correct": self.correct, "CE_loss_sum": self.loss,
                "CE_loss_mean": self.loss / self.targets, "canonical_target_trace_sha256": self.digest.hexdigest()}


def one_lesson(net, row, trace, replay):
    q, a, position = row["Q"], row["A"], 0
    native = net.step
    predictions, total = "", 0.

    def step(prefix, target):
        nonlocal position, predictions, total
        assert prefix == q + a[:position] and target == (a + "S")[position]
        pred, loss = native(prefix, target)
        trace.observe(row["input_id"], position, pred, loss, target)
        predictions += pred
        total += loss
        position += 1
        return pred, loss

    if replay:
        for label in a + "S":
            step(q + a[:position], label)
    else:
        net.step = step
        try:
            actual = net.lesson(q, a)
        finally:
            del net.step
        assert actual == (predictions, total)
    assert position == len(a) + 1


def generate(net, q):
    tokens = ""
    for _ in range(16):
        prefix = q + tokens
        if len(prefix) > net.L:
            return {"tokens": tokens, "overflow": True, "context_exhausted": True, "cap_exhausted": False}
        token = "01S"[int(net.forward(prefix)[2].argmax())]
        tokens += token
        if token == "S":
            return {"tokens": tokens, "overflow": False, "context_exhausted": False, "cap_exhausted": False}
    return {"tokens": tokens, "overflow": False, "context_exhausted": False, "cap_exhausted": True}


def probe(net, pool):
    before = net.state()
    calls, macs = net.inference_calls, net.inference_macs
    rows = []
    for row in pool:
        generated = generate(net, row["Q"])
        rows.append({"input_id": row["input_id"], "op": row["op"], "value": row["value"], **generated,
                     "whole_correct": generated["tokens"] == row["A"] + "S" and not generated["overflow"]})
    assert equal_state(before, net.state())
    scores = {str(op): {"whole_correct": sum(row["whole_correct"] for row in rows if row["op"] == op),
                        "questions": sum(row["op"] == op for row in rows)} for op in (0, 1)}
    return {"scores": scores, "rows": rows, "inference_calls": net.inference_calls - calls,
            "inference_dense_MAC": net.inference_macs - macs}


def stop_decision(streak, scores, epoch, max_epochs=40):
    passed = all(scores[str(op)]["questions"] == scores[str(op)]["whole_correct"] == 256 for op in (0, 1))
    streak = streak + 1 if passed else 0
    reason = "two_consecutive_full_training_passes" if streak >= 2 else "epoch_cap" if epoch >= max_epochs else None
    return streak, reason


def run_seed(cls, initial, course, pool, output, seed, replay=False):
    folder = output / f"seed{seed}"
    if not replay:
        folder.mkdir()
    net = restore(cls, initial)
    if not replay:
        save_state(folder / "initial-state.npz", net)
    else:
        assert equal_state(full_state(net), read_npz((folder / "initial-state.npz").read_bytes()))
    curve, streak, reason = [], 0, None
    started = time.perf_counter()
    try:
        for epoch, order in enumerate(course, 1):
            trace = EpochTrace()
            start_t, start_macs = net.t, net.train_macs
            for op, value in order:
                one_lesson(net, pool[int(op) * 256 + int(value)], trace, replay)
            training = trace.result()
            assert training["targets"] == net.t - start_t == 5120
            assert net.train_macs - start_macs == 35681280 and net.t == epoch * 5120
            assert net.parameters == 3453 and (net.L, net.H) == (23, 69) and net.events == []
            assert all(a.dtype == np.float32 and np.isfinite(a).all() for label in ("p", "m", "v") for a in getattr(net, label))
            evaluation = probe(net, pool)
            streak, reason = stop_decision(streak, evaluation["scores"], epoch)
            record = {"epoch": epoch, "updates": net.t, "training_dense_MAC": net.train_macs, "training": training,
                      "scores": evaluation["scores"], "streak": streak, "stop_reason": reason,
                      "epoch_probe_inference_calls": evaluation["inference_calls"],
                      "epoch_probe_inference_MAC": evaluation["inference_dense_MAC"],
                      "cumulative_probe_inference_calls": net.inference_calls, "cumulative_probe_inference_MAC": net.inference_macs,
                      "full_state_sha256": state_sha(full_state(net))}
            state_path, probe_path = folder / f"state-{epoch:03}.npz", folder / f"generation-{epoch:03}.json"
            if replay:
                assert record == read(folder / f"epoch-{epoch:03}.json")
                assert evaluation == read(probe_path)
                assert equal_state(full_state(net), read_npz(state_path.read_bytes()))
            else:
                save_state(state_path, net)
                write(probe_path, evaluation)
                write(folder / f"epoch-{epoch:03}.json", record)
            curve.append(record)
            print(canonical({"mode": "replay" if replay else "primary", "seed": seed, "epoch": epoch,
                             "E": evaluation["scores"]["0"]["whole_correct"], "N": evaluation["scores"]["1"]["whole_correct"],
                             "streak": streak, "stop": reason}), flush=True)
            if reason:
                break
        assert reason is not None and len(curve) <= 40
        summary = {"seed": seed, "epochs": len(curve), "stop_reason": reason, "streak": streak,
                   "training_updates": net.t, "training_dense_MAC": net.train_macs,
                   "probe_inference_calls": net.inference_calls, "probe_inference_MAC": net.inference_macs,
                   "final_scores": curve[-1]["scores"], "final_full_state_sha256": state_sha(full_state(net)),
                   "p_m_v_birth_array_bytes": 69060}
        if replay:
            assert summary == read(folder / "training-summary.json") and curve == read(folder / "curve.json")
            assert equal_state(full_state(net), read_npz((folder / "final-state.npz").read_bytes()))
        else:
            save_state(folder / "final-state.npz", net)
            write(folder / "training-summary.json", summary)
            write(folder / "curve.json", curve)
        return {"seed": seed, "mode": "replay" if replay else "primary", "seconds": time.perf_counter() - started}
    except Exception:
        save_state(folder / ("replay-failure-state.npz" if replay else "primary-failure-state.npz"), net)
        raise


def final_tf(net, pool, generation):
    before = net.state()
    calls, macs = net.inference_calls, net.inference_macs
    assert len(generation["rows"]) == len(pool) == 512
    truth = []
    for row, free in zip(pool, generation["rows"], strict=True):
        assert row["input_id"] == free["input_id"]
        tf = []
        for position, target in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            logits = net.forward(prefix)[2].astype(np.float64)
            logp = logits - np.logaddexp.reduce(logits)
            tf.append({"position": position, "prefix": prefix, "target": target, "prediction": "01S"[int(logits.argmax())],
                       "logits_01S": logits.tolist(), "probabilities_01S": np.exp(logp).tolist(),
                       "target_CE": -float(logp["01S".index(target)])})
        truth.append({**row, "expected": row["A"] + "S", "generation": free, "TF": tf})
    assert equal_state(before, net.state())
    assert net.inference_calls - calls == 5120 and net.inference_macs - macs == 5120 * 3381
    metrics = {str(op): {"questions": 256, "TF_data_correct": sum(point["prediction"] == point["target"] for row in truth if row["op"] == op for point in row["TF"][:8]),
                         "TF_data_targets": 2048, "TF_tail0_correct": sum(row["TF"][8]["prediction"] == "0" for row in truth if row["op"] == op),
                         "TF_STOP_correct": sum(row["TF"][9]["prediction"] == "S" for row in truth if row["op"] == op)} for op in (0, 1)}
    return {"truth": truth, "metrics": metrics, "inference_calls": net.inference_calls - calls,
            "inference_dense_MAC": net.inference_macs - macs, "learning_state_unchanged": True,
            "free_generation_reused_from_final_epoch": True}


def execute(manifest_path, approved, commit, output):
    assert re.fullmatch(r"[0-9a-f]{40}", commit or ""), "Coordinator preregistration commit required"
    manifest, cls, pool, initials, courses = validate_inputs(manifest_path, approved)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "manifest.json", manifest)
    write(output / "execution-start.json", {"author": "Codex", "manifest_sha256": approved, "preregistration_commit": commit,
                                           "commit_scope": "Coordinator supplied, runner performs no Git operations", "auto_retry": False})
    timings = []
    started = time.perf_counter()
    try:
        for seed in manifest["protocol"]["seeds"]:
            timings.append(run_seed(cls, initials[str(seed)], courses[str(seed)], pool, output, seed))
        # Only seed101 is replayed; this is a fresh trajectory, never extra training on primary.
        timings.append(run_seed(cls, initials["101"], courses["101"], pool, output, 101, replay=True))
        validate_inputs(manifest_path, approved)
        students = []
        for seed in manifest["protocol"]["seeds"]:
            folder = output / f"seed{seed}"
            summary = read(folder / "training-summary.json")
            net = restore(cls, read_npz((folder / "final-state.npz").read_bytes()))
            generation = read(folder / f"generation-{summary['epochs']:03}.json")
            result = final_tf(net, pool, generation)
            write(folder / "final-truth.json", result)
            write(folder / "final-failures.json", [row for row in result["truth"] if not row["generation"]["whole_correct"]])
            students.append({**summary, "replay_status": "complete_exact" if seed == 101 else "not_planned",
                             "final_TF_metrics": result["metrics"], "final_TF_inference_calls": result["inference_calls"],
                             "final_TF_inference_MAC": result["inference_dense_MAC"]})
        validate_inputs(manifest_path, approved)
        summary = {"id": manifest["id"], "status": "complete", "author": "Codex", "manifest_sha256": approved,
                   "preregistration_commit": commit, "students": students, "primary_students": 3, "exact_full_replays": [101],
                   "primary_updates": sum(row["training_updates"] for row in students),
                   "primary_training_dense_MAC": sum(row["training_dense_MAC"] for row in students),
                   "replay_updates": students[0]["training_updates"], "replay_training_dense_MAC": students[0]["training_dense_MAC"],
                   "primary_epoch_probe_inference_calls": sum(row["probe_inference_calls"] for row in students),
                   "primary_epoch_probe_inference_MAC": sum(row["probe_inference_MAC"] for row in students),
                   "replay_epoch_probe_inference_calls": students[0]["probe_inference_calls"],
                   "replay_epoch_probe_inference_MAC": students[0]["probe_inference_MAC"],
                   "final_TF_inference_calls": sum(row["final_TF_inference_calls"] for row in students),
                   "final_TF_inference_MAC": sum(row["final_TF_inference_MAC"] for row in students),
                   "array_bytes_per_student": 69060, "all_confirmed_full_train_fit": all(row["streak"] >= 2 for row in students),
                   "external_model_calls": 0, "scope": manifest["protocol"]["scope"], "limits": manifest["protocol"]["limits"]}
        write(output / "compact.json", summary)
        write(output / "timing.json", {"trajectories": timings, "total_seconds": time.perf_counter() - started,
                                      "scope": "Training, all epoch probes/state IO, planned seed101 replay, input guards and final TF; not pure kernels"})
        write(output / "storage.json", {"output_bytes_before_this_record": sum(path.stat().st_size for path in output.rglob("*") if path.is_file()),
                                       "input_archive_bytes": manifest["archive"]["bytes"]})
        return summary
    except Exception as error:
        write(output / "failure.json", {"status": "incomplete", "error_type": type(error).__name__, "message": str(error),
                                        "completed_trajectories": timings, "auto_retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--engineering", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--approved-manifest-sha")
    parser.add_argument("--prereg-commit")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.prepare:
        if args.source is None:
            parser.error("--prepare requires --source original P030")
        result = prepare(args.source, args.out)
    elif args.engineering:
        if args.source is None:
            parser.error("--engineering requires --source for synthetic-only checks")
        import unittest
        import test_full_domain
        test_full_domain.SOURCE = args.source
        report = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_full_domain))
        assert report.wasSuccessful()
        args.out.mkdir(parents=True, exist_ok=False)
        result = {"status": "PASS", "tests": report.testsRun, "source_hashes": {name: file_sha(HERE / name) for name in CORE},
                  "synthetic_native_optimizer_updates": test_full_domain.NATIVE_UPDATES,
                  "synthetic_native_inference_calls": test_full_domain.NATIVE_INFERENCE,
                  "synthetic_mock_target_calls": test_full_domain.MOCK_TARGETS,
                  "synthetic_mock_epoch_probes": test_full_domain.MOCK_PROBES,
                  "formal_optimizer_updates": 0, "formal_inference_calls": 0, "external_model_calls": 0}
        write(args.out / "checks.json", result)
    else:
        if args.manifest is None or not args.approved_manifest_sha or not args.prereg_commit:
            parser.error("--execute requires --manifest, --approved-manifest-sha, --prereg-commit after coordinator gate")
        result = execute(args.manifest, args.approved_manifest_sha, args.prereg_commit, args.out)
    print(canonical(result), flush=True)


if __name__ == "__main__":
    main()
