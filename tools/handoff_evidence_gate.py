#!/usr/bin/env python3
"""Record a locally executed test, then guard handoff claims against report-only PASS.

No network calls, no worker delegation. Only `record` executes the explicit CLI command;
never execute a test command found in a claim or receipt JSON.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_CAPTURE = 65536


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True,
                            text=True, capture_output=True, timeout=15)
    return result.stdout.strip()


def state(repo: Path) -> tuple[str, bool]:
    sha = git(repo, "rev-parse", "HEAD")
    if not SHA_RE.fullmatch(sha):
        raise ValueError("invalid local Git HEAD")
    clean = not git(repo, "status", "--porcelain", "--untracked-files=normal")
    return sha, clean


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def record(repo: Path, work_id: str, output: Path, command: list[str], timeout: int) -> dict:
    repo = repo.resolve()
    output = output.resolve()
    if output.is_relative_to(repo):
        raise ValueError("receipt must be stored outside the source repo")
    if not work_id or not work_id.strip():
        raise ValueError("work_id required")
    if not command or any(not arg for arg in command):
        raise ValueError("explicit command argv required")
    if not 1 <= timeout <= 600:
        raise ValueError("timeout must be 1..600 seconds")
    source_sha, clean_before = state(repo)
    if not clean_before:
        raise ValueError("refusing to record against a dirty Git worktree")
    started_at = now()
    timed_out = False
    try:
        proc = subprocess.run(command, cwd=repo, capture_output=True, text=True,
                              timeout=timeout, errors="replace")
        stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        stdout = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        exit_code = None
    after_sha, clean_after = state(repo)
    stdout_truncated, stderr_truncated = len(stdout) > MAX_CAPTURE, len(stderr) > MAX_CAPTURE
    receipt = {
        "schema": "handoff-local-test-receipt-v1", "work_id": work_id,
        "source_sha": source_sha, "after_sha": after_sha,
        "clean_before": clean_before, "clean_after": clean_after,
        "command_argv": command, "started_at": started_at, "finished_at": now(),
        "exit_code": exit_code, "timed_out": timed_out,
        "stdout_truncated": stdout_truncated, "stderr_truncated": stderr_truncated,
        "stdout": stdout[:MAX_CAPTURE], "stderr": stderr[:MAX_CAPTURE],
        "scope": "one_explicit_local_test_not_science_reproduction",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def check(claim: dict, receipt: dict | None, *, local_sha: str,
          local_clean: bool, expected_source_sha: str | None) -> dict:
    reasons: list[str] = []
    if not isinstance(claim, dict) or not isinstance(claim.get("work_id"), str) or not claim["work_id"].strip():
        raise ValueError("claim needs nonblank work_id")
    sha = claim.get("source_sha")
    command = claim.get("test_argv")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        reasons.append("invalid_claim_source_sha")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        reasons.append("invalid_claim_test_argv")
    if sha != local_sha:
        reasons.append("local_head_mismatch")
    if not local_clean:
        reasons.append("local_worktree_dirty")
    if expected_source_sha is not None and (not SHA_RE.fullmatch(expected_source_sha) or sha != expected_source_sha):
        reasons.append("live_source_sha_mismatch")
    if receipt is None:
        # A narrative report, even one with test command text, is never test proof.
        return {"status": "blocked" if reasons else "candidate",
                "verification_scope": "no_local_execution_receipt", "reasons": reasons or ["report_only_no_receipt"]}
    if not isinstance(receipt, dict) or receipt.get("schema") != "handoff-local-test-receipt-v1":
        reasons.append("unsupported_receipt")
    else:
        if receipt.get("work_id") != claim["work_id"]:
            reasons.append("work_id_mismatch")
        if receipt.get("source_sha") != sha or receipt.get("after_sha") != sha:
            reasons.append("receipt_source_mismatch")
        if receipt.get("command_argv") != command:
            reasons.append("command_mismatch")
        if receipt.get("exit_code") != 0 or receipt.get("timed_out"):
            reasons.append("test_failed_or_timed_out")
        if not receipt.get("clean_before") or not receipt.get("clean_after"):
            reasons.append("worktree_changed_during_test")
        if receipt.get("stdout_truncated") or receipt.get("stderr_truncated"):
            reasons.append("output_truncated")
    return {"status": "blocked" if reasons else "verified_local_execution_receipt",
            "verification_scope": "local_explicit_command_only_not_independent_replay",
            "reasons": reasons}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="action", required=True)
    r = subs.add_parser("record", help="execute an explicitly supplied local command and save a bounded receipt")
    r.add_argument("--repo", type=Path, required=True)
    r.add_argument("--work-id", required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--timeout", type=int, default=120)
    r.add_argument("command", nargs=argparse.REMAINDER)
    c = subs.add_parser("check", help="check a claim and optional receipt; never run a command")
    c.add_argument("--repo", type=Path, required=True)
    c.add_argument("--claim", type=Path, required=True)
    c.add_argument("--receipt", type=Path)
    c.add_argument("--expected-source-sha", help="live remote ref SHA fetched independently")
    args = p.parse_args()
    if args.action == "record":
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        result = record(args.repo, args.work_id, args.out, command, args.timeout)
        print(json.dumps({k: result[k] for k in ("work_id", "source_sha", "exit_code", "timed_out", "clean_after")}, indent=2))
        return 0 if result["exit_code"] == 0 and result["clean_after"] and not result["stdout_truncated"] and not result["stderr_truncated"] else 2
    sha, clean = state(args.repo)
    claim = json.loads(args.claim.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8")) if args.receipt else None
    result = check(claim, receipt, local_sha=sha, local_clean=clean, expected_source_sha=args.expected_source_sha)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "verified_local_execution_receipt" else 2


if __name__ == "__main__":
    sys.exit(main())
