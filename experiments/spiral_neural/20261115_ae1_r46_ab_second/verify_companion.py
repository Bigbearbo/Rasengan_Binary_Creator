#!/usr/bin/env python3
"""Read-only R46 companion ZIP verification (Python stdlib; no neural replay)."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ZIP_SHA = "522bf4e495220ecbe030bb456c69d048dcd42b0677e4c5e43450bc81e887a5cc"
FIXED = {
    "r46_ab_second_route.py": "b10356f0161eebe12037b07c3bb7dc9ddce9b252b428641309bd8e77a2fba0b9",
    "r46_manifest.jsonl": "d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416",
    "r46_prereg.json": "de3f7f63300aa6ad3d550f43ed191abee1c0d526c13b0d1ad8438be40038f3d1",
    "r46_outputs/raw_results.jsonl": "09cc6f393fa7b69b8ddbd3f4fa7abb6a3ccf266c238d806a99c62502b4b57e04",
    "r46_outputs/results.json": "47e3c8bee9a9d0a4627155282ef1cbe48748c792f790f27a4f99d1ce95e184ff",
}
EXPECTED_SECOND = {
    "known_b18_19": (40,48),
    "removed_b20_23": (20,96),
    "new_taught_b24_25": (18,48),
    "reduced_b26_27": (32,48),
    "untrained_b28_29": (20,48),
}

def sha(x):
    return hashlib.sha256(x).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    assert sha(args.archive.read_bytes()) == ZIP_SHA, "ZIP SHA mismatch"
    with ZipFile(args.archive) as z:
        entries = set(z.namelist())
        root = "r45/"
        signed = z.read(root+"R46_SHA256SUMS").decode("utf-8").splitlines()
        n = 0
        for line in signed:
            if not line.strip():
                continue
            h, filename = line.split("  ",1)
            name = root+filename
            assert name in entries, ("missing", name)
            assert sha(z.read(name)) == h, ("SHA mismatch", name)
            n += 1
        assert n == 233, n
        for filename, h in FIXED.items():
            assert sha(z.read(root+filename)) == h, filename
        r = json.loads(z.read(root+"r46_outputs/results.json"))
        assert r["gate"] == "FAIL"
        assert sum(r["checks"].values()) == 1
        assert (r["updates"], r["train_target_presentations"], r["train_forward_dense_MAC"]) == (9900,633600,6918912000)
        assert (r["generated"], r["infer_forward_calls"], r["infer_dense_MAC"]) == (528,12375,135135000)
        for group, pair in EXPECTED_SECOND.items():
            p = r["comparisons"]["R46_a_b"][group]
            assert (p["second"],p["n"]) == pair, group
        rows = [json.loads(s) for s in z.read(root+"r46_outputs/raw_results.jsonl").splitlines()]
        assert len(rows) == 528
        assert all(len(x["Q"]) == 39 and set(x["Q"]) <= {"0","1"} for x in rows)
        assert all(x["seed"] in (101,202,303) and x["arm"] == "R46_ab_second" for x in rows)
        assert sum(x["exact"] for x in rows if x["split"] == "historical_retention") == 206
        assert sum(x["exact"] for x in rows if x["split"] != "historical_retention") == 0
    print(f"PASS: ZIP checksum, {n} file checksums, 528 actual answer receipts and prereg gates")
    print("This checks evidence integrity, not neural replay.")
    print("For PyTorch and independent NumPy replay, extract the ZIP and run:")
    print("python r46_ab_second_route.py replay")
    print("python r46_ab_second_route.py numpy")

if __name__ == "__main__":
    main()
