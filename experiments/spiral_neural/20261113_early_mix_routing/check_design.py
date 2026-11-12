"""Check one synthetic comparison and a routing-identifiability counterexample.

This is a non-neural design example, not a training preregistration or result.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

VALUES = (0, 1, 2, 3, 4, 7)


def question(op, value):
    return "01" + format(op, "02b") + "0" + format(value, "03b") + "0"


def answer(op, value):
    bits = format(value, "03b")
    return (bits if op == 0 else "".join("1" if bit == "0" else "0" for bit in bits)) + "0S"


def task_order(echo, neg, seed):
    order = [0] * echo + [1] * neg
    random.Random(seed).shuffle(order)
    return order


def lessons(order):
    seen = Counter()
    result = []
    for op in order:
        result.append((op, VALUES[seen[op] % len(VALUES)]))
        seen[op] += 1
    return result


def check():
    tail = task_order(600, 600, 733)
    early = lessons(task_order(600, 600, 731) + tail)
    late = lessons([0] * 300 + task_order(300, 600, 732) + tail)
    assert early[1200:] == late[1200:]
    assert Counter(early) == Counter(late) == Counter({(op, value): 200 for op in (0, 1) for value in VALUES})
    for op in (0, 1):
        assert [value for kind, value in early if kind == op] == [value for kind, value in late if kind == op]
    assert all(op == 0 for op, _ in late[:300]) and late[300:1200].count((1, 0)) == 100
    assert sum(op == 1 for op, _ in early[:300]) > 0
    # A flat exact-prefix table has no explicit per-task neural routing module.
    # It can still pass every valid finite-domain opcode contrast.
    lookup = {}
    for op in (0, 1):
        for value in range(8):
            q, a = question(op, value), answer(op, value)
            for position, target in enumerate(a):
                prefix = q + a[:position]
                assert prefix not in lookup or lookup[prefix] == target
                lookup[prefix] = target
    assert len(lookup) == 80
    for value in range(8):
        left, right = question(0, value), question(1, value)
        assert len(left) == len(right) == 9
        assert [i for i, (x, y) in enumerate(zip(left, right)) if x != y] == [3]
        assert lookup[left] != lookup[right]
        for op in (0, 1):
            q, a = question(op, value), answer(op, value)
            assert all(lookup[q + a[:position]] == target for position, target in enumerate(a))
    return {
        "status": "PASS", "scope": "Synthetic design checks only; not a neural experiment",
        "training_protocol_frozen": False,
        "example_schedule": {
            "lessons_each_condition": 2400, "Echo_each": 1200, "Neg_each": 1200,
            "presentations_per_operation_value": 200, "targets_each_condition": 12000,
            "same_full_multiset": True, "same_per_operation_data_order": True,
            "identical_final_mixed_lessons": 1200, "late_Echo_only_prefix_lessons": 300,
            "early_first_Neg_lesson_1based": next(i + 1 for i, row in enumerate(early) if row[0] == 1),
            "demo_task_order_seeds": [731, 732, 733]
        },
        "grammar": {"questions": 16, "unique_teacher_inputs": 80, "contradictory_labels": 0,
                    "legal_first_token_opcode_pairs": 8, "changed_raw_position_zero_based": 3},
        "mechanism_counterexample": {
            "flat_lookup_matches_all_80_oracle_targets": True,
            "flat_lookup_passes_all_8_first_token_opcode_pairs": True,
            "meaning": "Opcode-dependent correctness alone does not identify an explicit learned neural router",
            "later_position_limit": "Correct earlier answers differ across Echo and Neg; use empty A prefix for the clean opcode-only intervention"
        },
        "NN_forward_calls": 0, "optimizer_calls": 0, "new_students": 0,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = check()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
