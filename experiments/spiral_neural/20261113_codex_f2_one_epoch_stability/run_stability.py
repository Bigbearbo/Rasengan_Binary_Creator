"""One matched historical F2 epoch: only P030 step eta .003 -> .001; prepare is NN-free."""
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
import types
import zipfile
import zlib

if sys.flags.optimize:
    raise RuntimeError("Optimized Python is disabled: exact assertions are required")
sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
CORE = ("run_stability.py", "protocol.json", "test_stability.py")
CLASSES = ("E1", "E2", "F1", "F2")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def git_blob(value):
    return hashlib.sha1(b"blob " + str(len(value)).encode("ascii") + b"\0" + value).hexdigest()


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
    assert p["id"] == "F2-STABILITY-ETA001-20261113" and p["seeds"] == [101, 202, 303]
    assert p["updates_per_seed"] == 36000 and p["new_updates_all_primary"] == 108000
    assert p["replay_seeds"] == [] and p["new_replay_updates"] == 0
    assert p["new_training_dense_MAC_per_seed"] == 36000 * 21056 == 758016000
    return p


def load_f2(content, original_protocol):
    """Pinned helper definitions only: no old main/import/prepare/execute is evaluated."""
    p = protocol()
    assert sha(content) == p["F2_runner_sha256"] and sha(original_protocol) == p["F2_protocol_sha256"]
    wanted = {"canonical", "sha", "git_blob", "counter_snapshot", "full_state", "state_sha", "equal_state", "npz_bytes",
              "read_npz", "save_state", "restore", "npy_bytes", "make_zip", "EpochTrace", "generate", "word", "encode",
              "flip_answer", "expected_bank", "questions", "target_pool", "schedules", "data_checks", "probe",
              "token_metrics", "churn_metrics", "final_tf", "source_model"}
    tree = ast.parse(content.decode("utf-8"))
    nodes = [copy.deepcopy(node) for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in wanted]
    assert {node.name for node in nodes} == wanted
    module = types.SimpleNamespace()
    namespace = {"np": np, "json": json, "copy": copy, "ast": ast, "hashlib": hashlib, "io": io,
                 "zipfile": zipfile, "Path": Path, "Counter": __import__("collections").Counter,
                 "protocol": lambda: json.loads(original_protocol.decode("utf-8")), "__name__": "pinned_F2_helpers"}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<pinned-F2-helper-definitions>", "exec"), namespace)
    namespace["write"] = write
    for name in wanted:
        setattr(module, name, namespace[name])
    return module


def model_classes(content):
    """Return original and intervention classes, exact AST dumps and single-leaf proof."""
    p = protocol()
    assert sha(content) == p["source_sha256"]
    original = next(node for node in ast.parse(content.decode("utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "Model")
    dump = ast.dump(original, include_attributes=False)
    assert sha(dump.encode("utf-8")) == p["Model_AST_sha256"]
    changed = copy.deepcopy(original)
    step = next(node for node in changed.body if isinstance(node, ast.FunctionDef) and node.name == "step")
    constants = [node for node in ast.walk(step) if isinstance(node, ast.Constant) and type(node.value) is float and node.value == .003]
    assert len(constants) == 1, "Exactly one eta leaf is allowed"
    constants[0].value = .001
    updated_dump = ast.dump(changed, include_attributes=False)
    constants[0].value = .003
    assert ast.dump(changed, include_attributes=False) == dump
    constants[0].value = .001
    classes = []
    for node in (original, changed):
        namespace = {"np": np, "json": json, "__name__": "fixed_P030_AST"}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<P030-single-eta-intervention>", "exec"), namespace)
        classes.append(namespace["Model"])
    proof = {"source_sha256": sha(content), "original_Model_AST_sha256": sha(dump.encode("utf-8")),
             "intervention_Model_AST_sha256": sha(updated_dump.encode("utf-8")), "function": "Model.step",
             "unique_changed_float_constant": {"before": .003, "after": .001}, "entire_AST_equal_after_reversing_one_leaf": True}
    return classes[0], classes[1], dump, updated_dump, proof


def exact_all(scores):
    return all(scores[name]["questions"] == scores[name]["whole_correct"] == 900 for name in CLASSES)


def paired_metrics(f2, rows, baseline, new, control):
    """QID-aligned pure token comparison; no net-score substitution for lost/recovered IDs."""
    maps = [{row["question_id"]: row["tokens"] for row in part} for part in (baseline, new, control)]
    assert all(len(part) == len(rows) and set(part) == {row["question_id"] for row in rows} for part in maps)
    result = {}
    for name in CLASSES:
        part = [row for row in rows if row["class"] == name]
        lost_new, lost_control = [], []
        categories = {key: [] for key in ("both_correct", "new_only_correct", "control_only_correct", "both_wrong")}
        for row in part:
            qid, expected = row["question_id"], row["A"] + "S"
            before, a, b = (mapping[qid] == expected for mapping in maps)
            assert before, "All matched starts must be correct"
            if not a:
                lost_new.append(qid)
            if not b:
                lost_control.append(qid)
            category = "both_correct" if a and b else "new_only_correct" if a else "control_only_correct" if b else "both_wrong"
            categories[category].append(qid)
        result[name] = {"questions": len(part), "new_lost_QIDs": lost_new, "control_lost_QIDs": lost_control,
                        "new_lost": len(lost_new), "control_lost": len(lost_control),
                        "new_minus_control_lost": len(lost_new) - len(lost_control), "between_arm_QIDs": categories}
    n, c = sum(row["new_lost"] for row in result.values()), sum(row["control_lost"] for row in result.values())
    return {"by_class": result, "new_total_lost": n, "historical_control_total_lost": c, "new_minus_control_lost": n - c,
            "directional_hypothesis_pass": n < c, "new_all_four_classes_full": n == 0,
            "new_churn": f2.churn_metrics(rows, baseline, new), "historical_churn": f2.churn_metrics(rows, baseline, control),
            "extra_forward_calls": 0}


def collect_public(parent_root):
    """Read only publicly pinned source archives and exact selected members; zero NN calls."""
    p, root = protocol(), Path(parent_root)
    public = root / "publication/final/public"
    publication_raw = (public / "publication-manifest.json").read_bytes()
    assert (sha(publication_raw), git_blob(publication_raw)) == (p["parent_publication_manifest_sha256"], p["parent_publication_manifest_Git_blob"])
    publication = json.loads(publication_raw)
    receipt_raw = (root / "publication-receipt.json").read_bytes()
    receipt = json.loads(receipt_raw)
    assert receipt["result_commit"] == p["parent_head"]
    receipts = {row["name"]: row for row in receipt["byte_checks"]}
    used, members, archives = {}, {}, {}
    def public_file(name):
        expected = {"sha256": sha(publication_raw), "Git_blob": git_blob(publication_raw), "bytes": len(publication_raw)} if name == "publication-manifest.json" else publication["files"][name]
        check = receipts[name]
        assert check["byte_match"] and check["ref_match"] and check["commit"] == p["parent_head"]
        assert all(check[key] == expected[key] for key in ("sha256", "Git_blob", "bytes"))
        candidate = root / "remote-byte-checks" / ("final-" + name)
        raw = candidate.read_bytes() if candidate.is_file() else (public / name).read_bytes()
        assert (sha(raw), git_blob(raw), len(raw)) == (expected["sha256"], expected["Git_blob"], expected["bytes"])
        used[name] = check
        return raw
    assert public_file("publication-manifest.json") == publication_raw
    inputs_raw = public_file("inputs.zip")
    old_manifest_raw = public_file("manifest.json")
    old_manifest = json.loads(old_manifest_raw)
    assert old_manifest["archive"]["sha256"] == sha(inputs_raw)
    contents = {"provenance/publication-manifest.json": publication_raw, "provenance/F2-manifest.json": old_manifest_raw,
                "vendor/run_f2.py": public_file("run_f2.py"), "vendor/protocol.json": public_file("protocol.json")}
    with zipfile.ZipFile(io.BytesIO(inputs_raw)) as archive:
        def input_member(name):
            raw = archive.read(name)
            assert old_manifest["files"][name] == {"sha256": sha(raw), "bytes": len(raw)}
            return raw
        for name in ("source/p030_binary_continual.py", "payloads.json", "questions.json"):
            contents[name] = input_member(name)
        for seed in p["seeds"]:
            old_name = old_manifest["schedules"][str(seed)]["file"]
            raw = input_member(old_name)
            actual = np.load(io.BytesIO(raw), allow_pickle=False)
            next_epoch = p["next_epochs"][str(seed)]
            assert actual.shape == (40, 36000, 2) and actual.dtype.str == "<u2"
            buffer = io.BytesIO()
            np.save(buffer, actual[next_epoch - 1], allow_pickle=False)
            name = f"orders/seed{seed}.npy"
            contents[name] = buffer.getvalue()
            members[name] = {"archive": "inputs.zip", "member": old_name, "source_sha256": sha(raw), "epoch_one_based": next_epoch,
                             "slice_sha256": sha(contents[name]), "source_shape": list(actual.shape)}
    def science_member(member, destination):
        matches = [name for name, value in publication["archives"].items() if member in value["members"]]
        assert len(matches) == 1
        archive_name = matches[0]
        if archive_name not in archives:
            archives[archive_name] = public_file(archive_name)
        expected = publication["archives"][archive_name]["members"][member]
        with zipfile.ZipFile(io.BytesIO(archives[archive_name])) as archive:
            raw, crc = archive.read(member), format(archive.getinfo(member).CRC, "08x")
        assert (sha(raw), git_blob(raw), len(raw), crc) == (expected["sha256"], expected["Git_blob"], expected["bytes"], expected["CRC32"])
        contents[destination] = raw
        members[destination] = {"archive": archive_name, "member": member, **expected}
    for seed in p["seeds"]:
        for role, epoch in (("start", p["start_epochs"][str(seed)]), ("control", p["next_epochs"][str(seed)])):
            for file, output in ((f"state-{epoch:03}.npz", "state.npz"), (f"generation-{epoch:03}.json", "generation.json"), (f"epoch-{epoch:03}.json", "record.json")):
                science_member(f"science/seed{seed}/{file}", f"historical/seed{seed}/{role}-{output}")
        contents[f"initial/seed{seed}.npz"] = contents[f"historical/seed{seed}/start-state.npz"]
    proof = {"parent_head": p["parent_head"], "original_receipt_sha256": sha(receipt_raw), "public_byte_checks": used,
             "selected_members": members, "formal_forward_calls": 0, "new_optimizer_calls": 0}
    contents["provenance/public-proof.json"] = (canonical(proof) + "\n").encode("utf-8")
    return contents, proof


def inspect_contents(contents):
    p = protocol()
    publication_raw = contents["provenance/publication-manifest.json"]
    assert (sha(publication_raw), git_blob(publication_raw)) == (p["parent_publication_manifest_sha256"], p["parent_publication_manifest_Git_blob"])
    publication, proof = json.loads(publication_raw), json.loads(contents["provenance/public-proof.json"])
    assert proof["parent_head"] == p["parent_head"]
    for name, check in proof["public_byte_checks"].items():
        expected = {"sha256": sha(publication_raw), "Git_blob": git_blob(publication_raw), "bytes": len(publication_raw)} if name == "publication-manifest.json" else publication["files"][name]
        assert all(check[key] == expected[key] for key in ("sha256", "Git_blob", "bytes"))
        assert check["byte_match"] and check["ref_match"] and check["commit"] == p["parent_head"]
    for name, source in proof["selected_members"].items():
        if source["archive"] == "inputs.zip":
            assert source["slice_sha256"] == sha(contents[name])
            continue
        expected = publication["archives"][source["archive"]]["members"][source["member"]]
        assert all(source[key] == expected[key] for key in expected)
        raw = contents[name]
        assert (sha(raw), git_blob(raw), len(raw), format(zlib.crc32(raw), "08x")) == (expected["sha256"], expected["Git_blob"], expected["bytes"], expected["CRC32"])
    old_manifest = json.loads(contents["provenance/F2-manifest.json"])
    assert sha(contents["provenance/F2-manifest.json"]) == publication["files"]["manifest.json"]["sha256"]
    for name in ("source/p030_binary_continual.py", "payloads.json", "questions.json"):
        assert old_manifest["files"][name] == {"sha256": sha(contents[name]), "bytes": len(contents[name])}
    f2 = load_f2(contents["vendor/run_f2.py"], contents["vendor/protocol.json"])
    original, changed, a, b, ast_proof = model_classes(contents["source/p030_binary_continual.py"])
    rows, bank = json.loads(contents["questions.json"]), json.loads(contents["payloads.json"])
    assert rows == f2.questions(bank, rows[:2700])
    assert f2.data_checks(bank, rows, rows[:2700])["unique_teacher_prefixes"] == 36000
    starts, controls, orders = {}, {}, {}
    parent_info = {}
    for seed in p["seeds"]:
        key, base = str(seed), f"historical/seed{seed}"
        starts[key] = f2.read_npz(contents[f"initial/seed{seed}.npz"])
        assert contents[f"initial/seed{seed}.npz"] == contents[f"{base}/start-state.npz"]
        controls[key] = f2.read_npz(contents[f"{base}/control-state.npz"])
        for role, saved, epoch, t in (("start", starts[key], p["start_epochs"][key], p["start_t"][key]), ("control", controls[key], p["next_epochs"][key], p["end_t"][key])):
            record = json.loads(contents[f"{base}/{role}-record.json"])
            assert (int(saved["L"]), int(saved["H"]), int(saved["meta_seed"]), int(saved["t"])) == (80, 64, seed, t)
            assert record["epoch"] == epoch and record["full_state_sha256"] == f2.state_sha(saved)
            assert f2.equal_state(saved, f2.full_state(f2.restore(changed, saved)))
            generation = json.loads(contents[f"{base}/{role}-generation.json"])
            assert generation["scores"] == record["scores"]
            assert f2.token_metrics(rows, generation["rows"])["by_class"] == record["token_metrics"]
        baseline = json.loads(contents[f"{base}/start-generation.json"])
        control = json.loads(contents[f"{base}/control-generation.json"])
        assert exact_all(baseline["scores"])
        assert json.loads(contents[f"{base}/start-record.json"])["first_full_epoch"] == p["start_epochs"][key]
        pairing = paired_metrics(f2, rows, baseline["rows"], baseline["rows"], control["rows"])
        assert pairing["historical_control_total_lost"] == p["historical_control_lost_QIDs"][key]
        orders[key] = np.load(io.BytesIO(contents[f"orders/seed{seed}.npy"]), allow_pickle=False)
        complete, _ = f2.schedules(seed, rows)
        assert sha(f2.npy_bytes(complete)) == old_manifest["files"][old_manifest["schedules"][key]["file"]]["sha256"]
        assert np.array_equal(orders[key], complete[p["next_epochs"][key] - 1]) and orders[key].dtype.str == "<u2"
        parent_info[key] = {"raw_sha256": sha(contents[f"initial/seed{seed}.npz"]), "full_state_sha256": f2.state_sha(starts[key]),
                            "counters": f2.counter_snapshot(starts[key]), "historical_control_lost": pairing["historical_control_total_lost"]}
    return f2, original, changed, rows, starts, controls, orders, parent_info, ast_proof, a, b


def prepare(parent_root, output):
    contents, _ = collect_public(parent_root)
    f2, _, _, _, _, _, _, parents, ast_proof, original_ast, changed_ast = inspect_contents(contents)
    contents.update({"plan.json": (HERE / "protocol.json").read_bytes(),
                     "source/Model-original.ast": (original_ast + "\n").encode("utf-8"),
                     "source/Model-eta001.ast": (changed_ast + "\n").encode("utf-8"),
                     "source/AST-change.json": (canonical(ast_proof) + "\n").encode("utf-8")})
    archive = f2.make_zip(contents)
    manifest = {"schema": "f2-stability-paired-v1", "id": protocol()["id"], "protocol": protocol(), "runtime": runtime(),
                "status": "frozen_before_any_new_trained_model_forward_or_update", "parents": parents, "AST_change": ast_proof,
                "source_hashes": {name: sha((HERE / name).read_bytes()) for name in CORE},
                "schedules": {str(seed): {"file": f"orders/seed{seed}.npy", "shape": [36000, 2], "dtype": "<u2", "source_epoch": protocol()["next_epochs"][str(seed)]} for seed in protocol()["seeds"]},
                "archive": {"file": "inputs.zip", "sha256": sha(archive), "bytes": len(archive)},
                "files": {name: {"sha256": sha(raw), "bytes": len(raw)} for name, raw in sorted(contents.items())},
                "formal_forward_calls": 0, "new_optimizer_calls": 0, "external_model_calls": 0}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "inputs.zip").open("xb") as stream:
        stream.write(archive)
    write(output / "manifest.json", manifest)
    result = {"manifest_sha256": sha((output / "manifest.json").read_bytes()), "source_hashes": manifest["source_hashes"],
              "inputs_zip_sha256": sha(archive), "inputs_zip_bytes": len(archive), "members": len(contents), "AST_change": ast_proof,
              "formal_forward_calls": 0, "new_optimizer_calls": 0}
    write(output / "source-freeze.json", result)
    return result


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
    assert data[7] == m["parents"] and data[8] == m["AST_change"]
    assert contents["source/Model-original.ast"] == (data[9] + "\n").encode("utf-8")
    assert contents["source/Model-eta001.ast"] == (data[10] + "\n").encode("utf-8")
    assert json.loads(contents["source/AST-change.json"]) == m["AST_change"]
    return m, contents, data


def baseline_one(f2, cls, parent, raw_parent, archived, rows, output, seed):
    folder = output / f"seed{seed}"
    folder.mkdir()
    with (folder / "initial-state.npz").open("xb") as stream:
        stream.write(raw_parent)
    net = f2.restore(cls, parent)
    before = f2.full_state(net)
    f2.save_state(folder / "baseline-before.npz", net)
    evaluation = f2.probe(net, rows)
    after = f2.full_state(net)
    unchanged = set(before) - {"meta_inference_calls", "meta_inference_macs"}
    assert f2.equal_state({key: before[key] for key in unchanged}, {key: after[key] for key in unchanged})
    record = {"seed": seed, "scores": evaluation["scores"], "all_four_integrity_pass": exact_all(evaluation["scores"]),
              "archived_start_generation_exact": evaluation == archived, "before_state_sha256": f2.state_sha(before),
              "after_state_sha256": f2.state_sha(after), "baseline_inference_calls": evaluation["inference_calls"],
              "baseline_inference_MAC": evaluation["inference_dense_MAC"], "new_optimizer_updates": 0, "only_inference_counters_changed": True}
    f2.save_state(folder / "baseline-after.npz", net)
    write(folder / "baseline-generation.json", evaluation)
    write(folder / "baseline.json", record)
    assert record["all_four_integrity_pass"] and record["archived_start_generation_exact"], "Whole batch aborted before any update: baseline integrity failed"
    return after, record


def all_baselines(f2, cls, parents, contents, rows, output, seeds):
    states, records = {}, {}
    for seed in seeds:
        key = str(seed)
        states[key], records[key] = baseline_one(f2, cls, parents[key], contents[f"initial/seed{seed}.npz"],
            json.loads(contents[f"historical/seed{seed}/start-generation.json"]), rows, output, seed)
    return states, records


def train_one(f2, cls, parent, baseline, order, rows, folder, seed):
    net = f2.restore(cls, baseline)
    trace = f2.EpochTrace()
    started = time.perf_counter()
    try:
        for qid, position in order:
            row, position = rows[int(qid)], int(position)
            target = (row["A"] + "S")[position]
            pred, loss = net.step(row["Q"] + row["A"][:position], target)
            trace.observe(row["question_id"], position, pred, loss, target)
        assert trace.targets == net.t - int(parent["t"]) == 36000
        assert net.train_macs - int(parent["meta_train_macs"]) == 758016000
        assert net.t == protocol()["end_t"][str(seed)] and (net.L, net.H, net.parameters) == (80, 64, 10499)
        assert json.loads(str(parent["meta_events"])) == net.events
        assert all(value.dtype == np.float32 and np.isfinite(value).all() for group in (net.p, net.m, net.v) for value in group)
        result = f2.probe(net, rows)
        f2.save_state(folder / "new-final-state.npz", net)
        write(folder / "new-generation.json", result)
        write(folder / "new-token-metrics.json", f2.token_metrics(rows, result["rows"]))
        record = {"seed": seed, "eta": .001, "source_epoch": protocol()["next_epochs"][str(seed)], "training": trace.result(),
                  "start_counters": f2.counter_snapshot(parent), "final_counters": f2.counter_snapshot(f2.full_state(net)),
                  "new_updates": 36000, "new_training_dense_MAC": 758016000, "scores": result["scores"],
                  "new_probe_inference_calls": result["inference_calls"], "new_probe_inference_MAC": result["inference_dense_MAC"],
                  "full_state_sha256": f2.state_sha(f2.full_state(net)), "replay_status": "not_planned"}
        write(folder / "training.json", record)
        return record, {"seed": seed, "mode": "primary", "seconds": time.perf_counter() - started}
    except Exception:
        f2.save_state(folder / "failure-state.npz", net)
        raise


def execute(path, approved, commit, output):
    assert re.fullmatch("[0-9a-f]{40}", commit or ""), "Coordinator Git preregistration commit required"
    m, contents, (f2, _, cls, rows, parents, controls, orders, _, _, _, _) = validate_inputs(path, approved)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write(output / "execution-intent.json", {"approved_manifest_sha256": approved, "preregistration_commit": commit,
          "source_hashes": m["source_hashes"], "all_baselines_before_any_optimizer": True, "primary_seeds": protocol()["seeds"],
          "replay_seeds": [], "new_updates_all_primary": 108000, "auto_retry": False})
    phase, timings, students = "all_baselines", [], []
    try:
        baselines, baseline_records = all_baselines(f2, cls, parents, contents, rows, output, protocol()["seeds"])
        phase = "three_primary_one_epoch_trajectories"
        for seed in protocol()["seeds"]:
            key, folder = str(seed), output / f"seed{seed}"
            _, timing = train_one(f2, cls, parents[key], baselines[key], orders[key], rows, folder, seed)
            timings.append(timing)
            print(canonical({"seed": seed, "phase": "one_epoch_primary_complete", "new_updates": 36000}), flush=True)
        phase = "final_TF_after_all_primary"
        for seed in protocol()["seeds"]:
            key, folder = str(seed), output / f"seed{seed}"
            baseline = read(folder / "baseline-generation.json")
            new = read(folder / "new-generation.json")
            historical = json.loads(contents[f"historical/seed{seed}/control-generation.json"])
            pairing = paired_metrics(f2, rows, baseline["rows"], new["rows"], historical["rows"])
            write(folder / "paired-metrics.json", pairing)
            for source, dest in (("control-state.npz", "historical-control-state.npz"), ("control-generation.json", "historical-control-generation.json"), ("control-record.json", "historical-control-record.json")):
                with (folder / dest).open("xb") as stream:
                    stream.write(contents[f"historical/seed{seed}/{source}"])
            net = f2.restore(cls, f2.read_npz((folder / "new-final-state.npz").read_bytes()))
            truth = f2.final_tf(net, rows, new)
            write(folder / "final-truth.json", truth)
            f2.save_state(folder / "final-after-TF.npz", net)
            students.append({"seed": seed, "start_epoch": protocol()["start_epochs"][key], "source_epoch": protocol()["next_epochs"][key],
                "start_counters": f2.counter_snapshot(parents[key]), "final_counters": f2.counter_snapshot(f2.full_state(net)),
                "new_updates": 36000, "new_training_dense_MAC": 758016000, "scores": new["scores"], "primary_pair": pairing,
                "baseline_inference_calls": baseline_records[key]["baseline_inference_calls"],
                "baseline_inference_MAC": baseline_records[key]["baseline_inference_MAC"],
                "new_probe_inference_calls": new["inference_calls"], "new_probe_inference_MAC": new["inference_dense_MAC"],
                "final_TF_inference_calls": truth["inference_calls"], "final_TF_inference_MAC": truth["inference_dense_MAC"],
                "TF_metrics": truth["metrics"], "replay_status": "not_planned"})
        summary = {"id": protocol()["id"], "status": "complete", "students": students,
            "primary_hypothesis_all_three_fewer_lost": all(item["primary_pair"]["directional_hypothesis_pass"] for item in students),
            "new_four_class_full_seeds": [item["seed"] for item in students if item["primary_pair"]["new_all_four_classes_full"]],
            "new_updates": 108000, "new_training_dense_MAC": 2274048000,
            "final_TF_inference_calls": sum(item["final_TF_inference_calls"] for item in students),
            "new_replay_updates": 0, "new_replay_training_dense_MAC": 0, "exact_full_replays": [], "external_model_calls": 0}
        write(output / "compact.json", summary)
        write(output / "timing.json", timings)
        assert sha(Path(path).read_bytes()) == approved and m["source_hashes"] == {name: sha((HERE / name).read_bytes()) for name in CORE}
        return summary
    except Exception as error:
        write(output / "failure.json", {"phase": phase, "type": type(error).__name__, "message": str(error), "auto_retry": False,
                                       "zero_new_updates_guaranteed": phase == "all_baselines", "completed_trajectories": timings})
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
        import test_stability
        args.out.mkdir(parents=True, exist_ok=False)
        result = test_stability.run_checks(args.parent_root)
        result["source_hashes"] = {name: sha((HERE / name).read_bytes()) for name in CORE}
        write(args.out / "checks.json", result)
    elif args.validate:
        manifest, _, _ = validate_inputs(args.manifest, args.approved_manifest_sha)
        args.out.mkdir(parents=True, exist_ok=False)
        result = {"status": "passed", "manifest_sha256": args.approved_manifest_sha, "members": len(manifest["files"]),
                  "formal_forward_calls": 0, "new_optimizer_calls": 0}
        write(args.out / "checks.json", result)
    else:
        result = execute(args.manifest, args.approved_manifest_sha, args.preregistration_commit, args.out)
    print(canonical(result), flush=True)


if __name__ == "__main__":
    main()
