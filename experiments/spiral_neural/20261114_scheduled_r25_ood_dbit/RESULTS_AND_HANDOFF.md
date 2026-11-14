# R25 — New d-bit OOD context; real 01 small NN test (2026-11-14)

This is a **fixed-checkpoint** comparison, not additional training, a VM/parser edit, or proof of universal copying.

**Preregistration precedes neural forwards:** raw 96 legal SLE-AE1-n5-v1 39-bit Q frozen in Git commit `5c0587f0d76d8c219c4b013a6508e98fb79facf8`; source, splits, weights, 3 seeds, MAC budget, and the joint gate frozen in Git commit `d1553157800c7db4c04cfdbf2c93661b5bac6765`. Manifest SHA256 `0465f40a29cd9a9c9069cad739e2dbb2018d8fce29fedc72328b290d7ffbbefb`. Public frozen runner SHA256 `e2c02b935c45b3a8f5b7fd1c73ad611e663d61d630ae8dfa9f06352aaa4f43f1` is included with full checkpoint ZIP.

Unique new within-pair change: **d=4 vs 5**, one raw input bit, while c=0/2 are nuisance strata; R20 and R23 are historical six true checkpoint states (3 seeds each, 10457 params/model), all weights immutable. No student was told its target during 01 greedy inference. Calibration 32 Q (a0,1;b8..11), test 64 Q (a2..5;b13..16), and 0 new optimizer updates. All d4/5 Q are new vs reviewed R20-R24; same 01 AE1 profile and label rule. Full train/test distinct by a, but not a full double-blind study.

## Real test (c=2, teacher-position STOP & complete free answers)

| seed | d | R20→R23 true STOP /16 | R20→R23 complete /16 | First word each arm | STOP margin gain | gate |
|---|---|---|---|---|---:|---|
| 101 | 4 | 8→14 | 8→14 | 16/16 | +2.650 | PASS |
| 101 | 5 | 8→13 | 8→13 | 16/16 | +2.314 | PASS |
| 202 | 4 | 6→11 | 6→11 | 16/16 | +2.266 | PASS |
| 202 | 5 | 4→9 | 4→9 | 16/16 | +2.211 | PASS |
| 303 | 4 | 8→11 | 8→11 | 16/16 | +1.670 | PASS |
| 303 | 5 | 6→7 | 6→7 | 16/16 | +1.772 | PASS |

Aggregate c2: **STOP and complete 40/96→65/96**. c0 STOP **87/96→88/96**. Joint preregistered gate **PASS 3/3** (both d values must exceed +0.75 STOP mean margin, with c2 first-word loss <=1/16, c0 STOP loss <=2/16, first-word c-invariance loss <=1/16).

**Important negative boundary:** c2 first words are **96/96 already correct in BOTH groups**, so the first-word nonregression gate is at ceiling. It does **not** refute the earlier R24 seed101 first-word regression in harder a4..7 cases. c2 STOP still fails 31/96 after lessons. A change of only d4→d5 caused seven R23 correct STOP calls to become wrong (0 reverse repairs) among 48 c2 test pairs, and nine changed full responses. This is residual dependence on irrelevant d, not universal invariance. For example seed202 c2 d5 a3 b15 should answer `000110S`, but instead answers `0001101S`.

**Actual execution:** 576 real complete greedy responses, 5643 greedy forwards plus 576 STOP-position forwards = **6219 new neural forwards**, **67,911,480 theoretical dense MAC**, 0 new training, 0 optimizer replay. Independent NumPy recomputed **576/576 complete outputs plus STOP logits**, largest abs logit discrepancy **2.86e-6**. Raw result SHA256 `9416ce8874e63c6500f27af1fe1d171313dbad0596bd278657f8cd218b69b923`; result summary SHA256 `5c96d66f6590e6564b64264f904582884280ab410b0e4631dceba7318735a705`.

## Reproduce and attribution

Full companion archive `sle_ae1_r25_ood_dbit_20261114.zip` SHA256 `e842869bdd900fab860559dfc20c5f4e2cd852b99b30079d9da784ce43f6bb29` includes all six true original weights, frozen source, 96 raw Q, 576 raw outputs, prereg, original PyTorch runner, NumPy verifier, and the failure log. Run in extracted root:

```sh
python r25_probe.py preflight --root . --work .
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python r25_probe.py replay --root . --work .
python r25_public_verify.py .
```

The Git directory contains frozen raw questions, protocol, result receipt, and standalone verification entry, but not large checkpoint binaries; **Git-only replay is insufficient**. Original sources/weights, checksums and the full 576 outputs are in companion archive, not fabricated within Git.

Provenance: **U** user's small NN 01 learning goals; **F** P030–P035, Pro UR1 #12, Codex #61, prior R20/R23/R24 real source and states; **T** this newly executed fixed-weight probe and independent NumPy replay; **A** STOP tolerance transfer for this finite OOD d domain only. No mathematical teaching or model growth claim. NVIDIA skipped (no authorized live worker endpoint); actual NVIDIA/Codex/Gemini calls all 0. No merge or edits outside isolated NN branch.

**Next owner:** independent small-NN stream. Freeze a harder high-a first-word domain, with STOP and first-word joint gate and non-ceiling controls; do not reuse R25 test as fresh evidence. A separate equal-budget ordinary-binary control is required before any SLE-advantage claim.
