"""Mechanical prereg/final publication only. No learner, optimizer, network or Git calls."""
from pathlib import Path
import argparse
import copy
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DEFAULT_WORK = HERE.parents[1] / "work/e3-continuation-20261113"
PREFIX = "experiments/spiral_neural/20261113_codex_e3_continuation"
HELPERS = {"package_publication.py": "652fe08c087a504a231ae351cf98e28bed6197f45594816a01571797b357a609",
           "package_final.py": "d98ac5ddc5da5846c5c0c4b419576e082abaf93c7605eaad7bfa03dcc2759149"}
PRE = ("prereg/source-freeze.json", "engineering/checks.json", "engineering/portable-input-validation/checks.json",
       "review/design.json", "review/check_protocol.py", "review/protocol-review.json", "review/check_pre_run.py", "review/pre-run.json")
POST = ("review/audit_post.py", "review/metadata-preflight.json", "review/audit-cost.json", "review/post-run.json",
        "review/post-run-details.json", "review/audit-execution-receipt.json", "review/audit.stdout.log", "review/audit.stderr.log")
EXEC = ("launch_formal.py", "execution.stdout.log", "execution.stderr.log", "formal-command-result.json",
        "execution-receipt.json", "git-prereg-receipt.json", "root-execution-intent.json", "latest-Git-read.json")


def load_helpers():
    """Reuse exact already-public helpers, rather than another packaging framework."""
    import hashlib
    candidates = (HERE / "packaging-helpers", HERE.parents[1] / "outputs/e3-learning-probe", HERE.parent / "20261113_codex_e3_learning_probe")
    folder = next((p for p in candidates if all((p / n).is_file() for n in HELPERS)), None)
    if folder is None:
        raise ValueError("Exact parent publication helpers are required beside this study")
    modules = []
    for name, pin in HELPERS.items():
        path = folder / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != pin:
            raise ValueError("Published helper bytes changed")
        spec = importlib.util.spec_from_file_location(Path(name).stem, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


def package(mode, work, approved, out, extras):
    b, z = load_helpers()
    work, out = work.resolve(), out.resolve()
    b.need(not out.exists(), "Never overwrite or retry an existing publication")
    manifest_raw = (work / "prereg/manifest.json").read_bytes()
    manifest = json.loads(manifest_raw.decode("utf-8"))
    b.need(manifest["schema"] == "e3-continuation-v1", "Wrong study")
    freeze = b.read_json(work / "prereg/source-freeze.json")
    pre = b.read_json(work / "review/pre-run.json")
    engineering = b.read_json(work / "engineering/checks.json")
    b.need(b.sha(manifest_raw) == freeze["manifest_sha256"] == pre["manifest_sha256"] == approved, "Manifest gate differs")
    pins = manifest["source_hashes"]
    b.need(len(pins) == 3 and pins == freeze["source_hashes"] == pre["source_hashes"] == engineering["source_hashes"], "Core pins differ")
    b.need(pre["status"] == engineering["status"] == "passed", "Final independent input/engineering gate missing")
    b.need(engineering["tests"] == 4 and engineering["synthetic_forward_calls"] == engineering["synthetic_optimizer_updates"]
           == engineering["trained_forward_calls"] == engineering["trained_optimizer_calls"] == 0,
           "Four mock checks must not claim actual NN/optimizer work")
    frozen = (work / "prereg/inputs.zip").read_bytes()
    b.need(b.info(frozen)["sha256"] == manifest["archive"]["sha256"] == freeze["inputs_zip_sha256"]
           and len(frozen) == manifest["archive"]["bytes"] == freeze["inputs_zip_bytes"], "Original inputs ZIP differs")
    input_index = b.inspect_zip(frozen, manifest["files"])
    files, archives, originals, evidence = {"inputs.zip": frozen, "manifest.json": manifest_raw}, {}, {}, {}
    archives["inputs.zip"] = {**b.info(frozen), **input_index}

    def read(path):
        raw = path.read_bytes()
        originals[path] = b.sha(raw)
        return raw

    def add_evidence(name, path):
        name = b.safe_name(name)
        b.need(name not in evidence, "Duplicate explicit evidence member")
        raw = read(path)
        if name == "formal-command-result.json":
            original = json.loads(raw.decode("utf-8"))
            if b.PRIVATE_TEXT.search(original["command"][0]):
                public = copy.deepcopy(original)
                public["command"][0] = "<python>"
                b.need(public["command"][1:] == original["command"][1:]
                       and all(public[k] == original[k] for k in original if k != "command"), "Redaction changed other fields")
                raw = b.json_bytes(public)
                evidence["public-redactions.json"] = b.json_bytes({"JSON_pointer": "/command/0", "public_member": name,
                    "reason": "machine-userpath", "original_sha256": originals[path], "public": b.info(raw),
                    "replacement": "<python>", "original_value_disclosed": False, "local_original_modified": False})
        b.check_content(name, raw)
        evidence[name] = raw

    for name, pin in pins.items():
        raw = read(b.file_under(HERE, name))
        b.need(b.sha(raw) == pin, "Core changed")
        files[name] = raw
    for name in ("README.md", "pack_public.py") + (("RESULTS.md",) if mode == "final" else ()):
        files[name] = read(b.file_under(HERE, name))
    for name in PRE:
        path = work / name
        if path.is_file():
            add_evidence(name, path)
    add_evidence("EXTERNAL_REVIEW.json", b.file_under(HERE, "EXTERNAL_REVIEW.json"))
    add_evidence("PR47-live-readback.json", b.file_under(work, "PR47-live-readback.json"))
    for module in (b, z):
        path = Path(module.__file__).resolve()
        add_evidence("packaging-helpers/" + path.name, path)
    for name, path in extras:
        add_evidence(name, path.resolve())
    originals[work / "prereg/inputs.zip"] = b.sha(frozen)
    originals[work / "prereg/manifest.json"] = b.sha(manifest_raw)
    science, prior = {}, {}
    if mode == "final":
        post, detail = (b.read_json(work / "review" / n) for n in ("post-run.json", "post-run-details.json"))
        receipt_raw = (work / "execution-receipt.json").read_bytes()
        receipt, closure = json.loads(receipt_raw.decode("utf-8")), b.read_json(work / "review/audit-execution-receipt.json")
        b.need(post["status"] == detail["status"] == "passed" and post["manifest_sha256"] == detail["manifest_sha256"] == approved
               and post["source_hashes"] == detail["source_hashes"] == pins and post["root_confirmed_formal_exit0"] is True,
               "Completed post-audit gate differs")
        b.need(post["receipt_sha256"] == detail["receipt_sha256"] == b.sha(receipt_raw)
               and receipt["exit_code"] == receipt["formal_exit"] == 0 and receipt["formal_session_closed"] is True,
               "Root formal receipt is not closed exit0")
        b.need(closure["status"] == "exit0" and closure["audit_exit_code"] == closure["audit_tool_exit_code"] == 0
               and closure["audit_process_closed"] is True and closure["audit_tool_session_closed"] is True, "Audit process not closed exit0")
        b.need(z.inventory(work / "science") == detail["science_file_inventory"], "Actual science inventory differs from independent audit")
        science = {"science/" + n: read(b.file_under(work / "science", n)) for n in detail["science_file_inventory"]}
        refs = detail["numeric_proof_refs"]
        b.need(len(refs) == len(set(refs)) and set(refs) == set(detail["numeric_proof_inventory"]), "Proof allowlist differs")
        for name in refs:
            raw = read(b.file_under(work / "review", name))
            b.need({"bytes": len(raw), "sha256": b.sha(raw)} == detail["numeric_proof_inventory"][name], "Proof bytes differ")
            add_evidence("review/" + name, work / "review" / name)
        for name in POST + EXEC:
            add_evidence(name, b.file_under(work, name))
        old = work / "publication/prereg"
        prior = b.read_json(old / "compact.json")["public_files"]
        snapshot = {"preregistration/" + n: read(b.file_under(old / "public", n)) for n in prior}
        b.need(all(b.info(snapshot["preregistration/" + n]) == p for n, p in prior.items()), "Original prereg bytes differ")
        raw, index = z.make_archive(snapshot, frozen)
        files["preregistration.zip"], archives["preregistration.zip"] = raw, index

    for kind, entries in (("evidence", evidence), ("science", science)):
        for number, part in enumerate(z.groups(entries), 1):
            name = f"{kind}-{number:03}.zip"
            raw, index = z.make_archive(part)
            b.need(len(raw) <= 3_000_000 or len(part) == 1, "Multi-member archive exceeded cap")
            files[name], archives[name] = raw, index
    for path, pin in originals.items():
        b.need(b.sha(path.read_bytes()) == pin, "Selected original bytes changed")
    if mode == "final":
        b.need(z.inventory(work / "science") == detail["science_file_inventory"], "Science changed while packaging")
    checks = {"status": "PASS", "science_files": len(science), "prereg_snapshot_files": len(prior),
              "all_science_files_preserved": True, "input_finite_arrays": input_index["finite_arrays"],
              "science_finite_arrays": {"NPZ": sum(n.endswith(".npz") for n in science), "NPY": sum(n.endswith(".npy") for n in science)},
              "all_selected_members_byte_CRC_SHA_checked": sum(a["member_count"] for a in archives.values()),
              "original_files_hash_unchanged": len(originals), "packager_NN_optimizer_external_Git_calls": 0}
    files["publication-manifest.json"] = b.json_bytes({"schema": "e3-continuation-publication-v1", "mode": mode,
        "manifest_sha256": approved, "source_hashes": pins, "files": {n: b.info(r) for n, r in sorted(files.items())},
        "archives": archives, "checks": checks, "reused_public_packaging_helpers": HELPERS})
    out.mkdir(parents=True, exist_ok=False)
    public = out / "public"
    public.mkdir()
    texts, binaries, expected = [], [], {}
    for name, raw in sorted(files.items()):
        b.check_content(name, raw) if not name.endswith(".zip") else None
        target = public / b.safe_name(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        b.need(target.read_bytes() == raw, "Public byte roundtrip differs")
        gitpath = PREFIX + "/" + name
        expected[gitpath] = b.blob(raw)
        if name.endswith(".zip"):
            binaries.append({"path": gitpath, "mode": "100644", "type": "blob", **b.info(raw), "local_file": "public/" + name})
        else:
            content = raw.decode("utf-8")
            b.need(content.encode("utf-8") == raw, "Text entry bytes differ")
            texts.append({"path": gitpath, "mode": "100644", "type": "blob", "content": content})
    for name, value in (("text-entries.json", texts), ("binary-entries.json", binaries), ("expected-blobs.json", expected)):
        b.write_json(out / name, value)
    compact = {"status": "verified", "mode": mode, "public_directory": public.as_posix(), "repo_prefix": PREFIX,
        "public_files": {n: b.info(r) for n, r in sorted(files.items())}, "removed_from_root": sorted(set(prior) - set(files)),
        "public_files_over_1MiB": {n: b.info(r) for n, r in sorted(files.items()) if len(r) > 1048576},
        "archive_indexes": {n: {k: v for k, v in a.items() if k != "members"} for n, a in archives.items()},
        "checks": checks, "text_entries": len(texts), "binary_entries": len(binaries), "packager_sha256": b.sha(Path(__file__).read_bytes())}
    b.write_json(out / "compact.json", compact)
    return compact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prereg", "final"), required=True)
    parser.add_argument("--approved-manifest-sha", required=True)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--evidence", action="append", default=[], help="Exact public member=local file; no directory globs")
    args = parser.parse_args()
    extras = [(name, Path(path)) for name, path in (value.split("=", 1) for value in args.evidence)]
    result = package(args.mode, args.work_root, args.approved_manifest_sha,
                     args.out or args.work_root / "publication" / args.mode, extras)
    print(json.dumps({k: result[k] for k in ("status", "mode", "text_entries", "binary_entries", "checks", "packager_sha256")}))
