# SLE NN R30 — removing firstword hard mask, real 3-student trial (2026-11-15)

**Preregistered joint gate: FAIL**. Independent SLE-AE1 native 01 NN experiment; NOT Hamster VM, parser, Pro UR1, or Codex P030–P035 rerun.

## Sources and prior freezing
- Git frozen before any new NN training/inference at `3579a225916de557786de91b159597e030c3ea63`. Static source audit found an erroneous “112 unique R28 course tuples” assertion. Verified **118** distinct tuples in the actual 136-event original source; correction made and published **before** training at `7bef5eb1cff73b818363cdb894416841dfc85369`. Both original freeze and erratum preserved. Original course, gate and raw input manifest unchanged.
- R28 original real checkpoints/source are the control, PR #78; R29 PR #79 documented why firstword `b,c,d` probes were confounded by hard masking. Original R28 ZIP SHA256 `bdb5d47ec9dcdef851247136c85acbf7923f4d9c9631b9b5357ccbe699d562dc`.
- Git AGENTS.md, GIT_RESEARCH_HANDOFF_20261113.md, live Pro UR1 #12 (actually trained, negative), shared-bank #5 and Codex P030–P035 evidence reviewed; no duplicate runs.

## Exactly one experimental difference

R28 `DualRoutedStudent` firstword (cursor0…5) can only access word `a`. R30 removes **only** that hard firstword mask, allowing firstword to access `a,b,c,d`; keep identical neural layers (10,457 parameters), `r2` secondword mask and STOP logic, matching per-seed random initial weights, R28 exactly ordered 136 training presentations / 1,408 targets per epoch, same Adam/shuffling/optimizer, 150 epochs, and 3,300 updates per seed. Seeds 101,202,303, **9,900 genuinely new Adam updates**, 633,600 training target presentations, training forward 6,918,912,000 theoretical dense MAC excluding backward. One forward 10,920 dense MAC; this is not an end-to-end wall-clock or training total FLOPs equality test.

Legal `SLE-AE1-n5-v1`: original **39 raw 01 input bits**, `01+010+r3+0+4*(5bit_ID+0)+111100`; first answer 6 bits, r2 adds second answer word, external `S` STOP (not a lexical SLE word). Deterministic offline codec produced supervised targets and evaluated model-generated answers; no teacher/LLM oracle used inside the student's inference.

Frozen manifest: 168 unique questions, including 4 validation, formal 24 student-unseen `a=28/29`, 32 near-high `a20..23` unseen full contexts, 24 one-word STOP, 4 r2, and existing R28 48+32 retention cases. The two formal unseen numeric values were already researcher-seen in R27–R29, not researcher-blind. Repeated contexts do not count as independent unseen word values.

## Raw result — control R28 → trained R30

| Seed | Unseen firstword /24 | Unseen exact answer /24 | Near-a firstword /32 | Correct-position STOP /24 |
|---|---:|---:|---:|---:|
| 101 | **24→0** | 9→0 | 32→2 | 20→20 |
| 202 | **0→16** | 0→8 | 32→18 | 10→16 |
| 303 | **24→4** | 10→4 | 32→12 | 23→24 |
| **Total** | **48→20 /72** | **19→12 /72** | **96→32 /96** | **53→60 /72** |

Old retained exact full answers **240/240 both arms**. Composite preregistered gate required unseen firstword gain≥6/72, unseen exact gain≥6/72, near firstword loss≤6/96, retention exact loss≤12/240, STOP correct-prefix loss≤6/72. Observed differences were **−28, −7, −64, 0, +7 respectively → FAIL**. The seed202 partial improvement must not be suppressed; neither should the dramatic 101/303 regressions.

Representative real failure: seed101 r1 a28,b16,c0,d4, Q `010100010111000100000000000001000111100`, expected `111000S`, generated `111110S` (firstword wrong). Seed202 r1 a28,b16,c2,d5, Q `010100010111000100000000100001010111100`, expected `111000S`, generated `11100010010011111111111111111111` (STOP failure). All errors are recorded without cherry-picking.

Under the artificial R28 firstword mask, varied b/c/d *cannot* change firstword by design (one output per a/seed). In the unmasked R30, unique firstword generations for heldout a28/a29 differ across contexts (seed101: 2/2, seed202: 3/3, seed303: 5/3). Thus there is genuine context sensitivity, but much of it is counterproductive. No claim of general rule learning or SLE-vs-plain-binary advantage.

## Executed verification, artifact, owner

- Actual local CPU PyTorch trained 3 students; all three **new full weight files** saved. 1,008 complete raw01 neural generations, 16,149 forward calls, inference theoretical dense MAC **176,347,080**.
- Exact saved-weight PyTorch autoregressive **replay 1,008/1,008**, all three new checkpoint SHA passes. Independent NumPy reimplementation independently matches **1,008/1,008 generated strings** and prefix/STOP logits within **2.861023e−6**. Clean ZIP extract: **65/65 contents SHA pass**, static preflight, full replay and independent NumPy PASS.
- Companion ZIP (original control weights, all 3 new checkpoints, source, prereg, manifest, 1008 raw outputs, independent auditor, failure examples) named `sle_ae1_r30_no_firstword_mask_20261115.zip`; SHA256 **`22747e62238b527bb6c1ce7fe1bb0f6352cf970495b90c74e37a86700809d714`**. This ZIP is attached in the experiment conversation, **NOT uploaded to Git**; do not pretend the Git text-only PR is sufficient for independent checkpoint replay.
- Runnable from ZIP root: `python r30_runner.py gate`; `python r30_runner.py replay`; `python r30_numpy_audit.py`; `sha256sum -c SHA256SUMS`.
- Frozen `r30_runner.py` SHA256 `e69dda36723ce435887715539728bfe8eff70f522dbbeef45acc9aeb1e353630`; `prereg.json` SHA256 `021684c38ff7a30fac9aece307571b3c5460dc9f7550e7b999e6944c5851f760`; 168-case raw manifest SHA256 `b8a7aa71b1921e28b8fc85f61e2ae16c5856dbd13d59d612bd506bbb7d2eac64`; 1008 raw generated case file SHA256 `f1fabf4abd7d9d6dfdcae3fbed3cd340dd40f1d52d96dbf641e78a8160b1e0e9`.
- New checkpoint SHA256 by seed: `101=79aa059bfd228bd25ddb54e097d288bf7ddbd2f7327baf2d5d059852b527fd6b`, `202=12474280aa26fc0fc4bce3721ff2c0685aad655207a6cc56c1910986f520e1f2`, `303=8bbb54300bbbfc9c6ed794d55f142ed74ecc79e9ec0dea486975d0ee2e8d6e7f`.
- U: author independent SLE01 neural learning/generalization and measurable education priority. F: R28 real source/checkpoint, R29 diagnostic, Pro/Codex prior evidence. T: corrected static source audit; 3 real newly trained student weights, 1008 raw inference, cross-framework replay. A: a narrow structural prior appears helpful for some firstword bit interpolation under finite training; different neural optimization/irrelevant context may explain regressions (**not** proved universal).
- NVIDIA `skipped_unavailable`: no authorized live reviewer worker/credential in this runtime, **0 actual calls**. Local Codex 0, Gemini 0. No secrets/private conversation/Git branch overwrite or auto merge.

**Next owner:** independent NN researcher. Design separately frozen, equal-budget matched *plain binary* comparison with equivalent structural prior, or a single-factor context-nuisance generalization study on truly unseen value patterns. Do not selectively extend the R30 failure with more updates or change the preregistered gate. Keep R30 artifacts and negative results.
