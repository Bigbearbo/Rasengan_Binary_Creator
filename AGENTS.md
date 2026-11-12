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

## Scheduled research worker separation (2026-11-13)

For recurring research tasks and Codex/Pro handoffs, read [Scheduled research role contract](docs/ai_orchestration/SCHEDULE_ROLE_CONTRACT_20261113.md) before choosing a write path. Syntax/protocol, Hamster VM, neural training, Git coordination, and memory index maintenance have distinct owners; do not duplicate completed experiments or treat the public repo as a copy of private Project Library. The live schedule and enabled state exist in ChatGPT Automations, **not in this file**.

## Current Git research routing (2026-11-13; check live PRs every time)

**Start with [Git research handoff](docs/ai_orchestration/GIT_RESEARCH_HANDOFF_20261113.md), not the older P032/P033 work-order prose.** As last checked, Codex had already completed P031–P035 experiments, Pro completed UR1 notification codec, and a new UR1 neural-ACK trial was at the frozen pre-training stage in the stacked PR #8 → #9 → #10 → #11 → #12 chain. Those PRs are **not automatically merged into main**. Check latest open/merged PRs, their actual bases, and the branch-specific `docs/ai_orchestration/RESEARCH_HANDOFF.md` / `CURRENT_RESEARCH_STATUS.md` before selecting new work. Do not rerun completed P032/P033/P034/P035 solely because historical plans or main still call them next.

For any new experiment, distinguish existing F/T evidence, new T results, user-authored U hypotheses, and A proposals; preserve the verified corpus/manifest, negative results and immutable checkpoints. Work in isolated branches and make a concise evidence-backed handoff; do not merge stacked PRs or claim NVIDIA/Codex execution without actual results. The shared-memory dispatcher remains a separate engineering MVP and must not delay the active experimental PR's next responsible owner.

## Active Codex implementation work order (2026-11-12)

The user requested a shared-memory / multi-model coordination MVP for their local Codex, OpenRouter NVIDIA worker, and Gemini worker. Read [docs/ai_orchestration/CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md](docs/ai_orchestration/CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md) before working on this specific task.

Start with the P0 environment audit, then P1 memory index and P2 mock/dry-run dispatcher. Keep the original SLE/Hamster code unchanged. The repository is public: never commit API keys, private ChatGPT Library contents, personal chats, or runtime state. Other workers are advisory/read-only; Codex validates and integrates. Report real test results, not anticipated ones. See the matching GitHub Issue for task tracking. This work order does not automatically start any desktop process.

## NVIDIA worker delegation rule (2026-11-12; applies to relevant new research tasks)

**Do not forget the NVIDIA worker.** **Current first task is PRIMARY-school SLE math, not middle/high school.** Read [docs/ai_orchestration/NVIDIA_ELEMENTARY_MATH_MEMORY_20261112.md](docs/ai_orchestration/NVIDIA_ELEMENTARY_MATH_MEMORY_20261112.md) first for current curriculum, single shared SLE corpus, and Markdown+local SQLite memory design (SNL-MEM stays an experimental shadow). Before substantial SLE mathematics, shared question-bank, parser, compression-baseline, NN growth, or Hamster VM research, read [docs/ai_orchestration/NVIDIA_WORKER_TASKS_20261112.md](docs/ai_orchestration/NVIDIA_WORKER_TASKS_20261112.md) and check whether the configured OpenRouter NVIDIA worker can receive at least one bounded, read-only, nontrivial analytical subtask. Prefer independent math task decomposition and parser edge-case review; Codex retains coding, test execution, and final decisions.

When live worker access is available and authorized, **delegate at least one genuinely useful review/research task** rather than doing all analysis inside Codex. If unavailable or the work is trivial, continue locally and record `nvidia_status=skipped` with a reason. Each research result must briefly say which NVIDIA task was delegated, its result, and how Codex verified or rejected it. Never claim a model call occurred without a real API response. Do not send secrets, private Library notes, or unpublished user content to free endpoints. Daily free-tier allowance is an account-level maximum, not a quota to consume for its own sake.

## SNL-MEM research source (2026-11-12)

For work on the shared-memory orchestration MVP, also inspect [experiments/spiral_memory/research_archive_20261102/README.md](experiments/spiral_memory/research_archive_20261102/README.md). It is a **sanitized public research derivative**, with both v0.1 and v0.2 studies and tests. Do not treat it as a live memory store, a definitive bitstream SLE grammar, or a reason to automatically adopt SNL-MEM. Compare against ordinary Markdown under equal budgets, and never fetch private Library originals into this public repository without screening.
