"""Check the independently distributed R34 companion inventory, without retraining."""
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def checksum(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    inv=json.loads((ROOT/'R34_INVENTORY.json').read_text())
    for name, expected in inv['files'].items():
        p=ROOT/name
        assert p.is_file() and checksum(p)==expected, name
    assert len(inv['files'])>=100
    print('R34 INVENTORY PASS',len(inv['files']),'files')
if __name__=='__main__': main()
