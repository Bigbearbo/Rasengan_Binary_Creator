# R28 SLE-AE1-n5-v1 — immutable pre-training freeze (2026-11-14)
Owner: independent scheduled native-01 NN researcher. Parent evidence: [R27 PR #77](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/77), head `dcd5d9ccf9f179f4030630879ed89e3903a21823`. Other streams P030–P035 / UR1 and Hamster VM are **not** re-executed.

## Unique factor and cost
Control **R27 saved weights** vs new R28: change only **12** of R27's 24 r1 firstword-high lesson tuples `a=24..27` to `a=20..23`; preserve r,b,c,d, episode count, answer target counts, architecture, initialization and Adam order. Original 24 slots occur at indices `0,2,...,46`. Reassign at exact zero-based course indices `8,10,12,14,24,26,28,30,40,42,44,46`: a becomes `20+j%4` for slot enumeration index j; remaining 12 are unchanged high. Result: each a20..27 occurs exactly 3 times among 24 high-/near-high r1 slots, as opposed to 6 each a24..27 in R27. Fixed 136 lesson events (r1=60, r2=76), 1,408 teacher target positions per epoch.

Profile **SLE-AE1-n5-v1** (do not apply to UR1): 39-bit question `01+010+r3+0+4*(five-bit word ID+0)+111100`, IDs 0..29 (not 30/31). Response: 6-bit a, optionally 6-bit b for r2, then external STOP S; S is not a SLE token. Student sees native 01, external deterministic codec provides exact supervised targets (not an LLM/large-model student's answer oracle). R20 dual-routed hard route stays unchanged: **this does not test unassisted discovery of input routing**.

3 seeds **101,202,303**; from matched `seed+12000` initial state. 150 epochs, 1,408 targets per epoch, batch64 shuffled by `np.random.default_rng(seed+201000+epoch)`; Adam lr .003, grad clip1, exactly 3,300 updates/student and 9,900 total, 633,600 targets. Model **10,457 parameters**, nominal **10,920 forward dense MAC/target**, total new training forward **6,918,912,000 MAC**, excluding backward and wall-time accounting. Immutable R20/R27 controls are loaded, *not retrained*.

## Data, bitstreams, and split
Complete frozen 136-row native 01 JSONL, including exact answers, deterministically generated before any new inference/training:
`validation_taught_high`: 8 r1 Q (a26/27 × b16/17/20/21, c0 d1);
`test_unseen_high`: 16 r1 Q (a28/29 × b16/17/20/21 × [c0 d2 or c2 d3]); a28/29 absent from both curricula, Q/context new to R27 experiment;
`test_near_transfer`: 16 r1 Q (a20..23 × b16/17/20/21, c1 d2); R28 *has taught those a values*, so this tests new pair/context transfer **not unexposed values**;
`legacy_near_diagnostic`: previous R27 near_high 16 Q (a20..23,b18/19/22/23,c0d0), already reviewed and *not* primary;
`seen_baseline`: 48 frozen R20 Q; `taught_high`: 32 frozen R20 Q, both mixed r1/r2; no r2 position6 mistaken for STOP. All 136 Q legal and unique and all novel test Q not repeated exactly in training.

Examples: `010100010110100100000000000000010111100` -> `110100S` (validation a26,b16); `010100010111000100000000000000100111100` -> `111000S` (new unseen-high a28,b16,c0d2).

## Precommitted composite success gate (ALL mandatory)
Against the exact saved R27 checkpoints:
1. Aggregate 3-seed new near-transfer firstword correctness must improve **at least +8/48**.
2. Aggregate new unseen-high a28/29 firstword must decrease **at most 6/48**, with no individual seed losing more than 4/16.
3. Aggregate new unseen-high true r1 correct-position STOP must decrease **at most 6/48**.
4. Each seed must lose at most **4/48** complete exact answers on seen_baseline and **4/32** on taught_high.
Firstword, full exact, true r1 STOP, old diagnostic examples and per-seed counterexamples are recorded whether PASS or FAIL. We will **not** revise gate after seeing results. If a ceiling occurs, report it, do not reframe.

## Immutable artifacts and provenance, pre-training
`r28_runner.py` SHA256 `606b7e3446c02fc00169e379988b99cd181e048a57877ef763f999aed38ed8a2`
`manifest.jsonl` SHA256 `e935dd9bc3836168ea93ce3a50860a25876c821b939172d000e87660b76cd9c9`
`prereg.json` SHA256 `8ca9f71039e207834f03bd3931885ac10c36c1be9b8a0ded0af0fed4317ed704`
Training course canonical JSON SHA256 to be matched by prereg. Source R27 ZIP SHA256 `73c13754de01739328547cda8dbe6f83c4aa105013b0a1a251681f57d15be0e0`; frozen R26 nested ZIP SHA256 `2c945803a5336820a5f17c72daaaa7cd1a9a46f9b9299c0fc0af87d1cbe115e3`. Original checkpoint SHA and course SHA registered in `prereg.json` and must pass static local gate **before** execution. The full three files and all source/checkpoints to be released with result evidence ZIP; until then this Git commit is the immutable **hash commitment** and deterministic design, not itself a complete executable checkpoint archive.

U: author requests independent native 01 small NN learning. F: R20/R27 original saved weights and P030–P035 reports. T (at freeze): static generation and local gate only; **0 R28 training updates so far**. A: rehearsing a20..23 may protect neighboring performance but sacrifice a28/29 extrapolation. NVIDIA unavailable as an authorized live worker in this runtime: `skipped_unavailable, actual_calls=0`; local Codex calls 0; no secret/private source uploaded. No automatic merge.
