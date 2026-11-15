# SLE 01 NN R59 — Actual a/b role-swap experiment and next owner (2026-11-16)

**Status: real 864 raw-01 model generations; prespecified joint 4/6 → FAIL.** Independent NN researcher. Prereg was remotely committed **before any R59 neural forward**, commit [`be048730`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/be048730a0abef5fc0914a784714e6ec317cc8dd). Source was exact head of prior Draft PR #109: `03768beeb69901d71cabf8662f6b2e6c780e943c`.

## Frozen setup

Single intervention: exchange the entire two legal 6-bit SLE numeric words `a` and `b`; keep instruction r, remaining c/d, weights, seed and STOP scheme identical. Gold output is recalculated for the new role; this is *NOT* a nuisance-invariance experiment. The comparison is among frozen R52 (learned cursor), R55 (8 value-conditioned slope parameters), R56 (equal-extra-updates static source weights) trained students, three seeds 101/202/303 each. **No new training updates**, and no teacher oracle generating student answers.

Legal `SLE-AE1-n5-v1`: integers 0..29, not an invented extension to 30/31. Q is 39 literal bits `01+010+bin3(r)+0+four*(bin5(value)+0)+111100`; role r1 target `bin5(a)+0+S`; role r2 `bin5(a)+0+bin5(b)+0+S`, `S` external stop action. Manifest numpy seed 59016. 48 matched swapped pairs: 16 pairs validation (32 questions), 32 pairs test (64 questions); each role and operand-stratum balanced, all 96 exact questions disjoint from 1932 existing archived exact questions. **Not** novel number/semantic domain. Historic 136 lesson events and 1272 non-STOP prefixes are unchanged. Each student 10465 model parameters (R55 also 8 frozen auxiliary buffer scalars), zero new training MAC. Theoretical forward cost 10920 dense MAC.

Immutable local files SHA256: `r59_role_swap_frozen.py=7fd87f9c70fffebcc10a869deda08d6e4699a73a58a4aeb32c1fb7f875dc44bd`; `r59_prereg.json=bc5bb504c54899602b23737e608e05d4f0f8af6059f3a4ac33f78384eec0add4`; `r59_manifest.jsonl=bfa77a5ebbf15a9876a0ed784853d9cbc23bd325199345f323685dc30b06c21b`. Full source-checkpoint SHA table is in prereg JSON. R58 archival source ZIP SHA256 `ec3245dacfda55f08c9d0b4ea8c345e4d992ee8821169abbc75944e6dd985b62`.

## True results, 3 seeds aggregated

| measure | R52 | R55 conditional | R56 static |
| --- | ---: | ---: | ---: |
| Validation full exact with STOP | 39/96 | 33/96 | 37/96 |
| Test full exact with STOP | **75/192** | 70/192 | 73/192 |
| Test pair BOTH exact with STOP | **21/96** | 19/96 | 20/96 |
| Test first output word exact | **85/192** | 80/192 | 83/192 |
| Test r2 second output word exact | 77/96 | 78/96 | 78/96 |
| Test r2 free two-word swap relationship | 13/48 | 11/48 | 12/48 |

R55 vs R52 on the same 192 test answers: **5 formerly correct become wrong, 0 formerly wrong become correct**. R56 vs R52: 2 lost, 0 gained.

Failure record: seed202, r1, a=2, b=28, c=10, d=15, swap=1; Q `010100010000100111000010100011110111100`; correct `000100S`; R52 and R56 `000100S`, R55 `000000S`. All examples, including R55 failures and non-triggers, remain in raw JSONL.

**Preregistered gates: 4/6 PASS, overall FAIL.** R55 failed (a) test paired-both-full must exceed R56 by ≥6 pairs and (b) test full-exact must exceed R52 by ≥8 questions. Static legality, R56 retention vs R52 ≥−4, R52 each seed ≥1 paired-correct r2 test, dual replay all PASS.

Total: **864 new free raw-01 student generations**, 8715 actual forward calls, **95,167,800 theoretical forward dense MAC**, **0 training updates**. Every student output reproduced PyTorch **864/864** and independent NumPy **864/864**, sample maximum absolute logits discrepancy `1.9073486328125e-06`. Standalone stdlib semantic/bit/gold/swap/split/sha/result audit PASS. Test STOP vs cap for each arm: 191 STOP / 1 cap; validation 96 STOP. Clean portable archive 398 files, 396 hashed files all verified.

Run from portable archive's `r56_workspace`:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r59_role_swap_frozen.py freeze
# The Git prereg commit and remote check happened HERE, before new inference.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r59_role_swap_frozen.py eval
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r59_role_swap_frozen.py torch
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r59_role_swap_frozen.py numpy
python verify_r59_public.py
```

Complete portable ZIP (not uploaded into this Git PR), `sle_ae1_r59_ab_role_swap_20261116.zip`, **SHA256 `f31579c430a607c74fcfd4af0a69d894af5ce1eac11f133717fb2ff2b6199017`**, is available in the originating conversation artifact. Do **NOT** claim Git-only neural replay or that a zip name proves its bytes are on Git. Git stores the frozen prereg and this report; program, checkpoints, full replies and checksums are in the separately verified portable ZIP.

## Attribution, boundaries, next owner

U: user requested isolated raw-01 student-learning research, legality, prereg and negative results. F: earlier immutable R52/R55/R56 checkpoint source and Pro/Codex P030–035/UR1 separate experiments. T: this run's 864 generated neural outputs + independent replays and audit. A: hypothesized advantage from value-conditioned routing; **unsupported** on this role-switch workload. Training history & output errors do not prove mechanistic explanation.

No local authorized callable NVIDIA worker/key: NVIDIA **0 actual requests** (skipped), local Codex **0**, Gemini **0**. Not merged, no edits to Pro UR1, Codex, Hamster VM, parser, protocol or shared curricula.

**Next owner: independent neural research worker.** Avoid further tuning on exposed 0..29 domain. Either protocol owner first authorizes a new legal numeric profile for genuinely unseen values, or freeze a matched neural **from-scratch** ordinary-binary baseline under equal train/val/test and full costs. Do not repurpose SLE-trained checkpoints as ordinary-binary students. New comparisons must preregister independent of this observed failure.
