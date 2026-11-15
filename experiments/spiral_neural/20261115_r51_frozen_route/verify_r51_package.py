"""Public R51 evidence verifier. Requires the complete conversation companion ZIP extracted.
No model inference here; run r51_frozen_r50_route.py replay/numpy for actual neural replays.
"""
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    receipt = json.loads((P / "PACKAGE_SHA256.json").read_text())
    found = {str(f.relative_to(P)) for f in P.rglob("*")
             if f.is_file() and "__pycache__" not in f.parts
             and f.name != "PACKAGE_SHA256.json"}
    assert found == set(receipt), (len(found), len(receipt), sorted(found ^ set(receipt))[:10])
    for rel, expected in receipt.items():
        assert sha(P / rel) == expected, (rel, expected)
    original = json.loads((P / "R50_PACKAGE_SHA256.json").read_text())
    assert len(original) == 288
    for rel, expected in original.items():
        assert sha(P / rel) == expected, ("IMMUTABLE_R50_SOURCE_CHANGED", rel)

    prereg = json.loads((P / "r51_prereg.json").read_text())
    assert sha(P / "r51_frozen_r50_route.py") == prereg["runner_sha256"]
    assert sha(P / "r50_outputs/raw_results.jsonl") == prereg["source"]["baseline_raw_sha256"]
    assert sha(P / "r50_manifest.jsonl") == prereg["source"]["r50_manifest_sha256"]
    for seed, digest in prereg["source"]["checkpoint_sha256"].items():
        assert sha(P / ("r50_outputs/weights_" + seed + "_dual.json")) == digest

    result = json.loads((P / "r51_outputs/summary.json").read_text())
    rows = [json.loads(line) for line in (P / "r51_outputs/raw_results.jsonl").read_text().splitlines()]
    assert len(rows) == 816 and len({(x["seed"], x["Q"]) for x in rows}) == 816
    assert sha(P / "r51_outputs/raw_results.jsonl") == result["raw_results_sha256"]
    assert result["gate"] == "PASS" and len(result["gates"]) == 5
    assert all(result["gates"].values())
    assert sum(z["actual"][:6] == z["before_actual"][:6] for z in rows) == 816
    f = result["groups"]["fresh_context"]
    l = result["groups"]["legacy"]
    h = result["groups"]["retention"]
    assert (f["second_before"], f["second_after"], f["full_before"], f["full_after"]) == (86,240,28,47)
    assert (l["second_before"], l["second_after"]) == (98,240)
    assert (h["full_before"], h["full_after"]) == (210,222)
    assert result["new_optimizer_updates"] == 0
    assert result["theoretical_dense_MAC"] == result["inference_forward_calls"] * 10920
    print("R51 integrity PASS", len(receipt), "files;", len(rows),
          "paired responses; neural replay is a separate check")

if __name__ == "__main__":
    main()
