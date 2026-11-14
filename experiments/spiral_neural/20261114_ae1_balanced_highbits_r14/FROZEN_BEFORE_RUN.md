# AE1 R14 — Frozen before neural run (2026-11-14)

Owner: independent scheduled SLE small-neural research. Status at commit: **0 R14 optimizer steps, 0 R14 NN forward**. Do not merge automatically. This independent AE1 experiment is NOT Pro UR1, Codex P035/F3, syntax-parser or Hamster VM research.

## Source and exact artifacts

Git main branch is branch creation base; old controls remain immutable and are loaded from companion checkpoint archives. Historical source [PR #55](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/55), latest [PR #62](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/62); [Pro #12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12) belongs to a separate UR1 protocol and has already run 3 NN students. R13 companion SHA256 `cfb4d067dd55f21da296d60402d82c72c3d221e59f4741d1936264a4ed621705`. PR55 checkpoint companion SHA256 `53f6e312f30570ef7d458f35b25c17b49eb7b161415bb5d3b165645aeb8f10a0`. Full runnable source and cases will be attached after this freeze; the byte hashes below pin them now. No outside oracle in student inference.

Static local files prepared and hash checked **before any NN forward / optimizer**:
| File | SHA256 |
| --- | --- |
| run.py (original PR55) | `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a` |
| parent_course.json (original 120 Q) | `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a` |
| train_r14.py (new) | `32369b8f5739780321e1f3e19984e41221c42054078d54b7fb444bd8c19ddebe` |
| cases.jsonl (new 176 real native Q, teacher oracle expected labels) | `2bdba9e6a1a9545af966c11dbf65be18df2b75ac266c2e0b5126bcd6c079fd93` |
| prereg.json (this experiment) | `424a8cf08457ea200057b78595130906ea3bb93287d80b548f13fb2ccacbb1e5` |

## One factor, lawful profile and fixed budget

`SLE-AE1-n5-v1` native 01. Question `01 + 010 + 3-bit r + 0 + four (5-bit ID + 0) + 111100`, length 39, words 0–29. For `r=2`, student must emit `word(a)+word(b)+S` (S = external STOP action; never an input wire bit). Static parser/teacher only encodes Q and expected targets, not student outputs.

Parent **120** presentations unchanged. Exactly **16** added r2 first-answer high examples, total **136 presentations, 112 unique Q, 1,408 teacher-target prefixes per epoch**. Compared with full bit8 exposure R13, replace exactly eight high8 examples with eight high16 examples; each high family sees a=8..11 or 16..19, 2 contexts per a; per family b=0..3 appears twice. Other parent lessons unchanged. This is a **frequency/coverage tradeoff** experiment; it does not isolate a neuron's effect.

Three new F32 tied-encoder models `seeds=101,202,303`, 10,457 parameters, **10,920 forward dense MAC per training target**, Adam LR0.003, gradient norm clip1, batch64, 150 epochs, **3,300 optimizer updates per model** (9,900 total; **633,600 training teacher targets**, **6,918,912,000 forward-only training dense MAC**, backward excluded). Control16 PR55 + control8 R13 checkpoint reuse, **zero control retraining**. Original initial seed routine and epoch permutation `seed+201000+ep` preserved.

## Splits fixed before inference

24 validation: first-answer a=12,20,24, each crossed with b=0,1,2,3,18,19,22,23. 72 heldout test: a=13,14,15 (bit8); a=21,22,23 (bit16); a=25,26,27 (both bits), with the same eight b. All test/validation first-answer values absent from new students' first-answer training. a25..27 are absent from every word slot in the training corpus. Plus 48 seen baseline (r1/r2 a0..5 b18,19,22,23) and 32 exposed-high values (a8..11,16..19 crossed with b0..3). **Researcher has inspected adjacent values in prior rounds; this is student-heldout, NOT fresh external blind.** Test never influences training, no post-result new seeds/epochs.

## Predeclared main gate

At least two of three seeds each meet ALL:
- balanced heldout bit16 >=4/24, and >=4/24 more than reused R13 control8;
- balanced heldout bit8 >= reused R13 control8 minus 4/24;
- balanced seen baseline >=40/48;
- balanced exposed-high >=16/32.
Report combined-high scores regardless. All failure traces retained; if group gate FAIL, label FAIL without extra optimizer.

U: user requested independent raw01 NN teaching/generalization growth; F: fixed PR55/R13 sources/checkpoints; A: the balance might preserve both bit roles, unverified; T: at freeze only static corpus/hash/gate verified (0 NN). NVIDIA reviewer **0 calls**, no available authorized endpoint; Codex 0, Gemini 0.

Next owner: independent NN reviewer; keep checkpoint provenance and all negative results. Do not assume Pro UR1 manifest approval or merge stacked PRs.
