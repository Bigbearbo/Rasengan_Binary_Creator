# R58 actual results — frozen legal c-MSB counterfactual (2026-11-16)

**Actual outcome: preregistered joint FAIL (3/6 PASS).** This is a new inference-only causal experiment, not a new student or a retraining of P030–P035. Initial prereg committed **before** any R58 neural forward: `345c83377d9a349fcb64d108151efec7f2502148`; remote file was fetched and receipt verified prior to evaluation.

## Single treatment and validity
- Raw 39-bit legal `SLE-AE1-n5-v1`, r1/r2, values 0..29. Change **only c numeric MSB bit** (third data word; raw index 21), `c=0..13` to `c+16=16..29`. Keep a,b,d,r, response truth and trained weights fixed; every pair changes exactly **one** raw bit.
- Manifest: 48 matched pairs / 96 new unique raw Q not among 1,836 archived distinct raw Q; validation 16 pairs, test 32 pairs, evenly balanced by r1/r2 and b-low(0..5)/high(24..29). Generator seed 58016. Existing 136-event/1,272-prefix-target lessons unchanged; no new training, 0 optimizer updates. Seeds 101,202,303; fixed checkpoint arms R52/R55/R56, 10,465 parameters each. R55 additional 8 frozen scalars; prior R55/R56 equal 500-update comparison.
- **Not** a new numerical-value or grammar blind test: the 0..29 domain and copy operator were previously taught/tested.
- Verified full pre-inference manifest SHA256 `fba1fcfdbe2f8a77a1630ad7d1e49d73a7b4010459efa4ad08a38bc6988b8cc8`, local freeze JSON `fa8039028cc46794559551c02ee220567c61f1fa0e9efbc0b8b836d297ed5796`, runner `9c20e32fc48c3719a32baa096c978a66b003a60531f4277d785f5afeca3b6e30`.
- Parent PR #108 exact head `5f816bee0e84b8747752c6ecf2a19e6fa2b4373b`, previous source archive SHA256 `61a863a0a209a43a15366e62db3b34494d52bd273f191aaddeef304984b82fea`.

## Test results: 32 pairs ×3 seeds =96 seed-pairs /192 complete responses per model

| Test metric | R52 | R55 (value conditional) | R56 (equal-budget fixed) |
|---|---:|---:|---:|
| Whole-answer exact including STOP | 40/192 | **40/192** | 38/192 |
| First answer word changed when only c-MSB changed | 37/96 | **34/96** | 36/96 |
| Whole-answer correctness changed | 18/96 | **16/96** | 16/96 |
| Both sides entirely correct | 11/96 | **12/96** | 11/96 |
| Correct with lower c, wrong with higher c | 18/96 | **16/96** | 16/96 |
| Wrong with lower c, correct with higher c | 0/96 | 0/96 | 0/96 |
| Validation whole exact (96 responses/model) | 27/96 | 29/96 | 28/96 |

R55 vs R56: two fewer firstword flips, identical exactness flips, one extra both-correct pair. All **three preregistered superiority thresholds failed** (need 8 fewer, 8 fewer, 4 more). Legality, R55 total not >4 worse than R52, and double replay passed. Joint **3/6 FAIL**. No p-values or model-wide claim; each seed reuses same deterministic paired corpus.

Specific same-target failure (also in source results): seed101, r1, a4 b0 c12 d0, expected `001000S`, all arms output `001000S`. With **only c12→c28**, expected is unchanged but all output `000000S`. Q low `010100010001000000000011000000000111100`; high `010100010001000000000111000000000111100`.

## Executed checks
On the complete portable archive, executed:
```sh
python r58_cmsb_frozen_probe.py freeze   # local static only, then freeze pushed and checked
python r58_cmsb_frozen_probe.py eval
python r58_cmsb_frozen_probe.py torch
python r58_cmsb_frozen_probe.py numpy
python verify_r58_public.py
```
(Actual commands used OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1, MKL_NUM_THREADS=1 for the neural commands.) **864** new complete native01+STOP responses, **9,066** actual neural forward calls, **99,000,720 theoretical dense inference MAC**, **0** new training updates. Exact PyTorch generation replay 864/864; independent NumPy generation replay 864/864; sampled logits max abs error `1.9073486328125e-06`. Public stdlib static/raw verifier PASS. Initial *new verifier-only* assertion guessed the termination label `length`; actual outputs are 852 `stop` and 12 `cap`. The verifier was corrected before packaging, with models, inputs and raw predictions untouched; this failed diagnostic is explicitly retained in this report.

## Evidence artifact and boundaries
Complete portable source/checkpoints/new model generation, negative examples, frozen JSON manifest and SHA receipts: `sle_ae1_r58_legal_c_msb_cf_20261116.zip` (linked in conversation; not silently uploaded to this public Git repository). ZIP SHA256: `ec3245dacfda55f08c9d0b4ea8c345e4d992ee8821169abbc75944e6dd985b62`. Clean unzipped 388 content-file SHA256 verified. Git retains the prereg, this results record and [public audit source](verify_r58_public.py); the complete experimental neural replay requires the ZIP.

**U** author assigned independent native01 small-NN experiments and source rigor. **F** prior PR #108, R57 artifact and frozen R52/R55/R56 checkpoints. **T** newly tested 864 raw full outputs; 3/6 gate FAIL; independent replay matched all. **A** low-confidence mechanism hypothesis that c-MSB changes distort route-sensitive representation, not established internally. Current evidence does **not** show value-conditioned slopes solving irrelevant-input invariance.

**NVIDIA:** skipped; authorized local OpenRouter callable worker/key unavailable in this runtime, 0 actual calls. **Codex:** no local runner, 0 actual calls. **Gemini:** 0 actual calls. Never use review models as the student oracle. **No Pro/Codex/VM/parser edits and no auto-merge.**

**Next owner:** independent native01 NN researcher. Deprioritize repeating the same exposed 0..29 nuisance test. Reserve truly new operand-role/numeric test domain or match ordinary binary input/output under a fixed comparable compute budget, including complete answer, STOP, and retained skill.
