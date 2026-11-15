# R42 — frozen before any model inference (2026-11-15)

**State at this commit: STATIC GATE ONLY. No new forward passes, no training.** Owner: independent SLE 01 small neural investigator. Parent R41 [PR #92](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/92), R38 [PR #88](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/88). R42 is not Codex, Pro UR1, Hamster VM or parser work.

## One causal intervention

With six **frozen** 10,457-parameter R38/R41 SLE→SLE checkpoints (seeds 101,202,303 per arm), substitute exactly one legal numeric input bit in the second data word b. The model's teacher-forced prefix **before the corresponding answer bit** is byte-identical on each pair; measure output log-odds shift (logit1−logit0) for an expected 0→1 flip, sign and both-endpoint correctness. Also generate independent full autonomous answers for each new question and report secondword/exact separately. This is a **bit-position identifiability probe**, not a new bitstream codec, new grammar or new NN training.

Legal profile: `SLE-AE1-n5-v1`, values 0..29, numeric token = 5 information bits followed by 0; raw question `01+010+bin3(r)+0+4*(bin5(v)+0)+111100` = **39 bits**. r=2, answer = two 6-bit numeric words plus external STOP class (S not a wire bit). No 30 or 31.

## Frozen dataset and splits

Training: unchanged, previously run R38 and R41, 136 teacher events, 1,408 target-prefix training items per epoch, 150 epochs and 3,300 Adam updates per seed. **R42 updates=0, training MAC=0**, same preexisting checkpoint for each arm. No baseline re-training.

Validation: historic R38/R41 panels for background only; no model selection. Test: **48 new raw Q strings**, eight held-out *contexts* (a=6,7,12,13 × (c,d)=(10,12)/(11,13)) × b={18,19,24,25,26,27}. All new Q checked against historical manifest files and training Q. Numeric b values **have already been investigated**; do NOT call them globally unseen integers.

Six predeclared one-bit legal paired contrasts for each a/c/d: 18→26 and 19→27 (2³ changed; trained both), 24→26 and 25→27 (2¹ changed; untrained 24/25, trained 26/27), 24→25 (2⁰; untrained endpoints), 26→27 (2⁰; trained endpoints). For each matched edge the exact output prefix through cursor 6+j is identical and only b-input bit differs. Thus 8 contexts × 6 pairs × 2 frozen arms × 3 seeds = **288 paired sensitivity measurements**. 48 Q × 2 arms × 3 seeds = **288 actual greedy answers**.

## Predeclared joint gate (ALL required)

R41 heldout-bit2 edges: 0→1 log-odds directional shift ≥18/48; both endpoint correct at changed teacher-forced output bit ≥12/48; secondword autonomous b24/25 ≥12/48. This is intentionally strict; report each metric and full answer separately even on FAIL.

## Source immutability and audit

Local prereg JSON SHA256: `b337c9d1638698608da9615acccfe6c99dfb975b557d12adfc69b7c4c3551425`
Local manifest SHA256: `483365f5de5ba70125ba9a36d1cf05fb27255a66b9d26786e0a713a2825147bc`
Full NN runner `r42_bitprobe.py` SHA256: `b63aa9a0b8833cc6f8bf39804de6978c6f84d9873d5e15e4c9f18c064530ce26`.
Source: R41 companion ZIP `f5ef137f0fbc424b01891d2c25d6eb4637d14abb9c8f812a245b9e05eebbc522`. All six checkpoint SHA stored in prereg; exact Python runner and model weights stored in companion output bundle, **not** presently uploaded to this Git freeze. Static gate executed: **48/48 legal 39-bit questions, 6/6 one-bit edges per context, all six checkpoint hashes pass**. No student was run before this Git freeze commit.

MAC model: 10,920 nominal dense MAC per forward. This is preexisting single-network estimate, not measured FLOPS or backward MAC. Report observed forward calls in result.

U: author's independent SLE neural education/research objective. F: R38 and R41 immutable prior evidence. T: R42 source/manifest checks only at freeze. A: strong context/bit-position role generalization absent despite paired 2³ contrasts (hypothesis to test). No model/teacher oracle computes answers for the students. NVIDIA=0 (no authorized live API in this runtime), Codex=0, Gemini=0. Do not merge automatically.

Next owner: run the exact frozen program and append failure/success/raw evidence without changing this gate. Review [PR #90](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/90) user correction separately: its full-answer 3-round student is **not this AE1 autoregressive student**.