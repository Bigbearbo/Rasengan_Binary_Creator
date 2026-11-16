# R64 — Joint raw-01 framing and elementary full-answer network: actual results

Date: 2026-11-16 (Taipei). Independent neural worker. **Prerecorded before any R64 NN training** on this branch: [FREEZE.md](FREEZE.md), Git commit `6a8fd14c3252c36b7b3aa20260a2a6d4f1647e92`; runner SHA256 `a8c4ffe2e0cb79f7575f84cf2b4e34f4d3a3ff4e2e54f8076f36b062540dc550`; 1,472-row manifest SHA256 `2201dc52d2c9b28bbf05439e85fb8b5405a963e4dc10c70468c748eef0f14ea2`. Parent R63 PR #114 head `38c77853720a916c0a1dd02f5ae8a5fa09d495f0`.

**Eight predeclared diagnostic gates: 8/8 PASS**. This is success under the fixed SLE-AE1-n5-v1 Echo task and its heldout data, **not proof of general SLE grammar or arithmetic mastery**.

## Paired experiment
Single intervention: framing BCE loss coefficient 0 versus 1. Both arms have same 5,160-parameter 39-bit ±1 -> tanh64 shared network, identical 13×3 non-autoregressive native-bit/host-STOP answer slots, identical frame logit, same initialization, 64-sample minibatches, optimizer, and exact teaching examples. The frame head exists in both arms, but remains unsupervised for lambda=0. Legal native 39-bit `01 + 010 + bin3(r) + 0 + 4×(bin5(v)+0) + 111100`; r1 copies a; r2 copies a,b, then emits separate external STOP class `S` (not an SLE wire token). Invalid start 00/11 are training negatives; 10 **never** trained. No numeric decoder or teacher LLM performs student computation.

Data: 256 independent base Q with operands 0..23 train, 48 with 24..26 validation, 64 with 27..29 test; four frame variants per base. Raw rows: 1,024 train (valid root duplicated to balance labels), 192 validation, 256 test. Historical 0..29 numerical universe was exposed in earlier studies; only within-this-run splits are disjoint.

Seeds 101/202/303, 600 Adam steps/student, six trained students (three per condition), **3,600 optimizer updates** and **230,400 training-row presentations**. Each training row ≈5,056 forward-only dense MAC, totaling **1,164,902,400 forward-only dense MAC**; excludes backward/evaluation/replay. All six NPZ checkpoints preserved.

| Heldout test, aggregate 3 seeds | Math only λ=0 | Joint λ=1 |
| --- | ---: | ---: |
| Legal 01 accept | 104/192 | **192/192** |
| Trained illegal 00/11 reject | 183/384 | **384/384** |
| Never-taught illegal 10 reject | 95/192 | **192/192** |
| Whole math answer exact **including STOP** | 149/192 | **165/192** |
| Correct STOP position | 192/192 | 192/192 |
| r1 whole answer | 79/96 | 82/96 |
| r2 whole answer | 70/96 | 83/96 |

Validation whole answer: **108/144 → 126/144**; joint frame accept **144/144**, malformed reject **432/432**. All three seeds retained correct math on all 256 train-origin legal base cases per arm, **1,536/1,536** paired source-near outputs. Test per seed: 101 **63→64/64**, 202 **58→63/64**, 303 **28→38/64**. Against lambda0, 27 paired test cases were rescued, 11 regressed; don't suppress negative cases.

Rescue: Seed101 r2 a29,b28,c29,d29, raw `010100100111010111000111010111010111100`, truth `111010111000S`; baseline `011010111000S`; joint correct.
Regression: Seed303 r1 a27,b28,c28,d29, truth `110110S`; baseline correct; joint `010110S` incorrect.

## Commands, audit, artifact and limitations

Executed **after frozen Git spec and readback**:
```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python r64_joint_frame_math.py train
OPENBLAS_NUM_THREADS=1 python verify_r64_public.py .
python r64_joint_frame_math.py verify
```

Actual six NN trainings PASS; 2,688 heldout model predictions preserved. Independent NumPy verifier redecodes **all 1,472 raw 39-bit questions** from scratch and reproduces all **2,688/2,688** output/logit predictions (max frame-score error **3.814697265625e-06**); no additional optimizer updates. ZIP/CRC and contents hashes reverified.

Full reproducibility bundle (runner, full 1,472 bit manifest, six NPZ checkpoint files, 2,688 raw predictions, independent verifier, all 74 paired val/test changes, failures, logs and SHA manifest) is conversation artifact `sle_ae1_r64_joint_frame_math_20261116.zip` SHA256 **`0f5e5a7361fd92d894c485e419236d25f17573cbf5eabc6eb59e6ad9e001a0b7`**. **Not claimed to be Git-uploaded**: only prereg / report are on this branch. The Git prereg froze the *hashes*, not full runner and manifest bytes. Do not regard a Git-only checkout as completely replayable without the ZIP.

Scope: this is a new shared-trunk, fixed-width **parallel-slot** Echo student, not the R52 autoregressive math NN, not Codex three-round 321-d whole-region design, and not a variable-width or arithmetic addition student. Fixed 01 can be checked more cheaply by two deterministic comparisons. Improvement may reflect auxiliary-loss regularization rather than semantic parsing; other profiles not demonstrated. No test-set fitting, rerun, extra seeds or post-gate training.

Provenance: U=user asks true native 01 neural/math curriculum independent of VM; F=R62/R63, P035 Codex, Pro UR1 existing sources; T=this run's six newly trained students, 2,688 independent output checks; A=framing supervision may regularize math features, mechanism not proven. NVIDIA actual calls **0** (no authorized callable live OpenRouter local worker); Codex **0**, Gemini **0**. Pro/Codex/VM/parser untouched.

**Next owner** independent SLE NN worker: isolate representation sharing versus detached independently supervised frame head under a new preregistered dataset. Add a deterministic 01 parser control and later explicitly authorized width/version profile before claiming structural SLE gains. Do not tune these now-observed test questions. No automatic merge.
