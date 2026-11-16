"""R62 independent NumPy-only scorer for the separately archived full R62 ZIP.

Copy this script next to the extracted r62_manifest.jsonl, r62_prereg.json,
r62_frame_validity.py and r62_outputs/; then run with Python+NumPy.
No PyTorch and no teacher-model responses are used in this verifier.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
def sha(rel):
    return hashlib.sha256((P / rel).read_bytes()).hexdigest()

cfg = json.loads((P / "r62_prereg.json").read_text())
assert sha("r62_manifest.jsonl") == cfg["manifest_sha256"]
assert sha("r62_frame_validity.py") == cfg["runner_sha256"]
manifest = [json.loads(s) for s in (P / "r62_manifest.jsonl").read_text().splitlines()]
assert len(manifest) == 744
for row in manifest:
    q = "01" + "010" + f"{row['r']:03b}" + "0"
    q += "".join(f"{row[k]:05b}0" for k in "abcd") + "111100"
    assert len(q) == 39 and row["raw_bits"][2:] == q[2:]
    assert row["label"] == int(row["raw_bits"].startswith("01"))
    lo, hi = {"train": (0, 19), "validation": (20, 24), "test": (25, 29)}[row["split"]]
    assert all(lo <= row[k] <= hi for k in "abcd")
pred = [json.loads(s) for s in (P / "r62_outputs/raw_predictions.jsonl").read_text().splitlines()]
assert len(pred) == 2304
worst = 0.0
groups = {}
for seed in (101, 202, 303):
    for arm in ("raw_frame", "frame_blind"):
        records = [r for r in pred if r["seed"] == seed and r["arm"] == arm]
        assert len(records) == 384
        x = np.array([[2*int(v)-1 for v in r["raw_bits"]] for r in records], dtype=np.float32)
        if arm == "frame_blind":
            x[:, :2] = 0
        with np.load(P / f"r62_outputs/weights_{seed}_{arm}.npz") as m:
            out = (np.tanh(x @ m["w1"].T + m["b1"]) @ m["w2"].T + m["b2"]).ravel()
        err = max(abs(float(xi) - r["logit"]) for xi, r in zip(out, records))
        worst = max(worst, err)
        assert err < 0.00005, (seed, arm, err)
        for r in records:
            key = (seed, arm, r["split"], r["id"])
            groups.setdefault(key, {})[r["kind"]] = r["logit"]
assert len(groups) == 3*2*(32+64)
for (seed, arm, split, id_), logits in groups.items():
    assert len(logits) == 4
    if arm == "frame_blind":
        assert max(logits.values()) - min(logits.values()) <= 0.000001
print("R62 NumPy-only PASS: 744 source records, 2,304 replayed logits; max abs diff", worst)
