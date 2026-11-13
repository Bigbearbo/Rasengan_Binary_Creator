"""Independent AE1 curriculum post-run audit, literal NumPy forward only.

No learner/driver imports, optimizer, extra r, or new student. Coordinator exit0,
session and preregistration arguments are mandatory. All paths and result schemas
are checked before any trained forward; proofs/cost persist after each epoch.
"""
import argparse
import ast
from collections import Counter
import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import time
import zipfile

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

APPROVED = "dcf3ea17d1f5a179ccaa37b5f544f630ad274afdfa7b56ab93684d1a9344fe60"
ZIP_SHA = "8eb05d5649c5568abf5da18a5b51ffa6c5a1be1e721481b1960d2e27cebe5efe"
DRIVER = "b95c9a96f096624c2d01ef6dcd1782070d1d3f172cfbc4a60b097754047895a6"
PREREG = "966297559b4f4dedc4b8cf655258d4036cc21cc8"
FORMAL_SESSION = 7462
SEEDS = (101, 202, 303)
PHASES = ("r1", "r12")
TAUGHT = {"r1": (1,), "r12": (1, 2)}
TARGETS = {"r1": 6300, "r12": 18000}
TRAIN_MAC, FORWARD_MAC = 21056, 10432
HERE = Path(__file__).resolve().parent
TRAIN_FIELDS = {"targets", "pre_update_prediction_correct", "CE_loss_sum", "CE_loss_mean", "canonical_target_trace_sha256"}
EPOCH_FIELDS = {"phase", "epoch", "global_updates", "phase_updates", "training_dense_MAC", "phase_training_dense_MAC", "training", "scores", "streak", "decision", "first_full_epoch", "stable_pass_epoch", "cumulative_question_exposures", "cumulative_question_exposures_by_r", "epoch_probe_inference_calls", "epoch_probe_inference_MAC", "phase_probe_inference_calls", "phase_probe_inference_MAC", "cumulative_probe_inference_calls", "cumulative_probe_inference_MAC", "full_state_sha256"}
PHASE_FIELDS = {"phase", "epochs", "decision", "first_full_epoch", "stable_pass_epoch", "entry_full_state_sha256", "exit_full_state_sha256", "target_updates", "question_exposures", "training_dense_MAC", "probe_inference_calls", "probe_inference_MAC", "final_scores"}
SUMMARY_FIELDS = {"seed", "phases", "phase_reached", "taught_r", "blocked_before_r2", "completed_curriculum", "training_updates", "training_dense_MAC", "question_exposures", "question_exposures_by_r", "probe_inference_calls", "probe_inference_MAC", "final_full_state_sha256", "p_m_v_birth_array_bytes"}
GEN_FIELDS = {"scores", "rows", "inference_calls", "inference_dense_MAC"}
GEN_ROW_FIELDS = {"question_id", "r", "pair_id", "tokens", "context_exhausted", "cap_exhausted", "whole_correct"}
TF_FIELDS = {"position", "prefix", "target", "prediction", "logits_01S", "probabilities_01S", "target_CE"}
QUESTION_FIELDS = {"question_id", "pair_id", "r", "payload", "Q", "A"}


def need(value, label):
    if not value:
        raise AssertionError(label)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def finite(value):
    if isinstance(value, float):
        need(math.isfinite(value), "nonfinite JSON value")
    elif isinstance(value, dict):
        for item in value.values():
            finite(item)
    elif isinstance(value, list):
        for item in value:
            finite(item)


def parse(text):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    result = json.loads(text, object_pairs_hook=pairs)
    finite(result)
    return result


def read(path):
    return parse(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def equal(left, right, label):
    need(left == right, label + " differs")


def keys(value, expected, label):
    need(isinstance(value, dict) and set(value) == set(expected), label + " schema")


def integer(value, lower, upper, label):
    need(type(value) is int and lower <= value <= upper, label + " integer range")


def inventory(root):
    return {path.relative_to(root).as_posix(): {"bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(root.rglob("*")) if path.is_file()}


def state_sha(state):
    result = hashlib.sha256()
    for name, value in sorted(state.items()):
        result.update(canonical([name, value.dtype.str, list(value.shape)]).encode())
        result.update(value.tobytes(order="C"))
    return result.hexdigest()


def same_state(left, right, label):
    need(left.keys() == right.keys(), label + " keys")
    for name in left:
        a, b = left[name], right[name]
        need(a.dtype == b.dtype and a.shape == b.shape and np.array_equal(a, b), label + " " + name)


def load_state(raw, seed, updates, probe_calls):
    with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
        state = {name: archive[name].copy() for name in archive.files}
    expected = {f"{label}{index}" for label in ("p", "m", "v", "birth") for index in range(4)}
    expected |= {"t", "L", "H", "growth_rng", "meta_seed", "meta_events", "meta_train_macs", "meta_inference_macs", "meta_inference_calls"}
    need(set(state) == expected, "all25 complete state fields")
    for label in ("p", "m", "v", "birth"):
        for index, shape in enumerate(((160, 64), (64,), (64, 3), (3,))):
            value = state[f"{label}{index}"]
            need(value.shape == shape and value.dtype == (np.int64 if label == "birth" else np.float32), "state parameter/moment shape and dtype")
            need(bool(np.isfinite(value).all()), "finite state arrays")
            if label == "birth":
                need(not np.any(value), "no parameter growth/birth")
            if label == "v":
                need(bool((value >= 0).all()), "nonnegative Adam second moment")
    for name in ("t", "L", "H", "meta_seed", "meta_train_macs", "meta_inference_macs", "meta_inference_calls"):
        need(state[name].shape == () and state[name].dtype == np.int64, "integer scalar dtype")
    need((int(state["L"]), int(state["H"]), int(state["meta_seed"])) == (80, 64, seed), "state model identity")
    need(int(state["t"]) == updates and int(state["meta_train_macs"]) == updates * TRAIN_MAC, "state cumulative training counters")
    need(int(state["meta_inference_calls"]) == probe_calls and int(state["meta_inference_macs"]) == probe_calls * FORWARD_MAC, "state cumulative probe counters")
    equal(parse(str(state["growth_rng"])), np.random.default_rng(seed + 73000).bit_generator.state, "unchanged growth RNG")
    need(str(state["meta_events"]) == "[]", "no growth events")
    need(sum(state[f"{label}{index}"].nbytes for label in ("p", "m", "v", "birth") for index in range(4)) == 209980, "array bytes")
    for value in state.values():
        value.setflags(write=False)
    return state


def inputs(args):
    need(sha(args.manifest) == APPROVED, "approved manifest bytes")
    manifest = read(args.manifest)
    freeze = read(args.manifest.parent / "source-freeze.json")
    need(freeze["manifest_sha256"] == APPROVED and freeze["source_hashes"] == manifest["source_hashes"], "source freeze identity")
    need(manifest["source_hashes"]["run_curriculum.py"] == DRIVER, "approved driver source")
    for name, pin in manifest["source_hashes"].items():
        need(sha(args.code_root / name) == pin, "approved core bytes")
    need((platform.python_version(), np.__version__) == ("3.12.14", "2.3.5"), "audit runtime")
    need(manifest["runtime"]["python"] == platform.python_version() and manifest["runtime"]["numpy"] == np.__version__, "manifest runtime")
    archive_path = args.manifest.parent / manifest["archive"]["file"]
    need(sha(archive_path) == manifest["archive"]["sha256"] == ZIP_SHA, "frozen input ZIP")
    names = {"source/p030_binary_continual.py", "plan.json", "payloads.json", "questions.json"}
    names |= {f"initial/seed{seed}.npz" for seed in SEEDS}
    names |= {f"orders/seed{seed}-{phase}.npy" for seed in SEEDS for phase in PHASES}
    with zipfile.ZipFile(archive_path) as archive:
        need(len(archive.namelist()) == 13 and set(archive.namelist()) == names == set(manifest["files"]), "13 unique portable input members")
        raw = {name: archive.read(name) for name in names}
    for name, value in raw.items():
        equal({"bytes": len(value), "sha256": digest(value)}, manifest["files"][name], "input exact bytes/hash")
    need(raw["plan.json"] == (args.code_root / "protocol.json").read_bytes(), "protocol exact bytes")
    equal(parse(raw["plan.json"].decode()), manifest["protocol"], "full embedded protocol")
    need(digest(raw["source/p030_binary_continual.py"]) == manifest["protocol"]["source_sha256"], "original P030 public source")
    node = next(node for node in ast.parse(raw["source/p030_binary_continual.py"].decode("utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "Model")
    need(digest(ast.dump(node, include_attributes=False).encode()) == manifest["protocol"]["Model_AST_sha256"], "original Model AST hash only, never executed/imported")
    extra = np.random.default_rng(331000).integers(0, 30, size=(900, 2))
    bank = [[pair // 30, pair % 30, int(extra[pair, 0]), int(extra[pair, 1])] for pair in range(900)]
    equal(parse(raw["payloads.json"].decode()), bank, "independent frozen payload bank")
    word = lambda value: format(value, "05b") + "0"
    questions = []
    labels = {"r1": Counter(), "r12": Counter()}
    prefixes = {}
    for r in (1, 2):
        for pair, payload in enumerate(bank):
            q = "01010" + format(r, "03b") + "0" + "".join(word(value) for value in payload) + "111100"
            a = "".join(word(value) for value in payload[:r])
            need(len(q) == 39 and len(a) == r * 6, "independent AE1 grammar lengths")
            questions.append({"question_id": (r - 1) * 900 + pair, "pair_id": pair, "r": r, "payload": payload, "Q": q, "A": a})
            for position, label in enumerate(a + "S"):
                prefix = q + a[:position]
                need(prefix not in prefixes, "unique true teacher prefixes")
                prefixes[prefix] = label
                labels["r12"][label] += 1
                if r == 1:
                    labels["r1"][label] += 1
    equal(parse(raw["questions.json"].decode()), questions, "independent1800 Q/A grammar")
    need(len(prefixes) == 18000, "all consistent teacher prefixes")
    equal(dict(labels["r1"]), {"0": 3270, "1": 2130, "S": 900}, "stage1 target label counts")
    equal(dict(labels["r12"]), {"0": 9810, "1": 6390, "S": 1800}, "stage2 target label counts")
    initials, courses = {}, {}
    for seed in SEEDS:
        state = load_state(raw[f"initial/seed{seed}.npz"], seed, 0, 0)
        need(state_sha(state) == manifest["initial_states"][str(seed)]["full_state_sha256"], "frozen complete initial state")
        rng = np.random.default_rng(seed)
        need(np.array_equal(state["p0"], rng.normal(0, .2, (160, 64)).astype(np.float32)), "fresh initial W1 seed")
        need(np.array_equal(state["p2"], rng.normal(0, .15, (64, 3)).astype(np.float32)), "fresh initial W2 seed")
        for name in ("p1", "p3", *[f"{label}{index}" for label in ("m", "v", "birth") for index in range(4)]):
            need(not np.any(state[name]), "initial zero biases/moments/birth")
        initials[seed] = state
        for phase, offset in (("r1", 332000), ("r12", 333000)):
            pool = np.asarray([((r - 1) * 900 + pair, position) for pair in range(900) for r in TAUGHT[phase] for position in range(6 * r + 1)], dtype="<u2")
            rng = np.random.default_rng(seed + offset)
            expected = np.stack([pool[rng.permutation(len(pool))] for _ in range(40)])
            actual = np.load(io.BytesIO(raw[f"orders/seed{seed}-{phase}.npy"]), allow_pickle=False)
            need(actual.dtype.str == "<u2" and actual.shape == (40, TARGETS[phase], 2) and np.array_equal(actual, expected), "all40 independent exact target permutations")
            equal(manifest["schedules"][f"seed{seed}-{phase}"]["final_schedule_RNG"], rng.bit_generator.state, "phase schedule RNG endpoint")
            courses[seed, phase] = actual
    return manifest, questions, initials, courses


def scores_schema(value, taught):
    keys(value, {str(r) for r in taught}, "taught-r scores")
    for score in value.values():
        keys(score, {"questions", "whole_correct"}, "score row")
        need(score["questions"] == 900, "all900 questions per taught r")
        integer(score["whole_correct"], 0, 900, "whole correct count")


def generation_schema(value, taught_rows):
    keys(value, GEN_FIELDS, "generation file")
    scores_schema(value["scores"], sorted({row["r"] for row in taught_rows}))
    need(len(value["rows"]) == len(taught_rows), "all actually taught free outputs")
    for item, task in zip(value["rows"], taught_rows, strict=True):
        keys(item, GEN_ROW_FIELDS, "generation row")
        need((item["question_id"], item["r"], item["pair_id"]) == (task["question_id"], task["r"], task["pair_id"]), "free row task identity/order")
        need(isinstance(item["tokens"], str) and set(item["tokens"]) <= set("01S") and 1 <= len(item["tokens"]) <= 32, "generated action sequence domain")
        need(all(type(item[name]) is bool for name in ("context_exhausted", "cap_exhausted", "whole_correct")), "generated row boolean fields")
    integer(value["inference_calls"], len(taught_rows), len(taught_rows) * 32, "probe forward count")
    need(value["inference_dense_MAC"] == value["inference_calls"] * FORWARD_MAC, "probe forward cost")


def preflight(args, manifest, questions, initials):
    required = [args.receipt, args.formal_log, args.formal_stderr]
    required += [args.science / name for name in ("manifest.json", "execution-start.json", "compact.json", "timing.json", "storage.json")]
    need(all(path.is_file() for path in required), "all top metadata/log/receipt paths exist")
    receipt, compact, start = read(args.receipt), read(args.science / "compact.json"), read(args.science / "execution-start.json")
    need(receipt["status"] == "exit0" and receipt["formal_exit"] == 0 and receipt["session_id"] == args.formal_session and receipt["command_invocations"] == 1, "actual unique formal process exit0 receipt")
    need(receipt["manifest_sha256"] == APPROVED and receipt["preregistration_commit"] == args.prereg_commit, "actual receipt prereg identity")
    stamp = lambda value: datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(stamp(receipt["PR_created_UTC"]) < stamp(receipt["execution_start_file_creation_UTC"]), "public preregistration before scientific execution")
    equal(read(args.science / "manifest.json"), manifest, "actual scientific manifest")
    need(start["manifest_sha256"] == compact["manifest_sha256"] == APPROVED and start["preregistration_commit"] == compact["preregistration_commit"] == args.prereg_commit, "actual execution source/version identity")
    need(start["auto_retry"] is False and compact["status"] == "complete", "completed nonretry scientific process")
    need(compact["primary_students"] == 3 and compact["exact_full_replays"] == [101], "three retained primary students and one designated replay")
    need([row["seed"] for row in compact["students"]] == list(SEEDS), "all fixed seeds retained")
    expected_files = {"manifest.json", "execution-start.json", "compact.json", "timing.json", "storage.json"}
    bundles = {}
    for row in compact["students"]:
        keys(row, SUMMARY_FIELDS | {"replay_status", "final_TF_scores", "final_TF_inference_calls", "final_TF_inference_MAC"}, "compact student")
        seed = row["seed"]
        folder = args.science / f"seed{seed}"
        base_files = {"initial-state.npz", "final-state.npz", "training-summary.json", "curve.json", "final-truth.json", "final-failures.json"}
        need(all((folder / name).is_file() for name in base_files), "student top files exist")
        expected_files |= {f"seed{seed}/{name}" for name in base_files}
        summary, curve = read(folder / "training-summary.json"), read(folder / "curve.json")
        keys(summary, SUMMARY_FIELDS, "training summary")
        need(summary["seed"] == seed and 1 <= len(summary["phases"]) <= 2, "actual stage count")
        phase_names = [phase["phase"] for phase in summary["phases"]]
        equal(phase_names, list(PHASES[:len(phase_names)]), "only ordered permitted stages")
        same_state(load_state((folder / "initial-state.npz").read_bytes(), seed, 0, 0), initials[seed], "science initial versus frozen complete state")
        previous_exit, prior_updates, prior_calls = initials[seed], 0, 0
        phase_bundles, flat_curve = [], []
        for phase_summary in summary["phases"]:
            keys(phase_summary, PHASE_FIELDS, "phase summary")
            phase, count = phase_summary["phase"], phase_summary["epochs"]
            integer(count, 1, 40, "actual phase epoch count")
            phase_folder = folder / phase
            names = {"initial-state.npz", "final-state.npz"}
            names |= {f"{kind}-{epoch:03}.{extension}" for epoch in range(1, count + 1) for kind, extension in (("state", "npz"), ("epoch", "json"), ("generation", "json"))}
            need(all((phase_folder / name).is_file() for name in names), "all declared phase epoch/state/generation files exist")
            expected_files |= {f"seed{seed}/{phase}/{name}" for name in names}
            entry = load_state((phase_folder / "initial-state.npz").read_bytes(), seed, prior_updates, prior_calls)
            same_state(entry, previous_exit, "phase entry exact previous exit including Adam/RNG/inference counters")
            need(state_sha(entry) == phase_summary["entry_full_state_sha256"], "phase entry complete state SHA")
            taught_rows = [task for task in questions if task["r"] in TAUGHT[phase]]
            records, generations, states = [], [], []
            for epoch in range(1, count + 1):
                point = read(phase_folder / f"epoch-{epoch:03}.json")
                keys(point, EPOCH_FIELDS, "phase epoch record")
                need(point["phase"] == phase and point["epoch"] == epoch, "phase/epoch identity")
                need(point["global_updates"] == prior_updates + epoch * TARGETS[phase] and point["phase_updates"] == epoch * TARGETS[phase], "global/phase target counters")
                need(point["training_dense_MAC"] == point["global_updates"] * TRAIN_MAC and point["phase_training_dense_MAC"] == point["phase_updates"] * TRAIN_MAC, "global/phase training costs")
                keys(point["training"], TRAIN_FIELDS, "epoch training aggregate")
                training = point["training"]
                need(training["targets"] == TARGETS[phase], "complete target set per epoch")
                integer(training["pre_update_prediction_correct"], 0, TARGETS[phase], "pre-update prediction count")
                need(training["CE_loss_sum"] >= 0 and training["CE_loss_mean"] == training["CE_loss_sum"] / TARGETS[phase], "finite sequential loss aggregate")
                need(re.fullmatch("[0-9a-f]{64}", training["canonical_target_trace_sha256"]) is not None, "per-target prediction/loss digest form")
                scores_schema(point["scores"], TAUGHT[phase])
                generation = read(phase_folder / f"generation-{epoch:03}.json")
                generation_schema(generation, taught_rows)
                state = load_state((phase_folder / f"state-{epoch:03}.npz").read_bytes(), seed, point["global_updates"], point["cumulative_probe_inference_calls"])
                need(state_sha(state) == point["full_state_sha256"], "epoch fullstate canonical SHA")
                records.append(point)
                generations.append(generation)
                states.append(state)
            previous_exit = load_state((phase_folder / "final-state.npz").read_bytes(), seed, records[-1]["global_updates"], records[-1]["cumulative_probe_inference_calls"])
            same_state(previous_exit, states[-1], "phase final exact last epoch NPZ")
            need(state_sha(previous_exit) == phase_summary["exit_full_state_sha256"], "phase exit fullstate SHA")
            phase_bundles.append({"phase": phase, "entry": entry, "exit": previous_exit, "summary": phase_summary, "records": records, "generations": generations, "states": states, "taught_rows": taught_rows})
            flat_curve.extend(records)
            prior_updates, prior_calls = records[-1]["global_updates"], records[-1]["cumulative_probe_inference_calls"]
        equal(curve, flat_curve, "complete ordered curriculum curve")
        if len(phase_bundles) == 1:
            need(not (folder / "r12").exists(), "phase1 blocked student has no stage2 artifacts")
        final_state = load_state((folder / "final-state.npz").read_bytes(), seed, prior_updates, prior_calls)
        same_state(final_state, previous_exit, "student final exact last phase fullstate")
        taught = TAUGHT[phase_names[-1]]
        taught_rows = [task for task in questions if task["r"] in taught]
        truth = read(folder / "final-truth.json")
        keys(truth, {"truth", "scores", "inference_calls", "inference_dense_MAC", "learning_state_unchanged", "free_generation_reused", "taught_r_only"}, "final TF file")
        need(truth["taught_r_only"] == list(taught) and len(truth["truth"]) == len(taught_rows), "final TF only actual taught set")
        for task, item in zip(taught_rows, truth["truth"], strict=True):
            keys(item, QUESTION_FIELDS | {"expected", "generation", "TF"}, "final truth row")
            need(all(item[name] == value for name, value in task.items()) and item["expected"] == task["A"] + "S", "final truth grammar identity")
            need(len(item["TF"]) == 6 * task["r"] + 1, "all actual taught TF targets")
            for position, label in enumerate(task["A"] + "S"):
                point = item["TF"][position]
                keys(point, TF_FIELDS, "TF token")
                need((point["position"], point["prefix"], point["target"]) == (position, task["Q"] + task["A"][:position], label), "correct true-prefix teacher target")
                need(len(point["prediction"]) == 1 and point["prediction"] in "01S", "TF predicted action")
                need(len(point["logits_01S"]) == len(point["probabilities_01S"]) == 3, "TF vector shapes")
                need(all(0 <= value <= 1 for value in point["probabilities_01S"]) and point["target_CE"] >= 0, "TF probability/CE domain")
        failures = read(folder / "final-failures.json")
        need(isinstance(failures, list) and len(failures) <= len(taught_rows), "all final failures")
        bundles[seed] = {"summary": summary, "compact": row, "phases": phase_bundles, "final_state": final_state, "truth": truth, "failures": failures}
    science_inventory = inventory(args.science)
    equal(set(science_inventory), expected_files, "exact completed science file inventory with no failure/extra-phase files")
    timing, storage = read(args.science / "timing.json"), read(args.science / "storage.json")
    equal([(row["mode"], row["seed"]) for row in timing["trajectories"]], [("primary", 101), ("primary", 202), ("primary", 303), ("replay", 101)], "actual three primary and designated replay timing records")
    need(all(row["seconds"] > 0 for row in timing["trajectories"]), "positive finite trajectory durations")
    need(timing["total_seconds"] >= sum(row["seconds"] for row in timing["trajectories"]), "full formal walltime scope")
    if "formal_seconds" in receipt:
        need(receipt["formal_seconds"] == timing["total_seconds"], "receipt actual walltime")
    for name in ("primary_updates", "replay_updates", "primary_training_dense_MAC", "replay_training_dense_MAC"):
        if name in receipt:
            equal(receipt[name], compact[name], "receipt complete scientific count")
    need(storage["input_archive_bytes"] == manifest["archive"]["bytes"], "input archive bytes")
    need(storage["output_bytes_before_this_record"] == sum(value["bytes"] for name, value in science_inventory.items() if name != "storage.json"), "science output bytes")
    progress, terminal = [], []
    for line in args.formal_log.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        item = parse(line)
        if item.get("mode") in ("primary", "replay"):
            progress.append(item)
        elif item.get("status") == "complete":
            terminal.append(item)
        else:
            need(False, "unknown formal stdout record")
    expected_progress = []
    for mode, seed in (("primary", 101), ("primary", 202), ("primary", 303), ("replay", 101)):
        for phase in bundles[seed]["phases"]:
            for point in phase["records"]:
                expected_progress.append({"mode": mode, "seed": seed, "phase": phase["phase"], "epoch": point["epoch"], "scores": point["scores"], "streak": point["streak"], "decision": point["decision"]})
    equal(progress, expected_progress, "actual complete phase/epoch stdout including replay")
    equal(terminal, [compact], "actual process completion stdout")
    metadata = {"receipt_sha256": sha(args.receipt), "stdout_sha256": sha(args.formal_log), "stdout_bytes": args.formal_log.stat().st_size, "stderr_sha256": sha(args.formal_stderr), "stderr_bytes": args.formal_stderr.stat().st_size, "preregistration_precedes_execution": True, "actual_timing_trajectories": 4, "epoch_progress_records": len(progress)}
    return compact, bundles, science_inventory, timing, metadata


class Cost:
    def __init__(self, output):
        self.output, self.started = output, time.perf_counter()
        self.calls, self.phases = 0, Counter()
        self.script_sha256 = sha(Path(__file__))

    def increment(self, phase):
        self.calls += 1
        self.phases[phase] += 1

    def record(self):
        return {"forward_calls": self.calls, "dense_MAC": self.calls * FORWARD_MAC, "calls_by_phase": dict(self.phases), "optimizer_calls": 0, "new_students": 0, "external_model_calls": 0}

    def persist(self, status):
        value = {"status": status, **self.record(), "seconds": time.perf_counter() - self.started, "script_sha256": self.script_sha256, "attempts": 1}
        target = self.output / "audit-cost.json"
        temporary = self.output / "audit-cost.json.tmp"
        temporary.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, target)


class Forward:
    def __init__(self, state, cost, phase):
        self.state, self.cost, self.phase, self.calls = state, cost, phase, 0

    def __call__(self, text):
        need(0 < len(text) <= 80 and set(text) <= set("01"), "only binary Q plus prefix within fixed80")
        x = np.zeros((80, 2), np.float32)
        for index, bit in enumerate(text):
            x[index, int(bit)] = 1
        hidden = np.tanh(x.reshape(1, 160) @ self.state["p0"] + self.state["p1"])
        logits = (hidden @ self.state["p2"] + self.state["p3"])[0]
        self.calls += 1
        self.cost.increment(self.phase)
        need(bool(np.isfinite(logits).all()), "finite independent logits")
        return logits

    def generate(self, q):
        tokens = ""
        for _ in range(32):
            if len(q + tokens) > 80:
                return {"tokens": tokens, "context_exhausted": True, "cap_exhausted": False}
            token = "01S"[int(np.argmax(self(q + tokens)))]
            tokens += token
            if token == "S":
                return {"tokens": tokens, "context_exhausted": False, "cap_exhausted": False}
        return {"tokens": tokens, "context_exhausted": False, "cap_exhausted": True}


def independent_generation(state, taught_rows, cost):
    before = state_sha(state)
    forward = Forward(state, cost, "epoch_free_generation")
    outputs = []
    for task in taught_rows:
        generated = forward.generate(task["Q"])
        outputs.append({"question_id": task["question_id"], "r": task["r"], "pair_id": task["pair_id"], **generated, "whole_correct": generated["tokens"] == task["A"] + "S" and not generated["context_exhausted"]})
    scores = {str(r): {"whole_correct": sum(row["whole_correct"] for row in outputs if row["r"] == r), "questions": 900} for r in sorted({row["r"] for row in taught_rows})}
    need(state_sha(state) == before, "full state unchanged by independent generation")
    return {"scores": scores, "rows": outputs, "inference_calls": forward.calls, "inference_dense_MAC": forward.calls * FORWARD_MAC}


def independent_tf(state, taught_rows, generation, cost):
    before = state_sha(state)
    forward = Forward(state, cost, "final_TF")
    truth = []
    for task, free in zip(taught_rows, generation["rows"], strict=True):
        targets = []
        for position, label in enumerate(task["A"] + "S"):
            prefix = task["Q"] + task["A"][:position]
            logits = forward(prefix).astype(np.float64)
            logp = logits - np.logaddexp.reduce(logits)
            targets.append({"position": position, "prefix": prefix, "target": label, "prediction": "01S"[int(logits.argmax())], "logits_01S": logits.tolist(), "probabilities_01S": np.exp(logp).tolist(), "target_CE": -float(logp["01S".index(label)])})
        truth.append({**task, "expected": task["A"] + "S", "generation": free, "TF": targets})
    taught = sorted({task["r"] for task in taught_rows})
    scores = {str(r): {"questions": 900, "TF_correct": sum(point["prediction"] == point["target"] for row in truth if row["r"] == r for point in row["TF"]), "TF_targets": 900 * (6 * r + 1)} for r in taught}
    need(state_sha(state) == before, "full state unchanged by independent TF")
    need(forward.calls == sum(len(task["A"]) + 1 for task in taught_rows), "complete actual taught TF count")
    return {"truth": truth, "scores": scores, "inference_calls": forward.calls, "inference_dense_MAC": forward.calls * FORWARD_MAC, "learning_state_unchanged": True, "free_generation_reused": True, "taught_r_only": taught}


def decomposed_metrics(truth):
    result = {}
    for r in sorted({row["r"] for row in truth}):
        rows = [row for row in truth if row["r"] == r]
        info = [position for position in range(6 * r) if position % 6 != 5]
        tails = [position for position in range(6 * r) if position % 6 == 5]
        free_correct = lambda row, position: position < len(row["generation"]["tokens"]) and row["generation"]["tokens"][position] == row["A"][position]
        result[str(r)] = {"questions": len(rows), "info_bit_targets": len(rows) * 5 * r, "tail0_targets": len(rows) * r, "STOP_targets": len(rows), "free_whole_correct": sum(row["generation"]["whole_correct"] for row in rows), "free_info_bits_correct": sum(free_correct(row, pos) for row in rows for pos in info), "free_tail0_correct": sum(free_correct(row, pos) for row in rows for pos in tails), "free_STOP_position_correct": sum(row["generation"]["tokens"].endswith("S") and len(row["generation"]["tokens"]) == 6 * r + 1 for row in rows), "TF_info_bits_correct": sum(row["TF"][pos]["prediction"] == row["TF"][pos]["target"] for row in rows for pos in info), "TF_tail0_correct": sum(row["TF"][pos]["prediction"] == "0" for row in rows for pos in tails), "TF_STOP_correct": sum(row["TF"][6 * r]["prediction"] == "S" for row in rows)}
    return result


def audit_student(seed, bundle, questions, courses, output, cost):
    started_calls = cost.calls
    cumulative_updates = cumulative_calls = cumulative_questions = 0
    cumulative_by_r = {"1": 0, "2": 0}
    phase_summaries, phase_proofs, refs = [], [], []
    final_generation = final_taught = None
    for index, phase_bundle in enumerate(bundle["phases"]):
        phase, records = phase_bundle["phase"], phase_bundle["records"]
        if index:
            need(phase_summaries[-1]["decision"] == "advance", "no stage2 after failed first stage")
        entry_updates, entry_calls = cumulative_updates, cumulative_calls
        streak, first_full, stable, decision = 0, None, None, None
        epoch_refs = []
        for epoch, (point, state, actual) in enumerate(zip(records, phase_bundle["states"], phase_bundle["generations"], strict=True), 1):
            need(decision is None, "continued training after fixed stage decision")
            generated = independent_generation(state, phase_bundle["taught_rows"], cost)
            equal(generated, actual, "every actual taught free output and score")
            full = all(generated["scores"][str(r)]["whole_correct"] == 900 for r in TAUGHT[phase])
            streak = streak + 1 if full else 0
            if full and first_full is None:
                first_full = epoch
            if streak >= 2:
                stable = epoch
                decision = "advance" if phase == "r1" else "complete"
            elif epoch == 40:
                decision = "blocked_before_r2" if phase == "r1" else "phase2_cap_failed"
            cumulative_updates += TARGETS[phase]
            cumulative_calls += generated["inference_calls"]
            cumulative_questions += len(phase_bundle["taught_rows"])
            for r in TAUGHT[phase]:
                cumulative_by_r[str(r)] += 900
            training = point["training"]
            expected_point = {"phase": phase, "epoch": epoch, "global_updates": cumulative_updates, "phase_updates": epoch * TARGETS[phase], "training_dense_MAC": cumulative_updates * TRAIN_MAC, "phase_training_dense_MAC": epoch * TARGETS[phase] * TRAIN_MAC, "training": training, "scores": generated["scores"], "streak": streak, "decision": decision, "first_full_epoch": first_full, "stable_pass_epoch": stable, "cumulative_question_exposures": cumulative_questions, "cumulative_question_exposures_by_r": cumulative_by_r.copy(), "epoch_probe_inference_calls": generated["inference_calls"], "epoch_probe_inference_MAC": generated["inference_dense_MAC"], "phase_probe_inference_calls": cumulative_calls - entry_calls, "phase_probe_inference_MAC": (cumulative_calls - entry_calls) * FORWARD_MAC, "cumulative_probe_inference_calls": cumulative_calls, "cumulative_probe_inference_MAC": cumulative_calls * FORWARD_MAC, "full_state_sha256": state_sha(state)}
            equal(point, expected_point, "all epoch counters, exposures, streak, first/full/stable and decisions")
            teacher = hashlib.sha256()
            for qid, position in courses[seed, phase][epoch - 1]:
                task, position = questions[int(qid)], int(position)
                teacher.update((canonical([task["question_id"], position, task["Q"] + task["A"][:position], (task["A"] + "S")[position]]) + "\n").encode())
            proof = {"status": "passed", "seed": seed, "phase": phase, "epoch": epoch, "full_state_sha256": state_sha(state), "scores": generated["scores"], "streak": streak, "first_full_epoch": first_full, "stable_pass_epoch": stable, "decision": decision, "free_questions_verified": len(phase_bundle["taught_rows"]), "independent_generation_canonical_sha256": digest(canonical(generated).encode()), "generation_exact_equal": True, "frozen_teacher_order_canonical_sha256": teacher.hexdigest(), "native_prediction_loss_digest_form_checked": training["canonical_target_trace_sha256"], "unarchived_target_losses_or_gradients_recomputed": False, "independent_epoch_forward_calls": generated["inference_calls"], "independent_epoch_dense_MAC": generated["inference_dense_MAC"], "audit_cost_so_far": cost.record()}
            name = f"seed{seed}-{phase}-epoch{epoch:03}.json"
            write(output / name, proof)
            ref = "numeric-proof/" + name
            refs.append(ref)
            epoch_refs.append(ref)
            cost.persist("running")
            final_generation, final_taught = generated, phase_bundle["taught_rows"]
        need(decision is not None, "complete fixed stage termination")
        expected_phase = {"phase": phase, "epochs": len(records), "decision": decision, "first_full_epoch": first_full, "stable_pass_epoch": stable, "entry_full_state_sha256": state_sha(phase_bundle["entry"]), "exit_full_state_sha256": state_sha(phase_bundle["exit"]), "target_updates": cumulative_updates - entry_updates, "question_exposures": len(records) * len(phase_bundle["taught_rows"]), "training_dense_MAC": (cumulative_updates - entry_updates) * TRAIN_MAC, "probe_inference_calls": cumulative_calls - entry_calls, "probe_inference_MAC": (cumulative_calls - entry_calls) * FORWARD_MAC, "final_scores": final_generation["scores"]}
        equal(expected_phase, phase_bundle["summary"], "full independently reconstructed phase summary")
        phase_summaries.append(expected_phase)
        phase_proofs.append({"phase": phase, "epochs": len(records), "first_full_epoch": first_full, "stable_pass_epoch": stable, "decision": decision, "scores": final_generation["scores"], "epoch_proof_refs": epoch_refs})
    last_phase = phase_summaries[-1]["phase"]
    need((len(phase_summaries) == 2) == (phase_summaries[0]["decision"] == "advance"), "actual stage advancement/block branch")
    summary = {"seed": seed, "phases": phase_summaries, "phase_reached": last_phase, "taught_r": list(TAUGHT[last_phase]), "blocked_before_r2": phase_summaries[-1]["decision"] == "blocked_before_r2", "completed_curriculum": phase_summaries[-1]["decision"] == "complete", "training_updates": cumulative_updates, "training_dense_MAC": cumulative_updates * TRAIN_MAC, "question_exposures": cumulative_questions, "question_exposures_by_r": cumulative_by_r, "probe_inference_calls": cumulative_calls, "probe_inference_MAC": cumulative_calls * FORWARD_MAC, "final_full_state_sha256": state_sha(bundle["final_state"]), "p_m_v_birth_array_bytes": 209980}
    equal(summary, bundle["summary"], "entire independently derived student summary")
    tf = independent_tf(bundle["final_state"], final_taught, final_generation, cost)
    equal(tf, bundle["truth"], "all final actual taught TF logits/probabilities/CE exact")
    failures = [row for row in tf["truth"] if not row["generation"]["whole_correct"]]
    equal(failures, bundle["failures"], "every final failure exact")
    row = {**summary, "replay_status": "complete_exact" if seed == 101 else "not_planned", "final_TF_scores": tf["scores"], "final_TF_inference_calls": tf["inference_calls"], "final_TF_inference_MAC": tf["inference_dense_MAC"]}
    equal(row, bundle["compact"], "complete compact student")
    proof = {"status": "passed", "seed": seed, "phases": phase_proofs, "taught_r_only": list(TAUGHT[last_phase]), "completed_curriculum": summary["completed_curriculum"], "blocked_before_r2": summary["blocked_before_r2"], "summary": summary, "final_TF_logits_probabilities_CE_verified": tf["inference_calls"], "final_truth_independent_canonical_sha256": digest(canonical(tf).encode()), "final_failures_independent_canonical_sha256": digest(canonical(failures).encode()), "final_failure_question_ids": [task["question_id"] for task in failures], "final_decomposed_metrics": decomposed_metrics(tf["truth"]), "independent_forward_calls": cost.calls - started_calls, "independent_dense_MAC": (cost.calls - started_calls) * FORWARD_MAC, "audit_cost_so_far": cost.record(), "optimizer_calls": 0}
    name = f"seed{seed}-student.json"
    write(output / name, proof)
    refs.append("numeric-proof/" + name)
    cost.persist("running")
    print(canonical({"phase": "independent_student_complete", "seed": seed, "actual_phases": [{"phase": point["phase"], "epochs": point["epochs"], "decision": point["decision"]} for point in phase_summaries], "final_scores": phase_summaries[-1]["final_scores"], "audit_forward_calls": cost.calls - started_calls}), flush=True)
    return row, proof, refs


def run(args, cost):
    need(args.root_confirmed_exit0, "explicit coordinator postrun GO required before trained-state access")
    need(args.prereg_commit == PREREG and args.formal_session == FORMAL_SESSION, "explicit approved prereg commit and actual formal session required")
    for path in (args.manifest, args.manifest.parent / "source-freeze.json", args.manifest.parent / "inputs.zip", args.receipt, args.formal_log, args.formal_stderr):
        need(path.is_file(), "all external input/log/receipt paths exist")
    manifest, questions, initials, courses = inputs(args)
    compact, bundles, before, timing, metadata = preflight(args, manifest, questions, initials)
    prereg_before = inventory(args.manifest.parent)
    write(args.output_root / "metadata-preflight.json", {"status": "passed", "manifest_sha256": APPROVED, "source_hashes": manifest["source_hashes"], "all_required_paths_and_schemas_checked_before_any_trained_forward": True, "model_forward_calls": 0, "science_files": len(before), "actual_phases_by_seed": {str(seed): [{"phase": item["phase"], "epochs": len(item["records"])} for item in bundle["phases"]] for seed, bundle in bundles.items()}, **metadata})
    output = args.output_root / "numeric-proof"
    output.mkdir(exist_ok=False)
    rows, details, refs = [], [], []
    for seed in SEEDS:
        row, proof, student_refs = audit_student(seed, bundles[seed], questions, courses, output, cost)
        rows.append(row)
        details.append(proof)
        refs.extend(student_refs)
    primary_updates = sum(row["training_updates"] for row in rows)
    primary_train_mac = sum(row["training_dense_MAC"] for row in rows)
    primary_probes = sum(row["probe_inference_calls"] for row in rows)
    final_tf_calls = sum(row["final_TF_inference_calls"] for row in rows)
    expected = {"id": manifest["protocol"]["id"], "status": "complete", "author": "Codex", "manifest_sha256": APPROVED, "preregistration_commit": args.prereg_commit, "students": rows, "primary_students": 3, "exact_full_replays": [101], "primary_updates": primary_updates, "primary_training_dense_MAC": primary_train_mac, "replay_updates": rows[0]["training_updates"], "replay_training_dense_MAC": rows[0]["training_dense_MAC"], "primary_probe_inference_calls": primary_probes, "primary_probe_inference_MAC": primary_probes * FORWARD_MAC, "replay_probe_inference_calls": rows[0]["probe_inference_calls"], "replay_probe_inference_MAC": rows[0]["probe_inference_MAC"], "final_TF_inference_calls": final_tf_calls, "final_TF_inference_MAC": final_tf_calls * FORWARD_MAC, "all_completed_curriculum": all(row["completed_curriculum"] for row in rows), "array_bytes_per_student": 209980, "external_model_calls": 0, "limits": manifest["protocol"]["limits"]}
    equal(compact, expected, "entire independently derived compact")
    need(cost.calls == primary_probes + final_tf_calls, "actual independent forward cost accounting")
    equal(before, inventory(args.science), "all science files unchanged after independent audit")
    equal(prereg_before, inventory(args.manifest.parent), "all frozen input files unchanged after audit")
    for name, pin in manifest["source_hashes"].items():
        need(sha(args.code_root / name) == pin, "core source unchanged after audit")
    need(sha(Path(__file__)) == cost.script_sha256, "auditor source unchanged during run")
    need(sha(args.receipt) == metadata["receipt_sha256"] and sha(args.formal_log) == metadata["stdout_sha256"] and sha(args.formal_stderr) == metadata["stderr_sha256"], "execution metadata unchanged after audit")
    proof_inventory = {ref: {"bytes": (args.output_root / ref).stat().st_size, "sha256": sha(args.output_root / ref)} for ref in refs}
    write(args.output_root / "post-run-details.json", {"status": "passed", "manifest_sha256": APPROVED, "source_hashes": manifest["source_hashes"], "students": details, "science_file_inventory": before, "prereg_file_inventory": prereg_before, "numeric_proof_refs": refs, "numeric_proof_inventory": proof_inventory})
    epochs = sum(len(bundle["records"]) for student in bundles.values() for bundle in student["phases"])
    free_questions = sum(len(bundle["records"]) * len(bundle["taught_rows"]) for student in bundles.values() for bundle in student["phases"])
    result = {"status": "passed", "root_confirmed_formal_exit0": True, "formal_session": args.formal_session, "preregistration_commit": args.prereg_commit, "manifest_sha256": APPROVED, "inputs_zip_sha256": ZIP_SHA, "source_hashes": manifest["source_hashes"], "receipt_sha256": metadata["receipt_sha256"], "actual_primary_students": 3, "actual_full_replay_seeds": [101], "not_replayed_seeds": [202, 303], "actual_phases_by_seed": {str(row["seed"]): row["phases"] for row in rows}, "all_students_including_failures_retained": True, "all_completed_curriculum": expected["all_completed_curriculum"], "actual_primary_epochs_verified": epochs, "whole_free_generations_verified": free_questions, "final_TF_logits_probabilities_CE_verified": final_tf_calls, "full_science_NPZ_verified": sum(name.endswith(".npz") for name in before), "frozen_initial_states_verified": 3, "frozen_target_permutations_independently_verified": 240, "phase_carry_fullarrays_Adam_birth_t_RNG_probe_counters_exact": True, "final_decomposed_metrics_by_seed": {str(proof["seed"]): proof["final_decomposed_metrics"] for proof in details}, "primary_updates_evidenced_by_epoch_counters": primary_updates, "primary_training_dense_MAC": primary_train_mac, "replay_updates_seed101": rows[0]["training_updates"], "replay_training_dense_MAC_seed101": rows[0]["training_dense_MAC"], "primary_probe_forward_calls": primary_probes, "replay_probe_forward_calls_seed101": rows[0]["probe_inference_calls"], "native_final_TF_forward_calls": final_tf_calls, "audit_extra_forward_calls": cost.calls, "audit_extra_dense_MAC": cost.calls * FORWARD_MAC, "audit_attempt_count": 1, "metadata_checked_before_any_trained_forward": True, "each_epoch_and_student_numeric_proof_and_cost_persisted": True, "numeric_proof_count": len(refs), "all_source_frozen_inputs_science_and_execution_metadata_unchanged": True, "all_generation_TF_failures_curves_exposures_stops_costs_exact": True, "formal_wall_seconds": timing["total_seconds"], "metadata": metadata, "replay_scope": "Actual exit0, frozen driver assertions, ordered stdout and timing establish one complete seed101 replay comparing epoch prediction/loss digests, generated outputs and full state. Separate replay state copies and raw target records are not stored; no claim of re-auditing those absent internals. Seeds202/303 are not replayed.", "independent_limit": "All archived primary states, phase transitions, free outputs, final taught-set TF, data/orders, aggregate/digest form, exposures, stops and costs were checked. Unarchived target losses, gradients and intermediate optimizer trajectories were not reconstructed.", "interpretation_limit": "Fixed900-payload r1-to-r12 curriculum fit/retention, not heldout or arbitrary-r/length generalization. No joint-training causal control; equal question counts have unequal target weight6300/11700.", "optimizer_calls": 0, "new_students": 0, "external_model_calls": 0, "legacy_or_driver_modules_imported": False, "details": "review/post-run-details.json"}
    write(args.output_root / "post-run.json", result)
    print(canonical({"status": "passed", "all_completed_curriculum": result["all_completed_curriculum"], "actual_epochs_verified": epochs, "free_questions_verified": free_questions, "TF_targets_verified": final_tf_calls, "audit_cost": cost.record()}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "science", "code-root", "formal-log", "formal-stderr", "receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--prereg-commit", required=True)
    parser.add_argument("--formal-session", type=int, required=True)
    parser.add_argument("--root-confirmed-exit0", action="store_true")
    parser.add_argument("--output-root", type=Path, default=HERE)
    args = parser.parse_args()
    need(not any((args.output_root / name).exists() for name in ("metadata-preflight.json", "numeric-proof", "post-run.json", "audit-cost.json", "audit-cost.json.tmp", "audit-failure.json")), "new audit attempt output required")
    args.output_root.mkdir(parents=True, exist_ok=True)
    cost, status = Cost(args.output_root), "failed"
    cost.persist("metadata_preflight_pending")
    try:
        run(args, cost)
        status = "passed"
    except Exception as error:
        message = str(error) if isinstance(error, AssertionError) else "Unexpected processing error; full traceback remains local tool evidence."
        write(args.output_root / "audit-failure.json", {"status": "failed", "error_type": type(error).__name__, "message": message, "cost": cost.record(), "script_sha256": sha(Path(__file__)), "completed_epoch_and_student_numeric_proofs_retained": True})
        raise
    finally:
        cost.persist(status)


if __name__ == "__main__":
    main()
