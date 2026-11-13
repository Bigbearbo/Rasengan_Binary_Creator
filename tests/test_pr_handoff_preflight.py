"""Only orchestration metadata tests; do not execute NN, parser, or VM experiments."""
import copy
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pr_handoff_preflight import check

FIXTURES = ROOT / "tests" / "fixtures"


class PRHandoffTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads((FIXTURES / "public_pr_fork_20261113.json").read_text())
        self.claim = json.loads((FIXTURES / "claim_ae1_pinned.json").read_text())
        self.now = dt.datetime.fromisoformat("2026-11-13T07:25:00+08:00")

    def validate(self, snap=None, claim=None, now=None, current=None):
        return check(snap if snap is not None else self.snapshot,
                     claim if claim is not None else self.claim,
                     now=now if now is not None else self.now,
                     current_main=current if current is not None else self.snapshot["main_sha"])

    def test_fork_and_leaf_routing(self):
        r = self.validate()
        self.assertEqual(r["status"], "verified_snapshot_only")
        self.assertEqual(r["forks"], [{"base_ref": "pro/advanced-echo-design-20261113", "children": [18, 19]}])
        self.assertEqual(r["leaf_pr_numbers_within_snapshot"], [20, 21, 22])

    def test_parent_pin_moved_blocks(self):
        snap = copy.deepcopy(self.snapshot)
        snap["prs"][2]["head_sha"] = "f" * 40
        self.assertIn("PARENT_HEAD_MOVED", [i["code"] for i in self.validate(snap)["issues"]])
        self.assertEqual(self.validate(snap)["status"], "blocked")

    def test_stacked_child_parent_moved_blocks(self):
        snap = copy.deepcopy(self.snapshot)
        snap["prs"][2]["head_sha"] = "f" * 40
        result = self.validate(snap)
        self.assertIn("PARENT_BRANCH_MOVED", [i["code"] for i in result["issues"]])
        self.assertEqual(result["status"], "blocked")

    def test_missing_owner_blocks(self):
        claim = dict(self.claim, owner="")
        self.assertIn("CLAIM_MISSING_FIELD", [i["code"] for i in self.validate(claim=claim)["issues"]])

    def test_ambiguous_fork_without_explicit_parent_blocks(self):
        claim = dict(self.claim, parent_pr=21)
        self.assertIn("AMBIGUOUS_FORK_ROUTE", [i["code"] for i in self.validate(claim=claim)["issues"]])

    def test_current_main_changed_blocks(self):
        self.assertIn("MAIN_CHANGED_AFTER_SNAPSHOT", [i["code"] for i in self.validate(current="f"*40)["issues"]])

    def test_stale_snapshot_blocks(self):
        old = dt.datetime.fromisoformat("2026-11-13T10:00:00+08:00")
        self.assertIn("STALE_SNAPSHOT", [i["code"] for i in self.validate(now=old)["issues"]])

    def test_invalid_pr_data_fails_closed(self):
        snap = copy.deepcopy(self.snapshot)
        snap["prs"][0]["base_sha"] = "bad"
        with self.assertRaises(ValueError):
            self.validate(snap)


if __name__ == "__main__":
    unittest.main()
