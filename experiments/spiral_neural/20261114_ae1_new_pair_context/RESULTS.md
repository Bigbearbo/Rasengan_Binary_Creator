# SLE AE1: new answer-word pair × irrelevant-context transfer (2026-11-14)

Work ID `SLE-AE1-NEW-PAIR-CONTEXT-20261114`. Owner: independent scheduled NN investigator. Status: **primary preregistered gate PASS** for the two `balanced_c` students, but limited to high-word values already seen in the historical curriculum. No new training. This is a constrained diagnostic of genuine frozen neural students, not the UR1 upgrade-notice work, parser, VM, or a proof of a universal copy algorithm.

## Provenance and preregistration

- **U**: study SLE raw-01 neural input/output, education, generalization under controlled costs, separate from Hamster VM/parser.
- **F**: `Bigbearbo/Rasengan_Binary_Creator`, PR #48 head `acb2947e558addfac1912870d61be439df4d9b7f`, parent evidence ZIP SHA256 `de9faa95e2ba8d178b0a52712a6aa0259894a04147d4894eab407b270ef48e4d`. The four 10,499-parameter F32 checkpoints originate in PR #44/#45 and were independently checked for file and tensor hashes. Prior P030–P035 and PR #49 are different completed workstreams. UR1 Pro #12 has separately reported real neural results; no UR1 training was authorized or attempted here.
- **A (before forwarding)**: mixed-c training might preserve r2 behavior on untrained a/b role-pair combinations. C parity and d invariance seen in prior a4/5/b26/27 panels might depend on context.
- **T**: Git published `PREREGISTRATION.json`, `experiment.py`, `verify_numpy.py`, `cases_preregistered.jsonl` in new branch before any new NN forward. The original Git content transport dropped one trailing newline in each file; the *same* missing newline was restored in each file before evaluation, restoring the preregistered runner SHA256. Final frozen Git commit `6e0a06c894edf28cb710dc0f6b8153579d2c845f`; code SHA256 `cad31ad92d3ad2f8a3262129ce5ef4617aeb99e9223fd7f8986c9c076ef5186f`. Static preregistered preflight ran (0 NN forward) before Git freeze, then again immediately before the single official inference run.

## Fixed profile and question sets

SLE-AE1-n5-v1; Q39 = `01 + 010 + 010 + 0 + [5-bit data + 0]×4 + 111100`. Valid data ID 0..29, reserved END30, UP31. Parameter r=2; answer is the first two intact six-bit data words, then student-generated S, **not** teacher-forced or forcibly stopped. Model input is one-hot position × 0/1 from its own generated prefix, L80/H64, logits 0/1/S, greedy cap32. Four genuine F32 states from seeds 101/202 and arms `frozen_c1_control` vs `balanced_c`; no RNG reseeding or new optimizer updates.

All 384 frozen rows enumerated before inference (96 unique native 01 questions; each of 4 students gets all 96). `a ∈ {0,1,2,3}`, `b ∈ {18,19,22,23}`, `c ∈ {0,2,3}`, `d ∈ {0,8}`, with unchanged output for every c/d intervention. Historical PR40 had r2-teaching for exactly the 8 of 16 a/b pairs where `(b−15+a)%2=1`; other 8 pairs not shown with r2, although their word values were previously used. This is **within-vocabulary recombination**, not out-of-vocabulary generalization. Historical training/validation/test unchanged. In this diagnostic, a0/1=train-domain probe, a2=validation-probe, a3=test-probe labels indicate provenance slices only: all values a0..3 were historically used in training, so this is **not a genuine independent heldout a**. Dataset Q and labels, model file hashes and independent benchmark replay saved in archive.

One scientific factor evaluated: transfer to previously **untaught r2 (a,b) pair** versus taught r2 pair at fixed checkpoints. c/d changes are preregistered nuisance-context audits, not chosen in response to generated results. A priori primary PASS requires separately for **each** balanced-c seed: ≥40/48 exact on untrained r2 pairs; ≥24/32 exact for c2/3 across d0/8; and 24/24 identical outputs between d0 and d8. Any single failure would mean FAIL. No threshold change after results.

## Actual full-answer results (including STOP)

| Student | r2 already taught pair | r2 untaught pair | c=2 on untaught pairs | c=3 on untaught pairs | untaught d0 vs d8 invariant |
|---|---:|---:|---:|---:|---:|
| c1-control seed101 | 40/48 | 40/48 | 16/16 | 8/16 | 24/24 |
| c1-control seed202 | 40/48 | 40/48 | 16/16 | 8/16 | 24/24 |
| mixed-c seed101 | 48/48 | **48/48** | 16/16 | 16/16 | **24/24** |
| mixed-c seed202 | 48/48 | **48/48** | 16/16 | 16/16 | **24/24** |

Balanced-c primary **PASS for both seeds**; all balanced-c 192/192 whole replies exact, including 96/96 untaught-pair replies. Older frozen-c1 controls achieve 160/192 exact. Aggregate 352/384. All 384 STOP positions proper. 384 genuine PyTorch generated replies, 4,992 forward calls, 52,076,544 dense inference MAC (10432/forward), 0 new optimizer updates, 0 train targets. NumPy verifier independently decoded the checkpoint tensors and computed all 4,992 one-hot+tanh logits: **384/384 full replies and 4,992 forward decisions match**, with no original PyTorch runner imports. This independent replay doubles actual evaluation computation but is not 384 new scientific samples.

## Negative findings, failed examples and confounds

The 32 failed full replies occur **only** for c1-control students, `c=3`, `b ∈ {22,23}`, across both a and d. Example seed101: a0/b22/c3/d0 expected `000000101100S`, actual `000000111000S`; a0/b23/c3/d0 expected `000000101110S`, actual `000000111010S`. These errors are about the second answer value; the first answer word and STOP position are intact. In this new a/b context, controls pass c2 yet fail some c3 cases. Historical PR46 controls were observed to fail c2 and pass c3 on **different** a/b values. Therefore the earlier apparent third-word parity rule is **not a context-independent law**.

One other failure of generalized invariance: frozen-c1 seed101, a0/b22/c3, changes its **wrong** answer when only fourth data word changes d0→d8, from `000000111000S` to `000000111010S` (same correct target `000000101100S`). In PR48 the c1 controls made **no** d-response changes in a4/5/b26/27; this is a concrete counterexample to extrapolating that result over all contexts. All balanced-c responses (96/96 paired d comparisons across seeds) stay identical and correct in this limited domain.

These r2-untaught a/b pairs are not new word values; the a and b symbols both occurred in older training, and researcher selected a limited domain with prior insight. So even 96/96 is **neither** a fully researcher-blind test nor demonstration of general algorithmic bit copy, longer strings, new n-width, SLE advantage over plain binary, arithmetic understanding, nor neural architectural growth. The old c1 arm and mixed-c arm differ in training and inherited states: this frozen-state probe does not prove which isolated training change *caused* the difference.

## Reproduction, integrity, cost

From this unmodified companion archive, with Python, NumPy and PyTorch installed, run in a **new extract directory**:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python experiment.py preflight
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_numpy.py
```

`experiment.py run` would repeat the same 384-PyTorch test and overwrite only its extracted directory; do not rerun in prior evidence roots. The archive preserves raw 384 original 01 queries, answers, all errors, metrics, all four genuine weight JSONs, actual PyTorch runner, NumPy verifier, exact pre-inference manifest, and SHA256SUMS. The Git version is byte-for-byte restored to match the runner/pre-reg hashes. Numerical deterministic settings are for this CPU environment; different BLAS environments may change marginal logits; exact evaluation is certified by this run's independent NumPy check.

NVIDIA `skipped`, 0 actual calls: no authorized credential/worker available; only public non-sensitive reviewer tasks permitted. Local Codex 0 calls; no local Codex session available. Gemini 0 calls. No LLM/teacher oracle computed student answers. Did not modify any existing Pro/Codex/VM branch or auto-merge. Only public synthetic data and models appear here.

**Next owner:** Independent NN/Codex reviewer. First verify the heldout-pair exposure ledger from PR40 vs this pre-specified panel; then consider a new preregistered truly out-of-vocabulary bit-combination or longer/variable r test with train/test split frozen before any model fitting. Do not re-tune on the now-seen c0/2/3/a0..3/b18..23 observations. An independent OOV challenge would be more discriminating than repeatedly checking already learned word values.
