"""Paired early/late task mixing; default modes do not start formal students."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import copy
import gzip
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
CORE = ("run_early_mix.py", "protocol.json", "test_early_mix.py")
TRAIN = (0, 1, 2, 3, 4, 7)


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
    assert p["id"] == "EARLY-MIX-MATCHED-20261113"
    assert p["seeds"] == [101, 202, 303] and p["arms"] == ["early", "late"]
    assert p["model"] == {"L": 13, "H": 69, "parameters": 2073}
    assert p["train_values"] == list(TRAIN) and p["diagnostic_values"] == [5, 6]
    assert p["checkpoint_lessons"] == [0, 300, 1200, 2400]
    assert p["targets_per_student"] == p["lessons_per_student"] * p["targets_per_lesson"] == 12000
    assert p["training_dense_MAC_per_target"] == 69 * (4 * 13 + 9) == 4209
    assert p["training_dense_MAC_per_student"] == 12000 * 4209 == 50508000
    assert p["primary_targets"] == p["replay_targets"] == 72000
    assert p["primary_training_dense_MAC"] == p["replay_training_dense_MAC"] == 303048000
    return p


def source_model(content):
    p = protocol()
    assert sha(content) == p["source_sha256"], "Frozen original source differs"
    nodes = {node.name: node for node in ast.parse(content.decode("utf-8")).body if isinstance(node, ast.ClassDef)}
    node = nodes["Model"]
    assert sha(ast.dump(node, include_attributes=False).encode("utf-8")) == p["Model_AST_sha256"]
    namespace = {"np": np, "json": json, "__name__": "original_P030_Model_AST"}
    exec(compile(ast.Module(body=[copy.deepcopy(node)], type_ignores=[]), "<unchanged-original-P030-Model>", "exec"), namespace)
    return namespace["Model"]


def encode(op, value):
    assert op in (0, 1) and 0 <= value < 8
    return "01" + format(op, "02b") + "0" + format(value, "03b") + "0"


def answer(op, value):
    bits = format(value, "03b")
    return (bits if op == 0 else "".join("1" if bit == "0" else "0" for bit in bits)) + "0"


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


def build_schedules(seed):
    values, value_rng_states = {}, {}
    for op in (0, 1):
        rng = np.random.default_rng(seed + 121000 + op)
        values[op] = np.concatenate([rng.permutation(TRAIN) for _ in range(200)]).astype("<i8")
        value_rng_states[str(op)] = copy.deepcopy(rng.bit_generator.state)
    early_rng = np.random.default_rng(seed + 122000)
    early = np.concatenate([early_rng.permutation([0, 1]), early_rng.permutation([0] * 599 + [1] * 599)])
    late_rng = np.random.default_rng(seed + 123000)
    late = np.concatenate([np.zeros(300, dtype=np.int64), late_rng.permutation([0] * 300 + [1] * 600)])
    tail_rng = np.random.default_rng(seed + 124000)
    tail = tail_rng.permutation([0] * 600 + [1] * 600)
    schedules = {}
    for arm, prefix in (("early", early), ("late", late)):
        ops = np.concatenate([prefix, tail])
        cursors = [0, 0]
        course = []
        for op in ops:
            op = int(op)
            course.append((op, int(values[op][cursors[op]])))
            cursors[op] += 1
        schedules[arm] = np.asarray(course, dtype="<i8")
        assert cursors == [1200, 1200]
        assert Counter(map(tuple, schedules[arm].tolist())) == Counter({(op, value): 200 for op in (0, 1) for value in TRAIN})
        assert Counter(schedules[arm][:1200, 0].tolist()) == {0: 600, 1: 600}
        for op in (0, 1):
            assert np.array_equal(schedules[arm][schedules[arm][:, 0] == op, 1], values[op])
    assert set(schedules["early"][:2, 0]) == {0, 1}
    assert np.all(schedules["late"][:300, 0] == 0)
    assert np.array_equal(schedules["early"][1200:], schedules["late"][1200:])
    return schedules, {"value_RNG_final": value_rng_states, "early_op_RNG_final": early_rng.bit_generator.state,
                       "late_op_RNG_final": late_rng.bit_generator.state, "tail_op_RNG_final": tail_rng.bit_generator.state}


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
    cls = source_model(content)
    p = protocol()
    contents = {"source/p030_binary_continual.py": content, "plan.json": (HERE / "protocol.json").read_bytes()}
    schedule_info, initial_info = {}, {}
    for seed in p["seeds"]:
        net = cls(seed, L=13, H=69)
        assert net.parameters == 2073 and net.t == 0 and net.events == []
        assert sum(a.nbytes for label in ("p", "m", "v", "birth") for a in getattr(net, label)) == 41460
        initial_name = f"initial/seed{seed}.npz"
        contents[initial_name] = npz_bytes(full_state(net))
        initial_info[str(seed)] = {"file": initial_name, "full_state_sha256": state_sha(full_state(net))}
        schedules, rng_states = build_schedules(seed)
        for arm, course in schedules.items():
            key = f"{arm}-seed{seed}"
            name = f"schedules/{key}.npy"
            contents[name] = npy_bytes(course)
            digest = hashlib.sha256()
            for op, value in course:
                q, a = encode(int(op), int(value)), answer(int(op), int(value))
                for i, target in enumerate(a + "S"):
                    digest.update((canonical([q + a[:i], target]) + "\n").encode("utf-8"))
            schedule_info[key] = {"file": name, "shape": [2400, 2], "dtype": "<i8", "lessons": 2400,
                                  "raw_teacher_target_stream_sha256": digest.hexdigest(), "RNG_states_after_build": rng_states}
    assert file_sha(source) == sha(content)
    archive = make_zip(contents)
    manifest = {"schema": "early-mix-manifest-v1", "id": p["id"], "status": "frozen_before_formal_training",
                "author": "Codex", "protocol": p, "runtime": runtime(),
                "local_source_hashes": {name: file_sha(HERE / name) for name in CORE},
                "original_source_sha256": sha(content), "Model_AST_sha256": p["Model_AST_sha256"],
                "initial_states": initial_info, "schedules": schedule_info,
                "archive": {"file": "inputs.zip", "sha256": sha(archive), "bytes": len(archive)},
                "files": {name: {"sha256": sha(value), "bytes": len(value)} for name, value in sorted(contents.items())},
                "teacher_label_counts_per_student": {"0": 6000, "1": 3600, "S": 2400},
                "formal_optimizer_calls_before_freeze": 0, "formal_inference_calls_before_freeze": 0,
                "external_model_calls": 0}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with (output / "inputs.zip").open("xb") as stream:
        stream.write(archive)
    write(output / "manifest.json", manifest)
    frozen = {"manifest_sha256": file_sha(output / "manifest.json"), "source_hashes": manifest["local_source_hashes"],
              "inputs_zip_sha256": manifest["archive"]["sha256"], "initial_states": initial_info,
              "schedule_file_sha256": {key: manifest["files"][row["file"]]["sha256"] for key, row in schedule_info.items()},
              "formal_optimizer_calls": 0, "formal_inference_calls": 0, "external_model_calls": 0}
    write(output / "source-freeze.json", frozen)
    return frozen


def validate_inputs(path, approved):
    path = Path(path).resolve()
    assert approved and file_sha(path) == approved, "Explicit approved manifest SHA missing or differs"
    manifest = read(path)
    assert manifest["protocol"] == protocol() and manifest["runtime"] == runtime()
    assert manifest["local_source_hashes"] == {name: file_sha(HERE / name) for name in CORE}
    archive_path = path.parent / manifest["archive"]["file"]
    assert file_sha(archive_path) == manifest["archive"]["sha256"]
    with zipfile.ZipFile(archive_path) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert set(archive.namelist()) == set(manifest["files"])
        contents = {name: archive.read(name) for name in archive.namelist()}
    for name, value in contents.items():
        assert {"sha256": sha(value), "bytes": len(value)} == manifest["files"][name]
    assert contents["plan.json"] == (HERE / "protocol.json").read_bytes()
    cls = source_model(contents["source/p030_binary_continual.py"])
    schedules, initial = {}, {}
    for seed in manifest["protocol"]["seeds"]:
        initial[str(seed)] = read_npz(contents[manifest["initial_states"][str(seed)]["file"]])
        assert state_sha(initial[str(seed)]) == manifest["initial_states"][str(seed)]["full_state_sha256"]
        assert equal_state(initial[str(seed)], full_state(cls(seed, L=13, H=69)))
        generated, _ = build_schedules(seed)
        for arm, expected in generated.items():
            key = f"{arm}-seed{seed}"
            with io.BytesIO(contents[manifest["schedules"][key]["file"]]) as stream:
                actual = np.load(stream, allow_pickle=False)
            assert actual.dtype.str == "<i8" and np.array_equal(actual, expected)
            schedules[key] = actual
    return manifest, cls, initial, schedules


class Trace:
    def __init__(self, path, replay):
        self.stream = gzip.open(path, "rt" if replay else "xt", encoding="utf-8", newline="\n")
        self.replay, self.count, self.digest = replay, 0, hashlib.sha256()

    def observe(self, row):
        line = canonical(row) + "\n"
        if self.replay:
            assert self.stream.readline() == line, f"Target replay mismatch at {self.count}"
        else:
            self.stream.write(line)
        self.digest.update(line.encode("utf-8"))
        self.count += 1

    def close(self):
        if self.replay:
            assert not self.stream.readline(), "Replay omitted target records"
        self.stream.close()
        return {"targets": self.count, "uncompressed_sha256": self.digest.hexdigest()}


def observed_lesson(net, q, a, metadata, trace, replay):
    predictions, total, position = "", 0., 0
    native = net.step

    def step(prefix, label):
        nonlocal predictions, total, position
        assert prefix == q + a[:position] and label == (a + "S")[position]
        pred, loss = native(prefix, label)
        assert np.isfinite(loss)
        trace.observe({**metadata, "position_zero_based": position, "prefix": prefix, "target": label,
                       "prediction": pred, "loss": loss, "global_update": net.t, "train_dense_MAC": net.train_macs,
                       "inference_calls": net.inference_calls, "inference_dense_MAC": net.inference_macs,
                       "full_state_sha256": state_sha(full_state(net))})
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
            result = net.lesson(q, a)
        finally:
            del net.step
        assert result == (predictions, total)
    assert position == len(a) + 1
    return predictions, total


def train_one(cls, saved_initial, course, output, arm, seed, replay=False):
    key = f"{arm}-seed{seed}"
    folder = output / key
    if not replay:
        folder.mkdir()
    net = restore(cls, saved_initial)
    trace_path = folder / "targets.jsonl.gz"
    trace = Trace(trace_path, replay)
    checkpoints = []
    started = time.perf_counter()

    def checkpoint(lesson):
        assert net.t == lesson * 5 and net.train_macs == net.t * 4209
        assert net.inference_calls == net.inference_macs == 0 and net.events == []
        assert all(a.dtype == np.float32 and np.isfinite(a).all() for label in ("p", "m", "v") for a in getattr(net, label))
        path = folder / f"state-{lesson:04}.npz"
        if replay:
            assert equal_state(full_state(net), read_npz(path.read_bytes()))
        else:
            save_state(path, net)
        checkpoints.append({"lesson": lesson, "updates": net.t, "training_dense_MAC": net.train_macs,
                            "full_state_sha256": state_sha(full_state(net))})

    try:
        checkpoint(0)
        for lesson, (op, value) in enumerate(course, 1):
            op, value = int(op), int(value)
            observed_lesson(net, encode(op, value), answer(op, value), {"lesson": lesson, "op": op, "value": value}, trace, replay)
            if lesson in (300, 1200, 2400):
                checkpoint(lesson)
                print(canonical({"mode": "replay" if replay else "primary", "arm": arm, "seed": seed, "lesson": lesson}), flush=True)
        result = trace.close()
        assert net.t == result["targets"] == 12000 and net.train_macs == 50508000
        summary = {"arm": arm, "seed": seed, "lessons": 2400, "targets": net.t, "training_dense_MAC": net.train_macs,
                   "training_inference_calls": net.inference_calls, "training_inference_MAC": net.inference_macs,
                   "parameters": net.parameters, "p_m_v_birth_array_bytes": 41460, "checkpoints": checkpoints,
                   "trace": result, "trace_file_sha256": file_sha(trace_path), "final_full_state_sha256": state_sha(full_state(net))}
        if replay:
            assert summary == read(folder / "training-summary.json")
            assert equal_state(full_state(net), read_npz((folder / "final-state.npz").read_bytes()))
        else:
            save_state(folder / "final-state.npz", net)
            write(folder / "training-summary.json", summary)
        return {"arm": arm, "seed": seed, "mode": "replay" if replay else "primary", "seconds": time.perf_counter() - started}
    except Exception:
        if not trace.stream.closed:
            trace.stream.close()
        save_state(folder / ("replay-failure-state.npz" if replay else "primary-failure-state.npz"), net)
        raise


def generate(net, q):
    tokens, details = "", []
    for _ in range(8):
        prefix = q + tokens
        if len(prefix) > net.L:
            return {"tokens": tokens, "overflow": True, "cap_exhausted": False, "steps": details}
        logits = net.forward(prefix)[2].copy()
        token = "01S"[int(logits.argmax())]
        tokens += token
        details.append({"prefix": prefix, "prediction": token, "logits_01S": logits.tolist()})
        if token == "S":
            return {"tokens": tokens, "overflow": False, "cap_exhausted": False, "steps": details}
    return {"tokens": tokens, "overflow": False, "cap_exhausted": True, "steps": details}


def metric(rows):
    return {"questions": len(rows), "whole_correct": sum(row["whole_correct"] for row in rows),
            "TF_data_bits_correct": sum(token["prediction"] == token["target"] for row in rows for token in row["TF"][:3]),
            "TF_data_bits_total": 3 * len(rows),
            "TF_tail0_correct": sum(row["TF"][3]["prediction"] == "0" for row in rows),
            "TF_STOP_correct": sum(row["TF"][4]["prediction"] == "S" for row in rows),
            "free_STOP_position_correct": sum(row["STOP_position_correct"] for row in rows),
            "wrong_as_other_op_full_answer": sum(row["wrong_as_other_op_full_answer"] for row in rows),
            "overflows": sum(row["generation"]["overflow"] for row in rows),
            "cap_exhausted": sum(row["generation"]["cap_exhausted"] for row in rows),
            "TF_CE_mean": sum(token["target_CE"] for row in rows for token in row["TF"]) / (5 * len(rows))}


def evaluate(net):
    before = net.state()
    calls, macs = net.inference_calls, net.inference_macs
    rows = []
    for op in (0, 1):
        for value in range(8):
            q, a = encode(op, value), answer(op, value)
            tf = []
            for position, label in enumerate(a + "S"):
                logits = net.forward(q + a[:position])[2].astype(np.float64)
                logp = logits - np.logaddexp.reduce(logits)
                tf.append({"position": position, "prefix": q + a[:position], "target": label,
                           "prediction": "01S"[int(logits.argmax())], "logits_01S": logits.tolist(),
                           "probabilities_01S": np.exp(logp).tolist(), "target_CE": -float(logp["01S".index(label)])})
            free = generate(net, q)
            rows.append({"op": op, "value": value, "split": "train" if value in TRAIN else "diagnostic_heldout_exposed",
                         "Q": q, "A": a, "expected": a + "S", "generation": free, "TF": tf,
                         "whole_correct": free["tokens"] == a + "S" and not free["overflow"],
                         "STOP_position_correct": free["tokens"].endswith("S") and len(free["tokens"]) == 5,
                         "wrong_as_other_op_full_answer": free["tokens"] == answer(1 - op, value) + "S"})
    by_key = {(row["op"], row["value"]): row for row in rows}
    probes = []
    for value in range(8):
        a, b = by_key[0, value], by_key[1, value]
        assert [i for i, pair in enumerate(zip(a["Q"], b["Q"])) if pair[0] != pair[1]] == [3]
        first = [a["TF"][0], b["TF"][0]]
        assert all(point["prefix"] == row["Q"] for point, row in zip(first, (a, b)))
        probes.append({"value": value, "A_prefix": "", "only_changed_Q_position": 3,
                       "predictions": [point["prediction"] for point in first], "targets": [point["target"] for point in first],
                       "raw_token_flip": first[0]["prediction"] != first[1]["prediction"],
                       "both_correct_and_flip": all(point["prediction"] == point["target"] for point in first),
                       "TF_cache_refs": [[0, value, 0], [1, value, 0]]})
    scores = {str(op): {"train": metric([row for row in rows if row["op"] == op and row["value"] in TRAIN]),
                        "diagnostic_heldout_exposed": metric([row for row in rows if row["op"] == op and row["value"] not in TRAIN])}
              for op in (0, 1)}
    both = {"train": sum(by_key[0, value]["whole_correct"] and by_key[1, value]["whole_correct"] for value in TRAIN),
            "diagnostic_heldout_exposed": sum(by_key[0, value]["whole_correct"] and by_key[1, value]["whole_correct"] for value in (5, 6)),
            "train_total": 6, "diagnostic_total": 2}
    assert equal_state(before, net.state())
    return {"metrics_by_op": scores, "same_payload_both_ops_correct": both, "truth": rows,
            "opcode_only_empty_A_prefix_probe": {"pairs": probes, "total": 8,
                                                   "raw_token_flip": sum(row["raw_token_flip"] for row in probes),
                                                   "both_correct_and_flip": sum(row["both_correct_and_flip"] for row in probes),
                                                   "extra_forward_calls": 0},
            "inference_calls": net.inference_calls - calls, "inference_dense_MAC": net.inference_macs - macs,
            "learning_state_unchanged": True}


def execute(manifest_path, approved, prereg_commit, output):
    assert re.fullmatch(r"[0-9a-f]{40}", prereg_commit or ""), "Actual preregistration commit required"
    manifest, cls, initials, schedules = validate_inputs(manifest_path, approved)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "manifest.json", manifest)
    write(output / "execution-start.json", {"author": "Codex", "manifest_sha256": approved, "preregistration_commit": prereg_commit,
                                           "commit_scope": "Coordinator-supplied Git ID, no local Git operations by runner", "auto_retry": False})
    timings, students = [], []
    started = time.perf_counter()
    try:
        for replay in (False, True):
            for seed in manifest["protocol"]["seeds"]:
                for arm in manifest["protocol"]["arms"]:
                    timings.append(train_one(cls, initials[str(seed)], schedules[f"{arm}-seed{seed}"], output, arm, seed, replay))
        validate_inputs(manifest_path, approved)
        # Every primary and full replay is finished before the first inference call.
        for seed in manifest["protocol"]["seeds"]:
            for arm in manifest["protocol"]["arms"]:
                folder = output / f"{arm}-seed{seed}"
                points = []
                for lesson in manifest["protocol"]["checkpoint_lessons"]:
                    net = restore(cls, read_npz((folder / f"state-{lesson:04}.npz").read_bytes()))
                    before = net.state()
                    result = evaluate(net)
                    assert equal_state(before, net.state())
                    name = f"truth-{lesson:04}.json"
                    write(folder / name, result)
                    points.append({"lesson": lesson, "updates": net.t, "training_dense_MAC": net.train_macs,
                                   "truth_file": name, **{key: value for key, value in result.items() if key != "truth"}})
                write(folder / "curve.json", points)
                write(folder / "final-failures.json", [row for row in result["truth"] if not row["whole_correct"]])
                students.append({"arm": arm, "seed": seed, "points": points, "final": points[-1]})
        validate_inputs(manifest_path, approved)
        summary = {"id": manifest["id"], "author": "Codex", "status": "complete", "manifest_sha256": approved,
                   "preregistration_commit": prereg_commit, "students": students, "complete_primary_students": 6, "exact_replays": 6,
                   "primary_targets": 72000, "replay_targets": 72000, "primary_training_dense_MAC": 303048000,
                   "replay_training_dense_MAC": 303048000, "training_inference_calls": 0,
                   "offline_inference_calls": sum(point["inference_calls"] for row in students for point in row["points"]),
                   "offline_inference_dense_MAC": sum(point["inference_dense_MAC"] for row in students for point in row["points"]),
                   "array_bytes_per_student": 41460, "external_model_calls": 0, "limits": manifest["protocol"]["limits"]}
        paired = []
        for seed in manifest["protocol"]["seeds"]:
            final = {row["arm"]: row["final"] for row in students if row["seed"] == seed}
            paired.append({"seed": seed, "difference": "early-minus-late",
                           "whole_correct_by_op_split": {str(op): {split: final["early"]["metrics_by_op"][str(op)][split]["whole_correct"] - final["late"]["metrics_by_op"][str(op)][split]["whole_correct"]
                                                                   for split in ("train", "diagnostic_heldout_exposed")} for op in (0, 1)},
                           "same_payload_both_ops_correct": {split: final["early"]["same_payload_both_ops_correct"][split] - final["late"]["same_payload_both_ops_correct"][split]
                                                             for split in ("train", "diagnostic_heldout_exposed")}})
        summary["paired_final_differences"] = paired
        write(output / "compact.json", summary)
        write(output / "timing.json", {"trajectories": timings, "total_seconds": time.perf_counter() - started,
                                      "scope": "Primary, full replay, state/trace IO, guards and offline diagnostics, not pure kernels"})
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
            parser.error("--prepare requires --source original P030 file")
        result = prepare(args.source, args.out)
    elif args.engineering:
        if args.source is None:
            parser.error("--engineering requires --source for synthetic-only checks")
        import unittest
        import test_early_mix
        test_early_mix.SOURCE = args.source
        report = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_early_mix))
        assert report.wasSuccessful()
        args.out.mkdir(parents=True, exist_ok=False)
        result = {"status": "PASS", "tests": report.testsRun, "source_hashes": {name: file_sha(HERE / name) for name in CORE},
                  "synthetic_native_optimizer_updates": test_early_mix.NATIVE_UPDATES,
                  "synthetic_native_inference_calls": test_early_mix.NATIVE_INFERENCE,
                  "formal_optimizer_updates": 0, "formal_inference_calls": 0, "external_model_calls": 0}
        write(args.out / "checks.json", result)
    else:
        if args.manifest is None or not args.approved_manifest_sha or not args.prereg_commit:
            parser.error("--execute requires --manifest, --approved-manifest-sha and --prereg-commit after coordinator gate")
        result = execute(args.manifest, args.approved_manifest_sha, args.prereg_commit, args.out)
    print(canonical(result), flush=True)


if __name__ == "__main__":
    main()
