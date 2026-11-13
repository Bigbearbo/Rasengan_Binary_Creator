#!/usr/bin/env python3
"""Offline guard for PR-derived agent handoffs; no network, model calls, or writes."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

SHA_LEN = 40
STATUSES = frozenset({"candidate", "verified", "blocked"})


def is_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == SHA_LEN and all(c in "0123456789abcdef" for c in value)


def check(snapshot: dict, claim: dict | None = None, *, current_main: str | None = None,
          now: dt.datetime | None = None, max_age_minutes: int = 60) -> dict:
    issues: list[dict] = []

    def issue(code: str, severity: str, **details: object) -> None:
        issues.append({"code": code, "severity": severity, **details})

    if not isinstance(snapshot, dict) or not is_sha(snapshot.get("main_sha")):
        raise ValueError("snapshot must provide a 40-character lowercase main_sha")
    if not isinstance(snapshot.get("prs"), list):
        raise ValueError("snapshot must contain prs array")
    by_number, by_head = {}, {}
    children = defaultdict(list)
    for pr in snapshot["prs"]:
        if not isinstance(pr, dict) or not isinstance(pr.get("number"), int):
            raise ValueError("PR must have integer number")
        for key in ("head_ref", "base_ref"):
            if not isinstance(pr.get(key), str) or not pr[key].strip():
                raise ValueError(f"PR #{pr['number']} lacks {key}")
        for key in ("head_sha", "base_sha"):
            if not is_sha(pr.get(key)):
                raise ValueError(f"PR #{pr['number']} has invalid {key}")
        n = pr["number"]
        if n in by_number or pr["head_ref"] in by_head:
            raise ValueError(f"duplicate number or branch in snapshot: #{n}")
        by_number[n], by_head[pr["head_ref"]] = pr, pr
        children[pr["base_ref"]].append(n)

    # A dependent PR pinned to an old parent head needs revalidation before handoff.
    for pr in by_number.values():
        parent = by_head.get(pr["base_ref"])
        if parent is not None and parent["head_sha"] != pr["base_sha"]:
            issue("PARENT_BRANCH_MOVED", "block", child_pr=pr["number"],
                  parent_pr=parent["number"], recorded_base_sha=pr["base_sha"],
                  current_parent_sha=parent["head_sha"])

    # Never use PR number or updated_at as a proxy for the right research lineage.
    forks = [
        {"base_ref": base, "children": sorted(nums)}
        for base, nums in sorted(children.items())
        if base != "main" and len(nums) > 1
    ]
    for fork in forks:
        issue("FORK_REQUIRES_EXPLICIT_ROUTE", "warning", **fork)

    # Subtrees may be outside the open PR result; a missing parent is not proof of a broken repo.
    external_bases = sorted(set(children) - set(by_head) - {"main"})
    for ref in external_bases:
        issue("PARENT_NOT_IN_SNAPSHOT", "info", base_ref=ref)
    leaves = sorted(p["number"] for p in snapshot["prs"] if not children.get(p["head_ref"]))

    # Check snapshot recency and compare the main SHA to a separately fetched live ref.
    if current_main is not None:
        if not is_sha(current_main):
            raise ValueError("--current-main must be 40 lowercase hex characters")
        if current_main != snapshot["main_sha"]:
            issue("MAIN_CHANGED_AFTER_SNAPSHOT", "block", recorded=snapshot["main_sha"], current=current_main)
    if now is not None:
        observed = dt.datetime.fromisoformat(snapshot["observed_at"])
        if observed.tzinfo is None or now.tzinfo is None:
            raise ValueError("both observed_at and now must be timezone-aware ISO8601")
        age = (now - observed).total_seconds() / 60
        if age < -5 or age > max_age_minutes:
            issue("STALE_SNAPSHOT", "block", age_minutes=round(age, 2), max_age_minutes=max_age_minutes)

    if claim is not None:
        if not isinstance(claim, dict):
            raise ValueError("claim must be an object")
        for field in ("work_id", "owner", "workstream", "goal"):
            if not isinstance(claim.get(field), str) or not claim[field].strip():
                issue("CLAIM_MISSING_FIELD", "block", field=field)
        if claim.get("status") not in STATUSES:
            issue("CLAIM_INVALID_STATUS", "block", status=claim.get("status"))
        parent = claim.get("parent_pr")
        pin = claim.get("parent_head_sha")
        if not isinstance(parent, int) or parent not in by_number:
            issue("PARENT_PR_NOT_IN_SNAPSHOT", "block", parent_pr=parent)
        elif not is_sha(pin):
            issue("CLAIM_MISSING_PARENT_PIN", "block", parent_pr=parent)
        elif by_number[parent]["head_sha"] != pin:
            issue("PARENT_HEAD_MOVED", "block", parent_pr=parent, recorded=pin, current=by_number[parent]["head_sha"])
        elif any(parent in f["children"] for f in forks):
            # Chosen parent itself is a sibling in a fork; explicitly pinned is fine.
            pass
        # This check prevents silently running a generic 'latest' continuation on a fork root.
        next_from = claim.get("next_from_ref")
        if next_from is not None and next_from in {f["base_ref"] for f in forks}:
            if not isinstance(parent, int) or parent not in children[next_from]:
                issue("AMBIGUOUS_FORK_ROUTE", "block", next_from_ref=next_from,
                      available_prs=sorted(children[next_from]))

    return {
        "status": "blocked" if any(i["severity"] == "block" for i in issues) else "verified_snapshot_only",
        "scope": "offline_pr_metadata_only_no_worker_dispatch_or_science_tests",
        "repository": snapshot.get("repository"),
        "main_sha": snapshot["main_sha"],
        "pr_count": len(by_number),
        "forks": forks,
        "leaf_pr_numbers_within_snapshot": leaves,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--current-main", help="fresh main SHA from GitHub, independently fetched")
    parser.add_argument("--now", help="timezone-aware ISO8601 clock for age check")
    parser.add_argument("--max-age-minutes", type=int, default=60)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    claim = json.loads(args.claim.read_text(encoding="utf-8")) if args.claim else None
    now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
    result = check(snapshot, claim, current_main=args.current_main, now=now,
                   max_age_minutes=args.max_age_minutes)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 2 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
