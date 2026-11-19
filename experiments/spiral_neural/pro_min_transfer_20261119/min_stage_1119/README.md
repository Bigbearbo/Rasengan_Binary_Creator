# Staged comparator release

**Prospective supplement** to `pro_min_transfer_20261119_v1`. The registered supplemental rule is in SUPPLEMENT_PREREG.md (Git `172ada5`). The input, selectors, batch stream and Adam implementation are the same as the main study.

The adapter initially mirrors the old choice. The MAX comparator remains fixed until the MIN adapter inverts the choice for both possible input bits. The next optimizer step is the first permitted update to the comparator. The choice threshold is inclusive of zero. The release test is independent of held-out scores. All 1,536 new minibatch steps were completed before evaluation, then all 513 saved states for each seed were scored. There is no standalone recovery phase for this supplementary arm.

| Seed | Gate first met | First open update | MAX and MIN correct on all ideal pairs at gate | Correct for each task on ideal pairs one step later | Both tasks on reused test at 512 | Both tasks on ideal pairs at 512 |
|---:|---:|---:|---:|---:|---:|---:|
| 101 | 55 | 56 | 16,384/16,384 | 15,293/16,384 | 3,108/3,120 | 16,280/16,384 |
| 202 | 54 | 55 | 16,384/16,384 | 15,994/16,384 | 3,076/3,120 | 16,033/16,384 |
| 303 | 54 | 55 | 16,384/16,384 | 15,862/16,384 | 3,104/3,120 | 16,347/16,384 |

On old MAX, the three minima across every validation checkpoint were 1,952/2,096, 1,988/2,096 and 1,956/2,096. Terminal old/new numeric errors on the 8,256 ideal in-range ordered pairs were 40, 151 and 18. Errors on the unrestricted ideal grid had absolute operand gaps of 1–4, 1–6 and 1–2 respectively. On equal ideal pairs the final comparator selected the opposite side to the starting comparator on 20, 2 and 51 inputs; these are correctly excluded from numeric errors. All endpoint counts for both matched main arms are in verification.json.

For unequal operands the two task answers are opposite by design; once the correct adapter relation holds, each wrong comparator decision can cause both tasks to fail on that pair. Exact scores at gate qualification follow from frozen exact comparison, correct polarity and correct copy. The measured part is the speed, extent and persistence of change after thawing.

The staged arm incurred 98,304 additional example presentations, 1,536 adapter updates and 1,373 comparator updates across those same 1,536 steps. The three end-to-end systems each have 1,370 parameter values (including both adapter coefficients), one fixed external task switch, 1,304 MAC per old query and 1,305 MAC per new query. All runs use identical supported width 7. Results are descriptive for the three paired seeds.

## Replay

The directory can be nested inside the main study root or supplied with its path using `--core`. The independent verifier reads the source weights, panels, comparative main endpoints and stored stages. No network access is needed.

```sh
python verify_staged.py --core /path/to/main_study --results results
python staged.py --core /path/to/main_study --output /path/to/new_empty_replay_folder
```

All panels and all observed steps have packed lossless decisions and the two possible seven-bit outputs of the actual neural copy circuit. The data include the full optimizer trajectory, batch rows, metrics by step, bounded-input challenge and full ideal component sweep. The validation script independently derived receiver word outputs and checked all 94,728,528 per-task numeric predictions as well as all 1,536 updates. Maximum independent one-step weight or moment deviation was 4.44e-16. A separate full rerun with the common optimizer reproduced every stored weight, moment and sampled minibatch exactly. An earlier verification attempt used a differently ordered independent formula across hundreds of chained steps; its absolute 1e-10 cross-path tolerance failed at seed 101 step 451. The final independent check evaluates every transition from its exact archived predecessor. No scientific results or original training steps were replaced.

Attribution: U, user proposal to grow while preserving prior behaviors. F, PR133 receiver, handfilled circuit and original panels. A, delayed release controlled by both decision states; this complementary task and its correct task switch were chosen by the experimenters. T, real paired updates, full saved old/new trajectories, verified predictions and separate audit.
