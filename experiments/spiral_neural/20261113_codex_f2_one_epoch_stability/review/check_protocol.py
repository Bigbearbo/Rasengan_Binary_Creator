"""Zero-NN historical pairing checks. Never imports learner/runner or calls an optimizer."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def word(value):
    return format(value, "05b") + "0"


def true_answer(row):
    a, b = divmod(row["pair_id"], 30)
    assert 0 <= a < 30 and 0 <= b < 30
    cls = row["class"]
    return {"E1": word(a), "E2": word(a) + word(b),
            "F1": word(31 - a), "F2": word(31 - a) + word(31 - b)}[cls] + "S"


def correct_map(generation):
    rows = generation["rows"]
    assert len(rows) == 3600
    result = {}
    for row in rows:
        pid, cls, qid = row["pair_id"], row["class"], row["question_id"]
        expected = ["E1", "E2", "F1", "F2"].index(cls) * 900 + pid
        assert qid == expected and qid not in result
        good = row["tokens"] == true_answer(row) and not row["cap_exhausted"] and not row["context_exhausted"]
        assert type(row["whole_correct"]) is bool and row["whole_correct"] == good
        result[qid] = (cls, good)
    assert set(result) == set(range(3600))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    parent = args.parent_root.resolve()
    public = parent / "publication/final/public"
    manifest_path = public / "publication-manifest.json"
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    assert sha(manifest_raw) == "193d2c49ccf052c55db808014cb837f80204789fc93388fd3955c4205720e9a4"
    receipt = read(parent / "execution-receipt.json")
    publication = read(parent / "publication-receipt.json")
    assert receipt["status"] == "exit0" and receipt["exit_code"] == 0
    assert publication["result_commit"] == "f9d41eb28f067a222682e02c85c7371297bddde9"
    assert receipt["manifest_sha256"] == manifest["manifest_sha256"] == "b8d385db584aec294f5363556f045aecb3ceb8864dc20f4816c30bc591426d95"
    inventory = manifest["complete_science_inventory"]
    checked = {}
    archive_hashes = {}

    def selected(rel):
        raw = (parent / "science" / rel).read_bytes()
        meta = inventory[rel]
        assert len(raw) == meta["bytes"] and sha(raw) == meta["sha256"]
        member = "science/" + rel
        matches = [(name, m, m["members"][member]) for name, m in manifest["archives"].items() if member in m["members"]]
        assert len(matches) == 1
        name, archive_meta, member_meta = matches[0]
        archive = public / name
        if name not in archive_hashes:
            archive_raw = archive.read_bytes()
            assert len(archive_raw) == archive_meta["bytes"] and sha(archive_raw) == archive_meta["sha256"]
            archive_hashes[name] = {"sha256": archive_meta["sha256"], "Git_blob": archive_meta["Git_blob"]}
        with zipfile.ZipFile(archive) as z:
            info = z.getinfo(member)
            assert format(info.CRC, "08x") == member_meta["CRC32"]
            assert info.file_size == member_meta["bytes"]
            assert z.read(member) == raw
        assert member_meta["sha256"] == sha(raw)
        checked[rel] = {"bytes": len(raw), "sha256": sha(raw), "archive": name,
                        "member": member, "CRC32": member_meta["CRC32"], "Git_blob": member_meta["Git_blob"]}
        return raw

    rows = []
    for seed, epoch, start_t in [(101, 19, 981000), (202, 22, 1192500), (303, 19, 1125900)]:
        curve = json.loads(selected(f"seed{seed}/curve.json"))
        full_epochs = [x["epoch"] for x in curve if all(s["whole_correct"] == 900 for s in x["scores"].values())]
        assert min(full_epochs) == epoch
        first, nxt = [next(x for x in curve if x["epoch"] == e) for e in (epoch, epoch + 1)]
        assert first["global_updates"] == start_t and nxt["global_updates"] == start_t + 36000
        before = correct_map(json.loads(selected(f"seed{seed}/generation-{epoch:03}.json")))
        after = correct_map(json.loads(selected(f"seed{seed}/generation-{epoch+1:03}.json")))
        assert all(good for _, good in before.values())
        lost = {cls: sorted(q for q, (c, good) in before.items() if c == cls and good and not after[q][1])
                for cls in ("E1", "E2", "F1", "F2")}
        assert all(len(lost[c]) == nxt["churn"]["by_class"][c]["previous_correct_to_wrong"] for c in lost)
        selected(f"seed{seed}/state-{epoch:03}.npz")
        selected(f"seed{seed}/state-{epoch+1:03}.npz")
        rows.append({"seed": seed, "first_full_epoch": epoch, "historical_next_epoch": epoch + 1,
                     "start_t_from_historical_curve": start_t, "new_end_t": start_t + 36000,
                     "historical_eta003_lost_by_class": {c: len(v) for c, v in lost.items()},
                     "historical_eta003_lost_total": sum(map(len, lost.values())),
                     "historical_eta003_lost_QIDs": lost})
    assert [r["historical_eta003_lost_total"] for r in rows] == [7, 5, 52]
    report = {
        "schema": "f2-stability-design-review-v1", "status": "ready_for_frozen_code_gate", "date": "2026-11-13",
        "reviewer_NN_forward_calls": 0, "reviewer_optimizer_updates": 0, "new_student_scores_read": False,
        "parent_result_commit": publication["result_commit"], "parent_publication_manifest_sha256": sha(manifest_raw),
        "parent_execution_receipt_sha256": sha((parent / "execution-receipt.json").read_bytes()),
        "parent_protocol_sha256": receipt["source_hashes"]["protocol.json"],
        "historical_checks": rows, "selected_parent_files": checked, "selected_public_archives": archive_hashes,
        "provenance_scope": "Actual local public ZIP bytes/memberCRC/rawscience verified against pinned publication manifest and recorded publication receipt; no fresh remote Git operation or optimizer replay.",
        "new_budget_arithmetic": {"targets_each_seed": 36000, "seeds": 3, "total_new_updates": 108000,
                                  "MAC_each_update": 21056, "new_training_MAC": 108000 * 21056,
                                  "new_final_TF_calls": 108000, "new_final_TF_MAC": 108000 * 10432,
                                  "formal_optimizer_replay": 0},
        "required_freeze_conditions": [
            "Same exact starting full learning state and same historical next-epoch36000target order; all ModelAST nodes unchanged except the one step learning-rate constant .003->.001.",
            "All3baseline integrity gates pass before any new optimizer; probe may change only inference counters, with new costs separate from inherited counters.",
            "Per-seed primary hypothesis new_lost<old_lost is strict; ties are not support. Preserve all3 results and paired QID sets, not only a pooled/best seed result.",
            "Fixed one epoch only, no extension, reselection, rate tuning, extra seeds or updates; parent formal endpoints remain historical.",
            "Public portable inputs must contain selected complete states, exact selected orders, bank/teacher protocol and historical generation/control-state evidence with rawSHA/memberCRC lineage."
        ],
        "interpretation_limits": [
            "First-full checkpoint selection is conditioned on previously observed training results. This is a posthoc choice of3fixed starting states, preregistered only before new eta001 outcomes.",
            "One-epoch paired finite-bank retention comparison, not proof of long-term stability, globally superior learning rate, fresh cohort or blind generalization.",
            "Historical eta003 control is reused public evidence, not a new trained student and not an independently recomputed optimizer trajectory.",
            "RawNumPy postrun inference can verify saved endpoints/TF and token-derived metrics, not unrecorded per-target gradients or weights."
        ],
        "gate_scope": "Design/history ready only. New code, manifest, portable inputs, engineering counters and source freeze are pending; no formal execution approval implied.",
        "blocking_design_findings": []
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({"status": report["status"], "historical_lost": [r["historical_eta003_lost_total"] for r in rows],
                      "public_files_checked": len(checked), "public_archives_checked": len(archive_hashes),
                      "new_updates_budget": 108000, "new_training_MAC": 2274048000, "NN_operations": 0,
                      "report_sha256": sha(args.out.read_bytes())}))


if __name__ == "__main__":
    main()
