"""Independent AE1 frozen-bank/order and portable-input gate, zero NN calls."""
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

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


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
    manifest = read(manifest_path)
    freeze = read(prereg / "source-freeze.json")
    pins = manifest["source_hashes"]
    assert set(pins) == {"run_curriculum.py", "protocol.json", "test_curriculum.py"}
    assert freeze["manifest_sha256"] == args.approved_manifest_sha and freeze["source_hashes"] == pins
    for name, pin in pins.items():
        assert sha((code / name).read_bytes()) == pin
    archive_path = prereg / "inputs.zip"
    assert manifest["archive"]["file"] == "inputs.zip"
    assert sha(archive_path.read_bytes()) == manifest["archive"]["sha256"] == freeze["inputs_zip_sha256"]
    assert archive_path.stat().st_size == manifest["archive"]["bytes"] == freeze["inputs_zip_bytes"]
    names = {"source/p030_binary_continual.py", "plan.json", "payloads.json", "questions.json"}
    names |= {f"initial/seed{seed}.npz" for seed in (101, 202, 303)}
    names |= {f"orders/seed{seed}-{phase}.npy" for seed in (101, 202, 303) for phase in ("r1", "r12")}
    with zipfile.ZipFile(archive_path) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) == 13
        assert set(archive.namelist()) == names == set(manifest["files"])
        raw = {name: archive.read(name) for name in names}
    for name, value in raw.items():
        assert {"bytes": len(value), "sha256": sha(value)} == manifest["files"][name]
    assert raw["plan.json"] == (code / "protocol.json").read_bytes()
    protocol = manifest["protocol"]
    assert json.loads(raw["plan.json"]) == protocol
    assert protocol["seeds"] == [101, 202, 303] and protocol["replay_seeds"] == [101]
    assert protocol["model"] == {"L": 80, "H": 64, "parameters": 10499}
    assert [(p["name"], p["taught_r"], p["questions_per_epoch"], p["targets_per_epoch"], p["schedule_seed_offset"], p["max_epochs"]) for p in protocol["phases"]] == [("r1", [1], 900, 6300, 332000, 40), ("r12", [1, 2], 1800, 18000, 333000, 40)]
    assert manifest["formal_optimizer_calls_before_freeze"] == manifest["formal_forward_calls_before_freeze"] == 0
    extra = np.random.default_rng(331000).integers(0, 30, size=(900, 2))
    bank = [[pair // 30, pair % 30, int(extra[pair, 0]), int(extra[pair, 1])] for pair in range(900)]
    assert json.loads(raw["payloads.json"]) == bank
    assert len(set(map(tuple, bank))) == 900
    word = lambda value: format(value, "05b") + "0"
    questions = []
    teacher = {}
    label_counts = {"r1": Counter(), "r12": Counter()}
    for r in (1, 2):
        for pair, payload in enumerate(bank):
            q = "01" + "010" + format(r, "03b") + "0" + "".join(word(value) for value in payload) + "111100"
            a = "".join(word(value) for value in payload[:r])
            assert len(q) == 39 and len(a + "S") == 6 * r + 1 and len(q + a) == (45 if r == 1 else 51)
            assert all(0 <= value < 30 and word(value) != "111100" for value in payload)
            questions.append({"question_id": (r - 1) * 900 + pair, "pair_id": pair, "r": r, "payload": payload, "Q": q, "A": a})
            for position, label in enumerate(a + "S"):
                prefix = q + a[:position]
                assert prefix not in teacher
                teacher[prefix] = label
                label_counts["r12"][label] += 1
                if r == 1:
                    label_counts["r1"][label] += 1
    assert len(teacher) == 18000 and len({row["Q"] for row in questions}) == 1800
    assert dict(label_counts["r1"]) == {"0": 3270, "S": 900, "1": 2130}
    assert dict(label_counts["r12"]) == {"0": 9810, "S": 1800, "1": 6390}
    assert json.loads(raw["questions.json"]) == questions
    counts = [{str(value): sum(payload[position] == value for payload in bank) for value in range(30)} for position in range(4)]
    assert all(value == 30 for position in (0, 1) for value in counts[position].values())
    expected_data = {"payloads": 900, "questions": 1800, "first_two_combinations": 900, "possible_four_word_payloads": 810000, "word_position_counts": counts, "consistent_unique_teacher_prefixes": 18000, "phase_targets": {"r1": 6300, "r12": 18000}}
    assert manifest["data_checks"] == expected_data
    target_pools = {name: np.asarray([((r - 1) * 900 + pair, position) for pair in range(900) for r in taught for position in range(6 * r + 1)], dtype="<u2") for name, taught in (("r1", (1,)), ("r12", (1, 2)))}
    initials, courses = {}, {}
    for seed in (101, 202, 303):
        with np.load(io.BytesIO(raw[f"initial/seed{seed}.npz"]), allow_pickle=False) as archive:
            state = {name: archive[name].copy() for name in archive.files}
        assert len(state) == 25 and state_sha(state) == manifest["initial_states"][str(seed)]["full_state_sha256"]
        assert (int(state["L"]), int(state["H"]), int(state["meta_seed"])) == (80, 64, seed)
        assert all(int(state[name]) == 0 for name in ("t", "meta_train_macs", "meta_inference_calls", "meta_inference_macs"))
        assert str(state["meta_events"]) == "[]"
        for label in ("p", "m", "v", "birth"):
            for index, shape in enumerate(((160, 64), (64,), (64, 3), (3,))):
                value = state[f"{label}{index}"]
                assert value.shape == shape and value.dtype == (np.int64 if label == "birth" else np.float32)
                assert np.isfinite(value).all()
                if label != "p":
                    assert not np.any(value)
        rng = np.random.default_rng(seed)
        assert np.array_equal(state["p0"], rng.normal(0, .2, (160, 64)).astype(np.float32))
        assert np.array_equal(state["p2"], rng.normal(0, .15, (64, 3)).astype(np.float32))
        assert not np.any(state["p1"]) and not np.any(state["p3"])
        assert sum(state[f"{label}{index}"].nbytes for label in ("p", "m", "v", "birth") for index in range(4)) == 209980
        initials[str(seed)] = state
        for phase in protocol["phases"]:
            name = phase["name"]
            key = f"seed{seed}-{name}"
            rng = np.random.default_rng(seed + phase["schedule_seed_offset"])
            pool = target_pools[name]
            expected = np.stack([pool[rng.permutation(len(pool))] for _ in range(40)])
            actual = np.load(io.BytesIO(raw[f"orders/{key}.npy"]), allow_pickle=False)
            assert actual.shape == (40, phase["targets_per_epoch"], 2) and actual.dtype.str == "<u2"
            assert np.array_equal(actual, expected)
            assert manifest["schedules"][key]["shape"] == list(actual.shape)
            assert manifest["schedules"][key]["final_schedule_RNG"] == rng.bit_generator.state
            assert manifest["schedules"][key]["schedule_seed"] == seed + phase["schedule_seed_offset"]
            courses[key] = actual
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
    spec = importlib.util.spec_from_file_location("relocated_curriculum_gate", fresh / "run_curriculum.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    native = module.source_model

    def denied(*values, **kwargs):
        forbidden.append(1)
        raise AssertionError("Model optimizer/inference forbidden in pre-run gate")

    def guarded(content):
        cls = native(content)
        for name in ("step", "lesson", "loss_grad", "forward", "generate", "grow"):
            setattr(cls, name, denied)
        return cls

    module.source_model = guarded
    for name in ("execute", "run_seed", "update_target", "probe", "final_tf", "generate"):
        setattr(module, name, denied)
    actual_manifest, cls, actual_questions, actual_initials, actual_courses = module.validate_inputs(fresh / "manifest.json", args.approved_manifest_sha)
    assert actual_manifest == manifest and actual_questions == questions and not blocked and not forbidden
    for key, actual in actual_courses.items():
        assert np.array_equal(actual, courses[key])
    for key, state in initials.items():
        assert state.keys() == actual_initials[key].keys()
        assert all(value.dtype == actual_initials[key][name].dtype and np.array_equal(value, actual_initials[key][name]) for name, value in state.items())
    enabled = False
    assert before == {path.name: sha(path.read_bytes()) for path in fresh.iterdir()}
    engineering = read(args.engineering)
    assert engineering["status"] == "PASS" and engineering["source_hashes"] == pins
    assert engineering["formal_optimizer_calls"] == engineering["formal_forward_calls"] == 0
    for name, pin in pins.items():
        assert sha((code / name).read_bytes()) == pin
    assert sha(manifest_path.read_bytes()) == args.approved_manifest_sha
    assert sha(archive_path.read_bytes()) == manifest["archive"]["sha256"]
    result = {
        "status": "passed",
        "round_id": "AE1-PARAMETER-EXEC-20261113",
        "manifest_sha256": args.approved_manifest_sha,
        "inputs_zip_sha256": manifest["archive"]["sha256"],
        "source_hashes": pins,
        "portable_archive_entries": 13,
        "fresh_bundle_real_validator_passed_original_workspace_reads_blocked": True,
        "fresh_input_files_before_after_exact": 6,
        "full_initial_states_independently_checked": 3,
        "frozen_stage_schedules_independently_checked": 6,
        "full_target_permutations_independently_checked": 240,
        "payloads": 900,
        "questions_r1_r2": 1800,
        "first_two_word_combinations": 900,
        "possible_four_word_inputs": 810000,
        "unique_consistent_teacher_prefixes": 18000,
        "teacher_label_counts_by_phase": {name: dict(value) for name, value in label_counts.items()},
        "source_review": {
            "original_P030_Model_AST_and_Adam_unmodified": True,
            "fresh_L80_H64_10499params_no_previous_weights_or_growth": True,
            "original_binary_Q_plus_true_A_prefix_only_in_training": True,
            "globally_shuffled_true_prefix_targets_not_contiguous_lessons": True,
            "fixed_cap32_free_generation_without_r_or_answer_length_oracle": True,
            "phase2_entry_fullstate_equals_phase1_after_probe_exit": True,
            "Adam_t_m_v_birth_RNG_and_inference_counters_carry": True,
            "phase_local_costs_use_entry_baselines_and_global_totals_preserved": True,
            "phase1_cap_failure_stops_student_and_does_not_evaluate_r2": True,
            "phase2_requires_both900_exact_including_STOP_twice": True,
            "all_three_seeds_retained_no_extra_epochs_or_seed_selection": True,
            "only_seed101_replay_independently_rederives_branches_streaks_stops": True,
            "final_TF_only_actual_taught_set_after_all_primary_and_replay": True,
            "trace_digest_scope_does_not_claim_unsaved_intermediate_statehashes": True,
        },
        "engineering_separate": {
            "tests": engineering["tests"],
            "synthetic_native_optimizer_updates": engineering["synthetic_native_optimizer_updates"],
            "synthetic_native_inference_calls": engineering["synthetic_native_inference_calls"],
            "synthetic_mock_targets": engineering["synthetic_mock_targets"],
            "synthetic_mock_probes": engineering["synthetic_mock_probes"],
        },
        "interpretation_limits": [
            "Finite fixed-bank curriculum fit/retention; no heldout, r3/r4 or length extrapolation inference.",
            "One sampled suffix pair per first pair covers900 of810000 possible four-word payloads.",
            "No joint-training control, hence no isolated curriculum benefit.",
            "Equal stage2 question counts carry6300 r1 versus11700 r2 CE updates per epoch.",
            "Finite r1/r2 success cannot uniquely identify a general count-following copy algorithm.",
        ],
        "material_findings_remaining": [],
        "required_root_before_formal": "Verify exact public Git preregistration raw bytes and this frozen manifest/source, then one formal command into a new output directory.",
        "reviewer_optimizer_calls": 0,
        "reviewer_model_forward_calls": 0,
        "reviewer_formal_students": 0,
        "external_model_calls": 0,
    }
    with (HERE / "pre-run.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(canonical({"status": "passed", "manifest_sha256": args.approved_manifest_sha, "archive_entries": 13, "target_permutations": 240, "optimizer_and_forward_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--approved-manifest-sha", required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--engineering", type=Path, required=True)
    main(parser.parse_args())
