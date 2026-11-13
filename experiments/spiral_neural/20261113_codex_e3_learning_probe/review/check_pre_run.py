"""Bounded independent portable validation. No neural/optimizer methods may run."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
import numpy as np

PINS = {"run_probe.py": "2e4033c6b47b1db84a5fa01cd9344622183a22b50178e2ee2f82331781d9b196",
        "protocol.json": "b59735c8933668fbe1ce5b630c01e1c4ffa5b4647ab77c8c786608ca7aaedac8",
        "test_probe.py": "8bf2d56b3b423e842ac1301e30a507ca9bd8c17860e7e9c0bdd6f54883b13a31"}
APPROVED = "5e2b3e6eb90c20a27c12ff9d743c8f0ab65a759fff4d561c6d156b535497c8bc"
ZIP_SHA = "b658716bd3e4bba693ab33c26e429f406fc326fe220bfa1679cb5fb446ff4efc"
NN = {"forward", "loss_grad", "step", "lesson", "generate", "grow"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--code", type=Path, required=True)
    p.add_argument("--prereg", type=Path, required=True)
    p.add_argument("--review", type=Path, required=True)
    a = p.parse_args()
    review = a.review.resolve()
    originals = {name: a.code / name for name in PINS}
    originals.update({name: a.prereg / name for name in ("manifest.json", "inputs.zip")})
    before = {name: sha(path) for name, path in originals.items()}
    assert all(before[name] == pin for name, pin in PINS.items())
    assert before["manifest.json"] == APPROVED and before["inputs.zip"] == ZIP_SHA
    assert originals["inputs.zip"].stat().st_size == 926204
    engineering = json.loads((a.prereg.parent / "engineering/checks.json").read_text(encoding="utf-8"))
    assert engineering["status"] == "passed" and engineering["tests"] == 5 and engineering["source_hashes"] == PINS
    assert engineering["synthetic_optimizer_updates"] == engineering["synthetic_forward_calls"] == 3
    assert engineering["trained_model_forward_calls"] == engineering["trained_parent_optimizer_calls"] == 0
    assert engineering["mock_inference_counter_increments_not_actual_forwards"] == 210600
    fresh = review / "portable-bundle"
    fresh.mkdir(exist_ok=False)
    (fresh / "tool").mkdir()
    (fresh / "prereg").mkdir()
    copied = {}
    for name, path in originals.items():
        target = fresh / ("tool" if name in PINS else "prereg") / name
        shutil.copyfile(path, target)
        copied[name] = target
    assert {name: sha(path) for name, path in copied.items()} == before
    workspace = a.code.resolve().parents[1]
    active, positive = [True], [False]
    denied, reads, nn_attempts, profiled = [], set(), [], []

    def audit(event, values):
        if event != "open" or not active[0] or isinstance(values[0], int):
            return
        try:
            path = Path(os.fsdecode(values[0])).resolve()
        except (TypeError, ValueError, OSError):
            return
        if path.is_relative_to(workspace) and not path.is_relative_to(fresh):
            denied.append(positive[0])
            raise PermissionError("Original workspace dependency forbidden")
        if path.is_relative_to(fresh):
            reads.add(path.relative_to(fresh).as_posix())

    sys.addaudithook(audit)
    positive[0] = True
    try:
        originals["protocol.json"].read_bytes()
        raise AssertionError("Original read guard did not reject positive control")
    except PermissionError:
        pass
    positive[0] = False
    spec = importlib.util.spec_from_file_location("independent_portable_E3", copied["run_probe.py"])
    r = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r)
    factory, protected = r.model_classes, []

    def reject(*args, **kwargs):
        nn_attempts.append("NN entry attempted")
        raise AssertionError("No NN/optimizer permitted in portable gate")

    def guard_classes(raw):
        result = factory(raw)
        for cls in result[0].values():
            for method in NN:
                setattr(cls, method, reject)
            protected.append(cls)
        return result

    def profile(frame, event, arg):
        if event == "call" and frame.f_code.co_filename == "<P030-single-eta-arm>" and frame.f_code.co_name in NN:
            profiled.append(frame.f_code.co_name)
            raise AssertionError("Native NN entered")

    r.model_classes = guard_classes
    sys.setprofile(profile)
    start = time.perf_counter()
    try:
        manifest, contents, data = r.validate_inputs(copied["manifest.json"], APPROVED)
        seconds = time.perf_counter() - start
        h, classes, rows, parents, orders, parent_info, proof, original, low, checks = data
        assert len(protected) == 2 and set(classes) == {"eta001", "eta003"}
        assert original.count("Constant(value=0.003)") == 1
        assert original.replace("Constant(value=0.003)", "Constant(value=0.001)", 1) == low
        assert len(contents) == 22 and checks["questions"] == 4500
        assert checks["teacher_targets"] == checks["unique_teacher_prefixes"] == 53100
        npz = npy = 0
        for name, raw in contents.items():
            assert not name.startswith(("/", "\\")) and ".." not in Path(name).parts
            if name.endswith(".npz"):
                npz += 1
                with np.load(io.BytesIO(raw), allow_pickle=False) as z:
                    assert len(z.files) == 25
                    assert all(np.isfinite(z[key]).all() for key in z.files if z[key].dtype.kind in "fc")
            elif name.endswith(".npy"):
                npy += 1
                order = np.load(io.BytesIO(raw), allow_pickle=False)
                assert order.shape == (53100, 2) and order.dtype.str == "<u2"
        assert (npz, npy) == (3, 3)
        state_info = {}
        for seed, t in ((101, 1017000), (202, 1228500), (303, 1161900)):
            state = parents[str(seed)]
            assert len(state) == 25 and int(state["t"]) == t
            for i, shape in enumerate(((160, 64), (64,), (64, 3), (3,))):
                for group in ("p", "m", "v"):
                    assert state[f"{group}{i}"].shape == shape and state[f"{group}{i}"].dtype == np.float32
                assert state[f"birth{i}"].shape == shape and state[f"birth{i}"].dtype == np.int64
            json.loads(str(state["growth_rng"]))
            json.loads(str(state["meta_events"]))
            pool = np.asarray([(offset + pair, position) for pair in range(900) for offset, count in ((0, 7), (900, 13), (1800, 7), (2700, 13), (3600, 19)) for position in range(count)], dtype="<u2")
            expected = pool[np.random.default_rng(seed + 666000).permutation(53100)]
            assert np.array_equal(orders[str(seed)], expected)
            state_info[str(seed)] = {"parent_t": t, "parent_raw_SHA256": parent_info[str(seed)]["raw_sha256"],
                                     "parent_full_state_SHA256": parent_info[str(seed)]["full_state_sha256"],
                                     "orders_exact_independent_pool_and_seed": True, "full_state_fields": 25}
        assert not nn_attempts and not profiled and denied == [True]
        assert {name: sha(path) for name, path in copied.items()} == before
    finally:
        sys.setprofile(None)
        active[0] = False
    assert {name: sha(path) for name, path in originals.items()} == before
    report = {"schema": "e3-learning-probe-independent-pre-run-v1", "status": "passed", "date": "2026-11-13",
        "manifest_sha256": APPROVED, "source_hashes": PINS, "inputs_zip_sha256": ZIP_SHA, "review_source_sha256": sha(Path(__file__)),
        "portable": {"native_validate_inputs_actually_called": True, "original_workspace_reads_denied": True,
                     "original_dependency_read_attempts": 0, "guard_positive_control_rejected": True,
                     "fresh_files_read": sorted(reads), "five_inputs_before_after_SHA256": before,
                     "original_files_unchanged": True, "validation_seconds": seconds,
                     "Model_NN_methods_patched": sorted(NN), "NN_entry_attempts": 0},
        "inputs": {"ZIP_members": 22, "finite_NPZ": 3, "NPY_orders": 3, "parents": state_info, "data_checks": checks,
                   "publicSHA_Gitblob_CRC_receipt_lineage": "native validator complete pass"},
        "AST_change": proof,
        "author_engineering": {"source_pins_match": True, "tests_passed": 5, "actual_tiny_updates": 3, "actual_tiny_forward_calls": 3,
                               "mock_counter_increments_not_NN": 210600, "not_repeated_by_reviewer": True},
        "static_review": [
            "All3 old3600generation integrity gates precede anyE3cold oroptimizer; integrationfailure abort0updates.",
            "Each seed shared oldfree+E3coldfree+coldTF is measured once; both arms restore identical25field sharedbaseline-endstate. Physical baseline summed3records, not6logicalancestry counters.",
            "Old3600Q/A dictionaries exact; only900 Echo010/r3 appended. Native and independent pool/order yield53100targets with17100E3 targets and maxcorrectSTOPprefix57.",
            "Each arm consumes the same seed order once, oneAdam step pertarget, no minibatching/grow/GPU/JIT; total318600updates/6708441600trainingMAC, zero optimizer replay.",
            "All6primary finish before finalTF. Greedy uses only own outputs/cap32/L80guard; no oracle answerlength cutoff. TF dynamic classes/word3 is separate from free.",
            "Both arms use the same feasibility formula. Low primary is all3strict conjunction, not rate superiority; ceiling interpretation never changes budget or selection.",
            "Dynamic perword/info/tail/STOP/firsterror/termination and QID churn preserve word3/missing-token denominators; i0 uses explicit None check."
        ],
        "reviewer_trained_forward_calls": 0, "reviewer_optimizer_updates": 0, "reviewer_external_calls": 0,
        "new_scores_observed": False, "blocking_findings": [],
        "gate_scope": "Final source/input portable acceptance only; coordinator still owns Git prereg and sole formal execution.",
        "postaudit_scope": "Only after root actualexit0+explicitGO: reuse pinned old pureForward/readoutdefs;3sharedbaselines includingE3TF,6endpoints/finalTF. No optimizer/fulltraining replay or extra cases."}
    with (review / "pre-run.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "passed", "manifest_sha256": APPROVED, "members": 22, "NPZ": 3, "NPY": 3, "NN": 0,
                      "source_sha256": sha(Path(__file__)), "report_sha256": sha(review / "pre-run.json")}))


if __name__ == "__main__":
    main()
