"""Metadata-only closure attestation after actual audit exec tool returned exit0."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(args):
    assert args.observed_audit_session == 60993 and args.observed_exit_code == 0
    path = HERE / "audit-execution-receipt.json"
    receipt = read(path)
    assert receipt["status"] == "running" and receipt["audit_exec_session_id"] == 60993
    result, details, cost = (read(HERE / name) for name in ("post-run.json", "post-run-details.json", "audit-cost.json"))
    assert result["status"] == details["status"] == cost["status"] == "passed"
    assert result["formal_session"] == receipt["formal_training_session_id"] == 36593
    assert result["manifest_sha256"] == receipt["manifest_sha256"]
    assert cost["attempts"] == result["audit_attempt_count"] == 1
    assert cost["script_sha256"] == sha(HERE / "audit_post.py") == receipt["script_sha256"]
    assert cost["forward_calls"] == result["audit_extra_forward_calls"] == 4072688
    assert cost["dense_MAC"] == result["audit_extra_dense_MAC"] == 42486281216
    assert cost["optimizer_calls"] == cost["new_students"] == cost["external_model_calls"] == 0
    assert result["actual_full_replay_seeds"] == [] and result["actual_primary_epochs_verified"] == 107
    assert len(details["numeric_proof_refs"]) == result["numeric_proof_count"] == 113
    assert result["receipt_sha256"] == receipt["formal_execution_receipt_sha256"] == sha(HERE.parent / "execution-receipt.json")
    receipt.update({
        "status": "exit0",
        "audit_exit_code": 0,
        "audit_process_closed": True,
        "closure_evidence": "Reviewer received the actual write_stdin tool return exit_code0 for exec session60993; no retry or second numerical audit.",
        "closure_attestation_UTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "audit_wall_seconds": cost["seconds"],
        "audit_forward_calls": cost["forward_calls"],
        "audit_dense_MAC": cost["dense_MAC"],
        "audit_calls_by_phase": cost["calls_by_phase"],
        "actual_primary_epochs_verified": 107,
        "free_questions_verified": result["total_baseline_and_mixed_free_questions_verified"],
        "final_TF_targets_verified": result["final_TF_logits_probabilities_CE_verified"],
        "science_files_verified": len(details["science_file_inventory"]),
        "science_NPZ_verified": result["full_science_NPZ_verified"],
        "numeric_proofs": 113,
        "all_confirmed_four_class_fit": result["all_confirmed_four_class_fit"],
        "note": "Audit PASS means artifact/numerical agreement. It does not change the two epoch-cap model failures or imply optimizer replay.",
        "post_run_sha256": sha(HERE / "post-run.json"),
        "post_run_details_sha256": sha(HERE / "post-run-details.json"),
        "audit_cost_sha256": sha(HERE / "audit-cost.json"),
        "closure_helper_sha256": sha(Path(__file__)),
        "closure_helper_model_forward_calls": 0,
        "closure_helper_optimizer_calls": 0,
    })
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, separators=(",", ":")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-audit-session", type=int, required=True)
    parser.add_argument("--observed-exit-code", type=int, required=True)
    main(parser.parse_args())
