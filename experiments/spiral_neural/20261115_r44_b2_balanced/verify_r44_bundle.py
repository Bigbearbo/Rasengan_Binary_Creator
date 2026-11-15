"""R44 companion evidence ZIP verifier (Python 3; torch/numpy for --replay).
Run from extracted sle_ae1_r44_b2_balanced_curriculum_20261115.zip folder.
Reads public source and checkpoint files; does not train, download, or write.
Git does NOT contain all weights: obtain the companion ZIP separately.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    ledger = json.loads((ROOT / "r44_package_manifest.json").read_text())
    for name, checksum in ledger["sha256"].items():
        filename = ROOT / name
        assert filename.is_file() and sha(filename) == checksum, name
    print("R44 PACKAGE SHA PASS", len(ledger["sha256"]))
    prereg = json.loads((ROOT / "r44_prereg.json").read_text())
    result = json.loads((ROOT / "r44_outputs/results.json").read_text())
    assert sha(ROOT / "r44_prereg.json") == "57b306d62fa7a804fc5229afb9ba54d6a088c4a07ce20c5f2030204a3ce3cdd5"
    assert sha(ROOT / "r44_manifest.jsonl") == "d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416"
    assert sha(ROOT / "r44_b2_balanced_curriculum.py") == prereg["runner_SHA256"]
    assert sha(ROOT / "r44_outputs/raw_results.jsonl") == result["raw_results_SHA256"]
    assert result["gate"] == "PASS" and len(result["checks"]) == 5
    assert all(result["checks"].values())
    print("R44 PREREG+RESULTS CONSISTENCY PASS", result["gate"])
    if "--replay" in sys.argv:
        for command, source in (("gate", "r44_b2_balanced_curriculum.py"),
                                ("replay", "r44_posthoc_evaluation.py"),
                                ("numpy", "r44_posthoc_evaluation.py")):
            subprocess.run([sys.executable, "-B", str(ROOT / source), command],
                           cwd=ROOT, check=True)
        print("R44 COMPLETE NEURAL REPLAY PASS")

if __name__ == "__main__":
    main()
