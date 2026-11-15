# R41: High/low bit-contrast pairs within minibatches — executed FAIL (2026-11-15)

**Scientific status: preregistered combined gate FAIL (4/5 individually passed).** This is an independent native-01 small-NN study, not Hamster VM, parser vocabulary, P030–P035 re-run or Pro UR1 experiment.

## Frozen single intervention

The R38 hard-b secondword route is kept: 10,457 parameters, the original 136-event teaching course, 1,408 target-prefix pairs per epoch, 150 epochs per seed, seeds 101/202/303, optimizer Adam lr0.003, batch 64, initialization seed+12000, 3,300 updates per student. Only rearrange the order of targets into minibatches: match b18→26 and b19→27 (each pair changes one numeric input bit), with identical a/c/d and each of the six secondword output positions, making 24 low/high target pairs per epoch appear in the same batch. The per-epoch target multiset and update count are untouched, and R38 checkpoints remain frozen. All 10,800 pair-epoch opportunities are same-batch under R41, compared with 509/10,800 under original R38 shuffling; 20,480 target positions across all three seeds differ. This changed the optimization trajectory, not the curriculum contents.

Legal input profile **SLE-AE1-n5-v1**: values 0..29, 39 binary raw bits: `01+010+bin3(r)+0+4*(bin5(v)+0)+111100`. Free outputs contain r six-bit words and externally defined STOP classification `S`; `S` is not a literal SLE wire bit. No model/LLM oracle supplies the student's output, only the deterministic program generates labels.

**Split:** train unchanged historical 136 events; validation/retention is formerly viewed R38/R40 data (b18/19, b26/27, removed b20..23 and 80 mixed-arity legacy questions); new test contains 32 novel raw 39-bit question strings for a14/15/20/21 × b24/25/26/27 × c/d=(4,7)/(5,8), 16 each of untrained-in-b-role b24/25 and taught b26/27, evaluated on all three seeds. b24/25 were already probed in R40, so they are **not globally unexposed numeric values**. Historical manifests were checked for exact raw-question repetitions; no global blindness claim.

**Before training**, source, test and joint thresholds were committed to `7416d80c034df70c55d111e39c8f129f3e59542e`, in `PREFREEZE.md`. Actual frozen SHA256: script `a3d8ea4d907aa008ab6cfab91e56f5a05ee16b40cfdd3e0d419104ed3fae49d8`; prereg JSON `fce44082023d484f6390015abc5a0c93e8d319a3b494950837de2bd3c913d7da`; raw-question manifest `1308efe5c747ae823af18be240d258d362c4a7751e2c98ff6177f96fa58cde16`. Frozen pre-train static gate passed.

## Final real-model results

| Three-seed measure | R38 prior checkpoint | R41 trained | Preregistered condition |
|---|---:|---:|---|
| New-context b24/25 secondword | 0/48 | **0/48** | >=12/48 **FAIL** |
| Prior taught high b26/27 secondword | 48/48 | 48/48 | >=40/48 PASS |
| Prior known b18/19 secondword | 48/48 | 48/48 | >=44/48 PASS |
| Historical r1/r2 mixed complete answers | 228/240 | 228/240 | >=216/240 PASS |
| New-context taught b26/27 secondword | 48/48 | 48/48 | >=24/48 PASS |
| New-context b24/25 *complete* answer | 0/48 | 0/48 | Diagnostic only |
| New-context b26/27 *complete* answer | 1/48 | 2/48 | Diagnostic only |
| Prior high-b firstword | 2/48 | 0/48 | Diagnostic only |

Nine of 48 new b24/25 autonomous outputs changed from R38; none became correct. Taught high b26/27 new-context outputs changed 8/48. Weight distance vs frozen R38 final checkpoints about 4.418 / 2.342 / 2.469 (seeds 101/202/303); training was a real, different optimization path, despite failure.

**Resources:** actually trained three new students, 9,900 Adam updates, 633,600 target presentations; estimated training forward dense MAC 6,918,912,000 (excludes backward). Actually generated 576 new complete native-01 outputs (480 R41 + 96 R38 on the new contexts); the old R38 384 stored outputs were only reused, not counted as new inferences. Actual 11,907 inference forwards, estimated 130,024,440 inference MAC. Student parameters 10,457 each.

**Validation:** complete saved-checkpoint PyTorch replay 576/576 exact, independently implemented NumPy network inference replay 576/576 exact, maximum logit difference `1.9073486328125e-06`. Companion ZIP was freshly extracted and 181/181 inventory SHA256 checks passed, then static gate, PyTorch and independent NumPy replay all passed from that clean extraction.

**Saved model checkpoint SHA256:**
- seed101: `2481ca757253e2009a285cda9c9b0231e29643a158a523f0a19cc224e5c7ac1a`
- seed202: `2f2c05be1f34ebaed1891a9286442c4caeee2ebafc5533cc469ef54ea91dfa12`
- seed303: `7abf803e6ee1b523e593fb8afb012bc6490896ee5ecc2fe302dd14f6b6fcfcf5`

One failure: Q `010100100011110110100000010001010111100`, gold `011110110100S`, R38 `11011011010011111111111111111111`, R41 `11111011010011111111111111111111`. The secondword remains correct but firstword and STOP fail.

## Artifact, reproducibility and handoff

Conversation companion **`sle_ae1_r41_contrast_batch_20261115.zip`**, SHA256 **`f5ef137f0fbc424b01891d2c25d6eb4637d14abb9c8f812a245b9e05eebbc522`**, 2,409,007 bytes, 182 entries. Contains full runnable source, R31–R40 dependency files, all required checkpoints, pre-registration, 32 raw-question manifest, 576 new raw neural outputs, failures, SHA inventory and expanded report. The ZIP is a **conversation attachment, not committed to Git**; Git-only checkout does NOT independently reproduce neural inference. From a clean unzip directory run:
```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python r41_paired_batch.py gate
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python r41_paired_batch.py replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python r41_paired_batch.py numpy
```
All passed in the current execution environment, not merely historical claims. No auto-merge or edits to Codex/Pro/VM branches.

Source roles: **U** the user's SLE raw-01 NN and matched scientific-comparison direction; **F** historical P030–P035, Pro #12 and R38/R40 actual archived sources/checkpoints; **T** this round's three actual R41 trainings, 576 new generations, static/cryptographic checks, PyTorch and NumPy verification; **A** grouping one-bit contrasts in the same minibatch might enable general copying (not supported by this trial).

NVIDIA reviewer **0 actual calls**, because no authorized local OpenRouter NVIDIA endpoint/key is callable in this environment. Local Codex **0**, Gemini **0**. Did not infer new approval for Pro UR1 manifests.

**Next owner:** independent NN researcher; prefer an explicitly approved globally new profile/task domain and compute-matched plain-binary control, or a genuinely distinct single-factor bit-copy intervention. Never relabel b24/25 as new blind values.

[更新] For this exact course and hard-b architecture, extreme single-bit contrast colocation changes training paths but leaves b24/25 transfer at 0/48. [取代] Simply batching matched one-bit teacher examples may induce compositional copying. [原因] Same-batch pairing 509/10800→10800/10800 did not meet the preregistered transfer condition. [狀態] Three-seed execution and independent replays: high confidence; extrapolation to other networks/profiles: low.
