# R65 results — detached frame-head gradient, 3 genuine new small-NN trainings

**Status: FAIL 7/8 preregistered gates** (one framing-acceptance gate failed), while the main math-gradient diagnostic passed. Research independent of VM, parser, Pro UR1, Codex P030–P035. Preregistered before the first R65 NN forward in commit `315f96fce13868e05c9f1553ca0aa1f078b11f38`. Source runner SHA256 `7a37d0a7276aa016d89ecc2e73cfb0c69bbab13e95651ade09df357a39b8183c`; frozen manifest SHA256 `2201dc52d2c9b28bbf05439e85fb8b5405a963e4dc10c70468c748eef0f14ea2`.

## One variable and actual training

R64 #115 jointly trained raw39-bit shared tanh64 Echo answer and framing heads, improving three-seed full math+STOP test 149→165/192 relative to math-only. R65 reran **only three new detached students** with one architecture change: frame branch input `h.detach()` instead of `h`. Keep R64 initializer, 1,472 synthetic cases, exact R64 train/val/test split, seeds 101/202/303, 600 Adam updates per seed (LR 0.006, batch64, global norm clip1), BCE framing + masked parallel 13-position Echo cross-entropy; 5,160 parameters/student, native 39 bits and legal `SLE-AE1-n5-v1`. 1,800 actual updates, 115,200 sample presentations, forward-only theoretical 582,451,200 dense MAC. Source fixed by SHA before training; no rerun or budget increase after test.

R64 comparators were frozen unchanged: no R64 students retrained. Malformed-root cases 00/11 train validity only, withheld 10 test validity only; no invalid case used as mathematics. STOP is a host class, not SLE word. All heldout questions are **already exposed** from R64; this is a paired mechanism diagnostic, not new blind generalization.

| Three seeds, legal test Q | R64 math-only | R65 detached auxiliary (new training) | R64 joint sharing |
|---|---:|---:|---:|
| Complete Echo answer + STOP | 149/192 | **149/192** | **165/192** |
| Legal 01 frame accepted | 104/192 | 137/192 | 192/192 |
| Unseen malformed 10 rejected | 95/192 | 188/192 | 192/192 |
| All malformed roots rejected | 278/576 | 543/576 | 576/576 |
| STOP position correct | 192/192 | 192/192 | 192/192 |

Per-seed math test: seed101 = 63/63/64, seed202 = 58/58/63, seed303 = 28/28/38 (math-only/detached/joint). Pairwise R65 detached vs R64 joint: 11 rescued, 27 lost, net −16. **All 1,344 R65 detached math predictions are identical to R64 math-only**; shared encoder and math head are exactly identical tensors across all three seeds (maximum absolute difference = 0.0). Detachment did **not** prevent the frame head itself from learning partial root validity.

Seven prereg gates PASS: manifest/hash, paired training budget, gradient-block probe, independent NumPy replay 1,344/1,344, test math >=baseline−12, unseen malformed 10 rejection >=150/192, and R64 joint math advantage >=6/192. One gate FAIL: detached legal 01 acceptance **137/192 < 150/192**. Overall **FAIL**. Training was completed once and not modified post-result.

Original R64 NumPy-independent verifier: 2,688/2,688 PASS. R65 independent NumPy verifier: 1,344/1,344 PASS, max frame-logit difference 2.384185791015625e−6. Clean ZIP extraction and 40 tracked SHA256 content checks PASS, and both verifiers re-ran. Test failures, raw bits, predictions, checkpoints, losses and per-seed audit are preserved.

## Interpretation and provenance

[更新] The R64 math gain on this specific Echo task **depends on allowing the auxiliary frame loss gradient into the shared representation**: detached R65 exactly reproduces the math-only math student. [取代] Training an additional isolated framing head alone could account for the 149→165/192 full-answer increase. [原因] Same schedule/init/data and all 1,344 outputs plus encoder/math weights are identical with detachment. [狀態] High confidence for this controlled experiment; **low confidence** that this is SLE semantic grammar learning or generalizes across codec/width. The common global gradient clip remains a potential mechanism; do not claim a unique causal *neuron feature* without further tests.

U=user independent neural teaching requirement. F=R64 #115, R62 #113, R63 #114, Pro UR1 #12 and Codex P035 #10 (read-only and not re-executed). T=this run trained R65 students with replay and clean audit. A=shared-frame gradient may provide useful supervision or generic auxiliary regularization. No NVIDIA/Codex/Gemini calls (0 each; no authorized local NVIDIA worker available).

## Reproduction and next owner

Complete **public synthetic** source, prereg JSON, 1,472-bit-question manifest, three new R65 NPZ checkpoints, 1,344 raw predictions, all test failures, six frozen R64 NPZs and original R64 NumPy independent verifier are retained in an external conversation ZIP; **ZIP is not hosted on GitHub**, so Git-only replay is not complete. ZIP SHA256 `50a46f5d735ed0791c871dfc4ee789fb926ad3ea8f9096f58dc1ec776e6b0cde`. In the unpacked `r65_work/` folder run `python r65_detached_frame.py static` then `python r65_detached_frame.py verify`; in `r65_work/r64/` run `python verify_r64_public.py .`. To reproduce training rather than audit original, copy the bundle into a clean dir without `r65_outputs/` and run `python r65_detached_frame.py train`.

Next owner: independent SLE NN research. Freeze **one factor** comparing correct frame BCE with balanced, deterministic *shuffled-frame-label* BCE at equal budget to distinguish semantic supervision from generic auxiliary regularization. These holdouts are already exposed, so do not report next controls as blind tests. Do not touch Pro/Codex/VM branches or auto-merge this PR.