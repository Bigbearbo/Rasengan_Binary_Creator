#!/usr/bin/env python3
"""R33 user-supplied companion integrity and optional independent forward replay.

Git contains a public result and frozen hash commitment, NOT checkpoint binaries.
Usage: python verify_r33_companion.py path/to/sle_ae1_r33_binary6_word_control_20261115.zip --full
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

EXPECTED_ZIP_SHA256 = "2668ecb623c4ea91b36f7e194e0b5f4c561af6a3cb2e240e14c8d815c31b4e13"
FROZEN = {
    "r33_binary6_control.py": "6ed0248820e5b7f603714365644e41fe44391dc2086574a2053ec85f4027a17e",
    "r33_prereg.json": "e9a794f92e02b03b674358e125a42a42a8f08b02308df2f1649a4006927bad5d",
    "r33_manifest.jsonl": "0f301ffe93bb151917d2fbe45dcde496e4a75e4e1f86995e0b20a32bc9ad16aa",
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def verify(zip_path, full=False):
    zip_path = Path(zip_path)
    assert digest(zip_path.read_bytes()) == EXPECTED_ZIP_SHA256, "wrong companion SHA256"
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.testzip() is None, "ZIP CRC failure"
        members = {v.filename: v for v in archive.infolist() if not v.is_dir()}
        assert len(members) == len(archive.namelist()), "directory entries unexpected"
        assert "INVENTORY.json" in members
        recorded = json.loads(archive.read("INVENTORY.json"))
        assert set(members) == set(recorded) | {"INVENTORY.json"}, "inventory mismatch"
        for name, entry in recorded.items():
            # Decline traversal and name shadowing before extracting.
            p = Path(name)
            assert not p.is_absolute() and p.parts and all(x not in (".", "..") for x in p.parts)
            raw = archive.read(name)
            assert len(raw) == entry["size"] and digest(raw) == entry["sha256"], name
        for name, expected in FROZEN.items():
            assert digest(archive.read(name)) == expected, name
        print(f"PASS: companion SHA, ZIP CRC, {len(recorded)} inventory entries, frozen script/prereg/raw bits")
        if full:
            with tempfile.TemporaryDirectory() as work:
                archive.extractall(work)
                env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
                subprocess.run([sys.executable, "verify_package.py", "--full"], cwd=work, check=True, env=env)
            print("PASS: fresh extract, real PyTorch checkpoint replay, independently implemented NumPy forward")
    return True

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("companion_zip")
    ap.add_argument("--full", action="store_true", help="requires PyTorch + NumPy; never trains")
    opt = ap.parse_args()
    verify(opt.companion_zip, opt.full)
