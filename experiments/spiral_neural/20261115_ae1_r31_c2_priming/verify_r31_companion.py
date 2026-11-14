#!/usr/bin/env python3
"""Verify the R31 portable ZIP; Git alone does not contain neural weights.

Usage:
  python verify_r31_companion.py /path/to/sle_ae1_r31_c2_priming_20261115.zip
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys
import tempfile
import zipfile

ARCHIVE_SHA256 = "961bad8563c23363c71812aab1c22b961c7f1f022b1896d3f107c3f19059776f"


def verify(path: pathlib.Path) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != ARCHIVE_SHA256:
        raise ValueError(f"Archive SHA mismatch: {actual} != {ARCHIVE_SHA256}")
    with tempfile.TemporaryDirectory(prefix="sle_r31_verify_") as tmp:
        root = pathlib.Path(tmp)
        with zipfile.ZipFile(path, "r") as z:
            for info in z.infolist():
                dest = (root / info.filename).resolve()
                if not dest.is_relative_to(root.resolve()):
                    raise ValueError(f"Unsafe ZIP member: {info.filename}")
            z.extractall(root)
        tests = [
            [sys.executable, "r31_runner.py", "replay"],
            [sys.executable, "r31_numpy_audit.py"],
        ]
        manifest = root / "SHA256SUMS_R31"
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            expected, relative = line.split("  ", 1)
            item = (root / relative).resolve()
            if not item.is_relative_to(root.resolve()) or not item.is_file():
                raise ValueError(f"Missing/unsafe inventory item: {relative}")
            if hashlib.sha256(item.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Inventory SHA mismatch: {relative}")
        print("SHA256 inventory verified")
        for command in tests:
            subprocess.run(command, cwd=root, check=True)
        print("R31 companion verified: independent actual-checkpoint replays")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python verify_r31_companion.py <companion.zip>")
    verify(pathlib.Path(sys.argv[1]).resolve())
