#!/usr/bin/env python3
"""Read-only verification of the separate R45 native01 companion ZIP.

Run: python verify_r45_companion.py /path/to/sle_ae1_r45_balanced_unmask_20261115.zip
Requires CPU PyTorch and NumPy for independent checkpoint replay.
The public Git branch does NOT contain the checkpoint weights.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ZIP_SHA256 = "7dfe1c5683fe117ae46e4c8e4569f5b62285eeda2fb2265c0f6f99da5a73eeea"
EXPECTED_HASHED_FILES = 223
EXPECTED_RAW_SHA = "21cda675240066c1436fe1edd73b00e687aa2418810eed03f0e0ab2f880667db"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(zip_path: str) -> None:
    source = Path(zip_path).resolve(strict=True)
    actual = sha256(source)
    if actual != ZIP_SHA256:
        raise ValueError(f"R45 ZIP SHA mismatch: {actual}")
    with tempfile.TemporaryDirectory(prefix="r45-verify-") as work:
        root = Path(work)
        with zipfile.ZipFile(source, "r") as archive:
            for entry in archive.infolist():
                dest = (root / entry.filename).resolve()
                if not dest.is_relative_to(root):
                    raise ValueError(f"Unsafe entry: {entry.filename}")
                if entry.is_dir():
                    continue
                # Never let a companion archive contain symlinks.
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError(f"Symlink entry refused: {entry.filename}")
            archive.extractall(root)
        lines = (root / "R45_SHA256SUMS").read_text(encoding="utf-8").splitlines()
        if len(lines) != EXPECTED_HASHED_FILES:
            raise ValueError(f"File hash count {len(lines)} != {EXPECTED_HASHED_FILES}")
        seen = set()
        for line in lines:
            wanted, relative = line.split("  ", 1)
            target = (root / relative).resolve()
            if not target.is_relative_to(root) or relative in seen:
                raise ValueError(f"Unsafe or duplicate checksum entry: {relative}")
            seen.add(relative)
            if not target.is_file() or sha256(target) != wanted:
                raise ValueError(f"File checksum failed: {relative}")
        if sha256(root / "r45_outputs" / "raw_results.jsonl") != EXPECTED_RAW_SHA:
            raise ValueError("Raw NN output digest mismatch")
        print(f"PASS companion ZIP and {len(lines)}/{EXPECTED_HASHED_FILES} file SHA256")
        env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
        for mode in ("static", "replay", "numpy"):
            print("Read-only R45", mode, flush=True)
            subprocess.run(
                [sys.executable, "r45_unmasked_balanced.py", mode],
                cwd=root,
                env=env,
                check=True,
            )
        print("PASS R45 clean, independent native01 verification")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python verify_r45_companion.py <R45 ZIP>")
    main(sys.argv[1])
