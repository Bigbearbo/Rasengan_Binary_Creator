# AE1 high-bit first-answer teaching: frozen preregistration (before optimizer)

work_id: SLE-AE1-FIRST-HIGH-ROLE-TRANSFER-20261114
owner: independent scheduled small-NN researcher; not VM/parser/UR1/Codex
source PR #52 head: `76636565b73c2d1dc0383ea1bbe9ff3fbb2e1ad5`
frozen student source: PR #40 head `80b814f0c4041471cd99395d2a10f6c86cb4f2d3` (2 F32 mixed-curriculum checkpoints).
profile: SLE-AE1-n5-v1; legal 39-bit Q = 01+010+r(3 bits,1/2)+0+(five-bit ID+0)*4+111100, IDs 0..29; r2 answer word(a)+word(b)+student STOP; r1 word(a)+STOP.
**Single treatment factor**: the high values 16,17,18,19 appear in first-answer slot versus second-answer slot of the same 16 added r2 training lessons, swapped with low values 0,1,2,3. Both arms have exactly the same payload value multiset, length, numerical bit/label histogram, and teacher target count. All else fixed.
Base course: PR40 120 presentations, 96 distinct (60 r1 + 60 r2); 16 added lessons/arm. High/low × Cartesian 4×4; c=d=0.
Warm start: identical PR40 seed 101/202 final model weights per arm; both restart **fresh Adam optimizer** because archived parent Adam moments are unavailable. L80/H64, tanh MLP, 10,499 params. Adam learning rate .003, grad norm clip1, deterministic order seed+131000+epoch. 100 epochs, 1408 target-prefix pairs/epoch, batches of64, 22 updates/epoch = 2200 updates/student, four students = 8800 updates. 5,875,? training dense MAC (exact integer computed from 1408×100×4×10432), excludes backward/optimizer.
Known-baseline 48 per student: a0..5 × b18,19,22,23 × r1/r2. Taught: a16..19 × same b, r2 (16). Validation: a20..23 × same b, r2 (16; second-role-known, first-role-unseen). Test: a24..27 × same b, r2 (16; never payload value in PR40 source or either injected curriculum). Exploratory r1 stress: a20..27 × b, r1 (32). All c=d=0; 128 different legal Q per student; 512 outputs across four students. These heldouts are fixed here before training; user/researcher has viewed earlier a8..13 experiments, so not independent investigator-blind across history.
**Pre-specified primary PASS**: for EACH seed, first_high correct ≥12/32 on val+test, first_high − second_high ≥8/32, both arms retain ≥40/48 known-baseline. No retuning seed, epochs, data or mid-checkpoint selection. STOP/accuracy/negative cases all preserved. Failure is a result.

Immutable local prereg + source digests (SHA256, before NN train):
- `run.py`: `9c912192f94c432c01d625219a4170bab05af047045df5fe2d1587ba06ce98d4`
- `cases.jsonl` 128 rows: `6e832a31e5eb9bfb20d2c967d6edb137d936bf81c7ebde20d29e4c12ad4a76ac`
- `parent_course.json`: `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a`
- `weights_seed101_parent.json`: `ac022fdcac1c6e9de5b78e1667519a6443e05c7f8e48fe4b84514432a1576009`
- `weights_seed202_parent.json`: `048c719e8c2afbbcac579b80a2f820989eb68ba030a1f2ce7c2747474897a157`

This freeze claims **zero new neural updates and no test forward yet**. Execution artifacts will be attached separately with exact program, raw Q/expected/actual, four final weights and independent NumPy verifier. Do not treat Git-only metadata as checkpoint-complete; no auto-merge.
U: author's original 01 small-NN education scope. F: PR40 student/PR52 failures/parent course. A: role-specific high-bit examples might transfer to untrained first word values, uncertain. T: future CPU run (not yet at freeze). Nvidia: skipped, 0 calls, no authorized callable NVIDIA runtime. Codex desktop: 0 calls. No LLM answers.