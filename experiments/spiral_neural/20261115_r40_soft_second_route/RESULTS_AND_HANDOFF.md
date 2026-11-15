# R40 — trainable non-b soft route, actual 3-seed result (2026-11-15)

**Status: new neural experiment executed; preregistered six-part joint gate FAIL (4/6).** The preregistration was committed **before R40 training** in `f7df79190d15f5ab353bc2af280e2de18880cc3f`. This result is subsequent, not a retroactive edit of frozen gate.

## Why this new factor

R38 `b`-only fixed second-answer-word route retained trained b values but failed generalization; R39 unrestricted second-word route impaired role-specific learning (e.g. high-b second word 48→17/48). R40 modifies **only that input route**: a single trainable `alpha=sigmoid(route_logit)` (initial logit -6 / alpha 0.002472623) scales access to a,c,d while generating the second numeric answer word; b unchanged. All other positions, training lessons, seeds, initial base weights, Adam and update budget match R38/R39. +1 trainable parameter: **10,458 vs 10,457**. It is not exact param/MAC matched.

## Legal raw-bit experimental contract

`SLE-AE1-n5-v1`, values 0..29, 39-bit question `01+010+bin3(r)+0+4*(bin5(value)+0)+111100`; answer r six-bit numeric words then separate external terminal classifier `S`. 136 ordered R38 training events, 1408 target positions/epoch, 150 epochs, seeds 101/202/303, 3300 Adam updates per seed at batch64/LR.003 and gradient clip1: **9900 updates; 633600 training-target presentations**. Forward dense base **6,918,912,000 MAC** with upper-bound extra **22,809,600 elementwise gate multiplications**, exclude backward. No teacher LLM answer inside student computation.

Split: 16 previously examined b26/27 high-role, 16 known b18/19, 16 displaced b20..23, 80 mixed-arity historical r1/r2, per seed (not blind); plus **16 genuinely new complete 39-bit questions** per seed: r2, a∈{14,15,20,21}, b∈{24,25}, (c,d)∈{(2,4),(3,6)}. This b role is absent from training, **not globally new numerical values**; prior test Q overlaps were checked against available R30–R39 manifests. No validation-guided model selection; final epoch150 only. Frozen raw code SHA256 `314ead28bdc43f00e144748410e79457bd436437c41b6104ba7ce763edebb411`, test manifest `cf9726b08f1f1592fa60327baea2e63bc7b925d11329fcf27e5ce03240ed6010`, prereg JSON `811dbac23dfbbdb1d87f7ecb9b3b5ea6fe32ead51fe3419b04ac15ca0a378445`.

## Measured results, three seeds pooled

| Result | R38 hard (familiar historical) | R39 unmasked (familiar historical) | R40 soft (new actual) |
|---|---:|---:|---:|
| High b26/27 second-word | 48/48 | 17/48 | **48/48** |
| Known b18/19 second-word | 48/48 | 11/48 | **48/48** |
| Displaced b20..23 second-word | 40/48 | 13/48 | **40/48** |
| Historical mixed-arity complete | 228/240 | 211/240 | **228/240** |
| High b26/27 autonomous complete | 1/48 | 1/48 | **1/48** |

**Brand-new to this run:** R38/R39/R40 checkpoint inference on the same unseen complete-Q b24/25 second-role contexts gave **0/48, 0/48, 0/48** second-word correct, all **0/48** full autonomous exact. Gold-supplied-prefix STOP on these: R38 **19/48**, R39 **48/48**, R40 **19/48**. Do not confuse correct-prefix STOP with actual answer generation.

Pre-registered six tests: high second >=40/48 PASS, known second >=44/48 PASS, displaced >=36/48 PASS, historical complete >=216/240 PASS, novel b24/25 second >=12/48 **FAIL**, high autonomous full >=6/48 **FAIL**. Overall **FAIL**; no threshold changes or retesting to improve outcome.

Learned alpha from initial 0.002472623 to seed101 **0.0015616369**, seed202 **0.0021659422**, seed303 **0.0016480983**. All moved further toward the b-only mask. This is descriptive, not causal proof of why novel-role transfer failed.

One observed negative example seed101: Q `010100100011100110000000100001000111100`, expected `011100110000S`, R38 predicted `010100100100S`, R39 `010100110100S`, R40 `010100100100S`. `S` is the local output-stop class, not an SLE wire bit.

## Actual T and reproducibility receipts

New students **3**, total Adam updates **9900**; additional full raw-01 autoregressive model generations **528**, inference forwards **9943**, base inference dense MAC **108,577,560**. Both checks: **PyTorch exact full replay 528/528 PASS** and separately implemented **NumPy full replay 528/528 PASS**, max gold-prefix logits absolute delta **2.86102294921875e-06**. Companion archive `sle_ae1_r40_soft_second_route_20261115.zip` has **171 files**, including all frozen R38/R39 source/weights needed, full R40 training runner/source, R40 prereg/manifest, all 528 raw generation rows, results, three new checkpoints, local reports and SHA256SUMS_R40; in clean independent extraction **170/170 file checksums + gate + both full replays PASS**.

**Companion ZIP SHA256: `07a63dbc11b8b424574bd4c9973cea4e8d0f390638c99a620ec13407f6a73f84`.** The ZIP is attached to the research conversation; **Git does not contain all weight/source bytes**, so Git alone cannot reproduce the NN forward results. The full runnable source is in companion ZIP. Commands from extracted ZIP root:
```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r40_soft_route.py gate
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r40_soft_route.py replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r40_soft_route.py numpy
```
Do not rerun `train` over existing output, and the runner itself refuses overwrite.

U: user's SLE raw-bit small-NN progress mandate and requirements. F: R38/R39 actual checkpoints; Codex P030–P035 and Pro UR1 branch #12; PR #5 synthetic math bank (no claim of math learning). T: this run's training, outputs, independent NumPy and clean ZIP replay; never attribute to other workers. A: the finite course appears to favor role specialization; mechanistic cause and broader learnable routing remain uncertain. **NVIDIA, local Codex, Gemini actual calls 0**; NVIDIA no authorized live reviewer endpoint here. Not merged, Pro/Codex work untouched.

[更新] Near-hard trainable routing retained b-role accuracy but still did not transfer to held-out b24/25; alpha moved toward hard routing. [取代] The hypothesis that merely softening this route would combine retention with generalization. [原因] b24/25 remained 0/48 and high autonomous exact 1/48 despite 4/6 gate subscores passing. [狀態] Actual reproducible scores high confidence; mechanistic interpretation low.

**Next owner:** independent SLE NN. The 16 b24/25 Q are now exposed and must never be called fresh blind again. Design a distinct legal new heldout role; change one factor (new-role coverage vs gate initialization, NOT both), and evaluate complete autonomous outputs as well as role-specific bit accuracy. No new Pro UR1 manifest authorization inferred; no automatic merge. 
