"""Validate an authorized archive and independently replay its saved results.

Requires Python 3.10+ and NumPy. Obtain the exact research archive from its
owner. This public entry point contains no private source or checkpoints.
Default replay recomputes data and the final channel. Optional full optimizer
recurrence audit is verification, not a new experimental training run.
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


ARCHIVE = "sle_retention_growth_20261118_v1.zip"
EXPECTED_SHA256 = '588c9d28b8e3e1ec61cec9a09ef31cb8b437f070678cf0d1ef5b55b7426acb14'
EXPECTED_BYTES = 407083289
VERIFIER_HASHES = {'verify_retention.py': '36b47b2582ba8822c18ec909edf0ce1406c79a71f786e866de629521cf240e94', 'verify_channel.py': 'b27ac87f5449c22b88301b76ae6fb4620b094915b9c28f9f593ca67fd62c9e03', 'prior_independent_helpers.py': 'c174a006716eb06dbf28ceffe01e91867c92ed6ac57bbd102192bf09089e38d2'}
ROOT_NAME = "retention_growth_20261118"
MANIFEST_NAME = "ARTIFACT_MANIFEST.json"
MAX_ARCHIVE_BYTES = 512*1024*1024
MAX_MEMBERS = 5000
MAX_TOTAL_UNCOMPRESSED_BYTES = 1024*1024*1024
MAX_MEMBER_BYTES = 128*1024*1024


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
    if len(items) > MAX_MEMBERS:
        raise ValueError("Archive exceeds the member-count limit")
    if sum(item.file_size for item in items) > MAX_TOTAL_UNCOMPRESSED_BYTES:
        raise ValueError("Archive exceeds the uncompressed-size limit")
    names, file_names, directory_names = set(), set(), set()
    for item in items:
        if item.file_size > MAX_MEMBER_BYTES:
            raise ValueError("Archive member exceeds the size limit")
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


def replay(archive_path, full_training=False):
    if not re.fullmatch(r"[0-9a-f]{64}", EXPECTED_SHA256):
        raise RuntimeError("Release archive hash has not been pinned")
    if Path(archive_path).stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds compressed-size limit")
    with Path(archive_path).open('rb') as stream:
        archive_digest, archive_size = stream_digest(stream)
    if archive_digest != EXPECTED_SHA256 or archive_size != EXPECTED_BYTES:
        raise ValueError("Archive identity differs from release")
    with tempfile.TemporaryDirectory(prefix='sle-retention-growth-replay-') as temp:
        destination=Path(temp)
        with zipfile.ZipFile(archive_path) as archive:
            items,count,size=checked_members(archive)
            extract_checked(archive,items,destination)
        root=destination/ROOT_NAME
        for name,wanted in VERIFIER_HASHES.items():
            with (root/name).open('rb') as stream:
                actual,_=stream_digest(stream)
            if actual!=wanted:raise ValueError('Verifier hash differs: '+name)
        env=os.environ.copy()
        for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):env[name]='1'
        first=destination/'data_or_training_receipt.json'
        phase='training' if full_training else 'preflight'
        command=[sys.executable,'-B',str(root/'verify_retention.py'),'--root',str(root),'--output',str(first)]
        if not full_training: command.append('--preflight-only')
        subprocess.run(command,cwd=destination,env=env,check=True,stdout=subprocess.PIPE)
        check=json.loads(first.read_text())
        if check.get('status')!='PASS' or check.get('replayed_optimizer_updates')!=(147456 if full_training else 0) or 'error' in check:raise ValueError('Data/training audit failed')
        second=destination/'channel_receipt.json'
        subprocess.run([sys.executable,'-B',str(root/'verify_channel.py'),'--root',str(root),'--directory',str(root/'channel_results'),'--output',str(second)],cwd=destination,env=env,check=True,stdout=subprocess.PIPE)
        channel=json.loads(second.read_text())
        if channel.get('status')!='PASS' or channel.get('channel_records')!=28800:raise ValueError('Final channel audit failed')
        prior=json.loads((root/'verification_training.json').read_text())
        if prior.get('status')!='PASS' or prior.get('replayed_optimizer_updates')!=147456:raise ValueError('Archived full training receipt absent')
        result={'status':'PASS','archive_sha256':archive_digest,'archive_bytes':archive_size,'manifest_file_count':count,'manifest_file_bytes':size,'mode':phase+'+final_channel','current_replayed_optimizer_updates':check['replayed_optimizer_updates'],'previous_full_audit_updates_in_pinned_receipt':prior['replayed_optimizer_updates'],'current_channel_records':channel['channel_records'],'current_wire_bytes':channel['wire_bytes'],'current_metric_groups':channel['groups'],'maximum_sender_logit_error':channel['maximum_sender_logit_error'],'maximum_receiver_logit_error':channel['maximum_receiver_logit_error'],'new_experimental_training_runs':0,'new_original_W_calls':0,'temporary_extraction_removed':True}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',nargs='?',type=Path,default=Path(ARCHIVE))
    parser.add_argument('--full-training',action='store_true',help='Also repeat all 147,456 independently implemented optimizer recurrences; does not modify released models.')
    args=parser.parse_args()
    print(json.dumps(replay(args.archive.resolve(),args.full_training),ensure_ascii=False,indent=2))


