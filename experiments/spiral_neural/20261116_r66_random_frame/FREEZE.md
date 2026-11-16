# R66 — before-training frozen causal contrast (2026-11-16)
Status: **FROZEN BEFORE R66 NN FORWARD/UPDATE**. This is an isolated native-01 small-NN experiment; no Pro UR1/Codex P030–P035/VM/parser changes. Owner: independent scheduled NN research.

## Question and sole intervention
R64 reported truthful joint-frame supervision Echo+STOP test **165/192** versus same architecture math-only **149/192**. R65 detached its auxiliary frame gradient and produced **149/192** math. R66 checks whether R64 benefit requires truthful `01` structure or can arise from any similarly weighted BCE gradient. Relative to **R64 joint**, only replace TRAIN frame labels: RNG NumPy `default_rng(66066)` permutes 256 base indices, invert the framing label for every row in the first 128 selected base groups. All four rows of each base flip together; each base still has two positives and two negatives, duplicate legal rows agree. True val/test labels and ALL Echo math targets unchanged. Shared-trunk gradients remain enabled.

## Exact fixed source and model
- R64 reference training script SHA256: `a8c4ffe2e0cb79f7575f84cf2b4e34f4d3a3ff4e2e54f8076f36b062540dc550`.
- R64 reference raw manifest SHA256: `2201dc52d2c9b28bbf05439e85fb8b5405a963e4dc10c70468c748eef0f14ea2`.
- R64 raw prediction control SHA256: `14abe2ca3f91138a005ea1f368ebe45a7d777aaf17595febfafd26ce52ccd249`.
- R66 exact Python runner SHA256: `28ac5ede380664cde2dee4e5a2eb3ebff68ce032f6743c467c2d9b437fdfebb1`.
- R66 fixed per-base 128-of-256 inverted mask JSON SHA256: `63e7bdb17041faea0b4a9986cd0bc0a47c4e009b7a30ccd31735b97659a26d01`.
- R66 complete local prereg JSON SHA256: `a8148bc2d486956f16da5c3abb445c45fb9bc707826dda81ee1703de170b3fa8`.
- Complete runner and manifest will be supplied after execution in the immutable companion ZIP. Public freeze hashes identify the **exact** inputs before training; Git alone is not claimed to contain weights.

Profile: lawful `SLE-AE1-n5-v1`, 39 raw bits `01+010+bin3(r)+0+4*(bin5(v)+0)+111100`, r1/r2 and numeric v=0..29. `00`/`11` training and `10` withheld are **malformed-root classification probes only**. Teacher math target for legal input is 6-bit Echo(a) or Echo(a,b) plus external STOP class S; parallel 13-slot head, **not** autoregressive 3-round Codex model or on-wire punctuation. Dataset same 1472 R64 records: train256 base×4=1024 numbers0..23, val48×4=192 numbers24..26, test64×4=256 numbers27..29; same val/test were exposed in R64/R65, so this is **not blind generalization**.

Three new students seeds101/202/303, identical torch init `seed+64000`, minibatches `numpy.default_rng(seed+64001)`; same tanh64 shared 39-bit MLP, 13×3 math and binary frame heads, 5,160 trainable parameters, **5,056 forward dense MAC/row**. Each seed Adam lr0.006, global gradient clip1, batch64×600 updates, math cross-entropy + shuffled frame BCE. No early stop / test-informed extension. Total **1,800 updates, 115,200 presentations, 582,451,200 forward training MAC**, excluding backward, probes and independent verification. R64 controls not retrained.

## Precommitted gates (all eight required for overall PASS)
1. Frozen script/manifest/mask hashes & legal SLE profile verified.
2. Every training base remains exactly class-balanced after permutation (512 positives).
3. Initial states, batch order, architecture, updates and theoretical MAC match R64.
4. Independent NumPy replay of 1,344 new predictions, frame logits tolerance <1e-4.
5. Truthful R64 joint math test exceeds R66 randomized-label math by **at least 6 of 192**.
6. Truthful R64 joint frame classification exceeds R66 shuffled-label arm by **at least 96 of 768 test frame cases**.
7. R66 STOP correct positions ≥180/192.
8. Truthful R64 joint math is at least as good as R66 randomized-label arm in **2/3 individual seeds**.

Report every gate and negative case, including two-way rescue/loss transitions, without reruns. A math difference here can support truthful auxiliary supervision **within this architecture**, but cannot establish SLE superiority versus ordinary binary or comprehension of variable widths.

Provenance: U user research mandate; F R64 #115 + R65 #116, Pro UR1 #12, Codex P035 #10 and separate shared-bank #5; T at freeze = deterministic static checks only, **0 new R66 NN forward or updates**; A = hypothesis about structured signal vs arbitrary auxiliary regularization. NVIDIA actual 0 (no authorized callable local worker in this runtime), Codex 0, Gemini 0. Next owner: independent NN researcher; no merges.
