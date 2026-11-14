"""R37 companion integrity + count verification, Python stdlib only.
Does NOT run any neural model; use r37_b_role_highbit.py replay/numpy in ZIP.
"""
import hashlib, json, sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
sha = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
checks = [line.strip().split("  ", 1)
          for line in (root / "R37_SHA256SUMS").read_text().splitlines()]
for digest, path in checks:
    assert sha(path) == digest, f"corrupt: {path}"
spec = json.loads((root / "r37_prereg.json").read_text())
manifest = [json.loads(x) for x in (root / "r37_manifest.jsonl").read_text().splitlines()]
rows = [json.loads(x) for x in (root / "r37_outputs/raw_results.jsonl").read_text().splitlines()]
result = json.loads((root / "r37_outputs/results.json").read_text())
assert spec["source_sha256"]["r37_b_role_highbit.py"] == sha("r37_b_role_highbit.py")
assert len(manifest) == 16 and len(rows) == 192
assert result["gate"] == "FAIL" and result["generation_count"] == 192
assert result["raw_sha"] == sha("r37_outputs/raw_results.jsonl")
assert result["manifest_sha"] == sha("r37_manifest.jsonl")
assert set(r["arm"] for r in rows) == {"SS", "SB", "BS", "BB"}
for arm in ("SS", "SB", "BS", "BB"):
    subset = [r for r in rows if r["arm"] == arm]
    assert len(subset) == 48
    assert sum(r["control_second_correct"] for r in subset) == 48
    assert sum(r["second_correct"] for r in subset) == 0
    assert sum(r["second_onebit_response"] for r in subset) == 0
    assert sum(r["first_same_after_b_change"] for r in subset) == result["by_arm"][arm]["firstword_same_bflip"]
print("R37 PORTABLE INTEGRITY/COUNTS PASS:", len(checks),
      "SHA files,", len(rows),
      "stored NN outputs. Neural replay requires PyTorch/NumPy.")
