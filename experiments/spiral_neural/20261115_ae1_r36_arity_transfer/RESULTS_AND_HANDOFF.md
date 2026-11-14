# R36 — frozen-checkpoint 01 arity transfer: actual FAIL

**2026-11-15 Asia/Taipei; owner: independent NN worker.** Freeze was published on this branch in commit `ff0ff4d4ddc790fab5489577457a09ae2b5973df` **before any R36 NN inference**. Base: R35 PR #85 head `31890565c38cbca1a33dc04ea18c611abf36694d`. Do not merge this stacked draft without reviewing dependencies.

## One controlled change and evidence boundary

The normal task-header response cardinality `r` changes 1→2; `a,b,c,d`, model weights, codec and checkpoint stay fixed. With r2, the answer is the first six-bit word a followed by six-bit word b and external STOP. Native SLE questions are 39 raw 01 bits using `SLE-AE1-n5-v1`; SLE numeric words have five info bits and terminal 0. Same-length binary6 input/output are controlled non-SLE variants. Four cells: SS (R31), SB (R35), BS (R34), BB (R33), three original seeds 101/202/303 each; **0 new training/updates**.

Fixed tests: `a={14,15,28,29}; b={18,19}; c={1,3}; d=5; r={1,2}`, 32 semantic task inputs, three seeds and four codec arms. Each arm has 48 matched pairs. No exact raw-question overlap with R35's test; the numeric values themselves are **not historically blind**. The complete 32-row bitstream, prereg and source SHA were recorded in the freeze file.

## Actual NN results

**Predeclared joint gate FAIL.** Both matched-codec arms SS and BB fail minimum r2 firstword (12/48) and r2 exact (6/48) even though r1/r2 prefix consistency exceeds 36/48. No post hoc retraining or gate adjustment.

| arm input→output | r1 first/exact, /48 | r2 first, /48 | r2 exact, /48 | r2 secondword, /48 | same first six bits r1/r2, /48 | true-prefix STOP r1→r2, /48 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SS SLE→SLE | 3/3 | 4 | 0 | 48 | 45 | 23→12 |
| SB SLE→binary6 | 2/2 | 4 | 3 | 48 | 40 | 47→31 |
| BS binary6→SLE | 0/0 | 0 | 0 | 48 | 45 | 16→12 |
| BB binary6→binary6 | 5/5 | 4 | 0 | 48 | 40 | 48→23 |

Second word b was correctly copied **192/192** in the r2 generated prefix, yet whole-string exact was **3/192**. The apparently high r1/r2 firstword consistency is overwhelmingly **stable wrong copying**, not generalizable correctness. All four codec arms scored **0** on firstword values a14/15 in both arities; the few firstword successes were from a28/29. Teacher-true-prefix STOP must not be confused with autonomous STOP.

Failure example: SS seed101 `a14,b18,c1,d5,r2`, truth `011100100100S`, raw output `110110100100S`. BB same semantic case truth `001110010010S`, output `01001101001011111111111111111111` (32-character generation limit reached with no STOP). The companion ZIP preserves all 384 raw outputs and errors.

## Actual execution / validation

```text
python r36_arity_transfer.py gate      # PASS frozen source+checkpoint+literal bits
python r36_arity_transfer.py evaluate  # 384 actual PyTorch full autoregressive outputs; gate FAIL
python r36_arity_transfer.py replay    # identical 384/384
python r36_arity_transfer.py numpy     # independent NumPy forward/generation, identical 384/384
```

7,764 actual NN forward evaluations ×10,920 dense forward MAC = **84,782,880 inference MAC** (theoretical, no encoder/CPU overhead); training updates/MAC = **0/0**. Maximum recorded NumPy/PyTorch checked logit error `2.86102294921875e-6`. Clean archive extraction, 128 individually listed SHA256 file checks, static gate and both replays PASS.

**Profile safeguard:** source functions `base/r26_source/r14_source/run.py` and `r33_binary6_control.py` explicitly permit numeric words only 0..29. Values 30/31 were *not* silently inserted: a five-bit payload's representational width does not override the fixed legal profile. Earlier R31–R35 and predecessor work already exposed all remaining a-role unseen-in-train values in probes. This is a fresh **context/arity**, not first-ever unseen numeric value, experiment.

## Public archive vs Git

Complete companion ZIP: `sle_ae1_r36_arity_transfer_20261115.zip`; SHA256 **`e329545a7a2f1df131d530d71cacd585e6a85886737a4291b390151d312a6f9b`**; 130 archive entries, ~2.1 MB. Git only contains freeze, public report and ZIP-requiring verifier/receipt. The ZIP (shared as conversation attachment, not committed to Git) contains source, 12 unchanged historical checkpoint JSONs, exact raw task bits, full 384 results, prior lesson manifests, Python/NumPy reproduction and per-file hash inventory. Git-only checkout is not fully reproducible without obtaining this exact ZIP.

U: user's raw01 SLE small-NN education objective. F: historical R31–35 checkpoints and P030–P035, current Pro PR #12 actual UR1 ANN result (17/36 trained, 0/18 heldout). T: this run's static integrity, PyTorch/NumPy inference/replay and failures. A: changing arity seems to preserve firstword mappings, **including wrong ones**, while known b copies stably in this narrow domain.

**NVIDIA** skipped: zero live calls, no authorized authenticated OpenRouter endpoint in this runtime. **Local Codex** zero; **Gemini** zero. No VM/parser changes, no private chats, API keys or auto merge.

**Next owner — independent NN research:** do not call a30/31 valid under AE1 current profile. Pre-register an approved enlarged numeric profile with new student/checkpoints, or change to an independently untouched *role/task* instead of asserting global novel-value generalization. Jointly gate firstword, whole exact, corrected STOP, retention and compute. Separate translation burden from actual bit-copying/generalization.
