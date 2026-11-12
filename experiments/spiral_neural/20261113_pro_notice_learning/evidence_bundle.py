"""Pure-file publication/reconstruction. No NumPy, model load, or training.

Each seed is one logical ZIP. ZIPs over 1 MiB are distributed in <=512 KiB
parts; the index hashes both ZIPs/parts and every uncompressed member.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

PART_LIMIT = 512 * 1024
SPLIT_THRESHOLD = 1024 * 1024


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_path(text):
    path = PurePosixPath(text)
    require(text and not path.is_absolute() and ".." not in path.parts and "\\" not in text,
            f"Unsafe archive path: {text!r}")
    return Path(*path.parts)


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def pack(source, output):
    source, output = source.resolve(), output.resolve()
    summary = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    require(summary["status"] == "complete", "Only a completed run may be published")
    execution = source.parent / "execution_record.json"
    record = json.loads(execution.read_text(encoding="utf-8"))
    require(record["status"] == "completed" and record["exit_code"] == 0, "Execution did not finish")
    require(sha(source / "manifest.json") == summary["manifest_sha256"], "Run manifest differs")
    output.mkdir(parents=True, exist_ok=False)
    groups = []
    for seed in (101, 202, 303):
        folder = source / f"seed{seed}"
        groups.append((f"seed{seed}.zip", [(p, p.relative_to(source).as_posix())
                                         for p in sorted(folder.rglob("*")) if p.is_file()]))
    metadata = [(p, p.name) for p in sorted(source.iterdir()) if p.is_file()]
    metadata += [(source.parent / name, name) for name in
                 ("execution_record.json", "formal_stdout.log", "preflight_results.json")]
    groups.append(("run-metadata.zip", metadata))
    index = {"schema": "pro-ur1-evidence-v1", "preregistration_commit": record["preregistration_commit"],
             "approved_manifest_sha256": summary["manifest_sha256"], "complete_target_traces_included": True,
             "split_threshold_bytes": SPLIT_THRESHOLD, "maximum_part_bytes": PART_LIMIT,
             "reconstruction_script_sha256": sha(__file__), "archives": []}
    seen = set()
    with tempfile.TemporaryDirectory(prefix="ur1-package-") as temporary:
        for name, files in groups:
            entries = []
            archive_path = Path(temporary) / name
            with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for path, member in files:
                    safe_path(member)
                    require(member not in seen, f"Duplicate evidence member: {member}")
                    seen.add(member)
                    entries.append({"path": member, "size": path.stat().st_size, "sha256": sha(path)})
                    archive.write(path, member, compress_type=zipfile.ZIP_STORED if path.suffix == ".gz" else zipfile.ZIP_DEFLATED)
            size = archive_path.stat().st_size
            item = {"archive": name, "size": size, "sha256": sha(archive_path), "entries": entries, "parts": []}
            if size <= SPLIT_THRESHOLD:
                destination = output / name
                shutil.copyfile(archive_path, destination)
                item["parts"].append({"path": name, "size": size, "sha256": item["sha256"]})
            else:
                with archive_path.open("rb") as stream:
                    part = 0
                    while block := stream.read(PART_LIMIT):
                        part_name = f"{name}.part{part:04}"
                        with (output / part_name).open("xb") as sink:
                            sink.write(block)
                        item["parts"].append({"path": part_name, "size": len(block),
                                              "sha256": hashlib.sha256(block).hexdigest()})
                        part += 1
            index["archives"].append(item)
    index["uncompressed_files"] = len(seen)
    index["uncompressed_bytes"] = sum(member["size"] for archive in index["archives"] for member in archive["entries"])
    index["distributed_bytes"] = sum(archive["size"] for archive in index["archives"])
    write_json(output / "evidence_index.json", index)
    return {"status": "packed", "archives": len(groups), "files": len(seen),
            "distributed_bytes": index["distributed_bytes"], "index_sha256": sha(output / "evidence_index.json")}


def restore(index_path, output=None):
    index_path = index_path.resolve()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    require(index["schema"] == "pro-ur1-evidence-v1", "Unsupported index schema")
    require(sha(__file__) == index["reconstruction_script_sha256"], "Reconstruction script differs")
    if output is not None:
        output = output.resolve()
        output.mkdir(parents=True, exist_ok=False)
    checked, bytes_checked, seen = 0, 0, set()
    with tempfile.TemporaryDirectory(prefix="ur1-reconstruct-") as temporary:
        for item in index["archives"]:
            archive_path = Path(temporary) / safe_path(item["archive"])
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            with archive_path.open("xb") as assembled:
                for part in item["parts"]:
                    path = index_path.parent / safe_path(part["path"])
                    require(path.stat().st_size == part["size"] and sha(path) == part["sha256"], f"Part differs: {path.name}")
                    with path.open("rb") as stream:
                        shutil.copyfileobj(stream, assembled)
            require(archive_path.stat().st_size == item["size"] and sha(archive_path) == item["sha256"], "Reconstructed ZIP differs")
            expected = {entry["path"]: entry for entry in item["entries"]}
            require(len(expected) == len(item["entries"]), "Repeated index entry")
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                require(len(names) == len(expected) and set(names) == set(expected), "ZIP members differ")
                for name in names:
                    relative = safe_path(name)
                    require(name not in seen, "Duplicate evidence path across ZIPs")
                    seen.add(name)
                    h, size = hashlib.sha256(), 0
                    destination = None
                    if output is not None:
                        path = output / relative
                        path.parent.mkdir(parents=True, exist_ok=True)
                        destination = path.open("xb")
                    try:
                        with archive.open(name) as stream:
                            for block in iter(lambda: stream.read(1024 * 1024), b""):
                                h.update(block)
                                size += len(block)
                                if destination is not None:
                                    destination.write(block)
                    finally:
                        if destination is not None:
                            destination.close()
                    require(size == expected[name]["size"] and h.hexdigest() == expected[name]["sha256"], f"Evidence member differs: {name}")
                    checked += 1
                    bytes_checked += size
    require(checked == index["uncompressed_files"] and bytes_checked == index["uncompressed_bytes"], "Evidence totals differ")
    return {"status": "PASS", "mode": "restore" if output is not None else "verify",
            "files": checked, "uncompressed_bytes": bytes_checked, "model_updates": 0,
            "model_inference_calls": 0, "index_sha256": sha(index_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    for name in ("restore", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--index", type=Path, required=True)
        if name == "restore":
            p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = pack(args.source, args.out) if args.mode == "pack" else restore(args.index, args.out if args.mode == "restore" else None)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
