#!/usr/bin/env python3
"""Verify the frozen R63 evidence ZIP from a clean temporary directory.

Requires Python 3, NumPy, PyTorch for loading reference source; never trains.
The full independent NumPy math+classifier replayer is packaged in the ZIP.
"""
import hashlib
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

EXPECTED_ZIP_SHA256 = "447ed20ee7290a63fbf05559823f63d22fdea06974979ad87990a6ae57dfa4f2"
EXPECTED_RAW_SHA256 = "425d786ae45e8af9d07039fe0afab76466ae198be893eaa1929906b51449d974"

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python verify_r63_bundle.py <sle_ae1_r63_frozen_frame_guard_20261116.zip>")
    src = Path(sys.argv[1])
    data = src.read_bytes()
    assert hashlib.sha256(data).hexdigest() == EXPECTED_ZIP_SHA256, "bundle SHA mismatch"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(src) as bundle:
            assert bundle.testzip() is None, "bundle CRC mismatch"
            names = bundle.namelist()
            assert all(x.startswith("r63/") and ".." not in Path(x).parts for x in names)
            bundle.extractall(tmp)
        root = tmp / "r63"
        records = root / "r63_outputs" / "raw_records.jsonl"
        assert hashlib.sha256(records.read_bytes()).hexdigest() == EXPECTED_RAW_SHA256
        subprocess.run([sys.executable, str(root / "verify_bundle.py")], cwd=root, check=True)
    print("R63_PUBLIC_VERIFICATION_PASS")

if __name__ == "__main__":
    main()
