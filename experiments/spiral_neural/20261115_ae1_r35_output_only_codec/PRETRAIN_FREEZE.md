# R35 — PRETRAIN FREEZE (no neural training when this file was published)

Work ID: `SLE-AE1-R35-SLE-IN-BINARY6-OUT-20261115`
Owner: independent scheduled SLE small-NN researcher.
Parent: R34 [PR #84](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/84), head `a3de2320428683b11328ffd8f9f457de0d2dbaba`.

## Single factor and profile
Hold the 39-bit input in legal `SLE-AE1-n5-v1`, hold the AE1 question frame and every semantic training tuple; replace only the six output numeric bits (SLE 5-information-bit + suffix 0 vs ordinary six-bit padded binary). The ordinary binary output is **not** a legal SLE profile or a complete second language. External `S` is an output stopping class, not a raw input bit. R1 answer six numeric bits + S; R2 twelve bits + S. No large-model teacher to compute labels; deterministic `a`, `b` numeric echo truth.

Historical equal-budget cells are R31 S-input/S-output, R34 B-input/S-output, R33 B-input/B-output, each from original checkpoints; **do not retrain** them. New cell R35 is S-input/B-output. This fills a 2×2 numerical word-layout comparison, not a full language comparison.

## Frozen curriculum and accounting
Exact **136 ordered teacher appearances / 122 distinct semantic tuples**, **1,408 prefix-target pairs per epoch**, 150 epochs, minibatch 64, deterministic shuffle `numpy.default_rng(seed+201000+epoch)`; three seeds 101, 202, 303, Adam lr 0.003, gradient norm clip 1. Initialization `torch.manual_seed(seed+12000)` then same initial tensors as R31/R33/R34. NoFirstMask 10,457 parameters (first-word input unmasked; unchanged second-word role mask), 3,300 updates/student, 9,900 new updates, 633,600 target presentations, 6,918,912,000 forward-only training dense MAC (backward excluded), 10,920 MAC/target.

Test semantic tuples and split fixed before training: validation_low 8, test_unseen_low 32, test_unseen_high 16, test_near 32, train_retention 40, test_stop 16 (144 total, 3 seeds ⇒ 432 complete outputs). `a=6,7,12,13,14,15,28,29` withheld from first-word train role, but **previously seen by researchers in other experiments**, so this is not globally blind. Autoregressive free generations with 32-token cap; score first six output bits, exact autonomous answer, and separately teacher-correct-prefix STOP. Any failures stay in the record.

## Precommitted symmetric primary gate
R35 S/B wins versus R31 S/S **only if all**: pooled unseen-low+high first-word gain ≥12/144; autonomous exact gain ≥12/144; course-retention exact loss ≤15/120; teacher-prefix STOP loss ≤12/48 on test_stop; and ≥2 of 3 seeds have nonnegative first-word gains. Reverse the inequalities and safeguards to call S/S a winner. Otherwise **INCONCLUSIVE**; never pick seeds or extend training after seeing results. Secondary factorial interaction (BB−BS)−(SB−SS) on heldout first-word/exact/STOP is descriptive only; three seeds are insufficient for broad causal or superiority assertions.

## Frozen SHA256 values (before any NN train)
- Exact runner `r35_output_only_codec.py`: `3f617c46cf67bd641bb0919b01199689cb13954c15b2403da76d115b5440a0a6`
- Prereg JSON: `7174a5e646dee2f37666dae5415604322fa09bbad05e09b3f942f1e9d77a1535`
- Training raw01 JSONL manifest: `ae94e8d7f4c730ce6b26451d57edd228a2ab3c93b664e84356b0905bb0897d72`
- Test raw01 JSONL manifest: `02f04ba556c4c70e49122371d5ee61e0cc2f82dce171602b3e02a394b5782825`
- Source `r33_binary6_control.py`: `6ed0248820e5b7f603714365644e41fe44391dc2086574a2053ec85f4027a17e`
- Source `r31_runner.py`: `d83a828df067e17d931477842b79bb51a303b61c2a39e7cecaf84b377ed7982b`
- R33 prior raw: `ea08bb175eb02c37fd8017854e57f9c915da3232d34061aa00cce976b196f79e`
- R34 prior raw: `87e60d1945c654d684012d89c7395746dc1e4030d5d65e99f687f42825e7148d`

Exact training row example: `Q=010100010110000000100000100000000111100`, `expected=011000S` (r1,a24,b2,c2,d0).
Exact test row example: `Q=010100010001100100000000000000100111100`, `expected=000110S` (r1,a6,b16,c0,d2).

Freeze + static gate performed locally with `python r35_output_only_codec.py freeze` and `python r35_output_only_codec.py gate`: PASS; these calls do not train NN. Complete JSONL, source and previous checkpoint SHA are kept in companion artifact and independently verifiable at execution. Git PR only contains public handoff/validation; **Git-only checkout does not contain all historical weights**.

Pro [PR #12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12) already has an actual failed UR1 neural training and is unrelated to this separate AE1 2×2. Codex P031–P035 are already executed; no repeats or changes to their stacks.

U: user requests independent 01 small NN and equal-budget control. F: R31/R33/R34 immutable artifacts, repository rules and existing P031–P035/UR1. T: only static frozen SHA/gate before training. A: direction of output-code effect unknown. NVIDIA actual calls 0 (no available authorized endpoint), local Codex 0, Gemini 0. No VM/parser core edits, secrets, private texts or automatic merge.
