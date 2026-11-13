# AE1 native-01: frozen high-ID value-domain transfer, inference only

Work ID: AE1-NUMERIC-DOMAIN-PROBE-20261113. Owner: independent small-NN scheduled researcher (not Codex/Pro). Status at first commit: PRE-FORWARD, no new scores known.

## Single manipulated test dimension
High data word **v**: TRAINED-VOCAB values 6..14 versus NEVER-TAUGHT values 15..23. Both exactly nine IDs; keep **r=2**, low partner **s=0..5**, HIGH_FIRST and HIGH_SECOND orientations, c=d=0, frozen six model checkpoints. No architecture, instruction profile, training, target logic, optimizer, sample count, other input words or answer positions change. This is an *evaluation distribution comparison*, not a randomized intervention that isolates numerical magnitude, unseen combination, or the 16 bit. ID15 is especially informative: 15 has no bit16 but is still untrained.

## Exact profile and provenance
Legal SLE-AE1-n5-v1, Q=01+010+three-bit-r+0+four six-bit data tokens+END111100 (39 input bits); ordinary data ID0..29, UP31 reserved. Answer=first two full six-bit words followed by *external* S. Data bit word(v)=five-bit binary(v)+0. Q fixture high-second with a=0,b=6: 010100100000000001100000000000000111100; answer 000000001100S. L80, hidden64 tanh, 160 one-hot 01 slots, 3 output logits (0/1/S), 10,499 params, generation cap32. No teacher feature, no parser hints, no injected correct prefix during generation.

Immutable sources:
PR36 head 0b4a39342ee4ef00a0775ece7a2c20a1dfa08b25; parent Python source SHA256 05e2d730eecefcb50fa92392697556ffde313f5ecb59c2f4e583aad52e321303.
PR37 head 6a2162a687dc05b68034b2d00c287584a463f545; mixed runner SHA256 e5b6f8b0c382b2720efdfa8acaa75c8352a41226045cc7768824e1630b47024c; mixed protocol Git blob b25785764e1a4d55ed043c14b5412a9ec3e4a554.
Model source: 4 PR36 exclusive-role checkpoints + 2 PR37 MIX_PARITY checkpoints, seeds 101/202. No retraining, no state edits.

## Train/validation/test and costs
Original inherited training (unchanged): base low a,b 0..5 split via (a+b)%6: val=0 (6 pairs×r1/r2), test=1 (6 pairs×r1/r2), train=2..5 (24 pairs×r1/r2). Per-model supplement=36 r2 rows, v6..14 with s0..3, assigned high-first or high-second by PR36 exclusive role or PR37 parity mix. Original s4/s5 heldout never trained in supplement but already inspected; not new researcher-blind.

NEW evaluation matrix for each of six frozen checkpoints: 2 high-word domains × 9 IDs × 6 low partners × 2 orientations =216 Q/answers. Total 1296 responses: 648 known-vocabulary and 648 new-vocabulary. Primary metric: free-generated full-answer exact with S on **never-taught v15..23, s=5**, separately per arm, orientation and seed (9 items per cell); paired descriptive known-vocabulary v6..14, s=5. Secondary: all s0..5 exact, each six-bit word exact, bit16 output on the high word, STOP position, cap and full raw failure strings.

Seed=101 and 202 are checkpoint provenance, no new stochastic sampling. Original training budget preserved as provenance: PR36/37 250epochs, 948 target-prefix examples/epoch, 3750 batched Adam(.003) updates per model; *this run* 0 updates, 0 teacher-forcing scored predictions, 10,499 parameters per student. One forward dense MAC=10,432; hard maximum 1,296×32=41,472 forward, 432,631,? count MAC exactly from runtime. Backward=0.

## Fixed gates before all new Q forward
1. Verify parent source hashes, original PR36 and PR37 archived result/raw hashes, checkpoint finite shapes/tensor hashes. Independently reload old 720+360 archived raw responses and check exact reproduction first. If any FAIL, DO NOT evaluate new domain.
2. Verify every new Q is legal 39-bit SLE with r2, END/UP reserved, expected answer computed by independent transparent bit arithmetic (never by LLM inference); ensure exactly 1296 unique (seed,arm,r,a,b) model-case pairs, no duplicate across two domains.
3. No updates, no checkpoint selection, no extra seed or post-hoc adjustment.

A-priori interpretation: Do not call ID15..23 test a pristine investigator-blind domain: PR34 previously examined some of these IDs using *different* checkpoints. The present six student checkpoints never trained on them as answer values. If even MIX students get <5/9 exact for either role at s5 in either seed, reject practical cross-domain transfer for this fixed trial; otherwise report a limited positive only for observed fixed configuration, not generic bit-copy or a SLE advantage. Frozen outcome thresholds are descriptive; report every numerator and denominator regardless.

U: author-native-bit small-NN transfer research. F: immutable PR36/PR37 checkpoints, previous P030–P035 and AE1/UR1 branches. T: not yet executed at prereg. A: mixed-role education may improve learned-vocab positioning but does not guarantee unseen-vocab copy. No Pro/Codex branch edits, no merge. NVIDIA review only if authorized read-only worker exists; no request for secrets. Next owner NN reviewer / Codex for independent reproduction.
