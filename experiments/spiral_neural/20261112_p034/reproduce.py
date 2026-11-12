"""Run original P034 guards in a reconstructed workspace; default is preflight.

Prepare inputs first with prepare_public_inputs.py. Only B1.OUT is rebound;
E900 uses its original --root/--out arguments. Scientific files stay unchanged.
An explicit --execute enables future full fixed-budget runs after preflight.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2,
                  allow_nan=False)
        stream.write("\n")


def within(path, root):
    return path == root or root in path.parents


def load_frozen(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_prepared(workspace):
    report = read_json(workspace / "prepared-inputs.json")
    if not report["source_bytes_rewritten"] is False or report["learning_code_changes"] != 0:
        raise ValueError("Prepared workspace reports scientific code changes")
    actual = {}
    for name, expected in report["staged_files"].items():
        path = (workspace/name).resolve()
        if not within(path, workspace) or not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing/unsafe prepared input: {name}")
        digest = sha(path)
        if digest != expected["sha256"] or path.stat().st_size != expected["bytes"]:
            raise ValueError(f"Prepared input changed before preflight: {name}")
        actual[name] = digest
    return report, actual


def child(workspace, output, kind, *, execute=False):
    """Separate interpreters preserve each original source-import identity guard."""
    here = workspace / "outputs/sle-p034"
    sys.path.insert(0, str(here))
    # Loading NumPy here establishes its installed runtime location without
    # importing any scientific source. Later scientific reads are confined.
    import numpy as np
    runtime_roots = {Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(),
                     Path(sys.executable).resolve().parent, Path(np.__file__).resolve().parent}
    wrapper_files = {Path(__file__).resolve(), Path(__file__).with_name(
        "prepare_public_inputs.py").resolve()}
    audit = {"writes": [], "learning_calls": 0, "source_modules": {},
             "reads_limited_to_prepared_workspace_runtime_and_wrappers": True}
    learning_names = {"step", "lesson", "loss_grad", "learning", "primary_run", "run_one",
                      "trial", "timing_learning", "fit_verified"}

    def writer_path(value):
        if isinstance(value, (str, bytes, os.PathLike)):
            return Path(os.fsdecode(value)).resolve()
        return None

    def enforce_write(value):
        path = writer_path(value)
        if path is not None:
            if not within(path, output):
                raise PermissionError(f"Portable guard blocked a write outside NEW output: {path}")
            audit["writes"].append(str(path))

    def audit_hook(event, args):
        if event == "open":
            name, mode, flags = args
            writing = ((isinstance(mode, str) and any(c in mode for c in "wax+")) or
                       (isinstance(flags, int) and flags &
                        (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
            if writing:
                enforce_write(name)
            else:
                path = writer_path(name)
                if path is not None and not (
                        within(path, workspace) or within(path, output) or path in wrapper_files or
                        any(within(path, root) for root in runtime_roots)):
                    raise PermissionError(f"Portable guard blocked a read outside prepared inputs/runtime: {path}")
        elif event in ("os.mkdir", "os.remove", "os.rmdir", "os.unlink", "os.chmod", "os.utime"):
            enforce_write(args[0])
        elif event in ("os.rename", "os.replace"):
            enforce_write(args[0])
            enforce_write(args[1])

    def profile(frame, event, arg):
        if event == "call" and frame.f_code.co_name in learning_names:
            filename = Path(frame.f_code.co_filename).resolve()
            if within(filename, workspace):
                audit["learning_calls"] += 1
                if not execute:
                    raise AssertionError(f"Preflight attempted a learning function: {filename}:{frame.f_code.co_name}")

    sys.addaudithook(audit_hook)
    sys.setprofile(profile)
    started = time.perf_counter()
    binding = {}
    try:
        if kind == "e900":
            module = load_frozen(here/"e900.py", "p034_frozen_e900")
            original_hash = sha(here/"e900.py")
            if execute:
                sys.argv = [str(here/"e900.py"), "--root", str(workspace),
                            "--out", str(output/"e900")]
                module.main()
                report = {"status": "passed", "mode": "original_fixed_budget_execution"}
            else:
                old, runs, before, pins = module.verify_sources(workspace)
                for name in ("PRO_RESEARCH_DESIGN_20261112.md", "PR8_AGENTS.md",
                             "CURRENT_RESEARCH_STATUS.md", "spiral_language_research_index.md"):
                    path = workspace/"work/sle-p034/source-plan"/name
                    before[module.relative(workspace, path)] = module.sha(path)
                before[module.relative(workspace, here/"e900.py")] = original_hash
                after = module.check_unchanged(workspace, before)
                report = {
                    "status": "passed", "original_functions": ["verify_sources", "check_unchanged"],
                    "historical_courses": len(runs), "immutable_inputs_checked": len(before),
                    "before_equals_after": before == after, "public_source_pins": pins,
                    "historical_ROOT_constant_preserved_unused": str(old.ref.ROOT),
                    "historical_OUT_constant_preserved_unused": str(old.ref.OUT),
                }
                audit["source_modules"] = {"p032_reference": str(Path(old.__file__).resolve()),
                                             "p030_reference": str(Path(old.ref.__file__).resolve())}
            assert sha(here/"e900.py") == original_hash
        else:
            module = load_frozen(here/"b1_trial.py", "p034_frozen_b1")
            original_hash = sha(here/"b1_trial.py")
            binding = {"B1.OUT": {"original": str(module.OUT), "bound": str(output/"b1")},
                       "unchanged": {"HERE": str(module.HERE), "ROOT": str(module.ROOT),
                                     "BASELINE": str(module.BASELINE)}}
            module.OUT = output/"b1"
            sys.argv = [str(here/"b1_trial.py")] + ([] if execute else ["--preflight-only"])
            module.main()
            report = read_json(module.OUT/("compact.json" if execute else "preflight.json"))
            audit["source_modules"] = {"p033": str(Path(module.p033.__file__).resolve()),
                                         "p032_reference": str(Path(module.old.__file__).resolve()),
                                         "p030_reference": str(Path(module.ref.__file__).resolve())}
            assert sha(here/"b1_trial.py") == original_hash
    finally:
        sys.setprofile(None)
    if not execute:
        assert audit["learning_calls"] == 0
    result = {"kind": kind, "status": "passed", "execute": execute,
              "scientific_updates": None if execute else 0,
              "frozen_runner_sha256": original_hash, "bindings": binding,
              "source_bytes_changed": False, "audit": audit,
              "original_guard_result": report, "seconds": time.perf_counter()-started}
    dump(output/f"{kind}-{'execution' if execute else 'portable-preflight'}.json", result)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true",
                        help="Explicitly run original scientific budgets after all read-only preflights")
    parser.add_argument("--_child", choices=("e900", "b1"), help=argparse.SUPPRESS)
    parser.add_argument("--_execute-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    workspace, output = args.workspace.resolve(), args.output.resolve()
    if args._child:
        return child(workspace, output, args._child, execute=args._execute_child)
    prepared, before = verify_prepared(workspace)
    if output.exists() or output == workspace or within(workspace, output):
        raise FileExistsError("Use a NEW output directory distinct from the input workspace")
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    for execute in ([False, True] if args.execute else [False]):
        for kind in ("e900", "b1"):
            command = [sys.executable, "-X", "utf8", "-B", str(Path(__file__).resolve()),
                       "--workspace", str(workspace), "--output", str(output), "--_child", kind]
            if execute:
                command.append("--_execute-child")
            subprocess.run(command, cwd=workspace, check=True)
    _, after = verify_prepared(workspace)
    if before != after:
        raise AssertionError("An original scientific source or prepared input was modified")
    reports = {kind: read_json(output/f"{kind}-portable-preflight.json")
               for kind in ("e900", "b1")}
    result = {"status": "passed", "mode": "execute" if args.execute else "preflight_only",
              "scientific_updates": None if args.execute else 0,
              "workspace": str(workspace), "new_output": str(output),
              "input_files_unchanged": len(before), "original_sources_and_guards_unchanged": True,
              "only_module_binding": reports["b1"]["bindings"],
              "preflight_learning_calls": sum(r["audit"]["learning_calls"] for r in reports.values()),
              "writes_limited_to_new_output": True, "seconds": time.perf_counter()-started,
              "public_PR7_git_blob": prepared["public_PR7_git_blob"],
              "frozen_scientific_sources": prepared["frozen_scientific_sources"],
              "prepare_script_sha256": sha(Path(__file__).with_name("prepare_public_inputs.py")),
              "reproduce_script_sha256": sha(Path(__file__).resolve())}
    dump(output/"portable-check.json", result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
