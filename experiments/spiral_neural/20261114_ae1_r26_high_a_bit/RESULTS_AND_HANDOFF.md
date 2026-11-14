# R26 — 高位首詞單 bit 轉換與 nuisance 課程的跨上下文測試 (2026-11-14)

Owner: independent SLE 01 neural research; not VM/parser/UR1 or Codex redo. **Preregistered diagnostic PASS 2/3, NOT neural rule-acquisition PASS.**

## Sources and immutable pre-inference freeze

Read main AGENTS, research index, GIT_RESEARCH_HANDOFF_20261113, role contract, open/closed PRs, Pro branch RESEARCH_HANDOFF/CURRENT_RESEARCH_STATUS, P030 evidence index and P035 actual README, PR #5 bank (semantic tests only), and previous R20/R23/R25 checkpoints/evidence. PR #12's actual UR1 training failed 0/18 holdouts, not only prereg.

This branch forked `main` independently, modifying only this experiment folder. Exact 48 raw 39-bit SLE-AE1-n5-v1 questions committed **before any neural forward** at `a1dbdfb5dcfab9717d5ade32955a4a0a6d6d8e51`; split, six weight/source SHA256s, seeds, updates=0, cost, thresholds, and code SHA256 frozen at `cac17829962214bce2a305ce8e16c2c2531c7a04`. Complete runner SHA256 `8f14bf35713b1d93db46cb726c14a1a52643ad2ff30a76403a872e1c63a67c15`; manifest SHA256 `5088f373281616abed19ef9fd1666f19170cc48557100c99f126a0742d09ae6d`. Remote source matches prereg exact bytes.

**One paired input intervention**: change first data word exactly one raw bit, calibration `a16→20`, formal test `a24→28`; all r1/b/c/d fixed within pairs. `c=0/2` is preregistered stratification, not handpicked after results. Calibration: a16/20×b6…9×c0/2, 16 distinct raw Q. Formal test: a24/28×b10…17×c0/2, 32 Q. Fixed d6; ordinary data IDs, no upgrade profile assumptions. All full Q absent historical train/diagnostic manifests, but vocabulary/hypothesis previously studied—student-heldout combinations, **not researcher-blind**.

Comparison arms = previously trained **R20** versus **R23 nuisance-c2 lesson**; three paired seeds 101/202/303, six genuine immutable 10,457-param checkpoints, 0 new training targets and 0 updates. No large-model teacher oracle for answers; deterministic labels used offline only.

Gate frozen beforehand: for each seed and both a24/a28, R23−R20 c2 STOP-class mean margin >=+0.5, first-word correct across c0+c2 drops <=2/16, c0 STOP correct drops <=1/8; across seed first words must not be perfect or all wrong, otherwise non-informative. Require >=2/3 seeds. **2/3 PASS (101,303)**; seed202 excluded due to first-word ceiling. No posthoc regrade or extra training.

## Actual T — independent inference and replay

`python r26_probe.py preflight --root . --work r26_experiment` **PASS**. `python r26_probe.py evaluate --root . --work r26_experiment` executed **288 full native-01 PyTorch generations**, 6,978 greedy+288 STOP-position forwards = **7,266 forwards**, 79,344,720 theoretical dense forward MAC, 0 optimizer updates. `python r26_probe.py replay --root . --work r26_experiment` independently reproduced **288/288** complete outputs + STOP logits using NumPy; max abs logits delta 1.43e-6. Original 288 raw replies/labels/stop causes/logits retained in companion ZIP; raw SHA256 `d5e1529fe514afe92d0ab5b820cf665e5ffa12011233181dbcbaee1f36df898c`.

| Formal test, three seeds | Historical R20 | Historical R23 |
|---|---:|---:|
| First answer word correct | **64/96** | **64/96** |
| STOP class correct at right cursor | 6/96 | 14/96 |
| Complete bits + S correct | 4/96 | 10/96 |
| c2 STOP class correct | 1/48 | 3/48 |
| c2 complete answer correct | **1/48** | **1/48** |
| c2 STOP mean margin | −7.3553 | −4.8072 |
| c0 STOP class correct | 5/48 | 11/48 |

Per-seed test: 101 first16→16/32, STOP2→3/32, exact2→3/32; 202 first32→32, STOP0→4, exact0→4 (informativeness FAIL, ceiling); 303 first16→16, STOP4→7, exact2→3. On calibration, first words **48/48→40/48 deteriorated**, although STOP12→21/48 and exact12→17/48 improved; keep this counterexample visible.

Representative full Q fail (seed101, R23, a28 b10 c2 d6):
```
Q        010100010111000010100000100001100111100
expected 111000S
actual   10100000011000000000000000000000
cause    cap (32 bits, never emitted S)
```

**[更新]** Nuisance lesson helps some STOP margins/class decisions even in harder high-bit first-word contexts; neither first-word exactness nor c2 full answers improved. **[取代]** Inferring broad copy generalization from R25's STOP benefit when first-word was already 96/96. **[原因]** New high-bit first-word cases show 64/96→64/96; c2 full answers 1/48→1/48, plus calibration regression. **[狀態]** High for these fixed-checkpoint metrics and NumPy replay; low for generalizable autonomous copy/rule learning.

## Boundaries and next owner

NVIDIA status **skipped_unavailable**: no authorized accessible OpenRouter worker/key in this runtime; actual NVIDIA calls=0; local Codex=0, Gemini=0. No merge, no Pro/Codex branch modifications, no private chats or credentials.

**Next owner**: independent native SLE-01 learner researcher. Preregister an **equal-training-budget curriculum intervention** on genuinely heldout *first word bit* values, separately gate first-word exactness, STOP, full-answer, and old-skill retention, and compare an ordinary-binary matched-inductive-bias control. Don't relabel R26 as blind or retry same exposed test. Do not add human routing fixes and call them autonomous learning.

**Companion reproducible ZIP** (not committed to Git; contains six exact weight files, 288 full raw outputs, prereg, runner, original reference & independent NumPy code, SHA256SUMS):
`sle_ae1_r26_firstword_highbit_20261114.zip`, SHA256 `2c945803a5336820a5f17c72daaaa7cd1a9a46f9b9299c0fc0af87d1cbe115e3`. Clean extract: **28/28 SHA256 PASS**, static preflight PASS, independent NumPy replay 288/288 PASS. Git alone is report/source, not complete checkpoint verification; the companion ZIP is required.
