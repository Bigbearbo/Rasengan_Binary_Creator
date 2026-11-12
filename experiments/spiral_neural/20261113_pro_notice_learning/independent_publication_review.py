"""Pure-file publication audit: no model imports, inference, or training."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

HERE = Path(__file__).resolve().parent
INDEX_SHA = "5f70385c60cbcc3807b7350f8b6a3877491a06f8a91162926cfe59bdb8bd6dde"
MANIFEST_SHA = "d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0"
REGISTRATION = "0b6de1d24481c2886833e412d173645fca98609c"
EXTERNAL_METADATA = {"execution_record.json", "formal_stdout.log", "preflight_results.json"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def safe_relative(value):
    path = PurePosixPath(value)
    check(not path.is_absolute() and ".." not in path.parts, "relative publication path")
    return path


def review():
    previous = json.loads((HERE / "independent_result_review.json").read_text())
    check(previous["passed"] is True, "prior neural audit passed")
    neural_script_sha = sha((HERE / "independent_result_review.py").read_bytes())
    check(neural_script_sha == previous["review_script_sha256"], "prior neural audit script provenance unchanged")
    bundle = HERE / "public_evidence"
    index_bytes = (bundle / "evidence_index.json").read_bytes()
    check(sha(index_bytes) == INDEX_SHA, "fixed publication index SHA")
    index = json.loads(index_bytes)
    check(index["approved_manifest_sha256"] == MANIFEST_SHA, "publication approved manifest")
    check(index["preregistration_commit"] == REGISTRATION, "publication preregistration commit")
    check(index["complete_target_traces_included"] is True, "complete trace publication declaration")
    check(sha((HERE / "evidence_bundle.py").read_bytes()) == index["reconstruction_script_sha256"], "reconstruction script SHA")
    original_hashes = previous["formal_artifact_hashes"]
    seen_entries, seen_parts = {}, set()
    archives = []
    payload_bytes = unpacked_bytes = 0
    for record in index["archives"]:
        chunks = []
        for part in record["parts"]:
            relative = str(safe_relative(part["path"]))
            check(relative not in seen_parts, "unique published payload parts")
            seen_parts.add(relative)
            data = (bundle / relative).read_bytes()
            check(len(data) == part["size"] and sha(data) == part["sha256"], f"part bytes/hash: {relative}")
            check(len(data) <= index["maximum_part_bytes"], "payload part size bound")
            payload_bytes += len(data)
            chunks.append(data)
        packed = b"".join(chunks)
        check(len(packed) == record["size"] and sha(packed) == record["sha256"], "reconstructed ZIP bytes/hash")
        expected = {item["path"]: item for item in record["entries"]}
        check(len(expected) == len(record["entries"]), "unique expected ZIP names")
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            names = archive.namelist()
            check(len(names) == len(set(names)) and set(names) == set(expected), "exact ZIP member set")
            for name in names:
                relative = str(safe_relative(name))
                check(relative not in seen_entries, "each raw artifact published exactly once")
                data = archive.read(name)  # Also verifies the ZIP member CRC.
                actual = sha(data)
                check(len(data) == expected[name]["size"] and actual == expected[name]["sha256"], f"ZIP entry bytes/hash: {name}")
                if relative in original_hashes:
                    check(actual == original_hashes[relative], f"ZIP member matches independently audited raw artifact: {name}")
                    source = HERE / "formal_run" / relative
                else:
                    # The bundle explicitly adds these three run-level files
                    # from the experiment directory, outside formal_run.
                    check(relative in EXTERNAL_METADATA, "only declared external run metadata added")
                    source = HERE / relative
                check(actual == sha(source.read_bytes()), f"published entry matches its raw source: {name}")
                seen_entries[relative] = actual
                unpacked_bytes += len(data)
        archives.append({"archive": record["archive"], "parts": len(record["parts"]),
                         "members": len(expected), "bytes": len(packed), "sha256": sha(packed)})
    check(set(seen_entries) == set(original_hashes) | EXTERNAL_METADATA, "all audited artifacts plus exact declared run metadata")
    check((len(archives), len(seen_parts), len(seen_entries)) == (4, 19, 82), "4 ZIPs / 19 payload files / 82 members")
    check(payload_bytes == index["distributed_bytes"] == 8695435, "total publication payload bytes")
    check(unpacked_bytes == index["uncompressed_bytes"] == 17548458, "total uncompressed bytes")
    check(index["uncompressed_files"] == 82, "uncompressed file count")
    for name, expected in original_hashes.items():
        check(sha((HERE / "formal_run" / name).read_bytes()) == expected, "formal raw files unchanged after publication review")
    return {"passed": True, "scope": "Pure-file part/ZIP/member hashes and CRC; no extraction or model execution.",
            "publication_index_sha256": INDEX_SHA, "approved_manifest_sha256": MANIFEST_SHA,
            "registration_commit": REGISTRATION, "archives": archives,
            "payload_files": len(seen_parts), "zip_members": len(seen_entries),
            "previously_audited_formal_members": len(original_hashes),
            "external_run_metadata_members": sorted(EXTERNAL_METADATA),
            "payload_bytes": payload_bytes, "uncompressed_bytes": unpacked_bytes,
            "complete_audited_formal_artifacts_covered": True, "formal_artifacts_unchanged": True,
            "prior_neural_review_script_sha256": neural_script_sha,
            "prior_neural_review_inference_calls": previous["review_actual_inference_calls"],
            "prior_neural_review_inference_dense_MAC": previous["review_actual_inference_dense_MAC"],
            "prior_neural_review_record_modified": False,
            "publication_review_inference_calls": 0, "publication_review_training_updates": 0,
            "publication_review_training_replays": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "independent_publication_review.json")
    args = parser.parse_args()
    try:
        report = review()
    except Exception as error:
        report = {"passed": False, "error": type(error).__name__, "detail": str(error),
                  "publication_review_inference_calls": 0, "publication_review_training_updates": 0}
    report["author"] = "ChatGPT Pro / independent delegated publication review"
    report["command"] = "python -B independent_publication_review.py --out independent_publication_review.json"
    report["review_script_sha256"] = sha(Path(__file__).read_bytes())
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("passed", "payload_files", "zip_members", "payload_bytes",
                     "uncompressed_bytes", "error", "detail") if key in report}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
