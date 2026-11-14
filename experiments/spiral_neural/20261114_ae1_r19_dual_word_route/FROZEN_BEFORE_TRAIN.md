# R19 frozen-before-training protocol — 2026-11-14

work_id: AE1-R19-DUAL-WORD-ROUTE-20261114
owner: independent scheduled SLE native01 small-NN research
provenance: U author raw01 learner agenda; F R14 #63 code/course & R18 #67 weights; T local static prereg gate only before this Git commit; A second-word isolation mechanism hypothesis (low confidence)

## Exact single factor
Compare **immutable R18 first-word-masked checkpoint** to a NEW model that has the same input encoding, parameter count, optimizer, training data, initialization, seeds and budget, but ALSO masks every data word except `b` when predicting output positions 6..11. For positions 0..5 the original R18 `a` mask is retained; for cursor >=12 including STOP, all input words remain visible. The feature mask is a human-written prior, NOT independently learned copy routing.

## Native profile, data and split
SLE-AE1-n5-v1: raw Q `01 + 010 + r(3bits)+0 + 4*(word5bits+0) + END(111100)`, 39 binary bits. Ordinary words IDs 0..29; END30/UP31 reserved. Answer is first r words, each encoded in 6 bits, followed by student-generated external STOP `S` (not silently truncated). 136 training presentations, 112 unique, 1408 next-symbol targets each epoch, same as R18 #67 and original R14 #63. Distinct Q manifest contains **168 legal native01 inputs**: seen_baseline48, taught_high32, val_b24 8, test_mid_b20, test_high_b20, test_joint_ab20, test_r1_stop20. New heldout Q absent R14 course and R18 manifest, but some values have been studied by researchers in previous experiments, so no project-wide researcher-blind claim.

## Budget and preregistered gate
Seeds 101/202/303, each new student initialized identically to its R18 arm with `torch.manual_seed(seed+12000)`, PyTorch Adam lr0.003, cross entropy, grad clip1, batch64, 150 epochs, deterministic 3300 optimizer updates/seed =9900 total; 633600 training next-symbol targets, 10457 parameters/student, 10920 forward dense MAC/target =6,918,912,000 training forward dense MAC (excludes backward, eval and encoding). R18 baseline checkpoints reused read-only, no rerun baseline training.
PASS only if at least 2/3 seeds EACH achieve teacher-forced SECOND-word six-bit exact gain >=8/40 over frozen R18 in test_mid_b + test_high_b AND retain full free-answer exact seen_baseline >=40/48 and taught_high >=16/32 AND r1 correct stop position >=15/20. The second-word teacher-forced metric is diagnostic, NOT entire free response and NOT unassisted generative proof. Full free exact first/second/STOP, negative results and failures must be published regardless. No checkpoint cherry-pick, post-test seed additions, extra epochs, manifest edits, or adaptive stopping.

## Byte-frozen local source artifacts (SHA256)
- `experiment_r19/prereg.json`: `72c7c0782985a7cfcc564a5cdcc754638380e63efc2c38e52fb92fff0abbfc45`
- `experiment_r19/manifest.jsonl`: `972265d5f851727f3ce181b032032986374932e3bd8671f12b79722325b53edc`
- `experiment_r19/run_r19.py`: `2705913fe770783778cb45bed586eecfa397fccb86433cc0c9d392720c3da682`
- R14 #63 `run.py`: `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a`
- R14 #63 parent course: `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a`
- R18 #67 `run_r18.py`: `4793596815bcac55803fae9bcb3a09526caaa7e10dbd00e6f645ae325e256722`
- R18 #67 `prereg.json`: `1af7c2002e3d47cae400859203352a999645cb86a3864db93c90ec7f1d19c795`
- R18 weights seed101: `9a459111552d90f857e00f854aaa89cc1d10bb680d80663bb8c9670aa9ae44ed`
- R18 weights seed202: `225a28f6e1871b44236627e0ed1ab60ad69085891ec04a1fc2d66782689ca5a4`
- R18 weights seed303: `c0b3b083f6b85bad5a6f03589fe95351f17085f761c5df3c7475de9db46fc004`
- raw training-course SHA256 `5c40359f46f23452b571edab5872a077fd1f296b7619cfe01d25b16951e47d40`

## Before first neural forward
Local static, non-neural `python experiment_r19/run_r19.py gate --source-root <R18 companion extraction>` returned `STATIC GATE PASS`: source and weights SHA correct; profile, training counts, split exclusions, manifest and unique Q, parameter/MAC passed. This is **not** neural inference. New training must not start before this Git commit is acknowledged; freeze is immutable. Complete machine-readable manifest, runner, checkpoint and raw output will be in companion ZIP and/or later Git evidence. Public repository is not a place for private conversations, keys, or account traces.

NVIDIA: 0 actual calls; no configured authorized read-only endpoint. Local Codex/Gemini: 0 calls. Do not touch Pro UR1 PR #12 manifest/approval, Codex or VM branches. No merge.
