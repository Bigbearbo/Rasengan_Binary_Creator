# R39 actual experiment — remove engineered b-only second-answer routing

Date 2026-11-15. Independent scheduled SLE raw-01 NN researcher. Parent R38 Draft #88. **PRE-TRAINING Git freeze `697b0cf967b42135f6d16944fc9e0a72bc89ad9f`**; no post-result gate edit. This is a new experiment, not a rerun of Pro UR1 or Codex P030–P035.

## One matched change

Use R38's 136 ordered teaching events (8 high-b replacements), exactly the same init/training/splits, and 10,457 weight-tied model parameters, but **remove the engineered b-only mask when generating the SECOND numeric answer word**. The old model was R30 `NoFirstMask` (unmasked first, hard-routed second); the new model is the fully unmasked reference `WordStudent(True)` with identical parameter tensors and same dense-MAC accounting. Preflight tested all unaffected output positions produce bitwise-identical logits given identical initial weights. No change to curriculum, answer, STOP, seed, or optimizer.

Profile `SLE-AE1-n5-v1`, values 0..29; raw Q exactly 39 bits: `01 + 010 + bin3(r)+0 + word(a)+word(b)+word(c)+word(d) + 111100`, `word(v)=bin5(v)+0`; answer one or two six-bit words and an external STOP action S. Teacher answer is deterministic frozen codec output, never LLM-student answer injection. Not Pro UR1, no unauthorized profile.

Three fixed seeds 101/202/303; Adam .003, batch64, clip1, 150 epochs, 3300 updates per seed, 9900 new updates; 633600 target presentations; **6,918,912,000 theoretical training-forward dense MAC** (backward and overhead excluded). Old R38 controls reused (not retrained). Same 128 per-seed questions across four previously inspected splits: high-b/known-b/displaced-b (16 each) and historical mixed-arity (80). This is a matched **nonblind** intervention.

## Preregistered gate and actual FAIL

All five required: high b second>=40/48; known b second>=44/48; displaced b second>=36/48; historical complete exact>=216/240; high-b complete exact>=6/48. **All five FAIL**, not adjusted after evaluation.

| Tested metric (3 seeds aggregate) | R38 hard-route | R39 full-input second | Δ |
|---|---:|---:|---:|
| High b26/27 second numeric word /48 | 48 | **17** | −31 |
| Old b18/19 second numeric word /48 | 48 | **11** | −37 |
| Displaced b20..23 second numeric word /48 | 40 | **13** | −27 |
| Historical mixed-arity complete answer /240 | 228 | **211** | −17 |
| High b26/27 complete autoregressive answer /48 | 1 | **1** | 0 |
| High b26/27 first numeric word /48 | 2 | **5** | +3 |
| High b26/27 STOP with **gold** answer prefix /48 | 13 | **48** | +35 |

The STOP contrast is crucial: predicting STOP after a **correct oracle-supplied prefix** is not successfully generating that prefix. Among historical examples the r1 subset stays **72/72**, but r2 complete outputs deteriorate **156/168→139/168**. The old name `prior_r1_retention` in the manifest covers *both* arities (24 r1+56 r2 per seed). High-b secondword per seed becomes 10/16, 3/16, 4/16; none gives overall mastery. This result supports a course-dependent engineered-routing inductive-bias benefit, **not proof that a b-only mask is a legitimate general solution**.

Counterexample: seed101, r2 a14 b26 c1 d5, raw Q `010100100011100110100000010001010111100`; gold `011100110100S`, model returned `010100110100S`. It does generate a correct secondword but fails firstword and thus full answer. Raw outputs contain all successes and failures.

## Real execution, audit and artifacts

New models trained in this run. 384 new original-01 autoregressive full generations, **4,944 neural forward evaluations**, ~53,988,480 inference dense MAC. PyTorch replay **384/384 exact**; independently written NumPy forward/greedy replay **384/384 exact**, maximum logits delta `1.9073486328125e-06`. Re-extracted companion bundle cleanly and checked **160/160 SHA256 files**, then both replays pass. No extra seeds, new answer labels or revisions to predeclared threshold.

Local immutable SHA256: R39 source `fc50668670a82add52a2b5ba23538f2d8780b815dba8750e89954134d96607f9`; prereg JSON `106e2ad84fad019e33c21d3b7b956c7bba9f21fe3c1872e5de192868cfe6a0bb`; 128-row Q manifest `781e351ead001a74a30f75be3f92347bbe70530149a4fec126b23b35c90c35b9`.

New weight SHA256: 101 `ac4abadea486343edf5452b151e92bdbe0b02288076e0d0d7257f691165e9467`; 202 `604f498f69cb1a2946012bfbdcfa41a6d705ec9cc3bfac57820e35ee2c3a1632`; 303 `e091257cb978142c085a885ac1c2c5151d76cabef7e968f6f643f742a13d2b79`.

Full companion `sle_ae1_r39_secondword_unmask_20261115.zip`, **2,036,902 bytes**, SHA256 **`7fd8ccf20c9f442fef187f9ce6261aab08525c827e262411b250da5a347a6880`**, 161 entries including exact frozen runner, source dependencies, 3 checkpoints, all 384 raw results, checker, 160-file SHA list. It is attached to the conversation, **not hosted on GitHub**; Git-only checkout cannot independently recompute the actual NN weights. Run after extraction:

```sh
python verify_r39_readonly.py
# or individually: python r39_second_route.py gate|replay|numpy
# train on a separate fresh directory without r39_outputs, never overwrite existing weights
```

## Provenance / limitations / next owner

**U** user's independent SLE bit learning/training/generalization direction. **F** R31–R38 frozen code/checkpoints, Codex P030–P035, Pro UR1 #12 (separate). **T** 3 R39 new trained students, 9,900 updates, 384 original-01 generations, two actual independent replay routes and clean archive verification. **A** route constraints can reduce interference at the cost of imposing a copy-specific prior; explanation in terms of learned internal representations remains uncertain.

NVIDIA 0 actual calls (no authorized callable worker), local Codex 0, Gemini 0. No Git merge; no edits to Pro/Codex/Hamster-VM/parser branches or any private material.

**Next owner:** independent SLE neural worker. Single candidate: train a learnable (soft, initialized b-only) route with extra parameter/MAC costs explicitly matched, testing whether it can keep new/old b retention while not hard-coding context independence. Test-set re-use needs fresh legal blind domain before external validity claims.

[更新] Full-input secondword degraded trained role mappings despite better gold-prefix STOP. [取代] Mask removal alone would support unrestricted copy. [原因] high-b 48→17, known b 48→11, historical exact 228→211 while full high-b exact stays 1. [狀態] controlled observation/replay high; mechanism/general advantage low.
