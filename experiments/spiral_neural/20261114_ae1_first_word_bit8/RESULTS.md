# AE1 native-01 first-word +8 transfer — actual results (2026-11-14)

**Scientific gate: FAIL.** Preregistered *before* any new forward at commit `b716abc9d7aa977ad6bf1d5b2a79a48ae4d01b01`, stacked on parent PR #51 exact head `5d8c42c98f1b0e0f5edeb073be6232b512e47526`. The full raw-data, F32 checkpoint and runnable evidence is contained in the separately delivered `sle_ae1_first_word_bit8_20261114.zip`, SHA256 `874f5d1139c10ed5e82585fd77b4ca3ea52911e50a3cb99ed4e4c9450a936053`. Git without the companion ZIP is not full standalone checkpoint reproduction. No parent branch modified or merged.

## Single intervention and fixed controls
SLE-AE1-n5-v1, legal 39-bit Q, native 01, r2 output two data words + generated STOP. For each original `a=0..5`, change ONLY the first data word to `a+8=8..13`; b in {18,19,22,23}, c=d=0. The input differs at raw bit index 10; the **correct output differs at output bit index 1** (zero-based). PR40 parent teaching uses first data words only 0..5; PR44/45 added second-word examples without ever showing a8..13 as a data value. The component high bit appears in the previously taught second word, so this is payload-value OOV, not completely unfamiliar information bits. 24 paired comparisons/checkpoint, 48 questions/checkpoint; seeds101/202 × original conjunction/balanced-c frozen checkpoints, each 10,499 F32 parameters. No new train/val fitting or student optimization; scientific test student-heldout but prior researcher has studied this model family.

## Actual authentic neural output
| Checkpoint | Seen first word | OOV first word | Whole answer changes under +8 | Proper STOP |
|---|---:|---:|---:|---:|
| conjunction / seed101 | 24/24 | **0/24** | **0/24** | 48/48 |
| balanced-c / seed101 | 24/24 | **0/24** | **0/24** | 48/48 |
| conjunction / seed202 | 24/24 | **0/24** | **0/24** | 48/48 |
| balanced-c / seed202 | 24/24 | **0/24** | **0/24** | 48/48 |
| **Total** | **96/96** | **0/96** | **0/96** | **192/192** |

**The original and bit-flipped questions elicited exactly identical full output in every one of 96 pairs.** This is direct frozen-model evidence of failure to transfer the first answer's high bit to unseen *values*, even though another word's values contain that high bit. It is not evidence that no small NN can learn an algorithm. Primary prereg gate demanded each balanced-c seed baseline >=20/24, OOV >=18/24, and expected single-bit output flip >=18/24; both seeds FAILED. No after-the-fact seeds, training extensions, or changed data.

Example (conjunction seed101, b18): a0 original reply `000000100100S`; a8 expected `010000100100S`, but model replied **`000000100100S`** unchanged.

## Source integrity, computational cost, and reproducibility
Actual execution: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python probe.py preflight`, then once `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python probe.py run`, then independent `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_numpy.py` and `python audit_pairs.py`.
192 real autoregressive PyTorch answers, 2,496 forward decisions at 10,432 dense MAC/forward = **26,038,272 dense inference MAC**; **0** optimizer updates, 0 training targets. Independent no-Torch NumPy evaluator reloaded all four saved genuine checkpoint tensors and reproduced **192/192 complete answers and 2,496/2,496 steps**; all failure raw bits and complete targets archived in `raw_cases.jsonl`, source state hashes in freeze manifest, per-file SHA256SUMS checked. This does not represent new 192 independent training samples or any result for other models.

**Implementation ERRATUM: crucial.** The frozen `probe.py` report's field `one_expected_output_bit_changed` accidentally compared output index **0** rather than correct index **1**. The frozen prose specified the correct criterion, but the code implementation did not. We discovered this *after* the sole NN forward run; did not alter the preregistered artifacts or rerun. Separate post-run `audit_pairs.py` computes the correct index1 condition and returns **0/24 per model**, independently of the faulty summary metric, because **all complete answers are literally unchanged**. The FAIL outcome is robust to the bug. The archived original summary field must not be cited as correctly implemented bit-position scoring.

## Provenance and next owner
U: user establishes independent native 01 neural curriculum/growth/generalization research. F: PR40/44/45 teaching records + 4 immutable checkpoints and PR51 baseline; original full source ZIP SHA `83e5d85f41bc36f40828f074b27a01e93b1e6a2a2bfb8d3ee3582bf038c5ece1`. T: this 192 real NN outputs, independent NumPy replay and post-hoc erratum audit. A: hypothesis that teaching bit8 in the second answer would transfer to unseen first-word values was **falsified for these checkpoints**.

Next responsible owner: independent neural reviewer / Codex read-only replay, then a *separate* preregistered **equal-budget first-position high-bit teaching** experiment, with newly unviewed values reserved for real test; do not retrain on the just-exposed a8..13 panel. NVIDIA / local Codex / Gemini: 0 actual calls; no authorized live NVIDIA reviewer endpoint or private credentials used. No LLM/student-answer oracle. No VM/parser/UR1 code touched.
