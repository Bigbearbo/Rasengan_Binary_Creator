"""One bounded portable native-validation check; all learner NN entry points are blocked."""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import zipfile

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
import numpy as np

PINS = {
    "run_stability.py": "2e11066e065103f6d8c211718fc4a3271b79876b52af00f49241fe79577cf6e3",
    "protocol.json": "8f4452756a63d3665d85ec2b319d8d902a5038cca047223c5d32154b37499854",
    "test_stability.py": "2262e781c3e1c32e0dafe58d3af38bef8e1bbd082d90f33087bfa60c4c6b5486",
}
APPROVED = "1079366438d667f7bce2ac8fce983792b6c7bf935f4a200fb9eda4e9612e328c"
ZIP_SHA = "46f14f6e233ed6f6304c9c0a01779c653647c2f40ae60c57ab4e5d7661f0dc79"
FORBIDDEN_METHODS = {"forward", "loss_grad", "step", "lesson", "generate", "grow"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    review = args.review.resolve()
    review.mkdir(parents=True, exist_ok=True)
    fresh = review / "portable-bundle"
    fresh.mkdir(exist_ok=False)
    code, prereg = fresh / "tool", fresh / "prereg"
    code.mkdir()
    prereg.mkdir()
    originals = {name: args.code / name for name in PINS}
    originals.update({"manifest.json": args.prereg / "manifest.json", "inputs.zip": args.prereg / "inputs.zip"})
    before = {name: sha(path.read_bytes()) for name, path in originals.items()}
    assert all(before[name] == value for name, value in PINS.items())
    assert before["manifest.json"] == APPROVED and before["inputs.zip"] == ZIP_SHA
    assert originals["inputs.zip"].stat().st_size == 1272100
    for name, path in originals.items():
        shutil.copyfile(path, (code if name in PINS else prereg) / name)
    copied = {name: (code if name in PINS else prereg) / name for name in originals}
    assert {name: sha(path.read_bytes()) for name, path in copied.items()} == before
    engineering = read(args.prereg.parent / "engineering/checks.json")
    assert engineering["status"] == "passed" and engineering["tests"] == 4
    assert engineering["source_hashes"] == PINS
    assert engineering["synthetic_optimizer_updates"] == engineering["synthetic_forward_calls"] == 3
    assert engineering["trained_parent_forward_calls"] == engineering["new_parent_optimizer_calls"] == 0
    workspace = args.code.resolve().parents[1]
    denied, accepted_reads, NN_attempts = [], set(), []
    guard_active = [True]
    testing_guard = [False]

    def audit(event, values):
        if event != "open" or not guard_active[0] or isinstance(values[0], int):
            return
        try:
            path = Path(os.fsdecode(values[0])).resolve()
        except (TypeError, ValueError, OSError):
            return
        if path.is_relative_to(workspace) and not path.is_relative_to(fresh):
            denied.append({"relative_path": path.relative_to(workspace).as_posix(), "intentional_guard_probe": testing_guard[0]})
            raise PermissionError("Original workspace read/write denied during portable validation")
        if path.is_relative_to(fresh):
            accepted_reads.add(path.relative_to(fresh).as_posix())

    sys.addaudithook(audit)
    testing_guard[0] = True
    try:
        originals["protocol.json"].read_bytes()
        raise AssertionError("Original-read guard did not reject its positive control")
    except PermissionError:
        pass
    finally:
        testing_guard[0] = False
    spec = importlib.util.spec_from_file_location("portable_f2_stability", code / "run_stability.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    native_model_classes = module.model_classes
    protected_classes = []

    def blocked(*unused_args, **unused_kwargs):
        NN_attempts.append("forbidden learner method")
        raise AssertionError("NN inference/optimizer/growth is forbidden in this pre-run check")

    def protected(content):
        result = native_model_classes(content)
        for cls in result[:2]:
            for name in FORBIDDEN_METHODS:
                setattr(cls, name, blocked)
            protected_classes.append(cls)
        return result

    module.model_classes = protected
    called_methods = []

    def profile(frame, event, arg):
        if event == "call" and frame.f_code.co_filename == "<P030-single-eta-intervention>" and frame.f_code.co_name in FORBIDDEN_METHODS:
            called_methods.append(frame.f_code.co_name)
            raise AssertionError("Unexpected native NN method entered")

    sys.setprofile(profile)
    started = time.perf_counter()
    try:
        manifest, contents, data = module.validate_inputs(prereg / "manifest.json", APPROVED)
        validation_seconds = time.perf_counter() - started
        f2, _, _, rows, starts, controls, orders, parent_info, ast_proof, a, b = data
        assert len(protected_classes) == 2
        assert a.count("Constant(value=0.003)") == 1
        assert a.replace("Constant(value=0.003)", "Constant(value=0.001)", 1) == b
        assert ast_proof["entire_AST_equal_after_reversing_one_leaf"]
        assert len(contents) == 36
        member_types = {"NPZ": 0, "NPY": 0}
        for name, raw in contents.items():
            assert not name.startswith(("/", "\\")) and ".." not in Path(name).parts
            if name.endswith(".npz"):
                member_types["NPZ"] += 1
                with np.load(io.BytesIO(raw), allow_pickle=False) as z:
                    assert len(z.files) == 25
                    for key in z.files:
                        arr = z[key]
                        if arr.dtype.kind in "fc":
                            assert np.isfinite(arr).all()
            elif name.endswith(".npy"):
                member_types["NPY"] += 1
                array = np.load(io.BytesIO(raw), allow_pickle=False)
                assert array.dtype.str == "<u2" and array.shape == (36000, 2)
        expected_shapes = [(160, 64), (64,), (64, 3), (3,)]
        state_info = {}
        for seed in (101, 202, 303):
            key = str(seed)
            for state in (starts[key], controls[key]):
                assert len(state) == 25
                for i, shape in enumerate(expected_shapes):
                    for group in ("p", "m", "v"):
                        assert state[f"{group}{i}"].shape == shape and state[f"{group}{i}"].dtype == np.float32
                    assert state[f"birth{i}"].shape == shape and state[f"birth{i}"].dtype == np.int64
                json.loads(str(state["growth_rng"]))
                json.loads(str(state["meta_events"]))
            assert int(controls[key]["t"]) - int(starts[key]["t"]) == 36000
            assert int(controls[key]["meta_train_macs"]) - int(starts[key]["meta_train_macs"]) == 758016000
            pool = np.asarray([(offset + pair, pos) for pair in range(900) for offset in (0, 900, 1800, 2700)
                               for pos in range(7 if offset in (0, 1800) else 13)], dtype="<u2")
            to_code = lambda x: x[:, 0].astype(np.int64) * 16 + x[:, 1]
            assert np.array_equal(np.sort(to_code(pool)), np.sort(to_code(orders[key])))
            state_info[key] = {"start_t": int(starts[key]["t"]), "end_t": int(controls[key]["t"]),
                               "fields": 25, "fullstate_restore_exact_in_native_validator": True,
                               "historical_lost": parent_info[key]["historical_control_lost"],
                               "order_SHA256": sha(contents[f"orders/seed{seed}.npy"])}
        assert [state_info[str(s)]["historical_lost"] for s in (101, 202, 303)] == [7, 5, 52]
        assert not NN_attempts and not called_methods
        assert len(denied) == 1 and denied[0]["intentional_guard_probe"]
        fresh_after = {name: sha(path.read_bytes()) for name, path in copied.items()}
        assert fresh_after == before
    finally:
        sys.setprofile(None)
        guard_active[0] = False
    assert {name: sha(path.read_bytes()) for name, path in originals.items()} == before
    report = {
        "schema": "f2-stability-independent-pre-run-v1", "status": "passed", "date": "2026-11-13",
        "manifest_sha256": APPROVED, "source_hashes": PINS, "inputs_zip_sha256": ZIP_SHA,
        "review_source_sha256": sha(Path(__file__).read_bytes()),
        "portable_native_validation": {"actual_call": "validate_inputs(fresh_manifest, approved_hash)",
            "fresh_bundle": "portable-bundle/", "original_workspace_reads_denied": True,
            "guard_positive_control_rejected": True, "validator_original_workspace_read_attempts": 0,
            "actual_relative_files_read": sorted(accepted_reads), "five_portable_inputs_SHA_unchanged": fresh_after,
            "original_five_source_inputs_SHA_unchanged": True, "validation_seconds": validation_seconds,
            "Model_NN_methods_patched_to_reject": sorted(FORBIDDEN_METHODS), "NN_method_attempts": 0},
        "inputs": {"ZIP_members": len(contents), "finite_array_members": member_types, "full_state_fields": 25,
                   "parents_and_control": state_info, "exact_order_slices_verified_by_native_validator": True,
                   "public_member_SHA_Gitblob_CRC_and_receipt_mapping_verified": True},
        "AST_change": ast_proof,
        "author_engineering": {"source_pins_match": True, "tests_passed": 4, "synthetic_updates": 3,
                               "synthetic_forward_calls": 3, "parent_forward_updates": 0,
                               "not_repeated_by_reviewer": True},
        "static_review": [
            "execute performs all3 baselines before its first train_one call; baseline failure retains evidence and exits with0newupdates.",
            "Baseline compares complete archived generation and all4class900scores; only inference counters may change, all learning/RNG/events/train counters exact.",
            "Train_one consumes one exact36000target order, visible Q+correct priorA only, original AST step except eta001, no GPU/JIT/grow/accumulation.",
            "Training counters are deltas from selected starts;108000 updates/2274048000MAC total; baseline/newprobe/finalTF separately recorded.",
            "All3primary complete before finalTF; lastfree reused. Historicalcontrol state/generation/record are copies of public evidence, no oldcontrol optimizer call.",
            "Primary condition all3strictly fewer lost; ties fail directional hypothesis; all seed/class QID categories retained; no outcome-driven extension.",
            "Formalreplay empty/notplanned. Tracepred/loss digest is recorded evidence, not an independently reconstructed gradient/optimizer trajectory."
        ],
        "reviewer_forward_calls": 0, "reviewer_optimizer_updates": 0, "reviewer_external_calls": 0,
        "new_outcomes_observed": False, "blocking_findings": [],
        "postrun_requirements": [
            "Explicit root exit0/receipt GO before trained forward; verify exact metadata paths and receipt/session/commit first.",
            "Pure independent NumPy forward for3baselines+3new endpoints+3historical controls, new finalTF108000targets; preserve incremental cost/proofs.",
            "Hash complete source/manifest/inputs/science/receipt before and after audit; formal driver endguard checks core/manifest but does not rehash inputsZIP there.",
            "Do not claim optimizer replay or reuse old control work as newly trained students; distinguish posthoc firstfull-start selection and one-epoch local inference."
        ],
        "initial_protocol_helper_error_record": "protocol-helper-attempt-01.json",
        "limits": "Pre-run acceptance only. No trained inference or optimizer work performed by reviewer; root still owns Git prereg and sole formal authorization."
    }
    with (review / "pre-run.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "passed", "manifest_sha256": APPROVED, "portable_members": len(contents),
                      "NPZ": member_types["NPZ"], "NPY": member_types["NPY"], "newNN": 0,
                      "source": sha(Path(__file__).read_bytes()), "report": sha((review / "pre-run.json").read_bytes())}))


if __name__ == "__main__":
    main()
