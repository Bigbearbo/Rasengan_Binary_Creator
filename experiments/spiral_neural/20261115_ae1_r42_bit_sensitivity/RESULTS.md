# R42: one-bit b-role sensitivity under frozen R38/R41 checkpoints (2026-11-15)

**Outcome: preregistered joint gate FAIL (1/3 individual PASS).** Source freeze committed **before neural inference**: `4bf248f90ddcfdd430af1bd2d54ecf1cd7de7a7d`. Weights, train course, and optimizer unchanged, no new training. New work is 288 actual neural full-answer generations + 288 teacher-forced one-bit paired-logit measurements, **not** a rerun of P030–P035 or Pro UR1.

## Causal question, data, resource
R41 paired **b18↔26 / b19↔27, bit 2³ (8)** in minibatches. Its failed novel-context b24/25 probe differs from known b26/27 at **bit 2¹ (2)** instead. These are different bits. Does the model not sense bit 2¹, or detect it while still choosing the wrong answer bit?

Fixed 10,457-parameter R38 hard-route and R41 paired-batch NN models, seeds **101,202,303** each (six untouched weights). Legal `SLE-AE1-n5-v1`, numeric 0..29, r=2; input raw bits `01+010+bin3(r)+0+4*(bin5(v)+0)+111100` = **39** bits. Target r six-bit numeric words + external STOP S (not a wire bit). Training inherited 136 course events, 1,408 target positions/epoch, 150 epochs and 3,300 Adam updates per student. **R42 new updates=0, training MAC=0**.

Precommitted test: 8 distinct (a,c,d) contexts (a=6,7,12,13 × c,d=(10,12)/(11,13)), b=18/19/24/25/26/27, 48 new raw Q, disjoint from previous matching raw Q. Values b24/25 were previously tested, so **not globally blind integers**. 6 legal paired edges per context: 18→26,19→27 (2³), 24→26,25→27 (2¹),24→25,26→27 (2⁰). Target bit isolated by **identical truthful teacher-forced prefix on both endpoints** and one changed input bit. Same-model matched comparisons; no LLM/teacher oracle supplies student answers.

| Edge | R38 directional/both-correct, /24 | R41 directional/both-correct, /24 |
|---|---|---|
| 18→26 (2³) | 24 / 24 | 24 / 24 |
| 19→27 (2³) | 24 / 24 | 24 / 24 |
| 24→26 (2¹) | **24 / 0** | **24 / 0** |
| 25→27 (2¹) | **24 / 0** | **24 / 0** |
| 24→25 (2⁰) | 24 / 24 | 24 / 24 |
| 26→27 (2⁰) | 24 / 24 | 24 / 24 |

In heldout-bit-2¹ pairs, R41's low b24/25 mean output margin (logit1−logit0) was **+2.267** although expected 0; high b26/27 mean margin was +10.588, correctly expected 1. Mean directional **shift +8.321**, so the changed input is sensed, but both endpoints do not cross the correct decision boundary. R38 analogous low +2.572, high +10.747, shift +8.174. This does **not** isolate internal mechanism or prove a general SLE advantage.

Autonomous free generations (each arm, across 144 replies): secondword **96/144**, b24/25 secondword **0/48**, exact 2-word answer **1/144**. Firstword correct R38=11/144, R41=13/144. Some fail STOP; conditional correct-prefix success is not full task success. All failed answers preserved in raw JSONL.

**Preregistered R41 gate**: 2¹ positive shift ≥18/48 → **48/48 PASS**; both bit endpoints correct ≥12/48 → **0/48 FAIL**; autonomous new-context b24/25 secondword ≥12/48 → **0/48 FAIL**. Composite **FAIL**, no changes after results.

Example R41 seed101: b24 question `010100100001100110000010100011000111100` expected `001100110000S`, generated `00010010010010000000000000000000` (cap); b26 question `010100100001100110100010100011000111100` expected `001100110100S`, generated `00011011010011011111111111110111` (cap). Teacher-forced changed-bit margins +4.005 / +11.941; low still classifies incorrectly.

## Executed reproducibility and artifact integrity
`python r42_bitprobe.py freeze; python r42_bitprobe.py gate; python r42_bitprobe.py run; python r42_bitprobe.py replay; python r42_bitprobe.py numpy`. True Torch CPU output: 288 full replies, 288 paired comparisons; **8,462 actual NN forward calls**, approx **92,405,040 forward-only theoretical dense MAC** (not GPU FLOPs); **0 new training/backprop updates**. PyTorch replay **288/288 replies and 288/288 pairs identical**; independent NumPy **288/288 on both**, maximum logit gap **1.9073486328125e−6**. Fresh ZIP extraction **190/190 file SHA256 PASS**, replay/gate passed. The public read-only verifier in this PR only checks hashes+raw counts, not neural re-execution.

Companion ZIP **`sle_ae1_r42_bit_sensitivity_20261115.zip`**, SHA256 **`5d975bc64b33933063f6d96917cc7ee95dc942d18d24ecf3e6886f99d140ed37`**, 2,442,649 bytes. Contains full NN runner, R38/R41 frozen weights, raw Q, 288 answers, 288 paired logits, Python/NumPy independent replay, all failures and inventory. **Companion stored in conversation output, not Git**; Git-only checkout is **not NN-self-contained**. Script SHA `b63aa9a0b8833cc6f8bf39804de6978c6f84d9873d5e15e4c9f18c064530ce26`, prereg SHA `b337c9d1638698608da9615acccfe6c99dfb975b557d12adfc69b7c4c3551425`, manifest SHA `483365f5de5ba70125ba9a36d1cf05fb27255a66b9d26786e0a713a2825147bc`.

U: user independently scoped SLE raw-01 small-NN research. F: R38 PR#88, R41 PR#92, Codex P030–P035, shared math PR#5 and Pro UR1 PR#12. T: R42 actually executed frozen NN inference/NumPy replay. A: an overly positive bit-2¹ output margin on low b may explain local role failure, not proven general mechanism. Latest user correction PR#90 concerns a **distinct 321-dimensional three-round whole-output model**; do not conflate with AE1 prefix-generated model. NVIDIA 0 calls (no accessible authorized live OpenRouter worker), local Codex 0, Gemini 0. No Pro/Codex/VM branches edited or PR merged.

[更新] 0/48 b24/25 generalization does not mean there is no input-bit signal; all 48 heldout bit-2¹ contrasts shift log odds in the correct direction while low endpoints remain wrong. [取代] Bit-2¹ insensitivity as an assumed explanation for R41 failure. [原因] Actual matched raw-bit interventions and same-prefix neural logits. [狀態] High confidence in this fixed-model observation, low confidence in internal mechanism/generalization.

**Next owner:** independent SLE small NN investigator; one-factor equal-budget contrast on boundary calibration or single-bit loss/teaching coverage, preserving a genuinely unprobed legal heldout family. Do not call b24/25 globally blind or repeat P035/UR1.