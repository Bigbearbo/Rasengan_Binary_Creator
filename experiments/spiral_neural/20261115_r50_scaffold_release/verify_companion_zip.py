"""Read-only verification of a complete R50 companion ZIP, using stdlib only.

Usage: python verify_companion_zip.py /path/to/sle_ae1_r50_scaffold_release_20261115.zip

This does NOT execute a neural network. For full PyTorch/NumPy inference replay,
extract the ZIP and follow RESULTS_AND_HANDOFF.md.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ZIP_SHA256 = "0f41050c5b09ca46465995e8779fc1530c37c2ff7a6d5ad5a3b4df415a6981e1"
PREREG_SHA256 = "492a447a2629e9f358d4a9e87a3206ea861023dc182c20a9721a81372a13be8a"
MANIFEST_SHA256 = "ff2d3801b5e413bf977a9f9b2bfbf18b1a97e0a9f6b643f11e4d48c51af8478c"
RUNNER_SHA256 = "6514f7a99ffb7ccf5958e9a4b5cde8847685d4d489f38ac7b1b4a4fc81683dde"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(path: Path) -> None:
    archive_bytes = path.read_bytes()
    assert digest(archive_bytes) == ZIP_SHA256, "complete archive SHA256 mismatch"
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        assert bad is None, f"ZIP CRC mismatch: {bad}"
        receipts = json.loads(z.read("PACKAGE_SHA256.json"))
        names = {i.filename for i in z.infolist() if not i.is_dir()}
        assert names == set(receipts) | {"PACKAGE_SHA256.json"}, "missing/unlisted files"
        assert len(receipts) == 288, "unexpected file count"
        for name, expected in receipts.items():
            assert digest(z.read(name)) == expected, f"SHA mismatch: {name}"
        assert digest(z.read("r50_prereg.json")) == PREREG_SHA256
        assert digest(z.read("r50_manifest.jsonl")) == MANIFEST_SHA256
        assert digest(z.read("r50_scaffold_release.py")) == RUNNER_SHA256
        prereg = json.loads(z.read("r50_prereg.json"))
        assert prereg["manifest_sha256"] == MANIFEST_SHA256
        assert prereg["source_runner_sha256"] == RUNNER_SHA256
        result = json.loads(z.read("r50_outputs/results.json"))
        assert result["gate"] == "FAIL" and sum(result["checks"].values()) == 1
        assert result["updates"] == 9900 and result["target_presentations"] == 633600
        assert sum(s["n"] for s in result["groups"].values()) == 816
        for seed, expected in result["checkpoint_sha256"].items():
            assert digest(z.read(f"r50_outputs/weights_{seed}_dual.json")) == expected
        assert len(z.read("r50_outputs/raw_results.jsonl").splitlines()) == 816
        assert len(z.read("r50_outputs/fresh_baseline_posthoc.jsonl").splitlines()) == 576
    print("PASS: 288 file digests; 3 checkpoints; 816 new outputs; 576 frozen controls; joint gate FAIL 1/8.")
    print("For independent neural calculation, run the PyTorch and NumPy replay programs inside the ZIP.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("zip_path", type=Path)
    verify(ap.parse_args().zip_path)
