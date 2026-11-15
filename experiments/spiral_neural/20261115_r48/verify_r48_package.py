"""Public read-only ZIP hash checker; no neural training, no network or API keys."""
import hashlib, sys, zipfile
from pathlib import Path
SHA = 'abdb7cf4d616e635d9a16946b81d149d98906aa0cedfe28b779190ad4b49ec17'
assert len(sys.argv) == 2, 'usage: python verify_r48_github_public.py companion.zip'
p = Path(sys.argv[1])
assert hashlib.sha256(p.read_bytes()).hexdigest() == SHA, 'ZIP hash mismatch'
with zipfile.ZipFile(p) as z:
    names = z.namelist()
    assert len(names) == len(set(names)) and 'R48_SHA256SUMS' in names
    manifest = z.read('R48_SHA256SUMS').decode().splitlines()
    assert len(manifest) == 262
    for line in manifest:
        digest,name = line.split('  ',1)
        assert name in names and not name.startswith('/') and '..' not in Path(name).parts
        assert hashlib.sha256(z.read(name)).hexdigest() == digest, name
    assert len(names) == 263
print('R48 ZIP SHA256 and internal 262-file manifest PASS; neural replay not run')
