# R30 PRE-TRAINING FREEZE — 2026-11-15

**Status:** FROZEN BEFORE NEW NEURAL FORWARDS/TRAINING. This is an independent SLE-AE1 native 01 NN study. NOT the Hamster VM, syntax/parser, Pro UR1, or Codex P030–P035.

**Owner:** independent scheduled native01 NN researcher. **Source control:** R28 draft PR #78, R29 draft PR #79. Parent R28 checkpoints retained exactly, not retrained. Separate new branch; no merges. The source bundle is the previously generated R29 companion ZIP, and R28 experimental materials are extracted from it. The public repository has *not* necessarily stored every original checkpoint; the runnable companion bundle will accompany the result.

## Unique causal variable

Compare R28 `DualRoutedStudent` against R30 `NoFirstMask`: remove *only* the `cursor < 6` hard mask which allowed the first six answer bits to attend only to first data word `a`. All four SLE input words are now available for those output steps. Retain `r2` secondword `b` mask, `r1` stop routing, identical linear layers / 10457 params, identity initial state per seed, identical R28 136 lesson presentations and exact ordered targets, Adam settings, batches/shuffles and budget. Dense per-target forward MAC remains 10920 (not accounting for tiny boolean masking overhead). This tests architectural prior's effect, **not** SLE-vs-plain-binary encoding advantage.

## Immutable sources

- R28 runner SHA256 `606b7e3446c02fc00169e379988b99cd181e048a57877ef763f999aed38ed8a2`
- R28 trial prereg SHA256 `frozen in prereg.json` (exact SHA in companion bundle)
- Original R20 dual-route runner SHA256 `frozen in prereg.json`
- R14 native codec SHA256 `frozen in prereg.json`
- R28 complete experimental ZIP SHA256 `bdb5d47ec9dcdef851247136c85acbf7923f4d9c9631b9b5357ccbe699d562dc`
- R30 runner SHA256 `6bee5e15bd2954c90907a1b9c033df0d4ec7002f867ac79d3c2ba19890c72a13`
- R30 exact 168-item native raw 01 manifest SHA256 `b8a7aa71b1921e28b8fc85f61e2ae16c5856dbd13d59d612bd506bbb7d2eac64`
- R30 prereg JSON SHA256 `a876f41b6a4719c8ed967c3b0fb202b982bd2789148fbfc5a887206f0b526eea`
- R28 immutable checkpoints, seed101/202/303:
  - `R28` hashes maintained in frozen companion `prereg.json`; verified before training by static gate
- Training course SHA256 and the other source SHA256 values also present in companion `prereg.json` and validated by code.

## Legal SLE profile / raw IO

`SLE-AE1-n5-v1`; each 39-bit input is `01+010+r3+0+four*(5bit_ID+0)+111100`, ID 0–29. Each first answer word is `word(a)` = five binary bits plus terminal zero; R2 additionally outputs `word(b)`; `S` is a **separate external stop action**, not a lexical bit. Output comes from model autoregression, not a teacher model or answer oracle. Codec is used **only** to construct supervised labels and score generated answers.

## Course, groups and gate

Train: R28's same **136 presentations (112 distinct)**, 1408 supervised prefix targets per epoch. R1=60 and R2=76, 150 epochs. Seeds 101/202/303. Adam lr .003, batch64, gradient clipping 1. 3300 updates per seed, **9900 new** updates across 3 students, 633600 new target presentations and **6,918,912,000 forward dense MAC** (backward excluded). Neither student's training contains a28 or a29.

Frozen 168 raw input / expected-answer records:
- validation 4, taught a26/27, new b/c/d context
- formal unseen-a 24, a28/29 not in either R28 or R30 training
- near-a 32, a20..23 taught values but never these full Q
- one-word STOP diagnostics 24
- second-word r2 diagnostics 4
- old retention: 48 seen_baseline and 32 taught_high copied *unchanged* from R28 manifest.

No full raw Q outside declared retention is in training. **R28's firstword b/c/d route implies repeated contexts are not functional independent observations; report effective distinct a count and logits variation instead of claiming 24 independent context replications for the masked arm.** The a28/29 values were already seen by *researchers* in R27–R29, so these are student-held-out but not researcher-blind.

Preregistered joint PASS requires **ALL** across 3 seeds: formal unseen-a firstword improvement >=6/72 against frozen R28; full-answer improvement >=6/72; near-a firstword regression <=6/96; old retention full-answer regression <=12/240; and true-position STOP accuracy regression <=6/72. A failed composite remains FAIL; do not re-tune after observing outputs. All per-seed results, 01 model outputs, failure examples and saved weights must be kept.

The single variable deliberately removes a high-bias structural aid. A possible result is worse firstword learning despite more contextual accessibility, and that is scientifically valid; we will not convert it to a new course or spend extra training budget. NVIDIA only if an authorized read-only non-sensitive worker endpoint is available; none is configured here, expected actual calls 0. Local Codex/Gemini calls 0.

Provenance: **U** user research scope/independent causal experiments, **F** immutable R28/R29 real training and checkpoints, **T** static manifest construction and SHA calculation only as of freeze, **A** impact of unmasking is uncertain. Do not infer new neural training from this freeze record.
