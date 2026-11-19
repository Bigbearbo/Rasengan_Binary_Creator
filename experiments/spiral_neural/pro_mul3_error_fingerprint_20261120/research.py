"""Census of seven decoded-answer rules for 3*x on seven-bit inputs."""
import argparse
import csv
import itertools
import json
from pathlib import Path


def predictions(x):
    if type(x) is not int or not 0 <= x < 128:
        raise ValueError("Expected an integer in 0..127")
    y = 2 * x
    propagate = x ^ y
    generated = x & y
    return {
        "true_mul3": x + y,
        "double": y,
        "xor": propagate,
        "or": x | y,
        "one_carry": propagate ^ (generated << 1),
        "trunc7": (x + y) % 128,
        "trunc8": (x + y) % 256,
    }


def column_reference(x):
    """Compute the same reference answers from individual binary columns."""
    vals = {name: 0 for name in predictions(0)}
    carry = generated_last = 0
    for i in range(9):
        a = (x >> i) & 1
        b = ((x >> (i - 1)) & 1) if i else 0
        s = a + b + carry
        bit = s % 2
        columns = {
            "true_mul3": bit, "double": b, "xor": (a + b) % 2,
            "or": int(a + b > 0), "one_carry": (a + b + generated_last) % 2,
            "trunc7": bit if i < 7 else 0, "trunc8": bit if i < 8 else 0,
        }
        for name, v in columns.items():
            vals[name] += v << i
        carry, generated_last = s // 2, a * b
    assert not carry
    return vals


def pair_distances(rows, panel, correct_only=False):
    pairs = {}
    for a, b in itertools.combinations(rows[0], 2):
        count = 0
        for x in panel:
            u, v = rows[x][a], rows[x][b]
            if correct_only:
                u, v = u == 3*x, v == 3*x
            count += u != v
        pairs[(a, b)] = count
    return pairs


def run(out):
    rows = [predictions(x) for x in range(128)]
    assert all(row == column_reference(x) for x, row in enumerate(rows))
    inputs = range(128)
    for x, row in enumerate(rows):
        assert row["true_mul3"] == 3*x
        assert (3*x == row["xor"]) == (3*x == row["or"]) == ((x & (2*x)) == 0)
    exact = {k: sum(rows[x][k] == 3*x for x in inputs) for k in rows[0]}
    current = pair_distances(rows, inputs)
    flags = pair_distances(rows, inputs, correct_only=True)
    shortest = next(p for n in (1, 2) for p in itertools.combinations(inputs, n)
                    if min(pair_distances(rows, p).values()) >= 1)

    # In each interval one truncation pair necessarily coincides. Keep every
    # row that attains six distinct outputs, and take the first three.
    middle = [x for x in inputs if 128 <= 3*x < 256 and len(set(rows[x].values())) == 6]
    upper = [x for x in inputs if 256 <= 3*x and len(set(rows[x].values())) == 6]
    robust = middle[:3] + upper[:3]
    assert len(robust) == 6 and min(pair_distances(rows, robust).values()) == 3
    assert len(shortest) == 2
    # Verify decoding for each one-word corruption using all seven outputs at
    # that input, plus a representative outside the set of possible outputs.
    codebook = {k: tuple(rows[x][k] for x in robust) for k in rows[0]}
    checked = 0
    for k, code in codebook.items():
        for j, x in enumerate(robust):
            for wrong in set(rows[x].values()) | {-1}:
                observed = code[:j] + (wrong,) + code[j+1:]
                matches = [name for name, words in codebook.items()
                           if sum(a != b for a, b in zip(observed, words)) <= 1]
                assert matches == [k]
                checked += 1
    out.mkdir(parents=True, exist_ok=True)
    with (out/"census.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["x", "has_carry", *rows[0]], lineterminator="\n")
        writer.writeheader()
        for x, row in enumerate(rows):
            writer.writerow({"x": x, "has_carry": int(bool(x & (2*x))), **row})
    with (out/"pair_distances.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["rule_a","rule_b","different_answers","different_correctness"])
        for (a,b), num in current.items():
            writer.writerow([a,b,num,flags[a,b]])
    summary = {
        "scope":"synthetic integer rules; no neural model evaluated",
        "inputs":len(rows), "no_carry":exact["xor"], "has_carry":128-exact["xor"],
        "correct_per_rule":exact,
        "same_correctness": [list(pair) for pair,count in flags.items() if not count],
        "shortest_panel":list(shortest), "shortest_panel_outputs":[rows[x] for x in shortest],
        "robust_panel":robust, "robust_panel_min_distance":3,
        "eligible_middle_upper":[len(middle),len(upper)], "corruption_checks":checked,
        "symmetric_difference_with_xor_on_held":{"random_order":(9-5)+4,"low_carry_first":(9-2)+0},
    }
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("results"))
    print(json.dumps(run(parser.parse_args().out),indent=2))
