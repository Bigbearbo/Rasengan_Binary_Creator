# AE1 R16: 單位元 b16→20 配對神經診斷 (2026-11-14)

**事前正式門檻 FAIL：0/3 平衡混教 Seed 達標。**

## 事前已固定
FROZEN_BEFORE_RUN.md at commit `89784f239fcc1828942d8c14b92f8e9e32b15fac` and six exact raw01 cases in manifest committed first (commit `2bd1891d93cfd15428830f5116e61ddac6bb23ac`), **before R16 neural forward**. Unique intervention: b16→20 toggles only b's bit4, while holding a, r2,c0,d1, SLE-AE1-n5-v1, 9 original checkpoint weights and output rule fixed. a24 paired validation was previously noticed by researcher; a28/29 paired heldout test had not appeared as a training word or R14/R15 complete question. This is an extension of a known diagnostic, not a fully researcher-blind discovery. All 6 questions are legal 39-bit native01 with a6+b6+external STOP response.

R14 136 course presentations /112 unique, 3 seeds (101,202,303) × 3 arms (control16,control8,balanced8_16). **0 new optimizer updates, 0 training targets**, 10,457 parameters and 10,920 forward-only dense MAC per model prefix. R14 source PR #63 head `b197299ec7b48f0a07118582be981bb5aaeb3318`. R15 PR #64 contains earlier b20 errors and informed this diagnostic.

Preregistered PASS requires ≥2/3 balanced seeds to exhibit both a28/29 first-word invariance between b configs (2/2), at least one pair with both full strings exact, and ≥1 b20 second-word exact. Do not replace this with post-hoc metrics.

## Results

| Three seeds combined | Validation a24 exact /6 | Heldout a28/29 exact /12 | Heldout first-word exact /12 | Heldout second-word exact /12 | Heldout first-word unchanged across b /6 |
|---|---:|---:|---:|---:|---:|
| control16 | 0 | 0 | 0 | 0 | 4 |
| control8 | 0 | 0 | 0 | 1 | 5 |
| balanced8_16 | **2** | **0** | **5** | **0** | **3** |

Balanced first-word invariance: seed101=1/2, seed202=1/2, seed303=1/2. **A one-bit modification of the SECOND data word changed the FIRST answer word in 3/6 paired heldout comparisons**, although its semantic value a was fixed. This is evidence of conditional cross-word interference, **not** proof of its neural cause. Some wrong first words also remain invariant, so invariance alone is not accuracy.

Concrete mixed seed202 a28: b16 expected `111000100000S`, generated `111010000100S`; after only b→20 expected `111000101000S`, generated `111000001000S`. The first answer word flips from wrong to right under the irrelevant-to-a b change. Mixed seed101 a28 has the correct first word both times but wrong second words `100010` and `101010` instead of `100000` and `101000`.

T actual: **54 complete neural 01 generations, 702 forward passes, 7,665,840 inference dense MAC**, 54/54 STOP locations correct, zero training. Independent NumPy replay of nine original F32 checkpoints recovered **54/54 full strings and 702 forward positions**; a second public replay script checked 54/54. Clean ZIP extraction passed all file SHA256 and both replay scripts. Inference replay is not optimizer re-execution.

## Evidence / provenance / next owner
- Full ZIP: `sle_ae1_b4_singlebit_r16_20261114.zip`, SHA256 `a7c941e60e8ae76cbbf362ac67bf75cf949811ae385b7dc8ac9fbb42df22ecc9` (separately provided). Git alone lacks the nine checkpoints and 54 raw outputs; `PUBLIC_REPLAY.py` requires the companion ZIP.
- R16 manifest SHA256 `ad63d5ba47b92ca2790a44bec42bf3e604a39fef0ead0dd811acb657ebd65c27`; pinned full runner SHA256 `a2f0c0ee81a56d487314e41fbd069c05b9bc47609416d2ef87c7c04c6390ea73`; raw generated SHA256 `bcf37171466a16e39414bf271dcfcffd4c361cfd75794ee159539a7040434fe5`; complete result JSON SHA256 `4740579472d19e44bca99c137e0e365f23856fb22d3f83eb0aa6caaa15821d60`.
- Test commands in companion extracted directory: `python run_r16.py gate`, `python run_r16.py infer`, `python verify_numpy_r16.py`, `python PUBLIC_REPLAY.py`. Actual gate PASS; inference executed; NumPy PASS 54/54; all SHA PASS.
- U: user independent raw01 neural learning objective. F: R14 #63 and R15 #64 immutable original files and weights. T: this round's true PyTorch inference + independent replay. A: b20 may cause cross-field dependence; representation vs output route not yet isolated.
- Next owner: independent SLE NN reviewer. Analyze correct-prefix first-word logit sensitivity and second-word bit errors on these frozen models; only start new curriculum after freezing a genuinely new, broader a/b domain. No Pro UR1 manifest approval. NVIDIA actual 0 calls (no authorized configured endpoint), local Codex actual 0, Gemini actual 0. No LLM oracle or automatic merge.
