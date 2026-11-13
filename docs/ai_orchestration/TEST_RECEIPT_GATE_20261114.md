# Coordinator test-receipt gate (2026-11-14)

Scope: **public Git handoff metadata**, not NN/VM/SLE execution. This is an isolated candidate for Codex issue #3, not a replacement for draft PR #23's PR-DAG/SHA preflight. No private Library/chat content or access token is included.

## Concrete failure mode

Research PR descriptions sometimes list a successful local test while the corresponding large checkpoints or complete raw outputs are outside Git. A reader can confirm that a **report exists** without having independently executed the stated test. A documentation PASS must not silently turn into this agent's `T` or a general `verified` claim. Example: public PR #59 has a valid local result claim and standalone NumPy verifier, but expressly says its six checkpoint files and full raw output are in a separate companion ZIP. A fresh Git-only coordinator must not claim it reproduced the NN experiment.

The tool `tools/handoff_evidence_gate.py` separates:

- `candidate`: report/claim exists, but **this working copy has no local execution receipt**;
- `blocked`: source SHA is stale or absent, command/owner key mismatch, test failed, worktree is dirty, outputs truncated, or receipt does not match;
- `verified_local_execution_receipt`: a single explicitly launched local command exited 0 against a clean Git HEAD; this does **not** prove science reproduced, hidden artifacts present, or that another model was called.

Use in a **trusted local checkout only**. The `record` subcommand executes only an explicit shell-free argv supplied by the caller, **never** commands from third-party reports. Run it in a separate clean test worktree and store receipts outside Git. A self-reported JSON receipt is not a tamper-proof attestation: use it for process discipline, compare to current source SHA, and independently replay when the evidence matters. Do not publish private receipts to the public repository.

## Reproducible local check

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_handoff_evidence_gate.py -v
```

Example workflow after local checkout, using a trusted existing test command:

```bash
python tools/handoff_evidence_gate.py record --repo . --work-id COORD-001 --out ../COORD-001.receipt.json -- python -B -m unittest discover -s tests -p 'test_pr_handoff_preflight.py'
python tools/handoff_evidence_gate.py check --repo . --claim ../COORD-001.claim.json --receipt ../COORD-001.receipt.json --expected-source-sha <live-remote-branch-sha>
```

A claim looks like:

```json
{"work_id":"COORD-001","source_sha":"<40-char-Git-SHA>","test_argv":["python","-B","-m","unittest","discover","-s","tests","-p","test_pr_handoff_preflight.py"],"claimed_pass":true}
```

`--expected-source-sha` must come from an independently refreshed live Git branch, not be copied from the report. Without receipt, `check` returns `candidate` (exit 2). A successful locally created receipt only validates that **specific** test and source state; it must not be used as a substitute for actual neural checkpoint replay. For cross-model workers, `planned`/`attempted` and `returned`/`accepted` stay distinct; this gate does not call NVIDIA, Gemini, Codex, or the model API.

## Source provenance and next step

U: author requests owner-aware multi-agent coordination, traceable claims and no private/public source mixing. F: public main `d032a825c2b419f365bf34a531baee3b53b91750` (seen 2026-11-14), [`AGENTS.md`](../../AGENTS.md), `GIT_RESEARCH_HANDOFF_20261113.md`, `CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md`, [PR #23](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/23) and [PR #59](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/59). T: local `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_handoff_evidence_gate.py -v` — **11/11 PASS** (2026-11-14); no NN, VM, parser or external agent call. A: the receipt gate could be integrated by the Codex dispatcher once an authorized local environment exists; no auto merge. Owner: Codex coordination / issue #3. `nvidia_status=skipped_unavailable`, `actual_calls=0` for this documentation and mock check.
