# R20 RESULT AND HANDOFF — route repair FAIL 1/3 (2026-11-14)

This is the independent SLE native01 small-NN study, separate from Pro UR1, Codex P030–P035, Hamster VM and dictionary/parser work. **Draft / do not auto-merge.** Parent is R19 PR #68 head `b7aada524b85f2771f6b98e7cb03402804037968`. [Frozen BEFORE training](FROZEN_BEFORE_TRAIN.md) commit `4878a53c4628f298da73f66320197a70f28304f5`; public [r2-only route core](route_core.py). All hashes and decision gate were registered before any new forward or optimizer call.

## Only neural semantic change

R19 had inadvertently masked **r1 STOP at cursor6** to input word b. R20 changes the R19 input route predicate:
```python
# R19:
second=((cursor>=6)&(cursor<12)).reshape(-1,1,1)
# R20, actual r2 header bit:
second=((cursor>=6)&(cursor<12)&(z[:,6,1]>0.5)).reshape(-1,1,1)
```
Therefore r1 STOP again sees a/b/c/d, while r2 second word still sees only b and r2 STOP cursor12 retains full input. Bookkeeping labels/reporting were also updated; model parameters and all remaining numerical operations unchanged. This is an **engineered prior**, not learned routing.

## Actual results

Predeclared primary gate: >=2/3 seeds, each r2 STOP correct position improves >=5/40 over frozen R19 on test_mid_b + test_high_b, with r1 STOP >=15/20, seen exact>=40/48 and taught_high exact>=16/32. **FAIL: only seed303 qualifies.**

| Seed | r2 STOP correct /40 R19→R20 | r1 STOP correct /20 R19→R20 | R20 seen and high retained | Gate |
| --- | ---: | ---: | --- | --- |
| 101 | 8→27 | 20→10 | 48/48; 32/32 | FAIL |
| 202 | 0→2 | 20→0 | 48/48; 32/32 | FAIL |
| 303 | 18→35 | 20→17 | 48/48; 32/32 | PASS |
| Total | **26/120→64/120** | **60/60→27/60** | 144/144; 96/96 | **1/3** |

R20 high-b full-answer score remains **0/60**, unchanged from R19. Mid-b full-answer score goes **8/60→11/60** (seed303 deteriorates 6/20→0/20). R20 did not establish transferable bit-copy ability. The r2 STOP improvement is an indirect trained-weight consequence of changing r1 STOP inputs; it is not proof of a unique gradient-interference mechanism.

One actual failed raw01 response: seed202 r1 a0 b24:
```text
Q        010100010000000110000000100000110111100
expected 000000S
actual   00000000000000000000000000000000 (cap, no STOP)
```

## Scope, costs, replays

Profile `SLE-AE1-n5-v1`: 39-bit raw01 input, four six-bit data words (five payload bits plus suffix zero), r1 or r2, no tokenizer/VM change. Exact same **already researcher-examined** R19 168-case manifest, SHA256 `972265d5f851727f3ce181b032032986374932e3bd8671f12b79722325b53edc`, same 136 teaching appearances/112 distinct examples. Splits seen_baseline48, taught_high32, val_b24 8, test_mid_b20, test_high_b20, test_joint_ab20, test_r1_stop20. All heldout **not newly blind**.

Fresh 3 students, seeds 101/202/303, 150 epochs/seed, **9,900 real Adam updates**, 633,600 supervised targets, 10,457 parameters/NN, 10,920 forward dense MAC/target, training forward 6,918,912,000 dense MAC excluding backprop. Initial weights, Adam, target multiset, order, seed and budget equal to R19.

Executed locally with Python 3.13.5, torch 2.10.0+cpu, NumPy 2.3.5:
```bash
python experiment_r20/run_r19.py gate --source-root .
python experiment_r20/run_r19.py train --source-root . --output outputs_r20
python experiment_r20/run_r19.py replay --source-root . --output outputs_r20
python experiment_r20/verify_numpy_r20.py --source-root . --output outputs_r20
python experiment_r20/route_contract_audit.py
```

Torch whole-answer replay 1008/1008 identical (includes 3 frozen R18 control students, NOT 1008 correct). Independent NumPy replay **1008/1008 identical**, measuring 15,405 greedy + 4,464 teacher-prefix = 19,869 neural forward calls / 216,969,480 inference dense MAC. Further bounded route audit 36 neural forwards / 393,120 MAC: old r1 STOP logits invariant to changing a, corrected r1 STOP sensitive, both r2-second logits invariant to a, both r2 STOP logits sensitive to a. First attempt at post-hoc route audit mistakenly loaded R19 weights into R20 code and failed; script fixed to instantiate the actual original R19 class, no changed student weights or training. No retry of the frozen experiment.

New checkpoint SHA256: seed101 `4231d63398493d683b94ab572f846a9267d5a20ad6a39edcec0baf976801b464`; 202 `0b241799b07458b144a3d2b9a6cf42f61f082d9b1b8377359878e5075bab5a62`; 303 `58137a8d4dacd33c1597bbdaa901a32640eb79060c9a16ebba0af8b2227d435a`. Raw results SHA256 `a24bd5b8ff545553fada7e4dbf1bd9b790fbee4444c38279b5587c3d5b7d9649`. Complete frozen R20 runner SHA256 `dbfad19c66ae2dd3f20113e8eb7e965fd576f9984462fd6a82c029897a28f15e`; prereg SHA256 `dc7b909c295840be5103f628ebd15fa2551d1a754a533622bab00c0de2d6b61d`. Full companion archive `sle_ae1_r20_r1stop_route_repair_20261114.zip` SHA256 `9c698971dfd6fe1f89701be99fc2fa592edce006f017efd5c4e89dbdf5671866`, 47 files, clean extraction SHA 46/46, torch replay, NumPy and route audit PASS. **Full weights and run file in companion ZIP, not Git**; Git-only repository contains frozen protocol, executable model core, results.

U = user requested independent native01 NN research; F = PR68 original runner/R19 checkpoints and R18/R14 sources; T = R20 actual training and independent checks; A = possible hidden task-specific shortcut and cross-task gradient effects, not proven. NVIDIA skipped (no authorized and reachable endpoint), local Codex 0, Gemini 0 actual calls. No private data, API keys, edits to other branches, or auto-merge.

## Next owner

Independent NN researcher: before introducing yet another hard-coded STOP rule, inspect r1 STOP mistakes, the r1/r2 STOP target frequency and logits under the **already observed** training domain. The next actual teaching experiment should freeze different unseen contexts and a capacity-/prior-matched ordinary-binary baseline; isolate one curriculum variable and preserve all retention failures. Shared math bank PR #5 is semantically verified synthetic material, not an NN mathematics-learning result.

[更新] Fixing r1 STOP input routing improves some r2 STOP scores but strongly reduces r1 STOP stability. [取代] Restoring original STOP input automatically improves the whole dual-route learner. [原因] Matched R20 experiment results: r2 26/120→64/120, r1 60/60→27/60, and 1/3 gate. [狀態] high confidence in measured behavior; low confidence in mechanism.
