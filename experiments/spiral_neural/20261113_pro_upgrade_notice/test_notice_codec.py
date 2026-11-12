"""Executable UR1 protocol checks; no training, learned parser, or NN claim."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import unittest

from notice_codec import (
    Branch, FIXTURE_PATHS, MAX_CHILD_ID, MAX_DEPTH, Node, NoticeError,
    NoticeReceiver, PROFILE_ID, ROOT_HEADER, branch_at, decode_address,
    decode_notice, decode_reply, encode_address, encode_notice, encode_reply,
    end, fixture_tree, ordinary_capacity, ordinary_value, ordinary_word, up,
    verify_reply, word,
)


class NoticeCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = {"fixture_roundtrips": [], "rejected_notices": [],
                        "data_control_collisions": [], "ordinary_capacities": [],
                        "tree_shape_rejections": []}

    def assert_rejected_unchanged(self, receiver, bits, code, label, *, profile_id=PROFILE_ID):
        tree_before = deepcopy(receiver.tree)
        commits_before = receiver.applied_transitions
        with self.assertRaises(NoticeError) as caught:
            receiver.receive_notice(bits, profile_id=profile_id)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(receiver.tree, tree_before)
        self.assertEqual(receiver.applied_transitions, commits_before)
        self.evidence["rejected_notices"].append({
            "case": label, "bits": len(bits), "error": caught.exception.code,
            "tree_and_commit_count_unchanged": True,
        })

    def test_fixture_roundtrips_commit_once_and_replay(self):
        for path in FIXTURE_PATHS:
            with self.subTest(path=path):
                receiver = NoticeReceiver()
                before = deepcopy(receiver.tree)
                branch = branch_at(before, path)
                target = branch.n + 1
                q = encode_notice(path, target, before)
                notice = decode_notice(q, before, profile_id=PROFILE_ID)
                self.assertEqual((notice.address, notice.target_n, notice.k), (path, target, branch.k))
                self.assertEqual(encode_notice(notice.address, notice.target_n, before), q)
                receipt = receiver.receive_notice(q, profile_id=PROFILE_ID)
                self.assertEqual(receipt.status, "upgraded")
                self.assertEqual(receiver.applied_transitions, 1)
                self.assertTrue(receipt.external_stop)
                self.assertEqual(receipt.reply_bits, encode_address(path) + up(target, branch.k))
                for tree in (before, receiver.tree):
                    reply = verify_reply(notice, receipt.reply_bits, tree, profile_id=PROFILE_ID)
                    self.assertEqual((reply.address, reply.target_n, reply.k), (path, target, branch.k))
                after = deepcopy(receiver.tree)
                replay = receiver.receive_notice(q, profile_id=PROFILE_ID)
                self.assertEqual(replay.status, "already_current")
                self.assertEqual(replay.reply_bits, receipt.reply_bits)
                self.assertEqual(receiver.tree, after)
                self.assertEqual(receiver.applied_transitions, 1)
                # Exactly one addressed branch changes; input tree and sibling profiles survive.
                self.assertEqual(branch_at(before, path).n, branch.n)
                for other in FIXTURE_PATHS:
                    expected = replace(branch_at(before, other), n=target) if other == path else branch_at(before, other)
                    self.assertEqual(branch_at(receiver.tree, other), expected)
                self.evidence["fixture_roundtrips"].append({
                    "address": list(path), "name": branch.name, "role": branch.role,
                    "current_n": branch.n, "target_n": target, "k": branch.k,
                    "address_bits": notice.address_bits, "up": notice.up_bits, "end": notice.end_bits,
                    "question": q, "answer": receipt.reply_bits,
                    "question_bits": len(q), "answer_bits": len(receipt.reply_bits),
                    "question_plus_answer_bits": len(q) + len(receipt.reply_bits),
                    "external_stop": True, "transition_count_after_replay": 1,
                })

    def test_exact_wire_examples_and_fixture_prefix_bound(self):
        tree = fixture_tree()
        expected_q = "00111100" "00100000" "111110" "111110" "111110" "111100"
        expected_a = "00100000" "111110"
        q = encode_notice((0,), 5, tree)
        a = encode_reply(decode_notice(q, tree, profile_id=PROFILE_ID))
        self.assertEqual((q, a, len(q), len(a)), (expected_q, expected_a, 40, 14))
        path3 = (5, 5, 0)
        q3 = encode_notice(path3, 5, tree)
        a3 = encode_reply(decode_notice(q3, tree, profile_id=PROFILE_ID))
        self.assertEqual(encode_address(path3), "0110101010100000")
        self.assertEqual((len(q3), len(a3), len(q3 + a3)), (48, 22, 70))
        costs = []
        for path in FIXTURE_PATHS:
            profile = branch_at(tree, path)
            q = encode_notice(path, profile.n + 1, tree)
            a = encode_reply(decode_notice(q, tree, profile_id=PROFILE_ID))
            costs.append(len(q) + len(a))
        self.assertEqual(max(costs), 70)  # This fixture, not the whole root address space.

    def test_control_words_and_k_are_not_trailing_zero_run(self):
        for n in range(1, 6):
            for k in range(1, 4):
                with self.subTest(n=n, k=k):
                    u, e = up(n, k), end(n, k)
                    self.assertEqual(len(u), n + k)
                    self.assertEqual(len(e), n + k)
                    self.assertNotEqual(u, e)
                    self.assertEqual(int(u[:n], 2), (1 << n) - 1)
                    self.assertEqual(int(e[:n], 2), (1 << n) - 2)
                    self.assertEqual(len(u) - len(u.rstrip("0")), k)
                    self.assertEqual(len(e) - len(e.rstrip("0")), k + 1)
        self.assertEqual(end(5, 1), "111100")
        self.assertEqual(ordinary_value("111100", Branch("number", "data", 5, 1)), 30)

    def test_role_scoped_reservations_and_full_data_values(self):
        for role in ("data", "address"):
            profile = Branch(role, role, 5, 1)
            for value in range(32):
                bits = ordinary_word(value, profile)
                self.assertEqual(ordinary_value(bits, profile), value)
                if value in (30, 31):
                    self.evidence["data_control_collisions"].append({
                        "role": role, "value": value, "word": bits, "accepted_as_number": True,
                    })
        for role in ("operator", "control"):
            profile = Branch(role, role, 5, 1)
            for value in range(30):
                self.assertEqual(ordinary_value(ordinary_word(value, profile), profile), value)
            for value in (30, 31):
                with self.assertRaisesRegex(NoticeError, "RESERVED_CONTROL"):
                    ordinary_word(value, profile)
                with self.assertRaisesRegex(NoticeError, "RESERVED_CONTROL"):
                    ordinary_value(word(value, 5, 1), profile)

    def test_small_control_capacities(self):
        for n, expected in ((1, 0), (2, 2), (3, 6)):
            profile = Branch("capacity", "operator", n, 1)
            accepted = []
            for value in range(1 << n):
                try:
                    ordinary_word(value, profile)
                    accepted.append(value)
                except NoticeError as error:
                    self.assertEqual(error.code, "RESERVED_CONTROL")
            self.assertEqual(accepted, list(range(expected)))
            self.assertEqual(ordinary_capacity(n, "operator"), expected)
            self.evidence["ordinary_capacities"].append({"n": n, "ordinary_operator_slots": len(accepted)})

    def test_low_bits_stable_child_ids_and_highwater_preserved(self):
        for path in FIXTURE_PATHS:
            receiver = NoticeReceiver()
            before = branch_at(receiver.tree, path)
            address_bits = encode_address(path)
            q = encode_notice(path, before.n + 1, receiver.tree)
            receiver.receive_notice(q, profile_id=PROFILE_ID)
            after = branch_at(receiver.tree, path)
            self.assertEqual((after.ordinary_ids, after.highwater), (before.ordinary_ids, before.highwater))
            self.assertEqual(encode_address(path), address_bits)
            for value in range(ordinary_capacity(before.n, before.role)):
                old_bits, new_bits = ordinary_word(value, before), ordinary_word(value, after)
                self.assertEqual(new_bits, "0" + old_bits)
                self.assertEqual(ordinary_value(new_bits, after), value)
        # The deleted ID is not recovered from the currently present IDs.
        self.assertEqual(branch_at(receiver.tree, (0,)).highwater, 3)
        self.assertEqual(branch_at(receiver.tree, (0,)).ordinary_ids, (0, 1, 2))

    def test_mixed_triples_rejected_without_commit(self):
        prefix = ROOT_HEADER + encode_address((0,))
        for label, triple in (
            ("second_is_old_width", (up(5, 1), up(4, 1), up(5, 1))),
            ("second_is_wider", (up(5, 1), up(6, 1), up(5, 1))),
            ("third_is_old_width", (up(5, 1), up(5, 1), up(4, 1))),
            ("END_inside_triple", (up(5, 1), end(5, 1), up(5, 1))),
            ("first_is_old_width", (up(4, 1), up(5, 1), up(5, 1))),
        ):
            with self.subTest(label=label):
                q = prefix + "".join(triple) + end(5, 1)
                self.assert_rejected_unchanged(NoticeReceiver(), q, "MIXED_UP", label)

    def test_every_truncation_rejected_without_commit(self):
        tree = fixture_tree()
        q = encode_notice((5, 5, 0), 5, tree)
        for stop in range(len(q)):
            with self.subTest(stop=stop):
                self.assert_rejected_unchanged(NoticeReceiver(tree), q[:stop], "TRUNCATED", f"truncate_at_{stop}")

    def test_wrong_end_extra_bits_and_repeat_count_rejected(self):
        prefix = ROOT_HEADER + encode_address((0,))
        u, e = up(5, 1), end(5, 1)
        for label, q, code in (
            ("UP_instead_of_END", prefix + u * 4, "BAD_END"),
            ("zero_instead_of_END", prefix + u * 3 + "000000", "BAD_END"),
            ("two_UP_copies", prefix + u * 2 + e, "MIXED_UP"),
            ("four_UP_copies", prefix + u * 4 + e, "BAD_END"),
            ("trailing_bit", prefix + u * 3 + e + "0", "EXTRA_BITS"),
        ):
            with self.subTest(label=label):
                self.assert_rejected_unchanged(NoticeReceiver(), q, code, label)

    def test_unknown_address_internal_node_and_root_rejected(self):
        body = up(5, 1) * 3 + end(5, 1)
        for label, address, code in (
            ("unknown_child", encode_address((6,)), "UNKNOWN_ADDRESS"),
            ("unknown_nested_child", encode_address((5, 2)), "UNKNOWN_ADDRESS"),
            ("internal_node", encode_address((5,)), "UNSUPPORTED_INTERNAL_NODE"),
            ("root_itself", "0000", "ROOT_GROWTH_UNSUPPORTED"),
        ):
            self.assert_rejected_unchanged(NoticeReceiver(), ROOT_HEADER + address + body, code, label)

    def test_stale_jump_and_current_confirmation(self):
        receiver = NoticeReceiver()
        for target, code in ((3, "STALE_TARGET"), (6, "JUMP_TARGET")):
            q = encode_notice((0,), target, receiver.tree)
            self.assert_rejected_unchanged(receiver, q, code, f"target_{target}_from_4")
        before = deepcopy(receiver.tree)
        q_current = encode_notice((0,), 4, receiver.tree)
        receipt = receiver.receive_notice(q_current, profile_id=PROFILE_ID)
        self.assertEqual(receipt.status, "already_current")
        self.assertEqual(receiver.applied_transitions, 0)
        self.assertEqual(receiver.tree, before)
        q5 = encode_notice((0,), 5, receiver.tree)
        receiver.receive_notice(q5, profile_id=PROFILE_ID)
        q6 = encode_notice((0,), 6, receiver.tree)
        receiver.receive_notice(q6, profile_id=PROFILE_ID)
        self.assertEqual(receiver.applied_transitions, 2)
        self.assertEqual(branch_at(receiver.tree, (0,)).n, 6)
        self.assert_rejected_unchanged(receiver, q5, "STALE_TARGET", "replay_5_after_growing_to_6")

    def test_explicit_profile_and_notice_entry(self):
        receiver = NoticeReceiver()
        q = encode_notice((0,), 5, receiver.tree)
        self.assert_rejected_unchanged(receiver, q, "UNKNOWN_PROFILE", "legacy_profile", profile_id="legacy")
        self.assert_rejected_unchanged(receiver, "111110", "TRUNCATED", "ordinary_31_is_not_a_notice")
        self.assert_rejected_unchanged(receiver, "111100", "TRUNCATED", "ordinary_30_is_not_a_notice")
        self.assert_rejected_unchanged(receiver, "0" + q[1:7] + "1" + q[8:], "BAD_ROOT_HEADER", "wrong_root_UP")
        self.assert_rejected_unchanged(receiver, "001" + up(4, 2) + q[len(ROOT_HEADER):], "BAD_ROOT_HEADER", "root_width_growth")
        self.assert_rejected_unchanged(receiver, q + "STOP", "NON_BINARY", "STOP_is_not_a_wire_token")
        with self.assertRaises(TypeError):
            receiver.receive_notice(q)  # No profile default or hidden auto-dispatch.
        self.assertEqual(receiver.applied_transitions, 0)

    def test_address_capacity_and_numeric_top_values(self):
        self.assertEqual((MAX_DEPTH, MAX_CHILD_ID), (7, 7))
        for path in ((6,), (7,), (7,) * 7):
            self.assertEqual(decode_address(encode_address(path)), path)
            tree = Node(Branch("deep", "data", 4, 1))
            for child in reversed(path):
                tree = Node(children={child: tree})
            q = encode_notice(path, 5, tree)
            receiver = NoticeReceiver(tree)
            self.assertEqual(receiver.receive_notice(q, profile_id=PROFILE_ID).address, path)
        for path, code in (((), "ROOT_GROWTH_UNSUPPORTED"), ((0,) * 8, "ADDRESS_CAPACITY"),
                           ((8,), "ADDRESS_CAPACITY"), ((-1,), "ADDRESS_CAPACITY"),
                           ((True,), "ADDRESS_CAPACITY")):
            with self.assertRaises(NoticeError) as caught:
                encode_address(path)
            self.assertEqual(caught.exception.code, code)

    def test_bad_address_suffix_rejected_without_commit(self):
        q = encode_notice((0,), 5, fixture_tree())
        for index in (len(ROOT_HEADER) + 3, len(ROOT_HEADER) + 7):
            altered = q[:index] + "1" + q[index + 1:]
            self.assert_rejected_unchanged(NoticeReceiver(), altered, "BAD_SUFFIX", f"address_suffix_at_{index}")

    def test_reply_pairing_requires_matching_address_and_target(self):
        tree = fixture_tree()
        notice = decode_notice(encode_notice((0,), 5, tree), tree, profile_id=PROFILE_ID)
        for bits in (encode_address((1,)) + up(5, 1), encode_address((0,)) + up(4, 1)):
            # Both are legal replies in isolation, but neither answers this request.
            decode_reply(bits, tree, profile_id=PROFILE_ID)
            with self.assertRaisesRegex(NoticeError, "REPLY_MISMATCH"):
                verify_reply(notice, bits, tree, profile_id=PROFILE_ID)
        self.assertEqual(verify_reply(notice, encode_reply(notice), tree, profile_id=PROFILE_ID).address, (0,))

    def test_reply_is_one_UP_without_END_or_in_band_STOP(self):
        tree = fixture_tree()
        notice = decode_notice(encode_notice((0,), 5, tree), tree, profile_id=PROFILE_ID)
        a = encode_reply(notice)
        for bad in (a + up(5, 1), a + end(5, 1), a + "STOP", a[:-1]):
            with self.assertRaises(NoticeError):
                decode_reply(bad, tree, profile_id=PROFILE_ID)


    def test_shared_node_alias_and_cycle_are_not_trees(self):
        shared = Node(Branch("shared_width", "data", 4, 1))
        aliased = Node(children={0: shared, 1: shared})
        cyclic = Node()
        cyclic.children[0] = cyclic
        for label, tree in (("two_paths_one_node", aliased), ("cycle", cyclic)):
            with self.subTest(label=label):
                with self.assertRaises(NoticeError) as caught:
                    NoticeReceiver(tree)
                self.assertEqual(caught.exception.code, "NOT_A_TREE")
                self.evidence["tree_shape_rejections"].append({"case": label, "error": "NOT_A_TREE"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path(__file__).with_name("results.json"))
    args = parser.parse_args()
    loader = unittest.defaultTestLoader
    names = loader.getTestCaseNames(NoticeCodecTests)
    result = unittest.TextTestRunner(verbosity=2).run(loader.loadTestsFromTestCase(NoticeCodecTests))
    here = Path(__file__).resolve().parent
    evidence = NoticeCodecTests.evidence
    rows = evidence["fixture_roundtrips"]
    report = {
        "profile_id": PROFILE_ID,
        "author": "ChatGPT Pro",
        "scope": "code/protocol tests only; no NN training; no learnability or training-benefit claim",
        "command": "python test_notice_codec.py --results results.json",
        "python_version": platform.python_version(),
        "source_sha256": {name: hashlib.sha256((here / name).read_bytes()).hexdigest()
                          for name in ("notice_codec.py", "test_notice_codec.py")},
        "unittest": {"tests_run": result.testsRun, "failures": len(result.failures),
                     "errors": len(result.errors), "skipped": len(result.skipped),
                     "passed": result.wasSuccessful(), "test_names": names},
        "fixture_max_question_plus_answer_bits": max((row["question_plus_answer_bits"] for row in rows), default=None),
        "fixture_path_count": len(rows),
        "rejection_case_count": len(evidence["rejected_notices"]),
        "evidence": evidence,
        "limitations": [
            "Root c=3/k=2 is fixed; root growth and unbounded-header replay are not implemented.",
            "Address depth is 1..7 and each stable child ID is 0..7; only configured targets resolve.",
            "The 70-bit Q+A maximum covers the eight fixture upgrades, not every legal future frame.",
            "The 001 prefix selects UR1 root syntax, not the maximum k of every target branch.",
            "profile_id and the syntax tree are oracle context, not additional NN input features.",
            "Single-process in-memory commit only; no persistent/distributed handshake or root migration.",
            "Only trees are supported: repeated Node identities and cycles are rejected at construction.",
            "Legacy parsers, model checkpoints, and training remain unchanged.",
        ],
        "nvidia": {"status": "skipped_unavailable", "calls": 0,
                   "reason": "No NVIDIA/OpenRouter worker tool is available in this execution environment."},
    }
    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Evidence written to {args.results}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
