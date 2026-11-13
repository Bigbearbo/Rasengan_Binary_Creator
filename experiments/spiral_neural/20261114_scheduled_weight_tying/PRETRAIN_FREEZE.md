# Pre-training freeze — AE1 positional word-encoder weight tying (2026-11-14)
Owner: independent scheduled small raw-01 NN researcher; work_id=SLE-AE1-WEIGHT-TYING-20261114-R11. Status: **pre-optimizer preregistration, not a reported result**.
Baseline PR #54 branch research/scheduled-nn-ae1-equal-unique-role-20261114 @ 3a5e3848cac8c4706aef24f30e41ab2bbf5008e4. Historical sources: PR #40 parent course, PR #54 first-high data; P030–P035/UR1 are different experiments and not repeated.
**Binding SHA256 of local files fixed before training:**
- run.py `4b5496f7eb0ceb86341e5a89b7052d6af4bfdf401ef4d5798a59b14e0cce62ce`
- manifest.jsonl `97749bd4c921a5eff34668e8a39776bc3704a4fb49a50f2456600915f1c68b74` (156 unique examples with Q/truth)
- parent_course.json `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a`
- prereg.json `d900813a324db3a9f98dc36526ccafd0eda8994d147ca61d4f459db4c3f37706`.
All original runnable source and raw manifest are to be published *byte-for-byte after this commitment* (or in companion audit ZIP if connector size prevents upload). Any SHA mismatch invalidates the experiment; do not edit a frozen source after seeing results.

## Single factor / exact educational input
Profile SLE-AE1-n5-v1: legal 39-bit Q = `01 + 010 + r(3 bits)+0 + 4*(ID5+0) + 111100`, data IDs 0..29, 30/31 reserved. Student input is only the raw Q 0/1 plus its own autoregressive output prefix; output is first r complete six-bit data words, then student-generated external STOP. No oracle for answer generation at evaluation, no LLM teacher.
Both models apply **the identical deterministic raw-input frontend**: four word-aligned 6-bit/2-channel sensors at Q[9:33]; exact Q header 8 channels; output position derived from raw occupied-bit prefix length 0..32. Both have 16d token embeddings, 94-hidden tanh decoder and 3 output logits. Sole model factor: 12→16 word embedding weights **tied across four word slots** versus **four independent copies**. For every paired seed the two networks are initialized with identical functions and shared decoder weights; after that weights update under their respective constraints. Tied 10,457 params; untied 11,081 (+5.97%); each 10,920 forward dense MAC by explicit matrix counts. Same MAC and dataset/updates, unequal parameter count inherent to factor. This *does not* isolate raw-MLP vs structured frontend, nor prove a universal copy algorithm.

Training: PR40 immutable 120 presentations (96 distinct) plus 16 first-high r2 lessons (high 16..19 in a; low 0..3 in b; c0 d1), total 136 presentations/112 distinct, 1,408 teacher prefix→target pairs per epoch. Both arms identical curriculum. Seeds [101,202,303]; fresh Adam lr.003 per arm, clip norm 1, epoch-shuffle seed+201000+epoch, batch 64, epochs 150, 22 updates/epoch=3,300 per student, 19,800 total across 6 students, 1,267,200 target presentations; forward-only training dense MAC 13,837,824,000 (exclude backward/optimizer).

## Fixed evaluation (no test during training)
Seen baseline 48 (r1/r2 a0..5 x b18,19,22,23 c0 d0). Actual taught injection 16. Validation 8: r2 a8/9 x b18,19,22,23 c0 d1. **Primary untouched student test** 28: r2 a6,7,10,11,12,13,14 × b18,19,22,23 c0 d1. Secondary second-word OOV 28: b6,7,10,11,12,13,14 × a0,1,2,3. Context robustness 28: same first-word OOV with c1 instead of c0.
All 6..14 OOV values absent from training anywhere, and manifest fixed before training; prior work studied adjacent domains, so call student-heldout **not independent researcher-blind**.

**Success gate frozen now**: at least 2/3 seeds each tied >=12/28 primary exact, exceeds untied by >=6/28, with both paired models seen baseline >=40/48. On failure publish negative result, no new seeds, checkpoints, epochs, or test-conditioned curriculum.
Preflight validates every raw Q, 136/112 exposure, no test-value collision, 156 manifest Q, source SHA, 10,457/11,081 params and 10,920 MAC. Only after this remote freeze may NN train and test. Exact failures, raw generated bits, 6 final F32 weights and independent NumPy replay are deliverables.

U: user wants SLE bitwise small NN curriculum/generalization. F: PR40/54 source and Git references, preceding P030-P035/UR1 independent. A: word sharing could help new combinations, unproved. T at freeze: static source generation and local SHA calculations only; 0 optimizer and 0 student eval. No Codex desktop process / NVIDIA authorized worker client available in the current runtime (0 calls planned, document actual counts). No secrets or private chats; no merge, no edits to other branches.