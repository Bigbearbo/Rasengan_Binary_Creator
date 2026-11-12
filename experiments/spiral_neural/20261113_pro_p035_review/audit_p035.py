"""Pro's bounded read-only audit of the frozen Codex P035 public package.

Defaults resolve beside this file, independently of the current directory.
Only the requested review report is written; no training/replay is performed.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import io
import json
import platform
import sys
import zipfile

HERE = Path(__file__).resolve().parent
CODEX_COMMIT = "a309f2fc3e23255327fcab35745c27012d15ed4f"
FREEZE_SHA = "f2b6ad6ef4b26bda02a20376f534a16d26cffece4527457fc102bd51b6b6f702"
PACKAGE_MANIFEST_SHA = "999b3d2ccb302613874b0f04a2efc67934847b33c88c5320b7ceb709492e4a8d"
if not __debug__:
    raise RuntimeError("Run this audit without -O: its assertions are required checks")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("package", type=Path, nargs="?", default=HERE.parent / "20261112_p035",
                    help="P035 package; defaults to the sibling 20261112_p035 directory")
parser.add_argument("--out", type=Path, default=HERE / "results.json",
                    help="Review JSON; defaults to results.json beside this script")
args = parser.parse_args()
p = args.package.resolve()
sys.dont_write_bytecode = True

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read(name):
    return json.loads((p / name).read_text(encoding="utf-8"))

before = {str(f.relative_to(p)): digest(f.read_bytes()) for f in p.rglob("*") if f.is_file()}
assert digest((p / "source-freeze.json").read_bytes()) == FREEZE_SHA
assert digest((p / "package-manifest.json").read_bytes()) == PACKAGE_MANIFEST_SHA
freeze = read("source-freeze.json")
for name, expected in freeze["sources_sha256"].items():
    assert digest((p / name).read_bytes()) == expected, name
package = read("package-manifest.json")
for name, info in package["files"].items():
    data = (p / name).read_bytes()
    assert len(data) == info["bytes"] and digest(data) == info["sha256"], name
archives = {name: zipfile.ZipFile(p / name) for name in package["zip_entries"]}
zmap = {}
for archive, entries in package["zip_entries"].items():
    z = archives[archive]
    assert set(z.namelist()) == {r["name"] for r in entries}
    for entry in entries:
        name = entry["name"]
        assert name not in zmap, name
        data = z.read(name)
        assert len(data) == entry["bytes"] and digest(data) == entry["sha256"], name
        zmap[name] = z

def zb(name):
    return zmap[name].read(name)

def zj(name):
    return json.loads(zb(name))

def state(name):
    with np.load(io.BytesIO(zb(name)), allow_pickle=False) as source:
        return {key: source[key].copy() for key in source.files}

for source, archived in (
    ("work/sle-p035/codec-final-gate/checks.json", "engineering/codec-final-gate/checks.json"),
    ("work/sle-p035/runner-engineering-final/checks.json", "engineering/runner/checks.json"),
    ("work/sle-p035/independent-engineering/checks.json", "reviews/independent-engineering/checks.json"),
):
    assert digest(zb(archived)) == freeze["engineering"][source]["sha256"]
manifest = zj("run/manifest.json")
assert manifest["source_sha256"] == freeze["sources_sha256"]
assert freeze["frozen_before_first_scientific_update_UTC"] < manifest["registered_UTC_before_first_scientific_update"]
# Import only after validating the frozen public source and archive bytes.
sys.path.insert(0, str(p))
import run_p035 as run
import numpy as np
run.validate_protocol(p / "protocol.json")

forbidden_calls = []
def forbid(*unused, **kwargs):
    forbidden_calls.append("gradient/update")
    raise AssertionError("No gradient or training call is allowed in this audit")
for method in ("step", "lesson", "loss_grad"):
    setattr(run.ref.Model, method, forbid)

def model(name, seed):
    saved = state(name)
    net = run.ref.Model(seed, int(saved["L"]), int(saved["H"]))
    for label in ("p", "m", "v", "birth"):
        setattr(net, label, [saved[f"{label}{i}"].copy() for i in range(4)])
    net.t = int(saved["t"])
    net.growth_rng.bit_generator.state = json.loads(str(saved["growth_rng"]))
    assert run.ref.equal_state(saved, net.state())
    return net

c = run.course
budgets = {policy: [c.lesson_budget(stage, policy) for stage in c.STAGES] for policy in ("F", "G")}
courses = {}
for row in manifest["courses"]:
    policy, seed, stage_name = row["policy"], row["seed"], row["stage"]
    stage = c.get_stage(stage_name)
    recorded = zj(f"run/courses/{policy}-seed{seed}/{stage_name}.json")
    regenerated = c.semantic_course(stage, seed, row["lessons"])
    assert recorded == [list(pair) for pair in regenerated]
    assert run.json_sha(recorded) == row["course_sha256_canonical"]
    assert run.json_sha([c.answer(stage, op, v) + "S" for op, v in recorded]) == row["target_stream_sha256"]
    assert c.lesson_budget(stage, policy) == row["budget"]
    courses[(policy, seed, stage.index)] = regenerated
for seed in c.SEEDS:
    for stage in c.STAGES:
        f, g = courses[("F", seed, stage.index)], courses[("G", seed, stage.index)]
        assert f == g[:len(f)]

compact = read("compact.json")
all_truth = []
scores = {}
totals = collections.Counter()
response_exposure = []
growth_records = []
for row in compact["student_rows"]:
    codec, policy, seed = row["codec"], row["policy"], row["seed"]
    tag = f"{codec}-{policy}-seed{seed}"
    result = zj(f"run/{tag}/result.json")
    lesson_lists = [courses[(policy, seed, stage.index)] for stage in c.STAGES]
    assert c.exposure_ledger(lesson_lists) == zj(f"run/{tag}/exposure-ledger.json")
    interface = run.interface_exposure(codec, lesson_lists)
    assert interface == zj(f"run/{tag}/interface-exposure.json")
    response_counts = collections.Counter()
    for item in interface:
        response_counts[int(item["target"][:-2], 2)] += item["presentations"]
    assert (response_counts[4], response_counts[6]) == (250, 250)
    response_exposure.append({"student": tag, "answer_value4": response_counts[4], "answer_value6": response_counts[6]})
    sums = collections.Counter()
    for stage in c.STAGES:
        summary = zj(f"run/{tag}/{stage.name}/summary.json")
        budget = budgets[policy][stage.index]
        assert summary["budget"] == budget
        assert summary["course_sha256"] == run.json_sha(lesson_lists[stage.index])
        assert summary["train_dense_MACs"] == budget["executed_train_MACs"]
        assert summary["target_updates"] == budget["target_updates"]
        assert summary["global_updates_at_end"] - summary["global_updates_at_start"] == budget["target_updates"]
        assert summary["parameters"] == budget["H"] * (2 * budget["L"] + 4) + 3
        sums.update(lessons=budget["lessons"], updates=budget["target_updates"], MAC=budget["executed_train_MACs"])
        growth_records.append((tag, stage.name, zj(f"run/{tag}/{stage.name}/growth.json")))
    assert sums["updates"] == row["target_updates"] == result["target_updates"]
    assert sums["MAC"] == row["executed_training_dense_MACs"] == result["executed_training_dense_MACs"]
    totals.update(sums)
    truth = zj(f"run/{tag}/final-truth.json")
    assert run.metrics(truth, c.STAGES[-1]) == row["final_metrics"]
    score = c.milestone_score({(r["operator"], r["value"]): r["whole_correct"] for r in truth})
    assert score == row["primary"] == result["primary"]
    scores[(codec, policy, seed)] = score["score"]
    all_truth.extend(truth)
    initial, final = state(f"run/{tag}/initial-state.npz"), state(f"run/{tag}/final-state.npz")
    assert run.state_hash(initial) == result["initial_state_sha256"]
    assert run.state_hash(final) == result["final_state_sha256"]
    assert int(final["t"]) == sums["updates"] and int(final["L"]) == 13 and int(final["H"]) == 69

for policy in ("F", "G"):
    for seed in c.SEEDS:
        assert run.ref.equal_state(state(f"run/S-{policy}-seed{seed}/initial-state.npz"), state(f"run/H-{policy}-seed{seed}/initial-state.npz"))
    fresh, _ = run.initialize(202, policy)
    assert run.ref.equal_state(fresh.state(), state(f"run/S-{policy}-seed202/initial-state.npz"))
interactions = [(scores[("S", "G", s)] - scores[("S", "F", s)]) - (scores[("H", "G", s)] - scores[("H", "F", s)]) for s in c.SEEDS]
assert interactions == [row["interaction"] for row in compact["primary"]["per_seed_interactions"]]
assert totals["updates"] == compact["primary_target_updates"]
assert totals["MAC"] == compact["primary_training_dense_MACs"]

inference_rows, inference_examples, max_logit_diff = 0, [], 0.
for codec, policy in (("S", "F"), ("S", "G"), ("H", "F"), ("H", "G")):
    tag = f"{codec}-{policy}-seed202"
    net = model(f"run/{tag}/final-state.npz", 202)
    actual = run.truth_table(net, codec, c.STAGES[-1])
    archived = zj(f"run/{tag}/final-truth.json")
    for a, b in zip(actual, archived, strict=True):
        for key in ("Q", "target", "generated", "whole_correct", "overflow", "first_error_position_zero_based"):
            assert a[key] == b[key], (tag, key)
        for x, y in zip(a["teacher_forcing"], b["teacher_forcing"], strict=True):
            assert x["prediction"] == y["prediction"]
            delta = float(np.max(np.abs(np.array(x["logits"]) - np.array(y["logits"]))))
            max_logit_diff = max(max_logit_diff, delta)
            np.testing.assert_allclose(x["logits"], y["logits"], atol=1e-5, rtol=1e-6)
        inference_rows += 1
    inference_examples.append({"student": tag, "whole_correct": sum(r["whole_correct"] for r in actual), "of": len(actual)})

growth_samples = []
for codec, seed, target_index in (("S", 202, 1), ("H", 101, 2), ("S", 202, 3), ("H", 202, 3)):
    tag = f"{codec}-G-seed{seed}"
    previous, target = c.STAGES[target_index - 1], c.STAGES[target_index]
    net = model(f"run/{tag}/{previous.name}/state-100.npz", seed)
    probes = run.raw_probes(codec, previous)
    event = run.grow_verified(net, target.L, target.H, probes, "readonly_audit")
    assert run.ref.equal_state(net.state(), state(f"run/{tag}/{target.name}/state-0.npz"))
    published = zj(f"run/{tag}/{target.name}/growth.json")
    growth_samples.append({"student": tag, "target_stage": target.name,
        "probes": len(probes), "max_same_raw_logit_difference": event["max_same_raw_logit_difference"],
        "published_difference": published["max_same_raw_logit_difference"],
        "old_arrays_moments_birth_t_exact": True, "result_equals_published_entry_state": True})

after = {str(f.relative_to(p)): digest(f.read_bytes()) for f in p.rglob("*") if f.is_file()}
assert before == after
assert not forbidden_calls
largest = max(growth_records, key=lambda r: r[2]["max_same_raw_logit_difference"])
report = {
    "schema": "PRO-P035-READONLY-REVIEW-v1",
    "author": "ChatGPT Pro",
    "status": "passed_no_findings_in_scope",
    "source": {
        "codex_commit": CODEX_COMMIT,
        "package": "experiments/spiral_neural/20261112_p035",
        "source_freeze_sha256": FREEZE_SHA,
        "package_manifest_sha256": PACKAGE_MANIFEST_SHA,
    },
    "reproduction": {
        "working_directory": "experiments/spiral_neural/20261113_pro_p035_review",
        "command": "python -B audit_p035.py --out results.json",
        "output": "results.json",
        "source_package_relative_to_review": "../20261112_p035",
    },
    "audit_script_sha256": digest(Path(__file__).read_bytes()),
    "scope": "Bounded read-only public artifact audit; four final checkpoint inferences and four growth copies; zero training/replay.",
    "python": platform.python_version(),
    "numpy": np.__version__, "source_freeze_hashes_verified": len(freeze["sources_sha256"]),
    "package_file_hashes_verified": len(package["files"]), "zip_entry_hashes_verified": len(zmap),
    "engineering_freeze_hashes_verified": 3, "published_freeze_precedes_manifest": True,
    "courses_regenerated": len(courses), "student_exposure_ledgers_verified": 12,
    "student_interface_ledgers_verified": 12, "stage_budgets_verified": 60,
    "budget_rows": budgets, "actual_primary_totals_from_stage_summaries": dict(totals),
    "archived_final_truth_rows_reaggregated": len(all_truth),
    "archived_final_train": [sum(r["whole_correct"] for r in all_truth if r["subset"] == "train"), sum(r["subset"] == "train" for r in all_truth)],
    "archived_final_operand_heldout": [sum(r["whole_correct"] for r in all_truth if r["subset"] != "train"), sum(r["subset"] != "train" for r in all_truth)],
    "interactions": interactions, "paired_initial_states_verified": 6,
    "seed202_initializations_recreated_without_updates": 2,
    "actual_final_checkpoint_rows": inference_rows, "actual_final_checkpoint_examples": inference_examples,
    "max_actual_vs_archived_TF_logit_difference": max_logit_diff,
    "actual_growth_copy_checks": growth_samples,
    "largest_published_growth_difference": {"student": largest[0], "stage": largest[1], "difference": largest[2]["max_same_raw_logit_difference"]},
    "answer_role_exposure": response_exposure,
    "gradient_update_calls": 0, "repo_package_unchanged": True,
    "new_students": 0, "new_training_target_updates": 0, "full_training_replays": 0,
    "forbidden_methods": ["Model.step", "Model.lesson", "Model.loss_grad"],
    "NVIDIA_calls_this_review": 0, "findings_in_scope": [],
    "limitations": ["Full target traces and intermediate quarter-state arrays are not all public; no independent full training replay is claimed.", "Published preregistration timestamps are checked for internal order, not independently authenticated.", "Input-codec by capacity-timing and shared response grammar only; equal MAC intentionally gives G more exposure."]
}
text = json.dumps(report, ensure_ascii=False, indent=2)
if args.out:
    assert not args.out.resolve().is_relative_to(p), "Report must stay outside the reviewed P035 package"
    args.out.write_text(text + "\n", encoding="utf-8")
print(text)
