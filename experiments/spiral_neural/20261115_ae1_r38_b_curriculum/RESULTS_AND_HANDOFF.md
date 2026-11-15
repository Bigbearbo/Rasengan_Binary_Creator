# R38 — SS second-role high-b lesson replacement: real NN PASS with a retention cost

Date: 2026-11-15. Independent SLE 01 tiny neural student work (not Codex P030–P035, Pro UR1, VM, or parser). This post-result report **does not alter** [the committed pre-training freeze](PREFREEZE.md), commit `ba4e7ef1b5d343959e252f67d71c9325965327a5`. R37 Draft #87 is the parent.

## Frozen intervention

Only **8 r=2 b-role teacher occurrences** were replaced: old b20/21/22/23 → new b26/27 (two occurrences of each old value, four each new value), at indices 68,70,73,75,76,78,81,83. R31 original 136 ordered training events, all r/a/c/d, model/optimizer/init, 3 seeds, targets and budget otherwise unchanged. **SS SLE input/SLE output only**. Legal `SLE-AE1-n5-v1`, integers 0..29, numeric word = 5 information bits + terminal 0, Q = 39 literal raw 01 bits. Output two 6-bit words plus external STOP action (not a wire bit). 10,457-parameter no-firstword-mask student, engineered secondword b-only input mask.

The **joint preregistered** PASS gate required high b26/27 secondword ≥24/48; old b18/19 ≥44/48; displaced b20–23 ≥36/48; historical exact answer retention loss ≤12/240. Historical validation did not choose hyperparameters, model/epoch, or data. The high-b test values were previously inspected by R37; **not global/blind novel values**, only unseen previously in training second-role.

## Measured results (all seeds combined)

| Metric | R31 original | R38 trained | Note |
|---|---:|---:|---|
| b26/27 second word | 0/48 | **48/48** | 16/16 each seed |
| old b18/19 second word | 48/48 | 48/48 | kept |
| displaced b20–23 second word | 48/48 | **40/48** | seed202 8/16; others16/16 |
| old-domain full answer | 240/240 | **228/240** | 12 exact losses, seed202 |
| high-b full answer | 0/48 | **1/48** | still poor free generation |
| high-b first word | 3/48 | **2/48** | still poor |
| high-b true-prefix STOP | 16/48 | **13/48** | still poor |

**Frozen combined gate PASS 4/4**, though historical full-answer retention drops exactly the allowed 12/240. There is no evidence here for generally learned copying or mathematical rule transfer. R38 seed202 r2/a0/b22/c0/d0 expects `000000101100S`, but generated `000000100000S`. On r2/a14/b26/c1/d5, target `011100110100S`, original model outputs `110110100100111...`, newly trained model outputs `110110110100111...`: correct second word now, but first word/STOP still wrong.

**Post-result scope correction, no data change:** the frozen machine name `prior_r1_retention` is misleading. The *same* 80 Q per seed are **24 r1 and 56 r2**, not 80 r1. Exact r1 performance remains 72/72→72/72; r2 declines 168/168→156/168, accounting for all 12 full-answer losses. The preregistered raw Q, threshold and evaluation were not changed. Interpret fourth gate as *historical mixed-arity retention*, not an r1-only result.

## Actual compute, test receipts, portable evidence

- **New training:** three 10,457-param students, seeds101/202/303, 150 epochs, 3,300 Adam steps per seed, 9,900 total updates, 633,600 target presentations, **6,918,912,000 theoretical train-forward dense MAC**, excluding backprop.
- **New neural inference:** 384 R38 complete raw 01 outputs, 6,806 forward calls; 288 additional R31 comparator outputs, 4,417 forwards. Historical R36/R37 96 SS controls reused without rerun. **672 actual new complete NN generations**, **11,223 forward evaluations**, **122,555,160 inference dense MAC**, 768 total archived rows.
- **Replay:** R38 PyTorch full generation **384/384 PASS**, independent NumPy **384/384 PASS**, max stop-logit discrepancy `2.86102294921875e-6`.
- **Cold extracted companion ZIP:** 150/150 individual SHA256 entries PASS, read-only independent record integrity PASS, PyTorch and NumPy full replays PASS.
- Frozen runner SHA256 `8704b05a8b1ec152fa9e3184e0248c6529ce975660277ba75c7375602d0a122e`; literal-Q manifest SHA `781e351ead001a74a30f75be3f92347bbe70530149a4fec126b23b35c90c35b9`; prereg SHA `8dfb4d25f96c6df2e908efc27383cbea5b0e784c20d778b28aa54de3defa04c6`; 768 raw responses SHA `438da17c8d40e3a280a4e70477dfaf106351a9f5e1857e475a6f3d9d9b4482da`.
- Original new checkpoint SHA: seed101 `07e4d54a7f19ace5bcd9bcb418a476dabc07e728e5c1db04d8f90345f4fb30b3`; 202 `43332a7419a566f1e3570474c04abb48645e4da07cf1f8cd92058bd794a73704`; 303 `db2150ee589686ea79a67c7ba9d8f3925399a04bc625ff9821ef0dbc2bd18cc9`.

**Portable ZIP:** `sle_ae1_r38_b_role_lessons_20261115.zip`, 2,337,598 bytes, SHA256 `4f418ef79a60e59a2bbd6682c205ca36dc27dffae7b9c602a272c4a99a7bca01`. Delivered as a conversation artifact, **NOT committed to Git**; exact frozen 200-line runner, all 3 new weights, source R31–R37 references, all 768 records, R38_SHA256SUMS, independent NumPy and read-only tests are inside. Git checkout alone **cannot** reproduce the neural run. From extracted archive: `python verify_r38_readonly.py`, `python r38_b_curriculum.py gate`, `python r38_b_curriculum.py replay`, `python r38_b_curriculum.py numpy`. Do not rerun `train` in populated outputs; it refuses overwrite.

## U/F/T/A and next owner

U: user request to test small independent SLE binary-bit neural learners and causal education/generalization under constrained resources. F: original P031–P035 and Pro #12 (UR1 neural ACK already completed), frozen R31/R36/R37 data. T: this independent worker's 3 actual model trainings, 672 actual new full neural answers, immutable prefreeze, historical comparisons, cold integrity and replay. A: 8 exposures likely repair a **role-conditioned** mapping; whether learned an actual bit algorithm is unresolved (low confidence).

NVIDIA actual calls 0 (no authorized live endpoint), local Codex0 (not present), Gemini0. No LLM teacher computing student output. No Pro/Codex/VM/parser branch modified, no merge, no secrets/private material.

**Next owner: independent tiny SLE NN researcher.** Isolate a new factor in an equal-budget trained student, ideally b-role routing architecture or controlled unseen legal domain, while recording firstword, secondword, exact and STOP plus displaced/old retention; do not equate the 48/48 role-specific result with general copying. No continuation training on this preregistered test.

[更新] Changing only 8 b-role teacher events restored unseen-in-role b26/27 success from 0/48 to 48/48, while preserving old b18/19. [取代] R37's zero score implied this NN cannot learn those b-values. [原因] A same-budget teaching substitution yields success, with displaced-value and whole-answer retention losses. [狀態] Direct observed result high confidence; internal learned mechanism low confidence.
