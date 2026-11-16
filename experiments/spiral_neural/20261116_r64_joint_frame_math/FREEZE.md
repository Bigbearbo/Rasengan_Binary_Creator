# R64 immutable preregistration — joint 01-frame and elementary full-answer learning

Date: 2026-11-16. Research owner: independent SLE 01 small neural-network worker. This is a **new** raw-bit learner, not Codex P030–P035, Pro UR1, Hamster VM, parser, or grammar dictionary work.

## Source freeze before neural forward
- Parent: R63 Draft PR #114 head `38c77853720a916c0a1dd02f5ae8a5fa09d495f0`, branch `research/sle-ae1-r63-frozen-frame-guard-20261116`.
- Full experiment runner SHA256: `a8c4ffe2e0cb79f7575f84cf2b4e34f4d3a3ff4e2e54f8076f36b062540dc550`.
- Full 1,472-row raw-bit manifest SHA256: `2201dc52d2c9b28bbf05439e85fb8b5405a963e4dc10c70468c748eef0f14ea2`.
- Local full prereg JSON SHA256: `b479311aa0ac29bec11cb34524ca66738af3bcb0fa8442e0dc69fdf09de7fd57`.
- Frozen source, manifest and JSON exist in a local, isolated working directory. This Git file carries their hashes and core spec **before training**; the complete source and manifest will be preserved in a separately checksummed downloadable bundle. No claim they are already Git-hosted.

## Single intervention and controls
Test whether one **shared** 39-bit NN can learn valid SLE framing and elementary two-operand Echo full answers simultaneously without losing STOP/full-answer accuracy. Matched arms:
1. `math_only_lambda0`: shared 39→tanh64→(13×3 response positions + one frame-score head), math cross-entropy only;
2. `joint_lambda1`: identical model, same initial state, samples, seeds, minibatch schedule, Adam/steps, plus a BCE framing loss weighted 1 on the same examples.

Frame head exists and executes in **both** arms; only frame-loss weight changes. This is neither a pretrained R52 math student's fine-tuning nor an upgrade to the canonical SLE grammar. An independent deterministic two-bit `01` check would be cheaper, so no efficiency superiority is claimed.

## Legal format, bits and targets
- Profile `SLE-AE1-n5-v1`, native 39 bits. `Q=01 + 010 + bin3(r) + 0 + [bin5(v)+0]×4 + 111100`, `r=1|2`, `a,b,c,d ∈ 0..29`.
- True math output: `bin5(a)+0+S` (r1) or `bin5(a)+0+bin5(b)+0+S` (r2). `S` is a model/external termination **class**, not an invented SLE wire token. The full-answer output head predicts 13 parallel 0/1/S positions, stops at its first generated S (no gold prefix at evaluation), and ignores positions after gold S in training; unlike R52 this is **not autoregressive**.
- Illegal-root `00`, `11` diagnostic examples occur in training; `10` is withheld entirely until validation/test. No mathematical answer is supplied for malformed examples. All bits are given directly as 39 individual {-1,+1} scalars; no programmer-provided numeric decoder inside student.
- Example legal raw bits (r=1,a=4,b=0,c=0,d=0): `010100010001000000000000000000000111100`; exact raw strings are validated by the frozen generator before training.

## Data, seed, budget, gates
Deterministic NumPy RNG seed 64001, alternating r1/r2, 4 rows per unique base. Train 256 base Q with **all** operands in 0..23 (1,024 rows, duplicate one valid root for 50:50 legal-vs-invalid class); validation 48 base Q with all operands 24..26 (192 rows), test 64 base Q with all operands 27..29 (256 rows). No validation/test rows used to train, select epochs or thresholds. Though within-split combinations are new, the 0..29 numeric universe has appeared in previous research; not globally unexposed numbers.

Three seeds 101/202/303; two arms; identical initial 5,160 parameters per arm/seed; six students, 600 Adam updates each = **3,600 total**; batch64, Adam LR0.006, fixed no-early-stop, gradient clip1, 230,400 supervised row presentations. Each example has 39×64 + 64×40 = **5,056 forward dense MAC**, training forward total **1,164,902,400 MAC** (backward, overhead, decoding, replay excluded).

Eight gates locked now; overall PASS only if all succeed:
1. Exact source/manifest SHA and legal corpus conditions;
2. Joint test valid `01` accepts ≥170/192;
3. Joint **unseen** malformed `10` rejects ≥150/192;
4. Joint test full-answer+STOP exact count ≥ math-only count minus 12/192;
5. Joint test STOP position accuracy ≥ math-only minus 12/192;
6. Joint rejects ≥90% of seen-type 00/11 on heldout test (≥346/384);
7. Identical initial weights, minibatch schedules and update counts across arms/seeds;
8. All 2,688 heldout predictions are independently replayed with NumPy from saved checkpoints (448 per arm/seed).

Keep every failure, seed, and illegal case. Do not add rounds, alter split, or choose checkpoint on validation/test. Retain negative results.

## Provenance and division of labor
U: user requested real native 01 neural teaching, math, STOP, generalization and growth, separated from VM/parser.
F: R62 PR #113 learned fixed framing; R63 PR #114 modular gate preserved math without improving it; separate P035 PR #10 and Pro UR1 PR #12 have executed their own studies.
A: shared frame supervision could help or interfere with math; not presumed to succeed.
T at Git freeze: deterministic 1,472-row generator and static SHA checks only; **zero R64 neural forward/optimizer steps**.
NVIDIA skipped (no authorized callable local OpenRouter endpoint in this runtime), actual calls 0; local Codex 0; Gemini 0.

Next owner: independent small NN researcher; publish actual code, raw-bit manifest, six checkpoints, all 2,688 answers, independent replay and negative result in new isolated directory. No automatic merge.