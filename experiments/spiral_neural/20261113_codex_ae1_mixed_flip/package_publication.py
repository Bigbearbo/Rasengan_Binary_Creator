"""Package mixed E1/E2/Flip1 evidence bytes; never execute scientific code.

prereg requires the frozen inputs and independent pre-run PASS. final additionally
requires root exit0 and independent post-run PASS. All science files are retained,
including failed probes/states. Existing destinations are never overwritten.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile
import zlib


PREFIX = "experiments/spiral_neural/20261113_codex_ae1_mixed_flip"
SEEDS = (101, 202, 303)
REFERENCE_SHA = "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"
GROUP_BYTES = 3_000_000
PRIVATE_TEXT = re.compile(r"(?i)(?:[A-Z]:[\\/]Us" r"ers[\\/]|/ho" r"me/|/Us" r"ers/|Bearer\s+[A-Za-z0-9._-]{8,}|sk-or-v1-[A-Za-z0-9]+)")
PRIVATE_KEYS = {"private_raw_api_record", "private_legacy_record", "raw_api_path", "api_key", "access_token",
                "refresh_token", "id_token", "authorization_header", "account_quota", "quota_remaining"}
PRIVATE_NAMES = {".git", ".ssh", ".aws", "__pycache__", "fontcache", "autonomous-state.json", "transport.json"}
REVIEW_PREREG = ("check_protocol.py", "protocol-review.json", "check_pre_run.py", "pre-run.json")
REVIEW_FINAL = ("audit_post.py", "metadata-preflight.json", "post-run.json", "post-run-details.json", "audit-cost.json")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def info(data):
    return {"bytes": len(data), "sha256": sha(data), "Git_blob": blob(data)}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(Path(path).read_bytes().decode("utf-8-sig"))


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json_bytes(value).decode("utf-8"))


def safe_name(name):
    need(isinstance(name, str) and name and "\\" not in name and ":" not in name, "Unsafe path")
    path = PurePosixPath(name)
    need(not path.is_absolute() and all(part not in (".", "..", "") for part in path.parts), "Path escaped")
    need(not any(part.casefold() in PRIVATE_NAMES for part in path.parts), "Private/cache path selected")
    return path.as_posix()


def file_under(root, name):
    root = Path(root).resolve()
    path = (root / safe_name(name)).resolve()
    need(path.is_relative_to(root) and path.is_file(), f"Missing/escaped source: {name}")
    return path


def scan_json(value, name):
    if isinstance(value, dict):
        for key, item in value.items():
            need(key.casefold() not in PRIVATE_KEYS, f"Private field in {name}")
            scan_json(item, name)
    elif isinstance(value, list):
        for item in value:
            scan_json(item, name)
    elif isinstance(value, str):
        need(not PRIVATE_TEXT.search(value), f"Private user path/credential in {name}")
    elif isinstance(value, float):
        need(math.isfinite(value), f"Nonfinite JSON in {name}")


def check_content(name, data):
    """Return finite NPZ/NPY counts. Array loading is not model inference."""
    safe_name(name)
    suffix = PurePosixPath(name).suffix.lower()
    if suffix in (".npz", ".npy"):
        import numpy as np
        loaded = np.load(io.BytesIO(data), allow_pickle=False)
        if suffix == ".npz":
            with loaded as archive:
                need(bool(archive.files), f"Empty NPZ: {name}")
                arrays = [archive[key] for key in archive.files]
        else:
            arrays = [loaded]
        for array in arrays:
            need(not array.dtype.hasobject, f"Object array: {name}")
            if np.issubdtype(array.dtype, np.number):
                need(bool(np.isfinite(array).all()), f"Nonfinite array: {name}")
            elif array.dtype.kind in "US":
                for text in array.ravel().tolist():
                    text = text.decode("utf-8") if isinstance(text, bytes) else text
                    need(not PRIVATE_TEXT.search(text), f"Private array metadata: {name}")
                    try:
                        scan_json(json.loads(text), name)
                    except json.JSONDecodeError:
                        pass
        return {"NPZ": int(suffix == ".npz"), "NPY": int(suffix == ".npy")}
    if suffix == ".gz":
        return check_content(name[:-3], gzip.decompress(data))
    need(suffix in (".json", ".jsonl", ".py", ".md", ".txt", ".log"), f"Unknown public content kind: {name}")
    text = data.decode("utf-8-sig")
    need(not PRIVATE_TEXT.search(text), f"Private user path/credential: {name}")
    if suffix == ".json":
        scan_json(json.loads(text), name)
    elif suffix == ".jsonl":
        for line in text.splitlines():
            if line:
                scan_json(json.loads(line), name)
    return {"NPZ": 0, "NPY": 0}


def inspect_zip(data, expected=None):
    members, counts = {}, {"NPZ": 0, "NPY": 0}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        need(len(infos) == len({item.filename for item in infos}), "Duplicate ZIP entries")
        if expected is not None:
            need({item.filename for item in infos} == set(expected), "ZIP member allowlist differs")
        for item in infos:
            safe_name(item.filename)
            need(not item.is_dir() and not (item.flag_bits & 1), "Directory/encrypted ZIP entry")
            need(((item.external_attr >> 16) & 0o170000) in (0, 0o100000), "Nonregular ZIP member")
            raw = archive.read(item)
            crc = zlib.crc32(raw) & 0xffffffff
            need(len(raw) == item.file_size and crc == item.CRC, "ZIP size/CRC mismatch")
            if expected is not None:
                value = expected[item.filename]
                if isinstance(value, bytes):
                    need(raw == value, f"ZIP byte roundtrip failed: {item.filename}")
                else:
                    need(len(raw) == value["bytes"] and sha(raw) == value["sha256"], "Frozen ZIP member differs")
            current = check_content(item.filename, raw)
            for key in counts:
                counts[key] += current[key]
            members[item.filename] = {**info(raw), "CRC32": f"{crc:08x}", "compressed_bytes": item.compress_size}
    return {"members": members, "member_count": len(members), "finite_arrays": counts}


def make_zip(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, raw in sorted(entries.items()):
            safe_name(name)
            item = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    raw = buffer.getvalue()
    return raw, inspect_zip(raw, entries)


def group_entries(entries, cap=GROUP_BYTES):
    """Bound actual ZIP bytes; a single oversized member is retained and flagged."""
    groups, group, total = [], {}, 22
    for name, raw in sorted(entries.items()):
        compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
        compressed = len(compressor.compress(raw) + compressor.flush())
        cost = 76 + 2 * len(name.encode("utf-8")) + compressed
        if group and total + cost > cap:
            groups.append(group)
            group, total = {}, 22
        group[name] = raw
        total += cost
    if group:
        groups.append(group)
    need({name for group in groups for name in group} == set(entries), "Grouping lost a member")
    return groups


def inventory(root):
    root = Path(root).resolve()
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            name = path.relative_to(root).as_posix()
            actual = file_under(root, name)
            data = actual.read_bytes()
            result[name] = {"bytes": len(data), "sha256": sha(data)}
    return result


def source_guard(work, tool, approved):
    manifest_path = work / "prereg/manifest.json"
    manifest_raw = manifest_path.read_bytes()
    need(sha(manifest_raw) == approved, "Approved manifest SHA differs")
    manifest = json.loads(manifest_raw.decode("utf-8"))
    freeze = read_json(work / "prereg/source-freeze.json")
    need(manifest["schema"] == "ae1-mixed-flip-continuation-v1", "Wrong mixed continuation manifest")
    need(freeze["manifest_sha256"] == approved and freeze["source_hashes"] == manifest["source_hashes"], "Source freeze differs")
    need(len(manifest["source_hashes"]) == 3 and "protocol.json" in manifest["source_hashes"], "Unexpected source set")
    for name, pin in manifest["source_hashes"].items():
        need(sha(file_under(tool, name).read_bytes()) == pin, f"Core source changed: {name}")
    need(manifest["protocol"]["seeds"] == list(SEEDS) and manifest["protocol"]["replay_seeds"] == [101], "Seed/replay scope differs")
    need(read_json(work / "engineering/checks.json")["status"] == "PASS", "Engineering is not PASS")
    need(read_json(work / "engineering/checks.json")["source_hashes"] == manifest["source_hashes"], "Engineering source pin differs")
    pre = read_json(work / "review/pre-run.json")
    need(pre["status"] == "passed" and pre["manifest_sha256"] == approved, "Independent pre-run gate missing/different")
    need(pre["source_hashes"] == manifest["source_hashes"], "Pre-run source pin differs")
    raw = file_under(work / "prereg", manifest["archive"]["file"]).read_bytes()
    need(len(raw) == manifest["archive"]["bytes"] == freeze["inputs_zip_bytes"]
         and sha(raw) == manifest["archive"]["sha256"] == freeze["inputs_zip_sha256"], "Frozen input ZIP differs")
    need(bool(manifest["files"]), "Frozen input member allowlist is empty")
    archive = inspect_zip(raw, manifest["files"])
    need(archive["members"]["source/p030_binary_continual.py"]["sha256"] == REFERENCE_SHA, "Reference source differs")
    need(archive["finite_arrays"] == {"NPZ": 3, "NPY": 3}, "All three parent states/courses must be finite")
    need(freeze["parents"] == manifest["parents"] and set(manifest["parents"]) == {str(seed) for seed in SEEDS}, "Parent freeze differs")
    for parent in manifest["parents"].values():
        member = archive["members"][parent["file"]]
        need(member["sha256"] == parent["raw_sha256"] == parent["source_member"]["sha256"]
             and all(member[key] == parent["source_member"][key] for key in ("bytes", "Git_blob", "CRC32"))
             and parent["source_archive"]["verified_against_prior_public_readback"] is True,
             "Raw parent state differs from the pinned public archive member")
    return manifest, raw, archive


def add_file(files, originals, root, source, target):
    target = safe_name(target)
    need(target not in files, f"Duplicate public path: {target}")
    path = file_under(root, source)
    data = path.read_bytes()
    check_content(target, data)
    files[target] = data
    originals[path] = sha(data)


def common_files(root, work, tool, manifest, raw_inputs):
    files, originals = {}, {}
    for name in tuple(manifest["source_hashes"]) + ("README.md", "RESEARCH_NOTE.md", "HANDOFF.md", "EXTERNAL_REVIEW.json"):
        add_file(files, originals, tool, name, name)
    for name in ("manifest.json", "source-freeze.json"):
        add_file(files, originals, work / "prereg", name, name)
    files["inputs.zip"] = raw_inputs
    originals[work / "prereg/inputs.zip"] = sha(raw_inputs)
    add_file(files, originals, work, "package_publication.py", "package_publication.py")
    add_file(files, originals, work, "engineering/checks.json", "engineering-checks.json")
    add_file(files, originals, root, "outputs/agent-team/context/ae1_mixed_flip.json", "external-context.json")
    add_file(files, originals, root, "work/agent-team/attempts/nvidia/AE1-MIXED-FLIP-PROSPECTIVE-001/candidate.json", "external-candidate.json")
    add_file(files, originals, work, "external-method-checks.json", "external-method-checks.json")
    for name in REVIEW_PREREG:
        add_file(files, originals, work / "review", name, "review/" + name)
    return files, originals


def proof_names(summary):
    result = {f"numeric-proof/seed{seed}-student.json" for seed in SEEDS}
    result |= {f"numeric-proof/seed{seed}-baseline.json" for seed in SEEDS}
    for student in summary["students"]:
        need(type(student["epochs"]) is int and 1 <= student["epochs"] <= 40, "Invalid actual epochs")
        result |= {f"numeric-proof/seed{student['seed']}-epoch{epoch:03}.json" for epoch in range(1, student["epochs"] + 1)}
    return result


def coordinator_guard(work, manifest, approved):
    git = read_json(work / "git-prereg-receipt.json")
    intent = read_json(work / "execution-intent.json")
    need(git["checked_before_formal"] is True and git["formal_invocations_at_this_receipt"] == 0,
         "Public byte verification did not precede the formal invocation")
    need(git["manifest_sha256"] == intent["manifest_sha256"] == approved,
         "Coordinator manifest differs")
    need(intent["preregistration_commit"] == git["commit"] and intent["formal_invocations"] == 1
         and intent["auto_retry"] is False, "Coordinator execution scope differs")
    need(intent["parent_commit"] == git["parent"] == manifest["protocol"]["parent_head"],
         "Coordinator parent continuation pin differs")
    need(intent["primary_continued_seeds"] == list(SEEDS) and intent["replay_seeds"] == [101]
         and intent["source_hashes"] == manifest["source_hashes"], "Coordinator seed/source pins differ")
    frozen_public = read_json(work / "publication/prereg/compact.json")["public_files"]
    checks = git["public_file_byte_checks"]
    need(len(checks) == len({item["name"] for item in checks}) == len(frozen_public)
         and {item["name"] for item in checks} == set(frozen_public)
         and intent["Git_byte_checks_before_formal"] == len(checks), "Public readback coverage differs")
    for item in checks:
        name = safe_name(item["name"])
        data = file_under(work / "publication/prereg/public", name).read_bytes()
        need(item["byte_match"] is True and item["commit"] == git["commit"]
             and info(data) == frozen_public[name]
             and all(item[key] == frozen_public[name][key] for key in ("bytes", "sha256", "Git_blob")),
             "Actual preregistration byte evidence differs")
    return git, intent


def final_guard(work, manifest, approved, receipt_path):
    post = read_json(work / "review/post-run.json")
    need(post["status"] == "passed" and post["manifest_sha256"] == approved, "Independent post-run gate missing/different")
    need(post["source_hashes"] == manifest["source_hashes"] and post["root_confirmed_formal_exit0"] is True, "Post-run source/exit gate differs")
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw.decode("utf-8-sig"))
    receipt_pin = post.get("receipt_sha256", post.get("metadata", {}).get("receipt_sha256"))
    need(receipt_pin == sha(receipt_raw) and receipt["exit_code"] == 0, "Root receipt bytes/exit differ")
    git, intent = coordinator_guard(work, manifest, approved)
    need(receipt["manifest_sha256"] == approved and receipt["preregistration_commit"] == git["commit"],
         "Root execution receipt coordinator pins differ")
    summary = read_json(work / "science/compact.json")
    need(summary["status"] == "complete" and summary["manifest_sha256"] == approved, "Formal result is incomplete/different")
    need(summary["primary_continued_students"] == 3 and summary["exact_full_replays"] == [101], "Formal continuation/replay scope differs")
    need([student["seed"] for student in summary["students"]] == list(SEEDS), "A seed is missing")
    need([student["replay_status"] for student in summary["students"]] == ["complete_exact", "not_planned", "not_planned"], "Replay disposition differs")
    need((work / "science/manifest.json").read_bytes() == (work / "prereg/manifest.json").read_bytes(), "Actual manifest bytes differ")
    start = read_json(work / "science/execution-start.json")
    need(start["preregistration_commit"] == summary["preregistration_commit"] == git["commit"]
         and start["auto_retry"] is False, "Actual execution does not match coordinator intent")
    details = read_json(work / "review/post-run-details.json")
    actual = inventory(work / "science")
    need(actual == details["science_file_inventory"], "Full actual science inventory differs from independent audit")
    refs = details["numeric_proof_refs"]
    need(isinstance(refs, list) and len(refs) == len(set(refs)) <= 126 and set(refs) == proof_names(summary), "Actual baseline/epoch/student proof list differs")
    proofs = {}
    for name in refs:
        safe_name(name)
        data = file_under(work / "review", name).read_bytes()
        need({"bytes": len(data), "sha256": sha(data)} == details["numeric_proof_inventory"][name], "Independent proof bytes differ")
        proofs["review/" + name] = data
    return summary, details, actual, proofs


def git_records(public, out):
    text, binary, expected = [], [], {}
    for path in sorted(public.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(public).as_posix()
        data = path.read_bytes()
        target = PREFIX + "/" + name
        expected[target] = blob(data)
        if path.suffix == ".zip":
            binary.append({"path": target, "mode": "100644", "type": "blob", **info(data),
                           "local_file": "public/" + name, "upload": "Read exact original bytes; do not print base64 to chat"})
        else:
            content = data.decode("utf-8")
            need(content.encode("utf-8") == data, "Text Git bytes differ")
            text.append({"path": target, "mode": "100644", "type": "blob", "content": content})
    write_json(out / "text-entries.json", text)
    write_json(out / "binary-entries.json", binary)
    write_json(out / "expected-blobs.json", expected)
    return {"text_entries": len(text), "binary_entries": len(binary), "base64_chunks": 0}


def package(mode, root, work, tool, approved, out, receipt=None, stdout=None, stderr=None):
    root, work, tool, out = (Path(value).resolve() for value in (root, work, tool, out))
    need(not out.exists(), "Publication destination exists; do not overwrite")
    manifest, raw_inputs, input_index = source_guard(work, tool, approved)
    files, originals = common_files(root, work, tool, manifest, raw_inputs)
    archives = {"inputs.zip": {**info(raw_inputs), **input_index, "exact_frozen_container": True,
                               "oversize_for_result_group_cap": len(raw_inputs) > GROUP_BYTES}}
    science_inventory, course_usage = {}, {}
    if mode == "final":
        need(receipt is not None and stdout is not None and stderr is not None, "Final requires exact receipt/stdout/stderr paths")
        receipt, stdout, stderr = (Path(value).resolve() for value in (receipt, stdout, stderr))
        summary, details, science_inventory, proofs = final_guard(work, manifest, approved, receipt)
        add_file(files, originals, tool, "RESULTS.md", "RESULTS.md")
        add_file(files, originals, work, "derived-readout.json", "derived-readout.json")
        for name in ("git-prereg-receipt.json", "execution-intent.json"):
            add_file(files, originals, work, name, name)
        science = {"science/" + name: file_under(work / "science", name).read_bytes() for name in science_inventory}
        covered = set()
        for seed in SEEDS:
            selected = {name: data for name, data in science.items() if name.startswith(f"science/seed{seed}/")}
            need(bool(selected), "Missing seed science")
            for index, group in enumerate(group_entries(selected), 1):
                name = f"science-seed{seed}-{index:03}.zip"
                raw, audit = make_zip(group)
                need(len(raw) <= GROUP_BYTES or len(group) == 1, "Unexpected multi-member oversize ZIP")
                files[name] = raw
                archives[name] = {**info(raw), **audit, "oversized_single_member_preserved": len(raw) > GROUP_BYTES}
                covered |= set(group)
        metadata = {name: data for name, data in science.items() if name not in covered}
        for index, group in enumerate(group_entries(metadata), 1):
            name = f"science-metadata-{index:03}.zip"
            raw, audit = make_zip(group)
            files[name] = raw
            archives[name] = {**info(raw), **audit, "oversized_single_member_preserved": len(raw) > GROUP_BYTES}
            covered |= set(group)
        need(covered == set(science), "An actual science file was omitted")
        evidence = dict(proofs)
        for name in REVIEW_FINAL:
            add_file(files, originals, work / "review", name, "review/" + name)
            evidence["review/" + name] = files["review/" + name]
        for path, name in ((receipt, "execution-receipt.json"), (stdout, "execution.stdout.log"), (stderr, "execution.stderr.log")):
            need(path.is_file() and path.is_relative_to(work), "Execution record is outside the authorized work root")
            evidence[name] = path.read_bytes()
            originals[path] = sha(evidence[name])
        for index, group in enumerate(group_entries(evidence), 1):
            name = f"independent-evidence-{index:03}.zip"
            raw, audit = make_zip(group)
            files[name] = raw
            archives[name] = {**info(raw), **audit, "oversized_single_member_preserved": len(raw) > GROUP_BYTES}
        for name in ("compact.json", "timing.json", "storage.json", "execution-start.json"):
            add_file(files, originals, work / "science", name, name)
        for student in summary["students"]:
            key = str(student['seed'])
            frozen = manifest["schedules"][key]
            course_usage[key] = {"file": frozen["file"], "prefrozen_epochs": frozen["shape"][0],
                                 "actual_primary_epochs": student["epochs"],
                                 "unused_prefrozen_epochs_retained": frozen["shape"][0] - student["epochs"],
                                 "full_replay": student["seed"] == 101}
    for path, pin in originals.items():
        need(sha(path.read_bytes()) == pin, "An original file changed while preparing publication")
    if mode == "final":
        need(inventory(work / "science") == science_inventory, "Science changed during packaging")
        for name, data in proofs.items():
            need(file_under(work / "review", name.removeprefix("review/")).read_bytes() == data, "Independent proof changed")
    # Every payload and ZIP has been checked before creating the public directory.
    for name, data in files.items():
        if not name.endswith(".zip"):
            check_content(name, data)
    finite = {key: sum(archive["finite_arrays"][key] for archive in archives.values()) for key in ("NPZ", "NPY")}
    publication = {"schema": "ae1-mixed-flip-publication-v1", "status": "verified", "mode": mode,
                   "manifest_sha256": approved, "source_hashes": manifest["source_hashes"], "author": "Codex",
                   "continuation_parent_states": manifest["parents"],
                   "cost_scope": "New optimizer/training/probe counts are deltas; inherited parent counters are retained separately, not new work.",
                   "files": {name: info(data) for name, data in sorted(files.items())}, "archives": archives,
                   "complete_science_inventory": science_inventory, "science_files": len(science_inventory),
                   "prefrozen_courses_including_unused": course_usage, "finite_arrays": finite,
                   "all_actual_science_files_preserved": mode == "final", "ZIP_byte_roundtrip_passed": True,
                   "package_model_inference_optimizer_external_calls": 0,
                   "external_round_dispositions_source": "EXTERNAL_REVIEW.json",
                   "private_transport_quota_chat_or_autonomous_state_selected": False,
                   "manifest_and_checks_excluded_from_self_inventory": True}
    files["publication-manifest.json"] = json_bytes(publication)
    checks = {"status": "PASS", "mode": mode, "frozen_inputs_byte_identical": True,
              "archive_members_size_CRC_SHA_byte_verified": sum(item["member_count"] for item in archives.values()),
              "finite_arrays": finite, "full_actual_science_files": len(science_inventory),
              "all_science_preserved": mode == "final", "privacy_checked_every_public_member": True,
              "original_source_and_input_hashes_unchanged": True, "model_optimizer_inference_external_calls": 0}
    files["export-checks.json"] = json_bytes(checks)
    out.mkdir(parents=True, exist_ok=False)
    public = out / "public"
    public.mkdir()
    for name, data in sorted(files.items()):
        target = public / safe_name(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        need(target.read_bytes() == data, "Published bytes differ")
    records = git_records(public, out)
    result = {"status": "verified", "mode": mode, "repo_prefix": PREFIX, "manifest_sha256": approved,
              "public_files": {name: info(data) for name, data in sorted(files.items())},
              "archive_indexes": {name: {key: value for key, value in archive.items() if key != "members"} for name, archive in archives.items()},
              "full_archive_member_indexes": "public/publication-manifest.json",
              "full_science_inventory": "public/publication-manifest.json",
              "complete_science_coverage": {"actual_files": len(science_inventory), "all_preserved": mode == "final"},
              "finite_arrays": finite, "checks": checks, **records, "packager_sha256": sha(Path(__file__).read_bytes())}
    write_json(out / "compact.json", result)
    return result


def self_test(out):
    import numpy as np
    out = Path(out).resolve()
    need(not out.exists(), "Self-test destination exists")
    out.mkdir(parents=True)
    checks = []
    with tempfile.TemporaryDirectory(dir=out) as temporary:
        state = io.BytesIO()
        np.savez(state, p=np.array([0, 1], dtype=np.float32), meta=np.array('{"t":0}'))
        entries = {"synthetic/state.npz": state.getvalue(), "synthetic/data.json": json_bytes({"value": "繁體"})}
        raw, audit = make_zip(entries)
        need(make_zip(entries)[0] == raw and audit["finite_arrays"]["NPZ"] == 1, "ZIP determinism/NPZ failed")
        checks.append("deterministic ZIP full byte/CRC/SHA roundtrip and finite NPZ")
        for name in ("../escaped.json", "/absolute.json", "x\\y.json", "x/.git/key.json"):
            try:
                safe_name(name)
            except ValueError:
                pass
            else:
                raise AssertionError("Unsafe member accepted")
        for data in (json_bytes({"access_token": "secret"}), json_bytes({"path": "C:" + "/Us" + "ers/" + "synthetic"})):
            try:
                check_content("bad.json", data)
            except ValueError:
                pass
            else:
                raise AssertionError("Private metadata accepted")
        checks.append("unsafe paths and private metadata rejected")
        bad = io.BytesIO()
        np.savez(bad, p=np.array([float("nan")]))
        try:
            check_content("bad.npz", bad.getvalue())
        except ValueError:
            pass
        else:
            raise AssertionError("Nonfinite NPZ accepted")
        checks.append("nonfinite actual-array validation rejects NaN")
        data = io.BytesIO()
        np.save(data, np.random.default_rng(910013).integers(0, 256, 7_400_000, dtype=np.uint8), allow_pickle=False)
        large = {"orders/synthetic.npy": data.getvalue()}
        groups = group_entries(large)
        large_zip, large_audit = make_zip(groups[0])
        need(len(groups) == 1 and len(large_zip) > GROUP_BYTES and large_audit["finite_arrays"]["NPY"] == 1, "Oversize member dropped")
        need(inspect_zip(large_zip, large)["member_count"] == 1, "Large frozen ZIP unsupported")
        checks.append("larger-than-seven-MB frozen ZIP and oversized single member retained")
        check_content("package_publication.py", Path(__file__).read_bytes())
    result = {"status": "PASS", "checks": checks, "scientific_modules_imported": False,
              "formal_results_read": False, "model_optimizer_inference_external_calls": 0,
              "packager_sha256": sha(Path(__file__).read_bytes())}
    write_json(out / "checks.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prereg", "final", "self-test"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--work", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--tool", type=Path)
    parser.add_argument("--approved-manifest-sha")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stdout", type=Path)
    parser.add_argument("--stderr", type=Path)
    args = parser.parse_args()
    if args.mode == "self-test":
        result = self_test(args.out)
    else:
        need(args.approved_manifest_sha is not None, "Explicit approved manifest SHA required")
        tool = args.tool or args.root / "outputs/ae1-mixed-flip"
        result = package(args.mode, args.root, args.work, tool, args.approved_manifest_sha, args.out,
                         args.receipt, args.stdout, args.stderr)
    print(json.dumps({key: result[key] for key in result if key not in ("public_files", "archive_indexes", "checks")}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
