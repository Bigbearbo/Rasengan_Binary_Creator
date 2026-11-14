# R27 SLE native01 firstword curriculum — executed results and handoff
Date: 2026-11-14. Independent scheduled SLE01 neural experiment (not a VM/parser study). Owner: scheduled NN researcher. Frozen prereg Git commit **a79ae0324f0007ca0c5a20d32fd366f6db9aa1e9**, pushed BEFORE R27 training. The prereg `FREEZE.md` is unmodified.

## Actual experiment
A single curriculum intervention on R20's unchanged 10,457-parameter dual-routed NN: of 136 training lesson tuples, replace 24 r=1 first-word low values a with 24,25,26,27, each six times, keeping r/b/c/d, total targets, optimizer and parameter topology. SLE-AE1-n5-v1 uses legal 39-bit native01 Q and 01 answers with external STOP. R20 control is **three frozen R20 checkpoints, NOT freshly retrained**. From initial states, train R27 seeds 101/202/303, 150 epochs, 3,300 Adam updates each, 9,900 total, 633,600 targets, 6,918,912,000 theoretical forward dense MAC (not backward, no FLOP/wall-time equivalence). No LLM oracle in the student's forward.

Before training: 120 distinct raw01 questions, 8 validation a26/27, 16 formal heldout a28/29 × contexts, 16 near-high a20..23, 48 seen_baseline retention and 32 taught_high retention. Test firstword a28,29 never shown in R27 course; these value concepts have been explored in historical work, so not globally investigator-blind. Precommitted gate needs >=2/3 seeds with test-firstword gain >=4/16, retention exact declines <=4/48 and <=4/32, test STOP decline <=2/16. Not redefined after scores.

## True primary outcomes
| seed | test firstword R20→R27 | test exact R20→R27 | test correct-position STOP R20→R27 | gate |
|---|---|---|---|---|
|101|8/16→16/16|2/16→8/16|5/16→8/16|PASS|
|202|16/16→16/16|7/16→7/16|7/16→7/16|FAIL|
|303|16/16→8/16|5/16→2/16|5/16→7/16|FAIL|
|**total**|**40/48→40/48**|**14/48→17/48**|**17/48→22/48**|**FAIL 1/3**|

The positive seed101 gain is cancelled by seed303 regression; seed202 begins at ceiling. Near-high a20..23 seed202 firstword regressed 16/16→4/16 (12 errors). Retention **complete responses** held: seen_baseline 48/48 and taught_high 32/32 for both arms, all seeds. R27 validation exact rose 12/24→21/24 across seeds but this does not prove novel a28/29 generalization. No extra seeds, patches or epochs were added.

Actual 720 complete native01 neural responses and all raw errors/logits saved; deterministic PyTorch replay passed 720/720. Separately implemented NumPy inference on original and new checkpoints reproduced 720/720 outputs, max logit difference 1.90735e-6, 8,920 NumPy forward calls. Original run 8,200 inference forward calls, 89,544,000 theoretical inference MAC.

## Post-hoc measurement erratum (do NOT erase)
The frozen experiment score() diagnosed STOP after response position6 for *both* r1 and r2. In r2 the cursor6 output is **second answer word's first bit, not STOP**, so the original retained r2 STOP diagnostics (e.g. taught_high 0/32) are **invalid**. Exact full outputs, firstword metrics and r1 validation/test STOP and all original gates are unaffected. Independent NumPy auditor rechecked the true correct-position STOP and obtained taught_high 32/32, seen_baseline 48/48, all 3 seeds, both arms. Raw flawed results retained. This is an evaluation-metric bug, not a failed NN training nor a posthoc alteration of frozen gates.

## Immutable evidence (SHA256)
```
R26 source ZIP      2c945803a5336820a5f17c72daaaa7cd1a9a46f9b9299c0fc0af87d1cbe115e3
R27 frozen runner   7ed975a5236f49d97f606aed6ae13b33bd010ae80591c503e19106c666c01399
R27 120 rawQ        5856ea02e4aff0d8386091b804f7fed886c5f3d7654b20aa024522945599b962
R27 prereg          9fe6a3052de9e0830a331c95e2a1861deb3e827037963d93fdd4ac0c5793e421
R27 full ZIP        73c13754de01739328547cda8dbe6f83c4aa105013b0a1a251681f57d15be0e0
new seed101 weights e8f2410ea8443ec4bcbb77e3375928d38a483d8fe91f2341730f8f78d184a83f
new seed202 weights 8a7f0dc273658b5af9a6249c47227d92841e8104ff7cba40fec3b9e042545e7f
new seed303 weights ddb5d382a5653229f7ece305c76fb20a91b71417868dacd57d76099577ea2845
raw full answers     cee763a9c84f14512b2d9729e5403602618f70d9d41e33594a6f4d634595b88e
```
Complete runnable source, frozen manifest, NumPy auditor, original R26 source+checkpoints, 3 new weights, 720 raw outputs, validation and SHA256SUMS are in the generated `sle_ae1_r27_firstword_curriculum_20261114.zip` conversation artifact (not yet embedded in Git; do not assume public Git by itself contains these binary checkpoints). Clean extracted bundle was independently verified with:
```sh
python r27_experiment/run_r27.py gate --source-root .
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r27_experiment/run_r27.py replay --source-root . --out ./r27_outputs
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r27_experiment/audit_numpy_r27.py --source-root . --out ./r27_outputs
```
The preserved prereg references the original source ZIP path `/mnt/data/work_r27/source_r26.zip` and unmodified source SHA; when re-executing frozen code extract at that same path. Running train mode again in the original output directory is intentionally rejected to preserve evidence.

## Ownership and next step
U: user's instruction for neural-native01 generalization, growth and elementary education; F: Git P030–P035 and R20/R23/R26 archived checkpoint evidence; T: this real three-seed NN run plus 720 replay and independent NumPy audit; A: value-targeted curriculum may promote new high-bit copying in some seeds but currently no robust group gain. Do not claim elementary arithmetic learned, SLE superior, or capacity growth demonstrated.

Next independent NN researcher: before any training freeze an additional *near-high preservation guard* and new disjoint high-a combinations to detect the 202/303 failures. Fair same-topology binary encoding comparator remains undone. No changes/merges to Pro/Codex branch; next owner should inspect new PRs before proceeding. NVIDIA skipped: no configured authorized live API endpoint, calls0. Codex calls0 (not local), Gemini calls0.
