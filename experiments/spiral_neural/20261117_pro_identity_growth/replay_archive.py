"""Validate an authorized archive and independently replay its saved results.

Requires Python 3.10+ and NumPy. Obtain the exact research archive from its
owner. This public entry point contains no private source or checkpoints.
It performs no training, new arithmetic-core execution, or network requests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile


ARCHIVE = "sle_identity_growth_20261117_v1.zip"
EXPECTED_SHA256 = '6f72122c769e83e5e3643a75fd97149fe610151e7ffe690f5b00a505395758f4'
EXPECTED_BYTES = 1519183  # Optional integer size pin, in addition to SHA256.
ROOT_NAME = "identity_growth_20261117"
MANIFEST_NAME = "ARTIFACT_MANIFEST.json"


def stream_digest(stream):
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(1024*1024), b""):
        digest.update(block)
        size += len(block)
    return digest.hexdigest(), size


def safe_parts(name, *, directory=False):
    """Accept one canonical portable relative ZIP/manifest path."""
    if not isinstance(name, str) or not name or "\x00" in name or "\\" in name:
        raise ValueError("Invalid archive member path")
    raw = name[:-1] if directory and name.endswith("/") else name
    parts = raw.split("/")
    if (not raw or PurePosixPath(raw).is_absolute()
            or any(part in ("", ".", "..") or ":" in part for part in parts)):
        raise ValueError("Unsafe or noncanonical archive member path")
    return tuple(parts)


def checked_members(archive):
    """Check every ZIP member and every manifest entry before extraction."""
    items = archive.infolist()
    names, file_names, directory_names = set(), set(), set()
    for item in items:
        parts = safe_parts(item.filename, directory=item.is_dir())
        if parts[0] != ROOT_NAME:
            raise ValueError("Unexpected archive root")
        canonical = "/".join(parts)
        if canonical in names:
            raise ValueError("Duplicate or colliding ZIP member")
        names.add(canonical)
        mode = item.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        allowed_type = stat.S_IFDIR if item.is_dir() else stat.S_IFREG
        if file_type not in (0, allowed_type) or stat.S_ISLNK(mode):
            raise ValueError("Symbolic link or special file in archive")
        if item.flag_bits & 1:
            raise ValueError("Encrypted archive members are unsupported")
        if item.is_dir():
            if item.file_size:
                raise ValueError("Directory member unexpectedly contains data")
            directory_names.add(canonical)
        else:
            if len(parts) < 2:
                raise ValueError("Archive root must be a directory")
            file_names.add(canonical)
    required_directories = {ROOT_NAME}
    for name in file_names:
        parts = name.split("/")
        for i in range(1, len(parts)):
            parent = "/".join(parts[:i])
            if parent in file_names:
                raise ValueError("ZIP file conflicts with a required directory")
            required_directories.add(parent)
    if not directory_names.issubset(required_directories):
        raise ValueError("Unaccounted empty directory in archive")
    if archive.testzip() is not None:
        raise ValueError("ZIP CRC verification failed")

    manifest_path = ROOT_NAME+"/"+MANIFEST_NAME
    if manifest_path not in file_names:
        raise ValueError("Missing artifact manifest")
    manifest = json.loads(archive.read(manifest_path).decode("utf-8"))
    if manifest.get("schema") != "sle-artifact-members-v1" or not isinstance(manifest.get("files"), list):
        raise ValueError("Unsupported artifact manifest schema")
    recorded = {}
    for item in manifest["files"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid manifest entry")
        relative = "/".join(safe_parts(item.get("path")))
        name = ROOT_NAME+"/"+relative
        if name == manifest_path or name in recorded:
            raise ValueError("Duplicate or self-referential manifest entry")
        size, digest = item.get("size_bytes"), item.get("sha256")
        if type(size) is not int or size < 0:
            raise ValueError("Invalid manifest size")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid manifest hash")
        recorded[name] = (size, digest)
    # The manifest cannot hash itself. The outer archive SHA256 pins it.
    if set(recorded) != file_names-{manifest_path}:
        raise ValueError("Manifest does not describe exactly all archive files")
    total_member_bytes = 0
    for name, (expected_size, expected_digest) in recorded.items():
        if archive.getinfo(name).file_size != expected_size:
            raise ValueError("Artifact member size differs from manifest")
        with archive.open(name) as stream:
            actual_digest, actual_size = stream_digest(stream)
        if actual_size != expected_size or actual_digest != expected_digest:
            raise ValueError("Artifact member hash or size differs from manifest")
        total_member_bytes += actual_size
    return items, len(recorded), total_member_bytes


def extract_checked(archive, items, destination):
    """Extract only prechecked ordinary files into a fresh temporary directory."""
    destination = destination.resolve()
    for item in items:
        parts = safe_parts(item.filename, directory=item.is_dir())
        target = destination.joinpath(*parts)
        if not target.resolve().is_relative_to(destination):
            raise ValueError("Extraction would escape the temporary directory")
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)


def replay(archive_path):
    if not re.fullmatch(r"[0-9a-f]{64}", EXPECTED_SHA256):
        raise RuntimeError("Pin EXPECTED_SHA256 to the released artifact before running")
    with Path(archive_path).open("rb") as stream:
        archive_digest, archive_size = stream_digest(stream)
    if archive_digest != EXPECTED_SHA256:
        raise ValueError("Archive SHA256 differs from the released artifact")
    if EXPECTED_BYTES is not None and archive_size != EXPECTED_BYTES:
        raise ValueError("Archive size differs from the released artifact")

    with tempfile.TemporaryDirectory(prefix="sle-identity-growth-replay-") as temp:
        destination = Path(temp)
        with zipfile.ZipFile(archive_path) as archive:
            items, member_count, member_bytes = checked_members(archive)
            extract_checked(archive, items, destination)
        root = destination/ROOT_NAME
        verifier = root/"verify_results.py"
        if not verifier.is_file():
            raise ValueError("Archive contains no independent verifier")
        receipt_path = destination/"replay_verification_receipt.json"
        environment = os.environ.copy()
        for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
            environment[name] = "1"
        subprocess.run([sys.executable, str(verifier), "--root", str(root),
                        "--output", str(receipt_path)],
                       cwd=destination, env=environment, check=True)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("status") != "PASS" or receipt.get("failures") != []:
            raise ValueError("Independent saved-result verification did not pass")
        result = {"status": "PASS", "archive_sha256": archive_digest,
                  "archive_bytes": archive_size, "manifest_file_count": member_count,
                  "manifest_file_bytes": member_bytes,
                  "independent_verifier_counts": receipt["counts"],
                  "maximum_absolute_numeric_error": receipt["maximum_absolute_numeric_error"],
                  "new_training_runs": 0, "new_core_executions": 0,
                  "temporary_extraction_removed": True}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path, default=Path(ARCHIVE),
                        help="Path to the exact authorized research ZIP")
    args = parser.parse_args()
    result = replay(args.archive.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
