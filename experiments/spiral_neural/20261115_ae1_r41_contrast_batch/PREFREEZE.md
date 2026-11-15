# R41 pre-training freeze — SLE AE1 contrast-paired minibatches

Status: **FROZEN, TRAINING NOT YET EXECUTED at this commit**.

Owner: independent SLE 01 small-neural researcher. Parent evidence: R40 [PR #91](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/91), head `54fe7930a4d4504282f7e4e2617fc87f668d34b8`. No changes to other workers' active branches.

## Precommitted single factor

R38 hard-b-only 10,457-parameter neural student. Identical 136 R38 teaching events and 1,408 next-symbol targets per epoch, 150 epochs, 3 paired seeds 101/202/303, initialization seed+12000, Adam lr0.003, 64 batch, gradient clip1; 3,300 updates per seed, 9,900 total; 633,600 target presentations; 6,918,912,000 theoretical dense forward MAC (excluding backward, evaluation and encoding).

**Only** reorder 24 low/high second-answer-word target-prefix pairs within each epoch so they appear in the same minibatch, preserving every training item once per epoch. Pairs are b18↔26 and b19↔27, same a,c,d, one numeric input bit apart, at output cursor 6–11. Starting schedule is the R38 seeded default RNG permutation, altered through deterministic swaps with nonpair targets. Same model, truth, data, losses, parameters and update count; no LLM oracle used by student.

Legal SLE-AE1-n5-v1, numeric 0..29 only; raw Q `01 + 010 + bin3(r)+0 + 4*(bin5(v)+0) + 111100` =39 binary input bits. Output r 6-bit words and a separate external STOP classification `S` (not a wire bit).

## Frozen test / gate before training

Training: identical R38 136 events. Validation diagnostics: previously tested R38/R40 high-b26/27, known-b18/19, removed-b20..23 and historical 80-case mixed-arity retention; no checkpoint selection. Test: 32 fresh raw 39-bit question strings, 16 untrained secondword b24/25 and 16 trained b26/27 with a14/15/20/21 and nuisance c/d=(4,7),(5,8); 3 seeds =48 each split. The numerical b24/25 values were **already tested in R40**; the new questions are novel contexts, NOT globally blind values. Baseline R38 final checkpoints are reused, not retrained.

Predefined **joint PASS requires all**: untrained b24/25 secondword ≥12/48, familiar high-b26/27 secondword ≥40/48, familiar known-b18/19 secondword ≥44/48, historical retention exact ≥216/240, new-context taught high-b26/27 secondword ≥24/48. Independently report autonomous exact answers and true-prefix STOP. Final checkpoint epoch150 for every seed regardless of result; no continuation or posthoc gate change.

## Immutable artifact receipts

- `r41_paired_batch.py` SHA256 `a3d8ea4d907aa008ab6cfab91e56f5a05ee16b40cfdd3e0d419104ed3fae49d8`
- `r41_prereg.json` SHA256 `fce44082023d484f6390015abc5a0c93e8d319a3b494950837de2bd3c913d7da`
- `r41_manifest.jsonl` SHA256 `1308efe5c747ae823af18be240d258d362c4a7751e2c98ff6177f96fa58cde16`
- Static `python r41_paired_batch.py freeze && python r41_paired_batch.py gate`: **PASS** (136 course events, 24 pairings per epoch, 32 new raw-Q contexts). Static check is not neural training.
- Complete runnable companion file bundle and checkpoint output will be saved separately; this Git freeze **does not claim to carry the model files**.

Sources: U=user's independently scoped SLE NN inquiry; F=R38/R40 actual old scripts, R40 companion ZIP and Codex P030–035/Pro UR1 branch documentation; T=static prereg/input check only at freeze; A=matched contrast batching may change generalization, unverified. NVIDIA=0 (no authorized local OpenRouter worker interface); local Codex=0; Gemini=0.

Next owner: independent NN experimental worker; publish results/failures, actual resources, checkpoint SHA and replay, leave stacked PR unmerged. UR1 Pro #12 has independent completed results; no manifest permission is inferred.
