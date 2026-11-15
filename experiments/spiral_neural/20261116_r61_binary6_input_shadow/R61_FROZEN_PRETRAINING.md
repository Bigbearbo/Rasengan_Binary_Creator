# R61 frozen pre-neural specification (2026-11-16)
Status: **pre-training freeze**. This file is being committed before any R61 binary-shadow neural forward, Adam update, or result inspection. No trainer output exists at freeze. Scope: independent SLE small neural experiments, not VM or parser changes.

Source: Draft PR #111 head `f22721d54f751beee33ba7e0a8145e3b5437590c` (R60); historical R52 real weights and course. Isolated branch `research/sle-ae1-r61-binary6-isomorphism-20261116`.

Immutable local evidence SHA256:
- full structured `r61_prereg.json`: `813f91a308c2d3da26601ccac761ff5e4d064293d5e7e98064b021397dfcb500`
- 272-row raw SLE/binary6 paired manifest `r61_manifest.jsonl`: `9e82173c8223da698da1b5198a6afb57345592a6d87e89e38ef4576b99f9c012`
- fixed Python runner `r61_binary6_input_isomorphism.py`: `845dd2507c7702053ea270d8d2fee5a4e57fb37245d8f52be3cb18f072a3b76b`
Original source SHA table (12 source files) is in the fixed structured prereg; final share must include it.

Single intervention: for each of four value slots, convert legal SLE `bin5(value)+0` to ordinary `0+bin5(value)` (binary6). All four six-bit slots remain same width. Reorder the *frozen* tied source encoder weight columns with the identical cyclic permutation to preserve the exact initial function. Train only the eight original R52 learned source-gate parameters, using identical R52 course and training RNG. **Binary6 is a comparison input shadow, NOT a legal SLE word/profile**; keep canonical SLE output and the original host STOP behavior. Do not claim all-system codec superiority, new numerals, grammar discovery, or blind heldout.

Legal SLE source profile `SLE-AE1-n5-v1`: 39 bits `01+010+bin3(r)+0+4*(bin5(v)+0)+111100`; r1/r2; v0..29. Training: 136 historical lessons, 1272 bit targets; evaluation 80 retention + 96 legacy + 96 already-exposed new Q (272 × three seeds = 816); **no genuinely unseen Q**.

Seeds 101/202/303; original trained backbone 10457 frozen parameters; 8 trainable gate logits; total 10465. Adam lr=.07; 500 updates × 3 seeds, batch64 sampled with replacement using NumPy `default_rng(seed+52001)`; 96,000 target presentations. Approx. training forward 1,048,320,000 dense MAC excluding backprop; independent inference MAC reported afterwards.

Predeclared all-six joint gates:
1. All 272 legal source Q / exact binary6 shadows verified.
2. All 1272 training onehot source slots are cyclic rotations of original.
3. All 3 final gate-logit vectors have max absolute difference **<0.01** against recorded R52.
4. Binary-shadow free answers equal recorded R52 for **at least 810/816**.
5. Fixed gold first/STOP diagnostic max logit difference **<0.005**.
6. Independent NumPy full-answer replay **816/816**.

U: author requests independent native01 NN work and fair ordinary-binary comparison. F: R52 checkpoints/course; R60 / P030-P035 repository records. T (at freeze): static checks only: 272 paired questions, 1272 training source onehot rotations, 0 neural calls. A: fixed-width codecs should be reparameterization-isomorphic under coordinated initial weights. NVIDIA / local Codex / Gemini: 0 calls; no authorized NVIDIA endpoint. No auto-merge and do not touch Pro/Codex branches.

Any training error, gate failure, or subsequent verifier patch must be logged, not retroactively change this freeze.
