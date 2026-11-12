#!/usr/bin/env python3
"""Execute bounded AE1 specification checks; stdlib only, no model inference."""

import hashlib
import itertools
import json
import platform
import sys
from pathlib import Path

import codec


HERE = Path(__file__).resolve().parent
BASE_HEAD = "365c5fbf3324d3decb625f9d04ddd1bc91af4d93"

# Literal reference words and raw examples are independent of codec.encode.
WORDS = (
    "000000", "000010", "000100", "000110", "001000", "001010",
    "001100", "001110", "010000", "010010", "010100", "010110",
    "011000", "011010", "011100", "011110", "100000", "100010",
    "100100", "100110", "101000", "101010", "101100", "101110",
    "110000", "110010", "110100", "110110", "111000", "111010",
)
COUNTS = {1: "0010", 2: "0100", 3: "0110", 4: "1000"}
RAW_FIXTURES = (
    (1, "010100010000010001100010110100010111100", "000010"),
    (2, "010100100000010001100010110100010111100", "000010001100"),
    (3, "010100110000010001100010110100010111100", "000010001100010110"),
    (4, "010101000000010001100010110100010111100", "000010001100010110100010"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def reject(name: str, expected: str, fn) -> dict:
    try:
        fn()
    except codec.CodecError as exc:
        require(exc.code == expected, f"{name}: expected {expected}, got {exc.code}")
        return {"name": name, "rejected": True, "code": exc.code}
    raise RuntimeError(f"{name}: invalid input was accepted")


def oracle_q(values: tuple[int, ...], r: int) -> str:
    return "01010" + COUNTS[r] + "".join(WORDS[v] for v in values) + "111100"


def check_case(q: str, values: tuple[int, ...], r: int, expected_a: str) -> None:
    decoded = codec.decode(q, profile=codec.PROFILE)
    require(decoded.payload == values and decoded.r == r, "decoded meaning mismatch")
    require(codec.encode(values, r, profile=codec.PROFILE) == q, "encoded raw mismatch")
    require(codec.answer(q, profile=codec.PROFILE) == expected_a, "answer mismatch")


def main() -> None:
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python -B check_design.py")

    for r, q, a in RAW_FIXTURES:
        check_case(q, (1, 6, 11, 17), r, a)
        require(len(q) == 39 and len(a) == 6 * r, "literal fixture lengths")
    rows = codec.fixtures(profile=codec.PROFILE)
    require([(row["r"], row["Q"], row["A"]) for row in rows] == list(RAW_FIXTURES),
            "fixture function differs from literal raw reference")

    # Every ordinary ID at every one of four payload positions; compare raw words.
    position_cases = 0
    for position in range(4):
        for value in range(30):
            values = [1, 6, 11, 17]
            values[position] = value
            values = tuple(values)
            q = oracle_q(values, 4)
            check_case(q, values, 4, "".join(WORDS[v] for v in values))
            position_cases += 1
    substring_ids = {
        marker: [i for i, word in enumerate(WORDS) if marker in word]
        for marker in ("100", "110")
    }
    require(6 in substring_ids["100"] and 11 in substring_ids["110"],
            "internal marker fixture missing")

    # Rejections use literal malformed wire frames, not mutations computed by codec.
    bad_wire = (
        ("empty", "", "BINARY"),
        ("nonbinary", "01010001000000011110x", "BINARY"),
        ("in_band_stop", "010100010000000111100S", "BINARY"),
        ("wrong_header", "000100010000000111100", "HEADER"),
        ("wrong_op", "010110010000000111100", "OP"),
        ("truncated_count", "01010001", "COUNT_TRUNCATED"),
        ("bad_count_suffix", "010100011000000111100", "COUNT_SUFFIX"),
        ("r_zero", "010100000000000111100", "R_RANGE"),
        ("r_five", "010101010000000111100", "R_RANGE"),
        ("r_seven", "010101110000000111100", "R_RANGE"),
        ("r_greater_than_N", "010100100000000111100", "R_RANGE"),
        ("zero_payload", "010100010111100", "N_RANGE"),
        ("five_payload", "010100010" + "000000" * 5 + "111100", "N_RANGE"),
        ("missing_end", "010100010000000", "MISSING_END"),
        ("only_count", "010100010", "MISSING_END"),
        ("short_word", "01010001000000111100", "WORD_LENGTH"),
        ("short_end", "01010001000000011110", "WORD_LENGTH"),
        ("bad_payload_suffix", "010100010000001111100", "WORD_SUFFIX"),
        ("bad_end_suffix", "010100010000000111101", "WORD_SUFFIX"),
        ("up_in_payload", "010100010111110111100", "UP_IN_PAYLOAD"),
        ("up_as_end", "010100010000000111110", "UP_IN_PAYLOAD"),
        ("end_then_word", "010100010000000111100000010", "TRAILING"),
        ("premature_end", "010100010111100000000111100", "TRAILING"),
        ("end_then_end", "010100010000000111100111100", "TRAILING"),
        ("end_then_bit", "0101000100000001111000", "WORD_LENGTH"),
    )
    rejected = [reject(name, code, lambda q=q: codec.decode(q, profile=codec.PROFILE))
                for name, q, code in bad_wire]
    bad_encode = (
        ("encode_empty", (), 1, "N_RANGE"),
        ("encode_five", (0, 0, 0, 0, 0), 1, "N_RANGE"),
        ("encode_reserved_END", (30,), 1, "VALUE_RANGE"),
        ("encode_reserved_UP", (31,), 1, "VALUE_RANGE"),
        ("encode_negative_ID", (-1,), 1, "VALUE_RANGE"),
        ("encode_ID32", (32,), 1, "VALUE_RANGE"),
        ("encode_bool_ID", (True,), 1, "VALUE_RANGE"),
        ("encode_float_ID", (1.0,), 1, "VALUE_RANGE"),
        ("encode_r0", (0,), 0, "R_RANGE"),
        ("encode_r_negative", (0,), -1, "R_RANGE"),
        ("encode_r_greater_N", (0,), 2, "R_RANGE"),
        ("encode_r8", (0, 0, 0, 0), 8, "R_RANGE"),
        ("encode_bool_r", (0,), True, "R_RANGE"),
        ("encode_float_r", (0,), 1.0, "R_RANGE"),
    )
    rejected.extend(reject(name, code, lambda v=v, r=r: codec.encode(v, r, profile=codec.PROFILE))
                    for name, v, r, code in bad_encode)
    rejected.append(reject("wrong_profile", "PROFILE",
                           lambda: codec.decode(RAW_FIXTURES[0][1], profile="legacy-Neg")))
    rejected.append(reject("nonstring_Q", "BINARY",
                           lambda: codec.decode(1010, profile=codec.PROFILE)))
    rejected.append(reject("noniterable_payload", "PAYLOAD",
                           lambda: codec.encode(None, 1, profile=codec.PROFILE)))

    # Full finite cross-question check: 3^N possible bodies at each r=1..N.
    domain = []
    per_n = {}
    for n in range(1, 5):
        n_count = 0
        for values in itertools.product((0, 1, 29), repeat=n):
            for r in range(1, n + 1):
                q = oracle_q(values, r)
                a = "".join(WORDS[v] for v in values[:r])
                check_case(q, values, r, a)
                domain.append((q, a, n, r))
                n_count += 1
        per_n[str(n)] = n_count
    require(len(domain) == 426, "finite domain must contain 426 questions")
    q_strings = [q for q, _, _, _ in domain]
    require(len(set(q_strings)) == 426, "duplicate Q in domain")
    pair_checks = 0
    prefix_pairs = []
    for q1, q2 in itertools.combinations(q_strings, 2):
        pair_checks += 1
        if q1.startswith(q2) or q2.startswith(q1):
            prefix_pairs.append([q1, q2])
    require(not prefix_pairs, "distinct complete questions are prefix-comparable")

    labels = {}
    presentations = 0
    same_label_repeats = 0
    conflicts = []
    observed_q_max = observed_a_max = observed_prefix_max = observed_actions_max = 0
    for q, a, n, r in domain:
        observed_q_max = max(observed_q_max, len(q))
        observed_a_max = max(observed_a_max, len(a))
        observed_actions_max = max(observed_actions_max, len(a) + 1)
        # i=len(A) is the teacher prefix whose target is the external STOP action.
        for i, target in enumerate(a + "S"):
            prefix = q + a[:i]
            presentations += 1
            observed_prefix_max = max(observed_prefix_max, len(prefix))
            if prefix in labels:
                if labels[prefix] != target:
                    conflicts.append({"prefix": prefix, "old": labels[prefix], "new": target})
                else:
                    same_label_repeats += 1
            else:
                labels[prefix] = target
    require(not conflicts, "teacher-prefix next-action contradiction")

    # Arithmetic budget calculation is independent of codec output lengths.
    budget_rows = []
    for n in range(1, 5):
        for r in range(1, n + 1):
            budget_rows.append({"N": n, "r": r, "Q_bits": 2 + 3 + (3 + 1) + (5 + 1) * n + (5 + 1),
                                "A_bits": 6 * r,
                                "max_teacher_prefix_bits": 15 + 6 * n + 6 * r,
                                "correct_actions_including_STOP": 6 * r + 1})
    calculated_maxima = {
        "Q_bits": max(row["Q_bits"] for row in budget_rows),
        "A_bits": max(row["A_bits"] for row in budget_rows),
        "teacher_prefix_bits": max(row["max_teacher_prefix_bits"] for row in budget_rows),
        "generation_actions_including_STOP": max(row["correct_actions_including_STOP"] for row in budget_rows),
    }
    observed_maxima = {"Q_bits": observed_q_max, "A_bits": observed_a_max,
                       "teacher_prefix_bits": observed_prefix_max,
                       "generation_actions_including_STOP": observed_actions_max}
    require(calculated_maxima == observed_maxima == {
        "Q_bits": 39, "A_bits": 24, "teacher_prefix_bits": 63,
        "generation_actions_including_STOP": 25}, "independent budget mismatch")
    require(observed_prefix_max <= 80 and observed_actions_max <= 32,
            "proposed L80/cap32 does not fit legal answers")
    require(observed_actions_max > 24, "legacy cap24 issue must remain visible")

    fixture_data = {"profile": codec.PROFILE, "provenance": {
        "U": "User advanced Echo idea: 01 + 010 + echo length + several n5 symbols + period.",
        "A": "AE1 bounds/profile and r<N prefix_echo are Pro design; prefix_echo is a root extension.",
        "T": "Rows generated by codec and compared with independent literal raw examples."},
        "not_a_training_split": True, "fixtures": rows}
    (HERE / "fixtures.json").write_text(json.dumps(fixture_data, indent=2, ensure_ascii=False) + "\n")
    source_hashes = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                     for name in ("codec.py", "check_design.py", "fixtures.json")}
    result = {
        "status": "PASS", "actor": "ChatGPT Pro / delegated memory_review",
        "profile": codec.PROFILE, "base_head": BASE_HEAD,
        "command": "python -B experiments/spiral_neural/20261113_pro_advanced_echo/check_design.py",
        "working_directory": "repository root", "python_version": platform.python_version(),
        "source_sha256": source_hashes,
        "fixed_literal_raw_fixtures": {"checked": len(RAW_FIXTURES), "passed": len(RAW_FIXTURES)},
        "ordinary_word_position_coverage": {"ordinary_IDs": 30, "positions": 4,
            "cases_checked": position_cases, "passed": position_cases,
            "internal_substring_IDs": substring_ids, "all_parsed_at_six_bit_boundaries": True},
        "malformed_inputs": {"checked": len(rejected), "rejected": len(rejected), "cases": rejected},
        "bounded_domain": {"alphabet": [0, 1, 29], "N": [1, 2, 3, 4], "r": "1..N",
            "question_count_by_N": per_n, "questions_checked": len(domain),
            "distinct_complete_Q": len(set(q_strings)), "unordered_Q_pairs_checked": pair_checks,
            "complete_Q_prefix_pairs": prefix_pairs, "teacher_prefix_presentations": presentations,
            "unique_teacher_prefixes": len(labels), "same_label_repeats": same_label_repeats,
            "teacher_prefix_label_conflicts": conflicts},
        "budgets": {"independent_arithmetic": calculated_maxima,
            "observed_from_executed_domain": observed_maxima, "by_N_r": budget_rows,
            "proposed_L": 80, "proposed_generation_cap": 32, "legacy_cap_24_sufficient": False,
            "existing_learner_changed": False},
        "cost": {"NN_forward_calls": 0, "NN_MAC": 0, "training_updates": 0,
            "external_model_calls": 0},
        "nvidia_status": {"status": "skipped", "reason": "Task is a bounded local codec check; external calls were explicitly excluded."},
        "not_tested": [
            "No neural learner, training, generalization, curriculum effectiveness or semantic growth.",
            "No exhaustive 30^4 body enumeration; only all 30 IDs at each position plus the stated 426-question domain.",
            "No legacy Neg migration, dynamic width, automatic profile inference or network expansion.",
            "No malformed-input fuzzing or full unbounded language proof; the proof in README is for this bounded grammar.",
            "cap32 is a proposed future learner setting, not a modification or execution of any existing learner.",
        ],
    }
    (HERE / "checks.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": result["status"], "raw_fixtures": len(rows),
        "ordinary_position_cases": position_cases, "rejected_invalid_cases": len(rejected),
        "domain_questions": len(domain), "Q_pair_checks": pair_checks,
        "teacher_prefixes": len(labels), "label_conflicts": len(conflicts),
        "observed_maxima": observed_maxima, "NN_forward_calls": 0, "training_updates": 0}))


if __name__ == "__main__":
    main()
