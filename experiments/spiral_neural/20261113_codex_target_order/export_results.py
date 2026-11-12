"""Explicit public evidence exporter; never imports a learner or calls a model.

`dependencies` packages the twelve fixed Windows control inputs for preregistration.
`finalize` is reserved for the complete three-seed run and independent post-run PASS.
The two modes create new directories and never overwrite scientific artifacts.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import gzip
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile


SEEDS = (101, 202, 303)
EPOCHS = (0, 16, 32, 64, 96, 128)
PREFIX = "experiments/spiral_neural/20261113_codex_target_order"
CONTROL_MANIFEST_SHA = "d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0"
CHUNK_CHARACTERS = 12000
MAX_ZIP_BYTES = 3_000_000
PRIVATE_KEYS = frozenset(("private_raw_api_record", "private_legacy_record", "raw_api_path",
                          "api_key", "access_token", "refresh_token", "id_token",
                          "authorization_header", "account_quota", "quota_remaining"))
PRIVATE_TEXT = re.compile(r"(?i)(?:[A-Z]:[\\/]Users[\\/]|/ho" r"me/|/Us" r"ers/|"
                          r"Bearer\s+[A-Za-z0-9._-]{8,}|sk-or-v1-[A-Za-z0-9]+)")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def json_bytes(value):
    # Explicit LF bytes avoid Windows text newline translation.
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(Path(path).read_bytes().decode("utf-8"))


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json_bytes(value).decode("utf-8"))


def metadata(data):
    return {"bytes": len(data), "sha256": sha(data), "Git_blob": git_blob(data)}


def safe_relative(name):
    require(isinstance(name, str) and bool(name) and "\\" not in name, "Invalid relative path")
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(part not in ("", ".", "..") for part in path.parts)
            and ":" not in name, f"Unsafe path: {name}")
    require(not any(part.casefold() in (".git", ".ssh", ".aws", "fontcache", "__pycache__")
                    for part in path.parts), f"Private/cache path: {name}")
    return path.as_posix()


def source_file(root, name):
    name = safe_relative(name)
    root = Path(root).resolve()
    path = (root / name).resolve()
    require(path.is_relative_to(root) and path.is_file(), f"Missing or escaped source: {name}")
    return path


def scan_json(value, label):
    if isinstance(value, dict):
        for key, item in value.items():
            require(key.casefold() not in PRIVATE_KEYS, f"Private metadata field: {label}/{key}")
            scan_json(item, f"{label}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            scan_json(item, f"{label}/{index}")
    elif isinstance(value, str):
        require(not PRIVATE_TEXT.search(value), f"Private path/credential: {label}")
    elif isinstance(value, float):
        require(math.isfinite(value), f"Nonfinite JSON number: {label}")


def validate_content(name, data):
    suffix = PurePosixPath(name).suffix.lower()
    if suffix == ".npz":
        import numpy as np
        with np.load(io.BytesIO(data), allow_pickle=False) as arrays:
            require(bool(arrays.files), f"Empty NPZ: {name}")
            for key in arrays.files:
                array = arrays[key]
                require(not array.dtype.hasobject, f"Pickled NPZ: {name}/{key}")
                if np.issubdtype(array.dtype, np.number):
                    require(bool(np.isfinite(array).all()), f"Nonfinite NPZ: {name}/{key}")
                elif array.dtype.kind in "US":
                    for text in array.ravel().tolist():
                        text = text.decode("utf-8") if isinstance(text, bytes) else text
                        require(not PRIVATE_TEXT.search(text), f"Private NPZ metadata: {name}/{key}")
                        try:
                            scan_json(json.loads(text), f"{name}/{key}")
                        except json.JSONDecodeError:
                            pass
        return 1
    require(suffix in (".json", ".md", ".py"), f"Unallowlisted content kind: {name}")
    text = data.decode("utf-8")
    require(not PRIVATE_TEXT.search(text), f"Private text: {name}")
    # Scientific source/guarded JSON is copied byte-for-byte; reject rather than normalize it.
    require(b"\r" not in data, f"Public text requires LF; use an explicitly recorded metadata copy: {name}")
    if suffix == ".json":
        scan_json(json.loads(text), name)
    return 0


@dataclass(frozen=True)
class Entry:
    name: str
    data: bytes
    source: Path | None = None
    source_sha256: str | None = None


def exact_entry(root, source_name, archive_name=None):
    path = source_file(root, source_name)
    data = path.read_bytes()
    return Entry(safe_relative(archive_name or source_name), data, path, sha(data))


def metadata_copy(root, source_name, archive_name, redactions):
    """Only explicit private fields/path prefixes may be removed; list every change."""
    path = source_file(root, source_name)
    original = path.read_bytes()
    changed = []
    root_text = str(Path(root).resolve())

    def clean(value, pointer=""):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                here = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                if key.casefold() in PRIVATE_KEYS:
                    changed.append({"pointer": here, "action": "removed_private_metadata_field"})
                else:
                    result[key] = clean(item, here)
            return result
        if isinstance(value, list):
            return [clean(item, pointer + "/" + str(i)) for i, item in enumerate(value)]
        if isinstance(value, str):
            for prefix in (root_text + "\\", Path(root_text).as_posix() + "/"):
                if value.startswith(prefix):
                    changed.append({"pointer": pointer, "action": "made_workspace_path_relative"})
                    return value[len(prefix):].replace("\\", "/")
        return value

    copied = json_bytes(clean(json.loads(original.decode("utf-8"))))
    redactions.append({"public_path": archive_name, "source_sha256": sha(original),
                       "public_sha256": sha(copied), "changes": changed,
                       "LF_JSON_serialization": True, "scientific_values_changed": False})
    return Entry(safe_relative(archive_name), copied, path, sha(original))


def write_archive(public, name, entries):
    require(name.endswith(".zip") and safe_relative(name) == name, "Invalid archive name")
    require(len({entry.name for entry in entries}) == len(entries), "Duplicate archive member")
    members, finite_count = [], 0
    target = public / name
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in sorted(entries, key=lambda item: item.name):
            safe_relative(entry.name)
            finite_count += validate_content(entry.name, entry.data)
            info = zipfile.ZipInfo(entry.name, (2026, 11, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entry.data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            members.append({"path": entry.name, **metadata(entry.data)})
    require(target.stat().st_size < MAX_ZIP_BYTES, f"Archive exceeds {MAX_ZIP_BYTES} bytes: {name}")
    with zipfile.ZipFile(target, "r") as archive:
        require(archive.testzip() is None and len(archive.infolist()) == len(entries), "Bad ZIP")
        for entry in entries:
            require(archive.read(entry.name) == entry.data, f"ZIP byte roundtrip failed: {entry.name}")
            if entry.source is not None:
                require(sha(entry.source.read_bytes()) == entry.source_sha256, f"Source changed: {entry.name}")
    return {"file": name, **metadata(target.read_bytes()), "entries": members,
            "entry_count": len(members), "NPZ_finite_verified": finite_count}


def git_records(public, out, prefix):
    prefix = safe_relative(prefix)
    texts, binaries, expected = [], [], {}
    for path in sorted(public.iterdir()):
        require(path.is_file(), "Public tree may contain only explicit top-level files")
        data = path.read_bytes()
        target = prefix + "/" + path.name
        expected[target] = git_blob(data)
        if path.suffix == ".zip":
            encoded = base64.b64encode(data).decode("ascii")
            folder = out / "base64-chunks" / path.name
            folder.mkdir(parents=True, exist_ok=False)
            chunks = []
            for index, start in enumerate(range(0, len(encoded), CHUNK_CHARACTERS)):
                part = folder / f"{index:05}.txt"
                part.write_bytes(encoded[start:start + CHUNK_CHARACTERS].encode("ascii"))
                chunks.append(part.relative_to(out).as_posix())
            restored = base64.b64decode("".join((out / part).read_bytes().decode("ascii") for part in chunks), validate=True)
            require(restored == data, f"Base64 roundtrip failed: {path.name}")
            binaries.append({"path": target, "mode": "100644", "type": "blob", **metadata(data),
                             "base64_characters": len(encoded), "chunk_characters": CHUNK_CHARACTERS,
                             "chunks": chunks})
        else:
            validate_content(path.name, data)
            content = data.decode("utf-8")  # No universal-newline translation before Git hashing.
            require(content.encode("utf-8") == data, "Text Git entry bytes differ")
            texts.append({"path": target, "mode": "100644", "type": "blob", "content": content})
    write_json(out / "text-entries.json", texts)
    write_json(out / "binary-entries.json", binaries)
    write_json(out / "expected-blobs.json", expected)
    return {"public_files": len(expected), "text_entries": len(texts), "binary_entries": len(binaries),
            "binary_bytes": sum(item["bytes"] for item in binaries),
            "base64_chunks": sum(len(item["chunks"]) for item in binaries)}


def baseline_names():
    names = ["manifest.json", "summary.json", "codex-execution-provenance.json"]
    for seed in SEEDS:
        names += [f"seed{seed}/{name}" for name in ("initial-state.npz", "curve.json", "offline-curve.json")]
    return names


def package_dependencies(control_root, out, prefix):
    """Read only the already-audited original-order control, never new results."""
    control_root, out = Path(control_root).resolve(), Path(out).resolve()
    require(not out.exists(), "Dependency output exists; do not overwrite")
    entries = [exact_entry(control_root, name, "baseline/" + name) for name in baseline_names()]
    original_hashes = {entry.name: sha(entry.data) for entry in entries}
    require(sha((control_root / "manifest.json").read_bytes()) == CONTROL_MANIFEST_SHA, "Control manifest differs")
    summary = read_json(control_root / "summary.json")
    provenance = read_json(control_root / "codex-execution-provenance.json")
    require(summary["status"] == provenance["status"] == "complete", "Control incomplete")
    require(summary["complete_trajectories"] == summary["exact_replays"] == 3, "Control replay incomplete")
    require([item["seed"] for item in summary["students"]] == list(SEEDS), "Control seeds differ")
    out.mkdir(parents=True, exist_ok=False)
    public = out / "public"
    public.mkdir()
    archive = write_archive(public, "baseline-inputs.zip", entries)
    manifest = {"schema": "sle-target-order-baseline-inputs-v1", "source_kind": "Windows replication of Pro fixed control",
                "original_manifest_sha256": CONTROL_MANIFEST_SHA, "new_independent_control_seeds": 0,
                "restore": "Extract baseline-inputs.zip into a new directory; pass its baseline/ directory as --control-root.",
                "layout": "baseline/<original science-relative path>", "archives": [archive],
                "full_control_target_trace_republished": False,
                "control_raw_bytes_preserved": True, "Pro_NPZ_or_truth_byte_identity_claimed": False}
    write_json(public / "baseline-inputs-manifest.json", manifest)
    for entry in entries:
        require(sha(entry.source.read_bytes()) == original_hashes[entry.name], f"Original changed: {entry.name}")
    checks = {"status": "PASS", "source_files_unchanged": len(entries), "archive_members_byte_verified": len(entries),
              "NPZ_finite_verified": archive["NPZ_finite_verified"], "privacy_checked_all_members": True,
              "learning_optimizer_or_model_calls": 0, "new_target_order_results_read": False,
              "large_control_trace_republished": False, "LF_text_Git_bytes_exact": True}
    write_json(public / "baseline-inputs-checks.json", checks)
    counts = git_records(public, out, prefix)
    compact = {"status": "PASS", "mode": "preregistration_dependencies", "repo_prefix": prefix,
               "archives": [{key: value for key, value in archive.items() if key != "entries"}],
               **counts, "checks": checks}
    write_json(out / "compact.json", compact)
    return compact


def restore_dependencies(archive_path, manifest_path, approved_manifest_sha, out):
    """Verify the complete allowlist before writing any member into a fresh root."""
    archive_path, manifest_path, out = Path(archive_path), Path(manifest_path), Path(out).resolve()
    require(not out.exists(), "Restore destination exists; never overwrite")
    manifest_data = manifest_path.read_bytes()
    require(sha(manifest_data) == approved_manifest_sha, "Explicit input manifest SHA differs")
    manifest = json.loads(manifest_data.decode("utf-8"))
    require(manifest["schema"] == "sle-target-order-baseline-inputs-v1", "Unexpected dependency schema")
    require(manifest["original_manifest_sha256"] == CONTROL_MANIFEST_SHA, "Wrong control manifest")
    require(len(manifest["archives"]) == 1, "Expected exactly one dependency ZIP")
    expected = manifest["archives"][0]
    content = archive_path.read_bytes()
    require(len(content) < MAX_ZIP_BYTES and metadata(content) == {key: expected[key] for key in metadata(content)},
            "Dependency ZIP size/SHA/Gitblob differs")
    entries = expected["entries"]
    require(expected["entry_count"] == len(entries) == 12, "Unexpected dependency count")
    wanted = {"baseline/" + name for name in baseline_names()}
    require({item["path"] for item in entries} == wanted and len(wanted) == len(entries), "Dependency allowlist differs")
    require(sum(item["bytes"] for item in entries) < 32_000_000, "Dependency extraction exceeds cap")
    members = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        infos = archive.infolist()
        require(len(infos) == len(entries) and {info.filename for info in infos} == wanted, "ZIP entries differ")
        by_name = {item["path"]: item for item in entries}
        for info in infos:
            safe_relative(info.filename)
            require(not info.is_dir() and not (info.flag_bits & 1), "Directory/encrypted ZIP entry")
            require((info.external_attr >> 16) & 0o170000 in (0, 0o100000), "Nonregular ZIP entry")
            require(info.file_size == by_name[info.filename]["bytes"] < 10_000_000, "ZIP member size differs")
            data = archive.read(info)
            require(metadata(data) == {key: by_name[info.filename][key] for key in metadata(data)}, "ZIP member hash differs")
            validate_content(info.filename, data)
            members[info.filename] = data
    require(sha(members["baseline/manifest.json"]) == CONTROL_MANIFEST_SHA, "Embedded original manifest differs")
    out.mkdir(parents=True, exist_ok=False)
    for name, data in sorted(members.items()):
        target = (out / name).resolve()
        require(target.is_relative_to(out), "Restore path escaped")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        require(target.read_bytes() == data, "Restored bytes differ")
    result = {"status": "PASS", "restored_files": len(members), "NPZ_finite_verified": 3,
              "approved_input_manifest_sha256": approved_manifest_sha, "archive_sha256": sha(content),
              "every_member_verified_before_writing": True, "new_output_only": True,
              "learning_optimizer_or_model_calls": 0}
    write_json(out / "restore-checks.json", result)
    return result


def result_names(seed):
    root = f"seed{seed}/"
    names = ["initial-state.npz", "final-state.npz", "curve.json", "offline-curve.json",
             "training-summary.json", "final-truth.json", "final-failures.json"]
    names += [f"state-{epoch:03}.npz" for epoch in EPOCHS]
    names += [f"train-truth-{epoch:03}.json" for epoch in EPOCHS]
    names += [f"offline-truth-{epoch:03}.json" for epoch in EPOCHS[:-1]]
    return [root + name for name in names]


def verify_final_gate(base, code, original_root, approved_sha):
    """The independent completion gate is read before any new scientific result."""
    prereg, reviews = base / "prereg", base / "review"
    post = read_json(reviews / "post-run.json")
    pre = read_json(reviews / "pre-run.json")
    require(post["status"] == pre["status"] == "passed", "Independent review is incomplete")
    require(post["manifest_sha256"] == pre["manifest_sha256"] == approved_sha, "Reviewed manifest differs")
    require(post.get("root_confirmed_formal_exit0") is True, "Independent audit did not confirm formal exit0")
    raw = source_file(prereg, "manifest.json").read_bytes()
    require(sha(raw) == approved_sha, "Explicit approved manifest SHA differs")
    manifest = json.loads(raw.decode("utf-8"))
    freeze = read_json(prereg / "source-freeze.json")
    require(freeze["manifest_sha256"] == approved_sha, "Source freeze differs")
    require(freeze["local_source_hashes"] == manifest["local_source_hashes"]
            and freeze["original_source_hashes"] == manifest["original_source_hashes"], "Source maps differ")
    require(pre["source_hashes"] == post["source_hashes"] == manifest["local_source_hashes"]
            and post["original_source_hashes"] == manifest["original_source_hashes"], "Reviewed source maps differ")
    root_gate, git = read_json(base / "formal-root-gate.json"), read_json(base / "prereg-git.json")
    require(root_gate["preregistration"] == git and git["manifest_sha256"] == approved_sha, "Root preregistration gate differs")
    require(root_gate["formal_launches_authorized"] == 1 and root_gate["auto_retry"] is False
            and root_gate["baseline_control_retraining"] is False, "Root launch/control scope differs")
    require(len(git["remote_byte_verifications"]) == 8
            and all(item["verified"] is True for item in git["remote_byte_verifications"]), "Remote preregistration bytes were not fully checked")
    receipt = read_json(base / "formal-receipt.json")
    require(sha((base / "formal-receipt.json").read_bytes()) == post["formal_receipt_sha256"], "Reviewed root receipt bytes differ")
    require(receipt["status"] == "complete" and receipt["exit_code"] == 0, "Root formal process is incomplete or nonzero")
    require(receipt["preregistration_commit"] == git["commit"] and receipt["manifest_sha256"] == approved_sha
            and receipt["driver_sha256"] == manifest["local_source_hashes"]["run_target_order.py"], "Root execution receipt pin differs")
    require(receipt["authorized_formal_launches"] == 1 and receipt["auto_retry"] is False
            and receipt["complete_trajectories"] == receipt["exact_replays"] == 3, "Root execution/replay scope differs")
    for root, hashes in ((code, manifest["local_source_hashes"]), (original_root, manifest["original_source_hashes"])):
        for name, expected in hashes.items():
            require(sha(source_file(root, name).read_bytes()) == expected, f"Pinned source changed: {name}")
    require(post.get("launcher_sha256", manifest["local_source_hashes"]["run_target_order.py"])
            == manifest["local_source_hashes"]["run_target_order.py"], "Reviewed runner differs")
    require(manifest["protocol"]["seeds"] == list(SEEDS), "All three fixed seeds required")
    require(manifest["protocol"]["checkpoint_epochs"] == list(EPOCHS), "Fixed checkpoints differ")
    return manifest, pre, post


def trace_record(science, seed):
    path = source_file(science, f"seed{seed}/targets.jsonl.gz")
    summary = read_json(science / f"seed{seed}/training-summary.json")
    data = path.read_bytes()
    require(sha(data) == summary["trace_file_sha256"], "Compressed target trace differs")
    stream_sha, count = hashlib.sha256(), 0
    with gzip.open(path, "rb") as stream:
        for line in stream:
            stream_sha.update(line)
            count += 1
    require(count == summary["trace"]["targets"] == 27136, "Target trace count differs")
    require(stream_sha.hexdigest() == summary["trace"]["uncompressed_stream_sha256"], "Target stream SHA differs")
    return {"path": f"seed{seed}/targets.jsonl.gz", **metadata(data), "targets": count,
            "uncompressed_stream_sha256": stream_sha.hexdigest(),
            "public": False, "reason": "Complete trace stays local; frozen input stream and full checkpoints are public."}


def artifact_inventory(root):
    return {path.relative_to(root).as_posix(): {"bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
            for path in sorted(root.rglob("*")) if path.is_file()}


def external_accounting(baseline_base):
    path = baseline_base / "review/nvidia-semantic-review.json"
    record = read_json(path)
    require(record["CLI_invocations"] == 1 and record["retry"] is False, "External call accounting differs")
    require(record["actual_usage"]["cost"] == 0 and record["status"] == "semantic_rejected", "External review disposition differs")
    return {"scope": "Whole user continuation round, including the Windows control replication review",
            "target_order_driver_external_calls": 0,
            "nvidia": {"actual_calls": 1, "cost": 0, "status": record["status"], "task_id": record["task_id"],
                       "reason": record["reason"], "accepted_as_scientific_evidence": False, "auto_retry": False},
            "gemini": {"actual_calls": 0, "status": "skipped_runtime_isolation_unverified"},
            "local_semantic_review_source_sha256": sha(path.read_bytes()),
            "raw_API_account_or_quota_record_exported": False}


def result_report(summary, timing, manifest, baseline, baseline_timing, external, truth_by_seed, receipt):
    lines = ["# UR1：target 更新次序診斷（2026-11-13）", "",
             "ChatGPT Pro 提出原任務與次序對照；Codex 實作新 driver、執行並保存結果。唯一變因是每 epoch 將原12題的212個教師 prefix/target 配對全部洗牌。模型、教材、初態、Adam、128 epochs、27,136 updates／seed 與 training dense MAC 固定。", "",
             "控制組重用 Pro 原序結果；本回合 Windows 同課程重現是執行旁證及額外實跑成本，不是新獨立 seed 或另一個研究條件。", "",
             "| seed | 已教整串：原序→target 洗牌 | 整串差 | 已教地址：原序→target 洗牌 | 地址差 | 已曝光 heldout | strong fit |",
             "|---|---:|---:|---:|---:|---:|---|"]
    by_seed = {item["seed"]: item for item in baseline["students"]}
    for item in summary["students"]:
        old = by_seed[item["seed"]]["metrics"]["train"]
        new, held = item["metrics"]["train"], item["metrics"]["heldout"]
        diff = item["paired_difference"]
        lines.append(f"| {item['seed']} | {old['whole_correct']}→{new['whole_correct']}/12 | {diff['train_whole_correct']:+d} | {old['address_correct']}→{new['address_correct']}/12 | {diff['train_address_correct']:+d} | {held['whole_correct']}/6 | {item['strong_fit_gate']} |")
    new_whole = sum(item["metrics"]["train"]["whole_correct"] for item in summary["students"])
    old_whole = sum(item["metrics"]["train"]["whole_correct"] for item in baseline["students"])
    new_address = sum(item["metrics"]["train"]["address_correct"] for item in summary["students"])
    old_address = sum(item["metrics"]["train"]["address_correct"] for item in baseline["students"])
    fits = sum(item["strong_fit_gate"] for item in summary["students"])
    held = sum(item["metrics"]["heldout"]["whole_correct"] for item in summary["students"])
    held_address = sum(item["metrics"]["heldout"]["address_correct"] for item in summary["students"])
    lines += ["", f"最終已教整串由原序{old_whole}/36提高到{new_whole}/36；地址由{old_address}/36到{new_address}/36。strong fit為{fits}/3學生，三seed全過＝{summary['strong_fit_gate_all_three']}。這支持本固定配置的擬合改善；已曝光heldout整串{held}/18、地址{held_address}/18，沒有完整回覆的搭配泛化成功。", "",
              "strong fit門檻是各 seed 最終 train 整串與地址都12/12；整串含正確 STOP。保留題先前已查看，是已曝光的搭配診斷，不是新盲測。三 seed 重用同六個題域。", "",
              "固定 epoch96／128 的已教整串／地址如下；所有 checkpoint 皆保留，沒有依分數選點：", ""]
    for item in summary["students"]:
        values = "; ".join(f"epoch{point['epoch']}={point['metrics']['train']['whole_correct']}/12 整串、{point['metrics']['train']['address_correct']}/12 地址" for point in item["stability"])
        lines.append(f"- seed{item['seed']}：{values}。")
    failure_counts = {seed: sum(not row["whole_correct"] for row in truth_by_seed[seed]) for seed in SEEDS}
    lines += ["", f"全部最終失敗共{sum(failure_counts.values())}題，seed101／202／303依序{failure_counts[101]}／{failure_counts[202]}／{failure_counts[303]}題；完整來源為各 `evidence-seed<seed>.zip/seed<seed>/final-failures.json` 與 `final-truth.json`。teacher forcing、logits、首錯位置及全部固定checkpoint truth一併保存。以下只列每 seed 依原題序的前兩個失敗，不據此挑 seed：", ""]
    for seed in SEEDS:
        failed = [row for row in truth_by_seed[seed] if not row["whole_correct"]]
        if not failed:
            lines.append(f"- seed{seed}：全18題無失敗。")
        for row in failed[:2]:
            lines.append(f"- seed{seed}／{row['id']}（{row['split']}）：target `{row['target']}`；generated `{row['generated']}`；首錯位置（從0起）{row['first_error_position_zero_based']}。")
    cap_rows = [(seed, row) for seed in SEEDS for row in truth_by_seed[seed] if row["cap_exhausted"]]
    overflow_rows = [(seed, row) for seed in SEEDS for row in truth_by_seed[seed] if row["overflow"]]
    lines += ["", f"最終 generation cap耗盡{len(cap_rows)}題，context overflow {len(overflow_rows)}題。上限保留原24動作，不強補STOP、不延長；所有固定checkpoint cap案例保存在完整truth，最終案例：", ""]
    if not cap_rows:
        lines.append("- 最終無cap耗盡。")
    for seed, row in cap_rows:
        lines.append(f"- seed{seed}／{row['id']}（{row['split']}）：generated `{row['generated']}`；target `{row['target']}`；來源 `evidence-seed{seed}.zip/seed{seed}/final-truth.json` 與 `final-failures.json`。")
    lines += ["", "## 來源、重播與成本", "",
              f"新事前Git提交：`{receipt['preregistration_commit']}`；manifest SHA256：`{summary['manifest_sha256']}`；原控制 manifest：`{CONTROL_MANIFEST_SHA}`。原七份科學來源與新三份 source freeze 原樣核對，初態包含 p/m/v/birth/t/RNG 與 counters。", "",
              f"新 target-order 完成3 primary＋3完整 exact replay。primary／replay 各{summary['primary_targets']:,} updates、{summary['primary_training_dense_MAC']:,} training dense MAC，合計{summary['primary_targets'] + summary['replay_targets']:,} updates、{summary['primary_training_dense_MAC'] + summary['replay_training_dense_MAC']:,} MAC。", "",
              f"本使用者回合另已完成 Windows 原序控制重現：primary／replay 各{baseline['primary_targets']:,} updates、{baseline['primary_training_dense_MAC']:,} MAC。這是額外實跑成本，不加入新條件或獨立 seed 數。兩批含 replay 的 training 合計{summary['primary_training_dense_MAC'] + summary['replay_training_dense_MAC'] + baseline['primary_training_dense_MAC'] + baseline['replay_training_dense_MAC']:,} dense MAC。", "",
              f"新批 primary／replay 的訓練診斷各{summary['primary_training_diagnostic_dense_MAC']:,} MAC；離線推論另{summary['offline_evaluation_inference_calls']:,} calls／{summary['offline_evaluation_dense_MAC']:,} MAC。新程序包含 trace／checkpoint／重播／守門／離線診斷共{timing['total_seconds']:.6f}秒；Windows控制重現另{baseline_timing['total_seconds']:.6f}秒。相同 training dense MAC 不表示所有推論、IO、硬體 FLOPs、能源或牆鐘成本相等。", "",
              f"Windows 控制重現的 primary／replay 訓練診斷各{baseline['primary_training_diagnostic_dense_MAC']:,} MAC，離線推論另{baseline['offline_evaluation_inference_calls']:,} calls／{baseline['offline_evaluation_dense_MAC']:,} MAC；獨立唯讀稽核額外推論見各 post-run.json，未混作訓練更新。", "",
              f"唯一正式程序session{receipt['session_id']}、exit_code={receipt['exit_code']}。root守門在 {receipt['root_gate_checked_UTC']}，觀察仍執行於 {receipt['root_observed_running_UTC']}，觀察退出於 {receipt['root_observed_exit_UTC']}。精確process_start_UTC與actual_process_exit_UTC分別為{json.dumps(receipt['process_start_UTC'])}與{json.dumps(receipt['actual_process_exit_UTC'])}；這些UTC是觀測界線，非從檔案mtime反推的程序起訖。driver以perf_counter量得{receipt['driver_measured_seconds']:.6f}秒。", "",
              "獨立 post-run 稽核 PASS 只表示來源、課程、狀態及保存結果一致，不代表 strong fit 成功。全部三 seed／六個固定 checkpoint／最終失敗完整保留；大逐 target trace 只公開壓縮與未壓縮 stream SHA，完整檔留本機，可用固定來源重建。", "",
              "Windows 與 Pro 控制摘要除三個 NPZ 容器 SHA 外各值完全一致，三條 curve.json byte SHA 相同並涵蓋18個 full-state canonical digest；42份 curve/truth/failure 中只有4份 byte 完全相同。不宣稱全部 JSON 或 NPZ 容器 bytes 相同。", "",
              "## 外部隊員與限制", "",
              f"target-order driver 自身外呼0次；整個本使用者回合 NVIDIA 公開長度審查{external['nvidia']['actual_calls']}次、cost0、語義拒收且不重送，Gemini0次／既有工具隔離未驗證而skip。這些派工狀態不代替神經證據，也不寫成已確認記憶。", "",
              "本輪只診斷這個 MLP、合法通知 ACK、既有12題和已見地址／寬度的搭配。不能推論一般通知理解、真正語義升階、擴網收益或所有更新次序的優劣。沒有依 heldout 延長、追加 seed、改判準或再訓練原控制。", ""]
    return "\n".join(lines).encode("utf-8")


def finalize(base, baseline_base, code, original_root, approved_sha, out, prefix):
    base, baseline_base, code, original_root, out = (Path(value).resolve() for value in (base, baseline_base, code, original_root, out))
    require(not out.exists(), "Final publication exists; do not overwrite")
    manifest, pre, post = verify_final_gate(base, code, original_root, approved_sha)
    # No new summary, curve, truth, heldout, trace or checkpoint was read before the gate above.
    science, prereg = base / "science", base / "prereg"
    details = read_json(base / "review/post-run-details.json")
    science_before = artifact_inventory(science)
    require(science_before == details["science_file_inventory"], "Scientific artifact bytes differ from independent audit")
    require(artifact_inventory(prereg) == details["prereg_file_inventory"], "Preregistered artifact bytes differ from independent audit")
    require(artifact_inventory(base / "approved-inputs/baseline") == details["baseline_file_inventory"], "Approved baseline input bytes differ from audit")
    summary, timing = read_json(science / "summary.json"), read_json(science / "timing.json")
    receipt = read_json(base / "formal-receipt.json")
    require(summary["status"] == "complete" and summary["manifest_sha256"] == approved_sha, "Formal run incomplete or different")
    require(summary["complete_trajectories"] == summary["exact_replays"] == 3, "All primary/replays required")
    require([row["seed"] for row in summary["students"]] == list(SEEDS), "Fixed seed set differs")
    require(summary["primary_targets"] == summary["replay_targets"] == 81408
            and summary["primary_training_dense_MAC"] == summary["replay_training_dense_MAC"] == 1714126848, "Fixed costs differ")
    require(receipt["driver_measured_seconds"] == timing["total_seconds"], "Root/native walltime differs")
    require(sha(source_file(science, "manifest.json").read_bytes()) == approved_sha, "Executed manifest differs")
    require({(row["seed"], row["mode"]) for row in timing["trajectories"]}
            == {(seed, mode) for seed in SEEDS for mode in ("primary", "replay")}
            and len(timing["trajectories"]) == 6, "Six trajectory timings required")
    baseline, baseline_timing = read_json(baseline_base / "science/summary.json"), read_json(baseline_base / "science/timing.json")
    comparison = read_json(baseline_base / "replication-comparison.json")
    require(comparison["status"] == "passed" and comparison["summary_all_values_except_NPZ_container_SHA_exact"] is True
            and comparison["curve_full_state_digests_match_at_all_18_checkpoints"] is True
            and comparison["exact_all_payload_or_NPZ_container_identity_claimed"] is False, "Baseline comparison differs")
    external, redactions = external_accounting(baseline_base), []
    all_entries, per_seed, truths = [], {}, {}
    for student in summary["students"]:
        seed = student["seed"]
        per_seed[seed] = [exact_entry(science, name) for name in result_names(seed)]
        truth = truths[seed] = read_json(science / f"seed{seed}/final-truth.json")
        require(len(truth) == 18 and sum(row["split"] == "train" for row in truth) == 12, "Full final truth missing")
        require(read_json(science / f"seed{seed}/final-failures.json") == [row for row in truth if not row["whole_correct"]], "Final failures missing")
        require([row["epoch"] for row in read_json(science / f"seed{seed}/curve.json")] == list(EPOCHS), "Train curve checkpoints differ")
        require([row["epoch"] for row in read_json(science / f"seed{seed}/offline-curve.json")] == list(EPOCHS), "Full curve checkpoints differ")
        all_entries.extend(per_seed[seed])
    traces = [trace_record(science, seed) for seed in SEEDS]
    run_entries = [exact_entry(science, name, "run/" + name) for name in ("manifest.json", "summary.json", "timing.json", "execution-start.json")]
    prereg_names = ["manifest.json", "source-freeze.json", "target-pool.json", "schedules.npz"] + [f"initial-state-seed{seed}.npz" for seed in SEEDS]
    run_entries += [exact_entry(prereg, name, "prereg/" + name) for name in prereg_names]
    run_entries += [exact_entry(code, name, "code/" + name) for name in ("run_target_order.py", "protocol.json", "test_target_order.py", "export_results.py")]
    run_entries.append(exact_entry(original_root, "experiments/spiral_neural/20261113_pro_notice_learning/source-freeze.json", "lineage/original-source-freeze.json"))
    run_entries += [exact_entry(base, "review/" + name, "reviews/" + name) for name in ("review_inputs.py", "audit_results.py")]
    for name in ("pre-run.json", "pre-run-details.json", "post-run.json", "post-run-details.json"):
        run_entries.append(metadata_copy(base, "review/" + name, "reviews/" + name, redactions))
    for source, target in (("engineering/checks.json", "engineering/checks.json"),
                           ("portable-prereg/checks.json", "engineering/portable-prereg.json")):
        run_entries.append(metadata_copy(base, source, target, redactions))
    for source, target in (("science/codex-execution-provenance.json", "execution-provenance.json"),
                           ("replication-comparison.json", "replication-comparison.json"),
                           ("review/pre-run.json", "independent-pre-run.json"),
                           ("review/post-run.json", "independent-post-run.json"),
                           ("review/post-run-details.json", "independent-post-run-details.json")):
        run_entries.append(metadata_copy(baseline_base, source, "baseline-replication/" + target, redactions))
    for source in ("review/audit_results.py",):
        run_entries.append(exact_entry(baseline_base, source, "baseline-replication/audit_results.py"))
    for source, target in (("prereg-git.json", "run/prereg-git.json"),
                           ("formal-root-gate.json", "run/formal-root-gate.json"),
                           ("formal-receipt.json", "run/formal-receipt.json"),
                           ("approved-inputs/restore-checks.json", "run/approved-input-restore-checks.json")):
        run_entries.append(metadata_copy(base, source, target, redactions))
    all_entries.extend(run_entries)
    originals = {str(entry.source): entry.source_sha256 for entry in all_entries if entry.source is not None}
    for name, expected in manifest["original_source_hashes"].items():
        originals[str(source_file(original_root, name))] = expected
    out.mkdir(parents=True, exist_ok=False)
    public = out / "public"
    public.mkdir()
    archives = [write_archive(public, f"evidence-seed{seed}.zip", per_seed[seed]) for seed in SEEDS]
    archives.append(write_archive(public, "run-metadata.zip", run_entries))
    report = result_report(summary, timing, manifest, baseline, baseline_timing, external, truths, receipt)
    validate_content("RESULTS.md", report)
    with (public / "RESULTS.md").open("xb") as stream:
        stream.write(report)
    report_path = code / "RESULTS.md"
    if report_path.exists():
        require(report_path.read_bytes() == report, "Existing RESULTS.md differs; do not overwrite")
    else:
        with report_path.open("xb") as stream:
            stream.write(report)
    readme = exact_entry(code, "README.md")
    validate_content("README.md", readme.data)
    with (public / "README.md").open("xb") as stream:
        stream.write(readme.data)
    with (public / "export_results.py").open("xb") as stream:
        stream.write(source_file(code, "export_results.py").read_bytes())
    compact = {"schema": "sle-target-order-public-results-v1", "status": "complete",
               "manifest_sha256": approved_sha, "students": summary["students"],
               "strong_fit_gate_all_three": summary["strong_fit_gate_all_three"],
               "heldout_status": "Previously viewed diagnostic, not a new blind test",
               "new_formal_students": 3, "new_exact_replays": 3, "new_independent_control_seeds": 0,
               "new_target_order_costs": {key: value for key, value in summary.items() if "MAC" in key or "inference_calls" in key or key in ("primary_targets", "replay_targets")},
               "additional_Windows_control_replication_costs": {key: value for key, value in baseline.items() if "MAC" in key or "inference_calls" in key or key in ("primary_targets", "replay_targets")},
               "target_order_timing": timing, "additional_replication_timing": baseline_timing,
               "formal_execution_receipt": receipt,
               "pooled_final_train": {"whole_correct": sum(item["metrics"]["train"]["whole_correct"] for item in summary["students"]),
                                      "address_correct": sum(item["metrics"]["train"]["address_correct"] for item in summary["students"]), "total": 36},
               "strong_fit_student_count": sum(item["strong_fit_gate"] for item in summary["students"]),
               "external_team_whole_user_round": external, "independent_audit_status": post["status"],
               "independent_readonly_audit_costs": {key: post[key] for key in ("audit_extra_inference_calls", "audit_extra_inference_dense_MAC", "audit_seconds", "optimizer_step_lesson_loss_grad_calls") if key in post},
               "audit_PASS_means_artifact_consistency_not_scientific_success": True}
    write_json(public / "compact.json", compact)
    write_json(public / "trace-hashes.json", traces)
    inputs_manifest_path = base / "publication/prereg-inputs/public/baseline-inputs-manifest.json"
    inputs = read_json(inputs_manifest_path)
    reference = {"manifest_path": prefix + "/baseline-inputs-manifest.json", "manifest_sha256": sha(inputs_manifest_path.read_bytes()),
                 "archives": [{key: value for key, value in item.items() if key != "entries"} for item in inputs["archives"]],
                 "already_published_for_preregistration": True, "republished_in_result_archives": False}
    record = {"schema": "sle-target-order-publication-record-v1", "author": "Codex", "manifest_sha256": approved_sha,
              "coverage": "All three students, all fixed checkpoints, free/TF truth and final failures; three full replay evidence summaries",
              "historical_control": "Reuse Pro fixed original order; Windows reproduction is an extra physical run, not new independent seeds",
              "omitted_large_target_traces": traces, "metadata_public_copies": redactions,
              "prepublished_baseline_inputs": reference, "scientific_source_bytes_changed": False,
              "raw_API_account_quota_or_autonomous_state_selected": False,
              "original_source_hashes": manifest["original_source_hashes"], "local_source_hashes": manifest["local_source_hashes"]}
    write_json(public / "PUBLICATION_RECORD.json", record)
    for name, expected in originals.items():
        require(sha(Path(name).read_bytes()) == expected, "Original changed during export")
    require(artifact_inventory(science) == science_before, "Scientific inventory changed during export")
    for item in traces:
        require(sha(source_file(science, item["path"]).read_bytes()) == item["sha256"], "Local trace changed during export")
    require(sha(readme.source.read_bytes()) == readme.source_sha256, "README changed during export")
    package = {"schema": "sle-target-order-public-package-v1", "manifest_sha256": approved_sha,
               "archives": archives, "prepublished_dependencies": reference,
               "files": {path.name: metadata(path.read_bytes()) for path in sorted(public.iterdir())},
               "self_and_export_checks_excluded_from_files_to_avoid_self_reference": True}
    write_json(public / "package-manifest.json", package)
    checks = {"status": "PASS", "archive_members_byte_verified": sum(item["entry_count"] for item in archives),
              "NPZ_finite_verified": sum(item["NPZ_finite_verified"] for item in archives),
              "original_files_SHA_verified_unchanged": len(originals), "local_traces_SHA_verified": len(traces),
              "complete_science_inventory_verified_against_independent_audit": len(science_before),
              "privacy_checked_all_members_and_top_level_text": True, "LF_text_Git_bytes_exact": True,
              "new_learning_inference_replay_or_external_calls": 0, "full_target_traces_public": False,
              "review_gate_checked_before_new_results_read": True, "metadata_redactions_listed": True}
    write_json(public / "export-checks.json", checks)
    counts = git_records(public, out, prefix)
    result = {"status": "PASS", "mode": "final_results", "repo_prefix": prefix, **counts,
              "manifest_sha256": approved_sha, "archives": [{key: value for key, value in item.items() if key != "entries"} for item in archives],
              "checks": checks, "report_sha256": sha(report), "exporter_sha256": sha(Path(__file__).read_bytes())}
    write_json(out / "compact.json", result)
    return result


def self_test(out):
    """Finite arrays and packaging checks only: no scientific imports or inference."""
    import numpy as np
    out = Path(out).resolve()
    require(not out.exists(), "Self-test output exists")
    out.mkdir(parents=True)
    checked = []
    validate_content("export_results.py", Path(__file__).read_bytes())
    checked.append("Exporter source is valid public UTF8/LF text")
    with tempfile.TemporaryDirectory(prefix="public-export-", dir=out) as temporary:
        base = Path(temporary)
        public = base / "public"
        public.mkdir()
        data = json_bytes({"text": "正體中文", "line": "a\nb", "zero": 0})
        state = io.BytesIO()
        np.savez(state, p=np.array([0, 1], dtype=np.float32), meta=np.array('{"t":0}'))
        archive = write_archive(public, "synthetic.zip", [Entry("test/data.json", data), Entry("test/state.npz", state.getvalue())])
        checked.append("ZIP byte roundtrip and finite NPZ")
        private_example = "C:" + "/Us" + "ers/" + "synthetic"
        for name in ("../escape.json", "/absolute.json", private_example + "/a.json", "cache/.git/key.json", "a\\b.json"):
            try:
                safe_relative(name)
            except ValueError:
                pass
            else:
                raise AssertionError("Unsafe path accepted")
        checked.append("Five unsafe path rejections")
        bad_values = [{"access_token": "secret"}, {"private_raw_api_record": "hidden"}, {"path": private_example + "/file"}]
        for value in bad_values:
            try:
                validate_content("bad.json", json_bytes(value))
            except ValueError:
                pass
            else:
                raise AssertionError("Private metadata accepted")
        checked.append("Three private metadata rejections")
        for invalid in (b'{"x":1}\r\n',):
            try:
                validate_content("bad.json", invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("CRLF accepted")
        invalid_state = io.BytesIO()
        np.savez(invalid_state, p=np.array([float("nan")]))
        try:
            validate_content("bad.npz", invalid_state.getvalue())
        except ValueError:
            pass
        else:
            raise AssertionError("Nonfinite NPZ accepted")
        checked.append("CRLF and nonfinite NPZ rejections")
        write_json(public / "record.json", {"text": "繁中\nline"})
        counts = git_records(public, base, PREFIX)
        records = read_json(base / "text-entries.json")
        expected = read_json(base / "expected-blobs.json")
        for record in records:
            require(git_blob(record["content"].encode("utf-8")) == expected[record["path"]], "Git bytes differ")
        checked.append("UTF8/LF text Gitblob and binary base64 roundtrip")
        require(archive["NPZ_finite_verified"] == 1 and counts["binary_entries"] == 1, "Count mismatch")
    result = {"status": "PASS", "checks": checked, "scientific_modules_imported": False,
              "model_or_network_calls": 0, "new_results_read": False,
              "exporter_sha256": sha(Path(__file__).read_bytes())}
    write_json(out / "checks.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    deps = modes.add_parser("dependencies", help="Publish only the twelve original-order control inputs")
    deps.add_argument("--control-root", type=Path, required=True)
    deps.add_argument("--out", type=Path, required=True)
    deps.add_argument("--prefix", default=PREFIX)
    restore = modes.add_parser("restore-inputs", help="Verify paths, sizes and hashes, then restore to a new root")
    restore.add_argument("--archive", type=Path, required=True)
    restore.add_argument("--manifest", type=Path, required=True)
    restore.add_argument("--approved-manifest-sha", required=True)
    restore.add_argument("--out", type=Path, required=True)
    test = modes.add_parser("self-test", help="Synthetic finite/byte/privacy checks; no learner")
    test.add_argument("--out", type=Path, required=True)
    final = modes.add_parser("finalize", help="Only after all formal runs, exact replays and independent post-run PASS")
    final.add_argument("--base", type=Path, required=True)
    final.add_argument("--baseline-base", type=Path, required=True)
    final.add_argument("--code", type=Path, default=Path(__file__).resolve().parent)
    final.add_argument("--original-source-root", type=Path, required=True)
    final.add_argument("--approved-manifest-sha", required=True)
    final.add_argument("--out", type=Path, required=True)
    final.add_argument("--prefix", default=PREFIX)
    args = parser.parse_args()
    if args.mode == "dependencies":
        result = package_dependencies(args.control_root, args.out, args.prefix)
    elif args.mode == "restore-inputs":
        result = restore_dependencies(args.archive, args.manifest, args.approved_manifest_sha, args.out)
    elif args.mode == "finalize":
        result = finalize(args.base, args.baseline_base, args.code, args.original_source_root,
                          args.approved_manifest_sha, args.out, args.prefix)
    else:
        result = self_test(args.out)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
