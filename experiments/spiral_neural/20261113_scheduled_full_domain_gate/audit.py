"""Read-only audit of a frozen full-domain neural experiment.

This script never authorizes training. A separate coordinator/owner must
approve the exact manifest digest and preregistration commit.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import zipfile

BASE = Path("experiments/spiral_neural/20261113_codex_full_domain_mix")
FROZEN_MANIFEST_SHA256 = "dabdb58a54ffd93afa350f19876a53550bcfcfd6de9b5199ee8b3b26d2b8d658"
FROZEN_RUNNER_SHA256 = "9c100c1b8d6e9d1aca4acfc0f5a89d1a4716286aae1fae44692cbb5d0066593e"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scope_of(source, name):
    tree = ast.parse(source)
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, func)


def gate_shape(source):
    exe = scope_of(source, "execute")
    validation = scope_of(source, "validate_inputs")
    return {
        "commit_only_shape_checked": 're.fullmatch(r"[0-9a-f]{40}", commit or "")' in exe,
        "manifest_hash_compared_to_caller_input": "file_sha(path) == approved" in validation,
        "formal_training_called_from_execute": "run_seed(" in exe,
        "commit_bound_to_manifest_by_execute": any(token in exe for token in (
            "fetch_commit(", "verify_commit(", "verify_approval(", "verify_signature(",
            "approval_record", "subprocess.run(", "git_show(", "git_cat_file(")),
        "any_40hex_meets_shape": re.fullmatch(r"[0-9a-f]{40}", "f" * 40) is not None,
    }


def audit(repo_root):
    directory = Path(repo_root) / BASE
    runner = (directory / "run_full_domain.py").read_bytes()
    manifest = (directory / "manifest.json").read_bytes()
    protocol = (directory / "protocol.json").read_bytes()
    parsed = json.loads(manifest)
    plan = json.loads(protocol)
    checks = {
        "manifest_sha256_matches_frozen": digest(manifest) == FROZEN_MANIFEST_SHA256,
        "runner_sha256_matches_frozen": digest(runner) == FROZEN_RUNNER_SHA256,
        "manifest_pins_runner": parsed["source_hashes"]["run_full_domain.py"] == digest(runner),
        "manifest_pins_protocol": parsed["source_hashes"]["protocol.json"] == digest(protocol),
        "plan_matches_manifest": parsed["protocol"] == plan,
        "status_is_frozen_not_executed": parsed["status"] == "frozen_before_formal_training",
        "formal_calls_declared_zero": parsed.get("formal_optimizer_calls_before_freeze") == 0 and parsed.get("formal_inference_calls_before_freeze") == 0,
    }
    archive = (directory / parsed["archive"]["file"]).read_bytes()
    checks["inputs_archive_digest"] = digest(archive) == parsed["archive"]["sha256"]
    with zipfile.ZipFile(directory / parsed["archive"]["file"]) as z:
        names = z.namelist()
        checks["entries_unique"] = len(names) == len(set(names)) and set(names) == set(parsed["files"])
        checks["all_entries_match_manifest"] = all(
            digest(z.read(n)) == parsed["files"][n]["sha256"]
            and len(z.read(n)) == parsed["files"][n]["bytes"] for n in names)
    shape = gate_shape(runner.decode("utf-8"))
    status = "frozen_inputs_verified__external_approval_unverified" if all(checks.values()) else "frozen_input_integrity_failed"
    return {
        "status": status, "checks": checks, "gate_shape": shape,
        "formal_optimizer_updates_this_audit": 0,
        "formal_nn_forwards_this_audit": 0,
        "external_approval_verified": False,
        "critical_boundary": "Runner validates a supplied manifest hash and a SHA-shaped commit string; it does not independently establish owner authorization or bind the commit to that manifest.",
    }


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--repo-root", type=Path, required=True)
    cli.add_argument("--out", type=Path)
    args = cli.parse_args()
    report = audit(args.repo_root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if report["status"] == "frozen_input_integrity_failed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
