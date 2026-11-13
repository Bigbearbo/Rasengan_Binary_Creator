# R13 results — actual SLE 01 neural training (2026-11-14)

Owner: independent scheduled NN researcher, **not Codex, NVIDIA, Gemini or Pro**. Scope: independent AE1 native raw-01 SLE small-NN learning experiment, not Hamster VM or dictionary/parser. This file is committed **after** the pre-NN Git frozen protocol `26aa353bb2d14415767a0382c7e7476e6f778b6b` and pre-NN arithmetic-only correction `915b1743145e8b8f7a640fbea773a8d8dfd26167`.

## New finding (T)

The old PR #55 first-answer curriculum has **zero** positive bit8 target exposure (16 positive bit16 first-answer cases). This is directly checkable from the immutable original 120 presentations plus 16 injected lessons. PR #59 showed that the target word embedding senses changed input bit8 while next-bit readout did not consistently change; R13 tests whether this first-answer target-exposure gap materially affects compositional generalization.

One curricular factor: for exactly 16 injected r2 questions, swap first answer values `a=16..19` (prior control) to `a=8..11` (new treatment), same low bits and b0..3, c0,d1. Reuse three original PR #55 tied checkpoints; train **three new** tied F32 students from matched original initialization/seeds. Both arms preserve 120 parent lessons, 136 presentations, 112 unique, 1408 teacher-prefix targets/epoch, 10,457 trainable parameters, 150 epochs, Adam 0.003, batch64, 3300 optimizer updates/student. All native raw01 `SLE-AE1-n5-v1` 39-bit Q with 13-character answer + STOP; deterministic source codec generates labels, NO LLM oracle.

| seed | frozen control a13/14 /16 | new bit8 treatment a13/14 /16 | new bit8 seen /48 | new bit8 taught /16 | predeclared gate |
| --- | ---: | ---: | ---: | ---: | --- |
| 101 | 0 | 11 | 47 | 16 | PASS |
| 202 | 0 | 7 | 45 | 16 | PASS |
| 303 | 0 | **0** | 44 | 16 | FAIL |
| all | **0/48** | **18/48** | **136/144** | **48/48** | **2/3 PASS** |

Fixed success gate from pre-run commit: >=2 paired seeds get >=4/16 exact primary new-a test, advantage >=4/16 vs control, >=40/48 seen retention, >=12/16 taught8. Here 2/3 passes. Predefined val was a12 (8 cases/seed, treatment 3/8,5/8,0/8, control0/8). Primary a13/14 × b0..3,18,19,22,23; these word values never appeared in either arm's training-input word positions. Researcher has seen adjacent bit8 problems, so **not externally blind**.

The result does **not** establish universal bit copy or an isolated causal neural mechanism. We swap bit16 for bit8 lessons, so the new treatment loses previously taught bit16 set (0/48) and seed303, despite perfect new taught examples, fails all 16 held-out. Seen retention 136/144 vs control 139/144. Stop boundaries all correct; content fails often. This is a curriculum exposure effect in this specific regime with mixed seed response.

## Concrete execution and costs (T)

Pre-NN: `python train_bit8.py gate` PASS (source/manifest hash, SLE legal cases, exact exposure counts, split, count and model gate). Then once `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python train_bit8.py train`: PyTorch CPU three new students, **9900 Adam updates**, 633600 target examples, **6,918,912,000 training forward-only dense MAC**, excludes backward/optimizer. No extra seeds or epochs. Six fixed/new students × 104 case questions = **624 native 01 complete greedy responses**, 7248 actual next-bit NN forwards and **79,148,160 inference dense MAC**, all failed examples retained. External NumPy verifier did not import Torch/student trainer or train; independently reconstructed F32 weight matrices and checked **624/624** complete responses, six weight hashes, 7248 forward count and split metrics. Fresh extraction check: **all 17 included files' SHA256 verified**, `python train_bit8.py gate` PASS, `python verify_numpy_r13.py` 624/624 PASS, exit0.

Full reproducible **companion ZIP** delivered to author, not hosted by Git: `sle_ae1_bit8_exposure_20261114_r13.zip`, ZIP SHA256 **`cfb4d067dd55f21da296d60402d82c72c3d221e59f4741d1936264a4ed621705`**, 18 members incl. SHA256SUMS, original `run.py`, frozen prereg and 104 valid raw Q, original/three new full F32 checkpoints, new runner, all 624 actual raw outputs, negative cases, NumPy verifier, trace+results. The 6 originally frozen checkpoint bytes are in this package. Git-only checkout **cannot independently execute this NN check without companion ZIP**, and is not mislabelled as independently reproduced from Git alone. See `VERIFY_COMPANION.py` here for portable SHA+replay.

Selected reproducible error: seed101 control a13 b0 expected `011010000000S` actual `001010000000S`; seed101 treatment actual `010010000000S`; seed303 treatment actual `000010000000S`.

## Provenance and handoff

U: user's original ongoing independent SLE bit-input/output neural teaching and generalization research. F: PR #55 actual six-source checkpoint experiments, PR #59 bit8 output routing, P030–P035 historical experiments and Pro UR1 #12 separately audited. A: target first-position bit8 exposure might be one limitation; **not** the sole mechanism (seed303 counterexample). T: above exact R13 CPU train/free-replay/NumPy checks. F and T distinguish *this* run from all old reports.

Sources frozen: original control ZIP `53f6e312f30570ef7d458f35b25c17b49eb7b161415bb5d3b165645aeb8f10a0`, original runner `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a`; new runner `8d2fa0224c86a189859e5046e52d10815a33da5989364e11580b9c201cc21c99`, fixed cases `8e9ab96501706fbb6d508955e559ccf8b20c50e41f7a0aaf1175d268bb484ed4`, prereg `df0dd16aab55da09177810f33e935b9546b2e5b31280b222585366c7a73aa82b`; output `raw_results.jsonl` `3bc733d21b405678cd3d73dc3781e04b86070ffc5d7d7dfed9aeabd239fc33f6`; results `361695eac7ad5d344b0184a85cc85e99873b5f8282b07e56bc3a94d5335c60f6`.

NVIDIA `skipped_unavailable` (no available authorized caller); actual calls **0**. Codex **0**, Gemini **0**. No programmatic auto-merge. Next owner: independent small-NN reviewer should design fixed-budget curriculum that teaches **both** bit8 and bit16 across roles and genuinely new reserved values, instead of overfitting these already-observed test pairs. Keep Codex E4/F3 and Pro UR1 separate.
