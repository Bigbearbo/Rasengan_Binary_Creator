"""Exploratory test of recovering two broken cutoffs in addition to the wide-move map."""
import argparse
import json
from pathlib import Path

from stride import FINE, model, scores, signature, test_sets, train, training


def main(primary_path, output_path):
    primary = json.loads(primary_path.read_text())
    initial = model(-1, 3, FINE["table"])
    records = []
    models = {}
    for row in primary["trials"]:
        fit, trajectory, queries = train(training(row["seed"]), "EC", initial)
        sig = signature(fit)
        if sig not in models:
            models[sig] = len(models)
        records.append({"seed": row["seed"], "readout": fit, "id": models[sig],
                        "accepted": trajectory, "objective_queries": queries})
    test = {}
    ablate = {}
    for label, data in test_sets():
        test[label] = {str(i): scores(data, model(s[0], s[1], s[2:])) for s, i in models.items()}
        if label == 'layouts_exhaustive_8':
            # All 16 main EC students have the same readout (verified against source JSON).
            fits = [r["models"]["EC"] for r in primary["trials"]]
            assert all(m == fits[0] for m in fits)
            fit = fits[0]
            ablate = {"original": scores(data, fit),
                      "s_negative_one": scores(data, model(-1, fit["k"], fit["table"])),
                      "k_three": scores(data, model(fit["s"], 3, fit["table"]))}
    out = {"stage": "exploration after observing primary results",
           "init": initial, "trained": records, "test_scores": test,
           "ablate_primary_no_further_training": ablate}
    output_path.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("primary", type=Path)
    parser.add_argument("--output", default=Path("recovery.json"), type=Path)
    args = parser.parse_args()
    main(args.primary, args.output)
