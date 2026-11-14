# R33 pretraining frozen protocol — 2026-11-15 (Asia/Taipei)

**Status at this Git commit: specification, 144-case manifest and local runnable Python source generated and statically checked; 0 new neural forward/optimizer steps. This file precedes all R33 training.** Owner: independent scheduled small-NN researcher, separate from VM, syntax, P030–P035 and UR1.

## Sources (F)
- Frozen baseline: R31 [PR #81](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/81), head `0fdbf0c79b4a91d2d492426c3854d3d188b07773`; companion archive SHA256 `961bad8563c23363c71812aab1c22b961c7f1f022b1896d3f107c3f19059776f`. Reuse its three real SLE checkpoints **without retraining**.
- Immediate handoff: R32 [PR #82](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/82), head `711a853403049b7fae4fbbbbcdbb81bb5e62e1b4`.
- Independently examined AGENTS.md, Git handoff, Pro PR #12 status/handoff, Codex P031–P035 results and more recent PR #61. P035 already contains a **different input-codec × growth experiment**, so R33 asks only about six-bit numeric-word placement in AE1, not an untested complete SLE advantage.

## One factor (A)
Paired arms under identical 39-bit question slots and six-bit answer slots: native **SLE-AE1-n5-v1** word `f'{n:05b}0'` vs **BINARY6-IN-AE1-FRAME** control `f'{n:06b}'`. Every `n` is an integer 0..29. Both question words a/b/c/d and output numeric words change according to the codec **as one joint representation policy**. Both use the same fixed SLE-like `01 010 rrr0 ... 111100` framing, same 6-bit positions, same literal 0/1 input/output, same external S stop. The control is *not* a legal SLE profile; it is ordinary padded numeric words **inside a shared frame**, **not** an entire ordinary-binary language, much less a full hierarchy comparison.

Model R30 `NoFirstMask`: 10,457 parameters, per-word tied 6bit input encoder, a separate hand-routed r2 secondword role, position features. This gives both arms the same structural prior; it is **not** an architecture-blind comparison. The representation changes both inputs and teacher target bits (honestly acknowledged), while numerical labels/tasks remain exactly matched. All expected answers are deterministic codec mathematics, not another neural or LLM oracle.

## Frozen course, split, model budget
Same R31 ordered 136 teaching appearances (122 distinct semantic tuples), 1408 teacher-forced targets/epoch; binary6 arm freshly trains three seeds 101,202,303 from original matching SLE init: torch seed+12000, WordStudent(True) initial weights copied to NoFirstMask, Adam lr 0.003, grad clip norm1, 150 epochs, batch64, shuffled indices numpy seed+201000+epoch. Exactly **3300 optimizer steps/seed, 9900 new steps total**, **633600 target presentations**, **6,918,912,000 theoretical training-forward dense MAC** (10920/target; excludes backward). R31 SLE arm is the already-trained same-budget comparator.

144 fixed semantic evaluation questions/arm: 8 validation a6/7; 32 test_unseen_low a12..15; 16 test_unseen_high a28/29; 32 test_near a20..23; 40 exact train_retention (first 40 distinct course tuples, including r1/r2); 16 test_stop a8..11. b/c/d contexts and order generated entirely by frozen `r33_binary6_control.py`. The **eight evaluation a values 6,7,12..15,28,29 are absent from the a role in training**; other roles may contain numeric values, and some had appeared in historic diagnostics, so these are new heldout for the current students, **not globally blind to researchers**. STOP is explicitly a teacher-correct-prefix diagnostic, separately from free-run complete answers; r1-only for test_stop.

**Predeclared descriptive gate** (not a p-value): SLE advantage only if SLE minus binary6 pooled firstword correct on unseen low+high (48 questions × 3 seeds =144) ≥+16, free-run exact ≥+12, exact train retention ≥−15/120, true-prefix STOP ≥−12/48, and unseen firstword SLE≥binary6 in at least 2 of 3 seeds. `BINARY6_ADVANTAGE` uses symmetric thresholds; otherwise `INCONCLUSIVE`. Always disclose both absolute scores and any near-domain regression. No checkpoint/seed selection and no training after seeing test results.

## Immutable local source and manifest commitments (F)
- Python runner `r33_binary6_control.py`: SHA256 **`6ed0248820e5b7f603714365644e41fe44391dc2086574a2053ec85f4027a17e`**
- `r33_prereg.json`: SHA256 **`e9a794f92e02b03b674358e125a42a42a8f08b02308df2f1649a4006927bad5d`**
- `r33_manifest.jsonl` (144 rows with both raw question and answer bits): SHA256 **`0f301ffe93bb151917d2fbe45dcde496e4a75e4e1f86995e0b20a32bc9ad16aa`**
- Source R31 `r31_runner.py` and weights have individual immutable SHA entries within the frozen prereg JSON.
- Actual local preflight at freeze: `python r33_binary6_control.py freeze` and `python r33_binary6_control.py gate` **PASS**, no neural forward. The full runner, JSON, manifest will be supplied with accompanying portable evidence. They are **not yet Git-uploaded at this first commit**; do not claim otherwise.

## Provenance
U: author requests native01 small-NN, education, genuine generalization and fair baselines. F: named PRs, old real checkpoints, frozen exact hashes. T at freeze: static corpus/profile/hash/parameter checks only. A: numeric-bit placement may alter extrapolation; causality of internal representations unknown. No NVIDIA authorized callable in this environment; planned actual NVIDIA calls 0. No local Codex/Gemini calls; no secrets or private material. After freezing, execute one fixed run and preserve FAIL/results, then verify and hand off without auto-merge.
