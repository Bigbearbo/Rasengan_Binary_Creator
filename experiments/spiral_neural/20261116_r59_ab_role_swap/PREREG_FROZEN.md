# SLE AE1 R59 — Pre-inference frozen experimental design (2026-11-16)

Status: **FROZEN BEFORE ANY R59 NEURAL FORWARD**. Owner: independent native-01 small-neural researcher. Source/parent: Draft PR #109, exact base head `03768beeb69901d71cabf8662f6b2e6c780e943c`. Isolated output path `experiments/spiral_neural/20261116_r59_ab_role_swap/`; do not edit Pro/Codex/VM/parser paths. No automatic merge.

## One variable and model control
Counterfactual **exchange entire first and second 6-bit encoded operands `a,b`**. The control is the same r,c,d, same model/weights/seed/STOP mechanism and answer scheme; the correct gold answer must update from `a,(b)` to `b,(a)` with role r held fixed. Thus NOT an irrelevant-input invariance trial. Novel exact question pairs, **not new values/semantics**. Test whether independent models can exchange source roles; do not infer mental mechanism solely from scores.

Fixed R52 learned 8 cursor gate / R55 extra 8 value slopes / R56 same-budget 8 static gate, each seed 101/202/303, 10465 model parameters (R55 also 8 frozen buffer scalars). Source from self-contained R58 ZIP, SHA256 `ec3245dacfda55f08c9d0b4ea8c345e4d992ee8821169abbc75944e6dd985b62`; runner and source checkpoint hashes pinned inside local `r59_prereg.json`. No retraining, optimizer updates 0, training MAC 0, theoretical forward dense MAC 10920/call.

Legal `SLE-AE1-n5-v1` **test domain 0..29** (30/31 NOT treated as automatically legal): raw Q `01+010+bin3(r)+0+4*(bin5(value)+0)+111100` = exactly **39 bits**. Output r=1: `bin5(a)+0+S`; r=2: `bin5(a)+0+bin5(b)+0+S`, where `S` is external stop action, *not a SLE word*. No LLM computes student answers. Gold task generator is deterministic and separate from model.

Historical train: **136 lesson events / 1272 nonSTOP teacher-forced prefix targets**; not changed, exposed. Exactly **48 matched operand-swap pairs / 96 distinct new Q**: validation 16 pairs, test 32 pairs. Each split balances r1/r2 and low-high/high-low. Pair generation uses numpy.default_rng(seed=59016), drawing low=randint(0,6), high=randint(24,30), c,d=randint(0,30), choosing a,b in stratum order; skip exact Q appearing in archived source or previously chosen pairs. Historical scan found **1,932 distinct exact 39-bit Q** and all 96 fresh ones are disjoint. All train/evaluation number values are previously encountered, so this is an unseen *combination* / role-exchange probe, not numerical OOD.

Source-based SHA256, frozen before forwards:
- local `r59_role_swap_frozen.py`: `7fd87f9c70fffebcc10a869deda08d6e4699a73a58a4aeb32c1fb7f875dc44bd`
- local `r59_prereg.json`: `bc5bb504c54899602b23737e608e05d4f0f8af6059f3a4ac33f78384eec0add4`
- local `r59_manifest.jsonl`: `bfa77a5ebbf15a9876a0ed784853d9cbc23bd325199345f323685dc30b06c21b`.
- Complete checkpoint and runner file SHA table saved in local prereg JSON, to be included as-is in finished artifact.
- Static command `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r59_role_swap_frozen.py freeze` **PASS**, 48 role-swaps/96 valid unique 39-bit Q/0 historical exact-Q collisions/source hashes all pass; no R59 model inference used at prereg.

## Prespecified *joint* gates — ALL required to claim R59's comparative hypothesis successful
1. All 96 legal unique Q, 48 exact a/b swap pairs, new exact Q and updated gold correct;
2. R55 test both-correct full-answer seed-pairs >= R56 + **6**;
3. R55 test full exact incl STOP >= R52 + **8** (test each model 192 generated answers);
4. R56 test full exact >= R52 minus **4**;
5. R52 each seed test contains >=1 fully correct r2 pair;
6. PyTorch AND independent NumPy replay 864/864 actual complete outputs.

Also report both-first-correct pairs, r2 both-second-correct pairs, raw first+second output permutation, per-seed losses, STOP/cap, actual fwd calls. Do not tune on validation/test after seeing results; no hidden continued training. Preserve all failures. U=user research direction; F=archived source; T=local static preflight only until execution; A=comparative hypothesis confidence LOW.

NVIDIA: no directly callable authorized local worker/key in this execution environment; skipped, actual calls 0. Codex 0, Gemini 0. These are NOT students or oracles.

Next owner: independent NN researcher. Correct replay/negative results must be retained, plain-binary matched-budget comparison remains separate unexecuted experiment.
