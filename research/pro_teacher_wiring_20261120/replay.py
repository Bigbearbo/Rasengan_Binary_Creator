"""Verify this archive, then reproduce the studies in a clean temporary directory."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(directory):
    entries = (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    for line in entries:
        checksum, name = line.split("  ", 1)
        if sha(directory / name) != checksum:
            raise ValueError(f"SHA-256 mismatch: {name}")
    return [line.split("  ", 1)[1] for line in entries]


def run(directory, *args, captured_file=None):
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONUTF8="1")
    process = subprocess.run([sys.executable, "-B", *args], cwd=directory, env=environment,
                             check=True, stdout=subprocess.PIPE)
    if captured_file:
        # These one-line JSON outputs are recorded with Unix line endings in the archive.
        (directory / captured_file).write_bytes(process.stdout.replace(b"\r\n", b"\n"))


def identical(reference, new):
    if sha(reference) != sha(new):
        raise ValueError(f"Replay differs: {new.name} (expected {sha(reference)}, found {sha(new)})")
    print(f"  SHA-256 agrees: {reference.relative_to(ROOT)}", flush=True)


def main():
    paths = verify(ROOT)
    print(f"{len(paths)} source/record hashes verified.", flush=True)
    with tempfile.TemporaryDirectory(prefix="sle_edge_teaching_replay_") as temp:
        work = Path(temp)
        for name in paths:
            dest = work / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        print("Original PR137 and frozen S1", flush=True)
        s1 = "upstream/serial_adder.py"
        previous = "remedial/previous/ste_test.py"
        run(work, previous, s1, "--output", "old_replay.json", "--raw", "old_raw.bin")
        identical(ROOT / "upstream/pr137_results.json", work / "old_replay.json")
        identical(ROOT / "raw_internal.bin", work / "old_raw.bin")
        print("Transfer training and two independent audits", flush=True)
        run(work, "transfer.py")
        for name in ("results.json", "raw_internal.bin"):
            identical(ROOT / name, work / name)
        run(work, "audit_transfer.py", "results.json", captured_file="independent.json")
        identical(ROOT / "independent.json", work / "independent.json")
        run(work, "audit.py")
        identical(ROOT / "audit.json", work / "audit.json")
        print("Remediation and its independent audit", flush=True)
        run(work, "remedial/remedial.py", previous, s1)
        identical(ROOT / "remedial/results.json", work / "remedial/results.json")
        run(work, "remedial/explore_wrong.py", "remedial/results.json", previous, s1)
        identical(ROOT / "remedial/explore_results.json", work / "remedial/explore_results.json")
        run(work, "remedial/check_scores.py", "remedial/results.json", "remedial/explore_results.json",
            captured_file="remedial/check_scores.json")
        identical(ROOT / "remedial/check_scores.json", work / "remedial/check_scores.json")
    verify(ROOT)
    print("PASS: 9 byte-for-byte reproductions; archived inputs unchanged.")


if __name__ == "__main__":
    main()
