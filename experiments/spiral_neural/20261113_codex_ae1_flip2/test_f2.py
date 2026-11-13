"""Parent byte/metadata checks and bounded synthetic updates; never formal parentNNforward."""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import run_f2 as r

SOURCE = PARENT_ROOT = None
NATIVE_UPDATES = NATIVE_FORWARD = MOCK_TARGETS = MOCK_PROBES = 0


def fixtures():
    bank = r.expected_bank()
    old = [{"question_id": (take - 1) * 900 + pair, "pair_id": pair, "r": take, "payload": payload,
            "Q": r.encode("010", take, payload), "A": "".join(r.word(x) for x in payload[:take]), "class": "E1" if take == 1 else "E2", "op": "010"}
           for take in (1, 2) for pair, payload in enumerate(bank)]
    old.extend({"question_id": 1800 + pair, "pair_id": pair, "r": 1, "payload": payload,
                "Q": r.encode("100", 1, payload), "A": r.flip_answer(payload), "class": "F1", "op": "100"} for pair, payload in enumerate(bank))
    return bank, old, r.questions(bank, old)


class Engineering(unittest.TestCase):
    def test_old_Echo_exact_profile_and_no_aliases(self):
        bank, old, rows = fixtures()
        checks = r.data_checks(bank, rows, old)
        self.assertEqual(checks["questions"], 3600)
        self.assertEqual(checks["old_QA_unchanged"], 2700)
        self.assertEqual(checks["unique_teacher_prefixes"], 36000)
        self.assertEqual(len({row["Q"] for row in rows}), 3600)
        for qid in range(2700):
            self.assertEqual(rows[qid], old[qid])
        for row in rows:
            self.assertEqual(row["Q"][:2], "01")
            self.assertEqual(row["Q"][2:5], row["op"])
            self.assertEqual(row["Q"][5:9], format(row["r"], "03b") + "0")
            self.assertEqual(row["Q"][-6:], "111100")
            self.assertEqual(len(row["Q"]), 39)
        with self.assertRaises(AssertionError):
            r.encode("100", 3, bank[0])

    def test_literal_control_like_answers_keep0_and1(self):
        _, _, rows = fixtures()
        self.assertEqual(rows[1800]["A"] + "S", "111110S")
        self.assertEqual(rows[1830]["A"] + "S", "111100S")
        self.assertEqual(rows[2670]["A"] + "S", "000100S")
        self.assertEqual(rows[2700]["A"] + "S", "111110111110S")
        self.assertEqual(rows[2701]["A"] + "S", "111110111100S")
        self.assertEqual(rows[2730]["A"] + "S", "111100111110S")
        self.assertEqual(sum(row["payload"][0] == 0 for row in rows[2700:]), 30)
        self.assertEqual(sum(row["payload"][1] == 1 for row in rows[2700:]), 30)
        for row in rows[1800:]:
            for slot in range(row["r"]):
                self.assertTrue(all(a != b for a, b in zip(row["A"][slot * 6:slot * 6 + 5], r.word(row["payload"][slot])[:5])))
                self.assertEqual(row["A"][slot * 6 + 5], "0")
            self.assertEqual(row["A"][-1], "0")
            self.assertEqual(len(row["Q"] + row["A"]), 39 + 6 * row["r"])
        with self.assertRaises(AssertionError):
            r.word(31)

    def test_all40_target_courses_and_unequal_class_weighting(self):
        _, _, rows = fixtures()
        pool = r.target_pool(rows)
        self.assertEqual(pool[:40].tolist(), [[0, x] for x in range(7)] + [[900, x] for x in range(13)] + [[1800, x] for x in range(7)] + [[2700, x] for x in range(13)])
        self.assertEqual([int(((pool[:, 0] // 900) == index).sum()) for index in range(4)], [6300, 11700, 6300, 11700])
        expected_keys = np.sort(pool[:, 0].astype(np.int64) * 16 + pool[:, 1])
        for seed in (101, 202, 303):
            course, final_rng = r.schedules(seed, rows)
            rng = np.random.default_rng(seed + 555000)
            self.assertEqual(course.shape, (40, 36000, 2))
            self.assertEqual(course.dtype.str, "<u2")
            for order in course:
                self.assertTrue(np.array_equal(order, pool[rng.permutation(len(pool))]))
                self.assertTrue(np.array_equal(np.sort(order[:, 0].astype(np.int64) * 16 + order[:, 1]), expected_keys))
            self.assertEqual(final_rng, rng.bit_generator.state)

    def test_parent_public_bytes_and_full_restore_without_forward(self):
        if SOURCE is None or PARENT_ROOT is None:
            self.skipTest("Use --engineering --source --parent-root")
        source = Path(SOURCE).read_bytes()
        cls = r.source_model(source)
        contents, parents, proof = r.parent_inputs(PARENT_ROOT, source)
        self.assertEqual(r.verify_parent_provenance(contents), proof)
        for seed in (101, 202, 303):
            raw = contents[parents[str(seed)]["file"]]
            saved = r.read_npz(raw)
            restored = r.restore(cls, saved)
            self.assertTrue(r.equal_state(saved, r.full_state(restored)))
            self.assertEqual(r.state_sha(saved), parents[str(seed)]["full_state_sha256"])
            self.assertEqual(restored.t, r.protocol()["parent_t"][str(seed)])
            self.assertEqual(r.sha(raw), parents[str(seed)]["source_member"]["sha256"])

    def test_three_parent_baseline_gate_aborts_before_first_update(self):
        calls = []
        def fake_baseline(cls, parent, raw, rows, output, seed, replay=False):
            calls.append(seed)
            if seed == 303:
                raise AssertionError("synthetic Echo integrity failure")
            return {}, {}
        prepared = ({"protocol": {"seeds": [101, 202, 303]}}, None, [], {str(x): {} for x in (101, 202, 303)},
                    {str(x): b"" for x in (101, 202, 303)}, {})
        with tempfile.TemporaryDirectory(prefix="mixed-all-parent-gate-") as directory, patch.object(r, "validate_inputs", return_value=prepared), patch.object(r, "baseline_one", fake_baseline), patch.object(r, "train_one") as train:
            out = Path(directory) / "out"
            with self.assertRaisesRegex(AssertionError, "Echo integrity"):
                r.execute("unused", "unused", "1" * 40, out)
            self.assertEqual(calls, [101, 202, 303])
            train.assert_not_called()
            self.assertTrue(r.read(out / "failure.json")["zero_new_updates_guaranteed"])

    def test_cap32_no_forced_STOP_and_gate_streak(self):
        class Constant:
            L = 80
            def forward(self, text):
                return None, None, np.array([1., 0., -1.])
        net = Constant()
        generated = r.generate(net, "0" * 39)
        self.assertEqual(generated["tokens"], "0" * 32)
        self.assertTrue(generated["cap_exhausted"])
        self.assertNotIn("S", generated["tokens"])
        net.L = 45
        self.assertTrue(r.generate(net, "0" * 39)["context_exhausted"])
        good = {name: {"questions": 900, "whole_correct": 900} for name in ("E1", "E2", "F1", "F2")}
        bad = copy.deepcopy(good)
        bad["E1"]["whole_correct"] = 899
        self.assertEqual(r.stop_decision(0, good, 1)[:2], (1, None))
        self.assertEqual(r.stop_decision(1, bad, 2)[:2], (0, None))
        self.assertEqual(r.stop_decision(1, good, 3)[:2], (2, "two_consecutive_all_class_passes"))
        self.assertEqual(r.stop_decision(0, good, 40)[:2], (1, "epoch_cap"))

    def test_native_six_tiny_updates_continue_moments_and_exact_replay(self):
        global NATIVE_UPDATES, NATIVE_FORWARD
        if SOURCE is None:
            self.skipTest("Use --engineering --source")
        cls = r.source_model(Path(SOURCE).read_bytes())
        original = cls(970061, L=80, H=64)
        original.t, original.train_macs = 17, 17 * 21056
        original.inference_calls, original.inference_macs = 11, 11 * 10432
        for a in original.m:
            a[:] = .01
        for a in original.v:
            a[:] = .02
        saved = r.full_state(original)
        primary, replay = r.restore(cls, saved), r.restore(cls, saved)
        traces = [r.EpochTrace(), r.EpochTrace()]
        for net, trace in zip((primary, replay), traces):
            for pos in (2, 0, 1):
                pred, loss = net.step("010" + "01"[:pos], "01S"[pos])
                trace.observe(0, pos, pred, loss, "01S"[pos])
                NATIVE_UPDATES += 1
        self.assertEqual(traces[0].result(), traces[1].result())
        self.assertTrue(r.equal_state(r.full_state(primary), r.full_state(replay)))
        self.assertEqual(primary.t - int(saved["t"]), 3)
        self.assertEqual(primary.train_macs - int(saved["meta_train_macs"]), 3 * 21056)
        roundtrip = r.restore(cls, r.read_npz(r.npz_bytes(r.full_state(primary))))
        self.assertTrue(r.equal_state(r.full_state(primary), r.full_state(roundtrip)))
        before = roundtrip.state()
        calls = roundtrip.inference_calls
        r.generate(roundtrip, "010")
        NATIVE_FORWARD += roundtrip.inference_calls - calls
        self.assertTrue(r.equal_state(before, roundtrip.state()))

    def test_mock_baseline_carry_delta_and_baseline_not_in_streak(self):
        global MOCK_TARGETS, MOCK_PROBES
        if SOURCE is None:
            self.skipTest("Use --engineering --source")
        native = r.source_model(Path(SOURCE).read_bytes())
        class Mock(native):
            def step(self, prefix, label):
                global MOCK_TARGETS
                MOCK_TARGETS += 1
                self.t += 1
                self.train_macs += 21056
                return label, .25
        _, _, rows = fixtures()
        seed = 970062
        parent = Mock(seed, L=80, H=64)
        parent.t, parent.train_macs = 123, 123 * 21056
        parent.inference_calls, parent.inference_macs = 77, 77 * 10432
        saved = r.full_state(parent)
        raw = r.npz_bytes(saved)
        def mock_probe(net, questions):
            global MOCK_PROBES
            MOCK_PROBES += 1
            count = sum(len(row["A"]) + 1 for row in questions)
            net.inference_calls += count
            net.inference_macs += count * 10432
            return {"scores": {name: {"questions": 900, "whole_correct": 900} for name in ("E1", "E2", "F1", "F2")},
                    "rows": [{"question_id": row["question_id"], "class": row["class"], "pair_id": row["pair_id"], "tokens": row["A"] + "S", "whole_correct": True} for row in questions],
                    "inference_calls": count, "inference_dense_MAC": count * 10432}
        course, _ = r.schedules(seed, rows)
        with tempfile.TemporaryDirectory(prefix="mixed-mock-delta-") as directory, patch.object(r, "probe", mock_probe), contextlib.redirect_stdout(io.StringIO()):
            out = Path(directory)
            baseline, record = r.baseline_one(Mock, saved, raw, rows, out, seed)
            self.assertEqual(record["baseline_streak"], 0)
            self.assertEqual(record["new_optimizer_updates"], 0)
            self.assertEqual(int(baseline["t"]), 123)
            self.assertEqual(int(baseline["meta_inference_calls"]), 77 + 36000)
            self.assertEqual((out / f"seed{seed}/initial-state.npz").read_bytes(), raw)
            r.train_one(Mock, saved, baseline, record, course, rows, out, seed)
            summary = r.read(out / f"seed{seed}/training-summary.json")
            self.assertEqual(summary["epochs"], 2)
            self.assertEqual(summary["new_updates"], 72000)
            self.assertEqual(summary["new_training_dense_MAC"], 72000 * 21056)
            self.assertEqual(summary["new_probe_inference_calls"], 72000)
            self.assertEqual(summary["baseline_inference_calls"], 36000)
            self.assertEqual(summary["total_counters_before_finalTF"]["t"], 123 + 72000)
            self.assertEqual(summary["total_counters_before_finalTF"]["inference_calls"], 77 + 36000 + 72000)

    def test_metrics_word_slots_missing_extra_firsterror_and_churn_swaps(self):
        _, _, all_rows = fixtures()
        rows = all_rows[2700:2702]
        expected = [row["A"] + "S" for row in rows]
        current = [{"question_id": rows[0]["question_id"], "tokens": expected[0]},
                   {"question_id": rows[1]["question_id"], "tokens": "S"}]
        with patch.object(r, "generate", side_effect=AssertionError("metrics must not call NN")):
            metrics = r.token_metrics(rows, current)
            self.assertEqual(metrics["per_question"][1]["first_error_position_zero_based"], 0)
            self.assertEqual(metrics["per_question"][1]["first_error_kind"], "early_STOP")
            self.assertEqual(metrics["per_question"][1]["termination_kind"], "early_STOP")
            self.assertEqual(metrics["by_class"]["F2"]["words"]["word1"]["complete6_correct"], 1)
            self.assertEqual(metrics["by_class"]["F2"]["words"]["word2"]["complete6_correct"], 1)
            missing = [{"question_id": rows[0]["question_id"], "tokens": rows[0]["A"][:6] + "S"}, current[1]]
            detail = r.token_metrics(rows, missing)["per_question"][0]
            self.assertTrue(detail["words"][0]["complete6_correct"])
            self.assertFalse(detail["words"][1]["complete6_correct"])
            self.assertFalse(detail["words"][1]["tail0_correct"])
            self.assertEqual(detail["first_error_position_zero_based"], 6)
            self.assertFalse(detail["STOP_position_correct"])
            extra = [{"question_id": rows[0]["question_id"], "tokens": expected[0] + "0"}, current[1]]
            detail = r.token_metrics(rows, extra)["per_question"][0]
            self.assertEqual(detail["first_error_position_zero_based"], len(expected[0]))
            self.assertEqual(detail["first_error_kind"], "extra_token")
            self.assertEqual(detail["termination_kind"], "tokens_after_STOP")
            self.assertEqual(detail["extra_output_positions"], 1)
            missing = [{"question_id": rows[0]["question_id"], "tokens": rows[0]["A"]}, current[1]]
            detail = r.token_metrics(rows, missing)["per_question"][0]
            self.assertEqual(detail["first_error_kind"], "missing_token")
            self.assertEqual(detail["termination_kind"], "no_STOP")
            self.assertEqual(detail["missing_expected_positions"], 1)
            late = [{"question_id": rows[0]["question_id"], "tokens": rows[0]["A"] + "0S"}, current[1]]
            detail = r.token_metrics(rows, late)["per_question"][0]
            self.assertEqual(detail["first_error_kind"], "STOP_expected_bit_emitted")
            self.assertEqual(detail["termination_kind"], "late_STOP")
            for flag in ("cap_exhausted", "context_exhausted"):
                flagged = [{"question_id": rows[0]["question_id"], "tokens": "0" * 32, flag: True}, current[1]]
                detail = r.token_metrics(rows, flagged)["per_question"][0]
                self.assertEqual(detail["termination_kind"], flag)
                self.assertTrue(detail[flag])
            altered = rows[0]["A"][:5] + "1" + rows[0]["A"][6:] + "S"
            detail = r.token_metrics(rows, [{"question_id": rows[0]["question_id"], "tokens": altered}, current[1]])["per_question"][0]
            self.assertTrue(detail["words"][0]["information5_correct"])
            self.assertFalse(detail["words"][0]["tail0_correct"])
            self.assertTrue(detail["words"][1]["complete6_correct"])
            before = [{"question_id": rows[0]["question_id"], "tokens": expected[0]}, {"question_id": rows[1]["question_id"], "tokens": "S"}]
            after = [{"question_id": rows[0]["question_id"], "tokens": "S"}, {"question_id": rows[1]["question_id"], "tokens": expected[1]}]
            churn = r.churn_metrics(rows, before, after)["by_class"]["F2"]
            self.assertEqual(churn["previous_correct_to_wrong"], 1)
            self.assertEqual(churn["previous_wrong_to_correct"], 1)
            self.assertIsNone(r.churn_metrics(rows, None, after)["by_class"]["F2"]["previous_correct_to_wrong"])

    def test_no_formal_training_replay_in_execution(self):
        import ast
        p = r.protocol()
        self.assertEqual(p["replay_seeds"], [])
        code = Path(r.__file__).read_text(encoding="utf-8")
        execute = next(node for node in ast.parse(code).body if isinstance(node, ast.FunctionDef) and node.name == "execute")
        for call in (node for node in ast.walk(execute) if isinstance(node, ast.Call)):
            self.assertFalse(any(item.arg == "replay" and isinstance(item.value, ast.Constant) and item.value.value is True for item in call.keywords))


if __name__ == "__main__":
    unittest.main()
