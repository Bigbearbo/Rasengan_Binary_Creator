#!/usr/bin/env python3
"""Public read-only R39 companion package verifier.
Needs the separately supplied R39 companion ZIP. Never downloads private data.
"""
import argparse, hashlib, pathlib, subprocess, sys, tempfile, zipfile
EXPECTED = '7fd8ccf20c9f442fef187f9ce6261aab08525c827e262411b250da5a347a6880'
parser = argparse.ArgumentParser()
parser.add_argument('archive', type=pathlib.Path)
a=parser.parse_args()
raw=a.archive.read_bytes()
assert hashlib.sha256(raw).hexdigest()==EXPECTED, 'R39 companion ZIP SHA mismatch'
with tempfile.TemporaryDirectory() as tmp:
    with zipfile.ZipFile(a.archive) as z:
        names=z.namelist()
        assert len(names)==161
        for name in names:
            path=pathlib.PurePosixPath(name)
            assert not path.is_absolute() and '..' not in path.parts, 'unsafe ZIP member'
        z.extractall(tmp)
    subprocess.run([sys.executable,'verify_r39_readonly.py'],cwd=tmp,check=True)
print('R39 verified against frozen artifact; this command never retrains')
