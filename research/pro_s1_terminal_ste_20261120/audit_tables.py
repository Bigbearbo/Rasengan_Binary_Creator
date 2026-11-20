"""Independent census of memory-one Boolean cells for the eight-step comparison task."""
import argparse
from collections import Counter
from itertools import product
import json
from pathlib import Path

import numpy as np


def gate(code, a, b, previous):
    return (code >> (4 * a + 2 * b + previous)) & 1


def truth_table(weights):
    wa, wb, wq, bias = weights
    return sum(1 << (4 * a + 2 * b + q) for a, b, q in product(range(2), repeat=3)
               if wa * a + wb * b + wq * q + bias >= 0)


def full_domain(code):
    # Multiplicity after a low-bit prefix, partitioned by predicted borrow, reference borrow
    # and whether any previous predicted step differed. Each next digit has four extensions.
    states = {(0, 0, False): 1}
    for _ in range(8):
        following = Counter()
        for (prediction, reference, error), count in states.items():
            for a, b in product(range(2), repeat=2):
                new_prediction = gate(code, a, b, prediction)
                new_reference = int(a < b) if a != b else reference
                following[new_prediction, new_reference,
                          error or new_prediction != new_reference] += count
        states = following
    assert sum(states.values()) == 65536
    tp = sum(n for (out, ref, _), n in states.items() if out == ref == 1)
    tn = sum(n for (out, ref, _), n in states.items() if out == ref == 0)
    return {"endpoint_correct": tp + tn, "sequence_correct": sum(n for (_, _, err), n in states.items() if not err),
            "true_positive": tp, "true_negative": tn}


def subset_scores(ids):
    a = np.array(ids, dtype=np.int32) // 256
    b = np.array(ids, dtype=np.int32) % 256
    codes = np.arange(256, dtype=np.int32)[:, None]
    q = np.zeros((256, len(ids)), dtype=np.int32)
    for k in range(8):
        indices = 4 * ((a >> k) & 1) + 2 * ((b >> k) & 1) + q
        q = (codes >> indices) & 1
    return (q == (a < b)).sum(axis=1)


def summary_of_tables(rows):
    return {metric: {"at_least_95": [r["code"] for r in rows if r[metric] * 100 >= 95 * 65536],
                     "perfect": [r["code"] for r in rows if r[metric] == 65536],
                     "best_imperfect_count": max(r[metric] for r in rows if r[metric] != 65536)}
            for metric in ("endpoint_correct", "sequence_correct")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("audit_tables.json"))
    parser.add_argument("--bench", type=Path, help="Optional independently generated experiment results")
    args = parser.parse_args()
    threshold_codes = {truth_table(w) for w in product(range(-2, 3), repeat=4)}
    gold = sum((1 << (4*a+2*b+q)) for a,b,q in product(range(2), repeat=3) if a < b+q)
    rows = [dict(code=code, integer_threshold_in_box=code in threshold_codes, **full_domain(code))
            for code in range(256)]
    subset = {}
    fits = []
    for seed in range(20261120, 20261136):
        ids = np.random.default_rng(seed).choice(65536, 64, replace=False)
        scores = subset_scores(ids)
        subset[seed] = (ids.tolist(), scores.tolist())
        satisfying = np.flatnonzero(scores == 64).tolist()
        fits.append({"seed": seed, "all_fits": satisfying, "fit_count": len(satisfying),
                     "fitting_threshold_codes": sorted(set(satisfying) & threshold_codes),
                     "threshold_fit_count": len(set(satisfying) & threshold_codes),
                     "true_rule_present": gold in satisfying, "uniquely_true": satisfying == [gold]})
    result = {"universe": 256, "depth": 8, "q0": 0, "gold_code": gold, "index": "4*A+2*B+q",
              "threshold_bounds_including_bias": [-2,2], "threshold_tables_in_box": len(threshold_codes),
              "legal_comparator_pairs": 65536, "all_table_summary": summary_of_tables(rows),
              "sample_fits": fits, "table_counts": rows}
    if args.bench is not None:
        bench = json.loads(args.bench.read_text(encoding="utf-8"))
        matched = 0
        primary_keys = ("endpoint_correct", "sequence_correct", "true_positive", "true_negative")
        for s, ids in zip(bench["seeds"], bench["ids_by_seed"], strict=True):
            assert ids == subset[s][0]
        for trials in bench["trials"].values():
            for record in trials:
                for name, obs in record.items():
                    if not isinstance(obs, dict) or "truth_table_code" not in obs:
                        continue
                    code = obs["truth_table_code"]
                    assert code == truth_table(obs["weights"]), (name, code, obs["weights"])
                    assert all(obs[k] == rows[code][k] for k in primary_keys), (name, code)
                    assert obs["train_endpoint_correct_of_64"] == subset[record["seed"]][1][code]
                    matched += 1
        result["crosscheck"] = {"score_records_matched": matched, "metrics": list(primary_keys),
                                "training_endpoints_and_ids_checked": True, "truth_tables_reconstructed_from_weights": True}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
