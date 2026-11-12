# Codex repository guidance

This repository records Bigbearbo's Spiral Language Encoding (SLE) and Hamster World research. Treat historical designs, experiments, and open hypotheses separately.

For tasks comparing Spiral Language with the **ICFP 2020 Message From Space** language, start with:
- [docs/spiral_language_vs_icfp2020_for_codex.md](docs/spiral_language_vs_icfp2020_for_codex.md)

Research and implementation expectations:
- Read relevant existing source files and tests before making changes. Preserve old working code and describe every changed file.
- The ICFP 2020 functional/symbolic language and its bit modulation are distinct; **do not substitute the different ICFP 2024 language**.
- Spiral Language parsing needs applicable layer/word-width/offset/version information. Do not silently guess unknown grammar and write it into confirmed state.
- The highest **ever allocated** operator ID belongs inside the corresponding parser syntax-tree branch node, not in a separate authoritative registry. Do not infer it from currently present nodes; respect version profiles when re-encoding tokens.
- Separate user-authored ideas, repo/document evidence, reproducible test results, assistant hypotheses, and unimplemented proposals.
- Scripted two-agent parser demonstrations are **not** proof of language acquisition by a previously nonverbal neural network.
- Compare both languages under equivalent workloads, extension rights, correctness checks, and full resource costs. Do not assume either is superior.
- Report actual commands, tests executed, results, changes and remaining limitations. Never claim tests ran unless they were executed.

This file is navigational guidance; it does not supersede repository code or a task's explicit requirements.

For **all** SLE research tasks (not just ICFP comparisons), read [docs/spiral_language_research_index.md](docs/spiral_language_research_index.md) first. It links:
- `experiments/spiral_parser/`: runnable v0.1–v0.6 scripted twin-agent parser and test suite;
- `experiments/spiral_teaching/`: teaching packet generators, two-layer verifiers, archived bitstream codec tools;
- `experiments/spiral_semantics/`: synthetic SL09–SL18 vocab/history/ICFP-transport studies;
- `experiments/spiral_memory/`: separately scoped SNL-MEM human-readable grammar with synthetic tests.
Do not confuse these code families, or treat historical draft documents as the current binding protocol.

## Current research status and Pro follow-up design (2026-11-12)

Read [CURRENT_RESEARCH_STATUS.md](docs/ai_orchestration/CURRENT_RESEARCH_STATUS.md) before planning new SLE/NN work. It pins the separate P031/P032/P033/P034/P035 evidence revisions and distinguishes user direction, Codex training results, ChatGPT Pro's independent checks, and untested proposals.

**P033 diagnosis, coverage and teaching-order controls have been executed in [PR #7](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/7). Do not rerun P032/P033 as if pending.** Mixed teaching retained taught Echo but did not repair heldout generalization; pairwise-complete coverage was not a reliable fix. Read the pinned report before choosing the next experiment.

Codex has executed the E900 control and one near-equal-parameter attention configuration from the [Pro follow-up design](docs/ai_orchestration/PRO_RESEARCH_DESIGN_20261112.md); see [P034 results and evidence](experiments/spiral_neural/20261112_p034/README.md). E900 retained Echo test 12/12 versus historical Neg70 1/12 at equal Echo exposure, with unequal optimizer steps/MAC. B1 reached taught 27/72 and heldout 1/24; all six failed the frozen strong criterion, and matrix MAC was 15.333 times B0. These are completed tests, not pending proposals or a rejection of all attention. Do not expand this failed configuration or rerun completed controls as new results; freeze a new single-variable protocol before additional training. Native raw 0/1 remains the student input; do not add a teacher/parser that computes answers.

P035 has executed the12-student candidate from [Pro's small-network/growth review](docs/ai_orchestration/PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md); read [frozen design, results and evidence](experiments/spiral_neural/20261112_p035/README.md). This is input-codec by capacity timing with a shared response grammar, not shortest-native-output or complete codec-system cost. All12 finished and replayed exactly; final taught144/144, operand-heldout5/48, scores SF/202=3 and every other student=2, interactions0/-1/0. Values4/6 were absent as training operands but appeared in Neg teacher answers. Common trainingMAC caps give Growing more lessons; report that policy effect and all failures. Nested milestones and three paired seeds are descriptive. Do not rerun this frozen screening as pending or infer a broad SLE/attention/growth verdict. Any new variable needs a separate preregistration.

PR #5's shared corpus was not used for P032. True VM execution, neural translation and the orchestration MVP have separate completion states. Refresh relevant PR/ref status at the start of each task; keep historical reports and checkpoints unchanged. Delegate one bounded NVIDIA review when available without blocking local work if unavailable.

## Active Codex implementation work order (2026-11-12)

The user requested a shared-memory / multi-model coordination MVP for their local Codex, OpenRouter NVIDIA worker, and Gemini worker. Read [docs/ai_orchestration/CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md](docs/ai_orchestration/CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md) before working on this specific task.

Start with the P0 environment audit, then P1 memory index and P2 mock/dry-run dispatcher. Keep the original SLE/Hamster code unchanged. The repository is public: never commit API keys, private ChatGPT Library contents, personal chats, or runtime state. Other workers are advisory/read-only; Codex validates and integrates. Report real test results, not anticipated ones. See the matching GitHub Issue for task tracking. This work order does not automatically start any desktop process.

## NVIDIA worker delegation rule (2026-11-12; applies to relevant new research tasks)

**Do not forget the NVIDIA worker.** For mathematics curriculum work, start with primary-school SLE tasks before middle/high-school topics; use [CURRENT_RESEARCH_STATUS.md](docs/ai_orchestration/CURRENT_RESEARCH_STATUS.md) for the immediate research priority. Read [docs/ai_orchestration/NVIDIA_ELEMENTARY_MATH_MEMORY_20261112.md](docs/ai_orchestration/NVIDIA_ELEMENTARY_MATH_MEMORY_20261112.md) for curriculum, single shared SLE corpus, and Markdown+local SQLite memory design (SNL-MEM stays an experimental shadow). Before substantial SLE mathematics, shared question-bank, parser, compression-baseline, NN growth, or Hamster VM research, read [docs/ai_orchestration/NVIDIA_WORKER_TASKS_20261112.md](docs/ai_orchestration/NVIDIA_WORKER_TASKS_20261112.md) and check whether the configured OpenRouter NVIDIA worker can receive at least one bounded, read-only, nontrivial analytical subtask. Prefer independent math task decomposition and parser edge-case review; Codex retains coding, test execution, and final decisions.

When live worker access is available and authorized, **delegate at least one genuinely useful review/research task** rather than doing all analysis inside Codex. If unavailable or the work is trivial, continue locally and record `nvidia_status=skipped` with a reason. Each research result must briefly say which NVIDIA task was delegated, its result, and how Codex verified or rejected it. Never claim a model call occurred without a real API response. Do not send secrets, private Library notes, or unpublished user content to free endpoints. Daily free-tier allowance is an account-level maximum, not a quota to consume for its own sake.

## SNL-MEM research source (2026-11-12)

For work on the shared-memory orchestration MVP, also inspect [experiments/spiral_memory/research_archive_20261102/README.md](experiments/spiral_memory/research_archive_20261102/README.md). It is a **sanitized public research derivative**, with both v0.1 and v0.2 studies and tests. Do not treat it as a live memory store, a definitive bitstream SLE grammar, or a reason to automatically adopt SNL-MEM. Compare against ordinary Markdown under equal budgets, and never fetch private Library originals into this public repository without screening.

