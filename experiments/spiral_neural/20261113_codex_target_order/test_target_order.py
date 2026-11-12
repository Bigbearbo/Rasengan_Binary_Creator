"""Offline/synthetic checks; never fit formal rows or score formal heldout."""
from collections import Counter
import tempfile
from pathlib import Path
import unittest
import numpy as np
import run_target_order as run


class Engineering(unittest.TestCase):
    def test_pool_keeps_occurrences_and_excludes_heldout(self):
        rows = [{"id": "a", "split": "train", "Q": "010", "A": "01", "target_n": 1},
                {"id": "b", "split": "train", "Q": "010", "A": "01", "target_n": 1},
                {"id": "hidden", "split": "heldout", "Q": "111", "A": "1", "target_n": 1}]
        pool = run.target_pool(rows)
        self.assertEqual(len(pool), 6)
        self.assertEqual([row["position"] for row in pool], [0, 1, 2, 0, 1, 2])
        self.assertEqual(run.target_multiset(pool), Counter({("010", "0"): 2, ("0100", "1"): 2, ("01001", "S"): 2}))
        self.assertTrue(all(row["row_id"] != "hidden" for row in pool))

    def test_exact_rng_orders_and_npz_roundtrip(self):
        pool = run.target_pool([{"id": "a", "split": "train", "Q": "010", "A": "01", "target_n": 1}])
        orders, descriptions, payload = run.make_schedules(pool, [101, 202, 303], 4, 81000)
        repeated, metadata, raw = run.make_schedules(pool, [101, 202, 303], 4, 81000)
        self.assertEqual(metadata, descriptions)
        self.assertEqual(payload, raw)
        for seed in (101, 202, 303):
            rng = np.random.default_rng(seed + 81000)
            expected = np.stack([rng.permutation(3) for _ in range(4)])
            self.assertTrue(np.array_equal(orders[f"seed{seed}"], expected))
            self.assertTrue(np.array_equal(repeated[f"seed{seed}"], expected))
        with np.load(run.io.BytesIO(payload), allow_pickle=False) as archive:
            for key, value in orders.items():
                self.assertEqual(archive[key].dtype.str, "<i8")
                self.assertEqual(run.array_sha(value), descriptions[key[4:]]["array_sha256"])

    def test_apply_target_passes_only_prefix_and_label(self):
        class Fake:
            L, t, train_macs, inference_calls, inference_macs = 80, 0, 0, 0, 0
            calls = []
            def step(self, prefix, label):
                self.calls.append((prefix, label))
                self.t += 1
                self.train_macs += 21056
                return "0", 1.25
        class Trace:
            values = []
            def observe(self, value):
                self.values.append(value)
        class Learner:
            @staticmethod
            def full_state(net):
                return {"t": np.array(net.t)}
            @staticmethod
            def state_sha(state):
                return run.array_sha(state["t"])
        net, trace = Fake(), Trace()
        item = {"index": 5, "row_id": "synthetic", "position": 2, "prefix": "01001", "target": "S", "target_n": 1}
        run.apply_target(net, item, 1, 0, trace, Learner)
        self.assertEqual(net.calls, [("01001", "S")])
        self.assertEqual(trace.values[0]["global_update"], 1)
        self.assertEqual(trace.values[0]["train_dense_MAC"], 21056)

    def test_manifest_approval_rejects_before_source_import(self):
        with tempfile.TemporaryDirectory(prefix="target-order-test-") as folder:
            path = Path(folder) / "manifest.json"
            run.write(path, {})
            with self.assertRaisesRegex(AssertionError, "approved manifest"):
                run.validate_manifest("not-a-source", "not-a-control", path, "0" * 64)

    def test_protocol_budget_and_fixed_gate(self):
        p = run.protocol()
        self.assertEqual(128 * 212, p["targets_per_seed"])
        self.assertEqual(27136 * 64 * (4 * 80 + 9), p["training_dense_MAC_per_seed"])
        self.assertEqual(p["including_replay_targets"], 2 * p["primary_targets_all_seeds"])
        self.assertEqual(p["target_schedule"]["seed_offset"], 81000)


if __name__ == "__main__":
    unittest.main()
