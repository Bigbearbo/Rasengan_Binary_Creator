# MAX → MIN handfill/learning transfer

Run `pro_min_transfer_20261119_v1`. The three-arm specification was committed as `e9ee14f24031265f154890fdbf4e00a002b208de` before the first optimizer update. Preregistration file SHA-256 is `51ca6bcaab3b8182b9360e6cb661efbd5a998b3fdbf863aa638338e135d52d49`. See the accompanying separate supplement for a staged-unfreeze arm.

## Replay

Extract the complete research archive. From this directory, run `python replay.py` in a Python environment with NumPy. This regenerates every optimizer trajectory in memory, runs the original receiver on raw bits, verifies 32,768 routes of the threshold copy network against the operand-copy definition, and checks all stored hard predictions, full-word accuracies and changed-output counts. The bundled inputs and outputs suffice offline. For a new fit in a separate directory run `python study.py --output /tmp/min_transfer_fresh`. The output directory must be new. The prepared source directory is already present. Optional `prepare.py PR133.zip` reconstructs that directory only in an empty copy, starting from the exact PR133 archive. No network or GPU is needed. The original run used Python 3.12.14 and NumPy 2.3.5.

## Data and model

The inherited directory contains PR133's exact legal Fable W n7 raw bits, split by unordered pair, the three trained PR130 receivers, source code and provenance, original MAX starting checkpoints, and the threshold copy network. Each source is rerun from its raw 34 bits; the hard bit outputs and row IDs are checked against the original cache hashes. Only training targets and scoring use the true operands. The challenge was already inspected in PR133 and is disjoint from this training set. It contains 117 unequal unordered pairs, 2 orders, and 4 prior opcodes (936 frames); there are no new independent challenge pairs in this study. The ideal grid is the full 128 x 128 ordered interface, with an additional legal-domain a+b<128 subset. The ideal grid intentionally overlaps the named panels when input numbers coincide and does not exercise the receiver.

We externally specify either MAX or MIN on each query. Each query returns a seven-bit answer and the opcodes in the frame retain their original roles. Copy weights (63) and receiver parameters (1,290) stay fixed. The inherited comparator is divided by 64 preserving every prior decision. Both expanded arms add one weight and one bias (17 comparator/head parameters in all, 1,370 for the complete system); overwrite uses the original 1,368. Raw per-query weighted-edge MACs including receiver and mux: old or overwrite 1,304, expanded MIN 1,305. Python's offline lookup tabulates each exact neural copy output and picks its appropriate precomputed value for scoring. The verifier also runs the actual gate weights for all 32,768 possible word/side inputs.

The three seeds pair original receivers, fresh training batches and recovery batches. All decoded hard operands coincide across seeds on the measured panels. Variation between arms at a given seed is independent of batches; variation across seeds combines batch/receiver identity and is not a population estimate. Equal pairs are omitted during supervised training; copying either side scores correctly on equal test inputs. Frozen old MAX is preserved by design. The direct control has no task-dependent path. The learning outcome in the joint arm depends on the hard threshold's chosen backward surrogate and relative step sizes.

## Original three-arm results

Counts below are MAX/MIN correct among 936 reused challenge frames after exactly 512 MIN-only steps, followed by measurements after switching to old-only practice. Results are in seed order 101, 202, 303.

| Arm | 512 MIN steps | Comparator restored (no training) | 128 MAX recovery steps |
|---|---|---|---|
| Frozen | 936/936 each | 936/936 each | 936/936 each (zero optimizer steps) |
| Joint | 24/912, 16/920, 16/920 | 936/0 each | 468/468, 348/588, 400/536 |
| Direct overwrite | 0/936, 0/936, 8/928 | 936/0 each | 212/724, 196/740, 184/752 |

The frozen adapter first reached 95% on validation at registered step 64 in all seeds and gave both functions exactly over all 16,384 ideal pairs at that checkpoint. Joint first crossed 95% on validation at registered step 512 in all seeds, direct at 256. On the full ideal grid at 512, joint MAX correct was 2,149/1,865/1,977 of 16,384 and MIN correct was 14,363/14,647/14,535. Rerouting the final joint model with only its old comparator restored removed MIN performance on all 936 unequal cases, localizing the acquired behavior to the shared comparator conditional on the retained adapter. The final joint adapter is identity on its two possible input signs. Frozen instead learned the inverse on both signs. These observations describe this two-choice task and optimizer. They do not establish a general freezing schedule, natural-language learning, autonomous growth, or a SLE encoding advantage.

## Artifacts

- `PREREG.md` is the unchanged original three-arm plan.
- `results/run_receipt.json` lists methods, resources, timing and update accounting. The main fits used 4,608 MIN updates and 768 MAX recovery updates across nine runs. Receiver training is inherited (5,120 prior updates per lineage).
- `results/*/states.npz` contains all comparator, adapter and Adam states (stages 0–512 MIN, weights-only restoration, and 1–128 MAX recovery). The restoration checkpoint's optimizer fields identify the original end-stage state for provenance; it isn't resumed.
- `results/*/{train,val,test,challenge,ideal}.npz` records the complete two selector bits and two numeric answers at every checkpoint, ordered like the inherited data. Equal-value changed sides and changed numerical answers are scored separately.
- `results/batches_*.npz` contains the actual paired batch row IDs; `results/metrics.json` has per-stage counts. `replay_receipt.json` records the read-only replay.
- Provenance: U, the user's small added-network and early-interference hypothesis; F, PR133's receiver, MAX comparator, copy gates, raw frames and prior challenge; T, results and signed-state interventions; A, the experimental design and transfer interpretation.
