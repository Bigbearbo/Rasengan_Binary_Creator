# AE1 first-answer high-value teaching (2026-11-14) — genuine NN run

**Preregistered primary gate: FAIL.** First-answer-slot teaching produced a limited transfer improvement, but **all genuinely new numeric values a24..27 remained wrong**, including both seeds. No retuning or added seed/epoch.

## Evidence and chronology

- Parent: Draft PR #52 head `76636565b73c2d1dc0383ea1bbe9ff3fbb2e1ad5`; read actual parent course and two PR #40 mixed NN F32 checkpoints (seed101 and seed202).
- Pre-optimizer Git freeze: `ce8483e53ec2e45d822792ea553a714b97a977bb`; **failed static assertion** followed by pre-optimizer erratum `5fc97aae878e3e6316a737e547dce911e3a50481`, then corrected preflight PASS.
- Profile: native legal `SLE-AE1-n5-v1`, 39-bit raw 01 Q, model-generated raw 01 answer+external STOP.
- Only lesson-policy factor: 16 additional r2 high(16..19)/low(0..3) payloads taught with high in first answer position (`first_high`) vs high in second position (`second_high`). Same 120 parent presentations, same 136 total presentations/1408 teacher target-prefix labels per epoch, same overall answer-bit histogram, paired checkpoint initialization, 100 epochs, equal 2200 Adam updates per student. Both arms restart Adam since parent moments unavailable.
- Important preflight limitation: parent 96 distinct lessons in 120 presentations, first_high 112 distinct in 136, second_high **104 distinct in 136**, eight added examples duplicates of parent. This is equal-budget **curriculum-policy**, not pure positional exposure isolated from example novelty; does **not** resolve a unique-coverage confound.

| Seed / arm | Baseline a0..5 /48 | High first-value a16..19 /16 | High-role heldout a20..23 /16 | Entirely unseen a24..27 /16 | r1 exploratory a20..27 /32 |
|---|---:|---:|---:|---:|---:|
| 101 first_high | 48 | 8 | 8 | **0** | 8 |
| 101 second_high | 48 | 0 | 0 | **0** | 0 |
| 202 first_high | 41 | 10 | 4 | **0** | 5 |
| 202 second_high | 48 | 0 | 0 | **0** | 0 |

Per-seed preregistered PASS: first_high val+test >=12/32, improvement >=8/32, and each baseline >=40/48. Seed101 8 vs0 (fails threshold); seed202 4 vs0 (fails both). The value IDs 20..23 already occurred in a *different answer position* before this experiment, so this is limited position transfer, not novel-value copy. IDs24..27 occurred in neither role of the trained course, so failure is a stronger novelty diagnostic.

**New T actual:** PyTorch CPU 4 genuine students (seed101/202 ×2 arms), 10,499 params each, 8,800 new Adam optimizer updates, 563,200 target-prefix presentations, **5,875,302,400 training forward dense MAC** (not backward/optimizer). 512 real free autoregressive outputs, 511/512 correct STOP position, 5,313 forward calls = **55,425,216 inference dense MAC**. Independently, separate NumPy-only implementation loaded all 4 saved F32 weight files and reproduced **512/512 complete 01+S replies**, same 5,313 calls. No big model served as student oracle.

## Source, reproduction, and custody

Companion self-contained ZIP `sle_ae1_first_high_role_transfer_20261114.zip` **SHA256 `0007d749ec257acb2c57cf1a11e5a7ee255dd9455b0f7ae9b5d54d6ee3d9602c`** (277,174 bytes) contains `run.py`, `verify_numpy.py`, exact `prereg.json`, `cases.jsonl`, `parent_course.json`, two F32 source checkpoints, four new F32 trained checkpoints, `raw_cases.jsonl` (512 correct/incorrect responses), `results.json`, per-file SHA256 manifest and full README. Bare Git status/report is **not checkpoint-complete** without companion archive. Recreated ZIP in clean extraction; `sha256sum -c SHA256SUMS.txt`, `python run.py gate`, `python verify_numpy.py` all PASS. Frozen runner SHA256 `3b7deb04c4f2e9050a2d67d29a0a4ed8d4ca196016a0cf0ee995326f3021be8a`; original preflight-failed runner sha `9c912192f94c432c01d625219a4170bab05af047045df5fe2d1587ba06ce98d4`.

Pro UR1 #12, Codex P030–P035, VM, parser and math-bank #5 were read or scoped but **not modified or rerun**. NVIDIA `skipped_unavailable`, no authorized callable runtime, calls 0; desktop Codex 0; Gemini 0; LLM-answer-oracle 0. No auto-merge.

**U:** author requested separate raw-01 NN education and causal generalization. **F:** actual PR40 course/checkpoint, PR52 OOV outcome, Pro/Codex statuses. **T:** this run four new PyTorch trainings plus NumPy replay. **A:** role-specific exposure may help, and controlled distinct-coverage followup is hypothesis only.

[更新] First-role exposure enables limited transfer to previously seen a20..23 but does not yield new-valued a24..27 copies; primary gate fails.
[取代] Equal-exposure first-role teaching alone may establish general unseen-bit-copy.
[原因] Per-seed 8/32 and 4/32 vs frozen threshold12, plus 0/64 genuinely novel-value evaluations.
[狀態] Exact outputs and cost reproducible (high); causal attribution strictly to policy as a whole and internal mechanism (low).

**Next owner:** independent small-NN reviewer; preregister equal-distinct-lesson contrast and fresh student-unknown a/b field, explicitly control duplication, prefix ordering and positions. Preserve old failures, do not tune on this now-exposed test.
