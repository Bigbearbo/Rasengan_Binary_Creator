"""Package every AE1 state, epoch record and prediction; verify every ZIP member."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pack():
    require(read(HERE / "evaluation_summary.json")["status"] == "completed", "Evaluation incomplete")
    require(read(HERE / "replay_check.json")["status"] == "PASS", "Replay not verified")
    require(read(HERE / "independent_result_review.json")["status"] == "PASS", "Independent audit not passed")
    destination = HERE / "evidence"
    destination.mkdir(exist_ok=False)
    bundles = []
    for role, seed in (("primary", 101), ("primary", 202), ("primary", 303), ("replay", 101)):
        folder = HERE / "runs" / f"{role}_seed{seed}"
        require(read(folder / "summary.json")["status"] == "completed", "Trajectory incomplete")
        sources = sorted(folder.glob("*.npz")) + sorted(folder.glob("*.json"))
        require(len(sources) == 11, "Expected five states, five phase records and one summary")
        if role == "primary":
            predictions = sorted((HERE / "evaluation").glob(f"seed{seed}_phase*.json"))
            require(len(predictions) == 6, "Expected six evaluation files")
            sources += predictions
        sources.append(HERE / "logs" / f"{role}_seed{seed}.log")
        archive = destination / f"{role}_seed{seed}.zip"
        members = []
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
            for path in sorted(sources):
                raw = path.read_bytes()
                relative = path.relative_to(HERE).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                output.writestr(info, raw, compresslevel=9)
                members.append({"path": relative, "bytes": len(raw), "sha256": digest(raw)})
        with zipfile.ZipFile(archive) as source:
            require(source.namelist() == [member["path"] for member in members], "Archive members differ")
            require(source.testzip() is None, "ZIP CRC failure")
            for member in members:
                raw = source.read(member["path"])
                require(len(raw) == member["bytes"] and digest(raw) == member["sha256"],
                        "Archive roundtrip mismatch")
        bundles.append({"archive": archive.relative_to(HERE).as_posix(),
                        "bytes": archive.stat().st_size, "sha256": digest(archive.read_bytes()),
                        "members": members})
    result = {"status": "PASS", "author": "ChatGPT Pro",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "preregistration_commit": "beb6dd7d4ce78d4f79e61164f838aaa881eafcd5",
              "bundles": bundles, "members_verified": sum(len(b["members"]) for b in bundles),
              "all_member_bytes_hashes_and_CRC_verified": True,
              "no_optimizer_or_neural_inference": True,
              "scope": "All15 primary and5 replay phase states, all epoch statistics and trajectory summaries, all18 checkpoint evaluation files and4 stdout logs. Initial states and exact schedules are already separately committed in frozen/.",
              "not_recorded": "No per-target intermediate weight states or per-target loss trace; the complete frozen schedule, epoch statistics and phase states are retained."}
    with (HERE / "evidence_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "bundles": len(bundles), "members": result["members_verified"],
                      "compressed_bytes": sum(b["bytes"] for b in bundles)}))


def unpack():
    manifest = read(HERE / "evidence_manifest.json")
    pending = []
    for bundle in manifest["bundles"]:
        archive = HERE / bundle["archive"]
        require(digest(archive.read_bytes()) == bundle["sha256"], "Archive SHA mismatch")
        with zipfile.ZipFile(archive) as source:
            require(source.namelist() == [m["path"] for m in bundle["members"]], "Unexpected member list")
            for member in bundle["members"]:
                relative = PurePosixPath(member["path"])
                require(not relative.is_absolute() and ".." not in relative.parts
                        and relative.parts[0] in ("runs", "evaluation", "logs"), "Unsafe archive path")
                path = HERE.joinpath(*relative.parts)
                require(path.resolve().is_relative_to(HERE.resolve()), "Archive escaped experiment root")
                raw = source.read(member["path"])
                require(digest(raw) == member["sha256"] and len(raw) == member["bytes"], "Member SHA mismatch")
                if path.exists():
                    require(path.is_file() and digest(path.read_bytes()) == member["sha256"],
                            f"Refuse to overwrite different existing evidence: {relative}")
                else:
                    pending.append((path, raw))
    for path, raw in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    print(json.dumps({"status": "PASS", "restored_files": len(pending)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=("pack", "unpack"))
    args = parser.parse_args()
    pack() if args.command == "pack" else unpack()
