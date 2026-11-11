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

## Active Codex implementation work order (2026-11-12)

The user requested a shared-memory / multi-model coordination MVP for their local Codex, OpenRouter NVIDIA worker, and Gemini worker. Read [docs/ai_orchestration/CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md](docs/ai_orchestration/CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md) before working on this specific task.

Start with the P0 environment audit, then P1 memory index and P2 mock/dry-run dispatcher. Keep the original SLE/Hamster code unchanged. The repository is public: never commit API keys, private ChatGPT Library contents, personal chats, or runtime state. Other workers are advisory/read-only; Codex validates and integrates. Report real test results, not anticipated ones. See the matching GitHub Issue for task tracking. This work order does not automatically start any desktop process.
