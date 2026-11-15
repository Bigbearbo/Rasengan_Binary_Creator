# R58 preregistration — single legal c-MSB intervention (FROZEN BEFORE NEW NN FORWARD)

Status: **PREREGISTERED / 0 R58 neural forwards / 0 optimizer updates**. Independent native-01 small neural-network research, isolated from Pro UR1, Codex P030–P035, VM and grammar. Parent is Draft PR #108 head `5f816bee0e84b8747752c6ecf2a19e6fa2b4373b`. No automatic merge.

## Immutable evidence receipts

- Prior R57 portable archive SHA256: `61a863a0a209a43a15366e62db3b34494d52bd273f191aaddeef304984b82fea` (locally verified by sha256sum before this Git freeze).
- R58 local complete prereg JSON SHA256: `fa8039028cc46794559551c02ee220567c61f1fa0e9efbc0b8b836d297ed5796`.
- R58 generated 96-line raw-Q paired manifest SHA256: `fba1fcfdbe2f8a77a1630ad7d1e49d73a7b4010459efa4ad08a38bc6988b8cc8`.
- R58 executable source `r58_cmsb_frozen_probe.py` SHA256: `9c20e32fc48c3719a32baa096c978a66b003a60531f4277d785f5afeca3b6e30`.
- Source refs/weights SHA256 for three seeds, the full manifest and executable are recorded inside frozen `r58_prereg.json`. Local original self-contained R57 archive is not overwritten. ZIP will include executable, source weights, manifests and failures; these receipts identify exact bytes rather than suggesting Git itself contains the checkpoints.

## One intervention and causal question

**Unique factor:** change only **one native 01 input bit**, the MSB of the **third numeric data word c**, going from legal `c ∈ [0,13]` to `c+16 ∈ [16,29]`. Keep r, a, b, d, correct output and all trained weights identical. Models: frozen R52 learned intercept gate, R55 8 value-conditioned slopes, and R56 8 static intercepts. R55 vs R56 compare conditional value sensitivity under equal prior 500-update budgets. This is an inference-only diagnostic, **not** a new training regime. c is irrelevant to the target, so invariance is desirable, but a constant wrong output does not count as success: independently count both-full-correct pairs.

- Legal profile: `SLE-AE1-n5-v1`; raw input 39 bits: `01+010+bin3(r)+0+4*(bin5(value)+0)+111100`; numeric values 0..29. Expected answer is r repetitions of the corresponding numeric word ending 0, then external STOP action `S` (not an SLE grammar token).
- Source curriculum **unchanged**, 136 historical events / 1,272 non-STOP prefix targets. No teacher oracle for neural inference. Seeds `101,202,303`; each frozen model has 10,465 parameter tensors/scalars counted under the experiment's convention, R55 additionally 8 frozen buffer scalars.
- Manifest construction RNG seed `58016`. Exactly 48 paired operand contexts / 96 raw Q. Validation = 16 pairs/32 Q; test = 32 pairs/64 Q. Each split evenly balances r=1/2 and b low=0..5 / high=24..29. Exact 39-bit Q are absent from **1,836** archived distinct Q (including R57). Numbers and rules already seen; **not a blind numerical-domain test**. One bit differs, at raw index 21, and the expected answer stays identical.
- Novel evaluation per three arms × three seeds × 96 Q = **864 complete neural generations**; zero training updates. Forward dense MAC reference = 10,920 per call; record actual call count, estimated dense MAC, raw free outputs, failures, parity vs previous weights.

## Gates declared before inference (joint PASS iff all six)

1. 96 new unique legal exact-Q / 48 matched c-MSB pairs, one input bit, same target, correctly balanced.
2. R55 test first-word changes at least **8 fewer** seed-pairs than R56 static gate (96 seed-pairs).
3. R55 test full correctness changes at least **8 fewer** seed-pairs than R56.
4. R55 test both-members-entire-answer-correct at least **4 more** seed-pairs than R56.
5. R55 test full-answer correct count no more than **4 below R52** across 192 outputs.
6. Exact PyTorch replay and independent NumPy free-generation replay for all 864.

No tuning/extra seed/restart based on outcomes. Failure results must be retained.

Provenance: **U** research scope and rigor from author; **F** PR #108 fixed-head/R57 ZIP and source checkpoint hashes; **T** at freeze, only local source/manifest static checks PASS (0 R58 neural forwards); **A** learned value slopes might reject irrelevant c changes better than fixed intercepts, low confidence. NVIDIA skipped: no authorized executable local OpenRouter worker/key (0 actual calls); local Codex 0; Gemini 0. Next owner is the independent NN lane, not the VM/parser owner.
