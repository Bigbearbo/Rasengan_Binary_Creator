"""Re-score every width-7/8 metadata layout from contiguous bus regions, scalar only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def reference_runs(labels):
    lengths = []
    prev = None
    for group in labels:
        if group != prev:
            lengths.append(1)
        else:
            lengths[-1] += 1
        prev = group
    return lengths


def counts(m, w):
    valid = optimal = matches = total = 0
    hist = Counter()
    for a in range(1 << w):
        for b in range(1 << w):
            label = [((a >> p) & 1, (b >> p) & 1) for p in range(w)]
            runs = reference_runs(label)
            min_rounds = sum((n + 1) // 2 for n in runs)
            demonstration = []
            for n in runs:
                demonstration.extend([2] * (n // 2))
                demonstration.extend([1] * (n % 2))
            p = 0
            trace = []
            while p <= w:
                lo = label[p] if p < w else (0, 0)
                hi = label[p + 1] if p + 1 < w else (0, 0)
                key = int(f"{lo[0]}{hi[0]}{lo[1]}{hi[1]}", 2)
                remaining = w - p
                if remaining <= m["s"]:
                    if p == w:
                        valid += 1
                        optimal += (len(trace) == min_rounds)
                        matches += trace == demonstration
                        total += len(trace)
                        hist[str(len(trace))] += 1
                    break
                move = 2 if remaining >= m["k"] and m["table"][key] else 1
                if move > remaining or (move == 2 and lo != hi):
                    break
                p += move
                trace.append(move)
    return {"episodes": 4 ** w, "legal_correct_stop": valid, "minimum_rounds": optimal,
            "matches_greedy": matches, "sum_successful_rounds": total,
            "round_histogram_successful": dict(sorted(hist.items()))}


def main(source, output):
    j = json.loads(source.read_text())
    models = {}
    for t in j["trials"]:
        for a, m in t["models"].items():
            ident = str(t["model_ids"][a])
            assert ident not in models or models[ident] == m
            models[ident] = m
    audited = {}
    for w in [7, 8]:
        scores = j["test_scores_by_model_id"][f"layouts_exhaustive_{w}"]
        audited[str(w)] = {}
        for ident, m in models.items():
            got = counts(m, w)
            assert got == scores[ident], (ident, got, scores[ident])
            audited[str(w)][ident] = got
    out = {"method": "Scalar independent bank runs, optimum = sum ceiling(region length / 2)",
           "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "counts": audited, "all_registered_models_match": True}
    output.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("--output", type=Path, default=Path("checked.json"))
    a = p.parse_args()
    main(a.source, a.output)
