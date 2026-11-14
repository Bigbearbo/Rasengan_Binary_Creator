"""Verify the externally delivered AE1-R14 companion ZIP, not a Git-only checkpoint replay.
Usage: python VERIFY_COMPANION.py /path/to/sle_ae1_balanced_highbits_20261114_r14.zip
Requires NumPy and PyTorch (for static gate only). Does not train students.
"""
from pathlib import Path
from hashlib import sha256
import sys, zipfile, tempfile, subprocess
ARCHIVE_SHA256 = "ec431291aef5e913690d4f0303d94cd3b5768ace73d86f98902cdddebb5eb0d3"
ROOT = "sle_ae1_balanced_highbits_r14"
def main():
    assert len(sys.argv)==2, "provide the explicit companion ZIP path"
    zpath=Path(sys.argv[1])
    assert zpath.is_file(), zpath
    assert sha256(zpath.read_bytes()).hexdigest()==ARCHIVE_SHA256, "archive SHA mismatch"
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zpath) as z:
            assert all(n.startswith(ROOT+"/") for n in z.namelist()), "unexpected archive member"
            assert all(".." not in Path(n).parts for n in z.namelist()), "unsafe archive path"
            z.extractall(tmp)
        folder=Path(tmp)/ROOT
        for line in (folder/"SHA256SUMS.txt").read_text().splitlines():
            digest, relative = line.split("  ",1)
            assert sha256((folder/relative).read_bytes()).hexdigest()==digest, relative
        for cmd in ([sys.executable,"train_r14.py","gate"],
                    [sys.executable,"verify_numpy_r14.py"]):
            result=subprocess.run(cmd,cwd=folder,check=True,text=True,capture_output=True)
            print(result.stdout)
        print("PASS: archive SHA, member SHA, prereg gate, independent 1584-answer replay; zero training updates")
if __name__=="__main__":
    main()
