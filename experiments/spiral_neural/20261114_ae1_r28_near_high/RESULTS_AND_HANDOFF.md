# R28 — real three-seed near-high rehearsal (2026-11-14)

**Formal preregistered composite gate: FAIL.** Independent SLE native-01 small NN, not a VM/parser/UR1/Codex P030–P035 rerun. Original freeze commit [`035975baa`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/035975baa1d17e2bb092b5ce6eba6eacdca857d1) existed and was pushed **before any R28 training**. Parent R27 [PR #77](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/77), head `dcd5d9ccf9f179f4030630879ed89e3903a21823`. `FREEZE.md` is unmodified. No merge into main.

## Unique change, honest resources and split
Compared with R27's same-initialization curriculum (24 r1 firstword `a24..27` slots), R28 **changes only 12 of those 24 training occurrences to `a20..23`**, keeping the other fields, fixed 136-lesson stream, 1408 target-prefix pairs/epoch, 10,457-parameter dual-routed NN, SGD? **Adam lr 0.003**, seed 101/202/303, 150 epochs, shuffled64-target minibatches, 3300 actual updates/student, **9900 new actual Adam updates, 633600 target appearances, 6,918,912,000 theoretical forward-only dense MAC**. Same initializer `seed+12000` and batch order `seed+201000+epoch`. R20/R27 are **frozen saved checkpoint controls, not retrained**. This is SLE-AE1-n5-v1, 39-bit legal input, 6-bit firstword (optional secondword for r2) plus external STOP, NOT Pro UR1.

Exact pre-frozen 136 unique native 01 questions: validation_taught_high8, test_unseen_high16 (a28/29 values **never trained**, new held-out Q/context not previously tested), test_near_transfer16 (a20..23 values now **trained in R28**, only pair/context is held out), legacy_near_diagnostic16 (already viewed), seen_baseline48 and taught_high32 (retention). Do not claim researcher-global blind high values or unseen a20..23 values.

## Precommitted composite gate (must pass ALL) — failed
Near-transfer firstword aggregate gain ≥8/48; high a28/29 firstword decline no worse than −6/48 in total or −4/16 per seed; high true r1 STOP loss no worse than −6/48; all seeds preserve seen-baseline full exact (loss ≤4/48) and taught-high full exact (loss ≤4/32). No post-outcome adjustment.

| Seed | Near-value firstword R27→R28 /16 | High a28/29 firstword R27→R28 /16 | High complete exact R27→R28 /16 |
|---|---:|---:|---:|
| 101 | 12→16 | 16→16 | 5→5 |
| 202 | 4→16 | **16→0** | 6→0 |
| 303 | 16→16 | 8→16 | 3→10 |
| **All** | **32→48 /48** | **40→32 /48** | **14→15 /48** |

Correct-position r1 STOP high 21/48→22/48, seen-baseline exact 144/144 and taught-high exact 96/96 retained. **Seed202 catastrophic reversal**: for all eight new a28 contexts, generated firstword `101000` where truth was `111000` (alias to **a20**); all eight a29 contexts produced `101010` where truth `111010` (alias **a21**). Raw full-response examples show some `c=2` cases continue without correct STOP. The alias is a directly observed behavior, not proof of neuron-level causality.

**Avoid repeat R27 scoring bug:** r1 STOP located at prefix6, r2 STOP at prefix12. Primary scoring only applies r1 STOP; r2 split in generic summary has `STOP=0` because it is **ineligible**, not because failures occurred. Independently recalculated r2 real STOP **32/32 each of three seeds in each control/training arm** on taught_high.

## Actual execution and independently verified archive
Real fresh PyTorch three-seed training: 9900 actual Adam updates, 3 full new checkpoint JSON files, **1224 complete generated native01 responses and STOP logits**. Independent PyTorch replay **1224/1224** matches byte-for-byte; separate NumPy (not PyTorch inference) implementation also matched **1224/1224**, max absolute STOP-logit difference **2.86102294921875e−6**, 15,634 NumPy forward calls. Original inference: 14,410 forward calls, ~157,357,200 dense MAC. These are replay correctness, *not* task answers or generalized language mastery. Parent zip, scripts, all weights, manifest, 1224 raw results and independent auditor included in conversation artifact `sle_ae1_r28_near_high_rehearsal_20261114.zip`, whose SHA256 is **`bdb5d47ec9dcdef851247136c85acbf7923f4d9c9631b9b5357ccbe699d562dc`**. Git does **not** embed full binary weights; do not pretend Git alone can replay.

Archive integrity: **53/53 files** hashed (52 data entries + SHA256SUMS), CRC PASS. In **clean extracted directory**, `sha256sum -c SHA256SUMS` PASS, static prereg `gate` PASS, original torch `replay` 1224/1224 PASS, independent NumPy 1224/1224 PASS. Commands:
```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python r28_experiment/r28_runner.py gate
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python r28_experiment/r28_runner.py replay --out r28_outputs
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python r28_experiment/audit_numpy_r28.py --root . --out r28_outputs
sha256sum -c SHA256SUMS
```
Key immutable SHA256:
```
frozen runner         606b7e3446c02fc00169e379988b99cd181e048a57877ef763f999aed38ed8a2
frozen prereg         8ca9f71039e207834f03bd3931885ac10c36c1be9b8a0ded0af0fed4317ed704
frozen raw manifest   e935dd9bc3836168ea93ce3a50860a25876c821b939172d000e87660b76cd9c9
R28 seed101 weights   8558e0c71f6e0a964f1eb5974903f63cb863c8ea0c57e0fd89867193b3122b0c
R28 seed202 weights   7f2d011cdf5bed155523823ea575ed0be640db8b0fdd2e6b062a65938443e44c
R28 seed303 weights   b395b800b2497c963c5ed1dcd58f8090b333fcb5b6780c1ec56311b7ccb1e5b6
R28 raw outputs       dbe5015ff430c0e2a4e85845fa7e1eb77d1218efbec246c8c67ed7ea2e84dbcb
R28 results           15bc08dd00836762a16d3826f14e24eeb0d465d5a1307c17f46355de268a49b3
NumPy audit           90b34e86b0d0cd26689d02376cbb525403c900151a7812859f70429d472a5379
```

## Provenance, collaboration, next owner
- U user: independent student NN native-01 learning/generalization/growth/primary-school mathematics; R28 is a narrow curriculum test only.
- F: saved R20/R27 source/checkpoints, Git P030–P035 source reports, Pro true UR1 negative results [PR #12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12), plus separate Codex [PR #61](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/61). No existing work re-executed.
- T: this actual R28 local PyTorch training, all generated outputs and independent NumPy tests.
- A: balancing nearby values may induce observed a28→a20 / a29→a21 alias and seed-specific interference; actual mechanism remains unverified.
- NVIDIA: **skipped_unavailable**, approved live OpenRouter endpoint not exposed to this run; **0 actual calls**. Local Codex **0 calls**; Gemini **0**. No private chats, Project Library or API keys included.
- Next independent NN owner: pre-freeze disjoint a28/29 context test and an **equal-topology/prior, equal-budget ordinary-binary comparator**, or investigate high→near alias with a controlled probe; do not add posthoc epochs/seeds to rescue this FAIL. No math learning, general copy induction, SLE-over-binary advantage, or NN physical growth claimed.

See frozen `FREEZE.md`; the generated ZIP includes full `R28_RESULTS_AND_HANDOFF.md` and runnable sources/checkpoints. Git publication contains only safe, publicly discussable provenance, metrics and code-verification guidance.
