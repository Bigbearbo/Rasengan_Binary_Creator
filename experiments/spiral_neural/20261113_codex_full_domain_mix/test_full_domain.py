"""Synthetic-only native updates and zero-optimizer orchestration tests."""
import ast
import contextlib
import copy
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
import run_full_domain as r

SOURCE = None
NATIVE_UPDATES = NATIVE_INFERENCE = MOCK_TARGETS = MOCK_PROBES = 0


class Engineering(unittest.TestCase):
    def test_complete_numeric_domain_and_original_grammar(self):
        pool = r.question_pool()
        self.assertEqual(len(pool), 512)
        self.assertEqual(len({row["Q"] for row in pool}), 512)
        self.assertEqual([row["input_id"] for row in pool], list(range(512)))
        for row in pool:
            self.assertEqual(len(row["Q"]), 14)
            self.assertEqual(len(row["A"]), 9)
            self.assertEqual(len(row["Q"] + row["A"]), 23)
            self.assertEqual(row["A"][-1], "0")
        self.assertEqual(r.answer(0, 255), "111111110")
        self.assertEqual(r.answer(1, 255), "000000000")
        if SOURCE is not None:
            nodes = {node.name: node for node in ast.parse(Path(SOURCE).read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef)}
            namespace = {}
            exec(compile(ast.Module(body=[copy.deepcopy(nodes[name]) for name in ("encode", "answer")], type_ignores=[]), "<pure-original-grammar>", "exec"), namespace)
            profile = SimpleNamespace(nop=2, nd=8, ops=(0, 1), end=False, reserved=[])
            for row in pool:
                self.assertEqual(row["Q"], namespace["encode"](profile, row["op"], row["value"]))
                self.assertEqual(row["A"], namespace["answer"](row["op"], 8, row["value"]))

    def test_all40_epoch_orders_fixed_and_complete(self):
        expected_pool = {(op, value) for op in (0, 1) for value in range(256)}
        for seed in (101, 202, 303):
            course, state = r.schedule(seed)
            repeated, repeated_state = r.schedule(seed)
            self.assertEqual(state, repeated_state)
            self.assertTrue(np.array_equal(course, repeated))
            self.assertEqual(course.shape, (40, 512, 2))
            for epoch in course:
                self.assertEqual(set(map(tuple, epoch.tolist())), expected_pool)
            rng = np.random.default_rng(seed + 221000)
            indices = rng.permutation(512)
            self.assertEqual((course[0, :, 0] * 256 + course[0, :, 1]).tolist(), indices.tolist())

    def test_stopping_requires_two_consecutive_full_free_passes(self):
        passed = {str(op): {"questions": 256, "whole_correct": 256} for op in (0, 1)}
        failed = copy.deepcopy(passed)
        failed["1"]["whole_correct"] = 255
        self.assertEqual(r.stop_decision(0, passed, 1), (1, None))
        self.assertEqual(r.stop_decision(1, failed, 2), (0, None))
        self.assertEqual(r.stop_decision(1, passed, 3), (2, "two_consecutive_full_training_passes"))
        self.assertEqual(r.stop_decision(0, passed, 40), (1, "epoch_cap"))
        self.assertEqual(r.stop_decision(1, failed, 40), (0, "epoch_cap"))

    def test_generation16_actions_and_context_guard(self):
        class Constant:
            L = 23
            def forward(self, text):
                return None, None, np.array([1., 0., -1.])
        net = Constant()
        result = r.generate(net, "0" * 14)
        self.assertEqual(result["tokens"], "0" * 10)
        self.assertTrue(result["context_exhausted"])
        self.assertFalse(result["cap_exhausted"])
        self.assertNotIn("S", result["tokens"])
        net.L = 100
        result = r.generate(net, "0" * 14)
        self.assertEqual(result["tokens"], "0" * 16)
        self.assertTrue(result["cap_exhausted"])
        self.assertFalse(result["overflow"])

    def test_native_lesson_digest_target_replay_and_full_restore(self):
        global NATIVE_UPDATES, NATIVE_INFERENCE
        if SOURCE is None:
            self.skipTest("Use --engineering --source for native synthetic check")
        cls = r.source_model(Path(SOURCE).read_bytes())
        primary = cls(950041, L=23, H=69)
        replay = copy.deepcopy(primary)
        row = {"input_id": 0, "Q": "010", "A": "01"}
        a, b = r.EpochTrace(), r.EpochTrace()
        r.one_lesson(primary, row, a, False)
        NATIVE_UPDATES += 3
        r.one_lesson(replay, row, b, True)
        NATIVE_UPDATES += 3
        self.assertEqual(a.result(), b.result())
        self.assertTrue(r.equal_state(r.full_state(primary), r.full_state(replay)))
        restored = r.restore(cls, r.read_npz(r.npz_bytes(r.full_state(primary))))
        self.assertTrue(r.equal_state(r.full_state(primary), r.full_state(restored)))
        before = restored.state()
        calls = restored.inference_calls
        r.probe(restored, [{"input_id": 0, "op": 0, "value": 0, "Q": "010", "A": "01"}])
        NATIVE_INFERENCE += restored.inference_calls - calls
        self.assertTrue(r.equal_state(before, restored.state()))

    def test_zero_optimizer_epoch_checkpoint_stop_and_replay(self):
        global MOCK_TARGETS, MOCK_PROBES
        if SOURCE is None:
            self.skipTest("Use --engineering --source for mock orchestration check")
        native = r.source_model(Path(SOURCE).read_bytes())
        class Mock(native):
            def step(self, prefix, target):
                global MOCK_TARGETS
                MOCK_TARGETS += 1
                self.t += 1
                self.train_macs += 6969
                return target, .25
        def mock_probe(net, pool):
            global MOCK_PROBES
            MOCK_PROBES += 1
            net.inference_calls += 5120
            net.inference_macs += 5120 * 3381
            return {"scores": {str(op): {"whole_correct": 256, "questions": 256} for op in (0, 1)},
                    "rows": [{"input_id": row["input_id"], "op": row["op"], "value": row["value"], "tokens": row["A"] + "S",
                              "overflow": False, "context_exhausted": False, "cap_exhausted": False, "whole_correct": True} for row in pool],
                    "inference_calls": 5120, "inference_dense_MAC": 5120 * 3381}
        pool = r.question_pool()
        initial = r.full_state(Mock(950042, L=23, H=69))
        course, _ = r.schedule(950042)
        with tempfile.TemporaryDirectory(prefix="full-domain-mock-") as folder, patch.object(r, "probe", mock_probe), contextlib.redirect_stdout(io.StringIO()):
            r.run_seed(Mock, initial, course, pool, Path(folder), 950042)
            r.run_seed(Mock, initial, course, pool, Path(folder), 950042, replay=True)
            summary = r.read(Path(folder) / "seed950042/training-summary.json")
            self.assertEqual(summary["epochs"], 2)
            self.assertEqual(summary["streak"], 2)
            self.assertEqual(summary["training_updates"], 10240)
            self.assertEqual(summary["stop_reason"], "two_consecutive_full_training_passes")

    def test_cost_formula_and_approval_gate(self):
        p = r.protocol()
        self.assertEqual(p["maximum_updates_per_seed"], 204800)
        self.assertEqual(204800 * 6969, 1427251200)
        self.assertEqual(p["replay_seeds"], [101])
        with tempfile.TemporaryDirectory(prefix="full-domain-gate-") as folder:
            path = Path(folder) / "manifest.json"
            r.write(path, {})
            with self.assertRaisesRegex(AssertionError, "approved manifest"):
                r.validate_inputs(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
