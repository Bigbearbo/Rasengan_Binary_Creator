# SLE-AE1 Fourth-word d single-bit invariance — pre-inference freeze

**State at publication: PRE-FORWARD.** This is an independent small-NN experiment, not a VM/parser, not UR1 training. Do not treat this as observed results. Owner: independent scheduled NN investigator.

## Source and unique factor
- Parent PR #46 branch SHA `1598246cde44d9b29a0fdf6645e27ff023dde4b0`; its four genuine checkpoints came from the exact accompanying ZIP SHA-256 `8b12a6ee72c7fe8746381cc7f80ef51dd84b378ee245aa0c5d2b3870b6709e2f`. Original source SHA/inventory checked.
- **Only fourth data word d changes**: d=0 baseline versus d=1,2,4,8,16 (exactly one information bit toggled). r=2, a, b, third word c, frozen model, expected answer unchanged. No tuning or additional training.
- SLE-AE1-n5-v1: Q39 = `01+010+010+0+4*(5bit value+0)+111100`, ordinary IDs 0..29; ID 30 END, 31 UP are reserved; answer copies first two intact six-bit words then **model-generated** `S`. This is a fixed known profile, not learning grammar.

## Complete enumeration and evidence contract
- Fixed seeds 101,202; arms `frozen_c1_control` (PR44) and `balanced_c` (PR45); four F32 student checkpoints, 10499 parameters each, 160-position one-hot -> 64 tanh -> logits3 for 0/1/S; max input length 80, greedy cap32.
- Historic training only (no new train split or optimizer). Heldout validation a=4, test a=5, b in {26,27}, fixed context blocks c in {2,3}. d in {0,1,2,4,8,16}. Exactly 2 seeds × 2 arms × 2 a × 2 b × 2 c × 6 d = **192 rows** and **48 distinct Q**, including 32 d0 reference predictions and 160 untrained one-bit-d interventions. This is newly intervened d, not researcher-blind a/b/c data.
- A priori **primary gate**: for **each** balanced_c seed, for each c in {2,3}, all four d0 anchors must be exact, and all 20 d>0 responses must be exactly correct and identical to their corresponding d0 free-generated full answer. Total 40/40 d-flips per seed required; otherwise FAIL. Old controls diagnostic only. Do not revise gate after data. Secondary: per-d bit and per-c effects, compare c2 old negative and c3 previously positive controls.
- Exactly 0 optimizer updates, 0 new teacher-target exposures, 0 training MAC. Frozen model dense inference MAC = 160×64 + 64×3 = **10,432 per generated bit/STOP**, actual count to be reported, not estimated. No LLM/teacher oracle for answers.
- All 192 raw Q/expected/generated answer, failure rows, actual greedy forward/STOP counts, all checkpoint SHA and repeatable independent Torch/NumPy result must be saved. Do not assume all outputs STOP correctly.
- Preflight **already passed with zero NN forwards**: four checkpoint SHA and embedded weight digests valid, legal 39-bit questions, exact d one-bit transformations, frozen code/profile/target integrity. Actual training/inference is not yet claimed.

## Frozen SHA commitments
- Full local `PREREGISTRATION.json`: SHA256 `ae29738dc5d69f8625c1c41754eb04079c86527ef03fbba01552448cd1046343`.
- Local executable `probe_d.py`: SHA256 `dfe595b4758bc9b9dfb3ebbfdff94bfe1bf78761ba81e8e97f739459b8d6f766`.
- Independent standalone NumPy verifier `verify_d_numpy.py`: SHA256 `18fb683449abe88212753dde8a5583a7766626060b09fcf8bc3ea2adaa7168fd`.
- Checkpoints: seed101 old `6472ff0222228b3b95cb2de781ccf9c97ae8f730ddd1caa5e5db95bb67f392bc`, balanced `c795c97cac145507a842f02eb8b8e65c92aa195523a2c8ec3b1f09a94fc0d3e3`; seed202 old `ee930b8fd2803f889502e709ede5e4853448c98901de6d37b03e62a09854047b`, balanced `1ae8a29f40d1ae11410c5948e1fad10088d7e1368744be0356110c8d7e0e2baf`.

## Provenance, scope and next owner
U: author requested SLE raw 01 small NN learning and controlled generalization. F: PR40–46 genuine saved weights, PR #47 Codex E3 is separate; P031–035 already completed, UR1 PR12/13 are separate executed experiments. A: sensitivity to fourth irrelevant data word can distinguish c-specific parity shortcut from broader suffix binding; neither proves internal mechanism. T prior-to-forward: local static preflight and hashes only. NVIDIA 0 calls (no configured authorized worker in this runtime); local Codex 0 calls (not exposed); Gemini 0. Never upload secrets/private chats. Await real run and independent replay. PR must stay Draft and must not be auto-merged.
