# R48 — b+d neural input-source ablation (2026-11-15)

**Preregistered joint gate FAIL: 2/7 pass.** Three new SLE native 01 small NN students trained only after the Git pretraining freeze commit e50746224b7a5583640c4962f7c311d5c193f250. Single factor relative to R44: r2 second answer word reads b+d rather than b only. a,c still masked. All other routes identical. Earlier R44/R45/R46/R47 models are read-only historical controls, not retrained.

## Results (3-seed aggregates)

| Metric | R44 b-only | R46 a+b | R47 b+c | R48 b+d | R45 all |
|---|---:|---:|---:|---:|---:|
| b18/19 second | 48/48 | 40/48 | 16/48 | **12/48** | 0/48 |
| b20–23 second | 80/96 | 20/96 | 8/96 | **0/96** | 0/96 |
| b24/25 second | 48/48 | 18/48 | 36/48 | **36/48** | 0/48 |
| b26/27 second | 48/48 | 32/48 | 32/48 | **28/48** | 2/48 |
| b28/29 second (role-untrained) | 48/48 | 20/48 | 4/48 | **8/48** | 1/48 |
| Historic 80Q full answer incl autonomous STOP | 228/240 | 206/240 | 234/240 | **221/240** | 209/240 |
| New 96Q full answer incl autonomous STOP | 0/288 | 0/288 | 0/288 | **1/288** | 0/288 |
| Gold-prefix STOP, not free accuracy | 10/288 | 3/288 | 202/288 | **273/288** | 288/288 |

**Preregistered thresholds**: b24/25 >=40/48 FAIL; b26/27 >=40/48 FAIL; b18/19 >=40/48 FAIL; b28/29 >=32/48 FAIL; b20–23 >=72/96 FAIL; old full >=216/240 PASS; new complete >=1/288 PASS. **Joint FAIL**. The lone complete success is seed101, Q=010100100010110100110011000011100111100 (r2,a11,b19,c12,d14), actual=expected=010110100110S. One success out of 288 is not reliable full-answer generation.

New 96Q secondword scores by seed: 24/96, 48/96, 12/96. Historic complete scores: 74/80, 67/80, 80/80. Gold-prefix STOP: 96/96, 81/96, 96/96. Strong cross-seed variation; interference effects of a/c/d cannot simply be added together.

## Exact protocol, workload and sources

Legal SLE-AE1-n5-v1 (0..29). Question is 39 literal bits: 01 + 010 + bin3(r)+0 + four*(bin5(v)+0) + 111100. Student produces r six-bit bin5(v)+0 words plus external S action; this is not an on-wire sentence terminator and is not the separate Codex whole-region model.

Exactly R44 136 ordered lesson events; 1408 teacher-forced targets/epoch, 150 epochs, batch64, Adam lr0.003 clip1, seeds 101/202/303; 10457 parameters/student, 3300 updates/student, **9900 actual Adam updates**, **633600 targets**, **6918912000 theoretical forward dense MAC**, backward/optimizer excluded. No LLM/teacher oracle during free generation. Historic 80Q read-only validation and previously inspected 96Q test x 3 seeds; **not blind**. d train0/1 vs test14/15 is an explicit nuisance shift. No post-test additional epochs, seeds, model selection or retuning.

Source freeze digests:
- Trainer R48 script SHA256: b2ea96c9c48e5635ddd48ad3d7a3e919677869f52a08ce0a00918eb45c252230
- R48 prereg JSON SHA256: 20bd680bb2542733097ccba6993c49e4e8655e56a14e2780a5b70e119735e254
- R48 manifest JSONL SHA256: d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416
- R44 course SHA256: a8c28b69fe15b8b8181dd701b3da4abb723e47acc866c8b920e854fac758f8fe
- New weights 101: ab39d2200835f179e36b9a3e845cd158ae8a5e7a9d610c8811bf69fcc5d21b09
- New weights 202: ac09556a77365f4b8a56cb26d426c55ba57c9ad98cc4327a0ab3d1b40da7493b
- New weights 303: e808951f75dc61f26d5df8a9220c20d2b4e1b482d3d95d1219bb6fdc4575497f
- Raw 528 results: 4c7f786fa61c9b19032d46928c5c04d2537e4946b94b4717d30e6ca529624563

**Executed in a clean extracted directory:** python verify_r48_companion.py -> 262 SHA256 files PASS; python r48_bd_second_route.py replay -> 528/528 PyTorch exact replay PASS; python r48_bd_second_route.py numpy -> 528/528 independent NumPy replay PASS, max logits error 1.9073486328125e-6; python audit_r48_route.py -> 414/414 fixed-weight pairs PASS, including 138 differences confined to r2 secondword and 276 unaffected positions exactly identical.

**Full companion file** sle_ae1_r48_bd_second_source_20261115.zip, SHA256 **abdb7cf4d616e635d9a16946b81d149d98906aa0cedfe28b779190ad4b49ec17**, shared in originating ChatGPT conversation, **NOT uploaded to Git**. ZIP contains 3 new complete checkpoints, previous immutable dependency files, the complete trained source, all free raw answers/failures, 262-entry SHA inventory, replay scripts and full detailed report. Git-only cannot replay weights without ZIP.

[更新] Independently admitting irrelevant d interferes with secondword correctness under identical training, yet increases gold-prefix STOP; a,c,d have now each been isolated. [取代] Only a and c isolated; d effect unknown. [原因] R48 trained 3 students with only b+d masking changed relative to R44. [狀態] Numeric result high confidence, neural causal mechanism and broad generalization medium-low confidence.

**U** user's SLE native01 NN learning scope; **F** PR#95–#98, P030–P035, Pro#12 and archived artifact; **T** actual three R48 trainings, 528 free generations, independent replay and fixed-weight mask audit; **A** input-source interference hypothesis. NVIDIA/desktop Codex/Gemini actual calls **0**; no authorized NVIDIA endpoint/local Codex connection in this runtime. No other branches changed, no automatic merge, no secrets.

**Next owner:** independent NN researcher. Instead of another blind source release, use existing frozen checkpoint diagnostics or preregister a matched-budget learned conditional source router, with complete autonomous output and STOP as independent necessary tests. Codex's PR#90 whole-region, three-round, native sentence-terminator student must not be confused with this separate AE1 per-bit external-STOP series.
