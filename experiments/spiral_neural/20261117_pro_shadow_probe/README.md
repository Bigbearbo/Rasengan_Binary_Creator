# Pro shadow-rule probe study — 2026-11-17

This isolated study asks whether an inactive proposed shared rule can request informative labels before deployment. The known semantic groups, 8-gate handfilled base and external controller are experimental scaffolding; only four output values per correction cell are learned. It is not a native SLE-perception or SLE-versus-vector experiment.

## Preregistration

Protocol was published before the single main run, in commit `056f178f5630cf66785609d342b786e588d8d639`.
Protocol SHA256: `effba5c6990385b96b60793df1036107a432d4095fd5682a4a62aa53a85c58fa`.
Unmodified base/optimizer source comes from PR 124, pinned in the private archive.

## Design

Two contexts, 4 known meanings, 6 aliases each:48 pairs. Four worlds have identical taught prefixes but changes affecting 2,3,4 or all 6 aliases. Two aliases are permanently excluded from teaching and queries. A 43-key query pool contains only 2 initial candidate/incumbent disagreements. Compare exact repair, immediate consolidation, inactive shadow, uniform 1/2 queries and disagreement-filtered 1/2 queries. Both budgets use the same acceptance rule: at least 1 informative support and no informative contradiction, after consuming the full budget.

Ten namespace/operation seeds and 8 paired permutation/reversal orders are reused across worlds and teacher conditions. These are not 80 independent optimization seeds. A second teacher condition has one fixed wrong key; it is a sensitivity stress, not iid noise or a general noise-robust method.

## Executed findings

| Condition | Disagreement 1 query | Disagreement 2 queries |
|---|---:|---:|
| True shared rule, clean teacher: held-alias accuracy |100%|100%|
| Three changed aliases, clean teacher: false activation |50%|0%|
| Four changed aliases, clean teacher: false activation |100%|100%|
| Three changed aliases, one wrong key: false activation |100%|100%|
| True shared rule, one wrong key: held-alias accuracy |50%|0%|

The four-changed world and the all-six-changed world agree on every queryable label. Their states and decisions are identical but held truth differs. Both query budgets can therefore yield 46/48 overall correctness yet 0/2 held correctness. Matching overall 95.83% does not identify which capability is missing.

Uniform-query sampled true-shared activation rates were 2.50%/6.25%; exact exhaustive probabilities are 2/43=4.65% and 83/903=9.19%. Disagreement's advantage here is relevant-scope filtering; it is equivalent to random choice among the two relevant aliases and does not rank a hidden counterexample.

Shadow isolation prevents the candidate itself changing live answers. It does not stop learning a wrong teacher label as an exact local correction. For the two-changed world with a wrong teacher and 2 queries, the shared rule is rejected but final accuracy is 47/48 because one wrong exact correction remains.

## Work and validation

One automated main run:2,750 episodes, 9,340 saved states, 3,840 queries, 504 corrupt responses encountered. Actual executed updates:3,000 parent+123,000 branch=126,000. Summing inherited work across every episode gives 923,000 logical updates and must not be reported as executed training. Another 600 updates belong to focused controller fixtures. Main elapsed 9.1499 s includes scoring/serialization and is not a hardware benchmark. No external-model calls or manual training interventions.

Each extension cell stores 4 learned outputs, 3 fixed gate values, 8 Adam values, keys and counters. Pending shadow carries real storage. Known mapping and evidence are not free weights. Common candidate initialization computes about 15,264 MAC under the stated dense-base convention, plus comparisons/array operations; it also runs for uniform-query controls.

Independent replay:PASS across all episodes/states, 1,793,280 logits, 252,180 metric fields, 551,060 cost fields, 27,312 optimizer states and 7,592 enumerated query sets; maximum numerical difference 8.88 e-16. The first verifier pass missed three zero fields in its expected immediate-deployment log schema; only that verifier expectation was fixed, with no experiment/model/result change.

Fixed W integration:16 cases/32 new primitive calls, 0 training. All 16 correctly execute the model-selected plan;9 have the correct semantic plan and final answer, 7 semantic errors remain. Uses the prior Fable candidate word-level profile with raw bits archived, not the canonical 151-bit codec. This diagnostic is fixed, not a population estimate.

## Reproduce the saved-result audit

Obtain the authorized private artifact from its owner. Full private Fable source, weights, raw trajectories and report remain in that artifact rather than public Git.

| Artifact | Value |
|---|---|
| Filename | `sle_shadow_probe_20261117_v1.zip` |
| Bytes | 2811267 |
| SHA256 | `e295864648ee8a4f8d8d174541001cabebf2fc948dfaf28df414ef1d9c7c0a79` |
| ZIP CRC |PASS|
| Members |433 files;432 hashed payload members plus manifest|

Use Python 3.10+ and NumPy 1.26–2.x:

```sh
python replay_archive.py /absolute/path/sle_shadow_probe_20261117_v1.zip
```

The entry validates the pinned archive hash/size, CRC, every member size/hash and portable paths, extracts only checked ordinary files into a fresh temporary directory, and runs the independent verifier. It performs no new experiment training, W execution or network call. Numerical Adam recurrences are replayed only to verify saved states. Main training is not required for transport.

## Attribution and scope

U:user's needs-based growth/internal-SLE direction. F:prior research/core and primary literature. A:assistant's identity-preserving shadow/query controller and hypotheses. T:the executed study and checks above. Dot:transport only. Future work should hold this controller constant while changing the internal representation; this study does not establish SLE encoding superiority, autonomous query-policy invention or general robustness.

Primary references: [Freund et al.,1992](https://proceedings.neurips.cc/paper_files/paper/1992/hash/3871bd64012152bfb53fdf04b401193f-Abstract.html) for disagreement queries; [Dasgupta et al.,2007](https://papers.neurips.cc/paper_files/paper/2007/file/8f85517967795eeef66c225f7883bdcb-Paper.pdf) for agnostic active-learning assumptions. Neither paper's theorem is claimed for this toy controller.

Draft only. Main queue unchanged; no automatic merge. Windows verification is a separate Dot responsibility.
