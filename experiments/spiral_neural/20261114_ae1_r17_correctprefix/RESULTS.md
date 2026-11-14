# AE1 R17 — b16→20 correct-prefix neural diagnostic (2026-11-14)

**Predeclared diagnostic gate: PASS 3/3 balanced seeds. This is NOT a learning-success gate.** R16's full-answer tests had already failed; no new training, free answer generation or model selection was performed.

## Scope and frozen evidence

- U: user's native-01 NN learning/generalization/math-education objective; not VM, protocol lexicon, or UR1 neural-ACK.
- F: R16 [PR #65](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/65) head `a8387971af7fcf72ec72cf51f24a735d97dcb419` and R14 [PR #63](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/63) nine F32 10,457-parameter checkpoint models.
- Freeze BEFORE forward: manifest commit `25717d17b2303688e7247807bd6691094b05cde3`, prereg commit `0b7b4b51868d645bfdc1a07e2d9a7f04d39dc35c`; manifest SHA256 `ad63d5ba47b92ca2790a44bec42bf3e604a39fef0ead0dd811acb657ebd65c27`; frozen runner SHA256 `0d909500873eb006c381500a7054300771f4583d0f9d356b7f4b8e0270cd3280`. Pre-run static gate PASS, 0 model forwards.
- SLE-AE1-n5-v1 legal raw 39-bit Q (`01+010+0100(r2)+4×(5-bit ID+0)+111100`), answer = a6+b6 + external STOP S. Only b changes 16→20 (one information bit). Fixed a, r2, c0, d1 and checkpoint. R14 train unchanged: 136 presentations /112 distinct; seeds 101,202,303; three arms control16, control8, balanced8_16.
- Validation a24 × b16/20 was previously visible; diagnostic test a28,29 × b16/20 was **already studied in R16**, so NOT a new researcher-blind test. Those first-word values are untrained in this student course.
- T: 54 cases ×13 correct-prefix positions = **702 new PyTorch next-token forward calls**, **7,665,840 forward dense MAC**, 0 optimizer updates, 0 new training targets, 0 new free generations. Prior R16 free strings only read.
- Reproduction: companion ZIP with 9 immutable checkpoint weights, R16/R14 source, all 54×13 raw logits, `run_r17.py`, independent NumPy verifier, and this public Torch replay. SHA256 of ZIP `bffbf615766bbc54efe32db6dc7dbb077214ebb5b9e86d5f1771118b738aa184`. Complete data and script supplied separately with run result; Git-only checkout does not contain weights. Independent NumPy **702/702 logits** agree (max abs delta 3.81469727e-6). Torch replay **54/54** agrees.

## Results

| Test (3 seeds ×2 first values ×2 b = 12 /arm) | Prior R16 full free exact | New teacher-forced first 6 positions all correct | New teacher-forced correct first-word bits |
|---|---:|---:|---:|
| control16 | 0/12 | 0/12 | 52/72 |
| control8 | 0/12 | 0/12 | 55/72 |
| balanced8_16 | **0/12** | **5/12** | **64/72** |

Predeclared gate: among the three balanced heldout paired b interventions whose R16 first generated word changed, **all 3/3 also changed first-word greedy predictions under identical correct-answer prefixes**. Individual pairs: seed101/a29, seed202/a28, seed303/a29. Two of the three had the free prefix still correct at the first differing position; seed101/a29 had already generated a wrong prefix.

## Post-hoc structural finding; do not relabel as preregistered mechanism test

The frozen R14 `WordStudent.forward` only uses input words, header and answer **cursor position**. It does not consume the actual values of the previously generated output bits: `cursor=z.sum(-1).sum(-1)-QLEN` counts positions. This was verified by inspecting the real source code, and **54/54** teacher-forced argmax strings are identical to the existing free-generated strings. Thus, in this architecture, contrasting correct-prefix vs generated-prefix responses **cannot distinguish error propagation**, because prefix content is not part of the network input features. The b perturbation demonstrably changes first-answer output via the full question, but no internal-layer bottleneck is identified.

This is compatible with a valid deterministic echo student design (input and cursor can suffice); it is not a protocol failure. However, calling the current setup an autoregressive model which learns from its output-bit history would be misleading.

## Decision / attribution

[更新] R16 first-word cross-field coupling persists under matched correct-prefix scoring, and previous-output bits are discarded by the student architecture. [取代] Correct teacher forcing alone could isolate feedback error amplification here. [原因] Real forward feature path excludes prefix values; all 54 correct-prefix argmax results equal free results. [狀態] High confidence for this frozen model; no claim about all neural architectures.

A: Next owner = independent NN researcher. Either freeze a matched resource comparison of cursor-only vs output-prefix-aware decoders, or test explicit a-output/b-input invariance with an entirely fresh unseen value+context split and equivalent curriculum. Do not retry this same prefix comparison as if it diagnoses a decoder that can read prefixes. Keep separate from Pro UR1, Codex F2/E3 and P031 shared-bank semantic completeness.

NVIDIA skipped: no authorized OpenRouter worker available (0 calls); Codex 0 calls (no local instance); Gemini 0 calls. No secret/private data published, no other branch overwritten, no auto-merge.
