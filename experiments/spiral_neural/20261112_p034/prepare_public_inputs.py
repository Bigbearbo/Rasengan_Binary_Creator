"""Rebuild a fresh P034 workspace from the public bundle and pinned PR7 ZIP.

No model is trained or imported. Original scientific source bytes are copied
without rewriting paths, guards, courses, model configuration or budgets.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

sys.dont_write_bytecode = True
PUBLIC_BASE = "experiments/spiral_neural/20261112_p033/"
SEEDS = (101, 202, 303)
SPLITS = ("S0", "C0", "S1", "C1")
CORE = ("attention_model.py", "test_attention.py", "b1_trial.py", "e900.py",
        "baseline_preflight.py", "reproduce.py", "prepare_public_inputs.py", "protocol.json")
REFERENCE = ("p030_reference.py", "p032_reference.py", "p033.py", "diagnostic.py",
             "echo_only_followup.py")
DESIGN = ("PRO_RESEARCH_DESIGN_20261112.md", "PR8_AGENTS.md",
          "CURRENT_RESEARCH_STATUS.md", "spiral_language_research_index.md")


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(path.read_bytes())


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2,
                  allow_nan=False)
        stream.write("\n")


def safe_relative(name):
    path = PurePosixPath(name)
    if (not name or "\\" in name or path.is_absolute() or
            any(part in ("", ".", "..") or ":" in part for part in path.parts)):
        raise ValueError(f"Unsafe public artifact path: {name!r}")
    return path.as_posix()


def validate_package(package):
    """Check the exact published file inventory before interpreting any ZIP."""
    manifest = read_json(package / "package-manifest.json")
    if manifest["schema"] != "P034-public-bundle-v1":
        raise ValueError("Unexpected public package schema")
    checked = {}
    for name, expected in manifest["files"].items():
        name = safe_relative(name)
        path = package.joinpath(*PurePosixPath(name).parts)
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing or symlinked public package file: {name}")
        data = path.read_bytes()
        if sha_bytes(data) != expected["sha256"] or len(data) != expected["bytes"]:
            raise ValueError(f"Public package file hash/size mismatch: {name}")
        if "git_blob" in expected and git_blob(data) != expected["git_blob"]:
            raise ValueError(f"Public package Git blob mismatch: {name}")
        checked[name] = sha_bytes(data)
    for name in CORE:
        if name not in checked:
            raise ValueError(f"Core source is absent from public inventory: {name}")
    for name in REFERENCE:
        if "reference/"+name not in checked:
            raise ValueError(f"Reference source is absent from inventory: {name}")
    archives = {}
    for name, entries in manifest["zip_entries"].items():
        if name not in checked:
            raise ValueError(f"ZIP is not in public file inventory: {name}")
        expected_entries = {safe_relative(e["name"]): e for e in entries}
        if len(expected_entries) != len(entries):
            raise ValueError(f"Duplicate ZIP inventory names: {name}")
        with zipfile.ZipFile(package / name) as archive:
            actual_names = [safe_relative(i.filename) for i in archive.infolist() if not i.is_dir()]
            if len(actual_names) != len(set(actual_names)) or set(actual_names) != set(expected_entries):
                raise ValueError(f"ZIP entry inventory differs: {name}")
            for info in archive.infolist():
                if info.is_dir():
                    continue
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError(f"ZIP symlink is not accepted: {info.filename}")
                data = archive.read(info)
                expected = expected_entries[info.filename]
                if sha_bytes(data) != expected["sha256"] or len(data) != expected["bytes"]:
                    raise ValueError(f"ZIP member hash/size mismatch: {name}/{info.filename}")
        archives[name] = expected_entries
    if "input-supplement.zip" not in archives:
        raise ValueError("Missing original trace/public metadata supplement")
    evidence_parts = sorted(n for n in archives if re.fullmatch(r"evidence(?:-\d+)?\.zip", n))
    if not evidence_parts:
        raise ValueError("Missing P034 evidence ZIP part(s)")
    return manifest, checked, archives, evidence_parts


def required_pr7_members():
    result = {"manifest.json", "echo-only-followup-v2/manifest.json"}
    for split in SPLITS:
        for seed in SEEDS:
            name = f"{split}-seed{seed}"
            coverage = f"coverage/{name}/"
            result.update(coverage + suffix for suffix in (
                "warm-3/final-state.npz", "neg70/final-state.npz", "result.json",
                "final-truth-table.json", "neg70/summary.json", "neg70/curve.json"))
            followup = f"echo-only-followup-v2/{name}-echo-only/"
            result.update(followup + suffix for suffix in
                          ("final-state.npz", "result.json", "summary.json", "curve.json"))
    for group in ("G0", "G1"):
        for seed in SEEDS:
            prefix = f"timing/{group}-seed{seed}-T1/"
            result.update(prefix + suffix for suffix in
                          ("state-3000.npz", "truth-table-3000.json", "result.json"))
    return sorted(result)


def prepare(package, pr7_zip, workspace):
    package, pr7_zip, workspace = package.resolve(), pr7_zip.resolve(), workspace.resolve()
    if workspace.exists():
        raise FileExistsError("Use a fresh workspace; existing directories are never modified")
    manifest, package_hashes, archives, evidence_parts = validate_package(package)
    staged, provenance = {}, {}

    def add(name, data, source):
        name = safe_relative(name)
        if name in staged and staged[name] != data:
            raise ValueError(f"Conflicting staged input: {name}")
        staged[name], provenance[name] = data, source

    supplement = "input-supplement.zip"
    with zipfile.ZipFile(package / supplement) as archive:
        pin_name = "work/sle-p033/publication-v2/expected-git-blobs.json"
        pins = json.loads(archive.read(pin_name).decode("utf-8"))
        for name in archives[supplement]:
            if not name.startswith(("work/sle-p033/trial-20261112/",
                                    "work/sle-p033/publication-v2/")):
                raise ValueError(f"Unexpected supplement destination: {name}")
            add(name, archive.read(name), supplement+":"+name)
    public_bytes = pr7_zip.read_bytes()
    expected_pr7_blob = pins[PUBLIC_BASE+"evidence.zip"]
    if git_blob(public_bytes) != expected_pr7_blob:
        raise ValueError("Provided PR7 evidence ZIP does not match the pinned public Git blob")
    add("work/sle-p033/publication-v2/evidence.zip", public_bytes,
        "pinned-public-PR7-evidence.zip")
    # Check the public inventory JSON's own Git blob, then original trace hashes.
    inventories = []
    for name, data in list(staged.items()):
        if name.startswith("work/sle-p033/publication-v2/entry-") and name.endswith(".json"):
            entry = json.loads(data.decode("utf-8"))
            if entry["path"].endswith("/local-artifact-hashes.json"):
                inventory_bytes = entry["content"].encode("utf-8")
                if git_blob(inventory_bytes) != pins[PUBLIC_BASE+"local-artifact-hashes.json"]:
                    raise ValueError("Public original artifact inventory Git blob mismatch")
                inventories.append(json.loads(inventory_bytes.decode("utf-8")))
    if len(inventories) != 1:
        raise ValueError("Exactly one pinned public artifact inventory is required")
    inventory = inventories[0]
    with zipfile.ZipFile(pr7_zip) as archive:
        for relative in required_pr7_members():
            member = "evidence/"+relative
            add("work/sle-p033/trial-20261112/"+relative, archive.read(member),
                "pinned-public-PR7-evidence.zip:"+member)
    for name, data in list(staged.items()):
        prefix = "work/sle-p033/trial-20261112/"
        if name.startswith(prefix) and name[len(prefix):] in inventory:
            if sha_bytes(data) != inventory[name[len(prefix):]]["sha256"]:
                raise ValueError(f"Original public artifact inventory mismatch: {name}")
    original_manifests = {}
    for part in evidence_parts:
        with zipfile.ZipFile(package / part) as archive:
            for name in archives[part]:
                if (name.startswith("work/sle-p034/baseline/") or
                        name == "work/sle-p034/attention-engineering/checks.json"):
                    add(name, archive.read(name), part+":"+name)
                if name in ("work/sle-p034/b1/manifest.json", "work/sle-p034/e900/manifest.json"):
                    original_manifests[name.split("/")[-2]] = json.loads(archive.read(name).decode("utf-8"))
                    add(name.replace("/b1/", "/original-evidence/b1/").replace(
                        "/e900/", "/original-evidence/e900/"), archive.read(name), part+":"+name)
    if set(original_manifests) != {"b1", "e900"}:
        raise ValueError("Original frozen B1 and E900 manifests must accompany the bundle")
    for name in CORE:
        add("outputs/sle-p034/"+name, (package/name).read_bytes(), "package:"+name)
    for name in REFERENCE:
        data = (package/"reference"/name).read_bytes()
        if git_blob(data) != pins[PUBLIC_BASE+name]:
            raise ValueError(f"Original PR7 reference source Git blob mismatch: {name}")
        add("outputs/sle-p034/reference/"+name, data, "package:reference/"+name)
        add("outputs/sle-p033/"+name, data, "package:reference/"+name)
    for name in DESIGN:
        add("work/sle-p034/source-plan/"+name, (package/"design"/name).read_bytes(),
            "package:design/"+name)
    b1_manifest, e900_manifest = original_manifests["b1"], original_manifests["e900"]
    for name, expected in b1_manifest["source_sha256"].items():
        if sha_bytes(staged["outputs/sle-p034/"+name]) != expected:
            raise ValueError(f"Frozen scientific source SHA256 changed: {name}")
    if sha_bytes(staged["outputs/sle-p034/e900.py"]) != e900_manifest["runner_sha256"]:
        raise ValueError("Frozen E900 runner SHA256 changed")
    for label, expected in b1_manifest["prerequisite_sha256"].items():
        relative = "outputs/sle-p034/protocol.json" if label == "protocol.json" else "work/sle-p034/"+label
        if sha_bytes(staged[relative]) != expected:
            raise ValueError(f"Frozen B1 prerequisite changed: {label}")
    # Every byte has been checked before creating the destination workspace.
    workspace.mkdir(parents=True, exist_ok=False)
    for name, data in staged.items():
        target = workspace.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if sha(target) != sha_bytes(data):
            raise IOError(f"Staged copy did not preserve bytes: {name}")
    report = {
        "status": "passed", "scientific_updates": 0,
        "package_schema": manifest["schema"], "workspace": str(workspace),
        "public_PR7_git_blob": expected_pr7_blob,
        "public_PR7_sha256": sha_bytes(public_bytes),
        "package_files_checked": package_hashes,
        "source_bytes_rewritten": False, "learning_code_changes": 0,
        "frozen_scientific_sources": b1_manifest["source_sha256"] | {"e900.py": e900_manifest["runner_sha256"]},
        "staged_files": {name: {"sha256": sha_bytes(data), "bytes": len(data),
                                 "source": provenance[name]} for name, data in sorted(staged.items())},
    }
    dump(workspace / "prepared-inputs.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--pr7-evidence", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.package_root, args.pr7_evidence, args.workspace)
    print(json.dumps({"status": report["status"], "scientific_updates": 0,
                      "staged_files": len(report["staged_files"]),
                      "workspace": report["workspace"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
