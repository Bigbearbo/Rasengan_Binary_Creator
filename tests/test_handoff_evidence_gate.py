"""Offline, no-network proof-of-execution checks for coordinator handoff."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "handoff_evidence_gate.py"
spec = importlib.util.spec_from_file_location("handoff_evidence_gate", MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=t@example.test", "commit", "--allow-empty", "-qm", "base"], check=True)
        self.sha, self.clean = gate.state(self.repo)
        self.cmd = [sys.executable, "-B", "-c", "print('test OK')"]
        self.claim = {"work_id": "COORD-RECEIPT-001", "source_sha": self.sha,
                      "test_argv": self.cmd, "claimed_pass": True}

    def take_receipt(self, command=None):
        path = self.root / "receipt.json"
        receipt = gate.record(self.repo, "COORD-RECEIPT-001", path, command or self.cmd, 10)
        self.assertEqual(json.loads(path.read_text()), receipt)
        return receipt

    def verify(self, receipt=None, claim=None, expected=None):
        sha, clean = gate.state(self.repo)
        return gate.check(claim or self.claim, receipt, local_sha=sha, local_clean=clean,
                          expected_source_sha=expected or self.sha)

    def test_actual_run_receipt_pass(self):
        receipt = self.take_receipt()
        self.assertEqual(receipt["stdout"], "test OK\n")
        self.assertEqual(self.verify(receipt)["status"], "verified_local_execution_receipt")

    def test_report_only_is_candidate_not_verified(self):
        result = self.verify()
        self.assertEqual(result["status"], "candidate")
        self.assertIn("report_only_no_receipt", result["reasons"])

    def test_failed_command_blocked(self):
        receipt = self.take_receipt([sys.executable, "-B", "-c", "raise SystemExit(1)"])
        claim = dict(self.claim, test_argv=receipt["command_argv"])
        self.assertIn("test_failed_or_timed_out", self.verify(receipt, claim)["reasons"])

    def test_swapped_command_blocked(self):
        receipt = self.take_receipt()
        claim = dict(self.claim, test_argv=[sys.executable, "-B", "-c", "print('different')"])
        self.assertIn("command_mismatch", self.verify(receipt, claim)["reasons"])

    def test_swapped_work_id_blocked(self):
        receipt = self.take_receipt()
        self.assertIn("work_id_mismatch", self.verify(receipt, dict(self.claim, work_id="OTHER"))["reasons"])

    def test_moved_remote_pin_blocked(self):
        receipt = self.take_receipt()
        self.assertIn("live_source_sha_mismatch", self.verify(receipt, expected="f" * 40)["reasons"])

    def test_dirty_before_record_rejected(self):
        (self.repo / "untracked.txt").write_text("dirty")
        with self.assertRaisesRegex(ValueError, "dirty"):
            self.take_receipt()

    def test_dirty_after_run_blocked(self):
        receipt = self.take_receipt()
        (self.repo / "modified.txt").write_text("dirty")
        self.assertIn("local_worktree_dirty", self.verify(receipt)["reasons"])

    def test_command_creates_file_cannot_verify(self):
        c = [sys.executable, "-B", "-c", "from pathlib import Path;Path('out.txt').write_text('x')"]
        receipt = self.take_receipt(c)
        claim = dict(self.claim, test_argv=c)
        self.assertIn("worktree_changed_during_test", self.verify(receipt, claim)["reasons"])

    def test_truncated_output_blocked(self):
        c = [sys.executable, "-B", "-c", "print('a'*70000)"]
        receipt = self.take_receipt(c)
        claim = dict(self.claim, test_argv=c)
        self.assertTrue(receipt["stdout_truncated"])
        self.assertIn("output_truncated", self.verify(receipt, claim)["reasons"])

    def test_receipt_inside_source_repo_forbidden(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            gate.record(self.repo, "x", self.repo / "result.json", self.cmd, 10)


if __name__ == "__main__":
    unittest.main()
