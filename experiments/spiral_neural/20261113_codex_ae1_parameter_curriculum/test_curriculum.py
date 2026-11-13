"""Meaningful bounded synthetic checks; no formal seed forward/optimizer call."""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import run_curriculum as r

SOURCE = None
NATIVE_UPDATES = NATIVE_INFERENCE = MOCK_TARGETS = MOCK_PROBES = 0


class Rows:
    def __init__(self, values):
        self.values = values
        self.mapping = {value["question_id"]: value for value in values}
    def __iter__(self):
        return iter(self.values)
    def __getitem__(self, key):
        return self.mapping[key]


class Engineering(unittest.TestCase):
    def test_payload_grammar_and_matched_r(self):
        bank = r.payload_bank()
        self.assertEqual(len(set(map(tuple, bank))), 900)
        self.assertEqual([(x[0], x[1]) for x in bank], [(a, b) for a in range(30) for b in range(30)])
        suffix = np.random.default_rng(331000).integers(0, 30, size=(900, 2))
        self.assertTrue(np.array_equal(np.array(bank)[:, 2:], suffix))
        rows = r.questions(bank)
        for pair, payload in enumerate(bank):
            a, b = rows[pair], rows[900 + pair]
            self.assertEqual(a["payload"], b["payload"])
            self.assertEqual(r.decode(a["Q"]), (1, payload))
            self.assertEqual(r.decode(b["Q"]), (2, payload))
            self.assertEqual(len(a["Q"]), 39)
            self.assertEqual(len(a["Q"] + a["A"]), 45)
            self.assertEqual(len(b["Q"] + b["A"]), 51)
            self.assertEqual(a["A"], r.word(payload[0]))
            self.assertEqual(b["A"], r.word(payload[0]) + r.word(payload[1]))
            self.assertTrue(a["Q"].endswith("111100"))
        self.assertEqual(r.word(0), "000000")
        self.assertEqual(r.word(29), "111010")
        for value in (30, 31):
            with self.assertRaises(AssertionError):
                r.word(value)
        with self.assertRaises(AssertionError):
            r.encode(3, bank[0])

    def test_teacher_labels_coverage_balance_and_target_weight(self):
        bank = r.payload_bank()
        rows = r.questions(bank)
        p = r.protocol()
        checks = r.data_checks(bank, rows, p)
        self.assertEqual(checks["consistent_unique_teacher_prefixes"], 18000)
        self.assertEqual(checks["first_two_combinations"], 900)
        self.assertEqual(checks["possible_four_word_payloads"], 810000)
        for position in (0, 1):
            self.assertEqual(set(checks["word_position_counts"][position].values()), {30})
        a, b = (r.target_pool(rows, phase) for phase in p["phases"])
        self.assertEqual(a.shape, (6300, 2))
        self.assertEqual(b.shape, (18000, 2))
        self.assertTrue(np.all(a[:, 0] < 900))
        self.assertEqual(int((b[:, 0] < 900).sum()), 6300)
        self.assertEqual(int((b[:, 0] >= 900).sum()), 11700)
        self.assertEqual(b[:8].tolist(), [[0, i] for i in range(7)] + [[900, 0]])

    def test_all_prefrozen_courses_rng_coverage_and_phase_isolation(self):
        rows, p = r.questions(r.payload_bank()), r.protocol()
        for seed in p["seeds"]:
            for phase in p["phases"]:
                course, state = r.schedules(seed, rows, phase)
                pool = r.target_pool(rows, phase)
                rng = np.random.default_rng(seed + phase["schedule_seed_offset"])
                self.assertEqual(course.dtype.str, "<u2")
                self.assertEqual(course.shape, (40, len(pool), 2))
                expected_keys = np.sort(pool[:, 0].astype(np.int64) * 16 + pool[:, 1])
                for epoch in range(40):
                    self.assertTrue(np.array_equal(course[epoch], pool[rng.permutation(len(pool))]))
                    keys = np.sort(course[epoch, :, 0].astype(np.int64) * 16 + course[epoch, :, 1])
                    self.assertTrue(np.array_equal(keys, expected_keys))
                self.assertEqual(state, rng.bit_generator.state)
                if phase["name"] == "r1":
                    self.assertTrue(np.all(course[:, :, 0] < 900))

    def test_gates_streak_reset_advance_and_block(self):
        a, b = r.protocol()["phases"]
        good1 = {"1": {"whole_correct": 900, "questions": 900}}
        self.assertEqual(r.phase_decision(a, 0, good1, 1)[:2], (1, None))
        self.assertEqual(r.phase_decision(a, 1, good1, 2)[:2], (2, "advance"))
        self.assertEqual(r.phase_decision(a, 0, good1, 40)[:2], (1, "blocked_before_r2"))
        good2 = {str(x): {"whole_correct": 900, "questions": 900} for x in (1, 2)}
        bad2 = copy.deepcopy(good2)
        bad2["1"]["whole_correct"] = 899
        self.assertEqual(r.phase_decision(b, 1, bad2, 3)[:2], (0, None))
        self.assertEqual(r.phase_decision(b, 1, good2, 4)[:2], (2, "complete"))
        self.assertEqual(r.phase_decision(b, 1, bad2, 40)[:2], (0, "phase2_cap_failed"))

    def test_generation_cap32_context_guard_and_final_taught_only(self):
        class Constant:
            L = 80
            inference_calls = inference_macs = 0
            def state(self):
                return {"t": np.array(0)}
            def forward(self, text):
                self.inference_calls += 1
                self.inference_macs += 10432
                return None, None, np.array([1., 0., -1.])
        net = Constant()
        output = r.generate(net, "0" * 39)
        self.assertEqual(output["tokens"], "0" * 32)
        self.assertTrue(output["cap_exhausted"])
        self.assertNotIn("S", output["tokens"])
        net.L = 45
        output = r.generate(net, "0" * 39)
        self.assertEqual(output["tokens"], "0" * 7)
        self.assertTrue(output["context_exhausted"])
        # Minimal mock rows ensure finalTF uses its taught argument only.
        net.L = 80
        taught = [{"question_id": 0, "r": 1, "pair_id": 0, "Q": "010", "A": "01"}]
        free = {"rows": [{"question_id": 0, "whole_correct": False, "tokens": "S"}]}
        result = r.final_tf(net, taught, free)
        self.assertEqual(result["taught_r_only"], [1])
        self.assertEqual(result["inference_calls"], 3)
        self.assertEqual(set(result["scores"]), {"1"})

    def test_native_tiny_state_restore_target_replay(self):
        global NATIVE_UPDATES, NATIVE_INFERENCE
        if SOURCE is None:
            self.skipTest("Use --engineering --source for native synthetic check")
        cls = r.source_model(Path(SOURCE).read_bytes())
        primary = cls(960051, L=80, H=64)
        replay = copy.deepcopy(primary)
        row = {"question_id": 0, "Q": "010", "A": "01"}
        a, b = r.EpochTrace(), r.EpochTrace()
        for position in (2, 0, 1):
            r.update_target(primary, row, position, a)
            NATIVE_UPDATES += 1
            pred, loss = replay.step(row["Q"] + row["A"][:position], (row["A"] + "S")[position])
            b.observe(0, position, pred, loss, (row["A"] + "S")[position])
            NATIVE_UPDATES += 1
        self.assertEqual(a.result(), b.result())
        self.assertTrue(r.equal_state(r.full_state(primary), r.full_state(replay)))
        restored = r.restore(cls, r.read_npz(r.npz_bytes(r.full_state(primary))))
        self.assertTrue(r.equal_state(r.full_state(primary), r.full_state(restored)))
        before = restored.state()
        calls = restored.inference_calls
        r.generate(restored, "010")
        NATIVE_INFERENCE += restored.inference_calls - calls
        self.assertTrue(r.equal_state(before, restored.state()))

    def test_mock_adaptive_curriculum_transfer_replay_and_phase1_block(self):
        global MOCK_TARGETS, MOCK_PROBES
        if SOURCE is None:
            self.skipTest("Use --engineering --source for mock orchestration")
        native = r.source_model(Path(SOURCE).read_bytes())
        class Mock(native):
            def step(self, prefix, target):
                global MOCK_TARGETS
                MOCK_TARGETS += 1
                self.t += 1
                self.train_macs += 21056
                return target, .25
        rows = Rows([{"question_id": 0, "pair_id": 0, "r": 1, "Q": "010", "A": "01"},
                     {"question_id": 900, "pair_id": 0, "r": 2, "Q": "011", "A": "10"}])
        phases = [{"name": "r1", "taught_r": [1], "questions_per_epoch": 1, "targets_per_epoch": 3, "max_epochs": 3},
                  {"name": "r12", "taught_r": [1, 2], "questions_per_epoch": 2, "targets_per_epoch": 6, "max_epochs": 3}]
        phase1 = np.array([[[0, 2], [0, 0], [0, 1]]] * 3, dtype="<u2")
        phase2 = np.array([[[900, 2], [0, 0], [900, 1], [0, 2], [900, 0], [0, 1]]] * 3, dtype="<u2")
        seed = 960052
        courses = {f"seed{seed}-r1": phase1, f"seed{seed}-r12": phase2}
        initial = r.full_state(Mock(seed, L=80, H=64))
        def mock_probe(net, taught):
            global MOCK_PROBES
            MOCK_PROBES += 1
            net.inference_calls += len(taught)
            net.inference_macs += len(taught) * 10432
            return {"scores": {str(x["r"]): {"questions": 1, "whole_correct": 1} for x in taught},
                    "rows": [{"question_id": x["question_id"], "r": x["r"], "pair_id": x["pair_id"], "tokens": x["A"] + "S", "whole_correct": True} for x in taught],
                    "inference_calls": len(taught), "inference_dense_MAC": len(taught) * 10432}
        with tempfile.TemporaryDirectory(prefix="ae1-mock-pass-") as directory, patch.object(r, "probe", mock_probe), contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            r.run_seed(Mock, initial, courses, rows, phases, root, seed)
            r.run_seed(Mock, initial, courses, rows, phases, root, seed, replay=True)
            summary = r.read(root / f"seed{seed}/training-summary.json")
            self.assertEqual(summary["phase_reached"], "r12")
            self.assertEqual(summary["taught_r"], [1, 2])
            self.assertTrue(summary["completed_curriculum"])
            self.assertEqual(summary["training_updates"], 18)
            self.assertEqual(summary["question_exposures"], 6)
            self.assertEqual(summary["phases"][0]["exit_full_state_sha256"], summary["phases"][1]["entry_full_state_sha256"])
        def failed_probe(net, taught):
            result = mock_probe(net, taught)
            for score in result["scores"].values():
                score["whole_correct"] = 0
            return result
        with tempfile.TemporaryDirectory(prefix="ae1-mock-block-") as directory, patch.object(r, "probe", failed_probe), contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            r.run_seed(Mock, initial, courses, rows, phases, root, seed)
            r.run_seed(Mock, initial, courses, rows, phases, root, seed, replay=True)
            summary = r.read(root / f"seed{seed}/training-summary.json")
            self.assertTrue(summary["blocked_before_r2"])
            self.assertEqual(summary["taught_r"], [1])
            self.assertFalse((root / f"seed{seed}/r12").exists())
            self.assertEqual(summary["training_updates"], 9)

    def test_budget_and_approval(self):
        p = r.protocol()
        self.assertEqual(40 * (6300 + 18000), p["maximum_updates_per_seed"])
        self.assertEqual(972000 * 21056, 20466432000)
        with tempfile.TemporaryDirectory(prefix="ae1-manifest-gate-") as directory:
            path = Path(directory) / "manifest.json"
            r.write(path, {})
            with self.assertRaisesRegex(AssertionError, "approved manifest"):
                r.validate_inputs(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
