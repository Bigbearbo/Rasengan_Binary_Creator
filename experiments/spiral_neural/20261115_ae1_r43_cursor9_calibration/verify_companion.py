#!/usr/bin/env python3
"""R43 public read-only companion verifier (requires separate ChatGPT artifact ZIP).

Usage: python verify_companion.py /path/to/sle_ae1_r43_cursor9_calibration_20261115.zip

Git intentionally does NOT carry six checkpoints or the raw 480-pair results.
The ZIP has its own full hash manifest and independent neural replay verifier.
"""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ARCHIVE_SHA256 = "e2fecd9eaade65b454bb06ea8242fd3411b6b9dc505fee4612ad900578d64026"

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: python verify_companion.py /path/to/R43.zip")
    source=Path(sys.argv[1])
    assert source.is_file(),source
    assert digest(source)==ARCHIVE_SHA256, "ZIP SHA256 differs from R43 research receipt"
    with zipfile.ZipFile(source) as z:
        assert z.testzip() is None, "ZIP CRC failure"
        paths=[Path(item.filename) for item in z.infolist()]
        assert all(not p.is_absolute() and ".." not in p.parts and len(p.parts)>0 for p in paths)
        assert not any((item.external_attr >> 16) & 0o170000 == 0o120000 for item in z.infolist()),"symlinks forbidden"
        with tempfile.TemporaryDirectory(prefix="sle-r43-audit-") as scratch:
            z.extractall(scratch)
            script=Path(scratch)/"verify_r43_bundle.py"
            assert script.is_file()
            subprocess.run([sys.executable,str(script)],cwd=scratch,check=True)
    print("R43 public companion integrity and two NN replays PASS")

if __name__=="__main__":
    main()
