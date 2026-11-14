# AE1 R14 independent native-01 NN study: balanced bit8/bit16 curriculum (2026-11-14)

**Predeclared gate FAIL: 1/3 seeds, requires 2/3.** All 3 new tied-encoder PyTorch students were actually trained. Researcher owner: independent scheduled SLE NN worker, not Codex, NVIDIA, Pro/UR1 or VM. **Git freeze commit `5282eb0ec998bfdeaf494d313a1b4ee0ee26dfa4` precedes NN training.** Full code+data+9 checkpoint package is a **separate companion ZIP**; Git-only checkout is not a complete reproduction.

## One intervention and cost

Exact SLE-AE1-n5-v1, 39-bit native 01 questions; teacher codec emits deterministic target bits + external STOP, no LLM/teacher oracle at student inference. Keep parent120 lessons, replace 8/16 R13 high8 first-answer injections with matched high16 lessons. Both control and new student courses have 136 presentations, 112 unique Q and 1,408 targets per epoch. In the balanced arm, high8 and high16 each have 8 examples, spanning low suffix 0–3 and balanced second-word b=0–3 exposure. This intervention is curriculum frequency/coverage, NOT proof of any specific neuron mechanism.

New students seeded 101/202/303; 10,457 parameters each, Adam lr0.003 clip1, 150 epochs, batch64, 3,300 updates/student. **Actual new training: 9,900 updates, 633,600 teacher-prefix targets, 6,918,912,000 forward-only dense MAC (backward excluded)**. Six frozen control checkpoints from PR55 (full16) and PR62/R13 (full8) reused without retraining. **New inference: 1,584 complete native 01 free generations (9 checkpoints ×176 questions), 19,562 actual forward passes, 213,617,040 dense MAC**.

Validation a12/20/24 × b0..3,18,19,22,23; held-out test a13/14/15 (bit8), a21/22/23 (bit16), a25/26/27 (combined) × same 8 b anchors; seen baseline 48 and exposed-high diagnostics32. All held-out a values absent from new students' first-answer training; a25..27 absent from any training data word slot. Nearby a values have previously been discussed by researchers: student-heldout, not researcher-blind.

## Results (exact whole greedy answers; pooled 3 seeds)

| Frozen curriculum | New bit8 value /72 | New bit16 value /72 | New bit8+16 value /72 |
| --- | ---: | ---: | ---: |
| PR55 full16 | 0 | 20 | 0 |
| PR62/R13 full8 | 22 | 0 | 0 |
| R14 balanced8+16 | 11 | 22 | **52** |

| Seed | R13 bit8 /24 | Balanced bit8 /24 | Balanced bit16 /24 | Balanced both /24 | Balanced seen /48 | Predeclared gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 101 | 14 | 5 | 12 | 19 | 47 | FAIL: bit8 retention fell too far |
| 202 | 7 | 6 | 1 | 17 | 46 | FAIL: bit16 under 4 |
| 303 | 1 | 0 | 9 | 16 | 44 | PASS |
| **Total** | 22 | 11 | 22 | 52 | 137 | **1/3 FAIL** |

The unexpected combined high-bit 52/72 is a genuine observed result from the trained weights, not the predeclared acceptance gate. Both fixed single-high curriculum controls yield 0/72 on a25..27. Balanced course does **not** demonstrate universal bit copying: bit8-only heldout worsened from 22/72 to 11/72, results vary with seed, and context/position-general behavior is unknown. The a25..27 result is limited compositional evidence; posthoc interest does not retroactively change the failed primary gate.

## Audit and raw evidence

Actual complete outputs `raw_results.jsonl`, cases `cases.jsonl`, nine real checkpoint files, frozen `train_r14.py`, original `run.py` and parent, `prereg.json`, full `RESULTS.md` and failing examples are in companion `sle_ae1_balanced_highbits_20261114_r14.zip`, SHA256 **`ec431291aef5e913690d4f0303d94cd3b5768ace73d86f98902cdddebb5eb0d3`** (422,102 bytes). **22/22 member hashes PASS** after clean extraction. Independent NumPy implementation (no Torch inference, no optimizer) independently recomputed 1,584/1,584 complete outputs and 19,562 forward decisions from all nine checkpoint weight files; static preflight also PASS. This independently verifies *inference*, **not** the exact training trajectory.

Locally executed after clean extraction:
```sh
sha256sum -c SHA256SUMS.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python train_r14.py gate
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_numpy_r14.py
```
All PASS; first NN training preceded by remote prereg SHA and static gate. The public `VERIFY_COMPANION.py` checks the ZIP byte hash, 22 file hashes, static gate and independent NumPy replay when the companion is supplied.

## Provenance and next owner

U: user's independent SLE raw01 NN learning/teaching/generalization mandate. F: [PR55](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/55), [PR62](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/62), original real checkpoints/course. T: three new trained students, new evaluation for six immutable checkpoint controls and three students, independent NumPy replay. A: joint bit8+bit16 exposure may support combined-bit values that individual exposure did not, but its internal mechanism has not been isolated.

No NVIDIA calls (no accessible authorized endpoint in this execution), local Codex calls 0, Gemini 0. No UR1 manifest approval, no branch merge, no teacher model output in student calculations. Next owner: independent NN analysis/review. Freeze genuinely new value-context and r/position holdouts *before* choosing further curriculum; investigate why combined-bit is 52/72 while bit8-alone degrades. Do not retune the now-visible a25..27 test to manufacture generalization.
