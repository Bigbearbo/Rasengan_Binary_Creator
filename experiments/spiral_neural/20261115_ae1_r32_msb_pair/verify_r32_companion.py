"""Verify R32 conversation companion ZIP and replay actual fixed NN checkpoints.

Usage: python verify_r32_companion.py /path/to/sle_ae1_r32_msb_pair_20261115.zip
Requires numpy and torch CPU; no new training or external services.
"""
from pathlib import Path
from hashlib import sha256
import argparse, tempfile, subprocess, sys, zipfile

EXPECTED = "ec33f5e4d88dce73f98773a3bc19263cc343025754e35180d2c99363f200c802"
ROOT = "sle_ae1_r32_msb_pair_20261115"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("companion_zip",type=Path)
    args = ap.parse_args()
    digest = sha256(args.companion_zip.read_bytes()).hexdigest()
    assert digest == EXPECTED, ("companion ZIP SHA256 mismatch", digest)
    with tempfile.TemporaryDirectory(prefix="r32-verification-") as td:
        dest = Path(td)
        with zipfile.ZipFile(args.companion_zip) as z:
            for entry in z.infolist():
                path = dest / entry.filename
                assert path.resolve().is_relative_to(dest.resolve()), ("unsafe path", entry.filename)
            z.extractall(dest)
        runner = dest/ROOT/"verify_package.py"
        assert runner.is_file(), "package verifier missing"
        subprocess.run([sys.executable,str(runner)],cwd=runner.parent,check=True)
    print("R32 immutable companion verification PASS")

if __name__ == "__main__":
    main()
