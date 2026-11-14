#!/usr/bin/env python3
"""Read-only verification of the complete external R35 companion ZIP after extraction."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
expected = {
    "r35_output_only_codec.py": "3f617c46cf67bd641bb0919b01199689cb13954c15b2403da76d115b5440a0a6",
    "r35_prereg.json": "7174a5e646dee2f37666dae5415604322fa09bbad05e09b3f942f1e9d77a1535",
    "r35_train_manifest.jsonl": "ae94e8d7f4c730ce6b26451d57edd228a2ab3c93b664e84356b0905bb0897d72",
    "r35_test_manifest.jsonl": "02f04ba556c4c70e49122371d5ee61e0cc2f82dce171602b3e02a394b5782825",
    "r35_outputs/raw_results.jsonl": "51689353796bfc05052766458ccde4b0adc6f51a5c3b3a604ae74a5800e8c814",
    "r35_outputs/weights_101_SB.json": "153aa8807929f3886b95a4ea2daa78644146f1c1cc102c6a6fd74d590580c8a9",
    "r35_outputs/weights_202_SB.json": "4de0d51fe5551046ef03dcd7852352bd80758232f85316fd2fd2032d311be9e9",
    "r35_outputs/weights_303_SB.json": "310bfcdc999275b94db922c3c9bb63ab2ea7e5a5ed339d695c8148455ca1e389",
}
for file, digest in expected.items():
    assert hashlib.sha256((root / file).read_bytes()).hexdigest() == digest, file

rows = [json.loads(line) for line in (root / "r35_outputs/raw_results.jsonl").read_text().splitlines()]
assert len(rows) == 432
counts = Counter((r["seed"], r["split"]) for r in rows)
split_counts = {"validation_low": 8, "test_unseen_low": 32, "test_unseen_high": 16,
                "test_near": 32, "train_retention": 40, "test_stop": 16}
for seed in [101, 202, 303]:
    for split, count in split_counts.items():
        assert counts[seed, split] == count, (seed, split)
assert all(len(r["Q"]) == 39 and set(r["Q"]) <= {"0", "1"} for r in rows)
for split, first, exact in [
    ("test_unseen_low", 2, 2),
    ("test_unseen_high", 17, 17),
    ("train_retention", 120, 120),
]:
    part = [r for r in rows if r["split"] == split]
    assert sum(r["first_correct"] for r in part) == first
    assert sum(r["exact"] for r in part) == exact
assert sum(r["true_prefix_stop"] for r in rows if r["split"] == "test_stop") == 48
out = json.loads((root / "r35_outputs/results.json").read_text())
assert out["gate"] == "INCONCLUSIVE"
assert out["diff_SB_minus_SS"] == {
    "first_correct": -14, "exact": 4, "retention_exact": 0, "stop_true_prefix": 5,
}
print("PASS R35: 8 SHA256, 432 raw NN responses, 3 seeds, precommitted INCONCLUSIVE gate")
