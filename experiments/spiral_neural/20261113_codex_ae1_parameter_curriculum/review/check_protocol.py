"""Independent curriculum arithmetic and finite-bank interpretation; zero NN calls."""
from collections import Counter
import json
from pathlib import Path


def main():
    L, H, N, word_bits = 80, 64, 4, 6
    q_length = 2 + 3 + 4 + N * word_bits + word_bits
    targets = {r: word_bits * r + 1 for r in (1, 2)}
    parameters = 2 * L * H + H + H * 3 + 3
    forward_mac = H * (2 * L + 3)
    train_mac = H * (4 * L + 9)
    stage1_targets, stage2_targets = 900 * targets[1], 900 * (targets[1] + targets[2])
    max_updates = 40 * (stage1_targets + stage2_targets)
    labels = {1: Counter(), 2: Counter()}
    for a in range(30):
        for b in range(30):
            words = (format(a, "05b") + "0", format(b, "05b") + "0")
            for r in (1, 2):
                labels[r].update("".join(words[:r]) + "S")
    assert q_length == 39 and targets == {1: 7, 2: 13}
    assert (parameters, forward_mac, train_mac) == (10499, 10432, 21056)
    assert (stage1_targets, stage2_targets, max_updates) == (6300, 18000, 972000)
    assert dict(labels[1]) == {"0": 3270, "S": 900, "1": 2130}
    assert dict(labels[1] + labels[2]) == {"0": 9810, "S": 1800, "1": 6390}
    result = {
        "status": "protocol_arithmetic_passed_code_gate_pending",
        "round_id": "AE1-PARAMETER-EXEC-20261113",
        "computed": {
            "Q_length": q_length,
            "target_actions_r1_r2_including_STOP": targets,
            "last_STOP_teacher_prefix_r1_r2": {r: q_length + word_bits * r for r in (1, 2)},
            "parameters": parameters,
            "forward_dense_MAC": forward_mac,
            "training_dense_MAC_per_target": train_mac,
            "stage1_targets_per_epoch": stage1_targets,
            "stage2_targets_per_epoch": stage2_targets,
            "stage1_MAC_per_epoch": stage1_targets * train_mac,
            "stage2_MAC_per_epoch": stage2_targets * train_mac,
            "maximum_updates_per_seed": max_updates,
            "maximum_training_MAC_per_seed": max_updates * train_mac,
            "maximum_3primary_plus1replay_updates": max_updates * 4,
            "maximum_3primary_plus1replay_training_MAC": max_updates * train_mac * 4,
            "p_m_v_birth_array_bytes": parameters * 20,
            "stage1_teacher_label_counts": dict(labels[1]),
            "stage2_teacher_label_counts": dict(labels[1] + labels[2]),
        },
        "required_code_checks": [
            "One fixed900 bank has all ordered first pairs0..29 and exactly one rng331000 suffix pair each; same payloads under r1/r2, no END as an ordinary word.",
            "All40 epoch target permutations per stage/seed are frozen before scores; each stage2 epoch has6300 r1 and11700 r2 targets, without question-level reweighting.",
            "Stage2 advances only after two consecutive exact full-stage1 generations, preserves p/m/v/birth/t/RNG/counters, and records every nonadvancing seed rather than dropping it.",
            "Free generation uses only Q and generated prefixes with a fixed cap at least13; no r-dependent true-length cutoff or forcedSTOP.",
            "Stage2 stopping requires all900 r1 and900 r2 exact includingSTOP twice consecutively; final TF covers only actually taught tasks.",
            "Only predetermined seed101 receives a full replay independently reproducing stage branches and stops; other seeds remain explicitly not replayed.",
        ],
        "interpretation_limits": [
            "This is a finite fixed-bank fit and retention curriculum, with no heldout, r3/r4 or length extrapolation evidence.",
            "All ordered first pairs do not cover30^4 payloads: only one suffix pair is sampled for each first pair.",
            "A single sequential curriculum without a joint-training control cannot isolate a curriculum benefit.",
            "Stage2 equal question counts do not imply equal optimization weight: r1/r2 contribute6300/11700 CE targets.",
            "A fixed finite r1/r2 bank cannot distinguish lookup from a general count-controlled copying algorithm.",
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
