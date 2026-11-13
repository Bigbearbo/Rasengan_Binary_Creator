"""Explicit GPU engineering evidence allowlist; no benchmark/model execution."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import zipfile
import zlib


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
TOOL = ROOT / "outputs/gpu-training-review"
PREFIX = "experiments/spiral_neural/20261113_codex_gpu_training_review"
REFERENCE_SHA = "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"
TOOL_FILES = ("bench_common.py", "cpu_bench.py", "gpu_bench.py", "plan.json", "plan-addendum-01.json",
              "plan-addendum-02.json", "README.md", "decision.json")
WORK_FILES = ("cpu-results.json", "fixture.npz", "independent-sources.md", "independent-sources.json",
              "gpu-method-review.json", "environment-checks.json", "external-review.json")
PRIVATE = re.compile(r"(?i)(?:[A-Z]:[\\/]Us" r"ers[\\/]|/ho" r"me/|/Us" r"ers/|Bearer\s+[A-Za-z0-9._-]{8,}|sk-or-v1-[A-Za-z0-9]+)")
PRIVATE_KEYS = {"private_raw_api_record", "private_legacy_record", "raw_api_path", "api_key", "access_token",
                "refresh_token", "id_token", "authorization_header", "account_quota", "quota_remaining"}
PRIVATE_PARTS = {".git", ".ssh", ".aws", "venv", "pipcache", "pip-cache", "cuda-cache", "cuda_cache",
                 "__pycache__", "fontcache", "autonomous-state.json", "transport.json"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def metadata(raw):
    return {"bytes": len(raw), "sha256": sha(raw), "Git_blob": blob(raw)}


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(Path(path).read_bytes().decode("utf-8-sig"))


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(encoded(value).decode("utf-8"))


def safe_name(name):
    require(isinstance(name, str) and name and ":" not in name and "\\" not in name, "Invalid relative name")
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(part not in (".", "..", "") for part in path.parts), "Escaped path")
    require(not any(part.casefold() in PRIVATE_PARTS for part in path.parts), "Private/cache path selected")
    return path.as_posix()


def scan_json(value, name):
    if isinstance(value, dict):
        for key, item in value.items():
            require(key.casefold() not in PRIVATE_KEYS, f"Private metadata field: {name}")
            scan_json(item, name)
    elif isinstance(value, list):
        for item in value:
            scan_json(item, name)
    elif isinstance(value, str):
        require(not PRIVATE.search(value), f"Private user path/credential: {name}")
    elif isinstance(value, float):
        require(math.isfinite(value), f"Nonfinite JSON: {name}")


def inspect_content(name, raw):
    safe_name(name)
    suffix = PurePosixPath(name).suffix.lower()
    if suffix == ".npz":
        # The only selected array archive is the synthetic frozen fixture.
        require(name == "fixture.npz", "Trained-state or unapproved NPZ selected")
        import numpy as np
        with np.load(io.BytesIO(raw), allow_pickle=False) as arrays:
            require(bool(arrays.files), "Empty fixture NPZ")
            for key in arrays.files:
                array = arrays[key]
                require(not array.dtype.hasobject, "Pickled fixture array")
                if np.issubdtype(array.dtype, np.number):
                    require(bool(np.isfinite(array).all()), "Nonfinite fixture")
                elif array.dtype.kind in "US":
                    for text in array.ravel().tolist():
                        text = text.decode("utf-8") if isinstance(text, bytes) else text
                        require(not PRIVATE.search(text), "Private fixture metadata")
        return 1
    require(suffix in (".py", ".json", ".md"), f"Unexpected content kind: {name}")
    text = raw.decode("utf-8-sig")
    require(not PRIVATE.search(text), f"Private user path/credential: {name}")
    if suffix == ".json":
        scan_json(json.loads(text), name)
    return 0


def selected_sources():
    sources = {name: TOOL / name for name in TOOL_FILES}
    sources.update({name: WORK / name for name in WORK_FILES})
    for number in range(1, 5):
        folder = f"gpu-attempt{number:02}"
        sources[folder + "/gpu-results.json"] = WORK / folder / "gpu-results.json"
        sources[folder + "/gpu_bench.py"] = WORK / folder / "gpu_bench.py"
    sources["reference/p030_binary_continual.py"] = ROOT / "outputs/sle-research-review/p030_binary_continual.py"
    sources["package_publication.py"] = Path(__file__).resolve()
    return sources


def source_guard(contents):
    plan = json.loads(contents["plan.json"].decode("utf-8"))
    require(plan["id"] == "GPU-TRAIN-REVIEW-20261113" and plan["formal_neural_experiment_updates"] == 0, "Wrong research scope")
    require(plan["maximum_all_backend_micro_updates"] == 40000, "Frozen total cap differs")
    require(sha(contents["reference/p030_binary_continual.py"]) == REFERENCE_SHA, "Original P030 reference differs")
    cpu = json.loads(contents["cpu-results.json"].decode("utf-8"))
    require(cpu["status"] == "complete" and cpu["formal_neural_experiment_updates"] == 0, "CPU record incomplete")
    for name, pin in cpu["source_hashes"].items():
        target = "reference/p030_binary_continual.py" if name == "original_reference" else name
        require(sha(contents[target]) == pin, "CPU executed source/plan pin differs")
    fixture_sha = sha(contents["fixture.npz"])
    require(cpu["fixture"]["sha256"] == fixture_sha, "CPU fixture differs")
    per_backend = {name: sum(phases.values()) for name, phases in cpu["actual_micro_updates"].items()}
    require(sum(per_backend.values()) == cpu["actual_micro_updates_total"], "CPU update ledger differs")
    attempts = {}
    total = cpu["actual_micro_updates_total"]
    for number in range(1, 5):
        folder = f"gpu-attempt{number:02}"
        result = json.loads(contents[folder + "/gpu-results.json"].decode("utf-8"))
        require(result["status"] == "complete" and result["formal_training_updates"] == 0, "GPU attempt record incomplete")
        require(result["fixture_sha256"] == fixture_sha and result["fixture_unchanged"] is True, "GPU fixture differs")
        require(result["plan_sha256"] == sha(contents["plan.json"]), "GPU plan pin differs")
        require(result["script_sha256"] == sha(contents[folder + "/gpu_bench.py"]), "GPU attempt source version differs")
        ledger = result["actual_synthetic_updates"]
        for name, count in ledger.items():
            require(type(count) is int and count >= 0, "Invalid actual update count")
            per_backend[name] = per_backend.get(name, 0) + count
        count = sum(ledger.values())
        total += count
        attempts[folder] = {"actual_micro_updates": count, "ledger": ledger,
                            "executed_script_sha256": result["script_sha256"],
                            "captured_steps_not_executed": result["captured_steps_not_executed"]}
    require(sha(contents["gpu_bench.py"]) == attempts["gpu-attempt04"]["executed_script_sha256"], "Current source is not the executed attempt04 source")
    require(total <= plan["maximum_all_backend_micro_updates"], "Total actual micro-update cap exceeded")
    require(all(value <= plan["maximum_actual_micro_updates_per_backend"] for value in per_backend.values()), "Per-backend cap exceeded")
    review = json.loads(contents["gpu-method-review.json"].decode("utf-8"))
    require(review["status"] == "passed_for_bounded_engineering_readout", "Independent method review is incomplete")
    return {"CPU_actual_micro_updates": cpu["actual_micro_updates_total"], "GPU_attempts": attempts,
            "actual_micro_updates_total": total, "per_backend_actual_updates": per_backend,
            "formal_neural_experiment_updates": 0, "fixture_sha256": fixture_sha,
            "parity_scope": plan["parity"], "source_versions_preserved_separately": True}


def evidence_zip(contents):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, raw in sorted(contents.items()):
            item = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    raw = buffer.getvalue()
    require(len(raw) <= 3_000_000, "Selected evidence ZIP exceeds the agreed 3MB bound")
    members = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        require(set(archive.namelist()) == set(contents) and len(archive.infolist()) == len(contents), "ZIP member set differs")
        for item in archive.infolist():
            selected = contents[item.filename]
            require(archive.read(item) == selected, "ZIP byte roundtrip differs")
            crc = zlib.crc32(selected) & 0xffffffff
            require(item.file_size == len(selected) and item.CRC == crc, "ZIP size/CRC differs")
            members[item.filename] = {**metadata(selected), "CRC32": f"{crc:08x}", "compressed_bytes": item.compress_size}
    return raw, members


def finalize(out):
    out = Path(out).resolve()
    require(not out.exists(), "Destination exists; never overwrite a prior publication")
    sources = selected_sources()
    contents = {}
    for name, path in sources.items():
        safe_name(name)
        require(path.resolve().is_relative_to(ROOT.resolve()) and path.is_file(), f"Missing/escaped allowlist source: {name}")
        contents[name] = path.read_bytes()
    source_pins = {name: sha(raw) for name, raw in contents.items()}
    finite = sum(inspect_content(name, raw) for name, raw in contents.items())
    accounting = source_guard(contents)
    archive, members = evidence_zip(contents)
    files = {name: raw for name, raw in contents.items() if not name.endswith(".npz")}
    files["evidence.zip"] = archive
    publication = {"schema": "gpu-training-review-publication-v1", "status": "verified",
                   "scope": "Bounded synthetic engineering evidence; not a formal training result or bitwise training replay",
                   "selected_files": {name: metadata(raw) for name, raw in sorted(contents.items())},
                   "archives": {"evidence.zip": {**metadata(archive), "member_count": len(members), "members": members}},
                   "accounting": accounting, "finite_fixture_NPZ": finite,
                   "not_selected": ["venv", "pipcache", "CUDAcache", "installation logs", "raw external worker transport", "account quota", "DPAPI", "chat", "private handoff", "trained study checkpoints"],
                   "packager_benchmark_or_model_calls": 0}
    files["publication-manifest.json"] = encoded(publication)
    checks = {"status": "PASS", "selected_original_files": len(contents), "archive_members_byte_CRC_SHA_verified": len(members),
              "finite_synthetic_fixture_NPZ": finite, "privacy_checked_all_selected_files": True,
              "source_versions_and_result_pins_verified": True, "original_source_result_fixture_files_unchanged": True,
              "packager_micro_updates": 0, "packager_model_forward_calls": 0, "external_calls": 0,
              "formal_training_updates": 0}
    files["export-checks.json"] = encoded(checks)
    for name, path in sources.items():
        require(sha(path.read_bytes()) == source_pins[name], "Original source changed during packaging")
    out.mkdir(parents=True, exist_ok=False)
    public = out / "public"
    public.mkdir()
    text, binary, expected = [], [], {}
    for name, raw in sorted(files.items()):
        if not name.endswith(".zip"):
            inspect_content(name, raw)
        target = public / safe_name(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        require(target.read_bytes() == raw, "Published bytes differ")
        git_path = PREFIX + "/" + name
        expected[git_path] = blob(raw)
        if name.endswith(".zip"):
            binary.append({"path": git_path, "mode": "100644", "type": "blob", **metadata(raw), "local_file": "public/" + name})
        else:
            content = raw.decode("utf-8")
            require(content.encode("utf-8") == raw, "Text Git entry bytes differ")
            text.append({"path": git_path, "mode": "100644", "type": "blob", "content": content})
    write_json(out / "text-entries.json", text)
    write_json(out / "binary-entries.json", binary)
    write_json(out / "expected-blobs.json", expected)
    result = {"status": "verified", "repo_prefix": PREFIX, "public_files": {name: metadata(raw) for name, raw in sorted(files.items())},
              "public_files_over_1MiB": {name: metadata(raw) for name, raw in sorted(files.items()) if len(raw) > 1024 * 1024},
              "archive_indexes": {"evidence.zip": {**metadata(archive), "member_count": len(members)}},
              "full_member_inventory": "public/publication-manifest.json", "text_entries": len(text), "binary_entries": len(binary),
              "checks": checks, "accounting": accounting, "packager_sha256": sha(Path(__file__).read_bytes())}
    write_json(out / "compact.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize", action="store_true", help="Only after root explicit FINALIZE authorization")
    parser.add_argument("--out", type=Path, default=WORK / "publication/final")
    args = parser.parse_args()
    require(args.finalize, "Preparation only: explicit --finalize is required to generate public outputs")
    result = finalize(args.out)
    print(json.dumps({key: result[key] for key in ("status", "text_entries", "binary_entries", "archive_indexes", "packager_sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
