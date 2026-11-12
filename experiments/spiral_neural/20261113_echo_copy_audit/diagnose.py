"""Read-only Echo behavior/exposure audit. --prepare and --engineering score no old student."""
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
import sys
import time
from types import SimpleNamespace
import zipfile

if sys.flags.optimize:
    raise RuntimeError("Optimized Python is disabled: assertions are required")
sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
REFERENCE_SHA = "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"
CORE_FILES = ("diagnose.py", "protocol.json", "test_diagnose.py")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def file_sha(path):
    return sha_bytes(Path(path).read_bytes())


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def state_sha(state):
    digest = hashlib.sha256()
    for name, value in sorted(state.items()):
        digest.update(canonical([name, value.dtype.str, list(value.shape)]).encode("utf-8"))
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def equal_state(a, b):
    return a.keys() == b.keys() and all(np.array_equal(value, b[name]) for name, value in a.items())


def protocol():
    p = read(HERE / "protocol.json")
    assert p["id"] == "ECHO-COPY-READONLY-20261113"
    assert p["seeds"] == [101, 202, 303] and p["snapshots"] == ["2a_echo_op2", "2b_add_neg"]
    assert p["checkpoint_shape"] == {"L": 13, "H": 69, "parameters": 2073}
    assert p["evaluated_values"] == list(range(8)) and p["training_updates"] == p["external_model_calls"] == 0
    assert [(x["name"], x["nop"], x["nd"], x["ops"]) for x in p["history_phases"]] == [
        ("0_echo_n1", 1, 1, [0]), ("1a_echo_n2", 1, 2, [0]), ("1b_echo_n3", 1, 3, [0]),
        ("2a_echo_op2", 2, 3, [0]), ("2b_add_neg", 2, 3, [0, 1])]
    return p


def encode(nop, nd, op, value):
    assert op in (0, 1) and 0 <= value < 2 ** nd
    return "01" + format(op, f"0{nop}b") + "0" + format(value, f"0{nd}b") + "0"


def answer(nd, op, value):
    bits = format(value, f"0{nd}b")
    return (bits if op == 0 else "".join("1" if bit == "0" else "0" for bit in bits)) + "0"


def ast_nodes(content):
    tree = ast.parse(content.decode("utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))}


def pure_grammar(reference):
    nodes = ast_nodes(reference)
    namespace = {"np": np}
    names = ("encode", "answer", "split", "Schedule")
    exec(compile(ast.Module(body=[copy.deepcopy(nodes[name]) for name in names], type_ignores=[]),
                 "<frozen-p030-grammar-schedule-AST>", "exec"), namespace)
    return namespace


def verify_sources(reference, historical, phases):
    assert sha_bytes(reference) == REFERENCE_SHA, "Pinned public reference differs"
    a, b = ast_nodes(reference), ast_nodes(historical)
    digests = {}
    for name in ("Model", "encode", "answer", "split", "Schedule"):
        left = ast.dump(a[name], include_attributes=False)
        assert left == ast.dump(b[name], include_attributes=False), f"Historical {name} AST differs"
        digests[name] = sha_bytes(left.encode("utf-8"))
    # Compile only pure grammar functions; neither old module or old main executes.
    grammar = pure_grammar(reference)
    for phase in phases:
        shape = SimpleNamespace(nop=phase["nop"], nd=phase["nd"], ops=tuple(phase["ops"]), end=False, reserved=[])
        assert grammar["split"](shape)[0] == phase["train"]
        for op in phase["ops"]:
            for value in range(2 ** phase["nd"]):
                assert grammar["encode"](shape, op, value) == encode(shape.nop, shape.nd, op, value)
                assert grammar["answer"](op, shape.nd, value) == answer(shape.nd, op, value)
    return digests


def model_class(reference):
    """Extract class AST only; reject every learning/growth call in this process."""
    namespace = {"np": np, "json": json, "__name__": "frozen_p030_ast_only"}
    node = copy.deepcopy(ast_nodes(reference)["Model"])
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<frozen-p030-Model-AST>", "exec"), namespace)
    cls = namespace["Model"]
    forbidden = {name: 0 for name in ("step", "lesson", "loss_grad", "grow", "forward_training")}
    for name in ("step", "lesson", "loss_grad", "grow"):
        def denied(self, *args, _name=name, **kwargs):
            forbidden[_name] += 1
            raise RuntimeError("Read-only audit forbids Model." + _name)
        setattr(cls, name, denied)
    native = cls.forward
    def guarded_forward(self, text, training=False):
        if training:
            forbidden["forward_training"] += 1
            raise RuntimeError("Read-only audit forbids training=True")
        return native(self, text, training=False)
    cls.forward = guarded_forward
    return cls, forbidden


def load_state_bytes(content):
    with np.load(io.BytesIO(content), allow_pickle=False) as archive:
        saved = {name: archive[name].copy() for name in archive.files}
    keys = {f"{label}{i}" for label in ("p", "m", "v", "birth") for i in range(4)} | {"t", "L", "H", "growth_rng"}
    assert set(saved) == keys
    L, H = int(saved["L"]), int(saved["H"])
    assert (L, H) == (13, 69)
    shapes = ((2 * L, H), (H,), (H, 3), (3,))
    for label in ("p", "m", "v", "birth"):
        for i, shape in enumerate(shapes):
            assert saved[f"{label}{i}"].shape == shape
            assert saved[f"{label}{i}"].dtype == (np.int64 if label == "birth" else np.float32)
            assert np.isfinite(saved[f"{label}{i}"]).all()
    return saved


def restore(cls, saved, seed):
    net = cls(seed, L=int(saved["L"]), H=int(saved["H"]))
    for label in ("p", "m", "v", "birth"):
        setattr(net, label, [saved[f"{label}{i}"].copy() for i in range(4)])
    net.t = int(saved["t"])
    net.growth_rng.bit_generator.state = json.loads(str(saved["growth_rng"]))
    assert equal_state(saved, net.state()) and net.parameters == 2073
    return net


class History:
    def __init__(self):
        self.prefixes, self.questions, self.answers = {}, {}, {}
        self.targets = 0
        self.phases = []

    @staticmethod
    def add_occurrence(table, key, label, location):
        if key not in table:
            table[key] = {"count": 0, "labels": {}, "first": location, "last": location, "last_label": label}
        row = table[key]
        row["count"] += 1
        row["labels"][label] = row["labels"].get(label, 0) + 1
        row["last"], row["last_label"] = location, label

    def add_phase(self, phase, trace):
        start = self.targets
        operations = Counter()
        for lesson, item in enumerate(trace, 1):
            assert isinstance(item, list) and len(item) == 3
            op, value, predictions = item
            assert type(op) is int and type(value) is int and op in phase["ops"] and value in phase["train"]
            assert isinstance(predictions, str) and set(predictions) <= {"0", "1", "S"}
            q, a = encode(phase["nop"], phase["nd"], op, value), answer(phase["nd"], op, value)
            assert len(predictions) == len(a) + 1
            # Third trace field is observed predictions, never teacher bits.
            location = {"phase": phase["name"], "lesson_index_1based": lesson, "op": op, "value": value,
                        "global_target_index_1based": self.targets + 1, "position_zero_based": 0}
            self.add_occurrence(self.questions, q, a + "S", location)
            self.add_occurrence(self.answers, a + "S", a, location)
            for position, label in enumerate(a + "S"):
                self.targets += 1
                location = {"phase": phase["name"], "lesson_index_1based": lesson, "op": op, "value": value,
                            "global_target_index_1based": self.targets, "position_zero_based": position}
                self.add_occurrence(self.prefixes, q + a[:position], label, location)
            operations[f"{op},{value}"] += 1
        self.phases.append({"phase": phase["name"], "lessons": len(trace), "targets": self.targets - start,
                            "first_global_target_index_1based": start + 1, "last_global_target_index_1based": self.targets,
                            "op_value_lesson_counts": dict(sorted(operations.items()))})

    def exposure(self, prefix, target):
        row = self.prefixes.get(prefix)
        if row is None:
            return {"raw_prefix_seen": False, "classification": "unseen", "optimizer_exposures": 0,
                    "label_counts": {}, "same_label_exposures": 0, "conflicting_label_exposures": 0,
                    "last_label": None, "last_label_matches_target": None, "first": None, "last": None}
        same = row["labels"].get(target, 0)
        conflict = row["count"] - same
        return {"raw_prefix_seen": True, "classification": "mixed" if same and conflict else "same_only" if same else "conflict_only",
                "optimizer_exposures": row["count"], "label_counts": dict(sorted(row["labels"].items())),
                "same_label_exposures": same, "conflicting_label_exposures": conflict,
                "last_label": row["last_label"], "last_label_matches_target": row["last_label"] == target,
                "first": row["first"], "last": row["last"]}


def histories_from_inputs(contents, p):
    result = {}
    grammar = pure_grammar(contents["reference/p030_reference.py"])
    for seed in p["seeds"]:
        history = History()
        for phase_index, phase in enumerate(p["history_phases"]):
            trace = json.loads(contents[f"traces/dynamic-{seed}/{phase['name']}/trace.json"].decode("utf-8"))
            shape = SimpleNamespace(nop=phase["nop"], nd=phase["nd"], ops=tuple(phase["ops"]),
                                    new=1 if phase["name"] == "2b_add_neg" else None)
            schedule = grammar["Schedule"](shape, seed + 100 * phase_index)
            assert [schedule.next() for _ in trace] == [(item[0], item[1]) for item in trace], "Actual trace order differs from original symbolic schedule"
            history.add_phase(phase, trace)
            history.phases[-1].update(schedule_seed=seed + 100 * phase_index, symbolic_original_schedule_exact=True)
            if phase["name"] in p["snapshots"]:
                name = f"dynamic-{seed}/{phase['name']}"
                saved = load_state_bytes(contents[f"checkpoints/{name}/state.npz"])
                assert history.targets == int(saved["t"]), "Trace teacher targets do not equal checkpoint.t"
                result[name] = copy.deepcopy(history)
    return result


def prefix_completion_table():
    rows = []
    for position in range(3):
        for value_prefix in range(2 ** position):
            prefix = format(value_prefix, f"0{position}b") if position else ""
            values = [value for value in (0, 1, 2, 3, 4, 7) if format(value, "03b").startswith(prefix)]
            rows.append({"output_data_position": position, "correct_answer_prefix": prefix,
                         "unique_training_values": values,
                         "next_bit_support_counts": dict(sorted(Counter(format(value, "03b")[position] for value in values).items()))})
    return {"basis": "Unique current-format Echo optimizer-training examples once each, not trace-weighted and not model predictions",
            "rows": rows, "limit": "Shows possible answer-prefix completion shortcuts; does not identify the neural mechanism"}


def verify_public_pins(contents):
    pins = json.loads(contents["provenance/public-checkpoint-pins.json"].decode("utf-8"))
    verification = json.loads(contents["provenance/published-checkpoints-verified.json"].decode("utf-8"))
    assert pins["source_manifest_Git_blob"] == "438cd02aa060c88e531afb9aafb477ad61fb2036"
    assert verification["status"] == "passed" and verification["trained_inference_calls"] == verification["optimizer_calls"] == 0
    prefix = "evidence/p030-binary-continual-20261112/"
    expected = {}
    for row in pins["checkpoints"]:
        assert row["path"].startswith(prefix)
        name = "checkpoints/" + row["path"][len(prefix):]
        assert name not in expected
        expected[name] = {"sha256": row["sha256"], "bytes": row["bytes"]}
        assert {"sha256": sha_bytes(contents[name]), "bytes": len(contents[name])} == expected[name]
    assert set(expected) == {name for name in contents if name.startswith("checkpoints/")} and len(expected) == 6
    assert {row["path"]: (row["sha256"], row["bytes"]) for row in verification["models"]} == {
        row["path"]: (row["sha256"], row["bytes"]) for row in pins["checkpoints"]}
    return {"source_commit": pins["source_commit"], "source_manifest": pins["source_manifest"],
            "source_manifest_Git_blob": pins["source_manifest_Git_blob"], "six_raw_checkpoint_SHA_matches": True}


def input_paths(workspace, p):
    root = Path(workspace).resolve()
    result = {"reference/p030_reference.py": root / "work/sle-ur1-20261113/source/experiments/spiral_neural/20261112_p035/reference/p030_reference.py",
              "reference/p030_binary_continual.py": root / "outputs/sle-research-review/p030_binary_continual.py",
              "provenance/public-checkpoint-pins.json": root / "work/echo-copy-audit-20261113/public-checkpoint-pins.json",
              "provenance/published-checkpoints-verified.json": root / "work/echo-copy-audit-20261113/published-checkpoints-verified.json"}
    old = root / "work/sle-research-review/p030-binary-continual-20261112"
    for seed in p["seeds"]:
        for phase in p["history_phases"]:
            ref = f"dynamic-{seed}/{phase['name']}"
            result[f"traces/{ref}/trace.json"] = old / ref / "trace.json"
        for snapshot in p["snapshots"]:
            ref = f"dynamic-{seed}/{snapshot}"
            result[f"checkpoints/{ref}/state.npz"] = old / ref / "state.npz"
    assert len(result) == 25
    return result


def zip_bytes(contents):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(contents.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def prepare(workspace, output):
    p = protocol()
    paths = input_paths(workspace, p)
    contents = {name: path.read_bytes() for name, path in paths.items()}
    provenance = verify_public_pins(contents)
    ast_hashes = verify_sources(contents["reference/p030_reference.py"], contents["reference/p030_binary_continual.py"], p["history_phases"])
    histories = histories_from_inputs(contents, p)
    archive = zip_bytes(contents)
    assert all(file_sha(paths[name]) == sha_bytes(content) for name, content in contents.items())
    manifest = {"schema": "echo-copy-input-manifest-v1", "id": p["id"], "status": "prepared_before_new_checkpoint_inference",
                "author": "Codex", "protocol": p,
                "source_hashes": {name: file_sha(HERE / name) for name in CORE_FILES}, "model_AST_sha256": ast_hashes,
                "public_checkpoint_provenance": provenance, "curriculum_answer_prefix_support": prefix_completion_table(),
                "runtime": {"python": platform.python_version(), "numpy": np.__version__, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
                "archive": {"file": "inputs.zip", "sha256": sha_bytes(archive), "bytes": len(archive)},
                "files": {name: {"sha256": sha_bytes(content), "bytes": len(content)} for name, content in sorted(contents.items())},
                "snapshots": {name: {"learning_state_sha256": state_sha(load_state_bytes(contents[f"checkpoints/{name}/state.npz"])),
                                     "optimizer_targets_reconstructed": history.targets, "phase_exposures": history.phases}
                              for name, history in histories.items()},
                "optimizer_calls": 0, "formal_checkpoint_forward_calls": 0, "external_model_calls": 0}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with (output / "inputs.zip").open("xb") as stream:
        stream.write(archive)
    write(output / "input-manifest.json", manifest)
    frozen = {"input_manifest_sha256": file_sha(output / "input-manifest.json"), "source_hashes": manifest["source_hashes"],
              "inputs_zip_sha256": manifest["archive"]["sha256"], "model_AST_sha256": ast_hashes,
              "snapshots": {name: row["learning_state_sha256"] for name, row in manifest["snapshots"].items()},
              "optimizer_calls": 0, "formal_checkpoint_forward_calls": 0, "external_model_calls": 0}
    write(output / "source-freeze.json", frozen)
    return frozen


def validated_inputs(manifest_path, approved_sha):
    manifest_path = Path(manifest_path).resolve()
    assert approved_sha and file_sha(manifest_path) == approved_sha, "Explicit approved manifest SHA is missing or differs"
    manifest = read(manifest_path)
    assert manifest["protocol"] == protocol()
    assert manifest["source_hashes"] == {name: file_sha(HERE / name) for name in CORE_FILES}
    assert manifest["runtime"] == {"python": platform.python_version(), "numpy": np.__version__, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    archive_path = manifest_path.parent / manifest["archive"]["file"]
    assert file_sha(archive_path) == manifest["archive"]["sha256"]
    with zipfile.ZipFile(archive_path) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert set(archive.namelist()) == set(manifest["files"])
        contents = {name: archive.read(name) for name in archive.namelist()}
    for name, content in contents.items():
        assert {"sha256": sha_bytes(content), "bytes": len(content)} == manifest["files"][name]
    assert verify_public_pins(contents) == manifest["public_checkpoint_provenance"]
    assert verify_sources(contents["reference/p030_reference.py"], contents["reference/p030_binary_continual.py"], protocol()["history_phases"]) == manifest["model_AST_sha256"]
    return manifest, contents, archive_path


def generation(net, q):
    tokens, details = "", []
    for _ in range(8):
        prefix = q + tokens
        if len(prefix) > net.L:
            return {"tokens": tokens, "overflow": True, "cap_exhausted": False, "steps": details}
        logits = net.forward(prefix)[2].copy()
        prediction = "01S"[int(logits.argmax())]
        details.append({"prefix": prefix, "prediction": prediction, "logits_01S": logits.tolist()})
        tokens += prediction
        if prediction == "S":
            return {"tokens": tokens, "overflow": False, "cap_exhausted": False, "steps": details}
    return {"tokens": tokens, "overflow": False, "cap_exhausted": True, "steps": details}


def pair_diagnostics(tf_rows):
    current, future = [], []
    for j in range(3):
        for k in range(j, 3):
            for left in range(8):
                right = left ^ (1 << (2 - k))
                if left > right:
                    continue
                a, b = tf_rows[left][j], tf_rows[right][j]
                assert a["correct_earlier_A_prefix"] == b["correct_earlier_A_prefix"]
                assert (a["target"] != b["target"]) == (j == k)
                both = a["prediction"] == a["target"] and b["prediction"] == b["target"]
                row = {"output_data_position_j": j, "flipped_Q_data_position_k": k, "values": [left, right],
                       "same_correct_earlier_A_prefix": a["correct_earlier_A_prefix"],
                       "TF_cache_refs": [[left, j], [right, j]], "targets": [a["target"], b["target"]],
                       "predictions": [a["prediction"], b["prediction"]], "both_correct": both,
                       "logit_delta_linf": float(np.max(np.abs(np.array(a["logits_01S"]) - np.array(b["logits_01S"]))))}
                if j == k:
                    row.update(raw_predicted_token_flip=a["prediction"] != b["prediction"], both_correct_and_follow=both)
                    current.append(row)
                else:
                    row.update(raw_predicted_token_invariant=a["prediction"] == b["prediction"], both_correct_and_invariant=both)
                    future.append(row)
    assert len(current) == len(future) == 12
    assert len({tuple(row["values"]) for row in future}) == 8
    return {"current_bit": {"conditional_pairs": 12, "distinct_whole_Q_pairs": 12,
                            "both_correct_and_follow": sum(row["both_correct_and_follow"] for row in current),
                            "raw_predicted_token_flip": sum(row["raw_predicted_token_flip"] for row in current), "rows": current},
            "future_bit": {"conditional_pairs": 12, "distinct_whole_Q_pairs": 8,
                           "both_correct_and_invariant": sum(row["both_correct_and_invariant"] for row in future),
                           "raw_predicted_token_invariant": sum(row["raw_predicted_token_invariant"] for row in future), "rows": future},
            "additional_forward_calls": 0, "cached_data_logits": 24,
            "sampling_limit": "Overlapping deterministic conditions over8 inputs; not independent statistical samples"}


def evaluate_snapshot(net, history):
    before = net.state()
    calls, macs = net.inference_calls, net.inference_macs
    rows, cache = [], {}
    for value in range(8):
        q, a = encode(2, 3, 0, value), answer(3, 0, value)
        free = generation(net, q)
        tf = []
        for position, target in enumerate(a + "S"):
            prefix = q + a[:position]
            logits = net.forward(prefix)[2].astype(np.float64)
            logp = logits - np.logaddexp.reduce(logits)
            tf.append({"position_zero_based": position, "role": "data" if position < 3 else "tail0" if position == 3 else "STOP",
                       "prefix": prefix, "target": target, "correct_earlier_A_prefix": a[:position],
                       "prediction": "01S"[int(logits.argmax())], "logits_01S": logits.tolist(),
                       "probabilities_01S": np.exp(logp).tolist(), "target_CE": -float(logp["01S".index(target)]),
                       "history_exposure": history.exposure(prefix, target)})
        cache[value] = tf[:3]
        whole = history.questions.get(q)
        teacher_answer = history.answers.get(a + "S")
        rows.append({"value": value, "historical_role": "optimizer_train" if value in (0, 1, 2, 3, 4, 7) else "validation_used_in_stage_gate" if value == 5 else "test_already_viewed",
                     "Q": q, "A": a, "expected": a + "S", "generation": free,
                     "whole_correct": free["tokens"] == a + "S" and not free["overflow"],
                     "STOP_position_correct": free["tokens"].endswith("S") and len(free["tokens"]) == len(a) + 1,
                     "whole_Q_optimizer_seen": whole is not None, "whole_Q_exposure": whole,
                     "whole_answer_bits_ever_teacher_answer": teacher_answer is not None,
                     "whole_answer_with_STOP_ever_teacher_answer": teacher_answer is not None,
                     "whole_answer_teacher_exposure": teacher_answer, "teacher_forcing": tf})
    pairs = pair_diagnostics(cache)
    assert equal_state(before, net.state()), "Diagnostic changed learning state"
    assert net.train_macs == 0
    exposure_counts = Counter(token["history_exposure"]["classification"] for row in rows for token in row["teacher_forcing"])
    summary = {"whole_correct": sum(row["whole_correct"] for row in rows), "whole_total": 8,
               "optimizer_train_whole_correct": sum(row["whole_correct"] for row in rows if row["value"] in (0, 1, 2, 3, 4, 7)),
               "validation5_whole_correct": rows[5]["whole_correct"], "test6_whole_correct": rows[6]["whole_correct"],
               "TF_data_correct": sum(token["prediction"] == token["target"] for row in rows for token in row["teacher_forcing"][:3]),
               "TF_data_targets": 24, "TF_all_correct": sum(token["prediction"] == token["target"] for row in rows for token in row["teacher_forcing"]),
               "TF_all_targets": 40, "TF_prefix_exposure_categories": dict(sorted(exposure_counts.items())),
               "current_both_correct_and_follow": pairs["current_bit"]["both_correct_and_follow"],
               "current_raw_flip": pairs["current_bit"]["raw_predicted_token_flip"],
               "future_both_correct_and_invariant": pairs["future_bit"]["both_correct_and_invariant"],
               "future_raw_invariant": pairs["future_bit"]["raw_predicted_token_invariant"],
               "inference_calls": net.inference_calls - calls, "inference_dense_MAC": net.inference_macs - macs,
               "learning_state_before_sha256": state_sha(before), "learning_state_after_sha256": state_sha(net.state()),
               "history_optimizer_targets": history.targets, "optimizer_calls": 0}
    return {"summary": summary, "truth": rows, "pair_diagnostics": pairs,
            "history_ledger": {"phases": history.phases, "targets": history.targets,
                               "raw_prefixes": history.prefixes, "whole_questions": history.questions, "teacher_answers_with_STOP": history.answers}}


def execute(manifest_path, approved_sha, output):
    manifest, contents, archive_path = validated_inputs(manifest_path, approved_sha)
    histories = histories_from_inputs(contents, manifest["protocol"])
    cls, forbidden = model_class(contents["reference/p030_reference.py"])
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "input-manifest.json", manifest)
    started, summaries = time.perf_counter(), []
    try:
        for name, history in histories.items():
            seed = int(name.split("/")[0].split("-")[1])
            saved = load_state_bytes(contents[f"checkpoints/{name}/state.npz"])
            assert state_sha(saved) == manifest["snapshots"][name]["learning_state_sha256"]
            net = restore(cls, saved, seed)
            result = evaluate_snapshot(net, history)
            assert equal_state(saved, net.state())
            result["snapshot"], result["seed"] = name, seed
            write(output / (name.replace("/", "--") + ".json"), result)
            summaries.append({"snapshot": name, "seed": seed, **result["summary"]})
        assert not any(forbidden.values())
        validated_inputs(manifest_path, approved_sha)
        assert file_sha(archive_path) == manifest["archive"]["sha256"]
        summary = {"id": manifest["id"], "status": "complete", "author": "Codex", "input_manifest_sha256": approved_sha,
                   "snapshots": summaries, "snapshot_count": 6, "optimizer_call_guards": forbidden,
                   "inference_calls": sum(row["inference_calls"] for row in summaries),
                   "inference_dense_MAC": sum(row["inference_dense_MAC"] for row in summaries),
                   "pair_extra_forward_calls": 0, "source_checkpoint_trace_hashes_unchanged": True,
                   "curriculum_answer_prefix_support": manifest["curriculum_answer_prefix_support"],
                   "learning_state_all_exact_unchanged": True, "external_model_calls": 0,
                   "wall_seconds": time.perf_counter() - started, "limits": manifest["protocol"]["limits"]}
        write(output / "compact.json", summary)
        return summary
    except Exception as error:
        write(output / "failure.json", {"status": "incomplete", "error": type(error).__name__, "message": str(error),
                                        "optimizer_call_guards": forbidden, "completed_snapshots": summaries})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--engineering", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--approved-manifest-sha")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.prepare:
        if args.workspace_root is None:
            parser.error("--prepare requires --workspace-root")
        result = prepare(args.workspace_root, args.out)
    elif args.engineering:
        import unittest
        import test_diagnose
        result_tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_diagnose))
        assert result_tests.wasSuccessful()
        args.out.mkdir(parents=True, exist_ok=False)
        result = {"status": "PASS", "tests": result_tests.testsRun, "source_hashes": {name: file_sha(HERE / name) for name in CORE_FILES},
                  "synthetic_only": True, "formal_checkpoint_forward_calls": 0, "optimizer_calls": 0, "external_model_calls": 0}
        write(args.out / "checks.json", result)
    else:
        if not args.manifest or not args.approved_manifest_sha:
            parser.error("--execute requires --manifest and --approved-manifest-sha after the review gate")
        result = execute(args.manifest, args.approved_manifest_sha, args.out)
    print(canonical(result), flush=True)


if __name__ == "__main__":
    main()
