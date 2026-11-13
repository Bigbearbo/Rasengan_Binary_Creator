"""Bounded single-eta engineering; no trained-parent forward or optimizer call."""
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import run_stability as r

CONTENTS = DATA = None
SYNTHETIC_UPDATES = SYNTHETIC_FORWARD = 0


class Engineering(unittest.TestCase):
    def test_public_inputs_mapping_and_orders(self):
        f2, _, _, rows, parents, controls, orders, info, proof, a, b = DATA
        self.assertEqual(len(rows), 3600)
        self.assertEqual(proof["unique_changed_float_constant"], {"before": .003, "after": .001})
        self.assertTrue(proof["entire_AST_equal_after_reversing_one_leaf"])
        self.assertNotEqual(a, b)
        for seed in r.protocol()["seeds"]:
            key = str(seed)
            self.assertEqual(int(parents[key]["t"]), r.protocol()["start_t"][key])
            self.assertEqual(int(controls[key]["t"]) - int(parents[key]["t"]), 36000)
            self.assertEqual(orders[key].shape, (36000, 2))
            pool = f2.target_pool(rows)
            self.assertEqual(sorted(map(tuple, orders[key].tolist())), sorted(map(tuple, pool.tolist())))
            self.assertEqual(info[key]["historical_control_lost"], r.protocol()["historical_control_lost_QIDs"][key])

    def test_native_eta003_exact_and_eta001_formula_nonzero_moments(self):
        global SYNTHETIC_UPDATES, SYNTHETIC_FORWARD
        f2, original, changed = DATA[:3]
        native = f2.source_model(CONTENTS["source/p030_binary_continual.py"])
        template = f2.full_state(native(882, L=80, H=64))
        rng = np.random.default_rng(884)
        template["t"] = np.array(400500, dtype=np.int64)
        for i in range(4):
            template[f"m{i}"] = rng.normal(0, .003, template[f"m{i}"].shape).astype(np.float32)
            template[f"v{i}"] = rng.uniform(.001, .002, template[f"v{i}"].shape).astype(np.float32)
            array = template[f"birth{i}"]
            array[:] = np.asarray([0, 400499, 400489], np.int64)[np.arange(array.size).reshape(array.shape) % 3]
        template["meta_train_macs"] = np.array(400500 * 21056, np.int64)
        nets = [f2.restore(cls, template) for cls in (native, original, changed)]
        observations = []
        for net in nets:
            before_t = net.t
            try:
                observations.append(net.step("010110001001010101001101010100010101011", "1"))
            finally:
                SYNTHETIC_UPDATES += net.t - before_t
                SYNTHETIC_FORWARD += 1
        self.assertEqual(observations[0], observations[1])
        self.assertEqual(observations[0], observations[2])
        self.assertTrue(f2.equal_state(f2.full_state(nets[0]), f2.full_state(nets[1])))
        for i in range(4):
            self.assertTrue(np.array_equal(nets[0].m[i], nets[2].m[i]))
            self.assertTrue(np.array_equal(nets[0].v[i], nets[2].v[i]))
            self.assertTrue(np.array_equal(nets[2].birth[i], template[f"birth{i}"]))
            age = nets[2].t - template[f"birth{i}"]
            expected = template[f"p{i}"].copy()
            expected -= .001 * (nets[2].m[i] / (1 - np.power(.9, age))) / (np.sqrt(nets[2].v[i] / (1 - np.power(.999, age))) + 1e-8)
            self.assertTrue(np.array_equal(nets[2].p[i], expected))
            self.assertEqual(nets[2].p[i].dtype, np.float32)
        self.assertTrue(any(not np.array_equal(a, b) for a, b in zip(nets[0].p, nets[2].p)))
        for net in nets:
            self.assertEqual(net.t, 400501)
            self.assertEqual(net.train_macs - int(template["meta_train_macs"]), 21056)
            saved = f2.full_state(net)
            self.assertTrue(f2.equal_state(saved, f2.full_state(f2.restore(type(net), saved))))
            for key in ("growth_rng", "meta_events", "meta_inference_calls", "meta_inference_macs"):
                self.assertTrue(np.array_equal(saved[key], template[key]))

    def test_all_baselines_before_any_step_and_integrity_abort(self):
        events = []
        def fake_baseline(*args):
            seed = args[-1]
            events.append(seed)
            if seed == 202:
                raise AssertionError("synthetic integrity rejection")
            return {}, {}
        parents = {str(s): {} for s in (101, 202, 303)}
        content = {f"initial/seed{s}.npz": b"synthetic" for s in (101, 202, 303)}
        content.update({f"historical/seed{s}/start-generation.json": b"{}" for s in (101, 202, 303)})
        with patch.object(r, "baseline_one", side_effect=fake_baseline):
            with self.assertRaisesRegex(AssertionError, "synthetic integrity"):
                r.all_baselines(None, None, parents, content, [], None, [101, 202, 303])
        self.assertEqual(events, [101, 202])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "attempt"
            fake_data = (None, None, None, [], parents, {}, {}, {}, {}, "", "")
            with patch.object(r, "validate_inputs", return_value=({"source_hashes": {}}, {}, fake_data)), \
                 patch.object(r, "all_baselines", side_effect=AssertionError("synthetic baseline failure")), \
                 patch.object(r, "train_one") as learner:
                with self.assertRaisesRegex(AssertionError, "baseline failure"):
                    r.execute(None, "a" * 64, "b" * 40, output)
                learner.assert_not_called()
            self.assertTrue(r.read(output / "failure.json")["zero_new_updates_guaranteed"])
        self.assertTrue(r.exact_all({name: {"questions": 900, "whole_correct": 900} for name in r.CLASSES}))
        bad = {name: {"questions": 900, "whole_correct": 900 - (name == "F2")} for name in r.CLASSES}
        self.assertFalse(r.exact_all(bad))

    def test_qid_aligned_ties_lost_sets_and_betweenarm(self):
        f2 = DATA[0]
        rows = [{"question_id": i, "class": name, "A": "000000"} for i, name in enumerate(r.CLASSES)]
        before = [{"question_id": row["question_id"], "tokens": row["A"] + "S"} for row in rows]
        new, old = copy.deepcopy(before), copy.deepcopy(before)
        new[0]["tokens"], old[1]["tokens"] = "100000S", "100000S"
        result = r.paired_metrics(f2, rows, before, new[::-1], old[::-1])
        self.assertEqual(result["new_total_lost"], 1)
        self.assertEqual(result["historical_control_total_lost"], 1)
        self.assertFalse(result["directional_hypothesis_pass"])
        self.assertEqual(result["by_class"]["E1"]["between_arm_QIDs"]["control_only_correct"], [0])
        self.assertEqual(result["by_class"]["E2"]["between_arm_QIDs"]["new_only_correct"], [1])
        self.assertEqual(result["new_churn"]["by_class"]["E1"]["previous_correct_to_wrong"], 1)
        passing = r.paired_metrics(f2, rows, before, before, old)
        self.assertTrue(passing["directional_hypothesis_pass"])
        self.assertTrue(passing["new_all_four_classes_full"])
        with self.assertRaises(AssertionError):
            r.paired_metrics(f2, rows, before, before[:-1], old)


def run_checks(parent_root):
    global CONTENTS, DATA
    assert parent_root is not None, "--parent-root verified public PR33 root required"
    CONTENTS, _ = r.collect_public(parent_root)
    DATA = r.inspect_contents(CONTENTS)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Engineering))
    return {"status": "passed" if result.wasSuccessful() else "failed", "tests": result.testsRun, "failures": len(result.failures),
            "errors": len(result.errors), "test_output": stream.getvalue(), "synthetic_optimizer_updates": SYNTHETIC_UPDATES,
            "synthetic_forward_calls": SYNTHETIC_FORWARD, "synthetic_training_dense_MAC": SYNTHETIC_UPDATES * 21056,
            "trained_parent_forward_calls": 0, "new_parent_optimizer_calls": 0, "external_model_calls": 0,
            "AST_change": DATA[8], "public_mapping_and_frozen_next_orders_verified": True}
