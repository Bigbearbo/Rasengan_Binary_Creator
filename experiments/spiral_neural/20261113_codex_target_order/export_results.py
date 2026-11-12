"""Explicit public evidence exporter; never imports a learner or calls a model.

`dependencies` packages the twelve fixed Windows control inputs for preregistration.
`finalize` is reserved for the complete three-seed run and independent post-run PASS.
The two modes create new directories and never overwrite scientific artifacts.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import io
import json
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
PRIVATE_TEXT = re.compile(r"(?i)(?:[A-Z]:[\\/]Users[\\/]|/home/|/Users/|"
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


def self_test(out):
    """Finite arrays and packaging checks only: no scientific imports or inference."""
    import numpy as np
    out = Path(out).resolve()
    require(not out.exists(), "Self-test output exists")
    out.mkdir(parents=True)
    checked = []
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
    args = parser.parse_args()
    if args.mode == "dependencies":
        result = package_dependencies(args.control_root, args.out, args.prefix)
    elif args.mode == "restore-inputs":
        result = restore_dependencies(args.archive, args.manifest, args.approved_manifest_sha, args.out)
    else:
        result = self_test(args.out)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
