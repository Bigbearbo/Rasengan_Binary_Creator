"""Bounded synthetic engineering; never train/evaluate an official seed."""
import copy
import io
from pathlib import Path
import tempfile
import unittest
import numpy as np
import run_early_mix as r

SOURCE = None
NATIVE_UPDATES = 0
NATIVE_INFERENCE = 0


class Engineering(unittest.TestCase):
    def test_schedules_exact_pairing_and_rng(self):
        for seed in (101, 202, 303):
            courses, states = r.build_schedules(seed)
            repeated, repeated_states = r.build_schedules(seed)
            self.assertEqual(states, repeated_states)
            for arm in ("early", "late"):
                self.assertTrue(np.array_equal(courses[arm], repeated[arm]))
                self.assertEqual(courses[arm].shape, (2400, 2))
            self.assertTrue(np.array_equal(courses["early"][1200:], courses["late"][1200:]))
            rng = np.random.default_rng(seed + 122000)
            expected = np.concatenate([rng.permutation([0, 1]), rng.permutation([0] * 599 + [1] * 599)])
            self.assertTrue(np.array_equal(courses["early"][:1200, 0], expected))
            for op in (0, 1):
                left = courses["early"][courses["early"][:, 0] == op, 1]
                right = courses["late"][courses["late"][:, 0] == op, 1]
                self.assertTrue(np.array_equal(left, right))
                self.assertTrue(all(set(cycle) == set(r.TRAIN) for cycle in left.reshape(200, 6)))

    def test_native_lesson_vs_target_replay_and_restore(self):
        global NATIVE_UPDATES, NATIVE_INFERENCE
        if SOURCE is None:
            self.skipTest("Use --engineering --source for the real bounded synthetic check")
        cls = r.source_model(Path(SOURCE).read_bytes())
        primary = cls(940031, L=13, H=69)
        replay = copy.deepcopy(primary)
        with tempfile.TemporaryDirectory(prefix="early-mix-synthetic-") as folder:
            path = Path(folder) / "targets.jsonl.gz"
            trace = r.Trace(path, False)
            r.observed_lesson(primary, "010", "01", {"lesson": 1, "op": 0, "value": 0}, trace, False)
            self.assertEqual(trace.close()["targets"], 3)
            NATIVE_UPDATES += 3
            trace = r.Trace(path, True)
            r.observed_lesson(replay, "010", "01", {"lesson": 1, "op": 0, "value": 0}, trace, True)
            trace.close()
            NATIVE_UPDATES += 3
            self.assertTrue(r.equal_state(r.full_state(primary), r.full_state(replay)))
            restored = r.restore(cls, r.read_npz(r.npz_bytes(r.full_state(primary))))
            self.assertTrue(r.equal_state(r.full_state(primary), r.full_state(restored)))
            before = restored.state()
            before_calls = restored.inference_calls
            r.generate(restored, "010")
            NATIVE_INFERENCE += restored.inference_calls - before_calls
            self.assertTrue(r.equal_state(before, restored.state()))
            self.assertEqual(restored.t, 3)

    def test_generation_and_opcode_probe_have_no_oracle(self):
        class Constant:
            L = 13
            inference_calls = inference_macs = 0
            def state(self):
                return {"t": np.array(0)}
            def forward(self, prefix):
                self.inference_calls += 1
                self.inference_macs += 2001
                return None, None, np.array([0., -1., 1.])
        net = Constant()
        result = r.evaluate(net)
        self.assertEqual(result["opcode_only_empty_A_prefix_probe"]["raw_token_flip"], 0)
        self.assertEqual(result["opcode_only_empty_A_prefix_probe"]["both_correct_and_flip"], 0)
        self.assertEqual(result["opcode_only_empty_A_prefix_probe"]["extra_forward_calls"], 0)
        self.assertEqual(result["inference_calls"], 96)
        self.assertTrue(all(row["generation"]["tokens"] == "S" for row in result["truth"]))
        for row in result["opcode_only_empty_A_prefix_probe"]["pairs"]:
            self.assertEqual(row["A_prefix"], "")
            self.assertEqual(row["only_changed_Q_position"], 3)

    def test_grammar_and_budget(self):
        p = r.protocol()
        for value in range(8):
            self.assertEqual(r.answer(0, value)[-1], "0")
            self.assertEqual(r.answer(1, value)[-1], "0")
            self.assertTrue(all(a != b for a, b in zip(r.answer(0, value)[:3], r.answer(1, value)[:3])))
            self.assertEqual(len(r.encode(0, value) + r.answer(0, value)), 13)
        self.assertEqual(12000 * 4209, p["training_dense_MAC_per_student"])
        self.assertEqual(6 * 12000, p["primary_targets"])

    def test_zip_bytes_and_approval_gate(self):
        data = {"source.py": b"# public\n", "plan.json": b"{}\n"}
        self.assertEqual(r.make_zip(data), r.make_zip(data))
        with tempfile.TemporaryDirectory(prefix="early-mix-gate-") as folder:
            path = Path(folder) / "manifest.json"
            r.write(path, {})
            with self.assertRaisesRegex(AssertionError, "approved manifest"):
                r.validate_inputs(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
