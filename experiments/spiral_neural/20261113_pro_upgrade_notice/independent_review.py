"""Bounded independent UR1 mutation review; no training or NN claims."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

from notice_codec import (
    Branch, FIXTURE_PATHS, Node, NoticeError, NoticeReceiver, PROFILE_ID,
    branch_at, encode_notice, fixture_tree,
)


def review() -> dict:
    tree = fixture_tree()
    rejected = Counter()
    accepted = []
    failures = []
    total = atomic_rejections = valid_commits = 0
    for source_path in FIXTURE_PATHS:
        source = branch_at(tree, source_path)
        question = encode_notice(source_path, source.n + 1, tree)
        for index in range(len(question)):
            total += 1
            changed = question[:index] + str(1 - int(question[index])) + question[index + 1:]
            receiver = NoticeReceiver(tree)
            before = deepcopy(receiver.tree)
            case = {"source_address": list(source_path), "flipped_bit_index": index}
            try:
                receipt = receiver.receive_notice(changed, profile_id=PROFILE_ID)
            except NoticeError as error:
                rejected[error.code] += 1
                if receiver.tree == before and receiver.applied_transitions == 0:
                    atomic_rejections += 1
                else:
                    failures.append({**case, "failure": "rejection_changed_state"})
                continue
            except Exception as error:
                failures.append({**case, "failure": type(error).__name__, "detail": str(error)})
                continue

            addressed_before = branch_at(before, receipt.address)
            grows_once = receipt.target_n == addressed_before.n + 1
            expected_status = "upgraded" if grows_once else "already_current"
            state_ok = receipt.status == expected_status
            state_ok &= receipt.target_n in (addressed_before.n, addressed_before.n + 1)
            state_ok &= receiver.applied_transitions == int(grows_once)
            for path in FIXTURE_PATHS:
                expected = branch_at(before, path)
                if grows_once and path == receipt.address:
                    expected = replace(expected, n=receipt.target_n)
                state_ok &= branch_at(receiver.tree, path) == expected
            accepted.append({**case, "received_address": list(receipt.address),
                             "target_n": receipt.target_n, "status": receipt.status,
                             "state_change_correct": state_ok, "mutated_question": changed})
            valid_commits += int(state_ok)
            if not state_ok:
                failures.append({**case, "failure": "accepted_frame_changed_wrong_state"})

    shared = Node(Branch("shared_data", "data", 4, 1))
    alias_tree = Node(children={1: shared, 2: shared})
    cycle_tree = Node()
    cycle_tree.children[0] = cycle_tree
    non_tree_inputs = []
    for label, invalid_tree in (("two_paths_share_one_node", alias_tree),
                                ("node_points_to_itself", cycle_tree)):
        try:
            NoticeReceiver(invalid_tree)
        except NoticeError as error:
            passed = error.code == "NOT_A_TREE"
            non_tree_inputs.append({"case": label, "error": error.code, "passed": passed})
        except Exception as error:
            passed = False
            non_tree_inputs.append({"case": label, "error": type(error).__name__, "passed": False})
        else:
            passed = False
            non_tree_inputs.append({"case": label, "error": None, "passed": False})
        if not passed:
            failures.append({"case": label, "failure": "non_tree_input_not_rejected_as_NOT_A_TREE"})

    here = Path(__file__).resolve().parent
    return {
        "profile_id": PROFILE_ID,
        "author": "ChatGPT Pro / independent delegated review",
        "scope": "Exhaustive single-bit changes to eight fixture upgrade frames; alias/cycle rejection.",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python -B independent_review.py --results independent_review.json",
        "working_directory": "experiments/spiral_neural/20261113_pro_upgrade_notice",
        "python_version": platform.python_version(),
        "source_sha256": {name: hashlib.sha256((here / name).read_bytes()).hexdigest()
                          for name in ("notice_codec.py", "independent_review.py")},
        "single_bit_mutations": {
            "fixture_frames": len(FIXTURE_PATHS), "total": total,
            "rejected": sum(rejected.values()), "atomic_rejections": atomic_rejections,
            "rejected_by_error": dict(sorted(rejected.items())),
            "valid_accepted": len(accepted), "accepted_state_checks_passed": valid_commits,
            "accepted_cases": accepted,
        },
        "non_tree_inputs": non_tree_inputs,
        "failures": failures,
        "passed": not failures,
        "limitations": [
            "A single-bit address change can form a valid different notice; UR1 has no checksum.",
            "This checks only these fixture frames and single-bit flips, not all possible corruptions.",
            "Shared width state must use one canonical address; DAG aliases and cycles are unsupported.",
            "Codec checks do not establish NN learning, useful transfer, or growth efficiency.",
        ],
        "nvidia": {"status": "skipped_unavailable", "calls": 0,
                   "reason": "No configured NVIDIA worker tool is available in this session."},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path(__file__).with_name("independent_review.json"))
    args = parser.parse_args()
    report = review()
    args.results.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "single_bit_mutations": {
        key: value for key, value in report["single_bit_mutations"].items() if key != "accepted_cases"
    }, "non_tree_inputs": report["non_tree_inputs"], "failures": report["failures"]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
