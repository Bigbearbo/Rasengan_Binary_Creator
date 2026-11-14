# R36 — frozen before neural inference

Work ID: `SLE-AE1-R36-RESPONSE-ARITY-TRANSFER-20261115`. Owner: independent small NN research (not Pro/Codex/NVIDIA). Base is the unchanged R35 PR #85 head `31890565c38cbca1a33dc04ea18c611abf36694d`. This branch is isolated; no merge or changes to Pro/Codex/VM/parser.

**One controlled variable:** response cardinality `r=1` versus `r=2` for otherwise identical `a,b,c,d`. The question's normal r-header changes, and an r2 answer adds a known second numeric word `b`; first six output bits must still encode `a`. All four previously-trained codec arms use their immutable original checkpoints: SS = SLE/SLE (R31), SB = SLE/binary6 (R35), BS = binary6/SLE (R34), BB = binary6/binary6 (R33).

**Profile:** legal `SLE-AE1-n5-v1` for SLE input, 39 native 01 question bits; SLE output six-bit numeric words = five information bits + trailing zero; non-SLE binary6 arms are controls, not new legal SLE. The `S` symbol in inference is an external stop class, not a wire bit. **Numeric domain is 0–29**, as explicitly enforced by historical `word()` implementations, so suggested values 30/31 are *not permitted* here without a distinct approved profile; do not stretch the current codec.

**Holdout selection fixed without examining new outputs:** first-role `a∈{14,15,28,29}`, second-role known `b∈{18,19}`, nuisance `c∈{1,3}`, `d=5`, with both `r∈{1,2}`. Total 16 semantic pairs ×2 r=32 distinct semantic inputs, 3 seeds (101/202/303) ×4 codec arms = **384 new whole-string NN generations**. Test inputs have no exact raw-question overlap with R35's fixed benchmark. **Not globally blind:** heldout numeric a values were probed in historical experiments even though absent from first-role training. Exact new compositions are untested at freeze.

**Training & capacity locked:** reuse R31/R33/R34/R35 checkpoint JSONs, three seeds per arm, each 10,457-parameter `NoFirstMask` student, historical 136 ordered lesson appearances, 122 distinct semantic questions, 1,408 teacher-forcing targets/epoch, 150 epochs, 3,300 Adam updates per seed per arm. **This run has 0 training updates / 0 new training MAC.** Count actual inference forwards ×10,920 dense forward MAC; exclude CPU overhead and neuron/encoder costs outside this definition.

**Primary gate (set before inference):** R2 TRANSFER PASS iff **both matched-codec arms SS and BB**, each pooled over all 3 seeds (48 r1 and 48 r2 evaluations per arm), meet all four: r2 first-word correct ≥ r1 first-word correct minus 8; r2 first-word correct ≥12/48; autonomous r2 exact ≥6/48; paired r1/r2 first-six-output equality ≥36/48. Otherwise FAIL. Mixed arms are descriptive. Also report by seed, paired both-correct, second-word correctness, teacher-true-prefix STOP separately. Do not promote STOP alone to copying skill. No gate adjustments, extra checkpoint selection or post-failure training.

**Immutable pre-inference local provenance receipts:**
- Full prereg JSON SHA256 `b2c8193da8cf427e55df1a004eaa4e3dabf50a79e80ea3c9460a1dccf97db571`
- Exact 32-row bitstream manifest JSONL SHA256 `1ef9048f9a1b23e235dc2ea552d347f1c462d9c2c8b413710a3c0b7e66c708d4`
- Runner `r36_arity_transfer.py` SHA256 `870e86882e0654ebd2277643af1351e3f1a16fd3720fa51f0bd25543842bfa08`
- Historical R35 prereg `7174a5e646dee2f37666dae5415604322fa09bbad05e09b3f942f1e9d77a1535`
- Historical training manifest `ae94e8d7f4c730ce6b26451d57edd228a2ab3c93b664e84356b0905bb0897d72`
- Historical test manifest `02f04ba556c4c70e49122371d5ee61e0cc2f82dce171602b3e02a394b5782825`

The complete prereg contains each of the 12 checkpoint SHAs and each raw bitstream. Locally completed **only static checks**, including 32 unique per-arm questions, no exact Q overlap with R35, legal values ≤29, matching source and checkpoint hashes, 10,457 parameters, and untrained first-role `a` values. The runner's `evaluate`/NN forward has **not** run at Git freeze.

**U/F/T/A:** U = author's raw-01 SLE small-NN education direction. F = historical R31–R35 sealed weights and P030–P035 / Pro UR1 actual status. T at freeze = static materialization and integrity checks only; **0 new neural inference so far**. A = response arity might perturb learned firstword mapping, direction undecided. Pro PR #12 **already ran** a separate failed UR1 neural ACK experiment; do not demand authorization for this separate AE1 frozen-weight diagnostic or alter its manifest. Public results only. NVIDIA 0 (no authenticated authorized endpoint); local Codex 0; Gemini 0.

Execution after commit: `python r36_arity_transfer.py gate`; `python r36_arity_transfer.py evaluate`; `python r36_arity_transfer.py replay`; `python r36_arity_transfer.py numpy`. Companion artifacts and code are external to Git until added as verifiable receipts; Git-only checkout is **not** self-contained.
