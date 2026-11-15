# R45 results and handoff — balanced lessons, unmasked second word (2026-11-15)

**Status: FROZEN 7/7 preregistration gates FAIL.** Independent native raw-01 SLE small NN worker. Research source: PR #95 R44 head `456c0127b62f32bcb896596be529e6c79fb803f9`. Prior to running any R45 student, this branch froze `PRETRAIN_FREEZE.md` in commit `82a66f6f677e4888c59e27ce40a4b993b10b4fd1`, then fetched and verified it. No post-hoc science/threshold/seed changes.

## Intervention and exact costs

Single change: train the same 10,457-parameter `WordStudent(True)` with **all four source fields a,b,c,d available at second-answer-word cursor**, replacing R44's engineered **b-only secondword input mask**. Fixed R44 balanced 136 ordered lessons, three seeds 101/202/303, same initialization tensors, Adam lr .003, clip1, batch64, 150 epochs; 1,408 target-prefix presentations/epoch; 3,300 Adam updates/student; **9,900 actual new updates** / 633,600 targets / **6,918,912,000 theoretical forward dense MAC** (excludes backward, inference and runtime overhead). Baseline R44 checkpoint scores reused, not retrained.

Legal `SLE-AE1-n5-v1`: 39 native 0/1 question bits `01+010+bin3(r)+0+4*(bin5(v)+0)+111100`, legal number values 0–29, generated r six-bit answer words + external STOP action `S` (not a wire bit or SLE punctuation token). Teacher label computation offline only; student generation no oracle or LLM. Frozen R44 question panel: 96 test Q and 80 mixed-r1/r2 retention Q, each ×3 seeds. These test Q and values were **previously examined** in R44, therefore this is a *paired diagnostic*, not fresh historical blind generalization.

## Preregistered outcomes

| Metric, all 3 seeds | R44 b-only | R45 unmasked | R45 pass gate |
|---|---:|---:|---:|
| b24/25 second word | 48/48 | **0/48** | ≥40 |
| b26/27 second word | 48/48 | **2/48** | ≥40 |
| b18/19 second word | 48/48 | **0/48** | ≥40 |
| b28/29 (not trained in this b-role) | 48/48 | **1/48** | ≥40 |
| b20–23 second word | 80/96 | **0/96** | ≥72 |
| 80Q × 3 historical full answer+STOP | 228/240 | **209/240** | ≥216 |
| 96Q × 3 full answer+STOP | 0/288 | **0/288** | ≥1 |

Correct-prefix STOP at new test 96Q×3: **R44 10/288, R45 288/288**. R45 also voluntarily emits STOP on 288/288 new free generations while complete answers remain zero. STOP success **does not imply answer-content mastery**. R45 firstword correct 0/288; 90/288 R45 new free outputs equal `000000000000S`. One failure: seed101 Q `010100100001100110000011000011100111100` (b24), expected `001100110000S`, got `000000000000S`.

**Separate clearly posthoc diagnostic, NOT additional preregistered gate:** provide the *gold correct six-bit firstword prefix*, then free-generate secondword+STOP on 96Q×3 under unchanged weights. R45 still scores (b24/25) 0/48, (b20–23) 0/96, (b18/19) 0/48, (b26/27) 2/48, (b28/29) 1/48. Hence failure is not explained solely by its incorrect *generated* firstword prefix. The diagnostic provides part of the answer; cannot be called autonomous generalization.

## Actual execution / verification

Actual run commands in companion clean extraction (CPU, PyTorch+NumPy):
```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python r45_unmasked_balanced.py static
# immutable prereg commit above created and fetched BEFORE:
python r45_unmasked_balanced.py train
python r45_unmasked_balanced.py replay
python r45_unmasked_balanced.py numpy
python r45_posthoc_prefix_diagnostic.py
sha256sum -c R45_SHA256SUMS
```
3 fresh weights SHA256:
seed101 `0ff0fd17bd8589ef7b4cae0b4164b96c8735ee192a16bb85bff1d265e7621da8`;
seed202 `260f90901fe514ee21d86333e13cba7974223ffdfcc4261f6acb41c187b19200`;
seed303 `c8e594eab20d21d7712ca0f90d008b8419ea72e4cd15f4595844424769628e38`.
New results include **528 complete native-01 generations** / 6,354 forward ops / 69,385,680 inference forward dense MAC. **PyTorch replay 528/528 PASS**, **independent NumPy replay 528/528 PASS**, maximal STOP logit difference `2.86102294921875e-06`. Extra diagnostic 576 conditioned emissions / 10,376 forwards, separate from free outputs. Full `r45_outputs/raw_results.jsonl` SHA256 `21cda675240066c1436fe1edd73b00e687aa2418810eed03f0e0ab2f880667db`; full machine summary `475e6b0e35353f467a0ee3ad743122ff1425ddc01791a090caddc8a0254bba14`.

**Companion `sle_ae1_r45_balanced_unmask_20261115.zip`, SHA256 `7dfe1c5683fe117ae46e4c8e4569f5b62285eeda2fb2265c0f6f99da5a73eeea`, 224 ZIP entries (223 individually hashed content files plus the checksum manifest).** Independently extracted it into a new directory and checked **223/223 SHA256**, static PASS, PyTorch replay 528/528 PASS and independent NumPy 528/528 PASS. It includes historical R44 actual weights, all R45 three new checkpoint weights, immutable code, prereg, exact manifest, raw 01, error examples, NumPy alternative and independent replay. The ZIP is a **conversation companion artifact, not committed to this Git branch**; this Git report and checker alone are not sufficient to replay weights.

## Interpretation, provenance and next owner

[更新] R44's b28/29 secondword local success is strongly dependent on an explicit engineered b-only route, not a demonstrated general unrestricted copy skill. [取代] "Balanced four-word lessons alone are sufficient to retain R44 gains with unmasked input." [原因] R45 changed only that input route with matched costs, lost even learned word-role values, and posthoc gold-firstword conditioning did not rescue. [狀態] This trial and independent replay: high confidence; internal mechanism and other architectures: medium/low confidence.

U: user's independent native01 / education / generalization study and provenance requirement. F: AGENTS, Git handoff, historical Codex P031–P035, Pro UR1 #12, R38/39 and R44 prereg/checkpoints from #95. T: new true three-seed R45 training, failures, 528 generated raw 01, independent replays, posthoc fixed-weight diagnostic. A: hard b-only masking lowers nuisance-feature competition, but exact learned representations not established. **No SLE-vs-binary superiority conclusion.**

Next owner: independent small NN. Investigate **learnable conditional source selection** with genuinely new legal untouched blind role/context and separate complete-answer / STOP gates. Avoid repeating failed near-closed-alpha R40 as if a new test; do not silently rewrite native SLE grammar. Three-round entire-answer/punctuation curriculum is assigned separately to Codex through PR #90. NVIDIA 0 actual calls (no authorized accessible credential/endpoint); Codex 0; Gemini 0. No edits to Pro UR1, VM, grammar, other worker branches, and **no merge**. Public technical evidence only; no private messages or keys.
