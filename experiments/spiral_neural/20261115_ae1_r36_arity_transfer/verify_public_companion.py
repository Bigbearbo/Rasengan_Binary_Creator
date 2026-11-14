#!/usr/bin/env python3
"""Read-only R36 companion integrity/aggregate checker; standard library only.

Usage after obtaining full R36 ZIP from the conversation:
  python verify_public_companion.py /path/to/extracted/R36-root
This script neither trains nor recomputes network outputs. For independent
inference check use 'python r36_arity_transfer.py replay' and '... numpy'
inside the companion.
"""
from __future__ import annotations
import collections
import hashlib
import json
import pathlib
import sys

EXPECTED = {
    "SS": (3, 4, 0, 48, 45),
    "SB": (2, 4, 3, 48, 40),
    "BS": (0, 0, 0, 48, 45),
    "BB": (5, 4, 0, 48, 40),
}
PREREG_SHA = "b2c8193da8cf427e55df1a004eaa4e3dabf50a79e80ea3c9460a1dccf97db571"
MANIFEST_SHA = "1ef9048f9a1b23e235dc2ea552d347f1c462d9c2c8b413710a3c0b7e66c708d4"
RUNNER_SHA = "870e86882e0654ebd2277643af1351e3f1a16fd3720fa51f0bd25543842bfa08"


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root: pathlib.Path) -> None:
    inventory = (root / "R36_SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(inventory) == 128, len(inventory)
    checked = set()
    for record in inventory:
        digest, rel = record.split("  ", 1)
        target = (root / rel).resolve()
        assert target.is_relative_to(root.resolve()), "unsafe archive inventory path"
        assert target.is_file() and sha(target) == digest, rel
        assert rel not in checked, rel
        checked.add(rel)
    for rel, digest in [
        ("r36_prereg.json", PREREG_SHA),
        ("r36_manifest.jsonl", MANIFEST_SHA),
        ("r36_arity_transfer.py", RUNNER_SHA),
    ]:
        assert sha(root / rel) == digest, rel
    rows = [
        json.loads(line)
        for line in (root / "r36_outputs/raw_results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 384, len(rows)
    byarm = collections.defaultdict(list)
    for row in rows:
        assert row["arm"] in EXPECTED
        assert row["r"] in (1, 2)
        assert row["seed"] in (101, 202, 303)
        assert row["a"] in (14, 15, 28, 29)
        assert row["b"] in (18, 19)
        assert row["c"] in (1, 3)
        assert row["d"] == 5
        assert len(row["Q"]) == 39
        assert set(row["Q"]) <= {"0", "1"}
        byarm[row["arm"]].append(row)
    summary = json.loads((root / "r36_outputs/results.json").read_text(encoding="utf-8"))
    assert summary["gate"] == "FAIL"
    for arm, expected in EXPECTED.items():
        records = byarm[arm]
        r1 = [x for x in records if x["r"] == 1]
        r2 = [x for x in records if x["r"] == 2]
        assert len(r1) == len(r2) == 48
        pair1 = {(x["seed"], x["pair_id"]): x for x in r1}
        pair2 = {(x["seed"], x["pair_id"]): x for x in r2}
        assert set(pair1) == set(pair2) and len(pair1) == 48
        got = (
            sum(x["first_correct"] for x in r1),
            sum(x["first_correct"] for x in r2),
            sum(x["exact"] for x in r2),
            sum(x["second_correct"] for x in r2),
            sum(pair1[k]["actual"][:6] == pair2[k]["actual"][:6] for k in pair1),
        )
        assert got == expected, (arm, got, expected)
        s = summary["by_arm"][arm]
        assert s["r1"]["first"] == got[0]
        assert s["r2"]["first"] == got[1]
        assert s["r2"]["exact"] == got[2]
        assert s["r2"]["second"] == got[3]
        assert s["paired_first_consistent"] == got[4]
    print("R36 companion PASS: 128 SHA256, 384 raw outputs, 4 arms, FAIL gate confirmed")
    print("This is an integrity/aggregate check, NOT new NN inference.")


if __name__ == "__main__":
    verify(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("."))
