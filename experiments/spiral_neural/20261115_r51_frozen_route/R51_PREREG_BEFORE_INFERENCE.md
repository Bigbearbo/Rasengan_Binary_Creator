# R51 pre-inference freeze — immutable R50 checkpoints, b-only projection
Date: 2026-11-15. Owner: independent SLE raw-01 small-NN lane.
Source parent: R50 PR #101, head `7bb9923a1399db474f4ea29b758ef8fce75f1382`. This commit is **before any R51 model forward**. Do not auto-merge.

## One causal variable
Exactly three R50 students (seed 101,202,303), all **frozen**. Compare the already archived R50 full a+b+c+d inference with **only b visible at second answer positions cursor 6..11**. First-answer, STOP, model/weights, codec, questions, course, Adam history unchanged. No teacher targets provided during free output; gold-prefix diagnostics separately labeled. This is *not* learned routing.

## Legal input/output / corpus
SLE-AE1-n5-v1 (0..29); raw input is exactly 39 literal 01 bits:
`01+010+bin3(r)+0+4*(bin5(v)+0)+111100`.
Answer `r*(bin5(v)+0)` followed by external stop action `S` (not on-wire punctuation). Fixed 136 original R50 training events (read-only), 80 historical retention Q, 96 exposed legacy Q, 96 R50-tested new exact-Q contexts, total 272 Q ×3 seeds = 816 pairs. Already exposed b18–29 values; neither test set is a new numeric-value blind split. No split tuning.

## Model / resources / checks
10,457 trainable parameters per student; 0 new optimizer updates, 0 target presentations, 0 training MAC. Count actual inference calls; theoretical dense forward 10,920 MAC/call (backward absent).
Predeclared **joint gate ALL REQUIRED**, else FAIL:
1. R50 b-only secondword on 96 new-context Q ×3 seeds improves at least +48/288 over full-open R50.
2. 96 legacy Q ×3 seeds secondword improves at least +48/288.
3. Firstword correctness remains identical in all 816 paired rows.
4. New-context full exact (including autonomous STOP) does not fall below old 28/288.
5. At most 12/240 previously correct historical retention complete answers are lost.

Preserve every generated raw 01 answer, success/failure, per-seed split, teacher-forced secondword and STOP checks separately. Replay all outputs in PyTorch and independent NumPy; assert non-intervened logits identical. No extras after seeing results.

## Frozen evidence / companion
R50 ZIP sha256 `0f41050c5b09ca46465995e8779fc1530c37c2ff7a6d5ad5a3b4df415a6981e1` (previous conversation attachment; not available inside Git).
R50 raw-result sha256 `04d9d87f91711a414b5ef7f6b8228d862c297a1afc885c3a0ed9ba82eefc4ee3`.
R50 checkpoint SHA256:
101 `8a30848c1084627fb8fb20bacbd8f844e8b9fb22a27879d6bf8202bdb6499417`
202 `490da5ea65b1ddf4119c573c3b048c84824905434a7241ba717bd036c5a0fc7e`
303 `c5c6a56b795ca114eb4cd42104f4d9aab056be77d61dfad11cbd1a1bb3993d6f`.
Local full R51 prereg sha256 `9697e921d49ab91508094c1ff890389520e73817c7a52ed641c60a5dbc0368af`.
Frozen pre-inference runner sha256 `dea69e7d3b39a5b9e677000b12ed09251cffa37f92663cb38eeaab93872ec159`. Source and prereg will be retained in the companion archive, Git contains this pre-inference freeze receipt.

Provenance: **U** independent 01 NN remit; **F** Git PR #101, prior R50 ZIP/checkpoint/manifest, PR #12 Pro UR1 and #5 shared bank were read as separate tracks; **T** prior archive integrity/static PASS before freeze only, no R51 model calls; **A** projection could restore residual b information, uncertain. NVIDIA/Codex/Gemini actual calls 0; no authorized NVIDIA runner, no other worker output claimed. No Pro/Codex/VM branch writes.
