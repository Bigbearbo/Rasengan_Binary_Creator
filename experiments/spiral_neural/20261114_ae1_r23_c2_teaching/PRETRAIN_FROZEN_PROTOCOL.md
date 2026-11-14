# R23 / SLE-AE1-n5-v1 — PRE-TRAIN frozen experiment (2026-11-14)

**Frozen BEFORE new student training.** Author's (U) priority: independent small neural network that consumes/produces raw `01`. This is a supervised narrow echo/STOP lesson, NOT VM, parser, UR1 authorization, math mastery, neural-language proof, or general SLE-vs-ordinary-binary comparison.

## F — immutable sources and SHA256

R14 reference `r14_source/run.py` SHA256 `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a`;
`r14_source/parent_course.json` SHA256 `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a`;
R20 runner `experiment_r20/run_r19.py` SHA256 `dbfad19c66ae2dd3f20113e8eb7e965fd576f9984462fd6a82c029897a28f15e`.
R20 original seeds101/202/303 weight SHA256 in order:
`4231d63398493d683b94ab572f846a9267d5a20ad6a39edcec0baf976801b464`,
`0b241799b07458b144a3d2b9a6cf42f61f082d9b1b8377359878e5075bab5a62`,
`58137a8d4dacd33c1597bbdaa901a32640eb79060c9a16ebba0af8b2227d435a`.
Original R20 archive: `sle_ae1_r20_r1stop_route_repair_20261114.zip`, SHA256 `9c698971dfd6fe1f89701be99fc2fa592edce006f017efd5c4e89dbdf5671866`. Its checkpoint weights remain immutable, serving as the equal-budget historical control (not retrained). R22 diagnostic archive remains independent.

## Exact single causal intervention and training budget

Take the exact original R20 136 ordered lesson tuples `(r,a,b,c,d)`: `R14 parent120 + 16 balanced high8/high16`. Replace **only the c field from 0 to 2** in the 24 tuples with index (0-based) < 48 and r=1; all other tuples remain bit-for-bit identical. Preserve each of 136 teaching presentations, all 1,408 teacher-prefix targets per epoch, each target label and order, 60 one-word lessons and 76 two-word lessons. The modified 136-tuple ordered curriculum must hash to SHA256 `b542f32b592cc68eecc7b7029eb93c7f061d07f5e89ed8ea2a6ea5785cf921d5`. R20 original has 112 distinct lessons, R23 124 (increased diversity is a **consequence of the specified replacement**, not extra updates). This comparison tests the *package of c2 exposure with identical target budget*, not a controlled test of diversity alone.

Architecture R20 `DualRoutedStudent`, 10,457 float parameters, training forward dense MAC 10,920/target (backward excluded), input 39 native raw bits and next-position labels `0/1/S`. Seeds 101/202/303, identical initialization procedure `torch.manual_seed(seed+12000)` **before** constructing the original tied `WordStudent` and then loading it into the routed architecture; independent Adam lr0.003, clip1, batch64, 150 epochs, 22 batches/epoch, 3,300 updates/student, 9,900 total, 633,600 training forward targets, 6,918,912,000 training forward dense MAC. No new teacher/oracle computations during free inference. No resuming a final checkpoint, no extra seeds, no post-test retraining.

R23 frozen `run_r23.py` SHA256 `8c9179cf36a56104af7d6323823e417a8a9ea7a004517f3f70087076656c1df3`.
`manifest.jsonl` SHA256 `81a6be7650ac89380434535e9df361ce461e9cafe7dd2d5dca835cd3dfa67f5e`. Raw manifest is committed beside this file BEFORE running new neural forwards.
One-word profile: `Q=01+010+r(3bits)+0+word(a)+word(b)+word(c)+word(d)+111100`, `word(n)=5bit(n)+0`, Q length 39, r=1. Output `word(a)+S`; `S` is an explicitly external STOP label, not a literal SLE bit. Values 0..29, reserve 30/31, no grammar change.

## Data split and predeclared gate

Train = modified 136 ordered events; validation = `r1, a0..5, b12/13, c0/c2, d1` (24 new Q); TEST = `r1, a0..5, b10/11/25/26, c0/c2, d1` (48 new Q, 24 c2/c0 pairs). Retention: original R20 `seen_baseline` 48 and `taught_high` 32. Each new raw Q is absent from the original and amended training, the R20 heldout manifest and the R22 diagnostic panel. Previously studied conceptual value ranges are not globally researcher-blind.

PASS requires **at least 2 of 3 fixed seeds** satisfying simultaneously: (1) TEST c2 one-word STOP categorical accuracy improves by >=4/24 relative to original R20 frozen weights; (2) TEST c0 STOP decreases no more than 2/24; (3) `seen_baseline` whole-response exact >=42/48. Otherwise FAIL. Also report continuous STOP margin `logit(S)-max(logit(0),logit(1))`, validation, high-lesson retention, failures and actual free outputs, whether favorable or not; no cherry-picked checkpoint. This gate concerns nuisance robustness, **not general copying skill**.

## Provenance / execution notes

U author: independent small neural learning with growth and correct controls. F: original R14/R20 source/checkpoints; separate Codex P030–P035 / Pro UR1 / Codex PR61 and scheduled R22 are not rewritten. A hypothesis (low confidence): equal-budget c2 exposure improves STOP invariance. T at freeze: local STATIC preflight of profile, 72 exact raw Q, hashes and counts; **0 new optimizer updates and no new student logits**. NVIDIA status: no available authorized reviewer endpoint, 0 actual calls; local Codex/Gemini also 0. The planned result will be appended in a new commit with all failures, a downloadable independent ZIP and next owner, without auto-merge. Initial frozen runner+manifest+curriculum hash are immutable even if the result fails.
