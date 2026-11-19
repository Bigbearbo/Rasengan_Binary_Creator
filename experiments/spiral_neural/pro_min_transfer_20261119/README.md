# Learning MIN after a handfilled MAX comparator

The original learned 34-bit SLE receiver decodes two 7-bit words. A handfilled comparator chooses a side and a handfilled threshold circuit copies that word. This study gives a new two-parameter adapter the comparator's one-bit decision and a supplied task switch. The starting MIN path produces MAX. All conditions use the same old operand receiver and paired training rows. The frozen and joint conditions have identical inference architectures.

Seeds are 101, 202, 303. Each cell below gives numeric whole-answer accuracy on the 936 previously examined challenge frames after 512 MIN training updates. These are 117 unordered pairs, both orders and four original opcodes.

| Training condition | Old MAX correct | New MIN correct |
|---|---|---|
| Comparator stays frozen | 936, 936, 936 | 936, 936, 936 |
| Unfreeze after the adapter reverses both possible signs | 936, 924, 936 | 936, 924, 936 |
| Train adapter and comparator together from step 1 | 24, 16, 16 | 912, 920, 920 |
| Overwrite comparator without a task switch | 0, 0, 8 | 936, 936, 928 |

On the complete ideal 7-bit pair grid (16,384 cases), the frozen condition has zero errors on either task in every seed. The staged condition has 104, 351, 37 errors on each task, respectively. Staged eligibility first occurred after updates 55, 54, 54; the old comparator was updated on the following step. The always-joint condition finishes above 95% MIN on the earlier raw validation split in every seed, while old MAX is correct on only 104, 96 and 112 cases of 2,096. Restoring only its old comparator yields 936/936 correct MAX and 0/936 correct MIN on the unequal challenge set in all seeds. The simultaneous training solution kept the task adapter's original sign rule and assigned the new function to the old comparator. The frozen condition learned to reverse the sign.

MIN is an especially favorable complementary task. Freezing the original comparator preserves MAX by construction. The observed acquisition speed and whether the optimizer writes a new rule into the adapter or the older module are empirical. A single comparator bit can implement MIN by reversing its choice; the experiment supplies the task switch, copying circuit and selector supervision. This study does not establish a general expansion schedule, discovery of task opcodes, or superiority of the SLE encoding.

A post-hoc census additionally enumerates all 33,024 valid raw n7 frames per seed, including 18,632 outside the earlier panels. The learned receiver misreads 3, 1 and 0 operand pairs. With a frozen exact comparison circuit, MAX is correct on 33,021, 33,024 and 33,024 raw frames, MIN on 33,023, 33,023 and 33,024. This distinguishes exact ideal-input behavior from occasional upstream decoding errors. The census, complete experiment report and archive receipt are available below.

[Chinese report](report_zh.md) · [Raw-frame census](min_census_1119/README.md) · [Archive identity](archive_delivery.json)

## Evidence and replay

The original and supplemental protocols were committed before the respective outcomes: [main](PREREG.md) and [staged release](SUPPLEMENT_PREREG.md). Public source is arranged like the immutable archive. Raw frames, the paired batches, trained weights and individual predictions are archive-only. Use Python 3.12 and NumPy 2.3.5 for a matched rerun. After extraction, run the following in the archive root:

```sh
python min_transfer_20261119/replay.py
OPENBLAS_NUM_THREADS=1 python review/independent_replay.py min_transfer_20261119
python min_stage_1119/verify_staged.py
python min_census_1119/census.py --verify
```

The main audit independently decodes 43,176 source evaluations, checks all 5,376 optimizer batches, every registered weight and Adam moment, and all 4,431,744 checkpoint/panel rows. A separate post-hoc audit uses mathematically equivalent floating-point expressions on the joint arm. Exact end values vary, but severe MAX loss persists in all three seeds. The raw-frame challenge is reused from PR133 and the exhaustive grid is a separately labeled component test. See the [main replay note](min_transfer_20261119/README.md), [independent audit receipt](review/scientific_replay.json), and [staged metrics](min_stage_1119/results/summary.json).

For the whole-file SHA, member CRC, member SHA and fresh extracted replay, keep the [archive verifier](replay_archive.py) and [receipt](archive_delivery.json) together, then run `python replay_archive.py sle_min_transfer_20261119_v1.zip`.
