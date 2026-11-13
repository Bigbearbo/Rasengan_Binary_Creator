"""Independent public-parent/data/order and portable continuation gate; zero NN calls."""
from collections import Counter
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile
import zlib

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARENT_HEAD = "7213cce112a8411b13dc128c49f9e88acfc9d65f"
PUBLICATION_SHA = "660390547db4dc014e094de2e1b03ca851cb511502f68c3d04975962baa32a6c"
PUBLICATION_BLOB = "30200c222b0086d02db7044269877501cd3d2d4d"
PARENT_T = {101: 151200, 202: 181800, 303: 223200}
PARENT_STATE_SHA = {
    101: "3408a4eeca740ad828c8000eaf50d3ea587430b092350a437f09e7eed50a5db1",
    202: "5e4d6763dddea23ab4f1ee583fc80f7d2c0d58470c4f43cbf527cea7bd3f48d0",
    303: "31dda85da683dfac8a869cab64dd7e5aab2fb780a4a4b757094bcb39f5407b31",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def state_sha(state):
    result = hashlib.sha256()
    for name, value in sorted(state.items()):
        result.update(canonical([name, value.dtype.str, list(value.shape)]).encode())
        result.update(value.tobytes(order="C"))
    return result.hexdigest()


def main(args):
    manifest_path, code = args.manifest.resolve(), args.code_root.resolve()
    prereg = manifest_path.parent
    assert sha(manifest_path.read_bytes()) == args.approved_manifest_sha
    manifest, freeze = read(manifest_path), read(prereg / "source-freeze.json")
    pins = manifest["source_hashes"]
    assert set(pins) == {"run_mixed.py", "protocol.json", "test_mixed.py"}
    assert freeze["manifest_sha256"] == args.approved_manifest_sha and freeze["source_hashes"] == pins
    for name, pin in pins.items():
        assert sha((code / name).read_bytes()) == pin
    zip_path = prereg / "inputs.zip"
    assert manifest["archive"]["file"] == "inputs.zip"
    assert sha(zip_path.read_bytes()) == manifest["archive"]["sha256"] == freeze["inputs_zip_sha256"]
    assert zip_path.stat().st_size == manifest["archive"]["bytes"] == freeze["inputs_zip_bytes"]
    names = {"payloads.json", "parent-questions.json", "questions.json", "source/p030_binary_continual.py", "plan.json", "provenance/parent-publication-manifest.json", "provenance/parent-provenance.json"}
    names |= {f"initial/seed{seed}.npz" for seed in PARENT_T} | {f"orders/seed{seed}.npy" for seed in PARENT_T}
    with zipfile.ZipFile(zip_path) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) == 13
        assert set(archive.namelist()) == names == set(manifest["files"])
        raw = {name: archive.read(name) for name in names}
    for name, value in raw.items():
        assert {"sha256": sha(value), "bytes": len(value)} == manifest["files"][name]
    assert raw["plan.json"] == (code / "protocol.json").read_bytes()
    protocol = manifest["protocol"]
    assert json.loads(raw["plan.json"]) == protocol
    assert protocol["parent_head"] == PARENT_HEAD and protocol["parent_t"] == {str(key): value for key, value in PARENT_T.items()}
    assert protocol["seeds"] == [101, 202, 303] and protocol["replay_seeds"] == [101]
    assert protocol["classes"] == ["E1", "E2", "F1"] and protocol["model"] == {"L": 80, "H": 64, "parameters": 10499}
    assert manifest["formal_forward_calls"] == manifest["new_optimizer_calls"] == 0
    publication_raw = raw["provenance/parent-publication-manifest.json"]
    assert (sha(publication_raw), blob(publication_raw)) == (PUBLICATION_SHA, PUBLICATION_BLOB)
    publication = json.loads(publication_raw)
    provenance = json.loads(raw["provenance/parent-provenance.json"])
    assert provenance["parent_head"] == provenance["prior_receipt_public_fields"]["result_commit"] == PARENT_HEAD
    assert provenance["prior_receipt_public_fields"]["status"] == "complete_verified"
    assert provenance["parent_publication_manifest_sha256"] == provenance["prior_receipt_public_fields"]["publication_manifest_sha256"] == PUBLICATION_SHA
    assert provenance["parent_publication_manifest_Git_blob"] == PUBLICATION_BLOB
    assert provenance["parents"] == manifest["parents"] == freeze["parents"]
    data_meta = provenance["data_archive"]
    assert all(data_meta[key] == publication["files"]["inputs.zip"][key] for key in ("bytes", "sha256", "Git_blob"))
    assert data_meta["payloads_member_sha256"] == sha(raw["payloads.json"])
    assert data_meta["old_questions_member_sha256"] == sha(raw["parent-questions.json"])
    parent_root = args.parent_root.resolve()
    assert sha((parent_root / "publication/final/public/publication-manifest.json").read_bytes()) == PUBLICATION_SHA
    old_receipt = read(parent_root / "publication-receipt.json")
    assert old_receipt["status"] == "complete_verified" and old_receipt["result_commit"] == PARENT_HEAD
    assert sha((parent_root / "publication-receipt.json").read_bytes()) == provenance["prior_publication_receipt_sha256"]
    remote_checks = {value["name"]: value for value in old_receipt["remote_file_byte_checks"]}
    archive_evidence = {}

    def check_public_zip(meta):
        name = meta["file"]
        check = remote_checks[name]
        assert check["byte_match"] and check["ref_match"] and check["commit"] == PARENT_HEAD
        assert all(check[key] == meta[key] for key in ("bytes", "sha256", "Git_blob"))
        path = parent_root / "remote-byte-checks" / ("final-" + name)
        if not path.exists():
            path = parent_root / "publication/final/public" / name
        content = path.read_bytes()
        assert (len(content), sha(content), blob(content)) == (meta["bytes"], meta["sha256"], meta["Git_blob"])
        archive_evidence[name] = {"bytes": len(content), "sha256": sha(content), "Git_blob": blob(content)}
        return content

    with zipfile.ZipFile(io.BytesIO(check_public_zip(data_meta))) as archive:
        assert archive.read("payloads.json") == raw["payloads.json"]
        assert archive.read("questions.json") == raw["parent-questions.json"]
        assert archive.read("source/p030_binary_continual.py") == raw["source/p030_binary_continual.py"]
    parents = {}
    for seed, t in PARENT_T.items():
        meta = manifest["parents"][str(seed)]
        source_archive, member = meta["source_archive"], meta["source_member"]
        public_archive = publication["archives"][source_archive["file"]]
        assert all(source_archive[key] == public_archive[key] for key in ("bytes", "sha256", "Git_blob"))
        assert member["path"] == f"science/seed{seed}/final-state.npz"
        assert {key: value for key, value in member.items() if key != "path"} == public_archive["members"][member["path"]]
        content = raw[meta["file"]]
        assert (len(content), sha(content), blob(content)) == (member["bytes"], member["sha256"], member["Git_blob"])
        assert format(zlib.crc32(content) & 0xffffffff, "08x") == member["CRC32"]
        with zipfile.ZipFile(io.BytesIO(check_public_zip(source_archive))) as archive:
            assert archive.read(member["path"]) == content
            assert format(archive.getinfo(member["path"]).CRC, "08x") == member["CRC32"]
        assert (parent_root / f"science/seed{seed}/final-state.npz").read_bytes() == content
        with np.load(io.BytesIO(content), allow_pickle=False) as archive:
            state = {name: archive[name].copy() for name in archive.files}
        assert len(state) == 25 and state_sha(state) == meta["full_state_sha256"] == PARENT_STATE_SHA[seed]
        assert (int(state["L"]), int(state["H"]), int(state["meta_seed"]), int(state["t"])) == (80, 64, seed, t)
        assert meta["raw_sha256"] == sha(content)
        counters = {"t": int(state["t"]), "train_MAC": int(state["meta_train_macs"]), "inference_calls": int(state["meta_inference_calls"]), "inference_MAC": int(state["meta_inference_macs"])}
        assert counters == meta["counters"] and counters["train_MAC"] == t * 21056 and counters["inference_MAC"] == counters["inference_calls"] * 10432
        assert str(state["meta_events"]) == "[]"
        assert json.loads(str(state["growth_rng"])) == np.random.default_rng(seed + 73000).bit_generator.state
        for label in ("p", "m", "v", "birth"):
            for index, shape in enumerate(((160, 64), (64,), (64, 3), (3,))):
                value = state[f"{label}{index}"]
                assert value.shape == shape and value.dtype == (np.int64 if label == "birth" else np.float32) and np.isfinite(value).all()
                if label == "birth":
                    assert not np.any(value)
                if label == "v":
                    assert (value >= 0).all()
        assert sum(state[f"{label}{index}"].nbytes for label in ("p", "m", "v", "birth") for index in range(4)) == 209980
        parents[str(seed)] = state
    suffix = np.random.default_rng(331000).integers(0, 30, size=(900, 2))
    bank = [[pair // 30, pair % 30, int(suffix[pair, 0]), int(suffix[pair, 1])] for pair in range(900)]
    assert json.loads(raw["payloads.json"]) == bank
    word = lambda value: format(value, "05b") + "0"
    old_questions, rows, prefixes = [], [], {}
    label_counts = Counter()
    for r in (1, 2):
        for pair, payload in enumerate(bank):
            q = "01010" + format(r, "03b") + "0" + "".join(word(value) for value in payload) + "111100"
            a = "".join(word(value) for value in payload[:r])
            old = {"question_id": (r - 1) * 900 + pair, "pair_id": pair, "r": r, "payload": payload, "Q": q, "A": a}
            old_questions.append(old)
            rows.append({**old, "class": "E1" if r == 1 else "E2", "op": "010"})
    assert json.loads(raw["parent-questions.json"]) == old_questions
    for pair, payload in enumerate(bank):
        a = "".join(str(1 - int(bit)) for bit in format(payload[0], "05b")) + "0"
        q = "01100" + "0010" + "".join(word(value) for value in payload) + "111100"
        rows.append({"question_id": 1800 + pair, "pair_id": pair, "r": 1, "payload": payload, "Q": q, "A": a, "class": "F1", "op": "100"})
    assert json.loads(raw["questions.json"]) == rows and len({row["Q"] for row in rows}) == 2700
    assert rows[1800]["A"] + "S" == "111110S" and rows[1830]["A"] + "S" == "111100S"
    for row in rows:
        assert len(row["Q"]) == 39 and len(row["A"] + "S") == (13 if row["class"] == "E2" else 7)
        for position, label in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:position]
            assert prefix not in prefixes
            prefixes[prefix] = label
            label_counts[label] += 1
    assert len(prefixes) == 24300 and dict(label_counts) == {"0": 12840, "S": 2700, "1": 8760}
    pool = np.asarray([(offset + pair, position) for pair in range(900) for offset in (0, 900, 1800) for position in range(len(rows[offset + pair]["A"]) + 1)], dtype="<u2")
    expected_data = {"payloads": 900, "questions": 2700, "old_Echo_QA_unchanged": 1800, "unique_teacher_prefixes": 24300, "target_counts_by_class": {"E1": 6300, "E2": 11700, "F1": 6300}, "literal_control_answer_cases_preserved": True}
    assert manifest["data_checks"] == expected_data
    orders = {}
    for seed in PARENT_T:
        rng = np.random.default_rng(seed + 444000)
        expected = np.stack([pool[rng.permutation(len(pool))] for _ in range(40)])
        actual = np.load(io.BytesIO(raw[f"orders/seed{seed}.npy"]), allow_pickle=False)
        assert actual.dtype.str == "<u2" and actual.shape == (40, 24300, 2) and np.array_equal(actual, expected)
        assert manifest["schedules"][str(seed)]["final_schedule_RNG"] == rng.bit_generator.state
        orders[str(seed)] = actual
    fresh = HERE / "portable-gate"
    fresh.mkdir(exist_ok=False)
    for name in pins:
        shutil.copyfile(code / name, fresh / name)
    for name in ("manifest.json", "inputs.zip", "source-freeze.json"):
        shutil.copyfile(prereg / name, fresh / name)
    before = {path.name: sha(path.read_bytes()) for path in fresh.iterdir()}
    enabled, forbidden, blocked = True, [], []

    def hook(event, values):
        if enabled and event == "open" and isinstance(values[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(values[0])).resolve()
            if path.is_relative_to(ROOT) and not path.is_relative_to(fresh):
                blocked.append(1)
                raise AssertionError("Original workspace dependency read")

    sys.addaudithook(hook)
    spec = importlib.util.spec_from_file_location("relocated_mixed_gate", fresh / "run_mixed.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    native = module.source_model

    def denied(*values, **kwargs):
        forbidden.append(1)
        raise AssertionError("Model inference/optimizer or original-parent dependency forbidden")

    def guarded(content):
        cls = native(content)
        for name in ("step", "lesson", "loss_grad", "forward", "generate", "grow"):
            setattr(cls, name, denied)
        return cls

    module.source_model = guarded
    for name in ("execute", "baseline_one", "all_baselines", "train_one", "probe", "final_tf", "generate", "parent_inputs"):
        setattr(module, name, denied)
    actual_manifest, cls, actual_rows, actual_parents, actual_raw, actual_orders = module.validate_inputs(fresh / "manifest.json", args.approved_manifest_sha)
    assert actual_manifest == manifest and actual_rows == rows and not forbidden and not blocked
    for key, state in parents.items():
        assert actual_raw[key] == raw[f"initial/seed{key}.npz"] and np.array_equal(actual_orders[key], orders[key])
        assert state.keys() == actual_parents[key].keys()
        assert all(value.dtype == actual_parents[key][name].dtype and np.array_equal(value, actual_parents[key][name]) for name, value in state.items())
    enabled = False
    assert before == {path.name: sha(path.read_bytes()) for path in fresh.iterdir()}
    engineering = read(args.engineering)
    assert engineering["status"] == "PASS" and engineering["source_hashes"] == pins
    assert engineering["formal_forward_calls"] == engineering["new_parent_optimizer_calls"] == 0
    for name, pin in pins.items():
        assert sha((code / name).read_bytes()) == pin
    assert sha(manifest_path.read_bytes()) == args.approved_manifest_sha and sha(zip_path.read_bytes()) == manifest["archive"]["sha256"]
    result = {"status": "passed", "round_id": "AE1-MIXED-FLIP-20261113", "manifest_sha256": args.approved_manifest_sha, "inputs_zip_sha256": manifest["archive"]["sha256"], "source_hashes": pins, "parent_result_commit": PARENT_HEAD, "parent_publication_manifest_sha256": PUBLICATION_SHA, "parent_publication_manifest_Git_blob": PUBLICATION_BLOB, "public_parent_archives_independently_byte_blob_member_CRC_checked": archive_evidence, "full_parent_checkpoints_exact_verified": 3, "parent_t": {str(seed): t for seed, t in PARENT_T.items()}, "portable_archive_entries": 13, "fresh_bundle_real_validator_passed_original_workspace_reads_blocked": True, "fresh_input_files_before_after_exact": 6, "old_Echo_QA_bitidentical": 1800, "mixed_questions": 2700, "consistent_unique_teacher_prefixes": 24300, "literal_Flip_input0_1_answers_preserved": ["111110S", "111100S"], "target_label_counts_per_epoch": dict(label_counts), "frozen_exact_RNG_full_target_permutations": 120, "source_review": {"all3_parent_baseline_integrity_before_any_new_optimizer": True, "baseline_failure_whole_batch_aborts0new_updates_no_repair": True, "baseline_only_inference_counters_change_and_streak_starts0": True, "trained_parent_Adam_t_m_v_birth_RNG_fullstate_continued": True, "parent_old_costs_separate_all_new_counts_are_deltas": True, "only_raw_Q_plus_true_prefix_for_training_free_uses_own_prefix": True, "Flip5_information_bits_plus_tail0_literal_control_pattern_answers": True, "only_external_S_stops_no_answer_length_cutoff_or_forced_STOP": True, "all3_classes900_exact_twice_or40cap_no_extension_selection": True, "only_seed101_full_baseline_and_mixed_epoch_replay": True, "all_primary_and_replay_before_final_TF_no_hidden_rawloss_claim": True}, "engineering_separate": {key: engineering[key] for key in ("tests", "synthetic_native_updates", "synthetic_native_forward_calls", "synthetic_mock_targets", "synthetic_mock_probes")}, "material_findings_remaining": [], "interpretation_limits": ["Continuation of3 existing models on the same exposed900-payload bank, no fresh-student or independent-new-dataset claim.", "Equal question counts have unequal6300/11700/6300 CE weighting.", "No control isolates Flip causality, unseen-bank/arbitrary-r/length generalization or internal control execution."], "required_root_before_formal": "Verify this exact source/input freeze in a public Git preregistration with byte readback, then one fresh formal command; no baseline NN before that authorization.", "reviewer_model_forward_calls": 0, "reviewer_optimizer_calls": 0, "reviewer_formal_students": 0, "external_model_calls": 0}
    with (HERE / "pre-run.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(canonical({"status": "passed", "manifest_sha256": args.approved_manifest_sha, "parent_checkpoints": 3, "archive_entries": 13, "target_permutations": 120, "optimizer_and_forward_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--approved-manifest-sha", required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--engineering", type=Path, required=True)
    parser.add_argument("--parent-root", type=Path, required=True)
    main(parser.parse_args())
