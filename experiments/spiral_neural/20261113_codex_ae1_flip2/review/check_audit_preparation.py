"""Zero-NN preparation check for the self-contained independent post-auditor."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("prepared_f2_independent_audit", HERE / "audit_post.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def forbidden(*args, **kwargs):
    raise AssertionError("No NumPy model forward allowed in audit preparation")


module.Forward.__call__ = forbidden
manifest, rows, parents, raw_parents, orders = module.inputs(SimpleNamespace(
    manifest=HERE.parent / "prereg/manifest.json",
    code_root=ROOT / "outputs/ae1-flip2",
))
tiny = [rows[offset] for offset in (0, 900, 1800, 2700)]


def outputs(tasks, maker):
    return [{"question_id": row["question_id"], "tokens": maker(row), "cap_exhausted": False, "context_exhausted": False} for row in tasks]


for maker, kind, termination in (
    (lambda row: row["A"] + "S", "none", "STOP_at_expected_position"),
    (lambda row: "S", "early_STOP", "early_STOP"),
    (lambda row: row["A"], "missing_token", "no_STOP"),
    (lambda row: row["A"] + "S0", "extra_token", "tokens_after_STOP"),
    (lambda row: row["A"] + "0S", "STOP_expected_bit_emitted", "late_STOP"),
):
    got = module.independent_readout(tiny, outputs(tiny, maker))
    assert got["metrics"]["extra_forward_calls"] == got["churn"]["extra_forward_calls"] == 0
    for item in got["metrics"]["per_question"]:
        assert item["first_error_kind"] == kind and item["termination_kind"] == termination
        if kind == "early_STOP":
            assert item["first_error_position_zero_based"] == 0
            assert not item["words"][0]["complete6_correct"]
f2 = [rows[2700]]
fixture = outputs(tiny, lambda row: str(1 - int(row["A"][0])) + row["A"][1:] + "S")
got = module.independent_readout(tiny, fixture)["metrics"]["per_question"][-1]
assert not got["words"][0]["complete6_correct"] and got["words"][1]["complete6_correct"]
pair_rows = [rows[offset + pair] for offset in (0, 900, 1800, 2700) for pair in (0, 1)]
previous = outputs(pair_rows, lambda row: row["A"] + "S" if row["pair_id"] == 0 else "S")
current = outputs(pair_rows, lambda row: "S" if row["pair_id"] == 0 else row["A"] + "S")
churn = module.independent_readout(pair_rows, current, previous, "baseline")["churn"]
for counts in churn["by_class"].values():
    assert counts == {"questions": 2, "previous_correct_to_wrong": 1, "previous_wrong_to_correct": 1, "retained_correct": 0, "retained_wrong": 0}
result = {
    "status": "passed",
    "auditor_sha256": module.sha(HERE / "audit_post.py"),
    "manifest_sha256": module.APPROVED,
    "portable_members": 13,
    "independent_parent_states": len(parents),
    "independent_questions": len(rows),
    "independent_frozen_permutations": sum(len(order) for order in orders.values()),
    "pure_metric_fixture_outputs": 24,
    "QID_swap_classes": 4,
    "actual_audit_attempts": 0,
    "model_forward_calls": 0,
    "optimizer_calls": 0,
    "note": "Only independent frozen-input parsing and pure string readouts were exercised; no scientific checkpoint generation or learner/driver imports.",
}
with (HERE / "audit-preparation.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps(result, separators=(",", ":")))
