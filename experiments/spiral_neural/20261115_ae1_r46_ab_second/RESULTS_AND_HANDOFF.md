# R46 native01 NN results — allow a+b at secondword, keep c,d masked

**Actual outcome: prereg joint gate FAIL (1/7 pass)**, on 2026-11-15. This experiment belongs to independent raw-01 neural research, not Hamster VM, syntax dictionary, Pro UR1 or Codex P030–P035.

Formal freeze was already committed at **`c56e38c10f810f1803bad36de421fe2f4f7ed903` before any R46 neural training/inference**. This report records the completed experiment; prereg/course/test/runner hashes were not altered.

## Intervention and resources

Relative to immutable **R44 PR #95** (second answer word only sees b), permit **a and b** but continue masking c,d for r2 cursors 6–11. Non-secondword paths remain unchanged; read-only **R45 PR #96** already permitted a,b,c,d. No new weights/parameter-count or additional input/output tokens. This tests contribution of a distractor in isolation, **not** a learnable source selector.

Legal SLE-AE1-n5-v1, integer range 0..29. 39 raw input bits; two SLE six-bit output words plus external STOP (S). R44's original ordered 136 teaching events, same 1408 teacher-forced targets/epoch, seeds 101/202/303, 150 epochs ×22 minibatches/seed, 10457 parameters/student. **9900 real Adam updates**, 633600 supervised target appearances, 6,918,912,000 theoretical training-forward dense MAC (backprop/optimizer excluded). No teacher oracle is available at autonomous generation.

Test the **same** 96 R44/R45 contexts ×3 seeds and 80 historical full-answer Q ×3. They were previously seen by the researcher; **NOT blind test**, and b28/29 is role-untrained rather than globally unseen. All controls below are archived real R44/R45 results, not newly retrained.

## Real autonomous neural results

| Three-seed aggregate | R44 b-only | R45 all-input | R46 a+b only |
| --- | ---: | ---: | ---: |
| Old b18/19, secondword | 48/48 | 0/48 | **40/48** |
| Displaced b20–23, secondword | 80/96 | 0/96 | **20/96** |
| Taught b24/25, secondword | 48/48 | 0/48 | **18/48** |
| Protected b26/27, secondword | 48/48 | 2/48 | **32/48** |
| Untrained-in-role b28/29, secondword | 48/48 | 1/48 | **20/48** |
| Historical 80Q×3, full exact | 228/240 | 209/240 | **206/240** |
| New 96Q×3, full exact incl autonomous S | 0/288 | 0/288 | **0/288** |
| New 96Q×3, correct-prefix STOP | 10/288 | 288/288 | **3/288** |

R46's prereg gates: b24/25≥40/48 FAIL; protected b26/27≥40/48 FAIL; old b18/19≥40/48 **PASS**; role-untrained b28/29≥32/48 FAIL; displaced b20–23≥72/96 FAIL; historical exact≥216/240 FAIL; new full exact≥1/288 FAIL.

**Interpretation:** a alone is enough to substantially disrupt the learned secondword mapping, even while c/d remain masked. It does not prove that a is the only source of R45's losses or that routing cannot be learned with different architectures. Training also changes parameters shared with STOP, so r2 correct-prefix STOP collapsed from R45 288/288 to R46 3/288 even though the STOP input mask itself was unchanged. Firstword/STOP must not be confused with secondword substring correctness.

Sample failure (seed101): Q `010100100001100110000011000011100111100` (r2,a6,b24,c12,d14), expected `001100110000S`, generated `00000010000010000000000000000000`, capped at 32 without stopping. Secondword-only correctness is not end-to-end correctness.

## Reproducibility and provenance

**528 new full native01 generations**, 12,375 model inference forwards, 135,135,000 inference dense MAC. PyTorch **528/528 exact replay PASS**; separate NumPy independent implementation **528/528 PASS**, maximum correct-prefix STOP logits delta **1.9073486328125e-6**. Posthoc fixed-weight routing check compared 80 forward positions and found equal logits outside r2-secondword. Clean extraction verified **233 files** by R46_SHA256SUMS and reran both replays successfully.

Companion ZIP: `sle_ae1_r46_ab_second_route_20261115.zip`, SHA256 **`522bf4e495220ecbe030bb456c69d048dcd42b0677e4c5e43450bc81e887a5cc`**. It contains complete `r46_ab_second_route.py` source, immutable historic source/weights, test manifest, three new checkpoints, all raw outputs, hash manifest, prereg and local report. **This ZIP is delivered in the originating conversation, not tracked by Git; Git checkout alone is insufficient to rerun the neural model.** Run from clean extracted `r45/` directory: `python r46_ab_second_route.py replay` and `python r46_ab_second_route.py numpy`. Re-training is not needed and would be a repeat experiment.

Immutable fingerprints: local runner `b10356f0161eebe12037b07c3bb7dc9ddce9b252b428641309bd8e77a2fba0b9`, manifest `d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416`, prereg `de3f7f63300aa6ad3d550f43ed191abee1c0d526c13b0d1ad8438be40038f3d1`; raw outputs `09cc6f393fa7b69b8ddbd3f4fa7abb6a3ccf266c238d806a99c62502b4b57e04`; result JSON `47e3c8bee9a9d0a4627155282ef1cbe48748c792f790f27a4f99d1ce95e184ff`. Checkpoints SHA seed101 `da687d05b9154dc156ff9c517b8caf70119d2ac537728d66438b87175aa343ed`, seed202 `d14cafa3cd74838750499a275571fce083e4ca589aee28a63ecf0d4dc5c9481f`, seed303 `b0d1900cfb6245281c8ebe6841148e91b9e6478e662328df9c89ef784c485ffb`.

Provenance: U — author wants SLE small neural learning and causal matched controls; F — exact R44/R45 immutable ZIP/Git evidence and other workstream summaries; T — actual 3 fresh R46 students/528 answers/2 replays and integrity check; A — source-interference mechanism under further test, no broad claim. NVIDIA=0 actual calls (no authorized callable endpoint); Codex=0; Gemini=0. No PR merged and no other researchers' branch modified.

**Next owner:** independent native01 NN researcher. A possible *new*, separately preregistered one-factor trial is c-only or d-only unmasking, or a learnable conditional source gate with matched cost. Do not reuse these 96 questions as fresh blind generalization. Measure actual whole-answer and autonomous STOP; do not optimize only secondword substring scores.
