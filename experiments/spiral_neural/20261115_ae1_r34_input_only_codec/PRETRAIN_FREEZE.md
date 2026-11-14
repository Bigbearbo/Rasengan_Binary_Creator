# R34 — preregistered, NOT TRAINED at this commit (2026-11-15 Asia/Taipei)

Owner: independent small-NN research; based on R33 draft #83 branch `research/sle-ae1-r33-binary6-word-control-20261115`. Worktree isolated; no changes to Pro, Codex, VM, parser.

## One causal factor, frozen before new NN computation

Relative to R31 native SLE-question/native SLE-answer fixed students, change **only numeric word encoding in the INPUT**, from legal `SLE-AE1-n5-v1` word `{n:05b}0` to ordinary `BINARY6-IN-AE1-FRAME` word `{n:06b}`. Native SLE 01 OUTPUT and its STOP S remain unchanged. Input binary6 is a deliberately non-SLE control, not a valid SLE profile. Same 39 raw input bits, 6-bit output word, exact frame, model-owned autoregressive output and separate true-prefix STOP diagnostic. `S/S` R31, `B/B` R33 remain fixed no-retrain controls; new students are `B/S`. This is not whole-language superiority or grammar-blind learning.

Course: unchanged ordered R31 136 appearances, 122 distinct semantic tuples, 1408 teacher-forced targets per epoch, 150 epochs, batch64, Adam lr .003, gradient clip1, seed 101/202/303, matched initial state, shuffled index seed+201000+epoch. 3300 updates/seed = 9900 new updates, 633600 target presentations, each NoFirstMask student 10457 parameters, 10920 forward dense MAC/target, **6,918,912,000 theoretical train forward MAC** excluding backward. Test same semantic 144 cases R33: validation_low 8; test_unseen_low 32 (a=12..15); test_unseen_high 16 (a=28,29); test_near 32 (a=20..23); train_retention 40; test_stop 16. Train a role omits a6/7/12..15/28/29, but historically some values probed. No global heldout-blindness claim. The number values, task labels, and output targets are invariant; only input numeric slot encoding switches. No neural or LLM oracle supplies target truth.

## Prespecified gate (one-sided, **all** required; otherwise FAIL)

Against reused R31 S/S, pooled heldout low+high first-answer 6bit correct gain >=12/144, **autonomous exact+STOP** gain >=12/144, original exact train-retention drop <=15/120, separate correct-prefix STOP test_stop drop <=12/48, and heldout firstword must not decline for at least 2/3 seeds. R33 B/B is reported descriptively but not used to alter this gate. Never select lucky seed or epoch.

## Exact local pre-run cryptographic commitments

Local source `r34_input_only_codec.py` and signed prereg/manifest generated before any R34 optimizer/NN call, static-only command `python r34_input_only_codec.py freeze && python r34_input_only_codec.py gate` => PASS.
- r34_prereg.json SHA256: `000378d3388a41fb9d8a218318a4dc2dd105583eb26a5d4502bcc410a77b8d2e`
- r34_train_manifest.jsonl SHA256: `768b063b5089800c5a3f9f7b4344d5ae506c4580a831a06e588e92dbb588997b`
- r34_test_manifest.jsonl SHA256: `9a17ce735b3262560cc144438c35655983c38665955a827e6befdc1b4dde9c02`
- Frozen local R33 companion SHA256: `2668ecb623c4ea91b36f7e194e0b5f4c561af6a3cb2e240e14c8d815c31b4e13`.
These files and all checkpoint weights will be delivered via a companion artifact; **not** in this commit. This commit is a real pretraining freeze record, not an assertion of runnable Git-only code. Do not execute UR1 #12 without its own required manifest permission.

U user SLE 01 NN learning objective; F R31/R33 saved source/checkpoints and live Git PR review, P031-P035 and Pro #12; T static gate only as of this freeze; A input-bit placement may explain part of joint-codec difference, unproven. NVIDIA=0 (no authorized callable endpoint in current runtime); Codex=0, Gemini=0.
