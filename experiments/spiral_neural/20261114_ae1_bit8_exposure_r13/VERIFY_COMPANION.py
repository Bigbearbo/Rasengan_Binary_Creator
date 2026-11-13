#!/usr/bin/env python3
"""Verify external R13 AE1 NN companion ZIP and independently replay its raw outputs.
Standalone public launcher; requires locally supplied ZIP, NumPy and PyTorch for
the frozen static gate, but the actual inference replay uses NumPy only.
No network calls and no model retraining.
Usage: python VERIFY_COMPANION.py /path/to/sle_ae1_bit8_exposure_20261114_r13.zip
"""
import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile

EXPECTED="cfb4d067dd55f21da296d60402d82c72c3d221e59f4741d1936264a4ed621705"
FOLDER="sle_ae1_bit8_exposure_r13"

def main(path):
    path=pathlib.Path(path)
    got=hashlib.sha256(path.read_bytes()).hexdigest()
    if got!=EXPECTED:
        raise ValueError(f"companion ZIP SHA256 mismatch: {got}")
    with tempfile.TemporaryDirectory(prefix="sle_ae1_r13_verify_") as td:
        root=pathlib.Path(td)
        with zipfile.ZipFile(path) as z:
            members=z.namelist()
            if not members or any(
                x.startswith("/") or ".." in pathlib.PurePosixPath(x).parts
                or not x.startswith(FOLDER+"/") for x in members):
                raise ValueError("Unsafe/unexpected ZIP member name")
            z.extractall(root)
        p=root/FOLDER
        lines=(p/"SHA256SUMS.txt").read_text().splitlines()
        for line in lines:
            sha,rel=line.split("  ",1)
            name=pathlib.PurePosixPath(rel)
            if rel.startswith("/") or ".." in name.parts:
                raise ValueError("unsafe relative file")
            if hashlib.sha256((p/rel).read_bytes()).hexdigest()!=sha:
                raise ValueError(f"file mismatch: {rel}")
        assert len(lines)==17
        env=os.environ.copy()
        env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
        for argv in (
            [sys.executable,"train_bit8.py","gate"],
            [sys.executable,"verify_numpy_r13.py"],
        ):
            subprocess.run(argv,cwd=p,env=env,check=True)
        print(f"R13 PASS: ZIP SHA256 {got}, {len(lines)} member hashes, "
              "preflight, 624/624 independent neural-inference answers; "
              "0 additional optimizer updates.")

if __name__=="__main__":
    if len(sys.argv)!=2:
        sys.exit("Usage: python VERIFY_COMPANION.py <original R13 ZIP>")
    main(sys.argv[1])
