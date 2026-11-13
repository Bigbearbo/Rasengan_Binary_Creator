"""Final artifact processing only. No learner imports, NN, optimizer or Git calls."""
from pathlib import Path
import argparse
import copy
import io
import json
import sys
import zipfile
import zlib

sys.dont_write_bytecode = True
import package_publication as b

HERE = Path(__file__).resolve().parent
WORK = b.WORK
PREFIX = b.PREFIX
SEEDS = (101, 202, 303)
REVIEW = ("audit_post.py", "metadata-preflight.json", "audit-cost.json", "post-run.json", "post-run-details.json",
          "audit-execution-receipt.json", "audit.stdout.log", "audit.stderr.log")
EXECUTION = ("execution-receipt.json", "git-prereg-receipt.json", "formal-command-result.json",
             "root-execution-intent.json", "launch_formal.py", "execution.stdout.log", "execution.stderr.log")
PRIVATE_COMMAND_SHA = "5c589c6ebbad598a823ebb8d0c4265cb5c500348bb6cd861ebff238890683739"


def inventory(root):
    return {p.relative_to(root).as_posix(): {"bytes": p.stat().st_size, "sha256": b.sha(p.read_bytes())}
            for p in sorted(root.rglob("*")) if p.is_file()}


def groups(entries, cap=3_000_000):
    answer, current, size = [], {}, 22
    for name, raw in sorted(entries.items()):
        compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
        cost = len(compressor.compress(raw) + compressor.flush()) + 76 + 2 * len(name.encode("utf-8"))
        if current and size + cost > cap:
            answer.append(current)
            current, size = {}, 22
        current[name] = raw
        size += cost
    if current:
        answer.append(current)
    b.need({name for part in answer for name in part} == set(entries), "Grouping omitted an artifact")
    return answer


def make_archive(entries, frozen_zip=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, raw in sorted(entries.items()):
            b.safe_name(name)
            if name.endswith(".zip"):
                b.need(frozen_zip is not None and raw == frozen_zip, "Unexpected nested ZIP")
            else:
                b.check_content(name, raw)
            item = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    raw = output.getvalue()
    members = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        b.need(len(archive.infolist()) == len(entries) and set(archive.namelist()) == set(entries), "ZIP inventory differs")
        for item in archive.infolist():
            data = entries[item.filename]
            b.need(archive.read(item) == data, "ZIP byte roundtrip differs")
            crc = zlib.crc32(data) & 0xffffffff
            b.need(item.CRC == crc and item.file_size == len(data), "ZIP size/CRC differs")
            members[item.filename] = {**b.info(data), "CRC32": f"{crc:08x}", "compressed_bytes": item.compress_size}
    return raw, {**b.info(raw), "member_count": len(members), "members": members}


def command_public_copy(raw):
    b.need(b.sha(raw) == PRIVATE_COMMAND_SHA, "Original command/timer source SHA differs")
    original = json.loads(raw.decode("utf-8"))
    public = copy.deepcopy(original)
    b.need(isinstance(original["command"], list) and original["command"] and b.PRIVATE_TEXT.search(original["command"][0]),
           "Authorized machine-userpath pointer was not found")
    public["command"][0] = "<python>"
    b.need(original.keys() == public.keys() and original["command"][1:] == public["command"][1:]
           and all(original[key] == public[key] for key in original if key != "command"), "Additional command/timer field changed")
    safe = b.json_bytes(public)
    b.check_content("formal-command-result.json", safe)
    return safe, {"public_file": "formal-command-result.json", "archive_member": "execution/formal-command-result.json",
                  "JSON_pointer": "/command/0", "replacement": "<python>", "reason": "machine-userpath",
                  "original_bytes": len(raw), "original_sha256": b.sha(raw), "public_bytes": b.info(safe),
                  "original_value_disclosed": False, "other_argv_exit_time_invocation_fields_exact": True,
                  "local_original_modified": False, "public_file_byte_identical_to_local_original": False}


def final_gate(approved, manifest):
    post = b.read_json(WORK / "review/post-run.json")
    detail = b.read_json(WORK / "review/post-run-details.json")
    receipt_raw = (WORK / "execution-receipt.json").read_bytes()
    receipt = json.loads(receipt_raw.decode("utf-8"))
    audit = b.read_json(WORK / "review/audit-execution-receipt.json")
    git = b.read_json(WORK / "git-prereg-receipt.json")
    root_intent = b.read_json(WORK / "root-execution-intent.json")
    command = b.read_json(WORK / "formal-command-result.json")
    b.need(post["status"] == detail["status"] == "passed" and post["manifest_sha256"] == detail["manifest_sha256"] == approved,
           "Independent numerical review is incomplete or for another manifest")
    b.need(post["source_hashes"] == detail["source_hashes"] == manifest["source_hashes"]
           and post["root_confirmed_formal_exit0"] is True, "Reviewed source/formal closure differs")
    b.need(post["receipt_sha256"] == detail["receipt_sha256"] == b.sha(receipt_raw), "Reviewed formal receipt bytes differ")
    b.need(receipt["exit_code"] == receipt["formal_exit"] == 0 and receipt["status"] == "exit0"
           and receipt["formal_session_closed"] is True and receipt["command_invocations"] == 1, "Formal process not closed exit0")
    b.need(audit["status"] == "exit0" and audit["audit_exit_code"] == audit["audit_tool_exit_code"] == 0
           and audit["audit_process_closed"] is True and audit["audit_tool_session_closed"] is True,
           "Numerical audit process not closed exit0")
    b.need(b.sha((WORK / "review/audit_post.py").read_bytes()) == post["review_source_sha256"] == audit["audit_source_sha256"],
           "Executed audit source differs")
    commit = git["preregistration_commit"]
    b.need(git["all_actual_bytes_verified"] is True and git["manifest_sha256"] == approved
           and root_intent["manifest_sha256"] == approved and root_intent["preregistration_commit"] == commit
           and root_intent["formal_command_invocations_authorized"] == 1 and root_intent["auto_retry"] is False,
           "Coordinator preregistration/intent differs")
    b.need(receipt["manifest_sha256"] == approved and receipt["preregistration_commit"] == post["preregistration_commit"] == commit
           and command["exit_code"] == 0 and command["command_invocations"] == 1
           and command["formal_seconds"] == receipt["formal_seconds"], "Formal invocation/timer provenance differs")
    intent = b.read_json(WORK / "science/execution-intent.json")
    b.need(intent["approved_manifest_sha256"] == approved and intent["source_hashes"] == manifest["source_hashes"]
           and intent["preregistration_commit"] == commit and intent["primary_seeds"] == list(SEEDS)
           and intent["replay_seeds"] == [] and intent["auto_retry"] is False, "Native execution intent differs")
    summary = b.read_json(WORK / "science/compact.json")
    b.need(summary["status"] == "complete" and [row["seed"] for row in summary["students"]] == list(SEEDS)
           and all(row["replay_status"] == "not_planned" and row["new_updates"] == 36000 for row in summary["students"])
           and summary["new_updates"] == 108000 and summary["new_training_dense_MAC"] == 2274048000
           and summary["new_replay_updates"] == summary["new_replay_training_dense_MAC"] == 0
           and summary["exact_full_replays"] == [], "Fixed one-epoch/no-replay scope differs")
    b.need(len(b.read_json(WORK / "science/timing.json")) == 3, "Three primary timing segments required")
    science = inventory(WORK / "science")
    b.need(science == detail["science_file_inventory"], "Science inventory differs from completed independent audit")
    expected = {f"numeric-proof/seed{seed}-{kind}.json" for seed in SEEDS for kind in ("baseline", "control", "new", "TF", "student")}
    refs = detail["numeric_proof_refs"]
    b.need(len(refs) == len(set(refs)) == 15 and set(refs) == expected, "Complete15proof set differs")
    for name in refs:
        raw = b.file_under(WORK / "review", name).read_bytes()
        b.need({"bytes": len(raw), "sha256": b.sha(raw)} == detail["numeric_proof_inventory"][name], "Numerical proof bytes differ")
    return summary, science, refs, git


def package(approved, out):
    out = Path(out).resolve()
    b.need(not out.exists(), "Final publication exists; never overwrite/retry in place")
    manifest, frozen_zip, input_index = b.source_guard(approved)
    summary, science_before, refs, git = final_gate(approved, manifest)
    files, originals, archive_indexes = {}, {}, {}

    def add(root, source, target):
        b.need(target not in files, "Duplicate public file")
        path = b.file_under(root, source)
        raw = path.read_bytes()
        b.check_content(target, raw)
        files[target] = raw
        originals[path] = b.sha(raw)
        return raw

    prereg_dir = WORK / "publication/prereg/public"
    prereg_manifest = b.read_json(WORK / "publication/prereg/compact.json")["public_files"]
    actual_prereg = {p.relative_to(prereg_dir).as_posix() for p in prereg_dir.rglob("*") if p.is_file()}
    b.need(len(prereg_manifest) == 23 and actual_prereg == set(prereg_manifest), "Original23prereg file set changed")
    checks = {item["name"]: item for item in git["byte_checks"]}
    b.need(git["public_files"] == 23 and set(checks) == set(prereg_manifest), "Remote byte-readback coverage differs")
    prior_entries = {}
    for name, pin in prereg_manifest.items():
        path = b.file_under(prereg_dir, name)
        raw = path.read_bytes()
        b.need(b.info(raw) == pin and checks[name]["byte_match"] is True
               and all(checks[name][key] == pin[key] for key in ("bytes", "sha256", "Git_blob")), "Original prereg bytes differ")
        prior_entries["preregistration/" + name] = raw
        originals[path] = b.sha(raw)
    raw, index = make_archive(prior_entries, frozen_zip)
    files["preregistration.zip"], archive_indexes["preregistration.zip"] = raw, index
    archive_indexes["preregistration.zip"]["nested_inputs"] = {"member": "preregistration/inputs.zip", **b.info(frozen_zip),
                                                               "validated_members": input_index["member_count"]}
    files["inputs.zip"] = frozen_zip
    archive_indexes["inputs.zip"] = {**b.info(frozen_zip), **input_index, "exact_frozen_container": True}
    for name in b.CORE + ("README.md", "RESEARCH_NOTE.md", "HANDOFF.md", "EXTERNAL_REVIEW.json", "RESULTS.md", "package_publication.py", "package_final.py"):
        add(HERE, name, name)
    for name in ("manifest.json", "source-freeze.json"):
        add(WORK / "prereg", name, name)
    originals[WORK / "prereg/inputs.zip"] = b.sha(frozen_zip)
    for name in ("PR33-publication-manifest.json", "PR33-live-readback.json"):
        add(WORK / "references", name, "references/" + name)
    add(WORK, "external-method-checks.json", "external-method-checks.json")
    add(b.ROOT, "outputs/agent-team/context/f2_one_epoch_stability.json", "external-context.json")

    science_entries = {}
    science_finite = {"NPZ": 0, "NPY": 0}
    for name in science_before:
        path = b.file_under(WORK / "science", name)
        data = path.read_bytes()
        finite = b.check_content(name, data)
        for key in science_finite:
            science_finite[key] += finite[key]
        science_entries["science/" + name] = data
        originals[path] = b.sha(data)
    covered = set()
    for seed in SEEDS:
        selected = {name: data for name, data in science_entries.items() if name.startswith(f"science/seed{seed}/")}
        b.need(bool(selected), "Missing actual seed artifacts")
        for number, part in enumerate(groups(selected), 1):
            name = f"science-seed{seed}-{number:03}.zip"
            raw, index = make_archive(part)
            b.need(len(raw) <= 3_000_000 or len(part) == 1, "Unexpected multi-member oversize archive")
            files[name], archive_indexes[name] = raw, index
            covered |= set(part)
    leftover = {name: data for name, data in science_entries.items() if name not in covered}
    raw, index = make_archive(leftover)
    files["science-metadata.zip"], archive_indexes["science-metadata.zip"] = raw, index
    covered |= set(leftover)
    b.need(covered == set(science_entries), "Science artifact omitted")
    for name in ("compact.json", "execution-intent.json", "timing.json"):
        add(WORK / "science", name, "science-" + name)

    redactions, execution_entries = [], {}
    for name in EXECUTION:
        path = b.file_under(WORK, name)
        raw = path.read_bytes()
        originals[path] = b.sha(raw)
        if name == "formal-command-result.json":
            public, redaction = command_public_copy(raw)
            redactions.append(redaction)
        else:
            public = raw
        b.check_content(name, public)
        files[name] = public
        execution_entries["execution/" + name] = public
    raw, index = make_archive(execution_entries)
    files["execution-evidence.zip"], archive_indexes["execution-evidence.zip"] = raw, index
    files["public-redactions.json"] = b.json_bytes({"schema": "machine-userpath-public-copy-v1", "records": redactions,
                                                   "all_science_prereg_source_and_numeric_values_unchanged": True})
    review_entries = {}
    for name in REVIEW:
        data = add(WORK / "review", name, "review/" + name)
        review_entries["review/" + name] = data
    for name in refs:
        path = b.file_under(WORK / "review", name)
        data = path.read_bytes()
        b.check_content(name, data)
        originals[path] = b.sha(data)
        review_entries["review/" + name] = data
    raw, index = make_archive(review_entries)
    files["independent-evidence.zip"], archive_indexes["independent-evidence.zip"] = raw, index
    for name in b.selected_sources():
        if name.startswith("review/") or name == "engineering-checks.json":
            path = b.selected_sources()[name]
            data = path.read_bytes()
            b.check_content(name, data)
            files[name] = data
            originals[path] = b.sha(data)

    for path, pin in originals.items():
        b.need(b.sha(path.read_bytes()) == pin, "Original bytes changed during artifact processing")
    b.need(inventory(WORK / "science") == science_before, "Science changed during packaging")
    coverage = {"source_files": len(science_before), "all_actual_files_preserved": True,
                "source_finite_arrays": science_finite, "prereg_finite_arrays": input_index["finite_arrays"],
                "unique_source_finite_NPZ": science_finite["NPZ"] + input_index["finite_arrays"]["NPZ"],
                "unique_source_finite_NPY": science_finite["NPY"] + input_index["finite_arrays"]["NPY"],
                "preregistration_nested_inputs_are_an_exact_duplicate_of_inputs_zip": True}
    report = {"schema": "f2-stability-final-publication-v1", "status": "verified", "manifest_sha256": approved,
              "source_hashes": manifest["source_hashes"], "preregistration_commit": git["preregistration_commit"],
              "files": {name: b.info(data) for name, data in sorted(files.items())}, "archives": archive_indexes,
              "science_file_inventory": science_before, "science_coverage": coverage, "preregistration_original_files": prereg_manifest,
              "public_copy_exceptions": "public-redactions.json: only formal-command-result.json#/command/0; public copy is not local-byte-identical",
              "audit_scope": "Independent free tokens and final-TF logits/probabilities/CE. No saved free-run raw logits or optimizer replay claim.",
              "formal_optimizer_replays": 0, "packager_NN_optimizer_external_Git_calls": 0}
    files["publication-manifest.json"] = b.json_bytes(report)
    check_report = {"status": "PASS", "original_prereg_files_byte_verified": 23,
                    "archive_members_byte_CRC_SHA_verified": sum(value["member_count"] for value in archive_indexes.values()),
                    "science_coverage": coverage, "all_original_files_hash_unchanged": len(originals),
                    "authorized_public_copy_redactions": len(redactions), "local_private_original_modified": False,
                    "packager_NN_optimizer_external_Git_calls": 0}
    files["export-checks.json"] = b.json_bytes(check_report)
    for name, data in files.items():
        if not name.endswith(".zip"):
            b.check_content(name, data)
    out.mkdir(parents=True, exist_ok=False)
    public = out / "public"
    public.mkdir()
    text, binaries, expected = [], [], {}
    for name, data in sorted(files.items()):
        target = public / b.safe_name(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        b.need(target.read_bytes() == data, "Published byte roundtrip differs")
        gitpath = PREFIX + "/" + name
        expected[gitpath] = b.blob(data)
        if name.endswith(".zip"):
            binaries.append({"path": gitpath, "mode": "100644", "type": "blob", **b.info(data), "local_file": "public/" + name})
        else:
            content = data.decode("utf-8")
            b.need(content.encode("utf-8") == data, "Text Git entry bytes differ")
            text.append({"path": gitpath, "mode": "100644", "type": "blob", "content": content})
    b.write_json(out / "text-entries.json", text)
    b.write_json(out / "binary-entries.json", binaries)
    b.write_json(out / "expected-blobs.json", expected)
    result = {"status": "verified", "mode": "final", "repo_prefix": PREFIX, "public_directory": public.as_posix(),
              "public_files": {name: b.info(data) for name, data in sorted(files.items())},
              "removed_from_root": sorted(set(prereg_manifest) - set(files)),
              "public_files_over_1MiB": {name: b.info(data) for name, data in sorted(files.items()) if len(data) > 1048576},
              "archive_indexes": {name: {key: value for key, value in index.items() if key != "members"} for name, index in archive_indexes.items()},
              "full_member_inventory": "public/publication-manifest.json", "science_coverage": coverage, "checks": check_report,
              "text_entries": len(text), "binary_entries": len(binaries), "packager_sha256": b.sha(Path(__file__).read_bytes())}
    b.write_json(out / "compact.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--approved-manifest-sha", required=True)
    parser.add_argument("--out", type=Path, default=WORK / "publication/final")
    args = parser.parse_args()
    b.need(args.finalize, "Root explicit FINAL-PACK GO and --finalize are required")
    result = package(args.approved_manifest_sha, args.out)
    print(json.dumps({key: result[key] for key in ("status", "text_entries", "binary_entries", "science_coverage", "checks", "packager_sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
