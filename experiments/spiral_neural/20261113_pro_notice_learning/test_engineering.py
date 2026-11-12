"""Bounded engineering checks, never a formal ACK learning-score pilot."""
import copy
from pathlib import Path
import subprocess
import sys
import unittest
from dataclasses import replace
import dataset
import learner
import run_trial


class Engineering(unittest.TestCase):
    def test_dataset_legality_and_split(self):
        rows = dataset.make_rows()
        checks = dataset.validate_rows(rows)
        self.assertEqual(checks["train_targets_per_epoch"], 212)
        for row in rows:
            tree = dataset.teacher_tree(row["path"], row["target_n"])
            receiver = dataset.codec.NoticeReceiver(tree)
            result = receiver.receive_notice(row["Q"], profile_id=dataset.codec.PROFILE_ID)
            self.assertEqual((result.status, result.reply_bits), ("upgraded", row["A"]))
            duplicate = receiver.receive_notice(row["Q"], profile_id=dataset.codec.PROFILE_ID)
            self.assertEqual((duplicate.status, duplicate.reply_bits), ("already_current", row["A"]))
            self.assertEqual(receiver.applied_transitions, 1)
            for path in dataset.PATHS:
                before = dataset.codec.branch_at(tree, path)
                after = dataset.codec.branch_at(receiver.tree, path)
                self.assertEqual(after, replace(before, n=row["target_n"]) if list(path) == row["path"] else before)

    def test_exact_covers_and_budget(self):
        p = run_trial.protocol()
        rows = dataset.make_rows()
        courses = dataset.make_curricula(rows, p["seeds"], p["epochs"], p["schedule_seed_offset"])
        other = dataset.make_curricula(rows, p["seeds"], p["epochs"], p["schedule_seed_offset"])
        self.assertEqual(courses, other)
        by_id = {row["id"]: row for row in rows}
        for course in courses.values():
            ids = [row_id for epoch in course["epochs"] for row_id in epoch]
            self.assertEqual(len(ids), 1536)
            self.assertTrue(all(by_id[row_id]["split"] == "train" for row_id in ids))
            self.assertEqual(sum(by_id[row_id]["target_updates"] for row_id in ids), 27136)
            self.assertEqual(27136 * 64 * (4 * 80 + 9), 571375616)

    def test_bounded_synthetic_replay(self):
        self.assertEqual(run_trial.preflight()["formal_student_updates"], 0)

    def test_evaluation_does_not_train(self):
        # Synthetic row only: never probe formal heldout neural performance here.
        row = {"id": "engineering", "split": "train", "path": [0], "target_n": 1,
               "Q": "010", "A": "01", "address_bits": "0", "up_bits": "1"}
        net = learner.new_student(910015)
        before = copy.deepcopy(net.state())
        learner.evaluate(net, [row])
        self.assertTrue(learner.reference.equal_state(before, net.state()))
        self.assertEqual(net.t, 0)

    def test_default_cap_is_not_eight(self):
        net = learner.new_student(910016)
        net.p[2][:] = 0
        net.p[3][:] = [1, 0, -1]
        result = learner.generate(net, "010")
        self.assertEqual(result["tokens"], "0" * 24)
        self.assertTrue(result["cap_exhausted"])
        self.assertFalse(result["tokens"].endswith("S"))

    def test_optimized_python_is_rejected(self):
        result = subprocess.run([sys.executable, "-O", "-B", str(Path(run_trial.__file__)), "--preflight"],
                                capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Optimized Python (-O/-OO) is disabled", result.stderr)


if __name__ == "__main__":
    unittest.main()
