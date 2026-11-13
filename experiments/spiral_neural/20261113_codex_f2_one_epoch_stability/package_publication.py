"""Preregistration bytes only; never import a learner, run NN, or mutate Git."""
from pathlib import Path, PurePosixPath
import argparse
import gzip
import hashlib
import io
import json
import math
import re
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "work/f2-stability-20261113"
PREFIX = "experiments/spiral_neural/20261113_codex_f2_one_epoch_stability"
CORE = ("run_stability.py", "protocol.json", "test_stability.py")
REFERENCE_SHA = "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"

PRIVATE_TEXT = re.compile(r"(?i)(?:[A-Z]:[\\/]Us" r"ers[\\/]|/ho" r"me/|/Us" r"ers/|Bearer\s+[A-Za-z0-9._-]{8,}|sk-or-v1-[A-Za-z0-9]+)")
PRIVATE_KEYS = {"private_raw_api_record", "private_legacy_record", "raw_api_path", "api_key", "access_token",
                "refresh_token", "id_token", "authorization_header", "account_quota", "quota_remaining"}
PRIVATE_NAMES = {".git", ".ssh", ".aws", "__pycache__", "fontcache", "autonomous-state.json", "transport.json"}

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
    need(suffix in (".json", ".jsonl", ".py", ".md", ".txt", ".log", ".ast"), f"Unknown public content kind: {name}")
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


def source_guard(approved):
    raw = (WORK / "prereg/manifest.json").read_bytes()
    need(sha(raw) == approved, "Approved manifest differs")
    manifest = json.loads(raw.decode("utf-8"))
    need(manifest["schema"] == "f2-stability-paired-v1", "Wrong study")
    freeze = read_json(WORK / "prereg/source-freeze.json")
    need(freeze["manifest_sha256"] == approved and freeze["source_hashes"] == manifest["source_hashes"], "Source freeze differs")
    need(set(manifest["source_hashes"]) == set(CORE), "Unexpected core sources")
    for name, pin in manifest["source_hashes"].items():
        need(sha(file_under(HERE, name).read_bytes()) == pin, "Core source changed")
    engineering = read_json(WORK / "engineering/checks.json")
    need(engineering["status"] == "passed" and engineering["tests"] == 4
         and engineering["source_hashes"] == manifest["source_hashes"], "Engineering gate differs")
    pre = read_json(WORK / "review/pre-run.json")
    need(pre["status"] == "passed" and pre["manifest_sha256"] == approved
         and pre["source_hashes"] == manifest["source_hashes"], "Final independent pre-run gate missing/different")
    portable = pre["portable_native_validation"]
    need(portable["original_workspace_reads_denied"] is True and portable["NN_method_attempts"] == 0
         and portable["original_five_source_inputs_SHA_unchanged"] is True, "Portable input gate incomplete")
    need(manifest["protocol"]["replay_seeds"] == [] and manifest["protocol"]["new_replay_updates"] == 0, "Wrong formal replay scope")
    archive = (WORK / "prereg/inputs.zip").read_bytes()
    need(info(archive)["sha256"] == manifest["archive"]["sha256"] == freeze["inputs_zip_sha256"]
         and len(archive) == manifest["archive"]["bytes"] == freeze["inputs_zip_bytes"], "Frozen input ZIP differs")
    index = inspect_zip(archive, manifest["files"])
    need(index["member_count"] == 36 and index["finite_arrays"] == {"NPZ": 9, "NPY": 3}, "Complete start/control states and courses required")
    need(index["members"]["source/p030_binary_continual.py"]["sha256"] == REFERENCE_SHA, "Original reference differs")
    for seed, parent in manifest["parents"].items():
        need(index["members"][f"initial/seed{seed}.npz"]["sha256"] == parent["raw_sha256"]
             == index["members"][f"historical/seed{seed}/start-state.npz"]["sha256"], "Initial raw state differs")
    return manifest, archive, index


def selected_sources():
    files = {name: HERE / name for name in CORE + ("README.md", "RESEARCH_NOTE.md", "HANDOFF.md", "EXTERNAL_REVIEW.json", "package_publication.py")}
    files.update({name: WORK / "prereg" / name for name in ("manifest.json", "source-freeze.json", "inputs.zip")})
    files["engineering-checks.json"] = WORK / "engineering/checks.json"
    for name in ("check_protocol.py", "protocol-review.json", "protocol-helper-attempt-01.json", "check_pre_run.py", "pre-run.json"):
        files["review/" + name] = WORK / "review" / name
    for name in ("PR33-publication-manifest.json", "PR33-live-readback.json"):
        files["references/" + name] = WORK / "references" / name
    files["external-method-checks.json"] = WORK / "external-method-checks.json"
    files["external-context.json"] = ROOT / "outputs/agent-team/context/f2_one_epoch_stability.json"
    return files


def package(approved, out):
    out = Path(out).resolve()
    need(not out.exists(), "Existing publication must not be overwritten")
    manifest, raw_archive, archive_index = source_guard(approved)
    sources = selected_sources()
    files = {}
    originals = {}
    for name, path in sources.items():
        safe_name(name)
        need(path.is_file() and path.resolve().is_relative_to(ROOT), "Missing/escaped selected source")
        raw = path.read_bytes()
        if name != "inputs.zip": check_content(name, raw)
        files[name] = raw
        originals[path] = sha(raw)
    need(files["inputs.zip"] == raw_archive, "Input container changed")
    report = {"schema": "f2-stability-prereg-publication-v1", "status": "verified", "mode": "preregistration",
              "manifest_sha256": approved, "source_hashes": manifest["source_hashes"],
              "files": {name: info(raw) for name,raw in sorted(files.items())},
              "archives": {"inputs.zip": {**info(raw_archive), **archive_index, "exact_frozen_container": True}},
              "historical_controls_retrained": False, "new_outcomes_observed": False,
              "portable_checks_evidence": "review/pre-run.json#portable_native_validation",
              "formal_optimizer_replay_planned": False, "packager_NN_optimizer_benchmark_external_calls": 0}
    files["publication-manifest.json"] = json_bytes(report)
    checks = {"status": "PASS", "mode": "preregistration", "archive_members_bytes_CRC_SHA_verified": archive_index["member_count"],
              "finite_arrays": archive_index["finite_arrays"], "final_independent_pre_run_gate": "passed",
              "source_inputs_original_bytes_unchanged": True, "privacy_all_selected_members_checked": True,
              "packager_NN_optimizer_benchmark_external_calls": 0, "new_science_read_or_executed": False}
    files["export-checks.json"] = json_bytes(checks)
    for path, pin in originals.items(): need(sha(path.read_bytes()) == pin, "Original changed while packaging")
    out.mkdir(parents=True, exist_ok=False);public=out/"public";public.mkdir()
    texts,binaries,expected=[],[],{}
    for name,raw in sorted(files.items()):
        target=public/safe_name(name);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("xb") as stream: stream.write(raw)
        need(target.read_bytes()==raw,"Published byte roundtrip differs")
        gitpath=PREFIX+"/"+name;expected[gitpath]=blob(raw)
        if name.endswith(".zip"):
            binaries.append({"path":gitpath,"mode":"100644","type":"blob",**info(raw),"local_file":"public/"+name})
        else:
            content=raw.decode("utf-8");need(content.encode("utf-8")==raw,"Text Git bytes differ")
            texts.append({"path":gitpath,"mode":"100644","type":"blob","content":content})
    write_json(out/"text-entries.json",texts);write_json(out/"binary-entries.json",binaries);write_json(out/"expected-blobs.json",expected)
    result={"status":"verified","mode":"preregistration","repo_prefix":PREFIX,"manifest_sha256":approved,
            "public_files":{name:info(raw) for name,raw in sorted(files.items())},
            "public_files_over_1MiB":{name:info(raw) for name,raw in sorted(files.items()) if len(raw)>1048576},
            "archive_indexes":{"inputs.zip":{**info(raw_archive),"member_count":archive_index["member_count"],"finite_arrays":archive_index["finite_arrays"]}},
            "full_member_inventory":"public/publication-manifest.json","text_entries":len(texts),"binary_entries":len(binaries),
            "checks":checks,"packager_sha256":sha(Path(__file__).read_bytes())}
    write_json(out/"compact.json",result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg",action="store_true")
    parser.add_argument("--approved-manifest-sha",required=True)
    parser.add_argument("--out",type=Path,default=WORK/"publication/prereg")
    args=parser.parse_args();need(args.prereg,"Only explicitly authorized prereg packaging is implemented")
    result=package(args.approved_manifest_sha,args.out)
    print(json.dumps({key:result[key] for key in ("status","mode","text_entries","binary_entries","archive_indexes","packager_sha256")},ensure_ascii=False))


if __name__=="__main__": main()
