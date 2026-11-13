"""AE1 r1 then r1+r2, frozen target-shuffle curriculum; no formal training in prepare/engineering."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
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
CORE = ("run_curriculum.py", "protocol.json", "test_curriculum.py")


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
    assert p["id"] == "AE1-PARAMETER-CURRICULUM-20261113" and p["seeds"] == [101, 202, 303]
    assert p["model"] == {"L": 80, "H": 64, "parameters": 10499}
    assert [(x["name"], x["taught_r"], x["questions_per_epoch"], x["targets_per_epoch"], x["schedule_seed_offset"], x["max_epochs"]) for x in p["phases"]] == [
        ("r1", [1], 900, 6300, 332000, 40), ("r12", [1, 2], 1800, 18000, 333000, 40)]
    assert p["maximum_updates_per_seed"] == 40 * (6300 + 18000) == 972000
    assert p["training_dense_MAC_per_target"] == 64 * (4 * 80 + 9) == 21056
    assert p["forward_dense_MAC_per_call"] == 64 * (2 * 80 + 3) == 10432
    assert p["phase_training_MAC_per_epoch"] == {"r1": 132652800, "r12": 379008000}
    assert p["maximum_training_dense_MAC_per_seed"] == 972000 * 21056 == 20466432000
    assert p["p_m_v_birth_array_bytes"] == 10499 * 20 == 209980 and p["replay_seeds"] == [101]
    return p


def source_model(content):
    p = protocol()
    assert sha(content) == p["source_sha256"]
    node = next(node for node in ast.parse(content.decode("utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "Model")
    assert sha(ast.dump(node, include_attributes=False).encode("utf-8")) == p["Model_AST_sha256"]
    namespace = {"np": np, "json": json, "__name__": "original_P030_Model_AST"}
    exec(compile(ast.Module(body=[copy.deepcopy(node)], type_ignores=[]), "<unchanged-P030-Model>", "exec"), namespace)
    return namespace["Model"]


def word(value):
    assert type(value) is int and 0 <= value < 30
    return format(value, "05b") + "0"


def encode(r, payload):
    assert r in (1, 2) and len(payload) == 4
    return "01" + "010" + format(r, "03b") + "0" + "".join(word(int(x)) for x in payload) + "111100"


def decode(raw):
    assert len(raw) == 39 and set(raw) <= {"0", "1"} and raw[:5] == "01010" and raw[8] == "0" and raw[-6:] == "111100"
    r = int(raw[5:8], 2)
    assert r in (1, 2)
    payload = []
    for start in range(9, 33, 6):
        assert raw[start + 5] == "0"
        value = int(raw[start:start + 5], 2)
        assert value < 30
        payload.append(value)
    return r, payload


def payload_bank():
    extra = np.random.default_rng(331000).integers(0, 30, size=(900, 2))
    return [[pair // 30, pair % 30, int(extra[pair, 0]), int(extra[pair, 1])] for pair in range(900)]


def questions(bank):
    rows = []
    for r in (1, 2):
        for pair, payload in enumerate(bank):
            q, a = encode(r, payload), "".join(word(x) for x in payload[:r])
            assert decode(q) == (r, payload) and len(q) == 39 and len(q + a) == 39 + 6 * r <= 80
            rows.append({"question_id": (r - 1) * 900 + pair, "pair_id": pair, "r": r, "payload": payload, "Q": q, "A": a})
    return rows


def phase_questions(rows, phase):
    return [row for row in rows if row["r"] in phase["taught_r"]]


def target_pool(rows, phase):
    by_id = {row["question_id"]: row for row in rows}
    pairs = [(by_id[(r - 1) * 900 + pair]["question_id"], position)
             for pair in range(900) for r in phase["taught_r"]
             for position in range(6 * r + 1)]
    result = np.asarray(pairs, dtype="<u2")
    assert len(result) == phase["targets_per_epoch"]
    return result


def schedules(seed, rows, phase):
    pool = target_pool(rows, phase)
    rng = np.random.default_rng(seed + phase["schedule_seed_offset"])
    actual = np.stack([pool[rng.permutation(len(pool))] for _ in range(phase["max_epochs"])])
    return actual, copy.deepcopy(rng.bit_generator.state)


def data_checks(bank, rows, p):
    assert len(bank) == len({tuple(x) for x in bank}) == 900
    assert len(rows) == len({row["Q"] for row in rows}) == 1800
    assert [(x[0], x[1]) for x in bank] == [(a, b) for a in range(30) for b in range(30)]
    counts = [{str(value): sum(payload[position] == value for payload in bank) for value in range(30)} for position in range(4)]
    assert all(count == 30 for position in (0, 1) for count in counts[position].values())
    labels = {}
    for row in rows:
        for position, label in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            assert prefix not in labels or labels[prefix] == label
            labels[prefix] = label
    return {"payloads": 900, "questions": 1800, "first_two_combinations": 900, "possible_four_word_payloads": 30 ** 4,
            "word_position_counts": counts, "consistent_unique_teacher_prefixes": len(labels),
            "phase_targets": {phase["name"]: len(target_pool(rows, phase)) for phase in p["phases"]}}


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
    source_bytes = Path(source).read_bytes()
    cls, p = source_model(source_bytes), protocol()
    bank = payload_bank()
    rows = questions(bank)
    checks = data_checks(bank, rows, p)
    contents = {"source/p030_binary_continual.py": source_bytes, "plan.json": (HERE / "protocol.json").read_bytes(),
                "payloads.json": (canonical(bank) + "\n").encode("utf-8"), "questions.json": (canonical(rows) + "\n").encode("utf-8")}
    initial, courses = {}, {}
    for seed in p["seeds"]:
        net = cls(seed, L=80, H=64)
        assert net.parameters == 10499 and net.t == net.train_macs == net.inference_calls == net.inference_macs == 0 and net.events == []
        assert sum(x.nbytes for label in ("p", "m", "v", "birth") for x in getattr(net, label)) == 209980
        name = f"initial/seed{seed}.npz"
        contents[name] = npz_bytes(full_state(net))
        initial[str(seed)] = {"file": name, "full_state_sha256": state_sha(full_state(net))}
        for phase in p["phases"]:
            actual, rng_state = schedules(seed, rows, phase)
            key = f"seed{seed}-{phase['name']}"
            name = f"orders/{key}.npy"
            contents[name] = npy_bytes(actual)
            courses[key] = {"file": name, "dtype": "<u2", "shape": list(actual.shape),
                            "schedule_seed": seed + phase["schedule_seed_offset"], "final_schedule_RNG": rng_state}
    archive = make_zip(contents)
    assert file_sha(source) == sha(source_bytes)
    manifest = {"schema": "ae1-parameter-curriculum-v1", "id": p["id"], "status": "frozen_before_formal_training",
                "author": "Codex", "protocol": p, "runtime": runtime(), "data_checks": checks,
                "source_hashes": {name: file_sha(HERE / name) for name in CORE}, "initial_states": initial, "schedules": courses,
                "archive": {"file": "inputs.zip", "sha256": sha(archive), "bytes": len(archive)},
                "files": {name: {"sha256": sha(value), "bytes": len(value)} for name, value in sorted(contents.items())},
                "formal_optimizer_calls_before_freeze": 0, "formal_forward_calls_before_freeze": 0, "external_model_calls": 0}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with (output / "inputs.zip").open("xb") as stream:
        stream.write(archive)
    write(output / "manifest.json", manifest)
    freeze = {"manifest_sha256": file_sha(output / "manifest.json"), "source_hashes": manifest["source_hashes"],
              "inputs_zip_sha256": manifest["archive"]["sha256"], "inputs_zip_bytes": len(archive),
              "schedule_sha256": {name: manifest["files"][value["file"]]["sha256"] for name, value in courses.items()},
              "initial_states": initial, "formal_optimizer_calls": 0, "formal_forward_calls": 0, "external_model_calls": 0}
    write(output / "source-freeze.json", freeze)
    return freeze


def validate_inputs(path, approved):
    path = Path(path).resolve()
    assert approved and file_sha(path) == approved, "Explicit approved manifest SHA missing or differs"
    manifest = read(path)
    p = protocol()
    assert manifest["protocol"] == p and manifest["runtime"] == runtime()
    assert manifest["source_hashes"] == {name: file_sha(HERE / name) for name in CORE}
    archive_path = path.parent / manifest["archive"]["file"]
    assert file_sha(archive_path) == manifest["archive"]["sha256"]
    with zipfile.ZipFile(archive_path) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) and set(archive.namelist()) == set(manifest["files"])
        contents = {name: archive.read(name) for name in archive.namelist()}
    for name, value in contents.items():
        assert {"sha256": sha(value), "bytes": len(value)} == manifest["files"][name]
    assert contents["plan.json"] == (HERE / "protocol.json").read_bytes()
    bank = json.loads(contents["payloads.json"].decode("utf-8"))
    rows = json.loads(contents["questions.json"].decode("utf-8"))
    assert bank == payload_bank() and rows == questions(bank) and data_checks(bank, rows, p) == manifest["data_checks"]
    cls = source_model(contents["source/p030_binary_continual.py"])
    initial, courses = {}, {}
    for seed in p["seeds"]:
        initial[str(seed)] = read_npz(contents[manifest["initial_states"][str(seed)]["file"]])
        assert equal_state(initial[str(seed)], full_state(cls(seed, L=80, H=64)))
        assert state_sha(initial[str(seed)]) == manifest["initial_states"][str(seed)]["full_state_sha256"]
        for phase in p["phases"]:
            key = f"seed{seed}-{phase['name']}"
            actual = np.load(io.BytesIO(contents[manifest["schedules"][key]["file"]]), allow_pickle=False)
            expected, rng_state = schedules(seed, rows, phase)
            assert actual.dtype.str == "<u2" and np.array_equal(actual, expected)
            assert rng_state == manifest["schedules"][key]["final_schedule_RNG"]
            courses[key] = actual
    return manifest, cls, rows, initial, courses


class EpochTrace:
    def __init__(self):
        self.digest = hashlib.sha256()
        self.targets = self.correct = 0
        self.loss = 0.

    def observe(self, qid, position, pred, loss, target):
        assert np.isfinite(loss)
        self.digest.update((canonical([qid, position, pred, loss]) + "\n").encode("utf-8"))
        self.targets += 1
        self.correct += pred == target
        self.loss += loss

    def result(self):
        return {"targets": self.targets, "pre_update_prediction_correct": self.correct, "CE_loss_sum": self.loss,
                "CE_loss_mean": self.loss / self.targets, "canonical_target_trace_sha256": self.digest.hexdigest()}


def update_target(net, row, position, trace):
    prefix, label = row["Q"] + row["A"][:position], (row["A"] + "S")[position]
    pred, loss = net.step(prefix, label)
    trace.observe(row["question_id"], position, pred, loss, label)


def generate(net, q):
    tokens = ""
    for _ in range(32):
        prefix = q + tokens
        if len(prefix) > net.L:
            return {"tokens": tokens, "context_exhausted": True, "cap_exhausted": False}
        token = "01S"[int(net.forward(prefix)[2].argmax())]
        tokens += token
        if token == "S":
            return {"tokens": tokens, "context_exhausted": False, "cap_exhausted": False}
    return {"tokens": tokens, "context_exhausted": False, "cap_exhausted": True}


def probe(net, rows):
    before = net.state()
    calls, macs = net.inference_calls, net.inference_macs
    outputs = []
    for row in rows:
        generated = generate(net, row["Q"])
        outputs.append({"question_id": row["question_id"], "r": row["r"], "pair_id": row["pair_id"], **generated,
                        "whole_correct": generated["tokens"] == row["A"] + "S" and not generated["context_exhausted"]})
    assert equal_state(before, net.state())
    scores = {str(r): {"whole_correct": sum(x["whole_correct"] for x in outputs if x["r"] == r),
                       "questions": sum(x["r"] == r for x in outputs)} for r in sorted({x["r"] for x in rows})}
    return {"scores": scores, "rows": outputs, "inference_calls": net.inference_calls - calls, "inference_dense_MAC": net.inference_macs - macs}


def phase_decision(phase, streak, scores, epoch):
    assert set(scores) == {str(r) for r in phase["taught_r"]}
    full = all(scores[str(r)]["questions"] == scores[str(r)]["whole_correct"] == phase["questions_per_epoch"] // len(phase["taught_r"]) for r in phase["taught_r"])
    streak = streak + 1 if full else 0
    if streak >= 2:
        return streak, "advance" if phase["name"] == "r1" else "complete", full
    if epoch >= phase["max_epochs"]:
        return streak, "blocked_before_r2" if phase["name"] == "r1" else "phase2_cap_failed", full
    return streak, None, full


def run_seed(cls, initial, courses, rows, phases, output, seed, replay=False):
    folder = output / f"seed{seed}"
    if not replay:
        folder.mkdir()
    net = restore(cls, initial)
    if replay:
        assert equal_state(full_state(net), read_npz((folder / "initial-state.npz").read_bytes()))
    else:
        save_state(folder / "initial-state.npz", net)
    summaries, curve, cumulative_questions = [], [], 0
    cumulative_by_r = {"1": 0, "2": 0}
    previous_exit = None
    started = time.perf_counter()
    try:
        for phase in phases:
            phase_name = phase["name"]
            phase_folder = folder / phase_name
            if not replay:
                phase_folder.mkdir()
            entry = full_state(net)
            if previous_exit is not None:
                assert equal_state(previous_exit, entry), "Phase transition changed state"
            entry_t, entry_mac, entry_calls, entry_infer_mac = net.t, net.train_macs, net.inference_calls, net.inference_macs
            if replay:
                assert equal_state(entry, read_npz((phase_folder / "initial-state.npz").read_bytes()))
            else:
                save_state(phase_folder / "initial-state.npz", net)
            taught_rows = phase_questions(rows, phase)
            assert len(taught_rows) == phase["questions_per_epoch"]
            streak, decision, first_full, stable_pass = 0, None, None, None
            course = courses[f"seed{seed}-{phase_name}"]
            for epoch, order in enumerate(course, 1):
                trace = EpochTrace()
                start_t, start_mac = net.t, net.train_macs
                if replay:
                    for question_id, position in order:
                        qid, position = int(question_id), int(position)
                        row = rows[qid]
                        pred, loss = net.step(row["Q"] + row["A"][:position], (row["A"] + "S")[position])
                        trace.observe(qid, position, pred, loss, (row["A"] + "S")[position])
                else:
                    for question_id, position in order:
                        update_target(net, rows[int(question_id)], int(position), trace)
                training = trace.result()
                assert net.t - start_t == training["targets"] == phase["targets_per_epoch"]
                assert net.train_macs - start_mac == phase["targets_per_epoch"] * 21056
                assert (net.L, net.H, net.parameters) == (80, 64, 10499) and net.events == []
                assert all(x.dtype == np.float32 and np.isfinite(x).all() for label in ("p", "m", "v") for x in getattr(net, label))
                evaluation = probe(net, taught_rows)
                streak, decision, full = phase_decision(phase, streak, evaluation["scores"], epoch)
                if full and first_full is None:
                    first_full = epoch
                if streak >= 2:
                    stable_pass = epoch
                cumulative_questions += len(taught_rows)
                for r in phase["taught_r"]:
                    cumulative_by_r[str(r)] += sum(row["r"] == r for row in taught_rows)
                record = {"phase": phase_name, "epoch": epoch, "global_updates": net.t, "phase_updates": net.t - entry_t,
                          "training_dense_MAC": net.train_macs, "phase_training_dense_MAC": net.train_macs - entry_mac,
                          "training": training, "scores": evaluation["scores"], "streak": streak, "decision": decision,
                          "first_full_epoch": first_full, "stable_pass_epoch": stable_pass,
                          "cumulative_question_exposures": cumulative_questions, "cumulative_question_exposures_by_r": cumulative_by_r.copy(),
                          "epoch_probe_inference_calls": evaluation["inference_calls"], "epoch_probe_inference_MAC": evaluation["inference_dense_MAC"],
                          "phase_probe_inference_calls": net.inference_calls - entry_calls, "phase_probe_inference_MAC": net.inference_macs - entry_infer_mac,
                          "cumulative_probe_inference_calls": net.inference_calls, "cumulative_probe_inference_MAC": net.inference_macs,
                          "full_state_sha256": state_sha(full_state(net))}
                if replay:
                    assert record == read(phase_folder / f"epoch-{epoch:03}.json")
                    assert evaluation == read(phase_folder / f"generation-{epoch:03}.json")
                    assert equal_state(full_state(net), read_npz((phase_folder / f"state-{epoch:03}.npz").read_bytes()))
                else:
                    save_state(phase_folder / f"state-{epoch:03}.npz", net)
                    write(phase_folder / f"epoch-{epoch:03}.json", record)
                    write(phase_folder / f"generation-{epoch:03}.json", evaluation)
                curve.append(record)
                print(canonical({"mode": "replay" if replay else "primary", "seed": seed, "phase": phase_name, "epoch": epoch,
                                 "scores": evaluation["scores"], "streak": streak, "decision": decision}), flush=True)
                if decision:
                    break
            assert decision is not None
            previous_exit = full_state(net)
            summaries.append({"phase": phase_name, "epochs": epoch, "decision": decision, "first_full_epoch": first_full,
                              "stable_pass_epoch": stable_pass, "entry_full_state_sha256": state_sha(entry), "exit_full_state_sha256": state_sha(previous_exit),
                              "target_updates": net.t - entry_t, "question_exposures": epoch * len(taught_rows),
                              "training_dense_MAC": net.train_macs - entry_mac, "probe_inference_calls": net.inference_calls - entry_calls,
                              "probe_inference_MAC": net.inference_macs - entry_infer_mac, "final_scores": evaluation["scores"]})
            if replay:
                assert equal_state(full_state(net), read_npz((phase_folder / "final-state.npz").read_bytes()))
            else:
                save_state(phase_folder / "final-state.npz", net)
            if decision != "advance":
                break
        summary = {"seed": seed, "phases": summaries, "phase_reached": summaries[-1]["phase"],
                   "taught_r": phases[len(summaries) - 1]["taught_r"], "blocked_before_r2": summaries[-1]["decision"] == "blocked_before_r2",
                   "completed_curriculum": summaries[-1]["decision"] == "complete", "training_updates": net.t,
                   "training_dense_MAC": net.train_macs, "question_exposures": cumulative_questions,
                   "question_exposures_by_r": cumulative_by_r, "probe_inference_calls": net.inference_calls, "probe_inference_MAC": net.inference_macs,
                   "final_full_state_sha256": state_sha(full_state(net)), "p_m_v_birth_array_bytes": 209980}
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


def final_tf(net, taught_rows, generation):
    before = net.state()
    calls, macs = net.inference_calls, net.inference_macs
    assert len(taught_rows) == len(generation["rows"])
    truth = []
    for row, free in zip(taught_rows, generation["rows"], strict=True):
        assert row["question_id"] == free["question_id"]
        tf = []
        for position, label in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            logits = net.forward(prefix)[2].astype(np.float64)
            logp = logits - np.logaddexp.reduce(logits)
            tf.append({"position": position, "prefix": prefix, "target": label, "prediction": "01S"[int(logits.argmax())],
                       "logits_01S": logits.tolist(), "probabilities_01S": np.exp(logp).tolist(), "target_CE": -float(logp["01S".index(label)])})
        truth.append({**row, "expected": row["A"] + "S", "generation": free, "TF": tf})
    assert equal_state(before, net.state())
    expected_targets = sum(len(row["A"]) + 1 for row in taught_rows)
    assert net.inference_calls - calls == expected_targets and net.inference_macs - macs == expected_targets * 10432
    scores = {str(r): {"questions": sum(row["r"] == r for row in truth),
                       "TF_correct": sum(x["prediction"] == x["target"] for row in truth if row["r"] == r for x in row["TF"]),
                       "TF_targets": sum(len(row["TF"]) for row in truth if row["r"] == r)} for r in sorted({row["r"] for row in taught_rows})}
    return {"truth": truth, "scores": scores, "inference_calls": net.inference_calls - calls, "inference_dense_MAC": net.inference_macs - macs,
            "learning_state_unchanged": True, "free_generation_reused": True, "taught_r_only": sorted({row["r"] for row in taught_rows})}


def execute(manifest_path, approved, commit, output):
    assert re.fullmatch(r"[0-9a-f]{40}", commit or ""), "Coordinator preregistration commit required"
    manifest, cls, rows, initial, courses = validate_inputs(manifest_path, approved)
    p = manifest["protocol"]
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "manifest.json", manifest)
    write(output / "execution-start.json", {"author": "Codex", "manifest_sha256": approved, "preregistration_commit": commit,
                                           "commit_scope": "Coordinator supplied, no Git operation by runner", "auto_retry": False})
    timings = []
    started = time.perf_counter()
    try:
        for seed in p["seeds"]:
            timings.append(run_seed(cls, initial[str(seed)], courses, rows, p["phases"], output, seed))
        timings.append(run_seed(cls, initial["101"], courses, rows, p["phases"], output, 101, replay=True))
        validate_inputs(manifest_path, approved)
        students = []
        for seed in p["seeds"]:
            folder = output / f"seed{seed}"
            summary = read(folder / "training-summary.json")
            last = summary["phases"][-1]
            taught_rows = [row for row in rows if row["r"] in summary["taught_r"]]
            generation = read(folder / last["phase"] / f"generation-{last['epochs']:03}.json")
            net = restore(cls, read_npz((folder / "final-state.npz").read_bytes()))
            result = final_tf(net, taught_rows, generation)
            write(folder / "final-truth.json", result)
            write(folder / "final-failures.json", [row for row in result["truth"] if not row["generation"]["whole_correct"]])
            students.append({**summary, "replay_status": "complete_exact" if seed == 101 else "not_planned",
                             "final_TF_scores": result["scores"], "final_TF_inference_calls": result["inference_calls"],
                             "final_TF_inference_MAC": result["inference_dense_MAC"]})
        validate_inputs(manifest_path, approved)
        summary = {"id": p["id"], "status": "complete", "author": "Codex", "manifest_sha256": approved,
                   "preregistration_commit": commit, "students": students, "primary_students": 3, "exact_full_replays": [101],
                   "primary_updates": sum(x["training_updates"] for x in students), "primary_training_dense_MAC": sum(x["training_dense_MAC"] for x in students),
                   "replay_updates": students[0]["training_updates"], "replay_training_dense_MAC": students[0]["training_dense_MAC"],
                   "primary_probe_inference_calls": sum(x["probe_inference_calls"] for x in students),
                   "primary_probe_inference_MAC": sum(x["probe_inference_MAC"] for x in students),
                   "replay_probe_inference_calls": students[0]["probe_inference_calls"], "replay_probe_inference_MAC": students[0]["probe_inference_MAC"],
                   "final_TF_inference_calls": sum(x["final_TF_inference_calls"] for x in students),
                   "final_TF_inference_MAC": sum(x["final_TF_inference_MAC"] for x in students),
                   "all_completed_curriculum": all(x["completed_curriculum"] for x in students), "array_bytes_per_student": 209980,
                   "external_model_calls": 0, "limits": p["limits"]}
        write(output / "compact.json", summary)
        write(output / "timing.json", {"trajectories": timings, "total_seconds": time.perf_counter() - started,
                                      "scope": "Allprimary/probes/epochstateIO,seed101replay,inputguards,finalTF;notpurekernels"})
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
            parser.error("--prepare requires --source originalP030")
        result = prepare(args.source, args.out)
    elif args.engineering:
        if args.source is None:
            parser.error("--engineering requires --source for bounded syntheticchecks")
        import unittest
        import test_curriculum
        test_curriculum.SOURCE = args.source
        tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_curriculum))
        assert tests.wasSuccessful()
        args.out.mkdir(parents=True, exist_ok=False)
        result = {"status": "PASS", "tests": tests.testsRun, "source_hashes": {name: file_sha(HERE / name) for name in CORE},
                  "synthetic_native_optimizer_updates": test_curriculum.NATIVE_UPDATES, "synthetic_native_inference_calls": test_curriculum.NATIVE_INFERENCE,
                  "synthetic_mock_targets": test_curriculum.MOCK_TARGETS, "synthetic_mock_probes": test_curriculum.MOCK_PROBES,
                  "formal_optimizer_calls": 0, "formal_forward_calls": 0, "external_model_calls": 0}
        write(args.out / "checks.json", result)
    else:
        if args.manifest is None or not args.approved_manifest_sha or not args.prereg_commit:
            parser.error("--execute requires --manifest/--approved-manifest-sha/--prereg-commit after coordinatorgate")
        result = execute(args.manifest, args.approved_manifest_sha, args.prereg_commit, args.out)
    print(canonical(result), flush=True)


if __name__ == "__main__":
    main()
