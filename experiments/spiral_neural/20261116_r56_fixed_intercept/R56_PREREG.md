# R56 — static-intercept equal-budget control (pre-execution freeze, 2026-11-16)

**Status at commit:** NO R56 neural forward, NO R56 optimizer update. Owner: independent native 01 small-NN lane. Parent is [R55 Draft #106](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/106) head `3d031b1481bc3006329e0aee66029cddb704d068`. Do not merge automatically.

## Exactly one intervention
Compare to R55 (eight **value-dependent slopes** trained with fixed R52 intercepts), by instead starting from the **same frozen R52 checkpoint** and updating only its **eight static cursor × source intercept logits**. No slopes; the 10,457 R50 backbone parameters are frozen. This is NOT a comparison of R55 and R52 with matched lifetime optimization; it isolates *type of the extra eight adjustable parameters under 500 additional updates*.

## Immutable dataset, protocol and resources
Profile `SLE-AE1-n5-v1`. 39 genuinely native 01 input bits:
`01 + 010 + bin3(r) + 0 + four*(bin5(operand)+0) + 111100`;
`r=1,2`, all a/b/c/d in 0–29; expected `r * (bin5(a if first else b)+0) + external STOP S`, with S a model output class (not a wire punctuation word).
Use the *identical* R52 teacher course of 136 events, 1,272 nonSTOP teacher-forced target-prefix pairs. Train 3 seeds 101, 202, 303; each 500 Adam updates, batch64, LR=0.04, samples by `np.random.default_rng(seed+55001).integers(0,1272,size=64)` with replacement. Overall 1,500 updates; 96,000 target presentations; 10,465 model parameters of which only 8 trainable. Theoretical **train forward** 1,048,320,000 dense MAC; excludes backprop/gate overhead. No early stopping, extension or oracle in free generation.

Use *the exact R55 evaluation manifest* — 32 validation and 64 test legal Q, each ×3 seeds — plus the fixed 80 historical retention Q ×3 seeds. These evaluation Q and the numerical domain have been exposed: the word "test" is a frozen split label, **not a new blind generalization claim**. R55 frozen predictions supply paired baseline without retraining.

## Gates frozen before inference
All must pass: (1) full test R56 ≥ R55 (44/192), (2) full test R56 ≥ original R52 (45/192), (3) retention R56 ≥ R55 minus12 (219−12), (4) each seed test loss against R55 ≤4/64, (5) all 528 free neural generations reproduced by PyTorch and separate NumPy implementation, with logit comparison. Keep all failures and individual seed trajectories, no post-test threshold changes.

Frozen local runner SHA256 `2197adbb9df85c5dd34269f6f1653240364daba2394e28d76bfe2be86f23c28c`; R55 manifest SHA256 `fd480fd1f8d1e88309fa7476b2be7721de7aca61f4c96b8ce6ac0870ae0f7fd8`. Frozen local prereg JSON SHA256 `e26173159cc52fb89e09e69a4e6a7aea5345c8fa4b570e8943ffca651a89bd4c`. These local bytes are not yet part of this Git freeze; **publish the exact runner and prerequisite bundle after execution**, and use its byte-hashes for replays. Preserve parent files unchanged.

Provenance: U = user goal and experimental-integrity constraint; F = public #106 and R55/R52 immutable artifacts; T = only static Python syntax check and hashing before Git freeze, no model training; A = extra intercept optimization might explain apparent value-conditioning effects, unproven.

NVIDIA calls 0: no accessible authorized local OpenRouter execution endpoint/key. Codex calls 0: no available local Codex runtime. No secrets, chats, or private Library exports in Git.
