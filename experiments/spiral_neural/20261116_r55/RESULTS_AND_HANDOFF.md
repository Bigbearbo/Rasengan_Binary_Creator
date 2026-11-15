# R55 — value-conditioned source gates: actual trained students, negative complete-answer result

**Owner/workstream:** independent native-01 SLE small-NN researcher. **Scope:** only `experiments/spiral_neural/20261116_r55/`. Parent [R54 PR #105](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/105), frozen head `fcdd81c85a644f6a28aeb28253cf5afd9c6e0ef3`. This stacked Draft is not merged. Do not modify Pro UR1, Codex P030–P035, parser or Hamster VM.

## Pre-training record, including correction

The unique causal treatment is eight **value-conditioned slopes** on the eight R52 cursor/source gate intercepts. Keep all 10,457 backbone weights and eight R52 gate intercept buffer scalars frozen; train only eight new slopes. Gate equation: `sigmoid(frozen_R52_intercept + learned_slope*(operand_value-14.5)/14.5)`; zero slopes exactly reproduce the frozen R52 function before new updates. No student input-source oracle during free generation. It is *not* a general learned router.

- Original public prereg commit **before any R55 neural forward:** `146a59b0ce0f1ba2ada6b197a33dfcab4a0b4f26`.
- **Documented pretraining abort/correction:** original runner asserted 10,473 parameter tensors but eight intercepts are registered buffers. Before any forward/update, corrected count to **10,465 model parameters** (10,457 frozen +8 trainable) plus eight frozen buffer scalars = 10,473 saved scalars. Public erratum commit `39627718447751706ad37257a842155c0dfeb71c`. No change to gate equation, labels, split, seeds, updates or thresholds.
- Corrected frozen code SHA256 `dca08e4c04620ca9110fa16a992c85c5c5ffed3d3310edbf6d39b60a354d12a5`, prereg SHA256 `40916f124696652675813b084b8bc0fb65e6549b676d4718708b901d77b07b96`, manifest SHA256 `fd480fd1f8d1e88309fa7476b2be7721de7aca61f4c96b8ce6ac0870ae0f7fd8`.
- R54 immutable parent ZIP source SHA256 `9aec51c9f7b2e4e48d33ea02af37fd26c5a2438a220bd00aa650058be110fc72`. Prior 325 file checksums PASS.

## Legitimate native-01 data and resources

Profile `SLE-AE1-n5-v1`: 39-bit raw binary question (`01|010|r:3|0|(a:5|0)...(d:5|0)|111100`), `r∈{1,2}`, legal operands 0..29; output six-bit SLE words (a, optionally b) and external STOP class `S`. Original **136 training events** (1,272 non-STOP targets), no new labels or changed corpus. Deterministic fresh *exact raw-bit question strings*, not globally unseen numeric values: 32 validation +64 test questions (16/32 each r1/r2), plus 80 previously exposed historic retention questions. Training samples do not include validation/test Q. Seeds **101/202/303**; Adam lr .04, batch64, **500 updates per seed =1,500 actual updates**, 96,000 target presentations. Theoretical base train-forward dense MAC **1,048,320,000**, excluding gates/backward/optimizer; evaluation **8,838 real neural forwards**, base proxy 96,510,960 MAC. Torch CPU 2.10.0, no GPU.

### All three seed scores, full autonomously generated answer **including STOP**

| Dataset | Frozen R52 | Trained R55 | newly right / previously right now wrong |
| --- | ---: | ---: | ---: |
| Validation 32×3 | 30/96 | 32/96 | 2 / 0 |
| **Test 64×3** | **45/192** | **44/192** | **1 / 2** |
| Historical retention 80×3 | 220/240 | 219/240 | 0 / 1 |
| All 176×3 | 295/528 | 295/528 | 3 / 3 |

Test first word 63/192→63/192; r2 second word 48/96→51/96. Test full by seed: 101 **16→16/64**, 202 **12→10/64**, 303 **17→18/64**. All three seed learned slope |max| values: **2.027**, **3.514**, **1.417**.

**Preregistered ALL-gate FAIL: 5/6 subgates PASS.** Primary test full must be at least R52+8/192, i.e. 53/192; actual R55 **44/192**. Remaining gates for firstword, secondword, retention, active slopes, and dual replay PASS. No seed/epoch/threshold changes after test inspection.

## Original 01 negative examples

- Test seed202 Q `010100010110100110010011110011110111100`, expected / R52 `110100S`, R55 `000100S`.
- Test seed202 Q `010100010101010100110100100111010111100`, expected / R52 `101010S`, R55 `101000S`.
- Retention seed101 Q `010100100000010101110000000000000111100`, expected / R52 `000010101110S`, R55 `000010111110S`.
- A rescued test seed303 Q `010100100111010001100011000010010111100`, expected / R55 `111010001100S`, R52 `101010001100S`.

## Actual independent verifications and source availability

528 NEW R55 raw complete native01/STOP generations, SHA256 `7f6199d17ae9ad2a8effc5e02682ab7b400584c383e051cca23a653aab4107ce`; results SHA256 `c0695b6a208d9ec1129a2260589d4dbfee58ed3f9e0ba1faa4455a2800573fd6`. Real PyTorch generation replay **528/528**, independent NumPy float32 **528/528**, max checked logits diff `3.814697265625e-06` (<1e-5). Stdlib independent raw/result audit PASS. Clean-room re-extraction of new ZIP: **339/339 SHA256** plus prior R54 **325/325** PASS; dual replays and raw audit PASS again. Full portable ZIP including three checkpoints, code, data, raw outputs, archived lineage and hash inventory is attached to the research run (not stored in Git). ZIP SHA256 **`f106b68b59016a0a81e7d79cd982686784d3368a6c75b9d93121f8cf410264b6`**; entrypoint `r54_workspace/R55_PORTABLE_README.md`. The public stdlib verifier `verify_r55_public_git.py` is committed here, but **Git alone does not contain full weights**; do not pretend it is a full neural replay.

[更新] Eight value-conditioned gate slopes demonstrably learned nonzero values but did **not** improve full answer correctness on new exact-Q test (45→44/192). [取代] Such minimal gates may be enough to resolve the R52 irrelevant-input interference. [原因] Predeclared primary gate failed, with losses after full answer+STOP generation. [狀態] This panel's measured result high confidence, general router limitations beyond this setup low confidence.

Important experimental limitation: frozen R52 versus R55 is **not matched for extra optimizer work**. R55 got 500 extra updates per seed, R52 zero. The counterfactual is therefore added slopes+further learning, *not* solely gating architecture at equal total budget. It also tests new *combinations of known numeric values*, not unseen number range, new math op, or a new valid SLE profile. SLE-versus-binary superiority and true primary-school math learning are not established.

**Next owner:** independent SLE neural lane, preregister an **equal-budget static-gate R52 continuation** (same 500 updates, prefix stream, seeds and holdout, but train intercepts instead of slopes), explicitly mark the reused test set as exposed by R55, or design a truly sealed new exact-Q set before evaluating either arm. No recourse to Pro UR1 target-order trial or Codex NN/VM. **No auto-merge.**

Provenance U=author study boundary; F=prior Git and checkpoint source; T=actual R55 model train, raw generation and clean replays; A=interpretation/counterfactual candidate. NVIDIA **0 calls** (no callable authorized entry or keys), local Codex **0**, Gemini **0**. No private data or key published.
