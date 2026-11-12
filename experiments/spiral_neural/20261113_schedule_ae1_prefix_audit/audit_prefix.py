#!/usr/bin/env python3
"""AE1 archived teacher-prefix versus self-prefix diagnostic (NO NEW NN RUN).

Use the *unchanged* JSON files published in PR #19:
  python audit_prefix.py --evaluation experiments/spiral_neural/20261113_pro_ae1_learning/evaluation_summary.json --results experiments/spiral_neural/20261113_pro_ae1_learning/results_summary.json
The --allow-fixture flag is only for arithmetic unit tests, not evidence verification.
"""
import argparse
import hashlib
import json
from pathlib import Path

EVAL_BLOB_SHA1 = "929fb940098259ce3b8c75c4cdb3a3aae1b9bb14"
RESULT_BLOB_SHA1 = "3ba95dce72a82de83977bfd74c1085787ad8ab73"
SEEDS = (101, 202, 303)
PHASES = (4, 5)
RS = (1, 2, 3, 4)

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()

def load_json(path: Path, expected_sha: str, allow_fixture=False):
    raw = path.read_bytes()
    observed = git_blob_sha(raw)
    if not allow_fixture and observed != expected_sha:
        raise ValueError(f"{path}: Git blob SHA mismatch: {observed} != {expected_sha}")
    return json.loads(raw)

def audit(evaluation, reported=None):
    found = {}
    for cp in evaluation["checkpoints"]:
        key = cp["seed"], cp["phase"]
        if key not in {(s, p) for s in SEEDS for p in PHASES}:
            continue
        if key in found:
            raise ValueError(f"duplicate checkpoint {key}")
        found[key] = cp
    if set(found) != {(s, p) for s in SEEDS for p in PHASES}:
        raise ValueError("missing specified seed/phase checkpoints")
    report_seeds = {v["seed"]: v for v in reported["students"]} if reported is not None else {}
    if reported is not None and set(report_seeds) != set(SEEDS):
        raise ValueError("reported seed set mismatch")
    output = []
    for phase in PHASES:
        for r in RS:
            rows = [found[(seed, phase)]["metrics"]["by_split"]["test"]["by_N_r"][f"4/{r}"] for seed in SEEDS]
            for seed, row in zip(SEEDS, rows):
                den = 60 * 5 * r
                if row["total"] != 60 or row["tf_info_total"] != den or row["free_info_total"] != den:
                    raise ValueError(f"bad sample size at phase{phase}/r{r}/seed{seed}")
                for key in ("tf_info_correct", "free_info_correct"):
                    if not 0 <= row[key] <= den:
                        raise ValueError(f"invalid {key} at phase{phase}/r{r}/seed{seed}")
                if not 0 <= row["whole_correct"] <= row["STOP_position_correct"] <= 60:
                    raise ValueError(f"whole/stop inconsistency at phase{phase}/r{r}/seed{seed}")
                if phase == 5 and reported is not None:
                    src = report_seeds[seed]["final"]["final_test_by_N_r"][f"4/{r}"]
                    for key in ("tf_info_correct", "free_info_correct", "whole_correct"):
                        if src[key] != row[key]:
                            raise ValueError(f"evaluation/results mismatch seed{seed}/r{r}/{key}")
            bits = sum(row["tf_info_total"] for row in rows)
            tf = sum(row["tf_info_correct"] for row in rows)
            free = sum(row["free_info_correct"] for row in rows)
            output.append({
                "phase":phase, "N":4, "r":r, "seeds":list(SEEDS),
                "responses":sum(row["total"] for row in rows),
                "bits":bits, "tf_correct":tf, "free_correct":free,
                "teacher_accuracy":round(tf/bits,9),
                "free_accuracy":round(free/bits,9),
                "gap_percentage_points":round(100*(tf-free)/bits,6),
                "whole_correct":sum(row["whole_correct"] for row in rows),
                "stop_correct":sum(row["STOP_position_correct"] for row in rows)
            })
    return {
        "id":"AE1-20261113-archived-prefix-audit",
        "profile":"SLE-AE1-n5-v1",
        "factor":"inference prefix conditioning: correct teacher prefix vs self-generated prefix",
        "scope":"saved aggregate readout only; no new forward, optimizer, or heldout test",
        "evaluation_blob_sha1":EVAL_BLOB_SHA1, "results_blob_sha1":RESULT_BLOB_SHA1,
        "rows":output, "new_neural_forward":0, "optimizer_updates":0, "new_neural_MAC":0
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--evaluation",type=Path,required=True)
    parser.add_argument("--results",type=Path)
    parser.add_argument("--allow-fixture",action="store_true",
                        help="ARITHMETIC UNIT TEST ONLY; filename must end fixture.json")
    args=parser.parse_args()
    if args.allow_fixture and not args.evaluation.name.endswith("fixture.json"):
        parser.error("--allow-fixture requires filename ending fixture.json")
    ev=load_json(args.evaluation,EVAL_BLOB_SHA1,args.allow_fixture)
    rs=None if args.results is None else load_json(args.results,RESULT_BLOB_SHA1,args.allow_fixture)
    print(json.dumps(audit(ev,rs),ensure_ascii=False,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
