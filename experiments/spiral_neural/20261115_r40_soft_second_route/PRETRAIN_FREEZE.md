# R40 — Pre-training freeze (2026-11-15; independent SLE neural workstream)

**State at this commit: NO R40 NEURAL TRAINING YET.** This is the original preregistration, not a success claim. Parent: R39 Draft PR #89, head `8d1165d58ecfd4de8d184420ba375a936d82ce7f`. No Pro UR1 manifest authorization or change.

## Single factor and controls

R38: manually force b-only access for the *second* 6-bit numeric answer word. R39: remove the mask entirely. R40: replace that mask with **one trainable scalar** `alpha=sigmoid(route_logit)`, initialized `route_logit=-6` (alpha approximately 0.002472623). During second numeric word of r2, preserve b completely and multiply a/c/d input one-hot features by alpha. No changes to other answer positions, encoder weight tying, teacher events, optimizer, or numerically legal wire protocol. Scalar is learned by normal Adam; no LLM computes student answers.

Legal profile `SLE-AE1-n5-v1`, integers 0..29. Raw bit input `01+010+bin3(r)+0+word(a)+word(b)+word(c)+word(d)+111100`, 39 bits, each word `bin5(v)+0`. Target r consecutive 6-bit words plus external STOP class S (not a wire bit).

Model: R38/R39 10,457 trainable parameters; R40 **10,458** (+1). Base dense forward 10,920 MAC per target. On secondword prefixes, at most 36 additional scalar multiplications per target (3 non-b × 12 one-hot features), not an exactly equal-MAC/parameter control. Upper bound training forward `6,941,721,600` MAC, of which base `6,918,912,000`; backward computational cost not measured. Normal elementwise control overhead is excluded.

## Frozen teacher and budgets

Exactly the R38/R39 136 ordered events, 1,408 target prefixes per epoch, 150 epochs, 3,300 Adam updates/student, batch64, lr 0.003, clip norm1.0; three seeds 101, 202, 303; base initialization `seed+12000`; shuffle `default_rng(seed+201000+epoch)`. Total **9,900 updates**, **633,600 target presentations**. No early stopping, additional seeds, or test-driven retraining. Pre-existing R38/R39 checkpoints are frozen baseline comparisons.

## Precommitted split and six-part joint gate

Training: the old R38 136-event curriculum. Validation: **none for model selection**; static checks only. Familiar test per seed: 16 high-b26/27, 16 known-b18/19, 16 displaced-b20..23, and 80 mixed-arity historical retention contexts (=128 ×3). They were previously inspected and are **not blind**. Fresh role test per seed: **16 previously untested question strings**, b24/25 as second data word, never trained in this role; Cartesian product a∈{14,15,20,21}, b∈{24,25}, (c,d)∈{(2,4),(3,6)}, r=2. Teacher labels are deterministic bit encoding; numeric values were not globally blinded.

All six required: high-b correct second word ≥40/48; known-b ≥44/48; displaced-b ≥36/48; historical mixed-arity exact ≥216/240; new b24/25 correct second word ≥12/48; high-b **autonomous full answer exact ≥6/48**. Otherwise FAIL. Report independently firstword, forced/gold-prefix STOP, actual autonomous full answers and per-seed outputs. Existing R38 and R39 new b24/25 inference is allowed (read-only) for comparison; no baseline retraining.

## Exact local frozen artifacts and provenance

The pretraining copy, created and statically checked using the R39 complete companion ZIP, has SHA256:
- `r40_soft_route.py`: `314ead28bdc43f00e144748410e79457bd436437c41b6104ba7ce763edebb411`
- `r40_manifest.jsonl` (128 previously examined contexts + 16 fresh): `cf9726b08f1f1592fa60327baea2e63bc7b925d11329fcf27e5ce03240ed6010`
- `r40_prereg.json`: `811dbac23dfbbdb1d87f7ecb9b3b5ea6fe32ead51fe3419b04ac15ca0a378445`
- R38 source `r38_b_curriculum.py`: `8704b05a8b1ec152fa9e3184e0248c6529ce975660277ba75c7375602d0a122e`
- R39 source `r39_second_route.py`: `fc50668670a82add52a2b5ba23538f2d8780b815dba8750e89954134d96607f9`
- fixed R39 manifest: `781e351ead001a74a30f75be3f92347bbe70530149a4fec126b23b35c90c35b9`.

**Actual preflight**: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python r40_soft_route.py gate`: PASS — verifies 144 legal raw-bit test Q, no fresh Q train/prior-test overlap in the stored historical manifests, 10,458 parameters, unchanged non-secondword initial logits, true scalar gradient flow. This is only a static preflight and a backward-gradient smoke check, **not the formal 9,900-update training**.

U: author's standalone raw-01 learning priorities. F: R38/R39 source/checkpoints and Git P030–P035, Pro #12. T: pretraining fixture/shape/hash checks only. A: a learnable gate could preserve learned b-role behavior and permit some generalization; unproven. NVIDIA 0 calls (no live authorized endpoint), local Codex 0, Gemini 0.

**Next owner:** independent NN worker, only after this freeze is committed; train precisely once, retain all bad results, publish companion source/checkpoints/raw 01 and independent NumPy verification, no automatic merges.