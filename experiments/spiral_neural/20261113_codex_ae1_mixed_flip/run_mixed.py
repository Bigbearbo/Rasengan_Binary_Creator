"""Continue exact PR26 states with SLE-AEM1 Echo1/Echo2/Flip1; prepare is NN-free."""
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
CORE = ("run_mixed.py", "protocol.json", "test_mixed.py")

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


def source_model(content):
    p = protocol()
    assert sha(content) == p["source_sha256"]
    node = next(node for node in ast.parse(content.decode("utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "Model")
    assert sha(ast.dump(node, include_attributes=False).encode("utf-8")) == p["Model_AST_sha256"]
    namespace = {"np": np, "json": json, "__name__": "original_P030_Model_AST"}
    exec(compile(ast.Module(body=[copy.deepcopy(node)], type_ignores=[]), "<unchanged-P030-Model>", "exec"), namespace)
    return namespace["Model"]


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


def protocol():
    p = read(HERE / "protocol.json")
    assert p["id"] == "AE1-MIXED-FLIP-CONTINUATION-20261113" and p["seeds"] == [101, 202, 303]
    assert p["parent_head"] == "7213cce112a8411b13dc128c49f9e88acfc9d65f"
    assert p["model"] == {"L": 80, "H": 64, "parameters": 10499}
    assert p["parent_t"] == {"101": 151200, "202": 181800, "303": 223200}
    assert p["classes"] == ["E1", "E2", "F1"] and p["max_epochs"] == 40
    assert p["targets_per_epoch"] == 24300 and p["maximum_new_updates_per_seed"] == 972000
    assert p["training_dense_MAC_per_target"] == 21056 and p["forward_dense_MAC_per_call"] == 10432
    assert p["new_training_dense_MAC_per_epoch"] == 24300 * 21056 == 511660800
    assert p["maximum_new_training_dense_MAC_per_seed"] == 972000 * 21056 == 20466432000
    assert p["p_m_v_birth_array_bytes"] == 209980 and p["replay_seeds"] == [101]
    return p


def git_blob(content):
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


def counter_snapshot(saved):
    return {"t": int(saved["t"]), "train_MAC": int(saved["meta_train_macs"]),
            "inference_calls": int(saved["meta_inference_calls"]), "inference_MAC": int(saved["meta_inference_macs"])}


def word(value):
    assert type(value) is int and 0 <= value < 30
    return format(value, "05b") + "0"


def encode(op, r, payload):
    assert (op, r) in (("010", 1), ("010", 2), ("100", 1)) and len(payload) == 4
    return "01" + op + format(r, "03b") + "0" + "".join(word(int(x)) for x in payload) + "111100"


def flip_answer(payload):
    # Output bits are literal, including complements31/30; never call word(31/30).
    return "".join("1" if bit == "0" else "0" for bit in word(int(payload[0]))[:5]) + "0"


def expected_bank():
    extra = np.random.default_rng(331000).integers(0, 30, size=(900, 2))
    return [[pair // 30, pair % 30, int(extra[pair, 0]), int(extra[pair, 1])] for pair in range(900)]


def questions(bank, old):
    assert bank == expected_bank() and len(old) == 1800
    rows = []
    for index, row in enumerate(old):
        r, pair = index // 900 + 1, index % 900
        assert row == {"question_id": index, "pair_id": pair, "r": r, "payload": bank[pair],
                       "Q": encode("010", r, bank[pair]), "A": "".join(word(x) for x in bank[pair][:r])}
        rows.append({**row, "class": "E1" if r == 1 else "E2", "op": "010"})
    for pair, payload in enumerate(bank):
        rows.append({"question_id": 1800 + pair, "pair_id": pair, "r": 1, "payload": payload,
                     "Q": encode("100", 1, payload), "A": flip_answer(payload), "class": "F1", "op": "100"})
    return rows


def target_pool(rows):
    result = np.asarray([(offset + pair, position) for pair in range(900) for offset in (0, 900, 1800)
                         for position in range(len(rows[offset + pair]["A"]) + 1)], dtype="<u2")
    assert result.shape == (24300, 2)
    return result


def schedules(seed, rows):
    pool = target_pool(rows)
    rng = np.random.default_rng(seed + 444000)
    actual = np.stack([pool[rng.permutation(len(pool))] for _ in range(40)])
    return actual, copy.deepcopy(rng.bit_generator.state)


def data_checks(bank, rows, old):
    assert len(bank) == len({tuple(x) for x in bank}) == 900
    assert len(rows) == len({row["Q"] for row in rows}) == 2700
    labels = {}
    for index, row in enumerate(rows):
        assert row["question_id"] == index and len(row["Q"]) == 39 and len(row["Q"] + row["A"]) in (45, 51)
        for position, label in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            assert prefix not in labels or labels[prefix] == label
            labels[prefix] = label
    assert all((rows[i]["Q"], rows[i]["A"]) == (old[i]["Q"], old[i]["A"]) for i in range(1800))
    assert rows[1800]["A"] + "S" == "111110S" and rows[1830]["A"] + "S" == "111100S"
    pool = target_pool(rows)
    return {"payloads": 900, "questions": 2700, "old_Echo_QA_unchanged": 1800, "unique_teacher_prefixes": len(labels),
            "target_counts_by_class": {name: int(sum(rows[int(qid)]["class"] == name for qid in pool[:, 0])) for name in ("E1", "E2", "F1")},
            "literal_control_answer_cases_preserved": True}


def parent_inputs(parent_root, source_bytes):
    """Verify cached PUBLIC bytes; no network, old model inference or old training."""
    root, p = Path(parent_root).resolve(), protocol()
    public = root / "publication/final/public"
    publication_bytes = (public / "publication-manifest.json").read_bytes()
    assert sha(publication_bytes) == p["parent_publication_manifest_sha256"]
    assert git_blob(publication_bytes) == p["parent_publication_manifest_Git_blob"]
    publication = json.loads(publication_bytes.decode("utf-8"))
    receipt_bytes = (root / "publication-receipt.json").read_bytes()
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    assert receipt["status"] == "complete_verified" and receipt["result_commit"] == p["parent_head"]
    assert receipt["publication_manifest_sha256"] == sha(publication_bytes)
    receipts = {row["name"]: row for row in receipt["remote_file_byte_checks"]}
    def verified_archive(name):
        meta = publication["files"].get(name, publication["archives"].get(name))
        check = receipts[name]
        assert check["byte_match"] and check["ref_match"] and check["commit"] == p["parent_head"]
        assert (check["sha256"], check["Git_blob"], check["bytes"]) == (meta["sha256"], meta["Git_blob"], meta["bytes"])
        cached = root / "remote-byte-checks" / ("final-" + name)
        path = cached if cached.exists() else public / name
        raw = path.read_bytes()
        assert (sha(raw), git_blob(raw), len(raw)) == (meta["sha256"], meta["Git_blob"], meta["bytes"])
        return raw, {"file": name, "sha256": sha(raw), "Git_blob": git_blob(raw), "bytes": len(raw),
                     "verified_against_prior_public_readback": True, "verification_source": "cached_remote_ZIP" if cached.exists() else "exact_local_published_ZIP_with_prior_remote_receipt"}
    data_bytes, data_meta = verified_archive("inputs.zip")
    with zipfile.ZipFile(io.BytesIO(data_bytes)) as archive:
        bank_bytes = archive.read("payloads.json")
        old_bytes = archive.read("questions.json")
        assert archive.read("source/p030_binary_continual.py") == source_bytes
    data_meta["payloads_member_sha256"] = sha(bank_bytes)
    data_meta["old_questions_member_sha256"] = sha(old_bytes)
    contents = {"payloads.json": bank_bytes, "parent-questions.json": old_bytes,
                "provenance/parent-publication-manifest.json": publication_bytes}
    parents = {}
    for seed in p["seeds"]:
        member = f"science/seed{seed}/final-state.npz"
        names = [name for name, row in publication["archives"].items() if member in row["members"]]
        assert len(names) == 1
        archive_bytes, archive_meta = verified_archive(names[0])
        member_meta = publication["archives"][names[0]]["members"][member]
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            raw = archive.read(member)
            assert format(archive.getinfo(member).CRC, "08x") == member_meta["CRC32"]
        local = root / f"science/seed{seed}/final-state.npz"
        assert local.read_bytes() == raw
        assert (sha(raw), git_blob(raw), len(raw)) == (member_meta["sha256"], member_meta["Git_blob"], member_meta["bytes"])
        saved = read_npz(raw)
        assert (int(saved["L"]), int(saved["H"]), int(saved["meta_seed"]), int(saved["t"])) == (80, 64, seed, p["parent_t"][str(seed)])
        name = f"initial/seed{seed}.npz"
        contents[name] = raw  # Preserve original NPZ container bytes, not a fresh re-save.
        parents[str(seed)] = {"file": name, "raw_sha256": sha(raw), "full_state_sha256": state_sha(saved),
                              "counters": counter_snapshot(saved), "source_archive": archive_meta,
                              "source_member": {"path": member, **member_meta}}
    provenance = {"parent_head": p["parent_head"], "parent_publication_manifest_sha256": sha(publication_bytes),
                  "parent_publication_manifest_Git_blob": git_blob(publication_bytes), "prior_publication_receipt_sha256": sha(receipt_bytes),
                  "prior_receipt_public_fields": {name: receipt[name] for name in ("status", "result_commit", "pull_request", "publication_manifest_sha256")},
                  "data_archive": data_meta, "parents": parents, "new_model_forward_optimizer_calls": 0}
    contents["provenance/parent-provenance.json"] = (canonical(provenance) + "\n").encode("utf-8")
    return contents, parents, provenance


def verify_parent_provenance(contents):
    p = protocol()
    publication_bytes = contents["provenance/parent-publication-manifest.json"]
    assert (sha(publication_bytes), git_blob(publication_bytes)) == (p["parent_publication_manifest_sha256"], p["parent_publication_manifest_Git_blob"])
    publication = json.loads(publication_bytes.decode("utf-8"))
    proof = json.loads(contents["provenance/parent-provenance.json"].decode("utf-8"))
    assert proof["parent_head"] == p["parent_head"] and proof["prior_receipt_public_fields"]["result_commit"] == p["parent_head"]
    data = proof["data_archive"]
    assert all(data[key] == publication["files"]["inputs.zip"][key] for key in ("sha256", "Git_blob", "bytes"))
    assert data["payloads_member_sha256"] == sha(contents["payloads.json"])
    assert data["old_questions_member_sha256"] == sha(contents["parent-questions.json"])
    for seed in p["seeds"]:
        parent = proof["parents"][str(seed)]
        archive, member = parent["source_archive"], parent["source_member"]
        expected_archive = publication["archives"][archive["file"]]
        assert all(archive[key] == expected_archive[key] for key in ("sha256", "Git_blob", "bytes"))
        assert {key: value for key, value in member.items() if key != "path"} == expected_archive["members"][member["path"]]
        raw = contents[parent["file"]]
        assert (sha(raw), git_blob(raw), len(raw)) == (member["sha256"], member["Git_blob"], member["bytes"])
        saved = read_npz(raw)
        assert sha(raw) == parent["raw_sha256"] and state_sha(saved) == parent["full_state_sha256"]
        assert counter_snapshot(saved) == parent["counters"] and int(saved["t"]) == p["parent_t"][str(seed)]
    return proof


def prepare(source, parent_root, output):
    source_bytes = Path(source).read_bytes()
    cls, p = source_model(source_bytes), protocol()
    contents, parents, proof = parent_inputs(parent_root, source_bytes)
    bank = json.loads(contents["payloads.json"].decode("utf-8"))
    old = json.loads(contents["parent-questions.json"].decode("utf-8"))
    rows = questions(bank, old)
    checks = data_checks(bank, rows, old)
    contents.update({"source/p030_binary_continual.py": source_bytes, "plan.json": (HERE / "protocol.json").read_bytes(),
                     "questions.json": (canonical(rows) + "\n").encode("utf-8")})
    course_info = {}
    for seed in p["seeds"]:
        saved = read_npz(contents[parents[str(seed)]["file"]])
        restored = restore(cls, saved)
        assert equal_state(saved, full_state(restored)) and restored.parameters == 10499
        actual, rng_state = schedules(seed, rows)
        name = f"orders/seed{seed}.npy"
        contents[name] = npy_bytes(actual)
        course_info[str(seed)] = {"file": name, "shape": list(actual.shape), "dtype": "<u2", "schedule_seed": seed + 444000,
                                  "final_schedule_RNG": rng_state}
    assert verify_parent_provenance(contents) == proof and file_sha(source) == sha(source_bytes)
    archive = make_zip(contents)
    manifest = {"schema": "ae1-mixed-flip-continuation-v1", "id": p["id"], "status": "frozen_before_baseline_or_new_updates",
                "author": "Codex", "protocol": p, "runtime": runtime(), "data_checks": checks,
                "source_hashes": {name: file_sha(HERE / name) for name in CORE}, "parents": parents, "schedules": course_info,
                "archive": {"file": "inputs.zip", "sha256": sha(archive), "bytes": len(archive)},
                "files": {name: {"sha256": sha(value), "bytes": len(value)} for name, value in sorted(contents.items())},
                "formal_forward_calls": 0, "new_optimizer_calls": 0, "external_model_calls": 0}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with (output / "inputs.zip").open("xb") as stream:
        stream.write(archive)
    write(output / "manifest.json", manifest)
    freeze = {"manifest_sha256": file_sha(output / "manifest.json"), "source_hashes": manifest["source_hashes"],
              "inputs_zip_sha256": manifest["archive"]["sha256"], "inputs_zip_bytes": len(archive), "parents": parents,
              "schedule_sha256": {seed: manifest["files"][row["file"]]["sha256"] for seed, row in course_info.items()},
              "formal_forward_calls": 0, "new_optimizer_calls": 0, "external_model_calls": 0}
    write(output / "source-freeze.json", freeze)
    return freeze


def validate_inputs(path, approved):
    path = Path(path).resolve()
    assert approved and file_sha(path) == approved, "Explicit approved manifest SHA missing or differs"
    manifest, p = read(path), protocol()
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
    proof = verify_parent_provenance(contents)
    assert proof["parents"] == manifest["parents"]
    bank = json.loads(contents["payloads.json"].decode("utf-8"))
    old = json.loads(contents["parent-questions.json"].decode("utf-8"))
    rows = json.loads(contents["questions.json"].decode("utf-8"))
    assert rows == questions(bank, old) and data_checks(bank, rows, old) == manifest["data_checks"]
    cls = source_model(contents["source/p030_binary_continual.py"])
    parents, raw_parents, orders = {}, {}, {}
    for seed in p["seeds"]:
        key = str(seed)
        raw_parents[key] = contents[manifest["parents"][key]["file"]]
        parents[key] = read_npz(raw_parents[key])
        assert equal_state(parents[key], full_state(restore(cls, parents[key])))
        actual = np.load(io.BytesIO(contents[manifest["schedules"][key]["file"]]), allow_pickle=False)
        expected, rng_state = schedules(seed, rows)
        assert actual.dtype.str == "<u2" and np.array_equal(actual, expected)
        assert rng_state == manifest["schedules"][key]["final_schedule_RNG"]
        orders[key] = actual
    return manifest, cls, rows, parents, raw_parents, orders


def probe(net, rows):
    before = net.state()
    calls, macs = net.inference_calls, net.inference_macs
    outputs = []
    for row in rows:
        output = generate(net, row["Q"])
        outputs.append({"question_id": row["question_id"], "class": row["class"], "pair_id": row["pair_id"], **output,
                        "whole_correct": output["tokens"] == row["A"] + "S" and not output["context_exhausted"]})
    assert equal_state(before, net.state())
    scores = {name: {"questions": sum(row["class"] == name for row in rows),
                     "whole_correct": sum(row["whole_correct"] for row in outputs if row["class"] == name)} for name in ("E1", "E2", "F1")}
    return {"scores": scores, "rows": outputs, "inference_calls": net.inference_calls - calls, "inference_dense_MAC": net.inference_macs - macs}


def baseline_one(cls, parent, raw_parent, rows, output, seed, replay=False):
    folder = output / f"seed{seed}"
    if not replay:
        folder.mkdir()
        with (folder / "initial-state.npz").open("xb") as stream:
            stream.write(raw_parent)
    else:
        assert (folder / "initial-state.npz").read_bytes() == raw_parent
    net = restore(cls, parent)
    before = full_state(net)
    if replay:
        assert equal_state(before, read_npz((folder / "baseline-before.npz").read_bytes()))
    else:
        save_state(folder / "baseline-before.npz", net)
    result = probe(net, rows)
    after = full_state(net)
    unchanged = set(before) - {"meta_inference_calls", "meta_inference_macs"}
    assert equal_state({key: before[key] for key in unchanged}, {key: after[key] for key in unchanged})
    integrity = all(result["scores"][name]["questions"] == result["scores"][name]["whole_correct"] == 900 for name in ("E1", "E2"))
    record = {"seed": seed, "parent_counters": counter_snapshot(parent), "before_full_state_sha256": state_sha(before),
              "after_full_state_sha256": state_sha(after), "scores": result["scores"], "old_Echo_integrity_pass": integrity,
              "baseline_streak": 0, "baseline_inference_calls": result["inference_calls"], "baseline_inference_MAC": result["inference_dense_MAC"],
              "new_optimizer_updates": 0, "only_inference_counters_changed": True}
    if replay:
        assert record == read(folder / "baseline.json") and result == read(folder / "baseline-generation.json")
        assert equal_state(after, read_npz((folder / "baseline-after.npz").read_bytes()))
    else:
        save_state(folder / "baseline-after.npz", net)
        write(folder / "baseline.json", record)
        write(folder / "baseline-generation.json", result)
    assert integrity, "Parent Echo baseline integrity failed; whole batch must abort before any new update"
    return after, record


def all_baselines(cls, parents, raw_parents, rows, output, seeds):
    states, records = {}, {}
    for seed in seeds:
        states[str(seed)], records[str(seed)] = baseline_one(cls, parents[str(seed)], raw_parents[str(seed)], rows, output, seed)
    return states, records


def stop_decision(streak, scores, epoch, maximum=40):
    passed = all(scores[name]["questions"] == scores[name]["whole_correct"] == 900 for name in ("E1", "E2", "F1"))
    streak = streak + 1 if passed else 0
    return streak, "two_consecutive_all_class_passes" if streak >= 2 else "epoch_cap" if epoch >= maximum else None, passed


def train_one(cls, parent, baseline_state, baseline_record, course, rows, output, seed, replay=False):
    folder = output / f"seed{seed}"
    net = restore(cls, baseline_state)
    parent_counts = counter_snapshot(parent)
    entry_calls, entry_macs = net.inference_calls, net.inference_macs
    curve, streak, first_full, reason = [], 0, None, None
    started = time.perf_counter()
    try:
        for epoch, order in enumerate(course, 1):
            trace = EpochTrace()
            start_t, start_mac = net.t, net.train_macs
            if replay:
                for qid, position in order:
                    qid, position = int(qid), int(position)
                    row = rows[qid]
                    pred, loss = net.step(row["Q"] + row["A"][:position], (row["A"] + "S")[position])
                    trace.observe(qid, position, pred, loss, (row["A"] + "S")[position])
            else:
                for qid, position in order:
                    row, position = rows[int(qid)], int(position)
                    pred, loss = net.step(row["Q"] + row["A"][:position], (row["A"] + "S")[position])
                    trace.observe(row["question_id"], position, pred, loss, (row["A"] + "S")[position])
            training = trace.result()
            assert training["targets"] == net.t - start_t == 24300
            assert net.train_macs - start_mac == 511660800 and net.t - parent_counts["t"] == epoch * 24300
            assert (net.L, net.H, net.parameters) == (80, 64, 10499) and net.events == json.loads(str(parent["meta_events"]))
            assert all(value.dtype == np.float32 and np.isfinite(value).all() for name in ("p", "m", "v") for value in getattr(net, name))
            evaluation = probe(net, rows)
            streak, reason, passed = stop_decision(streak, evaluation["scores"], epoch)
            if passed and first_full is None:
                first_full = epoch
            record = {"seed": seed, "epoch": epoch, "global_updates": net.t, "new_updates": net.t - parent_counts["t"],
                      "total_training_dense_MAC": net.train_macs, "new_training_dense_MAC": net.train_macs - parent_counts["train_MAC"],
                      "parent_counters": parent_counts, "training": training, "scores": evaluation["scores"],
                      "streak": streak, "stop_reason": reason, "first_full_epoch": first_full,
                      "baseline_inference_calls": baseline_record["baseline_inference_calls"], "baseline_inference_MAC": baseline_record["baseline_inference_MAC"],
                      "epoch_probe_inference_calls": evaluation["inference_calls"], "epoch_probe_inference_MAC": evaluation["inference_dense_MAC"],
                      "new_probe_inference_calls_cumulative": net.inference_calls - entry_calls,
                      "new_probe_inference_MAC_cumulative": net.inference_macs - entry_macs,
                      "total_inference_calls": net.inference_calls, "total_inference_MAC": net.inference_macs,
                      "full_state_sha256": state_sha(full_state(net))}
            if replay:
                assert record == read(folder / f"epoch-{epoch:03}.json") and evaluation == read(folder / f"generation-{epoch:03}.json")
                assert equal_state(full_state(net), read_npz((folder / f"state-{epoch:03}.npz").read_bytes()))
            else:
                save_state(folder / f"state-{epoch:03}.npz", net)
                write(folder / f"epoch-{epoch:03}.json", record)
                write(folder / f"generation-{epoch:03}.json", evaluation)
            curve.append(record)
            print(canonical({"mode": "replay" if replay else "primary", "seed": seed, "epoch": epoch,
                             "scores": evaluation["scores"], "streak": streak, "stop": reason}), flush=True)
            if reason:
                break
        assert reason is not None
        summary = {"seed": seed, "epochs": len(curve), "stop_reason": reason, "streak": streak, "first_full_epoch": first_full,
                   "stable_pass_epoch": len(curve) if streak >= 2 else None, "parent_counters": parent_counts,
                   "new_updates": net.t - parent_counts["t"], "new_training_dense_MAC": net.train_macs - parent_counts["train_MAC"],
                   "baseline_inference_calls": baseline_record["baseline_inference_calls"], "baseline_inference_MAC": baseline_record["baseline_inference_MAC"],
                   "new_probe_inference_calls": net.inference_calls - entry_calls, "new_probe_inference_MAC": net.inference_macs - entry_macs,
                   "total_counters_before_finalTF": counter_snapshot(full_state(net)), "final_scores": curve[-1]["scores"],
                   "final_full_state_sha256": state_sha(full_state(net))}
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


def final_tf(net, rows, free):
    before = net.state()
    calls, macs = net.inference_calls, net.inference_macs
    assert len(rows) == len(free["rows"]) == 2700
    truth = []
    for row, output in zip(rows, free["rows"], strict=True):
        assert row["question_id"] == output["question_id"]
        tf = []
        for position, label in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            logits = net.forward(prefix)[2].astype(np.float64)
            logp = logits - np.logaddexp.reduce(logits)
            tf.append({"position": position, "prefix": prefix, "target": label, "prediction": "01S"[int(logits.argmax())],
                       "logits_01S": logits.tolist(), "probabilities_01S": np.exp(logp).tolist(), "target_CE": -float(logp["01S".index(label)])})
        truth.append({**row, "expected": row["A"] + "S", "generation": output, "TF": tf})
    assert equal_state(before, net.state())
    assert net.inference_calls - calls == 24300 and net.inference_macs - macs == 24300 * 10432
    metrics = {name: {"questions": 900, "TF_correct": sum(point["prediction"] == point["target"] for row in truth if row["class"] == name for point in row["TF"]),
                      "TF_targets": sum(len(row["TF"]) for row in truth if row["class"] == name)} for name in ("E1", "E2", "F1")}
    return {"truth": truth, "metrics": metrics, "inference_calls": net.inference_calls - calls, "inference_dense_MAC": net.inference_macs - macs,
            "learning_state_unchanged": True, "free_generation_reused": True}


def execute(manifest_path, approved, commit, output):
    assert re.fullmatch(r"[0-9a-f]{40}", commit or ""), "Coordinator preregistration commit required"
    manifest, cls, rows, parents, raw_parents, courses = validate_inputs(manifest_path, approved)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "manifest.json", manifest)
    write(output / "execution-start.json", {"author": "Codex", "manifest_sha256": approved, "preregistration_commit": commit,
                                           "all_parent_baselines_before_any_optimizer": True, "auto_retry": False})
    timings, phase = [], "all_parent_baselines"
    started = time.perf_counter()
    try:
        # Whole-batch integrity gate: no new optimizer is entered until all3 pass.
        baseline_states, baselines = all_baselines(cls, parents, raw_parents, rows, output, manifest["protocol"]["seeds"])
        write(output / "baseline-gate.json", {"all_three_passed": True, "new_optimizer_updates_at_gate": 0, "baselines": baselines})
        phase = "primary_training"
        for seed in manifest["protocol"]["seeds"]:
            key = str(seed)
            timings.append(train_one(cls, parents[key], baseline_states[key], baselines[key], courses[key], rows, output, seed))
        phase = "seed101_replay"
        replay_base, replay_record = baseline_one(cls, parents["101"], raw_parents["101"], rows, output, 101, replay=True)
        timings.append(train_one(cls, parents["101"], replay_base, replay_record, courses["101"], rows, output, 101, replay=True))
        validate_inputs(manifest_path, approved)
        phase, students = "final_TF", []
        for seed in manifest["protocol"]["seeds"]:
            folder = output / f"seed{seed}"
            summary = read(folder / "training-summary.json")
            net = restore(cls, read_npz((folder / "final-state.npz").read_bytes()))
            free = read(folder / f"generation-{summary['epochs']:03}.json")
            result = final_tf(net, rows, free)
            write(folder / "final-truth.json", result)
            write(folder / "final-failures.json", [row for row in result["truth"] if not row["generation"]["whole_correct"]])
            students.append({**summary, "replay_status": "complete_exact" if seed == 101 else "not_planned", "final_TF_metrics": result["metrics"],
                             "final_TF_inference_calls": result["inference_calls"], "final_TF_inference_MAC": result["inference_dense_MAC"]})
        validate_inputs(manifest_path, approved)
        summary = {"id": manifest["id"], "status": "complete", "author": "Codex", "manifest_sha256": approved,
                   "preregistration_commit": commit, "students": students, "primary_continued_students": 3, "exact_full_replays": [101],
                   "new_primary_updates": sum(x["new_updates"] for x in students), "new_primary_training_dense_MAC": sum(x["new_training_dense_MAC"] for x in students),
                   "new_replay_updates": students[0]["new_updates"], "new_replay_training_dense_MAC": students[0]["new_training_dense_MAC"],
                   "baseline_inference_calls": sum(x["baseline_inference_calls"] for x in students), "baseline_inference_MAC": sum(x["baseline_inference_MAC"] for x in students),
                   "mixed_probe_inference_calls": sum(x["new_probe_inference_calls"] for x in students), "mixed_probe_inference_MAC": sum(x["new_probe_inference_MAC"] for x in students),
                   "replay_baseline_inference_calls": students[0]["baseline_inference_calls"], "replay_baseline_inference_MAC": students[0]["baseline_inference_MAC"],
                   "replay_probe_inference_calls": students[0]["new_probe_inference_calls"], "replay_probe_inference_MAC": students[0]["new_probe_inference_MAC"],
                   "final_TF_inference_calls": sum(x["final_TF_inference_calls"] for x in students), "final_TF_inference_MAC": sum(x["final_TF_inference_MAC"] for x in students),
                   "all_confirmed_three_class_fit": all(x["streak"] >= 2 for x in students), "array_bytes_per_student": 209980,
                   "external_model_calls": 0, "limits": manifest["protocol"]["limits"]}
        write(output / "compact.json", summary)
        write(output / "timing.json", {"trajectories": timings, "total_seconds": time.perf_counter() - started,
                                      "scope": "Allbaseline,training,probes,seed101replay,stateIO,guards,finalTF;notpurekernels"})
        write(output / "storage.json", {"output_bytes_before_this_record": sum(path.stat().st_size for path in output.rglob("*") if path.is_file()), "input_archive_bytes": manifest["archive"]["bytes"]})
        return summary
    except Exception as error:
        write(output / "failure.json", {"status": "incomplete", "stage": phase, "error_type": type(error).__name__, "message": str(error),
                                        "zero_new_updates_guaranteed": phase == "all_parent_baselines", "completed_trajectories": timings, "auto_retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--engineering", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--parent-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--approved-manifest-sha")
    parser.add_argument("--prereg-commit")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.prepare:
        if args.source is None or args.parent_root is None:
            parser.error("--prepare requires --source originalP030 and --parent-root verifiedPR26 evidence root")
        result = prepare(args.source, args.parent_root, args.out)
    elif args.engineering:
        if args.source is None or args.parent_root is None:
            parser.error("--engineering requires --source and --parent-root for pure parent-byte checks plus bounded syntheticchecks")
        import unittest
        import test_mixed
        test_mixed.SOURCE = args.source
        test_mixed.PARENT_ROOT = args.parent_root
        tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_mixed))
        assert tests.wasSuccessful()
        args.out.mkdir(parents=True, exist_ok=False)
        result = {"status": "PASS", "tests": tests.testsRun, "source_hashes": {name: file_sha(HERE / name) for name in CORE},
                  "synthetic_native_updates": test_mixed.NATIVE_UPDATES, "synthetic_native_forward_calls": test_mixed.NATIVE_FORWARD,
                  "synthetic_mock_targets": test_mixed.MOCK_TARGETS, "synthetic_mock_probes": test_mixed.MOCK_PROBES,
                  "formal_forward_calls": 0, "new_parent_optimizer_calls": 0, "external_model_calls": 0}
        write(args.out / "checks.json", result)
    else:
        if args.manifest is None or not args.approved_manifest_sha or not args.prereg_commit:
            parser.error("--execute requires --manifest/--approved-manifest-sha/--prereg-commit after coordinatorgate")
        result = execute(args.manifest, args.approved_manifest_sha, args.prereg_commit, args.out)
    print(canonical(result), flush=True)


if __name__ == "__main__":
    main()
