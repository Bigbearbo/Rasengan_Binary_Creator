# AE1 R18 — FROZEN BEFORE ANY R18 NEURAL FORWARD (2026-11-14)

Work ID: AE1-R18-FIRST-WORD-HARD-ROUTING-20261114. Owner: independent scheduled SLE NN. This is **not** Codex/Pro UR1 approval, and does not modify Hamster VM or protocol dictionary.

## One isolated factor
Compare three R14 **immutable** full-input balanced8_16 checkpoints (PR #63, original head `b197299ec7b48f0a07118582be981bb5aaeb3318`) with three newly trained, identically initialized and equally parameterized/updated 10,457-parameter students. Only difference: in the *first 6 generated bit positions*, zero out input embeddings for words b,c,d before the common hidden layer, so first-answer bits see word a + header + cursor only. Second answer and STOP see all words, exactly like baseline. No answer oracle gets fed to the student. This **hard-codes invariance**, so invariant predictions cannot count as learned copying/generalization.

## Immutable inputs, seed, cost, split
Profile: `SLE-AE1-n5-v1`. Native Q: `01+010+(r as 3 bits)+0+four ((ID as 5 bits)+0)+111100`, Q length39, IDs 0..29. Offline target `word(a)+(word(b) iff r=2)+S` where S is external STOP, not a transmitted 01 bit. Network inputs are only raw 01 prefix/one-hot with position derived from occupied length. Same R14 training: 120 parent + 8 bit8 + 8 bit16 lessons = 136 appearances/112 unique; 1,408 next-symbol targets per epoch. Seeds101/202/303; Adam lr.003, 150 epochs, batch64, clip1; 3,300 updates/student = 9,900 total; 633,600 new training target forwards, 10,920 nominal dense MAC/forward, 6,918,912,000 training forward dense MAC (backward excluded). Comparison reuses baseline weights: 0 baseline retraining, no cherry-picked checkpoints.

Freeze manifest in local companion ZIP as 168 exact raw Q with SHA below. Deterministic generation order and tuples: seen_baseline r in(1,2), a0..5, b(18,19,22,23),c0,d0 =>48; taught_high a(8..11,16..19),b0..3,r2,c0,d1 =>32; validation a24,b(4,5,16,17),r2,c0,d1 =>4; test_new_a_d2 a25..29,b(18,19,22,23),r2,c0,d2 =>20; test_new_a_new_b a25..29,b(16,20,17,21),r2,c0,d1 =>20; test_new_a_extreme a25..29,b(0,5,9,29),r2,c1,d2 =>20; paired_invariance a24..29,b(16,20,17,21),r2,c0,d2 =>24. 168 distinct Q, 5-bit words. a24..29 never in training first-word. Several IDs/context patterns have been previously viewed by researchers; do not call this fully blinded research.

**Predeclared learning gate:** at least 2/3 seeds: routed first-word exact on test_new_a_d2 + test_new_a_new_b (40) exceeds immutable full-input checkpoint by at least 8; routed exact seen_baseline >=40/48 and taught_high >=16/32; plus 12/12 paired b16↔20 and b17↔21 first-output invariant. The invariance criterion is merely implementation audit, not independent learning success. All seeds and negatives retained, no changes after evaluation.

## Hash-frozen source (SHA256)
- R18 runner `4793596815bcac55803fae9bcb3a09526caaa7e10dbd00e6f645ae325e256722`
- R18 manifest (168 newline-delimited JSON raw-bit Q/expected) `1b16c0cf72d9a9517959aac21b8cf9e7a81110b7ab6c2b52dd634d181c5ca3cc`
- Frozen R14 runner `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a`
- R14 parent course `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a`
- Exact new training course JSON compact SHA `5c40359f46f23452b571edab5872a077fd1f296b7619cfe01d25b16951e47d40`
- Immutable balanced checkpoint F32 JSON: seed101 `a39194ac3c3abc8d5904eec35c46e2179c47c60895e14f5d9ffa84b839d9c0fa`; seed202 `f177fe19471d3b4d7612a90a7483d9d01602e2636e9f8011a1b9ff420137feb9`; seed303 `3045399adffdc0578ae8d0be7c233b78ed568c63d123471a97f959f8111b6ebd`.

Preflight run before Git freeze: `python run_r18.py gate --source-root <R14>`: PASS, static only, zero R18 neural forwards/optimizer updates. Frozen local runner + prereg + raw-bit manifest will be published intact after actual run with a companion ZIP holding full checkpoints and raw results.

U: user authorizes SLE small NN curriculum/generalization work. F: R14 PR63 immutable source, R17 PR66 diagnosis and hashes. T at freeze: static schema/hash checks only. A: constrained first-answer route might improve robustness but could degrade capacity/integration. NVIDIA: no authorized callable worker endpoint, zero calls; local Codex and Gemini zero; no secrets or private materials.

Next owner: independent SLE NN; report actual output and failures, numerical replay, and distinguish enforced structure from learned ability. Do not auto-merge.
