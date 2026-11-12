# PR DAG preflight: cross-agent handoff guard

Date: 2026-11-13 (Asia/Taipei). Scope: coordination metadata only. Implementation status: candidate (offline tests passed, live dispatcher not integrated).

## Observed handoff problem (F)

An agent reading only main or choosing the largest PR number cannot safely select a next branch when a stacked PR chain forks. The public GitHub metadata shows [PR #16](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/16) head 685c6f92d9e5a335a2f2a7193d9b501918d90b00 is the base of two distinct branches:

- [PR #18](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/18) → [#20](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/20), Codex early/late mixing.
- [PR #19](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/19) → [#21](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/21), Pro AE1 and read-only follow-up.
- A separate VM branch: [#17](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/17) → [#22](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/22).

Observed main commit was a28d6fa582bf60bd051c78897f7aa900d863c6e7. The [PR #19 results report](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/1d8db6b6d265d4a6b059437444178e87edbb9808/docs/ai_orchestration/PRO_ADVANCED_ECHO_RESULTS_20261113.md) and [PR #20 results artifact](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/3fe2a9aa945512c8510222c13b769b2fbb2cc859/experiments/spiral_neural/20261113_codex_early_mix/RESULTS.md) are distinct scientific lines. This guard did not rerun, reconstruct or validate those training experiments. The existing main handoff already says to reread live PRs; the new tool tests a specific failure mode without rewriting others' research cards.

## Implementation

The read-only Python standard-library script at tools/pr_handoff_preflight.py consumes an explicit public, sanitized JSON snapshot containing main_sha, observed_at, and PR base/head refs and SHAs. Optional claim fields: work_id, owner, workstream, goal, status (candidate/verified/blocked), parent_pr, parent_head_sha and next_from_ref.

It finds non-main forks, sample-only leaves and bases not present in the sample. It blocks claims with a missing owner or pin, parent head changes, dependent PR base/head mismatch, ambiguous fork route, stale supplied snapshot or a mismatching independently fetched main SHA. A parent missing *from the sample* is not evidence of a missing branch. It never guesses the newest branch by PR number.

Output verified_snapshot_only means exactly that the metadata passed offline checks; it does not check live repository state, perform scientific verification, acquire a distributed task lock, or dispatch NVIDIA/Gemini/Codex. The Python script makes zero network or model calls.

## Reproduction and test (T)

From the repo root run:

    python -m unittest discover -s tests -p test_pr_handoff_preflight.py -v
    python tools/pr_handoff_preflight.py tests/fixtures/public_pr_fork_20261113.json --claim tests/fixtures/claim_ae1_pinned.json --current-main a28d6fa582bf60bd051c78897f7aa900d863c6e7 --now 2026-11-13T07:25:00+08:00

On the source files before upload: **8/8 local unit tests PASS**. The positive sample finds fork #18/#19 and sample leaves #20/#21/#22. Negative tests cover moved parent pin, moved stacked parent, missing owner, wrong fork route, changed main, stale snapshot and invalid SHA. Fixed --now is for historical replay only: a future live run must acquire fresh GitHub metadata and create a new time-stamped snapshot. The checked fixture contains seven public PRs, not the full set, so its leaf summary is only valid within that subset.

## Next owner, provenance and boundaries

U: user requested traceable Git coordination without running scientific experiments or exposing private sources. F: actual public Git metadata, project AGENTS.md, GIT_RESEARCH_HANDOFF_20261113.md, CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md, and [issue #3](https://github.com/Bigbearbo/Rasengan_Binary_Creator/issues/3). T: eight local offline metadata tests; zero new NN, VM or SLE tests; no external NVIDIA or Gemini call. A: connecting this preflight gate to the authorized local dispatcher remains unimplemented.

Next owner: Codex orchestration, issue #3. Check existing local dispatcher first; then implement authorized live GitHub metadata fetch and a private SQLite/FTS5 work-id dedup/lease if useful. Do not auto-select a fork, auto-merge a PR, overwrite other research handoffs, copy private Library or private project materials into this public repo, or present a planned worker call as an executed call.

Status: candidate for dispatcher integration; verified only for the isolated offline metadata tests.
