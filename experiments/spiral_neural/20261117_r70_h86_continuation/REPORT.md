# R70 — Fable151 trained B H86 old-skill pretraining continuation

Scope: independent scheduled neural researcher; no Hamster VM, grammar tree, Pro UR1, Codex P030–P035, LEFT or H110 experiment. Public Git preregistration **before** new training: `a5e893ee19105db8cc3a1a3befb8d37fb77003b8` at `research/sle-nn-r70-old-h86-continuation-20261117`, parent R69 PR #120 head `2e3ecd4600a7ca1ca422fe7d3c3d2388d53b81c2`.

## Single manipulation and invariant controls

F: unchanged R69 saved B checkpoint at step4096, Adam first/second moment and RNG state, and immutable `hand.py` / `compiler.py` / `filltrain.py` whose SHA256 match original R69. Same Fable151 fixed experimental 151-bit input / 41-bit output, **not** certified normative SLE-AE1. Same original 94 train/16 val/16 test word-value pools, hand.sets(2603). Same nine old skills, 64 examples/update, original source mix, full 16,639-parameter tanh H86 architecture (16,512 dense forward MAC), lr=.003 Adam, global gradient norm clipping, all parameters trainable. Three preselected seeds 101,202,303; no new seed or seed selection.

T: only **4096 more updates**, from 4096→8192 per original seed. Checkpoints fixed at 4096,4608,5120,6144,8192. Validation used to find first observed >=95% full-sentence+submit on each of nine skills. At 256 Q per skill, threshold is >=244/256; PUNCT 1/1. At 4096 original validation per-family was independently matched exactly before new training. Same raw val/test records frozen; old R69 test has already been viewed, so any R70 test is **not new blind**. Test was inspected only after final 8192 training and not used to choose changes.

## Real results

| B seed | val whole at 4096 | first observed 9-family >=95% | val whole 8192 | final formerly-inspected test 8192 | COPY4 val 4096→8192 | R3 val 4096→8192 |
|---|---:|---:|---:|---:|---:|---:|
| 101 | 2014/2049 | 5120 | 2044/2049 | 4086/4097 | 239→254 /256 | 254→256 /256 |
| 202 | 2003/2049 | 5120 | 2047/2049 | 4090/4097 | 241→255 /256 | 242→256 /256 |
| 303 | 2011/2049 | 4608 | 2043/2049 | 4088/4097 | 243→255 /256 | 251→256 /256 |

All three seed B models meet the preregistered nine-family validation >=95% comparability gate at a fixed checkpoint. At 8192 each seed's minimum validation skill score >95%. This removes the specific R69 blocked status **under the preregistered threshold only**. It does not equal A's 100% baseline, prove A/B causal initialization effects, or justify LEFT success claims. First gate observation is bounded by two evaluated checkpoints, not by a precise number of individual questions.

Pretraining total B cost per seed: 8192 Adam updates, 524,288 training question appearances; 3 students total 24,576 updates, 1,572,864 appearances. This run added 12,288 updates and 786,432 appearances, theoretical forward dense MAC **12,985,565,184** (this does not count backprop, evaluation or human hand-design cost). A original handfilled H86 had 0 *optimizer* updates, but its manual encoding/build cost is unmeasured; B initial training is not free.

## Validation and provenance

R70 independent raw-bit NumPy checker reproduced all 3×5=15 fixed validation checkpoint score sets and the three final test score sets, including 4096 baseline equality with R69. All new checkpoints include full weights, m/v, RNG state and update number. The TRAIN-only continuation stream's SHA256 per seed and final failure rows are saved. Original R69 ZIP SHA256: `22179e2b944c616d3559195361901dc36c941b788b0340ab58ea9fcb0be94890`. R70 main runner SHA256: `cfbfb0048a213b942b4b75cf01467370a30dfc26933f616c5e77dca045d79cdf`. The original Fable SHA mapping is in public prereg and output JSON; private Fable source is available only in authorized GPT Library and inside this private handoff archive, never public Git.

U = user-specified causal comparison and threshold protocol. F = R69 checked archive and locked Fable source. T = this run's new 3-seed additional training + 15 validation checkpoint/3 final test independent raw-bit replay. A = further inference that B is now eligible to attempt H110 LEFT paired comparison under the stated baseline gate. NVIDIA actual calls: 0 (no authorized model endpoint in current chat), Windows Codex: 0, Gemini: 0. No PR automatically merged or altered other workstream branch.

## Next owner

Separate study: A original handfilled H86 and the three now gate-eligible B H86→H110 using identical neuron initialization, optimizer/reset/freeze and original legal LEFT codec; C random H110 reference. Before training freeze paired 3/4 word ECHO/REV/LEFT panel (including word-value pool exposure, full information-bit 0/1, and triple noncolliding outputs), same batches and evaluation checkpoints, test locked, carry old-skill retention, count cumulative LEFT exposures and new unique ordered payloads. B 8192 old-skill pretraining must appear as separate cost. Be clear A still outperforms B slightly at zero-step baseline. Avoid treating R68 synthetic 1..16 candidate panel as Fable-valid corpus.

Replay: from packaged root run `OPENBLAS_NUM_THREADS=1 python run_r70.py` (the script resumes original R69 4096 checkpoints) then `OPENBLAS_NUM_THREADS=1 python verify_r70.py`; results are deterministic within reported floating-point environment. The archive is private because it contains original Fable source; public Git may contain sanitized script/report but **must not** mirror Fable originals.