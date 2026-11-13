# SLE-AE1 high-r mixed curriculum: two new raw-bit students (2026-11-13)

Work ID: `SLE-AE1-HIGH-R-MIXED-20261113-11`. Independent NN research only; does not modify Hamster VM, parser dictionaries, Pro UR1 or Codex branches. This branch is stacked on PR #39 head `b18bc81009364318b14e35fada37036e4e412719`, not main. No merge authorized.

## Prior evidence, rationale, and provenance

[F] Existing PR #39 (two seeds, two fresh curriculum arms, same 120 raw-bit payloads): HIGH_OUTPUT directly taught high values in answer word 2; HIGH_INPUT_ONLY encountered the same values in inputs but not answer word 2. Both showed strong position-conditional training. Earlier PR #36–#38 showed location teaching and value exposure mattered. This is **not** a generic proof of algorithm learning.

[U] The author asked for actual small-network learning tests of 01 SLE, controlled variables, preserved negative results, and cost accounting. [A] Prediction: alternate high values between r1 and r2 while maintaining identical payload count and total answer-length exposure, to allow generalization to unseen low partner IDs.

## Single experimental factor and frozen method

Change only **r allocation over the same 120 training payloads**: 36 new-high values ID15..23 paired with low first-word ID0..3 are distributed 18 as r1 and 18 as r2, each high value appearing twice at each r; reciprocal reallocation of 36 low controls preserves 60 total r1 and 60 total r2. Base curriculum train 48 questions remains unchanged. Different r necessarily changes the question parameter bits and answer labels; the intervention isolates the *allocation policy*, not a single neuron mechanism.

Legal wire profile: `SLE-AE1-n5-v1`, `01+010+r(3 bits)+0+4*(5 data bits+0)+111100`, fixed 39-bit native 01 Q, ordinary word IDs0..29, END30/UP31 reserved. Output first r complete tokens and an **external** `S` stopping action; no teacher oracle is fed to the student. For example r1 Q `010100010001010011110000000000000111100` -> `001010S`; r2 same payload Q `010100100001010011110000000000000111100` -> `001010011110S`.

Train: base low pair 24 distinct payloads x two r (48 questions), high 36, low controls 36 => 120 questions / 1,200 supervised target-prefix samples per epoch. Base split according to `(a+b)%6`: train 24 pairs, val 6 pairs, test 6 pairs, each doubled r1/r2. High val partner a=4, test a=5, high ID15..23 all values (9 for each r); neither partner was present among high training pairs, although similar test domains were examined in previous research. Seeds 101 and 202; each fresh 10,499-parameter 160->64 tanh->3 MLP, Adam 0.003, batch64, gradient clipping1.0, 200 epochs, 3,800 updates per student. Same initial RNG mapping, same optimizer updates and target-count budgets as #39.

Pre-registered gates: base train >=44/48, mixed high train r1/r2 >=14/18 each; when fit passes, high test r1 >=5/9 and r2 >=8/9 and STOP >=8/9 for both seeds. No retuning, additional seeds, or changing split after scores. Frozen public prereg commit `b4ecf4504978aec381d7f4126b1373eead406865` happened **before training**; earlier `9fb37a957822aabcbc3548bad6a8ae01d08f6a81` preceded two preflight Python loader errors, both fixed without running optimizer steps.

Frozen runner SHA256: `79dc4dca3c8e03f3889258a33532b639f5db11c0d3a6cf12dcba79443c826193`. Git runner blob `9b1c56180ee087f2bfce7d15f81af67c2aa4c699`. Parent PR39 runner SHA256 `bf97b897c89f97a40d9e34247990112e4319513054eb873d02329e8b27dc9ffc`. Parent PR36 runner SHA256 `05e2d730eecefcb50fa92392697556ffde313f5ecb59c2f4e583aad52e321303`. Pre-reg manifest SHA256 `e5693803ab1ef45b95d7a39971430ae12140da0e3ae53674c5400eb803b15703` (Git blob `32844715cf2dcf05ca8d1b402cf9c332bb72c2b5`).

## Real neural results (T)

| Seed | high train r1/r2 | high val r1/r2 | high test r1/r2 | base train / val / test |
| --- | --- | --- | --- | --- |
| 101 | 18/18, 18/18 | 9/9, 9/9 | **9/9, 9/9** | 48/48, 12/12, 12/12 |
| 202 | 18/18, 18/18 | 9/9, 9/9 | **9/9, 9/9** | 48/48, 12/12, 12/12 |

All pre-registered gates **PASS**; 288/288 generated outputs correct on the specified evaluation groups, every S at the correct position. Each checkpoint independently reloaded in a separately implemented NumPy forward to reproduce **288/288** bit-exact generated strings and per-question forward counts.

New *read-only* matched probes of the existing frozen PR39 checkpoints (144 actual cases, s=4/5, both r, high v15..23; no baseline retraining), per seed and per partner:
- PR39 HIGH_OUTPUT: r1 **1/9**, r2 **9/9**; r1 failures are present and preserved, e.g. a=4,b=16 expected `001000S`, generated `001010S`.
- PR39 HIGH_INPUT_ONLY: r1 **9/9**, r2 **0/9**; e.g. a=4,b=15 expected `001000011110S`, generated `001000001010S`.
- Mixed new model: r1 **9/9**, r2 **9/9** for each seed with s=4/5.
- All baseline probes correctly chose STOP position, despite wrong content. There are 68 incorrect baseline answers among these 144 evaluations.

Costs: two models x 200 epochs x 1,200 true-label training targets = **480,000** training forwards / 7,600 Adam updates; **5,007,360,000 dense forward MAC** (backprop and optimizer costs excluded), plus 2,880 generation forwards / 30,044,160 MAC. Parameters 10,499 each. Independent NumPy replay and 144 baseline probes performed **0 optimizer updates**. Torch CPU 2.10.0+cpu, NumPy2.3.5, deterministic algorithms enabled. The 288 outcomes include repeated shared base pairs across the two seeds; they are not 288 independent new task types.

Files: `run.py` and `verify_numpy.py` are public in this branch. Full raw evidence `raw_cases.jsonl` (288 rows, SHA256 `6a7ed2df3751a8130e337ac41541b1e4169accdfa16cd2141b0614d045fe354f`), `results.json`, `verification.json` (all 144 baseline probes and failures), and the two actual 10,499-param weight checkpoint JSONs are included in the companion reproducibility archive delivered to the owner. They are **not committed to this Git branch**, so a clone alone cannot verify checkpoint replay; no claim of full Git-only reproducibility. Checkpoint file SHA256 seed101 `ac022fdcac1c6e9de5b78e1667519a6443e05c7f8e48fe4b84514432a1576009` and seed202 `048c719e8c2afbbcac579b80a2f820989eb68ba030a1f2ce7c2747474897a157`.

Reproduction with the companion archive at `experiments/spiral_neural/`: `python 20261113_scheduled_high_r_mixed/run.py gate` then `python 20261113_scheduled_high_r_mixed/verify_numpy.py`. Running `train` is optional and **creates fresh checkpoints**, rather than verifying the old ones. No need to rerun previous #39 training.

## Interpretation and limitations

[更新] Both observed students learned the limited high-word r-selection and copy behavior when taught both response lengths on the same high values, without greater model size or target/update budget. [取代] In the previous single-role arms, r1 and r2 had been traded off. [原因] The two new mixed students passed paired high test r1 and r2, while frozen historical arms failed the complementary r. [狀態] High confidence for this specific observed domain; **low confidence for unseen high IDs, longer strings, genuine abstract copy, statistical population generality, or any specific neural mechanism**. This comparison controls the overall curriculum allocation, not every teacher-prefix distribution. Two seeds are insufficient for a general significance claim. These s=4/5 tests were not newly researcher-blinded.

NVIDIA calls: 0; the current tool environment does not expose authorized local OpenRouter worker or credentials. Local Codex calls: 0. No big-model/teacher oracle computed student answers, no merge, no protected-branch changes.

Next owner: independent researcher or authorized Codex. Next suggested *distinct* test: preregister a new **numeric-value-disjoint** test (e.g. v24..29 with matched bit-distribution control), or a longer-length r3 study; do not report this as new-value generalization. Before starting such training, obtain a new frozen manifest and ensure no concurrent PR already addresses it.
