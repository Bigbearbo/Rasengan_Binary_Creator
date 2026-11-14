#!/usr/bin/env python3
"""Public R30 companion verifier. Does NOT train a student or use any oracle.
Usage: python verify_r30_companion.py /path/sle_ae1_r30_no_firstword_mask_20261115.zip
Requires numpy, torch and the Python interpreter in PATH. The companion ZIP
contains runnable full source, original controls, new weights and raw outputs.
"""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import tempfile
import zipfile

ZIP_NAME = "sle_ae1_r30_no_firstword_mask_20261115.zip"
ZIP_SHA256 = "22747e62238b527bb6c1ce7fe1bb0f6352cf970495b90c74e37a86700809d714"
RUNNER_SHA256 = "e69dda36723ce435887715539728bfe8eff70f522dbbeef45acc9aeb1e353630"
PREREG_SHA256 = "021684c38ff7a30fac9aece307571b3c5460dc9f7550e7b999e6944c5851f760"
RAW_SHA256 = "f1fabf4abd7d9d6dfdcae3fbed3cd340dd40f1d52d96dbf641e78a8160b1e0e9"
MANIFEST_SHA256 = "b8a7aa71b1921e28b8fc85f61e2ae16c5856dbd13d59d612bd506bbb7d2eac64"
SEED_WEIGHT_SHA256 = {
    101: "79aa059bfd228bd25ddb54e097d288bf7ddbd2f7327baf2d5d059852b527fd6b",
    202: "12474280aa26fc0fc4bce3721ff2c0685aad655207a6cc56c1910986f520e1f2",
    303: "8bbb54300bbbfc9c6ed794d55f142ed74ecc79e9ec0dea486975d0ee2e8d6e7f",
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check(root, name, expected):
    actual = sha(root / name)
    if actual != expected:
        raise ValueError(f"{name}: SHA256 mismatch {actual} != {expected}")

def verify(archive):
    if archive.name != ZIP_NAME:
        print(f"Note: file named {archive.name!r}; checking its bytes, not its name")
    if sha(archive) != ZIP_SHA256:
        raise ValueError("Companion ZIP SHA256 mismatch; do not run mismatched source")
    with tempfile.TemporaryDirectory(prefix="sle_r30_verify_") as work:
        root = Path(work)
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            if len(names) != len(set(names)):
                raise ValueError("duplicate names inside ZIP")
            if any(n.startswith("/") or ".." in Path(n).parts for n in names):
                raise ValueError("unsafe ZIP path")
            z.extractall(root)
        check(root, "r30_runner.py", RUNNER_SHA256)
        check(root, "prereg.json", PREREG_SHA256)
        check(root, "manifest.jsonl", MANIFEST_SHA256)
        check(root, "outputs/raw_results.jsonl", RAW_SHA256)
        for seed, expected in SEED_WEIGHT_SHA256.items():
            check(root, f"outputs/weights_{seed}_dual.json", expected)
        pairs = []
        for line in (root / "SHA256SUMS").read_text().splitlines():
            digest, rel = line.split("  ", 1)
            check(root, rel, digest)
            pairs.append(rel)
        if len(pairs) != 65:
            raise ValueError("unexpected manifest size")
        env = {**os.environ, "OMP_NUM_THREADS": "1",
               "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
        for argv in (["r30_runner.py", "gate"],
                     ["r30_runner.py", "replay"], ["r30_numpy_audit.py"]):
            p = subprocess.run([sys.executable, *argv], cwd=root, env=env,
                               capture_output=True, text=True, check=True)
            print(p.stdout.strip())
        print("R30 COMPANION VERIFY PASS: 65 SHA entries; 1008 replay; 1008 NumPy")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} {ZIP_NAME}")
    verify(Path(sys.argv[1]).resolve())
