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
