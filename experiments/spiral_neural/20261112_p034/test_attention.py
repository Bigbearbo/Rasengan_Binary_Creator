"""Engineering gates for P034 B1; synthetic snippets, no SLE experiment data."""
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import time
import unittest

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

from attention_model import Model, PARAMETER_NAMES, SHAPES

EVIDENCE = Path("D:/Codex用/work/sle-p034/attention-engineering")
DETAILS = {}


def state_equal(a, b):
    return a.keys() == b.keys() and all(np.array_equal(a[k], b[k]) for k in a)


def loss_value(model, text, target):
    z = model.forward(text, training=True)[2]
    return float(np.logaddexp.reduce(z) - z["01S".index(target)])


class AttentionEngineering(unittest.TestCase):
    def test_01_parameter_count_and_frozen_initialization(self):
        model, same, different = Model(471), Model(471), Model(472)
        self.assertEqual(model.parameters, 2596)
        self.assertEqual(len(model.p), 20)
        self.assertEqual(tuple(a.shape for a in model.p), SHAPES)
        self.assertEqual(sum(model.p[i].size for i in range(2, 10)), 1088)
        self.assertEqual(sum(model.p[i].size for i in range(14, 18)), 1105)
        self.assertEqual(sum(model.p[i].size for i in range(10, 14)), 64)
        self.assertTrue(state_equal(model.state(), same.state()))
        self.assertFalse(np.array_equal(model.p[0], different.p[0]))
        rng = np.random.default_rng(471)
        for name, p in zip(PARAMETER_NAMES, model.p):
            if name in ("embedding", "position"):
                expected = rng.normal(0., .02, p.shape)
            elif name.startswith("W"):
                limit = np.sqrt(6. / (p.shape[0] + p.shape[1]))
                expected = rng.uniform(-limit, limit, p.shape)
            else:
                expected = np.ones(p.shape) if name.endswith("_scale") else np.zeros(p.shape)
            np.testing.assert_array_equal(p, expected.astype(np.float32))
            self.assertEqual(p.dtype, np.float32)
        for group in (model.m, model.v, model.birth):
            self.assertTrue(all(not np.any(a) for a in group))
        self.assertEqual(model.array_bytes(), {
            "parameters": 10384, "adam_m": 10384, "adam_v": 10384,
            "birth_int64": 20768, "total": 51920})
        DETAILS["parameter_count"] = model.parameters
        DETAILS["array_bytes_float32"] = model.array_bytes()
        DETAILS["deterministic_frozen_initialization"] = True

    def test_02_exhaustive_all_parameter_gradients_all_three_targets(self):
        model = Model(481, dtype=np.float64)
        text = "0010110"
        epsilon, reports, global_max = 1e-6, [], 0.
        for target in "01S":
            loss, grads, prediction = model.loss_grad(text, target)
            self.assertTrue(np.isfinite(loss))
            self.assertIn(prediction, "01S")
            group_reports = []
            for name, parameter, gradient in zip(PARAMETER_NAMES, model.p, grads):
                maximum, maximum_scaled = 0., 0.
                for index in range(parameter.size):
                    original = parameter.flat[index]
                    parameter.flat[index] = original + epsilon
                    plus = loss_value(model, text, target)
                    parameter.flat[index] = original - epsilon
                    minus = loss_value(model, text, target)
                    parameter.flat[index] = original
                    numerical = (plus - minus) / (2. * epsilon)
                    error = abs(numerical - gradient.flat[index])
                    scaled = error / max(1., abs(numerical), abs(gradient.flat[index]))
                    maximum, maximum_scaled = max(maximum, error), max(maximum_scaled, scaled)
                self.assertLess(maximum, 2e-6, (target, name, maximum))
                self.assertLess(maximum_scaled, 2e-7, (target, name, maximum_scaled))
                group_reports.append({"parameter": name, "coordinates": parameter.size,
                                      "max_absolute_error": maximum,
                                      "max_scaled_error": maximum_scaled,
                                      "gradient_nonzero": bool(np.any(abs(gradient) > 1e-12))})
                global_max = max(global_max, maximum)
            np.testing.assert_array_equal(grads[1][len(text):], 0.)
            for token in "01":
                positions = [i for i, actual in enumerate(text) if actual == token]
                np.testing.assert_allclose(grads[0][int(token)],
                                           grads[1][positions].sum(axis=0), atol=1e-12)
            for i in (0, 1, 10, 11, 12, 13):
                self.assertTrue(np.any(abs(grads[i]) > 1e-10), (target, PARAMETER_NAMES[i]))
            reports.append({"target": target, "coordinates": 2596,
                            "groups": group_reports})
        DETAILS["finite_difference"] = {"dtype": "float64", "epsilon": epsilon,
                                       "total_coordinates": 7788,
                                       "max_absolute_error": global_max,
                                       "targets": reports}
        DETAILS["repeated_token_embedding_scatter_add"] = True

    def test_03_causal_future_perturbation_and_prefix_equivalence(self):
        model = Model(482, dtype=np.float64)
        text = "0100110101101"
        before = model.state()
        full = model.forward_all(text)
        self.assertEqual(full["logits"].shape, (len(text), 3))
        self.assertEqual(full["states"].shape, (len(text), 16))
        np.testing.assert_array_equal(np.triu(full["attention_weights"], k=1), 0.)
        np.testing.assert_allclose(full["attention_weights"].sum(axis=1), 1., atol=1e-15)
        maximum = 0.
        for changed in range(1, len(text)):
            alternative = text[:changed] + ("1" if text[changed] == "0" else "0") + text[changed+1:]
            perturbed = model.forward_all(alternative)
            for key in ("embeddings", "ln1", "attention_context", "attention_residual",
                        "ln2", "ffn_hidden", "states", "logits"):
                error = float(np.max(abs(full[key][:changed] - perturbed[key][:changed])))
                maximum = max(maximum, error)
                self.assertLess(error, 1e-12, (changed, key))
        for n in range(1, len(text) + 1):
            _, state, z = model.forward(text[:n])
            np.testing.assert_allclose(z, full["logits"][n-1], atol=1e-12)
            np.testing.assert_allclose(state[-1], full["states"][n-1], atol=1e-12)
        self.assertTrue(state_equal(before, model.state()))
        DETAILS["causal_future_perturbation"] = {
            "changed_future_positions": len(text)-1, "max_error": maximum,
            "prefix_logits_and_states_equal": True}

    def test_04_stop_context_and_action_guards(self):
        model = Model(483)
        model.p[18][:] = 0.
        model.p[19][:] = [0., 0., 50.]
        self.assertEqual(model.generate("0" * 16), ("S", False))
        model.p[19][:] = [50., 0., 0.]
        self.assertEqual(model.generate("0" * 16), ("0", True))
        self.assertEqual(model.generate("0" * 17), ("", True))
        self.assertEqual(model.generate("01"), ("0" * 8, False))
        # The reference flag denotes a blocked forward request, not whether
        # an unused ninth-action prefix would overflow after action exhaustion.
        self.assertEqual(model.generate("0" * 9), ("0" * 8, False))
        for bad in ("", "S", "010S", "01x", 1, None):
            with self.assertRaises(ValueError):
                model.generate(bad)
        for bad in ("", "1" * 17, "010S"):
            with self.assertRaises(ValueError):
                model.forward(bad)
        initial = model.state()
        for q, answer in (("0" * 16, "0"), ("01", "S")):
            with self.assertRaises(ValueError):
                model.lesson(q, answer)
        self.assertTrue(state_equal(initial, model.state()))
        DETAILS["guards"] = {"stop_model_emitted": True, "context_overflow_flag": True,
                             "max_eight_actions_no_forced_stop": True,
                             "invalid_lesson_has_no_partial_updates": True}

    def test_05_float32_optimizer_clipping_and_all_parameter_groups(self):
        model = Model(484)
        raw_loss, gradients, prediction = model.loss_grad("0010011", "S")
        initial = [p.copy() for p in model.p]
        norm = np.sqrt(sum(float(np.sum(g.astype(np.float64)**2)) for g in gradients))
        self.assertGreater(norm, 1.)
        actual_prediction, actual_loss = model.step("0010011", "S")
        self.assertEqual(actual_prediction, prediction)
        self.assertEqual(actual_loss, raw_loss)
        self.assertEqual(model.t, 1)
        self.assertAlmostEqual(model.last_gradient_norm, norm, delta=norm*2e-6)
        self.assertAlmostEqual(model.last_gradient_scale, 1./norm, delta=2e-6)
        # Independent Adam expression validates every coordinate and group.
        for name, original, gradient, p, m, v in zip(
                PARAMETER_NAMES, initial, gradients, model.p, model.m, model.v):
            clipped = gradient.astype(np.float64) / norm
            expected_m = .1 * clipped
            expected_v = .001 * clipped**2
            expected_p = original.astype(np.float64) - .003 * clipped / (abs(clipped) + 1e-8)
            np.testing.assert_allclose(m, expected_m, rtol=3e-6, atol=3e-8, err_msg=name)
            np.testing.assert_allclose(v, expected_v, rtol=5e-6, atol=3e-10, err_msg=name)
            np.testing.assert_allclose(p, expected_p, rtol=2e-5, atol=1e-7, err_msg=name)
            self.assertEqual((p.dtype, m.dtype, v.dtype), (np.float32,)*3)
        cache = model.forward_all("0010011")
        for key, a in cache.items():
            if key != "ids":
                self.assertEqual(a.dtype, np.float32, key)
        DETAILS["float32_optimizer"] = {"raw_norm": norm,
                                        "actual_norm": model.last_gradient_norm,
                                        "clip_scale": model.last_gradient_scale,
                                        "all_20_parameter_groups_checked": True}

    def test_06_full_optimizer_checkpoint_and_repeated_token_replay(self):
        snippets = [("001001", "001"), ("110010", "110"),
                    ("0101", "0"), ("000111", "010"), ("111000", "101")]
        baseline = Model(485)
        first_results = [baseline.lesson(*snippet) for snippet in snippets[:2]]
        self.assertEqual(baseline.t, 8)
        checkpoint_state = baseline.state()
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        checkpoint = EVIDENCE / "synthetic-engineering-checkpoint.npz"
        baseline.save_checkpoint(checkpoint)
        restored = Model.load_checkpoint(checkpoint)
        self.assertTrue(state_equal(checkpoint_state, restored.state()))
        direct = Model.from_state(checkpoint_state)
        self.assertTrue(state_equal(checkpoint_state, direct.state()))
        expected = [baseline.lesson(*snippet) for snippet in snippets[2:]]
        actual = [restored.lesson(*snippet) for snippet in snippets[2:]]
        self.assertEqual(actual, expected)
        self.assertTrue(state_equal(baseline.state(), restored.state()))
        full = Model(485)
        self.assertEqual([full.lesson(*s) for s in snippets], first_results + expected)
        self.assertTrue(state_equal(full.state(), baseline.state()))
        # RNG snapshots restore future draws, despite no stochastic training.
        np.testing.assert_array_equal(baseline.rng.integers(0, 2**32, 19),
                                      restored.rng.integers(0, 2**32, 19))
        np.testing.assert_array_equal(baseline.growth_rng.integers(0, 2**32, 19),
                                      restored.growth_rng.integers(0, 2**32, 19))
        corrupted = direct.state()
        corrupted["p0"] = corrupted["p0"][:1]
        unchanged = direct.state()
        with self.assertRaises(ValueError):
            direct.load_state(corrupted)
        self.assertTrue(state_equal(unchanged, direct.state()))
        # Restores must own array storage, not alias the input snapshot.
        saved_value = float(direct.p[0][0, 0])
        checkpoint_state["p0"][0, 0] += 1.
        self.assertEqual(float(direct.p[0][0, 0]), saved_value)
        DETAILS["checkpoint_replay"] = {"synthetic_lessons": len(snippets),
                                        "target_updates": full.t,
                                        "parameters_moments_birth_rng_exact": True,
                                        "all_predictions_losses_exact": True,
                                        "disk_checkpoint_roundtrip": True}

    def test_07_no_oracle_access_or_teacher_labels_in_generation(self):
        model = Model(486)
        self.assertEqual(tuple(inspect.signature(model.generate).parameters), ("q",))
        self.assertEqual(tuple(inspect.signature(model.forward).parameters), ("text", "training"))
        model.p[18][:] = 0.
        model.p[19][:] = [0., 50., 0.]
        prefixes, original_forward = [], model.forward

        def forbidden(*args, **kwargs):
            raise AssertionError("Teacher/training/oracle access during generation")

        def spy(text, training=False):
            self.assertFalse(training)
            self.assertFalse(set(text) - set("01"))
            prefixes.append(text)
            return original_forward(text, training)

        model.forward = spy
        model.lesson = model.step = model.loss_grad = forbidden
        model.oracle = model.answer = model.parser = model.teacher = forbidden
        initial = model.state()
        self.assertEqual(model.generate("0010"), ("1" * 8, False))
        self.assertEqual(prefixes, ["0010" + "1" * i for i in range(8)])
        self.assertTrue(state_equal(initial, model.state()))
        DETAILS["generation_visibility"] = {
            "only_q_and_self_generated_binary_prefix": True,
            "training_teacher_oracle_spies_not_called": True,
            "learner_state_unchanged": True}

    def test_08_prefix_costs_and_counter_accounting(self):
        model = Model(487)
        for n in range(1, 17):
            before = model.inference_macs
            model.forward("0" * n)
            dense = n * (4*16*16 + 16*33 + 33*16) + 16*3
            attention = 2*n*n*16
            self.assertEqual(model.inference_macs - before, dense + attention)
            before = model.train_macs
            model.loss_grad("0" * n, "S")
            self.assertEqual(model.train_macs - before, 3*(dense + attention))
            f = Model.cost_for_prefix(n)
            b = Model.cost_for_prefix(n, backward=True)
            self.assertEqual(f["layernorm_token_elements"], 32*n)
            self.assertEqual(f["attention_softmax_elements"], n*n)
            self.assertEqual(f["attention_softmax_valid_elements"], n*(n+1)//2)
            self.assertEqual(b["dense_macs"], 2*f["dense_macs"])
            self.assertEqual(b["attention_macs"], 2*f["attention_macs"])
            self.assertEqual(b["output_softmax_elements"], 3)
        self.assertEqual(model.inference_calls, 16)
        before = model.inference_macs
        model.forward_all("00101")
        self.assertEqual(model.inference_macs-before, 2080*5 + 32*25 + 48*5)
        for invalid in (0, 17, 1.5):
            with self.assertRaises(ValueError):
                Model.cost_for_prefix(invalid)
        lesson_cost = sum(6240*n + 96*n*n + 144 for n in range(9, 14))
        self.assertEqual(lesson_cost, 402960)
        self.assertEqual(lesson_cost*3000, 1208880000)
        DETAILS["costs"] = {
            "normal_forward_dense": "2080*n+48",
            "normal_forward_attention": "32*n*n",
            "last_token_backward_dense": "4160*n+96",
            "last_token_backward_attention": "64*n*n",
            "all_position_probe_head_dense": "48*n instead of 48",
            "attention_softmax_dense_elements_per_direction": "n*n",
            "attention_softmax_valid_elements": "n*(n+1)/2",
            "layernorm_token_elements_per_direction": "32*n",
            "output_softmax_training_elements": 3,
            "example_n9_through_n13_lesson_macs": lesson_cost,
            "masked_future_cells_still_counted_in_dense_matmul": True,
        }


def main():
    started = time.perf_counter()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AttentionEngineering)
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    report = {
        "scope": "engineering-only synthetic snippets; no scientific SLE training",
        "passed": result.wasSuccessful(), "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "seconds": time.perf_counter()-started, "numpy": np.__version__,
        "python": sys.version, "details": DETAILS,
        "source_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                          for name in ("attention_model.py", "test_attention.py")},
    }
    (EVIDENCE / "checks.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "tests": result.testsRun,
                      "seconds": report["seconds"],
                      "max_gradient_error": DETAILS.get("finite_difference", {}).get("max_absolute_error"),
                      "evidence": str(EVIDENCE / "checks.json")}, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
