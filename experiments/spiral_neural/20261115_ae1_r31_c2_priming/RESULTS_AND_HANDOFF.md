# R31 actual native-01 SLE neural training: frozen-gate FAIL

Date: 2026-11-15. Owner: independent small-NN researcher. Parent: Draft PR #80 R30 (`research/sle-ae1-r30-no-firstword-mask-20261115`). Do not merge automatically or edit Pro/Codex branches. **Pretraining Git freeze was committed first:** `ba79e74da9d299a689272af2b1bdaaf88c135f60`; see [FROZEN_BEFORE_TRAIN.md](FROZEN_BEFORE_TRAIN.md). Original R30 trained weights/checkpoints used as read-only control; new R31 models *actually trained*, not scripted agents.

## Single input-curriculum intervention

Only 16/24 high-a (a=20..27), r=1 training examples change **irrelevant third data word** `c=0→c=2` (one native input bit). Every high-a value has 2 c2 and 1 c0 presentations. All targets, a/b/d/r, 150 epochs, seed initial states, 136 course appearances, batch schedule, architecture, Adam, firstword **unmasked**, r2 secondword routing, STOP unchanged. Distinct course tuples 118→122 (the changed distribution is the intervention). Legal `SLE-AE1-n5-v1`, 39-bit raw01 Q, data IDs 0..29, first 6-bit answer, optional r2 6-bit second answer, external STOP `S`.

3 seeds (101,202,303), 10,457 parameters/model, 3,300 Adam steps/student (9,900 total), 633,600 teacher-forced target presentations, 6,918,912,000 theoretical **training forward** dense MAC (backprop/overhead excluded). Teacher codec supplies training labels/offline scoring, NEVER student inference.

Pre-frozen 224 distinct full Q: 168 original R30 train/val/test panel reused and 56 new paired c0/c2 cases (8 paired_val, 16 paired_unseen a28/29, 32 paired_near a20..23). a28/29 were student held-out, **NOT researcher-blind** because earlier workers already viewed them. Train contains no a28/29.

## Original joint gate FAIL (unchanged)

| Fixed panel across 3 seeds | R30 frozen control | R31 actual trained |
|---|---:|---:|
| a28/29 firstword correct | 20/72 | **23/72** |
| a28/29 entire answer correct | 12/72 | **14/72** |
| near a20..23 firstword correct | 32/96 | **38/96** |
| STOP correct location | 60/72 | **69/72** |
| original exact full-answer retention | 240/240 | **240/240** |
| new paired unseen a28/29 firstword | 19/48 | **20/48** |
| new paired unseen entire answer | 10/48 | **20/48** |
| new paired near entire answer | 39/96 | **57/96** |

Predeclared gate requires **ALL**: a28/29 firstword >=+8/72 (observed +3), complete >=+6/72 (observed +2), near loss <=8/96, retention loss <=12/240, STOP loss <=6/72, no seed unseen-firstword reduction >8/24. So formally **FAIL**, regardless of secondary gains. Per-seed known a28/29 firstword: 0→1/24, 16→16/24, 4→6/24. Near firstword seed202 REGRESSED 18→15/32.

Particularly instructive negative case: in the new paired panel, c0 firstword improves 9→12/24, but the c2 firstword **degrades 10→8/24**, though c2 was newly exposed in teaching. Paired exact rises 10→20/48 mainly with STOP positions improving 29→48/48. Hence **STOP improvement is not proof of high-word generalization**.

Concrete failure (seed101, heldout): Q `010100010111000100000000000001000111100` expected `111000S`, R31 `111100S`. The same incorrect firstword occurs with c0,d0 Q `010100010111000100000000000000000111100`. Record these failures, do not cherry-pick seed303.

## Executed evidence and portable companion

**Companion archive** `sle_ae1_r31_c2_priming_20261115.zip`, SHA256 `961bad8563c23363c71812aab1c22b961c7f1f022b1896d3f107c3f19059776f`; delivered as a ChatGPT conversation artifact, **not uploaded to Git**. Includes R30 original controls, 3 R31 actual checkpoint weights, frozen source and 224-case raw01 manifest, prereg, 1,344 saved output rows, logits, 78-file SHA inventory, training logs, NumPy independent implementation, detailed U/F/T/A report.

Actual R31 training: 9,900 Adam updates. New true PyTorch free-generations **840** (3 new models×224 cases = 672, plus frozen baseline×56 novel cases×3 =168). Reused 504 original R30 records without new baseline Torch inference, resulting combined 1,344 rows. Executed 10,875 forward calls for newly generated rows (118,755,000 theoretical inference dense MAC). NumPy independent implementation really **recomputed all 1,344 rows** from checkpoints, including the 504 previously cached ones; all exact answers match, largest logits difference `3.337860107421875e-06`.

**Fresh clean extraction tests actually run**:

```bash
unzip -q sle_ae1_r31_c2_priming_20261115.zip -d <new-directory>
cd <new-directory>
sha256sum -c SHA256SUMS_R31                  # PASS 78/78
python r31_runner.py replay                 # PASS 1344/1344, STATIC source/course gate
python r31_numpy_audit.py                   # PASS 1344/1344 independent NN
```

Frozen runner hash `d83a828df067e17d931477842b79bb51a303b61c2a39e7cecaf84b377ed7982b`, 224-case manifest `8dc4c608930d693aeaae29c2b5109cbc91cfc6ca3df50442861a9c308474f630`, prereg JSON `f85442ce2f2bff364e9a340485b9364184bfeeb9a4bdd419ab7025590c96d06f`, course `7926392fc6bc0147763fc5c5fd35e776449540a96cbb9ff59b49f618f730f8e4`. Exact frozen hashes in Git prereg before any new NN training. Full weights **only in companion**; Git alone cannot scientifically replay R31 without it.

U: user independent neural education/generalization request. F: PR #80 original R30 checkpoints/code/manifest and Pro/Codex historical records. T: this run's actual R31 training/forward, independent NumPy audit, clean archive tests. A: irrelevant c diversity might improve high-a invariance; **not established**. NVIDIA unavailable/not authorized (0 actual calls), local Codex 0, Gemini 0. No sensitive/private content or API keys.

**Next owner: independent small-NN worker.** Design new truly held-out firstword values and equal-budget flat-binary control, with per-seed firstword+STOP+retention gate. Do not repeat P030–P035, UR1 or R30; no auto-merge.
