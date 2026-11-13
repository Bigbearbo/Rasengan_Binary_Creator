# AE1: Fourth-word d bit invariance — real frozen-NN result (2026-11-13)

**Pre-registered primary gate PASS.** No training, no VM/parser/UR1 modification, no LLM answer oracle.

The pre-inference freeze was published at Git commit `affa395bf64071ac899872f339f804668b2c1368` before any new NN forward; original four checkpoints are from parent PR #46 head `1598246cde44d9b29a0fdf6645e27ff023dde4b0`. Full original experiment archive (including genuine checkpoints, code, all outputs) SHA256 `de9faa95e2ba8d178b0a52712a6aa0259894a04147d4894eab407b270ef48e4d`. Keep those bytes: the verifier in this Git directory validates the full archive.

## Single factor and fixed split
Only semantically irrelevant fourth operand `d` varies: 0 baseline vs 1,2,4,8,16, five independent one-bit toggles. The SLE-AE1-n5-v1 input is 39 bits: `01+010+010+0+4*(5-bit-data+0)+111100`, with 0..29 ordinary values and 30/31 reserved. Expected response is first two whole 6-bit words plus freely generated `S`; no answer-length forcing.

Two frozen seeds 101/202 × two prior model arms (PR44 c1-only, PR45 balanced-c) × validation a4 / test a5 × b26/27 × c2/3 × 6 d variants: **192 full 01 responses, 48 unique Q, 32 baselines and 160 new d-only interventions**. c2/c3 are a priori fixed blocks, *not* an additional changed experimental variable. Historic training exists; **new updates 0**, new target exposures 0. a/b/c already researcher-inspected, so do **not** claim a fully researcher-blind heldout.

A priori gate: separately for both balanced-c seeds, all four d0 cases correct in each c2/c3 block and every one of the 20 d>0 variations per block correct **and identical to d0**. Frozen c1 controls are diagnostic, not selection targets.

## Actual observations

| student | c2: d0 → d>0 exact | c3: d0 → d>0 exact | d flips changing output |
|---|---:|---:|---:|
| old c1-only, seed101 | 0/4 → 0/20 | 4/4 → 20/20 | 0/40 |
| old c1-only, seed202 | 0/4 → 0/20 | 4/4 → 20/20 | 0/40 |
| mixed-c, seed101 | 4/4 → 20/20 | 4/4 → 20/20 | 0/40 |
| mixed-c, seed202 | 4/4 → 20/20 | 4/4 → 20/20 | 0/40 |

**Key negative observation:** the old controls preserve their *wrong* c2 answer across every d mutation. Thus unchanged output is not sufficient evidence of learned semantic invariance. In this narrow fixed domain, the dramatic earlier c low-bit parity effect does **not** transfer to the separate d word; neither old nor mixed-c checkpoints are sensitive to any of the five d information-bit toggles here. This does not establish general copying, general suffix ignoring, or a neural mechanism. Overall 144/192 answers exactly correct; all 192 use the proper STOP location.

## Exact execution and verification
- Preflight before Git freeze and before neural forward: four source-checkpoint SHA and weight-tensor digests checked, 192-case uniqueness and 39-bit legality checked, each d0→d bit-change exactly one Q bit, target invariant. **PASS**; 0 NN forward then.
- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python probe_d.py run`: actual **192 PyTorch free-generated outputs**, **2,496 forward calls**, **26,038,272 dense forward MAC** (10,432/step), 0 optimizer updates.
- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_d_numpy.py`: independent no-Torch/no-original-runner F32 eval **192/192 full 01+S replies and 2,496/2,496 forward decisions match**, prereg gate verified.
- `python verify_public_zip.py /path/to/sle_ae1_d_intervention_20261113.zip` works with the **unchanged** companion ZIP and independently replays all 192 outputs from four genuine JSON checkpoints: tested locally, PASS. SHA of this exact Git verifier blob `180206674a49ca374790b0de187b7c858b929cad`.
- Full runner `probe_d.py` and prereg JSON in immutable ZIP: published prereg hashes `dfe595b4758bc9b9dfb3ebbfdff94bfe1bf78761ba81e8e97f739459b8d6f766` and `ae29738dc5d69f8625c1c41754eb04079c86527ef03fbba01552448cd1046343`. Individual bundle file digests in `SHA256SUMS`.

[更新] The observed irrelevant-input c parity dependence is not a universal fourth-word bit sensitivity. [取代] Hypothesis that any irrelevant data word's changed bit will similarly perturb generation. [原因] All 160 d-bit interventions leave generated replies unchanged even when c2 anchors are wrong. [狀態] High confidence for this four-checkpoint test domain; low confidence on why the NN does it or generalization elsewhere.

U: user's small true 01 NN study request. F: immutable PR40/44/45/46 checkpoint archive and separate Pro UR1, P030–P035, Codex E3. T: this run's genuine PyTorch and independent NumPy forward tests. A: word-slot-specific spurious c binding is a plausible mechanism, unproven. NVIDIA actual calls 0 (no authorized configured runtime worker); Codex local calls 0; Gemini 0. No secrets or private conversations.

**Next owner:** independent NN investigator. Prefer pre-frozen new a/b partner splits and uninspected combinations, optionally a matched-cost d-variation curriculum; avoid tuning this inspected c2/c3 region or conflating invariance with correctness. Draft only; no automatic merge.
