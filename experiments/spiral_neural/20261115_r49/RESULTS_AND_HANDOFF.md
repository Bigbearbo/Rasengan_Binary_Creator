# R49 — frozen-checkpoint b-only inference rescue: actual neural diagnostic

**2026-11-15. Pre-inference freeze:** commit `340d8b3f95fa2863e8a2c2ba83132482add308ee`, see `FROZEN_PREINFERENCE.md`. **Preregistered joint gate FAIL.** New inference is real; no new training or optimizer updates. Distinct from Pro UR1 and Codex whole-region period/three-attempt lane.

## Single variable
R45/R46/R47/R48 historical trained checkpoints (3 seeds 101/202/303 per arm; 12 immutable 10,457-param models) originally allowed respectively a+b+c+d, a+b, b+c, b+d for r=2 answer cursors 6..11. R49 **changes only the inference mask at those positions to b-only**; all trained weights and all other answer positions stay identical. Contrasts use original historical free-generation output records, without retraining.

Profile `SLE-AE1-n5-v1` values 0..29; literal 39-bit input `01+010+bin3(r)+0+4*(bin5(value)+0)+111100`, output six-bit words and external `S` STOP (**not** SLE punctuation). Train source remains original R44 136 teaching events; R49 does **0 updates, 0 new training targets, 0 training MAC**. Historical 80Q × 3 seeds × 4 arms (retention); 96Q ×3 ×4 (exposed, **not blind**): b18/19=16, b20..23=32, b24/25=16, b26/27=16, b28/29=16.

## Observed three-seed totals (actual free NN generations)

| Frozen training arm | Second word baseline/288 | Inference b-only /288 | Change | Historic full baseline→b-only /240 | Previously-correct historic LOST | Test full exact baseline→b-only /288 |
|---|---:|---:|---:|---:|---:|---:|
| R45 all | 3 | 88 | +85 | 209→158 | 51 | 0→0 |
| R46 a+b | 130 | 240 | +110 | 206→218 | 5 | 0→0 |
| R47 b+c | 96 | 208 | +112 | 234→210 | 24 | 0→0 |
| R48 b+d | 84 | 200 | +116 | 221→203 | 18 | 1→1 |

All four arms improved in **all 3/3 seeds**. Historical full-answer counts can increase while some previously correct answers are lost; report both. R46 second word increases +110 and historic full improves +12, but test full remains 0. R48 retains just the already-existing single full test success; no new complete success.

**Frozen gate** required ≥2 arms each with +24/288 secondwords, ≥2/3 seeds improving, historical previously-correct loss ≤12/240, and ≥1/288 autonomous full exact test answers including STOP. All arms pass secondword, but R45 loss51, R47 loss24, R48 loss18; R46 loss5 but full exact=0. **Zero qualifying arms, overall FAIL.** Gold-prefix r2 bit accuracies (diagnostic, not free generation): R45 1015→1416, R46 1514→1672, R47 1496→1640, R48 1416→1624, each /1728.

## Verification and resources
2,112 NEW full native01 free generations from 12 checkpoints×176 inputs; PyTorch free replay **2112/2112 PASS**; standalone NumPy forward/free replay **2112/2112 PASS**. 5,472 paired logits outside r2 positions unchanged **exactly**. 57,830 actual new forward calls (33,062 free +24,768 paired); 631,503,600 theoretical forward dense MAC at 10,920/call (excluding historical reference and additional replay). No backwards pass, no Adam. The 272-file companion archive was independently re-extracted, verified against `R49_SHA256SUMS` and the `verify_r49_package.py` integrity/scores verifier; clean static check passed for 12 weights, 176 legal prompts and 10,457 parameters. No new students.

## Full companion artifact and provenance
Artifact (NOT in Git): `sle_ae1_r49_frozen_source_rescue_20261115.zip`, SHA256 `bfe14eea874ec060ccfe08fddabda7f47a69847c00a04034adf70c03eea821d7`; 272 entries including 12 checkpoint weights, all raw bits and outputs, frozen trainer/source, NumPy checker, 2112 new answers, failures, `R49_SHA256SUMS`. Original R48 archive SHA256 `abdb7cf4d616e635d9a16946b81d149d98906aa0cedfe28b779190ad4b49ec17`. ZIP furnished alongside this scheduled experiment, not silently pushed to the public repo. The Git-only report is NOT full neural replay.

Source lock SHA256: `r49_frozen_rescue.py` `7e63301a1d6f34f91b575c4993d6c1de479fda6cdd79d19082a38e14ba21969a`; `r49_prereg.json` `413bc7fc82a0c5a5b49fb6fb34973803fda1674e60b0f8d41534ef4b94a22586`; `r49_manifest.jsonl` `5539a78575e688e9032b696e55259b157f16f7ff5be9daaf94bff3e97e7ac820`; `r49_outputs/raw_results.jsonl` `6e36dc0c47f8a294c4aa1e2d2605e7013478b9a3a7c7cf35e00a6d1017bfd14e`.

Minimal verifier (from archive root): `python verify_r49_package.py`; then `python r49_frozen_rescue.py static`; `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python r49_frozen_rescue.py replay`; same command ending `numpy`. Distinguish SHA-only static validation from actual PyTorch/NumPy neural execution.

**Failure example** R46 seed101 Q `010100100001100110000011000011100111100`: original `00000010000010000000000000000000`, b-only `00000011000010000000000000000000`, true `001100110000S`; secondword correction does not fix firstword/STOP.

**Interpretation boundary:** Free inference performance changes without weight modification; therefore prior failures are NOT fully explained by irreversible training-time loss of every b feature. This does not show that the NN learned to route conditionally, or to solve full math/period/STOP; no new blind generalization. Training-time interference and inference-time competition may coexist. External b-only mask itself is a strong human structural prior.

**U/F/T/A** U user independent raw01 NN remit, F immutable PR #5/P030–P035, Pro #12, Codex #90, R44–48, T the above 2112 actual inference/replay with frozen hashes, A future learned context-dependent selector with separately necessary full output & valid punctuation gate. NVIDIA 0 actual calls (no authorized working live endpoint); local Codex 0; Gemini 0. No VM/parser edits, private chats, credentials, branch merges or changes to others' active work.

**Next owner** independent NN researcher: establish a truly unexposed legal heldout and compare matched-budget learned conditional source selection against fixed/fully open routing, with firstword, secondword, complete answer and autonomous STOP separated; obtain Codex current whole-region period implementation separately rather than treating this AE1 `S` as its on-wire period.
