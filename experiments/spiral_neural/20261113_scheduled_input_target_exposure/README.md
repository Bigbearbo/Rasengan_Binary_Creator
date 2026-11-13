# AE1: identical raw data payloads, changing which examples expose new high values as answer words

2026-11-13, independent scheduled small-NN researcher. This is a **new, real PyTorch training** experiment with native 0/1, distinct from UR1, Codex F2, grammar, dictionary, Hamster VM, and PR #38's no-training probe. No neural/LLM teacher supplies answers at inference. All examples are publicly generated synthetic math-free copy tasks.

## Immutable preregistration, before training

Public preregistration committed to isolated branch as commit `bd008367030f6e0f45a658dbf72258c05b9ab183`, runnable source commit `83afa8d1e4198802517283fcac439efe6ebdce30`, both before invoking `python run.py train`. Source branch base is PR #38 head `553817cdad83bb1db2bc6fe2806017628006a1b4`. The archived parent implementation from PR #36 must have SHA256 `05e2d730eecefcb50fa92392697556ffde313f5ecb59c2f4e583aad52e321303`. The prereg is saved verbatim in `PREREGISTRATION.json`; the script's public Git blob SHA1 is `6f4ca26501e80cade582eed7753877d5b03e550e`.

Question: for high vocabulary ID15..23 appearing **at the second data input position**, is training its correct *second answer word* necessary to use the same already-exposed values with new first-word partners? Both student arms see the same multiset of 120 four-word data payloads per epoch. Only the assignment of `r=1` vs `r=2` to a high-second-word class versus a matched low-only class changes. In `HIGH_OUTPUT`, the 36 high/low pairs use r2; in `HIGH_INPUT_ONLY`, those identical pairs use r1. The low-only control class swaps r the opposite way. Both arms contain exactly 60 r1 and 60 r2 questions, hence 1,200 teacher-target examples each epoch. **The r field, answer lengths, answer prefix and label distribution necessarily change**, so this is a matched-payload target-curriculum policy intervention, not identical raw Q or an isolated internal circuit mechanism.

Profile SLE-AE1-n5-v1: legal native Q is 39 bits (`01 + 010 + r(3 info bits + 0) + a,b,c,d (each 5 info bits+0) + END 111100`), ordinary IDs 0..29, controls END30/UP31 reserved, output is the first r complete data words and externally generated `S`. Fixture for s0,v15,r2: `010100100000000011110000000000000111100` -> `000000011110S`. No parser side information supplied to students.

Data split: 36 low `(a,b)` combinations in ID0..5, base 24 train, 6 validation, 6 test by `(a+b)%6`, each r1/r2. Supplement has 36 `(s,v,0,0)` with `s=0..3`, `v=15..23` and 36 matched low-control `(a,b,c,d)` choices. Validation has previously untrained `s=4`, nine high-ID r2 questions; test has previously untrained `s=5`, nine high-ID r2 questions. These combinations are student-heldout, **not research-team-blind**, because earlier rounds examined similar ID and partner ranges. No test-driven early stopping or additional seed was authorized.

Same 160→64 tanh→3 one-hot raw-bit NN, 10,499 parameters, two seeds 101/202 paired across both arms, Adam lr0.003, clip norm1, batch64, 200 epochs, 3,800 optimizer steps and 240,000 target exposures per student, exactly 15,200 steps / 960,000 targets across four students. Training forward dense MAC 10,014,720,000; excludes backward and optimizer costs. Each pair shares initial weight digest and an identical epoch-target permutation. Pre-run gate validates profile, targets, identical input-payload multiset, role counts, split separation, frozen parent and resource budget.

## Actual result — all 4 students trained and assessed

| Seed | Arm | Exposed high-r2 | High-r2 heldout val s4 | High-r2 heldout test s5 | High-r1 diagnostic | Base train/val/test |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 101 | HIGH_OUTPUT | 36/36 | **9/9** | **9/9** | 4/36 | 48/48, 12/12, 12/12 |
| 101 | HIGH_INPUT_ONLY | 0/36 | **0/9** | **0/9** | 36/36 | 48/48, 12/12, 12/12 |
| 202 | HIGH_OUTPUT | 36/36 | **9/9** | **9/9** | 4/36 | 48/48, 12/12, 12/12 |
| 202 | HIGH_INPUT_ONLY | 0/36 | **0/9** | **0/9** | 36/36 | 48/48, 12/12, 12/12 |

**Precommitted gates passed**: adequate in-domain fitting, both seed tests HIGH_OUTPUT >=5/9 and HIGH_INPUT_ONLY <=2/9. The new heldout partner s5 is correct in 18/18 treated versus 0/18 paired controls (val likewise 18/18 versus 0/18). STOP positions all correct on both groups' heldout s4/s5. This is evidence that **supervision at the relevant answer position**, not merely exposure of the token as an input, drives this limited transfer under this training policy.

**Important negative control**: for the exact same high input payload with `r=1` (where the high token must be ignored), HIGH_OUTPUT learners generated the correct full output only 4/36 each, whereas HIGH_INPUT_ONLY did 36/36 each. In both arms the ordinary low-only r1/r2 controls were all 36/36. The good r2 generalization came alongside poor untrained r1 selection on high payloads. This is **not forgetting** of an earlier trained high-r1 skill in HIGH_OUTPUT, because that arm never learned high-r1. The model remains operator/word-value conditional; no universal copy/ignore algorithm proven.

NumPy-only verification (`verify_numpy.py`) did **not** load PyTorch or the training module. It independently deserialized the four float32 checkpoint tensors, verified every parameter hash, then recomputed all **936/936** archived full generated answers, first/second word, STOP cause and 9,577 greedy forward decisions exactly from raw bit strings. Recomputed metrics, costs and raw SHA matched. This is post-run arithmetic corroboration, not a second training run or independently sampled test.

Raw file `raw_cases.jsonl`: **936** cases including correct and incorrect 0/1/S output, SHA256 `2d9416634339f1d42117eafcef70c959613b11c7f2656b3b9a864196122f6217`. Evaluation forward count 9,577; dense MAC 99,907,264. Four float32 inference-only checkpoints and `results.json` published; training optimizer histories and per-step gradient traces **not** archived, so training cannot be proved by inference-only replay alone. One actual deterministic training invocation exited 0 in 9.36 wall seconds in this container; that includes fitting and all evaluation, not benchmarked kernel time.

Run with the parent's PR #36 directory beside this one:

```bash
python run.py selftest
python run.py train               # new training, optional; do not confuse with verification
OPENBLAS_NUM_THREADS=1 python verify_numpy.py   # no training; independently checks archived outputs
sha256sum raw_cases.jsonl
```

## Evidence and handoff

U: the author prioritized actual small 01-bit NN learning, new heldout combinations and resource-controlled experiments. F: PRs #36/#37/#38 and historical P030–P035/UR1 with separate ownership. T: this four-student PyTorch training, pre-run gate, 936 case generation and independent NumPy replay. A: relevant output-position supervision is beneficial here, but exact internal mechanism and any advantage over a plain binary language are unknown. Earlier PRs have seen the numeric/partner-domain choice; this trial is **not a fresh independent scientific holdout** and has only two seeds.

NVIDIA external calls: **0** (no confirmed directly accessible authorized read-only worker in this runtime); local Codex: **0**; Gemini: **0**; large-model student or teacher-answer calls: **0**. All code/data are synthetic and public; no private chat, key or unpublished source included. This is an isolated **Draft** evidence PR stacked on PR #38, with no auto merge and no modifications to the Pro/Codex or VM branches.

Next owner: independent NN reviewer or Codex, **read-only** verification. The next genuinely discriminating experiment should teach both r1 and r2 for the high domain at equal aggregate costs and check whether the r1-high failure can be removed without reducing new-partner r2 accuracy; preregister a genuinely new payload split and distinguish r-rule exposure from input/answer position effects. Do not expand current budgets on the basis of this readout.
