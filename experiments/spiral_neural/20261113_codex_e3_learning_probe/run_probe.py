"""One-epoch paired E3 learning probe; prepare is trained-NN-free."""
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
import types
import zipfile
import zlib

if sys.flags.optimize:
    raise RuntimeError("Exact assertion guards require non-optimized Python")
sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
CORE = ("run_probe.py", "protocol.json", "test_probe.py")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def runtime():
    return {"python": platform.python_version(), "numpy": np.__version__, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}


def protocol():
    p = read(HERE / "protocol.json")
    assert p["id"] == "E3-LR-PROBE-20261113" and p["seeds"] == [101, 202, 303]
    assert p["classes"] == ["E1", "E2", "F1", "F2", "E3"] and p["arm_order"] == ["eta001", "eta003"]
    assert p["arms"] == {"eta001": .001, "eta003": .003} and p["replay_seeds"] == []
    assert p["updates_per_arm"] * 21056 == p["training_dense_MAC_per_arm"] == 1118073600
    assert p["new_updates_all_primary"] == 318600 and p["training_dense_MAC_all_primary"] == 6708441600
    return p


def load_helpers(raw):
    assert sha(raw) == protocol()["F2_runner_sha256"]
    names = {"canonical", "full_state", "state_sha", "equal_state", "npz_bytes", "read_npz", "save_state", "restore",
             "npy_bytes", "make_zip", "EpochTrace", "generate", "counter_snapshot"}
    nodes = [copy.deepcopy(node) for node in ast.parse(raw.decode("utf-8")).body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    assert {node.name for node in nodes} == names
    namespace = {"np": np, "json": json, "hashlib": hashlib, "io": io, "zipfile": zipfile, "Path": Path}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<pinned-F2-state-trace-generation-helpers>", "exec"), namespace)
    return types.SimpleNamespace(**{name: namespace[name] for name in names})


def model_classes(raw):
    p = protocol()
    assert sha(raw) == p["source_sha256"]
    original = next(node for node in ast.parse(raw.decode("utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "Model")
    original_dump = ast.dump(original, include_attributes=False)
    assert sha(original_dump.encode("utf-8")) == p["Model_AST_sha256"]
    changed = copy.deepcopy(original)
    step = next(node for node in changed.body if isinstance(node, ast.FunctionDef) and node.name == "step")
    leaves = [node for node in ast.walk(step) if isinstance(node, ast.Constant) and type(node.value) is float and node.value == .003]
    assert len(leaves) == 1
    leaves[0].value = .001
    changed_dump = ast.dump(changed, include_attributes=False)
    leaves[0].value = .003
    assert ast.dump(changed, include_attributes=False) == original_dump
    leaves[0].value = .001
    classes = {}
    for name, node in (("eta001", changed), ("eta003", original)):
        namespace = {"np": np, "json": json, "__name__": "pinned_P030_single_eta_AST"}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<P030-single-eta-arm>", "exec"), namespace)
        classes[name] = namespace["Model"]
    proof = {"eta003_Model_AST_sha256": sha(original_dump.encode("utf-8")), "eta001_Model_AST_sha256": sha(changed_dump.encode("utf-8")),
             "unique_changed_leaf": {"function": "Model.step", "before": .003, "after": .001}, "entire_AST_equal_after_reversing_one_leaf": True}
    return classes, proof, original_dump, changed_dump


def collect_public(parent_root):
    """Exact public-byte extraction only; no old main, forward or step."""
    p, root = protocol(), Path(parent_root)
    public = root / "publication/final/public"
    publication_raw = (public / "publication-manifest.json").read_bytes()
    assert (sha(publication_raw), git_blob(publication_raw)) == (p["parent_publication_manifest_sha256"], p["parent_publication_manifest_Git_blob"])
    publication = json.loads(publication_raw)
    receipt_raw = (root / "publication-receipt.json").read_bytes()
    receipt = json.loads(receipt_raw)
    assert receipt["status"] == "complete" and receipt["result_commit"] == p["parent_head"]
    receipts = {row["name"]: row for row in receipt["byte_checks"]}
    used, selected, archives = {}, {}, {}
    def public_file(name):
        expected = {"sha256": sha(publication_raw), "Git_blob": git_blob(publication_raw), "bytes": len(publication_raw)} if name == "publication-manifest.json" else publication["files"][name]
        check = receipts[name]
        assert check["byte_match"] and check["ref_match"] and check["commit"] == p["parent_head"]
        assert all(check[key] == expected[key] for key in ("sha256", "Git_blob", "bytes"))
        cached = root / "remote-byte-checks" / ("final-" + name)
        raw = cached.read_bytes() if cached.is_file() else (public / name).read_bytes()
        assert (sha(raw), git_blob(raw), len(raw)) == (expected["sha256"], expected["Git_blob"], expected["bytes"])
        used[name] = check
        return raw
    assert public_file("publication-manifest.json") == publication_raw
    old_manifest_raw = public_file("manifest.json")
    old_manifest = json.loads(old_manifest_raw)
    inputs_raw = public_file("inputs.zip")
    assert old_manifest["archive"]["sha256"] == sha(inputs_raw)
    contents = {"provenance/parent-publication-manifest.json": publication_raw, "provenance/parent-manifest.json": old_manifest_raw}
    with zipfile.ZipFile(io.BytesIO(inputs_raw)) as archive:
        for old, new in (("source/p030_binary_continual.py", "source/p030_binary_continual.py"), ("vendor/run_f2.py", "vendor/run_f2.py"),
                         ("vendor/protocol.json", "vendor/F2-protocol.json"), ("payloads.json", "payloads.json"), ("questions.json", "parent-questions.json")):
            raw = archive.read(old)
            assert old_manifest["files"][old] == {"sha256": sha(raw), "bytes": len(raw)}
            contents[new] = raw
            selected[new] = {"archive": "inputs.zip", "member": old, "sha256": sha(raw), "bytes": len(raw), "CRC32": format(archive.getinfo(old).CRC, "08x")}
    for seed in p["seeds"]:
        for member, destination in ((f"science/seed{seed}/final-after-TF.npz", f"initial/seed{seed}.npz"),
                                    (f"science/seed{seed}/new-generation.json", f"historical/seed{seed}/generation.json")):
            matches = [name for name, row in publication["archives"].items() if member in row["members"]]
            assert len(matches) == 1
            name = matches[0]
            if name not in archives:
                archives[name] = public_file(name)
            expected = publication["archives"][name]["members"][member]
            with zipfile.ZipFile(io.BytesIO(archives[name])) as archive:
                raw, crc = archive.read(member), format(archive.getinfo(member).CRC, "08x")
            assert (sha(raw), git_blob(raw), len(raw), crc) == (expected["sha256"], expected["Git_blob"], expected["bytes"], expected["CRC32"])
            contents[destination] = raw
            selected[destination] = {"archive": name, "member": member, **expected}
    proof = {"parent_head": p["parent_head"], "original_receipt_sha256": sha(receipt_raw), "public_byte_checks": used,
             "selected_members": selected, "formal_forward_calls": 0, "new_optimizer_calls": 0}
    contents["provenance/parent-proof.json"] = (canonical(proof) + "\n").encode("utf-8")
    return contents, proof


def inspect_contents(contents, require_orders=True):
    p = protocol()
    publication_raw = contents["provenance/parent-publication-manifest.json"]
    assert (sha(publication_raw), git_blob(publication_raw)) == (p["parent_publication_manifest_sha256"], p["parent_publication_manifest_Git_blob"])
    publication, proof = json.loads(publication_raw), json.loads(contents["provenance/parent-proof.json"])
    assert proof["parent_head"] == p["parent_head"]
    for name, check in proof["public_byte_checks"].items():
        expected = {"sha256": sha(publication_raw), "Git_blob": git_blob(publication_raw), "bytes": len(publication_raw)} if name == "publication-manifest.json" else publication["files"][name]
        assert all(check[key] == expected[key] for key in ("sha256", "Git_blob", "bytes"))
        assert check["byte_match"] and check["ref_match"] and check["commit"] == p["parent_head"]
    old_manifest_raw = contents["provenance/parent-manifest.json"]
    assert sha(old_manifest_raw) == publication["files"]["manifest.json"]["sha256"]
    old_manifest = json.loads(old_manifest_raw)
    for name, origin in proof["selected_members"].items():
        raw = contents[name]
        assert sha(raw) == origin["sha256"] and len(raw) == origin["bytes"] and format(zlib.crc32(raw), "08x") == origin["CRC32"]
        if origin["archive"] == "inputs.zip":
            assert old_manifest["files"][origin["member"]] == {"sha256": sha(raw), "bytes": len(raw)}
        else:
            expected = publication["archives"][origin["archive"]]["members"][origin["member"]]
            assert all(origin[key] == expected[key] for key in expected) and git_blob(raw) == expected["Git_blob"]
    assert sha(contents["vendor/F2-protocol.json"]) == p["F2_protocol_sha256"]
    helpers = load_helpers(contents["vendor/run_f2.py"])
    classes, ast_proof, original_ast, low_ast = model_classes(contents["source/p030_binary_continual.py"])
    bank, old = json.loads(contents["payloads.json"]), json.loads(contents["parent-questions.json"])
    extra = np.random.default_rng(331000).integers(0, 30, size=(900, 2))
    assert bank == [[pair // 30, pair % 30, int(extra[pair, 0]), int(extra[pair, 1])] for pair in range(900)]
    rows = make_rows(bank, old)
    if "questions.json" in contents:
        assert json.loads(contents["questions.json"]) == rows
    checks = data_checks(rows, p["classes"])
    assert checks["teacher_targets"] == checks["unique_teacher_prefixes"] == 53100
    parents, parent_info, orders = {}, {}, {}
    for seed in p["seeds"]:
        key = str(seed)
        raw = contents[f"initial/seed{seed}.npz"]
        saved = helpers.read_npz(raw)
        assert (int(saved["L"]), int(saved["H"]), int(saved["meta_seed"]), int(saved["t"])) == (80, 64, seed, p["parent_t"][key])
        for cls in classes.values():
            assert helpers.equal_state(saved, helpers.full_state(helpers.restore(cls, saved)))
        archived = json.loads(contents[f"historical/seed{seed}/generation.json"])
        assert all(archived["scores"][name]["questions"] == archived["scores"][name]["whole_correct"] == 900 for name in p["old_classes"])
        assert all(item["tokens"] == old[item["question_id"]]["A"] + "S" for item in archived["rows"])
        parents[key] = saved
        parent_info[key] = {"file": f"initial/seed{seed}.npz", "raw_sha256": sha(raw), "full_state_sha256": helpers.state_sha(saved),
                            "counters": helpers.counter_snapshot(saved)}
        expected, schedule_rng = shuffled_order(target_pool(rows, p["classes"]), seed + 666000)
        if require_orders:
            actual = np.load(io.BytesIO(contents[f"orders/seed{seed}.npy"]), allow_pickle=False)
            assert actual.dtype.str == "<u2" and np.array_equal(actual, expected)
        else:
            actual = expected
        orders[key] = actual
    return helpers, classes, rows, parents, orders, parent_info, ast_proof, original_ast, low_ast, checks


def prepare(parent_root, output):
    contents, _ = collect_public(parent_root)
    h, _, rows, _, orders, parent_info, ast_proof, original_ast, low_ast, checks = inspect_contents(contents, require_orders=False)
    for seed in protocol()["seeds"]:
        contents[f"orders/seed{seed}.npy"] = h.npy_bytes(orders[str(seed)])
    contents.update({"questions.json": (canonical(rows) + "\n").encode("utf-8"), "plan.json": (HERE / "protocol.json").read_bytes(),
                     "source/Model-eta003.ast": (original_ast + "\n").encode("utf-8"), "source/Model-eta001.ast": (low_ast + "\n").encode("utf-8"),
                     "source/AST-change.json": (canonical(ast_proof) + "\n").encode("utf-8")})
    inspect_contents(contents)
    raw = h.make_zip(contents)
    manifest = {"schema": "e3-learning-probe-v1", "id": protocol()["id"], "protocol": protocol(), "runtime": runtime(),
                "status": "frozen_before_any_new_trained_model_score_or_update", "parents": parent_info, "AST_change": ast_proof, "data_checks": checks,
                "source_hashes": {name: sha((HERE / name).read_bytes()) for name in CORE},
                "schedules": {str(seed): {"file": f"orders/seed{seed}.npy", "shape": [53100, 2], "dtype": "<u2", "rng_seed": seed + 666000,
                                        "both_arms_share_exact_order": True} for seed in protocol()["seeds"]},
                "archive": {"file": "inputs.zip", "sha256": sha(raw), "bytes": len(raw)},
                "files": {name: {"sha256": sha(value), "bytes": len(value)} for name, value in sorted(contents.items())},
                "formal_forward_calls": 0, "new_optimizer_calls": 0, "external_model_calls": 0}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "inputs.zip").open("xb") as stream:
        stream.write(raw)
    write(output / "manifest.json", manifest)
    freeze = {"manifest_sha256": sha((output / "manifest.json").read_bytes()), "source_hashes": manifest["source_hashes"],
              "inputs_zip_sha256": sha(raw), "inputs_zip_bytes": len(raw), "members": len(contents), "AST_change": ast_proof,
              "formal_forward_calls": 0, "new_optimizer_calls": 0}
    write(output / "source-freeze.json", freeze)
    return freeze


def validate_inputs(path, approved):
    path = Path(path)
    assert re.fullmatch("[0-9a-f]{64}", approved or "") and sha(path.read_bytes()) == approved
    m = read(path)
    assert m["protocol"] == protocol() and m["runtime"] == runtime()
    assert m["source_hashes"] == {name: sha((HERE / name).read_bytes()) for name in CORE}
    raw = (path.parent / m["archive"]["file"]).read_bytes()
    assert sha(raw) == m["archive"]["sha256"] and len(raw) == m["archive"]["bytes"]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) and set(archive.namelist()) == set(m["files"])
        contents = {name: archive.read(name) for name in archive.namelist()}
    assert all(m["files"][name] == {"sha256": sha(value), "bytes": len(value)} for name, value in contents.items())
    assert contents["plan.json"] == (HERE / "protocol.json").read_bytes()
    data = inspect_contents(contents)
    assert m["parents"] == data[5] and m["AST_change"] == data[6] and m["data_checks"] == data[9]
    assert contents["source/Model-eta003.ast"] == (data[7] + "\n").encode("utf-8")
    assert contents["source/Model-eta001.ast"] == (data[8] + "\n").encode("utf-8")
    assert json.loads(contents["source/AST-change.json"]) == data[6]
    return m, contents, data


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def word(value):
    assert type(value) is int and 0 <= value < 30
    return format(value, "05b") + "0"


def encode(op, take, payload):
    assert (op, take) in (("010", 1), ("010", 2), ("010", 3), ("100", 1), ("100", 2))
    assert len(payload) == 4
    return "01" + op + format(take, "03b") + "0" + "".join(word(value) for value in payload) + "111100"


def expected_answer(op, take, payload):
    if op == "010":
        return "".join(word(value) for value in payload[:take])
    assert op == "100" and take in (1, 2)
    return "".join("".join("1" if bit == "0" else "0" for bit in word(value)[:5]) + "0" for value in payload[:take])


def make_rows(bank, old_rows):
    """Keep all old dictionaries identical; append Echo/r3 using the same four input words."""
    assert len(bank) == 900 and len(old_rows) == 3600
    old_specs = (("E1", "010", 1), ("E2", "010", 2), ("F1", "100", 1), ("F2", "100", 2))
    rows = []
    for index, row in enumerate(old_rows):
        name, op, take = old_specs[index // 900]
        pair = index % 900
        expected = {"question_id": index, "pair_id": pair, "r": take, "payload": bank[pair],
                    "Q": encode(op, take, bank[pair]), "A": expected_answer(op, take, bank[pair]), "class": name, "op": op}
        assert row == expected
        rows.append(copy.deepcopy(row))
    for pair, payload in enumerate(bank):
        rows.append({"question_id": len(old_rows) + pair, "pair_id": pair, "r": 3, "payload": payload,
                     "Q": encode("010", 3, payload), "A": expected_answer("010", 3, payload), "class": "E3", "op": "010"})
    assert rows[:len(old_rows)] == old_rows
    assert len({row["Q"] for row in rows}) == 4500
    return rows


def target_pool(rows, class_order):
    """Actual teacher (QID,position) pairs, canonical pair->class->answer position."""
    by_key = {(row["pair_id"], row["class"]): row for row in rows}
    assert len(by_key) == len(rows) and set(class_order) == {row["class"] for row in rows}
    pairs = sorted({row["pair_id"] for row in rows})
    actual = [(by_key[pair, name]["question_id"], position) for pair in pairs for name in class_order
              for position in range(len(by_key[pair, name]["A"]) + 1)]
    pool = np.asarray(actual, dtype="<u2")
    assert len(set(map(tuple, pool.tolist()))) == len(pool)
    return pool


def shuffled_order(pool, rng_seed):
    """Seed is supplied by the future approved protocol, not selected by scores."""
    rng = np.random.default_rng(rng_seed)
    return pool[rng.permutation(len(pool))], copy.deepcopy(rng.bit_generator.state)


def data_checks(rows, class_order):
    labels = {}
    for index, row in enumerate(rows):
        assert row["question_id"] == index and len(row["Q"]) == 39 and len(row["A"]) == 6 * row["r"]
        for position, label in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            assert prefix not in labels or labels[prefix] == label
            labels[prefix] = label
    pool = target_pool(rows, class_order)
    return {"questions": len(rows), "teacher_targets": len(pool), "unique_teacher_prefixes": len(labels),
            "by_class": {name: {"questions": sum(row["class"] == name for row in rows),
                                "targets": sum(len(row["A"]) + 1 for row in rows if row["class"] == name),
                                "STOP_prefix_length": max(len(row["Q"] + row["A"]) for row in rows if row["class"] == name)} for name in class_order}}


def token_metrics(rows, outputs, class_order):
    """Generic saved-string readout: every answer word, including E3's third word, has its own denominator."""
    by_id = {output["question_id"]: output for output in outputs}
    assert len(by_id) == len(outputs) == len(rows) and set(by_id) == {row["question_id"] for row in rows}
    per_question = []
    for row in rows:
        output = by_id[row["question_id"]]
        actual, expected = output["tokens"], row["A"] + "S"
        bit = [actual[i:i + 1] == target for i, target in enumerate(row["A"])]
        words = [{"information5_correct": actual[start:start + 5] == row["A"][start:start + 5],
                  "tail0_correct": actual[start + 5:start + 6] == "0",
                  "complete6_correct": actual[start:start + 6] == row["A"][start:start + 6]} for start in range(0, len(row["A"]), 6)]
        first = next((i for i in range(max(len(actual), len(expected))) if actual[i:i + 1] != expected[i:i + 1]), None)
        if first is None:
            error_kind = "none"
        elif actual[first:first + 1] == "":
            error_kind = "missing_token"
        elif expected[first:first + 1] == "":
            error_kind = "extra_token"
        elif actual[first:first + 1] == "S":
            error_kind = "early_STOP"
        elif expected[first:first + 1] == "S":
            error_kind = "STOP_expected_bit_emitted"
        else:
            error_kind = "content_bit"
        stop_at = actual.find("S")
        if output.get("context_exhausted", False):
            termination = "context_exhausted"
        elif output.get("cap_exhausted", False):
            termination = "cap_exhausted"
        elif stop_at < 0:
            termination = "no_STOP"
        elif stop_at < len(actual) - 1:
            termination = "tokens_after_STOP"
        elif stop_at < len(row["A"]):
            termination = "early_STOP"
        elif stop_at == len(row["A"]):
            termination = "STOP_at_expected_position"
        else:
            termination = "late_STOP"
        per_question.append({"question_id": row["question_id"], "class": row["class"], "whole_correct": actual == expected,
                             "answer_bit_correct": bit, "words": words, "STOP_position_correct": actual.endswith("S") and len(actual) == len(expected),
                             "first_error_position_zero_based": first, "first_error_kind": error_kind, "termination_kind": termination,
                             "missing_expected_positions": max(0, len(expected) - len(actual)), "extra_output_positions": max(0, len(actual) - len(expected)),
                             "context_exhausted": bool(output.get("context_exhausted", False)), "cap_exhausted": bool(output.get("cap_exhausted", False))})
    by_class = {}
    for name in class_order:
        part = [row for row in per_question if row["class"] == name]
        length = max((len(row["answer_bit_correct"]) for row in part), default=0)
        slots = max((len(row["words"]) for row in part), default=0)
        word_scores = {}
        for slot in range(slots):
            available = [row["words"][slot] for row in part if len(row["words"]) > slot]
            word_scores[f"word{slot + 1}"] = {"questions": len(available),
                **{key: sum(row[key] for row in available) for key in ("information5_correct", "tail0_correct", "complete6_correct")}}
        by_class[name] = {"questions": len(part), "whole_correct": sum(row["whole_correct"] for row in part), "words": word_scores,
            "answer_position_bit_correct": [sum(row["answer_bit_correct"][i] for row in part) for i in range(length)],
            "answer_position_bit_totals": [len(part)] * length, "STOP_position_correct": sum(row["STOP_position_correct"] for row in part),
            "first_error_position_histogram": dict(sorted(Counter("none" if row["first_error_position_zero_based"] is None else str(row["first_error_position_zero_based"]) for row in part).items())),
            "first_error_kind_histogram": dict(sorted(Counter(row["first_error_kind"] for row in part).items())),
            "termination_kind_histogram": dict(sorted(Counter(row["termination_kind"] for row in part).items())),
            "missing_expected_positions": sum(row["missing_expected_positions"] for row in part), "extra_output_positions": sum(row["extra_output_positions"] for row in part),
            "context_exhausted_questions": sum(row["context_exhausted"] for row in part), "cap_exhausted_questions": sum(row["cap_exhausted"] for row in part)}
    return {"by_class": by_class, "per_question": per_question, "extra_forward_calls": 0}


def churn_metrics(rows, previous, current, class_order):
    ids = {row["question_id"] for row in rows}
    maps = [{output["question_id"]: output["tokens"] for output in outputs} for outputs in (previous, current)]
    assert all(len(mapping) == len(rows) and set(mapping) == ids for mapping in maps)
    result = {}
    for name in class_order:
        changes = {key: [] for key in ("previous_correct_to_wrong", "previous_wrong_to_correct", "retained_correct", "retained_wrong")}
        for row in rows:
            if row["class"] != name:
                continue
            qid, expected = row["question_id"], row["A"] + "S"
            before, after = maps[0][qid] == expected, maps[1][qid] == expected
            key = "retained_correct" if before and after else "previous_correct_to_wrong" if before else "previous_wrong_to_correct" if after else "retained_wrong"
            changes[key].append(qid)
        result[name] = {"questions": sum(row["class"] == name for row in rows),
                        **{key: len(value) for key, value in changes.items()}, "QIDs": changes}
    return {"by_class": result, "extra_forward_calls": 0}


def probe(h, net, rows, class_order):
    before, calls, macs = net.state(), net.inference_calls, net.inference_macs
    outputs = []
    for row in rows:
        output = h.generate(net, row["Q"])
        outputs.append({"question_id": row["question_id"], "class": row["class"], "pair_id": row["pair_id"], **output,
                        "whole_correct": output["tokens"] == row["A"] + "S" and not output["context_exhausted"]})
    assert h.equal_state(before, net.state())
    scores = {name: {"questions": sum(row["class"] == name for row in rows),
                     "whole_correct": sum(row["whole_correct"] for row in outputs if row["class"] == name)} for name in class_order}
    return {"scores": scores, "rows": outputs, "inference_calls": net.inference_calls - calls, "inference_dense_MAC": net.inference_macs - macs}


def teacher_forced(h, net, rows, free, class_order):
    before, calls, macs = net.state(), net.inference_calls, net.inference_macs
    by_id = {row["question_id"]: row for row in free["rows"]}
    assert len(by_id) == len(rows) and set(by_id) == {row["question_id"] for row in rows}
    truth = []
    for row in rows:
        tf = []
        for position, label in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            logits = net.forward(prefix)[2].astype(np.float64)
            lp = logits - np.logaddexp.reduce(logits)
            tf.append({"position": position, "prefix": prefix, "target": label, "prediction": "01S"[int(logits.argmax())],
                       "logits_01S": logits.tolist(), "probabilities_01S": np.exp(lp).tolist(), "target_CE": -float(lp["01S".index(label)])})
        truth.append({**row, "expected": row["A"] + "S", "generation": by_id[row["question_id"]], "TF": tf})
    count = sum(len(row["A"]) + 1 for row in rows)
    assert h.equal_state(before, net.state()) and net.inference_calls - calls == count
    assert net.inference_macs - macs == count * 10432
    metrics = {}
    for name in class_order:
        part = [row for row in truth if row["class"] == name]
        length = max((len(row["A"]) for row in part), default=0)
        words = {}
        for start in range(0, length, 6):
            available = [row for row in part if len(row["A"]) > start]
            words[f"word{start // 6 + 1}"] = {"questions": len(available),
                "information5_correct": sum(all(point["prediction"] == point["target"] for point in row["TF"][start:start + 5]) for row in available),
                "information_bits_correct": sum(point["prediction"] == point["target"] for row in available for point in row["TF"][start:start + 5]),
                "information_bits_total": 5 * len(available),
                "tail0_correct": sum(row["TF"][start + 5]["prediction"] == "0" for row in available),
                "complete6_correct": sum(all(point["prediction"] == point["target"] for point in row["TF"][start:start + 6]) for row in available)}
        metrics[name] = {"questions": len(part), "TF_correct": sum(point["prediction"] == point["target"] for row in part for point in row["TF"]),
            "TF_targets": sum(len(row["TF"]) for row in part), "TF_STOP_correct": sum(row["TF"][-1]["prediction"] == "S" for row in part),
            "CE_loss_sum": sum(point["target_CE"] for row in part for point in row["TF"]), "words": words,
            "answer_position_TF_correct": [sum(row["TF"][i]["prediction"] == row["TF"][i]["target"] for row in part) for i in range(length)],
            "answer_position_TF_total": [len(part)] * length}
    return {"truth": truth, "metrics": metrics, "inference_calls": count, "inference_dense_MAC": count * 10432,
            "learning_state_unchanged": True, "free_generation_reused": True}


def learning_unchanged(h, before, after):
    keys = set(before) - {"meta_inference_calls", "meta_inference_macs"}
    return h.equal_state({key: before[key] for key in keys}, {key: after[key] for key in keys})


def all_old_baselines(h, cls, parents, contents, rows, output, seeds):
    states, records = {}, {}
    old_rows, names = [row for row in rows if row["class"] != "E3"], protocol()["old_classes"]
    for seed in seeds:
        key, folder = str(seed), output / f"seed{seed}"
        folder.mkdir()
        with (folder / "initial-state.npz").open("xb") as stream:
            stream.write(contents[f"initial/seed{seed}.npz"])
        net = h.restore(cls, parents[key])
        before = h.full_state(net)
        h.save_state(folder / "baseline-old-before.npz", net)
        result = probe(h, net, old_rows, names)
        after = h.full_state(net)
        assert learning_unchanged(h, before, after)
        archived = json.loads(contents[f"historical/seed{seed}/generation.json"])
        integrity = all(result["scores"][name]["questions"] == result["scores"][name]["whole_correct"] == 900 for name in names)
        record = {"seed": seed, "scores": result["scores"], "integrity_pass": integrity, "archived_generation_exact": result == archived,
                  "parent_counters": h.counter_snapshot(before), "old_baseline_inference_calls": result["inference_calls"],
                  "old_baseline_inference_MAC": result["inference_dense_MAC"], "learning_state_unchanged": True, "new_optimizer_updates": 0}
        h.save_state(folder / "baseline-old-after.npz", net)
        write(folder / "baseline-old-generation.json", result)
        write(folder / "baseline-old.json", record)
        assert integrity and result == archived, "Whole batch old integrity failed before E3 probes or optimizer"
        states[key], records[key] = after, record
    return states, records


def all_cold_baselines(h, cls, parents, old_states, old_records, rows, output, seeds):
    states, records = {}, {}
    new_rows = [row for row in rows if row["class"] == "E3"]
    for seed in seeds:
        key, folder = str(seed), output / f"seed{seed}"
        net = h.restore(cls, old_states[key])
        cold = probe(h, net, new_rows, ["E3"])
        write(folder / "baseline-E3-generation.json", cold)
        h.save_state(folder / "baseline-E3-after-free.npz", net)
        truth = teacher_forced(h, net, new_rows, cold, ["E3"])
        assert truth["inference_calls"] == 17100
        write(folder / "baseline-E3-truth.json", truth)
        after = h.full_state(net)
        assert learning_unchanged(h, parents[key], after)
        old = read(folder / "baseline-old-generation.json")
        joined = {"scores": old["scores"] | cold["scores"], "rows": old["rows"] + cold["rows"],
                  "inference_calls": old["inference_calls"] + cold["inference_calls"],
                  "inference_dense_MAC": old["inference_dense_MAC"] + cold["inference_dense_MAC"]}
        write(folder / "baseline-generation.json", joined)
        write(folder / "baseline-token-metrics.json", token_metrics(rows, joined["rows"], protocol()["classes"]))
        cold_whole = cold["scores"]["E3"]["whole_correct"]
        record = {**old_records[key], "cold_E3_scores": cold["scores"], "baseline_ceiling": cold_whole == 900,
                  "learning_gain_identifiability": "ceiling" if cold_whole == 900 else "not_at_ceiling",
                  "cold_free_inference_calls": cold["inference_calls"], "cold_free_inference_MAC": cold["inference_dense_MAC"],
                  "cold_TF_inference_calls": truth["inference_calls"], "cold_TF_inference_MAC": truth["inference_dense_MAC"],
                  "physical_shared_baseline_inference_calls": old["inference_calls"] + cold["inference_calls"] + truth["inference_calls"],
                  "physical_shared_baseline_inference_MAC": old["inference_dense_MAC"] + cold["inference_dense_MAC"] + truth["inference_dense_MAC"],
                  "shared_end_counters": h.counter_snapshot(after), "shared_full_state_sha256": h.state_sha(after),
                  "both_arms_start_from_this_exact_full_state": True, "physical_baseline_copies": 1}
        h.save_state(folder / "baseline-after-TF.npz", net)
        write(folder / "baseline.json", record)
        states[key], records[key] = after, record
    return states, records


def arm_feasibility(rows, cold, endpoint, class_order, old_classes):
    churn = churn_metrics(rows, cold, endpoint, class_order)
    cold_map, end_map = ({item["question_id"]: item["tokens"] for item in part} for part in (cold, endpoint))
    old_lost = {name: churn["by_class"][name]["QIDs"]["previous_correct_to_wrong"] for name in old_classes}
    assert all(cold_map[row["question_id"]] == row["A"] + "S" for row in rows if row["class"] in old_classes)
    new_rows = [row for row in rows if row["class"] == "E3"]
    cold_count = sum(cold_map[row["question_id"]] == row["A"] + "S" for row in new_rows)
    count = sum(end_map[row["question_id"]] == row["A"] + "S" for row in new_rows)
    lost = sum(map(len, old_lost.values()))
    ceiling = cold_count == len(new_rows)
    return {"old_lost_total": lost, "old_lost_QIDs_by_class": old_lost, "cold_E3_whole": cold_count, "E3_whole": count,
            "E3_whole_gain": count - cold_count, "strict_feasibility": lost == 0 and count > cold_count,
            "baseline_ceiling": ceiling, "learning_gain_identifiability": "ceiling" if ceiling else "not_at_ceiling",
            "churn": churn, "extra_forward_calls": 0}


def paired_arms(rows, cold, low, high, class_order, old_classes):
    a, b = (arm_feasibility(rows, cold, outputs, class_order, old_classes) for outputs in (low, high))
    maps = [{item["question_id"]: item["tokens"] for item in outputs} for outputs in (low, high)]
    by_class = {}
    for name in class_order:
        categories = {key: [] for key in ("both_correct", "eta001_only_correct", "eta003_only_correct", "both_wrong")}
        for row in rows:
            if row["class"] != name:
                continue
            qid, expected = row["question_id"], row["A"] + "S"
            lc, hc = maps[0][qid] == expected, maps[1][qid] == expected
            key = "both_correct" if lc and hc else "eta001_only_correct" if lc else "eta003_only_correct" if hc else "both_wrong"
            categories[key].append(qid)
        by_class[name] = {"questions": sum(row["class"] == name for row in rows), "QIDs": categories,
                          "counts": {key: len(value) for key, value in categories.items()}}
    return {"eta001": a, "eta003": b, "axes_eta001_minus_eta003": {"old_lost": a["old_lost_total"] - b["old_lost_total"],
            "E3_whole_gain": a["E3_whole_gain"] - b["E3_whole_gain"]}, "by_class": by_class, "extra_forward_calls": 0}


def feasibility_interpretation(items):
    passed = all(item["strict_feasibility"] for item in items)
    interpretation = "not_identifiable_ceiling" if any(item["baseline_ceiling"] for item in items) else "pass" if passed else "not_met"
    return {"strict_feasibility_all_three": passed, "overall_interpretation": interpretation}


def train_arm(h, cls, parent, shared, order, rows, folder, seed, arm):
    folder.mkdir()
    net = h.restore(cls, shared)
    h.save_state(folder / "entry-state.npz", net)
    trace, started = h.EpochTrace(), time.perf_counter()
    try:
        for qid, position in order:
            row, position = rows[int(qid)], int(position)
            target = (row["A"] + "S")[position]
            pred, loss = net.step(row["Q"] + row["A"][:position], target)
            trace.observe(row["question_id"], position, pred, loss, target)
        assert trace.targets == net.t - int(shared["t"]) == 53100
        assert net.train_macs - int(shared["meta_train_macs"]) == 1118073600
        assert net.t == protocol()["end_t"][str(seed)] and (net.L, net.H, net.parameters) == (80, 64, 10499)
        assert net.events == json.loads(str(parent["meta_events"]))
        assert all(value.dtype == np.float32 and np.isfinite(value).all() for group in (net.p, net.m, net.v) for value in group)
        evaluation = probe(h, net, rows, protocol()["classes"])
        h.save_state(folder / "final-state.npz", net)
        write(folder / "generation.json", evaluation)
        write(folder / "token-metrics.json", token_metrics(rows, evaluation["rows"], protocol()["classes"]))
        record = {"seed": seed, "arm": arm, "eta": protocol()["arms"][arm], "entry_shared_state_sha256": h.state_sha(shared),
                  "parent_counters": h.counter_snapshot(parent), "entry_counters": h.counter_snapshot(shared),
                  "endpoint_counters": h.counter_snapshot(h.full_state(net)), "new_updates": 53100, "new_training_dense_MAC": 1118073600,
                  "training": trace.result(), "scores": evaluation["scores"], "new_probe_inference_calls": evaluation["inference_calls"],
                  "new_probe_inference_MAC": evaluation["inference_dense_MAC"], "full_state_sha256": h.state_sha(h.full_state(net)),
                  "replay_status": "not_planned", "shared_baseline_cost_billed_in_this_arm": False}
        write(folder / "training.json", record)
        return record, {"seed": seed, "arm": arm, "mode": "primary", "seconds_training_and_freeprobe": time.perf_counter() - started}
    except Exception as error:
        h.save_state(folder / "failure-state.npz", net)
        write(folder / "failure.json", {"type": type(error).__name__, "message": str(error), "new_updates": net.t - int(shared["t"]),
                                        "completed_target_trace": trace.result() if trace.targets else None, "auto_retry": False})
        raise


def execute(path, approved, commit, output):
    assert re.fullmatch("[0-9a-f]{40}", commit or ""), "Coordinator Git preregistration commit required"
    started = time.perf_counter()
    manifest, contents, (h, classes, rows, parents, orders, _, _, _, _, _) = validate_inputs(path, approved)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    p = protocol()
    write(output / "execution-intent.json", {"approved_manifest_sha256": approved, "preregistration_commit": commit,
          "source_hashes": manifest["source_hashes"], "all_three_old_gates_before_E3_or_optimizer": True,
          "shared_baseline_physical_copies": 3, "primary_seeds": p["seeds"], "arms": p["arms"], "replay_seeds": [],
          "new_updates_all_primary": 318600, "auto_retry": False})
    phase, timings, training = "all_old_baselines", [], {}
    try:
        begin = time.perf_counter()
        old_states, old_records = all_old_baselines(h, classes["eta001"], parents, contents, rows, output, p["seeds"])
        old_seconds = time.perf_counter() - begin
        phase = "all_cold_E3_baselines"
        begin = time.perf_counter()
        shared, baselines = all_cold_baselines(h, classes["eta001"], parents, old_states, old_records, rows, output, p["seeds"])
        cold_seconds = time.perf_counter() - begin
        phase = "six_primary_one_epoch_arms"
        for seed in p["seeds"]:
            key = str(seed)
            training[key] = {}
            for arm in p["arm_order"]:
                folder = output / f"seed{seed}" / arm
                training[key][arm], timing = train_arm(h, classes[arm], parents[key], shared[key], orders[key], rows, folder, seed, arm)
                timings.append(timing)
                print(canonical({"seed": seed, "arm": arm, "phase": "one_epoch_primary_complete", "new_updates": 53100}), flush=True)
        phase = "all_final_TF_after_six_primary"
        begin = time.perf_counter()
        students, physical_TF_calls, physical_probe_calls = [], 0, 0
        for seed in p["seeds"]:
            key, seed_folder = str(seed), output / f"seed{seed}"
            cold = read(seed_folder / "baseline-generation.json")
            free = {arm: read(seed_folder / arm / "generation.json") for arm in p["arm_order"]}
            paired = paired_arms(rows, cold["rows"], free["eta001"]["rows"], free["eta003"]["rows"], p["classes"], p["old_classes"])
            write(seed_folder / "paired-metrics.json", paired)
            arm_summaries = {}
            for arm in p["arm_order"]:
                folder = seed_folder / arm
                net = h.restore(classes[arm], h.read_npz((folder / "final-state.npz").read_bytes()))
                truth = teacher_forced(h, net, rows, free[arm], p["classes"])
                assert truth["inference_calls"] == 53100
                write(folder / "final-truth.json", truth)
                h.save_state(folder / "final-after-TF.npz", net)
                write(folder / "feasibility.json", paired[arm])
                physical_TF_calls += truth["inference_calls"]
                physical_probe_calls += free[arm]["inference_calls"]
                arm_summaries[arm] = {**training[key][arm], "feasibility": paired[arm], "TF_metrics": truth["metrics"],
                    "final_TF_inference_calls": truth["inference_calls"], "final_TF_inference_MAC": truth["inference_dense_MAC"],
                    "final_counters_with_logical_shared_ancestry": h.counter_snapshot(h.full_state(net))}
            students.append({"seed": seed, "baseline": baselines[key], "arms": arm_summaries,
                             "paired_axes": paired["axes_eta001_minus_eta003"], "paired_metrics_file": f"seed{seed}/paired-metrics.json"})
        TF_seconds = time.perf_counter() - begin
        physical_baseline_calls = sum(record["physical_shared_baseline_inference_calls"] for record in baselines.values())
        feasibility = {arm: feasibility_interpretation([student["arms"][arm]["feasibility"] for student in students]) for arm in p["arm_order"]}
        summary = {"id": p["id"], "status": "complete", "students": students, "feasibility_by_arm": feasibility,
            "primary_low_eta_strict_feasibility": feasibility["eta001"]["strict_feasibility_all_three"],
            "primary_low_eta_interpretation": feasibility["eta001"]["overall_interpretation"],
            "new_updates": 318600, "new_training_dense_MAC": 6708441600,
            "physical_shared_baseline_inference_calls": physical_baseline_calls, "physical_shared_baseline_inference_MAC": physical_baseline_calls * 10432,
            "physical_new_probe_inference_calls": physical_probe_calls, "physical_new_probe_inference_MAC": physical_probe_calls * 10432,
            "physical_final_TF_inference_calls": physical_TF_calls, "physical_final_TF_inference_MAC": physical_TF_calls * 10432,
            "physical_new_inference_calls_total": physical_baseline_calls + physical_probe_calls + physical_TF_calls,
            "physical_new_inference_MAC_total": (physical_baseline_calls + physical_probe_calls + physical_TF_calls) * 10432,
            "physical_baseline_copies": 3, "new_replay_updates": 0, "new_replay_training_dense_MAC": 0, "exact_full_replays": [], "external_model_calls": 0}
        assert physical_TF_calls == 318600
        write(output / "compact.json", summary)
        write(output / "timing.json", {"primary_trajectories": timings, "all_old_baselines_seconds": old_seconds,
              "all_cold_baselines_seconds": cold_seconds, "all_final_TF_and_readout_seconds": TF_seconds,
              "execute_wall_seconds_including_guards": time.perf_counter() - started})
        assert sha(Path(path).read_bytes()) == approved and manifest["source_hashes"] == {name: sha((HERE / name).read_bytes()) for name in CORE}
        return summary
    except Exception as error:
        write(output / "failure.json", {"phase": phase, "type": type(error).__name__, "message": str(error), "auto_retry": False,
              "zero_new_updates_guaranteed": phase in ("all_old_baselines", "all_cold_E3_baselines"), "completed_trajectories": timings})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--engineering", action="store_true")
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument("--parent-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--approved-manifest-sha")
    parser.add_argument("--preregistration-commit")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.prepare:
        assert args.parent_root is not None
        result = prepare(args.parent_root, args.out)
    elif args.engineering or not (args.validate or args.execute):
        import test_probe
        args.out.mkdir(parents=True, exist_ok=False)
        result = test_probe.run_checks(args.parent_root)
        result["source_hashes"] = {name: sha((HERE / name).read_bytes()) for name in CORE}
        write(args.out / "checks.json", result)
    elif args.validate:
        m, _, _ = validate_inputs(args.manifest, args.approved_manifest_sha)
        args.out.mkdir(parents=True, exist_ok=False)
        result = {"status": "passed", "manifest_sha256": args.approved_manifest_sha, "members": len(m["files"]),
                  "trained_model_forward_calls": 0, "new_optimizer_calls": 0}
        write(args.out / "checks.json", result)
    else:
        result = execute(args.manifest, args.approved_manifest_sha, args.preregistration_commit, args.out)
    print(canonical(result), flush=True)
    if result.get("status") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
