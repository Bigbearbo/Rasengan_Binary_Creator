"""AE1 r1/r2 suffix non-identifiability: exhaustive model-free lookup control.

Frozen source: codex/ae1-parameter-curriculum-20261113 at
966297559b4f4dedc4b8cf655258d4036cc21cc8; protocol SLE-AE1-n5-v1.
No model inference, training or external teacher oracle is used during testing.
"""
import hashlib
import json
from collections import Counter

import numpy as np

SOURCE = "966297559b4f4dedc4b8cf655258d4036cc21cc8"
MANIFEST_SHA = "dcf3ea17d1f5a179ccaa37b5f544f630ad274afdfa7b56ab93684d1a9344fe60"


def word(n):
    assert isinstance(n, int) and 0 <= n < 30
    return format(n, "05b") + "0"


def raw_question(r, payload):
    assert r in (1, 2) and len(payload) == 4
    return "01" + "010" + format(r, "03b") + "0" + "".join(map(word, payload)) + "111100"


def raw_answer(r, payload):
    return "".join(map(word, payload[:r])) + "S"


def key_from_raw(q):
    assert len(q) == 39 and q[:5] == "01010" and q[-6:] == "111100"
    return (q[5:8], q[9:21])  # r and first two complete 6-bit words only


def run():
    suffixes = np.random.default_rng(331000).integers(0, 30, size=(900, 2))
    bank = [(a, b, int(suffixes[30*a + b, 0]), int(suffixes[30*a + b, 1]))
            for a in range(30) for b in range(30)]
    # Check generator against selected public manifest counts (not just formulas).
    assert Counter(row[2] for row in bank)[0] == 25
    assert Counter(row[3] for row in bank)[0] == 27
    assert Counter(row[2] for row in bank)[25] == 19
    assert Counter(row[3] for row in bank)[25] == 33

    table = {}
    for r in (1, 2):
        for payload in bank:
            q, label = raw_question(r, payload), raw_answer(r, payload)
            key = key_from_raw(q)
            assert key not in table
            table[key] = label  # memorize only the 1,800 frozen training answers
    assert len(table) == 1800

    total = correct = unseen = unseen_correct = seen = 0
    for r in (1, 2):
        for a in range(30):
            for b in range(30):
                frozen_tail = tuple(bank[30*a + b][2:])
                for c in range(30):
                    for d in range(30):
                        payload = (a, b, c, d)
                        q = raw_question(r, payload)
                        pred = table[key_from_raw(q)]
                        truth = raw_answer(r, payload)  # score-only reference
                        ok = pred == truth
                        total += 1
                        correct += ok
                        if (c, d) == frozen_tail:
                            seen += 1
                        else:
                            unseen += 1
                            unseen_correct += ok
    assert (total, correct, seen, unseen, unseen_correct) == (1620000, 1620000, 1800, 1618200, 1618200)
    a, b, c, d = bank[0]
    changed = (a, b, (c + 1) % 30, d)
    original_q = raw_question(2, bank[0])
    changed_q = raw_question(2, changed)
    assert original_q != changed_q and raw_answer(2, bank[0]) == raw_answer(2, changed)
    outcome = {
        "status": "PASS", "source_commit": SOURCE, "manifest_sha256_reported": MANIFEST_SHA,
        "profile": "SLE-AE1-n5-v1 fixed N4, legal r1/r2 only",
        "train_questions": 1800, "train_payloads": 900,
        "all_legal_N4_payloads": 810000, "possible_r1_r2_questions": total,
        "test_unseen_suffix_questions": unseen, "test_unseen_suffix_correct": unseen_correct,
        "test_train_questions": seen, "correct_all": correct,
        "table_entries": len(table), "network_forward_calls": 0, "optimizer_updates": 0,
        "training_MAC": 0, "model_parameters": 0,
        "initial_frozen_seed_for_suffixes": 331000,
        "example_train_Q": original_q, "example_changed_suffix_Q": changed_q,
        "example_identical_A": raw_answer(2, changed),
        "finding": "All r1/r2 answers depend only on r and first 2 words; unseen suffixes cannot falsify prefix-pair memorization.",
        "limit": "This is a symbolic lookup control, NOT trained NN generalization or evidence of a learned copy rule. Frozen PR26 formal NN still unexecuted."
    }
    print(json.dumps(outcome, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    run()
