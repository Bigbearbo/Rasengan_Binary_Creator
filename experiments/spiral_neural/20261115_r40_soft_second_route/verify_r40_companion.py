#!/usr/bin/env python3
"""Verify the separate R40 reproducible research archive, without executing training."""
import argparse
import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile

EXPECTED_ZIP_SHA256 = "07a63dbc11b8b424574bd4c9973cea4e8d0f390638c99a620ec13407f6a73f84"
EXPECTED_COUNT = 171

def checksum(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                return h.hexdigest()
            h.update(chunk)

def verify(zip_path, replay):
    if checksum(zip_path) != EXPECTED_ZIP_SHA256:
        raise ValueError('companion ZIP SHA256 mismatch')
    with tempfile.TemporaryDirectory(prefix='r40_clean_') as name:
        root = pathlib.Path(name)
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.namelist()
            if len(members) != EXPECTED_COUNT or len(members) != len(set(members)):
                raise ValueError('companion archive count/duplicate mismatch')
            for member in members:
                p = pathlib.PurePosixPath(member)
                if p.is_absolute() or '..' in p.parts or '\\' in member:
                    raise ValueError('unsafe archive path')
            archive.extractall(root)
        lines = (root / 'SHA256SUMS_R40').read_text(encoding='utf8').splitlines()
        if len(lines) != EXPECTED_COUNT - 1:
            raise ValueError('expected 170 checksummed files')
        for line in lines:
            expected, relpath = line.split('  ', 1)
            p = root / relpath
            if not p.is_file() or checksum(p) != expected:
                raise ValueError(f'file checksum mismatch: {relpath}')
        print('R40 clean archive 170/170 SHA256 checks PASS')
        if replay:
            environment = dict(os.environ, OPENBLAS_NUM_THREADS='1',
                               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
            for action in ('gate', 'replay', 'numpy'):
                subprocess.run([sys.executable, 'r40_soft_route.py', action],
                               check=True, cwd=root, env=environment)
        print('R40 verification PASS')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=pathlib.Path)
    parser.add_argument('--replay', action='store_true', help='also require NumPy and PyTorch')
    a = parser.parse_args()
    verify(a.archive, a.replay)
