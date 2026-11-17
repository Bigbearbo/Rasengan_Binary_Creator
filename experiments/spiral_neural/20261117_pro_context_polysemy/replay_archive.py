"""Verify the exact archived study, then replay saved results without retraining.

The original Fable source and weights are intentionally not published in Git.
Obtain the authorized research archive from its owner, then run this entry point.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ARCHIVE = 'sle_context_polysemy_controls_20261117_v1.zip'
EXPECTED_SHA256 = 'f46557d9a22810c6cf6de5b2bce2e6516dab0c709e8672a7dd3d1a97bc7f891f'
EXPECTED_BYTES = 2042247


def replay(archive: Path, destination: Path, train: bool):
    if archive.stat().st_size != EXPECTED_BYTES:
        raise ValueError('Archive size differs from the recorded artifact')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Archive SHA256 differs from the recorded artifact')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failed')
        for item in z.infolist():
            path = (destination/item.filename).resolve()
            if not path.is_relative_to(destination.resolve()):
                raise ValueError('Unsafe archive path')
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unexpected symbolic link in artifact')
        z.extractall(destination)
    root = destination/'context_polysemy_20261117'
    manifest = json.loads((root/'ARTIFACT_MANIFEST.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        p = root/item['path']
        if p.stat().st_size != item['size_bytes'] or hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Artifact member mismatch: {item["path"]}')
    env = os.environ.copy()
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
        env[key] = '1'
    subprocess.run([sys.executable,'verify_results.py'],cwd=root,env=env,check=True)
    if train:
        subprocess.run([sys.executable,'run_study.py','--output',str(root/'retrained_results')],cwd=root,env=env,check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',nargs='?',type=Path,default=Path(ARCHIVE))
    p.add_argument('--train',action='store_true',help='Explicitly rerun the fixed training protocol after verification')
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix='sle-context-replay-') as tmp:
        replay(args.archive.resolve(),Path(tmp),args.train)
    print('Verified archive and saved-result replay; temporary extraction removed.')


if __name__=='__main__':
    main()
