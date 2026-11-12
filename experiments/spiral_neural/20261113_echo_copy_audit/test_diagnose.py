"""Synthetic grammar/history/causal-condition checks; zero old-checkpoint inference."""
import unittest
import numpy as np
import diagnose as d


class Synthetic(unittest.TestCase):
    def test_trace_prediction_is_not_teacher_answer(self):
        history = d.History()
        phase = {"name": "synthetic", "nop": 2, "nd": 3, "ops": [0], "train": [2]}
        history.add_phase(phase, [[0, 2, "SSSSS"]])
        q = d.encode(2, 3, 0, 2)
        self.assertEqual(history.targets, 5)
        self.assertEqual(history.exposure(q, "0")["label_counts"], {"0": 1})
        self.assertEqual(history.exposure(q + "0100", "S")["classification"], "same_only")
        self.assertIn("0100S", history.answers)
        self.assertNotIn("SSSSS", history.answers)

    def test_cross_stage_raw_alias_and_last_label(self):
        history = d.History()
        history.add_phase({"name": "old", "nop": 1, "nd": 3, "ops": [0], "train": [3]}, [[0, 3, "00000"]])
        old_prefix = d.encode(1, 3, 0, 3) + d.answer(3, 0, 3)[:4]
        new_prefix = d.encode(2, 3, 0, 6) + d.answer(3, 0, 6)[:3]
        self.assertEqual(old_prefix, new_prefix)
        self.assertEqual(history.exposure(new_prefix, "0")["classification"], "conflict_only")
        self.assertNotIn(d.encode(2, 3, 0, 6), history.questions)
        history.add_phase({"name": "new", "nop": 2, "nd": 3, "ops": [0], "train": [6]}, [[0, 6, "11111"]])
        row = history.exposure(new_prefix, "0")
        self.assertEqual(row["classification"], "mixed")
        self.assertEqual(row["last_label"], "0")
        self.assertEqual(row["first"]["phase"], "old")
        self.assertEqual(row["last"]["phase"], "new")
        self.assertEqual(sum(x["count"] for x in history.prefixes.values()), history.targets)

    def test_pairs_share_true_prefix_and_reuse24_logits(self):
        cache = {}
        for value in range(8):
            bits = format(value, "03b")
            cache[value] = [{"target": bits[j], "prediction": bits[j], "correct_earlier_A_prefix": bits[:j],
                             "logits_01S": [float(bits[j] == "0"), float(bits[j] == "1"), -1.]} for j in range(3)]
        pairs = d.pair_diagnostics(cache)
        self.assertEqual(pairs["current_bit"]["both_correct_and_follow"], 12)
        self.assertEqual(pairs["future_bit"]["both_correct_and_invariant"], 12)
        self.assertEqual(pairs["future_bit"]["distinct_whole_Q_pairs"], 8)
        self.assertEqual(pairs["additional_forward_calls"], 0)
        for tokens in cache.values():
            for row in tokens:
                row["prediction"] = "S"
        wrong = d.pair_diagnostics(cache)
        self.assertEqual(wrong["future_bit"]["raw_predicted_token_invariant"], 12)
        self.assertEqual(wrong["future_bit"]["both_correct_and_invariant"], 0)
        self.assertEqual(wrong["current_bit"]["both_correct_and_follow"], 0)

    def test_generation_never_forces_STOP(self):
        class Constant:
            L = 13
            def forward(self, prefix):
                return None, None, np.array([1., 0., -1.])
        row = d.generation(Constant(), "0" * 9)
        self.assertEqual(row["tokens"], "0" * 5)
        self.assertTrue(row["overflow"])
        self.assertNotIn("S", row["tokens"])

    def test_ast_only_loader_hard_denies_learning(self):
        # Synthetic class with the required API, not a historical student.
        code = b'class Model:\n def __init__(self): self.calls=0\n def forward(self,text,training=False): self.calls+=1; return text\n def step(self,*a): pass\n def lesson(self,*a): pass\n def loss_grad(self,*a): pass\n def grow(self,*a): pass\n'
        cls, guards = d.model_class(code)
        net = cls()
        for name in ("step", "lesson", "loss_grad", "grow"):
            with self.assertRaisesRegex(RuntimeError, "forbids"):
                getattr(net, name)("0", "1")
        with self.assertRaises(RuntimeError):
            net.forward("0", training=True)
        self.assertEqual(net.calls, 0)
        self.assertTrue(all(value == 1 for value in guards.values()))

    def test_zip_is_deterministic_and_preserves_bytes(self):
        import io
        import zipfile
        values = {"source.py": b"print('public')\n", "trace.json": b'[[0,1,"SSS"]]'}
        payload = d.zip_bytes(values)
        self.assertEqual(payload, d.zip_bytes(values))
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, values)

    def test_prefix_completion_support_is_material_only(self):
        rows = d.prefix_completion_table()["rows"]
        self.assertEqual(next(row for row in rows if row["correct_answer_prefix"] == "10")["next_bit_support_counts"], {"0": 1})
        self.assertEqual(next(row for row in rows if row["correct_answer_prefix"] == "11")["next_bit_support_counts"], {"1": 1})
        self.assertFalse(any("prediction" in row for row in rows))


if __name__ == "__main__":
    unittest.main()
