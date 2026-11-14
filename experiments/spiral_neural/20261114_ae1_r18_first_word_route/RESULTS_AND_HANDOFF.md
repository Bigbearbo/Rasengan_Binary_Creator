# SLE-AE1 R18: first-answer hard-input routing (actual result, 2026-11-14)

This is an **independent neural student** experiment, not Hamster VM, syntax-dictionary research, or Pro UR1 approval. Research branch: `research/scheduled-nn-ae1-first-word-route-20261114-r18`. Base: main `d032a825c2b419f365bf34a531baee3b53b91750`. No other worker's branch changed.

**Prerequisite/freeze:** [FROZEN_BEFORE_TRAIN.md](FROZEN_BEFORE_TRAIN.md) landed as Git commit `736456ec67d1268317c972a40ea42b6f68eb8472` *before* the first R18 neural forward. All 168 full raw-01 questions, seven splits, gate, seeds, R14 checkpoint/source SHA and runner SHA were fixed. `gen_manifest.py` deterministically reproduces the 168-case Q/expected manifest with SHA256 `1b16c0cf72d9a9517959aac21b8cf9e7a81110b7ab6c2b52dd634d181c5ca3cc`. Offline expected labels are **not** inputs to students.

## One-factor test

Existing R14 PR #63: 3 frozen `balanced8_16` full-input checkpoints (seeds 101/202/303), identical model family. New R18: 3 newly trained 10,457-parameter students; first six predicted positions may see only **first word a**, common header, and cursor, with b/c/d input embeddings masked; second answer/STOP see all four input words. Same seed initialization, 136 training appearances (112 distinct, 120 parent+8 bit8+8 bit16), 150 epochs, Adam .003, batch64, 3,300 updates/seed and fixed target multiset/order. The route is **hand-imposed**, therefore invariance is not student-inferred understanding.

Legal profile `SLE-AE1-n5-v1`, 39-bit native Q `01+010+r(3bits)+0+4*(5bit ID+0)+111100`. S is the external generation STOP **symbol**, not an 01 token. The model never reads an oracle answer during prediction.

## Results

| Three seeds combined | Baseline full answer | Routed full answer | Baseline first answer word | Routed first answer word |
|---|---:|---:|---:|---:|
| Seen baseline (144) | 137 | 132 | 144 | 144 |
| Taught high-bit examples (96) | 96 | 96 | 96 | 96 |
| New first-word value with d2 (60) | 0 | 19 | 0 | 52 |
| New first-word value with other b (60) | 11 | 39 | 32 | 52 |
| New first-word with extreme b (60) | 0 | 9 | 0 | 52 |
| Paired b bit interventions (72) | 0 | 31 | 0 | 64 |

**Predeclared gate PASS 3/3 seeds**: first-word gains (of 40 target cases per seed) +31, +18, +23; seen-exact 47/48,43/48,42/48; taught-exact 32/32 each; deliberately enforced first-word b-pair invariance 12/12 each. On the 40 primary unseen-first-word cases per seed, first-word success pooled from 32/120 to 104/120, and full-answer from 11/120 to 58/120. First-word mask is a designed bias, not autonomous copying discovery.

**Failure examples**, retained verbatim:
- Seed101, r2,a25,b0,c1,d2: Q `010100100110010000000000010000100111100`; expected `110010000000S`; actual `11001000000000000000000000000000`. First word and second word matched but STOP failed (generation cap).
- Seed101, r2,a25,b16,c0,d1: Q `010100100110010100000000000000010111100`; expected `110010100000S`; actual `110010000000S` (second-word mistake).
- Overall routed first word in *extreme b* 52/60 but full string only 9/60. Seen baseline exact falls by 5 across 144; therefore the intervention is not cost-free.

## Execution & independently checked evidence

New training: **3 students, 9,900 Adam updates, 633,600 training target forwards**, 10,457 parameters each, **6,918,912,000 theoretical training-forward dense MAC**, backward excluded. Six models x168 questions = **1,008 complete native01 free answers**, **13,684 generator forwards**, **149,429,280 theoretical inference-forward dense MAC**. No target answers fed during evaluation.

Actual CPU PyTorch replay from saved six checkpoints: **1,008/1,008 output rows identical**. Independently implemented NumPy tensor-only evaluator: **13,684/13,684 generation positions reproduced**, 0 mismatches. Independent repeat is numerical agreement, not a claim that every answer is correct. ZIP with frozen original runner, raw cases, complete outputs, three new + three baseline weights, source and course, SHA256SUMS, and NumPy checker was verified after clean extraction; SHA256 of entire ZIP is `fca99a3c51193a7aa59d414c80a6407ea9b189175aacdb1abfd77e27f1fcaca7`. The ZIP companion was delivered in the conversation, while the full binary/source research bundle **is not in Git**; Git-only checkout cannot independently replay 1,008 predictions without companion archive. Exact runner SHA256 `4793596815bcac55803fae9bcb3a09526caaa7e10dbd00e6f645ae325e256722`; raw result SHA256 `5db61ed6b3dc68421e33faba7f1a8a570c02b0a332048b0e5599de183a6549de`. Trained weight SHA by seed: 101 `9a459111552d90f857e00f854aaa89cc1d10bb680d80663bb8c9670aa9ae44ed`, 202 `225a28f6e1871b44236627e0ed1ab60ad69085891ec04a1fc2d66782689ca5a4`, 303 `c0b3b083f6b85bad5a6f03589fe95351f17085f761c5df3c7475de9db46fc004`.

Inside companion ZIP:
```bash
python experiment/run_r18.py gate --source-root r14_source
python experiment/run_r18.py replay --source-root r14_source --output outputs
python experiment/verify_numpy_r18.py --source-root r14_source --output outputs
# Fresh training in a *new* directory only:
python experiment/run_r18.py train --source-root r14_source --output NEW_OUTPUT
```

## U/F/T/A and next owner

**U:** user requested autonomous, small native01 neural research with curricula, unseen values and causal comparisons. **F:** original P030–P035 evidence, R14 PR #63 checkpoint/source, R17 PR #66 prefix-blind architecture analysis. **T (this run):** Git prereg, static preflight, three new real CPU trainings, 1008 free responses, PyTorch and independent NumPy checkpoint replay, ZIP SHA clean extraction. **A:** first-answer masking may reduce shortcut dependence on other words; mechanism generality unknown. The fixed benchmark has previously researcher-viewed related values; not globally blind. There is not yet an equal-structural-prior binary-vs-SLE comparison.

**Next owner:** independent SLE NN worker; preserve this batch immutable, preregister truly new context/value split, evaluate route-to-second-answer and STOP/retention, *then* equal-prior non-SLE raw binary control. Avoid optimizing previously observed heldout values. Even if full-word routing succeeds, it can become an engineered copier rather than evidence of genuinely learned hierarchical semantics.

NVIDIA reviewer **skipped_unavailable** (no authorized callable endpoint), actual calls 0; local Codex 0; Gemini 0. No private notes, account data or keys uploaded. This is an unmerged draft evidence result, not a statement of Codex/Pro execution.

[更新] Forced first-answer input isolation improves heldout first-word predictions under this matched course.
[取代] Training more examples is necessarily the only plausible way to address b-to-first-word interference.
[原因] Both groups have matched seeds, exposure and parameter/MAC budget and three predeclared gates pass; full-output error and seen-task loss survive.
[狀態] This sample's measured improvement high confidence; independent general copying and SLE-specific advantage low confidence.
