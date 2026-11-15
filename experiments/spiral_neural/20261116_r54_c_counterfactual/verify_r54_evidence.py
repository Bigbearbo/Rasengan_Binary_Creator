#!/usr/bin/env python3
"""R54 public read-only evidence gate. Needs R54 portable archive extracted locally.

This script does not recompute NN inference on its own: the archive contains
full checkpoint state and two independent neural replay programs. This script
checks SHA256, legal SLE Q, paired causality, exact F/T result counters,
preregistered gate, and the documented output/gate provenance.
No external network, training or teacher oracle is used.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

EXPECTED = {
 "R54_PACKAGE_SHA256.json": None,
 "r54_manifest.jsonl": "88ddd8ac2e390e735be907f0f797b23620ac5800b2df753b613638e3a30c809c",
 "r54_prereg.json": "36a229d85da023306cfa0dbd83e1896be6968690c12595d2eaf73d82faea98ad",
 "r54_legal_c_counterfactual.py": "17463cbe947454592317ef26dc2d920da4e8353fffde9f2fcd87905d46fc7a03",
 "r54_outputs/raw_results.jsonl": "25b833007f58ef59da32abbedce6684f403c8703b2dc4c7d96745f8bc3817f2b",
}
SEEDS = (101, 202, 303)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def word(v):
    assert type(v) is int and 0 <= v <= 29
    return f"{v:05b}0"

def question(rec):
    return ("01" + "010" + f"{rec['r']:03b}0" +
            "".join(word(rec[k]) for k in "abcd") + "111100")

def answer(rec):
    return word(rec["a"]) + (word(rec["b"]) if rec["r"] == 2 else "") + "S"

def readjl(f):
    return [json.loads(line) for line in f.read_text().splitlines()]

def verify(root):
    expected_archive = root / "R54_PACKAGE_SHA256.json"
    audit = json.loads(expected_archive.read_text())
    assert len(audit) == 325, len(audit)
    for filename, digest in audit.items():
        assert sha(root / filename) == digest, ("archive drift", filename)
    for filename,digest in EXPECTED.items():
        if digest:
            assert sha(root / filename) == digest, ("preregistered drift", filename)

    prereg = json.loads((root / "r54_prereg.json").read_text())
    assert prereg["trainable_updates"] == 0
    assert prereg["source_git_parent_sha"] == "1165204c1425ce084e049725781468c7b10df66d"
    manifest = readjl(root / "r54_manifest.jsonl")
    pairs = collections.defaultdict(list)
    assert len(manifest) == 96
    for rec in manifest:
        assert len(rec["Q"]) == 39 and set(rec["Q"]) <= set("01")
        assert rec["r"] in (1,2)
        assert rec["Q"] == question(rec)
        assert rec["expected"] == answer(rec)
        pairs[rec["pair"]].append(rec)
    assert len(pairs) == 48
    assert len({x["Q"] for x in manifest}) == 96
    for pair in pairs.values():
        assert len(pair) == 2
        left,right = pair
        assert left["c"] == 0 and 1 <= right["c"] <= 29
        assert left["d"] == right["d"] == 0
        assert all(left[key] == right[key] for key in ("r","a","b","expected","split"))
    results = readjl(root / "r54_outputs/raw_results.jsonl")
    assert len(results) == 576
    by_key = {(z["arm"],z["seed"],z["pair"],z["variant"]):z for z in results}
    assert len(by_key) == len(results)
    counts = collections.Counter()
    for arm in ("R52","R53"):
        for seed in SEEDS:
            for pairid in pairs:
                a = by_key[(arm,seed,pairid,"c0")]
                b = by_key[(arm,seed,pairid,"c_alternative")]
                counts[arm,"initial_logit_change"] += a["initial_logits"] != b["initial_logits"]
                counts[arm,"free_firstword_change"] += a["actual"][:6] != b["actual"][:6]
                counts[arm,"full_correctness_discordance"] += a["exact"] != b["exact"]
                for row in (a,b):
                    assert row["Q"] in {p["Q"] for p in pairs[pairid]}
                    assert row["exact"] == (row["actual"] == row["expected"])
                    counts[arm,"full_correct"] += row["exact"]
    assert counts["R52","initial_logit_change"] == 144
    assert counts["R53","initial_logit_change"] == 0
    assert counts["R52","free_firstword_change"] == 50
    assert counts["R53","free_firstword_change"] == 0
    assert counts["R52","full_correctness_discordance"] == 40
    assert counts["R53","full_correctness_discordance"] == 2
    assert counts["R52","full_correct"] == 192
    assert counts["R53","full_correct"] == 126
    summary = json.loads((root / "r54_outputs/results.json").read_text())
    assert summary["joint_gate"] == "PASS"
    assert all(summary["gates"].values())
    assert summary["actual_forwards"] == 6336
    assert summary["numpy_replay"]["count"] == 576
    assert summary["numpy_replay"]["max_abs_logit_error"] <= 1e-5
    print("R54 PUBLIC READ-ONLY CHECK PASS; 325 SHA files, 96 legal raw Q, 576 stored responses")
    print("R52: firstword c-sensitivity 50/144; R53 hard-mask control 0/144")
    print("Note: actual neural verification is a *separate* check. In the archive run:")
    print("  python r54_verify_erratum.py verify")
    print("  python r54_verify_erratum.py numpy")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_root", type=Path, help="extracted r54_workspace directory")
    verify(parser.parse_args().archive_root)
