# SLE-AE1 R32 — unseen low/high firstword one-bit comparison
Date: 2026-11-15 (Asia/Taipei). Owner: independent scheduled 01 small-neural-network research; this is **not** Hamster VM, syntax/parser or Pro UR1 work. **Formal preregistered gate: FAIL.** This report is a public evidence index; full PyTorch source, six checkpoints, all generated 01 bits/logits and independent NumPy reconstruction are in the *conversation companion ZIP*, not committed to Git.

## Verified frozen-before-inference provenance

Parent R31 PR [#81](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/81), head at start `0fdbf0c79b4a91d2d492426c3854d3d188b07773`, itself based on R30 [#80](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/80). PRs [#5](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/5) (P031 shared bank), [#9](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/9) (P034), [#10](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/10) (P035) and [#12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12) (Pro UR1 actual neural failure) inspected; did not rerun completed work or mistake semantic corpus checks for student learning. Read main AGENTS.md and Git handoff, plus Pro branch CURRENT_RESEARCH_STATUS.md and RESEARCH_HANDOFF.md.

**Published to own Git branch BEFORE R32 first neural forward:** fixed profile and four-part success gate in `FROZEN_BEFORE_INFERENCE.md`, commit `03aa9be14631f40114524625f4370178e96d5691`; 48 legal Q manifest committed and JSON ASCII-key-order discrepancy corrected **before any forward** at commit `0b427ac8624de09507b83cea0086e125338adf16`. The correction changed serialization only, not Q, cases, split or gate.

Companion whole ZIP: `sle_ae1_r32_msb_pair_20261115.zip`; **SHA256 `ec33f5e4d88dce73f98773a3bc19263cc343025754e35180d2c99363f200c802`** (97 SHA256-inventoried files + inventory).
Original source ZIP SHA256 `961bad8563c23363c71812aab1c22b961c7f1f022b1896d3f107c3f19059776f`. Frozen runner `7a9169a6ddf34a4a9c87d1d331c343e23626873741994636620de3365bd99d82`. Frozen prereg `6912998cce56f8a875eb24b02b49250191613da514e85ed3d5d9b56d6b3c3989`. Raw 48-Q manifest `bfdc7e5d52a03940c43fb8d75decc8c0dbfd4d9aded8f680984c06a033e9cac9`. Raw generations `cfc1b2167a503f9f0c88f5ffaa6969705bee4ff4acfb8d15638f6115316ee754`.

## Exactly one intervention, fixed checkpoint controls

Legal SLE-AE1-n5-v1, 39-bit input, exactly native 0/1; r1 answer six data bits + **external** STOP `S`. In each pair **only input bit index 9** (0-based) flips: `a12→28` or `a13→29`. All other b,c,d/r and six frozen NN checkpoints stay identical. Original R30/R31 136 teaching events, 1408 teacher targets, 3300 Adam updates per seed and 10,457 model params; R31 changed only c2 nuisance lessons. Current R32 **fresh training updates 0**. Neither low a12/13 nor high a28/29 occurs in any role of the training inputs, but a28/29 previously appeared in historical tests; this is new input combinations, **not four globally unseen values**.

Calibration: 8 paired contexts (16 Q), b16/17 c0/2 d0. Predeclared formal test: 16 contexts (32 Q), b16/17/20/21 c0/2 d1. Six immutable models ×48 Q = **288 true full neural free generations**, plus first output bit/true-answer-prefix STOP probes; **3492 actual PyTorch forwards, 38,132,640 theoretical inference dense MAC**, 0 newly trained models. Not 48 independent word-value trials: only two numeric a-pair identities across contexts/seeds.

## Test outcome (three seeds pooled)

| Metric (TEST) | R30 unmasked | R31 c2 lesson |
| --- | ---: | ---: |
| Low a12/13 firstword correct | **3/48** | **1/48** |
| High a28/29 firstword correct | **18/48** | **13/48** |
| Low first output bit correct | 11/48 | 1/48 |
| High first output bit correct | 48/48 | 48/48 |
| Both sides of a pair full firstword correct | 3/48 | 1/48 |
| Both sides of pair flip first output bit correctly | 11/48 | 1/48 |
| True-prefix STOP correct low/high | 41/48, 33/48 | 48/48, 47/48 |
| Autonomous exact full answer low/high | 2/48, 9/48 | 1/48, 13/48 |

**Four-part prereg gate:** R31−R30 low firstword improvement >=+6 (actual **−2 FAIL**); high firstword regression >=−4 (actual **−5 FAIL**); R31 both sides firstword correct >=12/48 (actual **1/48 FAIL**); individual low-side losses no worse than −4/16 (seed deltas **+1/−3/0 PASS**). Hence **overall FAIL**. No posthoc modified gate.

R31 mean first-output-bit margin change on high-vs-low pair **+6.39**, yet only **1/48** paired contexts produce the correct 0→1 decisions. The network numerically reacts to high input bit, but usually predicts 1 even on low-side where correct bit=0. Merely moving logit is not learning the bit-copy rule. Improving STOP correct-prefix probes can coincide with losing copy discrimination. These STOP scores use a **teacher-forced correct answer prefix only for measurement**; they are not autonomous exact-success counts.

Concrete seed202 Q pair with b16,c0,d1:
```
low  Q 010100010011000100000000000000010111100  truth 011000S
high Q 010100010111000100000000000000010111100  truth 111000S
R30 actual: low 111000S; high 111100S
R31 actual: low 111000S; high 111100S
```
All failures, bitstrings and raw logits in companion `r32_outputs/raw_results.jsonl`.

## Actual independent verification, U/F/T/A and next handoff

Actual PyTorch complete output replay **288/288 PASS**; separate independent NumPy checkpoint reconstruction **288/288 PASS**, maximum firstbit/STOP logit difference `2.86102294921875e-6`; in clean extracted directory companion `python verify_package.py` checked **97/97 SHA256** file inventory and re-ran both identical 288-output paths. The portable verifier changes only the archived source ZIP **path** to local identical original bytes; the fixed runner source SHA stays unchanged. No teacher/LLM oracle generates student outputs. Local Codex 0, NVIDIA 0 (no authorized callable runtime reviewer), Gemini 0. No other agent branch writes, no auto merge.

U: user's native01 small-NN education, generalization and growth research direction. F: original R30/R31 checkpoints, code, P030–P035 and UR1 evidence with source SHAs. T: R32 fresh PyTorch and NumPy inferences, tests, negative examples and bytes verification. A (unproven): nuisance-word curriculum may trade first-bit discrimination for STOP stability; internal causal weights still unknown.

**Next owner:** independent NN researcher. Do not rerun R30/R31 or re-label this tested pair as blind. A strong next preregistered question is equal-update/MAC ordinary binary input+output benchmark with genuinely reserved values, joint gate on firstword, STOP, full-answer and retention. Do not claim a unique SLE advantage from the present failure. Git branch remains draft, companion full binary weights are not in Git.
