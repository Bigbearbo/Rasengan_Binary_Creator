"""Independent mixed-continuation arithmetic/role checks; no checkpoint inference."""
from collections import Counter
import json
from pathlib import Path


def main():
    L, H = 80, 64
    labels = {name: Counter() for name in ("E1", "E2", "F1")}
    outputs = {}
    for a in range(30):
        for b in range(30):
            first, second = format(a, "05b") + "0", format(b, "05b") + "0"
            flip = "".join(str(1 - int(bit)) for bit in format(a, "05b")) + "0"
            for name, answer in (("E1", first), ("E2", first + second), ("F1", flip)):
                labels[name].update(answer + "S")
            if b == 0:
                outputs[a] = flip + "S"
    assert outputs[0] == "111110S" and outputs[1] == "111100S"
    totals = sum(labels.values(), Counter())
    assert dict(totals) == {"0": 12840, "1": 8760, "S": 2700}
    updates = 900 * (7 + 13 + 7)
    parameters = 2 * L * H + H + H * 3 + 3
    forward_mac, train_mac = H * (2 * L + 3), H * (4 * L + 9)
    assert (parameters, forward_mac, train_mac, updates) == (10499, 10432, 21056, 24300)
    result = {
        "status": "protocol_arithmetic_passed_code_gate_pending",
        "round_id": "AE1-MIXED-FLIP-20261113",
        "public_parent_result_commit": "7213cce112a8411b13dc128c49f9e88acfc9d65f",
        "computed": {
            "parameters": parameters,
            "forward_dense_MAC": forward_mac,
            "training_dense_MAC_per_target": train_mac,
            "class_targets_per_epoch": {"E1": 6300, "E2": 11700, "F1": 6300},
            "targets_per_epoch": updates,
            "training_MAC_per_epoch": updates * train_mac,
            "maximum_new_updates_per_seed": 40 * updates,
            "maximum_new_training_MAC_per_seed": 40 * updates * train_mac,
            "maximum_3primary_plus1replay_new_updates": 4 * 40 * updates,
            "maximum_3primary_plus1replay_new_training_MAC": 4 * 40 * updates * train_mac,
            "class_teacher_label_counts": {name: dict(counts) for name, counts in labels.items()},
            "mixed_teacher_label_counts": dict(totals),
            "literal_flip_answers_0_1": {str(value): outputs[value] for value in (0, 1)},
            "parent_t_starts": {"101": 151200, "202": 181800, "303": 223200},
        },
        "required_code_gates": [
            "Public parent result commit/archive/blob/member provenance and all3 full parent checkpoints must match exact pinned raw bytes; bundle all necessary inputs without private path dependencies.",
            "All3 primary baseline E1/E2 integrity gates pass before the first new optimizer call. Failure is an integration abort with0 new updates and no repair/reset/replacement.",
            "Baseline checks all2700 questions using only Q/generated bits. F1 baseline is diagnostic, baseline does not enter streak; only inference counters may change from exact parent state.",
            "Flip complements the first word's5 information bits and keeps tail0; literal output IDs30/31 are legal answer bits, never executed END/UP or filtered.",
            "E1/E2 raw Q/A remain bitidentical to the parent profile, while F1 uses new opcode100 under explicit mixed profile, not old numericZero/Neg semantics.",
            "Freeze40 full24300-target permutations from rng(seed+444000). Preserve global parent t/m/v/birth/RNG and bill only new training/baseline/probe/TF deltas.",
            "Stop only after two consecutive epoch-end900/900 exact+STOP in all3 classes or cap40. Only seed101 full replay includes its baseline and all new epochs; finalTF after all primary+planned replay only.",
        ],
        "interpretation_limits": [
            "Continuation of3 existing models on one fixed900-payload bank, not3 fresh students or new independent datasets.",
            "No additional control isolates Flip-specific causality from continued mixed practice; no unseen-bank, arbitrary-r or length claim.",
            "Equal class question counts imply unequal CE target counts6300/11700/6300; no length normalization.",
            "The before/after Flip score is a trained-domain diagnostic and cannot establish a general complement algorithm.",
        ],
        "reviewer_model_forward_calls": 0,
        "reviewer_optimizer_calls": 0,
        "formal_students": 0,
        "external_model_calls": 0,
    }
    with Path(__file__).with_name("protocol-review.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "computed": result["computed"], "NN_calls": 0}))


if __name__ == "__main__":
    main()
