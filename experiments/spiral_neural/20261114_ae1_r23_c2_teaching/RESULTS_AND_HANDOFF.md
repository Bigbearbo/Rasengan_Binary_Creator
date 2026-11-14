# R23 — 無關 c2 教學曝光，三位真實 SLE01 小型神經學生（2026-11-14）

**Formal preregistered gate: FAIL 0/3**. This is **not** evidence the teaching failed, because the gate was later discovered to be mathematically unattainable on the frozen panel. Preserve this negative result and the protocol defect; never silently regrade.

## Frozen evidence and factor

The exact 72 new raw01 Q were committed **before** any new neural forward: `bd3342477de7fcada5aaa2a19658393c15d2ade9`, SHA256 `81a6be7650ac89380434535e9df361ce461e9cafe7dd2d5dca835cd3dfa67f5e`. Pre-training 3-seed protocol committed `d5c1f0cd6ea1070c50b621f73049e0ce198c7a32`, including immutable full training runner SHA256 `8c9179cf36a56104af7d6323823e417a8a9ea7a004517f3f70087076656c1df3`; course SHA256 `b542f32b592cc68eecc7b7029eb93c7f061d07f5e89ed8ea2a6ea5785cf921d5`. These preregistered files were not edited after result exposure.

Single intervention: in original R20 ordered 136 presentations, replace only c=0→2 in the 24 first-block `r=1` lessons. Same 120 parent +16 high-bit events, answer targets, target order, model/initialization procedure, Adam, and update budget. R20 three historical real checkpoints reused, **not retrained**. Three new R23 students (seeds 101,202,303) have 10,457 params each, 150 epochs, 1,408 training targets/epoch, 3,300 Adam steps each / 9,900 total, 633,600 forward targets, 6,918,912,000 theoretical training-forward dense MAC (backward excluded), optimizer lr.003, batch64, clip1. The 136 event sequence increases distinct lessons from 112 to 124 **as a consequence** of c2 substitution; that potential diversity contribution is not separately isolated.

Legal profile `SLE-AE1-n5-v1`: raw Q `01+010+r(3bit)+0+word(a)+word(b)+word(c)+word(d)+111100`, with `word(n)=binary5(n)+0`, Q length39, values0..29, r1 output `word(a)+S` where S is an external STOP class, **not a raw SLE bit**. Val 24 Q b12/13; test48 Q b10/11/25/26; both a0..5, c0/c2,d1,r1. This is novel exact-Q holdout, not a fully researcher-blind semantic domain.

## Formal results, including gate defect

Pre-registered PASS per seed required test c2 STOP gain >=4/24 vs R20, no more than 2/24 loss on c0 STOP, old base-response retention >=42/48; 2/3 seeds required. **0/3 FAIL**; after evaluation R20 c2 STOP was already 24/24, 23/24, 22/24, so no seed could possibly gain 4. The criterion was poorly calibrated, and its FAIL cannot identify a failure to learn.

| Seed | R20→R23 test c2 STOP /24 | c0 STOP /24 | Mean (c0 minus c2) STOP margin R20→R23 | Old base exact R23 |
|---|---|---|---|---|
| 101 | 24→24 | 24→24 | 4.748→2.568 | 48/48 |
| 202 | 23→24 | 24→24 | 6.691→4.494 | 48/48 |
| 303 | 22→24 | 24→24 | 2.955→1.284 | 48/48 |

All new full-Q test answers: original R20 141/144 → new R23 144/144. Validation full old70/72→new72/72. Taught-high retention 96/96; old baseline full 144/144. Mean c2 absolute STOP margins improved in all 3 seeds, so the margin shift is a descriptive secondary sign of local c2 learning, not a rescue of the primary FAIL.

**Posthoc, researcher-seen** R21 and R22 diagnostic panels evaluated with frozen models *after* formal results: R21 c2 STOP old13/30→new19/30, R22 old18/36→new28/36; **seed202 remains 0/10 on R21**. These are diagnostic transport checks, **not new independent blind-test wins**, and no second optimizer pass was run.

## Real execution, independent verification, and source trail

Actual training completed once for each of 3 new students: 9,900 optimizer steps, NumPy2.3.5 / PyTorch2.10.0+cpu. 912 free-generated native01 outputs (R20+R23 6 models × 152 Q each); 9,353 total formal Torch forward probes (8,441 greedy + 912 teacher STOP). Theoretical infer dense MAC 102,134,760. Complete PyTorch replay **912/912 exact**. Independent NumPy engine **912/912 complete outputs + STOP logits**, max absolute logit error 2.86102294921875e-6; posthoc independent 480/480 logits. These confirm reproducibility, **not that 912 answers are correct**. Clean extracted ZIP: SHA256SUMS 24/24 + manifest, public preflight PASS, frozen gate PASS, Torch replay PASS, independent NumPy PASS.

One preserved historical R20 runner field issue: `stop_correct` at cursor6 on `r=2` items is actually scoring first bit of answer word two, not STOP. Only exact whole output is used for r2 retention; one-word STOP metrics use r1 exclusively. No rewriting original raw evidence.

Companion ZIP `sle_ae1_r23_nuisance_c2_training_20261114.zip` is **required** for 6 original checkpoints, complete training runner, 912 raw results/logits and clean independent reproduction. ZIP SHA256 `be906fefa585d1c85b5256ba75292f25fbb05bee35dfb7475663c72f4b6a6496` (artifact shared in associated conversation). Git itself contains public prereg Q, protocol, SHA-matching `public_preflight.py`, and this report, **not** the 6 checkpoint binaries. Do not claim Git-only replay is possible. This is a separate branch/draft PR with **no merge** and no VM/Pro/Codex changes.

U = author's SLE 01 small-neural education/growth priority; F = R14/R20 immutable source, historical checkpoints and published P030–P035/Pro UR1; T = this run's 3 student updates and independent checks; A (medium only for this limited teaching setup, low for general language acquisition) = varied irrelevant c word might train output invariance. NVIDIA calls0 (no authorized configured endpoint), local Codex calls0, Gemini calls0; no private secrets sent.

Next owner: independent small-NN researcher. **Do not repeat R23**. Freeze a more difficult non-ceiling c-disturbance transfer panel, with baseline performance calibrated on a *different calibration split* before final gate is fixed; do not inspect the final test first. Keep original/modified checkpoints fixed when diagnosing out-of-context transport. Separately design equal-budget standard-binary structure-matched control before making SLE superiority claims. For math education, PR #5 is benchmark semantic coverage only, not student success.
