"""Five bounded E3 engineering checks; trained forward/step calls are forbidden."""
import ast
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import run_probe as r

CONTENTS = DATA = None
SYNTHETIC_UPDATES = SYNTHETIC_FORWARD = MOCK_COUNTER_INCREMENTS = 0


class Engineering(unittest.TestCase):
    def test_grammar_third_word_and_three_exact_courses(self):
        h, _, rows, _, _, _, _, _, _, checks = DATA
        p = r.protocol()
        old = r.json.loads(CONTENTS["parent-questions.json"])
        self.assertEqual(rows[:3600], old)
        self.assertEqual(checks["teacher_targets"], 53100)
        self.assertEqual(checks["unique_teacher_prefixes"], 53100)
        self.assertEqual([checks["by_class"][name]["targets"] for name in p["classes"]], [6300, 11700, 6300, 11700, 17100])
        self.assertEqual(checks["by_class"]["E3"]["STOP_prefix_length"], 57)
        for row in rows[3600:]:
            old_echo2 = old[900 + row["pair_id"]]
            self.assertEqual(row["Q"][:5], old_echo2["Q"][:5])
            self.assertEqual(row["Q"][5:9], "0110")
            self.assertEqual(row["Q"][9:], old_echo2["Q"][9:])
            self.assertEqual(len(row["A"] + "S"), 19)
            self.assertEqual(row["A"][12:18], r.word(row["payload"][2]))
        with self.assertRaises(AssertionError):
            r.encode("100", 3, rows[0]["payload"])
        with self.assertRaises(AssertionError):
            r.encode("010", 4, rows[0]["payload"])
        pool = r.target_pool(rows, p["classes"])
        for seed in p["seeds"]:
            a, state = r.shuffled_order(pool, seed + 666000)
            b, state2 = r.shuffled_order(pool, seed + 666000)
            self.assertTrue(np.array_equal(a, b))
            self.assertEqual(state, state2)
            self.assertEqual(sorted(map(tuple, a.tolist())), sorted(map(tuple, pool.tolist())))
            self.assertEqual(a.dtype.str, "<u2")
        self.assertEqual(6 * len(pool) * 21056, 6708441600)

    def test_native_eta_formulas_nonzero_moments_heterogeneous_birth(self):
        global SYNTHETIC_UPDATES, SYNTHETIC_FORWARD
        h, classes = DATA[:2]
        source = ast.parse(CONTENTS["source/p030_binary_continual.py"].decode("utf-8"))
        node = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == "Model")
        namespace = {"np": np, "json": r.json}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<native-unmodified-P030>", "exec"), namespace)
        native = namespace["Model"]
        template = h.full_state(native(882, L=80, H=64))
        template["t"], template["meta_train_macs"] = np.array(400500, np.int64), np.array(400500 * 21056, np.int64)
        rng = np.random.default_rng(885)
        for i in range(4):
            template[f"m{i}"] = rng.normal(0, .003, template[f"m{i}"].shape).astype(np.float32)
            template[f"v{i}"] = rng.uniform(.001, .002, template[f"v{i}"].shape).astype(np.float32)
            birth = template[f"birth{i}"]
            birth[:] = np.asarray([0, 400499, 400489], np.int64)[np.arange(birth.size).reshape(birth.shape) % 3]
        nets = [h.restore(cls, template) for cls in (native, classes["eta003"], classes["eta001"])]
        observed = []
        for net in nets:
            before = net.t
            try:
                observed.append(net.step("010110001001010101001101010100010101011", "1"))
            finally:
                SYNTHETIC_UPDATES += net.t - before
                SYNTHETIC_FORWARD += 1
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(observed[0], observed[2])
        self.assertTrue(h.equal_state(h.full_state(nets[0]), h.full_state(nets[1])))
        for i in range(4):
            self.assertTrue(np.array_equal(nets[1].m[i], nets[2].m[i]))
            self.assertTrue(np.array_equal(nets[1].v[i], nets[2].v[i]))
            for net, eta in ((nets[1], .003), (nets[2], .001)):
                age = net.t - template[f"birth{i}"]
                expected = template[f"p{i}"].copy()
                expected -= eta * (net.m[i] / (1 - np.power(.9, age))) / (np.sqrt(net.v[i] / (1 - np.power(.999, age))) + 1e-8)
                self.assertTrue(np.array_equal(net.p[i], expected))
                self.assertEqual(net.p[i].dtype, np.float32)
                self.assertTrue(np.array_equal(net.birth[i], template[f"birth{i}"]))
        for net in nets:
            self.assertEqual(net.t, 400501)
            saved = h.full_state(net)
            for key in ("growth_rng", "meta_events", "meta_inference_calls", "meta_inference_macs"):
                self.assertTrue(np.array_equal(saved[key], template[key]))

    def test_mock_shared_baseline_once_and_exact_arm_clones(self):
        global MOCK_COUNTER_INCREMENTS
        h, classes, rows, parents = DATA[:4]
        events = []
        def fake_probe(hh, net, part, names):
            nonlocal events
            global MOCK_COUNTER_INCREMENTS
            events.append(("old" if len(names) == 4 else "cold", net.seed))
            outputs = [{"question_id": row["question_id"], "class": row["class"], "pair_id": row["pair_id"],
                        "tokens": row["A"] + "S", "context_exhausted": False, "cap_exhausted": False, "whole_correct": True} for row in part]
            calls = sum(len(row["A"]) + 1 for row in part)
            net.inference_calls += calls
            net.inference_macs += calls * 10432
            MOCK_COUNTER_INCREMENTS += calls
            return {"scores": {name: {"questions": 900, "whole_correct": 900} for name in names}, "rows": outputs,
                    "inference_calls": calls, "inference_dense_MAC": calls * 10432}
        def fake_TF(hh, net, part, free, names):
            global MOCK_COUNTER_INCREMENTS
            events.append(("TF", net.seed))
            calls = sum(len(row["A"]) + 1 for row in part)
            net.inference_calls += calls
            net.inference_macs += calls * 10432
            MOCK_COUNTER_INCREMENTS += calls
            return {"inference_calls": calls, "inference_dense_MAC": calls * 10432}
        cls = classes["eta001"]
        with tempfile.TemporaryDirectory() as directory, patch.object(cls, "forward", side_effect=AssertionError("trained forward forbidden")), \
             patch.object(cls, "step", side_effect=AssertionError("trained optimizer forbidden")), patch.object(r, "probe", side_effect=fake_probe), \
             patch.object(r, "teacher_forced", side_effect=fake_TF):
            folder = Path(directory)
            old_states, old_records = r.all_old_baselines(h, cls, parents, CONTENTS, rows, folder, r.protocol()["seeds"])
            shared, records = r.all_cold_baselines(h, cls, parents, old_states, old_records, rows, folder, r.protocol()["seeds"])
            self.assertEqual(events[:3], [("old", 101), ("old", 202), ("old", 303)])
            self.assertEqual(sum(record["physical_shared_baseline_inference_calls"] for record in records.values()), 3 * (36000 + 17100 + 17100))
            for seed in r.protocol()["seeds"]:
                key = str(seed)
                a, b = (h.restore(classes[arm], shared[key]) for arm in ("eta001", "eta003"))
                self.assertTrue(h.equal_state(h.full_state(a), h.full_state(b)))
                self.assertTrue(r.learning_unchanged(h, parents[key], shared[key]))
                self.assertTrue(records[key]["baseline_ceiling"])

    def test_old_gate_abort_prevents_cold_and_optimizer(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = (None, {"eta001": None}, [], {}, {}, {}, {}, "", "", {})
            with patch.object(r, "validate_inputs", return_value=({"source_hashes": {}}, {}, fake)), \
                 patch.object(r, "all_old_baselines", side_effect=AssertionError("synthetic integrity failure")), \
                 patch.object(r, "all_cold_baselines") as cold, patch.object(r, "train_arm") as train:
                with self.assertRaisesRegex(AssertionError, "synthetic integrity"):
                    r.execute(None, "a" * 64, "b" * 40, Path(directory) / "attempt")
                cold.assert_not_called()
                train.assert_not_called()
            self.assertTrue(r.read(Path(directory) / "attempt/failure.json")["zero_new_updates_guaranteed"])

    def test_thirdword_metrics_paired_axes_and_ceiling(self):
        names, old_names = r.protocol()["classes"], r.protocol()["old_classes"]
        rows = [{"question_id": i, "class": name, "A": "000000" if name != "E3" else "000000111110001010"} for i, name in enumerate(names)]
        cold = [{"question_id": row["question_id"], "tokens": row["A"] + "S"} for row in rows]
        low, high = copy.deepcopy(cold), copy.deepcopy(cold)
        low[-1]["tokens"] = rows[-1]["A"][:12] + "S"
        high[0]["tokens"] = "100000S"
        metrics = r.token_metrics(rows, low, names)
        self.assertEqual(metrics["by_class"]["E3"]["words"]["word3"]["questions"], 1)
        self.assertEqual(metrics["by_class"]["E3"]["words"]["word3"]["complete6_correct"], 0)
        self.assertEqual(metrics["by_class"]["E3"]["words"]["word1"]["complete6_correct"], 1)
        wrong = r.token_metrics(rows, high, names)["per_question"][0]
        self.assertEqual(wrong["first_error_position_zero_based"], 0)
        pair = r.paired_arms(rows, cold, low[::-1], high[::-1], names, old_names)
        self.assertEqual(pair["axes_eta001_minus_eta003"], {"old_lost": -1, "E3_whole_gain": -1})
        self.assertTrue(pair["eta001"]["baseline_ceiling"])
        self.assertFalse(pair["eta001"]["strict_feasibility"])
        self.assertEqual(r.feasibility_interpretation([pair["eta001"]])["overall_interpretation"], "not_identifiable_ceiling")
        before = copy.deepcopy(cold)
        before[-1]["tokens"] = "S"
        gain = r.arm_feasibility(rows, before, cold, names, old_names)
        self.assertTrue(gain["strict_feasibility"])
        self.assertEqual(gain["E3_whole_gain"], 1)
        self.assertEqual(gain["churn"]["by_class"]["E3"]["QIDs"]["previous_wrong_to_correct"], [4])


def run_checks(parent_root):
    global CONTENTS, DATA
    assert parent_root is not None
    CONTENTS, _ = r.collect_public(parent_root)
    DATA = r.inspect_contents(CONTENTS, require_orders=False)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Engineering))
    return {"status": "passed" if result.wasSuccessful() else "failed", "tests": result.testsRun, "failures": len(result.failures),
            "errors": len(result.errors), "test_output": stream.getvalue(), "synthetic_optimizer_updates": SYNTHETIC_UPDATES,
            "synthetic_forward_calls": SYNTHETIC_FORWARD, "synthetic_training_dense_MAC": SYNTHETIC_UPDATES * 21056,
            "mock_inference_counter_increments_not_actual_forwards": MOCK_COUNTER_INCREMENTS,
            "trained_model_forward_calls": 0, "trained_parent_optimizer_calls": 0, "external_model_calls": 0, "AST_change": DATA[6]}
