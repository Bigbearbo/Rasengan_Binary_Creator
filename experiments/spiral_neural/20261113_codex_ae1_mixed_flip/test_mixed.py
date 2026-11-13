"""Parent byte/metadata checks and bounded synthetic updates; never formal parentNNforward."""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import run_mixed as r

SOURCE = PARENT_ROOT = None
NATIVE_UPDATES = NATIVE_FORWARD = MOCK_TARGETS = MOCK_PROBES = 0


def fixtures():
    bank = r.expected_bank()
    old = [{"question_id": (take - 1) * 900 + pair, "pair_id": pair, "r": take, "payload": payload,
            "Q": r.encode("010", take, payload), "A": "".join(r.word(x) for x in payload[:take])}
           for take in (1, 2) for pair, payload in enumerate(bank)]
    return bank, old, r.questions(bank, old)


class Engineering(unittest.TestCase):
    def test_old_Echo_exact_profile_and_no_aliases(self):
        bank, old, rows = fixtures()
        checks = r.data_checks(bank, rows, old)
        self.assertEqual(checks["questions"], 2700)
        self.assertEqual(checks["old_Echo_QA_unchanged"], 1800)
        self.assertEqual(checks["unique_teacher_prefixes"], 24300)
        self.assertEqual(len({row["Q"] for row in rows}), 2700)
        for qid in range(1800):
            self.assertEqual((rows[qid]["Q"], rows[qid]["A"]), (old[qid]["Q"], old[qid]["A"]))
        for row in rows:
            self.assertEqual(row["Q"][:2], "01")
            self.assertEqual(row["Q"][2:5], row["op"])
            self.assertEqual(row["Q"][5:9], format(row["r"], "03b") + "0")
            self.assertEqual(row["Q"][-6:], "111100")
            self.assertEqual(len(row["Q"]), 39)
        with self.assertRaises(AssertionError):
            r.encode("100", 2, bank[0])

    def test_literal_control_like_answers_keep0_and1(self):
        _, _, rows = fixtures()
        self.assertEqual(rows[1800]["A"] + "S", "111110S")
        self.assertEqual(rows[1830]["A"] + "S", "111100S")
        self.assertEqual(rows[2670]["A"] + "S", "000100S")
        self.assertEqual(sum(row["payload"][0] == 0 for row in rows[1800:]), 30)
        self.assertEqual(sum(row["payload"][0] == 1 for row in rows[1800:]), 30)
        for row in rows[1800:]:
            self.assertTrue(all(a != b for a, b in zip(row["A"][:5], r.word(row["payload"][0])[:5])))
            self.assertEqual(row["A"][-1], "0")
            self.assertEqual(len(row["Q"] + row["A"]), 45)
        with self.assertRaises(AssertionError):
            r.word(31)

    def test_all40_target_courses_and_unequal_class_weighting(self):
        _, _, rows = fixtures()
        pool = r.target_pool(rows)
        self.assertEqual(pool[:27].tolist(), [[0, x] for x in range(7)] + [[900, x] for x in range(13)] + [[1800, x] for x in range(7)])
        self.assertEqual([int(((pool[:, 0] // 900) == index).sum()) for index in range(3)], [6300, 11700, 6300])
        expected_keys = np.sort(pool[:, 0].astype(np.int64) * 16 + pool[:, 1])
        for seed in (101, 202, 303):
            course, final_rng = r.schedules(seed, rows)
            rng = np.random.default_rng(seed + 444000)
            self.assertEqual(course.shape, (40, 24300, 2))
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
        good = {name: {"questions": 900, "whole_correct": 900} for name in ("E1", "E2", "F1")}
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

    def test_mock_baseline_carry_delta_and_full_baseline_epoch_replay(self):
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
            return {"scores": {name: {"questions": 900, "whole_correct": 900} for name in ("E1", "E2", "F1")},
                    "rows": [{"question_id": row["question_id"], "class": row["class"], "pair_id": row["pair_id"], "tokens": row["A"] + "S", "whole_correct": True} for row in questions],
                    "inference_calls": count, "inference_dense_MAC": count * 10432}
        course, _ = r.schedules(seed, rows)
        with tempfile.TemporaryDirectory(prefix="mixed-mock-delta-") as directory, patch.object(r, "probe", mock_probe), contextlib.redirect_stdout(io.StringIO()):
            out = Path(directory)
            baseline, record = r.baseline_one(Mock, saved, raw, rows, out, seed)
            self.assertEqual(record["baseline_streak"], 0)
            self.assertEqual(record["new_optimizer_updates"], 0)
            self.assertEqual(int(baseline["t"]), 123)
            self.assertEqual(int(baseline["meta_inference_calls"]), 77 + 24300)
            self.assertEqual((out / f"seed{seed}/initial-state.npz").read_bytes(), raw)
            r.train_one(Mock, saved, baseline, record, course, rows, out, seed)
            baseline2, record2 = r.baseline_one(Mock, saved, raw, rows, out, seed, replay=True)
            r.train_one(Mock, saved, baseline2, record2, course, rows, out, seed, replay=True)
            summary = r.read(out / f"seed{seed}/training-summary.json")
            self.assertEqual(summary["epochs"], 2)
            self.assertEqual(summary["new_updates"], 48600)
            self.assertEqual(summary["new_training_dense_MAC"], 48600 * 21056)
            self.assertEqual(summary["new_probe_inference_calls"], 48600)
            self.assertEqual(summary["baseline_inference_calls"], 24300)
            self.assertEqual(summary["total_counters_before_finalTF"]["t"], 123 + 48600)
            self.assertEqual(summary["total_counters_before_finalTF"]["inference_calls"], 77 + 24300 + 48600)


if __name__ == "__main__":
    unittest.main()
