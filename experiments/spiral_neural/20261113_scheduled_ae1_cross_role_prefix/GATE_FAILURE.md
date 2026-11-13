# AE1 prefix-role audit: pre-registered gate failure and correction (2026-11-13)

Original script commit: `dee980832994943e96794277bbfa1de0f5e94402`.
Frozen protocol commit: `1811d6fd6302e618aea2c11ccee1ca54a20f4c2c`.
Frozen source: PR #29 head `dcabc3a65a4b9e7a50ab83ff8266b2c233d15000`, result Git blob `7d87bfc417564c4af08892534d15b1b3af96e104`. No source data altered.

**First actual validation failed**, with `Error: High suffix invalid`. The script expected every `unseen_high`-labelled row to use ID15..29. Inspecting PR29's frozen `experiment.py` proves `rows('train',suffix_mode=...)` selects `suffix(a,b,epoch,mode)` whenever `which=='train'`, ignoring the passed `suffix_mode`. This is true for both r1 and r2, independent of students.

**Independent archive T:** for each of four students, all train `seen`, `changed_low`, `unseen_high` prediction tuples are byte-for-byte identical (both 24 r1 and 24 r2 per label); their suffix IDs stay in 0..14. Validation/test labels do correspond to different suffixes: high uses 15..29. A train/high score is **not** evidence of train high-suffix robustness. This does **not** invalidate PR29's stated val/test high-suffix outcomes.

**Amendment:** Preserve the original pre-registration and failure in Git history. Modify only the auditor's data validity gate so train permits the frozen-low suffix for each label, and explicitly **requires** identical train outputs across all three labels. Original research metric (first-word correctness under r1 vs r2, source/split/seed/model, budget) is unchanged. The amended audit remains post-hoc descriptive, no new training, no added seeds or test resampling.

[更新] Train/high and train/changed_low were aliases of train/seen. [取代] The original validity assumption that all three train-labelled suffix regimes differed. [原因] Frozen experiment.py branch plus 4-student archived tuple inspection. [狀態] Exact source-level and archive check: high confidence. The failure was a *new* audit gate failure, not a newly discovered bad NN checkpoint or a formally rerun NN train.

Reproduce after checking out this PR branch: `node experiments/spiral_neural/20261113_scheduled_ae1_cross_role_prefix/analysis.cjs selftest`; `node experiments/spiral_neural/20261113_scheduled_ae1_cross_role_prefix/analysis.cjs [source results.json] [new output.json]`.
